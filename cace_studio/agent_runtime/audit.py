from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from uuid import uuid4

from cace_studio.core.reproducibility import sha256_identity

from .contracts import ToolAuditRecord


class AuditIntegrityError(ValueError):
    pass


class HashChainedAuditJournal:
    """Append-only local JSONL audit journal with a SHA-256 hash chain.

    This journal is engineering/provenance data only. Its hashes attest to the
    ordering and identity of recorded tool actions; they do not establish
    mathematical correctness, verification PASS, or formal proof status.
    """

    def __init__(self, path: str | Path, *, session_id: str | None = None) -> None:
        self.path = Path(path).expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.session_id = session_id or str(uuid4())
        self._entries, self._last_sha256 = self.verify()

    @staticmethod
    def _entry_digest(previous_sha256: str | None, session_id: str, record: dict[str, Any]) -> str:
        return sha256_identity(
            {
                "audit_chain_schema": 1,
                "previous_sha256": previous_sha256,
                "session_id": session_id,
                "record": record,
            }
        )

    def verify(self) -> tuple[int, str | None]:
        if not self.path.exists():
            return 0, None

        previous: str | None = None
        count = 0
        with self.path.open("r", encoding="utf-8") as handle:
            for line_no, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise AuditIntegrityError(f"audit line {line_no} is not valid JSON") from exc
                if not isinstance(entry, dict) or entry.get("audit_entry_schema") != 1:
                    raise AuditIntegrityError(f"audit line {line_no} has unsupported schema")
                if entry.get("previous_sha256") != previous:
                    raise AuditIntegrityError(f"audit line {line_no} previous hash mismatch")
                session_id = entry.get("session_id")
                record = entry.get("record")
                digest = entry.get("entry_sha256")
                if not isinstance(session_id, str) or not session_id:
                    raise AuditIntegrityError(f"audit line {line_no} missing session_id")
                if not isinstance(record, dict):
                    raise AuditIntegrityError(f"audit line {line_no} missing record")
                expected = self._entry_digest(previous, session_id, record)
                if digest != expected:
                    raise AuditIntegrityError(f"audit line {line_no} content hash mismatch")
                previous = expected
                count += 1
        return count, previous

    @property
    def entries(self) -> int:
        return self._entries

    @property
    def last_sha256(self) -> str | None:
        return self._last_sha256

    def append(self, record: ToolAuditRecord) -> str:
        if not isinstance(record, ToolAuditRecord):
            raise TypeError("audit journal accepts ToolAuditRecord objects only")
        payload = record.to_dict()
        digest = self._entry_digest(self._last_sha256, self.session_id, payload)
        entry = {
            "audit_entry_schema": 1,
            "session_id": self.session_id,
            "previous_sha256": self._last_sha256,
            "record": payload,
            "entry_sha256": digest,
            "evidence_note": "tamper-evident engineering audit only; not scientific or formal evidence",
        }
        line = json.dumps(entry, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
        flags = os.O_APPEND | os.O_CREAT | os.O_WRONLY
        fd = os.open(self.path, flags, 0o600)
        try:
            remaining = memoryview(line.encode("utf-8"))
            while remaining:
                written = os.write(fd, remaining)
                if written <= 0:
                    raise OSError("audit journal write made no progress")
                remaining = remaining[written:]
            os.fsync(fd)
        finally:
            os.close(fd)
        self._entries += 1
        self._last_sha256 = digest
        return digest
