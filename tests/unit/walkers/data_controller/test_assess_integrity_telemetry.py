"""Operation logging for Data Controller walker (WI-4.1.4)."""

from __future__ import annotations

import logging
from datetime import date

import pytest

from src.modules.controls_integrity.fixtures import build_controls_integrity_fixture_index
from src.modules.risk_analytics.contracts import HierarchyScope, MeasureType, NodeLevel, NodeRef
from src.modules.risk_analytics.fixtures import build_fixture_index
from src.shared.telemetry import LOGGER_NAME, StdlibLoggerAdapter, configure_operation_logging
from src.walkers.data_controller import assess_integrity

D_02 = date(2026, 1, 2)


def _walker_structured_payload(caplog: pytest.LogCaptureFixture) -> dict[str, object]:
    """Return the structured_event dict for the walker layer (``assess_integrity``)."""
    for rec in caplog.records:
        payload = getattr(rec, "structured_event", None)
        if isinstance(payload, dict) and payload.get("operation") == "assess_integrity":
            return payload
    raise AssertionError("expected one operation log for assess_integrity")


def _firm_grp() -> NodeRef:
    return NodeRef(
        hierarchy_scope=HierarchyScope.TOP_OF_HOUSE,
        legal_entity_id=None,
        node_level=NodeLevel.FIRM,
        node_id="FIRM_GRP",
        node_name="Firm Group",
    )


def test_walker_emit_status_matches_integrity_assessment(caplog: pytest.LogCaptureFixture) -> None:
    risk_index = build_fixture_index()
    controls_index = build_controls_integrity_fixture_index()
    configure_operation_logging(enabled=True, logger=StdlibLoggerAdapter(LOGGER_NAME))
    caplog.set_level(logging.INFO, logger=LOGGER_NAME)

    outcome = assess_integrity(
        node_ref=_firm_grp(),
        measure_type=MeasureType.VAR_1D_99,
        as_of_date=D_02,
        risk_fixture_index=risk_index,
        controls_fixture_index=controls_index,
    )
    payload = _walker_structured_payload(caplog)

    assert payload["status"] == outcome.assessment_status.value
    assert "trace_id" not in payload
    assert "span_id" not in payload
    nr = payload["node_ref"]
    assert isinstance(nr, dict)
    assert nr["node_id"] == "FIRM_GRP"
    assert payload["measure_type"] == MeasureType.VAR_1D_99
    assert payload["snapshot_id"] is None
    assert isinstance(payload["duration_ms"], int)


def test_walker_emit_status_matches_service_error(caplog: pytest.LogCaptureFixture) -> None:
    risk_index = build_fixture_index()
    controls_index = build_controls_integrity_fixture_index()
    configure_operation_logging(enabled=True, logger=StdlibLoggerAdapter(LOGGER_NAME))
    caplog.set_level(logging.INFO, logger=LOGGER_NAME)

    outcome = assess_integrity(
        node_ref=_firm_grp(),
        measure_type=MeasureType.VAR_1D_99,
        as_of_date=D_02,
        snapshot_id="SNAP-NOT-THERE",
        risk_fixture_index=risk_index,
        controls_fixture_index=controls_index,
    )
    payload = _walker_structured_payload(caplog)

    assert payload["status"] == outcome.status_code
    assert outcome.status_code == "MISSING_SNAPSHOT"
    assert "trace_id" not in payload
    assert "span_id" not in payload
