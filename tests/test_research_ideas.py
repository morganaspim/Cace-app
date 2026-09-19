from __future__ import annotations

from hashlib import sha256
import json

from cace_studio.ai.grow_candidates import GrowCandidate
from cace_studio.ai.research_ideas import (
    IDEA_STATUSES,
    ResearchIdeaStore,
    seed_from_grow_candidate,
)


def _candidate() -> GrowCandidate:
    return GrowCandidate(
        candidate_id="group:a|b",
        target_kind="group",
        target_ids=("a", "b"),
        title="Combination 1: Rotor + Piola",
        detail="Cross-check this combination for a shared invariant.",
        score=0.8123,
        novelty=0.73,
    )


def test_seed_from_grow_candidate_is_editable_and_module_aware():
    seed = seed_from_grow_candidate(
        _candidate(),
        source_query="can these work together?",
        associated_modules=("research.geometry", "research.piola", "research.geometry"),
    )
    assert seed["title"] == "Rotor + Piola"
    assert seed["hypotheses"]
    assert "reproducible experiment" in seed["proposed_experiment"]
    assert seed["associated_modules"] == ("research.geometry", "research.piola")
    assert seed["source_query"] == "can these work together?"


def test_keep_candidate_creates_one_idempotent_research_idea(tmp_path):
    path = tmp_path / "ideas.json"
    store = ResearchIdeaStore(path)
    seed = seed_from_grow_candidate(_candidate(), source_query="private question")

    first, created_first = store.create_or_get_from_grow(
        candidate_id=seed["candidate_id"],
        target_ids=seed["target_ids"],
        title=seed["title"],
        notes=seed["notes"],
        hypotheses=seed["hypotheses"],
        proposed_experiment=seed["proposed_experiment"],
        associated_modules=seed["associated_modules"],
        source_query=seed["source_query"],
    )
    second, created_second = store.create_or_get_from_grow(
        candidate_id=seed["candidate_id"],
        target_ids=reversed(seed["target_ids"]),
        title="Different title should not duplicate",
        notes="different notes",
        hypotheses=("different",),
        proposed_experiment="different",
        associated_modules=("other",),
        source_query="other query",
    )

    assert created_first is True
    assert created_second is False
    assert first.idea_id == second.idea_id
    assert len(store.ideas) == 1
    raw = path.read_text(encoding="utf-8")
    assert "private question" not in raw
    assert sha256(b"private question").hexdigest() in raw


def test_research_idea_round_trip_and_editable_fields(tmp_path):
    path = tmp_path / "ideas.json"
    store = ResearchIdeaStore(path)
    idea = store.create(
        title="Initial",
        notes="note",
        hypotheses=("h1",),
        proposed_experiment="experiment",
        associated_modules=("m1",),
    )
    updated = store.update(
        idea.idea_id,
        title="Edited",
        notes="new notes",
        hypotheses=("h1", "h2"),
        proposed_experiment="new experiment",
        associated_modules=("m1", "m2"),
        status="Testable",
    )

    reloaded = ResearchIdeaStore(path)
    loaded = reloaded.get(updated.idea_id)
    assert loaded is not None
    assert loaded.title == "Edited"
    assert loaded.notes == "new notes"
    assert loaded.hypotheses == ("h1", "h2")
    assert loaded.proposed_experiment == "new experiment"
    assert loaded.associated_modules == ("m1", "m2")
    assert loaded.status == "Testable"


def test_status_advancement_follows_research_lifecycle_only(tmp_path):
    store = ResearchIdeaStore(tmp_path / "ideas.json")
    idea = store.create(title="Lifecycle")
    observed = [idea.status]
    for _ in range(10):
        idea = store.advance_status(idea.idea_id)
        observed.append(idea.status)

    assert observed[:5] == list(IDEA_STATUSES)
    assert observed[-1] == "Proof Candidate"
    assert set(observed).issubset(set(IDEA_STATUSES))

    raw = json.loads(store.path.read_text(encoding="utf-8"))
    assert raw["role"] == "local research notebook; never verification evidence"
    assert raw["ideas"][0]["status"] == "Proof Candidate"
    assert "proof_status" not in raw["ideas"][0]
    assert "verification" not in raw["ideas"][0]
    assert "certificate" not in raw["ideas"][0]


def test_status_can_move_backward_by_explicit_edit(tmp_path):
    store = ResearchIdeaStore(tmp_path / "ideas.json")
    idea = store.create(title="Backtrack", status="Promising")
    idea = store.update(idea.idea_id, status="Testable")
    assert idea.status == "Testable"


def test_unknown_fields_and_invalid_status_fail_closed(tmp_path):
    store = ResearchIdeaStore(tmp_path / "ideas.json")
    idea = store.create(title="Strict")
    try:
        store.update(idea.idea_id, proof_status="formal")
    except ValueError as exc:
        assert "unsupported research idea fields" in str(exc)
    else:
        raise AssertionError("unsupported field should fail")

    try:
        store.update(idea.idea_id, status="Proved")
    except ValueError as exc:
        assert "invalid research idea status" in str(exc)
    else:
        raise AssertionError("invalid status should fail")


def test_corrupt_entries_are_ignored_without_destroying_valid_ideas(tmp_path):
    path = tmp_path / "ideas.json"
    valid_store = ResearchIdeaStore(path)
    valid = valid_store.create(title="Valid")
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["ideas"].append({"idea_id": "", "title": "bad"})
    path.write_text(json.dumps(payload), encoding="utf-8")

    loaded = ResearchIdeaStore(path)
    assert loaded.get(valid.idea_id) is not None
    assert len(loaded.ideas) == 1


def test_delete_is_local_to_notebook_store(tmp_path):
    store = ResearchIdeaStore(tmp_path / "ideas.json")
    first = store.create(title="Delete me")
    second = store.create(title="Keep me")
    assert store.delete(first.idea_id) is True
    assert store.get(first.idea_id) is None
    assert store.get(second.idea_id) is not None
    assert store.delete("missing") is False
