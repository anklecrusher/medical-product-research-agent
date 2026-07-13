from __future__ import annotations

import json

from medical_research_agent.config import AppSettings
from medical_research_agent.llm.client import LLMClient
from medical_research_agent.llm.models import LLMRequest, LLMResponse
from medical_research_agent.schemas import DocumentFormat, ParsedDocument, SourceRecord, SourceType
from medical_research_agent.source_contracts import AccessCheck, CitationEligibility, FreeAccessStatus
from medical_research_agent.workflow import evidence_nodes, nodes
from medical_research_agent.workflow.graph import create_initial_state


class StaticEvidenceLLM(LLMClient):
    provider = "openai_compatible"

    def __init__(self, content: str) -> None:
        self.content = content
        self.calls: list[LLMRequest] = []

    def complete(self, request: LLMRequest) -> LLMResponse:
        self.calls.append(request)
        return LLMResponse(content=self.content, model="workflow-evidence-test", provider=self.provider)


def test_mock_provider_keeps_deterministic_extraction_without_llm_call(monkeypatch) -> None:
    state = _state_with_public_source("Frequency 130 Hz is listed in the public manual.")
    monkeypatch.setattr(evidence_nodes, "get_settings", lambda: AppSettings(llm_provider="mock"))
    monkeypatch.setattr(evidence_nodes, "get_llm_client", lambda settings: _fail_client_creation())

    result = nodes.extract_evidence(state)

    assert result["evidence"]
    assert result["intermediate"]["llm_evidence_used"] is False
    assert result["intermediate"]["llm_evidence_errors"] == []


def test_openai_provider_merges_source_bound_llm_evidence_and_claims(monkeypatch) -> None:
    state = _state_with_public_source("Public manual text without a deterministic numeric parameter.")
    source = state["sources"][0]
    document = state["documents"][0]
    client = StaticEvidenceLLM(
        json.dumps(
            {
                "evidence": [
                    {
                        "source_id": source.source_id,
                        "document_id": document.document_id,
                        "kind": "engineering_note",
                        "statement": "The manual describes a clinician programming workflow.",
                        "quote": "clinician programming workflow",
                        "location": "paragraph 1",
                        "confidence": 0.8,
                        "facet": "programmer_ui",
                    }
                ],
                "product_specs": [],
                "claims": [
                    {
                        "source_id": source.source_id,
                        "evidence_indices": [0],
                        "text": "The public manual describes a clinician programming workflow.",
                    }
                ],
                "rationale": "fixture",
            }
        )
    )
    _configure_openai(monkeypatch, client)

    result = nodes.extract_evidence(state)

    assert len(client.calls) == 1
    assert any(item.metadata.get("extractor") == "llm_structured" for item in result["evidence"])
    assert result["claims"][0].source_ids == [source.source_id]
    assert result["intermediate"]["llm_evidence_used"] is True


def test_llm_failure_preserves_deterministic_evidence_and_records_review(monkeypatch) -> None:
    state = _state_with_public_source("Frequency 130 Hz is listed in the public manual.")
    client = StaticEvidenceLLM("not json")
    _configure_openai(monkeypatch, client)

    result = nodes.extract_evidence(state)

    assert result["evidence"]
    assert result["intermediate"]["deterministic_evidence_count"] > 0
    assert result["intermediate"]["llm_evidence_needs_review"] is True
    assert result["errors"] == ["llm_evidence:llm_output_invalid"]


def test_private_only_documents_never_reach_external_llm(monkeypatch) -> None:
    state = create_initial_state("Use private uploaded product notes")
    source = SourceRecord(
        source_id="src_private_workflow",
        task_id=state["task"].task_id,
        source_type=SourceType.USER_UPLOADED_PRIVATE,
        title="Private product notes",
        local_path="uploads/private.md",
    )
    state["sources"] = [source]
    state["documents"] = [
        ParsedDocument(
            document_id="doc_private_workflow",
            task_id=state["task"].task_id,
            source_id=source.source_id,
            format=DocumentFormat.TEXT,
            text="Private stimulation frequency 130 Hz.",
        )
    ]
    client = StaticEvidenceLLM("should not be used")
    _configure_openai(monkeypatch, client)

    result = nodes.extract_evidence(state)

    assert client.calls == []
    assert result["evidence"]
    assert result["intermediate"]["llm_evidence_skipped_private_source_ids"] == [source.source_id]
    assert any("private_sources_skipped" in error for error in result["errors"])


def _state_with_public_source(text: str):
    state = create_initial_state("Research a public medical product manual")
    source = SourceRecord(
        source_id="src_public_workflow",
        task_id=state["task"].task_id,
        source_type=SourceType.VENDOR_PUBLIC_DOC,
        title="Public programmer manual",
        url="https://example.test/manual",
    )
    access = AccessCheck(
        source_id=source.source_id,
        url=str(source.url),
        status=FreeAccessStatus.FREE_LANDING_PAGE,
    )
    source = source.model_copy(
        update={
            "metadata": {
                "access_check": access.model_dump(mode="json"),
                "citation_eligibility": CitationEligibility.from_access_check(access).model_dump(mode="json"),
            }
        }
    )
    state["sources"] = [source]
    state["documents"] = [
        ParsedDocument(
            document_id="doc_public_workflow",
            task_id=state["task"].task_id,
            source_id=source.source_id,
            format=DocumentFormat.TEXT,
            title=source.title,
            text=text,
        )
    ]
    return state


def _configure_openai(monkeypatch, client: LLMClient) -> None:
    monkeypatch.setattr(
        evidence_nodes,
        "get_settings",
        lambda: AppSettings(llm_provider="openai_compatible"),
    )
    monkeypatch.setattr(evidence_nodes, "get_llm_client", lambda settings: client)


def _fail_client_creation():
    raise AssertionError("mock provider must not create an LLM evidence client")
