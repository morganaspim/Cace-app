from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import sqlite3
import time
from typing import Any

import numpy as np

from .math_features import cosine_similarity


@dataclass(frozen=True)
class Experience:
    experience_id: int
    created_at: float
    task_text: str
    task_sketch: np.ndarray
    candidate_ids: tuple[str, ...]
    candidate_feature: np.ndarray
    target: float
    evidence_kind: str
    cost: float
    metadata: dict[str, Any]
    similarity: float = 0.0


class ExperienceMemory:
    """Small local SQLite experience store for proof/experiment feedback."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=NORMAL")
        return connection

    def _initialize(self) -> None:
        with self._connect() as db:
            db.execute(
                """
                CREATE TABLE IF NOT EXISTS ai_experience (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at REAL NOT NULL,
                    task_text TEXT NOT NULL,
                    task_dim INTEGER NOT NULL,
                    task_blob BLOB NOT NULL,
                    candidate_ids_json TEXT NOT NULL,
                    feature_dim INTEGER NOT NULL,
                    feature_blob BLOB NOT NULL,
                    target REAL NOT NULL,
                    evidence_kind TEXT NOT NULL,
                    cost REAL NOT NULL,
                    metadata_json TEXT NOT NULL
                )
                """
            )
            db.execute(
                "CREATE INDEX IF NOT EXISTS idx_ai_experience_created ON ai_experience(created_at DESC)"
            )

    @staticmethod
    def _encode_vector(vector: np.ndarray) -> tuple[int, bytes]:
        x = np.asarray(vector, dtype=np.float32)
        if x.ndim != 1 or x.size == 0 or not np.all(np.isfinite(x)):
            raise ValueError("experience vectors must be finite nonempty 1D arrays")
        return int(x.size), x.tobytes(order="C")

    @staticmethod
    def _decode_vector(dim: int, blob: bytes) -> np.ndarray:
        vector = np.frombuffer(blob, dtype=np.float32, count=int(dim)).astype(np.float64)
        if vector.size != int(dim):
            raise ValueError("stored experience vector has invalid byte length")
        return vector

    def add(
        self,
        *,
        task_text: str,
        task_sketch: np.ndarray,
        candidate_ids: tuple[str, ...],
        candidate_feature: np.ndarray,
        target: float,
        evidence_kind: str = "experimental",
        cost: float = 0.0,
        metadata: dict[str, Any] | None = None,
    ) -> int:
        y = float(target)
        runtime_cost = float(cost)
        if not 0.0 <= y <= 1.0:
            raise ValueError("experience target must be in [0,1]")
        if not np.isfinite(runtime_cost) or runtime_cost < 0.0:
            raise ValueError("experience cost must be finite and nonnegative")
        task_dim, task_blob = self._encode_vector(task_sketch)
        feature_dim, feature_blob = self._encode_vector(candidate_feature)
        ids_json = json.dumps(list(candidate_ids), separators=(",", ":"))
        metadata_json = json.dumps(metadata or {}, sort_keys=True, separators=(",", ":"), default=repr)
        now = time.time()
        with self._connect() as db:
            cursor = db.execute(
                """
                INSERT INTO ai_experience (
                    created_at, task_text, task_dim, task_blob,
                    candidate_ids_json, feature_dim, feature_blob,
                    target, evidence_kind, cost, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    now,
                    str(task_text),
                    task_dim,
                    task_blob,
                    ids_json,
                    feature_dim,
                    feature_blob,
                    y,
                    str(evidence_kind),
                    runtime_cost,
                    metadata_json,
                ),
            )
            return int(cursor.lastrowid)

    def recent(self, *, limit: int = 1000) -> list[Experience]:
        if limit <= 0:
            return []
        with self._connect() as db:
            rows = db.execute(
                """
                SELECT id, created_at, task_text, task_dim, task_blob,
                       candidate_ids_json, feature_dim, feature_blob,
                       target, evidence_kind, cost, metadata_json
                FROM ai_experience
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (int(limit),),
            ).fetchall()
        return [self._row_to_experience(row) for row in rows]

    def nearest(
        self,
        task_sketch: np.ndarray,
        *,
        k: int = 8,
        scan_limit: int = 2000,
    ) -> list[Experience]:
        if k <= 0:
            return []
        query = np.asarray(task_sketch, dtype=np.float64)
        scored: list[Experience] = []
        for experience in self.recent(limit=scan_limit):
            if experience.task_sketch.shape != query.shape:
                continue
            similarity = cosine_similarity(query, experience.task_sketch)
            scored.append(
                Experience(
                    **{**experience.__dict__, "similarity": float(similarity)}
                )
            )
        scored.sort(key=lambda item: (-item.similarity, -item.created_at))
        return scored[:k]

    def training_examples(self, *, limit: int = 5000) -> list[tuple[np.ndarray, float, float]]:
        """Return (candidate feature, target, sample weight) triples.

        Formal evidence is intentionally weighted more strongly as historical
        feedback, but it still trains only an advisory ranker.
        """
        weights = {
            "experimental": 1.0,
            "numerical": 1.25,
            "symbolic": 1.6,
            "interval-certified": 1.8,
            "formally-verified": 2.5,
        }
        out: list[tuple[np.ndarray, float, float]] = []
        for experience in self.recent(limit=limit):
            weight = weights.get(experience.evidence_kind, 1.0)
            cost_discount = 1.0 / (1.0 + 0.01 * experience.cost)
            out.append(
                (
                    experience.candidate_feature,
                    experience.target,
                    float(weight * cost_discount),
                )
            )
        return out

    def _row_to_experience(self, row: tuple[Any, ...]) -> Experience:
        (
            experience_id,
            created_at,
            task_text,
            task_dim,
            task_blob,
            candidate_ids_json,
            feature_dim,
            feature_blob,
            target,
            evidence_kind,
            cost,
            metadata_json,
        ) = row
        return Experience(
            experience_id=int(experience_id),
            created_at=float(created_at),
            task_text=str(task_text),
            task_sketch=self._decode_vector(task_dim, task_blob),
            candidate_ids=tuple(json.loads(candidate_ids_json)),
            candidate_feature=self._decode_vector(feature_dim, feature_blob),
            target=float(target),
            evidence_kind=str(evidence_kind),
            cost=float(cost),
            metadata=dict(json.loads(metadata_json)),
        )
