# Gemini Handoff — Production VRE Closure

Read first:

- `GEMINI_CONNECTION_MANIFEST.json`
- `ops/production_vre_closure.json`
- `docs/PRODUCTION_VRE_CLOSURE_PLAN.md`
- `ops/multi_user_session_policy.json`
- `gemini/requests/MULTI_USER_CONCURRENT_SESSION_API.md`

## Your closure workload

Proceed in bounded batches inside Gemini's allowed write scope.

### Batch G-CLOSE-1

Build/finish the React shell and one typed CACE API client. No scientific logic in components.

### Batch G-CLOSE-2

Build multi-user UX against the versioned API contract:

- SessionProvider;
- workspace IDs/versions;
- reconnect;
- conflicts/rebase;
- queue/run status;
- SSE + polling fallback;
- local IndexedDB drafts.

Keep `MULTI_USER_BACKEND_PENDING` until backend readiness is verified.

### Batch G-CLOSE-3

Build account/entitlement UI using Base44 adapter and canonical pricing/promotion policies.

### Batch G-CLOSE-4

Build Monero checkout UI against the payment-only Cloud Run contract. The browser never decides payment success or paid entitlement.

### Batch G-CLOSE-5

Build module help/example surfaces from typed module metadata; show assumptions, units, validity domain, evidence/proof state and limitations.

### Batch G-CLOSE-6

Build admin/operations UI for Oracle/CACE health, queue, storage pressure, worker/sandbox status, and recovery attention.

### Batch G-CLOSE-7

Add browser-level concurrency/reconnect/accessibility/cross-browser tests.

For every batch, report:

- files changed;
- API endpoints consumed/needed;
- Base44 operations introduced;
- tests;
- unresolved backend requirements;
- any protected path you believe needs a change.

Do not implement missing protected backend/scientific semantics in frontend code.
