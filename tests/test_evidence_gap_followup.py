from __future__ import annotations

import json

from medical_research_agent.evidence_gaps import (
    detect_evidence_gaps,
    plan_follow_up_searches,
)
from medical_research_agent.parsers import DocumentParseError
from medical_research_agent.research_planning import (
    EvidenceGapStatus,
    ResearchFacetKind,
    build_query_expansion_plan,
)
from medical_research_agent.schemas import (
    DocumentFormat,
    EvidenceItem,
    EvidenceKind,
    ParsedDocument,
    SourceRecord,
    SourceType,
    TaskStatus,
)
from medical_research_agent.source_contracts import AccessCheck, FreeAccessStatus
from medical_research_agent.workflow import follow_up
from medical_research_agent.workflow import source_nodes
from medical_research_agent.workflow.graph import run_source_workflow
from medical_research_agent.workflow.query_expansion import build_search_items_from_expansion
from medical_research_agent.workflow.state import ResearchPlan


class LiteratureOnlyConnector:
    name = "pubmed"

    def search(self, request):
        return [
            SourceRecord(
                task_id=request.task_id,
                source_type=SourceType.PUBLIC_LITERATURE,
                title="DBS clinical literature evidence",
                url="https://example.com/literature",
                search_query=request.query,
                metadata={"connector": self.name},
            )
        ]


class EmptyConnector:
    name = "empty"

    def __init__(self, *args, **kwargs):
        pass

    def search(self, request):
        return []


class FollowUpVendorConnector:
    name = "duckduckgo_html"

    def __init__(self, source_type=SourceType.PUBLIC_WEB):
        self.source_type = source_type

    def search(self, request):
        if request.metadata and request.metadata.get("follow_up_round") == 1:
            return [
                SourceRecord(
                    task_id=request.task_id,
                    source_type=self.source_type,
                    title="DBS clinician programmer manual",
                    url="https://example.com/dbs-programmer-manual.pdf",
                    search_query=request.query,
                    metadata={"connector": self.name},
                )
            ]
        return []


class EmptyVendorConnector:
    name = "duckduckgo_html"

    def __init__(self, source_type=SourceType.PUBLIC_WEB):
        self.source_type = source_type

    def search(self, request):
        return []


class FakeWebPageParser:
    name = "fake_web"

    def parse_url(self, source):
        return ParsedDocument(
            task_id=source.task_id,
            source_id=source.source_id,
            format=DocumentFormat.WEB_PAGE,
            title=source.title,
            text=(
                "Clinical follow-up evidence for DBS programming workflow. "
                "The article summarizes programming practice without manual screenshots."
            ),
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
            text=(
                "DBS clinician programmer manual. Programming interface range: "
                "frequency 130 Hz and pulse width 60 μs are shown in the programmer screen."
            ),
            parser_name=self.name,
        )


class FailingPDFParser:
    name = "failing_pdf"

    def parse_url(self, source):
        raise DocumentParseError(self.name, "blocked pdf parser")


class FreeAccessVerifier:
    def verify(self, source: SourceRecord) -> AccessCheck:
        return AccessCheck(
            source_id=source.source_id,
            url=str(source.url) if source.url is not None else None,
            status=FreeAccessStatus.FREE_LANDING_PAGE,
            checked_by="test",
        )


def _plan(query: str) -> ResearchPlan:
    expansion = build_query_expansion_plan(query)
    return ResearchPlan(
        objective="test plan",
        query_expansion=expansion,
        search_items=build_search_items_from_expansion(expansion),
        expected_evidence=[],
    )


def _patch_access_verifiers(monkeypatch) -> None:
    monkeypatch.setattr(source_nodes, "SourceAccessVerifier", FreeAccessVerifier)
    monkeypatch.setattr(follow_up, "SourceAccessVerifier", FreeAccessVerifier)


def test_gap_planner_targets_missing_programmer_manual_facets() -> None:
    plan = _plan("调研 DBS 程控界面和论文证据")
    literature_source = SourceRecord(
        source_type=SourceType.PUBLIC_LITERATURE,
        title="DBS programming literature",
        metadata={"facet": ResearchFacetKind.CLINICAL_STUDY.value},
    )
    literature_evidence = EvidenceItem(
        source_id=literature_source.source_id,
        kind=EvidenceKind.CLINICAL_FINDING,
        statement="Literature evidence exists for DBS programming.",
        metadata={"facet": ResearchFacetKind.CLINICAL_STUDY.value},
    )

    gaps = detect_evidence_gaps(plan, [literature_source], [literature_evidence])
    follow_ups = plan_follow_up_searches(plan, gaps, follow_up_round=1)

    missing_facets = {gap.facet for gap in gaps if gap.status == EvidenceGapStatus.NEEDS_MORE_SOURCES}
    follow_up_facets = {item.facet for item in follow_ups}

    assert ResearchFacetKind.CLINICAL_STUDY not in missing_facets
    assert ResearchFacetKind.PROGRAMMER_UI in follow_up_facets
    assert ResearchFacetKind.VENDOR_MANUAL in follow_up_facets
    assert len(follow_ups) <= 2
    assert all("follow-up for missing" in item.rationale for item in follow_ups)
    assert all(item.metadata["gap_facet"] == item.facet for item in follow_ups)
    assert {
        SourceType.VENDOR_PUBLIC_DOC,
        SourceType.PUBLIC_WEB,
    }.issuperset({item.source_type for item in follow_ups})


def test_source_workflow_records_follow_up_when_vendor_manual_supplies_gap(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(source_nodes, "PubMedConnector", LiteratureOnlyConnector)
    monkeypatch.setattr(source_nodes, "CrossrefConnector", EmptyConnector)
    monkeypatch.setattr(source_nodes, "SemanticScholarConnector", EmptyConnector)
    monkeypatch.setattr(source_nodes, "DuckDuckGoHTMLSearchConnector", FollowUpVendorConnector)
    monkeypatch.setattr(source_nodes, "OpenFDA510kConnector", EmptyConnector)
    monkeypatch.setattr(source_nodes, "ClinicalTrialsConnector", EmptyConnector)
    monkeypatch.setattr(source_nodes, "WebPageParser", FakeWebPageParser)
    monkeypatch.setattr(source_nodes, "PDFParser", FakePDFParser)
    monkeypatch.setattr(follow_up, "DuckDuckGoHTMLSearchConnector", FollowUpVendorConnector)
    monkeypatch.setattr(follow_up, "WebPageParser", FakeWebPageParser)
    monkeypatch.setattr(follow_up, "PDFParser", FakePDFParser)
    _patch_access_verifiers(monkeypatch)

    state = run_source_workflow("调研 DBS 程控界面和论文证据", output_dir=tmp_path)

    workflow_state = json.loads((tmp_path / "workflow_state.json").read_text(encoding="utf-8"))
    follow_up_sources = [source for source in state["sources"] if source.metadata.get("follow_up_round") == 1]

    assert state["intermediate"]["follow_up_round_count"] == 1
    assert state["intermediate"]["follow_up_searches"]
    assert state["intermediate"]["evidence_gaps"]
    assert follow_up_sources
    assert all(source.metadata["gap_facet"] in {"programmer_ui", "vendor_manual"} for source in follow_up_sources)
    assert all(source.metadata.get("bounded") is True for source in follow_up_sources)
    assert workflow_state["intermediate"]["follow_up_round_count"] == 1
    assert workflow_state["intermediate"]["follow_up_searches"]
    workflow_follow_up_sources = [
        source
        for source in workflow_state["sources"]
        if source["metadata"].get("follow_up_round") == 1
    ]
    assert workflow_follow_up_sources
    assert all(source["metadata"].get("bounded") is True for source in workflow_follow_up_sources)


def test_source_workflow_keeps_missing_gap_when_follow_up_finds_nothing(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(source_nodes, "PubMedConnector", LiteratureOnlyConnector)
    monkeypatch.setattr(source_nodes, "CrossrefConnector", EmptyConnector)
    monkeypatch.setattr(source_nodes, "SemanticScholarConnector", EmptyConnector)
    monkeypatch.setattr(source_nodes, "DuckDuckGoHTMLSearchConnector", EmptyVendorConnector)
    monkeypatch.setattr(source_nodes, "OpenFDA510kConnector", EmptyConnector)
    monkeypatch.setattr(source_nodes, "ClinicalTrialsConnector", EmptyConnector)
    monkeypatch.setattr(source_nodes, "WebPageParser", FakeWebPageParser)
    monkeypatch.setattr(source_nodes, "PDFParser", FakePDFParser)
    monkeypatch.setattr(follow_up, "DuckDuckGoHTMLSearchConnector", EmptyVendorConnector)
    monkeypatch.setattr(follow_up, "WebPageParser", FakeWebPageParser)
    monkeypatch.setattr(follow_up, "PDFParser", FakePDFParser)
    _patch_access_verifiers(monkeypatch)

    state = run_source_workflow("调研 DBS 程控界面和论文证据", output_dir=tmp_path)
    report_markdown = (tmp_path / "report.md").read_text(encoding="utf-8")

    missing_gap_facets = {
        gap["facet"]
        for gap in state["intermediate"]["evidence_gaps"]
        if gap["status"] == EvidenceGapStatus.NEEDS_MORE_SOURCES.value
    }

    assert state["intermediate"]["follow_up_round_count"] == 1
    assert ResearchFacetKind.PROGRAMMER_UI.value in missing_gap_facets
    assert ResearchFacetKind.VENDOR_MANUAL.value in missing_gap_facets
    assert state["task"].status == TaskStatus.NEEDS_REVIEW
    assert "Missing required facet programmer_ui" in report_markdown
    assert "Missing required facet vendor_manual" in report_markdown
    assert "needs_more_sources" in report_markdown
    assert not any(source.metadata.get("follow_up_round") == 1 for source in state["sources"])
    assert not any(
        item.metadata.get("gap_facet") in missing_gap_facets
        for item in state["evidence"]
    )


def test_source_workflow_keeps_gap_when_follow_up_source_parse_fails(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(source_nodes, "PubMedConnector", LiteratureOnlyConnector)
    monkeypatch.setattr(source_nodes, "CrossrefConnector", EmptyConnector)
    monkeypatch.setattr(source_nodes, "SemanticScholarConnector", EmptyConnector)
    monkeypatch.setattr(source_nodes, "DuckDuckGoHTMLSearchConnector", FollowUpVendorConnector)
    monkeypatch.setattr(source_nodes, "OpenFDA510kConnector", EmptyConnector)
    monkeypatch.setattr(source_nodes, "ClinicalTrialsConnector", EmptyConnector)
    monkeypatch.setattr(source_nodes, "WebPageParser", FakeWebPageParser)
    monkeypatch.setattr(source_nodes, "PDFParser", FailingPDFParser)
    monkeypatch.setattr(follow_up, "DuckDuckGoHTMLSearchConnector", FollowUpVendorConnector)
    monkeypatch.setattr(follow_up, "WebPageParser", FakeWebPageParser)
    monkeypatch.setattr(follow_up, "PDFParser", FailingPDFParser)
    _patch_access_verifiers(monkeypatch)

    state = run_source_workflow("调研 DBS 程控界面和论文证据", output_dir=tmp_path)
    report_markdown = (tmp_path / "report.md").read_text(encoding="utf-8")

    follow_up_sources = [source for source in state["sources"] if source.metadata.get("follow_up_round") == 1]
    follow_up_source_ids = {source.source_id for source in follow_up_sources}
    missing_gap_facets = {
        gap["facet"]
        for gap in state["intermediate"]["evidence_gaps"]
        if gap["status"] == EvidenceGapStatus.NEEDS_MORE_SOURCES.value
    }

    assert follow_up_sources
    assert all(source.url and str(source.url).endswith(".pdf") for source in follow_up_sources)
    assert ResearchFacetKind.PROGRAMMER_UI.value in missing_gap_facets
    assert ResearchFacetKind.VENDOR_MANUAL.value in missing_gap_facets
    assert state["task"].status == TaskStatus.NEEDS_REVIEW
    assert "Missing required facet programmer_ui" in report_markdown
    assert "Missing required facet vendor_manual" in report_markdown
    assert "needs_more_sources" in report_markdown
    assert not any(item.source_id in follow_up_source_ids for item in state["evidence"])
    assert not any(
        item.metadata.get("gap_facet") in missing_gap_facets
        for item in state["evidence"]
    )
    assert not any(follow_up_source_ids.intersection(spec.source_ids) for spec in state["product_specs"])
