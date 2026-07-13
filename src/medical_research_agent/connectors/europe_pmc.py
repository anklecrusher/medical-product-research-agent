"""Europe PMC open literature connector."""

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


class EuropePMCConnector(SourceConnector):
    """Search Europe PMC and prefer record-level open full-text URLs."""

    name = "europe_pmc"
    search_url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"

    def __init__(self, *, client: httpx.Client | None = None, timeout_seconds: float = 20.0) -> None:
        super().__init__(client=client, timeout_seconds=timeout_seconds)

    def search(self, request: SearchRequest) -> list[SourceRecord]:
        params = {
            "query": request.query,
            "format": "json",
            "pageSize": str(request.limit),
            "resultType": "core",
        }
        try:
            response = self._client.get(self.search_url, params=params)
            response.raise_for_status()
            payload = json_object_response(response, self.name)
            items = object_items(object_value(payload.get("resultList")).get("result"))
        except httpx.HTTPStatusError as exc:
            raise connector_error_from_http_status(self.name, exc) from exc
        except httpx.HTTPError as exc:
            raise ConnectorError(self.name, f"network request failed: {exc}") from exc
        except ValueError as exc:
            raise ConnectorError(self.name, f"invalid response: {exc}", kind=ConnectorErrorKind.PARSER_BLOCKED_OR_WAF) from exc
        return [self._item_to_source(item, request) for item in items]

    def _item_to_source(self, item: dict[str, Any], request: SearchRequest) -> SourceRecord:
        pmcid = _clean_text(item.get("pmcid"))
        full_text_url = _first_full_text_url(item)
        record_url = f"https://europepmc.org/articles/{pmcid}" if pmcid else None
        doi = _clean_text(item.get("doi"))
        url = full_text_url or record_url or doi_url(doi)
        status = FreeAccessStatus.OPEN_FULL_TEXT if full_text_url or record_url else FreeAccessStatus.METADATA_ONLY
        source = SourceRecord(
            task_id=request.task_id,
            source_type=SourceType.PUBLIC_LITERATURE,
            title=_clean_text(item.get("title")) or f"Europe PMC record {item.get('id', '')}".strip(),
            url=url,
            publisher=_clean_text(item.get("journalTitle")) or "Europe PMC",
            authors=_authors_from_string(item.get("authorString")),
            published_at=_date_from_year(item.get("pubYear")),
            search_query=request.query,
            credibility_note="Europe PMC public literature and open full-text metadata.",
            metadata={
                "connector": self.name,
                "europe_pmc_id": item.get("id"),
                "pmid": item.get("pmid"),
                "pmcid": pmcid,
                "doi": doi,
                "is_open_access": item.get("isOpenAccess"),
            },
        )
        return attach_access_metadata(
            source,
            status=status,
            evidence_note="Europe PMC open full-text URL found." if status is FreeAccessStatus.OPEN_FULL_TEXT else "Europe PMC record retained as metadata-only; no free full-text URL found.",
        )


def _first_full_text_url(item: dict[str, Any]) -> str | None:
    urls = object_items(object_value(item.get("fullTextUrlList")).get("fullTextUrl"))
    for entry in urls:
        url = valid_http_url(_clean_text(entry.get("url")))
        if url is not None:
            return url
    return None


def _authors_from_string(value: Any) -> list[str]:
    if not isinstance(value, str):
        return []
    return [author.strip() for author in value.split(",") if author.strip()]


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
