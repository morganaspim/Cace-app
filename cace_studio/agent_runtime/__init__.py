"""Local Agent runtime and typed CACE Tool Bus.

This package is intentionally outside the CACE verification/proof trusted computing
base. Agent output and successful tool calls are observations/orchestration only.
"""

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
from .tool_bus import ToolBus

__all__ = [
    "AgentBudget",
    "AgentController",
    "AgentDecision",
    "AgentPlanner",
    "AgentRunReport",
    "AgentTurnContext",
    "Capability",
    "CapabilityPolicy",
    "LocalJSONPlanner",
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
