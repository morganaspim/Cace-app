#!/usr/bin/env python3
"""Independently verify a Titan CACE evidence bundle and its artifact bytes."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from cace_studio.core.evidence_ledger import bundle_from_payload, verify_bundle

SHA40 = re.compile(r"^[0-9a-f]{40}$")
REQUIRED_BINDINGS = (
    "source_repository", "source_commit_sha", "workflow_run_id",
    "provider_commit", "vector_source_commit", "verification_scope",
)

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--artifact-root", type=Path, required=True)
    args = parser.parse_args()
    try:
        document = json.loads(args.bundle.read_text(encoding="utf-8"))
        if not isinstance(document, dict) or document.get("proof_effect") != "none":
            raise ValueError("bundle envelope must be an object with proof_effect=none")
        if document.get("command") != "titan-bundle":
            raise ValueError("unsupported bundle command")
        bundle = bundle_from_payload(document["bundle"])
        if document.get("bundle_sha256") != bundle.bundle_sha256:
            raise ValueError("declared bundle digest does not match canonical CACE bundle")
        bindings = bundle.bindings
        missing = [name for name in REQUIRED_BINDINGS if name not in bindings]
        if missing:
            raise ValueError(f"missing required provenance bindings: {missing}")
        for name in ("source_commit_sha", "provider_commit", "vector_source_commit"):
            if not isinstance(bindings[name], str) or not SHA40.fullmatch(bindings[name]):
                raise ValueError(f"{name} must be a full lowercase Git commit SHA")
        if not isinstance(bindings["workflow_run_id"], int) or isinstance(bindings["workflow_run_id"], bool):
            raise ValueError("workflow_run_id must be an integer")
        artifact_bytes = {}
        for artifact in bundle.artifacts:
            relative = Path(artifact.path or "")
            if relative.is_absolute() or ".." in relative.parts or not relative.parts:
                raise ValueError(f"unsafe or missing artifact path for {artifact.artifact_id}")
            target = (args.artifact_root / relative).resolve()
            root = args.artifact_root.resolve()
            if root not in target.parents:
                raise ValueError(f"artifact escapes artifact root: {artifact.artifact_id}")
            artifact_bytes[artifact.artifact_id] = target.read_bytes()
        digest = verify_bundle(bundle, artifact_bytes=artifact_bytes)
        print(json.dumps({
            "cli_schema": 1,
            "command": "titan-independent-bundle-verify",
            "valid": True,
            "bundle_sha256": digest,
            "merkle_root_sha256": bundle.merkle_root_sha256,
            "artifact_count": len(bundle.artifacts),
            "proof_effect": "none",
            "qualification_effect": "none",
            "signature_status": "not_checked",
            "note": "Artifact bytes and canonical provenance were verified; this does not establish mathematical or cryptographic correctness."
        }, sort_keys=True))
        return 0
    except Exception as exc:
        print(json.dumps({"cli_schema":1,"command":"titan-independent-bundle-verify","valid":False,"error":str(exc),"error_type":type(exc).__name__},sort_keys=True),file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
