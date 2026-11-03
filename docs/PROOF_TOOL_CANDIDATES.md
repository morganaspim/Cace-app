# Proof Tool Candidates

This queue tracks high-value proof families that should become canonical CACE tools only after source, tests and proof linkage are complete.

Status values:

- `idea`: useful mathematical target.
- `implemented`: deterministic code exists.
- `tested`: ordinary tests pass.
- `lean-linked`: Lean theorem/proof artifact is linked.
- `canonically-verified`: exact-head CACE qualification has passed.

| Rank | Candidate | Target Tool | Initial Status | Science Benefit |
| --- | --- | --- | --- | --- |
| 1 | Prager-Synge / equilibrated error identity | `proof.prager_synge_certificate` | idea | certified FEM and continuum error bounds |
| 2 | Interval residual enclosure | `proof.interval_residual_bound` | idea | uncertainty-aware PDE/science workflows |
| 3 | Discrete Green identity | `proof.discrete_green_identity` | idea | conservation and operator consistency |
| 4 | Mesh conformity invariant | `proof.mesh_conformity` | idea | safe adaptive geometry |
| 5 | CPU/GPU equivalence envelope | `proof.cpu_gpu_equivalence` | idea | trusted acceleration |
| 6 | Unit/typed-port compatibility | `proof.typed_unit_contract` | implemented | prevents category errors in mixed science graphs |

No candidate in this table is formal evidence merely by being listed here. A candidate becomes a canonical tool only when the implementation, tests, Lean linkage where required, and exact-head qualification evidence all agree.

## AI role

Granite can explain candidates and route work. Phi can identify proof obligations and draft structured tool plans. Qwen can inspect geometry/mesh visuals. A coding model can propose implementation patches. CACE and Lean decide what is verified.

## PR rule

Open a PR only after:

1. candidate source changes exist;
2. cheap tests pass;
3. any claimed Lean/proof linkage is present and runnable;
4. docs state the exact evidence boundary;
5. unverified candidates remain labeled as unverified.
