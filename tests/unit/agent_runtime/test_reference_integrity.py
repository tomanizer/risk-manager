from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pytest

from agent_runtime.drift.reference_integrity import build_reference_scan_report


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


def test_reference_scan_reports_missing_internal_paths(tmp_path: Path) -> None:
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (tmp_path / "README.md").write_text("# root\n", encoding="utf-8")
    (docs_dir / "existing.md").write_text("# existing\n", encoding="utf-8")
    (docs_dir / "guide.md").write_text(
        "\n".join(
            [
                "# Guide",
                "See `docs/existing.md`.",
                "See `docs/missing.md`.",
                "See [prompt](../README.md).",
                "Ignore [external](https://example.com/docs/missing.md).",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    report = build_reference_scan_report(tmp_path)

    assert report.stats.files_scanned == 3
    assert report.stats.findings_count == 1
    finding = report.findings[0]
    assert finding.source_file == "docs/guide.md"
    assert finding.source_line == 3
    assert finding.reference == "docs/missing.md"
    assert finding.drift_class == "canon drift"
    assert finding.owner == "PM"


def test_reference_scan_ignores_repo_bound_git_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    git_dir, work_tree = _repo_git_binding()
    monkeypatch.setenv("GIT_DIR", git_dir)
    monkeypatch.setenv("GIT_WORK_TREE", work_tree)

    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (tmp_path / "README.md").write_text("# root\n", encoding="utf-8")
    (docs_dir / "guide.md").write_text("See `docs/missing.md`.\n", encoding="utf-8")

    report = build_reference_scan_report(tmp_path)

    assert report.stats.files_scanned == 2
    assert report.stats.findings_count == 1
    assert report.findings[0].reference == "docs/missing.md"


def test_reference_scan_classifies_prompt_refs_as_operational_instruction_drift(tmp_path: Path) -> None:
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    (prompts_dir / "agent.md").write_text("Read `docs/does-not-exist.md`.\n", encoding="utf-8")

    report = build_reference_scan_report(tmp_path)

    assert report.stats.findings_count == 1
    finding = report.findings[0]
    assert finding.drift_class == "operational-instruction drift"
    assert finding.owner == "PM"


def test_reference_scan_reports_escaping_paths(tmp_path: Path) -> None:
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "guide.md").write_text("See `../../outside.md`.\n", encoding="utf-8")

    report = build_reference_scan_report(tmp_path)

    assert report.stats.findings_count == 1
    finding = report.findings[0]
    assert finding.reference == "../../outside.md"
    assert "escapes the repository root" in finding.message


def test_reference_scan_allows_documented_generated_artifact_paths(tmp_path: Path) -> None:
    artifacts_drift_dir = tmp_path / "artifacts" / "drift"
    artifacts_drift_dir.mkdir(parents=True)
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (tmp_path / ".gitignore").write_text("artifacts/drift/*.json\n", encoding="utf-8")
    (artifacts_drift_dir / "README.md").write_text(
        "\n".join(
            [
                "# Drift Artifacts",
                "",
                "Recommended local output paths:",
                "- `artifacts/drift/reference_integrity.json`",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (docs_dir / "guide.md").write_text("See `docs/missing.md`.\n", encoding="utf-8")

    report = build_reference_scan_report(tmp_path)

    assert report.stats.findings_count == 1
    assert {finding.reference for finding in report.findings} == {"docs/missing.md"}


def test_reference_scan_reports_undocumented_generated_artifact_paths(tmp_path: Path) -> None:
    artifacts_drift_dir = tmp_path / "artifacts" / "drift"
    artifacts_drift_dir.mkdir(parents=True)
    (tmp_path / ".gitignore").write_text("artifacts/drift/*.json\n", encoding="utf-8")
    (artifacts_drift_dir / "notes.md").write_text(
        "See `artifacts/drift/reference_integrity.json`.\n",
        encoding="utf-8",
    )

    report = build_reference_scan_report(tmp_path)

    assert report.stats.findings_count == 1
    finding = report.findings[0]
    assert finding.reference == "artifacts/drift/reference_integrity.json"
    assert finding.source_file == "artifacts/drift/notes.md"


def test_reference_scan_handles_repo_under_hidden_parent_directory(tmp_path: Path) -> None:
    repo_root = tmp_path / ".shadow" / "repo"
    docs_dir = repo_root / "docs"
    docs_dir.mkdir(parents=True)
    (docs_dir / "guide.md").write_text("See `docs/missing.md`.\n", encoding="utf-8")

    report = build_reference_scan_report(repo_root)

    assert report.stats.files_scanned == 1
    assert report.stats.findings_count == 1
    assert report.findings[0].reference == "docs/missing.md"


def test_reference_scan_skips_backtick_paths_inside_fenced_code_blocks(tmp_path: Path) -> None:
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "guide.md").write_text(
        "\n".join(
            [
                "# Guide",
                "See `docs/real.md` for details.",
                "```bash",
                "python scripts/drift/run_all.py  # docs/missing-in-code-block.md",
                "cat `docs/also-missing.md`",
                "```",
                "After the fence.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (docs_dir / "real.md").write_text("# real\n", encoding="utf-8")

    report = build_reference_scan_report(tmp_path)

    assert report.stats.findings_count == 0


def test_reference_scan_skips_lines_with_drift_ignore_comment(tmp_path: Path) -> None:
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "guide.md").write_text(
        "\n".join(
            [
                "See `docs/missing.md`. <!-- drift-ignore -->",
                "See `docs/also-missing.md`.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    report = build_reference_scan_report(tmp_path)

    assert report.stats.findings_count == 1
    assert report.findings[0].reference == "docs/also-missing.md"


def test_check_references_cli_writes_json_report(tmp_path: Path) -> None:
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "guide.md").write_text("See `docs/missing.md`.\n", encoding="utf-8")
    output_path = tmp_path / "artifacts" / "drift" / "reference_integrity.json"

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/drift/check_references.py",
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

    assert payload["scan_name"] == "reference_integrity"
    assert payload["root"] == "."
    assert payload == written_payload
    assert payload["stats"]["findings_count"] == 1


def test_repo_scan_has_no_missing_test_layout_references() -> None:
    repo_root = Path(__file__).resolve().parents[3]

    report = build_reference_scan_report(repo_root)

    blocked_findings = {
        ("tests/README.md", "tests/integration/"),
        ("tests/README.md", "tests/replay/"),
        ("tests/README.md", "tests/golden_cases/"),
    }

    unexpected = {
        (finding.source_file, finding.reference) for finding in report.findings if (finding.source_file, finding.reference) in blocked_findings
    }

    assert unexpected == set()
