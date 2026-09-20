# External Builder Connection Contracts

CACE currently recognizes two external product builders with deliberately different roles.

## Base44

Entrypoint:

- `BASE44.md`
- `BASE44_CONNECTION_MANIFEST.json`
- `base44/BASE44_TASK_STATE.json`

Role:

**low-volume commodity application services only**

Default direct-write area:

`base44/**`

Base44 does not build the scientific runtime, proof system, CACE web UI, event bus, telemetry path, or AI inference plane.

## Gemini / Google AI Studio Build Mode / Antigravity

Entrypoint:

- `GEMINI.md`
- `GEMINI_CONNECTION_MANIFEST.json`
- `gemini/CACE_GEMINI_TASK_STATE.json`

Role:

**primary browser/interface builder**

Default direct-write areas:

- `webapp/**`
- `gemini/**`

The existing `web/**` implementation is a fallback/reference and is read-only until the React replacement reaches tested feature parity and migration is explicitly approved.

## Branch rule shared by both

Both integrations must resolve branch permission through `BRANCH_LIFECYCLE.json`.

Only exact status `ACTIVE` is writable by default.

- `main` is read-only integration.
- `FROZEN` is read/compare only.
- `DEPRECATED` and `ARCHIVED` must not be used as work bases.
- unknown branches are `REVIEW_REQUIRED`.

Neither integration may force-push, merge PRs, or delete branches by default.

## Permission escalation

If a task genuinely requires a path outside the default direct-write allowlist:

1. stop;
2. identify the exact file/path and reason;
3. classify the change under CACE governance;
4. obtain explicit user/ChatGPT task permission;
5. run the appropriate tests/rigor gates;
6. remove the temporary permission after the task.

Permission escalation never grants proof/evidence authority.

## Authority

Gemini and Base44 are implementation/service providers.

Oracle/CACE remains authoritative for:

- scientific execution;
- verification;
- certificates;
- sandbox/security state;
- proof/claim governance;
- formal qualification.

The machine manifests are coordination/security policy, not mathematical evidence.
