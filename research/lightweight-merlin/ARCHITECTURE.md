# Lightweight connected Merlin: architecture decision proposal

Date: 2026-11-19. Status: RESEARCH / DRAFT, not deployed or qualified.

## Decision and objective

Use a thin device interface plus an optional local companion, one cloud coordinator reusing Merlin's canonical stores, and separately bounded specialist workers. Prefer independent task distribution over splitting every generated token across intermittently connected devices. Small resident quantized models are optional assistants; no model is required to run deterministic tools, retrieve evidence, or verify a proof. Large streamed models and device meshes are opt-in experimental backends, not the default interactive path.

This is the best-supported baseline to test under the observed resource constraints, not a universal optimum. Measure quality, first-token latency, end-to-end latency, peak RAM/VRAM, storage, energy, failure recovery and total cost on actual devices before selecting a production engine. Memory feasibility alone is not performance evidence.

## Observed cloud state, not assumed capacity

The existing OCI instance was already running. No wake, restart, service deployment, model installation, cache deletion or paid provider invocation was performed.

* Inventory run [44587555030](https://github.com/morganaspim/Cace-app/actions/runs/44587555030): cace-oci-a1, ARM64, two CPUs, 11,427,774,464 bytes total RAM, 104,579,764,224 bytes free on the observed filesystem. Total RAM is not free RAM or a lease. No accelerator was established by this probe.
* Read-only MCP run [44589627595](https://github.com/morganaspim/Cace-app/actions/runs/44589627595): CACE Studio cace-web active, HTTP health 200; loopback MCP responded. Generic shell, restart, IAM, secrets and network writes were not enabled.
* Private Merlin inspection [44589955769](https://github.com/morganaspim/Cace-app/actions/runs/44589955769): the existing Unix-socket service was active; health, context status, research contract, mathematical-lenses demo, research-episode demo and ideal virtual-circuit demo worked. A job_submit call was correctly denied. The context store contained TWO explicitly ingested synthetic records, not all private project context. General job execution was unavailable; Hermes was draft_only; live Drive sync and independent CACE verification were not configured; RSI promotion was unavailable.

A running CACE Studio webpage is not proof that every Merlin lab is integrated. The research demos are fixed fixtures, not an autonomous model researching this architecture. The architecture reasoning was performed in this conversation; its deterministic experiments ran on OCI through an exact-source research workflow.

## Proposed components and reuse boundaries

```text
Phone / browser / tablet ---- authenticated project-scoped interface ----+
Laptop companion ----------- resumable tasks and immutable references ----+--> Merlin coordinator
                                                                        |    canonical registry + graph
                                                                        |    Hermes outbox + leases
                                                                        |    protocol / review / plan history
                                                                        +--> bounded workers
                                                                             numerical and virtual labs
                                                                             Lean / Mathlib
                                                                             optional local/cloud inference
                                                                             retrieval and code tests
                                                                        +--> independent verification boundary
                                                                             separate identity and approval
```

### Device tier

The base interface displays evidence, progress, budgets, exact assumptions and pending approvals. An offline draft queue can preserve user work, but cannot declare a cloud task complete. A local companion may run bounded retrieval and allowlisted tools, optionally with a resident small model. Use one inference process per selected device rather than one model for every persona. Logical scientist, proposer and critic roles can run serially; shared weights are correlated reviewers, not independent validation.

Treat browser storage as an optional, revocable cache, not the sole durable research archive. Private context should remain on the device unless its project policy permits transfer. Browser code presents canonical results; it does not redefine CACE scientific or proof semantics. Keep long-lived credentials out of browser storage and model prompts. Device enrollment, authenticated transport, revoked-key behavior and actual offline recovery require tests before deployment.

### Cloud coordinator

Keep a modular monolith initially: existing canonical registry / ArtifactRef, knowledge graph, research protocol, Hermes outbox, task state and append-only plan references. Do not introduce a parallel evidence database or a second self-improvement ledger. A local SQLite writer is appropriate for an initial single-host queue; never put its live database on a shared network filesystem. Consider a managed multiwriter database only after measuring concurrency or availability requirements.

Run workers on demand, with one heavy job initially on the observed two-CPU instance and a fresh resource lease for every launch. The coordinator should not import the entire inference, CAD and proof toolchain at startup. Treat idle RSS <=512 MiB as an initial acceptance TARGET, not a measured property. Avoid an always-on microservice fleet or Kubernetes requirement for this small deployment.

### Worker and tool contract

A task binds project, authenticated principal, allowed tool/version, exact ArtifactRefs, input digest, budget, deadline, privacy class and requested evidence type. Capability records carry actual host observations, expiry, architecture, available memory/storage and isolation status. Admission must reject stale, future, simulated, mismatched, ungranted or over-budget capacity.

The existing host supervisor must enforce process-tree cancellation, cgroups/resource limits, filesystem/network restrictions, secret separation and concurrency leases. This episode's RLIMIT-protected fixed-source jobs are not a general multi-tenant sandbox. A model can propose a task; it cannot supply its own trusted capability or authorize execution.

Use the canonical outbox's at-least-once delivery and idempotency keys bound to the complete request. Preserve failed and timed-out results. Do not claim exactly-once external API calls. Cache keys must include source bytes, toolchain, model/adapter revision, parameters, tenant, precision, domain, observation and error metric. Lossy summaries may guide retrieval, but never replace proof source or numerical evidence.

### Studio, tools and labs

CACE Studio and the private Merlin endpoint remain different observed surfaces. The intended unified interface is a capability-and-evidence view over their typed adapters, not an unrestricted shell connecting everything. ChatGPT's GitHub/Drive authorization is not automatically an OCI credential. Future live source connectors need separately configured, project-scoped authorization.

Connect research retrieval, Ideonomy, Logos review, numerical labs, xenomath glyphs, virtual circuits, Titan/CAD and Lean through exact artifact contracts. Each adapter reports source identity, tool version, execution mode, result and limitations. Offline or missing tools remain visibly unavailable. A simulated circuit is not physical hardware; a technology simulator cannot contribute fictitious RAM, GPUs or energy to scheduler capacity.

## Upstream ideas to reuse, with limits

Sources were read on 2026-11-19; no upstream installation or model benchmark was performed.

| Upstream | Recommended role | Important boundary |
| --- | --- | --- |
| [llama.cpp](https://github.com/ggml-org/llama.cpp) | Portable optional local inference adapter using reviewed builds and model artifacts | Benchmark the actual CPU/GPU, context and model; portable does not mean every configuration is fast |
| [MLX-LM](https://github.com/ml-explore/mlx-lm) | Apple-silicon inference, quantization, prompt cache and separately evaluated low-rank adapters | Apple-specific route, not the OCI ARM Linux default; bound context/cache and review model licensing/code |
| [WebLLM](https://webllm.mlc.ai/docs/) | Optional WebGPU inference with worker-separated UI | Never require a weight download just to access Merlin; test browser memory, cancellation and lifecycle |
| [AirLLM](https://github.com/lyogavin/airllm) | Layer streaming and frozen-base/adaptor ideas for latency-tolerant experiments | Low GPU residency does not eliminate host RAM, disk, KV cache, loading or compute costs; current upstream also has training support |
| [FlexGen](https://arxiv.org/abs/2303.06865) | Strong offloading/batched-throughput comparison | Latency-insensitive batch results must not be presented as single-user interactive speed |
| [exo](https://github.com/exo-explore/exo) | Opt-in stable-LAN topology-aware model partitioning | Measure link bandwidth/latency and disconnect behavior; do not assume phone/WAN links behave like workstation interconnects |
| [GEPA](https://github.com/gepa-ai/gepa) | Reflection, text-parameter optimization and Pareto-aware parent selection | Reuse Merlin's existing pinned training-only parent selector; independent heldout admission remains separate |

The inspected Expert Robot LIGHTWEIGHT_RSI_RESEARCH.md already describes the narrow GEPA v0.1.4 utility integration, pinned to upstream 8b0ce6cd99a234f6b74daf37558a2ac0ce18f975. Do not replace it with an unreviewed latest dependency or pretend its synthetic tests establish model improvement.

## Analytical study and falsifiers

`study.py` and `test_study.py` are research fixtures, not a production router or verifier. Source commit: 214b529d77a60563980614cd6314ad753e76a240.

The 288 cases vary four TOY dense-model configurations, three weight precisions, three context lengths, two batch sizes and four ASSUMED storage bandwidths. They calculate weight residency, conventional grouped-query KV storage and a storage-transfer lower bound. They do not simulate model intelligence or execute inference. Case digest: a5a3b4c1568deb16cd6d35b3b3b7323ca5a603649382d241c9ab86f3a38cc34b.

For parameters P, weight precision q and overhead fraction o:

    weights = ceil(P*q/8*(1+o))
    KV = 2*layers*KV_heads*head_dimension*context*batch*KV_element_bytes
    decode_step_time >= spilled_weight_bytes / storage_bandwidth

The spill fraction refers to weights not retained above the storage boundary, NOT GPU residency. Full host-RAM caching can remove repeated disk traffic. Batching improves aggregate throughput, not automatically each sequence's token latency. Compute, prefill, activation/workspace storage, decompression and network costs are excluded, so this is a lower-bound screen, not a latency forecast.

Illustration: a dense 70B toy at four bits plus 10% overhead requires 38.5 GB of prepared weights. With 80 layers, eight KV heads, width128, 8192 context and FP16 KV, the cache is 2.5 GiB for batch1. If all prepared weights spill each decode step through an assumed 2 GB/s storage path, the IO lower bound is 19.25 seconds per next token per sequence, before compute. Retaining an original FP16 copy would bring this illustrative storage total to 178.5 GB. This is not an AirLLM benchmark and does not apply unchanged to MoE, different KV layouts or RAM-resident caches.

All 36 local tests passed and reproduced on OCI in run44591194275. All 288 cloud analytic results equal the local results. A second replay in run44591557934 again passed the same36 tests. Neither run executed a language model. Run44591194275's combined workflow failed because Lean could not create a thread; the analytical pass is not obscured by, or used to erase, that failure.

A routing fixture checks project/tool scope, fresh observed capacity, hard privacy/memory/deadline gates and rejects simulated resources. The RSI fixture rejects overlapping/reused heldout content, changed candidate bytes, simulated evidence, regressions, missing evaluator authentication and rollback mismatch. Even a valid fixture returns only ready_for_independent_review and never promotion. Statistical power, evaluator independence and truth of scores are not established by these checks.

Two actual schema defects were repaired: empty matching project names admitted a request, and malformed unhashable case values raised TypeError before validation. New tests first failed, then passed with the fix. Preserved failing outputs are in the downloadable episode bundle; no production incident is claimed.

## Lean and xenomath execution boundary

Use the existing pinned Lean4.32.1 / Mathlib520045ab14e26149ee970e2e617ca04b09bde5d6 cache without installs or replacement. Preserve exact source, declarations, axiom audits, positive infrastructure controls and false-statement rejection. No sorry/admit/custom proof escape may be accepted.

The 18 explicit xenomath candidates cover joint witnesses, the Dowker translation, threshold and subset monotonicity, surjective pullback, error composition, cover exclusion, simplex/corner bounds and polynomial dynamics. Their source SHA256 is c52626fa8e0752715152aee19bd2acf83d534b8013941c1b5e1bc8546037948a.

The first cloud attempt failed before proofs with thread creation under a3GiB virtual-memory cap. Lean4.32.1's runtime source specifies1GiB default thread stacks. The repair set16MiB stacks while leaving memory/time limits unchanged. The next run compiled a core `0=0` canary but both Mathlib-dependent files failed to read Lean/Structure.ir. Thus the xenomath candidates remain NOT COMPILED. The exact cause of the IR read failure (missing/inaccessible file versus constrained mapping) is not yet established. The strengthened negative gate does not confuse that infrastructure failure with rejection of a false theorem.

Do not loosen proof checks or silently install a different toolchain. Next diagnose only the exact missing dependency and compare narrow imports under the same budget. A successful future compile proves the declared statements under recorded axioms; it still will not prove the Python executor correct or supply independent CACE qualification.

## Lightweight RSI loop

    observed problem + immutable protocol
      -> literature / source-bound idea catalogue
      -> at most two training-only parent candidates
      -> bounded change and measured experiment
      -> adversarial / null / regression controls
      -> separately authenticated fresh-holdout evaluation
      -> review and explicit approval
      -> reversible canary deployment, then monitoring

Start with retrieval selection, prompts, tool selection, caching and scheduling before model fine-tuning. Weight adaptation is a later explicit data-license, privacy, cost and regression decision. Use small fresh evaluation batches with predeclared metrics, paired baseline comparisons and uncertainty; the required sample depends on effect size. Repeatedly selecting on the same holdout turns it into training feedback. Two agents using the same model are not independent verification.

The simulator may rank candidate architectures or generate test cases. It cannot move a candidate from simulated to measured, qualified or deployed. Numerical tests, formal statements, independent attestations and physical measurements remain distinct evidence classes.

## Integration sequence and acceptance gates

This proposal attaches to MERLIN-PRODUCTION-MASTER-20261117 v6, observed in Expert Robot584b948332b76596311d75133c0430d761e2f67a. It does not overwrite or adopt a new canonical master version.

1. P00/P04: one canonical ArtifactRef request, host-authenticated capability/lease, existing outbox, one real bounded worker and returned exact receipt. Test stale scope, tampering, crash/replay, cancellation and denied writes. Current fixture success is insufficient.
2. P05/P09: diagnose pinned Lean dependency access; compile the18 candidates with explicit assumptions, known false control and full axiom audit. Bind runtime inputs to theorem assumptions separately.
3. P07/P08: thin-device client plus one optional resident model adapter. Benchmark no-model, small local and approved cloud baselines on actual consented devices, including cold/warm context, battery, private data and disconnect recovery.
4. P03: reuse training-only GEPA selection; test one real, reversible optimization against a separately held fresh set, cost ceiling and rollback. Independent verifier remains blocked until legitimately configured.
5. P04/P08: evaluate streamed/batched and LAN-mesh routes only when baseline limitations justify them. Compare at matched quality, context, total storage and user-visible latency.

Simplex weights rank already eligible normalized cost vectors. N-ality records joint engine/device/model/task/privacy/verification compatibility. Continuum sensitivity sweeps keep bandwidth and context assumptions explicit. Fuzzy suitability is UI advice only. None may relax authorization, integrity or qualification gates.

Rollback is to keep all new code under research and leave the production services and parent PRs unchanged. No Avrea before December1; no automatic later dispatch. Before merging, review the narrow diff independently rather than bulk-merging the stacked ancestors.
