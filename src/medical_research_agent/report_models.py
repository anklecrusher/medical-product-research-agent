"""Shared report-writing value objects."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import TypeAlias

from pydantic import ValidationError

from medical_research_agent.llm.privacy import PRIVATE_SOURCE_TYPES
from medical_research_agent.schemas import (
    EvidenceItem,
    ParsedDocument,
    ProductSpec,
    ReportSection,
    ResearchTask,
    SourceRecord,
    SourceType,
)
from medical_research_agent.source_contracts import AccessCheck, CitationEligibility, FreeAccessStatus


GapSnapshotValue: TypeAlias = str | list[str]


@dataclass(frozen=True, slots=True)
class EvidenceGapReportItem:
    facet: str
    status: str
    description: str
    required_source_types: tuple[str, ...]
    recommended_queries: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ReportInputs:
    task: ResearchTask
    planned_sections: list[ReportSection]
    sources: list[SourceRecord]
    documents: list[ParsedDocument]
    evidence: list[EvidenceItem]
    product_specs: list[ProductSpec]
    evidence_gaps: list[EvidenceGapReportItem] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class ReportIndexes:
    source_by_id: dict[str, SourceRecord]
    evidence_by_id: dict[str, EvidenceItem]


@dataclass(frozen=True, slots=True)
class SourceAuditItem:
    source_id: str
    title: str
    source_type: str
    access_status: str
    reason: str


@dataclass(frozen=True, slots=True)
class CitationRenderProjection:
    references: list[SourceRecord]
    audit_items: list[SourceAuditItem]


def evidence_gap_report_items(gaps: Iterable[Mapping[str, GapSnapshotValue]]) -> list[EvidenceGapReportItem]:
    """Convert persisted evidence-gap snapshots into report-facing items."""

    return [
        EvidenceGapReportItem(
            facet=_string_value(gap.get("facet")),
            status=_string_value(gap.get("status")),
            description=_string_value(gap.get("description")),
            required_source_types=_tuple_value(gap.get("required_source_types")),
            recommended_queries=_tuple_value(gap.get("recommended_queries")),
        )
        for gap in gaps
    ]


def has_unresolved_evidence_gaps(inputs: ReportInputs) -> bool:
    """Return whether bounded follow-up still left a missing evidence facet."""

    return any(gap.status == "needs_more_sources" for gap in inputs.evidence_gaps)


def citation_render_projection(sources: Iterable[SourceRecord]) -> CitationRenderProjection:
    """Project source records into final references and an auditable exclusion list."""

    references: list[SourceRecord] = []
    audit_items: list[SourceAuditItem] = []
    for source in sources:
        access_check = _access_check(source)
        citation = _citation_eligibility(source)
        reason = _citation_exclusion_reason(source, access_check, citation)
        if reason is None:
            references.append(_reference_source(source, citation))
        else:
            audit_items.append(_source_audit_item(source, access_check, reason))
    return CitationRenderProjection(references=references, audit_items=audit_items)


def rejected_source_audit_items(sources: Iterable[SourceRecord]) -> list[SourceAuditItem]:
    """Render persisted rejected or pending public sources without promoting citations."""

    audit_items: list[SourceAuditItem] = []
    for source in sources:
        access_check = _access_check(source)
        citation = _citation_eligibility(source)
        reason = _citation_exclusion_reason(source, access_check, citation)
        audit_items.append(_source_audit_item(source, access_check, reason or _review_rejection_reason(source)))
    return audit_items


def eligible_citation_access_check(source: SourceRecord) -> AccessCheck | None:
    """Return the access check only when the source passes the final citation boundary."""

    access_check = _access_check(source)
    citation = _citation_eligibility(source)
    if _citation_exclusion_reason(source, access_check, citation) is not None:
        return None
    return access_check


def _access_check(source: SourceRecord) -> AccessCheck | None:
    raw_access_check = source.metadata.get("access_check")
    if raw_access_check is None:
        return None
    try:
        return AccessCheck.model_validate(raw_access_check)
    except ValidationError:
        return None


def _citation_eligibility(source: SourceRecord) -> CitationEligibility | None:
    raw_citation = source.metadata.get("citation_eligibility")
    if raw_citation is None:
        return None
    try:
        return CitationEligibility.model_validate(raw_citation)
    except ValidationError:
        return None


def _citation_exclusion_reason(
    source: SourceRecord,
    access_check: AccessCheck | None,
    citation: CitationEligibility | None,
) -> str | None:
    if SourceType(source.source_type) in PRIVATE_SOURCE_TYPES:
        return "private_source_not_allowed"
    if access_check is None:
        return "missing_or_invalid_access_check"
    if access_check.source_id != source.source_id:
        return "access_check_source_id_mismatch"
    if access_check.url is None or source.url is None or str(access_check.url) != str(source.url):
        return "access_check_url_mismatch"
    if citation is None:
        return "missing_or_invalid_citation_eligibility"
    if citation.source_id != source.source_id:
        return "citation_eligibility_source_id_mismatch"

    derived = CitationEligibility.from_access_check(access_check)
    if not derived.eligible:
        return _access_reason(derived.reason, access_check)
    if not citation.eligible or citation.status != derived.status or citation.url != derived.url:
        return "citation_eligibility_mismatch"
    return None


def _source_audit_item(
    source: SourceRecord,
    access_check: AccessCheck | None,
    reason: str,
) -> SourceAuditItem:
    return SourceAuditItem(
        source_id=source.source_id,
        title=source.title,
        source_type=str(source.source_type),
        access_status=access_check.status.value if access_check is not None else "pending",
        reason=reason,
    )


def _review_rejection_reason(source: SourceRecord) -> str:
    llm_triage = source.metadata.get("llm_triage")
    if isinstance(llm_triage, Mapping):
        decision_reasons = {
            "rejected": "llm_triage_rejected",
            "pending_review": "llm_triage_pending_review",
        }
        decision = llm_triage.get("decision")
        if isinstance(decision, str):
            decision_reason = decision_reasons.get(decision)
            if decision_reason is not None:
                return decision_reason
    quality_review = source.metadata.get("quality_review")
    if isinstance(quality_review, Mapping) and quality_review.get("decision") == "rejected":
        return "quality_review_rejected"
    return "rejected_or_pending_source"


def _access_reason(reason: str, access_check: AccessCheck) -> str:
    if access_check.failure_reason:
        return f"{reason}; {access_check.failure_reason}"
    return reason


def _reference_source(source: SourceRecord, citation: CitationEligibility | None) -> SourceRecord:
    if citation is None or citation.url is None:
        return source
    title = source.title
    if citation.status == FreeAccessStatus.ABSTRACT_ACCESSIBLE:
        title = f"{title}（仅摘要证据，非全文）"
    return source.model_copy(update={"title": title, "url": str(citation.url)})


def _string_value(value: GapSnapshotValue | None) -> str:
    if isinstance(value, str):
        return value
    return ""


def _tuple_value(value: GapSnapshotValue | None) -> tuple[str, ...]:
    if isinstance(value, list):
        return tuple(item for item in value if isinstance(item, str))
    string_value = _string_value(value)
    if string_value:
        return (string_value,)
    return ()
