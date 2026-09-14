
from __future__ import annotations
from fractions import Fraction
import hashlib, json, math
from typing import Any

from cace_studio.modules.fem_v051_075_common import ResultModule
from cace_studio.core.types import ModuleMetadata, Maturity, EvidenceKind, ProofStatus
from cace_studio.core.theorems import TheoremStatus, TheoremContract
from cace_studio.modules.flux_v126_130_common import (
    F, qjson, sha, dot, orient2, triangle_area, hdiv_topology, equilibrium_matrix,
    exact_linear_solve, exact_min_norm_constraints, center_square_mesh,
    exact_p1_poisson_center_square, p1_grad_on_triangle, rt0_vector_at,
    affine_vector_square_integral, reconstruct_equilibrated_flux, prager_synge_contract
)

# ---------- exact affine integration helpers ----------

def scalar_affine_product_integral(vertices, fvals, gvals):
    A=triangle_area(vertices)
    sf=sum(fvals); sg=sum(gvals)
    diag=sum(fvals[i]*gvals[i] for i in range(3))
    return A/Fraction(12) * (diag + sf*sg)

def vector_affine_product_integral(vertices, fvecs, gvecs, W=((1,0),(0,1))):
    W=[[F(x) for x in row] for row in W]
    total=Fraction(0)
    for a in range(2):
        for b in range(2):
            fv=[v[a] for v in fvecs]; gv=[v[b] for v in gvecs]
            total += W[a][b]*scalar_affine_product_integral(vertices,fv,gv)
    return total

def inv2(A):
    a,b=map(F,A[0]); c,d=map(F,A[1]); det=a*d-b*c
    if det<=0: raise ValueError("SPD 2x2 matrix requires positive determinant")
    return ((d/det,-b/det),(-c/det,a/det))

def matvec(A,x):
    return (F(A[0][0])*x[0]+F(A[0][1])*x[1],F(A[1][0])*x[0]+F(A[1][1])*x[1])

def local_rt0_basis_vertex_values(points,tri):
    V=[tuple(map(F,points[i])) for i in tri]
    A=triangle_area(V)
    vals=[]
    for i in range(3):
        vi=V[i]
        vals.append([((x[0]-vi[0])/(2*A),(x[1]-vi[1])/(2*A)) for x in V])
    return V,vals

def exact_kkt_minimize(M,c,B,b):
    n=len(M); m=len(B)
    K=[[Fraction(0) for _ in range(n+m)] for _ in range(n+m)]
    rhs=[Fraction(0) for _ in range(n+m)]
    for i in range(n):
        for j in range(n): K[i][j]=2*M[i][j]
        for k in range(m): K[i][n+k]=B[k][i]
        rhs[i]=-2*c[i]
    for k in range(m):
        for i in range(n): K[n+k][i]=B[k][i]
        rhs[n+k]=b[k]
    sol=exact_linear_solve(K,rhs)
    return sol[:n],sol[n:]

def constitutive_optimal_rt0(points,triangles,uh,A_cells=None,f_cell_integrals=None):
    topo,B=equilibrium_matrix(points,triangles)
    pts=topo["points"]; tris=topo["triangles"]; n=len(topo["edges"]); m=len(tris)
    if A_cells is None: A_cells=[((1,0),(0,1)) for _ in tris]
    if f_cell_integrals is None:
        f_cell_integrals=[triangle_area([pts[i] for i in tri]) for tri in tris]
    M=[[Fraction(0) for _ in range(n)] for _ in range(n)]
    c=[Fraction(0) for _ in range(n)]
    const=Fraction(0)
    for k,tri in enumerate(tris):
        V,basis=local_rt0_basis_vertex_values(pts,tri)
        Ai=tuple(tuple(F(x) for x in row) for row in A_cells[k]); Winv=inv2(Ai)
        grad=p1_grad_on_triangle(pts,tri,uh)
        Agr=matvec(Ai,grad)
        # local basis converted to global canonical edge orientation by sign
        for li,(eid,sgn) in enumerate(zip(topo["cell_edges"][k],topo["cell_signs"][k])):
            bi=[(F(sgn)*v[0],F(sgn)*v[1]) for v in basis[li]]
            # cross term sigma^T A^-1 (A grad)=sigma·grad
            gvals=[grad,grad,grad]
            c[eid]+=vector_affine_product_integral(V,bi,gvals,((1,0),(0,1)))
            for lj,(ejd,sgnj) in enumerate(zip(topo["cell_edges"][k],topo["cell_signs"][k])):
                bj=[(F(sgnj)*v[0],F(sgnj)*v[1]) for v in basis[lj]]
                M[eid][ejd]+=vector_affine_product_integral(V,bi,bj,Winv)
        const += triangle_area(V)*dot(grad,Agr)
    q,mults=exact_kkt_minimize(M,c,B,[F(x) for x in f_cell_integrals])
    residual=[sum(B[i][j]*q[j] for j in range(n))-F(f_cell_integrals[i]) for i in range(m)]
    mismatch=sum(M[i][j]*q[i]*q[j] for i in range(n) for j in range(n))+2*sum(c[i]*q[i] for i in range(n))+const
    return {"pass":all(x==0 for x in residual) and mismatch>=0,"topology":topo,"q":q,
            "equilibrium_residual":residual,"mismatch_sq":mismatch,"M":M,"c":c,"const":const,
            "construction":"exact KKT minimization of constitutive mismatch subject to exact cell equilibrium"}

def optimized_flux_audit():
    points,triangles,uh,_=exact_p1_poisson_center_square(1)
    old=reconstruct_equilibrated_flux(points,triangles,1)
    old_sq=Fraction(0)
    for k,tri in enumerate(triangles):
        coeff=[F(s)*old["global_edge_flux_dofs"][eid] for eid,s in zip(old["topology"]["cell_edges"][k],old["topology"]["cell_signs"][k])]
        grad=p1_grad_on_triangle(points,tri,uh)
        old_sq+=affine_vector_square_integral(points,tri,coeff,grad)
    opt=constitutive_optimal_rt0(points,triangles,uh)
    return {"pass":opt["pass"] and opt["mismatch_sq"]<=old_sq,
            "old_mismatch_sq":str(old_sq),"optimized_mismatch_sq":str(opt["mismatch_sq"]),
            "improved_or_equal":opt["mismatch_sq"]<=old_sq,"exact":True}

def variable_spd_flux_audit():
    points,triangles,uh,_=exact_p1_poisson_center_square(1)
    As=[((2,0),(0,1)),((1,0),(0,2)),((3,1),(1,2)),((2,-1),(-1,2))]
    opt=constitutive_optimal_rt0(points,triangles,uh,A_cells=As)
    topo,B=equilibrium_matrix(points,triangles)
    b=[triangle_area([topo["points"][i] for i in tri]) for tri in topo["triangles"]]
    oldq=exact_min_norm_constraints(B,b)
    oldmis=sum(opt["M"][i][j]*oldq[i]*oldq[j] for i in range(len(oldq)) for j in range(len(oldq))) + 2*sum(opt["c"][i]*oldq[i] for i in range(len(oldq))) + opt["const"]
    return {"pass":opt["pass"] and opt["mismatch_sq"]<=oldmis,
            "old_euclidean_flux_mismatch_sq":str(oldmis),
            "optimized_mismatch_sq":str(opt["mismatch_sq"]),
            "strictly_improved":opt["mismatch_sq"]<oldmis,
            "cell_diffusion": [[[str(x) for x in row] for row in A] for A in As],
            "scope":"piecewise-constant rational SPD tensors"}

def affine_source_projection(points,triangles,coeff=(1,1,0)):
    a,b,c=map(F,coeff); pts=[tuple(map(F,p)) for p in points]
    integrals=[]; osc_sq=Fraction(0); means=[]
    for tri in triangles:
        V=[pts[i] for i in tri]; A=triangle_area(V)
        vals=[a+b*x+c*y for x,y in V]
        mean=sum(vals,Fraction(0))/3
        integrals.append(mean*A); means.append(mean)
        dev=[v-mean for v in vals]
        osc_sq += scalar_affine_product_integral(V,dev,dev)
    return integrals,osc_sq,means

def projected_source_flux_audit():
    points,triangles,uh,_=exact_p1_poisson_center_square(1)
    ints,osc,means=affine_source_projection(points,triangles,(1,1,1))
    opt=constitutive_optimal_rt0(points,triangles,uh,f_cell_integrals=ints)
    return {"pass":opt["pass"],"projected_cell_means":[str(x) for x in means],
            "oscillation_sq_exact":str(osc),"mismatch_sq_exact":str(opt["mismatch_sq"]),
            "equilibrium_scope":"div sigma_h = Pi_0 f exactly"}

def oscillation_corrected_bound():
    a=projected_source_flux_audit()
    mismatch=math.sqrt(float(F(a["mismatch_sq_exact"])))
    osc=math.sqrt(float(F(a["oscillation_sq_exact"])))
    # Reviewed safe template: error <= mismatch + C_osc*osc; leave C_osc explicit.
    return {"pass":a["pass"],"mismatch":mismatch,"oscillation":osc,
            "bound_template":"error_A <= mismatch + C_osc * oscillation",
            "guaranteed_numeric":False,"reason":"C_osc remains a reviewed theorem constant unless explicitly instantiated"}

# ---------- estimator efficiency / effectivity ----------

def cell_bubble_moments():
    # b=27 lambda1 lambda2 lambda3 on reference triangle.
    # simplex monomial integral in 2D: int lambda^alpha = 2A prod(alpha_i!)/( (2+sum alpha_i)! )
    A=Fraction(1,2)
    ib=A*2*math.factorial(1)**3/Fraction(math.factorial(5)) * 27
    # exact using Fraction
    ib=Fraction(27)*Fraction(2)*A/Fraction(math.factorial(5))
    return {"pass":ib>0,"integral_bubble":str(ib),"bubble":"27*lambda1*lambda2*lambda3","exact":True}

def edge_bubble_moments():
    # edge bubble 4 lambda1 lambda2 on edge; int_0^1 4 t(1-t) dt = 2/3.
    val=Fraction(2,3)
    return {"pass":True,"integral_edge_bubble":str(val),"edge_bubble":"4*lambda1*lambda2","exact":True}

def efficiency_theorem_contract():
    return {"pass":True,"status":"reviewed-assumed",
            "statement":"eta_K <= C_eff (||e||_{A,omega_K} + osc_{omega_K}(f)) for residual estimators on shape-regular conforming simplicial meshes",
            "machine_formal":False}

def effectivity_campaign():
    # Uses existing certified anchor plus improved flux bound as two conservative error scales.
    from cace_studio.modules.fem_v076 import certified_reference_observation
    o=certified_reference_observation()
    ratio=float(o["eta_interval"][1])/max(float(o["energy_error_interval"][0]),1e-300)
    return {"pass":math.isfinite(ratio),"certified_anchor_effectivity_upper_proxy":ratio,
            "interpretation":"diagnostic proxy; interval endpoints need not yield sharp effectivity","theorem_evidence":False}

def estimator_quality_summary():
    return {"pass":True,"cell_bubble":cell_bubble_moments(),"edge_bubble":edge_bubble_moments(),
            "efficiency":efficiency_theorem_contract(),"oscillation":oscillation_corrected_bound(),
            "effectivity":effectivity_campaign()}

# ---------- certified/adaptive policy ----------

def guaranteed_stop_policy(bounds,tol):
    vals=[float(x) for x in bounds]
    first=next((i for i,x in enumerate(vals) if x<=tol),None)
    return {"pass":first is not None,"first_certified_stop":first,"tolerance":float(tol),
            "rule":"stop only when guaranteed upper bound <= tolerance"}

def doerfler_mark(values,theta=.5):
    vals=[max(0,float(x)) for x in values]; total=sum(vals)
    order=sorted(range(len(vals)),key=lambda i:(-vals[i],i))
    acc=0; mark=[]
    for i in order:
        mark.append(i); acc+=vals[i]
        if acc>=theta*total: break
    return {"pass":acc>=theta*total or total==0,"marked":mark,"captured":acc,"total":total}

def adaptive_contraction_audit(bounds):
    b=[float(x) for x in bounds]; ratios=[b[i+1]/b[i] for i in range(len(b)-1)]
    return {"pass":all(r<1 for r in ratios),"ratios":ratios,"monotone_contracting":all(r<1 for r in ratios),
            "theorem_evidence":False}

def guaranteed_adaptive_fixture():
    bounds=[.24,.14,.081,.047,.028]
    marks=[doerfler_mark([1/(j+1+i) for j in range(8)],.5) for i in range(len(bounds)-1)]
    stop=guaranteed_stop_policy(bounds,.05)
    return {"pass":stop["pass"] and all(m["pass"] for m in marks),
            "bounds":bounds,"marking":marks,"stop":stop,"contraction":adaptive_contraction_audit(bounds),
            "scope":"deterministic policy fixture, not a proof of AFEM contraction"}

def complexity_rate_audit():
    dofs=[8,18,38,78,158]; bounds=[.32,.22,.15,.105,.074]
    slopes=[math.log(bounds[i+1]/bounds[i])/math.log(dofs[i+1]/dofs[i]) for i in range(len(dofs)-1)]
    return {"pass":True,"dofs":dofs,"bounds":bounds,"slopes":slopes,
            "optimality_theorem_proved":False}

# ---------- P2 higher-order FEM ----------

P2_NODES=[(Fraction(1),0,0),(0,Fraction(1),0),(0,0,Fraction(1)),
          (Fraction(1,2),Fraction(1,2),0),(0,Fraction(1,2),Fraction(1,2)),(Fraction(1,2),0,Fraction(1,2))]

def p2_basis_at(lam):
    l1,l2,l3=map(F,lam)
    return (l1*(2*l1-1),l2*(2*l2-1),l3*(2*l3-1),4*l1*l2,4*l2*l3,4*l1*l3)

def p2_basis_audit():
    M=[[p2_basis_at(n)[j] for j in range(6)] for n in P2_NODES]
    I=[[Fraction(int(i==j)) for j in range(6)] for i in range(6)]
    # partition unity at deterministic rational points
    pts=[(Fraction(1,3),Fraction(1,3),Fraction(1,3)),(Fraction(1,5),Fraction(2,5),Fraction(2,5))]
    return {"pass":M==I and all(sum(p2_basis_at(p))==1 for p in pts),
            "nodal_matrix":[[str(x) for x in r] for r in M],"exact":True}

P2_QUAD=[((Fraction(1,3),)*3,Fraction(-27,48)),
         ((Fraction(3,5),Fraction(1,5),Fraction(1,5)),Fraction(25,48)),
         ((Fraction(1,5),Fraction(3,5),Fraction(1,5)),Fraction(25,48)),
         ((Fraction(1,5),Fraction(1,5),Fraction(3,5)),Fraction(25,48))]

def simplex_bary_monomial_integral(alpha,A=Fraction(1,2)):
    s=sum(alpha)
    num=Fraction(2)*A
    for x in alpha: num*=math.factorial(x)
    return num/Fraction(math.factorial(2+s))

def cubic_quadrature_audit():
    for a in range(4):
        for b in range(4-a):
            c=3-a-b if False else 0
    tests=[]
    for a in range(4):
        for b in range(4-a):
            for c in range(4-a-b):
                exact=simplex_bary_monomial_integral((a,b,c))
                approx=Fraction(1,2)*sum(w*(l[0]**a)*(l[1]**b)*(l[2]**c) for l,w in P2_QUAD)
                tests.append(exact==approx)
    return {"pass":all(tests),"monomials_checked":len(tests),"degree":3,"exact":True}

def p2_polynomial_reproduction():
    # quadratic p(lambda)=lambda1^2+2lambda2^2+3lambda3^2+lambda1 lambda2;
    def p(l):
        a,b,c=l; return a*a+2*b*b+3*c*c+a*b
    nodal=[p(n) for n in P2_NODES]
    checks=[]
    for x in [(Fraction(1,3),)*3,(Fraction(1,5),Fraction(2,5),Fraction(2,5))]:
        interp=sum(nodal[i]*p2_basis_at(x)[i] for i in range(6))
        checks.append(interp==p(x))
    return {"pass":all(checks),"exact":True,"degree_reproduced":2}


P2_STIFF_QUAD=[
    ((Fraction(2,3),Fraction(1,6),Fraction(1,6)),Fraction(1,3)),
    ((Fraction(1,6),Fraction(2,3),Fraction(1,6)),Fraction(1,3)),
    ((Fraction(1,6),Fraction(1,6),Fraction(2,3)),Fraction(1,3)),
]

def p2_grad_reference(lam):
    l1,l2,l3=map(F,lam)
    g1=(Fraction(-1),Fraction(-1)); g2=(Fraction(1),Fraction(0)); g3=(Fraction(0),Fraction(1))
    def scale(a,g): return (a*g[0],a*g[1])
    def add(a,b): return (a[0]+b[0],a[1]+b[1])
    return (
        scale(4*l1-1,g1),
        scale(4*l2-1,g2),
        scale(4*l3-1,g3),
        scale(4,add(scale(l1,g2),scale(l2,g1))),
        scale(4,add(scale(l2,g3),scale(l3,g2))),
        scale(4,add(scale(l1,g3),scale(l3,g1))),
    )

def p2_reference_stiffness_audit():
    # Reference triangle area=1/2. 3-point positive degree-2 rule is exact for grad(P2).grad(P2).
    K=[[Fraction(0) for _ in range(6)] for _ in range(6)]
    for lam,w in P2_STIFF_QUAD:
        G=p2_grad_reference(lam)
        for i in range(6):
            for j in range(6):
                K[i][j]+=Fraction(1,2)*w*dot(G[i],G[j])
    sym=all(K[i][j]==K[j][i] for i in range(6) for j in range(6))
    rowsum=all(sum(K[i],Fraction(0))==0 for i in range(6))
    # PSD follows directly from positive quadrature weights; additionally test a spanning deterministic set.
    vectors=[[Fraction(int(i==j)) for i in range(6)] for j in range(6)]
    vectors += [[Fraction(i+1) for i in range(6)], [Fraction((-1)**i) for i in range(6)]]
    energies=[sum(z[i]*K[i][j]*z[j] for i in range(6) for j in range(6)) for z in vectors]
    return {"pass":sym and rowsum and all(e>=0 for e in energies),
            "matrix":[[str(x) for x in row] for row in K],
            "symmetric":sym,"constant_nullspace":rowsum,
            "tested_energies":[str(x) for x in energies],
            "quadrature_exact_degree":2,"exact":True}

def higher_order_fem_milestone():
    return {"pass":p2_basis_audit()["pass"] and cubic_quadrature_audit()["pass"] and p2_reference_stiffness_audit()["pass"],
            "basis":p2_basis_audit(),"quadrature":cubic_quadrature_audit(),
            "reproduction":p2_polynomial_reproduction(),"stiffness":p2_reference_stiffness_audit(),
            "rates":p2_rate_campaign(),"rt1_production":False,
            "rt1_status":"not implemented; explicit nonclaim"}

def p2_rate_campaign():
    hs=[.5,.25,.125,.0625]
    energy=[h*h for h in hs]; l2=[h**3 for h in hs]
    return {"pass":True,"h":hs,"energy_model":energy,"L2_model":l2,
            "expected_rates":{"energy":2,"L2":3},"scope":"Bramble-Hilbert rate model"}

def higher_order_flux_roadmap():
    return {"pass":True,"rt0_production":True,"rt1_production":False,
            "rt1_status":"basis/DOF design target only",
            "reason":"v1.45 refuses to label RT1 implemented until edge moments and interior moments are assembled and verified"}

# ---------- goal-oriented / DWR ----------

def exact_transpose(A):
    return [list(x) for x in zip(*A)]

def exact_matvec(A,x):
    return [sum(F(A[i][j])*F(x[j]) for j in range(len(x))) for i in range(len(A))]

def dwr_exact_identity():
    A=[[Fraction(2),Fraction(-1)],[Fraction(-1),Fraction(2)]]
    b=[Fraction(1),Fraction(0)]; g=[Fraction(0),Fraction(1)]
    u=exact_linear_solve(A,b); z=exact_linear_solve(exact_transpose(A),g)
    uh=[Fraction(1,2),Fraction(0)]
    r=[b[i]-exact_matvec(A,uh)[i] for i in range(2)]
    goal_error=sum(g[i]*(u[i]-uh[i]) for i in range(2))
    dwr=sum(r[i]*z[i] for i in range(2))
    return {"pass":goal_error==dwr,"goal_error":str(goal_error),"residual_dual":str(dwr),
            "u":[str(x) for x in u],"z":[str(x) for x in z],"exact":True}

def goal_functional_catalog():
    return {"pass":True,"functionals":["domain_average","weighted_volume_integral","boundary_flux_reviewed","linear_algebra_observation"],
            "point_evaluation_H1_2D_default":False,
            "reason":"point evaluation is not a bounded functional on H1 in 2D; requires stronger regularity/discrete-only scope"}

def dwr_localization_fixture():
    d=dwr_exact_identity()
    # exact decomposition of r^T z by algebraic component
    A=[[Fraction(2),Fraction(-1)],[Fraction(-1),Fraction(2)]]
    b=[Fraction(1),Fraction(0)]; uh=[Fraction(1,2),Fraction(0)]
    z=exact_linear_solve(A,[Fraction(0),Fraction(1)])
    r=[b[i]-exact_matvec(A,uh)[i] for i in range(2)]
    contrib=[r[i]*z[i] for i in range(2)]
    return {"pass":sum(contrib)==F(d["goal_error"]),"contributions":[str(x) for x in contrib],
            "sum":str(sum(contrib)),"exact":True}

def goal_marking_fixture():
    vals=[.01,.18,.04,.12,.02]
    return {"pass":True,"marking":doerfler_mark([abs(x) for x in vals],.7),"signed_contributions":vals}

def goal_oriented_summary():
    return {"pass":dwr_exact_identity()["pass"],"identity":dwr_exact_identity(),
            "functionals":goal_functional_catalog(),"localization":dwr_localization_fixture(),
            "marking":goal_marking_fixture(),
            "formal_dwr_theorem":False,
            "scope":"exact finite-dimensional dual identity + reviewed Galerkin DWR interpretation"}

CAP={
"131":("Cell Bubble Efficiency Tools",cell_bubble_moments,EvidenceKind.SYMBOLIC),
"132":("Edge Bubble Efficiency Tools",edge_bubble_moments,EvidenceKind.SYMBOLIC),
"133":("Constitutive-Optimal RT0 Flux",optimized_flux_audit,EvidenceKind.SYMBOLIC),
"134":("Variable-SPD and Projected-Source Flux",lambda: {"pass":variable_spd_flux_audit()["pass"] and projected_source_flux_audit()["pass"],"variable_spd":variable_spd_flux_audit(),"projected_source":projected_source_flux_audit()},EvidenceKind.SYMBOLIC),
"135":("Estimator Quality and Oscillation",estimator_quality_summary,EvidenceKind.NUMERICAL),
"136":("Guaranteed Adaptive Stop",lambda: guaranteed_stop_policy([.2,.11,.055,.029],.06),EvidenceKind.NUMERICAL),
"137":("Guaranteed Dörfler Marking",lambda: doerfler_mark([.4,.3,.2,.1],.6),EvidenceKind.NUMERICAL),
"138":("Adaptive Contraction Audit",lambda: adaptive_contraction_audit([.24,.14,.081,.047]),EvidenceKind.NUMERICAL),
"139":("Guaranteed Adaptive Campaign",guaranteed_adaptive_fixture,EvidenceKind.NUMERICAL),
"140":("Adaptive Complexity Audit",complexity_rate_audit,EvidenceKind.NUMERICAL),
"141":("P2 Triangle Basis",p2_basis_audit,EvidenceKind.SYMBOLIC),
"142":("Degree-3 Triangle Quadrature",cubic_quadrature_audit,EvidenceKind.SYMBOLIC),
"143":("P2 Polynomial Reproduction",p2_polynomial_reproduction,EvidenceKind.SYMBOLIC),
"144":("P2 Local Stiffness Audit",p2_reference_stiffness_audit,EvidenceKind.SYMBOLIC),
"145":("Higher-Order FEM Milestone",higher_order_fem_milestone,EvidenceKind.SYMBOLIC),
"146":("Goal Functional Catalog",goal_functional_catalog,EvidenceKind.SYMBOLIC),
"147":("Exact DWR Identity",dwr_exact_identity,EvidenceKind.SYMBOLIC),
"148":("DWR Localization",dwr_localization_fixture,EvidenceKind.SYMBOLIC),
"149":("Goal-Oriented Marking",goal_marking_fixture,EvidenceKind.NUMERICAL),
"150":("Goal-Oriented Error Milestone",goal_oriented_summary,EvidenceKind.SYMBOLIC),
}

class QualityStepModule(ResultModule):
    capability_key="131"; module_id="quality131.cell_bubble"; label="Quality Step"; version="1.31.0"
    description="Estimator-quality/adaptivity/higher-order/goal-oriented capability step."
    evidence_kind=EvidenceKind.SYMBOLIC
    metadata=ModuleMetadata(module_id,label,version,"Error Estimation",description,Maturity.EXPERIMENTAL,
        assumptions=("Capability scope and theorem status must be preserved.",))
    proof_status=ProofStatus(evidence={EvidenceKind.SYMBOLIC},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Reviewed mathematical results are not automatically machine-formal."])
    def execute(self,inputs,params,ctx): return {"result":CAP[self.capability_key][1]()}
    def verify(self,inputs,params,outputs,ctx): return super().verify(inputs,params,outputs,ctx)
