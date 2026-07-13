from __future__ import annotations

from medical_research_agent.llm.client import LLMClient
from medical_research_agent.llm.models import LLMRequest, LLMResponse
from medical_research_agent.llm_evidence import extract_public_evidence_with_llm
from medical_research_agent.schemas import DocumentFormat, ParsedDocument, SourceRecord, SourceType


class NeverCalledLLM(LLMClient):
    provider = "test"

    def complete(self, request: LLMRequest) -> LLMResponse:
        raise AssertionError(f"private source reached external LLM: {request}")


def test_llm_evidence_skips_private_sources_without_external_llm_call() -> None:
    private_source = SourceRecord(
        source_id="src_private",
        task_id="task_private",
        source_type=SourceType.USER_UPLOADED_PRIVATE,
        title="Internal DBS notes",
        local_path="uploads/internal.md",
    )
    private_doc = ParsedDocument(
        document_id="doc_private",
        task_id=private_source.task_id,
        source_id=private_source.source_id,
        format=DocumentFormat.TEXT,
        text="Internal private parameter notes.",
    )

    result = extract_public_evidence_with_llm(
        private_source.task_id,
        [private_source],
        [private_doc],
        llm_client=NeverCalledLLM(),
    )

    assert result.evidence == []
    assert result.skipped_private_source_ids == (private_source.source_id,)
    assert result.needs_review is True
    assert result.errors == ("private_sources_skipped:src_private",)
