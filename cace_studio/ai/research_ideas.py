from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
from typing import Iterable, Literal
from uuid import uuid4


IdeaStatus = Literal[
    "Idea",
    "Testable",
    "Experimented",
    "Promising",
    "Proof Candidate",
]

IDEA_STATUSES: tuple[IdeaStatus, ...] = (
    "Idea",
    "Testable",
    "Experimented",
    "Promising",
    "Proof Candidate",
)

_SCHEMA_VERSION = 1


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _default_ideas_path() -> Path:
    override = os.environ.get("CACE_RESEARCH_IDEAS_PATH")
    return (
        Path(override).expanduser()
        if override
        else Path.home() / ".cace" / "research_ideas.json"
    )


def _clean_list(values: Iterable[str], *, limit: int = 64) -> tuple[str, ...]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        item = str(value).strip()
        if not item or item in seen:
            continue
        seen.add(item)
        result.append(item[:500])
        if len(result) >= limit:
            break
    return tuple(result)


def _source_key(candidate_id: str, target_ids: Iterable[str]) -> str:
    material = str(candidate_id).strip() + "\x1f" + "\x1f".join(sorted(_clean_list(target_ids)))
    return sha256(material.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ResearchIdea:
    idea_id: str
    title: str
    notes: str
    hypotheses: tuple[str, ...]
    proposed_experiment: str
    associated_modules: tuple[str, ...]
    status: IdeaStatus
    created_utc: str
    updated_utc: str
    source_candidate_id: str = ""
    source_target_ids: tuple[str, ...] = ()
    source_key: str = ""
    source_query_sha256: str = ""

    def to_dict(self) -> dict:
        return {
            "idea_id": self.idea_id,
            "title": self.title,
            "notes": self.notes,
            "hypotheses": list(self.hypotheses),
            "proposed_experiment": self.proposed_experiment,
            "associated_modules": list(self.associated_modules),
            "status": self.status,
            "created_utc": self.created_utc,
            "updated_utc": self.updated_utc,
            "source_candidate_id": self.source_candidate_id,
            "source_target_ids": list(self.source_target_ids),
            "source_key": self.source_key,
            "source_query_sha256": self.source_query_sha256,
        }

    @classmethod
    def from_dict(cls, payload: dict) -> "ResearchIdea":
        status = str(payload.get("status", "Idea"))
        if status not in IDEA_STATUSES:
            status = "Idea"
        idea_id = str(payload.get("idea_id", "")).strip()
        if not idea_id:
            raise ValueError("research idea requires idea_id")
        source_target_ids = _clean_list(payload.get("source_target_ids", ()))
        source_candidate_id = str(payload.get("source_candidate_id", "")).strip()
        source_key = str(payload.get("source_key", "")).strip()
        if source_candidate_id and source_target_ids:
            expected = _source_key(source_candidate_id, source_target_ids)
            if source_key and source_key != expected:
                raise ValueError("research idea source key mismatch")
            source_key = expected
        return cls(
            idea_id=idea_id,
            title=str(payload.get("title", "Untitled Research Idea"))[:500],
            notes=str(payload.get("notes", ""))[:50_000],
            hypotheses=_clean_list(payload.get("hypotheses", ()), limit=128),
            proposed_experiment=str(payload.get("proposed_experiment", ""))[:50_000],
            associated_modules=_clean_list(payload.get("associated_modules", ()), limit=128),
            status=status,  # type: ignore[arg-type]
            created_utc=str(payload.get("created_utc", "")),
            updated_utc=str(payload.get("updated_utc", "")),
            source_candidate_id=source_candidate_id,
            source_target_ids=source_target_ids,
            source_key=source_key,
            source_query_sha256=str(payload.get("source_query_sha256", ""))[:64],
        )


class ResearchIdeaStore:
    """Atomic local research notebook storage.

    Research ideas are planning artifacts, not proof or verification evidence.
    """

    def __init__(
        self,
        path: str | Path | None = None,
        *,
        max_ideas: int = 5000,
    ) -> None:
        self.path = Path(path).expanduser() if path is not None else _default_ideas_path()
        self.max_ideas = max(32, int(max_ideas))
        self.ideas: list[ResearchIdea] = []
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
        raw = payload.get("ideas", [])
        if not isinstance(raw, list):
            return
        loaded: list[ResearchIdea] = []
        for item in raw[-self.max_ideas :]:
            if not isinstance(item, dict):
                continue
            try:
                loaded.append(ResearchIdea.from_dict(item))
            except ValueError:
                continue
        self.ideas = loaded

    def _write(self) -> Path:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": _SCHEMA_VERSION,
            "role": "local research notebook; never verification evidence",
            "ideas": [idea.to_dict() for idea in self.ideas[-self.max_ideas :]],
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

    def list(self, *, status: str | None = None) -> tuple[ResearchIdea, ...]:
        values = self.ideas
        if status and status in IDEA_STATUSES:
            values = [idea for idea in values if idea.status == status]
        return tuple(sorted(values, key=lambda idea: (idea.updated_utc, idea.idea_id), reverse=True))

    def get(self, idea_id: str) -> ResearchIdea | None:
        return next((idea for idea in self.ideas if idea.idea_id == idea_id), None)

    def find_by_source(
        self,
        candidate_id: str,
        target_ids: Iterable[str],
    ) -> ResearchIdea | None:
        key = _source_key(candidate_id, target_ids)
        matches = [idea for idea in self.ideas if idea.source_key == key]
        if not matches:
            return None
        return max(matches, key=lambda idea: (idea.updated_utc, idea.idea_id))

    def create(
        self,
        *,
        title: str,
        notes: str = "",
        hypotheses: Iterable[str] = (),
        proposed_experiment: str = "",
        associated_modules: Iterable[str] = (),
        status: IdeaStatus = "Idea",
        source_candidate_id: str = "",
        source_target_ids: Iterable[str] = (),
        source_query: str = "",
    ) -> ResearchIdea:
        if status not in IDEA_STATUSES:
            raise ValueError(f"invalid research idea status: {status!r}")
        now = _utc_now()
        target_ids = _clean_list(source_target_ids)
        source_candidate_id = str(source_candidate_id).strip()
        source_key = (
            _source_key(source_candidate_id, target_ids)
            if source_candidate_id and target_ids
            else ""
        )
        idea = ResearchIdea(
            idea_id=uuid4().hex,
            title=str(title).strip()[:500] or "Untitled Research Idea",
            notes=str(notes)[:50_000],
            hypotheses=_clean_list(hypotheses, limit=128),
            proposed_experiment=str(proposed_experiment)[:50_000],
            associated_modules=_clean_list(associated_modules, limit=128),
            status=status,
            created_utc=now,
            updated_utc=now,
            source_candidate_id=source_candidate_id,
            source_target_ids=target_ids,
            source_key=source_key,
            source_query_sha256=sha256(str(source_query).encode("utf-8")).hexdigest()
            if source_query
            else "",
        )
        self.ideas.append(idea)
        if len(self.ideas) > self.max_ideas:
            self.ideas = self.ideas[-self.max_ideas :]
        self._write()
        return idea

    def create_or_get_from_grow(
        self,
        *,
        candidate_id: str,
        target_ids: Iterable[str],
        title: str,
        notes: str,
        hypotheses: Iterable[str],
        proposed_experiment: str,
        associated_modules: Iterable[str],
        source_query: str = "",
    ) -> tuple[ResearchIdea, bool]:
        existing = self.find_by_source(candidate_id, target_ids)
        if existing is not None:
            return existing, False
        return (
            self.create(
                title=title,
                notes=notes,
                hypotheses=hypotheses,
                proposed_experiment=proposed_experiment,
                associated_modules=associated_modules,
                status="Idea",
                source_candidate_id=candidate_id,
                source_target_ids=target_ids,
                source_query=source_query,
            ),
            True,
        )

    def update(self, idea_id: str, **changes) -> ResearchIdea:
        index = next((i for i, idea in enumerate(self.ideas) if idea.idea_id == idea_id), None)
        if index is None:
            raise KeyError(f"unknown research idea: {idea_id}")
        current = self.ideas[index]
        allowed = {
            "title",
            "notes",
            "hypotheses",
            "proposed_experiment",
            "associated_modules",
            "status",
        }
        unknown = set(changes) - allowed
        if unknown:
            raise ValueError(f"unsupported research idea fields: {sorted(unknown)}")
        status = changes.get("status", current.status)
        if status not in IDEA_STATUSES:
            raise ValueError(f"invalid research idea status: {status!r}")
        updated = replace(
            current,
            title=str(changes.get("title", current.title)).strip()[:500] or "Untitled Research Idea",
            notes=str(changes.get("notes", current.notes))[:50_000],
            hypotheses=_clean_list(changes.get("hypotheses", current.hypotheses), limit=128),
            proposed_experiment=str(
                changes.get("proposed_experiment", current.proposed_experiment)
            )[:50_000],
            associated_modules=_clean_list(
                changes.get("associated_modules", current.associated_modules),
                limit=128,
            ),
            status=status,
            updated_utc=_utc_now(),
        )
        self.ideas[index] = updated
        self._write()
        return updated

    def delete(self, idea_id: str) -> bool:
        before = len(self.ideas)
        self.ideas = [idea for idea in self.ideas if idea.idea_id != idea_id]
        if len(self.ideas) == before:
            return False
        self._write()
        return True
