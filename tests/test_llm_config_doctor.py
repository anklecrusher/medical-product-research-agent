import httpx
import pytest

from medical_research_agent.config import AppSettings
from medical_research_agent.llm.doctor import run_llm_config_check


def test_no_env_reports_mock_provider_without_key() -> None:
    result = run_llm_config_check(settings=AppSettings())

    assert result.exit_code == 0
    assert "provider=mock" in result.stdout
    assert "api_key_set=false" in result.stdout
    assert "mock-medical-research-model" in result.stdout
    assert result.stderr == ""


def test_openai_compatible_without_key_exits_nonzero() -> None:
    result = run_llm_config_check(settings=AppSettings(llm_provider="openai_compatible", llm_api_key=None))

    assert result.exit_code != 0
    assert "Missing LLM API key" in result.stderr
    assert "MEDICAL_RESEARCH_LLM_API_KEY" in result.stderr
    assert "provider=openai_compatible" in result.stdout


def test_mock_provider_smoke_exercises_fake_openai_path_without_secret_output() -> None:
    secret = "doctor-fake-token-do-not-print"

    result = run_llm_config_check(
        settings=AppSettings(
            llm_provider="mock",
            llm_api_key=secret,
            llm_model="doctor-test-model",
            llm_max_retries=0,
        ),
        mock_provider_smoke=True,
    )

    assert result.exit_code == 0
    assert "mock_provider_smoke=ok" in result.stdout
    assert "provider=mock" in result.stdout
    assert secret not in result.stdout
    assert secret not in result.stderr


def test_mock_provider_smoke_reports_retry_after_fake_http_failure() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(500, text="temporary failure", request=request)
        return httpx.Response(
            200,
            json={
                "model": "doctor-test-model",
                "choices": [{"message": {"content": "retry succeeded"}}],
            },
            request=request,
        )

    result = run_llm_config_check(
        settings=AppSettings(llm_max_retries=1),
        mock_provider_smoke=True,
        transport=httpx.MockTransport(handler),
        sleep=lambda _seconds: None,
    )

    assert result.exit_code == 0
    assert "mock_provider_smoke=ok" in result.stdout
    assert "retry_attempts=2" in result.stdout


def test_mock_provider_smoke_reports_fake_http_error_without_secret_output() -> None:
    secret = "doctor-fake-failure-token-do-not-print"
    transport = httpx.MockTransport(lambda request: httpx.Response(500, text="boom", request=request))

    result = run_llm_config_check(
        settings=AppSettings(llm_api_key=secret, llm_max_retries=1),
        mock_provider_smoke=True,
        transport=transport,
        sleep=lambda _seconds: None,
    )

    assert result.exit_code != 0
    assert "LLM request failed after 2 attempt(s)" in result.stderr
    assert secret not in result.stdout
    assert secret not in result.stderr


def test_mock_provider_smoke_reports_privacy_gate_failure() -> None:
    result = run_llm_config_check(
        settings=AppSettings(allow_external_llm_for_private_sources=False),
        mock_provider_smoke=True,
        smoke_private_source=True,
    )

    assert result.exit_code != 0
    assert "private source content" in result.stderr


def test_openai_compatible_provider_switch_uses_fake_smoke_without_real_key() -> None:
    result = run_llm_config_check(
        settings=AppSettings(llm_provider="openai_compatible", llm_api_key=None, llm_max_retries=0),
        mock_provider_smoke=True,
    )

    assert result.exit_code == 0
    assert "provider=openai_compatible" in result.stdout
    assert "api_key_set=false" in result.stdout
    assert "mock_provider_smoke=ok" in result.stdout
