"""OpenAI SDK backend for PM, Spec, and Review runners.

``openai`` is a base project dependency and is always available.  The import
is kept lazy (inside the dispatch function) so the module can be imported
without side-effects even when the openai_api backend is not configured.
"""

from __future__ import annotations

import json
from pathlib import Path

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
    """Dispatch PM/Spec/Review via OpenAI structured outputs.

    Uses ``client.chat.completions.create()`` with
    ``response_format={"type": "json_schema", ...}``.
    The system prompt is loaded via ``load_system_prompt()``.
    The result is validated by ``parse_structured_outcome()``.
    The API key is read from ``get_settings().openai.api_key_str``.
    """
    import openai

    from agent_runtime.config import get_settings

    cfg = get_settings()
    try:
        api_key = cfg.openai.api_key_str
    except ValueError as exc:
        return RunnerResult(
            runner_name=execution.runner_name,
            work_item_id=execution.work_item_id,
            status=RunnerDispatchStatus.FAILED,
            summary=f"OpenAI backend configuration error: {exc}",
            prompt=execution.prompt,
            details=dict(execution.metadata),
        )

    system_prompt = load_system_prompt(execution.runner_name, repo_root)
    backend_label = f"openai_api:{model}"

    try:
        client = openai.OpenAI(
            api_key=api_key,
            base_url=cfg.openai.base_url,
            organization=cfg.openai.organization,
        )
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": execution.prompt},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": f"{execution.runner_name.value}_outcome",
                    "strict": True,
                    "schema": output_schema,
                },
            },
        )
    except openai.AuthenticationError as exc:
        return RunnerResult(
            runner_name=execution.runner_name,
            work_item_id=execution.work_item_id,
            status=RunnerDispatchStatus.FAILED,
            summary=f"OpenAI authentication failed: {exc}",
            prompt=execution.prompt,
            details=dict(execution.metadata),
        )
    except openai.APIError as exc:
        return RunnerResult(
            runner_name=execution.runner_name,
            work_item_id=execution.work_item_id,
            status=RunnerDispatchStatus.FAILED,
            summary=f"OpenAI API error: {exc}",
            prompt=execution.prompt,
            details=dict(execution.metadata),
        )

    raw_content = response.choices[0].message.content or ""
    try:
        payload = json.loads(raw_content)
        if not isinstance(payload, dict):
            raise ValueError("OpenAI response content is not a JSON object")
    except (json.JSONDecodeError, ValueError) as exc:
        return RunnerResult(
            runner_name=execution.runner_name,
            work_item_id=execution.work_item_id,
            status=RunnerDispatchStatus.FAILED,
            summary=f"OpenAI backend returned unparseable content: {exc}",
            prompt=execution.prompt,
            details=dict(execution.metadata),
        )

    return parse_structured_outcome(payload, allowed_decisions, execution, backend_label)
