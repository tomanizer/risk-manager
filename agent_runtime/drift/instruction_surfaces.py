from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
import re


GITHUB_AGENTS_DIR = Path(".github/agents")
PROMPT_AGENTS_DIR = Path("prompts/agents")
DRIFT_PROMPT_PATH = Path("prompts/drift_monitor/repo_health_audit_prompt.md")
COPILOT_INSTRUCTIONS_PATH = Path(".github/copilot-instructions.md")

FRESHNESS_TRIAD = (
    "git fetch origin",
    "git switch main",
    "git pull --ff-only origin main",
)

ROLE_SURFACES: tuple[tuple[str, Path, Path], ...] = (
    ("coding", Path(".github/agents/coding.agent.md"), Path("prompts/agents/coding_agent_instruction.md")),
    ("drift-monitor", Path(".github/agents/drift-monitor.agent.md"), Path("prompts/agents/drift_monitor_agent_instruction.md")),
    ("issue-planner", Path(".github/agents/issue-planner.agent.md"), Path("prompts/agents/issue_planner_instruction.md")),
    ("pm", Path(".github/agents/pm.agent.md"), Path("prompts/agents/pm_agent_instruction.md")),
    ("review", Path(".github/agents/review.agent.md"), Path("prompts/agents/review_agent_instruction.md")),
    (
        "risk-methodology-spec",
        Path(".github/agents/risk-methodology-spec.agent.md"),
        Path("prompts/agents/risk_methodology_spec_agent_instruction.md"),
    ),
)

README_EXPECTATIONS: tuple[tuple[Path, tuple[str, ...]], ...] = (
    (
        Path(".github/agents/README.md"),
        (
            "pm.agent.md",
            "issue-planner.agent.md",
            "risk-methodology-spec.agent.md",
            "coding.agent.md",
            "review.agent.md",
            "drift-monitor.agent.md",
        ),
    ),
    (
        Path("prompts/agents/README.md"),
        (
            "pm_agent_instruction.md",
            "coding_agent_instruction.md",
            "review_agent_instruction.md",
            "issue_planner_instruction.md",
            "risk_methodology_spec_agent_instruction.md",
            "drift_monitor_agent_instruction.md",
        ),
    ),
)

AGENTS_REFERENCE_FILES: tuple[Path, ...] = (
    Path("CLAUDE.md"),
    Path("GEMINI.md"),
    Path(".github/agents/coding.agent.md"),
    Path(".github/agents/drift-monitor.agent.md"),
    Path(".github/agents/issue-planner.agent.md"),
    Path(".github/agents/pm.agent.md"),
    Path(".github/agents/review.agent.md"),
    Path(".github/agents/risk-methodology-spec.agent.md"),
)

DRIFT_ENTRYPOINT_FILES: tuple[Path, ...] = (
    Path(".github/agents/drift-monitor.agent.md"),
    Path("prompts/agents/drift_monitor_agent_instruction.md"),
    Path("prompts/drift_monitor/repo_health_audit_prompt.md"),
)

INSTRUCTION_SURFACE_SEVERITY = "major"
BACKTICK_TOKEN_PATTERN = re.compile(r"`([^`\n]+)`")


@dataclass(frozen=True, slots=True)
class InstructionSurfaceFinding:
    kind: str
    severity: str
    drift_class: str
    owner: str
    source_path: str
    related_paths: tuple[str, ...]
    message: str


@dataclass(frozen=True, slots=True)
class InstructionSurfaceStats:
    instruction_files_scanned: int
    role_surfaces_checked: int
    readme_inventories_checked: int
    freshness_surfaces_checked: int
    findings_count: int


@dataclass(frozen=True, slots=True)
class InstructionSurfaceReport:
    scan_name: str
    root: str
    generated_at: str
    findings: tuple[InstructionSurfaceFinding, ...]
    stats: InstructionSurfaceStats

    def to_dict(self) -> dict[str, object]:
        return {
            "scan_name": self.scan_name,
            "root": self.root,
            "generated_at": self.generated_at,
            "findings": [asdict(finding) for finding in self.findings],
            "stats": asdict(self.stats),
        }


def build_instruction_surface_report(root: Path) -> InstructionSurfaceReport:
    repo_root = root.resolve()
    findings: list[InstructionSurfaceFinding] = []
    instruction_files_scanned = 0
    freshness_surfaces_checked = 0

    for _, github_path, prompt_path in ROLE_SURFACES:
        if (repo_root / github_path).is_file():
            instruction_files_scanned += 1
        if (repo_root / prompt_path).is_file():
            instruction_files_scanned += 1
    for path in (
        Path("AGENTS.md"),
        Path("CLAUDE.md"),
        Path("GEMINI.md"),
        COPILOT_INSTRUCTIONS_PATH,
        Path(".github/agents/README.md"),
        Path("prompts/agents/README.md"),
        DRIFT_PROMPT_PATH,
    ):
        if (repo_root / path).is_file():
            instruction_files_scanned += 1

    _append_role_surface_findings(findings, repo_root)
    _append_readme_inventory_findings(findings, repo_root)
    _append_agents_reference_findings(findings, repo_root)

    for path in _freshness_rule_files(repo_root):
        freshness_surfaces_checked += 1
        _append_freshness_findings(findings, repo_root, path)

    _append_drift_entrypoint_findings(findings, repo_root)

    findings.sort(key=lambda finding: (finding.source_path, finding.kind, finding.related_paths))
    return InstructionSurfaceReport(
        scan_name="instruction_surfaces",
        root=".",
        generated_at=datetime.now(UTC).isoformat(),
        findings=tuple(findings),
        stats=InstructionSurfaceStats(
            instruction_files_scanned=instruction_files_scanned,
            role_surfaces_checked=len(ROLE_SURFACES),
            readme_inventories_checked=len(README_EXPECTATIONS),
            freshness_surfaces_checked=freshness_surfaces_checked,
            findings_count=len(findings),
        ),
    )


def _append_role_surface_findings(findings: list[InstructionSurfaceFinding], repo_root: Path) -> None:
    for role_name, github_path, prompt_path in ROLE_SURFACES:
        github_exists = (repo_root / github_path).is_file()
        prompt_exists = (repo_root / prompt_path).is_file()
        if github_exists and prompt_exists:
            continue
        missing_paths = tuple(path.as_posix() for path, exists in ((github_path, github_exists), (prompt_path, prompt_exists)) if not exists)
        findings.append(
            InstructionSurfaceFinding(
                kind="missing_instruction_surface",
                severity=INSTRUCTION_SURFACE_SEVERITY,
                drift_class="operational-instruction drift",
                owner="repository maintenance",
                source_path=github_path.as_posix() if not github_exists else prompt_path.as_posix(),
                related_paths=missing_paths,
                message=(f"Role `{role_name}` is missing an instruction surface pair: {', '.join(f'`{path}`' for path in missing_paths)}."),
            )
        )


def _append_readme_inventory_findings(findings: list[InstructionSurfaceFinding], repo_root: Path) -> None:
    for readme_path, expected_entries in README_EXPECTATIONS:
        full_path = repo_root / readme_path
        if not full_path.is_file():
            findings.append(
                InstructionSurfaceFinding(
                    kind="missing_instruction_inventory",
                    severity=INSTRUCTION_SURFACE_SEVERITY,
                    drift_class="operational-instruction drift",
                    owner="repository maintenance",
                    source_path=readme_path.as_posix(),
                    related_paths=(),
                    message=f"Instruction inventory file `{readme_path.as_posix()}` is missing.",
                )
            )
            continue
        listed_entries = _listed_backtick_tokens(full_path)
        expected = tuple(sorted(expected_entries))
        actual = tuple(sorted(entry for entry in listed_entries if entry in expected_entries))
        if actual == expected:
            continue
        missing_entries = tuple(entry for entry in expected if entry not in actual)
        findings.append(
            InstructionSurfaceFinding(
                kind="instruction_inventory_drift",
                severity=INSTRUCTION_SURFACE_SEVERITY,
                drift_class="operational-instruction drift",
                owner="repository maintenance",
                source_path=readme_path.as_posix(),
                related_paths=missing_entries,
                message=(
                    f"Instruction inventory `{readme_path.as_posix()}` is missing listed entries for: "
                    f"{', '.join(f'`{entry}`' for entry in missing_entries)}."
                ),
            )
        )


def _append_agents_reference_findings(findings: list[InstructionSurfaceFinding], repo_root: Path) -> None:
    for path in AGENTS_REFERENCE_FILES:
        full_path = repo_root / path
        if not full_path.is_file():
            continue
        contents = full_path.read_text(encoding="utf-8")
        if "AGENTS.md" in contents:
            continue
        findings.append(
            InstructionSurfaceFinding(
                kind="missing_agents_reference",
                severity=INSTRUCTION_SURFACE_SEVERITY,
                drift_class="operational-instruction drift",
                owner="repository maintenance",
                source_path=path.as_posix(),
                related_paths=("AGENTS.md",),
                message=f"Instruction surface `{path.as_posix()}` no longer references `AGENTS.md` as the primary repo-level source of truth.",
            )
        )


def _append_freshness_findings(findings: list[InstructionSurfaceFinding], repo_root: Path, path: Path) -> None:
    contents = (repo_root / path).read_text(encoding="utf-8")
    command_positions = {command: contents.find(command) for command in FRESHNESS_TRIAD if command in contents}
    if not command_positions:
        return
    if len(command_positions) != len(FRESHNESS_TRIAD):
        missing = tuple(command for command in FRESHNESS_TRIAD if command not in command_positions)
        findings.append(
            InstructionSurfaceFinding(
                kind="incomplete_freshness_rule",
                severity=INSTRUCTION_SURFACE_SEVERITY,
                drift_class="operational-instruction drift",
                owner="repository maintenance",
                source_path=path.as_posix(),
                related_paths=missing,
                message=(
                    f"Instruction surface `{path.as_posix()}` mentions the freshness rule but omits: "
                    f"{', '.join(f'`{command}`' for command in missing)}."
                ),
            )
        )
        return
    ordered_positions = [command_positions[command] for command in FRESHNESS_TRIAD]
    if ordered_positions != sorted(ordered_positions):
        findings.append(
            InstructionSurfaceFinding(
                kind="out_of_order_freshness_rule",
                severity=INSTRUCTION_SURFACE_SEVERITY,
                drift_class="operational-instruction drift",
                owner="repository maintenance",
                source_path=path.as_posix(),
                related_paths=FRESHNESS_TRIAD,
                message=(
                    f"Instruction surface `{path.as_posix()}` contains the freshness commands but not in canonical order: "
                    "`git fetch origin`, `git switch main`, `git pull --ff-only origin main`."
                ),
            )
        )


def _append_drift_entrypoint_findings(findings: list[InstructionSurfaceFinding], repo_root: Path) -> None:
    canonical_entrypoint = "scripts/drift/run_all.py"
    stale_tokens = (
        "scripts/drift/check_dependency_hygiene.py",
        "scripts/drift/check_references.py",
        "scripts/drift/check_registry_alignment.py",
    )
    for path in DRIFT_ENTRYPOINT_FILES:
        full_path = repo_root / path
        if not full_path.is_file():
            continue
        contents = full_path.read_text(encoding="utf-8")
        if canonical_entrypoint not in contents:
            findings.append(
                InstructionSurfaceFinding(
                    kind="missing_drift_suite_entrypoint",
                    severity=INSTRUCTION_SURFACE_SEVERITY,
                    drift_class="operational-instruction drift",
                    owner="repository maintenance",
                    source_path=path.as_posix(),
                    related_paths=(canonical_entrypoint,),
                    message=(
                        f"Drift-monitor surface `{path.as_posix()}` does not reference the canonical suite entrypoint `{canonical_entrypoint}`."
                    ),
                )
            )
        stale_present = tuple(token for token in stale_tokens if token in contents)
        if stale_present:
            findings.append(
                InstructionSurfaceFinding(
                    kind="stale_drift_monitor_commands",
                    severity=INSTRUCTION_SURFACE_SEVERITY,
                    drift_class="operational-instruction drift",
                    owner="repository maintenance",
                    source_path=path.as_posix(),
                    related_paths=stale_present,
                    message=(
                        f"Drift-monitor surface `{path.as_posix()}` still references individual scanner commands instead of the "
                        f"canonical suite runner `scripts/drift/run_all.py`."
                    ),
                )
            )


def _freshness_rule_files(repo_root: Path) -> tuple[Path, ...]:
    candidates = [
        Path("AGENTS.md"),
        Path("CLAUDE.md"),
        Path("GEMINI.md"),
        Path("docs/guides/overnight_agent_runbook.md"),
    ]
    candidates.extend(github_path for _, github_path, _ in ROLE_SURFACES)
    return tuple(path for path in candidates if (repo_root / path).is_file())


def _listed_backtick_tokens(path: Path) -> tuple[str, ...]:
    entries = {match.group(1) for match in BACKTICK_TOKEN_PATTERN.finditer(path.read_text(encoding="utf-8"))}
    return tuple(sorted(entries))
