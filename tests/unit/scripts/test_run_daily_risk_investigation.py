from __future__ import annotations

from src.orchestrators.daily_risk_investigation import ReadinessState, TerminalRunStatus

from scripts.run_daily_risk_investigation import run_scenario


def test_happy_path_scenario_completes_with_selected_targets() -> None:
    scenario, result = run_scenario("happy-path")

    assert scenario.name == "happy-path"
    assert result.readiness_state is ReadinessState.READY
    assert len(result.selected_targets) == 2
    assert result.terminal_status in {
        TerminalRunStatus.COMPLETED,
        TerminalRunStatus.COMPLETED_WITH_CAVEATS,
    }


def test_blocked_readiness_scenario_short_circuits() -> None:
    scenario, result = run_scenario("blocked-readiness")

    assert scenario.name == "blocked-readiness"
    assert result.readiness_state is ReadinessState.BLOCKED
    assert result.terminal_status is TerminalRunStatus.BLOCKED_READINESS
    assert result.selected_targets == ()


def test_missing_node_exclusion_filters_legal_entity_variant() -> None:
    scenario, result = run_scenario("missing-node-exclusion")

    assert scenario.name == "missing-node-exclusion"
    assert result.readiness_state is ReadinessState.READY
    assert result.terminal_status in {
        TerminalRunStatus.COMPLETED,
        TerminalRunStatus.COMPLETED_WITH_CAVEATS,
    }
    assert len(result.selected_targets) == 2
    assert {(node.hierarchy_scope.value, node.legal_entity_id, node.node_id) for node in result.selected_targets} == {
        ("TOP_OF_HOUSE", None, "FIRM_GRP"),
        ("TOP_OF_HOUSE", None, "DIV_GM"),
    }


def test_hold_investigation_failed_scenario_produces_partial_run() -> None:
    scenario, result = run_scenario("hold-investigation-failed")

    assert scenario.name == "hold-investigation-failed"
    assert result.readiness_state is ReadinessState.READY
    assert result.terminal_status is TerminalRunStatus.COMPLETED_WITH_FAILURES
    assert result.partial is True
