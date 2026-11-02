# Tier-1 qualification check

`./run.sh <repo> [report.json]` → exit 0 PASS, 1 FAIL, 2 REFUSED.

Stdlib Python only. No Lean, no network, no install. Every row names the file and the check.
What it reads: `cace_studio/data/proof_contracts.json` (the contract), `formal/cace_formal/`
(toolchain pin, TOOLCHAIN_LOCK, lake-manifest if generated, audited Lean sources, executable bindings).

Checks: endpoints present/unique/declared in audited sources, allowed axioms ⊆ {Classical.choice, Quot.sound, propext},
toolchain pin shape, mathlib pin vs contract, audited sources exist, executable bindings exist, evidence bundle present.

REFUSED is a real answer: the repo does not carry what is needed to certify, and the row says which piece is missing.
It is not a softer FAIL. Tier 2 (kernel axiom closure) only runs when the pin and build tree match exactly.
