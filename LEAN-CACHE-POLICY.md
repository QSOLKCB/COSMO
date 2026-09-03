# COSMO Lean Dependency Cache and Trust Policy

This document is normative for **Phase B1 / OPT-LEAN-001**.  COSMO keeps a
routine verified-reuse lane and a separate cold-trust authority.  They answer
different questions and their evidence must not be conflated.

Normative optimization source: immutable QSOL OPT v1.0.0,
`OPT-LEAN-001 — Trust-Preserving Lean Dependency Reuse`.

## Routine lane: `COSMO CI / Lean 4 formal integrity`

The pull-request/main CI lane may reuse dependency state only after two
independent identities have been verified.

### Source cache

The source-cache key binds:

- cache schema;
- runner OS and `x86_64` architecture;
- Lean 4.33.1 distribution SHA-256;
- exact `lean-toolchain` bytes;
- exact `lakefile.lean` bytes;
- frozen `lake-manifest.json` SHA-256.

A source-cache hit is not trusted because the key matched.  Before use,
`scripts/verify-lean-source-state.py`:

1. requires generated dependency `.lake` state to be absent;
2. rejects Git replacement refs, grafts, alternates, hooks and worktree config;
3. disables replacement processing and repository-local executable Git state;
4. verifies each manifest Git dependency at the exact revision;
5. compares tracked bytes and executable/symlink modes with the pinned commit
   tree; and
6. rejects every untracked source-tree entry outside `.git`.

The source receipt binds the dependency declaration SHA-256, frozen manifest
SHA-256 and each dependency revision/tree identity.

### Build-artifact cache

Compiled dependency state has a separate cache key and separate authority.
The reviewed anchor is `audit/lean-dependency-anchor.json`.

`scripts/verify-lean-dependency-artifacts.py` hashes every regular file under
all dependency `.lake/build` trees as a sorted stream of:

```text
path NUL size NUL sha256 LF
```

The reviewed anchor commits cryptographically to that complete per-file stream
and to the exact artifact count.  A run-local receipt is also taken before
COSMO compilation and recomputed afterwards as an immutability witness.

The cache never authenticates itself.  A receipt restored from the same cache
is not authoritative.

### Current reviewed routine anchor

The initial B1 anchor inherits the dependency build population already accepted
by the protected PR-A kernel replay and is bound to:

- Lean: `4.33.1`;
- Lean Linux archive SHA-256:
  `890afd185370f85666025b883914ab4f4b339136f8c96167b69cfb62aecaf235`;
- Mathlib commit:
  `0df444a360eaa60ab8c11dca51a86af692955474`;
- Lake manifest SHA-256:
  `da84374efd9e7a24d40bbd0273c55409f1957fe121b6a795d3d5776381edc86e`;
- dependency build artifact count: `130468`;
- canonical dependency SHA-256:
  `c3018c5d6758f15709c9578478973d0c131e29531a0fecdb4eb56487dd5677df`.

Those values authorize **verified reuse only**.  They are not evidence that the
dependency graph was rebuilt from source on every routine run.

### Project rebuild and audit

After both dependency identities are accepted:

1. dependency source and build state become root-owned/read-only;
2. only COSMO's isolated output directory is writable by `cosmobuild`;
3. `CosmoTrust`, `cosmovirus`, and `COSMO` are rebuilt directly with the
   hash-pinned Lean binary and warnings-as-errors;
4. dependency artifacts must still reproduce the run-local and reviewed
   receipts;
5. the trusted runner derives the external dependency closure from the actual
   compiled project headers and kernel-replays it;
6. every captured COSMO module is kernel-replayed and semantically audited; and
7. generated-axiom and malformed-unchecked-theorem negative fixtures must fail
   for the expected reasons.

A cache mismatch fails closed.  CI does not silently replace a failed
verification with trust in the cache key.

## Cold-trust lane

`.github/workflows/lean-cold-trust.yml` is manually dispatched and restores no
Lean dependency source or build cache.  It is the only workflow intended to
support the statement:

> the dependency graph was reconstructed from pinned source under the cold
> trust boundary on this exact run.

The cold lane must use the same Lean/toolchain/dependency declarations and the
same final project kernel/semantic audits, but its dependency build receipt is
run-local evidence rather than the routine cache anchor.  Routine and cold
wall times must be reported separately.

## Rollback conditions

Disable or invalidate reuse if any of the following changes unexpectedly:

- toolchain or Lean distribution identity;
- dependency declaration or manifest identity;
- dependency commit-tree verification;
- build-artifact count or canonical digest;
- project module set;
- kernel replay result;
- semantic axiom/declaration audit;
- deterministic Python results; or
- the ability of an unprivileged project build to write dependency state.

A faster wrong result is not an optimization.
