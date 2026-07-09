"""Semantic Scholar literature connector."""

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
from medical_research_agent.connectors.query_sanitizer import sanitized_api_query
from medical_research_agent.schemas import SourceRecord, SourceType


class SemanticScholarConnector(SourceConnector):
    """Minimal Semantic Scholar search connector with optional API key support."""

    name = "semantic_scholar"
    search_url = "https://api.semanticscholar.org/graph/v1/paper/search"

    def __init__(
        self,
        *,
        client: httpx.Client | None = None,
        api_key: str | None = None,
        timeout_seconds: float = 20.0,
    ) -> None:
        self._client = client or httpx.Client(timeout=timeout_seconds, follow_redirects=True)
        self.api_key = api_key

    def search(self, request: SearchRequest) -> list[SourceRecord]:
        params = {
            "query": sanitized_api_query(request),
            "limit": str(request.limit),
            "fields": "title,authors,year,venue,url,externalIds,publicationDate,abstract,citationCount",
        }
        headers = {"x-api-key": self.api_key} if self.api_key else None
        try:
            response = self._client.get(self.search_url, params=params, headers=headers)
            response.raise_for_status()
            items = response.json().get("data", [])
        except httpx.HTTPStatusError as exc:
            raise connector_error_from_http_status(self.name, exc) from exc
        except httpx.HTTPError as exc:
            raise ConnectorError(self.name, f"network request failed: {exc}") from exc
        except ValueError as exc:
            raise ConnectorError(self.name, f"invalid response: {exc}", kind=ConnectorErrorKind.PARSER_BLOCKED_OR_WAF) from exc

        return [self._item_to_source(item, request) for item in items]

    def _item_to_source(self, item: dict[str, Any], request: SearchRequest) -> SourceRecord:
        external_ids = item.get("externalIds") or {}
        doi = external_ids.get("DOI")
        url = item.get("url") or (f"https://doi.org/{doi}" if doi else None)
        authors = [
            author.get("name", "").strip()
            for author in item.get("authors", [])
            if author.get("name", "").strip()
        ]

        return SourceRecord(
            task_id=request.task_id,
            source_type=SourceType.PUBLIC_LITERATURE,
            title=item.get("title") or "Untitled Semantic Scholar paper",
            url=url,
            publisher=item.get("venue") or "Semantic Scholar",
            authors=authors,
            published_at=_parse_publication_date(item.get("publicationDate"), item.get("year")),
            search_query=request.query,
            credibility_note="Semantic Scholar public scholarly metadata.",
            metadata={
                "connector": self.name,
                "paper_id": item.get("paperId"),
                "doi": doi,
                "pubmed_id": external_ids.get("PubMed"),
                "venue": item.get("venue"),
                "year": item.get("year"),
                "citation_count": item.get("citationCount"),
                "abstract": item.get("abstract"),
            },
        )


def _parse_publication_date(value: str | None, year: int | None) -> datetime | None:
    if value:
        parts = value.split("-")
        try:
            return datetime(
                int(parts[0]),
                int(parts[1]) if len(parts) > 1 else 1,
                int(parts[2]) if len(parts) > 2 else 1,
                tzinfo=timezone.utc,
            )
        except ValueError:
            return None
    if year:
        return datetime(int(year), 1, 1, tzinfo=timezone.utc)
    return None
