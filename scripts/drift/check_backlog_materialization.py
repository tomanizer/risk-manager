from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scan implementation-ready PRDs for decomposed work items that have not been materialized in the live backlog."
    )
    parser.add_argument("--root", help="Repository root to scan. Defaults to the repo root containing this script.")
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
        sys.path.insert(0, str(repo_root))

    from agent_runtime.drift.backlog_materialization import build_backlog_materialization_report

    args = parse_args()
    scan_root = repo_root if args.root is None else _resolve_scan_root(repo_root, args.root)
    report = build_backlog_materialization_report(scan_root)
    payload = json.dumps(report.to_dict(), indent=2, sort_keys=True)
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(payload + "\n", encoding="utf-8")
    print(payload)
    if args.fail_on_findings and report.findings:
        return 1
    return 0


def _resolve_scan_root(repo_root: Path, raw_root: str) -> Path:
    candidate = Path(raw_root)
    resolved = candidate if candidate.is_absolute() else (repo_root / candidate)
    resolved = resolved.resolve()
    if not resolved.exists():
        raise FileNotFoundError(f"Scan root `{resolved}` does not exist.")
    if not resolved.is_dir():
        raise NotADirectoryError(f"Scan root `{resolved}` is not a directory.")
    return resolved


if __name__ == "__main__":
    raise SystemExit(main())
