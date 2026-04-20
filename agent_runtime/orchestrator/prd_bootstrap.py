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
    registry_path = repo_root / REGISTRY_PATH
    if not registry_path.is_file():
        return ()

    candidates: list[PrdBootstrapCandidate] = []
    for capability in _load_registry_capabilities(registry_path):
        if not _is_actionable_prd_gap(capability):
            continue

        next_slice = str(capability.get("next_slice") or "").strip()
        next_version_reason = str(capability.get("next_version_reason") or "").strip()
        missing_prds = _coerce_string_tuple(capability.get("missing_prds"))
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


def _load_registry_capabilities(registry_path: Path) -> tuple[dict[str, object], ...]:
    lines = registry_path.read_text(encoding="utf-8").splitlines()
    capabilities: list[dict[str, object]] = []
    in_capabilities = False
    current: dict[str, object] | None = None
    collecting_missing_prds = False

    def finalize_current() -> None:
        nonlocal current, collecting_missing_prds
        if current is not None:
            capabilities.append(current)
        current = None
        collecting_missing_prds = False

    for raw_line in lines:
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" "))

        if stripped == "capabilities:":
            finalize_current()
            in_capabilities = True
            continue

        if not in_capabilities:
            continue

        if indent <= 2 and stripped.endswith(":") and stripped != "capabilities:":
            finalize_current()
            in_capabilities = False
            continue

        if indent == 6 and stripped.startswith("- "):
            finalize_current()
            current = {}
            collecting_missing_prds = False
            _parse_capability_entry(current, stripped[2:])
            continue

        if current is None:
            continue

        if collecting_missing_prds:
            if indent >= 8 and stripped.startswith("- "):
                missing_prds = current.setdefault("missing_prds", [])
                assert isinstance(missing_prds, list)
                missing_prds.append(stripped[2:].strip())
                continue
            collecting_missing_prds = False

        if indent >= 8:
            key, _, value = stripped.partition(":")
            if not _:
                continue
            key = key.strip()
            value = value.strip()
            if key == "missing_prds":
                if value.startswith("[") and value.endswith("]"):
                    current["missing_prds"] = _parse_inline_list(value)
                else:
                    current["missing_prds"] = []
                    collecting_missing_prds = True
                continue
            current[key] = _parse_scalar(value)

    finalize_current()
    return tuple(capabilities)


def _parse_capability_entry(current: dict[str, object], entry: str) -> None:
    key, _, value = entry.partition(":")
    if not _:
        return
    current[key.strip()] = _parse_scalar(value.strip())


def _parse_inline_list(value: str) -> list[str]:
    inner = value[1:-1].strip()
    if not inner:
        return []
    return [item.strip().strip("'\"") for item in inner.split(",") if item.strip()]


def _parse_scalar(value: str) -> object:
    if value in {"true", "True"}:
        return True
    if value in {"false", "False"}:
        return False
    if value in {"[]", ""}:
        return []
    return value.strip().strip("'\"")


def _coerce_string_tuple(value: object) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(str(item).strip() for item in value if str(item).strip())


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
