#!/usr/bin/env bash
set -euo pipefail

# Keep the trust scanner self-contained and lexical rather than relying on
# line-oriented grep. Lean permits executable syntax inside interpolated strings,
# apostrophes/question marks/bangs in identifiers, quoted identifiers, raw
# strings, and source modules exposed through symlinks.
python3 <<'PY'
from __future__ import annotations

import sys
import tempfile
import unicodedata
from pathlib import Path

FORBIDDEN: dict[str, str] = {
    "sorry": "admitted proof (sorry/admit/sorryAx)",
    "admit": "admitted proof (sorry/admit/sorryAx)",
    "sorryAx": "direct Lean.sorryAx trust",
    "axiom": "custom axiom declaration",
    "constant": "custom axiom-like constant declaration",
    "opaque": "opaque declaration forbidden by the trusted core",
    "native_decide": "native_decide / Lean.ofReduceBool trust",
    "ofReduceBool": "direct Lean.ofReduceBool trust",
}

# Quoted identifiers are normally ordinary identifiers even when their contents
# spell a Lean keyword (for example `«sorry»`). These two names are different:
# quoted spelling can resolve directly to the same trusted-base escape hatches.
FORBIDDEN_QUOTED = {"sorryAx", "ofReduceBool"}


def is_identifier_start(char: str) -> bool:
    if char == "_":
        return True
    category = unicodedata.category(char)
    return category.startswith("L") or category == "Nl"


def is_identifier_continue(char: str) -> bool:
    # Lean conventionally permits apostrophe, question-mark, and bang suffixes
    # in identifiers. Treat them as continuation characters so `sorry!` and
    # `native_decide?` are not confused with the forbidden bare tokens.
    if char in {"_", "'", "?", "!"}:
        return True
    category = unicodedata.category(char)
    return category[0] in {"L", "M", "N"}


def discover_lean_files(root: Path) -> list[Path]:
    """Return project .lean paths, including symlinked source modules."""

    files: list[Path] = []
    for path in root.rglob("*.lean"):
        try:
            relative = path.relative_to(root)
        except ValueError:
            continue
        if ".lake" in relative.parts:
            continue
        # is_file() follows a valid symlink; is_symlink() also keeps a dangling
        # .lean link visible so the gate fails closed when read_text() is tried.
        if path.is_file() or path.is_symlink():
            files.append(path)
    return sorted(files, key=lambda item: str(item))


def blank_like(source: str) -> list[str]:
    return ["\n" if char == "\n" else " " for char in source]


def mask_noncode(source: str) -> str:
    """Preserve executable Lean code while masking comments and string literals.

    Identifier-bang interpolation macros such as s!"...", m!"...", f!"...",
    v!"...", and project-defined macros with the same lexical shape preserve
    their {...} expressions as executable code. Context-sensitive interpolation
    forms are additionally covered by the package-level warningAsError compiler
    backstop, so an admission parsed by Lean cannot remain a non-fatal warning.
    Raw strings are consumed through their full hash-delimited terminator.
    """

    out = blank_like(source)
    n = len(source)

    def mask_line_comment(index: int) -> int:
        index += 2
        while index < n and source[index] != "\n":
            index += 1
        return index

    def mask_block_comment(index: int) -> int:
        depth = 1
        index += 2
        while index < n and depth > 0:
            if source.startswith("/-", index):
                depth += 1
                index += 2
            elif source.startswith("-/", index):
                depth -= 1
                index += 2
            else:
                index += 1
        return index

    def mask_plain_string(index: int) -> int:
        # index points at the opening quote.
        index += 1
        while index < n:
            if source[index] == "\\":
                index += 2
                continue
            if source[index] == '"':
                return index + 1
            index += 1
        return index

    def raw_string_end(index: int) -> int | None:
        """Return the first index after r###"..."###, or None if not an opener."""

        if source[index] != "r":
            return None
        cursor = index + 1
        hashes = 0
        while cursor < n and source[cursor] == "#":
            hashes += 1
            cursor += 1
        if cursor >= n or source[cursor] != '"':
            return None

        terminator = '"' + ("#" * hashes)
        end = source.find(terminator, cursor + 1)
        if end == -1:
            # Fail closed lexically by masking to EOF; Lean itself will reject
            # the unterminated raw string during `lake build`.
            return n
        return end + len(terminator)

    def mask_quoted_identifier(index: int) -> int:
        # Lean quoted identifiers such as «sorry» are identifiers, not keywords.
        # Preserve only the two quoted names that can directly spell trusted-base
        # escape hatches; mask every other quoted identifier to avoid keyword
        # false positives.
        start = index + 1
        cursor = start
        while cursor < n and source[cursor] != "»":
            cursor += 1
        content = source[start:cursor]
        if content in FORBIDDEN_QUOTED:
            for offset, char in enumerate(content, start=start):
                out[offset] = char
        return min(cursor + 1, n)

    def interpolation_macro_quote(index: int) -> int | None:
        """Return the quote in identifier!"...", else None.

        Lean ships multiple interpolation macros (`s!`, `m!`, `f!`, `v!`) and
        projects can define more. Recognizing the lexical family rather than a
        hard-coded prefix list prevents a new identifier-bang macro from silently
        turning an executable interpolation into an ordinary masked string.
        """

        if index >= n or not is_identifier_start(source[index]):
            return None
        cursor = index + 1
        while cursor < n and is_identifier_continue(source[cursor]):
            cursor += 1
        if (
            cursor < n
            and source[cursor] == '"'
            and cursor > index
            and source[cursor - 1] == "!"
        ):
            return cursor
        return None

    def scan_interpolated_string(index: int) -> int:
        # index points immediately after the opening quote.
        while index < n:
            if source[index] == "\\":
                index += 2
                continue
            if source.startswith("{{", index) or source.startswith("}}", index):
                index += 2
                continue
            if source[index] == "{":
                out[index] = "{"
                index = scan_code(index + 1, stop_at_closing_brace=True)
                continue
            if source[index] == '"':
                return index + 1
            index += 1
        return index

    def scan_code(index: int, *, stop_at_closing_brace: bool = False) -> int:
        while index < n:
            if source.startswith("--", index):
                index = mask_line_comment(index)
                continue
            if source.startswith("/-", index):
                index = mask_block_comment(index)
                continue

            raw_end = raw_string_end(index)
            if raw_end is not None:
                index = raw_end
                continue

            interpolation_quote = interpolation_macro_quote(index)
            if interpolation_quote is not None:
                # Preserve the interpolation macro token as code, mask literal
                # text, and recursively preserve each {...} expression.
                for offset in range(index, interpolation_quote):
                    out[offset] = source[offset]
                index = scan_interpolated_string(interpolation_quote + 1)
                continue
            if source[index] == '"':
                index = mask_plain_string(index)
                continue
            if source[index] == "«":
                index = mask_quoted_identifier(index)
                continue
            if stop_at_closing_brace and source[index] == "}":
                out[index] = "}"
                return index + 1
            if stop_at_closing_brace and source[index] == "{":
                out[index] = "{"
                index = scan_code(index + 1, stop_at_closing_brace=True)
                continue

            out[index] = source[index]
            index += 1
        return index

    scan_code(0)
    return "".join(out)


def identifiers(code: str):
    index = 0
    n = len(code)
    while index < n:
        if not is_identifier_start(code[index]):
            index += 1
            continue
        start = index
        index += 1
        while index < n and is_identifier_continue(code[index]):
            index += 1
        yield start, index, code[start:index]


def violations_in(source: str) -> list[tuple[int, str, str]]:
    code = mask_noncode(source)
    violations: list[tuple[int, str, str]] = []
    for start, _end, token in identifiers(code):
        description = FORBIDDEN.get(token)
        if description is None:
            continue
        line = source.count("\n", 0, start) + 1
        violations.append((line, description, token))
    return violations


# Regression checks for every review-discovered bypass, plus false-positive
# guards for legitimate Lean identifiers and non-code text.
assert violations_in("axiom\nbogus : False\n")
assert violations_in("@[simp] axiom\nbogus : False\n")
assert violations_in("constant bogus : False\n")
assert violations_in("opaque bogus : False\n")
assert violations_in("opaque implementationHidden : Nat := 0\n")
assert violations_in('def hidden : String := s!"{(sorry : Nat)}"\n')
assert violations_in('def hidden : MessageData := m!"{(sorry : Nat)}"\n')
assert violations_in('def hidden : Format := f!"{(sorry : Nat)}"\n')
assert violations_in('def hidden := v!"{(sorry : Nat)}"\n')
assert violations_in('def hidden := projectMacro!"{(sorry : Nat)}"\n')
assert violations_in("theorem trustBypass : False := sorryAx False true\n")
assert violations_in("theorem trustBypass : False := Lean.sorryAx False true\n")
assert violations_in("theorem trustBypass : False := Lean.«sorryAx» False true\n")
assert violations_in("theorem trustBypass : True := Lean.ofReduceBool True rfl\n")
assert violations_in("theorem trustBypass : True := Lean.«ofReduceBool» True rfl\n")
assert not violations_in("def native_decide' : Nat := 0\n")
assert not violations_in("def sorry' : Nat := 0\n")
assert not violations_in("def native_decide? : Nat := 0\n")
assert not violations_in("def sorry! : Nat := 0\n")
assert not violations_in("-- sorry axiom constant opaque native_decide sorryAx\ndef ok := 0\n")
assert not violations_in('/- nested /- sorry -/ axiom constant opaque -/\ndef ok := 0\n')
assert not violations_in('def note := "sorry axiom constant opaque native_decide sorryAx"\n')
assert not violations_in('def note := r#"literal \\"sorry\\" and axiom opaque text"#\n')
assert not violations_in('def note := r##"literal "sorry" # axiom opaque sorry"##\n')
assert not violations_in('def note := s!"literal sorry, but {1 + 1} is code"\n')
assert not violations_in('def note := m!"literal sorry, but {1 + 1} is code"\n')
assert not violations_in("def «sorry» : Nat := 0\n")
assert not violations_in("def «axiom» : Nat := 0\n")

# Verify that a .lean symlink is discovered and that its target contents are
# actually scanned even when the target has a non-.lean extension.
with tempfile.TemporaryDirectory() as temporary:
    root = Path(temporary)
    payload = root / "review_payload.txt"
    payload.write_text("theorem hidden : True := by sorry\n", encoding="utf-8")
    link = root / "ReviewSymlink.lean"
    link.symlink_to(payload.name)
    discovered = discover_lean_files(root)
    assert link in discovered
    assert violations_in(link.read_text(encoding="utf-8"))

lean_files = discover_lean_files(Path("."))
if not lean_files:
    print("ERROR: no project Lean files found.", file=sys.stderr)
    raise SystemExit(1)

violations: list[tuple[str, int, str, str]] = []
for path in lean_files:
    try:
        source = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        print(f"{path}: ERROR: unable to read Lean source: {error}", file=sys.stderr)
        raise SystemExit(1) from error

    for line, description, token in violations_in(source):
        violations.append((str(path), line, description, token))

if violations:
    for path, line, description, token in violations:
        print(f"{path}:{line}: ERROR: {description}: {token!r}", file=sys.stderr)
    raise SystemExit(1)

print(
    "Lean trust gate passed: no admitted proofs, custom axioms/constants/opaque "
    "declarations, native-evaluator trust, or reviewed scanner bypasses."
)
PY
