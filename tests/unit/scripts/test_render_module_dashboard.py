from __future__ import annotations

from pathlib import Path
import subprocess
import sys

from scripts.render_module_dashboard import load_registry, render_dashboards, render_module_dashboard


def test_render_module_dashboard_contains_expected_sections(tmp_path: Path) -> None:
    registry_path = _write_registry(tmp_path)

    payload = load_registry(registry_path)
    rendered = render_module_dashboard(payload, module_id="MODULE-1-VAR")

    assert "# Module 1 Dashboard: End-to-End VaR Workflow" in rendered
    assert "## Capability Status" in rendered
    assert "| Risk Analytics | module | `implemented` |" in rendered
    assert "PRD-4.2-v2" in rendered
    assert "## Next Recommended Slices" in rendered


def test_render_dashboards_writes_markdown_file(tmp_path: Path) -> None:
    registry_path = _write_registry(tmp_path)
    payload = load_registry(registry_path)

    written = render_dashboards(payload, repo_root=tmp_path, module_id="MODULE-1-VAR")

    assert written == (tmp_path / "docs" / "roadmap" / "module_1_var_dashboard.md",)
    contents = written[0].read_text(encoding="utf-8")
    assert "Source of truth: `docs/registry/current_state_registry.yaml`" in contents


def test_render_module_dashboard_cli_writes_dashboard_file(tmp_path: Path) -> None:
    _write_registry(tmp_path)
    (tmp_path / "AGENTS.md").write_text("# AGENTS\n", encoding="utf-8")

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/render_module_dashboard.py",
            "--root",
            str(tmp_path),
            "--module-id",
            "MODULE-1-VAR",
        ],
        cwd=Path(__file__).resolve().parents[3],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout.strip() == "docs/roadmap/module_1_var_dashboard.md"
    dashboard_path = tmp_path / "docs" / "roadmap" / "module_1_var_dashboard.md"
    assert dashboard_path.is_file()
    assert "# Module 1 Dashboard: End-to-End VaR Workflow" in dashboard_path.read_text(encoding="utf-8")


def _write_registry(root: Path) -> Path:
    registry_path = root / "docs" / "registry" / "current_state_registry.yaml"
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(
        """
version: 2
last_updated: 2026-04-19

module_dashboards:
  - id: MODULE-1-VAR
    name: "Module 1 Dashboard: End-to-End VaR Workflow"
    owner_role: PM / Coordination Agent
    dashboard_path: docs/roadmap/module_1_var_dashboard.md
    overall_state: MVP_PARTIAL
    delivery_phase: Phase 5
    mission: Deliver a replayable, deterministic, explainable daily VaR investigation workflow.
    mvp_definition:
      - deterministic VaR retrieval and change-profile analysis
      - trust / readiness assessment
    summary: Deterministic core exists; multi-walker interpretation is still missing.
    current_mvp_blockers:
      - Quant Walker v2 contract not yet defined
    not_required_for_mvp:
      - Market Context Walker
    journey_stages:
      - label: Deterministic foundation
        goal: canonical deterministic VaR analytics
        status: done
        notes: Risk Analytics is implemented.
    capabilities:
      - component_ref: MOD-RISK-ANALYTICS
        layer: module
        current_state: implemented
        implemented_now:
          - get_risk_summary
        missing_for_mvp:
          - none
        missing_prds: []
        needs_new_prd_version: false
        next_version_reason: ""
        next_slice: decide whether live integration is in MVP
      - component_ref: WALKER-QUANT
        layer: walker
        current_state: delegate_only
        implemented_now:
          - summarize_change delegate
        missing_for_mvp:
          - interpretive output
        missing_prds: []
        needs_new_prd_version: true
        next_version_reason: Current PRD is delegation-only.
        next_slice: Author PRD-4.2-v2.
    prd_lineage:
      - capability: Quant Walker
        active_prd: PRD-4.2-v1
        status: active
        supersedes: ""
        next_needed_prd: PRD-4.2-v2
        why: v1 is delegation-only.
    in_progress_items: []
    next_recommended_slices:
      - Author PRD-4.2-v2
    post_mvp_enhancements:
      - Critic / Challenge Walker
    open_questions:
      - Is live-data integration in MVP?
    change_log:
      - "2026-04-19: Initial dashboard seed."

components:
  modules:
    - id: MOD-RISK-ANALYTICS
      name: Risk Analytics
      status: implemented
      contract_status: implemented
  walkers:
    - id: WALKER-QUANT
      name: Quant Walker
      status: implemented
      contract_status: implemented
  orchestrators: []
""".strip()
        + "\n",
        encoding="utf-8",
    )
    return registry_path
