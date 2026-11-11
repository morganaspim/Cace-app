# Merlin Mathematics & Computational Learning System — Foundation

Status: implementation contract / proposal. This document is not evidence that an LMS runtime, learner database, or production deployment exists.

## Product objective

Build an adaptive mathematics learning system that develops three complementary capabilities:

1. **Mathematician** — formulate questions, notice structure, make conjectures, construct examples/counterexamples, reason rigorously, and communicate proofs.
2. **Mathematics programmer** — translate mathematical ideas into executable models, algorithms, numerical experiments, symbolic computation, and verified software.
3. **Computational hacker / problem solver** — decompose unfamiliar problems, inspect systems, use tools, test hypotheses, debug, automate, and explain solutions (a CS50-inspired practical path, not a copy of its course materials).

A learner may follow one path or a weighted blend. The system must not force a single identity or assume that speed, grades, or prior credentials equal mastery.

## Architecture boundary

The LMS is a Merlin learning domain, not a second mathematical authority.

- **Learning domain:** goals, learner preferences, pathway plans, prerequisite graph, exercises, attempts, feedback, and progress projections.
- **CACE domain:** mathematical execution, numerical evidence, exact checking, Lean compilation, proof artifacts, and canonical evidence/claim governance.
- **Hermes:** task decomposition, scheduling, tutor/agent assignment, and bounded execution requests.
- **Logos:** skeptical review, ambiguity detection, counterexample prompts, and critique of explanations.
- **Presentation:** lesson, exercise, graph, visualization, and conversation UI. It may render state but cannot promote mathematical truth.
- **Evidence bridge:** every external verification result is imported as a typed, source-bound receipt. A learner's answer, model-generated explanation, or visualization is never itself a proof.

No browser-side proof engine, duplicated CACE semantics, or AI-only pass state is permitted.

## Learner model

Persist only information needed to improve instruction:

- learner-controlled goals and interests;
- pathway weights and current learning objectives;
- concept-level state: unknown, introduced, practicing, provisional, mastered, or needs_review;
- evidence supporting each state, including task, rubric, timestamp, source/version, and verifier type;
- misconceptions and unresolved prerequisite gaps;
- preferred explanation modes and accessibility/pace settings;
- learner-visible history and correction/appeal events.

A concept becomes mastered only under a versioned mastery policy with multiple independent demonstrations, including transfer to a new context when appropriate. A single correct answer or AI judgment is insufficient. Decay or review scheduling may lower a recommendation priority, but must not erase historical evidence.

## Curriculum graph

Represent curriculum as a directed, typed graph:

- concept nodes: definitions, structures, theorems, techniques, and computational ideas;
- skill nodes: proof construction, estimation, abstraction, debugging, and algorithm design;
- task nodes: lesson, exercise, project, experiment, proof, and reflection;
- resource nodes: textbook section, open lecture, video, article, and interactive notebook;
- typed edges: requires, introduces, practices, assesses, generalizes, contrasts, implements, proves, and visualizes.

Prerequisites are explicit and versioned. The planner may recommend a bridge task when a prerequisite is missing; it must not silently skip a critical prerequisite. Concepts can belong to multiple pathways.

## Adaptive planning loop

1. **Observe:** collect the learner's stated goals, interests, prior work, diagnostic responses, and task outcomes.
2. **Infer cautiously:** update concept estimates with evidence provenance and confidence; preserve unknown/ambiguous states.
3. **Enumerate:** generate a bounded candidate set of next tasks across the three pathways and relevant prerequisite bridges.
4. **Rank:** score candidates by prerequisite readiness, learning value, transfer potential, learner interest, diversity, time/effort, and accessibility constraints.
5. **Explain:** show why a task is recommended, what it develops, prerequisites, expected effort, and what evidence will count.
6. **Teach/practice:** offer concise explanation, worked example, Socratic prompts, exploratory activity, coding lab, or proof task.
7. **Audit:** use skeptical review and targeted counterexamples; distinguish conceptual error from notation, execution, or environment failure.
8. **Verify:** invoke the appropriate checker or human rubric. Record exact evidence type and tool/version.
9. **Reflect/update:** ask the learner to explain what changed; update the plan only from observed outcomes and explicit preferences.

Planning is multi-objective, not a single opaque score. Keep component scores and reason codes in the plan record. Do not optimize only for streaks, time-on-platform, or answer speed.

## Pathway design

### Mathematician

Discovery before formalization: concrete cases, pattern observation, definitions, conjecture, counterexample search, proof strategy, proof writing, peer/skeptical review, and generalization. Include historical context and the methods of mathematical pioneers as intellectual case studies, not authority substitutes.

### Mathematics programmer

Map concepts to algorithms and representations: exact arithmetic, symbolic algebra, numerical methods, complexity, data structures, simulation, visualization, reproducibility, and property-based testing. Numerical agreement is experimental evidence, not proof.

### Computational hacker / problem solver

Use practical challenge cycles: understand the problem, decompose, inspect inputs/tools, form a hypothesis, implement a minimal test, debug, measure, improve, and communicate. Include command-line literacy, programming fundamentals, data handling, APIs, algorithmic thinking, and responsible security boundaries.

Each task can contribute to multiple pathways with separate rubric dimensions.

## Exercise and assessment contract

Every task declares:
- stable ID and version;
- objective/concept/skill links;
- pathway contributions;
- prerequisite IDs;
- task type and estimated effort;
- prompt, allowed tools, and accessibility alternatives;
- rubric dimensions and scoring policy;
- acceptable evidence types;
- hint policy and solution-release policy;
- deterministic fixtures or seeds where applicable;
- provenance for external resources.

Attempt records preserve the learner's submitted work, environment/tool versions when relevant, feedback, rubric scores, and verifier receipts. Do not store secrets or unnecessary personal data. A failed run due to infrastructure is not a learner failure.

## Evidence and proof levels

Keep these distinct and visible:

- self_report — learner says they understand;
- explanation_review — rubric-based review of reasoning;
- automated_test — executable checks within stated scope;
- numerical_experiment — finite computation under recorded assumptions;
- symbolic_or_exact_check — checker-specific exact result;
- lean_compile — exact Lean source/toolchain compile result;
- cace_qualified_claim — canonical CACE claim/receipt verified for the exact artifact and source state;
- human_review — identified reviewer and rubric.

A lean_compile receipt does not automatically mean a learner's entire solution is proved; the theorem statement, hypotheses, source digest, toolchain, dependencies, and checker output must be bound. Only CACE's canonical gate can label a claim formally qualified. LMS progress is pedagogical state, never proof authority.

## Video and external resources

Use video as an optional supplement selected by concept, level, language, accessibility, duration, and learner interest. Store title, provider, canonical URL, creator, publication date if known, duration if known, transcript/caption availability, license/usage notes, concept mapping, and retrieval timestamp. Do not assume availability or license from a title. Prefer official/open educational resources and provide a non-video alternative. Never make a video required when equivalent accessible text is unavailable.

## Initial release slices

1. LMS contract: learner state, concept graph, task, attempt, rubric, and evidence schemas; fixtures and schema validation.
2. Planner core: deterministic candidate filtering/ranking with explainable reason codes; no LLM dependency.
3. Three-pathway starter curriculum: foundational algebra, functions, proof habits, Python/problem solving, and computational experiments.
4. Practice loop: diagnostic, hint ladder, attempt history, misconception tagging, and review queue.
5. CACE bridge: read-only import of typed verification receipts; fail closed on missing/mismatched digests.
6. Tutor council: Hermes decomposition, Logos critique, and tutor explanations behind explicit capability/availability states.
7. Media supplements: resource discovery and learner-selected video/text supplements.
8. Production UX: accessible lesson player, exercise workspace, concept graph, progress/evidence view, and learner export/delete controls.

## Acceptance criteria for the first usable vertical slice

- A learner can choose goals and pathway weights without being locked into one path.
- A diagnostic produces a transparent baseline with uncertainty, not a permanent label.
- The planner returns at least three eligible tasks when available, each with prerequisites and reason codes.
- The learner can complete an exercise, receive rubric-linked feedback, and inspect the saved attempt.
- A new-context transfer task is required before a concept is marked mastered.
- A mathematical result is never marked formally proved from AI output, numerical simulation, or an LMS score.
- The same learner/task/evidence fixture yields deterministic planner output under the same planner version.
- Infrastructure failures are classified separately from learner errors.
- The learner can inspect and export their learning record.

## Open implementation questions to resolve from repository inspection

- Canonical Merlin app/runtime repository and current web/API entry point.
- Existing user identity/session and persistence boundaries.
- Existing CACE evidence receipt schema and stable verification API.
- Existing Hermes/Logos task interfaces and capability registry.
- Deployment target and migration constraints.

Until those are confirmed, this foundation is additive and must not invent or replace existing runtime contracts.
