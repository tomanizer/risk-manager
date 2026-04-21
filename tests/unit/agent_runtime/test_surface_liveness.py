from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pytest

from agent_runtime.drift.surface_liveness import build_surface_liveness_report


def _repo_git_binding() -> tuple[str, str]:
    repo_root = Path(__file__).resolve().parents[3]
    git_dir = subprocess.run(
        ["git", "rev-parse", "--git-dir"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    work_tree = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    return git_dir, work_tree


def test_surface_liveness_report_detects_missing_repo_module_entrypoint(tmp_path: Path) -> None:
    _write_surface_liveness_repo(tmp_path)
    (tmp_path / "agent_runtime").mkdir(parents=True, exist_ok=True)
    (tmp_path / "agent_runtime" / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / "docs" / "guide.md").write_text(".venv/bin/python -m agent_runtime\n", encoding="utf-8")

    report = build_surface_liveness_report(tmp_path)

    assert report.stats.findings_count == 1
    finding = report.findings[0]
    assert finding.kind == "missing_repo_module_entrypoint"
    assert finding.related_path == "agent_runtime"


def test_surface_liveness_report_ignores_repo_bound_git_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    git_dir, work_tree = _repo_git_binding()
    monkeypatch.setenv("GIT_DIR", git_dir)
    monkeypatch.setenv("GIT_WORK_TREE", work_tree)

    _write_surface_liveness_repo(tmp_path)
    (tmp_path / "agent_runtime").mkdir(parents=True, exist_ok=True)
    (tmp_path / "agent_runtime" / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / "docs" / "guide.md").write_text(".venv/bin/python -m agent_runtime\n", encoding="utf-8")

    report = build_surface_liveness_report(tmp_path)

    assert report.stats.active_text_files_scanned == 6
    assert report.stats.findings_count == 1
    assert report.findings[0].kind == "missing_repo_module_entrypoint"


def test_surface_liveness_report_detects_legacy_import_in_active_code(tmp_path: Path) -> None:
    _write_surface_liveness_repo(tmp_path)
    app_path = tmp_path / "src" / "app.py"
    app_path.parent.mkdir(parents=True, exist_ok=True)
    app_path.write_text("from agent_runtime.legacy.dispatch import run\n", encoding="utf-8")

    report = build_surface_liveness_report(tmp_path)

    legacy_findings = [f for f in report.findings if f.kind == "active_code_imports_legacy_surface"]
    assert len(legacy_findings) >= 1
    related_paths = {f.related_path for f in legacy_findings}
    assert "agent_runtime.legacy.dispatch" in related_paths


def test_surface_liveness_report_detects_legacy_import_via_from_import(tmp_path: Path) -> None:
    _write_surface_liveness_repo(tmp_path)
    pkg_dir = tmp_path / "agent_runtime" / "services"
    pkg_dir.mkdir(parents=True, exist_ok=True)
    (tmp_path / "agent_runtime" / "__init__.py").write_text("", encoding="utf-8")
    (pkg_dir / "__init__.py").write_text("", encoding="utf-8")
    (pkg_dir / "runner.py").write_text("from agent_runtime import legacy\n", encoding="utf-8")

    report = build_surface_liveness_report(tmp_path)

    legacy_findings = [f for f in report.findings if f.kind == "active_code_imports_legacy_surface"]
    assert len(legacy_findings) == 1
    assert legacy_findings[0].related_path == "agent_runtime.legacy"


def test_surface_liveness_report_ignores_non_repo_entrypoints(tmp_path: Path) -> None:
    _write_surface_liveness_repo(tmp_path)
    (tmp_path / "docs" / "guide.md").write_text("python -m pytest\npython -m mypy src/\n", encoding="utf-8")

    report = build_surface_liveness_report(tmp_path)

    assert report.findings == ()


def test_check_surface_liveness_cli_writes_json_report(tmp_path: Path) -> None:
    _write_surface_liveness_repo(tmp_path)
    output_path = tmp_path / "artifacts" / "drift" / "surface_liveness.json"

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/drift/check_surface_liveness.py",
            "--root",
            str(tmp_path),
            "--output",
            str(output_path),
        ],
        cwd=Path(__file__).resolve().parents[3],
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(completed.stdout)
    written_payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert payload["scan_name"] == "surface_liveness"
    assert payload["root"] == "."
    assert payload == written_payload
    assert payload["stats"]["findings_count"] == 0


def test_repo_surface_liveness_scan_has_no_findings() -> None:
    repo_root = Path(__file__).resolve().parents[3]

    report = build_surface_liveness_report(repo_root)

    assert report.findings == ()


def _write_surface_liveness_repo(root: Path) -> None:
    (root / "README.md").write_text("# Repo\n", encoding="utf-8")
    (root / "AGENTS.md").write_text("# AGENTS\n", encoding="utf-8")
    (root / "docs").mkdir(parents=True, exist_ok=True)
    (root / "docs" / "guide.md").write_text("# Guide\n", encoding="utf-8")
    (root / "prompts").mkdir(parents=True, exist_ok=True)
    (root / "prompts" / "agent.md").write_text("Use current entrypoints.\n", encoding="utf-8")
    (root / "work_items" / "ready").mkdir(parents=True, exist_ok=True)
    (root / "work_items" / "ready" / "WI-1.md").write_text("# Work item\n", encoding="utf-8")
    (root / ".github").mkdir(parents=True, exist_ok=True)
    (root / ".github" / "copilot-instructions.md").write_text("# Copilot\n", encoding="utf-8")
