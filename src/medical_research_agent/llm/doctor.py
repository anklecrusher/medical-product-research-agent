"""Redacted LLM configuration diagnostics."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import httpx
from pydantic import SecretStr

from medical_research_agent.config import AppSettings, get_settings
from medical_research_agent.llm.client import OpenAICompatibleLLMClient
from medical_research_agent.llm.models import LLMMessage, LLMRequest
from medical_research_agent.schemas import SourceType


@dataclass(frozen=True, slots=True)
class LLMConfigCheckResult:
    """CLI-ready LLM configuration check output."""

    exit_code: int
    stdout: str
    stderr: str = ""


def run_llm_config_check(
    *,
    settings: AppSettings | None = None,
    mock_provider_smoke: bool = False,
    smoke_private_source: bool = False,
    transport: httpx.BaseTransport | None = None,
    sleep: Callable[[float], None] | None = None,
) -> LLMConfigCheckResult:
    """Return a redacted diagnostic report for the configured LLM provider."""

    resolved = settings or get_settings()
    lines = [
        f"provider={resolved.llm_provider}",
        f"model={resolved.llm_model}",
        f"base_url={resolved.llm_base_url.rstrip('/')}",
        f"api_key_set={str(resolved.llm_api_key_value() is not None).lower()}",
    ]

    if not mock_provider_smoke and resolved.llm_provider == "openai_compatible" and not resolved.llm_api_key_value():
        return LLMConfigCheckResult(
            exit_code=1,
            stdout=_join_lines(lines),
            stderr=(
                "Missing LLM API key. Set MEDICAL_RESEARCH_LLM_API_KEY in .env for "
                "openai_compatible provider."
            ),
        )

    if not mock_provider_smoke:
        lines.append("status=ok")
        return LLMConfigCheckResult(exit_code=0, stdout=_join_lines(lines))

    smoke_settings = resolved.model_copy(
        update={
            "llm_provider": "openai_compatible",
            "llm_api_key": SecretStr("doctor-fake-token-redacted"),
            "llm_base_url": "https://doctor-smoke.local/v1",
        }
    )
    source_types = [SourceType.PUBLIC_WEB]
    if smoke_private_source:
        source_types = [SourceType.USER_UPLOADED_PRIVATE]
    client = OpenAICompatibleLLMClient(
        settings=smoke_settings,
        transport=transport or _default_smoke_transport(),
        sleep=sleep or _sleep_noop,
    )
    try:
        response = client.complete(
            LLMRequest(
                messages=[
                    LLMMessage(role="system", content="Return a minimal diagnostic response."),
                    LLMMessage(role="user", content="LLM configuration smoke test."),
                ],
                source_types=source_types,
            )
        )
    except (PermissionError, RuntimeError, ValueError) as exc:
        lines.append("mock_provider_smoke=failed")
        return LLMConfigCheckResult(exit_code=1, stdout=_join_lines(lines), stderr=_redact(str(exc)))

    lines.append("mock_provider_smoke=ok")
    lines.append(f"smoke_provider={response.provider}")
    lines.append(f"smoke_model={response.model}")
    lines.append(f"retry_attempts={response.metadata.get('attempts', 1)}")
    return LLMConfigCheckResult(exit_code=0, stdout=_join_lines(lines))


def _default_smoke_transport() -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return httpx.Response(401, text="missing bearer token", request=request)
        payload = request.read().decode("utf-8")
        if "\"messages\"" not in payload:
            return httpx.Response(400, text="missing messages", request=request)
        return httpx.Response(
            200,
            json={
                "model": "doctor-smoke-model",
                "choices": [{"message": {"content": "ok"}}],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            },
            request=request,
        )

    return httpx.MockTransport(handler)


def _join_lines(lines: list[str]) -> str:
    return "\n".join(lines) + "\n"


def _redact(text: str) -> str:
    return text.replace("doctor-fake-token-redacted", "<redacted>")


def _sleep_noop(_seconds: float) -> None:
    return None
