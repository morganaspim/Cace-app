# Base44 ↔ GitHub Two-Way Sync Architecture

Status: production architecture contract.

## Purpose

CACE should use Base44's two-way GitHub sync to accelerate customer-facing web
development without turning Base44 into the authority for scientific truth,
formal proof, wallets, secrets, or production databases.

The division of responsibility is:

```
Base44
  = customer-facing web/product builder + preview + early web checks

GitHub
  = canonical source history + PR review + CACE CI + release identity

Private CACE service plane
  = science + proofs + AI + native compute + private data + wallet custody
```

GitHub is the long-term canonical source. Base44 is a synchronized builder.

## Why two-way sync is valuable

When Base44 changes UI/product code:

`Base44 -> GitHub commit -> PR/diff -> CACE checks -> reviewed merge`

When Codex/Gemini/human developers change public contracts/UI code:

`GitHub reviewed commit -> Base44 sync -> builder/preview sees the same source`

This eliminates repeated manual copying and makes Base44 read the same durable
architecture that other coding agents use.

## Ownership zones

### Base44-owned

Base44 may edit directly:

- `web/**`
- `base44/**`
- `docs/base44/**`

These are presentation/product integration zones. They may not invent separate
scientific semantics.

### Joint review

These may be changed for product integration, but only through a normal GitHub
review and the applicable CACE checks:

- `api/**`
- `schema/public/**`
- `docs/help/**`
- public product docs;
- web/API regression tests.

The gateway remains server-authoritative and must continue to revalidate all
browser input.

### CACE-protected

Base44 must not directly edit:

- `formal/**`
- `cpp/**`
- `cace_studio/core/**`
- `cace_studio/modules/**`
- proof contracts/ledger/qualification code;
- account/trial authoritative logic;
- AI capability/sandbox logic;
- payment/wallet custody logic;
- Lean/proof workflows;
- machine security/payment/proof policies;
- agent/bootstrap/build-planner authority files.

If Base44 needs one of these changed, it must describe the required typed
API/schema contract and let the protected CACE implementation go through normal
review.

## GitHub branch/PR rule

Because a repository-connected Base44 project uses GitHub for version
management, CACE should use GitHub branches and pull requests as the development
control plane.

Recommended:

1. Base44 creates/syncs customer-facing changes.
2. Those changes are reviewed as GitHub commits/PRs.
3. CACE path-boundary checks classify the diff.
4. Base44-owned changes continue through web/product tests.
5. Joint/protected changes require the stronger owner/gate path.
6. Only a reviewed exact GitHub commit is eligible for CACE production.

If the Base44 GitHub integration cannot reliably stay within the monorepo
protected workflow, move Base44 to a dedicated `Cace-web` repository and share
versioned public API/schema contracts with `Cace-app`.

## Check hierarchy

Base44's own verification/security tools are useful early signals, but CACE
keeps its stronger hierarchy:

1. Base44 Verification
2. Base44 Testing Agent
3. Base44 Security Scan
4. CACE Build Lite
5. GitHub Python/C++/web/security/policy regression
6. qualification-drift / Exact-Pin Lean / audited-root checks
7. canonical exact-current-head qualification

A Base44 green check cannot create formal proof status.

## Database architecture

Two-way Git sync is for **schema and code**, never production data.

Version in Git:

- entity/schema definitions;
- migrations;
- public API/read-model contracts;
- non-sensitive test fixtures.

Never sync through Git:

- production users/sessions;
- experiment contents;
- proof/evidence payloads;
- private protein objects;
- raw feedback/contributions;
- wallet balances as authoritative state;
- wallet keys/seeds;
- payment credentials;
- telemetry.

Base44 may own or cache low-risk customer-facing data such as profile UX,
preferences, public help metadata, and receipt IDs.

The private CACE plane remains authoritative for:

- trial anti-abuse entitlement;
- scientific experiments/results;
- proof/evidence/provenance;
- private protein library;
- local-AI capabilities;
- Math Coin authoritative ledger;
- Monero/payment settlement;
- formal qualification evidence.

Base44 may receive a customer-facing read model, never proof/wallet authority.

## API boundary

Base44 browser/product code calls only reviewed typed public CACE APIs.

Example:

```
Base44 UI
   |
   | HTTPS/WSS public contract
   v
CACE Web Gateway
   |
   | typed private IPC
   v
CACE private services
```

Base44 should not connect the browser directly to:

- local AI/model servers;
- databases;
- wallet RPC;
- Lean runners;
- C++ workers;
- scientific worker queues;
- local filesystem services.

## Secrets

Two-way sync is never a secret transport.

Never put in Git/Base44 prompts/client bundles:

- private keys/seeds;
- Monero spend/view keys;
- wallet-RPC credentials;
- database credentials;
- signing keys;
- proof-runner credentials;
- production API secrets;
- model-control secrets.

Use server-side secret stores/connectors.

## Deployment authority

Base44 may deploy or preview the customer-facing app.

Base44 deployment is **not** permission to deploy/replace:

- CACE scientific runtime;
- formal qualification runner;
- wallet custody;
- local-AI authority service;
- native C++/GPU workers;
- private evidence/experiment storage.

A CACE production release should record the exact reviewed GitHub commit and the
checks/qualification appropriate to the changed surface.

## Protected-change handshake

When a Base44-generated feature needs protected functionality:

1. Base44 does not duplicate the private implementation.
2. Base44 records the typed API/schema it needs.
3. Protected CACE code is implemented/reviewed separately.
4. CI proves the protected change did not weaken architecture.
5. The reviewed public contract syncs back to Base44.
6. Base44 finishes the customer-facing flow.

This keeps two-way sync fast without making it a security bypass.

## Repository settings to enable manually

GitHub settings should require:

- pull requests for protected production branches;
- required CACE status checks;
- CODEOWNERS review on protected paths where supported;
- no Base44 integration bypass of branch protection;
- a repository variable `BASE44_GITHUB_ACTOR` once the actual app/bot actor is known.

If Base44-originated changes cannot be reliably identified, use a dedicated
Base44 integration branch/repository instead of allowing direct production-main
writes.

Machine-readable authority:
`CACE_BASE44_GITHUB_SYNC_POLICY.json`.
