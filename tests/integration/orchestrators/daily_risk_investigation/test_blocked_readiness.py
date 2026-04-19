"""WI-5.1.2 — BLOCKED_READINESS short-circuit.

Canary `get_risk_summary` call returns `ServiceError(MISSING_SNAPSHOT)` because
`snapshot_id` does not exist in the fixture pack. Per PRD-5.1 §"Stage 2 —
readiness_gate", this must:

- set `readiness_state = BLOCKED`
- set `readiness_reason_codes = ("MISSING_SNAPSHOT",)`
- skip Stages 3–8 (no walker calls; empty `selected_targets`, `target_results`, `handoff`)
- set `terminal_status = BLOCKED_READINESS`
- fall back `generated_at` to the deterministic 18:00 UTC anchor on `as_of_date`
"""

from __future__ import annotations

from datetime import datetime, time, timezone

from src.modules.controls_integrity.fixtures import ControlsIntegrityFixtureIndex
from src.modules.risk_analytics.fixtures import FixtureIndex
from src.orchestrators.daily_risk_investigation import (
    ReadinessState,
    TerminalRunStatus,
    start_daily_run,
)

from .conftest import D_02, VAR_1D_99, division_toh, firm_grp


def test_missing_snapshot_blocks_readiness(risk_index: FixtureIndex, controls_index: ControlsIntegrityFixtureIndex) -> None:
    candidates = (firm_grp(), division_toh())
    bogus_snapshot_id = "SNAP-DOES-NOT-EXIST-IN-FIXTURE"

    result = start_daily_run(
        as_of_date=D_02,
        snapshot_id=bogus_snapshot_id,
        candidate_targets=candidates,
        measure_type=VAR_1D_99,
        risk_fixture_index=risk_index,
        controls_fixture_index=controls_index,
    )

    assert result.readiness_state is ReadinessState.BLOCKED
    assert result.readiness_reason_codes == ("MISSING_SNAPSHOT",)
    assert result.terminal_status is TerminalRunStatus.BLOCKED_READINESS

    # Stages 3–8 skipped → empty tuples.
    assert result.selected_targets == ()
    assert result.target_results == ()
    assert result.handoff == ()

    # Run-level flags must be False under the blocked path.
    assert result.degraded is False
    assert result.partial is False

    # generated_at fallback: deterministic 18:00 UTC anchor on as_of_date.
    expected_generated_at = datetime.combine(D_02, time(18, 0, tzinfo=timezone.utc))
    assert result.generated_at == expected_generated_at

    # Candidate set is preserved on the result for replay context.
    assert result.candidate_targets == candidates
    assert result.snapshot_id == bogus_snapshot_id
