from __future__ import annotations

import ast
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ArchitectureBoundaryFinding:
    kind: str
    severity: str
    drift_class: str
    owner: str
    source_path: str
    source_line: int
    import_target: str
    message: str


@dataclass(frozen=True, slots=True)
class ArchitectureBoundaryStats:
    python_files_scanned: int
    imports_checked: int
    findings_count: int


@dataclass(frozen=True, slots=True)
class ArchitectureBoundaryReport:
    scan_name: str
    root: str
    generated_at: str
    findings: tuple[ArchitectureBoundaryFinding, ...]
    stats: ArchitectureBoundaryStats

    def to_dict(self) -> dict[str, object]:
        return {
            "scan_name": self.scan_name,
            "root": self.root,
            "generated_at": self.generated_at,
            "findings": [asdict(finding) for finding in self.findings],
            "stats": asdict(self.stats),
        }


@dataclass(frozen=True, slots=True)
class _ScopeRule:
    forbidden_prefix: str
    kind: str
    message: str


_SCOPED_ROOTS: tuple[tuple[Path, str], ...] = (
    (Path("src/modules"), "module"),
    (Path("src/walkers"), "walker"),
    (Path("src/orchestrators"), "orchestrator"),
    (Path("src/ui"), "ui"),
    (Path("src/presentation"), "ui"),
    (Path("agent_runtime"), "runtime"),
)

_FORBIDDEN_IMPORTS: dict[str, tuple[_ScopeRule, ...]] = {
    "module": (
        _ScopeRule("src.walkers", "module_imports_walker_surface", "Module code must not import walker surfaces."),
        _ScopeRule(
            "src.orchestrators",
            "module_imports_orchestrator_surface",
            "Module code must not import orchestrator surfaces.",
        ),
        _ScopeRule("agent_runtime", "module_imports_runtime_surface", "Module code must not import runtime surfaces."),
    ),
    "walker": (
        _ScopeRule(
            "src.orchestrators",
            "walker_imports_orchestrator_surface",
            "Walker code must not import orchestrator surfaces.",
        ),
        _ScopeRule("agent_runtime", "walker_imports_runtime_surface", "Walker code must not import runtime surfaces."),
    ),
    "orchestrator": (
        _ScopeRule(
            "agent_runtime",
            "orchestrator_imports_runtime_surface",
            "Domain orchestrator code must not import runtime surfaces.",
        ),
    ),
    "ui": (
        _ScopeRule("src.walkers", "ui_imports_walker_surface", "UI code must not import walker surfaces directly."),
        _ScopeRule(
            "src.orchestrators",
            "ui_imports_orchestrator_surface",
            "UI code must not import orchestrator surfaces directly.",
        ),
        _ScopeRule("agent_runtime", "ui_imports_runtime_surface", "UI code must not import runtime surfaces."),
    ),
    "runtime": (
        _ScopeRule("src.modules", "runtime_imports_module_surface", "Runtime code must not import deterministic module surfaces."),
        _ScopeRule("src.walkers", "runtime_imports_walker_surface", "Runtime code must not import walker surfaces."),
        _ScopeRule(
            "src.orchestrators",
            "runtime_imports_orchestrator_surface",
            "Runtime code must not import domain orchestrator surfaces.",
        ),
    ),
}


def build_architecture_boundary_report(root: Path) -> ArchitectureBoundaryReport:
    repo_root = root.resolve()
    findings: list[ArchitectureBoundaryFinding] = []
    python_files_scanned = 0
    imports_checked = 0

    for source_path, scope_name in _scoped_source_files(repo_root):
        python_files_scanned += 1
        module_name = _module_name_for_path(source_path)
        tree = ast.parse((repo_root / source_path).read_text(encoding="utf-8"), filename=source_path.as_posix())
        for lineno, import_target in _import_targets(tree, module_name):
            imports_checked += 1
            for rule in _FORBIDDEN_IMPORTS.get(scope_name, ()):
                if _matches_import(import_target, rule.forbidden_prefix):
                    findings.append(
                        ArchitectureBoundaryFinding(
                            kind=rule.kind,
                            severity="critical",
                            drift_class="implementation drift",
                            owner="coding",
                            source_path=source_path.as_posix(),
                            source_line=lineno,
                            import_target=import_target,
                            message=f"{rule.message} `{source_path.as_posix()}` imports `{import_target}`.",
                        )
                    )

    findings.sort(key=lambda finding: (finding.source_path, finding.source_line, finding.import_target))
    return ArchitectureBoundaryReport(
        scan_name="architecture_boundaries",
        root=".",
        generated_at=datetime.now(UTC).isoformat(),
        findings=tuple(findings),
        stats=ArchitectureBoundaryStats(
            python_files_scanned=python_files_scanned,
            imports_checked=imports_checked,
            findings_count=len(findings),
        ),
    )


def _scoped_source_files(repo_root: Path) -> tuple[tuple[Path, str], ...]:
    source_files: list[tuple[Path, str]] = []
    for root_path, scope_name in _SCOPED_ROOTS:
        full_root = repo_root / root_path
        if not full_root.exists():
            continue
        for full_path in sorted(full_root.rglob("*.py")):
            rel_path = full_path.relative_to(repo_root)
            if any(part == "tests" for part in rel_path.parts):
                continue
            source_files.append((rel_path, scope_name))
    return tuple(source_files)


def _module_name_for_path(source_path: Path) -> str:
    module_parts = source_path.with_suffix("").parts
    if source_path.name == "__init__.py":
        module_parts = source_path.parent.parts
    return ".".join(module_parts)


def _import_targets(tree: ast.AST, module_name: str) -> tuple[tuple[int, str], ...]:
    import_targets: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                import_targets.append((node.lineno, alias.name))
        elif isinstance(node, ast.ImportFrom):
            resolved = _resolve_import_from(module_name, node)
            if resolved is not None:
                import_targets.append((node.lineno, resolved))
    return tuple(import_targets)


def _resolve_import_from(module_name: str, node: ast.ImportFrom) -> str | None:
    if node.level == 0:
        return node.module
    module_parts = module_name.split(".")
    package_parts = module_parts if module_name.endswith(".__init__") else module_parts[:-1]
    ascend = node.level - 1
    if ascend > len(package_parts):
        return None
    base_parts = package_parts[: len(package_parts) - ascend]
    if node.module is None:
        return ".".join(base_parts)
    return ".".join(base_parts + node.module.split("."))


def _matches_import(import_target: str, forbidden_prefix: str) -> bool:
    return import_target == forbidden_prefix or import_target.startswith(f"{forbidden_prefix}.")
