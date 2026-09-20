# CACE AI Context Pack — START HERE

Status: implementation/governance navigation only. This file is not scientific, proof, qualification, or production evidence.

## Why this exists

Gemini AI Code / Google AI Studio and Google Antigravity must be able to reconstruct CACE implementation intent without loading the entire repository or relying on private chat history.

**Hard context-budget rule:** never request or ingest more than **800 repository files in one context pull**. The user has observed that Gemini can retain at most about 1000 files and silently discard overflow. CACE therefore reserves a safety margin and treats 800 as the maximum planned pull.

If a requested set would exceed 800 files, **do not continue with a truncated set**. Split the work into deterministic shards and record which shard is active.

## Tiered loading protocol

### Tier 0 — mandatory context pack

Read these first, in this order:

1. `AI_CONTEXT/00_START_HERE.md`
2. `AI_CONTEXT/IMPLEMENTATION_PLAN_A_I.md`
3. `CACE_AGENT_BOOTSTRAP.json`
4. `AGENTS.md`
5. `GEMINI.md`
6. `CACE_AI_BUILDER_CONTRACT.md`
7. `docs/MASTER_BUILD_SPEC.md`
8. `docs/GOAL_REGISTRY.json`
9. `docs/CHAT_IDEA_LEDGER.md`
10. `docs/CROSS_CHAT_HANDOFF.md`
11. `docs/STATUS.md`
12. `docs/ARCHITECTURE.md`
13. `docs/CONSTITUTION.md`
14. `docs/CLAIMS.md`
15. `docs/BUILD_AND_TRUST_GUIDE.md`
16. `docs/CACE_RIGOROUS_MATH_KERNEL_V1.md`
17. `docs/PROOF_BACKED_MATH_TOOLBOX_ROADMAP.md`
18. `docs/SCIENCE_MODULE_COMPLETENESS_STANDARD.md`
19. `docs/proofs/SOURCE_TO_FORMAL_LINKAGE_SPEC.md`
20. `gemini/CACE_GEMINI_TASK_STATE.json`
21. `AI_REPO_MAP.json`

For Antigravity also read `.agents/AGENTS.md` and use the relevant skill under `.agents/skills/`.

Tier 0 is the canonical **intent pack**. It contains the implementation plan, all durable goals, the append-only idea ledger, current status, proof/evidence rules, and navigation to implementation source.

### Tier 1 — active A–I track

Read only the plan/docs/source indexes required by the active A–I track from `AI_CONTEXT/IMPLEMENTATION_PLAN_A_I.md`.

### Tier 2 — task source shard

Use `AI_REPO_MAP.json`, generated indexes, exact paths referenced by the active plan item, and dependency/test ownership to select the minimal source/test set.

Target: <= 500 source/test files per batch.
Absolute planned maximum: 800 total files including Tier 0.

Do not bulk-load build output, caches, binary artifacts, historical archives, vendored dependency trees, generated package caches, or unrelated domains.

## Coverage rule: all ideas must remain visible

Two files together are the durable idea source:

- `docs/GOAL_REGISTRY.json` — mature/accepted implementation goals.
- `docs/CHAT_IDEA_LEDGER.md` — append-only meritorious ideas, including research ideas not yet promoted into implementation goals.

An AI builder must never infer that an idea was rejected merely because it is not in the current implementation batch. Deferred/research ideas remain preserved in the ledger.

When a new idea has merit:
1. preserve it in the idea ledger;
2. promote it to `GOAL_REGISTRY.json` when it becomes durable implementation intent;
3. map it to an A–I track or explicitly mark it cross-cutting/later;
4. never upgrade evidence/proof status through documentation.

## Implementation contract

Before coding a batch, the builder should emit or internally maintain:

- active A–I track;
- exact goal IDs / idea IDs being implemented;
- exact source commit;
- files selected for the source shard;
- file count;
- qualification-sensitive paths: yes/no;
- acceptance tests;
- unresolved obligations.

After coding, report:

- changed files;
- goals/ideas covered;
- tests run and results;
- scientific/evidence impact;
- qualification-sensitive files changed;
- remaining plan items;
- next recommended batch.

## No silent truncation

If any environment reports that files were discarded, context was truncated, indexes are incomplete, or the active source shard cannot be proven complete for the task:

**STOP implementation and rebuild a smaller deterministic shard.**

Never guess the contents of discarded files.

## Authority

Implementation plan/idea coverage is not proof evidence. Scientific/formal truth still comes from exact source, canonical claim/proof data, Lean source, and exact qualification artifacts.
