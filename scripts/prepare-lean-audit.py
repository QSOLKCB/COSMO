#!/usr/bin/env python3
"""Derive a frozen Lean import path and complete project module set.

The audit phase must not execute project Lake configuration.  This helper reads
the already-frozen Lake artifact layout, classifies local path packages from the
Lake manifest, rejects symlinked output paths, and emits deterministic files for
direct `lean` / `leanchecker` invocations.
"""

from __future__ import annotations

import argparse
import json
import os
import stat
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class AuditLayoutError(RuntimeError):
    """Raised when the frozen Lean artifact layout is not auditable."""


@dataclass(frozen=True)
class Analysis:
    lean_path_entries: tuple[Path, ...]
    project_output_dirs: tuple[Path, ...]
    project_modules: tuple[str, ...]
    project_package_roots: tuple[Path, ...]


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
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise AuditLayoutError(f"cannot read Lake manifest {path}: {error}") from error
    if not isinstance(value, dict):
        raise AuditLayoutError(f"Lake manifest is not an object: {path}")
    return value


def _collect_manifest_regions(
    manifest: Path,
    workspace: Path,
    *,
    project_roots: set[Path],
    package_dirs: set[Path],
    seen: set[Path],
) -> None:
    manifest = _absolute(manifest)
    _require_within(manifest, workspace, description="Lake manifest")
    _reject_symlink_components(manifest, workspace, description="Lake manifest")
    if manifest in seen:
        return
    seen.add(manifest)

    data = _load_manifest(manifest)
    manifest_root = manifest.parent

    packages_dir_value = data.get("packagesDir", ".lake/packages")
    if not isinstance(packages_dir_value, str) or not packages_dir_value:
        raise AuditLayoutError(f"invalid packagesDir in {manifest}")
    packages_dir = _absolute(Path(packages_dir_value), relative_to=manifest_root)
    _require_within(packages_dir, workspace, description="Lake packages directory")
    package_dirs.add(packages_dir)

    packages = data.get("packages", [])
    if not isinstance(packages, list):
        raise AuditLayoutError(f"invalid packages list in {manifest}")

    for package in packages:
        if not isinstance(package, dict) or package.get("type") != "path":
            continue
        directory = package.get("dir")
        if not isinstance(directory, str) or not directory:
            raise AuditLayoutError(f"path package without a directory in {manifest}")
        package_root = _absolute(Path(directory), relative_to=manifest_root)
        _require_within(package_root, workspace, description="local Lake package")
        _reject_symlink_components(
            package_root, workspace, description="local Lake package root"
        )
        project_roots.add(package_root)

        manifest_name = package.get("manifestFile", "lake-manifest.json")
        if not isinstance(manifest_name, str) or not manifest_name:
            raise AuditLayoutError(
                f"invalid local package manifest name for {package_root}"
            )
        nested_manifest = _absolute(Path(manifest_name), relative_to=package_root)
        if nested_manifest.exists():
            _collect_manifest_regions(
                nested_manifest,
                workspace,
                project_roots=project_roots,
                package_dirs=package_dirs,
                seen=seen,
            )


def _contains_build_segment(path: Path, workspace: Path) -> bool:
    parts = path.relative_to(workspace).parts
    return any(
        parts[index] == ".lake" and parts[index + 1] == "build"
        for index in range(len(parts) - 1)
    )


def _discover_output_dirs(workspace: Path, package_dirs: set[Path]) -> set[Path]:
    output_dirs: set[Path] = set()

    for current_text, directory_names, file_names in os.walk(
        workspace, topdown=True, followlinks=False
    ):
        current = Path(current_text)

        for name in list(directory_names):
            candidate = current / name
            if candidate.is_symlink():
                direct_package_link = any(candidate.parent == root for root in package_dirs)
                if direct_package_link or _contains_build_segment(candidate, workspace):
                    raise AuditLayoutError(
                        f"symlink in Lean package/output path is forbidden: {candidate}"
                    )
                directory_names.remove(name)

        for name in file_names:
            candidate = current / name
            if candidate.is_symlink() and _contains_build_segment(candidate, workspace):
                raise AuditLayoutError(
                    f"symlinked Lean build artifact is forbidden: {candidate}"
                )

        relative_parts = current.relative_to(workspace).parts
        if len(relative_parts) >= 4 and relative_parts[-4:] == (
            ".lake",
            "build",
            "lib",
            "lean",
        ):
            output_dirs.add(current)

    if not output_dirs:
        raise AuditLayoutError("no .lake/build/lib/lean directories found")
    return output_dirs


def _classify_region(
    path: Path, *, project_roots: set[Path], package_dirs: set[Path]
) -> str:
    matches: list[tuple[int, int, str]] = []
    for root in project_roots:
        if _is_within(path, root):
            matches.append((len(root.parts), 1, "project"))
    for root in package_dirs:
        if _is_within(path, root):
            matches.append((len(root.parts), 0, "external"))
    if not matches:
        raise AuditLayoutError(f"cannot classify Lean output directory: {path}")
    return max(matches)[2]


def _module_name(output_dir: Path, olean: Path) -> str:
    relative = olean.relative_to(output_dir)
    if relative.suffix != ".olean":
        raise AuditLayoutError(f"unexpected Lean artifact suffix: {olean}")
    parts = list(relative.with_suffix("").parts)
    if not parts or any(not part for part in parts):
        raise AuditLayoutError(f"cannot derive Lean module name from {olean}")
    return ".".join(parts)


def analyze(workspace: Path, manifest: Path) -> Analysis:
    workspace = _absolute(workspace)
    manifest = _absolute(manifest, relative_to=workspace)
    if not workspace.is_dir():
        raise AuditLayoutError(f"frozen workspace is not a directory: {workspace}")

    project_roots: set[Path] = {workspace}
    package_dirs: set[Path] = set()
    _collect_manifest_regions(
        manifest,
        workspace,
        project_roots=project_roots,
        package_dirs=package_dirs,
        seen=set(),
    )

    output_dirs = _discover_output_dirs(workspace, package_dirs)
    classified = {
        output_dir: _classify_region(
            output_dir, project_roots=project_roots, package_dirs=package_dirs
        )
        for output_dir in output_dirs
    }
    project_output_dirs = {
        output_dir for output_dir, kind in classified.items() if kind == "project"
    }
    if not project_output_dirs:
        raise AuditLayoutError("no project-controlled Lean output directories found")

    top_level_output = workspace / ".lake" / "build" / "lib" / "lean"
    if top_level_output not in project_output_dirs:
        raise AuditLayoutError(
            "top-level package did not produce the standard .lake/build/lib/lean output"
        )

    all_modules: dict[str, list[tuple[Path, str]]] = {}
    for output_dir in sorted(output_dirs, key=str):
        kind = classified[output_dir]
        for olean in sorted(output_dir.rglob("*.olean"), key=str):
            mode = olean.lstat().st_mode
            if stat.S_ISLNK(mode):
                raise AuditLayoutError(f"symlinked .olean is forbidden: {olean}")
            if not stat.S_ISREG(mode):
                raise AuditLayoutError(f"non-regular .olean is forbidden: {olean}")
            module = _module_name(output_dir, olean)
            all_modules.setdefault(module, []).append((olean, kind))

    project_modules: set[str] = set()
    for module, locations in all_modules.items():
        project_locations = [path for path, kind in locations if kind == "project"]
        if not project_locations:
            continue
        if len(locations) != 1:
            rendered = ", ".join(str(path) for path, _kind in locations)
            raise AuditLayoutError(
                f"project module {module} is shadowed by multiple artifacts: {rendered}"
            )
        project_modules.add(module)

    if not project_modules:
        raise AuditLayoutError("no project-controlled Lean modules found")

    external_dirs = sorted(
        (path for path, kind in classified.items() if kind == "external"), key=str
    )
    local_dirs = sorted(project_output_dirs, key=str)
    lean_path_entries = tuple(external_dirs + local_dirs)
    for path in lean_path_entries:
        rendered = str(path)
        if os.pathsep in rendered or "\n" in rendered or "\0" in rendered:
            raise AuditLayoutError(f"unsafe Lean import path: {path}")

    return Analysis(
        lean_path_entries=lean_path_entries,
        project_output_dirs=tuple(local_dirs),
        project_modules=tuple(sorted(project_modules)),
        project_package_roots=tuple(sorted(project_roots, key=str)),
    )


def _write_private(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    path.chmod(0o600)


def self_test() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        workspace = Path(temporary)
        root_output = workspace / ".lake/build/lib/lean"
        external_output = workspace / ".lake/packages/external/.lake/build/lib/lean"
        local_root = workspace / ".lake/packages/local"
        local_output = local_root / ".lake/build/lib/lean"
        for directory in (root_output, external_output, local_output):
            directory.mkdir(parents=True)

        (root_output / "Root.olean").write_bytes(b"root")
        (external_output / "External.olean").write_bytes(b"external")
        (local_output / "Local.olean").write_bytes(b"local")
        (workspace / "lake-manifest.json").write_text(
            json.dumps(
                {
                    "version": "1.2.0",
                    "packagesDir": ".lake/packages",
                    "packages": [
                        {"type": "git", "name": "external"},
                        {
                            "type": "path",
                            "name": "local",
                            "dir": ".lake/packages/local",
                            "manifestFile": "lake-manifest.json",
                        },
                    ],
                    "name": "fixture",
                    "lakeDir": ".lake",
                }
            ),
            encoding="utf-8",
        )

        result = analyze(workspace, workspace / "lake-manifest.json")
        assert result.project_modules == ("Local", "Root")
        assert local_output in result.project_output_dirs
        assert external_output in result.lean_path_entries

        hidden = root_output / "Hidden.olean"
        hidden.symlink_to(root_output / "Root.olean")
        try:
            analyze(workspace, workspace / "lake-manifest.json")
        except AuditLayoutError as error:
            assert "symlink" in str(error)
        else:
            raise AssertionError("symlinked module output was accepted")

    print("Lean audit layout self-test passed.")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--workspace", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--lean-path-output", type=Path)
    parser.add_argument("--modules-output", type=Path)
    args = parser.parse_args()

    if args.self_test:
        self_test()
        return 0

    required = {
        "--workspace": args.workspace,
        "--manifest": args.manifest,
        "--lean-path-output": args.lean_path_output,
        "--modules-output": args.modules_output,
    }
    missing = [name for name, value in required.items() if value is None]
    if missing:
        parser.error(f"missing required arguments: {', '.join(missing)}")

    try:
        result = analyze(args.workspace, args.manifest)
    except AuditLayoutError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1

    assert args.lean_path_output is not None
    assert args.modules_output is not None
    _write_private(
        args.lean_path_output,
        os.pathsep.join(str(path) for path in result.lean_path_entries) + "\n",
    )
    _write_private(
        args.modules_output,
        "".join(f"{module}\n" for module in result.project_modules),
    )

    print(
        "Frozen Lean audit layout prepared: "
        f"{len(result.project_package_roots)} project package root(s), "
        f"{len(result.project_output_dirs)} project output dir(s), "
        f"{len(result.project_modules)} project module(s), and "
        f"{len(result.lean_path_entries)} total import path(s)."
    )
    for root in result.project_package_roots:
        print(f"  project package root: {root}")
    for module in result.project_modules:
        print(f"  project module: {module}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
