import CACEFormal.V330AxiomAudit
import Lean

/-!
# Continuum Lean-environment theorem metadata exporter

This module emits machine-readable metadata for the exact audited continuum endpoints.
The data comes from declarations already loaded into `Lean.Environment`; no theorem
edges are inferred from source text. Python qualification tooling canonicalizes and
hashes these records and fails closed if the endpoint set differs from the proof
contract.
-/

open Lean Meta

namespace CACEFormal.V330TheoremMetadata

private def endpoints : List Name := [
  ``CACEFormal.Continuum.smoothBoxProduct_hasFDerivAt,
  ``CACEFormal.Continuum.smoothBoxProduct_divergence_eq_greenVolume,
  ``CACEFormal.Continuum.smoothBoxGreen_schwartz,
  ``CACEFormal.Continuum.boxGraphNormalTrace_smooth_eq_classical_auto,
  ``CACEFormal.Continuum.submodule_topologicalClosure_eq_of_regularizer,
  ``CACEFormal.Continuum.submodule_topologicalClosure_eq_ker_of_regularizer,
  ``CACEFormal.Continuum.ker_le_topologicalClosure_of_regularizer,
  ``CACEFormal.Continuum.topologicalClosure_eq_top_of_regularizer,
  ``CACEFormal.Continuum.complexSmoothGraphClosure_eq_distributional_of_regularizer,
  ``CACEFormal.Continuum.distributional_le_complexSmoothGraphClosure_of_regularizer,
  ``CACEFormal.Continuum.realHDivSmoothGraphClosure_eq_distributionalPreimage_of_regularizer,
  ``CACEFormal.Continuum.realDistributionalPreimage_le_HDivSmoothGraphClosure_of_regularizer,
  ``CACEFormal.Continuum.mem_H1DistributionalGraphSubmodule_iff,
  ``CACEFormal.Continuum.smoothComplexH1GraphMap_mem_distributional,
  ``CACEFormal.Continuum.complexH1SmoothGraphClosure_le_distributional,
  ``CACEFormal.Continuum.complexH1SmoothGraphClosure_eq_distributional_of_regularizer,
  ``CACEFormal.Continuum.complexL2ToDistribution_l2RepresentativeOfInL2,
  ``CACEFormal.Continuum.inH1GraphRepresentative_mem,
  ``CACEFormal.Continuum.inHDivGraphRepresentative_mem,
  ``CACEFormal.Continuum.inHDiv_iff_exists_distributionalGraphRepresentative,
  ``CACEFormal.Continuum.reversedHDivGraph_mem_H1_of_mem_orthogonal,
  ``CACEFormal.Continuum.complexSmoothGraphHilbertClosure_eq_distributional,
  ``CACEFormal.Continuum.besselRieszSymbol_norm_le,
  ``CACEFormal.Continuum.h1RieszSymbol_norm_le_one,
  ``CACEFormal.Continuum.h1RieszSymbol_hasTemperateGrowth,
  ``CACEFormal.Continuum.besselPotential_neg_two_inH1_of_inL2,
  ``CACEFormal.Continuum.besselPotential_neg_one_weakPartial_inH1_of_inL2,
  ``CACEFormal.Continuum.rieszFiltered_weakPartial_inH1_of_inL2,
  ``CACEFormal.Continuum.h1RieszCorrection_inH1,
  ``CACEFormal.Continuum.inH1_of_besselRiesz_reconstruction,
  ``CACEFormal.Continuum.inH1_of_mem_H1DistributionalGraphSubmodule,
  ``CACEFormal.Continuum.inH1_iff_exists_distributionalGraphRepresentative,
  ``CACEFormal.Continuum.BoundedGreenPairing.normalTrace_bound,
  ``CACEFormal.Continuum.normalTrace_unique_of_dense_agreement,
  ``CACEFormal.Continuum.weakGreen_of_denseSmoothCore,
  ``CACEFormal.Continuum.hasZeroBoundaryTrace_zero,
  ``CACEFormal.Continuum.volumePairing_eq_zero_of_zeroBoundaryTrace,
  ``CACEFormal.Continuum.zeroBoundaryOrthogonality,
  ``CACEFormal.Continuum.zeroBoundaryOrthogonality_of_mem,
  ``CACEFormal.Continuum.continuumPragerSynge_of_weakGreen,
  ``CACEFormal.Continuum.boxGradientFlux_inner_eq_green_of_divergence_zero,
  ``CACEFormal.Continuum.boxGraphPragerSynge_of_divergence_zero,
  ``CACEFormal.Continuum.zeroBoundarySubmodule_eq_iInf_ker,
  ``CACEFormal.Continuum.isClosed_zeroBoundarySubmodule,
  ``CACEFormal.Continuum.topologicalClosure_le_zeroBoundarySubmodule,
  ``CACEFormal.Continuum.hasZeroBoundaryTrace_of_mem_topologicalClosure,
  ``CACEFormal.Continuum.boxHasZeroBoundaryTrace_of_mem_coreClosure,
  ``CACEFormal.Continuum.boxGraphPragerSynge_of_divergence_zero_of_mem_coreClosure
]

private def insertName (name : Name) (names : List Name) : List Name :=
  if names.contains name then names else name :: names

private partial def collectConstants (expr : Expr) (acc : List Name := []) : List Name :=
  match expr with
  | .bvar _ => acc
  | .fvar _ => acc
  | .mvar _ => acc
  | .sort _ => acc
  | .const name _ => insertName name acc
  | .app fn arg => collectConstants arg (collectConstants fn acc)
  | .lam _ domain body _ => collectConstants body (collectConstants domain acc)
  | .forallE _ domain body _ => collectConstants body (collectConstants domain acc)
  | .letE _ type value body _ =>
      collectConstants body (collectConstants value (collectConstants type acc))
  | .lit _ => acc
  | .mdata _ body => collectConstants body acc
  | .proj _ _ body => collectConstants body acc

private def isCACEName (name : Name) : Bool :=
  name.toString.startsWith "CACEFormal."

private def theoremDependencies (env : Environment) (self : Name) (expr : Expr) : List Name :=
  (collectConstants expr).filter fun name =>
    name != self && isCACEName name &&
      match env.find? name with
      | some (.thmInfo _) => true
      | _ => false

private partial def theoremClosure
    (env : Environment) (todo visited : List Name) : List Name :=
  match todo with
  | [] => visited
  | name :: rest =>
      if visited.contains name then
        theoremClosure env rest visited
      else
        match env.find? name with
        | some (.thmInfo info) =>
            let direct := theoremDependencies env name info.value
            theoremClosure env (direct ++ rest) (name :: visited)
        | _ => theoremClosure env rest visited

private def namesJson (names : List Name) : Json :=
  toJson (names.map Name.toString)

private def theoremRecord (env : Environment) (name : Name) : MetaM Json := do
  let some info := env.find? name
    | throwError "continuum metadata exporter: missing declaration {name}"
  let .thmInfo thm := info
    | throwError "continuum metadata exporter: {name} is not a theorem declaration"
  let direct := theoremDependencies env name thm.value
  let transitive := (theoremClosure env direct []).filter (· != name)
  let statement ← withOptions (fun options =>
      options.setBool `pp.all true |>.setBool `pp.universes true) do
    pure s!"{← ppExpr thm.type}"
  pure <| Json.mkObj [
    ("schema", toJson "cace-lean-theorem-record-v1"),
    ("generator", toJson "CACEFormal.V330TheoremMetadata"),
    ("theorem", toJson name.toString),
    ("declaration_kind", toJson "theorem"),
    ("level_parameters", toJson (thm.levelParams.map Name.toString)),
    ("statement_pp_all", toJson statement),
    ("statement_constants", namesJson (collectConstants thm.type)),
    ("direct_cace_theorem_dependencies", namesJson direct),
    ("transitive_cace_theorem_dependencies", namesJson transitive)
  ]

run_meta do
  let env ← getEnv
  for name in endpoints do
    let record ← theoremRecord env name
    IO.println s!"CACE_THEOREM_METADATA\t{record.compress}"

end CACEFormal.V330TheoremMetadata
