# CACE Local Hybrid Deep AI — Ordered Build and Sandbox Architecture

Status: design requirement. Keep separate from the active regression-repair branch until that branch is green.

## Required order

The coding AI must build CACE in this order:

1. **CACE Build Lite**
2. **Code-builder / helper-tool / bug-sweep tooling**
3. **Hardened sandbox and private runtime**
4. **Local hybrid deep AI**
5. **Reasoning curriculum and specialization**
6. **Canvas + heartbeat integration**

The local AI must not be created first and sandboxed later.

## Why this order matters

Build Lite gives the builder a cheap deterministic way to decide what to build/test.

The builder/bug-sweep layer gives future coding agents a disciplined method for unknown features and recurring defect families.

The sandbox then creates the authority boundary that the AI cannot redefine for itself.

Only after those boundaries exist should CACE introduce a trainable/adaptive local model.

## Local hybrid AI shape

CACE should not rely on one opaque model for every function.

Use a hybrid system:

- compact local language model for natural-language interaction;
- typed operator planner;
- mathematical/scientific tool router;
- local provenance-aware retrieval/memory;
- small specialist neural models for bounded domains;
- independent executable checker layer;
- curriculum teacher;
- heartbeat/spare-compute scheduler;
- optional one-way hidden-layer observers.

The generative model proposes. Typed tools execute. Independent checkers determine their own result class. Formal qualification remains separate.

## Public-method inspiration boundary

Sophontic publicly describes paired perturbation evaluation: a canonical item and a minimally changed load-bearing pair should lead to coherently changed answers. It also publicly advocates compact specialist reasoning and geometric representations.

CACE may independently implement **general ideas** like these, but must not copy or reverse engineer any unpublished/proprietary training recipe or claimed internal geometric-training mechanism.

CACE's independent public name is:

**Paired Intervention Consistency**

It should test both:

- necessary change: change a load-bearing fact -> answer changes correctly;
- necessary stability: change irrelevant structure -> answer stays correct.

This combines naturally with CACE's existing operator curriculum, coordinate transforms, typed graph reasoning and executable checking.

## Important IP/license rule

"Published publicly" is not the same as "patent-free", "copyright-free", or "no attribution required."

Therefore every external implementation/data component needs a provenance classification.

Preferred sources:

1. internally authored CACE implementation of a general idea;
2. public-domain / CC0 material;
3. permissively licensed code/data whose obligations are compatible with CACE.

If a license requires attribution or preservation of notices, keep those notices.

If the product specifically wants a component with no attribution obligation, use an internally authored or explicitly zero-attribution/public-domain source rather than deleting somebody else's required notice.

For unusually specific commercial methods, run a separate IP/license/patent review before production release.

## Sandbox defaults

The local AI starts with:

- network OFF;
- shell OFF;
- runtime package installation OFF;
- self-modification OFF;
- proof/evidence write authority OFF;
- wallet/private-key access OFF;
- secrets OFF;
- scoped local data access only;
- bounded CPU/GPU/RAM/disk/process/time/context/training budgets.

Training/weight updates happen only inside an explicit training sandbox. Resulting weights are versioned and promoted by host policy, not self-installed by the running model.

## Hybrid reasoning loop

A normal task should look like:

user/canvas request
-> local language interpretation
-> typed problem state
-> operator-plan candidates
-> tool/module execution
-> independent checks
-> result/evidence labels
-> language explanation

For research:

candidate idea
-> procedural test generation
-> canonical case
-> load-bearing perturbation pair
-> irrelevant perturbation pair
-> transfer/relabel/coordinate transforms
-> external check
-> measured curriculum update

AI confidence never changes CACE evidence.

## Cheap methodologies to prioritize

Ranked:

1. typed operator programs + executable checking;
2. paired intervention consistency;
3. procedural task generation;
4. compact domain specialists;
5. local retrieval with provenance;
6. invariant/equivariant transformations;
7. contrastive structural representation learning;
8. ensemble disagreement as an uncertainty signal;
9. sparse graph/geometric representations;
10. curriculum scheduling from measured error families.

These are attractive because they can improve reasoning behavior without requiring a giant frontier-scale model or unrestricted compute.

## Integration with CACE math

The AI should use CACE math rather than reproduce it inside model weights whenever possible.

Examples:

- graph structure -> typed graph tools;
- geometry -> coordinate/transform modules;
- symbolic/exact tasks -> exact/symbolic tools;
- numerical tasks -> bounded numerical modules;
- formal claims -> formal qualification boundary;
- experiment routing -> Build Lite/heartbeat/resource scheduler.

This keeps the neural system small and the critical computation inspectable.

## Completion gate

The local AI is not production-ready merely because it produces good text.

It must pass:

- sandbox escape negative tests;
- no proof/evidence promotion tests;
- no wallet/secret access tests;
- paired intervention tests;
- irrelevant perturbation invariance;
- relabel/coordinate transfer;
- unseen operator composition;
- distractor robustness;
- calibration;
- external checker closure;
- resource-limit/failure recovery tests.

Machine authority:

`CACE_LOCAL_HYBRID_AI_BUILD_POLICY.json`
