#!/usr/bin/env bash
set -euo pipefail

: "${GITHUB_WORKSPACE:?}"
: "${RUNNER_TEMP:?}"
: "${PINNED_LEAN_HOME:?}"
: "${LEAN_NUM_THREADS:?}"
: "${COSMO_BUILD_WORKSPACE:?}"
: "${COSMO_AUDIT_WORKSPACE:?}"
COSMO_DEPENDENCY_ANCHOR="${COSMO_DEPENDENCY_ANCHOR:-}"
COSMO_DEPENDENCY_AUTHORITY="${COSMO_DEPENDENCY_AUTHORITY:-verified-reuse}"

BUILD_HOME=/tmp/cosmobuild-home
AUDIT_HOME=/tmp/cosmoaudit-home
TOOLCHAIN_LIB="$PINNED_LEAN_HOME/lib/lean"
DEPENDENCY_RECEIPT="$RUNNER_TEMP/cosmo-dependency-run-receipt.json"
LEAN_PATH_FILE="$RUNNER_TEMP/cosmo-lean-path.txt"
TRUSTED_LEAN_PATH_FILE="$RUNNER_TEMP/cosmo-trusted-lean-path.txt"
ARTIFACTS_FILE="$RUNNER_TEMP/cosmo-project-artifacts.txt"
SOURCE_CACHE_RECEIPT="$COSMO_BUILD_WORKSPACE/.lean-cache/source-receipt.json"
SOURCE_CACHE_RECEIPT_SHA=""

begin_group() { printf '::group::%s\n' "$1"; }
end_group() { printf '::endgroup::\n'; }

terminate_identity() {
  local identity="$1"
  sudo pkill -TERM -u "$identity" 2>/dev/null || true
  for _ in 1 2 3 4 5; do
    if ! sudo pgrep -u "$identity" >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
  done
  sudo pkill -KILL -u "$identity" 2>/dev/null || true
  if sudo pgrep -u "$identity" >/dev/null 2>&1; then
    echo "ERROR: process owned by $identity survived termination." >&2
    return 1
  fi
}

cleanup() {
  terminate_identity cosmoaudit || true
  terminate_identity cosmobuild || true
}
trap cleanup EXIT

begin_group "Self-test reviewed trust helpers"
python3 scripts/prepare-lean-audit.py --self-test
./scripts/check-lean-trust.sh
end_group

begin_group "Prepare protected identities"
sudo useradd --system --no-create-home --shell /usr/sbin/nologin cosmobuild 2>/dev/null || true
sudo useradd --system --no-create-home --shell /usr/sbin/nologin cosmoaudit 2>/dev/null || true
sudo rm -rf "$BUILD_HOME" "$AUDIT_HOME" "$COSMO_AUDIT_WORKSPACE"
sudo install -d -o cosmobuild -g cosmobuild -m 0700 "$BUILD_HOME"
sudo install -d -o cosmoaudit -g cosmoaudit -m 0700 "$AUDIT_HOME"
sudo install -d -o cosmoaudit -g cosmoaudit -m 0700 "$COSMO_AUDIT_WORKSPACE"
sudo chmod o+x /home/runner /home/runner/work "$RUNNER_TEMP" \
  "$GITHUB_WORKSPACE/.." "$GITHUB_WORKSPACE"

test -d "$TOOLCHAIN_LIB"
test -f "$COSMO_BUILD_WORKSPACE/lake-manifest.json"
test -d "$COSMO_BUILD_WORKSPACE/.lake/packages"

if sudo -u cosmobuild test -w "$GITHUB_WORKSPACE"; then
  echo "ERROR: build identity can write reviewed checkout." >&2
  exit 1
fi
if sudo -u cosmobuild test -w "$COSMO_BUILD_WORKSPACE/.lake/packages"; then
  echo "ERROR: build identity can write verified dependency tree." >&2
  exit 1
fi
if sudo -u cosmobuild test -w "$COSMO_BUILD_WORKSPACE/lake-manifest.json"; then
  echo "ERROR: build identity can write frozen Lake manifest." >&2
  exit 1
fi

# The routine source-cache receipt is generated verification metadata, not
# reviewed project source. If present, authenticate and freeze it explicitly so
# the protected source-closure check can allow exactly this one untracked path.
if [ -e "$SOURCE_CACHE_RECEIPT" ] || [ -L "$SOURCE_CACHE_RECEIPT" ]; then
  if [ -L "$SOURCE_CACHE_RECEIPT" ] || [ ! -f "$SOURCE_CACHE_RECEIPT" ]; then
    echo "ERROR: source-cache receipt is missing, non-regular, or symlinked." >&2
    exit 1
  fi
  SOURCE_CACHE_RECEIPT_SHA="$(sha256sum "$SOURCE_CACHE_RECEIPT" | awk '{print $1}')"
  if sudo -u cosmobuild test -w "$SOURCE_CACHE_RECEIPT"; then
    echo "ERROR: build identity can write frozen source-cache receipt." >&2
    exit 1
  fi
  echo "Frozen source-cache receipt sha256=$SOURCE_CACHE_RECEIPT_SHA"
fi
end_group

begin_group "Compile trusted auditor from reviewed source"
staging="$(mktemp -d)"
trap 'rm -rf "$staging"; cleanup' EXIT
cp CosmoTrust.lean "$staging/CosmoTrustAudit.lean"
cat > "$staging/GeneratedAxiomFixture.lean" <<'LEAN'
import CosmoTrustAudit
open Lean Elab Command
run_cmd do
  liftCoreM <| addDecl <| Declaration.axiomDecl {
    name := `CosmoTrustFixture.generatedBogus
    levelParams := []
    type := mkConst ``False
    isUnsafe := false
  }
run_cmd do
  CosmoTrust.auditNamedDeclarations
    "generated declaration regression fixture"
    #[`CosmoTrustFixture.generatedBogus]
LEAN
cat > "$staging/GeneratedUncheckedTheorem.lean" <<'LEAN'
import Lean.Elab.Command
open Lean Elab Command
set_option debug.skipKernelTC true in
run_cmd do
  liftCoreM <| addDecl (forceExpose := true) <| Declaration.thmDecl {
    name := `GeneratedUncheckedTheorem.bogus
    levelParams := []
    type := mkConst ``False
    value := mkConst ``True.intro
  }
LEAN

sudo install -o cosmoaudit -g cosmoaudit -m 0600 \
  "$staging/CosmoTrustAudit.lean" "$COSMO_AUDIT_WORKSPACE/CosmoTrustAudit.lean"
sudo install -o cosmoaudit -g cosmoaudit -m 0600 \
  "$staging/GeneratedAxiomFixture.lean" "$COSMO_AUDIT_WORKSPACE/GeneratedAxiomFixture.lean"
sudo install -o cosmoaudit -g cosmoaudit -m 0600 \
  "$staging/GeneratedUncheckedTheorem.lean" "$COSMO_AUDIT_WORKSPACE/GeneratedUncheckedTheorem.lean"

sudo -u cosmoaudit env -i \
  HOME="$AUDIT_HOME" PATH="$PINNED_LEAN_HOME/bin:/usr/bin:/bin" \
  LEAN_PATH="$TOOLCHAIN_LIB" LC_ALL=C.UTF-8 LANG=C.UTF-8 TZ=UTC \
  LEAN_NUM_THREADS=1 \
  bash -c 'cd "$1"; shift; exec "$@"' \
  _ "$COSMO_AUDIT_WORKSPACE" \
  "$PINNED_LEAN_HOME/bin/lean" -o CosmoTrustAudit.olean CosmoTrustAudit.lean

sudo chown -R root:root "$COSMO_AUDIT_WORKSPACE"
sudo find "$COSMO_AUDIT_WORKSPACE" -type f -exec chmod 0444 {} +
sudo chmod 0555 "$COSMO_AUDIT_WORKSPACE"
rm -rf "$staging"
trap cleanup EXIT
end_group

begin_group "Authenticate dependency build state"
if [ -n "$COSMO_DEPENDENCY_ANCHOR" ]; then
  python3 scripts/verify-lean-dependency-artifacts.py verify-anchor \
    --root "$COSMO_BUILD_WORKSPACE/.lake/packages" \
    --anchor "$COSMO_DEPENDENCY_ANCHOR"
else
  echo "Cold authority uses exact-run source reconstruction plus run-local artifact receipt; no routine cache anchor is consulted."
fi
python3 scripts/verify-lean-dependency-artifacts.py snapshot \
  --root "$COSMO_BUILD_WORKSPACE/.lake/packages" \
  --receipt "$DEPENDENCY_RECEIPT"
sudo chown root:root "$DEPENDENCY_RECEIPT"
sudo chmod 0444 "$DEPENDENCY_RECEIPT"
end_group

begin_group "Expose only COSMO output to compilation identity"
sudo rm -rf "$COSMO_BUILD_WORKSPACE/.lake/build"
sudo install -d -o cosmobuild -g cosmobuild -m 0700 \
  "$COSMO_BUILD_WORKSPACE/.lake/build/lib/lean"
project_output="$COSMO_BUILD_WORKSPACE/.lake/build/lib/lean"

if ! sudo -u cosmobuild test -w "$project_output"; then
  echo "ERROR: build identity cannot write isolated COSMO output." >&2
  exit 1
fi
if sudo -u cosmobuild test -w "$COSMO_BUILD_WORKSPACE"; then
  echo "ERROR: build identity can write frozen workspace root." >&2
  exit 1
fi
end_group

begin_group "Compile current COSMO modules against verified dependencies"
dependency_lean_path="$TOOLCHAIN_LIB"
dependency_libs=0
for pkg in "$COSMO_BUILD_WORKSPACE"/.lake/packages/*; do
  [ -e "$pkg" ] || continue
  if [ -L "$pkg" ]; then
    echo "ERROR: symlinked dependency package: $pkg" >&2
    exit 1
  fi
  [ -d "$pkg" ] || continue
  lib="$pkg/.lake/build/lib/lean"
  [ -e "$lib" ] || continue
  if [ -L "$lib" ] || [ ! -d "$lib" ]; then
    echo "ERROR: invalid dependency Lean output: $lib" >&2
    exit 1
  fi
  dependency_lean_path="$dependency_lean_path:$lib"
  dependency_libs="$((dependency_libs + 1))"
done
test "$dependency_libs" -gt 0
project_lean_path="$dependency_lean_path:$project_output"

compile_project_module() {
  local source="$1"
  local output="$2"
  echo "Compiling $source -> $output"
  sudo -u cosmobuild env -i \
    HOME="$BUILD_HOME" PATH="$PINNED_LEAN_HOME/bin:/usr/bin:/bin" \
    LEAN_PATH="$project_lean_path" \
    LC_ALL=C.UTF-8 LANG=C.UTF-8 TZ=UTC \
    LEAN_NUM_THREADS="$LEAN_NUM_THREADS" \
    bash -c 'cd "$1"; shift; exec "$@"' \
    _ "$COSMO_BUILD_WORKSPACE" \
    "$PINNED_LEAN_HOME/bin/lean" -DwarningAsError=true \
    -o "$output" "$source"
}

compile_project_module CosmoTrust.lean "$project_output/CosmoTrust.olean"
compile_project_module cosmovirus.lean "$project_output/cosmovirus.olean"
compile_project_module COSMO.lean "$project_output/COSMO.olean"
terminate_identity cosmobuild
end_group

begin_group "Prove dependency state stayed immutable"
python3 scripts/verify-lean-dependency-artifacts.py verify \
  --root "$COSMO_BUILD_WORKSPACE/.lake/packages" \
  --receipt "$DEPENDENCY_RECEIPT"
if [ -n "$COSMO_DEPENDENCY_ANCHOR" ]; then
  python3 scripts/verify-lean-dependency-artifacts.py verify-anchor \
    --root "$COSMO_BUILD_WORKSPACE/.lake/packages" \
    --anchor "$COSMO_DEPENDENCY_ANCHOR"
fi

if [ -n "$SOURCE_CACHE_RECEIPT_SHA" ]; then
  if [ -L "$SOURCE_CACHE_RECEIPT" ] || [ ! -f "$SOURCE_CACHE_RECEIPT" ]; then
    echo "ERROR: frozen source-cache receipt disappeared or changed type." >&2
    exit 1
  fi
  actual_source_receipt_sha="$(sha256sum "$SOURCE_CACHE_RECEIPT" | awk '{print $1}')"
  if [ "$actual_source_receipt_sha" != "$SOURCE_CACHE_RECEIPT_SHA" ]; then
    echo "ERROR: frozen source-cache receipt changed during COSMO compilation." >&2
    exit 1
  fi
fi
end_group

begin_group "Verify isolated COSMO source stayed identical"
python3 - <<'PY'
from __future__ import annotations
import hashlib
import os
import stat
import subprocess
from pathlib import Path

reviewed = Path(os.environ["GITHUB_WORKSPACE"])
built = Path(os.environ["COSMO_BUILD_WORKSPACE"])
tracked_raw = subprocess.check_output(["git", "ls-files", "-z"], cwd=reviewed)
tracked = {Path(os.fsdecode(item)) for item in tracked_raw.split(b"\0") if item}
approved_generated = {
    Path("lake-manifest.json"),
    Path(".lean-cache/source-receipt.json"),
}

def fingerprint(path: Path) -> tuple[str, str, int]:
    info = path.lstat()
    executable = info.st_mode & 0o111
    if stat.S_ISLNK(info.st_mode):
        return ("symlink", os.readlink(path), executable)
    if stat.S_ISREG(info.st_mode):
        return ("file", hashlib.sha256(path.read_bytes()).hexdigest(), executable)
    return ("other", str(stat.S_IFMT(info.st_mode)), executable)

failures: list[str] = []
for relative in sorted(tracked, key=str):
    source_path = reviewed / relative
    built_path = built / relative
    if not built_path.exists() and not built_path.is_symlink():
        failures.append(f"missing tracked path: {relative}")
    elif fingerprint(source_path) != fingerprint(built_path):
        failures.append(f"tracked path changed during protected build: {relative}")

actual: set[Path] = set()
for path in built.rglob("*"):
    relative = path.relative_to(built)
    if not relative.parts or relative.parts[0] == ".lake":
        continue
    if relative in approved_generated:
        continue
    if path.is_file() or path.is_symlink():
        actual.add(relative)
for extra in sorted(actual - tracked, key=str):
    failures.append(f"unexpected protected-build path: {extra}")

if failures:
    for failure in failures:
        print(f"ERROR: {failure}")
    raise SystemExit(1)
print(f"Isolated source verification passed for {len(tracked)} tracked path(s).")
PY
end_group

begin_group "Freeze COSMO outputs and derive exact audit set"
sudo chown -R root:root "$COSMO_BUILD_WORKSPACE/.lake/build"
sudo chmod -R a+rX "$COSMO_BUILD_WORKSPACE/.lake/build"
sudo chmod -R a-w "$COSMO_BUILD_WORKSPACE/.lake/build"

python3 scripts/prepare-lean-audit.py \
  --workspace "$COSMO_BUILD_WORKSPACE" \
  --manifest "$COSMO_BUILD_WORKSPACE/lake-manifest.json" \
  --toolchain-lib "$TOOLCHAIN_LIB" \
  --lean-path-output "$LEAN_PATH_FILE" \
  --trusted-lean-path-output "$TRUSTED_LEAN_PATH_FILE" \
  --artifacts-output "$ARTIFACTS_FILE"
sudo chown root:root "$LEAN_PATH_FILE" "$TRUSTED_LEAN_PATH_FILE" "$ARTIFACTS_FILE"
sudo chmod 0444 "$LEAN_PATH_FILE" "$TRUSTED_LEAN_PATH_FILE" "$ARTIFACTS_FILE"
end_group

begin_group "Replay dependency closure and protected COSMO artifacts"
lean_path="$(cat "$LEAN_PATH_FILE")"
mapfile -t artifacts < "$ARTIFACTS_FILE"
test "${#artifacts[@]}" -gt 0
audit_report="$RUNNER_TEMP/cosmo-semantic-audit.txt"
sudo -u cosmoaudit env -i \
  HOME="$AUDIT_HOME" PATH="$PINNED_LEAN_HOME/bin:/usr/bin:/bin" \
  LEAN_PATH="$lean_path" LC_ALL=C.UTF-8 LANG=C.UTF-8 TZ=UTC \
  LEAN_NUM_THREADS=1 \
  bash -c 'cd "$1"; shift; exec "$@"' \
  _ "$COSMO_AUDIT_WORKSPACE" \
  "$PINNED_LEAN_HOME/bin/lean" --run CosmoTrustAudit.lean \
  --project "$TOOLCHAIN_LIB" "${artifacts[@]}" | tee "$audit_report"
grep -Eq '^COSMO_DEPENDENCY_AUDIT_COMPLETE roots=[0-9]+ declarations=[0-9]+ kernel_replay=verified dependency_axioms=0$' \
  "$audit_report"
grep -Eq '^COSMO_PROTECTED_AUDIT_COMPLETE modules=[0-9]+ declarations=[0-9]+ kernel_replay=verified project_initializers=not_executed$' \
  "$audit_report"
end_group

begin_group "Regression-test generated axiom rejection"
generated_report="$RUNNER_TEMP/generated-axiom-report.txt"
if sudo -u cosmoaudit env -i \
  HOME="$AUDIT_HOME" PATH="$PINNED_LEAN_HOME/bin:/usr/bin:/bin" \
  LEAN_PATH="$COSMO_AUDIT_WORKSPACE:$TOOLCHAIN_LIB" \
  LC_ALL=C.UTF-8 LANG=C.UTF-8 TZ=UTC LEAN_NUM_THREADS=1 \
  bash -c 'cd "$1"; shift; exec "$@"' \
  _ "$COSMO_AUDIT_WORKSPACE" \
  "$PINNED_LEAN_HOME/bin/lean" GeneratedAxiomFixture.lean \
  >"$generated_report" 2>&1
then
  cat "$generated_report"
  echo "ERROR: semantic trust audit accepted generated axiom." >&2
  exit 1
fi
cat "$generated_report"
grep -F "project-generated axiom declaration" "$generated_report" >/dev/null
end_group

begin_group "Regression-test unchecked theorem rejection"
unchecked_output="$AUDIT_HOME/GeneratedUncheckedTheorem.olean"
unchecked_report="$RUNNER_TEMP/unchecked-theorem-report.txt"
sudo -u cosmoaudit rm -f "$unchecked_output"
sudo -u cosmoaudit env -i \
  HOME="$AUDIT_HOME" PATH="$PINNED_LEAN_HOME/bin:/usr/bin:/bin" \
  LEAN_PATH="$TOOLCHAIN_LIB" LC_ALL=C.UTF-8 LANG=C.UTF-8 TZ=UTC \
  LEAN_NUM_THREADS=1 \
  bash -c 'cd "$1"; shift; exec "$@"' \
  _ "$COSMO_AUDIT_WORKSPACE" \
  "$PINNED_LEAN_HOME/bin/lean" -o "$unchecked_output" GeneratedUncheckedTheorem.lean
if sudo -u cosmoaudit env -i \
  HOME="$AUDIT_HOME" PATH="$PINNED_LEAN_HOME/bin:/usr/bin:/bin" \
  LEAN_PATH="$AUDIT_HOME:$TOOLCHAIN_LIB" LC_ALL=C.UTF-8 LANG=C.UTF-8 TZ=UTC \
  LEAN_NUM_THREADS=1 \
  "$PINNED_LEAN_HOME/bin/leanchecker" GeneratedUncheckedTheorem \
  >"$unchecked_report" 2>&1
then
  cat "$unchecked_report"
  echo "ERROR: kernel replay accepted unchecked malformed theorem." >&2
  exit 1
fi
cat "$unchecked_report"
grep -F "leanchecker found a problem in GeneratedUncheckedTheorem" \
  "$unchecked_report" >/dev/null
end_group

printf 'COSMO Lean protected integrity pipeline completed successfully authority=%s.\n' "$COSMO_DEPENDENCY_AUTHORITY"
