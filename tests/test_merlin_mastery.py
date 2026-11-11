import pytest

from merlin_lms.mastery import evaluate_mastery


def evidence_set():
    return [
        {"evidence_id": "ev-1", "task_id": "task-a", "session_id": "session-1",
         "kind": "explanation_review", "score": 0.95, "passed": True},
        {"evidence_id": "ev-2", "task_id": "task-b", "session_id": "session-2",
         "kind": "automated_test", "score": 0.9, "passed": True},
        {"evidence_id": "ev-3", "task_id": "task-c", "session_id": "session-3",
         "kind": "human_review", "score": 0.92, "passed": True, "is_transfer": True},
    ]


def test_requires_independent_demonstrations_and_transfer_for_mastery():
    result = evaluate_mastery(evidence_set())
    assert result["state"] == "mastered"
    assert result["metrics"] == {
        "qualifying_demonstrations": 3,
        "distinct_tasks": 3,
        "distinct_sessions": 3,
        "distinct_evidence_kinds": 3,
        "transfer_demonstrated": True,
    }
    assert result["is_formal_proof"] is False
    assert result["proof_authority"] is None


def test_two_independent_demonstrations_are_provisional_without_transfer():
    result = evaluate_mastery(evidence_set()[:2])
    assert result["state"] == "provisional"
    assert "transfer_demonstration_still_required" in result["reason_codes"]


def test_same_task_or_session_does_not_satisfy_independence():
    evidence = evidence_set()[:2]
    evidence[1]["task_id"] = evidence[0]["task_id"]
    evidence[1]["session_id"] = evidence[0]["session_id"]
    result = evaluate_mastery(evidence)
    assert result["state"] == "practicing"
    assert result["metrics"]["distinct_tasks"] == 1
    assert result["metrics"]["distinct_sessions"] == 1


def test_critical_misconception_blocks_mastery():
    result = evaluate_mastery(
        evidence_set(),
        unresolved_critical_misconceptions=["division-by-zero"],
    )
    assert result["state"] == "needs_review"
    assert result["is_formal_proof"] is False


def test_failed_or_low_score_evidence_is_not_qualifying():
    evidence = evidence_set()
    evidence[0]["score"] = 0.4
    evidence[1]["passed"] = False
    result = evaluate_mastery(evidence)
    assert result["state"] == "practicing"
    assert len(result["qualifying_evidence_refs"]) == 1
    assert len(result["rejected_evidence"]) == 2


def test_formal_or_ai_only_evidence_kinds_are_rejected():
    evidence = evidence_set()
    evidence[0]["kind"] = "lean_compile"
    with pytest.raises(ValueError, match="unsupported pedagogical evidence kind"):
        evaluate_mastery(evidence)


def test_rejects_duplicate_evidence_ids():
    evidence = evidence_set()
    evidence[1]["evidence_id"] = evidence[0]["evidence_id"]
    with pytest.raises(ValueError, match="duplicate evidence_id"):
        evaluate_mastery(evidence)


def test_policy_is_versioned_and_validated():
    with pytest.raises(ValueError, match="unknown mastery policy keys"):
        evaluate_mastery([], policy={"auto_master": True})
    with pytest.raises(ValueError, match="minimum_score"):
        evaluate_mastery([], policy={"minimum_score": 2})
