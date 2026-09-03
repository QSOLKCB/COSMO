#!/usr/bin/env python3
"""Derive the frozen Lean import layout for the protected COSMO audit.

Protected CI intentionally supports one top-level COSMO package plus pinned
external dependencies. Local `type: "path"` Lake packages are rejected in this
baseline rather than recursively trusting mutable nested manifests. Project
outputs must use the standard `.lake/build/lib/lean` directory. Every project
`.olean` artifact path is passed to the trusted Lean runner, which derives the
exact module `Name` from Lean's own artifact metadata/search-path machinery.
"""

from __future__ import annotations

import argparse
import json
import os
import stat
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class AuditLayoutError(RuntimeError):
    """Raised when the frozen Lean artifact layout is not auditable."""


@dataclass(frozen=True)
class Analysis:
    lean_path_entries: tuple[Path, ...]
    trusted_path_entries: tuple[Path, ...]
    project_output_dirs: tuple[Path, ...]
    project_artifacts: tuple[Path, ...]


def _absolute(path: Path, *, relative_to: Path | None = None) -> Path:
    if not path.is_absolute():
        if relative_to is None:
            raise AuditLayoutError(f"relative path has no base: {path}")
        path = relative_to / path
    return Path(os.path.abspath(path))


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _require_within(path: Path, root: Path, *, description: str) -> None:
    if not _is_within(path, root):
        raise AuditLayoutError(f"{description} escapes frozen workspace: {path}")


def _reject_symlink_components(path: Path, root: Path, *, description: str) -> None:
    _require_within(path, root, description=description)
    current = root
    for part in path.relative_to(root).parts:
        current = current / part
        try:
            mode = current.lstat().st_mode
        except FileNotFoundError as error:
            raise AuditLayoutError(f"missing {description}: {current}") from error
        if stat.S_ISLNK(mode):
            raise AuditLayoutError(f"symlinked {description} is forbidden: {current}")


def _load_manifest(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise AuditLayoutError(f"Lake manifest is missing or symlinked: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise AuditLayoutError(f"cannot read Lake manifest {path}: {error}") from error
    if not isinstance(value, dict):
        raise AuditLayoutError(f"Lake manifest is not an object: {path}")
    return value


def _manifest_packages_dir(manifest: Path, workspace: Path) -> Path:
    data = _load_manifest(manifest)
    value = data.get("packagesDir", ".lake/packages")
    if not isinstance(value, str) or not value:
        raise AuditLayoutError(f"invalid packagesDir in {manifest}")
    packages_dir = _absolute(Path(value), relative_to=manifest.parent)
    _require_within(packages_dir, workspace, description="Lake packages directory")
    _reject_symlink_components(
        packages_dir, workspace, description="Lake packages directory"
    )

    packages = data.get("packages", [])
    if not isinstance(packages, list):
        raise AuditLayoutError(f"invalid packages list in {manifest}")
    for package in packages:
        if not isinstance(package, dict):
            raise AuditLayoutError(f"invalid package entry in {manifest}")
        if package.get("type") == "path":
            name = package.get("name", "<unnamed>")
            raise AuditLayoutError(
                "protected COSMO baseline forbids local Lake path packages; "
                f"found {name!r} in {manifest}"
            )
    return packages_dir


def _standard_output(root: Path) -> Path:
    return root / ".lake" / "build" / "lib" / "lean"


def _is_lake_config_olean(path: Path) -> bool:
    parts = path.parts
    return len(parts) >= 2 and parts[-2:] == (".lake", "lakefile.olean")


def _contains(path: Path, root: Path) -> bool:
    return _is_within(path, root)


def _validate_workspace_oleans(
    workspace: Path, allowed_outputs: tuple[Path, ...]
) -> None:
    for current_text, directory_names, file_names in os.walk(
        workspace, topdown=True, followlinks=False
    ):
        current = Path(current_text)
        for name in list(directory_names):
            candidate = current / name
            if candidate.is_symlink():
                relative = candidate.relative_to(workspace)
                if ".lake" in relative.parts:
                    raise AuditLayoutError(
                        f"symlink in Lean state/output tree is forbidden: {candidate}"
                    )
                directory_names.remove(name)

        for name in file_names:
            if not name.endswith(".olean"):
                continue
            candidate = current / name
            mode = candidate.lstat().st_mode
            if stat.S_ISLNK(mode):
                raise AuditLayoutError(f"symlinked .olean is forbidden: {candidate}")
            if not stat.S_ISREG(mode):
                raise AuditLayoutError(f"non-regular .olean is forbidden: {candidate}")
            if _is_lake_config_olean(candidate):
                continue
            if not any(_contains(candidate, output) for output in allowed_outputs):
                raise AuditLayoutError(
                    "Lean .olean exists outside inventoried standard output "
                    f"directories: {candidate}"
                )


def analyze(workspace: Path, manifest: Path, toolchain_lib: Path) -> Analysis:
    workspace = _absolute(workspace)
    manifest = _absolute(manifest, relative_to=workspace)
    toolchain_lib = _absolute(toolchain_lib)
    if not workspace.is_dir() or workspace.is_symlink():
        raise AuditLayoutError(f"frozen workspace is not a regular directory: {workspace}")
    if not toolchain_lib.is_dir() or toolchain_lib.is_symlink():
        raise AuditLayoutError(f"trusted Lean library root is invalid: {toolchain_lib}")

    _reject_symlink_components(manifest, workspace, description="Lake manifest")
    packages_dir = _manifest_packages_dir(manifest, workspace)

    project_output = _standard_output(workspace)
    _reject_symlink_components(
        project_output, workspace, description="project Lean output directory"
    )
    if not project_output.is_dir():
        raise AuditLayoutError(
            "top-level package did not produce standard .lake/build/lib/lean output"
        )

    external_outputs: list[Path] = []
    for package in sorted(packages_dir.iterdir(), key=lambda path: path.name):
        if package.is_symlink():
            raise AuditLayoutError(f"symlinked dependency package: {package}")
        if not package.is_dir():
            continue
        output = _standard_output(package)
        if output.exists():
            _reject_symlink_components(
                output, workspace, description="dependency Lean output directory"
            )
            if not output.is_dir():
                raise AuditLayoutError(f"invalid dependency Lean output: {output}")
            external_outputs.append(output)

    allowed_outputs = tuple(external_outputs + [project_output])
    _validate_workspace_oleans(workspace, allowed_outputs)

    project_artifacts: list[Path] = []
    for artifact in sorted(project_output.rglob("*.olean"), key=str):
        mode = artifact.lstat().st_mode
        if stat.S_ISLNK(mode):
            raise AuditLayoutError(f"symlinked project .olean is forbidden: {artifact}")
        if not stat.S_ISREG(mode):
            raise AuditLayoutError(f"non-regular project .olean is forbidden: {artifact}")
        project_artifacts.append(artifact)
    if not project_artifacts:
        raise AuditLayoutError("no project-controlled Lean .olean artifacts found")

    # Trusted modules always precede project outputs. A project artifact using
    # the same module name as the toolchain or a pinned dependency therefore
    # resolves to the trusted artifact; CosmoTrust then rejects the project
    # artifact because its exact path does not round-trip through `findOLean`.
    trusted_entries = tuple([toolchain_lib] + external_outputs)
    lean_entries = tuple([toolchain_lib] + external_outputs + [project_output])
    for path in lean_entries:
        rendered = str(path)
        if os.pathsep in rendered or "\n" in rendered or "\0" in rendered:
            raise AuditLayoutError(f"unsafe Lean import path: {path}")

    return Analysis(
        lean_path_entries=lean_entries,
        trusted_path_entries=trusted_entries,
        project_output_dirs=(project_output,),
        project_artifacts=tuple(project_artifacts),
    )


def _write_private(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    path.chmod(0o600)


def self_test() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        workspace = Path(temporary)
        root_output = _standard_output(workspace)
        external_root = workspace / ".lake" / "packages" / "external"
        external_output = _standard_output(external_root)
        toolchain_lib = workspace / "trusted-toolchain-lib"
        for directory in (root_output, external_output, toolchain_lib):
            directory.mkdir(parents=True)

        (root_output / "Root.olean").write_bytes(b"root")
        quoted = root_output / "Foo" / "Bar.Baz.olean"
        quoted.parent.mkdir(parents=True)
        quoted.write_bytes(b"quoted")
        (external_output / "External.olean").write_bytes(b"external")
        (workspace / ".lake" / "lakefile.olean").write_bytes(b"config")
        manifest = workspace / "lake-manifest.json"
        manifest.write_text(
            json.dumps(
                {
                    "version": "1.2.0",
                    "packagesDir": ".lake/packages",
                    "packages": [{"type": "git", "name": "external"}],
                    "name": "fixture",
                    "lakeDir": ".lake",
                }
            ),
            encoding="utf-8",
        )

        result = analyze(workspace, manifest, toolchain_lib)
        assert quoted in result.project_artifacts
        assert root_output in result.project_output_dirs
        assert external_output in result.trusted_path_entries
        assert result.trusted_path_entries[0] == toolchain_lib
        assert result.lean_path_entries[-1] == root_output

        hidden = root_output / "Hidden.olean"
        hidden.symlink_to(root_output / "Root.olean")
        try:
            analyze(workspace, manifest, toolchain_lib)
        except AuditLayoutError as error:
            assert "symlink" in str(error)
        else:
            raise AssertionError("symlinked module output was accepted")
        hidden.unlink()

        custom = workspace / ".lake" / "hidden" / "lib" / "lean" / "Escape.olean"
        custom.parent.mkdir(parents=True)
        custom.write_bytes(b"escape")
        try:
            analyze(workspace, manifest, toolchain_lib)
        except AuditLayoutError as error:
            assert "outside inventoried" in str(error)
        else:
            raise AssertionError("custom hidden Lean output was accepted")
        custom.unlink()

        manifest.write_text(
            json.dumps(
                {
                    "version": "1.2.0",
                    "packagesDir": ".lake/packages",
                    "packages": [
                        {
                            "type": "path",
                            "name": "local",
                            "dir": ".lake/packages/local",
                        }
                    ],
                    "name": "fixture",
                    "lakeDir": ".lake",
                }
            ),
            encoding="utf-8",
        )
        try:
            analyze(workspace, manifest, toolchain_lib)
        except AuditLayoutError as error:
            assert "forbids local Lake path packages" in str(error)
        else:
            raise AssertionError("local path package was accepted")

    print("Lean audit layout self-test passed.")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--workspace", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--toolchain-lib", type=Path)
    parser.add_argument("--lean-path-output", type=Path)
    parser.add_argument("--trusted-lean-path-output", type=Path)
    parser.add_argument("--artifacts-output", type=Path)
    args = parser.parse_args()

    if args.self_test:
        self_test()
        return 0

    required = {
        "--workspace": args.workspace,
        "--manifest": args.manifest,
        "--toolchain-lib": args.toolchain_lib,
        "--lean-path-output": args.lean_path_output,
        "--trusted-lean-path-output": args.trusted_lean_path_output,
        "--artifacts-output": args.artifacts_output,
    }
    missing = [name for name, value in required.items() if value is None]
    if missing:
        parser.error(f"missing required arguments: {', '.join(missing)}")

    assert args.workspace is not None
    assert args.manifest is not None
    assert args.toolchain_lib is not None
    try:
        result = analyze(args.workspace, args.manifest, args.toolchain_lib)
    except AuditLayoutError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1

    assert args.lean_path_output is not None
    assert args.trusted_lean_path_output is not None
    assert args.artifacts_output is not None
    _write_private(
        args.lean_path_output,
        os.pathsep.join(str(path) for path in result.lean_path_entries) + "\n",
    )
    _write_private(
        args.trusted_lean_path_output,
        os.pathsep.join(str(path) for path in result.trusted_path_entries) + "\n",
    )
    _write_private(
        args.artifacts_output,
        "".join(f"{artifact}\n" for artifact in result.project_artifacts),
    )

    print(
        "Frozen Lean audit layout prepared: "
        f"{len(result.project_output_dirs)} project output dir(s), "
        f"{len(result.project_artifacts)} project artifact(s), and "
        f"{len(result.lean_path_entries)} total import path(s)."
    )
    for artifact in result.project_artifacts:
        print(f"  project artifact: {artifact}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
