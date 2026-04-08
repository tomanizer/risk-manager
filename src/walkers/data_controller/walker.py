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
    return get_integrity_assessment(
        node_ref,
        measure_type,
        as_of_date,
        snapshot_id,
        risk_fixture_index=risk_fixture_index,
        controls_fixture_index=controls_fixture_index,
    )
