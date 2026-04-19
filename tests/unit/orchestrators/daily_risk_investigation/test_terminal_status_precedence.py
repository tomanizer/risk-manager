"""WI-5.1.2 — Terminal-status precedence (Stage 9).

Asserts the five-level precedence from PRD-5.1 §"Terminal states":
  1. BLOCKED_READINESS         (short-circuited by Stage 2; tested via stage_ordering)
  2. FAILED_ALL_TARGETS        (selected_targets non-empty AND every outcome SE)
  3. COMPLETED_WITH_FAILURES   (>=1 SE AND >=1 ASSESSMENT)
  4. COMPLETED_WITH_CAVEATS    (all assessments AND (any DEGRADED OR any non-READY))
  5. COMPLETED                 (all assessments OK + all READY_FOR_HANDOFF)

Synthesizes target_results / handoff via the public model constructors;
exercises _derive_terminal_status as a pure function so each precedence
transition is asserted in isolation.
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
    TargetHandoffEntry,
    TargetInvestigationResult,
    TerminalRunStatus,
)
from src.orchestrators.daily_risk_investigation.orchestrator import (
    _build_handoff_entry,
    _derive_terminal_status,
)
from src.shared import ServiceError


_AS_OF_DATE = date(2024, 1, 15)
_GENERATED_AT = datetime(2024, 1, 15, 18, 0, 0, tzinfo=timezone.utc)
_SNAPSHOT_ID = "snap-001"


def _node(node_id: str) -> NodeRef:
    return NodeRef(
        hierarchy_scope=HierarchyScope.TOP_OF_HOUSE,
        legal_entity_id=None,
        node_level=NodeLevel.DESK,
        node_id=node_id,
    )


def _make_assessment(
    node_ref: NodeRef,
    *,
    trust_state: TrustState,
    assessment_status: AssessmentStatus,
) -> IntegrityAssessment:
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
        trust_state=trust_state,
        false_signal_risk=FalseSignalRisk.LOW,
        assessment_status=assessment_status,
        blocking_reason_codes=(),
        cautionary_reason_codes=(),
        check_results=checks,
        snapshot_id=_SNAPSHOT_ID,
        data_version="dv-1",
        service_version="sv-1",
        generated_at=_GENERATED_AT,
    )


def _assessment_target(
    node_id: str,
    trust_state: TrustState,
    assessment_status: AssessmentStatus,
) -> TargetInvestigationResult:
    node = _node(node_id)
    return TargetInvestigationResult(
        node_ref=node,
        measure_type=MeasureType.VAR_1D_99,
        outcome_kind=OutcomeKind.ASSESSMENT,
        assessment=_make_assessment(node, trust_state=trust_state, assessment_status=assessment_status),
        service_error=None,
    )


def _service_error_target(node_id: str, status_code: str = "MISSING_NODE") -> TargetInvestigationResult:
    node = _node(node_id)
    return TargetInvestigationResult(
        node_ref=node,
        measure_type=MeasureType.VAR_1D_99,
        outcome_kind=OutcomeKind.SERVICE_ERROR,
        assessment=None,
        service_error=ServiceError(operation="assess_integrity", status_code=status_code),
    )


def _handoff_for(target_results: tuple[TargetInvestigationResult, ...]) -> tuple[TargetHandoffEntry, ...]:
    return tuple(_build_handoff_entry(r) for r in target_results)


# ---------------------------------------------------------------------------
# Precedence-level assertions
# ---------------------------------------------------------------------------


def test_failed_all_targets_when_every_outcome_is_service_error() -> None:
    selected = (_node("D-1"), _node("D-2"))
    target_results = (
        _service_error_target("D-1", "MISSING_NODE"),
        _service_error_target("D-2", "MISSING_CONTROL_CONTEXT"),
    )
    handoff = _handoff_for(target_results)
    assert _derive_terminal_status(selected, target_results, handoff) is TerminalRunStatus.FAILED_ALL_TARGETS


def test_completed_with_failures_when_mixed_se_and_assessment() -> None:
    selected = (_node("D-1"), _node("D-2"))
    target_results = (
        _service_error_target("D-1"),
        _assessment_target("D-2", TrustState.TRUSTED, AssessmentStatus.OK),
    )
    handoff = _handoff_for(target_results)
    assert _derive_terminal_status(selected, target_results, handoff) is TerminalRunStatus.COMPLETED_WITH_FAILURES


def test_completed_with_caveats_when_any_assessment_degraded() -> None:
    selected = (_node("D-1"), _node("D-2"))
    target_results = (
        _assessment_target("D-1", TrustState.TRUSTED, AssessmentStatus.OK),
        _assessment_target("D-2", TrustState.TRUSTED, AssessmentStatus.DEGRADED),
    )
    handoff = _handoff_for(target_results)
    assert _derive_terminal_status(selected, target_results, handoff) is TerminalRunStatus.COMPLETED_WITH_CAVEATS


def test_completed_with_caveats_when_any_handoff_status_not_ready() -> None:
    """All assessments OK trust-wise but with CAUTION → PROCEED_WITH_CAVEAT non-ready handoff."""
    selected = (_node("D-1"), _node("D-2"))
    target_results = (
        _assessment_target("D-1", TrustState.TRUSTED, AssessmentStatus.OK),
        _assessment_target("D-2", TrustState.CAUTION, AssessmentStatus.OK),
    )
    handoff = _handoff_for(target_results)
    assert _derive_terminal_status(selected, target_results, handoff) is TerminalRunStatus.COMPLETED_WITH_CAVEATS


def test_completed_when_every_target_ok_trusted_and_ready() -> None:
    selected = (_node("D-1"), _node("D-2"))
    target_results = (
        _assessment_target("D-1", TrustState.TRUSTED, AssessmentStatus.OK),
        _assessment_target("D-2", TrustState.TRUSTED, AssessmentStatus.OK),
    )
    handoff = _handoff_for(target_results)
    assert _derive_terminal_status(selected, target_results, handoff) is TerminalRunStatus.COMPLETED


# ---------------------------------------------------------------------------
# Precedence interaction edges
# ---------------------------------------------------------------------------


def test_completed_with_failures_dominates_caveats() -> None:
    """If any SE is present alongside any assessment, COMPLETED_WITH_FAILURES wins
    over COMPLETED_WITH_CAVEATS even when degraded assessments are also present."""
    selected = (_node("D-1"), _node("D-2"), _node("D-3"))
    target_results = (
        _service_error_target("D-1"),
        _assessment_target("D-2", TrustState.TRUSTED, AssessmentStatus.DEGRADED),
        _assessment_target("D-3", TrustState.TRUSTED, AssessmentStatus.OK),
    )
    handoff = _handoff_for(target_results)
    assert _derive_terminal_status(selected, target_results, handoff) is TerminalRunStatus.COMPLETED_WITH_FAILURES


def test_failed_all_targets_dominates_completed_with_failures_when_no_assessment() -> None:
    selected = (_node("D-1"),)
    target_results = (_service_error_target("D-1", "MISSING_NODE"),)
    handoff = _handoff_for(target_results)
    assert _derive_terminal_status(selected, target_results, handoff) is TerminalRunStatus.FAILED_ALL_TARGETS


@pytest.mark.parametrize(
    "trust_state,expected_handoff_status,expected_terminal",
    [
        (TrustState.BLOCKED, HandoffStatus.HOLD_BLOCKING_TRUST, TerminalRunStatus.COMPLETED_WITH_CAVEATS),
        (TrustState.UNRESOLVED, HandoffStatus.HOLD_UNRESOLVED_TRUST, TerminalRunStatus.COMPLETED_WITH_CAVEATS),
        (TrustState.CAUTION, HandoffStatus.PROCEED_WITH_CAVEAT, TerminalRunStatus.COMPLETED_WITH_CAVEATS),
    ],
)
def test_non_ready_handoff_drives_completed_with_caveats(
    trust_state: TrustState,
    expected_handoff_status: HandoffStatus,
    expected_terminal: TerminalRunStatus,
) -> None:
    selected = (_node("D-1"),)
    target_results = (_assessment_target("D-1", trust_state, AssessmentStatus.OK),)
    handoff = _handoff_for(target_results)
    assert handoff[0].handoff_status is expected_handoff_status
    assert _derive_terminal_status(selected, target_results, handoff) is expected_terminal
