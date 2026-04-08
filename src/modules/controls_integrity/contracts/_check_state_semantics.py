"""Shared PASS / WARN / FAIL / UNKNOWN invariants for reason_codes and evidence_refs.

Canonical rules match PRD-2.1 as encoded on ControlCheckResult (WI-2.1.5).

``evidence_refs`` is typed loosely to avoid a circular import with ``models.py``;
callers pass the same tuples used on ``ControlCheckResult`` / ``NormalizedControlRecord``.
"""

from __future__ import annotations

from typing import Any

from .enums import CheckState, ReasonCode


def _validate_check_state_reason_evidence(
    check_state: CheckState,
    reason_codes: tuple[ReasonCode, ...],
    evidence_refs: tuple[Any, ...],
) -> None:
    """Enforce check_state ↔ reason_codes ↔ evidence_refs invariants.

    Matches ``ControlCheckResult.validate_result`` semantics (including
    ``EVIDENCE_REF_MISSING`` for WARN/FAIL and UNKNOWN empty-evidence cases).
    """
    state = check_state

    if state == CheckState.PASS:
        if reason_codes:
            raise ValueError("reason_codes must be empty when check_state is PASS")
        if evidence_refs:
            raise ValueError("evidence_refs must be empty when check_state is PASS")
        return

    if state in (CheckState.WARN, CheckState.FAIL):
        if not evidence_refs and ReasonCode.EVIDENCE_REF_MISSING not in reason_codes:
            raise ValueError(f"evidence_refs must contain at least one reference when check_state is {state}")
        return

    if state == CheckState.UNKNOWN:
        if not evidence_refs:
            if ReasonCode.CHECK_RESULT_MISSING not in reason_codes and ReasonCode.EVIDENCE_REF_MISSING not in reason_codes:
                raise ValueError(
                    "evidence_refs may be empty for UNKNOWN check_state only when reason_codes includes CHECK_RESULT_MISSING or EVIDENCE_REF_MISSING"
                )
        return
