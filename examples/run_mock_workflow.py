"""Run the mock medical research workflow from the command line."""

from __future__ import annotations

import argparse

from medical_research_agent.workflow import dump_workflow_state, run_mock_workflow


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the mock LangGraph research workflow.")
    parser.add_argument(
        "query",
        nargs="?",
        default="调研 SCS 刺激参数的产品范围、论文证据和监管资料",
        help="One-sentence medical product research request.",
    )
    parser.add_argument("--output-dir", default=None, help="Optional output directory for mock artifacts.")
    args = parser.parse_args()

    state = run_mock_workflow(args.query, output_dir=args.output_dir)
    print(dump_workflow_state(state))


if __name__ == "__main__":
    main()
