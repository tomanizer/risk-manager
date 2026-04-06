from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from fnmatch import fnmatch
from pathlib import Path
import re
import subprocess


TEXT_SUFFIXES = {
    ".json",
    ".md",
    ".mdx",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}
ROOT_REFERENCES = {
    "AGENTS.md",
    "CLAUDE.md",
    "CODEOWNERS",
    "GEMINI.md",
    "README.md",
    "pyproject.toml",
    "requirements.txt",
}
REPO_PREFIXES = (
    ".github/",
    "agent_runtime/",
    "artifacts/",
    "docs/",
    "fixtures/",
    "prompts/",
    "scripts/",
    "src/",
    "tests/",
    "work_items/",
)
FALLBACK_SCAN_DIRS = tuple(prefix.removesuffix("/") for prefix in REPO_PREFIXES)
MARKDOWN_LINK_PATTERN = re.compile(r"\[[^\]]+\]\(([^)\s]+)\)")
BACKTICK_PATTERN = re.compile(r"`([^`\n]+)`")


@dataclass(frozen=True, slots=True)
class ReferenceFinding:
    kind: str
    severity: str
    drift_class: str
    owner: str
    source_file: str
    source_line: int
    reference: str
    message: str


@dataclass(frozen=True, slots=True)
class ReferenceScanStats:
    files_scanned: int
    references_checked: int
    findings_count: int


@dataclass(frozen=True, slots=True)
class ReferenceScanReport:
    scan_name: str
    root: str
    generated_at: str
    findings: tuple[ReferenceFinding, ...]
    stats: ReferenceScanStats

    def to_dict(self) -> dict[str, object]:
        return {
            "scan_name": self.scan_name,
            "root": self.root,
            "generated_at": self.generated_at,
            "findings": [asdict(finding) for finding in self.findings],
            "stats": asdict(self.stats),
        }


def build_reference_scan_report(root: Path) -> ReferenceScanReport:
    repo_root = root.resolve()
    findings: list[ReferenceFinding] = []
    files_scanned = 0
    references_checked = 0
    sanctioned_generated_outputs = _documented_generated_artifact_paths(repo_root)

    for source_file in _tracked_text_files(repo_root):
        files_scanned += 1
        try:
            lines = source_file.read_text(encoding="utf-8").splitlines()
        except (FileNotFoundError, UnicodeDecodeError):
            continue
        in_code_fence = False
        for line_number, line in enumerate(lines, start=1):
            stripped = line.strip()
            if stripped.startswith("```") or stripped.startswith("~~~"):
                in_code_fence = not in_code_fence
                continue
            if in_code_fence:
                continue
            if "<!-- drift-ignore -->" in line:
                continue
            for raw_reference in _extract_references(line):
                normalized = _normalize_reference(raw_reference)
                if normalized is None:
                    continue
                references_checked += 1
                resolved = _resolve_reference(repo_root, source_file, normalized)
                if resolved is None:
                    _append_missing_reference_finding(
                        findings=findings,
                        repo_root=repo_root,
                        source_file=source_file,
                        source_line=line_number,
                        reference=normalized,
                        message=f"Referenced path `{normalized}` escapes the repository root.",
                    )
                    continue
                if not resolved.exists():
                    if normalized in sanctioned_generated_outputs:
                        continue
                    _append_missing_reference_finding(
                        findings=findings,
                        repo_root=repo_root,
                        source_file=source_file,
                        source_line=line_number,
                        reference=normalized,
                        message=f"Referenced path `{normalized}` does not exist under the repository root.",
                    )

    findings.sort(key=lambda finding: (finding.source_file, finding.source_line, finding.reference))
    return ReferenceScanReport(
        scan_name="reference_integrity",
        root=".",
        generated_at=datetime.now(UTC).isoformat(),
        findings=tuple(findings),
        stats=ReferenceScanStats(
            files_scanned=files_scanned,
            references_checked=references_checked,
            findings_count=len(findings),
        ),
    )


def _tracked_text_files(root: Path) -> tuple[Path, ...]:
    git_files = _git_tracked_files(root)
    if git_files is not None:
        return tuple(path for path in git_files if _should_scan(path.relative_to(root)))

    collected: list[Path] = []
    for path in _fallback_scan_candidates(root):
        if path.is_file() and _should_scan(path.relative_to(root)):
            collected.append(path)
    return tuple(sorted(collected))


def _git_tracked_files(root: Path) -> tuple[Path, ...] | None:
    try:
        completed = subprocess.run(
            ["git", "ls-files"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None

    tracked_paths: list[Path] = []
    for line in completed.stdout.splitlines():
        if not line:
            continue
        tracked_paths.append(root / line)
    return tuple(tracked_paths)


def _should_scan(path: Path) -> bool:
    if path.name.startswith(".") and path.name != ".github":
        return False
    if any(part.startswith(".") and part != ".github" for part in path.parts):
        return False
    return path.suffix in TEXT_SUFFIXES or path.name in ROOT_REFERENCES


def _extract_references(line: str) -> tuple[str, ...]:
    references: list[str] = []
    references.extend(match.group(1) for match in MARKDOWN_LINK_PATTERN.finditer(line))
    references.extend(match.group(1) for match in BACKTICK_PATTERN.finditer(line))
    unique_references = dict.fromkeys(references)
    return tuple(unique_references)


def _append_missing_reference_finding(
    findings: list[ReferenceFinding],
    repo_root: Path,
    source_file: Path,
    source_line: int,
    reference: str,
    message: str,
) -> None:
    drift_class, owner = _classify_source(source_file.relative_to(repo_root).as_posix())
    findings.append(
        ReferenceFinding(
            kind="missing_reference",
            severity="major",
            drift_class=drift_class,
            owner=owner,
            source_file=source_file.relative_to(repo_root).as_posix(),
            source_line=source_line,
            reference=reference,
            message=message,
        )
    )


def _documented_generated_artifact_paths(root: Path) -> frozenset[str]:
    """Return documented generated artifact outputs sanctioned by repo policy.

    A path is sanctioned only when it is listed in an artifacts README under the
    "Recommended local output paths:" section and also matches an ignored
    `artifacts/` pattern from the repository `.gitignore`.
    """
    ignored_artifact_patterns = _ignored_generated_artifact_patterns(root)
    artifacts_root = root / "artifacts"
    if not ignored_artifact_patterns or not artifacts_root.is_dir():
        return frozenset()

    documented_paths: set[str] = set()
    for readme_path in sorted(artifacts_root.rglob("README.md")):
        try:
            lines = readme_path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue

        in_output_section = False
        for line in lines:
            stripped = line.strip()
            if stripped == "Recommended local output paths:":
                in_output_section = True
                continue
            if not in_output_section:
                continue
            if not stripped:
                continue
            if not stripped.startswith("- "):
                in_output_section = False
                continue
            for raw_reference in _extract_references(stripped):
                normalized = _normalize_reference(raw_reference)
                if normalized is None:
                    continue
                if _matches_ignored_artifact_pattern(normalized, ignored_artifact_patterns):
                    documented_paths.add(normalized)
    return frozenset(documented_paths)


def _ignored_generated_artifact_patterns(root: Path) -> tuple[str, ...]:
    """Load `.gitignore` patterns that explicitly cover generated `artifacts/` paths."""
    gitignore_path = root / ".gitignore"
    if not gitignore_path.is_file():
        return ()

    patterns: list[str] = []
    for line in gitignore_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith(("#", "!")):
            continue
        normalized = stripped.removeprefix("./").rstrip("/")
        if normalized.startswith("artifacts/"):
            patterns.append(normalized)
    return tuple(patterns)


def _matches_ignored_artifact_pattern(reference: str, patterns: tuple[str, ...]) -> bool:
    return any(fnmatch(reference, pattern) for pattern in patterns)


def _normalize_reference(raw_reference: str) -> str | None:
    reference = raw_reference.strip().strip("\"'").rstrip(".,:;")
    if not reference or reference.startswith("#"):
        return None
    if "://" in reference or reference.startswith(("mailto:", "app://", "plugin://")):
        return None
    if any(char in reference for char in "<>*{}"):
        return None
    reference = reference.split("#", maxsplit=1)[0]
    reference = reference.split("?", maxsplit=1)[0]
    if reference.startswith("/"):
        return None
    if reference.startswith("../") or reference.startswith("./"):
        return reference
    if reference in ROOT_REFERENCES or reference.startswith(REPO_PREFIXES):
        return reference
    return None


def _resolve_reference(root: Path, source_file: Path, reference: str) -> Path | None:
    candidate = (source_file.parent / reference) if reference.startswith(("./", "../")) else (root / reference)
    try:
        resolved = candidate.resolve(strict=False)
        resolved.relative_to(root)
    except ValueError:
        return None
    return resolved


def _fallback_scan_candidates(root: Path) -> tuple[Path, ...]:
    candidates: list[Path] = []
    for child in root.iterdir():
        if child.is_file():
            candidates.append(child)
            continue
        if child.name not in FALLBACK_SCAN_DIRS:
            continue
        candidates.extend(path for path in child.rglob("*"))
    return tuple(sorted(candidates))


def _classify_source(source_file: str) -> tuple[str, str]:
    if source_file.startswith(("prompts/", ".github/agents/")) or source_file in {"AGENTS.md", "CLAUDE.md", "GEMINI.md"}:
        return ("operational-instruction drift", "PM")
    if source_file.startswith(("docs/", "work_items/")):
        return ("canon drift", "PM")
    if source_file.startswith((".github/workflows/", "tests/", "agent_runtime/", "src/")):
        return ("tooling drift", "repository maintenance")
    return ("canon drift", "PM")
