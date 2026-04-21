"""Unit tests for Quant Walker v2 typed contracts."""

from __future__ import annotations

import unittest
from datetime import date, datetime, timezone

from pydantic import ValidationError

from src.modules.risk_analytics.contracts import (
    HierarchyScope,
    MeasureType,
    NodeLevel,
    NodeRef,
    RiskChangeProfile,
    SummaryStatus,
    VolatilityChangeFlag,
    VolatilityRegime,
)
from src.walkers.quant import (
    QUANT_WALKER_VERSION,
    ChangeKind,
    ConfidenceLevel,
    InvestigationHint,
    QuantCaveatCode,
    QuantInterpretation,
    SignificanceLevel,
    summarize_change,
)


def _make_node_ref() -> NodeRef:
    return NodeRef(
        hierarchy_scope=HierarchyScope.TOP_OF_HOUSE,
        legal_entity_id=None,
        node_level=NodeLevel.DESK,
        node_id="DESK_CREDIT_INDEX",
        node_name="Credit Index",
    )


def _make_risk_change_profile() -> RiskChangeProfile:
    return RiskChangeProfile(
        node_ref=_make_node_ref(),
        measure_type=MeasureType.VAR_1D_99,
        as_of_date=date(2026, 1, 12),
        compare_to_date=date(2026, 1, 9),
        current_value=120.0,
        previous_value=100.0,
        delta_abs=20.0,
        delta_pct=0.2,
        rolling_mean=103.5,
        rolling_std=10.0,
        rolling_min=90.0,
        rolling_max=125.0,
        history_points_used=60,
        status=SummaryStatus.OK,
        status_reasons=(),
        snapshot_id="SNAP-2026-01-12",
        data_version="synthetic-risk-analytics-v1",
        service_version="risk-summary-service-v1",
        generated_at=datetime(2026, 1, 12, 18, 0, tzinfo=timezone.utc),
        volatility_regime=VolatilityRegime.ELEVATED,
        volatility_change_flag=VolatilityChangeFlag.RISING,
    )


class EnumClosureTest(unittest.TestCase):
    def test_change_kind_exact_members(self) -> None:
        self.assertEqual(
            {member.value for member in ChangeKind},
            {
                "FIRST_ORDER_DRIVEN",
                "SECOND_ORDER_DRIVEN",
                "COMBINED",
                "NEUTRAL",
                "INDETERMINATE",
            },
        )

    def test_significance_level_exact_members(self) -> None:
        self.assertEqual(
            {member.value for member in SignificanceLevel},
            {"LOW", "MODERATE", "HIGH", "INSUFFICIENT_DATA"},
        )

    def test_confidence_level_exact_members(self) -> None:
        self.assertEqual({member.value for member in ConfidenceLevel}, {"HIGH", "MEDIUM", "LOW"})

    def test_quant_caveat_code_exact_members(self) -> None:
        self.assertEqual(
            {member.value for member in QuantCaveatCode},
            {
                "COMPARE_POINT_MISSING",
                "HISTORY_INSUFFICIENT",
                "PROFILE_DEGRADED",
                "VOLATILITY_REGIME_INDETERMINATE",
                "VOLATILITY_CHANGE_FLAG_INDETERMINATE",
            },
        )

    def test_investigation_hint_exact_members(self) -> None:
        self.assertEqual(
            {member.value for member in InvestigationHint},
            {
                "INVESTIGATE_VOLATILITY_REGIME",
                "INVESTIGATE_VOLATILITY_CHANGE",
                "INVESTIGATE_DATA_COMPLETENESS",
                "INVESTIGATE_COMPARE_GAP",
                "INVESTIGATE_LARGE_FIRST_ORDER",
            },
        )


class QuantInterpretationContractTest(unittest.TestCase):
    def test_exact_field_order(self) -> None:
        self.assertEqual(
            list(QuantInterpretation.model_fields),
            [
                "risk_change_profile",
                "change_kind",
                "significance",
                "confidence",
                "caveats",
                "investigation_hints",
                "walker_version",
            ],
        )

    def test_replay_metadata_not_duplicated_at_top_level(self) -> None:
        self.assertNotIn("snapshot_id", QuantInterpretation.model_fields)
        self.assertNotIn("data_version", QuantInterpretation.model_fields)
        self.assertNotIn("service_version", QuantInterpretation.model_fields)
        self.assertNotIn("generated_at", QuantInterpretation.model_fields)

    def test_constructs_with_typed_upstream_profile(self) -> None:
        profile = _make_risk_change_profile()
        interpretation = QuantInterpretation(
            risk_change_profile=profile,
            change_kind=ChangeKind.COMBINED,
            significance=SignificanceLevel.HIGH,
            confidence=ConfidenceLevel.HIGH,
            caveats=(QuantCaveatCode.PROFILE_DEGRADED,),
            investigation_hints=(
                InvestigationHint.INVESTIGATE_LARGE_FIRST_ORDER,
                InvestigationHint.INVESTIGATE_VOLATILITY_CHANGE,
            ),
            walker_version=QUANT_WALKER_VERSION,
        )

        self.assertIs(interpretation.risk_change_profile, profile)
        self.assertEqual(interpretation.change_kind, ChangeKind.COMBINED)
        self.assertEqual(interpretation.significance, SignificanceLevel.HIGH)
        self.assertEqual(interpretation.confidence, ConfidenceLevel.HIGH)
        self.assertEqual(interpretation.walker_version, QUANT_WALKER_VERSION)

    def test_extra_fields_forbidden(self) -> None:
        with self.assertRaises(ValidationError):
            QuantInterpretation(
                risk_change_profile=_make_risk_change_profile(),
                change_kind=ChangeKind.NEUTRAL,
                significance=SignificanceLevel.LOW,
                confidence=ConfidenceLevel.MEDIUM,
                caveats=(),
                investigation_hints=(),
                walker_version=QUANT_WALKER_VERSION,
                unexpected_field="forbidden",
            )

    def test_frozen_model(self) -> None:
        interpretation = QuantInterpretation(
            risk_change_profile=_make_risk_change_profile(),
            change_kind=ChangeKind.NEUTRAL,
            significance=SignificanceLevel.LOW,
            confidence=ConfidenceLevel.MEDIUM,
            caveats=(),
            investigation_hints=(),
            walker_version=QUANT_WALKER_VERSION,
        )

        with self.assertRaises(ValidationError):
            interpretation.change_kind = ChangeKind.COMBINED  # type: ignore[misc]


class PublicSurfaceTest(unittest.TestCase):
    def test_quant_contract_surface_importable(self) -> None:
        self.assertTrue(callable(summarize_change))
        self.assertEqual(QUANT_WALKER_VERSION, "v2.0.0")
        self.assertTrue(QUANT_WALKER_VERSION)
