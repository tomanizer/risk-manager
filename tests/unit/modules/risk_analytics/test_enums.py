"""Enum coverage for risk analytics contracts."""

from __future__ import annotations

import unittest

from src.modules.risk_analytics.contracts import (
    HierarchyScope,
    MeasureType,
    NodeLevel,
    SummaryStatus,
    VolatilityChangeFlag,
    VolatilityRegime,
)


class EnumsTestCase(unittest.TestCase):
    def test_measure_type_values(self) -> None:
        self.assertEqual(
            [member.value for member in MeasureType],
            ["VAR_1D_99", "VAR_10D_99", "ES_97_5"],
        )

    def test_scope_values(self) -> None:
        self.assertEqual(
            [member.value for member in HierarchyScope],
            ["TOP_OF_HOUSE", "LEGAL_ENTITY"],
        )

    def test_node_levels(self) -> None:
        self.assertEqual(
            [member.value for member in NodeLevel],
            ["FIRM", "DIVISION", "AREA", "DESK", "BOOK", "POSITION", "TRADE"],
        )

    def test_status_values(self) -> None:
        self.assertEqual(
            [member.value for member in SummaryStatus],
            [
                "OK",
                "PARTIAL",
                "MISSING_COMPARE",
                "MISSING_HISTORY",
                "MISSING_NODE",
                "MISSING_SNAPSHOT",
                "UNSUPPORTED_MEASURE",
                "DEGRADED",
            ],
        )

    def test_volatility_values(self) -> None:
        self.assertEqual(
            [member.value for member in VolatilityRegime],
            ["LOW", "NORMAL", "ELEVATED", "HIGH", "INSUFFICIENT_HISTORY"],
        )
        self.assertEqual(
            [member.value for member in VolatilityChangeFlag],
            ["STABLE", "RISING", "FALLING", "INSUFFICIENT_HISTORY"],
        )


if __name__ == "__main__":
    unittest.main()
