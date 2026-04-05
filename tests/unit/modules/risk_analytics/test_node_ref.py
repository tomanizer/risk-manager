"""NodeRef validation tests."""

from __future__ import annotations

import unittest

from pydantic import ValidationError

from src.modules.risk_analytics.contracts import HierarchyScope, NodeLevel, NodeRef


class NodeRefTestCase(unittest.TestCase):
    def test_top_of_house_firm_is_valid(self) -> None:
        node_ref = NodeRef(
            hierarchy_scope=HierarchyScope.TOP_OF_HOUSE,
            legal_entity_id=None,
            node_level=NodeLevel.FIRM,
            node_id="FIRM_GRP",
            node_name="Firm Group",
        )

        self.assertEqual(node_ref.node_level, NodeLevel.FIRM)

    def test_top_of_house_rejects_legal_entity(self) -> None:
        with self.assertRaises(ValidationError):
            NodeRef(
                hierarchy_scope=HierarchyScope.TOP_OF_HOUSE,
                legal_entity_id="LE-UK-BANK",
                node_level=NodeLevel.DESK,
                node_id="DESK_RATES_MACRO",
            )

    def test_legal_entity_requires_legal_entity_id(self) -> None:
        with self.assertRaises(ValidationError):
            NodeRef(
                hierarchy_scope=HierarchyScope.LEGAL_ENTITY,
                legal_entity_id=None,
                node_level=NodeLevel.DESK,
                node_id="DESK_RATES_MACRO",
            )

    def test_legal_entity_rejects_firm_level(self) -> None:
        with self.assertRaises(ValidationError):
            NodeRef(
                hierarchy_scope=HierarchyScope.LEGAL_ENTITY,
                legal_entity_id="LE-UK-BANK",
                node_level=NodeLevel.FIRM,
                node_id="FIRM_GRP",
            )


if __name__ == "__main__":
    unittest.main()
