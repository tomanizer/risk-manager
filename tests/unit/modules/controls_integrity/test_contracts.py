"""Contract model tests for the controls integrity assessment layer.

Covers:
- schema validation and instantiation
- mirror-field enforcement from node_ref
- required-check ordering and uniqueness
- reason-code ordering and deduplication
- evidence-reference validation rules across PASS / WARN / FAIL / UNKNOWN
- rejection of invalid or partial contract shapes
"""

from __future__ import annotations

import unittest
from datetime import date, datetime, timezone

from pydantic import ValidationError

from src.modules.controls_integrity.contracts import (
    AssessmentStatus,
    CheckState,
    CheckType,
    ControlCheckResult,
    EvidenceRef,
    FalseSignalRisk,
    IntegrityAssessment,
    NormalizedControlRecord,
    ReasonCode,
    REQUIRED_CHECK_ORDER,
    TrustState,
)
from src.modules.risk_analytics.contracts import (
    HierarchyScope,
    MeasureType,
    NodeLevel,
    NodeRef,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

AS_OF = date(2026, 1, 12)
SNAP_ID = "SNAP-2026-01-12"
DATA_VER = "synthetic-controls-v1"
SVC_VER = "controls-integrity-service-v1"
GENERATED_AT = datetime(2026, 1, 12, 18, 0, tzinfo=timezone.utc)


def make_toh_node_ref() -> NodeRef:
    return NodeRef(
        hierarchy_scope=HierarchyScope.TOP_OF_HOUSE,
        legal_entity_id=None,
        node_level=NodeLevel.DESK,
        node_id="DESK_CREDIT_INDEX",
    )


def make_le_node_ref(le_id: str = "LE1") -> NodeRef:
    return NodeRef(
        hierarchy_scope=HierarchyScope.LEGAL_ENTITY,
        legal_entity_id=le_id,
        node_level=NodeLevel.DESK,
        node_id="DESK_RATES",
    )


def make_evidence_ref(
    evidence_type: str = "CONTROL_RECORD",
    evidence_id: str = "CTRL-001",
    source_as_of_date: date | None = None,
    snapshot_id: str | None = SNAP_ID,
) -> EvidenceRef:
    return EvidenceRef(
        evidence_type=evidence_type,
        evidence_id=evidence_id,
        source_as_of_date=source_as_of_date,
        snapshot_id=snapshot_id,
    )


def make_pass_result(check_type: CheckType) -> ControlCheckResult:
    return ControlCheckResult(
        check_type=check_type,
        check_state=CheckState.PASS,
    )


def make_all_pass_results() -> tuple[ControlCheckResult, ...]:
    return tuple(make_pass_result(ct) for ct in REQUIRED_CHECK_ORDER)


def make_warn_result(
    check_type: CheckType,
    reason_codes: tuple[ReasonCode, ...] = (ReasonCode.FRESHNESS_WARN,),
    evidence_refs: tuple[EvidenceRef, ...] | None = None,
) -> ControlCheckResult:
    if evidence_refs is None:
        evidence_refs = (make_evidence_ref(),)
    return ControlCheckResult(
        check_type=check_type,
        check_state=CheckState.WARN,
        reason_codes=reason_codes,
        evidence_refs=evidence_refs,
    )


def make_fail_result(
    check_type: CheckType,
    reason_codes: tuple[ReasonCode, ...] = (ReasonCode.FRESHNESS_FAIL,),
    evidence_refs: tuple[EvidenceRef, ...] | None = None,
) -> ControlCheckResult:
    if evidence_refs is None:
        evidence_refs = (make_evidence_ref(),)
    return ControlCheckResult(
        check_type=check_type,
        check_state=CheckState.FAIL,
        reason_codes=reason_codes,
        evidence_refs=evidence_refs,
    )


def make_unknown_missing_result(check_type: CheckType) -> ControlCheckResult:
    return ControlCheckResult(
        check_type=check_type,
        check_state=CheckState.UNKNOWN,
        reason_codes=(ReasonCode.CHECK_RESULT_MISSING,),
        evidence_refs=(),
    )


def make_base_assessment_kwargs(
    node_ref: NodeRef | None = None,
    check_results: tuple[ControlCheckResult, ...] | None = None,
    trust_state: TrustState = TrustState.TRUSTED,
    false_signal_risk: FalseSignalRisk = FalseSignalRisk.LOW,
    assessment_status: AssessmentStatus = AssessmentStatus.OK,
    blocking_reason_codes: tuple[ReasonCode, ...] = (),
    cautionary_reason_codes: tuple[ReasonCode, ...] = (),
) -> dict:
    if node_ref is None:
        node_ref = make_toh_node_ref()
    if check_results is None:
        check_results = make_all_pass_results()
    return {
        "node_ref": node_ref,
        "measure_type": MeasureType.VAR_1D_99,
        "as_of_date": AS_OF,
        "trust_state": trust_state,
        "false_signal_risk": false_signal_risk,
        "assessment_status": assessment_status,
        "blocking_reason_codes": blocking_reason_codes,
        "cautionary_reason_codes": cautionary_reason_codes,
        "check_results": check_results,
        "snapshot_id": SNAP_ID,
        "data_version": DATA_VER,
        "service_version": SVC_VER,
        "generated_at": GENERATED_AT,
    }


# ---------------------------------------------------------------------------
# EvidenceRef tests
# ---------------------------------------------------------------------------


class EvidenceRefTest(unittest.TestCase):
    def test_valid_evidence_ref_instantiates(self) -> None:
        ref = make_evidence_ref()
        self.assertEqual(ref.evidence_type, "CONTROL_RECORD")
        self.assertEqual(ref.evidence_id, "CTRL-001")
        self.assertEqual(ref.snapshot_id, SNAP_ID)

    def test_rejects_empty_evidence_type(self) -> None:
        with self.assertRaises(ValidationError):
            EvidenceRef(evidence_type="", evidence_id="CTRL-001")

    def test_rejects_empty_evidence_id(self) -> None:
        with self.assertRaises(ValidationError):
            EvidenceRef(evidence_type="CONTROL_RECORD", evidence_id="")

    def test_optional_fields_can_be_none(self) -> None:
        ref = EvidenceRef(
            evidence_type="CONTROL_RECORD",
            evidence_id="CTRL-002",
            source_as_of_date=None,
            snapshot_id=None,
        )
        self.assertIsNone(ref.source_as_of_date)
        self.assertIsNone(ref.snapshot_id)

    def test_extra_fields_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            EvidenceRef(
                evidence_type="CONTROL_RECORD",
                evidence_id="CTRL-001",
                unexpected_field="value",
            )


# ---------------------------------------------------------------------------
# NormalizedControlRecord tests
# ---------------------------------------------------------------------------


class NormalizedControlRecordTest(unittest.TestCase):
    def test_valid_record_instantiates(self) -> None:
        record = NormalizedControlRecord(
            node_ref=make_toh_node_ref(),
            measure_type=MeasureType.VAR_1D_99,
            as_of_date=AS_OF,
            snapshot_id=SNAP_ID,
            check_type=CheckType.FRESHNESS,
            check_state=CheckState.PASS,
        )
        self.assertEqual(record.check_type, CheckType.FRESHNESS)
        self.assertEqual(record.check_state, CheckState.PASS)
        self.assertFalse(record.is_row_degraded)

    def test_rejects_empty_snapshot_id(self) -> None:
        with self.assertRaises(ValidationError):
            NormalizedControlRecord(
                node_ref=make_toh_node_ref(),
                measure_type=MeasureType.VAR_1D_99,
                as_of_date=AS_OF,
                snapshot_id="",
                check_type=CheckType.FRESHNESS,
                check_state=CheckState.PASS,
            )

    def test_degraded_flag_defaults_false(self) -> None:
        record = NormalizedControlRecord(
            node_ref=make_toh_node_ref(),
            measure_type=MeasureType.VAR_1D_99,
            as_of_date=AS_OF,
            snapshot_id=SNAP_ID,
            check_type=CheckType.COMPLETENESS,
            check_state=CheckState.WARN,
            reason_codes=(ReasonCode.COMPLETENESS_WARN,),
            evidence_refs=(make_evidence_ref(),),
        )
        self.assertFalse(record.is_row_degraded)

    def test_degraded_flag_can_be_set_true(self) -> None:
        record = NormalizedControlRecord(
            node_ref=make_toh_node_ref(),
            measure_type=MeasureType.VAR_1D_99,
            as_of_date=AS_OF,
            snapshot_id=SNAP_ID,
            check_type=CheckType.FRESHNESS,
            check_state=CheckState.WARN,
            reason_codes=(ReasonCode.FRESHNESS_WARN, ReasonCode.CONTROL_ROW_DEGRADED),
            evidence_refs=(make_evidence_ref(),),
            is_row_degraded=True,
        )
        self.assertTrue(record.is_row_degraded)


# ---------------------------------------------------------------------------
# ControlCheckResult tests
# ---------------------------------------------------------------------------


class ControlCheckResultPassTest(unittest.TestCase):
    def test_pass_result_accepts_empty_codes_and_refs(self) -> None:
        result = make_pass_result(CheckType.FRESHNESS)
        self.assertEqual(result.check_state, CheckState.PASS)
        self.assertEqual(result.reason_codes, ())
        self.assertEqual(result.evidence_refs, ())

    def test_pass_result_rejects_reason_codes(self) -> None:
        with self.assertRaises(ValidationError):
            ControlCheckResult(
                check_type=CheckType.FRESHNESS,
                check_state=CheckState.PASS,
                reason_codes=(ReasonCode.FRESHNESS_WARN,),
            )

    def test_pass_result_rejects_evidence_refs(self) -> None:
        with self.assertRaises(ValidationError):
            ControlCheckResult(
                check_type=CheckType.FRESHNESS,
                check_state=CheckState.PASS,
                evidence_refs=(make_evidence_ref(),),
            )


class ControlCheckResultWarnTest(unittest.TestCase):
    def test_warn_result_requires_evidence_refs(self) -> None:
        with self.assertRaises(ValidationError):
            ControlCheckResult(
                check_type=CheckType.FRESHNESS,
                check_state=CheckState.WARN,
                reason_codes=(ReasonCode.FRESHNESS_WARN,),
                evidence_refs=(),
            )

    def test_warn_result_valid_with_evidence_refs(self) -> None:
        result = make_warn_result(
            CheckType.FRESHNESS,
            reason_codes=(ReasonCode.FRESHNESS_WARN,),
        )
        self.assertEqual(result.check_state, CheckState.WARN)
        self.assertEqual(len(result.evidence_refs), 1)

    def test_warn_result_reason_codes_deduplicated_and_sorted(self) -> None:
        result = ControlCheckResult(
            check_type=CheckType.COMPLETENESS,
            check_state=CheckState.WARN,
            reason_codes=(
                ReasonCode.CONTROL_ROW_DEGRADED,
                ReasonCode.COMPLETENESS_WARN,
                ReasonCode.COMPLETENESS_WARN,  # duplicate
            ),
            evidence_refs=(make_evidence_ref(),),
        )
        # After deduplication and sort: COMPLETENESS_WARN < CONTROL_ROW_DEGRADED
        self.assertEqual(
            result.reason_codes,
            (ReasonCode.COMPLETENESS_WARN, ReasonCode.CONTROL_ROW_DEGRADED),
        )


class ControlCheckResultFailTest(unittest.TestCase):
    def test_fail_result_requires_evidence_refs(self) -> None:
        with self.assertRaises(ValidationError):
            ControlCheckResult(
                check_type=CheckType.FRESHNESS,
                check_state=CheckState.FAIL,
                reason_codes=(ReasonCode.FRESHNESS_FAIL,),
                evidence_refs=(),
            )

    def test_fail_result_valid_with_evidence_refs(self) -> None:
        result = make_fail_result(CheckType.FRESHNESS)
        self.assertEqual(result.check_state, CheckState.FAIL)
        self.assertGreater(len(result.evidence_refs), 0)

    def test_fail_result_reason_codes_deduplicated_and_sorted(self) -> None:
        result = ControlCheckResult(
            check_type=CheckType.LINEAGE,
            check_state=CheckState.FAIL,
            reason_codes=(
                ReasonCode.LINEAGE_FAIL,
                ReasonCode.EVIDENCE_REF_MISSING,
                ReasonCode.LINEAGE_FAIL,  # duplicate
            ),
            evidence_refs=(make_evidence_ref(),),
        )
        # EVIDENCE_REF_MISSING < LINEAGE_FAIL lexicographically
        self.assertEqual(
            result.reason_codes,
            (ReasonCode.EVIDENCE_REF_MISSING, ReasonCode.LINEAGE_FAIL),
        )


class ControlCheckResultUnknownTest(unittest.TestCase):
    def test_unknown_with_check_result_missing_allows_empty_evidence(self) -> None:
        result = make_unknown_missing_result(CheckType.FRESHNESS)
        self.assertEqual(result.check_state, CheckState.UNKNOWN)
        self.assertEqual(result.evidence_refs, ())
        self.assertIn(ReasonCode.CHECK_RESULT_MISSING, result.reason_codes)

    def test_unknown_without_check_result_missing_rejects_empty_evidence(self) -> None:
        with self.assertRaises(ValidationError):
            ControlCheckResult(
                check_type=CheckType.FRESHNESS,
                check_state=CheckState.UNKNOWN,
                reason_codes=(ReasonCode.CONTROL_ROW_DEGRADED,),
                evidence_refs=(),
            )

    def test_unknown_with_evidence_refs_and_no_check_result_missing_is_valid(self) -> None:
        result = ControlCheckResult(
            check_type=CheckType.FRESHNESS,
            check_state=CheckState.UNKNOWN,
            reason_codes=(ReasonCode.CONTROL_ROW_DEGRADED,),
            evidence_refs=(make_evidence_ref(),),
        )
        self.assertEqual(result.check_state, CheckState.UNKNOWN)

    def test_unknown_all_empty_reason_codes_and_empty_evidence_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            ControlCheckResult(
                check_type=CheckType.FRESHNESS,
                check_state=CheckState.UNKNOWN,
                reason_codes=(),
                evidence_refs=(),
            )


# ---------------------------------------------------------------------------
# IntegrityAssessment tests
# ---------------------------------------------------------------------------


class IntegrityAssessmentMirrorFieldTest(unittest.TestCase):
    def test_mirror_fields_populated_from_node_ref_toh(self) -> None:
        assessment = IntegrityAssessment(**make_base_assessment_kwargs())
        self.assertEqual(assessment.node_level, NodeLevel.DESK)
        self.assertEqual(assessment.hierarchy_scope, HierarchyScope.TOP_OF_HOUSE)
        self.assertIsNone(assessment.legal_entity_id)

    def test_mirror_fields_populated_from_node_ref_legal_entity(self) -> None:
        assessment = IntegrityAssessment(**make_base_assessment_kwargs(node_ref=make_le_node_ref("LE_ALPHA")))
        self.assertEqual(assessment.node_level, NodeLevel.DESK)
        self.assertEqual(assessment.hierarchy_scope, HierarchyScope.LEGAL_ENTITY)
        self.assertEqual(assessment.legal_entity_id, "LE_ALPHA")

    def test_mirror_field_mismatch_rejected(self) -> None:
        kwargs = make_base_assessment_kwargs()
        kwargs["node_level"] = NodeLevel.BOOK  # does not match DESK in node_ref
        with self.assertRaises(ValidationError):
            IntegrityAssessment(**kwargs)

    def test_mirror_field_hierarchy_scope_mismatch_rejected(self) -> None:
        kwargs = make_base_assessment_kwargs()
        kwargs["hierarchy_scope"] = HierarchyScope.LEGAL_ENTITY
        with self.assertRaises(ValidationError):
            IntegrityAssessment(**kwargs)

    def test_mirror_legal_entity_id_mismatch_rejected(self) -> None:
        kwargs = make_base_assessment_kwargs(node_ref=make_le_node_ref("LE1"))
        kwargs["legal_entity_id"] = "LE2"
        with self.assertRaises(ValidationError):
            IntegrityAssessment(**kwargs)


class IntegrityAssessmentRequiredCheckOrderTest(unittest.TestCase):
    def test_all_pass_check_results_in_order(self) -> None:
        assessment = IntegrityAssessment(**make_base_assessment_kwargs())
        actual_types = [r.check_type for r in assessment.check_results]
        self.assertEqual(actual_types, list(REQUIRED_CHECK_ORDER))

    def test_wrong_order_rejected(self) -> None:
        # Swap FRESHNESS and COMPLETENESS
        results = (
            make_pass_result(CheckType.COMPLETENESS),
            make_pass_result(CheckType.FRESHNESS),
            make_pass_result(CheckType.LINEAGE),
            make_pass_result(CheckType.RECONCILIATION),
            make_pass_result(CheckType.PUBLICATION_READINESS),
        )
        kwargs = make_base_assessment_kwargs(check_results=results)
        with self.assertRaises(ValidationError):
            IntegrityAssessment(**kwargs)

    def test_missing_check_rejected(self) -> None:
        # Only 4 checks, RECONCILIATION missing
        results = (
            make_pass_result(CheckType.FRESHNESS),
            make_pass_result(CheckType.COMPLETENESS),
            make_pass_result(CheckType.LINEAGE),
            make_pass_result(CheckType.PUBLICATION_READINESS),
        )
        kwargs = make_base_assessment_kwargs(check_results=results)
        with self.assertRaises(ValidationError):
            IntegrityAssessment(**kwargs)

    def test_duplicate_check_type_rejected(self) -> None:
        # FRESHNESS appears twice
        results = (
            make_pass_result(CheckType.FRESHNESS),
            make_pass_result(CheckType.FRESHNESS),
            make_pass_result(CheckType.LINEAGE),
            make_pass_result(CheckType.RECONCILIATION),
            make_pass_result(CheckType.PUBLICATION_READINESS),
        )
        kwargs = make_base_assessment_kwargs(check_results=results)
        with self.assertRaises(ValidationError):
            IntegrityAssessment(**kwargs)

    def test_extra_check_type_rejected(self) -> None:
        # 6 results
        results = make_all_pass_results() + (make_pass_result(CheckType.FRESHNESS),)
        kwargs = make_base_assessment_kwargs(check_results=results)
        with self.assertRaises(ValidationError):
            IntegrityAssessment(**kwargs)


class IntegrityAssessmentReasonCodesTest(unittest.TestCase):
    def test_blocking_reason_codes_deduplicated_and_sorted(self) -> None:
        assessment = IntegrityAssessment(
            **make_base_assessment_kwargs(
                check_results=make_all_pass_results(),
                trust_state=TrustState.BLOCKED,
                false_signal_risk=FalseSignalRisk.HIGH,
                assessment_status=AssessmentStatus.OK,
                blocking_reason_codes=(
                    ReasonCode.FRESHNESS_FAIL,
                    ReasonCode.LINEAGE_FAIL,
                    ReasonCode.FRESHNESS_FAIL,  # duplicate
                ),
            )
        )
        # FRESHNESS_FAIL < LINEAGE_FAIL lexicographically
        self.assertEqual(
            assessment.blocking_reason_codes,
            (ReasonCode.FRESHNESS_FAIL, ReasonCode.LINEAGE_FAIL),
        )

    def test_cautionary_reason_codes_deduplicated_and_sorted(self) -> None:
        assessment = IntegrityAssessment(
            **make_base_assessment_kwargs(
                trust_state=TrustState.CAUTION,
                false_signal_risk=FalseSignalRisk.MEDIUM,
                assessment_status=AssessmentStatus.OK,
                cautionary_reason_codes=(
                    ReasonCode.RECONCILIATION_WARN,
                    ReasonCode.COMPLETENESS_WARN,
                    ReasonCode.COMPLETENESS_WARN,  # duplicate
                ),
            )
        )
        # COMPLETENESS_WARN < RECONCILIATION_WARN
        self.assertEqual(
            assessment.cautionary_reason_codes,
            (ReasonCode.COMPLETENESS_WARN, ReasonCode.RECONCILIATION_WARN),
        )

    def test_empty_reason_code_lists_accepted(self) -> None:
        assessment = IntegrityAssessment(**make_base_assessment_kwargs())
        self.assertEqual(assessment.blocking_reason_codes, ())
        self.assertEqual(assessment.cautionary_reason_codes, ())


class IntegrityAssessmentVersionFieldsTest(unittest.TestCase):
    def test_rejects_empty_snapshot_id(self) -> None:
        kwargs = make_base_assessment_kwargs()
        kwargs["snapshot_id"] = ""
        with self.assertRaises(ValidationError):
            IntegrityAssessment(**kwargs)

    def test_rejects_empty_data_version(self) -> None:
        kwargs = make_base_assessment_kwargs()
        kwargs["data_version"] = ""
        with self.assertRaises(ValidationError):
            IntegrityAssessment(**kwargs)

    def test_rejects_empty_service_version(self) -> None:
        kwargs = make_base_assessment_kwargs()
        kwargs["service_version"] = ""
        with self.assertRaises(ValidationError):
            IntegrityAssessment(**kwargs)


class IntegrityAssessmentTrustStatesTest(unittest.TestCase):
    def test_trusted_all_pass(self) -> None:
        assessment = IntegrityAssessment(**make_base_assessment_kwargs())
        self.assertEqual(assessment.trust_state, TrustState.TRUSTED)
        self.assertEqual(assessment.false_signal_risk, FalseSignalRisk.LOW)
        self.assertEqual(assessment.assessment_status, AssessmentStatus.OK)

    def test_caution_with_warn_result(self) -> None:
        results = (
            make_warn_result(CheckType.FRESHNESS, (ReasonCode.FRESHNESS_WARN,)),
            make_pass_result(CheckType.COMPLETENESS),
            make_pass_result(CheckType.LINEAGE),
            make_pass_result(CheckType.RECONCILIATION),
            make_pass_result(CheckType.PUBLICATION_READINESS),
        )
        kwargs = make_base_assessment_kwargs(
            check_results=results,
            trust_state=TrustState.CAUTION,
            false_signal_risk=FalseSignalRisk.MEDIUM,
            assessment_status=AssessmentStatus.OK,
            cautionary_reason_codes=(ReasonCode.FRESHNESS_WARN,),
        )
        assessment = IntegrityAssessment(**kwargs)
        self.assertEqual(assessment.trust_state, TrustState.CAUTION)
        self.assertEqual(assessment.false_signal_risk, FalseSignalRisk.MEDIUM)

    def test_blocked_with_fail_result(self) -> None:
        results = (
            make_fail_result(CheckType.FRESHNESS, (ReasonCode.FRESHNESS_FAIL,)),
            make_pass_result(CheckType.COMPLETENESS),
            make_pass_result(CheckType.LINEAGE),
            make_pass_result(CheckType.RECONCILIATION),
            make_pass_result(CheckType.PUBLICATION_READINESS),
        )
        kwargs = make_base_assessment_kwargs(
            check_results=results,
            trust_state=TrustState.BLOCKED,
            false_signal_risk=FalseSignalRisk.HIGH,
            assessment_status=AssessmentStatus.OK,
            blocking_reason_codes=(ReasonCode.FRESHNESS_FAIL,),
        )
        assessment = IntegrityAssessment(**kwargs)
        self.assertEqual(assessment.trust_state, TrustState.BLOCKED)
        self.assertEqual(assessment.false_signal_risk, FalseSignalRisk.HIGH)

    def test_unresolved_with_unknown_result(self) -> None:
        results = (
            make_unknown_missing_result(CheckType.FRESHNESS),
            make_pass_result(CheckType.COMPLETENESS),
            make_pass_result(CheckType.LINEAGE),
            make_pass_result(CheckType.RECONCILIATION),
            make_pass_result(CheckType.PUBLICATION_READINESS),
        )
        kwargs = make_base_assessment_kwargs(
            check_results=results,
            trust_state=TrustState.UNRESOLVED,
            false_signal_risk=FalseSignalRisk.UNKNOWN,
            assessment_status=AssessmentStatus.DEGRADED,
            cautionary_reason_codes=(ReasonCode.CHECK_RESULT_MISSING,),
        )
        assessment = IntegrityAssessment(**kwargs)
        self.assertEqual(assessment.trust_state, TrustState.UNRESOLVED)
        self.assertEqual(assessment.assessment_status, AssessmentStatus.DEGRADED)
        self.assertEqual(assessment.false_signal_risk, FalseSignalRisk.UNKNOWN)


class IntegrityAssessmentLegalEntityScopeTest(unittest.TestCase):
    def test_le_scoped_assessment_carries_legal_entity_id(self) -> None:
        le_ref = make_le_node_ref("LE_BETA")
        assessment = IntegrityAssessment(**make_base_assessment_kwargs(node_ref=le_ref))
        self.assertEqual(assessment.legal_entity_id, "LE_BETA")
        self.assertEqual(assessment.hierarchy_scope, HierarchyScope.LEGAL_ENTITY)

    def test_two_legal_entities_produce_distinct_assessments(self) -> None:
        le_ref_1 = make_le_node_ref("LE1")
        le_ref_2 = make_le_node_ref("LE2")

        a1 = IntegrityAssessment(**make_base_assessment_kwargs(node_ref=le_ref_1))
        a2 = IntegrityAssessment(**make_base_assessment_kwargs(node_ref=le_ref_2))

        self.assertNotEqual(a1.legal_entity_id, a2.legal_entity_id)
        self.assertEqual(a1.legal_entity_id, "LE1")
        self.assertEqual(a2.legal_entity_id, "LE2")

    def test_toh_assessment_has_null_legal_entity_id(self) -> None:
        assessment = IntegrityAssessment(**make_base_assessment_kwargs())
        self.assertIsNone(assessment.legal_entity_id)


class IntegrityAssessmentExtraFieldsTest(unittest.TestCase):
    def test_extra_fields_rejected(self) -> None:
        kwargs = make_base_assessment_kwargs()
        kwargs["unexpected_field"] = "surprise"
        with self.assertRaises(ValidationError):
            IntegrityAssessment(**kwargs)

    def test_missing_required_field_rejected(self) -> None:
        kwargs = make_base_assessment_kwargs()
        del kwargs["trust_state"]
        with self.assertRaises(ValidationError):
            IntegrityAssessment(**kwargs)


class RequiredCheckOrderConstantTest(unittest.TestCase):
    def test_required_check_order_is_canonical(self) -> None:
        self.assertEqual(
            list(REQUIRED_CHECK_ORDER),
            [
                CheckType.FRESHNESS,
                CheckType.COMPLETENESS,
                CheckType.LINEAGE,
                CheckType.RECONCILIATION,
                CheckType.PUBLICATION_READINESS,
            ],
        )

    def test_required_check_order_has_five_entries(self) -> None:
        self.assertEqual(len(REQUIRED_CHECK_ORDER), 5)


if __name__ == "__main__":
    unittest.main()
