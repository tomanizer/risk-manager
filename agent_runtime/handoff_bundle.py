"""Shared governed handoff-bundle contract for manual and runtime surfaces."""

from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass
import json
from pathlib import Path
import re
from typing import Mapping, cast

from agent_runtime.orchestrator.state import PullRequestSnapshot

_SECTION_RE = re.compile(r"^##\s+(.+)$", re.MULTILINE)
_PRD_REF_RE = re.compile(r"\b(PRD-[\d.]+)(?:-.+?)?(?:-v(\d+))?\b", re.IGNORECASE)
_ADR_REF_RE = re.compile(r"\bADR-\d+\b")
_DOC_PATH_RE = re.compile(r"(?P<path>docs/[^\s)`]+\.md)")


def _canonical_heading(heading: str) -> str:
    stripped = heading.strip().lstrip("#").strip()
    stripped = re.sub(r"\s+\([^)]*\)$", "", stripped)
    return re.sub(r"\s+", " ", stripped).lower()


def _split_sections(text: str) -> dict[str, str]:
    headings = [(match.start(), _canonical_heading(match.group(1))) for match in _SECTION_RE.finditer(text)]
    sections: dict[str, str] = {}
    for index, (start, heading) in enumerate(headings):
        end = headings[index + 1][0] if index + 1 < len(headings) else len(text)
        body_start = text.find("\n", start)
        if body_start == -1:
            sections[heading] = ""
            continue
        sections[heading] = text[body_start + 1 : end].strip()
    return sections


def _extract_title(text: str, fallback: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
    return fallback


def _is_none_text(value: str | None) -> bool:
    if value is None:
        return True
    normalized = value.strip().lower()
    return normalized in {"", "none", "none required.", "none required", "n/a", "not applicable"}


def _repo_relative(path: Path, repo_root: Path) -> str:
    try:
        return path.relative_to(repo_root).as_posix()
    except ValueError:
        return path.as_posix()


def _normalize_reference_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _extract_doc_path(text: str | None) -> str | None:
    if text is None:
        return None
    match = _DOC_PATH_RE.search(text)
    return match.group("path") if match else None


def _find_repo_root(work_item_path: Path, repo_root: Path | None) -> Path:
    if repo_root is not None:
        return repo_root.resolve()
    candidate = work_item_path.resolve()
    search_roots = (candidate.parent,) + tuple(candidate.parents)
    for root in search_roots:
        if (root / "work_items").exists() and (root / "docs").exists():
            return root
    for root in search_roots:
        if root.name == "work_items":
            return root.parent
    return candidate.parent


def _resolve_prd_path(reference_text: str | None, repo_root: Path) -> str | None:
    if _is_none_text(reference_text):
        return None
    assert reference_text is not None

    extracted_path = _extract_doc_path(reference_text)
    if extracted_path is not None:
        candidate = repo_root / extracted_path
        if candidate.exists():
            return extracted_path

    docs_dir = repo_root / "docs"
    first_line = next((line.strip().strip("`") for line in reference_text.splitlines() if line.strip()), "")
    if first_line and not any(char in first_line for char in "*?[]"):
        candidates = sorted(docs_dir.rglob(f"*{first_line}*.md"))
        if candidates:
            return _repo_relative(candidates[0], repo_root)

    match = _PRD_REF_RE.search(first_line)
    if not match:
        return None
    base_part = match.group(1)
    version = match.group(2)
    if version:
        candidates = sorted(docs_dir.rglob(f"*{base_part}*-v{version}*.md"))
        if candidates:
            return _repo_relative(candidates[0], repo_root)
    candidates = sorted(docs_dir.rglob(f"*{base_part}*.md"))
    if candidates:
        return _repo_relative(candidates[0], repo_root)
    return None


def _extract_adr_reference_texts(section_text: str | None) -> tuple[str, ...]:
    if _is_none_text(section_text):
        return ()
    assert section_text is not None

    references: list[str] = []
    for line in section_text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("- "):
            references.append(stripped[2:].strip())
    if references:
        return tuple(dict.fromkeys(references))

    discovered = tuple(dict.fromkeys(_ADR_REF_RE.findall(section_text)))
    return discovered


def _resolve_adr_path(reference_text: str, repo_root: Path) -> str | None:
    extracted_path = _extract_doc_path(reference_text)
    if extracted_path is not None:
        candidate = repo_root / extracted_path
        if candidate.exists():
            return extracted_path

    adr_ref = next(iter(_ADR_REF_RE.findall(reference_text)), None)
    if adr_ref is None:
        return None
    candidates = sorted((repo_root / "docs" / "adr").rglob(f"*{adr_ref}*.md"))
    if not candidates:
        return None
    return _repo_relative(candidates[0], repo_root)


def _parse_optional_bool(value: str | None) -> bool | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    if normalized in {"true", "1", "yes"}:
        return True
    if normalized in {"false", "0", "no"}:
        return False
    return None


def _coerce_work_item_path(work_item_path: str | Path, repo_root: Path | None) -> Path:
    path = Path(work_item_path)
    if path.is_absolute():
        return path
    if repo_root is not None:
        return repo_root / path
    return path.resolve()


@dataclass(frozen=True)
class HandoffDocumentReference:
    reference_text: str
    resolved_path: str | None = None


@dataclass(frozen=True)
class HandoffCheckoutContext:
    base_ref: str | None = None
    checkout_ref: str | None = None
    checkout_detached: bool | None = None
    branch_name: str | None = None
    branch_owned_by_runtime: bool | None = None
    pr_head_branch: str | None = None
    worktree_path: str | None = None
    run_id: str | None = None


@dataclass(frozen=True)
class HandoffPullRequestContext:
    number: int
    is_draft: bool
    url: str | None = None
    head_ref_name: str | None = None
    base_ref_name: str | None = None
    updated_at: str | None = None
    unresolved_review_threads: int | None = None
    has_new_review_comments: bool | None = None
    review_decision: str | None = None
    merge_state_status: str | None = None
    ci_status: str | None = None


@dataclass(frozen=True)
class HandoffSourceProvenance:
    builder_name: str
    repo_root: str
    work_item_path: str
    work_item_stage: str | None = None
    runtime_metadata_keys: tuple[str, ...] = ()
    pull_request_source: str | None = None


@dataclass(frozen=True)
class HandoffBundle:
    role: str
    work_item_id: str
    work_item_title: str
    work_item_path: str
    checkout_context: HandoffCheckoutContext
    linked_prd: HandoffDocumentReference | None
    linked_adrs: tuple[HandoffDocumentReference, ...]
    dependencies: str
    scope: str
    target_area: str
    out_of_scope: str
    acceptance_criteria: str
    stop_conditions: str | None
    pr_context: HandoffPullRequestContext | None
    source_provenance: HandoffSourceProvenance

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True) + "\n"

    def render_markdown(self) -> str:
        lines = [
            "# Agent Handoff Bundle",
            "",
            f"- role: `{self.role}`",
            f"- work_item_id: `{self.work_item_id}`",
            f"- work_item_title: `{self.work_item_title}`",
            f"- work_item_path: `{self.work_item_path}`",
            "",
            "## Checkout Context",
        ]
        lines.extend(_render_key_value_list(self.checkout_context))
        lines.extend(["", "## Linked PRD"])
        if self.linked_prd is None:
            lines.append("- none")
        else:
            lines.extend(_render_document_reference(self.linked_prd))
        lines.extend(["", "## Linked ADRs"])
        if not self.linked_adrs:
            lines.append("- none")
        else:
            for item in self.linked_adrs:
                lines.extend(_render_document_reference(item))
        lines.extend(
            [
                "",
                "## Dependencies",
                self.dependencies or "<none>",
                "",
                "## Scope",
                self.scope or "<none>",
                "",
                "## Target Area",
                self.target_area or "<none>",
                "",
                "## Out Of Scope",
                self.out_of_scope or "<none>",
                "",
                "## Acceptance Criteria",
                self.acceptance_criteria or "<none>",
                "",
                "## Stop Conditions",
                self.stop_conditions or "<none>",
                "",
                "## PR Context",
            ]
        )
        if self.pr_context is None:
            lines.append("- none")
        else:
            lines.extend(_render_key_value_list(self.pr_context))
        lines.extend(["", "## Source Provenance"])
        lines.extend(_render_key_value_list(self.source_provenance))
        return "\n".join(lines).rstrip() + "\n"


def _render_document_reference(reference: HandoffDocumentReference) -> list[str]:
    lines = ["- reference_text:"]
    lines.extend(_render_multiline_list_value(reference.reference_text))
    if reference.resolved_path is not None:
        lines.append(f"  - resolved_path: `{reference.resolved_path}`")
    else:
        lines.append("  - resolved_path: <unresolved>")
    return lines


def _render_multiline_list_value(value: str, *, indent: str = "  ") -> list[str]:
    rendered_lines = value.splitlines() or [""]
    return [f"{indent}{line}" if line else indent for line in rendered_lines]


def _render_key_value_list(
    value: Mapping[str, object] | HandoffCheckoutContext | HandoffPullRequestContext | HandoffSourceProvenance,
) -> list[str]:
    if isinstance(value, Mapping):
        payload = dict(value)
    elif is_dataclass(value):
        payload = cast(dict[str, object], asdict(value))
    else:
        raise TypeError(f"Expected dataclass or dict for markdown rendering, got {type(value)!r}")
    lines: list[str] = []
    for key, raw_value in payload.items():
        if isinstance(raw_value, (list, tuple)):
            rendered = ", ".join(f"`{item}`" for item in raw_value) if raw_value else "<none>"
        elif raw_value is None:
            rendered = "<none>"
        elif isinstance(raw_value, bool):
            rendered = "true" if raw_value else "false"
        else:
            rendered = f"`{raw_value}`"
        lines.append(f"- {key}: {rendered}")
    return lines


def build_handoff_bundle(
    *,
    role: str,
    work_item_path: str | Path,
    runtime_metadata: Mapping[str, str] | None = None,
    pull_request: PullRequestSnapshot | None = None,
    repo_root: Path | None = None,
) -> HandoffBundle:
    """Build a typed, serializable handoff bundle from a live work item."""

    runtime_metadata = dict(runtime_metadata or {})
    resolved_work_item_path = _coerce_work_item_path(work_item_path, repo_root)
    repo_root_path = _find_repo_root(resolved_work_item_path, repo_root)
    text = resolved_work_item_path.read_text(encoding="utf-8")
    sections = _split_sections(text)
    work_item_stage = resolved_work_item_path.parent.name if resolved_work_item_path.parent.name != "work_items" else None

    linked_prd_text = _normalize_reference_text(sections.get("linked prd"))
    linked_prd = None
    if not _is_none_text(linked_prd_text):
        assert linked_prd_text is not None
        linked_prd = HandoffDocumentReference(
            reference_text=linked_prd_text,
            resolved_path=_resolve_prd_path(linked_prd_text, repo_root_path),
        )

    linked_adrs = tuple(
        HandoffDocumentReference(
            reference_text=reference_text,
            resolved_path=_resolve_adr_path(reference_text, repo_root_path),
        )
        for reference_text in _extract_adr_reference_texts(sections.get("linked adrs"))
    )

    pr_context = None
    if pull_request is not None:
        pr_context = HandoffPullRequestContext(
            number=pull_request.number,
            is_draft=pull_request.is_draft,
            url=pull_request.url,
            head_ref_name=pull_request.head_ref_name,
            base_ref_name=pull_request.base_ref_name,
            updated_at=pull_request.updated_at,
            unresolved_review_threads=pull_request.unresolved_review_threads,
            has_new_review_comments=pull_request.has_new_review_comments,
            review_decision=pull_request.review_decision,
            merge_state_status=pull_request.merge_state_status,
            ci_status=pull_request.ci_status,
        )

    stop_conditions = _normalize_reference_text(sections.get("stop conditions"))

    return HandoffBundle(
        role=role,
        work_item_id=resolved_work_item_path.stem,
        work_item_title=_extract_title(text, resolved_work_item_path.stem),
        work_item_path=_repo_relative(resolved_work_item_path, repo_root_path),
        checkout_context=HandoffCheckoutContext(
            base_ref=runtime_metadata.get("base_ref"),
            checkout_ref=runtime_metadata.get("checkout_ref"),
            checkout_detached=_parse_optional_bool(runtime_metadata.get("checkout_detached")),
            branch_name=runtime_metadata.get("branch_name"),
            branch_owned_by_runtime=_parse_optional_bool(runtime_metadata.get("branch_owned_by_runtime")),
            pr_head_branch=runtime_metadata.get("pr_head_branch"),
            worktree_path=runtime_metadata.get("worktree_path"),
            run_id=runtime_metadata.get("run_id"),
        ),
        linked_prd=linked_prd,
        linked_adrs=linked_adrs,
        dependencies=sections.get("dependencies", ""),
        scope=sections.get("scope", ""),
        target_area=sections.get("target area", ""),
        out_of_scope=sections.get("out of scope", ""),
        acceptance_criteria=sections.get("acceptance criteria", ""),
        stop_conditions=stop_conditions,
        pr_context=pr_context,
        source_provenance=HandoffSourceProvenance(
            builder_name="agent_runtime.handoff_bundle.build_handoff_bundle",
            repo_root=repo_root_path.as_posix(),
            work_item_path=_repo_relative(resolved_work_item_path, repo_root_path),
            work_item_stage=work_item_stage,
            runtime_metadata_keys=tuple(sorted(runtime_metadata.keys())),
            pull_request_source="PullRequestSnapshot" if pull_request is not None else None,
        ),
    )
