from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

from agent_runtime.drift.dependency_hygiene import build_dependency_hygiene_report


def test_dependency_hygiene_reports_undeclared_runtime_dependency(tmp_path: Path) -> None:
    _write_pyproject(tmp_path, project_dependencies=["pydantic>=2.0,<3.0"])
    runtime_file = tmp_path / "src" / "app.py"
    runtime_file.parent.mkdir(parents=True)
    runtime_file.write_text("import requests\n", encoding="utf-8")

    report = build_dependency_hygiene_report(tmp_path)

    assert report.stats.findings_count == 1
    finding = report.findings[0]
    assert finding.kind == "undeclared_runtime_dependency"
    assert finding.dependency_name == "requests"
    assert finding.source_path == "src/app.py"
    assert finding.severity == "critical"


def test_dependency_hygiene_reports_runtime_dependency_declared_only_in_optional_extra(tmp_path: Path) -> None:
    _write_pyproject(
        tmp_path,
        project_dependencies=["pydantic>=2.0,<3.0"],
        optional_dependencies={"compute": ["numpy==2.4.4"], "dev": ["pytest==9.0.2"]},
    )
    runtime_file = tmp_path / "agent_runtime" / "service.py"
    runtime_file.parent.mkdir(parents=True)
    runtime_file.write_text("import numpy\n", encoding="utf-8")

    report = build_dependency_hygiene_report(tmp_path)

    assert report.stats.findings_count == 1
    finding = report.findings[0]
    assert finding.kind == "runtime_dependency_declared_only_in_optional_extra"
    assert finding.dependency_name == "numpy"
    assert finding.source_path == "agent_runtime/service.py"
    assert finding.severity == "major"


def test_dependency_hygiene_reports_runtime_dependency_declared_only_in_dev_extra(tmp_path: Path) -> None:
    _write_pyproject(
        tmp_path,
        project_dependencies=["pydantic>=2.0,<3.0"],
        optional_dependencies={"dev": ["pytest==9.0.2"]},
    )
    runtime_file = tmp_path / "src" / "app.py"
    runtime_file.parent.mkdir(parents=True)
    runtime_file.write_text("import pytest\n", encoding="utf-8")

    report = build_dependency_hygiene_report(tmp_path)

    assert report.stats.findings_count == 1
    finding = report.findings[0]
    assert finding.kind == "runtime_dependency_declared_only_in_optional_extra"
    assert finding.dependency_name == "pytest"
    assert finding.source_path == "src/app.py"


def test_dependency_hygiene_reports_workflow_tool_missing_from_dev_extra(tmp_path: Path) -> None:
    _write_pyproject(tmp_path, project_dependencies=["pydantic>=2.0,<3.0"], optional_dependencies={"dev": ["pytest==9.0.2"]})
    workflow = tmp_path / ".github" / "workflows" / "ci.yml"
    workflow.parent.mkdir(parents=True)
    workflow.write_text(
        "\n".join(
            [
                "name: ci",
                "jobs:",
                "  test:",
                "    steps:",
                '      - run: pip install -e ".[dev]"',
                "      - run: mypy src/ agent_runtime/",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    report = build_dependency_hygiene_report(tmp_path)

    assert report.stats.findings_count == 1
    finding = report.findings[0]
    assert finding.kind == "workflow_tool_missing_from_dev_extra"
    assert finding.dependency_name == "mypy"
    assert finding.source_path == ".github/workflows/ci.yml"


def test_dependency_hygiene_reports_stale_requirements_guidance(tmp_path: Path) -> None:
    _write_pyproject(tmp_path, project_dependencies=["pydantic>=2.0,<3.0"])
    doc_path = tmp_path / "docs" / "guide.md"
    doc_path.parent.mkdir(parents=True)
    doc_path.write_text("If you add a dependency, update requirements.txt.\n", encoding="utf-8")

    report = build_dependency_hygiene_report(tmp_path)

    assert report.stats.findings_count == 1
    finding = report.findings[0]
    assert finding.kind == "stale_requirements_txt_update_guidance"
    assert finding.dependency_name == "requirements.txt"
    assert finding.source_path == "docs/guide.md:1"


def test_dependency_hygiene_skips_invalid_python_files(tmp_path: Path) -> None:
    _write_pyproject(tmp_path, project_dependencies=["pydantic>=2.0,<3.0"])
    runtime_file = tmp_path / "src" / "broken.py"
    runtime_file.parent.mkdir(parents=True)
    runtime_file.write_text("def broken(:\n", encoding="utf-8")

    report = build_dependency_hygiene_report(tmp_path)

    assert report.findings == ()


def test_dependency_hygiene_skips_non_utf8_workflow_files(tmp_path: Path) -> None:
    _write_pyproject(tmp_path, project_dependencies=["pydantic>=2.0,<3.0"], optional_dependencies={"dev": ["pytest==9.0.2"]})
    workflow = tmp_path / ".github" / "workflows" / "ci.yml"
    workflow.parent.mkdir(parents=True)
    workflow.write_bytes(b"\xff\xfe\x00\x00")

    report = build_dependency_hygiene_report(tmp_path)

    assert report.findings == ()


def test_dependency_hygiene_skips_non_utf8_instruction_files(tmp_path: Path) -> None:
    _write_pyproject(tmp_path, project_dependencies=["pydantic>=2.0,<3.0"])
    doc_path = tmp_path / "docs" / "guide.md"
    doc_path.parent.mkdir(parents=True)
    doc_path.write_bytes(b"\xff\xfe\x00\x00")

    report = build_dependency_hygiene_report(tmp_path)

    assert report.findings == ()


def test_check_dependency_hygiene_cli_writes_json_report(tmp_path: Path) -> None:
    _write_pyproject(
        tmp_path,
        project_dependencies=["pydantic>=2.0,<3.0"],
        optional_dependencies={"dev": ["pytest==9.0.2", "ruff==0.15.9", "mypy"]},
    )
    runtime_file = tmp_path / "src" / "app.py"
    runtime_file.parent.mkdir(parents=True)
    runtime_file.write_text("import pydantic\n", encoding="utf-8")
    workflow = tmp_path / ".github" / "workflows" / "ci.yml"
    workflow.parent.mkdir(parents=True)
    workflow.write_text(
        "name: ci\njobs:\n  test:\n    steps:\n      - run: pytest -q\n      - run: ruff check .\n      - run: mypy src/\n", encoding="utf-8"
    )
    output_path = tmp_path / "artifacts" / "drift" / "dependency_hygiene.json"

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/drift/check_dependency_hygiene.py",
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

    assert payload["scan_name"] == "dependency_hygiene"
    assert payload["root"] == "."
    assert payload == written_payload
    assert payload["stats"]["findings_count"] == 0


def test_repo_dependency_hygiene_scan_has_no_findings() -> None:
    repo_root = Path(__file__).resolve().parents[3]

    report = build_dependency_hygiene_report(repo_root)

    assert report.findings == ()


def _write_pyproject(
    root: Path,
    *,
    project_dependencies: list[str],
    optional_dependencies: dict[str, list[str]] | None = None,
) -> None:
    optional_dependencies = optional_dependencies or {}
    lines = [
        "[project]",
        'name = "risk-manager"',
        'version = "0.0.0"',
        'requires-python = ">=3.12"',
        "dependencies = [",
    ]
    lines.extend(f'    "{dependency}",' for dependency in project_dependencies)
    lines.append("]")
    if optional_dependencies:
        lines.append("")
        lines.append("[project.optional-dependencies]")
        for extra_name, dependencies in optional_dependencies.items():
            lines.append(f"{extra_name} = [")
            lines.extend(f'    "{dependency}",' for dependency in dependencies)
            lines.append("]")
    (root / "pyproject.toml").write_text("\n".join(lines) + "\n", encoding="utf-8")
