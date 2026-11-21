"""Typed immutable reference to one exact Merlin artifact version."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any, Mapping


@dataclass(frozen=True)
class ArtifactRef:
    """Stable identity across registry, orchestration, execution and verification."""

    project_id: str
    logical_path: str
    version: int
    sha256: str

    SCHEMA = "merlin-artifact-ref/1"
    FIELDS = frozenset({"schema", "project_id", "logical_path", "version", "sha256"})

    def __post_init__(self) -> None:
        if not isinstance(self.project_id, str) or not self.project_id.strip() or len(self.project_id) > 256:
            raise ValueError("project_id must be a non-empty string of at most 256 characters")
        if not isinstance(self.logical_path, str) or not self.logical_path or len(self.logical_path) > 1024:
            raise ValueError("logical_path must be a non-empty string of at most 1024 characters")
        path = PurePosixPath(self.logical_path)
        if (path.is_absolute() or "\\" in self.logical_path or "\x00" in self.logical_path
                or any(part in {"", ".", ".."} for part in self.logical_path.split("/"))):
            raise ValueError("logical_path must be normalized, relative and traversal-free")
        if isinstance(self.version, bool) or not isinstance(self.version, int) or self.version < 1:
            raise ValueError("version must be a positive integer")
        if (not isinstance(self.sha256, str) or len(self.sha256) != 64
                or any(char not in "0123456789abcdef" for char in self.sha256)):
            raise ValueError("sha256 must be a lowercase 64-character digest")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.SCHEMA,
            "project_id": self.project_id,
            "logical_path": self.logical_path,
            "version": self.version,
            "sha256": self.sha256,
        }

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "ArtifactRef":
        if not isinstance(value, Mapping) or set(value) != cls.FIELDS:
            raise ValueError("artifact reference must contain exactly the declared v1 fields")
        if value.get("schema") != cls.SCHEMA:
            raise ValueError("unsupported artifact reference schema")
        return cls(
            project_id=value["project_id"],
            logical_path=value["logical_path"],
            version=value["version"],
            sha256=value["sha256"],
        )
