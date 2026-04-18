from __future__ import annotations

import argparse
from pathlib import Path
import sys


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate multi-platform skill mirrors and inventories from canonical skills/.")
    parser.add_argument("--root", help="Repository root to sync. Defaults to the repo root containing this script.")
    return parser.parse_args()


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    from scripts.skills.common import apply_sync

    args = parse_args()
    sync_root = repo_root if args.root is None else _resolve_root(repo_root, args.root)
    skills = apply_sync(sync_root)
    print(f"Synced {len(skills)} skills from `{(sync_root / 'skills').relative_to(sync_root).as_posix()}`.")
    return 0


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
