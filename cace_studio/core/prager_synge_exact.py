from __future__ import annotations
from fractions import Fraction
from typing import Any
import hashlib, json

KERNEL_NAME = "CACE-Prager-Synge-Exact-Kernel"
KERNEL_VERSION = "3.10.0"

def F(x):
    if isinstance(x, Fraction): return x
    return Fraction(str(x))

def dotW(x,y,W):
    return sum(F(x[i])*sum(F(W[i][j])*F(y[j]) for j in range(len(y))) for i in range(len(x)))

def check_artifact(a: dict[str,Any]) -> dict[str,Any]:
    errors=[]
    x=[F(v) for v in a.get("primal_error",[])]
    y=[F(v) for v in a.get("dual_error",[])]
    W=[[F(v) for v in row] for row in a.get("weight",[])]
    if not x or len(x)!=len(y) or len(W)!=len(x) or any(len(r)!=len(x) for r in W):
        errors.append("dimension mismatch")
    else:
        if any(W[i][j] != W[j][i] for i in range(len(W)) for j in range(len(W))): errors.append("weight not symmetric")
        orth=dotW(x,y,W)
        lhs=dotW([x[i]+y[i] for i in range(len(x))],[x[i]+y[i] for i in range(len(x))],W)
        rhs=dotW(x,x,W)+dotW(y,y,W)
        if orth != 0: errors.append(f"orthogonality failed: {orth}")
        if lhs != rhs: errors.append(f"hypercircle identity failed: {lhs} != {rhs}")
    B=[[F(v) for v in row] for row in a.get("equilibrium_matrix",[])]
    q=[F(v) for v in a.get("flux_dofs",[])]
    f=[F(v) for v in a.get("source_integrals",[])]
    if B:
        if len(B)!=len(f) or any(len(r)!=len(q) for r in B): errors.append("equilibrium dimensions invalid")
        else:
            res=[sum(B[i][j]*q[j] for j in range(len(q)))-f[i] for i in range(len(B))]
            if any(v!=0 for v in res): errors.append("equilibrium failed: "+str(res))
    signs=a.get("interior_face_sign_pairs",[])
    if any(len(p)!=2 or int(p[0])+int(p[1])!=0 for p in signs): errors.append("interior face cancellation failed")
    canonical={k:a[k] for k in sorted(a)}
    return {
      "passed": not errors,
      "errors": errors,
      "checker": KERNEL_NAME,
      "checker_version": KERNEL_VERSION,
      "artifact_sha256": hashlib.sha256(json.dumps(canonical,sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest(),
    }
