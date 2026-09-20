# CACE Gemini Implementation Contract

Status: implementation contract. Not scientific/proof evidence.

## Product role

Gemini AI Studio Build Mode / Antigravity is the primary implementation environment for the CACE browser experience.

Gemini builds the interface against typed contracts. It does not duplicate CACE scientific/proof authority.

## Required architecture

```text
Gemini-generated React/TypeScript
        |
        +--> Base44 adapter
        |      low-volume commodity app services only
        |
        +--> CACE typed API
               |
               v
            Oracle VM
               |
               +--> Python orchestration
               +--> C++ kernels
               +--> Lean/proof governance
               +--> sandboxed science workers
```

## Gemini owns

- UI components;
- routing/navigation;
- canvas interaction;
- visualization;
- accessibility;
- client-side view state;
- Help/tutorial surfaces;
- approval/recovery UX;
- typed API clients;
- typed Base44 adapter;
- frontend tests.

## Gemini must not own

Gemini must not create an alternate implementation of:

- GraphExecutor;
- scientific modules;
- numerical/exact kernels;
- verification;
- certificate validity;
- claim/proof promotion;
- formal status;
- Lean theorem semantics;
- sandbox/security truth;
- canonical scientific hashes.

## Base44 adapter rule

All Base44 calls must go through one narrow adapter surface.

Recommended location:

`webapp/src/services/base44Client.ts`

Do not scatter Base44 calls across components.

The adapter must classify every operation as one of:

- `CORE_LOW_VOLUME`;
- `OPTIONAL_METERED`;
- `FORBIDDEN_HIGH_FREQUENCY`.

`FORBIDDEN_HIGH_FREQUENCY` operations must never execute.

## CACE API rule

All scientific calls go through the typed CACE client.

Recommended location:

`webapp/src/api/caceClient.ts`

The UI must treat CACE-returned scientific/evidence/security fields as read-only authority.

## Base44 monthly-budget UX

Gemini must expose a small admin/status panel showing:

- configured monthly message-credit budget;
- configured monthly integration-credit budget;
- internal estimated usage counter if available;
- current policy zone: GREEN/YELLOW/RED/HARD_STOP;
- which optional Base44 features are disabled by policy.

The UI must not claim Base44's authoritative billing total unless the platform supplies that value through an official API. Local counters are estimates and must be labeled as such.

## Oracle free-VM UX

The admin/status surface should show CACE-returned:

- worker concurrency;
- CPU/RAM limits;
- storage pressure;
- sandbox preflight status;
- cgroup/sandbox capability status;
- recovery/attention items.

Do not infer these from browser timing.

## Offline/degraded behavior

If Base44 is unavailable or at HARD_STOP:

- scientific execution remains Oracle/CACE-backed;
- transient UI state remains local;
- non-critical metadata writes may queue locally;
- no scientific truth migrates to Base44/browser state.

## Credit-sensitive implementation rule

Do not use Base44 for:

- polling loops;
- canvas position updates;
- science-run progress;
- telemetry;
- AI chat;
- run artifacts;
- proof artifacts;
- high-frequency notifications.

Batch low-volume metadata changes where practical.

## Security

Never put Oracle credentials, proof-runner credentials, signing keys, or CACE secrets in Gemini-generated browser bundles or Base44 records.

## Required handoff after each Gemini batch

Report:

- changed files;
- CACE endpoints consumed/changed;
- Base44 operations added;
- expected monthly credit impact;
- tests;
- scientific/evidence impact;
- qualification-sensitive changes yes/no;
- unresolved obligations.
