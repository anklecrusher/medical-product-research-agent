from __future__ import annotations

from medical_research_agent.schemas import (
    Claim,
    ClaimStatus,
    EvidenceItem,
    EvidenceKind,
    EvidenceStatus,
    ReportSection,
    SourceRecord,
    SourceType,
)
from medical_research_agent.workflow import nodes
from medical_research_agent.workflow.state import WorkflowState


def _source() -> SourceRecord:
    return SourceRecord(
        source_id="src_claim_ok",
        source_type=SourceType.VENDOR_PUBLIC_DOC,
        title="Fixture product manual",
    )


def _evidence(status: EvidenceStatus = EvidenceStatus.EXTRACTED) -> EvidenceItem:
    return EvidenceItem(
        evidence_id="ev_claim_ok",
        source_id="src_claim_ok",
        kind=EvidenceKind.PRODUCT_PARAMETER,
        statement="Fixture manual reports stimulation frequency 2-130 Hz.",
        value="2-130",
        unit="Hz",
        status=status,
    )


def test_verify_claims_supports_only_existing_evidence_and_source_links() -> None:
    # Given: one real evidence/source pair and one claim with fabricated IDs.
    valid_claim = Claim(
        claim_id="claim_valid",
        text="Frequency is linked to an existing source-backed evidence item.",
        evidence_ids=["ev_claim_ok"],
        source_ids=["src_claim_ok"],
        status=ClaimStatus.DRAFT,
    )
    bogus_claim = Claim(
        claim_id="claim_bogus",
        text="This claim names IDs that are not present in workflow state.",
        evidence_ids=["ev_missing"],
        source_ids=["src_missing"],
        status=ClaimStatus.DRAFT,
    )
    state = WorkflowState(
        sources=[_source()],
        evidence=[_evidence()],
        claims=[valid_claim, bogus_claim],
        report_sections=[],
    )

    # When: claim verification runs against the state indexes.
    result = nodes.verify_claims(state)
    claims = {claim.claim_id: claim for claim in result["claims"]}

    # Then: only the claim with existing evidence and source IDs becomes supported.
    assert claims["claim_valid"].status == ClaimStatus.SUPPORTED
    assert claims["claim_bogus"].status == ClaimStatus.NEEDS_REVIEW
    assert "missing" in (claims["claim_bogus"].verification_note or "")


def test_verify_claims_marks_mixed_valid_and_missing_links_partial() -> None:
    # Given: a claim with at least one real evidence/source link plus one missing evidence ID.
    claim = Claim(
        claim_id="claim_partial",
        text="This claim is only partially linked to the current evidence set.",
        evidence_ids=["ev_claim_ok", "ev_missing"],
        source_ids=["src_claim_ok"],
        status=ClaimStatus.DRAFT,
    )
    state = WorkflowState(
        sources=[_source()],
        evidence=[_evidence()],
        claims=[claim],
        report_sections=[],
    )

    # When: verification compares claim IDs with the current state IDs.
    result = nodes.verify_claims(state)

    # Then: mixed valid/missing linkage is not treated as fully supported.
    verified = result["claims"][0]
    assert verified.status == ClaimStatus.PARTIALLY_SUPPORTED
    assert verified.evidence_ids == ["ev_claim_ok", "ev_missing"]
    assert "missing evidence_ids" in (verified.verification_note or "")


def test_verify_claims_marks_one_sided_existing_link_partial() -> None:
    # Given: a claim with an existing evidence ID but no source ID.
    claim = Claim(
        claim_id="claim_one_sided",
        text="This claim has only one side of the evidence/source linkage.",
        evidence_ids=["ev_claim_ok"],
        source_ids=[],
        status=ClaimStatus.DRAFT,
    )
    state = WorkflowState(
        sources=[_source()],
        evidence=[_evidence()],
        claims=[claim],
        report_sections=[],
    )

    # When: verification checks the current state indexes.
    result = nodes.verify_claims(state)

    # Then: the claim is partial, not supported, because a source link is missing.
    verified = result["claims"][0]
    assert verified.status == ClaimStatus.PARTIALLY_SUPPORTED
    assert "no existing source_id link" in (verified.verification_note or "")


def test_verify_claims_marks_invalid_only_conflicting_claim_needs_review() -> None:
    # Given: a conflicting claim whose evidence/source links are all stale.
    claim = Claim(
        claim_id="claim_invalid_conflict",
        text="This conflict claim has no support links in the current workflow state.",
        evidence_ids=["ev_missing"],
        source_ids=["src_missing"],
        status=ClaimStatus.CONFLICTING,
    )
    state = WorkflowState(
        sources=[_source()],
        evidence=[_evidence()],
        claims=[claim],
        report_sections=[],
    )

    # When: verification compares the claim links with current state IDs.
    result = nodes.verify_claims(state)

    # Then: an invalid-only conflicting claim is downgraded for review.
    verified = result["claims"][0]
    assert verified.status == ClaimStatus.NEEDS_REVIEW
    assert "missing evidence_ids" in (verified.verification_note or "")
    assert "missing source_ids" in (verified.verification_note or "")


def test_verify_claims_preserves_review_claims_and_filters_section_claim_ids() -> None:
    # Given: a needs-review claim with valid links and a section containing a stale claim ID.
    claim = Claim(
        claim_id="claim_review",
        text="This claim should stay under review because its evidence needs review.",
        evidence_ids=["ev_claim_ok"],
        source_ids=["src_claim_ok"],
        status=ClaimStatus.NEEDS_REVIEW,
    )
    section = ReportSection(
        section_id="section_claims",
        title="Claims",
        claim_ids=["claim_review", "claim_deleted"],
        status="draft",
    )
    state = WorkflowState(
        sources=[_source()],
        evidence=[_evidence(EvidenceStatus.NEEDS_REVIEW)],
        claims=[claim],
        report_sections=[section],
    )

    # When: verification runs after report writing.
    result = nodes.verify_claims(state)

    # Then: review semantics survive and section claim references only existing claims.
    assert result["claims"][0].status == ClaimStatus.NEEDS_REVIEW
    assert result["report_sections"][0].claim_ids == ["claim_review"]
