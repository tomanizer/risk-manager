"""Registry-driven PRD/spec bootstrap candidates for empty-backlog routing."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re


REGISTRY_PATH = Path("docs/registry/current_state_registry.yaml")
_AUTHOR_PRD_PATTERN = re.compile(r"\bauthor\b.*\bprd\b", re.IGNORECASE)
_POST_MVP_PATTERN = re.compile(r"\bpost-mvp\b", re.IGNORECASE)
_PRD_ID_PATTERN = re.compile(r"\b(PRD-[A-Za-z0-9.\-]+)\b")
_PRD_ID_HEADER_PATTERN = re.compile(r"^\s*-\s+\*\*PRD ID:\*\*\s+(PRD-[A-Za-z0-9.\-]+)\s*$", re.MULTILINE)


@dataclass(frozen=True, slots=True)
class PrdBootstrapCandidate:
    capability_name: str
    target_prd_id: str | None
    existing_prd_path: str | None
    registry_path: str
    next_slice: str
    next_version_reason: str


def load_prd_bootstrap_candidates(repo_root: Path) -> tuple[PrdBootstrapCandidate, ...]:
    """Return actionable PRD/spec bootstrap candidates from the registry.

    The runtime should only bootstrap into PRD/spec work when the registry says a
    new PRD or PRD version is needed *now* rather than in a post-MVP phase. This
    keeps empty-backlog routing deterministic and governed.
    """
    try:
        import yaml
    except ImportError:
        return ()

    registry_path = repo_root / REGISTRY_PATH
    if not registry_path.is_file():
        return ()

    payload = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return ()

    candidates: list[PrdBootstrapCandidate] = []
    for dashboard in payload.get("module_dashboards", ()):
        if not isinstance(dashboard, dict):
            continue
        for capability in dashboard.get("capabilities", ()):
            if not isinstance(capability, dict):
                continue
            if not _is_actionable_prd_gap(capability):
                continue

            next_slice = str(capability.get("next_slice") or "").strip()
            next_version_reason = str(capability.get("next_version_reason") or "").strip()
            missing_prds = tuple(str(item).strip() for item in capability.get("missing_prds", ()) if str(item).strip())
            target_prd_id = _extract_target_prd_id(next_slice, missing_prds)
            existing_prd_id = _extract_existing_prd_id(next_version_reason, target_prd_id)
            existing_prd_path = _find_prd_path_by_id(repo_root, existing_prd_id) if existing_prd_id is not None else None
            capability_name = str(capability.get("name") or capability.get("component_ref") or "unknown capability")
            candidates.append(
                PrdBootstrapCandidate(
                    capability_name=capability_name,
                    target_prd_id=target_prd_id,
                    existing_prd_path=existing_prd_path,
                    registry_path=REGISTRY_PATH.as_posix(),
                    next_slice=next_slice,
                    next_version_reason=next_version_reason,
                )
            )

    return tuple(candidates)


def _is_actionable_prd_gap(capability: dict[str, object]) -> bool:
    missing_prds = capability.get("missing_prds")
    needs_new_prd_version = bool(capability.get("needs_new_prd_version"))
    if not needs_new_prd_version and not missing_prds:
        return False

    next_slice = str(capability.get("next_slice") or "").strip()
    next_version_reason = str(capability.get("next_version_reason") or "").strip()
    if not _AUTHOR_PRD_PATTERN.search(next_slice):
        return False
    if _POST_MVP_PATTERN.search(next_slice) or _POST_MVP_PATTERN.search(next_version_reason):
        return False
    return True


def _extract_target_prd_id(next_slice: str, missing_prds: tuple[str, ...]) -> str | None:
    for missing_prd in missing_prds:
        match = _PRD_ID_PATTERN.search(missing_prd)
        if match is not None:
            return match.group(1)
    match = _PRD_ID_PATTERN.search(next_slice)
    if match is None:
        return None
    return match.group(1)


def _extract_existing_prd_id(next_version_reason: str, target_prd_id: str | None) -> str | None:
    for match in _PRD_ID_PATTERN.finditer(next_version_reason):
        prd_id = match.group(1)
        if prd_id != target_prd_id:
            return prd_id
    return None


def _find_prd_path_by_id(repo_root: Path, prd_id: str | None) -> str | None:
    if not prd_id:
        return None
    docs_root = repo_root / "docs" / "prds"
    if not docs_root.is_dir():
        return None
    for full_path in sorted(docs_root.rglob("*.md")):
        contents = full_path.read_text(encoding="utf-8")
        match = _PRD_ID_HEADER_PATTERN.search(contents)
        if match is None:
            continue
        if match.group(1) == prd_id:
            return full_path.relative_to(repo_root).as_posix()
    return None
