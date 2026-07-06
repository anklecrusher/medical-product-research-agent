"""Run the workflow with real source connectors and document parsers enabled.

This still uses the existing mock evidence/report nodes after source parsing.

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
    output_dir = state["task"].output_dir or state["intermediate"].get("report_path", "")

    print(f"Task: {state['task'].task_id}")
    print(f"Sources: {len(state.get('sources', []))}")
    print(f"Documents: {len(state.get('documents', []))}")
    print(f"Errors: {len(state.get('errors', []))}")
    if output_dir:
        print(f"Output: {output_dir}")


if __name__ == "__main__":
    main()
