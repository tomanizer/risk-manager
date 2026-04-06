"""Anthropic SDK reasoning backend for PM, Spec, and Review runner roles.

Import is guarded: ``anthropic`` is an optional dependency (``pip install .[sdk]``).
The functions in this module are only called when the runner is configured with
``AGENT_RUNTIME_{ROLE}_BACKEND=anthropic_api``.
"""

from __future__ import annotations

from pathlib import Path

from agent_runtime.config.settings import get_settings

from ._outcome_parsing import parse_structured_outcome
from .contracts import RunnerDispatchStatus, RunnerExecution, RunnerResult
from .prompt_loader import load_system_prompt


def dispatch_anthropic_reasoning(
    execution: RunnerExecution,
    repo_root: Path,
    model: str,
    allowed_decisions: dict[str, str],
    output_schema: dict[str, object],
) -> RunnerResult:
    """Dispatch a reasoning role (PM, Spec, Review) via the Anthropic SDK.

    Uses ``client.messages.create()`` with a single forced ``tool_use`` call
    whose ``input_schema`` matches ``output_schema``.  This guarantees a
    structured JSON response without relying on prompt-based output coercion.

    Args:
        execution: runner execution context.
        repo_root: repository root used to load the governed system prompt.
        model: Anthropic model identifier (e.g. ``"claude-sonnet-4-5"``).
        allowed_decisions: mapping of uppercase decision key → normalised value.
        output_schema: JSON Schema object describing the expected response shape.

    Returns:
        ``RunnerResult`` with ``status=COMPLETED`` and outcome fields populated
        on success, or ``status=FAILED`` with a descriptive summary on error.
    """
    try:
        import anthropic
    except ImportError:
        return RunnerResult(
            runner_name=execution.runner_name,
            work_item_id=execution.work_item_id,
            status=RunnerDispatchStatus.FAILED,
            summary=(
                f"{execution.runner_name.value} Anthropic backend requires the anthropic package. "
                "Install it with: pip install '.[sdk]'"
            ),
            prompt=execution.prompt,
            details=dict(execution.metadata),
        )

    role = execution.runner_name.value

    anthropic_cfg = get_settings().anthropic
    try:
        api_key = anthropic_cfg.api_key_str
    except ValueError as exc:
        return RunnerResult(
            runner_name=execution.runner_name,
            work_item_id=execution.work_item_id,
            status=RunnerDispatchStatus.FAILED,
            summary=f"{role} Anthropic backend is not configured: {exc}",
            prompt=execution.prompt,
            details=dict(execution.metadata),
        )

    system_prompt = load_system_prompt(execution.runner_name, repo_root)
    client = anthropic.Anthropic(
        api_key=api_key,
        base_url=anthropic_cfg.base_url,
    )

    tool_name = "emit_outcome"
    tools = [
        {
            "name": tool_name,
            "description": f"Emit the structured {role} outcome.",
            "input_schema": output_schema,
        }
    ]

    try:
        response = client.messages.create(
            model=model,
            max_tokens=1024,
            system=system_prompt,
            tools=tools,
            tool_choice={"type": "tool", "name": tool_name},
            messages=[{"role": "user", "content": execution.prompt}],
        )
    except anthropic.AuthenticationError as exc:
        return RunnerResult(
            runner_name=execution.runner_name,
            work_item_id=execution.work_item_id,
            status=RunnerDispatchStatus.FAILED,
            summary=f"{role} Anthropic backend authentication failed: {exc}",
            prompt=execution.prompt,
            details=dict(execution.metadata),
        )
    except anthropic.APIConnectionError as exc:
        return RunnerResult(
            runner_name=execution.runner_name,
            work_item_id=execution.work_item_id,
            status=RunnerDispatchStatus.FAILED,
            summary=f"{role} Anthropic backend connection error: {exc}",
            prompt=execution.prompt,
            details=dict(execution.metadata),
        )
    except anthropic.APIError as exc:
        return RunnerResult(
            runner_name=execution.runner_name,
            work_item_id=execution.work_item_id,
            status=RunnerDispatchStatus.FAILED,
            summary=f"{role} Anthropic backend API error: {exc}",
            prompt=execution.prompt,
            details=dict(execution.metadata),
        )

    # Extract the tool_use block input as the structured payload.
    tool_block = next(
        (block for block in response.content if getattr(block, "type", None) == "tool_use"),
        None,
    )
    if tool_block is None:
        return RunnerResult(
            runner_name=execution.runner_name,
            work_item_id=execution.work_item_id,
            status=RunnerDispatchStatus.FAILED,
            summary=f"{role} Anthropic backend returned no tool_use block.",
            prompt=execution.prompt,
            details=dict(execution.metadata),
        )

    payload = tool_block.input
    if not isinstance(payload, dict):
        return RunnerResult(
            runner_name=execution.runner_name,
            work_item_id=execution.work_item_id,
            status=RunnerDispatchStatus.FAILED,
            summary=f"{role} Anthropic backend tool input is not a dict.",
            prompt=execution.prompt,
            details=dict(execution.metadata),
        )

    return parse_structured_outcome(payload, allowed_decisions, execution, "anthropic_api")
