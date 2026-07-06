"""Search public literature sources and optionally parse a URL.

Example:
    .venv\\Scripts\\python.exe examples\\search_sources.py "deep brain stimulation electrode impedance"
"""

from __future__ import annotations

import argparse
import json

from medical_research_agent.config import get_settings
from medical_research_agent.connectors import (
    CrossrefConnector,
    PubMedConnector,
    SearchRequest,
    SemanticScholarConnector,
    URLSourceConnector,
)
from medical_research_agent.io import write_model_json
from medical_research_agent.parsers import PDFParser, WebPageParser


def main() -> None:
    parser = argparse.ArgumentParser(description="Search public sources for a medical product research query.")
    parser.add_argument("query", help="Search query for public literature.")
    parser.add_argument("--limit", type=int, default=3, help="Maximum records per literature connector.")
    parser.add_argument("--output-dir", help="Optional directory for sources.json and documents.json.")
    parser.add_argument("--url", help="Optional public URL to normalize and parse.")
    args = parser.parse_args()

    request = SearchRequest(query=args.query, limit=args.limit)
    sources = []
    errors = []

    semantic_key = get_settings().semantic_scholar_api_key_value()
    for connector in [PubMedConnector(), CrossrefConnector(), SemanticScholarConnector(api_key=semantic_key)]:
        try:
            sources.extend(connector.search(request))
        except Exception as exc:
            errors.append(str(exc))

    parsed_documents = []
    if args.url:
        url_source = URLSourceConnector().from_url(args.url)
        sources.append(url_source)
        parser_impl = PDFParser() if args.url.lower().split("?")[0].endswith(".pdf") else WebPageParser()
        try:
            parsed_documents.append(parser_impl.parse_url(url_source))
        except Exception as exc:
            errors.append(str(exc))

    payload = {
        "sources": [source.model_dump(mode="json") for source in sources],
        "documents": [document.model_dump(mode="json") for document in parsed_documents],
        "errors": errors,
    }
    if args.output_dir:
        write_model_json(f"{args.output_dir}/sources.json", sources)
        write_model_json(f"{args.output_dir}/documents.json", parsed_documents)
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
