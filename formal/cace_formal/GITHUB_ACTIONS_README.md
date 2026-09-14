# CACE Formal v3.21 GitHub execution

The repository-level workflow `.github/workflows/cace-formal-v321.yml` executes the
external Lean proof boundary using the pinned `lean-toolchain` (`leanprover/lean4:v4.32.1`)
and mathlib `v4.32.1` from `lakefile.lean`.

A successful workflow must:

1. install the pinned Lean toolchain;
2. resolve the pinned mathlib dependency and cache;
3. reject `sorry` / `OPEN OBLIGATION` in the formal source tree;
4. complete `lake build`;
5. pass the independent exact-checker regression;
6. emit `v321_github_formal_build_attestation.json` as a workflow artifact.

Only step 4 completing successfully permits CACE to promote the relevant theorem from
`source-ready` to external Lean theorem-prover evidence.

`Dockerfile` is an alternative isolated route. It downloads the official Lean 4.32.1
Linux release and checks SHA-256
`57d5c062a6b4bae6fba511a1704aa124dff461c37d0fc94585637fbb7d951b50`
before executing Lake.
