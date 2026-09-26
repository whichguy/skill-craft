#!/usr/bin/env python3
"""Bind the selected ShipLoop E2E audit package to its bundled harness."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


SKILL = "shiploop-e2e-audit"
SCRIPT = "resolve_harness.py"
SENTINELS = ("run.py", "check_suite.py", "README.md", "scenarios.json", "suites.json")
IGNORED_DIRECTORIES = {".git", ".mypy_cache", ".pytest_cache", ".ruff_cache", "__pycache__"}
GIT_ENVIRONMENT = {
    "GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR",
    "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES",
    "GIT_CONFIG_COUNT", "GIT_CONFIG_PARAMETERS",
}


class ResolverError(RuntimeError):
    pass


def absolute(value: str | Path, base: Path) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = base / path
    return Path(os.path.abspath(os.fspath(path)))


def directory(path: Path, label: str) -> Path:
    try:
        resolved = path.resolve(strict=True)
    except (OSError, RuntimeError) as error:
        raise ResolverError(f"{label} cannot be resolved: {path}") from error
    if not resolved.is_dir():
        raise ResolverError(f"{label} is not a directory: {path}")
    return resolved


def git_environment() -> dict[str, str]:
    environment = dict(os.environ)
    for key in list(environment):
        if key in GIT_ENVIRONMENT or key.startswith(("GIT_CONFIG_KEY_", "GIT_CONFIG_VALUE_")):
            environment.pop(key, None)
    environment["GIT_OPTIONAL_LOCKS"] = "0"
    environment["GIT_TERMINAL_PROMPT"] = "0"
    return environment


def find_git(requested: str | None, base: Path) -> str | None:
    if requested is None:
        found = shutil.which("git")
        return os.fspath(Path(found).resolve()) if found else None
    path = Path(requested).expanduser()
    has_separator = os.path.sep in requested or (os.path.altsep and os.path.altsep in requested)
    if path.is_absolute() or has_separator:
        path = absolute(requested, base)
        if not path.is_file() or not os.access(path, os.X_OK):
            raise ResolverError(f"Git executable is not runnable: {path}")
        return os.fspath(path.resolve())
    found = shutil.which(requested)
    if not found:
        raise ResolverError(f"Git executable is not available on PATH: {requested}")
    return os.fspath(Path(found).resolve())


def git(git_path: str, checkout: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            [git_path, "-c", "core.hooksPath=/dev/null", "-c", "core.fsmonitor=false",
             "-C", os.fspath(checkout), *arguments],
            capture_output=True, check=False, text=True, encoding="utf-8", errors="replace",
            env=git_environment(), timeout=10,
        )
    except (FileNotFoundError, PermissionError) as error:
        raise ResolverError(f"Git executable is not runnable: {git_path}") from error
    except subprocess.TimeoutExpired as error:
        raise ResolverError("Git timed out while inspecting the checkout") from error


def git_text(git_path: str, checkout: Path, *arguments: str) -> str | None:
    result = git(git_path, checkout, *arguments)
    return result.stdout.strip() if result.returncode == 0 else None


def validate_harness(candidate: Path) -> Path:
    harness = directory(candidate, "harness")
    missing = [name for name in SENTINELS if not (harness / name).is_file()]
    if missing:
        raise ResolverError(f"harness is missing required files ({', '.join(missing)}): {harness}")
    return harness


def harness_digest(harness: Path) -> str:
    """Hash regular stable harness files, excluding interpreter and tool caches."""
    digest = hashlib.sha256()
    files = []
    for path in harness.rglob("*"):
        relative = path.relative_to(harness)
        if any(part in IGNORED_DIRECTORIES for part in relative.parts) or path.suffix == ".pyc":
            continue
        if path.is_symlink():
            raise ResolverError(f"harness contains an unsupported file: {relative.as_posix()}")
        if path.is_dir():
            continue
        if not path.is_file():
            raise ResolverError(f"harness contains an unsupported file: {relative.as_posix()}")
        files.append((relative.as_posix(), path))
    for relative, path in sorted(files):
        digest.update(relative.encode("utf-8", "surrogateescape"))
        digest.update(b"\0")
        try:
            with path.open("rb") as handle:
                while chunk := handle.read(1024 * 1024):
                    digest.update(chunk)
        except OSError as error:
            raise ResolverError(f"cannot read harness file: {relative}") from error
        digest.update(b"\0")
    return digest.hexdigest()


def selected_package() -> tuple[Path, Path, Path, Path]:
    module = Path(__file__)
    invoked = Path(sys.argv[0]) if sys.argv and sys.argv[0] else module
    script = absolute(invoked if invoked.name == SCRIPT else module, Path.cwd())
    logical_package = script.parent.parent
    card = logical_package / "SKILL.md"
    if not card.is_file():
        raise ResolverError(f"selected audit card is missing: {card}")
    try:
        resolved_card = card.resolve(strict=True)
    except (OSError, RuntimeError) as error:
        raise ResolverError(f"selected audit card cannot be resolved: {card}") from error
    return logical_package, directory(logical_package, "selected package"), card, resolved_card


def source_facts(package_root: Path, git_path: str | None) -> tuple[str | None, str | None, bool | None]:
    """Return Git identity only for the exact source-package layout."""
    if git_path is None or package_root.name != SKILL or package_root.parent.name != "skills":
        return None, None, None
    checkout = package_root.parent.parent
    try:
        root_text = git_text(git_path, checkout, "rev-parse", "--path-format=absolute", "--show-toplevel")
        if not root_text:
            return None, None, None
        if Path(root_text).resolve(strict=True) != checkout:
            return None, None, None
        head = git_text(git_path, checkout, "rev-parse", "--verify", "HEAD^{commit}")
        status = git(git_path, checkout, "status", "--porcelain=v1", "--untracked-files=all")
    except (OSError, RuntimeError, ResolverError):
        return None, None, None
    if not head or status.returncode:
        return None, None, None
    return os.fspath(checkout), head, bool(status.stdout.strip())


def explicit_harness(raw_checkout: str, starting_cwd: Path, git_path: str | None) -> tuple[Path, str, str, bool]:
    if git_path is None:
        raise ResolverError("explicit checkout requires a runnable Git executable")
    checkout = directory(absolute(raw_checkout, starting_cwd), "explicit checkout")
    root_text = git_text(git_path, checkout, "rev-parse", "--path-format=absolute", "--show-toplevel")
    if not root_text:
        raise ResolverError(f"explicit checkout is not a Git worktree root: {checkout}")
    try:
        root = Path(root_text).resolve(strict=True)
    except (OSError, RuntimeError) as error:
        raise ResolverError("Git returned an unusable explicit checkout root") from error
    if root != checkout:
        raise ResolverError(f"explicit checkout must be the Git worktree root: {checkout}")
    head = git_text(git_path, checkout, "rev-parse", "--verify", "HEAD^{commit}")
    status = git(git_path, checkout, "status", "--porcelain=v1", "--untracked-files=all")
    if not head or status.returncode:
        raise ResolverError(f"explicit checkout cannot provide Git identity: {checkout}")
    try:
        harness = validate_harness(checkout / "skills" / SKILL / "harness")
    except ResolverError as error:
        raise ResolverError(f"explicit checkout has no usable E2E harness: {error}") from error
    return harness, os.fspath(checkout), head, bool(status.stdout.strip())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cwd", default=os.fspath(Path.cwd()), help="starting working directory")
    parser.add_argument("--checkout", help="optional development checkout root")
    parser.add_argument("--git", help="optional Git executable")
    args = parser.parse_args(argv)
    try:
        starting_cwd = directory(absolute(args.cwd, Path.cwd()), "starting CWD")
        logical_package, package_root, card, resolved_card = selected_package()
        git_path = find_git(args.git, starting_cwd)
        if args.checkout is None:
            harness = validate_harness(logical_package / "harness")
            checkout, head, dirty = source_facts(package_root, git_path)
            binding_source, path_base = "package", starting_cwd
        else:
            try:
                harness, checkout, head, dirty = explicit_harness(args.checkout, starting_cwd, git_path)
            except ResolverError as error:
                raise ResolverError(f"explicit checkout is invalid: {error}") from error
            binding_source, path_base = "explicit", Path(checkout)
        print(json.dumps({
            "harness": os.fspath(harness), "package_root": os.fspath(package_root),
            "binding_source": binding_source, "starting_cwd": os.fspath(starting_cwd),
            "path_base": os.fspath(path_base), "checkout": checkout, "head": head,
            "dirty": dirty, "selected_skill_file": os.fspath(card),
            "resolved_skill_file": os.fspath(resolved_card), "harness_sha256": harness_digest(harness),
            "git": git_path,
        }, sort_keys=True))
        return 0
    except ResolverError as error:
        print(f"resolve_harness: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
