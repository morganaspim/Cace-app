"""Pure policy helpers for bounded, metadata-only OCI inventory.

This module performs no filesystem I/O. The eventual inventory adapter must
apply these checks to each entry and independently use descriptor-relative,
no-follow filesystem operations to avoid TOCTOU and symlink races.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath
import re

MAX_DEPTH = 8
MAX_ENTRIES = 500
MAX_FILE_BYTES = 256 * 1024
MAX_TOTAL_BYTES = 2 * 1024 * 1024

# Conservative component-level deny list. This is defense in depth, not a
# substitute for an explicit allowlist of roots and file types.
_DENIED_COMPONENTS = frozenset({
    ".ssh", ".gnupg", ".aws", ".oci", ".config",
    "secrets", "secret", "credentials", "credential",
    "private", "keys", "keyring", ".kube",
})
_DENIED_NAMES = frozenset({
    ".env", ".env.local", ".env.production", "authorized_keys",
    "known_hosts", "id_rsa", "id_ed25519", "config",
})
_DENIED_SUFFIXES = (".pem", ".key", ".p12", ".pfx", ".jks")
_TOKEN_NAME = re.compile(r"(token|secret|credential|private[-_]?key)", re.I)


@dataclass(frozen=True)
class InventoryLimits:
    max_depth: int = MAX_DEPTH
    max_entries: int = MAX_ENTRIES
    max_file_bytes: int = MAX_FILE_BYTES
    max_total_bytes: int = MAX_TOTAL_BYTES

    def __post_init__(self) -> None:
        for name in ("max_depth", "max_entries", "max_file_bytes", "max_total_bytes"):
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
                raise ValueError(f"{name} must be a positive integer")
        if self.max_depth > MAX_DEPTH:
            raise ValueError(f"max_depth cannot exceed {MAX_DEPTH}")
        if self.max_entries > MAX_ENTRIES:
            raise ValueError(f"max_entries cannot exceed {MAX_ENTRIES}")
        if self.max_file_bytes > MAX_FILE_BYTES:
            raise ValueError(f"max_file_bytes cannot exceed {MAX_FILE_BYTES}")
        if self.max_total_bytes > MAX_TOTAL_BYTES:
            raise ValueError(f"max_total_bytes cannot exceed {MAX_TOTAL_BYTES}")


def validate_relative_path(value: str) -> str:
    """Return a normalized relative POSIX path or reject traversal/absolute paths."""
    if not isinstance(value, str) or not value or "\x00" in value:
        raise ValueError("path must be a non-empty relative path")
    path = PurePosixPath(value)
    if path.is_absolute() or value.startswith("/") or "\\" in value:
        raise ValueError("absolute paths and backslashes are not allowed")
    parts = path.parts
    if not parts or any(part in ("", ".", "..") for part in parts):
        raise ValueError("path traversal and empty components are not allowed")
    normalized = path.as_posix()
    if normalized != value:
        raise ValueError("path must be normalized")
    return normalized


def is_sensitive_relative_path(value: str) -> bool:
    """Conservatively reject common credential and secret-bearing path names."""
    try:
        normalized = validate_relative_path(value)
    except ValueError:
        return True
    parts = PurePosixPath(normalized).parts
    for part in parts:
        lowered = part.lower()
        if lowered in _DENIED_COMPONENTS or lowered in _DENIED_NAMES:
            return True
        if lowered.endswith(_DENIED_SUFFIXES) or _TOKEN_NAME.search(lowered):
            return True
    return False


def validate_inventory_entry(
    relative_path: str,
    *,
    depth: int,
    size_bytes: int,
    is_symlink: bool = False,
    limits: InventoryLimits = InventoryLimits(),
) -> str:
    """Validate one candidate metadata entry; return its normalized path."""
    path = validate_relative_path(relative_path)
    if is_symlink:
        raise PermissionError("symlink entries are excluded")
    if is_sensitive_relative_path(path):
        raise PermissionError("sensitive path is excluded")
    if not isinstance(depth, int) or isinstance(depth, bool) or depth < 1:
        raise ValueError("depth must be a positive integer")
    if depth > limits.max_depth:
        raise ValueError("entry exceeds maximum inventory depth")
    if not isinstance(size_bytes, int) or isinstance(size_bytes, bool) or size_bytes < 0:
        raise ValueError("size_bytes must be a non-negative integer")
    if size_bytes > limits.max_file_bytes:
        raise ValueError("entry exceeds maximum per-file size")
    return path


def validate_page_request(*, limit: int, cursor: str | None = None) -> str | None:
    """Validate bounded pagination input; cursors are opaque server-issued tokens."""
    if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= MAX_ENTRIES:
        raise ValueError(f"limit must be between 1 and {MAX_ENTRIES}")
    if cursor is not None and (
        not isinstance(cursor, str) or not cursor or len(cursor) > 512
    ):
        raise ValueError("cursor must be a non-empty opaque token of at most 512 characters")
    return cursor


def validate_transfer_destination(path: str, *, destination_exists: bool) -> str:
    """Require a new relative destination; never authorize replacement."""
    normalized = validate_relative_path(path)
    if is_sensitive_relative_path(normalized):
        raise PermissionError("sensitive destination path is excluded")
    if destination_exists:
        raise FileExistsError("destination already exists; refusing to overwrite")
    return normalized
