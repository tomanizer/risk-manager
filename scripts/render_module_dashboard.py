#!/usr/bin/env python3
"""Render human-readable module dashboard pages from the registry."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import yaml


DEFAULT_REGISTRY_PATH = Path("docs/registry/current_state_registry.yaml")


def find_repo_root(start: Path) -> Path:
    candidate = start if start.is_dir() else start.parent
    for path in (candidate, *candidate.parents):
        if (path / "AGENTS.md").exists() and (path / "docs").is_dir():
            return path
    raise RuntimeError("Could not find repository root.")


def load_registry(registry_path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("registry payload must be a mapping")
    return payload


def build_component_index(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    components = payload.get("components", {})
    if not isinstance(components, dict):
        raise ValueError("registry `components` must be a mapping")
    out: dict[str, dict[str, Any]] = {}
    for section_name in ("modules", "walkers", "orchestrators"):
        entries = components.get(section_name, [])
        if not isinstance(entries, list):
            raise ValueError(f"registry `components.{section_name}` must be a list")
        for entry in entries:
            if not isinstance(entry, dict):
                raise ValueError(f"registry `components.{section_name}` entries must be mappings")
            component_id = entry.get("id")
            if isinstance(component_id, str) and component_id:
                out[component_id] = entry
    return out


def render_module_dashboard(payload: dict[str, Any], *, module_id: str) -> str:
    module_dashboards = payload.get("module_dashboards", [])
    if not isinstance(module_dashboards, list):
        raise ValueError("registry `module_dashboards` must be a list")

    dashboard_entry = next(
        (entry for entry in module_dashboards if isinstance(entry, dict) and entry.get("id") == module_id),
        None,
    )
    if dashboard_entry is None:
        raise KeyError(f"module dashboard `{module_id}` not found in registry")

    component_index = build_component_index(payload)
    lines: list[str] = [
        "<!-- GENERATED FILE: edit docs/registry/current_state_registry.yaml and rerun scripts/render_module_dashboard.py -->",
        "",
        f"# {dashboard_entry['name']}",
        "",
        f"_Last updated: {payload.get('last_updated', 'unknown')}_  ",
        f"_Source of truth: `{DEFAULT_REGISTRY_PATH.as_posix()}`_  ",
        f"_Owner: {dashboard_entry.get('owner_role', 'PM')}_",
        "",
        "## Mission",
        "",
        str(dashboard_entry.get("mission", "")).strip(),
        "",
        "## MVP Definition",
        "",
    ]
    lines.extend(_render_bullets(_string_list(dashboard_entry.get("mvp_definition"))))
    lines.extend(
        [
            "",
            "## Current Overall Status",
            "",
            f"- Overall state: `{dashboard_entry.get('overall_state', 'unknown')}`",
            f"- Delivery phase: `{dashboard_entry.get('delivery_phase', 'unknown')}`",
            f"- Summary: {_normalize_text(dashboard_entry.get('summary'))}",
            "- Current MVP blockers:",
        ]
    )
    lines.extend(_render_indented_bullets(_string_list(dashboard_entry.get("current_mvp_blockers")), empty_text="none recorded"))
    lines.extend(
        [
            "",
            "## Journey Status",
            "",
            "| Stage | Goal | Status | Notes |",
            "| --- | --- | --- | --- |",
        ]
    )
    for stage in _mapping_list(dashboard_entry.get("journey_stages")):
        lines.append(
            f"| {_escape_markdown_table_text(stage.get('label'))} | {_normalize_text(stage.get('goal'))} | "
            f"`{stage.get('status', 'unknown')}` | {_normalize_text(stage.get('notes'))} |"
        )

    lines.extend(
        [
            "",
            "## Capability Status",
            "",
            "| Capability | Layer | Current State | Implemented Now | Missing For MVP | Missing PRD | Needs New PRD Version? | Reason | Next Slice |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for capability in _mapping_list(dashboard_entry.get("capabilities")):
        component_ref = str(capability.get("component_ref", ""))
        component = component_index.get(component_ref, {})
        capability_name = str(component.get("name") or capability.get("name") or component_ref)
        lines.append(
            f"| {_escape_markdown_table_text(capability_name)} | {_escape_markdown_table_text(capability.get('layer'))} | "
            f"`{capability.get('current_state', 'unknown')}` | "
            f"{_render_table_list(_string_list(capability.get('implemented_now')))} | "
            f"{_render_table_list(_string_list(capability.get('missing_for_mvp')))} | "
            f"{_render_table_list(_string_list(capability.get('missing_prds')))} | "
            f"`{'yes' if capability.get('needs_new_prd_version') else 'no'}` | "
            f"{_normalize_text(capability.get('next_version_reason'))} | "
            f"{_normalize_text(capability.get('next_slice'))} |"
        )

    lines.extend(
        [
            "",
            "## MVP Gap Summary",
            "",
            "The following items are still required to declare Module 1 MVP complete:",
            "",
        ]
    )
    lines.extend(_render_bullets(_string_list(dashboard_entry.get("current_mvp_blockers"))))
    lines.extend(
        [
            "",
            "The following items are explicitly not required for Module 1 MVP:",
            "",
        ]
    )
    lines.extend(_render_bullets(_string_list(dashboard_entry.get("not_required_for_mvp"))))
    lines.extend(
        [
            "",
            "## PRD Lineage",
            "",
            "| Capability | Active PRD | Status | Supersedes | Next Needed PRD | Why |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    for lineage in _mapping_list(dashboard_entry.get("prd_lineage")):
        lines.append(
            f"| {_escape_markdown_table_text(lineage.get('capability'))} | {_normalize_text(lineage.get('active_prd'))} | "
            f"`{lineage.get('status', 'unknown')}` | {_normalize_text(lineage.get('supersedes'))} | "
            f"{_normalize_text(lineage.get('next_needed_prd'))} | {_normalize_text(lineage.get('why'))} |"
        )

    lines.extend(["", "## In Progress", ""])
    in_progress_items = _mapping_list(dashboard_entry.get("in_progress_items"))
    if in_progress_items:
        lines.extend(
            [
                "| Item | Type | Status | Owner | Blocking? | Notes |",
                "| --- | --- | --- | --- | --- | --- |",
            ]
        )
        for item in in_progress_items:
            lines.append(
                f"| {_escape_markdown_table_text(item.get('id'))} | `{item.get('type', '')}` | `{item.get('status', '')}` | "
                f"{_escape_markdown_table_text(item.get('owner'))} | `{'yes' if item.get('blocking') else 'no'}` | {_normalize_text(item.get('notes'))} |"
            )
    else:
        lines.append("None recorded.")

    lines.extend(["", "## Next Recommended Slices", ""])
    lines.extend(_render_numbered(_string_list(dashboard_entry.get("next_recommended_slices"))))
    lines.extend(["", "## Post-MVP Enhancements", ""])
    lines.extend(_render_bullets(_string_list(dashboard_entry.get("post_mvp_enhancements"))))
    lines.extend(["", "## Open Questions", ""])
    open_questions = _string_list(dashboard_entry.get("open_questions"))
    lines.extend(_render_bullets(open_questions) if open_questions else ["None — all open questions have been closed."])

    closed_decisions = _mapping_list(dashboard_entry.get("closed_decisions"))
    if closed_decisions:
        lines.extend(["", "## Closed Decisions", ""])
        for decision in closed_decisions:
            lines.append(f"### {decision.get('id', 'DECISION')} — {decision.get('date', '')}")
            lines.append("")
            lines.append(f"**Question:** {_normalize_text(decision.get('question'))}")
            lines.append("")
            lines.append(f"**Decision:** {_normalize_text(decision.get('decision'))}")
            lines.append("")
            lines.append(f"**Rationale:** {_normalize_text(decision.get('rationale'))}")
            note = decision.get("note")
            if note:
                lines.append("")
                lines.append(f"**Note:** {_normalize_text(note)}")
            lines.append("")

    lines.extend(["## Change Log", ""])
    lines.extend(_render_bullets(_string_list(dashboard_entry.get("change_log"))))
    lines.append("")
    return "\n".join(lines)


def render_dashboards(
    payload: dict[str, Any],
    *,
    repo_root: Path,
    module_id: str | None = None,
) -> tuple[Path, ...]:
    module_dashboards = payload.get("module_dashboards", [])
    if not isinstance(module_dashboards, list):
        raise ValueError("registry `module_dashboards` must be a list")

    targets = [entry for entry in module_dashboards if isinstance(entry, dict)]
    if module_id is not None:
        targets = [entry for entry in targets if entry.get("id") == module_id]
        if not targets:
            raise KeyError(f"module dashboard `{module_id}` not found in registry")

    written_paths: list[Path] = []
    for entry in targets:
        output_rel = entry.get("dashboard_path")
        if not isinstance(output_rel, str) or not output_rel:
            raise ValueError("module dashboard entries must declare a non-empty `dashboard_path`")
        output_path = repo_root / output_rel
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(render_module_dashboard(payload, module_id=str(entry["id"])), encoding="utf-8")
        written_paths.append(output_path)
    return tuple(written_paths)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render module dashboard pages from the current-state registry.")
    parser.add_argument("--root", default=None, help="Repository root. Defaults to auto-detected root from the current working directory.")
    parser.add_argument("--registry", default=str(DEFAULT_REGISTRY_PATH), help="Registry path relative to repo root.")
    parser.add_argument("--module-id", default=None, help="Render only one module dashboard id.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path(args.root).resolve() if args.root else find_repo_root(Path.cwd())
    registry_path = repo_root / args.registry
    payload = load_registry(registry_path)
    written_paths = render_dashboards(payload, repo_root=repo_root, module_id=args.module_id)
    for path in written_paths:
        print(path.relative_to(repo_root).as_posix())
    return 0


def _mapping_list(value: Any) -> list[dict[str, Any]]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError("expected a list of mappings")
    out: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, dict):
            raise ValueError("expected a list of mappings")
        out.append(item)
    return out


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError("expected a list of strings")
    out: list[str] = []
    for item in value:
        text = _escape_markdown_table_text(item)
        if text:
            out.append(text)
    return out


def _normalize_text(value: Any) -> str:
    text = _escape_markdown_table_text(value)
    return text or "none"


def _escape_markdown_table_text(value: Any) -> str:
    text = str(value).strip() if value is not None else ""
    return text.replace("|", "\\|")


def _render_table_list(items: list[str]) -> str:
    return "<br>".join(items) if items else "none"


def _render_bullets(items: list[str]) -> list[str]:
    if not items:
        return ["- none"]
    return [f"- {item}" for item in items]


def _render_indented_bullets(items: list[str], *, empty_text: str) -> list[str]:
    if not items:
        return [f"  - {empty_text}"]
    return [f"  - {item}" for item in items]


def _render_numbered(items: list[str]) -> list[str]:
    if not items:
        return ["1. none"]
    return [f"{index}. {item}" for index, item in enumerate(items, start=1)]


if __name__ == "__main__":
    raise SystemExit(main())
