from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Iterable

from .graph import Experiment
from .reproducibility import experiment_fingerprint, sha256_identity


@dataclass(frozen=True)
class ExecutionScope:
    """Content-bound description of what portion of a source graph is executed.

    A scope establishes execution identity only. It is not scientific evidence
    and cannot promote verification or proof status.
    """

    kind: str
    source_semantic_experiment_sha256: str
    source_full_experiment_sha256: str
    execution_semantic_experiment_sha256: str
    execution_full_experiment_sha256: str
    target_node_ids: tuple[str, ...]
    included_node_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.kind, str) or not self.kind.strip():
            raise ValueError("execution scope kind must be a non-empty string")
        for field_name in (
            "source_semantic_experiment_sha256",
            "source_full_experiment_sha256",
            "execution_semantic_experiment_sha256",
            "execution_full_experiment_sha256",
        ):
            value = getattr(self, field_name)
            if (
                not isinstance(value, str)
                or len(value) != 64
                or any(ch not in "0123456789abcdef" for ch in value)
            ):
                raise ValueError(f"{field_name} must be a lowercase SHA-256 digest")
        if any(not isinstance(node_id, str) or not node_id for node_id in self.target_node_ids):
            raise ValueError("target node ids must be non-empty strings")
        if any(not isinstance(node_id, str) or not node_id for node_id in self.included_node_ids):
            raise ValueError("included node ids must be non-empty strings")
        if len(self.target_node_ids) != len(set(self.target_node_ids)):
            raise ValueError("target node ids must be unique")
        if len(self.included_node_ids) != len(set(self.included_node_ids)):
            raise ValueError("included node ids must be unique")
        if not set(self.target_node_ids).issubset(self.included_node_ids):
            raise ValueError("execution-scope targets must be included in the executed graph")

    def payload(self) -> dict:
        return {
            "scope_schema": 1,
            "kind": self.kind,
            "source_semantic_experiment_sha256": self.source_semantic_experiment_sha256,
            "source_full_experiment_sha256": self.source_full_experiment_sha256,
            "execution_semantic_experiment_sha256": self.execution_semantic_experiment_sha256,
            "execution_full_experiment_sha256": self.execution_full_experiment_sha256,
            "target_node_ids": list(self.target_node_ids),
            "included_node_ids": list(self.included_node_ids),
            "proof_effect": "none",
        }

    @property
    def scope_sha256(self) -> str:
        return sha256_identity(self.payload())


def full_execution_scope(experiment: Experiment, *, kind: str = "full") -> ExecutionScope:
    semantic = experiment_fingerprint(experiment, include_layout=False)
    full = experiment_fingerprint(experiment, include_layout=True)
    return ExecutionScope(
        kind=kind.strip(),
        source_semantic_experiment_sha256=semantic,
        source_full_experiment_sha256=full,
        execution_semantic_experiment_sha256=semantic,
        execution_full_experiment_sha256=full,
        target_node_ids=(),
        included_node_ids=tuple(node.id for node in experiment.nodes),
    )


def build_upstream_subgraph(
    experiment: Experiment,
    target_node_ids: Iterable[str],
) -> tuple[Experiment, ExecutionScope]:
    """Return selected targets plus their complete transitive upstream closure.

    Source node/edge order is preserved. The returned experiment is a deep copy,
    so execution cannot mutate the source graph through parameter/metadata aliasing.
    """

    targets = tuple(sorted(set(str(node_id) for node_id in target_node_ids)))
    if not targets:
        raise ValueError("selected-upstream execution requires at least one target node")

    node_map = experiment.node_map()
    unknown = sorted(set(targets) - set(node_map))
    if unknown:
        raise ValueError(f"unknown target node ids: {unknown}")

    reverse: dict[str, set[str]] = {node_id: set() for node_id in node_map}
    for edge in experiment.edges:
        if edge.source_node not in node_map or edge.target_node not in node_map:
            raise ValueError("source experiment contains an edge referencing a missing node")
        reverse[edge.target_node].add(edge.source_node)

    included = set(targets)
    stack = list(targets)
    while stack:
        current = stack.pop()
        for upstream in sorted(reverse[current]):
            if upstream not in included:
                included.add(upstream)
                stack.append(upstream)

    nodes = [deepcopy(node) for node in experiment.nodes if node.id in included]
    edges = [
        deepcopy(edge)
        for edge in experiment.edges
        if edge.source_node in included and edge.target_node in included
    ]
    scoped = Experiment(
        schema_version=experiment.schema_version,
        name=experiment.name,
        nodes=nodes,
        edges=edges,
        metadata=deepcopy(experiment.metadata),
    )

    scope = ExecutionScope(
        kind="selected-upstream",
        source_semantic_experiment_sha256=experiment_fingerprint(
            experiment, include_layout=False
        ),
        source_full_experiment_sha256=experiment_fingerprint(
            experiment, include_layout=True
        ),
        execution_semantic_experiment_sha256=experiment_fingerprint(
            scoped, include_layout=False
        ),
        execution_full_experiment_sha256=experiment_fingerprint(
            scoped, include_layout=True
        ),
        target_node_ids=targets,
        included_node_ids=tuple(node.id for node in nodes),
    )
    return scoped, scope
