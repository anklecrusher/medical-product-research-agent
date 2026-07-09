"""Workflow completion status policy."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from medical_research_agent.schemas import TaskStatus

NEEDS_MORE_SOURCES_STATUS: Final = "needs_more_sources"
FATAL_ERROR_MARKERS: Final = ("fatal", "exception")


@dataclass(frozen=True, slots=True)
class WorkflowCompletionSignals:
    accepted_source_count: int
    rejected_source_count: int
    evidence_count: int
    claim_count: int
    source_quality_status: str | None
    has_unresolved_evidence_gaps: bool
    errors: tuple[str, ...] = ()


def decide_workflow_status(signals: WorkflowCompletionSignals) -> TaskStatus:
    has_evidence = signals.evidence_count > 0
    has_fatal_error = any(
        marker in error.lower()
        for error in signals.errors
        for marker in FATAL_ERROR_MARKERS
    )
    needs_more_sources = signals.source_quality_status == NEEDS_MORE_SOURCES_STATUS

    if has_fatal_error and not has_evidence:
        return TaskStatus.FAILED
    if signals.accepted_source_count == 0 and not has_evidence:
        return TaskStatus.NEEDS_MORE_SOURCES
    if needs_more_sources and not has_evidence:
        return TaskStatus.NEEDS_MORE_SOURCES
    if needs_more_sources and has_evidence:
        return TaskStatus.NEEDS_REVIEW
    if signals.has_unresolved_evidence_gaps:
        return TaskStatus.NEEDS_REVIEW
    if signals.accepted_source_count > 0 and not has_evidence:
        return TaskStatus.NEEDS_REVIEW
    return TaskStatus.COMPLETED
