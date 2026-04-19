"""WI-5.1.2 — HOLD_INVESTIGATION_FAILED propagation through Stage 7 challenge gate.

Uses fixture combinations where Stage 3 selection passes (the node has a
RiskSummary in the snapshot) but the data_controller walker returns a
ServiceError from controls_integrity. Per PRD-5.1 §"Per-target gate rules"
rule 1, that target's `handoff_status` must be `HOLD_INVESTIGATION_FAILED`
and `service_error_status_code` must carry the upstream code.

`book_new_issues` at D_08 satisfies this: get_risk_summary returns a
RiskSummary (DEGRADED status, but typed RiskSummary nonetheless), while
data_controller.assess_integrity returns ServiceError(MISSING_CONTROL_CONTEXT).
"""

from __future__ import annotations

from src.modules.controls_integrity.fixtures import ControlsIntegrityFixtureIndex
from src.modules.risk_analytics.fixtures import FixtureIndex
from src.orchestrators.daily_risk_investigation import (
    HandoffStatus,
    OutcomeKind,
    ReadinessState,
    TerminalRunStatus,
    start_daily_run,
)

from .conftest import (
    D_08,
    SNAP_D_08,
    VAR_1D_99,
    book_new_issues,
    division_toh,
)


def test_hold_investigation_failed_for_walker_service_error_target(risk_index: FixtureIndex, controls_index: ControlsIntegrityFixtureIndex) -> None:
    failing_target = book_new_issues()
    succeeding_target = division_toh()
    candidates = (succeeding_target, failing_target)

    result = start_daily_run(
        as_of_date=D_08,
        snapshot_id=SNAP_D_08,
        candidate_targets=candidates,
        measure_type=VAR_1D_99,
        risk_fixture_index=risk_index,
        controls_fixture_index=controls_index,
    )

    assert result.readiness_state is ReadinessState.READY
    # Both candidates resolve in the snapshot at D_08 (have RiskSummary entries),
    # so neither is excluded by the MISSING_NODE filter at Stage 3.
    assert result.selected_targets == candidates

    # Target outcomes: succeeding_target → ASSESSMENT; failing_target → SERVICE_ERROR.
    by_node = {r.node_ref: r for r in result.target_results}
    assert by_node[succeeding_target].outcome_kind is OutcomeKind.ASSESSMENT
    assert by_node[failing_target].outcome_kind is OutcomeKind.SERVICE_ERROR
    failing_se = by_node[failing_target].service_error
    assert failing_se is not None
    assert failing_se.status_code == "MISSING_CONTROL_CONTEXT"

    # Challenge gate (Stage 7): SE outcome → HOLD_INVESTIGATION_FAILED with status code propagated.
    handoff_by_node = {h.node_ref: h for h in result.handoff}
    failing_handoff = handoff_by_node[failing_target]
    assert failing_handoff.handoff_status is HandoffStatus.HOLD_INVESTIGATION_FAILED
    assert failing_handoff.service_error_status_code == "MISSING_CONTROL_CONTEXT"
    assert failing_handoff.blocking_reason_codes == ()
    assert failing_handoff.cautionary_reason_codes == ()

    # Mixed run: at least one SE + at least one assessment → COMPLETED_WITH_FAILURES.
    assert result.terminal_status is TerminalRunStatus.COMPLETED_WITH_FAILURES
    assert result.partial is True
