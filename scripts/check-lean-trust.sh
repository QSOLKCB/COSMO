#!/usr/bin/env bash
set -euo pipefail

mapfile -t lean_files < <(
  find . -path './.lake' -prune -o -type f -name '*.lean' -print
)

if grep -nH -E '(^|[^[:alnum:]_])sorry([^[:alnum:]_]|$)' "${lean_files[@]}"; then
  echo 'ERROR: project-authored Lean contains sorry.' >&2
  exit 1
fi

if grep -nH -E '^[[:space:]]*axiom[[:space:]]+' "${lean_files[@]}"; then
  echo 'ERROR: project-authored Lean contains a custom axiom declaration.' >&2
  exit 1
fi

echo 'Lean trust gate passed: no project sorry and no project axiom declarations.'
