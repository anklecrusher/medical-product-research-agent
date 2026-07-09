"""Workflow nodes for mock and source-backed medical research runs."""

from __future__ import annotations

from typing import Any

from medical_research_agent.evidence import extract_evidence_from_documents
from medical_research_agent.evidence_dedup import deduplicate_evidence_items
from medical_research_agent.research_planning import build_query_expansion_plan
from medical_research_agent.schemas import (
    DocumentFormat,
    ParsedDocument,
    SourceRecord,
    TaskStatus,
)
from medical_research_agent.source_quality import review_source_quality
from medical_research_agent.workflow.state import (
    NodeLog,
    ResearchIntent,
    ResearchPlan,
    WorkflowState,
)
from medical_research_agent.workflow.query_expansion import (
    build_search_items_from_expansion,
    focus_terms_from_expansion,
    source_types_from_expansion,
)
from medical_research_agent.workflow.report_nodes import plan_report, render_outputs, verify_claims, write_report
from medical_research_agent.workflow.source_nodes import fetch_and_parse_sources_real, search_sources_real


def _log(node: str, message: str, **metadata: Any) -> list[NodeLog]:
    return [NodeLog(node=node, message=message, metadata=metadata)]


def parse_intent(state: WorkflowState) -> dict[str, Any]:
    """Parse a one-sentence request into a workflow intent."""

    task = state["task"]
    query = task.query.strip()
    title = task.title or query[:36]
    query_expansion = build_query_expansion_plan(query)
    focus_terms = focus_terms_from_expansion(query_expansion)

    intent = ResearchIntent(
        title=title,
        original_query=query,
        query_expansion=query_expansion,
        focus_terms=focus_terms,
        target_source_types=source_types_from_expansion(query_expansion),
        language=task.language,
    )
    task.title = title
    task.status = TaskStatus.RUNNING

    return {
        "task": task,
        "intent": intent,
        "current_step": "parse_intent",
        "intermediate": {
            "intent": intent.model_dump(mode="json"),
            "query_expansion": query_expansion.model_dump(mode="json"),
        },
        "node_logs": _log(
            "parse_intent",
            "Parsed mock research intent.",
            focus_terms=focus_terms,
            query_expansion_terms=len(query_expansion.english_terms),
        ),
    }


def plan_research(state: WorkflowState) -> dict[str, Any]:
    """Create connector-ready search tasks from parsed intent."""

    intent = state["intent"]
    query_expansion = intent.query_expansion
    search_items = build_search_items_from_expansion(query_expansion)
    plan = ResearchPlan(
        objective=f"围绕“{intent.original_query}”形成可追溯的医疗产品调研草稿。",
        query_expansion=query_expansion,
        search_items=search_items,
        expected_evidence=["产品参数", "论文证据", "厂商资料", "监管线索", "风险与未确认项"],
    )

    return {
        "research_plan": plan,
        "current_step": "plan_research",
        "intermediate": {
            "query_expansion": query_expansion.model_dump(mode="json"),
            "research_plan": plan.model_dump(mode="json"),
        },
        "node_logs": _log("plan_research", "Created mock research plan.", search_items=len(search_items)),
    }


def search_sources(state: WorkflowState) -> dict[str, Any]:
    """Search sources with real connectors when enabled, otherwise use mock data."""

    if state.get("use_real_connectors"):
        return search_sources_real(state)

    return _search_sources_mock(state)


def _search_sources_mock(state: WorkflowState) -> dict[str, Any]:
    """Return mock normalized sources in the same shape as real connectors."""

    task = state["task"]
    plan = state["research_plan"]
    sources: list[SourceRecord] = []
    for index, item in enumerate(plan.search_items, start=1):
        sources.append(
            SourceRecord(
                task_id=task.task_id,
                source_type=item.source_type,
                title=f"Mock source {index}: {item.source_type.value}",
                url=f"https://example.com/mock/{task.task_id}/{index}",
                publisher="Mock Connector",
                search_query=item.query,
                credibility_note="Mock source for workflow wiring only.",
                metadata={
                    "mock": True,
                    "rationale": item.rationale,
                    "facet": item.facet.value if item.facet else None,
                    "preferred_connectors": item.preferred_connectors,
                    "route_priority": item.route_priority,
                },
            )
        )

    review = review_source_quality(sources, plan.query_expansion)

    return {
        "sources": list(review.accepted),
        "rejected_sources": list(review.rejected),
        "current_step": "search_sources",
        "intermediate": {
            "source_count": len(review.accepted),
            "raw_source_count": len(sources),
            "rejected_source_count": len(review.rejected),
            "source_quality_status": review.status.value,
        },
        "node_logs": _log(
            "search_sources",
            "Produced mock source records.",
            source_count=len(review.accepted),
            rejected_source_count=len(review.rejected),
        ),
    }


def fetch_and_parse_sources(state: WorkflowState) -> dict[str, Any]:
    """Fetch and parse sources with real parsers when enabled."""

    if state.get("use_real_connectors"):
        return fetch_and_parse_sources_real(state)

    return _fetch_and_parse_sources_mock(state)


def _fetch_and_parse_sources_mock(state: WorkflowState) -> dict[str, Any]:
    """Convert mock sources into parsed documents without network access."""

    task = state["task"]
    documents = [
        ParsedDocument(
            task_id=task.task_id,
            source_id=source.source_id,
            format=DocumentFormat.WEB_PAGE,
            title=source.title,
            text=(
                f"{source.title}\n"
                f"Mock parsed content for {task.query}. "
                "Includes product parameters, source boundaries, and evidence notes."
            ),
            summary=f"Mock summary derived from {source.title}.",
            language=task.language,
            parser_name="mock_parser",
            metadata={"mock": True},
        )
        for source in state.get("sources", [])
    ]

    return {
        "documents": documents,
        "current_step": "fetch_and_parse_sources",
        "intermediate": {"document_count": len(documents)},
        "node_logs": _log(
            "fetch_and_parse_sources",
            "Parsed mock documents from source records.",
            document_count=len(documents),
        ),
    }


def extract_evidence(state: WorkflowState) -> dict[str, Any]:
    """Extract deterministic structured evidence from parsed documents."""

    task = state["task"]
    extracted = extract_evidence_from_documents(
        task.task_id,
        state.get("sources", []),
        state.get("documents", []),
    )

    return {
        "evidence": extracted.evidence,
        "product_specs": extracted.product_specs,
        "current_step": "extract_evidence",
        "intermediate": {
            "evidence_count": len(extracted.evidence),
            "product_spec_count": len(extracted.product_specs),
        },
        "node_logs": _log(
            "extract_evidence",
            "Extracted deterministic structured evidence.",
            evidence_count=len(extracted.evidence),
            product_spec_count=len(extracted.product_specs),
        ),
    }


def deduplicate_evidence(state: WorkflowState) -> dict[str, Any]:
    """Deduplicate evidence while preserving status for conflict checks."""

    deduped = deduplicate_evidence_items(
        state.get("evidence", []),
        state.get("product_specs", []),
    )

    return {
        "evidence": deduped.evidence,
        "product_specs": deduped.product_specs,
        "current_step": "deduplicate_evidence",
        "intermediate": {
            "deduplicated_evidence_count": len(deduped.evidence),
            "deduplicated_product_spec_count": len(deduped.product_specs),
            "duplicate_count": deduped.duplicate_count,
            "conflict_count": deduped.conflict_count,
        },
        "node_logs": _log(
            "deduplicate_evidence",
            "Deduplicated evidence and marked parameter conflicts.",
            evidence_count=len(deduped.evidence),
            product_spec_count=len(deduped.product_specs),
            duplicate_count=deduped.duplicate_count,
            conflict_count=deduped.conflict_count,
        ),
    }
