"""Regression coverage mandated by WI-2.1.4.

Maps to acceptance criteria:
  - missing evidence propagation / degraded assessment object
  - degraded normalized rows
  - missing required check (partial control context)
  - distinct legal-entity outcomes when fixture control rows differ
"""

from __future__ import annotations

from datetime import date

import pytest

from src.modules.controls_integrity import get_integrity_assessment
from src.modules.controls_integrity.contracts import (
    AssessmentStatus,
    CheckState,
    CheckType,
    IntegrityAssessment,
    ReasonCode,
    TrustState,
)
from src.modules.controls_integrity.fixtures import build_controls_integrity_fixture_index
from src.modules.risk_analytics.contracts import HierarchyScope, MeasureType, NodeLevel, NodeRef
from src.modules.risk_analytics.fixtures import build_fixture_index

D_02 = date(2026, 1, 2)
D_09 = date(2026, 1, 9)
D_12 = date(2026, 1, 12)


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


def desk_le(legal_entity_id: str) -> NodeRef:
    return NodeRef(
        hierarchy_scope=HierarchyScope.LEGAL_ENTITY,
        legal_entity_id=legal_entity_id,
        node_level=NodeLevel.DESK,
        node_id="DESK_RATES_MACRO",
        node_name="Rates Macro",
    )


@pytest.fixture
def risk_index():
    return build_fixture_index()


@pytest.fixture
def controls_index():
    return build_controls_integrity_fixture_index()


def test_wi_2_1_4_regression_missing_evidence_degrades_object(
    risk_index,
    controls_index,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """WARN without usable evidence after assessment-date filtering → DEGRADED + EVIDENCE_REF_MISSING."""
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
    assert isinstance(out, IntegrityAssessment)
    assert out.trust_state == TrustState.CAUTION
    assert out.assessment_status == AssessmentStatus.DEGRADED
    fresh = next(c for c in out.check_results if c.check_type == CheckType.FRESHNESS)
    assert ReasonCode.EVIDENCE_REF_MISSING in fresh.reason_codes


def test_wi_2_1_4_regression_degraded_normalized_row(
    risk_index,
    controls_index,
) -> None:
    """Fixture row with ``is_row_degraded`` → DEGRADED assessment + CONTROL_ROW_DEGRADED on check."""
    out = get_integrity_assessment(
        division_toh(),
        MeasureType.VAR_1D_99,
        D_09,
        "SNAP-2026-01-09",
        risk_fixture_index=risk_index,
        controls_fixture_index=controls_index,
    )
    assert isinstance(out, IntegrityAssessment)
    assert out.trust_state == TrustState.CAUTION
    assert out.assessment_status == AssessmentStatus.DEGRADED
    fresh = next(c for c in out.check_results if c.check_type == CheckType.FRESHNESS)
    assert fresh.check_state == CheckState.WARN
    assert ReasonCode.CONTROL_ROW_DEGRADED in fresh.reason_codes


def test_wi_2_1_4_regression_missing_required_check_row(
    risk_index,
    controls_index,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Absent required check → UNKNOWN check, UNRESOLVED trust, DEGRADED assessment."""
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
    assert isinstance(out, IntegrityAssessment)
    assert out.trust_state == TrustState.UNRESOLVED
    assert out.assessment_status == AssessmentStatus.DEGRADED
    lineage = next(c for c in out.check_results if c.check_type == CheckType.LINEAGE)
    assert lineage.check_state == CheckState.UNKNOWN
    assert lineage.reason_codes == (ReasonCode.CHECK_RESULT_MISSING,)


def test_wi_2_1_4_regression_legal_entity_desk_control_context_differs(
    risk_index,
    controls_index,
) -> None:
    """LE-UK-BANK vs LE-US-BROKER desks on SNAP-2026-01-12: pack differs on completeness (TRUSTED vs CAUTION)."""
    snap = "SNAP-2026-01-12"
    uk = get_integrity_assessment(
        desk_le("LE-UK-BANK"),
        MeasureType.VAR_1D_99,
        D_12,
        snap,
        risk_fixture_index=risk_index,
        controls_fixture_index=controls_index,
    )
    us = get_integrity_assessment(
        desk_le("LE-US-BROKER"),
        MeasureType.VAR_1D_99,
        D_12,
        snap,
        risk_fixture_index=risk_index,
        controls_fixture_index=controls_index,
    )
    assert isinstance(uk, IntegrityAssessment)
    assert isinstance(us, IntegrityAssessment)
    assert uk.trust_state == TrustState.TRUSTED
    assert us.trust_state == TrustState.CAUTION
    assert uk.assessment_status == AssessmentStatus.OK
    assert us.assessment_status == AssessmentStatus.OK
    assert uk != us
