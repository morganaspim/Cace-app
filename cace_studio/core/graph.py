from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Node:
    id: str
    module_id: str
    params: dict[str, Any] = field(default_factory=dict)
    position: tuple[float, float] = (0.0, 0.0)


@dataclass(frozen=True)
class Edge:
    source_node: str
    source_port: str
    target_node: str
    target_port: str


@dataclass(frozen=True)
class ExperimentGroup:
    """Named organizational subgraph membership.

    Groups do not add edges, hidden execution dependencies, or proof semantics.
    They are persisted presentation/workspace structure over existing node IDs.
    """

    id: str
    name: str
    node_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.id, str) or not self.id or self.id != self.id.strip():
            raise ValueError("group id must be a non-empty canonical string")
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("group name must be non-empty")
        if not isinstance(self.node_ids, tuple) or not self.node_ids:
            raise ValueError("group must contain at least one node id")
        if any(not isinstance(node_id, str) or not node_id for node_id in self.node_ids):
            raise ValueError("group node ids must be non-empty strings")
        if len(self.node_ids) != len(set(self.node_ids)):
            raise ValueError("group node ids must be unique")


@dataclass
class Experiment:
    # Scientific/computational graph schema. The .cace container schema is
    # versioned independently by core.serialization.
    schema_version: int = 1
    name: str = "Untitled"
    nodes: list[Node] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    groups: list[ExperimentGroup] = field(default_factory=list)

    def node_map(self) -> dict[str, Node]:
        return {n.id: n for n in self.nodes}
