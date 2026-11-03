from __future__ import annotations

from cace_studio.ai.compact_geometric_ranker import (
    FEATURE_NAMES,
    CompactGeometricRanker,
    GeometricCandidateFeatures,
)


def _features(**overrides):
    base = {name: 0.5 for name in FEATURE_NAMES}
    base.update(overrides)
    return GeometricCandidateFeatures.from_mapping(base)


def test_compact_ranker_is_tiny_and_deterministic():
    a = CompactGeometricRanker(seed=7)
    b = CompactGeometricRanker(seed=7)
    candidate = _features(user_relevance=1.0, workflow_coverage=1.0)
    assert a.parameter_count == 385
    assert a.float32_size_bytes == 1540
    assert a.score(candidate) == b.score(candidate)
    assert a.to_dict()["evidence_authority"] is False


def test_pairwise_training_improves_preferred_margin():
    model = CompactGeometricRanker(seed=11)
    preferred = [
        _features(
            user_relevance=1.0,
            workflow_coverage=1.0,
            typed_connection_fraction=1.0,
            invariant_preservation=1.0,
            geometric_structure=1.0,
            resource_headroom=0.8,
            sparsity=0.9,
        )
        for _ in range(8)
    ]
    rejected = [
        _features(
            user_relevance=0.1,
            workflow_coverage=0.2,
            typed_connection_fraction=0.2,
            invariant_preservation=0.2,
            geometric_structure=0.1,
            resource_headroom=0.4,
            sparsity=0.2,
        )
        for _ in range(8)
    ]
    before = model.score(preferred[0]) - model.score(rejected[0])
    history = model.fit_pairwise(
        preferred,
        rejected,
        epochs=100,
        learning_rate=0.02,
    )
    after = model.score(preferred[0]) - model.score(rejected[0])
    assert history[-1] < history[0]
    assert after > before


def test_ranker_round_trip(tmp_path):
    model = CompactGeometricRanker(seed=4)
    path = model.save(tmp_path / "ranker.json")
    loaded = CompactGeometricRanker.load(path)
    candidate = _features(novelty=0.9, symmetry_reduction=0.8)
    assert loaded.parameter_count == model.parameter_count
    assert loaded.score(candidate) == model.score(candidate)
