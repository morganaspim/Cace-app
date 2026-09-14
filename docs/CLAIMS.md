# CACE claim registry and proof ledger

CACE treats scientific claims as versioned data rather than prose scattered through modules.

## Canonical runtime data

- `cace_studio/data/claim_registry.json` defines claim IDs, module bindings, scope, evidence ceilings, qualification state, and explicit nonclaims.
- `cace_studio/data/proof_ledger.json` records the proof/release qualification that supports each claim.
- `schema/claim.schema.json` and `schema/proof-ledger.schema.json` define the machine-readable formats.
- `cace_studio/core/formal_gate.py` enforces the runtime rule.

The policy is **fail closed**. A verifier that returns `EvidenceKind.FORMAL` with state `PASS` is not enough by itself. The executor preserves that `PASS` only when:

1. the module is bound to exactly one canonical claim;
2. the claim is marked qualified for the current source state;
3. the proof ledger has a matching qualified entry;
4. the claim and proof ledger agree on the attested Git commit; and
5. the claim and proof ledger agree on a 64-hex SHA-256 proof artifact digest.

Otherwise the record is downgraded to `NOT_RUN`. Numerical, symbolic, interval, failed, and already-`NOT_RUN` records are not upgraded by this gate.

## Current status

The v3.22 fixed rational square-with-center P1/constant-RT0-error certificate has a historical successful GitHub Actions baseline at commit `a69dd2bd83082baa20106eabb8baab30eb49302a`, run `34806285322`. That historical success is deliberately **not** treated as a current-head formal qualification.

The v3.23-v3.30 continuum proof-strengthening chain is tracked as not currently qualified until a pinned current-head Lean build, axiom audit, exact commit binding, and content-addressed proof artifact are accepted into the registry/ledger.

This means the registry can honestly preserve historical proof facts while refusing to imply that later source revisions have inherited them.

## Updating a formal qualification

A release qualification should update the claim registry and proof ledger only after the same commit has passed the required formal workflow. The recorded proof artifact digest must be produced from the exact attestation/proof bundle that the release intends to cite.

A code change must never flip `current_head_qualified` to `true` merely to make a test pass.

## Scope versus software maturity

Formal qualification of a theorem does not imply the Python/C++ application is production-grade. Software maturity, numerical validation, packaging, security, and formal theorem evidence remain separate dimensions.
