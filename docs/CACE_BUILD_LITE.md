# CACE Build Lite

Status: executable low-cost build planner for humans and coding agents.

## Purpose

CACE Build Lite is a deliberately small version of CACE for **building CACE itself**.

It does not run the scientific GUI, own proof truth, or try to autonomously rewrite the repository. Instead, a coding agent such as Base44, Gemini AI Studio, Codex, or another GitHub-connected builder can call one deterministic planner before spending compute.

Build Lite answers:

- which checks are impacted by the changed files;
- which dependencies must run first;
- which exact-content cache hits are reusable;
- which tasks can run in parallel;
- the resource-bounded batch order;
- the longest/critical build path;
- which cheap fail-fast checks should run before expensive work.

## Mathematical core

The planner models build tasks as a directed acyclic graph.

For task `v`:

- `c(v)` is estimated wall-clock cost;
- `r(v)` is CPU/resource demand;
- dependencies define precedence constraints;
- reverse reachability estimates how many later tasks a task unlocks;
- the critical path is the maximum-cost path through the selected DAG.

Ready tasks are ranked deterministically by:

1. fail-fast status;
2. critical-path membership;
3. downstream unlock count;
4. explicit priority;
5. inverse estimated cost.

Then a greedy resource-bounded scheduler packs ready tasks into parallel batches subject to `cpu_budget` and `max_parallel`.

This is intentionally inexpensive: graph traversal, hashing, and deterministic scheduling rather than LLM search.

## Exact cache behavior

For ordinary engineering tasks, Build Lite may skip a task only when:

- its cache policy explicitly permits skipping; and
- the exact content fingerprint matches a previously successful fingerprint.

Formal/proof-sensitive tasks are different:

- an exact cache hit is marked **restore-only**;
- the formal task stays in the plan;
- Build Lite never treats a cache artifact as proof/qualification truth.

This preserves the CACE rule: caches accelerate proof runs but never create evidence.

## CLI

Quick development plan from git changes:

```bash
python scripts/cace_build_lite.py \
  --repo . \
  --git-base origin/main \
  --profile quick \
  --commands
```

Merge-quality plan:

```bash
python scripts/cace_build_lite.py \
  --repo . \
  --git-base origin/main \
  --profile merge \
  --commands
```

Formal work:

```bash
python scripts/cace_build_lite.py \
  --repo . \
  --git-base origin/main \
  --profile proof \
  --commands
```

The command prints JSON so an AI code builder can consume it without scraping prose.

## Coding-agent contract

Before a substantial CACE code change, a capable code builder should:

1. read `AGENTS.md`, `CACE_AGENT_BOOTSTRAP.json`, and `CACE_BUILD_LITE.json`;
2. make the smallest coherent code change;
3. run Build Lite with the actual changed paths;
4. execute cheap batches first;
5. reuse only exact successful caches allowed by policy;
6. stop/fix on fail-fast failures;
7. defer expensive GitHub/Lean jobs until Build Lite says their dependency gates are ready;
8. never use Build Lite output as proof evidence.

## Why this helps Base44 / Gemini AI Studio

The app builder does not need to ingest the entire scientific application into an expensive reasoning loop merely to decide what to test next.

It can invoke one small Python process, receive a compact JSON build plan, then spend model/tool compute only on the selected frontier. This makes CACE itself useful as a mathematical build optimizer while keeping the optimization layer small enough for frequent use.
