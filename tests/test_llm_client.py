import pytest

from medical_research_agent.config import AppSettings
from medical_research_agent.llm import (
    LLMMessage,
    LLMRequest,
    MockLLMClient,
    OpenAICompatibleLLMClient,
    get_llm_client,
)
from medical_research_agent.schemas import SourceType


def test_default_llm_client_is_mock() -> None:
    settings = AppSettings()
    client = get_llm_client(settings)

    assert isinstance(client, MockLLMClient)


def test_mock_llm_client_returns_deterministic_response() -> None:
    client = MockLLMClient()
    response = client.complete(
        LLMRequest(messages=[LLMMessage(role="user", content="生成调研计划")])
    )

    assert response.provider == "mock"
    assert "[MOCK LLM RESPONSE]" in response.content
    assert "生成调研计划" in response.content


def test_openai_compatible_requires_api_key() -> None:
    settings = AppSettings(llm_provider="openai_compatible", llm_api_key=None)
    client = OpenAICompatibleLLMClient(settings=settings)

    with pytest.raises(ValueError, match="Missing LLM API key"):
        client.complete(LLMRequest(messages=[LLMMessage(role="user", content="hello")]))


def test_external_llm_blocks_private_sources_by_default() -> None:
    settings = AppSettings(llm_provider="openai_compatible", llm_api_key="test-key")
    client = OpenAICompatibleLLMClient(settings=settings)

    with pytest.raises(PermissionError, match="private source content"):
        client.complete(
            LLMRequest(
                messages=[LLMMessage(role="user", content="summarize private document")],
                source_types=[SourceType.USER_UPLOADED_PRIVATE],
            )
        )
