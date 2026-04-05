from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
import re


ACTIVE_STATUSES = {"implemented", "in-progress"}
INACTIVE_STATUSES = {"draft", "not-started", "proposed"}
REGISTRY_PATH = Path("docs/registry/current_state_registry.yaml")
SECTIONS = ("modules", "walkers", "orchestrators")
REGISTRY_ALIGNMENT_SEVERITY = "critical"


@dataclass(frozen=True, slots=True)
class RegistrySubcomponent:
    name: str
    path: str | None
    status: str | None


@dataclass(frozen=True, slots=True)
class RegistryComponent:
    section: str
    component_id: str
    name: str | None
    status: str | None
    contract_status: str | None
    sub_components: tuple[RegistrySubcomponent, ...]


@dataclass(frozen=True, slots=True)
class RegistryAlignmentFinding:
    kind: str
    severity: str
    drift_class: str
    owner: str
    component_id: str
    component_name: str
    registry_path: str
    implementation_path: str | None
    message: str


@dataclass(frozen=True, slots=True)
class RegistryAlignmentStats:
    components_scanned: int
    subcomponents_scanned: int
    module_roots_discovered: int
    findings_count: int


@dataclass(frozen=True, slots=True)
class RegistryAlignmentReport:
    scan_name: str
    root: str
    generated_at: str
    findings: tuple[RegistryAlignmentFinding, ...]
    stats: RegistryAlignmentStats

    def to_dict(self) -> dict[str, object]:
        return {
            "scan_name": self.scan_name,
            "root": self.root,
            "generated_at": self.generated_at,
            "findings": [asdict(finding) for finding in self.findings],
            "stats": asdict(self.stats),
        }


def build_registry_alignment_report(root: Path) -> RegistryAlignmentReport:
    repo_root = root.resolve()
    components = _load_registry_components(repo_root / REGISTRY_PATH)
    findings: list[RegistryAlignmentFinding] = []
    discovered_module_roots = _discovered_module_roots(repo_root)
    registered_module_roots: set[str] = set()
    subcomponents_scanned = 0

    for component in components:
        if component.section != "modules":
            continue
        module_root = _module_root_from_name(component.name)
        if module_root is not None:
            registered_module_roots.add(module_root)
            _maybe_append_module_root_finding(
                findings=findings,
                repo_root=repo_root,
                component=component,
                module_root=module_root,
            )
        for subcomponent in component.sub_components:
            subcomponents_scanned += 1
            _maybe_append_subcomponent_finding(
                findings=findings,
                repo_root=repo_root,
                component=component,
                subcomponent=subcomponent,
            )

    for module_root in sorted(discovered_module_roots):
        if module_root not in registered_module_roots:
            findings.append(
                RegistryAlignmentFinding(
                    kind="unregistered_module_root",
                    severity=REGISTRY_ALIGNMENT_SEVERITY,
                    drift_class="maturity or status drift",
                    owner="PM",
                    component_id="UNREGISTERED",
                    component_name=module_root,
                    registry_path=REGISTRY_PATH.as_posix(),
                    implementation_path=f"src/modules/{module_root}",
                    message=f"Discovered module root `src/modules/{module_root}` is not represented in the current-state registry.",
                )
            )

    findings.sort(key=lambda finding: (finding.component_id, finding.kind, finding.implementation_path or ""))
    return RegistryAlignmentReport(
        scan_name="registry_alignment",
        root=".",
        generated_at=datetime.now(UTC).isoformat(),
        findings=tuple(findings),
        stats=RegistryAlignmentStats(
            components_scanned=len(components),
            subcomponents_scanned=subcomponents_scanned,
            module_roots_discovered=len(discovered_module_roots),
            findings_count=len(findings),
        ),
    )


def _load_registry_components(registry_path: Path) -> tuple[RegistryComponent, ...]:
    if not registry_path.is_file():
        raise FileNotFoundError(f"Registry file `{registry_path}` does not exist.")

    lines = registry_path.read_text(encoding="utf-8").splitlines()
    section: str | None = None
    current_component: dict[str, object] | None = None
    current_subcomponent: dict[str, object] | None = None
    in_subcomponents = False
    components: list[RegistryComponent] = []

    def finalize_subcomponent() -> None:
        nonlocal current_component, current_subcomponent
        if current_component is None or current_subcomponent is None:
            return
        sub_components = current_component.setdefault("sub_components", [])
        assert isinstance(sub_components, list)
        sub_components.append(
            RegistrySubcomponent(
                name=str(current_subcomponent.get("name", "")),
                path=_normalize_scalar(current_subcomponent.get("path")),
                status=_normalize_scalar(current_subcomponent.get("status")),
            )
        )
        current_subcomponent = None

    def finalize_component() -> None:
        nonlocal current_component, in_subcomponents
        finalize_subcomponent()
        if current_component is None or section is None:
            current_component = None
            in_subcomponents = False
            return
        raw_subcomponents = current_component.get("sub_components", [])
        assert isinstance(raw_subcomponents, list)
        components.append(
            RegistryComponent(
                section=section,
                component_id=str(current_component.get("id", "")),
                name=_normalize_scalar(current_component.get("name")),
                status=_normalize_scalar(current_component.get("status")),
                contract_status=_normalize_scalar(current_component.get("contract_status")),
                sub_components=tuple(raw_subcomponents),
            )
        )
        current_component = None
        in_subcomponents = False

    for raw_line in lines:
        line_content = _strip_yaml_comment(raw_line)
        if not line_content.strip():
            continue
        stripped = line_content.strip()

        if stripped.endswith(":") and stripped[:-1] in SECTIONS:
            finalize_component()
            section = stripped[:-1]
            continue

        if section is None:
            continue

        if stripped.startswith("- id: "):
            finalize_component()
            current_component = {"id": _parse_scalar(stripped.partition(":")[2].strip()), "sub_components": []}
            continue

        if current_component is None:
            continue

        if stripped == "sub_components:":
            finalize_subcomponent()
            in_subcomponents = True
            continue

        if in_subcomponents and stripped.startswith("- name: "):
            finalize_subcomponent()
            current_subcomponent = {"name": _parse_scalar(stripped.partition(":")[2].strip())}
            continue

        if in_subcomponents and current_subcomponent is not None and ":" in stripped and not stripped.startswith("- "):
            key, _, raw_value = stripped.partition(":")
            current_subcomponent[key] = _parse_scalar(raw_value.strip())
            continue

        if not in_subcomponents and ":" in stripped and not stripped.startswith("- "):
            key, _, raw_value = stripped.partition(":")
            current_component[key] = _parse_scalar(raw_value.strip())
            continue

    finalize_component()
    return tuple(components)


def _maybe_append_module_root_finding(
    findings: list[RegistryAlignmentFinding],
    repo_root: Path,
    component: RegistryComponent,
    module_root: str,
) -> None:
    implementation_path = repo_root / "src" / "modules" / module_root
    exists = implementation_path.exists()
    registry_status = component.status or "unknown"
    relative_path = implementation_path.relative_to(repo_root).as_posix()

    if registry_status in ACTIVE_STATUSES and not exists:
        findings.append(
            RegistryAlignmentFinding(
                kind="missing_module_root",
                severity=REGISTRY_ALIGNMENT_SEVERITY,
                drift_class="maturity or status drift",
                owner="PM",
                component_id=component.component_id,
                component_name=component.name or component.component_id,
                registry_path=REGISTRY_PATH.as_posix(),
                implementation_path=relative_path,
                message=f"Registry marks module `{component.name}` as `{registry_status}` but expected module root `{relative_path}` does not exist.",
            )
        )
    if registry_status in INACTIVE_STATUSES and exists:
        findings.append(
            RegistryAlignmentFinding(
                kind="unexpected_module_root",
                severity=REGISTRY_ALIGNMENT_SEVERITY,
                drift_class="maturity or status drift",
                owner="PM",
                component_id=component.component_id,
                component_name=component.name or component.component_id,
                registry_path=REGISTRY_PATH.as_posix(),
                implementation_path=relative_path,
                message=f"Registry marks module `{component.name}` as `{registry_status}` but implementation already exists at `{relative_path}`.",
            )
        )


def _maybe_append_subcomponent_finding(
    findings: list[RegistryAlignmentFinding],
    repo_root: Path,
    component: RegistryComponent,
    subcomponent: RegistrySubcomponent,
) -> None:
    status = subcomponent.status or "unknown"
    if subcomponent.path is None:
        if status in ACTIVE_STATUSES:
            findings.append(
                RegistryAlignmentFinding(
                    kind="implemented_subcomponent_without_path",
                    severity=REGISTRY_ALIGNMENT_SEVERITY,
                    drift_class="maturity or status drift",
                    owner="PM",
                    component_id=component.component_id,
                    component_name=subcomponent.name,
                    registry_path=REGISTRY_PATH.as_posix(),
                    implementation_path=None,
                    message=f"Registry marks subcomponent `{subcomponent.name}` as `{status}` but does not declare an implementation path.",
                )
            )
        return

    implementation_path = repo_root / subcomponent.path
    exists = implementation_path.exists()
    relative_path = implementation_path.relative_to(repo_root).as_posix()
    if status in ACTIVE_STATUSES and not exists:
        findings.append(
            RegistryAlignmentFinding(
                kind="missing_registered_path",
                severity=REGISTRY_ALIGNMENT_SEVERITY,
                drift_class="maturity or status drift",
                owner="PM",
                component_id=component.component_id,
                component_name=subcomponent.name,
                registry_path=REGISTRY_PATH.as_posix(),
                implementation_path=relative_path,
                message=f"Registry marks subcomponent `{subcomponent.name}` as `{status}` but `{relative_path}` does not exist.",
            )
        )
    if status in INACTIVE_STATUSES and exists:
        findings.append(
            RegistryAlignmentFinding(
                kind="unexpected_implemented_path",
                severity=REGISTRY_ALIGNMENT_SEVERITY,
                drift_class="maturity or status drift",
                owner="PM",
                component_id=component.component_id,
                component_name=subcomponent.name,
                registry_path=REGISTRY_PATH.as_posix(),
                implementation_path=relative_path,
                message=f"Registry marks subcomponent `{subcomponent.name}` as `{status}` but implementation already exists at `{relative_path}`.",
            )
        )


def _discovered_module_roots(root: Path) -> frozenset[str]:
    modules_root = root / "src" / "modules"
    if not modules_root.is_dir():
        return frozenset()
    return frozenset(child.name for child in modules_root.iterdir() if child.is_dir() and not child.name.startswith((".", "__")))


def _module_root_from_name(name: str | None) -> str | None:
    if not name:
        return None
    slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    return slug or None


def _parse_scalar(raw_value: str) -> object | None:
    if raw_value == "null":
        return None
    return raw_value.strip("\"'")


def _strip_yaml_comment(raw_line: str) -> str:
    in_single_quote = False
    in_double_quote = False
    for index, char in enumerate(raw_line):
        if char == "'" and not in_double_quote:
            in_single_quote = not in_single_quote
            continue
        if char == '"' and not in_single_quote:
            in_double_quote = not in_double_quote
            continue
        if char == "#" and not in_single_quote and not in_double_quote:
            return raw_line[:index]
    return raw_line


def _normalize_scalar(value: object | None) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None
