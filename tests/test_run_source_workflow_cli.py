from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from medical_research_agent.schemas import TaskStatus
from medical_research_agent.workflow.graph import create_initial_state


def test_cli_prints_status_quality_summary_and_report_path(monkeypatch, capsys, tmp_path) -> None:
    # Given: a completed workflow snapshot with explicit quality diagnostics and artifact paths.
    module = _load_cli_module()
    state = create_initial_state("Research public product evidence", output_dir=tmp_path)
    state["task"] = state["task"].model_copy(update={"status": TaskStatus.NEEDS_REVIEW})
    state["intermediate"] = {
        "report_path": str(tmp_path / "report.md"),
        "pdf_path": str(tmp_path / "report.pdf"),
        "report_quality": {
            "passed": False,
            "score": 0.67,
            "reasons": ["free citations: insufficient eligible links"],
        },
    }
    monkeypatch.setattr(module, "run_source_workflow", lambda query, output_dir: state)
    monkeypatch.setattr(sys, "argv", ["run_source_workflow.py", "Research public product evidence"])

    # When: the CLI presents the workflow result.
    module.main()

    # Then: status, quality diagnostics, and report location are visible without inspecting JSON manually.
    output = capsys.readouterr().out
    assert "Status: needs_review" in output
    assert "Report quality: passed=False score=0.67" in output
    assert "free citations: insufficient eligible links" in output
    assert f"Report: {tmp_path / 'report.md'}" in output


def _load_cli_module():
    path = Path(__file__).resolve().parents[1] / "examples" / "run_source_workflow.py"
    spec = importlib.util.spec_from_file_location("run_source_workflow_cli", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
