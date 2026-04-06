"""Shared typed service-error models."""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints


NonEmptyStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class _SharedOutcomeBase(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    operation: NonEmptyStr
    status_code: NonEmptyStr
    status_reasons: tuple[NonEmptyStr, ...] = Field(default_factory=tuple)


class ServiceError(_SharedOutcomeBase):
    """Typed non-object service outcome."""


class RequestValidationFailure(_SharedOutcomeBase):
    """Typed request-validation failure outcome."""
