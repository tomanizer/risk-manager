"""Summary-service behavior tests for get_risk_summary."""

from __future__ import annotations

import logging
import math
import unittest
from datetime import date, datetime, timezone

import pytest

from src.modules.risk_analytics import get_risk_summary
from src.modules.risk_analytics.contracts import (
    HierarchyScope,
    MeasureType,
    NodeLevel,
    NodeRef,
    RiskSummary,
    SummaryStatus,
)
from src.modules.risk_analytics.fixtures import (
    FixtureIndex,
    FixtureRow,
    FixtureSnapshot,
    RiskSummaryFixturePack,
    build_fixture_index,
)
from src.shared import ServiceError
from src.shared.telemetry import LOGGER_NAME, StdlibLoggerAdapter, configure_operation_logging


# ---------------------------------------------------------------------------
# Fixture-derived constants
# ---------------------------------------------------------------------------
# Calendar: 2026-01-02, 2026-01-05, 2026-01-06, 2026-01-08, 2026-01-09, 2026-01-12
# SNAP-2026-01-09 is degraded (all rows degraded).
# LE-UK-BANK DIV_GM only appears from SNAP-2026-01-05 onward (absent from SNAP-2026-01-02).
# BOOK_NEW_ISSUES only appears from SNAP-2026-01-08 onward.

D_02 = date(2026, 1, 2)
D_05 = date(2026, 1, 5)
D_06 = date(2026, 1, 6)
D_08 = date(2026, 1, 8)
D_09 = date(2026, 1, 9)
D_12 = date(2026, 1, 12)


# ---------------------------------------------------------------------------
# NodeRef helpers
# ---------------------------------------------------------------------------


def desk_toh(node_id: str = "DESK_RATES_MACRO") -> NodeRef:
    return NodeRef(
        hierarchy_scope=HierarchyScope.TOP_OF_HOUSE,
        legal_entity_id=None,
        node_level=NodeLevel.DESK,
        node_id=node_id,
        node_name="Rates Macro",
    )


def desk_le(legal_entity_id: str) -> NodeRef:
    return NodeRef(
        hierarchy_scope=HierarchyScope.LEGAL_ENTITY,
        legal_entity_id=legal_entity_id,
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


def book_toh(node_id: str) -> NodeRef:
    return NodeRef(
        hierarchy_scope=HierarchyScope.TOP_OF_HOUSE,
        legal_entity_id=None,
        node_level=NodeLevel.BOOK,
        node_id=node_id,
        node_name="Rates EM",
    )


# ---------------------------------------------------------------------------
# Rolling-stat helpers for expected-value computation
# ---------------------------------------------------------------------------


def _mean(values: list[float]) -> float:
    return sum(values) / len(values)


def _std(values: list[float]) -> float:
    """Sample standard deviation (ddof=1)."""
    n = len(values)
    assert n >= 2, "std requires at least 2 points"
    m = _mean(values)
    return math.sqrt(sum((v - m) ** 2 for v in values) / (n - 1))


def _make_synthetic_summary_index(
    *,
    current_value: float,
    previous_value: float | None,
    current_degraded: bool = False,
) -> tuple[FixtureIndex, date, date, NodeRef]:
    d1 = date(2026, 2, 2)
    d2 = date(2026, 2, 3)
    d3 = date(2026, 2, 4)
    d4 = date(2026, 2, 5)
    d5 = date(2026, 2, 6)
    node_ref = desk_toh("DESK_SYNTH_SUMMARY")

    rows_d4 = ()
    if previous_value is not None:
        rows_d4 = (
            FixtureRow(
                node_ref=node_ref,
                measure_type=MeasureType.VAR_1D_99,
                value=previous_value,
                status=SummaryStatus.OK,
            ),
        )

    pack = RiskSummaryFixturePack(
        service_version="v1-synth-summary-test",
        data_version="d1-synth-summary-test",
        calendar=(d1, d2, d3, d4, d5),
        snapshots=(
            FixtureSnapshot(snapshot_id="S1", as_of_date=d1, is_degraded=False, rows=()),
            FixtureSnapshot(snapshot_id="S2", as_of_date=d2, is_degraded=False, rows=()),
            FixtureSnapshot(snapshot_id="S3", as_of_date=d3, is_degraded=False, rows=()),
            FixtureSnapshot(snapshot_id="S4", as_of_date=d4, is_degraded=False, rows=rows_d4),
            FixtureSnapshot(
                snapshot_id="S5",
                as_of_date=d5,
                is_degraded=current_degraded,
                rows=(
                    FixtureRow(
                        node_ref=node_ref,
                        measure_type=MeasureType.VAR_1D_99,
                        value=current_value,
                        status=SummaryStatus.OK,
                    ),
                ),
            ),
        ),
    )
    return FixtureIndex(pack), d5, d4, node_ref


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------


class SummaryServiceCompleteHistoryTestCase(unittest.TestCase):
    """Four clean window dates (2026-01-02 through 2026-01-08), no degraded rows."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.index = build_fixture_index()

    def _call(self, **kwargs):  # type: ignore[override]
        return get_risk_summary(
            node_ref=desk_toh(),
            measure_type=MeasureType.VAR_1D_99,
            as_of_date=D_08,
            fixture_index=self.index,
            **kwargs,
        )

    def test_returns_risk_summary_instance(self) -> None:
        result = self._call()
        self.assertIsInstance(result, RiskSummary)

    def test_status_is_ok_for_clean_complete_history(self) -> None:
        result = self._call()
        assert isinstance(result, RiskSummary)
        self.assertEqual(result.status, SummaryStatus.OK)
        self.assertEqual(result.status_reasons, ())

    def test_history_points_used_equals_four(self) -> None:
        result = self._call()
        assert isinstance(result, RiskSummary)
        # Window: D_02, D_05, D_06, D_08 — all clean.
        self.assertEqual(result.history_points_used, 4)

    def test_rolling_mean_is_correct(self) -> None:
        result = self._call()
        assert isinstance(result, RiskSummary)
        expected = _mean([40.0, 42.0, 41.0, 43.0])
        self.assertAlmostEqual(result.rolling_mean, expected)

    def test_rolling_std_is_correct(self) -> None:
        result = self._call()
        assert isinstance(result, RiskSummary)
        expected = _std([40.0, 42.0, 41.0, 43.0])
        self.assertAlmostEqual(result.rolling_std, expected)  # type: ignore[arg-type]

    def test_rolling_min_and_max_are_correct(self) -> None:
        result = self._call()
        assert isinstance(result, RiskSummary)
        self.assertAlmostEqual(result.rolling_min, 40.0)
        self.assertAlmostEqual(result.rolling_max, 43.0)

    def test_compare_defaults_to_prior_business_day(self) -> None:
        result = self._call()
        assert isinstance(result, RiskSummary)
        self.assertEqual(result.compare_to_date, D_06)
        self.assertAlmostEqual(result.current_value, 43.0)
        self.assertAlmostEqual(result.previous_value, 41.0)  # type: ignore[arg-type]
        self.assertAlmostEqual(result.delta_abs, 2.0)  # type: ignore[arg-type]
        self.assertAlmostEqual(result.delta_pct, 2.0 / 41.0)  # type: ignore[arg-type]

    def test_explicit_compare_date_is_used(self) -> None:
        result = get_risk_summary(
            node_ref=desk_toh(),
            measure_type=MeasureType.VAR_1D_99,
            as_of_date=D_08,
            compare_to_date=D_02,
            fixture_index=self.index,
        )
        assert isinstance(result, RiskSummary)
        self.assertEqual(result.compare_to_date, D_02)
        self.assertAlmostEqual(result.previous_value, 40.0)  # type: ignore[arg-type]

    def test_top_level_fields_mirror_node_ref(self) -> None:
        node_ref = desk_toh()
        result = self._call()
        assert isinstance(result, RiskSummary)
        self.assertEqual(result.node_ref, node_ref)
        self.assertEqual(result.node_level, node_ref.node_level)
        self.assertEqual(result.hierarchy_scope, node_ref.hierarchy_scope)
        self.assertIsNone(result.legal_entity_id)

    def test_top_level_fields_mirror_legal_entity_node_ref(self) -> None:
        node_ref = desk_le("LE-UK-BANK")
        result = get_risk_summary(
            node_ref=node_ref,
            measure_type=MeasureType.VAR_1D_99,
            as_of_date=D_08,
            compare_to_date=D_06,
            fixture_index=self.index,
        )
        assert isinstance(result, RiskSummary)
        self.assertEqual(result.node_ref, node_ref)
        self.assertEqual(result.node_level, NodeLevel.DESK)
        self.assertEqual(result.hierarchy_scope, HierarchyScope.LEGAL_ENTITY)
        self.assertEqual(result.legal_entity_id, "LE-UK-BANK")

    def test_replay_metadata_fields_populated(self) -> None:
        result = self._call()
        assert isinstance(result, RiskSummary)
        self.assertEqual(result.snapshot_id, "SNAP-2026-01-08")
        self.assertEqual(result.generated_at, datetime(2026, 1, 8, 18, 0, tzinfo=timezone.utc))
        self.assertNotEqual(result.data_version, "")
        self.assertNotEqual(result.service_version, "")

    def test_lookback_window_60_explicit_is_accepted(self) -> None:
        result = get_risk_summary(
            node_ref=desk_toh(),
            measure_type=MeasureType.VAR_1D_99,
            as_of_date=D_08,
            lookback_window=60,
            fixture_index=self.index,
        )
        self.assertIsInstance(result, RiskSummary)


class SummaryServiceRollingWindowEdgeCasesTestCase(unittest.TestCase):
    """One-point and two-point rolling windows."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.index = build_fixture_index()

    def test_two_point_window_rolling_std_defined(self) -> None:
        # as_of_date=D_05: window = [D_02, D_05], two clean points.
        result = get_risk_summary(
            node_ref=desk_toh(),
            measure_type=MeasureType.VAR_1D_99,
            as_of_date=D_05,
            fixture_index=self.index,
        )
        assert isinstance(result, RiskSummary)
        self.assertEqual(result.history_points_used, 2)
        self.assertAlmostEqual(result.rolling_mean, _mean([40.0, 42.0]))
        self.assertAlmostEqual(result.rolling_std, _std([40.0, 42.0]))  # type: ignore[arg-type]
        self.assertAlmostEqual(result.rolling_min, 40.0)
        self.assertAlmostEqual(result.rolling_max, 42.0)
        self.assertEqual(result.status, SummaryStatus.OK)

    def test_one_point_window_rolling_std_is_null(self) -> None:
        # as_of_date=D_02: only one window date (D_02 itself).
        result = get_risk_summary(
            node_ref=desk_toh(),
            measure_type=MeasureType.VAR_1D_99,
            as_of_date=D_02,
            fixture_index=self.index,
        )
        assert isinstance(result, RiskSummary)
        self.assertEqual(result.history_points_used, 1)
        self.assertAlmostEqual(result.rolling_mean, 40.0)
        self.assertIsNone(result.rolling_std)
        self.assertAlmostEqual(result.rolling_min, 40.0)
        self.assertAlmostEqual(result.rolling_max, 40.0)

    def test_one_point_window_status_is_missing_compare(self) -> None:
        # D_02 is the earliest calendar date — no prior business day.
        result = get_risk_summary(
            node_ref=desk_toh(),
            measure_type=MeasureType.VAR_1D_99,
            as_of_date=D_02,
            fixture_index=self.index,
        )
        assert isinstance(result, RiskSummary)
        self.assertEqual(result.status, SummaryStatus.MISSING_COMPARE)
        self.assertIsNone(result.previous_value)
        self.assertIsNone(result.delta_abs)
        self.assertIsNone(result.delta_pct)


class SummaryServiceDegradedHistoryTestCase(unittest.TestCase):
    """History window contains degraded snapshot rows."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.index = build_fixture_index()

    def test_degraded_history_upgrades_status_to_degraded(self) -> None:
        # Window for D_12 includes D_09 (SNAP-2026-01-09 is fully degraded).
        # Explicit compare_to_date=D_08 so compare itself is clean.
        result = get_risk_summary(
            node_ref=desk_toh(),
            measure_type=MeasureType.VAR_1D_99,
            as_of_date=D_12,
            compare_to_date=D_08,
            fixture_index=self.index,
        )
        assert isinstance(result, RiskSummary)
        self.assertEqual(result.status, SummaryStatus.DEGRADED)

    def test_degraded_history_reason_code_present(self) -> None:
        result = get_risk_summary(
            node_ref=desk_toh(),
            measure_type=MeasureType.VAR_1D_99,
            as_of_date=D_12,
            compare_to_date=D_08,
            fixture_index=self.index,
        )
        assert isinstance(result, RiskSummary)
        reasons = " ".join(result.status_reasons)
        self.assertIn("DEGRADED_HISTORY_DATES", reasons)
        self.assertIn("2026-01-09", reasons)

    def test_degraded_history_excluded_from_rolling_stats(self) -> None:
        # D_09 is degraded; valid points for D_12 window are D_02,D_05,D_06,D_08,D_12.
        result = get_risk_summary(
            node_ref=desk_toh(),
            measure_type=MeasureType.VAR_1D_99,
            as_of_date=D_12,
            compare_to_date=D_08,
            fixture_index=self.index,
        )
        assert isinstance(result, RiskSummary)
        expected_values = [40.0, 42.0, 41.0, 43.0, 45.0]  # D_09 (44.0) excluded
        self.assertEqual(result.history_points_used, 5)
        self.assertAlmostEqual(result.rolling_mean, _mean(expected_values))
        self.assertAlmostEqual(result.rolling_std, _std(expected_values))  # type: ignore[arg-type]
        self.assertAlmostEqual(result.rolling_min, 40.0)
        self.assertAlmostEqual(result.rolling_max, 45.0)

    def test_history_points_used_counts_only_valid_points(self) -> None:
        # 6 window dates; 1 degraded (D_09) → 5 valid.
        result = get_risk_summary(
            node_ref=desk_toh(),
            measure_type=MeasureType.VAR_1D_99,
            as_of_date=D_12,
            compare_to_date=D_08,
            fixture_index=self.index,
        )
        assert isinstance(result, RiskSummary)
        self.assertEqual(result.history_points_used, 5)

    def test_degraded_current_snapshot_included_in_degraded_status(self) -> None:
        # as_of_date=D_09: SNAP-2026-01-09 is degraded.
        result = get_risk_summary(
            node_ref=desk_toh(),
            measure_type=MeasureType.VAR_1D_99,
            as_of_date=D_09,
            compare_to_date=D_08,
            fixture_index=self.index,
        )
        assert isinstance(result, RiskSummary)
        self.assertEqual(result.status, SummaryStatus.DEGRADED)
        reasons = " ".join(result.status_reasons)
        self.assertIn("CURRENT_POINT_DEGRADED", reasons)


class SummaryServiceSparseHistoryTestCase(unittest.TestCase):
    """History window has missing calendar dates for the requested node."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.index = build_fixture_index()

    def test_sparse_history_maps_to_degraded(self) -> None:
        # LE-UK-BANK DIV_GM is absent from SNAP-2026-01-02.
        # Window for D_06 = [D_02, D_05, D_06]; D_02 is missing for this node.
        result = get_risk_summary(
            node_ref=division_le("LE-UK-BANK"),
            measure_type=MeasureType.VAR_1D_99,
            as_of_date=D_06,
            compare_to_date=D_05,
            fixture_index=self.index,
        )
        assert isinstance(result, RiskSummary)
        self.assertEqual(result.status, SummaryStatus.DEGRADED)

    def test_sparse_history_reason_code_present(self) -> None:
        result = get_risk_summary(
            node_ref=division_le("LE-UK-BANK"),
            measure_type=MeasureType.VAR_1D_99,
            as_of_date=D_06,
            compare_to_date=D_05,
            fixture_index=self.index,
        )
        assert isinstance(result, RiskSummary)
        reasons = " ".join(result.status_reasons)
        self.assertIn("MISSING_HISTORY_DATES", reasons)
        self.assertIn("2026-01-02", reasons)

    def test_sparse_history_rolling_stats_computed_from_valid_points(self) -> None:
        # Valid points: D_05 (31.0) and D_06 (32.0); D_02 missing.
        result = get_risk_summary(
            node_ref=division_le("LE-UK-BANK"),
            measure_type=MeasureType.VAR_1D_99,
            as_of_date=D_06,
            compare_to_date=D_05,
            fixture_index=self.index,
        )
        assert isinstance(result, RiskSummary)
        self.assertEqual(result.history_points_used, 2)
        self.assertAlmostEqual(result.rolling_mean, _mean([31.0, 32.0]))
        self.assertAlmostEqual(result.rolling_std, _std([31.0, 32.0]))  # type: ignore[arg-type]

    def test_degraded_precedence_beats_missing_compare(self) -> None:
        # LE-UK-BANK DIV_GM at D_05: compare falls on D_02 where node is absent.
        # BOTH DEGRADED (from sparse window) and MISSING_COMPARE conditions apply.
        # DEGRADED must win per precedence.
        result = get_risk_summary(
            node_ref=division_le("LE-UK-BANK"),
            measure_type=MeasureType.VAR_1D_99,
            as_of_date=D_05,
            fixture_index=self.index,
        )
        assert isinstance(result, RiskSummary)
        # compare_to_date = D_02 (prior), no row there → MISSING_COMPARE reason
        # window D_02 also missing → MISSING_HISTORY_DATES reason → DEGRADED
        self.assertEqual(result.status, SummaryStatus.DEGRADED)
        reasons = " ".join(result.status_reasons)
        self.assertIn("MISSING_HISTORY_DATES", reasons)
        self.assertIn("COMPARE_NODE_MEASURE_NOT_FOUND", reasons)

    def test_require_complete_adds_reason_code(self) -> None:
        result = get_risk_summary(
            node_ref=division_le("LE-UK-BANK"),
            measure_type=MeasureType.VAR_1D_99,
            as_of_date=D_06,
            compare_to_date=D_05,
            require_complete=True,
            fixture_index=self.index,
        )
        assert isinstance(result, RiskSummary)
        self.assertEqual(result.status, SummaryStatus.DEGRADED)
        reasons = " ".join(result.status_reasons)
        self.assertIn("REQUIRE_COMPLETE_MISSING_DATES", reasons)


class SummaryServiceMissingCompareTestCase(unittest.TestCase):
    """Compare point absent but no degraded history condition."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.index = build_fixture_index()

    def test_no_prior_business_day_returns_missing_compare(self) -> None:
        # D_02 is the first calendar date; no prior business day.
        result = get_risk_summary(
            node_ref=desk_toh(),
            measure_type=MeasureType.VAR_1D_99,
            as_of_date=D_02,
            fixture_index=self.index,
        )
        assert isinstance(result, RiskSummary)
        self.assertEqual(result.status, SummaryStatus.MISSING_COMPARE)
        self.assertIsNone(result.previous_value)
        self.assertIsNone(result.delta_abs)
        self.assertIsNone(result.delta_pct)

    def test_current_value_still_returned_on_missing_compare(self) -> None:
        result = get_risk_summary(
            node_ref=desk_toh(),
            measure_type=MeasureType.VAR_1D_99,
            as_of_date=D_02,
            fixture_index=self.index,
        )
        assert isinstance(result, RiskSummary)
        self.assertAlmostEqual(result.current_value, 40.0)

    def test_rolling_stats_still_present_on_missing_compare(self) -> None:
        result = get_risk_summary(
            node_ref=desk_toh(),
            measure_type=MeasureType.VAR_1D_99,
            as_of_date=D_02,
            fixture_index=self.index,
        )
        assert isinstance(result, RiskSummary)
        self.assertIsNotNone(result.rolling_mean)
        self.assertEqual(result.history_points_used, 1)


class SummaryServiceErrorPathsTestCase(unittest.TestCase):
    """UNSUPPORTED_MEASURE, MISSING_SNAPSHOT, and MISSING_NODE paths."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.index = build_fixture_index()

    def test_unsupported_measure_returns_service_error(self) -> None:
        result = get_risk_summary(
            node_ref=desk_toh(),
            measure_type=MeasureType.VAR_10D_99,
            as_of_date=D_08,
            fixture_index=self.index,
        )
        self.assertIsInstance(result, ServiceError)
        self.assertEqual(result.operation, "get_risk_summary")
        self.assertEqual(result.status_code, "UNSUPPORTED_MEASURE")

    def test_missing_snapshot_via_explicit_id_returns_service_error(self) -> None:
        result = get_risk_summary(
            node_ref=desk_toh(),
            measure_type=MeasureType.VAR_1D_99,
            as_of_date=D_08,
            snapshot_id="SNAP-NONEXISTENT",
            fixture_index=self.index,
        )
        self.assertIsInstance(result, ServiceError)
        self.assertEqual(result.operation, "get_risk_summary")
        self.assertEqual(result.status_code, "MISSING_SNAPSHOT")
        self.assertIn("ANCHOR_SNAPSHOT_NOT_FOUND:SNAP-NONEXISTENT", result.status_reasons)

    def test_missing_snapshot_via_date_returns_service_error(self) -> None:
        result = get_risk_summary(
            node_ref=desk_toh(),
            measure_type=MeasureType.VAR_1D_99,
            as_of_date=date(2026, 1, 13),
            compare_to_date=D_12,
            fixture_index=self.index,
        )
        self.assertIsInstance(result, ServiceError)
        self.assertEqual(result.status_code, "MISSING_SNAPSHOT")

    def test_missing_node_returns_service_error(self) -> None:
        # LE-UK-BANK DIV_GM absent from SNAP-2026-01-02.
        result = get_risk_summary(
            node_ref=division_le("LE-UK-BANK"),
            measure_type=MeasureType.VAR_1D_99,
            as_of_date=D_02,
            compare_to_date=D_02,
            fixture_index=self.index,
        )
        self.assertIsInstance(result, ServiceError)
        self.assertEqual(result.operation, "get_risk_summary")
        self.assertEqual(result.status_code, "MISSING_NODE")

    def test_service_errors_are_not_risk_summary_objects(self) -> None:
        unsupported = get_risk_summary(
            node_ref=desk_toh(),
            measure_type=MeasureType.VAR_10D_99,
            as_of_date=D_08,
            fixture_index=self.index,
        )
        missing_snap = get_risk_summary(
            node_ref=desk_toh(),
            measure_type=MeasureType.VAR_1D_99,
            as_of_date=D_08,
            snapshot_id="SNAP-NONEXISTENT",
            fixture_index=self.index,
        )
        self.assertNotIsInstance(unsupported, RiskSummary)
        self.assertNotIsInstance(missing_snap, RiskSummary)


class SummaryServiceValidationTestCase(unittest.TestCase):
    """Request validation failures raise ValueError."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.index = build_fixture_index()

    def test_unsupported_lookback_window_raises(self) -> None:
        with self.assertRaises(ValueError):
            get_risk_summary(
                node_ref=desk_toh(),
                measure_type=MeasureType.VAR_1D_99,
                as_of_date=D_08,
                lookback_window=30,
                fixture_index=self.index,
            )

    def test_lookback_window_1_raises(self) -> None:
        with self.assertRaises(ValueError):
            get_risk_summary(
                node_ref=desk_toh(),
                measure_type=MeasureType.VAR_1D_99,
                as_of_date=D_08,
                lookback_window=1,
                fixture_index=self.index,
            )

    def test_blank_snapshot_id_raises(self) -> None:
        with self.assertRaises(ValueError):
            get_risk_summary(
                node_ref=desk_toh(),
                measure_type=MeasureType.VAR_1D_99,
                as_of_date=D_08,
                snapshot_id="   ",
                fixture_index=self.index,
            )

    def test_compare_to_date_after_as_of_date_raises(self) -> None:
        with self.assertRaises(ValueError):
            get_risk_summary(
                node_ref=desk_toh(),
                measure_type=MeasureType.VAR_1D_99,
                as_of_date=D_08,
                compare_to_date=D_12,
                fixture_index=self.index,
            )

    def test_explicit_compare_not_in_calendar_raises(self) -> None:
        # 2026-01-07 (Wednesday) is not in the fixture calendar.
        with self.assertRaises(ValueError):
            get_risk_summary(
                node_ref=desk_toh(),
                measure_type=MeasureType.VAR_1D_99,
                as_of_date=D_08,
                compare_to_date=date(2026, 1, 7),
                fixture_index=self.index,
            )


class SummaryServiceFirstOrderReuseTestCase(unittest.TestCase):
    """get_risk_summary reuses first-order retrieval semantics from get_risk_delta
    without divergence in compare-date handling, delta construction, or status precedence.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.index = build_fixture_index()

    def test_delta_pct_null_when_previous_value_is_zero(self) -> None:
        # BOOK_RATES_EM on D_12 with compare D_08 (value=0.0).
        result = get_risk_summary(
            node_ref=book_toh("BOOK_RATES_EM"),
            measure_type=MeasureType.VAR_1D_99,
            as_of_date=D_12,
            compare_to_date=D_08,
            fixture_index=self.index,
        )
        assert isinstance(result, RiskSummary)
        self.assertAlmostEqual(result.previous_value, 0.0)  # type: ignore[arg-type]
        self.assertIsNone(result.delta_pct)
        self.assertAlmostEqual(result.delta_abs, 16.0)  # type: ignore[arg-type]

    def test_scope_fidelity_top_of_house_vs_legal_entity_differ(self) -> None:
        top = get_risk_summary(
            node_ref=desk_toh(),
            measure_type=MeasureType.VAR_1D_99,
            as_of_date=D_08,
            compare_to_date=D_06,
            fixture_index=self.index,
        )
        le = get_risk_summary(
            node_ref=desk_le("LE-UK-BANK"),
            measure_type=MeasureType.VAR_1D_99,
            as_of_date=D_08,
            compare_to_date=D_06,
            fixture_index=self.index,
        )
        assert isinstance(top, RiskSummary)
        assert isinstance(le, RiskSummary)
        self.assertNotEqual(top.current_value, le.current_value)
        self.assertNotEqual(top.previous_value, le.previous_value)
        self.assertEqual(top.hierarchy_scope, HierarchyScope.TOP_OF_HOUSE)
        self.assertEqual(le.hierarchy_scope, HierarchyScope.LEGAL_ENTITY)
        self.assertIsNone(top.legal_entity_id)
        self.assertEqual(le.legal_entity_id, "LE-UK-BANK")

    def test_degraded_compare_upgrades_status(self) -> None:
        # Default compare for D_12 is D_09 (degraded snapshot).
        result = get_risk_summary(
            node_ref=desk_toh(),
            measure_type=MeasureType.VAR_1D_99,
            as_of_date=D_12,
            fixture_index=self.index,
        )
        assert isinstance(result, RiskSummary)
        self.assertEqual(result.status, SummaryStatus.DEGRADED)
        reasons = " ".join(result.status_reasons)
        self.assertIn("COMPARE_POINT_DEGRADED", reasons)

    def test_negative_prior_uses_abs_denominator(self) -> None:
        index, as_of_date, compare_to_date, node_ref = _make_synthetic_summary_index(
            current_value=2.0,
            previous_value=-4.0,
        )
        result = get_risk_summary(
            node_ref=node_ref,
            measure_type=MeasureType.VAR_1D_99,
            as_of_date=as_of_date,
            compare_to_date=compare_to_date,
            fixture_index=index,
        )
        assert isinstance(result, RiskSummary)
        self.assertEqual(result.delta_abs, 6.0)
        self.assertAlmostEqual(result.delta_pct, 6.0 / 4.0)

    def test_degraded_status_does_not_suppress_delta_when_previous_exists(self) -> None:
        index, as_of_date, compare_to_date, node_ref = _make_synthetic_summary_index(
            current_value=14.0,
            previous_value=10.0,
            current_degraded=True,
        )
        result = get_risk_summary(
            node_ref=node_ref,
            measure_type=MeasureType.VAR_1D_99,
            as_of_date=as_of_date,
            compare_to_date=compare_to_date,
            fixture_index=index,
        )
        assert isinstance(result, RiskSummary)
        self.assertEqual(result.status, SummaryStatus.DEGRADED)
        self.assertEqual(result.delta_abs, 4.0)
        self.assertAlmostEqual(result.delta_pct, 0.4)

    def test_contract_validation_accepts_abs_denominator_for_negative_previous(self) -> None:
        node_ref = desk_toh("DESK_SYNTH_SUMMARY")
        obj = RiskSummary(
            node_ref=node_ref,
            node_level=node_ref.node_level,
            hierarchy_scope=node_ref.hierarchy_scope,
            legal_entity_id=node_ref.legal_entity_id,
            measure_type=MeasureType.VAR_1D_99,
            as_of_date=date(2026, 2, 6),
            compare_to_date=date(2026, 2, 5),
            current_value=2.0,
            previous_value=-4.0,
            delta_abs=6.0,
            delta_pct=1.5,
            rolling_mean=1.0,
            rolling_std=1.0,
            rolling_min=0.0,
            rolling_max=2.0,
            history_points_used=2,
            status=SummaryStatus.OK,
            status_reasons=(),
            snapshot_id="S5",
            data_version="d1",
            service_version="v1",
            generated_at=datetime(2026, 2, 6, 18, 0, tzinfo=timezone.utc),
        )
        self.assertEqual(obj.delta_pct, 1.5)


class SummaryServiceHistoryPointsUsedTestCase(unittest.TestCase):
    """Focused tests on history_points_used invariants."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.index = build_fixture_index()

    def test_history_points_used_is_non_negative(self) -> None:
        result = get_risk_summary(
            node_ref=desk_toh(),
            measure_type=MeasureType.VAR_1D_99,
            as_of_date=D_08,
            fixture_index=self.index,
        )
        assert isinstance(result, RiskSummary)
        self.assertGreaterEqual(result.history_points_used, 0)  # type: ignore[operator]

    def test_history_points_used_does_not_count_degraded_points(self) -> None:
        # Window for D_12 = 6 dates; D_09 is degraded → 5 valid.
        result = get_risk_summary(
            node_ref=desk_toh(),
            measure_type=MeasureType.VAR_1D_99,
            as_of_date=D_12,
            compare_to_date=D_08,
            fixture_index=self.index,
        )
        assert isinstance(result, RiskSummary)
        self.assertEqual(result.history_points_used, 5)

    def test_history_points_used_consistent_with_rolling_stats_availability(self) -> None:
        # If history_points_used >= 1, rolling_mean/min/max must be defined.
        # If history_points_used >= 2, rolling_std must be defined.
        result = get_risk_summary(
            node_ref=desk_toh(),
            measure_type=MeasureType.VAR_1D_99,
            as_of_date=D_08,
            fixture_index=self.index,
        )
        assert isinstance(result, RiskSummary)
        n = result.history_points_used
        if n is not None and n >= 1:
            self.assertIsNotNone(result.rolling_mean)
            self.assertIsNotNone(result.rolling_min)
            self.assertIsNotNone(result.rolling_max)
        if n is not None and n >= 2:
            self.assertIsNotNone(result.rolling_std)

    def test_rolling_std_null_when_fewer_than_two_valid_points(self) -> None:
        # Single-point window: as_of_date = D_02.
        result = get_risk_summary(
            node_ref=desk_toh(),
            measure_type=MeasureType.VAR_1D_99,
            as_of_date=D_02,
            fixture_index=self.index,
        )
        assert isinstance(result, RiskSummary)
        self.assertEqual(result.history_points_used, 1)
        self.assertIsNone(result.rolling_std)


def _summary_log_record(caplog: pytest.LogCaptureFixture) -> tuple[object, dict[str, object]]:
    assert len(caplog.records) == 1
    record = caplog.records[0]
    payload = getattr(record, "structured_event")
    return record, payload


def _assert_summary_log_shape(payload: dict[str, object]) -> None:
    assert set(payload.keys()) == {
        "operation",
        "node_ref",
        "measure_type",
        "as_of_date",
        "compare_to_date",
        "lookback_window",
        "snapshot_id",
        "status",
        "history_points_used",
        "duration_ms",
    }
    assert isinstance(payload["duration_ms"], int)
    assert payload["duration_ms"] >= 0
    node_ref = payload["node_ref"]
    assert isinstance(node_ref, dict)
    assert set(node_ref.keys()) == {"node_id", "node_level", "hierarchy_scope", "legal_entity_id"}
    for forbidden in (
        "points",
        "rows",
        "snapshots",
        "rolling_mean",
        "rolling_std",
        "rolling_min",
        "rolling_max",
        "volatility_regime",
        "volatility_change_flag",
        "current_value",
        "previous_value",
        "delta_abs",
        "delta_pct",
        "trace_id",
        "span_id",
    ):
        assert forbidden not in payload


def test_summary_logging_ok_case(caplog: pytest.LogCaptureFixture) -> None:
    index = build_fixture_index()
    configure_operation_logging(enabled=True, logger=StdlibLoggerAdapter(LOGGER_NAME))
    caplog.set_level(logging.INFO, logger=LOGGER_NAME)

    _ = get_risk_summary(
        node_ref=desk_toh(),
        measure_type=MeasureType.VAR_1D_99,
        as_of_date=D_08,
        fixture_index=index,
    )

    record, payload = _summary_log_record(caplog)
    assert record.levelname == "INFO"
    assert payload["status"] == "OK"
    _assert_summary_log_shape(payload)


def test_summary_logging_error_case(caplog: pytest.LogCaptureFixture) -> None:
    index = build_fixture_index()
    configure_operation_logging(enabled=True, logger=StdlibLoggerAdapter(LOGGER_NAME))
    caplog.set_level(logging.INFO, logger=LOGGER_NAME)

    _ = get_risk_summary(
        node_ref=desk_toh(),
        measure_type=MeasureType.VAR_10D_99,
        as_of_date=D_08,
        fixture_index=index,
    )

    record, payload = _summary_log_record(caplog)
    assert record.levelname == "WARNING"
    assert payload["status"] == "UNSUPPORTED_MEASURE"
    assert payload["history_points_used"] is None
    _assert_summary_log_shape(payload)


if __name__ == "__main__":
    unittest.main()
