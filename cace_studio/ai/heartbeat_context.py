from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from cace_studio.core.graph import Experiment
from cace_studio.core.heartbeat import HeartbeatFrame


@dataclass(frozen=True)
class HeartbeatContextPacket:
    schema: str
    tick: int
    role: str
    changed_nodes: tuple[dict[str, Any], ...]
    edges: tuple[dict[str, str], ...]
    note: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "tick": self.tick,
            "role": self.role,
            "changed_nodes": [dict(item) for item in self.changed_nodes],
            "edges": [dict(item) for item in self.edges],
            "note": self.note,
        }

    def to_prompt_text(self) -> str:
        lines = [
            "CACE CANVAS HEARTBEAT CONTEXT",
            "Coordination/navigation context only; never verification evidence.",
            f"Tick: {self.tick}",
            f"Changed nodes: {len(self.changed_nodes)}",
        ]
        for node in self.changed_nodes:
            lines.append(
                "- "
                + " ".join(
                    (
                        f"node={node['node_id']}",
                        f"module={node['module_id']}",
                        f"state={node['state']}",
                        f"interest={node['research_interest']:.3f}",
                        f"hash_changed={str(node['semantic_hash_changed']).lower()}",
                    )
                )
            )
        if self.edges:
            lines.append("Relevant dependency edges:")
            for edge in self.edges:
                lines.append(
                    f"- {edge['source_node']} -> {edge['target_node']}"
                )
        lines.append(self.note)
        return "\n".join(lines)


def build_heartbeat_context_packet(
    experiment: Experiment,
    current: HeartbeatFrame,
    previous: HeartbeatFrame | None = None,
    *,
    max_nodes: int = 64,
) -> HeartbeatContextPacket:
    """Build a bounded local-AI context packet from heartbeat deltas.

    The packet exposes state changes and dependency structure, but no mutation
    capability and no mechanism for promoting verification.
    """
    node_map = experiment.node_map()
    delta = current.delta(previous)
    current_by_id = current.by_id()

    changed = []
    included_ids: set[str] = set()
    for item in delta.changed[: max(0, int(max_nodes))]:
        heartbeat = current_by_id.get(item.node_id)
        node = node_map.get(item.node_id)
        if heartbeat is None or node is None:
            continue
        included_ids.add(item.node_id)
        changed.append(
            {
                "node_id": item.node_id,
                "module_id": node.module_id,
                "state": heartbeat.state.value,
                "previous_state": item.previous_state,
                "semantic_hash_changed": item.semantic_hash_changed,
                "research_interest": float(heartbeat.research_interest),
                "verification_summary": heartbeat.verification_summary,
                "error_family": heartbeat.error_family,
            }
        )

    edges = []
    for edge in experiment.edges:
        if edge.source_node in included_ids or edge.target_node in included_ids:
            edges.append(
                {
                    "source_node": edge.source_node,
                    "source_port": edge.source_port,
                    "target_node": edge.target_node,
                    "target_port": edge.target_port,
                }
            )

    return HeartbeatContextPacket(
        schema="cace.ai-heartbeat-context.v1",
        tick=current.tick,
        role="local AI attention/routing context; non-evidentiary",
        changed_nodes=tuple(changed),
        edges=tuple(edges),
        note=(
            "AI may use this packet to decide what to inspect or suggest next. "
            "AI attention cannot set PASS/FAIL/VERIFIED or mutate canonical evidence."
        ),
    )
