# ADR-0047: Offline Hybrid Research AI and Grow

Status: Accepted for experimental implementation — 2026-09-18

## Decision

CACE Studio's local assistant may use a hybrid research engine outside the
verification trusted computing base.

The engine is intentionally split into:

1. a local neural language model chosen by the user through the existing
   loopback-only provider interface;
2. deterministic sparse retrieval over local CACE source and metadata;
3. tiny signed-hash latent sketches for cheap reranking;
4. prompt-expert routing;
5. bounded combinatorial concept search;
6. seeded semantic random walks for controlled novelty;
7. multi-step experiment/hypothesis proposals.

AI output, Grow output, retrieved source, and generated combinations are never
verification evidence and never promote claim/proof state.

## Grow semantics

The Grow button expands the *research search space*. It does not corrupt or
perturb canonical scientific data.

For a query, one Grow cycle:

- retrieves a bounded set of relevant local fragments;
- routes to a small set of specialist prompt experts;
- performs a reproducible semantic random walk;
- evaluates concept combinations of size 2 through 4;
- penalizes combinations already explored in the current session;
- emits cheap next-step experiments or proof obligations;
- passes the bounded context to the next local-model request only after user
  review.

The chaos setting is a bounded exploration weight. It changes candidate
selection, not source data, proof evidence, or model weights.

## Ranked cheap-learning mechanisms

Highest value per unit of compute first:

1. **Incremental sparse retrieval and cache reuse.**
   Learn the local project faster by indexing only local source and reusing the
   in-memory index during the session.
2. **User-query expert routing.**
   Route proof, experiment, geometry, code, pattern, and general questions to
   focused instructions instead of making every prompt invoke every capability.
3. **Anti-repeat novelty memory.**
   Penalize already explored fragments/combinations so repeated Grow cycles buy
   new coverage with the same compute budget.
4. **2-4 way combinatorial concept search.**
   Test small cross-domain groups for shared invariants, equivalent
   representations, or falsifiable experiments. Larger groups are deferred
   unless earlier groups justify them.
5. **Seeded semantic random walk.**
   Occasionally leave the nearest-neighbor path to discover adjacent concepts,
   while preserving exact reproducibility for a query/cycle.
6. **Compressed latent sketch reranking.**
   Use a tiny deterministic signed-hash vector to capture token interactions
   without requiring an embedding model.
7. **Multi-step proposal heads.**
   Produce several next experiments/proof obligations from one retrieval pass,
   analogous in spirit to predicting more than one useful next unit.
8. **Optional local neural embeddings.**
   Add only when a dedicated local embedding model is available and the quality
   gain justifies its inference cost.
9. **User-approved persistent memory.**
   Persist only accepted useful discoveries; never train automatically on the
   model's own unreviewed outputs.
10. **LoRA/fine-tuning or distillation.**
    Much later: requires curated data, evaluation, rollback, licensing review,
    and more compute. It is not the default Grow path.

## DeepSeek architectural inspiration

CACE may borrow general architectural ideas, not implementation identity:

- sparse candidate selection inspired by sparse-attention efficiency;
- small specialist prompt experts inspired by mixture-of-experts routing;
- compact latent sketches inspired by latent attention/compression;
- deterministic routing bias to reduce expert collapse;
- multiple next-step proposals inspired by multi-token prediction.

The CACE implementation is deliberately small and dependency-light. It does not
attempt to reproduce DeepSeek's parameter scale, training recipe, kernels, or
weights.

As of this ADR, DeepSeek-V3.2-Exp is a useful public reference for sparse
attention and states that its repository and model weights are MIT licensed.
Any future direct incorporation of third-party code or weights still requires a
separate license/provenance review at the exact version used.

## Security and trust boundary

- Provider endpoints remain loopback-only.
- Proxy environment variables and redirects remain disabled for local AI.
- Corpus reads are bounded to an allowlisted local CACE checkout.
- Grow has no write path to claim registries, proof ledgers, certificates, or
  experiment graphs.
- Graph mutation remains a user-reviewed UI action.
- Formal qualification remains independent of AI state.


## Persistent user-supervised growth memory

Persistent Grow memory is explicit feedback, not automatic self-training.

For the latest Grow candidate the user can choose:

- **Keep** — retain the concept/group for gentle future resurfacing;
- **Useful** — add a bounded positive ranking preference;
- **Reject** — add a bounded negative preference without deleting canonical source.

Only these explicit user actions write persistent feedback. Queries are stored
only as SHA-256 digests; the memory file does not store the plaintext research
question. Target ids identify local corpus fragments/groups.

Feedback influence is capped. A later explicit feedback direction can override
stale preference in the opposite direction. Kept concepts may be recalled into
a small shortlist but do not outrank strongly relevant current-query results by
recall alone.

The memory file is local, atomic-replaced, permission-hardened where supported,
and separate from experiments, claims, proof ledgers, certificates, and
verification results. The UI provides **Clear Grow Memory** so the user can
erase all persistent research-preference events without affecting scientific
or formal state.

## Animated coordinate preview

CACE may animate transform results as an evidence-neutral presentation layer.

Scientific modules can opt into `animation_payload()` and provide explicit
source/target coordinate arrays. The GUI interpolates only the displayed
points; it does not alter the module output consumed by verification. The
coordinate preview anchors axes to true coordinate zero when visible.

Local-AI activity can use the same preview surface with deterministic
pseudo-coordinates for visual delight, but this mode is labeled as a decorative
semantic-activity map and must never be presented as scientific geometry,
embedding coordinates, or verification evidence.


## Individually rateable Grow discovery cards

Each completed Grow cycle exposes a small mixed shortlist of up to five
discoveries for explicit user feedback.

The shortlist deliberately mixes:

- up to three high-scoring concept groups; and
- individual retrieved source concepts for independent rating.

Group and fragment score scales are not treated as directly calibrated against
one another. Reserving slots for both prevents a numerically larger score from
one candidate family from crowding out the other.

Each card displays a human-readable title, source/rationale context, score, and
novelty when available. Every card has its own **Keep / Useful / Reject**
controls. Rating one card disables only that card for the current Grow cycle;
the other cards remain independently rateable.

Candidate target ids are derived from canonical local corpus fragment ids and
sorted group membership. Unchanged local source therefore produces stable
feedback targets across restarts. If a source file changes, its content digest
changes intentionally, so stale feedback does not silently attach to materially
different content.

The panel is a research-preference surface only. Card feedback cannot write
experiments, claims, proof ledgers, certificates, or verification results.


## Research Ideas notebook

A **Keep** action promotes a Grow discovery only into a local planning artifact
called `ResearchIdea`. This is deliberately different from promoting a
scientific claim or formal theorem.

Each Research Idea contains editable:

- title;
- notes;
- hypotheses;
- proposed experiment;
- associated CACE module ids;
- local source provenance; and
- workflow status.

The workflow statuses are:

`Idea → Testable → Experimented → Promising → Proof Candidate`

These labels describe research maturity only. In particular, **Proof Candidate**
means "worth attempting to formalize"; it does not write or imply
`ProofStatus.FORMAL`, Lean compilation, kernel audit, qualification, claim
registry state, certificate state, or verification PASS.

The notebook is stored atomically in
`~/.cace/research_ideas.json` by default, with an environment override for
testing/deployment. The source query is represented by SHA-256 rather than
stored in plaintext. A stable unchanged Grow candidate maps idempotently to one
Research Idea so repeatedly keeping the same discovery does not create duplicate
notebook spam.

The Research Ideas dock supports manual idea creation, editing, deletion,
filtering by status, direct status selection, and one-click lifecycle
advancement. The user can also move an idea backward when new evidence weakens
it.

When Keep creates or finds an idea, CACE opens that idea in the notebook.
Associated module ids are seeded from the modules currently present in the
experiment graph and remain editable.

A compact read-only notebook summary may be supplied to the local assistant so
it can help plan follow-up work. The assistant is explicitly told that notebook
status is planning context, not proof or verification evidence.


## Proposed Experiment → Build on Canvas

A Research Idea can propose a small experiment graph from its editable
`associated_modules` list.

The workflow is explicitly two-phase:

1. **Propose / preview**
   - resolve at most eight unique associated module ids through the local module registry;
   - skip and report unknown module ids;
   - order nodes deterministically from the notebook list;
   - connect only earlier outputs to later inputs;
   - use CACE's canonical `port_connection_error` contract for exact
     type/unit compatibility;
   - report every unresolved required input;
   - display the idea's Proposed Experiment text, nodes, compatible edges,
     unresolved inputs, and skipped modules in a read-only preview dialog.

2. **Explicit approval / build**
   - Cancel performs no experiment mutation;
   - Approve & Build materializes the proposal into a copied `Experiment`;
   - proposal-local node ids are translated to fresh experiment node ids;
   - the entire approved proposal is installed as one undoable edit;
   - stale run evidence is detached through the existing graph-restore path;
   - autosave runs after the approved build;
   - an unexpected restore failure rolls the edit back to the pre-build
     experiment snapshot.

A proposal with unresolved required inputs is visibly labeled **Partial** and
uses an **Approve Partial & Build** action. CACE does not invent values,
implicit conversions, hidden adapters, or hidden execution dependencies to make
a partial graph appear runnable.

Building an experiment does **not** automatically advance the Research Idea
status. The user remains responsible for deciding when an idea moves from Idea
to Testable, Experimented, Promising, or Proof Candidate.

The proposal engine and materializer are pure/testable layers outside the GUI.
They do not import or mutate proof ledgers, claim registries, formal
qualification state, certificates, or verification results.


## Minimal / Balanced / Exploratory proposal strategies

The **Build on Canvas** preview presents three independently generated,
read-only proposals before approval.

### Minimal — lowest compute

Minimal searches associated-module subsets up to size three and prefers the
smallest useful compatibility-checked graph. It prioritizes:

1. a useful compatible connection or a standalone execution-ready source;
2. execution readiness;
3. more valid compatible edges;
4. fewer unresolved required inputs; and
5. fewer nodes.

Minimal is intended for the cheapest falsifiable experiment, not maximum
coverage.

### Balanced — best connected

Balanced keeps the bounded associated-module set but reorders it
deterministically. At each step it prefers modules whose inputs can already be
satisfied by placed outputs, then source-like modules, then modules that retain
downstream producer value.

All actual edges are still produced only by CACE's canonical exact type/unit
compatibility contract. Balanced does not infer hidden semantic conversions.

### Exploratory — bounded novelty

Exploratory starts from Balanced and may add at most two locally registered
modules not already associated with the idea.

Candidate extras are derived from the Grow-seeded Research Idea text: title,
notes, hypotheses, and Proposed Experiment. Ranking rewards:

- lexical/metadata overlap with that idea context;
- a compatible interface with the current proposed modules;
- category diversity; and
- a bounded amount of useful module interface structure.

Connected idea-relevant novelty is preferred. If none exists, Exploratory may
include at most one strongly idea-relevant disconnected concept; the preview
must expose its unresolved state rather than pretending the graph is runnable.

After bounded expansion, the combined module set is re-balanced before edge
generation. Exploratory therefore remains acyclic, local, deterministic, and
subject to exactly the same type/unit checks as Minimal and Balanced.

### Strategy preview and approval

The proposal dialog shows summary metrics for all three strategies:

- node count;
- compatible edge count;
- unresolved required input count; and
- ready / partial / empty status.

The user can switch strategies repeatedly with no experiment mutation. The
visual graph, rationale, Proposed Experiment text, unresolved inputs, and
skipped modules update to match the selected strategy.

Only the strategy selected when **Approve & Build** is pressed is materialized.
Cancel leaves the experiment unchanged. Approval remains one undoable,
autosaved edit and does not auto-advance Research Idea status.


## Compare proposal strategy results

The multi-strategy proposal preview can run a non-destructive **Compare Ready
Strategies** evaluation before the user builds anything on the canvas.

Comparison semantics:

- Minimal, Balanced, and Exploratory are materialized into separate temporary
  `Experiment` objects;
- the user's current canvas experiment is never used as the comparison target
  and is not mutated;
- every runnable temporary experiment receives the same explicit seed;
- the current GPU policy is reused consistently across strategies;
- proposal-local ids (`p1`, `p2`, …) are translated only inside each
  temporary experiment;
- unresolved required inputs make a strategy **not runnable** unless explicit
  comparison inputs provide every missing required port;
- no missing input value, type conversion, or unit conversion is guessed.

The results dialog reports each strategy independently:

- runnable / not runnable;
- completed / interrupted;
- node and edge counts;
- unresolved required input count;
- one local wall-clock runtime sample;
- verifier PASS / FAIL / NOT-RUN counts;
- the existing `all_verifiers_passed` property without reinterpretation;
- compact per-node output summaries and SHA-256 output fingerprints;
- temporary experiment semantic/full SHA-256 fingerprints;
- modules unique relative to the common strategy core; and
- a descriptive structural novelty fraction.

Runtime is explicitly labeled as one local wall-clock sample, not a benchmark
verdict. Structural novelty is descriptive, not evidence that a strategy is
scientifically better.

The comparison object intentionally has no `winner`, `best_strategy`, or
automatic recommendation field. The user can select a row only to return that
strategy to the proposal preview for further inspection. **Approve & Build**
remains a separate explicit action.

Comparison work runs on a GUI worker thread. Failure returns an error message
to the preview and leaves the canvas unchanged.

The current UI compares execution-ready proposals using their graph-generated
inputs and one shared seed. The comparison engine also supports explicit
per-strategy inputs keyed by proposal-local node ids for future workflows; such
inputs can make an otherwise partial proposal runnable only when every missing
required port is supplied.


## Qualification-neutral AI preference boundary

Grow-specific preferences (Generally Useful mode, local embedding model, chaos,
combination budget, and maximum group size) live in
`cace_studio.ai.preferences.AIResearchPreferences`, persisted separately from
`cace_studio.core.settings.StudioSettings`.

This separation is intentional: changing experimental AI/UI preferences must
not modify the formally qualified core settings surface or require a fresh
formal attestation.

Likewise, transform animation remains opt-in by duck typing at the GUI boundary.
The qualified `cace_studio.core.module.Module` base class is unchanged; a
research module may expose an `animation_payload` method, and the GUI calls it
only when present. Animation remains evidence-neutral presentation state.
