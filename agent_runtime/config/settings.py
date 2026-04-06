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

from enum import Enum
from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class BackendType(str, Enum):
    """Pluggable backend provider for autonomous agent execution.

    ``PREPARED`` (default) emits a handoff result without calling any external
    agent — safe for manual workflows and CI environments that have no API key
    or autonomous CLI installed.  Set a role's backend env var to one of the
    other values to enable autonomous execution for that role.
    """

    PREPARED = "prepared"
    CODEX_EXEC = "codex_exec"
    OPENAI_API = "openai_api"
    ANTHROPIC_API = "anthropic_api"
    CURSOR_API = "cursor_api"

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
        populate_by_name=True,
    )

    api_key: SecretStr | None = Field(default=None, validation_alias=AliasChoices("GEMINI_API_KEY", "GOOGLE_API_KEY"))
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
    """Agent runtime backend and model settings.

    All values are read from ``AGENT_RUNTIME_*`` env vars (see ``.env.example``
    for the full list).  Defaults to the ``prepared`` backend for every role so
    that the runtime is safe to instantiate in environments with no API keys or
    autonomous CLI present.
    """

    model_config = SettingsConfigDict(
        env_prefix="AGENT_RUNTIME_",
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # -- PM role --
    pm_backend: BackendType = BackendType.PREPARED
    pm_codex_bin: str = "codex"
    pm_codex_model: str = "gpt-5"
    pm_openai_model: str = "gpt-4o"
    pm_anthropic_model: str = "claude-sonnet-4-5"
    pm_cursor_model: str = "cursor-fast"

    # -- Review role --
    review_backend: BackendType = BackendType.PREPARED
    review_codex_bin: str = "codex"
    review_codex_model: str = "gpt-5"
    review_openai_model: str = "gpt-4o"
    review_anthropic_model: str = "claude-sonnet-4-5"
    review_cursor_model: str = "cursor-fast"

    # -- Coding role --
    coding_backend: BackendType = BackendType.PREPARED
    coding_codex_bin: str = "codex"
    coding_codex_model: str = "gpt-5"
    coding_openai_model: str = "gpt-4o"
    coding_anthropic_model: str = "claude-sonnet-4-5"
    coding_cursor_model: str = "cursor-fast"
    coding_tool_max_iterations: int = 50

    # -- Spec role --
    spec_backend: BackendType = BackendType.PREPARED
    spec_codex_bin: str = "codex"
    spec_codex_model: str = "gpt-5"
    spec_openai_model: str = "gpt-4o"
    spec_anthropic_model: str = "claude-sonnet-4-5"
    spec_cursor_model: str = "cursor-fast"

    # -- PR publication --
    coding_pr_backend: str | None = None
    coding_pr_title_prefix: str = "[codex]"

    # -- Autonomy gates --
    auto_merge: bool = False
    auto_promote_wi: bool = False

    def get_role_backend(self, role: str) -> BackendType:
        """Return the configured ``BackendType`` for a given role name.

        Args:
            role: one of ``"pm"``, ``"review"``, ``"coding"``, ``"spec"``
        """
        return BackendType(getattr(self, f"{role}_backend"))

    def get_role_model(self, role: str, backend: BackendType) -> str:
        """Return the model string for a role + backend combination.

        Returns an empty string for ``PREPARED`` (no model needed).
        """
        if backend is BackendType.CODEX_EXEC:
            return str(getattr(self, f"{role}_codex_model"))
        if backend is BackendType.OPENAI_API:
            return str(getattr(self, f"{role}_openai_model"))
        if backend is BackendType.ANTHROPIC_API:
            return str(getattr(self, f"{role}_anthropic_model"))
        if backend is BackendType.CURSOR_API:
            return str(getattr(self, f"{role}_cursor_model"))
        return ""


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
        """Return True if the named provider has a non-blank API key set.

        Args:
            provider: a field name on ``Settings`` other than ``"agent_runtime"``
        """
        block = getattr(self, provider, None)
        if block is None:
            return False
        key: SecretStr | None = getattr(block, "api_key", None)
        if key is None:
            return False
        return bool(key.get_secret_value().strip())

    def configured_providers(self) -> list[str]:
        """Return names of all provider fields that have a non-blank API key set.

        Automatically includes any provider field added to ``Settings`` in the
        future; ``agent_runtime`` is excluded because it has no API key.
        """
        return [name for name in type(self).model_fields if name != "agent_runtime" and self.is_provider_configured(name)]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached singleton ``Settings`` instance.

    Call ``get_settings.cache_clear()`` in tests to reset between cases.
    """
    return Settings()
