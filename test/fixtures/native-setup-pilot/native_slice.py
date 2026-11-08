#!/usr/bin/env python3
"""Point the frozen step-slice runner at an external case catalog and fixture root."""
from __future__ import annotations

import argparse
import contextlib
import importlib.util
import os
import subprocess
import sys
from pathlib import Path

SLICE_RELATIVE = Path("test") / "shiploop_e2e" / "slice.py"


def _adapter_args(argv: list[str] | None) -> tuple[argparse.Namespace, list[str]]:
    # Preserve native --case for forwarding; abbreviation would consume it as --case-catalog.
    parser = argparse.ArgumentParser(add_help=False, allow_abbrev=False)
    parser.add_argument("--harness-root", required=True, type=Path,
                        help="frozen skill-craft checkout")
    parser.add_argument("--expected-head", required=True,
                        help="full Git HEAD expected for the frozen checkout")
    parser.add_argument("--case-catalog", required=True, type=Path,
                        help="external step_cases.json-compatible catalog")
    parser.add_argument("--fixture-root", required=True, type=Path,
                        help="external root containing case fixtures and seed-state folders")
    return parser.parse_known_args(argv)


def _load_frozen_slice(harness_root: Path, expected_head: str, case_catalog: Path, fixture_root: Path):
    harness_root = harness_root.expanduser().resolve()
    case_catalog = case_catalog.expanduser().resolve()
    fixture_root = fixture_root.expanduser().resolve()
    source = harness_root / SLICE_RELATIVE
    if not source.is_file() or not case_catalog.is_file() or not fixture_root.is_dir():
        raise SystemExit("harness slice, external case catalog, and fixture root must exist")
    try:
        head = subprocess.run(["git", "-C", str(harness_root), "rev-parse", "HEAD"], capture_output=True,
                              text=True, check=True, timeout=10).stdout.strip()
        status = subprocess.run(["git", "-C", str(harness_root), "status", "--porcelain",
                                 "--untracked-files=all"], capture_output=True, text=True,
                                check=True, timeout=10).stdout
    except (OSError, subprocess.SubprocessError) as error:
        raise SystemExit(f"cannot verify frozen harness checkout: {type(error).__name__}") from error
    if head != expected_head:
        raise SystemExit(f"frozen harness HEAD is {head}, expected {expected_head}")
    # Matching HEAD is insufficient if adjacent imports can still be changed or shadowed.
    if status:
        raise SystemExit("frozen harness checkout must be clean (tracked, staged, and untracked changes found)")

    spec = importlib.util.spec_from_file_location("shiploop_native_frozen_slice", source)
    if spec is None or spec.loader is None:
        raise SystemExit(f"cannot load frozen slice module at {source}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    module.STEP_CASES = case_catalog
    module.FIXTURES = fixture_root
    return module


@contextlib.contextmanager
def isolated_git_discovery(output: Path | None):
    """Bound run_checks Git discovery for no-.git exports without hiding owned worktrees."""
    if output is None:
        yield
        return
    old = os.environ.get("GIT_CEILING_DIRECTORIES")
    ceiling = str(output.expanduser().resolve())
    os.environ["GIT_CEILING_DIRECTORIES"] = ceiling + (os.pathsep + old if old else "")
    try:
        yield
    finally:
        if old is None:
            os.environ.pop("GIT_CEILING_DIRECTORIES", None)
        else:
            os.environ["GIT_CEILING_DIRECTORIES"] = old


def main(argv: list[str] | None = None) -> int:
    args, forwarded = _adapter_args(argv)
    frozen_slice = _load_frozen_slice(args.harness_root, args.expected_head,
                                      args.case_catalog, args.fixture_root)
    native_args = frozen_slice.parser().parse_args(forwarded)
    # A strategy seed bypasses step-plan; without an outer stop, slice_complete treats it as already finished.
    if native_args.seed_at == "test-strategy" and native_args.stop_after is None and native_args.regrade is None:
        raise SystemExit("--seed-at test-strategy requires --stop-after (for example, --stop-after plan)")
    output = native_args.regrade or native_args.output
    with isolated_git_discovery(output):
        return frozen_slice.main(forwarded)


if __name__ == "__main__":
    raise SystemExit(main())
