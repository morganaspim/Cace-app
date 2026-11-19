# Quantifier-aware temporal witness atlas

Research checkpoint, 2026-11-19. Not production deployment, independent CACE qualification, or a global-novelty claim.

## Actual formal advance

`TemporalWitness.lean` has 17 core-only theorems compiled and axiom-audited on the existing OCI runner, Lean 4.32.1, ARM64. Successful run: https://github.com/morganaspim/Cace-app/actions/runs/44594388375 . Exact source commit `966cee1eee9d58e094f9602cbc87c5e59df3b833`, blob `41608e663422e0c86bd7e036ec7b2eee900050d6`, SHA256 `c27c185b5ef9f300c24eccba087c40bdc674bfb1eda57bca45a71fa6d3b463d7`. Workflow commit `fa2430eb0bd61bc6ea281a85fdd8927221e3f9f2`.

Ten theorems report no axioms; seven use only standard propext and/or Quot.sound. Both false controls, 0=1 and a single Boolean equaling both possible Booleans, were rejected logically. No native proof escape, custom axiom or recovery sorryAx occurs in the accepted audit. Independent kernel replay/comparator and canonical CACE qualification were not performed.

The first run 44594059075 failed when a rewrite encountered an unreduced lambda in the pulled-back predicate. The exit status and axiom audit rejected the recovery placeholder. Explicit `change` statements exposed the predicate before rewriting; premises and resource limits were unchanged. Failed source, logs and archive remain preserved.

The earlier 18 statements in `XenoCore.lean` remain uncompiled. A narrow Mathlib import still fails reading Lean/Data/Lsp/LanguageFeatures.olean.private. Targeted metadata and first-byte probes show this and Lean/Structure.ir exist and are readable; the actual import/mapping failure remains unresolved. No shared cache was changed. The older `run_compiler.py` is an unexecuted, incomplete multi-file harness, not the successful workflow; some files it references remain unstaged.

## Shared state is not a mixture or a succession of unrelated states

For a state-transition family Phi_t and observations mu_i, a joint trajectory witness means:

    exists x0, for all selected (i,t), threshold <= mu_i(Phi_t(x0)).

The same x0 must work throughout. Moving the existential quantifier inside the time/observation quantifier changes the question. It does not solve a paradox or establish a valid trajectory.

The six-phase rotating example has these membership rows, one row per initial state and one column per time:

    [1,   1/4, 1/4]
    [3/4, 0,   3/4]
    [1/4, 1/4, 1]
    [0,   3/4, 3/4]
    [1/4, 1,   1/4]
    [3/4, 3/4, 0]

One shared trajectory has grade 1/4. Every pair of times has grade 3/4. Separate states at each time yield 1. A uniform probability mixture over rows 0,2,4 yields expected membership 1/2 at each time. Every row sums to 3/2, so no probability mixture can make all three expected observations exceed 1/2.

For that same mixture, the expectation of the pathwise minimum is only 1/4. In general, for any distribution p over rows,

    E_p[min observations] <= max_row min observations
        <= max_p min_observation E_p[observation]
        <= min_observation max_row observation.

Fuzzy cell values are membership grades, not probabilities. The simplex coordinates p genuinely describe randomization over states. A good expected observation does not imply a single successful trajectory.

## Coordinate-independent scoped theorem

If f:X->Y is onto and f(Phi_t(x))=Psi_t(f(x)), and source observations are pullbacks of target observations, then a shared-initial-state witness exists in X exactly when it exists in Y. This is proved as `trajectory_surjective_transport` for arbitrary typed carriers and index sets.

It does not assume or prove differential-equation existence, semigroup laws, injectivity or preservation of every possible source observation. A noninjective map may lose information invisible to the declared observations. `matched_slack_transfer` separately proves additive threshold-error transport in natural-number fixed-point grade units, not general real analysis.

The local research adapter distinguishes shared_state, separate_state, mixture_expected and mixture_pathwise. It refuses a witness-mode mismatch. It reuses Merlin ArtifactRef and scientific-loop primitives, but its resolver is a fixture, not the deployed canonical registry or a live Hermes worker. Parallel Python and Lean examples do not yet prove runtime-to-formal linkage.

## Exact finite measurements

The additive local laboratory passed 52 tests and a fresh-directory replay. The prior 308-test suite was not rerun.

All 512 binary 3x3 tables were examined. Exact rational primal and dual optimization agreed on every case; 174 had a strictly larger randomized-expected value than the shared-state value. The largest mixture gap was 2/3; the largest separate-state gap was 1. These are finite objective-relaxation gaps, not alienness percentages or population estimates.

All 720 relabelings of the six-state example preserved the query-order profile. Thirty-two independently implemented SciPy/HiGHS numerical LP checks matched the exact values. Seven additional n-way controls, n=2 through 8, preserve every proper subset of queries but fail the full conjunction. The exact primal and dual enumerators share code; the HiGHS checks are a separate numerical implementation, not independent proof.

Six problem-directed primitives and ten authored pair contracts produced 16 combinations from 35 examined pairs/triples; 19 were rejected and none omitted. Pairwise compatibility is not a proof of whole-system feasibility. The plan update is a proposal linked to canonical master v6, not an overwrite.

## Fractal extension, explicitly exploratory

After the main finite study, encode binary sequences by x=sum(2*b_k/3^(k+1)). All sequences form the middle-thirds Cantor set. Forbid the contiguous temporal pattern 111. Every adjacent pair 00,01,10,11 remains possible, but an actual three-way rule has changed.

The trailing-ones automaton has adjacency matrix

    [[1,1,0], [1,0,1], [1,0,0]],

with characteristic polynomial z^3-z^2-z-1. Exact recurrence N_0=1,N_1=2,N_2=4 and N_n=N_(n-1)+N_(n-2)+N_(n-3) agrees with direct enumeration at lengths 0 through 16 (131071 total words). An 80-step rational root bracket gives tau approximately 1.8392867552141612.

Established separated graph-directed dimension theory gives:

    dim(full Cantor) = log(2)/log(3) approximately 0.6309297536
    dim(no-111 subset) = log(tau)/log(3) approximately 0.5546796351.

The dimension statement follows from the standard theorem and the explicit separated construction, not from finite counts. It is NOT Lean-proved. Equality of allowed adjacent pair patterns does not imply equality of pairwise probability laws or all geometry. The rule changes the admissible set; it is not a coordinate change or physical-dimension claim.

An analytic circle extension also distinguishes pure trajectory, mixture and separate witnesses: with n equally spaced times and membership (1+cos(theta))/2, the pure value is (1-cos(pi/n))/2, mixture optimum 1/2, separate value 1. This continuum formula is a reviewed mathematical derivation, not a Lean-checked theorem.

## Literature and interpretation

Multiway Dowker theory already treats higher-order relations: https://arxiv.org/abs/2506.10909 . Signal temporal logic already provides quantitative semantics for continuous/hybrid observations: https://arxiv.org/abs/2008.00097 . Graph-directed dimensions and spectral-radius calculations are established: Mauldin-Williams, https://sites.math.unt.edu/~mauldin/papers/no67.pdf ; Friedland, https://www.sciencedirect.com/science/article/pii/S0024379597003716 . The dimension sources were reviewed through their primary abstracts/definition excerpts; no full-paper claim is made. Lean evidence boundaries follow https://lean-lang.org/doc/reference/latest/ValidatingProofs/ .

No new calibrated alienness or community-availability model was run. The measured contribution is a counterexample catalogue, explicit semantic contracts and a small audited proof layer. A representation that improves a score by changing the witness contract has not improved the original problem.

## Next acceptance gate

Bind a runtime-generated trajectory table to the formal definition and certify the serialization/interpretation relation. Then test new nonlinear traces against strong temporal-logic and optimization baselines at matched semantics, precision and cost. Diagnose pinned Mathlib imports separately, without deleting shared runner data.

The cloud workflow used bounded CPU/wall/output and a 3GiB address-space limit with 16MiB Lean thread stacks. It is fixed-source research, not a general untrusted-code sandbox. No Avrea, installs, cache replacement, production-service change, merge, signing, qualification or promotion occurred. Keep this research stack draft; do not bulk-merge its ancestors.
