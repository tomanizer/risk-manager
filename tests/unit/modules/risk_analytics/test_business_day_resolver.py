"""Business-day resolver tests."""

from __future__ import annotations

import unittest
from datetime import date

from src.modules.risk_analytics.time import (
    BusinessDayResolutionError,
    resolve_compare_to_date,
    resolve_prior_business_day,
)


CALENDAR = (
    date(2026, 1, 2),
    date(2026, 1, 5),
    date(2026, 1, 6),
    date(2026, 1, 8),
    date(2026, 1, 9),
    date(2026, 1, 12),
)


class BusinessDayResolverTestCase(unittest.TestCase):
    def test_resolve_prior_business_day_uses_calendar_holes(self) -> None:
        self.assertEqual(resolve_prior_business_day(date(2026, 1, 8), CALENDAR), date(2026, 1, 6))

    def test_resolve_compare_to_date_returns_explicit_override(self) -> None:
        self.assertEqual(
            resolve_compare_to_date(
                as_of_date=date(2026, 1, 12),
                compare_to_date=date(2026, 1, 5),
                calendar=CALENDAR,
            ),
            date(2026, 1, 5),
        )

    def test_resolve_prior_business_day_rejects_missing_as_of_date(self) -> None:
        with self.assertRaises(BusinessDayResolutionError):
            resolve_prior_business_day(date(2026, 1, 7), CALENDAR)

    def test_resolve_prior_business_day_rejects_earliest_date(self) -> None:
        with self.assertRaises(BusinessDayResolutionError):
            resolve_prior_business_day(date(2026, 1, 2), CALENDAR)

    def test_resolve_compare_to_date_defaults_to_prior_business_day(self) -> None:
        self.assertEqual(
            resolve_compare_to_date(
                as_of_date=date(2026, 1, 9),
                compare_to_date=None,
                calendar=CALENDAR,
            ),
            date(2026, 1, 8),
        )


if __name__ == "__main__":
    unittest.main()
