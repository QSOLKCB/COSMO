#!/usr/bin/env python3
"""Verify the top-level cold-build dependency repository.

The routine source verifier operates on packages listed by a Lake manifest.
The cold lane also needs to authenticate the Mathlib repository that owns that
manifest before executing Mathlib's own Lake configuration.  This wrapper
reuses the same hardened Git/tree machinery and records the verified revision
and tree identity.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from types import ModuleType


def load_source_verifier(path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location("cosmo_source_verifier", path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"cannot load source verifier: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--expected-revision", required=True)
    parser.add_argument("--expected-url", required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument(
        "--source-verifier",
        type=Path,
        default=Path(__file__).with_name("verify-lean-source-state.py"),
    )
    args = parser.parse_args()

    revision = args.expected_revision.lower()
    if len(revision) != 40:
        raise SystemExit("expected revision must be a 40-character Git object id")
    if not args.repo.is_dir() or args.repo.is_symlink():
        raise SystemExit(f"cold dependency root missing/invalid: {args.repo}")

    verifier = load_source_verifier(args.source_verifier)
    verifier.sanitize_git_metadata(args.repo, "mathlib")
    head = verifier.git_text(args.repo, "rev-parse", "HEAD").lower()
    if head != revision:
        raise SystemExit(f"cold Mathlib revision mismatch: {head} != {revision}")
    verifier.git_text(args.repo, "cat-file", "-e", f"{revision}^{{commit}}")
    tree = verifier.verify_commit_tree(args.repo, "mathlib", revision)
    verifier.restore_manifest_remote(args.repo, "mathlib", args.expected_url)

    snapshot = {
        "schema": "COSMO-COLD-ROOT-SOURCE-1",
        "name": "mathlib",
        "revision": revision,
        "tree": tree,
        "url": args.expected_url,
    }
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n")
    print(
        "COSMO cold root source verified "
        f"revision={revision} tree={tree}"
    )


if __name__ == "__main__":
    main()
