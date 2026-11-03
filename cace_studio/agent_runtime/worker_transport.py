from __future__ import annotations

from dataclasses import asdict
from typing import Any, Mapping

from cace_studio.core.certificate import RunCertificate
from cace_studio.core.executor import RunResult
from cace_studio.core.types import EvidenceKind
from cace_studio.core.verification import VerificationRecord, VerificationState


def _jsonable(value: Any) -> Any:
    try:
        import numpy as np
        if isinstance(value, np.ndarray):
            return value.tolist()
        if isinstance(value, np.generic):
            return value.item()
    except Exception:
        pass
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return repr(value)


def run_result_to_data(result: RunResult) -> dict[str, Any]:
    return {
        "run_result_transport_schema": 1,
        "run_id": result.run_id,
        "outputs": _jsonable(result.outputs),
        "certificates": [asdict(item) for item in result.certificates],
        "verification": {
            node_id: [record.to_dict() for record in records]
            for node_id, records in result.verification.items()
        },
        "claim_decisions": _jsonable(result.claim_decisions),
        "experiment_name": result.experiment_name,
        "semantic_experiment_sha256": result.semantic_experiment_sha256,
        "full_experiment_sha256": result.full_experiment_sha256,
        "source_semantic_experiment_sha256": result.source_semantic_experiment_sha256,
        "source_full_experiment_sha256": result.source_full_experiment_sha256,
        "execution_scope_sha256": result.execution_scope_sha256,
        "scope_target_node_ids": list(result.scope_target_node_ids),
        "scope_included_node_ids": list(result.scope_included_node_ids),
        "seed": result.seed,
        "run_scope": result.run_scope,
        "completed": result.completed,
        "interruption_reason": result.interruption_reason,
    }


def run_result_from_data(payload: Mapping[str, Any]) -> RunResult:
    if payload.get("run_result_transport_schema") != 1:
        raise ValueError("unsupported run-result transport schema")
    outputs = payload.get("outputs")
    certificates = payload.get("certificates")
    verification = payload.get("verification")
    claim_decisions = payload.get("claim_decisions")
    if not isinstance(outputs, Mapping):
        raise ValueError("worker outputs must be an object")
    if not isinstance(certificates, list):
        raise ValueError("worker certificates must be an array")
    if not isinstance(verification, Mapping):
        raise ValueError("worker verification must be an object")
    if not isinstance(claim_decisions, Mapping):
        raise ValueError("worker claim_decisions must be an object")

    parsed_verification: dict[str, list[VerificationRecord]] = {}
    for node_id, raw_records in verification.items():
        if not isinstance(raw_records, list):
            raise ValueError("worker verification node entry must be an array")
        records: list[VerificationRecord] = []
        for raw in raw_records:
            if not isinstance(raw, Mapping):
                raise ValueError("worker verification record must be an object")
            metrics = raw.get("metrics", {})
            notes = raw.get("notes", [])
            if not isinstance(metrics, Mapping) or not isinstance(notes, list):
                raise ValueError("worker verification metrics/notes malformed")
            records.append(
                VerificationRecord(
                    verifier=str(raw["verifier"]),
                    kind=EvidenceKind(str(raw["kind"])),
                    claim=str(raw["claim"]),
                    state=VerificationState(str(raw["state"])),
                    method=str(raw["method"]),
                    metrics=dict(metrics),
                    notes=tuple(str(item) for item in notes),
                )
            )
        parsed_verification[str(node_id)] = records

    parsed_certificates: list[RunCertificate] = []
    for raw in certificates:
        if not isinstance(raw, Mapping):
            raise ValueError("worker certificate must be an object")
        parsed_certificates.append(
            RunCertificate(
                run_id=str(raw["run_id"]),
                node_id=str(raw["node_id"]),
                module_id=str(raw["module_id"]),
                module_version=str(raw["module_version"]),
                input_hash=str(raw["input_hash"]),
                parameter_hash=str(raw["parameter_hash"]),
                output_hash=str(raw["output_hash"]),
                evidence=tuple(str(item) for item in raw.get("evidence", [])),
                verification_hashes=tuple(
                    str(item) for item in raw.get("verification_hashes", [])
                ),
                requested_device=str(raw["requested_device"]),
                actual_device=str(raw["actual_device"]),
                backend=str(raw["backend"]),
                created_at=str(raw["created_at"]),
            )
        )

    normalized_outputs: dict[str, dict[str, Any]] = {}
    for node_id, value in outputs.items():
        if not isinstance(value, Mapping):
            raise ValueError("worker node output must be an object")
        normalized_outputs[str(node_id)] = dict(value)

    return RunResult(
        run_id=str(payload["run_id"]),
        outputs=normalized_outputs,
        certificates=parsed_certificates,
        verification=parsed_verification,
        claim_decisions={
            str(key): dict(value)
            for key, value in claim_decisions.items()
            if isinstance(value, Mapping)
        },
        experiment_name=str(payload.get("experiment_name", "")),
        semantic_experiment_sha256=str(
            payload.get("semantic_experiment_sha256", "")
        ),
        full_experiment_sha256=str(payload.get("full_experiment_sha256", "")),
        source_semantic_experiment_sha256=str(
            payload.get("source_semantic_experiment_sha256", "")
        ),
        source_full_experiment_sha256=str(
            payload.get("source_full_experiment_sha256", "")
        ),
        execution_scope_sha256=str(payload.get("execution_scope_sha256", "")),
        scope_target_node_ids=tuple(
            str(item) for item in payload.get("scope_target_node_ids", [])
        ),
        scope_included_node_ids=tuple(
            str(item) for item in payload.get("scope_included_node_ids", [])
        ),
        seed=int(payload.get("seed", 0)),
        run_scope=str(payload.get("run_scope", "full")),
        completed=bool(payload.get("completed", True)),
        interruption_reason=str(payload.get("interruption_reason", "")),
    )
