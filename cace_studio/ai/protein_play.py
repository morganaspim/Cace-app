from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import math
import random
from typing import Any, Mapping, Sequence

from cace_studio.ai.heartbeat_context import build_heartbeat_context_packet
from cace_studio.core.graph import Edge, Experiment, Node
from cace_studio.core.heartbeat import AIHeartbeatUpdate, CanvasHeartbeatEngine, HeartbeatFrame


def _coord3(value) -> tuple[float, float, float]:
    if not isinstance(value, (tuple, list)) or len(value) != 3:
        raise ValueError("protein C-alpha coordinates must be 3-vectors")
    result = tuple(float(item) for item in value)
    if not all(math.isfinite(item) for item in result):
        raise ValueError("protein coordinates must be finite")
    return result


def _sequence_text(sequence_obj) -> str:
    value = getattr(sequence_obj, "sequence", sequence_obj)
    text = str(value).strip().upper()
    if not text:
        raise ValueError("protein sequence is empty")
    return text


def _provenance_fields(provenance) -> tuple[str, str, str]:
    if provenance is None:
        return ("unspecified", "unspecified", "")
    return (
        str(getattr(provenance, "source", "unspecified")),
        str(getattr(provenance, "license_id", "unspecified")),
        str(getattr(provenance, "attribution", "")),
    )


@dataclass(frozen=True)
class ProteinPlayView:
    source_node_id: str
    sequence: str
    ca_coordinates: tuple[tuple[float, float, float], ...]
    confidence: tuple[float | None, ...]
    chain_ids: tuple[str, ...]
    source: str
    license_id: str
    attribution: str
    method: str
    limitations: tuple[str, ...]
    semantic_sha256: str

    @property
    def residue_count(self) -> int:
        return len(self.sequence)

    @property
    def mean_confidence(self) -> float | None:
        values = [value for value in self.confidence if value is not None]
        return None if not values else sum(values) / len(values)


def adapt_protein_structure(structure, *, source_node_id: str) -> ProteinPlayView:
    """Adapt a typed protein output without importing its implementation class."""
    if structure is None:
        raise ValueError("protein structure is missing")
    sequence = _sequence_text(getattr(structure, "sequence", ""))
    raw_coordinates = getattr(structure, "ca_coordinates", None)
    if not isinstance(raw_coordinates, (tuple, list)):
        raise ValueError("protein structure does not expose C-alpha coordinates")
    coordinates = tuple(_coord3(value) for value in raw_coordinates)
    if len(coordinates) != len(sequence):
        raise ValueError("protein sequence and coordinate counts differ")

    raw_confidence = getattr(structure, "plddt", ())
    if raw_confidence:
        if len(raw_confidence) != len(sequence):
            raise ValueError("protein confidence length does not match sequence")
        confidence = tuple(
            None
            if value is None
            else max(0.0, min(100.0, float(value)))
            for value in raw_confidence
        )
    else:
        confidence = tuple(None for _ in sequence)

    raw_chains = getattr(structure, "chain_ids", ())
    if raw_chains:
        if len(raw_chains) != len(sequence):
            raise ValueError("protein chain-id length does not match sequence")
        chain_ids = tuple(str(value) for value in raw_chains)
    else:
        chain_ids = tuple("_" for _ in sequence)

    source, license_id, attribution = _provenance_fields(
        getattr(structure, "provenance", None)
    )
    method = str(getattr(structure, "method", "unspecified"))
    limitations = tuple(str(value) for value in getattr(structure, "limitations", ()))

    payload = {
        "source_node_id": str(source_node_id),
        "sequence": sequence,
        "coordinates": coordinates,
        "confidence": confidence,
        "chain_ids": chain_ids,
        "source": source,
        "license_id": license_id,
        "attribution": attribution,
        "method": method,
        "limitations": limitations,
    }
    digest = sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), default=repr).encode()
    ).hexdigest()
    return ProteinPlayView(
        source_node_id=str(source_node_id),
        sequence=sequence,
        ca_coordinates=coordinates,
        confidence=confidence,
        chain_ids=chain_ids,
        source=source,
        license_id=license_id,
        attribution=attribution,
        method=method,
        limitations=limitations,
        semantic_sha256=digest,
    )


def discover_protein_outputs(run_result) -> tuple[tuple[str, ProteinPlayView], ...]:
    if run_result is None:
        return ()
    outputs = getattr(run_result, "outputs", {})
    if not isinstance(outputs, Mapping):
        return ()
    found = []
    for node_id in sorted(outputs):
        node_outputs = outputs[node_id]
        if not isinstance(node_outputs, Mapping) or "structure" not in node_outputs:
            continue
        try:
            view = adapt_protein_structure(
                node_outputs["structure"],
                source_node_id=str(node_id),
            )
        except (TypeError, ValueError):
            continue
        found.append((str(node_id), view))
    return tuple(found)


def _distance(a: Sequence[float], b: Sequence[float]) -> float:
    return math.sqrt(sum((float(x) - float(y)) ** 2 for x, y in zip(a, b)))


def _contact_counts(view: ProteinPlayView, cutoff: float = 8.0) -> tuple[int, ...]:
    counts = [0] * view.residue_count
    for left in range(view.residue_count):
        for right in range(left + 3, view.residue_count):
            if _distance(view.ca_coordinates[left], view.ca_coordinates[right]) <= cutoff:
                counts[left] += 1
                counts[right] += 1
    return tuple(counts)


def _heartbeat_experiment(view: ProteinPlayView) -> Experiment:
    nodes = []
    edges = []
    for index, residue in enumerate(view.sequence):
        node_id = f"residue_{index:05d}"
        nodes.append(
            Node(
                id=node_id,
                module_id=f"protein.play.residue.{residue}",
                params={
                    "residue": residue,
                    "index": index,
                    "chain_id": view.chain_ids[index],
                    "confidence": view.confidence[index],
                },
                position=(view.ca_coordinates[index][0], view.ca_coordinates[index][1]),
            )
        )
        if index:
            edges.append(
                Edge(
                    source_node=f"residue_{index - 1:05d}",
                    source_port="backbone",
                    target_node=node_id,
                    target_port="backbone",
                )
            )
    return Experiment(
        name=f"Protein Play: {view.source_node_id}",
        nodes=nodes,
        edges=edges,
        metadata={
            "role": "read-only protein heartbeat analysis; non-evidentiary",
            "protein_sha256": view.semantic_sha256,
        },
    )


@dataclass(frozen=True)
class ProteinPlayStep:
    cycle: int
    focus_indices: tuple[int, ...]
    focus_reasons: tuple[str, ...]
    frame: HeartbeatFrame
    context: str


class ProteinHeartbeatPlayEngine:
    """Read-only heartbeat exploration of an already-produced protein structure."""

    def __init__(self, view: ProteinPlayView, *, seed: int = 0) -> None:
        self.view = view
        self.seed = int(seed)
        self.cycle = 0
        self.experiment = _heartbeat_experiment(view)
        self.heartbeat = CanvasHeartbeatEngine()
        self.contact_counts = _contact_counts(view)

    def _semantic_hashes(self) -> dict[str, str]:
        result = {}
        for index, residue in enumerate(self.view.sequence):
            payload = (
                residue,
                self.view.ca_coordinates[index],
                self.view.confidence[index],
                self.view.chain_ids[index],
            )
            result[f"residue_{index:05d}"] = sha256(repr(payload).encode()).hexdigest()
        return result

    def _rank_focus(self) -> list[tuple[float, int, str]]:
        counts = self.contact_counts
        median = sorted(counts)[len(counts) // 2] if counts else 0
        ranked = []
        for index, residue in enumerate(self.view.sequence):
            conf = self.view.confidence[index]
            uncertainty = 0.25 if conf is None else max(0.0, (100.0 - conf) / 100.0)
            contacts = counts[index] if counts else 0
            geometry = min(1.0, abs(contacts - median) / max(2.0, median + 2.0))
            tie = random.Random(f"{self.seed}:{self.cycle}:{index}").random() * 1e-8
            score = 0.65 * uncertainty + 0.35 * geometry + tie
            ranked.append(
                (
                    score,
                    index,
                    (
                        f"{residue}{index + 1}: confidence="
                        f"{'n/a' if conf is None else f'{conf:.1f}'}, contacts={contacts}"
                    ),
                )
            )
        ranked.sort(key=lambda item: (-item[0], item[1]))
        return ranked

    def step(self, *, focus_budget: int = 8) -> ProteinPlayStep:
        previous = self.heartbeat.frame
        prior = previous.by_id() if previous is not None else {}
        updates = []
        for node_id, heartbeat in prior.items():
            if heartbeat.research_interest > 0.0:
                updates.append(
                    AIHeartbeatUpdate(
                        node_id,
                        -min(0.20, heartbeat.research_interest),
                        "decay prior protein-play attention",
                    )
                )
        ranked = self._rank_focus()
        selected = ranked[: max(1, min(int(focus_budget), len(ranked)))]
        for score, index, reason in selected:
            updates.append(
                AIHeartbeatUpdate(
                    f"residue_{index:05d}",
                    min(0.85, 0.25 + score),
                    reason,
                )
            )

        frame = self.heartbeat.advance(
            self.experiment,
            semantic_hashes=self._semantic_hashes(),
            inputs_ready_nodes=tuple(node.id for node in self.experiment.nodes),
            ai_updates=tuple(updates),
        )
        packet = build_heartbeat_context_packet(
            self.experiment,
            frame,
            previous,
            max_nodes=max(16, len(selected) * 2),
        )
        mean_conf = self.view.mean_confidence
        reasons = tuple(reason for _, _, reason in selected)
        context = "\n".join(
            [
                "CACE PROTEIN PLAY CONTEXT",
                "Read-only research exploration of an existing protein structure.",
                "Do not mutate the source structure. Do not treat this as experimental or clinical evidence.",
                f"Source canvas node: {self.view.source_node_id}",
                f"Sequence length: {self.view.residue_count}",
                f"Structure method: {self.view.method}",
                f"Source/provenance: {self.view.source}",
                f"License: {self.view.license_id}",
                f"Attribution: {self.view.attribution or 'none supplied'}",
                (
                    f"Mean confidence: {mean_conf:.2f}"
                    if mean_conf is not None
                    else "Mean confidence: unavailable"
                ),
                "Current heartbeat focus:",
                *(f"- {reason}" for reason in reasons),
                "",
                packet.to_prompt_text(),
                "",
                "Analyze structural patterns, uncertainty, contacts, and safe computational experiments. "
                "Do not provide biological-agent redesign or synthesis instructions. "
                "AI output remains non-evidentiary.",
            ]
        )
        result = ProteinPlayStep(
            cycle=self.cycle,
            focus_indices=tuple(index for _, index, _ in selected),
            focus_reasons=reasons,
            frame=frame,
            context=context,
        )
        self.cycle += 1
        return result
