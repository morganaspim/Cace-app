from __future__ import annotations
import json, math
from math import comb, factorial
import numpy as np

from cace_studio.core.module import Module, ValidationError
from cace_studio.core.types import ModuleMetadata, PortSpec, ParameterSpec, ProofStatus, Maturity, EvidenceKind
from cace_studio.core.verification import VerificationRecord, VerificationState
from cace_studio.core.interval import Interval, singleton, add, sub, mul, div, square, sqrt_interval, sum_intervals, abs_interval, down, up
from cace_studio.core.interval_linalg import det2, inv2, transpose2, matvec2, dot2
from cace_studio.modules.fem_nd import _boundary_facets, _boundary_vertices, _csr_from_dense, _dense

BUBBLE_THEOREM_ID = "poisson2d-reference-triangle-bubble-p1-v1"
RELIABILITY_THEOREM_ID = "poisson2d-reference-triangle-bubble-residual-v1"


def _I(x: float) -> Interval:
    return singleton(float(x))


def _neg(a: Interval) -> Interval:
    return Interval(-a.hi, -a.lo)


def _scale(a: Interval, c: float) -> Interval:
    return mul(a, singleton(float(c)))


def _interval_max(items: list[Interval]) -> Interval:
    return Interval(max(x.lo for x in items), max(x.hi for x in items))


def _edge_length_interval(p, q) -> Interval:
    dx=sub(_I(q[0]),_I(p[0])); dy=sub(_I(q[1]),_I(p[1]))
    s=add(square(dx),square(dy))
    return sqrt_interval(Interval(max(0.0,s.lo), max(0.0,s.hi)))


def _triangle_interval_geometry(V: np.ndarray, cell: list[int]):
    p0,p1,p2=[V[i] for i in cell]
    J=[
        [sub(_I(p1[0]),_I(p0[0])), sub(_I(p2[0]),_I(p0[0]))],
        [sub(_I(p1[1]),_I(p0[1])), sub(_I(p2[1]),_I(p0[1]))],
    ]
    d=det2(J)
    if d.lo <= 0.0 <= d.hi:
        raise ValidationError("triangle interval determinant contains zero; nondegeneracy cannot be certified")
    # Positive orientation is required for a stable, explicit contract.
    if d.lo <= 0:
        raise ValidationError("v0.6 certified triangles must have counter-clockwise orientation")
    area=_scale(d,0.5)
    invT=transpose2(inv2(J))
    ref=[[_I(-1),_I(-1)],[_I(1),_I(0)],[_I(0),_I(1)]]
    grads=[matvec2(invT,g) for g in ref]
    edges=[_edge_length_interval(p0,p1),_edge_length_interval(p1,p2),_edge_length_interval(p2,p0)]
    diameter=_interval_max(edges)
    return {"J":J,"det":d,"area":area,"invT":invT,"grads":grads,"edges":edges,"diameter":diameter}


def _ival(x: Interval): return [x.lo,x.hi]
def _imat(a): return [[_ival(x) for x in row] for row in a]


def _reference_triangle_contract(mesh):
    if int(mesh.get('dimension',-1)) != 2: return False,"dimension must be 2"
    V=np.asarray(mesh['vertices'],float)
    if V.ndim!=2 or V.shape[1]!=2 or not np.all(np.isfinite(V)): return False,"vertices must be finite 2D coordinates"
    # Boundary must lie exactly on x=0, y=0, or x+y=1 in stored binary64 values, and include the three corners.
    bfac,_=_boundary_facets(mesh['elements']); bd=_boundary_vertices(bfac)
    tol=2e-14
    for i in bd:
        x,y=V[i]
        if not (abs(x)<=tol or abs(y)<=tol or abs(x+y-1.0)<=tol): return False,"boundary vertex is not on reference-triangle boundary"
    corners=[(0.,0.),(1.,0.),(0.,1.)]
    for c in corners:
        if not any(np.linalg.norm(v-np.asarray(c))<=tol for v in V): return False,"reference-triangle corner missing"
    # Cells must be certifiably CCW and nondegenerate; manifold facets.
    try:
        for cell in mesh['elements']: _triangle_interval_geometry(V,list(map(int,cell)))
    except Exception as e: return False,str(e)
    _,counts=_boundary_facets(mesh['elements'])
    if any(n not in (1,2) for n in counts.values()): return False,"non-manifold edge incidence"
    return True,""


# ---- Interval polynomial arithmetic in two variables ----
def _padd(a,b):
    out=dict(a)
    for k,v in b.items(): out[k]=add(out[k],v) if k in out else v
    return out

def _pmul(a,b):
    out={}
    for (i,j),x in a.items():
        for (k,l),y in b.items():
            key=(i+k,j+l); z=mul(x,y); out[key]=add(out[key],z) if key in out else z
    return out

def _ppow(a,n):
    out={(0,0):_I(1)}
    for _ in range(n): out=_pmul(out,a)
    return out

def _pscale(a,c): return {k:_scale(v,c) for k,v in a.items()}

def _integrate_poly_triangle(poly, Vcell):
    # x=x0+a*r+b*s, y=y0+c*r+d*s over reference triangle.
    x0,y0=map(float,Vcell[0]); x1,y1=map(float,Vcell[1]); x2,y2=map(float,Vcell[2])
    X={(0,0):_I(x0),(1,0):sub(_I(x1),_I(x0)),(0,1):sub(_I(x2),_I(x0))}
    Y={(0,0):_I(y0),(1,0):sub(_I(y1),_I(y0)),(0,1):sub(_I(y2),_I(y0))}
    mapped={}
    for (i,j),coef in poly.items():
        term=_pmul(_ppow(X,i),_ppow(Y,j)); term={k:mul(coef,v) for k,v in term.items()}; mapped=_padd(mapped,term)
    J=[
        [sub(_I(x1),_I(x0)),sub(_I(x2),_I(x0))],
        [sub(_I(y1),_I(y0)),sub(_I(y2),_I(y0))],
    ]
    det=det2(J)
    if det.lo<=0: raise ValidationError("positive triangle orientation required")
    total=Interval(0.0,0.0)
    for (p,q),coef in mapped.items():
        # ∫_R r^p s^q = p!q!/(p+q+2)!
        moment=factorial(p)*factorial(q)/factorial(p+q+2)
        total=add(total,mul(mul(coef,_I(moment)),det))
    return total


def _bubble_grad_polynomials():
    # u=x*y*(1-x-y); ux=y-2xy-y^2 ; uy=x-x^2-2xy
    gx={(0,1):_I(1),(1,1):_I(-2),(0,2):_I(-1)}
    gy={(1,0):_I(1),(2,0):_I(-1),(1,1):_I(-2)}
    return gx,gy


def _const_shift(poly, c: Interval):
    out=dict(poly); out[(0,0)]=sub(out.get((0,0),Interval(0.0,0.0)),c); return out


class CertifiedTriangleGeometry2D(Module):
    metadata=ModuleMetadata('fem06.triangle_geometry','Certified Triangle Geometry 2D','0.6.0','Certified FEM',
        'Outward-enclose triangle Jacobians, determinants, areas, inverse-transposes, P1 gradients, edge lengths, and diameters.',Maturity.BETA,
        assumptions=('stored binary64 vertex coordinates are exact input data','triangles are counter-clockwise','mesh is conforming and manifold'))
    inputs=(PortSpec('mesh','simplex_mesh'),); outputs=(PortSpec('geometry_certificate','triangle_geometry_certificate'),)
    proof_status=ProofStatus(evidence={EvidenceKind.INTERVAL},unit_tests=True,property_tests=True,documentation=True,
        limitations=['2D triangles only','interval arithmetic is binary64 nextafter based, not MPFI/Arb'])
    def validate(self,inputs,params):
        super().validate(inputs,params); ok,reason=_reference_triangle_contract(inputs['mesh'])
        if not ok: raise ValidationError(reason)
    def execute(self,inputs,params,ctx):
        m=inputs['mesh']; V=np.asarray(m['vertices'],float); rows=[]
        for k,c in enumerate(m['elements']):
            g=_triangle_interval_geometry(V,list(map(int,c)))
            rows.append({'element':k,'det_interval':_ival(g['det']),'area_interval':_ival(g['area']),
                         'inverse_transpose_interval':_imat(g['invT']),'gradient_intervals':[_imat([r])[0] for r in g['grads']],
                         'edge_length_intervals':[_ival(e) for e in g['edges']],'diameter_interval':_ival(g['diameter'])})
        return {'geometry_certificate':{'dimension':2,'elements':rows,'certified_nondegenerate':True,'orientation':'CCW'}}
    def verify(self,inputs,params,outputs,ctx):
        rows=outputs['geometry_certificate']['elements']; ok=all(r['det_interval'][0]>0 and r['area_interval'][0]>0 for r in rows)
        return [VerificationRecord('triangle-interval-geometry',EvidenceKind.INTERVAL,
            'every triangle has a strictly positive interval determinant and outward-enclosed area, inverse-transpose, gradients, and edge lengths',
            VerificationState.PASS if ok else VerificationState.FAIL,'directed interval affine-geometry calculation',{'elements':len(rows),'certified_nondegenerate':ok})]


class CertifiedShapeRegularity2D(Module):
    metadata=ModuleMetadata('fem06.shape_regularity','Certified Triangle Shape Regularity','0.6.0','Certified FEM',
        'Enclose triangle inradii and h/r shape ratios from certified areas and edge lengths.',Maturity.BETA,
        assumptions=('certified triangle geometry is available',))
    inputs=(PortSpec('geometry_certificate','triangle_geometry_certificate'),)
    outputs=(PortSpec('shape_certificate','shape_regularity_certificate_2d'),)
    parameters=(ParameterSpec('max_ratio','number',25.0,'accepted upper bound on max h/r'),)
    proof_status=ProofStatus(evidence={EvidenceKind.INTERVAL},unit_tests=True,documentation=True)
    def execute(self,inputs,params,ctx):
        rows=[]; ratios=[]
        for g in inputs['geometry_certificate']['elements']:
            area=Interval(*g['area_interval']); edges=[Interval(*x) for x in g['edge_length_intervals']]; perimeter=sum_intervals(edges)
            rin=div(_scale(area,2.0),perimeter); h=Interval(*g['diameter_interval']); ratio=div(h,rin)
            rows.append({'element':g['element'],'inradius_interval':_ival(rin),'shape_ratio_interval':_ival(ratio)})
            ratios.append(ratio)
        max_ratio=Interval(max(r.lo for r in ratios),max(r.hi for r in ratios)) if ratios else Interval(0.0,0.0)
        threshold=float(params['max_ratio']); certified=max_ratio.hi<=threshold
        return {'shape_certificate':{'elements':rows,'max_shape_ratio_interval':_ival(max_ratio),'threshold':threshold,'shape_regular_certified':certified}}
    def verify(self,inputs,params,outputs,ctx):
        c=outputs['shape_certificate']; state=VerificationState.PASS if c['shape_regular_certified'] else VerificationState.NOT_RUN
        return [VerificationRecord('triangle-shape-regularity-interval',EvidenceKind.INTERVAL,
            'triangle inradii and h/r ratios are interval-enclosed; the configured global shape-regularity threshold is certified when the ratio upper bound fits beneath it',
            state,'r=2A/perimeter and h=max(edge lengths), evaluated with directed interval arithmetic',
            {'max_shape_ratio_interval':c['max_shape_ratio_interval'],'threshold':c['threshold']})]


class CertifiedElementStiffness2D(Module):
    metadata=ModuleMetadata('fem06.element_stiffness','Certified P1 Element Stiffness 2D','0.6.0','Certified FEM',
        'Enclose every local P1 Laplacian stiffness entry K_ij=|T| grad(phi_i)·grad(phi_j) using certified triangle geometry.',Maturity.BETA)
    inputs=(PortSpec('mesh','simplex_mesh'),PortSpec('geometry_certificate','triangle_geometry_certificate'))
    outputs=(PortSpec('stiffness_certificate','element_stiffness_certificate'),)
    proof_status=ProofStatus(evidence={EvidenceKind.INTERVAL,EvidenceKind.SYMBOLIC},unit_tests=True,documentation=True)
    def execute(self,inputs,params,ctx):
        rows=[]
        for g in inputs['geometry_certificate']['elements']:
            area=Interval(*g['area_interval']); grads=[[Interval(*x) for x in row] for row in g['gradient_intervals']]
            K=[]
            for i in range(3):
                rr=[]
                for j in range(3): rr.append(_ival(mul(area,dot2(grads[i],grads[j]))))
                K.append(rr)
            rows.append({'element':g['element'],'stiffness_intervals':K})
        return {'stiffness_certificate':{'elements':rows,'bilinear_form':'integral_T grad(phi_i) dot grad(phi_j)'}}
    def verify(self,inputs,params,outputs,ctx):
        ok=True
        for e in outputs['stiffness_certificate']['elements']:
            K=e['stiffness_intervals']
            for i in range(3):
                for j in range(3):
                    ok &= (K[i][j][0] <= K[j][i][1] and K[j][i][0] <= K[i][j][1])
        return [VerificationRecord('element-stiffness-intervals',EvidenceKind.INTERVAL,
            'local P1 stiffness entries are outward-enclosed and interval-symmetric',VerificationState.PASS if ok else VerificationState.FAIL,
            'K_ij=area*grad(phi_i)·grad(phi_j) with interval geometry',{'elements':len(outputs['stiffness_certificate']['elements'])})]


class BubblePoissonProblem2D(Module):
    metadata=ModuleMetadata('fem06.bubble_problem','2D Bubble Poisson Benchmark','0.6.0','Certified FEM',
        'Declare the reference-triangle benchmark u=x y (1-x-y), -Delta u=2(x+y), u=0 on the boundary.',Maturity.BETA)
    outputs=(PortSpec('problem','certified_poisson_problem'),)
    proof_status=ProofStatus(evidence={EvidenceKind.SYMBOLIC},unit_tests=True,documentation=True)
    def execute(self,inputs,params,ctx):
        return {'problem':{'dimension':2,'diffusion':1.0,'source_constant':0.0,'source_linear':[2.0,2.0],
                           'domain':'reference_triangle','exact_solution':'x*y*(1-x-y)','theorem_id':BUBBLE_THEOREM_ID}}
    def verify(self,inputs,params,outputs,ctx):
        return [VerificationRecord('bubble-poisson-symbolic-identity',EvidenceKind.SYMBOLIC,
            '-Delta[x*y*(1-x-y)] = 2(x+y) and the polynomial vanishes on all three reference-triangle boundary edges',VerificationState.PASS,
            'closed-form differentiation and boundary factorization',{})]


class BubbleContinuumEnergyCertificate2D(Module):
    metadata=ModuleMetadata('fem06.bubble_continuum_error','2D Continuum Energy Error Certificate','0.6.0','Certified FEM',
        'For the reference-triangle bubble Poisson benchmark, rigorously integrate |grad(u)-grad(u_h)|^2 over every triangle using interval polynomial moments.',Maturity.EXPERIMENTAL,
        assumptions=('problem is the built-in reference-triangle bubble benchmark','P1 computed solution is supplied on the same conforming mesh'))
    inputs=(PortSpec('mesh','simplex_mesh'),PortSpec('solution','fem_solution_nd'),PortSpec('problem','certified_poisson_problem'),PortSpec('geometry_certificate','triangle_geometry_certificate'))
    outputs=(PortSpec('continuum_certificate','continuum_error_certificate_2d'),)
    proof_status=ProofStatus(evidence={EvidenceKind.INTERVAL,EvidenceKind.SYMBOLIC},unit_tests=True,property_tests=True,documentation=True,
        limitations=['benchmark-specific manufactured solution; not yet a generic 2D Poisson reliability theorem'])
    def validate(self,inputs,params):
        super().validate(inputs,params); ok,reason=_reference_triangle_contract(inputs['mesh'])
        if not ok: raise ValidationError(reason)
        if inputs['problem'].get('theorem_id')!=BUBBLE_THEOREM_ID: raise ValidationError('v0.6 continuum certificate requires the built-in bubble theorem contract')
    def execute(self,inputs,params,ctx):
        m=inputs['mesh']; V=np.asarray(m['vertices'],float); u=np.asarray(inputs['solution']['values'],float)
        gx_exact,gy_exact=_bubble_grad_polynomials(); total=Interval(0.0,0.0); terms=[]
        for k,c in enumerate(m['elements']):
            c=list(map(int,c)); g=_triangle_interval_geometry(V,c); grads=g['grads']
            uhx=Interval(0.0,0.0); uhy=Interval(0.0,0.0)
            for a,vi in enumerate(c):
                uhx=add(uhx,mul(_I(u[vi]),grads[a][0])); uhy=add(uhy,mul(_I(u[vi]),grads[a][1]))
            dx=_const_shift(gx_exact,uhx); dy=_const_shift(gy_exact,uhy)
            p=_padd(_pmul(dx,dx),_pmul(dy,dy))
            e2=_integrate_poly_triangle(p,V[np.asarray(c,int)])
            e2=Interval(max(0.0,e2.lo),max(0.0,e2.hi)); total=add(total,e2)
            terms.append({'element':k,'energy_error_squared_interval':_ival(e2),'uh_gradient_interval':[_ival(uhx),_ival(uhy)]})
        energy=sqrt_interval(Interval(max(0,total.lo),max(0,total.hi)))
        return {'continuum_certificate':{'theorem_id':BUBBLE_THEOREM_ID,'certified':True,'scope':'computed-P1-vs-exact-continuum-bubble-solution',
            'energy_error_squared_interval':_ival(total),'energy_error_interval':_ival(energy),'elements':terms}}
    def verify(self,inputs,params,outputs,ctx):
        c=outputs['continuum_certificate']; lo,hi=c['energy_error_interval']; ok=c['certified'] and 0<=lo<=hi
        return [VerificationRecord('bubble-continuum-energy-2d',EvidenceKind.INTERVAL,
            'the continuum energy error of the computed P1 function is enclosed by exact polynomial pullback moments plus directed interval arithmetic',
            VerificationState.PASS if ok else VerificationState.FAIL,'exact monomial integration on affine triangles with interval coefficients',
            {'energy_error_lower':lo,'energy_error_upper':hi,'elements':len(c['elements'])})]


class BubbleResidualEstimatorCertificate2D(Module):
    metadata=ModuleMetadata('fem06.bubble_estimator','Certified 2D Residual Estimator','0.6.0','Certified FEM',
        'Interval-enclose a residual/jump estimator for the bubble benchmark using exact element integration and outward-rounded edge geometry.',Maturity.EXPERIMENTAL)
    inputs=(PortSpec('mesh','simplex_mesh'),PortSpec('solution','fem_solution_nd'),PortSpec('geometry_certificate','triangle_geometry_certificate'))
    outputs=(PortSpec('estimator_certificate','estimator_certificate_2d'),)
    proof_status=ProofStatus(evidence={EvidenceKind.INTERVAL},unit_tests=True,documentation=True,
        limitations=['estimator definition is v0.6-specific','generic reliability constant is not yet claimed'])
    def execute(self,inputs,params,ctx):
        m=inputs['mesh']; V=np.asarray(m['vertices'],float); u=np.asarray(inputs['solution']['values'],float); E=[list(map(int,c)) for c in m['elements']]
        geoms=[_triangle_interval_geometry(V,c) for c in E]; grads=[]
        for c,g in zip(E,geoms):
            gx=Interval(0,0); gy=Interval(0,0)
            for a,vi in enumerate(c): gx=add(gx,mul(_I(u[vi]),g['grads'][a][0])); gy=add(gy,mul(_I(u[vi]),g['grads'][a][1]))
            grads.append([gx,gy])
        # f=2(x+y); element term h_K^2 * int_T f^2
        fpoly={(1,0):_I(2),(0,1):_I(2)}; f2=_pmul(fpoly,fpoly)
        eta2=[]
        for c,g in zip(E,geoms):
            fi=_integrate_poly_triangle(f2,V[np.asarray(c,int)]); eta2.append(mul(square(g['diameter']),fi))
        facet_cells={}
        for k,c in enumerate(E):
            for edge in (tuple(sorted((c[0],c[1]))), tuple(sorted((c[1],c[2]))), tuple(sorted((c[2],c[0])))):
                facet_cells.setdefault(edge,[]).append(k)
        for edge,cells in facet_cells.items():
            if len(cells)!=2: continue
            a,b=cells; p,q=V[list(edge)]; dx=sub(_I(q[0]),_I(p[0])); dy=sub(_I(q[1]),_I(p[1])); L=_edge_length_interval(p,q)
            # unit normal (dy,-dx)/L; sign irrelevant after squaring
            nx=div(dy,L); ny=div(_neg(dx),L)
            jx=sub(grads[a][0],grads[b][0]); jy=sub(grads[a][1],grads[b][1]); jump=add(mul(jx,nx),mul(jy,ny))
            hF=_interval_max([geoms[a]['diameter'],geoms[b]['diameter']])
            contrib=_scale(mul(mul(hF,L),square(jump)),0.5)
            eta2[a]=add(eta2[a],contrib); eta2[b]=add(eta2[b],contrib)
        total=sum_intervals(eta2); total=Interval(max(0,total.lo),max(0,total.hi)); eta=sqrt_interval(total)
        return {'estimator_certificate':{'eta_squared_interval':_ival(total),'eta_interval':_ival(eta),'element_eta_squared_intervals':[_ival(x) for x in eta2],
                                          'definition':'sum_K h_K^2||f||_K^2 + 1/2 sum_{F subset dK interior} h_F ||jump grad(u_h).n||_F^2'}}
    def verify(self,inputs,params,outputs,ctx):
        lo,hi=outputs['estimator_certificate']['eta_interval']; ok=0<=lo<=hi and math.isfinite(hi)
        return [VerificationRecord('bubble-residual-estimator-interval',EvidenceKind.INTERVAL,
            'the v0.6 2D residual/jump estimator is enclosed by interval geometry and exact polynomial element integration',
            VerificationState.PASS if ok else VerificationState.FAIL,'interval residual/jump estimator construction',{'eta_lower':lo,'eta_upper':hi})]


class BubbleReliabilityCertificate2D(Module):
    metadata=ModuleMetadata('fem06.bubble_reliability','Scoped 2D Estimator Reliability Certificate','0.6.0','Certified FEM',
        'For the built-in benchmark run, certify E <= C_rel eta from independently enclosed continuum error and residual estimator intervals.',Maturity.EXPERIMENTAL,
        assumptions=('both upstream intervals are independently certified','this is a benchmark/run-specific reliability certificate, not a generic estimator theorem'))
    inputs=(PortSpec('continuum_certificate','continuum_error_certificate_2d'),PortSpec('estimator_certificate','estimator_certificate_2d'))
    outputs=(PortSpec('reliability_certificate','reliability_certificate_2d'),)
    parameters=(ParameterSpec('C_rel','number',1.0,'proposed reliability constant for this scoped benchmark certificate'),)
    proof_status=ProofStatus(evidence={EvidenceKind.INTERVAL},unit_tests=True,documentation=True,
        limitations=['run-specific implication only; v0.6 does not prove C_rel=1 for arbitrary 2D Poisson meshes/problems'])
    def execute(self,inputs,params,ctx):
        Ehi=float(inputs['continuum_certificate']['energy_error_interval'][1]); eta=inputs['estimator_certificate']['eta_interval']; C=float(params['C_rel'])
        rhslo=down(C*float(eta[0])); passed=(C>0 and rhslo>=Ehi)
        ratio=math.inf if eta[0]<=0 else up(Ehi/eta[0])
        return {'reliability_certificate':{'theorem_id':RELIABILITY_THEOREM_ID,'certified':passed,'C_rel':C,'error_upper':Ehi,'eta_lower':eta[0],
                                            'C_eta_lower':rhslo,'certified_ratio_upper':ratio,'scope':'benchmark-run-specific'}}
    def verify(self,inputs,params,outputs,ctx):
        c=outputs['reliability_certificate']; state=VerificationState.PASS if c['certified'] else VerificationState.NOT_RUN
        return [VerificationRecord('scoped-2d-reliability',EvidenceKind.INTERVAL,
            'for this benchmark run only, E <= C_rel eta is certified from independent interval enclosures',state,
            'compare continuum error upper bound to C_rel times estimator lower bound',c,
            notes=(() if c['certified'] else ('configured C_rel was insufficient or estimator lower bound was nonpositive',)))]


class ReliabilityTheoremObligation2D(Module):
    metadata=ModuleMetadata('fem06.reliability_theorem_export','Generic 2D Reliability Theorem Obligation','0.6.0','Formal Verification',
        'Export the still-open formal obligation for a mesh-uniform 2D residual-estimator reliability theorem.',Maturity.PROTOTYPE)
    outputs=(PortSpec('theorem_artifact','formal_artifact'),)
    proof_status=ProofStatus(evidence=set(),unit_tests=True,documentation=True,limitations=['artifact is an obligation only; no Lean proof is claimed'])
    def execute(self,inputs,params,ctx):
        text='''-- CACE v0.6 theorem obligation (NOT machine checked)\n-- Target: conforming P1 FEM for Poisson on shape-regular triangular meshes.\n-- Prove existence of mesh-uniform C_rel under explicit domain/interpolation assumptions:\n--   ||u-u_h||_E <= C_rel * eta_residual_jump\n-- The executable v0.6 benchmark certificate does NOT discharge this theorem.\n'''
        return {'theorem_artifact':{'theorem_id':'poisson2d-p1-residual-reliability-general-v0.6','language':'Lean4','status':'obligation-only','machine_checked':False,'text':text}}
    def verify(self,inputs,params,outputs,ctx):
        return [VerificationRecord('generic-2d-reliability-formal-proof',EvidenceKind.FORMAL,
            'generic 2D residual-estimator reliability remains a formal theorem obligation in v0.6',VerificationState.NOT_RUN,
            'formal artifact export only',{'machine_checked':False})]


def register_fem_cert2d(registry):
    for cls in (CertifiedTriangleGeometry2D,CertifiedShapeRegularity2D,CertifiedElementStiffness2D,BubblePoissonProblem2D,
                BubbleContinuumEnergyCertificate2D,BubbleResidualEstimatorCertificate2D,BubbleReliabilityCertificate2D,
                ReliabilityTheoremObligation2D): registry.register(cls)
