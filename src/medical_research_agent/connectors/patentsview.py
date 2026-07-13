"""PatentsView public patent source connector."""

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
    json_object_response,
    object_items,
)
from medical_research_agent.connectors.query_sanitizer import sanitized_api_query
from medical_research_agent.public_sources import PublicSourceCategory
from medical_research_agent.schemas import SourceRecord, SourceType


class PatentsViewConnector(SourceConnector):
    """Search free public patent metadata through PatentsView."""

    name = "patentsview"
    search_url = "https://search.patentsview.org/api/v1/patent/"

    def __init__(self, *, client: httpx.Client | None = None, timeout_seconds: float = 20.0) -> None:
        super().__init__(client=client, timeout_seconds=timeout_seconds)

    def search(self, request: SearchRequest) -> list[SourceRecord]:
        params = {
            "q": sanitized_api_query(request),
            "f": "patent_id,patent_title,patent_date,assignees.assignee_organization",
            "o": f"size:{request.limit}",
        }
        try:
            response = self._client.get(self.search_url, params=params)
            response.raise_for_status()
            payload = json_object_response(response, self.name)
            patents = object_items(payload.get("patents"))
        except httpx.HTTPStatusError as exc:
            raise connector_error_from_http_status(self.name, exc) from exc
        except httpx.HTTPError as exc:
            raise ConnectorError(self.name, f"network request failed: {exc}") from exc
        except ValueError as exc:
            raise ConnectorError(
                self.name,
                f"invalid response: {exc}",
                kind=ConnectorErrorKind.PARSER_BLOCKED_OR_WAF,
            ) from exc

        return [self._patent_to_source(item, request) for item in patents[: request.limit]]

    def _patent_to_source(self, item: dict[str, Any], request: SearchRequest) -> SourceRecord:
        patent_id = _text(item.get("patent_id"))
        title = _text(item.get("patent_title")) or patent_id or "PatentsView patent record"
        assignees = _assignee_names(item.get("assignees"))

        return SourceRecord(
            task_id=request.task_id,
            source_type=SourceType.PUBLIC_WEB,
            title=title,
            url=f"https://patents.google.com/patent/{patent_id}" if patent_id else self.search_url,
            publisher="PatentsView",
            authors=list(assignees),
            published_at=_parse_date(_text(item.get("patent_date"))),
            search_query=request.query,
            credibility_note="Free public patent metadata discovered via PatentsView.",
            metadata={
                "connector": self.name,
                "public_source_category": PublicSourceCategory.PATENT,
                "patent_id": patent_id,
                "assignees": list(assignees),
                "patentsview_url": self.search_url,
            },
        )


def _assignee_names(values: Any) -> tuple[str, ...]:
    if not isinstance(values, list):
        return ()
    result: list[str] = []
    for value in values:
        if not isinstance(value, dict):
            continue
        name = _text(value.get("assignee_organization"))
        if name:
            result.append(name)
    return tuple(result)


def _text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    return cleaned or None


def _parse_date(value: str | None) -> datetime | None:
    if value is None:
        return None
    try:
        parts = value.split("-")
        return datetime(
            int(parts[0]),
            int(parts[1]) if len(parts) > 1 else 1,
            int(parts[2]) if len(parts) > 2 else 1,
            tzinfo=timezone.utc,
        )
    except ValueError:
        return None
