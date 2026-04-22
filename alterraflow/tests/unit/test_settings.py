"""Tests for alterraflow.config.settings."""

from __future__ import annotations

import pytest

from alterraflow.config.settings import Settings, get_settings


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _settings(**env_overrides: str) -> Settings:
    """Build a fresh Settings instance with given env vars injected.

    Uses monkeypatching via the pydantic-settings env_file bypass: we
    construct Settings directly with explicit field values so no real
    .env or process-env leaks in.
    """
    # pydantic-settings respects keyword args passed to the constructor as
    # field overrides; provider sub-configs are themselves independent
    # BaseSettings instances, so we test them directly below.
    _ = env_overrides  # unused at this level – sub-config tests use monkeypatch
    return Settings()


# ---------------------------------------------------------------------------
# configured_providers – empty state
# ---------------------------------------------------------------------------


def test_configured_providers_empty_when_no_keys_set(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in (
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "GEMINI_API_KEY",
        "GOOGLE_API_KEY",
        "CURSOR_API_KEY",
        "LANGCHAIN_API_KEY",
        "LANGGRAPH_API_KEY",
    ):
        monkeypatch.delenv(var, raising=False)

    get_settings.cache_clear()
    cfg = get_settings()
    assert cfg.configured_providers() == []


# ---------------------------------------------------------------------------
# configured_providers – blank / whitespace keys treated as not configured
# ---------------------------------------------------------------------------


def test_blank_api_key_not_treated_as_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "   ")
    get_settings.cache_clear()
    cfg = get_settings()
    assert "openai" not in cfg.configured_providers()
    assert not cfg.is_provider_configured("openai")


def test_empty_api_key_not_treated_as_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "")
    get_settings.cache_clear()
    cfg = get_settings()
    assert "openai" not in cfg.configured_providers()


# ---------------------------------------------------------------------------
# configured_providers – real keys
# ---------------------------------------------------------------------------


def test_configured_providers_returns_openai_when_key_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-openai")
    get_settings.cache_clear()
    cfg = get_settings()
    assert "openai" in cfg.configured_providers()


def test_configured_providers_returns_multiple_providers(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-openai")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    get_settings.cache_clear()
    cfg = get_settings()
    providers = cfg.configured_providers()
    assert "openai" in providers
    assert "anthropic" in providers


# ---------------------------------------------------------------------------
# api_key_str
# ---------------------------------------------------------------------------


def test_api_key_str_returns_plain_value(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-real-key")
    get_settings.cache_clear()
    cfg = get_settings()
    assert cfg.openai.api_key_str == "sk-real-key"


def test_api_key_str_raises_when_not_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    get_settings.cache_clear()
    cfg = get_settings()
    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        cfg.openai.api_key_str


# ---------------------------------------------------------------------------
# Gemini AliasChoices – GOOGLE_API_KEY accepted
# ---------------------------------------------------------------------------


def test_gemini_accepts_google_api_key_alias(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("GOOGLE_API_KEY", "AIza-google-alias")
    get_settings.cache_clear()
    cfg = get_settings()
    assert cfg.gemini.api_key_str == "AIza-google-alias"
    assert "gemini" in cfg.configured_providers()


def test_gemini_prefers_gemini_api_key_over_google_alias(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "AIza-gemini-primary")
    monkeypatch.setenv("GOOGLE_API_KEY", "AIza-google-alias")
    get_settings.cache_clear()
    cfg = get_settings()
    assert cfg.gemini.api_key_str == "AIza-gemini-primary"


# ---------------------------------------------------------------------------
# Cache isolation
# ---------------------------------------------------------------------------


def test_get_settings_cache_clear_resets_singleton(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    get_settings.cache_clear()
    cfg_before = get_settings()
    assert "openai" not in cfg_before.configured_providers()

    monkeypatch.setenv("OPENAI_API_KEY", "sk-injected-after-clear")
    get_settings.cache_clear()
    cfg_after = get_settings()
    assert "openai" in cfg_after.configured_providers()


def test_get_settings_returns_same_instance_without_clear(monkeypatch: pytest.MonkeyPatch) -> None:
    get_settings.cache_clear()
    assert get_settings() is get_settings()


# ---------------------------------------------------------------------------
# AgentRuntime defaults
# ---------------------------------------------------------------------------


def test_alterraflow_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in ("AGENT_RUNTIME_PM_BACKEND", "AGENT_RUNTIME_REVIEW_BACKEND", "AGENT_RUNTIME_CODING_BACKEND"):
        monkeypatch.delenv(var, raising=False)
    get_settings.cache_clear()
    cfg = get_settings()
    assert cfg.alterraflow.pm_backend == "prepared"
    assert cfg.alterraflow.review_backend == "prepared"
    assert cfg.alterraflow.coding_backend == "prepared"
    assert cfg.alterraflow.coding_pr_backend is None


def test_alterraflow_backend_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENT_RUNTIME_CODING_BACKEND", "codex_exec")
    get_settings.cache_clear()
    cfg = get_settings()
    assert cfg.alterraflow.coding_backend == "codex_exec"
