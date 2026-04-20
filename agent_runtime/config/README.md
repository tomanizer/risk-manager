# Configuration

This directory holds the typed configuration layer for the agent runtime.

All API keys and provider settings are loaded from environment variables
and/or a `.env` file at the repository root. Secrets are stored as
`SecretStr` and are never logged.

## Quick start

```bash
cp .env.example .env
# Open .env and fill in the keys for the providers you want to use.
# Every key is optional; the runtime skips providers that have no key set.
```

## Provider environment variables

### OpenAI

| Variable | Required | Default | Notes |
| --- | --- | --- | --- |
| `OPENAI_API_KEY` | for OpenAI calls | — | `sk-…` key from [platform.openai.com/api-keys](https://platform.openai.com/api-keys) |
| `OPENAI_MODEL` | no | `gpt-4o` | Default inference model |
| `OPENAI_EMBEDDING_MODEL` | no | `text-embedding-3-small` | Embedding model |
| `OPENAI_ORGANIZATION` | no | — | Org ID for multi-org accounts |
| `OPENAI_BASE_URL` | no | — | Override for proxies or Azure OpenAI |

### Anthropic / Claude

| Variable | Required | Default | Notes |
| --- | --- | --- | --- |
| `ANTHROPIC_API_KEY` | for Anthropic calls | — | `sk-ant-…` key from [console.anthropic.com](https://console.anthropic.com/keys) |
| `ANTHROPIC_MODEL` | no | `claude-opus-4-5` | Default model |
| `ANTHROPIC_BASE_URL` | no | — | Override for proxies |

### Google Gemini

Accepts `GEMINI_API_KEY` (preferred) or `GOOGLE_API_KEY` (alias). If both are
set, `GEMINI_API_KEY` takes priority.

| Variable | Required | Default | Notes |
| --- | --- | --- | --- |
| `GEMINI_API_KEY` | for Gemini calls | — | `AIza…` key from [aistudio.google.com](https://aistudio.google.com/app/apikey) |
| `GOOGLE_API_KEY` | for Gemini calls | — | Accepted alias for `GEMINI_API_KEY` |
| `GEMINI_MODEL` | no | `gemini-2.0-flash` | Default model |
| `GEMINI_EMBEDDING_MODEL` | no | `models/text-embedding-004` | Embedding model |

### Cursor

| Variable | Required | Default | Notes |
| --- | --- | --- | --- |
| `CURSOR_API_KEY` | for Cursor endpoints | — | API key for Cursor-hosted model endpoints |
| `CURSOR_BASE_URL` | no | `https://api.cursor.sh/v1` | Endpoint override |
| `CURSOR_MODEL` | no | `cursor-fast` | Default model |

### LangChain / LangSmith

Set these to enable tracing and evaluation via [LangSmith](https://smith.langchain.com).

| Variable | Required | Default | Notes |
| --- | --- | --- | --- |
| `LANGCHAIN_API_KEY` | for tracing | — | `ls__…` key from LangSmith |
| `LANGCHAIN_TRACING_V2` | no | `false` | Set `true` to enable LangSmith tracing |
| `LANGCHAIN_PROJECT` | no | `risk-manager` | LangSmith project name |
| `LANGCHAIN_ENDPOINT` | no | `https://api.smith.langchain.com` | API endpoint |

### LangGraph Cloud

| Variable | Required | Default | Notes |
| --- | --- | --- | --- |
| `LANGGRAPH_API_KEY` | for LangGraph Cloud | — | Deployment API key |
| `LANGGRAPH_API_URL` | no | — | Your deployment URL |
| `LANGGRAPH_GRAPH_ID` | no | — | Target graph ID |

### Agent runtime backends

These control whether each runner executes automatically or waits for manual
handoff. See `agent_runtime/README.md` for full documentation.

| Variable | Required | Default | Notes |
| --- | --- | --- | --- |
| `AGENT_RUNTIME_PM_BACKEND` | no | `prepared` | `prepared` (manual) or `codex_exec` |
| `AGENT_RUNTIME_PM_CODEX_BIN` | no | `codex` | Codex binary path |
| `AGENT_RUNTIME_PM_CODEX_MODEL` | no | `gpt-5` | Model for PM runs |
| `AGENT_RUNTIME_REVIEW_BACKEND` | no | `prepared` | `prepared` or `codex_exec` |
| `AGENT_RUNTIME_REVIEW_CODEX_BIN` | no | `codex` | Codex binary path |
| `AGENT_RUNTIME_REVIEW_CODEX_MODEL` | no | `gpt-5` | Model for review runs |
| `AGENT_RUNTIME_CODING_BACKEND` | no | `prepared` | `prepared` or `codex_exec` |
| `AGENT_RUNTIME_CODING_CODEX_BIN` | no | `codex` | Codex binary path |
| `AGENT_RUNTIME_CODING_CODEX_MODEL` | no | `gpt-5` | Model for coding runs |
| `AGENT_RUNTIME_CODING_PR_BACKEND` | no | — | Set `gh_draft` to auto-publish draft PRs |
| `AGENT_RUNTIME_CODING_PR_TITLE_PREFIX` | no | `[codex]` | Prefix for auto-created PR titles |

## Python API

Import `get_settings()` anywhere in the codebase to access the cached
configuration object:

```python
from agent_runtime.config import get_settings

cfg = get_settings()

# Check which providers are ready to use
cfg.configured_providers()          # → ["openai", "anthropic"]

# Check a single provider
cfg.is_provider_configured("gemini")  # → True / False

# Retrieve a key as a plain string (only at the call site, never store it)
cfg.openai.api_key_str              # raises ValueError if OPENAI_API_KEY not set
cfg.anthropic.api_key_str
cfg.gemini.api_key_str

# Read non-secret settings
cfg.openai.model                    # "gpt-4o"
cfg.langchain.tracing_v2            # False
cfg.agent_runtime.pm_backend        # "prepared"
```

`get_settings()` is an `@lru_cache` singleton. It parses `.env` and the
process environment exactly once per process. All provider sub-configs
share the same `.env` file and loading order:

1. **Shell environment variables** (highest priority)
2. **`.env` file** at the repository root
3. **Defaults** defined in the settings classes

## Rules for using `api_key_str`

- Only call `api_key_str` at the point where you pass the key to an API
  client. Do not store the plain-text value in a variable that outlives
  the call.
- `api_key_str` raises `ValueError` with a clear message if the key is
  not set. Catch this at the integration boundary, not silently.
- Blank or whitespace-only values are treated as not configured.

## Testing

Reset the singleton between test cases with `cache_clear()`:

```python
from agent_runtime.config import get_settings

def test_something(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    get_settings.cache_clear()      # force re-parse with new env
    cfg = get_settings()
    assert cfg.openai.api_key_str == "sk-test"
```

See `tests/unit/agent_runtime/test_settings.py` for the full test suite.

## Pre-push hook

A repo-tracked `pre-commit` pre-push hook runs the shared push gate
before every push. The gate aligns local checks with the CI
`lint-and-test` workflow by running `ruff check`, `mypy`, `ruff format
--check`, `pytest`, and skill mirror parity as applicable. Activate it
once per clone:

```bash
pre-commit install --hook-type pre-push
```

To bypass in an emergency:

```bash
git push --no-verify
```
