"""Crossref literature metadata connector."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any

import httpx
from pydantic import ValidationError

from medical_research_agent.connectors.base import (
    ConnectorError,
    ConnectorErrorKind,
    SearchRequest,
    SourceConnector,
    connector_error_from_http_status,
)
from medical_research_agent.connectors.literature_access import attach_access_metadata, valid_http_url
from medical_research_agent.schemas import SourceRecord, SourceType
from medical_research_agent.source_contracts import FreeAccessStatus


class CrossrefConnector(SourceConnector):
    """Minimal Crossref works search connector."""

    name = "crossref"
    works_url = "https://api.crossref.org/works"

    def __init__(
        self,
        *,
        client: httpx.Client | None = None,
        mailto: str | None = None,
        timeout_seconds: float = 20.0,
    ) -> None:
        super().__init__(client=client, timeout_seconds=timeout_seconds)
        self.mailto = mailto

    def search(self, request: SearchRequest) -> list[SourceRecord]:
        params: dict[str, str] = {
            "query": request.query,
            "rows": str(request.limit),
            "sort": "relevance",
            "order": "desc",
        }
        if self.mailto:
            params["mailto"] = self.mailto

        try:
            response = self._client.get(self.works_url, params=params)
            response.raise_for_status()
            items = _response_items(response.json())
        except httpx.HTTPStatusError as exc:
            raise connector_error_from_http_status(self.name, exc) from exc
        except httpx.HTTPError as exc:
            raise ConnectorError(self.name, f"network request failed: {exc}") from exc
        except ValueError as exc:
            raise ConnectorError(self.name, f"invalid response: {exc}", kind=ConnectorErrorKind.PARSER_BLOCKED_OR_WAF) from exc

        records: list[SourceRecord] = []
        for item in items:
            record = self._item_to_source(item, request)
            if record is not None:
                records.append(record)
        return records

    def _item_to_source(self, item: Mapping[str, Any], request: SearchRequest) -> SourceRecord | None:
        raw_doi = item.get("DOI")
        doi = _text_value(raw_doi)
        raw_url = item.get("URL")
        url = valid_http_url(raw_url) if isinstance(raw_url, str) else None
        raw_publisher = item.get("publisher")
        publisher = _text_value(raw_publisher)
        if (raw_doi is not None and doi is None) or (raw_url is not None and url is None) or (
            raw_publisher is not None and publisher is None
        ):
            return None

        title = _first_text(item.get("title")) or doi or "Untitled Crossref work"
        if url is None and doi is not None:
            url = f"https://doi.org/{doi}"
        container = _first_text(item.get("container-title"))
        authors = _authors_from_item(item)

        try:
            source = SourceRecord(
                task_id=request.task_id,
                source_type=SourceType.PUBLIC_LITERATURE,
                title=title,
                url=url,
                publisher=publisher or container or "Crossref",
                authors=authors,
                published_at=_date_from_crossref_candidates(item),
                search_query=request.query,
                credibility_note="Crossref public scholarly metadata.",
                metadata={
                    "connector": self.name,
                    "doi": doi,
                    "type": item.get("type"),
                    "container_title": container,
                    "is_referenced_by_count": item.get("is-referenced-by-count"),
                    "score": item.get("score"),
                },
            )
        except ValidationError:
            return None
        return attach_access_metadata(
            source,
            status=FreeAccessStatus.METADATA_ONLY,
            evidence_note="Crossref provides scholarly metadata only; free item-level access must be verified elsewhere.",
        )


def _first_text(values: Any) -> str | None:
    if isinstance(values, list) and values:
        return str(values[0]).strip() or None
    if isinstance(values, str):
        return values.strip() or None
    return None


def _response_items(payload: Any) -> list[Mapping[str, Any]]:
    if not isinstance(payload, Mapping):
        raise ConnectorError("crossref", "invalid response root", kind=ConnectorErrorKind.PARSER_BLOCKED_OR_WAF)
    message = payload.get("message")
    if not isinstance(message, Mapping):
        raise ConnectorError("crossref", "invalid response message", kind=ConnectorErrorKind.PARSER_BLOCKED_OR_WAF)
    items = message.get("items")
    if not isinstance(items, list):
        raise ConnectorError("crossref", "invalid response items", kind=ConnectorErrorKind.PARSER_BLOCKED_OR_WAF)
    return [item for item in items if isinstance(item, Mapping)]


def _authors_from_item(item: Mapping[str, Any]) -> list[str]:
    raw_authors = item.get("author")
    if not isinstance(raw_authors, list):
        return []
    return [author for author in (_format_author(item) for item in raw_authors if isinstance(item, Mapping)) if author]


def _format_author(author: Mapping[str, Any]) -> str:
    parts = [author.get("given"), author.get("family")]
    value = " ".join(part.strip() for part in parts if isinstance(part, str) and part.strip())
    return value or str(author.get("name", "")).strip()


def _date_from_crossref_parts(date_payload: Mapping[str, Any] | None) -> datetime | None:
    if not isinstance(date_payload, Mapping):
        return None

    parts = date_payload.get("date-parts") or []
    if not isinstance(parts, list) or not parts or not isinstance(parts[0], list) or not parts[0]:
        return None

    values = parts[0]
    try:
        year = int(values[0])
        month = int(values[1]) if len(values) > 1 else 1
        day = int(values[2]) if len(values) > 2 else 1
        return datetime(year, month, day, tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def _date_from_crossref_candidates(item: Mapping[str, Any]) -> datetime | None:
    for field_name in ("published-print", "published-online", "published", "issued"):
        date_value = _date_from_crossref_parts(item.get(field_name))
        if date_value is not None:
            return date_value
    return None


def _text_value(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    return value.strip() or None
