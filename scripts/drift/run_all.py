from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run all deterministic drift scanners, apply baseline filtering, and write aggregate artifacts.")
    parser.add_argument("--root", help="Repository root to scan. Defaults to the repo root containing this script.")
    parser.add_argument("--artifact-dir", help="Directory for per-scanner JSON artifacts. Defaults to `artifacts/drift` under the repo root.")
    parser.add_argument("--baseline", help="Optional baseline JSON file. Defaults to `artifacts/drift/baseline.json` under the repo root.")
    parser.add_argument("--output", help="Optional aggregate JSON report path. Defaults to `artifacts/drift/latest_report.json`.")
    parser.add_argument("--summary-output", help="Optional markdown summary path. Defaults to `artifacts/drift/summary.md`.")
    parser.add_argument(
        "--fail-on-findings",
        action="store_true",
        help="Exit non-zero when net-new findings remain after baseline filtering.",
    )
    return parser.parse_args()


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    from agent_runtime.drift.drift_suite import write_drift_suite_artifacts

    args = parse_args()
    scan_root = repo_root if args.root is None else _resolve_scan_root(repo_root, args.root)
    report = write_drift_suite_artifacts(
        scan_root,
        artifact_dir=None if args.artifact_dir is None else Path(args.artifact_dir),
        baseline_path=None if args.baseline is None else Path(args.baseline),
        output_path=None if args.output is None else Path(args.output),
        summary_output_path=None if args.summary_output is None else Path(args.summary_output),
    )
    payload = json.dumps(report.to_dict(), indent=2, sort_keys=True)
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
