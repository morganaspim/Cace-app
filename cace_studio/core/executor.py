from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Iterable
import uuid
from .graph import Experiment
from .module import ExecutionContext, ValidationError
from .registry import ModuleRegistry
from .certificate import RunCertificate
from .verification import VerificationRecord, VerificationState
from .device import DeviceManager
from .claim_promotion import fail_closed_module_decision, unsafe_self_promotion_paths
from .formal_gate import enforce_formal_claim_qualification
from .reproducibility import experiment_fingerprint
from .execution_scope import ExecutionScope, build_upstream_subgraph, full_execution_scope
from .execution_control import ExecutionControl


@dataclass
class RunResult:
    run_id: str
    outputs: dict[str, dict[str, Any]]
    certificates: list[RunCertificate]
    verification: dict[str, list[VerificationRecord]]
    claim_decisions: dict[str, dict[str, Any]] = field(default_factory=dict)
    experiment_name: str = ""
    semantic_experiment_sha256: str = ""
    full_experiment_sha256: str = ""
    source_semantic_experiment_sha256: str = ""
    source_full_experiment_sha256: str = ""
    execution_scope_sha256: str = ""
    scope_target_node_ids: tuple[str, ...] = ()
    scope_included_node_ids: tuple[str, ...] = ()
    seed: int = 0
    run_scope: str = "full"
    completed: bool = True
    interruption_reason: str = ""

    @property
    def all_verifiers_passed(self) -> bool:
        if not self.completed:
            return False
        records = [r for rs in self.verification.values() for r in rs]
        return bool(records) and all(r.state is VerificationState.PASS for r in records)

    @property
    def any_public_resolution_claim_allowed(self) -> bool:
        return any(bool(d.get("public_resolution_claim_allowed", False)) for d in self.claim_decisions.values())


class GraphExecutor:
    def __init__(self, registry: ModuleRegistry, *, gpu_enabled: bool = False) -> None:
        self.registry = registry
        self.gpu_enabled = gpu_enabled

    def _validate_and_order(self, exp: Experiment) -> list[str]:
        nodes = exp.node_map()
        if len(nodes) != len(exp.nodes):
            raise ValidationError("node ids must be unique")
        for n in exp.nodes:
            if not self.registry.contains(n.module_id):
                raise ValidationError(f"unknown module on node {n.id}: {n.module_id}")
        incoming = {n.id: 0 for n in exp.nodes}
        outgoing = {n.id: [] for n in exp.nodes}
        occupied = set()
        for e in exp.edges:
            if e.source_node not in nodes or e.target_node not in nodes:
                raise ValidationError("edge references missing node")
            if (e.target_node, e.target_port) in occupied:
                raise ValidationError(f"input already connected: {e.target_node}.{e.target_port}")
            occupied.add((e.target_node, e.target_port))
            src = self.registry.create(nodes[e.source_node].module_id)
            dst = self.registry.create(nodes[e.target_node].module_id)
            sp = {p.name: p for p in src.outputs}
            dp = {p.name: p for p in dst.inputs}
            if e.source_port not in sp or e.target_port not in dp:
                raise ValidationError("edge references missing port")
            st, dt = sp[e.source_port].type_name, dp[e.target_port].type_name
            if st != "any" and dt != "any" and st != dt:
                raise ValidationError(f"type mismatch: {st} -> {dt}")
            outgoing[e.source_node].append(e.target_node)
            incoming[e.target_node] += 1
        ready = sorted(k for k, v in incoming.items() if v == 0)
        order = []
        while ready:
            cur = ready.pop(0)
            order.append(cur)
            for nxt in sorted(outgoing[cur]):
                incoming[nxt] -= 1
                if incoming[nxt] == 0:
                    ready.append(nxt)
                    ready.sort()
        if len(order) != len(nodes):
            raise ValidationError("experiment graph contains a cycle")
        return order

    @staticmethod
    def _validated_scope(
        exp: Experiment,
        *,
        run_scope: str,
        execution_scope: ExecutionScope | None,
    ) -> ExecutionScope:
        if not isinstance(run_scope, str) or not run_scope.strip():
            raise ValidationError("run_scope must be a non-empty string")

        if execution_scope is None:
            return full_execution_scope(exp, kind=run_scope.strip())

        if run_scope != "full" and run_scope.strip() != execution_scope.kind:
            raise ValidationError("run_scope disagrees with the supplied execution scope")

        semantic = experiment_fingerprint(exp, include_layout=False)
        full = experiment_fingerprint(exp, include_layout=True)
        if semantic != execution_scope.execution_semantic_experiment_sha256:
            raise ValidationError("execution scope semantic graph hash does not match executed graph")
        if full != execution_scope.execution_full_experiment_sha256:
            raise ValidationError("execution scope full graph hash does not match executed graph")
        included_ids = tuple(node.id for node in exp.nodes)
        if included_ids != execution_scope.included_node_ids:
            raise ValidationError("execution scope included-node identity does not match executed graph")
        return execution_scope

    def run(
        self,
        exp: Experiment,
        external_inputs: dict[str, dict[str, Any]] | None = None,
        seed: int = 0,
        *,
        run_scope: str = "full",
        execution_scope: ExecutionScope | None = None,
        control: ExecutionControl | None = None,
    ) -> RunResult:
        scope = self._validated_scope(
            exp,
            run_scope=run_scope,
            execution_scope=execution_scope,
        )

        semantic_experiment_sha256 = scope.execution_semantic_experiment_sha256
        full_experiment_sha256 = scope.execution_full_experiment_sha256

        order = self._validate_and_order(exp)
        nodes = exp.node_map()
        external_inputs = external_inputs or {}
        run_id = str(uuid.uuid4())
        outputs = {}
        certs = []
        verification = {}
        claim_decisions = {}
        completed = True
        interruption_reason = ""

        for node_id in order:
            if control is not None and not control.wait_until_runnable():
                completed = False
                interruption_reason = f"cancelled-before-node:{node_id}"
                break

            node = nodes[node_id]
            module = self.registry.create(node.module_id)
            ins = dict(external_inputs.get(node_id, {}))
            for e in exp.edges:
                if e.target_node == node_id:
                    ins[e.target_port] = outputs[e.source_node][e.source_port]
            params = module.resolved_params(node.params)
            module.validate(ins, node.params)
            device = DeviceManager.select(self.gpu_enabled, module.supports_gpu)
            ctx = ExecutionContext(run_id=run_id, seed=seed, device=device)
            out = dict(module.execute(ins, params, ctx))
            expected = {p.name for p in module.outputs}
            unknown = set(out) - expected
            if unknown:
                raise ValidationError(f"{node_id}: undeclared outputs {sorted(unknown)}")
            out = {k: DeviceManager.to_host(v) for k, v in out.items()}
            outputs[node_id] = out

            attempted = unsafe_self_promotion_paths(out)
            decision = fail_closed_module_decision(module.metadata.category, module.proof_status, out)
            if attempted:
                if decision is None:
                    raise ValidationError(
                        f"{node_id}: module attempted reserved public promotion at {list(attempted)}; "
                        "ordinary module outputs cannot authorize open-problem resolution"
                    )
                if not decision.public_resolution_claim_allowed:
                    raise ValidationError(
                        f"{node_id}: open-problem module attempted reserved public promotion at {list(attempted)}; "
                        "promotion must go through artifact-bound claim evaluation"
                    )
            if decision is not None:
                claim_decisions[node_id] = decision.to_dict()

            records = enforce_formal_claim_qualification(
                module.metadata.module_id,
                list(module.verify(ins, params, out, ctx)),
            )
            verification[node_id] = records
            certs.append(
                RunCertificate.build(
                    run_id=run_id,
                    node_id=node_id,
                    module_id=module.metadata.module_id,
                    module_version=module.metadata.version,
                    inputs=ins,
                    params=params,
                    outputs=out,
                    verification=records,
                    device=device,
                )
            )

            if control is not None and control.cancelled:
                completed = False
                interruption_reason = f"cancelled-after-node:{node_id}"
                break

        return RunResult(
            run_id=run_id,
            outputs=outputs,
            certificates=certs,
            verification=verification,
            claim_decisions=claim_decisions,
            experiment_name=exp.name,
            semantic_experiment_sha256=semantic_experiment_sha256,
            full_experiment_sha256=full_experiment_sha256,
            source_semantic_experiment_sha256=scope.source_semantic_experiment_sha256,
            source_full_experiment_sha256=scope.source_full_experiment_sha256,
            execution_scope_sha256=scope.scope_sha256,
            scope_target_node_ids=scope.target_node_ids,
            scope_included_node_ids=scope.included_node_ids,
            seed=seed,
            run_scope=scope.kind,
            completed=completed,
            interruption_reason=interruption_reason,
        )

    def run_selected_upstream(
        self,
        source_exp: Experiment,
        target_node_ids: Iterable[str],
        external_inputs: dict[str, dict[str, Any]] | None = None,
        seed: int = 0,
        *,
        control: ExecutionControl | None = None,
    ) -> RunResult:
        scoped_exp, scope = build_upstream_subgraph(source_exp, target_node_ids)
        return self.run(
            scoped_exp,
            external_inputs=external_inputs,
            seed=seed,
            execution_scope=scope,
            control=control,
        )
