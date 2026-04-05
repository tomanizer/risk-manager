"""Canonical business-day resolution for risk analytics."""

from __future__ import annotations

import bisect
from datetime import date


class BusinessDayResolutionError(ValueError):
    """Raised when a canonical calendar cannot resolve a business day."""


def validate_calendar(calendar: tuple[date, ...]) -> tuple[date, ...]:
    """Validate a business-day calendar.

    Returns the input tuple unchanged when it is non-empty and strictly ascending.
    Raises BusinessDayResolutionError if the calendar is empty, unsorted, or
    contains duplicates.
    """
    if not calendar:
        raise BusinessDayResolutionError("calendar must not be empty")
    if any(
        calendar[index] >= calendar[index + 1]
        for index in range(len(calendar) - 1)
    ):
        raise BusinessDayResolutionError(
            "calendar must be sorted ascending and contain no duplicates"
        )
    return calendar


def resolve_prior_business_day(as_of_date: date, calendar: tuple[date, ...]) -> date:
    index = bisect.bisect_left(calendar, as_of_date)
    if index >= len(calendar) or calendar[index] != as_of_date:
        raise BusinessDayResolutionError(
            f"as_of_date {as_of_date.isoformat()} is not present in the supplied calendar"
        )

    if index == 0:
        raise BusinessDayResolutionError(
            f"as_of_date {as_of_date.isoformat()} has no prior business day in the supplied calendar"
        )

    return calendar[index - 1]


def resolve_compare_to_date(
    as_of_date: date,
    compare_to_date: date | None,
    calendar: tuple[date, ...],
) -> date:
    if compare_to_date is not None:
        return compare_to_date
    return resolve_prior_business_day(as_of_date, calendar)
