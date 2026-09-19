# CACE Heartbeat Compute Economy and High-Capability AI Controls

Status: research/engineering design. Non-evidentiary orchestration only.

Date: 2026-09-19

## 1. Economic Conway heartbeat

The existing Conway-inspired heartbeat becomes a resource game over internal compute credits.

Credits are non-transferable, non-monetary, not cryptocurrency, local to one CACE workspace/run, and incapable of changing verification/proof status.

A host-owned resource probe estimates bounded spare CPU headroom and optional GPU headroom. A versioned mint rule converts spare headroom into a small treasury budget per tick. No spare resource means no new exploratory credits.

Each canvas/research node may hold a capped wallet. A research task bid declares node/task ID, estimated credit cost, bounded compute class, policy utility/urgency, and optional deadline. The scheduler allocates only within the treasury and host quotas.

The AI may suggest tasks but cannot mint or reward credits. Optimization statistics come only from host/executor measurements such as actual completion, wall-clock/CPU/GPU cost, cache hits, or candidates pruned by an executed checker. AI text saying a task was useful has zero economic weight.

CACE may compare scheduling strategies using a bounded scoreboard over measured useful-work-per-credit and latency. Exploration is capped, and user-triggered or verification-critical jobs may preempt the research economy.

## 2. Superintelligence-class gate

The GUI exposes an experimental checkbox: Allow superintelligence-class AI.

Default: OFF.

This is a capability-admission gate, not a consciousness or intelligence detector. Provider/model integrations may declare a manifest tier: bounded, advanced, or superintelligence-class. When OFF, the last tier is rejected before inference.

When ON, that tier may be admitted, but network access, shell/host access, self-modification, worker spawning, code/plugin installation, evidence/proof mutation, and compute budget remain separate fail-closed controls.

No checkbox can mathematically guarantee that an arbitrary model is not superintelligent; CACE can reliably enforce only the capabilities, resources, and provider classifications under its control.

## 3. Immutable deep-layer matrix observation

For local/open inference engines that expose hidden activations, CACE can attach host-controlled observation taps.

Conceptual flow:

input -> layer 0 -> layer 1 -> ... -> output
                         |
                         +--> one-way broker --> observer A
                                          \--> observer B

For every selected layer/step, the host broker copies an activation matrix or bounded encoding.

Observers run as separate unprivileged containers/processes, have no network, receive no model credentials, expose no RPC/socket back to inference, use host-owned immutable configuration, use read-only runtime/weights where practical, and write content-addressed append-only observation artifacts.

The inference model receives no observer output during the same inference path.

Each record binds inference/run ID, model digest, layer index/name, token/step index, matrix shape/dtype, capture mode (full/sketch/hash-only), content hash, observer replica ID, and sequence.

Two or more observers can independently confirm the same brokered matrix digest.

Some providers such as ordinary text-only Ollama/OpenAI-compatible HTTP endpoints do not expose hidden layers. In that case CACE must display observer unavailable rather than pretending to capture internals.

Full all-layer matrices can be extremely large; full capture therefore requires an explicit disk/RAM budget. Otherwise deterministic sketches/hashes are used.

## 4. Open Problems integration

Open-problem nodes participate in the same heartbeat economy. Importing a problem costs nothing. Play raises research-interest. Candidate computational experiments can bid for spare credits. Formal/proof checks remain outside the game and retain their normal qualification gates.

As of 2026-09-19, the Millennium catalog represents Navier–Stokes as active-review because Clay announced an apparent settlement on 2026-09-11 while its official problem page still says Active and the prize process is not complete.

## 5. First implementation slice

1. deterministic ComputeCreditEconomy core;
2. host-measured strategy scoreboard;
3. GUI credit/heartbeat display hooks;
4. default-OFF high-capability gate in Studio settings/controls;
5. provider capability manifest API;
6. immutable MatrixObserver archive API;
7. two-replica no-network Docker example;
8. packaged Millennium catalog with active-review status;
9. Open Problems GUI dock, Import to Canvas and Play buttons;
10. regression tests for fail-closed authority boundaries.
