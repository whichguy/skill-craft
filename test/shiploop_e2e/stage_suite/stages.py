#!/usr/bin/env python3
"""The stage suite's runner (docs/plans/shiploop-stage-suite.md, "Runner and selectors"): list, verify and render over a
selection of scenarios, no model.

    python3 test/shiploop_e2e/stage_suite/stages.py list   [SELECTOR ...] [--json]
    python3 test/shiploop_e2e/stage_suite/stages.py verify [SELECTOR ...] [--json]
    python3 test/shiploop_e2e/stage_suite/stages.py render [SELECTOR ...] [--keep DIR] [--json]
    python3 test/shiploop_e2e/stage_suite/stages.py verify @inner -validate-existing/all-match +catch

It sits below the harness's top level, so it is in neither the evaluator digest nor the qualification snapshot, and it runs from any
working directory. It reads scenarios with stage_build, runs their checks with stage_oracle and holds neither's logic.

Selectors (a union of the includes, then the excludes removed; no include means all):

    all                  every scenario (the default; an empty scenario folder is "nothing selected", not an error)
    <stage>              every scenario of one stage; ``improve@<stage>`` names an Improve stage and ``spec`` never selects it
    <stage>/<scenario>   one scenario
    @prelude @inner @outer @improve   a phase (an ``improve@`` stage is phase improve)
    +<tag>               every scenario with that tag
    -<selector>          remove what the selector selects

A selector that is not one of these, or that selects nothing, is a usage error naming it. Excludes are written with a leading
dash, which argparse would take for an option, so ``main`` hides them from it first.

The tiers (this step builds the first two; ``live``, ``grade`` and ``report`` are step 3 of the plan):
- ``verify`` (T0) composes each scenario's seed tree from files, with no ShipLoop run. The oracle must pass ``reference/good``
  (every planted condition caught, every control held, nothing else failing) and must fail, for each ``reference/bad-*``, every id
  its meta.json declares. An id that fails and is not declared is a surprise: reported, not an error.
- ``render`` (T1) builds each scenario's run with stage_build.render and runs its ``render`` checks on the packet. An id no render
  check proves is "not exercised", never a pass. A scenario the builder cannot build yet (an Improve or outer stage) is skipped.
A scenario without the tier is skipped (it counts in the total, not as a failure).

Output is a plain table (per scenario: tier, PASS / FAIL / skipped, and each id caught, held, missed or not exercised) and a
one-line total; ``--json`` prints the same data as one document. Exit codes: 0 everything selected passed, 1 something failed,
2 a usage or schema error (the ScenarioError text is printed), 3 nothing selected.
"""
from __future__ import annotations

import argparse
import contextlib
import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
HARNESS = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HARNESS))
import stage_build as sb  # noqa: E402  (also puts the harness and skills/shiploop/scripts on sys.path)
import stage_oracle  # noqa: E402
import shiploop_stage_spec as stage_spec  # noqa: E402

PHASES = (*stage_spec.PHASES, "improve")
COMMANDS = ("list", "verify", "render")
NOT_BUILT_COMMANDS = ("live", "grade", "report")  # named when asked for, never stubbed
HIDE = "\x1f"  # in front of an exclude (-<selector>) while argparse reads the command line
VALUE_OPTIONS = ("--keep", "--cases-dir")
EXIT_PASS, EXIT_FAIL, EXIT_USAGE, EXIT_NOTHING = 0, 1, 2, 3
NOT_BUILT = "live, grade and report are not built yet (step 3 of docs/plans/shiploop-stage-suite.md)"
DETAIL = 300  # characters of a check's detail the table keeps


class UsageError(Exception):
    """A command line that selects or asks for something that does not exist; the message names it."""


# ---------------------------------------------------------------------------------------------------------------- selectors

def phase_of(sc: sb.Scenario) -> str:
    """The phase of the stage a scenario exercises: prelude, inner or outer, and improve for an ``improve@`` stage."""
    return "improve" if sc.stage.startswith(sb.IMPROVE) else stage_spec.STAGE_SPEC[sc.stage].phase


def _stages() -> str:
    return ", ".join(stage_spec.STAGES)


def _resolve(token: str, scenarios: list[sb.Scenario], typed: str | None = None) -> set[str]:
    """The ids of the scenarios one selector (without its dash) selects; UsageError, naming `typed` (the selector as it was
    written, default `token`), when it is not a selector."""
    typed = typed or token
    if token == "all":
        return {sc.id for sc in scenarios}
    if token.startswith("@"):
        if token[1:] not in PHASES:
            raise UsageError(f"unknown selector {typed!r}: a phase is one of {', '.join('@' + name for name in PHASES)}")
        return {sc.id for sc in scenarios if phase_of(sc) == token[1:]}
    if token.startswith("+"):
        if not sb.TAG.match(token[1:]):
            raise UsageError(f"unknown selector {typed!r}: +<tag> takes a tag (letters, digits, - and _)")
        return {sc.id for sc in scenarios if token[1:] in sc.tags}
    stage, slash, name = token.partition("/")
    if sb.base_stage(stage) is None or (slash and (not name or "/" in name)):
        raise UsageError(f"unknown selector {typed!r}: all, <stage>, <stage>/<scenario>, @<phase>, +<tag> or -<selector> "
                         f"(a stage is one of {_stages()}, or {sb.IMPROVE}<stage>)")
    return {sc.id for sc in scenarios if sc.stage == stage and (not slash or sc.name == name)}


def select(tokens: list[str], scenarios: list[sb.Scenario]) -> list[sb.Scenario]:
    """The scenarios the selectors select, in the order `scenarios` has them: the union of the includes (all when there are
    none) minus the excludes. A selector that selects nothing is a UsageError naming it, ``all`` aside (an empty folder is the
    caller's "nothing selected")."""
    includes = [token for token in tokens if not token.startswith("-")]
    excludes = [token for token in tokens if token.startswith("-")]
    chosen: set[str] = set()
    for token in includes:
        found = _resolve(token, scenarios)
        if not found and token != "all":
            raise UsageError(f"selector {token!r} selects no scenario")
        chosen |= found
    if not includes:
        chosen = {sc.id for sc in scenarios}
    for token in excludes:
        if len(token) == 1:
            raise UsageError("unknown selector '-': write -<selector> to remove what a selector selects")
        found = _resolve(token[1:], scenarios, token)
        if not found and token[1:] != "all":
            raise UsageError(f"selector {token!r} selects no scenario")
        chosen -= found
    return [sc for sc in scenarios if sc.id in chosen]


def _hide_excludes(argv: list[str]) -> list[str]:
    """`argv` with every ``-<selector>`` marked, so argparse reads it as a positional (``-handoff`` would otherwise be ``-h``
    with an argument). The values of the options that take one, ``--x=y`` forms, ``--options`` and ``-h`` stay as they are."""
    hidden, value = [], False
    for token in argv:
        if value:
            hidden.append(token)
            value = False
        elif token in VALUE_OPTIONS:
            hidden.append(token)
            value = True
        elif len(token) > 1 and token[0] == "-" and token[1] != "-" and token != "-h":
            hidden.append(HIDE + token)
        else:
            hidden.append(token)
    return hidden


# ------------------------------------------------------------------------------------------------------------------ rows

def _ids(sc: sb.Scenario) -> tuple[list[str], list[str]]:
    return [row["id"] for row in sc.data.get("planted", [])], [row["id"] for row in sc.data.get("controls", [])]


def _word(ident: str, value: bool | None) -> str:
    """What a verdict says of one id: caught / held when every check proving it passed, missed when one failed, and not
    exercised when no check in the list that ran proves it."""
    if value is None:
        return "not exercised"
    return ("caught" if ident.startswith("P") else "held") if value else "missed"


def _words(sc: sb.Scenario, found: dict) -> dict:
    return {ident: _word(ident, value) for ident, value in {**found["caught"], **found["held"]}.items()}


def _row(sc: sb.Scenario, tier: str) -> dict:
    return {"id": sc.id, "phase": phase_of(sc), "tier": tier, "result": "pass", "reason": None, "ids": {}, "problems": [],
            "notes": []}


def _skipped(sc: sb.Scenario, tier: str, reason: str) -> dict:
    return {**_row(sc, tier), "result": "skipped", "reason": reason}


def _failed_checks(results: list[dict]) -> list[dict]:
    return [{"proves": row["proves"], "kind": row["kind"], "detail": row["detail"]} for row in results if not row["pass"]]


def _clip(text: str, limit: int = DETAIL) -> str:
    text = " ".join(str(text).split())
    return text if len(text) <= limit else text[:limit] + "..."


# ------------------------------------------------------------------------------------------------------------------ verify

def _reference(sc: sb.Scenario, name: str, tmp: Path) -> dict:
    """The oracle's verdict on one reference output: ``ok`` is the bare outcome the scenario's rules ask of that kind of
    reference, ``ids`` what the verdict says of each id, ``failed`` the ids that came out False, ``checks`` the failed checks."""
    bundle, meta = sb.reference_bundle(sc, name, tmp)
    planted, controls = _ids(sc)
    results = stage_oracle.run_checks(sc.data.get("oracle", []), bundle)
    found = stage_oracle.verdict(planted, controls, results)
    status = {**found["caught"], **found["held"]}
    return {"found": found, "ids": _words(sc, found), "failed": [ident for ident, value in status.items() if value is False],
            "declared": list(meta.get("fails", [])), "checks": _failed_checks(results), "meta": meta}


def verify_one(sc: sb.Scenario, tmp: Path) -> dict:
    """T0 for one scenario: the oracle passes ``reference/good`` and fails each ``reference/bad-*`` on the ids it declares."""
    if "verify" not in sc.tiers:
        return _skipped(sc, "verify", "tier off")
    row = _row(sc, "verify")
    references = {}
    try:
        for name in sb.reference_names(sc):
            references[name] = _reference(sc, name, tmp / name.replace("/", "_"))
    except sb.ScenarioError as error:
        row["problems"] += error.problems
    for name, ref in references.items():
        if name == "good":
            row["ids"] = ref["ids"]
            unmet = [f"{ident} {word}" for ident, word in ref["ids"].items() if word not in ("caught", "held")]
            if unmet or ref["found"]["unproved_failures"] or not ref["found"]["pass"]:
                row["problems"].append("reference/good: the oracle does not pass it" + (f" ({', '.join(unmet)})" if unmet else ""))
                row["problems"] += [f"reference/good: {check['kind']} failed" + (f" for {check['proves']}" if check["proves"] else "")
                                    + f": {_clip(check['detail'])}" for check in ref["checks"]]
            continue
        for ident in ref["declared"]:
            if ident not in ref["failed"]:
                row["problems"].append(f"reference/{name}: declared {ident} must fail, but the oracle says {ident} is "
                                       f"{ref['ids'].get(ident, 'unknown')}")
        surprises = [ident for ident in ref["failed"] if ident not in ref["declared"]]
        if surprises:
            row["notes"].append(f"reference/{name} also fails {', '.join(surprises)}, which its meta.json does not declare")
        ref["surprises"] = surprises
    row["references"] = {name: {"declared": ref["declared"], "failed": ref["failed"], "ids": ref["ids"],
                               "surprises": ref.get("surprises", []), "pass": ref["found"]["pass"]}
                         for name, ref in references.items()}
    if "good" not in references and not row["problems"]:
        row["problems"].append("reference/good is missing")
    if row["problems"]:
        row["result"] = "fail"
    return row


def cmd_verify(args: argparse.Namespace, scenarios: list[sb.Scenario]) -> list[dict]:
    rows = []
    with tempfile.TemporaryDirectory(prefix="stage-verify-", ignore_cleanup_errors=True) as temp:
        for number, sc in enumerate(scenarios):
            tmp = Path(temp) / str(number)
            rows.append(verify_one(sc, tmp))
            shutil.rmtree(tmp, ignore_errors=True)
    return rows


# ------------------------------------------------------------------------------------------------------------------ render

def render_one(sc: sb.Scenario, out: Path) -> dict:
    """T1 for one scenario: build it under `out`, render its packet and run its render checks on the bundle. A build that fails
    (the seed refuses a record that breaks the engine's contract, ShipLoop errors) fails the scenario with the reason."""
    if "render" not in sc.tiers:
        return _skipped(sc, "render", "tier off")
    row = _row(sc, "render")
    try:
        bundle = sb.render(sc, out)
    except NotImplementedError as error:
        return _skipped(sc, "render", f"not buildable yet: {error}")
    except (Exception, SystemExit) as error:  # noqa: BLE001 - one scenario's build must not end the run of the others
        message = error.code if isinstance(error, SystemExit) else f"{type(error).__name__}: {error}"
        return {**row, "result": "fail", "problems": [f"the build failed: {_clip(message, 1500)}"]}
    planted, controls = _ids(sc)
    results = stage_oracle.run_checks(sc.data.get("render", []), bundle)
    found = stage_oracle.verdict(planted, controls, results)
    row["ids"] = _words(sc, found)
    row["checks"] = [{"proves": item["proves"], "kind": item["kind"], "pass": item["pass"], "detail": item["detail"]}
                     for item in results]
    row["problems"] += [f"{check['kind']} failed" + (f" for {check['proves']}" if check["proves"] else "")
                        + f": {_clip(check['detail'])}" for check in _failed_checks(results)]
    if not results:
        row["problems"].append("the scenario has no render check")
    row["stage"] = {"issued": bundle.issued, "settled": bundle.settled, "current_stage": bundle.current_stage}
    if row["problems"]:
        row["result"] = "fail"
    return row


def cmd_render(args: argparse.Namespace, scenarios: list[sb.Scenario]) -> list[dict]:
    keep = Path(args.keep).resolve() if args.keep else None
    if keep is not None:
        taken = [sc.id for sc in scenarios if "render" in sc.tiers and (keep / sc.stage / sc.name).exists()]
        if taken:
            raise UsageError(f"--keep {args.keep}: {', '.join(taken)} already has a folder there (build into a new folder)")
    with contextlib.ExitStack() as stack:
        base = keep or Path(stack.enter_context(tempfile.TemporaryDirectory(prefix="stage-render-", ignore_cleanup_errors=True)))
        return [render_one(sc, base / sc.stage / sc.name) for sc in scenarios]


# -------------------------------------------------------------------------------------------------------------------- list

def cmd_list(args: argparse.Namespace, scenarios: list[sb.Scenario]) -> list[dict]:
    return [{"id": sc.id, "stage": sc.stage, "name": sc.name, "phase": phase_of(sc), "tags": list(sc.tags),
             "tiers": list(sc.tiers), "planted": len(sc.data.get("planted", [])), "controls": len(sc.data.get("controls", [])),
             "checks": {"render": len(sc.data.get("render", [])), "oracle": len(sc.data.get("oracle", []))}} for sc in scenarios]


# ----------------------------------------------------------------------------------------------------------------- output

def _table(rows: list[list[str]]) -> str:
    widths = [max(len(row[index]) for row in rows) for index in range(len(rows[0]))]
    return "\n".join("  ".join(cell.ljust(width) for cell, width in zip(row, widths)).rstrip() for row in rows)


def _total(rows: list[dict]) -> dict:
    count = {name: sum(1 for row in rows if row["result"] == name) for name in ("pass", "fail", "skipped")}
    return {"scenarios": len(rows), "passed": count["pass"], "failed": count["fail"], "skipped": count["skipped"]}


def _text_list(rows: list[dict]) -> str:
    table = [["scenario", "phase", "tiers", "tags", "planted", "controls", "render", "oracle"]]
    table += [[row["id"], row["phase"], ",".join(row["tiers"]), ",".join(row["tags"]) or "-", str(row["planted"]),
               str(row["controls"]), str(row["checks"]["render"]), str(row["checks"]["oracle"])] for row in rows]
    return _table(table) + f"\ntotal: {len(rows)} scenario{'s' if len(rows) != 1 else ''}"


def _text_run(command: str, rows: list[dict]) -> str:
    table = [["scenario", "tier", "result", "ids"]]
    for row in rows:
        result = {"pass": "PASS", "fail": "FAIL"}.get(row["result"]) or f"skipped: {row['reason']}"
        table.append([row["id"], row["tier"], result, "  ".join(f"{ident} {word}" for ident, word in row["ids"].items()) or "-"])
    lines = [_table(table)]
    for row in rows:
        if row["problems"] or row["notes"]:
            lines += ["", row["id"]] + [f"  {problem}" for problem in row["problems"]] + [f"  note: {note}" for note in row["notes"]]
    total = _total(rows)
    lines += ["", f"total: {total['scenarios']} scenario{'s' if total['scenarios'] != 1 else ''}, {total['passed']} passed, "
                  f"{total['failed']} failed, {total['skipped']} skipped"]
    return "\n".join(lines)


def _emit(args: argparse.Namespace, rows: list[dict], cases: Path) -> int:
    """Print the rows as the table or, with --json, as one document; the exit code of the command."""
    if args.json:
        document: dict[str, Any] = {"command": args.command, "cases_dir": str(cases), "scenarios": rows}
        if args.command != "list":
            document["total"] = _total(rows)
        else:
            document["total"] = {"scenarios": len(rows)}
        print(json.dumps(document, indent=2, ensure_ascii=False))
    else:
        print(_text_list(rows) if args.command == "list" else _text_run(args.command, rows))
    return EXIT_FAIL if any(row.get("result") == "fail" for row in rows) else EXIT_PASS


# ---------------------------------------------------------------------------------------------------------------- the CLI

def _parser() -> tuple[argparse.ArgumentParser, dict[str, argparse.ArgumentParser]]:
    top = argparse.ArgumentParser(prog="stages.py", description=__doc__.split("\n\n")[0], epilog=NOT_BUILT + ".",
                                  formatter_class=argparse.RawDescriptionHelpFormatter, allow_abbrev=False)
    sub = top.add_subparsers(dest="command", metavar="{" + ",".join(COMMANDS) + "}", required=True)
    parsers = {}
    about = {"list": "one row per scenario: phase, tags, tiers, the planted, control and check counts",
             "verify": "T0, no model, no ShipLoop run: the oracle passes reference/good and fails each reference/bad-*",
             "render": "T1, no model: build each scenario, render its packet and run its render checks"}
    for name in COMMANDS:
        parser = sub.add_parser(name, help=about[name], description=about[name] + ".", epilog=NOT_BUILT + ".", allow_abbrev=False,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
        parser.add_argument("selectors", nargs="*", metavar="SELECTOR",
                            help="all | <stage> | <stage>/<scenario> | @prelude | @inner | @outer | @improve | +<tag>, and "
                                 "-<selector> to exclude (a union of the includes, minus the excludes; none means all)")
        parser.add_argument("--json", action="store_true", help="print one JSON document instead of the table")
        parser.add_argument("--cases-dir", metavar="DIR", default=None,
                            help="the scenario folders (default: test/shiploop_e2e/stage_cases)")
        if name == "render":
            parser.add_argument("--keep", metavar="DIR", default=None,
                                help="leave the built folders under DIR/<stage>/<scenario> (default: a temporary folder removed afterwards)")
        parsers[name] = parser
    return top, parsers


def main(argv: list[str] | None = None) -> int:
    top, parsers = _parser()
    argv = _hide_excludes(list(sys.argv[1:] if argv is None else argv))
    if argv and argv[0] in NOT_BUILT_COMMANDS:
        print(f"stages.py: error: {NOT_BUILT} (asked for {argv[0]!r})", file=sys.stderr)
        return EXIT_USAGE
    try:
        if argv and argv[0] in parsers:
            args = parsers[argv[0]].parse_intermixed_args(argv[1:])
            args.command = argv[0]
        else:
            args = top.parse_args(argv)
    except SystemExit as stop:  # argparse's own: --help (0) or a usage error (2, with its message already on stderr)
        return stop.code if isinstance(stop.code, int) else EXIT_USAGE
    selectors = [token[len(HIDE):] if token.startswith(HIDE) else token for token in args.selectors]
    cases = Path(args.cases_dir) if args.cases_dir else sb.SCENARIOS_DIR
    try:
        found = sb.discover(cases)
        chosen = select(selectors, found)
        if not chosen:
            if args.json:
                _emit(args, [], cases)
            print(f"stages.py: nothing selected ({len(found)} scenario{'s' if len(found) != 1 else ''} under {cases})", file=sys.stderr)
            return EXIT_NOTHING
        rows = {"list": cmd_list, "verify": cmd_verify, "render": cmd_render}[args.command](args, chosen)
    except sb.ScenarioError as error:
        print(f"stages.py: {error}", file=sys.stderr)
        return EXIT_USAGE
    except UsageError as error:
        print(f"stages.py: error: {error}", file=sys.stderr)
        return EXIT_USAGE
    return _emit(args, rows, cases)


if __name__ == "__main__":
    sys.exit(main())
