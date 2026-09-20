# Base44 Account Tier and Entitlement Contract

Status: product/account integration contract. Not scientific or proof evidence.

Canonical machine-readable tier manifest:

`ops/base44_account_tiers.json`

Base44 and the Gemini-generated UI should read/use this contract rather than separately inventing account benefits.

## Authority boundary

Base44 may own low-volume account and entitlement metadata and may use it to show/hide ordinary product features.

Base44 does **not** decide:

- whether a scientific result is correct;
- whether verification passed;
- whether a theorem is FORMAL;
- whether a proof is canonically qualified;
- whether a proof package is proof-ready.

Those decisions remain Oracle/CACE + the normal proof/qualification pipeline.

## Common benefits

All account tiers may:

- use the GPU Acceleration control when a supported backend exists;
- see/use CUDA controls only when a compatible NVIDIA CUDA backend is actually detected;
- submit a proof candidate for CACE project review.

A proof candidate submitted by any tier is a review contribution only. Gemini may package it and send it to a controlled GitHub draft PR, but it is not proof evidence until the normal CACE rigor checks and human review pass.

## Basic

Intended for personal learning, evaluation, and noncommercial exploration.

Benefits:

- one first-time 24-hour introductory entitlement for eligible users;
- GPU acceleration;
- CUDA when compatible hardware/backend is detected;
- single-thread CPU by default;
- optional one-time permanent Basic multithread unlock:
  - `feature.cpu_multithread.basic.perpetual.v1`
  - current target price: USD $15;
- proof-candidate submission for project improvement;
- no Enterprise full-rigor proof-package purchase path.

Current target passes:

| Duration | Target |
|---|---:|
| 1 day | $4.99 |
| 1 week | $14.99 |
| 1 month | $39 |
| 1 year | $199 |

## Researcher

Intended for academic, nonprofit, independent scientific, and other noncommercial research under the applicable license.

Benefits:

- one first-time 48-hour introductory entitlement for eligible users;
- GPU acceleration;
- CUDA when compatible hardware/backend is detected;
- CPU multithreading included;
- proof-candidate submission for project improvement;
- no Enterprise commercial full-rigor proof-package purchase path.

Current target passes:

| Duration | Target |
|---|---:|
| 1 day | $14.99 |
| 1 week | $49 |
| 1 month | $149 |
| 1 year | $999 |

## Enterprise

Required for intended business/commercial use such as engineering/product development, commercial scientific discovery, client work, or other revenue-generating activity under the applicable commercial terms.

Benefits:

- GPU acceleration;
- CUDA when compatible hardware/backend is detected;
- CPU multithreading included;
- commercial-use entitlement;
- proof-candidate submission for project improvement;
- **Request Full-Rigor Proof Package** eligibility;
- optional separately quoted enterprise compute/private deployment/support/storage/seat arrangements.

There is no automatic Enterprise free allowance in the current policy. A separate sales/evaluation entitlement may be issued.

Current target named-user/seat passes:

| Duration | Target |
|---|---:|
| 1 day | $99 |
| 1 week | $399 |
| 1 month | $1,499 |
| 1 year | $9,999 |

## Enterprise proof package rule

Base44 may show the request/order UI and store low-volume order/status metadata.

The purchase flow remains:

`freeze request -> internal proof PR -> normal CACE rigor pipeline -> human review -> canonical qualification -> deliverability/IP review -> PROOF_READY_FOR_SALE -> contract/signature/payment -> delivery`

Base44 must not move an order to `PROOF_READY_FOR_SALE` merely because Gemini generated a proof or a GitHub PR exists.

## UI implementation

Gemini should render benefits from `ops/base44_account_tiers.json` and keep tier checks centralized in the Base44/account adapter.

Do not scatter checks such as `if tier === "Enterprise"` throughout unrelated UI code.

Preferred pattern:

`accountEntitlements.can("request_full_rigor_proof_package")`

The underlying entitlement service may be Base44-backed, but security/scientific-sensitive actions are revalidated server-side by CACE.

## Cost discipline

Reading account metadata is a low-volume Base44 use.

Do not repeatedly query Base44 on canvas events or scientific polling. Cache the signed/current entitlement view for the session and refresh only on meaningful account/entitlement changes according to the account-security policy.

See:

- `docs/BASE44_CREDIT_POLICY.md`
- `docs/ACCOUNTS_AND_ENTERPRISE_PROOF_COMMERCE.md`
- `docs/PROOF_SUBMISSION_REVIEW_WORKFLOW.md`


## Recurring Tuesday/Saturday pass sale

The machine-readable recurring promotion is:

- `ops/pass_promotion_policy.json`
- mirrored in `ops/base44_account_tiers.json`

Commercial calendar:

- timezone: **America/Phoenix**
- eligible days: **Tuesday and Saturday**
- active for the full local calendar day
- non-stackable

Discounts:

| Tier | Discount | 1 day | 1 week | 1 month | 1 year |
|---|---:|---:|---:|---:|---:|
| Basic | 50% off | $2.50 | $7.50 | $19.50 | $99.50 |
| Researcher | 60% off | $6.00 | $19.60 | $59.60 | $399.60 |
| Enterprise | 75% off | $24.75 | $99.75 | $374.75 | $2,499.75 |

The sale applies only to eligible day/week/month/year account passes.

It does **not** apply to:

- the Basic perpetual CPU multithread unlock;
- Enterprise Full-Rigor Proof Packages;
- proof consulting/SOW pricing;
- separately quoted Enterprise compute/deployment/support/storage/site arrangements.

Gemini/Base44 should render the price from the promotion policy and persist the promotion policy ID, normal price, discount percent, final price, and purchase timestamp in invoice/order metadata.

The discount is commercial configuration only and has no effect on scientific or proof status.
