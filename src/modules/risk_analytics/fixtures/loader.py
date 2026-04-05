"""Deterministic fixture-pack loader for risk analytics."""

from __future__ import annotations

import json
import os
from collections import Counter
from datetime import date
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.modules.risk_analytics.contracts import (
    MeasureType,
    NodeRef,
    SummaryStatus,
)


FIXTURE_PATH_ENV_VAR = "RISK_ANALYTICS_FIXTURE_PATH"
FIXTURE_PACK_RELATIVE_PATH = Path("fixtures/risk_analytics/risk_summary_fixture_pack.json")


def resolve_default_fixture_path() -> Path:
    env_path = os.environ.get(FIXTURE_PATH_ENV_VAR)
    if env_path:
        return Path(env_path).expanduser().resolve()

    current_path = Path(__file__).resolve()
    for parent in current_path.parents:
        candidate = parent / FIXTURE_PACK_RELATIVE_PATH
        if candidate.exists():
            return candidate

    raise FileNotFoundError("could not locate risk summary fixture pack from the current source tree")


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
        if len(set(snapshot_dates)) != len(snapshot_dates):
            date_counts = Counter(snapshot_dates)
            duplicates = sorted([d for d, cnt in date_counts.items() if cnt > 1])
            raise ValueError(f"snapshot as_of_date values must be unique; duplicates: {duplicates}")
        calendar_dates = set(self.calendar)
        for snapshot in self.snapshots:
            if snapshot.as_of_date not in calendar_dates:
                raise ValueError("snapshot as_of_date values must be present in the pinned fixture calendar")

        return self

    def build_index(self) -> "FixtureIndex":
        return FixtureIndex(self)


class FixtureIndex:
    """Stable helper indexes for the canonical fixture pack."""

    def __init__(self, pack: RiskSummaryFixturePack) -> None:
        self.pack = pack
        self.snapshots_by_id = {snapshot.snapshot_id: snapshot for snapshot in pack.snapshots}
        self.snapshots_by_date = {snapshot.as_of_date: snapshot for snapshot in pack.snapshots}
        self.rows_by_key: dict[tuple[str, tuple[str, str | None, str, str], str], FixtureRow] = {}
        self.rows_by_date_key: dict[tuple[date, tuple[str, str | None, str, str], str], FixtureRow] = {}
        self.supported_measures: set[MeasureType] = set()
        self.available_node_measures: set[tuple[tuple[str, str | None, str, str], str]] = set()

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
                self.supported_measures.add(row.measure_type)
                self.available_node_measures.add((node_key, row.measure_type.value))

    @staticmethod
    def node_key(node_ref: NodeRef) -> tuple[str, str | None, str, str]:
        return (
            node_ref.hierarchy_scope.value,
            node_ref.legal_entity_id,
            node_ref.node_level.value,
            node_ref.node_id,
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
        return self.rows_by_key.get((snapshot_id, self.node_key(node_ref), measure_type.value))

    def get_row_by_date(
        self,
        as_of_date: date,
        node_ref: NodeRef,
        measure_type: MeasureType,
    ) -> FixtureRow | None:
        return self.rows_by_date_key.get((as_of_date, self.node_key(node_ref), measure_type.value))


def load_risk_summary_fixture_pack(
    fixture_path: str | Path | None = None,
) -> RiskSummaryFixturePack:
    resolved = Path(fixture_path) if fixture_path is not None else resolve_default_fixture_path()
    payload = json.loads(resolved.read_text(encoding="utf-8"))
    return RiskSummaryFixturePack.model_validate(payload)


def build_fixture_index(
    fixture_path: str | Path | None = None,
) -> FixtureIndex:
    return load_risk_summary_fixture_pack(fixture_path).build_index()
