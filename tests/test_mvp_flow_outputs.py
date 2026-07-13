from __future__ import annotations

import json
from pathlib import Path

from pytest import MonkeyPatch

from medical_research_agent.schemas import ArtifactFormat, ClaimStatus, TaskStatus
from mvp_flow_fixtures import run_fixture_workflow


def test_fixture_flow_writes_evidence_linked_report_claims(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    # Given: the deterministic fixture flow has reached render_outputs without network or LLM calls.
    state = run_fixture_workflow(monkeypatch, tmp_path)

    # When: the report, claim, and artifact outputs are inspected.
    evidence_ids = {item.evidence_id for item in state["evidence"]}
    source_ids = {source.source_id for source in state["sources"]}
    claim_ids = {claim.claim_id for claim in state["claims"]}
    markdown_path = tmp_path / "report.md"
    report_text = markdown_path.read_text(encoding="utf-8")

    # Then: output is evidence-driven and claim-linked, with stale mock wording removed.
    assert all(set(section.claim_ids) <= claim_ids for section in state["report_sections"])
    assert all(set(claim.evidence_ids) <= evidence_ids for claim in state["claims"])
    assert all(set(claim.source_ids) <= source_ids for claim in state["claims"])
    assert all(
        claim.status != ClaimStatus.SUPPORTED or (claim.evidence_ids and claim.source_ids)
        for claim in state["claims"]
    )
    assert all("Mock" not in claim.text for claim in state["claims"])
    assert "Mock" not in state["report_markdown"]
    assert "Mock" not in report_text
    assert "Mock vendor parameter" not in report_text
    assert "Mock workflow" not in report_text
    assert "Fixture NeuroStim" in report_text
    assert "2-130 Hz" in report_text
    assert "| 参数/主题 | 证据摘要 | 数值 | 来源类型 | 证据状态 | 证据ID |" in report_text
    assert "vendor_public_doc" in report_text
    assert "public_literature" in report_text
    assert "public_regulatory" in report_text
    assert "user_uploaded_private" in report_text
    assert "needs_review" in report_text


def test_fixture_flow_writes_required_artifacts_including_pdf(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    # Given: the deterministic fixture flow writes artifacts into a temp output directory.
    state = run_fixture_workflow(monkeypatch, tmp_path)

    # When: the artifact set and files are inspected.
    markdown_path = tmp_path / "report.md"
    pdf_path = tmp_path / "report.pdf"
    workflow_state_path = tmp_path / "workflow_state.json"

    # Then: every first-loop output exists and PDF is a real PDF, not a renamed placeholder.
    assert (tmp_path / "sources.json").exists()
    assert (tmp_path / "documents.json").exists()
    assert (tmp_path / "evidence.json").exists()
    assert (tmp_path / "claims.json").exists()
    assert markdown_path.exists()
    assert workflow_state_path.exists()
    assert (tmp_path / "run.log").exists()
    assert pdf_path.exists()
    assert pdf_path.read_bytes().startswith(b"%PDF")
    assert {artifact.format for artifact in state["artifacts"]} >= {ArtifactFormat.MARKDOWN, ArtifactFormat.PDF}
    workflow_state = json.loads(workflow_state_path.read_text(encoding="utf-8"))
    assert workflow_state["task"]["status"] == TaskStatus.NEEDS_REVIEW
    assert workflow_state["intermediate"]["report_quality"]["passed"] is False
    assert workflow_state["intermediate"]["report_quality"]["reasons"]
    assert workflow_state["current_step"] == "render_outputs"
    assert {artifact["format"] for artifact in workflow_state["artifacts"]} >= {
        ArtifactFormat.MARKDOWN,
        ArtifactFormat.PDF,
    }
