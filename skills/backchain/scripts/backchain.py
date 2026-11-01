#!/usr/bin/env python3
"""Backchain's command line: the deterministic half of a planning run.

The model plans and reviews; this script checks, packages, exports and keeps the books.
It never launches a model and never runs a planned step. Standard library only, Python 3.9+.

  check PLAN                  structural check (the seven invariants) and completion; prints a receipt
  package PLAN --out FILE     the plan with recomputed parallel_groups, written atomically; prints a receipt
  export PLAN [--out FILE]    the Plan Dispatcher execution graph (execution-graph/v1) of a complete plan

Exit codes: 0 ok; 1 the plan fails (invalid structure, or not exportable); 3 the command could not run
(unreadable input, not JSON, bad arguments). A could-not-run is never a finding about the plan.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
import backchain_graph as graph  # noqa: E402

CHECK_SCHEMA = "backchain-check/v1"
EXIT_OK = 0
EXIT_FAILS = 1
EXIT_UNAVAILABLE = 3
EXPORT_VALIDATION = ("structurally valid and completionStatus=complete; done strings carry each produce's confirm "
                     "method when the plan declares one; readiness and semantic verification remain dispatcher-owned")


class Unavailable(Exception):
    """The command could not run (input unreadable, not JSON, wrong shape for the command): never a finding."""


class Fails(Exception):
    """The plan fails what the command requires."""


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_plan(path: Path) -> tuple:
    """(raw bytes, parsed JSON) of a plan file; Unavailable when it cannot be read or is not JSON."""
    try:
        data = Path(path).read_bytes()
    except OSError as exc:
        raise Unavailable(f"cannot read {path}: {exc.strerror or exc}") from exc
    try:
        return data, graph.loads(data)
    except graph.CheckUnavailable as exc:
        raise Unavailable(f"{path}: {exc}") from exc


_LONE_SURROGATE = re.compile("[\ud800-\udfff]")


def json_text(value: Any) -> str:
    """Two-space JSON with a final newline, writable as UTF-8.

    A plan may hold a lone surrogate (JSON allows the escape, JS strings allow the code unit); like
    JS's well-formed JSON.stringify, it is written back as its ``\\uXXXX`` escape.
    """
    text = json.dumps(value, indent=2, ensure_ascii=False)
    return _LONE_SURROGATE.sub(lambda match: "\\u%04x" % ord(match.group()), text) + "\n"


def write_atomically(path: Path, text: str) -> None:
    """Replace ``path`` in one rename, keeping its mode (a new file is 0644, not mkstemp's private 0600)."""
    path = Path(path)
    mode = path.stat().st_mode & 0o777 if path.exists() else 0o644
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(text)
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise


def check_receipt(data: bytes, plan: Any, locator: str) -> Dict[str, Any]:
    """The structural verdict on the packaged plan: what a reader needs to trust or repair it."""
    packaged = graph.package(plan)
    structure = graph.validate_structure(packaged)
    completion = graph.completion_status(packaged, structure)
    return {
        "schema": CHECK_SCHEMA,
        "plan": locator,
        "plan_sha256": sha256(data),
        "packaged_sha256": sha256(graph.js_stringify(packaged).encode("utf-8")),
        "ok": structure["ok"],
        "failures": structure["failures"],
        "completion": completion["status"],
        "open_goal_needs": completion["open_goal_needs"],
        "unresolved_count": completion["unresolved_count"],
        "parallel_groups": graph.compute_parallel_groups(packaged),
        "counts": graph.counts(packaged),
        "unconfirmed_produces": graph.unconfirmed_produces(packaged),
    }


def summary(receipt: Dict[str, Any]) -> str:
    counts = receipt["counts"]
    if receipt["ok"]:
        verdict = f"valid, {receipt['completion']}"
    else:
        invariants = sorted({failure["invariant"] for failure in receipt["failures"]})
        verdict = f"invalid on invariant(s) {', '.join(map(str, invariants))}"
    return (f"backchain check: {verdict}; {counts['steps']} steps, {len(receipt['parallel_groups'])} parallel "
            f"group(s), {len(receipt['unconfirmed_produces'])} unconfirmed produce(s)")


# ---------------------------------------------------------------- export (Plan Dispatcher execution-graph/v1)

def done_string(produce: str, confirmation: Optional[Dict[str, Any]]) -> str:
    """A done string carries its confirmation method inline, so an executor reading only contract.done learns it."""
    if not confirmation:
        return produce
    if confirmation["level"] == "unconfirmable":
        return f"{produce}. Confirm by: unconfirmable here — {confirmation['by']}"
    if confirmation["level"] == "inspect":
        return f"{produce}. Confirm by: {confirmation['by']} (inspection is sufficient)"
    return f"{produce}. Confirm by: {confirmation['by']}"


def unique(values: List[Any]) -> List[Any]:
    return list(dict.fromkeys(values))


def export_graph(plan: Any, plan_sha256: str) -> Dict[str, Any]:
    """Plan Dispatcher's execution graph for a structurally valid, complete plan (packaged first).

    Ported from the Backchain checkout's scripts/export-execution-graph.js. That exporter refuses an
    unpackaged plan on invariant 6; this one packages first, so stored parallel_groups never block an export.
    Plan Dispatcher's own ``validate-graph`` remains the executor's acceptance check.
    """
    packaged = graph.package(plan)
    structure = graph.validate_structure(packaged)
    if not structure["ok"]:
        raise Fails("Backchain plan is structurally invalid: " + json.dumps(structure["failures"]))
    completion = graph.completion_status(packaged, structure)
    if completion["status"] != "complete":
        raise Fails("Backchain plan is incomplete: " + json.dumps(
            {"unresolved_count": completion["unresolved_count"], "open_goal_needs": completion["open_goal_needs"]}))
    if not packaged["steps"]:
        raise Fails("Backchain plan has no work to dispatch")
    steps = []
    for step in packaged["steps"]:
        confirmations = {entry["produces"]: entry for entry in step.get("confirm", [])}
        steps.append({
            "id": step["id"],
            "deps": unique([entry["from"] for entry in step["inputs"] if entry["from"] is not None]),
            # Backchain permits repeated condition wording, including one need from different suppliers; the compact
            # condition lists must not collapse the dependencies or the input bindings kept in source.inputs.
            "contract": {
                "task": step["statement"],
                "ready": unique([entry["need"] for entry in step["inputs"]]),
                "done": unique([done_string(produce, confirmations.get(produce)) for produce in step["produces"]]),
            },
        })
    return {
        "version": 1,
        "source": {
            "format": "backchain",
            "plan_sha256": plan_sha256,
            "goal": packaged["goal"],
            "initial_state": packaged["initial_state"],
            "goal_needs": packaged.get("goal_needs", []),
            "inputs": {step["id"]: step["inputs"] for step in packaged["steps"]},
            "validation": EXPORT_VALIDATION,
        },
        "steps": steps,
    }


# ---------------------------------------------------------------- commands

def command_check(args: argparse.Namespace) -> int:
    data, plan = read_plan(args.plan)
    receipt = check_receipt(data, plan, str(Path(args.plan).absolute()))
    sys.stdout.write(json_text(receipt))
    print(summary(receipt), file=sys.stderr)
    return EXIT_OK if receipt["ok"] else EXIT_FAILS


def command_package(args: argparse.Namespace) -> int:
    data, plan = read_plan(args.plan)
    out = Path(args.out).absolute()
    write_atomically(out, json_text(graph.package(plan)))
    receipt = check_receipt(data, plan, str(Path(args.plan).absolute()))
    receipt["output"] = str(out)
    receipt["output_sha256"] = sha256(out.read_bytes())
    sys.stdout.write(json_text(receipt))
    print(summary(receipt) + f"; packaged to {out}", file=sys.stderr)
    return EXIT_OK if receipt["ok"] else EXIT_FAILS


def command_export(args: argparse.Namespace) -> int:
    data, plan = read_plan(args.plan)
    try:
        exported = export_graph(plan, sha256(data))
    except Fails as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return EXIT_FAILS
    text = json_text(exported)
    if args.out:
        out = Path(args.out).absolute()
        write_atomically(out, text)
        print(f"backchain export: {len(exported['steps'])} step(s) to {out}; check it with Plan Dispatcher's "
              f"`validate-graph` before binding a run", file=sys.stderr)
    else:
        sys.stdout.write(text)
    return EXIT_OK


def parser() -> argparse.ArgumentParser:
    top = argparse.ArgumentParser(prog="backchain.py", description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = top.add_subparsers(dest="command", required=True)
    check = commands.add_parser("check", help="structural check and completion of a plan")
    check.add_argument("plan", type=Path)
    check.set_defaults(run=command_check)
    package = commands.add_parser("package", help="write the plan with recomputed parallel_groups")
    package.add_argument("plan", type=Path)
    package.add_argument("--out", type=Path, required=True)
    package.set_defaults(run=command_package)
    export = commands.add_parser("export", help="Plan Dispatcher execution graph of a complete plan")
    export.add_argument("plan", type=Path)
    export.add_argument("--out", type=Path)
    export.set_defaults(run=command_export)
    return top


def main(argv: Optional[List[str]] = None) -> int:
    try:
        args = parser().parse_args(argv)
    except SystemExit as exc:
        return EXIT_OK if exc.code == 0 else EXIT_UNAVAILABLE
    try:
        return args.run(args)
    except Unavailable as exc:
        print(f"backchain {args.command} could not run: {exc}; this is not a finding about the plan", file=sys.stderr)
        return EXIT_UNAVAILABLE


if __name__ == "__main__":
    raise SystemExit(main())
