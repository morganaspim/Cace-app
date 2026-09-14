from __future__ import annotations
import json, math
from itertools import combinations
from typing import Any
import numpy as np

from cace_studio.core.module import Module, ExecutionContext, ValidationError
from cace_studio.core.types import ModuleMetadata, PortSpec, ParameterSpec, ProofStatus, Maturity, EvidenceKind
from cace_studio.core.verification import VerificationRecord, VerificationState


def _jload(x):
    return json.loads(x) if isinstance(x, str) else x

def _csr_from_dense(A: np.ndarray, tol: float=0.0):
    data=[]; indices=[]; indptr=[0]
    for row in A:
        for j,v in enumerate(row):
            if abs(float(v))>tol: data.append(float(v)); indices.append(int(j))
        indptr.append(len(data))
    return {'shape':[int(A.shape[0]),int(A.shape[1])],'data':data,'indices':indices,'indptr':indptr}

def _dense(csr):
    n,m=map(int,csr['shape']); A=np.zeros((n,m),float)
    for i in range(n):
        for p in range(csr['indptr'][i],csr['indptr'][i+1]): A[i,int(csr['indices'][p])]=float(csr['data'][p])
    return A

def _facet_tuples(cell):
    return [tuple(sorted(cell[:i]+cell[i+1:])) for i in range(len(cell))]

def _boundary_facets(elements):
    counts={}
    for c in elements:
        for f in _facet_tuples(list(c)): counts[f]=counts.get(f,0)+1
    return sorted([list(f) for f,n in counts.items() if n==1]), counts

def _simplex_geometry(vertices: np.ndarray, cell: list[int]):
    d=vertices.shape[1]; X=vertices[np.asarray(cell,int)]
    J=(X[1:]-X[0]).T
    det=float(np.linalg.det(J)) if d>1 else float(J[0,0])
    volume=abs(det)/math.factorial(d)
    if volume<=0: raise ValidationError('degenerate simplex')
    # lambdas satisfy [1,x] C = I; columns of inverse are coefficients [c, grad...]
    M=np.column_stack([np.ones(d+1),X])
    C=np.linalg.inv(M)
    grads=C[1:,:].T
    coeffs=C.T
    diameter=max(float(np.linalg.norm(X[i]-X[j])) for i in range(d+1) for j in range(i+1,d+1))
    return {'J':J,'det':det,'volume':volume,'gradients':grads,'coefficients':coeffs,'diameter':diameter,'centroid':X.mean(axis=0)}

def _boundary_vertices(boundary_facets):
    return sorted(set(i for f in boundary_facets for i in f))

def _assemble(mesh, source=1.0):
    V=np.asarray(mesh['vertices'],float); elems=[list(map(int,c)) for c in mesh['elements']]; n=len(V)
    A=np.zeros((n,n),float); b=np.zeros(n,float)
    geom=[]
    for cell in elems:
        g=_simplex_geometry(V,cell); geom.append(g); G=g['gradients']; vol=g['volume']
        ke=vol*(G@G.T); fe=np.full(len(cell),float(source)*vol/len(cell))
        for i,I in enumerate(cell):
            b[I]+=fe[i]
            for j,J in enumerate(cell): A[I,J]+=ke[i,j]
    bfac,_=_boundary_facets(elems); bd=_boundary_vertices(bfac); interior=[i for i in range(n) if i not in set(bd)]
    Ar=A[np.ix_(interior,interior)]; br=b[interior]
    return A,b,Ar,br,interior,bd,geom

def _solve(mesh, source=1.0):
    A,b,Ar,br,interior,bd,geom=_assemble(mesh,source); u=np.zeros(len(mesh['vertices']),float)
    if interior: u[np.asarray(interior,int)]=np.linalg.solve(Ar,br)
    return u,(A,b,Ar,br,interior,bd,geom)

class SimplexMeshND(Module):
    metadata=ModuleMetadata('fem_nd.mesh','Arbitrary Simplex Mesh','0.3.0','Meshes',
        'Create an explicit conforming simplicial mesh in dimensions 1, 2, or 3; boundary facets are derived by incidence counting.',Maturity.BETA,
        assumptions=('each cell has d+1 distinct valid vertex indices','cells are nondegenerate','mesh is intended to be conforming'))
    outputs=(PortSpec('mesh','simplex_mesh'),)
    parameters=(
        ParameterSpec('vertices','string','[[0,0],[1,0],[1,1],[0,1],[0.5,0.5]]','JSON array of vertex coordinates'),
        ParameterSpec('elements','string','[[0,1,4],[1,2,4],[2,3,4],[3,0,4]]','JSON array of simplices'))
    proof_status=ProofStatus(evidence={EvidenceKind.NUMERICAL},unit_tests=True,property_tests=True,documentation=True)
    def validate(self,inputs,params):
        super().validate(inputs,params); p=self.resolved_params(params); V=np.asarray(_jload(p['vertices']),float); E=_jload(p['elements'])
        if V.ndim!=2 or V.shape[1] not in (1,2,3) or len(V)<V.shape[1]+1: raise ValidationError('vertices must be an NxD array with D in {1,2,3}')
        d=V.shape[1]
        if not np.all(np.isfinite(V)): raise ValidationError('vertices must be finite')
        if not E: raise ValidationError('mesh needs at least one element')
        for c in E:
            if len(c)!=d+1 or len(set(c))!=d+1 or min(c)<0 or max(c)>=len(V): raise ValidationError('invalid simplex connectivity')
            _simplex_geometry(V,list(map(int,c)))
        _,counts=_boundary_facets(E)
        if any(n>2 for n in counts.values()): raise ValidationError('non-manifold facet incidence > 2')
    def execute(self,inputs,params,ctx):
        V=np.asarray(_jload(params['vertices']),float); E=[list(map(int,c)) for c in _jload(params['elements'])]; bfac,counts=_boundary_facets(E)
        return {'mesh':{'dimension':int(V.shape[1]),'vertices':V.tolist(),'elements':E,'boundary_facets':bfac,'boundary_vertices':_boundary_vertices(bfac)}}
    def verify(self,inputs,params,outputs,ctx):
        m=outputs['mesh']; V=np.asarray(m['vertices'],float); vols=[]; ok=True
        for c in m['elements']:
            try: vols.append(_simplex_geometry(V,c)['volume'])
            except Exception: ok=False
        bfac,counts=_boundary_facets(m['elements']); ok &= bfac==m['boundary_facets'] and all(n in (1,2) for n in counts.values())
        return [VerificationRecord('simplex-topology-geometry',EvidenceKind.NUMERICAL,
            'all simplices are nondegenerate and every codimension-one facet has incidence one or two; boundary is recomputed from incidence',
            VerificationState.PASS if ok else VerificationState.FAIL,'independent simplex determinant and facet-incidence checks',
            {'dimension':m['dimension'],'vertices':len(V),'elements':len(m['elements']),'boundary_facets':len(bfac),'min_volume':min(vols) if vols else 0.0})]

class P1SimplexSpaceND(Module):
    metadata=ModuleMetadata('fem_nd.p1_space','P1 Simplex Coordinates / Shape Functions','0.3.0','Finite Elements',
        'Construct affine barycentric P1 basis coefficients and constant physical gradients on each simplex.',Maturity.BETA,
        assumptions=('input is a valid nondegenerate simplex mesh',))
    inputs=(PortSpec('mesh','simplex_mesh'),); outputs=(PortSpec('space','fem_space_nd'),)
    proof_status=ProofStatus(evidence={EvidenceKind.SYMBOLIC,EvidenceKind.NUMERICAL},unit_tests=True,property_tests=True,documentation=True)
    def execute(self,inputs,params,ctx):
        m=inputs['mesh']; V=np.asarray(m['vertices'],float); local=[]
        for c in m['elements']:
            g=_simplex_geometry(V,c); local.append({'element':c,'volume':g['volume'],'diameter':g['diameter'],'coefficients':g['coefficients'].tolist(),'gradients':g['gradients'].tolist()})
        return {'space':{'family':'P1-simplex','dimension':m['dimension'],'dofs':len(V),'local':local}}
    def verify(self,inputs,params,outputs,ctx):
        V=np.asarray(inputs['mesh']['vertices'],float); maxerr=0.0
        for rec in outputs['space']['local']:
            c=rec['element']; C=np.asarray(rec['coefficients'],float); X=V[np.asarray(c,int)]
            vals=np.column_stack([np.ones(len(c)),X])@C.T
            maxerr=max(maxerr,float(np.max(np.abs(vals-np.eye(len(c))))))
            cent=X.mean(axis=0); lamb=C[:,0]+C[:,1:]@cent
            maxerr=max(maxerr,abs(float(np.sum(lamb))-1.0))
        ok=maxerr<=5e-12
        return [VerificationRecord('p1-barycentric-identities-nd',EvidenceKind.SYMBOLIC,
            'affine coordinates satisfy the nodal Kronecker identities and partition of unity in physical coordinates',
            VerificationState.PASS if ok else VerificationState.FAIL,'direct coefficient identity evaluation',{'max_identity_error':maxerr})]

class SimplexQuadratureND(Module):
    metadata=ModuleMetadata('fem_nd.quadrature','Simplex Quadrature','0.3.0','Finite Elements',
        'Generate centroid quadrature on every simplex; exact for affine scalar integrands.',Maturity.BETA)
    inputs=(PortSpec('mesh','simplex_mesh'),); outputs=(PortSpec('quadrature','quadrature_nd'),)
    proof_status=ProofStatus(evidence={EvidenceKind.SYMBOLIC,EvidenceKind.NUMERICAL},unit_tests=True,documentation=True,
        limitations=['centroid rule is degree-1 exact, not a general high-order quadrature rule'])
    def execute(self,inputs,params,ctx):
        m=inputs['mesh']; V=np.asarray(m['vertices'],float); q=[]
        for c in m['elements']:
            g=_simplex_geometry(V,c); q.append({'element':c,'point':g['centroid'].tolist(),'weight':g['volume']})
        return {'quadrature':{'rule':'simplex-centroid','degree_exact':1,'cells':q}}
    def verify(self,inputs,params,outputs,ctx):
        m=inputs['mesh']; V=np.asarray(m['vertices'],float); maxerr=0.0
        # Check constants and each coordinate x_j using vertex-average exact simplex integral.
        for rec,c in zip(outputs['quadrature']['cells'],m['elements']):
            X=V[np.asarray(c,int)]; w=float(rec['weight']); p=np.asarray(rec['point']); vol=_simplex_geometry(V,c)['volume']
            maxerr=max(maxerr,abs(w-vol))
            for j in range(V.shape[1]): maxerr=max(maxerr,abs(w*p[j]-vol*float(np.mean(X[:,j]))))
        return [VerificationRecord('centroid-quadrature-degree1',EvidenceKind.SYMBOLIC,
            'centroid quadrature integrates constants and coordinate functions exactly up to floating-point evaluation',
            VerificationState.PASS if maxerr<=5e-12 else VerificationState.FAIL,'affine simplex moment identities',{'max_moment_error':maxerr})]

class PoissonAssemblyND(Module):
    metadata=ModuleMetadata('fem_nd.poisson_assemble','Sparse Poisson Assembly ND','0.3.0','PDE',
        'Assemble the P1 simplex Galerkin operator for -Delta u = f with constant f and homogeneous Dirichlet data on all boundary vertices.',Maturity.BETA,
        assumptions=('domain is represented by a conforming simplex mesh','diffusion coefficient is one','all detected boundary vertices use u=0'))
    inputs=(PortSpec('mesh','simplex_mesh'),PortSpec('space','fem_space_nd')); outputs=(PortSpec('system','linear_system_nd'),)
    parameters=(ParameterSpec('source','number',1.0,'constant source f'),)
    proof_status=ProofStatus(evidence={EvidenceKind.NUMERICAL,EvidenceKind.SYMBOLIC},unit_tests=True,property_tests=True,documentation=True)
    def execute(self,inputs,params,ctx):
        m=inputs['mesh']; A,b,Ar,br,interior,bd,geom=_assemble(m,float(params['source']))
        return {'system':{'matrix':_csr_from_dense(Ar),'rhs':br.tolist(),'interior_dofs':interior,'boundary_dofs':bd,'full_dofs':len(b),'source':float(params['source'])}}
    def verify(self,inputs,params,outputs,ctx):
        A=_dense(outputs['system']['matrix']); sym=float(np.max(np.abs(A-A.T))) if A.size else 0.0
        eig=float(np.min(np.linalg.eigvalsh(A))) if A.size else math.inf; ok=sym<=5e-12 and eig>0
        return [VerificationRecord('poisson-stiffness-spd-nd',EvidenceKind.NUMERICAL,
            'reduced P1 Poisson stiffness matrix is symmetric positive definite for the detected Dirichlet subspace',
            VerificationState.PASS if ok else VerificationState.FAIL,'host symmetry and symmetric eigenvalue checks',
            {'symmetry_error':sym,'min_eigenvalue':eig,'nnz':len(outputs['system']['matrix']['data']),'interior_dofs':len(outputs['system']['interior_dofs'])})]

class LinearSolverND(Module):
    metadata=ModuleMetadata('fem_nd.linear_solve','Linear / PDE Solver ND','0.3.0','PDE','Solve a reduced simplex-FEM system and reconstruct homogeneous boundary values.',Maturity.BETA)
    inputs=(PortSpec('system','linear_system_nd'),); outputs=(PortSpec('solution','fem_solution_nd'),)
    supports_gpu=True
    proof_status=ProofStatus(evidence={EvidenceKind.NUMERICAL},unit_tests=True,documentation=True,
        limitations=['v0.3 stores CSR but converts to a dense array for the reference solve','GPU policy provenance is implemented; sparse CUDA kernels are a later backend'])
    def execute(self,inputs,params,ctx):
        s=inputs['system']; A=_dense(s['matrix']); b=np.asarray(s['rhs'],float); ui=np.linalg.solve(A,b) if len(b) else np.array([])
        u=np.zeros(int(s['full_dofs'])); u[np.asarray(s['interior_dofs'],int)]=ui
        return {'solution':{'values':u.tolist(),'interior':ui.tolist()}}
    def verify(self,inputs,params,outputs,ctx):
        s=inputs['system']; A=_dense(s['matrix']); b=np.asarray(s['rhs'],float); u=np.asarray(outputs['solution']['interior'],float); r=A@u-b
        rn=float(np.linalg.norm(r,np.inf)) if r.size else 0.0
        return [VerificationRecord('linear-solve-residual-nd',EvidenceKind.NUMERICAL,'independently recomputed reduced-system residual is small',
            VerificationState.PASS if rn<=1e-10 else VerificationState.FAIL,'host-side CSR reconstruction and residual',{'residual_inf':rn})]

class AlgebraicResidualND(Module):
    metadata=ModuleMetadata('fem_nd.residual','Residual ND','0.3.0','Verification','Independently recompute the reduced algebraic residual.',Maturity.BETA)
    inputs=(PortSpec('system','linear_system_nd'),PortSpec('solution','fem_solution_nd')); outputs=(PortSpec('residual_inf','number'),PortSpec('residual','array'))
    proof_status=ProofStatus(evidence={EvidenceKind.NUMERICAL},unit_tests=True,documentation=True)
    def execute(self,inputs,params,ctx):
        A=_dense(inputs['system']['matrix']); b=np.asarray(inputs['system']['rhs'],float); u=np.asarray(inputs['solution']['interior'],float); r=A@u-b
        return {'residual_inf':float(np.linalg.norm(r,np.inf)) if r.size else 0.0,'residual':r.tolist()}
    def verify(self,inputs,params,outputs,ctx):
        rn=float(outputs['residual_inf']); return [VerificationRecord('algebraic-residual-nd',EvidenceKind.NUMERICAL,'algebraic infinity residual is below 1e-10',VerificationState.PASS if rn<=1e-10 else VerificationState.FAIL,'independent residual node',{'residual_inf':rn})]

class ResidualEstimatorND(Module):
    metadata=ModuleMetadata('fem_nd.estimator','A-posteriori Residual Indicator ND','0.3.0','Verification',
        'Compute a residual/jump indicator for P1 Poisson elements in dimensions 2 or 3. This is an estimator diagnostic, not a certified error bound.',Maturity.EXPERIMENTAL,
        assumptions=('constant source','P1 gradients are elementwise constant'))
    inputs=(PortSpec('mesh','simplex_mesh'),PortSpec('solution','fem_solution_nd')); outputs=(PortSpec('estimator','error_estimator_nd'),)
    parameters=(ParameterSpec('source','number',1.0),)
    proof_status=ProofStatus(evidence={EvidenceKind.NUMERICAL},unit_tests=True,documentation=True,
        limitations=['no reliability/efficiency constant is certified in v0.3','implemented for dimensions 2 and 3'])
    def validate(self,inputs,params):
        super().validate(inputs,params)
        if inputs['mesh']['dimension'] not in (2,3): raise ValidationError('ND residual estimator currently supports d=2 or d=3')
    def execute(self,inputs,params,ctx):
        m=inputs['mesh']; V=np.asarray(m['vertices'],float); u=np.asarray(inputs['solution']['values'],float); f=float(params['source']); d=m['dimension']; E=m['elements']
        geoms=[_simplex_geometry(V,c) for c in E]; grads=[]
        for c,g in zip(E,geoms): grads.append(np.asarray(g['gradients']).T@u[np.asarray(c,int)])
        facet_cells={}
        for k,c in enumerate(E):
            for fac in _facet_tuples(list(c)): facet_cells.setdefault(fac,[]).append(k)
        eta2=np.array([(g['diameter']**2)*g['volume']*(f**2) for g in geoms],float)
        for fac,cells in facet_cells.items():
            if len(cells)!=2: continue
            a,b=cells; pts=V[np.asarray(fac,int)]
            if d==2:
                t=pts[1]-pts[0]; measure=float(np.linalg.norm(t)); n=np.array([t[1],-t[0]],float); n/=np.linalg.norm(n)
            else:
                cr=np.cross(pts[1]-pts[0],pts[2]-pts[0]); measure=float(np.linalg.norm(cr))/2.0; n=cr/np.linalg.norm(cr)
            jump=float(np.dot(grads[a]-grads[b],n)); hF=max(geoms[a]['diameter'],geoms[b]['diameter']); contrib=0.5*hF*measure*jump*jump
            eta2[a]+=contrib; eta2[b]+=contrib
        eta=np.sqrt(np.maximum(eta2,0)); return {'estimator':{'eta':float(np.linalg.norm(eta)),'element_eta':eta.tolist(),'kind':'residual-jump-diagnostic'}}
    def verify(self,inputs,params,outputs,ctx):
        vals=np.asarray(outputs['estimator']['element_eta']); ok=np.all(np.isfinite(vals)) and np.all(vals>=0)
        return [VerificationRecord('estimator-sanity-nd',EvidenceKind.NUMERICAL,'all local residual indicators are finite and nonnegative; no reliability theorem is claimed',VerificationState.PASS if ok else VerificationState.FAIL,'sanity/property check',{'eta':float(outputs['estimator']['eta']),'elements':len(vals)})]

class UniformRefinementND(Module):
    metadata=ModuleMetadata('fem_nd.refine','Conforming Uniform Refinement','0.3.0','Meshes',
        'Uniformly refine 1D segments or 2D triangles while sharing edge midpoints globally.',Maturity.EXPERIMENTAL)
    inputs=(PortSpec('mesh','simplex_mesh'),); outputs=(PortSpec('refined_mesh','simplex_mesh'),)
    proof_status=ProofStatus(evidence={EvidenceKind.NUMERICAL},unit_tests=True,property_tests=True,documentation=True,
        limitations=['v0.3 conforming refinement supports d=1 and d=2; tetrahedral refinement is intentionally not claimed'])
    def validate(self,inputs,params):
        super().validate(inputs,params)
        if inputs['mesh']['dimension'] not in (1,2): raise ValidationError('uniform refinement currently supports d=1 or d=2')
    def execute(self,inputs,params,ctx):
        m=inputs['mesh']; d=m['dimension']; V=[list(map(float,p)) for p in m['vertices']]; E=m['elements']; midpoint={}
        def mid(i,j):
            key=tuple(sorted((i,j)))
            if key not in midpoint:
                midpoint[key]=len(V); V.append(((np.asarray(V[i])+np.asarray(V[j]))/2).tolist())
            return midpoint[key]
        new=[]
        if d==1:
            for a,b in E:
                ab=mid(a,b); new += [[a,ab],[ab,b]]
        else:
            for a,b,c in E:
                ab,bc,ca=mid(a,b),mid(b,c),mid(c,a)
                new += [[a,ab,ca],[ab,b,bc],[ca,bc,c],[ab,bc,ca]]
        bfac,_=_boundary_facets(new)
        return {'refined_mesh':{'dimension':d,'vertices':V,'elements':new,'boundary_facets':bfac,'boundary_vertices':_boundary_vertices(bfac)}}
    def verify(self,inputs,params,outputs,ctx):
        old=inputs['mesh']; new=outputs['refined_mesh']; bfac,counts=_boundary_facets(new['elements']); V=np.asarray(new['vertices'],float)
        ok=all(n in (1,2) for n in counts.values()) and bfac==new['boundary_facets'] and all(_simplex_geometry(V,c)['volume']>0 for c in new['elements'])
        factor=2 if old['dimension']==1 else 4
        ok &= len(new['elements'])==factor*len(old['elements'])
        return [VerificationRecord('uniform-refinement-conformity-nd',EvidenceKind.NUMERICAL,'uniform refinement is nondegenerate and facet-conforming with expected cell multiplication',VerificationState.PASS if ok else VerificationState.FAIL,'global midpoint map plus independent facet incidence check',{'old_elements':len(old['elements']),'new_elements':len(new['elements']),'old_vertices':len(old['vertices']),'new_vertices':len(new['vertices'])})]

class ConvergenceStudyND(Module):
    metadata=ModuleMetadata('fem_nd.convergence','Adaptive/Convergence History','0.3.0','Research',
        'Run repeated uniform-refine → assemble → solve cycles and record mesh size, DOFs, and algebraic residual history.',Maturity.EXPERIMENTAL,
        assumptions=('homogeneous Dirichlet Poisson with constant source',))
    inputs=(PortSpec('mesh','simplex_mesh'),); outputs=(PortSpec('history','convergence_history'),)
    parameters=(ParameterSpec('levels','integer',3),ParameterSpec('source','number',1.0))
    proof_status=ProofStatus(evidence={EvidenceKind.NUMERICAL},unit_tests=True,documentation=True,
        limitations=['history is a reproducibility/performance artifact, not by itself a convergence theorem','refinement path currently d=1 or d=2'])
    def validate(self,inputs,params):
        super().validate(inputs,params); levels=int(self.resolved_params(params)['levels'])
        if levels<1 or levels>8: raise ValidationError('levels must be in [1,8]')
        if inputs['mesh']['dimension'] not in (1,2): raise ValidationError('convergence refinement currently supports d=1 or d=2')
    def execute(self,inputs,params,ctx):
        mesh=json.loads(json.dumps(inputs['mesh'])); levels=int(params['levels']); source=float(params['source']); hist=[]
        for level in range(levels):
            u,pack=_solve(mesh,source); A,b,Ar,br,interior,bd,geom=pack; r=Ar@u[np.asarray(interior,int)]-br if interior else np.array([])
            hist.append({'level':level,'vertices':len(mesh['vertices']),'elements':len(mesh['elements']),'interior_dofs':len(interior),'h_max':max(g['diameter'] for g in geom),'residual_inf':float(np.linalg.norm(r,np.inf)) if r.size else 0.0})
            if level<levels-1:
                # same conforming uniform refinement logic as the module, kept pure for repeatability
                V=[list(map(float,p)) for p in mesh['vertices']]; E=mesh['elements']; midpoint={}
                def mid(i,j):
                    key=tuple(sorted((i,j)))
                    if key not in midpoint: midpoint[key]=len(V); V.append(((np.asarray(V[i])+np.asarray(V[j]))/2).tolist())
                    return midpoint[key]
                new=[]
                if mesh['dimension']==1:
                    for a,b0 in E:
                        ab=mid(a,b0); new += [[a,ab],[ab,b0]]
                else:
                    for a,b0,c in E:
                        ab,bc,ca=mid(a,b0),mid(b0,c),mid(c,a); new += [[a,ab,ca],[ab,b0,bc],[ca,bc,c],[ab,bc,ca]]
                bfac,_=_boundary_facets(new); mesh={'dimension':mesh['dimension'],'vertices':V,'elements':new,'boundary_facets':bfac,'boundary_vertices':_boundary_vertices(bfac)}
        return {'history':{'kind':'uniform-refinement-poisson','records':hist}}
    def verify(self,inputs,params,outputs,ctx):
        h=outputs['history']['records']; decreasing=all(b['h_max']<a['h_max'] for a,b in zip(h,h[1:])); residual_ok=all(r['residual_inf']<=1e-10 for r in h)
        return [VerificationRecord('convergence-history-invariants',EvidenceKind.NUMERICAL,'uniform refinement decreases h_max and each linear solve satisfies the algebraic residual tolerance',VerificationState.PASS if decreasing and residual_ok else VerificationState.FAIL,'history invariant checks',{'levels':len(h),'h_initial':h[0]['h_max'],'h_final':h[-1]['h_max'],'max_residual':max(r['residual_inf'] for r in h)})]


class AdaptiveRefinement2D(Module):
    metadata=ModuleMetadata('fem_nd.adapt2d','Adaptive Refinement 2D','0.3.0','Meshes',
        'Dörfler-mark triangle indicators, split all edges of marked cells, and apply conforming red/green refinement to neighboring cells.',Maturity.EXPERIMENTAL,
        assumptions=('input is a conforming triangular mesh','0 < theta <= 1'))
    inputs=(PortSpec('mesh','simplex_mesh'),PortSpec('estimator','error_estimator_nd')); outputs=(PortSpec('refined_mesh','simplex_mesh'),PortSpec('marked','array'),PortSpec('marked_edges','array'))
    parameters=(ParameterSpec('theta','number',0.5,'Dörfler bulk fraction'),)
    proof_status=ProofStatus(evidence={EvidenceKind.NUMERICAL},unit_tests=True,property_tests=True,documentation=True,
        limitations=['2D triangles only in v0.3','refinement is red/green edge splitting; no shape-regularity theorem is encoded yet'])
    def validate(self,inputs,params):
        super().validate(inputs,params); t=float(self.resolved_params(params)['theta'])
        if inputs['mesh']['dimension']!=2: raise ValidationError('adaptive red/green refinement currently supports 2D triangles only')
        if not (0<t<=1): raise ValidationError('theta must satisfy 0 < theta <= 1')
        if len(inputs['estimator']['element_eta'])!=len(inputs['mesh']['elements']): raise ValidationError('estimator size does not match mesh')
    def execute(self,inputs,params,ctx):
        m=inputs['mesh']; eta=np.asarray(inputs['estimator']['element_eta'],float); w=eta*eta; target=float(params['theta'])*float(w.sum())
        order=sorted(range(len(w)), key=lambda i:(-float(w[i]), int(i))); marked=[]; acc=0.0
        for k in order:
            marked.append(int(k)); acc += float(w[k])
            if acc>=target: break
        split_edges=set()
        for k in marked:
            a,b,c=m['elements'][k]
            split_edges.update((tuple(sorted(e)) for e in ((a,b),(b,c),(c,a))))
        V=[list(map(float,p)) for p in m['vertices']]; mids={}
        def mid(edge):
            edge=tuple(sorted(edge))
            if edge not in mids:
                i,j=edge; mids[edge]=len(V); V.append(((np.asarray(V[i])+np.asarray(V[j]))/2).tolist())
            return mids[edge]
        new=[]
        for tri in m['elements']:
            a,b,c=tri; edges=[(a,b),(b,c),(c,a)]; flags=[tuple(sorted(e)) in split_edges for e in edges]; n=sum(flags)
            if n==0:
                new.append([a,b,c]); continue
            if n==3:
                ab,bc,ca=[mid(e) for e in edges]
                new += [[a,ab,ca],[ab,b,bc],[ca,bc,c],[ab,bc,ca]]; continue
            if n==1:
                idx=flags.index(True); u,v=edges[idx]; opp=[x for x in tri if x not in (u,v)][0]; uv=mid((u,v))
                new += [[u,uv,opp],[uv,v,opp]]; continue
            # Two split edges necessarily share one vertex. Split into three triangles.
            marked_es=[edges[i] for i,f in enumerate(flags) if f]
            common=set(marked_es[0]).intersection(marked_es[1]).pop()
            others=[]
            for e in marked_es: others.append(e[0] if e[1]==common else e[1])
            o1,o2=others; m1=mid((common,o1)); m2=mid((common,o2))
            # The unsplit edge is o1-o2. This triangulates the quadrilateral without a hanging node.
            new += [[common,m1,m2],[m1,o1,o2],[m1,o2,m2]]
        bfac,_=_boundary_facets(new)
        return {'refined_mesh':{'dimension':2,'vertices':V,'elements':new,'boundary_facets':bfac,'boundary_vertices':_boundary_vertices(bfac)},
                'marked':sorted(marked),'marked_edges':[list(e) for e in sorted(split_edges)]}
    def verify(self,inputs,params,outputs,ctx):
        old=inputs['mesh']; new=outputs['refined_mesh']; V=np.asarray(new['vertices'],float); bfac,counts=_boundary_facets(new['elements'])
        conform=all(n in (1,2) for n in counts.values()) and bfac==new['boundary_facets']
        nondeg=all(_simplex_geometry(V,c)['volume']>0 for c in new['elements'])
        oldpts={tuple(map(float,p)) for p in old['vertices']}; newpts={tuple(map(float,p)) for p in new['vertices']}; preserve=oldpts.issubset(newpts)
        ok=conform and nondeg and preserve and len(outputs['marked'])>=1
        return [VerificationRecord('adaptive-red-green-conformity',EvidenceKind.NUMERICAL,
            'Dörfler-selected cells induce globally shared edge splits and the resulting red/green triangulation has no facet incidence above two or degenerate cells',
            VerificationState.PASS if ok else VerificationState.FAIL,'independent facet-incidence, determinant, and vertex-preservation checks',
            {'marked_cells':outputs['marked'],'split_edges':len(outputs['marked_edges']),'old_elements':len(old['elements']),'new_elements':len(new['elements']),'old_vertices':len(old['vertices']),'new_vertices':len(new['vertices'])})]


class FEMNDCertificate(Module):
    metadata=ModuleMetadata('fem_nd.certificate','FEM ND Certificate Summary','0.3.0','Verification',
        'Summarize topology, algebraic residual, estimator diagnostic, refinement, and convergence-history results without elevating their evidence classes.',Maturity.EXPERIMENTAL)
    inputs=(PortSpec('mesh','simplex_mesh'),PortSpec('residual_inf','number'),PortSpec('estimator','error_estimator_nd'),PortSpec('refined_mesh','simplex_mesh'),PortSpec('history','convergence_history'))
    outputs=(PortSpec('certificate_summary','record'),)
    parameters=(ParameterSpec('residual_tolerance','number',1e-10),)
    proof_status=ProofStatus(evidence={EvidenceKind.NUMERICAL},unit_tests=True,documentation=True,
        limitations=['summary is not a formal proof or general a-posteriori error certificate','authoritative evidence remains in per-node RunCertificates and graph certificate'])
    def execute(self,inputs,params,ctx):
        hist=inputs['history']['records']; r=float(inputs['residual_inf']); tol=float(params['residual_tolerance'])
        return {'certificate_summary':{'dimension':inputs['mesh']['dimension'],'vertices':len(inputs['mesh']['vertices']),'elements':len(inputs['mesh']['elements']),
            'residual_inf':r,'residual_tolerance':tol,'residual_pass':r<=tol,'estimator':float(inputs['estimator']['eta']),
            'refined_vertices':len(inputs['refined_mesh']['vertices']),'refined_elements':len(inputs['refined_mesh']['elements']),
            'history_levels':len(hist),'h_initial':hist[0]['h_max'],'h_final':hist[-1]['h_max'],'history_max_residual':max(x['residual_inf'] for x in hist)}}
    def verify(self,inputs,params,outputs,ctx):
        s=outputs['certificate_summary']; ok=s['residual_pass'] and s['h_final']<s['h_initial'] and s['history_max_residual']<=s['residual_tolerance']
        return [VerificationRecord('fem-nd-summary-consistency',EvidenceKind.NUMERICAL,
            'summary is consistent with residual tolerance and refinement history; it does not certify a general PDE error bound',
            VerificationState.PASS if ok else VerificationState.FAIL,'aggregation/invariant check only',s)]


def register_fem_nd(registry):
    for cls in (SimplexMeshND,P1SimplexSpaceND,SimplexQuadratureND,PoissonAssemblyND,LinearSolverND,AlgebraicResidualND,ResidualEstimatorND,UniformRefinementND,AdaptiveRefinement2D,ConvergenceStudyND,FEMNDCertificate):
        registry.register(cls)
