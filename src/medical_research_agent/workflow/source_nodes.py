"""Source-search and parsing workflow nodes for real public connectors."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any, assert_never

from medical_research_agent.config import AppSettings, get_settings
from medical_research_agent.connectors import (
    AccessGUDIDConnector,
    ClinicalTrialsConnector,
    ConnectorError,
    CrossrefConnector,
    DuckDuckGoHTMLSearchConnector,
    EuropePMCConnector,
    OpenFDA510kConnector,
    OpenAlexConnector,
    PatentsViewConnector,
    PMCFullTextConnector,
    PubMedConnector,
    SearchRequest,
    SemanticScholarConnector,
    SourceConnector,
)
from medical_research_agent.parsers import PDFParser, WebPageParser
from medical_research_agent.resource_context import managed_resource
from medical_research_agent.schemas import SourceRecord, SourceType
from medical_research_agent.source_access import SourceAccessVerifier
from medical_research_agent.source_contracts import CitationEligibility
from medical_research_agent.source_triage import review_sources_with_configured_llm_triage
from medical_research_agent.source_triage_models import with_access_metadata
from medical_research_agent.workflow.source_access_contracts import effective_access_check
from medical_research_agent.workflow.source_parsing import fetch_and_parse_sources_real as _fetch_and_parse_sources_real
from medical_research_agent.workflow.state import NodeLog, SearchPlanItem, WorkflowState


def _log(node: str, message: str, **metadata: Any) -> list[NodeLog]:
    return [NodeLog(node=node, message=message, metadata=metadata)]


def search_sources_real(state: WorkflowState) -> dict[str, Any]:
    """Run public connectors and preserve workflow progress on failures."""

    task = state["task"]
    plan = state["research_plan"]
    settings = get_settings()
    sources: list[SourceRecord] = []
    errors: list[str] = []

    connector_counts: dict[str, int] = {}

    for index, item in enumerate(plan.search_items, start=1):
        request = SearchRequest(
            query=item.query,
            limit=item.limit,
            task_id=task.task_id,
            metadata={
                "expanded_terms": item.expanded_terms,
                "facet": item.facet.value if item.facet else None,
                "source_type": item.source_type.value,
                "preferred_connectors": item.preferred_connectors,
            },
        )
        match SourceType(item.source_type):
            case SourceType.PUBLIC_LITERATURE | SourceType.VENDOR_PUBLIC_DOC | SourceType.PUBLIC_REGULATORY | SourceType.PUBLIC_WEB:
                item_sources, item_errors = _run_connectors(route_connectors(item, settings), request, item, connector_counts)
                sources.extend(item_sources)
                errors.extend(item_errors)
            case SourceType.USER_UPLOADED_PRIVATE | SourceType.INTERNAL_PRIVATE:
                sources.append(_placeholder_source(task.task_id, index, item))
            case unreachable:
                assert_never(unreachable)

    message = "Searched public source connectors."
    if errors:
        message = "Searched public source connectors with recoverable errors."

    with managed_resource(SourceAccessVerifier()) as verifier:
        access_checks = [effective_access_check(source, verifier) for source in sources]
    verified_sources = [
        with_access_metadata(source, access_check, CitationEligibility.from_access_check(access_check))
        for source, access_check in zip(sources, access_checks, strict=True)
    ]
    review = review_sources_with_configured_llm_triage(
        verified_sources,
        plan.query_expansion,
        access_checks=access_checks,
        require_access_check=True,
    )
    rejected_sources = [*review.rejected, *review.pending_review]

    return {
        "sources": list(review.accepted),
        "rejected_sources": rejected_sources,
        "current_step": "search_sources",
        "intermediate": {
            "source_count": len(review.accepted),
            "raw_source_count": len(sources),
            "rejected_source_count": len(rejected_sources),
            "pending_source_review_count": len(review.pending_review),
            "source_quality_status": review.status.value,
            "source_triage_status": review.status.value,
            "source_triage_llm_used": review.llm_used,
            "source_triage_follow_up_queries": list(review.follow_up_queries),
            "source_triage_follow_up_searches": [
                item.model_dump(mode="json") for item in review.follow_up_searches
            ],
            "source_access_check_count": len(access_checks),
            "source_access_rejected_count": sum(
                not CitationEligibility.from_access_check(access_check).eligible for access_check in access_checks
            ),
            "connector_counts": connector_counts,
            "source_error_count": len(errors),
        },
        "errors": errors,
        "node_logs": _log(
            "search_sources",
            message,
            source_count=len(review.accepted),
            rejected_source_count=len(rejected_sources),
            pending_source_review_count=len(review.pending_review),
            source_triage_llm_used=review.llm_used,
            source_access_check_count=len(access_checks),
            connector_counts=connector_counts,
            error_count=len(errors),
        ),
    }


def fetch_and_parse_sources_real(state: WorkflowState) -> dict[str, Any]:
    """Preserve the parser injection seam for source workflow callers and tests."""

    return _fetch_and_parse_sources_real(
        state,
        web_parser_factory=WebPageParser,
        pdf_parser_factory=PDFParser,
    )


def _run_connectors(
    connectors: Sequence[SourceConnector],
    request: SearchRequest,
    item: SearchPlanItem,
    connector_counts: dict[str, int],
) -> tuple[list[SourceRecord], list[str]]:
    sources: list[SourceRecord] = []
    errors: list[str] = []
    for connector in connectors:
        try:
            with managed_resource(connector):
                records = connector.search(request)
        except ConnectorError as exc:
            errors.append(
                f"{exc} [kind={exc.kind.value}; "
                f"facet={item.facet.value if item.facet else 'unspecified'}; "
                f"source_type={item.source_type.value}]"
            )
            connector_counts[connector.name] = connector_counts.get(connector.name, 0)
            continue
        for record in records:
            record.metadata.setdefault("rationale", item.rationale)
            record.metadata.setdefault("facet", item.facet.value if item.facet else None)
            record.metadata.setdefault("preferred_connectors", item.preferred_connectors)
            record.metadata.setdefault("route_priority", item.route_priority)
        sources.extend(records)
        connector_counts[connector.name] = connector_counts.get(connector.name, 0) + len(records)
    return sources, errors


def route_connectors(item: SearchPlanItem, settings: AppSettings) -> tuple[SourceConnector, ...]:
    """Build only the bounded connector families explicitly selected for one search item."""

    source_type = SourceType(item.source_type)
    builders: dict[str, Callable[[], SourceConnector]] = {
        "pubmed": PubMedConnector,
        "crossref": CrossrefConnector,
        "semantic_scholar": lambda: SemanticScholarConnector(api_key=settings.semantic_scholar_api_key_value()),
        "pmc": PMCFullTextConnector,
        "europe_pmc": EuropePMCConnector,
        "openalex": OpenAlexConnector,
        "duckduckgo_html": lambda: DuckDuckGoHTMLSearchConnector(source_type=source_type),
        "openfda_510k": OpenFDA510kConnector,
        "clinicaltrials_gov": ClinicalTrialsConnector,
        "accessgudid": AccessGUDIDConnector,
        "patentsview": PatentsViewConnector,
    }
    return tuple(
        builder()
        for connector_name in item.preferred_connectors
        if (builder := builders.get(connector_name)) is not None
    )


def _placeholder_source(task_id: str, index: int, item: SearchPlanItem) -> SourceRecord:
    return SourceRecord(
        task_id=task_id,
        source_type=item.source_type,
        title=f"Pending source search {index}: {item.source_type.value}",
        publisher="Workflow placeholder",
        search_query=item.query,
        credibility_note="Real connector not implemented for this source type yet.",
        metadata={
            "placeholder": True,
            "rationale": item.rationale,
            "facet": item.facet.value if item.facet else None,
            "preferred_connectors": item.preferred_connectors,
            "route_priority": item.route_priority,
        },
    )
