"""Shared typed service-error models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class _SharedOutcomeBase(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    operation: str
    status_code: str
    status_reasons: tuple[str, ...] = Field(default_factory=tuple)

    @model_validator(mode="before")
    @classmethod
    def validate_required_strings(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        values = dict(data)
        for field_name in ("operation", "status_code"):
            raw_value = values.get(field_name)
            if not isinstance(raw_value, str) or not raw_value.strip():
                raise ValueError(f"{field_name} must be a non-empty string")
            values[field_name] = raw_value.strip()

        raw_reasons = values.get("status_reasons")
        if raw_reasons is None:
            values["status_reasons"] = ()
            return values

        normalized_reasons: list[str] = []
        for reason in raw_reasons:
            if not isinstance(reason, str) or not reason.strip():
                raise ValueError("status_reasons entries must be non-empty strings")
            normalized_reasons.append(reason.strip())
        values["status_reasons"] = tuple(normalized_reasons)
        return values


class ServiceError(_SharedOutcomeBase):
    """Typed non-object service outcome."""


class RequestValidationFailure(_SharedOutcomeBase):
    """Typed request-validation failure outcome."""
