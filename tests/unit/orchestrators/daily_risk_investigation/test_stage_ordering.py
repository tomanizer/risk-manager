"""WI-5.1.2 — Stage ordering with injected fakes.

Patches `get_risk_summary` and `assess_integrity` at their import sites inside
the orchestrator module to:

- Verify the BLOCKED_READINESS short-circuit (Stages 3–8 skipped; assess_integrity
  is never called; selected_targets / target_results / handoff are empty tuples).
- Verify the READY path call ordering: canary call once, then exactly one
  selection-stage get_risk_summary call per candidate (in input order), then one
  assess_integrity call per selected target (in selected_targets order).
- Verify that an unexpected ServiceError from get_risk_summary after the gate
  passed raises RuntimeError("readiness invariant violated after gate passed").
- Verify that a ValueError from the walker escapes start_daily_run unchanged
  (programmer-error escape per PRD-4.1 / PRD-5.1).
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from unittest.mock import patch

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
    RiskSummary,
)
from src.modules.risk_analytics.contracts.enums import SummaryStatus
from src.orchestrators.daily_risk_investigation import (
    ReadinessState,
    TerminalRunStatus,
    start_daily_run,
)
from src.shared import ServiceError


_AS_OF_DATE = date(2024, 1, 15)
_GENERATED_AT = datetime(2024, 1, 15, 18, 0, 0, tzinfo=timezone.utc)
_SNAPSHOT_ID = "snap-001"

_RISK_PATCH = "src.orchestrators.daily_risk_investigation.orchestrator.get_risk_summary"
_WALKER_PATCH = "src.orchestrators.daily_risk_investigation.orchestrator.assess_integrity"


def _node(node_id: str) -> NodeRef:
    return NodeRef(
        hierarchy_scope=HierarchyScope.TOP_OF_HOUSE,
        legal_entity_id=None,
        node_level=NodeLevel.DESK,
        node_id=node_id,
    )


def _make_risk_summary(node_ref: NodeRef) -> RiskSummary:
    """Construct a minimal valid RiskSummary that satisfies the contract."""
    return RiskSummary(
        node_ref=node_ref,
        measure_type=MeasureType.VAR_1D_99,
        as_of_date=_AS_OF_DATE,
        current_value=1.0,
        status=SummaryStatus.OK,
        snapshot_id=_SNAPSHOT_ID,
        data_version="dv-1",
        service_version="sv-1",
        generated_at=_GENERATED_AT,
    )


def _make_assessment(node_ref: NodeRef) -> IntegrityAssessment:
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
# BLOCKED_READINESS short-circuit
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("blocking_status", ["MISSING_SNAPSHOT", "UNSUPPORTED_MEASURE"])
def test_blocked_readiness_short_circuits_stages_3_through_8(blocking_status: str) -> None:
    candidates = (_node("D-1"), _node("D-2"), _node("D-3"))
    canary_error = ServiceError(operation="get_risk_summary", status_code=blocking_status)

    with (
        patch(_RISK_PATCH, return_value=canary_error) as risk_spy,
        patch(_WALKER_PATCH) as walker_spy,
    ):
        result = start_daily_run(
            as_of_date=_AS_OF_DATE,
            snapshot_id=_SNAPSHOT_ID,
            candidate_targets=candidates,
            measure_type=MeasureType.VAR_1D_99,
        )

    # Only the canary call to get_risk_summary; selection stage skipped.
    assert risk_spy.call_count == 1
    walker_spy.assert_not_called()

    # Run-level shape under BLOCKED_READINESS short-circuit.
    assert result.readiness_state is ReadinessState.BLOCKED
    assert result.readiness_reason_codes == (blocking_status,)
    assert result.terminal_status is TerminalRunStatus.BLOCKED_READINESS
    assert result.selected_targets == ()
    assert result.target_results == ()
    assert result.handoff == ()
    assert result.degraded is False
    assert result.partial is False
    # generated_at fallback: 18:00 UTC anchor on as_of_date.
    assert result.generated_at == datetime(2024, 1, 15, 18, 0, 0, tzinfo=timezone.utc)


def test_readiness_canary_missing_node_does_not_block_run() -> None:
    """Canary MISSING_NODE → READY with READINESS_CANARY_MISSING_NODE reason code,
    Stage 3 still runs, that node is excluded from selected_targets."""
    candidates = (_node("D-1"), _node("D-2"))

    def risk_side_effect(*, node_ref: NodeRef, **_: object) -> RiskSummary | ServiceError:
        if node_ref.node_id == "D-1":
            return ServiceError(operation="get_risk_summary", status_code="MISSING_NODE")
        return _make_risk_summary(node_ref)

    with (
        patch(_RISK_PATCH, side_effect=risk_side_effect),
        patch(_WALKER_PATCH, side_effect=lambda node_ref, *args, **kwargs: _make_assessment(node_ref)) as walker_spy,
    ):
        result = start_daily_run(
            as_of_date=_AS_OF_DATE,
            snapshot_id=_SNAPSHOT_ID,
            candidate_targets=candidates,
            measure_type=MeasureType.VAR_1D_99,
        )

    assert result.readiness_state is ReadinessState.READY
    assert result.readiness_reason_codes == ("READINESS_CANARY_MISSING_NODE",)
    # D-1 (the canary) is excluded by Stage 3 MISSING_NODE filter.
    assert result.selected_targets == (_node("D-2"),)
    walker_spy.assert_called_once()


# ---------------------------------------------------------------------------
# READY-path call ordering
# ---------------------------------------------------------------------------


def test_ready_path_call_ordering() -> None:
    candidates = (_node("D-1"), _node("D-2"), _node("D-3"))

    risk_calls: list[NodeRef] = []
    walker_calls: list[NodeRef] = []

    def risk_side_effect(*, node_ref: NodeRef, **_: object) -> RiskSummary:
        risk_calls.append(node_ref)
        return _make_risk_summary(node_ref)

    def walker_side_effect(node_ref: NodeRef, *args: object, **kwargs: object) -> IntegrityAssessment:
        walker_calls.append(node_ref)
        return _make_assessment(node_ref)

    with (
        patch(_RISK_PATCH, side_effect=risk_side_effect),
        patch(_WALKER_PATCH, side_effect=walker_side_effect),
    ):
        result = start_daily_run(
            as_of_date=_AS_OF_DATE,
            snapshot_id=_SNAPSHOT_ID,
            candidate_targets=candidates,
            measure_type=MeasureType.VAR_1D_99,
        )

    # Stage 2 canary call: D-1 once.
    # Stage 3 selection: D-1, D-2, D-3 (one per candidate, in input order).
    # Total: 1 + 3 = 4 get_risk_summary calls; first call is canary (D-1).
    assert len(risk_calls) == 4
    assert risk_calls[0] == _node("D-1")  # canary
    assert risk_calls[1:] == [_node("D-1"), _node("D-2"), _node("D-3")]

    # Stage 5 walker calls: one per selected target, in selected_targets order.
    assert walker_calls == list(result.selected_targets)
    assert result.selected_targets == candidates


def test_unexpected_service_error_after_gate_passed_raises_runtime_error() -> None:
    """Stage 3 selection: any non-MISSING_NODE ServiceError after gate passed → RuntimeError."""
    candidates = (_node("D-1"), _node("D-2"))
    call_count = {"n": 0}

    def risk_side_effect(*, node_ref: NodeRef, **_: object) -> RiskSummary | ServiceError:
        call_count["n"] += 1
        if call_count["n"] == 1:
            # canary succeeds
            return _make_risk_summary(node_ref)
        # selection: simulate an invariant-violating ServiceError on a later candidate
        return ServiceError(operation="get_risk_summary", status_code="UNSUPPORTED_MEASURE")

    with (
        patch(_RISK_PATCH, side_effect=risk_side_effect),
        patch(_WALKER_PATCH) as walker_spy,
    ):
        with pytest.raises(RuntimeError, match="readiness invariant violated after gate passed"):
            start_daily_run(
                as_of_date=_AS_OF_DATE,
                snapshot_id=_SNAPSHOT_ID,
                candidate_targets=candidates,
                measure_type=MeasureType.VAR_1D_99,
            )

    walker_spy.assert_not_called()


def test_walker_value_error_propagates_unchanged() -> None:
    """Per PRD-4.1 / PRD-5.1, walker ValueError is a programmer-error escape; the
    orchestrator must not catch it."""
    candidates = (_node("D-1"),)

    def risk_side_effect(*, node_ref: NodeRef, **_: object) -> RiskSummary:
        return _make_risk_summary(node_ref)

    def walker_side_effect(*args: object, **kwargs: object) -> IntegrityAssessment:
        raise ValueError("invalid walker input from upstream contract")

    with (
        patch(_RISK_PATCH, side_effect=risk_side_effect),
        patch(_WALKER_PATCH, side_effect=walker_side_effect),
    ):
        with pytest.raises(ValueError, match="invalid walker input"):
            start_daily_run(
                as_of_date=_AS_OF_DATE,
                snapshot_id=_SNAPSHOT_ID,
                candidate_targets=candidates,
                measure_type=MeasureType.VAR_1D_99,
            )


# ---------------------------------------------------------------------------
# Identity propagation: TargetInvestigationResult carries upstream object by reference
# ---------------------------------------------------------------------------


def test_assessment_propagated_by_reference_into_target_result() -> None:
    candidates = (_node("D-1"),)
    upstream_assessment = _make_assessment(_node("D-1"))

    def risk_side_effect(*, node_ref: NodeRef, **_: object) -> RiskSummary:
        return _make_risk_summary(node_ref)

    with (
        patch(_RISK_PATCH, side_effect=risk_side_effect),
        patch(_WALKER_PATCH, return_value=upstream_assessment),
    ):
        result = start_daily_run(
            as_of_date=_AS_OF_DATE,
            snapshot_id=_SNAPSHOT_ID,
            candidate_targets=candidates,
            measure_type=MeasureType.VAR_1D_99,
        )

    assert len(result.target_results) == 1
    # Identity: orchestrator must not transform / rebuild the upstream object.
    assert result.target_results[0].assessment is upstream_assessment


def test_service_error_propagated_by_reference_into_target_result() -> None:
    candidates = (_node("D-1"),)
    upstream_error = ServiceError(operation="assess_integrity", status_code="MISSING_CONTROL_CONTEXT")

    def risk_side_effect(*, node_ref: NodeRef, **_: object) -> RiskSummary:
        return _make_risk_summary(node_ref)

    with (
        patch(_RISK_PATCH, side_effect=risk_side_effect),
        patch(_WALKER_PATCH, return_value=upstream_error),
    ):
        result = start_daily_run(
            as_of_date=_AS_OF_DATE,
            snapshot_id=_SNAPSHOT_ID,
            candidate_targets=candidates,
            measure_type=MeasureType.VAR_1D_99,
        )

    assert len(result.target_results) == 1
    assert result.target_results[0].service_error is upstream_error
    assert result.handoff[0].service_error_status_code == "MISSING_CONTROL_CONTEXT"
