# API Extension Request — Multi-User Concurrent Sessions

Owner: Oracle/CACE API/runtime
Consumer: Gemini webapp
Status: REQUIRED FOR PRODUCTION MULTI-USER READINESS
Proof effect: none

## Current gap

The current browser API has process-local run/job state and does not expose a complete authenticated tenant/workspace lifecycle.

Gemini must not compensate with client-side authority.

## Required server capabilities

### Authenticated principal context

Every workspace/run operation must use a server-validated principal and optional organization context. Browser tier/workspace claims are not authority.

### Durable workspace API

Illustrative versioned endpoints:

- `POST /api/v2/workspaces`
- `GET /api/v2/workspaces`
- `GET /api/v2/workspaces/{workspace_id}`
- `PUT /api/v2/workspaces/{workspace_id}`

Workspace returns:

- workspace ID;
- version;
- canonical experiment;
- semantic/full hashes;
- timestamps;
- permissions.

Update requires expected version + idempotency/client request ID.

### Durable run queue

Illustrative endpoints:

- `POST /api/v2/runs`
- `GET /api/v2/runs`
- `GET /api/v2/runs/{run_id}`
- `POST /api/v2/runs/{run_id}/pause`
- `POST /api/v2/runs/{run_id}/resume`
- `POST /api/v2/runs/{run_id}/cancel`

Create Run binds an immutable workspace version/snapshot and an idempotency key.

### Fair scheduling

Free Oracle default:

- one heavy worker;
- max global queued runs: 32;
- max queued runs per principal: 4;
- round-robin by principal, FIFO within principal;
- interactive API capacity reserved separately.

### Events

Preferred versioned SSE endpoint:

`GET /api/v2/events`

Events are advisory. Snapshot GET endpoints remain authoritative.

### Isolation tests

Server tests must show:

- principal A cannot list/get/update private workspace B;
- A cannot control B's run;
- organization access follows explicit membership policy;
- opaque IDs do not bypass auth;
- browser entitlements do not bypass server-side checks.

### Recovery

Browser disconnect never cancels a run.

API restart reconciles durable queue/run metadata.

Worker/VM failure results in FAILED/RECOVERY_REQUIRED, never fabricated completion.

### Compatibility

Expose the multi-user/session surface through additive/versioned typed schemas so future proof promotion/internal scientific changes do not break Gemini/Base44.
