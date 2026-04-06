"""Shared service-error model tests."""

from __future__ import annotations

import unittest

from pydantic import ValidationError

from src.shared import RequestValidationFailure, ServiceError


class ServiceErrorTestCase(unittest.TestCase):
    def test_constructs_service_error_with_minimal_fields(self) -> None:
        error = ServiceError(
            operation="get_risk_delta",
            status_code="MISSING_SNAPSHOT",
            status_reasons=("AS_OF_DATE_SNAPSHOT_NOT_FOUND:2026-01-07",),
        )

        self.assertEqual(error.operation, "get_risk_delta")
        self.assertEqual(error.status_code, "MISSING_SNAPSHOT")
        self.assertEqual(
            error.status_reasons,
            ("AS_OF_DATE_SNAPSHOT_NOT_FOUND:2026-01-07",),
        )

    def test_constructs_request_validation_failure(self) -> None:
        failure = RequestValidationFailure(
            operation="get_risk_delta",
            status_code="INVALID_REQUEST",
            status_reasons=("COMPARE_DATE_AFTER_AS_OF_DATE",),
        )

        self.assertEqual(failure.operation, "get_risk_delta")
        self.assertEqual(failure.status_code, "INVALID_REQUEST")
        self.assertEqual(
            failure.status_reasons,
            ("COMPARE_DATE_AFTER_AS_OF_DATE",),
        )

    def test_service_error_does_not_require_risk_delta_payload_fields(self) -> None:
        error = ServiceError(
            operation="get_risk_delta",
            status_code="UNSUPPORTED_MEASURE",
        )

        self.assertEqual(error.status_reasons, ())
        self.assertFalse(hasattr(error, "current_value"))
        self.assertFalse(hasattr(error, "snapshot_id"))
        self.assertFalse(hasattr(error, "data_version"))
        self.assertFalse(hasattr(error, "service_version"))
        self.assertFalse(hasattr(error, "generated_at"))

    def test_rejects_missing_and_blank_required_fields(self) -> None:
        with self.assertRaises(ValidationError):
            ServiceError(status_code="MISSING_NODE")
        with self.assertRaises(ValidationError):
            ServiceError(operation="get_risk_delta", status_code=" ")
        with self.assertRaises(ValidationError):
            RequestValidationFailure(operation=" ", status_code="INVALID_REQUEST")

    def test_rejects_blank_status_reason_entries(self) -> None:
        with self.assertRaises(ValidationError):
            ServiceError(
                operation="get_risk_delta",
                status_code="MISSING_SNAPSHOT",
                status_reasons=(" ",),
            )

    def test_normalizes_trimmed_string_fields(self) -> None:
        error = ServiceError(
            operation=" get_risk_delta ",
            status_code=" MISSING_NODE ",
            status_reasons=(" NODE_NOT_FOUND ", " SCOPE_MISMATCH "),
        )

        self.assertEqual(error.operation, "get_risk_delta")
        self.assertEqual(error.status_code, "MISSING_NODE")
        self.assertEqual(error.status_reasons, ("NODE_NOT_FOUND", "SCOPE_MISMATCH"))

    def test_shared_models_are_distinct_outcome_types(self) -> None:
        error = ServiceError(operation="get_risk_delta", status_code="MISSING_NODE")
        failure = RequestValidationFailure(
            operation="get_risk_delta",
            status_code="INVALID_REQUEST",
        )

        self.assertIsInstance(error, ServiceError)
        self.assertIsInstance(failure, RequestValidationFailure)
        self.assertNotIsInstance(error, RequestValidationFailure)
        self.assertNotIsInstance(failure, ServiceError)


if __name__ == "__main__":
    unittest.main()
