"""Deterministic drift scanners used by repo-health audits."""

from .canon_lineage import CanonLineageReport, build_canon_lineage_report
from .dependency_hygiene import DependencyHygieneReport, build_dependency_hygiene_report
from .drift_suite import (
    DriftSuiteReport,
    build_drift_suite_report,
    render_drift_suite_issue_body,
    render_drift_suite_markdown_summary,
)
from .instruction_surfaces import InstructionSurfaceReport, build_instruction_surface_report
from .reference_integrity import ReferenceScanReport, build_reference_scan_report
from .registry_alignment import RegistryAlignmentReport, build_registry_alignment_report

__all__ = [
    "CanonLineageReport",
    "DependencyHygieneReport",
    "DriftSuiteReport",
    "InstructionSurfaceReport",
    "ReferenceScanReport",
    "RegistryAlignmentReport",
    "build_canon_lineage_report",
    "build_dependency_hygiene_report",
    "build_drift_suite_report",
    "build_instruction_surface_report",
    "build_reference_scan_report",
    "build_registry_alignment_report",
    "render_drift_suite_issue_body",
    "render_drift_suite_markdown_summary",
]
