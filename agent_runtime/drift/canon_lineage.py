from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
import re


VERSIONED_DOC_PATTERN = re.compile(r"^(?P<base>.+)-v(?P<version>\d+)(?P<archived>-archived)?$", re.IGNORECASE)
SUPERCEDES_PATTERN = re.compile(r"^\s*-\s+\*\*Supersedes:\*\*\s+`([^`\n]+\.md)`", re.IGNORECASE | re.MULTILINE)
MARKDOWN_DOC_REF_PATTERN = re.compile(r"`([^`\n]+\.md)`")
EXECUTION_SURFACE_ROOTS: tuple[Path, ...] = (
    Path("docs/implementation"),
    Path("work_items"),
    Path("prompts"),
    Path(".github/agents"),
)


@dataclass(frozen=True, slots=True)
class CanonLineageFinding:
    kind: str
    severity: str
    drift_class: str
    owner: str
    source_path: str
    related_paths: tuple[str, ...]
    message: str


@dataclass(frozen=True, slots=True)
class CanonLineageStats:
    versioned_docs_scanned: int
    lineage_groups_scanned: int
    execution_surfaces_scanned: int
    findings_count: int


@dataclass(frozen=True, slots=True)
class CanonLineageReport:
    scan_name: str
    root: str
    generated_at: str
    findings: tuple[CanonLineageFinding, ...]
    stats: CanonLineageStats

    def to_dict(self) -> dict[str, object]:
        return {
            "scan_name": self.scan_name,
            "root": self.root,
            "generated_at": self.generated_at,
            "findings": [asdict(finding) for finding in self.findings],
            "stats": asdict(self.stats),
        }


@dataclass(frozen=True, slots=True)
class _VersionedDoc:
    path: Path
    family_key: str
    version: int
    archived: bool


def build_canon_lineage_report(root: Path) -> CanonLineageReport:
    repo_root = root.resolve()
    versioned_docs = _discover_versioned_docs(repo_root)
    findings: list[CanonLineageFinding] = []

    _append_lineage_group_findings(findings, repo_root, versioned_docs)
    execution_surfaces_scanned = _append_archived_reference_findings(findings, repo_root)

    findings.sort(key=lambda finding: (finding.source_path, finding.kind, finding.related_paths))
    return CanonLineageReport(
        scan_name="canon_lineage",
        root=".",
        generated_at=datetime.now(UTC).isoformat(),
        findings=tuple(findings),
        stats=CanonLineageStats(
            versioned_docs_scanned=len(versioned_docs),
            lineage_groups_scanned=len({doc.family_key for doc in versioned_docs}),
            execution_surfaces_scanned=execution_surfaces_scanned,
            findings_count=len(findings),
        ),
    )


def _discover_versioned_docs(repo_root: Path) -> tuple[_VersionedDoc, ...]:
    versioned_docs: list[_VersionedDoc] = []
    for full_path in sorted((repo_root / "docs").rglob("*.md")):
        rel_path = full_path.relative_to(repo_root)
        match = VERSIONED_DOC_PATTERN.match(full_path.stem)
        if match is None:
            continue
        archived = _is_archived_versioned_doc(rel_path)
        lineage_dir = rel_path.parent.parent if rel_path.parent.name == "archive" else rel_path.parent
        family_key = f"{lineage_dir.as_posix()}::{match.group('base')}"
        versioned_docs.append(
            _VersionedDoc(
                path=rel_path,
                family_key=family_key,
                version=int(match.group("version")),
                archived=archived,
            )
        )
    return tuple(versioned_docs)


def _append_lineage_group_findings(findings: list[CanonLineageFinding], repo_root: Path, versioned_docs: tuple[_VersionedDoc, ...]) -> None:
    docs_by_group: dict[str, list[_VersionedDoc]] = {}
    for doc in versioned_docs:
        docs_by_group.setdefault(doc.family_key, []).append(doc)

    for group_docs in docs_by_group.values():
        active_docs = sorted((doc for doc in group_docs if not doc.archived), key=lambda doc: doc.version)
        archived_by_version = {doc.version: doc for doc in group_docs if doc.archived}
        active_by_version = {doc.version: doc for doc in active_docs}

        if len(active_docs) > 1:
            findings.append(
                CanonLineageFinding(
                    kind="multiple_active_versions",
                    severity="critical",
                    drift_class="canon drift",
                    owner=_lineage_owner(active_docs[-1].path),
                    source_path=active_docs[-1].path.as_posix(),
                    related_paths=tuple(doc.path.as_posix() for doc in active_docs),
                    message=(
                        "Multiple active versioned canon documents remain live for the same lineage group: "
                        f"{', '.join(f'`{doc.path.as_posix()}`' for doc in active_docs)}."
                    ),
                )
            )

        for active_doc in active_docs:
            if active_doc.version <= 1:
                continue
            if active_doc.version - 1 in active_by_version:
                continue
            predecessor = archived_by_version.get(active_doc.version - 1)
            if predecessor is None:
                continue
            supersedes_refs = _supersedes_references(repo_root, active_doc.path)
            expected_refs = _expected_predecessor_references(active_doc.path, predecessor.path)
            if not supersedes_refs:
                findings.append(
                    CanonLineageFinding(
                        kind="missing_supersedes_reference",
                        severity="major",
                        drift_class="canon drift",
                        owner=_lineage_owner(active_doc.path),
                        source_path=active_doc.path.as_posix(),
                        related_paths=(min(expected_refs, key=len),),
                        message=(
                            f"Versioned canon document `{active_doc.path.as_posix()}` has an archived predecessor but does not declare "
                            f"a `Supersedes` reference to `{predecessor.path.as_posix()}`."
                        ),
                    )
                )
                continue
            if not any(ref in expected_refs for ref in supersedes_refs):
                findings.append(
                    CanonLineageFinding(
                        kind="mismatched_supersedes_reference",
                        severity="major",
                        drift_class="canon drift",
                        owner=_lineage_owner(active_doc.path),
                        source_path=active_doc.path.as_posix(),
                        related_paths=tuple(sorted(supersedes_refs)),
                        message=(
                            f"Versioned canon document `{active_doc.path.as_posix()}` declares `Supersedes` but not for its archived "
                            f"predecessor `{predecessor.path.as_posix()}`."
                        ),
                    )
                )


def _append_archived_reference_findings(findings: list[CanonLineageFinding], repo_root: Path) -> int:
    scanned_files = 0
    for root_path in EXECUTION_SURFACE_ROOTS:
        full_root = repo_root / root_path
        if not full_root.exists():
            continue
        for full_path in sorted(full_root.rglob("*.md")):
            rel_path = full_path.relative_to(repo_root)
            scanned_files += 1
            for archived_ref in _archived_canon_references(repo_root, rel_path, full_path.read_text(encoding="utf-8")):
                findings.append(
                    CanonLineageFinding(
                        kind="archived_canon_reference_in_active_surface",
                        severity="major",
                        drift_class="canon drift",
                        owner="PM",
                        source_path=rel_path.as_posix(),
                        related_paths=(archived_ref,),
                        message=(
                            f"Active execution surface `{rel_path.as_posix()}` references archived canon document `{archived_ref}` "
                            "instead of the current active document."
                        ),
                    )
                )
    return scanned_files


def _supersedes_references(repo_root: Path, path: Path) -> set[str]:
    contents = (repo_root / path).read_text(encoding="utf-8")
    return {match.group(1).replace("\\", "/") for match in SUPERCEDES_PATTERN.finditer(contents)}


def _expected_predecessor_references(current_path: Path, predecessor_path: Path) -> set[str]:
    expected = {
        predecessor_path.as_posix(),
        predecessor_path.name,
    }
    try:
        expected.add(predecessor_path.relative_to(current_path.parent).as_posix())
    except ValueError:
        pass
    docs_prefix = Path("docs")
    try:
        expected.add(predecessor_path.relative_to(docs_prefix).as_posix())
    except ValueError:
        pass
    return expected


def _archived_canon_references(repo_root: Path, source_path: Path, contents: str) -> tuple[str, ...]:
    archived_refs: list[str] = []
    for match in MARKDOWN_DOC_REF_PATTERN.finditer(contents):
        ref = match.group(1).replace("\\", "/")
        resolved = _resolve_markdown_reference(repo_root, source_path, ref)
        if resolved is None:
            continue
        if not _is_archived_versioned_doc(resolved):
            continue
        archived_refs.append(ref)
    return tuple(sorted(set(archived_refs)))


def _resolve_markdown_reference(repo_root: Path, source_path: Path, reference: str) -> Path | None:
    candidate = Path(reference)
    if candidate.is_absolute():
        return None
    for unresolved in (source_path.parent / candidate, candidate):
        resolved = (repo_root / unresolved).resolve()
        try:
            normalized = resolved.relative_to(repo_root)
        except ValueError:
            continue
        if resolved.is_file():
            return normalized
    return None


def _lineage_owner(path: Path) -> str:
    if path.parts[:2] in (("docs", "prds"), ("docs", "prd_exemplars")):
        return "PRD author"
    return "repository maintenance"


def _is_archived_versioned_doc(path: Path) -> bool:
    match = VERSIONED_DOC_PATTERN.match(path.stem)
    if match is None:
        return False
    return path.parent.name == "archive" or match.group("archived") is not None
