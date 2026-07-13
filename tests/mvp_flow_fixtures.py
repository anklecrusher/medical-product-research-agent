from __future__ import annotations

from pathlib import Path

from pytest import MonkeyPatch

from medical_research_agent.llm.client import LLMClient, MockLLMClient, OpenAICompatibleLLMClient
from medical_research_agent.llm.models import LLMRequest, LLMResponse
from medical_research_agent.schemas import DocumentFormat, ParsedDocument, SourceRecord, SourceType
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


def run_fixture_workflow(monkeypatch: MonkeyPatch, output_dir: Path) -> WorkflowState:
    _install_fixture_nodes(monkeypatch)
    _install_llm_traps(monkeypatch)
    app = build_workflow_graph()
    state = create_initial_state(
        "Fixture MVP evidence/report/PDF flow for DBS product research",
        output_dir=output_dir,
    )
    state["use_real_connectors"] = True
    return app.invoke(state)
