"""Browser and API boundary for CACE Studio.

The browser shell edits experiment graphs only. Scientific execution, typed/unit
connection validation, verification, and proof/claim truth remain in the canonical
Python core so the web UI cannot invent a second semantics.
"""
from __future__ import annotations

from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import re
import threading
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import uuid4

from fastapi import Body, FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from cace_studio.app import build_registry
from cace_studio.core.module import ValidationError
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

_UNIPROT_RE = re.compile(r"^[A-Z0-9]{1,12}$")


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


def _stable_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=repr)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _client_port_payload(port) -> dict[str, Any]:
    payload = asdict(port)
    payload["type"] = port.type_name
    return payload


def _client_parameter_payload(parameter) -> dict[str, Any]:
    payload = asdict(parameter)
    payload["type"] = parameter.type_name
    return payload


def _proof_evidence_level(proof: dict[str, Any]) -> str:
    evidence = set(proof.get("evidence") or [])
    for level in (
        "formally-verified",
        "interval-certified",
        "symbolic",
        "numerical",
        "experimental",
    ):
        if level in evidence:
            return level
    return "unverified"


def _capability_payload(cls) -> dict[str, Any]:
    payload = _module_payload(cls)
    proof = dict(payload["declared_proof_status"])
    proof["evidence_level"] = _proof_evidence_level(proof)
    proof["is_verified"] = False
    proof["proof_note"] = (
        "Declared module metadata is not formal qualification evidence. Exact-head "
        "qualification requires the CACE provenance and proof pipeline."
    )
    payload["inputs"] = [_client_port_payload(port) for port in cls.inputs]
    payload["outputs"] = [_client_port_payload(port) for port in cls.outputs]
    payload["parameters"] = [_client_parameter_payload(parameter) for parameter in cls.parameters]
    payload["declared_proof_status"] = proof
    return payload


def _capability_classes() -> list[type]:
    return sorted(
        _registry.classes(),
        key=lambda cls: (cls.metadata.category, cls.metadata.name, cls.metadata.module_id),
    )


def _capabilities_payload() -> dict[str, Any]:
    modules = [_capability_payload(cls) for cls in _capability_classes()]
    registry_identity = [
        {
            "module_id": item["metadata"]["module_id"],
            "version": item["metadata"]["version"],
            "inputs": item["inputs"],
            "outputs": item["outputs"],
            "parameters": item["parameters"],
        }
        for item in modules
    ]
    return {
        "schema": 1,
        "metadata_is_verification_evidence": False,
        "capability_policy_hash": _stable_hash(
            {"source": "cace-app-python-registry", "modules": registry_identity}
        ),
        "registry_contract_hash": _stable_hash({"modules": registry_identity}),
        "modules": modules,
    }


def _fetch_json_url(url: str, *, timeout: float = 15.0) -> Any:
    request = Request(url, headers={"Accept": "application/json", "User-Agent": "CACE-Studio/3.36"})
    with urlopen(request, timeout=timeout) as response:
        if response.status != 200:
            raise ValueError(f"upstream returned HTTP {response.status}")
        return json.loads(response.read(2_000_000).decode("utf-8"))



LOCAL_AI_MODELS = {
    "assistant": {
        "model": os.getenv("CACE_AI_GRANITE_MODEL", "granite3.3:2b-instruct"),
        "role": "conversation, routing, explanations",
        "capability": "chat",
    },
    "reasoner": {
        "model": os.getenv("CACE_AI_PHI_MODEL", "phi4-mini-reasoning"),
        "role": "mathematics, science, geometry, proof obligations",
        "capability": "reasoning",
    },
    "vision": {
        "model": os.getenv("CACE_AI_QWEN_MODEL", "qwen3.5:4b"),
        "role": "visual and spatial geometry interpretation",
        "capability": "vision",
    },
}
LOCAL_AI_PROVIDER = os.getenv("CACE_AI_PROVIDER", "ollama").strip().lower()
LOCAL_AI_BASE_URL = os.getenv("CACE_AI_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
LOCAL_AI_ENABLED = os.getenv("CACE_AI_ENABLED", "0").strip().lower() in {"1", "true", "yes", "on"}


def _post_json_url(url: str, payload: dict[str, Any], *, timeout: float = 60.0) -> Any:
    encoded = json.dumps(payload).encode("utf-8")
    request = Request(
        url,
        data=encoded,
        headers={"Content-Type": "application/json", "Accept": "application/json", "User-Agent": "CACE-Studio/3.36"},
        method="POST",
    )
    with urlopen(request, timeout=timeout) as response:
        if response.status < 200 or response.status >= 300:
            raise ValueError(f"upstream returned HTTP {response.status}")
        return json.loads(response.read(8_000_000).decode("utf-8"))


def _local_ai_network_boundary() -> dict[str, Any]:
    return {
        "ai_network_mode": "LOCAL_ZERO_CONTACT",
        "internet_access": False,
        "allowed_provider_hosts": ["127.0.0.1", "localhost"],
        "remote_api_imports_are_gui_backend_only": True,
        "evidence_authority": False,
    }


def _local_ai_status_payload() -> dict[str, Any]:
    status: dict[str, Any] = {
        "schema": "cace-local-ai-status-v1",
        "enabled": LOCAL_AI_ENABLED,
        "provider": LOCAL_AI_PROVIDER,
        "base_url": LOCAL_AI_BASE_URL if LOCAL_AI_ENABLED else None,
        "roles": LOCAL_AI_MODELS,
        "boundary": _local_ai_network_boundary(),
        "provider_health": "disabled",
        "available_models": [],
        "message": "Set CACE_AI_ENABLED=1 and run a local provider such as Ollama to enable real local inference.",
    }
    if not LOCAL_AI_ENABLED:
        return status
    if not (LOCAL_AI_BASE_URL.startswith("http://127.0.0.1") or LOCAL_AI_BASE_URL.startswith("http://localhost")):
        status["provider_health"] = "blocked"
        status["message"] = "Local AI provider URL must be localhost/127.0.0.1."
        return status
    try:
        if LOCAL_AI_PROVIDER == "ollama":
            payload = _fetch_json_url(f"{LOCAL_AI_BASE_URL}/api/tags", timeout=3.0)
            status["available_models"] = [item.get("name") for item in payload.get("models", []) if isinstance(item, dict)]
            status["provider_health"] = "ready"
            status["message"] = "Local Ollama provider reachable."
        else:
            payload = _fetch_json_url(f"{LOCAL_AI_BASE_URL}/v1/models", timeout=3.0)
            status["available_models"] = [item.get("id") for item in payload.get("data", []) if isinstance(item, dict)]
            status["provider_health"] = "ready"
            status["message"] = "Local OpenAI-compatible provider reachable."
    except Exception as exc:
        status["provider_health"] = "unreachable"
        status["message"] = f"Local provider not reachable: {exc}"
    return status


def _classify_ai_task(message: str, has_image: bool = False) -> str:
    lower = message.lower()
    if has_image or any(word in lower for word in ("image", "mesh", "see", "screenshot", "diagram")):
        return "vision"
    if any(word in lower for word in ("prove", "proof", "derive", "equation", "geometry", "pde", "fem", "field", "quantum", "molecule", "metamaterial")):
        return "reasoner"
    return "assistant"


def _local_ai_generate(role: str, message: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
    status = _local_ai_status_payload()
    if not status["enabled"] or status["provider_health"] != "ready":
        return {
            "schema": "cace-local-ai-response-v1",
            "status": "unavailable",
            "role": role,
            "model": LOCAL_AI_MODELS[role]["model"],
            "response": status["message"],
            "route_trace": ["Granite/router", "provider unavailable"],
            "boundary": _local_ai_network_boundary(),
        }
    model = LOCAL_AI_MODELS[role]["model"]
    system = (
        "You are a local CACE research assistant. You have no internet access. "
        "You may observe, reason, plan, and explain, but you cannot verify, certify, promote evidence, "
        "or override CACE validation. Prefer structured tool plans and identify proof obligations."
    )
    prompt = f"{system}\n\nContext JSON:\n{json.dumps(context or {}, sort_keys=True, default=repr)[:12000]}\n\nUser task:\n{message}"
    try:
        if LOCAL_AI_PROVIDER == "ollama":
            payload = _post_json_url(
                f"{LOCAL_AI_BASE_URL}/api/generate",
                {"model": model, "prompt": prompt, "stream": False},
                timeout=120.0,
            )
            response = str(payload.get("response", ""))
        else:
            payload = _post_json_url(
                f"{LOCAL_AI_BASE_URL}/v1/chat/completions",
                {"model": model, "messages": [{"role": "system", "content": system}, {"role": "user", "content": message}], "stream": False},
                timeout=120.0,
            )
            response = str(payload.get("choices", [{}])[0].get("message", {}).get("content", ""))
        return {
            "schema": "cace-local-ai-response-v1",
            "status": "ok",
            "role": role,
            "model": model,
            "response": response,
            "route_trace": ["Granite/router", role, "CACE boundary applied"],
            "boundary": _local_ai_network_boundary(),
        }
    except Exception as exc:
        return {
            "schema": "cace-local-ai-response-v1",
            "status": "failed",
            "role": role,
            "model": model,
            "response": f"Local inference failed: {exc}",
            "route_trace": ["Granite/router", role, "provider error"],
            "boundary": _local_ai_network_boundary(),
        }


def _proof_recompile_plan() -> dict[str, Any]:
    claims_payload = claims()
    capability_payload = _capabilities_payload()
    verified_like = [
        claim for claim in claims_payload.get("claims", [])
        if claim.get("qualification", {}).get("status") in {"PASS", "HISTORICAL_PASS"}
    ]
    modules = capability_payload.get("modules", [])
    proof_rank = sorted(
        [
            {
                "module_id": item["metadata"]["module_id"],
                "name": item["metadata"]["name"],
                "evidence_level": item["declared_proof_status"].get("evidence_level", "unverified"),
                "optimization_use": "train/evaluate tool-use, graph planning, proof-obligation extraction",
            }
            for item in modules
        ],
        key=lambda item: (item["evidence_level"] == "unverified", item["module_id"]),
    )[:24]
    return {
        "schema": "cace-ai-recompile-plan-v1",
        "status": "plan-only",
        "button_label": "Recompile AI with latest proofs",
        "recompile_is_automatic": False,
        "reason": "Model rebuilding must be explicit, benchmarked, and reviewed. This endpoint prepares the local proof/tool dataset plan only.",
        "inputs": {
            "qualified_claim_count": len(verified_like),
            "capability_count": len(modules),
            "network_mode": "LOCAL_ZERO_CONTACT",
        },
        "ranked_training_sources": proof_rank,
        "pipeline": [
            "collect exact-head CACE claims and module contracts",
            "generate local structured tool-use traces",
            "benchmark Granite routing, Phi reasoning, Qwen geometry perception",
            "fine-tune or adapter-train only after baseline metrics exist",
            "run regression/equivalence tests and Lean/CACE proof gates",
            "promote no model output unless CACE validation independently passes",
        ],
        "forbidden": [
            "internet access by the AI group",
            "automatic proof promotion",
            "silent self-modifying code deployment",
            "claims about God, aliens, multiverse, or reality beyond validated evidence",
        ],
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
    return {
        "schema": 1,
        "metadata_is_verification_evidence": False,
        "modules": [_module_payload(cls) for cls in _capability_classes()],
    }


@app.get("/api/capabilities")
def capabilities() -> dict[str, Any]:
    return _capabilities_payload()


@app.get("/api/capabilities/{module_id:path}")
def capability(module_id: str) -> dict[str, Any]:
    for item in _capabilities_payload()["modules"]:
        if item["metadata"]["module_id"] == module_id:
            return item
    raise HTTPException(status_code=404, detail="unknown module capability")


@app.get("/api/claims")
def claims() -> dict[str, Any]:
    explorer = ProofExplorer()
    return {
        "schema": 1,
        "proof_effect": "none",
        "claims": [view.to_dict() for view in explorer.all_claims()],
    }




@app.get("/api/ai/status")
def local_ai_status() -> dict[str, Any]:
    return _local_ai_status_payload()


@app.post("/api/ai/chat")
def local_ai_chat(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    message = str(payload.get("message", "")).strip()
    if not message:
        raise HTTPException(status_code=400, detail="message is required")
    role = payload.get("role") or _classify_ai_task(message, bool(payload.get("image")))
    if role not in LOCAL_AI_MODELS:
        raise HTTPException(status_code=400, detail="role must be assistant, reasoner, or vision")
    context = payload.get("context") if isinstance(payload.get("context"), dict) else {}
    return _local_ai_generate(str(role), message, context)


@app.post("/api/ai/recompile-plan")
def local_ai_recompile_plan() -> dict[str, Any]:
    return _proof_recompile_plan()


@app.get("/api/alphafold/{accession}")
def alphafold_prediction(accession: str) -> dict[str, Any]:
    normalized = accession.strip().upper()
    if not _UNIPROT_RE.fullmatch(normalized):
        raise HTTPException(status_code=400, detail="accession must look like a UniProt accession")
    url = f"https://alphafold.ebi.ac.uk/api/prediction/{normalized}"
    try:
        payload = _fetch_json_url(url)
    except HTTPError as exc:
        if exc.code == 404:
            raise HTTPException(status_code=404, detail="AlphaFold prediction not found") from exc
        raise HTTPException(status_code=502, detail=f"AlphaFold upstream HTTP {exc.code}") from exc
    except (URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=502, detail=f"AlphaFold lookup failed: {exc}") from exc

    predictions = payload if isinstance(payload, list) else [payload]
    if not predictions:
        raise HTTPException(status_code=404, detail="AlphaFold prediction not found")
    first = predictions[0]
    return {
        "schema": "cace-alphafold-prediction-v1",
        "authority": "AlphaFold Protein Structure Database / EMBL-EBI",
        "accession": normalized,
        "prediction_count": len(predictions),
        "entry": first,
        "urls": {
            "api": url,
            "entry": f"https://alphafold.ebi.ac.uk/entry/{normalized}",
            "cif": first.get("cifUrl"),
            "pdb": first.get("pdbUrl"),
            "pae": first.get("paeDocUrl"),
        },
        "evidence_note": (
            "AlphaFold predictions are imported as attributed protein-structure objects. "
            "They are not CACE proof evidence unless later checked by canonical CACE tools."
        ),
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


@app.post("/api/graphs/validate")
def validate_graph(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    try:
        experiment = _experiment_from_payload(payload.get("experiment"))
        order = GraphExecutor(_registry)._validate_and_order(experiment)
        return {
            "valid": True,
            "reason": None,
            "node_count": len(experiment.nodes),
            "edge_count": len(experiment.edges),
            "topological_order": order,
            "disallowed_modules": [],
        }
    except (KeyError, TypeError, ValueError, ValidationError) as exc:
        return {
            "valid": False,
            "reason": str(exc),
            "node_count": 0,
            "edge_count": 0,
        }


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
