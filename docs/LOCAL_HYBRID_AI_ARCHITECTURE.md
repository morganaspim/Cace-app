# CACE Local Hybrid Deep AI — Architecture

Branch: `feature/local-hybrid-ai`

## Goal

Build a local, sandboxed research assistant that gets cheaper and more useful as CACE accumulates
proofs and experiments.  The AI may rank, suggest, combine, summarize, and propose experiments, but
it never promotes a mathematical claim to formal evidence.  Lean remains the proof trust boundary.

## Zero-contact runtime

Normal AI execution is offline.

- no cloud inference;
- no browser/network tools;
- optional LLM endpoint must resolve syntactically to loopback only
  (`127.0.0.1`, `::1`, or `localhost`);
- model files stay outside the repository and are user-selected;
- proof artifacts are read-only inputs to the AI;
- AI output is advisory/experimental evidence only.

A local `llama.cpp` server is the first optional LLM backend.  The mathematical planner and neural
ranker do not require it.

## Hybrid stack

```
                 +----------------------+
task/context --->| cheap feature sketch |----+
                 +----------------------+    |
                                               v
proof memory ---> hashed retrieval --------> fusion ------+
                                                          |
module atoms ---> combinatorial beam planner ------------+--> ranked combinations
                                                          |
success/cost ---> tiny residual neural ranker ------------+
                                                          |
local LLM (optional, loopback only) <---------------------+
        |
        +--> explanation / experiment suggestions / code-plan prose
```

## Cheap mathematical primitives

1. **Signed hash / CountSketch features**
   - O(number of tokens/features)
   - fixed memory
   - deterministic from seed
   - avoids a heavyweight embedding model for first-pass retrieval.

2. **Fast Walsh-Hadamard transform**
   - O(d log d)
   - optional mixing of dense feature vectors
   - multiplication-free except normalization/sign operations.

3. **Random sign projection**
   - compact task/candidate fingerprints
   - deterministic, cacheable, inexpensive.

4. **Normalized additive group features**
   - a combination starts from the normalized sum of its member sketches.

5. **Pair-interaction sketch**
   - elementwise low-dimensional interactions capture synergy without a quadratic full tensor.

6. **Diversity penalty**
   - cosine similarity discourages the beam from returning near-duplicate combinations.

7. **Cost-aware score**
   - predicted utility - compute penalty + proof-success prior + novelty/diversity.

8. **Beam search over combinations**
   - avoids enumerating every n-choose-k group;
   - supports 2+, 3+, ... group search with bounded width.

9. **Online residual neural ranker**
   - small NumPy MLP;
   - learns from accepted/rejected suggestions and proof/experiment outcomes;
   - no GPU or ML framework required;
   - can later be exported/replaced by ONNX without changing the planner contract.

## Learning loop

Every completed experiment/proof attempt can append an experience:

```
(task sketch, candidate sketch, outcome, verified level, cost, timestamp)
```

The ranker learns only from explicit outcomes.  Formal proof success can receive a stronger target
weight than numerical/experimental success, but the model itself remains non-formal.

As the experience store grows:

- nearest prior tasks seed the candidate prior;
- repeated losing combinations are pruned earlier;
- repeated useful subgroups receive a cached prior;
- the beam width can shrink when confidence is high;
- expensive LLM calls are reserved for ambiguous top candidates.

## Evidence firewall

AI suggestion -> EXPERIMENTAL

numerical test -> NUMERICAL

symbolic/interval verifier -> corresponding evidence

Lean kernel qualification -> FORMAL

The AI cannot directly cross these boundaries.

## Implementation stages

1. Pure-Python/NumPy mathematical feature sketch.
2. Tiny residual neural ranker with online updates.
3. Cost/diversity-aware combinatorial beam planner.
4. SQLite proof/experiment experience memory.
5. Loopback-only local LLM adapter.
6. Hybrid engine joining planner + memory + ranker + LLM.
7. CACE module/GUI adapter.
8. Proof-aware training events and theorem/module metadata features.
9. Optional optimized backends:
   - llama.cpp quantized GGUF for language model;
   - ONNX Runtime quantized small ranker/embedding model;
   - C++ kernels for sketches/Hadamard/combination scoring if profiling justifies them.

## Performance policy

No speed claim is accepted from architecture alone.  Benchmark separately:

- candidates evaluated/sec;
- planner latency vs exhaustive combinations;
- memory retrieval latency;
- ranker inference/update latency;
- task success@k;
- proof-success@k;
- LLM calls avoided;
- wall-clock compute per accepted suggestion.
