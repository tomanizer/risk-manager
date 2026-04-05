"""History contracts for risk analytics."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .enums import MeasureType, SummaryStatus
from .node_ref import NodeRef


class RiskHistoryPoint(BaseModel):
    """Single dated risk history point."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    node_ref: NodeRef
    measure_type: MeasureType
    date: date
    value: float
    snapshot_id: str
    status: SummaryStatus

    @model_validator(mode="after")
    def validate_snapshot_id(self) -> "RiskHistoryPoint":
        if not self.snapshot_id:
            raise ValueError("snapshot_id must be non-empty")
        return self


class RiskHistorySeries(BaseModel):
    """Ordered history series for a node and measure."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    node_ref: NodeRef
    measure_type: MeasureType
    start_date: date
    end_date: date
    points: tuple[RiskHistoryPoint, ...] = Field(default_factory=tuple)
    status: SummaryStatus
    status_reasons: tuple[str, ...] = Field(default_factory=tuple)
    service_version: str

    @model_validator(mode="after")
    def validate_dates_and_points(self) -> "RiskHistorySeries":
        if self.start_date > self.end_date:
            raise ValueError("start_date must be on or before end_date")
        if not self.service_version:
            raise ValueError("service_version must be non-empty")
        ordered_dates = tuple(point.date for point in self.points)
        if any(
            ordered_dates[index] > ordered_dates[index + 1]
            for index in range(len(ordered_dates) - 1)
        ):
            raise ValueError("points must be ordered ascending by date")
        for point in self.points:
            if point.node_ref != self.node_ref:
                raise ValueError("all points must match series node_ref")
            if point.measure_type != self.measure_type:
                raise ValueError("all points must match series measure_type")
            if point.date < self.start_date or point.date > self.end_date:
                raise ValueError(
                    "all points must fall within the inclusive [start_date, end_date] range"
                )
        return self
