"""Unit tests for src.shared.telemetry.operation_log."""

from __future__ import annotations

import logging
from datetime import date
from enum import Enum

import pytest

from src.shared.telemetry import operation_log as tel
from src.shared.telemetry.operation_log import emit_operation, reset_operation_logging_to_defaults


class _SampleEnum(Enum):
    A = "alpha"


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

    assert len(caplog.records) == 1
    assert caplog.records[0].levelname == "WARNING"


def test_normalize_context_value_date_enum_and_dict() -> None:
    d = date(2026, 4, 7)
    assert tel._normalize_context_value(d) == "2026-04-07"
    assert tel._normalize_context_value(_SampleEnum.A) == "alpha"
    assert tel._normalize_context_value({1: "x", "y": {True: 2}}) == {"1": "x", "y": {"True": 2}}


def test_normalize_context_value_unsupported_raises() -> None:
    with pytest.raises(TypeError, match="unsupported log context"):
        tel._normalize_context_value(object())


def test_emit_context_normalization_and_unserializable_fallback(caplog: pytest.LogCaptureFixture) -> None:
    tel.configure_operation_logging(enabled=True, logger=tel.StdlibLoggerAdapter(tel.LOGGER_NAME))
    caplog.set_level(logging.INFO, logger=tel.LOGGER_NAME)

    bad = object()
    emit_operation(
        "test.op",
        status="OK",
        start_time=tel.timer_start(),
        include_trace_context=False,
        as_of=date(2026, 4, 7),
        sample_enum=_SampleEnum.A,
        nested={"k": 1},
        bad_obj=bad,
    )

    assert len(caplog.records) == 1
    payload = getattr(caplog.records[0], "structured_event")
    assert payload["as_of"] == "2026-04-07"
    assert payload["sample_enum"] == "alpha"
    assert payload["nested"] == {"k": 1}
    assert payload["bad_obj"] == "<unserializable:object>"


def test_stdlib_logger_adapter_bind_merges_context(caplog: pytest.LogCaptureFixture) -> None:
    log = tel.StdlibLoggerAdapter(tel.LOGGER_NAME)
    bound = log.bind(request_id="r1")
    caplog.set_level(logging.INFO, logger=tel.LOGGER_NAME)

    bound.info("evt", step="one")

    assert len(caplog.records) == 1
    payload = getattr(caplog.records[0], "structured_event")
    assert payload["request_id"] == "r1"
    assert payload["step"] == "one"
