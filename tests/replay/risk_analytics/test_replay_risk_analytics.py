"""Replay tests for risk analytics service operations.

These tests prove that repeated calls with the same pinned request context
produce identical outputs — deterministic replay is a first-class requirement
per ADR-002 and PRD-1.1-v2.

Each test class pins:
  - operation variant
  - node_ref
  - as_of_date
  - measure_type
  - resolved compare_to_date (explicit, not defaulted, so replay is unambiguous)
  - snapshot_id when provided
  - lookback_window when relevant

Volatility-aware replay tests additionally pin the effective window policy
carried by service_version:
  - baseline_window = 60 business days
  - short_window = 10 business days
  - business-day basis (canonical risk calendar)
  - inclusive anchor on as_of_date

No new evidence or trace fields are introduced. Replayability is satisfied
by the pinned request context here and the replay/version metadata already
on each output contract.
"""

from __future__ import annotations

import unittest
from datetime import date, timedelta

from src.modules.risk_analytics import (
    get_risk_change_profile,
    get_risk_delta,
    get_risk_summary,
)
from src.modules.risk_analytics.contracts import (
    HierarchyScope,
    MeasureType,
    NodeLevel,
    NodeRef,
    RiskChangeProfile,
    RiskDelta,
    RiskSummary,
)
from src.modules.risk_analytics.fixtures import (
    FixtureIndex,
    FixtureRow,
    FixtureSnapshot,
    RiskSummaryFixturePack,
    build_fixture_index,
)
from src.modules.risk_analytics.contracts import SummaryStatus


# ---------------------------------------------------------------------------
# Default-fixture date constants.
# Calendar: 2026-01-02, 2026-01-05, 2026-01-06, 2026-01-08, 2026-01-09, 2026-01-12
# ---------------------------------------------------------------------------

D_02 = date(2026, 1, 2)
D_05 = date(2026, 1, 5)
D_06 = date(2026, 1, 6)
D_08 = date(2026, 1, 8)
D_12 = date(2026, 1, 12)


# ---------------------------------------------------------------------------
# NodeRef helpers
# ---------------------------------------------------------------------------


def desk_toh() -> NodeRef:
    return NodeRef(
        hierarchy_scope=HierarchyScope.TOP_OF_HOUSE,
        legal_entity_id=None,
        node_level=NodeLevel.DESK,
        node_id="DESK_RATES_MACRO",
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


# ---------------------------------------------------------------------------
# Programmatic fixture builder for volatility-aware replay tests.
# Uses >= 20 synthetic business-day dates so volatility flags are classifiable.
# ---------------------------------------------------------------------------


def _make_business_days(n: int, start: date = date(2020, 1, 2)) -> list[date]:
    days: list[date] = []
    d = start
    while len(days) < n:
        if d.weekday() < 5:
            days.append(d)
        d += timedelta(days=1)
    return days


def _make_volatility_replay_index(node_ref: NodeRef) -> FixtureIndex:
    """22-date synthetic fixture used for volatility-aware replay tests.

    Effective window policy (VOLATILITY_RULES_V1):
      baseline_window = 60, short_window = 10,
      business-day basis, inclusive anchor on as_of_date.

    Values: alternating [90.0, 110.0] × 11 → 22 dates.
      - Regime: NORMAL (ratio ≈ 0.093)
      - Change flag: STABLE (ratio ≈ 1.030)
    """
    values = [90.0, 110.0] * 11  # 22 values, last = 110.0
    calendar = _make_business_days(22)
    snapshots = []
    for i, (d, val) in enumerate(zip(calendar, values)):
        row = FixtureRow(
            node_ref=node_ref,
            measure_type=MeasureType.VAR_1D_99,
            value=val,
            status=SummaryStatus.OK,
        )
        snap = FixtureSnapshot(
            snapshot_id=f"REPLAY-{i:04d}",
            as_of_date=d,
            is_degraded=False,
            rows=(row,),
        )
        snapshots.append(snap)
    pack = RiskSummaryFixturePack(
        service_version="v1-replay-test",
        data_version="d1-replay-test",
        calendar=tuple(calendar),
        snapshots=tuple(snapshots),
    )
    return FixtureIndex(pack)


_REPLAY_NODE = NodeRef(
    hierarchy_scope=HierarchyScope.TOP_OF_HOUSE,
    legal_entity_id=None,
    node_level=NodeLevel.DESK,
    node_id="DESK_REPLAY",
    node_name="Replay Desk",
)


# ---------------------------------------------------------------------------
# get_risk_summary replay tests
# ---------------------------------------------------------------------------


class ReplaySummaryTestCase(unittest.TestCase):
    """Two consecutive get_risk_summary calls with pinned context return identical output.

    Pinned request context:
      operation   : get_risk_summary
      node_ref    : DESK_RATES_MACRO / TOP_OF_HOUSE
      as_of_date  : 2026-01-08
      measure_type: VAR_1D_99
      compare_to_date (resolved): 2026-01-06
      lookback_window: 60
      snapshot_id : SNAP-2026-01-08 (explicit pin)
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.index = build_fixture_index()
        cls.node_ref = desk_toh()
        cls.as_of_date = D_08
        cls.compare_to_date = D_06  # explicit: resolved compare, not defaulted
        cls.snapshot_id = "SNAP-2026-01-08"

    def _call(self) -> RiskSummary:
        result = get_risk_summary(
            node_ref=self.node_ref,
            measure_type=MeasureType.VAR_1D_99,
            as_of_date=self.as_of_date,
            compare_to_date=self.compare_to_date,
            lookback_window=60,
            snapshot_id=self.snapshot_id,
            fixture_index=self.index,
        )
        assert isinstance(result, RiskSummary)
        return result

    def test_two_calls_return_identical_current_value(self) -> None:
        self.assertEqual(self._call().current_value, self._call().current_value)

    def test_two_calls_return_identical_previous_value(self) -> None:
        self.assertEqual(self._call().previous_value, self._call().previous_value)

    def test_two_calls_return_identical_delta_abs(self) -> None:
        self.assertEqual(self._call().delta_abs, self._call().delta_abs)

    def test_two_calls_return_identical_rolling_mean(self) -> None:
        self.assertEqual(self._call().rolling_mean, self._call().rolling_mean)

    def test_two_calls_return_identical_rolling_std(self) -> None:
        self.assertEqual(self._call().rolling_std, self._call().rolling_std)

    def test_two_calls_return_identical_status(self) -> None:
        self.assertEqual(self._call().status, self._call().status)

    def test_two_calls_return_identical_snapshot_id(self) -> None:
        self.assertEqual(self._call().snapshot_id, self._call().snapshot_id)

    def test_two_calls_return_identical_service_version(self) -> None:
        self.assertEqual(self._call().service_version, self._call().service_version)

    def test_two_calls_return_identical_generated_at(self) -> None:
        self.assertEqual(self._call().generated_at, self._call().generated_at)

    def test_two_calls_return_identical_history_points_used(self) -> None:
        self.assertEqual(self._call().history_points_used, self._call().history_points_used)


# ---------------------------------------------------------------------------
# get_risk_delta replay tests
# ---------------------------------------------------------------------------


class ReplayDeltaTestCase(unittest.TestCase):
    """Two consecutive get_risk_delta calls with pinned context return identical output.

    Pinned request context:
      operation   : get_risk_delta
      node_ref    : DESK_RATES_MACRO / TOP_OF_HOUSE
      as_of_date  : 2026-01-08
      measure_type: VAR_1D_99
      compare_to_date (resolved): 2026-01-06
      snapshot_id : SNAP-2026-01-08 (explicit pin)
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.index = build_fixture_index()
        cls.node_ref = desk_toh()
        cls.as_of_date = D_08
        cls.compare_to_date = D_06
        cls.snapshot_id = "SNAP-2026-01-08"

    def _call(self) -> RiskDelta:
        result = get_risk_delta(
            node_ref=self.node_ref,
            measure_type=MeasureType.VAR_1D_99,
            as_of_date=self.as_of_date,
            compare_to_date=self.compare_to_date,
            snapshot_id=self.snapshot_id,
            fixture_index=self.index,
        )
        assert isinstance(result, RiskDelta)
        return result

    def test_two_calls_return_identical_current_value(self) -> None:
        self.assertEqual(self._call().current_value, self._call().current_value)

    def test_two_calls_return_identical_previous_value(self) -> None:
        self.assertEqual(self._call().previous_value, self._call().previous_value)

    def test_two_calls_return_identical_delta_abs(self) -> None:
        self.assertEqual(self._call().delta_abs, self._call().delta_abs)

    def test_two_calls_return_identical_status(self) -> None:
        self.assertEqual(self._call().status, self._call().status)

    def test_two_calls_return_identical_snapshot_id(self) -> None:
        self.assertEqual(self._call().snapshot_id, self._call().snapshot_id)

    def test_two_calls_return_identical_service_version(self) -> None:
        self.assertEqual(self._call().service_version, self._call().service_version)

    def test_two_calls_return_identical_generated_at(self) -> None:
        self.assertEqual(self._call().generated_at, self._call().generated_at)


# ---------------------------------------------------------------------------
# get_risk_change_profile replay tests (default fixture, INSUFFICIENT_HISTORY)
# ---------------------------------------------------------------------------


class ReplayChangeProfileDefaultFixtureTestCase(unittest.TestCase):
    """Two consecutive get_risk_change_profile calls against the default pinned
    fixture return identical output.

    The default fixture has 6 calendar dates (< 20 valid baseline points),
    so volatility flags are INSUFFICIENT_HISTORY — but all other fields and
    replay/version metadata must still be identical across calls.

    Pinned request context:
      operation      : get_risk_change_profile
      node_ref       : DESK_RATES_MACRO / TOP_OF_HOUSE
      as_of_date     : 2026-01-08
      measure_type   : VAR_1D_99
      compare_to_date (resolved): 2026-01-06
      lookback_window: 60
      snapshot_id    : SNAP-2026-01-08 (explicit pin)
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.index = build_fixture_index()
        cls.node_ref = desk_toh()
        cls.as_of_date = D_08
        cls.compare_to_date = D_06
        cls.snapshot_id = "SNAP-2026-01-08"

    def _call(self) -> RiskChangeProfile:
        result = get_risk_change_profile(
            node_ref=self.node_ref,
            measure_type=MeasureType.VAR_1D_99,
            as_of_date=self.as_of_date,
            compare_to_date=self.compare_to_date,
            lookback_window=60,
            snapshot_id=self.snapshot_id,
            fixture_index=self.index,
        )
        assert isinstance(result, RiskChangeProfile)
        return result

    def test_two_calls_return_identical_current_value(self) -> None:
        self.assertEqual(self._call().current_value, self._call().current_value)

    def test_two_calls_return_identical_status(self) -> None:
        self.assertEqual(self._call().status, self._call().status)

    def test_two_calls_return_identical_volatility_regime(self) -> None:
        self.assertEqual(self._call().volatility_regime, self._call().volatility_regime)

    def test_two_calls_return_identical_volatility_change_flag(self) -> None:
        self.assertEqual(self._call().volatility_change_flag, self._call().volatility_change_flag)

    def test_two_calls_return_identical_snapshot_id(self) -> None:
        self.assertEqual(self._call().snapshot_id, self._call().snapshot_id)

    def test_two_calls_return_identical_service_version(self) -> None:
        self.assertEqual(self._call().service_version, self._call().service_version)

    def test_two_calls_return_identical_generated_at(self) -> None:
        self.assertEqual(self._call().generated_at, self._call().generated_at)

    def test_two_calls_return_identical_rolling_mean(self) -> None:
        self.assertEqual(self._call().rolling_mean, self._call().rolling_mean)

    def test_two_calls_return_identical_rolling_std(self) -> None:
        self.assertEqual(self._call().rolling_std, self._call().rolling_std)


# ---------------------------------------------------------------------------
# get_risk_change_profile replay tests (volatility-aware, programmatic fixture)
# ---------------------------------------------------------------------------


class ReplayChangeProfileVolatilityAwareTestCase(unittest.TestCase):
    """Volatility-aware replay: pinned synthetic fixture with >= 20 business dates.

    Effective window policy (VOLATILITY_RULES_V1) — pinned by service_version:
      baseline_window = 60 business days
      short_window    = 10 business days
      business-day basis (canonical risk calendar)
      inclusive anchor on as_of_date

    Two consecutive calls against the same pinned fixture_index produce
    identical volatility_regime, volatility_change_flag, rolling statistics,
    and all replay/version metadata.

    Pinned request context:
      operation      : get_risk_change_profile
      node_ref       : DESK_REPLAY / TOP_OF_HOUSE
      measure_type   : VAR_1D_99
      as_of_date     : last date in synthetic 22-date calendar
      compare_to_date (resolved): second-to-last date in synthetic calendar
      lookback_window: 60
      snapshot_id    : last snapshot in synthetic fixture (explicit pin)
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.index = _make_volatility_replay_index(_REPLAY_NODE)
        calendar = list(cls.index.pack.calendar)
        cls.as_of_date = calendar[-1]
        cls.compare_to_date = calendar[-2]
        cls.snapshot_id = cls.index.pack.snapshots[-1].snapshot_id

    def _call(self) -> RiskChangeProfile:
        result = get_risk_change_profile(
            node_ref=_REPLAY_NODE,
            measure_type=MeasureType.VAR_1D_99,
            as_of_date=self.as_of_date,
            compare_to_date=self.compare_to_date,
            lookback_window=60,
            snapshot_id=self.snapshot_id,
            fixture_index=self.index,
        )
        assert isinstance(result, RiskChangeProfile)
        return result

    def test_two_calls_return_identical_volatility_regime(self) -> None:
        self.assertEqual(self._call().volatility_regime, self._call().volatility_regime)

    def test_two_calls_return_identical_volatility_change_flag(self) -> None:
        self.assertEqual(self._call().volatility_change_flag, self._call().volatility_change_flag)

    def test_two_calls_return_identical_rolling_mean(self) -> None:
        self.assertEqual(self._call().rolling_mean, self._call().rolling_mean)

    def test_two_calls_return_identical_rolling_std(self) -> None:
        self.assertEqual(self._call().rolling_std, self._call().rolling_std)

    def test_two_calls_return_identical_rolling_min(self) -> None:
        self.assertEqual(self._call().rolling_min, self._call().rolling_min)

    def test_two_calls_return_identical_rolling_max(self) -> None:
        self.assertEqual(self._call().rolling_max, self._call().rolling_max)

    def test_two_calls_return_identical_history_points_used(self) -> None:
        self.assertEqual(self._call().history_points_used, self._call().history_points_used)

    def test_two_calls_return_identical_current_value(self) -> None:
        self.assertEqual(self._call().current_value, self._call().current_value)

    def test_two_calls_return_identical_previous_value(self) -> None:
        self.assertEqual(self._call().previous_value, self._call().previous_value)

    def test_two_calls_return_identical_delta_abs(self) -> None:
        self.assertEqual(self._call().delta_abs, self._call().delta_abs)

    def test_two_calls_return_identical_status(self) -> None:
        self.assertEqual(self._call().status, self._call().status)

    def test_two_calls_return_identical_snapshot_id(self) -> None:
        self.assertEqual(self._call().snapshot_id, self._call().snapshot_id)

    def test_two_calls_return_identical_service_version(self) -> None:
        self.assertEqual(self._call().service_version, self._call().service_version)

    def test_two_calls_return_identical_generated_at(self) -> None:
        self.assertEqual(self._call().generated_at, self._call().generated_at)

    def test_volatility_regime_is_normal_for_pinned_values(self) -> None:
        # Pinned expectation for the alternating [90,110] value pattern:
        # ratio ≈ 0.093 ∈ [0.05, 0.15) → NORMAL.
        from src.modules.risk_analytics.contracts import VolatilityRegime

        self.assertEqual(self._call().volatility_regime, VolatilityRegime.NORMAL)

    def test_volatility_change_flag_is_stable_for_pinned_values(self) -> None:
        # Pinned expectation: uniform alternating pattern throughout both windows
        # → dispersion_change_ratio ≈ 1.030 ∈ (0.80, 1.20) → STABLE.
        from src.modules.risk_analytics.contracts import VolatilityChangeFlag

        self.assertEqual(self._call().volatility_change_flag, VolatilityChangeFlag.STABLE)

    def test_service_version_is_non_empty(self) -> None:
        # service_version carries the effective volatility policy identifier.
        self.assertNotEqual(self._call().service_version, "")

    def test_history_points_used_equals_22(self) -> None:
        # All 22 synthetic dates are valid (no degraded rows).
        self.assertEqual(self._call().history_points_used, 22)


# ---------------------------------------------------------------------------
# Cross-operation replay consistency
# ---------------------------------------------------------------------------


class ReplayCrossOperationTestCase(unittest.TestCase):
    """Shared fields are consistent across get_risk_summary and get_risk_change_profile
    for identical pinned request context against the same snapshot.

    Both operations share first-order retrieval semantics; this test confirms
    no divergence was introduced by the change-profile implementation.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.index = build_fixture_index()
        cls.node_ref = desk_toh()
        cls.as_of_date = D_08
        cls.compare_to_date = D_06
        cls.snapshot_id = "SNAP-2026-01-08"

    def _summary(self) -> RiskSummary:
        r = get_risk_summary(
            node_ref=self.node_ref,
            measure_type=MeasureType.VAR_1D_99,
            as_of_date=self.as_of_date,
            compare_to_date=self.compare_to_date,
            lookback_window=60,
            snapshot_id=self.snapshot_id,
            fixture_index=self.index,
        )
        assert isinstance(r, RiskSummary)
        return r

    def _profile(self) -> RiskChangeProfile:
        r = get_risk_change_profile(
            node_ref=self.node_ref,
            measure_type=MeasureType.VAR_1D_99,
            as_of_date=self.as_of_date,
            compare_to_date=self.compare_to_date,
            lookback_window=60,
            snapshot_id=self.snapshot_id,
            fixture_index=self.index,
        )
        assert isinstance(r, RiskChangeProfile)
        return r

    def test_current_value_identical_across_operations(self) -> None:
        self.assertEqual(self._summary().current_value, self._profile().current_value)

    def test_previous_value_identical_across_operations(self) -> None:
        self.assertEqual(self._summary().previous_value, self._profile().previous_value)

    def test_delta_abs_identical_across_operations(self) -> None:
        self.assertEqual(self._summary().delta_abs, self._profile().delta_abs)

    def test_rolling_mean_identical_across_operations(self) -> None:
        self.assertEqual(self._summary().rolling_mean, self._profile().rolling_mean)

    def test_rolling_std_identical_across_operations(self) -> None:
        self.assertEqual(self._summary().rolling_std, self._profile().rolling_std)

    def test_history_points_used_identical_across_operations(self) -> None:
        self.assertEqual(self._summary().history_points_used, self._profile().history_points_used)

    def test_status_identical_across_operations(self) -> None:
        self.assertEqual(self._summary().status, self._profile().status)

    def test_snapshot_id_identical_across_operations(self) -> None:
        self.assertEqual(self._summary().snapshot_id, self._profile().snapshot_id)

    def test_service_version_identical_across_operations(self) -> None:
        self.assertEqual(self._summary().service_version, self._profile().service_version)

    def test_generated_at_identical_across_operations(self) -> None:
        self.assertEqual(self._summary().generated_at, self._profile().generated_at)


if __name__ == "__main__":
    unittest.main()
