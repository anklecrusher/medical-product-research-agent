from __future__ import annotations

import json

from medical_research_agent.llm.client import LLMClient
from medical_research_agent.llm.models import LLMRequest, LLMResponse
from medical_research_agent.llm_report_writer import draft_llm_report
from medical_research_agent.report_models import ReportInputs, citation_render_projection
from medical_research_agent.schemas import (
    EvidenceItem,
    EvidenceKind,
    ProductSpec,
    ReportSection,
    ResearchTask,
    SourceRecord,
    SourceType,
)
from medical_research_agent.source_contracts import AccessCheck, CitationEligibility, FreeAccessStatus


class CaptureReportLLM(LLMClient):
    provider = "test"

    def __init__(self, content: str) -> None:
        self.content = content
        self.requests: list[LLMRequest] = []

    def complete(self, request: LLMRequest) -> LLMResponse:
        self.requests.append(request)
        return LLMResponse(content=self.content, model="test", provider=self.provider)


def _source(source_id: str, source_type: SourceType, url: str, access_url: str | None = None) -> SourceRecord:
    access = AccessCheck(
        source_id=source_id,
        url=access_url or url,
        status=FreeAccessStatus.FREE_LANDING_PAGE,
    )
    return SourceRecord(
        source_id=source_id,
        source_type=source_type,
        title=f"Title for {source_id}",
        url=url,
        metadata={
            "access_check": access.model_dump(mode="json"),
            "citation_eligibility": CitationEligibility.from_access_check(access).model_dump(mode="json"),
        },
    )


def test_citation_projection_rejects_private_and_access_url_mismatched_sources() -> None:
    private = _source("src_private", SourceType.INTERNAL_PRIVATE, "https://private.example/notes")
    mismatched = _source(
        "src_mismatched",
        SourceType.PUBLIC_WEB,
        "https://public.example/source",
        "https://public.example/other",
    )

    projection = citation_render_projection([private, mismatched])

    assert projection.references == []
    assert {item.source_id: item.reason for item in projection.audit_items} == {
        "src_private": "private_source_not_allowed",
        "src_mismatched": "access_check_url_mismatch",
    }


def test_report_llm_request_excludes_private_and_access_url_mismatched_sources() -> None:
    task = ResearchTask(task_id="task_projection_security", query="Public product research")
    public = _source("src_public", SourceType.PUBLIC_WEB, "https://public.example/verified")
    private = _source("src_private", SourceType.USER_UPLOADED_PRIVATE, "https://private.example/notes")
    mismatched = _source(
        "src_mismatched",
        SourceType.PUBLIC_WEB,
        "https://public.example/source",
        "https://public.example/other",
    )
    evidence = EvidenceItem(
        evidence_id="ev_public",
        task_id=task.task_id,
        source_id=public.source_id,
        kind=EvidenceKind.ENGINEERING_NOTE,
        statement="Public parameter evidence.",
        quote="Public parameter evidence.",
        location="fixture",
    )
    section = ReportSection(section_id="summary", task_id=task.task_id, title="Summary", status="planned")
    content = json.dumps(
        {
            "sections": [
                {
                    "section_id": section.section_id,
                    "content_markdown": "Public evidence summary.",
                    "evidence_ids": [evidence.evidence_id],
                    "source_ids": [public.source_id],
                    "claim_indices": [0],
                }
            ],
            "claims": [
                {
                    "text": "Public evidence supports the summary.",
                    "evidence_ids": [evidence.evidence_id],
                    "source_ids": [public.source_id],
                    "needs_review": False,
                }
            ],
            "rationale": "fixture",
        }
    )
    client = CaptureReportLLM(content)

    result = draft_llm_report(
        ReportInputs(
            task=task,
            planned_sections=[section],
            sources=[public, private, mismatched],
            documents=[],
            evidence=[evidence],
            product_specs=[],
        ),
        llm_client=client,
    )

    assert result.external_llm_used is True
    payload = client.requests[0].messages[1].content
    assert "src_private" not in payload
    assert "src_mismatched" not in payload
    assert "https://private.example/notes" not in payload
    assert "https://public.example/other" not in payload


def test_report_llm_request_excludes_ungrounded_product_specs() -> None:
    # Given: public evidence plus specs with empty, cross-source, and private grounding links.
    task = ResearchTask(task_id="task_product_spec_security", query="Public product research")
    public_a = _source("src_public_a", SourceType.PUBLIC_WEB, "https://public.example/a")
    public_b = _source("src_public_b", SourceType.PUBLIC_WEB, "https://public.example/b")
    private = _source("src_private", SourceType.INTERNAL_PRIVATE, "https://private.example/notes")
    evidence_a = EvidenceItem(
        evidence_id="ev_public_a",
        task_id=task.task_id,
        source_id=public_a.source_id,
        kind=EvidenceKind.PRODUCT_PARAMETER,
        statement="Public A evidence.",
    )
    evidence_b = evidence_a.model_copy(
        update={"evidence_id": "ev_public_b", "source_id": public_b.source_id, "statement": "Public B evidence."}
    )
    private_evidence = evidence_a.model_copy(
        update={"evidence_id": "ev_private", "source_id": private.source_id, "statement": "PRIVATE_EVIDENCE_SECRET"}
    )
    section = ReportSection(section_id="summary", task_id=task.task_id, title="Summary", status="planned")
    specs = [
        ProductSpec(product_name="EMPTY_SOURCE_SECRET", parameter_name="frequency", value="1", source_ids=[], evidence_ids=[evidence_a.evidence_id]),
        ProductSpec(product_name="EMPTY_EVIDENCE_SECRET", parameter_name="frequency", value="2", source_ids=[public_a.source_id], evidence_ids=[]),
        ProductSpec(product_name="CROSS_SOURCE_SECRET", parameter_name="frequency", value="3", source_ids=[public_a.source_id], evidence_ids=[evidence_b.evidence_id]),
        ProductSpec(product_name="PRIVATE_SOURCE_SECRET", parameter_name="frequency", value="4", source_ids=[public_a.source_id, private.source_id], evidence_ids=[evidence_a.evidence_id]),
        ProductSpec(product_name="PRIVATE_EVIDENCE_SECRET", parameter_name="frequency", value="5", source_ids=[public_a.source_id], evidence_ids=[private_evidence.evidence_id]),
        ProductSpec(product_name="PUBLIC_SAFE_SPEC", parameter_name="frequency", value="130", source_ids=[public_a.source_id], evidence_ids=[evidence_a.evidence_id]),
    ]
    response = json.dumps(
        {
            "sections": [{"section_id": "summary", "content_markdown": "Public summary.", "evidence_ids": [evidence_a.evidence_id], "source_ids": [public_a.source_id], "claim_indices": [0]}],
            "claims": [{"text": "Public claim.", "evidence_ids": [evidence_a.evidence_id], "source_ids": [public_a.source_id], "needs_review": False}],
        }
    )
    client = CaptureReportLLM(response)

    # When: report input is projected across the external LLM boundary.
    draft_llm_report(
        ReportInputs(
            task=task,
            planned_sections=[section],
            sources=[public_a, public_b, private],
            documents=[],
            evidence=[evidence_a, evidence_b, private_evidence],
            product_specs=specs,
        ),
        llm_client=client,
    )

    # Then: only the fully public spec whose evidence belongs to its declared source is serialized.
    payload = client.requests[0].messages[1].content
    assert "PUBLIC_SAFE_SPEC" in payload
    assert all(secret not in payload for secret in (
        "EMPTY_SOURCE_SECRET",
        "EMPTY_EVIDENCE_SECRET",
        "CROSS_SOURCE_SECRET",
        "PRIVATE_SOURCE_SECRET",
        "PRIVATE_EVIDENCE_SECRET",
    ))
