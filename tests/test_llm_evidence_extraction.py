from __future__ import annotations

import json

from medical_research_agent.llm.client import LLMClient
from medical_research_agent.llm.models import LLMRequest, LLMResponse
from medical_research_agent.llm_evidence import extract_public_evidence_with_llm
from medical_research_agent.schemas import (
    ClaimStatus,
    DocumentFormat,
    EvidenceKind,
    EvidenceStatus,
    ParsedDocument,
    SourceRecord,
    SourceType,
)
from medical_research_agent.source_contracts import AccessCheck, CitationEligibility, FreeAccessStatus


class StaticEvidenceLLM(LLMClient):
    provider = "openai_compatible"

    def __init__(self, content: str) -> None:
        self.content = content
        self.calls: list[LLMRequest] = []

    def complete(self, request: LLMRequest) -> LLMResponse:
        self.calls.append(request)
        return LLMResponse(content=self.content, model="evidence-test", provider=self.provider)


def test_llm_extracts_source_bound_public_literature_vendor_and_news_evidence() -> None:
    # Given: three public free-access documents covering literature, vendor, and news/announcement shapes.
    sources = [
        _source("src_lit", SourceType.PUBLIC_LITERATURE, "DBS clinical paper", "https://example.test/lit"),
        _source("src_vendor", SourceType.VENDOR_PUBLIC_DOC, "DBS programmer manual", "https://example.test/manual.pdf"),
        _source("src_news", SourceType.PUBLIC_WEB, "Company tender announcement", "https://example.test/news"),
    ]
    documents = [
        _document("doc_lit", "src_lit", "Clinical follow-up found improved programming outcomes."),
        _document("doc_vendor", "src_vendor", "Manual lists stimulation frequency 130 Hz and pulse width 60 us."),
        _document("doc_news", "src_news", "Company announced a public procurement award for DBS programmers."),
    ]
    client = StaticEvidenceLLM(
        _payload(
            evidence=[
                _evidence("src_lit", "doc_lit", "clinical_finding", "Follow-up outcomes were reported.", "clinical follow-up", "abstract"),
                _evidence("src_vendor", "doc_vendor", "product_parameter", "Frequency is 130 Hz.", "frequency 130 Hz", "p. 4", value="130", unit="Hz", parameter_name="stimulation_frequency"),
                _evidence("src_news", "doc_news", "market_finding", "A public procurement award was announced.", "procurement award", "paragraph 2"),
            ],
            specs=[
                {
                    "source_id": "src_vendor",
                    "evidence_index": 1,
                    "product_name": "DBS programmer manual",
                    "parameter_name": "stimulation_frequency",
                    "value": "130",
                    "unit": "Hz",
                    "notes": "Source-bound LLM extraction.",
                }
            ],
            claims=[
                {
                    "source_id": "src_vendor",
                    "evidence_indices": [1],
                    "text": "The public manual reports a 130 Hz stimulation-frequency parameter.",
                }
            ],
        )
    )

    # When: schema-bound LLM extraction runs.
    result = extract_public_evidence_with_llm("task_llm_ev", sources, documents, llm_client=client)

    # Then: evidence, specs, and claims are linked to source/document IDs and citable URLs.
    assert len(client.calls) == 1
    assert {source_type.value for source_type in client.calls[0].source_types} == {
        SourceType.PUBLIC_LITERATURE.value,
        SourceType.VENDOR_PUBLIC_DOC.value,
        SourceType.PUBLIC_WEB.value,
    }
    assert [item.kind for item in result.evidence] == [
        EvidenceKind.CLINICAL_FINDING,
        EvidenceKind.PRODUCT_PARAMETER,
        EvidenceKind.MARKET_FINDING,
    ]
    assert all(item.task_id == "task_llm_ev" for item in result.evidence)
    assert all(item.metadata["source_url"].startswith("https://example.test/") for item in result.evidence)
    assert all(item.metadata["extractor"] == "llm_structured" for item in result.evidence)
    assert result.product_specs[0].source_ids == ["src_vendor"]
    assert result.product_specs[0].evidence_ids == [result.evidence[1].evidence_id]
    assert result.claims[0].source_ids == ["src_vendor"]
    assert result.claims[0].evidence_ids == [result.evidence[1].evidence_id]
    assert result.claims[0].status == ClaimStatus.DRAFT
    assert result.needs_review is False


def test_llm_evidence_rejects_malformed_json_as_needs_review() -> None:
    # Given: a public free-access document and an LLM response that is not JSON.
    source = _source("src_vendor", SourceType.VENDOR_PUBLIC_DOC, "DBS programmer manual", "https://example.test/manual.pdf")
    document = _document("doc_vendor", "src_vendor", "Manual lists stimulation frequency 130 Hz.")
    client = StaticEvidenceLLM("not json")

    # When: extraction parses the malformed response.
    result = extract_public_evidence_with_llm("task_bad_json", [source], [document], llm_client=client)

    # Then: no unsupported evidence enters the result and the run is marked for review.
    assert result.evidence == []
    assert result.product_specs == []
    assert result.claims == []
    assert result.needs_review is True
    assert result.errors == ("llm_output_invalid",)


def test_llm_evidence_rejects_output_missing_source_or_url_linkage() -> None:
    # Given: the model emits an evidence item for an unknown source.
    source = _source("src_vendor", SourceType.VENDOR_PUBLIC_DOC, "DBS programmer manual", "https://example.test/manual.pdf")
    document = _document("doc_vendor", "src_vendor", "Manual lists stimulation frequency 130 Hz.")
    client = StaticEvidenceLLM(
        _payload(evidence=[_evidence("src_missing", "doc_vendor", "product_parameter", "Unsupported claim.", "quote", "p. 1")])
    )

    # When: extraction validates source and URL linkage.
    result = extract_public_evidence_with_llm("task_missing_link", [source], [document], llm_client=client)

    # Then: the unsupported item is rejected and cannot enter evidence/spec/claim outputs.
    assert result.evidence == []
    assert result.product_specs == []
    assert result.claims == []
    assert result.needs_review is True
    assert result.errors == ("unknown_source_id:src_missing",)


def test_llm_evidence_marks_public_source_without_url_for_review_without_call() -> None:
    # Given: a public document whose source lacks the URL required for a final citation.
    source = SourceRecord(
        source_id="src_missing_url",
        task_id="task_missing_url",
        source_type=SourceType.PUBLIC_WEB,
        title="Public announcement without a retained URL",
    )
    client = StaticEvidenceLLM(_payload(evidence=[]))

    # When: LLM extraction receives the source.
    result = extract_public_evidence_with_llm("task_missing_url", [source], [_document("doc_url", source.source_id, "Text.")], llm_client=client)

    # Then: it records an audit error instead of sending unverifiable content externally.
    assert client.calls == []
    assert result.needs_review is True
    assert result.errors == ("missing_source_url:src_missing_url", "no_eligible_public_documents")


def test_llm_evidence_rejects_invalid_evidence_index() -> None:
    # Given: a product parameter points to an evidence item outside the LLM response.
    source = _source("src_vendor", SourceType.VENDOR_PUBLIC_DOC, "Product manual", "https://example.test/manual.pdf")
    client = StaticEvidenceLLM(
        _payload(
            evidence=[_evidence(source.source_id, "doc_vendor", "product_parameter", "Frequency is 130 Hz.", "130 Hz", "p. 4")],
            specs=[{"source_id": source.source_id, "evidence_index": 1, "product_name": "Product", "parameter_name": "frequency", "value": "130"}],
        )
    )

    # When: the structured response is converted to output models.
    result = extract_public_evidence_with_llm("task_invalid_index", [source], [_document("doc_vendor", source.source_id, "Frequency 130 Hz.")], llm_client=client)

    # Then: none of the partially valid response reaches ordinary outputs.
    assert result.evidence == []
    assert result.product_specs == []
    assert result.claims == []
    assert result.errors == ("invalid_evidence_index:1",)


def _source(source_id: str, source_type: SourceType, title: str, url: str) -> SourceRecord:
    source = SourceRecord(
        source_id=source_id,
        task_id="task_llm_ev",
        source_type=source_type,
        title=title,
        url=url,
    )
    access = AccessCheck(source_id=source_id, url=url, status=FreeAccessStatus.FREE_LANDING_PAGE)
    return source.model_copy(
        update={
            "metadata": {
                "access_check": access.model_dump(mode="json"),
                "citation_eligibility": CitationEligibility.from_access_check(access).model_dump(mode="json"),
            }
        }
    )


def _document(document_id: str, source_id: str, text: str) -> ParsedDocument:
    return ParsedDocument(
        document_id=document_id,
        task_id="task_llm_ev",
        source_id=source_id,
        format=DocumentFormat.TEXT,
        title=f"Document {document_id}",
        text=text,
    )


def _evidence(
    source_id: str,
    document_id: str,
    kind: str,
    statement: str,
    quote: str,
    location: str,
    *,
    value: str | None = None,
    unit: str | None = None,
    parameter_name: str | None = None,
) -> dict[str, str | float | None]:
    return {
        "source_id": source_id,
        "document_id": document_id,
        "kind": kind,
        "statement": statement,
        "value": value,
        "unit": unit,
        "product_name": "DBS programmer manual" if source_id == "src_vendor" else None,
        "parameter_name": parameter_name,
        "quote": quote,
        "location": location,
        "confidence": 0.82,
        "facet": "programmer_ui",
    }


def _payload(
    *,
    evidence: list[dict[str, str | float | None]],
    specs: list[dict[str, str | int | None]] | None = None,
    claims: list[dict[str, str | list[int]]] | None = None,
) -> str:
    return json.dumps(
        {
            "evidence": evidence,
            "product_specs": specs or [],
            "claims": claims or [],
            "rationale": "fixture extraction",
        }
    )
