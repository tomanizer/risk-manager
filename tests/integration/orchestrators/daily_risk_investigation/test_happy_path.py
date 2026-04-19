"""WI-5.1.2 — Happy-path integration test against existing fixture indices.

Drives `start_daily_run` over a small candidate set drawn from the existing
controls_integrity / risk_analytics fixture packs (no new fixture data).

PRD-5.1 §"Test intent" allows `terminal_status in {COMPLETED, COMPLETED_WITH_CAVEATS}`
because the smallest available fixture is not guaranteed to be fully clean.
"""

from __future__ import annotations

from src.modules.controls_integrity.fixtures import ControlsIntegrityFixtureIndex
from src.modules.risk_analytics.fixtures import FixtureIndex
from src.orchestrators.daily_risk_investigation import (
    OutcomeKind,
    ReadinessState,
    TerminalRunStatus,
    start_daily_run,
)

from .conftest import (
    D_02,
    SNAP_D_02,
    VAR_1D_99,
    division_toh,
    firm_grp,
)


def test_happy_path_completes_against_real_fixtures(risk_index: FixtureIndex, controls_index: ControlsIntegrityFixtureIndex) -> None:
    candidates = (firm_grp(), division_toh())

    result = start_daily_run(
        as_of_date=D_02,
        snapshot_id=SNAP_D_02,
        candidate_targets=candidates,
        measure_type=VAR_1D_99,
        risk_fixture_index=risk_index,
        controls_fixture_index=controls_index,
    )

    assert result.readiness_state is ReadinessState.READY
    assert result.readiness_reason_codes == ()
    assert result.candidate_targets == candidates
    # Both targets resolve in the snapshot, so selection is the input set in order.
    assert result.selected_targets == candidates
    assert len(result.target_results) == len(candidates)
    assert all(r.outcome_kind is OutcomeKind.ASSESSMENT for r in result.target_results)
    assert len(result.handoff) == len(candidates)

    # PRD-5.1 explicitly does not guarantee a fully-clean fixture.
    assert result.terminal_status in {
        TerminalRunStatus.COMPLETED,
        TerminalRunStatus.COMPLETED_WITH_CAVEATS,
    }

    # Run-level flags must be consistent with no service errors.
    assert result.partial is False
    if result.terminal_status is TerminalRunStatus.COMPLETED:
        assert result.degraded is False
    else:
        # COMPLETED_WITH_CAVEATS may or may not flip degraded depending on
        # assessment_status across the assessments.
        assert isinstance(result.degraded, bool)

    # generated_at must equal the max of upstream IntegrityAssessment.generated_at.
    expected_generated_at = max(
        r.assessment.generated_at for r in result.target_results if r.outcome_kind is OutcomeKind.ASSESSMENT and r.assessment is not None
    )
    assert result.generated_at == expected_generated_at

    # Reason-code propagation: handoff entries carry upstream tuples byte-for-byte.
    for tr, h in zip(result.target_results, result.handoff, strict=True):
        assert tr.assessment is not None
        assert h.blocking_reason_codes == tr.assessment.blocking_reason_codes
        assert h.cautionary_reason_codes == tr.assessment.cautionary_reason_codes
        assert h.service_error_status_code is None
