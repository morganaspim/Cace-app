# Gemini Request — Monero Checkout + Account Entitlement UI

Owner: Gemini webapp + Cloud Run payment edge + Base44 account backend
Scientific authority: Oracle/CACE
Status: READY FOR IMPLEMENTATION AFTER PAYMENT VERIFIER IS SELECTED

## UI responsibilities

Build:

- product/pass selection;
- server-returned recurring promotional price display (Tuesday day pass, alternating-Saturday week pass, quarterly month pass, triennial 24-hour year pass);
- Monero checkout QR/address/payment URI;
- quote expiry countdown;
- payment state display;
- confirmation progress;
- purchase history;
- current entitlement display;
- Basic permanent multithread unlock purchase option;
- Enterprise pass purchase;
- Enterprise proof-package invoice payment only when the existing proof-commerce state permits payment.

## Never decide paid state in the browser

The browser cannot submit:

- `paid=true`;
- `confirmed=true`;
- entitlement tier;
- entitlement expiry;
- confirmation count

as authority.

All authority comes from Cloud Run payment finalization + signed entitlement/backend records.

## Typed payment endpoints

Suggested versioned surface:

- `POST /payments/v1/orders`
- `GET /payments/v1/orders/{order_id}`
- `POST /payments/v1/provider-events/<adapter>` (authenticated provider/webhook only)
- `GET /payments/v1/me/history`
- `GET /payments/v1/me/entitlements`

Order creation input includes the SKU only. The server resolves the current catalog, promotion eligibility, and final price from `ops/pass_promotion_policy.json`. The browser never sends an authoritative discount or final price.

## Reconnect

Payment/order state survives browser reload.

Store only opaque `order_id` locally and refresh authoritative status.

Do not store payment signing keys, Base44 service keys or Monero wallet credentials in the browser.

## Base44

Display Base44-backed low-volume purchase history and account entitlement metadata.

Do not poll Base44 rapidly. Use the Cloud Run order-status endpoint during an active checkout and refresh Base44 account metadata after finalization.

## Production readiness

Do not enable live Monero checkout until:

- verifier adapter selected;
- Cloud Run payment service approved/enabled;
- payment signing key created securely;
- Base44 payment/entitlement entities have server-only write policy;
- Oracle/CACE entitlement signature verification exists;
- idempotency/partial/overpayment/expired quote tests pass;
- test payment completes end-to-end.


## Triennial year-pass UX

On the one-day year-pass sale every three years:

- show the exact America/Phoenix sale end time;
- do not imply that merely opening checkout reserves the discount;
- explain that the order and first verified payment sighting must occur before the 24-hour window closes;
- confirmation progress may continue after the window if payment was first verified in time;
- after the window closes, refresh catalog/pricing from the server and remove the discounted year SKU.
