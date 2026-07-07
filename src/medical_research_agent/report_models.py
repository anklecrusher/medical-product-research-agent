"""Shared report-writing value objects."""

from __future__ import annotations

from dataclasses import dataclass

from medical_research_agent.schemas import (
    EvidenceItem,
    ParsedDocument,
    ProductSpec,
    ReportSection,
    ResearchTask,
    SourceRecord,
)


@dataclass(frozen=True, slots=True)
class ReportInputs:
    task: ResearchTask
    planned_sections: list[ReportSection]
    sources: list[SourceRecord]
    documents: list[ParsedDocument]
    evidence: list[EvidenceItem]
    product_specs: list[ProductSpec]


@dataclass(frozen=True, slots=True)
class ReportIndexes:
    source_by_id: dict[str, SourceRecord]
    evidence_by_id: dict[str, EvidenceItem]
