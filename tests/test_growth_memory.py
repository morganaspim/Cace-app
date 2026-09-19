from __future__ import annotations

import json

from cace_studio.ai.growth_memory import PersistentGrowthMemory
from cace_studio.ai.hybrid import GrowthEngine, ResearchFragment, SparseResearchIndex


def _memory_fragments():
    return (
        ResearchFragment("a", "a.py", "research-module", "alpha shared pattern"),
        ResearchFragment("b", "b.py", "research-module", "alpha shared pattern"),
        ResearchFragment("c", "c.py", "research-module", "distant retained concept"),
    )


def test_feedback_persists_without_storing_plain_query(tmp_path):
    path = tmp_path / "growth-memory.json"
    memory = PersistentGrowthMemory(path)
    event = memory.record(
        "useful",
        "group",
        ("b", "a"),
        query="private research question",
        note="good combination",
    )

    assert path.exists()
    raw = path.read_text(encoding="utf-8")
    assert "private research question" not in raw
    assert event.query_sha256 in raw

    loaded = PersistentGrowthMemory(path)
    assert len(loaded.events) == 1
    assert loaded.events[0].target_ids == ("a", "b")
    assert loaded.events[0].feedback == "useful"
    assert loaded.summary() == {"keep": 0, "useful": 1, "reject": 0, "total": 1}


def test_feedback_bias_is_bounded(tmp_path):
    memory = PersistentGrowthMemory(tmp_path / "growth-memory.json")
    for _ in range(20):
        memory.record("useful", "fragment", ("a",))
        memory.record("reject", "group", ("a", "b"))

    assert memory.fragment_bias("a") <= 0.25
    assert memory.group_bias(("a", "b")) >= -0.60


def test_latest_feedback_controls_keep_recall(tmp_path):
    memory = PersistentGrowthMemory(tmp_path / "growth-memory.json")
    memory.record("keep", "group", ("a", "b"))
    assert set(memory.kept_fragment_ids()) == {"a", "b"}

    memory.record("reject", "group", ("b", "a"))
    assert memory.kept_fragment_ids() == ()

    memory.record("keep", "fragment", ("c",))
    assert memory.kept_fragment_ids() == ("c",)


def test_corrupt_or_unknown_memory_entries_fail_closed(tmp_path):
    path = tmp_path / "growth-memory.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "events": [
                    {
                        "event_id": "bad",
                        "timestamp_utc": "x",
                        "feedback": "invented",
                        "target_kind": "group",
                        "target_ids": ["a"],
                        "target_key": "bad",
                        "query_sha256": "bad",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    memory = PersistentGrowthMemory(path)
    assert memory.events == []


def test_useful_feedback_can_change_tied_fragment_ranking(tmp_path):
    index = SparseResearchIndex(_memory_fragments())
    baseline = GrowthEngine(index).grow("alpha shared pattern", retrieval_limit=3)
    assert baseline.retrieved[0].fragment.fragment_id == "a"

    memory = PersistentGrowthMemory(tmp_path / "growth-memory.json")
    memory.record("useful", "fragment", ("b",))
    learned = GrowthEngine(index, memory=memory).grow(
        "alpha shared pattern",
        retrieval_limit=3,
    )
    assert learned.retrieved[0].fragment.fragment_id == "b"
    assert learned.persistent_memory_used is True
    assert "1 event" in learned.persistent_memory_note


def test_keep_resurfaces_unrelated_fragment_without_dominating(tmp_path):
    index = SparseResearchIndex(_memory_fragments())
    memory = PersistentGrowthMemory(tmp_path / "growth-memory.json")
    memory.record("keep", "fragment", ("c",))

    result = GrowthEngine(index, memory=memory).grow(
        "alpha shared pattern",
        retrieval_limit=2,
    )
    ids = [item.fragment.fragment_id for item in result.retrieved]
    assert "c" in ids
    assert ids[0] in {"a", "b"}
    assert ids.index("c") > 0


def test_clear_persists_empty_memory(tmp_path):
    path = tmp_path / "growth-memory.json"
    memory = PersistentGrowthMemory(path)
    memory.record("keep", "fragment", ("a",))
    memory.clear()

    reloaded = PersistentGrowthMemory(path)
    assert reloaded.events == []
    assert reloaded.summary()["total"] == 0
