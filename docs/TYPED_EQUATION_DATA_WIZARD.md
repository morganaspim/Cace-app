# CACE Typed Equation and Data Wizard

Status: product/UX/engineering specification. Not scientific or proof evidence.

## Goal

Whenever a module needs nontrivial mathematical/data input, CACE should offer a guided wizard so users can enter valid equations, domains, units, boundary conditions and datasets without memorizing internal syntax.

The wizard must produce canonical typed objects, not unvalidated text strings.

## 1. Equation editor

Provide a math-aware editor with:

- natural keyboard entry;
- structured symbol palette;
- fractions, powers, roots, sums/products, integrals and derivatives;
- vectors/matrices/tensors;
- Greek symbols;
- subscripts/superscripts;
- piecewise expressions;
- gradients/divergence/curl/Laplacian;
- equations/inequalities;
- common domain/set notation;
- unit-aware constants;
- live high-quality mathematical rendering;
- copyable LaTeX/text representation.

Internally parse into a typed canonical AST. Rendered LaTeX is presentation/export, not the semantic source of truth.

## 2. Guided equation wizard

For modules such as PDEs, optimization, transforms and statistics, ask context-specific questions.

Example PDE flow:

```text
What are you solving?
 -> choose/enter equation
What is the domain?
 -> geometry / interval / mesh
What are the unknown fields?
 -> names + scalar/vector/tensor type
What are the units?
What initial/boundary conditions apply?
What coefficients/materials are known?
What assumptions should CACE check?
Which result/evidence level do you want?
 -> numerical / exact where possible / certified / theorem-linked
```

The wizard generates the canonical module/object graph and shows a human-readable summary before applying it.

## 3. Symbol table

Every equation workspace should maintain explicit definitions:

- symbol name;
- pretty display;
- semantic type;
- scalar/vector/tensor rank;
- domain;
- unit/dimension;
- known/unknown/parameter status;
- allowed range;
- provenance;
- assumptions.

Undefined or multiply-defined symbols should be surfaced before execution.

## 4. Validation

Validate before Build/Run:

- parser/type correctness;
- dimension/unit consistency;
- shape/rank compatibility;
- domain compatibility;
- required initial/boundary conditions;
- singular/invalid parameter ranges;
- unresolved symbols;
- module-specific assumptions;
- theorem applicability where requested.

Validation failures should explain what is wrong and offer a repair action rather than only an error code.

## 5. Data import wizard

For CSV/tabular/array/mesh/time-series/scientific files where supported:

1. preview data;
2. select columns/fields;
3. infer candidate types/units but require confirmation when ambiguous;
4. identify missing/invalid values;
5. map columns to canonical CACE objects;
6. choose uncertainty/error columns where available;
7. set coordinate/time interpretation;
8. show transformations that will occur;
9. preserve source/provenance/hash;
10. preview resulting module connections.

Never silently discard or reinterpret columns.

## 6. AI assistance

The Research Assistant may help fill the wizard conversationally.

Example:

> "I have temperature measurements every 0.1 seconds and want to fit a damped oscillator."

The assistant may propose:

- time column mapping;
- observed variable;
- units;
- candidate model equation;
- parameters to estimate;
- objective/residual;
- solver;
- uncertainty/diagnostics.

The user sees the structured wizard state and can edit it before building.

AI suggestions are proposals; deterministic validation remains authoritative.

## 7. Templates

Provide reusable templates for common tasks such as:

- linear system;
- polynomial;
- coordinate transform;
- ODE IVP;
- PDE + boundary conditions;
- optimization objective + constraints;
- regression/model fit;
- FFT/signal processing;
- FEM Poisson/elasticity/Maxwell;
- group action / permutation experiment;
- geometric algebra rotor/blade transform.

Templates instantiate typed objects and remain editable.

## 8. Pretty equations throughout CACE

Use the same canonical expression AST for:

- wizard;
- Properties panel;
- Help;
- Research Assistant explanations;
- canvas node summaries;
- Results;
- Proof Explorer;
- reports/export/print.

This avoids inconsistent string formulas.

Support accessible text equivalents and copy as LaTeX/plain text.

## 9. Production requirements

A module requiring complex input is not production-grade unless:

- users can discover required fields;
- types/units/domains are validated;
- equations render readably;
- invalid inputs fail before expensive execution where feasible;
- defaults are explicit and scientifically defensible;
- Help links explain each field;
- example inputs can be loaded;
- wizard output round-trips through save/load;
- the same typed semantics are used by GUI/API/CLI/agent.

## 10. Nonclaim

A beautifully rendered or syntactically valid equation is not necessarily mathematically well-posed or scientifically appropriate. CACE should separately report the validation/evidence that it can actually establish.
