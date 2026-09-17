#!/usr/bin/env python3
"""Generate deterministic repository indexes for humans and AI agents.

Generated artifacts are navigation aids only. They do not establish scientific
or formal evidence. Canonical source, claim registries, proof ledgers and exact
qualification artifacts remain authoritative.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import asdict, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
OUTPUTS = {
    "MODULE_CATALOG.json",
    "CLAIM_CATALOG.json",
    "LEAN_IMPORT_GRAPH.json",
    "SOURCE_INDEX.json",
    "generated/CACE_SOURCE_CONTEXT.txt",
}
SOURCE_SUFFIXES = {".py", ".cpp", ".cc", ".cxx", ".c", ".hpp", ".h", ".lean", ".json", ".toml", ".yml", ".yaml", ".md"}
SOURCE_ROOTS = ("cace_studio", "cpp", "formal/cace_formal", "schema", "scripts", "tests")
LEAN_IMPORT_RE = re.compile(r"^\s*import\s+CACEFormal\.([A-Za-z0-9_.]+)\s*$")


def _json_safe(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return _json_safe(asdict(value))
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in sorted(value.items(), key=lambda item: str(item[0]))}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    if isinstance(value, set):
        return sorted((_json_safe(v) for v in value), key=lambda x: json.dumps(x, sort_keys=True, default=str))
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return repr(value)


def _stable_json(value: Any) -> str:
    return json.dumps(_json_safe(value), indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def _port(port: Any) -> dict[str, Any]:
    return {"name": port.name, "required": bool(port.required), "type_name": port.type_name}


def _parameter(param: Any) -> dict[str, Any]:
    return {
        "default": _json_safe(param.default),
        "description": param.description,
        "name": param.name,
        "type_name": param.type_name,
    }


def build_module_catalog() -> dict[str, Any]:
    from cace_studio.app import build_registry

    modules = []
    for cls in sorted(build_registry().classes(), key=lambda c: c.metadata.module_id):
        m = cls.metadata
        modules.append(
            {
                "assumptions": list(m.assumptions),
                "category": m.category,
                "description": m.description,
                "inputs": [_port(p) for p in cls.inputs],
                "maturity": m.maturity.value,
                "module_id": m.module_id,
                "name": m.name,
                "outputs": [_port(p) for p in cls.outputs],
                "parameters": [_parameter(p) for p in cls.parameters],
                "proof_status": cls.proof_status.to_dict(),
                "supports_gpu": bool(cls.supports_gpu),
                "version": m.version,
            }
        )
    return {
        "artifact_role": "generated navigation; not verification evidence",
        "canonical_registry": "cace_studio.app:build_registry",
        "module_count": len(modules),
        "modules": modules,
        "schema_version": 1,
    }


def build_claim_catalog() -> dict[str, Any]:
    source = ROOT / "cace_studio/data/claim_registry.json"
    data = json.loads(source.read_text(encoding="utf-8"))
    claims = sorted(data.get("claims", []), key=lambda item: item.get("claim_id", ""))
    return {
        "artifact_role": "generated navigation; canonical claim registry remains authoritative",
        "canonical_source": "cace_studio/data/claim_registry.json",
        "claim_count": len(claims),
        "claims": claims,
        "policy": data.get("policy"),
        "schema_version": 1,
    }


def _lean_files() -> list[Path]:
    base = ROOT / "formal/cace_formal/CACEFormal"
    return sorted((p for p in base.rglob("*.lean") if p.is_file()), key=lambda p: p.as_posix())


def build_lean_import_graph() -> dict[str, Any]:
    """Return source-level Lean imports only; this is never a theorem proof graph."""
    files = _lean_files()
    base = ROOT / "formal/cace_formal/CACEFormal"
    local_names = {
        p.relative_to(base).with_suffix("").as_posix().replace("/", ".") for p in files
    }
    edges: list[dict[str, str]] = []
    nodes = []
    for path in files:
        rel = path.relative_to(base).with_suffix("").as_posix().replace("/", ".")
        nodes.append({"id": rel, "path": path.relative_to(ROOT).as_posix()})
        for line in path.read_text(encoding="utf-8").splitlines():
            match = LEAN_IMPORT_RE.match(line)
            if match and match.group(1) in local_names:
                edges.append({"from": rel, "to": match.group(1)})
    edges.sort(key=lambda item: (item["from"], item["to"]))
    return {
        "artifact_role": "generated Lean import navigation only; not theorem dependency or verification evidence",
        "edge_count": len(edges),
        "edges": edges,
        "node_count": len(nodes),
        "nodes": nodes,
        "schema": "cace-lean-import-graph-v1",
    }


def _source_files() -> Iterable[Path]:
    for root_name in SOURCE_ROOTS:
        base = ROOT / root_name
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in SOURCE_SUFFIXES:
                continue
            rel = path.relative_to(ROOT).as_posix()
            if rel in OUTPUTS or rel.startswith("generated/"):
                continue
            if any(part in {".git", ".lake", "__pycache__", "build", "dist", ".pytest_cache"} for part in path.parts):
                continue
            yield path


def build_source_index() -> dict[str, Any]:
    entries = []
    for path in sorted(_source_files(), key=lambda p: p.relative_to(ROOT).as_posix()):
        data = path.read_bytes()
        entries.append(
            {
                "path": path.relative_to(ROOT).as_posix(),
                "sha256": hashlib.sha256(data).hexdigest(),
                "size_bytes": len(data),
            }
        )
    return {
        "artifact_role": "generated content index; hashes identify files but do not verify scientific claims",
        "file_count": len(entries),
        "files": entries,
        "hash_algorithm": "sha256",
        "schema_version": 1,
    }


def build_context_text(module_catalog: dict[str, Any], claim_catalog: dict[str, Any], lean_import_graph: dict[str, Any], source_index: dict[str, Any]) -> str:
    return "\n".join(
        [
            "CACE SOURCE CONTEXT — GENERATED NAVIGATION ONLY",
            "",
            "This file is generated from canonical repository source. It is not verification evidence.",
            "Do not infer PASS from metadata, historical artifacts, AI output, or absent verification.",
            "Canonical current claim status lives in cace_studio/data/claim_registry.json and proof_ledger.json.",
            "Formal source lives in formal/cace_formal/ and requires exact-commit qualification.",
            "PROOF_DEPENDENCY_GRAPH.json is reserved for evidence-derived theorem/assumption DAG output.",
            "",
            f"Registered modules: {module_catalog['module_count']}",
            f"Canonical claims: {claim_catalog['claim_count']}",
            f"Lean import nodes: {lean_import_graph['node_count']}",
            f"Lean local import edges: {lean_import_graph['edge_count']}",
            f"Indexed source files: {source_index['file_count']}",
            "",
            "Read first:",
            "- AGENTS.md",
            "- docs/STATUS.md",
            "- docs/ARCHITECTURE.md",
            "- docs/CONSTITUTION.md",
            "- docs/CLAIMS.md",
            "- docs/ROADMAP.md",
            "- AI_REPO_MAP.json",
            "- MODULE_CATALOG.json",
            "- CLAIM_CATALOG.json",
            "- LEAN_IMPORT_GRAPH.json",
            "- SOURCE_INDEX.json",
            "",
        ]
    )


def render_outputs() -> dict[str, str]:
    modules = build_module_catalog()
    claims = build_claim_catalog()
    lean_import_graph = build_lean_import_graph()
    source_index = build_source_index()
    return {
        "MODULE_CATALOG.json": _stable_json(modules),
        "CLAIM_CATALOG.json": _stable_json(claims),
        "LEAN_IMPORT_GRAPH.json": _stable_json(lean_import_graph),
        "SOURCE_INDEX.json": _stable_json(source_index),
        "generated/CACE_SOURCE_CONTEXT.txt": build_context_text(modules, claims, lean_import_graph, source_index),
    }


def write_or_check(outputs: dict[str, str], *, check: bool) -> int:
    stale = []
    for rel, content in outputs.items():
        path = ROOT / rel
        if check:
            if not path.exists() or path.read_text(encoding="utf-8") != content:
                stale.append(rel)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
    if stale:
        print("Generated AI indexes are stale:")
        for rel in stale:
            print(f" - {rel}")
        return 1
    if not check:
        print("Generated: " + ", ".join(sorted(outputs)))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail if committed generated indexes differ from canonical source")
    args = parser.parse_args()
    return write_or_check(render_outputs(), check=args.check)


if __name__ == "__main__":
    raise SystemExit(main())
