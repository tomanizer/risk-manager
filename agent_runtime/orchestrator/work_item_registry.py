"""Filesystem-backed work-item discovery for the runtime."""

from __future__ import annotations

from pathlib import Path

from .state import WorkItemSnapshot, WorkItemStage


def _normalize_heading(heading: str) -> str:
    return heading.strip().lstrip("#").strip()


def _extract_section_lines(text: str, heading: str) -> list[str]:
    lines = text.splitlines()
    in_section = False
    collected: list[str] = []
    for line in lines:
        normalized_line = _normalize_heading(line)
        if normalized_line == _normalize_heading(heading):
            in_section = True
            continue
        if in_section and line.strip().startswith("#"):
            break
        if in_section:
            collected.append(line)
    return collected


def _extract_title(text: str, fallback: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
    return fallback


def _extract_linked_prd(text: str) -> str | None:
    for line in _extract_section_lines(text, "## Linked PRD"):
        stripped = line.strip()
        if stripped:
            return stripped
    return None


def _extract_dependencies(text: str) -> tuple[str, ...]:
    dependencies: list[str] = []
    for line in _extract_section_lines(text, "## Dependencies"):
        stripped = line.strip()
        if stripped.startswith("- "):
            dependencies.append(stripped[2:].strip())
    return tuple(dependencies)


def _snapshot_from_file(path: Path, stage: WorkItemStage) -> WorkItemSnapshot:
    text = path.read_text(encoding="utf-8")
    return WorkItemSnapshot(
        id=path.stem,
        title=_extract_title(text, path.stem),
        path=path,
        stage=stage,
        linked_prd=_extract_linked_prd(text),
        dependencies=_extract_dependencies(text),
    )


def load_work_items(repo_root: Path) -> tuple[tuple[WorkItemSnapshot, ...], tuple[str, ...]]:
    stage_dirs = (
        ("work_items/ready", WorkItemStage.READY),
        ("work_items/in_progress", WorkItemStage.IN_PROGRESS),
        ("work_items/blocked", WorkItemStage.BLOCKED),
        ("work_items/done", WorkItemStage.DONE),
    )
    snapshots: list[WorkItemSnapshot] = []
    warnings: list[str] = []
    for relative_dir, stage in stage_dirs:
        base_dir = repo_root / relative_dir
        if not base_dir.exists():
            continue
        for path in sorted(base_dir.glob("WI-*.md")):
            try:
                snapshots.append(_snapshot_from_file(path, stage))
            except (OSError, UnicodeDecodeError) as exc:
                warnings.append(f"skipped unreadable work item {path}: {exc}")
    return tuple(snapshots), tuple(warnings)
