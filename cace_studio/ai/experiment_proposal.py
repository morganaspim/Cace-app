from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, replace
from itertools import combinations
import re
from typing import Callable, Iterable, Literal
from uuid import uuid4

from cace_studio.core.graph import Edge, Experiment, Node
from cace_studio.core.types import port_connection_error


ProposalStrategy = Literal["minimal", "balanced", "exploratory"]
PROPOSAL_STRATEGIES: tuple[ProposalStrategy, ...] = (
    "minimal",
    "balanced",
    "exploratory",
)


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
    description: str
    nodes: tuple[ProposedNode, ...]
    edges: tuple[ProposedEdge, ...]
    unresolved_required_inputs: tuple[UnresolvedInput, ...]
    skipped_modules: tuple[str, ...]
    rationale: str
    strategy: ProposalStrategy = "balanced"

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
    description: str = "",
    strategy: ProposalStrategy = "balanced",
    max_modules: int = 8,
) -> ExperimentGraphProposal:
    """Build a deterministic, compatibility-checked graph proposal.

    Only outputs from earlier proposal nodes may feed later inputs, so the
    generated graph is acyclic by construction. CACE's canonical port
    type/unit compatibility function is the sole connection rule.
    """
    if strategy not in PROPOSAL_STRATEGIES:
        raise ValueError(f"unknown proposal strategy: {strategy!r}")
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
        description=str(description).strip()[:20_000],
        strategy=strategy,
        nodes=tuple(nodes),
        edges=tuple(edges),
        unresolved_required_inputs=tuple(unresolved),
        skipped_modules=tuple(skipped),
        rationale=rationale,
    )




_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9_.-]{1,}")


def _tokens(text: str) -> set[str]:
    return {token.lower() for token in _TOKEN_RE.findall(str(text))}


def _proposal_quality(proposal: ExperimentGraphProposal) -> tuple[int, int, int, int]:
    """Lexicographic quality: readiness, more edges, fewer unresolved, fewer nodes."""
    return (
        int(proposal.is_execution_ready),
        len(proposal.edges),
        -len(proposal.unresolved_required_inputs),
        -len(proposal.nodes),
    )


def _minimal_module_ids(
    registry,
    requested: tuple[str, ...],
    *,
    title: str,
    description: str,
) -> tuple[str, ...]:
    valid = tuple(module_id for module_id in requested if registry.contains(module_id))
    if not valid:
        return ()
    best_ids = (valid[0],)
    best_key = None
    for size in range(1, min(3, len(valid)) + 1):
        for subset in combinations(valid, size):
            ordered_subset = _balanced_module_ids(registry, tuple(subset))
            proposal = propose_experiment_graph(
                registry,
                ordered_subset,
                title=title,
                description=description,
                strategy="minimal",
                max_modules=size,
            )
            useful = int(bool(proposal.edges) or (size == 1 and proposal.is_execution_ready))
            key = (
                useful,
                int(proposal.is_execution_ready),
                len(proposal.edges),
                -len(proposal.unresolved_required_inputs),
                -size,
                tuple(-valid.index(item) for item in subset),
            )
            if best_key is None or key > best_key:
                best_key = key
                best_ids = ordered_subset
        # Once a connected/readiness-positive proposal exists at a smaller size,
        # do not spend extra compute/modules merely for decoration.
        if best_key is not None and best_key[0] and size >= 2:
            break
    return tuple(best_ids)


def _compatible_input_count(placed_modules, candidate_module) -> int:
    count = 0
    for target_port in candidate_module.inputs:
        if any(
            port_connection_error(source_port, target_port) is None
            for _, source_module in placed_modules
            for source_port in source_module.outputs
        ):
            count += 1
    return count


def _balanced_module_ids(registry, requested: tuple[str, ...]) -> tuple[str, ...]:
    remaining = [
        (module_id, registry.create(module_id), index)
        for index, module_id in enumerate(requested)
        if registry.contains(module_id)
    ]
    if not remaining:
        return ()

    placed: list[tuple[str, object]] = []
    ordered: list[str] = []
    while remaining:
        scored = []
        for module_id, module, original_index in remaining:
            required = sum(1 for port in module.inputs if port.required)
            compatible = _compatible_input_count(placed, module)
            source_bonus = 1 if not module.inputs else 0
            producer_value = min(len(module.outputs), 4)
            scored.append(
                (
                    compatible,
                    source_bonus,
                    producer_value,
                    -required,
                    -original_index,
                    module_id,
                    module,
                )
            )
        scored.sort(
            key=lambda item: (
                -item[0],
                -item[1],
                -item[2],
                -item[3],
                -item[4],
                item[5],
            )
        )
        (
            _compatible,
            _source_bonus,
            _producer_value,
            _required,
            _index,
            module_id,
            module,
        ) = scored[0]
        ordered.append(module_id)
        placed.append((module_id, module))
        remaining = [item for item in remaining if item[0] != module_id]
    return tuple(ordered)


def _exploratory_extra_modules(
    registry,
    base_ids: tuple[str, ...],
    *,
    idea_text: str,
    limit: int = 2,
) -> tuple[str, ...]:
    query_tokens = _tokens(idea_text)
    base_categories = {
        registry.create(module_id).metadata.category
        for module_id in base_ids
        if registry.contains(module_id)
    }
    base_modules = [
        registry.create(module_id)
        for module_id in base_ids
        if registry.contains(module_id)
    ]
    candidates = []
    for cls in registry.classes():
        metadata = cls.metadata
        module_id = metadata.module_id
        if module_id in base_ids:
            continue
        text = " ".join(
            (
                module_id,
                metadata.name,
                metadata.category,
                metadata.description,
                " ".join(metadata.assumptions),
            )
        )
        overlap = len(query_tokens & _tokens(text))
        if overlap <= 0:
            continue
        category_novelty = 1 if metadata.category not in base_categories else 0
        module = registry.create(module_id)
        incoming_links = sum(
            1
            for target_port in module.inputs
            for base_module in base_modules
            for source_port in base_module.outputs
            if port_connection_error(source_port, target_port) is None
        )
        outgoing_links = sum(
            1
            for source_port in module.outputs
            for base_module in base_modules
            for target_port in base_module.inputs
            if port_connection_error(source_port, target_port) is None
        )
        compatible_links = incoming_links + outgoing_links
        interface_value = len(module.inputs) + len(module.outputs)
        candidates.append(
            (
                compatible_links,
                overlap,
                category_novelty,
                min(interface_value, 6),
                module_id,
            )
        )
    candidates.sort(
        key=lambda item: (-item[0], -item[1], -item[2], -item[3], item[4])
    )
    selected = [item[4] for item in candidates if item[0] > 0][: max(0, int(limit))]
    if len(selected) < max(0, int(limit)):
        # If no interface-compatible novelty remains, allow at most one
        # disconnected but strongly idea-relevant module; the preview will make
        # its unresolved state explicit rather than hiding the gap.
        for item in candidates:
            module_id = item[4]
            if module_id in selected:
                continue
            selected.append(module_id)
            break
    return tuple(selected[: max(0, int(limit))])


def propose_experiment_strategies(
    registry,
    module_ids: Iterable[str],
    *,
    title: str = "Proposed experiment",
    description: str = "",
    idea_context: str = "",
    max_modules: int = 8,
) -> dict[ProposalStrategy, ExperimentGraphProposal]:
    """Return three deterministic proposal policies for one Research Idea."""
    requested = _canonical_module_ids(module_ids, limit=max_modules)
    unknown_requested = tuple(
        module_id for module_id in requested if not registry.contains(module_id)
    )

    minimal_ids = _minimal_module_ids(
        registry,
        requested,
        title=title,
        description=description,
    )
    balanced_ids = _balanced_module_ids(registry, requested)
    exploratory_extras = _exploratory_extra_modules(
        registry,
        balanced_ids,
        idea_text=" ".join((title, description, idea_context)),
        limit=2,
    )
    exploratory_ids = _balanced_module_ids(
        registry,
        _canonical_module_ids(
            (*balanced_ids, *exploratory_extras),
            limit=max_modules,
        ),
    )

    proposals = {
        "minimal": propose_experiment_graph(
            registry,
            minimal_ids,
            title=title,
            description=description,
            strategy="minimal",
            max_modules=max_modules,
        ),
        "balanced": propose_experiment_graph(
            registry,
            balanced_ids,
            title=title,
            description=description,
            strategy="balanced",
            max_modules=max_modules,
        ),
        "exploratory": propose_experiment_graph(
            registry,
            exploratory_ids,
            title=title,
            description=description,
            strategy="exploratory",
            max_modules=max_modules,
        ),
    }

    strategy_rationales = {
        "minimal": (
            "Minimal strategy: smallest useful subset found within the first three-module "
            "search depth, prioritizing low node count and few unresolved inputs."
        ),
        "balanced": (
            "Balanced strategy: associated modules are greedily ordered to maximize compatible "
            "upstream coverage while remaining bounded and deterministic."
        ),
        "exploratory": (
            "Exploratory strategy: Balanced plus at most two locally registered modules selected "
            "from Grow-seeded idea text by metadata overlap and category diversity; all edges still "
            "require exact CACE type/unit compatibility."
        ),
    }
    return {
        strategy: replace(
            proposal,
            skipped_modules=tuple(
                dict.fromkeys((*proposal.skipped_modules, *unknown_requested))
            ),
            rationale=strategy_rationales[strategy] + " " + proposal.rationale,
        )
        for strategy, proposal in proposals.items()
    }

def materialize_experiment_proposal(
    experiment: Experiment,
    proposal: ExperimentGraphProposal,
    *,
    origin: tuple[float, float] = (40.0, 40.0),
    id_factory: Callable[[], str] | None = None,
) -> tuple[Experiment, dict[str, str]]:
    """Return a copied Experiment with the approved proposal appended.

    The input Experiment is never mutated. Proposal node ids are translated to
    fresh experiment node ids and every edge is mapped through that translation.
    """
    if proposal.is_empty:
        raise ValueError("cannot materialize an empty experiment proposal")

    factory = id_factory or (lambda: f"n_{uuid4().hex[:8]}")
    updated = deepcopy(experiment)
    existing_ids = {node.id for node in updated.nodes}
    mapping: dict[str, str] = {}

    for proposed in proposal.nodes:
        node_id = str(factory()).strip()
        attempts = 0
        while not node_id or node_id in existing_ids:
            attempts += 1
            if attempts > 1000:
                raise RuntimeError("could not allocate a unique experiment node id")
            node_id = str(factory()).strip()
        existing_ids.add(node_id)
        mapping[proposed.proposal_id] = node_id
        updated.nodes.append(
            Node(
                id=node_id,
                module_id=proposed.module_id,
                params={},
                position=(
                    float(origin[0]) + proposed.position[0],
                    float(origin[1]) + proposed.position[1],
                ),
            )
        )

    for edge in proposal.edges:
        try:
            source_node = mapping[edge.source_node]
            target_node = mapping[edge.target_node]
        except KeyError as exc:
            raise ValueError(
                f"proposal edge references unknown proposal node: {exc.args[0]}"
            ) from exc
        updated.edges.append(
            Edge(
                source_node=source_node,
                source_port=edge.source_port,
                target_node=target_node,
                target_port=edge.target_port,
            )
        )

    return updated, mapping
