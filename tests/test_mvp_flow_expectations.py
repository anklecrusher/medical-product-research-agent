from __future__ import annotations

import json
from pathlib import Path

from pytest import MonkeyPatch

from medical_research_agent.llm.client import LLMClient, MockLLMClient, OpenAICompatibleLLMClient
from medical_research_agent.llm.models import LLMRequest, LLMResponse
from medical_research_agent.schemas import (
    ArtifactFormat,
    ClaimStatus,
    DocumentFormat,
    EvidenceKind,
    ParsedDocument,
    SourceRecord,
    SourceType,
    TaskStatus,
)
from medical_research_agent.workflow import nodes
from medical_research_agent.workflow.graph import build_workflow_graph, create_initial_state
from medical_research_agent.workflow.state import NodeLog, WorkflowState


EXPECTED_SOURCE_IDS = {
    "src_literature",
    "src_vendor",
    "src_regulatory",
    "src_public_web",
    "src_private_upload",
}


def _fixture_sources(task_id: str) -> list[SourceRecord]:
    return [
        SourceRecord(
            source_id="src_literature",
            task_id=task_id,
            source_type=SourceType.PUBLIC_LITERATURE,
            title="Fixture DBS clinical literature",
            url="https://example.test/literature/dbs-outcomes",
            publisher="Fixture Journal",
            metadata={"fixture": "mvp_red"},
        ),
        SourceRecord(
            source_id="src_vendor",
            task_id=task_id,
            source_type=SourceType.VENDOR_PUBLIC_DOC,
            title="Fixture NeuroStim product manual",
            url="https://example.test/vendor/neurostim-manual.pdf",
            publisher="Fixture Medical",
            metadata={"fixture": "mvp_red", "document_format_hint": DocumentFormat.PDF},
        ),
        SourceRecord(
            source_id="src_regulatory",
            task_id=task_id,
            source_type=SourceType.PUBLIC_REGULATORY,
            title="Fixture FDA 510(k) summary",
            url="https://example.test/regulatory/k123456",
            publisher="FDA",
            metadata={"fixture": "mvp_red"},
        ),
        SourceRecord(
            source_id="src_public_web",
            task_id=task_id,
            source_type=SourceType.PUBLIC_WEB,
            title="Fixture public product comparison page",
            url="https://example.test/market/dbs-compare",
            publisher="Fixture Market Notes",
            metadata={"fixture": "mvp_red"},
        ),
        SourceRecord(
            source_id="src_private_upload",
            task_id=task_id,
            source_type=SourceType.USER_UPLOADED_PRIVATE,
            title="Fixture local uploaded bench note",
            local_path="uploads/fixture-local-only.md",
            publisher="Local upload",
            credibility_note="Local-only private fixture; must not require external LLM calls.",
            metadata={"fixture": "mvp_red", "privacy": "local_only"},
        ),
    ]


def _fixture_documents(task_id: str) -> list[ParsedDocument]:
    return [
        ParsedDocument(
            document_id="doc_literature",
            task_id=task_id,
            source_id="src_literature",
            format=DocumentFormat.WEB_PAGE,
            title="Fixture DBS clinical literature",
            text=(
                "A clinical follow-up study reported DBS stimulation at 130 Hz and 60 us pulse width. "
                "The paper describes tremor outcome improvement but warns that one study should not be treated "
                "as industry consensus without additional source corroboration."
            ),
            parser_name="fixture_parser",
            metadata={"fixture": "mvp_red"},
        ),
        ParsedDocument(
            document_id="doc_vendor",
            task_id=task_id,
            source_id="src_vendor",
            format=DocumentFormat.PDF,
            title="Fixture NeuroStim product manual",
            text=(
                "Fixture NeuroStim manual: stimulation frequency 2-130 Hz, pulse width 60-450 us, "
                "amplitude 0.1-10.5 mA, and lead impedance operating note 500 ohm to 1500 ohm. "
                "These are product parameters from a vendor public document, not clinical conclusions."
            ),
            parser_name="fixture_pdf_parser",
            metadata={"fixture": "mvp_red"},
        ),
        ParsedDocument(
            document_id="doc_regulatory",
            task_id=task_id,
            source_id="src_regulatory",
            format=DocumentFormat.WEB_PAGE,
            title="Fixture FDA 510(k) summary",
            text=(
                "FDA 510(k) summary K123456 lists the device as substantially equivalent for neurological "
                "stimulation indications. The regulatory source confirms clearance context but does not prove "
                "clinical superiority or long-term product performance."
            ),
            parser_name="fixture_parser",
            metadata={"fixture": "mvp_red"},
        ),
        ParsedDocument(
            document_id="doc_public_web",
            task_id=task_id,
            source_id="src_public_web",
            format=DocumentFormat.WEB_PAGE,
            title="Fixture public product comparison page",
            text=(
                "A public comparison page states that closed-loop sensing modes can use 1.5 mA test pulses "
                "and electrode spacing examples around 1.27 mm for bench comparison. Marketing notes require "
                "review before being promoted to engineering requirements."
            ),
            parser_name="fixture_parser",
            metadata={"fixture": "mvp_red"},
        ),
        ParsedDocument(
            document_id="doc_private_upload",
            task_id=task_id,
            source_id="src_private_upload",
            format=DocumentFormat.MARKDOWN,
            title="Fixture local uploaded bench note",
            text=(
                "Private uploaded bench note for local processing only: prototype electrode spacing is 1.5 mm, "
                "measured impedance was 300 Ω, and pulse width observations mention 90 μs. This fixture must "
                "preserve local-only privacy metadata and must not require an external LLM request."
            ),
            parser_name="fixture_local_parser",
            metadata={
                "fixture": "mvp_red",
                "privacy": "local_only",
                "source_type": SourceType.USER_UPLOADED_PRIVATE,
            },
        ),
    ]


def _install_fixture_nodes(monkeypatch: MonkeyPatch) -> None:
    def fixture_search_sources(state: WorkflowState) -> dict[str, list[SourceRecord] | str | list[NodeLog]]:
        task = state["task"]
        return {
            "sources": _fixture_sources(task.task_id),
            "current_step": "search_sources",
            "node_logs": [NodeLog(node="search_sources", message="Loaded deterministic MVP fixture sources.")],
        }

    def fixture_fetch_and_parse_sources(
        state: WorkflowState,
    ) -> dict[str, list[ParsedDocument] | str | list[NodeLog]]:
        task = state["task"]
        return {
            "documents": _fixture_documents(task.task_id),
            "current_step": "fetch_and_parse_sources",
            "node_logs": [NodeLog(node="fetch_and_parse_sources", message="Loaded deterministic MVP fixture documents.")],
        }

    monkeypatch.setattr(nodes, "search_sources", fixture_search_sources)
    monkeypatch.setattr(nodes, "fetch_and_parse_sources", fixture_fetch_and_parse_sources)


def _install_llm_traps(monkeypatch: MonkeyPatch) -> None:
    def fail_complete(self: LLMClient, request: LLMRequest) -> LLMResponse:
        raise AssertionError(f"Fixture MVP flow must not require LLM client {self.provider}: {request.source_types}")

    monkeypatch.setattr(MockLLMClient, "complete", fail_complete)
    monkeypatch.setattr(OpenAICompatibleLLMClient, "complete", fail_complete)


def _run_fixture_workflow(monkeypatch: MonkeyPatch, output_dir: Path) -> WorkflowState:
    _install_fixture_nodes(monkeypatch)
    _install_llm_traps(monkeypatch)
    app = build_workflow_graph()
    state = create_initial_state(
        "Fixture MVP evidence/report/PDF flow for DBS product research",
        output_dir=output_dir,
    )
    state["use_real_connectors"] = True
    return app.invoke(state)


def test_fixture_flow_extracts_source_traced_evidence_and_product_specs_without_external_llm(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    # Given: five deterministic in-memory source/document fixtures, including a private upload.
    state = _run_fixture_workflow(monkeypatch, tmp_path)

    # When: the current workflow back half extracts evidence and product specs.
    evidence = state["evidence"]
    product_specs = state["product_specs"]
    evidence_source_ids = {item.source_id for item in evidence}
    spec_keys = {(item.product_name, item.parameter_name, str(item.value), item.unit) for item in product_specs}

    # Then: every fixture source is traced by non-mock evidence and unit-bearing sources create specs.
    assert {source.source_id for source in state["sources"]} == EXPECTED_SOURCE_IDS
    assert EXPECTED_SOURCE_IDS <= evidence_source_ids
    assert all(item.evidence_id and item.source_id in EXPECTED_SOURCE_IDS for item in evidence)
    assert all(item.document_id is not None for item in evidence)
    assert all(item.metadata.get("mock") is not True for item in evidence)
    assert any(item.kind == EvidenceKind.CLINICAL_FINDING and item.source_id == "src_literature" for item in evidence)
    assert any(item.kind == EvidenceKind.REGULATORY_FINDING and item.source_id == "src_regulatory" for item in evidence)
    assert any(item.kind == EvidenceKind.PRODUCT_PARAMETER and item.source_id == "src_vendor" for item in evidence)
    assert any(item.kind == EvidenceKind.PRODUCT_PARAMETER and item.source_id == "src_public_web" for item in evidence)
    assert any(item.kind == EvidenceKind.PRODUCT_PARAMETER and item.source_id == "src_private_upload" for item in evidence)
    assert ("Fixture NeuroStim", "stimulation_frequency", "2-130", "Hz") in spec_keys
    assert any(item.source_ids and item.evidence_ids for item in product_specs)


def test_fixture_flow_writes_evidence_linked_report_claims(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    # Given: the deterministic fixture flow has reached render_outputs without network or LLM calls.
    state = _run_fixture_workflow(monkeypatch, tmp_path)

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
    state = _run_fixture_workflow(monkeypatch, tmp_path)

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
    assert workflow_state["task"]["status"] == TaskStatus.COMPLETED
    assert workflow_state["current_step"] == "render_outputs"
    assert {artifact["format"] for artifact in workflow_state["artifacts"]} >= {
        ArtifactFormat.MARKDOWN,
        ArtifactFormat.PDF,
    }
