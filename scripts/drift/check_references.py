from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scan repo-tracked text files for broken internal file references.")
    parser.add_argument("--root", default=".", help="Repository root to scan.")
    parser.add_argument("--output", help="Optional JSON report path.")
    parser.add_argument(
        "--fail-on-findings",
        action="store_true",
        help="Exit non-zero when any findings are detected.",
    )
    return parser.parse_args()


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    if str(repo_root) not in sys.path:
        # Allow direct script execution from a repo checkout without requiring installation.
        sys.path.insert(0, str(repo_root))

    from agent_runtime.drift.reference_integrity import build_reference_scan_report

    args = parse_args()
    report = build_reference_scan_report(Path(args.root))
    payload = json.dumps(report.to_dict(), indent=2, sort_keys=True)
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(payload + "\n", encoding="utf-8")
    print(payload)
    if args.fail_on_findings and report.findings:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
