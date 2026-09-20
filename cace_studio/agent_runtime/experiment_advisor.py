from __future__ import annotations

from dataclasses import dataclass
import json
import math
from typing import Any, Mapping

from cace_studio.ai.compact_geometric_ranker import (
    FEATURE_NAMES,
    CompactGeometricRanker,
    GeometricCandidateFeatures,
)
from cace_studio.ai.provider import AIProvider
from cace_studio.core.capability_registry import QualifiedCapabilityRegistry
from cace_studio.core.executor import GraphExecutor
from cace_studio.core.graph import Edge, Experiment, Node
from cace_studio.core.registry import ModuleRegistry
from cace_studio.core.reproducibility import experiment_fingerprint

from .canvas_mutation import (
    CanvasMutationOperation,
    CanvasPreviewRequest,
)


_ALLOWED_STRATEGIES = ("minimal", "balanced", "exploratory")


@dataclass(frozen=True)
class ExperimentProposal:
    strategy: str
    title: str
    rationale: str
    experiment: Experiment
    neural_score: float
    features: GeometricCandidateFeatures
    proof_effect: str = "none"
    promotion_authority: bool = False

    def __post_init__(self) -> None:
        if self.strategy not in _ALLOWED_STRATEGIES:
            raise ValueError("unsupported proposal strategy")
        if not self.title.strip():
            raise ValueError("proposal title must be non-empty")
        if not math.isfinite(self.neural_score):
            raise ValueError("proposal score must be finite")
        if self.proof_effect != "none" or self.promotion_authority:
            raise ValueError("experiment proposal cannot carry proof authority")

    def to_dict(self) -> dict[str, Any]:
        return {
            "strategy": self.strategy,
            "title": self.title,
            "rationale": self.rationale,
            "semantic_experiment_sha256": experiment_fingerprint(
                self.experiment, include_layout=False
            ),
            "node_count": len(self.experiment.nodes),
            "edge_count": len(self.experiment.edges),
            "neural_score": self.neural_score,
            "feature_names": list(FEATURE_NAMES),
            "features": list(self.features.values),
            "proof_effect": "none",
            "promotion_authority": False,
        }


class LocalExperimentAdvisor:
    """Strict local-LLM -> qualified graph -> neural ranking adapter.

    The LLM produces JSON candidates only. CACE then parses, capability-gates,
    validates, ranks, and converts candidates into preview-only canvas mutations.
    """

    def __init__(
        self,
        *,
        provider: AIProvider,
        registry: ModuleRegistry,
        capabilities: QualifiedCapabilityRegistry,
        ranker: CompactGeometricRanker | None = None,
        max_response_chars: int = 64_000,
        max_nodes_per_proposal: int = 24,
    ) -> None:
        if capabilities.registry is not registry:
            raise ValueError("capabilities must wrap the supplied registry")
        if max_response_chars <= 0:
            raise ValueError("max_response_chars must be positive")
        if max_nodes_per_proposal <= 0:
            raise ValueError("max_nodes_per_proposal must be positive")
        self.provider = provider
        self.registry = registry
        self.capabilities = capabilities
        self.ranker = ranker or CompactGeometricRanker()
        self.max_response_chars = int(max_response_chars)
        self.max_nodes_per_proposal = int(max_nodes_per_proposal)

    def _system_message(self) -> str:
        return (
            "You are the local CACE-KSEE experiment proposal model. "
            "Return exactly one JSON object and no markdown. "
            "You may use only modules and exact connection paths in the supplied "
            "capability catalog. Produce up to three proposals using strategies "
            "minimal, balanced, exploratory. Do not claim proof, verification, "
            "formal status, or module availability beyond the catalog. "
            "Schema: {\"proposals\":[{\"strategy\":\"minimal|balanced|exploratory\","
            "\"title\":\"...\",\"rationale\":\"...\","
            "\"nodes\":[{\"id\":\"...\",\"module_id\":\"...\","
            "\"params\":{},\"position\":[x,y]}],"
            "\"edges\":[{\"source_node\":\"...\",\"source_port\":\"...\","
            "\"target_node\":\"...\",\"target_port\":\"...\"}]}]}"
        )

    def _catalog_payload(self) -> dict[str, Any]:
        modules = []
        for module_id in self.capabilities.module_ids("ai"):
            payload = self.capabilities.module_payload(module_id)
            modules.append(
                {
                    "module_id": module_id,
                    "name": payload["metadata"]["name"],
                    "summary": payload["public_help"]["summary"],
                    "inputs": payload["inputs"],
                    "outputs": payload["outputs"],
                    "parameters": payload["parameters"],
                    "qualified_connections": payload["compatible_targets"],
                }
            )
        return {
            "schema": "cace-ai-experiment-catalog-v1",
            "modules": modules,
            "capability_policy_sha256": self.capabilities.policy_sha256,
            "proof_effect": "none",
        }

    def suggest(self, objective: str) -> tuple[ExperimentProposal, ...]:
        if not isinstance(objective, str) or not objective.strip():
            raise ValueError("objective must be a non-empty string")
        user_payload = {
            "objective": objective.strip(),
            "catalog": self._catalog_payload(),
        }
        raw = self.provider.chat(
            [
                {"role": "system", "content": self._system_message()},
                {
                    "role": "user",
                    "content": json.dumps(
                        user_payload,
                        sort_keys=True,
                        separators=(",", ":"),
                    ),
                },
            ],
            temperature=0.15,
        )
        if len(raw) > self.max_response_chars:
            raise ValueError("local proposal response exceeded configured size limit")
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError("local proposal model must return one JSON object") from exc
        if not isinstance(payload, dict) or set(payload) != {"proposals"}:
            raise ValueError("proposal response must contain only proposals")
        proposals_raw = payload["proposals"]
        if not isinstance(proposals_raw, list) or not 1 <= len(proposals_raw) <= 3:
            raise ValueError("proposal response must contain one to three proposals")

        seen_strategies: set[str] = set()
        validated: list[tuple[str, str, str, Experiment, GeometricCandidateFeatures]] = []
        for index, item in enumerate(proposals_raw):
            if not isinstance(item, dict):
                raise ValueError(f"proposals[{index}] must be an object")
            allowed = {"strategy", "title", "rationale", "nodes", "edges"}
            unknown = sorted(set(item) - allowed)
            missing = sorted({"strategy", "title", "nodes", "edges"} - set(item))
            if unknown or missing:
                raise ValueError(
                    f"proposals[{index}] fields mismatch missing={missing} extra={unknown}"
                )
            strategy = str(item["strategy"]).strip().lower()
            if strategy not in _ALLOWED_STRATEGIES:
                raise ValueError(f"unsupported strategy: {strategy}")
            if strategy in seen_strategies:
                raise ValueError(f"duplicate strategy: {strategy}")
            seen_strategies.add(strategy)

            experiment = self._experiment_from_item(item, index=index)
            self.capabilities.validate_experiment(experiment, surface="ai")
            GraphExecutor(self.registry).validate(experiment)
            features = self._features(experiment, strategy)
            validated.append(
                (
                    strategy,
                    str(item["title"]).strip(),
                    str(item.get("rationale", "")).strip(),
                    experiment,
                    features,
                )
            )

        scores = self.ranker.score_many([item[4] for item in validated])
        proposals = [
            ExperimentProposal(
                strategy=item[0],
                title=item[1],
                rationale=item[2],
                experiment=item[3],
                features=item[4],
                neural_score=float(scores[index]),
            )
            for index, item in enumerate(validated)
        ]
        return tuple(
            sorted(
                proposals,
                key=lambda proposal: (
                    -proposal.neural_score,
                    _ALLOWED_STRATEGIES.index(proposal.strategy),
                ),
            )
        )

    def _experiment_from_item(self, item: Mapping[str, Any], *, index: int) -> Experiment:
        nodes_raw = item["nodes"]
        edges_raw = item["edges"]
        if not isinstance(nodes_raw, list) or not isinstance(edges_raw, list):
            raise ValueError(f"proposals[{index}] nodes/edges must be arrays")
        if not 1 <= len(nodes_raw) <= self.max_nodes_per_proposal:
            raise ValueError(
                f"proposals[{index}] must contain 1..{self.max_nodes_per_proposal} nodes"
            )
        if len(edges_raw) > self.max_nodes_per_proposal * 3:
            raise ValueError(f"proposals[{index}] contains too many edges")

        nodes: list[Node] = []
        for node_index, raw in enumerate(nodes_raw):
            if not isinstance(raw, dict):
                raise ValueError(f"proposals[{index}].nodes[{node_index}] must be object")
            allowed = {"id", "module_id", "params", "position"}
            unknown = sorted(set(raw) - allowed)
            if unknown:
                raise ValueError(
                    f"proposals[{index}].nodes[{node_index}] unknown fields {unknown}"
                )
            position = raw.get("position", [0.0, 0.0])
            if (
                not isinstance(position, (list, tuple))
                or len(position) != 2
                or not all(isinstance(value, (int, float)) for value in position)
            ):
                raise ValueError("proposal node position must contain two numbers")
            params = raw.get("params", {})
            if not isinstance(params, dict):
                raise ValueError("proposal node params must be object")
            nodes.append(
                Node(
                    id=str(raw["id"]),
                    module_id=str(raw["module_id"]),
                    params=dict(params),
                    position=(float(position[0]), float(position[1])),
                )
            )

        if len({node.id for node in nodes}) != len(nodes):
            raise ValueError("proposal node ids must be unique")

        edges: list[Edge] = []
        by_id = {node.id: node for node in nodes}
        for edge_index, raw in enumerate(edges_raw):
            if not isinstance(raw, dict):
                raise ValueError(f"proposals[{index}].edges[{edge_index}] must be object")
            required = {
                "source_node",
                "source_port",
                "target_node",
                "target_port",
            }
            if set(raw) != required:
                raise ValueError(
                    f"proposals[{index}].edges[{edge_index}] must contain exact edge fields"
                )
            source_node = str(raw["source_node"])
            target_node = str(raw["target_node"])
            if source_node not in by_id or target_node not in by_id:
                raise ValueError("proposal edge references missing node")
            reason = self.capabilities.connection_error(
                by_id[source_node].module_id,
                str(raw["source_port"]),
                by_id[target_node].module_id,
                str(raw["target_port"]),
            )
            if reason is not None:
                raise ValueError(f"proposal contains unqualified connection: {reason}")
            edges.append(
                Edge(
                    source_node=source_node,
                    source_port=str(raw["source_port"]),
                    target_node=target_node,
                    target_port=str(raw["target_port"]),
                )
            )

        return Experiment(
            name=str(item.get("title", "AI proposal")),
            nodes=nodes,
            edges=edges,
            metadata={
                "proposal_strategy": str(item["strategy"]),
                "proposal_source": "local-ai",
                "proof_effect": "none",
            },
        )

    def _features(
        self,
        experiment: Experiment,
        strategy: str,
    ) -> GeometricCandidateFeatures:
        module_ids = [node.module_id for node in experiment.nodes]
        module_payloads = [
            self.capabilities.module_payload(module_id) for module_id in module_ids
        ]

        edge_fraction = 1.0 if not experiment.edges else sum(
            1
            for edge in experiment.edges
            if self.capabilities.connection_error(
                experiment.node_map()[edge.source_node].module_id,
                edge.source_port,
                experiment.node_map()[edge.target_node].module_id,
                edge.target_port,
            )
            is None
        ) / len(experiment.edges)
        workflow_coverage = sum(
            1 for payload in module_payloads if payload["workflow_ids"]
        ) / len(module_payloads)
        verifier_fraction = sum(
            1
            for module_id in module_ids
            if module_id.startswith("verify.")
        ) / len(module_ids)
        geometric_fraction = sum(
            1
            for payload in module_payloads
            if "geometry" in payload["metadata"]["category"].lower()
            or "geometry" in payload["metadata"]["description"].lower()
        ) / len(module_payloads)

        possible_edges = max(1, len(experiment.nodes) * max(1, len(experiment.nodes) - 1))
        sparsity = max(0.0, 1.0 - len(experiment.edges) / possible_edges)
        resource_headroom = max(0.0, 1.0 - len(experiment.nodes) / self.max_nodes_per_proposal)
        target_depth = {"minimal": 2.0, "balanced": 4.0, "exploratory": 6.0}[strategy]
        depth_fit = max(0.0, 1.0 - abs(len(experiment.nodes) - target_depth) / 10.0)
        novelty = {"minimal": 0.2, "balanced": 0.55, "exploratory": 0.9}[strategy]

        values = {
            "user_relevance": 0.5,
            "workflow_coverage": workflow_coverage,
            "typed_connection_fraction": edge_fraction,
            "invariant_preservation": verifier_fraction,
            "symmetry_reduction": 0.5,
            "geometric_structure": geometric_fraction,
            "novelty": novelty,
            "mastery_frontier": 0.5,
            "proof_alignment": verifier_fraction,
            "resource_headroom": resource_headroom,
            "sparsity": sparsity,
            "composition_depth_fit": depth_fit,
        }
        return GeometricCandidateFeatures.from_mapping(values)

    @staticmethod
    def to_canvas_preview_request(proposal: ExperimentProposal) -> CanvasPreviewRequest:
        operations: list[CanvasMutationOperation] = []
        for node in proposal.experiment.nodes:
            operations.append(
                CanvasMutationOperation(
                    action="add_node",
                    node_id=node.id,
                    module_id=node.module_id,
                    params=dict(node.params),
                    position=node.position,
                )
            )
        for edge in proposal.experiment.edges:
            operations.append(
                CanvasMutationOperation(
                    action="add_edge",
                    source_node=edge.source_node,
                    source_port=edge.source_port,
                    target_node=edge.target_node,
                    target_port=edge.target_port,
                )
            )
        return CanvasPreviewRequest(tuple(operations))
