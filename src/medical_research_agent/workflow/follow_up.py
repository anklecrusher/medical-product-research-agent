"""Bounded evidence-gap follow-up search orchestration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

from medical_research_agent.config import get_settings
from medical_research_agent.connectors import DuckDuckGoHTMLSearchConnector, SearchRequest
from medical_research_agent.evidence import extract_evidence_from_documents
from medical_research_agent.evidence_dedup import deduplicate_evidence_items
from medical_research_agent.evidence_gaps import detect_evidence_gaps, plan_follow_up_searches
from medical_research_agent.parsers import DocumentParseError, PDFParser, WebPageParser
from medical_research_agent.resource_context import managed_resource
from medical_research_agent.schemas import EvidenceItem, ParsedDocument, ProductSpec, SourceRecord, SourceType
from medical_research_agent.source_access import SourceAccessVerifier
from medical_research_agent.source_contracts import CitationEligibility
from medical_research_agent.source_triage import review_sources_with_configured_llm_triage
from medical_research_agent.source_triage_models import with_access_metadata
from medical_research_agent.source_quality import SourceQualityStatus
from medical_research_agent.workflow.source_access_contracts import effective_access_check
from medical_research_agent.workflow.follow_up_search import search_follow_up_sources as _search_follow_up_sources
from medical_research_agent.workflow.source_nodes import route_connectors
from medical_research_agent.workflow.state import NodeLog
from medical_research_agent.workflow.state import ResearchPlan, SearchPlanItem, WorkflowState


class SearchConnector(Protocol):
    name: str

    def search(self, request: SearchRequest) -> list[SourceRecord]:
        """Return connector sources for a normalized request."""


class SourceParser(Protocol):
    def parse_url(self, source: SourceRecord) -> ParsedDocument:
        """Parse one URL-backed source into a document."""


@dataclass(frozen=True, slots=True)
class FollowUpAdapters:
    vendor_connector: SearchConnector
    web_parser: SourceParser
    pdf_parser: SourceParser
    connector_selector: Callable[[SearchPlanItem], tuple[SearchConnector, ...]] | None = None


@dataclass(frozen=True, slots=True)
class FollowUpResult:
    sources: list[SourceRecord]
    rejected_sources: list[SourceRecord]
    documents: list[ParsedDocument]
    evidence: list[EvidenceItem]
    product_specs: list[ProductSpec]
    evidence_gaps: list[dict[str, str | list[str]]]
    follow_up_searches: list[dict[str, str | int | bool | list[str]]]
    follow_up_round_count: int
    follow_up_added_source_count: int
    errors: list[str]


def run_bounded_follow_up(
    state: WorkflowState,
    adapters: FollowUpAdapters,
) -> FollowUpResult:
    """Run one explicit gap-driven follow-up round and return merged state slices."""

    plan = state["research_plan"]
    task = state["task"]
    initial_gaps = detect_evidence_gaps(plan, state.get("sources", []), state.get("evidence", []))
    follow_up_items = plan_follow_up_searches(plan, initial_gaps, follow_up_round=1)
    searches = [_search_snapshot(item) for item in follow_up_items]
    sources = list(state.get("sources", []))
    rejected = list(state.get("rejected_sources", []))
    documents = list(state.get("documents", []))
    new_sources: list[SourceRecord] = []
    new_documents: list[ParsedDocument] = []
    errors: list[str] = []

    if follow_up_items and state.get("use_real_connectors"):
        raw_sources = _search_follow_up_sources(task.task_id, follow_up_items, adapters, errors)
        unique_sources = _unique_sources_by_id(raw_sources)
        with managed_resource(SourceAccessVerifier()) as verifier:
            access_checks = [effective_access_check(source, verifier) for source in unique_sources]
        verified_sources = [
            with_access_metadata(source, access_check, CitationEligibility.from_access_check(access_check))
            for source, access_check in zip(unique_sources, access_checks, strict=True)
        ]
        review = review_sources_with_configured_llm_triage(
            verified_sources,
            plan.query_expansion,
            access_checks=access_checks,
            require_access_check=True,
        )
        accepted = [_mark_follow_up_source(source, follow_up_items) for source in review.accepted]
        rejected.extend(_mark_follow_up_source(source, follow_up_items) for source in (*review.rejected, *review.pending_review))
        new_sources.extend(accepted)
        sources.extend(accepted)
        new_documents.extend(_parse_follow_up_sources(accepted, adapters, errors))
        documents.extend(new_documents)

    extracted = extract_evidence_from_documents(task.task_id, new_sources, new_documents)
    deduped = deduplicate_evidence_items(
        [*state.get("evidence", []), *extracted.evidence],
        [*state.get("product_specs", []), *extracted.product_specs],
    )
    final_gaps = detect_evidence_gaps(plan, sources, deduped.evidence)
    return FollowUpResult(
        sources=sources,
        rejected_sources=rejected,
        documents=documents,
        evidence=deduped.evidence,
        product_specs=deduped.product_specs,
        evidence_gaps=[_gap_snapshot(gap) for gap in final_gaps],
        follow_up_searches=searches,
        follow_up_round_count=1 if follow_up_items else 0,
        follow_up_added_source_count=len(sources) - len(state.get("sources", [])),
        errors=errors,
    )


def follow_up_evidence_gaps(state: WorkflowState) -> dict[str, Any]:
    """Run one bounded follow-up search round for missing required facets."""

    settings = get_settings()
    with (
        managed_resource(DuckDuckGoHTMLSearchConnector(source_type=SourceType.VENDOR_PUBLIC_DOC)) as vendor_connector,
        managed_resource(WebPageParser()) as web_parser,
        managed_resource(PDFParser()) as pdf_parser,
    ):
        result = run_bounded_follow_up(
            state,
            FollowUpAdapters(
                vendor_connector=vendor_connector,
                web_parser=web_parser,
                pdf_parser=pdf_parser,
                connector_selector=lambda item: route_connectors(item, settings),
            ),
        )
    intermediate: dict[str, Any] = {
        "evidence_gaps": result.evidence_gaps,
        "follow_up_searches": result.follow_up_searches,
        "follow_up_round_count": result.follow_up_round_count,
        "follow_up_added_source_count": result.follow_up_added_source_count,
    }
    if result.follow_up_added_source_count > 0:
        intermediate["source_quality_status"] = SourceQualityStatus.HAS_ACCEPTED_SOURCES.value

    return {
        "sources": result.sources,
        "rejected_sources": result.rejected_sources,
        "documents": result.documents,
        "evidence": result.evidence,
        "product_specs": result.product_specs,
        "current_step": "follow_up_evidence_gaps",
        "intermediate": intermediate,
        "errors": result.errors,
        "node_logs": [
            NodeLog(
                node="follow_up_evidence_gaps",
                message="Ran bounded evidence-gap follow-up search.",
                metadata={
                    "follow_up_round_count": result.follow_up_round_count,
                    "follow_up_search_count": len(result.follow_up_searches),
                    "follow_up_added_source_count": result.follow_up_added_source_count,
                },
            )
        ],
    }


def _unique_sources_by_id(sources: list[SourceRecord]) -> list[SourceRecord]:
    seen: set[str] = set()
    unique_sources: list[SourceRecord] = []
    for source in sources:
        if source.source_id in seen:
            continue
        seen.add(source.source_id)
        unique_sources.append(source)
    return unique_sources


def _parse_follow_up_sources(
    sources: list[SourceRecord],
    adapters: FollowUpAdapters,
    errors: list[str],
) -> list[ParsedDocument]:
    documents: list[ParsedDocument] = []
    for source in sources:
        if source.url is None:
            continue
        parser = _parser_for_follow_up_source(source, adapters)
        try:
            document = parser.parse_url(source)
        except DocumentParseError as exc:
            errors.append(f"{source.source_id} {source.title}: {exc}")
            continue
        documents.append(_mark_follow_up_document(document, source))
    return documents


def _parser_for_follow_up_source(source: SourceRecord, adapters: FollowUpAdapters) -> SourceParser:
    url = str(source.url or "").lower().split("?")[0]
    if url.endswith(".pdf"):
        return adapters.pdf_parser
    return adapters.web_parser


def _mark_follow_up_source(source: SourceRecord, items: list[SearchPlanItem]) -> SourceRecord:
    item_by_facet = {item.facet: item for item in items}
    facet = source.metadata.get("facet")
    matched = item_by_facet.get(facet)
    metadata = dict(source.metadata)
    if matched is not None:
        metadata["follow_up_round"] = matched.metadata["follow_up_round"]
        metadata["gap_facet"] = matched.metadata["gap_facet"].value
        metadata["gap_description"] = matched.rationale
        metadata["bounded"] = True
    return source.model_copy(update={"metadata": metadata})


def _mark_follow_up_document(document: ParsedDocument, source: SourceRecord) -> ParsedDocument:
    metadata = {
        **document.metadata,
        "follow_up_round": source.metadata.get("follow_up_round"),
        "gap_facet": source.metadata.get("gap_facet"),
        "gap_description": source.metadata.get("gap_description"),
        "bounded": source.metadata.get("bounded"),
    }
    return document.model_copy(update={"metadata": metadata})


def _gap_snapshot(gap) -> dict[str, str | list[str]]:
    return {
        "facet": gap.facet.value,
        "status": gap.status.value,
        "description": gap.description,
        "required_source_types": [source_type.value for source_type in gap.required_source_types],
        "recommended_queries": list(gap.recommended_queries),
    }


def _search_snapshot(item: SearchPlanItem) -> dict[str, str | int | bool | list[str]]:
    return {
        "query": item.query,
        "source_type": item.source_type.value,
        "facet": item.facet.value if item.facet else "",
        "rationale": item.rationale,
        "expanded_terms": item.expanded_terms,
        "preferred_connectors": item.preferred_connectors,
        "follow_up_round": item.metadata["follow_up_round"],
        "gap_facet": item.metadata["gap_facet"].value,
        "gap_description": item.rationale,
        "bounded": True,
    }
