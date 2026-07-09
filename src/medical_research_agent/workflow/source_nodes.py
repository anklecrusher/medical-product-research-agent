"""Source-search and parsing workflow nodes for real public connectors."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, assert_never

from medical_research_agent.config import get_settings
from medical_research_agent.connectors import (
    ClinicalTrialsConnector,
    ConnectorError,
    CrossrefConnector,
    DuckDuckGoHTMLSearchConnector,
    OpenFDA510kConnector,
    PubMedConnector,
    SearchRequest,
    SemanticScholarConnector,
    SourceConnector,
)
from medical_research_agent.parsers import DocumentParseError, PDFParser, WebPageParser
from medical_research_agent.schemas import DocumentFormat, ParsedDocument, SourceRecord, SourceType
from medical_research_agent.source_quality import review_source_quality
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

    connector_groups = ConnectorGroups(
        literature=(
            PubMedConnector(),
            CrossrefConnector(),
            SemanticScholarConnector(api_key=settings.semantic_scholar_api_key_value()),
        ),
        vendor=(DuckDuckGoHTMLSearchConnector(source_type=SourceType.VENDOR_PUBLIC_DOC),),
        regulatory=(
            OpenFDA510kConnector(),
            ClinicalTrialsConnector(),
            DuckDuckGoHTMLSearchConnector(source_type=SourceType.PUBLIC_REGULATORY),
        ),
    )
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
            case SourceType.PUBLIC_LITERATURE:
                item_sources, item_errors = _run_connectors(connector_groups.literature, request, item, connector_counts)
                sources.extend(item_sources)
                errors.extend(item_errors)
            case SourceType.VENDOR_PUBLIC_DOC:
                item_sources, item_errors = _run_connectors(connector_groups.vendor, request, item, connector_counts)
                sources.extend(item_sources)
                errors.extend(item_errors)
            case SourceType.PUBLIC_REGULATORY:
                item_sources, item_errors = _run_connectors(connector_groups.regulatory, request, item, connector_counts)
                sources.extend(item_sources)
                errors.extend(item_errors)
            case SourceType.PUBLIC_WEB | SourceType.USER_UPLOADED_PRIVATE | SourceType.INTERNAL_PRIVATE:
                sources.append(_placeholder_source(task.task_id, index, item))
            case unreachable:
                assert_never(unreachable)

    message = "Searched public source connectors."
    if errors:
        message = "Searched public source connectors with recoverable errors."

    review = review_source_quality(sources, plan.query_expansion)

    return {
        "sources": list(review.accepted),
        "rejected_sources": list(review.rejected),
        "current_step": "search_sources",
        "intermediate": {
            "source_count": len(review.accepted),
            "raw_source_count": len(sources),
            "rejected_source_count": len(review.rejected),
            "source_quality_status": review.status.value,
            "connector_counts": connector_counts,
            "source_error_count": len(errors),
        },
        "errors": errors,
        "node_logs": _log(
            "search_sources",
            message,
            source_count=len(review.accepted),
            rejected_source_count=len(review.rejected),
            connector_counts=connector_counts,
            error_count=len(errors),
        ),
    }


def fetch_and_parse_sources_real(state: WorkflowState) -> dict[str, Any]:
    """Parse real URL-backed sources while allowing individual failures."""

    task = state["task"]
    web_parser = WebPageParser()
    pdf_parser = PDFParser()
    documents: list[ParsedDocument] = []
    errors: list[str] = []
    skipped = 0

    for source in state.get("sources", []):
        if source.metadata.get("mock"):
            documents.append(_mock_document_for_source(task.query, task.task_id, source))
            continue
        if source.metadata.get("placeholder") or source.url is None:
            skipped += 1
            continue

        parser = _parser_for_source(source, web_parser, pdf_parser)
        try:
            documents.append(parser.parse_url(source))
        except DocumentParseError as exc:
            errors.append(f"{source.source_id} {source.title}: {exc}")

    message = "Parsed URL-backed sources."
    if errors:
        message = "Parsed URL-backed sources with recoverable errors."

    return {
        "documents": documents,
        "current_step": "fetch_and_parse_sources",
        "intermediate": {
            "document_count": len(documents),
            "parse_error_count": len(errors),
            "skipped_source_count": skipped,
        },
        "errors": errors,
        "node_logs": _log(
            "fetch_and_parse_sources",
            message,
            document_count=len(documents),
            error_count=len(errors),
            skipped_source_count=skipped,
        ),
    }

@dataclass(frozen=True, slots=True)
class ConnectorGroups:
    literature: Sequence[SourceConnector]
    vendor: Sequence[SourceConnector]
    regulatory: Sequence[SourceConnector]


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


def _parser_for_source(source: SourceRecord, web_parser: WebPageParser, pdf_parser: PDFParser) -> WebPageParser | PDFParser:
    format_hint = source.metadata.get("document_format_hint")
    url = str(source.url or "").lower().split("?")[0]
    if format_hint == DocumentFormat.PDF or url.endswith(".pdf"):
        return pdf_parser
    return web_parser


def _mock_document_for_source(query: str, task_id: str, source: SourceRecord) -> ParsedDocument:
    return ParsedDocument(
        task_id=task_id,
        source_id=source.source_id,
        format=DocumentFormat.WEB_PAGE,
        title=source.title,
        text=(
            f"{source.title}\n"
            f"Mock parsed content for {query}. "
            "Includes product parameters, source boundaries, and evidence notes."
        ),
        summary=f"Mock summary derived from {source.title}.",
        parser_name="mock_parser",
        metadata={"mock": True},
    )
