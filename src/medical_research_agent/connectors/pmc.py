"""NCBI PMC open full-text connector."""

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
from medical_research_agent.connectors.literature_access import attach_access_metadata
from medical_research_agent.schemas import SourceRecord, SourceType
from medical_research_agent.source_contracts import FreeAccessStatus


class PMCFullTextConnector(SourceConnector):
    """Search PubMed Central as an item-level open full-text route."""

    name = "pmc"
    search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    summary_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"

    def __init__(
        self,
        *,
        client: httpx.Client | None = None,
        email: str | None = None,
        api_key: str | None = None,
        timeout_seconds: float = 20.0,
    ) -> None:
        super().__init__(client=client, timeout_seconds=timeout_seconds)
        self.email = email
        self.api_key = api_key

    def search(self, request: SearchRequest) -> list[SourceRecord]:
        try:
            ids = self._search_ids(request)
            if not ids:
                return []
            summaries = self._fetch_summaries(ids)
        except httpx.HTTPStatusError as exc:
            raise connector_error_from_http_status(self.name, exc) from exc
        except httpx.HTTPError as exc:
            raise ConnectorError(self.name, f"network request failed: {exc}") from exc
        except ValueError as exc:
            raise ConnectorError(self.name, f"invalid response: {exc}", kind=ConnectorErrorKind.PARSER_BLOCKED_OR_WAF) from exc
        return [self._summary_to_source(summary, request) for summary in summaries]

    def _base_params(self) -> dict[str, str]:
        params = {"retmode": "json"}
        if self.email:
            params["email"] = self.email
        if self.api_key:
            params["api_key"] = self.api_key
        return params

    def _search_ids(self, request: SearchRequest) -> list[str]:
        params = {
            **self._base_params(),
            "db": "pmc",
            "term": request.query,
            "retmax": str(request.limit),
            "sort": "relevance",
        }
        response = self._client.get(self.search_url, params=params)
        response.raise_for_status()
        data = json_object_response(response, self.name)
        raw_ids = object_value(data.get("esearchresult")).get("idlist")
        return [str(item) for item in raw_ids] if isinstance(raw_ids, list) else []

    def _fetch_summaries(self, ids: list[str]) -> list[dict[str, Any]]:
        params = {
            **self._base_params(),
            "db": "pmc",
            "id": ",".join(ids),
        }
        response = self._client.get(self.summary_url, params=params)
        response.raise_for_status()
        data = json_object_response(response, self.name)
        result = object_value(data.get("result"))
        uids = result.get("uids")
        if not isinstance(uids, list):
            return []
        return object_items([result.get(str(item_id)) for item_id in uids])

    def _summary_to_source(self, summary: dict[str, Any], request: SearchRequest) -> SourceRecord:
        pmcid = _pmcid(summary)
        url = f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/" if pmcid else None
        source = SourceRecord(
            task_id=request.task_id,
            source_type=SourceType.PUBLIC_LITERATURE,
            title=_clean_text(summary.get("title")) or f"PMC record {summary.get('uid', '')}".strip(),
            url=url,
            publisher=_clean_text(summary.get("fulljournalname")) or _clean_text(summary.get("source")) or "PubMed Central",
            authors=[],
            published_at=_parse_date(_clean_text(summary.get("pubdate")) or _clean_text(summary.get("epubdate"))),
            search_query=request.query,
            credibility_note="PubMed Central open full-text record from NCBI E-utilities.",
            metadata={
                "connector": self.name,
                "pmc_uid": summary.get("uid"),
                "pmcid": pmcid,
                "pubdate": summary.get("pubdate"),
            },
        )
        return attach_access_metadata(
            source,
            status=FreeAccessStatus.OPEN_FULL_TEXT if pmcid else FreeAccessStatus.METADATA_ONLY,
            evidence_note="PMC item-level open full-text URL found." if pmcid else "PMC metadata retained without a usable PMCID URL.",
        )


def _pmcid(summary: dict[str, Any]) -> str | None:
    for article_id in object_items(summary.get("articleids")):
        if article_id.get("idtype") != "pmcid":
            continue
        value = article_id.get("value")
        if isinstance(value, str) and value.strip():
            cleaned = value.strip()
            return cleaned if cleaned.upper().startswith("PMC") else f"PMC{cleaned}"
    uid = summary.get("uid")
    return f"PMC{uid}" if isinstance(uid, str) and uid.strip() else None


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    parts = value.replace("-", " ").split()
    if not parts or not parts[0].isdigit():
        return None
    try:
        return datetime(int(parts[0]), _month_number(parts[1]) if len(parts) > 1 else 1, 1, tzinfo=timezone.utc)
    except ValueError:
        return None


def _month_number(value: str) -> int:
    months = {
        "jan": 1,
        "feb": 2,
        "mar": 3,
        "apr": 4,
        "may": 5,
        "jun": 6,
        "jul": 7,
        "aug": 8,
        "sep": 9,
        "oct": 10,
        "nov": 11,
        "dec": 12,
    }
    if value.isdigit():
        return max(1, min(12, int(value)))
    return months.get(value[:3].lower(), 1)


def _clean_text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    return value.strip() or None
