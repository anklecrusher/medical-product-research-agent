from __future__ import annotations

from collections.abc import Callable

from medical_research_agent.connectors.literature_access import attach_access_metadata
from medical_research_agent.schemas import SourceRecord, SourceType
from medical_research_agent.source_contracts import AccessCheck, FreeAccessStatus
from medical_research_agent.workflow import nodes, source_nodes
from medical_research_agent.workflow.graph import create_initial_state
from medical_research_agent.workflow.state import ResearchPlan, SearchPlanItem


class _RoutedConnector:
    calls: list[tuple[str, tuple[str, ...]]] = []

    def __init__(self, name: str, source_type: SourceType) -> None:
        self.name = name
        self._source_type = source_type

    def search(self, request) -> list[SourceRecord]:  # noqa: ANN001
        preferred = request.metadata.get("preferred_connectors", ()) if request.metadata else ()
        self.calls.append((self.name, tuple(preferred)))
        return [
            SourceRecord(
                task_id=request.task_id,
                source_type=self._source_type,
                title=f"DBS open access FDA regulatory patent evidence from {self.name}",
                url=f"https://records.example/{self.name}",
                search_query=request.query,
                credibility_note="Public medical-device research fixture.",
                metadata={"connector": self.name, "snippet": "DBS open access FDA patent evidence"},
            )
        ]


class _RecordingAccessVerifier:
    checked_connectors: list[str] = []

    def verify(self, source: SourceRecord) -> AccessCheck:
        connector = str(source.metadata["connector"])
        self.checked_connectors.append(connector)
        status = FreeAccessStatus.PAYWALLED if connector == "patentsview" else FreeAccessStatus.FREE_LANDING_PAGE
        return AccessCheck(
            source_id=source.source_id,
            url=str(source.url),
            status=status,
            checked_by="route-test",
        )


def test_real_source_node_selects_bounded_route_connectors_and_access_gates_candidates(monkeypatch) -> None:
    # Given: a strategy that selects open literature, regulatory device records, and patents.
    _RoutedConnector.calls = []
    _RecordingAccessVerifier.checked_connectors = []
    _patch_connector_factories(monkeypatch)
    monkeypatch.setattr(source_nodes, "SourceAccessVerifier", _RecordingAccessVerifier, raising=False)
    state = create_initial_state("调研 DBS 开放全文论文、FDA监管资料、AccessGUDID和专利")
    state.update(nodes.parse_intent(state))
    state.update(nodes.plan_research(state))

    # When: the real source-search workflow node executes the planned routes.
    result = source_nodes.search_sources_real(state)

    # Then: only selected public connector families execute, and item-level access rejects the paywalled item.
    called_names = {name for name, _ in _RoutedConnector.calls}
    assert {"pmc", "europe_pmc", "openalex", "accessgudid", "patentsview"} <= called_names
    assert all(name in preferred for name, preferred in _RoutedConnector.calls)
    assert set(_RecordingAccessVerifier.checked_connectors) == called_names
    assert result["intermediate"]["source_access_check_count"] == len(_RecordingAccessVerifier.checked_connectors)
    assert result["intermediate"]["source_access_rejected_count"] == 1
    assert all(source.metadata["connector"] != "patentsview" for source in result["sources"])
    rejected_patent = next(source for source in result["rejected_sources"] if source.metadata["connector"] == "patentsview")
    assert rejected_patent.metadata["access_check"]["status"] == FreeAccessStatus.PAYWALLED.value
    assert rejected_patent.metadata["citation_eligibility"]["eligible"] is False


def _patch_connector_factories(monkeypatch) -> None:
    patch = lambda attribute, name, source_type: monkeypatch.setattr(  # noqa: E731
        source_nodes,
        attribute,
        _connector_factory(name, source_type),
        raising=False,
    )
    patch("PubMedConnector", "pubmed", SourceType.PUBLIC_LITERATURE)
    patch("CrossrefConnector", "crossref", SourceType.PUBLIC_LITERATURE)
    patch("SemanticScholarConnector", "semantic_scholar", SourceType.PUBLIC_LITERATURE)
    patch("PMCFullTextConnector", "pmc", SourceType.PUBLIC_LITERATURE)
    patch("EuropePMCConnector", "europe_pmc", SourceType.PUBLIC_LITERATURE)
    patch("OpenAlexConnector", "openalex", SourceType.PUBLIC_LITERATURE)
    patch("OpenFDA510kConnector", "openfda_510k", SourceType.PUBLIC_REGULATORY)
    patch("ClinicalTrialsConnector", "clinicaltrials_gov", SourceType.PUBLIC_REGULATORY)
    patch("AccessGUDIDConnector", "accessgudid", SourceType.PUBLIC_REGULATORY)
    patch("PatentsViewConnector", "patentsview", SourceType.PUBLIC_WEB)
    patch("DuckDuckGoHTMLSearchConnector", "duckduckgo_html", SourceType.PUBLIC_WEB)


def _connector_factory(name: str, source_type: SourceType) -> Callable[..., _RoutedConnector]:
    def factory(*args, **kwargs) -> _RoutedConnector:  # noqa: ANN002, ANN003
        configured_type = kwargs.get("source_type", source_type)
        return _RoutedConnector(name, configured_type)

    return factory


class _DeclaredMetadataOnlyCrossrefConnector:
    name = "crossref"

    def search(self, request) -> list[SourceRecord]:  # noqa: ANN001
        source = SourceRecord(
            source_id="src_crossref_metadata_only",
            task_id=request.task_id,
            source_type=SourceType.PUBLIC_LITERATURE,
            title="DBS electrode impedance literature metadata record",
            url="https://doi.org/10.1000/dbs-metadata",
            search_query=request.query,
            credibility_note="Crossref scholarly metadata record.",
            metadata={"connector": self.name, "snippet": "DBS electrode impedance literature evidence"},
        )
        return [
            attach_access_metadata(
                source,
                status=FreeAccessStatus.METADATA_ONLY,
                evidence_note="Crossref metadata is not a final citation contract.",
            )
        ]


class _GenericFreeLandingVerifier:
    def verify(self, source: SourceRecord) -> AccessCheck:
        return AccessCheck(
            source_id=source.source_id,
            url=str(source.url),
            status=FreeAccessStatus.FREE_LANDING_PAGE,
            checked_by="test-generic-verifier",
        )


def test_real_source_node_preserves_declared_crossref_metadata_only_contract(monkeypatch) -> None:
    # Given: Crossref declares its record as metadata-only while a generic verifier sees a free landing page.
    state = create_initial_state("调研 DBS 电极阻抗论文证据")
    state.update(nodes.parse_intent(state))
    state["research_plan"] = ResearchPlan(
        objective="Test Crossref source contract preservation.",
        query_expansion=state["intent"].query_expansion,
        search_items=[
            SearchPlanItem(
                query="DBS electrode impedance literature",
                source_type=SourceType.PUBLIC_LITERATURE,
                rationale="Crossref metadata regression fixture.",
                preferred_connectors=["crossref"],
                limit=1,
            )
        ],
    )
    monkeypatch.setattr(source_nodes, "CrossrefConnector", _DeclaredMetadataOnlyCrossrefConnector)
    monkeypatch.setattr(source_nodes, "SourceAccessVerifier", _GenericFreeLandingVerifier)

    # When: the real source node verifies and triages the declared Crossref source.
    result = source_nodes.search_sources_real(state)

    # Then: its restrictive contract remains rejected and cannot enter parsing through accepted sources.
    assert result["sources"] == []
    rejected = result["rejected_sources"]
    assert [source.source_id for source in rejected] == ["src_crossref_metadata_only"]
    assert rejected[0].metadata["access_check"]["status"] == FreeAccessStatus.METADATA_ONLY.value
    assert rejected[0].metadata["citation_eligibility"]["eligible"] is False
