"""Validation for learner-facing exercise content."""
from __future__ import annotations

from typing import Any


ANSWER_FORMATS = frozenset({
    "written_explanation",
    "table_and_explanation",
    "python_code_and_explanation",
    "conjecture_and_counterexample_search",
    "proof",
    "python_code_and_tests",
    "python_experiment_and_explanation",
})


def validate_exercise_content(content: dict[str, Any], catalogue: dict[str, Any]) -> dict[str, Any]:
    """Validate that every curriculum task has a well-formed learner exercise."""
    if not isinstance(content, dict) or content.get("schema_version") != 1:
        raise ValueError("unsupported exercise content schema")
    if content.get("curriculum_id") != catalogue.get("curriculum_id"):
        raise ValueError("exercise content curriculum_id mismatch")
    curriculum_tasks = catalogue.get("tasks", [])
    expected = {item.get("task_id") for item in curriculum_tasks if isinstance(item, dict)}
    exercises = content.get("exercises")
    if not isinstance(exercises, list):
        raise ValueError("exercises must be an array")
    seen: set[str] = set()
    for exercise in exercises:
        if not isinstance(exercise, dict):
            raise ValueError("each exercise must be an object")
        task_id = exercise.get("task_id")
        if not isinstance(task_id, str) or task_id not in expected:
            raise ValueError(f"unknown exercise task_id: {task_id!r}")
        if task_id in seen:
            raise ValueError(f"duplicate exercise task_id: {task_id}")
        seen.add(task_id)
        for field in ("objective", "prompt"):
            if not isinstance(exercise.get(field), str) or not exercise[field].strip():
                raise ValueError(f"{task_id}: {field} is required")
        if exercise.get("answer_format") not in ANSWER_FORMATS:
            raise ValueError(f"{task_id}: unsupported answer_format")
        hints = exercise.get("hints")
        if not isinstance(hints, list) or len(hints) < 2 or any(not isinstance(x, str) or not x.strip() for x in hints):
            raise ValueError(f"{task_id}: at least two non-empty hints are required")
        rubric = exercise.get("rubric")
        if not isinstance(rubric, list) or not rubric:
            raise ValueError(f"{task_id}: rubric must be a non-empty array")
        dimensions: set[str] = set()
        for criterion in rubric:
            if not isinstance(criterion, dict):
                raise ValueError(f"{task_id}: rubric criterion must be an object")
            dimension = criterion.get("dimension")
            points = criterion.get("points")
            if not isinstance(dimension, str) or not dimension or dimension in dimensions:
                raise ValueError(f"{task_id}: rubric dimensions must be unique non-empty strings")
            if isinstance(points, bool) or not isinstance(points, int) or points < 1:
                raise ValueError(f"{task_id}: rubric points must be positive integers")
            if not isinstance(criterion.get("description"), str) or not criterion["description"].strip():
                raise ValueError(f"{task_id}: rubric description is required")
            dimensions.add(dimension)
        if not isinstance(exercise.get("transfer_prompt"), str) or not exercise["transfer_prompt"].strip():
            raise ValueError(f"{task_id}: transfer_prompt is required")
        tools = exercise.get("allowed_tools", [])
        if not isinstance(tools, list) or any(not isinstance(x, str) or not x for x in tools):
            raise ValueError(f"{task_id}: allowed_tools must be an array of strings")
    missing = sorted(expected - seen)
    if missing:
        raise ValueError(f"curriculum tasks missing exercise content: {missing}")
    return {
        "content_id": content.get("content_id"),
        "curriculum_id": content["curriculum_id"],
        "exercise_count": len(exercises),
        "exercises_by_task": {item["task_id"]: item for item in exercises},
    }
