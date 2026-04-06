"""Shared pytest fixtures for agent_runtime tests."""

from __future__ import annotations

from typing import Generator

import pytest

from agent_runtime.config.settings import get_settings


@pytest.fixture(autouse=True)
def clear_settings_cache() -> Generator[None, None, None]:
    """Clear the cached Settings singleton before every test.

    Runner dispatch functions call ``get_settings()`` which is cached with
    ``@lru_cache``.  Tests that patch ``os.environ`` to change backend
    configuration rely on the cache being cold so that pydantic-settings
    re-reads the environment.
    """
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
