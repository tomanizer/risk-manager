"""Template auto-fill CLI for agent invocation prompts.

Usage:
    python scripts/invoke.py --role coding --work-item WI-1.1.4
    python scripts/invoke.py --role review --work-item WI-1.1.4 --pr 42 --branch codex/wi-1-1-4
    python scripts/invoke.py --role pm --work-item WI-1.1.4 --context "WI-1.1.6 merged."
    python scripts/invoke.py --role drift
    python scripts/invoke.py --list-roles
    python scripts/invoke.py --list-work-items

Reads the matching invocation template from prompts/agents/invocation_templates/,
resolves <PLACEHOLDER> fields from the named work item and its linked PRD / ADRs,
and writes the filled prompt to stdout (or --output <file>).

Fields that require operator context (free-text CONTEXT, TASK, etc.) are left as
bracketed reminders so the operator can complete them before pasting.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Ensure the repository root is in sys.path
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from agent_runtime.handoff_bundle import build_handoff_bundle, HandoffBundle
from typing import Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATES_DIR = REPO_ROOT / "prompts" / "agents" / "invocation_templates"
WORK_ITEMS_DIR = REPO_ROOT / "work_items"
DOCS_DIR = REPO_ROOT / "docs"
ADR_DIR = DOCS_DIR / "adr"
PRD_DIR = DOCS_DIR / "prds"

ROLE_TEMPLATE_MAP: dict[str, str] = {
    "pm": "pm_invocation.md",
    "spec": "prd_spec_invocation.md",
    "prd": "prd_spec_invocation.md",
    "issue-planner": "issue_planner_invocation.md",
    "coding": "coding_invocation.md",
    "review": "review_invocation.md",
    "drift": "drift_monitor_invocation.md",
}

# Section heading patterns used to extract WI sections
_SECTION_RE = re.compile(r"^##\s+(.+)$", re.MULTILINE)


# ---------------------------------------------------------------------------
# Work-item discovery
# ---------------------------------------------------------------------------


def find_work_item_file(work_item_id: str) -> Optional[Path]:
    """Search all subdirectories of work_items/ for a file matching the WI id."""
    pattern = f"*{work_item_id}*"
    matches = sorted(WORK_ITEMS_DIR.rglob(pattern))
    # Prefer non-archived/done matches when multiple exist; sort for determinism
    priority = []
    rest = []
    for m in matches:
        if m.is_file() and m.suffix == ".md":
            if "archived" in m.parts or "done" in m.parts:
                rest.append(m)
            else:
                priority.append(m)
    candidates = priority or rest
    return candidates[0] if candidates else None


def list_work_items() -> list[Path]:
    """Return all WI-*.md files across work_items/ subdirectories."""
    return sorted(WORK_ITEMS_DIR.rglob("WI-*.md"))


# ---------------------------------------------------------------------------
# PRD / ADR path resolution
# ---------------------------------------------------------------------------


def _fill_template(template: str, bundle: Optional[HandoffBundle], extra: dict[str, str]) -> str:
    """Replace known <PLACEHOLDER> tokens in template with resolved values."""

    inline: dict[str, str] = {}
    list_tokens: dict[str, str] = {}

    if bundle:
        inline["<LINKED_PRD>"] = bundle.linked_prd.resolved_path if bundle.linked_prd and bundle.linked_prd.resolved_path else f"<PRD not found: {bundle.linked_prd.reference_text if bundle.linked_prd else 'none'}>"
        inline["<ASSIGNED_WORK_ITEM>"] = bundle.work_item_path
        inline["<TARGET_WORK_ITEM>"] = bundle.work_item_path
        inline["<WORK_ITEM_ID>"] = bundle.work_item_id
        inline["<RELEVANT_WORK_ITEMS>"] = bundle.work_item_path

        adr_paths = []
        for adr in bundle.linked_adrs:
            if adr.resolved_path:
                adr_paths.append(adr.resolved_path)
            else:
                adr_paths.append(f"<ADR not found: {adr.reference_text}>")

        list_tokens["<LINKED_ADRS>"] = "\n".join(adr_paths) if adr_paths else "<no ADRs found>"

        inline["<BULLETED_SCOPE_LIST — what the coding agent must build>"] = bundle.scope or "<scope not found>"
        inline["<TARGET_FILES — exact file paths the agent should create or modify>"] = bundle.target_area or "<target area not found>"
        inline["<BULLETED_OUT_OF_SCOPE — explicit reminders of what not to touch>"] = bundle.out_of_scope or "<out of scope not found>"
        inline["<BULLETED_ACCEPTANCE_CRITERIA — what must be true when the slice is complete>"] = bundle.acceptance_criteria or "<acceptance criteria not found>"
        inline["<BULLETED_STOP_CONDITIONS — when the agent should stop and report a blocker>"] = bundle.stop_conditions or "<stop conditions not found in work item>"

    inline.update(extra)

    lines = template.splitlines()
    out_lines: list[str] = []
    for line in lines:
        stripped = line.strip()
        matched = False
        for token, multiline_value in list_tokens.items():
            if stripped == token or stripped == f"- {token}":
                indent = line[: len(line) - len(line.lstrip())]
                for path in multiline_value.splitlines():
                    out_lines.append(f"{indent}- {path}")
                matched = True
                break
        if not matched:
            out_lines.append(line)

    result = "\n".join(out_lines)

    for token, value in inline.items():
        result = result.replace(token, value)

    return result



def _repo_relative(path: Optional[Path]) -> str:
    if not path:
        return ""
    try:
        return path.resolve().relative_to(_REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fill an agent invocation template from a work item and output the ready-to-paste prompt.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--role",
        choices=sorted(ROLE_TEMPLATE_MAP),
        metavar="ROLE",
        help=f"Agent role. One of: {', '.join(sorted(ROLE_TEMPLATE_MAP))}",
    )
    parser.add_argument(
        "--work-item",
        metavar="WI_ID",
        help="Work item ID fragment, e.g. WI-1.1.4 or 1.1.4",
    )
    parser.add_argument(
        "--pr",
        metavar="NUMBER",
        help="PR number (for review role)",
    )
    parser.add_argument(
        "--branch",
        metavar="NAME",
        help="Branch name (for review role)",
    )
    parser.add_argument(
        "--context",
        metavar="TEXT",
        help="Free-text context to inject into the <CONTEXT> placeholder",
    )
    parser.add_argument(
        "--task",
        metavar="TEXT",
        help="Free-text task description to inject into the <TASK> placeholder",
    )
    parser.add_argument(
        "--focus-area",
        metavar="TEXT",
        help="Focus area for the drift monitor role",
    )
    parser.add_argument(
        "--output",
        metavar="FILE",
        help="Write the filled prompt to this file instead of stdout",
    )
    parser.add_argument(
        "--list-roles",
        action="store_true",
        help="List available roles and exit",
    )
    parser.add_argument(
        "--list-work-items",
        action="store_true",
        help="List discovered work items and exit",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.list_roles:
        print("Available roles:")
        for role, tmpl in sorted(ROLE_TEMPLATE_MAP.items()):
            print(f"  {role:<16}  → {tmpl}")
        return 0

    if args.list_work_items:
        items = list_work_items()
        if not items:
            print("No work items found under work_items/", file=sys.stderr)
            return 1
        print("Discovered work items:")
        for p in items:
            rel = _repo_relative(p)
            status_dir = p.parent.name
            print(f"  [{status_dir}]  {rel}")
        return 0

    if not args.role:
        print("error: --role is required (use --list-roles to see options)", file=sys.stderr)
        return 1

    # Load template
    template_name = ROLE_TEMPLATE_MAP[args.role]
    template_path = TEMPLATES_DIR / template_name
    if not template_path.exists():
        print(f"error: template not found: {template_path}", file=sys.stderr)
        return 1
    template_text = template_path.read_text(encoding="utf-8")

    # Load work item (optional for drift / spec)
    wi: Optional['HandoffBundle'] = None
    if args.work_item:
        wi_file = find_work_item_file(args.work_item)
        if not wi_file:
            print(f"error: no work item file found matching '{args.work_item}'", file=sys.stderr)
            return 1
        wi = build_handoff_bundle(role=args.role, work_item_path=wi_file, repo_root=Path(__file__).resolve().parents[1])
        print(f"# Resolved work item: {_repo_relative(wi_file)}", file=sys.stderr)
        if wi.linked_prd and wi.linked_prd.resolved_path:
            print(f"# Resolved PRD:       {wi.linked_prd.resolved_path}", file=sys.stderr)
        if wi.linked_adrs:
            print(f"# Resolved ADRs:      {', '.join(p.resolved_path for p in wi.linked_adrs if p.resolved_path)}", file=sys.stderr)
    elif args.role not in {"drift", "spec", "prd"}:
        print(f"warning: no --work-item supplied; role '{args.role}' may need one", file=sys.stderr)

    # Build extra replacements from operator-supplied flags
    extra: dict[str, str] = {}
    if args.pr:
        extra["<PR_NUMBER>"] = args.pr
    if args.branch:
        extra["<BRANCH_NAME>"] = args.branch
    if args.context:
        extra["<CONTEXT — what has changed since the last assessment, recent merges, known blockers>"] = args.context
        extra["<CONTEXT — what the PR implements, any known concerns>"] = args.context
        extra["<CONTEXT — what triggered this PRD/spec work, what gap exists, what has changed>"] = args.context
        extra["<CONTEXT — what triggered this planning work, what blocker was identified, what PM assessment found>"] = args.context
        extra["<CONTEXT — what triggered this audit, any known concerns>"] = args.context
        # Generic fallback
        extra["<CONTEXT>"] = args.context
    if args.task:
        extra['<TASK — e.g. "Reassess whether WI-X.Y.Z is now coding-ready on merged main.">'] = args.task
        extra['<TASK — e.g. "Write PRD for X capability" or "Update PRD-1.1 to clarify error semantics for as-of-date retrieval">'] = args.task
        extra['<TASK — e.g. "Create one bounded prerequisite work item that unblocks WI-X.Y.Z">'] = args.task
        extra["<TASK>"] = args.task
    if args.focus_area:
        extra['<FOCUS_AREA — "full repo audit" or a specific area like "canon vs implementation coherence for risk_analytics module">'] = (
            args.focus_area
        )
        extra["<FOCUS_AREA>"] = args.focus_area

    filled = _fill_template(template_text, wi, extra)

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(filled, encoding="utf-8")
        print(f"# Written to: {out_path}", file=sys.stderr)
    else:
        print(filled)

    return 0


if __name__ == "__main__":
    sys.exit(main())
