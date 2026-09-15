from __future__ import annotations
from dataclasses import asdict
from pathlib import Path
import hashlib, json, platform, sys
from typing import Any


def _clean(v: Any) -> Any:
    try:
        import numpy as np
        if isinstance(v, np.ndarray):
            return v.tolist()
        if isinstance(v, np.generic):
            return v.item()
    except Exception:
        pass
    if isinstance(v, dict):
        return {str(k): _clean(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [_clean(x) for x in v]
    return v


def _stable_hash(v: Any) -> str:
    return hashlib.sha256(
        json.dumps(_clean(v), sort_keys=True, separators=(",", ":"), default=repr).encode()
    ).hexdigest()


def _run_identity(result) -> dict[str, Any]:
    """Return experiment/run-scope identity recorded by the executor.

    Empty strings are retained for historical/manually-constructed RunResult
    objects. Current v3.36 qualification must exercise GraphExecutor-created
    results, which populate both experiment fingerprints.
    """
    return {
        "experiment_name": getattr(result, "experiment_name", ""),
        "semantic_experiment_sha256": getattr(result, "semantic_experiment_sha256", ""),
        "full_experiment_sha256": getattr(result, "full_experiment_sha256", ""),
        "seed": getattr(result, "seed", 0),
        "run_scope": getattr(result, "run_scope", "full"),
    }


def graph_certificate(result) -> dict[str, Any]:
    node_certs = [_clean(asdict(c)) for c in result.certificates]
    passed_records = [r for records in result.verification.values() for r in records if r.passed]
    all_records = [r for records in result.verification.values() for r in records]
    failed_records = [r for r in all_records if r.state.value == "fail"]
    not_run_records = [r for r in all_records if r.state.value == "not-run"]
    evidence = sorted({r.kind.value for r in passed_records})
    claim_decisions = _clean(getattr(result, "claim_decisions", {}))
    allowed_claims = sum(
        1
        for d in claim_decisions.values()
        if bool(d.get("public_resolution_claim_allowed", False))
    )
    payload = {
        "run_id": result.run_id,
        **_run_identity(result),
        "node_certificate_hashes": [_stable_hash(c) for c in node_certs],
        "all_verifiers_passed": result.all_verifiers_passed,
        "evidence_generated": evidence,
        "verification_records": sum(len(x) for x in result.verification.values()),
        "failed_verifiers": len(failed_records),
        "not_run_verifiers": len(not_run_records),
        "claim_decision_nodes": len(claim_decisions),
        "public_resolution_claims_allowed": allowed_claims,
        "claim_decisions_hash": _stable_hash(claim_decisions),
    }
    return {**payload, "certificate_hash": _stable_hash(payload)}


def run_report(result, experiment_name: str) -> dict[str, Any]:
    identity = _run_identity(result)
    recorded_name = identity["experiment_name"] or experiment_name
    return {
        "report_schema": 3,
        "experiment": recorded_name,
        "run_id": result.run_id,
        "run_scope": identity["run_scope"],
        "seed": identity["seed"],
        "semantic_experiment_sha256": identity["semantic_experiment_sha256"],
        "full_experiment_sha256": identity["full_experiment_sha256"],
        "all_verifiers_passed": result.all_verifiers_passed,
        "environment": {"python": sys.version, "platform": platform.platform()},
        "graph_certificate": graph_certificate(result),
        "claim_decisions": _clean(getattr(result, "claim_decisions", {})),
        "outputs": _clean(result.outputs),
        "certificates": [_clean(asdict(c)) for c in result.certificates],
        "verification": {
            node: [r.to_dict() for r in records]
            for node, records in result.verification.items()
        },
    }


def save_run_report(result, experiment_name: str, path: str | Path) -> None:
    Path(path).write_text(
        json.dumps(run_report(result, experiment_name), indent=2, sort_keys=True, default=repr)
        + "\n\n",
        encoding="utf-8",
    )
