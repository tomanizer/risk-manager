"""Typed contract models for the controls integrity assessment service."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, model_validator

from src.modules.risk_analytics.contracts import (
    HierarchyScope,
    MeasureType,
    NodeLevel,
    NodeRef,
)

from ._check_state_semantics import _validate_check_state_reason_evidence
from .enums import (
    AssessmentStatus,
    CheckState,
    CheckType,
    FalseSignalRisk,
    ReasonCode,
    TrustState,
)

# ---------------------------------------------------------------------------
# Required check ordering — canonical, replay-stable order enforced in
# IntegrityAssessment.check_results.
# ---------------------------------------------------------------------------
REQUIRED_CHECK_ORDER: tuple[CheckType, ...] = (
    CheckType.FRESHNESS,
    CheckType.COMPLETENESS,
    CheckType.LINEAGE,
    CheckType.RECONCILIATION,
    CheckType.PUBLICATION_READINESS,
)

# ---------------------------------------------------------------------------
# TypeAdapters for mirror-field validation (matches risk_analytics pattern).
# ---------------------------------------------------------------------------
_MIRROR_FIELD_ADAPTERS: dict[str, TypeAdapter[Any]] = {
    "node_level": TypeAdapter(NodeLevel | None),
    "hierarchy_scope": TypeAdapter(HierarchyScope | None),
    "legal_entity_id": TypeAdapter(str | None),
}
_NODE_REF_ADAPTER = TypeAdapter(NodeRef)
_DATE_ADAPTER = TypeAdapter(date)


def _deduplicated_sorted_reason_codes(
    codes: tuple[ReasonCode, ...],
) -> tuple[ReasonCode, ...]:
    """Return deduplicated, lexicographically ascending reason codes."""
    return tuple(sorted(set(codes), key=lambda c: c.value))


class EvidenceRef(BaseModel):
    """Typed evidence reference.

    Module-local in this slice (WI-2.1.1).  A repo-wide shared extraction
    remains an open question governed by ADR-003 and must not happen here.
    """

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    evidence_type: str
    evidence_id: str
    source_as_of_date: date | None = None
    snapshot_id: str | None = None

    @model_validator(mode="after")
    def validate_fields(self) -> "EvidenceRef":
        if not self.evidence_type:
            raise ValueError("evidence_type must be non-empty")
        if not self.evidence_id:
            raise ValueError("evidence_id must be non-empty")
        return self


class NormalizedControlRecord(BaseModel):
    """Canonical upstream normalized control record shape per required check.

    One uniqueness-resolved record per (node_ref, measure_type, as_of_date,
    snapshot_id, check_type).  Upstream normalization defects are out of scope
    for this service.
    """

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    node_ref: NodeRef
    measure_type: MeasureType
    as_of_date: date
    snapshot_id: str
    check_type: CheckType
    check_state: CheckState
    reason_codes: tuple[ReasonCode, ...] = Field(default_factory=tuple)
    evidence_refs: tuple[EvidenceRef, ...] = Field(default_factory=tuple)
    is_row_degraded: bool = False

    @model_validator(mode="before")
    @classmethod
    def normalize_reason_codes(cls, data: Any) -> Any:
        """Deduplicate and sort reason_codes before field assignment (mirror ControlCheckResult)."""
        if not isinstance(data, dict):
            return data
        values = dict(data)
        raw_codes = values.get("reason_codes")
        if raw_codes is not None:
            if isinstance(raw_codes, str):
                raise ValueError("reason_codes must be provided as a list or tuple of ReasonCode values, not a string")  # fmt: skip
            if not isinstance(raw_codes, (list, tuple)):
                raise ValueError("reason_codes must be provided as a list or tuple of ReasonCode values")  # fmt: skip
            parsed: tuple[ReasonCode, ...] = tuple(ReasonCode(c) if not isinstance(c, ReasonCode) else c for c in raw_codes)  # fmt: skip
            values["reason_codes"] = _deduplicated_sorted_reason_codes(parsed)
        return values

    @model_validator(mode="after")
    def validate_record(self) -> "NormalizedControlRecord":
        if not self.snapshot_id:
            raise ValueError("snapshot_id must be non-empty")
        _validate_check_state_reason_evidence(self.check_state, self.reason_codes, self.evidence_refs)
        return self


class ControlCheckResult(BaseModel):
    """Result for one required control check within an IntegrityAssessment."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    check_type: CheckType
    check_state: CheckState
    reason_codes: tuple[ReasonCode, ...] = Field(default_factory=tuple)
    evidence_refs: tuple[EvidenceRef, ...] = Field(default_factory=tuple)

    @model_validator(mode="before")
    @classmethod
    def normalize_reason_codes(cls, data: Any) -> Any:
        """Deduplicate and sort reason_codes before field assignment."""
        if not isinstance(data, dict):
            return data
        values = dict(data)
        raw_codes = values.get("reason_codes")
        if raw_codes is not None:
            if isinstance(raw_codes, str):
                raise ValueError("reason_codes must be provided as a list or tuple of ReasonCode values, not a string")  # fmt: skip
            if not isinstance(raw_codes, (list, tuple)):
                raise ValueError("reason_codes must be provided as a list or tuple of ReasonCode values")  # fmt: skip
            parsed: tuple[ReasonCode, ...] = tuple(ReasonCode(c) if not isinstance(c, ReasonCode) else c for c in raw_codes)  # fmt: skip
            values["reason_codes"] = _deduplicated_sorted_reason_codes(parsed)
        return values

    @model_validator(mode="after")
    def validate_result(self) -> "ControlCheckResult":
        _validate_check_state_reason_evidence(self.check_state, self.reason_codes, self.evidence_refs)
        return self


class IntegrityAssessment(BaseModel):
    """Deterministic trust assessment for one target in a pinned snapshot context.

    Validation rules enforced here:
    - node_level, hierarchy_scope, legal_entity_id mirror node_ref exactly
    - hierarchy_scope = TOP_OF_HOUSE requires legal_entity_id = None
    - hierarchy_scope = LEGAL_ENTITY requires non-empty legal_entity_id
    - check_results contains exactly one result per required check in canonical order
    - blocking_reason_codes and cautionary_reason_codes are deduplicated and sorted
    - snapshot_id, data_version, service_version are required non-empty
    """

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    node_ref: NodeRef
    node_level: NodeLevel | None = None
    hierarchy_scope: HierarchyScope | None = None
    legal_entity_id: str | None = None

    measure_type: MeasureType
    as_of_date: date

    trust_state: TrustState
    false_signal_risk: FalseSignalRisk
    assessment_status: AssessmentStatus

    blocking_reason_codes: tuple[ReasonCode, ...] = Field(default_factory=tuple)
    cautionary_reason_codes: tuple[ReasonCode, ...] = Field(default_factory=tuple)
    check_results: tuple[ControlCheckResult, ...]

    snapshot_id: str
    data_version: str
    service_version: str
    generated_at: datetime

    @model_validator(mode="before")
    @classmethod
    def normalize_contract(cls, data: Any) -> Any:
        """Mirror node_ref fields, normalize reason-code tuples."""
        if not isinstance(data, dict):
            return data

        values = dict(data)

        # Mirror fields from node_ref
        node_ref_value = values.get("node_ref")
        if node_ref_value is not None:
            node_ref = _NODE_REF_ADAPTER.validate_python(node_ref_value)
            values["node_ref"] = node_ref
            expected = {
                "node_level": node_ref.node_level,
                "hierarchy_scope": node_ref.hierarchy_scope,
                "legal_entity_id": node_ref.legal_entity_id,
            }
            for field_name, expected_value in expected.items():
                raw_actual = values.get(field_name)
                if raw_actual is None or raw_actual == expected_value:
                    values[field_name] = expected_value
                    continue
                validated_actual = _MIRROR_FIELD_ADAPTERS[field_name].validate_python(raw_actual)
                if validated_actual is not None and validated_actual != expected_value:
                    raise ValueError(f"{field_name} must mirror node_ref exactly")
                values[field_name] = expected_value

        # Non-empty version fields (strip before checking — str_strip_whitespace
        # runs after the before-validator, so whitespace-only must be caught here)
        for field_name in ("snapshot_id", "data_version", "service_version"):
            if field_name in values and not str(values[field_name]).strip():
                raise ValueError(f"{field_name} must be non-empty")

        # Deduplicate and sort aggregate reason-code lists
        for field_name in ("blocking_reason_codes", "cautionary_reason_codes"):
            raw = values.get(field_name)
            if raw is None:
                continue
            if not isinstance(raw, (list, tuple)):
                raise ValueError(f"{field_name} must be provided as a list or tuple of reason codes")
            parsed_codes: tuple[ReasonCode, ...] = tuple(ReasonCode(c) if not isinstance(c, ReasonCode) else c for c in raw)  # fmt: skip
            values[field_name] = _deduplicated_sorted_reason_codes(parsed_codes)

        return values

    @model_validator(mode="after")
    def validate_assessment(self) -> "IntegrityAssessment":
        # Verify exactly the required check types, in canonical order
        expected = list(REQUIRED_CHECK_ORDER)
        actual = [r.check_type for r in self.check_results]
        if actual != expected:
            raise ValueError(f"check_results must contain exactly one result for each required check in order {expected!r}; got {actual!r}")  # fmt: skip

        return self
