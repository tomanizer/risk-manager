"""BackendType enum — shared constant used by both config and runners.

Defined in a standalone module with no agent_runtime dependencies so that
``config/settings.py`` can import it without triggering ``runners/__init__.py``
(which would create a circular import via the runner files importing
``agent_runtime.config``).
"""

from __future__ import annotations

from enum import Enum


class BackendType(str, Enum):
    """Identifies the execution backend for a runner role."""

    PREPARED = "prepared"
    CODEX_EXEC = "codex_exec"
    OPENAI_API = "openai_api"
    ANTHROPIC_API = "anthropic_api"
    CURSOR_API = "cursor_api"
