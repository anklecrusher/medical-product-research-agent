"""Document parsers for public web and PDF sources."""

from medical_research_agent.parsers.local_files import LocalFileIngestor, detect_document_format
from medical_research_agent.parsers.pdf import PDFParser
from medical_research_agent.parsers.web import DocumentParseError, WebPageParser

__all__ = ["DocumentParseError", "LocalFileIngestor", "PDFParser", "WebPageParser", "detect_document_format"]
