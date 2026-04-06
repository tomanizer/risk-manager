from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import timezone, datetime
from pathlib import Path


# ---------------------------------------------------------------------------
# Context surface loading
# ---------------------------------------------------------------------------

_CONTEXT_SURFACES: list[tuple[str, str]] = [
    ("deterministic_summary", "artifacts/drift/summary.md"),
    ("deterministic_report", "artifacts/drift/latest_report.json"),
    ("registry", "docs/registry/current_state_registry.yaml"),
    ("agents_md", "AGENTS.md"),
    ("tom_overview", "docs/00_tom_overview.md"),
    ("delivery_canon", "docs/delivery/05_repo_drift_monitoring.md"),
]

_SYSTEM_PROMPT_PATH = "prompts/agents/drift_monitor_agent_instruction.md"

# Cap the number of findings serialised into the prompt to avoid exceeding
# model context limits and driving up token costs on noisy weeks.
_MAX_FINDINGS_IN_PROMPT = 50


def _load_surface(repo_root: Path, rel_path: str) -> tuple[str, str | None]:
    """Return (rel_path, content_or_None). Unavailable or undecodable files return None."""
    abs_path = repo_root / rel_path
    try:
        return rel_path, abs_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return rel_path, None


def _load_all_surfaces(repo_root: Path) -> dict[str, str | None]:
    result: dict[str, str | None] = {}
    for key, path in _CONTEXT_SURFACES:
        _, content = _load_surface(repo_root, path)
        result[key] = content
    return result


def _load_report(report_path: Path) -> dict | None:  # type: ignore[type-arg]
    try:
        return json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None


def _load_system_prompt(repo_root: Path) -> str:
    _, content = _load_surface(repo_root, _SYSTEM_PROMPT_PATH)
    return content or "You are the drift monitor agent for the risk-manager repository."


# ---------------------------------------------------------------------------
# Prompt assembly
# ---------------------------------------------------------------------------

def _truncate_report_for_prompt(report: dict) -> str:  # type: ignore[type-arg]
    """Serialise the report, capping findings at _MAX_FINDINGS_IN_PROMPT."""
    findings = report.get("findings", [])
    if len(findings) <= _MAX_FINDINGS_IN_PROMPT:
        return json.dumps(report, indent=2)
    truncated = dict(report)
    truncated["findings"] = findings[:_MAX_FINDINGS_IN_PROMPT]
    truncated["_truncated"] = f"findings list truncated to {_MAX_FINDINGS_IN_PROMPT} of {len(findings)} for prompt brevity"
    return json.dumps(truncated, indent=2)


def _assemble_user_message(surfaces: dict[str, str | None]) -> str:
    missing_notes: list[str] = []

    def _section(label: str, key: str) -> str:
        val = surfaces.get(key)
        if val is None:
            missing_notes.append(f"- {label}: not found on disk")
            return f"## {label}\n\n*(surface missing — not available)*\n"
        return f"## {label}\n\n{val}\n"

    parts: list[str] = [
        "You are the drift monitor agent for the risk-manager repository.\n",
        "The deterministic scanner suite has already run. Here is the aggregate output:\n",
        _section("Deterministic summary", "deterministic_summary"),
        _section("Full finding list (JSON)", "deterministic_report"),
        _section("Registry snapshot", "registry"),
        _section("AGENTS.md", "agents_md"),
        _section("Project overview (TOM)", "tom_overview"),
        _section("Drift monitoring delivery canon", "delivery_canon"),
    ]

    if missing_notes:
        parts.append("## Missing context surfaces\n\n" + "\n".join(missing_notes) + "\n")

    parts.append(
        "Perform a synthesis pass. Focus on:\n"
        "1. Themes and root causes across the findings above\n"
        "2. Findings that are surprising, recurring, or indicate a systemic problem\n"
        "3. Areas of the repo that are drifting silently (not yet caught by deterministic checks)\n"
        "4. The two or three highest-leverage actions to reduce drift before the next agent coding run\n\n"
        "Output format:\n"
        "- Overall health: HEALTHY / WATCH / DRIFTING\n"
        "- Thematic summary (2–4 bullet points)\n"
        "- Root-cause hypotheses for any critical or major findings\n"
        "- Top priority actions (ranked, with owner and drift class)\n"
        "- Any patterns not yet covered by deterministic scanners (flag as CANDIDATE findings)\n"
    )

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Output rendering
# ---------------------------------------------------------------------------

def _render_output(llm_content: str, model: str, new_findings: int, waived_findings: int) -> str:
    today = datetime.now(timezone.utc).date().isoformat()
    return (
        f"<!-- drift-synthesis -->\n"
        f"## Drift Synthesis — {today}\n\n"
        f"**Health:** (see synthesis below)\n"
        f"**Model:** {model}\n"
        f"**Findings in report:** {new_findings} net-new, {waived_findings} waived\n\n"
        f"{llm_content}\n"
    )


# ---------------------------------------------------------------------------
# LLM call
# ---------------------------------------------------------------------------

def _call_openai(system_prompt: str, user_message: str, model: str) -> str:
    try:
        import openai  # type: ignore[import-untyped]
    except ImportError as exc:
        raise RuntimeError("openai package is not installed. Add 'openai>=1.0' to project dependencies.") from exc

    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY environment variable is not set.")

    client = openai.OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
    )
    return response.choices[0].message.content or ""


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run LLM drift synthesis against the latest deterministic report.")
    parser.add_argument("--report", default="artifacts/drift/latest_report.json", help="Path to latest_report.json.")
    parser.add_argument("--repo-root", default=".", help="Repository root (default: CWD).")
    parser.add_argument("--output", default="artifacts/drift/synthesis.md", help="Output markdown path.")
    parser.add_argument("--model", default="o4-mini", help="OpenAI model name (default: o4-mini).")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    repo_root = Path(args.repo_root).resolve()
    report_path = Path(args.report) if Path(args.report).is_absolute() else repo_root / args.report
    output_path = Path(args.output) if Path(args.output).is_absolute() else repo_root / args.output

    # --- Load report ---
    report = _load_report(report_path)
    if report is None:
        print(f"[run_synthesis] ERROR: could not read or parse report at {report_path}", file=sys.stderr)
        return 1

    new_findings: int = int(report.get("stats", {}).get("new_findings", 0))
    waived_findings: int = int(report.get("stats", {}).get("waived_findings", 0))

    # Exit 2: zero findings — skip synthesis (non-fatal)
    if new_findings == 0:
        print("[run_synthesis] No net-new findings — synthesis skipped.", file=sys.stderr)
        return 2

    # --- Check API key early ---
    if not os.environ.get("OPENAI_API_KEY", ""):
        print("[run_synthesis] ERROR: OPENAI_API_KEY is not set.", file=sys.stderr)
        return 1

    # --- Load context surfaces ---
    surfaces = _load_all_surfaces(repo_root)
    # Override deterministic_report with pretty-printed JSON (capped) from the already-parsed payload
    surfaces["deterministic_report"] = _truncate_report_for_prompt(report)

    # --- Build prompts ---
    system_prompt = _load_system_prompt(repo_root)
    user_message = _assemble_user_message(surfaces)

    # --- Call LLM ---
    try:
        llm_content = _call_openai(system_prompt, user_message, args.model)
    except RuntimeError as exc:
        print(f"[run_synthesis] ERROR: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"[run_synthesis] ERROR: LLM call failed: {exc}", file=sys.stderr)
        return 1

    # --- Write output ---
    output = _render_output(llm_content, args.model, new_findings, waived_findings)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(output, encoding="utf-8")
    print(f"[run_synthesis] Synthesis written to {output_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
