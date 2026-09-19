from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from time import perf_counter
from typing import Any, Mapping

from cace_studio.core.certificate import stable_hash
from cace_studio.core.executor import GraphExecutor
from cace_studio.core.graph import Experiment
from cace_studio.core.verification import VerificationState

from .experiment_proposal import (
    PROPOSAL_STRATEGIES,
    ExperimentGraphProposal,
    ProposalStrategy,
    materialize_experiment_proposal,
)


@dataclass(frozen=True)
class OutputSummary:
    node_id: str
    module_id: str
    output_hash: str
    fields: tuple[str, ...]
    summary: str


@dataclass(frozen=True)
class StrategyRunSummary:
    strategy: ProposalStrategy
    runnable: bool
    run_attempted: bool
    completed: bool
    error: str
    seed: int
    runtime_seconds: float | None
    node_count: int
    edge_count: int
    unresolved_required_inputs: int
    skipped_modules: tuple[str, ...]
    completed_node_count: int
    verifier_pass: int
    verifier_fail: int
    verifier_not_run: int
    verifier_record_count: int
    all_verifiers_passed: bool
    output_summaries: tuple[OutputSummary, ...]
    novel_modules: tuple[str, ...]
    novelty_fraction: float
    semantic_experiment_sha256: str
    full_experiment_sha256: str


@dataclass(frozen=True)
class StrategyComparison:
    seed: int
    gpu_enabled: bool
    summaries: tuple[StrategyRunSummary, ...]
    common_modules: tuple[str, ...]

    def by_strategy(self) -> dict[ProposalStrategy, StrategyRunSummary]:
        return {summary.strategy: summary for summary in self.summaries}


def _finite_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and isfinite(float(value))


def _summarize_value(value: Any, *, max_text: int = 140) -> str:
    if value is None:
        return "None"
    if isinstance(value, bool):
        return f"bool={value}"
    if _finite_number(value):
        return f"{type(value).__name__}={float(value):.8g}"
    if isinstance(value, str):
        compact = value.replace("\n", " ")
        return f"str[{len(value)}]={compact[:max_text]!r}"
    if isinstance(value, Mapping):
        keys = tuple(sorted(str(key) for key in value))
        preview = ", ".join(keys[:8])
        if len(keys) > 8:
            preview += ", …"
        return f"mapping[{len(keys)}] keys={preview}"
    if isinstance(value, (list, tuple)):
        return f"{type(value).__name__}[{len(value)}]"
    try:
        import numpy as np
        if isinstance(value, np.ndarray):
            parts = [f"ndarray shape={tuple(value.shape)} dtype={value.dtype}"]
            if value.size and np.issubdtype(value.dtype, np.number):
                finite = value[np.isfinite(value)]
                if finite.size:
                    parts.append(f"min={float(finite.min()):.6g}")
                    parts.append(f"max={float(finite.max()):.6g}")
            return " ".join(parts)
        if isinstance(value, np.generic):
            return _summarize_value(value.item(), max_text=max_text)
    except Exception:
        pass
    return type(value).__name__


def _summarize_outputs(
    proposal: ExperimentGraphProposal,
    mapping: Mapping[str, str],
    outputs: Mapping[str, Mapping[str, Any]],
) -> tuple[OutputSummary, ...]:
    summaries = []
    for proposed in proposal.nodes:
        node_id = mapping.get(proposed.proposal_id, "")
        node_outputs = dict(outputs.get(node_id, {}))
        field_names = tuple(sorted(node_outputs))
        field_summary = "; ".join(
            f"{name}: {_summarize_value(node_outputs[name])}"
            for name in field_names[:8]
        )
        if len(field_names) > 8:
            field_summary += "; …"
        summaries.append(
            OutputSummary(
                node_id=node_id,
                module_id=proposed.module_id,
                output_hash=stable_hash(node_outputs),
                fields=field_names,
                summary=field_summary or "no outputs",
            )
        )
    return tuple(summaries)


def _verification_counts(result) -> tuple[int, int, int, int]:
    records = [
        record
        for node_records in result.verification.values()
        for record in node_records
    ]
    pass_count = sum(record.state is VerificationState.PASS for record in records)
    fail_count = sum(record.state is VerificationState.FAIL for record in records)
    not_run_count = sum(record.state is VerificationState.NOT_RUN for record in records)
    return pass_count, fail_count, not_run_count, len(records)


def _module_sets(
    proposals: Mapping[ProposalStrategy, ExperimentGraphProposal],
) -> tuple[dict[ProposalStrategy, set[str]], set[str]]:
    module_sets = {
        strategy: {node.module_id for node in proposal.nodes}
        for strategy, proposal in proposals.items()
    }
    nonempty = [values for values in module_sets.values() if values]
    common = set.intersection(*nonempty) if nonempty else set()
    return module_sets, common



def _remaining_unresolved(
    proposal: ExperimentGraphProposal,
    supplied: Mapping[str, Mapping[str, Any]],
) -> tuple:
    remaining = []
    for item in proposal.unresolved_required_inputs:
        values = supplied.get(item.node_id, {})
        if item.port_name not in values:
            remaining.append(item)
    return tuple(remaining)


def compare_proposal_strategies(
    registry,
    proposals: Mapping[ProposalStrategy, ExperimentGraphProposal],
    *,
    seed: int = 0,
    gpu_enabled: bool = False,
    external_inputs: Mapping[ProposalStrategy, Mapping[str, Mapping[str, Any]]] | None = None,
) -> StrategyComparison:
    """Run ready proposals independently with the same seed and summarize them.

    The comparison never mutates the user's Experiment and never interprets a
    faster/more-verified/more-novel strategy as an automatic winner.
    """
    seed = int(seed)
    external_inputs = external_inputs or {}
    module_sets, common = _module_sets(proposals)
    summaries: list[StrategyRunSummary] = []

    for strategy in PROPOSAL_STRATEGIES:
        proposal = proposals.get(strategy)
        if proposal is None:
            continue
        modules = module_sets[strategy]
        novel_modules = tuple(sorted(modules - common))
        novelty_fraction = (
            len(novel_modules) / len(modules)
            if modules
            else 0.0
        )

        supplied_inputs = external_inputs.get(strategy, {})
        remaining_unresolved = _remaining_unresolved(proposal, supplied_inputs)
        runnable = (not proposal.is_empty) and not remaining_unresolved
        if not runnable:
            summaries.append(
                StrategyRunSummary(
                    strategy=strategy,
                    runnable=False,
                    run_attempted=False,
                    completed=False,
                    error="unresolved required inputs" if remaining_unresolved else "empty proposal",
                    seed=seed,
                    runtime_seconds=None,
                    node_count=len(proposal.nodes),
                    edge_count=len(proposal.edges),
                    unresolved_required_inputs=len(remaining_unresolved),
                    skipped_modules=proposal.skipped_modules,
                    completed_node_count=0,
                    verifier_pass=0,
                    verifier_fail=0,
                    verifier_not_run=0,
                    verifier_record_count=0,
                    all_verifiers_passed=False,
                    output_summaries=(),
                    novel_modules=novel_modules,
                    novelty_fraction=novelty_fraction,
                    semantic_experiment_sha256="",
                    full_experiment_sha256="",
                )
            )
            continue

        temporary = Experiment(name=f"Strategy comparison — {strategy}")
        id_counter = iter(f"{strategy}_{index}" for index in range(1, len(proposal.nodes) + 1))
        temporary, mapping = materialize_experiment_proposal(
            temporary,
            proposal,
            origin=(0.0, 0.0),
            id_factory=id_counter.__next__,
        )
        strategy_inputs = {}
        for proposal_node_id, values in supplied_inputs.items():
            actual_node_id = mapping.get(str(proposal_node_id))
            if actual_node_id is None:
                raise ValueError(
                    f"{strategy}: external inputs reference unknown proposal node "
                    f"{proposal_node_id!r}"
                )
            strategy_inputs[actual_node_id] = dict(values)

        started = perf_counter()
        try:
            result = GraphExecutor(
                registry,
                gpu_enabled=bool(gpu_enabled),
            ).run(
                temporary,
                external_inputs=strategy_inputs,
                seed=seed,
                run_scope=f"strategy-compare:{strategy}",
            )
        except Exception as exc:
            elapsed = perf_counter() - started
            summaries.append(
                StrategyRunSummary(
                    strategy=strategy,
                    runnable=True,
                    run_attempted=True,
                    completed=False,
                    error=f"{type(exc).__name__}: {exc}",
                    seed=seed,
                    runtime_seconds=elapsed,
                    node_count=len(proposal.nodes),
                    edge_count=len(proposal.edges),
                    unresolved_required_inputs=0,
                    skipped_modules=proposal.skipped_modules,
                    completed_node_count=0,
                    verifier_pass=0,
                    verifier_fail=0,
                    verifier_not_run=0,
                    verifier_record_count=0,
                    all_verifiers_passed=False,
                    output_summaries=(),
                    novel_modules=novel_modules,
                    novelty_fraction=novelty_fraction,
                    semantic_experiment_sha256="",
                    full_experiment_sha256="",
                )
            )
            continue

        elapsed = perf_counter() - started
        passed, failed, not_run, record_count = _verification_counts(result)
        summaries.append(
            StrategyRunSummary(
                strategy=strategy,
                runnable=True,
                run_attempted=True,
                completed=bool(result.completed),
                error="" if result.completed else result.interruption_reason,
                seed=seed,
                runtime_seconds=elapsed,
                node_count=len(proposal.nodes),
                edge_count=len(proposal.edges),
                unresolved_required_inputs=0,
                skipped_modules=proposal.skipped_modules,
                completed_node_count=len(result.outputs),
                verifier_pass=passed,
                verifier_fail=failed,
                verifier_not_run=not_run,
                verifier_record_count=record_count,
                all_verifiers_passed=bool(result.all_verifiers_passed),
                output_summaries=_summarize_outputs(
                    proposal,
                    mapping,
                    result.outputs,
                ),
                novel_modules=novel_modules,
                novelty_fraction=novelty_fraction,
                semantic_experiment_sha256=result.semantic_experiment_sha256,
                full_experiment_sha256=result.full_experiment_sha256,
            )
        )

    return StrategyComparison(
        seed=seed,
        gpu_enabled=bool(gpu_enabled),
        summaries=tuple(summaries),
        common_modules=tuple(sorted(common)),
    )
