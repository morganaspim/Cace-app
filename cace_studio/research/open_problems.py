from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any, Iterable, Mapping
from urllib.parse import urlsplit


OPEN_PROBLEM_STATUSES = (
    "open",
    "active-review",
    "solved",
    "partially-resolved",
    "unknown",
)


def _canonical(value: str, name: str, *, limit: int = 4000) -> str:
    text = str(value).strip()
    if not text:
        raise ValueError(f"{name} is required")
    if len(text) > limit:
        raise ValueError(f"{name} exceeds size limit")
    if any(ord(char) < 32 and char not in "\n\t" for char in text):
        raise ValueError(f"{name} contains control characters")
    return text


def _https_url(value: str) -> str:
    text = _canonical(value, "source URL", limit=2000)
    parsed = urlsplit(text)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError("open-problem source URLs must be absolute https URLs")
    return text


@dataclass(frozen=True)
class OpenProblem:
    problem_id: str
    title: str
    domain: str
    status: str
    collection: str
    authority: str
    summary: str
    source_urls: tuple[str, ...]
    last_verified: str
    tags: tuple[str, ...] = ()
    status_note: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "problem_id", _canonical(self.problem_id, "problem_id", limit=128))
        object.__setattr__(self, "title", _canonical(self.title, "title", limit=500))
        object.__setattr__(self, "domain", _canonical(self.domain, "domain", limit=120))
        object.__setattr__(self, "collection", _canonical(self.collection, "collection", limit=240))
        object.__setattr__(self, "authority", _canonical(self.authority, "authority", limit=240))
        object.__setattr__(self, "summary", _canonical(self.summary, "summary", limit=6000))
        if self.status not in OPEN_PROBLEM_STATUSES:
            raise ValueError(f"unsupported open-problem status: {self.status}")
        if not self.source_urls:
            raise ValueError("at least one authoritative source URL is required")
        object.__setattr__(self, "source_urls", tuple(_https_url(url) for url in self.source_urls))
        if len(self.tags) > 64:
            raise ValueError("too many tags")
        object.__setattr__(self, "tags", tuple(_canonical(tag, "tag", limit=80) for tag in self.tags))
        if len(self.last_verified) != 10 or self.last_verified[4] != "-" or self.last_verified[7] != "-":
            raise ValueError("last_verified must use YYYY-MM-DD")
        if len(self.status_note) > 4000:
            raise ValueError("status_note exceeds size limit")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_module_params(self) -> dict[str, Any]:
        return {
            "problem_id": self.problem_id,
            "title": self.title,
            "domain": self.domain,
            "status": self.status,
            "collection": self.collection,
            "authority": self.authority,
            "summary": self.summary,
            "source_url": self.source_urls[0],
            "last_verified": self.last_verified,
            "tags": ", ".join(self.tags),
            "status_note": self.status_note,
        }

    def ai_context(self) -> str:
        return "\n".join(
            [
                "CACE OPEN PROBLEM PLAY CONTEXT",
                "Research navigation only; never proof that the problem is solved.",
                f"Title: {self.title}",
                f"Domain: {self.domain}",
                f"Status: {self.status}",
                f"Authority/collection: {self.authority} / {self.collection}",
                f"Last verified: {self.last_verified}",
                f"Summary: {self.summary}",
                f"Status note: {self.status_note or 'none'}",
                "Sources:",
                *(f"- {url}" for url in self.source_urls),
                "Suggest decompositions, invariants, counterexamples, computational experiments, and formal obligations. "
                "Keep conjecture, numerical evidence, and proof strictly separate.",
            ]
        )

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> "OpenProblem":
        urls = raw.get("source_urls")
        if not isinstance(urls, (list, tuple)):
            single = raw.get("source_url")
            urls = [single] if single else []
        tags = raw.get("tags", ())
        if isinstance(tags, str):
            tags = [item.strip() for item in tags.split(",") if item.strip()]
        return cls(
            problem_id=str(raw.get("problem_id", "")),
            title=str(raw.get("title", "")),
            domain=str(raw.get("domain", "")),
            status=str(raw.get("status", "unknown")),
            collection=str(raw.get("collection", "")),
            authority=str(raw.get("authority", "")),
            summary=str(raw.get("summary", "")),
            source_urls=tuple(str(value) for value in urls),
            last_verified=str(raw.get("last_verified", "")),
            tags=tuple(str(value) for value in tags),
            status_note=str(raw.get("status_note", "")),
        )


class OpenProblemCatalog:
    def __init__(self, entries: Iterable[OpenProblem], *, catalog_id: str = "custom") -> None:
        self.catalog_id = _canonical(catalog_id, "catalog_id", limit=128)
        values = tuple(entries)
        ids = [entry.problem_id for entry in values]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate open-problem IDs")
        self.entries = values
        self._by_id = {entry.problem_id: entry for entry in values}

    def get(self, problem_id: str) -> OpenProblem | None:
        return self._by_id.get(problem_id)

    def search(self, text: str = "", *, status: str | None = None) -> tuple[OpenProblem, ...]:
        needle = str(text).strip().casefold()
        result = []
        for entry in self.entries:
            if status and entry.status != status:
                continue
            haystack = " ".join(
                (entry.title, entry.domain, entry.collection, entry.summary, " ".join(entry.tags))
            ).casefold()
            if needle and needle not in haystack:
                continue
            result.append(entry)
        result.sort(key=lambda item: (item.domain, item.title, item.problem_id))
        return tuple(result)

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "OpenProblemCatalog":
        if payload.get("schema") != "cace.open-problem-catalog.v1":
            raise ValueError("unsupported open-problem catalog schema")
        raw_entries = payload.get("entries")
        if not isinstance(raw_entries, list):
            raise ValueError("catalog entries must be a list")
        if len(raw_entries) > 5000:
            raise ValueError("catalog exceeds maximum entry count")
        entries = [OpenProblem.from_mapping(item) for item in raw_entries]
        return cls(entries, catalog_id=str(payload.get("catalog_id", "custom")))

    @classmethod
    def from_json_text(cls, text: str) -> "OpenProblemCatalog":
        raw = json.loads(text)
        if not isinstance(raw, Mapping):
            raise ValueError("catalog JSON root must be an object")
        return cls.from_payload(raw)


def load_millennium_catalog() -> OpenProblemCatalog:
    path = Path(__file__).resolve().parents[1] / "data" / "open_problems_millennium.json"
    return OpenProblemCatalog.from_json_text(path.read_text(encoding="utf-8"))
