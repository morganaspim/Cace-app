# Google AI Studio + Cloud Run Deployment Contract

Status: deployment/product architecture. Not proof evidence.

## Default position

Cloud Run is **optional and disabled by default**.

Use it only when CACE genuinely needs a stateless public web/server edge that should scale independently from the Oracle VM.

The default CACE path remains:

```text
Gemini UI
   -> Oracle/CACE typed API
   -> Base44 only for low-volume account/entitlement metadata
```

Cloud Run is inserted only when it solves a real production-edge problem.

## Cost guard

Canonical policy:

- `ops/cloud_run_cost_guard.json`
- `ops/cloud_run_edge_policy.json`

Initial production defaults:

- request-based billing;
- minimum instances: **0**;
- maximum instances: **1**;
- 1 vCPU;
- 512 MiB memory;
- no GPU;
- no always-on CPU;
- no automatic continuous deployment;
- no deployment per commit;
- explicit operator approval before enabling production Cloud Run.

Google documents service-level maximum instances as a cost safeguard, but also notes the configured maximum can be exceeded briefly in some scaling/revision circumstances. Therefore CACE does **not** treat max-instances as a perfect billing hard stop.

A monthly operator budget must be set before production enablement. Budget alerts are useful monitoring, but are not themselves a guaranteed hard spending cap.

## Recommended architecture when enabled

```text
Gemini AI Studio / Antigravity
        |
        | builds + syncs
        v
GitHub (canonical source)
        |
        | reviewed, approved deployment only
        v
Cloud Run
optional stateless web/server edge
        |
        +--> Base44
        |    low-volume accounts/entitlements
        |
        +--> Oracle/CACE
             durable workspaces + fair run queue
             science + proofs + workers
```

## Use Cloud Run only when necessary

Examples of valid reasons:

- multi-user public web traffic needs independent edge scaling;
- server-side authentication/session callbacks cannot safely live in browser code;
- SSE/status fanout materially reduces load on Oracle;
- approved production traffic needs a stateless edge.

Not sufficient:

- development convenience;
- every Git push;
- a single-user session;
- scientific computation;
- proof computation;
- polling/background work;
- static files alone.

## Deployment source

GitHub remains the canonical source of reviewed application code.

AI Studio may build and synchronize the frontend.

Preferred deployment behavior:

- manual/reviewed deployment by default;
- continuous deployment disabled unless explicitly approved;
- Cloud Build only for approved deployments;
- keep Artifact Registry image churn low.

Cloud Run source deployments can use Cloud Build and Artifact Registry, which have pricing separate from Cloud Run. Avoid rebuilding/deploying on every commit merely for convenience.

## Multi-user role

If enabled, Cloud Run can absorb browser-facing traffic while the free Oracle VM keeps the durable scientific queue.

Default model:

- many browser sessions;
- at most one Cloud Run instance initially;
- high HTTP concurrency on that one instance;
- one heavy Oracle science worker;
- durable queued runs on Oracle/CACE;
- no scientific state stored only in Cloud Run memory.

## Service name and region

Do not choose the production Cloud Run service name or region automatically.

Both are deployment identity choices. Changing either later should be treated as creating/migrating to a new service.

The operator must explicitly approve them.

## Billing safety

CACE should surface:

- Cloud Run enabled/disabled state;
- configured monthly budget;
- max instance cap;
- last deployment reason;
- current cost-policy zone when available.

Never claim the Google billing budget is a hard spend cap.

At the internal 75% budget-alert zone, optional Cloud Run use should stop. At 90%, preserve only explicitly approved critical edge traffic.

## Proof/science boundary

Cloud Run never becomes:

- CACE scientific authority;
- proof qualification engine;
- proof ledger;
- worker sandbox;
- canonical workspace/run store.

Oracle/CACE remains authoritative.
