from __future__ import annotations
from fractions import Fraction
from typing import Any
import hashlib, json

KERNEL_NAME = 'cace-exact-affine-kernel'
KERNEL_VERSION = '0.13.0'
SCHEMA = 'cace-formal-affine-proof-v1'


def _sha(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def _q(x: Any) -> Fraction:
    if isinstance(x, int): return Fraction(x)
    if not isinstance(x, str): raise ValueError('rational coefficient must be an integer or string')
    return Fraction(x)


def canonical_artifact(dimension: int) -> dict[str, Any]:
    d = int(dimension)
    if d < 1 or d > 3: raise ValueError('v0.13 formal kernel supports reference simplex dimensions 1..3')
    basis = [{'name':'lambda0','coeffs':['1'] + ['-1']*d}]
    for i in range(d):
        coeff = ['0']*(d+1); coeff[i+1] = '1'
        basis.append({'name':f'lambda{i+1}','coeffs':coeff})
    return {
        'schema': SCHEMA,
        'theorem_id': f'reference-simplex-p1-barycentric-d{d}-v013',
        'statement': 'On the canonical reference d-simplex, the supplied affine P1 barycentric basis sums exactly to 1 and satisfies lambda_i(v_j)=delta_ij.',
        'dimension': d,
        'basis': basis,
        'claims': ['partition-of-unity','kronecker-nodal-identity'],
        'scope': 'canonical reference simplex only',
    }


def check_artifact(artifact: dict[str, Any]) -> dict[str, Any]:
    """Tiny exact-arithmetic proof kernel for affine reference-simplex identities.

    The kernel trusts only Python integer/Fraction arithmetic and the small rules below.
    It does not trust SymPy, numerical evaluation, or metadata claiming success.
    """
    result = {
        'checker': KERNEL_NAME, 'checker_version': KERNEL_VERSION,
        'artifact_sha256': _sha(artifact), 'passed': False, 'claims_checked': [], 'errors': []
    }
    try:
        if artifact.get('schema') != SCHEMA: raise ValueError('unsupported proof schema')
        d = int(artifact['dimension'])
        if d < 1 or d > 3: raise ValueError('unsupported dimension')
        basis = artifact['basis']
        if len(basis) != d+1: raise ValueError('basis must contain d+1 affine functions')
        coeffs=[]
        for row in basis:
            c=[_q(x) for x in row['coeffs']]
            if len(c) != d+1: raise ValueError('each affine coefficient vector must have length d+1')
            coeffs.append(c)

        # Claim 1: exact polynomial identity sum_i lambda_i == 1.
        summed=[sum((coeffs[i][j] for i in range(d+1)), Fraction(0)) for j in range(d+1)]
        if summed != [Fraction(1)] + [Fraction(0)]*d:
            raise ValueError('partition-of-unity identity failed exact normalization')
        result['claims_checked'].append('partition-of-unity')

        # Canonical simplex vertices: v0=0, vj=e_j. Exact affine evaluation.
        verts=[[Fraction(0)]*d]
        for j in range(d):
            v=[Fraction(0)]*d; v[j]=Fraction(1); verts.append(v)
        table=[]
        for i,c in enumerate(coeffs):
            row=[]
            for j,v in enumerate(verts):
                val=c[0] + sum((c[k+1]*v[k] for k in range(d)), Fraction(0))
                row.append(val)
                if val != Fraction(1 if i==j else 0):
                    raise ValueError(f'Kronecker identity failed at lambda_{i}(v_{j})')
            table.append([str(x) for x in row])
        result['claims_checked'].append('kronecker-nodal-identity')

        # Require the artifact to request exactly the claims this kernel checked.
        if sorted(artifact.get('claims', [])) != sorted(result['claims_checked']):
            raise ValueError('artifact claim set does not exactly match checked claim set')
        result.update({'passed':True,'theorem_id':artifact.get('theorem_id'),'dimension':d,'nodal_table':table,
                       'proof_method':'exact rational affine normalization and exact nodal evaluation'})
    except Exception as exc:
        result['errors'].append(str(exc))
    return result
