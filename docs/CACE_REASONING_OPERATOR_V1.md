# CACE ReasoningOperator v1

Status: engineering/research runtime. **Not proof evidence.**

## Purpose

ReasoningOperator is the typed advisory bridge between the Local Research
Assistant and CACE's canonical mathematical tools.

It does not create a second mathematical engine. The operator registry points
to canonical implementations such as the exact C++ RMK/group-action backend.

## Trust boundary

Every operator descriptor has:

`evidence_authority = false`

Reasoning execution, plan success, symmetry reduction, paired-intervention
scores, and model confidence cannot create or promote VerificationRecord,
ProofStatus, claim-registry, proof-ledger, or FORMAL state.

If a reasoning step needs authoritative mathematical evidence, it must request
the existing exact/certified/formal subsystem separately.

## Initial exact geometric operator set

- permutation inverse/compose;
- permutation action on exact coordinates;
- permutation action on exact exterior elements;
- finite-group canonical coordinate representative;
- finite-group canonical exterior representative;
- exact wedge;
- exact Hodge dual under the declared Euclidean basis convention;
- exact exterior pushforward;
- exact affine-map application;
- exact simplex barycentric coordinates.

The Python layer contains orchestration metadata and calls. The mathematical
operations themselves remain in `cpp/include/cace/math/**`.

## Evaluation

The first evaluation utilities include:

- paired intervention correctness;
- necessary answer-flip consistency;
- invariance under irrelevant interventions;
- symmetry-state canonicalization;
- canonicalization idempotence.

The benchmark script:

`python scripts/benchmark_group_reasoning.py`

uses the optional `_cace_runtime` pybind module and measures S3 orbit
canonicalization. It reports state-count reduction and descriptive timing.

A reduction in equivalent search states is not automatically a wall-clock,
token, quality, or intelligence improvement. Those must be measured separately
on representative planning/model workloads.

## Next slice

1. persist operator mastery statistics;
2. add procedural exact group/geometric task generators;
3. add composition-holdout evaluation;
4. connect operator descriptors to the Local Agent Tool Bus;
5. feed experiment heartbeat/perception deltas into operator planning;
6. route discovered exact invariants into ProofOpportunity records.
