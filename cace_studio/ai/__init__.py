"""Optional local-AI interfaces for CACE Studio.

AI output is assistance only. This package is intentionally outside CACE's
verification and formal-evidence trusted computing base.
"""
from .provider import AIProvider, LocalAIError, ProviderHealth
from .local import create_local_provider, detect_local_providers
from .compact_geometric_ranker import CompactGeometricRanker, GeometricCandidateFeatures, FEATURE_NAMES

__all__ = [
    "AIProvider",
    "LocalAIError",
    "ProviderHealth",
    "create_local_provider",
    "detect_local_providers",
    "CompactGeometricRanker",
    "GeometricCandidateFeatures",
    "FEATURE_NAMES",
]
