"""Browser and API boundary for CACE Studio.

The browser shell edits experiment graphs only. Scientific execution, typed/unit
connection validation, verification, and proof/claim truth remain in the canonical
Python core so the web UI cannot invent a second semantics.
"""
from __future__ import annotations

from dataclasses import asdict
import os
from pathlib import Path
import threading
import time
from typing import Any
from uuid import uuid4

from fastapi import Body, FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from cace_studio.app import build_registry
from cace_studio.core.execution_control import ExecutionControl
from cace_studio.core.executor import GraphExecutor
from cace_studio.core.graph import Edge, Experiment, ExperimentGroup, Node
from cace_studio.core.proof_explorer import ProofExplorer
from cace_studio.core.report import run_report
from cace_studio.core.types import port_connection_error


FORMAL_BASELINE_SHA = "7091548766deef4301ac8d62d3445d95945662e7"
FORMAL_QUALIFICATION_RUN_ID = "35280458500"
WEB_ROOT = Path(__file__).resolve().parents[1] / "web"

app = FastAPI(
    title="CACE Studio",
    description=(
        "Browser-facing CACE graph editor and execution API. Browser metadata is "
        "not verification evidence; run evidence is emitted by the canonical core."
    ),
)

if WEB_ROOT.is_dir():
    app.mount("/assets", StaticFiles(directory=WEB_ROOT), name="assets")


_registry = build_registry()
_jobs_lock = threading.RLock()
_jobs: dict[str, dict[str, Any]] = {}


def _module_payload(cls) -> dict[str, Any]:
    metadata = asdict(cls.metadata)
    metadata["maturity"] = cls.metadata.maturity.value
    return {
        "metadata": metadata,
        "inputs": [asdict(port) for port in cls.inputs],
        "outputs": [asdict(port) for port in cls.outputs],
        "parameters": [asdict(parameter) for parameter in cls.parameters],
        "declared_proof_status": cls.proof_status.to_dict(),
        "supports_gpu": bool(cls.supports_gpu),
    }


def _require_mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    return value


def _require_list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(f"{label} must be an array")
    return value


def _experiment_from_payload(raw: Any) -> Experiment:
    data = _require_mapping(raw, "experiment")
    container_schema = int(data.get("schema_version", 2))
    if container_schema not in {1, 2}:
        raise ValueError(f"unsupported experiment schema: {container_schema}")

    nodes: list[Node] = []
    for index, item in enumerate(_require_list(data.get("nodes", []), "nodes")):
        node = _require_mapping(item, f"nodes[{index}]")
        position = node.get("position", [0.0, 0.0])
        if not isinstance(position, (list, tuple)) or len(position) != 2:
            raise ValueError(f"nodes[{index}].position must contain x,y")
        params = node.get("params", {})
        if not isinstance(params, dict):
            raise ValueError(f"nodes[{index}].params must be an object")
        nodes.append(
            Node(
                id=str(node["id"]),
                module_id=str(node["module_id"]),
                params=dict(params),
                position=(float(position[0]), float(position[1])),
            )
        )

    edges: list[Edge] = []
    for index, item in enumerate(_require_list(data.get("edges", []), "edges")):
        edge = _require_mapping(item, f"edges[{index}]")
        edges.append(
            Edge(
                source_node=str(edge["source_node"]),
                source_port=str(edge["source_port"]),
                target_node=str(edge["target_node"]),
                target_port=str(edge["target_port"]),
            )
        )

    groups: list[ExperimentGroup] = []
    raw_groups = [] if container_schema == 1 else data.get("groups", [])
    for index, item in enumerate(_require_list(raw_groups, "groups")):
        group = _require_mapping(item, f"groups[{index}]")
        groups.append(
            ExperimentGroup(
                id=str(group["id"]),
                name=str(group["name"]),
                node_ids=tuple(str(node_id) for node_id in group.get("node_ids", [])),
            )
        )

    exp = Experiment(
        schema_version=int(data.get("graph_schema_version", 1)),
        name=str(data.get("name", "Untitled")),
        nodes=nodes,
        edges=edges,
        metadata=dict(data.get("metadata", {})),
        groups=groups,
    )

    node_ids = {node.id for node in nodes}
    if len(node_ids) != len(nodes):
        raise ValueError("node ids must be unique")
    grouped: set[str] = set()
    group_ids: set[str] = set()
    for group in groups:
        if group.id in group_ids:
            raise ValueError(f"duplicate experiment group id: {group.id}")
        group_ids.add(group.id)
        missing = sorted(set(group.node_ids) - node_ids)
        if missing:
            raise ValueError(f"group {group.id!r} references missing nodes: {missing}")
        overlap = sorted(grouped & set(group.node_ids))
        if overlap:
            raise ValueError(f"nodes may belong to only one group: {overlap}")
        grouped.update(group.node_ids)
    return exp


def _job_snapshot(job: dict[str, Any]) -> dict[str, Any]:
    control: ExecutionControl = job["control"]
    return {
        "job_id": job["job_id"],
        "status": job["status"],
        "paused": control.paused,
        "cancelled": control.cancelled,
        "created_at": job["created_at"],
        "started_at": job.get("started_at"),
        "finished_at": job.get("finished_at"),
        "result": job.get("result"),
        "error": job.get("error"),
    }


def _trim_jobs() -> None:
    with _jobs_lock:
        if len(_jobs) <= 64:
            return
        completed = sorted(
            (
                job for job in _jobs.values()
                if job["status"] in {"completed", "cancelled", "failed"}
            ),
            key=lambda job: float(job.get("finished_at") or job["created_at"]),
        )
        for job in completed[: max(0, len(_jobs) - 64)]:
            _jobs.pop(job["job_id"], None)


def _execute_job(
    job_id: str,
    experiment: Experiment,
    *,
    seed: int,
    target_node_ids: tuple[str, ...],
    gpu_enabled: bool,
) -> None:
    with _jobs_lock:
        job = _jobs[job_id]
        job["status"] = "running"
        job["started_at"] = time.time()
        control: ExecutionControl = job["control"]
    try:
        executor = GraphExecutor(_registry, gpu_enabled=gpu_enabled)
        if target_node_ids:
            result = executor.run_selected_upstream(
                experiment,
                target_node_ids,
                seed=seed,
                control=control,
            )
        else:
            result = executor.run(experiment, seed=seed, control=control)
        report = run_report(result, experiment.name)
        with _jobs_lock:
            job["result"] = report
            job["status"] = "completed" if result.completed else "cancelled"
            job["finished_at"] = time.time()
    except Exception as exc:
        with _jobs_lock:
            job["error"] = {
                "error": str(exc),
                "error_type": type(exc).__name__,
            }
            job["status"] = "failed"
            job["finished_at"] = time.time()
    finally:
        _trim_jobs()


@app.get("/")
def studio() -> FileResponse:
    index = WEB_ROOT / "index.html"
    if not index.is_file():
        raise HTTPException(status_code=503, detail="browser studio assets are unavailable")
    return FileResponse(index)


@app.get("/studio")
def studio_alias() -> FileResponse:
    return studio()


@app.get("/api")
def home() -> dict[str, Any]:
    return {
        "service": "CACE Studio",
        "status": "ok",
        "surface": "browser",
        "formal_baseline_commit": FORMAL_BASELINE_SHA,
        "formal_qualification_run_id": FORMAL_QUALIFICATION_RUN_ID,
        "deployed_source_commit": os.getenv("CACE_DEPLOYED_SHA", "unknown"),
        "proof_note": (
            "The browser shell is application code. Formal claims remain bounded by "
            "the canonical proof contract and the exact qualified baseline."
        ),
    }


@app.get("/api/health")
def health() -> dict[str, str]:
    return {
        "service": "CACE Studio",
        "status": "ok",
        "surface": "browser",
    }


@app.get("/api/modules")
def modules() -> dict[str, Any]:
    classes = sorted(
        _registry.classes(),
        key=lambda cls: (cls.metadata.category, cls.metadata.name, cls.metadata.module_id),
    )
    return {
        "schema": 1,
        "metadata_is_verification_evidence": False,
        "modules": [_module_payload(cls) for cls in classes],
    }


@app.get("/api/claims")
def claims() -> dict[str, Any]:
    explorer = ProofExplorer()
    return {
        "schema": 1,
        "proof_effect": "none",
        "claims": [view.to_dict() for view in explorer.all_claims()],
    }


@app.post("/api/connections/validate")
def validate_connection(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    try:
        source_module = _registry.create(str(payload["source_module_id"]))
        target_module = _registry.create(str(payload["target_module_id"]))
        source_port_name = str(payload["source_port"])
        target_port_name = str(payload["target_port"])
        source_ports = {port.name: port for port in source_module.outputs}
        target_ports = {port.name: port for port in target_module.inputs}
        if source_port_name not in source_ports:
            raise ValueError(f"unknown output port: {source_port_name}")
        if target_port_name not in target_ports:
            raise ValueError(f"unknown input port: {target_port_name}")
        reason = port_connection_error(
            source_ports[source_port_name],
            target_ports[target_port_name],
        )
        return {"valid": reason is None, "reason": reason}
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/runs")
def start_run(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    try:
        experiment = _experiment_from_payload(payload.get("experiment"))
        seed = int(payload.get("seed", 0))
        target_node_ids = tuple(str(node_id) for node_id in payload.get("target_node_ids", []))
        unknown_targets = sorted(set(target_node_ids) - {node.id for node in experiment.nodes})
        if unknown_targets:
            raise ValueError(f"unknown target node ids: {unknown_targets}")
        gpu_enabled = bool(payload.get("gpu_enabled", False))
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    job_id = str(uuid4())
    job = {
        "job_id": job_id,
        "status": "queued",
        "created_at": time.time(),
        "control": ExecutionControl(),
        "result": None,
        "error": None,
    }
    with _jobs_lock:
        _jobs[job_id] = job

    worker = threading.Thread(
        target=_execute_job,
        args=(job_id, experiment),
        kwargs={
            "seed": seed,
            "target_node_ids": target_node_ids,
            "gpu_enabled": gpu_enabled,
        },
        daemon=True,
        name=f"cace-web-run-{job_id[:8]}",
    )
    worker.start()
    return _job_snapshot(job)


@app.get("/api/runs/{job_id}")
def run_status(job_id: str) -> dict[str, Any]:
    with _jobs_lock:
        job = _jobs.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="unknown run job")
        return _job_snapshot(job)


@app.post("/api/runs/{job_id}/{action}")
def control_run(job_id: str, action: str) -> dict[str, Any]:
    if action not in {"pause", "resume", "cancel"}:
        raise HTTPException(status_code=404, detail="unknown run action")
    with _jobs_lock:
        job = _jobs.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="unknown run job")
        if job["status"] in {"completed", "cancelled", "failed"}:
            return _job_snapshot(job)
        control: ExecutionControl = job["control"]
        if action == "pause":
            control.pause()
        elif action == "resume":
            control.resume()
        else:
            control.cancel()
        return _job_snapshot(job)


# Authenticated, provenance-only artifact integrity endpoint. This router is
# deliberately separate from proof qualification and fails closed when its
# dedicated credentials, GitHub read token, or pinned signer are absent.
from cace_studio.core.artifact_integrity_api import router as artifact_integrity_router

app.include_router(artifact_integrity_router)
