# Portable formal qualification

CACE formal qualification must not depend on one CI vendor or one runner machine.
The canonical evidence requirement is therefore:

`exact commit + named qualification system + unique run id + pinned dependencies + successful audited build + axiom audit + content-addressed attestation`

GitHub Actions is one possible qualification system, not the definition of formal evidence.

## One-command Linux / WSL qualification

From a **clean checkout** of the exact commit to be qualified:

```sh
bash scripts/qualify_v330_portable.sh
```

The script:

1. refuses a dirty working tree;
2. creates an isolated temporary Python/Lean environment;
3. runs the v3.30/v3.31 fail-closed claim-governance tests;
4. installs the pinned Lean toolchain from `formal/cace_formal/lean-toolchain`;
5. resolves Mathlib and requires commit `520045ab14e26149ee970e2e617ca04b09bde5d6`;
6. downloads only the transitive cache closure of `CACEFormal/V330AxiomAudit.lean`;
7. rejects `sorry`, `admit`, and `OPEN OBLIGATION` tokens in the audited source set;
8. builds `CACEFormal.V330AxiomAudit`;
9. runs Lean's endpoint axiom reports and rejects `sorryAx` or non-whitelisted axioms;
10. writes an exact-commit qualification attestation and SHA-256 digest.

Default artifacts are written outside the repository under:

```text
~/.cace/qualification/<qualification-run-id>/
```

Set `CACE_QUALIFICATION_OUTPUT` to choose another external artifact directory.
Set `CACE_QUALIFICATION_RUN_ID` to a unique stable run identifier when another system supplies one.
Set `CACE_QUALIFICATION_SYSTEM` to identify that system, for example `portable-local`, `docker`, or an approved external CI service.

## Requirements

The portable shell driver currently targets Linux and WSL and requires:

- `git`
- `curl`
- `python3` with `venv`
- `grep`
- GNU `timeout`
- network access to the official Lean/Mathlib sources and cache

The project can later wrap this command in Docker, GitHub Actions, another CI service, or a local GUI action without changing its mathematical meaning.

## Qualification provenance model

A current-head proof-ledger entry requires:

- `status = PASS`;
- `current_head_qualified = true`;
- exact 40-hex Git commit;
- exact 64-hex proof-attestation digest;
- non-empty `qualification_system`;
- non-empty `qualification_run_id`;
- at least one recorded qualification check;
- zero blockers.

`workflow_run_id` is optional metadata unless `qualification_system` is `github-actions`, in which case a positive GitHub run id is also required.

Historical ledger entries containing only a GitHub `workflow_run_id` remain readable through a backwards-compatibility mapping to generic qualification provenance.

## Evidence boundary

A successful portable qualification establishes only the exact Lean theorem scope and hypotheses recorded by the attestation. It does **not**:

- prove all Python/C++ program behavior;
- turn numerical evidence into a continuum theorem;
- discharge explicitly conditional H1/H(div) regularization assumptions;
- establish external reviewer/reproducer independence;
- establish production readiness.

The canonical claim registry and proof ledger remain fail-closed until the resulting artifact digest and exact qualified commit are reviewed and deliberately accepted.
