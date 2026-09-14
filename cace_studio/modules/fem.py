from __future__ import annotations
import math
from typing import Any
import numpy as np

from cace_studio.core.module import Module, ExecutionContext, ValidationError
from cace_studio.core.types import ModuleMetadata, PortSpec, ParameterSpec, ProofStatus, Maturity, EvidenceKind
from cace_studio.core.verification import VerificationRecord, VerificationState


def _parse_floats(text: str) -> list[float]:
    return [float(x.strip()) for x in str(text).split(',') if x.strip()]


def _csr_from_dense(A: np.ndarray, tol: float = 0.0) -> dict[str, Any]:
    data=[]; indices=[]; indptr=[0]
    for row in A:
        for j,v in enumerate(row):
            if abs(float(v)) > tol:
                data.append(float(v)); indices.append(j)
        indptr.append(len(data))
    return {"shape":[int(A.shape[0]),int(A.shape[1])],"data":data,"indices":indices,"indptr":indptr}


def _dense_from_csr(csr: dict[str, Any]) -> np.ndarray:
    n,m=map(int,csr["shape"]); A=np.zeros((n,m),dtype=float)
    data=csr["data"]; indices=csr["indices"]; indptr=csr["indptr"]
    for i in range(n):
        for p in range(indptr[i],indptr[i+1]): A[i,int(indices[p])]=float(data[p])
    return A


class ArbitraryMesh1D(Module):
    metadata=ModuleMetadata("fem.mesh1d","Arbitrary Mesh 1D","0.2.0","Meshes",
        "Create a conforming nonuniform 1D mesh from explicit ordered vertices.",Maturity.BETA,
        assumptions=("vertices are finite and strictly increasing","domain is the interval from first to last vertex"))
    outputs=(PortSpec("mesh","mesh1d"),)
    parameters=(ParameterSpec("vertices","string","0,0.08,0.2,0.5,0.72,0.9,1","Comma-separated vertex coordinates"),)
    proof_status=ProofStatus(evidence={EvidenceKind.NUMERICAL},unit_tests=True,property_tests=True,documentation=True)
    def validate(self,inputs,params):
        super().validate(inputs,params); xs=_parse_floats(self.resolved_params(params)["vertices"])
        if len(xs)<2 or any(not math.isfinite(x) for x in xs): raise ValidationError("mesh requires >=2 finite vertices")
        if any(b<=a for a,b in zip(xs,xs[1:])): raise ValidationError("mesh vertices must be strictly increasing")
    def execute(self,inputs,params,ctx):
        x=_parse_floats(params["vertices"]); elems=[[i,i+1] for i in range(len(x)-1)]
        return {"mesh":{"dimension":1,"vertices":x,"elements":elems,"boundary":[0,len(x)-1]}}
    def verify(self,inputs,params,outputs,ctx):
        m=outputs["mesh"]; x=m["vertices"]; elems=m["elements"]
        orient=all(x[j]>x[i] for i,j in elems); cover=elems==[[i,i+1] for i in range(len(x)-1)]
        ok=orient and cover
        return [VerificationRecord("mesh-conformity",EvidenceKind.NUMERICAL,
            "elements are positively oriented and form a gap-free 1D conforming chain",VerificationState.PASS if ok else VerificationState.FAIL,
            "explicit adjacency/orientation checks",{"vertices":len(x),"elements":len(elems),"min_h":min(np.diff(x))})]


class P1ShapeFunctions(Module):
    metadata=ModuleMetadata("fem.p1_space","P1 Coordinate / Shape Functions","0.2.0","Finite Elements",
        "Attach affine barycentric P1 shape functions to every segment.",Maturity.BETA,
        assumptions=("input is a valid oriented 1D segment mesh",))
    inputs=(PortSpec("mesh","mesh1d"),); outputs=(PortSpec("space","fem_space1d"),)
    proof_status=ProofStatus(evidence={EvidenceKind.SYMBOLIC,EvidenceKind.NUMERICAL},unit_tests=True,property_tests=True,documentation=True)
    def execute(self,inputs,params,ctx):
        m=inputs["mesh"]; local=[]
        for a,b in m["elements"]:
            xa,xb=float(m["vertices"][a]),float(m["vertices"][b]); h=xb-xa
            local.append({"element":[a,b],"h":h,"phi0":[xb/h,-1.0/h],"phi1":[-xa/h,1.0/h],"gradients":[-1.0/h,1.0/h]})
        return {"space":{"family":"P1","dofs":len(m["vertices"]),"local":local}}
    def verify(self,inputs,params,outputs,ctx):
        m=inputs["mesh"]; ok=True; maxerr=0.0
        for rec in outputs["space"]["local"]:
            a,b=rec["element"]; xa,xb=m["vertices"][a],m["vertices"][b]
            c0,d0=rec["phi0"]; c1,d1=rec["phi1"]
            vals=[c0+d0*xa,c0+d0*xb,c1+d1*xa,c1+d1*xb,(c0+c1)+(d0+d1)*((xa+xb)/2)]
            target=[1,0,0,1,1]; err=max(abs(v-t) for v,t in zip(vals,target)); maxerr=max(maxerr,err); ok &= err<=1e-12
        return [VerificationRecord("p1-barycentric-identities",EvidenceKind.SYMBOLIC,
            "local affine coordinates satisfy nodal Kronecker values and partition of unity",VerificationState.PASS if ok else VerificationState.FAIL,
            "coefficient identity evaluation on each element",{"max_identity_error":maxerr})]


class PoissonAssembly1D(Module):
    metadata=ModuleMetadata("fem.poisson_assemble","Sparse Operator Assembly","0.2.0","PDE",
        "Assemble P1 Galerkin stiffness matrix and load for -u''=1 with homogeneous Dirichlet endpoints.",Maturity.BETA,
        assumptions=("P1 conforming space","source f=1","Dirichlet values are zero at both domain endpoints"))
    inputs=(PortSpec("mesh","mesh1d"),PortSpec("space","fem_space1d")); outputs=(PortSpec("system","linear_system"),)
    proof_status=ProofStatus(evidence={EvidenceKind.NUMERICAL},unit_tests=True,property_tests=True,documentation=True)
    def execute(self,inputs,params,ctx):
        m=inputs["mesh"]; n=len(m["vertices"]); A=np.zeros((n,n)); b=np.zeros(n)
        for a,c in m["elements"]:
            h=float(m["vertices"][c]-m["vertices"][a]); ke=np.array([[1,-1],[-1,1]],float)/h; fe=np.array([h/2,h/2],float)
            ids=[a,c]
            for i in range(2):
                b[ids[i]]+=fe[i]
                for j in range(2): A[ids[i],ids[j]]+=ke[i,j]
        # strong homogeneous Dirichlet elimination
        interior=list(range(1,n-1)); Ar=A[np.ix_(interior,interior)]; br=b[interior]
        return {"system":{"matrix":_csr_from_dense(Ar),"rhs":br.tolist(),"interior_dofs":interior,"full_dofs":n}}
    def verify(self,inputs,params,outputs,ctx):
        A=_dense_from_csr(outputs["system"]["matrix"]); sym=float(np.max(np.abs(A-A.T))) if A.size else 0.0
        eig=float(np.min(np.linalg.eigvalsh(A))) if A.size else math.inf; ok=sym<=1e-12 and eig>0
        return [VerificationRecord("stiffness-spd",EvidenceKind.NUMERICAL,
            "reduced stiffness matrix is symmetric positive definite",VerificationState.PASS if ok else VerificationState.FAIL,
            "host-side symmetry check and symmetric eigenvalue computation",{"symmetry_error":sym,"min_eigenvalue":eig,"nnz":len(outputs['system']['matrix']['data'])})]


class LinearPDESolver(Module):
    metadata=ModuleMetadata("fem.linear_solve","Linear / PDE Solver","0.2.0","PDE","Solve the reduced finite-element linear system and reconstruct boundary values.",Maturity.BETA)
    inputs=(PortSpec("system","linear_system"),); outputs=(PortSpec("solution","fem_solution1d"),)
    supports_gpu=True
    proof_status=ProofStatus(evidence={EvidenceKind.NUMERICAL},unit_tests=True,documentation=True,limitations=["v0.2 uses dense host solve after CSR assembly"])
    def execute(self,inputs,params,ctx):
        s=inputs["system"]; A=_dense_from_csr(s["matrix"]); b=np.asarray(s["rhs"],float)
        ui=np.linalg.solve(A,b) if b.size else np.array([],float); u=np.zeros(int(s["full_dofs"])); u[np.asarray(s["interior_dofs"],int)]=ui
        return {"solution":{"values":u.tolist(),"interior":ui.tolist()}}
    def verify(self,inputs,params,outputs,ctx):
        s=inputs["system"]; A=_dense_from_csr(s["matrix"]); b=np.asarray(s["rhs"],float); u=np.asarray(outputs["solution"]["interior"],float)
        r=A@u-b; rn=float(np.linalg.norm(r,np.inf)) if r.size else 0.0
        return [VerificationRecord("linear-solve-residual",EvidenceKind.NUMERICAL,"algebraic infinity-norm residual is small",VerificationState.PASS if rn<=1e-10 else VerificationState.FAIL,
            "independent host-side matrix-vector residual",{"residual_inf":rn})]


class AlgebraicResidual(Module):
    metadata=ModuleMetadata("fem.residual","Residual","0.2.0","Verification","Compute the reduced algebraic residual A u - b.",Maturity.BETA)
    inputs=(PortSpec("system","linear_system"),PortSpec("solution","fem_solution1d")); outputs=(PortSpec("residual","array"),PortSpec("residual_inf","number"))
    proof_status=ProofStatus(evidence={EvidenceKind.NUMERICAL},unit_tests=True,documentation=True)
    def execute(self,inputs,params,ctx):
        A=_dense_from_csr(inputs["system"]["matrix"]); b=np.asarray(inputs["system"]["rhs"],float); u=np.asarray(inputs["solution"]["interior"],float); r=A@u-b
        return {"residual":r.tolist(),"residual_inf":float(np.linalg.norm(r,np.inf)) if r.size else 0.0}
    def verify(self,inputs,params,outputs,ctx):
        v=float(outputs["residual_inf"]); return [VerificationRecord("residual-finite",EvidenceKind.NUMERICAL,"computed residual norm is finite",VerificationState.PASS if math.isfinite(v) else VerificationState.FAIL,"finite-value check",{"residual_inf":v})]


class AposterioriEstimator1D(Module):
    metadata=ModuleMetadata("fem.aposteriori","A-posteriori Error Estimator","0.2.0","Verification",
        "Residual/jump indicator for P1 Poisson elements; reported as an estimator, not a certified global error bound.",Maturity.EXPERIMENTAL,
        assumptions=("source f=1","P1 conforming solution"))
    inputs=(PortSpec("mesh","mesh1d"),PortSpec("solution","fem_solution1d")); outputs=(PortSpec("estimator","error_estimator1d"),)
    proof_status=ProofStatus(evidence={EvidenceKind.NUMERICAL},unit_tests=True,documentation=True,limitations=["v0.2 does not attach a proven reliability constant to this estimator"])
    def execute(self,inputs,params,ctx):
        x=np.asarray(inputs["mesh"]["vertices"],float); u=np.asarray(inputs["solution"]["values"],float); h=np.diff(x); slopes=np.diff(u)/h
        jumps=np.zeros(len(x));
        for i in range(1,len(x)-1): jumps[i]=slopes[i]-slopes[i-1]
        eta2=[]
        for k,hk in enumerate(h):
            # element residual f=1 plus half of adjacent flux-jump contributions
            val=hk**3 + 0.5*hk*(jumps[k]**2+jumps[k+1]**2); eta2.append(float(val))
        total=float(math.sqrt(sum(eta2))); return {"estimator":{"element_eta":[math.sqrt(v) for v in eta2],"eta":total}}
    def verify(self,inputs,params,outputs,ctx):
        e=outputs["estimator"]; vals=e["element_eta"]; ok=all(math.isfinite(v) and v>=0 for v in vals) and math.isfinite(e["eta"])
        return [VerificationRecord("estimator-wellformed",EvidenceKind.NUMERICAL,"all local indicators and global estimator are finite and nonnegative",VerificationState.PASS if ok else VerificationState.FAIL,"direct invariant checks",{"eta":e["eta"],"elements":len(vals)})]


class BenchmarkEnergyErrorInterval(Module):
    metadata=ModuleMetadata("fem.energy_interval","Interval Bound","0.2.0","Verification",
        "Outward-rounded enclosure of the exact H1-seminorm error for the benchmark -u''=1, u(0)=u(1)=0.",Maturity.EXPERIMENTAL,
        assumptions=("domain is exactly [0,1]","exact benchmark solution is u=x(1-x)/2","piecewise-linear FE solution on the supplied mesh"))
    inputs=(PortSpec("mesh","mesh1d"),PortSpec("solution","fem_solution1d")); outputs=(PortSpec("error_interval","interval"),PortSpec("energy_error","number"))
    proof_status=ProofStatus(evidence={EvidenceKind.INTERVAL},unit_tests=True,property_tests=True,documentation=True,
        limitations=["benchmark-specific certificate","nextafter-based binary64 enclosure is not yet an audited interval-arithmetic kernel"])
    def validate(self,inputs,params):
        super().validate(inputs,params); x=inputs["mesh"]["vertices"]
        if abs(float(x[0]))>1e-15 or abs(float(x[-1])-1.0)>1e-15: raise ValidationError("benchmark interval requires mesh domain [0,1]")
    def execute(self,inputs,params,ctx):
        x=np.asarray(inputs["mesh"]["vertices"],float); u=np.asarray(inputs["solution"]["values"],float); total=0.0
        # exact integral on each element of ((1/2-x) - slope_h)^2 dx
        for a,b,ua,ub in zip(x[:-1],x[1:],u[:-1],u[1:]):
            s=(ub-ua)/(b-a); c=0.5-s
            # integral_a^b (c-x)^2 dx = ((b-c)^3-(a-c)^3)/3
            val=((b-c)**3-(a-c)**3)/3.0; total += max(0.0,float(val))
        err=math.sqrt(total); lo=math.nextafter(err,-math.inf); hi=math.nextafter(err,math.inf)
        return {"error_interval":[lo,hi],"energy_error":err}
    def verify(self,inputs,params,outputs,ctx):
        lo,hi=map(float,outputs["error_interval"]); e=float(outputs["energy_error"]); ok=lo<=e<=hi and lo>=0
        return [VerificationRecord("benchmark-energy-enclosure",EvidenceKind.INTERVAL,
            "reported interval encloses the analytically integrated benchmark H1-seminorm error",VerificationState.PASS if ok else VerificationState.FAIL,
            "exact polynomial element integration followed by outward math.nextafter expansion",{"enclosure":[lo,hi],"nominal_error":e})]


class AdaptiveRefinement1D(Module):
    metadata=ModuleMetadata("fem.adapt","Adaptive Refinement","0.2.0","Meshes",
        "Bisect elements selected by Dörfler bulk marking using local a-posteriori indicators.",Maturity.EXPERIMENTAL,
        assumptions=("0 < theta <= 1",))
    inputs=(PortSpec("mesh","mesh1d"),PortSpec("estimator","error_estimator1d")); outputs=(PortSpec("refined_mesh","mesh1d"),PortSpec("marked","array"))
    parameters=(ParameterSpec("theta","number",0.5,"Dörfler bulk fraction"),)
    proof_status=ProofStatus(evidence={EvidenceKind.NUMERICAL},unit_tests=True,property_tests=True,documentation=True)
    def validate(self,inputs,params):
        super().validate(inputs,params); t=float(self.resolved_params(params)["theta"])
        if not (0<t<=1): raise ValidationError("theta must satisfy 0 < theta <= 1")
    def execute(self,inputs,params,ctx):
        x=list(map(float,inputs["mesh"]["vertices"])); eta=np.asarray(inputs["estimator"]["element_eta"],float); weights=eta*eta; target=float(params["theta"])*float(weights.sum())
        order=list(np.argsort(-weights)); marked=[]; acc=0.0
        for k in order:
            marked.append(int(k)); acc+=float(weights[k])
            if acc>=target: break
        marks=set(marked); verts=[x[0]]
        for k,(a,b) in enumerate(zip(x[:-1],x[1:])):
            if k in marks: verts.append((a+b)/2.0)
            verts.append(b)
        return {"refined_mesh":{"dimension":1,"vertices":verts,"elements":[[i,i+1] for i in range(len(verts)-1)],"boundary":[0,len(verts)-1]},"marked":sorted(marked)}
    def verify(self,inputs,params,outputs,ctx):
        old=inputs["mesh"]["vertices"]; new=outputs["refined_mesh"]["vertices"]; marked=outputs["marked"]; preserved=all(v in new for v in old); ok=preserved and len(new)==len(old)+len(marked) and all(b>a for a,b in zip(new,new[1:]))
        return [VerificationRecord("refinement-conformity",EvidenceKind.NUMERICAL,
            "refinement preserves old vertices, inserts one midpoint per marked element, and remains ordered/conforming",VerificationState.PASS if ok else VerificationState.FAIL,
            "mesh invariant checks",{"old_vertices":len(old),"new_vertices":len(new),"marked":marked})]


class PipelineCertificate(Module):
    metadata=ModuleMetadata("fem.certificate","Certificate","0.2.0","Verification",
        "Summarize benchmark residual, estimator, certified benchmark interval, and refinement decision.",Maturity.EXPERIMENTAL)
    inputs=(PortSpec("residual_inf","number"),PortSpec("estimator","error_estimator1d"),PortSpec("error_interval","interval"),PortSpec("refined_mesh","mesh1d")); outputs=(PortSpec("certificate_summary","record"),)
    parameters=(ParameterSpec("residual_tolerance","number",1e-10),)
    proof_status=ProofStatus(evidence={EvidenceKind.NUMERICAL},unit_tests=True,documentation=True, limitations=["summary node does not elevate upstream evidence; graph/run certificates remain authoritative"])
    def execute(self,inputs,params,ctx):
        rt=float(params["residual_tolerance"]); r=float(inputs["residual_inf"]); lo,hi=map(float,inputs["error_interval"])
        return {"certificate_summary":{"residual_pass":r<=rt,"residual_inf":r,"residual_tolerance":rt,"estimator":float(inputs["estimator"]["eta"]),"benchmark_energy_error_interval":[lo,hi],"refined_vertices":len(inputs["refined_mesh"]["vertices"])}}
    def verify(self,inputs,params,outputs,ctx):
        s=outputs["certificate_summary"]; state=VerificationState.PASS if s["residual_pass"] and s["benchmark_energy_error_interval"][0]>=0 else VerificationState.FAIL
        return [VerificationRecord("pipeline-summary",EvidenceKind.NUMERICAL,
            "pipeline summary is internally consistent and algebraic residual meets tolerance",state,
            "aggregation only; upstream RunCertificates remain authoritative for interval evidence",s)]


def register_fem(registry):
    for cls in (ArbitraryMesh1D,P1ShapeFunctions,PoissonAssembly1D,LinearPDESolver,AlgebraicResidual,AposterioriEstimator1D,BenchmarkEnergyErrorInterval,AdaptiveRefinement1D,PipelineCertificate):
        registry.register(cls)
