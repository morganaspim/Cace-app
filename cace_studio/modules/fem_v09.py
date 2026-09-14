from __future__ import annotations
import json, math, os
import numpy as np

from cace_studio.core.module import Module, ValidationError
from cace_studio.core.types import ModuleMetadata, PortSpec, ParameterSpec, ProofStatus, Maturity, EvidenceKind
from cace_studio.core.verification import VerificationRecord, VerificationState
from cace_studio.core.interval import Interval, add, sub, mul, div, sqrt_interval, square, sum_intervals, down, up
from cace_studio.modules.fem_cert2d import _triangle_interval_geometry, _integrate_poly_triangle, _I, _ival, _boundary_facets, _boundary_vertices
from cace_studio.modules.fem_cert2d_general import _tensor_interval, _spd_certificate

THEOREM_RUN_ID='poisson2d-p1-run-reliability-envelope-v0.9'
THEOREM_UNIFORM_ID='poisson2d-p1-mesh-uniform-residual-reliability-v0.9'

def _neg(a): return Interval(-a.hi,-a.lo)
def _dot(a,b): return add(mul(a[0],b[0]),mul(a[1],b[1]))
def _scale(a,c): return mul(a,_I(c))
def _il(x): return [x.lo,x.hi]

def _generic_mesh_contract(mesh):
    if int(mesh.get('dimension',-1))!=2: return False,'dimension must be 2'
    V=np.asarray(mesh.get('vertices',[]),float); E=mesh.get('elements',[])
    if V.ndim!=2 or V.shape[1]!=2 or len(V)<3 or not np.all(np.isfinite(V)): return False,'vertices must be finite 2D coordinates'
    if not E: return False,'mesh has no elements'
    try:
        for c in E:
            if len(c)!=3: return False,'all elements must be triangles'
            if any(int(i)<0 or int(i)>=len(V) for i in c): return False,'element index out of range'
            _triangle_interval_geometry(V,list(map(int,c)))
        _,counts=_boundary_facets(E)
        if any(n not in (1,2) for n in counts.values()): return False,'non-manifold edge incidence'
    except Exception as e: return False,str(e)
    return True,''

def _affine_square_poly(c,lx,ly):
    # (c+lx*x+ly*y)^2
    return {(0,0):_I(c*c),(1,0):_I(2*c*lx),(0,1):_I(2*c*ly),
            (2,0):_I(lx*lx),(0,2):_I(ly*ly),(1,1):_I(2*lx*ly)}

class GeneralTriangleGeometry2D(Module):
    metadata=ModuleMetadata('fem09.geometry','General Certified Triangle Geometry 2D','0.9.0','Certified FEM',
        'Certify interval geometry for any conforming CCW triangular mesh, without requiring the reference-triangle domain.',Maturity.BETA)
    inputs=(PortSpec('mesh','simplex_mesh'),); outputs=(PortSpec('geometry_certificate','triangle_geometry_certificate'),)
    proof_status=ProofStatus(evidence={EvidenceKind.INTERVAL},unit_tests=True,property_tests=True,documentation=True)
    def validate(self,inputs,params):
        super().validate(inputs,params); ok,why=_generic_mesh_contract(inputs['mesh'])
        if not ok: raise ValidationError(why)
    def execute(self,inputs,params,ctx):
        V=np.asarray(inputs['mesh']['vertices'],float); rows=[]
        for k,c in enumerate(inputs['mesh']['elements']):
            g=_triangle_interval_geometry(V,list(map(int,c)))
            rows.append({'element':k,'det_interval':_il(g['det']),'area_interval':_il(g['area']),
                         'gradient_intervals':[[*x] for x in [[_il(z) for z in r] for r in g['grads']]],
                         'edge_length_intervals':[_il(e) for e in g['edges']],'diameter_interval':_il(g['diameter'])})
        return {'geometry_certificate':{'dimension':2,'elements':rows,'certified_nondegenerate':True,'orientation':'CCW','domain_class':'general-triangular-mesh'}}
    def verify(self,inputs,params,outputs,ctx):
        rows=outputs['geometry_certificate']['elements']; ok=all(r['det_interval'][0]>0 for r in rows)
        return [VerificationRecord('general-triangle-interval-geometry',EvidenceKind.INTERVAL,'all triangles are certifiably CCW/nondegenerate with outward-enclosed geometry',VerificationState.PASS if ok else VerificationState.FAIL,'directed interval affine geometry',{'elements':len(rows)})]

class GeneralIntervalAssembly2D(Module):
    metadata=ModuleMetadata('fem09.interval_assembly','General Interval Global Assembly 2D','0.9.0','Certified FEM',
        'Assemble interval-enclosed reduced P1 stiffness matrix on a general triangular mesh for constant SPD diffusion.',Maturity.EXPERIMENTAL)
    inputs=(PortSpec('mesh','simplex_mesh'),PortSpec('diffusion_certificate','diffusion_certificate_2d'))
    outputs=(PortSpec('interval_system','interval_linear_system_2d'),)
    proof_status=ProofStatus(evidence={EvidenceKind.INTERVAL},unit_tests=True,documentation=True)
    def validate(self,inputs,params):
        super().validate(inputs,params); ok,why=_generic_mesh_contract(inputs['mesh'])
        if not ok: raise ValidationError(why)
    def execute(self,inputs,params,ctx):
        m=inputs['mesh']; V=np.asarray(m['vertices'],float); n=len(V); G=[[Interval(0,0) for _ in range(n)] for _ in range(n)]
        A=[[Interval(*x) for x in row] for row in inputs['diffusion_certificate']['tensor']]
        for c in m['elements']:
            ids=list(map(int,c)); g=_triangle_interval_geometry(V,ids)
            for i in range(3):
                Ag=[add(mul(A[0][0],g['grads'][i][0]),mul(A[0][1],g['grads'][i][1])),add(mul(A[1][0],g['grads'][i][0]),mul(A[1][1],g['grads'][i][1]))]
                for j in range(3): G[ids[i]][ids[j]]=add(G[ids[i]][ids[j]],mul(g['area'],_dot(Ag,g['grads'][j])))
        bfac,_=_boundary_facets(m['elements']); bd=set(_boundary_vertices(bfac)); interior=[i for i in range(n) if i not in bd]
        red=[[G[i][j] for j in interior] for i in interior]
        return {'interval_system':{'interior_dofs':interior,'matrix_intervals':[[[_x.lo,_x.hi] for _x in row] for row in red],'dimension':len(interior),'homogeneous_dirichlet':True}}
    def verify(self,inputs,params,outputs,ctx):
        A=outputs['interval_system']['matrix_intervals']; ok=all(A[i][j][0]<=A[j][i][1] and A[j][i][0]<=A[i][j][1] for i in range(len(A)) for j in range(len(A)))
        return [VerificationRecord('general-interval-global-assembly',EvidenceKind.INTERVAL,'global reduced stiffness entries are outward-enclosed and interval-symmetric',VerificationState.PASS if ok else VerificationState.FAIL,'sum certified local interval contributions',{'dimension':len(A)})]

class GeneralAffineSourceNorm2D(Module):
    metadata=ModuleMetadata('fem09.source_norm','General Certified Affine Source Norm 2D','0.9.0','Certified FEM',
        'Certify ||f||_L2 for affine f=c+lx*x+ly*y over any certified triangular mesh by exact element polynomial moments.',Maturity.BETA)
    inputs=(PortSpec('mesh','simplex_mesh'),); outputs=(PortSpec('source_norm_certificate','source_norm_certificate_2d'),)
    parameters=(ParameterSpec('c','number',1.0),ParameterSpec('lx','number',0.0),ParameterSpec('ly','number',0.0))
    proof_status=ProofStatus(evidence={EvidenceKind.INTERVAL,EvidenceKind.SYMBOLIC},unit_tests=True,documentation=True)
    def validate(self,inputs,params):
        super().validate(inputs,params); ok,why=_generic_mesh_contract(inputs['mesh'])
        if not ok: raise ValidationError(why)
    def execute(self,inputs,params,ctx):
        c,lx,ly=map(float,(params['c'],params['lx'],params['ly'])); p=_affine_square_poly(c,lx,ly); V=np.asarray(inputs['mesh']['vertices'],float); total=Interval(0,0); terms=[]
        for k,cell in enumerate(inputs['mesh']['elements']):
            val=_integrate_poly_triangle(p,V[np.asarray(cell,int)]); total=add(total,val); terms.append({'element':k,'source_l2_squared_interval':_il(val)})
        total=Interval(max(0,total.lo),max(0,total.hi)); norm=sqrt_interval(total)
        return {'source_norm_certificate':{'source':[c,lx,ly],'l2_squared_interval':_il(total),'l2_norm_interval':_il(norm),'elements':terms,'certified':True,'domain':'mesh-domain'}}
    def verify(self,inputs,params,outputs,ctx):
        c=outputs['source_norm_certificate']; ok=0<=c['l2_norm_interval'][0]<=c['l2_norm_interval'][1]
        return [VerificationRecord('general-affine-source-l2',EvidenceKind.INTERVAL,'affine source L2 norm is enclosed by exact polynomial integration over every triangle',VerificationState.PASS if ok else VerificationState.FAIL,'exact triangle monomial moments plus outward rounding',c)]

class StripPoincare2D(Module):
    metadata=ModuleMetadata('fem09.poincare','Certified Strip Poincare Constant 2D','0.9.0','Certified FEM',
        'Certify a Dirichlet Poincare constant Cp <= min(width_x,width_y)/pi from mesh bounding-strip widths.',Maturity.EXPERIMENTAL,
        assumptions=('homogeneous Dirichlet trace on the entire mesh boundary','mesh domain is the union of the supplied triangles'))
    inputs=(PortSpec('mesh','simplex_mesh'),); outputs=(PortSpec('poincare_certificate','poincare_certificate_2d'),)
    proof_status=ProofStatus(evidence={EvidenceKind.INTERVAL,EvidenceKind.SYMBOLIC},unit_tests=True,documentation=True,
        limitations=['uses a conservative strip-width bound rather than an optimal domain constant'])
    def validate(self,inputs,params):
        super().validate(inputs,params); ok,why=_generic_mesh_contract(inputs['mesh'])
        if not ok: raise ValidationError(why)
    def execute(self,inputs,params,ctx):
        V=np.asarray(inputs['mesh']['vertices'],float); wx=up(float(V[:,0].max()-V[:,0].min())); wy=up(float(V[:,1].max()-V[:,1].min())); w=min(wx,wy); cp=up(w/down(math.pi))
        return {'poincare_certificate':{'width_x_upper':wx,'width_y_upper':wy,'selected_width_upper':w,'C_p_upper':cp,'certified':w>0,'theorem':'slice-wise 1D Dirichlet Poincare'}}
    def verify(self,inputs,params,outputs,ctx):
        c=outputs['poincare_certificate']; return [VerificationRecord('strip-poincare-2d',EvidenceKind.SYMBOLIC,'for H0^1 functions, slice-wise 1D Poincare yields ||v|| <= width/pi ||grad v||',VerificationState.PASS if c['certified'] else VerificationState.FAIL,'Fubini plus 1D Dirichlet Poincare on line-slice components',c)]

class GeneralStabilityBound2D(Module):
    metadata=ModuleMetadata('fem09.stability','General Exact-Solution-Free Stability Bound 2D','0.9.0','Certified FEM',
        'Bound ||u||_A for homogeneous-Dirichlet Poisson from certified source norm, Poincare constant, and diffusion coercivity.',Maturity.EXPERIMENTAL)
    inputs=(PortSpec('source_norm_certificate','source_norm_certificate_2d'),PortSpec('poincare_certificate','poincare_certificate_2d'),PortSpec('diffusion_certificate','diffusion_certificate_2d'))
    outputs=(PortSpec('stability_certificate','continuum_stability_certificate_2d'),)
    proof_status=ProofStatus(evidence={EvidenceKind.INTERVAL,EvidenceKind.SYMBOLIC},unit_tests=True,documentation=True)
    def execute(self,inputs,params,ctx):
        fhi=float(inputs['source_norm_certificate']['l2_norm_interval'][1]); cp=float(inputs['poincare_certificate']['C_p_upper']); alpha=float(inputs['diffusion_certificate']['coercivity_lower_interval'][0])
        if alpha<=0: return {'stability_certificate':{'certified':False,'status':'not-run'}}
        ub=up(cp*fhi/math.sqrt(alpha)); return {'stability_certificate':{'certified':True,'continuum_solution_energy_upper':ub,'C_p_upper':cp,'source_l2_upper':fhi,'coercivity_lower':alpha,'requires_exact_solution':False}}
    def verify(self,inputs,params,outputs,ctx):
        c=outputs['stability_certificate']; return [VerificationRecord('general-poisson-energy-stability',EvidenceKind.INTERVAL,'weak-form energy stability bound is certified without an exact solution',VerificationState.PASS if c.get('certified') else VerificationState.NOT_RUN,'coercivity plus Cauchy-Schwarz plus certified Poincare',c)]

class GeneralErrorEnvelope2D(Module):
    metadata=ModuleMetadata('fem09.error_envelope','General Continuum Error Envelope 2D','0.9.0','Certified FEM',
        'Combine certified continuum stability and computed FEM energy to enclose ||u-u_h||_A without an exact solution.',Maturity.EXPERIMENTAL)
    inputs=(PortSpec('stability_certificate','continuum_stability_certificate_2d'),PortSpec('computed_energy_certificate','computed_energy_certificate_2d'))
    outputs=(PortSpec('error_envelope','general_error_envelope_2d'),)
    proof_status=ProofStatus(evidence={EvidenceKind.INTERVAL,EvidenceKind.SYMBOLIC},unit_tests=True,documentation=True)
    def execute(self,inputs,params,ctx):
        s=inputs['stability_certificate']; h=inputs['computed_energy_certificate']; ok=s.get('certified') and h.get('certified')
        ub=up(float(s['continuum_solution_energy_upper'])+float(h['energy_interval'][1])) if ok else math.inf
        return {'error_envelope':{'certified':bool(ok),'energy_error_interval':[0.0,ub] if ok else None,'requires_exact_solution':False,'scope':'general-mesh-stability-envelope'}}
    def verify(self,inputs,params,outputs,ctx):
        c=outputs['error_envelope']; return [VerificationRecord('general-continuum-error-envelope',EvidenceKind.INTERVAL,'continuum error is enclosed by triangle inequality using exact-solution-free certified terms',VerificationState.PASS if c['certified'] else VerificationState.NOT_RUN,'||u-u_h||_A <= ||u||_A + ||u_h||_A',c)]

class GeneralResidualEstimatorAffine2D(Module):
    metadata=ModuleMetadata('fem09.residual_estimator','General Certified Residual Estimator 2D','0.9.0','Certified FEM',
        'Interval-enclose the standard P1 residual/jump estimator for affine forcing and constant SPD diffusion on a general triangular mesh.',Maturity.EXPERIMENTAL)
    inputs=(PortSpec('mesh','simplex_mesh'),PortSpec('solution','fem_solution_nd'),PortSpec('diffusion_certificate','diffusion_certificate_2d'))
    outputs=(PortSpec('estimator_certificate','estimator_certificate_2d'),)
    parameters=(ParameterSpec('c','number',1.0),ParameterSpec('lx','number',0.0),ParameterSpec('ly','number',0.0))
    proof_status=ProofStatus(evidence={EvidenceKind.INTERVAL},unit_tests=True,documentation=True,
        limitations=['estimator enclosure is rigorous; mesh-uniform reliability constant remains a separate theorem obligation'])
    def validate(self,inputs,params):
        super().validate(inputs,params); ok,why=_generic_mesh_contract(inputs['mesh'])
        if not ok: raise ValidationError(why)
    def execute(self,inputs,params,ctx):
        m=inputs['mesh']; V=np.asarray(m['vertices'],float); u=np.asarray(inputs['solution']['values'],float); E=[list(map(int,c)) for c in m['elements']]
        A=[[Interval(*x) for x in row] for row in inputs['diffusion_certificate']['tensor']]
        geoms=[_triangle_interval_geometry(V,c) for c in E]; grads=[]; flux=[]
        for c,g in zip(E,geoms):
            gu=[Interval(0,0),Interval(0,0)]
            for a,vi in enumerate(c):
                gu[0]=add(gu[0],mul(_I(u[vi]),g['grads'][a][0])); gu[1]=add(gu[1],mul(_I(u[vi]),g['grads'][a][1]))
            grads.append(gu); flux.append([add(mul(A[0][0],gu[0]),mul(A[0][1],gu[1])),add(mul(A[1][0],gu[0]),mul(A[1][1],gu[1]))])
        f2=_affine_square_poly(float(params['c']),float(params['lx']),float(params['ly'])); eta2=[]
        for c,g in zip(E,geoms): eta2.append(mul(square(g['diameter']),_integrate_poly_triangle(f2,V[np.asarray(c,int)])))
        facet_cells={}
        for k,c in enumerate(E):
            for e in (tuple(sorted((c[0],c[1]))),tuple(sorted((c[1],c[2]))),tuple(sorted((c[2],c[0])))): facet_cells.setdefault(e,[]).append(k)
        for edge,cells in facet_cells.items():
            if len(cells)!=2: continue
            a,b=cells; p,q=V[list(edge)]; dx=sub(_I(q[0]),_I(p[0])); dy=sub(_I(q[1]),_I(p[1])); L=sqrt_interval(add(square(dx),square(dy)))
            nx=div(dy,L); ny=div(_neg(dx),L); jx=sub(flux[a][0],flux[b][0]); jy=sub(flux[a][1],flux[b][1]); jump=add(mul(jx,nx),mul(jy,ny))
            hF=Interval(max(geoms[a]['diameter'].lo,geoms[b]['diameter'].lo),max(geoms[a]['diameter'].hi,geoms[b]['diameter'].hi)); contrib=_scale(mul(mul(hF,L),square(jump)),0.5)
            eta2[a]=add(eta2[a],contrib); eta2[b]=add(eta2[b],contrib)
        total=sum_intervals(eta2); total=Interval(max(0,total.lo),max(0,total.hi)); eta=sqrt_interval(total)
        return {'estimator_certificate':{'eta_squared_interval':_il(total),'eta_interval':_il(eta),'element_eta_squared_intervals':[_il(x) for x in eta2],'certified':True,'source':[float(params['c']),float(params['lx']),float(params['ly'])]}}
    def verify(self,inputs,params,outputs,ctx):
        c=outputs['estimator_certificate']; lo,hi=c['eta_interval']; ok=0<=lo<=hi and math.isfinite(hi)
        return [VerificationRecord('general-affine-residual-estimator-interval',EvidenceKind.INTERVAL,'residual/jump estimator is interval-enclosed on the general mesh',VerificationState.PASS if ok else VerificationState.FAIL,'exact affine source moments plus interval flux jumps',c)]

class TheoremRegistryV2(Module):
    metadata=ModuleMetadata('fem09.theorem_registry_v2','FEM Theorem Registry v2','0.9.0','Formal Verification',
        'Expose structured theorem contracts with premise status, evidence requirements, scope, and proof maturity.',Maturity.BETA)
    outputs=(PortSpec('registry','theorem_registry_snapshot_v2'),)
    proof_status=ProofStatus(evidence={EvidenceKind.SYMBOLIC},unit_tests=True,documentation=True)
    def execute(self,inputs,params,ctx):
        th=[
          {'theorem_id':THEOREM_RUN_ID,'status':'computationally-discharged','scope':'one certified run','formal_evidence':False,
           'statement':'If E<=B, eta>=eta_lo>0 and C>=B/eta_lo, then E<=C eta.',
           'premises':[{'id':'error-envelope','required_evidence':'interval-certified'},{'id':'estimator-lower','required_evidence':'interval-certified'},{'id':'eta-positive','required_evidence':'interval-certified'}]},
          {'theorem_id':THEOREM_UNIFORM_ID,'status':'obligation-only','scope':'mesh family','formal_evidence':False,
           'statement':'There exists a mesh-uniform C_rel depending only on domain/diffusion/shape regularity such that ||u-u_h||_A <= C_rel eta.',
           'premises':[{'id':'shape-regular-family','required_evidence':'formal-or-reviewed'},{'id':'interpolation-constant','required_evidence':'formal'},{'id':'trace-constant','required_evidence':'formal'},{'id':'ellipticity','required_evidence':'interval-certified'}],
           'artifact':'docs/proofs/poisson2d_p1_reliability_v09.lean'}]
        return {'registry':{'schema_version':2,'theorems':th}}
    def verify(self,inputs,params,outputs,ctx):
        r=outputs['registry']; ok=r['schema_version']==2 and all('premises' in t and 'status' in t for t in r['theorems'])
        return [VerificationRecord('theorem-registry-v2-integrity',EvidenceKind.SYMBOLIC,'theorem contracts expose structured premises and cannot imply formal evidence from registration alone',VerificationState.PASS if ok else VerificationState.FAIL,'schema validation',{'theorems':len(r['theorems'])})]

class RunReliabilityEnvelope2D(Module):
    metadata=ModuleMetadata('fem09.reliability_envelope','General Run Reliability Envelope 2D','0.9.0','Certified FEM',
        'Derive a certified run-specific C_rel from an exact-solution-free continuum error envelope and an independently certified estimator lower bound.',Maturity.EXPERIMENTAL)
    inputs=(PortSpec('error_envelope','general_error_envelope_2d'),PortSpec('estimator_certificate','estimator_certificate_2d'))
    outputs=(PortSpec('reliability_certificate','theorem_backed_certificate_2d'),)
    parameters=(ParameterSpec('max_C_rel','number',1000.0),)
    proof_status=ProofStatus(evidence={EvidenceKind.INTERVAL,EvidenceKind.SYMBOLIC},unit_tests=True,documentation=True,
        limitations=['C_rel is run-specific and conservative; this does not prove a mesh-uniform residual reliability theorem'])
    def execute(self,inputs,params,ctx):
        e=inputs['error_envelope']; eta=inputs['estimator_certificate']['eta_interval']; maxC=float(params['max_C_rel'])
        if not e.get('certified') or eta[0]<=0: return {'reliability_certificate':{'certified':False,'status':'not-run','reason':'missing error envelope or nonpositive estimator lower bound'}}
        Ehi=float(e['energy_error_interval'][1]); etalo=float(eta[0]); C=up(Ehi/etalo); passed=C<=maxC
        return {'reliability_certificate':{'theorem_id':THEOREM_RUN_ID,'certified':passed,'status':'pass' if passed else 'not-run','C_rel_run_upper':C,'max_C_rel':maxC,'error_upper':Ehi,'eta_lower':etalo,'formal_evidence':False,'scope':'run-specific-general-mesh'}}
    def verify(self,inputs,params,outputs,ctx):
        c=outputs['reliability_certificate']; state=VerificationState.PASS if c.get('certified') else VerificationState.NOT_RUN
        return [VerificationRecord('general-run-reliability-envelope',EvidenceKind.INTERVAL,'run-specific E <= C_rel eta is discharged without knowing the exact solution',state,'directed quotient of certified error upper and estimator lower bounds',c)]

class GenericReliabilityObligationV09(Module):
    metadata=ModuleMetadata('fem09.uniform_reliability_obligation','Mesh-Uniform 2D Reliability Obligation v0.9','0.9.0','Formal Verification','Export the structured Lean obligation for a mesh-uniform residual reliability theorem.',Maturity.PROTOTYPE)
    outputs=(PortSpec('theorem_artifact','formal_artifact'),)
    proof_status=ProofStatus(evidence=set(),unit_tests=True,documentation=True,formal_artifact='docs/proofs/poisson2d_p1_reliability_v09.lean')
    def execute(self,inputs,params,ctx): return {'theorem_artifact':{'theorem_id':THEOREM_UNIFORM_ID,'language':'Lean4','status':'obligation-only','machine_checked':False,'artifact':'docs/proofs/poisson2d_p1_reliability_v09.lean'}}
    def verify(self,inputs,params,outputs,ctx): return [VerificationRecord('mesh-uniform-reliability-v09',EvidenceKind.FORMAL,'mesh-uniform 2D residual reliability remains an explicit unproved formal obligation',VerificationState.NOT_RUN,'artifact export only',outputs['theorem_artifact'])]

class EstimatorHeatmap2D(Module):
    metadata=ModuleMetadata('viz09.estimator_heatmap','Estimator Heatmap 2D','0.9.0','Visualization','Render elementwise certified estimator contributions on the triangular mesh.',Maturity.BETA)
    inputs=(PortSpec('mesh','simplex_mesh'),PortSpec('estimator_certificate','estimator_certificate_2d'))
    outputs=(PortSpec('visualization','visualization_artifact'),)
    parameters=(ParameterSpec('output_path','string','examples/v09_estimator_heatmap.png'),)
    proof_status=ProofStatus(evidence={EvidenceKind.EXPERIMENTAL},unit_tests=True,documentation=True,limitations=['visualization contributes no proof evidence'])
    def execute(self,inputs,params,ctx):
        import matplotlib; matplotlib.use('Agg',force=True)
        import matplotlib.pyplot as plt
        from matplotlib.collections import PolyCollection
        V=np.asarray(inputs['mesh']['vertices'],float); E=np.asarray(inputs['mesh']['elements'],int); vals=np.asarray([math.sqrt(max(0,x[1])) for x in inputs['estimator_certificate']['element_eta_squared_intervals']],float)
        path=str(params['output_path']); os.makedirs(os.path.dirname(path) or '.',exist_ok=True)
        fig,ax=plt.subplots(figsize=(6,5)); coll=PolyCollection(V[E],array=vals,edgecolors='black'); ax.add_collection(coll); ax.autoscale(); ax.set_aspect('equal'); fig.colorbar(coll,ax=ax,label='element eta upper'); ax.set_xlabel('x'); ax.set_ylabel('y'); ax.set_title('CACE v0.9 certified estimator heatmap'); fig.tight_layout(); fig.savefig(path,dpi=140); plt.close(fig)
        return {'visualization':{'path':path,'format':'png','bytes':os.path.getsize(path),'elements':len(E),'eta_element_upper':vals.tolist()}}
    def verify(self,inputs,params,outputs,ctx):
        a=outputs['visualization']; ok=os.path.exists(a['path']) and a['bytes']>1000
        return [VerificationRecord('v09-estimator-heatmap-smoke',EvidenceKind.EXPERIMENTAL,'heatmap PNG was rendered from actual certified element-estimator data',VerificationState.PASS if ok else VerificationState.FAIL,'headless Matplotlib render',a)]

def register_fem_v09(registry):
    for cls in (GeneralTriangleGeometry2D,GeneralIntervalAssembly2D,GeneralAffineSourceNorm2D,StripPoincare2D,GeneralStabilityBound2D,GeneralErrorEnvelope2D,GeneralResidualEstimatorAffine2D,TheoremRegistryV2,RunReliabilityEnvelope2D,GenericReliabilityObligationV09,EstimatorHeatmap2D): registry.register(cls)
