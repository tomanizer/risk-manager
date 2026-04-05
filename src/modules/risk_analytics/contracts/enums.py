"""Enumerations for the risk analytics contract layer."""

from __future__ import annotations

from enum import StrEnum


class MeasureType(StrEnum):
    VAR_1D_99 = "VAR_1D_99"
    VAR_10D_99 = "VAR_10D_99"
    ES_97_5 = "ES_97_5"


class HierarchyScope(StrEnum):
    TOP_OF_HOUSE = "TOP_OF_HOUSE"
    LEGAL_ENTITY = "LEGAL_ENTITY"


class NodeLevel(StrEnum):
    FIRM = "FIRM"
    DIVISION = "DIVISION"
    AREA = "AREA"
    DESK = "DESK"
    BOOK = "BOOK"
    POSITION = "POSITION"
    TRADE = "TRADE"


class SummaryStatus(StrEnum):
    OK = "OK"
    PARTIAL = "PARTIAL"
    MISSING_COMPARE = "MISSING_COMPARE"
    MISSING_HISTORY = "MISSING_HISTORY"
    MISSING_NODE = "MISSING_NODE"
    MISSING_SNAPSHOT = "MISSING_SNAPSHOT"
    UNSUPPORTED_MEASURE = "UNSUPPORTED_MEASURE"
    DEGRADED = "DEGRADED"


class VolatilityRegime(StrEnum):
    LOW = "LOW"
    NORMAL = "NORMAL"
    ELEVATED = "ELEVATED"
    HIGH = "HIGH"
    INSUFFICIENT_HISTORY = "INSUFFICIENT_HISTORY"


class VolatilityChangeFlag(StrEnum):
    STABLE = "STABLE"
    RISING = "RISING"
    FALLING = "FALLING"
    INSUFFICIENT_HISTORY = "INSUFFICIENT_HISTORY"
