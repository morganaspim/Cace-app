# CACE Customer Help System

This directory is the source for customer-facing help.

The public help system is designed to be complete for users while protecting CACE proprietary implementation details and custom mathematics.

## Canonical generated file

Production/release builds generate:

`docs/help/generated/CACE_PUBLIC_HELP.md`

and:

`docs/help/generated/cace_public_help.json`

with:

```bash
python scripts/generate_public_help.py
```

The generated guide covers:

- every customer-facing feature recorded in the public help fragments;
- every currently registered CACE module;
- visible inputs, outputs, parameter names/types/units, maturity and evidence categories;
- at least two direct-use examples per feature/module;
- at least two combined-module examples per module;
- public explanations of why type/unit/verification/proof boundaries make an experiment rigorous.

## Proprietary boundary

The generator intentionally does **not** expose:

- source paths or internal class/function names;
- internal module IDs;
- theorem bodies or Lean implementation;
- proprietary equations, derivations, algorithms or heuristics;
- internal parameter defaults that could reveal custom methods;
- raw internal assumptions/descriptions when they reveal implementation details;
- proof artifacts/hashes;
- database schemas;
- credentials, wallet secrets, service internals or prompts.

The leakage policy is machine-readable in `CACE_PUBLIC_HELP_POLICY.json`.

## Accuracy rule

Help pages are generated from the live public module contract rather than manually duplicated module documentation. This means adding a registered module without help coverage causes the public-help coverage test to fail.

A suggested connection means only that the public port type/unit contract is compatible. Users must still judge scientific appropriateness and inspect the resulting evidence state.
