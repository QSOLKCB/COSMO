import Lake
open Lake DSL

package «COSMO» where
  version := v!"0.1.0"
  -- Make every project Lean warning fatal. In particular, any `sorry`/`admit`
  -- that reaches Lean's parser fails the build even if it appears inside a
  -- context-sensitive interpolation syntax the lightweight trust lexer does
  -- not model directly.
  leanOptions := #[⟨`warningAsError, true⟩]

require mathlib from git
  "https://github.com/leanprover-community/mathlib4.git" @
  "0df444a360eaa60ab8c11dca51a86af692955474"

@[default_target]
lean_lib «cosmovirus»
