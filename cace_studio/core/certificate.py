from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import hashlib, json
from typing import Any
from .verification import VerificationRecord


def _jsonable(value: Any) -> Any:
    try:
        import numpy as np
        if isinstance(value, np.ndarray): return value.tolist()
        if isinstance(value, np.generic): return value.item()
    except Exception: pass
    if isinstance(value, dict): return {str(k): _jsonable(v) for k,v in value.items()}
    if isinstance(value, (list, tuple)): return [_jsonable(v) for v in value]
    return value

def stable_hash(value: Any) -> str:
    payload = json.dumps(_jsonable(value), sort_keys=True, separators=(",", ":"), default=repr).encode()
    return hashlib.sha256(payload).hexdigest()

@dataclass(frozen=True)
class RunCertificate:
    run_id: str
    node_id: str
    module_id: str
    module_version: str
    input_hash: str
    parameter_hash: str
    output_hash: str
    evidence: tuple[str, ...]
    verification_hashes: tuple[str, ...]
    requested_device: str
    actual_device: str
    backend: str
    created_at: str

    @classmethod
    def build(cls, *, run_id: str, node_id: str, module_id: str, module_version: str,
              inputs: Any, params: Any, outputs: Any, verification: list[VerificationRecord], device) -> "RunCertificate":
        passed = [r for r in verification if r.passed]
        evidence = tuple(sorted({r.kind.value for r in passed}))
        return cls(run_id, node_id, module_id, module_version,
                   stable_hash(inputs), stable_hash(params), stable_hash(outputs), evidence,
                   tuple(r.artifact_hash() for r in verification), device.requested, device.actual, device.backend,
                   datetime.now(timezone.utc).isoformat())
