from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

# Provide stubs since we no longer have access to risk-manager scripts
DEFAULT_REGISTRY_PATH = Path("docs/registry/current_state_registry.yaml")

def load_registry(path: Path) -> dict:
    return {}

def render_module_dashboard(payload: dict, module_id: str) -> str:
    return ""


@dataclass(frozen=True, slots=True)
class ModuleDashboardFreshnessFinding:
    kind: str
    severity: str
    drift_class: str
    owner: str
    module_id: str
    dashboard_path: str
    registry_path: str
    message: str


@dataclass(frozen=True, slots=True)
class ModuleDashboardFreshnessStats:
    dashboards_declared: int
    dashboards_checked: int
    missing_dashboards: int
    stale_dashboards: int
    findings_count: int


@dataclass(frozen=True, slots=True)
class ModuleDashboardFreshnessReport:
    scan_name: str
    root: str
    generated_at: str
    findings: tuple[ModuleDashboardFreshnessFinding, ...]
    stats: ModuleDashboardFreshnessStats

    def to_dict(self) -> dict[str, object]:
        return {
            "scan_name": self.scan_name,
            "root": self.root,
            "generated_at": self.generated_at,
            "findings": [asdict(finding) for finding in self.findings],
            "stats": asdict(self.stats),
        }


def build_module_dashboard_freshness_report(root: Path) -> ModuleDashboardFreshnessReport:
    repo_root = root.resolve()
    registry_path = repo_root / DEFAULT_REGISTRY_PATH
    payload = load_registry(registry_path)
    raw_dashboards = payload.get("module_dashboards")
    if raw_dashboards is None:
        raw_dashboards = []
    if not isinstance(raw_dashboards, list):
        raise ValueError("registry `module_dashboards` must be a list")

    findings: list[ModuleDashboardFreshnessFinding] = []
    dashboards_checked = 0
    missing_dashboards = 0
    stale_dashboards = 0

    for entry in raw_dashboards:
        if not isinstance(entry, dict):
            raise ValueError("registry `module_dashboards` entries must be mappings")
        module_id = str(entry.get("id") or "UNKNOWN")
        dashboard_path = entry.get("dashboard_path")
        if not isinstance(dashboard_path, str) or not dashboard_path:
            raise ValueError("module dashboard entries must declare a non-empty `dashboard_path`")

        dashboards_checked += 1
        output_path = repo_root / dashboard_path
        expected = render_module_dashboard(payload, module_id=module_id)

        if not output_path.is_file():
            missing_dashboards += 1
            findings.append(
                ModuleDashboardFreshnessFinding(
                    kind="missing_generated_dashboard",
                    severity="critical",
                    drift_class="maturity or status drift",
                    owner="PM",
                    module_id=module_id,
                    dashboard_path=dashboard_path,
                    registry_path=DEFAULT_REGISTRY_PATH.as_posix(),
                    message=(
                        f"Generated module dashboard `{dashboard_path}` for `{module_id}` is missing. "
                        f"Rerun `python scripts/render_module_dashboard.py --module-id {module_id}` after updating the registry."
                    ),
                )
            )
            continue

        actual = output_path.read_text(encoding="utf-8")
        if actual != expected:
            stale_dashboards += 1
            findings.append(
                ModuleDashboardFreshnessFinding(
                    kind="stale_generated_dashboard",
                    severity="critical",
                    drift_class="maturity or status drift",
                    owner="PM",
                    module_id=module_id,
                    dashboard_path=dashboard_path,
                    registry_path=DEFAULT_REGISTRY_PATH.as_posix(),
                    message=(
                        f"Generated module dashboard `{dashboard_path}` is out of sync with "
                        f"`{DEFAULT_REGISTRY_PATH.as_posix()}` for `{module_id}`. "
                        f"Rerun `python scripts/render_module_dashboard.py --module-id {module_id}`."
                    ),
                )
            )

    findings.sort(key=lambda finding: (finding.dashboard_path, finding.kind, finding.module_id))
    return ModuleDashboardFreshnessReport(
        scan_name="module_dashboard_freshness",
        root=".",
        generated_at=datetime.now(UTC).isoformat(),
        findings=tuple(findings),
        stats=ModuleDashboardFreshnessStats(
            dashboards_declared=len(raw_dashboards),
            dashboards_checked=dashboards_checked,
            missing_dashboards=missing_dashboards,
            stale_dashboards=stale_dashboards,
            findings_count=len(findings),
        ),
    )
