"""Scope-aware node reference contract."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, model_validator

from .enums import HierarchyScope, NodeLevel


class NodeRef(BaseModel):
    """Typed hierarchy address plus scope context."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    hierarchy_scope: HierarchyScope
    legal_entity_id: str | None
    node_level: NodeLevel
    node_id: str
    node_name: str | None = None

    @model_validator(mode="after")
    def validate_scope_and_level(self) -> "NodeRef":
        if not self.node_id:
            raise ValueError("node_id must be non-empty")

        if self.hierarchy_scope == HierarchyScope.TOP_OF_HOUSE:
            if self.legal_entity_id is not None:
                raise ValueError(
                    "legal_entity_id must be None for TOP_OF_HOUSE scope"
                )
            return self

        if not self.legal_entity_id:
            raise ValueError(
                "legal_entity_id must be provided for LEGAL_ENTITY scope"
            )

        if self.node_level == NodeLevel.FIRM:
            raise ValueError("FIRM level is only valid for TOP_OF_HOUSE scope")

        return self
