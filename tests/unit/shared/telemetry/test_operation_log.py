"""Unit tests for src.shared.telemetry.operation_log."""

from __future__ import annotations

import logging
from datetime import date
from enum import Enum, StrEnum

import pytest

from src.shared.telemetry import operation_log as tel
from src.shared.telemetry.operation_log import (
    canonical_terminal_run_status_status,
    emit_operation,
    reset_operation_logging_to_defaults,
)


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


def test_normalize_context_value_list_and_tuple() -> None:
    d = date(2026, 4, 7)
    assert tel._normalize_context_value([d, _SampleEnum.A]) == ["2026-04-07", "alpha"]
    assert tel._normalize_context_value((1, "a")) == [1, "a"]


def test_emit_normalizes_status_reasons_like_sequence(caplog: pytest.LogCaptureFixture) -> None:
    tel.configure_operation_logging(enabled=True, logger=tel.StdlibLoggerAdapter(tel.LOGGER_NAME))
    caplog.set_level(logging.INFO, logger=tel.LOGGER_NAME)

    emit_operation(
        "test.op",
        status="OK",
        start_time=tel.timer_start(),
        include_trace_context=False,
        status_reasons=("REASON_A", "REASON_B"),
    )

    assert len(caplog.records) == 1
    payload = getattr(caplog.records[0], "structured_event")
    assert payload["status_reasons"] == ["REASON_A", "REASON_B"]


def test_emit_list_with_unserializable_element(caplog: pytest.LogCaptureFixture) -> None:
    tel.configure_operation_logging(enabled=True, logger=tel.StdlibLoggerAdapter(tel.LOGGER_NAME))
    caplog.set_level(logging.INFO, logger=tel.LOGGER_NAME)

    emit_operation(
        "test.op",
        status="OK",
        start_time=tel.timer_start(),
        include_trace_context=False,
        mixed=["ok", object()],
    )

    assert len(caplog.records) == 1
    payload = getattr(caplog.records[0], "structured_event")
    assert payload["mixed"] == ["ok", "<unserializable:object>"]


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


class _TerminalRunStatus(StrEnum):
    """Replica of TerminalRunStatus used to verify exhaustive mapping without an orchestrator import."""

    COMPLETED = "COMPLETED"
    COMPLETED_WITH_CAVEATS = "COMPLETED_WITH_CAVEATS"
    COMPLETED_WITH_FAILURES = "COMPLETED_WITH_FAILURES"
    FAILED_ALL_TARGETS = "FAILED_ALL_TARGETS"
    BLOCKED_READINESS = "BLOCKED_READINESS"


_EXPECTED_TERMINAL_STATUS_MAPPING = {
    "COMPLETED": "OK",
    "COMPLETED_WITH_CAVEATS": "DEGRADED",
    "COMPLETED_WITH_FAILURES": "PARTIAL",
    "FAILED_ALL_TARGETS": "DEGRADED",
    "BLOCKED_READINESS": "DEGRADED",
}


def test_canonical_terminal_run_status_covers_all_known_values() -> None:
    """Every TerminalRunStatus value must map to a canonical shared-telemetry status.

    This test pins the exhaustive mapping so that adding a new TerminalRunStatus
    member surfaces here rather than falling through to the graceful-degradation path
    at runtime.
    """
    for member in _TerminalRunStatus:
        result = canonical_terminal_run_status_status(member)
        assert result == _EXPECTED_TERMINAL_STATUS_MAPPING[member.value], f"unexpected telemetry status for {member!r}: got {result!r}"


def test_canonical_terminal_run_status_accepts_plain_string() -> None:
    assert canonical_terminal_run_status_status("COMPLETED") == "OK"
    assert canonical_terminal_run_status_status("COMPLETED_WITH_FAILURES") == "PARTIAL"


def test_canonical_terminal_run_status_degrades_gracefully_on_unknown(
    caplog: pytest.LogCaptureFixture,
) -> None:
    tel.configure_operation_logging(enabled=True, logger=tel.StdlibLoggerAdapter(tel.LOGGER_NAME))
    caplog.set_level(logging.WARNING, logger=tel.LOGGER_NAME)

    result = canonical_terminal_run_status_status("UNKNOWN_FUTURE_STATUS")

    assert result == "DEGRADED"
    assert len(caplog.records) == 1
    payload = getattr(caplog.records[0], "structured_event")
    assert payload.get("unrecognised_terminal_status") == "UNKNOWN_FUTURE_STATUS"


def test_stdlib_logger_adapter_bind_merges_context(caplog: pytest.LogCaptureFixture) -> None:
    log = tel.StdlibLoggerAdapter(tel.LOGGER_NAME)
    bound = log.bind(request_id="r1")
    caplog.set_level(logging.INFO, logger=tel.LOGGER_NAME)

    bound.info("evt", step="one")

    assert len(caplog.records) == 1
    payload = getattr(caplog.records[0], "structured_event")
    assert payload["request_id"] == "r1"
    assert payload["step"] == "one"
