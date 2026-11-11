"""Evidence-based pedagogical mastery policy.

This evaluates learning progress only. It never establishes mathematical truth,
formal proof, or CACE claim qualification.
"""
from __future__ import annotations

from typing import Any, Iterable

POLICY_VERSION = "1.0.0"
ALLOWED_KINDS = frozenset({
    "explanation_review",
    "automated_test",
    "human_review",
    "problem_solution",
    "code_task",
    "proof_explanation",
    "transfer_task",
})
DEFAULT_POLICY = {
    "minimum_score": 0.8,
    "minimum_mastery_demonstrations": 3,
    "minimum_provisional_demonstrations": 2,
    "minimum_distinct_tasks": 2,
    "minimum_distinct_sessions": 2,
    "minimum_evidence_kinds": 2,
    "require_transfer": True,
}


def evaluate_mastery(
    evidence: Iterable[dict[str, Any]],
    *,
    policy: dict[str, Any] | None = None,
    unresolved_critical_misconceptions: Iterable[str] = (),
) -> dict[str, Any]:
    """Return a transparent mastery recommendation from independent evidence.

    Evidence is pedagogical only. Self-report, numerical experiments, Lean
    compilation, model confidence, and CACE qualification receipts are not
    accepted as substitutes for learner demonstrations in this policy.
    """
    active = dict(DEFAULT_POLICY)
    if policy is not None:
        if not isinstance(policy, dict):
            raise ValueError("policy must be an object")
        unknown = set(policy) - set(DEFAULT_POLICY)
        if unknown:
            raise ValueError(f"unknown mastery policy keys: {sorted(unknown)}")
        active.update(policy)

    score_floor = active["minimum_score"]
    if isinstance(score_floor, bool) or not isinstance(score_floor, (int, float)) or not 0 <= score_floor <= 1:
        raise ValueError("minimum_score must be between 0 and 1")
    for key in (
        "minimum_mastery_demonstrations",
        "minimum_provisional_demonstrations",
        "minimum_distinct_tasks",
        "minimum_distinct_sessions",
        "minimum_evidence_kinds",
    ):
        value = active[key]
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise ValueError(f"{key} must be a positive integer")
    if active["minimum_provisional_demonstrations"] > active["minimum_mastery_demonstrations"]:
        raise ValueError("provisional threshold cannot exceed mastery threshold")
    if not isinstance(active["require_transfer"], bool):
        raise ValueError("require_transfer must be boolean")

    critical = list(unresolved_critical_misconceptions)
    if any(not isinstance(item, str) or not item for item in critical):
        raise ValueError("critical misconception tags must be non-empty strings")

    seen_ids: set[str] = set()
    qualifying: list[dict[str, Any]] = []
    rejected: list[dict[str, str]] = []
    for item in evidence:
        if not isinstance(item, dict):
            raise ValueError("each evidence item must be an object")
        evidence_id = item.get("evidence_id")
        if not isinstance(evidence_id, str) or not evidence_id:
            raise ValueError("each evidence item requires a non-empty evidence_id")
        if evidence_id in seen_ids:
            raise ValueError(f"duplicate evidence_id: {evidence_id}")
        seen_ids.add(evidence_id)

        for field in ("task_id", "session_id"):
            if not isinstance(item.get(field), str) or not item[field]:
                raise ValueError(f"{evidence_id}: {field} is required")
        kind = item.get("kind")
        if not isinstance(kind, str) or kind not in ALLOWED_KINDS:
            raise ValueError(f"{evidence_id}: unsupported pedagogical evidence kind")
        score = item.get("score")
        if isinstance(score, bool) or not isinstance(score, (int, float)) or not 0 <= score <= 1:
            raise ValueError(f"{evidence_id}: score must be between 0 and 1")
        if not isinstance(item.get("passed"), bool):
            raise ValueError(f"{evidence_id}: passed must be boolean")
        if not isinstance(item.get("is_transfer", False), bool):
            raise ValueError(f"{evidence_id}: is_transfer must be boolean")

        if not item["passed"]:
            rejected.append({"evidence_id": evidence_id, "reason": "not_passed"})
        elif score < score_floor:
            rejected.append({"evidence_id": evidence_id, "reason": "below_score_threshold"})
        else:
            qualifying.append({
                "evidence_id": evidence_id,
                "task_id": item["task_id"],
                "session_id": item["session_id"],
                "kind": kind,
                "is_transfer": item.get("is_transfer", False),
            })

    distinct_tasks = {item["task_id"] for item in qualifying}
    distinct_sessions = {item["session_id"] for item in qualifying}
    distinct_kinds = {item["kind"] for item in qualifying}
    transfer_seen = any(item["is_transfer"] for item in qualifying)
    metrics = {
        "qualifying_demonstrations": len(qualifying),
        "distinct_tasks": len(distinct_tasks),
        "distinct_sessions": len(distinct_sessions),
        "distinct_evidence_kinds": len(distinct_kinds),
        "transfer_demonstrated": transfer_seen,
    }

    provisional = (
        len(qualifying) >= active["minimum_provisional_demonstrations"]
        and len(distinct_tasks) >= active["minimum_distinct_tasks"]
        and len(distinct_sessions) >= active["minimum_distinct_sessions"]
    )
    mastered = (
        len(qualifying) >= active["minimum_mastery_demonstrations"]
        and len(distinct_tasks) >= active["minimum_distinct_tasks"]
        and len(distinct_sessions) >= active["minimum_distinct_sessions"]
        and len(distinct_kinds) >= active["minimum_evidence_kinds"]
        and (transfer_seen or not active["require_transfer"])
    )

    reasons: list[str] = []
    if critical:
        state = "needs_review"
        reasons.append("unresolved_critical_misconceptions")
    elif mastered:
        state = "mastered"
        reasons.append("all_mastery_policy_conditions_satisfied")
    elif provisional:
        state = "provisional"
        reasons.append("independent_demonstrations_support_provisional_mastery")
        if active["require_transfer"] and not transfer_seen:
            reasons.append("transfer_demonstration_still_required")
        if len(distinct_kinds) < active["minimum_evidence_kinds"]:
            reasons.append("additional_evidence_modality_required")
    elif qualifying:
        state = "practicing"
        reasons.append("more_independent_demonstrations_required")
    else:
        state = "unknown"
        reasons.append("no_qualifying_demonstrations")

    return {
        "state": state,
        "policy_version": POLICY_VERSION,
        "metrics": metrics,
        "qualifying_evidence_refs": sorted(item["evidence_id"] for item in qualifying),
        "rejected_evidence": sorted(rejected, key=lambda item: item["evidence_id"]),
        "unresolved_critical_misconceptions": sorted(set(critical)),
        "reason_codes": reasons,
        "is_formal_proof": False,
        "proof_authority": None,
    }
