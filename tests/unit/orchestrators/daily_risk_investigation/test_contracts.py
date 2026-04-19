"""Unit tests for WI-5.1.1: typed contracts, enums, and run_id derivation.

Coverage:
- Enum vocabulary exactness (count and values, no extras)
- Pydantic model field shapes (required fields, correct types, optionality)
- start_daily_run importability and NotImplementedError raise
- run_id derivation determinism (equal inputs → equal run_id, starts with "drun_")
- Pinned digest regression guard (fixed input → hardcoded expected hex)
"""

from __future__ import annotations

import unittest
from datetime import date, datetime, timezone

from src.modules.controls_integrity import (
    AssessmentStatus,
    CheckState,
    CheckType,
    ControlCheckResult,
    IntegrityAssessment,
    ReasonCode,
    TrustState,
)
from src.modules.controls_integrity.contracts.enums import FalseSignalRisk
from src.modules.risk_analytics.contracts import MeasureType, NodeRef
from src.modules.risk_analytics.contracts.enums import HierarchyScope, NodeLevel
from src.orchestrators.daily_risk_investigation import (
    DailyRunResult,
    HandoffStatus,
    OutcomeKind,
    ReadinessState,
    TargetHandoffEntry,
    TargetInvestigationResult,
    TerminalRunStatus,
    start_daily_run,
)
from src.orchestrators.daily_risk_investigation.orchestrator import (
    _derive_run_id,
    orchestrator_version,
)
from src.shared import ServiceError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SNAPSHOT_ID = "snap-001"
_AS_OF_DATE = date(2024, 1, 15)
_GENERATED_AT = datetime(2024, 1, 15, 18, 0, 0, tzinfo=timezone.utc)

_NODE_REF_TOH = NodeRef(
    hierarchy_scope=HierarchyScope.TOP_OF_HOUSE,
    legal_entity_id=None,
    node_level=NodeLevel.FIRM,
    node_id="FIRM-001",
)

_NODE_REF_DESK = NodeRef(
    hierarchy_scope=HierarchyScope.TOP_OF_HOUSE,
    legal_entity_id=None,
    node_level=NodeLevel.DESK,
    node_id="DESK-001",
)

_PINNED_NODE_REF = NodeRef(
    hierarchy_scope=HierarchyScope.TOP_OF_HOUSE,
    legal_entity_id=None,
    node_level=NodeLevel.DESK,
    node_id="DESK-001",
)

# Pinned digest computed at authoring time (WI-5.1.1) for inputs:
#   as_of_date=2024-01-15, snapshot_id="snap-001", measure_type=VAR_1D_99,
#   candidate_targets=(DESK-001/DESK/TOP_OF_HOUSE), orchestrator_version="1.0.0"
# Do NOT recompute at test execution time.
_PINNED_EXPECTED_RUN_ID = (
    "drun_a8a300f67269080abd5bb319e8c491a9b843d8ef2ddb35509531db454dddb61d"
)


def _make_integrity_assessment(node_ref: NodeRef) -> IntegrityAssessment:
    checks = tuple(
        ControlCheckResult(
            check_type=ct,
            check_state=CheckState.PASS,
            reason_codes=(),
            evidence_refs=(),
        )
        for ct in [
            CheckType.FRESHNESS,
            CheckType.COMPLETENESS,
            CheckType.LINEAGE,
            CheckType.RECONCILIATION,
            CheckType.PUBLICATION_READINESS,
        ]
    )
    return IntegrityAssessment(
        node_ref=node_ref,
        measure_type=MeasureType.VAR_1D_99,
        as_of_date=_AS_OF_DATE,
        trust_state=TrustState.TRUSTED,
        false_signal_risk=FalseSignalRisk.LOW,
        assessment_status=AssessmentStatus.OK,
        blocking_reason_codes=(),
        cautionary_reason_codes=(),
        check_results=checks,
        snapshot_id=_SNAPSHOT_ID,
        data_version="dv-1",
        service_version="sv-1",
        generated_at=_GENERATED_AT,
    )


# ---------------------------------------------------------------------------
# Enum vocabulary tests
# ---------------------------------------------------------------------------


class HandoffStatusEnumTest(unittest.TestCase):
    def test_exact_members(self) -> None:
        expected = {
            "READY_FOR_HANDOFF",
            "PROCEED_WITH_CAVEAT",
            "HOLD_BLOCKING_TRUST",
            "HOLD_UNRESOLVED_TRUST",
            "HOLD_INVESTIGATION_FAILED",
        }
        self.assertEqual({m.value for m in HandoffStatus}, expected)

    def test_count(self) -> None:
        self.assertEqual(len(HandoffStatus), 5)


class TerminalRunStatusEnumTest(unittest.TestCase):
    def test_exact_members(self) -> None:
        expected = {
            "COMPLETED",
            "COMPLETED_WITH_CAVEATS",
            "COMPLETED_WITH_FAILURES",
            "FAILED_ALL_TARGETS",
            "BLOCKED_READINESS",
        }
        self.assertEqual({m.value for m in TerminalRunStatus}, expected)

    def test_count(self) -> None:
        self.assertEqual(len(TerminalRunStatus), 5)


class ReadinessStateEnumTest(unittest.TestCase):
    def test_exact_members(self) -> None:
        self.assertEqual({m.value for m in ReadinessState}, {"READY", "BLOCKED"})

    def test_count(self) -> None:
        self.assertEqual(len(ReadinessState), 2)


class OutcomeKindEnumTest(unittest.TestCase):
    def test_exact_members(self) -> None:
        self.assertEqual({m.value for m in OutcomeKind}, {"ASSESSMENT", "SERVICE_ERROR"})

    def test_count(self) -> None:
        self.assertEqual(len(OutcomeKind), 2)


# ---------------------------------------------------------------------------
# Model field shape tests
# ---------------------------------------------------------------------------


class TargetInvestigationResultShapeTest(unittest.TestCase):
    def test_assessment_outcome(self) -> None:
        assessment = _make_integrity_assessment(_NODE_REF_TOH)
        result = TargetInvestigationResult(
            node_ref=_NODE_REF_TOH,
            measure_type=MeasureType.VAR_1D_99,
            outcome_kind=OutcomeKind.ASSESSMENT,
            assessment=assessment,
            service_error=None,
        )
        self.assertEqual(result.node_ref, _NODE_REF_TOH)
        self.assertEqual(result.measure_type, MeasureType.VAR_1D_99)
        self.assertEqual(result.outcome_kind, OutcomeKind.ASSESSMENT)
        self.assertIs(result.assessment, assessment)
        self.assertIsNone(result.service_error)

    def test_service_error_outcome(self) -> None:
        error = ServiceError(operation="assess_integrity", status_code="MISSING_NODE")
        result = TargetInvestigationResult(
            node_ref=_NODE_REF_TOH,
            measure_type=MeasureType.VAR_1D_99,
            outcome_kind=OutcomeKind.SERVICE_ERROR,
            assessment=None,
            service_error=error,
        )
        self.assertEqual(result.outcome_kind, OutcomeKind.SERVICE_ERROR)
        self.assertIsNone(result.assessment)
        self.assertIs(result.service_error, error)

    def test_frozen(self) -> None:
        assessment = _make_integrity_assessment(_NODE_REF_TOH)
        result = TargetInvestigationResult(
            node_ref=_NODE_REF_TOH,
            measure_type=MeasureType.VAR_1D_99,
            outcome_kind=OutcomeKind.ASSESSMENT,
            assessment=assessment,
        )
        with self.assertRaises(Exception):
            result.outcome_kind = OutcomeKind.SERVICE_ERROR  # type: ignore[misc]


class TargetHandoffEntryShapeTest(unittest.TestCase):
    def test_ready_for_handoff(self) -> None:
        entry = TargetHandoffEntry(
            node_ref=_NODE_REF_TOH,
            measure_type=MeasureType.VAR_1D_99,
            handoff_status=HandoffStatus.READY_FOR_HANDOFF,
            blocking_reason_codes=(),
            cautionary_reason_codes=(),
            service_error_status_code=None,
        )
        self.assertEqual(entry.handoff_status, HandoffStatus.READY_FOR_HANDOFF)
        self.assertEqual(entry.blocking_reason_codes, ())
        self.assertEqual(entry.cautionary_reason_codes, ())
        self.assertIsNone(entry.service_error_status_code)

    def test_hold_with_reason_codes(self) -> None:
        entry = TargetHandoffEntry(
            node_ref=_NODE_REF_TOH,
            measure_type=MeasureType.VAR_1D_99,
            handoff_status=HandoffStatus.HOLD_BLOCKING_TRUST,
            blocking_reason_codes=(ReasonCode.FRESHNESS_FAIL,),
            cautionary_reason_codes=(ReasonCode.LINEAGE_WARN,),
            service_error_status_code=None,
        )
        self.assertEqual(entry.blocking_reason_codes, (ReasonCode.FRESHNESS_FAIL,))
        self.assertEqual(entry.cautionary_reason_codes, (ReasonCode.LINEAGE_WARN,))

    def test_service_error_status_code_populated(self) -> None:
        entry = TargetHandoffEntry(
            node_ref=_NODE_REF_TOH,
            measure_type=MeasureType.VAR_1D_99,
            handoff_status=HandoffStatus.HOLD_INVESTIGATION_FAILED,
            service_error_status_code="MISSING_NODE",
        )
        self.assertEqual(entry.service_error_status_code, "MISSING_NODE")

    def test_frozen(self) -> None:
        entry = TargetHandoffEntry(
            node_ref=_NODE_REF_TOH,
            measure_type=MeasureType.VAR_1D_99,
            handoff_status=HandoffStatus.READY_FOR_HANDOFF,
        )
        with self.assertRaises(Exception):
            entry.handoff_status = HandoffStatus.HOLD_BLOCKING_TRUST  # type: ignore[misc]


class DailyRunResultShapeTest(unittest.TestCase):
    def _make_result(self, **overrides: object) -> DailyRunResult:
        assessment = _make_integrity_assessment(_NODE_REF_TOH)
        target_result = TargetInvestigationResult(
            node_ref=_NODE_REF_TOH,
            measure_type=MeasureType.VAR_1D_99,
            outcome_kind=OutcomeKind.ASSESSMENT,
            assessment=assessment,
        )
        handoff_entry = TargetHandoffEntry(
            node_ref=_NODE_REF_TOH,
            measure_type=MeasureType.VAR_1D_99,
            handoff_status=HandoffStatus.READY_FOR_HANDOFF,
        )
        defaults: dict[str, object] = {
            "run_id": "drun_abc123",
            "as_of_date": _AS_OF_DATE,
            "snapshot_id": _SNAPSHOT_ID,
            "measure_type": MeasureType.VAR_1D_99,
            "candidate_targets": (_NODE_REF_TOH,),
            "selected_targets": (_NODE_REF_TOH,),
            "target_results": (target_result,),
            "handoff": (handoff_entry,),
            "readiness_state": ReadinessState.READY,
            "readiness_reason_codes": (),
            "terminal_status": TerminalRunStatus.COMPLETED,
            "degraded": False,
            "partial": False,
            "orchestrator_version": orchestrator_version,
            "generated_at": _GENERATED_AT,
        }
        defaults.update(overrides)
        return DailyRunResult(**defaults)

    def test_all_required_fields_present(self) -> None:
        result = self._make_result()
        self.assertEqual(result.run_id, "drun_abc123")
        self.assertEqual(result.as_of_date, _AS_OF_DATE)
        self.assertEqual(result.snapshot_id, _SNAPSHOT_ID)
        self.assertEqual(result.measure_type, MeasureType.VAR_1D_99)
        self.assertEqual(result.readiness_state, ReadinessState.READY)
        self.assertEqual(result.terminal_status, TerminalRunStatus.COMPLETED)
        self.assertFalse(result.degraded)
        self.assertFalse(result.partial)
        self.assertEqual(result.orchestrator_version, orchestrator_version)
        self.assertEqual(result.generated_at, _GENERATED_AT)

    def test_blocked_readiness_empty_tuples(self) -> None:
        result = self._make_result(
            selected_targets=(),
            target_results=(),
            handoff=(),
            readiness_state=ReadinessState.BLOCKED,
            readiness_reason_codes=("MISSING_SNAPSHOT",),
            terminal_status=TerminalRunStatus.BLOCKED_READINESS,
        )
        self.assertEqual(result.selected_targets, ())
        self.assertEqual(result.target_results, ())
        self.assertEqual(result.handoff, ())
        self.assertEqual(result.terminal_status, TerminalRunStatus.BLOCKED_READINESS)

    def test_frozen(self) -> None:
        result = self._make_result()
        with self.assertRaises(Exception):
            result.run_id = "different"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Public surface importability
# ---------------------------------------------------------------------------


class PublicSurfaceTest(unittest.TestCase):
    def test_start_daily_run_importable(self) -> None:
        from src.orchestrators.daily_risk_investigation import start_daily_run as sdr
        self.assertTrue(callable(sdr))

    def test_all_types_importable(self) -> None:
        from src.orchestrators.daily_risk_investigation import (  # noqa: F401
            DailyRunResult,
            HandoffStatus,
            OutcomeKind,
            ReadinessState,
            TargetHandoffEntry,
            TargetInvestigationResult,
            TerminalRunStatus,
        )

    def test_start_daily_run_raises_not_implemented(self) -> None:
        with self.assertRaises(NotImplementedError):
            start_daily_run(
                as_of_date=_AS_OF_DATE,
                snapshot_id=_SNAPSHOT_ID,
                candidate_targets=(_NODE_REF_TOH,),
                measure_type=MeasureType.VAR_1D_99,
            )

    def test_start_daily_run_with_optional_kwargs(self) -> None:
        with self.assertRaises(NotImplementedError):
            start_daily_run(
                as_of_date=_AS_OF_DATE,
                snapshot_id=_SNAPSHOT_ID,
                candidate_targets=(_NODE_REF_TOH,),
                measure_type=MeasureType.VAR_1D_99,
                risk_fixture_index=None,
                controls_fixture_index=None,
            )


# ---------------------------------------------------------------------------
# run_id derivation tests
# ---------------------------------------------------------------------------


class RunIdDeterminismTest(unittest.TestCase):
    def test_equal_inputs_produce_equal_run_id(self) -> None:
        run_id_1 = _derive_run_id(
            as_of_date=_AS_OF_DATE,
            snapshot_id=_SNAPSHOT_ID,
            measure_type=MeasureType.VAR_1D_99,
            candidate_targets=(_NODE_REF_DESK,),
        )
        run_id_2 = _derive_run_id(
            as_of_date=_AS_OF_DATE,
            snapshot_id=_SNAPSHOT_ID,
            measure_type=MeasureType.VAR_1D_99,
            candidate_targets=(_NODE_REF_DESK,),
        )
        self.assertEqual(run_id_1, run_id_2)

    def test_run_id_starts_with_drun_prefix(self) -> None:
        run_id = _derive_run_id(
            as_of_date=_AS_OF_DATE,
            snapshot_id=_SNAPSHOT_ID,
            measure_type=MeasureType.VAR_1D_99,
            candidate_targets=(_NODE_REF_DESK,),
        )
        self.assertTrue(run_id.startswith("drun_"), f"Expected 'drun_' prefix, got: {run_id!r}")

    def test_run_id_is_string(self) -> None:
        run_id = _derive_run_id(
            as_of_date=_AS_OF_DATE,
            snapshot_id=_SNAPSHOT_ID,
            measure_type=MeasureType.VAR_1D_99,
            candidate_targets=(_NODE_REF_DESK,),
        )
        self.assertIsInstance(run_id, str)

    def test_different_snapshot_produces_different_run_id(self) -> None:
        run_id_a = _derive_run_id(
            as_of_date=_AS_OF_DATE,
            snapshot_id="snap-001",
            measure_type=MeasureType.VAR_1D_99,
            candidate_targets=(_NODE_REF_DESK,),
        )
        run_id_b = _derive_run_id(
            as_of_date=_AS_OF_DATE,
            snapshot_id="snap-002",
            measure_type=MeasureType.VAR_1D_99,
            candidate_targets=(_NODE_REF_DESK,),
        )
        self.assertNotEqual(run_id_a, run_id_b)

    def test_different_date_produces_different_run_id(self) -> None:
        run_id_a = _derive_run_id(
            as_of_date=date(2024, 1, 15),
            snapshot_id=_SNAPSHOT_ID,
            measure_type=MeasureType.VAR_1D_99,
            candidate_targets=(_NODE_REF_DESK,),
        )
        run_id_b = _derive_run_id(
            as_of_date=date(2024, 1, 16),
            snapshot_id=_SNAPSHOT_ID,
            measure_type=MeasureType.VAR_1D_99,
            candidate_targets=(_NODE_REF_DESK,),
        )
        self.assertNotEqual(run_id_a, run_id_b)

    def test_different_measure_type_produces_different_run_id(self) -> None:
        run_id_a = _derive_run_id(
            as_of_date=_AS_OF_DATE,
            snapshot_id=_SNAPSHOT_ID,
            measure_type=MeasureType.VAR_1D_99,
            candidate_targets=(_NODE_REF_DESK,),
        )
        run_id_b = _derive_run_id(
            as_of_date=_AS_OF_DATE,
            snapshot_id=_SNAPSHOT_ID,
            measure_type=MeasureType.ES_97_5,
            candidate_targets=(_NODE_REF_DESK,),
        )
        self.assertNotEqual(run_id_a, run_id_b)


class RunIdPinnedDigestTest(unittest.TestCase):
    """Regression guard: fixed input → fixed expected hex digest.

    The expected value was computed at WI-5.1.1 authoring time and is
    hardcoded here. It must not be recomputed at test execution time.
    Input set:
      as_of_date=2024-01-15, snapshot_id="snap-001",
      measure_type=VAR_1D_99,
      candidate_targets=(NodeRef DESK-001/DESK/TOP_OF_HOUSE/legal_entity_id=None),
      orchestrator_version="1.0.0"
    """

    def test_pinned_digest(self) -> None:
        run_id = _derive_run_id(
            as_of_date=date(2024, 1, 15),
            snapshot_id="snap-001",
            measure_type=MeasureType.VAR_1D_99,
            candidate_targets=(_PINNED_NODE_REF,),
        )
        self.assertEqual(run_id, _PINNED_EXPECTED_RUN_ID)


# ---------------------------------------------------------------------------
# orchestrator_version constant
# ---------------------------------------------------------------------------


class OrchestratorVersionTest(unittest.TestCase):
    def test_orchestrator_version_is_non_empty_string(self) -> None:
        self.assertIsInstance(orchestrator_version, str)
        self.assertTrue(orchestrator_version, "orchestrator_version must be non-empty")

    def test_orchestrator_version_is_included_in_run_id_derivation(self) -> None:
        """Changing orchestrator_version changes run_id (tested indirectly via module constant)."""
        # The pinned digest test pins orchestrator_version="1.0.0"; if the constant
        # were empty or different the digest would differ from the pinned value.
        self.assertEqual(orchestrator_version, "1.0.0")


if __name__ == "__main__":
    unittest.main()
