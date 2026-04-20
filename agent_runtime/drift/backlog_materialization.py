from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
import re


PRDS_ROOT = Path("docs/prds")
WORK_ITEMS_ROOT = Path("work_items")
LIVE_WORK_ITEM_DIRS: tuple[str, ...] = ("ready", "in_progress", "done", "blocked")
READY_STATUS_PATTERN = re.compile(r"^\s*-\s+\*\*Status:\*\*\s+Ready for implementation\b", re.IGNORECASE | re.MULTILINE)
WORK_ITEM_ID_PATTERN = re.compile(r"\b(WI-(?:[A-Z]+-\d+[A-Z]?|\d+(?:\.\d+)*(?:[A-Z])?))\b")
WORK_ITEM_HEADING_PATTERN = re.compile(r"^#\s+(WI-[A-Z0-9][A-Z0-9.\-]*)\b", re.MULTILINE)
ISSUE_DECOMPOSITION_HEADING = "## Issue decomposition guidance"
NEXT_SECTION_PATTERN = re.compile(r"^##\s+", re.MULTILINE)


@dataclass(frozen=True, slots=True)
class BacklogMaterializationFinding:
    kind: str
    severity: str
    drift_class: str
    owner: str
    source_path: str
    related_paths: tuple[str, ...]
    message: str


@dataclass(frozen=True, slots=True)
class BacklogMaterializationStats:
    active_prds_scanned: int
    prds_with_issue_decomposition: int
    live_work_items_indexed: int
    findings_count: int


@dataclass(frozen=True, slots=True)
class BacklogMaterializationReport:
    scan_name: str
    root: str
    generated_at: str
    findings: tuple[BacklogMaterializationFinding, ...]
    stats: BacklogMaterializationStats

    def to_dict(self) -> dict[str, object]:
        return {
            "scan_name": self.scan_name,
            "root": self.root,
            "generated_at": self.generated_at,
            "findings": [asdict(finding) for finding in self.findings],
            "stats": asdict(self.stats),
        }


def build_backlog_materialization_report(root: Path) -> BacklogMaterializationReport:
    repo_root = root.resolve()
    findings: list[BacklogMaterializationFinding] = []
    prd_paths = _active_ready_prd_paths(repo_root)
    live_work_item_ids = _live_work_item_ids(repo_root)
    prds_with_issue_decomposition = 0

    for prd_path in prd_paths:
        contents = (repo_root / prd_path).read_text(encoding="utf-8")
        decomposition = _issue_decomposition_section(contents)
        if decomposition is None:
            continue
        prds_with_issue_decomposition += 1
        wi_ids = _decomposed_work_item_ids(decomposition)
        if not wi_ids:
            continue
        missing_ids = tuple(sorted(wi_id for wi_id in wi_ids if wi_id not in live_work_item_ids))
        if not missing_ids:
            continue
        findings.append(
            BacklogMaterializationFinding(
                kind="missing_decomposed_work_items",
                severity="major",
                drift_class="operational-instruction drift",
                owner="PM",
                source_path=prd_path.as_posix(),
                related_paths=missing_ids,
                message=(
                    f"Implementation-ready PRD `{prd_path.as_posix()}` names decomposed work items "
                    f"{', '.join(f'`{wi_id}`' for wi_id in missing_ids)} but no live backlog files exist for them under "
                    "`work_items/ready/`, `work_items/in_progress/`, `work_items/done/`, or `work_items/blocked/`. "
                    "Route to Issue Planner or reconcile backlog lifecycle state before a PM coding handoff."
                ),
            )
        )

    findings.sort(key=lambda finding: (finding.source_path, finding.related_paths))
    return BacklogMaterializationReport(
        scan_name="backlog_materialization",
        root=".",
        generated_at=datetime.now(UTC).isoformat(),
        findings=tuple(findings),
        stats=BacklogMaterializationStats(
            active_prds_scanned=len(prd_paths),
            prds_with_issue_decomposition=prds_with_issue_decomposition,
            live_work_items_indexed=len(live_work_item_ids),
            findings_count=len(findings),
        ),
    )


def _active_ready_prd_paths(repo_root: Path) -> tuple[Path, ...]:
    active_paths: list[Path] = []
    prds_root = repo_root / PRDS_ROOT
    if not prds_root.is_dir():
        return ()
    for full_path in sorted(prds_root.rglob("*.md")):
        rel_path = full_path.relative_to(repo_root)
        if "archive" in rel_path.parts:
            continue
        contents = full_path.read_text(encoding="utf-8")
        if READY_STATUS_PATTERN.search(contents) is None:
            continue
        active_paths.append(rel_path)
    return tuple(active_paths)


def _live_work_item_ids(repo_root: Path) -> frozenset[str]:
    work_item_ids: set[str] = set()
    for stage_dir in LIVE_WORK_ITEM_DIRS:
        stage_root = repo_root / WORK_ITEMS_ROOT / stage_dir
        if not stage_root.is_dir():
            continue
        for full_path in sorted(stage_root.glob("*.md")):
            try:
                contents = full_path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            match = WORK_ITEM_HEADING_PATTERN.search(contents)
            if match is None:
                continue
            work_item_ids.add(match.group(1))
    return frozenset(work_item_ids)


def _issue_decomposition_section(contents: str) -> str | None:
    start = contents.find(ISSUE_DECOMPOSITION_HEADING)
    if start == -1:
        return None
    section_body_start = contents.find("\n", start)
    if section_body_start == -1:
        return ""
    next_section = NEXT_SECTION_PATTERN.search(contents, section_body_start + 1)
    if next_section is None:
        return contents[section_body_start + 1 :]
    return contents[section_body_start + 1 : next_section.start()]


def _decomposed_work_item_ids(section: str) -> tuple[str, ...]:
    wi_ids: dict[str, None] = {}
    for match in WORK_ITEM_ID_PATTERN.finditer(section):
        trailing = section[match.end() : match.end() + 2]
        if len(trailing) == 2 and trailing[0] == "." and trailing[1].isalpha():
            continue
        wi_ids.setdefault(match.group(1), None)
    return tuple(wi_ids)
