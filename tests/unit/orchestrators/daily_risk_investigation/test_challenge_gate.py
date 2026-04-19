"""WI-5.1.2 — Per-target challenge gate truth-table (Stage 7).

Parametrizes _evaluate_challenge over every (outcome_kind, trust_state,
assessment_status) combination implied by PRD-5.1 §"Per-target gate rules"
and asserts the documented HandoffStatus per the six-rule precedence (first
match wins). Also asserts that _build_handoff_entry propagates the upstream
reason-code tuples byte-for-byte.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

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
from src.modules.risk_analytics.contracts import (
    HierarchyScope,
    MeasureType,
    NodeLevel,
    NodeRef,
)
from src.orchestrators.daily_risk_investigation import (
    HandoffStatus,
    OutcomeKind,
    TargetInvestigationResult,
)
from src.orchestrators.daily_risk_investigation.orchestrator import (
    _build_handoff_entry,
    _evaluate_challenge,
)
from src.shared import ServiceError


_AS_OF_DATE = date(2024, 1, 15)
_GENERATED_AT = datetime(2024, 1, 15, 18, 0, 0, tzinfo=timezone.utc)
_SNAPSHOT_ID = "snap-001"

_NODE_REF = NodeRef(
    hierarchy_scope=HierarchyScope.TOP_OF_HOUSE,
    legal_entity_id=None,
    node_level=NodeLevel.FIRM,
    node_id="FIRM-001",
)


def _make_assessment(
    *,
    trust_state: TrustState,
    assessment_status: AssessmentStatus,
    blocking: tuple[ReasonCode, ...] = (),
    cautionary: tuple[ReasonCode, ...] = (),
) -> IntegrityAssessment:
    """Construct a minimal valid IntegrityAssessment with the given state.

    Uses PASS check_results so reason-code/evidence cross-validation is satisfied;
    blocking/cautionary tuples are passed independently to exercise propagation.
    """
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
        node_ref=_NODE_REF,
        measure_type=MeasureType.VAR_1D_99,
        as_of_date=_AS_OF_DATE,
        trust_state=trust_state,
        false_signal_risk=FalseSignalRisk.LOW,
        assessment_status=assessment_status,
        blocking_reason_codes=blocking,
        cautionary_reason_codes=cautionary,
        check_results=checks,
        snapshot_id=_SNAPSHOT_ID,
        data_version="dv-1",
        service_version="sv-1",
        generated_at=_GENERATED_AT,
    )


def _assessment_target(
    trust_state: TrustState,
    assessment_status: AssessmentStatus,
    *,
    blocking: tuple[ReasonCode, ...] = (),
    cautionary: tuple[ReasonCode, ...] = (),
) -> TargetInvestigationResult:
    return TargetInvestigationResult(
        node_ref=_NODE_REF,
        measure_type=MeasureType.VAR_1D_99,
        outcome_kind=OutcomeKind.ASSESSMENT,
        assessment=_make_assessment(
            trust_state=trust_state,
            assessment_status=assessment_status,
            blocking=blocking,
            cautionary=cautionary,
        ),
        service_error=None,
    )


def _service_error_target(status_code: str = "MISSING_NODE") -> TargetInvestigationResult:
    return TargetInvestigationResult(
        node_ref=_NODE_REF,
        measure_type=MeasureType.VAR_1D_99,
        outcome_kind=OutcomeKind.SERVICE_ERROR,
        assessment=None,
        service_error=ServiceError(operation="assess_integrity", status_code=status_code),
    )


# ---------------------------------------------------------------------------
# Truth-table over (outcome_kind, trust_state, assessment_status)
# ---------------------------------------------------------------------------
#
# Rule precedence (PRD-5.1 §"Per-target gate rules", first match wins):
#   1. SERVICE_ERROR                         -> HOLD_INVESTIGATION_FAILED
#   2. trust_state == BLOCKED                -> HOLD_BLOCKING_TRUST
#   3. trust_state == UNRESOLVED             -> HOLD_UNRESOLVED_TRUST
#   4. assessment_status == DEGRADED         -> PROCEED_WITH_CAVEAT
#   5. trust_state == CAUTION  & status==OK  -> PROCEED_WITH_CAVEAT
#   6. trust_state == TRUSTED  & status==OK  -> READY_FOR_HANDOFF


_ASSESSMENT_CASES: list[tuple[TrustState, AssessmentStatus, HandoffStatus]] = [
    # Rule 2 (BLOCKED dominates DEGRADED)
    (TrustState.BLOCKED, AssessmentStatus.OK, HandoffStatus.HOLD_BLOCKING_TRUST),
    (TrustState.BLOCKED, AssessmentStatus.DEGRADED, HandoffStatus.HOLD_BLOCKING_TRUST),
    # Rule 3 (UNRESOLVED dominates DEGRADED)
    (TrustState.UNRESOLVED, AssessmentStatus.OK, HandoffStatus.HOLD_UNRESOLVED_TRUST),
    (TrustState.UNRESOLVED, AssessmentStatus.DEGRADED, HandoffStatus.HOLD_UNRESOLVED_TRUST),
    # Rule 4 (DEGRADED for non-blocked/unresolved trust states)
    (TrustState.TRUSTED, AssessmentStatus.DEGRADED, HandoffStatus.PROCEED_WITH_CAVEAT),
    (TrustState.CAUTION, AssessmentStatus.DEGRADED, HandoffStatus.PROCEED_WITH_CAVEAT),
    # Rule 5 (CAUTION + OK)
    (TrustState.CAUTION, AssessmentStatus.OK, HandoffStatus.PROCEED_WITH_CAVEAT),
    # Rule 6 (TRUSTED + OK)
    (TrustState.TRUSTED, AssessmentStatus.OK, HandoffStatus.READY_FOR_HANDOFF),
]


@pytest.mark.parametrize("trust_state,assessment_status,expected_status", _ASSESSMENT_CASES)
def test_evaluate_challenge_assessment_truth_table(
    trust_state: TrustState,
    assessment_status: AssessmentStatus,
    expected_status: HandoffStatus,
) -> None:
    target = _assessment_target(trust_state, assessment_status)
    assert _evaluate_challenge(target) is expected_status


def test_evaluate_challenge_service_error_dominates_all() -> None:
    """Rule 1: SERVICE_ERROR outcome maps to HOLD_INVESTIGATION_FAILED unconditionally."""
    assert _evaluate_challenge(_service_error_target()) is HandoffStatus.HOLD_INVESTIGATION_FAILED


@pytest.mark.parametrize(
    "status_code",
    ["MISSING_NODE", "MISSING_SNAPSHOT", "UNSUPPORTED_MEASURE", "MISSING_CONTROL_CONTEXT"],
)
def test_evaluate_challenge_service_error_any_status_code(status_code: str) -> None:
    assert _evaluate_challenge(_service_error_target(status_code)) is HandoffStatus.HOLD_INVESTIGATION_FAILED


# ---------------------------------------------------------------------------
# Reason-code propagation through Stage 7 build_handoff_entry
# ---------------------------------------------------------------------------


def test_build_handoff_entry_propagates_assessment_reason_codes_by_value() -> None:
    blocking = (ReasonCode.FRESHNESS_FAIL, ReasonCode.COMPLETENESS_FAIL)
    cautionary = (ReasonCode.LINEAGE_WARN,)
    target = _assessment_target(
        TrustState.BLOCKED,
        AssessmentStatus.OK,
        blocking=blocking,
        cautionary=cautionary,
    )
    entry = _build_handoff_entry(target)
    assert entry.handoff_status is HandoffStatus.HOLD_BLOCKING_TRUST
    # Byte-for-byte equality with upstream tuples
    assert entry.blocking_reason_codes == target.assessment.blocking_reason_codes  # type: ignore[union-attr]
    assert entry.cautionary_reason_codes == target.assessment.cautionary_reason_codes  # type: ignore[union-attr]
    assert entry.service_error_status_code is None


def test_build_handoff_entry_service_error_carries_status_code() -> None:
    target = _service_error_target("MISSING_CONTROL_CONTEXT")
    entry = _build_handoff_entry(target)
    assert entry.handoff_status is HandoffStatus.HOLD_INVESTIGATION_FAILED
    assert entry.blocking_reason_codes == ()
    assert entry.cautionary_reason_codes == ()
    assert entry.service_error_status_code == "MISSING_CONTROL_CONTEXT"


def test_build_handoff_entry_no_orchestrator_originated_codes() -> None:
    """PRD-5.1 forbids orchestrator-originated reason codes; empty assessment tuples stay empty."""
    target = _assessment_target(TrustState.TRUSTED, AssessmentStatus.OK)
    entry = _build_handoff_entry(target)
    assert entry.blocking_reason_codes == ()
    assert entry.cautionary_reason_codes == ()
