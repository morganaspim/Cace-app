from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
import uuid
from .graph import Experiment
from .module import ExecutionContext, ValidationError
from .registry import ModuleRegistry
from .certificate import RunCertificate
from .verification import VerificationRecord, VerificationState
from .device import DeviceManager
from .claim_promotion import fail_closed_module_decision

@dataclass
class RunResult:
    run_id: str
    outputs: dict[str, dict[str, Any]]
    certificates: list[RunCertificate]
    verification: dict[str, list[VerificationRecord]]
    claim_decisions: dict[str, dict[str, Any]] = field(default_factory=dict)

    @property
    def all_verifiers_passed(self) -> bool:
        records = [r for rs in self.verification.values() for r in rs]
        return all(r.state is not VerificationState.FAIL for r in records)

    @property
    def any_public_resolution_claim_allowed(self) -> bool:
        return any(bool(d.get("public_resolution_claim_allowed", False)) for d in self.claim_decisions.values())

class GraphExecutor:
    def __init__(self, registry: ModuleRegistry, *, gpu_enabled: bool = False) -> None:
        self.registry = registry
        self.gpu_enabled = gpu_enabled

    def _validate_and_order(self, exp: Experiment) -> list[str]:
        nodes = exp.node_map()
        if len(nodes) != len(exp.nodes): raise ValidationError("node ids must be unique")
        for n in exp.nodes:
            if not self.registry.contains(n.module_id): raise ValidationError(f"unknown module on node {n.id}: {n.module_id}")
        incoming = {n.id: 0 for n in exp.nodes}; outgoing = {n.id: [] for n in exp.nodes}; occupied=set()
        for e in exp.edges:
            if e.source_node not in nodes or e.target_node not in nodes: raise ValidationError("edge references missing node")
            if (e.target_node,e.target_port) in occupied: raise ValidationError(f"input already connected: {e.target_node}.{e.target_port}")
            occupied.add((e.target_node,e.target_port))
            src=self.registry.create(nodes[e.source_node].module_id); dst=self.registry.create(nodes[e.target_node].module_id)
            sp={p.name:p for p in src.outputs}; dp={p.name:p for p in dst.inputs}
            if e.source_port not in sp or e.target_port not in dp: raise ValidationError("edge references missing port")
            st,dt=sp[e.source_port].type_name,dp[e.target_port].type_name
            if st!="any" and dt!="any" and st!=dt: raise ValidationError(f"type mismatch: {st} -> {dt}")
            outgoing[e.source_node].append(e.target_node); incoming[e.target_node]+=1
        ready=sorted(k for k,v in incoming.items() if v==0); order=[]
        while ready:
            cur=ready.pop(0); order.append(cur)
            for nxt in sorted(outgoing[cur]):
                incoming[nxt]-=1
                if incoming[nxt]==0: ready.append(nxt); ready.sort()
        if len(order)!=len(nodes): raise ValidationError("experiment graph contains a cycle")
        return order

    def run(self, exp: Experiment, external_inputs: dict[str, dict[str, Any]] | None=None, seed: int=0) -> RunResult:
        order=self._validate_and_order(exp); nodes=exp.node_map(); external_inputs=external_inputs or {}
        run_id=str(uuid.uuid4()); outputs={}; certs=[]; verification={}; claim_decisions={}
        for node_id in order:
            node=nodes[node_id]; module=self.registry.create(node.module_id); ins=dict(external_inputs.get(node_id,{}))
            for e in exp.edges:
                if e.target_node==node_id: ins[e.target_port]=outputs[e.source_node][e.source_port]
            params=module.resolved_params(node.params); module.validate(ins,node.params)
            device=DeviceManager.select(self.gpu_enabled,module.supports_gpu); ctx=ExecutionContext(run_id=run_id,seed=seed,device=device)
            out=dict(module.execute(ins,params,ctx)); expected={p.name for p in module.outputs}; unknown=set(out)-expected
            if unknown: raise ValidationError(f"{node_id}: undeclared outputs {sorted(unknown)}")
            out={k:DeviceManager.to_host(v) for k,v in out.items()}; outputs[node_id]=out
            decision=fail_closed_module_decision(module.metadata.category,module.proof_status,out)
            if decision is not None:
                claim_decisions[node_id]=decision.to_dict()
            records=list(module.verify(ins,params,out,ctx)); verification[node_id]=records
            if any(r.state is VerificationState.FAIL for r in records):
                # Failure is evidence, not a crash: preserve outputs/certificate for investigation.
                pass
            certs.append(RunCertificate.build(run_id=run_id,node_id=node_id,module_id=module.metadata.module_id,
                module_version=module.metadata.version,inputs=ins,params=params,outputs=out,verification=records,device=device))
        return RunResult(run_id,outputs,certs,verification,claim_decisions)
