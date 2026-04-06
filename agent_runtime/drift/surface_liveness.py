from __future__ import annotations

import ast
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
import re
import subprocess

from .registry_alignment import _load_registry_components, _module_root_from_component_id


TEXT_SUFFIXES = {
    ".md",
    ".mdx",
    ".txt",
    ".toml",
    ".yaml",
    ".yml",
}
ROOT_TEXT_FILES = {
    "AGENTS.md",
    "CLAUDE.md",
    "GEMINI.md",
    "README.md",
}
ACTIVE_TEXT_ROOTS = {
    ".github",
    "agent_runtime",
    "docs",
    "prompts",
    "src",
    "work_items",
}
ACTIVE_CODE_ROOTS = (
    Path("agent_runtime"),
    Path("scripts"),
    Path("src"),
)
LEGACY_SEGMENTS = frozenset({"archive", "archived", "deprecated", "legacy"})
REPO_MODULE_ENTRYPOINT_ROOTS = frozenset({"agent_runtime", "src"})
REGISTRY_PATH = Path("docs/registry/current_state_registry.yaml")
MODULE_ENTRYPOINT_PATTERN = re.compile(r"(?:^|\s)(?:\S*python(?:\d+(?:\.\d+)*)?)\s+-m\s+([A-Za-z_][\w\.]*)")


@dataclass(frozen=True, slots=True)
class SurfaceLivenessFinding:
    kind: str
    severity: str
    drift_class: str
    owner: str
    source_path: str
    source_line: int | None
    related_path: str | None
    message: str


@dataclass(frozen=True, slots=True)
class SurfaceLivenessStats:
    active_text_files_scanned: int
    entrypoint_references_checked: int
    active_code_files_scanned: int
    imports_checked: int
    module_roots_scanned: int
    findings_count: int


@dataclass(frozen=True, slots=True)
class SurfaceLivenessReport:
    scan_name: str
    root: str
    generated_at: str
    findings: tuple[SurfaceLivenessFinding, ...]
    stats: SurfaceLivenessStats

    def to_dict(self) -> dict[str, object]:
        return {
            "scan_name": self.scan_name,
            "root": self.root,
            "generated_at": self.generated_at,
            "findings": [asdict(finding) for finding in self.findings],
            "stats": asdict(self.stats),
        }


def build_surface_liveness_report(root: Path) -> SurfaceLivenessReport:
    repo_root = root.resolve()
    findings: list[SurfaceLivenessFinding] = []

    active_text_files_scanned = 0
    entrypoint_references_checked = 0
    for text_path in _active_text_files(repo_root):
        active_text_files_scanned += 1
        try:
            lines = text_path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        for line_number, line in enumerate(lines, start=1):
            for module_name in _module_entrypoints_in_line(line):
                entrypoint_references_checked += 1
                if _repo_module_entrypoint_exists(repo_root, module_name):
                    continue
                findings.append(
                    SurfaceLivenessFinding(
                        kind="missing_repo_module_entrypoint",
                        severity="major",
                        drift_class="operational-instruction drift",
                        owner="repository maintenance",
                        source_path=text_path.relative_to(repo_root).as_posix(),
                        source_line=line_number,
                        related_path=module_name,
                        message=(
                            f"Active surface `{text_path.relative_to(repo_root).as_posix()}` references repo module entrypoint "
                            f"`python -m {module_name}` but that module entrypoint does not exist."
                        ),
                    )
                )

    active_code_files_scanned = 0
    imports_checked = 0
    for code_path in _active_code_files(repo_root):
        active_code_files_scanned += 1
        module_name = _module_name_for_path(code_path.relative_to(repo_root))
        try:
            source_text = code_path.read_text(encoding="utf-8")
            tree = ast.parse(source_text, filename=code_path.relative_to(repo_root).as_posix())
        except (SyntaxError, UnicodeDecodeError):
            continue
        for line_number, import_target in _import_targets(tree, module_name):
            imports_checked += 1
            if not _imports_legacy_repo_surface(import_target):
                continue
            findings.append(
                SurfaceLivenessFinding(
                    kind="active_code_imports_legacy_surface",
                    severity="critical",
                    drift_class="implementation drift",
                    owner="coding",
                    source_path=code_path.relative_to(repo_root).as_posix(),
                    source_line=line_number,
                    related_path=import_target,
                    message=(f"Active code `{code_path.relative_to(repo_root).as_posix()}` imports legacy-marked surface `{import_target}`."),
                )
            )

    registry_module_roots = _registered_module_roots(repo_root)
    test_signals = _test_signals(repo_root)
    active_text_signals = _active_text_signals(repo_root)
    module_roots = _discovered_module_roots(repo_root)
    for module_root in module_roots:
        if module_root in registry_module_roots:
            continue
        if module_root in test_signals:
            continue
        if module_root in active_text_signals:
            continue
        findings.append(
            SurfaceLivenessFinding(
                kind="orphaned_module_root",
                severity="major",
                drift_class="implementation drift",
                owner="repository maintenance",
                source_path=f"src/modules/{module_root}",
                source_line=None,
                related_path=None,
                message=(
                    f"Module root `src/modules/{module_root}` has no registry entry, no active canon or execution-surface reference, "
                    "and no matching test signal."
                ),
            )
        )

    findings.sort(key=lambda finding: (finding.source_path, finding.source_line or 0, finding.kind, finding.related_path or ""))
    return SurfaceLivenessReport(
        scan_name="surface_liveness",
        root=".",
        generated_at=datetime.now(UTC).isoformat(),
        findings=tuple(findings),
        stats=SurfaceLivenessStats(
            active_text_files_scanned=active_text_files_scanned,
            entrypoint_references_checked=entrypoint_references_checked,
            active_code_files_scanned=active_code_files_scanned,
            imports_checked=imports_checked,
            module_roots_scanned=len(module_roots),
            findings_count=len(findings),
        ),
    )


def _active_text_files(root: Path) -> tuple[Path, ...]:
    tracked = _git_tracked_files(root)
    if tracked is None:
        return _fallback_active_text_files(root)
    return tuple(path for path in tracked if _is_active_text_surface(path.relative_to(root)))


def _active_code_files(root: Path) -> tuple[Path, ...]:
    code_files: list[Path] = []
    for code_root in ACTIVE_CODE_ROOTS:
        full_root = root / code_root
        if not full_root.exists():
            continue
        for full_path in sorted(full_root.rglob("*.py")):
            rel_path = full_path.relative_to(root)
            if any(part == "tests" for part in rel_path.parts):
                continue
            if not full_path.is_file():
                continue
            code_files.append(full_path)
    return tuple(code_files)


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


def _fallback_active_text_files(root: Path) -> tuple[Path, ...]:
    candidates: list[Path] = []
    for root_name in sorted(ACTIVE_TEXT_ROOTS):
        full_root = root / root_name
        if not full_root.exists():
            continue
        for full_path in sorted(full_root.rglob("*")):
            if not full_path.is_file():
                continue
            if _is_active_text_surface(full_path.relative_to(root)):
                candidates.append(full_path)
    for file_name in sorted(ROOT_TEXT_FILES):
        candidate = root / file_name
        if candidate.is_file():
            candidates.append(candidate)
    return tuple(dict.fromkeys(candidates))


def _is_active_text_surface(path: Path) -> bool:
    if path.name in ROOT_TEXT_FILES:
        return True
    if path.suffix not in TEXT_SUFFIXES:
        return False
    if not path.parts:
        return False
    if path.parts[0] not in ACTIVE_TEXT_ROOTS:
        return False
    if "archived" in path.parts or "archive" in path.parts:
        return False
    if path.parts[0] == "work_items" and len(path.parts) > 1 and path.parts[1] != "ready":
        return False
    if path.parts[0] == "tests":
        return False
    if path.parts[0] in {"agent_runtime", "src"} and path.name != "README.md":
        return False
    return True


def _module_entrypoints_in_line(line: str) -> tuple[str, ...]:
    matches = []
    for match in MODULE_ENTRYPOINT_PATTERN.finditer(line):
        module_name = match.group(1)
        if module_name.split(".", maxsplit=1)[0] not in REPO_MODULE_ENTRYPOINT_ROOTS:
            continue
        matches.append(module_name)
    return tuple(dict.fromkeys(matches))


def _repo_module_entrypoint_exists(root: Path, module_name: str) -> bool:
    module_path = root.joinpath(*module_name.split("."))
    if module_path.with_suffix(".py").is_file():
        return True
    if module_path.is_dir() and (module_path / "__main__.py").is_file():
        return True
    return False


def _module_name_for_path(source_path: Path) -> str:
    return ".".join(source_path.with_suffix("").parts)


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
    package_parts = module_parts[:-1]
    ascend = node.level - 1
    if ascend > len(package_parts):
        return None
    base_parts = package_parts[: len(package_parts) - ascend]
    if node.module is None:
        return ".".join(base_parts)
    return ".".join(base_parts + node.module.split("."))


def _imports_legacy_repo_surface(import_target: str) -> bool:
    parts = import_target.split(".")
    if not parts or parts[0] not in REPO_MODULE_ENTRYPOINT_ROOTS:
        return False
    return any(part in LEGACY_SEGMENTS for part in parts[1:])


def _registered_module_roots(root: Path) -> frozenset[str]:
    registry_path = root / REGISTRY_PATH
    if not registry_path.is_file():
        return frozenset()
    module_roots: set[str] = set()
    for component in _load_registry_components(registry_path):
        if component.section != "modules":
            continue
        module_root = _module_root_from_component_id(component.component_id)
        if module_root is not None:
            module_roots.add(module_root)
    return frozenset(module_roots)


def _test_signals(root: Path) -> frozenset[str]:
    tests_root = root / "tests"
    if not tests_root.is_dir():
        return frozenset()
    signal_text_by_root = _module_signal_text_by_root(root)
    signaled: set[str] = set()
    for test_path in sorted(tests_root.rglob("*.py")):
        if not test_path.is_file():
            continue
        rel_path = test_path.relative_to(root).as_posix()
        try:
            contents = test_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for module_root, signals in signal_text_by_root.items():
            if module_root in rel_path or any(signal in contents for signal in signals):
                signaled.add(module_root)
    return frozenset(signaled)


def _active_text_signals(root: Path) -> frozenset[str]:
    signal_text_by_root = _module_signal_text_by_root(root)
    signaled: set[str] = set()
    for text_path in _active_text_files(root):
        try:
            contents = text_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        rel_path = text_path.relative_to(root).as_posix()
        for module_root, signals in signal_text_by_root.items():
            if any(signal in contents for signal in signals) or module_root in rel_path:
                signaled.add(module_root)
    return frozenset(signaled)


def _module_signal_text_by_root(root: Path) -> dict[str, tuple[str, ...]]:
    return {
        module_root: (
            f"src/modules/{module_root}",
            f"src.modules.{module_root}",
        )
        for module_root in _discovered_module_roots(root)
    }


def _discovered_module_roots(root: Path) -> tuple[str, ...]:
    modules_root = root / "src" / "modules"
    if not modules_root.is_dir():
        return ()
    return tuple(sorted(child.name for child in modules_root.iterdir() if child.is_dir() and not child.name.startswith((".", "__"))))
