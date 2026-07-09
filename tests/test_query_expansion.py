import json

from medical_research_agent.schemas import SourceType
from medical_research_agent.workflow import nodes
from medical_research_agent.workflow.graph import create_initial_state
from medical_research_agent.workflow.state import WorkflowState, dump_workflow_state


def _state_after_planning(query: str) -> WorkflowState:
    # Given: a workflow state before connector search.
    state = create_initial_state(query)
    parsed = nodes.parse_intent(state)
    state.update(parsed)

    # When: research planning runs.
    planned = nodes.plan_research(state)
    state.update(planned)

    return state


def test_workflow_planning_expands_chinese_ui_contact_topic_before_search() -> None:
    # Given: a Chinese UI/programming topic with interleaving stimulation and 8 contacts.
    topic = "调研交叉刺激与8触点刺激的相关程控逻辑和ui界面"

    # When: the workflow reaches the research-planning step.
    state = _state_after_planning(topic)

    # Then: the state preserves the original query and exposes deterministic expansion.
    expansion = state["intermediate"]["query_expansion"]
    assert expansion["original_query"] == topic

    search_text = " | ".join(item.query for item in state["research_plan"].search_items).casefold()
    assert topic in search_text
    assert "interleaving stimulation" in search_text
    assert "8-contact lead" in search_text or "8-contact electrode" in search_text
    assert "clinician programmer" in search_text
    assert "programming interface" in search_text
    assert "scs programmer" in search_text
    assert "dbs programmer" in search_text


def test_workflow_planning_keeps_unrelated_math_topic_generic() -> None:
    # Given: an unrelated non-medical-device research topic.
    topic = "证明黎曼猜想的直觉解释"

    # When: the workflow plans connector search.
    state = _state_after_planning(topic)

    # Then: the workflow routes it as generic/background and avoids neurostimulation terms.
    expansion = state["intermediate"]["query_expansion"]
    assert [facet["kind"] for facet in expansion["facets"]] == ["generic_background"]
    assert [item.source_type for item in state["research_plan"].search_items] == [SourceType.PUBLIC_WEB]

    search_text = " | ".join(item.query for item in state["research_plan"].search_items).casefold()
    blocked_terms = (
        "neurostimulation",
        "interleaving stimulation",
        "deep brain stimulation",
        "spinal cord stimulation",
        "scs programmer",
        "dbs programmer",
    )
    assert all(term not in search_text for term in blocked_terms)


def test_workflow_planning_keeps_scs_only_query_out_of_dbs_terms() -> None:
    # Given: an SCS-specific stimulation topic.
    topic = "调研 SCS 刺激参数的产品范围和论文证据"

    # When: the workflow plans connector search.
    state = _state_after_planning(topic)

    # Then: search terms stay on the SCS domain and do not inject DBS vocabulary.
    expansion_terms = state["intermediate"]["query_expansion"]["english_terms"]
    assert "spinal cord stimulation" in expansion_terms
    assert "deep brain stimulation" not in expansion_terms
    assert "DBS programmer" not in expansion_terms
    assert "interleaving stimulation" not in expansion_terms

    serialized = json.loads(dump_workflow_state(state))
    serialized_terms = serialized["intermediate"]["research_plan"]["query_expansion"]["english_terms"]
    assert "spinal cord stimulation" in serialized_terms
    assert "deep brain stimulation" not in serialized_terms
    assert "DBS programmer" not in serialized_terms
    assert "interleaving stimulation" not in serialized_terms

    search_text = " | ".join(item.query for item in state["research_plan"].search_items).casefold()
    assert "spinal cord stimulation" in search_text
    assert "deep brain stimulation" not in search_text
    assert "dbs programmer" not in search_text
    assert "interleaving stimulation" not in search_text


def test_workflow_planning_keeps_dbs_only_query_out_of_scs_terms() -> None:
    # Given: a DBS-specific stimulation topic.
    topic = "调研 DBS 电极阻抗的论文证据和程控资料"

    # When: the workflow plans connector search.
    state = _state_after_planning(topic)

    # Then: search terms stay on the DBS domain and do not inject SCS vocabulary.
    expansion_terms = state["intermediate"]["query_expansion"]["english_terms"]
    assert "deep brain stimulation" in expansion_terms
    assert "spinal cord stimulation" not in expansion_terms
    assert "SCS programmer" not in expansion_terms
    assert "interleaving stimulation" not in expansion_terms

    serialized = json.loads(dump_workflow_state(state))
    serialized_terms = serialized["intermediate"]["research_plan"]["query_expansion"]["english_terms"]
    assert "deep brain stimulation" in serialized_terms
    assert "spinal cord stimulation" not in serialized_terms
    assert "SCS programmer" not in serialized_terms
    assert "interleaving stimulation" not in serialized_terms

    search_text = " | ".join(item.query for item in state["research_plan"].search_items).casefold()
    assert "deep brain stimulation" in search_text
    assert "dbs programmer" in search_text
    assert "spinal cord stimulation" not in search_text
    assert "scs programmer" not in search_text
    assert "interleaving stimulation" not in search_text


def test_workflow_planning_handles_blank_input_as_generic() -> None:
    # Given: malformed whitespace input that passes the initial task boundary.
    state = _state_after_planning("   ")

    # When: the workflow plans connector search.
    expansion = state["intermediate"]["query_expansion"]

    # Then: the fallback remains generic and bounded.
    assert expansion["original_query"] == "未命名医疗产品调研需求"
    assert [facet["kind"] for facet in expansion["facets"]] == ["generic_background"]
    assert [item.source_type for item in state["research_plan"].search_items] == [SourceType.PUBLIC_WEB]
    assert "neurostimulation" not in state["research_plan"].search_items[0].query.casefold()


def test_workflow_state_serializes_query_expansion_without_stale_models() -> None:
    # Given: a planned workflow state containing the expansion snapshot.
    state = _state_after_planning("调研交叉刺激与8触点刺激的相关程控逻辑和ui界面")

    # When: the state is serialized for workflow_state.json.
    serialized = json.loads(dump_workflow_state(state))

    # Then: intermediate expansion and research plan are plain JSON-compatible data.
    assert serialized["intermediate"]["query_expansion"]["original_query"] == state["task"].query
    assert serialized["intermediate"]["research_plan"]["query_expansion"]["original_query"] == state["task"].query
    assert serialized["research_plan"]["query_expansion"]["original_query"] == state["task"].query
