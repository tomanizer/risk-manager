"""Shared fixtures for Daily Risk Investigation orchestrator integration tests."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date

import pytest

from src.modules.controls_integrity.fixtures import (
    ControlsIntegrityFixtureIndex,
    build_controls_integrity_fixture_index,
)
from src.modules.risk_analytics.contracts import HierarchyScope, MeasureType, NodeLevel, NodeRef
from src.modules.risk_analytics.fixtures import FixtureIndex, build_fixture_index
from src.shared.telemetry import reset_operation_logging_to_defaults


# Snapshot identifiers and as-of dates available in both fixture indices,
# sourced from the existing controls_integrity / risk_analytics fixture packs.
SNAP_D_02 = "SNAP-2026-01-02"
SNAP_D_05 = "SNAP-2026-01-05"
SNAP_D_06 = "SNAP-2026-01-06"
SNAP_D_08 = "SNAP-2026-01-08"

D_02 = date(2026, 1, 2)
D_05 = date(2026, 1, 5)
D_06 = date(2026, 1, 6)
D_08 = date(2026, 1, 8)


@pytest.fixture
def risk_index() -> FixtureIndex:
    return build_fixture_index()


@pytest.fixture
def controls_index() -> ControlsIntegrityFixtureIndex:
    return build_controls_integrity_fixture_index()


@pytest.fixture(autouse=True)
def _reset_shared_operation_logging() -> Iterator[None]:
    """Avoid cross-test leakage from module-level operation logging configuration."""
    reset_operation_logging_to_defaults()
    yield
    reset_operation_logging_to_defaults()


def firm_grp() -> NodeRef:
    return NodeRef(
        hierarchy_scope=HierarchyScope.TOP_OF_HOUSE,
        legal_entity_id=None,
        node_level=NodeLevel.FIRM,
        node_id="FIRM_GRP",
    )


def division_toh() -> NodeRef:
    return NodeRef(
        hierarchy_scope=HierarchyScope.TOP_OF_HOUSE,
        legal_entity_id=None,
        node_level=NodeLevel.DIVISION,
        node_id="DIV_GM",
    )


def division_le_uk() -> NodeRef:
    return NodeRef(
        hierarchy_scope=HierarchyScope.LEGAL_ENTITY,
        legal_entity_id="LE-UK-BANK",
        node_level=NodeLevel.DIVISION,
        node_id="DIV_GM",
    )


def book_new_issues() -> NodeRef:
    return NodeRef(
        hierarchy_scope=HierarchyScope.TOP_OF_HOUSE,
        legal_entity_id=None,
        node_level=NodeLevel.BOOK,
        node_id="BOOK_NEW_ISSUES",
    )


VAR_1D_99 = MeasureType.VAR_1D_99
