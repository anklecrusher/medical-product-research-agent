"""Workflow state contracts for LangGraph orchestration."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from operator import add
from typing import Annotated, Any, TypedDict

from pydantic import BaseModel, Field

from medical_research_agent.schemas import (
    Claim,
    EvidenceItem,
    ParsedDocument,
    ProductSpec,
    ReportArtifact,
    ReportSection,
    ResearchTask,
    SourceRecord,
    SourceType,
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def merge_intermediate(left: dict[str, Any] | None, right: dict[str, Any] | None) -> dict[str, Any]:
    """Merge intermediate snapshots emitted by sequential workflow nodes."""

    return {**(left or {}), **(right or {})}


class NodeLog(BaseModel):
    """A compact audit entry emitted by each workflow node."""

    node: str
    message: str
    status: str = "completed"
    created_at: datetime = Field(default_factory=_utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ResearchIntent(BaseModel):
    """Parsed intent from a one-sentence research request."""

    title: str
    original_query: str
    focus_terms: list[str] = Field(default_factory=list)
    target_source_types: list[SourceType] = Field(default_factory=list)
    language: str = "zh-CN"


class SearchPlanItem(BaseModel):
    """A planned search task that future connectors can execute."""

    query: str
    source_type: SourceType
    rationale: str
    limit: int = Field(default=3, ge=1)


class ResearchPlan(BaseModel):
    """High-level research plan produced before retrieval."""

    objective: str
    search_items: list[SearchPlanItem] = Field(default_factory=list)
    expected_evidence: list[str] = Field(default_factory=list)


class WorkflowState(TypedDict, total=False):
    """LangGraph state shared by all workflow nodes.

    Lists use additive reducers so every node can append logs and artifacts
    without overwriting prior state.
    """

    task: ResearchTask
    intent: ResearchIntent
    research_plan: ResearchPlan
    sources: list[SourceRecord]
    documents: list[ParsedDocument]
    evidence: list[EvidenceItem]
    product_specs: list[ProductSpec]
    report_sections: list[ReportSection]
    claims: list[Claim]
    report_markdown: str
    artifacts: list[ReportArtifact]
    intermediate: Annotated[dict[str, Any], merge_intermediate]
    current_step: str
    use_real_connectors: bool
    node_logs: Annotated[list[NodeLog], add]
    errors: Annotated[list[str], add]


def _jsonable(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    return value


def dump_workflow_state(state: WorkflowState) -> str:
    """Serialize workflow state for logs, examples, and tests."""

    return json.dumps(_jsonable(dict(state)), ensure_ascii=False, indent=2, default=str)
