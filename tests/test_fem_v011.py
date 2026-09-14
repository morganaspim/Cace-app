import json
from cace_studio.core.module import ExecutionContext, ValidationError
from cace_studio.modules.fem_nd import SimplexMeshND
from cace_studio.modules.fem_v011 import CertifiedAdaptiveSolveLoop2D, AdaptiveHistoryPlot


def ctx(): return ExecutionContext(run_id='test-v011')

def mesh():
    p={'vertices':json.dumps([[0,0],[1,0],[1,1],[0,1],[.5,.5]]),'elements':json.dumps([[0,1,4],[1,2,4],[2,3,4],[3,0,4]])}
    m=SimplexMeshND(); m.validate({},p); return m.execute({},p,ctx())['mesh']

def test_adaptive_loop_multiple_iterations_and_final_enclosure():
    mod=CertifiedAdaptiveSolveLoop2D(); inp={'mesh':mesh()}; p={'source':1.0,'theta':0.5,'max_iterations':3,'stop_mode':'estimator_upper','tolerance':0.0}
    mod.validate(inp,p); out=mod.execute(inp,p,ctx()); h=out['adaptive_run']['iterations']
    assert len(h)==3
    assert h[1]['elements']>h[0]['elements'] and h[2]['elements']>h[1]['elements']
    assert out['final_enclosure']['certified']
    assert mod.verify(inp,p,out,ctx())[0].passed

def test_discrete_enclosure_stop_is_certified():
    mod=CertifiedAdaptiveSolveLoop2D(); inp={'mesh':mesh()}; p={'source':1.0,'theta':0.5,'max_iterations':5,'stop_mode':'discrete_enclosure_radius','tolerance':1e-12}
    out=mod.execute(inp,p,ctx())
    assert out['adaptive_run']['stop_reason']=='certified_discrete_enclosure_tolerance'
    assert len(out['adaptive_run']['iterations'])==1
    assert out['final_enclosure']['radius']<=1e-12

def test_continuum_stop_refuses_without_general_theorem():
    mod=CertifiedAdaptiveSolveLoop2D(); inp={'mesh':mesh()}; p={'source':1.0,'theta':0.5,'max_iterations':2,'stop_mode':'continuum_error','tolerance':1e-2}
    mod.validate(inp,p)
    try: mod.execute(inp,p,ctx())
    except ValidationError as e: assert 'not available' in str(e)
    else: raise AssertionError('continuum_error mode must refuse')

def test_adaptive_history_visualization(tmp_path):
    mod=CertifiedAdaptiveSolveLoop2D(); inp={'mesh':mesh()}; p={'source':1.0,'theta':0.5,'max_iterations':3,'stop_mode':'estimator_upper','tolerance':0.0}
    out=mod.execute(inp,p,ctx()); path=tmp_path/'adaptive.png'; plot=AdaptiveHistoryPlot(); art=plot.execute({'adaptive_run':out['adaptive_run']},{'output_path':str(path)},ctx())
    assert path.exists() and path.stat().st_size>1000 and path.read_bytes()[:8]==b'\x89PNG\r\n\x1a\n'
    assert plot.verify({}, {}, art, ctx())[0].passed
