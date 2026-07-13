"""Connector helpers for user-supplied public URLs."""

from __future__ import annotations

from urllib.parse import urlparse

import httpx

from medical_research_agent.connectors.base import ConnectorError
from medical_research_agent.schemas import DocumentFormat, SourceRecord, SourceType
from medical_research_agent.url_security import PublicURLFetcherOwner, request_public_url, validate_public_http_url


class URLSourceConnector(PublicURLFetcherOwner):
    """Create and lightly validate public URL source records."""

    name = "url"

    def __init__(self, *, transport: httpx.MockTransport | None = None, timeout_seconds: float = 20.0) -> None:
        super().__init__(transport=transport, timeout_seconds=timeout_seconds)

    def from_url(
        self,
        url: str,
        *,
        task_id: str | None = None,
        title: str | None = None,
        source_type: SourceType = SourceType.PUBLIC_WEB,
    ) -> SourceRecord:
        parsed = urlparse(url)
        try:
            validate_public_http_url(url)
        except httpx.HTTPError as exc:
            raise ConnectorError(self.name, str(exc)) from exc

        metadata = {
            "connector": self.name,
            "document_format_hint": DocumentFormat.PDF
            if parsed.path.lower().endswith(".pdf")
            else DocumentFormat.WEB_PAGE,
        }
        return SourceRecord(
            task_id=task_id,
            source_type=source_type,
            title=title or parsed.netloc,
            url=url,
            publisher=parsed.netloc,
            credibility_note="User supplied public URL; credibility must be assessed downstream.",
            metadata=metadata,
        )

    def fetch_head_metadata(self, source: SourceRecord) -> SourceRecord:
        if source.url is None:
            raise ConnectorError(self.name, "cannot fetch metadata for a source without url.")
        try:
            response = request_public_url(self._fetcher, "HEAD", str(source.url))
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ConnectorError(self.name, f"URL metadata request failed: {exc}") from exc

        source.metadata.update(
            {
                "status_code": response.status_code,
                "content_type": response.headers.get("content-type"),
                "content_length": response.headers.get("content-length"),
                "final_url": str(response.url),
            }
        )
        return source
