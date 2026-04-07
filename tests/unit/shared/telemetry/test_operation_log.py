"""Unit tests for src.shared.telemetry.operation_log."""

from __future__ import annotations

import logging

import pytest

from src.shared.telemetry import operation_log as tel
from src.shared.telemetry.operation_log import emit_operation, reset_operation_logging_to_defaults


@pytest.fixture(autouse=True)
def _reset_telemetry() -> None:
    reset_operation_logging_to_defaults()
    yield
    reset_operation_logging_to_defaults()


def test_emit_skips_when_disabled(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    monkeypatch.setenv("SRC_TELEMETRY_ENABLED", "0")
    reset_operation_logging_to_defaults()
    caplog.set_level(logging.INFO, logger=tel.LOGGER_NAME)
    tel.configure_operation_logging(logger=tel.StdlibLoggerAdapter(tel.LOGGER_NAME))

    emit_operation("test.op", status="OK", start_time=tel.timer_start(), foo="bar")

    assert len(caplog.records) == 0


def test_emit_includes_core_fields_and_respects_level(caplog: pytest.LogCaptureFixture) -> None:
    tel.configure_operation_logging(enabled=True, logger=tel.StdlibLoggerAdapter(tel.LOGGER_NAME))
    caplog.set_level(logging.INFO, logger=tel.LOGGER_NAME)

    t0 = tel.timer_start()
    emit_operation(
        "test.op",
        status="OK",
        start_time=t0,
        include_trace_context=False,
        measure_type="VAR_1D_99",
    )

    assert len(caplog.records) == 1
    record = caplog.records[0]
    assert record.levelname == "INFO"
    payload = getattr(record, "structured_event")
    assert payload["operation"] == "test.op"
    assert payload["status"] == "OK"
    assert payload["measure_type"] == "VAR_1D_99"
    assert isinstance(payload["duration_ms"], int)
    assert payload["duration_ms"] >= 0


def test_warning_status_uses_warning_level(caplog: pytest.LogCaptureFixture) -> None:
    tel.configure_operation_logging(enabled=True, logger=tel.StdlibLoggerAdapter(tel.LOGGER_NAME))
    caplog.set_level(logging.DEBUG, logger=tel.LOGGER_NAME)

    emit_operation(
        "test.op",
        status="DEGRADED",
        start_time=tel.timer_start(),
        include_trace_context=False,
    )

    assert caplog.records[0].levelname == "WARNING"
