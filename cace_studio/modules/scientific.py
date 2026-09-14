from __future__ import annotations
from typing import Mapping, Any
import math
from cace_studio.core.module import Module, ExecutionContext, ValidationError
from cace_studio.core.types import ModuleMetadata, PortSpec, ParameterSpec, ProofStatus, Maturity, EvidenceKind
from cace_studio.core.verification import VerificationRecord, VerificationState
from cace_studio.core.device import DeviceManager
from cace_studio.core.interval import Interval, square as interval_square

class Grid1D(Module):
    metadata = ModuleMetadata("science.grid1d", "Grid 1D", "0.1.0", "Data", "Uniform one-dimensional grid.", Maturity.BETA,
                              assumptions=("start < stop", "points >= 3"))
    outputs = (PortSpec("x","array"),)
    parameters = (ParameterSpec("start","number",-1.0), ParameterSpec("stop","number",1.0), ParameterSpec("points","integer",101))
    supports_gpu = True
    proof_status = ProofStatus(evidence={EvidenceKind.NUMERICAL}, unit_tests=True, documentation=True)
    def validate(self, inputs, params):
        super().validate(inputs,params); p=self.resolved_params(params)
        if float(p["start"]) >= float(p["stop"]): raise ValidationError("Grid1D requires start < stop")
        if int(p["points"]) < 3: raise ValidationError("Grid1D requires points >= 3")
    def execute(self, inputs, params, ctx):
        xp=DeviceManager.array_module(ctx.device); return {"x":xp.linspace(float(params["start"]),float(params["stop"]),int(params["points"]))}
    def verify(self, inputs, params, outputs, ctx):
        x=outputs["x"]; n=int(params["points"]); ok=len(x)==n and abs(float(x[0])-float(params["start"]))<=1e-14 and abs(float(x[-1])-float(params["stop"]))<=1e-14
        return [VerificationRecord("grid-shape-endpoints",EvidenceKind.NUMERICAL,"grid has requested length and endpoints",VerificationState.PASS if ok else VerificationState.FAIL,"direct endpoint/shape checks",{"points":len(x)})]

class QuadraticField(Module):
    metadata = ModuleMetadata("science.quadratic", "Quadratic Field", "0.1.0", "Analysis", "Evaluate a*x^2 + b*x + c.", Maturity.BETA)
    inputs=(PortSpec("x","array"),); outputs=(PortSpec("y","array"),)
    parameters=(ParameterSpec("a","number",1.0),ParameterSpec("b","number",0.0),ParameterSpec("c","number",0.0))
    supports_gpu=True
    proof_status=ProofStatus(evidence={EvidenceKind.NUMERICAL},unit_tests=True,property_tests=True,documentation=True)
    def execute(self,inputs,params,ctx):
        xp=DeviceManager.array_module(ctx.device); x=xp.asarray(inputs["x"]); return {"y":float(params["a"])*x*x+float(params["b"])*x+float(params["c"])}

class CentralSecondDerivative(Module):
    metadata=ModuleMetadata("science.second_derivative", "Centered Second Derivative", "0.1.0", "PDE", "Second derivative on a uniform grid using the three-point centered stencil.", Maturity.EXPERIMENTAL,
                            assumptions=("x is uniformly spaced", "len(x) == len(y) >= 3"))
    inputs=(PortSpec("x","array"),PortSpec("y","array")); outputs=(PortSpec("x_interior","array"),PortSpec("d2y","array"))
    supports_gpu=True
    proof_status=ProofStatus(evidence={EvidenceKind.NUMERICAL},unit_tests=True,property_tests=True,documentation=True, limitations=["uniform grids only", "second-order stencil"])
    def validate(self,inputs,params):
        super().validate(inputs,params)
        if len(inputs["x"])!=len(inputs["y"]) or len(inputs["x"])<3: raise ValidationError("x and y must have equal length >= 3")
    def execute(self,inputs,params,ctx):
        xp=DeviceManager.array_module(ctx.device); x=xp.asarray(inputs["x"]); y=xp.asarray(inputs["y"]); h=x[1]-x[0]
        return {"x_interior":x[1:-1], "d2y":(y[:-2]-2*y[1:-1]+y[2:])/(h*h)}
    def verify(self,inputs,params,outputs,ctx):
        import numpy as np
        x=np.asarray(inputs["x"],dtype=float); dif=np.diff(x); tol=max(1e-12,abs(float(dif[0]))*1e-10); uniform=bool(np.all(np.abs(dif-dif[0])<=tol))
        return [VerificationRecord("uniform-grid-precondition",EvidenceKind.NUMERICAL,"input grid satisfies the module's uniform-spacing assumption",VerificationState.PASS if uniform else VerificationState.FAIL,"spacing consistency check",{"max_spacing_deviation":float(np.max(np.abs(dif-dif[0])))})]

class ConstantResidualVerifier(Module):
    metadata=ModuleMetadata("verify.constant_residual", "Constant Residual Verifier", "0.1.0", "Verification", "Verify that an array is within a tolerance of a target constant.", Maturity.BETA)
    inputs=(PortSpec("values","array"),); outputs=(PortSpec("max_abs_residual","number"),PortSpec("verified","bool"))
    parameters=(ParameterSpec("target","number",2.0),ParameterSpec("tolerance","number",1e-9))
    proof_status=ProofStatus(evidence={EvidenceKind.NUMERICAL},unit_tests=True,property_tests=True,documentation=True)
    def execute(self,inputs,params,ctx):
        import numpy as np
        v=np.asarray(inputs["values"],dtype=float); residual=float(np.max(np.abs(v-float(params["target"])))) if v.size else math.inf
        return {"max_abs_residual":residual,"verified":bool(residual<=float(params["tolerance"]))}
    def verify(self,inputs,params,outputs,ctx):
        state=VerificationState.PASS if outputs["verified"] else VerificationState.FAIL
        return [VerificationRecord("constant-residual",EvidenceKind.NUMERICAL,
            f"max |value - {float(params['target'])}| <= {float(params['tolerance'])}",state,
            "independent host-side max absolute residual",{"max_abs_residual":outputs["max_abs_residual"],"tolerance":float(params["tolerance"])})]

class IntervalLiteral(Module):
    metadata=ModuleMetadata("verify.interval_literal", "Interval", "0.1.0", "Verification", "Create a closed floating-point interval.", Maturity.BETA)
    outputs=(PortSpec("interval","interval"),); parameters=(ParameterSpec("lo","number",-1.0),ParameterSpec("hi","number",1.0))
    proof_status=ProofStatus(evidence={EvidenceKind.INTERVAL},unit_tests=True,documentation=True)
    def validate(self,inputs,params):
        super().validate(inputs,params); p=self.resolved_params(params)
        if float(p["lo"])>float(p["hi"]): raise ValidationError("interval requires lo <= hi")
    def execute(self,inputs,params,ctx): return {"interval":[float(params["lo"]),float(params["hi"])]}
    def verify(self,inputs,params,outputs,ctx):
        lo,hi=outputs["interval"]; ok=lo<=hi and not(math.isnan(lo) or math.isnan(hi))
        return [VerificationRecord("interval-wellformed",EvidenceKind.INTERVAL,"output is a well-formed closed interval",VerificationState.PASS if ok else VerificationState.FAIL,"endpoint ordering and NaN checks")]

class IntervalSquare(Module):
    metadata=ModuleMetadata("verify.interval_square", "Interval Square", "0.1.0", "Verification", "Outward-rounded enclosure of x^2 over a closed interval.", Maturity.EXPERIMENTAL,
        assumptions=("finite IEEE-754 binary64 endpoints", "Python math.nextafter has platform-conforming behavior"))
    inputs=(PortSpec("interval","interval"),); outputs=(PortSpec("squared","interval"),)
    proof_status=ProofStatus(evidence={EvidenceKind.INTERVAL},unit_tests=True,property_tests=True,documentation=True,
        limitations=["binary64 finite endpoints only", "not a substitute for a full directed-rounding interval library"])
    def validate(self,inputs,params):
        super().validate(inputs,params); lo,hi=inputs["interval"]
        if not(math.isfinite(float(lo)) and math.isfinite(float(hi))) or float(lo)>float(hi): raise ValidationError("finite ordered interval required")
    def execute(self,inputs,params,ctx):
        a=Interval(float(inputs["interval"][0]),float(inputs["interval"][1])); return {"squared":interval_square(a).to_list()}
    def verify(self,inputs,params,outputs,ctx):
        lo,hi=map(float,inputs["interval"]); slo,shi=map(float,outputs["squared"])
        candidates=[lo*lo,hi*hi]; exact_lo=0.0 if lo<=0<=hi else min(candidates); exact_hi=max(candidates)
        ok=slo<=exact_lo and shi>=exact_hi
        return [VerificationRecord("outward-square-enclosure",EvidenceKind.INTERVAL,"returned interval encloses x^2 for every x in the input interval",VerificationState.PASS if ok else VerificationState.FAIL,
            "endpoint extremum analysis plus outward nextafter expansion",{"reference_extrema":[exact_lo,exact_hi],"enclosure":[slo,shi]})]

def register_scientific(registry):
    for cls in (Grid1D,QuadraticField,CentralSecondDerivative,ConstantResidualVerifier,IntervalLiteral,IntervalSquare): registry.register(cls)
