"""Claim verification by existing evidence and source links."""

from __future__ import annotations

from dataclasses import dataclass
from typing import assert_never

from medical_research_agent.schemas import Claim, ClaimStatus, EvidenceItem, ReportSection, SourceRecord


@dataclass(frozen=True, slots=True)
class ClaimVerificationInputs:
    claims: list[Claim]
    evidence: list[EvidenceItem]
    sources: list[SourceRecord]
    sections: list[ReportSection]


@dataclass(frozen=True, slots=True)
class ClaimVerificationResult:
    claims: list[Claim]
    sections: list[ReportSection]
    supported_count: int
    partial_count: int
    review_count: int


@dataclass(frozen=True, slots=True)
class ClaimLinkCheck:
    has_valid_evidence: bool
    has_valid_source: bool
    missing_evidence_ids: list[str]
    missing_source_ids: list[str]


def verify_claim_links(inputs: ClaimVerificationInputs) -> ClaimVerificationResult:
    """Verify claim support against current workflow evidence and sources."""

    evidence_ids = {item.evidence_id for item in inputs.evidence}
    source_ids = {source.source_id for source in inputs.sources}
    verified_claims = [_verify_claim(claim, evidence_ids, source_ids) for claim in inputs.claims]
    existing_claim_ids = {claim.claim_id for claim in verified_claims}
    verified_sections = _sections_with_claim_status(
        [_filter_section_claim_ids(section, existing_claim_ids) for section in inputs.sections],
        verified_claims,
    )

    return ClaimVerificationResult(
        claims=verified_claims,
        sections=verified_sections,
        supported_count=_status_count(verified_claims, ClaimStatus.SUPPORTED),
        partial_count=_status_count(verified_claims, ClaimStatus.PARTIALLY_SUPPORTED),
        review_count=_status_count(verified_claims, ClaimStatus.NEEDS_REVIEW),
    )


def _verify_claim(claim: Claim, evidence_ids: set[str], source_ids: set[str]) -> Claim:
    link_check = _check_links(claim, evidence_ids, source_ids)
    status = _claim_status(claim, link_check)
    return claim.model_copy(update={"status": status, "verification_note": _verification_note(status, link_check)})


def _check_links(claim: Claim, evidence_ids: set[str], source_ids: set[str]) -> ClaimLinkCheck:
    missing_evidence_ids = [evidence_id for evidence_id in claim.evidence_ids if evidence_id not in evidence_ids]
    missing_source_ids = [source_id for source_id in claim.source_ids if source_id not in source_ids]
    return ClaimLinkCheck(
        has_valid_evidence=any(evidence_id in evidence_ids for evidence_id in claim.evidence_ids),
        has_valid_source=any(source_id in source_ids for source_id in claim.source_ids),
        missing_evidence_ids=missing_evidence_ids,
        missing_source_ids=missing_source_ids,
    )


def _claim_status(claim: Claim, link_check: ClaimLinkCheck) -> ClaimStatus:
    current_status = ClaimStatus(claim.status)
    match current_status:
        case ClaimStatus.NEEDS_REVIEW:
            return ClaimStatus.NEEDS_REVIEW
        case ClaimStatus.CONFLICTING:
            if link_check.has_valid_evidence or link_check.has_valid_source:
                return ClaimStatus.CONFLICTING
            return ClaimStatus.NEEDS_REVIEW
        case ClaimStatus.DRAFT | ClaimStatus.SUPPORTED | ClaimStatus.PARTIALLY_SUPPORTED:
            return _link_status(link_check)
        case unreachable:
            assert_never(unreachable)


def _link_status(link_check: ClaimLinkCheck) -> ClaimStatus:
    has_missing_ids = bool(link_check.missing_evidence_ids) or bool(link_check.missing_source_ids)
    has_valid_pair = link_check.has_valid_evidence and link_check.has_valid_source
    has_any_valid_link = link_check.has_valid_evidence or link_check.has_valid_source
    if has_valid_pair and not has_missing_ids:
        return ClaimStatus.SUPPORTED
    if has_any_valid_link:
        return ClaimStatus.PARTIALLY_SUPPORTED
    return ClaimStatus.NEEDS_REVIEW


def _verification_note(status: ClaimStatus, link_check: ClaimLinkCheck) -> str:
    parts: list[str] = []
    if link_check.missing_evidence_ids:
        parts.append(f"missing evidence_ids: {', '.join(link_check.missing_evidence_ids)}")
    if link_check.missing_source_ids:
        parts.append(f"missing source_ids: {', '.join(link_check.missing_source_ids)}")
    if not link_check.has_valid_evidence:
        parts.append("no existing evidence_id link")
    if not link_check.has_valid_source:
        parts.append("no existing source_id link")
    if parts:
        return f"缺少有效证据或来源链路; {'; '.join(parts)}"

    match status:
        case ClaimStatus.SUPPORTED:
            return "Claim has existing evidence_id and source_id links."
        case ClaimStatus.PARTIALLY_SUPPORTED:
            return "Claim has partial evidence/source linkage."
        case ClaimStatus.CONFLICTING:
            return "Claim remains conflicting after link verification."
        case ClaimStatus.NEEDS_REVIEW:
            return "Claim remains needs_review after link verification."
        case ClaimStatus.DRAFT:
            return "Claim remains draft after link verification."
        case unreachable:
            assert_never(unreachable)


def _filter_section_claim_ids(section: ReportSection, existing_claim_ids: set[str]) -> ReportSection:
    claim_ids = [claim_id for claim_id in section.claim_ids if claim_id in existing_claim_ids]
    return section.model_copy(update={"claim_ids": claim_ids})


def _sections_with_claim_status(sections: list[ReportSection], claims: list[Claim]) -> list[ReportSection]:
    if not sections or not claims:
        return sections

    final_section = sections[-1]
    return [
        *sections[:-1],
        final_section.model_copy(
            update={
                "content_markdown": f"{final_section.content_markdown}\n\n### 结论核查状态\n\n{_claim_status_table(claims)}",
                "status": "reviewed",
            }
        ),
    ]


def _claim_status_table(claims: list[Claim]) -> str:
    rows = [
        "| claim_id | 状态 | 核查说明 |",
        "|---|---|---|",
    ]
    for claim in claims:
        rows.append(
            "| "
            + " | ".join(
                [
                    _cell(claim.claim_id),
                    _cell(str(claim.status)),
                    _cell(claim.verification_note or "needs_review"),
                ]
            )
            + " |"
        )
    return "\n".join(rows)


def _status_count(claims: list[Claim], status: ClaimStatus) -> int:
    return sum(1 for claim in claims if ClaimStatus(claim.status) == status)


def _cell(value: str) -> str:
    return " ".join(value.split()).replace("|", "/")
