"""Crossref literature metadata connector."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx

from medical_research_agent.connectors.base import (
    ConnectorError,
    ConnectorErrorKind,
    SearchRequest,
    SourceConnector,
    connector_error_from_http_status,
)
from medical_research_agent.schemas import SourceRecord, SourceType


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
        self._client = client or httpx.Client(timeout=timeout_seconds, follow_redirects=True)
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
            items = response.json().get("message", {}).get("items", [])
        except httpx.HTTPStatusError as exc:
            raise connector_error_from_http_status(self.name, exc) from exc
        except httpx.HTTPError as exc:
            raise ConnectorError(self.name, f"network request failed: {exc}") from exc
        except ValueError as exc:
            raise ConnectorError(self.name, f"invalid response: {exc}", kind=ConnectorErrorKind.PARSER_BLOCKED_OR_WAF) from exc

        return [self._item_to_source(item, request) for item in items]

    def _item_to_source(self, item: dict[str, Any], request: SearchRequest) -> SourceRecord:
        title = _first_text(item.get("title")) or item.get("DOI") or "Untitled Crossref work"
        doi = item.get("DOI")
        url = item.get("URL") or (f"https://doi.org/{doi}" if doi else None)
        container = _first_text(item.get("container-title"))
        authors = [_format_author(author) for author in item.get("author", [])]
        authors = [author for author in authors if author]

        return SourceRecord(
            task_id=request.task_id,
            source_type=SourceType.PUBLIC_LITERATURE,
            title=title,
            url=url,
            publisher=item.get("publisher") or container or "Crossref",
            authors=authors,
            published_at=_date_from_crossref_parts(
                item.get("published-print")
                or item.get("published-online")
                or item.get("published")
                or item.get("issued")
            ),
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


def _first_text(values: Any) -> str | None:
    if isinstance(values, list) and values:
        return str(values[0]).strip() or None
    if isinstance(values, str):
        return values.strip() or None
    return None


def _format_author(author: dict[str, Any]) -> str:
    parts = [author.get("given"), author.get("family")]
    value = " ".join(part.strip() for part in parts if isinstance(part, str) and part.strip())
    return value or str(author.get("name", "")).strip()


def _date_from_crossref_parts(date_payload: dict[str, Any] | None) -> datetime | None:
    parts = (date_payload or {}).get("date-parts") or []
    if not parts or not parts[0]:
        return None

    values = list(parts[0])
    year = int(values[0])
    month = int(values[1]) if len(values) > 1 else 1
    day = int(values[2]) if len(values) > 2 else 1
    return datetime(year, month, day, tzinfo=timezone.utc)
