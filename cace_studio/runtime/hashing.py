from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, is_dataclass
from enum import Enum
from typing import Any


class HashBackendUnavailable(RuntimeError):
    """Requested content-hash backend is not installed.

    CACE deliberately fails closed instead of calling a different algorithm
    "BLAKE3". Deployments that select BLAKE3 must install the optional blake3
    Python package (see requirements-runtime.txt).
    """


def _json_default(value: Any) -> Any:
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, bytes):
        return {"__bytes_hex__": value.hex()}
    if isinstance(value, tuple):
        return list(value)
    raise TypeError(f"unsupported canonical JSON value: {type(value)!r}")


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        default=_json_default,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def digest_bytes(data: bytes, *, algorithm: str = "sha256") -> str:
    normalized = algorithm.strip().lower()
    if normalized == "sha256":
        return hashlib.sha256(data).hexdigest()
    if normalized == "blake3":
        try:
            import blake3  # type: ignore[import-not-found]
        except ImportError as exc:
            raise HashBackendUnavailable(
                "BLAKE3 requested but Python package 'blake3' is unavailable"
            ) from exc
        return blake3.blake3(data).hexdigest()
    raise ValueError(f"unsupported hash algorithm: {algorithm}")


def stable_hash(value: Any, *, algorithm: str = "sha256") -> str:
    return digest_bytes(canonical_json_bytes(value), algorithm=algorithm)
