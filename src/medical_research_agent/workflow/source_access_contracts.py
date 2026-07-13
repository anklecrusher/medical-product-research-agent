"""Preserve restrictive connector access contracts during workflow verification."""

from __future__ import annotations

from typing import Protocol

from pydantic import ValidationError

from medical_research_agent.schemas import SourceRecord
from medical_research_agent.source_contracts import AccessCheck, CitationEligibility


class SourceAccessChecker(Protocol):
    """Check the current access state of a public source."""

    def verify(self, source: SourceRecord) -> AccessCheck:
        """Return the generic verifier's current access observation."""


def effective_access_check(source: SourceRecord, verifier: SourceAccessChecker) -> AccessCheck:
    """Keep a valid declared non-citable contract instead of upgrading it generically."""

    declared = _declared_access_check(source)
    if declared is not None and not CitationEligibility.from_access_check(declared).eligible:
        return declared
    return verifier.verify(source)


def _declared_access_check(source: SourceRecord) -> AccessCheck | None:
    raw_access_check = source.metadata.get("access_check")
    if not isinstance(raw_access_check, dict):
        return None
    try:
        return AccessCheck.model_validate(raw_access_check)
    except ValidationError:
        return None
