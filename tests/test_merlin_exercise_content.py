import json
from pathlib import Path

import pytest

from merlin_lms.content import validate_exercise_content
from merlin_lms.curriculum import load_starter_curriculum


def load_content():
    path = Path(__file__).parents[1] / "merlin_lms" / "data" / "math_foundations_exercises_v1.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_all_starter_tasks_have_valid_exercise_content():
    result = validate_exercise_content(load_content(), {
        "curriculum_id": "math-foundations-v1",
        "tasks": load_starter_curriculum()["tasks"],
    })
    assert result["exercise_count"] == 7
    assert result["exercises_by_task"]["prove-infinite-primes"]["answer_format"] == "proof"


def test_rejects_missing_exercise_for_curriculum_task():
    content = load_content()
    content["exercises"].pop()
    with pytest.raises(ValueError, match="missing exercise content"):
        validate_exercise_content(content, {
            "curriculum_id": "math-foundations-v1",
            "tasks": load_starter_curriculum()["tasks"],
        })


def test_rejects_duplicate_exercise_ids():
    content = load_content()
    content["exercises"][1]["task_id"] = content["exercises"][0]["task_id"]
    with pytest.raises(ValueError, match="duplicate exercise"):
        validate_exercise_content(content, {
            "curriculum_id": "math-foundations-v1",
            "tasks": load_starter_curriculum()["tasks"],
        })


def test_rejects_exercise_without_transfer_prompt():
    content = load_content()
    content["exercises"][0].pop("transfer_prompt")
    with pytest.raises(ValueError, match="transfer_prompt"):
        validate_exercise_content(content, {
            "curriculum_id": "math-foundations-v1",
            "tasks": load_starter_curriculum()["tasks"],
        })


def test_rejects_rubric_with_duplicate_dimensions():
    content = load_content()
    rubric = content["exercises"][0]["rubric"]
    rubric[1]["dimension"] = rubric[0]["dimension"]
    with pytest.raises(ValueError, match="rubric dimensions"):
        validate_exercise_content(content, {
            "curriculum_id": "math-foundations-v1",
            "tasks": load_starter_curriculum()["tasks"],
        })
