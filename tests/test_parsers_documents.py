from __future__ import annotations

from io import BytesIO

import httpx
import pytest
from pypdf import PdfWriter

from medical_research_agent.parsers import DocumentParseError, PDFParser, WebPageParser
from medical_research_agent.schemas import DocumentFormat, SourceRecord, SourceType


def _source(url: str = "https://example.com/page") -> SourceRecord:
    return SourceRecord(
        source_type=SourceType.PUBLIC_WEB,
        title="Example",
        url=url,
    )


def test_web_parser_extracts_main_text_and_title() -> None:
    html = """
    <html>
      <head><title>Device Page</title><style>.hidden {}</style></head>
      <body>
        <nav>navigation noise</nav>
        <main><h1>DBS Device</h1><p>Frequency range is 2 to 130 Hz.</p></main>
        <script>alert("skip")</script>
      </body>
    </html>
    """

    document = WebPageParser().parse_html(html, source=_source())

    assert document.format == DocumentFormat.WEB_PAGE
    assert document.title == "Device Page"
    assert "DBS Device" in document.text
    assert "Frequency range" in document.text
    assert "alert" not in document.text


def test_web_parser_fetch_error_is_clear() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("offline", request=request)

    parser = WebPageParser(client=httpx.Client(transport=httpx.MockTransport(handler)))

    with pytest.raises(DocumentParseError, match="web_page_parser: fetch failed"):
        parser.parse_url(_source())


def test_pdf_parser_extracts_page_count_even_without_text() -> None:
    buffer = BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    writer.write(buffer)

    document = PDFParser().parse_bytes(buffer.getvalue(), source=_source("https://example.com/file.pdf"))

    assert document.format == DocumentFormat.PDF
    assert document.page_count == 1
    assert document.parser_name == "pdf_parser"


def test_pdf_parser_rejects_invalid_pdf() -> None:
    with pytest.raises(DocumentParseError, match="pdf_parser: PDF text extraction failed"):
        PDFParser().parse_bytes(b"not a pdf", source=_source("https://example.com/file.pdf"))
