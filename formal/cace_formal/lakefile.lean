import Lake
open Lake DSL

package «cace_formal» where

require mathlib from git
  "https://github.com/leanprover-community/mathlib4.git" @ "v4.32.1"

@[default_target]
lean_lib CACEFormal where

require LeanCert from git
  "https://github.com/alerad/leancert.git" @ "8a0104b8a8472e3c4695791c0671d89a37ae404f"
