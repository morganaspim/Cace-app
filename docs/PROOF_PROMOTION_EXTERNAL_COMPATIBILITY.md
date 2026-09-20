# Proof Promotion Compatibility with Gemini and Base44

Status: interface compatibility policy. Not proof evidence.

## Invariant

**CACE may strengthen, requalify, and canonically promote proofs without breaking Gemini or Base44.**

Internal proof machinery remains behind Oracle/CACE. External builders consume stable/versioned projections only.

## Gemini

Gemini may display CACE claim/evidence/qualification data through typed API projections.

Gemini must not depend on:

- Lean source paths;
- proof-ledger structure;
- canonical proof artifact SHA values;
- exact qualification run IDs;
- a fixed claim-ID list.

Unknown additive fields must be ignored safely. Unknown proof/evidence states must never be interpreted as PASS or FORMAL.

## Base44

Base44 mirrors only low-volume order/commercial status supplied by CACE, including `PROOF_READY_FOR_SALE` after CACE establishes it.

Base44 never inspects Lean, proof ledgers, claim registries, proof artifacts, or qualification jobs.

## Breaking changes

A genuinely breaking external proof/evidence interface change requires a new explicit API/schema version, migration notes, compatibility tests, and user/ChatGPT review.

Internal canonical proof promotion itself is not a breaking external change.
