from __future__ import annotations
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any
import hashlib, json
from .types import EvidenceKind

class VerificationState(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    NOT_RUN = "not-run"

@dataclass(frozen=True)
class VerificationRecord:
    verifier: str
    kind: EvidenceKind
    claim: str
    state: VerificationState
    method: str
    metrics: dict[str, Any] = field(default_factory=dict)
    notes: tuple[str, ...] = ()

    @property
    def passed(self) -> bool:
        return self.state is VerificationState.PASS

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["kind"] = self.kind.value
        d["state"] = self.state.value
        return d

    def artifact_hash(self) -> str:
        payload = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"), default=repr).encode()
        return hashlib.sha256(payload).hexdigest()
