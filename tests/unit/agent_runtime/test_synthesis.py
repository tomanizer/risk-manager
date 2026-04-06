from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "drift" / "run_synthesis.py"


def _make_report(new_findings: int = 1, waived_findings: int = 0) -> dict:  # type: ignore[type-arg]
    return {
        "scan_name": "drift_suite",
        "stats": {
            "new_findings": new_findings,
            "waived_findings": waived_findings,
            "total_findings": new_findings,
            "scans_run": 7,
        },
        "findings": [
            {
                "scan_name": "reference_integrity",
                "kind": "missing_reference",
                "severity": "major",
                "signature": "reference_integrity|kind=missing_reference|...",
                "message": "broken ref",
            }
        ]
        * new_findings,
        "waived_findings": [],
        "scans": [],
    }


def _run_subprocess(tmp_path: Path, extra_env: dict | None = None) -> subprocess.CompletedProcess:  # type: ignore[type-arg]
    import os

    cmd = [
        sys.executable,
        str(_SCRIPT),
        "--report",
        str(tmp_path / "latest_report.json"),
        "--repo-root",
        str(tmp_path),
        "--output",
        str(tmp_path / "synthesis.md"),
    ]

    run_env = os.environ.copy()
    run_env.pop("OPENAI_API_KEY", None)
    if extra_env:
        run_env.update(extra_env)

    return subprocess.run(cmd, capture_output=True, text=True, env=run_env)


def _load_module() -> object:
    import importlib.util
    import types

    spec = importlib.util.spec_from_file_location("run_synthesis", _SCRIPT)
    assert spec is not None and spec.loader is not None
    module = types.ModuleType("run_synthesis")
    spec.loader.exec_module(module)  # type: ignore[attr-defined]
    return module


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_exit_2_when_zero_new_findings(tmp_path: Path) -> None:
    """Script exits 2 (skip) when new_findings == 0 without calling the LLM."""
    report = _make_report(new_findings=0)
    (tmp_path / "latest_report.json").write_text(json.dumps(report), encoding="utf-8")

    result = _run_subprocess(tmp_path)

    assert result.returncode == 2
    assert not (tmp_path / "synthesis.md").exists()


def test_exit_1_when_api_key_missing(tmp_path: Path) -> None:
    """Script exits 1 when OPENAI_API_KEY is not set."""
    report = _make_report(new_findings=2)
    (tmp_path / "latest_report.json").write_text(json.dumps(report), encoding="utf-8")

    result = _run_subprocess(tmp_path)

    assert result.returncode == 1
    assert "OPENAI_API_KEY" in result.stderr


def test_synthesis_output_contains_marker(tmp_path: Path) -> None:
    """Synthesis output file contains the <!-- drift-synthesis --> idempotency marker."""
    module = _load_module()

    report = _make_report(new_findings=1)
    report_path = tmp_path / "latest_report.json"
    report_path.write_text(json.dumps(report), encoding="utf-8")
    output_path = tmp_path / "synthesis.md"

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "**Health:** HEALTHY\n\nThematic summary here."

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response

    old_argv = sys.argv
    sys.argv = [
        str(_SCRIPT),
        "--report",
        str(report_path),
        "--repo-root",
        str(tmp_path),
        "--output",
        str(output_path),
    ]
    try:
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            with patch("openai.OpenAI", return_value=mock_client):
                return_code = module.main()  # type: ignore[attr-defined]
    finally:
        sys.argv = old_argv

    assert return_code == 0
    content = output_path.read_text(encoding="utf-8")
    assert "<!-- drift-synthesis -->" in content


def test_missing_context_surfaces_noted_not_raised(tmp_path: Path) -> None:
    """Missing optional surfaces are noted in the assembled prompt rather than raising exceptions."""
    module = _load_module()

    # tmp_path has no AGENTS.md, registry, etc. — all surfaces are absent
    surfaces = module._load_all_surfaces(tmp_path)  # type: ignore[attr-defined]
    user_message = module._assemble_user_message(surfaces)  # type: ignore[attr-defined]

    assert "Missing context surfaces" in user_message
    assert "not available" in user_message

