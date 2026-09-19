from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
from typing import Iterable, Literal


FeedbackKind = Literal["keep", "useful", "reject"]
TargetKind = Literal["group", "fragment"]
_VALID_FEEDBACK = {"keep", "useful", "reject"}
_VALID_TARGETS = {"group", "fragment"}
_SCHEMA_VERSION = 1


def _default_memory_path() -> Path:
    override = os.environ.get("CACE_AI_GROWTH_MEMORY_PATH")
    return (
        Path(override).expanduser()
        if override
        else Path.home() / ".cace" / "ai_growth_memory.json"
    )


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _canonical_ids(ids: Iterable[str]) -> tuple[str, ...]:
    normalized = tuple(sorted({str(item).strip() for item in ids if str(item).strip()}))
    if not normalized:
        raise ValueError("persistent Grow feedback requires at least one target id")
    return normalized


def _target_key(kind: str, target_ids: Iterable[str]) -> str:
    ids = _canonical_ids(target_ids)
    material = kind + "\x1f" + "\x1f".join(ids)
    return sha256(material.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class GrowthFeedbackEvent:
    event_id: str
    timestamp_utc: str
    feedback: FeedbackKind
    target_kind: TargetKind
    target_ids: tuple[str, ...]
    target_key: str
    query_sha256: str
    note: str = ""

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "timestamp_utc": self.timestamp_utc,
            "feedback": self.feedback,
            "target_kind": self.target_kind,
            "target_ids": list(self.target_ids),
            "target_key": self.target_key,
            "query_sha256": self.query_sha256,
            "note": self.note,
        }

    @classmethod
    def from_dict(cls, payload: dict) -> "GrowthFeedbackEvent":
        feedback = str(payload.get("feedback", ""))
        target_kind = str(payload.get("target_kind", ""))
        if feedback not in _VALID_FEEDBACK:
            raise ValueError(f"invalid Grow feedback: {feedback!r}")
        if target_kind not in _VALID_TARGETS:
            raise ValueError(f"invalid Grow target kind: {target_kind!r}")
        target_ids = _canonical_ids(payload.get("target_ids", ()))
        expected_key = _target_key(target_kind, target_ids)
        target_key = str(payload.get("target_key", ""))
        if target_key != expected_key:
            raise ValueError("Grow memory target key does not match target ids")
        event_id = str(payload.get("event_id", ""))
        if len(event_id) != 64:
            raise ValueError("Grow memory event_id must be SHA-256 hex")
        query_sha256 = str(payload.get("query_sha256", ""))
        if len(query_sha256) != 64:
            raise ValueError("Grow memory query_sha256 must be SHA-256 hex")
        return cls(
            event_id=event_id,
            timestamp_utc=str(payload.get("timestamp_utc", "")),
            feedback=feedback,  # type: ignore[arg-type]
            target_kind=target_kind,  # type: ignore[arg-type]
            target_ids=target_ids,
            target_key=target_key,
            query_sha256=query_sha256,
            note=str(payload.get("note", ""))[:500],
        )


class PersistentGrowthMemory:
    """Atomic, local, user-supervised feedback memory for Grow.

    This store is outside CACE verification/proof state. It records explicit
    user feedback only; AI output never writes itself here automatically.
    """

    def __init__(
        self,
        path: str | Path | None = None,
        *,
        max_events: int = 10_000,
    ) -> None:
        self.path = Path(path).expanduser() if path is not None else _default_memory_path()
        self.max_events = max(32, int(max_events))
        self.events: list[GrowthFeedbackEvent] = []
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        if not isinstance(payload, dict) or payload.get("schema_version") != _SCHEMA_VERSION:
            return
        raw_events = payload.get("events", [])
        if not isinstance(raw_events, list):
            return
        loaded: list[GrowthFeedbackEvent] = []
        for item in raw_events[-self.max_events :]:
            if not isinstance(item, dict):
                continue
            try:
                loaded.append(GrowthFeedbackEvent.from_dict(item))
            except ValueError:
                continue
        self.events = loaded

    def _write(self) -> Path:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": _SCHEMA_VERSION,
            "role": "user-supervised AI research preference memory; never verification evidence",
            "events": [event.to_dict() for event in self.events[-self.max_events :]],
        }
        temp = self.path.with_name(self.path.name + ".tmp")
        temp.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        temp.replace(self.path)
        try:
            self.path.chmod(0o600)
        except OSError:
            pass
        return self.path

    def record(
        self,
        feedback: FeedbackKind,
        target_kind: TargetKind,
        target_ids: Iterable[str],
        *,
        query: str = "",
        note: str = "",
    ) -> GrowthFeedbackEvent:
        if feedback not in _VALID_FEEDBACK:
            raise ValueError(f"invalid Grow feedback: {feedback!r}")
        if target_kind not in _VALID_TARGETS:
            raise ValueError(f"invalid Grow target kind: {target_kind!r}")
        ids = _canonical_ids(target_ids)
        timestamp = _utc_now()
        query_sha = sha256(str(query).encode("utf-8")).hexdigest()
        key = _target_key(target_kind, ids)
        material = "\x1f".join(
            (timestamp, feedback, target_kind, key, query_sha, str(note)[:500])
        )
        event = GrowthFeedbackEvent(
            event_id=sha256(material.encode("utf-8")).hexdigest(),
            timestamp_utc=timestamp,
            feedback=feedback,
            target_kind=target_kind,
            target_ids=ids,
            target_key=key,
            query_sha256=query_sha,
            note=str(note)[:500],
        )
        self.events.append(event)
        if len(self.events) > self.max_events:
            self.events = self.events[-self.max_events :]
        self._write()
        return event

    @staticmethod
    def _bounded(raw: float, lower: float, upper: float) -> float:
        return min(upper, max(lower, raw))

    def group_bias(self, target_ids: Iterable[str]) -> float:
        key = _target_key("group", target_ids)
        raw = 0.0
        for event in self.events:
            if event.target_kind != "group" or event.target_key != key:
                continue
            if event.feedback == "keep":
                raw += 0.08
            elif event.feedback == "useful":
                raw += 0.18
            else:
                raw -= 0.28
        return self._bounded(raw, -0.60, 0.40)

    def fragment_bias(self, fragment_id: str) -> float:
        fragment_id = str(fragment_id).strip()
        if not fragment_id:
            return 0.0
        direct_key = _target_key("fragment", (fragment_id,))
        raw = 0.0
        for event in self.events:
            if event.target_kind == "fragment" and event.target_key == direct_key:
                if event.feedback == "keep":
                    raw += 0.05
                elif event.feedback == "useful":
                    raw += 0.12
                else:
                    raw -= 0.20
            elif event.target_kind == "group" and fragment_id in event.target_ids:
                # Group feedback propagates only weakly to individual fragments.
                if event.feedback == "keep":
                    raw += 0.015
                elif event.feedback == "useful":
                    raw += 0.035
                else:
                    raw -= 0.05
        return self._bounded(raw, -0.35, 0.25)

    def summary(self) -> dict[str, int]:
        result = {"keep": 0, "useful": 0, "reject": 0, "total": len(self.events)}
        for event in self.events:
            result[event.feedback] += 1
        return result

    def clear(self) -> None:
        self.events.clear()
        self._write()
