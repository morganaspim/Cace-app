from __future__ import annotations

from cace_studio.ai.reasoning import (
    CurriculumMastery,
    OperatorStep,
    ReasoningAttempt,
    ReasoningProgram,
    default_operator_registry,
    evaluate_contrast_set,
    generate_parity_contrast,
)


def _correct_attempts(task):
    return tuple(
        ReasoningAttempt(
            case.case_id,
            case.expected_answer,
            case.expected_program,
        )
        for case in (task.canonical, task.causal_variant, task.invariant_variant)
    )


def test_operator_order_is_semantic_not_decorative():
    registry = default_operator_registry()
    scale_then_add = ReasoningProgram(
        (
            OperatorStep("scale", {"factor": 2}),
            OperatorStep("add", {"value": 3}),
        )
    )
    add_then_scale = ReasoningProgram(
        (
            OperatorStep("add", {"value": 3}),
            OperatorStep("scale", {"factor": 2}),
        )
    )
    first = registry.execute(scale_then_add, 4)
    second = registry.execute(add_then_scale, 4)
    assert first.valid and second.valid
    assert first.final_state == 11
    assert second.final_state == 14


def test_paired_intervention_passes_only_when_flip_and_invariance_are_correct():
    registry = default_operator_registry()
    task = generate_parity_contrast(17)
    result = evaluate_contrast_set(task, _correct_attempts(task), registry)
    assert result.pair_correct is True
    assert result.necessary_flip is True
    assert result.invariant_consistency is True
    assert result.all_programs_valid is True
    assert result.score == 1.0


def test_memorized_answer_fails_load_bearing_flip():
    registry = default_operator_registry()
    task = generate_parity_contrast(23)
    memorized = task.canonical.expected_answer
    attempts = tuple(
        ReasoningAttempt(case.case_id, memorized, case.expected_program)
        for case in (task.canonical, task.causal_variant, task.invariant_variant)
    )
    result = evaluate_contrast_set(task, attempts, registry)
    assert result.canonical.answer_correct is True
    assert result.causal.answer_correct is False
    assert result.necessary_flip is False
    assert result.score < 1.0


def test_unknown_operator_fails_closed():
    registry = default_operator_registry()
    result = registry.execute(
        ReasoningProgram((OperatorStep("not-a-real-operator"),)),
        3,
    )
    assert result.valid is False
    assert "unknown operator" in result.error


def test_curriculum_focus_prefers_unmastered_operator():
    registry = default_operator_registry()
    task = generate_parity_contrast(31)
    result = evaluate_contrast_set(task, _correct_attempts(task), registry)
    mastery = CurriculumMastery()
    mastery.record(task, result)
    assert mastery.score("parity") == 1.0
    assert mastery.next_focus(("parity", "rotate90"), limit=1) == ("rotate90",)


def test_reasoning_evaluation_explicitly_does_not_claim_thinking_or_proof():
    registry = default_operator_registry()
    task = generate_parity_contrast(41)
    result = evaluate_contrast_set(task, _correct_attempts(task), registry)
    payload = result.to_dict()
    assert "behavioral reasoning evaluation only" in payload["interpretation"]
    assert "mathematical verification" in payload["interpretation"]
