"""Controls integrity fixture pack loader and index tests (WI-2.1.2)."""

from __future__ import annotations

import json
import tempfile
import unittest
from copy import deepcopy
from datetime import date
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker
from pydantic import ValidationError

from src.modules.controls_integrity.contracts import (
    CheckState,
    CheckType,
    ReasonCode,
    REQUIRED_CHECK_ORDER,
)
from src.modules.controls_integrity.fixtures import (
    build_controls_integrity_fixture_index,
    load_controls_integrity_fixture_pack,
    resolve_default_controls_integrity_fixture_path,
)
from src.modules.risk_analytics.contracts import (
    HierarchyScope,
    MeasureType,
    NodeLevel,
    NodeRef,
)


class ControlsIntegrityFixtureLoaderTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.pack = load_controls_integrity_fixture_pack()
        cls.index = build_controls_integrity_fixture_index()

    def test_fixture_pack_pins_calendar_and_basis(self) -> None:
        self.assertEqual(len(self.pack.calendar), 6)
        self.assertEqual(self.pack.calendar[0], date(2026, 1, 2))
        self.assertTrue(self.pack.calendar_basis.strip())
        self.assertIn("risk_analytics", self.pack.calendar_basis)
        self.assertIn("ADR-004", self.pack.calendar_basis)

    def test_pack_metadata_matches_contract(self) -> None:
        self.assertTrue(self.pack.service_version.strip())
        self.assertTrue(self.pack.data_version.strip())

    def test_at_least_two_legal_entities_and_three_distinct_nodes(self) -> None:
        legal_entities: set[str] = set()
        node_ids: set[str] = set()
        for snapshot in self.pack.snapshots:
            for row in snapshot.rows:
                if row.node_ref.legal_entity_id:
                    legal_entities.add(row.node_ref.legal_entity_id)
                node_ids.add(row.node_ref.node_id)
        self.assertGreaterEqual(len(legal_entities), 2)
        self.assertGreaterEqual(len(node_ids), 3)

    def test_scenario_shapes(self) -> None:
        div_gm = NodeRef(
            hierarchy_scope=HierarchyScope.TOP_OF_HOUSE,
            legal_entity_id=None,
            node_level=NodeLevel.DIVISION,
            node_id="DIV_GM",
            node_name="Global Markets",
        )
        m = MeasureType.VAR_1D_99

        snap_pass = "SNAP-2026-01-02"
        d_pass = date(2026, 1, 2)
        for ct in REQUIRED_CHECK_ORDER:
            r = self.index.get_record(div_gm, m, d_pass, snap_pass, ct)
            self.assertIsNotNone(r, ct)
            assert r is not None
            self.assertEqual(r.check_state, CheckState.PASS)
            self.assertFalse(r.is_row_degraded)

        snap_warn = "SNAP-2026-01-05"
        d_warn = date(2026, 1, 5)
        r_comp = self.index.get_record(div_gm, m, d_warn, snap_warn, CheckType.COMPLETENESS)
        self.assertIsNotNone(r_comp)
        assert r_comp is not None
        self.assertEqual(r_comp.check_state, CheckState.WARN)
        self.assertIn(ReasonCode.COMPLETENESS_WARN, r_comp.reason_codes)
        self.assertTrue(r_comp.evidence_refs)

        snap_fail = "SNAP-2026-01-06"
        d_fail = date(2026, 1, 6)
        r_rec = self.index.get_record(div_gm, m, d_fail, snap_fail, CheckType.RECONCILIATION)
        self.assertIsNotNone(r_rec)
        assert r_rec is not None
        self.assertEqual(r_rec.check_state, CheckState.FAIL)
        self.assertIn(ReasonCode.RECONCILIATION_FAIL, r_rec.reason_codes)

        snap_miss = "SNAP-2026-01-08"
        d_miss = date(2026, 1, 8)
        r_lin = self.index.get_record(div_gm, m, d_miss, snap_miss, CheckType.LINEAGE)
        self.assertIsNotNone(r_lin)
        assert r_lin is not None
        self.assertEqual(r_lin.check_state, CheckState.UNKNOWN)
        self.assertIn(ReasonCode.CHECK_RESULT_MISSING, r_lin.reason_codes)
        self.assertEqual(r_lin.evidence_refs, ())

        snap_deg = "SNAP-2026-01-09"
        d_deg = date(2026, 1, 9)
        r_fr = self.index.get_record(div_gm, m, d_deg, snap_deg, CheckType.FRESHNESS)
        self.assertIsNotNone(r_fr)
        assert r_fr is not None
        self.assertTrue(r_fr.is_row_degraded)
        self.assertIn(ReasonCode.CONTROL_ROW_DEGRADED, r_fr.reason_codes)
        self.assertEqual(r_fr.check_state, CheckState.WARN)

    def test_index_lookup_deterministic_order_for_target(self) -> None:
        div_gm = NodeRef(
            hierarchy_scope=HierarchyScope.TOP_OF_HOUSE,
            legal_entity_id=None,
            node_level=NodeLevel.DIVISION,
            node_id="DIV_GM",
            node_name="Global Markets",
        )
        snap = "SNAP-2026-01-02"
        d = date(2026, 1, 2)
        got = self.index.iter_records_for_target(div_gm, MeasureType.VAR_1D_99, d, snap)
        self.assertEqual([r.check_type for r in got], list(REQUIRED_CHECK_ORDER))

    def test_get_record_by_resolved_snapshot(self) -> None:
        div_gm = NodeRef(
            hierarchy_scope=HierarchyScope.TOP_OF_HOUSE,
            legal_entity_id=None,
            node_level=NodeLevel.DIVISION,
            node_id="DIV_GM",
            node_name="Global Markets",
        )
        r = self.index.get_record_by_resolved_snapshot(
            div_gm,
            MeasureType.VAR_1D_99,
            date(2026, 1, 5),
            CheckType.FRESHNESS,
        )
        self.assertIsNotNone(r)
        assert r is not None
        self.assertEqual(r.snapshot_id, "SNAP-2026-01-05")

    def test_duplicate_uniqueness_key_rejected_on_index_build(self) -> None:
        payload = json.loads(resolve_default_controls_integrity_fixture_path().read_text(encoding="utf-8"))
        dup = deepcopy(payload["snapshots"][0]["rows"][0])
        payload["snapshots"][0]["rows"] = list(payload["snapshots"][0]["rows"]) + [dup]

        with tempfile.TemporaryDirectory() as temp_dir:
            p = Path(temp_dir) / "dup.json"
            p.write_text(json.dumps(payload), encoding="utf-8")
            pack = load_controls_integrity_fixture_pack(p)
            with self.assertRaisesRegex(ValueError, "duplicate normalized control row"):
                pack.build_index()

    def test_same_logical_desk_differs_by_legal_entity(self) -> None:
        uk = NodeRef(
            hierarchy_scope=HierarchyScope.LEGAL_ENTITY,
            legal_entity_id="LE-UK-BANK",
            node_level=NodeLevel.DESK,
            node_id="DESK_RATES_MACRO",
            node_name="Rates Macro",
        )
        us = NodeRef(
            hierarchy_scope=HierarchyScope.LEGAL_ENTITY,
            legal_entity_id="LE-US-BROKER",
            node_level=NodeLevel.DESK,
            node_id="DESK_RATES_MACRO",
            node_name="Rates Macro",
        )
        snap = "SNAP-2026-01-12"
        d = date(2026, 1, 12)
        uk_r = self.index.get_record(uk, MeasureType.VAR_1D_99, d, snap, CheckType.COMPLETENESS)
        us_r = self.index.get_record(us, MeasureType.VAR_1D_99, d, snap, CheckType.COMPLETENESS)
        self.assertIsNotNone(uk_r)
        self.assertIsNotNone(us_r)
        assert uk_r is not None and us_r is not None
        self.assertEqual(uk_r.check_state, CheckState.PASS)
        self.assertEqual(us_r.check_state, CheckState.WARN)

    def test_fixture_pack_rejects_calendar_snapshot_drift(self) -> None:
        payload = json.loads(resolve_default_controls_integrity_fixture_path().read_text(encoding="utf-8"))
        payload["calendar"] = payload["calendar"][:-1]

        with tempfile.TemporaryDirectory() as temp_dir:
            fixture_path = Path(temp_dir) / "drifted.json"
            fixture_path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(ValidationError):
                load_controls_integrity_fixture_pack(fixture_path)

    def test_fixture_pack_rejects_empty_calendar_basis(self) -> None:
        payload = json.loads(resolve_default_controls_integrity_fixture_path().read_text(encoding="utf-8"))
        payload["calendar_basis"] = "   "

        with tempfile.TemporaryDirectory() as temp_dir:
            fixture_path = Path(temp_dir) / "bad_basis.json"
            fixture_path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(ValidationError):
                load_controls_integrity_fixture_pack(fixture_path)

    def test_pass_row_rejects_non_empty_reason_codes(self) -> None:
        payload = json.loads(resolve_default_controls_integrity_fixture_path().read_text(encoding="utf-8"))
        row = payload["snapshots"][0]["rows"][0]
        row["reason_codes"] = ["FRESHNESS_WARN"]

        with tempfile.TemporaryDirectory() as temp_dir:
            fixture_path = Path(temp_dir) / "bad_pass.json"
            fixture_path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValidationError, "reason_codes must be empty when check_state is PASS"):
                load_controls_integrity_fixture_pack(fixture_path)

    def test_fixture_pack_matches_standalone_json_schema(self) -> None:
        fixture_path = resolve_default_controls_integrity_fixture_path()
        schema_path = fixture_path.with_name("normalized_controls_fixture_pack.schema.json")
        fixture_payload = json.loads(fixture_path.read_text(encoding="utf-8"))
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        validator = Draft202012Validator(schema, format_checker=FormatChecker())
        errors = sorted(validator.iter_errors(fixture_payload), key=lambda error: tuple(error.path))
        error_details = [{"path": list(error.path), "message": error.message, "value": error.instance} for error in errors]
        self.assertEqual([], errors, f"Schema validation failed: {error_details}")


if __name__ == "__main__":
    unittest.main()
