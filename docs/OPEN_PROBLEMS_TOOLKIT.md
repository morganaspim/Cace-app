# CACE Open Problems Toolkit

Status: research/product design. Catalog entries are source-backed research navigation objects, not proof evidence and not claims that CACE has solved the listed problems.

Date: 2026-09-19

## Objective

Provide a GUI toolkit that lets users:

- browse important open problems across mathematics and the sciences;
- filter/search by field, status, collection, and tags;
- inspect a concise source-backed problem card;
- import a problem onto the CACE scientific canvas as a typed research object;
- press **Play** to focus the local AI and heartbeat system on the imported problem;
- connect the problem node to relevant CACE modules, Research Ideas, experiments, and proof obligations.

## Source/status policy

Open-problem status can change, so every curated entry stores:

- stable CACE problem ID;
- title;
- field/domain;
- status: open / solved / partially-resolved / unknown;
- collection/authority;
- source URL;
- last-verified date;
- short CACE-authored summary;
- tags;
- explicit limitations/known constraints.

CACE must never infer a current "open" status from an old snapshot. Curated catalogs are date-stamped and should be refreshed from authoritative sources before release updates.

The v1 seed catalog uses the Clay Mathematics Institute Millennium Prize Problems. As verified on 2026-09-19, six remain unsolved/open and the Poincaré Conjecture is solved.

## Offline-first architecture

The scientific runtime does not scrape the web.

CACE ships/imports catalog snapshots such as:

`cace.open-problem-catalog.v1`

Each snapshot carries source metadata and dates. Additional catalogs for physics, chemistry, biology, astronomy, computer science, and other domains can be imported later without granting the scientific worker general Internet access.

## Canvas object

A problem imported to the canvas becomes a typed `research.open_problem` node with parameters such as:

- `problem_id`
- `title`
- `domain`
- `status`
- `collection`
- `summary`
- `authority`
- `source_url`
- `last_verified`
- `tags`

This node emits a research/problem object and a bounded research prompt, but emits no verification evidence simply by existing.

## Play mode

**Play** is exploratory, not a solver-status button.

When Play is pressed:

1. ensure the problem is present on the canvas;
2. raise non-authoritative heartbeat research-interest on that node;
3. propagate the current canvas heartbeat/delta to the local AI;
4. provide the problem card, source/status date, assumptions, connected modules, and current evidence state;
5. ask for candidate decompositions, invariants, experiments, computational checks, formal obligations, and falsification paths;
6. keep AI output outside PASS/FAIL/VERIFIED authority.

The local AI may suggest:
- decompositions;
- subproblems;
- mathematical operators;
- relevant existing CACE modules;
- simulation/experiment plans;
- missing assumptions;
- possible proof obligations;
- counterexamples/tests.

It may not claim an open problem has been solved merely because a numerical experiment, heuristic, or AI response looks promising.

## Millennium seed set

Curated from Clay Mathematics Institute:

- Birch and Swinnerton-Dyer Conjecture — open
- Hodge Conjecture — open
- Navier-Stokes Equation — open
- P vs NP — open
- Riemann Hypothesis — open
- Yang-Mills & the Mass Gap — open
- Poincaré Conjecture — solved

All entries carry Clay as authority and a 2026-09-19 last-verified date.

## Custom catalog import

Users can import JSON problem catalogs if they match the strict schema.

Imported entries:
- do not execute code;
- cannot set verification status;
- do not install plugins;
- store source URLs only as metadata;
- are validated for duplicate IDs, allowed status values, field sizes, and canonical identifiers.

## Future science catalogs

Potential separately curated catalogs:
- fundamental physics;
- condensed matter/materials;
- chemistry;
- molecular biology/genomics;
- neuroscience;
- astronomy/cosmology;
- climate/earth science;
- theoretical computer science.

Each catalog should use domain-appropriate authorities and evidence/status language rather than treating every research question as a theorem.

## First executable slice

1. strict `OpenProblem` and catalog schemas;
2. packaged Millennium catalog;
3. search/filter GUI dock;
4. Import to Canvas button;
5. Play on Canvas button;
6. heartbeat integration;
7. local-AI structured-context bridge;
8. custom JSON catalog import;
9. tests that:
   - packaged catalog has six open + one solved Millennium entries;
   - duplicate/invalid catalog entries fail closed;
   - importing a problem generates no verification evidence;
   - Play changes only heartbeat attention/context;
   - solved entries remain available for historical/method study but are visibly distinguished from open ones.
