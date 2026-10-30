# CACE Antigravity Instructions

Read root `AGENTS.md` first, then `AI_CONTEXT/00_START_HERE.md` and `AI_CONTEXT/IMPLEMENTATION_PLAN_A_I.md`.

## Context limit

Never request more than 800 repository files for one working context. If the candidate set is larger, split it into deterministic source shards. Do not trust silently discarded files.

## Role

Antigravity is a preferred implementation/orchestration environment for CACE. It is not scientific/proof evidence and is not a mandatory dependency of the finished Local AI.

Use the A–I plan plus `docs/GOAL_REGISTRY.json` and `docs/CHAT_IDEA_LEDGER.md` to preserve all implementation goals and research ideas.

## Hard boundaries

- AI cannot create PASS/VERIFIED/FORMAL.
- Heartbeats are liveness/progress/attention metadata, never evidence.
- Browser code is presentation only.
- C++ owns load-bearing exact/high-performance kernels.
- Python owns orchestration/API.
- Lean owns formal theorem/qualification authority.
- Local / Zero Contact AI must remain possible with no required cloud/network dependency.
- Preserve explicit hypotheses, NOT_RUN, stale and unresolved obligations.


## Rigorous Tool Builder

Antigravity may create and improve canonical CACE math/science tools.

Use `.agents/skills/cace-rigorous-tool-builder/SKILL.md` and `docs/AI_RIGOROUS_TOOL_CONTRIBUTION_PIPELINE.md`.

Allowed work includes C++ implementation, C++ tests, exact/certified checkers, thin Python bindings, Lean theorem statements/proofs, and source-to-formal bindings.

If formal closure is incomplete, produce a validated packet conforming to `collaboration/schema/cace-ai-tool-submission.schema.json` with explicit unresolved obligations and recommended next gate.

Antigravity never has promotion authority. Canonical qualification is separate.

## Canvas perception

Use `schema/cace-agent-perception.schema.json` for the compact live experimental state stream. It may guide attention/planning but never evidence promotion.

## MCFC–CACE project investigation skill (research)

For MCFC–CACE project goal interpretation, project-only source recall, case-study mathematics and abductive scientific inquiry, see `.agents/skills/merlin-project-investigator/SKILL.md` and its partial-context reference. This skill is advisory; first perform the usual Tier-0 source loading and engineering specifications. It adds no proof promotion, runtime authority, runner access, or permissions. The CACE rigorous-tool-builder skill and all evidence/qualification rules remain authoritative.

## Project-only M.E.R.L.I.N. pre-PR fail-fast coding rule

For **every MCFC–CACE software change** created by ChatGPT or M.E.R.L.I.N., load `.agents/skills/merlin-failfast-bugflush/SKILL.md`, write engineering requirements before coding, use RED–GREEN–REFACTOR, and clear bug families permanently. Before opening/pushing a PR, run `python -m scripts.cace_prepr_gate --base-ref origin/main --change-kind feature --profile quick` (select the truthful change kind). Do not waive failures by renaming tests or altering proof/security gates. Follow `docs/PRE_PR_FAIL_FAST_AND_BUG_CLEARING.md`. No other user project inherits this rule automatically.
