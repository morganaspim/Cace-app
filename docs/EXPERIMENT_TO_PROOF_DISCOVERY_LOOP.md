# CACE Experiment-to-Proof Discovery and Math-Tool Flywheel

Status: product/research/engineering specification. This document is not proof evidence.

## Goal

CACE should use running experiments to continuously surface mathematical structure worth proving, connect results to already-qualified theorems when possible, and convert successfully formalized reusable mathematics into new canonical tools.

The loop is:

```text
experiment runs
  -> typed observations / exact identities / residuals / invariants
  -> proof-opportunity detector
  -> existing theorem/tool matcher
       |-> existing qualified theorem applies -> attach explicit proof/evidence link
       |
       -> no qualified match -> create Proof Candidate
                -> formulate exact statement + assumptions
                -> exact/symbolic checks and counterexample search
                -> Lean proof attempt in quarantine
                -> source-to-formal binding when runtime data is involved
                -> canonical proof gates / qualification
                -> reusable canonical math tool
                -> AI operator library + Help/examples
                -> future experiments reuse it
```

Experiments **discover proof opportunities**; empirical/numerical behavior is never itself a formal proof.

## 1. Proof discovery during execution

Every suitable module/result may emit a non-authoritative `ProofOpportunity` record containing:

- source experiment/run/node IDs;
- semantic hashes;
- candidate statement in a typed mathematical AST;
- variables, domains and units;
- observed invariants/identities;
- assumptions currently known;
- assumptions still missing;
- evidence that motivated the candidate;
- counterexamples already found;
- nearest existing theorem/tool matches;
- estimated proof route;
- novelty/reuse score;
- status: `OBSERVED | MATCHED | CANDIDATE | REFUTED | QUARANTINED | QUALIFICATION_REQUIRED | QUALIFIED_REFERENCE`.

The record cannot set FORMAL/PASS.

## 2. Detection sources

Proof opportunities can be triggered by:

- exact equality repeatedly produced by canonical exact kernels;
- invariant preservation under transformations;
- symmetry/group action structure;
- conservation/balance identities;
- residual/orthogonality patterns;
- commutation or composition laws;
- rank/nullspace structure;
- polynomial identities;
- mesh incidence/orientation cancellation;
- exterior/graded identities;
- dimensional/unit constraints;
- recurring successful operator programs;
- a user/AI explicit "can this be proved?" request.

Numerical pattern detection should be treated as conjecture generation unless an exact/certified checker independently establishes the finite statement.

## 3. Existing theorem matcher first

Before inventing a new proof, CACE should search the canonical proof-backed toolbox and qualified theorem metadata.

The matcher should compare:

- statement/operator family;
- type/domain;
- hypotheses;
- representation identity;
- theorem conclusion;
- source-to-formal bridge requirements.

A theorem match is usable only when the runtime object actually satisfies the theorem's required binding/hypotheses. Similar-looking algebra is insufficient.

## 4. Proof Candidate object

When no existing qualified endpoint closes the opportunity, create or update a Research Idea with status `Proof Candidate`.

Suggested fields:

- conjecture/statement AST;
- human-readable rendered equation;
- motivating experiment refs;
- exact/certified finite checks;
- counterexample attempts;
- theorem dependencies;
- candidate Lean namespace/theorem name;
- runtime-to-formal obligations;
- unresolved premises;
- expected reusable tool if proved;
- proof attempt history;
- next gate.

The Local Research Assistant may explain and prioritize these objects.

## 5. Automatic proof attempt policy

For bounded/approved development work, Gemini/Antigravity/Local AI may:

1. normalize the statement;
2. reduce by known exact identities;
3. search canonical theorem/tool metadata;
4. generate small counterexamples;
5. create a quarantined Lean theorem statement/proof attempt;
6. run only permitted cheap/static checks automatically;
7. prepare a proof-ready submission packet;
8. request serialized Exact-Pin/canonical gates according to existing policy.

No repeated expensive proof run should occur merely because the AI is curious. The one-job-at-a-time and proof-cost rules remain authoritative.

## 6. Math-tool flywheel

A newly qualified reusable theorem should not remain isolated in the proof corpus.

Where useful, promote it through ordinary engineering review into:

- a canonical C++ exact/high-performance operation;
- an exact/certificate checker;
- a thin Python/API binding;
- a typed canvas module;
- structured Help and examples;
- theorem/proof metadata;
- an AI `ReasoningOperator` with explicit preconditions/invariants/failure domain.

The result becomes a reusable capability for later experiments and AI planning.

## 7. Combinatorics and group actions as a high-leverage reasoning layer

Prioritize exact reusable tools for:

- permutations and permutation composition;
- combinations/subsets/multisets;
- finite explicit groups;
- generators and relations in bounded supported classes;
- group actions;
- orbits and stabilizers;
- canonical representatives;
- Cayley-graph construction for small groups;
- cosets where tractable;
- symmetry detection/certification;
- graph automorphism interfaces where an exact/certified backend exists;
- incidence/boundary combinatorics;
- rewrite/normal-form systems;
- composition tables;
- finite counting identities.

Connect these to geometry:

```text
combinatorial/group object
 -> action on vectors/frames/cells/blades/graphs
 -> invariant/equivariant representation
 -> compressed operator program
 -> exact/certified check
 -> geometric visualization / scientific use
```

This can make AI reasoning more efficient by shrinking equivalent search states, reusing canonical transformations and exposing compositional structure. Any efficiency claim must be benchmarked against a suitable baseline.

## 8. AI operator-library integration

Every accepted reusable math tool may expose an operator record containing:

- stable ID;
- typed inputs/outputs;
- preconditions;
- invariants;
- inverse where available;
- group/composition relations;
- commutation rules where proved;
- canonicalization rule;
- cost estimate measured separately;
- checker/theorem references;
- failure domain.

The AI should plan using these typed operators rather than re-deriving long raw calculations in language every time.

## 9. Heartbeat integration

The canvas perception stream may announce:

- candidate invariant detected;
- theorem match found;
- proof candidate created;
- counterexample found;
- exact checker passed/failed;
- Lean attempt entered quarantine;
- qualification state changed;
- new accepted operator/tool available.

These signals guide attention only. Evidence remains in the authoritative verifier/proof subsystem.

## 10. Production integration rule

Proof discovery is integrated into normal experimentation, but it must never make ordinary runs fragile.

- failure to find a proof is not an experiment failure;
- theorem search has bounded resource budgets;
- proof work may be paused/deferred;
- scientific results retain their actual evidence status;
- proof candidates remain visible in Research Notebook/Proof Explorer;
- accepted theorem/tool relationships are deterministic/reproducible.

## 11. Definition of done

The proof-discovery loop is production-grade only when:

1. runtime modules can emit typed proof opportunities without inventing PASS;
2. theorem matching checks hypotheses/bindings, not text similarity alone;
3. proof candidates survive save/reload and link back to exact experiment state;
4. counterexamples can refute/close candidates cleanly;
5. bounded AI proof attempts go to quarantine;
6. expensive gates remain serialized and explicit;
7. newly accepted reusable mathematics can become a canonical tool/operator;
8. the UI distinguishes observation, conjecture, exact finite fact, and formal theorem;
9. Help explains why a proof link does or does not apply;
10. regression tests prove numerical patterns cannot auto-promote to formal evidence.
