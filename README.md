# CACE Studio — Verified Research Environment

> **CONFIDENTIAL AND PROPRIETARY**  
> **Owner:** Emmanuel Spiro  
> **Copyright © 2026 Emmanuel Spiro. All rights reserved.**  
> Original CACE materials are proprietary. Third-party/open-source components retain their own licenses and notices. See `LICENSE` and `NOTICE`.

CACE Studio is a modular scientific research environment combining a visual typed experiment graph, Python orchestration, native C++ kernels, reproducible run certificates and selectively formalized mathematics in Lean.

**Current software version:** `3.30.0.dev1`  
**Current development focus:** v3.31 truth/formal qualification  
**Production readiness:** **not established**

The project deliberately separates software maturity from evidence strength. A numerical test, exact checker, interval certificate and Lean theorem are different kinds of evidence. `NOT_RUN` or absent verification is never treated as `PASS`.

## Start here

- `BRANCH_LIFECYCLE.json` — canonical branch status registry; only ACTIVE branches are writable by agents
- `THIRD_PARTY_NOTICES.md` + `docs/LICENSE_COMPLIANCE.md` — third-party dependency/license inventory and fail-closed release compliance gate
- `BASE44.md` + `BASE44_CONNECTION_MANIFEST.json` — Base44 connection entrypoint, responsibilities, credit-aware build scope and strict repository permissions
- `GEMINI_CONNECTION_MANIFEST.json` — Gemini/AI Studio build program, branch/file permissions and protected CACE boundaries
- `docs/EXTERNAL_BUILDER_CONNECTIONS.md` — shared connection/permission escalation overview
- `docs/GEMINI_MULTI_USER_SESSION_CONTRACT.md` — reconnectable concurrent-session UX, workspace isolation and fair queued science
- `gemini/requests/MULTI_USER_CONCURRENT_SESSION_API.md` — required Oracle/CACE backend extensions before multi-user production readiness
- `docs/CLOUD_RUN_MONERO_PAYMENT_DEPLOYMENT.md` — payment-only Cloud Run deployment contract; no general CACE hosting/edge use
- `ops/cloud_run_payment_service_policy.json` — canonical payment-only Cloud Run responsibility/route/security policy
- `ops/cloud_run_cost_guard.json` — fail-closed Cloud Run payment-service budget/scaling/deployment guard; disabled by default
- `ops/cloud_run_edge_policy.json` — deprecated compatibility tombstone explicitly disabling general Cloud Run edge use
- `docs/MONERO_PAYMENT_CLOUD_RUN_CONTRACT.md` — Cloud Run Monero payment verification + Base44 payment history + signed entitlement architecture
- `ops/monero_payment_policy.json` — server-side payment, confirmation, promotion, and entitlement rules
- `gemini/requests/MONERO_PAYMENT_ENTITLEMENT_API.md` — Gemini checkout/history UI contract
- `schema/cace-payment-entitlement-grant.schema.json` — signed paid-feature entitlement payload
- `docs/PROOF_PROMOTION_EXTERNAL_COMPATIBILITY.md` — proof promotion compatibility boundary for Gemini/Base44
- `docs/PRODUCTION_VRE_CLOSURE_PLAN.md` + `ops/production_vre_closure.json` — production VRE release blockers, owners, and gates
- `gemini/VRE_CLOSURE_HANDOFF.md` — ordered Gemini production-closure batches
- `base44/BASE44_TASK_STATE.json` — minimum ordered Base44 service build plan
- `gemini/CACE_GEMINI_TASK_STATE.json` — Gemini implementation prerequisites and live task state
- `docs/BRANCH_LIFECYCLE.md` — branch deprecation/freeze/archive policy and recovery rules
- `GEMINI.md` — Gemini / Google AI Studio entrypoint; browser presentation must consume CACE's typed API/core rather than duplicate scientific/proof semantics
- `docs/GEMINI_AI_STUDIO_HANDOFF.md` — explicit web integration topology, ownership matrix and migration batches
- `docs/architecture/ADR-001-GEMINI-BASE44-ORACLE-CACE.md` — accepted product split: Gemini interface, Base44 commodity services, Oracle/CACE scientific authority
- `docs/BASE44_CREDIT_POLICY.md` — free-tier monthly Base44 budget and hard-stop policy
- `docs/ORACLE_ALWAYS_FREE_RESOURCE_POLICY.md` — free-VM CPU/RAM/storage/concurrency guardrails
- `docs/PROOF_SUBMISSION_REVIEW_WORKFLOW.md` — UI/Gemini proof candidates → GitHub draft PR → normal rigor → human review; Enterprise prove-first/sell-second path
- `docs/BASE44_ACCOUNT_ENTITLEMENT_CONTRACT.md` — Base44-facing Basic/Researcher/Enterprise benefits and UI entitlement rules
- `ops/base44_account_tiers.json` — machine-readable account tier/benefit manifest
- `ops/pass_promotion_policy.json` — recurring Tuesday/Saturday pass-sale pricing and eligibility rules
- `CACE_AGENT_BOOTSTRAP.json` — single machine-readable repository handoff
- `docs/BUILD_AND_TRUST_GUIDE.md` — unified build, rigor, security, bug-flush and provenance architecture
- `docs/STATUS.md` — current implementation and qualification state
- `docs/ARCHITECTURE.md` — system boundaries and trusted-computing-base model
- `docs/SECURITY_ARCHITECTURE.md` — security trust zones, threat boundaries and isolation policy
- `docs/CONSTITUTION.md` — non-negotiable scientific/software rules
- `docs/CLAIMS.md` — canonical claim registry/proof-ledger policy
- `docs/BUG_FLUSH_ARCHITECTURE.md` — defect-class prevention and permanent guardrail loop
- `docs/ROADMAP.md` — v3.31 through v4.0 dependency-ordered roadmap
- `docs/AI_QUICKSTART.md` — headless usage for tools and AI agents
- `AGENTS.md` — repository instructions for coding/research agents
- `AI_REPO_MAP.json` — machine-readable repository navigation
- `docs/PROVENANCE_ATTESTATION.md` — later-phase immutable provenance/distributed-attestation design
- `docs/HISTORY.md` — historical milestone notes; not current evidence

## Quick start

```sh
python -m pip install -e '.[test]'
python -m cace_studio.cli registry
python -m cace_studio.cli run examples/verified_quadratic.cace --output report.json
```

For the full native/Python qualification path, build and test the C++ runtime before running the complete Python suite. Formal qualification additionally uses the pinned Lean project in `formal/cace_formal/` and the v3.30 formal workflow.

## Core repository areas

`cace_studio/core/` contains graph execution, verification/certificates, serialization and claim/proof governance. `cace_studio/modules/` contains scientific modules. `cace_studio/gui/` contains the PySide6 visual playground. `cpp/` contains native kernels. `formal/cace_formal/` contains Lean sources. `tests/` contains behavioral/regression tests. `schema/` contains machine-readable contracts.

## Formal-evidence rule

A module returning `FORMAL + PASS` is not sufficient for public formal evidence. CACE preserves formal PASS only when the canonical claim registry and proof ledger agree on a valid content-addressed qualification, workflow provenance and source state, and the qualification-drift checker confirms that no proof-sensitive source has changed since the attested commit.

Historical successful runs therefore do not automatically qualify later source revisions.

## AI rule

AI is optional. CACE execution and verification must work without an AI service. AI may help explain, propose or construct research workflows, but AI output is not evidence and cannot set formal proof status.

## Scientific scope

CACE includes research work across certified FEM/PDE methods, graph-space/continuum analysis, geometric/Clifford algebra, numerical/HPC kernels, coordinate/tiling systems and additional experimental scientific modules. Each capability must be judged by its own documented assumptions, tests, evidence class and maturity. CACE does not claim resolution of famous open problems from simulations, benchmarks or incomplete formal reductions.
