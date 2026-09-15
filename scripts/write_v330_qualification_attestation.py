#!/usr/bin/env python3
"""Write a content-addressed formal qualification artifact after all checks pass.

This script does not run Lean and cannot create proof evidence on its own. The
portable qualifier invokes it only after the contract-required build and audit
checks succeed. The artifact binds that run to the exact claim, proof contract,
source bundle, toolchain/dependency state and axiom output.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cace_studio.core.claim_registry import ClaimRegistry
from cace_studio.core.proof_contract import ProofContractRegistry

CLAIM_ID = "cace.v330.continuum-proof-strengthening"
ARTIFACT_SCHEMA = "cace-formal-qualification-v2"


def out(cmd: list[str], *, cwd: Path | None = None) -> str:
    return subprocess.check_output(cmd, cwd=cwd, text=True).strip()


def source_bundle_sha256(formal_dir: Path, sources: tuple[str, ...]) -> str:
    digest = hashlib.sha256()
    for relative in sources:
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update((formal_dir / relative).read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--formal-dir", type=Path, required=True)
    parser.add_argument("--qualification-system", required=True)
    parser.add_argument("--qualification-run-id", required=True)
    parser.add_argument("--workflow-run-id", type=int)
    parser.add_argument("--axiom-audit", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path.cwd())
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    formal_dir = args.formal_dir.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    claims = ClaimRegistry.load_default()
    contracts = ProofContractRegistry.load_default()
    claim = claims.by_id(CLAIM_ID)
    contract = contracts.for_claim(CLAIM_ID)
    if claim is None or contract is None:
        raise SystemExit(f"canonical claim/proof contract is missing for {CLAIM_ID}")
    if claim.proof_contract_id != contract.contract_id:
        raise SystemExit(
            f"claim proof-contract binding mismatch: {claim.proof_contract_id!r} != "
            f"{contract.contract_id!r}"
        )

    if not args.qualification_system.strip() or not args.qualification_run_id.strip():
        raise SystemExit("qualification system/run id must be non-empty")
    if args.qualification_system == "github-actions" and (
        args.workflow_run_id is None or args.workflow_run_id <= 0
    ):
        raise SystemExit("github-actions attestation requires a positive workflow run id")
    if not args.axiom_audit.is_file():
        raise SystemExit(f"axiom audit is missing: {args.axiom_audit}")

    commit = out(["git", "rev-parse", "HEAD"], cwd=repo_root)
    if len(commit) != 40:
        raise SystemExit("could not resolve exact 40-hex git commit")
    if out(["git", "status", "--porcelain"], cwd=repo_root):
        raise SystemExit("refusing qualification artifact for a dirty working tree")

    expected_mathlib = contract.dependency_pins.get("mathlib_commit")
    if not expected_mathlib:
        raise SystemExit("proof contract does not pin mathlib_commit")
    mathlib_commit = out(
        ["git", "-C", str(formal_dir / ".lake/packages/mathlib"), "rev-parse", "HEAD"]
    )
    if mathlib_commit != expected_mathlib:
        raise SystemExit(
            f"mathlib commit mismatch: expected {expected_mathlib}, got {mathlib_commit}"
        )

    data = {
        "artifact_schema": ARTIFACT_SCHEMA,
        "release": "3.30.0-dev",
        "claim_id": CLAIM_ID,
        "claim_statement": claim.statement,
        "claim_scope": claim.scope,
        "status": "PASS",
        "commit": commit,
        "proof_contract_id": contract.contract_id,
        "proof_contract_sha256": contract.contract_sha256,
        "proof_contract_registry_sha256": contracts.registry_sha256,
        "claim_registry_sha256": claims.registry_sha256,
        "qualification_system": args.qualification_system.strip(),
        "qualification_run_id": args.qualification_run_id.strip(),
        "workflow_run_id": args.workflow_run_id,
        "lean_version": out(["lean", "--version"]),
        "mathlib_commit": mathlib_commit,
        "build_target": contract.build_target,
        "mathlib_cache_scope": "CACEFormal/V330AxiomAudit.lean transitive import closure",
        "endpoint_theorems": list(contract.endpoint_theorems),
        "audited_source_files": list(contract.audited_source_files),
        "audited_source_bundle_sha256": source_bundle_sha256(
            formal_dir, contract.audited_source_files
        ),
        "axiom_audit_sha256": hashlib.sha256(args.axiom_audit.read_bytes()).hexdigest(),
        "allowed_axioms": list(contract.allowed_axioms),
        "required_checks": list(contract.required_checks),
        "theorem_dependency_metadata": {
            "state": contract.theorem_dependency_metadata_state,
            "note": contract.theorem_dependency_metadata_note,
        },
        "claim_nonclaims": list(claim.nonclaims),
        "proof_contract_nonclaims": list(contract.nonclaims),
        "promotion_guards": {
            "unfinished_tokens_rejected": True,
            "sorryAx_rejected": True,
            "nonfoundation_axioms_rejected": True,
            "open_problem_requires_artifact_bound_independent_reproduction": True,
            "open_problem_requires_artifact_bound_external_review": True,
            "module_self_promotion_reserved_flags_rejected": True,
            "numerical_symbolic_interval_evidence_cannot_self_promote": True,
        },
    }

    path = output_dir / "v330_formal_qualification_attestation.json"
    rendered = json.dumps(data, indent=2, sort_keys=True) + "\n\n"
    path.write_text(rendered, encoding="utf-8")
    digest = hashlib.sha256(rendered.encode("utf-8")).hexdigest()
    (output_dir / "v330_formal_qualification_attestation.sha256").write_text(
        f"{digest}  {path.name}\n", encoding="utf-8"
    )
    print(rendered, end="")
    print("attestation_sha256:", digest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
