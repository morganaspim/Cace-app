"""Optional local-AI interfaces for CACE Studio.

AI output is assistance only. This package is intentionally outside CACE's
verification and formal-evidence trusted computing base.
"""
from .provider import AIProvider, LocalAIError, ProviderHealth
from .local import create_local_provider, detect_local_providers
from .math_features import combine_sketches, hashed_text_sketch, signed_hash_sketch
from .ranker import RankerConfig, TinyResidualRanker
from .planner import CandidateAtom, CombinationPlanner, GroupCandidate, PlannerConfig
from .memory import ExperienceMemory
from .hybrid import HybridLocalAI, HybridSuggestion

__all__ = [
    "AIProvider",
    "LocalAIError",
    "ProviderHealth",
    "create_local_provider",
    "detect_local_providers",
    "CandidateAtom",
    "CombinationPlanner",
    "ExperienceMemory",
    "GroupCandidate",
    "HybridLocalAI",
    "HybridSuggestion",
    "PlannerConfig",
    "RankerConfig",
    "TinyResidualRanker",
    "combine_sketches",
    "hashed_text_sketch",
    "signed_hash_sketch",
]
