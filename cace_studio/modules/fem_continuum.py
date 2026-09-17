from __future__ import annotations
import hashlib
import json
import math
import numpy as np
from cace_studio.core.module import Module, ValidationError
from cace_studio.core.proof_contract import ProofContractRegistry
from cace_studio.core.types import ModuleMetadata,PortSpec,ParameterSpec,ProofStatus,Maturity,EvidenceKind
from cace_studio.core.verification import VerificationRecord,VerificationState
from cace_studio.core.interval import Interval,singleton,sub,abs_interval,add,div,cube,sqrt_interval,up,square,sum_intervals
from cace_studio.modules.fem_nd import _simplex_geometry,_facet_tuples

THEOREM_ID='poisson1d-p1-constant-v1'
RIEZ_CLAIM_ID='cace.v330.continuum-proof-strengthening'
RIEZ_THEOREM='CACEFormal.Continuum.h1RieszSymbol_norm_le_one'
PRAGER_SYNG_THEOREM='CACEFormal.Continuum.continuumPragerSynge_of_weakGreen'
HYPOTHESIS_PACKET_SCHEMA='cace-runtime-formal-hypothesis-packet-v1'


def _edges_cover_unit_interval(mesh):
    if int(mesh['dimension']) != 1:
        return False, 'dimension must be 1'
    xs=np.asarray(mesh['vertices'],float).reshape(-1)
    if not np.all(np.isfinite(xs)):
        return False,'nonfinite coordinates'
    order=np.argsort(xs); sx=xs[order]
    if len(sx)<2 or abs(float(sx[0]))>1e-14 or abs(float(sx[-1])-1.0)>1e-14:
        return False,'mesh endpoints must be 0 and 1'
    if np.any(np.diff(sx)<=0):
        return False,'coordinates must be strictly increasing'
    pos={int(v):i for i,v in enumerate(order.tolist())}
    expected={tuple(sorted((int(order[i]),int(order[i+1])))) for i in range(len(order)-1)}
    got={tuple(sorted(map(int,e))) for e in mesh['elements']}
    if got != expected:
        return False,'elements must form exactly the adjacent partition of [0,1]'
    return True,''


def _edge_length_interval(x0:float,x1:float):
    return abs_interval(sub(singleton(float(x1)),singleton(float(x0))))


def _canonical_sha256(value):
    payload=json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode('utf-8')
    return hashlib.sha256(payload).hexdigest()


def _riesz_norm_interval(vector,index):
    coords=[singleton(float(value)) for value in vector]
    norm_sq=sum_intervals(square(coord) for coord in coords)
    norm_sq=Interval(max(0.0,norm_sq.lo),max(0.0,norm_sq.hi))
    denom_sq=add(singleton(1.0),norm_sq)
    denom=sqrt_interval(Interval(max(0.0,denom_sq.lo),denom_sq.hi))
    return div(abs_interval(coords[index]),denom)


def _binary64_product_interval(a,b):
    product=float(a)*float(b)
    if not math.isfinite(product):
        raise ValidationError('Prager-Synge adapter product exceeds the audited binary64 interval range')
    return Interval(math.nextafter(product,-math.inf),math.nextafter(product,math.inf))


def _dot_interval(left,right):
    return sum_intervals(_binary64_product_interval(a,b) for a,b in zip(left,right))


class MeshShapeCertificate(Module):
    metadata=ModuleMetadata('fem_cont.mesh_shape','Mesh Shape / Regularity Certificate','0.5.0','Certified FEM',
        'Compute simplex shape metrics and, in 1D, outward-rounded element-length intervals used by continuum certificates.',Maturity.BETA,
        assumptions=('input mesh is conforming and nondegenerate',))
    inputs=(PortSpec('mesh','simplex_mesh'),); outputs=(PortSpec('shape_certificate','mesh_shape_certificate'),)
    parameters=(ParameterSpec('max_shape_ratio','number',50.0,'diagnostic h/r threshold for d>=2'),)
    proof_status=ProofStatus(evidence={EvidenceKind.NUMERICAL,EvidenceKind.INTERVAL},unit_tests=True,property_tests=True,documentation=True,
        limitations=['d>=2 inradius/shape-ratio values are floating-point diagnostics in v0.5; interval geometry inversion remains future work'])
    def execute(self,inputs,params,ctx):
        m=inputs['mesh']; V=np.asarray(m['vertices'],float); d=int(m['dimension']); rows=[]
        if d==1:
            for k,c in enumerate(m['elements']):
                h=_edge_length_interval(V[c[0],0],V[c[1],0])
                rows.append({'element':k,'h_interval':h.to_list(),'shape_ratio':2.0})
            maxratio=2.0
        else:
            ratios=[]
            for k,c in enumerate(m['elements']):
                g=_simplex_geometry(V,c); vol=float(g['volume']); h=float(g['diameter'])
                X=V[np.asarray(c,int)]
                facet_measure=0.0
                for f in _facet_tuples(list(range(d+1))):
                    pts=X[np.asarray(f,int)]
                    if d==2: facet_measure += float(np.linalg.norm(pts[1]-pts[0]))
                    else: facet_measure += float(np.linalg.norm(np.cross(pts[1]-pts[0],pts[2]-pts[0])))/2.0
                rin=d*vol/facet_measure
                ratio=h/rin
                ratios.append(ratio); rows.append({'element':k,'diameter':h,'inradius':rin,'shape_ratio':ratio})
            maxratio=max(ratios) if ratios else 0.0
        return {'shape_certificate':{'dimension':d,'elements':rows,'max_shape_ratio':maxratio,'threshold':float(params['max_shape_ratio']),
                                     'shape_regular':bool(maxratio<=float(params['max_shape_ratio']))}}
    def verify(self,inputs,params,outputs,ctx):
        c=outputs['shape_certificate']; ok=math.isfinite(float(c['max_shape_ratio'])) and all((r.get('shape_ratio',0)>0) for r in c['elements'])
        return [VerificationRecord('mesh-shape-certificate',EvidenceKind.INTERVAL if c['dimension']==1 else EvidenceKind.NUMERICAL,
            'mesh element shape metrics are finite; 1D element lengths are outward-rounded intervals',VerificationState.PASS if ok else VerificationState.FAIL,
            'simplex metric recomputation with interval edge lengths in 1D',{'dimension':c['dimension'],'max_shape_ratio':c['max_shape_ratio'],'shape_regular':c['shape_regular']})]


class Poisson1DContinuumCertificate(Module):
    metadata=ModuleMetadata('fem_cont.poisson1d_continuum','Poisson 1D Continuum Error Certificate','0.5.0','Certified FEM',
        'For -u"=1 on [0,1], u(0)=u(1)=0, certify the P1 Galerkin energy discretization error on an arbitrary conforming 1D mesh using sum(h_K^3/12).',Maturity.EXPERIMENTAL,
        assumptions=('dimension is 1','domain is exactly [0,1]','P1 conforming mesh partitions the interval','diffusion is 1','forcing is 1','homogeneous Dirichlet endpoints'))
    inputs=(PortSpec('mesh','simplex_mesh'),PortSpec('problem','certified_poisson_problem'),PortSpec('shape_certificate','mesh_shape_certificate'))
    outputs=(PortSpec('continuum_certificate','continuum_error_certificate'),)
    proof_status=ProofStatus(evidence={EvidenceKind.INTERVAL,EvidenceKind.SYMBOLIC},unit_tests=True,property_tests=True,documentation=True,
        limitations=['the theorem is scoped only to the stated 1D constant-coefficient benchmark','formal Lean proof is exported separately but not yet checked by Lean'])
    def validate(self,inputs,params):
        super().validate(inputs,params)
        m=inputs['mesh']; p=inputs['problem']
        ok,reason=_edges_cover_unit_interval(m)
        if not ok: raise ValidationError(reason)
        if p.get('dimension')!=1: raise ValidationError('problem dimension must be 1')
        diff=p.get('diffusion')
        try: d=float(diff)
        except Exception: raise ValidationError('v0.5 theorem requires scalar diffusion=1')
        if abs(d-1.0)>0: raise ValidationError('v0.5 theorem requires diffusion=1 exactly')
        if abs(float(p.get('source_constant',0))-1.0)>0 or list(p.get('source_linear',[])) not in ([],[0.0]):
            raise ValidationError('v0.5 theorem requires forcing f=1 exactly')
    def execute(self,inputs,params,ctx):
        m=inputs['mesh']; V=np.asarray(m['vertices'],float)
        total=Interval(0.0,0.0)
        terms=[]
        twelve=singleton(12.0)
        for k,c in enumerate(m['elements']):
            h=_edge_length_interval(V[c[0],0],V[c[1],0])
            e2=div(cube(h),twelve)
            total=add(total,e2)
            terms.append({'element':k,'h_interval':h.to_list(),'energy_error_squared_interval':e2.to_list()})
        energy=sqrt_interval(Interval(max(0.0,total.lo),max(0.0,total.hi)))
        return {'continuum_certificate':{'theorem_id':THEOREM_ID,'certified':True,'scope':'continuum-P1-Galerkin-discretization-error',
            'energy_error_squared_interval':total.to_list(),'energy_error_interval':energy.to_list(),'elements':terms,
            'identity':'||u-u_h||_E^2 = sum_K h_K^3/12','exact_solution':'u(x)=x(1-x)/2'}}
    def verify(self,inputs,params,outputs,ctx):
        c=outputs['continuum_certificate']; lo,hi=c['energy_error_interval']; ok=(c['certified'] and 0<=lo<=hi and c['theorem_id']==THEOREM_ID)
        return [VerificationRecord('poisson1d-continuum-energy-certificate',EvidenceKind.INTERVAL,
            'for the scoped 1D Poisson theorem, the exact P1 Galerkin continuum energy error is enclosed by outward-rounded interval arithmetic',
            VerificationState.PASS if ok else VerificationState.FAIL,'closed-form element identity h^3/12 plus directed interval arithmetic',
            {'energy_error_lower':lo,'energy_error_upper':hi,'elements':len(c['elements'])})]


class TotalContinuumErrorCertificate(Module):
    metadata=ModuleMetadata('fem_cont.total_error','Total Continuum + Algebraic Error Certificate','0.5.0','Certified FEM',
        'Combine a certified continuum Galerkin discretization error with a certified algebraic energy error by the triangle inequality.',Maturity.EXPERIMENTAL)
    inputs=(PortSpec('continuum_certificate','continuum_error_certificate'),PortSpec('algebraic_error_certificate','algebraic_error_certificate'))
    outputs=(PortSpec('total_error_certificate','total_error_certificate'),)
    proof_status=ProofStatus(evidence={EvidenceKind.INTERVAL,EvidenceKind.SYMBOLIC},unit_tests=True,documentation=True)
    def execute(self,inputs,params,ctx):
        c=inputs['continuum_certificate']; a=inputs['algebraic_error_certificate']
        if not c.get('certified') or not a.get('certified'):
            return {'total_error_certificate':{'certified':False,'reason':'both continuum and algebraic certificates must be certified'}}
        cu=float(c['energy_error_interval'][1]); au=float(a['energy_error_upper']); total=up(cu+au)
        return {'total_error_certificate':{'certified':True,'norm':'energy','upper':total,'continuum_upper':cu,'algebraic_upper':au,
            'bound':'||u-u_hat||_E <= ||u-u_h*||_E + ||u_h*-u_hat||_E'}}
    def verify(self,inputs,params,outputs,ctx):
        c=outputs['total_error_certificate']; state=VerificationState.PASS if c.get('certified') else VerificationState.NOT_RUN
        return [VerificationRecord('total-continuum-error-triangle-bound',EvidenceKind.INTERVAL,
            'combined continuum-to-computed-solution energy error follows by triangle inequality from two certified component bounds',state,
            'triangle inequality over certified energy-norm component upper bounds',c)]


class H1RieszSymbolHypothesisAdapter(Module):
    metadata=ModuleMetadata(
        'fem_cont.h1_riesz_hypothesis_adapter',
        'H1 Riesz Symbol Hypothesis Adapter',
        '3.41.0',
        'Formal Runtime Adapter',
        'Connect a qualified v3.30 theorem endpoint descriptor to concrete Euclidean runtime data and certify the Riesz-symbol bound with outward-rounded interval arithmetic.',
        Maturity.BETA,
        assumptions=(
            'the upstream theorem endpoint descriptor is produced by formal330.qualified_theorem_endpoint',
            'the runtime vector represents a concrete EuclideanDomain coordinate vector',
        ),
    )
    inputs=(PortSpec('theorem_endpoint','object'),PortSpec('vector','array'))
    outputs=(PortSpec('hypothesis_packet','formal_hypothesis_packet'),)
    parameters=(ParameterSpec('index','int',0,'Coordinate index corresponding to Lean Fin n.'),)
    proof_status=ProofStatus(
        evidence={EvidenceKind.INTERVAL,EvidenceKind.SYMBOLIC},
        unit_tests=True,
        regression_tests=True,
        documentation=True,
        limitations=[
            'This adapter does not emit FORMAL evidence and does not instantiate Lean terms.',
            'Formal proof provenance remains an independent upstream verification record.',
            'PASS certifies only the runtime representation obligations and interval evaluation recorded in the packet.',
        ],
    )

    @staticmethod
    def _contract():
        return ProofContractRegistry.load_default().for_claim(RIEZ_CLAIM_ID)

    def validate(self,inputs,params):
        super().validate(inputs,params)
        vector=np.asarray(inputs['vector'],dtype=float)
        if vector.ndim != 1 or vector.size == 0:
            raise ValidationError('Riesz adapter requires a non-empty one-dimensional vector')
        if not np.all(np.isfinite(vector)):
            raise ValidationError('Riesz adapter vector coordinates must be finite')
        if np.max(np.abs(vector)) > 1e150:
            raise ValidationError('Riesz adapter coordinates exceed the audited binary64 interval range')
        try:
            int(params['index'])
        except Exception as exc:
            raise ValidationError('Riesz adapter index must be an integer') from exc

    def _packet(self,inputs,params):
        endpoint=inputs['theorem_endpoint']
        vector=np.asarray(inputs['vector'],dtype=float)
        index=int(params['index'])
        contract=self._contract()
        endpoint_ok=bool(
            isinstance(endpoint,dict)
            and contract is not None
            and endpoint.get('claim_id') == RIEZ_CLAIM_ID
            and endpoint.get('theorem_name') == RIEZ_THEOREM
            and endpoint.get('endpoint_member') is True
            and endpoint.get('proof_contract_id') == contract.contract_id
            and endpoint.get('proof_contract_sha256') == contract.contract_sha256
            and RIEZ_THEOREM in contract.endpoint_theorems
        )
        index_ok=0 <= index < int(vector.size)
        bound_interval=None
        bound_ok=False
        if index_ok:
            bound=_riesz_norm_interval(vector,index)
            bound_interval=bound.to_list()
            bound_ok=bool(bound.hi <= 1.0)
        obligations=[
            {
                'id':'canonical-endpoint-descriptor',
                'theorem_interface':'qualified endpoint identity and current proof-contract identity',
                'state':'pass' if endpoint_ok else 'fail',
                'method':'exact claim/theorem/contract-id/contract-sha comparison against the current canonical proof contract',
            },
            {
                'id':'euclidean-runtime-vector',
                'theorem_interface':'x : EuclideanDomain n',
                'state':'pass',
                'method':'non-empty one-dimensional finite binary64 coordinate vector checked during module validation',
                'dimension':int(vector.size),
            },
            {
                'id':'fin-index-range',
                'theorem_interface':'i : Fin n',
                'state':'pass' if index_ok else 'fail',
                'method':'integer range check 0 <= index < dimension',
                'index':index,
                'dimension':int(vector.size),
            },
            {
                'id':'riesz-symbol-bound-cross-check',
                'theorem_interface':'norm (h1RieszSymbol i x) <= 1',
                'state':'pass' if bound_ok else ('not-run' if not index_ok else 'fail'),
                'method':'outward-rounded interval evaluation of abs(x_i)/sqrt(1+sum_j x_j^2)',
                'norm_interval':bound_interval,
            },
        ]
        packet={
            'schema':HYPOTHESIS_PACKET_SCHEMA,
            'claim_id':RIEZ_CLAIM_ID,
            'theorem_name':RIEZ_THEOREM,
            'proof_contract_id':contract.contract_id if contract else None,
            'proof_contract_sha256':contract.contract_sha256 if contract else None,
            'theorem_explicit_hypotheses':[],
            'runtime_representation_obligations':obligations,
            'runtime_ready':all(item['state']=='pass' for item in obligations),
            'formal_instantiation':False,
            'formal_provenance_source':'upstream verification record for formal330.qualified_theorem_endpoint',
            'scope_note':'This packet checks the concrete runtime representation and an interval cross-check of the theorem conclusion; it does not transfer Lean proof status to the numerical computation.',
        }
        packet['packet_sha256']=_canonical_sha256(packet)
        return packet

    def execute(self,inputs,params,ctx):
        return {'hypothesis_packet':self._packet(inputs,params)}

    def verify(self,inputs,params,outputs,ctx):
        expected=self._packet(inputs,params)
        actual=outputs.get('hypothesis_packet')
        consistent=isinstance(actual,dict) and actual == expected
        passed=bool(consistent and expected['runtime_ready'])
        return [VerificationRecord(
            'h1-riesz-runtime-hypothesis-adapter',
            EvidenceKind.INTERVAL,
            'runtime representation obligations for the qualified h1RieszSymbol_norm_le_one endpoint are checked and the concrete symbol norm is interval-enclosed by 1',
            VerificationState.PASS if passed else VerificationState.FAIL,
            'canonical endpoint descriptor comparison plus outward-rounded interval evaluation',
            {
                'theorem_name':RIEZ_THEOREM,
                'runtime_ready':expected['runtime_ready'],
                'packet_sha256':expected['packet_sha256'],
                'formal_instantiation':False,
                'output_consistent':consistent,
            },
            notes=(
                'Formal theorem provenance is separate and must come from the upstream formal330 verification record.',
                'This adapter cannot promote numerical or interval evidence to FORMAL evidence.',
            ),
        )]


class PragerSyngeHypothesisInventoryAdapter(Module):
    metadata=ModuleMetadata(
        'fem_cont.prager_synge_hypothesis_adapter',
        'Continuum Prager-Synge Hypothesis Adapter',
        '3.42.0',
        'Formal Runtime Adapter',
        'Inventory the exact premises of continuumPragerSynge_of_weakGreen against a qualified endpoint descriptor and concrete error vectors without pretending unresolved abstract Lean structures are satisfied.',
        Maturity.BETA,
        assumptions=(
            'the upstream theorem endpoint descriptor is produced by formal330.qualified_theorem_endpoint',
            'e_grad and e_flux are concrete coordinates in a common finite-dimensional real inner-product representation used only for diagnostics',
        ),
    )
    inputs=(PortSpec('theorem_endpoint','object'),PortSpec('e_grad','array'),PortSpec('e_flux','array'))
    outputs=(PortSpec('hypothesis_packet','formal_hypothesis_packet'),)
    proof_status=ProofStatus(
        evidence={EvidenceKind.SYMBOLIC,EvidenceKind.INTERVAL},
        unit_tests=True,
        regression_tests=True,
        documentation=True,
        limitations=[
            'This adapter deliberately leaves BoundedGreenPairing, GreenSmoothCore, HasZeroBoundaryTrace, and the exact weak-Green cross-term identity unresolved.',
            'Numerical orthogonality or a near-zero cross term does not instantiate the Lean theorem hypotheses.',
            'This adapter never emits FORMAL evidence and runtime_ready remains false until dedicated bridge certificates are implemented and independently bound.',
        ],
    )

    @staticmethod
    def _contract():
        return ProofContractRegistry.load_default().for_claim(RIEZ_CLAIM_ID)

    def validate(self,inputs,params):
        super().validate(inputs,params)
        e_grad=np.asarray(inputs['e_grad'],dtype=float)
        e_flux=np.asarray(inputs['e_flux'],dtype=float)
        if e_grad.ndim != 1 or e_flux.ndim != 1 or e_grad.size == 0 or e_flux.size == 0:
            raise ValidationError('Prager-Synge adapter requires non-empty one-dimensional error vectors')
        if e_grad.shape != e_flux.shape:
            raise ValidationError('Prager-Synge adapter error vectors must have identical dimensions')
        if not np.all(np.isfinite(e_grad)) or not np.all(np.isfinite(e_flux)):
            raise ValidationError('Prager-Synge adapter error-vector coordinates must be finite')
        if max(float(np.max(np.abs(e_grad))),float(np.max(np.abs(e_flux)))) > 1e150:
            raise ValidationError('Prager-Synge adapter coordinates exceed the audited binary64 interval range')

    def _packet(self,inputs):
        endpoint=inputs['theorem_endpoint']
        e_grad=np.asarray(inputs['e_grad'],dtype=float)
        e_flux=np.asarray(inputs['e_flux'],dtype=float)
        contract=self._contract()
        endpoint_ok=bool(
            isinstance(endpoint,dict)
            and contract is not None
            and endpoint.get('claim_id') == RIEZ_CLAIM_ID
            and endpoint.get('theorem_name') == PRAGER_SYNG_THEOREM
            and endpoint.get('endpoint_member') is True
            and endpoint.get('proof_contract_id') == contract.contract_id
            and endpoint.get('proof_contract_sha256') == contract.contract_sha256
            and PRAGER_SYNG_THEOREM in contract.endpoint_theorems
        )
        inner=_dot_interval(e_grad,e_flux)
        gap=add(inner,inner)
        zero_consistent=bool(gap.lo <= 0.0 <= gap.hi)
        explicit_hypotheses=[
            {
                'id':'bounded-green-pairing',
                'lean_interface':'G : BoundedGreenPairing V Q',
                'state':'unresolved',
                'resolution_requirement':'a dedicated executable bridge must construct and bind the concrete runtime Green pairing to the qualified Lean interface',
            },
            {
                'id':'green-smooth-core',
                'lean_interface':'C : GreenSmoothCore G',
                'state':'unresolved',
                'resolution_requirement':'a dedicated executable bridge must establish the smooth-core/density structure for the same bound Green pairing',
            },
            {
                'id':'zero-boundary-trace',
                'lean_interface':'hv : HasZeroBoundaryTrace G v',
                'state':'unresolved',
                'resolution_requirement':'a boundary-trace bridge certificate must connect concrete runtime data to HasZeroBoundaryTrace for the same G and v',
            },
            {
                'id':'weak-green-cross-term-identity',
                'lean_interface':'hcross : inner real eGrad eFlux = G.volumePairing q v',
                'state':'unresolved',
                'resolution_requirement':'an exact weak-Green bridge certificate is required; numerical orthogonality or interval overlap is diagnostic only',
            },
        ]
        runtime_obligations=[
            {
                'id':'canonical-endpoint-descriptor',
                'theorem_interface':'qualified endpoint identity and current proof-contract identity',
                'state':'pass' if endpoint_ok else 'fail',
                'method':'exact claim/theorem/contract-id/contract-sha comparison against the current canonical proof contract',
            },
            {
                'id':'common-error-vector-representation',
                'theorem_interface':'eGrad eFlux : E',
                'state':'pass',
                'method':'matching non-empty one-dimensional finite binary64 coordinate vectors checked during module validation',
                'dimension':int(e_grad.size),
            },
        ]
        unresolved=[item['id'] for item in explicit_hypotheses if item['state']=='unresolved']
        packet={
            'schema':HYPOTHESIS_PACKET_SCHEMA,
            'claim_id':RIEZ_CLAIM_ID,
            'theorem_name':PRAGER_SYNG_THEOREM,
            'proof_contract_id':contract.contract_id if contract else None,
            'proof_contract_sha256':contract.contract_sha256 if contract else None,
            'theorem_explicit_hypotheses':explicit_hypotheses,
            'runtime_representation_obligations':runtime_obligations,
            'runtime_diagnostics':{
                'inner_product_interval':inner.to_list(),
                'hypercircle_gap_interval':gap.to_list(),
                'zero_gap_numerically_consistent':zero_consistent,
                'interpretation':'The gap diagnostic equals 2*inner(eGrad,eFlux) in the concrete coordinate model. It does not discharge hcross or any abstract Green-pairing premise.',
            },
            'unresolved_hypotheses':unresolved,
            'runtime_ready':bool(endpoint_ok and not unresolved and all(item['state']=='pass' for item in runtime_obligations)),
            'formal_instantiation':False,
            'formal_provenance_source':'upstream verification record for formal330.qualified_theorem_endpoint',
            'scope_note':'This packet inventories theorem premises and concrete diagnostics only. Unresolved abstract bridges block theorem application even when the numerical hypercircle gap contains zero.',
        }
        packet['packet_sha256']=_canonical_sha256(packet)
        return packet

    def execute(self,inputs,params,ctx):
        return {'hypothesis_packet':self._packet(inputs)}

    def verify(self,inputs,params,outputs,ctx):
        expected=self._packet(inputs)
        actual=outputs.get('hypothesis_packet')
        consistent=isinstance(actual,dict) and actual == expected
        endpoint_ok=expected['runtime_representation_obligations'][0]['state']=='pass'
        unresolved_exactly={
            'bounded-green-pairing',
            'green-smooth-core',
            'zero-boundary-trace',
            'weak-green-cross-term-identity',
        } == set(expected['unresolved_hypotheses'])
        inventory_ok=bool(
            consistent
            and endpoint_ok
            and unresolved_exactly
            and expected['runtime_ready'] is False
            and expected['formal_instantiation'] is False
        )
        diagnostic=expected['runtime_diagnostics']
        diagnostic_ok=bool(
            isinstance(diagnostic.get('inner_product_interval'),list)
            and len(diagnostic['inner_product_interval']) == 2
            and isinstance(diagnostic.get('hypercircle_gap_interval'),list)
            and len(diagnostic['hypercircle_gap_interval']) == 2
        )
        return [
            VerificationRecord(
                'prager-synge-hypothesis-inventory',
                EvidenceKind.SYMBOLIC,
                'the exact explicit premises of continuumPragerSynge_of_weakGreen are inventoried and unresolved bridge obligations prevent runtime theorem readiness',
                VerificationState.PASS if inventory_ok else VerificationState.FAIL,
                'canonical endpoint matching plus fail-closed theorem-premise inventory',
                {
                    'theorem_name':PRAGER_SYNG_THEOREM,
                    'runtime_ready':expected['runtime_ready'],
                    'unresolved_hypotheses':expected['unresolved_hypotheses'],
                    'packet_sha256':expected['packet_sha256'],
                    'formal_instantiation':False,
                    'output_consistent':consistent,
                },
                notes=(
                    'A PASS here certifies the correctness of the obligation inventory, not satisfaction of the unresolved Lean hypotheses.',
                    'No user-supplied boolean or numerical orthogonality test can promote these unresolved premises.',
                ),
            ),
            VerificationRecord(
                'prager-synge-hypercircle-diagnostic',
                EvidenceKind.INTERVAL,
                'the concrete coordinate-model inner product and hypercircle gap are enclosed by outward-rounded binary64 intervals',
                VerificationState.PASS if diagnostic_ok else VerificationState.FAIL,
                'outward-rounded products and interval summation; gap computed as 2*inner(eGrad,eFlux)',
                {
                    'inner_product_interval':diagnostic['inner_product_interval'],
                    'hypercircle_gap_interval':diagnostic['hypercircle_gap_interval'],
                    'zero_gap_numerically_consistent':diagnostic['zero_gap_numerically_consistent'],
                    'formal_instantiation':False,
                },
                notes=(
                    'This diagnostic does not discharge the exact weak-Green cross-term identity hcross.',
                ),
            ),
        ]


class TheoremObligationExport(Module):
    metadata=ModuleMetadata('fem_cont.theorem_export','Lean Theorem Obligation Export','0.5.0','Formal Verification',
        'Export the scoped continuum theorem statement and proof obligations as a Lean-oriented artifact. Export is structural; Lean checking is not claimed.',Maturity.PROTOTYPE)
    inputs=(PortSpec('continuum_certificate','continuum_error_certificate'),)
    outputs=(PortSpec('theorem_artifact','formal_theorem_artifact'),)
    proof_status=ProofStatus(evidence={EvidenceKind.SYMBOLIC},unit_tests=True,documentation=True,
        limitations=['generated Lean text is a theorem obligation/skeleton, not a completed machine-checked proof'])
    def execute(self,inputs,params,ctx):
        c=inputs['continuum_certificate']; tid=c.get('theorem_id','unknown')
        lean='''-- CACE v0.5 theorem obligation (not yet machine checked)\nimport Mathlib\n\n/-- Scoped target: P1 FEM for -u''=1 on [0,1]. -/\ntheorem cace_poisson1d_p1_energy_error\n    (h : List ℝ)\n    (hpos : ∀ x ∈ h, 0 < x)\n    (hsum : h.sum = 1) :\n    True := by\n  -- TODO: formalize mesh, Galerkin solution, interpolation identity,\n  -- and prove ‖u-u_h‖_E^2 = Σ h_K^3/12.\n  trivial\n'''
        return {'theorem_artifact':{'theorem_id':tid,'language':'Lean4','status':'obligation-only','machine_checked':False,
            'assumptions':['P1 conforming partition of [0,1]','-u\'\'=1','homogeneous Dirichlet endpoints'],
            'target_identity':'||u-u_h||_E^2 = sum_K h_K^3/12','lean_source':lean}}
    def verify(self,inputs,params,outputs,ctx):
        a=outputs['theorem_artifact']; structural=(a.get('theorem_id')==THEOREM_ID and 'theorem cace_poisson1d_p1_energy_error' in a.get('lean_source',''))
        return [VerificationRecord('lean-obligation-export-structure',EvidenceKind.SYMBOLIC,
            'Lean-oriented theorem obligation contains the expected theorem id and target skeleton',VerificationState.PASS if structural else VerificationState.FAIL,
            'structural artifact validation',{'machine_checked':False,'status':a.get('status') }),
                VerificationRecord('lean-machine-check',EvidenceKind.FORMAL,
            'the exported theorem obligation has been accepted by Lean',VerificationState.NOT_RUN,
            'Lean is not invoked and the proof body is intentionally incomplete in v0.5',{'theorem_id':a.get('theorem_id')})]


def register_fem_continuum(registry):
    for cls in (MeshShapeCertificate,Poisson1DContinuumCertificate,TotalContinuumErrorCertificate,H1RieszSymbolHypothesisAdapter,PragerSyngeHypothesisInventoryAdapter,TheoremObligationExport):
        registry.register(cls)