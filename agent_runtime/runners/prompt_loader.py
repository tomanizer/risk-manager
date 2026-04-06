"""Load governed system prompts from the repository prompt pack."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from .contracts import RunnerName

_INSTRUCTION_FILES: dict[RunnerName, str] = {
    RunnerName.PM: "prompts/agents/pm_agent_instruction.md",
    RunnerName.SPEC: "prompts/agents/risk_methodology_spec_agent_instruction.md",
    RunnerName.CODING: "prompts/agents/coding_agent_instruction.md",
    RunnerName.REVIEW: "prompts/agents/review_agent_instruction.md",
}


@lru_cache(maxsize=8)
def _read_file(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_system_prompt(runner_name: RunnerName, repo_root: Path) -> str:
    """Load the governed instruction document for a runner role.

    Falls back to a minimal role preamble when the instruction file
    is missing so that the runtime remains functional in stripped
    environments (CI, tests, fresh clones without prompts/).
    """
    relative_path = _INSTRUCTION_FILES.get(runner_name)
    if relative_path is None:
        return f"You are the {runner_name.value} agent."

    instruction_path = repo_root / relative_path
    if not instruction_path.is_file():
        return f"You are the {runner_name.value} agent."

    return _read_file(instruction_path)
