---
name: cace-local-agent-runtime
description: Implement or review CACE local agentic AI, provider adapters, typed tools, zero-contact mode, heartbeats/checkpoints, Research Agent, Grow, or specialist-agent coordination.
---

# CACE Local Agent Runtime Skill

Before work, read:
- `AI_CONTEXT/00_START_HERE.md`
- `AI_CONTEXT/IMPLEMENTATION_PLAN_A_I.md`
- `docs/CACE_LOCAL_AGENT_RUNTIME.md`
- `docs/CACE_AGENT_HEARTBEAT_PROTOCOL.md`
- `AGENTS.md`
- `CACE_AI_BUILDER_CONTRACT.md`

Keep context pulls <= 800 files and use deterministic source shards.

Hard rules:
- provider-independent runtime;
- real Local / Zero Contact path;
- typed/capability-scoped tools;
- checkpoints + monotonic heartbeats;
- liveness != progress != verification;
- no AI-authored PASS/VERIFIED/FORMAL;
- adversarial tests for truncation, network denial, stale heartbeat, loops, budgets, checkpoint recovery, and evidence-isolation attempts.
