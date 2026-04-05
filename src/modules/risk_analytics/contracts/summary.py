"""Summary, delta, and change-profile contracts."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .enums import (
    HierarchyScope,
    MeasureType,
    NodeLevel,
    SummaryStatus,
    VolatilityChangeFlag,
    VolatilityRegime,
)
from .node_ref import NodeRef


class _RiskContractBase(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    node_ref: NodeRef
    node_level: NodeLevel | None = None
    hierarchy_scope: HierarchyScope | None = None
    legal_entity_id: str | None = None
    measure_type: MeasureType
    as_of_date: date
    compare_to_date: date | None = None
    current_value: float
    previous_value: float | None = None
    delta_abs: float | None = None
    delta_pct: float | None = None
    status: SummaryStatus
    status_reasons: tuple[str, ...] = Field(default_factory=tuple)
    snapshot_id: str
    data_version: str
    service_version: str
    generated_at: datetime

    @model_validator(mode="after")
    def validate_contract(self) -> "_RiskContractBase":
        expected_level = self.node_ref.node_level
        expected_scope = self.node_ref.hierarchy_scope
        expected_legal_entity = self.node_ref.legal_entity_id

        updates = {
            "node_level": expected_level,
            "hierarchy_scope": expected_scope,
            "legal_entity_id": expected_legal_entity,
        }
        for field_name, expected in updates.items():
            actual = getattr(self, field_name)
            if actual is not None and actual != expected:
                raise ValueError(f"{field_name} must mirror node_ref exactly")
            object.__setattr__(self, field_name, expected)

        if not self.snapshot_id:
            raise ValueError("snapshot_id must be non-empty")
        if not self.data_version:
            raise ValueError("data_version must be non-empty")
        if not self.service_version:
            raise ValueError("service_version must be non-empty")

        if self.compare_to_date is not None and self.compare_to_date > self.as_of_date:
            raise ValueError("compare_to_date must be on or before as_of_date")

        if self.previous_value is None:
            if self.delta_abs is not None:
                raise ValueError("delta_abs must be None when previous_value is None")
            if self.delta_pct is not None:
                raise ValueError("delta_pct must be None when previous_value is None")
            return self

        expected_delta_abs = self.current_value - self.previous_value
        if self.delta_abs is None:
            object.__setattr__(self, "delta_abs", expected_delta_abs)
        elif self.delta_abs != expected_delta_abs:
            raise ValueError("delta_abs must equal current_value - previous_value")

        if self.previous_value == 0:
            if self.delta_pct is not None:
                raise ValueError("delta_pct must be None when previous_value is zero")
            return self

        expected_delta_pct = self.delta_abs / self.previous_value
        if self.delta_pct is None:
            object.__setattr__(self, "delta_pct", expected_delta_pct)
        elif self.delta_pct != expected_delta_pct:
            raise ValueError("delta_pct must equal delta_abs / previous_value")

        return self


class RiskDelta(_RiskContractBase):
    """First-order change only."""


class RiskSummary(_RiskContractBase):
    """Current value plus rolling-stat context."""

    rolling_mean: float | None = None
    rolling_std: float | None = None
    rolling_min: float | None = None
    rolling_max: float | None = None
    history_points_used: int | None = None

    @model_validator(mode="after")
    def validate_history_fields(self) -> "RiskSummary":
        if self.history_points_used is not None and self.history_points_used < 0:
            raise ValueError("history_points_used must be non-negative")
        return self


class RiskChangeProfile(RiskSummary):
    """First-order delta plus second-order volatility context."""

    volatility_regime: VolatilityRegime
    volatility_change_flag: VolatilityChangeFlag
