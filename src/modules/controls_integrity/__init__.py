"""Controls and Production Integrity Assessment module.

Deterministic trust assessment contracts (WI-2.1.1), replayable fixtures (WI-2.1.2),
and integrity assessment service (WI-2.1.3).
"""

from .contracts import (
    AssessmentStatus,
    CheckState,
    CheckType,
    ControlCheckResult,
    EvidenceRef,
    FalseSignalRisk,
    IntegrityAssessment,
    NormalizedControlRecord,
    ReasonCode,
    REQUIRED_CHECK_ORDER,
    TrustState,
)
from .fixtures import (
    ControlsIntegrityFixtureIndex,
    ControlsIntegrityFixturePack,
    ControlsIntegrityFixtureSnapshot,
    build_controls_integrity_fixture_index,
    load_controls_integrity_fixture_pack,
    resolve_default_controls_integrity_fixture_path,
)
from .service import get_integrity_assessment

__all__ = [
    "AssessmentStatus",
    "CheckState",
    "CheckType",
    "ControlsIntegrityFixtureIndex",
    "ControlsIntegrityFixturePack",
    "ControlsIntegrityFixtureSnapshot",
    "ControlCheckResult",
    "EvidenceRef",
    "FalseSignalRisk",
    "get_integrity_assessment",
    "IntegrityAssessment",
    "NormalizedControlRecord",
    "ReasonCode",
    "REQUIRED_CHECK_ORDER",
    "TrustState",
    "build_controls_integrity_fixture_index",
    "load_controls_integrity_fixture_pack",
    "resolve_default_controls_integrity_fixture_path",
]
