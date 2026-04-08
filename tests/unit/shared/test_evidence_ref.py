"""Unit tests for shared ``EvidenceRef`` validation (PRD-2.1, WI-2.1.6)."""

from __future__ import annotations

import unittest
from datetime import date

from pydantic import ValidationError

from src.shared import EvidenceRef


class EvidenceRefSharedTest(unittest.TestCase):
    def test_valid_minimal(self) -> None:
        ref = EvidenceRef(evidence_type="CONTROL_RECORD", evidence_id="CTRL-001")
        self.assertEqual(ref.evidence_type, "CONTROL_RECORD")
        self.assertEqual(ref.evidence_id, "CTRL-001")
        self.assertIsNone(ref.source_as_of_date)
        self.assertIsNone(ref.snapshot_id)

    def test_valid_with_optionals(self) -> None:
        ref = EvidenceRef(
            evidence_type="LEDGER",
            evidence_id="L-42",
            source_as_of_date=date(2026, 1, 15),
            snapshot_id="snap-abc",
        )
        self.assertEqual(ref.source_as_of_date, date(2026, 1, 15))
        self.assertEqual(ref.snapshot_id, "snap-abc")

    def test_rejects_empty_evidence_type(self) -> None:
        with self.assertRaises(ValidationError):
            EvidenceRef(evidence_type="", evidence_id="x")

    def test_rejects_empty_evidence_id(self) -> None:
        with self.assertRaises(ValidationError):
            EvidenceRef(evidence_type="T", evidence_id="")

    def test_rejects_whitespace_only_evidence_type_after_strip(self) -> None:
        with self.assertRaises(ValidationError):
            EvidenceRef(evidence_type="   ", evidence_id="x")

    def test_rejects_whitespace_only_evidence_id_after_strip(self) -> None:
        with self.assertRaises(ValidationError):
            EvidenceRef(evidence_type="T", evidence_id="  \t  ")

    def test_strips_and_accepts_padded_non_empty_strings(self) -> None:
        ref = EvidenceRef(evidence_type="  TYPE  ", evidence_id="  id-1  ")
        self.assertEqual(ref.evidence_type, "TYPE")
        self.assertEqual(ref.evidence_id, "id-1")

    def test_extra_fields_forbidden(self) -> None:
        with self.assertRaises(ValidationError):
            EvidenceRef(
                evidence_type="T",
                evidence_id="i",
                unexpected="no",
            )

    def test_frozen_model(self) -> None:
        ref = EvidenceRef(evidence_type="T", evidence_id="i")
        with self.assertRaises(ValidationError):
            ref.evidence_type = "other"  # type: ignore[misc]
