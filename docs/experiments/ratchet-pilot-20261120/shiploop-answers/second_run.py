#!/usr/bin/env python3
"""A second ShipLoop run on the project an earlier delivery left: the owner's ruling as its request, graded by the case's
own checks.

    second_run.py --prior DIR --output DIR --baseline FILE --host H --model M --effort E [run.py arguments ...]

It reads the eight checks of ``ticket-due-times`` from ``test/shiploop_e2e/cases.json`` and the request from
``late-notes.json`` beside it (``notes["start"]``, the owner's ruling word for word), refuses when ``<prior>/work`` is
not a Git checkout or has uncommitted changes, and replaces itself with ``test/shiploop_e2e/run.py`` run from the root
of the build copy it lives in: ``--continue-from <prior>`` starts the new run in a copy of ``<prior>/work``, as case
``custom``, and every ``--check`` grades it.  The argument list is built here, never through a shell, so
``$E2E_CHECKS`` reaches run.py unexpanded.  ``--print`` prints that list as JSON and runs nothing.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]   # the repository root of this build copy
CASE = "ticket-due-times"


def refusal(prior: Path) -> str | None:
    """Why ``prior``'s project cannot be continued from, or None."""
    work = prior / "work"
    if not (work / ".git").exists():
        return f"second_run: {work} has no .git; nothing was started"
    status = subprocess.run(["git", "-C", str(work), "status", "--porcelain"], capture_output=True, text=True, check=False)
    if status.returncode != 0:
        return f"second_run: git status failed in {work}: {status.stderr.strip()}; nothing was started"
    if status.stdout.strip():
        return f"second_run: {work} has uncommitted changes; nothing was started"
    return None


def command(args: argparse.Namespace, passed: list[str]) -> list[str]:
    checks = json.loads((ROOT / "test" / "shiploop_e2e" / "cases.json").read_text(encoding="utf-8"))[CASE]["checks"]
    request = json.loads((HERE / "late-notes.json").read_text(encoding="utf-8"))["notes"]["start"]
    argv = ["python3", "-B", "test/shiploop_e2e/run.py", "--source", "checkout", "--prompt", request,
            "--continue-from", str(args.prior), "--host", args.host, "--model", args.model, "--effort", args.effort,
            "--output", str(args.output), "--baseline", str(args.baseline), "--quiet"]
    for check in checks:
        argv += ["--check", check]
    return argv + passed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], allow_abbrev=False)
    for name in ("--prior", "--output", "--baseline"):
        parser.add_argument(name, type=Path, required=True)
    for name in ("--host", "--model", "--effort"):
        parser.add_argument(name, required=True)
    parser.add_argument("--print", action="store_true", help="print the run.py argument list as JSON and run nothing")
    args, passed = parser.parse_known_args()
    args.prior = args.prior.expanduser().resolve()
    why = refusal(args.prior)
    if why:
        print(why, file=sys.stderr)
        return 2
    argv = command(args, passed)
    if args.print:
        print(json.dumps(argv, indent=1, ensure_ascii=False))
        return 0
    os.chdir(ROOT)
    os.execvp(argv[0], argv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
