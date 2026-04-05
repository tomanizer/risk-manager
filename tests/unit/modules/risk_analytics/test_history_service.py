"""History-service behavior tests."""

from __future__ import annotations

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
        self.assertTrue(
            any("missing history dates in requested range" in reason for reason in series.status_reasons)
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
        self.assertTrue(
            any("require_complete=true" in reason for reason in series.status_reasons)
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
        self.assertTrue(
            any(point.status is SummaryStatus.DEGRADED for point in series.points)
        )

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


if __name__ == "__main__":
    unittest.main()
