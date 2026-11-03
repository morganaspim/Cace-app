#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess

from cace_studio.app import build_qualified_capabilities, build_registry
from cace_studio.core.reproducibility import sha256_identity


ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / "ops" / "capability_workflows.json"
COORDINATE_VIEWS = ROOT / "ops" / "coordinate_views.json"


def resolve_source_commit(explicit: str | None) -> str:
    if explicit:
        value = explicit.strip()
    else:
        value = os.getenv("GITHUB_SHA", "").strip()
    if not value:
        value = subprocess.check_output(
            ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
            text=True,
        ).strip()
    if len(value) < 7:
        raise ValueError("source commit identity is invalid")
    return value


def build_manifest(source_commit: str) -> dict:
    registry = build_registry()
    capabilities = build_qualified_capabilities(registry)
    workflows = json.loads(WORKFLOWS.read_text(encoding="utf-8"))
    coordinate_views = json.loads(COORDINATE_VIEWS.read_text(encoding="utf-8"))
    manifest = capabilities.release_manifest_payload(source_commit=source_commit)
    manifest["workflow_contract_sha256"] = sha256_identity(workflows)
    manifest["coordinate_view_contract_sha256"] = sha256_identity(coordinate_views)
    manifest["coordinate_view_ids"] = sorted(
        item["view_id"] for item in coordinate_views.get("views", [])
    )
    manifest["workflow_ids"] = sorted(
        item["workflow_id"] for item in workflows.get("workflows", [])
    )
    manifest["artifact_identity_algorithm"] = "sha256/cace-canonical-json-v1"
    canonical = dict(manifest)
    manifest["manifest_sha256"] = sha256_identity(canonical)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-commit")
    parser.add_argument("--output", type=Path, default=Path("cace-capability-manifest.json"))
    args = parser.parse_args()

    manifest = build_manifest(resolve_source_commit(args.source_commit))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "status": "PASS",
        "output": str(args.output),
        "source_commit": manifest["source_commit"],
        "manifest_sha256": manifest["manifest_sha256"],
        "ui_modules": len(manifest["ui_module_ids"]),
        "ai_modules": len(manifest["ai_module_ids"]),
        "proof_effect": "none",
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
