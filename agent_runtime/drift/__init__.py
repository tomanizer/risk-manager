"""Deterministic drift scanners used by repo-health audits."""

from .architecture_boundaries import ArchitectureBoundaryReport, build_architecture_boundary_report
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
from .surface_liveness import SurfaceLivenessReport, build_surface_liveness_report

__all__ = [
    "ArchitectureBoundaryReport",
    "CanonLineageReport",
    "DependencyHygieneReport",
    "DriftSuiteReport",
    "InstructionSurfaceReport",
    "ReferenceScanReport",
    "RegistryAlignmentReport",
    "SurfaceLivenessReport",
    "build_architecture_boundary_report",
    "build_canon_lineage_report",
    "build_dependency_hygiene_report",
    "build_drift_suite_report",
    "build_instruction_surface_report",
    "build_reference_scan_report",
    "build_registry_alignment_report",
    "build_surface_liveness_report",
    "render_drift_suite_issue_body",
    "render_drift_suite_markdown_summary",
]
