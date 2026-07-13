"""Replaceable LLM clients used by workflow nodes."""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import httpx

from medical_research_agent.config import AppSettings, get_settings
from medical_research_agent.llm.models import LLMRequest, LLMResponse, LLMUsage
from medical_research_agent.llm.privacy import assert_external_llm_allowed


@dataclass(frozen=True, slots=True)
class MissingLLMAPIKeyError(ValueError):
    """Raised when an OpenAI-compatible provider has no configured API key."""

    env_var: str = "MEDICAL_RESEARCH_LLM_API_KEY"
    provider: str = "openai_compatible"

    def __str__(self) -> str:
        return f"Missing LLM API key. Set {self.env_var} in .env for {self.provider} provider."


@dataclass(frozen=True, slots=True)
class LLMRequestFailedError(RuntimeError):
    """Raised after retryable LLM transport or response parsing failures."""

    attempts: int
    reason: str

    def __str__(self) -> str:
        return f"LLM request failed after {self.attempts} attempt(s): {self.reason}"


@dataclass(frozen=True, slots=True)
class UnsupportedLLMProviderError(ValueError):
    """Raised when configuration names an unsupported LLM provider."""

    provider: str

    def __str__(self) -> str:
        return f"Unsupported LLM provider: {self.provider}"


class LLMClient(ABC):
    """Minimal interface every workflow LLM implementation should satisfy."""

    provider: str

    @abstractmethod
    def complete(self, request: LLMRequest) -> LLMResponse:
        """Return a provider-neutral completion response."""


class MockLLMClient(LLMClient):
    """Deterministic local client for tests and offline workflow wiring."""

    provider = "mock"

    def __init__(self, model: str = "mock-medical-research-model") -> None:
        self.model = model

    def complete(self, request: LLMRequest) -> LLMResponse:
        last_user_message = next((message.content for message in reversed(request.messages) if message.role == "user"), "")
        content = (
            "[MOCK LLM RESPONSE]\n"
            f"model={request.model or self.model}\n"
            f"input={last_user_message[:500]}"
        )
        return LLMResponse(
            content=content,
            model=request.model or self.model,
            provider=self.provider,
            usage=LLMUsage(prompt_tokens=0, completion_tokens=0, total_tokens=0),
            metadata={"mock": True},
        )


class OpenAICompatibleLLMClient(LLMClient):
    """HTTP client for OpenAI-compatible `/chat/completions` APIs."""

    provider = "openai_compatible"

    def __init__(
        self,
        settings: AppSettings | None = None,
        *,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.settings = settings or get_settings()
        self.base_url = self.settings.llm_base_url.rstrip("/")
        self.model = self.settings.llm_model
        self.transport = transport
        self.sleep = sleep

    def complete(self, request: LLMRequest) -> LLMResponse:
        assert_external_llm_allowed(request.source_types, self.settings)
        api_key = self.settings.llm_api_key_value()
        if not api_key:
            raise MissingLLMAPIKeyError()

        payload: dict[str, Any] = {
            "model": request.model or self.model,
            "messages": [message.model_dump() for message in request.messages],
            "temperature": request.temperature,
        }
        if request.max_tokens is not None:
            payload["max_tokens"] = request.max_tokens
        if request.response_format is not None:
            payload["response_format"] = request.response_format

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        return self._post_with_retries(payload, headers)

    def _post_with_retries(self, payload: dict[str, Any], headers: dict[str, str]) -> LLMResponse:
        last_error: Exception | None = None
        attempts = self.settings.llm_max_retries + 1
        for attempt in range(attempts):
            try:
                with httpx.Client(timeout=self.settings.llm_timeout_seconds, transport=self.transport) as client:
                    response = client.post(f"{self.base_url}/chat/completions", json=payload, headers=headers)
                    response.raise_for_status()
                    data = response.json()
                    parsed = _parse_openai_compatible_response(
                        data,
                        provider=self.provider,
                        fallback_model=payload["model"],
                    )
                    parsed.metadata["attempts"] = attempt + 1
                    return parsed
            except (httpx.HTTPError, ValueError, KeyError, IndexError) as exc:
                last_error = exc
                if attempt >= attempts - 1:
                    break
                self.sleep(min(2**attempt, 8))

        raise LLMRequestFailedError(attempts=attempts, reason=str(last_error)) from last_error


def _parse_openai_compatible_response(data: dict[str, Any], *, provider: str, fallback_model: str) -> LLMResponse:
    choice = data["choices"][0]
    message = choice.get("message", {})
    content = message.get("content") or ""
    usage_data = data.get("usage") or {}
    usage = LLMUsage(
        prompt_tokens=usage_data.get("prompt_tokens"),
        completion_tokens=usage_data.get("completion_tokens"),
        total_tokens=usage_data.get("total_tokens"),
    )
    return LLMResponse(
        content=content,
        model=data.get("model") or fallback_model,
        provider=provider,
        usage=usage,
        raw=data,
    )


def get_llm_client(settings: AppSettings | None = None) -> LLMClient:
    """Create the configured LLM client.

    Defaults to the local mock client so tests and workflow demos never require
    API keys or network access.
    """

    resolved = settings or get_settings()
    if resolved.llm_provider == "mock":
        return MockLLMClient(model=resolved.llm_model)
    if resolved.llm_provider == "openai_compatible":
        return OpenAICompatibleLLMClient(settings=resolved)
    raise UnsupportedLLMProviderError(provider=resolved.llm_provider)
