from medical_research_agent.schemas import ArtifactFormat, TaskStatus
from medical_research_agent.workflow import run_mock_workflow


def test_mock_workflow_runs_to_markdown_artifact(tmp_path) -> None:
    state = run_mock_workflow(
        "调研 SCS 刺激参数的产品范围、论文证据和监管资料",
        output_dir=tmp_path,
    )

    assert state["task"].status == TaskStatus.COMPLETED
    assert state["current_step"] == "render_outputs"
    assert len(state["sources"]) == 3
    assert len(state["documents"]) == 3
    assert len(state["evidence"]) == 3
    assert len(state["claims"]) == 2
    assert len(state["node_logs"]) == 10

    artifact = state["artifacts"][0]
    assert artifact.format == ArtifactFormat.MARKDOWN
    assert (tmp_path / "report.md").exists()
    assert (tmp_path / "sources.json").exists()
    assert (tmp_path / "documents.json").exists()
    assert (tmp_path / "evidence.json").exists()
    assert (tmp_path / "claims.json").exists()
    assert (tmp_path / "workflow_state.json").exists()
    assert (tmp_path / "run.log").exists()
    assert "Mock 医疗产品调研报告" in state["report_markdown"] or "调研 SCS" in state["report_markdown"]
    assert {"intent", "research_plan", "source_count", "report_path"}.issubset(state["intermediate"])


def test_mock_workflow_keeps_node_order(tmp_path) -> None:
    state = run_mock_workflow("调研 DBS 脑电采集电极要求", output_dir=tmp_path)

    assert [entry.node for entry in state["node_logs"]] == [
        "parse_intent",
        "plan_research",
        "search_sources",
        "fetch_and_parse_sources",
        "extract_evidence",
        "deduplicate_evidence",
        "plan_report",
        "write_report",
        "verify_claims",
        "render_outputs",
    ]
