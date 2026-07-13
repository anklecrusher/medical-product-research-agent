"""Run the workflow with real source connectors and document parsers enabled.

Example:
    .venv\\Scripts\\python.exe examples\\run_source_workflow.py "deep brain stimulation electrode impedance"
"""

from __future__ import annotations

import argparse
from pathlib import Path

from medical_research_agent.workflow import run_source_workflow


def main() -> None:
    parser = argparse.ArgumentParser(description="Run real source retrieval/parsing through the workflow.")
    parser.add_argument("query", help="One-sentence medical product research query.")
    parser.add_argument("--output-dir", type=Path, help="Optional output directory for workflow artifacts.")
    args = parser.parse_args()

    state = run_source_workflow(args.query, output_dir=args.output_dir)
    intermediate = state.get("intermediate", {})
    artifact_paths = [
        ("Sources", intermediate.get("sources_path")),
        ("Documents", intermediate.get("documents_path")),
        ("Evidence", intermediate.get("evidence_path")),
        ("Claims", intermediate.get("claims_path")),
        ("Report", intermediate.get("report_path")),
        ("PDF", intermediate.get("pdf_path")),
        ("Workflow state", intermediate.get("state_path")),
        ("Run log", intermediate.get("log_path")),
    ]

    print(f"Task: {state['task'].task_id}")
    print(f"Status: {state['task'].status.value}")
    print(f"Sources: {len(state.get('sources', []))}")
    print(f"Documents: {len(state.get('documents', []))}")
    print(f"Evidence: {len(state.get('evidence', []))}")
    print(f"Claims: {len(state.get('claims', []))}")
    print(f"Artifacts: {len(state.get('artifacts', []))}")
    print(f"Errors: {len(state.get('errors', []))}")
    quality = intermediate.get("report_quality")
    if isinstance(quality, dict):
        print(f"Report quality: passed={quality.get('passed')} score={quality.get('score')}")
        for reason in quality.get("reasons", []):
            print(f"- Quality: {reason}")
    print("Output artifacts:")
    for label, path in artifact_paths:
        if path:
            print(f"- {label}: {path}")


if __name__ == "__main__":
    main()
