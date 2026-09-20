# CACE Math-Guided Neural Efficiency Roadmap

Status: research roadmap. No performance claim is implied until benchmarked.

Goal: make the local CACE neural/LLM research assistant more efficient and more
transferable by giving it mathematically structured state and reusable exact
operators.

## Ranked implementation ideas

1. **Symmetry canonicalization and finite-group actions**
   Collapse symmetry-equivalent states before planning or retrieval. Measure
   search-state count, tokens, latency and task accuracy against a no-
   canonicalization baseline.

2. **Typed executable ReasoningOperator programs**
   Train/select short checked operation programs instead of regenerating long
   free-form reasoning for transformations CACE already knows how to execute.

3. **Equivariant neural layers where the domain actually has a declared group**
   Use E(n)/SE(n)/permutation-equivariant architectures only where the physical
   or mathematical symmetry is explicit; test against ordinary baselines.

4. **Sparse geometric/exterior representations**
   Use blades, grades, incidence and sparse k-cell structure when they compress
   geometry better than dense coordinates.

5. **Curriculum over generators and compositions**
   Learn primitive operations first, then 2-, 3-, and n-operation compositions;
   hold out entire compositions to measure transfer rather than memorization.

6. **Invariant/equivariance contrastive objectives**
   Pull equivalent states together and push causally different states apart,
   with exact group actions generating controlled positive/negative pairs.

7. **Canonical-state caching and orbit reuse**
   Cache model/tool results by exact canonical representative and transport them
   through checked actions instead of recomputing every equivalent case.

8. **Typed graph/mesh message passing**
   Let neural components consume CACE module graphs, mesh incidence and semantic
   port types directly, preserving locality and sparsity.

9. **Low-rank/spectral/subspace compression**
   Detect reusable subspaces/eigenspaces or low-rank structure and feed compact
   representations to the model when reconstruction/error checks justify it.

10. **Verifier-guided distillation**
    Distill successful exact/certified operator traces into a smaller local
    specialist model, while keeping the verifier external and authoritative.

## Evaluation suite

Every claimed optimization should report at least:

- correctness;
- paired intervention consistency;
- invariance/equivariance score;
- composition-holdout accuracy;
- search states explored;
- operator steps;
- tokens/context used;
- latency;
- peak memory;
- compute/energy proxy where available;
- verifier closure rate.

A technique is retained only if it improves a useful metric without materially
damaging correctness, transfer, or evidence integrity.
