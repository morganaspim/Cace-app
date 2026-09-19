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
