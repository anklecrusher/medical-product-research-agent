"""Mock workflow nodes with clear seams for future real implementations."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

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
)
from medical_research_agent.parsers import DocumentParseError, PDFParser, WebPageParser
from medical_research_agent.report_templates import render_report_markdown
from medical_research_agent.schemas import (
    ArtifactFormat,
    Claim,
    ClaimStatus,
    DocumentFormat,
    EvidenceItem,
    EvidenceKind,
    EvidenceStatus,
    ParsedDocument,
    ProductSpec,
    ReportArtifact,
    ReportSection,
    SourceRecord,
    SourceType,
    TaskStatus,
)
from medical_research_agent.workflow.state import (
    NodeLog,
    ResearchIntent,
    ResearchPlan,
    SearchPlanItem,
    WorkflowState,
    dump_workflow_state,
)


def _log(node: str, message: str, **metadata: Any) -> list[NodeLog]:
    return [NodeLog(node=node, message=message, metadata=metadata)]


def _task_output_dir(state: WorkflowState) -> Path:
    task = state["task"]
    if task.output_dir:
        return Path(task.output_dir)
    return get_settings().outputs_dir / task.task_id


def parse_intent(state: WorkflowState) -> dict[str, Any]:
    """Parse a one-sentence request into a workflow intent."""

    task = state["task"]
    query = task.query.strip()
    title = task.title or query[:36]
    focus_terms = [
        term
        for term in ["DBS", "SCS", "刺激", "电极", "参数", "监管", "竞品", "临床"]
        if term.lower() in query.lower()
    ]
    if not focus_terms:
        focus_terms = ["医疗产品", "参数", "证据"]

    intent = ResearchIntent(
        title=title,
        original_query=query,
        focus_terms=focus_terms,
        target_source_types=[
            SourceType.PUBLIC_LITERATURE,
            SourceType.VENDOR_PUBLIC_DOC,
            SourceType.PUBLIC_REGULATORY,
            SourceType.PUBLIC_WEB,
        ],
        language=task.language,
    )
    task.title = title
    task.status = TaskStatus.RUNNING

    return {
        "task": task,
        "intent": intent,
        "current_step": "parse_intent",
        "intermediate": {"intent": intent.model_dump(mode="json")},
        "node_logs": _log("parse_intent", "Parsed mock research intent.", focus_terms=focus_terms),
    }


def plan_research(state: WorkflowState) -> dict[str, Any]:
    """Create connector-ready search tasks from parsed intent."""

    intent = state["intent"]
    search_items = [
        SearchPlanItem(
            query=f"{intent.original_query} 论文 参数 evidence",
            source_type=SourceType.PUBLIC_LITERATURE,
            rationale="查找论文证据和参数范围。",
            limit=2,
        ),
        SearchPlanItem(
            query=f"{intent.original_query} 产品手册 规格 参数",
            source_type=SourceType.VENDOR_PUBLIC_DOC,
            rationale="查找厂商公开资料和产品规格。",
            limit=2,
        ),
        SearchPlanItem(
            query=f"{intent.original_query} FDA NMPA regulatory",
            source_type=SourceType.PUBLIC_REGULATORY,
            rationale="补充监管和注册资料线索。",
            limit=1,
        ),
    ]
    plan = ResearchPlan(
        objective=f"围绕“{intent.original_query}”形成可追溯的医疗产品调研草稿。",
        search_items=search_items,
        expected_evidence=["产品参数", "论文证据", "厂商资料", "监管线索", "风险与未确认项"],
    )

    return {
        "research_plan": plan,
        "current_step": "plan_research",
        "intermediate": {"research_plan": plan.model_dump(mode="json")},
        "node_logs": _log("plan_research", "Created mock research plan.", search_items=len(search_items)),
    }


def search_sources(state: WorkflowState) -> dict[str, Any]:
    """Search sources with real connectors when enabled, otherwise use mock data."""

    if state.get("use_real_connectors"):
        return _search_sources_real(state)

    return _search_sources_mock(state)


def _search_sources_mock(state: WorkflowState) -> dict[str, Any]:
    """Return mock normalized sources in the same shape as real connectors."""

    task = state["task"]
    plan = state["research_plan"]
    sources: list[SourceRecord] = []
    for index, item in enumerate(plan.search_items, start=1):
        sources.append(
            SourceRecord(
                task_id=task.task_id,
                source_type=item.source_type,
                title=f"Mock source {index}: {item.source_type.value}",
                url=f"https://example.com/mock/{task.task_id}/{index}",
                publisher="Mock Connector",
                search_query=item.query,
                credibility_note="Mock source for workflow wiring only.",
                metadata={"mock": True, "rationale": item.rationale},
            )
        )

    return {
        "sources": sources,
        "current_step": "search_sources",
        "intermediate": {"source_count": len(sources)},
        "node_logs": _log("search_sources", "Produced mock source records.", source_count=len(sources)),
    }


def fetch_and_parse_sources(state: WorkflowState) -> dict[str, Any]:
    """Fetch and parse sources with real parsers when enabled."""

    if state.get("use_real_connectors"):
        return _fetch_and_parse_sources_real(state)

    return _fetch_and_parse_sources_mock(state)


def _fetch_and_parse_sources_mock(state: WorkflowState) -> dict[str, Any]:
    """Convert mock sources into parsed documents without network access."""

    task = state["task"]
    documents = [
        ParsedDocument(
            task_id=task.task_id,
            source_id=source.source_id,
            format=DocumentFormat.WEB_PAGE,
            title=source.title,
            text=(
                f"{source.title}\n"
                f"Mock parsed content for {task.query}. "
                "Includes product parameters, source boundaries, and evidence notes."
            ),
            summary=f"Mock summary derived from {source.title}.",
            language=task.language,
            parser_name="mock_parser",
            metadata={"mock": True},
        )
        for source in state.get("sources", [])
    ]

    return {
        "documents": documents,
        "current_step": "fetch_and_parse_sources",
        "intermediate": {"document_count": len(documents)},
        "node_logs": _log(
            "fetch_and_parse_sources",
            "Parsed mock documents from source records.",
            document_count=len(documents),
        ),
    }


def _search_sources_real(state: WorkflowState) -> dict[str, Any]:
    """Run public literature connectors and preserve workflow progress on failures."""

    task = state["task"]
    plan = state["research_plan"]
    settings = get_settings()
    sources: list[SourceRecord] = []
    errors: list[str] = []

    literature_connectors = [
        PubMedConnector(),
        CrossrefConnector(),
        SemanticScholarConnector(api_key=settings.semantic_scholar_api_key_value()),
    ]
    vendor_connectors = [
        DuckDuckGoHTMLSearchConnector(source_type=SourceType.VENDOR_PUBLIC_DOC),
    ]
    regulatory_connectors = [
        OpenFDA510kConnector(),
        ClinicalTrialsConnector(),
        DuckDuckGoHTMLSearchConnector(source_type=SourceType.PUBLIC_REGULATORY),
    ]
    connector_counts: dict[str, int] = {}

    for index, item in enumerate(plan.search_items, start=1):
        request = SearchRequest(query=item.query, limit=item.limit, task_id=task.task_id)
        if item.source_type == SourceType.PUBLIC_LITERATURE:
            item_sources, item_errors = _run_connectors(literature_connectors, request, item.rationale, connector_counts)
            sources.extend(item_sources)
            errors.extend(item_errors)
        elif item.source_type == SourceType.VENDOR_PUBLIC_DOC:
            item_sources, item_errors = _run_connectors(vendor_connectors, request, item.rationale, connector_counts)
            sources.extend(item_sources)
            errors.extend(item_errors)
        elif item.source_type == SourceType.PUBLIC_REGULATORY:
            item_sources, item_errors = _run_connectors(regulatory_connectors, request, item.rationale, connector_counts)
            sources.extend(item_sources)
            errors.extend(item_errors)
        else:
            sources.append(
                SourceRecord(
                    task_id=task.task_id,
                    source_type=item.source_type,
                    title=f"Pending source search {index}: {item.source_type.value}",
                    publisher="Workflow placeholder",
                    search_query=item.query,
                    credibility_note="Real connector not implemented for this source type yet.",
                    metadata={"placeholder": True, "rationale": item.rationale},
                )
            )

    message = "Searched public source connectors."
    if errors:
        message = "Searched public source connectors with recoverable errors."

    return {
        "sources": sources,
        "current_step": "search_sources",
        "intermediate": {
            "source_count": len(sources),
            "connector_counts": connector_counts,
            "source_error_count": len(errors),
        },
        "errors": errors,
        "node_logs": _log(
            "search_sources",
            message,
            source_count=len(sources),
            connector_counts=connector_counts,
            error_count=len(errors),
        ),
    }


def _run_connectors(
    connectors: list[Any],
    request: SearchRequest,
    rationale: str,
    connector_counts: dict[str, int],
) -> tuple[list[SourceRecord], list[str]]:
    sources: list[SourceRecord] = []
    errors: list[str] = []
    for connector in connectors:
        try:
            records = connector.search(request)
        except ConnectorError as exc:
            errors.append(str(exc))
            connector_counts[connector.name] = connector_counts.get(connector.name, 0)
            continue
        for record in records:
            record.metadata.setdefault("rationale", rationale)
        sources.extend(records)
        connector_counts[connector.name] = connector_counts.get(connector.name, 0) + len(records)
    return sources, errors


def _fetch_and_parse_sources_real(state: WorkflowState) -> dict[str, Any]:
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


def extract_evidence(state: WorkflowState) -> dict[str, Any]:
    """Extract mock structured evidence from parsed documents."""

    task = state["task"]
    evidence: list[EvidenceItem] = []
    product_specs: list[ProductSpec] = []

    for document in state.get("documents", []):
        source = next(item for item in state["sources"] if item.source_id == document.source_id)
        if source.source_type == SourceType.VENDOR_PUBLIC_DOC:
            item = EvidenceItem(
                task_id=task.task_id,
                source_id=source.source_id,
                document_id=document.document_id,
                kind=EvidenceKind.PRODUCT_PARAMETER,
                statement="Mock vendor document lists stimulation frequency range for comparison.",
                value="2-130",
                unit="Hz",
                product_name="Mock Medical Device",
                parameter_name="stimulation_frequency",
                quote="Mock quoted vendor parameter range.",
                location="mock section 2",
                confidence=0.72,
                metadata={"mock": True},
            )
            evidence.append(item)
            product_specs.append(
                ProductSpec(
                    task_id=task.task_id,
                    product_name="Mock Medical Device",
                    parameter_name="stimulation_frequency",
                    value="2-130",
                    unit="Hz",
                    source_ids=[source.source_id],
                    evidence_ids=[item.evidence_id],
                    notes="Mock product parameter prepared for workflow integration.",
                )
            )
        elif source.source_type == SourceType.PUBLIC_REGULATORY:
            evidence.append(
                EvidenceItem(
                    task_id=task.task_id,
                    source_id=source.source_id,
                    document_id=document.document_id,
                    kind=EvidenceKind.REGULATORY_FINDING,
                    statement="Mock regulatory source should be separated from clinical conclusions.",
                    quote="Mock regulatory classification and indication text.",
                    location="mock regulatory note",
                    confidence=0.65,
                    metadata={"mock": True},
                )
            )
        else:
            evidence.append(
                EvidenceItem(
                    task_id=task.task_id,
                    source_id=source.source_id,
                    document_id=document.document_id,
                    kind=EvidenceKind.ENGINEERING_NOTE,
                    statement="Mock evidence notes that parameter interpretation requires source context.",
                    quote="Mock engineering interpretation evidence.",
                    location="mock paragraph 1",
                    confidence=0.68,
                    metadata={"mock": True},
                )
            )

    return {
        "evidence": evidence,
        "product_specs": product_specs,
        "current_step": "extract_evidence",
        "intermediate": {"evidence_count": len(evidence), "product_spec_count": len(product_specs)},
        "node_logs": _log(
            "extract_evidence",
            "Extracted mock structured evidence.",
            evidence_count=len(evidence),
            product_spec_count=len(product_specs),
        ),
    }


def deduplicate_evidence(state: WorkflowState) -> dict[str, Any]:
    """Deduplicate evidence while preserving status for conflict checks."""

    seen: set[tuple[str | None, str, str | None]] = set()
    deduped: list[EvidenceItem] = []
    duplicates = 0

    for item in state.get("evidence", []):
        key = (item.parameter_name, item.statement, item.unit)
        if key in seen:
            duplicates += 1
            continue
        seen.add(key)
        deduped.append(item)

    return {
        "evidence": deduped,
        "current_step": "deduplicate_evidence",
        "intermediate": {"deduplicated_evidence_count": len(deduped), "duplicate_count": duplicates},
        "node_logs": _log(
            "deduplicate_evidence",
            "Deduplicated mock evidence.",
            evidence_count=len(deduped),
            duplicate_count=duplicates,
        ),
    }


def plan_report(state: WorkflowState) -> dict[str, Any]:
    """Create report sections that downstream writers can fill."""

    task = state["task"]
    evidence_ids = [item.evidence_id for item in state.get("evidence", [])]
    sections = [
        ReportSection(
            task_id=task.task_id,
            title="参数与产品资料证据",
            order=1,
            evidence_ids=evidence_ids,
            status="planned",
        ),
        ReportSection(
            task_id=task.task_id,
            title="工程解释与来源边界",
            order=2,
            evidence_ids=evidence_ids,
            status="planned",
        ),
        ReportSection(
            task_id=task.task_id,
            title="监管资料与未确认项",
            order=3,
            evidence_ids=evidence_ids,
            status="planned",
        ),
    ]

    return {
        "report_sections": sections,
        "current_step": "plan_report",
        "intermediate": {"section_count": len(sections)},
        "node_logs": _log("plan_report", "Planned mock report sections.", section_count=len(sections)),
    }


def write_report(state: WorkflowState) -> dict[str, Any]:
    """Draft report sections and claims from mock evidence."""

    task = state["task"]
    evidence = state.get("evidence", [])
    evidence_ids = [item.evidence_id for item in evidence]
    source_ids = [item.source_id for item in evidence]
    sections: list[ReportSection] = []

    for section in state.get("report_sections", []):
        if section.title.startswith("参数"):
            section.content_markdown = (
                "| 参数/主题 | Mock 结论 | 来源状态 |\n"
                "|---|---|---|\n"
                "| stimulation_frequency | 2-130 Hz 为 mock 厂商参数，用于验证参数表链路。 | vendor_public_doc |\n"
            )
        elif section.title.startswith("工程"):
            section.content_markdown = (
                "不同来源的参数需要区分论文证据、厂商资料和监管资料；"
                "当前内容均为 mock 数据，不能作为产品或临床结论。"
            )
        else:
            section.content_markdown = (
                "- mock 监管资料仅用于验证 workflow 字段流转。\n"
                "- 真实 connector 接入后应检查适应证、注册状态和资料发布日期。"
            )
        section.status = "draft"
        section.claim_ids = []
        sections.append(section)

    claims = [
        Claim(
            task_id=task.task_id,
            text="Mock vendor parameter evidence can flow into the report parameter table.",
            evidence_ids=evidence_ids[:1],
            source_ids=source_ids[:1],
        ),
        Claim(
            task_id=task.task_id,
            text="Mock workflow keeps source type boundaries visible before final writing.",
            evidence_ids=evidence_ids,
            source_ids=source_ids,
        ),
    ]
    claim_ids = [claim.claim_id for claim in claims]
    for section in sections:
        section.claim_ids = claim_ids

    return {
        "report_sections": sections,
        "claims": claims,
        "current_step": "write_report",
        "intermediate": {"claim_count": len(claims)},
        "node_logs": _log("write_report", "Drafted mock report sections and claims.", claim_count=len(claims)),
    }


def verify_claims(state: WorkflowState) -> dict[str, Any]:
    """Mark claims as supported only when linked evidence and sources exist."""

    verified: list[Claim] = []
    for claim in state.get("claims", []):
        if claim.evidence_ids and claim.source_ids:
            claim.status = ClaimStatus.SUPPORTED
            claim.verification_note = "Mock verification: claim has linked evidence and sources."
        else:
            claim.status = ClaimStatus.NEEDS_REVIEW
            claim.verification_note = "Mock verification: missing evidence or source link."
        verified.append(claim)

    for item in state.get("evidence", []):
        item.status = EvidenceStatus.VERIFIED

    return {
        "claims": verified,
        "evidence": state.get("evidence", []),
        "current_step": "verify_claims",
        "intermediate": {"verified_claim_count": len(verified)},
        "node_logs": _log("verify_claims", "Verified mock claims by evidence linkage.", claim_count=len(verified)),
    }


def render_outputs(state: WorkflowState) -> dict[str, Any]:
    """Render a mock Markdown report artifact and persist run state."""

    task = state["task"]
    output_dir = _task_output_dir(state)
    output_dir.mkdir(parents=True, exist_ok=True)

    references = []
    for source in state.get("sources", []):
        source_ref = f"{source.title}: {source.url}" if source.url else source.title
        references.append(source_ref)

    report = SimpleNamespace(
        title=task.title or "Mock 医疗产品调研报告",
        subtitle=f"任务 ID：{task.task_id}",
        core_conclusions=[
            "当前为 mock workflow 输出，用于验证从一句需求到报告 artifact 的状态流转。",
            "所有结论均带 mock 来源链路，真实内容需由后续 connector/extractor/writer 接入。",
        ],
        sections=state.get("report_sections", []),
        risks_and_gaps=[
            "mock 数据不能用于真实产品、临床或注册判断。",
            "后续需接入真实检索、解析、证据抽取和引用核查。",
        ],
        references=references,
    )
    markdown = render_report_markdown(report)

    report_path = output_dir / "report.md"
    sources_path = output_dir / "sources.json"
    documents_path = output_dir / "documents.json"
    evidence_path = output_dir / "evidence.json"
    claims_path = output_dir / "claims.json"
    state_path = output_dir / "workflow_state.json"
    log_path = output_dir / "run.log"
    report_path.write_text(markdown, encoding="utf-8")
    sources_path.write_text(
        json.dumps([item.model_dump(mode="json") for item in state.get("sources", [])], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    documents_path.write_text(
        json.dumps([item.model_dump(mode="json") for item in state.get("documents", [])], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    evidence_path.write_text(
        json.dumps([item.model_dump(mode="json") for item in state.get("evidence", [])], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    claims_path.write_text(
        json.dumps([item.model_dump(mode="json") for item in state.get("claims", [])], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    task.status = TaskStatus.COMPLETED
    artifact = ReportArtifact(
        task_id=task.task_id,
        format=ArtifactFormat.MARKDOWN,
        path=str(report_path),
        metadata={"mock": True, "renderer": "render_report_markdown"},
    )
    render_log = _log("render_outputs", "Rendered mock Markdown report artifact.", path=str(report_path))
    final_state = {
        **state,
        "task": task,
        "report_markdown": markdown,
        "artifacts": [artifact],
        "current_step": "render_outputs",
        "node_logs": state.get("node_logs", []) + render_log,
    }
    state_path.write_text(dump_workflow_state(final_state), encoding="utf-8")
    log_path.write_text(
        "\n".join(f"{entry.created_at.isoformat()} [{entry.node}] {entry.message}" for entry in final_state["node_logs"]),
        encoding="utf-8",
    )

    return {
        "task": task,
        "report_markdown": markdown,
        "artifacts": [artifact],
        "current_step": "render_outputs",
        "intermediate": {
            "artifact_count": 1,
            "report_path": str(report_path),
            "sources_path": str(sources_path),
            "documents_path": str(documents_path),
            "evidence_path": str(evidence_path),
            "claims_path": str(claims_path),
            "state_path": str(state_path),
            "log_path": str(log_path),
        },
        "node_logs": render_log,
    }
