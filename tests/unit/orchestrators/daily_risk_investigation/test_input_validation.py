"""WI-5.1.2 — Input validation (Stage 1 — intake).

Asserts that start_daily_run raises ValueError for the documented invalid
input shapes per PRD-5.1 §"Trigger prerequisites" and §"Error handling".
"""

from __future__ import annotations

import unittest
from datetime import date

import pytest

from src.modules.risk_analytics.contracts import (
    HierarchyScope,
    MeasureType,
    NodeLevel,
    NodeRef,
)
from src.orchestrators.daily_risk_investigation import start_daily_run


_AS_OF_DATE = date(2024, 1, 15)
_NODE_REF = NodeRef(
    hierarchy_scope=HierarchyScope.TOP_OF_HOUSE,
    legal_entity_id=None,
    node_level=NodeLevel.FIRM,
    node_id="FIRM-001",
)


class InputValidationTest(unittest.TestCase):
    def test_empty_snapshot_id_raises_value_error(self) -> None:
        with self.assertRaises(ValueError):
            start_daily_run(
                as_of_date=_AS_OF_DATE,
                snapshot_id="",
                candidate_targets=(_NODE_REF,),
                measure_type=MeasureType.VAR_1D_99,
            )

    def test_whitespace_only_snapshot_id_raises_value_error(self) -> None:
        with self.assertRaises(ValueError):
            start_daily_run(
                as_of_date=_AS_OF_DATE,
                snapshot_id="   ",
                candidate_targets=(_NODE_REF,),
                measure_type=MeasureType.VAR_1D_99,
            )

    def test_none_snapshot_id_raises_value_error(self) -> None:
        with self.assertRaises(ValueError):
            start_daily_run(
                as_of_date=_AS_OF_DATE,
                snapshot_id=None,  # type: ignore[arg-type]
                candidate_targets=(_NODE_REF,),
                measure_type=MeasureType.VAR_1D_99,
            )

    def test_empty_candidate_targets_raises_value_error(self) -> None:
        with self.assertRaises(ValueError):
            start_daily_run(
                as_of_date=_AS_OF_DATE,
                snapshot_id="snap-001",
                candidate_targets=(),
                measure_type=MeasureType.VAR_1D_99,
            )


@pytest.mark.parametrize(
    "snapshot_id",
    ["", "   ", "\t", "\n"],
)
def test_blank_snapshot_id_variants_raise(snapshot_id: str) -> None:
    with pytest.raises(ValueError):
        start_daily_run(
            as_of_date=_AS_OF_DATE,
            snapshot_id=snapshot_id,
            candidate_targets=(_NODE_REF,),
            measure_type=MeasureType.VAR_1D_99,
        )


if __name__ == "__main__":
    unittest.main()
