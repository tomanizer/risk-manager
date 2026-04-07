"""Deterministic service surface for risk analytics."""

from __future__ import annotations

import bisect
import statistics
from datetime import date, datetime, time, timezone
from functools import lru_cache
from typing import Any

from src.shared import ServiceError
from src.shared.telemetry import (
    emit_operation,
    node_ref_log_dict,
    status_string as _status_string,
    timer_start as _timer_start,
)

from .contracts import (
    MeasureType,
    NodeRef,
    RiskChangeProfile,
    RiskDelta,
    RiskHistoryPoint,
    RiskHistorySeries,
    RiskSummary,
    SummaryStatus,
    VolatilityChangeFlag,
    VolatilityRegime,
)
from .fixtures import FixtureIndex, FixtureRow, FixtureSnapshot, build_fixture_index
from .time import BusinessDayResolutionError, resolve_compare_to_date


def _emit_risk_operation(
    operation: str,
    *,
    status: str,
    start_time: float,
    node_ref: NodeRef,
    measure_type: MeasureType,
    **context: Any,
) -> None:
    """WI-1.1.11 logging via shared telemetry; PRD fields only (no trace_id/span_id)."""
    emit_operation(
        operation,
        status=status,
        start_time=start_time,
        include_trace_context=False,
        node_ref=node_ref_log_dict(node_ref),
        measure_type=measure_type,
        **context,
    )


def _emit_risk_history_operation(
    *,
    start_time: float,
    node_ref: NodeRef,
    measure_type: MeasureType,
    start_date: date,
    end_date: date,
    snapshot_id: str | None,
    series: RiskHistorySeries,
) -> None:
    _emit_risk_operation(
        "get_risk_history",
        status=series.status.value,
        start_time=start_time,
        node_ref=node_ref,
        measure_type=measure_type,
        start_date=start_date,
        end_date=end_date,
        snapshot_id=snapshot_id,
    )


_DETERMINISTIC_GENERATED_AT_TIME = time(hour=18, minute=0, tzinfo=timezone.utc)


@lru_cache(maxsize=1)
def _default_fixture_index() -> FixtureIndex:
    return build_fixture_index()


def _resolve_fixture_index(fixture_index: FixtureIndex | None) -> FixtureIndex:
    if fixture_index is not None:
        return fixture_index
    return _default_fixture_index()


def _resolve_measure_status(
    measure_type: MeasureType,
    fixture_index: FixtureIndex,
) -> SummaryStatus | None:
    if measure_type not in fixture_index.supported_measures:
        return SummaryStatus.UNSUPPORTED_MEASURE
    return None


def _expected_dates(
    start_date: date,
    end_date: date,
    calendar: tuple[date, ...],
) -> tuple[date, ...]:
    return tuple(day for day in calendar if start_date <= day <= end_date)


def _node_measure_exists_in_pinned_context(
    fixture_index: FixtureIndex,
    node_ref: NodeRef,
    measure_type: MeasureType,
) -> bool:
    node_key = fixture_index.node_key(node_ref)
    return (node_key, measure_type.value) in fixture_index.available_node_measures


def _encode_dates_reason(reason_code: str, dates: list[date]) -> str:
    return reason_code + ":" + ",".join(day.isoformat() for day in dates)


def _deterministic_generated_at(as_of_date: date) -> datetime:
    return datetime.combine(as_of_date, _DETERMINISTIC_GENERATED_AT_TIME)


def _resolve_current_snapshot(
    as_of_date: date,
    snapshot_id: str | None,
    index: FixtureIndex,
    operation: str = "get_risk_delta",
) -> FixtureSnapshot | ServiceError:
    if snapshot_id is not None:
        snapshot = index.get_snapshot(snapshot_id)
        if snapshot is None:
            return ServiceError(
                operation=operation,
                status_code="MISSING_SNAPSHOT",
                status_reasons=(f"ANCHOR_SNAPSHOT_NOT_FOUND:{snapshot_id}",),
            )
        if snapshot.as_of_date != as_of_date:
            raise ValueError("snapshot_id must resolve to a snapshot whose as_of_date equals as_of_date")
        return snapshot

    snapshot = index.get_snapshot_by_date(as_of_date)
    if snapshot is None:
        return ServiceError(
            operation=operation,
            status_code="MISSING_SNAPSHOT",
            status_reasons=(f"AS_OF_DATE_SNAPSHOT_NOT_FOUND:{as_of_date.isoformat()}",),
        )
    return snapshot


def _resolve_lookback_window_start(
    as_of_date: date,
    lookback_window: int,
    calendar: tuple[date, ...],
) -> date:
    """Return the inclusive start date of a lookback window ending on as_of_date.

    The window is lookback_window business days ending on as_of_date inclusive,
    so the start date is the (lookback_window - 1)th prior business day.
    If as_of_date is not in the calendar or fewer prior days exist, the earliest
    available calendar date is used.
    """
    idx = bisect.bisect_left(calendar, as_of_date)
    if idx >= len(calendar) or calendar[idx] != as_of_date:
        return as_of_date
    start_idx = max(0, idx - (lookback_window - 1))
    return calendar[start_idx]


def _resolve_compare_context(
    as_of_date: date,
    compare_to_date: date | None,
    calendar: tuple[date, ...],
    index: FixtureIndex,
) -> tuple[date | None, FixtureSnapshot | None, tuple[str, ...]]:
    """Resolve the compare date and snapshot.

    Returns (resolved_date, snapshot, reason_codes).
    Raises ValueError for explicit compare_to_date values not in the calendar.
    """
    try:
        resolved = resolve_compare_to_date(
            as_of_date=as_of_date,
            compare_to_date=compare_to_date,
            calendar=calendar,
        )
    except BusinessDayResolutionError:
        if compare_to_date is not None:
            raise ValueError(f"compare_to_date {compare_to_date.isoformat()} is not a business day in the supplied calendar")
        return None, None, (f"NO_PRIOR_BUSINESS_DAY:{as_of_date.isoformat()}",)

    compare_snapshot = index.get_snapshot_by_date(resolved)
    if compare_snapshot is None:
        return resolved, None, (f"COMPARE_SNAPSHOT_NOT_FOUND:{resolved.isoformat()}",)
    return resolved, compare_snapshot, ()


def _compute_delta_fields(
    current_value: float,
    previous_value: float | None,
) -> tuple[float | None, float | None]:
    """Compute first-order delta fields per PRD-1.1-v2 normative semantics."""
    if previous_value is None:
        return None, None

    delta_abs = current_value - previous_value
    if previous_value == 0:
        return delta_abs, None

    return delta_abs, delta_abs / abs(previous_value)


def get_risk_summary(
    node_ref: NodeRef,
    measure_type: MeasureType,
    as_of_date: date,
    compare_to_date: date | None = None,
    lookback_window: int = 60,
    require_complete: bool = False,
    snapshot_id: str | None = None,
    fixture_index: FixtureIndex | None = None,
) -> RiskSummary | ServiceError:
    """Return deterministic summary with rolling statistics for a node and measure.

    Reuses the same first-order retrieval semantics as get_risk_delta without
    divergence in compare-date handling, delta construction, or status precedence.
    Rolling statistics are computed from valid (non-degraded) history points within
    the resolved 60-business-day lookback window ending on as_of_date inclusive.

    Returns a RiskSummary when a current scoped point exists. Returns a typed
    ServiceError for UNSUPPORTED_MEASURE, MISSING_SNAPSHOT, and MISSING_NODE
    outcomes.     Raises ValueError for request validation failures.
    """
    start_time = _timer_start()
    if lookback_window != 60:
        raise ValueError("lookback_window must be 60 in v1; any other value is unsupported")
    if snapshot_id is not None and not snapshot_id.strip():
        raise ValueError("snapshot_id must be non-empty when provided")
    if compare_to_date is not None and compare_to_date > as_of_date:
        raise ValueError("compare_to_date must be on or before as_of_date")

    index = _resolve_fixture_index(fixture_index)
    pack = index.pack

    if _resolve_measure_status(measure_type, index) is not None:
        result = ServiceError(
            operation="get_risk_summary",
            status_code="UNSUPPORTED_MEASURE",
            status_reasons=("UNSUPPORTED_MEASURE_IN_FIXTURE_PACK",),
        )
        _emit_risk_operation(
            "get_risk_summary",
            status=_status_string(result),
            start_time=start_time,
            node_ref=node_ref,
            measure_type=measure_type,
            as_of_date=as_of_date,
            compare_to_date=compare_to_date,
            lookback_window=lookback_window,
            snapshot_id=snapshot_id,
            history_points_used=None,
        )
        return result

    current_snapshot_or_error = _resolve_current_snapshot(as_of_date, snapshot_id, index, operation="get_risk_summary")
    if isinstance(current_snapshot_or_error, ServiceError):
        err = current_snapshot_or_error
        _emit_risk_operation(
            "get_risk_summary",
            status=_status_string(err),
            start_time=start_time,
            node_ref=node_ref,
            measure_type=measure_type,
            as_of_date=as_of_date,
            compare_to_date=compare_to_date,
            lookback_window=lookback_window,
            snapshot_id=snapshot_id,
            history_points_used=None,
        )
        return err
    current_snapshot = current_snapshot_or_error

    current_row = index.get_row(current_snapshot.snapshot_id, node_ref, measure_type)
    if current_row is None:
        result = ServiceError(
            operation="get_risk_summary",
            status_code="MISSING_NODE",
            status_reasons=("CURRENT_NODE_MEASURE_NOT_FOUND_IN_SNAPSHOT",),
        )
        _emit_risk_operation(
            "get_risk_summary",
            status=_status_string(result),
            start_time=start_time,
            node_ref=node_ref,
            measure_type=measure_type,
            as_of_date=as_of_date,
            compare_to_date=compare_to_date,
            lookback_window=lookback_window,
            snapshot_id=snapshot_id,
            history_points_used=None,
        )
        return result

    resolved_compare_date, compare_snapshot, compare_reasons = _resolve_compare_context(
        as_of_date=as_of_date,
        compare_to_date=compare_to_date,
        calendar=pack.calendar,
        index=index,
    )

    window_start = _resolve_lookback_window_start(as_of_date, lookback_window, pack.calendar)
    window_dates = _expected_dates(window_start, as_of_date, pack.calendar)

    valid_values: list[float] = []
    missing_dates: list[date] = []
    degraded_dates: list[date] = []

    for hist_date in window_dates:
        hist_snapshot = index.get_snapshot_by_date(hist_date)
        if hist_snapshot is None:
            missing_dates.append(hist_date)
            continue
        hist_row = index.get_row(hist_snapshot.snapshot_id, node_ref, measure_type)
        if hist_row is None:
            missing_dates.append(hist_date)
            continue
        if hist_snapshot.is_degraded or hist_row.status == SummaryStatus.DEGRADED:
            degraded_dates.append(hist_date)
        else:
            valid_values.append(hist_row.value)

    n_valid = len(valid_values)
    rolling_mean = statistics.mean(valid_values) if n_valid >= 1 else None
    rolling_std = statistics.stdev(valid_values) if n_valid >= 2 else None
    rolling_min = min(valid_values) if n_valid >= 1 else None
    rolling_max = max(valid_values) if n_valid >= 1 else None

    status_reasons: list[str] = []

    current_is_degraded = current_snapshot.is_degraded or current_row.status == SummaryStatus.DEGRADED
    if current_is_degraded:
        status_reasons.append(f"CURRENT_POINT_DEGRADED:{as_of_date.isoformat()}")

    previous_row: FixtureRow | None = None
    compare_is_degraded = False

    if compare_snapshot is None:
        status_reasons.extend(compare_reasons)
    else:
        previous_row = index.get_row(compare_snapshot.snapshot_id, node_ref, measure_type)
        compare_is_degraded = compare_snapshot.is_degraded or (previous_row is not None and previous_row.status == SummaryStatus.DEGRADED)
        if compare_is_degraded:
            status_reasons.append(f"COMPARE_POINT_DEGRADED:{compare_snapshot.as_of_date.isoformat()}")
        if previous_row is None:
            status_reasons.append(f"COMPARE_NODE_MEASURE_NOT_FOUND:{compare_snapshot.as_of_date.isoformat()}")

    if degraded_dates:
        status_reasons.append(_encode_dates_reason("DEGRADED_HISTORY_DATES", degraded_dates))

    if missing_dates:
        if require_complete:
            status_reasons.append(_encode_dates_reason("REQUIRE_COMPLETE_MISSING_DATES", missing_dates))
        else:
            status_reasons.append(_encode_dates_reason("MISSING_HISTORY_DATES", missing_dates))

    # Status precedence: DEGRADED > MISSING_COMPARE > MISSING_HISTORY > OK.
    # Sparse history (missing dates) maps to DEGRADED for RiskSummary rather than PARTIAL.
    history_is_degraded = bool(degraded_dates) or bool(missing_dates)
    no_history = not window_dates or (n_valid == 0 and not degraded_dates and not missing_dates)

    summary_status: SummaryStatus
    if current_is_degraded or compare_is_degraded or history_is_degraded:
        summary_status = SummaryStatus.DEGRADED
    elif compare_snapshot is None or previous_row is None:
        summary_status = SummaryStatus.MISSING_COMPARE
    elif no_history:
        summary_status = SummaryStatus.MISSING_HISTORY
    else:
        summary_status = SummaryStatus.OK

    previous_value = None if previous_row is None else previous_row.value
    delta_abs, delta_pct = _compute_delta_fields(
        current_value=current_row.value,
        previous_value=previous_value,
    )

    summary = RiskSummary(
        node_ref=node_ref,
        node_level=node_ref.node_level,
        hierarchy_scope=node_ref.hierarchy_scope,
        legal_entity_id=node_ref.legal_entity_id,
        measure_type=measure_type,
        as_of_date=as_of_date,
        compare_to_date=resolved_compare_date,
        current_value=current_row.value,
        previous_value=previous_value,
        delta_abs=delta_abs,
        delta_pct=delta_pct,
        rolling_mean=rolling_mean,
        rolling_std=rolling_std,
        rolling_min=rolling_min,
        rolling_max=rolling_max,
        history_points_used=n_valid,
        status=summary_status,
        status_reasons=tuple(status_reasons),
        snapshot_id=current_snapshot.snapshot_id,
        data_version=pack.data_version,
        service_version=pack.service_version,
        generated_at=_deterministic_generated_at(current_snapshot.as_of_date),
    )
    _emit_risk_operation(
        "get_risk_summary",
        status=_status_string(summary),
        start_time=start_time,
        node_ref=node_ref,
        measure_type=measure_type,
        as_of_date=as_of_date,
        compare_to_date=summary.compare_to_date,
        lookback_window=lookback_window,
        snapshot_id=snapshot_id,
        history_points_used=summary.history_points_used,
    )
    return summary


def get_risk_delta(
    node_ref: NodeRef,
    measure_type: MeasureType,
    as_of_date: date,
    compare_to_date: date | None = None,
    snapshot_id: str | None = None,
    fixture_index: FixtureIndex | None = None,
) -> RiskDelta | ServiceError:
    """Return deterministic first-order delta retrieval for a node and measure.

    Returns a RiskDelta when a current scoped point exists and all required fields
    can be populated honestly. Returns a typed ServiceError for UNSUPPORTED_MEASURE,
    MISSING_SNAPSHOT, and MISSING_NODE outcomes. Raises ValueError for request
    validation failures such as blank snapshot_id or compare_to_date not in calendar.
    """
    start_time = _timer_start()
    if snapshot_id is not None and not snapshot_id.strip():
        raise ValueError("snapshot_id must be non-empty when provided")
    if compare_to_date is not None and compare_to_date > as_of_date:
        raise ValueError("compare_to_date must be on or before as_of_date")

    index = _resolve_fixture_index(fixture_index)
    pack = index.pack

    if _resolve_measure_status(measure_type, index) is not None:
        result = ServiceError(
            operation="get_risk_delta",
            status_code="UNSUPPORTED_MEASURE",
            status_reasons=("UNSUPPORTED_MEASURE_IN_FIXTURE_PACK",),
        )
        _emit_risk_operation(
            "get_risk_delta",
            status=_status_string(result),
            start_time=start_time,
            node_ref=node_ref,
            measure_type=measure_type,
            as_of_date=as_of_date,
            compare_to_date=compare_to_date,
            snapshot_id=snapshot_id,
        )
        return result

    current_snapshot_or_error = _resolve_current_snapshot(as_of_date, snapshot_id, index)
    if isinstance(current_snapshot_or_error, ServiceError):
        err = current_snapshot_or_error
        _emit_risk_operation(
            "get_risk_delta",
            status=_status_string(err),
            start_time=start_time,
            node_ref=node_ref,
            measure_type=measure_type,
            as_of_date=as_of_date,
            compare_to_date=compare_to_date,
            snapshot_id=snapshot_id,
        )
        return err
    current_snapshot = current_snapshot_or_error

    current_row = index.get_row(current_snapshot.snapshot_id, node_ref, measure_type)
    if current_row is None:
        result = ServiceError(
            operation="get_risk_delta",
            status_code="MISSING_NODE",
            status_reasons=("CURRENT_NODE_MEASURE_NOT_FOUND_IN_SNAPSHOT",),
        )
        _emit_risk_operation(
            "get_risk_delta",
            status=_status_string(result),
            start_time=start_time,
            node_ref=node_ref,
            measure_type=measure_type,
            as_of_date=as_of_date,
            compare_to_date=compare_to_date,
            snapshot_id=snapshot_id,
        )
        return result

    resolved_compare_date, compare_snapshot, compare_reasons = _resolve_compare_context(
        as_of_date=as_of_date,
        compare_to_date=compare_to_date,
        calendar=pack.calendar,
        index=index,
    )

    status_reasons: list[str] = []
    current_is_degraded = current_snapshot.is_degraded or current_row.status == SummaryStatus.DEGRADED
    if current_is_degraded:
        status_reasons.append(f"CURRENT_POINT_DEGRADED:{as_of_date.isoformat()}")

    previous_row: FixtureRow | None = None
    compare_is_degraded = False

    if compare_snapshot is None:
        status_reasons.extend(compare_reasons)
    else:
        previous_row = index.get_row(compare_snapshot.snapshot_id, node_ref, measure_type)
        compare_is_degraded = compare_snapshot.is_degraded or (previous_row is not None and previous_row.status == SummaryStatus.DEGRADED)
        if compare_is_degraded:
            status_reasons.append(f"COMPARE_POINT_DEGRADED:{compare_snapshot.as_of_date.isoformat()}")
        if previous_row is None:
            status_reasons.append(f"COMPARE_NODE_MEASURE_NOT_FOUND:{compare_snapshot.as_of_date.isoformat()}")

    delta_status = SummaryStatus.OK
    if current_is_degraded or compare_is_degraded:
        delta_status = SummaryStatus.DEGRADED
    elif compare_snapshot is None or previous_row is None:
        delta_status = SummaryStatus.MISSING_COMPARE

    previous_value = None if previous_row is None else previous_row.value
    delta_abs, delta_pct = _compute_delta_fields(
        current_value=current_row.value,
        previous_value=previous_value,
    )

    delta = RiskDelta(
        node_ref=node_ref,
        node_level=node_ref.node_level,
        hierarchy_scope=node_ref.hierarchy_scope,
        legal_entity_id=node_ref.legal_entity_id,
        measure_type=measure_type,
        as_of_date=as_of_date,
        compare_to_date=resolved_compare_date,
        current_value=current_row.value,
        previous_value=previous_value,
        delta_abs=delta_abs,
        delta_pct=delta_pct,
        status=delta_status,
        status_reasons=tuple(status_reasons),
        snapshot_id=current_snapshot.snapshot_id,
        data_version=pack.data_version,
        service_version=pack.service_version,
        generated_at=_deterministic_generated_at(current_snapshot.as_of_date),
    )
    _emit_risk_operation(
        "get_risk_delta",
        status=_status_string(delta),
        start_time=start_time,
        node_ref=node_ref,
        measure_type=measure_type,
        as_of_date=as_of_date,
        compare_to_date=delta.compare_to_date,
        snapshot_id=snapshot_id,
    )
    return delta


def get_risk_history(
    node_ref: NodeRef,
    measure_type: MeasureType,
    start_date: date,
    end_date: date,
    require_complete: bool = False,
    snapshot_id: str | None = None,
    fixture_index: FixtureIndex | None = None,
) -> RiskHistorySeries:
    """Return deterministic dated history for a node and measure.

    The request is anchored to `end_date` or to the explicit anchor snapshot when
    `snapshot_id` is provided. Node resolution is performed against the broader
    pinned fixture-backed dataset context for that request, while returned points
    remain restricted to the inclusive requested range.
    """
    start_time = _timer_start()
    if start_date > end_date:
        raise ValueError("start_date must be on or before end_date")
    if snapshot_id is not None and not snapshot_id.strip():
        raise ValueError("snapshot_id must be non-empty when provided")

    index = _resolve_fixture_index(fixture_index)
    pack = index.pack

    unsupported_status = _resolve_measure_status(measure_type, index)
    if unsupported_status is not None:
        series = RiskHistorySeries(
            node_ref=node_ref,
            measure_type=measure_type,
            start_date=start_date,
            end_date=end_date,
            points=(),
            status=unsupported_status,
            status_reasons=("UNSUPPORTED_MEASURE_IN_FIXTURE_PACK",),
            service_version=pack.service_version,
        )
        _emit_risk_history_operation(
            start_time=start_time,
            node_ref=node_ref,
            measure_type=measure_type,
            start_date=start_date,
            end_date=end_date,
            snapshot_id=snapshot_id,
            series=series,
        )
        return series

    anchor_snapshot = None
    if snapshot_id is not None:
        anchor_snapshot = index.get_snapshot(snapshot_id)
        if anchor_snapshot is None:
            series = RiskHistorySeries(
                node_ref=node_ref,
                measure_type=measure_type,
                start_date=start_date,
                end_date=end_date,
                points=(),
                status=SummaryStatus.MISSING_SNAPSHOT,
                status_reasons=(f"ANCHOR_SNAPSHOT_NOT_FOUND:{snapshot_id}",),
                service_version=pack.service_version,
            )
            _emit_risk_history_operation(
                start_time=start_time,
                node_ref=node_ref,
                measure_type=measure_type,
                start_date=start_date,
                end_date=end_date,
                snapshot_id=snapshot_id,
                series=series,
            )
            return series
        if anchor_snapshot.as_of_date != end_date:
            raise ValueError("snapshot_id must resolve to a snapshot whose as_of_date equals end_date")

    pinned_snapshot = anchor_snapshot or index.get_snapshot_by_date(end_date)
    if pinned_snapshot is None:
        series = RiskHistorySeries(
            node_ref=node_ref,
            measure_type=measure_type,
            start_date=start_date,
            end_date=end_date,
            points=(),
            status=SummaryStatus.MISSING_SNAPSHOT,
            status_reasons=(f"END_DATE_SNAPSHOT_NOT_FOUND:{end_date.isoformat()}",),
            service_version=pack.service_version,
        )
        _emit_risk_history_operation(
            start_time=start_time,
            node_ref=node_ref,
            measure_type=measure_type,
            start_date=start_date,
            end_date=end_date,
            snapshot_id=snapshot_id,
            series=series,
        )
        return series

    if not _node_measure_exists_in_pinned_context(index, node_ref, measure_type):
        series = RiskHistorySeries(
            node_ref=node_ref,
            measure_type=measure_type,
            start_date=start_date,
            end_date=end_date,
            points=(),
            status=SummaryStatus.MISSING_NODE,
            status_reasons=("NODE_MEASURE_NOT_IN_PINNED_DATASET_CONTEXT",),
            service_version=pack.service_version,
        )
        _emit_risk_history_operation(
            start_time=start_time,
            node_ref=node_ref,
            measure_type=measure_type,
            start_date=start_date,
            end_date=end_date,
            snapshot_id=snapshot_id,
            series=series,
        )
        return series

    expected_dates = _expected_dates(start_date, end_date, pack.calendar)
    points: list[RiskHistoryPoint] = []
    missing_dates: list[date] = []
    degraded_dates: list[date] = []

    for as_of_date in expected_dates:
        snapshot = index.get_snapshot_by_date(as_of_date)
        if snapshot is None:
            missing_dates.append(as_of_date)
            continue

        row = index.get_row(snapshot.snapshot_id, node_ref, measure_type)
        if row is None:
            missing_dates.append(as_of_date)
            continue

        if snapshot.is_degraded or row.status == SummaryStatus.DEGRADED:
            degraded_dates.append(as_of_date)

        points.append(
            RiskHistoryPoint(
                node_ref=node_ref,
                measure_type=measure_type,
                date=as_of_date,
                value=row.value,
                snapshot_id=snapshot.snapshot_id,
                status=SummaryStatus.DEGRADED if snapshot.is_degraded else row.status,
            )
        )

    if not points:
        series = RiskHistorySeries(
            node_ref=node_ref,
            measure_type=measure_type,
            start_date=start_date,
            end_date=end_date,
            points=(),
            status=SummaryStatus.MISSING_HISTORY,
            status_reasons=("NO_RETURNABLE_POINTS_IN_RANGE",),
            service_version=pack.service_version,
        )
        _emit_risk_history_operation(
            start_time=start_time,
            node_ref=node_ref,
            measure_type=measure_type,
            start_date=start_date,
            end_date=end_date,
            snapshot_id=snapshot_id,
            series=series,
        )
        return series

    status = SummaryStatus.OK
    status_reasons: list[str] = []

    if degraded_dates:
        status = SummaryStatus.DEGRADED
        status_reasons.append(_encode_dates_reason("DEGRADED_DATES", degraded_dates))

    if missing_dates:
        missing_reason = _encode_dates_reason("MISSING_DATES", missing_dates)
        if require_complete:
            status = SummaryStatus.DEGRADED
            status_reasons.append(_encode_dates_reason("REQUIRE_COMPLETE_MISSING_DATES", missing_dates))
        elif status is SummaryStatus.OK:
            status = SummaryStatus.PARTIAL
            status_reasons.append(missing_reason)
        else:
            status_reasons.append(missing_reason)

    series = RiskHistorySeries(
        node_ref=node_ref,
        measure_type=measure_type,
        start_date=start_date,
        end_date=end_date,
        points=tuple(points),
        status=status,
        status_reasons=tuple(status_reasons),
        service_version=pack.service_version,
    )
    _emit_risk_history_operation(
        start_time=start_time,
        node_ref=node_ref,
        measure_type=measure_type,
        start_date=start_date,
        end_date=end_date,
        snapshot_id=snapshot_id,
        series=series,
    )
    return series


# Volatility policy constants — VOLATILITY_RULES_V1.
# Any change to these values requires a service_version bump.
_BASELINE_WINDOW = 60
_SHORT_WINDOW = 10
_REGIME_MIN_BASELINE_POINTS = 20
_CHANGE_FLAG_MIN_SHORT_POINTS = 5
_CHANGE_FLAG_MIN_BASELINE_POINTS = 20


def _classify_volatility_regime(
    current_value: float,
    rolling_mean: float,
    rolling_std: float,
    n_valid: int,
) -> VolatilityRegime:
    """Derive volatility_regime per VOLATILITY_RULES_V1 regime calculation."""
    if n_valid < _REGIME_MIN_BASELINE_POINTS:
        return VolatilityRegime.INSUFFICIENT_HISTORY

    reference_level = max(abs(current_value), abs(rolling_mean))
    if reference_level == 0.0:
        return VolatilityRegime.LOW if rolling_std == 0.0 else VolatilityRegime.HIGH

    volatility_ratio = rolling_std / reference_level
    if volatility_ratio < 0.05:
        return VolatilityRegime.LOW
    if volatility_ratio < 0.15:
        return VolatilityRegime.NORMAL
    if volatility_ratio < 0.30:
        return VolatilityRegime.ELEVATED
    return VolatilityRegime.HIGH


def _classify_volatility_change_flag(
    short_std: float | None,
    baseline_std: float | None,
    n_short_valid: int,
    n_baseline_valid: int,
) -> VolatilityChangeFlag:
    """Derive volatility_change_flag per VOLATILITY_RULES_V1 change-flag calculation."""
    if n_short_valid < _CHANGE_FLAG_MIN_SHORT_POINTS or n_baseline_valid < _CHANGE_FLAG_MIN_BASELINE_POINTS:
        return VolatilityChangeFlag.INSUFFICIENT_HISTORY

    # Both stds are defined when their respective valid-point counts are >= 2.
    # With n_short_valid >= 5 and n_baseline_valid >= 20, both stds are well-defined.
    # Treat None as 0.0 defensively (not reachable under normal conditions).
    s_short = short_std if short_std is not None else 0.0
    s_baseline = baseline_std if baseline_std is not None else 0.0

    if s_baseline == 0.0:
        # Defensive: mathematically unreachable from normal data (short ⊆ baseline)
        # if baseline_std==0 then short_std must also be 0, but handled defensively.
        return VolatilityChangeFlag.STABLE if s_short == 0.0 else VolatilityChangeFlag.RISING

    dispersion_change_ratio = s_short / s_baseline
    if dispersion_change_ratio <= 0.80:
        return VolatilityChangeFlag.FALLING
    if dispersion_change_ratio < 1.20:
        return VolatilityChangeFlag.STABLE
    return VolatilityChangeFlag.RISING


def get_risk_change_profile(
    node_ref: NodeRef,
    measure_type: MeasureType,
    as_of_date: date,
    compare_to_date: date | None = None,
    lookback_window: int = _BASELINE_WINDOW,
    require_complete: bool = False,
    snapshot_id: str | None = None,
    fixture_index: FixtureIndex | None = None,
) -> RiskChangeProfile | ServiceError:
    """Return first-order delta plus second-order volatility context for a node and measure.

    Mirrors get_risk_summary for all first-order retrieval semantics: compare-date
    handling, delta construction, rolling stats, and status precedence. Adds
    volatility_regime and volatility_change_flag derived from the governed
    VOLATILITY_RULES_V1 policy (baseline_window=60, short_window=10, business-day
    basis, inclusive anchor on as_of_date).

    Returns a RiskChangeProfile when a current scoped point exists. Returns a typed
    ServiceError for UNSUPPORTED_MEASURE, MISSING_SNAPSHOT, and MISSING_NODE outcomes.
    Raises ValueError for request validation failures.
    """
    start_time = _timer_start()
    if lookback_window != _BASELINE_WINDOW:
        raise ValueError(f"lookback_window must be {_BASELINE_WINDOW} in v1; any other value is unsupported")
    if snapshot_id is not None and not snapshot_id.strip():
        raise ValueError("snapshot_id must be non-empty when provided")
    if compare_to_date is not None and compare_to_date > as_of_date:
        raise ValueError("compare_to_date must be on or before as_of_date")

    index = _resolve_fixture_index(fixture_index)
    pack = index.pack

    if _resolve_measure_status(measure_type, index) is not None:
        result = ServiceError(
            operation="get_risk_change_profile",
            status_code="UNSUPPORTED_MEASURE",
            status_reasons=("UNSUPPORTED_MEASURE_IN_FIXTURE_PACK",),
        )
        _emit_risk_operation(
            "get_risk_change_profile",
            status=_status_string(result),
            start_time=start_time,
            node_ref=node_ref,
            measure_type=measure_type,
            as_of_date=as_of_date,
            compare_to_date=compare_to_date,
            lookback_window=lookback_window,
            snapshot_id=snapshot_id,
            history_points_used=None,
        )
        return result

    current_snapshot_or_error = _resolve_current_snapshot(as_of_date, snapshot_id, index, operation="get_risk_change_profile")
    if isinstance(current_snapshot_or_error, ServiceError):
        err = current_snapshot_or_error
        _emit_risk_operation(
            "get_risk_change_profile",
            status=_status_string(err),
            start_time=start_time,
            node_ref=node_ref,
            measure_type=measure_type,
            as_of_date=as_of_date,
            compare_to_date=compare_to_date,
            lookback_window=lookback_window,
            snapshot_id=snapshot_id,
            history_points_used=None,
        )
        return err
    current_snapshot = current_snapshot_or_error

    current_row = index.get_row(current_snapshot.snapshot_id, node_ref, measure_type)
    if current_row is None:
        result = ServiceError(
            operation="get_risk_change_profile",
            status_code="MISSING_NODE",
            status_reasons=("CURRENT_NODE_MEASURE_NOT_FOUND_IN_SNAPSHOT",),
        )
        _emit_risk_operation(
            "get_risk_change_profile",
            status=_status_string(result),
            start_time=start_time,
            node_ref=node_ref,
            measure_type=measure_type,
            as_of_date=as_of_date,
            compare_to_date=compare_to_date,
            lookback_window=lookback_window,
            snapshot_id=snapshot_id,
            history_points_used=None,
        )
        return result

    resolved_compare_date, compare_snapshot, compare_reasons = _resolve_compare_context(
        as_of_date=as_of_date,
        compare_to_date=compare_to_date,
        calendar=pack.calendar,
        index=index,
    )

    # Baseline window (60 business days inclusive of as_of_date).
    baseline_start = _resolve_lookback_window_start(as_of_date, _BASELINE_WINDOW, pack.calendar)
    baseline_dates = _expected_dates(baseline_start, as_of_date, pack.calendar)

    valid_values: list[float] = []
    missing_dates: list[date] = []
    degraded_dates: list[date] = []

    for hist_date in baseline_dates:
        hist_snapshot = index.get_snapshot_by_date(hist_date)
        if hist_snapshot is None:
            missing_dates.append(hist_date)
            continue
        hist_row = index.get_row(hist_snapshot.snapshot_id, node_ref, measure_type)
        if hist_row is None:
            missing_dates.append(hist_date)
            continue
        if hist_snapshot.is_degraded or hist_row.status == SummaryStatus.DEGRADED:
            degraded_dates.append(hist_date)
        else:
            valid_values.append(hist_row.value)

    n_valid = len(valid_values)
    rolling_mean = statistics.mean(valid_values) if n_valid >= 1 else None
    rolling_std = statistics.stdev(valid_values) if n_valid >= 2 else None
    rolling_min = min(valid_values) if n_valid >= 1 else None
    rolling_max = max(valid_values) if n_valid >= 1 else None

    # Short window (10 business days inclusive of as_of_date, per VOLATILITY_RULES_V1).
    short_start = _resolve_lookback_window_start(as_of_date, _SHORT_WINDOW, pack.calendar)
    short_dates = _expected_dates(short_start, as_of_date, pack.calendar)

    short_valid_values: list[float] = []
    for hist_date in short_dates:
        hist_snapshot = index.get_snapshot_by_date(hist_date)
        if hist_snapshot is None:
            continue
        hist_row = index.get_row(hist_snapshot.snapshot_id, node_ref, measure_type)
        if hist_row is None:
            continue
        if not (hist_snapshot.is_degraded or hist_row.status == SummaryStatus.DEGRADED):
            short_valid_values.append(hist_row.value)

    n_short_valid = len(short_valid_values)
    short_std = statistics.stdev(short_valid_values) if n_short_valid >= 2 else None

    volatility_regime = _classify_volatility_regime(
        current_value=current_row.value,
        rolling_mean=rolling_mean if rolling_mean is not None else 0.0,
        rolling_std=rolling_std if rolling_std is not None else 0.0,
        n_valid=n_valid,
    )
    volatility_change_flag = _classify_volatility_change_flag(
        short_std=short_std,
        baseline_std=rolling_std,
        n_short_valid=n_short_valid,
        n_baseline_valid=n_valid,
    )

    status_reasons: list[str] = []

    current_is_degraded = current_snapshot.is_degraded or current_row.status == SummaryStatus.DEGRADED
    if current_is_degraded:
        status_reasons.append(f"CURRENT_POINT_DEGRADED:{as_of_date.isoformat()}")

    previous_row: FixtureRow | None = None
    compare_is_degraded = False

    if compare_snapshot is None:
        status_reasons.extend(compare_reasons)
    else:
        previous_row = index.get_row(compare_snapshot.snapshot_id, node_ref, measure_type)
        compare_is_degraded = compare_snapshot.is_degraded or (previous_row is not None and previous_row.status == SummaryStatus.DEGRADED)
        if compare_is_degraded:
            status_reasons.append(f"COMPARE_POINT_DEGRADED:{compare_snapshot.as_of_date.isoformat()}")
        if previous_row is None:
            status_reasons.append(f"COMPARE_NODE_MEASURE_NOT_FOUND:{compare_snapshot.as_of_date.isoformat()}")

    if degraded_dates:
        status_reasons.append(_encode_dates_reason("DEGRADED_HISTORY_DATES", degraded_dates))

    if missing_dates:
        if require_complete:
            status_reasons.append(_encode_dates_reason("REQUIRE_COMPLETE_MISSING_DATES", missing_dates))
        else:
            status_reasons.append(_encode_dates_reason("MISSING_HISTORY_DATES", missing_dates))

    # Status precedence: DEGRADED > MISSING_COMPARE > MISSING_HISTORY > OK.
    history_is_degraded = bool(degraded_dates) or bool(missing_dates)
    no_history = not baseline_dates or (n_valid == 0 and not degraded_dates and not missing_dates)

    profile_status: SummaryStatus
    if current_is_degraded or compare_is_degraded or history_is_degraded:
        profile_status = SummaryStatus.DEGRADED
    elif compare_snapshot is None or previous_row is None:
        profile_status = SummaryStatus.MISSING_COMPARE
    elif no_history:
        profile_status = SummaryStatus.MISSING_HISTORY
    else:
        profile_status = SummaryStatus.OK

    previous_value = None if previous_row is None else previous_row.value
    delta_abs, delta_pct = _compute_delta_fields(
        current_value=current_row.value,
        previous_value=previous_value,
    )

    profile = RiskChangeProfile(
        node_ref=node_ref,
        node_level=node_ref.node_level,
        hierarchy_scope=node_ref.hierarchy_scope,
        legal_entity_id=node_ref.legal_entity_id,
        measure_type=measure_type,
        as_of_date=as_of_date,
        compare_to_date=resolved_compare_date,
        current_value=current_row.value,
        previous_value=previous_value,
        delta_abs=delta_abs,
        delta_pct=delta_pct,
        rolling_mean=rolling_mean,
        rolling_std=rolling_std,
        rolling_min=rolling_min,
        rolling_max=rolling_max,
        volatility_regime=volatility_regime,
        volatility_change_flag=volatility_change_flag,
        history_points_used=n_valid,
        status=profile_status,
        status_reasons=tuple(status_reasons),
        snapshot_id=current_snapshot.snapshot_id,
        data_version=pack.data_version,
        service_version=pack.service_version,
        generated_at=_deterministic_generated_at(current_snapshot.as_of_date),
    )
    _emit_risk_operation(
        "get_risk_change_profile",
        status=_status_string(profile),
        start_time=start_time,
        node_ref=node_ref,
        measure_type=measure_type,
        as_of_date=as_of_date,
        compare_to_date=profile.compare_to_date,
        lookback_window=lookback_window,
        snapshot_id=snapshot_id,
        history_points_used=profile.history_points_used,
    )
    return profile
