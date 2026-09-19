"""Optional local-AI interfaces for CACE Studio.

AI output is assistance only. This package is intentionally outside CACE's
verification and formal-evidence trusted computing base.
"""
from .provider import AIProvider, LocalAIError, ProviderHealth
from .local import create_local_provider, detect_local_providers
from .corpus import build_local_fragments, build_local_index
from .experiment_proposal import (
    PROPOSAL_STRATEGIES,
    ExperimentGraphProposal,
    ProposalStrategy,
    ProposedEdge,
    ProposedNode,
    UnresolvedInput,
    materialize_experiment_proposal,
    propose_experiment_graph,
    propose_experiment_strategies,
)
from .grow_candidates import GrowCandidate, build_grow_candidates
from .growth_memory import GrowthFeedbackEvent, PersistentGrowthMemory
from .research_ideas import IDEA_STATUSES, ResearchIdea, ResearchIdeaStore, seed_from_grow_candidate
from .strategy_compare import (
    OutputSummary,
    StrategyComparison,
    StrategyRunSummary,
    compare_proposal_strategies,
)
from .hybrid import GrowthEngine, GrowResult, ResearchFragment, SparseResearchIndex

__all__ = [
    "AIProvider",
    "LocalAIError",
    "ProviderHealth",
    "create_local_provider",
    "detect_local_providers",
    "build_local_fragments",
    "build_local_index",
    "PROPOSAL_STRATEGIES",
    "ExperimentGraphProposal",
    "ProposalStrategy",
    "ProposedEdge",
    "ProposedNode",
    "UnresolvedInput",
    "materialize_experiment_proposal",
    "propose_experiment_graph",
    "propose_experiment_strategies",
    "GrowthEngine",
    "GrowResult",
    "ResearchFragment",
    "SparseResearchIndex",
    "GrowthFeedbackEvent",
    "PersistentGrowthMemory",
    "GrowCandidate",
    "build_grow_candidates",
    "IDEA_STATUSES",
    "ResearchIdea",
    "ResearchIdeaStore",
    "seed_from_grow_candidate",
    "OutputSummary",
    "StrategyComparison",
    "StrategyRunSummary",
    "compare_proposal_strategies",
]
