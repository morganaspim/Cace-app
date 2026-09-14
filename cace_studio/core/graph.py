from __future__ import annotations
from dataclasses import dataclass, field, asdict
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

@dataclass
class Experiment:
    schema_version: int = 1
    name: str = "Untitled"
    nodes: list[Node] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def node_map(self) -> dict[str, Node]:
        return {n.id: n for n in self.nodes}
