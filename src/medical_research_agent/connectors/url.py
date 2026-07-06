"""Connector helpers for user-supplied public URLs."""

from __future__ import annotations

from urllib.parse import urlparse

import httpx

from medical_research_agent.connectors.base import ConnectorError
from medical_research_agent.schemas import DocumentFormat, SourceRecord, SourceType


class URLSourceConnector:
    """Create and lightly validate public URL source records."""

    name = "url"

    def __init__(self, *, client: httpx.Client | None = None, timeout_seconds: float = 20.0) -> None:
        self._client = client or httpx.Client(timeout=timeout_seconds, follow_redirects=True)

    def from_url(
        self,
        url: str,
        *,
        task_id: str | None = None,
        title: str | None = None,
        source_type: SourceType = SourceType.PUBLIC_WEB,
    ) -> SourceRecord:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ConnectorError(self.name, f"unsupported URL: {url}")

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
            response = self._client.head(str(source.url), follow_redirects=True)
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
