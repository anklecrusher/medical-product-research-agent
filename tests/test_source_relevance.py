from __future__ import annotations

import json

from medical_research_agent.research_planning import build_query_expansion_plan
from medical_research_agent.schemas import SourceRecord, SourceType
from medical_research_agent.source_quality import SourceQualityStatus, review_source_quality
from medical_research_agent.workflow import nodes
from medical_research_agent.workflow import source_nodes
from medical_research_agent.workflow.graph import create_initial_state


BAD_ODE_TITLE = "常微分方程的理论基础与数学逻辑研究"
BAD_LASER_TITLE = "Influence of key parameters on the interaction of the laser induced plasma hot core and shock wave"


class EmptyConnector:
    name = "empty"

    def __init__(self, *args, **kwargs):
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
                title=BAD_ODE_TITLE,
                url="https://example.com/ode",
                publisher="Crossref",
                search_query=request.query,
                metadata={"connector": self.name},
            ),
            SourceRecord(
                task_id=request.task_id,
                source_type=SourceType.PUBLIC_LITERATURE,
                title=BAD_LASER_TITLE,
                url="https://example.com/laser-plasma",
                publisher="Crossref",
                search_query=request.query,
                metadata={"connector": self.name},
            ),
        ]


class RelevantVendorConnector:
    name = "duckduckgo_html"

    def __init__(self, source_type=SourceType.PUBLIC_WEB):
        self.source_type = source_type

    def search(self, request):
        return [
            SourceRecord(
                task_id=request.task_id,
                source_type=self.source_type,
                title="Clinician programmer manual for interleaving stimulation and 8-contact lead UI",
                url="https://example.com/programmer-manual",
                publisher="Vendor manual index",
                search_query=request.query,
                metadata={"connector": self.name},
            )
        ]


def _planned_real_state(tmp_path):
    state = create_initial_state("调研交叉刺激与8触点刺激的相关程控逻辑和ui界面", output_dir=tmp_path)
    state["use_real_connectors"] = True
    state.update(nodes.parse_intent(state))
    state.update(nodes.plan_research(state))
    return state


def test_noisy_crossref_titles_are_rejected_with_reasons(monkeypatch, tmp_path) -> None:
    # Given: Crossref returns unrelated math and laser-plasma records for a neurostimulation UI topic.
    monkeypatch.setattr(source_nodes, "PubMedConnector", EmptyConnector)
    monkeypatch.setattr(source_nodes, "CrossrefConnector", NoisyCrossrefConnector)
    monkeypatch.setattr(source_nodes, "SemanticScholarConnector", EmptyConnector)
    monkeypatch.setattr(source_nodes, "DuckDuckGoHTMLSearchConnector", RelevantVendorConnector)
    monkeypatch.setattr(source_nodes, "OpenFDA510kConnector", EmptyConnector)
    monkeypatch.setattr(source_nodes, "ClinicalTrialsConnector", EmptyConnector)
    state = _planned_real_state(tmp_path)

    # When: source search applies the relevance gate.
    result = nodes.search_sources(state)

    # Then: noisy Crossref records are excluded from accepted sources and kept with audit reasons.
    accepted_titles = {source.title for source in result["sources"]}
    rejected_sources = result["rejected_sources"]
    rejected_titles = {source.title for source in rejected_sources}

    assert BAD_ODE_TITLE not in accepted_titles
    assert BAD_LASER_TITLE not in accepted_titles
    assert BAD_ODE_TITLE in rejected_titles
    assert BAD_LASER_TITLE in rejected_titles
    assert any("quality_review" in source.metadata for source in rejected_sources)
    assert all(source.metadata["quality_review"]["reasons"] for source in rejected_sources)
    assert any("math" in " ".join(source.metadata["quality_review"]["reasons"]) for source in rejected_sources)
    assert any("laser" in " ".join(source.metadata["quality_review"]["reasons"]) for source in rejected_sources)


def test_all_rejected_sources_record_needs_more_sources_and_render_json(monkeypatch, tmp_path) -> None:
    # Given: every connector either returns no records or unrelated noisy Crossref records.
    monkeypatch.setattr(source_nodes, "PubMedConnector", EmptyConnector)
    monkeypatch.setattr(source_nodes, "CrossrefConnector", NoisyCrossrefConnector)
    monkeypatch.setattr(source_nodes, "SemanticScholarConnector", EmptyConnector)
    monkeypatch.setattr(source_nodes, "DuckDuckGoHTMLSearchConnector", EmptyConnector)
    monkeypatch.setattr(source_nodes, "OpenFDA510kConnector", EmptyConnector)
    monkeypatch.setattr(source_nodes, "ClinicalTrialsConnector", EmptyConnector)
    state = _planned_real_state(tmp_path)
    state["research_plan"].search_items = [
        item for item in state["research_plan"].search_items if item.source_type == SourceType.PUBLIC_LITERATURE
    ]

    # When: the search and render nodes run without network fetching.
    search_result = nodes.search_sources(state)
    state.update(search_result)
    render_result = nodes.render_outputs(state)

    # Then: the workflow keeps rejection evidence and records the needs-more-sources signal.
    assert search_result["sources"] == []
    assert len(search_result["rejected_sources"]) > 0
    assert search_result["intermediate"]["source_quality_status"] == "needs_more_sources"
    assert render_result["intermediate"]["rejected_sources_path"] == str(tmp_path / "rejected_sources.json")

    sources_json = json.loads((tmp_path / "sources.json").read_text(encoding="utf-8"))
    rejected_json = json.loads((tmp_path / "rejected_sources.json").read_text(encoding="utf-8"))
    assert sources_json == []
    assert {item["title"] for item in rejected_json} == {BAD_ODE_TITLE, BAD_LASER_TITLE}
    assert all(item["metadata"]["quality_review"]["decision"] == "rejected" for item in rejected_json)


def test_zero_relevance_vendor_programmer_ui_source_is_rejected() -> None:
    # Given: a vendor/manual-shaped result has the requested UI facet but no topical overlap.
    query_expansion = build_query_expansion_plan("调研交叉刺激与8触点刺激的相关程控逻辑和ui界面")
    source = SourceRecord(
        source_type=SourceType.VENDOR_PUBLIC_DOC,
        title="Cafe patio furniture permit checklist",
        url="https://example.test/vendor/cafe-patio-permit",
        publisher="Fixture Vendor",
        search_query=query_expansion.original_query,
        metadata={
            "facet": "programmer_ui",
            "snippet": "Outdoor seating layout rules, table spacing, awning dimensions, and municipal filing deadlines.",
        },
    )

    # When: the shared source-quality gate reviews the candidate.
    review = review_source_quality([source], query_expansion)

    # Then: low relevance alone is enough to reject the source and preserve audit metadata.
    assert review.accepted == ()
    assert review.status == SourceQualityStatus.NEEDS_MORE_SOURCES
    assert len(review.rejected) == 1
    quality_review = review.rejected[0].metadata["quality_review"]
    assert quality_review["decision"] == "rejected"
    assert quality_review["scores"]["relevance"] == 0.0
    assert quality_review["reasons"] == [
        "low_relevance: no title/snippet overlap with query expansion or medical-device terminology"
    ]


def test_short_ui_token_does_not_match_inside_unrelated_words() -> None:
    # Given: an unrelated English title contains "ui" only inside a longer word.
    query_expansion = build_query_expansion_plan("DBS interleaving stimulation 8 contact programmer UI")
    unrelated_source = SourceRecord(
        source_type=SourceType.PUBLIC_WEB,
        title="Warehouse shelving permit guide",
        url="https://example.test/permits/shelving",
        publisher="Municipal Building Desk",
        search_query=query_expansion.original_query,
        metadata={
            "facet": "programmer_ui",
            "snippet": "Industrial storage fixture spacing and commercial filing steps.",
        },
    )
    legitimate_source = SourceRecord(
        source_type=SourceType.VENDOR_PUBLIC_DOC,
        title="DBS clinician programmer UI manual for interleaving stimulation on 8 contact leads",
        url="https://example.test/dbs/programmer-ui",
        publisher="Fixture Neuro",
        search_query=query_expansion.original_query,
        metadata={
            "facet": "programmer_ui",
            "snippet": "Standalone UI workflows for DBS programming, interleaving stimulation, and 8 contact lead setup.",
        },
    )

    # When: the shared source-quality gate reviews both candidates.
    review = review_source_quality([unrelated_source, legitimate_source], query_expansion)

    # Then: substring-only UI collisions are rejected while real UI/programmer matches survive.
    assert [source.title for source in review.accepted] == [legitimate_source.title]
    assert [source.title for source in review.rejected] == [unrelated_source.title]
    rejected_quality = review.rejected[0].metadata["quality_review"]
    assert rejected_quality["decision"] == "rejected"
    assert rejected_quality["scores"]["relevance"] == 0.0
    assert rejected_quality["reasons"] == [
        "low_relevance: no title/snippet overlap with query expansion or medical-device terminology"
    ]
    accepted_quality = review.accepted[0].metadata["quality_review"]
    assert accepted_quality["decision"] == "accepted"
    assert accepted_quality["scores"]["relevance"] >= 0.18
    assert any("UI" in reason for reason in accepted_quality["reasons"])
    assert any("query_terms" in reason for reason in accepted_quality["reasons"])
    assert any("medical_device_terms" in reason for reason in accepted_quality["reasons"])
