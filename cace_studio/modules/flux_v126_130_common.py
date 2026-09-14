from __future__ import annotations

from fractions import Fraction
import hashlib
import json
import math
from typing import Any

from cace_studio.modules.fem_v051_075_common import ResultModule
from cace_studio.core.types import ModuleMetadata, Maturity, EvidenceKind, ProofStatus
from cace_studio.core.theorems import TheoremStatus, TheoremContract


def F(x: Any) -> Fraction:
    if isinstance(x, Fraction):
        return x
    return Fraction(str(x))


def qjson(obj: Any) -> str:
    """Project JSON default: pretty printed and terminated by two newlines."""
    return json.dumps(obj, indent=2, sort_keys=True, default=str) + "\n\n"


def sha(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def sub(a, b):
    return (a[0] - b[0], a[1] - b[1])


def dot(a, b):
    return a[0] * b[0] + a[1] * b[1]


def det2(a, b):
    return a[0] * b[1] - a[1] * b[0]


def orient2(a, b, c):
    return det2(sub(b, a), sub(c, a))


def triangle_area(vertices):
    V = [tuple(map(F, p)) for p in vertices]
    d = orient2(*V)
    if d <= 0:
        raise ValueError("RT0 triangle must be nondegenerate and CCW")
    return d / 2


def local_edges_opposite(vertices):
    # Edge i is opposite vertex i; boundary direction is CCW.
    V = [tuple(map(F, p)) for p in vertices]
    return [(V[1], V[2]), (V[2], V[0]), (V[0], V[1])]


def edge_integrated_flux_of_rt0_basis(vertices, basis_index, edge_index):
    """Exact integral int_E phi_i.n ds using unnormalised outward normal*ds.

    phi_i(x)=(x-v_i)/(2|K|).  On a CCW edge p0->p1, n_out ds=(dy,-dx).
    The integrand is affine but constant in its normal component along a straight edge;
    midpoint integration is therefore exact.
    """
    V = [tuple(map(F, p)) for p in vertices]
    area = triangle_area(V)
    edges = local_edges_opposite(V)
    p0, p1 = edges[edge_index]
    mid = ((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2)
    vi = V[basis_index]
    phi = ((mid[0] - vi[0]) / (2 * area), (mid[1] - vi[1]) / (2 * area))
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    n_ds = (dy, -dx)
    return dot(phi, n_ds)


def rt0_reference_audit(vertices=((0, 0), (1, 0), (0, 1))):
    V = [tuple(map(F, p)) for p in vertices]
    area = triangle_area(V)
    flux_matrix = [[edge_integrated_flux_of_rt0_basis(V, i, j) for j in range(3)] for i in range(3)]
    identity = [[Fraction(int(i == j), 1) for j in range(3)] for i in range(3)]
    # div (x-v_i)/(2A)=2/(2A)=1/A, hence integrated divergence is 1.
    divs = [Fraction(1, 1) / area for _ in range(3)]
    integrated_divs = [d * area for d in divs]
    return {
        "pass": flux_matrix == identity and all(x == 1 for x in integrated_divs),
        "area": str(area),
        "edge_flux_matrix": [[str(x) for x in row] for row in flux_matrix],
        "divergence": [str(x) for x in divs],
        "integrated_divergence": [str(x) for x in integrated_divs],
        "exact": True,
        "scope": "RT0 on one rational CCW affine triangle",
    }


def edge_key(a: int, b: int):
    return (a, b) if a < b else (b, a)


def triangle_local_edge_vertex_ids(tri):
    a, b, c = tri
    return [(b, c), (c, a), (a, b)]  # opposite a,b,c; CCW boundary directions


def hdiv_topology(points, triangles):
    pts = [tuple(map(F, p)) for p in points]
    tris = [tuple(map(int, t)) for t in triangles]
    for t in tris:
        if orient2(pts[t[0]], pts[t[1]], pts[t[2]]) <= 0:
            raise ValueError("all triangles must be CCW")
    edge_ids = {}
    edge_records = []
    cell_edges = []
    cell_signs = []
    for k, tri in enumerate(tris):
        ce, cs = [], []
        for u, v in triangle_local_edge_vertex_ids(tri):
            key = edge_key(u, v)
            if key not in edge_ids:
                edge_ids[key] = len(edge_records)
                edge_records.append({"vertices": key, "cells": []})
            eid = edge_ids[key]
            # Global edge direction is low vertex id -> high vertex id; its right normal is global normal.
            sign = 1 if (u, v) == key else -1
            edge_records[eid]["cells"].append({"cell": k, "local_directed_edge": (u, v), "sign": sign})
            ce.append(eid); cs.append(sign)
        cell_edges.append(ce); cell_signs.append(cs)
    manifold = all(len(e["cells"]) in (1, 2) for e in edge_records)
    interior_opposite = True
    for e in edge_records:
        if len(e["cells"]) == 2:
            interior_opposite &= e["cells"][0]["sign"] == -e["cells"][1]["sign"]
    return {
        "pass": manifold and interior_opposite,
        "points": pts,
        "triangles": tris,
        "edges": edge_records,
        "cell_edges": cell_edges,
        "cell_signs": cell_signs,
        "manifold": manifold,
        "interior_local_signs_opposite": interior_opposite,
        "hdiv_normal_continuity_by_construction": manifold and interior_opposite,
    }


def two_triangle_mesh():
    points = [(0, 0), (1, 0), (1, 1), (0, 1)]
    triangles = [(0, 1, 3), (1, 2, 3)]
    return points, triangles


def center_square_mesh():
    points = [(0, 0), (1, 0), (1, 1), (0, 1), (Fraction(1, 2), Fraction(1, 2))]
    triangles = [(0, 1, 4), (1, 2, 4), (2, 3, 4), (3, 0, 4)]
    return points, triangles


def hdiv_continuity_audit():
    points, triangles = two_triangle_mesh()
    topo = hdiv_topology(points, triangles)
    interior = [e for e in topo["edges"] if len(e["cells"]) == 2]
    return {
        "pass": topo["pass"] and len(interior) == 1,
        "edge_count": len(topo["edges"]),
        "interior_edge_count": len(interior),
        "interior_sign_pairs": [[c["sign"] for c in e["cells"]] for e in interior],
        "normal_continuity": topo["hdiv_normal_continuity_by_construction"],
        "scope": "global RT0 edge-DOF orientation topology",
    }


def exact_linear_solve(A, b):
    A = [[F(x) for x in row] for row in A]
    b = [F(x) for x in b]
    n = len(A)
    M = [A[i] + [b[i]] for i in range(n)]
    for col in range(n):
        pivot = next((r for r in range(col, n) if M[r][col] != 0), None)
        if pivot is None:
            raise ValueError("singular exact system")
        M[col], M[pivot] = M[pivot], M[col]
        p = M[col][col]
        M[col] = [x / p for x in M[col]]
        for r in range(n):
            if r == col:
                continue
            f = M[r][col]
            if f:
                M[r] = [M[r][j] - f * M[col][j] for j in range(n + 1)]
    return [M[i][-1] for i in range(n)]


def exact_min_norm_constraints(B, b):
    """Return q=B^T (B B^T)^-1 b exactly; minimizes Euclidean ||q|| subject Bq=b."""
    B = [[F(x) for x in row] for row in B]
    b = [F(x) for x in b]
    m, n = len(B), len(B[0])
    G = [[sum(B[i][k] * B[j][k] for k in range(n)) for j in range(m)] for i in range(m)]
    y = exact_linear_solve(G, b)
    q = [sum(B[i][k] * y[i] for i in range(m)) for k in range(n)]
    return q


def equilibrium_matrix(points, triangles):
    topo = hdiv_topology(points, triangles)
    m, n = len(triangles), len(topo["edges"])
    B = [[Fraction(0) for _ in range(n)] for _ in range(m)]
    for k in range(m):
        for eid, s in zip(topo["cell_edges"][k], topo["cell_signs"][k]):
            B[k][eid] = Fraction(s)
    return topo, B


def reconstruct_equilibrated_flux(points, triangles, f_value=1):
    topo, B = equilibrium_matrix(points, triangles)
    pts = topo["points"]
    b = []
    for tri in topo["triangles"]:
        V = [pts[i] for i in tri]
        b.append(F(f_value) * triangle_area(V))
    q = exact_min_norm_constraints(B, b)
    residual = [sum(B[i][j] * q[j] for j in range(len(q))) - b[i] for i in range(len(B))]
    return {
        "pass": all(r == 0 for r in residual) and topo["pass"],
        "topology": topo,
        "B": B,
        "source_integrals": b,
        "global_edge_flux_dofs": q,
        "equilibrium_residual": residual,
        "exact": True,
        "construction": "minimum-Euclidean-norm global RT0 edge flux subject to exact cell equilibrium",
    }


def local_reconstruction_audit():
    points, triangles = [ (0,0),(1,0),(0,1) ], [(0,1,2)]
    r = reconstruct_equilibrated_flux(points, triangles, 1)
    q = r["global_edge_flux_dofs"]
    # single triangle all global/local signs happen to depend on ids; audit via Bq exactly.
    return {
        "pass": r["pass"],
        "edge_flux_dofs": [str(x) for x in q],
        "source_integral": str(r["source_integrals"][0]),
        "balance_residual": str(r["equilibrium_residual"][0]),
        "exact": True,
    }


def global_equilibrium_audit():
    points, triangles = center_square_mesh()
    r = reconstruct_equilibrated_flux(points, triangles, 1)
    interior = [e for e in r["topology"]["edges"] if len(e["cells"]) == 2]
    return {
        "pass": r["pass"],
        "cells": len(triangles),
        "edges": len(r["topology"]["edges"]),
        "interior_edges": len(interior),
        "max_exact_equilibrium_residual": "0" if r["pass"] else "nonzero",
        "hdiv_normal_continuity": r["topology"]["hdiv_normal_continuity_by_construction"],
        "edge_flux_dofs": [str(x) for x in r["global_edge_flux_dofs"]],
        "exact": True,
    }


def p1_grad_on_triangle(points, tri, nodal_values):
    V = [tuple(map(F, points[i])) for i in tri]
    vals = [F(nodal_values[i]) for i in tri]
    x0, y0 = V[0]; x1, y1 = V[1]; x2, y2 = V[2]
    det = orient2(*V)
    # grad barycentric coordinates for CCW triangle.
    grads = [
        ((y1-y2)/det, (x2-x1)/det),
        ((y2-y0)/det, (x0-x2)/det),
        ((y0-y1)/det, (x1-x0)/det),
    ]
    gx = sum(vals[i]*grads[i][0] for i in range(3))
    gy = sum(vals[i]*grads[i][1] for i in range(3))
    return (gx, gy)


def exact_p1_poisson_center_square(f_value=1):
    points, triangles = center_square_mesh()
    # only node 4 is interior. Assemble scalar stiffness and load exactly.
    K = Fraction(0); rhs = Fraction(0)
    for tri in triangles:
        if 4 not in tri:
            continue
        V = [tuple(map(F, points[i])) for i in tri]
        area = triangle_area(V)
        local_index = tri.index(4)
        det = orient2(*V)
        x0,y0=V[0]; x1,y1=V[1]; x2,y2=V[2]
        grads=[((y1-y2)/det,(x2-x1)/det),((y2-y0)/det,(x0-x2)/det),((y0-y1)/det,(x1-x0)/det)]
        g=grads[local_index]
        K += area * dot(g,g)
        rhs += F(f_value) * area / 3
    u4 = rhs / K
    vals = [Fraction(0),Fraction(0),Fraction(0),Fraction(0),u4]
    return points, triangles, vals, {"K":K,"rhs":rhs,"u_center":u4}


def rt0_vector_at(points, tri, local_coeffs, x):
    V=[tuple(map(F, points[i])) for i in tri]
    area=triangle_area(V)
    xx=tuple(map(F,x))
    vx=Fraction(0); vy=Fraction(0)
    for i,c in enumerate(local_coeffs):
        vi=V[i]
        vx += c*(xx[0]-vi[0])/(2*area)
        vy += c*(xx[1]-vi[1])/(2*area)
    return (vx,vy)


def affine_vector_square_integral(points, tri, local_coeffs, constant_vec=(0,0)):
    """Exact integral |sigma_RT0 + constant_vec|^2 using degree-2 vertex formula."""
    V=[tuple(map(F, points[i])) for i in tri]
    area=triangle_area(V)
    vals=[]
    c0=(F(constant_vec[0]),F(constant_vec[1]))
    for x in V:
        s=rt0_vector_at(points,tri,local_coeffs,x)
        vals.append((s[0]+c0[0],s[1]+c0[1]))
    # For scalar affine g: int_K g^2 = A/6*(sum g_i^2 + sum_{i<j} g_i g_j).
    total=Fraction(0)
    for comp in (0,1):
        z=[v[comp] for v in vals]
        total += area/Fraction(6) * (sum(t*t for t in z) + z[0]*z[1]+z[0]*z[2]+z[1]*z[2])
    return total


def prager_synge_certificate():
    """Guaranteed bound for the admitted Poisson setting on an exact rational fixture.

    Uses reviewed Prager-Synge theorem. Admissibility (H(div) continuity and div sigma=f)
    is checked exactly for an RT0 flux. The mismatch norm is integrated exactly as a rational
    squared norm. The square root is rounded upward with nextafter for the reported float bound.
    """
    points, triangles, uh, fem = exact_p1_poisson_center_square(1)
    rec = reconstruct_equilibrated_flux(points, triangles, 1)
    if not rec["pass"]:
        return {"pass":False,"guaranteed":False,"reason":"equilibrated flux reconstruction failed"}
    total_sq=Fraction(0)
    cell_terms=[]
    for k, tri in enumerate(triangles):
        # Convert global canonical edge DOFs into local outward RT0 coefficients.
        coeff=[]
        for eid,s in zip(rec["topology"]["cell_edges"][k],rec["topology"]["cell_signs"][k]):
            coeff.append(F(s)*rec["global_edge_flux_dofs"][eid])
        grad=p1_grad_on_triangle(points,tri,uh)
        # sigma + grad u_h for A=I since sigma=-grad u exact convention.
        term=affine_vector_square_integral(points,tri,coeff,grad)
        total_sq += term
        cell_terms.append(term)
    val=math.sqrt(float(total_sq))
    upper=math.nextafter(val, math.inf)
    return {
        "pass": rec["pass"] and total_sq >= 0,
        "guaranteed": True,
        "theorem_status": "reviewed-assumed",
        "machine_formal": False,
        "problem": "-Delta u = 1 on unit square, homogeneous Dirichlet, conforming P1",
        "flux_space": "global RT0 with canonical shared edge DOFs",
        "admissibility": {
            "exact_cell_equilibrium": True,
            "hdiv_normal_continuity": True,
            "div_sigma_equals_f": True,
        },
        "fem": {k:str(v) for k,v in fem.items()},
        "mismatch_norm_squared_exact": str(total_sq),
        "cell_mismatch_squared_exact": [str(x) for x in cell_terms],
        "guaranteed_energy_error_upper_float": upper,
        "bound_statement": "||grad(u-u_h)||_L2 <= ||sigma_h + grad(u_h)||_L2",
        "scope": "reviewed Prager-Synge theorem + exact admissibility/mismatch integration on this fixture",
    }


def prager_synge_contract():
    def matcher(facts):
        needed={
            "conforming_primal": bool(facts.get("conforming_primal")),
            "hdiv_flux": bool(facts.get("hdiv_flux")),
            "exact_equilibrium": bool(facts.get("exact_equilibrium")),
            "homogeneous_dirichlet": bool(facts.get("homogeneous_dirichlet")),
            "spd_diffusion": bool(facts.get("spd_diffusion")),
        }
        miss=[k for k,v in needed.items() if not v]
        return not miss, miss
    return TheoremContract(
        theorem_id="apost.prager_synge.guaranteed.v130",
        statement="For conforming primal v and statically admissible H(div) flux sigma, the Prager-Synge hypercircle identity yields a guaranteed energy-error upper bound by the constitutive mismatch.",
        status=TheoremStatus.REVIEWED_ASSUMED,
        assumptions=("conforming primal approximation","H(div) flux","exact equilibrium","compatible Dirichlet data","SPD diffusion"),
        evidence_kind=EvidenceKind.SYMBOLIC.value,
        checker="CACE v1.30 hypothesis matcher + exact RT0 admissibility fixture",
        artifact="docs/proofs/prager_synge_rt0_v130.json",
        matcher=matcher,
    )


CAP = {
    "126": ("RT0 Basis and Geometry", rt0_reference_audit, EvidenceKind.SYMBOLIC),
    "127": ("Global H(div) Edge Assembly", hdiv_continuity_audit, EvidenceKind.SYMBOLIC),
    "128": ("Local Equilibrated Flux Reconstruction", local_reconstruction_audit, EvidenceKind.SYMBOLIC),
    "129": ("Global Equilibrium Verification", global_equilibrium_audit, EvidenceKind.SYMBOLIC),
    "130": ("Prager-Synge Guaranteed Bound", prager_synge_certificate, EvidenceKind.SYMBOLIC),
}


class FluxStepModule(ResultModule):
    capability_key="126"
    module_id="flux126.rt0_basis"
    label="Flux Step"
    version="1.26.0"
    description="RT0 equilibrated-flux capability step."
    evidence_kind=EvidenceKind.SYMBOLIC
    metadata=ModuleMetadata(module_id,label,version,"Equilibrated Flux",description,Maturity.EXPERIMENTAL,
        assumptions=("Conforming affine CCW triangular mesh",))
    proof_status=ProofStatus(evidence={EvidenceKind.SYMBOLIC},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Prager-Synge is a reviewed imported theorem, not machine-formal unless explicitly stated otherwise."])
    def execute(self,inputs,params,ctx):
        return {"result": CAP[self.capability_key][1]()}
    def verify(self,inputs,params,outputs,ctx):
        return super().verify(inputs,params,outputs,ctx)
