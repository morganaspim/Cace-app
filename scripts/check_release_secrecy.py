#!/usr/bin/env python3
"""Fail-closed CACE customer-release secrecy scanner.

This scanner inspects the final staged artifact, not just the source tree.
Supported inputs: directory, zip/wheel, tar/tar.gz/tgz.
"""
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import io
import json
import tarfile
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath


@dataclass(frozen=True)
class Entry:
    name: str
    data: bytes


def _norm(name: str) -> str:
    value = str(PurePosixPath(name.replace("\\", "/")))
    while value.startswith("./"):
        value = value[2:]
    return value


def _entries(path: Path) -> list[Entry]:
    if path.is_dir():
        out: list[Entry] = []
        for item in sorted(p for p in path.rglob("*") if p.is_file()):
            out.append(Entry(_norm(item.relative_to(path).as_posix()), item.read_bytes()))
        return out
    if not path.is_file():
        raise ValueError(f"release artifact not found: {path}")
    lower = path.name.lower()
    if lower.endswith((".zip", ".whl")):
        with zipfile.ZipFile(path) as zf:
            return [
                Entry(_norm(info.filename), zf.read(info))
                for info in zf.infolist()
                if not info.is_dir()
            ]
    if lower.endswith((".tar", ".tar.gz", ".tgz")):
        mode = "r:gz" if lower.endswith((".tar.gz", ".tgz")) else "r:"
        with tarfile.open(path, mode) as tf:
            out = []
            for member in tf.getmembers():
                if not member.isfile():
                    continue
                handle = tf.extractfile(member)
                if handle is None:
                    continue
                out.append(Entry(_norm(member.name), handle.read()))
            return out
    raise ValueError("unsupported release artifact type; expected directory, zip/whl, tar, tar.gz, or tgz")


def _matches_glob(name: str, pattern: str) -> bool:
    # fnmatch does not make ** special, but it is suitable here because paths
    # are normalized and the patterns intentionally match path strings.
    return fnmatch.fnmatchcase(name, pattern) or (
        pattern.endswith("/**") and (name == pattern[:-3] or name.startswith(pattern[:-2]))
    )


def scan(artifact: Path, policy: dict) -> tuple[dict, int]:
    try:
        entries = _entries(artifact)
    except Exception as exc:
        return {
            "schema": "cace-release-secrecy-scan-v1",
            "status": "INPUT_ERROR",
            "artifact": str(artifact),
            "issues": [],
            "error": str(exc),
        }, 2

    if not entries:
        return {
            "schema": "cace-release-secrecy-scan-v1",
            "status": "FAIL",
            "artifact": str(artifact),
            "issues": [{"kind": "empty-artifact", "path": ""}],
        }, 1

    forbidden_paths = list(policy.get("forbidden_paths", []))
    forbidden_suffixes = tuple(policy.get("forbidden_suffixes", []))
    forbidden_basenames = set(policy.get("forbidden_basenames", []))
    markers = [m.encode("utf-8") for m in policy.get("forbidden_text_markers", [])]
    issues: list[dict] = []
    manifest_files: list[dict] = []

    for entry in entries:
        name = _norm(entry.name)
        base = PurePosixPath(name).name
        digest = hashlib.sha256(entry.data).hexdigest()
        manifest_files.append({"path": name, "size_bytes": len(entry.data), "sha256": digest})

        for pattern in forbidden_paths:
            if _matches_glob(name, pattern):
                issues.append({"kind": "forbidden-path", "path": name, "rule": pattern})
                break
        if forbidden_suffixes and name.endswith(forbidden_suffixes):
            issues.append({"kind": "forbidden-suffix", "path": name})
        if base in forbidden_basenames:
            issues.append({"kind": "forbidden-basename", "path": name})
        for marker in markers:
            if marker in entry.data:
                issues.append({
                    "kind": "forbidden-text-marker",
                    "path": name,
                    "marker": marker.decode("utf-8", errors="replace"),
                })

    canonical_manifest = json.dumps(manifest_files, sort_keys=True, separators=(",", ":")).encode("utf-8")
    report = {
        "schema": "cace-release-secrecy-scan-v1",
        "policy_id": policy.get("policy_id"),
        "artifact": str(artifact),
        "file_count": len(entries),
        "manifest_sha256": hashlib.sha256(canonical_manifest).hexdigest(),
        "status": "PASS" if not issues else "FAIL",
        "issues": issues,
        "files": manifest_files,
    }
    return report, 0 if not issues else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("artifact", type=Path)
    parser.add_argument(
        "--policy",
        type=Path,
        default=Path("security/release_secrecy_policy.json"),
    )
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    try:
        policy = json.loads(args.policy.read_text(encoding="utf-8"))
    except Exception as exc:
        print(json.dumps({
            "schema": "cace-release-secrecy-scan-v1",
            "status": "INPUT_ERROR",
            "error": f"cannot load policy: {exc}",
        }, indent=2, sort_keys=True))
        return 2

    report, code = scan(args.artifact, policy)
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    print(payload, end="")
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(payload, encoding="utf-8")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
