from __future__ import annotations

from dataclasses import replace
from typing import Iterable
from uuid import uuid4

from .graph import Experiment, ExperimentGroup


def group_map(experiment: Experiment) -> dict[str, ExperimentGroup]:
    return {group.id: group for group in experiment.groups}


def node_group_map(experiment: Experiment) -> dict[str, str]:
    result: dict[str, str] = {}
    for group in experiment.groups:
        for node_id in group.node_ids:
            prior = result.get(node_id)
            if prior is not None and prior != group.id:
                raise ValueError(
                    f"node {node_id!r} belongs to multiple groups: {prior!r}, {group.id!r}"
                )
            result[node_id] = group.id
    return result


def create_group(
    experiment: Experiment,
    node_ids: Iterable[str],
    *,
    name: str,
    group_id: str | None = None,
) -> ExperimentGroup:
    """Create one named group transactionally over existing ungrouped nodes."""
    selected = tuple(sorted(set(str(node_id) for node_id in node_ids)))
    if not selected:
        raise ValueError("a group must contain at least one selected node")
    clean_name = name.strip()
    if not clean_name:
        raise ValueError("group name must be non-empty")

    known = {node.id for node in experiment.nodes}
    missing = sorted(set(selected) - known)
    if missing:
        raise ValueError(f"cannot group unknown nodes: {missing}")

    memberships = node_group_map(experiment)
    already_grouped = sorted(node_id for node_id in selected if node_id in memberships)
    if already_grouped:
        raise ValueError(f"selected nodes are already grouped: {already_grouped}")

    existing_ids = {group.id for group in experiment.groups}
    candidate_id = group_id or f"g_{uuid4().hex[:8]}"
    if candidate_id in existing_ids:
        raise ValueError(f"duplicate group id: {candidate_id}")

    group = ExperimentGroup(candidate_id, clean_name, selected)
    experiment.groups.append(group)
    return group


def remove_group(experiment: Experiment, group_id: str) -> ExperimentGroup:
    for index, group in enumerate(experiment.groups):
        if group.id == group_id:
            return experiment.groups.pop(index)
    raise KeyError(f"unknown experiment group: {group_id}")


def remove_nodes_from_groups(
    experiment: Experiment,
    node_ids: Iterable[str],
) -> tuple[str, ...]:
    """Remove node membership, deleting groups that become empty.

    Returns the IDs of groups that changed or were removed.
    """
    removing = set(str(node_id) for node_id in node_ids)
    if not removing:
        return ()
    changed: list[str] = []
    updated: list[ExperimentGroup] = []
    for group in experiment.groups:
        remaining = tuple(node_id for node_id in group.node_ids if node_id not in removing)
        if remaining == group.node_ids:
            updated.append(group)
            continue
        changed.append(group.id)
        if remaining:
            updated.append(replace(group, node_ids=remaining))
    experiment.groups = updated
    return tuple(changed)


def group_node_ids(experiment: Experiment, group_id: str) -> tuple[str, ...]:
    group = group_map(experiment).get(group_id)
    if group is None:
        raise KeyError(f"unknown experiment group: {group_id}")
    return group.node_ids
