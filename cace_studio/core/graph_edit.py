from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Callable, Iterable, Mapping
from uuid import uuid4

from .graph import Edge, Experiment, Node


@dataclass(frozen=True)
class FragmentNode:
    """One copied node expressed relative to the fragment's anchor."""

    source_id: str
    module_id: str
    params: Mapping[str, Any]
    relative_position: tuple[float, float]


@dataclass(frozen=True)
class GraphFragment:
    """GUI-independent copy/paste payload for a selected experiment subgraph."""

    origin: tuple[float, float]
    nodes: tuple[FragmentNode, ...]
    edges: tuple[Edge, ...]

    @property
    def source_ids(self) -> tuple[str, ...]:
        return tuple(node.source_id for node in self.nodes)


def _selected_ids(experiment: Experiment, node_ids: Iterable[str]) -> tuple[str, ...]:
    requested = tuple(dict.fromkeys(str(node_id) for node_id in node_ids))
    available = experiment.node_map()
    unknown = sorted(set(requested) - set(available))
    if unknown:
        raise ValueError(f"unknown node ids: {unknown}")
    return requested


def copy_graph_fragment(experiment: Experiment, node_ids: Iterable[str]) -> GraphFragment:
    """Copy selected nodes plus edges whose two endpoints are selected.

    Node order follows experiment order so serialization and tests are stable.
    Parameters are deep-copied so editing a pasted fragment cannot alias mutable
    parameter structures in the source graph.
    """

    selected = set(_selected_ids(experiment, node_ids))
    if not selected:
        raise ValueError("copy requires at least one selected node")

    nodes = [node for node in experiment.nodes if node.id in selected]
    origin_x = min(float(node.position[0]) for node in nodes)
    origin_y = min(float(node.position[1]) for node in nodes)
    fragment_nodes = tuple(
        FragmentNode(
            source_id=node.id,
            module_id=node.module_id,
            params=deepcopy(node.params),
            relative_position=(
                float(node.position[0]) - origin_x,
                float(node.position[1]) - origin_y,
            ),
        )
        for node in nodes
    )
    fragment_edges = tuple(
        edge
        for edge in experiment.edges
        if edge.source_node in selected and edge.target_node in selected
    )
    return GraphFragment(
        origin=(origin_x, origin_y),
        nodes=fragment_nodes,
        edges=fragment_edges,
    )


def _default_id_factory() -> str:
    return f"n_{uuid4().hex[:8]}"


def paste_graph_fragment(
    experiment: Experiment,
    fragment: GraphFragment,
    *,
    offset: tuple[float, float] = (30.0, 30.0),
    id_factory: Callable[[], str] | None = None,
) -> tuple[str, ...]:
    """Append a copied fragment transactionally and return the new node IDs.

    Validation and all ID generation happen before the experiment is mutated.
    Internal fragment edges are remapped to fresh node IDs. The caller owns any
    visual selection/history behavior.
    """

    if not fragment.nodes:
        raise ValueError("cannot paste an empty graph fragment")
    factory = id_factory or _default_id_factory

    source_ids = [node.source_id for node in fragment.nodes]
    if len(source_ids) != len(set(source_ids)):
        raise ValueError("fragment source node ids must be unique")
    source_set = set(source_ids)
    for edge in fragment.edges:
        if edge.source_node not in source_set or edge.target_node not in source_set:
            raise ValueError("fragment edge references a node outside the fragment")

    existing_ids = {node.id for node in experiment.nodes}
    new_ids: list[str] = []
    for _ in fragment.nodes:
        new_id = str(factory())
        if not new_id:
            raise ValueError("id_factory returned an empty node id")
        if new_id in existing_ids or new_id in new_ids:
            raise ValueError(f"id_factory produced duplicate node id: {new_id}")
        new_ids.append(new_id)

    id_map = dict(zip(source_ids, new_ids, strict=True))
    offset_x, offset_y = float(offset[0]), float(offset[1])
    origin_x, origin_y = fragment.origin

    pending_nodes = [
        Node(
            id=id_map[node.source_id],
            module_id=node.module_id,
            params=deepcopy(dict(node.params)),
            position=(
                float(origin_x) + float(node.relative_position[0]) + offset_x,
                float(origin_y) + float(node.relative_position[1]) + offset_y,
            ),
        )
        for node in fragment.nodes
    ]
    pending_edges = [
        Edge(
            id_map[edge.source_node],
            edge.source_port,
            id_map[edge.target_node],
            edge.target_port,
        )
        for edge in fragment.edges
    ]

    experiment.nodes.extend(pending_nodes)
    experiment.edges.extend(pending_edges)
    return tuple(new_ids)


def align_node_positions(
    experiment: Experiment,
    node_ids: Iterable[str],
    *,
    axis: str,
    strategy: str = "min",
) -> float:
    """Align selected node anchor coordinates on one axis.

    `axis` is `x` or `y`. `strategy=min` aligns to the left/top-most selected
    node. `strategy=mean` aligns the selected anchors to their arithmetic mean,
    which is useful for forming a vertical column or horizontal row.
    """

    selected_ids = _selected_ids(experiment, node_ids)
    if len(selected_ids) < 2:
        raise ValueError("alignment requires at least two selected nodes")
    if axis not in {"x", "y"}:
        raise ValueError("axis must be 'x' or 'y'")
    if strategy not in {"min", "mean"}:
        raise ValueError("strategy must be 'min' or 'mean'")

    selected = set(selected_ids)
    nodes = [node for node in experiment.nodes if node.id in selected]
    index = 0 if axis == "x" else 1
    coordinates = [float(node.position[index]) for node in nodes]
    target = min(coordinates) if strategy == "min" else sum(coordinates) / len(coordinates)

    for node in nodes:
        x, y = float(node.position[0]), float(node.position[1])
        node.position = (target, y) if axis == "x" else (x, target)
    return target
