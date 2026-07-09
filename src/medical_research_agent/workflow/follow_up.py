"""Bounded evidence-gap follow-up search orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from medical_research_agent.connectors import ConnectorError, DuckDuckGoHTMLSearchConnector, SearchRequest
from medical_research_agent.evidence import extract_evidence_from_documents
from medical_research_agent.evidence_dedup import deduplicate_evidence_items
from medical_research_agent.evidence_gaps import detect_evidence_gaps, plan_follow_up_searches
from medical_research_agent.parsers import DocumentParseError, PDFParser, WebPageParser
from medical_research_agent.schemas import EvidenceItem, ParsedDocument, ProductSpec, SourceRecord, SourceType
from medical_research_agent.source_quality import review_source_quality
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
    errors: list[str] = []

    if follow_up_items and state.get("use_real_connectors"):
        raw_sources = _search_follow_up_sources(task.task_id, follow_up_items, adapters.vendor_connector, errors)
        review = review_source_quality(raw_sources, plan.query_expansion)
        accepted = [_mark_follow_up_source(source, follow_up_items) for source in review.accepted]
        rejected.extend(_mark_follow_up_source(source, follow_up_items) for source in review.rejected)
        sources.extend(accepted)
        documents.extend(_parse_follow_up_sources(accepted, adapters, errors))

    extracted = extract_evidence_from_documents(task.task_id, sources, documents)
    deduped = deduplicate_evidence_items(extracted.evidence, extracted.product_specs)
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

    result = run_bounded_follow_up(
        state,
        FollowUpAdapters(
            vendor_connector=DuckDuckGoHTMLSearchConnector(source_type=SourceType.VENDOR_PUBLIC_DOC),
            web_parser=WebPageParser(),
            pdf_parser=PDFParser(),
        ),
    )
    return {
        "sources": result.sources,
        "rejected_sources": result.rejected_sources,
        "documents": result.documents,
        "evidence": result.evidence,
        "product_specs": result.product_specs,
        "current_step": "follow_up_evidence_gaps",
        "intermediate": {
            "evidence_gaps": result.evidence_gaps,
            "follow_up_searches": result.follow_up_searches,
            "follow_up_round_count": result.follow_up_round_count,
            "follow_up_added_source_count": result.follow_up_added_source_count,
        },
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


def _search_follow_up_sources(
    task_id: str,
    items: list[SearchPlanItem],
    connector: SearchConnector,
    errors: list[str],
) -> list[SourceRecord]:
    sources: list[SourceRecord] = []
    for item in items:
        request = SearchRequest(
            query=item.query,
            limit=item.limit,
            task_id=task_id,
            metadata={
                "expanded_terms": item.expanded_terms,
                "facet": item.facet.value if item.facet else None,
                "source_type": item.source_type.value,
                "preferred_connectors": item.preferred_connectors,
                "follow_up_round": item.metadata["follow_up_round"],
                "gap_facet": item.metadata["gap_facet"].value,
                "bounded": True,
            },
        )
        try:
            records = connector.search(request)
        except ConnectorError as exc:
            errors.append(f"{exc} [follow_up_round=1; gap_facet={request.metadata['gap_facet']}]")
            continue
        for record in records:
            record.metadata.setdefault("rationale", item.rationale)
            record.metadata.setdefault("facet", item.facet.value if item.facet else None)
            record.metadata.setdefault("preferred_connectors", item.preferred_connectors)
            record.metadata.setdefault("route_priority", item.route_priority)
            record.metadata["follow_up_round"] = item.metadata["follow_up_round"]
            record.metadata["gap_facet"] = item.metadata["gap_facet"].value
            record.metadata["bounded"] = True
        sources.extend(records)
    return sources


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
        metadata["bounded"] = True
    return source.model_copy(update={"metadata": metadata})


def _mark_follow_up_document(document: ParsedDocument, source: SourceRecord) -> ParsedDocument:
    metadata = {
        **document.metadata,
        "follow_up_round": source.metadata.get("follow_up_round"),
        "gap_facet": source.metadata.get("gap_facet"),
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
        "bounded": True,
    }
