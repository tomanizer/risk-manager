"""Typed contracts for the Quant Walker v2 surface."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from src.modules.risk_analytics import RiskChangeProfile


NonEmptyStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]

QUANT_WALKER_VERSION: NonEmptyStr = "v2.0.0"


class ChangeKind(StrEnum):
    FIRST_ORDER_DRIVEN = "FIRST_ORDER_DRIVEN"
    SECOND_ORDER_DRIVEN = "SECOND_ORDER_DRIVEN"
    COMBINED = "COMBINED"
    NEUTRAL = "NEUTRAL"
    INDETERMINATE = "INDETERMINATE"


class SignificanceLevel(StrEnum):
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class ConfidenceLevel(StrEnum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class QuantCaveatCode(StrEnum):
    COMPARE_POINT_MISSING = "COMPARE_POINT_MISSING"
    HISTORY_INSUFFICIENT = "HISTORY_INSUFFICIENT"
    PROFILE_DEGRADED = "PROFILE_DEGRADED"
    VOLATILITY_REGIME_INDETERMINATE = "VOLATILITY_REGIME_INDETERMINATE"
    VOLATILITY_CHANGE_FLAG_INDETERMINATE = "VOLATILITY_CHANGE_FLAG_INDETERMINATE"


class InvestigationHint(StrEnum):
    INVESTIGATE_VOLATILITY_REGIME = "INVESTIGATE_VOLATILITY_REGIME"
    INVESTIGATE_VOLATILITY_CHANGE = "INVESTIGATE_VOLATILITY_CHANGE"
    INVESTIGATE_DATA_COMPLETENESS = "INVESTIGATE_DATA_COMPLETENESS"
    INVESTIGATE_COMPARE_GAP = "INVESTIGATE_COMPARE_GAP"
    INVESTIGATE_LARGE_FIRST_ORDER = "INVESTIGATE_LARGE_FIRST_ORDER"


class QuantInterpretation(BaseModel):
    """Typed Quant Walker interpretation built over a ``RiskChangeProfile``."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    risk_change_profile: RiskChangeProfile
    change_kind: ChangeKind
    significance: SignificanceLevel
    confidence: ConfidenceLevel
    caveats: tuple[QuantCaveatCode, ...] = Field(default_factory=tuple)
    investigation_hints: tuple[InvestigationHint, ...] = Field(default_factory=tuple)
    walker_version: NonEmptyStr


__all__ = [
    "QUANT_WALKER_VERSION",
    "ChangeKind",
    "ConfidenceLevel",
    "InvestigationHint",
    "QuantCaveatCode",
    "QuantInterpretation",
    "SignificanceLevel",
]
