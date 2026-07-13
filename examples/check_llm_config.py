#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "httpx>=0.28,<1",
#     "pydantic>=2.7,<3",
#     "pydantic-settings>=2.2,<3",
# ]
# ///

# --- How to run ---
# 1. Install uv (if not installed):
#      curl -LsSf https://astral.sh/uv/install.sh | sh
# 2. Run directly (no venv, no pip install needed):
#      uv run examples/check_llm_config.py [--mock-provider-smoke]
# 3. Or use the project environment:
#      .venv\Scripts\python.exe examples\check_llm_config.py [--mock-provider-smoke]
# ------------------

"""Print a redacted LLM configuration diagnostic."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from medical_research_agent.llm.doctor import run_llm_config_check


def main() -> int:
    parser = argparse.ArgumentParser(description="Check redacted LLM provider configuration.")
    parser.add_argument(
        "--mock-provider-smoke",
        action="store_true",
        help="Exercise the OpenAI-compatible client with an in-memory fake provider.",
    )
    args = parser.parse_args()

    result = run_llm_config_check(mock_provider_smoke=args.mock_provider_smoke)
    print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    return result.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
