from __future__ import annotations

import ast
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
import re
import sys
import tomllib


PYPROJECT_PATH = Path("pyproject.toml")
WORKFLOWS_DIR = Path(".github/workflows")
INSTRUCTION_SCAN_DIRS = ("docs", "prompts", ".github")
INSTRUCTION_SCAN_FILES = ("AGENTS.md", "CLAUDE.md", "GEMINI.md")
RUNTIME_SCAN_DIRS = ("src", "agent_runtime")
DEV_SCAN_DIRS = ("tests", "scripts")
LOCAL_IMPORT_ROOTS = {"agent_runtime", "src", "tests", "scripts"}
WORKFLOW_TOOL_DEPENDENCIES = {
    "mypy": "mypy",
    "pytest": "pytest",
    "ruff": "ruff",
}
RUNTIME_OPTIONAL_SEVERITY = "major"
UNDECLARED_IMPORT_SEVERITY = "critical"
WORKFLOW_TOOL_SEVERITY = "major"
STALE_GUIDANCE_SEVERITY = "major"
STDLIB_MODULES = set(sys.stdlib_module_names)


@dataclass(frozen=True, slots=True)
class DependencyHygieneFinding:
    kind: str
    severity: str
    drift_class: str
    owner: str
    dependency_name: str
    source_path: str
    message: str


@dataclass(frozen=True, slots=True)
class DependencyHygieneStats:
    runtime_python_files_scanned: int
    dev_python_files_scanned: int
    workflows_scanned: int
    instruction_files_scanned: int
    runtime_imports_checked: int
    dev_imports_checked: int
    findings_count: int


@dataclass(frozen=True, slots=True)
class DependencyHygieneReport:
    scan_name: str
    root: str
    generated_at: str
    findings: tuple[DependencyHygieneFinding, ...]
    stats: DependencyHygieneStats

    def to_dict(self) -> dict[str, object]:
        return {
            "scan_name": self.scan_name,
            "root": self.root,
            "generated_at": self.generated_at,
            "findings": [asdict(finding) for finding in self.findings],
            "stats": asdict(self.stats),
        }


@dataclass(frozen=True, slots=True)
class _DeclaredDependencies:
    base: set[str]
    optional: dict[str, set[str]]

    @property
    def all(self) -> set[str]:
        return self.base.union(*(values for values in self.optional.values()))


@dataclass(frozen=True, slots=True)
class _ImportScanResult:
    imports: dict[str, set[str]]
    files_scanned: int


def build_dependency_hygiene_report(root: Path) -> DependencyHygieneReport:
    repo_root = root.resolve()
    declared_dependencies = _load_declared_dependencies(repo_root / PYPROJECT_PATH)
    runtime_scan = _scan_imports(repo_root, RUNTIME_SCAN_DIRS)
    dev_scan = _scan_imports(repo_root, DEV_SCAN_DIRS)
    workflows = _workflow_files(repo_root)
    instruction_files = _instruction_files(repo_root)
    findings: list[DependencyHygieneFinding] = []

    _append_runtime_import_findings(findings, declared_dependencies, runtime_scan.imports)
    _append_dev_import_findings(findings, declared_dependencies, dev_scan.imports)
    _append_workflow_tool_findings(findings, declared_dependencies.optional.get("dev", set()), workflows, repo_root)
    _append_stale_guidance_findings(findings, instruction_files, repo_root)

    findings.sort(key=lambda finding: (finding.kind, finding.dependency_name, finding.source_path))
    return DependencyHygieneReport(
        scan_name="dependency_hygiene",
        root=".",
        generated_at=datetime.now(UTC).isoformat(),
        findings=tuple(findings),
        stats=DependencyHygieneStats(
            runtime_python_files_scanned=runtime_scan.files_scanned,
            dev_python_files_scanned=dev_scan.files_scanned,
            workflows_scanned=len(workflows),
            instruction_files_scanned=len(instruction_files),
            runtime_imports_checked=len(runtime_scan.imports),
            dev_imports_checked=len(dev_scan.imports),
            findings_count=len(findings),
        ),
    )


def _load_declared_dependencies(pyproject_path: Path) -> _DeclaredDependencies:
    if not pyproject_path.is_file():
        raise FileNotFoundError(f"Dependency source `{pyproject_path}` does not exist.")
    with pyproject_path.open("rb") as handle:
        payload = tomllib.load(handle)

    project = payload.get("project", {})
    if not isinstance(project, dict):
        raise ValueError(f"`{pyproject_path}` has an invalid `[project]` section.")
    optional = project.get("optional-dependencies", {})
    if not isinstance(optional, dict):
        raise ValueError(f"`{pyproject_path}` has an invalid `[project.optional-dependencies]` section.")
    dependencies = {_canonicalize_dependency_name(item) for item in project.get("dependencies", [])}
    optional_dependencies = {extra: {_canonicalize_dependency_name(item) for item in entries} for extra, entries in optional.items()}
    return _DeclaredDependencies(base=dependencies, optional=optional_dependencies)


def _scan_imports(root: Path, scan_dirs: tuple[str, ...]) -> _ImportScanResult:
    imports: dict[str, set[str]] = {}
    files_scanned = 0
    for directory_name in scan_dirs:
        scan_root = root / directory_name
        if not scan_root.exists():
            continue
        for path in sorted(scan_root.rglob("*.py")):
            if not path.is_file():
                continue
            files_scanned += 1
            for module_name in _third_party_imports_in_file(path):
                imports.setdefault(module_name, set()).add(path.relative_to(root).as_posix())
    return _ImportScanResult(imports=imports, files_scanned=files_scanned)


def _third_party_imports_in_file(path: Path) -> set[str]:
    try:
        content = path.read_text(encoding="utf-8")
        tree = ast.parse(content, filename=str(path))
    except (SyntaxError, UnicodeDecodeError):
        return set()
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                _maybe_add_third_party_import(imports, alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.level != 0 or node.module is None:
                continue
            _maybe_add_third_party_import(imports, node.module)
    return imports


def _maybe_add_third_party_import(imports: set[str], module_path: str) -> None:
    top_level = module_path.partition(".")[0]
    if top_level in STDLIB_MODULES or top_level in LOCAL_IMPORT_ROOTS or top_level == "__future__":
        return
    imports.add(_canonicalize_dependency_name(top_level))


def _append_runtime_import_findings(
    findings: list[DependencyHygieneFinding],
    declared_dependencies: _DeclaredDependencies,
    runtime_imports: dict[str, set[str]],
) -> None:
    base_dependencies = declared_dependencies.base
    all_dependencies = declared_dependencies.all
    for dependency_name, source_paths in runtime_imports.items():
        source_path = min(source_paths)
        if dependency_name not in all_dependencies:
            findings.append(
                DependencyHygieneFinding(
                    kind="undeclared_runtime_dependency",
                    severity=UNDECLARED_IMPORT_SEVERITY,
                    drift_class="tooling drift",
                    owner="repository maintenance",
                    dependency_name=dependency_name,
                    source_path=source_path,
                    message=f"Runtime code imports `{dependency_name}` in `{source_path}` but it is not declared in `pyproject.toml`.",
                )
            )
            continue
        if dependency_name not in base_dependencies:
            findings.append(
                DependencyHygieneFinding(
                    kind="runtime_dependency_declared_only_in_optional_extra",
                    severity=RUNTIME_OPTIONAL_SEVERITY,
                    drift_class="tooling drift",
                    owner="repository maintenance",
                    dependency_name=dependency_name,
                    source_path=source_path,
                    message=f"Runtime code imports `{dependency_name}` in `{source_path}`, but it is declared only in an optional extra rather than `[project.dependencies]`.",
                )
            )


def _append_dev_import_findings(
    findings: list[DependencyHygieneFinding],
    declared_dependencies: _DeclaredDependencies,
    dev_imports: dict[str, set[str]],
) -> None:
    all_dependencies = declared_dependencies.all
    for dependency_name, source_paths in dev_imports.items():
        if dependency_name in all_dependencies:
            continue
        findings.append(
            DependencyHygieneFinding(
                kind="undeclared_dev_dependency",
                severity=UNDECLARED_IMPORT_SEVERITY,
                drift_class="tooling drift",
                owner="repository maintenance",
                dependency_name=dependency_name,
                source_path=min(source_paths),
                message=f"Test or tooling code imports `{dependency_name}` in `{min(source_paths)}` but it is not declared in `pyproject.toml`.",
            )
        )


def _append_workflow_tool_findings(
    findings: list[DependencyHygieneFinding],
    dev_dependencies: set[str],
    workflows: tuple[Path, ...],
    repo_root: Path,
) -> None:
    for workflow_path in workflows:
        try:
            contents = workflow_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        relative_path = workflow_path.relative_to(repo_root).as_posix()
        for tool_name, dependency_name in WORKFLOW_TOOL_DEPENDENCIES.items():
            if not re.search(rf"\b{re.escape(tool_name)}\b", contents):
                continue
            if dependency_name in dev_dependencies:
                continue
            findings.append(
                DependencyHygieneFinding(
                    kind="workflow_tool_missing_from_dev_extra",
                    severity=WORKFLOW_TOOL_SEVERITY,
                    drift_class="tooling drift",
                    owner="repository maintenance",
                    dependency_name=dependency_name,
                    source_path=relative_path,
                    message=f"Workflow `{relative_path}` invokes `{tool_name}` but `pyproject.toml` does not declare `{dependency_name}` in `[project.optional-dependencies].dev`.",
                )
            )


def _append_stale_guidance_findings(findings: list[DependencyHygieneFinding], instruction_files: tuple[Path, ...], repo_root: Path) -> None:
    stale_pattern = re.compile(r"(?i)\bupdat\w*\b.*\brequirements\.txt\b|\brequirements\.txt\b.*\bupdate\b")
    for file_path in instruction_files:
        try:
            lines = file_path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
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
            if not stale_pattern.search(line):
                continue
            relative_path = file_path.relative_to(repo_root).as_posix()
            findings.append(
                DependencyHygieneFinding(
                    kind="stale_requirements_txt_update_guidance",
                    severity=STALE_GUIDANCE_SEVERITY,
                    drift_class="operational-instruction drift",
                    owner="repository maintenance",
                    dependency_name="requirements.txt",
                    source_path=f"{relative_path}:{line_number}",
                    message=f"Instruction surface `{relative_path}:{line_number}` still tells agents to update `requirements.txt` instead of treating `pyproject.toml` as the dependency source of truth.",
                )
            )


def _workflow_files(root: Path) -> tuple[Path, ...]:
    workflows_root = root / WORKFLOWS_DIR
    if not workflows_root.is_dir():
        return ()
    return tuple(sorted(path for path in workflows_root.glob("*.yml")))


def _instruction_files(root: Path) -> tuple[Path, ...]:
    files: list[Path] = []
    for filename in INSTRUCTION_SCAN_FILES:
        path = root / filename
        if path.is_file():
            files.append(path)
    for dirname in INSTRUCTION_SCAN_DIRS:
        base = root / dirname
        if not base.exists():
            continue
        for path in sorted(base.rglob("*")):
            if path.suffix.lower() not in {".md", ".mdx", ".yml", ".yaml"}:
                continue
            if path.is_file():
                files.append(path)
    return tuple(files)


def _canonicalize_dependency_name(requirement: str) -> str:
    match = re.match(r"[A-Za-z0-9_.-]+", requirement)
    if match is None:
        return requirement.lower()
    return match.group(0).lower().replace("_", "-")
