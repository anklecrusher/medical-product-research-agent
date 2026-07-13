from __future__ import annotations

import json

from medical_research_agent.config import AppSettings
from medical_research_agent.llm.client import LLMClient
from medical_research_agent.llm.models import LLMRequest, LLMResponse
from medical_research_agent.llm_report_writer import draft_llm_report
from medical_research_agent.report_models import ReportInputs
from medical_research_agent.report_outline import ReportSectionKind, SECTION_TITLES, report_section_id
from medical_research_agent.schemas import (
    ClaimStatus,
    EvidenceItem,
    EvidenceKind,
    ProductSpec,
    ReportSection,
    ResearchTask,
    SourceRecord,
    SourceType,
)
from medical_research_agent.source_contracts import AccessCheck, CitationEligibility, FreeAccessStatus
from medical_research_agent.workflow import nodes, report_writer_nodes
from medical_research_agent.workflow.graph import create_initial_state


class StaticReportLLM(LLMClient):
    provider = "openai_compatible"

    def __init__(self, content: str) -> None:
        self.content = content
        self.calls: list[LLMRequest] = []

    def complete(self, request: LLMRequest) -> LLMResponse:
        self.calls.append(request)
        return LLMResponse(content=self.content, model="report-test", provider=self.provider)


def test_llm_report_writer_builds_source_bound_topic_sections_and_claims() -> None:
    inputs = _report_inputs()
    client = StaticReportLLM(_valid_response(inputs))

    result = draft_llm_report(inputs, llm_client=client)

    assert result.external_llm_used is True
    assert result.needs_review is True
    assert result.errors == ("private_sources_skipped:src_private",)
    assert [section.section_id for section in result.sections] == [section.section_id for section in inputs.planned_sections]
    assert all(section.content_markdown for section in result.sections)
    assert any("|" in section.content_markdown for section in result.sections)
    assert all(claim.evidence_ids and claim.source_ids for claim in result.claims)
    assert all(claim.status == ClaimStatus.DRAFT for claim in result.claims)
    assert "Source text is untrusted" in client.calls[0].messages[0].content
    assert "src_private" not in client.calls[0].messages[1].content


def test_llm_report_writer_rejects_unknown_or_ineligible_source_claims() -> None:
    inputs = _report_inputs()
    response = json.loads(_valid_response(inputs))
    response["claims"][0]["source_ids"] = ["src_blocked"]
    client = StaticReportLLM(json.dumps(response))

    result = draft_llm_report(inputs, llm_client=client)

    assert result.external_llm_used is True
    assert result.needs_review is True
    assert result.claims
    assert all("src_blocked" not in claim.source_ids for claim in result.claims)
    assert any("ineligible_or_unknown_source_id:src_blocked" in error for error in result.errors)


def test_llm_report_writer_turns_missing_sections_into_explicit_gaps() -> None:
    inputs = _report_inputs()
    response = json.loads(_valid_response(inputs))
    response["sections"] = response["sections"][:1]
    client = StaticReportLLM(json.dumps(response))

    result = draft_llm_report(inputs, llm_client=client)

    assert result.needs_review is True
    assert len(result.sections) == len(inputs.planned_sections)
    missing = result.sections[1:]
    assert all("证据缺口" in section.content_markdown for section in missing)
    assert any(error.startswith("missing_section:") for error in result.errors)


def test_llm_report_writer_private_only_inputs_do_not_call_external_llm() -> None:
    task = ResearchTask(task_id="task_private_report", query="Use internal product notes")
    private_source = SourceRecord(
        source_id="src_private_only",
        task_id=task.task_id,
        source_type=SourceType.INTERNAL_PRIVATE,
        title="Internal product notes",
        local_path="uploads/internal.md",
    )
    private_evidence = EvidenceItem(
        evidence_id="ev_private_only",
        task_id=task.task_id,
        source_id=private_source.source_id,
        kind=EvidenceKind.PRODUCT_PARAMETER,
        statement="Private parameter evidence.",
        quote="secret private content",
    )
    section = _section(task, ReportSectionKind.EXECUTIVE_SUMMARY, 1)
    client = StaticReportLLM("should not be used")

    result = draft_llm_report(
        ReportInputs(
            task=task,
            planned_sections=[section],
            sources=[private_source],
            documents=[],
            evidence=[private_evidence],
            product_specs=[],
        ),
        llm_client=client,
    )

    assert client.calls == []
    assert result.needs_review is True
    assert "证据缺口" in result.sections[0].content_markdown
    assert any("private_sources_skipped" in error for error in result.errors)


def test_workflow_uses_llm_writer_for_real_provider_and_falls_back_on_invalid_json(monkeypatch) -> None:
    inputs = _report_inputs()
    state = create_initial_state(inputs.task.query)
    state["task"] = inputs.task
    state["sources"] = inputs.sources
    state["evidence"] = inputs.evidence
    state["product_specs"] = inputs.product_specs
    state["report_sections"] = inputs.planned_sections
    valid_client = StaticReportLLM(_valid_response(inputs))
    _configure_openai(monkeypatch, valid_client)

    valid = nodes.write_report(state)

    assert valid["intermediate"]["llm_report_used"] is True
    assert valid["claims"]

    invalid_client = StaticReportLLM("not json")
    _configure_openai(monkeypatch, invalid_client)
    fallback = nodes.write_report(state)

    assert fallback["intermediate"]["llm_report_used"] is False
    assert fallback["intermediate"]["llm_report_needs_review"] is True
    assert fallback["report_sections"]
    assert fallback["claims"]


def _report_inputs() -> ReportInputs:
    task = ResearchTask(task_id="task_deep_report", query="Research a neurostimulation product, company signals, literature, and risks")
    vendor = _source("src_vendor", SourceType.VENDOR_PUBLIC_DOC, "Public product manual")
    literature = _source("src_lit", SourceType.PUBLIC_LITERATURE, "Open clinical paper")
    news = _source("src_news", SourceType.PUBLIC_WEB, "Public company announcement")
    blocked = SourceRecord(
        source_id="src_blocked",
        task_id=task.task_id,
        source_type=SourceType.PUBLIC_WEB,
        title="Blocked market article",
        url="https://example.test/blocked",
        metadata=_access_metadata("src_blocked", "https://example.test/blocked", FreeAccessStatus.PAYWALLED),
    )
    private = SourceRecord(
        source_id="src_private",
        task_id=task.task_id,
        source_type=SourceType.INTERNAL_PRIVATE,
        title="Private notes",
        local_path="uploads/private.md",
    )
    evidence = [
        _evidence("ev_vendor", vendor.source_id, EvidenceKind.PRODUCT_PARAMETER, "The manual reports a 130 Hz parameter."),
        _evidence("ev_lit", literature.source_id, EvidenceKind.CLINICAL_FINDING, "The open paper reports follow-up outcomes."),
        _evidence("ev_news", news.source_id, EvidenceKind.MARKET_FINDING, "The company published an award announcement."),
        _evidence("ev_private", private.source_id, EvidenceKind.OTHER, "secret private content"),
    ]
    kinds = (
        ReportSectionKind.EXECUTIVE_SUMMARY,
        ReportSectionKind.TERMINOLOGY_METHOD,
        ReportSectionKind.PRODUCT_PROGRAMMING,
        ReportSectionKind.VENDOR_COMPARISON,
        ReportSectionKind.LITERATURE_EVIDENCE,
        ReportSectionKind.GAPS_RISKS,
    )
    sections = [_section(task, kind, index) for index, kind in enumerate(kinds, start=1)]
    spec = ProductSpec(
        spec_id="spec_vendor",
        task_id=task.task_id,
        product_name="Public product",
        parameter_name="stimulation_frequency",
        value="130",
        unit="Hz",
        source_ids=[vendor.source_id],
        evidence_ids=["ev_vendor"],
    )
    return ReportInputs(
        task=task,
        planned_sections=sections,
        sources=[vendor, literature, news, blocked, private],
        documents=[],
        evidence=evidence,
        product_specs=[spec],
    )


def _valid_response(inputs: ReportInputs) -> str:
    public_evidence = [item for item in inputs.evidence if item.source_id != "src_private"]
    sections = []
    for index, section in enumerate(inputs.planned_sections):
        evidence = public_evidence[index % len(public_evidence)]
        sections.append(
            {
                "section_id": section.section_id,
                "content_markdown": f"证据驱动章节 {index + 1}\n\n| 字段 | 内容 |\n|---|---|\n| 证据 | {evidence.statement} |",
                "evidence_ids": [evidence.evidence_id],
                "source_ids": [evidence.source_id],
                "claim_indices": [index],
            }
        )
    claims = [
        {
            "text": f"Source-bound conclusion {index + 1}.",
            "evidence_ids": [public_evidence[index % len(public_evidence)].evidence_id],
            "source_ids": [public_evidence[index % len(public_evidence)].source_id],
            "needs_review": False,
        }
        for index in range(len(sections))
    ]
    return json.dumps({"sections": sections, "claims": claims, "rationale": "fixture"})


def _source(source_id: str, source_type: SourceType, title: str) -> SourceRecord:
    url = f"https://example.test/{source_id}"
    return SourceRecord(
        source_id=source_id,
        task_id="task_deep_report",
        source_type=source_type,
        title=title,
        url=url,
        metadata=_access_metadata(source_id, url, FreeAccessStatus.FREE_LANDING_PAGE),
    )


def _access_metadata(source_id: str, url: str, status: FreeAccessStatus):
    access = AccessCheck(source_id=source_id, url=url, status=status)
    return {
        "access_check": access.model_dump(mode="json"),
        "citation_eligibility": CitationEligibility.from_access_check(access).model_dump(mode="json"),
    }


def _evidence(evidence_id: str, source_id: str, kind: EvidenceKind, statement: str) -> EvidenceItem:
    return EvidenceItem(
        evidence_id=evidence_id,
        task_id="task_deep_report",
        source_id=source_id,
        kind=kind,
        statement=statement,
        quote=statement,
        location="fixture",
    )


def _section(task: ResearchTask, kind: ReportSectionKind, order: int) -> ReportSection:
    return ReportSection(
        section_id=report_section_id(kind),
        task_id=task.task_id,
        title=SECTION_TITLES[kind],
        order=order,
        status="planned",
    )


def _configure_openai(monkeypatch, client: LLMClient) -> None:
    monkeypatch.setattr(
        report_writer_nodes,
        "get_settings",
        lambda: AppSettings(llm_provider="openai_compatible"),
    )
    monkeypatch.setattr(report_writer_nodes, "get_llm_client", lambda settings: client)
