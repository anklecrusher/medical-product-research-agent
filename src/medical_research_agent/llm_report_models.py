"""Strict response contracts for the evidence-grounded LLM report writer."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class FrozenReportModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class LLMReportClaim(FrozenReportModel):
    text: str = Field(min_length=1)
    evidence_ids: tuple[str, ...] = Field(min_length=1)
    source_ids: tuple[str, ...] = Field(min_length=1)
    needs_review: bool = False


class LLMReportSection(FrozenReportModel):
    section_id: str = Field(min_length=1)
    content_markdown: str = Field(min_length=1)
    evidence_ids: tuple[str, ...] = Field(default=())
    source_ids: tuple[str, ...] = Field(default=())
    claim_indices: tuple[int, ...] = Field(default=())


class LLMReportResponse(FrozenReportModel):
    sections: tuple[LLMReportSection, ...] = Field(default=())
    claims: tuple[LLMReportClaim, ...] = Field(default=())
    rationale: str = Field(min_length=1)
