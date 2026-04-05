"""Fixture loader integrity tests."""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from pydantic import ValidationError

from src.modules.risk_analytics.contracts import (
    HierarchyScope,
    MeasureType,
    NodeLevel,
    NodeRef,
    SummaryStatus,
)
from src.modules.risk_analytics.fixtures import (
    build_fixture_index,
    load_risk_summary_fixture_pack,
    resolve_default_fixture_path,
)


class FixtureLoaderTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.pack = load_risk_summary_fixture_pack()
        cls.index = build_fixture_index()

    def test_fixture_pack_loads_with_pinned_calendar(self) -> None:
        self.assertEqual(len(self.pack.calendar), 6)
        self.assertEqual(self.pack.calendar[0], date(2026, 1, 2))
        self.assertEqual(self.pack.calendar[3], date(2026, 1, 8))

    def test_required_scope_and_hierarchy_coverage_exists(self) -> None:
        levels = set()
        scopes = set()
        legal_entities = set()
        for snapshot in self.pack.snapshots:
            for row in snapshot.rows:
                levels.add(row.node_ref.node_level)
                scopes.add(row.node_ref.hierarchy_scope)
                if row.node_ref.legal_entity_id:
                    legal_entities.add(row.node_ref.legal_entity_id)

        self.assertEqual(scopes, {HierarchyScope.TOP_OF_HOUSE, HierarchyScope.LEGAL_ENTITY})
        self.assertTrue({NodeLevel.FIRM, NodeLevel.DIVISION, NodeLevel.DESK, NodeLevel.BOOK}.issubset(levels))
        self.assertEqual(legal_entities, {"LE-UK-BANK", "LE-US-BROKER"})

    def test_same_logical_desk_differs_by_legal_entity(self) -> None:
        uk_desk = NodeRef(
            hierarchy_scope=HierarchyScope.LEGAL_ENTITY,
            legal_entity_id="LE-UK-BANK",
            node_level=NodeLevel.DESK,
            node_id="DESK_RATES_MACRO",
            node_name="Rates Macro",
        )
        us_desk = NodeRef(
            hierarchy_scope=HierarchyScope.LEGAL_ENTITY,
            legal_entity_id="LE-US-BROKER",
            node_level=NodeLevel.DESK,
            node_id="DESK_RATES_MACRO",
            node_name="Rates Macro",
        )

        uk_row = self.index.get_row("SNAP-2026-01-09", uk_desk, MeasureType.VAR_1D_99)
        us_row = self.index.get_row("SNAP-2026-01-09", us_desk, MeasureType.VAR_1D_99)

        self.assertIsNotNone(uk_row)
        self.assertIsNotNone(us_row)
        self.assertNotEqual(uk_row.value, us_row.value)

    def test_same_node_id_remains_distinct_across_scope(self) -> None:
        top_of_house_desk = NodeRef(
            hierarchy_scope=HierarchyScope.TOP_OF_HOUSE,
            legal_entity_id=None,
            node_level=NodeLevel.DESK,
            node_id="DESK_RATES_MACRO",
            node_name="Rates Macro",
        )
        legal_entity_desk = NodeRef(
            hierarchy_scope=HierarchyScope.LEGAL_ENTITY,
            legal_entity_id="LE-UK-BANK",
            node_level=NodeLevel.DESK,
            node_id="DESK_RATES_MACRO",
            node_name="Rates Macro",
        )

        top_of_house_row = self.index.get_row("SNAP-2026-01-09", top_of_house_desk, MeasureType.VAR_1D_99)
        legal_entity_row = self.index.get_row("SNAP-2026-01-09", legal_entity_desk, MeasureType.VAR_1D_99)

        self.assertIsNotNone(top_of_house_row)
        self.assertIsNotNone(legal_entity_row)
        self.assertNotEqual(top_of_house_row.value, legal_entity_row.value)

    def test_missing_compare_case_is_present(self) -> None:
        node_ref = NodeRef(
            hierarchy_scope=HierarchyScope.TOP_OF_HOUSE,
            legal_entity_id=None,
            node_level=NodeLevel.BOOK,
            node_id="BOOK_NEW_ISSUES",
            node_name="New Issues",
        )

        self.assertIsNone(self.index.get_row_by_date(date(2026, 1, 6), node_ref, MeasureType.VAR_1D_99))
        self.assertIsNotNone(self.index.get_row_by_date(date(2026, 1, 8), node_ref, MeasureType.VAR_1D_99))

    def test_zero_prior_and_degraded_snapshot_cases_are_present(self) -> None:
        node_ref = NodeRef(
            hierarchy_scope=HierarchyScope.TOP_OF_HOUSE,
            legal_entity_id=None,
            node_level=NodeLevel.BOOK,
            node_id="BOOK_RATES_EM",
            node_name="Rates EM",
        )

        prior_row = self.index.get_row_by_date(date(2026, 1, 8), node_ref, MeasureType.VAR_1D_99)
        degraded_row = self.index.get_row_by_date(date(2026, 1, 9), node_ref, MeasureType.VAR_1D_99)

        self.assertIsNotNone(prior_row)
        self.assertEqual(prior_row.value, 0.0)
        self.assertIsNotNone(degraded_row)
        self.assertEqual(degraded_row.status, SummaryStatus.DEGRADED)
        self.assertTrue(self.index.get_snapshot("SNAP-2026-01-09").is_degraded)

    def test_loader_indexes_by_snapshot_and_date(self) -> None:
        node_ref = NodeRef(
            hierarchy_scope=HierarchyScope.TOP_OF_HOUSE,
            legal_entity_id=None,
            node_level=NodeLevel.FIRM,
            node_id="FIRM_GRP",
            node_name="Firm Group",
        )

        by_snapshot = self.index.get_row("SNAP-2026-01-12", node_ref, MeasureType.ES_97_5)
        by_date = self.index.get_row_by_date(date(2026, 1, 12), node_ref, MeasureType.ES_97_5)

        self.assertIsNotNone(by_snapshot)
        self.assertIsNotNone(by_date)
        self.assertEqual(by_snapshot.value, by_date.value)
        self.assertEqual(str(by_snapshot.measure_type), "ES_97_5")

    def test_required_volatility_shape_cases_are_present(self) -> None:
        elevated_volatility_node = NodeRef(
            hierarchy_scope=HierarchyScope.TOP_OF_HOUSE,
            legal_entity_id=None,
            node_level=NodeLevel.DESK,
            node_id="DESK_CREDIT_INDEX",
            node_name="Credit Index",
        )
        stable_context_node = NodeRef(
            hierarchy_scope=HierarchyScope.TOP_OF_HOUSE,
            legal_entity_id=None,
            node_level=NodeLevel.DESK,
            node_id="DESK_MACRO_FLOW",
            node_name="Macro Flow",
        )

        elevated_values = [
            self.index.get_row_by_date(as_of_date, elevated_volatility_node, MeasureType.VAR_1D_99).value for as_of_date in self.pack.calendar
        ]
        stable_values = [
            self.index.get_row_by_date(as_of_date, stable_context_node, MeasureType.VAR_1D_99).value for as_of_date in self.pack.calendar
        ]

        self.assertEqual(elevated_values[-2:], [95.0, 98.0])
        self.assertEqual(max(elevated_values[:-2]) - min(elevated_values[:-2]), 80.0)
        self.assertEqual(stable_values[:-1], [50.0, 51.0, 50.0, 52.0, 53.0])
        self.assertEqual(stable_values[-1] - stable_values[-2], 17.0)

    def test_fixture_pack_rejects_calendar_snapshot_drift(self) -> None:
        payload = json.loads(resolve_default_fixture_path().read_text(encoding="utf-8"))
        payload["calendar"] = payload["calendar"][:-1]

        with tempfile.TemporaryDirectory() as temp_dir:
            fixture_path = Path(temp_dir) / "drifted_fixture_pack.json"
            fixture_path.write_text(json.dumps(payload), encoding="utf-8")

            with self.assertRaises(ValidationError):
                load_risk_summary_fixture_pack(fixture_path)

    def test_fixture_pack_rejects_duplicate_as_of_date(self) -> None:
        payload = json.loads(resolve_default_fixture_path().read_text(encoding="utf-8"))
        # duplicate the first snapshot entry with a different ID but same as_of_date
        duplicate = dict(payload["snapshots"][0])
        duplicate["snapshot_id"] = "SNAP-DUPLICATE"
        payload["snapshots"] = [payload["snapshots"][0], duplicate]

        with tempfile.TemporaryDirectory() as temp_dir:
            fixture_path = Path(temp_dir) / "duplicate_date_fixture_pack.json"
            fixture_path.write_text(json.dumps(payload), encoding="utf-8")

            with self.assertRaises(ValidationError):
                load_risk_summary_fixture_pack(fixture_path)


if __name__ == "__main__":
    unittest.main()
