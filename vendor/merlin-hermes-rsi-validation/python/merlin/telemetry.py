""""Versioned, source-separated telemetry contracts for Merlin."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from math import isfinite
from typing import Any, Mapping
from uuid import uuid4

SOURCES = {"runtime", "simulation", "model_output", "verifier", "operator", "hermes", "mcfc", "avrea", "cace"}
KINDS = {
    "task.started", "task.progress", "task.completed", "agent.status",
    "model.inference", "verification.completed", "resource.sample",
    "decision.trace", "operator.action", "system.error",
    "research.stage", "agent.tool.started", "agent.tool.completed",
    "artifact.registered", "experiment.completed", "proof.checked",
    "hypothesis.updated", "outbox.acknowledged",
}

@dataclass(frozen=True)
class TelemetryEvent:
    event_id: str
    schema: str
    source: str
    kind: str
    timestamp: str
    run_id: str
    task_id: str | None
    payload: dict[str, Any]
    evidence_refs: tuple[str, ...] = ()
    model_id: str | None = None
    duration_ms: float | None = None
    cpu_percent: float | None = None
    memory_bytes: int | None = None

    def to_dict(self) -> dict[str, Any]:
        row = asdict(self)
        row["evidence_refs"] = list(self.evidence_refs)
        return row

def normalize_event(data: Mapping[str, Any]) -> dict[str, Any]:
    """Validate caller-supplied telemetry; never infer its source."""
    source, kind = data.get("source"), data.get("kind")
    if source not in SOURCES or kind not in KINDS:
        raise ValueError("unsupported telemetry source or kind")
    run_id = data.get("run_id")
    if not isinstance(run_id, str) or not run_id.strip() or len(run_id) > 128:
        raise ValueError("run_id must be a non-empty string of at most 128 chars")
    task_id = data.get("task_id")
    if task_id is not None and (not isinstance(task_id, str) or len(task_id) > 128):
        raise ValueError("task_id must be a string of at most 128 chars")
    payload = data.get("payload", {})
    if not isinstance(payload, dict):
        raise ValueError("payload must be an object")
    if kind == "resource.sample":
        for key in (
            "gpu_percent", "gpu_memory_bytes", "wall_seconds", "cpu_seconds",
            "peak_memory_bytes", "cpu_cores_reserved", "memory_bytes_reserved",
            "max_wall_seconds_reserved", "gpu_count_reserved",
            "compute_budget_units_reserved",
        ):
            value = payload.get(key)
            if value is not None and (
                isinstance(value, bool) or not isinstance(value, (int, float))
                or not isfinite(value) or value < 0
            ):
                raise ValueError(key + " must be finite and non-negative")
        if payload.get("gpu_percent", 0) > 100:
            raise ValueError("gpu_percent cannot exceed 100")
    refs = data.get("evidence_refs", [])
    if not isinstance(refs, (list, tuple)) or len(refs) > 100 or any(not isinstance(x, str) or not x or len(x) > 512 for x in refs):
        raise ValueError("evidence_refs must contain at most 100 non-empty strings")
    numeric = {}
    for key in ("duration_ms", "cpu_percent", "memory_bytes"):
        value = data.get(key)
        if value is not None:
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value) or value < 0:
                raise ValueError(f"{key} must be finite and non-negative")
            numeric[key] = value
    if numeric.get("cpu_percent", 0) > 100:
        raise ValueError("cpu_percent cannot exceed 100")
    model_id = data.get("model_id")
    if model_id is not None and (not isinstance(model_id, str) or len(model_id) > 256):
        raise ValueError("model_id must be a string of at most 256 chars")
    timestamp = data.get("timestamp", datetime.now(timezone.utc).isoformat())
    if not isinstance(timestamp, str) or len(timestamp) > 64:
        raise ValueError("timestamp must be an ISO timestamp string")
    event = TelemetryEvent(
        event_id=str(data.get("event_id") or uuid4()), schema="merlin-telemetry/1",
        source=source, kind=kind, timestamp=timestamp, run_id=run_id.strip(),
        task_id=task_id, payload=payload, evidence_refs=tuple(refs), model_id=model_id,
        duration_ms=numeric.get("duration_ms"), cpu_percent=numeric.get("cpu_percent"),
        memory_bytes=numeric.get("memory_bytes"))
    return event.to_dict()


def record_runtime_event(store: Any, *, path: str, method: str, status: int,
                         duration_ms: float, response_bytes: int) -> dict[str, Any]:
    """Append measured HTTP boundary telemetry; never persist request/response content."""
    event = normalize_event({
        "source": "runtime",
        "kind": "system.error" if status >= 500 else "task.completed",
        "run_id": str(uuid4()),
        "task_id": path[:128],
        "duration_ms": max(0.0, duration_ms),
        "payload": {"component": "http_api", "method": method,
                    "status_code": int(status), "response_bytes": int(response_bytes)},
    })
    store.append("/api/telemetry/ingest",
                 {"event_id": event["event_id"], "source": "runtime"},
                 {"event": event})
    return event


def loader_event_sink(store: Any):
    """Return a catalog event sink that persists normalized metadata-only telemetry."""
    def sink(data: Mapping[str, Any]) -> None:
        event = normalize_event(data)
        store.append("/api/telemetry/ingest",
                     {"event_id": event["event_id"], "source": "runtime"},
                     {"event": event})
    return sink


SERVICE_SOURCES = frozenset({"hermes", "mcfc", "avrea", "cace"})


def agent_event_sink(outbox: Any, service: str):
    """Create a source-bound publisher for observable service events."""
    if service not in SERVICE_SOURCES:
        raise ValueError("service must be hermes, mcfc, avrea, or cace")
    sink = telemetry_outbox_sink(outbox)

    def publish(*, kind: str, run_id: str, payload: Mapping[str, Any],
                task_id: str | None = None,
                evidence_refs: tuple[str, ...] | list[str] = (),
                duration_ms: float | None = None,
                cpu_percent: float | None = None,
                memory_bytes: int | None = None) -> dict[str, Any]:
        if not isinstance(payload, Mapping):
            raise ValueError("payload must be an object")
        body = dict(payload)
        if kind == "agent.status":
            body.setdefault("agent_id", service)
        normalized = normalize_event({
            "source": service, "kind": kind, "run_id": run_id,
            "task_id": task_id, "payload": body,
            "evidence_refs": list(evidence_refs),
            "duration_ms": duration_ms, "cpu_percent": cpu_percent,
            "memory_bytes": memory_bytes,
        })
        return sink(normalized)

    return publish

def telemetry_view(events: list[dict[str, Any]]) -> dict[str, Any]:
    grouped = {source: [] for source in sorted(SOURCES)}
    for event in events:
        if event.get("source") in grouped:
            grouped[event["source"]].append(event)
    return {"schema": "merlin-telemetry-view/1",
            "source_counts": {key: len(value) for key, value in grouped.items()},
            "streams": grouped, "simulation_is_not_runtime": True}


def telemetry_outbox_sink(outbox: Any):
    """Return a durable telemetry sink using event IDs as idempotency keys."""
    def sink_event(data: Mapping[str, Any]) -> dict[str, Any]:
        event = normalize_event(data)
        return outbox.enqueue(
            idempotency_key="telemetry:" + event["event_id"],
            topic="merlin.telemetry." + event["kind"],
            payload=event,
        )
    return sink_event
