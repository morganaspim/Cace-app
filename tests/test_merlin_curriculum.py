import json
from pathlib import Path

import pytest

from merlin_lms.curriculum import validate_curriculum


def valid_catalogue():
    path = Path(__file__).parents[1] / "merlin_lms" / "data" / "math_foundations_v1.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_starter_catalogue_has_valid_dag_and_task_references():
    result = validate_curriculum(valid_catalogue())
    assert result["curriculum_id"] == "math-foundations-v1"
    assert len(result["concept_order"]) == 7
    assert len(result["tasks"]) == 7
    assert result["concept_order"].index("whole-number-structure") < result["concept_order"].index("divisibility")
    assert result["concept_order"].index("prime-numbers") < result["concept_order"].index("proof-by-contradiction")


def test_rejects_unknown_concept_prerequisite():
    data = valid_catalogue()
    data["concepts"][0]["requires"] = ["not-a-concept"]
    with pytest.raises(ValueError, match="unknown prerequisite"):
        validate_curriculum(data)


def test_rejects_prerequisite_cycles():
    data = valid_catalogue()
    data["concepts"][0]["requires"] = ["finite-experiment-design"]
    with pytest.raises(ValueError, match="cycle detected"):
        validate_curriculum(data)


def test_rejects_duplicate_task_ids():
    data = valid_catalogue()
    data["tasks"].append(dict(data["tasks"][0]))
    with pytest.raises(ValueError, match="duplicate task_id"):
        validate_curriculum(data)


def test_rejects_task_with_unknown_concept():
    data = valid_catalogue()
    data["tasks"][0]["concept_id"] = "not-a-concept"
    with pytest.raises(ValueError, match="unknown concept_id"):
        validate_curriculum(data)


def test_catalogue_tasks_can_be_passed_directly_to_planner():
    from merlin_lms.planner import plan_next_tasks

    data = valid_catalogue()
    result = plan_next_tasks(
        {"pathway_weights": {"mathematician": 1.0},
         "interests": ["patterns"],
         "concept_states": []},
        data["tasks"],
    )
    assert result["eligible_count"] == 1
    assert result["ranked_tasks"][0]["task_id"] == "discover-counting-patterns"


def test_rejects_non_string_prerequisite_instead_of_crashing():
    data = valid_catalogue()
    data["tasks"][0]["requires"] = [["not-a-string"]]
    with pytest.raises(ValueError, match="requires references unknown concepts"):
        validate_curriculum(data)


def test_rejects_boolean_pathway_score():
    data = valid_catalogue()
    data["tasks"][0]["pathways"]["mathematician"] = True
    with pytest.raises(ValueError, match="must be between 0 and 1"):
        validate_curriculum(data)


def test_rejects_boolean_schema_version():
    data = valid_catalogue()
    data["schema_version"] = True
    with pytest.raises(ValueError, match="schema_version"):
        validate_curriculum(data)
