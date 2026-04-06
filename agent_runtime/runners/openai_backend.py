"""OpenAI SDK reasoning backend for PM, Spec, and Review runner roles.

Import is guarded: ``openai`` is an optional dependency (``pip install .[sdk]``).
The functions in this module are only called when the runner is configured with
``AGENT_RUNTIME_{ROLE}_BACKEND=openai_api``.
"""

from __future__ import annotations

import json
from pathlib import Path

from agent_runtime.config.settings import get_settings

from ._outcome_parsing import parse_structured_outcome
from .contracts import RunnerDispatchStatus, RunnerExecution, RunnerResult
from .prompt_loader import load_system_prompt


def dispatch_openai_reasoning(
    execution: RunnerExecution,
    repo_root: Path,
    model: str,
    allowed_decisions: dict[str, str],
    output_schema: dict[str, object],
) -> RunnerResult:
    """Dispatch a reasoning role (PM, Spec, Review) via the OpenAI SDK.

    Uses ``client.chat.completions.create()`` with a ``json_schema``
    ``response_format`` for structured output.  The system prompt is loaded
    from the governed instruction file for the runner's role.

    Args:
        execution: runner execution context.
        repo_root: repository root used to load the governed system prompt.
        model: OpenAI model identifier (e.g. ``"gpt-4o"``).
        allowed_decisions: mapping of uppercase decision key → normalised value.
        output_schema: JSON Schema object describing the expected response shape.

    Returns:
        ``RunnerResult`` with ``status=COMPLETED`` and outcome fields populated
        on success, or ``status=FAILED`` with a descriptive summary on error.
    """
    try:
        import openai
    except ImportError:
        return RunnerResult(
            runner_name=execution.runner_name,
            work_item_id=execution.work_item_id,
            status=RunnerDispatchStatus.FAILED,
            summary=(
                f"{execution.runner_name.value} OpenAI backend requires the openai package. "
                "Install it with: pip install '.[sdk]'"
            ),
            prompt=execution.prompt,
            details=dict(execution.metadata),
        )

    role = execution.runner_name.value

    openai_cfg = get_settings().openai
    try:
        api_key = openai_cfg.api_key_str
    except ValueError as exc:
        return RunnerResult(
            runner_name=execution.runner_name,
            work_item_id=execution.work_item_id,
            status=RunnerDispatchStatus.FAILED,
            summary=f"{role} OpenAI backend is not configured: {exc}",
            prompt=execution.prompt,
            details=dict(execution.metadata),
        )

    system_prompt = load_system_prompt(execution.runner_name, repo_root)
    client = openai.OpenAI(
        api_key=api_key,
        organization=openai_cfg.organization,
        base_url=openai_cfg.base_url,
    )

    try:
        response = client.chat.completions.create(
            model=model,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "outcome",
                    "strict": True,
                    "schema": output_schema,
                },
            },
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": execution.prompt},
            ],
        )
    except openai.AuthenticationError as exc:
        return RunnerResult(
            runner_name=execution.runner_name,
            work_item_id=execution.work_item_id,
            status=RunnerDispatchStatus.FAILED,
            summary=f"{role} OpenAI backend authentication failed: {exc}",
            prompt=execution.prompt,
            details=dict(execution.metadata),
        )
    except openai.APIConnectionError as exc:
        return RunnerResult(
            runner_name=execution.runner_name,
            work_item_id=execution.work_item_id,
            status=RunnerDispatchStatus.FAILED,
            summary=f"{role} OpenAI backend connection error: {exc}",
            prompt=execution.prompt,
            details=dict(execution.metadata),
        )
    except openai.APIError as exc:
        return RunnerResult(
            runner_name=execution.runner_name,
            work_item_id=execution.work_item_id,
            status=RunnerDispatchStatus.FAILED,
            summary=f"{role} OpenAI backend API error: {exc}",
            prompt=execution.prompt,
            details=dict(execution.metadata),
        )

    content = (response.choices[0].message.content or "").strip()
    try:
        payload = json.loads(content)
        if not isinstance(payload, dict):
            raise ValueError("Response is not a JSON object")
    except (json.JSONDecodeError, ValueError) as exc:
        return RunnerResult(
            runner_name=execution.runner_name,
            work_item_id=execution.work_item_id,
            status=RunnerDispatchStatus.FAILED,
            summary=f"{role} OpenAI backend returned unparseable content: {exc}",
            prompt=execution.prompt,
            details=dict(execution.metadata),
        )

    return parse_structured_outcome(payload, allowed_decisions, execution, "openai_api")
