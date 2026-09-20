#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from time import perf_counter

from cace_studio.core.reasoning import (
    NativeReasoningBackendUnavailable,
    evaluate_symmetry_reduction,
    load_exact_geometric_registry,
)


def _build_s3(native):
    swap01 = native.ExactPermutation([1, 0, 2])
    swap12 = native.ExactPermutation([0, 2, 1])
    return native.FinitePermutationGroup(3, [swap01, swap12], 64)


def run_benchmark(repetitions: int = 1000) -> dict[str, object]:
    if repetitions < 1:
        raise ValueError("repetitions must be positive")

    try:
        import _cace_runtime as native
    except Exception as exc:
        raise NativeReasoningBackendUnavailable(
            "benchmark requires the optional _cace_runtime pybind module"
        ) from exc

    registry = load_exact_geometric_registry()
    group = _build_s3(native)
    seed = native.ExactVector(
        [
            native.ExactRational(3),
            native.ExactRational(1),
            native.ExactRational(2),
        ]
    )
    orbit = [element.act_coordinates(seed) for element in group.elements]

    canonical_operator = (
        "math.combinatorics.group.canonical_coordinate_representative"
    )
    result = evaluate_symmetry_reduction(
        orbit,
        lambda state: registry.execute(
            canonical_operator,
            state,
            {"group": group},
        ),
        key=lambda value: value.canonical_text(),
    )

    start = perf_counter()
    for _ in range(repetitions):
        for state in orbit:
            state.canonical_text()
    raw_key_seconds = perf_counter() - start

    start = perf_counter()
    for _ in range(repetitions):
        for state in orbit:
            registry.execute(
                canonical_operator,
                state,
                {"group": group},
            ).canonical_text()
    canonicalization_seconds = perf_counter() - start

    return {
        "benchmark": "cace-group-reasoning-s3-v1",
        "repetitions": repetitions,
        "group_size": group.size,
        "raw_states": result.raw_states,
        "canonical_states": result.canonical_states,
        "eliminated_states": result.eliminated_states,
        "reduction_fraction": result.reduction_fraction,
        "canonicalization_idempotent": result.idempotent,
        "raw_key_seconds": raw_key_seconds,
        "canonicalization_seconds": canonicalization_seconds,
        "performance_claim": "none; timings are descriptive only",
        "evidence_authority": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Measure exact finite-group state canonicalization."
    )
    parser.add_argument("--repetitions", type=int, default=1000)
    args = parser.parse_args()
    print(json.dumps(run_benchmark(args.repetitions), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
