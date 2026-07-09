from __future__ import annotations

import httpx
import pytest

from medical_research_agent.connectors import (
    ClinicalTrialsConnector,
    ConnectorError,
    ConnectorErrorKind,
    OpenFDA510kConnector,
    SearchRequest,
    SemanticScholarConnector,
)
from medical_research_agent.research_planning import ResearchFacetKind
from medical_research_agent.schemas import SourceRecord, SourceType, TaskStatus
from medical_research_agent.workflow.graph import run_source_workflow
from medical_research_agent.workflow import source_nodes
from medical_research_agent.workflow.source_nodes import _run_connectors
from medical_research_agent.workflow.state import SearchPlanItem


def test_openfda_sanitizes_chinese_topic_from_api_search_params() -> None:
    captured_search: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured_search.append(request.url.params["search"])
        return httpx.Response(200, json={"results": []})

    connector = OpenFDA510kConnector(client=httpx.Client(transport=httpx.MockTransport(handler)))
    request = SearchRequest(
        query="调研交叉刺激与8触点刺激的相关程控逻辑和ui界面",
        limit=1,
        metadata={
            "expanded_terms": [
                "interleaving stimulation",
                "neurostimulation",
                "clinician programmer",
                "8-contact lead",
            ],
            "facet": ResearchFacetKind.REGULATORY.value,
        },
    )

    connector.search(request)

    assert captured_search == [
        'device_name:"interleaving stimulation neurostimulation clinician programmer 8-contact lead"+applicant:"interleaving stimulation neurostimulation clinician programmer 8-contact lead"'
    ]
    assert "调研交叉刺激" not in captured_search[0]
    assert "product_code" not in captured_search[0]


def test_openfda_400_is_bad_query_error() -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(400, text="invalid query", request=request))
    connector = OpenFDA510kConnector(client=httpx.Client(transport=transport))

    with pytest.raises(ConnectorError) as error:
        connector.search(SearchRequest(query="调研交叉刺激", limit=1))

    assert error.value.kind == ConnectorErrorKind.BAD_QUERY
    assert "invalid query" in error.value.message


def test_semantic_scholar_429_is_retryable_error() -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(429, text="rate limit", request=request))
    connector = SemanticScholarConnector(client=httpx.Client(transport=transport))

    with pytest.raises(ConnectorError) as error:
        connector.search(SearchRequest(query="interleaving stimulation", limit=1))

    assert error.value.kind == ConnectorErrorKind.RETRYABLE
    assert "rate limit" in error.value.message


def test_clinical_trials_403_is_blocked_error() -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(403, text="forbidden", request=request))
    connector = ClinicalTrialsConnector(client=httpx.Client(transport=transport))

    with pytest.raises(ConnectorError) as error:
        connector.search(SearchRequest(query="interleaving stimulation", limit=1))

    assert error.value.kind == ConnectorErrorKind.BLOCKED
    assert "forbidden" in error.value.message


def test_workflow_connector_error_includes_classification() -> None:
    class BlockedConnector:
        name = "blocked_connector"

        def search(self, request: SearchRequest) -> list[SourceRecord]:
            raise ConnectorError(self.name, "blocked by upstream", kind=ConnectorErrorKind.BLOCKED)

    item = SearchPlanItem(
        query="调研交叉刺激 interleaving stimulation",
        source_type=SourceType.PUBLIC_REGULATORY,
        rationale="regulatory search",
        facet=ResearchFacetKind.REGULATORY,
    )
    connector_counts: dict[str, int] = {}

    sources, errors = _run_connectors([BlockedConnector()], SearchRequest(query=item.query), item, connector_counts)

    assert sources == []
    assert errors == [
        "blocked_connector: blocked by upstream [kind=blocked; facet=regulatory; source_type=public_regulatory]"
    ]
    assert connector_counts == {"blocked_connector": 0}


def test_chinese_topic_smoke_records_classified_connector_errors(monkeypatch, tmp_path) -> None:
    class BadQueryConnector:
        name = "openfda_510k"

        def search(self, request: SearchRequest) -> list[SourceRecord]:
            raise ConnectorError(self.name, "HTTP 400: invalid query", kind=ConnectorErrorKind.BAD_QUERY)

    class BlockedConnector:
        name = "clinicaltrials_gov"

        def search(self, request: SearchRequest) -> list[SourceRecord]:
            raise ConnectorError(self.name, "HTTP 403: forbidden", kind=ConnectorErrorKind.BLOCKED)

    class RetryableConnector:
        name = "semantic_scholar"

        def __init__(self, api_key: str | None = None) -> None:
            self.api_key = api_key

        def search(self, request: SearchRequest) -> list[SourceRecord]:
            raise ConnectorError(self.name, "HTTP 429: rate limit", kind=ConnectorErrorKind.RETRYABLE)

    class WebBlockedConnector:
        name = "duckduckgo_html"

        def __init__(self, source_type: SourceType = SourceType.PUBLIC_WEB) -> None:
            self.source_type = source_type

        def search(self, request: SearchRequest) -> list[SourceRecord]:
            raise ConnectorError(self.name, "HTTP 403: forbidden", kind=ConnectorErrorKind.BLOCKED)

    monkeypatch.setattr(source_nodes, "PubMedConnector", BadQueryConnector)
    monkeypatch.setattr(source_nodes, "CrossrefConnector", BlockedConnector)
    monkeypatch.setattr(source_nodes, "SemanticScholarConnector", RetryableConnector)
    monkeypatch.setattr(source_nodes, "DuckDuckGoHTMLSearchConnector", WebBlockedConnector)
    monkeypatch.setattr(source_nodes, "OpenFDA510kConnector", BadQueryConnector)
    monkeypatch.setattr(source_nodes, "ClinicalTrialsConnector", BlockedConnector)

    state = run_source_workflow("调研交叉刺激与8触点刺激的相关程控逻辑和ui界面", output_dir=tmp_path)

    assert any("kind=bad_query" in error for error in state["errors"])
    assert any("kind=blocked" in error for error in state["errors"])
    assert any("kind=retryable" in error for error in state["errors"])
    assert state["intermediate"]["source_quality_status"] == "needs_more_sources"
    assert state["task"].status == TaskStatus.NEEDS_MORE_SOURCES
