# Gemini Multi-User Concurrent Session Contract

Status: product/runtime integration contract. Not proof evidence.

## Target experience

CACE should support many authenticated users at once even on constrained infrastructure:

- many users can browse/edit independent workspaces concurrently;
- one heavy scientific run does not freeze another user's UI/API;
- refresh, laptop sleep, temporary network loss, or closing a tab does not cancel a run;
- reconnect uses stable `workspace_id` / `run_id`;
- no cross-user workspace/run leakage;
- free Oracle compute is queued fairly instead of oversubscribed.

Machine policy: `ops/multi_user_session_policy.json`.

## Concurrency model

**Interactive concurrency is not the same as heavy-compute concurrency.**

Default free-VM model:

- many browser sessions;
- scalable/stateless Cloud Run web edge where enabled;
- responsive Oracle/CACE API control plane;
- one heavy scientific worker at a time;
- durable fair queue for additional runs.

## Base44

Base44 handles low-frequency identity/membership/entitlement metadata only.

Never use Base44 for:

- presence heartbeats;
- canvas autosave;
- run progress;
- queue position;
- worker status;
- proof polling.

## Oracle/CACE

Oracle/CACE is authoritative for:

- workspace authorization;
- canonical experiment/workspace version;
- scientific run queue;
- run ownership;
- pause/resume/cancel;
- scientific/proof/evidence/security truth.

## Browser/Gemini

Gemini builds:

- `SessionProvider`;
- per-tab `client_instance_id`;
- workspace tabs;
- optimistic editing;
- local IndexedDB drafts;
- reconnect UX;
- run queue/status UI;
- one SSE event stream per active browser session;
- polling fallback with backoff;
- version-conflict/rebase UI.

Do not create one global mutable "current experiment" singleton.

## Workspace saves

Every mutation conceptually includes:

```text
workspace_id
expected_workspace_version
client_request_id
candidate experiment/mutation
```

Server returns the next version or a typed conflict.

Never silently last-write-wins over another accepted update.

## Scientific runs

A run binds an immutable workspace/experiment snapshot.

Run creation is idempotent.

Closing/reloading a browser must not issue cancel.

Fair scheduling should rotate between principals before taking a second queued job from the same principal.

## Reconnect

On reconnect:

1. restore authenticated identity/entitlements;
2. restore known workspace/run IDs;
3. GET authoritative workspace/version;
4. GET active/recent run snapshots;
5. open/reopen the event stream;
6. reconcile local drafts;
7. continue showing the same run.

## Failure semantics

"Without interruption" must not fabricate survival of a dead process.

- Browser/network interruption: run continues.
- Cloud Run instance replacement: stateless edge reconnects.
- Oracle API restart: durable state reloads.
- Worker crash: FAILED or RECOVERY_REQUIRED.
- Oracle VM reboot/reclamation: recover durable workspace/queue state; interrupted science is explicitly recovered/restarted where supported.

Never manufacture COMPLETED.

## Readiness gate

The current API is not yet sufficient for production multi-user claims.

Gemini may build against typed mocks/adapters, but production UI must show `MULTI_USER_BACKEND_PENDING` until the backend requirements in `gemini/requests/MULTI_USER_CONCURRENT_SESSION_API.md` are implemented and tested.
