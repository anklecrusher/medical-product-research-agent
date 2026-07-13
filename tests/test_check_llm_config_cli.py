import os
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = PROJECT_ROOT / "examples" / "check_llm_config.py"


def test_cli_reports_mock_without_env() -> None:
    env = _clean_llm_env()

    result = subprocess.run(  # noqa: S603
        [sys.executable, str(SCRIPT)],
        cwd=PROJECT_ROOT,
        env=env,
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode == 0
    assert "provider=mock" in result.stdout
    assert "api_key_set=false" in result.stdout
    assert result.stderr == ""


def test_cli_openai_compatible_without_key_exits_nonzero() -> None:
    env = _clean_llm_env()
    env["MEDICAL_RESEARCH_LLM_PROVIDER"] = "openai_compatible"
    secret = "doctor-fake-cli-token-do-not-print"
    env.pop("MEDICAL_RESEARCH_LLM_API_KEY", None)

    result = subprocess.run(  # noqa: S603
        [sys.executable, str(SCRIPT)],
        cwd=PROJECT_ROOT,
        env=env,
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode != 0
    assert "provider=openai_compatible" in result.stdout
    assert "Missing LLM API key" in result.stderr
    assert secret not in result.stdout
    assert secret not in result.stderr


def test_cli_mock_provider_smoke_redacts_key() -> None:
    env = _clean_llm_env()
    secret = "doctor-fake-cli-smoke-token-do-not-print"
    env["MEDICAL_RESEARCH_LLM_API_KEY"] = secret

    result = subprocess.run(  # noqa: S603
        [sys.executable, str(SCRIPT), "--mock-provider-smoke"],
        cwd=PROJECT_ROOT,
        env=env,
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode == 0
    assert "mock_provider_smoke=ok" in result.stdout
    assert secret not in result.stdout
    assert secret not in result.stderr


def _clean_llm_env() -> dict[str, str]:
    env = dict(os.environ)
    for key in list(env):
        if key.startswith("MEDICAL_RESEARCH_"):
            env.pop(key)
    return env
