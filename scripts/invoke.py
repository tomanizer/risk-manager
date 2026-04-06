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
    matches = list(WORK_ITEMS_DIR.rglob(pattern))
    # Prefer non-archived/done matches when multiple exist
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
# Section extraction from markdown
# ---------------------------------------------------------------------------


def _split_sections(text: str) -> dict[str, str]:
    """Return a dict mapping lowercased section heading → section body text."""
    headings = [(m.start(), m.group(1).strip()) for m in _SECTION_RE.finditer(text)]
    sections: dict[str, str] = {}
    for i, (start, heading) in enumerate(headings):
        end = headings[i + 1][0] if i + 1 < len(headings) else len(text)
        # body is everything after the heading line; find() avoids ValueError on trailing headings
        nl = text.find("\n", start)
        body_start = nl + 1 if nl != -1 else len(text)
        sections[heading.lower()] = text[body_start:end].strip()
    return sections


def _extract_section(sections: dict[str, str], *keys: str) -> str:
    """Return the first matching section body, or empty string.

    Uses exact heading lookup so that e.g. 'scope' does not match 'out of scope'.
    """
    for k in keys:
        body = sections.get(k.lower())
        if body is not None:
            return body
    return ""


# ---------------------------------------------------------------------------
# PRD / ADR path resolution
# ---------------------------------------------------------------------------


def _find_prd(prd_ref: str) -> Optional[Path]:
    """Resolve a PRD reference like 'PRD-1.1-v2' to a file path."""
    if not prd_ref:
        return None
    # Try glob search under docs/
    candidates = list(DOCS_DIR.rglob(f"*{prd_ref}*.md"))
    if candidates:
        return candidates[0]
    # Fuzzy: strip version suffix and try again
    base = re.sub(r"-v\d+$", "", prd_ref, flags=re.IGNORECASE)
    candidates = list(DOCS_DIR.rglob(f"*{base}*.md"))
    return candidates[0] if candidates else None


def _find_adr(adr_ref: str) -> Optional[Path]:
    """Resolve an ADR reference like 'ADR-001' to a file path."""
    candidates = list(ADR_DIR.rglob(f"*{adr_ref}*.md"))
    return candidates[0] if candidates else None


def _repo_relative(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


# ---------------------------------------------------------------------------
# Work-item parsing
# ---------------------------------------------------------------------------


class WorkItemInfo:
    """Parsed representation of a WI-*.md file."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.raw = path.read_text(encoding="utf-8")
        self._sections = _split_sections(self.raw)

        # Work item ID from the H1 heading; re.search + MULTILINE handles files with front-matter
        m = re.search(r"^#\s+(WI-\S+)", self.raw, re.MULTILINE)
        self.wi_id: str = m.group(1) if m else path.stem

        self.linked_prd_raw: str = _extract_section(self._sections, "linked prd")
        self.purpose: str = _extract_section(self._sections, "purpose")
        self.scope: str = _extract_section(self._sections, "scope")
        self.out_of_scope: str = _extract_section(self._sections, "out of scope")
        self.dependencies_raw: str = _extract_section(self._sections, "dependencies")
        self.target_area: str = _extract_section(self._sections, "target area")
        self.acceptance_criteria: str = _extract_section(self._sections, "acceptance criteria")
        self.stop_conditions: str = _extract_section(self._sections, "stop conditions")
        self.review_focus: str = _extract_section(self._sections, "review focus")
        self.suggested_agent: str = _extract_section(self._sections, "suggested agent")

        # Resolve linked PRD path
        prd_id = self.linked_prd_raw.strip().splitlines()[0].strip() if self.linked_prd_raw else ""
        self.prd_path: Optional[Path] = _find_prd(prd_id)

        # Resolve ADR paths from dependencies section
        adr_refs = re.findall(r"ADR-\d+", self.dependencies_raw)
        self.adr_paths: list[Path] = []
        for ref in dict.fromkeys(adr_refs):  # deduplicate, preserve order
            p = _find_adr(ref)
            if p:
                self.adr_paths.append(p)

    def prd_path_str(self) -> str:
        return _repo_relative(self.prd_path) if self.prd_path else f"<PRD not found: {self.linked_prd_raw.strip()}>"

    def adr_paths_str(self) -> str:
        if not self.adr_paths:
            return "<no ADRs found>"
        return "\n".join(_repo_relative(p) for p in self.adr_paths)

    def wi_path_str(self) -> str:
        return _repo_relative(self.path)


# ---------------------------------------------------------------------------
# Template filling
# ---------------------------------------------------------------------------


def _fill_template(template: str, wi: Optional[WorkItemInfo], extra: dict[str, str]) -> str:
    """Replace known <PLACEHOLDER> tokens in template with resolved values.

    Inline placeholders (single path or short text) are replaced in-place.
    List placeholders (ADRs, multi-path areas) that appear as the sole content
    on a ``- <TOKEN>`` line are expanded into properly indented bullet lists.
    """

    # Inline token → replacement text (no leading bullet; template provides it)
    inline: dict[str, str] = {}
    # List tokens that may expand to multiple bullet lines
    # key = token text inside the angle brackets, value = newline-joined paths
    list_tokens: dict[str, str] = {}

    if wi:
        inline["<LINKED_PRD>"] = wi.prd_path_str()
        inline["<ASSIGNED_WORK_ITEM>"] = wi.wi_path_str()
        inline["<TARGET_WORK_ITEM>"] = wi.wi_path_str()
        inline["<WORK_ITEM_ID>"] = wi.wi_id
        inline["<RELEVANT_WORK_ITEMS>"] = wi.wi_path_str()
        # LINKED_ADRS may expand to multiple lines
        list_tokens["<LINKED_ADRS>"] = wi.adr_paths_str()
        # Multi-line block replacements (body sections already contain bullets)
        inline["<BULLETED_SCOPE_LIST — what the coding agent must build>"] = wi.scope or "<scope not found>"
        inline["<TARGET_FILES — exact file paths the agent should create or modify>"] = wi.target_area or "<target area not found>"
        inline["<BULLETED_OUT_OF_SCOPE — explicit reminders of what not to touch>"] = wi.out_of_scope or "<out of scope not found>"
        inline["<BULLETED_ACCEPTANCE_CRITERIA — what must be true when the slice is complete>"] = (
            wi.acceptance_criteria or "<acceptance criteria not found>"
        )
        inline["<BULLETED_STOP_CONDITIONS — when the agent should stop and report a blocker>"] = (
            wi.stop_conditions or "<stop conditions not found in work item>"
        )

    inline.update(extra)

    # Pass 1: expand list tokens that appear as "- <TOKEN>" on their own line
    lines = template.splitlines()
    out_lines: list[str] = []
    for line in lines:
        stripped = line.strip()
        matched = False
        for token, multiline_value in list_tokens.items():
            # Match both "- <TOKEN>" (token as list item) and bare "<TOKEN>"
            if stripped == token or stripped == f"- {token}":
                indent = line[: len(line) - len(line.lstrip())]
                for path in multiline_value.splitlines():
                    out_lines.append(f"{indent}- {path}")
                matched = True
                break
        if not matched:
            out_lines.append(line)

    result = "\n".join(out_lines)

    # Pass 2: inline token substitution
    for token, value in inline.items():
        result = result.replace(token, value)

    return result


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
    wi: Optional[WorkItemInfo] = None
    if args.work_item:
        wi_file = find_work_item_file(args.work_item)
        if not wi_file:
            print(f"error: no work item file found matching '{args.work_item}'", file=sys.stderr)
            return 1
        wi = WorkItemInfo(wi_file)
        print(f"# Resolved work item: {_repo_relative(wi_file)}", file=sys.stderr)
        if wi.prd_path:
            print(f"# Resolved PRD:       {_repo_relative(wi.prd_path)}", file=sys.stderr)
        if wi.adr_paths:
            print(f"# Resolved ADRs:      {', '.join(_repo_relative(p) for p in wi.adr_paths)}", file=sys.stderr)
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
