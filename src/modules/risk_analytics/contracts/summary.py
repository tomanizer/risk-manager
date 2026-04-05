"""Summary, delta, and change-profile contracts."""

from __future__ import annotations

from datetime import date, datetime
import math
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, model_validator

from .enums import (
    HierarchyScope,
    MeasureType,
    NodeLevel,
    SummaryStatus,
    VolatilityChangeFlag,
    VolatilityRegime,
)
from .node_ref import NodeRef


def _float_matches(actual: float, expected: float) -> bool:
    return math.isclose(actual, expected, rel_tol=1e-9, abs_tol=1e-12)


_MIRROR_FIELD_ADAPTERS = {
    "node_level": TypeAdapter(NodeLevel | None),
    "hierarchy_scope": TypeAdapter(HierarchyScope | None),
    "legal_entity_id": TypeAdapter(str | None),
}
_DATE_ADAPTER = TypeAdapter(date)
_FLOAT_ADAPTER = TypeAdapter(float)


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

    @model_validator(mode="before")
    @classmethod
    def validate_contract(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        values = dict(data)
        node_ref_value = values.get("node_ref")
        if node_ref_value is not None:
            node_ref = NodeRef.model_validate(node_ref_value)
            updates = {
                "node_level": node_ref.node_level,
                "hierarchy_scope": node_ref.hierarchy_scope,
                "legal_entity_id": node_ref.legal_entity_id,
            }
            for field_name, expected in updates.items():
                actual = values.get(field_name)
                if actual is None:
                    values[field_name] = expected
                    continue
                actual = _MIRROR_FIELD_ADAPTERS[field_name].validate_python(actual)
                if actual is not None and actual != expected:
                    raise ValueError(f"{field_name} must mirror node_ref exactly")
                values[field_name] = expected

        if "snapshot_id" in values and not values["snapshot_id"]:
            raise ValueError("snapshot_id must be non-empty")
        if "data_version" in values and not values["data_version"]:
            raise ValueError("data_version must be non-empty")
        if "service_version" in values and not values["service_version"]:
            raise ValueError("service_version must be non-empty")

        as_of_date = values.get("as_of_date")
        compare_to_date = values.get("compare_to_date")
        if as_of_date is not None and compare_to_date is not None:
            parsed_as_of_date = _DATE_ADAPTER.validate_python(as_of_date)
            parsed_compare_to_date = _DATE_ADAPTER.validate_python(compare_to_date)
            if parsed_compare_to_date > parsed_as_of_date:
                raise ValueError("compare_to_date must be on or before as_of_date")

        previous_value = values.get("previous_value")
        if previous_value is None:
            if values.get("delta_abs") is not None:
                raise ValueError("delta_abs must be None when previous_value is None")
            if values.get("delta_pct") is not None:
                raise ValueError("delta_pct must be None when previous_value is None")
            return values

        current_value = values.get("current_value")
        if current_value is None:
            return values
        current_value = _FLOAT_ADAPTER.validate_python(current_value)
        previous_value = _FLOAT_ADAPTER.validate_python(previous_value)
        expected_delta_abs = current_value - previous_value

        delta_abs = values.get("delta_abs")
        if delta_abs is None:
            values["delta_abs"] = expected_delta_abs
            delta_abs = expected_delta_abs
        else:
            delta_abs = _FLOAT_ADAPTER.validate_python(delta_abs)
        if not _float_matches(delta_abs, expected_delta_abs):
            raise ValueError("delta_abs must equal current_value - previous_value")

        if previous_value == 0:
            if values.get("delta_pct") is not None:
                raise ValueError("delta_pct must be None when previous_value is zero")
            values["delta_pct"] = None
            return values

        expected_delta_pct = delta_abs / previous_value
        delta_pct = values.get("delta_pct")
        if delta_pct is None:
            values["delta_pct"] = expected_delta_pct
            return values

        delta_pct = _FLOAT_ADAPTER.validate_python(delta_pct)
        if not _float_matches(delta_pct, expected_delta_pct):
            raise ValueError("delta_pct must equal delta_abs / previous_value")

        return values


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
