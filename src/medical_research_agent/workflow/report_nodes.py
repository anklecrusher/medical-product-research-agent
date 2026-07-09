"""Report-related workflow nodes for planning, writing, verification, and rendering."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from medical_research_agent.claim_verifier import ClaimVerificationInputs, verify_claim_links
from medical_research_agent.config import get_settings
from medical_research_agent.report_content import build_render_report
from medical_research_agent.report_models import ReportInputs, evidence_gap_report_items, has_unresolved_evidence_gaps
from medical_research_agent.report_outline import plan_report_outline
from medical_research_agent.report_templates import render_report_markdown
from medical_research_agent.report_writer import draft_evidence_report
from medical_research_agent.renderers import render_markdown_pdf
from medical_research_agent.schemas import ArtifactFormat, ReportArtifact
from medical_research_agent.workflow.state import NodeLog, WorkflowState, dump_workflow_state
from medical_research_agent.workflow.status_policy import WorkflowCompletionSignals, decide_workflow_status


def _log(node: str, message: str, **metadata: Any) -> list[NodeLog]:
    return [NodeLog(node=node, message=message, metadata=metadata)]


def _task_output_dir(state: WorkflowState) -> Path:
    task = state["task"]
    if task.output_dir:
        return Path(task.output_dir)
    return get_settings().outputs_dir / task.task_id


def _report_inputs(state: WorkflowState) -> ReportInputs:
    return ReportInputs(
        task=state["task"],
        planned_sections=state.get("report_sections", []),
        sources=state.get("sources", []),
        documents=state.get("documents", []),
        evidence=state.get("evidence", []),
        product_specs=state.get("product_specs", []),
        evidence_gaps=evidence_gap_report_items(state.get("intermediate", {}).get("evidence_gaps", [])),
    )


def plan_report(state: WorkflowState) -> dict[str, Any]:
    """Create report sections that downstream writers can fill."""

    sections = plan_report_outline(_report_inputs(state))

    return {
        "report_sections": sections,
        "current_step": "plan_report",
        "intermediate": {"section_count": len(sections)},
        "node_logs": _log("plan_report", "Planned report sections.", section_count=len(sections)),
    }


def write_report(state: WorkflowState) -> dict[str, Any]:
    """Draft report sections and claims from extracted evidence."""

    draft = draft_evidence_report(_report_inputs(state))
    return {
        "report_sections": draft.sections,
        "claims": draft.claims,
        "current_step": "write_report",
        "intermediate": {"claim_count": len(draft.claims)},
        "node_logs": _log("write_report", "Drafted evidence-driven report sections and claims.", claim_count=len(draft.claims)),
    }


def verify_claims(state: WorkflowState) -> dict[str, Any]:
    """Mark claims as supported only when linked evidence and sources exist."""

    result = verify_claim_links(
        ClaimVerificationInputs(
            claims=state.get("claims", []),
            evidence=state.get("evidence", []),
            sources=state.get("sources", []),
            sections=state.get("report_sections", []),
        )
    )

    return {
        "claims": result.claims,
        "evidence": state.get("evidence", []),
        "report_sections": result.sections,
        "current_step": "verify_claims",
        "intermediate": {
            "verified_claim_count": len(result.claims),
            "supported_claim_count": result.supported_count,
            "partial_claim_count": result.partial_count,
            "needs_review_claim_count": result.review_count,
        },
        "node_logs": _log(
            "verify_claims",
            "Verified claims against existing evidence/source IDs.",
            claim_count=len(result.claims),
            supported_count=result.supported_count,
            partial_count=result.partial_count,
            needs_review_count=result.review_count,
        ),
    }


def render_outputs(state: WorkflowState) -> dict[str, Any]:
    """Render durable Markdown, JSON, state/log, and PDF artifacts."""

    task = state["task"]
    output_dir = _task_output_dir(state)
    output_dir.mkdir(parents=True, exist_ok=True)

    report_inputs = _report_inputs(state)
    report = build_render_report(report_inputs)
    markdown = render_report_markdown(report)

    report_path = output_dir / "report.md"
    pdf_path = output_dir / "report.pdf"
    sources_path = output_dir / "sources.json"
    rejected_sources_path = output_dir / "rejected_sources.json"
    documents_path = output_dir / "documents.json"
    evidence_path = output_dir / "evidence.json"
    claims_path = output_dir / "claims.json"
    state_path = output_dir / "workflow_state.json"
    log_path = output_dir / "run.log"
    render_intermediate = {
        "artifact_count": 2,
        "report_path": str(report_path),
        "pdf_path": str(pdf_path),
        "sources_path": str(sources_path),
        "rejected_sources_path": str(rejected_sources_path),
        "documents_path": str(documents_path),
        "evidence_path": str(evidence_path),
        "claims_path": str(claims_path),
        "state_path": str(state_path),
        "log_path": str(log_path),
    }

    report_path.write_text(markdown, encoding="utf-8")
    sources_path.write_text(
        json.dumps([item.model_dump(mode="json") for item in state.get("sources", [])], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    rejected_sources_path.write_text(
        json.dumps(
            [item.model_dump(mode="json") for item in state.get("rejected_sources", [])],
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    documents_path.write_text(
        json.dumps([item.model_dump(mode="json") for item in state.get("documents", [])], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    evidence_path.write_text(
        json.dumps([item.model_dump(mode="json") for item in state.get("evidence", [])], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    claims_path.write_text(
        json.dumps([item.model_dump(mode="json") for item in state.get("claims", [])], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    pdf_result = render_markdown_pdf(markdown, pdf_path, title=task.title)
    completed_status = decide_workflow_status(
        WorkflowCompletionSignals(
            accepted_source_count=len(state.get("sources", [])),
            rejected_source_count=len(state.get("rejected_sources", [])),
            evidence_count=len(state.get("evidence", [])),
            claim_count=len(state.get("claims", [])),
            source_quality_status=state.get("intermediate", {}).get("source_quality_status"),
            has_unresolved_evidence_gaps=has_unresolved_evidence_gaps(report_inputs),
            errors=tuple(state.get("errors", [])),
        )
    )
    completed_task = task.model_copy(update={"status": completed_status})
    markdown_artifact = ReportArtifact(
        task_id=task.task_id,
        format=ArtifactFormat.MARKDOWN,
        path=str(report_path),
        metadata={"renderer": "render_report_markdown"},
    )
    pdf_artifact = ReportArtifact(
        task_id=task.task_id,
        format=ArtifactFormat.PDF,
        path=str(pdf_result.path),
        metadata={
            "renderer": "reportlab_canvas",
            "font_name": pdf_result.font_name,
            "warnings": pdf_result.warnings,
        },
    )
    artifacts = [markdown_artifact, pdf_artifact]
    render_log = _log(
        "render_outputs",
        "Rendered Markdown and PDF report artifacts.",
        report_path=str(report_path),
        pdf_path=str(pdf_result.path),
        rejected_sources_path=str(rejected_sources_path),
        pdf_font=pdf_result.font_name,
        pdf_warnings=pdf_result.warnings,
    )
    final_state = {
        **state,
        "task": completed_task,
        "report_markdown": markdown,
        "artifacts": artifacts,
        "intermediate": {**state.get("intermediate", {}), **render_intermediate},
        "current_step": "render_outputs",
        "node_logs": state.get("node_logs", []) + render_log,
    }
    state_path.write_text(dump_workflow_state(final_state), encoding="utf-8")
    log_path.write_text(
        "\n".join(f"{entry.created_at.isoformat()} [{entry.node}] {entry.message}" for entry in final_state["node_logs"]),
        encoding="utf-8",
    )

    return {
        "task": completed_task,
        "report_markdown": markdown,
        "artifacts": artifacts,
        "current_step": "render_outputs",
        "intermediate": render_intermediate,
        "node_logs": render_log,
    }
