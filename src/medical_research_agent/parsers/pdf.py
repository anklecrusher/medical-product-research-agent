"""PDF download and text extraction."""

from __future__ import annotations

from io import BytesIO

import httpx
from pypdf.errors import PdfReadError
from pypdf import PdfReader

from medical_research_agent.parsers.web import DocumentParseError
from medical_research_agent.schemas import DocumentFormat, ParsedDocument, SourceRecord
from medical_research_agent.url_security import PublicURLFetcherOwner, request_public_url


class PDFParser(PublicURLFetcherOwner):
    """Minimal PDF parser using pypdf."""

    name = "pdf_parser"

    def __init__(self, *, transport: httpx.MockTransport | None = None, timeout_seconds: float = 30.0) -> None:
        super().__init__(transport=transport, timeout_seconds=timeout_seconds)

    def parse_url(self, source: SourceRecord) -> ParsedDocument:
        if source.url is None:
            raise DocumentParseError(self.name, "source has no URL.")
        try:
            response = request_public_url(self._fetcher, "GET", str(source.url))
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise DocumentParseError(self.name, f"fetch failed: {exc}") from exc

        return self.parse_bytes(
            response.content,
            source=source,
            final_url=str(response.url),
            content_type=response.headers.get("content-type"),
            status_code=response.status_code,
        )

    def parse_bytes(
        self,
        pdf_bytes: bytes,
        *,
        source: SourceRecord,
        final_url: str | None = None,
        content_type: str | None = None,
        status_code: int | None = None,
    ) -> ParsedDocument:
        try:
            reader = PdfReader(BytesIO(pdf_bytes))
            page_texts = [(page.extract_text() or "").strip() for page in reader.pages]
        except PdfReadError as exc:
            raise DocumentParseError(self.name, f"PDF text extraction failed: {exc}") from exc

        text = "\n\n".join(text for text in page_texts if text)
        return ParsedDocument(
            source_id=source.source_id,
            task_id=source.task_id,
            format=DocumentFormat.PDF,
            title=source.title,
            text=text,
            page_count=len(reader.pages),
            parser_name=self.name,
            metadata={
                "content_type": content_type,
                "status_code": status_code,
                "final_url": final_url,
                "text_length": len(text),
            },
        )
