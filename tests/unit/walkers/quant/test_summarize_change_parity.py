"""Parity tests for the Quant Walker (WI-4.2.2 / PRD-4.2).

Each test calls both ``summarize_change`` (walker) and ``get_risk_change_profile``
(service) with identical arguments and asserts equality on the result. This proves
the walker is a faithful delegate with no semantic divergence from the service.

PRD-4.2 minimum parity matrix:
  - Successful change profile         -> RiskChangeProfile  (walker == service)
  - UNSUPPORTED_MEASURE               -> ServiceError       (walker == service)
  - MISSING_SNAPSHOT                  -> ServiceError       (walker == service)
  - MISSING_NODE                      -> ServiceError       (walker == service)
  - Invalid lookback_window           -> ValueError         (same message)
  - Blank snapshot_id                 -> ValueError         (same message)
  - compare_to_date > as_of_date      -> ValueError         (same message)

All seven parity rows are reachable with the existing risk_analytics fixture
infrastructure (``build_fixture_index``); no new fixtures are introduced for v1.
"""

from __future__ import annotations

from datetime import date

import pytest

from src.modules.risk_analytics import get_risk_change_profile
from src.modules.risk_analytics.contracts import (
    HierarchyScope,
    MeasureType,
    NodeLevel,
    NodeRef,
)
from src.modules.risk_analytics.fixtures import build_fixture_index
from src.shared import ServiceError
from src.walkers.quant import summarize_change


D_02 = date(2026, 1, 2)
D_06 = date(2026, 1, 6)
D_08 = date(2026, 1, 8)


def desk_toh() -> NodeRef:
    return NodeRef(
        hierarchy_scope=HierarchyScope.TOP_OF_HOUSE,
        legal_entity_id=None,
        node_level=NodeLevel.DESK,
        node_id="DESK_RATES_MACRO",
        node_name="Rates Macro",
    )


def division_le(legal_entity_id: str) -> NodeRef:
    return NodeRef(
        hierarchy_scope=HierarchyScope.LEGAL_ENTITY,
        legal_entity_id=legal_entity_id,
        node_level=NodeLevel.DIVISION,
        node_id="DIV_GM",
        node_name="Global Markets",
    )


@pytest.fixture
def risk_index():
    return build_fixture_index()


# ---------------------------------------------------------------------------
# Smoke test — importability from the package root
# ---------------------------------------------------------------------------


def test_summarize_change_importable() -> None:
    """`from src.walkers.quant import summarize_change` works and yields a callable."""
    from src.walkers.quant import summarize_change as fn  # noqa: F401

    assert callable(fn)


# ---------------------------------------------------------------------------
# Parity matrix — successful RiskChangeProfile
# ---------------------------------------------------------------------------


def test_parity_successful_change_profile(risk_index) -> None:
    """Case: valid node + supported measure + as_of with prior business day."""
    kwargs = dict(
        node_ref=desk_toh(),
        measure_type=MeasureType.VAR_1D_99,
        as_of_date=D_08,
        compare_to_date=D_06,
        fixture_index=risk_index,
    )
    walker_result = summarize_change(**kwargs)
    service_result = get_risk_change_profile(**kwargs)
    assert walker_result == service_result


# ---------------------------------------------------------------------------
# Parity matrix — typed ServiceError paths
# ---------------------------------------------------------------------------


def test_parity_unsupported_measure(risk_index) -> None:
    """Case: measure not in fixture pack supported_measures -> UNSUPPORTED_MEASURE."""
    kwargs = dict(
        node_ref=desk_toh(),
        measure_type=MeasureType.VAR_10D_99,
        as_of_date=D_08,
        fixture_index=risk_index,
    )
    walker_result = summarize_change(**kwargs)
    service_result = get_risk_change_profile(**kwargs)
    assert walker_result == service_result
    assert isinstance(walker_result, ServiceError)
    assert walker_result.status_code == "UNSUPPORTED_MEASURE"
    assert walker_result.operation == "get_risk_change_profile"


def test_parity_missing_snapshot(risk_index) -> None:
    """Case: explicit snapshot_id not present -> MISSING_SNAPSHOT."""
    kwargs = dict(
        node_ref=desk_toh(),
        measure_type=MeasureType.VAR_1D_99,
        as_of_date=D_08,
        snapshot_id="SNAP-NONEXISTENT",
        fixture_index=risk_index,
    )
    walker_result = summarize_change(**kwargs)
    service_result = get_risk_change_profile(**kwargs)
    assert walker_result == service_result
    assert isinstance(walker_result, ServiceError)
    assert walker_result.status_code == "MISSING_SNAPSHOT"
    assert walker_result.operation == "get_risk_change_profile"


def test_parity_missing_node(risk_index) -> None:
    """Case: snapshot exists but (node_ref, measure_type) absent -> MISSING_NODE.

    LE-UK-BANK DIV_GM is absent from SNAP-2026-01-02 in the default fixture pack.
    """
    kwargs = dict(
        node_ref=division_le("LE-UK-BANK"),
        measure_type=MeasureType.VAR_1D_99,
        as_of_date=D_02,
        compare_to_date=D_02,
        fixture_index=risk_index,
    )
    walker_result = summarize_change(**kwargs)
    service_result = get_risk_change_profile(**kwargs)
    assert walker_result == service_result
    assert isinstance(walker_result, ServiceError)
    assert walker_result.status_code == "MISSING_NODE"
    assert walker_result.operation == "get_risk_change_profile"


# ---------------------------------------------------------------------------
# Parity matrix — ValueError request-validation paths
# ---------------------------------------------------------------------------


def _capture_value_error(callable_, kwargs):
    """Call ``callable_(**kwargs)`` expecting ValueError; return the exception."""
    with pytest.raises(ValueError) as excinfo:
        callable_(**kwargs)
    return excinfo.value


def test_parity_invalid_lookback_window_raises_same_value_error(risk_index) -> None:
    """Case: lookback_window != 60 -> ValueError with identical message."""
    kwargs = dict(
        node_ref=desk_toh(),
        measure_type=MeasureType.VAR_1D_99,
        as_of_date=D_08,
        lookback_window=30,
        fixture_index=risk_index,
    )
    walker_err = _capture_value_error(summarize_change, kwargs)
    service_err = _capture_value_error(get_risk_change_profile, kwargs)
    assert type(walker_err) is type(service_err)
    assert str(walker_err) == str(service_err)


def test_parity_blank_snapshot_id_raises_same_value_error(risk_index) -> None:
    """Case: snapshot_id provided but blank -> ValueError with identical message."""
    kwargs = dict(
        node_ref=desk_toh(),
        measure_type=MeasureType.VAR_1D_99,
        as_of_date=D_08,
        snapshot_id="   ",
        fixture_index=risk_index,
    )
    walker_err = _capture_value_error(summarize_change, kwargs)
    service_err = _capture_value_error(get_risk_change_profile, kwargs)
    assert type(walker_err) is type(service_err)
    assert str(walker_err) == str(service_err)


def test_parity_compare_after_as_of_raises_same_value_error(risk_index) -> None:
    """Case: compare_to_date > as_of_date -> ValueError with identical message."""
    kwargs = dict(
        node_ref=desk_toh(),
        measure_type=MeasureType.VAR_1D_99,
        as_of_date=D_06,
        compare_to_date=D_08,
        fixture_index=risk_index,
    )
    walker_err = _capture_value_error(summarize_change, kwargs)
    service_err = _capture_value_error(get_risk_change_profile, kwargs)
    assert type(walker_err) is type(service_err)
    assert str(walker_err) == str(service_err)
