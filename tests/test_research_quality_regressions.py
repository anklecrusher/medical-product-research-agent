from __future__ import annotations

import json
from pathlib import Path

from medical_research_agent.connectors import ConnectorError
from medical_research_agent.research_planning import ResearchFacetKind
from medical_research_agent.schemas import ClaimStatus, DocumentFormat, ParsedDocument, SourceRecord, SourceType, TaskStatus
from medical_research_agent.workflow import follow_up, source_nodes
from medical_research_agent.workflow.graph import run_source_workflow


NOISY_CROSSREF_TITLES = {
    "常微分方程的理论基础与数学逻辑研究",
    "Influence of key parameters on the interaction of the laser induced plasma hot core and shock wave",
}


class EmptyConnector:
    name = "empty"

    def __init__(self, *args, **kwargs) -> None:
        pass

    def search(self, request):
        return []


class NoisyCrossrefConnector:
    name = "crossref"

    def search(self, request):
        return [
            SourceRecord(
                task_id=request.task_id,
                source_type=SourceType.PUBLIC_LITERATURE,
                title=title,
                url=f"https://example.test/crossref/{index}",
                publisher="Crossref",
                search_query=request.query,
                metadata={"connector": self.name, "snippet": title},
            )
            for index, title in enumerate(NOISY_CROSSREF_TITLES, start=1)
        ]


class LiteratureOnlyConnector:
    name = "pubmed"

    def search(self, request):
        return [
            SourceRecord(
                task_id=request.task_id,
                source_type=SourceType.PUBLIC_LITERATURE,
                title="DBS programming clinical literature",
                url="https://example.test/literature/dbs-programming",
                publisher="Fixture Journal",
                search_query=request.query,
                metadata={"connector": self.name, "snippet": "clinical DBS programming follow-up evidence"},
            )
        ]


class VendorManualConnector:
    name = "duckduckgo_html"

    def __init__(self, source_type=SourceType.PUBLIC_WEB) -> None:
        self.source_type = source_type

    def search(self, request):
        title = "DBS clinician programmer manual UI and 8-contact lead programming guide"
        return [
            SourceRecord(
                task_id=request.task_id,
                source_type=self.source_type,
                title=title,
                url="https://example.test/vendor/dbs-programmer-manual.pdf",
                publisher="Fixture Vendor",
                search_query=request.query,
                metadata={
                    "connector": self.name,
                    "snippet": "clinician programmer manual interface UI 8-contact lead stimulation frequency",
                },
            )
        ]


class VendorSpecConnector:
    name = "duckduckgo_html"

    def __init__(self, source_type=SourceType.PUBLIC_WEB) -> None:
        self.source_type = source_type

    def search(self, request):
        return [
            SourceRecord(
                task_id=request.task_id,
                source_type=self.source_type,
                title="NeuroStim DBS competitor product manual and specification sheet",
                url="https://example.test/vendor/neurostim-spec.pdf",
                publisher="Fixture Vendor",
                search_query=request.query,
                metadata={
                    "connector": self.name,
                    "snippet": "vendor manual DBS electrode contacts stimulation frequency pulse width amplitude",
                },
            )
        ]


class RegulatoryFailingConnector:
    name = "openfda_510k"

    def search(self, request):
        raise ConnectorError(self.name, "blocked regulatory fixture")


class RegulatoryEmptyConnector:
    name = "clinicaltrials_gov"

    def search(self, request):
        return []


class QualityWebParser:
    name = "quality_web"

    def parse_url(self, source):
        return _document_for_source(source, self.name, DocumentFormat.WEB_PAGE)


class QualityPDFParser:
    name = "quality_pdf"

    def parse_url(self, source):
        return _document_for_source(source, self.name, DocumentFormat.PDF)


def _document_for_source(source: SourceRecord, parser_name: str, document_format: DocumentFormat) -> ParsedDocument:
    title = source.title.casefold()
    if "competitor" in title or "specification" in title:
        text = (
            "NeuroStim DBS competitor product manual. Stimulation frequency 2-130 Hz; "
            "pulse width 60-450 us; amplitude 0.1-10.5 mA; lead spacing 1.27 mm. "
            "These values are vendor_public_doc product parameters, not clinical claims."
        )
    elif "manual" in title or "programmer" in title:
        text = (
            "DBS clinician programmer manual UI. The programming interface shows interleaving stimulation "
            "for an 8-contact lead, with screen controls for frequency 130 Hz and pulse width 60 μs. "
            "This is manual/UI evidence from a vendor document."
        )
    else:
        text = (
            "Clinical literature discusses DBS programming follow-up and outcomes, but it does not include "
            "clinician programmer screenshots, UI workflow, vendor manual tables, or product interface claims."
        )
    return ParsedDocument(
        task_id=source.task_id,
        source_id=source.source_id,
        format=document_format,
        title=source.title,
        text=text,
        parser_name=parser_name,
    )


def _patch_common_parsers(monkeypatch) -> None:
    monkeypatch.setattr(source_nodes, "WebPageParser", QualityWebParser)
    monkeypatch.setattr(source_nodes, "PDFParser", QualityPDFParser)
    monkeypatch.setattr(follow_up, "WebPageParser", QualityWebParser)
    monkeypatch.setattr(follow_up, "PDFParser", QualityPDFParser)


def _patch_connectors(monkeypatch, *, pubmed, crossref, vendor, openfda=EmptyConnector, clinical=EmptyConnector) -> None:
    monkeypatch.setattr(source_nodes, "PubMedConnector", pubmed)
    monkeypatch.setattr(source_nodes, "CrossrefConnector", crossref)
    monkeypatch.setattr(source_nodes, "SemanticScholarConnector", EmptyConnector)
    monkeypatch.setattr(source_nodes, "DuckDuckGoHTMLSearchConnector", vendor)
    monkeypatch.setattr(source_nodes, "OpenFDA510kConnector", openfda)
    monkeypatch.setattr(source_nodes, "ClinicalTrialsConnector", clinical)
    monkeypatch.setattr(follow_up, "DuckDuckGoHTMLSearchConnector", vendor)


def _titles(items: list[SourceRecord]) -> set[str]:
    return {item.title for item in items}


def test_ui_manual_happy_path_accepts_manual_rejects_noisy_literature_and_reports_ui_section(
    monkeypatch,
    tmp_path: Path,
) -> None:
    # Given: a UI/manual topic where vendor manual evidence is relevant and Crossref returns noise.
    _patch_connectors(monkeypatch, pubmed=EmptyConnector, crossref=NoisyCrossrefConnector, vendor=VendorManualConnector)
    _patch_common_parsers(monkeypatch)

    # When: the no-network source workflow runs end to end.
    state = run_source_workflow("调研交叉刺激与8触点刺激的相关程控逻辑和ui界面", output_dir=tmp_path)
    report_text = (tmp_path / "report.md").read_text(encoding="utf-8")

    # Then: noisy Crossref sources are rejected and only accepted manual sources feed evidence/report wording.
    assert NOISY_CROSSREF_TITLES.isdisjoint(_titles(state["sources"]))
    assert NOISY_CROSSREF_TITLES <= _titles(state["rejected_sources"])
    assert NOISY_CROSSREF_TITLES.isdisjoint({item.statement for item in state["evidence"]})
    assert {ResearchFacetKind.PROGRAMMER_UI.value, ResearchFacetKind.VENDOR_MANUAL.value} <= {
        source.metadata["facet"] for source in state["sources"]
    }
    assert any(claim.status == ClaimStatus.SUPPORTED for claim in state["claims"])
    assert "程控 UI / 界面资料" in report_text
    assert "论文证据不在本节充当产品界面证据" in report_text
    assert "常微分方程" not in report_text
    assert "laser induced plasma" not in report_text


def test_ui_manual_missing_path_keeps_literature_only_as_needs_review_gap(monkeypatch, tmp_path: Path) -> None:
    # Given: literature exists, but vendor/manual follow-up returns no UI/manual sources.
    _patch_connectors(monkeypatch, pubmed=LiteratureOnlyConnector, crossref=EmptyConnector, vendor=EmptyConnector)
    _patch_common_parsers(monkeypatch)

    # When: the workflow completes with unresolved UI/manual gaps.
    state = run_source_workflow("调研 DBS 程控界面和论文证据", output_dir=tmp_path)
    report_text = (tmp_path / "report.md").read_text(encoding="utf-8")
    missing_facets = {
        gap["facet"]
        for gap in state["intermediate"]["evidence_gaps"]
        if gap["status"] == "needs_more_sources"
    }

    # Then: literature is not promoted into UI/manual evidence and gap wording remains explicit.
    assert {ResearchFacetKind.PROGRAMMER_UI.value, ResearchFacetKind.VENDOR_MANUAL.value} <= missing_facets
    assert state["task"].status == TaskStatus.NEEDS_REVIEW
    assert all(source.source_type == SourceType.PUBLIC_LITERATURE for source in state["sources"])
    assert all(claim.status != ClaimStatus.SUPPORTED or claim.evidence_ids for claim in state["claims"])
    assert "程控/UI资料缺口与需补充资料" in report_text
    assert "Missing required facet programmer_ui" in report_text
    assert "needs_more_sources" in report_text
    assert "程控/UI证据已覆盖" not in report_text


def test_regulatory_weak_path_records_diagnostic_status_and_artifacts(monkeypatch, tmp_path: Path) -> None:
    # Given: regulatory connectors fail or return no accepted evidence.
    _patch_connectors(
        monkeypatch,
        pubmed=EmptyConnector,
        crossref=EmptyConnector,
        vendor=EmptyConnector,
        openfda=RegulatoryFailingConnector,
        clinical=RegulatoryEmptyConnector,
    )
    _patch_common_parsers(monkeypatch)

    # When: a regulatory topic is run without live web.
    state = run_source_workflow("调研 DBS FDA 510(k) 注册监管资料", output_dir=tmp_path)
    workflow_state = json.loads((tmp_path / "workflow_state.json").read_text(encoding="utf-8"))
    report_text = (tmp_path / "report.md").read_text(encoding="utf-8")

    # Then: outputs exist but status is diagnostic, not completed success.
    assert state["task"].status in {TaskStatus.NEEDS_MORE_SOURCES, TaskStatus.FAILED}
    assert workflow_state["task"]["status"] in {TaskStatus.NEEDS_MORE_SOURCES, TaskStatus.FAILED}
    assert state["sources"] == []
    assert state["evidence"] == []
    assert any("openfda_510k" in error for error in state["errors"])
    assert (tmp_path / "sources.json").exists()
    assert (tmp_path / "rejected_sources.json").exists()
    assert (tmp_path / "evidence.json").exists()
    assert "证据不足" in report_text
    assert "needs_review" in report_text


def test_vendor_competitor_spec_path_produces_vendor_sections_and_supported_claims(monkeypatch, tmp_path: Path) -> None:
    # Given: vendor product spec fixtures supply unit-bearing competitor parameters.
    _patch_connectors(monkeypatch, pubmed=EmptyConnector, crossref=EmptyConnector, vendor=VendorSpecConnector)
    _patch_common_parsers(monkeypatch)

    # When: the source workflow drafts the report.
    state = run_source_workflow("调研 DBS 厂商 手册 竞品 参数 触点", output_dir=tmp_path)
    report_text = (tmp_path / "report.md").read_text(encoding="utf-8")

    # Then: vendor/spec evidence drives parameter and competitor sections with supported claims.
    assert any(source.source_type == SourceType.VENDOR_PUBLIC_DOC for source in state["sources"])
    assert any(spec.parameter_name == "stimulation_frequency" and spec.unit == "Hz" for spec in state["product_specs"])
    assert any(spec.parameter_name == "pulse_width" and spec.unit in {"us", "μs"} for spec in state["product_specs"])
    assert any(claim.status == ClaimStatus.SUPPORTED and claim.evidence_ids for claim in state["claims"])
    assert "参数与产品资料证据" in report_text
    assert "竞品/厂商资料对照" in report_text
    assert "vendor_public_doc" in report_text
    assert "2-130 Hz" in report_text


def test_no_network_integration_flow_writes_quality_artifacts_and_blocks_noisy_crossref(
    monkeypatch,
    tmp_path: Path,
) -> None:
    # Given: all connectors/parsers are monkeypatched, including a noisy Crossref failure candidate.
    _patch_connectors(monkeypatch, pubmed=EmptyConnector, crossref=NoisyCrossrefConnector, vendor=VendorManualConnector)
    _patch_common_parsers(monkeypatch)

    # When: the CLI-equivalent workflow surface writes artifacts.
    state = run_source_workflow("调研交叉刺激与8触点刺激的相关程控逻辑和ui界面", output_dir=tmp_path)
    sources_json = json.loads((tmp_path / "sources.json").read_text(encoding="utf-8"))
    rejected_json = json.loads((tmp_path / "rejected_sources.json").read_text(encoding="utf-8"))
    evidence_json = json.loads((tmp_path / "evidence.json").read_text(encoding="utf-8"))
    workflow_state = json.loads((tmp_path / "workflow_state.json").read_text(encoding="utf-8"))
    report_text = (tmp_path / "report.md").read_text(encoding="utf-8")

    # Then: topic-level quality artifacts expose accepted/rejected counts, facets, claims, and wording.
    assert len(sources_json) >= 1
    assert len(rejected_json) >= len(NOISY_CROSSREF_TITLES)
    assert len(evidence_json) >= 1
    assert workflow_state["current_step"] == "render_outputs"
    assert workflow_state["task"]["status"] in {TaskStatus.COMPLETED, TaskStatus.NEEDS_REVIEW}
    assert {item["title"] for item in rejected_json} >= NOISY_CROSSREF_TITLES
    assert not any(item["title"] in NOISY_CROSSREF_TITLES for item in sources_json)
    assert not any(item["source_id"] in {source["source_id"] for source in rejected_json} for item in evidence_json)
    assert {ResearchFacetKind.PROGRAMMER_UI.value, ResearchFacetKind.VENDOR_MANUAL.value} <= {
        item["metadata"]["facet"] for item in sources_json
    }
    assert workflow_state["intermediate"]["rejected_sources_path"] == str(tmp_path / "rejected_sources.json")
    assert any(claim["status"] == ClaimStatus.SUPPORTED for claim in workflow_state["claims"])
    assert "程控 UI / 界面资料" in report_text
    assert "常微分方程" not in report_text
    assert "laser induced plasma" not in report_text
