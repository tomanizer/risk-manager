"""Unit tests for get_risk_change_profile.

Covers all volatility-regime bands, volatility-change-flag bands, both
INSUFFICIENT_HISTORY gates, zero-denominator edge cases for each flag,
all typed service-error paths, both hierarchy scopes, and the status
precedence model.

Positive volatility-band tests use a programmatic FixtureIndex built
inline with >= 20 synthetic business-day dates per the fixture injection
pattern established in test_summary_service.py.
"""

from __future__ import annotations

import unittest
from datetime import date, datetime, timedelta, timezone

from src.modules.risk_analytics import get_risk_change_profile
from src.modules.risk_analytics.contracts import (
    HierarchyScope,
    MeasureType,
    NodeLevel,
    NodeRef,
    RiskChangeProfile,
    SummaryStatus,
    VolatilityChangeFlag,
    VolatilityRegime,
)
from src.modules.risk_analytics.fixtures import (
    FixtureIndex,
    FixtureRow,
    FixtureSnapshot,
    RiskSummaryFixturePack,
    build_fixture_index,
)
from src.shared import ServiceError


# ---------------------------------------------------------------------------
# Default-fixture date constants (6 calendar dates).
# SNAP-2026-01-09 is fully degraded.
# LE-UK-BANK DIV_GM absent from SNAP-2026-01-02.
# ---------------------------------------------------------------------------

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


# Synthetic node used in programmatic-fixture tests.
_SYNTH_NODE = NodeRef(
    hierarchy_scope=HierarchyScope.TOP_OF_HOUSE,
    legal_entity_id=None,
    node_level=NodeLevel.DESK,
    node_id="DESK_SYNTH",
    node_name="Synthetic Desk",
)

_SYNTH_LE_NODE = NodeRef(
    hierarchy_scope=HierarchyScope.LEGAL_ENTITY,
    legal_entity_id="LE-SYNTH",
    node_level=NodeLevel.DESK,
    node_id="DESK_SYNTH_LE",
    node_name="Synthetic LE Desk",
)


# ---------------------------------------------------------------------------
# Programmatic FixtureIndex builder
# ---------------------------------------------------------------------------


def _make_business_days(n: int, start: date = date(2020, 1, 2)) -> list[date]:
    """Return n consecutive Mon–Fri dates starting from start (inclusive)."""
    days: list[date] = []
    d = start
    while len(days) < n:
        if d.weekday() < 5:
            days.append(d)
        d += timedelta(days=1)
    return days


def _make_synthetic_index(
    values: list[float],
    node_ref: NodeRef = _SYNTH_NODE,
    measure_type: MeasureType = MeasureType.VAR_1D_99,
    degraded_indices: list[int] | None = None,
    service_version: str = "v1-synth-test",
    data_version: str = "d1-synth-test",
) -> FixtureIndex:
    """Build a FixtureIndex with len(values) synthetic business-day dates.

    degraded_indices marks specific date positions as is_degraded=True on the
    snapshot level (row still present but excluded from volatility calculations).
    """
    n = len(values)
    assert n >= 5, "pack requires at least 5 calendar dates"
    degraded_set = set(degraded_indices or [])
    calendar = _make_business_days(n)
    snapshots = []
    for i, (d, val) in enumerate(zip(calendar, values)):
        row = FixtureRow(
            node_ref=node_ref,
            measure_type=measure_type,
            value=val,
            status=SummaryStatus.OK,
        )
        snap = FixtureSnapshot(
            snapshot_id=f"SYNTH-{i:04d}",
            as_of_date=d,
            is_degraded=(i in degraded_set),
            rows=(row,),
        )
        snapshots.append(snap)
    pack = RiskSummaryFixturePack(
        service_version=service_version,
        data_version=data_version,
        calendar=tuple(calendar),
        snapshots=tuple(snapshots),
    )
    return FixtureIndex(pack)


# ---------------------------------------------------------------------------
# Value patterns for volatility band tests.
#
# 22-date synthetic fixture: baseline window = all 22 dates (60 >= 22),
# short window = last 10 dates.
#
# Alternating [A, B] × 11 → 22 values, last = B.
#   mean = (A+B)/2, std = (B-A) × sqrt(11/42) ≈ (B-A) × 0.5118
#
# Regime bands (reference_level = max(|current|, |mean|)):
#   LOW     [98, 102]:  std≈2.047, ref=102, ratio≈0.020 <0.05
#   NORMAL  [90, 110]:  std≈10.24, ref=110, ratio≈0.093 ∈[0.05,0.15)
#   ELEVATED[80, 120]:  std≈20.47, ref=120, ratio≈0.171 ∈[0.15,0.30)
#   HIGH    [0,  200]:  std≈102.4, ref=200, ratio≈0.512 ≥0.30
# ---------------------------------------------------------------------------

_LOW_VALUES = [98.0, 102.0] * 11  # current=102
_NORMAL_VALUES = [90.0, 110.0] * 11  # current=110
_ELEVATED_VALUES = [80.0, 120.0] * 11  # current=120
_HIGH_VALUES = [0.0, 200.0] * 11  # current=200

# Zero-denominator regime: reference_level == 0 → current=0, mean=0.
_REF_ZERO_STD_ZERO = [0.0] * 22  # std=0, ref=0 → LOW
# 21 values: 20 alternating [−10, 10] + last 0 → mean=0, std=10, ref=0 → HIGH.
_REF_ZERO_STD_POS = [-10.0, 10.0] * 10 + [0.0]  # 21 values, current=0

# Change-flag band patterns for 22-date fixture.
# STABLE (zero-denom): all equal → both stds = 0 → STABLE.
_FLAG_STABLE_ZERO = [100.0] * 22

# STABLE (non-zero): alternating [95, 105] throughout → ratio ≈ 1.03 ∈ (0.80,1.20).
#   baseline_std ≈ 5.118, short_std ≈ 5.270 (for 10-alt pattern), ratio ≈ 1.030.
_FLAG_STABLE_NONZERO = [95.0, 105.0] * 11  # current=105

# RISING: first 12 = 100, last 10 alternating [0, 200].
#   baseline: 12×100 + 5×0 + 5×200 → std ≈ 69.0
#   short: [0,200]×5 → short_std ≈ 105.4
#   ratio ≈ 1.527 ≥ 1.20 → RISING.
_FLAG_RISING = [100.0] * 12 + [0.0, 200.0] * 5  # current=200

# FALLING: first 12 alternating [0, 200], last 10 = 100.
#   baseline: [0,200]×6 + [100]×10 → std ≈ 75.6
#   short: [100]×10 → short_std = 0
#   ratio = 0 ≤ 0.80 → FALLING.
_FLAG_FALLING = [0.0, 200.0] * 6 + [100.0] * 10  # current=100


# ---------------------------------------------------------------------------
# Helper: call get_risk_change_profile with a synthetic index
# ---------------------------------------------------------------------------


def _call_synth(
    values: list[float],
    node_ref: NodeRef = _SYNTH_NODE,
    degraded_indices: list[int] | None = None,
    compare_to_date: date | None = None,
) -> RiskChangeProfile | ServiceError:
    index = _make_synthetic_index(values, node_ref=node_ref, degraded_indices=degraded_indices)
    calendar = list(index.pack.calendar)
    as_of_date = calendar[-1]
    # Use second-to-last as compare when not specified so delta is available.
    resolved_compare = compare_to_date if compare_to_date is not None else calendar[-2]
    return get_risk_change_profile(
        node_ref=node_ref,
        measure_type=MeasureType.VAR_1D_99,
        as_of_date=as_of_date,
        compare_to_date=resolved_compare,
        fixture_index=index,
    )


# ---------------------------------------------------------------------------
# INSUFFICIENT_HISTORY gate tests
# ---------------------------------------------------------------------------


class ChangeProfileInsufficientHistoryTestCase(unittest.TestCase):
    """Both INSUFFICIENT_HISTORY gates exercised."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.index = build_fixture_index()

    def _call_default(self, as_of_date: date = D_08, **kwargs) -> RiskChangeProfile | ServiceError:
        return get_risk_change_profile(
            node_ref=desk_toh(),
            measure_type=MeasureType.VAR_1D_99,
            as_of_date=as_of_date,
            fixture_index=self.index,
            **kwargs,
        )

    def test_regime_insufficient_history_when_baseline_lt_20_valid_points(self) -> None:
        # Default fixture has 6 calendar dates → at most 4 valid baseline points at D_08.
        result = self._call_default()
        assert isinstance(result, RiskChangeProfile)
        self.assertEqual(result.volatility_regime, VolatilityRegime.INSUFFICIENT_HISTORY)

    def test_change_flag_insufficient_history_when_baseline_lt_20_valid_points(self) -> None:
        result = self._call_default()
        assert isinstance(result, RiskChangeProfile)
        self.assertEqual(result.volatility_change_flag, VolatilityChangeFlag.INSUFFICIENT_HISTORY)

    def test_profile_returned_even_when_volatility_flags_are_insufficient_history(self) -> None:
        result = self._call_default()
        self.assertIsInstance(result, RiskChangeProfile)

    def test_status_ok_when_history_complete_despite_insufficient_volatility_points(self) -> None:
        # As-of D_08 with clean compare (D_06): no degraded/missing → status OK.
        result = self._call_default(compare_to_date=D_06)
        assert isinstance(result, RiskChangeProfile)
        self.assertEqual(result.status, SummaryStatus.OK)
        # Volatility flags still INSUFFICIENT_HISTORY (< 20 valid baseline points).
        self.assertEqual(result.volatility_regime, VolatilityRegime.INSUFFICIENT_HISTORY)
        self.assertEqual(result.volatility_change_flag, VolatilityChangeFlag.INSUFFICIENT_HISTORY)

    def test_change_flag_insufficient_history_via_short_window_gate(self) -> None:
        # 30-date synthetic: baseline window = all 30 dates.
        # Dates 20–26 (7 dates, 0-indexed) are degraded.
        # Short window = last 10 dates (indices 20–29):
        #   valid = indices 27,28,29 → 3 < 5 → INSUFFICIENT_HISTORY for change_flag.
        # Baseline valid = indices 0–19 (20) + 27,28,29 (3) = 23 ≥ 20 → regime not gated.
        n_dates = 30
        values = [100.0] * n_dates
        degraded = list(range(20, 27))  # indices 20–26 degraded
        index = _make_synthetic_index(values, degraded_indices=degraded)
        as_of_date = index.pack.calendar[-1]
        result = get_risk_change_profile(
            node_ref=_SYNTH_NODE,
            measure_type=MeasureType.VAR_1D_99,
            as_of_date=as_of_date,
            compare_to_date=index.pack.calendar[-2],
            fixture_index=index,
        )
        assert isinstance(result, RiskChangeProfile)
        # Baseline has 23 valid points (≥20); regime is classifiable (all-100 → LOW).
        self.assertEqual(result.volatility_regime, VolatilityRegime.LOW)
        # Short window has only 3 valid points (< 5) → INSUFFICIENT_HISTORY.
        self.assertEqual(result.volatility_change_flag, VolatilityChangeFlag.INSUFFICIENT_HISTORY)


# ---------------------------------------------------------------------------
# Volatility-regime band tests (programmatic fixture, >= 20 synthetic dates)
# ---------------------------------------------------------------------------


class ChangeProfileVolatilityRegimeBandTestCase(unittest.TestCase):
    """All four volatility_regime bands plus zero-denominator edge cases."""

    def test_regime_low(self) -> None:
        # [98,102]×11: ratio ≈ 0.020 < 0.05 → LOW.
        result = _call_synth(_LOW_VALUES)
        assert isinstance(result, RiskChangeProfile)
        self.assertEqual(result.volatility_regime, VolatilityRegime.LOW)

    def test_regime_normal(self) -> None:
        # [90,110]×11: ratio ≈ 0.093 ∈ [0.05, 0.15) → NORMAL.
        result = _call_synth(_NORMAL_VALUES)
        assert isinstance(result, RiskChangeProfile)
        self.assertEqual(result.volatility_regime, VolatilityRegime.NORMAL)

    def test_regime_elevated(self) -> None:
        # [80,120]×11: ratio ≈ 0.171 ∈ [0.15, 0.30) → ELEVATED.
        result = _call_synth(_ELEVATED_VALUES)
        assert isinstance(result, RiskChangeProfile)
        self.assertEqual(result.volatility_regime, VolatilityRegime.ELEVATED)

    def test_regime_high(self) -> None:
        # [0,200]×11: ratio ≈ 0.512 ≥ 0.30 → HIGH.
        result = _call_synth(_HIGH_VALUES)
        assert isinstance(result, RiskChangeProfile)
        self.assertEqual(result.volatility_regime, VolatilityRegime.HIGH)

    def test_regime_zero_denominator_both_zero_classifies_low(self) -> None:
        # All zeros: reference_level == 0 and rolling_std == 0 → LOW.
        result = _call_synth(_REF_ZERO_STD_ZERO)
        assert isinstance(result, RiskChangeProfile)
        self.assertEqual(result.volatility_regime, VolatilityRegime.LOW)

    def test_regime_zero_denominator_std_positive_classifies_high(self) -> None:
        # 20×[−10,10] + [0]: current=0, mean=0, ref=0, std=10 > 0 → HIGH.
        result = _call_synth(_REF_ZERO_STD_POS)
        assert isinstance(result, RiskChangeProfile)
        self.assertEqual(result.volatility_regime, VolatilityRegime.HIGH)

    def test_regime_threshold_boundary_low_normal(self) -> None:
        # Alternating [100±d]×11: sample stdev / ref crosses 0.05 near d≈5.14
        # (ref = |current| = 100+d). d=5.13 → ratio < 0.05 → LOW; d=5.14 → NORMAL.
        values_just_below = [100.0 - 5.13, 100.0 + 5.13] * 11
        result_low = _call_synth(values_just_below)
        assert isinstance(result_low, RiskChangeProfile)
        self.assertEqual(result_low.volatility_regime, VolatilityRegime.LOW)

        values_at_boundary = [100.0 - 5.14, 100.0 + 5.14] * 11
        result_normal = _call_synth(values_at_boundary)
        assert isinstance(result_normal, RiskChangeProfile)
        self.assertEqual(result_normal.volatility_regime, VolatilityRegime.NORMAL)

    def test_history_points_used_matches_valid_count(self) -> None:
        result = _call_synth(_NORMAL_VALUES)
        assert isinstance(result, RiskChangeProfile)
        # All 22 values are valid.
        self.assertEqual(result.history_points_used, 22)


# ---------------------------------------------------------------------------
# Volatility-change-flag band tests
# ---------------------------------------------------------------------------


class ChangeProfileVolatilityChangeFlagTestCase(unittest.TestCase):
    """All change-flag bands and zero-denominator edge cases."""

    def test_change_flag_stable_zero_denominator(self) -> None:
        # All-100 → baseline_std=0, short_std=0 → STABLE (zero-denominator rule).
        result = _call_synth(_FLAG_STABLE_ZERO)
        assert isinstance(result, RiskChangeProfile)
        self.assertEqual(result.volatility_change_flag, VolatilityChangeFlag.STABLE)

    def test_change_flag_stable_nonzero(self) -> None:
        # [95,105]×11: ratio ≈ 1.030 ∈ (0.80, 1.20) → STABLE.
        result = _call_synth(_FLAG_STABLE_NONZERO)
        assert isinstance(result, RiskChangeProfile)
        self.assertEqual(result.volatility_change_flag, VolatilityChangeFlag.STABLE)

    def test_change_flag_rising(self) -> None:
        # [100]×12 + [0,200]×5: ratio ≈ 1.527 ≥ 1.20 → RISING.
        result = _call_synth(_FLAG_RISING)
        assert isinstance(result, RiskChangeProfile)
        self.assertEqual(result.volatility_change_flag, VolatilityChangeFlag.RISING)

    def test_change_flag_falling(self) -> None:
        # [0,200]×6 + [100]×10: ratio = 0 ≤ 0.80 → FALLING.
        result = _call_synth(_FLAG_FALLING)
        assert isinstance(result, RiskChangeProfile)
        self.assertEqual(result.volatility_change_flag, VolatilityChangeFlag.FALLING)

    def test_both_flags_computed_independently(self) -> None:
        # RISING has HIGH regime and RISING flag — both are derived independently.
        result = _call_synth(_FLAG_RISING)
        assert isinstance(result, RiskChangeProfile)
        self.assertEqual(result.volatility_regime, VolatilityRegime.HIGH)
        self.assertEqual(result.volatility_change_flag, VolatilityChangeFlag.RISING)


# ---------------------------------------------------------------------------
# Status model tests
# ---------------------------------------------------------------------------


class ChangeProfileStatusModelTestCase(unittest.TestCase):
    """In-object status precedence: DEGRADED > MISSING_COMPARE > OK."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.index = build_fixture_index()

    def test_status_missing_compare_when_no_prior_business_day(self) -> None:
        # D_02 is the earliest calendar date; no prior business day.
        result = get_risk_change_profile(
            node_ref=desk_toh(),
            measure_type=MeasureType.VAR_1D_99,
            as_of_date=D_02,
            fixture_index=self.index,
        )
        assert isinstance(result, RiskChangeProfile)
        self.assertEqual(result.status, SummaryStatus.MISSING_COMPARE)
        self.assertIsNone(result.previous_value)
        self.assertIsNone(result.delta_abs)
        self.assertIsNone(result.delta_pct)

    def test_current_value_present_on_missing_compare(self) -> None:
        result = get_risk_change_profile(
            node_ref=desk_toh(),
            measure_type=MeasureType.VAR_1D_99,
            as_of_date=D_02,
            fixture_index=self.index,
        )
        assert isinstance(result, RiskChangeProfile)
        self.assertAlmostEqual(result.current_value, 40.0)

    def test_status_degraded_when_history_contains_degraded_snapshot(self) -> None:
        # Window for D_12 includes D_09 (SNAP-2026-01-09 fully degraded).
        result = get_risk_change_profile(
            node_ref=desk_toh(),
            measure_type=MeasureType.VAR_1D_99,
            as_of_date=D_12,
            compare_to_date=D_08,
            fixture_index=self.index,
        )
        assert isinstance(result, RiskChangeProfile)
        self.assertEqual(result.status, SummaryStatus.DEGRADED)

    def test_status_degraded_when_current_snapshot_is_degraded(self) -> None:
        # SNAP-2026-01-09 is fully degraded.
        result = get_risk_change_profile(
            node_ref=desk_toh(),
            measure_type=MeasureType.VAR_1D_99,
            as_of_date=D_09,
            compare_to_date=D_08,
            fixture_index=self.index,
        )
        assert isinstance(result, RiskChangeProfile)
        self.assertEqual(result.status, SummaryStatus.DEGRADED)
        reasons = " ".join(result.status_reasons)
        self.assertIn("CURRENT_POINT_DEGRADED", reasons)

    def test_status_ok_with_synthetic_clean_complete_history(self) -> None:
        # 22-date clean synthetic fixture; compare = second-to-last date.
        result = _call_synth(_NORMAL_VALUES)
        assert isinstance(result, RiskChangeProfile)
        self.assertEqual(result.status, SummaryStatus.OK)

    def test_degraded_precedence_over_missing_compare(self) -> None:
        # LE-UK-BANK DIV_GM at D_05: compare defaults to D_02 (node absent there).
        # Window [D_02, D_05] also missing D_02 for this node → DEGRADED beats MISSING_COMPARE.
        result = get_risk_change_profile(
            node_ref=division_le("LE-UK-BANK"),
            measure_type=MeasureType.VAR_1D_99,
            as_of_date=D_05,
            fixture_index=self.index,
        )
        assert isinstance(result, RiskChangeProfile)
        self.assertEqual(result.status, SummaryStatus.DEGRADED)

    def test_require_complete_adds_reason_code(self) -> None:
        result = get_risk_change_profile(
            node_ref=division_le("LE-UK-BANK"),
            measure_type=MeasureType.VAR_1D_99,
            as_of_date=D_06,
            compare_to_date=D_05,
            require_complete=True,
            fixture_index=self.index,
        )
        assert isinstance(result, RiskChangeProfile)
        self.assertEqual(result.status, SummaryStatus.DEGRADED)
        reasons = " ".join(result.status_reasons)
        self.assertIn("REQUIRE_COMPLETE_MISSING_DATES", reasons)


# ---------------------------------------------------------------------------
# Service error paths
# ---------------------------------------------------------------------------


class ChangeProfileServiceErrorTestCase(unittest.TestCase):
    """UNSUPPORTED_MEASURE, MISSING_SNAPSHOT, and MISSING_NODE typed errors."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.index = build_fixture_index()

    def test_unsupported_measure_returns_service_error(self) -> None:
        result = get_risk_change_profile(
            node_ref=desk_toh(),
            measure_type=MeasureType.VAR_10D_99,
            as_of_date=D_08,
            fixture_index=self.index,
        )
        self.assertIsInstance(result, ServiceError)
        self.assertEqual(result.operation, "get_risk_change_profile")
        self.assertEqual(result.status_code, "UNSUPPORTED_MEASURE")

    def test_missing_snapshot_via_explicit_id_returns_service_error(self) -> None:
        result = get_risk_change_profile(
            node_ref=desk_toh(),
            measure_type=MeasureType.VAR_1D_99,
            as_of_date=D_08,
            snapshot_id="SNAP-NONEXISTENT",
            fixture_index=self.index,
        )
        self.assertIsInstance(result, ServiceError)
        self.assertEqual(result.operation, "get_risk_change_profile")
        self.assertEqual(result.status_code, "MISSING_SNAPSHOT")
        self.assertIn("ANCHOR_SNAPSHOT_NOT_FOUND:SNAP-NONEXISTENT", result.status_reasons)

    def test_missing_snapshot_via_date_returns_service_error(self) -> None:
        result = get_risk_change_profile(
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
        result = get_risk_change_profile(
            node_ref=division_le("LE-UK-BANK"),
            measure_type=MeasureType.VAR_1D_99,
            as_of_date=D_02,
            compare_to_date=D_02,
            fixture_index=self.index,
        )
        self.assertIsInstance(result, ServiceError)
        self.assertEqual(result.operation, "get_risk_change_profile")
        self.assertEqual(result.status_code, "MISSING_NODE")

    def test_service_errors_are_not_risk_change_profile_objects(self) -> None:
        unsupported = get_risk_change_profile(
            node_ref=desk_toh(),
            measure_type=MeasureType.VAR_10D_99,
            as_of_date=D_08,
            fixture_index=self.index,
        )
        missing_snap = get_risk_change_profile(
            node_ref=desk_toh(),
            measure_type=MeasureType.VAR_1D_99,
            as_of_date=D_08,
            snapshot_id="SNAP-NONEXISTENT",
            fixture_index=self.index,
        )
        self.assertNotIsInstance(unsupported, RiskChangeProfile)
        self.assertNotIsInstance(missing_snap, RiskChangeProfile)


# ---------------------------------------------------------------------------
# Hierarchy scope tests
# ---------------------------------------------------------------------------


class ChangeProfileHierarchyScopeTestCase(unittest.TestCase):
    """Both TOP_OF_HOUSE and LEGAL_ENTITY scopes exercised."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.index = build_fixture_index()

    def test_top_of_house_scope_resolved_correctly(self) -> None:
        result = get_risk_change_profile(
            node_ref=desk_toh(),
            measure_type=MeasureType.VAR_1D_99,
            as_of_date=D_08,
            compare_to_date=D_06,
            fixture_index=self.index,
        )
        assert isinstance(result, RiskChangeProfile)
        self.assertEqual(result.hierarchy_scope, HierarchyScope.TOP_OF_HOUSE)
        self.assertIsNone(result.legal_entity_id)

    def test_legal_entity_scope_resolved_correctly(self) -> None:
        result = get_risk_change_profile(
            node_ref=desk_le("LE-UK-BANK"),
            measure_type=MeasureType.VAR_1D_99,
            as_of_date=D_08,
            compare_to_date=D_06,
            fixture_index=self.index,
        )
        assert isinstance(result, RiskChangeProfile)
        self.assertEqual(result.hierarchy_scope, HierarchyScope.LEGAL_ENTITY)
        self.assertEqual(result.legal_entity_id, "LE-UK-BANK")

    def test_top_of_house_and_legal_entity_return_different_values(self) -> None:
        toh = get_risk_change_profile(
            node_ref=desk_toh(),
            measure_type=MeasureType.VAR_1D_99,
            as_of_date=D_08,
            compare_to_date=D_06,
            fixture_index=self.index,
        )
        le = get_risk_change_profile(
            node_ref=desk_le("LE-UK-BANK"),
            measure_type=MeasureType.VAR_1D_99,
            as_of_date=D_08,
            compare_to_date=D_06,
            fixture_index=self.index,
        )
        assert isinstance(toh, RiskChangeProfile)
        assert isinstance(le, RiskChangeProfile)
        self.assertNotEqual(toh.current_value, le.current_value)

    def test_legal_entity_scope_with_synthetic_fixture(self) -> None:
        # Confirm LE node resolves correctly through the programmatic path.
        values = [100.0] * 22
        index = _make_synthetic_index(values, node_ref=_SYNTH_LE_NODE)
        calendar = list(index.pack.calendar)
        result = get_risk_change_profile(
            node_ref=_SYNTH_LE_NODE,
            measure_type=MeasureType.VAR_1D_99,
            as_of_date=calendar[-1],
            compare_to_date=calendar[-2],
            fixture_index=index,
        )
        assert isinstance(result, RiskChangeProfile)
        self.assertEqual(result.hierarchy_scope, HierarchyScope.LEGAL_ENTITY)
        self.assertEqual(result.legal_entity_id, "LE-SYNTH")
        self.assertEqual(result.node_level, NodeLevel.DESK)


# ---------------------------------------------------------------------------
# Contract and replay-metadata tests
# ---------------------------------------------------------------------------


class ChangeProfileContractTestCase(unittest.TestCase):
    """Contract fidelity: required fields, replay metadata, and rolling stats."""

    def test_returns_risk_change_profile_instance(self) -> None:
        result = _call_synth(_NORMAL_VALUES)
        self.assertIsInstance(result, RiskChangeProfile)

    def test_all_volatility_and_rolling_fields_present(self) -> None:
        result = _call_synth(_NORMAL_VALUES)
        assert isinstance(result, RiskChangeProfile)
        self.assertIsNotNone(result.volatility_regime)
        self.assertIsNotNone(result.volatility_change_flag)
        self.assertIsNotNone(result.rolling_mean)
        self.assertIsNotNone(result.rolling_std)
        self.assertIsNotNone(result.rolling_min)
        self.assertIsNotNone(result.rolling_max)
        self.assertIsNotNone(result.history_points_used)

    def test_replay_metadata_fields_populated(self) -> None:
        index = build_fixture_index()
        result = get_risk_change_profile(
            node_ref=desk_toh(),
            measure_type=MeasureType.VAR_1D_99,
            as_of_date=D_08,
            compare_to_date=D_06,
            fixture_index=index,
        )
        assert isinstance(result, RiskChangeProfile)
        self.assertEqual(result.snapshot_id, "SNAP-2026-01-08")
        self.assertEqual(result.generated_at, datetime(2026, 1, 8, 18, 0, tzinfo=timezone.utc))
        self.assertNotEqual(result.data_version, "")
        self.assertNotEqual(result.service_version, "")

    def test_node_level_and_scope_mirror_node_ref(self) -> None:
        node_ref = desk_toh()
        result = _call_synth(_NORMAL_VALUES, node_ref=node_ref)
        assert isinstance(result, RiskChangeProfile)
        self.assertEqual(result.node_level, node_ref.node_level)
        self.assertEqual(result.hierarchy_scope, node_ref.hierarchy_scope)
        self.assertEqual(result.node_ref, node_ref)

    def test_delta_abs_and_pct_computed_from_current_and_previous(self) -> None:
        result = _call_synth(_NORMAL_VALUES)
        assert isinstance(result, RiskChangeProfile)
        if result.previous_value is not None:
            expected_abs = result.current_value - result.previous_value
            self.assertAlmostEqual(result.delta_abs, expected_abs)  # type: ignore[arg-type]
            if result.previous_value != 0:
                self.assertAlmostEqual(
                    result.delta_pct,  # type: ignore[arg-type]
                    expected_abs / result.previous_value,
                )

    def test_rolling_std_null_for_single_valid_point(self) -> None:
        # 5-date fixture (minimum pack size), as_of = first date with only 1 window point.
        values = [100.0] * 5
        index = _make_synthetic_index(values)
        first_date = index.pack.calendar[0]
        result = get_risk_change_profile(
            node_ref=_SYNTH_NODE,
            measure_type=MeasureType.VAR_1D_99,
            as_of_date=first_date,
            fixture_index=index,
        )
        assert isinstance(result, RiskChangeProfile)
        self.assertEqual(result.history_points_used, 1)
        self.assertIsNone(result.rolling_std)

    def test_lookback_window_60_explicit_is_accepted(self) -> None:
        index = _make_synthetic_index(_NORMAL_VALUES)
        calendar = list(index.pack.calendar)
        result = get_risk_change_profile(
            node_ref=_SYNTH_NODE,
            measure_type=MeasureType.VAR_1D_99,
            as_of_date=calendar[-1],
            compare_to_date=calendar[-2],
            lookback_window=60,
            fixture_index=index,
        )
        self.assertIsInstance(result, RiskChangeProfile)


# ---------------------------------------------------------------------------
# Request validation tests
# ---------------------------------------------------------------------------


class ChangeProfileValidationTestCase(unittest.TestCase):
    """ValueError raised for invalid request inputs."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.index = build_fixture_index()

    def test_unsupported_lookback_window_raises(self) -> None:
        with self.assertRaises(ValueError):
            get_risk_change_profile(
                node_ref=desk_toh(),
                measure_type=MeasureType.VAR_1D_99,
                as_of_date=D_08,
                lookback_window=30,
                fixture_index=self.index,
            )

    def test_lookback_window_1_raises(self) -> None:
        with self.assertRaises(ValueError):
            get_risk_change_profile(
                node_ref=desk_toh(),
                measure_type=MeasureType.VAR_1D_99,
                as_of_date=D_08,
                lookback_window=1,
                fixture_index=self.index,
            )

    def test_blank_snapshot_id_raises(self) -> None:
        with self.assertRaises(ValueError):
            get_risk_change_profile(
                node_ref=desk_toh(),
                measure_type=MeasureType.VAR_1D_99,
                as_of_date=D_08,
                snapshot_id="   ",
                fixture_index=self.index,
            )

    def test_compare_to_date_after_as_of_date_raises(self) -> None:
        with self.assertRaises(ValueError):
            get_risk_change_profile(
                node_ref=desk_toh(),
                measure_type=MeasureType.VAR_1D_99,
                as_of_date=D_08,
                compare_to_date=D_12,
                fixture_index=self.index,
            )

    def test_explicit_compare_not_in_calendar_raises(self) -> None:
        with self.assertRaises(ValueError):
            get_risk_change_profile(
                node_ref=desk_toh(),
                measure_type=MeasureType.VAR_1D_99,
                as_of_date=D_08,
                compare_to_date=date(2026, 1, 7),
                fixture_index=self.index,
            )


if __name__ == "__main__":
    unittest.main()
