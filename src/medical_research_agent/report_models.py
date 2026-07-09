"""Shared report-writing value objects."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import TypeAlias

from medical_research_agent.schemas import (
    EvidenceItem,
    ParsedDocument,
    ProductSpec,
    ReportSection,
    ResearchTask,
    SourceRecord,
)


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
