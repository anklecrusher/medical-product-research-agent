"""Access metadata helpers for open-literature connector records."""

from __future__ import annotations

from urllib.parse import urlparse

from medical_research_agent.schemas import SourceRecord
from medical_research_agent.source_contracts import AccessCheck, CitationEligibility, FreeAccessStatus


def attach_access_metadata(
    source: SourceRecord,
    *,
    status: FreeAccessStatus,
    evidence_note: str,
) -> SourceRecord:
    """Attach shared AccessCheck and CitationEligibility metadata to a source."""

    access_check = AccessCheck(
        source_id=source.source_id,
        url=str(source.url) if source.url is not None else None,
        status=status,
        checked_by="open_literature_connector",
        evidence_note=evidence_note,
    )
    metadata = {
        **source.metadata,
        "access_check": access_check.model_dump(mode="json"),
        "citation_eligibility": CitationEligibility.from_access_check(access_check).model_dump(mode="json"),
    }
    return source.model_copy(update={"metadata": metadata})


def valid_http_url(value: str | None) -> str | None:
    """Return a clean HTTP(S) URL or None for malformed/missing values."""

    if value is None:
        return None
    cleaned = value.strip()
    parsed = urlparse(cleaned)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    return cleaned


def doi_url(value: str | None) -> str | None:
    """Normalize DOI payloads into a DOI resolver URL."""

    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    if cleaned.startswith("http://") or cleaned.startswith("https://"):
        return cleaned
    return f"https://doi.org/{cleaned}"
