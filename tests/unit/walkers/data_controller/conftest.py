"""Shared fixtures for data_controller walker unit tests."""

from __future__ import annotations

import pytest

from src.shared.telemetry import reset_operation_logging_to_defaults


@pytest.fixture(autouse=True)
def _reset_shared_operation_logging() -> None:
    """Avoid cross-test leakage when tests configure module-level operation logging."""
    reset_operation_logging_to_defaults()
    yield
    reset_operation_logging_to_defaults()
