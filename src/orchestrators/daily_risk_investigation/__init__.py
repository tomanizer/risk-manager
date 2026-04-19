"""Daily Risk Investigation Orchestrator package (PRD-5.1).

Public surface re-exported from this package:
- start_daily_run       — entry point (stage execution in WI-5.1.2)
- DailyRunResult        — canonical run-level state object
- TargetInvestigationResult — per-target investigation result
- TargetHandoffEntry    — per-target handoff entry
- HandoffStatus         — five-value challenge-gate enum
- TerminalRunStatus     — five-value terminal run status enum
- ReadinessState        — two-value readiness gate enum
- OutcomeKind           — two-value per-target discriminator enum
"""

from .orchestrator import (
    DailyRunResult,
    HandoffStatus,
    OutcomeKind,
    ReadinessState,
    TargetHandoffEntry,
    TargetInvestigationResult,
    TerminalRunStatus,
    start_daily_run,
)

__all__ = [
    "DailyRunResult",
    "HandoffStatus",
    "OutcomeKind",
    "ReadinessState",
    "TargetHandoffEntry",
    "TargetInvestigationResult",
    "TerminalRunStatus",
    "start_daily_run",
]
