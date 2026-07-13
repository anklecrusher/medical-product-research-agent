"""Source parsing helpers for public connector workflow nodes."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from medical_research_agent.parsers import DocumentParseError, PDFParser, WebPageParser
from medical_research_agent.resource_context import managed_resource
from medical_research_agent.schemas import DocumentFormat, ParsedDocument, SourceRecord
from medical_research_agent.workflow.state import NodeLog, WorkflowState


def fetch_and_parse_sources_real(
    state: WorkflowState,
    *,
    web_parser_factory: Callable[[], WebPageParser] = WebPageParser,
    pdf_parser_factory: Callable[[], PDFParser] = PDFParser,
) -> dict[str, Any]:
    """Parse accepted URL-backed sources while allowing individual failures."""

    task = state["task"]
    documents: list[ParsedDocument] = []
    errors: list[str] = []
    skipped = 0

    with managed_resource(web_parser_factory()) as web_parser, managed_resource(pdf_parser_factory()) as pdf_parser:
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
        "node_logs": [
            NodeLog(
                node="fetch_and_parse_sources",
                message=message,
                metadata={
                    "document_count": len(documents),
                    "error_count": len(errors),
                    "skipped_source_count": skipped,
                },
            )
        ],
    }


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
