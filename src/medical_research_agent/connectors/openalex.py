"""OpenAlex open-access literature metadata connector."""

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
    object_value,
)
from medical_research_agent.connectors.literature_access import attach_access_metadata, doi_url, valid_http_url
from medical_research_agent.schemas import SourceRecord, SourceType
from medical_research_agent.source_contracts import FreeAccessStatus


class OpenAlexConnector(SourceConnector):
    """Search OpenAlex works and expose item-level OA URLs when present."""

    name = "openalex"
    works_url = "https://api.openalex.org/works"

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
        params = {
            "search": request.query,
            "per-page": str(request.limit),
        }
        if self.mailto:
            params["mailto"] = self.mailto
        try:
            response = self._client.get(self.works_url, params=params)
            response.raise_for_status()
            payload = json_object_response(response, self.name)
            items = object_items(payload.get("results"))
        except httpx.HTTPStatusError as exc:
            raise connector_error_from_http_status(self.name, exc) from exc
        except httpx.HTTPError as exc:
            raise ConnectorError(self.name, f"network request failed: {exc}") from exc
        except ValueError as exc:
            raise ConnectorError(self.name, f"invalid response: {exc}", kind=ConnectorErrorKind.PARSER_BLOCKED_OR_WAF) from exc
        return [self._item_to_source(item, request) for item in items]

    def _item_to_source(self, item: dict[str, Any], request: SearchRequest) -> SourceRecord:
        location = object_value(item.get("primary_location"))
        oa = object_value(item.get("open_access"))
        doi = doi_url(_clean_text(item.get("doi")))
        pdf_url = valid_http_url(_clean_text(location.get("pdf_url")))
        oa_url = valid_http_url(_clean_text(oa.get("oa_url")))
        landing_url = valid_http_url(_clean_text(location.get("landing_page_url")))
        url = pdf_url or oa_url or landing_url or doi
        status = _status_for_url(pdf_url=pdf_url, oa_url=oa_url, landing_url=landing_url, is_oa=bool(oa.get("is_oa")))
        source = SourceRecord(
            task_id=request.task_id,
            source_type=SourceType.PUBLIC_LITERATURE,
            title=_clean_text(item.get("display_name")) or "Untitled OpenAlex work",
            url=url,
            publisher=_publisher(location),
            authors=_authors(item.get("authorships")),
            published_at=_date_from_year(item.get("publication_year")),
            search_query=request.query,
            credibility_note="OpenAlex public scholarly metadata with open-access URL fields.",
            metadata={
                "connector": self.name,
                "openalex_id": item.get("id"),
                "doi": doi,
                "is_oa": oa.get("is_oa"),
                "oa_status": oa.get("oa_status"),
                "oa_url": oa_url,
                "pdf_url": pdf_url,
                "landing_page_url": landing_url,
            },
        )
        return attach_access_metadata(
            source,
            status=status,
            evidence_note="OpenAlex item-level OA URL found." if status is not FreeAccessStatus.METADATA_ONLY else "OpenAlex record retained as metadata-only; no valid free item-level URL found.",
        )


def _status_for_url(
    *,
    pdf_url: str | None,
    oa_url: str | None,
    landing_url: str | None,
    is_oa: bool,
) -> FreeAccessStatus:
    if pdf_url is not None:
        return FreeAccessStatus.PDF_ACCESSIBLE
    if oa_url is not None:
        return FreeAccessStatus.OPEN_ACCESS
    if landing_url is not None and is_oa:
        return FreeAccessStatus.FREE_LANDING_PAGE
    return FreeAccessStatus.METADATA_ONLY


def _authors(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    names: list[str] = []
    for item in values:
        if not isinstance(item, dict):
            continue
        author = item.get("author")
        if not isinstance(author, dict):
            continue
        name = _clean_text(author.get("display_name"))
        if name is not None:
            names.append(name)
    return names


def _publisher(location: dict[str, Any]) -> str:
    source = location.get("source")
    if isinstance(source, dict):
        name = _clean_text(source.get("display_name"))
        if name is not None:
            return name
    return "OpenAlex"


def _date_from_year(value: Any) -> datetime | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text.isdigit():
        return None
    year = int(text)
    return datetime(year, 1, 1, tzinfo=timezone.utc) if 1 <= year <= 9999 else None


def _clean_text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    return value.strip() or None
