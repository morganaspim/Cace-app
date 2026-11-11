"""Deterministic, explainable task ranking for Merlin's learning domain.

This module recommends learning tasks. It is not an assessment authority and
cannot create or promote mathematical evidence.
"""
from __future__ import annotations

from typing import Any, Iterable

PATHWAYS = (
    "mathematician",
    "mathematics_programmer",
    "computational_problem_solver",
)
MASTERY_PREREQUISITE_STATES = frozenset({"provisional", "mastered"})
CONCEPT_NEED = {
    "unknown": 1.0, "needs_review": 0.95, "introduced": 0.8,
    "practicing": 0.65, "provisional": 0.35, "mastered": 0.15,
}


def _unit_interval(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be a number between 0 and 1")
    result = float(value)
    if not 0.0 <= result <= 1.0:
        raise ValueError(f"{label} must be between 0 and 1")
    return result


def _learner_pathway_weights(learner: dict[str, Any]) -> dict[str, float]:
    raw = learner.get("pathway_weights", {})
    if not isinstance(raw, dict):
        raise ValueError("learner.pathway_weights must be an object")
    weights = {p: _unit_interval(raw.get(p, 0.0), f"pathway_weights.{p}") for p in PATHWAYS}
    total = sum(weights.values())
    if total <= 0:
        raise ValueError("at least one pathway weight must be greater than zero")
    return {key: value / total for key, value in weights.items()}


def _concept_index(learner: dict[str, Any]) -> dict[str, str]:
    raw = learner.get("concept_states", [])
    if not isinstance(raw, list):
        raise ValueError("learner.concept_states must be an array")
    result: dict[str, str] = {}
    for item in raw:
        if not isinstance(item, dict):
            raise ValueError("each concept state must be an object")
        concept_id, state = item.get("concept_id"), item.get("state")
        if not isinstance(concept_id, str) or not concept_id:
            raise ValueError("concept state requires a non-empty concept_id")
        if state not in CONCEPT_NEED:
            raise ValueError(f"unsupported concept state for {concept_id}: {state!r}")
        result[concept_id] = state
    return result


def _validate_task(task: dict[str, Any]) -> None:
    if not isinstance(task, dict):
        raise ValueError("each task must be an object")
    if not isinstance(task.get("task_id"), str) or not task["task_id"]:
        raise ValueError("task requires a non-empty task_id")
    if not isinstance(task.get("concept_id"), str) or not task["concept_id"]:
        raise ValueError(f"{task['task_id']}: concept_id is required")
    if not isinstance(task.get("requires", []), list):
        raise ValueError(f"{task['task_id']}: requires must be an array")
    if not isinstance(task.get("interest_tags", []), list):
        raise ValueError(f"{task['task_id']}: interest_tags must be an array")
    if not isinstance(task.get("pathways", {}), dict):
        raise ValueError(f"{task['task_id']}: pathways must be an object")
    for pathway, value in task.get("pathways", {}).items():
        if pathway not in PATHWAYS:
            raise ValueError(f"{task['task_id']}: unknown pathway {pathway!r}")
        _unit_interval(value, f"{task['task_id']}.pathways.{pathway}")
    _unit_interval(task.get("learning_value", 0.5), f"{task['task_id']}.learning_value")
    _unit_interval(task.get("transfer_value", 0.5), f"{task['task_id']}.transfer_value")
    minutes = task.get("estimated_minutes", 20)
    if isinstance(minutes, bool) or not isinstance(minutes, int) or minutes < 1:
        raise ValueError(f"{task['task_id']}: estimated_minutes must be a positive integer")


def _score_task(task, learner, weights, concepts, max_minutes):
    task_pathways = task.get("pathways", {})
    pathway_fit = sum(weights[p] * float(task_pathways.get(p, 0.0)) for p in PATHWAYS)
    learner_interests = set(learner.get("interests", []))
    task_interests = set(task.get("interest_tags", []))
    interest_fit = len(learner_interests & task_interests) / len(task_interests) if task_interests else 0.0
    learning_value = float(task.get("learning_value", 0.5))
    transfer_value = float(task.get("transfer_value", 0.5))
    current_state = concepts.get(task["concept_id"], "unknown")
    concept_need = CONCEPT_NEED[current_state]
    time_fit = 0.5 if max_minutes is None else max(0.0, 1.0 - task.get("estimated_minutes", 20) / max_minutes)
    components = {
        "pathway_fit": round(pathway_fit, 6),
        "interest_fit": round(interest_fit, 6),
        "learning_value": round(learning_value, 6),
        "transfer_value": round(transfer_value, 6),
        "concept_need": round(concept_need, 6),
        "time_fit": round(time_fit, 6),
    }
    score = (0.35 * pathway_fit + 0.20 * interest_fit + 0.20 * learning_value
             + 0.15 * transfer_value + 0.05 * concept_need + 0.05 * time_fit)
    reasons = []
    if pathway_fit > 0: reasons.append("matches_selected_pathways")
    if interest_fit > 0: reasons.append("matches_learner_interests")
    if learning_value >= 0.7: reasons.append("high_learning_value")
    if transfer_value >= 0.7: reasons.append("supports_transfer")
    if current_state in {"unknown", "needs_review", "introduced"}: reasons.append("addresses_unsettled_concept")
    if max_minutes is not None: reasons.append("fits_time_budget")
    return round(score, 6), components, reasons


def plan_next_tasks(learner: dict[str, Any], tasks: Iterable[dict[str, Any]], *,
                    max_minutes: int | None = None, limit: int = 5,
                    completed_task_ids: Iterable[str] = ()) -> dict[str, Any]:
    """Return ranked eligible tasks and explicit prerequisite/time-budget blocks.

    The ranking is deterministic for identical inputs and planner version.
    Prerequisites are ready only when their state is provisional or mastered.
    """
    if not isinstance(learner, dict):
        raise ValueError("learner must be an object")
    if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
        raise ValueError("limit must be a positive integer")
    if max_minutes is not None and (isinstance(max_minutes, bool) or not isinstance(max_minutes, int) or max_minutes < 1):
        raise ValueError("max_minutes must be a positive integer when supplied")
    weights = _learner_pathway_weights(learner)
    concepts = _concept_index(learner)
    completed = set(completed_task_ids)
    ranked, blocked, seen = [], [], set()
    for task in tasks:
        _validate_task(task)
        task_id = task["task_id"]
        if task_id in seen:
            raise ValueError(f"duplicate task_id: {task_id}")
        seen.add(task_id)
        if task_id in completed:
            continue
        minutes = task.get("estimated_minutes", 20)
        if max_minutes is not None and minutes > max_minutes:
            blocked.append({"task_id": task_id, "blocked_reason": "exceeds_time_budget", "estimated_minutes": minutes})
            continue
        missing = sorted({p for p in task.get("requires", []) if concepts.get(p) not in MASTERY_PREREQUISITE_STATES})
        if missing:
            blocked.append({"task_id": task_id, "blocked_reason": "prerequisites_not_yet_demonstrated", "missing_prerequisites": missing})
            continue
        score, components, reasons = _score_task(task, learner, weights, concepts, max_minutes)
        ranked.append({"task_id": task_id, "concept_id": task["concept_id"], "score": score,
                       "score_components": components, "reason_codes": reasons,
                       "estimated_minutes": minutes, "planner_version": "1.0.0"})
    ranked.sort(key=lambda item: (-item["score"], item["task_id"]))
    blocked.sort(key=lambda item: item["task_id"])
    return {"planner_version": "1.0.0", "ranked_tasks": ranked[:limit],
            "blocked_tasks": blocked, "eligible_count": len(ranked),
            "returned_count": min(len(ranked), limit)}
