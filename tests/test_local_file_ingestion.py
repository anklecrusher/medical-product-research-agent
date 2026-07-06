from __future__ import annotations

from io import BytesIO
import zipfile

import pytest
from pypdf import PdfWriter

from medical_research_agent.parsers import DocumentParseError, LocalFileIngestor, detect_document_format
from medical_research_agent.schemas import DocumentFormat, SourceType


def test_local_markdown_file_becomes_private_source_and_document(tmp_path) -> None:
    markdown_path = tmp_path / "product_notes.md"
    markdown_path.write_text("# 产品资料\n\n刺激频率范围需要核查。", encoding="utf-8")

    source, document = LocalFileIngestor().parse_path(markdown_path, task_id="task_private")

    assert source.source_type == SourceType.USER_UPLOADED_PRIVATE
    assert source.task_id == "task_private"
    assert source.local_path == str(markdown_path.resolve())
    assert source.metadata["privacy"] == "local_only"
    assert len(source.metadata["sha256"]) == 64
    assert document.format == DocumentFormat.MARKDOWN
    assert document.text.startswith("# 产品资料")
    assert document.metadata["source_type"] == SourceType.USER_UPLOADED_PRIVATE


def test_local_text_file_parses_utf8_text(tmp_path) -> None:
    text_path = tmp_path / "notes.txt"
    text_path.write_text("local private text evidence", encoding="utf-8")

    source, document = LocalFileIngestor().parse_path(text_path)

    assert detect_document_format(text_path) == DocumentFormat.TEXT
    assert source.title == "notes.txt"
    assert document.text == "local private text evidence"
    assert document.parser_name == "local_file_ingestor"


def test_local_pdf_file_reuses_pdf_parser(tmp_path) -> None:
    pdf_path = tmp_path / "manual.pdf"
    buffer = BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    writer.write(buffer)
    pdf_path.write_bytes(buffer.getvalue())

    source, document = LocalFileIngestor().parse_path(pdf_path)

    assert source.metadata["document_format_hint"] == DocumentFormat.PDF
    assert document.format == DocumentFormat.PDF
    assert document.page_count == 1
    assert document.metadata["privacy"] == "local_only"


def test_local_docx_file_extracts_paragraph_text(tmp_path) -> None:
    docx_path = tmp_path / "sample.docx"
    _write_minimal_docx(docx_path, ["第一段产品说明", "第二段参数说明"])

    source, document = LocalFileIngestor().parse_path(docx_path)

    assert source.metadata["document_format_hint"] == DocumentFormat.WORD
    assert document.format == DocumentFormat.WORD
    assert "第一段产品说明" in document.text
    assert "第二段参数说明" in document.text


def test_local_ingestor_rejects_unknown_file_type(tmp_path) -> None:
    binary_path = tmp_path / "image.bin"
    binary_path.write_bytes(b"\x00\x01")

    with pytest.raises(DocumentParseError, match="unsupported local file type"):
        LocalFileIngestor().parse_path(binary_path)


def test_local_ingestor_rejects_missing_file(tmp_path) -> None:
    with pytest.raises(DocumentParseError, match="file does not exist"):
        LocalFileIngestor().parse_path(tmp_path / "missing.pdf")


def _write_minimal_docx(path, paragraphs: list[str]) -> None:
    body = "".join(
        f"<w:p><w:r><w:t>{paragraph}</w:t></w:r></w:p>"
        for paragraph in paragraphs
    )
    document_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body>{body}</w:body>"
        "</w:document>"
    )
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types />")
        archive.writestr("word/document.xml", document_xml)
