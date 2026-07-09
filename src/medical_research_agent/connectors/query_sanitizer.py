"""Sanitize planner queries before sending them to strict public APIs."""

from __future__ import annotations

import re
from typing import Any, Final, Iterable

from medical_research_agent.connectors.base import SearchRequest

_ASCII_RUN_RE: Final = re.compile(r"[A-Za-z0-9][A-Za-z0-9 +/()._-]*")
_PRODUCT_CODE_RE: Final = re.compile(r"\b[A-Z0-9]{2,4}\b")
_PRODUCT_CODE_STOPWORDS: Final = frozenset({"DBS", "SCS", "FDA", "IFU", "NCT", "UI"})
_SAFE_FALLBACK_TERM: Final = "medical device"


def sanitized_api_query(request: SearchRequest, *, max_terms: int = 6) -> str:
    """Return an ASCII API-facing query from expansion metadata or mixed query text."""

    terms = list(_metadata_terms(request.metadata))
    if not terms:
        terms = list(_ascii_terms_from_text(request.query))
    cleaned = list(_clean_terms(terms))
    if not cleaned:
        return _SAFE_FALLBACK_TERM
    return " ".join(cleaned[:max_terms])


def product_codes_from_request(request: SearchRequest) -> tuple[str, ...]:
    """Extract short uppercase product-code-like tokens only."""

    candidates = [
        token
        for term in (*_metadata_terms(request.metadata), *_ascii_terms_from_text(request.query))
        for token in _PRODUCT_CODE_RE.findall(term)
    ]
    return tuple(
        token
        for token in _unique(candidates)
        if any(char.isalpha() for char in token) and token not in _PRODUCT_CODE_STOPWORDS
    )


def _metadata_terms(metadata: dict[str, Any] | None) -> tuple[str, ...]:
    if metadata is None:
        return ()
    value = metadata.get("expanded_terms")
    if not isinstance(value, list | tuple):
        return ()
    return tuple(item for item in value if isinstance(item, str))


def _ascii_terms_from_text(text: str) -> tuple[str, ...]:
    return tuple(match.group(0) for match in _ASCII_RUN_RE.finditer(text))


def _clean_terms(terms: Iterable[str]) -> tuple[str, ...]:
    return _unique(cleaned for term in terms for cleaned in (_clean_term(term),) if cleaned)


def _clean_term(term: str) -> str:
    ascii_only = "".join(char if ord(char) < 128 else " " for char in term)
    safe_chars = "".join(char if char.isalnum() or char in " +/()._-" else " " for char in ascii_only)
    cleaned = " ".join(safe_chars.replace("_", " ").split())
    if not any(char.isalpha() for char in cleaned):
        return ""
    return cleaned


def _unique(values: Iterable[str]) -> tuple[str, ...]:
    result: list[str] = []
    for value in values:
        if value not in result:
            result.append(value)
    return tuple(result)
