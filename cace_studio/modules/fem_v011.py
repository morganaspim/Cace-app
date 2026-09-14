from __future__ import annotations
import math, os
import numpy as np

from cace_studio.core.module import Module, ValidationError
from cace_studio.core.types import ModuleMetadata, PortSpec, ParameterSpec, ProofStatus, Maturity, EvidenceKind
from cace_studio.core.verification import VerificationRecord, VerificationState
from cace_studio.modules.fem_nd import P1SimplexSpaceND, PoissonAssemblyND, LinearSolverND, ResidualEstimatorND, AdaptiveRefinement2D
from cace_studio.modules.fem_v010 import _verified_enclosure
from cace_studio.modules.fem_nd import _dense


def _run_iteration(mesh, source, theta, ctx):
    space=P1SimplexSpaceND().execute({'mesh':mesh},{},ctx)['space']
    system=PoissonAssemblyND().execute({'mesh':mesh,'space':space},{'source':source},ctx)['system']
    solution=LinearSolverND().execute({'system':system},{},ctx)['solution']
    A=_dense(system['matrix']); b=np.asarray(system['rhs'],float); x=np.asarray(solution['interior'],float)
    enclosure=_verified_enclosure(A,b,x)
    estimator=ResidualEstimatorND().execute({'mesh':mesh,'solution':solution},{'source':source},ctx)['estimator']
    refined=None; marked=[]
    if len(mesh['elements']) and len(estimator['element_eta']):
        out=AdaptiveRefinement2D().execute({'mesh':mesh,'estimator':estimator},{'theta':theta},ctx)
        refined=out['refined_mesh']; marked=out['marked']
    return space,system,solution,enclosure,estimator,refined,marked


class CertifiedAdaptiveSolveLoop2D(Module):
    metadata=ModuleMetadata('fem11.adaptive_certified_loop','Certified Adaptive Solve Loop 2D','0.11.0','Certified FEM',
        'Repeat solve -> verified discrete enclosure -> estimator -> Dörfler mark -> conforming refinement while preserving every iteration as a research artifact.',Maturity.BETA,
        assumptions=('2D conforming P1 triangle mesh','constant source','homogeneous Dirichlet data on detected boundary','red/green refinement from fem_nd.adapt2d'))
    inputs=(PortSpec('mesh','simplex_mesh'),)
    outputs=(PortSpec('adaptive_run','certified_adaptive_history'),PortSpec('final_mesh','simplex_mesh'),PortSpec('final_solution','fem_solution_nd'),PortSpec('final_enclosure','verified_solution_enclosure'))
    parameters=(
        ParameterSpec('source','number',1.0),
        ParameterSpec('theta','number',0.5),
        ParameterSpec('max_iterations','integer',5),
        ParameterSpec('stop_mode','string','discrete_enclosure_radius'),
        ParameterSpec('tolerance','number',1e-12),
    )
    proof_status=ProofStatus(evidence={EvidenceKind.INTERVAL,EvidenceKind.NUMERICAL},unit_tests=True,property_tests=True,documentation=True,
        limitations=['estimator_upper stopping certifies the estimator magnitude, not continuum FEM error','continuum_error stopping is deliberately unsupported until a matching reliability theorem is machine-dischargeable','reference sparse solve/enclosure currently densifies reduced CSR matrices'])
    def validate(self,inputs,params):
        super().validate(inputs,params); p=self.resolved_params(params); m=inputs['mesh']
        if m['dimension']!=2: raise ValidationError('v0.11 adaptive loop currently supports 2D triangles only')
        if not (0<float(p['theta'])<=1): raise ValidationError('theta must satisfy 0 < theta <= 1')
        if int(p['max_iterations'])<1: raise ValidationError('max_iterations must be >= 1')
        if float(p['tolerance'])<0: raise ValidationError('tolerance must be nonnegative')
        if p['stop_mode'] not in ('discrete_enclosure_radius','estimator_upper','continuum_error'):
            raise ValidationError('unknown stop_mode')
    def execute(self,inputs,params,ctx):
        p=self.resolved_params(params); source=float(p['source']); theta=float(p['theta']); maxit=int(p['max_iterations']); tol=float(p['tolerance']); mode=str(p['stop_mode'])
        if mode=='continuum_error':
            raise ValidationError('continuum_error stopping is not available in v0.11: no mesh-uniform reliability theorem is machine-dischargeable')
        mesh=inputs['mesh']; history=[]; final_solution=None; final_enclosure=None; stop_reason='max_iterations'
        for level in range(maxit):
            space,system,solution,enclosure,estimator,refined,marked=_run_iteration(mesh,source,theta,ctx)
            radius=float(enclosure.get('radius',math.inf)) if enclosure.get('certified') else math.inf
            eta=float(estimator['eta'])
            rec={
                'iteration':level,'vertices':len(mesh['vertices']),'elements':len(mesh['elements']),
                'interior_dofs':len(system['interior_dofs']),'estimator':eta,'element_eta':list(map(float,estimator['element_eta'])),
                'discrete_enclosure_certified':bool(enclosure.get('certified')),'enclosure_radius':radius,
                'q_upper':float(enclosure.get('q_upper',math.inf)),'marked_cells':list(map(int,marked)),
            }
            history.append(rec); final_solution=solution; final_enclosure=enclosure
            stop=False
            if mode=='discrete_enclosure_radius' and enclosure.get('certified') and radius<=tol:
                stop=True; stop_reason='certified_discrete_enclosure_tolerance'
            elif mode=='estimator_upper' and eta<=tol:
                stop=True; stop_reason='certified_estimator_magnitude_tolerance'
            if stop or level==maxit-1 or refined is None:
                break
            mesh=refined
        return {'adaptive_run':{'schema_version':1,'stop_mode':mode,'tolerance':tol,'stop_reason':stop_reason,'iterations':history,
                'continuum_error_certified':False,'note':'estimator tolerance is not a continuum-error certificate without a matching reliability theorem'},
                'final_mesh':mesh,'final_solution':final_solution,'final_enclosure':final_enclosure}
    def verify(self,inputs,params,outputs,ctx):
        run=outputs['adaptive_run']; hist=run['iterations']; enclosure=outputs['final_enclosure']
        basic=bool(hist) and all(r['vertices']>0 and r['elements']>0 and math.isfinite(r['estimator']) and r['estimator']>=0 for r in hist)
        growth=all(hist[i+1]['elements']>hist[i]['elements'] for i in range(len(hist)-1))
        certified=bool(enclosure.get('certified'))
        stop_ok=True
        if run['stop_reason']=='certified_discrete_enclosure_tolerance': stop_ok=certified and float(enclosure['radius'])<=float(run['tolerance'])
        if run['stop_reason']=='certified_estimator_magnitude_tolerance': stop_ok=hist[-1]['estimator']<=float(run['tolerance'])
        ok=basic and growth and certified and stop_ok
        return [VerificationRecord('adaptive-loop-integrity-v011',EvidenceKind.INTERVAL,
            'every adaptive iteration has a valid estimator record, refinement grows the mesh, and the final discrete solution has a verified coefficient enclosure',
            VerificationState.PASS if ok else VerificationState.FAIL,'history invariants plus final interval fixed-point enclosure',
            {'iterations':len(hist),'stop_reason':run['stop_reason'],'final_vertices':hist[-1]['vertices'] if hist else 0,'final_elements':hist[-1]['elements'] if hist else 0,'final_radius':enclosure.get('radius'),'final_estimator':hist[-1]['estimator'] if hist else None})]


class AdaptiveHistoryPlot(Module):
    metadata=ModuleMetadata('viz11.adaptive_history','Adaptive Certification History Plot','0.11.0','Visualization',
        'Render estimator and verified discrete-enclosure radius across adaptive iterations from recorded run data.',Maturity.BETA)
    inputs=(PortSpec('adaptive_run','certified_adaptive_history'),)
    outputs=(PortSpec('visualization','visualization_artifact'),)
    parameters=(ParameterSpec('output_path','string','examples/v11_adaptive_history.png'),)
    proof_status=ProofStatus(evidence={EvidenceKind.EXPERIMENTAL},unit_tests=True,documentation=True,limitations=['plot is an inspection artifact and contributes no proof evidence'])
    def execute(self,inputs,params,ctx):
        import matplotlib; matplotlib.use('Agg',force=True)
        import matplotlib.pyplot as plt
        h=inputs['adaptive_run']['iterations']; x=[r['iteration'] for r in h]; eta=[r['estimator'] for r in h]; rad=[r['enclosure_radius'] for r in h]
        path=str(params['output_path']); os.makedirs(os.path.dirname(path) or '.',exist_ok=True)
        fig,ax=plt.subplots(figsize=(7,5)); ax.semilogy(x,eta,marker='o',label='Estimator'); ax.semilogy(x,rad,marker='s',label='Discrete enclosure radius'); ax.set_xlabel('Adaptive iteration'); ax.set_ylabel('Certified / recorded magnitude'); ax.set_title('CACE v0.11 adaptive certification history'); ax.grid(True,which='both',alpha=.25); ax.legend(); fig.tight_layout(); fig.savefig(path,dpi=140); plt.close(fig)
        return {'visualization':{'path':path,'format':'png','bytes':os.path.getsize(path),'iterations':len(h),'estimator':eta,'enclosure_radius':rad}}
    def verify(self,inputs,params,outputs,ctx):
        a=outputs['visualization']; ok=os.path.exists(a['path']) and a['bytes']>1000
        return [VerificationRecord('v011-adaptive-history-plot-smoke',EvidenceKind.EXPERIMENTAL,'PNG was rendered from actual adaptive-run estimator and certified enclosure data',VerificationState.PASS if ok else VerificationState.FAIL,'headless Matplotlib render',a)]


def register_fem_v011(registry):
    for cls in (CertifiedAdaptiveSolveLoop2D,AdaptiveHistoryPlot): registry.register(cls)
