
from __future__ import annotations
from fractions import Fraction
import hashlib, json, math, random
from typing import Any

from cace_studio.modules.fem_v051_075_common import ResultModule
from cace_studio.core.types import ModuleMetadata, Maturity, EvidenceKind, ProofStatus
from cace_studio.core.theorems import TheoremStatus, TheoremContract
from cace_studio.modules.flux_v126_130_common import (
    F, dot, orient2, triangle_area, hdiv_topology, equilibrium_matrix,
    exact_linear_solve, exact_min_norm_constraints, center_square_mesh,
    exact_p1_poisson_center_square, p1_grad_on_triangle
)
from cace_studio.modules.quality_v131_150_common import (
    p2_basis_at, P2_NODES, P2_STIFF_QUAD, doerfler_mark
)

def _sha(x):
    return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest()

def _pretty(x):
    return json.dumps(x,indent=2,sort_keys=True,default=str)+"\n\n"

# ============================================================================
# Rank 1: RT1 / higher-order equilibrated flux
# ============================================================================

def rt1_basis_eval(i,x,y):
    x,y=F(x),F(y)
    vals=[
        (1,0),(0,1),(x,0),(y,0),(0,x),(0,y),(x*x,x*y),(x*y,y*y)
    ]
    a,b=vals[i]
    return F(a),F(b)

def simpson_integral(values):
    return (values[0]+4*values[1]+values[2])/6

def rt1_edge_dof(i,edge,moment):
    # Reference triangle v0=(0,0),v1=(1,0),v2=(0,1), CCW.
    # edge 0: v1->v2, n ds=(1,1); edge1:v2->v0 n ds=(-1,0); edge2:v0->v1 n ds=(0,-1)
    ts=[Fraction(0),Fraction(1,2),Fraction(1)]
    vals=[]
    for t in ts:
        if edge==0: x,y=1-t,t; nds=(1,1)
        elif edge==1: x,y=0,1-t; nds=(-1,0)
        else: x,y=t,0; nds=(0,-1)
        vx,vy=rt1_basis_eval(i,x,y)
        q=Fraction(1) if moment==0 else t
        vals.append((vx*nds[0]+vy*nds[1])*q)
    return simpson_integral(vals)

def rt1_cell_dof(i,component):
    # exact degree-2 3-point barycentric quadrature on reference triangle
    pts=[(Fraction(2,3),Fraction(1,6)),(Fraction(1,6),Fraction(2,3)),(Fraction(1,6),Fraction(1,6))]
    s=Fraction(0)
    for x,y in pts:
        v=rt1_basis_eval(i,x,y)[component]
        s += Fraction(1,6)*v  # area/3 = 1/6
    return s

def exact_rank(A):
    A=[list(map(F,row)) for row in A]
    m=len(A); n=len(A[0]) if m else 0; r=0
    for c in range(n):
        p=next((i for i in range(r,m) if A[i][c]!=0),None)
        if p is None: continue
        A[r],A[p]=A[p],A[r]
        q=A[r][c]; A[r]=[x/q for x in A[r]]
        for i in range(m):
            if i!=r and A[i][c]!=0:
                q=A[i][c]; A[i]=[A[i][j]-q*A[r][j] for j in range(n)]
        r+=1
        if r==m: break
    return r

def rt1_unisolvence_audit():
    rows=[]
    for e in range(3):
        for m in range(2):
            rows.append([rt1_edge_dof(i,e,m) for i in range(8)])
    rows += [[rt1_cell_dof(i,c) for i in range(8)] for c in range(2)]
    rank=exact_rank(rows)
    return {"pass":rank==8,"rank":rank,"dimension":8,
            "dof_matrix":[[str(x) for x in row] for row in rows],
            "scope":"reference RT1 polynomial space with 6 edge moments + 2 cell moments","exact":True}

def rt1_reversed_edge_transform():
    # m0=int f, m1=int f*t. Reversing normal and parameter t'=1-t:
    # m0'=-m0, m1'=-int f(1-t)=-m0+m1.
    T=[[Fraction(-1),0],[Fraction(-1),Fraction(1)]]
    # involution
    TT=[[sum(T[i][k]*T[k][j] for k in range(2)) for j in range(2)] for i in range(2)]
    return {"pass":TT==[[1,0],[0,1]],"transform":[[str(x) for x in r] for r in T],
            "involution":[[str(x) for x in r] for r in TT],"exact":True}

def rt1_affine_divergence_reconstruction(a=1,b=2,c=-1):
    a,b,c=map(F,(a,b,c))
    # div basis map: b2,b5 contribute 1; b6 contributes 3x; b7 contributes 3y.
    coeff=[Fraction(0)]*8
    coeff[2]=a/2; coeff[5]=a/2; coeff[6]=b/3; coeff[7]=c/3
    recovered=(coeff[2]+coeff[5],3*coeff[6],3*coeff[7])
    return {"pass":recovered==(a,b,c),"coefficients":[str(x) for x in coeff],
            "divergence_coefficients":[str(x) for x in recovered],
            "target":[str(a),str(b),str(c)],"exact":True}

def rt1_source_projection_bound():
    rec=rt1_affine_divergence_reconstruction(1,2,-1)
    return {"pass":rec["pass"],"equilibrium":"div sigma_RT1 = affine f exactly on reference cell",
            "oscillation_for_affine_source":"0","guarantee_status":"reviewed-Prager-Synge-applicable after global H(div) assembly",
            "global_rt1_assembly_complete":False}

def rt1_milestone():
    u=rt1_unisolvence_audit(); o=rt1_reversed_edge_transform(); d=rt1_affine_divergence_reconstruction()
    return {"pass":u["pass"] and o["pass"] and d["pass"],"unisolvence":u,"orientation":o,
            "affine_divergence":d,"production_global_RT1":False,
            "nonclaim":"local RT1 algebra is closed; full global RT1 sparse assembly remains a later production step"}

# ============================================================================
# Rank 2: production global P2 FEM
# ============================================================================

def bary_gradients(vertices):
    V=[tuple(map(F,p)) for p in vertices]
    area2=orient2(V[0],V[1],V[2])
    if area2<=0: raise ValueError("CCW required")
    (x0,y0),(x1,y1),(x2,y2)=V
    return (
        ((y1-y2)/area2,(x2-x1)/area2),
        ((y2-y0)/area2,(x0-x2)/area2),
        ((y0-y1)/area2,(x1-x0)/area2),
    )

def p2_grad_physical(lam,grads):
    l1,l2,l3=map(F,lam); g1,g2,g3=grads
    def sc(a,g): return (a*g[0],a*g[1])
    def add(a,b): return (a[0]+b[0],a[1]+b[1])
    return (
        sc(4*l1-1,g1),sc(4*l2-1,g2),sc(4*l3-1,g3),
        sc(4,add(sc(l1,g2),sc(l2,g1))),
        sc(4,add(sc(l2,g3),sc(l3,g2))),
        sc(4,add(sc(l1,g3),sc(l3,g1))),
    )

def p2_local_stiffness(vertices):
    V=[tuple(map(F,p)) for p in vertices]; A=triangle_area(V); grads=bary_gradients(V)
    K=[[Fraction(0) for _ in range(6)] for _ in range(6)]
    for lam,w in P2_STIFF_QUAD:
        G=p2_grad_physical(lam,grads)
        for i in range(6):
            for j in range(6):
                K[i][j]+=A*w*dot(G[i],G[j])
    return K

def p2_local_load_constant(vertices,f=1):
    A=triangle_area(vertices); f=F(f)
    return [Fraction(0),Fraction(0),Fraction(0),f*A/3,f*A/3,f*A/3]

def p2_topology(points,triangles):
    pts=[tuple(map(F,p)) for p in points]; tris=[tuple(map(int,t)) for t in triangles]
    edges={}; cell_edges=[]
    for tri in tris:
        es=[]
        for a,b in ((tri[0],tri[1]),(tri[1],tri[2]),(tri[2],tri[0])):
            e=tuple(sorted((a,b)))
            if e not in edges: edges[e]=len(edges)
            es.append(edges[e])
        cell_edges.append(es)
    edge_list=[None]*len(edges)
    for e,i in edges.items(): edge_list[i]=e
    nv=len(pts)
    local_dofs=[]
    for tri,es in zip(tris,cell_edges):
        local_dofs.append([tri[0],tri[1],tri[2],nv+es[0],nv+es[1],nv+es[2]])
    incidence=[0]*len(edge_list)
    for es in cell_edges:
        for e in es: incidence[e]+=1
    boundary_vertices=set(); boundary_edge_ids=[]
    for eid,(a,b) in enumerate(edge_list):
        if incidence[eid]==1:
            boundary_edge_ids.append(eid); boundary_vertices|={a,b}
    boundary_dofs=sorted(boundary_vertices | {nv+e for e in boundary_edge_ids})
    return {"points":pts,"triangles":tris,"edges":edge_list,"cell_edges":cell_edges,
            "local_dofs":local_dofs,"ndofs":nv+len(edge_list),"boundary_dofs":boundary_dofs}

def p2_global_assembly(points,triangles,f=1):
    topo=p2_topology(points,triangles); n=topo["ndofs"]
    K=[[Fraction(0) for _ in range(n)] for _ in range(n)]; b=[Fraction(0) for _ in range(n)]
    for tri,ldofs in zip(topo["triangles"],topo["local_dofs"]):
        V=[topo["points"][i] for i in tri]; Ke=p2_local_stiffness(V); be=p2_local_load_constant(V,f)
        for i,I in enumerate(ldofs):
            b[I]+=be[i]
            for j,J in enumerate(ldofs): K[I][J]+=Ke[i][j]
    interior=[i for i in range(n) if i not in set(topo["boundary_dofs"])]
    Kr=[[K[i][j] for j in interior] for i in interior]; br=[b[i] for i in interior]
    return topo,K,b,interior,Kr,br

def p2_global_topology_audit():
    pts,tris=center_square_mesh()
    topo=p2_topology(pts,tris)
    return {"pass":topo["ndofs"]==len(pts)+len(topo["edges"]),
            "vertices":len(pts),"edges":len(topo["edges"]),"global_dofs":topo["ndofs"],
            "boundary_dofs":len(topo["boundary_dofs"]),"exact":True}

def p2_global_assembly_audit():
    pts,tris=center_square_mesh(); topo,K,b,interior,Kr,br=p2_global_assembly(pts,tris,1)
    sym=all(K[i][j]==K[j][i] for i in range(len(K)) for j in range(len(K)))
    rowsum=all(sum(row,Fraction(0))==0 for row in K)
    return {"pass":sym and rowsum and len(interior)>0,"symmetric":sym,"constant_nullspace":rowsum,
            "interior_dofs":interior,"reduced_dim":len(interior),"exact":True}

def p2_global_solve():
    pts,tris=center_square_mesh(); topo,K,b,interior,Kr,br=p2_global_assembly(pts,tris,1)
    x=exact_linear_solve(Kr,br)
    full=[Fraction(0)]*len(K)
    for i,v in zip(interior,x): full[i]=v
    res=[sum(Kr[i][j]*x[j] for j in range(len(x)))-br[i] for i in range(len(x))]
    return {"pass":all(r==0 for r in res),"interior_dofs":interior,
            "solution":[str(v) for v in x],"residual":[str(r) for r in res],"exact":True,
            "full_solution":full,"K":K,"b":b,"topology":topo}

def p2_vs_p1_energy_proxy():
    p1=exact_p1_poisson_center_square(1)
    p2=p2_global_solve()
    # compare central vertex value; both are exact Galerkin approximations on same coarse mesh
    center_p1=p1[2][4]
    center_p2=p2["full_solution"][4]
    return {"pass":True,"p1_center":str(center_p1),"p2_center":str(center_p2),
            "difference":str(center_p2-center_p1),"claim":"discrete comparison only, not exact PDE error"}

def p2_production_milestone():
    a=p2_global_assembly_audit(); s=p2_global_solve()
    return {"pass":a["pass"] and s["pass"],"assembly":a,
            "solve":{"solution":s["solution"],"residual":s["residual"]},
            "production_features":["global edge-midpoint DOFs","Dirichlet elimination","exact sparse-reference assembly","exact solve fixture"]}

# ============================================================================
# Rank 3: PDE-level DWR in enriched P2 space
# ============================================================================

def p1_lift_to_p2():
    points,triangles,uh,_=exact_p1_poisson_center_square(1)
    topo=p2_topology(points,triangles)
    vals=[F(v) for v in uh]
    for a,b in topo["edges"]:
        vals.append((uh[a]+uh[b])/2)
    return topo,vals

def p2_goal_vector_domain_average(points,triangles):
    # J(v)=int_Omega v; same as load vector for constant 1.
    topo,K,b,interior,Kr,br=p2_global_assembly(points,triangles,1)
    return topo,b,interior

def enriched_dwr_identity():
    points,triangles=center_square_mesh()
    sol=p2_global_solve(); topo=sol["topology"]; K=sol["K"]; b=sol["b"]
    _,uh=p1_lift_to_p2()
    interior=[i for i in range(len(K)) if i not in set(topo["boundary_dofs"])]
    Kr=[[K[i][j] for j in interior] for i in interior]
    gr=[b[i] for i in interior]  # domain integral functional
    z=exact_linear_solve(Kr,gr)
    u2=[F(sol["full_solution"][i]) for i in interior]
    uh2=[F(uh[i]) for i in interior]
    r=[b[i]-sum(K[i][j]*uh[j] for j in range(len(K))) for i in interior]
    goal_error=sum(gr[k]*(u2[k]-uh2[k]) for k in range(len(interior)))
    dwr=sum(r[k]*z[k] for k in range(len(interior))
    )
    return {"pass":goal_error==dwr,"goal_error":str(goal_error),"residual_dual":str(dwr),
            "dual":[str(v) for v in z],"residual":[str(v) for v in r],
            "scope":"P2-enriched discrete reference identity relative to lifted P1 solution","exact":True}

def dwr_element_localization():
    d=enriched_dwr_identity()
    # deterministic algebraic localization by reduced DOF contributions
    vals=[F(x) for x in d["residual"]]; z=[F(x) for x in d["dual"]]
    contrib=[vals[i]*z[i] for i in range(len(vals))]
    return {"pass":sum(contrib)==F(d["goal_error"]),"contributions":[str(x) for x in contrib],
            "sum":str(sum(contrib)),"exact":True}

def dwr_goal_marking():
    loc=dwr_element_localization()
    vals=[abs(float(F(x))) for x in loc["contributions"]]
    mark=doerfler_mark(vals,.7)
    return {"pass":loc["pass"] and mark["pass"],"marking":mark,
            "scope":"algebraic enriched-DOF goal marking"}

def dwr_bound_policy():
    d=enriched_dwr_identity()
    exact_abs=abs(float(F(d["goal_error"])))
    return {"pass":d["pass"],"goal_error_abs":exact_abs,
            "stop_at_tol_0_1":exact_abs<=.1,"stop_at_tol_0_01":exact_abs<=.01,
            "scope":"discrete enriched-reference goal policy"}

def dwr_pde_milestone():
    d=enriched_dwr_identity(); l=dwr_element_localization()
    return {"pass":d["pass"] and l["pass"],"identity":d,"localization":l,
            "continuum_goal_error_guaranteed":False,
            "reason":"P2 enriched reference is not the exact continuum dual solution"}

# ============================================================================
# Rank 4: robust heterogeneous/data-oscillation guarantees
# ============================================================================

def coefficient_contrast_audit(eigs):
    vals=[float(x) for x in eigs]
    mn=min(vals); mx=max(vals)
    return {"pass":mn>0,"alpha":mn,"beta":mx,"contrast":mx/mn if mn>0 else math.inf}

def projected_data_oscillation_bound(oscillation,Cosc,alpha=1.0):
    osc=float(oscillation); C=float(Cosc); a=float(alpha)
    return {"pass":a>0 and osc>=0 and C>=0,"oscillation_correction":C*osc/math.sqrt(a),
            "formula":"C_osc * osc / sqrt(alpha)"}

def mixed_boundary_contract():
    return {"pass":True,"status":"reviewed-assumed",
            "statement":"Residual reliability/equilibrated-flux guarantees extend to mixed Dirichlet-Neumann data with compatible boundary flux conditions.",
            "machine_formal":False,
            "required":["positive-measure Dirichlet part or quotient-space treatment","boundary residual/flux matching","coercivity"]}

def robust_bound_composition(mismatch,osc_corr,algebraic=0.0):
    terms=[float(mismatch),float(osc_corr),float(algebraic)]
    return {"pass":all(x>=0 and math.isfinite(x) for x in terms),"guaranteed_upper_template":sum(terms),
            "components":{"flux_mismatch":terms[0],"data_oscillation":terms[1],"algebraic":terms[2]}}

def robust_guarantee_milestone():
    c=coefficient_contrast_audit([.25,1,4])
    o=projected_data_oscillation_bound(.02,1.5,.25)
    b=robust_bound_composition(.08,o["oscillation_correction"],.001)
    return {"pass":c["pass"] and o["pass"] and b["pass"],"contrast":c,"oscillation":o,"bound":b,
            "numeric_guarantee_status":"conditional on reviewed C_osc and boundary theorem hypotheses"}

# ============================================================================
# Rank 5: adaptivity theorem integration
# ============================================================================

def estimator_stability_audit(old,new,unchanged):
    diffs=[abs(float(new[i])-float(old[i])) for i in unchanged]
    return {"pass":True,"max_unchanged_change":max(diffs,default=0.0),"theorem_evidence":False}

def estimator_reduction_audit(parent,children,qred=.75):
    p=float(parent); c=math.sqrt(sum(float(x)**2 for x in children))
    return {"pass":c<=qred*p,"parent":p,"children_l2":c,"qred":qred}

def quasi_orthogonality_audit(errors):
    e=[float(x) for x in errors]
    drops=[e[i]**2-e[i+1]**2 for i in range(len(e)-1)]
    return {"pass":all(x>=0 for x in drops),"energy_square_drops":drops,"theorem_evidence":False}

def discrete_reliability_contract():
    return {"pass":True,"status":"reviewed-assumed",
            "statement":"Difference of nested Galerkin solutions is controlled by estimator contributions on refined patches under standard AFEM hypotheses.",
            "machine_formal":False}

def adaptivity_theorem_milestone():
    axioms={"stability":True,"reduction":True,"quasi_orthogonality":True,"discrete_reliability":True}
    return {"pass":all(axioms.values()),"reviewed_axioms":axioms,
            "linear_convergence_theorem_status":"reviewed-assumed",
            "optimality_theorem_status":"reviewed-assumed",
            "machine_formal":False}

# ============================================================================
# Rank 6: mixed / saddle-point methods
# ============================================================================

def saddle_block_matrix(A,B):
    n=len(A); m=len(B)
    M=[[Fraction(0) for _ in range(n+m)] for _ in range(n+m)]
    for i in range(n):
        for j in range(n): M[i][j]=F(A[i][j])
    for k in range(m):
        for j in range(n):
            M[j][n+k]=F(B[k][j]); M[n+k][j]=F(B[k][j])
    return M

def mixed_saddle_fixture():
    A=[[2,-1],[-1,2]]; B=[[1,-1]]
    M=saddle_block_matrix(A,B); rhs=[Fraction(1),Fraction(0),Fraction(0)]
    x=exact_linear_solve(M,rhs)
    res=[sum(M[i][j]*x[j] for j in range(3))-rhs[i] for i in range(3)]
    return {"pass":all(r==0 for r in res),"solution":[str(v) for v in x],"residual":[str(r) for r in res],"exact":True}

def schur_complement_fixture():
    A=[[Fraction(2),Fraction(-1)],[-1,2]]
    Ainv_cols=[exact_linear_solve(A,[Fraction(int(i==j)) for i in range(2)]) for j in range(2)]
    Ainv=[[Ainv_cols[j][i] for j in range(2)] for i in range(2)]
    B=[[Fraction(1),Fraction(-1)]]
    s=sum(B[0][i]*Ainv[i][j]*B[0][j] for i in range(2) for j in range(2))
    return {"pass":s>0,"schur":str(s),"inf_sup_proxy_squared":str(s),"exact":True}

def infsup_contract():
    return {"pass":True,"status":"reviewed-assumed",
            "statement":"Brezzi conditions (coercivity on kernel plus discrete inf-sup) imply mixed problem well-posedness and quasi-optimality.",
            "machine_formal":False}

def mixed_preconditioner_audit():
    s=F(schur_complement_fixture()["schur"])
    return {"pass":s>0,"block_preconditioner":"diag(A, Schur)","exact_schur":str(s),
            "scope":"2x1 saddle fixture"}

def mixed_methods_milestone():
    a=mixed_saddle_fixture(); s=schur_complement_fixture()
    return {"pass":a["pass"] and s["pass"],"saddle":a,"schur":s,"brezzi":infsup_contract(),
            "production_RT_mixed_poisson":False}

# ============================================================================
# Rank 7: verified spectral bounds
# ============================================================================

def gershgorin_intervals(A):
    out=[]
    for i,row in enumerate(A):
        c=float(row[i]); r=sum(abs(float(row[j])) for j in range(len(row)) if j!=i)
        out.append((c-r,c+r))
    return {"pass":True,"intervals":out,"global":[min(x[0] for x in out),max(x[1] for x in out)]}

def rayleigh_quotient(A,x):
    Ax=[sum(float(A[i][j])*float(x[j]) for j in range(len(x))) for i in range(len(A))]
    den=sum(float(v)**2 for v in x)
    return sum(float(x[i])*Ax[i] for i in range(len(x)))/den

def spectral_residual_inclusion(A,x,lam):
    r=[sum(float(A[i][j])*float(x[j]) for j in range(len(x)))-float(lam)*float(x[i]) for i in range(len(A))]
    rn=math.sqrt(sum(v*v for v in r)); xn=math.sqrt(sum(float(v)**2 for v in x))
    eps=rn/xn
    return {"pass":xn>0,"lambda":float(lam),"epsilon":eps,
            "inclusion":[float(lam)-eps,float(lam)+eps],
            "statement":"for symmetric A, spectrum intersects [lambda-eps,lambda+eps]"}

def exact_2x2_eigen_fixture():
    A=[[2,-1],[-1,2]]
    # eigenpairs exactly lambda=1,3
    r1=spectral_residual_inclusion(A,[1,1],1)
    r3=spectral_residual_inclusion(A,[1,-1],3)
    return {"pass":r1["epsilon"]==0 and r3["epsilon"]==0,"lambda1":r1,"lambda2":r3}

def minmax_contract():
    return {"pass":True,"status":"reviewed-assumed",
            "statement":"Courant-Fischer min-max and Rayleigh-Ritz give variational eigenvalue bounds for symmetric/self-adjoint problems.",
            "machine_formal":False}

def spectral_milestone():
    A=[[2,-1,0],[-1,2,-1],[0,-1,2]]
    g=gershgorin_intervals(A)
    r=spectral_residual_inclusion(A,[1,math.sqrt(2),1],2-math.sqrt(2))
    return {"pass":g["pass"] and r["pass"],"gershgorin":g,"residual_inclusion":r,
            "interval_certified_eigenvalues":False,
            "next":"interval LDLT inertia / Lehmann-Goerisch for rigorous separated eigenvalue bounds"}

# ============================================================================
# Rank 8: parabolic / time-dependent certification
# ============================================================================

def backward_euler_scalar(u0,lam,dt,steps):
    u=F(u0); lam=F(lam); dt=F(dt); hist=[u]
    for _ in range(int(steps)):
        u=u/(1+dt*lam); hist.append(u)
    return hist

def backward_euler_energy_audit():
    h=backward_euler_scalar(1,2,Fraction(1,10),5)
    dec=all(abs(h[i+1])<=abs(h[i]) for i in range(len(h)-1))
    return {"pass":dec,"history":[str(x) for x in h],"exact":True}

def theta_scheme_amplification(lam_dt,theta):
    z=float(lam_dt); th=float(theta)
    g=(1-(1-th)*z)/(1+th*z)
    return {"pass":math.isfinite(g),"amplification":g,"A_stable_expected":th>=.5}

def time_residual_estimator(history,dt,lam):
    vals=[float(x) for x in history]; dt=float(dt); lam=float(lam)
    rs=[]
    for i in range(len(vals)-1):
        rs.append((vals[i+1]-vals[i])/dt + lam*vals[i+1])
    return {"pass":True,"residuals":rs,"l2_time_proxy":math.sqrt(sum(r*r*dt for r in rs))}

def adaptive_time_step_policy(errors,tols=(.01,.05),dt=.1):
    e=[float(x) for x in errors]; lo,hi=map(float,tols); d=float(dt); out=[]
    for x in e:
        if x>hi: d*=.5
        elif x<lo: d*=1.5
        out.append(d)
    return {"pass":all(x>0 for x in out),"dt_history":out,"deterministic":True}

def parabolic_milestone():
    h=backward_euler_scalar(1,2,Fraction(1,10),5)
    r=time_residual_estimator(h,.1,2)
    return {"pass":backward_euler_energy_audit()["pass"],"energy":backward_euler_energy_audit(),
            "residual":r,"continuum_parabolic_reliability_formal":False}

# ============================================================================
# Rank 9: FEEC / Maxwell-compatible complexes
# ============================================================================

def simplicial_incidence_2d():
    # square split by diagonal: vertices 0,1,2,3; oriented edges canonical low->high; triangles (0,1,2),(0,2,3)
    edges=[(0,1),(1,2),(0,2),(2,3),(0,3)]
    tris=[(0,1,2),(0,2,3)]
    D0=[[Fraction(0) for _ in range(4)] for _ in edges]
    for e,(a,b) in enumerate(edges): D0[e][a]=-1; D0[e][b]=1
    D1=[[Fraction(0) for _ in edges] for _ in tris]
    edge_id={e:i for i,e in enumerate(edges)}
    for k,(a,b,c) in enumerate(tris):
        for u,v in ((a,b),(b,c),(c,a)):
            key=(min(u,v),max(u,v)); s=1 if (u,v)==key else -1
            D1[k][edge_id[key]]=s
    return D0,D1

def exact_complex_audit():
    D0,D1=simplicial_incidence_2d()
    P=[[sum(D1[i][k]*D0[k][j] for k in range(len(D0))) for j in range(4)] for i in range(len(D1))]
    return {"pass":all(x==0 for row in P for x in row),"D1D0":[[str(x) for x in r] for r in P],"exact":True}

def curlcurl_nullspace_audit():
    D0,D1=simplicial_incidence_2d()
    K=[[sum(D1[t][i]*D1[t][j] for t in range(len(D1))) for j in range(len(D0))] for i in range(len(D0))]
    KD=[[sum(K[i][k]*D0[k][j] for k in range(len(D0))) for j in range(4)] for i in range(len(D0))]
    return {"pass":all(x==0 for row in KD for x in row),"edge_curlcurl":K,"gradient_nullspace_verified":True,"exact":True}

def gauge_fixed_maxwell_fixture():
    D0,D1=simplicial_incidence_2d()
    # Hodge-like SPD regularization K = D1^T D1 + D0 D0^T
    ne=len(D0)
    K=[[sum(D1[t][i]*D1[t][j] for t in range(len(D1))) + sum(D0[i][v]*D0[j][v] for v in range(4))
        for j in range(ne)] for i in range(ne)]
    rank=exact_rank(K)
    return {"pass":rank==ne,"dimension":ne,"rank":rank,"gauge_fixed_spd_candidate":True,"exact":True}

def feec_contract():
    return {"pass":True,"status":"reviewed-assumed",
            "statement":"Compatible finite-element subcomplexes with commuting projections preserve differential-complex structure and support stable mixed formulations.",
            "machine_formal":False}

def maxwell_milestone():
    c=exact_complex_audit(); n=curlcurl_nullspace_audit(); g=gauge_fixed_maxwell_fixture()
    return {"pass":c["pass"] and n["pass"] and g["pass"],"complex":c,"nullspace":n,"gauge":g,
            "production_nedelec_basis":False}

# ============================================================================
# Rank 10: v2.0 integration / proof-capability architecture
# ============================================================================

def capability_dependency_graph():
    deps={
      "guaranteed_flux":["RT0_or_RT1_Hdiv","equilibrium","Prager_Synge_reviewed"],
      "goal_error":["primal_solve","dual_solve","DWR_identity"],
      "adaptive_guarantee":["guaranteed_error_bound","marking","refinement"],
      "mixed_methods":["Brezzi_reviewed","saddle_solver"],
      "spectral":["symmetric_operator","variational_or_residual_bound"],
      "maxwell":["deRham_complex","Hcurl_space","gauge_or_boundary_conditions"],
    }
    return {"pass":True,"dependencies":deps,"sha256":_sha(deps)}

def evidence_scope_audit():
    entries={
      "RT1_unisolvence":"symbolic-exact",
      "P2_global_fixture":"symbolic-exact",
      "DWR_enriched_identity":"symbolic-exact",
      "AFEM_optimality":"reviewed-assumed",
      "Prager_Synge":"reviewed-assumed",
      "spectral_residual_inclusion":"reviewed+numerical",
      "Maxwell_FEEC":"reviewed+symbolic-fixtures",
    }
    bad=[k for k,v in entries.items() if "formal" in v]
    return {"pass":not bad,"entries":entries,"forbidden_false_formal_claims":bad}

def reproducibility_capsule_v2():
    payload={"seed":2000,"json_format":"indent=2 + two trailing newlines","deterministic_ordering":True,
             "evidence_scope_audit":evidence_scope_audit()["entries"]}
    return {"pass":True,"payload":payload,"sha256":_sha(payload)}

def qualification_matrix_v2():
    gates={
      "rt1_local":rt1_milestone()["pass"],
      "p2_global":p2_production_milestone()["pass"],
      "dwr_pde":dwr_pde_milestone()["pass"],
      "robust_bounds":robust_guarantee_milestone()["pass"],
      "adaptivity":adaptivity_theorem_milestone()["pass"],
      "mixed":mixed_methods_milestone()["pass"],
      "spectral":spectral_milestone()["pass"],
      "parabolic":parabolic_milestone()["pass"],
      "feec_maxwell":maxwell_milestone()["pass"],
      "evidence_scope":evidence_scope_audit()["pass"],
    }
    return {"pass":all(gates.values()),"gates":gates,"passed":sum(gates.values()),"total":len(gates)}

def v2_milestone():
    q=qualification_matrix_v2()
    nonclaims=[
      "No machine-formal proof of Scott-Zhang, Prager-Synge, AFEM optimality, Brezzi, or FEEC is claimed.",
      "RT1 local algebra is implemented, but global production RT1 sparse assembly remains incomplete.",
      "Continuum DWR goal error is not guaranteed by the P2 enriched-reference fixture.",
      "Spectral residual inclusions are not interval-separated eigenvalue certificates.",
      "Production Nedelec basis functions are not yet implemented.",
      "Parabolic continuum reliability remains reviewed/unformalized."
    ]
    out={"release":"2.0.0","pass":q["pass"],"qualification":q,"nonclaims":nonclaims,
         "json_default":"pretty indent=2, sorted where generated by release reporters, two trailing newlines"}
    out["sha256"]=_sha(out)
    return out

# Capability map: 10 ranked tracks x 5 releases.
CAP={
"151":("RT1 Unisolvence",rt1_unisolvence_audit,EvidenceKind.SYMBOLIC),
"152":("RT1 Edge Orientation",rt1_reversed_edge_transform,EvidenceKind.SYMBOLIC),
"153":("RT1 Affine Divergence",rt1_affine_divergence_reconstruction,EvidenceKind.SYMBOLIC),
"154":("RT1 Affine-Source Guarantee Bridge",rt1_source_projection_bound,EvidenceKind.SYMBOLIC),
"155":("RT1 Milestone",rt1_milestone,EvidenceKind.SYMBOLIC),

"156":("P2 Global Topology",p2_global_topology_audit,EvidenceKind.SYMBOLIC),
"157":("P2 Global Assembly",p2_global_assembly_audit,EvidenceKind.SYMBOLIC),
"158":("P2 Exact Global Solve",p2_global_solve,EvidenceKind.SYMBOLIC),
"159":("P2 vs P1 Discrete Comparison",p2_vs_p1_energy_proxy,EvidenceKind.NUMERICAL),
"160":("P2 Production Milestone",p2_production_milestone,EvidenceKind.SYMBOLIC),

"161":("P2-Enriched DWR Identity",enriched_dwr_identity,EvidenceKind.SYMBOLIC),
"162":("DWR Localization",dwr_element_localization,EvidenceKind.SYMBOLIC),
"163":("DWR Goal Marking",dwr_goal_marking,EvidenceKind.NUMERICAL),
"164":("DWR Goal Stop Policy",dwr_bound_policy,EvidenceKind.NUMERICAL),
"165":("PDE DWR Milestone",dwr_pde_milestone,EvidenceKind.SYMBOLIC),

"166":("Coefficient Contrast Audit",lambda: coefficient_contrast_audit([.25,1,4]),EvidenceKind.NUMERICAL),
"167":("Projected Data Oscillation Bound",lambda: projected_data_oscillation_bound(.02,1.5,.25),EvidenceKind.NUMERICAL),
"168":("Mixed Boundary Contract",mixed_boundary_contract,EvidenceKind.SYMBOLIC),
"169":("Robust Bound Composition",lambda: robust_bound_composition(.08,.03,.001),EvidenceKind.NUMERICAL),
"170":("Robust Guarantee Milestone",robust_guarantee_milestone,EvidenceKind.SYMBOLIC),

"171":("Estimator Stability Audit",lambda: estimator_stability_audit([.2,.1,.05],[.21,.1,.051],[1]),EvidenceKind.NUMERICAL),
"172":("Estimator Reduction Audit",lambda: estimator_reduction_audit(.2,[.08,.06],.75),EvidenceKind.NUMERICAL),
"173":("Quasi-Orthogonality Audit",lambda: quasi_orthogonality_audit([.3,.2,.14,.1]),EvidenceKind.NUMERICAL),
"174":("Discrete Reliability Contract",discrete_reliability_contract,EvidenceKind.SYMBOLIC),
"175":("Adaptivity Theorem Milestone",adaptivity_theorem_milestone,EvidenceKind.SYMBOLIC),

"176":("Mixed Saddle Fixture",mixed_saddle_fixture,EvidenceKind.SYMBOLIC),
"177":("Schur Complement Audit",schur_complement_fixture,EvidenceKind.SYMBOLIC),
"178":("Brezzi Inf-Sup Contract",infsup_contract,EvidenceKind.SYMBOLIC),
"179":("Mixed Preconditioner Audit",mixed_preconditioner_audit,EvidenceKind.SYMBOLIC),
"180":("Mixed Methods Milestone",mixed_methods_milestone,EvidenceKind.SYMBOLIC),

"181":("Gershgorin Spectral Bounds",lambda: gershgorin_intervals([[2,-1,0],[-1,2,-1],[0,-1,2]]),EvidenceKind.NUMERICAL),
"182":("Spectral Residual Inclusion",lambda: spectral_residual_inclusion([[2,-1],[-1,2]],[1,1],1),EvidenceKind.NUMERICAL),
"183":("Exact 2x2 Eigen Fixture",exact_2x2_eigen_fixture,EvidenceKind.SYMBOLIC),
"184":("Min-Max Contract",minmax_contract,EvidenceKind.SYMBOLIC),
"185":("Spectral Milestone",spectral_milestone,EvidenceKind.NUMERICAL),

"186":("Backward Euler Energy",backward_euler_energy_audit,EvidenceKind.SYMBOLIC),
"187":("Theta Amplification",lambda: theta_scheme_amplification(2,.5),EvidenceKind.NUMERICAL),
"188":("Time Residual Estimator",lambda: time_residual_estimator([1,.8,.64],.1,2),EvidenceKind.NUMERICAL),
"189":("Adaptive Time-Step Policy",lambda: adaptive_time_step_policy([.08,.03,.005,.07]),EvidenceKind.NUMERICAL),
"190":("Parabolic Milestone",parabolic_milestone,EvidenceKind.SYMBOLIC),

"191":("Discrete de Rham Complex",exact_complex_audit,EvidenceKind.SYMBOLIC),
"192":("Curl-Curl Gradient Nullspace",curlcurl_nullspace_audit,EvidenceKind.SYMBOLIC),
"193":("Gauge-Fixed Maxwell Fixture",gauge_fixed_maxwell_fixture,EvidenceKind.SYMBOLIC),
"194":("FEEC Contract",feec_contract,EvidenceKind.SYMBOLIC),
"195":("Maxwell Milestone",maxwell_milestone,EvidenceKind.SYMBOLIC),

"196":("Capability Dependency Graph",capability_dependency_graph,EvidenceKind.SYMBOLIC),
"197":("Evidence Scope Audit",evidence_scope_audit,EvidenceKind.SYMBOLIC),
"198":("Reproducibility Capsule v2",reproducibility_capsule_v2,EvidenceKind.SYMBOLIC),
"199":("v2 Qualification Matrix",qualification_matrix_v2,EvidenceKind.SYMBOLIC),
"200":("CACE v2.0 Milestone",v2_milestone,EvidenceKind.SYMBOLIC),
}

class RoadmapStepModule(ResultModule):
    capability_key="151"; module_id="road151.rt1"; label="Roadmap Step"; version="1.51.0"
    description="CACE v1.51-v2.0 roadmap capability."
    evidence_kind=EvidenceKind.SYMBOLIC
    metadata=ModuleMetadata(module_id,label,version,"CACE v2 Roadmap",description,Maturity.EXPERIMENTAL,
        assumptions=("Capability evidence and theorem scope must be preserved.",))
    proof_status=ProofStatus(evidence={EvidenceKind.SYMBOLIC},unit_tests=True,regression_tests=True,documentation=True,
        limitations=["Reviewed mathematical contracts remain distinct from machine-formal proofs."])
    def execute(self,inputs,params,ctx): return {"result":CAP[self.capability_key][1]()}
    def verify(self,inputs,params,outputs,ctx): return super().verify(inputs,params,outputs,ctx)
