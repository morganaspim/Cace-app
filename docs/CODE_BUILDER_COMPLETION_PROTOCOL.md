# CACE Code-Builder Completion Protocol

Status: required engineering policy for GitHub-connected code builders.

## Core rule

Build every required production feature. Difficulty or model uncertainty is not
permission to drop the feature, replace it with a mock, or simplify away an
established architecture.

## Unknown feature procedure

When the builder cannot immediately implement a feature:

1. list all affected CACE architectures/contracts;
2. generate 10 materially different implementation approaches by default;
3. score/rank each approach on:
   1. architecture preservation;
   2. correctness and evidence-boundary preservation;
   3. security/privacy/least privilege;
   4. implementation tractability;
   5. testability and bug-sweep coverage;
   6. reuse of existing CACE modules/tools;
   7. compute/build cost;
   8. maintainability/extensibility;
4. reject any candidate that weakens proof, evidence, account, network, AI,
   provenance, commercial, or security boundaries;
5. use CACE Build Lite to analyze actual changed-path/dependency/critical-path
   cost before choosing the implementation frontier;
6. use existing CACE computational/mathematical modules where they provide an
   inspectable advantage;
7. implement the highest-ranked viable candidate;
8. add tests and bug-sweep guards.

## Custom-tool fallback

If no existing CACE component can perform a required implementation subtask, the
builder may create a helper tool.

A helper tool must:

- solve one explicit gap;
- expose typed inputs/outputs;
- have no unnecessary authority;
- be deterministic where practical;
- have bounded resource/file/network behavior;
- include positive and negative regression tests;
- participate in Build Lite if it becomes part of the normal build;
- receive a permanent bug-pattern/guard when the defect class is mechanically
  recognizable;
- never become a second scientific runtime, second proof authority, shadow
  account system, or security bypass.

## Architecture preservation checklist

Before a feature/refactor is complete, record whether it touches and how it
preserves:

- typed scientific objects and graph execution;
- PASS/FAIL/NOT_RUN/stale evidence semantics;
- claim/proof ledger and exact-head Lean qualification;
- web/API/scientific/proof trust zones;
- optional-AI and AI non-authority rules;
- high-capability and network capability gates;
- account/profile/protein-storage boundaries;
- heartbeat/internal-credit/Math Coin separation from scientific truth;
- wallet custody and payment-key secrecy;
- provenance/log retention;
- source secrecy and commercial proof boundaries;
- public schemas/file formats/API compatibility;
- cross-chat/agent continuity.

## Completion rule

A feature is not complete merely because UI renders or a code generator produced
a plausible path. Completion requires the appropriate executable tests,
security checks, evidence rules, and integration gates.

If no safe implementation is possible yet, leave the feature visibly
`INCOMPLETE` with the ranked candidates, blocker, and next experiment. This is
preferred to architectural damage or false completion.
