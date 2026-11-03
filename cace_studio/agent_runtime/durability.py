from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Mapping
from uuid import uuid4

from cace_studio.core.reproducibility import sha256_identity


class CrossProcessFileLock:
    """Small cross-platform advisory lock around one byte of a trusted lock file.

    The lock file is host-owned coordination state. It is never selected by the
    planning model and carries no proof/evidence authority.
    """

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path).expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._fd: int | None = None

    def __enter__(self) -> "CrossProcessFileLock":
        flags = os.O_RDWR | os.O_CREAT
        fd = os.open(self.path, flags, 0o600)
        try:
            if os.fstat(fd).st_size == 0:
                os.write(fd, b"\0")
                os.fsync(fd)
            os.lseek(fd, 0, os.SEEK_SET)
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(fd, msvcrt.LK_LOCK, 1)
            else:
                import fcntl
                fcntl.flock(fd, fcntl.LOCK_EX)
        except Exception:
            os.close(fd)
            raise
        self._fd = fd
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        fd = self._fd
        self._fd = None
        if fd is None:
            return
        try:
            os.lseek(fd, 0, os.SEEK_SET)
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)


def atomic_write_json(path: str | Path, payload: Mapping[str, Any]) -> None:
    """Durably replace a JSON object using a same-directory temporary file."""
    target = Path(path).expanduser()
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_name(f".{target.name}.{uuid4().hex}.tmp")
    text = (
        json.dumps(
            dict(payload),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    )
    try:
        with temp.open("x", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            temp.chmod(0o600)
        except OSError:
            pass
        os.replace(temp, target)
        _fsync_directory(target.parent)
    finally:
        try:
            temp.unlink()
        except FileNotFoundError:
            pass


def _fsync_directory(path: Path) -> None:
    if os.name == "nt":
        return
    flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY
    try:
        fd = os.open(path, flags)
    except OSError:
        return
    try:
        os.fsync(fd)
    except OSError:
        pass
    finally:
        os.close(fd)


def hashed_envelope(
    *,
    schema_key: str,
    schema_value: int,
    digest_key: str,
    payload_key: str,
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    plain = dict(payload)
    return {
        schema_key: schema_value,
        digest_key: sha256_identity(plain),
        payload_key: plain,
    }


def validate_hashed_envelope(
    raw: Any,
    *,
    schema_key: str,
    schema_value: int,
    digest_key: str,
    payload_key: str,
) -> dict[str, Any]:
    if not isinstance(raw, dict) or raw.get(schema_key) != schema_value:
        raise ValueError("unsupported durable coordination envelope")
    payload = raw.get(payload_key)
    if not isinstance(payload, dict):
        raise ValueError("durable coordination envelope missing payload")
    if raw.get(digest_key) != sha256_identity(payload):
        raise ValueError("durable coordination envelope hash mismatch")
    return payload
