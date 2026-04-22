"""Canonical BackendType enum for the agent runtime.

Kept in a standalone module with no intra-package dependencies so that
both ``alterraflow.config.settings`` and ``alterraflow.runners.contracts``
can import it without triggering a circular import through
``alterraflow.runners.__init__``.
"""

from __future__ import annotations

from enum import Enum


class BackendType(str, Enum):
    """Selects which agent backend a runner dispatches through."""

    PREPARED = "prepared"
    CODEX_EXEC = "codex_exec"
    OPENAI_API = "openai_api"
    ANTHROPIC_API = "anthropic_api"
    CURSOR_API = "cursor_api"

    @classmethod
    def _missing_(cls, value: object) -> BackendType | None:
        """Accept env-style values with surrounding whitespace and mixed case."""
        if isinstance(value, str):
            normalized = value.strip().lower()
            for member in cls:
                if member.value == normalized:
                    return member
        return None
