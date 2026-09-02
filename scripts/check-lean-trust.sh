#!/usr/bin/env bash
set -euo pipefail

mapfile -t lean_files < <(
  find . -path './.lake' -prune -o -type f -name '*.lean' -print
)

if ((${#lean_files[@]} == 0)); then
  echo 'ERROR: no project Lean files found.' >&2
  exit 1
fi

# Scan each Lean source as one continuous token stream rather than line by line.
# This catches declarations such as:
#
#   axiom
#   bogus : False
#
# while masking Lean line comments, nested block/doc comments, and strings so
# documentation text does not become a false trust violation.
python3 - "${lean_files[@]}" <<'PY'
from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Pattern

IDENT = r"A-Za-z0-9_"
RULES: tuple[tuple[str, Pattern[str]], ...] = (
    (
        "admitted proof (sorry/admit)",
        re.compile(rf"(?<![{IDENT}])(?:sorry|admit)(?![{IDENT}])"),
    ),
    (
        "custom axiom declaration",
        # Lean accepts any whitespace, including a newline, between `axiom`
        # and the declaration that follows it.
        re.compile(rf"(?<![{IDENT}])axiom(?=\s)"),
    ),
    (
        "native_decide / Lean.ofReduceBool trust",
        re.compile(rf"(?<![{IDENT}])native_decide(?![{IDENT}])"),
    ),
)


def mask_noncode(source: str) -> str:
    """Replace comments/string contents with spaces while preserving newlines."""

    chars = list(source)
    i = 0
    n = len(source)
    block_depth = 0
    in_line_comment = False
    in_string = False

    def mask(index: int) -> None:
        if chars[index] != "\n":
            chars[index] = " "

    while i < n:
        if in_line_comment:
            if source[i] == "\n":
                in_line_comment = False
            else:
                mask(i)
            i += 1
            continue

        if block_depth > 0:
            if source.startswith("/-", i):
                mask(i)
                if i + 1 < n:
                    mask(i + 1)
                block_depth += 1
                i += 2
                continue
            if source.startswith("-/", i):
                mask(i)
                if i + 1 < n:
                    mask(i + 1)
                block_depth -= 1
                i += 2
                continue
            mask(i)
            i += 1
            continue

        if in_string:
            if source[i] == "\\":
                mask(i)
                if i + 1 < n:
                    mask(i + 1)
                i += 2
                continue
            if source[i] == '"':
                mask(i)
                in_string = False
                i += 1
                continue
            mask(i)
            i += 1
            continue

        if source.startswith("--", i):
            mask(i)
            if i + 1 < n:
                mask(i + 1)
            in_line_comment = True
            i += 2
            continue

        if source.startswith("/-", i):
            mask(i)
            if i + 1 < n:
                mask(i + 1)
            block_depth = 1
            i += 2
            continue

        if source[i] == '"':
            mask(i)
            in_string = True
            i += 1
            continue

        i += 1

    return "".join(chars)


def find_rule(source: str, pattern: Pattern[str]) -> re.Match[str] | None:
    return pattern.search(mask_noncode(source))


# Regression checks for the exact bypass reported by review, plus the masking
# behavior that keeps ordinary comments/strings usable in trusted Lean files.
_axiom_pattern = RULES[1][1]
assert find_rule("axiom\nbogus : False\n", _axiom_pattern) is not None
assert find_rule("@[simp] axiom\nbogus : False\n", _axiom_pattern) is not None
assert find_rule("-- axiom\nbogus : False\n", _axiom_pattern) is None
assert find_rule('/- axiom\nbogus : False -/\n', _axiom_pattern) is None
assert find_rule('def note := "axiom\\nbogus"\n', _axiom_pattern) is None

violations: list[tuple[str, int, str, str]] = []

for file_name in sys.argv[1:]:
    path = Path(file_name)
    source = path.read_text(encoding="utf-8")
    code = mask_noncode(source)

    for description, pattern in RULES:
        for match in pattern.finditer(code):
            line = source.count("\n", 0, match.start()) + 1
            token = source[match.start() : match.end()].replace("\n", "\\n")
            violations.append((str(path), line, description, token))

if violations:
    for path, line, description, token in violations:
        print(f"{path}:{line}: ERROR: {description}: {token!r}", file=sys.stderr)
    raise SystemExit(1)

print("Lean trust gate passed: no admitted proofs, custom axioms, or native_decide.")
PY
