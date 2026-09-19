"""Optional local-AI interfaces for CACE Studio.

AI output is assistance only. This package is intentionally outside CACE's
verification and formal-evidence trusted computing base.
"""
from .provider import AIProvider, LocalAIError, ProviderHealth
from .local import create_local_provider, detect_local_providers
from .corpus import build_local_fragments, build_local_index
from .growth_memory import GrowthFeedbackEvent, PersistentGrowthMemory
from .hybrid import GrowthEngine, GrowResult, ResearchFragment, SparseResearchIndex

__all__ = [
    "AIProvider",
    "LocalAIError",
    "ProviderHealth",
    "create_local_provider",
    "detect_local_providers",
    "build_local_fragments",
    "build_local_index",
    "GrowthEngine",
    "GrowResult",
    "ResearchFragment",
    "SparseResearchIndex",
    "GrowthFeedbackEvent",
    "PersistentGrowthMemory",
]
