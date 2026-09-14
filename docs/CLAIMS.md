# CACE claim registry and proof ledger

CACE treats scientific claims as versioned data rather than prose scattered through modules.

## Canonical runtime data

- `cace_studio/data/claim_registry.json` defines claim IDs, module bindings, scope, evidence ceilings, qualification state, and explicit nonclaims.
- `cace_studio/data/proof_ledger.json` records the proof/release qualification that supports each claim.
- `schema/claim.schema.json` and `schema/proof-ledger.schema.json` define the machine-readable formats.
- `cace_studio/core/formal_gate.py` enforces the runtime promotion rule.
- `cace_studio/core/qualification_drift.py` enforces inheritance of a qualification across later commits only when no qualification-sensitive source has changed.
- `scripts/check_qualification_drift.py` is the CI/local qualification-drift gate.

The policy is **fail closed**. A verifier that returns `EvidenceKind.FORMAL` with state `PASS` is not enough by itself. The executor preserves that `PASS` only when:

1. the module is bound to exactly one canonical claim;
2. the claim has `status=PASS`, an evidence ceiling of at least formally verified, and a qualified source state;
3. the proof ledger has a matching `PASS` entry with no blockers;
4. the claim and proof ledger agree on the attested Git commit;
5. the claim and proof ledger agree on a 64-hex SHA-256 proof artifact digest;
6. the proof ledger records a positive GitHub Actions workflow run ID and explicit qualification checks; and
7. CI confirms that the current checkout has not changed any qualification-sensitive path since the attested commit.

Otherwise the record is downgraded to `NOT_RUN`. Numerical, symbolic, interval, failed, and already-`NOT_RUN` records are not upgraded by this gate.

## Qualification-sensitive source

Formal qualification is attached to the proof-sensitive source state rather than to unrelated documentation or GUI changes. The drift guard treats the following as qualification-sensitive:

- `formal/**`;
- `cace_studio/core/**`;
- formal module implementations and module registration;
- `cace_studio/app.py`;
- the claim/proof schemas;
- the formal qualification tests and drift checker;
- `pyproject.toml`; and
- the v3.30 formal workflow itself.

The two canonical provenance files, `cace_studio/data/claim_registry.json` and `cace_studio/data/proof_ledger.json`, are intentionally allowed to change after a successful attestation so that the attestation can be accepted into the ledger without creating a circular commit/hash requirement. The Python regression workflow must then run the drift audit. If any qualification-sensitive file changed after the attested commit, the inherited qualification fails and a fresh formal attestation is required.

This policy also prevents later source revisions from silently inheriting a stale formal `PASS`.

## Current status

The v3.22 fixed rational square-with-center P1/constant-RT0-error certificate has a historical successful GitHub Actions baseline at commit `a69dd2bd83082baa20106eabb8baab30eb49302a`, run `34806285322`. That historical success is deliberately **not** treated as a current qualification.

The v3.23-v3.30 continuum proof-strengthening chain remains unqualified until a pinned self-hosted Lean build, axiom audit, exact attested commit, workflow provenance, and content-addressed proof attestation are accepted into the registry/ledger.

## Updating a formal qualification

A release qualification should be accepted only after the qualification-sensitive source commit has passed the required formal workflow. The recorded proof artifact digest must be produced from the exact attestation that the release intends to cite.

Promotion of the two provenance JSON files may occur in a descendant commit after the successful attested commit. That descendant is eligible only when `scripts/check_qualification_drift.py` proves that all intervening changes are qualification-insensitive. Any qualification-sensitive change requires a fresh formal workflow run and a new proof artifact.

A code change must never flip `current_head_qualified` to `true` merely to make a test pass.

## Scope versus software maturity

Formal qualification of a theorem does not imply the Python/C++ application is production-grade. Software maturity, numerical validation, packaging, security, and formal theorem evidence remain separate dimensions.
