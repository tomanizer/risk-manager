"""Replay tests for ``get_integrity_assessment``.

Repeated calls with the same pinned request context and the same fixture indices
must return identical ``IntegrityAssessment`` objects — deterministic replay
per ADR-002 and PRD-2.1.

Each scenario pins:
  - ``node_ref``, ``measure_type``, ``as_of_date``
  - explicit ``snapshot_id`` where the pack defines one per date
  - default Phase 1 risk fixture index and normalized controls fixture index

Additional replay coverage proves fixture-backed **degraded** assessments
(``assessment_status == DEGRADED``) remain stable across calls, including
``UNRESOLVED`` trust and CAUTION with degraded rows.
"""

from __future__ import annotations

import unittest
from datetime import date

from src.modules.controls_integrity import REQUIRED_CHECK_ORDER, get_integrity_assessment
from src.modules.controls_integrity.contracts import IntegrityAssessment
from src.modules.controls_integrity.fixtures import build_controls_integrity_fixture_index
from src.modules.risk_analytics.contracts import HierarchyScope, MeasureType, NodeLevel, NodeRef
from src.modules.risk_analytics.fixtures import build_fixture_index

D_02 = date(2026, 1, 2)
D_05 = date(2026, 1, 5)
D_06 = date(2026, 1, 6)
D_08 = date(2026, 1, 8)
D_09 = date(2026, 1, 9)


def firm_grp() -> NodeRef:
    return NodeRef(
        hierarchy_scope=HierarchyScope.TOP_OF_HOUSE,
        legal_entity_id=None,
        node_level=NodeLevel.FIRM,
        node_id="FIRM_GRP",
        node_name="Firm Group",
    )


def division_toh() -> NodeRef:
    return NodeRef(
        hierarchy_scope=HierarchyScope.TOP_OF_HOUSE,
        legal_entity_id=None,
        node_level=NodeLevel.DIVISION,
        node_id="DIV_GM",
        node_name="Global Markets",
    )


def assert_controls_integrity_replay_equal(first: IntegrityAssessment, second: IntegrityAssessment) -> None:
    """WI-2.1.4 replay assertions: metadata, trust, ordering, check rows, aggregate reason codes."""
    assert first.snapshot_id == second.snapshot_id
    assert first.data_version == second.data_version
    assert first.service_version == second.service_version
    assert first.generated_at == second.generated_at
    assert first.trust_state == second.trust_state
    assert first.false_signal_risk == second.false_signal_risk
    assert first.assessment_status == second.assessment_status

    assert [c.check_type for c in first.check_results] == list(REQUIRED_CHECK_ORDER)
    assert [c.check_type for c in second.check_results] == list(REQUIRED_CHECK_ORDER)
    assert first.check_results == second.check_results

    assert first.blocking_reason_codes == second.blocking_reason_codes
    assert first.cautionary_reason_codes == second.cautionary_reason_codes
    assert tuple(first.blocking_reason_codes) == tuple(sorted(set(first.blocking_reason_codes), key=lambda x: x.value))
    assert tuple(first.cautionary_reason_codes) == tuple(sorted(set(first.cautionary_reason_codes), key=lambda x: x.value))

    assert first == second


class ReplayIntegrityTrustedTestCase(unittest.TestCase):
    """TRUSTED: firm / TOP_OF_HOUSE, all required checks PASS."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.risk_index = build_fixture_index()
        cls.controls_index = build_controls_integrity_fixture_index()
        cls.node_ref = firm_grp()
        cls.as_of_date = D_02
        cls.snapshot_id = "SNAP-2026-01-02"

    def _call(self) -> IntegrityAssessment:
        out = get_integrity_assessment(
            self.node_ref,
            MeasureType.VAR_1D_99,
            self.as_of_date,
            self.snapshot_id,
            risk_fixture_index=self.risk_index,
            controls_fixture_index=self.controls_index,
        )
        self.assertIsInstance(out, IntegrityAssessment)
        return out

    def test_two_calls_identical_integrity_assessment(self) -> None:
        assert_controls_integrity_replay_equal(self._call(), self._call())


class ReplayIntegrityCautionTestCase(unittest.TestCase):
    """CAUTION: division / TOP_OF_HOUSE with WARN on completeness (assessment OK)."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.risk_index = build_fixture_index()
        cls.controls_index = build_controls_integrity_fixture_index()
        cls.node_ref = division_toh()
        cls.as_of_date = D_05
        cls.snapshot_id = "SNAP-2026-01-05"

    def _call(self) -> IntegrityAssessment:
        out = get_integrity_assessment(
            self.node_ref,
            MeasureType.VAR_1D_99,
            self.as_of_date,
            self.snapshot_id,
            risk_fixture_index=self.risk_index,
            controls_fixture_index=self.controls_index,
        )
        self.assertIsInstance(out, IntegrityAssessment)
        return out

    def test_two_calls_identical_integrity_assessment(self) -> None:
        assert_controls_integrity_replay_equal(self._call(), self._call())


class ReplayIntegrityBlockedTestCase(unittest.TestCase):
    """BLOCKED: division / TOP_OF_HOUSE with FAIL on reconciliation."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.risk_index = build_fixture_index()
        cls.controls_index = build_controls_integrity_fixture_index()
        cls.node_ref = division_toh()
        cls.as_of_date = D_06
        cls.snapshot_id = "SNAP-2026-01-06"

    def _call(self) -> IntegrityAssessment:
        out = get_integrity_assessment(
            self.node_ref,
            MeasureType.VAR_1D_99,
            self.as_of_date,
            self.snapshot_id,
            risk_fixture_index=self.risk_index,
            controls_fixture_index=self.controls_index,
        )
        self.assertIsInstance(out, IntegrityAssessment)
        return out

    def test_two_calls_identical_integrity_assessment(self) -> None:
        assert_controls_integrity_replay_equal(self._call(), self._call())


class ReplayIntegrityUnresolvedTestCase(unittest.TestCase):
    """UNRESOLVED + DEGRADED assessment: LINEAGE UNKNOWN with CHECK_RESULT_MISSING."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.risk_index = build_fixture_index()
        cls.controls_index = build_controls_integrity_fixture_index()
        cls.node_ref = division_toh()
        cls.as_of_date = D_08
        cls.snapshot_id = "SNAP-2026-01-08"

    def _call(self) -> IntegrityAssessment:
        out = get_integrity_assessment(
            self.node_ref,
            MeasureType.VAR_1D_99,
            self.as_of_date,
            self.snapshot_id,
            risk_fixture_index=self.risk_index,
            controls_fixture_index=self.controls_index,
        )
        self.assertIsInstance(out, IntegrityAssessment)
        return out

    def test_two_calls_identical_integrity_assessment(self) -> None:
        assert_controls_integrity_replay_equal(self._call(), self._call())


class ReplayIntegrityCautionDegradedRowTestCase(unittest.TestCase):
    """CAUTION + DEGRADED assessment: degraded normalized freshness row (replay-stable)."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.risk_index = build_fixture_index()
        cls.controls_index = build_controls_integrity_fixture_index()
        cls.node_ref = division_toh()
        cls.as_of_date = D_09
        cls.snapshot_id = "SNAP-2026-01-09"

    def _call(self) -> IntegrityAssessment:
        out = get_integrity_assessment(
            self.node_ref,
            MeasureType.VAR_1D_99,
            self.as_of_date,
            self.snapshot_id,
            risk_fixture_index=self.risk_index,
            controls_fixture_index=self.controls_index,
        )
        self.assertIsInstance(out, IntegrityAssessment)
        return out

    def test_two_calls_identical_integrity_assessment(self) -> None:
        assert_controls_integrity_replay_equal(self._call(), self._call())


if __name__ == "__main__":
    unittest.main()
