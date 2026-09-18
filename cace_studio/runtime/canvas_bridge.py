from __future__ import annotations

from typing import Any

from .heartbeat import (
    CellState,
    HeartbeatCell,
    HeartbeatEdge,
    HeartbeatMode,
    HeartbeatPolicy,
    HeartbeatScheduler,
)
from .hashing import stable_hash


def _policy(raw: Any) -> HeartbeatPolicy:
    if not isinstance(raw, dict):
        return HeartbeatPolicy(HeartbeatMode.EVENT)
    mode = HeartbeatMode(str(raw.get("mode", "EVENT")).upper())
    return HeartbeatPolicy(
        mode=mode,
        period_ticks=int(raw["period_ticks"]) if raw.get("period_ticks") is not None else None,
        batch_size=int(raw["batch_size"]) if raw.get("batch_size") is not None else None,
        condition_name=str(raw["condition_name"]) if raw.get("condition_name") else None,
        stale_after_ticks=int(raw["stale_after_ticks"]) if raw.get("stale_after_ticks") is not None else None,
    )


def compile_canvas_heartbeat(
    experiment: dict[str, Any],
    *,
    master_seed: str,
    hash_algorithm: str = "blake3",
) -> tuple[HeartbeatScheduler, dict[str, Any]]:
    """Compile a web/JSON canvas into the runtime heartbeat control graph.

    Presentation-only fields such as node `position`, `tiling_mode`, and
    `rotation_3d` are deliberately ignored by the control-graph identity.
    """
    nodes = experiment.get("nodes")
    edges = experiment.get("edges")
    if not isinstance(nodes, list) or not isinstance(edges, list):
        raise ValueError("canvas experiment requires node and edge arrays")

    scheduler = HeartbeatScheduler(master_seed=master_seed, hash_algorithm=hash_algorithm)
    node_ids: set[str] = set()
    for raw in nodes:
        if not isinstance(raw, dict) or not isinstance(raw.get("id"), str) or not raw["id"]:
            raise ValueError("canvas node requires non-empty id")
        node_id = raw["id"]
        if node_id in node_ids:
            raise ValueError("canvas node ids must be unique")
        node_ids.add(node_id)
        params = raw.get("params") if isinstance(raw.get("params"), dict) else {}
        policy = _policy(params.get("__heartbeat"))
        scheduler.add_cell(
            HeartbeatCell(
                cell_id=node_id,
                policy=policy,
                state=CellState.READY,
                metadata={"module_id": str(raw.get("module_id", ""))},
            )
        )

    dedupe: set[tuple[str, str]] = set()
    for raw in edges:
        if not isinstance(raw, dict):
            raise ValueError("canvas edge must be an object")
        source = raw.get("source_node")
        target = raw.get("target_node")
        if source not in node_ids or target not in node_ids:
            raise ValueError("canvas edge references unknown node")
        key = (source, target)
        if key in dedupe:
            continue
        dedupe.add(key)
        scheduler.add_edge(
            HeartbeatEdge(
                source=source,
                target=target,
                transform_hash=str(raw.get("transform_hash", "identity")),
                unit_mapping=str(raw.get("unit_mapping", "identity")),
                coordinate_mapping="view-only:no-semantic-effect",
                evidence_policy="no-promotion",
            )
        )

    # Canvas computational dependency graphs must remain DAGs. Experimental
    # feedback worlds can use HeartbeatScheduler directly with explicit guards.
    scheduler.assert_acyclic()
    identity_payload = {
        "schema": "cace-canvas-heartbeat-graph-v1",
        "cells": [
            {
                "id": cell_id,
                "module_id": scheduler.cells[cell_id].metadata.get("module_id"),
                "heartbeat": scheduler.cells[cell_id].policy.mode.value,
            }
            for cell_id in sorted(scheduler.cells)
        ],
        "edges": [
            {
                "source": edge.source,
                "target": edge.target,
                "transform_hash": edge.transform_hash,
                "unit_mapping": edge.unit_mapping,
                "coordinate_mapping": edge.coordinate_mapping,
                "evidence_policy": edge.evidence_policy,
            }
            for edge in sorted(scheduler.edges, key=lambda item: (item.source, item.target))
        ],
    }
    summary = {
        **identity_payload,
        "graph_hash": stable_hash(identity_payload, algorithm=hash_algorithm),
        "hash_algorithm": hash_algorithm,
        "node_count": len(scheduler.cells),
        "edge_count": len(scheduler.edges),
    }
    return scheduler, summary
