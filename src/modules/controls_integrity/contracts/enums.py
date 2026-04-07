"""Enumerations for the controls integrity contract layer."""

from __future__ import annotations

from enum import StrEnum


class CheckType(StrEnum):
    """Required check types evaluated in every integrity assessment.

    The canonical order for required checks is:
    FRESHNESS, COMPLETENESS, LINEAGE, RECONCILIATION, PUBLICATION_READINESS.
    """

    FRESHNESS = "FRESHNESS"
    COMPLETENESS = "COMPLETENESS"
    LINEAGE = "LINEAGE"
    RECONCILIATION = "RECONCILIATION"
    PUBLICATION_READINESS = "PUBLICATION_READINESS"


class CheckState(StrEnum):
    """Result state for a single normalized control check."""

    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"


class TrustState(StrEnum):
    """Canonical trust classification for a target integrity assessment."""

    TRUSTED = "TRUSTED"
    CAUTION = "CAUTION"
    BLOCKED = "BLOCKED"
    UNRESOLVED = "UNRESOLVED"


class FalseSignalRisk(StrEnum):
    """False-signal risk level associated with a trust state."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    UNKNOWN = "UNKNOWN"


class AssessmentStatus(StrEnum):
    """Integrity of the returned assessment object itself.

    Distinct from trust_state — describes whether the assessment object
    is fully resolved or carries internal degradation.
    """

    OK = "OK"
    DEGRADED = "DEGRADED"


class ReasonCode(StrEnum):
    """Closed governed v1 vocabulary for reason codes.

    PASS check results carry no reason codes in v1.
    Any addition to this vocabulary requires a PRD update and service_version bump.
    """

    CHECK_RESULT_MISSING = "CHECK_RESULT_MISSING"
    COMPLETENESS_FAIL = "COMPLETENESS_FAIL"
    COMPLETENESS_WARN = "COMPLETENESS_WARN"
    CONTROL_ROW_DEGRADED = "CONTROL_ROW_DEGRADED"
    EVIDENCE_REF_MISSING = "EVIDENCE_REF_MISSING"
    FRESHNESS_FAIL = "FRESHNESS_FAIL"
    FRESHNESS_WARN = "FRESHNESS_WARN"
    LINEAGE_FAIL = "LINEAGE_FAIL"
    LINEAGE_WARN = "LINEAGE_WARN"
    PUBLICATION_READINESS_FAIL = "PUBLICATION_READINESS_FAIL"
    PUBLICATION_READINESS_WARN = "PUBLICATION_READINESS_WARN"
    RECONCILIATION_FAIL = "RECONCILIATION_FAIL"
    RECONCILIATION_WARN = "RECONCILIATION_WARN"
