"""LLM provider and agent runtime configuration.

All values are loaded from environment variables and/or a .env file
at the repository root.  Secrets are stored as ``SecretStr`` so they
are never accidentally logged.

Usage::

    from agent_runtime.config import get_settings

    cfg = get_settings()
    openai_key = cfg.openai.api_key_str       # plain str, use only at call site
    print(cfg.anthropic.model)               # "claude-opus-4-5"
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve the .env file relative to this file's location so the config works
# regardless of the current working directory when the runtime is invoked.
_REPO_ROOT = Path(__file__).parent.parent.parent
_ENV_FILE = _REPO_ROOT / ".env"


# ---------------------------------------------------------------------------
# Per-provider config blocks
# Each is an independent BaseSettings with its own env_prefix so that the
# standard naming conventions (OPENAI_API_KEY, ANTHROPIC_API_KEY, etc.)
# work out of the box.
# ---------------------------------------------------------------------------


class OpenAIConfig(BaseSettings):
    """OpenAI / ChatGPT provider settings."""

    model_config = SettingsConfigDict(
        env_prefix="OPENAI_",
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    api_key: SecretStr | None = None
    organization: str | None = None
    base_url: str | None = None
    model: str = "gpt-4o"
    embedding_model: str = "text-embedding-3-small"

    @property
    def api_key_str(self) -> str:
        """Return the plain-text key; raises if not set."""
        if self.api_key is None:
            raise ValueError("OPENAI_API_KEY is not configured")
        return self.api_key.get_secret_value()


class AnthropicConfig(BaseSettings):
    """Anthropic / Claude provider settings."""

    model_config = SettingsConfigDict(
        env_prefix="ANTHROPIC_",
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    api_key: SecretStr | None = None
    base_url: str | None = None
    model: str = "claude-opus-4-5"

    @property
    def api_key_str(self) -> str:
        if self.api_key is None:
            raise ValueError("ANTHROPIC_API_KEY is not configured")
        return self.api_key.get_secret_value()


class GeminiConfig(BaseSettings):
    """Google Gemini provider settings.

    Accepts both ``GEMINI_API_KEY`` (preferred) and ``GOOGLE_API_KEY``
    (widely used alias) via the ``validation_alias`` on the field.
    """

    model_config = SettingsConfigDict(
        env_prefix="GEMINI_",
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    api_key: SecretStr | None = Field(default=None, validation_alias="GEMINI_API_KEY")
    model: str = "gemini-2.0-flash"
    embedding_model: str = "models/text-embedding-004"

    @property
    def api_key_str(self) -> str:
        if self.api_key is None:
            raise ValueError("GEMINI_API_KEY is not configured")
        return self.api_key.get_secret_value()


class CursorConfig(BaseSettings):
    """Cursor AI settings.

    ``CURSOR_API_KEY`` can be used to authenticate requests when accessing
    Cursor-hosted model endpoints directly.
    """

    model_config = SettingsConfigDict(
        env_prefix="CURSOR_",
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    api_key: SecretStr | None = None
    base_url: str = "https://api.cursor.sh/v1"
    model: str = "cursor-fast"

    @property
    def api_key_str(self) -> str:
        if self.api_key is None:
            raise ValueError("CURSOR_API_KEY is not configured")
        return self.api_key.get_secret_value()


class LangChainConfig(BaseSettings):
    """LangChain / LangSmith observability settings."""

    model_config = SettingsConfigDict(
        env_prefix="LANGCHAIN_",
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    api_key: SecretStr | None = None
    tracing_v2: bool = False
    project: str = "risk-manager"
    endpoint: str = "https://api.smith.langchain.com"

    @property
    def api_key_str(self) -> str:
        if self.api_key is None:
            raise ValueError("LANGCHAIN_API_KEY is not configured")
        return self.api_key.get_secret_value()


class LangGraphConfig(BaseSettings):
    """LangGraph Cloud / self-hosted deployment settings."""

    model_config = SettingsConfigDict(
        env_prefix="LANGGRAPH_",
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    api_key: SecretStr | None = None
    api_url: str | None = None
    graph_id: str | None = None

    @property
    def api_key_str(self) -> str:
        if self.api_key is None:
            raise ValueError("LANGGRAPH_API_KEY is not configured")
        return self.api_key.get_secret_value()


class AgentRuntimeConfig(BaseSettings):
    """Agent runtime backend and Codex execution settings.

    These mirror the ``AGENT_RUNTIME_*`` env vars documented in
    ``agent_runtime/README.md``.
    """

    model_config = SettingsConfigDict(
        env_prefix="AGENT_RUNTIME_",
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    pm_backend: str = "prepared"
    pm_codex_bin: str = "codex"
    pm_codex_model: str = "gpt-5"

    review_backend: str = "prepared"
    review_codex_bin: str = "codex"
    review_codex_model: str = "gpt-5"

    coding_backend: str = "prepared"
    coding_codex_bin: str = "codex"
    coding_codex_model: str = "gpt-5"

    coding_pr_backend: str | None = None
    coding_pr_title_prefix: str = "[codex]"


# ---------------------------------------------------------------------------
# Composite settings object
# ---------------------------------------------------------------------------


class Settings(BaseSettings):
    """Top-level settings that composes all provider configs.

    Instantiating this object is cheap; ``get_settings()`` caches the result.
    """

    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    openai: OpenAIConfig = Field(default_factory=OpenAIConfig)
    anthropic: AnthropicConfig = Field(default_factory=AnthropicConfig)
    gemini: GeminiConfig = Field(default_factory=GeminiConfig)
    cursor: CursorConfig = Field(default_factory=CursorConfig)
    langchain: LangChainConfig = Field(default_factory=LangChainConfig)
    langgraph: LangGraphConfig = Field(default_factory=LangGraphConfig)
    agent_runtime: AgentRuntimeConfig = Field(default_factory=AgentRuntimeConfig)

    def is_provider_configured(self, provider: str) -> bool:
        """Return True if the named provider has an API key set.

        Args:
            provider: one of ``"openai"``, ``"anthropic"``, ``"gemini"``,
                ``"cursor"``, ``"langchain"``, ``"langgraph"``
        """
        block = getattr(self, provider, None)
        if block is None:
            return False
        return getattr(block, "api_key", None) is not None

    def configured_providers(self) -> list[str]:
        """Return names of providers that have an API key set."""
        return [p for p in ("openai", "anthropic", "gemini", "cursor", "langchain", "langgraph") if self.is_provider_configured(p)]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached singleton ``Settings`` instance.

    Call ``get_settings.cache_clear()`` in tests to reset between cases.
    """
    return Settings()
