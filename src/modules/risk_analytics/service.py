"""Deterministic service surface for risk analytics."""

from __future__ import annotations

import bisect
import statistics
from datetime import date, datetime, time, timezone
from functools import lru_cache

from src.shared import ServiceError

from .contracts import MeasureType, NodeRef, RiskDelta, RiskHistoryPoint, RiskHistorySeries, RiskSummary, SummaryStatus
from .fixtures import FixtureIndex, FixtureRow, FixtureSnapshot, build_fixture_index
from .time import BusinessDayResolutionError, resolve_compare_to_date


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
    outcomes. Raises ValueError for request validation failures.
    """
    if lookback_window != 60:
        raise ValueError("lookback_window must be 60 in v1; any other value is unsupported")
    if snapshot_id is not None and not snapshot_id.strip():
        raise ValueError("snapshot_id must be non-empty when provided")
    if compare_to_date is not None and compare_to_date > as_of_date:
        raise ValueError("compare_to_date must be on or before as_of_date")

    index = _resolve_fixture_index(fixture_index)
    pack = index.pack

    if _resolve_measure_status(measure_type, index) is not None:
        return ServiceError(
            operation="get_risk_summary",
            status_code="UNSUPPORTED_MEASURE",
            status_reasons=("UNSUPPORTED_MEASURE_IN_FIXTURE_PACK",),
        )

    current_snapshot_or_error = _resolve_current_snapshot(as_of_date, snapshot_id, index, operation="get_risk_summary")
    if isinstance(current_snapshot_or_error, ServiceError):
        return current_snapshot_or_error
    current_snapshot = current_snapshot_or_error

    current_row = index.get_row(current_snapshot.snapshot_id, node_ref, measure_type)
    if current_row is None:
        return ServiceError(
            operation="get_risk_summary",
            status_code="MISSING_NODE",
            status_reasons=("CURRENT_NODE_MEASURE_NOT_FOUND_IN_SNAPSHOT",),
        )

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

    status: SummaryStatus
    if current_is_degraded or compare_is_degraded or history_is_degraded:
        status = SummaryStatus.DEGRADED
    elif compare_snapshot is None or previous_row is None:
        status = SummaryStatus.MISSING_COMPARE
    elif no_history:
        status = SummaryStatus.MISSING_HISTORY
    else:
        status = SummaryStatus.OK

    return RiskSummary(
        node_ref=node_ref,
        node_level=node_ref.node_level,
        hierarchy_scope=node_ref.hierarchy_scope,
        legal_entity_id=node_ref.legal_entity_id,
        measure_type=measure_type,
        as_of_date=as_of_date,
        compare_to_date=resolved_compare_date,
        current_value=current_row.value,
        previous_value=None if previous_row is None else previous_row.value,
        delta_abs=None,
        delta_pct=None,
        rolling_mean=rolling_mean,
        rolling_std=rolling_std,
        rolling_min=rolling_min,
        rolling_max=rolling_max,
        history_points_used=n_valid,
        status=status,
        status_reasons=tuple(status_reasons),
        snapshot_id=current_snapshot.snapshot_id,
        data_version=pack.data_version,
        service_version=pack.service_version,
        generated_at=_deterministic_generated_at(current_snapshot.as_of_date),
    )


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
    if snapshot_id is not None and not snapshot_id.strip():
        raise ValueError("snapshot_id must be non-empty when provided")
    if compare_to_date is not None and compare_to_date > as_of_date:
        raise ValueError("compare_to_date must be on or before as_of_date")

    index = _resolve_fixture_index(fixture_index)
    pack = index.pack

    if _resolve_measure_status(measure_type, index) is not None:
        return ServiceError(
            operation="get_risk_delta",
            status_code="UNSUPPORTED_MEASURE",
            status_reasons=("UNSUPPORTED_MEASURE_IN_FIXTURE_PACK",),
        )

    current_snapshot_or_error = _resolve_current_snapshot(as_of_date, snapshot_id, index)
    if isinstance(current_snapshot_or_error, ServiceError):
        return current_snapshot_or_error
    current_snapshot = current_snapshot_or_error

    current_row = index.get_row(current_snapshot.snapshot_id, node_ref, measure_type)
    if current_row is None:
        return ServiceError(
            operation="get_risk_delta",
            status_code="MISSING_NODE",
            status_reasons=("CURRENT_NODE_MEASURE_NOT_FOUND_IN_SNAPSHOT",),
        )

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

    status = SummaryStatus.OK
    if current_is_degraded or compare_is_degraded:
        status = SummaryStatus.DEGRADED
    elif compare_snapshot is None or previous_row is None:
        status = SummaryStatus.MISSING_COMPARE

    return RiskDelta(
        node_ref=node_ref,
        node_level=node_ref.node_level,
        hierarchy_scope=node_ref.hierarchy_scope,
        legal_entity_id=node_ref.legal_entity_id,
        measure_type=measure_type,
        as_of_date=as_of_date,
        compare_to_date=resolved_compare_date,
        current_value=current_row.value,
        previous_value=None if previous_row is None else previous_row.value,
        delta_abs=None,
        delta_pct=None,
        status=status,
        status_reasons=tuple(status_reasons),
        snapshot_id=current_snapshot.snapshot_id,
        data_version=pack.data_version,
        service_version=pack.service_version,
        generated_at=_deterministic_generated_at(current_snapshot.as_of_date),
    )


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
    if start_date > end_date:
        raise ValueError("start_date must be on or before end_date")
    if snapshot_id is not None and not snapshot_id.strip():
        raise ValueError("snapshot_id must be non-empty when provided")

    index = _resolve_fixture_index(fixture_index)
    pack = index.pack

    unsupported_status = _resolve_measure_status(measure_type, index)
    if unsupported_status is not None:
        return RiskHistorySeries(
            node_ref=node_ref,
            measure_type=measure_type,
            start_date=start_date,
            end_date=end_date,
            points=(),
            status=unsupported_status,
            status_reasons=("UNSUPPORTED_MEASURE_IN_FIXTURE_PACK",),
            service_version=pack.service_version,
        )

    anchor_snapshot = None
    if snapshot_id is not None:
        anchor_snapshot = index.get_snapshot(snapshot_id)
        if anchor_snapshot is None:
            return RiskHistorySeries(
                node_ref=node_ref,
                measure_type=measure_type,
                start_date=start_date,
                end_date=end_date,
                points=(),
                status=SummaryStatus.MISSING_SNAPSHOT,
                status_reasons=(f"ANCHOR_SNAPSHOT_NOT_FOUND:{snapshot_id}",),
                service_version=pack.service_version,
            )
        if anchor_snapshot.as_of_date != end_date:
            raise ValueError("snapshot_id must resolve to a snapshot whose as_of_date equals end_date")

    pinned_snapshot = anchor_snapshot or index.get_snapshot_by_date(end_date)
    if pinned_snapshot is None:
        return RiskHistorySeries(
            node_ref=node_ref,
            measure_type=measure_type,
            start_date=start_date,
            end_date=end_date,
            points=(),
            status=SummaryStatus.MISSING_SNAPSHOT,
            status_reasons=(f"END_DATE_SNAPSHOT_NOT_FOUND:{end_date.isoformat()}",),
            service_version=pack.service_version,
        )

    if not _node_measure_exists_in_pinned_context(index, node_ref, measure_type):
        return RiskHistorySeries(
            node_ref=node_ref,
            measure_type=measure_type,
            start_date=start_date,
            end_date=end_date,
            points=(),
            status=SummaryStatus.MISSING_NODE,
            status_reasons=("NODE_MEASURE_NOT_IN_PINNED_DATASET_CONTEXT",),
            service_version=pack.service_version,
        )

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
        return RiskHistorySeries(
            node_ref=node_ref,
            measure_type=measure_type,
            start_date=start_date,
            end_date=end_date,
            points=(),
            status=SummaryStatus.MISSING_HISTORY,
            status_reasons=("NO_RETURNABLE_POINTS_IN_RANGE",),
            service_version=pack.service_version,
        )

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

    return RiskHistorySeries(
        node_ref=node_ref,
        measure_type=measure_type,
        start_date=start_date,
        end_date=end_date,
        points=tuple(points),
        status=status,
        status_reasons=tuple(status_reasons),
        service_version=pack.service_version,
    )
