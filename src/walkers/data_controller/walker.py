"""Data Controller Walker — thin typed delegate to controls_integrity (PRD-4.1)."""

from __future__ import annotations

from datetime import date

from src.modules.controls_integrity import (
    ControlsIntegrityFixtureIndex,
    IntegrityAssessment,
    get_integrity_assessment,
)
from src.modules.risk_analytics.contracts import MeasureType, NodeRef
from src.modules.risk_analytics.fixtures import FixtureIndex
from src.shared import ServiceError
from src.shared.telemetry import emit_operation, node_ref_log_dict, timer_start


def assess_integrity(
    node_ref: NodeRef,
    measure_type: MeasureType,
    as_of_date: date,
    snapshot_id: str | None = None,
    *,
    risk_fixture_index: FixtureIndex | None = None,
    controls_fixture_index: ControlsIntegrityFixtureIndex | None = None,
) -> IntegrityAssessment | ServiceError:
    """Delegate to get_integrity_assessment; return its result unchanged."""
    start_time = timer_start()
    outcome = get_integrity_assessment(
        node_ref,
        measure_type,
        as_of_date,
        snapshot_id=snapshot_id,
        risk_fixture_index=risk_fixture_index,
        controls_fixture_index=controls_fixture_index,
    )
    status: str
    if isinstance(outcome, ServiceError):
        status = outcome.status_code
    else:
        status = outcome.assessment_status.value

    emit_operation(
        "assess_integrity",
        status=status,
        start_time=start_time,
        include_trace_context=False,
        node_ref=node_ref_log_dict(node_ref),
        measure_type=measure_type,
        as_of_date=as_of_date,
        snapshot_id=snapshot_id,
    )
    return outcome
