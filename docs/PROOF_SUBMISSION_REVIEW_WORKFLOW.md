# CACE Proof Submission, Review, and Enterprise Verification Workflow

Status: implementation/product governance. Not proof evidence.

## Purpose

CACE may collect proof ideas, proof sketches, formalization candidates, and customer-specific proof requests through the browser UI.

When Gemini AI Studio / Antigravity is enabled, Gemini may help structure and package those submissions for repository review.

The submission itself is never verification evidence.

## Core authority rule

> **UI submission -> Gemini packaging -> GitHub draft PR -> CACE rigor pipeline -> human/ChatGPT-guided review -> merge/qualification**

No earlier stage may create `PASS`, `VERIFIED`, `FORMAL`, theorem qualification, or proof-ledger promotion.

## Path A — research/community improvement submission

A user working in CACE may identify:

- a proof sketch;
- a missing lemma;
- a candidate theorem;
- a stronger assumption set;
- a counterexample;
- a reusable formalization;
- a runtime-to-formal bridge;
- a correction to an existing proof path.

The UI may provide:

**Submit Proof Candidate for CACE Review**

The submission packet should freeze:

- source workspace/canvas hash;
- theorem/proof goal;
- assumptions;
- user-authored notes;
- generated Lean draft if any;
- relevant experiment/run IDs;
- referenced CACE theorem/certificate IDs;
- Gemini-generated explanation/normalization if enabled;
- exact CACE commit/API/schema identities;
- submitter attribution/consent metadata.

### Gemini role

If enabled, Gemini may:

- normalize the submission into CACE's typed contribution format;
- create or improve a Lean proof draft;
- add tests/fixtures;
- prepare source-to-formal linkage notes;
- create a bounded repository patch;
- prepare a draft PR description.

Gemini may not:

- mark the candidate formally proved;
- alter proof-ledger truth;
- bypass kernel/axiom audits;
- weaken theorem hypotheses;
- replace unresolved obligations with `sorry`, axioms, unchecked assertions, or prose.

### GitHub handoff

The controlled submission service may create a dedicated branch such as:

`submission/proof/<submission-id>`

and open a **draft pull request**.

Immediately after the submission commit is created, the branch is treated as **FROZEN for general agents**. Further changes require explicit review/reactivation under `BRANCH_LIFECYCLE.json`.

The PR must run the normal applicable CACE pipeline:

1. source/static sanity;
2. unfinished-token rejection;
3. relevant Python/C++ tests;
4. source-to-formal linkage checks where applicable;
5. exact-pin Lean preflight;
6. axiom/kernel/theorem-metadata checks;
7. audited-root compile where required;
8. canonical exact-head qualification when promotion is intended;
9. provenance/drift checks;
10. proof-ledger/claim promotion only through the canonical gate.

### Operator alert

When the submission reaches a human-review gate, CACE should surface an operator attention item:

`PR_REVIEW_REQUIRED`

containing:

- submission ID;
- PR number/URL;
- exact head SHA;
- current CI/qualification state;
- unresolved obligations;
- whether proof-sensitive files changed;
- recommended next gate.

The expected operator workflow is:

**CACE alert -> ChatGPT review session -> inspect exact PR/head/checks -> user approves merge or requests changes.**

ChatGPT may help inspect and prepare the PR, but final repository merge remains an explicit user action unless the user explicitly instructs an available GitHub action to merge.

## Path B — Enterprise proof-package request

Enterprise users may select a result and choose:

**Request Full-Rigor Proof Package**

This creates a frozen customer proof request, not a sale.

The request binds:

- organization/user;
- canvas/workspace snapshot;
- exact inputs/data identifiers;
- assumptions;
- desired theorem/conclusion;
- current CACE source/version;
- proof-contract/version identity;
- customer-visible scope hash.

### Internal verification branch

CACE/Gemini may prepare an internal proof branch/PR for the frozen request.

The branch/PR is reviewed through the same CACE rigor pipeline as any other formal contribution.

The customer does not receive a completed-proof claim merely because:

- Gemini produced Lean;
- tests passed;
- a draft PR exists;
- a proof preflight passed.

### Human approval

When the internal proof PR reaches its human gate, CACE alerts the operator.

The operator may use ChatGPT to:

- inspect the PR;
- inspect exact-current-head CI;
- inspect Lean/kernel/axiom audit results;
- inspect source-to-formal binding;
- inspect proof/provenance artifacts;
- summarize unresolved obligations;
- prepare the merge/qualification decision.

Only after the qualified proof and deliverability review are green may the order become:

`PROOF_READY_FOR_SALE`

Then the existing enterprise sequence continues:

`qualified proof -> deliverability/IP review -> SOW -> signature -> payment/credit approval -> render already-qualified package -> disclosure review -> final artifact binding -> delivery`

This preserves the existing rule:

> **prove first, sell second**

## Submission states

Recommended states:

- `COLLECTED`
- `PACKAGED`
- `GITHUB_DRAFT`
- `CI_PREFLIGHT`
- `CHANGES_REQUIRED`
- `HUMAN_REVIEW_REQUIRED`
- `QUALIFICATION_PENDING`
- `QUALIFIED`
- `REJECTED`
- `WITHDRAWN`

Enterprise-only continuation:

- `DELIVERABILITY_REVIEW`
- `PROOF_READY_FOR_SALE`
- `CONTRACT_PENDING`
- `PAYMENT_PENDING`
- `DELIVERY_READY`
- `DELIVERED`

No state before canonical qualification may be interpreted as formal proof evidence.

## Base44 boundary

Base44 may hold low-volume submission metadata such as:

- submission ID;
- submitter/account reference;
- PR number;
- UI status;
- notification/read state.

Base44 must not store the authoritative proof artifact, proof-ledger truth, formal qualification, or high-frequency CI/proof telemetry.

Authoritative proof state remains Oracle/CACE + GitHub/qualification artifacts.

## Security/privacy

Before repository submission:

- strip account/payment credentials;
- strip unrelated customer data;
- preserve only explicitly approved proof inputs;
- classify customer/confidential material;
- prevent accidental disclosure of CACE trade-secret theorem source;
- keep enterprise/customer branches private.

## Branch lifecycle

Generic coding agents may not use proof-submission branches merely because they exist.

Submission branches are controlled review artifacts and should be classified/frozen under `BRANCH_LIFECYCLE.json`.

## Trust boundary

User proof sketches, Gemini output, GitHub PRs, review comments, and commercial intent are all non-evidentiary until the canonical CACE proof/qualification pipeline establishes the relevant result.
