"""Typed contracts for source strategy, access checks, and report quality."""

from __future__ import annotations

from enum import StrEnum
from typing import Final

from pydantic import AnyUrl, BaseModel, ConfigDict, Field, computed_field

from medical_research_agent.research_planning import ResearchFacetKind
from medical_research_agent.schemas import SourceType


class FrozenContractModel(BaseModel):
    model_config = ConfigDict(frozen=True)


class FreeAccessStatus(StrEnum):
    FREE_ACCESSIBLE = "free_accessible"
    OPEN_ACCESS = "open_access"
    OPEN_FULL_TEXT = "open_full_text"
    PDF_ACCESSIBLE = "pdf_accessible"
    ABSTRACT_ACCESSIBLE = "abstract_accessible"
    FREE_LANDING_PAGE = "free_landing_page"
    METADATA_ONLY = "metadata_only"
    BLOCKED = "blocked"
    PAYWALLED = "paywalled"
    LOGIN_REQUIRED = "login_required"
    NOT_FOUND = "not_found"
    PARSER_FAILED = "parser_failed"
    NEEDS_REVIEW = "needs_review"


FINAL_CITABLE_ACCESS_STATUSES: Final[tuple[FreeAccessStatus, ...]] = (
    FreeAccessStatus.FREE_ACCESSIBLE,
    FreeAccessStatus.OPEN_ACCESS,
    FreeAccessStatus.OPEN_FULL_TEXT,
    FreeAccessStatus.PDF_ACCESSIBLE,
    FreeAccessStatus.ABSTRACT_ACCESSIBLE,
    FreeAccessStatus.FREE_LANDING_PAGE,
)


class SourceRoute(FrozenContractModel):
    route_id: str = Field(min_length=1)
    facet: ResearchFacetKind
    source_types: tuple[SourceType, ...] = Field(min_length=1)
    connectors: tuple[str, ...] = Field(min_length=1)
    queries: tuple[str, ...] = Field(min_length=1)
    budget: int = Field(default=3, ge=1)
    rationale: str = Field(min_length=1)


class SourceStrategy(FrozenContractModel):
    task_id: str | None = None
    objective: str = Field(min_length=1)
    routes: tuple[SourceRoute, ...] = Field(min_length=1)
    max_follow_up_rounds: int = Field(default=1, ge=0)
    privacy_note: str | None = None


class AccessCheck(FrozenContractModel):
    source_id: str = Field(min_length=1)
    url: AnyUrl | None = None
    status: FreeAccessStatus
    content_type: str | None = None
    status_code: int | None = Field(default=None, ge=100, le=599)
    final_url: AnyUrl | None = None
    redirected: bool = False
    failure_reason: str | None = None
    checked_by: str | None = None
    evidence_note: str | None = None


class CitationEligibility(FrozenContractModel):
    source_id: str = Field(min_length=1)
    eligible: bool
    status: FreeAccessStatus
    url: AnyUrl | None = None
    reason: str

    @classmethod
    def from_access_check(cls, access_check: AccessCheck) -> CitationEligibility:
        can_cite = access_check.status in FINAL_CITABLE_ACCESS_STATUSES and access_check.url is not None
        reason = "eligible_free_access_source"
        if access_check.url is None:
            reason = "source_url_required_for_final_citation"
        elif not can_cite:
            reason = f"access_status_not_final_citable:{access_check.status.value}"
        return cls(
            source_id=access_check.source_id,
            eligible=can_cite,
            status=access_check.status,
            url=access_check.url,
            reason=reason,
        )


class LLMResearchDecision(FrozenContractModel):
    decision_id: str = Field(min_length=1)
    selected_routes: tuple[str, ...] = Field(default=())
    accepted_source_ids: tuple[str, ...] = Field(default=())
    rejected_source_ids: tuple[str, ...] = Field(default=())
    follow_up_queries: tuple[str, ...] = Field(default=())
    rationale: str = Field(min_length=1)


class ReportQualityMetric(FrozenContractModel):
    name: str = Field(min_length=1)
    score: float = Field(ge=0.0, le=1.0)
    required: bool = True
    passed: bool = True
    detail: str | None = None


class ReportQualityMetrics(FrozenContractModel):
    metrics: tuple[ReportQualityMetric, ...] = Field(min_length=1)
    summary: str = Field(min_length=1)

    @computed_field
    @property
    def passed(self) -> bool:
        return all(metric.passed and metric.score > 0.0 for metric in self.metrics if metric.required)
