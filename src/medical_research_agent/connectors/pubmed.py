"""PubMed connector using NCBI E-utilities."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx

from medical_research_agent.connectors.base import ConnectorError, SearchRequest, SourceConnector
from medical_research_agent.schemas import SourceRecord, SourceType


class PubMedConnector(SourceConnector):
    """Minimal PubMed search connector backed by ESearch and ESummary."""

    name = "pubmed"
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
        self._client = client or httpx.Client(timeout=timeout_seconds, follow_redirects=True)
        self.email = email
        self.api_key = api_key

    def search(self, request: SearchRequest) -> list[SourceRecord]:
        try:
            ids = self._search_ids(request)
            if not ids:
                return []
            summaries = self._fetch_summaries(ids)
        except httpx.HTTPError as exc:
            raise ConnectorError(self.name, f"network request failed: {exc}") from exc
        except ValueError as exc:
            raise ConnectorError(self.name, f"invalid response: {exc}") from exc

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
            "db": "pubmed",
            "term": request.query,
            "retmax": str(request.limit),
            "sort": "relevance",
        }
        response = self._client.get(self.search_url, params=params)
        response.raise_for_status()
        data = response.json()
        return [str(item) for item in data.get("esearchresult", {}).get("idlist", [])]

    def _fetch_summaries(self, pmids: list[str]) -> list[dict[str, Any]]:
        params = {
            **self._base_params(),
            "db": "pubmed",
            "id": ",".join(pmids),
        }
        response = self._client.get(self.summary_url, params=params)
        response.raise_for_status()
        data = response.json()
        result = data.get("result", {})
        return [result[pmid] for pmid in result.get("uids", []) if pmid in result]

    def _summary_to_source(self, summary: dict[str, Any], request: SearchRequest) -> SourceRecord:
        pmid = str(summary.get("uid", "")).strip()
        authors = [
            author.get("name", "").strip()
            for author in summary.get("authors", [])
            if author.get("name", "").strip()
        ]
        article_ids = summary.get("articleids", [])
        doi = next(
            (item.get("value") for item in article_ids if item.get("idtype") == "doi" and item.get("value")),
            None,
        )
        published_at = _parse_pubmed_date(summary.get("pubdate") or summary.get("epubdate"))
        url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else None

        return SourceRecord(
            task_id=request.task_id,
            source_type=SourceType.PUBLIC_LITERATURE,
            title=summary.get("title") or f"PubMed record {pmid}",
            url=url,
            publisher=summary.get("source") or "PubMed",
            authors=authors,
            published_at=published_at,
            search_query=request.query,
            credibility_note="PubMed literature metadata from NCBI E-utilities.",
            metadata={
                "connector": self.name,
                "pmid": pmid,
                "doi": doi,
                "journal": summary.get("fulljournalname"),
                "pubdate": summary.get("pubdate"),
                "volume": summary.get("volume"),
                "issue": summary.get("issue"),
                "pages": summary.get("pages"),
            },
        )


def _parse_pubmed_date(value: str | None) -> datetime | None:
    if not value:
        return None
    parts = value.replace("-", " ").split()
    if not parts or not parts[0].isdigit():
        return None

    year = int(parts[0])
    month = _month_number(parts[1]) if len(parts) > 1 else 1
    day = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 1
    return datetime(year, month, day, tzinfo=timezone.utc)


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
