from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
from pathlib import Path
import sys


AUTO_REMEDIABLE_KINDS = frozenset(
    {
        "missing_agents_reference",
        "missing_drift_suite_entrypoint",
        "stale_drift_monitor_commands",
        "stale_requirements_txt_update_guidance",
    }
)

WORK_ITEM_TEMPLATE = """\
# Drift Fix: {date}

type: drift_fix
status: ready
created: {timestamp}
source: automated drift monitor

## Summary

The drift monitor detected {count} auto-remediable finding(s) in the latest scan.
These findings have machine-safe fix patterns and should be resolved before the
next coding run to prevent the relay from compounding known drift.

## Findings

{findings_section}

## Instructions

1. For each finding above, apply the fix described in the message.
2. Run `python scripts/drift/run_all.py` locally to verify zero net-new findings.
3. Commit and push. The drift monitor will close this work item automatically
   when the next scan reports zero net-new findings of these kinds.

## Acceptance Criteria

- `python scripts/drift/run_all.py` exits 0 with no net-new findings.
- No new `baseline.json` entries are added; the root causes are fixed.
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a drift-fix work item when auto-remediable findings are present."
    )
    parser.add_argument("--report", required=True, help="Path to latest_report.json.")
    parser.add_argument("--output-dir", help="Directory for the work item. Defaults to `work_items/ready` under the repo root.")
    parser.add_argument("--dry-run", action="store_true", help="Print the work item without writing it.")
    return parser.parse_args()


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    args = parse_args()
    report_path = Path(args.report)
    if not report_path.is_file():
        print(f"ERROR: Report not found at `{report_path}`.", file=sys.stderr)
        return 1

    payload = json.loads(report_path.read_text(encoding="utf-8"))
    all_findings: list[dict[str, object]] = payload.get("findings", [])

    remediable = [f for f in all_findings if f.get("kind") in AUTO_REMEDIABLE_KINDS]
    if not remediable:
        print("No auto-remediable findings in the latest report. Skipping work item creation.")
        return 0

    now = datetime.now(UTC)
    date_str = now.strftime("%Y-%m-%d")
    timestamp = now.isoformat()

    findings_lines: list[str] = []
    for finding in remediable:
        findings_lines.append(
            f"- **{finding['kind']}** (`{finding['scan_name']}`): {finding['message']}"
        )
    findings_section = "\n".join(findings_lines)

    content = WORK_ITEM_TEMPLATE.format(
        date=date_str,
        timestamp=timestamp,
        count=len(remediable),
        findings_section=findings_section,
    )

    if args.dry_run:
        print(content)
        return 0

    output_dir = repo_root / "work_items" / "ready" if args.output_dir is None else Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    work_item_path = output_dir / f"drift-fix-{date_str}.md"

    if work_item_path.exists():
        print(f"Work item already exists at `{work_item_path}`. Skipping.")
        return 0

    work_item_path.write_text(content, encoding="utf-8")
    print(f"Created drift-fix work item: {work_item_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
