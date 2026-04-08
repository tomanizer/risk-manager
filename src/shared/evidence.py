"""Shared typed evidence reference (PRD-2.1, ADR-003).

Canonical cross-module shape for pointers to supporting artifacts. Modules
should import this type from ``src.shared`` rather than redefining it.
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, model_validator


class EvidenceRef(BaseModel):
    """Typed evidence reference with stable fields for replay and audit."""

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
