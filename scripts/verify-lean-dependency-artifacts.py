#!/usr/bin/env python3
"""Create and verify a run-local receipt for Lean dependency build artifacts.

This receipt is an immutability witness, not an external provenance authority.
Protected CI first validates the dependency proof environment with the pinned
Lean kernel, then snapshots every regular file under each dependency package's
`.lake/build` tree. After COSMO project compilation, the same file set must
produce the identical canonical digest and artifact count.

The externally anchored OPT-LEAN-001 two-cache design remains a later roadmap
optimization. PR A deliberately avoids pretending that Mathlib's public cache
artifact population is identical to QSOL-GEO-REASON's cold-build receipt.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import sys
from pathlib import Path
from typing import Any

SCHEMA = "COSMO-LEAN-DEPS-RUN-RECEIPT-1"


class VerificationError(RuntimeError):
    """Raised when dependency artifact state is malformed or changed."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def collect_records(root: Path) -> list[tuple[str, int, str]]:
    root = Path(os.path.abspath(root))
    if not root.is_dir() or root.is_symlink():
        raise VerificationError(f"dependency root is missing or symlinked: {root}")

    records: list[tuple[str, int, str]] = []
    for package in sorted(root.iterdir(), key=lambda path: path.name):
        if package.is_symlink():
            raise VerificationError(f"symlinked dependency package: {package}")
        if not package.is_dir():
            continue
        build = package / ".lake" / "build"
        if not build.exists():
            continue
        if build.is_symlink() or not build.is_dir():
            raise VerificationError(f"invalid dependency build tree: {build}")
        for path in sorted(build.rglob("*"), key=lambda item: item.as_posix()):
            mode = path.lstat().st_mode
            if stat.S_ISLNK(mode):
                raise VerificationError(f"symlink in dependency build tree: {path}")
            if stat.S_ISDIR(mode):
                continue
            if not stat.S_ISREG(mode):
                raise VerificationError(f"non-regular dependency artifact: {path}")
            relative = path.relative_to(root).as_posix()
            records.append((relative, path.stat().st_size, sha256_file(path)))

    if not records:
        raise VerificationError("no dependency build artifacts found")
    if not any(path.endswith(".olean") for path, _size, _digest in records):
        raise VerificationError("dependency artifact set contains no .olean files")
    return records


def canonical_digest(records: list[tuple[str, int, str]]) -> str:
    digest = hashlib.sha256()
    for path, size, file_digest in records:
        digest.update(path.encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(size).encode("ascii"))
        digest.update(b"\0")
        digest.update(file_digest.encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def snapshot(root: Path) -> dict[str, Any]:
    records = collect_records(root)
    return {
        "schema": SCHEMA,
        "artifact_count": len(records),
        "canonical_sha256": canonical_digest(records),
    }


def write_receipt(root: Path, receipt: Path) -> None:
    data = snapshot(root)
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt.write_text(json.dumps(data, sort_keys=True) + "\n", encoding="utf-8")
    receipt.chmod(0o600)
    print(
        "Lean dependency run receipt created: "
        f"files={data['artifact_count']} canonical_sha256={data['canonical_sha256']}"
    )


def verify_receipt(root: Path, receipt: Path) -> None:
    if receipt.is_symlink() or not receipt.is_file():
        raise VerificationError(f"dependency run receipt is missing or symlinked: {receipt}")
    try:
        expected = json.loads(receipt.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise VerificationError(f"cannot read dependency run receipt: {error}") from error
    actual = snapshot(root)
    if expected.get("schema") != SCHEMA:
        raise VerificationError(
            f"dependency receipt schema mismatch: {expected.get('schema')!r} != {SCHEMA!r}"
        )
    for field in ("artifact_count", "canonical_sha256"):
        if expected.get(field) != actual[field]:
            raise VerificationError(
                f"dependency artifact {field} changed: "
                f"{actual[field]!r} != {expected.get(field)!r}"
            )
    print(
        "Lean dependency run receipt verified: "
        f"files={actual['artifact_count']} canonical_sha256={actual['canonical_sha256']}"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("snapshot", "verify"):
        sub = subparsers.add_parser(command)
        sub.add_argument("--root", type=Path, required=True)
        sub.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()

    try:
        if args.command == "snapshot":
            write_receipt(args.root, args.receipt)
        else:
            verify_receipt(args.root, args.receipt)
    except VerificationError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
