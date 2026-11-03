# Monero Payment + Entitlement Contract

Status: commerce/security architecture. Not proof evidence.

## Decision

CACE may use the optional paid Cloud Run service for **Monero checkout and payment finalization**.

This is a justified Cloud Run use because secrets and payment verification need a server-side boundary.

Cloud Run remains stateless and must **not** custody a Monero wallet seed or spend key.

## Flow

```text
User selects exact CACE product/SKU
        |
        v
Cloud Run payment service
  - resolves Basic / Researcher / Enterprise price
  - applies Tuesday/Saturday promotion when eligible
  - freezes USD + XMR quote
  - creates payment order with verifier
        |
        v
Monero payment verifier
  - unique invoice destination/subaddress
  - observes payment
  - confirms amount + confirmations
        |
        v
Cloud Run finalizer
  - independently verifies order/payment
  - idempotently finalizes
  - signs entitlement grant
        |
        +--> Base44
        |    payment history + paid amount/time
        |    current account entitlement mirror
        |
        +--> Oracle/CACE
             verifies signed entitlement before
             executing paid capabilities
```

## Product, not amount, determines access

Never determine account tier by asking "how much XMR arrived?"

The order freezes a specific SKU, for example:

- Basic 1 month;
- Researcher 1 year;
- Enterprise 1 week;
- Basic permanent CPU multithread unlock.

The payment must satisfy that invoice.

Overpayment does not upgrade the customer.

Underpayment does not unlock the product.

This prevents exchange-rate movement, accidental overpayment, or malicious amount selection from changing entitlements.

## Recurring pass promotions

Order creation reads:

- `ops/base44_account_tiers.json`
- `ops/pass_promotion_policy.json`

Cloud Run computes the catalog and price server-side in `America/Phoenix`.

- Every Tuesday: 1-day pass, 75% off for all tiers.
- Every 14 days on Saturday starting 2026-09-26: 1-week pass; Basic 50% off, Researcher 60% off, Enterprise 75% off.
- Every 3 months starting 2026-12-20: 1-month pass, 45% off for all tiers.
- Every 3 years starting 2027-01-01: 1-year pass, 50% off for all tiers for exactly one 24-hour America/Phoenix day.

For the triennial year-pass event, both the order creation time and the first verified payment sighting must fall within that 24-hour window. Required blockchain/payment confirmations may finish afterward.


The browser submits the SKU, not an authoritative price or promotion flag.

The applicable price is frozen at checkout. If confirmations complete after the promotional day ends, the already-created unexpired order keeps its frozen quote.

If two promotions coincide, each applies only to its own duration and the discounts do not stack.

The invoice records the requested SKU, normal USD price, active promotion branch, discount, final USD price, promotion policy ID, XMR/USD quote, XMR amount due, and quote expiry.

## Payment confirmation

Production default is 10 confirmations unless the operator raises the threshold.

Monero's merchant guidance says more confirmations increase safety and notes 10 confirmations before newly received funds are spendable/unlocked.

A seen transaction is not enough to unlock CACE.

Recommended states:

`AWAITING_PAYMENT -> PAYMENT_SEEN -> CONFIRMING -> PAYMENT_CONFIRMED -> ENTITLEMENT_GRANTED`

Partial/expired/problem payments remain non-entitled and visible for review.

## Monero verifier

Cloud Run should not run `monerod` or persist `monero-wallet-rpc` wallet files.

Configure one reviewed persistent payment verifier.

A compatible architecture can use BTCPay Server with the community Monero plugin, or a dedicated wallet-RPC payment verifier. BTCPay's official documentation describes Monero as an opt-in plugin integration rather than core support, and the Monero plugin warns that it shares one Monero wallet across stores on an instance.

For CACE, use a dedicated merchant instance/verifier rather than a shared third-party multi-store wallet arrangement unless explicitly reviewed.

## Base44 records

After final verification Cloud Run writes a server-only payment record to Base44.

The user's account can show:

- what was purchased;
- XMR received;
- USD order price;
- discount used;
- date payment was first seen;
- date confirmed;
- purchased tier/duration;
- active entitlement;
- historical purchase list.

Useful account aggregates:

- lifetime USD-equivalent paid, based on frozen order prices;
- lifetime XMR paid;
- most recent confirmed payment date.

The end user may read their own records but may not create/edit payment or entitlement records.

## Signed entitlement grant

Do not make "Base44 row says paid" the only server-side control.

After confirmation, Cloud Run creates a signed entitlement grant.

Recommended: Ed25519.

Private signing key stays in a server-side secret store. Oracle/CACE has only the verification/public key.

Before a paid scientific action, CACE verifies:

- signature;
- principal/account binding;
- feature/tier;
- validity interval;
- policy version.

This prevents browser edits or an accidental Base44 write from becoming paid scientific access.

## Enterprise proof packages

Enterprise Full-Rigor Proof Packages remain **prove first, sell second**.

Monero may be used to pay an approved Enterprise proof-package invoice only after the existing commerce/proof workflow reaches the appropriate sale/contract/payment stage.

Payment never creates proof qualification.

## Refunds

Initial version should use a manual/refund-review workflow.

Cloud Run should not automatically send XMR. That would require spend-key custody and creates a much larger security boundary.

## Cloud Run cost rule

The payment service still obeys `ops/cloud_run_cost_guard.json`:

- request-based billing;
- min 0;
- max 1 initially;
- no GPU;
- no always-on CPU;
- no deploy-on-push;
- no background polling.

Payment status should be driven by authenticated verifier callbacks or short user-requested status checks, not continuous Cloud Run polling.
