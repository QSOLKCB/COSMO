#!/usr/bin/env bash
set -euo pipefail

mapfile -t lean_files < <(
  find . -path './.lake' -prune -o -type f -name '*.lean' -print
)

if ((${#lean_files[@]} == 0)); then
  echo 'ERROR: no project Lean files found.' >&2
  exit 1
fi

if grep -nH -E '(^|[^[:alnum:]_])(sorry|admit)([^[:alnum:]_]|$)' "${lean_files[@]}"; then
  echo 'ERROR: project-authored Lean contains an admitted proof (sorry/admit).' >&2
  exit 1
fi

# Match the axiom command even when it is preceded by attributes/modifiers such
# as `@[simp]`, `private`, or `noncomputable`.  The trailing whitespace keeps
# ordinary words such as `axioms` out of the match.
if grep -nH -E '(^|[^[:alnum:]_])axiom[[:space:]]+' "${lean_files[@]}"; then
  echo 'ERROR: project-authored Lean contains a custom axiom declaration.' >&2
  exit 1
fi

# PR A advertises a kernel-checked FORMAL layer.  `native_decide` introduces
# `Lean.ofReduceBool`, extending trust to the native evaluator, so it is not
# permitted in the trusted Lean source.
if grep -nH -E '(^|[^[:alnum:]_])native_decide([^[:alnum:]_]|$)' "${lean_files[@]}"; then
  echo 'ERROR: project-authored Lean contains native_decide / Lean.ofReduceBool trust.' >&2
  exit 1
fi

echo 'Lean trust gate passed: no admitted proofs, custom axioms, or native_decide.'
