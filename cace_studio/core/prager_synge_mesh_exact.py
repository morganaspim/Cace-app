from __future__ import annotations
from fractions import Fraction
import hashlib, json
from typing import Any

KERNEL_NAME = "CACE-Mesh-Admissibility-Orthogonality-Exact-Kernel"
KERNEL_VERSION = "3.21.0"

def F(x):
    return x if isinstance(x, Fraction) else Fraction(str(x))

def orient2(a,b,c):
    ax,ay=map(F,a); bx,by=map(F,b); cx,cy=map(F,c)
    return (bx-ax)*(cy-ay)-(by-ay)*(cx-ax)

def grad_p1(vertices, values):
    (x0,y0),(x1,y1),(x2,y2)=[tuple(map(F,p)) for p in vertices]
    u0,u1,u2=map(F,values)
    det=orient2(vertices[0],vertices[1],vertices[2])
    if det <= 0:
        raise ValueError("triangle must be CCW and nondegenerate")
    g0=((y1-y2)/det,(x2-x1)/det)
    g1=((y2-y0)/det,(x0-x2)/det)
    g2=((y0-y1)/det,(x1-x0)/det)
    return (
        u0*g0[0]+u1*g1[0]+u2*g2[0],
        u0*g0[1]+u1*g1[1]+u2*g2[1],
    )

def dot(a,b):
    return sum(F(x)*F(y) for x,y in zip(a,b))

def canonical_edge(a,b):
    return (a,b) if a < b else (b,a)

def check_artifact(a: dict[str,Any]) -> dict[str,Any]:
    errors=[]
    pts=[tuple(map(F,p)) for p in a.get("points",[])]
    tris=[tuple(map(int,t)) for t in a.get("triangles",[])]
    vals=[F(v) for v in a.get("primal_nodal_values",[])]
    flux=[tuple(map(F,q)) for q in a.get("flux_error_cell_vectors",[])]

    if not pts or len(vals)!=len(pts) or len(flux)!=len(tris):
        errors.append("mesh/value/flux dimensions invalid")

    boundary=set(map(int,a.get("boundary_vertices",[])))
    if boundary and any(vals[i] != 0 for i in boundary):
        errors.append("boundary admissibility failed: primal trace is nonzero")

    cell_pairings=[]
    cell_divergence=[]
    edge_inc={}
    if not errors:
        for k,t in enumerate(tris):
            V=[pts[i] for i in t]
            det=orient2(*V)
            if det <= 0:
                errors.append(f"cell {k} not CCW/nondegenerate")
                continue
            area=det/Fraction(2)
            g=grad_p1(V,[vals[i] for i in t])
            q=flux[k]
            # Constant vector fields are a divergence-free RT0 subspace.
            div=Fraction(0)
            cell_divergence.append(div)
            cell_pairings.append(area*dot(q,g))
            for a0,b0 in ((t[0],t[1]),(t[1],t[2]),(t[2],t[0])):
                key=canonical_edge(a0,b0)
                # For a CCW triangle, unnormalized outward normal integrated along
                # the edge a->b is (dy, -dx).
                xa,ya=pts[a0]; xb,yb=pts[b0]
                n_ds=(yb-ya, -(xb-xa))
                normal_flux=dot(q,n_ds)
                edge_inc.setdefault(key,[]).append((k,normal_flux))

    face_cancellation=[]
    for e,inc in sorted(edge_inc.items()):
        if len(inc)==2:
            s=inc[0][1]+inc[1][1]
            face_cancellation.append((e,s))
            if s != 0:
                errors.append(f"interior normal continuity/cancellation failed on edge {e}: {s}")
        elif len(inc)==1:
            # On the physical boundary v is zero, so the flux pairing contributes zero.
            pass
        else:
            errors.append(f"nonmanifold edge {e}")

    if any(v != 0 for v in cell_divergence):
        errors.append("flux-error divergence is nonzero")

    global_pairing=sum(cell_pairings,Fraction(0))
    if global_pairing != 0:
        errors.append(f"derived mesh orthogonality failed: {global_pairing}")

    expected=a.get("expected_global_pairing")
    if expected is not None and global_pairing != F(expected):
        errors.append("expected global pairing does not match derived pairing")

    canonical={k:a[k] for k in sorted(a)}
    return {
      "passed": not errors,
      "errors": errors,
      "checker": KERNEL_NAME,
      "checker_version": KERNEL_VERSION,
      "artifact_sha256": hashlib.sha256(json.dumps(canonical,sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest(),
      "cell_pairings":[str(v) for v in cell_pairings],
      "cell_divergence":[str(v) for v in cell_divergence],
      "interior_face_cancellation":[{"edge":list(e),"sum":str(s)} for e,s in face_cancellation],
      "global_pairing":str(global_pairing),
      "orthogonality_derived_not_assumed": True,
    }
