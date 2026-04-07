"""Enum value coverage for the controls integrity contract layer."""

from __future__ import annotations

import unittest

from src.modules.controls_integrity.contracts import (
    AssessmentStatus,
    CheckState,
    CheckType,
    FalseSignalRisk,
    ReasonCode,
    TrustState,
)


class CheckTypeEnumTest(unittest.TestCase):
    def test_check_type_values_and_order(self) -> None:
        self.assertEqual(
            [m.value for m in CheckType],
            [
                "FRESHNESS",
                "COMPLETENESS",
                "LINEAGE",
                "RECONCILIATION",
                "PUBLICATION_READINESS",
            ],
        )

    def test_check_type_count(self) -> None:
        self.assertEqual(len(CheckType), 5)


class CheckStateEnumTest(unittest.TestCase):
    def test_check_state_values(self) -> None:
        self.assertEqual(
            [m.value for m in CheckState],
            ["PASS", "WARN", "FAIL", "UNKNOWN"],
        )


class TrustStateEnumTest(unittest.TestCase):
    def test_trust_state_values(self) -> None:
        self.assertEqual(
            [m.value for m in TrustState],
            ["TRUSTED", "CAUTION", "BLOCKED", "UNRESOLVED"],
        )


class FalseSignalRiskEnumTest(unittest.TestCase):
    def test_false_signal_risk_values(self) -> None:
        self.assertEqual(
            [m.value for m in FalseSignalRisk],
            ["LOW", "MEDIUM", "HIGH", "UNKNOWN"],
        )


class AssessmentStatusEnumTest(unittest.TestCase):
    def test_assessment_status_values(self) -> None:
        self.assertEqual(
            [m.value for m in AssessmentStatus],
            ["OK", "DEGRADED"],
        )


class ReasonCodeEnumTest(unittest.TestCase):
    def test_reason_code_values_present(self) -> None:
        expected_codes = {
            "CHECK_RESULT_MISSING",
            "COMPLETENESS_FAIL",
            "COMPLETENESS_WARN",
            "CONTROL_ROW_DEGRADED",
            "EVIDENCE_REF_MISSING",
            "FRESHNESS_FAIL",
            "FRESHNESS_WARN",
            "LINEAGE_FAIL",
            "LINEAGE_WARN",
            "PUBLICATION_READINESS_FAIL",
            "PUBLICATION_READINESS_WARN",
            "RECONCILIATION_FAIL",
            "RECONCILIATION_WARN",
        }
        actual_codes = {m.value for m in ReasonCode}
        self.assertEqual(actual_codes, expected_codes)

    def test_reason_code_count(self) -> None:
        self.assertEqual(len(ReasonCode), 13)

    def test_reason_codes_are_lexicographically_ordered_in_enum(self) -> None:
        """Enum members are declared in lexicographic order for predictability."""
        values = [m.value for m in ReasonCode]
        self.assertEqual(values, sorted(values))


if __name__ == "__main__":
    unittest.main()
