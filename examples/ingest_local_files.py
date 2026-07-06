"""Ingest local private files into SourceRecord and ParsedDocument JSON.

Example:
    .venv\\Scripts\\python.exe examples\\ingest_local_files.py uploads\\sample.pdf --output-dir outputs\\local_ingest_demo
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from medical_research_agent.io import write_model_json
from medical_research_agent.parsers import LocalFileIngestor


def main() -> None:
    parser = argparse.ArgumentParser(description="Parse local private files without external API calls.")
    parser.add_argument("files", nargs="+", type=Path, help="Local PDF, Markdown, TXT, or DOCX files.")
    parser.add_argument("--task-id", help="Optional task id to attach to generated records.")
    parser.add_argument("--output-dir", type=Path, help="Optional directory for sources.json and documents.json.")
    args = parser.parse_args()

    ingestor = LocalFileIngestor()
    sources = []
    documents = []
    errors = []

    for file_path in args.files:
        try:
            source, document = ingestor.parse_path(file_path, task_id=args.task_id)
        except Exception as exc:
            errors.append(f"{file_path}: {exc}")
            continue
        sources.append(source)
        documents.append(document)

    if args.output_dir:
        write_model_json(args.output_dir / "sources.json", sources)
        write_model_json(args.output_dir / "documents.json", documents)

    print(
        json.dumps(
            {
                "sources": [source.model_dump(mode="json") for source in sources],
                "documents": [document.model_dump(mode="json") for document in documents],
                "errors": errors,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
