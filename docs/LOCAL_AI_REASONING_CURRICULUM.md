# CACE Local AI Reasoning Curriculum and Geometric Evaluation

Status: research/engineering design. Not proof evidence, not a claim of human-like thought, and not an assertion of novelty over the literature.

Date: 2026-09-19

## Objective

Train and evaluate the local CACE AI so that success depends on **learning reusable operations and structural relationships**, not memorizing answer surfaces.

The target behavior is a compact specialist that can:

1. identify the load-bearing structure of a problem;
2. choose a small set of valid operations;
3. apply them in a sensible order;
4. track how conclusions change under interventions;
5. transfer the same method to relabeled, geometrically transformed, or newly generated instances;
6. verify the result against explicit invariants, executable checks, or CACE evidence.

The design deliberately avoids dependence on hidden chain-of-thought disclosure. Reasoning is tested by behavior under controlled transformations and by externally checkable intermediate objects.

## Inspiration and attribution

The **geometric reasoning and training/curriculum direction is Sophonic-AI-inspired at the level of high-level ideas**.

CACE uses that inspiration as a prompt to investigate structured/geometric representations, transformation-aware training, compositional reasoning, counterfactual evaluation, and compact reusable operator programs.

CACE must still implement its own architecture, datasets/task generators, mathematical operators, training objectives, evaluation suite, code, and proof/evidence integration. This attribution does not imply affiliation with Sophonic AI, compatibility with any proprietary Sophonic system, access to non-public methods, or transfer of external verification claims.

## Independent-design / IP rule

CACE may take inspiration from **publicly described general ideas** such as paired counterfactual/perturbation evaluation, compact specialist models, geometric representations, curriculum learning, program induction, contrastive learning, and cellular automata.

Do not copy:

- proprietary source code;
- unreleased training recipes;
- confidential model internals;
- patented claim language as an implementation specification;
- trademarked branding as if it were CACE technology;
- dataset content whose license does not permit the intended use.

CACE should implement its own task generators, loss functions, data schemas, operator library, model architecture, and evaluation code from first principles and permissively licensed/public-domain building blocks.

Before commercial deployment, a separate license/provenance review and, where appropriate, patent freedom-to-operate review should be performed. This document itself does not provide legal clearance.

## 1. Core learning unit: operation, not answer

Represent a reasoning task as:

[
(s_0, O_1, O_2,ldots,O_k, s_k, y)
]

where:

- `s_0` is the initial structured state;
- each `O_i` is an allowed abstract operation;
- `s_k` is the resulting state;
- `y` is the externally checkable answer.

Example operator vocabulary:

- OBSERVE
- NORMALIZE
- DECOMPOSE
- IDENTIFY_INVARIANT
- MAP
- PROJECT
- ROTATE
- REFLECT
- SCALE
- COMPOSE
- SUBSTITUTE
- INVERT
- COUNTERFACTUAL
- COMPARE
- BOUND
- CHECK
- REPAIR
- VERIFY

The model should learn that different surface questions may share the same operator program.

## 2. Pedagogical curriculum

Use a teacher-style progression rather than random brute-force exposure.

### Stage A — one operation

Teach isolated transformations with many procedurally generated examples.

Examples:

- reflection;
- rotation;
- parity flip;
- implication;
- conservation;
- graph edge reversal;
- affine map;
- set complement.

### Stage B — two-operation compositions

Require the correct **order**.

Example:

`normalize -> rotate`

must be distinguished from

`rotate -> normalize`

when the operators do not commute.

### Stage C — short programs

Train 3–6 operation sequences with distractors.

### Stage D — inverse problems

Provide the result and ask which valid sequence could have produced it.

### Stage E — counterfactual interventions

Change exactly one load-bearing premise. The conclusion must update coherently.

### Stage F — transfer

Apply the learned operation program to:

- unseen labels;
- unseen numerical values;
- new graph topologies;
- rotated/reflected coordinate systems;
- different surface wording;
- different but isomorphic representations.

### Stage G — discovery

Ask the model to propose a candidate invariant/operator sequence, then test it in CACE before reinforcement.

## 3. Anti-memorization data generation

Prefer procedural generators over static answer corpora.

For every task family generate large equivalence classes using:

- symbol renaming;
- permutation of irrelevant facts;
- coordinate rotation/reflection;
- scale changes;
- graph relabeling;
- alternate textual phrasing;
- distractor injection;
- answer-balanced generation;
- reversed/inverse instances;
- counterexamples;
- minimally perturbed paired instances.

Keep train/test generator seeds and structural templates separated.

Hold out entire **operation compositions**, not only examples, to test compositional generalization.

## 4. Paired answer-flip evaluation

For each canonical item create a paired intervention:

[
P ightarrow A
]

then minimally change a load-bearing fact:

[
P' ightarrow A'
]

where a valid reasoner must recognize that the correct answer changed.

Do not merely measure whether the final token flips. Measure whether:

1. the canonical answer is correct;
2. the perturbed answer is correct;
3. the answer changed iff the changed premise is causally load-bearing;
4. the selected operator program changed at the correct point;
5. irrelevant perturbations leave the answer invariant.

This becomes CACE's independently implemented **paired intervention consistency** metric.

## 5. Reasoning evaluation suite

Track separate metrics.

### Pair correctness

Both members of a canonical/perturbed pair must be correct.

### Necessary-flip sensitivity

When a load-bearing fact changes, the answer changes correctly.

### Invariance score

When only irrelevant/symmetry-preserving details change, the answer remains correct.

### Operator-program validity

The emitted operator sequence type-checks and executes.

### Order sensitivity

The model distinguishes noncommuting operation orders.

### Inverse consistency

Forward and inverse tasks agree.

### Isomorphism transfer

Performance survives symbol/graph/coordinate relabeling.

### Composition holdout

Performance on operator compositions absent from training.

### Distractor robustness

Performance under increasing irrelevant-information density.

### Memorization leakage test

Search nearest training structures and compare performance on high-similarity versus structurally novel items.

### Verification closure

Final claims survive the appropriate CACE checker, theorem, certificate, or simulator.

No single metric is called “thinking.” The test suite measures a collection of behaviors expected from reusable reasoning.

## 6. Geometric reasoning representation

Use mathematical structure to compress chaotic real-world data before asking the model to relate everything to everything.

Candidate representations:

- typed graphs;
- manifolds / local charts where justified;
- symmetry groups and group actions;
- invariant/equivariant features;
- sparse geometric algebra / blades / rotors where useful;
- spectral graph embeddings;
- multiscale coordinates;
- conserved quantities;
- low-rank/subspace structure;
- topological summaries;
- causal/intervention graphs.

The model should preferentially search over **structured transformations** rather than all pairwise raw-feature relationships.

Example:

[
	ext{raw observations}
	o
	ext{typed relational graph}
	o
	ext{candidate symmetry/invariant}
	o
	ext{small operator program}
	o
	ext{prediction}
	o
	ext{counterfactual test}
]

## 7. Geometry-aware training objectives

Possible independent objectives:

### Equivariance consistency

If input state transforms by (g), the internal/result representation should transform predictably.

[
f(gx) approx ho(g) f(x)
]

where (ho) is explicitly declared.

### Invariant agreement

For invariants (I):

[
I(x) = I(gx)
]

for allowed symmetry transforms.

### Contrastive structural loss

Bring states with the same operator structure closer while separating superficially similar states with different causal/operator structure.

### Program consistency loss

Predicted operator program must execute to the predicted result.

### Counterfactual consistency loss

Minimal causal interventions must induce the appropriate result/program change.

### Simplicity regularization

Prefer a shorter valid operator sequence over a longer equivalent sequence when both solve the task.

This encourages reusable methods rather than brute-force association.

## 8. Teacher / pedagogy controller

Create a curriculum scheduler that estimates mastery per operator and composition.

For skill (j), maintain:

- success rate;
- pair consistency;
- invariance score;
- transfer score;
- confidence calibration;
- recency-weighted error families.

Select the next lesson near the frontier of competence:

[
	ext{known} ightarrow 	ext{one controlled extension}
]

rather than random difficulty jumps.

When failure occurs:

1. identify the first invalid operation;
2. generate simpler sibling examples around that operation;
3. retrain/rehearse;
4. retest the original composition;
5. test an isomorphic unseen variant.

This mirrors effective pedagogy: isolate the missing operation, then recompose.

## 9. Explicit world-navigation operator memory

The local AI should maintain a learned **operator library** rather than an answer notebook.

Each learned operator record can include:

- stable operator ID;
- typed input/output schema;
- preconditions;
- invariants;
- inverse if known;
- commutation relations;
- composition examples;
- failure conditions;
- cost estimate;
- confidence/validation state;
- CACE modules that implement/check it.

This lets the model internalize “what operations work when” and how operations compose.

## 10. Canvas <-> local AI connection

Every semantic canvas node should expose a typed state channel to the local AI:

- node ID;
- module type;
- semantic hash;
- verification state;
- inputs ready?;
- outputs ready?;
- stale?;
- blocked?;
- error family?;
- research-interest score;
- dependency neighbors.

AI suggestions should reference node IDs and typed operations, not arbitrary screen coordinates.

## 11. Conway-inspired custom heartbeat field

Use a deterministic cellular-automaton-like layer as a **coordination/visualization heartbeat**, not as proof evidence.

Each canvas item owns one heartbeat cell or neighborhood.

Suggested states:

- DORMANT
- READY
- ACTIVE
- WAITING
- BLOCKED
- STALE
- VERIFYING
- VERIFIED
- FAILED
- RESEARCH_INTEREST

Update on fixed ticks using local neighborhood rules.

Example custom rules:

1. READY + all required neighbors VERIFIED -> ACTIVE
2. ACTIVE + output produced -> VERIFYING
3. VERIFYING + checker PASS -> VERIFIED
4. dependency semantic hash changes -> STALE
5. FAILED propagates BLOCKED only across hard dependencies
6. RESEARCH_INTEREST can diffuse weakly across related nodes but can never alter verification state
7. AI attention follows activity gradients but cannot promote a cell to VERIFIED
8. heartbeat expiry returns abandoned transient states to DORMANT/WAITING safely

The automaton should be **Life-inspired, not literal Conway Life**, because semantic dependency states need typed deterministic rules.

## 12. Heartbeat geometry

Render the heartbeat as an optional overlay.

Possible mappings:

- each node = cell;
- each edge = neighbor relation;
- local cluster activity = glow/pulse frequency;
- proof-valid state = stable pattern;
- stale/error state = visibly unstable pattern;
- AI research attention = separate non-authoritative halo.

The heartbeat field may also feed the local AI a compact activity representation:

[
H_t = (V, E, s_t)
]

and temporal difference:

[
Delta H_t = H_t - H_{t-1}
]

so the AI can reason about what changed without rereading the entire canvas.

## 13. Game-of-Life research mode

Separately from production coordination, CACE may expose a research sandbox in which Conway/Life-like local rules are evolved or searched as candidate computational substrates.

This mode must be labeled experimental.

Potential experiments:

- whether local rule dynamics create useful sparse attention routing;
- whether stable/oscillating structures encode reusable operator motifs;
- whether heartbeat topology predicts bottlenecks;
- whether cellular dynamics help curriculum scheduling.

No claim should be made that cellular automata inherently create reasoning.

## 14. Tests for “method learning”

A model passes the reasoning curriculum only if it succeeds on:

1. canonical task;
2. load-bearing answer-flip pair;
3. irrelevant perturbation invariance;
4. symbol-renamed instance;
5. coordinate-transformed instance;
6. inverse problem;
7. unseen operator composition;
8. increased distractor density;
9. executable operator-plan validation;
10. checker/simulator verification.

A memorizer can pass some items. It should fail the combined battery.

## 15. Data contamination protection

Record for every generated task:

- generator version;
- seed;
- structural template ID;
- operator program;
- canonical/perturbed pair ID;
- split;
- answer;
- verification result.

Keep test generator families and held-out composition templates inaccessible to ordinary training.

Use cryptographic hashes for released eval sets so repeated tuning against the test set is visible.

## 16. Integration with CACE Grow

Grow should generate hypotheses in operator language.

Example:

`DECOMPOSE -> ROTATE -> IDENTIFY_INVARIANT -> COMPARE`

The local AI may rank candidate programs.

CACE then:

1. builds the corresponding experiment graph;
2. runs/checks it;
3. stores evidence;
4. updates the Research Idea;
5. records whether the operator motif transferred to sibling problems.

Validated motifs may become curriculum material. Failed motifs remain useful negative examples.

## 17. Safety and truth boundary

The reasoning model remains advisory.

- operator-program validity is not mathematical proof unless checked by the appropriate formal/exact verifier;
- high flip consistency is not proof of general intelligence;
- geometric embeddings are model representations, not discoveries by themselves;
- heartbeat states are orchestration metadata, not scientific evidence;
- AI confidence cannot change PASS/FAIL/NOT_RUN;
- CACE formal qualification remains unchanged.

## 18. First implementation slice

Build the smallest useful version:

1. `ReasoningOperator` schema;
2. procedural generator for 5–10 simple operator families;
3. canonical/perturbed pair schema;
4. paired intervention evaluator;
5. symbol/coordinate relabel transforms;
6. executable operator-plan checker;
7. curriculum mastery table;
8. canvas heartbeat state machine;
9. heartbeat overlay;
10. local-AI context packet containing node graph + heartbeat delta;
11. regression tests proving verification state cannot be promoted by AI/heartbeat rules.

Only after this baseline works should CACE experiment with representation-learning changes inside the local neural model.


## 19. Combinatorial/group canonicalization for efficient reasoning

Prioritize exact group/combinatorial operators as compact reasoning primitives.

Useful patterns include:

```text
state
 -> detect symmetry/group action
 -> canonical representative
 -> solve/reason once
 -> transport result across orbit
 -> checker/theorem validation
```

and:

```text
long transform sequence
 -> identify generators
 -> compose/normalize group element
 -> execute one canonical action
 -> verify invariant/equivariance
```

Candidate operator families:

- permutation / compose / inverse;
- orbit / stabilizer;
- canonical representative;
- group action;
- coset for supported finite cases;
- Cayley neighbor/action lookup;
- incidence and boundary composition;
- rewrite to normal form.

Use only mathematically declared actions. Do not infer a symmetry group because an embedding "looks symmetric."

Measure whether the representation reduces planning steps, token/context use, search states, latency or error rate relative to baselines.

## 20. Proof discovery as curriculum growth

The experiment-to-proof system in `docs/EXPERIMENT_TO_PROOF_DISCOVERY_LOOP.md` may propose new reusable operator motifs.

Only after a mathematical operation has the appropriate exact/certified/formal support and engineering review should it enter the trusted operator curriculum as a validated operation.

Unproved conjectures may remain research examples, never trusted operator rules.


## 21. Implemented ReasoningOperator v1 bridge

The first operator-runtime slice is implemented in:

- `cace_studio/core/reasoning.py`
- `schema/cace-reasoning-operator.schema.json`
- `docs/CACE_REASONING_OPERATOR_V1.md`
- `scripts/benchmark_group_reasoning.py`

The initial registry maps advisory operator IDs to the canonical exact C++/pybind
RMK implementations for permutations, finite-group canonicalization, exterior
algebra, affine maps and simplex barycentric coordinates.

The Python layer deliberately does **not** reimplement those mathematical
algorithms.

Initial evaluation support includes paired interventions and measured
symmetry-state canonicalization. All results carry
`evidence_authority=false`.

This completes the schema/registry portion of the first implementation slice.
The next curriculum work is procedural task generation, composition holdouts,
mastery statistics, Tool-Bus integration and heartbeat-aware planning.


## 22. Implemented curriculum engine v1

The first executable curriculum layer is now implemented in:

- `cace_studio/core/reasoning_curriculum.py`
- `tests/test_reasoning_curriculum.py`

Implemented capabilities:

- immutable `ReasoningTask` and `ReasoningTaskOutcome` records;
- deterministic operator-composition signatures and train/holdout assignment;
- executable task evaluation through `ReasoningOperatorRegistry`;
- paired baseline/intervention task evaluation;
- per-skill mastery, pair-consistency, and transfer statistics;
- deterministic frontier selection near a target competence level;
- seeded exact permutation-action pair generation using the canonical native backend for expected outputs.

The curriculum layer remains advisory. Every task, outcome, pair, and mastery
record has `evidence_authority=false`. Curriculum accuracy, pair consistency,
or transfer performance cannot promote mathematical/scientific evidence.

The underlying RMK Lean bridge may be canonically qualified for its explicitly
audited theorem surface, but that does not make curriculum scheduling,
task-generation policy, model behavior, or arbitrary native runtime algorithms
formal proof evidence.

Implemented in the same curriculum batch:

1. exact paired task generators for permutation action, finite-group coordinate canonicalization, exterior wedge, affine application, and simplex barycentric coordinates;
2. deterministic multi-family batches with one entire generator family held out for transfer evaluation;
3. an Agent Perception Packet adapter that converts heartbeat/change/residual/resource/research-interest state into non-evidentiary curriculum attention signals;
4. deterministic heartbeat-aware lesson ranking layered on top of mastery statistics.

The perception adapter consumes the existing
`schema/cace-agent-perception.schema.json` contract. It does not create a
parallel heartbeat format and rejects any packet that attempts to set
`evidence_authority=true`.

Remaining implementation priorities are:

1. integrate task execution/reporting with the future concrete AgentController / typed CACE Tool Bus runtime once that class exists;
2. persist/replay generated curriculum batches with generator-version and seed manifests;
3. add measured raw-vs-symmetry-canonicalized workload benchmarks to the curriculum evaluation report;
4. connect accepted Research Ideas / canvas node types to explicit skill IDs for automatic but reviewable lesson targeting;
5. add model-provider training adapters only after the deterministic task/evaluation contracts are stable.
