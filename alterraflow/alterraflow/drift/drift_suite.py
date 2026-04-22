from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime
import json
from pathlib import Path
from typing import Callable

from alterraflow.telemetry import drift_scan_span, record_drift_findings

from .architecture_boundaries import ArchitectureBoundaryReport, build_architecture_boundary_report
from .backlog_materialization import BacklogMaterializationReport, build_backlog_materialization_report
from .canon_lineage import CanonLineageReport, build_canon_lineage_report
from .dependency_hygiene import DependencyHygieneReport, build_dependency_hygiene_report
from .instruction_surfaces import InstructionSurfaceReport, build_instruction_surface_report
from .module_dashboard_freshness import ModuleDashboardFreshnessReport, build_module_dashboard_freshness_report
from .reference_integrity import ReferenceScanReport, build_reference_scan_report
from .registry_alignment import RegistryAlignmentReport, build_registry_alignment_report
from .surface_liveness import SurfaceLivenessReport, build_surface_liveness_report


BASELINE_VERSION = 1
DEFAULT_BASELINE_PATH = Path("artifacts/drift/baseline.json")
DEFAULT_LATEST_REPORT_PATH = Path("artifacts/drift/latest_report.json")
DEFAULT_SUMMARY_PATH = Path("artifacts/drift/summary.md")

_ReportT = (
    ArchitectureBoundaryReport
    | BacklogMaterializationReport
    | CanonLineageReport
    | DependencyHygieneReport
    | InstructionSurfaceReport
    | ModuleDashboardFreshnessReport
    | ReferenceScanReport
    | RegistryAlignmentReport
    | SurfaceLivenessReport
)


@dataclass(frozen=True, slots=True)
class DriftBaselineEntry:
    scan_name: str
    signature: str
    rationale: str
    issue: str | None = None
    expires_on: str | None = None


@dataclass(frozen=True, slots=True)
class DriftSuiteFinding:
    scan_name: str
    signature: str
    kind: str
    severity: str
    drift_class: str
    owner: str
    message: str
    raw_finding: dict[str, object]
    rationale: str | None = None
    issue: str | None = None
    expires_on: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> DriftSuiteFinding:
        raw_finding = data.get("raw_finding")
        if not isinstance(raw_finding, dict):
            raise ValueError("DriftSuiteFinding payload `raw_finding` must be an object.")
        return cls(
            scan_name=str(data["scan_name"]),
            signature=str(data["signature"]),
            kind=str(data["kind"]),
            severity=str(data["severity"]),
            drift_class=str(data["drift_class"]),
            owner=str(data["owner"]),
            message=str(data["message"]),
            raw_finding=dict(raw_finding),
            rationale=_optional_string(data.get("rationale")),
            issue=_optional_string(data.get("issue")),
            expires_on=_optional_string(data.get("expires_on")),
        )


@dataclass(frozen=True, slots=True)
class DriftScanSummary:
    scan_name: str
    title: str
    artifact_path: str
    stats: dict[str, object]
    total_findings: int
    new_findings: tuple[DriftSuiteFinding, ...]
    waived_findings: tuple[DriftSuiteFinding, ...]

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> DriftScanSummary:
        raw_stats = data.get("stats")
        raw_new = data.get("new_findings")
        raw_waived = data.get("waived_findings")
        if not isinstance(raw_stats, dict):
            raise ValueError("DriftScanSummary payload `stats` must be an object.")
        if not isinstance(raw_new, (list, tuple)):
            raise ValueError("DriftScanSummary payload `new_findings` must be a list.")
        if not isinstance(raw_waived, (list, tuple)):
            raise ValueError("DriftScanSummary payload `waived_findings` must be a list.")
        return cls(
            scan_name=str(data["scan_name"]),
            title=str(data["title"]),
            artifact_path=str(data["artifact_path"]),
            stats={str(k): v for k, v in raw_stats.items()},
            total_findings=_require_payload_int(data, "total_findings"),
            new_findings=tuple(DriftSuiteFinding.from_dict(f) for f in raw_new if isinstance(f, dict)),
            waived_findings=tuple(DriftSuiteFinding.from_dict(f) for f in raw_waived if isinstance(f, dict)),
        )


@dataclass(frozen=True, slots=True)
class DriftSuiteStats:
    scans_run: int
    total_findings: int
    new_findings: int
    waived_findings: int


@dataclass(frozen=True, slots=True)
class DriftSuiteReport:
    scan_name: str
    root: str
    generated_at: str
    baseline_path: str
    scans: tuple[DriftScanSummary, ...]
    findings: tuple[DriftSuiteFinding, ...]
    waived_findings: tuple[DriftSuiteFinding, ...]
    stats: DriftSuiteStats

    def to_dict(self) -> dict[str, object]:
        return {
            "scan_name": self.scan_name,
            "root": self.root,
            "generated_at": self.generated_at,
            "baseline_path": self.baseline_path,
            "scans": [asdict(scan) for scan in self.scans],
            "findings": [asdict(finding) for finding in self.findings],
            "waived_findings": [asdict(finding) for finding in self.waived_findings],
            "stats": asdict(self.stats),
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> DriftSuiteReport:
        raw_stats = data.get("stats")
        raw_scans = data.get("scans")
        raw_findings = data.get("findings")
        raw_waived = data.get("waived_findings")
        if not isinstance(raw_stats, dict):
            raise ValueError("DriftSuiteReport payload `stats` must be an object.")
        if not isinstance(raw_scans, (list, tuple)):
            raise ValueError("DriftSuiteReport payload `scans` must be a list.")
        if not isinstance(raw_findings, (list, tuple)):
            raise ValueError("DriftSuiteReport payload `findings` must be a list.")
        if not isinstance(raw_waived, (list, tuple)):
            raise ValueError("DriftSuiteReport payload `waived_findings` must be a list.")
        return cls(
            scan_name=str(data["scan_name"]),
            root=str(data["root"]),
            generated_at=str(data["generated_at"]),
            baseline_path=str(data["baseline_path"]),
            scans=tuple(DriftScanSummary.from_dict(s) for s in raw_scans if isinstance(s, dict)),
            findings=tuple(DriftSuiteFinding.from_dict(f) for f in raw_findings if isinstance(f, dict)),
            waived_findings=tuple(DriftSuiteFinding.from_dict(f) for f in raw_waived if isinstance(f, dict)),
            stats=DriftSuiteStats(
                scans_run=_require_payload_int(raw_stats, "scans_run"),
                total_findings=_require_payload_int(raw_stats, "total_findings"),
                new_findings=_require_payload_int(raw_stats, "new_findings"),
                waived_findings=_require_payload_int(raw_stats, "waived_findings"),
            ),
        )


@dataclass(frozen=True, slots=True)
class _CollectedDriftSuite:
    report: DriftSuiteReport
    scanner_payloads: dict[str, str]


@dataclass(frozen=True, slots=True)
class _ScannerSpec:
    scan_name: str
    title: str
    artifact_name: str
    build_report: Callable[[Path], _ReportT]


_SCANNERS: tuple[_ScannerSpec, ...] = (
    _ScannerSpec(
        scan_name="architecture_boundaries",
        title="Architecture Boundaries",
        artifact_name="architecture_boundaries.json",
        build_report=build_architecture_boundary_report,
    ),
    _ScannerSpec(
        scan_name="backlog_materialization",
        title="Backlog Materialization",
        artifact_name="backlog_materialization.json",
        build_report=build_backlog_materialization_report,
    ),
    _ScannerSpec(
        scan_name="canon_lineage",
        title="Canon Lineage",
        artifact_name="canon_lineage.json",
        build_report=build_canon_lineage_report,
    ),
    _ScannerSpec(
        scan_name="dependency_hygiene",
        title="Dependency Hygiene",
        artifact_name="dependency_hygiene.json",
        build_report=build_dependency_hygiene_report,
    ),
    _ScannerSpec(
        scan_name="instruction_surfaces",
        title="Instruction Surfaces",
        artifact_name="instruction_surfaces.json",
        build_report=build_instruction_surface_report,
    ),
    _ScannerSpec(
        scan_name="module_dashboard_freshness",
        title="Module Dashboard Freshness",
        artifact_name="module_dashboard_freshness.json",
        build_report=build_module_dashboard_freshness_report,
    ),
    _ScannerSpec(
        scan_name="reference_integrity",
        title="Reference Integrity",
        artifact_name="reference_integrity.json",
        build_report=build_reference_scan_report,
    ),
    _ScannerSpec(
        scan_name="registry_alignment",
        title="Registry Alignment",
        artifact_name="registry_alignment.json",
        build_report=build_registry_alignment_report,
    ),
    _ScannerSpec(
        scan_name="surface_liveness",
        title="Surface Liveness",
        artifact_name="surface_liveness.json",
        build_report=build_surface_liveness_report,
    ),
)

_SIGNATURE_FIELDS: dict[str, tuple[str, ...]] = {
    "architecture_boundaries": ("kind", "source_path", "source_line", "import_target"),
    "backlog_materialization": ("kind", "source_path", "related_paths"),
    "canon_lineage": ("kind", "source_path", "related_paths"),
    "dependency_hygiene": ("kind", "dependency_name", "source_path"),
    "instruction_surfaces": ("kind", "source_path", "related_paths"),
    "module_dashboard_freshness": ("kind", "module_id", "dashboard_path", "registry_path"),
    "reference_integrity": ("kind", "source_file", "source_line", "reference"),
    "registry_alignment": ("kind", "component_id", "implementation_path", "registry_path"),
    "surface_liveness": ("kind", "source_path", "source_line", "related_path"),
}


def build_drift_suite_report(root: Path, *, baseline_path: Path | None = None, artifact_dir: Path | None = None) -> DriftSuiteReport:
    return _collect_drift_suite(root, baseline_path=baseline_path, artifact_dir=artifact_dir).report


def _collect_drift_suite(root: Path, *, baseline_path: Path | None = None, artifact_dir: Path | None = None) -> _CollectedDriftSuite:
    repo_root = root.resolve()
    resolved_baseline_path = _resolve_baseline_path(repo_root, baseline_path)
    baseline_entries = _load_baseline_entries(resolved_baseline_path)
    resolved_artifact_dir = _resolve_artifact_dir(repo_root, artifact_dir)

    scan_summaries: list[DriftScanSummary] = []
    all_new_findings: list[DriftSuiteFinding] = []
    all_waived_findings: list[DriftSuiteFinding] = []
    scanner_payloads: dict[str, str] = {}
    total_findings = 0

    for scanner in _SCANNERS:
        with drift_scan_span(scanner.scan_name) as _span:
            report = scanner.build_report(repo_root)
            raw_payload = report.to_dict()
            raw_findings = _require_list(raw_payload.get("findings"), scan_name=scanner.scan_name, field_name="findings")
            new_findings, waived_findings = _partition_findings(scanner.scan_name, raw_findings, baseline_entries)
            artifact_path = _display_path(resolved_artifact_dir / scanner.artifact_name, repo_root)
            raw_stats = _require_dict(raw_payload.get("stats"), scan_name=scanner.scan_name, field_name="stats")
            scan_summaries.append(
                DriftScanSummary(
                    scan_name=scanner.scan_name,
                    title=scanner.title,
                    artifact_path=artifact_path,
                    stats=raw_stats,
                    total_findings=len(raw_findings),
                    new_findings=tuple(new_findings),
                    waived_findings=tuple(waived_findings),
                )
            )
            total_findings += len(raw_findings)
            all_new_findings.extend(new_findings)
            all_waived_findings.extend(waived_findings)
            scanner_payloads[scanner.artifact_name] = json.dumps(raw_payload, indent=2, sort_keys=True)

            if _span is not None:
                _span.set_attribute("drift.total_findings", len(raw_findings))
                _span.set_attribute("drift.new_findings", len(new_findings))

            # Emit per-severity counters for Prometheus / Grafana.
            severity_counts: dict[str, int] = {}
            for f in new_findings:
                severity_counts[f.severity] = severity_counts.get(f.severity, 0) + 1
            for severity, count in severity_counts.items():
                record_drift_findings(scanner.scan_name, severity, count)

    all_new_findings.sort(key=_sort_suite_finding)
    all_waived_findings.sort(key=_sort_suite_finding)
    return _CollectedDriftSuite(
        report=DriftSuiteReport(
            scan_name="drift_suite",
            root=".",
            generated_at=datetime.now(UTC).isoformat(),
            baseline_path=_display_path(resolved_baseline_path, repo_root),
            scans=tuple(scan_summaries),
            findings=tuple(all_new_findings),
            waived_findings=tuple(all_waived_findings),
            stats=DriftSuiteStats(
                scans_run=len(_SCANNERS),
                total_findings=total_findings,
                new_findings=len(all_new_findings),
                waived_findings=len(all_waived_findings),
            ),
        ),
        scanner_payloads=scanner_payloads,
    )


def write_drift_suite_artifacts(
    root: Path,
    *,
    artifact_dir: Path | None = None,
    output_path: Path | None = None,
    baseline_path: Path | None = None,
    summary_output_path: Path | None = None,
) -> DriftSuiteReport:
    repo_root = root.resolve()
    resolved_artifact_dir = _resolve_artifact_dir(repo_root, artifact_dir)
    resolved_output_path = _resolve_output_path(repo_root, output_path, DEFAULT_LATEST_REPORT_PATH)
    resolved_summary_path = _resolve_output_path(repo_root, summary_output_path, DEFAULT_SUMMARY_PATH)
    resolved_baseline_path = _resolve_baseline_path(repo_root, baseline_path)

    resolved_artifact_dir.mkdir(parents=True, exist_ok=True)
    collected = _collect_drift_suite(
        repo_root,
        baseline_path=resolved_baseline_path,
        artifact_dir=resolved_artifact_dir,
    )
    report = collected.report

    for artifact_name, scanner_payload in collected.scanner_payloads.items():
        (resolved_artifact_dir / artifact_name).write_text(scanner_payload + "\n", encoding="utf-8")

    resolved_output_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_output_path.write_text(json.dumps(report.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    resolved_summary_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_summary_path.write_text(render_drift_suite_markdown_summary(report) + "\n", encoding="utf-8")
    return report


def render_drift_suite_markdown_summary(report: DriftSuiteReport) -> str:
    lines = [
        "## Drift Monitor",
        "",
        f"- Scans run: `{report.stats.scans_run}`",
        f"- Total findings: `{report.stats.total_findings}`",
        f"- New findings: `{report.stats.new_findings}`",
        f"- Waived findings: `{report.stats.waived_findings}`",
        f"- Baseline: `{report.baseline_path}`",
        "",
    ]

    for scan in report.scans:
        lines.append(f"### {scan.title}")
        lines.append(f"- Scan: `{scan.scan_name}`")
        lines.append(f"- Artifact: `{scan.artifact_path}`")
        lines.append(f"- Total findings: `{scan.total_findings}`")
        lines.append(f"- New findings: `{len(scan.new_findings)}`")
        lines.append(f"- Waived findings: `{len(scan.waived_findings)}`")
        for key, value in scan.stats.items():
            if key == "findings_count":
                continue
            lines.append(f"- {_labelize_stat_name(key)}: `{value}`")
        if scan.new_findings:
            lines.append("- Top new findings:")
            for finding in scan.new_findings[:10]:
                lines.append(f"- `{finding.severity}` `{_summary_anchor(finding)}` -> {finding.owner}")
            if len(scan.new_findings) > 10:
                lines.append(f"- ... and `{len(scan.new_findings) - 10}` more")
        elif scan.waived_findings:
            lines.append("- No new findings detected.")
            lines.append("- Current findings are fully covered by baseline.")
        else:
            lines.append("- No findings detected.")
        lines.append("")

    return "\n".join(lines).rstrip()


def render_drift_suite_issue_body(report: DriftSuiteReport) -> str:
    lines = [
        "<!-- drift-monitor-issue -->",
        "# Repo Health Drift Report",
        "",
        f"- Generated at: `{report.generated_at}`",
        f"- Baseline: `{report.baseline_path}`",
        f"- Scans run: `{report.stats.scans_run}`",
        f"- Total findings: `{report.stats.total_findings}`",
        f"- Net-new findings: `{report.stats.new_findings}`",
        f"- Waived findings: `{report.stats.waived_findings}`",
        "",
    ]

    if report.findings:
        lines.append("## Net-New Findings")
        lines.append("")
        for finding in report.findings:
            lines.extend(
                [
                    f"### {finding.scan_name}: {finding.kind}",
                    f"- Severity: `{finding.severity}`",
                    f"- Drift class: `{finding.drift_class}`",
                    f"- Owner: `{finding.owner}`",
                    f"- Signature: `{finding.signature}`",
                    f"- Evidence: `{_summary_anchor(finding)}`",
                    f"- Message: {finding.message}",
                    "",
                ]
            )
    else:
        lines.extend(
            [
                "## Net-New Findings",
                "",
                "No net-new drift findings were detected in the latest run.",
                "",
            ]
        )

    if report.waived_findings:
        lines.extend(
            [
                "## Baselined Findings",
                "",
                f"These findings are still present but currently covered by `{report.baseline_path}`.",
                "",
            ]
        )
        for finding in report.waived_findings[:20]:
            rationale = finding.rationale or "No rationale recorded."
            issue = "" if finding.issue is None else f" Issue: `{finding.issue}`."
            lines.append(f"- `{finding.scan_name}` `{_summary_anchor(finding)}`: {rationale}{issue}")
        if len(report.waived_findings) > 20:
            lines.append(f"- ... and `{len(report.waived_findings) - 20}` more baselined findings")
        lines.append("")

    lines.extend(
        [
            "## Per-Scanner Summary",
            "",
        ]
    )
    for scan in report.scans:
        lines.extend(
            [
                f"### {scan.title}",
                f"- Total findings: `{scan.total_findings}`",
                f"- New findings: `{len(scan.new_findings)}`",
                f"- Waived findings: `{len(scan.waived_findings)}`",
                f"- Artifact: `{scan.artifact_path}`",
                "",
            ]
        )

    return "\n".join(lines).rstrip()


def _resolve_artifact_dir(repo_root: Path, artifact_dir: Path | None) -> Path:
    if artifact_dir is None:
        return repo_root / DEFAULT_LATEST_REPORT_PATH.parent
    return _resolve_path_argument(repo_root, artifact_dir)


def _resolve_output_path(repo_root: Path, output_path: Path | None, default_path: Path) -> Path:
    if output_path is None:
        return repo_root / default_path
    return _resolve_path_argument(repo_root, output_path)


def _resolve_baseline_path(repo_root: Path, baseline_path: Path | None) -> Path:
    if baseline_path is None:
        return repo_root / DEFAULT_BASELINE_PATH
    return _resolve_path_argument(repo_root, baseline_path)


def _resolve_path_argument(repo_root: Path, path: Path) -> Path:
    return path if path.is_absolute() else (repo_root / path)


def _display_path(path: Path, repo_root: Path) -> str:
    try:
        return path.relative_to(repo_root).as_posix()
    except ValueError:
        return path.as_posix()


def _load_baseline_entries(baseline_path: Path) -> dict[tuple[str, str], DriftBaselineEntry]:
    if not baseline_path.is_file():
        return {}

    payload = json.loads(baseline_path.read_text(encoding="utf-8"))
    if payload.get("version") != BASELINE_VERSION:
        raise ValueError(f"Baseline `{baseline_path}` has unsupported version `{payload.get('version')}`.")
    allowed_findings = payload.get("allowed_findings", [])
    if not isinstance(allowed_findings, list):
        raise ValueError(f"Baseline `{baseline_path}` has an invalid `allowed_findings` section.")

    entries: dict[tuple[str, str], DriftBaselineEntry] = {}
    for raw_entry in allowed_findings:
        if not isinstance(raw_entry, dict):
            raise ValueError(f"Baseline `{baseline_path}` contains a non-object finding entry.")
        scan_name = str(raw_entry["scan_name"])
        signature = str(raw_entry["signature"])
        entry = DriftBaselineEntry(
            scan_name=scan_name,
            signature=signature,
            rationale=str(raw_entry["rationale"]),
            issue=_optional_string(raw_entry.get("issue")),
            expires_on=_optional_string(raw_entry.get("expires_on")),
        )
        entries[(scan_name, signature)] = entry
    return entries


def _require_list(value: object, *, scan_name: str, field_name: str) -> list[object]:
    if isinstance(value, list):
        return value
    raise ValueError(f"Scanner `{scan_name}` emitted invalid `{field_name}` data; expected a list.")


def _require_dict(value: object, *, scan_name: str, field_name: str) -> dict[str, object]:
    if isinstance(value, dict):
        return {str(key): item for key, item in value.items()}
    raise ValueError(f"Scanner `{scan_name}` emitted invalid `{field_name}` data; expected an object.")


def _partition_findings(
    scan_name: str,
    raw_findings: list[object],
    baseline_entries: dict[tuple[str, str], DriftBaselineEntry],
) -> tuple[list[DriftSuiteFinding], list[DriftSuiteFinding]]:
    today = datetime.now(UTC).date()
    new_findings: list[DriftSuiteFinding] = []
    waived_findings: list[DriftSuiteFinding] = []

    for raw_finding in raw_findings:
        if not isinstance(raw_finding, dict):
            raise ValueError(f"Scanner `{scan_name}` emitted a non-object finding.")
        signature = finding_signature(scan_name, raw_finding)
        entry = baseline_entries.get((scan_name, signature))
        finding = DriftSuiteFinding(
            scan_name=scan_name,
            signature=signature,
            kind=str(raw_finding["kind"]),
            severity=str(raw_finding["severity"]),
            drift_class=str(raw_finding["drift_class"]),
            owner=str(raw_finding["owner"]),
            message=str(raw_finding["message"]),
            raw_finding=raw_finding,
            rationale=None if entry is None else entry.rationale,
            issue=None if entry is None else entry.issue,
            expires_on=None if entry is None else entry.expires_on,
        )
        if entry is None or _is_baseline_expired(entry, today):
            new_findings.append(finding)
        else:
            waived_findings.append(finding)
    return new_findings, waived_findings


def _is_baseline_expired(entry: DriftBaselineEntry, today: date) -> bool:
    if entry.expires_on is None:
        return False
    try:
        return today > date.fromisoformat(entry.expires_on)
    except ValueError:
        return False


def finding_signature(scan_name: str, raw_finding: dict[str, object]) -> str:
    fields = _SIGNATURE_FIELDS.get(scan_name)
    if fields is None:
        raise KeyError(f"No signature fields configured for scanner `{scan_name}`.")
    parts = [scan_name]
    for field_name in fields:
        parts.append(f"{field_name}={_signature_value(raw_finding.get(field_name))}")
    return "|".join(parts)


def _signature_value(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


def _require_payload_int(data: dict[str, object], field_name: str) -> int:
    value = data[field_name]
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"Payload field `{field_name}` must be an integer.")
    return value


def _sort_suite_finding(finding: DriftSuiteFinding) -> tuple[str, str, str]:
    return (finding.scan_name, finding.kind, _summary_anchor(finding))


def _summary_anchor(finding: DriftSuiteFinding) -> str:
    raw = finding.raw_finding
    if finding.scan_name == "architecture_boundaries":
        return f"{raw['source_path']}:{raw['source_line']} `{raw['import_target']}`"
    if finding.scan_name == "backlog_materialization":
        related_paths = raw.get("related_paths")
        if isinstance(related_paths, list) and related_paths:
            return f"{raw['source_path']} `{', '.join(str(path) for path in related_paths)}`"
        return f"{raw['source_path']} `{raw['kind']}`"
    if finding.scan_name == "canon_lineage":
        return f"{raw['source_path']} `{raw['kind']}`"
    if finding.scan_name == "dependency_hygiene":
        return f"{raw['source_path']} `{raw['dependency_name']}`"
    if finding.scan_name == "instruction_surfaces":
        return f"{raw['source_path']} `{raw['kind']}`"
    if finding.scan_name == "reference_integrity":
        return f"{raw['source_file']}:{raw['source_line']} `{raw['reference']}`"
    if finding.scan_name == "registry_alignment":
        component_id = raw["component_id"]
        kind = raw["kind"]
        implementation_path = raw.get("implementation_path") or raw["registry_path"]
        return f"{component_id} `{kind}` `{implementation_path}`"
    if finding.scan_name == "surface_liveness":
        source_line = raw.get("source_line")
        related_path = raw.get("related_path")
        if source_line is None:
            return f"{raw['source_path']} `{raw['kind']}`"
        if related_path is None:
            return f"{raw['source_path']}:{source_line} `{raw['kind']}`"
        return f"{raw['source_path']}:{source_line} `{related_path}`"
    return finding.kind


def _labelize_stat_name(name: str) -> str:
    return name.replace("_", " ").capitalize()
