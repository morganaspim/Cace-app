# Base44 Free-Tier Credit Policy for CACE

Status: cost/governance policy. Not a guarantee of Base44 pricing or metering.

Last checked: 2026-09-20.

Current Base44 Free pricing page advertises:

- 25 message credits/month;
- 100 integration credits/month.

Exact usage can vary by action/model and Base44 may change free/trial allowances. The application must therefore use conservative internal budgets rather than assuming every action costs exactly one credit.

## Monthly operating target

CACE reserves substantial capacity for unexpected use.

Internal target:

- message credits: **15/month target**, hard application budget 18;
- integration credits: **60/month target**, hard application budget 75;
- remaining platform allowance is preserved as emergency reserve.

The machine-readable policy is `ops/base44_free_tier_budget.json`.

## Zones

### GREEN

Estimated use below 50% of CACE hard application budget.

Behavior:

- ordinary low-volume commodity operations allowed.

### YELLOW

50–65%.

Behavior:

- batch metadata writes;
- suppress optional notifications;
- avoid cosmetic/duplicate operations.

### RED

65–75%.

Behavior:

- essential account/workspace metadata only;
- optional Base44 integrations disabled.

### HARD STOP

Above 75% of the advertised free-tier monthly allowance, or when the configured CACE hard application budget is reached.

Behavior:

- no optional metered Base44 integrations;
- no Base44 AI/model/image/email actions;
- preserve capacity for essential account/recovery operations;
- queue non-critical metadata locally when safe.

## Never spend Base44 credits on

- scientific execution;
- canvas movement;
- worker heartbeats;
- run/proof polling;
- autonomous-agent turns;
- LLM inference;
- generated scientific images;
- raw datasets;
- scientific artifacts;
- worker receipts;
- proof artifacts;
- logs/telemetry streams.

## Build-credit policy

Gemini, not Base44, is the primary code/UI builder for CACE.

Base44 message credits should not be consumed by routine iterative CACE frontend development.

If Base44 must be prompted for a commodity-service change:

1. batch requirements into one prompt;
2. avoid cosmetic iteration;
3. verify locally before another prompt;
4. prefer code/config changes through the normal repository once available.

## Accounting

Because platform metering can change, maintain two values:

- **platform-reported balance** when available;
- **CACE local estimate** for operations initiated through the Base44 adapter.

Never present the local estimate as the official bill.

## Sources

- https://base44.com/pricing
- https://base44.com/terms-of-service


## Account entitlement reads

Account tier/benefit definitions live in `ops/base44_account_tiers.json`.

The app should avoid repeated Base44 entitlement reads:

- resolve/cache the current entitlement view at login/session start;
- refresh on meaningful entitlement/account changes;
- do not query Base44 on canvas events, scientific progress, proof polling, or worker heartbeats;
- revalidate sensitive operations at Oracle/CACE rather than increasing Base44 polling frequency.


## Enterprise Full-Rigor Proof Package credit reserve

An active Enterprise Full-Rigor Proof Package order is a **high-priority permitted Base44 use**.

The machine budget reserves:

- **5 message credits/month**
- **20 integration credits/month**

for Enterprise proof-order administration.

Normal/optional Base44 features must not consume this protected reserve.

When ordinary Base44 activity has reached the normal HARD STOP, an active Enterprise proof-order workflow may still use the protected reserve for low-volume operations such as:

- order metadata;
- proof-order status transitions;
- SOW/contract status;
- signature status;
- payment/credit approval status;
- delivery status;
- operator/customer notifications related to that order.

This exception does **not** move scientific/proof work into Base44. Even for an Enterprise order, Base44 must not run Lean, execute science, store authoritative proof artifacts, stream CI, or carry high-frequency proof telemetry.

The reserve may never silently exceed the platform-reported monthly allowance or trigger paid credits/resources.
