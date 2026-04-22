"""Anthropic SDK backend for PM, Spec, and Review runners.

Import is guarded: ``anthropic`` is only imported when ``anthropic_api``
backend is configured.  Install the optional dependency with::

    pip install 'risk-manager[sdk]'
"""

from __future__ import annotations

from pathlib import Path

from ._outcome_parsing import parse_structured_outcome
from .contracts import RunnerDispatchStatus, RunnerExecution, RunnerResult
from .prompt_loader import load_system_prompt


def _ensure_anthropic() -> None:
    """Raise ImportError with an install hint if the anthropic package is absent."""
    try:
        import anthropic  # noqa: F401
    except ImportError:
        raise ImportError(
            "The 'anthropic' package is required for the anthropic_api backend. Install it with: pip install 'risk-manager[sdk]'"
        ) from None


def dispatch_anthropic_reasoning(
    execution: RunnerExecution,
    repo_root: Path,
    model: str,
    allowed_decisions: dict[str, str],
    output_schema: dict[str, object],
) -> RunnerResult:
    """Dispatch PM/Spec/Review via Anthropic tool_use for structured output.

    Uses ``client.messages.create()`` with a single forced tool call whose
    ``input_schema`` matches ``output_schema``.  The tool input (already a dict
    in anthropic >= 0.40) is passed directly to ``parse_structured_outcome()``.
    The API key is read from ``get_settings().anthropic.api_key_str``.
    """
    _ensure_anthropic()
    import anthropic

    from alterraflow.config import get_settings

    cfg = get_settings()
    try:
        api_key = cfg.anthropic.api_key_str
    except ValueError as exc:
        return RunnerResult(
            runner_name=execution.runner_name,
            work_item_id=execution.work_item_id,
            status=RunnerDispatchStatus.FAILED,
            summary=f"Anthropic backend configuration error: {exc}",
            prompt=execution.prompt,
            details=dict(execution.metadata),
        )

    system_prompt = load_system_prompt(execution.runner_name, repo_root)
    backend_label = f"anthropic_api:{model}"
    tool_name = f"{execution.runner_name.value}_outcome"
    tool_def: dict[str, object] = {
        "name": tool_name,
        "description": f"Structured outcome for the {execution.runner_name.value} role.",
        "input_schema": output_schema,
    }

    try:
        client = anthropic.Anthropic(
            api_key=api_key,
            base_url=cfg.anthropic.base_url,
        )
        response = client.messages.create(
            model=model,
            max_tokens=4096,
            system=system_prompt,
            messages=[{"role": "user", "content": execution.prompt}],
            tools=[tool_def],
            tool_choice={"type": "tool", "name": tool_name},
        )
    except anthropic.AuthenticationError as exc:
        return RunnerResult(
            runner_name=execution.runner_name,
            work_item_id=execution.work_item_id,
            status=RunnerDispatchStatus.FAILED,
            summary=f"Anthropic authentication failed: {exc}",
            prompt=execution.prompt,
            details=dict(execution.metadata),
        )
    except anthropic.APIError as exc:
        return RunnerResult(
            runner_name=execution.runner_name,
            work_item_id=execution.work_item_id,
            status=RunnerDispatchStatus.FAILED,
            summary=f"Anthropic API error: {exc}",
            prompt=execution.prompt,
            details=dict(execution.metadata),
        )

    tool_use_block = next(
        (block for block in response.content if block.type == "tool_use"),
        None,
    )
    if tool_use_block is None:
        return RunnerResult(
            runner_name=execution.runner_name,
            work_item_id=execution.work_item_id,
            status=RunnerDispatchStatus.FAILED,
            summary="Anthropic backend returned no tool_use block.",
            prompt=execution.prompt,
            details=dict(execution.metadata),
        )

    # tool_use_block.input is already a dict in anthropic >= 0.40
    payload = tool_use_block.input
    if not isinstance(payload, dict):
        return RunnerResult(
            runner_name=execution.runner_name,
            work_item_id=execution.work_item_id,
            status=RunnerDispatchStatus.FAILED,
            summary="Anthropic backend tool_use input is not a JSON object.",
            prompt=execution.prompt,
            details=dict(execution.metadata),
        )

    return parse_structured_outcome(payload, allowed_decisions, execution, backend_label)
