from __future__ import annotations

from pathlib import Path

from cace_studio.ai.corpus import build_local_fragments
from cace_studio.ai.grow_candidates import build_grow_candidates
from cace_studio.ai.hybrid import (
    GrowthEngine,
    ResearchFragment,
    SparseResearchIndex,
)
from cace_studio.core.settings import StudioSettings


def _fragments():
    return (
        ResearchFragment(
            "proof",
            "formal/example.lean",
            "formal-source",
            "affine triangle determinant theorem proof lean piola mesh",
        ),
        ResearchFragment(
            "geometry",
            "cace_studio/modules/research_geometry.py",
            "research-module",
            "rotor spinor blade exterior algebra geometry transform mesh",
        ),
        ResearchFragment(
            "walk",
            "cace_studio/modules/research_dynamics.py",
            "research-module",
            "seeded random walk growth rotation stochastic experiment data",
        ),
        ResearchFragment(
            "runtime",
            "cace_studio/core/native_runtime.py",
            "runtime-core",
            "c++ runtime cache serialization kernel gpu deterministic execution",
        ),
        ResearchFragment(
            "ai",
            "cace_studio/ai/hybrid.py",
            "ai-code",
            "sparse attention expert routing latent pattern combine novelty",
        ),
    )


def test_sparse_retrieval_prefers_relevant_fragments():
    index = SparseResearchIndex(_fragments())
    ranked = index.rank("rotor blade geometry")
    assert ranked
    assert ranked[0].fragment.fragment_id == "geometry"


def test_grow_is_reproducible_for_same_query_and_cycle():
    engine_a = GrowthEngine(SparseResearchIndex(_fragments()))
    engine_b = GrowthEngine(SparseResearchIndex(_fragments()))
    a = engine_a.grow("combine geometry proof experiment", cycle=3, chaos=0.35)
    b = engine_b.grow("combine geometry proof experiment", cycle=3, chaos=0.35)
    assert a.seed == b.seed
    assert a.walk == b.walk
    assert a.groups == b.groups
    assert a.next_steps == b.next_steps


def test_grow_changes_exploration_without_mutating_fragments():
    fragments = _fragments()
    before = tuple(fragment.text for fragment in fragments)
    engine = GrowthEngine(SparseResearchIndex(fragments))
    low = engine.grow("random walk geometry", cycle=1, chaos=0.0)
    high = engine.grow("random walk geometry", cycle=1, chaos=0.8)
    after = tuple(fragment.text for fragment in fragments)
    assert before == after
    assert low.chaos == 0.0
    assert high.chaos == 0.8
    assert all(2 <= len(group.fragment_ids) <= 4 for group in high.groups)


class _FakeEmbeddingProvider:
    def embeddings(self, texts):
        vectors = []
        for text in texts:
            lowered = text.lower()
            if "rotor" in lowered or "blade" in lowered or "geometry" in lowered:
                vectors.append((1.0, 0.0, 0.0))
            elif "proof" in lowered or "theorem" in lowered:
                vectors.append((0.0, 1.0, 0.0))
            else:
                vectors.append((0.0, 0.0, 1.0))
        return tuple(vectors)


class _BrokenEmbeddingProvider:
    def embeddings(self, texts):
        raise RuntimeError("embedding backend unavailable")


def test_optional_neural_rerank_is_used_when_available():
    engine = GrowthEngine(SparseResearchIndex(_fragments()))
    result = engine.grow(
        "rotor blade geometry",
        embedding_provider=_FakeEmbeddingProvider(),
    )
    assert result.neural_rerank_used is True
    assert "reranked" in result.neural_rerank_note
    assert result.retrieved[0].fragment.fragment_id == "geometry"


def test_neural_rerank_failure_falls_back_to_sparse_path():
    engine = GrowthEngine(SparseResearchIndex(_fragments()))
    result = engine.grow(
        "proof geometry",
        embedding_provider=_BrokenEmbeddingProvider(),
    )
    assert result.retrieved
    assert result.neural_rerank_used is False
    assert "fallback after RuntimeError" in result.neural_rerank_note


def test_growth_memory_tracks_and_resets_seen_candidates():
    engine = GrowthEngine(SparseResearchIndex(_fragments()))
    first = engine.grow("combine geometry experiment", cycle=0, chaos=0.4)
    assert first.walk
    assert engine.seen_fragments
    assert engine.seen_groups
    seen_before = dict(engine.seen_groups)

    engine.grow("combine geometry experiment", cycle=1, chaos=0.4)
    assert sum(engine.seen_groups.values()) > sum(seen_before.values())

    engine.reset_growth_memory()
    assert not engine.seen_fragments
    assert not engine.seen_groups


def test_context_is_explicitly_non_evidentiary():
    result = GrowthEngine(SparseResearchIndex(_fragments())).grow("proof geometry")
    context = result.context_text()
    assert "never mathematical proof" in context
    assert "verification evidence" in context
    assert "formal/example.lean" in context


def test_general_mode_and_growth_settings_round_trip(tmp_path, monkeypatch):
    path = tmp_path / "settings.json"
    monkeypatch.setenv("CACE_SETTINGS_PATH", str(path))
    settings = StudioSettings()
    settings.assistant_mode = "general"
    settings.ai_growth_chaos = 0.42
    settings.ai_growth_budget = 17
    settings.ai_growth_max_group_size = 3
    settings.save()

    loaded = StudioSettings.load()
    assert loaded.assistant_mode == "general"
    assert loaded.ai_growth_chaos == 0.42
    assert loaded.ai_growth_budget == 17
    assert loaded.ai_growth_max_group_size == 3


def test_growth_settings_are_clamped_on_load(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text(
        '{"assistant_mode":"general","ai_growth_chaos":99,'
        '"ai_growth_budget":999,"ai_growth_max_group_size":12}',
        encoding="utf-8",
    )
    settings = StudioSettings.load(path)
    assert settings.ai_growth_chaos == 0.85
    assert settings.ai_growth_budget == 32
    assert settings.ai_growth_max_group_size == 4


def test_local_corpus_stays_inside_supplied_root(tmp_path):
    root = Path(tmp_path)
    (root / "cace_studio" / "ai").mkdir(parents=True)
    (root / "formal" / "cace_formal" / "CACEFormal").mkdir(parents=True)
    (root / "docs").mkdir()
    (root / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    (root / "AI_REPO_MAP.json").write_text('{"project":"local"}', encoding="utf-8")
    (root / "docs" / "ARCHITECTURE.md").write_text("local architecture", encoding="utf-8")
    (root / "formal" / "cace_formal" / "CACEFormal" / "A.lean").write_text(
        "theorem local_only : True := by trivial\n", encoding="utf-8"
    )
    outside = root.parent / "outside-secret.txt"
    outside.write_text("do not index", encoding="utf-8")
    try:
        fragments = build_local_fragments(root)
    finally:
        outside.unlink(missing_ok=True)

    assert fragments
    joined = "\n".join(fragment.text for fragment in fragments)
    assert "local architecture" in joined
    assert "local_only" in joined
    assert "do not index" not in joined


def test_grow_candidate_shortlist_is_stable_mixed_and_bounded():
    result = GrowthEngine(SparseResearchIndex(_fragments())).grow(
        "combine geometry proof experiment runtime",
        group_budget=10,
        max_group_size=4,
    )
    first = build_grow_candidates(result, limit=5, max_groups=3)
    second = build_grow_candidates(result, limit=5, max_groups=3)

    assert first == second
    assert 1 <= len(first) <= 5
    assert len({candidate.candidate_id for candidate in first}) == len(first)
    assert any(candidate.target_kind == "group" for candidate in first)
    assert any(candidate.target_kind == "fragment" for candidate in first)
    assert all(candidate.target_ids for candidate in first)
    assert all(
        candidate.target_ids == tuple(sorted(candidate.target_ids))
        for candidate in first
        if candidate.target_kind == "group"
    )


def test_grow_candidate_shortlist_respects_limit():
    result = GrowthEngine(SparseResearchIndex(_fragments())).grow(
        "pattern combine geometry proof",
        group_budget=10,
    )
    candidates = build_grow_candidates(result, limit=3, max_groups=2)
    assert len(candidates) <= 3
    assert sum(candidate.target_kind == "group" for candidate in candidates) <= 2
