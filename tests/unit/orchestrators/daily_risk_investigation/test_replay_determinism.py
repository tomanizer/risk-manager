"""WI-5.1.4 — Replay/determinism tests for the start_daily_run public entrypoint.

Closes the remaining public-entrypoint replay gap identified after WI-5.1.3:

- Case 1: Happy-path two-invocation equality — full COMPLETED run.
- Case 2: Blocked-readiness two-invocation equality — BLOCKED_READINESS short-circuit.

Both cases invoke start_daily_run twice with identical
(as_of_date, snapshot_id, candidate_targets, measure_type) arguments and
identical fixture-backed side effects, then assert the two returned
DailyRunResult instances are equal under Pydantic model equality.

Uses only the existing helper-factory pattern already established in
test_stage_ordering.py and test_telemetry.py; no new fixture files or
fixture-index extensions are introduced.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from unittest.mock import patch

from src.modules.controls_integrity import (
    AssessmentStatus,
    CheckState,
    CheckType,
    ControlCheckResult,
    IntegrityAssessment,
    TrustState,
)
from src.modules.controls_integrity.contracts.enums import FalseSignalRisk
from src.modules.risk_analytics.contracts import (
    HierarchyScope,
    MeasureType,
    NodeLevel,
    NodeRef,
    RiskSummary,
)
from src.modules.risk_analytics.contracts.enums import SummaryStatus
from src.orchestrators.daily_risk_investigation import start_daily_run
from src.shared import ServiceError

_AS_OF_DATE = date(2024, 1, 15)
_GENERATED_AT = datetime(2024, 1, 15, 18, 0, 0, tzinfo=timezone.utc)
_SNAPSHOT_ID = "snap-replay-001"

_RISK_PATCH = "src.orchestrators.daily_risk_investigation.orchestrator.get_risk_summary"
_WALKER_PATCH = "src.orchestrators.daily_risk_investigation.orchestrator.assess_integrity"


def _node(node_id: str) -> NodeRef:
    return NodeRef(
        hierarchy_scope=HierarchyScope.TOP_OF_HOUSE,
        legal_entity_id=None,
        node_level=NodeLevel.DESK,
        node_id=node_id,
    )


def _make_risk_summary(node_ref: NodeRef) -> RiskSummary:
    return RiskSummary(
        node_ref=node_ref,
        measure_type=MeasureType.VAR_1D_99,
        as_of_date=_AS_OF_DATE,
        current_value=1.0,
        status=SummaryStatus.OK,
        snapshot_id=_SNAPSHOT_ID,
        data_version="dv-1",
        service_version="sv-1",
        generated_at=_GENERATED_AT,
    )


def _make_assessment(node_ref: NodeRef) -> IntegrityAssessment:
    checks = tuple(
        ControlCheckResult(
            check_type=ct,
            check_state=CheckState.PASS,
            reason_codes=(),
            evidence_refs=(),
        )
        for ct in (
            CheckType.FRESHNESS,
            CheckType.COMPLETENESS,
            CheckType.LINEAGE,
            CheckType.RECONCILIATION,
            CheckType.PUBLICATION_READINESS,
        )
    )
    return IntegrityAssessment(
        node_ref=node_ref,
        measure_type=MeasureType.VAR_1D_99,
        as_of_date=_AS_OF_DATE,
        trust_state=TrustState.TRUSTED,
        false_signal_risk=FalseSignalRisk.LOW,
        assessment_status=AssessmentStatus.OK,
        blocking_reason_codes=(),
        cautionary_reason_codes=(),
        check_results=checks,
        snapshot_id=_SNAPSHOT_ID,
        data_version="dv-1",
        service_version="sv-1",
        generated_at=_GENERATED_AT,
    )


# ---------------------------------------------------------------------------
# Case 1 — Happy-path two-invocation equality
# ---------------------------------------------------------------------------


def test_happy_path_two_invocations_produce_equal_result() -> None:
    """Equal inputs across two calls to start_daily_run yield equal DailyRunResult.

    Exercises the full COMPLETED path through all nine stages. Both invocations
    receive identical (as_of_date, snapshot_id, candidate_targets, measure_type)
    arguments and deterministic fixture-backed side effects; the returned
    DailyRunResult objects must satisfy Pydantic model equality.

    Determinism sources verified:
    - run_id: derived deterministically via _derive_run_id (SHA-256 of fixed inputs).
    - generated_at: max of upstream assessment.generated_at values; all assessments
      carry the same fixed _GENERATED_AT timestamp, so max is stable across calls.
    - All other fields are structural aggregates of the mocked upstream objects.
    """
    candidates = (_node("D-1"), _node("D-2"))

    def risk_side_effect(*, node_ref: NodeRef, **_: object) -> RiskSummary:
        return _make_risk_summary(node_ref)

    def walker_side_effect(node_ref: NodeRef, *_args: object, **_kwargs: object) -> IntegrityAssessment:
        return _make_assessment(node_ref)

    common_kwargs: dict[str, object] = dict(
        as_of_date=_AS_OF_DATE,
        snapshot_id=_SNAPSHOT_ID,
        candidate_targets=candidates,
        measure_type=MeasureType.VAR_1D_99,
    )

    with (
        patch(_RISK_PATCH, side_effect=risk_side_effect),
        patch(_WALKER_PATCH, side_effect=walker_side_effect),
    ):
        result_1 = start_daily_run(**common_kwargs)  # type: ignore[arg-type]

    with (
        patch(_RISK_PATCH, side_effect=risk_side_effect),
        patch(_WALKER_PATCH, side_effect=walker_side_effect),
    ):
        result_2 = start_daily_run(**common_kwargs)  # type: ignore[arg-type]

    assert result_1 == result_2, (
        "start_daily_run must be deterministic on the happy path: two calls with "
        "identical inputs returned non-equal DailyRunResult objects.\n"
        f"result_1={result_1!r}\n"
        f"result_2={result_2!r}"
    )


# ---------------------------------------------------------------------------
# Case 2 — Blocked-readiness two-invocation equality
# ---------------------------------------------------------------------------


def test_blocked_readiness_two_invocations_produce_equal_result() -> None:
    """Equal inputs across two calls to start_daily_run yield equal DailyRunResult
    for the BLOCKED_READINESS short-circuit path (Stages 3–8 skipped).

    Both invocations use a blocking ServiceError from the readiness canary
    (status_code="MISSING_SNAPSHOT"). The walker must never be called on this
    path. The returned DailyRunResult objects must satisfy Pydantic model equality.

    Determinism sources verified:
    - run_id: derived deterministically via _derive_run_id (SHA-256 of fixed inputs).
    - generated_at: 18:00 UTC anchor on as_of_date (no assessments present),
      computed by datetime.combine — no wall-clock dependency.
    - selected_targets, target_results, handoff: all empty tuples on this path.
    """
    candidates = (_node("D-1"), _node("D-2"))
    blocking_error = ServiceError(operation="get_risk_summary", status_code="MISSING_SNAPSHOT")

    common_kwargs: dict[str, object] = dict(
        as_of_date=_AS_OF_DATE,
        snapshot_id=_SNAPSHOT_ID,
        candidate_targets=candidates,
        measure_type=MeasureType.VAR_1D_99,
    )

    with (
        patch(_RISK_PATCH, return_value=blocking_error),
        patch(_WALKER_PATCH) as walker_spy_1,
    ):
        result_1 = start_daily_run(**common_kwargs)  # type: ignore[arg-type]

    assert walker_spy_1.call_count == 0, "walker must not be called on the BLOCKED_READINESS path"

    with (
        patch(_RISK_PATCH, return_value=blocking_error),
        patch(_WALKER_PATCH) as walker_spy_2,
    ):
        result_2 = start_daily_run(**common_kwargs)  # type: ignore[arg-type]

    assert walker_spy_2.call_count == 0, "walker must not be called on the BLOCKED_READINESS path"

    assert result_1 == result_2, (
        "start_daily_run must be deterministic on the BLOCKED_READINESS path: two calls "
        "with identical inputs returned non-equal DailyRunResult objects.\n"
        f"result_1={result_1!r}\n"
        f"result_2={result_2!r}"
    )
