# Base44 Instructions for CACE

You are building the customer-facing/product surface of CACE through two-way
GitHub sync.

Read first:

1. `CACE_BASE44_GITHUB_SYNC_POLICY.json`
2. `AGENTS.md`
3. `CACE_CODE_BUILDER_BOOTSTRAP.json`
4. `CACE_AGENT_BOOTSTRAP.json`
5. `CACE_DEPLOYMENT_BOUNDARY.json`
6. `docs/BASE44_GITHUB_SYNC_ARCHITECTURE.md`

## Your normal write zone

You may directly build in:

- `web/**`
- `base44/**`
- `docs/base44/**`

## Review-required integration zone

Changes to `api/**`, public schemas, and customer-help contracts require
GitHub review and CACE CI.

## Do not directly modify

Do not directly change formal proof source, proof contracts/ledger, canonical
qualification, scientific kernels/modules, C++ runtime, wallet/payment custody,
AI sandbox/capability authority, authoritative account/trial logic, secrets,
security/payment/proof policies, or agent/bootstrap/build-planner authority.

If your feature needs one of those changes:

1. keep the protected implementation intact;
2. describe the typed API/schema capability you need;
3. rank viable public-contract approaches if needed;
4. let the protected CACE implementation go through review;
5. continue after the reviewed contract syncs back.

## Truth rules

- UI confidence is not scientific evidence.
- Base44 Verification/Security Scan is not formal proof.
- Browser/client state is untrusted.
- Base44 must never create PASS/VERIFIED/formal qualification.
- Never move wallet keys, secrets, proof authority, private scientific data, or
  proprietary theorem machinery into the browser just to simplify generation.

## Database rules

Git contains schema/migrations/test fixtures, not production rows.

Base44 may hold customer-facing profile/preferences/read-model data. The private
CACE plane remains authoritative for experiments, proof/evidence, wallet state,
trial anti-abuse, private protein content, local-AI capabilities, and formal
qualification.

## Completion rule

A feature is complete only when:

- the customer-facing flow works;
- changed paths respect this ownership contract;
- CACE Build Lite selects the correct checks;
- required GitHub engineering/security checks pass;
- proof-sensitive changes, if any, follow formal qualification separately.
