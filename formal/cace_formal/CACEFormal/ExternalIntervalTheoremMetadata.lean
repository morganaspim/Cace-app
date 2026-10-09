import CACEFormal.ExternalIntervalAxiomAudit
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

namespace CACEFormal.ExternalIntervalTheoremMetadata

private def endpoints : List Name := [
  ``CACEFormal.CertifiedIntervalBounds.residual_component_bound,
  ``CACEFormal.CertifiedIntervalBounds.energy_error_bound,
  ``CACEFormal.CertifiedIntervalBounds.linear_residual_certificate,
  ``CACEFormal.CertifiedIntervalBounds.linear_residual_bound,
  ``CACEFormal.CertifiedIntervalBounds.invalid_linear_upper_rejected,
  ``CACEFormal.CertifiedIntervalBounds.exp_unit_certificate,
  ``CACEFormal.CertifiedIntervalBounds.exp_unit_bound
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
    ("generator", toJson "CACEFormal.ExternalIntervalTheoremMetadata"),
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

end CACEFormal.ExternalIntervalTheoremMetadata

