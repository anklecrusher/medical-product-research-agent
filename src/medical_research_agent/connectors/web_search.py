"""Lightweight public web search connector for vendor/public document leads."""

from __future__ import annotations

from typing import Any
from urllib.parse import parse_qs, urlparse

import httpx
from bs4 import BeautifulSoup

from medical_research_agent.connectors.base import (
    ConnectorError,
    SearchRequest,
    SourceConnector,
    connector_error_from_http_status,
)
from medical_research_agent.schemas import DocumentFormat, SourceRecord, SourceType


class DuckDuckGoHTMLSearchConnector(SourceConnector):
    """Minimal no-key web search connector using DuckDuckGo HTML results."""

    name = "duckduckgo_html"
    search_url = "https://html.duckduckgo.com/html/"

    def __init__(
        self,
        *,
        client: httpx.Client | None = None,
        timeout_seconds: float = 20.0,
        source_type: SourceType = SourceType.PUBLIC_WEB,
    ) -> None:
        self._client = client or httpx.Client(timeout=timeout_seconds, follow_redirects=True)
        self.source_type = source_type

    def search(self, request: SearchRequest) -> list[SourceRecord]:
        try:
            response = self._client.get(self.search_url, params={"q": request.query})
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise connector_error_from_http_status(self.name, exc) from exc
        except httpx.HTTPError as exc:
            raise ConnectorError(self.name, f"network request failed: {exc}") from exc

        return self._parse_results(response.text, request)

    def _parse_results(self, html: str, request: SearchRequest) -> list[SourceRecord]:
        soup = BeautifulSoup(html, "html.parser")
        anchors = soup.select("a.result__a")
        if not anchors:
            anchors = soup.select("a[href]")

        records: list[SourceRecord] = []
        for rank, anchor in enumerate(anchors, start=1):
            href = anchor.get("href")
            title = " ".join(anchor.get_text(" ", strip=True).split())
            url = _clean_duckduckgo_url(href)
            if not url or not title:
                continue

            parsed = urlparse(url)
            records.append(
                SourceRecord(
                    task_id=request.task_id,
                    source_type=self.source_type,
                    title=title,
                    url=url,
                    publisher=parsed.netloc,
                    search_query=request.query,
                    credibility_note="Public web search result; source credibility must be checked downstream.",
                    metadata={
                        "connector": self.name,
                        "rank": rank,
                        "document_format_hint": DocumentFormat.PDF
                        if parsed.path.lower().endswith(".pdf")
                        else DocumentFormat.WEB_PAGE,
                    },
                )
            )
            if len(records) >= request.limit:
                break
        return records


def _clean_duckduckgo_url(href: str | None) -> str | None:
    if not href:
        return None
    parsed = urlparse(href)
    query = parse_qs(parsed.query)
    if "uddg" in query and query["uddg"]:
        return query["uddg"][0]
    if parsed.scheme in {"http", "https"}:
        return href
    return None
