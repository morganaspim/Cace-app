"""Validation utilities for versioned Merlin curriculum catalogues."""
from __future__ import annotations

from typing import Any


PATHWAYS = frozenset({
    "mathematician",
    "mathematics_programmer",
    "computational_problem_solver",
})


def validate_curriculum(catalogue: dict[str, Any]) -> dict[str, Any]:
    """Validate identifiers, references, pathway labels, and prerequisite DAG.

    Returns a normalized view containing concepts, tasks, and a deterministic
    prerequisite-first concept order. Raises ValueError on malformed input.
    """
    if not isinstance(catalogue, dict):
        raise ValueError("curriculum must be an object")
    if catalogue.get("schema_version") != 1:
        raise ValueError("unsupported curriculum schema_version")
    if not isinstance(catalogue.get("curriculum_id"), str) or not catalogue["curriculum_id"]:
        raise ValueError("curriculum_id is required")
    concepts = catalogue.get("concepts")
    tasks = catalogue.get("tasks")
    if not isinstance(concepts, list) or not isinstance(tasks, list):
        raise ValueError("curriculum concepts and tasks must be arrays")

    concept_by_id: dict[str, dict[str, Any]] = {}
    for concept in concepts:
        if not isinstance(concept, dict):
            raise ValueError("each concept must be an object")
        concept_id = concept.get("concept_id")
        if not isinstance(concept_id, str) or not concept_id:
            raise ValueError("each concept requires a non-empty concept_id")
        if concept_id in concept_by_id:
            raise ValueError(f"duplicate concept_id: {concept_id}")
        requires = concept.get("requires", [])
        pathways = concept.get("pathways", [])
        if not isinstance(requires, list) or any(not isinstance(x, str) or not x for x in requires):
            raise ValueError(f"{concept_id}: requires must be an array of concept IDs")
        if not isinstance(pathways, list) or any(x not in PATHWAYS for x in pathways):
            raise ValueError(f"{concept_id}: pathways contains an unknown pathway")
        concept_by_id[concept_id] = concept

    for concept_id, concept in concept_by_id.items():
        missing = sorted(set(concept.get("requires", [])) - concept_by_id.keys())
        if missing:
            raise ValueError(f"{concept_id}: unknown prerequisite concepts: {missing}")

    # Deterministic Kahn topological sort; a cycle is a curriculum authoring error.
    indegree = {concept_id: len(set(concept.get("requires", [])))
                for concept_id, concept in concept_by_id.items()}
    dependents = {concept_id: [] for concept_id in concept_by_id}
    for concept_id, concept in concept_by_id.items():
        for prerequisite in set(concept.get("requires", [])):
            dependents[prerequisite].append(concept_id)
    ready = sorted(key for key, degree in indegree.items() if degree == 0)
    order: list[str] = []
    while ready:
        current = ready.pop(0)
        order.append(current)
        for dependent in sorted(dependents[current]):
            indegree[dependent] -= 1
            if indegree[dependent] == 0:
                ready.append(dependent)
                ready.sort()
    if len(order) != len(concept_by_id):
        cyclic = sorted(key for key, degree in indegree.items() if degree > 0)
        raise ValueError(f"curriculum prerequisite cycle detected: {cyclic}")

    task_ids: set[str] = set()
    for task in tasks:
        if not isinstance(task, dict):
            raise ValueError("each task must be an object")
        task_id = task.get("task_id")
        if not isinstance(task_id, str) or not task_id:
            raise ValueError("each task requires a non-empty task_id")
        if task_id in task_ids:
            raise ValueError(f"duplicate task_id: {task_id}")
        task_ids.add(task_id)
        concept_id = task.get("concept_id")
        if concept_id not in concept_by_id:
            raise ValueError(f"{task_id}: unknown concept_id {concept_id!r}")
        task_requires = task.get("requires", [])
        if not isinstance(task_requires, list) or any(x not in concept_by_id for x in task_requires):
            raise ValueError(f"{task_id}: requires references unknown concepts")
        task_pathways = task.get("pathways", {})
        if not isinstance(task_pathways, dict) or any(key not in PATHWAYS for key in task_pathways):
            raise ValueError(f"{task_id}: pathways contains an unknown pathway")

    return {
        "curriculum_id": catalogue["curriculum_id"],
        "concept_order": order,
        "concepts": concept_by_id,
        "tasks": tasks,
    }
