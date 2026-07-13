from __future__ import annotations

import json

from medical_research_agent.schemas import TaskStatus
from medical_research_agent.workflow.graph import create_initial_state
from medical_research_agent.workflow.nodes import render_outputs
from medical_research_agent.workflow.status_policy import (
    WorkflowCompletionSignals,
    decide_workflow_status,
)


def _signals(
    *,
    accepted_source_count: int = 1,
    rejected_source_count: int = 0,
    evidence_count: int = 1,
    claim_count: int = 1,
    source_quality_status: str | None = "has_accepted_sources",
    has_unresolved_evidence_gaps: bool = False,
    prior_status: TaskStatus | None = None,
    report_quality_passed: bool | None = None,
    errors: tuple[str, ...] = (),
) -> WorkflowCompletionSignals:
    return WorkflowCompletionSignals(
        accepted_source_count=accepted_source_count,
        rejected_source_count=rejected_source_count,
        evidence_count=evidence_count,
        claim_count=claim_count,
        source_quality_status=source_quality_status,
        has_unresolved_evidence_gaps=has_unresolved_evidence_gaps,
        prior_status=prior_status,
        report_quality_passed=report_quality_passed,
        errors=errors,
    )


def test_policy_needs_more_sources_when_no_accepted_sources_and_no_evidence() -> None:
    # Given: the workflow has no accepted source and no extracted evidence.
    signals = _signals(accepted_source_count=0, evidence_count=0)

    # When: completion status is decided.
    status = decide_workflow_status(signals)

    # Then: the caller can distinguish under-sourced completion from success.
    assert status == TaskStatus.NEEDS_MORE_SOURCES


def test_policy_needs_more_sources_when_source_quality_needs_more_sources_without_evidence() -> None:
    # Given: source review requested more sources and extraction found no evidence.
    signals = _signals(source_quality_status="needs_more_sources", evidence_count=0)

    # When: completion status is decided.
    status = decide_workflow_status(signals)

    # Then: more source collection is the next workflow action.
    assert status == TaskStatus.NEEDS_MORE_SOURCES


def test_policy_needs_review_when_source_quality_needs_more_sources_with_evidence() -> None:
    # Given: source review is weak, but the workflow still extracted evidence.
    signals = _signals(source_quality_status="needs_more_sources", evidence_count=2)

    # When: completion status is decided.
    status = decide_workflow_status(signals)

    # Then: an operator should review the partial evidence instead of rerunning blindly.
    assert status == TaskStatus.NEEDS_REVIEW


def test_policy_needs_review_when_unresolved_gaps_exist() -> None:
    # Given: report inputs still expose unresolved evidence gaps.
    signals = _signals(has_unresolved_evidence_gaps=True)

    # When: completion status is decided.
    status = decide_workflow_status(signals)

    # Then: the final task stays reviewable.
    assert status == TaskStatus.NEEDS_REVIEW


def test_policy_needs_review_when_sources_exist_without_evidence() -> None:
    # Given: accepted sources exist, but extraction produced no evidence.
    signals = _signals(accepted_source_count=2, evidence_count=0)

    # When: completion status is decided.
    status = decide_workflow_status(signals)

    # Then: the source set should be reviewed rather than marked successful.
    assert status == TaskStatus.NEEDS_REVIEW


def test_policy_completed_when_run_has_evidence_without_review_signals() -> None:
    # Given: the workflow has accepted sources, evidence, and a passing rendered quality snapshot.
    signals = _signals(report_quality_passed=True)

    # When: completion status is decided.
    status = decide_workflow_status(signals)

    # Then: the run is complete.
    assert status == TaskStatus.COMPLETED


def test_policy_needs_review_when_report_quality_snapshot_is_missing() -> None:
    # Given: earlier workflow signals are sufficient, but rendering did not provide a quality snapshot.
    signals = _signals()

    # When: completion status is decided.
    status = decide_workflow_status(signals)

    # Then: completion remains blocked until the rendered-report gate explicitly passes.
    assert status == TaskStatus.NEEDS_REVIEW


def test_policy_needs_review_when_source_relevance_was_not_confirmed() -> None:
    # Given: evidence exists, but source triage did not confirm a relevant accepted source set.
    signals = _signals(source_quality_status=None)

    # When: completion status is decided.
    status = decide_workflow_status(signals)

    # Then: the workflow cannot claim completion without the relevance gate.
    assert status == TaskStatus.NEEDS_REVIEW


def test_policy_needs_review_when_report_quality_fails() -> None:
    # Given: source/evidence signals are otherwise sufficient, but the rendered report fails quality checks.
    signals = _signals(report_quality_passed=False)

    # When: completion status is decided.
    status = decide_workflow_status(signals)

    # Then: the task remains reviewable instead of being silently marked completed.
    assert status == TaskStatus.NEEDS_REVIEW


def test_policy_failed_when_fatal_error_exists_without_evidence() -> None:
    # Given: the workflow recorded an explicit fatal error and has no evidence.
    signals = _signals(evidence_count=0, errors=("Connector failed with exception",))

    # When: completion status is decided.
    status = decide_workflow_status(signals)

    # Then: the task is failed instead of merely under-sourced.
    assert status == TaskStatus.FAILED


def test_policy_failed_when_fatal_error_exists_with_evidence_and_passing_quality() -> None:
    # Given: usable evidence and a passing report exist, but the workflow recorded an explicit fatal connector failure.
    signals = _signals(
        report_quality_passed=True,
        errors=("fatal connector failure",),
    )

    # When: completion status is decided.
    status = decide_workflow_status(signals)

    # Then: a fatal pipeline error remains authoritative and cannot be masked by report quality.
    assert status == TaskStatus.FAILED


def test_policy_failed_when_prior_needs_more_sources_has_fatal_error() -> None:
    # Given: a source-gap status exists, but a later fatal connector error was recorded with usable evidence.
    signals = _signals(
        prior_status=TaskStatus.NEEDS_MORE_SOURCES,
        report_quality_passed=True,
        errors=("fatal connector failure",),
    )

    # When: completion status is decided.
    status = decide_workflow_status(signals)

    # Then: fatal workflow failure remains stronger than the recoverable source-gap status.
    assert status == TaskStatus.FAILED


def test_policy_needs_review_when_recoverable_parse_failure_has_sources() -> None:
    # Given: source retrieval worked, but a parser failed before evidence extraction.
    signals = _signals(
        accepted_source_count=1,
        evidence_count=0,
        errors=("src_1 DBS manual: web_page_parser: parse failed",),
    )

    # When: completion status is decided.
    status = decide_workflow_status(signals)

    # Then: recoverable parser failures remain reviewable rather than fatal.
    assert status == TaskStatus.NEEDS_REVIEW


def test_render_outputs_persists_needs_more_sources_status_when_policy_selects_it(tmp_path) -> None:
    # Given: rendering receives no accepted sources and no evidence.
    state = create_initial_state("调研不存在的医疗器械资料", output_dir=tmp_path)

    # When: outputs are rendered through the real node.
    rendered = render_outputs(state)
    workflow_state = json.loads((tmp_path / "workflow_state.json").read_text(encoding="utf-8"))

    # Then: the persisted workflow state records the policy-selected status.
    assert rendered["task"].status == TaskStatus.NEEDS_MORE_SOURCES
    assert workflow_state["task"]["status"] == TaskStatus.NEEDS_MORE_SOURCES
    assert (tmp_path / "report.md").exists()
    assert (tmp_path / "report.pdf").read_bytes().startswith(b"%PDF")
