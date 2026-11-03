"""Optional local-AI interfaces for CACE Studio.

AI output is assistance only. This package is intentionally outside CACE's
verification and formal-evidence trusted computing base.
"""
from .provider import AIProvider, LocalAIError, ProviderHealth
from .local import create_local_provider, detect_local_providers
from .capability_gate import (
    AICapabilityManifest,
    AICapabilityPolicy,
    CapabilityDecision,
    CapabilityTier,
)
from .latent_observer import (
    LayerObservation,
    MatrixObserverArchive,
    MultiObserverBroker,
    ReplicatedObservation,
)
from .protein_play import (
    ProteinHeartbeatPlayEngine,
    ProteinPlayStep,
    ProteinPlayView,
    adapt_protein_structure,
    discover_protein_outputs,
)

__all__ = [
    "AIProvider",
    "LocalAIError",
    "ProviderHealth",
    "create_local_provider",
    "detect_local_providers",
    "AICapabilityManifest",
    "AICapabilityPolicy",
    "CapabilityDecision",
    "CapabilityTier",
    "LayerObservation",
    "MatrixObserverArchive",
    "MultiObserverBroker",
    "ReplicatedObservation",
    "ProteinHeartbeatPlayEngine",
    "ProteinPlayStep",
    "ProteinPlayView",
    "adapt_protein_structure",
    "discover_protein_outputs",
]
