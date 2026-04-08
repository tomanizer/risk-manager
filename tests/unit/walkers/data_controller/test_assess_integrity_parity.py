"""Parity tests for the Data Controller Walker (WI-4.1.2 / PRD-4.1).

Each test calls both ``assess_integrity`` (walker) and ``get_integrity_assessment``
(service) with identical arguments and asserts equality on the result.  This proves
the walker is a faithful delegate with no semantic divergence.

PRD-4.1 minimum test matrix:
  - All checks pass          → IntegrityAssessment  (walker == service)
  - Warning check            → IntegrityAssessment  (walker == service)
  - Failing check            → IntegrityAssessment  (walker == service)
  - Missing snapshot         → ServiceError         (walker == service)
  - Missing node             → ServiceError         (walker == service)
  - Missing control context  → ServiceError         (walker == service)

All six cases are reachable with the existing fixture infrastructure.
"""

from __future__ import annotations

from datetime import date

import pytest

from src.modules.controls_integrity import get_integrity_assessment
from src.modules.controls_integrity.fixtures import build_controls_integrity_fixture_index
from src.modules.risk_analytics.contracts import HierarchyScope, MeasureType, NodeLevel, NodeRef
from src.modules.risk_analytics.fixtures import build_fixture_index
from src.walkers.data_controller import assess_integrity

D_02 = date(2026, 1, 2)
D_05 = date(2026, 1, 5)
D_06 = date(2026, 1, 6)
D_08 = date(2026, 1, 8)


def firm_grp() -> NodeRef:
    return NodeRef(
        hierarchy_scope=HierarchyScope.TOP_OF_HOUSE,
        legal_entity_id=None,
        node_level=NodeLevel.FIRM,
        node_id="FIRM_GRP",
        node_name="Firm Group",
    )


def division_toh() -> NodeRef:
    return NodeRef(
        hierarchy_scope=HierarchyScope.TOP_OF_HOUSE,
        legal_entity_id=None,
        node_level=NodeLevel.DIVISION,
        node_id="DIV_GM",
        node_name="Global Markets",
    )


def division_le(legal_entity_id: str) -> NodeRef:
    return NodeRef(
        hierarchy_scope=HierarchyScope.LEGAL_ENTITY,
        legal_entity_id=legal_entity_id,
        node_level=NodeLevel.DIVISION,
        node_id="DIV_GM",
        node_name="Global Markets",
    )


def book_new_issues() -> NodeRef:
    return NodeRef(
        hierarchy_scope=HierarchyScope.TOP_OF_HOUSE,
        legal_entity_id=None,
        node_level=NodeLevel.BOOK,
        node_id="BOOK_NEW_ISSUES",
        node_name="New Issues",
    )


@pytest.fixture
def risk_index():
    return build_fixture_index()


@pytest.fixture
def controls_index():
    return build_controls_integrity_fixture_index()


# ---------------------------------------------------------------------------
# Smoke test — importability
# ---------------------------------------------------------------------------


def test_assess_integrity_importable() -> None:
    from src.walkers.data_controller import assess_integrity as fn  # noqa: F401

    assert callable(fn)


# ---------------------------------------------------------------------------
# Parity matrix
# ---------------------------------------------------------------------------


def test_parity_all_checks_pass(risk_index, controls_index) -> None:
    """Case: all checks pass → IntegrityAssessment; walker == service."""
    kwargs = dict(
        node_ref=firm_grp(),
        measure_type=MeasureType.VAR_1D_99,
        as_of_date=D_02,
        risk_fixture_index=risk_index,
        controls_fixture_index=controls_index,
    )
    walker_result = assess_integrity(**kwargs)
    service_result = get_integrity_assessment(**kwargs)
    assert walker_result == service_result


def test_parity_warning_check(risk_index, controls_index) -> None:
    """Case: warning check (CAUTION) → IntegrityAssessment; walker == service."""
    kwargs = dict(
        node_ref=division_toh(),
        measure_type=MeasureType.VAR_1D_99,
        as_of_date=D_05,
        risk_fixture_index=risk_index,
        controls_fixture_index=controls_index,
    )
    walker_result = assess_integrity(**kwargs)
    service_result = get_integrity_assessment(**kwargs)
    assert walker_result == service_result


def test_parity_failing_check(risk_index, controls_index) -> None:
    """Case: failing check (BLOCKED) → IntegrityAssessment; walker == service."""
    kwargs = dict(
        node_ref=division_toh(),
        measure_type=MeasureType.VAR_1D_99,
        as_of_date=D_06,
        risk_fixture_index=risk_index,
        controls_fixture_index=controls_index,
    )
    walker_result = assess_integrity(**kwargs)
    service_result = get_integrity_assessment(**kwargs)
    assert walker_result == service_result


def test_parity_missing_snapshot(risk_index, controls_index) -> None:
    """Case: missing snapshot → ServiceError(MISSING_SNAPSHOT); walker == service."""
    kwargs = dict(
        node_ref=firm_grp(),
        measure_type=MeasureType.VAR_1D_99,
        as_of_date=D_02,
        snapshot_id="SNAP-NOT-THERE",
        risk_fixture_index=risk_index,
        controls_fixture_index=controls_index,
    )
    walker_result = assess_integrity(**kwargs)
    service_result = get_integrity_assessment(**kwargs)
    assert walker_result == service_result


def test_parity_missing_node(risk_index, controls_index) -> None:
    """Case: missing node → ServiceError(MISSING_NODE); walker == service."""
    kwargs = dict(
        node_ref=division_le("LE-UK-BANK"),
        measure_type=MeasureType.VAR_1D_99,
        as_of_date=D_02,
        risk_fixture_index=risk_index,
        controls_fixture_index=controls_index,
    )
    walker_result = assess_integrity(**kwargs)
    service_result = get_integrity_assessment(**kwargs)
    assert walker_result == service_result


def test_parity_missing_control_context(risk_index, controls_index) -> None:
    """Case: missing control context → ServiceError(MISSING_CONTROL_CONTEXT); walker == service."""
    kwargs = dict(
        node_ref=book_new_issues(),
        measure_type=MeasureType.VAR_1D_99,
        as_of_date=D_08,
        risk_fixture_index=risk_index,
        controls_fixture_index=controls_index,
    )
    walker_result = assess_integrity(**kwargs)
    service_result = get_integrity_assessment(**kwargs)
    assert walker_result == service_result
