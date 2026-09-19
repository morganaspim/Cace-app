from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Sequence
import math

import numpy as np

from .math_features import combine_sketches, cosine_similarity
from .ranker import TinyResidualRanker


@dataclass(frozen=True)
class CandidateAtom:
    atom_id: str
    sketch: np.ndarray
    static_cost: float = 1.0
    prior: float = 0.0
    proof_strength: float = 0.0

    def __post_init__(self) -> None:
        vector = np.asarray(self.sketch, dtype=np.float64)
        if not self.atom_id:
            raise ValueError("atom_id must be nonempty")
        if vector.ndim != 1 or vector.size == 0 or not np.all(np.isfinite(vector)):
            raise ValueError("atom sketch must be a finite nonempty vector")
        if not math.isfinite(float(self.static_cost)) or self.static_cost < 0.0:
            raise ValueError("static_cost must be finite and nonnegative")
        if not math.isfinite(float(self.prior)):
            raise ValueError("prior must be finite")
        if not 0.0 <= float(self.proof_strength) <= 1.0:
            raise ValueError("proof_strength must be in [0,1]")


@dataclass(frozen=True)
class GroupCandidate:
    member_ids: tuple[str, ...]
    feature: np.ndarray
    member_feature: np.ndarray
    total_cost: float
    prior: float
    proof_strength: float
    neural_score: float
    score: float


@dataclass(frozen=True)
class PlannerConfig:
    beam_width: int = 32
    min_group: int = 1
    max_group: int = 9
    cost_weight: float = 0.08
    prior_weight: float = 0.25
    proof_weight: float = 0.30
    diversity_weight: float = 0.15
    relevance_weight: float = 0.35


class CombinationPlanner:
    """Bounded beam search over useful combinations instead of exhaustive n-choose-k search."""

    META_DIM = 4

    def __init__(self, ranker: TinyResidualRanker, config: PlannerConfig | None = None):
        self.ranker = ranker
        self.config = config or PlannerConfig()
        if self.config.beam_width <= 0:
            raise ValueError("beam_width must be positive")
        if self.config.min_group <= 0 or self.config.max_group < self.config.min_group:
            raise ValueError("invalid group-size bounds")

    @staticmethod
    def ranker_input_dim(sketch_dim: int) -> int:
        return 4 * int(sketch_dim) + CombinationPlanner.META_DIM

    def _group(
        self,
        members: Sequence[CandidateAtom],
        context_sketch: np.ndarray,
    ) -> GroupCandidate:
        member_feature = combine_sketches([member.sketch for member in members])
        sketch_dim = int(np.asarray(members[0].sketch).size)
        context = np.asarray(context_sketch, dtype=np.float64)
        if context.shape != (sketch_dim,):
            raise ValueError("context sketch must match atom sketch dimension")
        member_mean = member_feature[:sketch_dim]
        relevance_interaction = member_mean * context
        total_cost = float(sum(member.static_cost for member in members))
        prior = float(sum(member.prior for member in members) / len(members))
        proof = float(sum(member.proof_strength for member in members) / len(members))
        metadata = np.asarray(
            [math.log1p(len(members)), math.log1p(total_cost), prior, proof],
            dtype=np.float64,
        )
        feature = np.concatenate(
            (member_feature, context, relevance_interaction, metadata)
        )
        if feature.shape != (self.ranker.config.input_dim,):
            raise ValueError(
                f"ranker expects {self.ranker.config.input_dim} features, planner produced {feature.size}"
            )
        neural = float(self.ranker.predict(feature))
        relevance = max(0.0, cosine_similarity(member_mean, context))
        score = (
            neural
            + self.config.relevance_weight * relevance
            + self.config.prior_weight * prior
            + self.config.proof_weight * proof
            - self.config.cost_weight * math.log1p(total_cost)
        )
        return GroupCandidate(
            member_ids=tuple(member.atom_id for member in members),
            feature=feature,
            member_feature=member_feature,
            total_cost=total_cost,
            prior=prior,
            proof_strength=proof,
            neural_score=neural,
            score=float(score),
        )

    def _diverse_top(
        self, candidates: Sequence[GroupCandidate], limit: int
    ) -> list[GroupCandidate]:
        remaining = sorted(candidates, key=lambda item: (-item.score, item.member_ids))
        selected: list[GroupCandidate] = []
        while remaining and len(selected) < limit:
            best_index = 0
            best_adjusted = -math.inf
            for index, candidate in enumerate(remaining):
                redundancy = 0.0
                if selected:
                    redundancy = max(
                        max(
                            0.0,
                            cosine_similarity(candidate.member_feature, previous.member_feature),
                        )
                        for previous in selected
                    )
                adjusted = candidate.score - self.config.diversity_weight * redundancy
                if adjusted > best_adjusted:
                    best_adjusted = adjusted
                    best_index = index
            selected.append(remaining.pop(best_index))
        return selected

    def search(
        self,
        atoms: Sequence[CandidateAtom],
        *,
        context_sketch: np.ndarray | None = None,
        top_k: int = 10,
    ) -> list[GroupCandidate]:
        if top_k <= 0 or not atoms:
            return []

        ordered = sorted(atoms, key=lambda atom: atom.atom_id)
        sketch_dim = int(np.asarray(ordered[0].sketch).size)
        if self.ranker.config.input_dim != self.ranker_input_dim(sketch_dim):
            raise ValueError("ranker input dimension does not match atom sketch dimension")
        if any(np.asarray(atom.sketch).size != sketch_dim for atom in ordered):
            raise ValueError("all atom sketches must use the same dimension")
        context = (
            np.zeros(sketch_dim, dtype=np.float64)
            if context_sketch is None
            else np.asarray(context_sketch, dtype=np.float64)
        )
        if context.shape != (sketch_dim,) or not np.all(np.isfinite(context)):
            raise ValueError("context sketch must be a finite vector matching atom dimension")

        index_by_id = {atom.atom_id: index for index, atom in enumerate(ordered)}
        beam = self._diverse_top(
            [self._group([atom], context) for atom in ordered],
            self.config.beam_width,
        )

        all_candidates: list[GroupCandidate] = []
        if self.config.min_group <= 1:
            all_candidates.extend(beam)

        for size in range(2, min(self.config.max_group, len(ordered)) + 1):
            expanded: dict[tuple[str, ...], GroupCandidate] = {}
            for group in beam:
                last_index = max(index_by_id[item] for item in group.member_ids)
                members = [ordered[index_by_id[item]] for item in group.member_ids]
                for next_index in range(last_index + 1, len(ordered)):
                    candidate = self._group(members + [ordered[next_index]], context)
                    expanded[candidate.member_ids] = candidate
            if not expanded:
                break
            beam = self._diverse_top(
                list(expanded.values()),
                self.config.beam_width,
            )
            if size >= self.config.min_group:
                all_candidates.extend(beam)

        return self._diverse_top(all_candidates, top_k)
