"""LLM request and response contracts."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from medical_research_agent.schemas import SourceType


class LLMMessage(BaseModel):
    """A provider-neutral chat message."""

    role: Literal["system", "user", "assistant"]
    content: str = Field(min_length=1)


class LLMUsage(BaseModel):
    """Token usage returned by a provider when available."""

    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None


class LLMRequest(BaseModel):
    """Provider-neutral LLM request with privacy context."""

    messages: list[LLMMessage]
    model: str | None = None
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    max_tokens: int | None = Field(default=None, gt=0)
    response_format: dict[str, Any] | None = None
    source_types: list[SourceType] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class LLMResponse(BaseModel):
    """Provider-neutral LLM response."""

    content: str
    model: str
    provider: str
    usage: LLMUsage | None = None
    raw: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
