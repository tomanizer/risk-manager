"""WI-5.1.2 — generated_at determinism rule (Stage 9 — persist).

Per PRD-5.1 §"Replay and determinism":
  - if at least one TargetInvestigationResult has outcome_kind == ASSESSMENT,
    generated_at = max(r.assessment.generated_at for those targets)
  - otherwise (no assessments — readiness blocked or all-service-errors),
    generated_at = datetime.combine(as_of_date, time(18, 0, tzinfo=UTC))

This test exercises the rule directly via the pure helper. Replay determinism
across two invocations is WI-5.1.4.
"""

from __future__ import annotations

from datetime import date, datetime, time, timezone

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
    OutcomeKind,
    TargetInvestigationResult,
)
from src.orchestrators.daily_risk_investigation.orchestrator import _derive_generated_at
from src.shared import ServiceError


_AS_OF_DATE = date(2024, 1, 15)
_SNAPSHOT_ID = "snap-001"


def _node(node_id: str) -> NodeRef:
    return NodeRef(
        hierarchy_scope=HierarchyScope.TOP_OF_HOUSE,
        legal_entity_id=None,
        node_level=NodeLevel.DESK,
        node_id=node_id,
    )


def _make_assessment(node_ref: NodeRef, generated_at: datetime) -> IntegrityAssessment:
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
        generated_at=generated_at,
    )


def _assessment_target(node_id: str, generated_at: datetime) -> TargetInvestigationResult:
    node = _node(node_id)
    return TargetInvestigationResult(
        node_ref=node,
        measure_type=MeasureType.VAR_1D_99,
        outcome_kind=OutcomeKind.ASSESSMENT,
        assessment=_make_assessment(node, generated_at),
        service_error=None,
    )


def _service_error_target(node_id: str) -> TargetInvestigationResult:
    return TargetInvestigationResult(
        node_ref=_node(node_id),
        measure_type=MeasureType.VAR_1D_99,
        outcome_kind=OutcomeKind.SERVICE_ERROR,
        assessment=None,
        service_error=ServiceError(operation="assess_integrity", status_code="MISSING_NODE"),
    )


def test_generated_at_is_max_of_assessment_timestamps() -> None:
    t1 = datetime(2024, 1, 15, 17, 30, 0, tzinfo=timezone.utc)
    t2 = datetime(2024, 1, 15, 18, 15, 12, tzinfo=timezone.utc)
    t3 = datetime(2024, 1, 15, 18, 5, 0, tzinfo=timezone.utc)
    target_results = (
        _assessment_target("D-1", t1),
        _assessment_target("D-2", t2),
        _assessment_target("D-3", t3),
    )
    assert _derive_generated_at(target_results, _AS_OF_DATE) == t2


def test_generated_at_single_assessment_returns_its_timestamp() -> None:
    only = datetime(2024, 1, 15, 18, 0, 0, tzinfo=timezone.utc)
    target_results = (_assessment_target("D-1", only),)
    assert _derive_generated_at(target_results, _AS_OF_DATE) == only


def test_generated_at_falls_back_to_18_00_utc_when_no_assessments() -> None:
    target_results: tuple[TargetInvestigationResult, ...] = (
        _service_error_target("D-1"),
        _service_error_target("D-2"),
    )
    expected = datetime.combine(_AS_OF_DATE, time(18, 0, tzinfo=timezone.utc))
    assert _derive_generated_at(target_results, _AS_OF_DATE) == expected


def test_generated_at_falls_back_when_target_results_is_empty() -> None:
    """Readiness-blocked path: no targets investigated → 18:00 UTC fallback."""
    expected = datetime.combine(_AS_OF_DATE, time(18, 0, tzinfo=timezone.utc))
    assert _derive_generated_at((), _AS_OF_DATE) == expected


def test_generated_at_uses_assessments_only_in_mixed_outcomes() -> None:
    """Mixed: at least one assessment → max of assessment timestamps; SE outcomes ignored."""
    assess_at = datetime(2024, 1, 15, 17, 45, 0, tzinfo=timezone.utc)
    target_results = (
        _service_error_target("D-1"),
        _assessment_target("D-2", assess_at),
    )
    assert _derive_generated_at(target_results, _AS_OF_DATE) == assess_at


def test_generated_at_fallback_uses_provided_as_of_date() -> None:
    other_day = date(2026, 6, 30)
    expected = datetime.combine(other_day, time(18, 0, tzinfo=timezone.utc))
    assert _derive_generated_at((), other_day) == expected
