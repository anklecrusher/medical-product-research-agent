from __future__ import annotations

from medical_research_agent.research_planning import ResearchFacetKind
from medical_research_agent.schemas import SourceRecord, SourceType
from medical_research_agent.workflow import follow_up
from medical_research_agent.workflow.state import SearchPlanItem


class RecordingConnector:
    calls: list[tuple[str, int, tuple[str, ...]]] = []

    def __init__(self, name: str, source_type: SourceType) -> None:
        self.name = name
        self._source_type = source_type

    def search(self, request) -> list[SourceRecord]:  # noqa: ANN001
        preferred = tuple(request.metadata["preferred_connectors"])
        self.calls.append((self.name, request.limit, preferred))
        return [
            SourceRecord(
                task_id=request.task_id,
                source_type=self._source_type,
                title=f"DBS bounded evidence from {self.name}",
                url=f"https://records.example/{self.name}/{request.limit}",
                search_query=request.query,
                metadata={"connector": self.name},
            )
        ]


class UnusedParser:
    def parse_url(self, source: SourceRecord):  # noqa: ANN001
        raise AssertionError(f"follow-up search routing should not parse {source.source_id}")


class OverproducingConnector:
    def __init__(self) -> None:
        self.name = "public_fixture"
        self.calls: list[str] = []

    def search(self, request) -> list[SourceRecord]:  # noqa: ANN001
        self.calls.append(request.query)
        return [
            SourceRecord(
                task_id=request.task_id,
                source_type=SourceType.PUBLIC_WEB,
                title=f"DBS overproduced result {index}",
                url=f"https://records.example/overproduced/{index}",
                search_query=request.query,
                metadata={"connector": self.name},
            )
            for index in range(3)
        ]


def test_bounded_follow_up_uses_preferred_public_routes_and_skips_private_items() -> None:
    # Given: literature and device route items plus a private-only item with no public connector route.
    literature = RecordingConnector("pmc", SourceType.PUBLIC_LITERATURE)
    device = RecordingConnector("accessgudid", SourceType.PUBLIC_REGULATORY)
    fallback = RecordingConnector("duckduckgo_html", SourceType.PUBLIC_WEB)
    RecordingConnector.calls = []
    items = [
        _item("DBS open literature", SourceType.PUBLIC_LITERATURE, ["pmc"], 1),
        _item("DBS device identifier", SourceType.PUBLIC_REGULATORY, ["accessgudid"], 2),
        _item("private DBS manual", SourceType.USER_UPLOADED_PRIVATE, ["local_upload"], 1),
    ]
    connectors_by_preference = {
        ("pmc",): (literature,),
        ("accessgudid",): (device,),
        ("local_upload",): (),
    }
    adapters = follow_up.FollowUpAdapters(
        vendor_connector=fallback,
        web_parser=UnusedParser(),
        pdf_parser=UnusedParser(),
        connector_selector=lambda item: connectors_by_preference[tuple(item.preferred_connectors)],
    )

    # When: bounded follow-up runs the explicit plan items.
    errors: list[str] = []
    sources = follow_up._search_follow_up_sources("task_preferred_routes", items, adapters, errors)

    # Then: each public route receives its item limit, while private-only and hard-coded fallback routes do not run.
    assert RecordingConnector.calls == [
        ("pmc", 1, ("pmc",)),
        ("accessgudid", 2, ("accessgudid",)),
    ]
    assert [source.metadata["connector"] for source in sources] == ["pmc", "accessgudid"]
    assert errors == []


def test_bounded_follow_up_skips_private_items_and_caps_connector_records() -> None:
    # Given: a selector incorrectly returns the same public connector for a public and a private item.
    connector = OverproducingConnector()
    adapters = follow_up.FollowUpAdapters(
        vendor_connector=connector,
        web_parser=UnusedParser(),
        pdf_parser=UnusedParser(),
        connector_selector=lambda item: (connector,),
    )
    items = [
        _item("public DBS route", SourceType.PUBLIC_WEB, ["public_fixture"], 1),
        _item("private DBS route", SourceType.USER_UPLOADED_PRIVATE, ["public_fixture"], 1),
    ]

    # When: bounded follow-up resolves the selected connector routes.
    sources = follow_up._search_follow_up_sources("task_follow_up_boundaries", items, adapters, [])

    # Then: private input triggers no public connector call, and public records cannot exceed its route budget.
    assert connector.calls == ["public DBS route"]
    assert len(sources) == 1
    assert sources[0].search_query == "public DBS route"


def _item(query: str, source_type: SourceType, preferred_connectors: list[str], limit: int) -> SearchPlanItem:
    return SearchPlanItem(
        query=query,
        source_type=source_type,
        rationale="bounded preferred route test",
        facet=ResearchFacetKind.CLINICAL_STUDY,
        preferred_connectors=preferred_connectors,
        limit=limit,
        metadata={
            "follow_up_round": 1,
            "gap_facet": ResearchFacetKind.CLINICAL_STUDY,
            "bounded": True,
        },
    )
