"""Daily Risk Investigation Orchestrator (PRD-5.1).

Slice ownership:
- WI-5.1.1: typed enums, typed models, entry-point signature, run_id derivation.
- WI-5.1.2: end-to-end Stages 1–9 implementation in start_daily_run (this slice).
- WI-5.1.3: telemetry adoption + adoption-matrix flip (deferred).
- WI-5.1.4: replay determinism test set (deferred).
"""

from __future__ import annotations

import hashlib
import json
import time as _time_module
from datetime import date, datetime, time, timezone
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from src.modules.controls_integrity import (
    AssessmentStatus,
    IntegrityAssessment,
    ReasonCode,
    TrustState,
)
from src.modules.controls_integrity.fixtures import ControlsIntegrityFixtureIndex
from src.modules.risk_analytics import get_risk_summary
from src.modules.risk_analytics.contracts import MeasureType, NodeRef
from src.modules.risk_analytics.fixtures import FixtureIndex
from src.shared import ServiceError
from src.shared.telemetry import node_ref_log_dict
from src.walkers.data_controller import assess_integrity

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


# ---------------------------------------------------------------------------
# Stage helpers (private; pure-function for testability)
# ---------------------------------------------------------------------------


_READINESS_BLOCKING_STATUS_CODES: frozenset[str] = frozenset({"MISSING_SNAPSHOT", "UNSUPPORTED_MEASURE"})
_READINESS_CANARY_MISSING_NODE_REASON: str = "READINESS_CANARY_MISSING_NODE"
_GENERATED_AT_FALLBACK_TIME: time = time(hour=18, minute=0, tzinfo=timezone.utc)


def _evaluate_challenge(target_result: TargetInvestigationResult) -> HandoffStatus:
    """Apply the per-target challenge gate (PRD-5.1 §"Per-target gate rules").

    Six rules in fixed precedence; first match wins.
    """
    if target_result.outcome_kind is OutcomeKind.SERVICE_ERROR:
        return HandoffStatus.HOLD_INVESTIGATION_FAILED
    assessment = target_result.assessment
    if assessment is None:
        raise RuntimeError("TargetInvestigationResult outcome_kind=ASSESSMENT requires assessment to be present")
    if assessment.trust_state is TrustState.BLOCKED:
        return HandoffStatus.HOLD_BLOCKING_TRUST
    if assessment.trust_state is TrustState.UNRESOLVED:
        return HandoffStatus.HOLD_UNRESOLVED_TRUST
    if assessment.assessment_status is AssessmentStatus.DEGRADED:
        return HandoffStatus.PROCEED_WITH_CAVEAT
    if assessment.trust_state is TrustState.CAUTION and assessment.assessment_status is AssessmentStatus.OK:
        return HandoffStatus.PROCEED_WITH_CAVEAT
    if assessment.trust_state is TrustState.TRUSTED and assessment.assessment_status is AssessmentStatus.OK:
        return HandoffStatus.READY_FOR_HANDOFF
    raise RuntimeError(
        "challenge gate received unhandled assessment combination: "
        f"trust_state={assessment.trust_state.value} "
        f"assessment_status={assessment.assessment_status.value}"
    )


def _build_handoff_entry(target_result: TargetInvestigationResult) -> TargetHandoffEntry:
    """Construct a TargetHandoffEntry by applying the challenge gate (Stage 7)."""
    handoff_status = _evaluate_challenge(target_result)
    if target_result.outcome_kind is OutcomeKind.SERVICE_ERROR:
        service_error = target_result.service_error
        if service_error is None:
            raise RuntimeError("TargetInvestigationResult outcome_kind=SERVICE_ERROR requires service_error")
        return TargetHandoffEntry(
            node_ref=target_result.node_ref,
            measure_type=target_result.measure_type,
            handoff_status=handoff_status,
            blocking_reason_codes=(),
            cautionary_reason_codes=(),
            service_error_status_code=service_error.status_code,
        )
    assessment = target_result.assessment
    if assessment is None:
        raise RuntimeError("TargetInvestigationResult outcome_kind=ASSESSMENT requires assessment to be present")
    return TargetHandoffEntry(
        node_ref=target_result.node_ref,
        measure_type=target_result.measure_type,
        handoff_status=handoff_status,
        blocking_reason_codes=assessment.blocking_reason_codes,
        cautionary_reason_codes=assessment.cautionary_reason_codes,
        service_error_status_code=None,
    )


def _derive_terminal_status(
    selected_targets: tuple[NodeRef, ...],
    target_results: tuple[TargetInvestigationResult, ...],
    handoff: tuple[TargetHandoffEntry, ...],
) -> TerminalRunStatus:
    """Compute terminal_status per PRD-5.1 §"Terminal states" precedence.

    BLOCKED_READINESS is handled by the readiness short-circuit and is never
    derived here.
    """
    n_total = len(target_results)
    n_service_error = sum(1 for r in target_results if r.outcome_kind is OutcomeKind.SERVICE_ERROR)
    n_assessment = n_total - n_service_error

    if selected_targets and n_service_error == n_total:
        return TerminalRunStatus.FAILED_ALL_TARGETS
    if n_service_error > 0 and n_assessment > 0:
        return TerminalRunStatus.COMPLETED_WITH_FAILURES

    any_degraded = any(
        r.outcome_kind is OutcomeKind.ASSESSMENT and r.assessment is not None and r.assessment.assessment_status is AssessmentStatus.DEGRADED
        for r in target_results
    )
    any_non_ready_for_handoff = any(h.handoff_status is not HandoffStatus.READY_FOR_HANDOFF for h in handoff)
    if selected_targets and (any_degraded or any_non_ready_for_handoff):
        return TerminalRunStatus.COMPLETED_WITH_CAVEATS
    return TerminalRunStatus.COMPLETED


def _derive_generated_at(
    target_results: tuple[TargetInvestigationResult, ...],
    as_of_date: date,
) -> datetime:
    """Compute generated_at per PRD-5.1 §"Replay and determinism".

    Max of upstream IntegrityAssessment.generated_at when at least one assessment
    is present; otherwise the deterministic 18:00 UTC anchor on as_of_date.
    """
    assessment_timestamps = [
        r.assessment.generated_at for r in target_results if r.outcome_kind is OutcomeKind.ASSESSMENT and r.assessment is not None
    ]
    if assessment_timestamps:
        return max(assessment_timestamps)
    return datetime.combine(as_of_date, _GENERATED_AT_FALLBACK_TIME)


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

    Implements Stages 1–9 per PRD-5.1 §"Workflow stages".
    No telemetry in this slice (deferred to WI-5.1.3).
    """
    # Stage 1 — intake
    if snapshot_id is None or not snapshot_id.strip():
        raise ValueError("snapshot_id must be a non-empty string")
    if not candidate_targets:
        raise ValueError("candidate_targets must be a non-empty tuple")

    run_id = _derive_run_id(as_of_date, snapshot_id, measure_type, candidate_targets)
    # Internal monotonic anchor for stage-internal bookkeeping; not part of the
    # returned model. Telemetry adoption (WI-5.1.3) will consume this anchor for
    # operation duration accounting; v1 exists deliberately to keep the surface
    # symmetric with the planned telemetry slice.
    _started_at_monotonic: float = _time_module.monotonic()
    del _started_at_monotonic

    # Stage 2 — readiness_gate (canary call against first candidate)
    canary_outcome = get_risk_summary(
        node_ref=candidate_targets[0],
        measure_type=measure_type,
        as_of_date=as_of_date,
        snapshot_id=snapshot_id,
        fixture_index=risk_fixture_index,
    )
    if isinstance(canary_outcome, ServiceError):
        if canary_outcome.status_code in _READINESS_BLOCKING_STATUS_CODES:
            readiness_state = ReadinessState.BLOCKED
            readiness_reason_codes: tuple[str, ...] = (canary_outcome.status_code,)
        elif canary_outcome.status_code == "MISSING_NODE":
            readiness_state = ReadinessState.READY
            readiness_reason_codes = (_READINESS_CANARY_MISSING_NODE_REASON,)
        else:
            raise RuntimeError(f"readiness gate received unexpected ServiceError status_code={canary_outcome.status_code!r}")
    else:
        readiness_state = ReadinessState.READY
        readiness_reason_codes = ()

    if readiness_state is ReadinessState.BLOCKED:
        # Stages 3–8 are skipped; Stage 9 still runs (terminal-state derivation).
        empty_target_results: tuple[TargetInvestigationResult, ...] = ()
        empty_handoff: tuple[TargetHandoffEntry, ...] = ()
        empty_selected: tuple[NodeRef, ...] = ()
        return DailyRunResult(
            run_id=run_id,
            as_of_date=as_of_date,
            snapshot_id=snapshot_id,
            measure_type=measure_type,
            candidate_targets=candidate_targets,
            selected_targets=empty_selected,
            target_results=empty_target_results,
            handoff=empty_handoff,
            readiness_state=readiness_state,
            readiness_reason_codes=readiness_reason_codes,
            terminal_status=TerminalRunStatus.BLOCKED_READINESS,
            degraded=False,
            partial=False,
            orchestrator_version=orchestrator_version,
            generated_at=_derive_generated_at(empty_target_results, as_of_date),
        )

    # Stage 3 — target_selection (pass-through with MISSING_NODE filter)
    selected_list: list[NodeRef] = []
    for node_ref in candidate_targets:
        selection_outcome = get_risk_summary(
            node_ref=node_ref,
            measure_type=measure_type,
            as_of_date=as_of_date,
            snapshot_id=snapshot_id,
            fixture_index=risk_fixture_index,
        )
        if isinstance(selection_outcome, ServiceError):
            if selection_outcome.status_code == "MISSING_NODE":
                continue
            raise RuntimeError("readiness invariant violated after gate passed")
        selected_list.append(node_ref)
    selected_targets = tuple(selected_list)

    # Stage 4 — target_routing (constant: every selected target → data_controller)
    # No telemetry in this slice; routing is implicit in the Stage 5 call shape.

    # Stage 5 — investigation (one walker call per selected target, sequentially)
    raw_outcomes: list[IntegrityAssessment | ServiceError] = []
    for node_ref in selected_targets:
        # Per PRD-4.1: walker may raise ValueError for invalid inputs; that
        # ValueError must escape unchanged (programmer error, not a workflow outcome).
        walker_outcome = assess_integrity(
            node_ref,
            measure_type,
            as_of_date,
            snapshot_id,
            risk_fixture_index=risk_fixture_index,
            controls_fixture_index=controls_fixture_index,
        )
        raw_outcomes.append(walker_outcome)

    # Stage 6 — synthesis (structural collation; upstream object propagated by reference)
    target_results = tuple(
        TargetInvestigationResult(
            node_ref=node_ref,
            measure_type=measure_type,
            outcome_kind=(OutcomeKind.ASSESSMENT if isinstance(outcome, IntegrityAssessment) else OutcomeKind.SERVICE_ERROR),
            assessment=outcome if isinstance(outcome, IntegrityAssessment) else None,
            service_error=outcome if isinstance(outcome, ServiceError) else None,
        )
        for node_ref, outcome in zip(selected_targets, raw_outcomes, strict=True)
    )

    # Stage 7 — challenge (per-target gate; reason codes propagated unchanged)
    handoff = tuple(_build_handoff_entry(r) for r in target_results)

    # Stage 8 — handoff (structural assembly only; no I/O)

    # Stage 9 — persist
    terminal_status = _derive_terminal_status(selected_targets, target_results, handoff)
    degraded = any(
        r.outcome_kind is OutcomeKind.ASSESSMENT and r.assessment is not None and r.assessment.assessment_status is AssessmentStatus.DEGRADED
        for r in target_results
    )
    has_service_error = any(r.outcome_kind is OutcomeKind.SERVICE_ERROR for r in target_results)
    has_assessment = any(r.outcome_kind is OutcomeKind.ASSESSMENT for r in target_results)
    partial = has_service_error and has_assessment
    generated_at = _derive_generated_at(target_results, as_of_date)

    return DailyRunResult(
        run_id=run_id,
        as_of_date=as_of_date,
        snapshot_id=snapshot_id,
        measure_type=measure_type,
        candidate_targets=candidate_targets,
        selected_targets=selected_targets,
        target_results=target_results,
        handoff=handoff,
        readiness_state=readiness_state,
        readiness_reason_codes=readiness_reason_codes,
        terminal_status=terminal_status,
        degraded=degraded,
        partial=partial,
        orchestrator_version=orchestrator_version,
        generated_at=generated_at,
    )
