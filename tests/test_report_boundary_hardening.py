from __future__ import annotations

from medical_research_agent.llm_report_grounding import validate_report_response
from medical_research_agent.llm_report_models import LLMReportResponse
from medical_research_agent.report_models import ReportInputs, rejected_source_audit_items
from medical_research_agent.schemas import EvidenceItem, EvidenceKind, ReportSection, ResearchTask, SourceRecord, SourceType
from medical_research_agent.source_contracts import AccessCheck, CitationEligibility, FreeAccessStatus


def test_report_grounding_rejects_source_only_sections_and_unlinked_claims() -> None:
    # Given: a factual section names a source but no evidence while attaching a separately evidenced claim.
    inputs, source, evidence = _inputs()
    parsed = LLMReportResponse.model_validate(
        {
            "sections": [
                {
                    "section_id": "core",
                    "content_markdown": "Unsupported strong conclusion.",
                    "evidence_ids": [],
                    "source_ids": [source.source_id],
                    "claim_indices": [0],
                }
            ],
            "claims": [
                {
                    "text": "A strong claim needs a direct evidence link.",
                    "evidence_ids": [evidence.evidence_id],
                    "source_ids": [source.source_id],
                    "needs_review": False,
                }
            ],
            "rationale": "boundary fixture",
        }
    )

    # When: report response grounding validates the section and claim links.
    errors = validate_report_response(parsed, inputs, {source.source_id}, [evidence])

    # Then: source-only content and its unlinked claim cannot pass as grounded prose.
    assert "section_without_evidence:core" in errors
    assert "section_claim_evidence_unlinked:core:0" in errors


def test_rejected_source_audit_tolerates_non_string_triage_decision() -> None:
    # Given: persisted rejected-source metadata contains an untrusted non-string decision value.
    _, source, _ = _inputs()
    source = source.model_copy(update={"metadata": {**source.metadata, "llm_triage": {"decision": []}}})

    # When: the audit projection evaluates the malformed triage metadata.
    audit_items = rejected_source_audit_items([source])

    # Then: rendering remains available and records a conservative audit reason.
    assert audit_items[0].source_id == source.source_id
    assert audit_items[0].reason == "rejected_or_pending_source"


def _inputs() -> tuple[ReportInputs, SourceRecord, EvidenceItem]:
    task = ResearchTask(task_id="task_report_boundary", query="DBS report grounding")
    access = AccessCheck(
        source_id="src_grounded",
        url="https://example.test/grounded",
        status=FreeAccessStatus.FREE_LANDING_PAGE,
    )
    source = SourceRecord(
        source_id=access.source_id,
        task_id=task.task_id,
        source_type=SourceType.PUBLIC_LITERATURE,
        title="Grounded source",
        url=str(access.url),
        metadata={
            "access_check": access.model_dump(mode="json"),
            "citation_eligibility": CitationEligibility.from_access_check(access).model_dump(mode="json"),
        },
    )
    evidence = EvidenceItem(
        evidence_id="ev_grounded",
        task_id=task.task_id,
        source_id=source.source_id,
        kind=EvidenceKind.CLINICAL_FINDING,
        statement="Grounded clinical finding.",
        quote="Grounded clinical finding.",
        location="fixture",
    )
    section = ReportSection(section_id="core", task_id=task.task_id, title="Core", order=1, status="planned")
    return (
        ReportInputs(
            task=task,
            planned_sections=[section],
            sources=[source],
            documents=[],
            evidence=[evidence],
            product_specs=[],
        ),
        source,
        evidence,
    )
