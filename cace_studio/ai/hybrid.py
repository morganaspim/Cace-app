from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np

from cace_studio.core.registry import ModuleRegistry
from cace_studio.core.types import EvidenceKind

from .math_features import hashed_text_sketch
from .memory import ExperienceMemory
from .planner import CandidateAtom, CombinationPlanner, GroupCandidate, PlannerConfig
from .ranker import RankerConfig, TinyResidualRanker


_EVIDENCE_STRENGTH = {
    EvidenceKind.EXPERIMENTAL: 0.15,
    EvidenceKind.NUMERICAL: 0.35,
    EvidenceKind.SYMBOLIC: 0.60,
    EvidenceKind.INTERVAL: 0.75,
    EvidenceKind.FORMAL: 1.00,
}

_TRAINING_WEIGHT = {
    "experimental": 1.0,
    "numerical": 1.25,
    "symbolic": 1.6,
    "interval-certified": 1.8,
    "formally-verified": 2.5,
}


@dataclass(frozen=True)
class HybridSuggestion:
    member_ids: tuple[str, ...]
    score: float
    neural_score: float
    proof_strength: float
    structural_cost: float
    learned_prior: float
    feature: np.ndarray


class HybridLocalAI:
    """Cheap mathematical planner + tiny learner for the optional local LLM.

    This class never creates verification evidence.  It produces advisory
    rankings and stores explicit user/proof/experiment feedback locally.
    """

    def __init__(
        self,
        registry: ModuleRegistry,
        *,
        state_dir: str | Path,
        sketch_dim: int = 128,
        hidden_dim: int = 32,
        seed: int = 0,
    ) -> None:
        if sketch_dim <= 0 or sketch_dim & (sketch_dim - 1):
            raise ValueError("sketch_dim must be a positive power of two")
        self.registry = registry
        self.sketch_dim = int(sketch_dim)
        self.seed = int(seed)
        self.state_dir = Path(state_dir).expanduser()
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.memory = ExperienceMemory(self.state_dir / "experience.sqlite3")
        self.ranker_path = self.state_dir / "ranker.npz"

        expected_dim = CombinationPlanner.ranker_input_dim(self.sketch_dim)
        if self.ranker_path.exists():
            try:
                ranker = TinyResidualRanker.load(self.ranker_path)
                if ranker.config.input_dim != expected_dim:
                    raise ValueError("stored ranker dimension does not match current sketch dimension")
                self.ranker = ranker
            except (OSError, ValueError, KeyError):
                self.ranker = TinyResidualRanker(
                    RankerConfig(expected_dim, hidden_dim=hidden_dim, seed=self.seed)
                )
        else:
            self.ranker = TinyResidualRanker(
                RankerConfig(expected_dim, hidden_dim=hidden_dim, seed=self.seed)
            )

    def _proof_strength(self, module_cls: type) -> float:
        status = getattr(module_cls, "proof_status", None)
        evidence = getattr(status, "evidence", set()) if status is not None else set()
        if not evidence:
            return 0.0
        return max(_EVIDENCE_STRENGTH.get(item, 0.0) for item in evidence)

    def _module_text(self, module_cls: type) -> str:
        metadata = module_cls.metadata
        inputs = " ".join(
            f"in:{port.name}:{port.type_name}:{port.unit or '-'}"
            for port in getattr(module_cls, "inputs", ())
        )
        outputs = " ".join(
            f"out:{port.name}:{port.type_name}:{port.unit or '-'}"
            for port in getattr(module_cls, "outputs", ())
        )
        params = " ".join(
            f"param:{param.name}:{param.type_name}:{param.unit or '-'}"
            for param in getattr(module_cls, "parameters", ())
        )
        assumptions = " ".join(getattr(metadata, "assumptions", ()) or ())
        status = getattr(module_cls, "proof_status", None)
        limitations = " ".join(getattr(status, "limitations", ()) or ())
        evidence = " ".join(
            sorted(item.value for item in getattr(status, "evidence", set()))
        ) if status is not None else ""
        return " | ".join(
            (
                metadata.module_id,
                metadata.name,
                metadata.category,
                metadata.description,
                assumptions,
                inputs,
                outputs,
                params,
                limitations,
                evidence,
            )
        )

    def _structural_cost(self, module_cls: type) -> float:
        """Cheap planner heuristic, explicitly not a runtime benchmark."""
        ports = len(getattr(module_cls, "inputs", ())) + len(getattr(module_cls, "outputs", ()))
        params = len(getattr(module_cls, "parameters", ()))
        return float(1.0 + 0.10 * ports + 0.05 * params)

    def _learned_priors(
        self,
        task_sketch: np.ndarray,
        *,
        generally_useful: bool,
    ) -> dict[str, float]:
        if generally_useful:
            experiences = self.memory.recent(limit=1000)
            weighted = [(experience, 1.0) for experience in experiences]
        else:
            experiences = self.memory.nearest(task_sketch, k=96, scan_limit=2500)
            weighted = [
                (experience, max(0.0, experience.similarity))
                for experience in experiences
                if experience.similarity > 0.0
            ]

        totals: dict[str, float] = {}
        masses: dict[str, float] = {}
        for experience, similarity_weight in weighted:
            evidence_weight = _TRAINING_WEIGHT.get(experience.evidence_kind, 1.0)
            weight = similarity_weight * evidence_weight
            signed_target = 2.0 * (experience.target - 0.5)
            for module_id in experience.candidate_ids:
                totals[module_id] = totals.get(module_id, 0.0) + weight * signed_target
                masses[module_id] = masses.get(module_id, 0.0) + abs(weight)

        return {
            module_id: totals[module_id] / masses[module_id]
            for module_id in totals
            if masses.get(module_id, 0.0) > 0.0
        }

    def _atoms(
        self,
        task_sketch: np.ndarray,
        *,
        generally_useful: bool,
    ) -> list[CandidateAtom]:
        priors = self._learned_priors(task_sketch, generally_useful=generally_useful)
        atoms: list[CandidateAtom] = []
        for module_cls in self.registry.classes():
            metadata = module_cls.metadata
            atoms.append(
                CandidateAtom(
                    atom_id=metadata.module_id,
                    sketch=hashed_text_sketch(
                        self._module_text(module_cls),
                        dim=self.sketch_dim,
                        seed=self.seed,
                    ),
                    static_cost=self._structural_cost(module_cls),
                    prior=float(priors.get(metadata.module_id, 0.0)),
                    proof_strength=self._proof_strength(module_cls),
                )
            )
        return atoms

    def _planner(self, *, generally_useful: bool, max_group: int) -> CombinationPlanner:
        if generally_useful:
            config = PlannerConfig(
                beam_width=40,
                min_group=1,
                max_group=max_group,
                cost_weight=0.10,
                prior_weight=0.38,
                proof_weight=0.38,
                diversity_weight=0.24,
                relevance_weight=0.0,
            )
        else:
            config = PlannerConfig(
                beam_width=40,
                min_group=1,
                max_group=max_group,
                cost_weight=0.08,
                prior_weight=0.22,
                proof_weight=0.28,
                diversity_weight=0.16,
                relevance_weight=0.42,
            )
        return CombinationPlanner(self.ranker, config)

    def suggest(
        self,
        task_text: str,
        *,
        generally_useful: bool = False,
        top_k: int = 8,
        max_group: int = 9,
    ) -> list[HybridSuggestion]:
        if max_group < 1:
            raise ValueError("max_group must be >= 1")
        task_sketch = hashed_text_sketch(
            task_text or "<general reusable CACE research>",
            dim=self.sketch_dim,
            seed=self.seed,
        )
        atoms = self._atoms(task_sketch, generally_useful=generally_useful)
        candidates = self._planner(
            generally_useful=generally_useful,
            max_group=max_group,
        ).search(
            atoms,
            context_sketch=task_sketch,
            top_k=top_k,
        )
        return [self._to_suggestion(candidate) for candidate in candidates]

    @staticmethod
    def _to_suggestion(candidate: GroupCandidate) -> HybridSuggestion:
        return HybridSuggestion(
            member_ids=candidate.member_ids,
            score=candidate.score,
            neural_score=candidate.neural_score,
            proof_strength=candidate.proof_strength,
            structural_cost=candidate.total_cost,
            learned_prior=candidate.prior,
            feature=candidate.feature.copy(),
        )

    def record_feedback(
        self,
        *,
        task_text: str,
        suggestion: HybridSuggestion,
        target: float,
        evidence_kind: str = "experimental",
        measured_cost: float = 0.0,
        metadata: dict | None = None,
    ) -> float:
        task_sketch = hashed_text_sketch(
            task_text or "<general reusable CACE research>",
            dim=self.sketch_dim,
            seed=self.seed,
        )
        self.memory.add(
            task_text=task_text,
            task_sketch=task_sketch,
            candidate_ids=suggestion.member_ids,
            candidate_feature=suggestion.feature,
            target=target,
            evidence_kind=evidence_kind,
            cost=measured_cost,
            metadata=metadata,
        )
        weight = _TRAINING_WEIGHT.get(evidence_kind, 1.0)
        loss = self.ranker.update(suggestion.feature, target, weight=weight)
        self.ranker.save(self.ranker_path)
        return loss

    def train_from_memory(self, *, epochs: int = 1, limit: int = 5000) -> int:
        examples = self.memory.training_examples(limit=limit)
        updates = 0
        for _ in range(max(0, int(epochs))):
            for feature, target, weight in examples:
                if feature.shape != (self.ranker.config.input_dim,):
                    continue
                self.ranker.update(feature, target, weight=weight)
                updates += 1
        if updates:
            self.ranker.save(self.ranker_path)
        return updates

    @staticmethod
    def prompt_context(
        suggestions: Iterable[HybridSuggestion],
        *,
        generally_useful: bool,
    ) -> str:
        rows = []
        for index, suggestion in enumerate(suggestions, start=1):
            rows.append(
                f"{index}. {', '.join(suggestion.member_ids)} "
                f"(planner={suggestion.score:.4f}, proof={suggestion.proof_strength:.3f}, "
                f"cost-heuristic={suggestion.structural_cost:.2f})"
            )
        mode = "generally useful / cross-workflow" if generally_useful else "task-focused"
        return (
            f"CACE cheap-math planner mode: {mode}. "
            "These are advisory candidate combinations, not proof or benchmark evidence.\n"
            + ("\n".join(rows) if rows else "No planner candidates were available.")
        )
