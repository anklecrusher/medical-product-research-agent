"""Application configuration for local-first research runs."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    """Settings loaded from environment variables or a local .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="MEDICAL_RESEARCH_",
        extra="ignore",
    )

    app_env: Literal["local", "dev", "test", "prod"] = "local"
    log_level: str = "INFO"
    data_dir: Path = Field(default=Path("data"))
    outputs_dir: Path = Field(default=Path("outputs"))
    cache_dir: Path = Field(default=Path("cache"))
    uploads_dir: Path = Field(default=Path("uploads"))
    llm_provider: Literal["mock", "openai_compatible"] = "mock"
    llm_model: str = "mock-medical-research-model"
    llm_base_url: str = "https://api.openai.com/v1"
    llm_api_key: SecretStr | None = None
    llm_timeout_seconds: float = Field(default=60.0, gt=0)
    llm_max_retries: int = Field(default=2, ge=0)
    allow_external_llm_for_public_sources: bool = True
    allow_external_llm_for_private_sources: bool = False
    semantic_scholar_api_key: SecretStr | None = None

    def runtime_dirs(self) -> dict[str, Path]:
        """Return the canonical local runtime directory mapping."""

        return {
            "data": self.data_dir,
            "outputs": self.outputs_dir,
            "cache": self.cache_dir,
            "uploads": self.uploads_dir,
        }

    def llm_api_key_value(self) -> str | None:
        """Return the configured LLM API key without exposing it in repr output."""

        if self.llm_api_key is None:
            return None
        value = self.llm_api_key.get_secret_value().strip()
        return value or None

    def semantic_scholar_api_key_value(self) -> str | None:
        """Return the optional Semantic Scholar API key."""

        if self.semantic_scholar_api_key is None:
            return None
        value = self.semantic_scholar_api_key.get_secret_value().strip()
        return value or None


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    """Return cached application settings."""

    return AppSettings()
