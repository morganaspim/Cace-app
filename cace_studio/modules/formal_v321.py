from __future__ import annotations
import hashlib, json, os, shutil
from pathlib import Path

from cace_studio.modules.formal_v301_320_common import *
from cace_studio.core.mesh_orthogonality_bridge import invoke_mesh_orthogonality_checker

def mesh_orthogonality_artifact():
    return {
      "theorem_id":"mesh-admissibility-to-orthogonality-v3.21",
      "points":[["0","0"],["1","0"],["1","1"],["0","1"],["1/2","1/2"]],
      "triangles":[[0,1,4],[1,2,4],[2,3,4],[3,0,4]],
      "primal_nodal_values":["0","0","0","0","1"],
      "flux_error_cell_vectors":[["1","0"],["1","0"],["1","0"],["1","0"]],
      "boundary_vertices":[0,1,2,3],
      "expected_global_pairing":"0"
    }

def local_lean_toolchain_probe():
    project_root=Path(__file__).resolve().parents[2]
    candidates=[]
    env_bin=os.environ.get("CACE_LEAN_BIN")
    if env_bin:
        candidates.append(Path(env_bin))
    candidates += [
      project_root/"formal"/"toolchain"/"bin",
      project_root/"formal"/"lean"/"bin",
      Path("/mnt/data/lean/bin"),
      Path("/mnt/data/lean4/bin"),
    ]
    # Also inspect shallow uploaded/extracted directories, without assuming a filename.
    try:
        for p in Path("/mnt/data").glob("*lean*"):
            if p.is_dir():
                candidates.extend([
                    p/"bin", p,
                    p/"build"/"release"/"stage1"/"bin",
                    p/"build"/"release"/"stage0"/"bin",
                    p/"build"/"stage1"/"bin",
                    p/"stage1"/"bin",
                    p/"stage0"/"bin",
                ])
        for pat in (
            "*/build/release/stage1/bin",
            "*/build/release/stage0/bin",
            "*/*/build/release/stage1/bin",
            "*/*/build/release/stage0/bin",
        ):
            candidates.extend(Path("/mnt/data").glob(pat))
    except Exception:
        pass

    system_lean=shutil.which("lean")
    system_lake=shutil.which("lake")
    if system_lean and system_lake:
        return {"pass":True,"lean":system_lean,"lake":system_lake,"source":"PATH"}

    for b in candidates:
        lean=b/"lean"; lake=b/"lake"
        if lean.exists() and lake.exists():
            return {"pass":True,"lean":str(lean),"lake":str(lake),"source":"local-candidate"}
    return {"pass":True,"lean":None,"lake":None,"source":"not-found","formal_status":"NOT_RUN"}


def uploaded_lean_assets_assessment():
    assets = []
    candidates = [
        Path("/mnt/data/lean-toolchain"),
        Path("/mnt/data/lakefile.toml"),
        Path("/mnt/data/run_test.sh"),
        Path("/mnt/data/run_clean.sh"),
        Path("/mnt/data/lean4-v4.0.0-m1-source.pdf"),
    ]
    for p in candidates:
        if p.exists():
            rec = {"path": str(p), "name": p.name, "exists": True}
            if p.name == "lean-toolchain":
                try:
                    rec["content"] = p.read_text(errors="replace").strip()
                except Exception:
                    pass
                rec["role"] = "toolchain selector/path reference; not an executable"
            elif p.suffix.lower() == ".pdf":
                rec["role"] = "source/documentation reference; not executable compiler payload"
                rec["source_version"] = "Lean 4 v4.0.0-m1"
                rec["compatibility_with_cace_pin"] = "incompatible with pinned Lean/mathlib v4.32.1"
            else:
                rec["role"] = "Lean/Lake build-test infrastructure fragment"
            assets.append(rec)
    tool = local_lean_toolchain_probe()
    return {
        "pass": True,
        "assets": assets,
        "runnable_toolchain_found": bool(tool.get("lean") and tool.get("lake")),
        "current_cace_pin": "Lean/mathlib v4.32.1",
        "policy": "Do not downgrade CACE Formal or promote source/documentation assets to executable theorem-prover evidence."
    }

def mesh_admissibility_to_orthogonality():
    artifact=mesh_orthogonality_artifact()
    check=invoke_mesh_orthogonality_checker(artifact)

    broken_boundary=json.loads(json.dumps(artifact))
    broken_boundary["primal_nodal_values"][0]="1/7"
    bad_boundary=invoke_mesh_orthogonality_checker(broken_boundary)

    broken_flux=json.loads(json.dumps(artifact))
    broken_flux["flux_error_cell_vectors"][1]=["2","0"]
    bad_flux=invoke_mesh_orthogonality_checker(broken_flux)

    tool=local_lean_toolchain_probe()
    root=Path(__file__).resolve().parents[2]
    source=root/"formal"/"cace_formal"/"CACEFormal"/"DiscreteOrthogonality.lean"
    source_text=source.read_text() if source.exists() else ""
    lean_source_closed=("theorem mesh_admissibility_to_orthogonality" in source_text and
                        "OPEN OBLIGATION" not in source_text)

    payload={
      "release":"3.21.0",
      "artifact":artifact,
      "exact_checker":check,
      "negative_tests":{
        "nonzero_boundary_rejected":not bool(bad_boundary.get("passed")),
        "normal_discontinuity_rejected":not bool(bad_flux.get("passed")),
      },
      "orthogonality_derived_not_assumed":bool(check.get("orthogonality_derived_not_assumed")),
      "lean_source_bridge_closed":lean_source_closed,
      "lean_toolchain":tool,
      "uploaded_lean_assets":uploaded_lean_assets_assessment(),
      "lean_external_build_status":"READY_TO_RUN" if tool.get("lean") and tool.get("lake") else "NOT_RUN",
      "full_external_machine_formal":False,
      "scope":"finite conforming P1/constant-RT0-error mesh fixture plus generic finite-sum Lean bridge"
    }
    payload["pass"]=(bool(check.get("passed")) and
                     all(payload["negative_tests"].values()) and
                     payload["orthogonality_derived_not_assumed"] and
                     lean_source_closed)
    payload["sha256"]=hashlib.sha256(
        json.dumps(payload,sort_keys=True,separators=(",",":"),default=str).encode()
    ).hexdigest()
    return payload

class FormalV321(FormalStepModule):
    capability_key="321"
    module_id="formal321.mesh_admissibility_to_orthogonality"
    label="Mesh Admissibility to Orthogonality"
    version="3.21.0"
    description="Derive finite-mesh primal/dual orthogonality from boundary admissibility, H(div) normal continuity, and divergence-free flux error."
    evidence_kind=EvidenceKind.SYMBOLIC
    metadata=ModuleMetadata(module_id,label,version,"CACE Formal",description,Maturity.EXPERIMENTAL,
        assumptions=("External Lean promotion still requires a successful pinned lake build.",))
    proof_status=ProofStatus(evidence={evidence_kind},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["The run-specific geometric derivation is custom exact-kernel evidence; Lean source is not external theorem-prover evidence until compiled."])
    def execute(self,inputs,params,ctx):
        return {"result":mesh_admissibility_to_orthogonality()}

def register_formal_v321(registry):
    registry.register(FormalV321)
