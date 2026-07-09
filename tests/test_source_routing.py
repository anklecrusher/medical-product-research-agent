from medical_research_agent.research_planning import ResearchFacetKind
from medical_research_agent.schemas import SourceType
from medical_research_agent.workflow import nodes
from medical_research_agent.workflow.graph import create_initial_state
from medical_research_agent.workflow.state import WorkflowState


def _planned_state(query: str) -> WorkflowState:
    # Given: a workflow state before source search.
    state = create_initial_state(query)
    state.update(nodes.parse_intent(state))

    # When: research planning builds connector-ready search items.
    state.update(nodes.plan_research(state))

    return state


def test_ui_programming_topic_routes_by_facet_before_literature() -> None:
    # Given: a neurostimulation topic that asks for programming logic and UI.
    topic = "调研交叉刺激与8触点刺激的相关程控逻辑和ui界面"

    # When: source routing is planned.
    state = _planned_state(topic)

    # Then: the plan keeps separate facets instead of collapsing them by source type.
    items = state["research_plan"].search_items
    routed_facets = {item.facet for item in items}
    assert ResearchFacetKind.VENDOR_MANUAL in routed_facets
    assert ResearchFacetKind.PROGRAMMER_UI in routed_facets
    assert ResearchFacetKind.STIMULATION in routed_facets
    assert ResearchFacetKind.ELECTRODE_CONTACTS in routed_facets

    assert any(
        item.facet == ResearchFacetKind.VENDOR_MANUAL
        and item.source_type == SourceType.VENDOR_PUBLIC_DOC
        and "duckduckgo_html" in item.preferred_connectors
        for item in items
    )
    assert any(
        item.facet == ResearchFacetKind.PROGRAMMER_UI
        and item.source_type == SourceType.PUBLIC_WEB
        and item.route_priority < 35
        for item in items
    )
    assert any(item.source_type == SourceType.PUBLIC_LITERATURE for item in items)
    assert any(item.source_type == SourceType.PUBLIC_REGULATORY for item in items)

    first_literature_index = next(
        index for index, item in enumerate(items) if item.source_type == SourceType.PUBLIC_LITERATURE
    )
    first_manual_index = next(
        index
        for index, item in enumerate(items)
        if item.source_type in (SourceType.VENDOR_PUBLIC_DOC, SourceType.PUBLIC_WEB)
    )
    assert first_manual_index < first_literature_index


def test_generic_math_topic_routes_only_to_bounded_public_web() -> None:
    # Given: a non-medical generic topic.
    state = _planned_state("证明黎曼猜想的直觉解释")

    # When: source routing is inspected.
    items = state["research_plan"].search_items

    # Then: it stays bounded to one generic public-web item.
    assert [(item.facet, item.source_type, item.limit) for item in items] == [
        (ResearchFacetKind.GENERIC_BACKGROUND, SourceType.PUBLIC_WEB, 2)
    ]
    assert items[0].preferred_connectors == ["duckduckgo_html"]
