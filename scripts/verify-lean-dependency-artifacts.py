#!/usr/bin/env python3
"""Verify cached Lean dependency build artifacts against a reviewed anchor.

The canonical digest algorithm is the OPT-LEAN-001 / QSOL-GEO-REASON receipt
algorithm: sorted relative path, file size, and SHA-256 for every regular file
under each dependency package's `.lake/build` tree.  The expected digest and
artifact count are supplied by reviewed CI source, never by the cache itself.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import stat
from pathlib import Path


class VerificationError(RuntimeError):
    """Raised when dependency artifacts do not match the reviewed contract."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def collect_records(root: Path) -> list[tuple[str, int, str]]:
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


def verify(root: Path, expected_digest: str, expected_count: int) -> None:
    root = Path(os.path.abspath(root))
    records = collect_records(root)
    actual_count = len(records)
    actual_digest = canonical_digest(records)
    if actual_count != expected_count:
        raise VerificationError(
            f"dependency artifact count mismatch: {actual_count} != {expected_count}"
        )
    if actual_digest.lower() != expected_digest.lower():
        raise VerificationError(
            "dependency canonical SHA-256 mismatch: "
            f"{actual_digest} != {expected_digest.lower()}"
        )
    print(
        "Verified Lean dependency artifacts: "
        f"files={actual_count} canonical_sha256={actual_digest}"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--expected-canonical-sha256", required=True)
    parser.add_argument("--expected-artifact-count", type=int, required=True)
    args = parser.parse_args()
    try:
        verify(
            args.root,
            args.expected_canonical_sha256,
            args.expected_artifact_count,
        )
    except VerificationError as error:
        print(f"ERROR: {error}", file=__import__("sys").stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
