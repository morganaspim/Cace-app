#!/usr/bin/env python3
"""Mine a disposable CACE formal workspace before guarded cleanup.

The resulting manifest is discovery/acceleration evidence only. It never
substitutes for exact-head compilation, kernel checking, axiom auditing, or
qualification attestation.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


BUILD_LINE_RE = re.compile(r"(?:✔|\[\d+/\d+\].*?Built)\s*(?:\[\d+/\d+\]\s*)?([^\n]+?)(?:\s+\(([0-9.]+)s\))?$", re.MULTILINE)
BUILT_RE = re.compile(r"(?:✔\s+)?\[(\d+)/(\d+)\]\s+Built\s+([^\s]+)(?:\s+\(([0-9.]+)s\))?")
FAILED_RE = re.compile(r"^✖\s+\[(\d+)/(\d+)\]\s+Building\s+([^\s]+)", re.MULTILINE)
IMPORT_RE = re.compile(r"^\s*import\s+(.+?)\s*$")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8").strip()
    except (FileNotFoundError, UnicodeDecodeError, OSError):
        return None


def git_head(path: Path) -> str | None:
    try:
        return subprocess.check_output(
            ["git", "-C", str(path), "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def rel_record(path: Path, root: Path) -> dict[str, object]:
    stat = path.stat()
    return {
        "path": path.relative_to(root).as_posix(),
        "size_bytes": stat.st_size,
        "sha256": sha256_file(path),
    }


def sum_tree_bytes(root: Path) -> int:
    total = 0
    if not root.exists():
        return 0
    for p in root.rglob("*"):
        try:
            if p.is_file() and not p.is_symlink():
                total += p.stat().st_size
        except OSError:
            pass
    return total


def main() -> int:
    formal_dir = Path(os.environ["CACE_FORMAL_DIR"]).resolve()
    status_dir = Path(os.environ["CACE_STATUS_DIR"]).resolve()
    output_dir = Path(os.environ.get("CACE_OUTPUT_DIR", status_dir)).resolve()
    workspace = Path(os.environ.get("GITHUB_WORKSPACE", ".")).resolve()
    build_root = formal_dir / ".lake" / "build"

    status_dir.mkdir(parents=True, exist_ok=True)

    source_root = formal_dir / "CACEFormal"
    source_files = sorted(source_root.rglob("*.lean")) if source_root.exists() else []
    source_modules = {
        ".".join(p.relative_to(formal_dir).with_suffix("").parts): p for p in source_files
    }
    dependency_edges: list[dict[str, str]] = []
    for module, path in sorted(source_modules.items()):
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for line in lines:
            m = IMPORT_RE.match(line)
            if not m:
                continue
            for imported in m.group(1).split():
                if imported.startswith("CACEFormal."):
                    dependency_edges.append({"module": module, "imports": imported})

    cace_build_artifacts: list[dict[str, object]] = []
    if build_root.exists():
        for path in sorted(build_root.rglob("*")):
            if not path.is_file() or path.is_symlink():
                continue
            rel = path.relative_to(build_root).as_posix()
            if "CACEFormal" not in rel:
                continue
            try:
                cace_build_artifacts.append(rel_record(path, build_root))
            except OSError:
                continue

    diagnostic_files: list[dict[str, object]] = []
    for path in sorted(status_dir.glob("*")):
        if not path.is_file() or path.name.startswith("mining_manifest"):
            continue
        try:
            diagnostic_files.append(rel_record(path, status_dir))
        except OSError:
            continue

    output_files: list[dict[str, object]] = []
    if output_dir.exists():
        for path in sorted(output_dir.glob("*")):
            if path.is_file() and not path.is_symlink():
                try:
                    output_files.append(rel_record(path, output_dir))
                except OSError:
                    continue

    compile_timings: list[dict[str, object]] = []
    failed_targets: list[dict[str, object]] = []
    frontier_current = 0
    frontier_total = 0
    for log in sorted(status_dir.glob("*.log")):
        try:
            text = log.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for m in BUILT_RE.finditer(text):
            cur, total, target, seconds = m.groups()
            cur_i, total_i = int(cur), int(total)
            if (total_i, cur_i) > (frontier_total, frontier_current):
                frontier_current, frontier_total = cur_i, total_i
            compile_timings.append(
                {
                    "target": target,
                    "current": cur_i,
                    "total": total_i,
                    "seconds": float(seconds) if seconds else None,
                    "log": log.name,
                }
            )
        for m in FAILED_RE.finditer(text):
            cur, total, target = m.groups()
            failed_targets.append(
                {"target": target, "current": int(cur), "total": int(total), "log": log.name}
            )

    heartbeat_files = [p for p in status_dir.glob("heartbeat*.jsonl") if p.is_file()]
    heartbeat_hashes = [rel_record(p, status_dir) for p in sorted(heartbeat_files)]

    disk = shutil.disk_usage(formal_dir)
    meminfo = read_text(Path("/proc/meminfo"))
    cache_invalidated = read_text(status_dir / "cache_invalidated_modules.txt")
    unrecognized = read_text(status_dir / "cache_unrecognized_formal_paths.txt")

    mathlib_dir = formal_dir / ".lake" / "packages" / "mathlib"
    manifest: dict[str, object] = {
        "schema": "cace-ephemeral-build-mining-v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "evidence_class": "DISCOVERY_ACCELERATION_ONLY",
        "qualification_authority": "none; fresh exact-current-head qualification remains mandatory",
        "identity": {
            "git_commit": os.environ.get("CACE_EXPECTED_SHA") or os.environ.get("GITHUB_SHA"),
            "workflow_run_id": os.environ.get("GITHUB_RUN_ID"),
            "workflow_run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
            "formal_tree_sha": os.environ.get("CACE_FORMAL_TREE_SHA"),
            "lean_toolchain": os.environ.get("CACE_TOOLCHAIN"),
            "mathlib_expected_commit": os.environ.get("CACE_MATHLIB_COMMIT"),
            "mathlib_actual_commit": git_head(mathlib_dir),
        },
        "cache": {
            "mode": read_text(status_dir / "cache_mode.txt") or os.environ.get("CACE_CACHE_MODE", "miss"),
            "baseline_tree": read_text(status_dir / "cache_baseline_tree.txt") or os.environ.get("CACE_CACHE_BASELINE_TREE") or None,
            "baseline_commit": read_text(status_dir / "cache_baseline_commit.txt"),
            "invalidation_mode": read_text(status_dir / "cache_invalidation_mode.txt"),
            "invalidated_modules": cache_invalidated.splitlines() if cache_invalidated else [],
            "unrecognized_formal_paths": unrecognized.splitlines() if unrecognized else [],
        },
        "frontier": {
            "max_lake_current": frontier_current or None,
            "max_lake_total": frontier_total or None,
            "failed_targets": failed_targets,
        },
        "source": {
            "cace_module_count": len(source_modules),
            "dependency_edges": dependency_edges,
        },
        "build": {
            "cace_artifact_count": len(cace_build_artifacts),
            "cace_artifacts": cace_build_artifacts,
            "compile_timings": compile_timings,
            "build_tree_bytes": sum_tree_bytes(build_root),
        },
        "diagnostics": {
            "files": diagnostic_files,
            "heartbeat_files": heartbeat_hashes,
        },
        "outputs": {
            "files": output_files,
            "qualification_attestation_present": (output_dir / "cace_continuum_qualification_attestation.json").is_file(),
        },
        "resources": {
            "filesystem_total_bytes": disk.total,
            "filesystem_used_bytes": disk.used,
            "filesystem_free_bytes": disk.free,
            "proc_meminfo": meminfo,
        },
        "workspace": {
            "formal_dir": str(formal_dir),
            "status_dir": str(status_dir),
            "workspace": str(workspace),
        },
    }

    manifest_path = status_dir / "mining_manifest.json"
    data = (json.dumps(manifest, sort_keys=True, indent=2) + "\n").encode("utf-8")
    manifest_path.write_bytes(data)
    digest = hashlib.sha256(data).hexdigest()
    (status_dir / "mining_manifest.json.sha256").write_text(
        f"{digest}  mining_manifest.json\n", encoding="utf-8"
    )
    print(
        "CACE_EPHEMERAL_BUILD_MINING_COMPLETE "
        f"manifest_sha256={digest} cace_artifacts={len(cace_build_artifacts)} "
        f"frontier={frontier_current or 0}/{frontier_total or 0} failed_targets={len(failed_targets)}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
