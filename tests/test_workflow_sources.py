from __future__ import annotations

from medical_research_agent.connectors import ConnectorError
from medical_research_agent.parsers import DocumentParseError
from medical_research_agent.schemas import DocumentFormat, ParsedDocument, SourceRecord, SourceType
from medical_research_agent.workflow.graph import create_initial_state, run_source_workflow
from medical_research_agent.workflow import nodes


class FakePubMedConnector:
    name = "pubmed"

    def search(self, request):
        return [
            SourceRecord(
                task_id=request.task_id,
                source_type=SourceType.PUBLIC_LITERATURE,
                title="PubMed source",
                url="https://example.com/pubmed",
                search_query=request.query,
                metadata={"connector": self.name},
            )
        ]


class FakeCrossrefConnector:
    name = "crossref"

    def search(self, request):
        raise ConnectorError(self.name, "offline")


class FakeSemanticScholarConnector:
    name = "semantic_scholar"

    def __init__(self, api_key=None):
        self.api_key = api_key

    def search(self, request):
        return [
            SourceRecord(
                task_id=request.task_id,
                source_type=SourceType.PUBLIC_LITERATURE,
                title="Semantic Scholar source",
                url="https://example.com/semantic",
                search_query=request.query,
                metadata={"connector": self.name},
            )
        ]


class FakeVendorSearchConnector:
    name = "duckduckgo_html"

    def __init__(self, source_type=SourceType.PUBLIC_WEB):
        self.source_type = source_type

    def search(self, request):
        return [
            SourceRecord(
                task_id=request.task_id,
                source_type=self.source_type,
                title=f"{self.source_type.value} web result",
                url="https://example.com/vendor-manual.pdf"
                if self.source_type == SourceType.VENDOR_PUBLIC_DOC
                else "https://example.com/fda-result",
                search_query=request.query,
                metadata={"connector": self.name},
            )
        ]


class FakeOpenFDAConnector:
    name = "openfda_510k"

    def search(self, request):
        return [
            SourceRecord(
                task_id=request.task_id,
                source_type=SourceType.PUBLIC_REGULATORY,
                title="FDA 510(k) source",
                url="https://example.com/fda-510k",
                search_query=request.query,
                metadata={"connector": self.name},
            )
        ]


class FakeClinicalTrialsConnector:
    name = "clinicaltrials_gov"

    def search(self, request):
        return [
            SourceRecord(
                task_id=request.task_id,
                source_type=SourceType.PUBLIC_REGULATORY,
                title="ClinicalTrials.gov source",
                url="https://example.com/trial",
                search_query=request.query,
                metadata={"connector": self.name},
            )
        ]


class FakeWebPageParser:
    name = "fake_web"

    def parse_url(self, source):
        if "semantic" in str(source.url):
            raise DocumentParseError(self.name, "parse failed")
        return ParsedDocument(
            task_id=source.task_id,
            source_id=source.source_id,
            format=DocumentFormat.WEB_PAGE,
            title=source.title,
            text="Parsed public web content",
            parser_name=self.name,
        )


class FakePDFParser:
    name = "fake_pdf"

    def parse_url(self, source):
        return ParsedDocument(
            task_id=source.task_id,
            source_id=source.source_id,
            format=DocumentFormat.PDF,
            title=source.title,
            text="Parsed vendor PDF content",
            parser_name=self.name,
        )


def test_source_workflow_uses_real_connectors_and_parsers(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(nodes, "PubMedConnector", FakePubMedConnector)
    monkeypatch.setattr(nodes, "CrossrefConnector", FakeCrossrefConnector)
    monkeypatch.setattr(nodes, "SemanticScholarConnector", FakeSemanticScholarConnector)
    monkeypatch.setattr(nodes, "DuckDuckGoHTMLSearchConnector", FakeVendorSearchConnector)
    monkeypatch.setattr(nodes, "OpenFDA510kConnector", FakeOpenFDAConnector)
    monkeypatch.setattr(nodes, "ClinicalTrialsConnector", FakeClinicalTrialsConnector)
    monkeypatch.setattr(nodes, "WebPageParser", FakeWebPageParser)
    monkeypatch.setattr(nodes, "PDFParser", FakePDFParser)

    state = run_source_workflow("调研 DBS 电极阻抗论文证据", output_dir=tmp_path)

    assert state["use_real_connectors"] is True
    assert state["current_step"] == "render_outputs"
    assert len(state["sources"]) == 6
    assert len(state["documents"]) == 5
    assert any("crossref: offline" in error for error in state["errors"])
    assert any("parse failed" in error for error in state["errors"])
    assert state["intermediate"]["source_error_count"] == 1
    assert state["intermediate"]["parse_error_count"] == 1
    assert state["intermediate"]["skipped_source_count"] == 0
    assert state["intermediate"]["connector_counts"]["openfda_510k"] == 1
    assert state["intermediate"]["connector_counts"]["clinicaltrials_gov"] == 1
    assert state["intermediate"]["connector_counts"]["duckduckgo_html"] == 2
    assert (tmp_path / "sources.json").exists()
    assert (tmp_path / "documents.json").exists()


def test_initial_state_defaults_to_mock_connectors() -> None:
    state = create_initial_state("调研 SCS 参数")

    assert state["use_real_connectors"] is False
