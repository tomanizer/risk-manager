from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
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

    for source_file in _tracked_text_files(repo_root):
        files_scanned += 1
        try:
            lines = source_file.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        for line_number, line in enumerate(lines, start=1):
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
        return tuple(path for path in git_files if _should_scan(path))

    collected: list[Path] = []
    for path in _fallback_scan_candidates(root):
        if path.is_file() and _should_scan(path):
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
