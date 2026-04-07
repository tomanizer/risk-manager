"""Loader and deterministic index for normalized control fixture packs (WI-2.1.2)."""

from __future__ import annotations

import json
import os
from collections import Counter
from datetime import date
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.modules.controls_integrity.contracts import (
    CheckState,
    CheckType,
    NormalizedControlRecord,
    ReasonCode,
    REQUIRED_CHECK_ORDER,
)
from src.modules.risk_analytics.contracts import MeasureType, NodeRef

FIXTURE_PATH_ENV_VAR = "CONTROLS_INTEGRITY_FIXTURE_PATH"
FIXTURE_PACK_RELATIVE_PATH = Path("fixtures/controls_integrity/normalized_controls_fixture_pack.json")


def resolve_default_controls_integrity_fixture_path() -> Path:
    env_path = os.environ.get(FIXTURE_PATH_ENV_VAR)
    if env_path:
        return Path(env_path).expanduser().resolve()

    current_path = Path(__file__).resolve()
    for parent in current_path.parents:
        candidate = parent / FIXTURE_PACK_RELATIVE_PATH
        if candidate.exists():
            return candidate

    raise FileNotFoundError(
        "could not locate controls integrity fixture pack from the current source tree",
    )


def _sorted_reason_codes(codes: tuple[ReasonCode, ...]) -> tuple[ReasonCode, ...]:
    return tuple(sorted(set(codes), key=lambda c: c.value))


def _validate_normalized_row_semantics(record: NormalizedControlRecord) -> None:
    """Fixture-only rules aligned with PRD-2.1 check semantics (upstream normalized row)."""
    state = record.check_state
    codes = record.reason_codes
    refs = record.evidence_refs

    if not _sorted_reason_codes(codes) == codes:
        raise ValueError("reason_codes must be deduplicated and lexicographically ascending")

    if state == CheckState.PASS:
        if codes:
            raise ValueError("PASS normalized rows must have empty reason_codes")
        if refs:
            raise ValueError("PASS normalized rows must have empty evidence_refs")
        return

    if state in (CheckState.WARN, CheckState.FAIL):
        if not refs:
            raise ValueError(
                f"{state} normalized rows must include at least one evidence_ref in fixtures",
            )
        return

    if state == CheckState.UNKNOWN:
        if not refs and ReasonCode.CHECK_RESULT_MISSING not in codes:
            raise ValueError(
                "UNKNOWN rows without evidence_refs must include CHECK_RESULT_MISSING",
            )
        return


class ControlsIntegrityFixtureSnapshot(BaseModel):
    """One pinned snapshot slice of normalized control rows."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    snapshot_id: str
    as_of_date: date
    rows: tuple[NormalizedControlRecord, ...] = Field(default_factory=tuple)

    @model_validator(mode="after")
    def validate_snapshot(self) -> ControlsIntegrityFixtureSnapshot:
        if not self.snapshot_id:
            raise ValueError("snapshot_id must be non-empty")
        for row in self.rows:
            if row.snapshot_id != self.snapshot_id:
                raise ValueError(
                    f"row snapshot_id {row.snapshot_id!r} does not match snapshot {self.snapshot_id!r}",
                )
            if row.as_of_date != self.as_of_date:
                raise ValueError(
                    f"row as_of_date {row.as_of_date!r} does not match snapshot date {self.as_of_date!r}",
                )
            _validate_normalized_row_semantics(row)
        return self


class ControlsIntegrityFixturePack(BaseModel):
    """Synthetic normalized-control fixture pack aligned to Phase 1 snapshot and calendar pins."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    service_version: str
    data_version: str
    calendar: tuple[date, ...]
    calendar_basis: str
    snapshots: tuple[ControlsIntegrityFixtureSnapshot, ...]

    @model_validator(mode="after")
    def validate_pack(self) -> ControlsIntegrityFixturePack:
        if not self.service_version.strip():
            raise ValueError("service_version must be non-empty")
        if not self.data_version.strip():
            raise ValueError("data_version must be non-empty")
        if not self.calendar_basis.strip():
            raise ValueError("calendar_basis must be non-empty (ADR-004 pinned replay context)")

        if len(self.calendar) < 5:
            raise ValueError("calendar must contain at least 5 business dates")
        if tuple(sorted(self.calendar)) != self.calendar:
            raise ValueError("calendar must be strictly ascending")
        if len(set(self.calendar)) != len(self.calendar):
            raise ValueError("calendar must not contain duplicate dates")

        snapshot_ids = {s.snapshot_id for s in self.snapshots}
        if len(snapshot_ids) != len(self.snapshots):
            raise ValueError("snapshot_id values must be unique")

        snapshot_dates = tuple(s.as_of_date for s in self.snapshots)
        if tuple(sorted(snapshot_dates)) != snapshot_dates:
            raise ValueError("snapshots must be ordered ascending by as_of_date")
        if len(set(snapshot_dates)) != len(self.snapshots):
            date_counts = Counter(snapshot_dates)
            duplicates = sorted([d for d, cnt in date_counts.items() if cnt > 1])
            raise ValueError(f"snapshot as_of_date values must be unique; duplicates: {duplicates}")

        calendar_dates = set(self.calendar)
        for snapshot in self.snapshots:
            if snapshot.as_of_date not in calendar_dates:
                raise ValueError("snapshot as_of_date values must be present in the pinned fixture calendar")

        return self

    def build_index(self) -> ControlsIntegrityFixtureIndex:
        return ControlsIntegrityFixtureIndex(self)


class ControlsIntegrityFixtureIndex:
    """Deterministic, replay-stable indexes over normalized control fixture rows."""

    def __init__(self, pack: ControlsIntegrityFixturePack) -> None:
        self.pack = pack
        self.snapshots_by_id: dict[str, ControlsIntegrityFixtureSnapshot] = {s.snapshot_id: s for s in pack.snapshots}
        self.snapshots_by_date: dict[date, ControlsIntegrityFixtureSnapshot] = {s.as_of_date: s for s in pack.snapshots}
        self._by_key: dict[tuple[tuple[str, str | None, str, str], str, date, str, str], NormalizedControlRecord] = {}

        for snapshot in pack.snapshots:
            for row in snapshot.rows:
                nk = self.node_key(row.node_ref)
                measure = row.measure_type.value
                ct = row.check_type.value
                key = (nk, measure, row.as_of_date, snapshot.snapshot_id, ct)
                if key in self._by_key:
                    raise ValueError(f"duplicate normalized control row for uniqueness key {key}")
                self._by_key[key] = row

    @staticmethod
    def node_key(node_ref: NodeRef) -> tuple[str, str | None, str, str]:
        """Stable target identity tuple (matches risk_analytics fixture index)."""
        return (
            node_ref.hierarchy_scope.value,
            node_ref.legal_entity_id,
            node_ref.node_level.value,
            node_ref.node_id,
        )

    def get_snapshot(self, snapshot_id: str) -> ControlsIntegrityFixtureSnapshot | None:
        return self.snapshots_by_id.get(snapshot_id)

    def get_snapshot_by_date(self, as_of_date: date) -> ControlsIntegrityFixtureSnapshot | None:
        return self.snapshots_by_date.get(as_of_date)

    def get_record(
        self,
        node_ref: NodeRef,
        measure_type: MeasureType,
        as_of_date: date,
        snapshot_id: str,
        check_type: CheckType,
    ) -> NormalizedControlRecord | None:
        nk = self.node_key(node_ref)
        key = (nk, measure_type.value, as_of_date, snapshot_id, check_type.value)
        return self._by_key.get(key)

    def get_record_by_resolved_snapshot(
        self,
        node_ref: NodeRef,
        measure_type: MeasureType,
        as_of_date: date,
        check_type: CheckType,
    ) -> NormalizedControlRecord | None:
        """Lookup using `as_of_date` as the resolved snapshot selector (one snapshot per date in pack)."""
        snapshot = self.snapshots_by_date.get(as_of_date)
        if snapshot is None:
            return None
        return self.get_record(node_ref, measure_type, as_of_date, snapshot.snapshot_id, check_type)

    def iter_records_for_target(
        self,
        node_ref: NodeRef,
        measure_type: MeasureType,
        as_of_date: date,
        snapshot_id: str,
    ) -> tuple[NormalizedControlRecord, ...]:
        """Return all checks for a target in canonical required-check order (missing types omitted)."""
        out: list[NormalizedControlRecord] = []
        for ct in REQUIRED_CHECK_ORDER:
            rec = self.get_record(node_ref, measure_type, as_of_date, snapshot_id, ct)
            if rec is not None:
                out.append(rec)
        return tuple(out)


def load_controls_integrity_fixture_pack(
    fixture_path: str | Path | None = None,
) -> ControlsIntegrityFixturePack:
    resolved = Path(fixture_path) if fixture_path is not None else resolve_default_controls_integrity_fixture_path()
    payload = json.loads(resolved.read_text(encoding="utf-8"))
    return ControlsIntegrityFixturePack.model_validate(payload)


def build_controls_integrity_fixture_index(
    fixture_path: str | Path | None = None,
) -> ControlsIntegrityFixtureIndex:
    return load_controls_integrity_fixture_pack(fixture_path).build_index()
