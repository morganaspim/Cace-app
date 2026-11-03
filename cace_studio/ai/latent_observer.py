from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import os
from pathlib import Path
import re
from typing import Any, Sequence

import numpy as np


_SAFE = re.compile(r"[^A-Za-z0-9_.-]+")


def _safe(value: str) -> str:
    text = _SAFE.sub("_", str(value).strip())[:96]
    if not text:
        raise ValueError("observer identifiers must be non-empty")
    return text


def _matrix_digest(array: np.ndarray) -> str:
    canonical = np.ascontiguousarray(array)
    header = json.dumps(
        {"shape": list(canonical.shape), "dtype": str(canonical.dtype)},
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return sha256(header + canonical.tobytes(order="C")).hexdigest()


@dataclass(frozen=True)
class LayerObservation:
    run_id: str
    model_digest: str
    layer_name: str
    layer_index: int
    step_index: int
    shape: tuple[int, ...]
    dtype: str
    capture_mode: str
    matrix_sha256: str
    replica_id: str
    artifact_path: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class MatrixObserverArchive:
    """Content-addressed hidden-layer archive with no inference feedback API."""

    MODES = {"full", "sketch", "hash-only"}

    def __init__(self, root: str | Path, *, replica_id: str) -> None:
        self.root = Path(root)
        self.replica_id = _safe(replica_id)
        self.root.mkdir(parents=True, exist_ok=True)
        self.manifest_path = self.root / "observations.jsonl"

    def observe(
        self,
        *,
        run_id: str,
        model_digest: str,
        layer_name: str,
        layer_index: int,
        step_index: int,
        matrix,
        capture_mode: str = "hash-only",
        max_full_bytes: int = 64 * 1024 * 1024,
    ) -> LayerObservation:
        if capture_mode not in self.MODES:
            raise ValueError(f"unsupported capture mode: {capture_mode}")
        array = np.asarray(matrix)
        if array.dtype.hasobject:
            raise TypeError("object-dtype activation matrices are not supported")
        if array.ndim < 1:
            raise ValueError("activation matrix must have at least one dimension")
        digest = _matrix_digest(array)
        artifact_path = ""
        stem = (
            f"{_safe(run_id)}-{_safe(model_digest)[:20]}-"
            f"L{int(layer_index):05d}-S{int(step_index):08d}-{digest[:16]}"
        )
        if capture_mode == "full":
            if int(array.nbytes) > int(max_full_bytes):
                raise ValueError("full activation capture exceeds the configured byte budget")
            target = self.root / f"{stem}.npy"
            if not target.exists():
                temp = self.root / f".{stem}.tmp.npy"
                with temp.open("wb") as handle:
                    np.save(handle, np.ascontiguousarray(array), allow_pickle=False)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temp, target)
                try:
                    target.chmod(0o444)
                except OSError:
                    pass
            artifact_path = str(target)
        elif capture_mode == "sketch":
            target = self.root / f"{stem}.sketch.json"
            flat = np.asarray(array, dtype=float).reshape(-1)
            payload = {
                "shape": list(array.shape),
                "dtype": str(array.dtype),
                "matrix_sha256": digest,
                "mean": float(np.mean(flat)) if flat.size else 0.0,
                "std": float(np.std(flat)) if flat.size else 0.0,
                "l2": float(np.linalg.norm(flat)) if flat.size else 0.0,
                "min": float(np.min(flat)) if flat.size else 0.0,
                "max": float(np.max(flat)) if flat.size else 0.0,
            }
            if not target.exists():
                temp = target.with_suffix(target.suffix + ".tmp")
                temp.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
                os.replace(temp, target)
                try:
                    target.chmod(0o444)
                except OSError:
                    pass
            artifact_path = str(target)
        record = LayerObservation(
            run_id=_safe(run_id),
            model_digest=_safe(model_digest),
            layer_name=str(layer_name)[:160],
            layer_index=int(layer_index),
            step_index=int(step_index),
            shape=tuple(int(value) for value in array.shape),
            dtype=str(array.dtype),
            capture_mode=capture_mode,
            matrix_sha256=digest,
            replica_id=self.replica_id,
            artifact_path=artifact_path,
        )
        with self.manifest_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record.to_dict(), sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        return record


@dataclass(frozen=True)
class ReplicatedObservation:
    observations: tuple[LayerObservation, ...]
    digests_match: bool


class MultiObserverBroker:
    """Host-side one-way fanout. There is deliberately no model feedback method."""

    def __init__(self, observers: Sequence[MatrixObserverArchive]) -> None:
        self.observers = tuple(observers)
        if len(self.observers) < 2:
            raise ValueError("at least two observer replicas are required")

    def fanout(self, **kwargs) -> ReplicatedObservation:
        observations = tuple(observer.observe(**kwargs) for observer in self.observers)
        return ReplicatedObservation(
            observations,
            len({record.matrix_sha256 for record in observations}) == 1,
        )
