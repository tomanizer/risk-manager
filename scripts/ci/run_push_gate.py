from __future__ import annotations

import argparse
from pathlib import Path
import shlex
import subprocess
import sys


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the repo-tracked pre-push / CI gate for selected change surfaces.")
    parser.add_argument(
        "--python",
        action="store_true",
        help="Run Python lint, type, format, and test checks.",
    )
    parser.add_argument(
        "--skills",
        action="store_true",
        help="Run skill mirror parity checks.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.python and not args.skills:
        print("push-gate: no check surfaces requested.")
        return 0

    repo_root = Path(__file__).resolve().parents[2]
    failures = 0

    if args.skills:
        failures += run_step(
            "Skill mirror parity",
            [sys.executable, "scripts/skills/check_skill_mirrors.py"],
            repo_root,
        )

    if args.python:
        if has_tracked_paths(repo_root, "*.py", "*.pyi"):
            failures += run_step("Ruff", [sys.executable, "-m", "ruff", "check", "."], repo_root)
            failures += run_step("Mypy", [sys.executable, "-m", "mypy", "src/", "agent_runtime/"], repo_root)
            failures += run_step("Ruff format", [sys.executable, "-m", "ruff", "format", "--check", "."], repo_root)
        else:
            print("push-gate: no tracked Python files found. Skipping Ruff, mypy, and format checks.")

        if has_tracked_paths(repo_root, "tests/**/*.py", "test_*.py", "*_test.py"):
            failures += run_step("Pytest", [sys.executable, "-m", "pytest", "-q"], repo_root)
        else:
            print("push-gate: no tracked Python tests found. Skipping pytest.")

    if failures:
        print(f"push-gate: {failures} check step(s) failed.", file=sys.stderr)
        return 1

    print("push-gate: all requested checks passed.")
    return 0


def has_tracked_paths(repo_root: Path, *patterns: str) -> bool:
    completed = subprocess.run(
        ["git", "ls-files", *patterns],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    return bool(completed.stdout.strip())


def run_step(name: str, command: list[str], repo_root: Path) -> int:
    print(f"push-gate: {name} ...")
    completed = subprocess.run(command, cwd=repo_root, check=False)
    if completed.returncode == 0:
        return 0
    rendered = " ".join(shlex.quote(part) for part in command)
    print(f"push-gate: {name} failed: {rendered}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
