# CACE-KSEE Gemini Implementation Contract

Status: implementation contract. Not scientific/proof evidence.

## Product role

Gemini AI Studio Build Mode / Antigravity is the primary implementation environment for the CACE-KSEE browser experience.

Gemini builds the interface against typed contracts. It does not duplicate CACE scientific/proof authority.

## Required architecture

```text
Gemini-generated React/TypeScript
        |
        +--> Base44 adapter
        |      low-volume commodity app services only
        |
        +--> CACE typed API
               |
               v
            Production CACE backend
               |
               +--> Python orchestration
               +--> C++ kernels
               +--> Lean/proof governance
               +--> sandboxed science workers
```

## Gemini owns

- UI components;
- routing/navigation;
- canvas interaction;
- visualization;
- accessibility;
- client-side view state;
- Help/tutorial surfaces;
- approval/recovery UX;
- typed API clients;
- typed Base44 adapter;
- frontend tests.

## Gemini must not own

Gemini must not create an alternate implementation of:

- GraphExecutor;
- scientific modules;
- numerical/exact kernels;
- verification;
- certificate validity;
- claim/proof promotion;
- formal status;
- Lean theorem semantics;
- sandbox/security truth;
- canonical scientific hashes.

## Base44 adapter rule

All Base44 calls must go through one narrow adapter surface.

Recommended location:

`webapp/src/services/base44Client.ts`

Do not scatter Base44 calls across components.

The adapter must classify every operation as one of:

- `CORE_LOW_VOLUME`;
- `OPTIONAL_METERED`;
- `FORBIDDEN_HIGH_FREQUENCY`.

`FORBIDDEN_HIGH_FREQUENCY` operations must never execute.

## CACE API rule

All scientific calls go through the typed CACE client.

Recommended location:

`webapp/src/api/caceClient.ts`

The UI must treat CACE-returned scientific/evidence/security fields as read-only authority.

## Base44 monthly-budget UX

Gemini must expose a small admin/status panel showing:

- configured monthly message-credit budget;
- configured monthly integration-credit budget;
- internal estimated usage counter if available;
- current policy zone: GREEN/YELLOW/RED/HARD_STOP;
- which optional Base44 features are disabled by policy.

The UI must not claim Base44's authoritative billing total unless the platform supplies that value through an official API. Local counters are estimates and must be labeled as such.

## Production CACE backend operations UX

The admin/status surface should show CACE-returned:

- worker concurrency;
- CPU/RAM limits;
- storage pressure;
- sandbox preflight status;
- cgroup/sandbox capability status;
- recovery/attention items.

Do not infer these from browser timing.

## Offline/degraded behavior

If Base44 is unavailable or at HARD_STOP:

- scientific execution remains Production CACE backend-backed;
- transient UI state remains local;
- non-critical metadata writes may queue locally;
- no scientific truth migrates to Base44/browser state.

## Credit-sensitive implementation rule

Do not use Base44 for:

- polling loops;
- canvas position updates;
- science-run progress;
- telemetry;
- AI chat;
- run artifacts;
- proof artifacts;
- high-frequency notifications.

Batch low-volume metadata changes where practical.

## Security

Never put production CACE credentials, proof-runner credentials, signing keys, or CACE secrets in Gemini-generated browser bundles or Base44 records.

## Required handoff after each Gemini batch

Report:

- changed files;
- CACE endpoints consumed/changed;
- Base44 operations added;
- expected monthly credit impact;
- tests;
- scientific/evidence impact;
- qualification-sensitive changes yes/no;
- unresolved obligations.


## Proof-candidate submission and GitHub review

When CACE exposes **Submit Proof Candidate for CACE Review** or an Enterprise **Request Full-Rigor Proof Package** flow, Gemini may help package the candidate for review.

Gemini may:

- normalize the theorem/assumption packet;
- draft Lean source;
- draft tests and source-to-formal notes;
- prepare a bounded repository patch;
- prepare a draft PR description.

Gemini must route the result through `docs/PROOF_SUBMISSION_REVIEW_WORKFLOW.md` and `ops/proof_submission_policy.json`.

Gemini must never treat the submission, generated Lean, draft PR, or passing preflight as proof authority.

A controlled submission should produce a draft GitHub PR on `submission/proof/<submission-id>`. After the initial submission commit, that branch is a frozen review artifact under `BRANCH_LIFECYCLE.json`.

When CI reaches the human gate, the UI should surface `PR_REVIEW_REQUIRED` with the PR URL, exact head SHA, current checks, unresolved obligations, and recommended next gate so the operator can review it through ChatGPT.

For Enterprise proof packages, the customer purchase flow cannot proceed to completed sale until canonical qualification and deliverability review produce `PROOF_READY_FOR_SALE`.


## Base44 account tiers and benefits

Base44/Gemini must use `ops/base44_account_tiers.json` and `docs/BASE44_ACCOUNT_ENTITLEMENT_CONTRACT.md` as the account-benefit contract.

Do not duplicate tier benefits in unrelated UI components.

Centralize account feature checks through one entitlement adapter, for example:

`accountEntitlements.can("request_full_rigor_proof_package")`

Required behavior includes:

- Basic: 24-hour first-time intro entitlement, GPU/CUDA when available, single-thread CPU by default, optional perpetual multithread unlock, proof-candidate submission;
- Researcher: 48-hour first-time intro entitlement, GPU/CUDA, CPU multithreading included, proof-candidate submission;
- Enterprise: commercial-use entitlement, GPU/CUDA, CPU multithreading included, proof-candidate submission, and eligibility to request a purchasable Full-Rigor Proof Package.

General proof-candidate submission is not Enterprise-only. The commercial Full-Rigor Proof Package path is Enterprise-only.

Base44 may gate ordinary UI benefits from account metadata, but CACE must revalidate scientific/security/proof-sensitive actions server-side.


## Recurring pass promotions + Enterprise order credit priority

Gemini must consume `ops/pass_promotion_policy.json`; do not hard-code promotion dates or percentages in components.

In `America/Phoenix`:

- every Tuesday: show the 1-day pass at 75% off for all tiers;
- every 14 days on Saturday starting 2026-09-26: show the 1-week sale (Basic 50%, Researcher 60%, Enterprise 75%);
- every 3 months starting 2026-12-20: show the 1-month pass at 45% off for all tiers;
- every 3 years starting 2027-01-01: show the 1-year pass at 50% off for all tiers for exactly one 24-hour America/Phoenix day; the checkout server requires both order creation and first verified payment sighting within that window.

The UI must treat server-returned catalog/price data as authoritative. Client-submitted promotion eligibility or final price is never trusted.

If promotions coincide, show both eligible SKUs independently; never stack discounts on one SKU.

For an active Enterprise proof-package order, the Base44 adapter may classify necessary low-volume order operations as `ENTERPRISE_ORDER_CRITICAL` and use the protected reserve defined in `ops/base44_free_tier_budget.json`.

Do not move proof computation/CI/artifact storage into Base44 merely because an Enterprise order exists.


## CACE-KSEE entry / branding / public-help contract

Gemini must read `docs/CACE_KSEE_ENTRY_EXPERIENCE.md`.

Required browser behavior includes:

- production-facing name **CACE-KSEE** (pronounced Casey);
- original aerospace-clean geometric/ASCII/Conway-inspired splash;
- Create account / Sign in / Learn about CACE-KSEE entry actions;
- post-account Research Assistant introduction and skippable canvas tour;
- exact **Invite Collaborators** workspace action;
- high-level module documentation showing typed inputs, outputs, examples,
  assumptions, limitations, and evidence without exposing proprietary internals;
- subtle `© 2026 Emmanuel Spiro. All rights reserved.` footer on the appropriate
  splash/account/About/Help surfaces;
- reduced-motion support.

Do not ship proprietary scientific/proof algorithms in the browser to make the UI
feel self-contained. Missing semantics require a typed Production CACE backend
endpoint, not a JavaScript reimplementation.

## Oracle boundary

Oracle is CI/runner/qualification only. Gemini must not configure production
browser sessions, scientific execution, user workspaces, payments, or production
secrets against Oracle. Production API origin is configurable and provider-neutral
until the production runtime host is selected.
