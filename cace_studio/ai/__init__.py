"""Optional local-AI interfaces for CACE Studio.

AI output is assistance only. This package is intentionally outside CACE's
verification and formal-evidence trusted computing base.
"""
from .provider import AIProvider, LocalAIError, ProviderHealth
from .local import create_local_provider, detect_local_providers
from .heartbeat_context import HeartbeatContextPacket, build_heartbeat_context_packet
from .reasoning import (
    CaseEvaluation,
    ContrastEvaluation,
    CurriculumMastery,
    OperatorMastery,
    OperatorRegistry,
    OperatorStep,
    ProgramExecution,
    ReasoningAttempt,
    ReasoningCase,
    ReasoningContrastSet,
    ReasoningOperator,
    ReasoningProgram,
    default_operator_registry,
    evaluate_case,
    evaluate_contrast_set,
    generate_parity_contrast,
)

__all__ = [
    "AIProvider",
    "LocalAIError",
    "ProviderHealth",
    "create_local_provider",
    "detect_local_providers",
    "HeartbeatContextPacket",
    "build_heartbeat_context_packet",
    "CaseEvaluation",
    "ContrastEvaluation",
    "CurriculumMastery",
    "OperatorMastery",
    "OperatorRegistry",
    "OperatorStep",
    "ProgramExecution",
    "ReasoningAttempt",
    "ReasoningCase",
    "ReasoningContrastSet",
    "ReasoningOperator",
    "ReasoningProgram",
    "default_operator_registry",
    "evaluate_case",
    "evaluate_contrast_set",
    "generate_parity_contrast",
]
