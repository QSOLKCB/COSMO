#!/usr/bin/env bash
set -euo pipefail

: "${GITHUB_WORKSPACE:?}"
: "${RUNNER_TEMP:?}"
: "${PINNED_LEAN_HOME:?}"
: "${LEAN_NUM_THREADS:?}"
: "${COSMO_BUILD_WORKSPACE:?}"
: "${COSMO_AUDIT_WORKSPACE:?}"

BUILD_HOME=/tmp/cosmobuild-home
AUDIT_HOME=/tmp/cosmoaudit-home
LEAN_PATH_FILE="$RUNNER_TEMP/cosmo-lean-path.txt"
TRUSTED_LEAN_PATH_FILE="$RUNNER_TEMP/cosmo-trusted-lean-path.txt"
ARTIFACTS_FILE="$RUNNER_TEMP/cosmo-project-artifacts.txt"
MANIFEST_SNAPSHOT="$RUNNER_TEMP/cosmo-lake-manifest.prebuild.json"
TOOLCHAIN_LIB="$PINNED_LEAN_HOME/lib/lean"

# Canonical dependency artifact authority imported from the reviewed
# OPT-LEAN-001 / QSOL-GEO-REASON Lean 4.33.1 + mathlib v4.33.1 receipt.
EXPECTED_DEP_CANONICAL_SHA256=91f7181f1657481a8a00a3f4fe67b8d5663951838b5a0a76ef2adbd8b54e66d3
EXPECTED_DEP_ARTIFACT_COUNT=37312

begin_group() {
  printf '::group::%s\n' "$1"
}

end_group() {
  printf '::endgroup::\n'
}

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

begin_group "Self-test protected audit helpers and scan reviewed Lean source"
python3 scripts/prepare-lean-audit.py --self-test
./scripts/check-lean-trust.sh
end_group

begin_group "Prepare isolated build identities"
sudo useradd --system --no-create-home --shell /usr/sbin/nologin cosmobuild 2>/dev/null || true
sudo useradd --system --no-create-home --shell /usr/sbin/nologin cosmoaudit 2>/dev/null || true
sudo install -d -o cosmobuild -g cosmobuild -m 0700 "$BUILD_HOME"
sudo install -d -o cosmoaudit -g cosmoaudit -m 0700 "$AUDIT_HOME"
sudo chown -R cosmobuild:cosmobuild "$COSMO_BUILD_WORKSPACE"

sudo chmod o+x \
  /home/runner \
  /home/runner/work \
  "$RUNNER_TEMP" \
  "$GITHUB_WORKSPACE/.." \
  "$GITHUB_WORKSPACE"

if sudo -u cosmobuild test -w "$GITHUB_WORKSPACE"; then
  echo "ERROR: isolated build identity can write the reviewed checkout." >&2
  exit 1
fi
for path in \
  scripts/check-lean-trust.sh \
  scripts/prepare-lean-audit.py \
  scripts/run-lean-integrity-ci.sh \
  scripts/verify-lean-dependency-artifacts.py \
  CosmoTrust.lean \
  audit/AxiomAudit.lean \
  COSMO.lean \
  lakefile.lean \
  lean-toolchain
do
  if sudo -u cosmobuild test -w "$path"; then
    echo "ERROR: isolated build identity can write reviewed trust input: $path" >&2
    exit 1
  fi
done
sudo -u cosmobuild test -x "$PINNED_LEAN_HOME/bin/lean"
sudo -u cosmobuild test -x "$PINNED_LEAN_HOME/bin/lake"
test -d "$TOOLCHAIN_LIB"
end_group

begin_group "Regenerate dependency configuration before project compilation"
# Never trust a manifest restored by the performance cache. Remove it and ask
# Lake to resolve the reviewed dependency declaration afresh. `lake update`
# evaluates package configuration but does not compile COSMO project modules.
sudo -u cosmobuild env -i \
  HOME="$BUILD_HOME" \
  PATH="$PINNED_LEAN_HOME/bin:/usr/bin:/bin" \
  LC_ALL=C.UTF-8 \
  LANG=C.UTF-8 \
  TZ=UTC \
  LEAN_NUM_THREADS="$LEAN_NUM_THREADS" \
  bash -c 'cd "$1"; rm -f lake-manifest.json; exec "$2" update' \
  _ "$COSMO_BUILD_WORKSPACE" "$PINNED_LEAN_HOME/bin/lake"

manifest="$COSMO_BUILD_WORKSPACE/lake-manifest.json"
if [ -L "$manifest" ] || [ ! -f "$manifest" ]; then
  echo "ERROR: fresh Lake manifest is missing, non-regular, or symlinked." >&2
  exit 1
fi

# PR A deliberately forbids local path packages. This removes mutable nested
# package manifests from the protected trust boundary until a later reviewed
# policy explicitly adds them.
python3 - "$manifest" <<'PY'
import json
import sys
from pathlib import Path

manifest = Path(sys.argv[1])
data = json.loads(manifest.read_text(encoding="utf-8"))
packages = data.get("packages", [])
if not isinstance(packages, list):
    raise SystemExit("ERROR: fresh Lake manifest packages entry is not a list")
path_packages = [
    package.get("name", "<unnamed>")
    for package in packages
    if isinstance(package, dict) and package.get("type") == "path"
]
if path_packages:
    raise SystemExit(
        "ERROR: protected COSMO baseline forbids local Lake path packages: "
        + ", ".join(map(str, path_packages))
    )
print("Fresh Lake manifest contains no local path packages.")
PY
end_group

begin_group "Authenticate dependency artifacts before project compilation"
python3 scripts/verify-lean-dependency-artifacts.py \
  --root "$COSMO_BUILD_WORKSPACE/.lake/packages" \
  --expected-canonical-sha256 "$EXPECTED_DEP_CANONICAL_SHA256" \
  --expected-artifact-count "$EXPECTED_DEP_ARTIFACT_COUNT"

sudo install -o root -g root -m 0444 "$manifest" "$MANIFEST_SNAPSHOT"
if sudo -u cosmobuild test -w "$MANIFEST_SNAPSHOT"; then
  echo "ERROR: build identity can modify immutable manifest snapshot." >&2
  exit 1
fi
manifest_sha="$(sha256sum "$MANIFEST_SNAPSHOT" | awk '{print $1}')"
echo "Frozen fresh pre-build Lake manifest sha256=$manifest_sha"
end_group

begin_group "Freeze dependencies and expose only project build output"
terminate_identity cosmobuild

# Freeze the entire resolved source/dependency/configuration tree. The project
# compiler receives write permission only to the standard top-level build
# directory. This prevents command elaborators from replacing dependency proof
# objects, manifests, package configuration, or reviewed source during build.
sudo chown -R root:root "$COSMO_BUILD_WORKSPACE"
sudo chmod -R a+rX "$COSMO_BUILD_WORKSPACE"
sudo chmod -R a-w "$COSMO_BUILD_WORKSPACE"
sudo rm -rf "$COSMO_BUILD_WORKSPACE/.lake/build"
sudo install -d -o cosmobuild -g cosmobuild -m 0700 \
  "$COSMO_BUILD_WORKSPACE/.lake/build"

if sudo -u cosmobuild test -w "$COSMO_BUILD_WORKSPACE"; then
  echo "ERROR: build identity can write frozen workspace root." >&2
  exit 1
fi
if sudo -u cosmobuild test -w "$manifest"; then
  echo "ERROR: build identity can write frozen Lake manifest." >&2
  exit 1
fi
if sudo -u cosmobuild test -w "$COSMO_BUILD_WORKSPACE/.lake/packages"; then
  echo "ERROR: build identity can write frozen dependency tree." >&2
  exit 1
fi
if ! sudo -u cosmobuild test -w "$COSMO_BUILD_WORKSPACE/.lake/build"; then
  echo "ERROR: build identity cannot write isolated project build output." >&2
  exit 1
fi
end_group

begin_group "Build current COSMO source against frozen dependencies"
sudo -u cosmobuild env -i \
  HOME="$BUILD_HOME" \
  PATH="$PINNED_LEAN_HOME/bin:/usr/bin:/bin" \
  LC_ALL=C.UTF-8 \
  LANG=C.UTF-8 \
  TZ=UTC \
  LEAN_NUM_THREADS="$LEAN_NUM_THREADS" \
  bash -c 'cd "$1"; shift; exec "$@"' \
  _ "$COSMO_BUILD_WORKSPACE" \
  "$PINNED_LEAN_HOME/bin/lake" build
end_group

begin_group "Terminate project build descendants"
terminate_identity cosmobuild
end_group

begin_group "Verify dependency configuration remained immutable"
if [ -L "$manifest" ] || [ ! -f "$manifest" ]; then
  echo "ERROR: project build replaced the Lake manifest path." >&2
  exit 1
fi
cmp --silent "$MANIFEST_SNAPSHOT" "$manifest" || {
  echo "ERROR: project build changed the fresh pre-build Lake manifest." >&2
  exit 1
}
python3 scripts/verify-lean-dependency-artifacts.py \
  --root "$COSMO_BUILD_WORKSPACE/.lake/packages" \
  --expected-canonical-sha256 "$EXPECTED_DEP_CANONICAL_SHA256" \
  --expected-artifact-count "$EXPECTED_DEP_ARTIFACT_COUNT"
echo "Dependency configuration and artifacts remained immutable during project build."
end_group

begin_group "Verify isolated project source stayed identical"
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
tracked = {
    Path(os.fsdecode(item))
    for item in tracked_raw.split(b"\0")
    if item
}


def fingerprint(path: Path) -> tuple[str, str, int]:
    info = path.lstat()
    executable = info.st_mode & 0o111
    if stat.S_ISLNK(info.st_mode):
        return ("symlink", os.readlink(path), executable)
    if stat.S_ISREG(info.st_mode):
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        return ("file", digest, executable)
    return ("other", str(stat.S_IFMT(info.st_mode)), executable)


failures: list[str] = []
for relative in sorted(tracked, key=str):
    source_path = reviewed / relative
    built_path = built / relative
    if not built_path.exists() and not built_path.is_symlink():
        failures.append(f"missing tracked path: {relative}")
        continue
    if fingerprint(source_path) != fingerprint(built_path):
        failures.append(f"tracked path changed during build: {relative}")

actual: set[Path] = set()
for path in built.rglob("*"):
    relative = path.relative_to(built)
    if not relative.parts:
        continue
    if relative.parts[0] == ".lake":
        continue
    if relative == Path("lake-manifest.json"):
        continue
    if path.is_file() or path.is_symlink():
        actual.add(relative)

extras = sorted(actual - tracked, key=str)
if extras:
    failures.extend(f"unexpected build-created path: {path}" for path in extras)

if failures:
    for failure in failures:
        print(f"ERROR: {failure}")
    raise SystemExit(1)

print(f"Isolated source verification passed for {len(tracked)} tracked path(s).")
PY
end_group

begin_group "Freeze project outputs and create one-time compiler enclave"
sudo chown -R root:root "$COSMO_BUILD_WORKSPACE/.lake/build"
sudo chmod -R a+rX "$COSMO_BUILD_WORKSPACE/.lake/build"
sudo chmod -R a-w "$COSMO_BUILD_WORKSPACE/.lake/build"
sudo rm -rf "$COSMO_AUDIT_WORKSPACE"
sudo install -d -o cosmoaudit -g cosmoaudit -m 0700 "$COSMO_AUDIT_WORKSPACE"

if sudo -u cosmoaudit test -w "$COSMO_BUILD_WORKSPACE/.lake/build"; then
  echo "ERROR: audit identity can write frozen project proof outputs." >&2
  exit 1
fi
if ! sudo -u cosmoaudit test -w "$COSMO_AUDIT_WORKSPACE"; then
  echo "ERROR: audit identity cannot populate one-time compiler enclave." >&2
  exit 1
fi
if sudo -u cosmobuild test -w "$COSMO_AUDIT_WORKSPACE"; then
  echo "ERROR: build identity can write audit compiler enclave." >&2
  exit 1
fi
end_group

begin_group "Derive complete frozen project artifact set"
python3 scripts/prepare-lean-audit.py \
  --workspace "$COSMO_BUILD_WORKSPACE" \
  --manifest "$manifest" \
  --toolchain-lib "$TOOLCHAIN_LIB" \
  --lean-path-output "$LEAN_PATH_FILE" \
  --trusted-lean-path-output "$TRUSTED_LEAN_PATH_FILE" \
  --artifacts-output "$ARTIFACTS_FILE"
sudo chown root:root "$LEAN_PATH_FILE" "$TRUSTED_LEAN_PATH_FILE" "$ARTIFACTS_FILE"
sudo chmod 0444 "$LEAN_PATH_FILE" "$TRUSTED_LEAN_PATH_FILE" "$ARTIFACTS_FILE"
end_group

begin_group "Compile reviewed auditor without project import paths"
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
  "$staging/CosmoTrustAudit.lean" \
  "$COSMO_AUDIT_WORKSPACE/CosmoTrustAudit.lean"
sudo install -o cosmoaudit -g cosmoaudit -m 0600 \
  "$staging/GeneratedAxiomFixture.lean" \
  "$COSMO_AUDIT_WORKSPACE/GeneratedAxiomFixture.lean"
sudo install -o cosmoaudit -g cosmoaudit -m 0600 \
  "$staging/GeneratedUncheckedTheorem.lean" \
  "$COSMO_AUDIT_WORKSPACE/GeneratedUncheckedTheorem.lean"

# Auditor compilation sees only the pinned Lean toolchain. Project output paths
# cannot shadow Lean.Replay, Lean.collectAxioms, or any other trusted import.
sudo -u cosmoaudit env -i \
  HOME="$AUDIT_HOME" \
  PATH="$PINNED_LEAN_HOME/bin:/usr/bin:/bin" \
  LEAN_PATH="$TOOLCHAIN_LIB" \
  LC_ALL=C.UTF-8 \
  LANG=C.UTF-8 \
  TZ=UTC \
  LEAN_NUM_THREADS=1 \
  bash -c 'cd "$1"; shift; exec "$@"' \
  _ "$COSMO_AUDIT_WORKSPACE" \
  "$PINNED_LEAN_HOME/bin/lean" \
  -o "$COSMO_AUDIT_WORKSPACE/CosmoTrustAudit.olean" \
  "$COSMO_AUDIT_WORKSPACE/CosmoTrustAudit.lean"

sudo chown -R root:root "$COSMO_AUDIT_WORKSPACE"
sudo find "$COSMO_AUDIT_WORKSPACE" -type f -exec chmod 0444 {} +
sudo chmod 0555 "$COSMO_AUDIT_WORKSPACE"
rm -rf "$staging"
trap cleanup EXIT

if sudo -u cosmoaudit test -w "$COSMO_AUDIT_WORKSPACE"; then
  echo "ERROR: audit identity can modify staged auditor." >&2
  exit 1
fi
if sudo -u cosmobuild test -w "$COSMO_AUDIT_WORKSPACE"; then
  echo "ERROR: build identity can modify staged auditor." >&2
  exit 1
fi
end_group

begin_group "Replay exact project artifacts and run semantic audit"
lean_path="$(cat "$LEAN_PATH_FILE")"
mapfile -t artifacts < "$ARTIFACTS_FILE"
test "${#artifacts[@]}" -gt 0
audit_report="$RUNNER_TEMP/cosmo-semantic-audit.txt"
sudo -u cosmoaudit env -i \
  HOME="$AUDIT_HOME" \
  PATH="$PINNED_LEAN_HOME/bin:/usr/bin:/bin" \
  LEAN_PATH="$lean_path" \
  LC_ALL=C.UTF-8 \
  LANG=C.UTF-8 \
  TZ=UTC \
  LEAN_NUM_THREADS=1 \
  bash -c 'cd "$1"; shift; exec "$@"' \
  _ "$COSMO_AUDIT_WORKSPACE" \
  "$PINNED_LEAN_HOME/bin/lean" --run \
  "$COSMO_AUDIT_WORKSPACE/CosmoTrustAudit.lean" \
  "${artifacts[@]}" | tee "$audit_report"

marker_count="$(grep -cE '^COSMO_PROTECTED_AUDIT_COMPLETE modules=[0-9]+ declarations=[0-9]+ kernel_replay=verified project_initializers=not_executed$' "$audit_report")"
test "$marker_count" -eq 1
end_group

begin_group "Regression-test generated axiom rejection"
generated_report="$RUNNER_TEMP/generated-axiom-report.txt"
if sudo -u cosmoaudit env -i \
  HOME="$AUDIT_HOME" \
  PATH="$PINNED_LEAN_HOME/bin:/usr/bin:/bin" \
  LEAN_PATH="$COSMO_AUDIT_WORKSPACE:$TOOLCHAIN_LIB" \
  LC_ALL=C.UTF-8 \
  LANG=C.UTF-8 \
  TZ=UTC \
  LEAN_NUM_THREADS=1 \
  bash -c 'cd "$1"; shift; exec "$@"' \
  _ "$COSMO_AUDIT_WORKSPACE" \
  "$PINNED_LEAN_HOME/bin/lean" \
  "$COSMO_AUDIT_WORKSPACE/GeneratedAxiomFixture.lean" \
  >"$generated_report" 2>&1
then
  cat "$generated_report"
  echo "ERROR: semantic trust audit accepted a generated axiom declaration." >&2
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
  HOME="$AUDIT_HOME" \
  PATH="$PINNED_LEAN_HOME/bin:/usr/bin:/bin" \
  LEAN_PATH="$TOOLCHAIN_LIB" \
  LC_ALL=C.UTF-8 \
  LANG=C.UTF-8 \
  TZ=UTC \
  LEAN_NUM_THREADS=1 \
  "$PINNED_LEAN_HOME/bin/lean" \
  -o "$unchecked_output" \
  "$COSMO_AUDIT_WORKSPACE/GeneratedUncheckedTheorem.lean"

if sudo -u cosmoaudit env -i \
  HOME="$AUDIT_HOME" \
  PATH="$PINNED_LEAN_HOME/bin:/usr/bin:/bin" \
  LEAN_PATH="$AUDIT_HOME:$TOOLCHAIN_LIB" \
  LC_ALL=C.UTF-8 \
  LANG=C.UTF-8 \
  TZ=UTC \
  LEAN_NUM_THREADS=1 \
  "$PINNED_LEAN_HOME/bin/leanchecker" GeneratedUncheckedTheorem \
  >"$unchecked_report" 2>&1
then
  cat "$unchecked_report"
  echo "ERROR: kernel replay accepted an unchecked malformed theorem." >&2
  exit 1
fi
cat "$unchecked_report"
grep -F "leanchecker found a problem in GeneratedUncheckedTheorem" \
  "$unchecked_report" >/dev/null
end_group

printf 'COSMO isolated Lean integrity pipeline completed successfully.\n'
