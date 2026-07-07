from __future__ import annotations

from pathlib import Path

from medical_research_agent.schemas import (
    Claim,
    ClaimStatus,
    EvidenceItem,
    EvidenceKind,
    ReportSection,
    SourceRecord,
    SourceType,
)
from medical_research_agent.workflow import nodes
from medical_research_agent.workflow.graph import create_initial_state


def test_report_generation_marks_insufficient_evidence_when_no_sources(tmp_path: Path) -> None:
    # Given: a workflow state with no source-backed evidence.
    state = create_initial_state("Fixture report with no usable evidence", output_dir=tmp_path)
    state.update(nodes.plan_report(state))

    # When: the report writer and Markdown renderer run.
    state.update(nodes.write_report(state))
    rendered = nodes.render_outputs(state)
    report_text = rendered["report_markdown"]

    # Then: the report explicitly marks the draft as insufficient instead of inventing evidence.
    assert "证据不足" in report_text
    assert "needs_review" in report_text
    assert all(claim.status == ClaimStatus.NEEDS_REVIEW for claim in state["claims"])
    assert "Mock" not in report_text


def test_verify_claims_marks_missing_evidence_and_source_links_as_needs_review(
    tmp_path: Path,
) -> None:
    # Given: a generated claim names evidence/source IDs that do not exist in the current state.
    state = create_initial_state("Fixture unsupported claim", output_dir=tmp_path)
    state["claims"] = [
        Claim(
            claim_id="claim_missing_links",
            task_id=state["task"].task_id,
            text="This conclusion has no current evidence link.",
            evidence_ids=["ev_missing"],
            source_ids=["src_missing"],
            status=ClaimStatus.DRAFT,
        )
    ]
    state["report_sections"] = [
        ReportSection(
            section_id="section_claim_check",
            task_id=state["task"].task_id,
            title="结论核查",
            content_markdown="核查前内容。",
            claim_ids=["claim_missing_links"],
            status="draft",
        )
    ]

    # When: claim verification and report rendering run.
    state.update(nodes.verify_claims(state))
    rendered = nodes.render_outputs(state)
    report_text = rendered["report_markdown"]

    # Then: the unsupported claim is not promoted and the report exposes its review status.
    assert state["claims"][0].status == ClaimStatus.NEEDS_REVIEW
    assert "claim_missing_links" in report_text
    assert "needs_review" in report_text
    assert "缺少有效证据或来源链路" in report_text


def test_verify_claims_keeps_section_claim_ids_valid_and_marks_partial_support() -> None:
    # Given: one valid evidence/source chain and one stale evidence ID on the same claim.
    state = create_initial_state("Fixture partial claim")
    source = SourceRecord(
        source_id="src_valid",
        task_id=state["task"].task_id,
        source_type=SourceType.VENDOR_PUBLIC_DOC,
        title="Valid vendor manual",
    )
    evidence = EvidenceItem(
        evidence_id="ev_valid",
        task_id=state["task"].task_id,
        source_id=source.source_id,
        kind=EvidenceKind.PRODUCT_PARAMETER,
        statement="Valid vendor parameter evidence.",
    )
    state["sources"] = [source]
    state["evidence"] = [evidence]
    state["claims"] = [
        Claim(
            claim_id="claim_partial",
            task_id=state["task"].task_id,
            text="Partially linked claim.",
            evidence_ids=["ev_valid", "ev_stale"],
            source_ids=["src_valid"],
            status=ClaimStatus.DRAFT,
        )
    ]
    state["report_sections"] = [
        ReportSection(
            task_id=state["task"].task_id,
            title="参数与产品资料证据",
            claim_ids=["claim_partial", "claim_stale"],
            evidence_ids=["ev_valid"],
            status="draft",
        )
    ]

    # When: claim verification runs against the current state only.
    result = nodes.verify_claims(state)

    # Then: stale section references are dropped and partial evidence is not marked supported.
    assert result["claims"][0].status == ClaimStatus.PARTIALLY_SUPPORTED
    assert result["report_sections"][0].claim_ids == ["claim_partial"]
