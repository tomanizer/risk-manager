"""Quant Walker — thin typed delegate to risk_analytics (PRD-4.2).

v1 is delegation-only: the walker forwards inputs unchanged to the public
``get_risk_change_profile`` deterministic-service API and returns its typed
``RiskChangeProfile | ServiceError`` union without inspection, branching,
transformation, or augmentation. Quant semantics (status precedence,
rolling stats, volatility classification, replay metadata) remain in
``src/modules/risk_analytics/`` per PRD-1.1-v2.

Defaults on this signature mirror ``get_risk_change_profile`` exactly; any
future change to the underlying service defaults must be reflected here in
lockstep — the walker does not pin or override defaults. Per PRD-4.2 v1,
this package contains no telemetry, no wrapper types, and no walker-authored
narrative, significance, localization, or caveat synthesis.
"""

from __future__ import annotations

from datetime import date

from src.modules.risk_analytics import RiskChangeProfile, get_risk_change_profile
from src.modules.risk_analytics.contracts import MeasureType, NodeRef
from src.modules.risk_analytics.fixtures import FixtureIndex
from src.shared import ServiceError

def summarize_change(
    node_ref: NodeRef,
    measure_type: MeasureType,
    as_of_date: date,
    compare_to_date: date | None = None,
    lookback_window: int = 60,
    require_complete: bool = False,
    snapshot_id: str | None = None,
    fixture_index: FixtureIndex | None = None,
) -> RiskChangeProfile | ServiceError:
    """Delegate to ``get_risk_change_profile``; return its result unchanged.

    All ``ServiceError`` cases (``UNSUPPORTED_MEASURE``, ``MISSING_SNAPSHOT``,
    ``MISSING_NODE``) and all ``ValueError`` request-validation cases
    propagate from the service unchanged.
    """
    return get_risk_change_profile(
        node_ref,
        measure_type,
        as_of_date,
        compare_to_date,
        lookback_window,
        require_complete,
        snapshot_id,
        fixture_index,
    )
