from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from hashlib import sha256
from itertools import combinations
import math
import random
import re
from typing import Iterable, Sequence


_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9_]{1,}|[0-9]+(?:\.[0-9]+)?")


def _tokens(text: str) -> tuple[str, ...]:
    return tuple(token.lower() for token in _TOKEN_RE.findall(text))


def _stable_unit_interval(text: str) -> float:
    digest = sha256(text.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") / float(2**64 - 1)


@dataclass(frozen=True)
class ResearchFragment:
    fragment_id: str
    source: str
    kind: str
    text: str
    evidence_note: str = "navigation/research context only; not verification evidence"


@dataclass(frozen=True)
class RankedFragment:
    fragment: ResearchFragment
    score: float


@dataclass(frozen=True)
class ConceptGroup:
    fragment_ids: tuple[str, ...]
    score: float
    novelty: float
    diversity: float
    rationale: str


@dataclass(frozen=True)
class ExpertRoute:
    expert_id: str
    score: float
    instruction: str


@dataclass(frozen=True)
class GrowResult:
    query: str
    seed: int
    chaos: float
    routes: tuple[ExpertRoute, ...]
    retrieved: tuple[RankedFragment, ...]
    walk: tuple[str, ...]
    groups: tuple[ConceptGroup, ...]
    next_steps: tuple[str, ...]
    neural_rerank_used: bool = False
    neural_rerank_note: str = ""

    def context_text(self, *, max_fragments: int = 8, max_chars: int = 9000) -> str:
        """Render bounded research context for a local model.

        The text is deliberately labeled as navigation/research material so a
        model cannot confuse retrieval with formal qualification.
        """
        blocks = [
            "CACE LOCAL HYBRID RESEARCH CONTEXT",
            "This context is navigation and hypothesis-generation material only.",
            "It is never mathematical proof, verification evidence, or permission to mutate CACE records.",
            "",
            "Expert routes: " + ", ".join(route.expert_id for route in self.routes),
            (
                "Neural rerank: ON — " + self.neural_rerank_note
                if self.neural_rerank_used
                else "Neural rerank: OFF/FALLBACK — " + (
                    self.neural_rerank_note or "deterministic sparse ranking"
                )
            ),
            "Semantic walk: " + " -> ".join(self.walk),
            "",
        ]
        used = sum(len(item) + 1 for item in blocks)
        for ranked in self.retrieved[:max_fragments]:
            frag = ranked.fragment
            block = (
                f"[source={frag.source} kind={frag.kind} score={ranked.score:.4f}]\n"
                f"{frag.text.strip()}\n"
                f"Evidence note: {frag.evidence_note}\n"
            )
            if used + len(block) > max_chars:
                break
            blocks.append(block)
            used += len(block)
        if self.groups:
            blocks.append("Candidate concept combinations:")
            for group in self.groups[:6]:
                blocks.append(
                    f"- {group.fragment_ids}: score={group.score:.4f}; "
                    f"novelty={group.novelty:.3f}; diversity={group.diversity:.3f}; "
                    f"{group.rationale}"
                )
        if self.next_steps:
            blocks.append("Cheap next-step proposals:")
            blocks.extend(f"- {step}" for step in self.next_steps)
        return "\n".join(blocks)


_EXPERTS: dict[str, tuple[tuple[str, ...], str]] = {
    "proof": (
        ("proof", "lean", "theorem", "axiom", "lemma", "formal", "rigor", "certificate"),
        "Preserve hypotheses and distinguish conjecture, numerical evidence, and formally qualified theorems.",
    ),
    "experiment": (
        ("experiment", "simulate", "random", "walk", "data", "measure", "test", "benchmark"),
        "Design cheap, reproducible experiments with explicit controls, seeds, observables, and falsification criteria.",
    ),
    "geometry": (
        ("geometry", "rotor", "spinor", "blade", "exterior", "cell", "mesh", "affine", "piola"),
        "Look for structure-preserving geometric representations and lower-cost equivalent transforms.",
    ),
    "code": (
        ("python", "c++", "code", "runtime", "cache", "serialize", "api", "kernel", "gpu"),
        "Prefer simple interfaces, deterministic caches, bounded resource use, and testable local components.",
    ),
    "pattern": (
        ("pattern", "combine", "group", "novel", "creative", "latent", "attention", "route", "expert"),
        "Search for cross-module patterns while penalizing redundant combinations and unsupported claims.",
    ),
    "general": (
        (),
        "Be generally useful: route to the cheapest relevant capability and make assumptions explicit.",
    ),
}


class SparseResearchIndex:
    """Small dependency-free sparse/latent index.

    This borrows the *idea* of sparse attention and latent compression without
    copying a model implementation.  Candidate generation is lexical/inverted
    index first, then a tiny signed-hash sketch reranks only the candidate set.
    """

    def __init__(self, fragments: Iterable[ResearchFragment], *, latent_dim: int = 96) -> None:
        self.fragments = tuple(fragments)
        self.latent_dim = max(16, int(latent_dim))
        self._by_id = {fragment.fragment_id: fragment for fragment in self.fragments}
        if len(self._by_id) != len(self.fragments):
            raise ValueError("fragment_id values must be unique")
        self._tf: dict[str, Counter[str]] = {}
        self._df: Counter[str] = Counter()
        self._inverted: dict[str, set[str]] = defaultdict(set)
        for fragment in self.fragments:
            counts = Counter(_tokens(fragment.text + " " + fragment.source + " " + fragment.kind))
            self._tf[fragment.fragment_id] = counts
            for token in counts:
                self._df[token] += 1
                self._inverted[token].add(fragment.fragment_id)
        self._sketches = {
            fragment.fragment_id: self._sketch(self._tf[fragment.fragment_id])
            for fragment in self.fragments
        }

    def _idf(self, token: str) -> float:
        n = max(1, len(self.fragments))
        return math.log((n + 1.0) / (self._df.get(token, 0) + 1.0)) + 1.0

    def _sketch(self, counts: Counter[str]) -> tuple[float, ...]:
        vector = [0.0] * self.latent_dim
        for token, count in counts.items():
            digest = sha256(token.encode("utf-8")).digest()
            slot = int.from_bytes(digest[:4], "big") % self.latent_dim
            sign = 1.0 if digest[4] & 1 else -1.0
            vector[slot] += sign * (1.0 + math.log(count)) * self._idf(token)
        norm = math.sqrt(sum(value * value for value in vector))
        if norm:
            vector = [value / norm for value in vector]
        return tuple(vector)

    @staticmethod
    def _cosine(a: Sequence[float], b: Sequence[float]) -> float:
        return sum(x * y for x, y in zip(a, b))

    def rank(self, query: str, *, limit: int = 12, candidate_limit: int = 96) -> tuple[RankedFragment, ...]:
        q_counts = Counter(_tokens(query))
        if not self.fragments:
            return ()
        candidates: set[str] = set()
        for token in q_counts:
            candidates.update(self._inverted.get(token, ()))
        if not candidates:
            candidates = set(self._by_id)
        if len(candidates) > candidate_limit:
            lexical = []
            for fragment_id in candidates:
                score = sum(
                    min(q_counts[token], self._tf[fragment_id].get(token, 0)) * self._idf(token)
                    for token in q_counts
                )
                lexical.append((score, fragment_id))
            lexical.sort(key=lambda item: (-item[0], item[1]))
            candidates = {fragment_id for _, fragment_id in lexical[:candidate_limit]}

        q_sketch = self._sketch(q_counts)
        ranked = []
        for fragment_id in candidates:
            tf = self._tf[fragment_id]
            lexical = sum(
                (1.0 + math.log(tf[token])) * self._idf(token)
                for token in q_counts
                if tf.get(token, 0)
            )
            latent = self._cosine(q_sketch, self._sketches[fragment_id])
            score = lexical + 1.5 * max(0.0, latent)
            ranked.append(RankedFragment(self._by_id[fragment_id], score))
        ranked.sort(key=lambda item: (-item.score, item.fragment.fragment_id))
        return tuple(ranked[: max(1, limit)])

    def similarity(self, left_id: str, right_id: str) -> float:
        return max(0.0, self._cosine(self._sketches[left_id], self._sketches[right_id]))


def _dense_cosine(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right) or not left:
        return 0.0
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return sum(a * b for a, b in zip(left, right)) / (left_norm * right_norm)


def rerank_with_local_embeddings(
    query: str,
    ranked: Sequence[RankedFragment],
    provider,
    *,
    semantic_weight: float = 0.35,
    max_chars_per_fragment: int = 2400,
) -> tuple[RankedFragment, ...]:
    """Rerank an already-small shortlist with a local neural embedding model."""
    if not ranked:
        return ()
    semantic_weight = min(0.75, max(0.0, float(semantic_weight)))
    texts = [query] + [
        item.fragment.text[:max_chars_per_fragment] for item in ranked
    ]
    vectors = provider.embeddings(texts)
    if len(vectors) != len(texts):
        raise ValueError("embedding provider returned the wrong number of vectors")
    query_vector = vectors[0]
    top_base = max(abs(item.score) for item in ranked) or 1.0
    reranked = []
    for item, vector in zip(ranked, vectors[1:]):
        base = max(0.0, item.score / top_base)
        semantic = max(0.0, _dense_cosine(query_vector, vector))
        combined = (1.0 - semantic_weight) * base + semantic_weight * semantic
        reranked.append(RankedFragment(item.fragment, combined))
    reranked.sort(key=lambda item: (-item.score, item.fragment.fragment_id))
    return tuple(reranked)


class ExpertRouter:
    """Cheap MoE-inspired prompt router with load-balancing bias."""

    def __init__(self) -> None:
        self.usage: Counter[str] = Counter()

    def route(self, query: str, *, top_k: int = 2) -> tuple[ExpertRoute, ...]:
        tokens = set(_tokens(query))
        scored = []
        total_usage = sum(self.usage.values())
        for expert_id, (keywords, instruction) in _EXPERTS.items():
            hits = sum(1 for keyword in keywords if keyword in tokens)
            lexical = float(hits)
            if expert_id == "general":
                lexical = 0.25
            # Auxiliary-loss-free inspiration: apply a tiny deterministic routing
            # bias rather than adding a training loss.
            load = self.usage[expert_id] / max(1, total_usage)
            balance_bias = 0.15 * (1.0 - load)
            scored.append((lexical + balance_bias, expert_id, instruction))
        scored.sort(key=lambda item: (-item[0], item[1]))
        routes = tuple(ExpertRoute(expert_id, score, instruction) for score, expert_id, instruction in scored[:top_k])
        for route in routes:
            self.usage[route.expert_id] += 1
        return routes


class GrowthEngine:
    """Controlled novelty generator for local research context.

    Chaos changes *which concepts are explored*.  It never perturbs canonical
    source, experiment data, verification records, proof ledgers, or model
    weights.
    """

    def __init__(self, index: SparseResearchIndex, router: ExpertRouter | None = None) -> None:
        self.index = index
        self.router = router or ExpertRouter()
        self.seen_groups: Counter[tuple[str, ...]] = Counter()
        self.seen_fragments: Counter[str] = Counter()

    def reset_growth_memory(self) -> None:
        self.seen_groups.clear()
        self.seen_fragments.clear()

    @staticmethod
    def _seed(query: str, cycle: int) -> int:
        digest = sha256(f"{cycle}:{query}".encode("utf-8")).digest()
        return int.from_bytes(digest[:8], "big")

    def _walk(
        self,
        ranked: Sequence[RankedFragment],
        *,
        seed: int,
        steps: int,
        chaos: float,
    ) -> tuple[str, ...]:
        if not ranked:
            return ()
        rng = random.Random(seed)
        ids = [item.fragment.fragment_id for item in ranked]
        relevance = {item.fragment.fragment_id: item.score for item in ranked}
        current = ids[0]
        path = [current]
        unvisited = set(ids[1:])
        for _ in range(max(0, steps - 1)):
            if not unvisited:
                break
            candidates = []
            for candidate in sorted(unvisited):
                sim = self.index.similarity(current, candidate)
                rel = relevance[candidate] / max(1e-12, relevance[ids[0]] or 1.0)
                novelty = 1.0 - max(self.index.similarity(candidate, seen) for seen in path)
                repeat_penalty = min(0.35, 0.07 * self.seen_fragments[candidate])
                score = (1.0 - chaos) * (0.55 * sim + 0.45 * rel) + chaos * novelty
                score -= repeat_penalty
                score += 1e-6 * _stable_unit_interval(f"{seed}:{current}:{candidate}")
                candidates.append((score, candidate))
            candidates.sort(key=lambda item: (-item[0], item[1]))
            # A bounded stochastic branch makes repeated cycles explore new areas
            # while remaining reproducible for the same query/cycle.
            width = min(len(candidates), 3 if chaos >= 0.2 else 1)
            choice = candidates[rng.randrange(width)][1]
            path.append(choice)
            unvisited.remove(choice)
            current = choice
        return tuple(path)

    def _groups(
        self,
        ranked: Sequence[RankedFragment],
        *,
        max_group_size: int,
        budget: int,
    ) -> tuple[ConceptGroup, ...]:
        pool = list(ranked[:8])
        if len(pool) < 2:
            return ()
        best_score = max(1e-12, pool[0].score)
        groups: list[ConceptGroup] = []
        for size in range(2, min(max_group_size, 4, len(pool)) + 1):
            for combo in combinations(pool, size):
                ids = tuple(item.fragment.fragment_id for item in combo)
                rel = sum(item.score / best_score for item in combo) / size
                kinds = {item.fragment.kind for item in combo}
                diversity = len(kinds) / size
                pair_sims = [
                    self.index.similarity(a.fragment.fragment_id, b.fragment.fragment_id)
                    for a, b in combinations(combo, 2)
                ]
                redundancy = sum(pair_sims) / max(1, len(pair_sims))
                novelty = 1.0 - redundancy
                size_cost = 0.06 * (size - 2)
                repeat_penalty = min(0.40, 0.08 * self.seen_groups[ids])
                score = (
                    0.55 * rel
                    + 0.25 * diversity
                    + 0.20 * novelty
                    - size_cost
                    - repeat_penalty
                )
                groups.append(
                    ConceptGroup(
                        fragment_ids=ids,
                        score=score,
                        novelty=novelty,
                        diversity=diversity,
                        rationale=(
                            "Cross-check this combination for a shared invariant, "
                            "cheaper representation, or falsifiable experiment."
                        ),
                    )
                )
        groups.sort(key=lambda group: (-group.score, group.fragment_ids))
        return tuple(groups[: max(1, budget)])

    def grow(
        self,
        query: str,
        *,
        cycle: int = 0,
        chaos: float = 0.18,
        retrieval_limit: int = 14,
        walk_steps: int = 6,
        group_budget: int = 10,
        max_group_size: int = 4,
        embedding_provider=None,
    ) -> GrowResult:
        chaos = min(0.85, max(0.0, float(chaos)))
        seed = self._seed(query, cycle)
        ranked = self.index.rank(query, limit=retrieval_limit)
        neural_rerank_used = False
        neural_rerank_note = ""
        if embedding_provider is not None and ranked:
            try:
                ranked = rerank_with_local_embeddings(query, ranked, embedding_provider)
            except Exception as exc:
                neural_rerank_note = f"fallback after {type(exc).__name__}: {exc}"
            else:
                neural_rerank_used = True
                neural_rerank_note = f"reranked {len(ranked)} sparse candidates locally"
        routes = self.router.route(query)
        walk = self._walk(ranked, seed=seed, steps=walk_steps, chaos=chaos)
        groups = self._groups(ranked, max_group_size=max_group_size, budget=group_budget)

        next_steps = []
        if ranked:
            next_steps.append("Compare the top retrieved source against the strongest dissimilar source from the semantic walk.")
        if groups:
            next_steps.append("Test the highest-scoring 2-4 concept group with a small deterministic experiment before expanding it.")
        if any(route.expert_id == "proof" for route in routes):
            next_steps.append("Extract exact hypotheses and unresolved proof obligations before treating any generated relation as a theorem.")
        if any(route.expert_id == "experiment" for route in routes):
            next_steps.append("Use at least two fixed seeds plus a zero-chaos control to separate exploration effects from stable structure.")
        next_steps.append("Promote nothing automatically: user review is required before persistent research memory or graph mutation.")

        for fragment_id in walk:
            self.seen_fragments[fragment_id] += 1
        for group in groups:
            self.seen_groups[group.fragment_ids] += 1

        return GrowResult(
            query=query,
            seed=seed,
            chaos=chaos,
            routes=routes,
            retrieved=ranked,
            walk=walk,
            groups=groups,
            next_steps=tuple(next_steps),
            neural_rerank_used=neural_rerank_used,
            neural_rerank_note=neural_rerank_note,
        )
