"""Contract instantiation and validation tests."""

from __future__ import annotations

import unittest
from datetime import date, datetime, timezone

from pydantic import ValidationError

from src.modules.risk_analytics.contracts import (
    HierarchyScope,
    MeasureType,
    NodeLevel,
    NodeRef,
    RiskChangeProfile,
    RiskDelta,
    RiskHistoryPoint,
    RiskHistorySeries,
    RiskSummary,
    SummaryStatus,
    VolatilityChangeFlag,
    VolatilityRegime,
)


def make_node_ref() -> NodeRef:
    return NodeRef(
        hierarchy_scope=HierarchyScope.TOP_OF_HOUSE,
        legal_entity_id=None,
        node_level=NodeLevel.DESK,
        node_id="DESK_CREDIT_INDEX",
        node_name="Credit Index",
    )


class ContractTestCase(unittest.TestCase):
    def assert_mirrored_field_mismatch_rejected(self, contract_type: type[RiskDelta | RiskSummary | RiskChangeProfile]) -> None:
        kwargs = {
            "node_ref": make_node_ref(),
            "node_level": NodeLevel.BOOK,
            "measure_type": MeasureType.VAR_1D_99,
            "as_of_date": date(2026, 1, 12),
            "compare_to_date": date(2026, 1, 9),
            "current_value": 98.0,
            "previous_value": 95.0,
            "delta_abs": 3.0,
            "delta_pct": 3.0 / 95.0,
            "status": SummaryStatus.OK,
            "snapshot_id": "SNAP-2026-01-12",
            "data_version": "synthetic-risk-analytics-v1",
            "service_version": "risk-summary-service-v1",
            "generated_at": datetime(2026, 1, 12, 18, 0, tzinfo=timezone.utc),
        }
        if contract_type is RiskSummary:
            kwargs.update(
                {
                    "rolling_mean": 96.6,
                    "rolling_std": 28.0,
                    "rolling_min": 60.0,
                    "rolling_max": 140.0,
                    "history_points_used": 5,
                }
            )
        if contract_type is RiskChangeProfile:
            kwargs.update(
                {
                    "rolling_mean": 96.6,
                    "rolling_std": 28.0,
                    "rolling_min": 60.0,
                    "rolling_max": 140.0,
                    "history_points_used": 5,
                    "volatility_regime": VolatilityRegime.ELEVATED,
                    "volatility_change_flag": VolatilityChangeFlag.STABLE,
                }
            )

        with self.assertRaises(ValidationError):
            contract_type(**kwargs)

    def test_risk_delta_populates_mirror_fields_and_delta_pct(self) -> None:
        risk_delta = RiskDelta(
            node_ref=make_node_ref(),
            measure_type=MeasureType.VAR_1D_99,
            as_of_date=date(2026, 1, 12),
            compare_to_date=date(2026, 1, 9),
            current_value=120.0,
            previous_value=100.0,
            delta_abs=20.0,
            delta_pct=0.2,
            status=SummaryStatus.OK,
            snapshot_id="SNAP-2026-01-12",
            data_version="synthetic-risk-analytics-v1",
            service_version="risk-summary-service-v1",
            generated_at=datetime(2026, 1, 12, 18, 0, tzinfo=timezone.utc),
        )

        self.assertEqual(risk_delta.node_level, NodeLevel.DESK)
        self.assertEqual(risk_delta.hierarchy_scope, HierarchyScope.TOP_OF_HOUSE)
        self.assertIsNone(risk_delta.legal_entity_id)
        self.assertEqual(risk_delta.delta_pct, 0.2)

    def test_risk_delta_sets_delta_pct_to_none_when_previous_is_zero(self) -> None:
        risk_delta = RiskDelta(
            node_ref=make_node_ref(),
            measure_type=MeasureType.VAR_1D_99,
            as_of_date=date(2026, 1, 9),
            compare_to_date=date(2026, 1, 8),
            current_value=15.0,
            previous_value=0.0,
            delta_abs=15.0,
            delta_pct=None,
            status=SummaryStatus.MISSING_COMPARE,
            snapshot_id="SNAP-2026-01-09",
            data_version="synthetic-risk-analytics-v1",
            service_version="risk-summary-service-v1",
            generated_at=datetime(2026, 1, 9, 18, 0, tzinfo=timezone.utc),
        )

        self.assertIsNone(risk_delta.delta_pct)

    def test_risk_delta_derives_delta_fields_when_previous_is_non_zero(self) -> None:
        risk_delta = RiskDelta(
            node_ref=make_node_ref(),
            measure_type=MeasureType.VAR_1D_99,
            as_of_date=date(2026, 1, 12),
            compare_to_date=date(2026, 1, 9),
            current_value=98.0,
            previous_value=95.0,
            delta_abs=None,
            delta_pct=None,
            status=SummaryStatus.OK,
            snapshot_id="SNAP-2026-01-12",
            data_version="synthetic-risk-analytics-v1",
            service_version="risk-summary-service-v1",
            generated_at=datetime(2026, 1, 12, 18, 0, tzinfo=timezone.utc),
        )

        self.assertEqual(risk_delta.delta_abs, 3.0)
        self.assertAlmostEqual(risk_delta.delta_pct, 3.0 / 95.0)

    def test_risk_delta_derives_fields_from_raw_node_ref_input(self) -> None:
        risk_delta = RiskDelta(
            node_ref=make_node_ref().model_dump(mode="python"),
            measure_type=MeasureType.VAR_1D_99,
            as_of_date=date(2026, 1, 12),
            compare_to_date=date(2026, 1, 9),
            current_value=98.0,
            previous_value=95.0,
            delta_abs=None,
            delta_pct=None,
            status=SummaryStatus.OK,
            snapshot_id="SNAP-2026-01-12",
            data_version="synthetic-risk-analytics-v1",
            service_version="risk-summary-service-v1",
            generated_at=datetime(2026, 1, 12, 18, 0, tzinfo=timezone.utc),
        )

        self.assertEqual(risk_delta.node_level, NodeLevel.DESK)
        self.assertEqual(risk_delta.hierarchy_scope, HierarchyScope.TOP_OF_HOUSE)
        self.assertIsNone(risk_delta.legal_entity_id)
        self.assertEqual(risk_delta.delta_abs, 3.0)
        self.assertAlmostEqual(risk_delta.delta_pct, 3.0 / 95.0)

    def test_risk_delta_accepts_close_float_inputs(self) -> None:
        risk_delta = RiskDelta(
            node_ref=make_node_ref(),
            measure_type=MeasureType.VAR_1D_99,
            as_of_date=date(2026, 1, 12),
            compare_to_date=date(2026, 1, 9),
            current_value=0.3,
            previous_value=0.1,
            delta_abs=0.2 + 1e-13,
            delta_pct=2.0 + 1e-12,
            status=SummaryStatus.OK,
            snapshot_id="SNAP-2026-01-12",
            data_version="synthetic-risk-analytics-v1",
            service_version="risk-summary-service-v1",
            generated_at=datetime(2026, 1, 12, 18, 0, tzinfo=timezone.utc),
        )

        self.assertAlmostEqual(risk_delta.delta_abs, 0.2 + 1e-13)
        self.assertAlmostEqual(risk_delta.delta_pct, 2.0 + 1e-12)

    def test_risk_delta_rejects_non_null_delta_pct_when_previous_is_zero(self) -> None:
        with self.assertRaises(ValidationError):
            RiskDelta(
                node_ref=make_node_ref(),
                measure_type=MeasureType.VAR_1D_99,
                as_of_date=date(2026, 1, 9),
                compare_to_date=date(2026, 1, 8),
                current_value=15.0,
                previous_value=0.0,
                delta_abs=15.0,
                delta_pct=1.0,
                status=SummaryStatus.OK,
                snapshot_id="SNAP-2026-01-09",
                data_version="synthetic-risk-analytics-v1",
                service_version="risk-summary-service-v1",
                generated_at=datetime(2026, 1, 9, 18, 0, tzinfo=timezone.utc),
            )

    def test_risk_summary_instantiates_with_missing_history_fields(self) -> None:
        risk_summary = RiskSummary(
            node_ref=make_node_ref(),
            measure_type=MeasureType.VAR_1D_99,
            as_of_date=date(2026, 1, 8),
            compare_to_date=date(2026, 1, 6),
            current_value=90.0,
            previous_value=140.0,
            delta_abs=-50.0,
            delta_pct=-50.0 / 140.0,
            rolling_mean=96.6666666667,
            rolling_std=None,
            rolling_min=60.0,
            rolling_max=140.0,
            history_points_used=3,
            status=SummaryStatus.MISSING_HISTORY,
            status_reasons=("insufficient lookback",),
            snapshot_id="SNAP-2026-01-08",
            data_version="synthetic-risk-analytics-v1",
            service_version="risk-summary-service-v1",
            generated_at=datetime(2026, 1, 8, 18, 0, tzinfo=timezone.utc),
        )

        self.assertEqual(risk_summary.history_points_used, 3)
        self.assertEqual(risk_summary.status, SummaryStatus.MISSING_HISTORY)

    def test_risk_change_profile_remains_distinct(self) -> None:
        profile = RiskChangeProfile(
            node_ref=make_node_ref(),
            measure_type=MeasureType.VAR_1D_99,
            as_of_date=date(2026, 1, 12),
            compare_to_date=date(2026, 1, 9),
            current_value=98.0,
            previous_value=95.0,
            delta_abs=3.0,
            delta_pct=3.0 / 95.0,
            rolling_mean=96.6,
            rolling_std=28.0,
            rolling_min=60.0,
            rolling_max=140.0,
            history_points_used=5,
            volatility_regime=VolatilityRegime.ELEVATED,
            volatility_change_flag=VolatilityChangeFlag.STABLE,
            status=SummaryStatus.OK,
            snapshot_id="SNAP-2026-01-12",
            data_version="synthetic-risk-analytics-v1",
            service_version="risk-summary-service-v1",
            generated_at=datetime(2026, 1, 12, 18, 0, tzinfo=timezone.utc),
        )

        self.assertEqual(profile.volatility_regime, VolatilityRegime.ELEVATED)
        self.assertEqual(profile.volatility_change_flag, VolatilityChangeFlag.STABLE)

    def test_history_contracts_instantiate_cleanly(self) -> None:
        point_one = RiskHistoryPoint(
            node_ref=make_node_ref(),
            measure_type=MeasureType.VAR_1D_99,
            date=date(2026, 1, 8),
            value=90.0,
            snapshot_id="SNAP-2026-01-08",
            status=SummaryStatus.OK,
        )
        point_two = RiskHistoryPoint(
            node_ref=make_node_ref(),
            measure_type=MeasureType.VAR_1D_99,
            date=date(2026, 1, 9),
            value=95.0,
            snapshot_id="SNAP-2026-01-09",
            status=SummaryStatus.DEGRADED,
        )

        series = RiskHistorySeries(
            node_ref=make_node_ref(),
            measure_type=MeasureType.VAR_1D_99,
            start_date=date(2026, 1, 8),
            end_date=date(2026, 1, 9),
            points=(point_one, point_two),
            status=SummaryStatus.DEGRADED,
            status_reasons=("snapshot partial",),
            service_version="risk-summary-service-v1",
        )

        self.assertEqual(len(series.points), 2)

    def test_history_series_rejects_unordered_points(self) -> None:
        point_one = RiskHistoryPoint(
            node_ref=make_node_ref(),
            measure_type=MeasureType.VAR_1D_99,
            date=date(2026, 1, 9),
            value=95.0,
            snapshot_id="SNAP-2026-01-09",
            status=SummaryStatus.DEGRADED,
        )
        point_two = RiskHistoryPoint(
            node_ref=make_node_ref(),
            measure_type=MeasureType.VAR_1D_99,
            date=date(2026, 1, 8),
            value=90.0,
            snapshot_id="SNAP-2026-01-08",
            status=SummaryStatus.OK,
        )

        with self.assertRaises(ValidationError):
            RiskHistorySeries(
                node_ref=make_node_ref(),
                measure_type=MeasureType.VAR_1D_99,
                start_date=date(2026, 1, 8),
                end_date=date(2026, 1, 9),
                points=(point_one, point_two),
                status=SummaryStatus.OK,
                service_version="risk-summary-service-v1",
            )

    def test_history_series_rejects_points_outside_range(self) -> None:
        point = RiskHistoryPoint(
            node_ref=make_node_ref(),
            measure_type=MeasureType.VAR_1D_99,
            date=date(2026, 1, 7),
            value=90.0,
            snapshot_id="SNAP-2026-01-08",
            status=SummaryStatus.OK,
        )

        with self.assertRaises(ValidationError):
            RiskHistorySeries(
                node_ref=make_node_ref(),
                measure_type=MeasureType.VAR_1D_99,
                start_date=date(2026, 1, 8),
                end_date=date(2026, 1, 9),
                points=(point,),
                status=SummaryStatus.OK,
                service_version="risk-summary-service-v1",
            )

    def test_risk_delta_rejects_mirrored_field_mismatch(self) -> None:
        self.assert_mirrored_field_mismatch_rejected(RiskDelta)

    def test_risk_summary_rejects_mirrored_field_mismatch(self) -> None:
        self.assert_mirrored_field_mismatch_rejected(RiskSummary)

    def test_risk_change_profile_rejects_mirrored_field_mismatch(self) -> None:
        self.assert_mirrored_field_mismatch_rejected(RiskChangeProfile)


if __name__ == "__main__":
    unittest.main()
