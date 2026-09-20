# ADR-002 — Oracle Is CI/Runner Only

Status: **accepted** — 2026-09-20

Supersedes the production-hosting portions of ADR-001.

## Decision

Oracle Cloud is reserved for CACE CI/runner workloads only.

Oracle may run:

- GitHub Actions self-hosted runner jobs;
- Lean/Mathlib builds and exact-head qualification;
- C++/Python build and regression jobs;
- source-secrecy/license/security release checks;
- CI artifact generation and retention staging.

Oracle must not be used for:

- the public production web application;
- the production CACE API/runtime;
- customer sessions/workspaces;
- customer scientific execution;
- payment handling;
- Base44 services;
- production databases or user artifact storage;
- production application secrets.

## Rationale

A self-hosted CI runner executes repository-controlled code and therefore has a
different threat model from a production application server. Keeping production
traffic and secrets off Oracle prevents CI jobs from becoming a path into
customer data or production credentials.

It also ensures expensive proof/build jobs cannot starve interactive users.

## Production topology

```text
Browser / Gemini-built presentation
        |
        | HTTPS / authenticated typed API
        v
Production CACE application/runtime
(non-Oracle host/service; exact provider selected separately)
        |
        +--> scientific runtime/workers
        +--> durable workspace/artifact storage
        +--> entitlement verification
        |
        +--> Base44 adapter (low-volume identity/membership/entitlement metadata)
        |
        +--> Cloud Run payment service (Monero only)

GitHub
  |
  v
Oracle CI runner
  -> tests / builds / Lean / qualification / release gates
  -> no production credentials or customer traffic
```

## Provider-neutral rule

Until the production CACE runtime host is deliberately selected, contracts should
say **Production CACE backend/runtime**, not Oracle/CACE.

Gemini must consume a configurable production API origin and must not hard-code
Oracle addresses, hostnames, or deployment assumptions.

## Security boundary

The production runtime and Oracle CI runner use separate:

- service identities;
- secrets;
- networks/firewall rules;
- storage credentials;
- signing/deployment credentials;
- logs and operational access.

A proof-submission PR or arbitrary CI checkout must never gain production
application credentials.

## Migration rule

Any canonical product document or machine manifest that still describes Oracle as
the interactive CACE runtime should be updated or marked historical. Historical
proof/run references to Oracle remain valid as CI evidence.
