"""Deterministic service surface for risk analytics."""

from __future__ import annotations

from datetime import date

from .contracts import MeasureType, NodeRef, RiskHistoryPoint, RiskHistorySeries, SummaryStatus
from .fixtures import FixtureIndex, build_fixture_index


def _resolve_fixture_index(fixture_index: FixtureIndex | None) -> FixtureIndex:
    if fixture_index is not None:
        return fixture_index
    return build_fixture_index()


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
            status_reasons=("measure is not available in the canonical fixture pack",),
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
                status_reasons=(f"anchor snapshot {snapshot_id} was not found",),
                service_version=pack.service_version,
            )
        if anchor_snapshot.as_of_date != end_date:
            raise ValueError(
                "snapshot_id must resolve to a snapshot whose as_of_date equals end_date"
            )

    pinned_snapshot = anchor_snapshot or index.get_snapshot_by_date(end_date)
    if pinned_snapshot is None:
        return RiskHistorySeries(
            node_ref=node_ref,
            measure_type=measure_type,
            start_date=start_date,
            end_date=end_date,
            points=(),
            status=SummaryStatus.MISSING_SNAPSHOT,
            status_reasons=(f"no snapshot exists for end_date {end_date.isoformat()}",),
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
            status_reasons=(
                "node and measure do not resolve in the pinned dataset context",
            ),
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
            status_reasons=(
                "node resolves, but zero returnable history points exist in the requested range",
            ),
            service_version=pack.service_version,
        )

    status = SummaryStatus.OK
    status_reasons: list[str] = []

    if degraded_dates:
        status = SummaryStatus.DEGRADED
        status_reasons.append(
            "degraded rows or snapshots present for dates: "
            + ", ".join(day.isoformat() for day in degraded_dates)
        )

    if missing_dates:
        missing_reason = "missing history dates in requested range: " + ", ".join(
            day.isoformat() for day in missing_dates
        )
        if require_complete:
            status = SummaryStatus.DEGRADED
            status_reasons.append("require_complete=true and " + missing_reason)
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
