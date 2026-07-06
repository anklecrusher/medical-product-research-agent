"""Local private file ingestion and parsing."""

from __future__ import annotations

import hashlib
import zipfile
from pathlib import Path
from xml.etree import ElementTree

from medical_research_agent.parsers.pdf import PDFParser
from medical_research_agent.parsers.web import DocumentParseError
from medical_research_agent.schemas import DocumentFormat, ParsedDocument, SourceRecord, SourceType


class LocalFileIngestor:
    """Create private source records and parsed documents from local files."""

    name = "local_file_ingestor"

    def __init__(self, *, pdf_parser: PDFParser | None = None) -> None:
        self.pdf_parser = pdf_parser or PDFParser()

    def source_from_path(self, path: str | Path, *, task_id: str | None = None) -> SourceRecord:
        file_path = _resolve_existing_file(path)
        file_format = detect_document_format(file_path)
        stat = file_path.stat()

        return SourceRecord(
            task_id=task_id,
            source_type=SourceType.USER_UPLOADED_PRIVATE,
            title=file_path.name,
            local_path=str(file_path),
            publisher="Local upload",
            credibility_note="User-uploaded private file; default policy is local-only processing.",
            metadata={
                "ingestor": self.name,
                "document_format_hint": file_format,
                "file_name": file_path.name,
                "file_suffix": file_path.suffix.lower(),
                "file_size_bytes": stat.st_size,
                "sha256": _sha256_file(file_path),
                "privacy": "local_only",
            },
        )

    def parse_path(self, path: str | Path, *, task_id: str | None = None) -> tuple[SourceRecord, ParsedDocument]:
        source = self.source_from_path(path, task_id=task_id)
        return source, self.parse_source(source)

    def parse_source(self, source: SourceRecord) -> ParsedDocument:
        if source.local_path is None:
            raise DocumentParseError(self.name, "source has no local_path.")

        file_path = _resolve_existing_file(source.local_path)
        file_format = detect_document_format(file_path)
        if file_format == DocumentFormat.PDF:
            document = self.pdf_parser.parse_bytes(file_path.read_bytes(), source=source)
            document.metadata.update(_local_metadata(file_path, source, file_format))
            return document
        if file_format in {DocumentFormat.MARKDOWN, DocumentFormat.TEXT}:
            text = file_path.read_text(encoding="utf-8")
            return _parsed_text_document(source, file_path, file_format, text)
        if file_format == DocumentFormat.WORD:
            if file_path.suffix.lower() != ".docx":
                raise DocumentParseError(self.name, "legacy .doc files are not supported yet.")
            text = _extract_docx_text(file_path)
            return _parsed_text_document(source, file_path, file_format, text)

        raise DocumentParseError(self.name, f"unsupported local file type: {file_path.suffix}")


def detect_document_format(path: str | Path) -> DocumentFormat:
    suffix = Path(path).suffix.lower()
    if suffix == ".pdf":
        return DocumentFormat.PDF
    if suffix in {".md", ".markdown"}:
        return DocumentFormat.MARKDOWN
    if suffix in {".txt", ".text"}:
        return DocumentFormat.TEXT
    if suffix in {".doc", ".docx"}:
        return DocumentFormat.WORD
    return DocumentFormat.UNKNOWN


def _resolve_existing_file(path: str | Path) -> Path:
    file_path = Path(path).expanduser().resolve()
    if not file_path.exists():
        raise DocumentParseError(LocalFileIngestor.name, f"file does not exist: {file_path}")
    if not file_path.is_file():
        raise DocumentParseError(LocalFileIngestor.name, f"path is not a file: {file_path}")
    return file_path


def _parsed_text_document(
    source: SourceRecord,
    file_path: Path,
    file_format: DocumentFormat,
    text: str,
) -> ParsedDocument:
    return ParsedDocument(
        source_id=source.source_id,
        task_id=source.task_id,
        format=file_format,
        title=source.title,
        text=text,
        parser_name=LocalFileIngestor.name,
        metadata=_local_metadata(file_path, source, file_format) | {"text_length": len(text)},
    )


def _local_metadata(file_path: Path, source: SourceRecord, file_format: DocumentFormat) -> dict[str, object]:
    return {
        "local_path": str(file_path),
        "document_format_hint": file_format,
        "source_type": source.source_type,
        "privacy": "local_only",
    }


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _extract_docx_text(path: Path) -> str:
    try:
        with zipfile.ZipFile(path) as archive:
            document_xml = archive.read("word/document.xml")
    except (KeyError, zipfile.BadZipFile) as exc:
        raise DocumentParseError(LocalFileIngestor.name, f"DOCX text extraction failed: {exc}") from exc

    root = ElementTree.fromstring(document_xml)
    namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    paragraphs: list[str] = []
    for paragraph in root.findall(".//w:p", namespace):
        text_parts = [
            node.text
            for node in paragraph.findall(".//w:t", namespace)
            if node.text
        ]
        if text_parts:
            paragraphs.append("".join(text_parts))
    return "\n".join(paragraphs)
