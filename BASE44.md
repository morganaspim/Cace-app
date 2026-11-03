# BASE44 — CACE Connection Entrypoint

Base44 is **not** a general CACE code builder.

Its CACE role is deliberately narrow:

> **Build and operate only the low-volume commodity application services CACE needs. Gemini builds the interface. Oracle/CACE remains the scientific authority.**

Before doing anything, read:

1. `BASE44_CONNECTION_MANIFEST.json`
2. `base44/BASE44_TASK_STATE.json`\n3. `BRANCH_LIFECYCLE.json`
4. `docs/architecture/ADR-001-GEMINI-BASE44-ORACLE-CACE.md`
5. `docs/BASE44_ACCOUNT_ENTITLEMENT_CONTRACT.md`
6. `docs/BASE44_CREDIT_POLICY.md`
7. `ops/base44_account_tiers.json`
8. `ops/base44_free_tier_budget.json`
9. `ops/pass_promotion_policy.json`
10. `docs/ACCOUNTS_AND_ENTERPRISE_PROOF_COMMERCE.md`
11. `docs/PROOF_SUBMISSION_REVIEW_WORKFLOW.md`

## Build only these services

- auth/accounts/profiles;
- organizations/teams/workspace-membership metadata;
- Basic/Researcher/Enterprise entitlement metadata;
- first-time trial claims;
- Basic permanent CPU-multithread unlock entitlement;
- pass/invoice metadata;
- Tuesday/Saturday promotion metadata;
- low-volume preferences/notes/tags/collaboration metadata;
- low-volume notifications;
- Enterprise proof-package order/SOW/contract/payment/delivery metadata;
- Base44 credit-usage estimate/policy state.

## Do not build

Do not implement CACE science, graph execution, Python/C++ kernels, Lean/proofs, qualification, proof ledgers, scientific artifact storage, telemetry, run/proof polling, agent turns, or the primary browser interface.

Do not use Base44 as the CACE event bus.

## Repository write boundary

Base44 may write directly only under:

`base44/**`

Everything else is read-only or proposal-only unless the user/ChatGPT explicitly grants a temporary exception.

Do not write to `main`. Do not create/force-push/merge/delete branches by default. A branch must be `ACTIVE` in `BRANCH_LIFECYCLE.json` before any permitted repository write.

## Credits

Treat Base44 credits as scarce.

Follow `ops/base44_free_tier_budget.json`.

Normal features must preserve the protected Enterprise proof-order reserve. Enterprise-order priority still covers only low-volume commercial/account workflow—never scientific/proof computation.

## Authority

Base44 account/entitlement metadata may control ordinary UI access.

It may never create scientific truth, verification PASS, FORMAL status, proof qualification, or proof-ready commercial status.


## Proof-promotion compatibility

Read `docs/PROOF_PROMOTION_EXTERNAL_COMPATIBILITY.md`.

A proof being strengthened or canonically promoted should require **no Base44 change** unless the versioned commercial/order interface itself changes. Base44 mirrors CACE-supplied order states only; it does not inspect Lean, proof ledgers, claim registries, proof artifacts, or qualification jobs.

## Multi-user session boundary

Read `ops/multi_user_session_policy.json`.

Base44 supports multi-user CACE by supplying low-volume identity, organization/workspace membership, and entitlement metadata. Do not implement presence heartbeats, workspace autosave, run progress, queue polling, worker state, or proof polling in Base44.


## Monero payments and paid entitlements

Read:

- `docs/MONERO_PAYMENT_CLOUD_RUN_CONTRACT.md`
- `ops/monero_payment_policy.json`
- `schema/cace-payment-entitlement-grant.schema.json`

Base44 stores only low-volume server-written payment/order history and entitlement mirror metadata.

Users may read their own purchase history but may not write:

- paid/confirmed status;
- received amount;
- tier;
- entitlement duration;
- entitlement grant;
- proof-ready state.

Cloud Run verifies the payment and signs the entitlement grant. Oracle/CACE verifies the signed grant before paid scientific capabilities execute.

Base44 must not run or poll the Monero verifier.
