"""WI-5.1.3 — Orchestrator telemetry emission and payload discipline."""

from __future__ import annotations

import json
import logging
import subprocess
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

from src.modules.controls_integrity import (
    AssessmentStatus,
    CheckState,
    CheckType,
    ControlCheckResult,
    IntegrityAssessment,
    TrustState,
)
from src.modules.controls_integrity.contracts.enums import FalseSignalRisk
from src.modules.risk_analytics.contracts import (
    HierarchyScope,
    MeasureType,
    NodeLevel,
    NodeRef,
    RiskSummary,
)
from src.modules.risk_analytics.contracts.enums import SummaryStatus
from src.orchestrators.daily_risk_investigation import start_daily_run
from src.shared import ServiceError
from src.shared.telemetry import (
    LOGGER_NAME,
    StdlibLoggerAdapter,
    configure_operation_logging,
    reset_operation_logging_to_defaults,
)

_AS_OF_DATE = date(2024, 1, 15)
_GENERATED_AT = datetime(2024, 1, 15, 18, 0, 0, tzinfo=timezone.utc)
_SNAPSHOT_ID = "snap-001"

_RISK_PATCH = "src.orchestrators.daily_risk_investigation.orchestrator.get_risk_summary"
_WALKER_PATCH = "src.orchestrators.daily_risk_investigation.orchestrator.assess_integrity"


@pytest.fixture(autouse=True)
def _reset_telemetry() -> None:
    reset_operation_logging_to_defaults()
    yield
    reset_operation_logging_to_defaults()


def _node(node_id: str) -> NodeRef:
    return NodeRef(
        hierarchy_scope=HierarchyScope.TOP_OF_HOUSE,
        legal_entity_id=None,
        node_level=NodeLevel.DESK,
        node_id=node_id,
    )


def _risk_summary(node_ref: NodeRef) -> RiskSummary:
    return RiskSummary(
        node_ref=node_ref,
        measure_type=MeasureType.VAR_1D_99,
        as_of_date=_AS_OF_DATE,
        current_value=1.0,
        status=SummaryStatus.OK,
        snapshot_id=_SNAPSHOT_ID,
        data_version="dv-1",
        service_version="sv-1",
        generated_at=_GENERATED_AT,
    )


def _assessment(node_ref: NodeRef) -> IntegrityAssessment:
    checks = tuple(
        ControlCheckResult(
            check_type=check_type,
            check_state=CheckState.PASS,
            reason_codes=(),
            evidence_refs=(),
        )
        for check_type in (
            CheckType.FRESHNESS,
            CheckType.COMPLETENESS,
            CheckType.LINEAGE,
            CheckType.RECONCILIATION,
            CheckType.PUBLICATION_READINESS,
        )
    )
    return IntegrityAssessment(
        node_ref=node_ref,
        measure_type=MeasureType.VAR_1D_99,
        as_of_date=_AS_OF_DATE,
        trust_state=TrustState.TRUSTED,
        false_signal_risk=FalseSignalRisk.LOW,
        assessment_status=AssessmentStatus.OK,
        blocking_reason_codes=(),
        cautionary_reason_codes=(),
        check_results=checks,
        snapshot_id=_SNAPSHOT_ID,
        data_version="dv-1",
        service_version="sv-1",
        generated_at=_GENERATED_AT,
    )


def _payloads(caplog: pytest.LogCaptureFixture) -> list[dict[str, object]]:
    payloads: list[dict[str, object]] = []
    for record in caplog.records:
        payload = getattr(record, "structured_event", None)
        if isinstance(payload, dict) and str(payload.get("operation", "")).startswith("daily_run"):
            payloads.append(payload)
    return payloads


def _assert_exact_keys(payload: dict[str, object], *context_keys: str) -> None:
    expected = {"operation", "status", "duration_ms", *context_keys}
    assert set(payload) == expected
    assert isinstance(payload["duration_ms"], int)
    assert "trace_id" not in payload
    assert "span_id" not in payload


def _assert_no_forbidden_payload_values(value: object) -> None:
    if isinstance(value, dict):
        for nested in value.values():
            _assert_no_forbidden_payload_values(nested)
        return
    if isinstance(value, list):
        for nested in value:
            _assert_no_forbidden_payload_values(nested)
        return
    assert not isinstance(value, (IntegrityAssessment, ServiceError))
    if isinstance(value, str):
        assert "IntegrityAssessment" not in value
        assert "ServiceError" not in value


def test_daily_run_emits_required_events_once_with_low_cardinality_payloads(
    caplog: pytest.LogCaptureFixture,
) -> None:
    configure_operation_logging(enabled=True, logger=StdlibLoggerAdapter(LOGGER_NAME))
    caplog.set_level(logging.INFO, logger=LOGGER_NAME)

    candidates = (_node("D-1"), _node("D-2"), _node("D-3"))

    def risk_side_effect(*, node_ref: NodeRef, **_: object) -> RiskSummary | ServiceError:
        if node_ref.node_id == "D-2":
            return ServiceError(operation="get_risk_summary", status_code="MISSING_NODE")
        return _risk_summary(node_ref)

    def walker_side_effect(node_ref: NodeRef, *_args: object, **_kwargs: object) -> IntegrityAssessment | ServiceError:
        if node_ref.node_id == "D-3":
            return ServiceError(operation="assess_integrity", status_code="MISSING_CONTROL_CONTEXT")
        return _assessment(node_ref)

    with (
        patch(_RISK_PATCH, side_effect=risk_side_effect),
        patch(_WALKER_PATCH, side_effect=walker_side_effect),
    ):
        result = start_daily_run(
            as_of_date=_AS_OF_DATE,
            snapshot_id=_SNAPSHOT_ID,
            candidate_targets=candidates,
            measure_type=MeasureType.VAR_1D_99,
        )

    payloads = _payloads(caplog)
    assert [payload["operation"] for payload in payloads] == [
        "daily_run.intake",
        "daily_run.readiness_gate",
        "daily_run.target_selection",
        "daily_run.investigation",
        "daily_run.challenge",
        "daily_run.handoff",
        "daily_run_complete",
    ]
    assert len(payloads) == 7

    intake, readiness, selection, investigation, challenge, handoff, complete = payloads

    _assert_exact_keys(intake, "run_id", "as_of_date", "snapshot_id", "measure_type", "candidate_count")
    assert intake["status"] == "OK"
    assert intake["run_id"] == result.run_id
    assert intake["as_of_date"] == "2024-01-15"
    assert intake["snapshot_id"] == _SNAPSHOT_ID
    assert intake["measure_type"] == "VAR_1D_99"
    assert intake["candidate_count"] == 3

    _assert_exact_keys(readiness, "run_id", "as_of_date", "snapshot_id", "readiness_state", "readiness_reason_codes")
    assert readiness["status"] == "OK"
    assert readiness["run_id"] == result.run_id
    assert readiness["readiness_state"] == "READY"
    assert readiness["readiness_reason_codes"] == []

    _assert_exact_keys(selection, "run_id", "candidate_count", "selected_count", "excluded_missing_node_count")
    assert selection["status"] == "OK"
    assert selection["run_id"] == result.run_id
    assert selection["candidate_count"] == 3
    assert selection["selected_count"] == 2
    assert selection["excluded_missing_node_count"] == 1

    _assert_exact_keys(investigation, "run_id", "selected_count", "assessment_count", "service_error_count")
    assert investigation["status"] == "OK"
    assert investigation["run_id"] == result.run_id
    assert investigation["selected_count"] == 2
    assert investigation["assessment_count"] == 1
    assert investigation["service_error_count"] == 1

    _assert_exact_keys(
        challenge,
        "run_id",
        "ready_for_handoff_count",
        "proceed_with_caveat_count",
        "hold_blocking_trust_count",
        "hold_unresolved_trust_count",
        "hold_investigation_failed_count",
    )
    assert challenge["status"] == "OK"
    assert challenge["run_id"] == result.run_id
    assert challenge["ready_for_handoff_count"] == 1
    assert challenge["proceed_with_caveat_count"] == 0
    assert challenge["hold_blocking_trust_count"] == 0
    assert challenge["hold_unresolved_trust_count"] == 0
    assert challenge["hold_investigation_failed_count"] == 1

    _assert_exact_keys(handoff, "run_id", "handoff_count")
    assert handoff["status"] == "OK"
    assert handoff["run_id"] == result.run_id
    assert handoff["handoff_count"] == 2

    _assert_exact_keys(
        complete,
        "run_id",
        "as_of_date",
        "snapshot_id",
        "terminal_status",
        "degraded",
        "partial",
        "selected_count",
        "assessment_count",
        "service_error_count",
    )
    assert complete["status"] == "PARTIAL"
    assert complete["run_id"] == result.run_id
    assert complete["as_of_date"] == "2024-01-15"
    assert complete["snapshot_id"] == _SNAPSHOT_ID
    assert complete["terminal_status"] == "COMPLETED_WITH_FAILURES"
    assert complete["degraded"] is False
    assert complete["partial"] is True
    assert complete["selected_count"] == 2
    assert complete["assessment_count"] == 1
    assert complete["service_error_count"] == 1

    for payload in payloads:
        _assert_no_forbidden_payload_values(payload)


@pytest.mark.parametrize("blocking_status", ["MISSING_SNAPSHOT", "UNSUPPORTED_MEASURE"])
def test_blocked_readiness_emits_only_intake_gate_and_complete(
    caplog: pytest.LogCaptureFixture,
    blocking_status: str,
) -> None:
    configure_operation_logging(enabled=True, logger=StdlibLoggerAdapter(LOGGER_NAME))
    caplog.set_level(logging.INFO, logger=LOGGER_NAME)

    candidates = (_node("D-1"), _node("D-2"))

    with (
        patch(_RISK_PATCH, return_value=ServiceError(operation="get_risk_summary", status_code=blocking_status)),
        patch(_WALKER_PATCH) as walker_spy,
    ):
        result = start_daily_run(
            as_of_date=_AS_OF_DATE,
            snapshot_id=_SNAPSHOT_ID,
            candidate_targets=candidates,
            measure_type=MeasureType.VAR_1D_99,
        )

    walker_spy.assert_not_called()
    payloads = _payloads(caplog)
    assert [payload["operation"] for payload in payloads] == [
        "daily_run.intake",
        "daily_run.readiness_gate",
        "daily_run_complete",
    ]
    assert len(payloads) == 3

    intake, readiness, complete = payloads
    _assert_exact_keys(intake, "run_id", "as_of_date", "snapshot_id", "measure_type", "candidate_count")
    assert intake["status"] == "OK"

    _assert_exact_keys(readiness, "run_id", "as_of_date", "snapshot_id", "readiness_state", "readiness_reason_codes")
    assert readiness["status"] == blocking_status
    assert readiness["readiness_state"] == "BLOCKED"
    assert readiness["readiness_reason_codes"] == [blocking_status]

    _assert_exact_keys(
        complete,
        "run_id",
        "as_of_date",
        "snapshot_id",
        "terminal_status",
        "degraded",
        "partial",
        "selected_count",
        "assessment_count",
        "service_error_count",
    )
    assert complete["status"] == "DEGRADED"
    assert complete["run_id"] == result.run_id
    assert complete["terminal_status"] == "BLOCKED_READINESS"
    assert complete["degraded"] is False
    assert complete["partial"] is False
    assert complete["selected_count"] == 0
    assert complete["assessment_count"] == 0
    assert complete["service_error_count"] == 0


def test_orchestrator_package_does_not_import_agent_runtime() -> None:
    repo_root = Path(__file__).resolve().parents[4]
    script = """
import json
import sys

before = set(sys.modules)
import src.orchestrators.daily_risk_investigation  # noqa: F401
after = set(sys.modules)
loaded = sorted(
    name for name in (after - before) if name == "agent_runtime" or name.startswith("agent_runtime.")
)
print(json.dumps(loaded))
"""
    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(completed.stdout.strip()) == []
