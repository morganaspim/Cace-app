from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Iterator, Mapping
from uuid import uuid4

from cace_studio.core.reproducibility import sha256_identity

from .contracts import (
    Capability,
    ToolAuditRecord,
    ToolResult,
    ToolStatus,
)


class AuditIntegrityError(ValueError):
    pass


def _record_from_dict(payload: Mapping[str, Any]) -> ToolAuditRecord:
    if payload.get("tool_audit_schema") != 1:
        raise AuditIntegrityError("unsupported Tool Bus audit record schema")
    record = ToolAuditRecord(
        sequence=int(payload["sequence"]),
        call_id=str(payload["call_id"]),
        tool_name=str(payload["tool_name"]),
        capability=Capability(str(payload["capability"])),
        status=ToolStatus(str(payload["status"])),
        approved=bool(payload["approved"]),
        input_sha256=str(payload["input_sha256"]),
        output_sha256=(
            str(payload["output_sha256"])
            if payload.get("output_sha256") is not None
            else None
        ),
        error=str(payload.get("error", "")),
        proof_effect=str(payload.get("proof_effect", "none")),
        promotion_authority=bool(payload.get("promotion_authority", False)),
    )
    if record.proof_effect != "none" or record.promotion_authority:
        raise AuditIntegrityError("durable audit record cannot carry proof authority")
    return record


def _result_from_dict(payload: Mapping[str, Any]) -> ToolResult:
    if payload.get("tool_result_schema") != 1:
        raise AuditIntegrityError("unsupported Tool Bus result schema")
    output = payload.get("output")
    if output is not None and not isinstance(output, Mapping):
        raise AuditIntegrityError("durable Tool Bus result output must be an object or null")
    result = ToolResult(
        call_id=str(payload["call_id"]),
        tool_name=str(payload["tool_name"]),
        status=ToolStatus(str(payload["status"])),
        output=dict(output) if output is not None else None,
        error=str(payload.get("error", "")),
        proof_effect=str(payload.get("proof_effect", "none")),
        promotion_authority=bool(payload.get("promotion_authority", False)),
    )
    if result.proof_effect != "none" or result.promotion_authority:
        raise AuditIntegrityError("durable Tool Bus result cannot carry proof authority")
    return result


class HashChainedAuditJournal:
    """Append-only local JSONL audit journal with a SHA-256 hash chain.

    Schema v1 stores ToolAuditRecord only. Schema v2 additionally stores the typed
    ToolResult so a checkpointed pending call can be recovered after a crash
    without re-executing the tool. Both schemas remain engineering/provenance data
    only and never create scientific or formal evidence.
    """

    def __init__(self, path: str | Path, *, session_id: str | None = None) -> None:
        self.path = Path(path).expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.session_id = session_id or str(uuid4())
        self._entries, self._last_sha256 = self.verify()

    @staticmethod
    def _entry_digest(
        previous_sha256: str | None,
        session_id: str,
        record: dict[str, Any],
        *,
        schema: int,
        result: dict[str, Any] | None = None,
    ) -> str:
        payload: dict[str, Any] = {
            "audit_chain_schema": schema,
            "previous_sha256": previous_sha256,
            "session_id": session_id,
            "record": record,
        }
        if schema == 2:
            payload["result"] = result
        return sha256_identity(payload)

    def _verified_entries(self) -> Iterator[dict[str, Any]]:
        if not self.path.exists():
            return
        previous: str | None = None
        with self.path.open("r", encoding="utf-8") as handle:
            for line_no, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise AuditIntegrityError(
                        f"audit line {line_no} is not valid JSON"
                    ) from exc
                if not isinstance(entry, dict):
                    raise AuditIntegrityError(
                        f"audit line {line_no} must be a JSON object"
                    )
                schema = entry.get("audit_entry_schema")
                if schema not in {1, 2}:
                    raise AuditIntegrityError(
                        f"audit line {line_no} has unsupported schema"
                    )
                if entry.get("previous_sha256") != previous:
                    raise AuditIntegrityError(
                        f"audit line {line_no} previous hash mismatch"
                    )
                session_id = entry.get("session_id")
                record_payload = entry.get("record")
                result_payload = entry.get("result")
                digest = entry.get("entry_sha256")
                if not isinstance(session_id, str) or not session_id:
                    raise AuditIntegrityError(
                        f"audit line {line_no} missing session_id"
                    )
                if not isinstance(record_payload, dict):
                    raise AuditIntegrityError(
                        f"audit line {line_no} missing record"
                    )
                if schema == 2 and not isinstance(result_payload, dict):
                    raise AuditIntegrityError(
                        f"audit line {line_no} missing typed result"
                    )
                expected = self._entry_digest(
                    previous,
                    session_id,
                    record_payload,
                    schema=schema,
                    result=result_payload if schema == 2 else None,
                )
                if digest != expected:
                    raise AuditIntegrityError(
                        f"audit line {line_no} content hash mismatch"
                    )

                record = _record_from_dict(record_payload)
                if schema == 2:
                    result = _result_from_dict(result_payload)
                    if (
                        result.call_id != record.call_id
                        or result.tool_name != record.tool_name
                        or result.status is not record.status
                    ):
                        raise AuditIntegrityError(
                            f"audit line {line_no} record/result mismatch"
                        )
                    if result.output is None:
                        if record.output_sha256 is not None:
                            raise AuditIntegrityError(
                                f"audit line {line_no} has output hash without output"
                            )
                    elif record.output_sha256 != sha256_identity(dict(result.output)):
                        raise AuditIntegrityError(
                            f"audit line {line_no} output hash mismatch"
                        )
                previous = expected
                yield entry

    def verify(self) -> tuple[int, str | None]:
        count = 0
        previous: str | None = None
        for entry in self._verified_entries():
            count += 1
            previous = str(entry["entry_sha256"])
        return count, previous

    @property
    def entries(self) -> int:
        return self._entries

    @property
    def last_sha256(self) -> str | None:
        return self._last_sha256

    def lookup_event(
        self,
        call_id: str,
    ) -> tuple[ToolAuditRecord, ToolResult] | None:
        found: tuple[ToolAuditRecord, ToolResult] | None = None
        for entry in self._verified_entries():
            if entry.get("audit_entry_schema") != 2:
                continue
            record_payload = entry["record"]
            if record_payload.get("call_id") == call_id:
                found = (
                    _record_from_dict(record_payload),
                    _result_from_dict(entry["result"]),
                )
        return found

    def lookup_result(self, call_id: str) -> ToolResult | None:
        event = self.lookup_event(call_id)
        return event[1] if event is not None else None

    def append(
        self,
        record: ToolAuditRecord,
        result: ToolResult | None = None,
    ) -> str:
        if not isinstance(record, ToolAuditRecord):
            raise TypeError("audit journal accepts ToolAuditRecord objects only")
        if result is not None:
            if not isinstance(result, ToolResult):
                raise TypeError("audit result must be a ToolResult")
            if (
                result.call_id != record.call_id
                or result.tool_name != record.tool_name
                or result.status is not record.status
            ):
                raise AuditIntegrityError("ToolAuditRecord and ToolResult do not match")

        record_payload = record.to_dict()
        result_payload = result.to_dict() if result is not None else None
        schema = 2 if result is not None else 1
        digest = self._entry_digest(
            self._last_sha256,
            self.session_id,
            record_payload,
            schema=schema,
            result=result_payload,
        )
        entry: dict[str, Any] = {
            "audit_entry_schema": schema,
            "session_id": self.session_id,
            "previous_sha256": self._last_sha256,
            "record": record_payload,
            "entry_sha256": digest,
            "evidence_note": (
                "tamper-evident engineering audit only; not scientific or formal evidence"
            ),
        }
        if result_payload is not None:
            entry["result"] = result_payload
        line = (
            json.dumps(
                entry,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
                allow_nan=False,
            )
            + "\n"
        )
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
