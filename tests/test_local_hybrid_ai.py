from __future__ import annotations

import numpy as np

from cace_studio.ai.hybrid import HybridLocalAI
from cace_studio.ai.math_features import combine_sketches, hashed_text_sketch, signed_hash_sketch
from cace_studio.ai.memory import ExperienceMemory
from cace_studio.ai.planner import (
    CandidateAtom,
    CombinationPlanner,
    PlannerConfig,
)
from cace_studio.ai.ranker import RankerConfig, TinyResidualRanker
from cace_studio.core.module import Module
from cace_studio.core.registry import ModuleRegistry
from cace_studio.core.types import (
    EvidenceKind,
    Maturity,
    ModuleMetadata,
    ProofStatus,
)


class _RelevantExperimental(Module):
    metadata = ModuleMetadata(
        "test.relevant",
        "Relevant",
        "1",
        "Test",
        "rotation geometry transform task",
        Maturity.EXPERIMENTAL,
    )
    proof_status = ProofStatus(evidence={EvidenceKind.EXPERIMENTAL})

    def execute(self, inputs, params, ctx):
        return {}


class _GeneralFormal(Module):
    metadata = ModuleMetadata(
        "test.general_formal",
        "General Formal",
        "1",
        "Verification",
        "general reusable proof verification composition",
        Maturity.BETA,
    )
    proof_status = ProofStatus(evidence={EvidenceKind.FORMAL})

    def execute(self, inputs, params, ctx):
        return {}


def test_signed_hash_sketch_is_deterministic_and_normalized():
    first = signed_hash_sketch(["alpha", "beta", ("gamma", 0.5)], dim=32, seed=17)
    second = signed_hash_sketch(["alpha", "beta", ("gamma", 0.5)], dim=32, seed=17)
    assert np.array_equal(first, second)
    assert np.isclose(np.linalg.norm(first), 1.0)


def test_combine_sketches_contains_additive_and_pair_interaction_halves():
    a = np.asarray([1.0, 0.0, 1.0, 0.0])
    b = np.asarray([1.0, 1.0, 0.0, 0.0])
    combined = combine_sketches([a, b])
    assert combined.shape == (8,)
    assert np.isclose(np.linalg.norm(combined[:4]), 1.0)
    # a*b = [1,0,0,0], so the normalized pair-interaction half is e0.
    assert np.allclose(combined[4:], np.asarray([1.0, 0.0, 0.0, 0.0]))


def test_untrained_ranker_is_neutral():
    ranker = TinyResidualRanker(RankerConfig(input_dim=20, hidden_dim=8, seed=123))
    for features in (
        np.zeros(20),
        np.linspace(-1.0, 1.0, 20),
        np.ones(20),
    ):
        assert ranker.predict(features) == 0.5


def test_task_focused_and_general_usefulness_are_distinct_policies():
    sketch_dim = 4
    ranker = TinyResidualRanker(
        RankerConfig(
            input_dim=CombinationPlanner.ranker_input_dim(sketch_dim),
            hidden_dim=8,
            seed=0,
        )
    )
    relevant = CandidateAtom(
        "relevant",
        np.asarray([1.0, 0.0, 0.0, 0.0]),
        static_cost=1.0,
        proof_strength=0.0,
    )
    formal = CandidateAtom(
        "formal",
        np.asarray([0.0, 1.0, 0.0, 0.0]),
        static_cost=1.0,
        proof_strength=1.0,
    )
    context = np.asarray([1.0, 0.0, 0.0, 0.0])

    task_planner = CombinationPlanner(
        ranker,
        PlannerConfig(
            beam_width=4,
            min_group=1,
            max_group=1,
            cost_weight=0.0,
            prior_weight=0.0,
            proof_weight=0.0,
            diversity_weight=0.0,
            relevance_weight=1.0,
        ),
    )
    general_planner = CombinationPlanner(
        ranker,
        PlannerConfig(
            beam_width=4,
            min_group=1,
            max_group=1,
            cost_weight=0.0,
            prior_weight=0.0,
            proof_weight=1.0,
            diversity_weight=0.0,
            relevance_weight=0.0,
        ),
    )

    assert task_planner.search(
        [relevant, formal], context_sketch=context, top_k=1
    )[0].member_ids == ("relevant",)
    assert general_planner.search(
        [relevant, formal], context_sketch=context, top_k=1
    )[0].member_ids == ("formal",)


def test_beam_planner_returns_unique_bounded_groups():
    sketch_dim = 8
    ranker = TinyResidualRanker(
        RankerConfig(
            input_dim=CombinationPlanner.ranker_input_dim(sketch_dim),
            hidden_dim=8,
            seed=0,
        )
    )
    atoms = [
        CandidateAtom(
            f"m{i}",
            signed_hash_sketch([f"module-{i}"], dim=sketch_dim, seed=0),
            proof_strength=i / 8.0,
        )
        for i in range(8)
    ]
    planner = CombinationPlanner(
        ranker,
        PlannerConfig(beam_width=6, min_group=2, max_group=3),
    )
    results = planner.search(
        atoms,
        context_sketch=hashed_text_sketch("module 1 proof", dim=sketch_dim),
        top_k=10,
    )
    assert results
    assert len({item.member_ids for item in results}) == len(results)
    assert all(2 <= len(item.member_ids) <= 3 for item in results)
    assert all(tuple(sorted(item.member_ids)) == item.member_ids for item in results)


def test_experience_memory_roundtrip_and_similarity(tmp_path):
    memory = ExperienceMemory(tmp_path / "experience.sqlite3")
    task = np.asarray([1.0, 0.0, 0.0, 0.0])
    other = np.asarray([0.0, 1.0, 0.0, 0.0])
    feature = np.linspace(0.0, 1.0, 20)

    memory.add(
        task_text="first",
        task_sketch=task,
        candidate_ids=("a", "b"),
        candidate_feature=feature,
        target=1.0,
        evidence_kind="formally-verified",
        cost=2.0,
    )
    memory.add(
        task_text="second",
        task_sketch=other,
        candidate_ids=("c",),
        candidate_feature=feature,
        target=0.0,
    )

    nearest = memory.nearest(task, k=1)
    assert nearest[0].task_text == "first"
    assert nearest[0].candidate_ids == ("a", "b")
    assert nearest[0].similarity > 0.99


def test_hybrid_engine_can_plan_without_an_llm(tmp_path):
    registry = ModuleRegistry()
    registry.register(_RelevantExperimental)
    registry.register(_GeneralFormal)
    engine = HybridLocalAI(
        registry,
        state_dir=tmp_path,
        sketch_dim=32,
        hidden_dim=8,
        seed=3,
    )

    task_results = engine.suggest(
        "rotation geometry transform",
        generally_useful=False,
        top_k=4,
        max_group=2,
    )
    general_results = engine.suggest(
        "",
        generally_useful=True,
        top_k=4,
        max_group=2,
    )

    assert task_results
    assert general_results
    assert all(len(item.member_ids) <= 2 for item in task_results + general_results)
