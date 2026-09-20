---
name: cace-rigorous-tool-builder
description: Use when creating or improving CACE mathematical/scientific tools in C++, adding exact/certified checks, writing Lean proof attempts, source-to-formal bindings, or preparing proof-ready handoff packets.
---

# CACE Rigorous Tool Builder

Read first:
- `AI_CONTEXT/00_START_HERE.md`
- `GEMINI.md` / `.agents/AGENTS.md`
- `CACE_AI_BUILDER_CONTRACT.md`
- `docs/AI_RIGOROUS_TOOL_CONTRIBUTION_PIPELINE.md`
- `docs/CACE_RIGOROUS_MATH_KERNEL_V1.md`
- `docs/PROOF_BACKED_MATH_TOOLBOX_ROADMAP.md`
- `docs/proofs/SOURCE_TO_FORMAL_LINKAGE_SPEC.md`
- `collaboration/PROTOCOL.md`

## Workflow

1. Define semantic tool ID, types, assumptions, failures, evidence target.
2. Implement load-bearing exact/high-performance semantics once in C++.
3. Add unit, property, regression and adversarial tests.
4. Add exact/certificate checker when useful.
5. Add only thin Python/API bindings.
6. Attempt Lean theorem/proof and explicit runtime-to-formal representation binding when FORMAL is a target.
7. Never add axiom/sorry/unchecked assertions as a substitute for proof.
8. If proof closure remains, generate a `cace-ai-tool-submission-v1` packet with every unresolved obligation.
9. Validate it with `python scripts/validate_ai_tool_submission.py <packet.json>`.
10. Recommend the next gate; never self-declare FORMAL/PASS.

## Evidence boundary

Engineering tests, AI reasoning, heartbeat/perception, hashes and preflight are not canonical formal qualification.

The submission packet has `promotion_authority=false` by design.
