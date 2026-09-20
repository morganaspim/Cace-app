# CACE Production VRE Closure Plan

Status: production-readiness plan. Not proof evidence.

CACE is **not yet finished as a production multi-user VRE**. The proof/agent architecture is strong, but several production closure items remain.

Canonical checklist: `ops/production_vre_closure.json`.

## Highest-priority closure

1. Merge/freeze the current architecture baseline.
2. Implement the durable authenticated multi-user workspace/run backend.
3. Separate production runtime trust from CI/self-hosted runner trust.
4. Add tested backup/restore/disaster recovery.
5. Add observability, rate limits, quotas and operational alerts.
6. Build a scientific validation matrix for every production module.
7. Make every result reproducible from a provenance bundle.
8. Add supply-chain/release security.
9. Complete the Monero payment + signed-entitlement production gate.
10. Run multi-user/load/crash/recovery campaigns.

## What Gemini should do

Lean heavily on Gemini for **presentation and integration engineering**:

- React/TypeScript CACE interface;
- typed API clients;
- drag/drop graph UX;
- reconnectable multi-user UI;
- queue/run status;
- proof/evidence presentation;
- Base44 accounts/entitlements UI;
- Monero checkout UI;
- help/examples/onboarding;
- admin dashboards;
- browser/load/reconnect tests;
- accessibility and cross-browser QA.

Gemini may also write detailed API-extension requests under `gemini/requests/**`.

Do not make Gemini the scientific/proof/security authority.

## Scientific VRE release gate

A scientific module is not production-grade merely because it runs.

Before marking a module production-ready, require:

- explicit input/output units/types;
- assumptions and validity domain;
- reference problem(s);
- manufactured solution/convergence test where applicable;
- invariant/conservation test where applicable;
- expected numerical tolerance/error envelope;
- negative/invalid-input tests;
- deterministic/reproducibility metadata;
- evidence/proof status mapping;
- limitations;
- example workflow.

The formal proof layer and numerical validation layer complement each other; neither substitutes for the other.

## CI vs production security

A self-hosted GitHub Actions runner executes repository-controlled code. Once CACE accepts external proof/code submissions, treating that runner as a production application host is an unnecessary trust coupling.

Production CACE secrets and customer data must not be available to a general-purpose self-hosted CI runner.

Prefer separate hosts/identities. If only one free machine is available during development, do not call that layout production-grade.

## Oracle

Oracle Always Free is useful, but constrained. The official Always Free documentation currently describes an A1 allocation equivalent to 2 OCPUs + 12 GB RAM total and 200 GB combined boot/block storage.

That is enough for an alpha/small VRE with bounded jobs, not for unlimited concurrent science.

The production scheduler must therefore queue heavy jobs and preserve API responsiveness.

See `docs/ORACLE_ALWAYS_FREE_RESOURCE_POLICY.md`.
