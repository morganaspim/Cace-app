"""Local Agent runtime and typed CACE Tool Bus.

This package is intentionally outside the CACE verification/proof trusted computing
base. Agent output and successful tool calls are observations/orchestration only.
"""

from .audit import AuditIntegrityError, HashChainedAuditJournal
from .contracts import (
    Capability,
    CapabilityPolicy,
    ToolAuditRecord,
    ToolCall,
    ToolContext,
    ToolDescriptor,
    ToolResult,
    ToolStatus,
    TypedTool,
)
from .controller import (
    AgentBudget,
    AgentController,
    AgentDecision,
    AgentPlanner,
    AgentRunReport,
    AgentTurnContext,
    LocalJSONPlanner,
)
from .core_tools import register_core_tools
from .perception import (
    AgentNetworkMode,
    AgentPerceptionPacket,
    AgentPerceptionTracker,
    CanonicalEvidenceState,
    NodePerception,
    PerceptionHeartbeatState,
    ResidualTrend,
)
from .recovery import (
    AgentCheckpoint,
    AgentHeartbeat,
    AgentLease,
    AgentLeaseManager,
    AgentPhase,
    FileCheckpointStore,
    LeaseUnavailableError,
)
from .tool_bus import ToolBus

__all__ = [
    "AgentBudget",
    "AgentCheckpoint",
    "AgentController",
    "AgentDecision",
    "AgentHeartbeat",
    "AgentNetworkMode",
    "AgentPerceptionPacket",
    "AgentPerceptionTracker",
    "AgentLease",
    "AgentLeaseManager",
    "AgentPhase",
    "AgentPlanner",
    "AgentRunReport",
    "AgentTurnContext",
    "AuditIntegrityError",
    "Capability",
    "CapabilityPolicy",
    "CanonicalEvidenceState",
    "FileCheckpointStore",
    "HashChainedAuditJournal",
    "LeaseUnavailableError",
    "LocalJSONPlanner",
    "NodePerception",
    "PerceptionHeartbeatState",
    "ResidualTrend",
    "ToolAuditRecord",
    "ToolBus",
    "ToolCall",
    "ToolContext",
    "ToolDescriptor",
    "ToolResult",
    "ToolStatus",
    "TypedTool",
    "register_core_tools",
]
