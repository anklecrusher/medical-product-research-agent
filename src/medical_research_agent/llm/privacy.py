"""Privacy gates for external LLM calls."""

from __future__ import annotations

from medical_research_agent.config import AppSettings
from medical_research_agent.schemas import SourceType


PRIVATE_SOURCE_TYPES = {
    SourceType.USER_UPLOADED_PRIVATE,
    SourceType.INTERNAL_PRIVATE,
}


def assert_external_llm_allowed(source_types: list[SourceType], settings: AppSettings) -> None:
    """Raise when a request would send disallowed source content externally."""

    if not source_types:
        return

    has_private_source = any(source_type in PRIVATE_SOURCE_TYPES for source_type in source_types)
    if has_private_source and not settings.allow_external_llm_for_private_sources:
        raise PermissionError(
            "External LLM call blocked because request includes private source content. "
            "Set MEDICAL_RESEARCH_ALLOW_EXTERNAL_LLM_FOR_PRIVATE_SOURCES=true only after explicit approval."
        )

    has_public_source = any(source_type not in PRIVATE_SOURCE_TYPES for source_type in source_types)
    if has_public_source and not settings.allow_external_llm_for_public_sources:
        raise PermissionError("External LLM call blocked because public-source external calls are disabled.")
