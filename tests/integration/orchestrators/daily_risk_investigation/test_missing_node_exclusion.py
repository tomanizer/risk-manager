"""WI-5.1.2 — MISSING_NODE exclusion in Stage 3 target_selection.

Candidate set includes a node that is not present in the fixture snapshot
(`division_le_uk` at the TOP_OF_HOUSE-only D_02 snapshot returns
`ServiceError(MISSING_NODE)` from `get_risk_summary`). The orchestrator must
exclude that node from `selected_targets` and complete with the remaining
targets, per PRD-5.1 Stage 3 §"target_selection".
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
    division_le_uk,
    division_toh,
    firm_grp,
)


def test_missing_node_excluded_from_selection(risk_index: FixtureIndex, controls_index: ControlsIntegrityFixtureIndex) -> None:
    excluded = division_le_uk()
    surviving_a = firm_grp()
    surviving_b = division_toh()
    candidates = (surviving_a, excluded, surviving_b)

    result = start_daily_run(
        as_of_date=D_02,
        snapshot_id=SNAP_D_02,
        candidate_targets=candidates,
        measure_type=VAR_1D_99,
        risk_fixture_index=risk_index,
        controls_fixture_index=controls_index,
    )

    # Readiness gate uses surviving_a as canary → READY.
    assert result.readiness_state is ReadinessState.READY
    assert result.readiness_reason_codes == ()

    # Stage 3 filter: excluded MISSING_NODE entry is dropped; order of survivors
    # is preserved as in the input.
    assert result.selected_targets == (surviving_a, surviving_b)
    assert excluded not in result.selected_targets

    # Per-target outcomes are produced for every selected target only.
    assert len(result.target_results) == len(result.selected_targets)
    for tr, expected_node in zip(result.target_results, result.selected_targets, strict=True):
        assert tr.node_ref == expected_node
        assert tr.outcome_kind is OutcomeKind.ASSESSMENT

    # Handoff is parallel to selected_targets.
    assert len(result.handoff) == len(result.selected_targets)

    # Run completes (no service errors after selection in this fixture combo).
    assert result.terminal_status in {
        TerminalRunStatus.COMPLETED,
        TerminalRunStatus.COMPLETED_WITH_CAVEATS,
    }
    assert result.partial is False
