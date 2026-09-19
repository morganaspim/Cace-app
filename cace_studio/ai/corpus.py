from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from typing import Iterable

from .hybrid import ResearchFragment, SparseResearchIndex


_TEXT_SUFFIXES = {".py", ".lean", ".md", ".json"}
_DEFAULT_FILES = (
    "AI_REPO_MAP.json",
    "AGENTS.md",
    "docs/ARCHITECTURE.md",
    "docs/CONSTITUTION.md",
    "docs/CLAIMS.md",
    "docs/STATUS.md",
    "docs/ROADMAP.md",
    "cace_studio/data/claim_registry.json",
    "cace_studio/data/proof_ledger.json",
)
_DEFAULT_DIRS = (
    "formal/cace_formal/CACEFormal",
    "cace_studio/ai",
    "cace_studio/core",
)
_MODULE_GLOBS = (
    "cace_studio/modules/research_*.py",
    "cace_studio/modules/formal_hypothesis_bridges.py",
    "cace_studio/modules/formal_v32*.py",
)


def repository_root(start: str | Path | None = None) -> Path:
    """Find a local CACE checkout without consulting the network."""
    path = Path(start).resolve() if start is not None else Path(__file__).resolve()
    if path.is_file():
        path = path.parent
    for candidate in (path, *path.parents):
        if (candidate / "cace_studio").is_dir() and (candidate / "pyproject.toml").is_file():
            return candidate
    # Installed-wheel fallback: the package parent is still a safe local root.
    return Path(__file__).resolve().parents[2]


def _safe_read(root: Path, path: Path, *, max_file_bytes: int) -> str | None:
    try:
        resolved = path.resolve()
        resolved.relative_to(root.resolve())
    except (OSError, ValueError):
        return None
    if not resolved.is_file() or resolved.suffix.lower() not in _TEXT_SUFFIXES:
        return None
    try:
        size = resolved.stat().st_size
    except OSError:
        return None
    if size <= 0 or size > max_file_bytes:
        return None
    try:
        return resolved.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def _kind_for(path: str) -> str:
    if path.endswith(".lean") or path.startswith("formal/"):
        return "formal-source"
    if path.startswith("docs/"):
        return "documentation"
    if "claim_registry" in path or "proof_ledger" in path:
        return "proof-metadata"
    if "/modules/" in path:
        return "research-module"
    if "/core/" in path:
        return "runtime-core"
    if "/ai/" in path:
        return "ai-code"
    return "project-map"


def _evidence_note(kind: str) -> str:
    if kind == "formal-source":
        return "Lean source only; current formal status still requires exact-head qualification."
    if kind == "proof-metadata":
        return "Canonical metadata may describe status, but AI retrieval itself never establishes PASS."
    return "Local navigation/research context only; not verification evidence."


def _chunks(text: str, *, chunk_chars: int, overlap_chars: int) -> Iterable[tuple[int, str]]:
    compact = text.replace("\x00", "")
    if len(compact) <= chunk_chars:
        yield 0, compact
        return
    step = max(1, chunk_chars - overlap_chars)
    for offset in range(0, len(compact), step):
        chunk = compact[offset : offset + chunk_chars]
        if chunk.strip():
            yield offset, chunk
        if offset + chunk_chars >= len(compact):
            break


def build_local_fragments(
    root: str | Path | None = None,
    *,
    max_file_bytes: int = 384_000,
    max_total_bytes: int = 5_000_000,
    chunk_chars: int = 1_400,
    overlap_chars: int = 160,
) -> tuple[ResearchFragment, ...]:
    """Build a deterministic, bounded, read-only local research corpus."""
    repo = repository_root(root)
    paths: set[Path] = set()

    for relative in _DEFAULT_FILES:
        path = repo / relative
        if path.is_file():
            paths.add(path)

    for relative in _DEFAULT_DIRS:
        base = repo / relative
        if base.is_dir():
            for path in base.rglob("*"):
                if path.is_file() and path.suffix.lower() in _TEXT_SUFFIXES:
                    paths.add(path)

    for pattern in _MODULE_GLOBS:
        paths.update(path for path in repo.glob(pattern) if path.is_file())

    fragments: list[ResearchFragment] = []
    total = 0
    for path in sorted(paths, key=lambda item: item.as_posix()):
        text = _safe_read(repo, path, max_file_bytes=max_file_bytes)
        if text is None:
            continue
        encoded_size = len(text.encode("utf-8"))
        if total + encoded_size > max_total_bytes:
            continue
        total += encoded_size
        relative = path.resolve().relative_to(repo.resolve()).as_posix()
        kind = _kind_for(relative)
        digest = sha256(text.encode("utf-8")).hexdigest()[:12]
        for offset, chunk in _chunks(
            text, chunk_chars=chunk_chars, overlap_chars=overlap_chars
        ):
            fragments.append(
                ResearchFragment(
                    fragment_id=f"{relative}:{digest}:{offset}",
                    source=relative,
                    kind=kind,
                    text=chunk,
                    evidence_note=_evidence_note(kind),
                )
            )
    return tuple(fragments)


def build_local_index(
    root: str | Path | None = None,
    **fragment_options,
) -> SparseResearchIndex:
    return SparseResearchIndex(build_local_fragments(root, **fragment_options))
