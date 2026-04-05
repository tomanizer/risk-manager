"""Deterministic fixture-pack loader for risk analytics."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.modules.risk_analytics.contracts import (
    MeasureType,
    NodeRef,
    SummaryStatus,
)


DEFAULT_FIXTURE_PATH = (
    Path(__file__).resolve().parents[4]
    / "fixtures"
    / "risk_analytics"
    / "risk_summary_fixture_pack.json"
)


class FixtureRow(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    node_ref: NodeRef
    measure_type: MeasureType
    value: float
    status: SummaryStatus


class FixtureSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    snapshot_id: str
    as_of_date: date
    is_degraded: bool
    rows: tuple[FixtureRow, ...] = Field(default_factory=tuple)

    @model_validator(mode="after")
    def validate_snapshot(self) -> "FixtureSnapshot":
        if not self.snapshot_id:
            raise ValueError("snapshot_id must be non-empty")
        return self


class RiskSummaryFixturePack(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    service_version: str
    data_version: str
    calendar: tuple[date, ...]
    snapshots: tuple[FixtureSnapshot, ...]

    @model_validator(mode="after")
    def validate_pack(self) -> "RiskSummaryFixturePack":
        if not self.service_version:
            raise ValueError("service_version must be non-empty")
        if not self.data_version:
            raise ValueError("data_version must be non-empty")
        if len(self.calendar) < 5:
            raise ValueError("calendar must contain at least 5 business dates")
        if tuple(sorted(self.calendar)) != self.calendar:
            raise ValueError("calendar must be strictly ascending")
        if len(set(self.calendar)) != len(self.calendar):
            raise ValueError("calendar must not contain duplicate dates")

        snapshot_ids = {snapshot.snapshot_id for snapshot in self.snapshots}
        if len(snapshot_ids) != len(self.snapshots):
            raise ValueError("snapshot_id values must be unique")

        snapshot_dates = tuple(snapshot.as_of_date for snapshot in self.snapshots)
        if tuple(sorted(snapshot_dates)) != snapshot_dates:
            raise ValueError("snapshots must be ordered ascending by as_of_date")

        return self

    def build_index(self) -> "FixtureIndex":
        return FixtureIndex(self)


class FixtureIndex:
    """Stable helper indexes for the canonical fixture pack."""

    def __init__(self, pack: RiskSummaryFixturePack) -> None:
        self.pack = pack
        self.snapshots_by_id = {snapshot.snapshot_id: snapshot for snapshot in pack.snapshots}
        self.snapshots_by_date = {snapshot.as_of_date: snapshot for snapshot in pack.snapshots}
        self.rows_by_key: dict[tuple[str, str, str], FixtureRow] = {}
        self.rows_by_date_key: dict[tuple[date, str, str], FixtureRow] = {}

        for snapshot in pack.snapshots:
            for row in snapshot.rows:
                node_key = self.node_key(row.node_ref)
                key = (snapshot.snapshot_id, node_key, row.measure_type.value)
                date_key = (snapshot.as_of_date, node_key, row.measure_type.value)
                if key in self.rows_by_key:
                    raise ValueError(f"duplicate snapshot row for key {key}")
                if date_key in self.rows_by_date_key:
                    raise ValueError(f"duplicate dated row for key {date_key}")
                self.rows_by_key[key] = row
                self.rows_by_date_key[date_key] = row

    @staticmethod
    def node_key(node_ref: NodeRef) -> str:
        legal_entity = node_ref.legal_entity_id or "-"
        return "|".join(
            (
                node_ref.hierarchy_scope.value,
                legal_entity,
                node_ref.node_level.value,
                node_ref.node_id,
            )
        )

    def get_snapshot(self, snapshot_id: str) -> FixtureSnapshot | None:
        return self.snapshots_by_id.get(snapshot_id)

    def get_snapshot_by_date(self, as_of_date: date) -> FixtureSnapshot | None:
        return self.snapshots_by_date.get(as_of_date)

    def get_row(
        self,
        snapshot_id: str,
        node_ref: NodeRef,
        measure_type: MeasureType,
    ) -> FixtureRow | None:
        return self.rows_by_key.get(
            (snapshot_id, self.node_key(node_ref), measure_type.value)
        )

    def get_row_by_date(
        self,
        as_of_date: date,
        node_ref: NodeRef,
        measure_type: MeasureType,
    ) -> FixtureRow | None:
        return self.rows_by_date_key.get(
            (as_of_date, self.node_key(node_ref), measure_type.value)
        )


def load_risk_summary_fixture_pack(
    fixture_path: str | Path = DEFAULT_FIXTURE_PATH,
) -> RiskSummaryFixturePack:
    payload = json.loads(Path(fixture_path).read_text(encoding="utf-8"))
    return RiskSummaryFixturePack.model_validate(payload)


def build_fixture_index(
    fixture_path: str | Path = DEFAULT_FIXTURE_PATH,
) -> FixtureIndex:
    return load_risk_summary_fixture_pack(fixture_path).build_index()
