"""History-service behavior tests."""

from __future__ import annotations

import logging
import unittest
from datetime import date

from src.modules.risk_analytics.contracts import (
    HierarchyScope,
    MeasureType,
    NodeLevel,
    NodeRef,
    SummaryStatus,
)
from src.modules.risk_analytics.fixtures import build_fixture_index
from src.modules.risk_analytics.service import get_risk_history
from src.shared.telemetry import (
    LOGGER_NAME,
    StdlibLoggerAdapter,
    configure_operation_logging,
)


def make_top_of_house_desk(node_id: str = "DESK_RATES_MACRO") -> NodeRef:
    return NodeRef(
        hierarchy_scope=HierarchyScope.TOP_OF_HOUSE,
        legal_entity_id=None,
        node_level=NodeLevel.DESK,
        node_id=node_id,
        node_name="Rates Macro",
    )


class HistoryServiceTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.index = build_fixture_index()

    def test_rejects_invalid_date_range(self) -> None:
        with self.assertRaises(ValueError):
            get_risk_history(
                node_ref=make_top_of_house_desk(),
                measure_type=MeasureType.VAR_1D_99,
                start_date=date(2026, 1, 12),
                end_date=date(2026, 1, 8),
                fixture_index=self.index,
            )

    def test_snapshot_anchor_must_match_end_date(self) -> None:
        with self.assertRaises(ValueError):
            get_risk_history(
                node_ref=make_top_of_house_desk(),
                measure_type=MeasureType.VAR_1D_99,
                start_date=date(2026, 1, 5),
                end_date=date(2026, 1, 12),
                snapshot_id="SNAP-2026-01-09",
                fixture_index=self.index,
            )

    def test_rejects_blank_snapshot_anchor(self) -> None:
        with self.assertRaises(ValueError):
            get_risk_history(
                node_ref=make_top_of_house_desk(),
                measure_type=MeasureType.VAR_1D_99,
                start_date=date(2026, 1, 5),
                end_date=date(2026, 1, 12),
                snapshot_id="  ",
                fixture_index=self.index,
            )

    def test_returns_missing_snapshot_for_unknown_anchor(self) -> None:
        series = get_risk_history(
            node_ref=make_top_of_house_desk(),
            measure_type=MeasureType.VAR_1D_99,
            start_date=date(2026, 1, 5),
            end_date=date(2026, 1, 12),
            snapshot_id="SNAP-DOES-NOT-EXIST",
            fixture_index=self.index,
        )

        self.assertEqual(series.status, SummaryStatus.MISSING_SNAPSHOT)
        self.assertEqual(series.points, ())
        self.assertEqual(
            series.status_reasons,
            ("ANCHOR_SNAPSHOT_NOT_FOUND:SNAP-DOES-NOT-EXIST",),
        )

    def test_returns_missing_snapshot_when_end_date_has_no_anchor_snapshot(self) -> None:
        series = get_risk_history(
            node_ref=make_top_of_house_desk(),
            measure_type=MeasureType.VAR_1D_99,
            start_date=date(2026, 1, 5),
            end_date=date(2026, 1, 7),
            fixture_index=self.index,
        )

        self.assertEqual(series.status, SummaryStatus.MISSING_SNAPSHOT)
        self.assertEqual(series.points, ())
        self.assertEqual(
            series.status_reasons,
            ("END_DATE_SNAPSHOT_NOT_FOUND:2026-01-07",),
        )

    def test_returns_missing_node_when_pinned_context_cannot_resolve_node(self) -> None:
        missing_node = NodeRef(
            hierarchy_scope=HierarchyScope.TOP_OF_HOUSE,
            legal_entity_id=None,
            node_level=NodeLevel.TRADE,
            node_id="TRADE_DOES_NOT_EXIST",
            node_name="Missing Trade",
        )

        series = get_risk_history(
            node_ref=missing_node,
            measure_type=MeasureType.VAR_1D_99,
            start_date=date(2026, 1, 5),
            end_date=date(2026, 1, 12),
            fixture_index=self.index,
        )

        self.assertEqual(series.status, SummaryStatus.MISSING_NODE)
        self.assertEqual(series.points, ())
        self.assertEqual(
            series.status_reasons,
            ("NODE_MEASURE_NOT_IN_PINNED_DATASET_CONTEXT",),
        )

    def test_returns_missing_history_when_node_resolves_but_range_has_no_points(self) -> None:
        node_ref = NodeRef(
            hierarchy_scope=HierarchyScope.TOP_OF_HOUSE,
            legal_entity_id=None,
            node_level=NodeLevel.BOOK,
            node_id="BOOK_NEW_ISSUES",
            node_name="New Issues",
        )

        series = get_risk_history(
            node_ref=node_ref,
            measure_type=MeasureType.VAR_1D_99,
            start_date=date(2026, 1, 2),
            end_date=date(2026, 1, 6),
            fixture_index=self.index,
        )

        self.assertEqual(series.status, SummaryStatus.MISSING_HISTORY)
        self.assertEqual(series.points, ())
        self.assertEqual(series.status_reasons, ("NO_RETURNABLE_POINTS_IN_RANGE",))

    def test_returns_ok_for_complete_non_degraded_history(self) -> None:
        series = get_risk_history(
            node_ref=make_top_of_house_desk(),
            measure_type=MeasureType.VAR_1D_99,
            start_date=date(2026, 1, 2),
            end_date=date(2026, 1, 8),
            fixture_index=self.index,
        )

        self.assertEqual(series.status, SummaryStatus.OK)
        self.assertEqual(series.status_reasons, ())
        self.assertEqual(
            [point.date for point in series.points],
            [date(2026, 1, 2), date(2026, 1, 5), date(2026, 1, 6), date(2026, 1, 8)],
        )

    def test_explicit_snapshot_anchor_can_return_successful_history(self) -> None:
        series = get_risk_history(
            node_ref=make_top_of_house_desk(),
            measure_type=MeasureType.VAR_1D_99,
            start_date=date(2026, 1, 2),
            end_date=date(2026, 1, 8),
            snapshot_id="SNAP-2026-01-08",
            fixture_index=self.index,
        )

        self.assertEqual(series.status, SummaryStatus.OK)
        self.assertEqual(series.status_reasons, ())
        self.assertEqual(
            [point.snapshot_id for point in series.points],
            [
                "SNAP-2026-01-02",
                "SNAP-2026-01-05",
                "SNAP-2026-01-06",
                "SNAP-2026-01-08",
            ],
        )

    def test_returns_partial_for_sparse_history(self) -> None:
        node_ref = NodeRef(
            hierarchy_scope=HierarchyScope.LEGAL_ENTITY,
            legal_entity_id="LE-UK-BANK",
            node_level=NodeLevel.DESK,
            node_id="DESK_RATES_MACRO",
            node_name="New Issues",
        )

        series = get_risk_history(
            node_ref=node_ref,
            measure_type=MeasureType.ES_97_5,
            start_date=date(2026, 1, 2),
            end_date=date(2026, 1, 8),
            fixture_index=self.index,
        )

        self.assertEqual(series.status, SummaryStatus.PARTIAL)
        self.assertEqual(
            [point.date for point in series.points],
            [date(2026, 1, 2), date(2026, 1, 5)],
        )
        self.assertIn(
            "MISSING_DATES:2026-01-06,2026-01-08",
            series.status_reasons,
        )

    def test_require_complete_upgrades_partial_to_degraded(self) -> None:
        node_ref = NodeRef(
            hierarchy_scope=HierarchyScope.LEGAL_ENTITY,
            legal_entity_id="LE-UK-BANK",
            node_level=NodeLevel.DESK,
            node_id="DESK_RATES_MACRO",
            node_name="New Issues",
        )

        series = get_risk_history(
            node_ref=node_ref,
            measure_type=MeasureType.ES_97_5,
            start_date=date(2026, 1, 2),
            end_date=date(2026, 1, 8),
            require_complete=True,
            fixture_index=self.index,
        )

        self.assertEqual(series.status, SummaryStatus.DEGRADED)
        self.assertIn(
            "REQUIRE_COMPLETE_MISSING_DATES:2026-01-06,2026-01-08",
            series.status_reasons,
        )

    def test_returns_degraded_when_history_contains_degraded_rows(self) -> None:
        series = get_risk_history(
            node_ref=make_top_of_house_desk(),
            measure_type=MeasureType.VAR_1D_99,
            start_date=date(2026, 1, 5),
            end_date=date(2026, 1, 12),
            fixture_index=self.index,
        )

        self.assertEqual(series.status, SummaryStatus.DEGRADED)
        self.assertEqual(series.points[0].date, date(2026, 1, 5))
        self.assertEqual(series.points[-1].date, date(2026, 1, 12))
        self.assertEqual(series.points[-1].snapshot_id, "SNAP-2026-01-12")
        degraded_point = next(point for point in series.points if point.date == date(2026, 1, 9))
        self.assertEqual(degraded_point.status, SummaryStatus.DEGRADED)

    def test_scope_fidelity_is_exact(self) -> None:
        top_of_house = make_top_of_house_desk()
        legal_entity = NodeRef(
            hierarchy_scope=HierarchyScope.LEGAL_ENTITY,
            legal_entity_id="LE-UK-BANK",
            node_level=NodeLevel.DESK,
            node_id="DESK_RATES_MACRO",
            node_name="Rates Macro",
        )

        top_series = get_risk_history(
            node_ref=top_of_house,
            measure_type=MeasureType.VAR_1D_99,
            start_date=date(2026, 1, 2),
            end_date=date(2026, 1, 12),
            fixture_index=self.index,
        )
        legal_entity_series = get_risk_history(
            node_ref=legal_entity,
            measure_type=MeasureType.VAR_1D_99,
            start_date=date(2026, 1, 2),
            end_date=date(2026, 1, 12),
            fixture_index=self.index,
        )

        self.assertEqual(top_series.status, SummaryStatus.DEGRADED)
        self.assertEqual(legal_entity_series.status, SummaryStatus.DEGRADED)
        self.assertNotEqual(
            [point.value for point in top_series.points],
            [point.value for point in legal_entity_series.points],
        )

    def test_returns_unsupported_measure_for_measure_not_available_in_fixture_pack(self) -> None:
        series = get_risk_history(
            node_ref=make_top_of_house_desk(),
            measure_type=MeasureType.VAR_10D_99,
            start_date=date(2026, 1, 5),
            end_date=date(2026, 1, 12),
            fixture_index=self.index,
        )

        self.assertEqual(series.status, SummaryStatus.UNSUPPORTED_MEASURE)
        self.assertEqual(series.points, ())
        self.assertEqual(
            series.status_reasons,
            ("UNSUPPORTED_MEASURE_IN_FIXTURE_PACK",),
        )


if __name__ == "__main__":
    unittest.main()


def _history_log_record(caplog):
    assert len(caplog.records) == 1
    record = caplog.records[0]
    payload = getattr(record, "structured_event")
    return record, payload


def _assert_history_log_shape(payload: dict[str, object]) -> None:
    keys = set(payload.keys()) - {"trace_id", "span_id"}
    assert keys == {
        "operation",
        "node_ref",
        "measure_type",
        "start_date",
        "end_date",
        "snapshot_id",
        "status",
        "duration_ms",
    }
    assert isinstance(payload["duration_ms"], int)
    assert payload["duration_ms"] >= 0
    node_ref = payload["node_ref"]
    assert isinstance(node_ref, dict)
    assert set(node_ref.keys()) == {"node_id", "node_level", "hierarchy_scope", "legal_entity_id"}
    for forbidden_key in (
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
    ):
        assert forbidden_key not in payload


def test_history_logging_ok_case(caplog):
    index = build_fixture_index()
    configure_operation_logging(
        enabled=True,
        logger=StdlibLoggerAdapter(LOGGER_NAME),
    )
    caplog.set_level(logging.INFO, logger=LOGGER_NAME)

    _ = get_risk_history(
        node_ref=make_top_of_house_desk(),
        measure_type=MeasureType.VAR_1D_99,
        start_date=date(2026, 1, 2),
        end_date=date(2026, 1, 8),
        fixture_index=index,
    )

    record, payload = _history_log_record(caplog)
    assert record.levelname == "INFO"
    assert payload["status"] == "OK"
    _assert_history_log_shape(payload)


def test_history_logging_error_case(caplog):
    index = build_fixture_index()
    configure_operation_logging(
        enabled=True,
        logger=StdlibLoggerAdapter(LOGGER_NAME),
    )
    caplog.set_level(logging.INFO, logger=LOGGER_NAME)

    _ = get_risk_history(
        node_ref=make_top_of_house_desk(),
        measure_type=MeasureType.VAR_10D_99,
        start_date=date(2026, 1, 5),
        end_date=date(2026, 1, 12),
        fixture_index=index,
    )

    record, payload = _history_log_record(caplog)
    assert record.levelname == "WARNING"
    assert payload["status"] == "UNSUPPORTED_MEASURE"
    _assert_history_log_shape(payload)
