# Cloud Run — Monero Payment Service Only

Status: deployment/security contract. Not proof evidence.

## Sole role

> **Cloud Run is used only for Monero payment coordination.**

Do not deploy the CACE web application, general API gateway, multi-user session edge, scientific workers, proof services, telemetry, or AI inference to Cloud Run.

Canonical machine policy:

`ops/cloud_run_payment_service_policy.json`

The historical `ops/cloud_run_edge_policy.json` file is a compatibility tombstone and explicitly disables general edge use.

## Architecture

```text
Gemini-built browser UI
        |
        +---------------------------> Oracle/CACE
        |                             workspaces
        |                             sessions
        |                             run queue
        |                             science/proofs
        |
        +--> Base44
        |    auth/account metadata
        |    low-volume entitlement mirror
        |
        +--> Cloud Run PAYMENT SERVICE ONLY
               |
               +--> persistent Monero payment verifier
               |
               +--> Base44 payment/order ledger
               |
               +--> signed entitlement grant
                        |
                        v
                    Oracle/CACE verifies
                    before paid execution
```

## Allowed requests

The Cloud Run service may expose only the payment surface defined in the payment contract, such as:

- create payment order;
- get payment order status;
- authenticated verifier callback/event;
- get own payment history;
- get own entitlement view.

It must reject or not implement general CACE routes.

## No wallet custody

Cloud Run must not store:

- Monero wallet seed;
- Monero spend key;
- persistent wallet files;
- a persistent `monero-wallet-rpc` wallet;
- a blockchain node.

It talks to a separately configured persistent payment verifier.

## Base44 update

After verified payment finalization Cloud Run writes server-authoritative, low-volume payment/order metadata to Base44 including:

- what SKU was purchased;
- XMR received;
- frozen USD order price;
- promotion used;
- when payment was first seen;
- when it was confirmed;
- tier/duration;
- entitlement ID and validity.

Users can read their own history but cannot create/edit paid status or entitlements.

## Unlock path

Cloud Run signs a narrow entitlement grant.

Oracle/CACE verifies the signature, principal binding, SKU/features, and validity before a paid scientific capability is executed.

Therefore:

`payment verified -> Base44 updated -> signed grant issued -> Oracle/CACE verifies -> feature unlocked`

Neither the browser nor a Base44 row alone is sufficient to unlock paid scientific access.

## Cost policy

Cloud Run remains disabled until payment support is explicitly enabled.

When enabled:

- request-based billing;
- min instances = 0;
- max instances = 1;
- 1 vCPU;
- 512 MiB;
- no GPU;
- no always-on CPU;
- no automatic deploy on push/PR;
- no continuous deployment;
- no background polling.

The service wakes for payment-related requests/callbacks and scales back to zero when idle.

## Multi-user sessions

Cloud Run is **not** part of the CACE multi-user session architecture.

Gemini/browser sessions talk directly to Oracle/CACE for workspaces, runs, status, and scientific state. Base44 supplies low-volume identity/entitlement metadata.

## Deployment

Do not select a production Cloud Run service name or region automatically.

Deployment requires:

1. Monero verifier selected and tested;
2. Base44 server-only payment/entitlement writes configured;
3. Oracle/CACE entitlement signature verification implemented;
4. Cloud Run monthly budget configured;
5. explicit operator approval;
6. reviewed payment-service revision.
