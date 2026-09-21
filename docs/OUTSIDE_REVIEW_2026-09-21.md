# Outside Review — 2026-09-21

Status: outside engineering review by an AI collaborator (Sui). This is **not** proof
evidence, carries no lease, and binds to no qualified head. It is an opinion offered
for the maintainer to accept, reject, or supersede. Nothing here changes a claim's
evidence class.

Scope read: repository top layer, `collaboration/PROTOCOL.md`, `schema/claim.schema.json`,
`docs/CONSTITUTION.md`, `docs/CLAIMS.md`, `docs/EVIDENCE_LEDGER.md`,
`docs/PORTABLE_QUALIFICATION.md`, `docs/TOOLCHAIN_LOCK.json` (if present at this head),
and the workflow definitions for the active jobs. I did not read all files, and I did
not execute a qualification run.

## What holds up

The evidence-class separation is real, not decoration. Four classes with a one-way
ratchet (`AI_PROPOSAL` -> `ENGINEERING_VERIFIED` -> `CERTIFIED_NUMERICAL` -> `PROVED`),
where prose and model consensus can never set `PROVED`, is the thing most projects
fake the moment a deadline arrives. Here it is written down as a rule and enforced in
`claim.schema.json`.

`NOT_RUN` is never `PASS`. The conditional in `claim.schema.json` requires
`qualification.status == "PASS"` plus an attested 40-hex commit and a 64-hex proof
artifact digest before the ceiling can rise to `formally-verified` or `cross-verified`.
That is the correct shape.

Best line in the repo: `liveness != progress != verification`. A number without a
named way to die is a mood, not evidence. The protocol says this in different words;
keep it.

SHA-256 is used for identity/integrity only, and the protocol explicitly forbids
promoting a digest to semantic or mathematical correctness. Correct and rare.

## Seams worth pushing on

**1. Toolchain closure is pinned, not locked.**
`TOOLCHAIN_LOCK.json` reports `lake_manifest_status: NOT_GENERATED` (elan unreachable
when it was written). Lean version and mathlib commit are pinned, but with no generated
`lake-manifest.json` the dependency closure is not transitively locked. So the honest
claim is "runner-independent *if the closure resolves the same*", not "runner-independent".
That is the gap between the claim and the mechanism. Generating the manifest once and
hashing it closes it.

**2. The 800-file context cap is policy, not mechanism.**
Right now it leans on the builder reporting honestly. Hash the shard manifest and fail
the run when the set drifts, and it becomes enforceable rather than aspirational.

**3. One runner is one failure point.**
All active workflows sit on `[self-hosted, cace, oci, aarch64]`. That is a single point
of failure for the whole qualification story. The portable qualifier is the right hedge;
keep it funded and keep it tested against the same head.

**4. A claim can be registered with no named falsifier.**
`schema/claim.schema.json` requires `statement`, `scope`, and `evidence_ceiling`, but
`nonclaims` is optional and there is no required field naming what would make the claim
false. A registry can therefore fill with claims that are not falsifiable in principle.
This review ships a companion schema, `collaboration/schema/cace-kill-rule.schema.json`,
which binds one pre-registered falsifier to each claim before its outcome exists.

## What I did not verify

- I did not run a qualification job, and I did not check that any claim's
  `proof_artifact_sha256` resolves to a real artifact at this head.
- I did not audit the C++ kernels or the Lean proofs for soundness.
- I did not confirm the runner's actual hardware or network posture.

Treat every line above as an AI proposal, evidence class `AI_PROPOSAL`.
