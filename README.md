# CACE Studio VRE v0.76

## Reliability Theorem Discovery Engine

v0.76 starts actively investigating the unresolved mesh-uniform 2D P1 residual reliability theorem without promoting numerical evidence into proof. It adds premise ablation, candidate-counterexample minimization, transparent empirical reliability-constant inference, and an explicit analytic proof-obligation DAG.

The release includes one real certified manufactured-solution anchor from the existing reference-triangle bubble benchmark. Synthetic ablation fixtures are separately labeled and contribute no continuum theorem evidence. `reliability_theorem` remains explicitly unpromotable while residual representation, local quasi-interpolation, local trace, and finite-overlap obligations are unresolved.

Qualification: 191 tests collected. The monolithic pytest invocation is watchdog-limited in this environment; all tests pass across four clean-exit partitions.

---

# CACE Studio VRE v0.25

## Consolidated evidence-aware solver policy

Combines dense-kernel benchmarks, memory accounting, conditional GPU equivalence, sparse scaling regressions, and an automatic native CPU solver selector that refuses unverified paths.

---

# CACE Studio VRE v0.24

## Larger sparse scaling/stress suite

Adds increasing structured-2D FEM factorization regressions so ordering/fill/certification behavior is tracked beyond a single 169-DOF demonstration.

---

# CACE Studio VRE v0.23

## Optional CUDA/CuPy frontal equivalence

Adds an explicitly conditional GPU dense-frontal comparison. Systems without CuPy/CUDA report NOT_RUN semantics instead of fabricating accelerator evidence.

---

# CACE Studio VRE v0.22

## Memory arena planning + allocation accounting

Adds deterministic aligned supernode arena planning and explicit workspace reuse metrics, separating structural allocation proxies from OS-level memory claims.

---

# CACE Studio VRE v0.21

## BLAS-backed dense-kernel benchmark

Adds a vendor-linked NumPy/BLAS dense-kernel benchmark and keeps native supernodal structure tied to the exact-rational oracle. No claim is made that the C++ kernel itself is BLAS-backed yet.

---

# CACE Studio VRE v0.20

## Dense-block supernodal LDLᵀ + reusable frontal workspaces + fixed thread pool

v0.20 turns the symbolic supernodes introduced in v0.18 into real numeric units in the native C++20 runtime. Consecutive compatible pivot columns are factored as dense supernode blocks, child contribution matrices are assembled through the elimination-tree structure, and thread-local frontal buffers are grown and reused rather than allocated afresh for every front.

The native runtime now exposes four comparable sparse-solve paths used by the release benchmark:

- left-looking sparse LDLᵀ;
- scalar multifrontal LDLᵀ;
- dense-block supernodal LDLᵀ with one worker;
- dense-block supernodal LDLᵀ scheduled through a fixed C++20 thread pool.

Correctness is not inferred from speed. The exact-rational sparse LDLᵀ implementation remains the structural oracle. Native paths receive numerical/backend evidence only when their factor nonzero count and fill count match the oracle and a deterministic known-solution test meets the configured error/residual tolerance.

### Scheduling and workspace contract

Supernodes are scheduled level-by-level from leaves toward elimination-tree roots. Nodes on one level are independent under the current tree contract. Every supernode must be scheduled exactly once. Each worker owns a `thread_local` dense workspace; the buffer is resized only when a larger front is encountered and is reused on later fronts.

Runtime instrumentation records:

- symbolic supernode count and largest supernode;
- thread count and scheduled task count;
- workspace growth-reallocation count;
- peak workspace entries;
- peak front size;
- dense-block flop proxy;
- machine-dependent wall time.

### Important limits

v0.20 is a real dense-block supernodal numeric implementation, but its dense block kernels are hand-written C++ loops rather than BLAS/LAPACK kernels. The scheduler is fixed-pool and level-synchronous, not work-stealing. Timing results are therefore benchmark evidence, not mathematical evidence or a claim of universal speedup. The continuum PDE formal-verification status is unchanged.

### Build and test

```bash
python -m pip install -e '.[dev]'
pytest -q
cmake -S cpp -B cpp/build
cmake --build cpp/build
./cpp/build/cace_runtime_smoke
```

The release example is `examples/supernodal_v020.cace`; its report, summary, and benchmark PNG are stored beside it.


## v0.26

Canonical reproducibility fingerprints for sparse systems and ordering analyses.


## v0.27

Mixed-precision iterative refinement with float64 residuals and exact structural oracle.


## v0.28

Hash-chained experiment checkpoints for resume/integrity auditing.


## v0.29

Sparse matrix health and conditioning-proxy diagnostics with explicit non-theorem scope.


## v0.30

Multi-right-hand-side solve campaigns reusing one certified sparse structure.


## v0.31

Structured 3D seven-point discrete Poisson stress testing; explicitly not tetrahedral continuum FEM.


## v0.32

Resource-aware solver portfolio scoring after correctness gates.


## v0.33

Content-addressed provenance manifests with deterministic root digest.


## v0.34

Negative/fault-injection verification that requires refusal under corrupted evidence.


## v0.35

Consolidated deterministic verification campaign spanning v0.26-v0.35.

## v0.36

Deterministic replay fingerprints. Evidence boundaries are unchanged unless explicitly stated by a verifier.

## v0.37

Certificate schema validation. Evidence boundaries are unchanged unless explicitly stated by a verifier.

## v0.38

Structural scaling/convergence audit. Evidence boundaries are unchanged unless explicitly stated by a verifier.

## v0.39

Sparse operator health diagnostics. Evidence boundaries are unchanged unless explicitly stated by a verifier.

## v0.40

Compensated reduction reference. Evidence boundaries are unchanged unless explicitly stated by a verifier.

## v0.41

Deterministic parameter sweep. Evidence boundaries are unchanged unless explicitly stated by a verifier.

## v0.42

Deterministic DAG campaign scheduling. Evidence boundaries are unchanged unless explicitly stated by a verifier.

## v0.43

Ordering Pareto portfolio. Evidence boundaries are unchanged unless explicitly stated by a verifier.

## v0.44

Exact factor replay checksum. Evidence boundaries are unchanged unless explicitly stated by a verifier.

## v0.45

Verification failure minimization. Evidence boundaries are unchanged unless explicitly stated by a verifier.

## v0.46

Append-only hash-chain evidence ledger. Evidence boundaries are unchanged unless explicitly stated by a verifier.

## v0.47

Expanded 3D discrete scaling. Evidence boundaries are unchanged unless explicitly stated by a verifier.

## v0.48

Performance regression budget policy. Evidence boundaries are unchanged unless explicitly stated by a verifier.

## v0.49

Release qualification matrix. Evidence boundaries are unchanged unless explicitly stated by a verifier.

## v0.50

Cumulative v0.50 evidence milestone. Evidence boundaries are unchanged unless explicitly stated by a verifier.


## v0.75

Cumulative verified-research milestone. See `RELEASE_MANIFEST.json`.
