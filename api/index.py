"""Browser and API boundary for CACE-KSEE.

The browser edits experiment graphs and renders typed capability metadata only.
Scientific execution, graph/type/unit validation, verification, and proof/claim
truth remain in the canonical CACE core.

The engineering ModuleRegistry may contain experimental/research modules that are
not product-ready.  Public discovery/execution is therefore fail-closed through
QualifiedCapabilityRegistry.
"""
from __future__ import annotations

import os
from pathlib import Path
import threading
import time
from typing import Any
from uuid import uuid4

from fastapi import Body, FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from cace_studio.app import build_qualified_capabilities, build_registry
from cace_studio.core.capability_registry import CapabilityRegistryError
from cace_studio.core.execution_control import ExecutionControl
from cace_studio.core.executor import GraphExecutor
from cace_studio.core.graph import Edge, Experiment, ExperimentGroup, Node
from cace_studio.core.proof_explorer import ProofExplorer
from cace_studio.core.report import run_report
from cace_studio.core.reproducibility import experiment_fingerprint


FORMAL_BASELINE_SHA = "7091548766deef4301ac8d62d3445d95945662e7"
FORMAL_QUALIFICATION_RUN_ID = "35280458500"
WEB_ROOT = Path(__file__).resolve().parents[1] / "web"

app = FastAPI(
    title="CACE-KSEE",
    description=(
        "Browser-facing CACE-KSEE graph editor and execution API. Browser metadata "
        "and engineering capability qualification are not mathematical proof "
        "evidence; run evidence is emitted by the canonical core."
    ),
)

if WEB_ROOT.is_dir():
    app.mount("/assets", StaticFiles(directory=WEB_ROOT), name="assets")


_registry = build_registry()
_capabilities = build_qualified_capabilities(_registry)
_jobs_lock = threading.RLock()
_jobs: dict[str, dict[str, Any]] = {}


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
                job
                for job in _jobs.values()
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
        # Defense in depth: a job accepted by the browser API remains constrained
        # even if queued state is mutated before the worker starts.
        _capabilities.validate_experiment(experiment, surface="api")
        executor = GraphExecutor(_registry, gpu_enabled=gpu_enabled)
        executor.validate(experiment)
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
        "service": "CACE-KSEE",
        "product_pronunciation": "Casey",
        "status": "ok",
        "surface": "browser",
        "formal_baseline_commit": FORMAL_BASELINE_SHA,
        "formal_qualification_run_id": FORMAL_QUALIFICATION_RUN_ID,
        "deployed_source_commit": os.getenv("CACE_DEPLOYED_SHA", "unknown"),
        "capability_policy_sha256": _capabilities.policy_sha256,
        "full_registry_contract_sha256": _capabilities.full_registry_contract_sha256,
        "proof_note": (
            "The browser shell and engineering capability manifest are application "
            "state. Formal claims remain bounded by the canonical proof contract "
            "and exact qualified proof provenance."
        ),
    }


@app.get("/api/health")
def health() -> dict[str, str]:
    return {
        "service": "CACE-KSEE",
        "status": "ok",
        "surface": "browser",
    }


@app.get("/api/capabilities")
def capabilities(surface: str = "ui") -> dict[str, Any]:
    try:
        return _capabilities.payload(surface)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/capabilities/{module_id}")
def capability(module_id: str) -> dict[str, Any]:
    try:
        _capabilities.require(module_id, "ui")
        return _capabilities.module_payload(module_id)
    except (KeyError, CapabilityRegistryError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/modules")
def modules() -> dict[str, Any]:
    """Compatibility catalog: only production UI-visible capabilities are returned."""
    payload = _capabilities.payload("ui")
    return {
        "schema": 2,
        "deprecated_in_favor_of": "/api/capabilities",
        "metadata_is_verification_evidence": False,
        "default_hidden": True,
        "capability_policy_sha256": payload["capability_policy_sha256"],
        "modules": payload["modules"],
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
        source_module_id = str(payload["source_module_id"])
        target_module_id = str(payload["target_module_id"])
        source_port_name = str(payload["source_port"])
        target_port_name = str(payload["target_port"])
        reason = _capabilities.connection_error(
            source_module_id,
            source_port_name,
            target_module_id,
            target_port_name,
        )
        return {
            "valid": reason is None,
            "reason": reason,
            "authority": "CACE backend",
        }
    except (KeyError, ValueError, CapabilityRegistryError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/graphs/validate")
def validate_graph(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    try:
        experiment = _experiment_from_payload(payload.get("experiment"))
        _capabilities.validate_experiment(experiment, surface="api")
        order = GraphExecutor(_registry).validate(experiment)
        return {
            "valid": True,
            "execution_order": list(order),
            "semantic_experiment_sha256": experiment_fingerprint(
                experiment, include_layout=False
            ),
            "capability_policy_sha256": _capabilities.policy_sha256,
            "proof_effect": "none",
        }
    except (KeyError, TypeError, ValueError, CapabilityRegistryError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/runs")
def start_run(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    try:
        experiment = _experiment_from_payload(payload.get("experiment"))
        _capabilities.validate_experiment(experiment, surface="api")
        GraphExecutor(_registry).validate(experiment)
        seed = int(payload.get("seed", 0))
        target_node_ids = tuple(
            str(node_id) for node_id in payload.get("target_node_ids", [])
        )
        unknown_targets = sorted(
            set(target_node_ids) - {node.id for node in experiment.nodes}
        )
        if unknown_targets:
            raise ValueError(f"unknown target node ids: {unknown_targets}")
        gpu_enabled = bool(payload.get("gpu_enabled", False))
    except (KeyError, TypeError, ValueError, CapabilityRegistryError) as exc:
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
