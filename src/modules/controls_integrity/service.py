"""Deterministic integrity assessment service (PRD-2.1, WI-2.1.3)."""

from __future__ import annotations

from datetime import date, datetime, time, timezone
from functools import lru_cache

from src.shared import ServiceError
from src.shared.telemetry import (
    emit_operation,
    node_ref_log_dict,
    timer_start as _timer_start,
)

from src.modules.risk_analytics.contracts import MeasureType, NodeRef
from src.modules.risk_analytics.fixtures import FixtureIndex, build_fixture_index

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
    ControlsIntegrityFixtureSnapshot,
    build_controls_integrity_fixture_index,
)

_DETERMINISTIC_GENERATED_AT_TIME = time(hour=18, minute=0, tzinfo=timezone.utc)


def _deterministic_generated_at(as_of_date: date) -> datetime:
    return datetime.combine(as_of_date, _DETERMINISTIC_GENERATED_AT_TIME)


@lru_cache(maxsize=1)
def _default_risk_fixture_index() -> FixtureIndex:
    return build_fixture_index()


@lru_cache(maxsize=1)
def _default_controls_fixture_index() -> ControlsIntegrityFixtureIndex:
    return build_controls_integrity_fixture_index()


def _resolve_risk_fixture_index(fixture_index: FixtureIndex | None) -> FixtureIndex:
    if fixture_index is not None:
        return fixture_index
    return _default_risk_fixture_index()


def _resolve_controls_fixture_index(
    fixture_index: ControlsIntegrityFixtureIndex | None,
) -> ControlsIntegrityFixtureIndex:
    if fixture_index is not None:
        return fixture_index
    return _default_controls_fixture_index()


def _operation_log_status(outcome: IntegrityAssessment | ServiceError) -> str:
    """Canonical status string for operation logs (level mapping in shared telemetry)."""
    if isinstance(outcome, ServiceError):
        return outcome.status_code
    return outcome.assessment_status.value


def _emit_integrity_operation(
    operation: str,
    *,
    status: str,
    start_time: float,
    node_ref: NodeRef,
    measure_type: MeasureType,
    as_of_date: date,
    snapshot_id: str | None,
    trust_state: str | None = None,
    assessment_status: str | None = None,
    fail_checks: int | None = None,
    warn_checks: int | None = None,
    unknown_checks: int | None = None,
) -> None:
    """Structured operation log for integrity assessment (no OTel / agent_runtime)."""
    emit_operation(
        operation,
        status=status,
        start_time=start_time,
        include_trace_context=False,
        node_ref=node_ref_log_dict(node_ref),
        measure_type=measure_type,
        as_of_date=as_of_date,
        snapshot_id=snapshot_id,
        trust_state=trust_state,
        assessment_status=assessment_status,
        fail_checks=fail_checks,
        warn_checks=warn_checks,
        unknown_checks=unknown_checks,
    )


def _resolve_controls_snapshot(
    as_of_date: date,
    snapshot_id: str | None,
    index: ControlsIntegrityFixtureIndex,
    *,
    operation: str,
) -> ControlsIntegrityFixtureSnapshot | ServiceError:
    """Resolve pinned or canonical snapshot from the controls fixture index only."""
    if snapshot_id is not None:
        snap = index.get_snapshot(snapshot_id)
        if snap is None:
            return ServiceError(
                operation=operation,
                status_code="MISSING_SNAPSHOT",
                status_reasons=(f"ANCHOR_SNAPSHOT_NOT_FOUND:{snapshot_id}",),
            )
        if snap.as_of_date != as_of_date:
            raise ValueError("snapshot_id must resolve to a snapshot whose as_of_date equals as_of_date")
        return snap

    snap = index.get_snapshot_by_date(as_of_date)
    if snap is None:
        return ServiceError(
            operation=operation,
            status_code="MISSING_SNAPSHOT",
            status_reasons=(f"AS_OF_DATE_SNAPSHOT_NOT_FOUND:{as_of_date.isoformat()}",),
        )
    return snap


def _evidence_refs_for_assessment_output(
    evidence_refs: tuple[EvidenceRef, ...],
    as_of_date: date,
) -> tuple[EvidenceRef, ...]:
    """Refs usable on this assessment: ``source_as_of_date`` null or on/before ``as_of_date`` (PRD-2.1)."""
    return tuple(ref for ref in evidence_refs if ref.source_as_of_date is None or ref.source_as_of_date <= as_of_date)


def _evidence_incomplete_for_assessment(
    check_state: CheckState,
    evidence_refs: tuple[EvidenceRef, ...],
) -> bool:
    """True when WARN/FAIL has no evidence refs left after assessment-date filtering (PRD-2.1)."""
    if check_state not in (CheckState.WARN, CheckState.FAIL):
        return False
    return not evidence_refs


def _merge_reason_codes(
    base: tuple[ReasonCode, ...],
    *extra: ReasonCode,
) -> tuple[ReasonCode, ...]:
    merged = tuple(sorted(set((*base, *extra)), key=lambda c: c.value))
    return merged


def _control_check_from_record(
    record: NormalizedControlRecord | None,
    check_type: CheckType,
    as_of_date: date,
) -> ControlCheckResult:
    """Map a normalized row (or absent row) to a governed ControlCheckResult."""
    if record is None:
        return ControlCheckResult(
            check_type=check_type,
            check_state=CheckState.UNKNOWN,
            reason_codes=(ReasonCode.CHECK_RESULT_MISSING,),
            evidence_refs=(),
        )

    reasons: list[ReasonCode] = list(record.reason_codes)
    if record.is_row_degraded and ReasonCode.CONTROL_ROW_DEGRADED not in reasons:
        reasons.append(ReasonCode.CONTROL_ROW_DEGRADED)

    filtered_evidence = _evidence_refs_for_assessment_output(record.evidence_refs, as_of_date)
    if record.check_state == CheckState.UNKNOWN and not filtered_evidence and record.evidence_refs and ReasonCode.EVIDENCE_REF_MISSING not in reasons:
        reasons.append(ReasonCode.EVIDENCE_REF_MISSING)
    evidence_incomplete = _evidence_incomplete_for_assessment(record.check_state, filtered_evidence)
    if evidence_incomplete and ReasonCode.EVIDENCE_REF_MISSING not in reasons:
        reasons.append(ReasonCode.EVIDENCE_REF_MISSING)

    merged = _merge_reason_codes(tuple(reasons))

    return ControlCheckResult(
        check_type=check_type,
        check_state=record.check_state,
        reason_codes=merged,
        evidence_refs=filtered_evidence,
    )


def _aggregate_trust_state(checks: tuple[ControlCheckResult, ...]) -> TrustState:
    states = [c.check_state for c in checks]
    if CheckState.FAIL in states:
        return TrustState.BLOCKED
    if CheckState.UNKNOWN in states:
        return TrustState.UNRESOLVED
    if CheckState.WARN in states:
        return TrustState.CAUTION
    return TrustState.TRUSTED


def _false_signal_risk(trust: TrustState) -> FalseSignalRisk:
    mapping: dict[TrustState, FalseSignalRisk] = {
        TrustState.BLOCKED: FalseSignalRisk.HIGH,
        TrustState.CAUTION: FalseSignalRisk.MEDIUM,
        TrustState.UNRESOLVED: FalseSignalRisk.UNKNOWN,
        TrustState.TRUSTED: FalseSignalRisk.LOW,
    }
    return mapping[trust]


def _blocking_and_cautionary_codes(
    checks: tuple[ControlCheckResult, ...],
) -> tuple[tuple[ReasonCode, ...], tuple[ReasonCode, ...]]:
    blocking: list[ReasonCode] = []
    cautionary: list[ReasonCode] = []
    for c in checks:
        if c.check_state == CheckState.FAIL:
            blocking.extend(c.reason_codes)
        elif c.check_state in (CheckState.WARN, CheckState.UNKNOWN):
            cautionary.extend(c.reason_codes)
    return (
        tuple(sorted(set(blocking), key=lambda x: x.value)),
        tuple(sorted(set(cautionary), key=lambda x: x.value)),
    )


def _assessment_status_from_checks(
    checks: tuple[ControlCheckResult, ...],
    records: tuple[NormalizedControlRecord | None, ...],
) -> AssessmentStatus:
    """PRD-2.1 rules 6–7 and interaction table."""
    for c in checks:
        if c.check_state == CheckState.UNKNOWN:
            return AssessmentStatus.DEGRADED
        if ReasonCode.EVIDENCE_REF_MISSING in c.reason_codes:
            return AssessmentStatus.DEGRADED

    for rec in records:
        if rec is not None and rec.is_row_degraded:
            return AssessmentStatus.DEGRADED

    return AssessmentStatus.OK


def get_integrity_assessment(
    node_ref: NodeRef,
    measure_type: MeasureType,
    as_of_date: date,
    snapshot_id: str | None = None,
    *,
    risk_fixture_index: FixtureIndex | None = None,
    controls_fixture_index: ControlsIntegrityFixtureIndex | None = None,
) -> IntegrityAssessment | ServiceError:
    """Return one deterministic trust assessment for a single target in a pinned snapshot context.

    Resolves snapshots using ``ControlsIntegrityFixtureIndex`` only (no silent
    fallback from a pinned ``snapshot_id`` to latest). Verifies the target row
    exists in the Phase 1 risk fixture index for the resolved snapshot.

    Returns ``IntegrityAssessment`` when at least one required control record
    exists for the target; ``MISSING_CONTROL_CONTEXT`` when none do.
    """
    start_time = _timer_start()
    operation = "get_integrity_assessment"

    if snapshot_id is not None and not snapshot_id.strip():
        raise ValueError("snapshot_id must be non-empty when provided")

    risk_index = _resolve_risk_fixture_index(risk_fixture_index)
    controls_index = _resolve_controls_fixture_index(controls_fixture_index)
    pack = controls_index.pack

    snap_or_err = _resolve_controls_snapshot(
        as_of_date,
        snapshot_id,
        controls_index,
        operation=operation,
    )
    if isinstance(snap_or_err, ServiceError):
        _emit_integrity_operation(
            operation,
            status=_operation_log_status(snap_or_err),
            start_time=start_time,
            node_ref=node_ref,
            measure_type=measure_type,
            as_of_date=as_of_date,
            snapshot_id=snapshot_id,
        )
        return snap_or_err

    resolved_snapshot = snap_or_err
    resolved_snapshot_id = resolved_snapshot.snapshot_id

    risk_row = risk_index.get_row(resolved_snapshot_id, node_ref, measure_type)
    if risk_row is None:
        err = ServiceError(
            operation=operation,
            status_code="MISSING_NODE",
            status_reasons=("CURRENT_NODE_MEASURE_NOT_FOUND_IN_SNAPSHOT",),
        )
        _emit_integrity_operation(
            operation,
            status=_operation_log_status(err),
            start_time=start_time,
            node_ref=node_ref,
            measure_type=measure_type,
            as_of_date=as_of_date,
            snapshot_id=snapshot_id,
        )
        return err

    raw_records: list[NormalizedControlRecord | None] = []
    for ct in REQUIRED_CHECK_ORDER:
        raw_records.append(
            controls_index.get_record(
                node_ref,
                measure_type,
                as_of_date,
                resolved_snapshot_id,
                ct,
            )
        )
    records_tuple = tuple(raw_records)

    if all(r is None for r in records_tuple):
        err = ServiceError(
            operation=operation,
            status_code="MISSING_CONTROL_CONTEXT",
            status_reasons=("NO_CONTROL_RECORDS_FOR_TARGET_IN_SNAPSHOT",),
        )
        _emit_integrity_operation(
            operation,
            status=_operation_log_status(err),
            start_time=start_time,
            node_ref=node_ref,
            measure_type=measure_type,
            as_of_date=as_of_date,
            snapshot_id=snapshot_id,
        )
        return err

    check_results = tuple(_control_check_from_record(rec, ct, as_of_date) for rec, ct in zip(records_tuple, REQUIRED_CHECK_ORDER, strict=True))

    trust_state = _aggregate_trust_state(check_results)
    false_signal_risk = _false_signal_risk(trust_state)
    blocking_codes, cautionary_codes = _blocking_and_cautionary_codes(check_results)
    assessment_status = _assessment_status_from_checks(check_results, records_tuple)

    fail_n = sum(1 for c in check_results if c.check_state == CheckState.FAIL)
    warn_n = sum(1 for c in check_results if c.check_state == CheckState.WARN)
    unknown_n = sum(1 for c in check_results if c.check_state == CheckState.UNKNOWN)

    assessment = IntegrityAssessment(
        node_ref=node_ref,
        measure_type=measure_type,
        as_of_date=as_of_date,
        trust_state=trust_state,
        false_signal_risk=false_signal_risk,
        assessment_status=assessment_status,
        blocking_reason_codes=blocking_codes,
        cautionary_reason_codes=cautionary_codes,
        check_results=check_results,
        snapshot_id=resolved_snapshot_id,
        data_version=pack.data_version,
        service_version=pack.service_version,
        generated_at=_deterministic_generated_at(resolved_snapshot.as_of_date),
    )

    _emit_integrity_operation(
        operation,
        status=_operation_log_status(assessment),
        start_time=start_time,
        node_ref=node_ref,
        measure_type=measure_type,
        as_of_date=as_of_date,
        snapshot_id=snapshot_id,
        trust_state=trust_state.value,
        assessment_status=assessment_status.value,
        fail_checks=fail_n,
        warn_checks=warn_n,
        unknown_checks=unknown_n,
    )

    return assessment
