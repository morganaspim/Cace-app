# MCFC–CACE Project-Only Coding Rule (Proposed ChatGPT Project Instructions)

Apply this rule only when developing, debugging, or modifying software in MCFC–CACE / M.E.R.L.I.N.; do not generalize it to unrelated user projects.

Before coding: retrieve the exact relevant project source and CACE canonical build/trust context; write an EngineeringSpec with behavior, invariants, risks, permissions, inputs, measurable acceptance tests, implementation plan, and rollback. Identify affected code and tests.

Always use red/green/refactor TDD. A new behavior gets a failing regression first; a bug gets an exact reproducer, a causal root-cause investigation, a sweep for sibling instances, a permanent guard where machine-checkable, and canonical `quality/bug_classes.json` closure. Do not bypass, dilute, or erase a failing test merely to make CI green. Keep an explicit `OPEN` item in `quality/bug_incidents.json` until the test and canonical guarded class are linked.

Before proposing a PR or push, run `python -m scripts.cace_prepr_gate --base-ref origin/main --change-kind KIND --profile quick` in a complete repository checkout. Block on missing baseline, syntax/JSON errors, missing tests, open bugs, invalid bug-class closure, targeted test failures, or canonical bug-sweep failures. Show every failed gate with cause and authorized next action. A quick pass is engineering feedback only; never claim CI, formal proof, security isolation, release, or deployment completion from it. For proof-sensitive source, use exact-head pinned Lean/Mathlib qualification independently. For native C++ run its native regression; for app surfaces run appropriate integration/E2E checks.

M.E.R.L.I.N.'s council can critique the design using source/bias/fallacy, mathematical, ethical and adversarial lenses; no persona can override a deterministic gate. Iterate when a new observation or amended test makes genuine progress; prevent repeated unchanged attempts. Keep all changes and context project-scoped and source-linked.

This file does not automatically change ChatGPT account/Project settings; it is a proposed patch for a user or eligible project editor to apply.