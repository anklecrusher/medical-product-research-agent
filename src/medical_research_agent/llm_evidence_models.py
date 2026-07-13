"""Strict response models for LLM evidence extraction."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from medical_research_agent.schemas import EvidenceKind


class FrozenExtractionModel(BaseModel):
    """Reject response fields outside the extraction contract."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class LLMEvidenceItem(FrozenExtractionModel):
    """One source- and document-bound evidence statement."""

    source_id: str = Field(min_length=1)
    document_id: str = Field(min_length=1)
    kind: EvidenceKind
    statement: str = Field(min_length=1)
    value: str | float | int | None = None
    unit: str | None = None
    product_name: str | None = None
    parameter_name: str | None = None
    quote: str = Field(min_length=1)
    location: str = Field(min_length=1)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    facet: str | None = None


class LLMProductSpec(FrozenExtractionModel):
    """A product parameter linked to one evidence response item."""

    source_id: str = Field(min_length=1)
    evidence_index: int = Field(ge=0)
    product_name: str = Field(min_length=1)
    parameter_name: str = Field(min_length=1)
    value: str | float | int
    unit: str | None = None
    notes: str | None = None


class LLMClaim(FrozenExtractionModel):
    """A report claim supported by at least one evidence response item."""

    source_id: str = Field(min_length=1)
    evidence_indices: tuple[int, ...] = Field(min_length=1)
    text: str = Field(min_length=1)


class LLMEvidenceResponse(FrozenExtractionModel):
    """The only response shape accepted from an evidence-extraction LLM."""

    evidence: tuple[LLMEvidenceItem, ...] = Field(default=())
    product_specs: tuple[LLMProductSpec, ...] = Field(default=())
    claims: tuple[LLMClaim, ...] = Field(default=())
    rationale: str = Field(min_length=1)
