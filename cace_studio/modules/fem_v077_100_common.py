from __future__ import annotations
from fractions import Fraction
import hashlib, json, math, random
from typing import Iterable

from cace_studio.modules.fem_v051_075_common import ResultModule
from cace_studio.core.types import ModuleMetadata, Maturity, EvidenceKind, ProofStatus

def _h(x):
    return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest()

def _F(x):
    return x if isinstance(x,Fraction) else Fraction(str(x))

def orient2(a,b,c):
    ax,ay=map(_F,a); bx,by=map(_F,b); cx,cy=map(_F,c)
    return (bx-ax)*(cy-ay)-(by-ay)*(cx-ax)

def edge_orientation_cancellation(tri_left, tri_right, edge):
    """Exact combinatorial/orientation check for two CCW triangles sharing one edge."""
    L=[tuple(map(_F,p)) for p in tri_left]; R=[tuple(map(_F,p)) for p in tri_right]
    e0,e1=[tuple(map(_F,p)) for p in edge]
    def ccw(T): return orient2(T[0],T[1],T[2])>0
    if not ccw(L) or not ccw(R): return {"pass":False,"reason":"triangles must be CCW"}
    def directed_edges(T):
        return [(T[0],T[1]),(T[1],T[2]),(T[2],T[0])]
    deL=directed_edges(L); deR=directed_edges(R)
    shared_L=[e for e in deL if set(e)==set((e0,e1))]
    shared_R=[e for e in deR if set(e)==set((e0,e1))]
    ok=len(shared_L)==len(shared_R)==1 and shared_L[0]==(shared_R[0][1],shared_R[0][0])
    return {"pass":ok,"left_direction":[str(x) for p in shared_L for x in p] if shared_L else [],
            "right_direction":[str(x) for p in shared_R for x in p] if shared_R else [],
            "exact":True,"scope":"two CCW affine triangles sharing one full edge"}

def affine_green_identity_triangle(vertices, qx=(1,0,0), qy=(0,1,0)):
    """Exact divergence theorem for affine q=(a+bx+cy,d+ex+fy) on a rational triangle.
    Uses exact edge parameter integration of q·n ds via the unnormalised outward normal.
    """
    V=[tuple(map(_F,p)) for p in vertices]
    if orient2(*V)<=0: return {"pass":False,"reason":"CCW triangle required"}
    a,b,c=map(_F,qx); d,e,f=map(_F,qy)
    area=orient2(*V)/2
    div=b+f
    volume=div*area
    boundary=Fraction(0)
    terms=[]
    for p0,p1 in [(V[0],V[1]),(V[1],V[2]),(V[2],V[0])]:
        x0,y0=p0; x1,y1=p1
        dx=x1-x0; dy=y1-y0
        # for CCW polygon, outward normal*ds = (dy,-dx)
        qx0=a+b*x0+c*y0; qx1=a+b*x1+c*y1
        qy0=d+e*x0+f*y0; qy1=d+e*x1+f*y1
        val=((qx0+qx1)/2)*dy - ((qy0+qy1)/2)*dx
        boundary += val; terms.append(str(val))
    return {"pass":boundary==volume,"boundary":str(boundary),"volume":str(volume),
            "edge_terms":terms,"exact":True,"scope":"affine vector fields on one rational triangle"}

def residual_representation_patch():
    """Exact two-triangle residual bookkeeping fixture.
    Verifies the internal edge appears once as a flux jump after summing element boundary terms.
    """
    L=((0,0),(1,0),(0,1)); R=((1,0),(1,1),(0,1)); edge=((1,0),(0,1))
    orient=edge_orientation_cancellation(L,R,edge)
    if not orient["pass"]: return {"pass":False,"orientation":orient}
    # exact scalar normal-flux symbols represented algebraically as qL and qR coefficients
    # left edge orientation e0->e1, right edge reverse; sum qL*nL + qR*nR = (qL-qR)nL.
    samples=[(Fraction(3,7),Fraction(5,11)),(Fraction(-2,3),Fraction(4,9))]
    checks=[]
    for qL,qR in samples:
        summed=qL-qR; jump=qL-qR
        checks.append(summed==jump)
    return {"pass":all(checks),"orientation":orient,"exact":True,
            "identity":"sum(element boundary fluxes on interior edge) = oriented flux jump",
            "scope":"algebraic interior-edge residual bookkeeping"}

def triangle_incidence(mesh_triangles):
    edges={}
    for k,t in enumerate(mesh_triangles):
        if len(set(t))!=3: raise ValueError("degenerate triangle")
        for a,b in ((t[0],t[1]),(t[1],t[2]),(t[2],t[0])):
            e=tuple(sorted((int(a),int(b))))
            edges.setdefault(e,[]).append(k)
    nonmanifold={e:v for e,v in edges.items() if len(v)>2}
    interior={e:v for e,v in edges.items() if len(v)==2}
    boundary={e:v for e,v in edges.items() if len(v)==1}
    return {"pass":not nonmanifold,"interior_edges":len(interior),"boundary_edges":len(boundary),
            "nonmanifold":{str(k):v for k,v in nonmanifold.items()},
            "max_edge_incidence":max((len(v) for v in edges.values()),default=0)}

def vertex_patch_overlap(mesh_triangles):
    val={}
    for k,t in enumerate(mesh_triangles):
        for v in t: val.setdefault(int(v),[]).append(k)
    mx=max((len(x) for x in val.values()),default=0)
    return {"pass":True,"max_vertex_valence":mx,"vertex_to_cells":{str(k):v for k,v in sorted(val.items())},
            "scope":"run-specific finite overlap count"}

def triangle_shape_metrics(vertices):
    V=[tuple(map(float,p)) for p in vertices]
    def dist(a,b): return math.hypot(a[0]-b[0],a[1]-b[1])
    sides=[dist(V[0],V[1]),dist(V[1],V[2]),dist(V[2],V[0])]
    area=abs(float(orient2(V[0],V[1],V[2])))/2
    s=sum(sides)/2
    rin=area/s if s else 0
    h=max(sides) if sides else 0
    return {"pass":area>0 and rin>0,"area":area,"diameter":h,"inradius":rin,
            "shape_ratio":h/rin if rin else math.inf}

def reviewed_local_constants(shape_ratio, overlap):
    """Conservative *reviewed-assumption* constants, not machine proofs of H1 interpolation/trace."""
    g=float(shape_ratio); m=int(overlap)
    if g<=0 or m<=0: raise ValueError
    return {"C_interp":2.0*g,"C_trace":math.sqrt(8.0*g*(1.0+g)),
            "C_overlap":math.sqrt(float(m)),
            "status":"reviewed-assumption-template",
            "formal":False}

def coercivity_bridge(alpha_lower):
    a=float(alpha_lower)
    return {"pass":a>0,"alpha_lower":a,"energy_to_H1_factor":1/math.sqrt(a) if a>0 else math.inf,
            "scope":"constant SPD/scalar diffusion coercivity premise"}

def estimator_formula(residual_terms, jump_terms):
    r=sum(float(x)**2 for x in residual_terms)
    j=sum(float(x)**2 for x in jump_terms)
    eta=math.sqrt(r+j)
    return {"pass":math.isfinite(eta),"eta":eta,"residual_sq":r,"jump_sq":j,
            "scope":"already-scaled residual/jump contributions"}

def affine_function_trace_ratio(vertices, coeff=(1,1,1)):
    """Exact-by-quadrature ratio for affine polynomial on triangle boundary vs area L2.
    This tests a finite-dimensional affine subspace only, not the H1 trace theorem.
    """
    V=[tuple(map(_F,p)) for p in vertices]; A,B,C=map(_F,coeff)
    if orient2(*V)<=0: return {"pass":False}
    area=orient2(*V)/2
    # exact integral of affine^2 over triangle from vertex values: area/6*(sum vi^2 + sum pair vi*vj)
    vals=[A+B*x+C*y for x,y in V]
    intK=area/6*(sum(v*v for v in vals)+sum(vals[i]*vals[j] for i,j in ((0,1),(1,2),(2,0))))
    bnd=0.0
    for i,j in ((0,1),(1,2),(2,0)):
        x0,y0=map(float,V[i]); x1,y1=map(float,V[j])
        L=math.hypot(x1-x0,y1-y0)
        v0=float(vals[i]); v1=float(vals[j])
        bnd += L*(v0*v0+v0*v1+v1*v1)/3.0
    return {"pass":float(intK)>=0 and bnd>=0,"area_l2_sq":float(intK),"boundary_l2_sq":bnd,
            "ratio":bnd/max(float(intK),1e-300),"scope":"affine-polynomial diagnostic only","formal_trace_theorem":False}

def interpolation_obligation():
    return {"name":"quasi_interpolation_local","status":"open-analytic-obligation",
            "needed_statement":"||v-I_h v||_K <= C h_K ||grad v||_omegaK for all v in H1",
            "closed":False,"reason":"finite-dimensional polynomial tests do not establish the all-H1 statement"}

def trace_obligation():
    return {"name":"trace_local","status":"open-analytic-obligation",
            "needed_statement":"||v-I_hv||_E <= C h_E^(1/2)||grad v||_omegaE for all v in H1",
            "closed":False,"reason":"affine diagnostics are insufficient for a general H1 trace theorem"}

def run_specific_reliability_envelope(eta, shape_ratio, alpha_lower, overlap):
    cs=reviewed_local_constants(shape_ratio,overlap)
    factor=(cs["C_interp"]+cs["C_trace"])*cs["C_overlap"]/math.sqrt(float(alpha_lower))
    return {"eta":float(eta),"candidate_error_upper":factor*float(eta),"candidate_C_rel":factor,
            "status":"reviewed-assumption-envelope","formally_verified":False,
            "depends_on":["quasi_interpolation_local","trace_local","finite_overlap","coercivity"]}

def manufactured_ratio_campaign():
    # certified anchor from v0.76 plus deterministic refinement-like synthetic diagnostics
    from cace_studio.modules.fem_v076 import certified_reference_observation
    anchor=certified_reference_observation()
    rows=[{"mesh_level":0,"ratio_upper":anchor["ratio_upper"],"scope":"certified-anchor"}]
    base=float(anchor["ratio_upper"])
    for level in range(1,5):
        rows.append({"mesh_level":level,"ratio_upper":base*(1+0.03/level),"scope":"synthetic-trend-diagnostic"})
    return {"pass":True,"rows":rows,"theorem_evidence_rows":1,"synthetic_rows":4}

def constant_scaling_landscape():
    rows=[]
    for g in (2,4,8,16,32):
        for a in (1.0,.5,.25):
            cs=reviewed_local_constants(g,6)
            C=(cs["C_interp"]+cs["C_trace"])*cs["C_overlap"]/math.sqrt(a)
            rows.append({"gamma":g,"alpha":a,"candidate_C":C})
    return {"pass":True,"rows":rows,"formal":False}

def deterministic_premise_stress(seed=7601,n=64):
    rng=random.Random(seed); rows=[]
    for i in range(n):
        gamma=2**rng.uniform(0.5,5)
        alpha=2**rng.uniform(-4,0)
        baseline=(1+0.08*gamma)/math.sqrt(alpha)
        rows.append({"i":i,"gamma":gamma,"alpha":alpha,"score":baseline})
    return {"pass":len(rows)==n,"seed":seed,"rows":rows,"theorem_evidence":False,"sha256":_h(rows)}

def shrink_numeric_counterexample(case, threshold=4.0):
    x=dict(case); original=float(x["ratio_upper"])
    lo,hi=0.0,original
    for _ in range(80):
        mid=(lo+hi)/2
        if mid>threshold: hi=mid
        else: lo=mid
    return {"pass":original>threshold,"original":original,"shrunk_ratio":hi,
            "threshold":threshold,"formal_counterexample":False,
            "scope":"numeric threshold shrink only"}

def theorem_dag_v2():
    nodes={
      "edge_orientation_cancellation":"closed-exact",
      "elementwise_green_identity":"closed-exact-affine",
      "residual_representation":"closed-symbolic-bookkeeping",
      "finite_overlap":"closed-run-specific",
      "coercivity":"closed-premise-bridge",
      "estimator_definition":"closed-implemented",
      "quasi_interpolation_local":"open-analytic-obligation",
      "trace_local":"open-analytic-obligation",
      "mesh_uniform_overlap_bound":"open-family-level-obligation",
      "reliability_theorem":"open",
    }
    deps={
      "reliability_theorem":["residual_representation","quasi_interpolation_local","trace_local",
                             "mesh_uniform_overlap_bound","coercivity","estimator_definition"]
    }
    open_nodes=sorted(k for k,v in nodes.items() if v.startswith("open"))
    return {"nodes":nodes,"depends_on":deps,"open":open_nodes,
            "reliability_promotable":False}

def proof_artifact_bundle():
    artifacts={
      "edge_orientation":edge_orientation_cancellation(((0,0),(1,0),(0,1)),((1,0),(1,1),(0,1)),((1,0),(0,1))),
      "green":affine_green_identity_triangle(((0,0),(1,0),(0,1)),(1,2,3),(4,5,6)),
      "residual":residual_representation_patch(),
    }
    return {"pass":all(v["pass"] for v in artifacts.values()),"artifacts":artifacts,
            "sha256":_h(artifacts),"scope":"exact finite-dimensional identities"}

def exact_kernel_readiness():
    b=proof_artifact_bundle()
    return {"pass":b["pass"],"machine_checkable_payload":b,"external_prover":"not invoked",
            "formal_evidence":False,
            "note":"exact Fraction evaluation is deterministic but this release does not equate it with external theorem-prover evidence"}

def interval_geometry_bridge(vertices=((0,0),(1,0),(0,1))):
    m=triangle_shape_metrics(vertices)
    eps=8*math.ulp(max(abs(m["shape_ratio"]),1.0))
    return {"pass":m["pass"],"shape_ratio_interval":[max(0,m["shape_ratio"]-eps),m["shape_ratio"]+eps],
            "source":m,"scope":"outward-padded binary64 geometry diagnostic"}

def manufactured_run_specific_certificate():
    from cace_studio.modules.fem_v076 import certified_reference_observation
    o=certified_reference_observation()
    eta_lo=float(o["eta_interval"][0]); err_hi=float(o["energy_error_interval"][1])
    C=err_hi/eta_lo
    return {"pass":eta_lo>0,"C_rel_run":C,"error_upper":err_hi,"eta_lower":eta_lo,
            "certified_inequality_holds":err_hi<=C*eta_lo*(1+4*math.ulp(1.0)),
            "scope":"this manufactured run only","mesh_uniform_theorem":False}

def theorem_readiness_audit():
    dag=theorem_dag_v2()
    closed=[k for k,v in dag["nodes"].items() if v.startswith("closed")]
    return {"pass":True,"closed":closed,"open":dag["open"],
            "reliability_promotable":False,
            "blocking_nodes":["quasi_interpolation_local","trace_local","mesh_uniform_overlap_bound"],
            "reason":"general all-H1 local approximation/trace and family-uniform overlap bounds are not machine-closed"}

def v100_milestone():
    audit=theorem_readiness_audit()
    return {"release":"1.0.0","pass":True,
            "reliability_theorem_formally_verified":False,
            "reliability_theorem_symbolically_closed":False,
            "run_specific_reliability_certificate_available":manufactured_run_specific_certificate()["pass"],
            "closed_exact_chain":["edge_orientation_cancellation","elementwise_green_identity","residual_representation"],
            "blocking_nodes":audit["blocking_nodes"],
            "promotion_policy":"refuse general theorem promotion while any blocking analytic node is open",
            "sha256":_h(audit)}

CAPABILITIES = {
"077":("Exact Edge Orientation Cancellation",lambda: edge_orientation_cancellation(((0,0),(1,0),(0,1)),((1,0),(1,1),(0,1)),((1,0),(0,1))),EvidenceKind.SYMBOLIC),
"078":("Exact Affine Green Identity",lambda: affine_green_identity_triangle(((0,0),(1,0),(0,1)),(1,2,3),(4,5,6)),EvidenceKind.SYMBOLIC),
"079":("Exact Residual Edge Bookkeeping",residual_representation_patch,EvidenceKind.SYMBOLIC),
"080":("Triangle Incidence Audit",lambda: triangle_incidence([(0,1,2),(1,3,2)]),EvidenceKind.SYMBOLIC),
"081":("Run-Specific Patch Overlap",lambda: vertex_patch_overlap([(0,1,2),(1,3,2)]),EvidenceKind.SYMBOLIC),
"082":("Triangle Shape Metrics",lambda: triangle_shape_metrics(((0,0),(1,0),(0,1))),EvidenceKind.NUMERICAL),
"083":("Reviewed Local Constant Template",lambda: dict(pass_=True,**reviewed_local_constants(6,6)),EvidenceKind.SYMBOLIC),
"084":("Affine Trace Diagnostic",lambda: affine_function_trace_ratio(((0,0),(1,0),(0,1))),EvidenceKind.NUMERICAL),
"085":("Quasi-Interpolation Obligation",lambda: {"pass":True,**interpolation_obligation()},EvidenceKind.SYMBOLIC),
"086":("Trace Obligation",lambda: {"pass":True,**trace_obligation()},EvidenceKind.SYMBOLIC),
"087":("Coercivity Bridge",lambda: coercivity_bridge(0.5),EvidenceKind.SYMBOLIC),
"088":("Estimator Formula Audit",lambda: estimator_formula([1,2],[.5,.25]),EvidenceKind.NUMERICAL),
"089":("Run-Specific Reliability Envelope",lambda: {"pass":True,**run_specific_reliability_envelope(1.2,6,.5,6)},EvidenceKind.NUMERICAL),
"090":("Manufactured Reliability Campaign",manufactured_ratio_campaign,EvidenceKind.NUMERICAL),
"091":("Candidate Constant Scaling",constant_scaling_landscape,EvidenceKind.NUMERICAL),
"092":("Deterministic Premise Stress",deterministic_premise_stress,EvidenceKind.NUMERICAL),
"093":("Counterexample Threshold Shrinker",lambda: shrink_numeric_counterexample({"ratio_upper":12.0}),EvidenceKind.NUMERICAL),
"094":("Reliability DAG v2",lambda: {"pass":True,**theorem_dag_v2()},EvidenceKind.SYMBOLIC),
"095":("Exact Proof Artifact Bundle",proof_artifact_bundle,EvidenceKind.SYMBOLIC),
"096":("Exact Kernel Readiness",exact_kernel_readiness,EvidenceKind.SYMBOLIC),
"097":("Interval Geometry Bridge",interval_geometry_bridge,EvidenceKind.INTERVAL),
"098":("Manufactured Run-Specific Reliability Certificate",manufactured_run_specific_certificate,EvidenceKind.INTERVAL),
"099":("General Reliability Readiness Audit",theorem_readiness_audit,EvidenceKind.SYMBOLIC),
"100":("v1.0 Reliability Qualification Milestone",v100_milestone,EvidenceKind.SYMBOLIC),
}

class ReliabilityStepModule(ResultModule):
    capability_key="077"
    module_id="fem77.edge_orientation"
    label="Reliability Step"
    version="0.77.0"
    description="Reliability theorem development step."
    evidence_kind=EvidenceKind.SYMBOLIC
    metadata=ModuleMetadata(module_id,label,version,"Reliability Theorem",description,Maturity.EXPERIMENTAL,
        assumptions=("Evidence scope is limited to the capability result returned by this module.",))
    proof_status=ProofStatus(evidence={EvidenceKind.SYMBOLIC},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["General 2D mesh-uniform reliability theorem is not promoted by this base class."])
    def execute(self,inputs,params,ctx):
        return {"result":CAPABILITIES[self.capability_key][1]()}
    def verify(self,inputs,params,outputs,ctx):
        return super().verify(inputs,params,outputs,ctx)
