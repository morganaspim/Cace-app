from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from hashlib import sha256
from importlib.resources import files
import json
from pathlib import Path
import re
from typing import Any, Iterable, Mapping
from urllib.parse import urlsplit


CATALOG_SCHEMA = "cace.open-problem-catalog.v1"
ALLOWED_PROBLEM_STATUSES = frozenset(
    {"open", "solved", "partially-resolved", "unknown"}
)
_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{1,127}$")


def _canonical_id(value: str, *, field: str) -> str:
    text = str(value)
    if not _ID_RE.fullmatch(text):
        raise ValueError(f"{field} must match {_ID_RE.pattern}")
    return text


def _bounded_text(value: Any, *, field: str, maximum: int, required: bool = True) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field} must be a string")
    text = value.strip()
    if required and not text:
        raise ValueError(f"{field} must be non-empty")
    if len(text) > maximum:
        raise ValueError(f"{field} exceeds {maximum} characters")
    if any(ord(char) < 32 and char not in "\n\t" for char in text):
        raise ValueError(f"{field} contains control characters")
    return text


def _iso_date(value: Any, *, field: str) -> str:
    text = _bounded_text(value, field=field, maximum=32)
    try:
        date.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"{field} must be an ISO date YYYY-MM-DD") from exc
    return text


def _source_url(value: Any) -> str:
    text = _bounded_text(value, field="source_url", maximum=2048)
    parsed = urlsplit(text)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("source_url must be an absolute http(s) URL")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("source_url must not contain credentials")
    return text


def _tags(value: Any) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        raise TypeError("tags must be a list/tuple")
    result: list[str] = []
    seen: set[str] = set()
    for raw in value:
        tag = _bounded_text(raw, field="tag", maximum=64).casefold().replace(" ", "-")
        if tag in seen:
            continue
        seen.add(tag)
        result.append(tag)
    if len(result) > 32:
        raise ValueError("at most 32 tags are allowed")
    return tuple(result)


@dataclass(frozen=True)
class OpenProblem:
    problem_id: str
    title: str
    domain: str
    status: str
    collection: str
    summary: str
    authority: str
    source_url: str
    last_verified: str
    tags: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "problem_id", _canonical_id(self.problem_id, field="problem_id"))
        object.__setattr__(self, "title", _bounded_text(self.title, field="title", maximum=300))
        object.__setattr__(self, "domain", _bounded_text(self.domain, field="domain", maximum=200))
        status = _bounded_text(self.status, field="status", maximum=32).casefold()
        if status not in ALLOWED_PROBLEM_STATUSES:
            raise ValueError(f"unsupported open-problem status: {status}")
        object.__setattr__(self, "status", status)
        object.__setattr__(
            self, "collection", _bounded_text(self.collection, field="collection", maximum=200)
        )
        object.__setattr__(self, "summary", _bounded_text(self.summary, field="summary", maximum=4000))
        object.__setattr__(
            self, "authority", _bounded_text(self.authority, field="authority", maximum=300)
        )
        object.__setattr__(self, "source_url", _source_url(self.source_url))
        object.__setattr__(
            self, "last_verified", _iso_date(self.last_verified, field="last_verified")
        )
        object.__setattr__(self, "tags", _tags(self.tags))

    @property
    def is_open(self) -> bool:
        return self.status == "open"

    @property
    def semantic_sha256(self) -> str:
        payload = json.dumps(
            self.to_dict(include_hash=False),
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return sha256(payload).hexdigest()

    def to_dict(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload = asdict(self)
        payload["tags"] = list(self.tags)
        if include_hash:
            payload["semantic_sha256"] = self.semantic_sha256
        return payload

    def to_module_params(self) -> dict[str, str]:
        return {
            "problem_id": self.problem_id,
            "title": self.title,
            "domain": self.domain,
            "status": self.status,
            "collection": self.collection,
            "summary": self.summary,
            "authority": self.authority,
            "source_url": self.source_url,
            "last_verified": self.last_verified,
            "tags_json": json.dumps(list(self.tags), separators=(",", ":")),
        }

    def play_context(self) -> str:
        status_note = (
            "This entry is marked OPEN by its cited authority snapshot. "
            "Exploration does not mean it has been solved."
            if self.status == "open"
            else (
                "This entry is SOLVED and is available as a methodological/historical example."
                if self.status == "solved"
                else "Status is not a simple open/solved claim; preserve the source wording."
            )
        )
        return "\n".join(
            [
                "CACE OPEN PROBLEM PLAY CARD",
                "Research navigation only; never verification evidence.",
                f"ID: {self.problem_id}",
                f"Title: {self.title}",
                f"Domain: {self.domain}",
                f"Status: {self.status}",
                f"Collection: {self.collection}",
                f"Authority: {self.authority}",
                f"Last status verification: {self.last_verified}",
                f"Source: {self.source_url}",
                f"Summary: {self.summary}",
                f"Tags: {', '.join(self.tags) or 'none'}",
                status_note,
                "",
                "Analyze by decomposing the problem into assumptions, invariants, subproblems, "
                "candidate mathematical operations, computational experiments, falsification or "
                "counterexample searches, and explicit formal proof obligations. Distinguish "
                "heuristic/numerical evidence from proof. Do not claim a famous open problem is "
                "solved without the required independent mathematical qualification.",
            ]
        )

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> "OpenProblem":
        allowed = {
            "problem_id",
            "title",
            "domain",
            "status",
            "collection",
            "summary",
            "authority",
            "source_url",
            "last_verified",
            "tags",
        }
        unknown = set(raw) - allowed
        if unknown:
            raise ValueError(f"unsupported open-problem fields: {sorted(unknown)}")
        required = allowed - {"tags"}
        missing = [name for name in sorted(required) if name not in raw]
        if missing:
            raise ValueError(f"missing open-problem fields: {missing}")
        return cls(
            problem_id=raw["problem_id"],
            title=raw["title"],
            domain=raw["domain"],
            status=raw["status"],
            collection=raw["collection"],
            summary=raw["summary"],
            authority=raw["authority"],
            source_url=raw["source_url"],
            last_verified=raw["last_verified"],
            tags=tuple(raw.get("tags", ())),
        )


@dataclass(frozen=True)
class OpenProblemCatalog:
    catalog_id: str
    title: str
    authority: str
    last_verified: str
    problems: tuple[OpenProblem, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "catalog_id", _canonical_id(self.catalog_id, field="catalog_id"))
        object.__setattr__(self, "title", _bounded_text(self.title, field="catalog title", maximum=300))
        object.__setattr__(
            self, "authority", _bounded_text(self.authority, field="catalog authority", maximum=300)
        )
        object.__setattr__(
            self, "last_verified", _iso_date(self.last_verified, field="catalog last_verified")
        )
        if not isinstance(self.problems, tuple) or not self.problems:
            raise ValueError("open-problem catalog must contain at least one problem")
        ids = [problem.problem_id for problem in self.problems]
        if len(ids) != len(set(ids)):
            raise ValueError("open-problem catalog contains duplicate problem_id values")

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> "OpenProblemCatalog":
        allowed = {
            "schema",
            "catalog_id",
            "title",
            "authority",
            "last_verified",
            "problems",
        }
        unknown = set(raw) - allowed
        if unknown:
            raise ValueError(f"unsupported catalog fields: {sorted(unknown)}")
        if raw.get("schema") != CATALOG_SCHEMA:
            raise ValueError(f"catalog schema must be {CATALOG_SCHEMA!r}")
        problems_raw = raw.get("problems")
        if not isinstance(problems_raw, list):
            raise TypeError("catalog problems must be a list")
        return cls(
            catalog_id=raw.get("catalog_id", ""),
            title=raw.get("title", ""),
            authority=raw.get("authority", ""),
            last_verified=raw.get("last_verified", ""),
            problems=tuple(OpenProblem.from_mapping(item) for item in problems_raw),
        )

    @classmethod
    def from_json(cls, text: str) -> "OpenProblemCatalog":
        if not isinstance(text, str):
            raise TypeError("catalog JSON must be text")
        if len(text.encode("utf-8")) > 2_000_000:
            raise ValueError("catalog exceeds 2 MB safety limit")
        try:
            raw = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError("invalid open-problem catalog JSON") from exc
        if not isinstance(raw, dict):
            raise TypeError("catalog root must be an object")
        return cls.from_mapping(raw)

    @classmethod
    def load_path(cls, path: str | Path) -> "OpenProblemCatalog":
        target = Path(path).expanduser()
        if target.stat().st_size > 2_000_000:
            raise ValueError("catalog exceeds 2 MB safety limit")
        return cls.from_json(target.read_text(encoding="utf-8"))

    def filtered(
        self,
        *,
        query: str = "",
        domain: str = "",
        status: str = "",
    ) -> tuple[OpenProblem, ...]:
        needle = query.strip().casefold()
        domain_key = domain.strip().casefold()
        status_key = status.strip().casefold()
        result = []
        for problem in self.problems:
            if status_key and status_key != "all" and problem.status != status_key:
                continue
            if domain_key and domain_key != "all" and problem.domain.casefold() != domain_key:
                continue
            if needle:
                haystack = " ".join(
                    (
                        problem.problem_id,
                        problem.title,
                        problem.domain,
                        problem.collection,
                        problem.summary,
                        " ".join(problem.tags),
                    )
                ).casefold()
                if needle not in haystack:
                    continue
            result.append(problem)
        return tuple(result)

    def by_id(self, problem_id: str) -> OpenProblem:
        for problem in self.problems:
            if problem.problem_id == problem_id:
                return problem
        raise KeyError(problem_id)


def default_open_problem_catalog() -> OpenProblemCatalog:
    resource = files("cace_studio").joinpath("data/open_problems_millennium.json")
    return OpenProblemCatalog.from_json(resource.read_text(encoding="utf-8"))


def merge_catalogs(catalogs: Iterable[OpenProblemCatalog]) -> tuple[OpenProblem, ...]:
    merged: dict[str, OpenProblem] = {}
    for catalog in catalogs:
        for problem in catalog.problems:
            existing = merged.get(problem.problem_id)
            if existing is not None and existing.semantic_sha256 != problem.semantic_sha256:
                raise ValueError(
                    f"conflicting open-problem definitions for {problem.problem_id}"
                )
            merged[problem.problem_id] = problem
    return tuple(merged[key] for key in sorted(merged))
