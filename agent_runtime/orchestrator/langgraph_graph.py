"""LangGraph-backed delivery graph for the agent runtime.

This module is an **optional** replacement for the custom poll loop in
``graph.py``.  It expresses the same delivery state machine as a LangGraph
``StateGraph``, which provides:

- Built-in checkpointing (via ``SqliteEventCheckpointer``)
- ``interrupt`` API for human gate pauses (replaces ``classify_loop_payload`` stop)
- ``Send`` API for parallel fan-out (replaces ``parallel_dispatch.py``)
- Streaming observability out of the box

Architecture mapping
--------------------
::

    RuntimeSnapshot          → DeliveryState (TypedDict)
    NextActionType           → graph nodes
    decide_all_actions()     → conditional edges from ``decide_node``
    human_merge/update_repo  → interrupt() in ``human_gate_node``
    RunnerResult             → state["last_results"] update

Usage
-----
This module requires the ``agent`` optional dependency group:

    pip install "risk-manager[agent]"

Then run the graph from the CLI:

    python -m agent_runtime --langgraph

Or programmatically::

    from agent_runtime.orchestrator.langgraph_graph import build_delivery_graph
    graph = build_delivery_graph(defaults)
    for event in graph.stream(None, config={"configurable": {"thread_id": "WI-1.1.4"}}):
        print(event)
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, TypedDict

from agent_runtime.config.defaults import RuntimeDefaults
from agent_runtime.orchestrator.execution import build_runner_execution
from agent_runtime.orchestrator.graph import build_runtime_snapshot
from agent_runtime.orchestrator.state import NextActionType, TransitionDecision
from agent_runtime.orchestrator.transitions import decide_all_actions
from agent_runtime.runners.dispatch import dispatch_runner_execution

if TYPE_CHECKING:
    pass

_log = logging.getLogger(__name__)

try:
    from langgraph.graph import END, StateGraph
    from langgraph.types import Send, interrupt

    _LANGGRAPH_AVAILABLE = True
except ImportError:
    _LANGGRAPH_AVAILABLE = False


def _require_langgraph() -> None:
    if not _LANGGRAPH_AVAILABLE:
        raise ImportError('langgraph is required for the LangGraph delivery graph. Install it with: pip install "risk-manager[agent]"')


# ---------------------------------------------------------------------------
# State definition
# ---------------------------------------------------------------------------


class DeliveryState(TypedDict, total=False):
    """LangGraph state for one delivery thread (one work item or the full queue)."""

    work_item_id: str | None
    action: str
    reason: str
    retry_count: int
    runner_result: dict[str, object] | None
    parallel_results: list[dict[str, object]]
    warnings: list[str]
    # Internal: accumulated decisions from the decide node
    _decisions: list[dict[str, object]]


# ---------------------------------------------------------------------------
# Graph nodes
# ---------------------------------------------------------------------------


def _snapshot_node(state: DeliveryState, *, defaults: RuntimeDefaults) -> DeliveryState:
    """Build a fresh ``RuntimeSnapshot`` and store it in state."""
    # We don't store the snapshot in state directly (it contains Path objects
    # that aren't serialisable) — instead we store the decisions produced from it.
    snapshot = build_runtime_snapshot(defaults.repo_root, defaults.state_db_path)
    decisions = decide_all_actions(snapshot)
    serialised: list[dict[str, object]] = [
        {
            "action": d.action.value,
            "work_item_id": d.work_item_id,
            "reason": d.reason,
            "target_path": str(d.target_path) if d.target_path else None,
        }
        for d in decisions
    ]
    return {
        "_decisions": serialised,
        "warnings": list(snapshot.warnings),
    }


def _decide_node(state: DeliveryState) -> list[Any] | str:
    """Route decisions to the appropriate agent nodes or to the human gate.

    Uses LangGraph ``Send`` for parallel fan-out when multiple items are ready.
    """
    _require_langgraph()
    decisions: list[dict[str, object]] = state.get("_decisions") or []

    if not decisions:
        return str(END)

    sends: list[Any] = []
    human_gate_needed = False
    for decision in decisions:
        action = str(decision.get("action") or "")
        if action in {"run_pm", "run_spec", "run_coding", "run_review"}:
            sends.append(Send("dispatch_node", decision))
        elif action in {"human_merge", "human_update_repo"}:
            human_gate_needed = True
        # wait_for_reviews / noop: no send, let the graph end naturally

    if human_gate_needed and not sends:
        return "human_gate_node"
    if sends:
        return sends
    return str(END)


def _dispatch_node(decision_payload: dict[str, object], *, defaults: RuntimeDefaults) -> DeliveryState:
    """Execute a single dispatch decision using the action already decided by _decide_node.

    Uses the ``decision_payload`` (passed via ``Send``) to drive execution rather than
    re-deciding from a fresh snapshot, which would break per-decision fan-out semantics.
    """
    action_str = str(decision_payload.get("action") or "")
    work_item_id = str(decision_payload["work_item_id"]) if decision_payload.get("work_item_id") is not None else None
    reason = str(decision_payload.get("reason") or "")
    retry_count = int(str(decision_payload.get("retry_count") or 0))

    try:
        action = NextActionType(action_str)
    except ValueError:
        _log.warning("_dispatch_node received unknown action %r, skipping dispatch", action_str)
        return {
            "action": action_str,
            "work_item_id": work_item_id,
            "reason": reason,
            "retry_count": retry_count,
            "runner_result": None,
        }

    decision = TransitionDecision(action=action, work_item_id=work_item_id, reason=reason)
    snapshot = build_runtime_snapshot(defaults.repo_root, defaults.state_db_path)
    execution = build_runner_execution(snapshot, decision)
    runner_result = dispatch_runner_execution(execution) if execution is not None else None

    result_dict = (
        {
            "name": runner_result.runner_name.value,
            "status": runner_result.status.value,
            "summary": runner_result.summary,
            "outcome_status": runner_result.outcome_status,
            "outcome_summary": runner_result.outcome_summary,
        }
        if runner_result is not None
        else None
    )
    return {
        "action": action_str,
        "work_item_id": work_item_id,
        "reason": reason,
        "retry_count": retry_count,
        "runner_result": result_dict,  # type: ignore[typeddict-item]
    }


def _human_gate_node(state: DeliveryState) -> DeliveryState:
    """Pause the graph and wait for human approval via the interrupt API."""
    _require_langgraph()
    decisions = state.get("_decisions") or []
    gate_decisions = [d for d in decisions if str(d.get("action") or "") in {"human_merge", "human_update_repo"}]
    interrupt({"message": "Human gate reached", "decisions": gate_decisions})
    return state


# ---------------------------------------------------------------------------
# Graph builder
# ---------------------------------------------------------------------------


def build_delivery_graph(
    defaults: RuntimeDefaults,
    *,
    use_checkpointer: bool = True,
) -> Any:
    """Build and compile a LangGraph ``StateGraph`` for the delivery relay.

    Parameters
    ----------
    defaults:
        Runtime configuration (repo root, DB path, timeouts, etc.).
    use_checkpointer:
        If ``True`` (default), wire the ``SqliteEventCheckpointer`` so that
        mid-run state is persisted and restartable.

    Returns
    -------
    langgraph ``CompiledGraph``
    """
    _require_langgraph()

    from functools import partial

    from langgraph.graph import StateGraph

    builder: StateGraph = StateGraph(DeliveryState)

    builder.add_node("snapshot_node", partial(_snapshot_node, defaults=defaults))
    builder.add_node("dispatch_node", partial(_dispatch_node, defaults=defaults))
    builder.add_node("human_gate_node", _human_gate_node)

    builder.set_entry_point("snapshot_node")
    builder.add_conditional_edges("snapshot_node", _decide_node)
    builder.add_edge("dispatch_node", END)
    builder.add_edge("human_gate_node", END)

    checkpointer = None
    if use_checkpointer:
        try:
            from agent_runtime.storage.langgraph_checkpointer import SqliteEventCheckpointer

            checkpointer = SqliteEventCheckpointer(defaults.state_db_path)
        except ImportError:
            _log.warning("SqliteEventCheckpointer unavailable; running without checkpointing")

    return builder.compile(checkpointer=checkpointer)
