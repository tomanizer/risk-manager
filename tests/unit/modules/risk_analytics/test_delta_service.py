"""Delta-service behavior tests for get_risk_delta."""

from __future__ import annotations

import unittest
from datetime import date, datetime, timezone

from src.modules.risk_analytics import get_risk_delta
from src.modules.risk_analytics.contracts import (
    HierarchyScope,
    MeasureType,
    NodeLevel,
    NodeRef,
    RiskDelta,
    SummaryStatus,
)
from src.modules.risk_analytics.fixtures import build_fixture_index
from src.shared import ServiceError


def make_top_of_house_desk(node_id: str = "DESK_RATES_MACRO") -> NodeRef:
    return NodeRef(
        hierarchy_scope=HierarchyScope.TOP_OF_HOUSE,
        legal_entity_id=None,
        node_level=NodeLevel.DESK,
        node_id=node_id,
        node_name="Rates Macro",
    )


def make_legal_entity_desk(legal_entity_id: str) -> NodeRef:
    return NodeRef(
        hierarchy_scope=HierarchyScope.LEGAL_ENTITY,
        legal_entity_id=legal_entity_id,
        node_level=NodeLevel.DESK,
        node_id="DESK_RATES_MACRO",
        node_name="Rates Macro",
    )


def make_legal_entity_division(legal_entity_id: str) -> NodeRef:
    return NodeRef(
        hierarchy_scope=HierarchyScope.LEGAL_ENTITY,
        legal_entity_id=legal_entity_id,
        node_level=NodeLevel.DIVISION,
        node_id="DIV_GM",
        node_name="Global Markets",
    )


def make_top_of_house_book(node_id: str) -> NodeRef:
    return NodeRef(
        hierarchy_scope=HierarchyScope.TOP_OF_HOUSE,
        legal_entity_id=None,
        node_level=NodeLevel.BOOK,
        node_id=node_id,
        node_name="Rates EM",
    )


class DeltaServiceOKCasesTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.index = build_fixture_index()

    def test_compare_defaults_to_prior_business_day(self) -> None:
        result = get_risk_delta(
            node_ref=make_top_of_house_desk(),
            measure_type=MeasureType.VAR_1D_99,
            as_of_date=date(2026, 1, 8),
            fixture_index=self.index,
        )

        self.assertIsInstance(result, RiskDelta)
        self.assertEqual(result.compare_to_date, date(2026, 1, 6))
        self.assertEqual(result.current_value, 43.0)
        self.assertEqual(result.previous_value, 41.0)
        self.assertAlmostEqual(result.delta_abs, 2.0)
        self.assertAlmostEqual(result.delta_pct, 2.0 / 41.0)
        self.assertEqual(result.status, SummaryStatus.OK)
        self.assertEqual(result.status_reasons, ())

    def test_explicit_compare_date_is_used_directly(self) -> None:
        result = get_risk_delta(
            node_ref=make_top_of_house_desk(),
            measure_type=MeasureType.VAR_1D_99,
            as_of_date=date(2026, 1, 12),
            compare_to_date=date(2026, 1, 5),
            fixture_index=self.index,
        )

        self.assertIsInstance(result, RiskDelta)
        self.assertEqual(result.compare_to_date, date(2026, 1, 5))
        self.assertEqual(result.current_value, 45.0)
        self.assertEqual(result.previous_value, 42.0)
        self.assertAlmostEqual(result.delta_abs, 3.0)
        self.assertAlmostEqual(result.delta_pct, 3.0 / 42.0)
        self.assertEqual(result.status, SummaryStatus.OK)

    def test_zero_prior_sets_delta_pct_to_none(self) -> None:
        result = get_risk_delta(
            node_ref=make_top_of_house_book("BOOK_RATES_EM"),
            measure_type=MeasureType.VAR_1D_99,
            as_of_date=date(2026, 1, 12),
            compare_to_date=date(2026, 1, 8),
            fixture_index=self.index,
        )

        self.assertIsInstance(result, RiskDelta)
        self.assertEqual(result.current_value, 16.0)
        self.assertEqual(result.previous_value, 0.0)
        self.assertAlmostEqual(result.delta_abs, 16.0)
        self.assertIsNone(result.delta_pct)
        self.assertEqual(result.status, SummaryStatus.OK)

    def test_mirrored_top_level_fields_populated_from_node_ref(self) -> None:
        node_ref = make_legal_entity_desk("LE-UK-BANK")
        result = get_risk_delta(
            node_ref=node_ref,
            measure_type=MeasureType.VAR_1D_99,
            as_of_date=date(2026, 1, 8),
            compare_to_date=date(2026, 1, 6),
            fixture_index=self.index,
        )

        self.assertIsInstance(result, RiskDelta)
        self.assertEqual(result.node_ref, node_ref)
        self.assertEqual(result.node_level, node_ref.node_level)
        self.assertEqual(result.hierarchy_scope, node_ref.hierarchy_scope)
        self.assertEqual(result.legal_entity_id, node_ref.legal_entity_id)
        self.assertEqual(result.snapshot_id, "SNAP-2026-01-08")
        self.assertEqual(
            result.generated_at,
            datetime(2026, 1, 8, 18, 0, tzinfo=timezone.utc),
        )
        self.assertNotEqual(result.data_version, "")
        self.assertNotEqual(result.service_version, "")

    def test_scope_fidelity_top_of_house_vs_legal_entity_differ(self) -> None:
        top_result = get_risk_delta(
            node_ref=make_top_of_house_desk(),
            measure_type=MeasureType.VAR_1D_99,
            as_of_date=date(2026, 1, 12),
            compare_to_date=date(2026, 1, 5),
            fixture_index=self.index,
        )
        le_result = get_risk_delta(
            node_ref=make_legal_entity_desk("LE-UK-BANK"),
            measure_type=MeasureType.VAR_1D_99,
            as_of_date=date(2026, 1, 12),
            compare_to_date=date(2026, 1, 5),
            fixture_index=self.index,
        )

        self.assertIsInstance(top_result, RiskDelta)
        self.assertIsInstance(le_result, RiskDelta)
        self.assertNotEqual(top_result.current_value, le_result.current_value)
        self.assertNotEqual(top_result.previous_value, le_result.previous_value)
        self.assertEqual(top_result.hierarchy_scope, HierarchyScope.TOP_OF_HOUSE)
        self.assertEqual(le_result.hierarchy_scope, HierarchyScope.LEGAL_ENTITY)
        self.assertIsNone(top_result.legal_entity_id)
        self.assertEqual(le_result.legal_entity_id, "LE-UK-BANK")


class DeltaServiceMissingCompareTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.index = build_fixture_index()

    def test_missing_compare_row_returns_current_and_null_deltas(self) -> None:
        result = get_risk_delta(
            node_ref=make_legal_entity_division("LE-UK-BANK"),
            measure_type=MeasureType.VAR_1D_99,
            as_of_date=date(2026, 1, 5),
            fixture_index=self.index,
        )

        self.assertIsInstance(result, RiskDelta)
        self.assertEqual(result.compare_to_date, date(2026, 1, 2))
        self.assertEqual(result.current_value, 31.0)
        self.assertIsNone(result.previous_value)
        self.assertIsNone(result.delta_abs)
        self.assertIsNone(result.delta_pct)
        self.assertEqual(result.status, SummaryStatus.MISSING_COMPARE)
        self.assertEqual(
            result.status_reasons,
            ("COMPARE_NODE_MEASURE_NOT_FOUND:2026-01-02",),
        )

    def test_degraded_precedence_beats_missing_compare(self) -> None:
        result = get_risk_delta(
            node_ref=make_legal_entity_division("LE-UK-BANK"),
            measure_type=MeasureType.VAR_1D_99,
            as_of_date=date(2026, 1, 9),
            compare_to_date=date(2026, 1, 2),
            fixture_index=self.index,
        )

        self.assertIsInstance(result, RiskDelta)
        self.assertEqual(result.status, SummaryStatus.DEGRADED)
        self.assertIsNone(result.previous_value)
        self.assertIsNone(result.delta_abs)
        self.assertIsNone(result.delta_pct)
        self.assertIn("CURRENT_POINT_DEGRADED:2026-01-09", result.status_reasons)
        self.assertIn("COMPARE_NODE_MEASURE_NOT_FOUND:2026-01-02", result.status_reasons)


class DeltaServiceErrorPathsTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.index = build_fixture_index()

    def test_unsupported_measure_returns_service_error(self) -> None:
        result = get_risk_delta(
            node_ref=make_top_of_house_desk(),
            measure_type=MeasureType.VAR_10D_99,
            as_of_date=date(2026, 1, 8),
            fixture_index=self.index,
        )

        self.assertIsInstance(result, ServiceError)
        self.assertEqual(result.operation, "get_risk_delta")
        self.assertEqual(result.status_code, "UNSUPPORTED_MEASURE")

    def test_missing_snapshot_via_explicit_id_returns_service_error(self) -> None:
        result = get_risk_delta(
            node_ref=make_top_of_house_desk(),
            measure_type=MeasureType.VAR_1D_99,
            as_of_date=date(2026, 1, 8),
            snapshot_id="SNAP-NONEXISTENT",
            fixture_index=self.index,
        )

        self.assertIsInstance(result, ServiceError)
        self.assertEqual(result.operation, "get_risk_delta")
        self.assertEqual(result.status_code, "MISSING_SNAPSHOT")
        self.assertIn("ANCHOR_SNAPSHOT_NOT_FOUND:SNAP-NONEXISTENT", result.status_reasons)

    def test_missing_snapshot_via_date_returns_service_error(self) -> None:
        # 2026-01-13 is not in the fixture calendar at all
        result = get_risk_delta(
            node_ref=make_top_of_house_desk(),
            measure_type=MeasureType.VAR_1D_99,
            as_of_date=date(2026, 1, 13),
            compare_to_date=date(2026, 1, 12),
            fixture_index=self.index,
        )

        self.assertIsInstance(result, ServiceError)
        self.assertEqual(result.operation, "get_risk_delta")
        self.assertEqual(result.status_code, "MISSING_SNAPSHOT")
        self.assertIn("AS_OF_DATE_SNAPSHOT_NOT_FOUND:2026-01-13", result.status_reasons)

    def test_missing_node_returns_service_error(self) -> None:
        # LE-UK-BANK DIV_GM does not appear in SNAP-2026-01-02
        result = get_risk_delta(
            node_ref=make_legal_entity_division("LE-UK-BANK"),
            measure_type=MeasureType.VAR_1D_99,
            as_of_date=date(2026, 1, 2),
            compare_to_date=date(2026, 1, 2),
            fixture_index=self.index,
        )

        self.assertIsInstance(result, ServiceError)
        self.assertEqual(result.operation, "get_risk_delta")
        self.assertEqual(result.status_code, "MISSING_NODE")

    def test_service_errors_are_not_risk_delta_objects(self) -> None:
        unsupported = get_risk_delta(
            node_ref=make_top_of_house_desk(),
            measure_type=MeasureType.VAR_10D_99,
            as_of_date=date(2026, 1, 8),
            fixture_index=self.index,
        )
        missing_snap = get_risk_delta(
            node_ref=make_top_of_house_desk(),
            measure_type=MeasureType.VAR_1D_99,
            as_of_date=date(2026, 1, 8),
            snapshot_id="SNAP-NONEXISTENT",
            fixture_index=self.index,
        )
        missing_node = get_risk_delta(
            node_ref=make_legal_entity_division("LE-UK-BANK"),
            measure_type=MeasureType.VAR_1D_99,
            as_of_date=date(2026, 1, 2),
            compare_to_date=date(2026, 1, 2),
            fixture_index=self.index,
        )

        self.assertNotIsInstance(unsupported, RiskDelta)
        self.assertNotIsInstance(missing_snap, RiskDelta)
        self.assertNotIsInstance(missing_node, RiskDelta)


class DeltaServiceValidationTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.index = build_fixture_index()

    def test_blank_snapshot_id_raises_validation_error(self) -> None:
        with self.assertRaises(ValueError):
            get_risk_delta(
                node_ref=make_top_of_house_desk(),
                measure_type=MeasureType.VAR_1D_99,
                as_of_date=date(2026, 1, 8),
                snapshot_id="   ",
                fixture_index=self.index,
            )

    def test_compare_to_date_after_as_of_date_raises_validation_error(self) -> None:
        with self.assertRaises(ValueError):
            get_risk_delta(
                node_ref=make_top_of_house_desk(),
                measure_type=MeasureType.VAR_1D_99,
                as_of_date=date(2026, 1, 8),
                compare_to_date=date(2026, 1, 12),
                fixture_index=self.index,
            )

    def test_explicit_compare_not_in_calendar_raises_validation_error(self) -> None:
        # 2026-01-07 (Wednesday) is not in the fixture calendar
        with self.assertRaises(ValueError):
            get_risk_delta(
                node_ref=make_top_of_house_desk(),
                measure_type=MeasureType.VAR_1D_99,
                as_of_date=date(2026, 1, 8),
                compare_to_date=date(2026, 1, 7),
                fixture_index=self.index,
            )

    def test_snapshot_id_date_mismatch_raises_validation_error(self) -> None:
        with self.assertRaises(ValueError):
            get_risk_delta(
                node_ref=make_top_of_house_desk(),
                measure_type=MeasureType.VAR_1D_99,
                as_of_date=date(2026, 1, 12),
                snapshot_id="SNAP-2026-01-08",
                fixture_index=self.index,
            )


if __name__ == "__main__":
    unittest.main()
