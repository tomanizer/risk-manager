"""Daily Risk Investigation Orchestrator — skeleton and typed contracts (WI-5.1.1).

Implements:
- Typed enums: HandoffStatus, TerminalRunStatus, ReadinessState, OutcomeKind
- Typed models: DailyRunResult, TargetInvestigationResult, TargetHandoffEntry
- Entry point: start_daily_run (signature only; raises NotImplementedError until WI-5.1.2)
- Run identity: _derive_run_id (deterministic sha256-based derivation per PRD-5.1)

No stage execution logic, telemetry, or adoption matrix changes in this slice (WI-5.1.2–5.1.3).
"""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from src.modules.controls_integrity import IntegrityAssessment, ReasonCode
from src.modules.controls_integrity.fixtures import ControlsIntegrityFixtureIndex
from src.modules.risk_analytics.contracts import MeasureType, NodeRef
from src.modules.risk_analytics.fixtures import FixtureIndex
from src.shared import ServiceError
from src.shared.telemetry import node_ref_log_dict

orchestrator_version: str = "1.0.0"


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class HandoffStatus(StrEnum):
    """Per-target handoff status produced by the challenge gate (Stage 7)."""

    READY_FOR_HANDOFF = "READY_FOR_HANDOFF"
    PROCEED_WITH_CAVEAT = "PROCEED_WITH_CAVEAT"
    HOLD_BLOCKING_TRUST = "HOLD_BLOCKING_TRUST"
    HOLD_UNRESOLVED_TRUST = "HOLD_UNRESOLVED_TRUST"
    HOLD_INVESTIGATION_FAILED = "HOLD_INVESTIGATION_FAILED"


class TerminalRunStatus(StrEnum):
    """Terminal run-level status assigned at Stage 9 (persist).

    Precedence (highest first): BLOCKED_READINESS > FAILED_ALL_TARGETS >
    COMPLETED_WITH_FAILURES > COMPLETED_WITH_CAVEATS > COMPLETED.
    """

    COMPLETED = "COMPLETED"
    COMPLETED_WITH_CAVEATS = "COMPLETED_WITH_CAVEATS"
    COMPLETED_WITH_FAILURES = "COMPLETED_WITH_FAILURES"
    FAILED_ALL_TARGETS = "FAILED_ALL_TARGETS"
    BLOCKED_READINESS = "BLOCKED_READINESS"


class ReadinessState(StrEnum):
    """Readiness gate outcome (Stage 2)."""

    READY = "READY"
    BLOCKED = "BLOCKED"


class OutcomeKind(StrEnum):
    """Discriminator for per-target investigation outcome."""

    ASSESSMENT = "ASSESSMENT"
    SERVICE_ERROR = "SERVICE_ERROR"


# ---------------------------------------------------------------------------
# Typed models
# ---------------------------------------------------------------------------


class TargetInvestigationResult(BaseModel):
    """Per-target investigation result (Stage 6 — synthesis output).

    The upstream typed object is propagated unchanged; the orchestrator must
    not collapse, transform, or summarize it.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    node_ref: NodeRef
    measure_type: MeasureType
    outcome_kind: OutcomeKind
    assessment: IntegrityAssessment | None = None
    service_error: ServiceError | None = None


class TargetHandoffEntry(BaseModel):
    """Per-target handoff entry produced by the challenge gate (Stage 7).

    All reason codes are propagated from upstream typed outputs unchanged;
    no orchestrator-originated codes are added.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    node_ref: NodeRef
    measure_type: MeasureType
    handoff_status: HandoffStatus
    blocking_reason_codes: tuple[ReasonCode, ...] = Field(default_factory=tuple)
    cautionary_reason_codes: tuple[ReasonCode, ...] = Field(default_factory=tuple)
    service_error_status_code: str | None = None


class DailyRunResult(BaseModel):
    """Canonical run-level state object returned by start_daily_run.

    Frozen typed model per ADR-001. All fields required unless noted.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: str
    as_of_date: date
    snapshot_id: str
    measure_type: MeasureType
    candidate_targets: tuple[NodeRef, ...]
    selected_targets: tuple[NodeRef, ...]
    target_results: tuple[TargetInvestigationResult, ...]
    handoff: tuple[TargetHandoffEntry, ...]
    readiness_state: ReadinessState
    readiness_reason_codes: tuple[str, ...]
    terminal_status: TerminalRunStatus
    degraded: bool
    partial: bool
    orchestrator_version: str
    generated_at: datetime


# ---------------------------------------------------------------------------
# Run identity
# ---------------------------------------------------------------------------


def _derive_run_id(
    as_of_date: date,
    snapshot_id: str,
    measure_type: MeasureType,
    candidate_targets: tuple[NodeRef, ...],
) -> str:
    """Derive a deterministic run_id from the canonical replay-determining inputs.

    Derivation (normative, per PRD-5.1 "Run identity"):
    - Components (fixed order): as_of_date ISO string, snapshot_id,
      measure_type.value, list of node_ref_log_dict per candidate_target,
      orchestrator_version.
    - JSON-serialized with sort_keys=True at every dict level.
    - run_id = "drun_" + sha256(serialized_utf8).hexdigest()

    Wall-clock values are excluded; equal inputs always produce equal run_id.
    """
    candidate_log_dicts: list[dict[str, Any]] = [node_ref_log_dict(ref) for ref in candidate_targets]
    components: list[Any] = [
        as_of_date.isoformat(),
        snapshot_id,
        measure_type.value,
        candidate_log_dicts,
        orchestrator_version,
    ]
    serialized = json.dumps(components, sort_keys=True)
    digest = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
    return f"drun_{digest}"


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def start_daily_run(
    as_of_date: date,
    snapshot_id: str,
    candidate_targets: tuple[NodeRef, ...],
    measure_type: MeasureType,
    *,
    risk_fixture_index: FixtureIndex | None = None,
    controls_fixture_index: ControlsIntegrityFixtureIndex | None = None,
) -> DailyRunResult:
    """Run one daily risk investigation end-to-end and return a typed DailyRunResult.

    Stage execution (Stages 1–9) is implemented in WI-5.1.2.
    """
    _derive_run_id(as_of_date, snapshot_id, measure_type, candidate_targets)
    raise NotImplementedError("start_daily_run stage execution is not yet implemented (WI-5.1.2)")
