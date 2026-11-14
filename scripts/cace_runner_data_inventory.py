#!/usr/bin/env python3
"""Read-only inventory of known CACE OCI runner data locations.

This script never reads file contents, follows symlinks, uploads, moves, or deletes.
It emits aggregate sizes and bounded lists of largest/recent files for migration planning.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import stat
from typing import Any

SENSITIVE_NAME_FRAGMENTS = (
    ".oci", ".ssh", ".aws", ".azure", ".config", ".env",
    "credential", "secret", "token", "private", "id_rsa",
    "id_ed25519", "authorized_keys", "known_hosts",
)
DEFAULT_MAX_ENTRIES = 250_000
TOP_FILES = 100


def _is_sensitive_path(path: Path) -> bool:
    return any(
        fragment in part.lower()
        for part in path.parts
        for fragment in SENSITIVE_NAME_FRAGMENTS
    )


def inventory_root(root: Path, max_entries: int = DEFAULT_MAX_ENTRIES) -> dict[str, Any]:
    """Summarize regular files without following symlinks or reading contents."""
    root = root.absolute()
    result: dict[str, Any] = {
        "path": str(root),
        "exists": root.exists(),
        "file_count": 0,
        "directory_count": 0,
        "symlink_count": 0,
        "total_bytes": 0,
        "truncated": False,
        "top_level": {},
        "largest_files": [],
        "newest_files": [],
        "warnings": [],
    }
    if not root.exists():
        return result
    if root.is_symlink() or not root.is_dir():
        result["warnings"].append("root is not a real directory; not traversed")
        return result

    largest: list[dict[str, Any]] = []
    newest: list[dict[str, Any]] = []
    stack = [root]
    visited = 0

    while stack:
        directory = stack.pop()
        try:
            entries = list(os.scandir(directory))
        except OSError as exc:
            result["warnings"].append(f"cannot scan {directory}: {type(exc).__name__}")
            continue

        for entry in entries:
            visited += 1
            if visited > max_entries:
                result["truncated"] = True
                stack.clear()
                break

            path = Path(entry.path)
            try:
                if _is_sensitive_path(path.relative_to(root)):
                    continue
                info = entry.stat(follow_symlinks=False)
            except OSError as exc:
                result["warnings"].append(f"cannot stat {path}: {type(exc).__name__}")
                continue

            if stat.S_ISLNK(info.st_mode):
                result["symlink_count"] += 1
                continue
            if stat.S_ISDIR(info.st_mode):
                result["directory_count"] += 1
                stack.append(path)
                continue
            if not stat.S_ISREG(info.st_mode):
                continue

            size = int(info.st_size)
            mtime = int(info.st_mtime)
            rel = path.relative_to(root).as_posix()
            top = rel.split("/", 1)[0]
            bucket = result["top_level"].setdefault(top, {"file_count": 0, "bytes": 0})
            bucket["file_count"] += 1
            bucket["bytes"] += size
            result["file_count"] += 1
            result["total_bytes"] += size

            item = {"path": rel, "bytes": size, "mtime_epoch": mtime}
            largest.append(item)
            newest.append(item)

    result["largest_files"] = sorted(
        largest, key=lambda item: (item["bytes"], item["path"]), reverse=True
    )[:TOP_FILES]
    result["newest_files"] = sorted(
        newest, key=lambda item: (item["mtime_epoch"], item["path"]), reverse=True
    )[:TOP_FILES]
    result["top_level"] = dict(
        sorted(result["top_level"].items(), key=lambda pair: pair[1]["bytes"], reverse=True)
    )
    if result["truncated"]:
        result["warnings"].append(f"entry limit reached ({max_entries}); totals are partial")
    return result


def discover_roots() -> list[Path]:
    candidates = [Path("/var/lib/cace-cache")]
    candidates.extend(sorted(Path("/var/tmp").glob("cace-formal.*")))
    unique: dict[str, Path] = {}
    for path in candidates:
        if not _is_sensitive_path(path):
            unique[str(path)] = path
    return list(unique.values())


def build_inventory(roots: list[Path], max_entries: int = DEFAULT_MAX_ENTRIES) -> dict[str, Any]:
    return {
        "schema": "cace-oci-runner-data-inventory-v1",
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "collection_mode": "read-only-metadata-only",
        "content_read": False,
        "symlinks_followed": False,
        "uploads_performed": False,
        "deletions_performed": False,
        "roots": [inventory_root(root, max_entries=max_entries) for root in roots],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("runner-data-inventory"))
    parser.add_argument("--max-entries-per-root", type=int, default=DEFAULT_MAX_ENTRIES)
    args = parser.parse_args()
    if args.max_entries_per_root < 1:
        parser.error("--max-entries-per-root must be positive")
    args.output.mkdir(parents=True, exist_ok=True)
    payload = build_inventory(discover_roots(), max_entries=args.max_entries_per_root)
    destination = args.output / "inventory.json"
    destination.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    total_bytes = sum(root["total_bytes"] for root in payload["roots"])
    print(json.dumps({
        "inventory": str(destination),
        "roots": len(payload["roots"]),
        "files": sum(root["file_count"] for root in payload["roots"]),
        "bytes": total_bytes,
        "truncated": any(root["truncated"] for root in payload["roots"]),
        "content_read": False,
        "deletions_performed": False,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
