"""Web page fetch and text extraction."""

from __future__ import annotations

import re

import httpx
from bs4 import BeautifulSoup

from medical_research_agent.schemas import DocumentFormat, ParsedDocument, SourceRecord
from medical_research_agent.url_security import PublicURLFetcherOwner, request_public_url


class DocumentParseError(RuntimeError):
    """Raised when a parser cannot fetch or extract a document."""

    def __init__(self, parser_name: str, message: str) -> None:
        super().__init__(f"{parser_name}: {message}")
        self.parser_name = parser_name
        self.message = message


class WebPageParser(PublicURLFetcherOwner):
    """Minimal parser for public HTML pages."""

    name = "web_page_parser"

    def __init__(self, *, transport: httpx.MockTransport | None = None, timeout_seconds: float = 20.0) -> None:
        super().__init__(transport=transport, timeout_seconds=timeout_seconds)

    def parse_url(self, source: SourceRecord) -> ParsedDocument:
        if source.url is None:
            raise DocumentParseError(self.name, "source has no URL.")
        try:
            response = request_public_url(self._fetcher, "GET", str(source.url))
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise DocumentParseError(self.name, f"fetch failed: {exc}") from exc

        return self.parse_html(
            response.text,
            source=source,
            final_url=str(response.url),
            content_type=response.headers.get("content-type"),
            status_code=response.status_code,
        )

    def parse_html(
        self,
        html: str,
        *,
        source: SourceRecord,
        final_url: str | None = None,
        content_type: str | None = None,
        status_code: int | None = None,
    ) -> ParsedDocument:
        soup = BeautifulSoup(html, "html.parser")
        for element in soup(["script", "style", "noscript", "svg"]):
            element.decompose()

        title = _clean_text(soup.title.get_text(" ")) if soup.title else source.title
        text_container = soup.find("main") or soup.find("article") or soup.body or soup
        text = _clean_text(text_container.get_text("\n"))

        return ParsedDocument(
            source_id=source.source_id,
            task_id=source.task_id,
            format=DocumentFormat.WEB_PAGE,
            title=title or source.title,
            text=text,
            parser_name=self.name,
            metadata={
                "content_type": content_type,
                "status_code": status_code,
                "final_url": final_url,
                "text_length": len(text),
            },
        )


def _clean_text(value: str) -> str:
    lines = [re.sub(r"\s+", " ", line).strip() for line in value.splitlines()]
    return "\n".join(line for line in lines if line)
