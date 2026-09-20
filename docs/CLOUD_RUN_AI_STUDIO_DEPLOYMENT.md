# Cloud Run General Edge — Disabled

Status: compatibility/deprecation notice.

Cloud Run must **not** be used as the CACE web application host, general API edge, multi-user session edge, SSE/event fanout service, Oracle proxy, scientific worker, proof service, telemetry service, or AI inference service.

Its only approved production responsibility is **Monero payment coordination**.

Read instead:

- `docs/CLOUD_RUN_MONERO_PAYMENT_DEPLOYMENT.md`
- `ops/cloud_run_payment_service_policy.json`
- `ops/cloud_run_cost_guard.json`
- `docs/MONERO_PAYMENT_CLOUD_RUN_CONTRACT.md`
- `ops/monero_payment_policy.json`

Gemini builds the interface. Browser/session/scientific traffic goes directly to Oracle/CACE. Base44 supplies low-volume account/entitlement metadata. Cloud Run wakes only for payment-related requests or authenticated payment-verifier callbacks.
