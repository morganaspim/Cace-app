from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from cace_studio.core.types import port_connection_error


@dataclass(frozen=True)
class ProposedNode:
    proposal_id: str
    module_id: str
    name: str
    category: str
    position: tuple[float, float]


@dataclass(frozen=True)
class ProposedEdge:
    source_node: str
    source_port: str
    target_node: str
    target_port: str


@dataclass(frozen=True)
class UnresolvedInput:
    node_id: str
    module_id: str
    port_name: str
    type_name: str
    unit: str | None


@dataclass(frozen=True)
class ExperimentGraphProposal:
    title: str
    nodes: tuple[ProposedNode, ...]
    edges: tuple[ProposedEdge, ...]
    unresolved_required_inputs: tuple[UnresolvedInput, ...]
    skipped_modules: tuple[str, ...]
    rationale: str

    @property
    def is_empty(self) -> bool:
        return not self.nodes

    @property
    def is_execution_ready(self) -> bool:
        return bool(self.nodes) and not self.unresolved_required_inputs


def _canonical_module_ids(module_ids: Iterable[str], *, limit: int = 8) -> tuple[str, ...]:
    result = []
    seen = set()
    for value in module_ids:
        module_id = str(value).strip()
        if not module_id or module_id in seen:
            continue
        seen.add(module_id)
        result.append(module_id)
        if len(result) >= max(1, int(limit)):
            break
    return tuple(result)


def propose_experiment_graph(
    registry,
    module_ids: Iterable[str],
    *,
    title: str = "Proposed experiment",
    max_modules: int = 8,
) -> ExperimentGraphProposal:
    """Build a deterministic, compatibility-checked graph proposal.

    Only outputs from earlier proposal nodes may feed later inputs, so the
    generated graph is acyclic by construction. CACE's canonical port
    type/unit compatibility function is the sole connection rule.
    """
    requested = _canonical_module_ids(module_ids, limit=max_modules)
    modules = []
    skipped = []
    for module_id in requested:
        if not registry.contains(module_id):
            skipped.append(module_id)
            continue
        modules.append((module_id, registry.create(module_id)))

    nodes = []
    for index, (module_id, module) in enumerate(modules):
        row = index // 4
        col = index % 4
        nodes.append(
            ProposedNode(
                proposal_id=f"p{index + 1}",
                module_id=module_id,
                name=module.metadata.name,
                category=module.metadata.category,
                position=(40.0 + col * 240.0, 40.0 + row * 180.0),
            )
        )

    edges: list[ProposedEdge] = []
    unresolved: list[UnresolvedInput] = []

    for target_index, ((module_id, module), target_node) in enumerate(zip(modules, nodes)):
        occupied_inputs: set[str] = set()
        for target_port in module.inputs:
            if target_port.name in occupied_inputs:
                continue
            chosen = None
            # Prefer the nearest earlier compatible producer. This tends to
            # produce compact pipelines without assuming semantic meaning that
            # is not encoded in the port contracts.
            for source_index in range(target_index - 1, -1, -1):
                source_module = modules[source_index][1]
                source_node = nodes[source_index]
                for source_port in source_module.outputs:
                    if port_connection_error(source_port, target_port) is None:
                        chosen = (source_node, source_port)
                        break
                if chosen is not None:
                    break
            if chosen is not None:
                source_node, source_port = chosen
                edges.append(
                    ProposedEdge(
                        source_node=source_node.proposal_id,
                        source_port=source_port.name,
                        target_node=target_node.proposal_id,
                        target_port=target_port.name,
                    )
                )
                occupied_inputs.add(target_port.name)
            elif target_port.required:
                unresolved.append(
                    UnresolvedInput(
                        node_id=target_node.proposal_id,
                        module_id=module_id,
                        port_name=target_port.name,
                        type_name=target_port.type_name,
                        unit=target_port.unit,
                    )
                )

    if not nodes:
        rationale = "No registered associated modules were available to propose."
    elif unresolved:
        rationale = (
            "CACE connected only ports with exact compatible type/unit contracts. "
            "Some required inputs remain unresolved and must be supplied manually before execution."
        )
    else:
        rationale = (
            "All required inputs that need upstream producers were satisfied using "
            "exact compatible type/unit contracts from earlier proposal nodes."
        )

    return ExperimentGraphProposal(
        title=str(title).strip() or "Proposed experiment",
        nodes=tuple(nodes),
        edges=tuple(edges),
        unresolved_required_inputs=tuple(unresolved),
        skipped_modules=tuple(skipped),
        rationale=rationale,
    )
