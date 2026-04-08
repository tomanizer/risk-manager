"""Unit tests for ``get_integrity_assessment`` (WI-2.1.3)."""

from __future__ import annotations

from datetime import date

import pytest

from src.modules.controls_integrity import (
    REQUIRED_CHECK_ORDER,
    get_integrity_assessment,
)
from src.modules.controls_integrity.contracts import (
    AssessmentStatus,
    CheckState,
    CheckType,
    FalseSignalRisk,
    IntegrityAssessment,
    ReasonCode,
    TrustState,
)
from src.modules.controls_integrity.fixtures import build_controls_integrity_fixture_index
from src.modules.risk_analytics.contracts import HierarchyScope, MeasureType, NodeLevel, NodeRef
from src.modules.risk_analytics.fixtures import build_fixture_index
from src.shared import ServiceError

D_02 = date(2026, 1, 2)
D_05 = date(2026, 1, 5)
D_06 = date(2026, 1, 6)
D_08 = date(2026, 1, 8)
D_09 = date(2026, 1, 9)


def firm_grp() -> NodeRef:
    return NodeRef(
        hierarchy_scope=HierarchyScope.TOP_OF_HOUSE,
        legal_entity_id=None,
        node_level=NodeLevel.FIRM,
        node_id="FIRM_GRP",
        node_name="Firm Group",
    )


def division_toh() -> NodeRef:
    return NodeRef(
        hierarchy_scope=HierarchyScope.TOP_OF_HOUSE,
        legal_entity_id=None,
        node_level=NodeLevel.DIVISION,
        node_id="DIV_GM",
        node_name="Global Markets",
    )


def division_le(legal_entity_id: str) -> NodeRef:
    return NodeRef(
        hierarchy_scope=HierarchyScope.LEGAL_ENTITY,
        legal_entity_id=legal_entity_id,
        node_level=NodeLevel.DIVISION,
        node_id="DIV_GM",
        node_name="Global Markets",
    )


def book_new_issues() -> NodeRef:
    return NodeRef(
        hierarchy_scope=HierarchyScope.TOP_OF_HOUSE,
        legal_entity_id=None,
        node_level=NodeLevel.BOOK,
        node_id="BOOK_NEW_ISSUES",
        node_name="New Issues",
    )


@pytest.fixture
def risk_index():
    return build_fixture_index()


@pytest.fixture
def controls_index():
    return build_controls_integrity_fixture_index()


def test_trusted_all_pass(risk_index, controls_index) -> None:
    out = get_integrity_assessment(
        firm_grp(),
        MeasureType.VAR_1D_99,
        D_02,
        risk_fixture_index=risk_index,
        controls_fixture_index=controls_index,
    )
    assert isinstance(out, IntegrityAssessment)
    assert out.trust_state == TrustState.TRUSTED
    assert out.false_signal_risk == FalseSignalRisk.LOW
    assert out.assessment_status == AssessmentStatus.OK
    assert out.blocking_reason_codes == ()
    assert out.cautionary_reason_codes == ()
    assert [c.check_type for c in out.check_results] == list(REQUIRED_CHECK_ORDER)
    assert all(c.check_state == CheckState.PASS for c in out.check_results)
    assert out.snapshot_id == "SNAP-2026-01-02"
    assert out.generated_at.isoformat() == "2026-01-02T18:00:00+00:00"


def test_caution_single_warn(risk_index, controls_index) -> None:
    out = get_integrity_assessment(
        division_toh(),
        MeasureType.VAR_1D_99,
        D_05,
        risk_fixture_index=risk_index,
        controls_fixture_index=controls_index,
    )
    assert not isinstance(out, ServiceError)
    assert out.trust_state == TrustState.CAUTION
    assert out.false_signal_risk == FalseSignalRisk.MEDIUM
    assert out.assessment_status == AssessmentStatus.OK
    assert out.blocking_reason_codes == ()
    assert out.cautionary_reason_codes == (ReasonCode.COMPLETENESS_WARN,)


def test_blocked_single_fail(risk_index, controls_index) -> None:
    out = get_integrity_assessment(
        division_toh(),
        MeasureType.VAR_1D_99,
        D_06,
        risk_fixture_index=risk_index,
        controls_fixture_index=controls_index,
    )
    assert not isinstance(out, ServiceError)
    assert out.trust_state == TrustState.BLOCKED
    assert out.false_signal_risk == FalseSignalRisk.HIGH
    assert out.assessment_status == AssessmentStatus.OK
    assert out.blocking_reason_codes == (ReasonCode.RECONCILIATION_FAIL,)
    assert out.cautionary_reason_codes == ()


def test_unresolved_upstream_unknown_lineage(risk_index, controls_index) -> None:
    out = get_integrity_assessment(
        division_toh(),
        MeasureType.VAR_1D_99,
        D_08,
        risk_fixture_index=risk_index,
        controls_fixture_index=controls_index,
    )
    assert not isinstance(out, ServiceError)
    assert out.trust_state == TrustState.UNRESOLVED
    assert out.false_signal_risk == FalseSignalRisk.UNKNOWN
    assert out.assessment_status == AssessmentStatus.DEGRADED
    lineage = next(c for c in out.check_results if c.check_type == CheckType.LINEAGE)
    assert lineage.check_state == CheckState.UNKNOWN
    assert ReasonCode.CHECK_RESULT_MISSING in lineage.reason_codes


def test_degraded_row_caution(risk_index, controls_index) -> None:
    out = get_integrity_assessment(
        division_toh(),
        MeasureType.VAR_1D_99,
        D_09,
        risk_fixture_index=risk_index,
        controls_fixture_index=controls_index,
    )
    assert not isinstance(out, ServiceError)
    assert out.trust_state == TrustState.CAUTION
    assert out.assessment_status == AssessmentStatus.DEGRADED
    fresh = next(c for c in out.check_results if c.check_type == CheckType.FRESHNESS)
    assert fresh.check_state == CheckState.WARN
    assert ReasonCode.CONTROL_ROW_DEGRADED in fresh.reason_codes
    assert ReasonCode.FRESHNESS_WARN in fresh.reason_codes


def test_missing_snapshot(risk_index, controls_index) -> None:
    out = get_integrity_assessment(
        firm_grp(),
        MeasureType.VAR_1D_99,
        D_02,
        snapshot_id="SNAP-NOT-THERE",
        risk_fixture_index=risk_index,
        controls_fixture_index=controls_index,
    )
    assert isinstance(out, ServiceError)
    assert out.status_code == "MISSING_SNAPSHOT"


def test_missing_node(risk_index, controls_index) -> None:
    out = get_integrity_assessment(
        division_le("LE-UK-BANK"),
        MeasureType.VAR_1D_99,
        D_02,
        risk_fixture_index=risk_index,
        controls_fixture_index=controls_index,
    )
    assert isinstance(out, ServiceError)
    assert out.status_code == "MISSING_NODE"


def test_missing_control_context(risk_index, controls_index) -> None:
    out = get_integrity_assessment(
        book_new_issues(),
        MeasureType.VAR_1D_99,
        D_08,
        risk_fixture_index=risk_index,
        controls_fixture_index=controls_index,
    )
    assert isinstance(out, ServiceError)
    assert out.status_code == "MISSING_CONTROL_CONTEXT"


def test_snapshot_date_mismatch_raises(risk_index, controls_index) -> None:
    with pytest.raises(ValueError, match="as_of_date"):
        get_integrity_assessment(
            firm_grp(),
            MeasureType.VAR_1D_99,
            D_05,
            snapshot_id="SNAP-2026-01-02",
            risk_fixture_index=risk_index,
            controls_fixture_index=controls_index,
        )


def test_blank_snapshot_id_raises(risk_index, controls_index) -> None:
    with pytest.raises(ValueError, match="non-empty"):
        get_integrity_assessment(
            firm_grp(),
            MeasureType.VAR_1D_99,
            D_02,
            snapshot_id="   ",
            risk_fixture_index=risk_index,
            controls_fixture_index=controls_index,
        )


def test_partial_missing_check(risk_index, controls_index, monkeypatch: pytest.MonkeyPatch) -> None:
    orig = controls_index.get_record

    def _patched(nr, mt, d, sid, ct):
        if ct == CheckType.LINEAGE:
            return None
        return orig(nr, mt, d, sid, ct)

    monkeypatch.setattr(controls_index, "get_record", _patched)

    out = get_integrity_assessment(
        firm_grp(),
        MeasureType.VAR_1D_99,
        D_02,
        risk_fixture_index=risk_index,
        controls_fixture_index=controls_index,
    )
    assert not isinstance(out, ServiceError)
    assert out.trust_state == TrustState.UNRESOLVED
    assert out.assessment_status == AssessmentStatus.DEGRADED
    lineage = next(c for c in out.check_results if c.check_type == CheckType.LINEAGE)
    assert lineage.check_state == CheckState.UNKNOWN
    assert lineage.reason_codes == (ReasonCode.CHECK_RESULT_MISSING,)


def test_missing_evidence_degrades_warn(risk_index, controls_index, monkeypatch: pytest.MonkeyPatch) -> None:
    orig = controls_index.get_record
    base = orig(
        firm_grp(),
        MeasureType.VAR_1D_99,
        D_02,
        "SNAP-2026-01-02",
        CheckType.FRESHNESS,
    )
    assert base is not None
    degraded_row = base.model_copy(
        update={
            "check_state": CheckState.WARN,
            "reason_codes": (ReasonCode.FRESHNESS_WARN,),
            "evidence_refs": (),
        }
    )

    def _patched(nr, mt, d, sid, ct):
        if ct == CheckType.FRESHNESS:
            return degraded_row
        return orig(nr, mt, d, sid, ct)

    monkeypatch.setattr(controls_index, "get_record", _patched)

    out = get_integrity_assessment(
        firm_grp(),
        MeasureType.VAR_1D_99,
        D_02,
        risk_fixture_index=risk_index,
        controls_fixture_index=controls_index,
    )
    assert not isinstance(out, ServiceError)
    assert out.trust_state == TrustState.CAUTION
    assert out.assessment_status == AssessmentStatus.DEGRADED
    fresh = next(c for c in out.check_results if c.check_type == CheckType.FRESHNESS)
    assert ReasonCode.EVIDENCE_REF_MISSING in fresh.reason_codes


def test_evidence_future_as_of_degrades(risk_index, controls_index, monkeypatch: pytest.MonkeyPatch) -> None:
    orig = controls_index.get_record
    base = orig(
        division_toh(),
        MeasureType.VAR_1D_99,
        D_05,
        "SNAP-2026-01-05",
        CheckType.COMPLETENESS,
    )
    assert base is not None
    ref = base.evidence_refs[0].model_copy(update={"source_as_of_date": date(2026, 2, 1)})
    row = base.model_copy(update={"evidence_refs": (ref,)})

    def _patched(nr, mt, d, sid, ct):
        if ct == CheckType.COMPLETENESS:
            return row
        return orig(nr, mt, d, sid, ct)

    monkeypatch.setattr(controls_index, "get_record", _patched)

    out = get_integrity_assessment(
        division_toh(),
        MeasureType.VAR_1D_99,
        D_05,
        risk_fixture_index=risk_index,
        controls_fixture_index=controls_index,
    )
    assert not isinstance(out, ServiceError)
    assert out.assessment_status == AssessmentStatus.DEGRADED
    comp = next(c for c in out.check_results if c.check_type == CheckType.COMPLETENESS)
    assert ReasonCode.EVIDENCE_REF_MISSING in comp.reason_codes
    assert not comp.evidence_refs


def test_reason_codes_sorted_and_deduplicated(risk_index, controls_index, monkeypatch: pytest.MonkeyPatch) -> None:
    """Two WARN checks with overlapping codes → single sorted cautionary union."""
    orig = controls_index.get_record
    d = D_06

    def _patched(nr, mt, dd, snapshot_id, ct):
        if nr.node_id != "DIV_GM":
            return orig(nr, mt, dd, snapshot_id, ct)
        if ct == CheckType.RECONCILIATION:
            base = orig(nr, mt, dd, snapshot_id, ct)
            assert base is not None
            return base.model_copy(
                update={
                    "check_state": CheckState.PASS,
                    "reason_codes": (),
                    "evidence_refs": (),
                }
            )
        if ct in (CheckType.FRESHNESS, CheckType.COMPLETENESS):
            template = orig(division_toh(), MeasureType.VAR_1D_99, dd, snapshot_id, CheckType.RECONCILIATION)
            assert template is not None
            refs = template.evidence_refs
            base_row = orig(nr, mt, dd, snapshot_id, ct)
            assert base_row is not None
            code = ReasonCode.FRESHNESS_WARN if ct == CheckType.FRESHNESS else ReasonCode.COMPLETENESS_WARN
            return base_row.model_copy(
                update={
                    "check_state": CheckState.WARN,
                    "reason_codes": (code, ReasonCode.CONTROL_ROW_DEGRADED),
                    "evidence_refs": refs,
                }
            )
        return orig(nr, mt, dd, snapshot_id, ct)

    monkeypatch.setattr(controls_index, "get_record", _patched)

    out = get_integrity_assessment(
        division_toh(),
        MeasureType.VAR_1D_99,
        d,
        risk_fixture_index=risk_index,
        controls_fixture_index=controls_index,
    )
    assert not isinstance(out, ServiceError)
    assert out.trust_state == TrustState.CAUTION
    codes = out.cautionary_reason_codes
    assert codes == tuple(sorted(set(codes), key=lambda x: x.value))
    assert codes.count(ReasonCode.CONTROL_ROW_DEGRADED) == 1


def test_check_results_stable_ordering(risk_index, controls_index) -> None:
    out = get_integrity_assessment(
        division_toh(),
        MeasureType.VAR_1D_99,
        D_05,
        risk_fixture_index=risk_index,
        controls_fixture_index=controls_index,
    )
    assert not isinstance(out, ServiceError)
    assert [c.check_type for c in out.check_results] == list(REQUIRED_CHECK_ORDER)


def test_exported_from_package() -> None:
    from src.modules import controls_integrity

    assert hasattr(controls_integrity, "get_integrity_assessment")
