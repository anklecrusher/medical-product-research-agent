"""LangGraph assembly for the medical research workflow."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from langgraph.graph import END, START, StateGraph

from medical_research_agent.schemas import ResearchTask
from medical_research_agent.workflow import follow_up
from medical_research_agent.workflow import nodes
from medical_research_agent.workflow.state import WorkflowState


WORKFLOW_NODE_ORDER = [
    "parse_intent",
    "plan_research",
    "search_sources",
    "fetch_and_parse_sources",
    "extract_evidence",
    "deduplicate_evidence",
    "follow_up_evidence_gaps",
    "plan_report",
    "write_report",
    "verify_claims",
    "render_outputs",
]


def build_workflow_graph() -> Any:
    """Build and compile the mock LangGraph workflow."""

    graph = StateGraph(WorkflowState)
    graph.add_node("parse_intent", nodes.parse_intent)
    graph.add_node("plan_research", nodes.plan_research)
    graph.add_node("search_sources", nodes.search_sources)
    graph.add_node("fetch_and_parse_sources", nodes.fetch_and_parse_sources)
    graph.add_node("extract_evidence", nodes.extract_evidence)
    graph.add_node("deduplicate_evidence", nodes.deduplicate_evidence)
    graph.add_node("follow_up_evidence_gaps", follow_up.follow_up_evidence_gaps)
    graph.add_node("plan_report", nodes.plan_report)
    graph.add_node("write_report", nodes.write_report)
    graph.add_node("verify_claims", nodes.verify_claims)
    graph.add_node("render_outputs", nodes.render_outputs)

    graph.add_edge(START, WORKFLOW_NODE_ORDER[0])
    for previous, current in zip(WORKFLOW_NODE_ORDER, WORKFLOW_NODE_ORDER[1:]):
        graph.add_edge(previous, current)
    graph.add_edge(WORKFLOW_NODE_ORDER[-1], END)
    return graph.compile()


def create_initial_state(query: str, *, output_dir: str | Path | None = None) -> WorkflowState:
    """Create the initial state for a one-sentence research request."""

    task = ResearchTask(query=query, output_dir=str(output_dir) if output_dir else None)
    return {
        "task": task,
        "sources": [],
        "rejected_sources": [],
        "documents": [],
        "evidence": [],
        "product_specs": [],
        "report_sections": [],
        "claims": [],
        "artifacts": [],
        "intermediate": {},
        "current_step": "created",
        "use_real_connectors": False,
        "node_logs": [],
        "errors": [],
    }


def run_mock_workflow(query: str, *, output_dir: str | Path | None = None) -> WorkflowState:
    """Run the compiled mock workflow from a single research query."""

    app = build_workflow_graph()
    return app.invoke(create_initial_state(query, output_dir=output_dir))


def run_source_workflow(query: str, *, output_dir: str | Path | None = None) -> WorkflowState:
    """Run the workflow with real connector and parser nodes enabled."""

    app = build_workflow_graph()
    state = create_initial_state(query, output_dir=output_dir)
    state["use_real_connectors"] = True
    return app.invoke(state)
