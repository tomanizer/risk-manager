"""Canonical business-day resolution for risk analytics."""

from __future__ import annotations

import bisect
from datetime import date
from typing import Iterable


class BusinessDayResolutionError(ValueError):
    """Raised when a canonical calendar cannot resolve a business day."""


def _normalize_calendar(calendar: Iterable[date]) -> tuple[date, ...]:
    normalized = tuple(calendar)
    if not normalized:
        raise BusinessDayResolutionError("calendar must not be empty")
    if any(
        normalized[index] >= normalized[index + 1]
        for index in range(len(normalized) - 1)
    ):
        raise BusinessDayResolutionError(
            "calendar must be sorted ascending and contain no duplicates"
        )
    return normalized


def resolve_prior_business_day(as_of_date: date, calendar: Iterable[date]) -> date:
    normalized = _normalize_calendar(calendar)
    index = bisect.bisect_left(normalized, as_of_date)
    if index >= len(normalized) or normalized[index] != as_of_date:
        raise BusinessDayResolutionError(
            f"as_of_date {as_of_date.isoformat()} is not present in the supplied calendar"
        )

    if index == 0:
        raise BusinessDayResolutionError(
            f"as_of_date {as_of_date.isoformat()} has no prior business day in the supplied calendar"
        )

    return normalized[index - 1]


def resolve_compare_to_date(
    as_of_date: date,
    compare_to_date: date | None,
    calendar: Iterable[date],
) -> date:
    if compare_to_date is not None:
        return compare_to_date
    return resolve_prior_business_day(as_of_date, calendar)
