#!/usr/bin/env python3
"""Auto-fill an agent invocation template from a work item file.

Usage:
    python scripts/invoke.py --role coding --work-item WI-1.1.4
    python scripts/invoke.py --role pm --work-item WI-1.1.4
    python scripts/invoke.py --role review --work-item WI-1.1.4 --pr-number 99 --branch fix/WI-1.1.4

The script locates the work item, extracts metadata from its markdown
sections, resolves linked PRDs and ADRs, and fills the template for the
requested role.  Fields that require live context (CONTEXT, TASK, etc.)
are left as labelled prompts so the operator can complete them.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ROLE_ALIASES: dict[str, str] = {
    "pm": "pm",
    "prd-spec": "prd_spec",
    "prd_spec": "prd_spec",
    "spec": "prd_spec",
    "issue-planner": "issue_planner",
    "issue_planner": "issue_planner",
    "coding": "coding",
    "review": "review",
    "drift-monitor": "drift_monitor",
    "drift_monitor": "drift_monitor",
    "drift": "drift_monitor",
}

TEMPLATE_FILENAMES: dict[str, str] = {
    "pm": "pm_invocation.md",
    "prd_spec": "prd_spec_invocation.md",
    "issue_planner": "issue_planner_invocation.md",
    "coding": "coding_invocation.md",
    "review": "review_invocation.md",
    "drift_monitor": "drift_monitor_invocation.md",
}

STAGE_DIRS = ("ready", "in_progress", "blocked", "done")


# ---------------------------------------------------------------------------
# Work item parsing
# ---------------------------------------------------------------------------

def _normalize_heading(line: str) -> str:
    return line.strip().lstrip("#").strip()


def _extract_section_lines(text: str, heading: str) -> list[str]:
    lines = text.splitlines()
    in_section = False
    collected: list[str] = []
    for line in lines:
        if _normalize_heading(line) == _normalize_heading(heading):
            in_section = True
            continue
        if in_section and line.strip().startswith("#"):
            break
        if in_section:
            collected.append(line)
    return collected


def _extract_section_text(text: str, heading: str) -> str:
    return "\n".join(_extract_section_lines(text, heading)).strip()


def _extract_bullet_list(text: str, heading: str) -> list[str]:
    items: list[str] = []
    for line in _extract_section_lines(text, heading):
        stripped = line.strip()
        if stripped.startswith("- "):
            items.append(stripped[2:].strip())
    return items


def _extract_numbered_list(text: str, heading: str) -> list[str]:
    items: list[str] = []
    pattern = re.compile(r"^\d+\.\s+(.+)")
    for line in _extract_section_lines(text, heading):
        match = pattern.match(line.strip())
        if match:
            items.append(match.group(1).strip())
    return items


def _extract_linked_prd(text: str) -> str | None:
    for line in _extract_section_lines(text, "## Linked PRD"):
        stripped = line.strip()
        if stripped:
            return stripped
    return None


def _extract_dependencies(text: str) -> list[str]:
    return _extract_bullet_list(text, "## Dependencies")


def _extract_title(text: str, fallback: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
    return fallback


class WorkItemData:
    def __init__(self, path: Path, text: str) -> None:
        self.path = path
        self.id = path.stem
        self.title = _extract_title(text, path.stem)
        self.linked_prd = _extract_linked_prd(text)
        self.dependencies = _extract_dependencies(text)
        self.scope_lines = _extract_bullet_list(text, "## Scope")
        self.out_of_scope_lines = _extract_bullet_list(text, "## Out of scope")
        self.target_area_lines = _extract_bullet_list(text, "## Target Area")
        self.acceptance_criteria = _extract_bullet_list(text, "## Acceptance Criteria")
        self.acceptance_numbered = _extract_numbered_list(text, "## Acceptance Criteria")
        self.stop_conditions = _extract_bullet_list(text, "## Stop Conditions")
        self.review_focus_lines = _extract_bullet_list(text, "## Review Focus")
        self.suggested_agent = _extract_section_text(text, "## Suggested Agent")

    @property
    def adr_dependencies(self) -> list[str]:
        return [d for d in self.dependencies if d.upper().startswith("ADR")]

    @property
    def wi_dependencies(self) -> list[str]:
        return [d for d in self.dependencies if d.upper().startswith("WI-")]


# ---------------------------------------------------------------------------
# Work item discovery
# ---------------------------------------------------------------------------

def find_repo_root(start: Path) -> Path:
    candidate = start if start.is_dir() else start.parent
    for path in (candidate, *candidate.parents):
        if (path / "AGENTS.md").exists() and (path / "work_items").is_dir():
            return path
    raise RuntimeError(
        "Could not find repository root (no AGENTS.md + work_items/ found in parent chain)."
    )


def find_work_item(repo_root: Path, work_item_id: str) -> Path:
    stem = work_item_id if work_item_id.endswith(".md") else f"{work_item_id}.md"
    # Accept partial prefix match (e.g. "WI-1.1.4" matches WI-1.1.4-risk-summary-core-service.md)
    for stage in STAGE_DIRS:
        stage_dir = repo_root / "work_items" / stage
        if not stage_dir.exists():
            continue
        for candidate in sorted(stage_dir.glob("WI-*.md")):
            if candidate.stem == stem.replace(".md", "") or candidate.stem.startswith(work_item_id):
                return candidate
    raise FileNotFoundError(
        f"Could not find work item '{work_item_id}' in any of work_items/{{{','.join(STAGE_DIRS)}}}/"
    )


def find_template(repo_root: Path, role_key: str) -> Path:
    filename = TEMPLATE_FILENAMES[role_key]
    template_path = repo_root / "prompts" / "agents" / "invocation_templates" / filename
    if not template_path.exists():
        raise FileNotFoundError(f"Template not found: {template_path}")
    return template_path


# ---------------------------------------------------------------------------
# Path resolvers
# ---------------------------------------------------------------------------

def _resolve_prd_path(repo_root: Path, prd_id: str) -> str:
    """Try to resolve a PRD ID to an actual file path.

    Handles full stems and short identifiers like PRD-1.1-v2 by scoring
    how many dash-separated tokens from the ID appear in the filename stem.
    """
    prd_dir = repo_root / "docs" / "prds"
    if not prd_dir.exists():
        return prd_id
    normalized_tokens = set(prd_id.lower().replace(" ", "-").split("-"))
    best_path: str | None = None
    best_score = 0
    for prd_file in sorted(prd_dir.rglob("*.md")):
        if "archive" in prd_file.parts:
            continue
        stem_tokens = set(prd_file.stem.lower().split("-"))
        score = len(normalized_tokens & stem_tokens)
        if score > best_score:
            best_score = score
            best_path = str(prd_file.relative_to(repo_root))
    if best_path and best_score >= 2:
        return best_path
    return prd_id


def _resolve_adr_path(repo_root: Path, adr_id: str) -> str:
    """Try to resolve an ADR ID to an actual file path."""
    for adr_file in sorted((repo_root / "docs" / "adr").rglob("*.md")):
        normalized = adr_id.upper().replace("-", "")
        if normalized in adr_file.stem.upper().replace("-", ""):
            return str(adr_file.relative_to(repo_root))
    return f"docs/adr/{adr_id}.md"


def _make_bullet(items: list[str]) -> str:
    if not items:
        return "- <none listed>"
    return "\n".join(f"- {item}" for item in items)


def _make_numbered(items: list[str]) -> str:
    if not items:
        return "1. <none listed>"
    return "\n".join(f"{i + 1}. {item}" for i, item in enumerate(items))


def _make_read_list(paths: list[str]) -> str:
    return "\n".join(f"- {p}" for p in paths)


# ---------------------------------------------------------------------------
# Template fillers per role
# ---------------------------------------------------------------------------

def _common_read_list(repo_root: Path, wi: WorkItemData, instruction_file: str) -> list[str]:
    paths: list[str] = [
        "AGENTS.md",
        f"prompts/agents/{instruction_file}",
    ]
    if wi.linked_prd:
        prd_path = _resolve_prd_path(repo_root, wi.linked_prd)
        paths.append(prd_path)
    paths.append(str(wi.path.relative_to(repo_root)))
    for adr in wi.adr_dependencies:
        paths.append(_resolve_adr_path(repo_root, adr))
    return paths


def fill_coding(repo_root: Path, wi: WorkItemData, template: str) -> str:
    read_paths = _common_read_list(repo_root, wi, "coding_agent_instruction.md")
    replacements = {
        "- AGENTS.md\n- prompts/agents/coding_agent_instruction.md\n- <LINKED_PRD>\n- <ASSIGNED_WORK_ITEM>\n- <LINKED_ADRS>":
            _make_read_list(read_paths),
        "Implement <WORK_ITEM_ID> exactly as the next bounded slice.":
            f"Implement {wi.id} exactly as the next bounded slice.",
        "<BULLETED_SCOPE_LIST — what the coding agent must build>":
            _make_bullet(wi.scope_lines) if wi.scope_lines else "<BULLETED_SCOPE_LIST — what the coding agent must build>",
        "<TARGET_FILES — exact file paths the agent should create or modify>":
            _make_bullet(wi.target_area_lines) if wi.target_area_lines else "<TARGET_FILES — exact file paths the agent should create or modify>",
        "<BULLETED_OUT_OF_SCOPE — explicit reminders of what not to touch>":
            _make_bullet(wi.out_of_scope_lines) if wi.out_of_scope_lines else "<BULLETED_OUT_OF_SCOPE — explicit reminders of what not to touch>",
        "<BULLETED_ACCEPTANCE_CRITERIA — what must be true when the slice is complete>":
            _make_bullet(wi.acceptance_criteria or wi.acceptance_numbered) if (wi.acceptance_criteria or wi.acceptance_numbered) else "<BULLETED_ACCEPTANCE_CRITERIA — what must be true when the slice is complete>",
        "<BULLETED_STOP_CONDITIONS — when the agent should stop and report a blocker>":
            _make_bullet(wi.stop_conditions) if wi.stop_conditions else "<BULLETED_STOP_CONDITIONS — when the agent should stop and report a blocker>",
    }
    result = template
    for old, new in replacements.items():
        result = result.replace(old, new)
    return result


def fill_pm(repo_root: Path, wi: WorkItemData, template: str) -> str:
    paths: list[str] = [
        "AGENTS.md",
        "prompts/agents/pm_agent_instruction.md",
    ]
    if wi.linked_prd:
        paths.append(_resolve_prd_path(repo_root, wi.linked_prd))
    paths.append(str(wi.path.relative_to(repo_root)))
    for adr in wi.adr_dependencies:
        paths.append(_resolve_adr_path(repo_root, adr))

    replacements = {
        "- AGENTS.md\n- prompts/agents/pm_agent_instruction.md\n- <LINKED_PRD>\n- <TARGET_WORK_ITEM>\n- <LINKED_ADRS>":
            _make_read_list(paths),
    }
    result = template
    for old, new in replacements.items():
        result = result.replace(old, new)
    return result


def fill_prd_spec(repo_root: Path, wi: WorkItemData, template: str) -> str:
    paths: list[str] = [
        "AGENTS.md",
        "prompts/agents/prd_spec_agent_instruction.md",
    ]
    for adr in wi.adr_dependencies:
        paths.append(_resolve_adr_path(repo_root, adr))
    if wi.linked_prd:
        paths.append(_resolve_prd_path(repo_root, wi.linked_prd))
    for wi_dep in wi.wi_dependencies:
        paths.append(f"work_items/ready/{wi_dep}.md")

    replacements = {
        "- AGENTS.md\n- prompts/agents/prd_spec_agent_instruction.md\n- <LINKED_ADRS>\n- <EXISTING_PRD_IF_UPDATING>\n- <RELEVANT_WORK_ITEMS>\n- <RELEVANT_SOURCE_FILES>":
            _make_read_list(paths),
    }
    result = template
    for old, new in replacements.items():
        result = result.replace(old, new)
    return result


def fill_issue_planner(repo_root: Path, wi: WorkItemData, template: str) -> str:
    paths: list[str] = [
        "AGENTS.md",
        "prompts/agents/issue_planner_instruction.md",
    ]
    if wi.linked_prd:
        paths.append(_resolve_prd_path(repo_root, wi.linked_prd))
    for adr in wi.adr_dependencies:
        paths.append(_resolve_adr_path(repo_root, adr))
    for wi_dep in wi.wi_dependencies:
        paths.append(f"work_items/ready/{wi_dep}.md")
    paths.append(str(wi.path.relative_to(repo_root)))

    replacements = {
        "- AGENTS.md\n- prompts/agents/issue_planner_instruction.md\n- <LINKED_PRD>\n- <LINKED_ADRS>\n- <RELEVANT_WORK_ITEMS>\n- <RELEVANT_SOURCE_FILES>":
            _make_read_list(paths),
    }
    result = template
    for old, new in replacements.items():
        result = result.replace(old, new)
    return result


def fill_review(repo_root: Path, wi: WorkItemData, template: str, pr_number: str | None, branch: str | None) -> str:
    paths: list[str] = [
        "AGENTS.md",
        "prompts/agents/review_agent_instruction.md",
        str(wi.path.relative_to(repo_root)),
    ]
    if wi.linked_prd:
        paths.append(_resolve_prd_path(repo_root, wi.linked_prd))
    for adr in wi.adr_dependencies:
        paths.append(_resolve_adr_path(repo_root, adr))

    replacements = {
        "- AGENTS.md\n- prompts/agents/review_agent_instruction.md\n- <ASSIGNED_WORK_ITEM>\n- <LINKED_PRD>\n- <LINKED_ADRS>":
            _make_read_list(paths),
        "- PR #<PR_NUMBER>": f"- PR #{pr_number or '<PR_NUMBER>'}",
        "- branch: <BRANCH_NAME>": f"- branch: {branch or '<BRANCH_NAME>'}",
    }
    if wi.review_focus_lines:
        replacements["1. scope fidelity to the linked work item\n2. contract fidelity to the linked PRD\n3. architecture boundary discipline\n4. degraded and error handling\n5. replay and evidence behavior\n6. test sufficiency\n7. Gemini and Copilot review comments if present"] = (
            "1. scope fidelity to the linked work item\n"
            "2. contract fidelity to the linked PRD\n"
            "3. architecture boundary discipline\n"
            "4. degraded and error handling\n"
            "5. replay and evidence behavior\n"
            "6. test sufficiency\n"
            "7. Gemini and Copilot review comments if present\n\n"
            "Work item review focus:\n" + _make_bullet(wi.review_focus_lines)
        )
    result = template
    for old, new in replacements.items():
        result = result.replace(old, new)
    return result


def fill_drift_monitor(repo_root: Path, wi: WorkItemData, template: str) -> str:  # noqa: ARG001
    # Drift monitor invocations are not WI-specific; return template as-is
    return template


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Auto-fill an agent invocation template from a work item.",
    )
    parser.add_argument(
        "--role",
        required=True,
        choices=sorted(ROLE_ALIASES.keys()),
        help="Agent role to generate the invocation for.",
    )
    parser.add_argument(
        "--work-item",
        required=True,
        help="Work item ID or stem, e.g. WI-1.1.4 or WI-1.1.4-risk-summary-core-service.",
    )
    parser.add_argument(
        "--pr-number",
        default=None,
        help="Pull request number (used for review role).",
    )
    parser.add_argument(
        "--branch",
        default=None,
        help="Branch name (used for review role).",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output file path. Defaults to stdout.",
    )
    parser.add_argument(
        "--repo-root",
        default=None,
        help="Repository root. Defaults to auto-detected root from current directory.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    role_key = ROLE_ALIASES.get(args.role)
    if role_key is None:
        print(f"error: unknown role '{args.role}'", file=sys.stderr)
        return 1

    repo_root_path = Path(args.repo_root) if args.repo_root else find_repo_root(Path.cwd())

    try:
        wi_path = find_work_item(repo_root_path, args.work_item)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    wi_text = wi_path.read_text(encoding="utf-8")
    wi = WorkItemData(wi_path, wi_text)

    try:
        template_path = find_template(repo_root_path, role_key)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    template = template_path.read_text(encoding="utf-8")

    if role_key == "coding":
        filled = fill_coding(repo_root_path, wi, template)
    elif role_key == "pm":
        filled = fill_pm(repo_root_path, wi, template)
    elif role_key == "prd_spec":
        filled = fill_prd_spec(repo_root_path, wi, template)
    elif role_key == "issue_planner":
        filled = fill_issue_planner(repo_root_path, wi, template)
    elif role_key == "review":
        filled = fill_review(repo_root_path, wi, template, args.pr_number, args.branch)
    elif role_key == "drift_monitor":
        filled = fill_drift_monitor(repo_root_path, wi, template)
    else:
        filled = template

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(filled, encoding="utf-8")
        print(f"Invocation written to {out_path}", file=sys.stderr)
    else:
        print(filled)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
