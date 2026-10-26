#!/usr/bin/env python3
"""A brownfield case's base tests, run from the case's work directory (SPEC "The promotion contract", build step 6):

    python3 "$E2E_CHECKS/base_tests.py" pristine BASE
    python3 "$E2E_CHECKS/base_tests.py" suite BASE

BASE is the case's base, a folder under test/shiploop_e2e/fixtures/ (its ``base.fixture``). Each subcommand copies the
delivered tree (the files git tracks or would track, without .git) into a temporary folder and runs `node --test` there,
so nothing is written into the delivery.

* ``pristine`` (pass-to-pass): the base's own test files, every .js, .cjs and .mjs file under its test/ folder, are written
  over the copy at the base's bytes and only they run. Every one of the base's tests must pass, as many as pass in the base
  itself. A delivery that edited or deleted a base test cannot make it pass, and its own added tests do not run.
* ``suite``: the delivery's own `node --test` passes with no failure, and more tests pass than in the base: the request asks
  for tests of the new behaviour, beside the base's, which it keeps unchanged.

Exit 0 on a pass, 1 with a ``FAIL:`` line naming what failed.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
TEST_SUFFIXES = (".js", ".cjs", ".mjs")
RUN_SECONDS = 120  # a ceiling for one `node --test` run, not a tuning value: the base's own runs take under a second
SUMMARY = re.compile(r"^(?:ℹ|#) (pass|fail) (\d+)\s*$", re.M)  # node's spec and TAP reporters' summary lines


def fail(reason: str) -> None:
    print("FAIL: " + reason)
    sys.exit(1)


def copy_tree(source: Path, dest: Path) -> None:
    """Copy the files `source` tracks or would track (its ignore rules applied) into `dest`; a folder that is not a
    repository is copied whole."""
    listed = subprocess.run(["git", "-C", str(source), "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
                            capture_output=True, stdin=subprocess.DEVNULL)
    if listed.returncode != 0:
        shutil.copytree(source, dest, dirs_exist_ok=True)
        return
    for raw in sorted({name for name in listed.stdout.split(b"\0") if name}):
        relative = Path(raw.decode("utf-8", "surrogateescape"))
        if not (source / relative).is_file():
            continue  # tracked and deleted
        (dest / relative).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / relative, dest / relative)


def node_test(folder: Path, files: list[str]) -> tuple[int | None, int, int, str]:
    """(return code or None on a hang, passed, failed, output tail) of `node --test [files]` in `folder`."""
    try:
        done = subprocess.run(["node", "--test", *files], cwd=folder, capture_output=True, text=True, timeout=RUN_SECONDS,
                              stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        return None, 0, 0, f"node --test did not end within {RUN_SECONDS} s"
    output = done.stdout + done.stderr
    counts = {kind: int(number) for kind, number in SUMMARY.findall(output)}
    return done.returncode, counts.get("pass", 0), counts.get("fail", 0), output[-1500:]


def failing_names(output: str) -> str:
    names = [line.strip().lstrip("✖").strip() for line in output.splitlines() if line.lstrip().startswith("✖")]
    return "; ".join(dict.fromkeys(name for name in names if name != "failing tests:")) or "no failing test named"


def base_folder(name: str) -> Path:
    folder = FIXTURES / name
    if not (folder / "test").is_dir():
        fail(f"the base {name!r} has no test/ folder under {FIXTURES}")
    return folder


def base_count(base: Path, files: list[str]) -> int:
    """How many of the base's tests pass in the base itself: the count a delivery must keep."""
    with tempfile.TemporaryDirectory(prefix="base-tests-") as tmp:
        copy_tree(base, Path(tmp))
        code, passed, failed, output = node_test(Path(tmp), files)
    if code != 0 or failed or not passed:
        fail(f"the base's own tests do not pass in the base (rc {code}, pass {passed}, fail {failed}): {output[-400:]}")
    return passed


def pristine(base: Path) -> None:
    files = sorted(str(path.relative_to(base)) for path in (base / "test").rglob("*")
                   if path.is_file() and path.suffix in TEST_SUFFIXES)
    expected = base_count(base, files)
    with tempfile.TemporaryDirectory(prefix="pristine-") as tmp:
        copy = Path(tmp)
        copy_tree(Path.cwd(), copy)
        for relative in files:
            (copy / relative).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(base / relative, copy / relative)
        code, passed, failed, output = node_test(copy, files)
    if code != 0 or failed or passed != expected:
        fail(f"the base's pristine tests against the delivered source: {passed} of {expected} pass, {failed} fail (rc {code}); "
             f"failing: {failing_names(output)}")
    print(f"the base's {len(files)} pristine test files pass against the delivered source: {passed} of {expected} tests")


def suite(base: Path) -> None:
    files = sorted(str(path.relative_to(base)) for path in (base / "test").rglob("*")
                   if path.is_file() and path.suffix in TEST_SUFFIXES)
    expected = base_count(base, files)
    with tempfile.TemporaryDirectory(prefix="suite-") as tmp:
        copy = Path(tmp)
        copy_tree(Path.cwd(), copy)
        code, passed, failed, output = node_test(copy, [])
    if code != 0 or failed:
        fail(f"the delivery's own node --test: {passed} pass, {failed} fail (rc {code}); failing: {failing_names(output)}")
    if passed <= expected:
        fail(f"the delivery's own node --test passes {passed} tests, no more than the base's {expected}: no test of the new "
             "behaviour was added")
    print(f"the delivery's own node --test passes {passed} tests, the base's {expected} and {passed - expected} more")


SUBCOMMANDS = {"pristine": pristine, "suite": suite}


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("subcommand", choices=sorted(SUBCOMMANDS))
    parser.add_argument("base", help="the case's base: a folder under test/shiploop_e2e/fixtures/")
    args = parser.parse_args(argv)
    SUBCOMMANDS[args.subcommand](base_folder(args.base))


if __name__ == "__main__":
    main()
