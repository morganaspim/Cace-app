# CACE AI Collaboration / Repository Coordination Protocol

Status: engineering coordination infrastructure. This protocol does not create mathematical proof evidence.

## Baseline and scope

The collaboration layer coordinates AI agents through repository-tracked, content-addressable records while preserving CACE proof/qualification boundaries. A message, agreement, review, benchmark, or AI-generated argument is never promoted to theorem evidence merely because multiple agents agree.

The branch introducing this protocol is based on exact repository commit `ce2487e2a7b85c095e0926b11c97fc1c4eba5de8`. Qualification evidence remains bound to the exact commit identified by its qualification artifact; later collaboration commits do not retroactively qualify themselves.

## Evidence classes

Only these collaboration evidence labels are accepted:

- `AI_PROPOSAL`: suggestion, hypothesis, review, plan, analogy, or unverified derivation from an AI agent.
- `ENGINEERING_VERIFIED`: direct reproducible engineering evidence such as tests, builds, deterministic checks, or exact artifact/hash verification. This is not mathematical proof.
- `CERTIFIED_NUMERICAL`: result carrying a rigorous numerical enclosure/error certificate under explicitly recorded assumptions. It remains distinct from kernel proof.
- `PROVED`: claim backed by the canonical kernel-checked formal qualification chain and exact theorem identity. The collaboration record must point to that proof evidence; an AI cannot self-declare a claim `PROVED`.

## Exact-head rule

Every task, message, acknowledgement, and decision MUST record `base_sha` as a 40-hex Git commit identity. Before acting, an agent compares its task `base_sha` with the repository state it actually inspected. A mismatched record is stale and MUST NOT authorize a repository mutation or proof claim. The agent may create a new proposal describing the mismatch.

## Task leases

A task lease records one owner, one exact base SHA, scope, creation time, and state. Lease states are `OPEN`, `ACTIVE`, `RELEASED`, or `SUPERSEDED`.

A lease is coordination metadata, not a distributed lock guaranteed by GitHub. Agents MUST independently check GitHub Actions immediately before dispatching a CACE proof/development/release workflow. If any CACE workflow is active or queued, no additional CACE workflow may be dispatched.

## Append-only records

Messages and decisions are append-only files. Corrections create a new record referencing `supersedes`; existing records are not rewritten to change history. Each record contains a canonical `payload_sha256` over its semantic payload. SHA-256 supplies content identity/integrity; it does not establish mathematical truth.

Recommended IDs:

- message: `msg-YYYYMMDDTHHMMSSZ-<short digest>`
- decision: `decision-YYYYMMDDTHHMMSSZ-<short digest>`
- lease: `lease-YYYYMMDDTHHMMSSZ-<short digest>`

## Message lifecycle

1. Agent reads exact repository head and relevant evidence.
2. Agent validates task lease and `base_sha`.
3. Agent writes an `AI_PROPOSAL` or evidence-backed message.
4. A second agent may independently inspect and acknowledge it as `ACCEPT`, `MODIFY`, `REJECT`, or `NEEDS_EVIDENCE`.
5. A decision record cites the exact message IDs and evidence references.
6. Promotion to trusted CACE behavior follows the existing Discovery Ledger / qualification rules. Collaboration consensus alone cannot promote a claim.

## Discovery Ledger linkage

A collaboration record may reference a Discovery Ledger entry by immutable identifier/hash. If the referenced entry is unavailable, the record remains coordination evidence only. New scientific or mathematical implications must be independently reconstructed and verified before promotion.

## GitHub Actions serialization

Before dispatching any CACE Actions proof/development/release job, an agent MUST query repository-wide `queued` and `in_progress` workflow runs and confirm no CACE job occupies the lane. The check must be fresh at dispatch time. Agents do not cancel, replace, rerun, or mutate an active/queued job to acquire the lane.

## Failure and stale-state behavior

- stale base SHA: reject mutation/dispatch; emit a new proposal against current head.
- conflicting active leases: stop the conflicting task until reconciled; leases never override Actions serialization.
- missing proof evidence: downgrade to `AI_PROPOSAL` or the supported non-proof evidence class.
- hash mismatch: reject the record as invalid until regenerated.
- unavailable external agent: continue only work that does not rely on that agent's acknowledgement.

## Security and provenance

Do not place credentials, tokens, private keys, personal data, or secrets in collaboration records. External model names/versions and tool identities may be recorded as provenance when known. Imported model output remains empirical/proposal evidence unless separately certified under CACE rules.
