# M.E.R.L.I.N. Investigative Reasoning v14 — Implementation Handoff

**Status:** DRAFT RESEARCH SKILL, not production or proof qualification.

## Current state
- Repo skill in `.agents/skills/merlin-project-investigator/SKILL.md`, linked by `.agents/AGENTS.md`, with project-only reference.
- Durable research goals G080/G081 and idea ledger I092–I095.
- Separate local artifact `MERLIN_Project_Investigative_Skill_and_Context_v14.zip` produced in the originating MCFC–CACE chat. It contains verbose project-only summaries and mathematical explanations, a ChatGPT Project-instructions patch, source-coverage statement, historical learning cases, a deterministic source-aware investigator and the prior v13 bounded intent planner.
- **38 local tests** of v14 investigative core and bridge plus **24 inherited v13 tests** passed. This is not current CACE repo CI, science validation or proof verification.
- Complete raw project chat archive not ingested. The summarized project-only context is an index, not a verified claim ledger.

## Engineering requirements
1. User intent must become an EngineeringSpec with objective, inputs, acceptance tests, limits, permissions, source and failure modes before tool planning.
2. Record source genealogy; copied secondary reports must not count as separate independent observations.
3. Generate competing explanations including OTHER_UNMODELED; ranking is HEURISTIC_NOT_PROBABILITY unless explicit priors and model likelihoods justify probability.
4. Mandatory source audit, counterexample, privacy-consent lenses; conditional task-specific mathematical, causal, cultural, geospatial, ethical, power or security lenses; lenses cannot change truth or action permissions.
5. Only caller-registered read-only tools execute in local prototype; changed plans and missing tools are blocked. Separate trusted executor would require an approval/authorization receipt.
6. Formal proof, physical measurement, numerical computation, model proposal, history and user intent remain different typed records. Only canonical CACE proof and claim subsystems decide verification.
7. Historical-critical + Feynman method: pioneer problem; documented aims; first-principles reconstruction; simple teach-back; strongest rival/counterexample; independent test.
8. Source-linked project memory, correction/deletion, no inferred personality diagnosis or private precise-person geolocation by default.
9. Output governor chooses answer, clarification, draft or hold according to stakes; no auto-send or publish.

## Acceptance plan
A. Review skill and context for faithful source coverage and project privacy. 
B. Port tested advisory module into CACE `cace_studio/ai` only after reading actual repo interfaces and avoiding duplicate scientific semantics.
C. Run CACE current-head Python and adversarial tests + documented API integration, not only the local v14 tests.
D. Compare blind held-out investigations against single-model/less-complex baseline: accuracy, missing explanations, false certainty, copied-source detection, correct tool/permission routing, cost.
E. Keep no-automatic-PASS, no hardware control, no independent runner/certificate authority, and explicit manual review/rollback.
F. If qualification-sensitive source changes, run full required CACE exact-head qualification and drift audit separately.

## References
- `AGENTS.md`, `AI_CONTEXT/00_START_HERE.md`, `AI_CONTEXT/IMPLEMENTATION_PLAN_A_I.md`, `CACE_AGENT_BOOTSTRAP.json`, `docs/GOAL_REGISTRY.json`, `docs/CHAT_IDEA_LEDGER.md`, `docs/MASTER_BUILD_SPEC.md`.
- https://plato.stanford.edu/entries/abduction/
- https://www.nist.gov/spo/forensic-science-program/forensic-science-research/evidential-statistics
- https://humanrights.berkeley.edu/publications/evaluating-digital-open-source-imagery-a-guide-for-judges-and-fact-finders/
