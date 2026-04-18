from __future__ import annotations

import argparse
from pathlib import Path
import sys


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify multi-platform skill mirrors and inventories are in sync.")
    parser.add_argument("--root", help="Repository root to check. Defaults to the repo root containing this script.")
    return parser.parse_args()


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    from scripts.skills.common import find_mirror_drift

    args = parse_args()
    check_root = repo_root if args.root is None else _resolve_root(repo_root, args.root)
    findings = find_mirror_drift(check_root)
    if not findings:
        print("Skill mirrors are in sync.")
        return 0

    print("Skill mirror drift detected:")
    for finding in findings:
        print(f"- {finding}")
    return 1


def _resolve_root(repo_root: Path, raw_root: str) -> Path:
    candidate = Path(raw_root)
    resolved = candidate if candidate.is_absolute() else (repo_root / candidate)
    resolved = resolved.resolve()
    if not resolved.exists():
        raise FileNotFoundError(f"Repository root `{resolved}` does not exist.")
    if not resolved.is_dir():
        raise NotADirectoryError(f"Repository root `{resolved}` is not a directory.")
    return resolved


if __name__ == "__main__":
    raise SystemExit(main())
