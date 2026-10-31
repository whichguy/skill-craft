#!/usr/bin/env python3
"""The stage suite's runner (docs/plans/shiploop-stage-suite.md, "Runner and selectors"): list, verify and render over a
selection of scenarios with no model, and live, grade and report for the model tier.

    python3 test/shiploop_e2e/stage_suite/stages.py list   [SELECTOR ...] [--json]
    python3 test/shiploop_e2e/stage_suite/stages.py verify [SELECTOR ...] [--json]
    python3 test/shiploop_e2e/stage_suite/stages.py render [SELECTOR ...] [--keep DIR] [--json]
    python3 test/shiploop_e2e/stage_suite/stages.py verify @inner -validate-existing/all-match +catch
    python3 test/shiploop_e2e/stage_suite/stages.py live   [SELECTOR ...] [--samples N] [--jobs J] [--host H --model M --effort E
                                                           --backend B --host-bin PATH] [--ref REF] [--overlay FILE] [--timeout S]
                                                           [--out DIR] [--dry-run] [--json]
    python3 test/shiploop_e2e/stage_suite/stages.py grade  OUTPUT [--json]
    python3 test/shiploop_e2e/stage_suite/stages.py report ROOT [--compare EARLIER_ROOT] [--json]

It sits below the harness's top level, so it is in neither the evaluator digest nor the qualification snapshot, and it runs from any
working directory. It reads scenarios with stage_build, runs their checks with stage_oracle, runs one live sample with stage_live
and reads results roots with stage_report; it holds none of their logic.

Selectors (a union of the includes, then the excludes removed; no include means all):

    all                  every scenario (the default; an empty scenario folder is "nothing selected", not an error)
    <stage>              every scenario of one stage; ``improve@<stage>`` names an Improve stage and ``spec`` never selects it
    <stage>/<scenario>   one scenario
    @prelude @inner @outer @improve   a phase (an ``improve@`` stage is phase improve)
    +<tag>               every scenario with that tag
    -<selector>          remove what the selector selects

A selector that is not one of these, or that selects nothing, is a usage error naming it. Excludes are written with a leading
dash, which argparse would take for an option, so ``main`` hides them from it first.

The tiers:
- ``verify`` (T0) composes each scenario's seed tree from files, with no ShipLoop run. The oracle must pass ``reference/good``
  (every planted condition caught, every control held, nothing else failing) and must fail, for each ``reference/bad-*``, every id
  its meta.json declares. An id that fails and is not declared is a surprise: reported, not an error.
- ``render`` (T1) builds each scenario's run with stage_build.render and runs its ``render`` checks on the packet. An id no render
  check proves is "not exercised", never a pass. A scenario the builder cannot build yet (an Improve or outer stage) is skipped.
- ``live`` (T2) starts a real model on each selected scenario that has the live tier on: it follows ONLY the one packet, a script
  grades what it did with the oracle verify uses, and every sample is repeated (``--samples``, default the scenario's
  ``live.samples``, 3). It costs money: the plan it prints says so. It selects, prints the plan (scenarios x samples, the driver,
  the results root), refuses before it creates anything when the driver is not ready (the host's binary is not found, it is not
  signed in, Ollama does not answer or lacks the model, or ``--ref`` has no ``accept_effects`` in its navigator), and then runs
  every sample as a subprocess of the hidden ``live-sample`` command, ``--jobs`` at once (separate processes, because the seed
  substitution of stage_build is process-global). A sample that crashes, is killed for exceeding ``--timeout`` plus
  ``SAMPLE_GRACE_SECONDS`` or leaves no whole stage-result.json is recorded as NOT RUN: it counts in the denominator and is never
  a pass, and the others go on; so is a sample an operator ended (the ``stop`` file in its folder, or a signal to it), which
  measured nothing. ``--timeout`` defaults to DEFAULT_TIMEOUT (3600 s) so that no sample runs unbounded. A SIGTERM, SIGHUP or
  Ctrl-C to ``live`` ends every running sample and the host under it (exit 128 + the signal; a SIGKILLed sample's host is ended
  from its ledger), and keeps the samples that finished. ``--dry-run`` builds and launches nothing and prints the plan (it does
  not look at the host).
  The results root is ``--out DIR`` (a new folder) or a new folder under the harness's usual runs location (run.new_output_dir:
  ``$TMPDIR/shiploop-e2e/stages-live-<stamp>-<id>``); it holds ``<stage>/<scenario>/<n>/`` per sample, ``live-plan.json`` and
  ``.logs/``. ``--host``, ``--backend``, ``--model`` and ``--effort`` default as slice.py's do (hosts.RUN_DEFAULT_HOST and its
  backend, the host's model and effort).
- ``grade OUTPUT`` regrades one live sample from its files alone (no host, no ShipLoop) and rewrites its stage-result.json.
- ``report ROOT`` prints the matrix of a results root (stage_report) and ``--json`` the same data; ``--compare EARLIER_ROOT``
  adds the per-cell change, and refuses roots whose drivers (host, backend, model, effort) differ, naming both.
A scenario without the tier is skipped (it counts in the total, not as a failure).

Output is a plain table (per scenario: tier, PASS / FAIL / skipped, and each id caught, held, missed or not exercised) and a
one-line total; ``--json`` prints the same data as one document. Exit codes: 0 everything selected passed, 1 something failed,
2 a usage or schema error or a refusal (the text is printed), 3 nothing selected. For ``live``, 0 means every scenario met its
``live.pass`` rule (the samples that passed, at least the number the rule asks of the samples run; "all" is every one), 1 any
did not, 2 a usage error or a refusal (``Nothing was started.``), 3 nothing selected, or none of what was selected has the live
tier on. ``grade`` exits 0 for a passing sample, 1 for a failing one, 2 for a folder that cannot be graded. ``report`` exits 0
once it printed, 2 for a root it cannot read or compare.

The test-only host (for the hermetic tests; nothing else may use it). ``live`` and ``live-sample`` can run a FAKE host in place of a
model, so a test drives the whole command line with no model and no network. It is off unless BOTH of these are set, in the
environment of the command:

    STAGE_SUITE_FAKE_HOST=PATH         a script that stands in for the model, run as ``python3 PATH SCRIPTS_DIR CONFIG PROMPT RESUME``
                                       (the ShipLoop scripts folder, the config as JSON, the opening prompt, the session id to
                                       resume or "")
    STAGE_SUITE_TEST_ONLY=hermetic-test-no-model   the second, explicit switch

Setting the first without the second is refused (exit 2, ``Nothing was started.``). STAGE_SUITE_FAKE_HOST_CONFIG is the JSON object
the script receives; the string ``{scenario_dir}`` in any of its values is the scenario's folder. Keys of the route itself, not
passed on: ``plugin_dir`` (a plugin folder to use instead of a build of this checkout), ``crash`` (true, or a list of sample
numbers: the host's environment raises, as a sample that crashes) and ``hang_seconds`` with ``hang_samples`` (a list of sample
numbers, default all: it sleeps first, as a sample that does not finish). The plan names the fake host loudly. Credentials: no command here reads, prints or logs any; the host classes of hosts.py own the environments.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import contextlib
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
HARNESS = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HARNESS))
import stage_build as sb  # noqa: E402  (also puts the harness and skills/shiploop/scripts on sys.path)
import stage_live  # noqa: E402
import stage_oracle  # noqa: E402
import stage_report  # noqa: E402
import hosts  # noqa: E402
import overlay as overlays  # noqa: E402
import run  # noqa: E402
import shiploop_stage_spec as stage_spec  # noqa: E402

PHASES = (*stage_spec.PHASES, "improve")
COMMANDS = ("list", "verify", "render", "live", "grade", "report")
HIDDEN_COMMANDS = ("live-sample",)  # the subprocess `live` starts for each sample: not part of the interface
HIDE = "\x1f"  # in front of an exclude (-<selector>) while argparse reads the command line
VALUE_OPTIONS = ("--keep", "--cases-dir", "--samples", "--jobs", "--host", "--model", "--effort", "--backend", "--host-bin", "--ref",
                 "--overlay", "--timeout", "--out", "--compare", "--sample")
EXIT_PASS, EXIT_FAIL, EXIT_USAGE, EXIT_NOTHING = 0, 1, 2, 3
EXIT_CRASH = 4  # live-sample only: the sample raised; the parent counts it as not run
EXIT_STOPPED = 5  # live-sample only: an operator ended the sample; the parent counts it as not run
EXIT_INTERRUPTED = 130  # live: ended by SIGINT (128 + 2); a SIGTERM is 143 and a SIGHUP 129
DEFAULT_TIMEOUT = 3600  # live: seconds a sample's host may run unless --timeout says otherwise (a real model costs money by the minute)
DETAIL = 300  # characters of a check's detail the table keeps
SAMPLE_GRACE_SECONDS = 900  # what a live sample may take beyond --timeout (the build, the seed, the exports) before it is killed
KILL_SECONDS = 15  # between the SIGTERM that ends a sample and the SIGKILL
RUNS_NAME = "stages-live"  # the name run.new_output_dir gives a default results root
PLAN = stage_report.PLAN
LOGS = ".logs"
COST_NOTE = "NOTE: a live run starts a real model for every sample and costs money (tokens, and minutes of host time)."
# The test-only route (see the module docstring): off unless both are set.
FAKE_HOST_ENV, FAKE_CONFIG_ENV, TEST_ONLY_ENV = "STAGE_SUITE_FAKE_HOST", "STAGE_SUITE_FAKE_HOST_CONFIG", "STAGE_SUITE_TEST_ONLY"
TEST_ONLY_VALUE = "hermetic-test-no-model"
ROUTE_KEYS = ("plugin_dir", "crash", "hang_seconds", "hang_samples")


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


def _words(found: dict) -> dict:
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
    return {"found": found, "ids": _words(found), "failed": [ident for ident, value in status.items() if value is False],
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
    row["ids"] = _words(found)
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


def _text_run(rows: list[dict]) -> str:
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
        print(_text_list(rows) if args.command == "list" else _text_run(rows))
    return EXIT_FAIL if any(row.get("result") == "fail" for row in rows) else EXIT_PASS


# ------------------------------------------------------------------------------------------------------------------- the driver

class Refusal(UsageError):
    """A live run that cannot start; the message ends ``Nothing was started.`` (exit 2)."""

    def __init__(self, why: str):
        super().__init__(f"{str(why).rstrip('. ')}. Nothing was started.")


class ScriptHost:
    """The host interface of hosts.Host over a fake host script: the TEST-ONLY route (module docstring). The script is run as
    ``python3 SCRIPT SCRIPTS_DIR CONFIG PROMPT RESUME``. It is never built unless both switches are set, and it starts no model."""

    name, model, effort, skill = "fake", "fake-model", None, "skill-craft:shiploop"
    marketplace = resumable = False
    backend = None

    def __init__(self, script: Path, config: dict):
        self.script = Path(script).resolve()
        self.config = {key: value for key, value in config.items() if key not in ROUTE_KEYS}
        self.route = {key: config[key] for key in ROUTE_KEYS if key in config}

    def _selected(self, key: str, home: Path) -> bool:
        """Whether the route key ``key`` applies to this sample: true for all, or a list of the sample numbers (the folder name)."""
        value = self.route.get(key)
        if isinstance(value, list):
            return Path(home).parent.name in {str(item) for item in value}
        return bool(value)

    def env(self, home: Path) -> dict:
        if self._selected("crash", home):
            raise RuntimeError("the fake host was told to crash (test-only)")
        if self.route.get("hang_seconds") and ("hang_samples" not in self.route or self._selected("hang_samples", home)):
            time.sleep(float(self.route["hang_seconds"]))
        return {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1", "SHIPLOOP_PROGRESS": "off",
                "SHIPLOOP_KEEPALIVE": "off"}

    def invoke(self, skill: str, prompt: str) -> str:
        return f"/{skill} {prompt}"

    def argv(self, *, prompt, prompt_file=None, resume=None, **_ignored) -> list[str]:
        return [sys.executable, str(self.script), str(sb.ROOT / stage_live.SCRIPTS), json.dumps(self.config), prompt, resume or ""]

    def install_plugin(self, env: dict, plugin_dir: Path):
        return None

    def plugin_cli(self, home: Path):
        return None

    def translator(self):
        return lambda raw: [raw]


@dataclass
class Driver:
    """Who answers the packet: ``host`` (a hosts.Host, or the test-only ScriptHost), its name, backend, model and effort as they
    will be recorded, and ``plugin_dir`` (the test-only route's, else None: a build of this checkout or of ``--ref``)."""
    host: Any
    name: str
    backend: str | None
    model: str
    effort: str | None
    plugin_dir: Path | None = None
    fake: str | None = None

    def label(self) -> str:
        return stage_report.driver_label((self.name, self.backend, self.model, self.effort))

    def identity(self) -> dict:
        return {"host": self.name, "backend": self.backend, "model": self.model, "effort": self.effort}


def fake_route() -> Path | None:
    """The fake host script of the test-only route, or None when it is off. Refusal when the script is named without the second
    switch, or does not exist: the route must never start by accident."""
    script = os.environ.get(FAKE_HOST_ENV)
    if not script:
        return None
    if os.environ.get(TEST_ONLY_ENV) != TEST_ONLY_VALUE:
        raise Refusal(f"{FAKE_HOST_ENV} is a test-only route, refused unless {TEST_ONLY_ENV} is also set (see the stages.py "
                      "docstring)")
    if not Path(script).is_file():
        raise Refusal(f"{FAKE_HOST_ENV} names {script}, which is not a file")
    return Path(script)


def _expand(value: Any, sc: sb.Scenario | None) -> Any:
    """`value` with ``{scenario_dir}`` in every string replaced by the scenario's folder."""
    if isinstance(value, str):
        return value.replace("{scenario_dir}", str(sc.dir)) if sc is not None else value
    if isinstance(value, list):
        return [_expand(item, sc) for item in value]
    if isinstance(value, dict):
        return {key: _expand(item, sc) for key, item in value.items()}
    return value


def resolve_driver(args: argparse.Namespace, sc: sb.Scenario | None = None) -> Driver:
    """The driver the options name, with slice.py's defaults: hosts.RUN_DEFAULT_HOST, that host's E2E backend, model and effort.
    Constructing it starts nothing. UsageError for an option that does not fit the host; Refusal for the test-only route misused."""
    script = fake_route()
    if script is not None:
        try:
            config = _expand(json.loads(os.environ.get(FAKE_CONFIG_ENV) or "{}"), sc)
        except ValueError as error:
            raise Refusal(f"{FAKE_CONFIG_ENV} is not JSON ({error})") from error
        if not isinstance(config, dict):
            raise Refusal(f"{FAKE_CONFIG_ENV} must be a JSON object")
        host = ScriptHost(script, config)
        plugin = host.route.get("plugin_dir")
        return Driver(host, host.name, None, args.model or host.model, args.effort or host.effort,
                      Path(plugin) if plugin else None, str(script))
    name = args.host or hosts.RUN_DEFAULT_HOST
    if args.backend and "backends" not in vars(hosts.HOSTS[name]):
        raise UsageError(f"--backend {args.backend} is a Claude host option; the {name} host has one backend")
    backend = args.backend or hosts.RUN_DEFAULT_BACKEND.get(name)
    host = hosts.host(name, args.host_bin, backend)
    return Driver(host, name, getattr(host, "backend", None), args.model or host.model, args.effort or host.effort)


def driver_gap(driver: Driver) -> str:
    """Why the driver cannot start a sample, or "": the host's binary is not on PATH, the host is not signed in (its own
    ``env`` says so; the environment it makes is dropped unread), or Ollama is not ready (stage_live.host_gap). Nothing is started,
    and no credential is read or shown."""
    if driver.fake:
        return ""
    binary = getattr(driver.host, "binary", None)
    if binary and shutil.which(binary) is None:
        return (f"the {driver.name} host's binary {str(binary)!r} was not found (put it on PATH, or name it with --host-bin)")
    with tempfile.TemporaryDirectory(prefix="stage-ready-") as scratch:
        try:
            driver.host.env(Path(scratch))
        except SystemExit as stop:
            return str(stop.code)
        except OSError as error:
            return f"the {driver.name} host's environment cannot be made ({type(error).__name__})"
    return stage_live.host_gap(driver.host, driver.model)


# --------------------------------------------------------------------------------------------------------------------- live

def _sample_plan(sc: sb.Scenario, args: argparse.Namespace) -> dict:
    """Samples and the pass rule of one scenario: ``--samples`` else ``live.samples`` (3); ``live.pass`` is ``all`` or a number of
    samples that must pass (never more than the samples run)."""
    live = sc.data.get("live") or {}
    samples = args.samples or live.get("samples", 3)
    rule = live.get("pass", "all")
    return {"samples": samples, "required": samples if rule == "all" else min(rule, samples), "rule": rule}


def _say(args: argparse.Namespace, text: str = "") -> None:
    """Human text: stdout, or stderr with --json (stdout then holds the one document)."""
    print(text, file=sys.stderr if args.json else sys.stdout, flush=True)


def _plan_text(plan: dict, args: argparse.Namespace) -> str:
    total = sum(item["samples"] for item in plan["scenarios"].values())
    lines = [f"live plan: {len(plan['scenarios'])} scenario{'s' if len(plan['scenarios']) != 1 else ''} x samples = {total} "
             f"sample{'s' if total != 1 else ''}, {plan['jobs']} at once"]
    for sid, item in plan["scenarios"].items():
        lines.append(f"  {sid}: {item['samples']} sample{'s' if item['samples'] != 1 else ''}, passes when {item['required']} pass"
                     + (f" (live.pass {item['rule']!r})" if item["required"] != item["samples"] else ""))
    driver = plan["driver"]
    lines.append("  driver: " + stage_report.driver_label((driver["host"], driver["backend"], driver["model"], driver["effort"])))
    if plan.get("fake_host"):
        lines.append(f"  !! TEST-ONLY FAKE HOST {plan['fake_host']} stands in for the model: no model is started")
    for key, label in (("ref", "ref"), ("overlay", "overlay")):
        if plan.get(key):
            lines.append(f"  {label}: {plan[key]}")
    lines.append("  timeout: " + (f"{plan['timeout']:g} s per sample" if plan["timeout"] else "none"))
    lines.append("  results root: " + plan["root"])
    if plan["off"]:
        lines.append("  not live (tier off): " + ", ".join(plan["off"]))
    for sid, why in plan["waiting"].items():
        lines.append(f"  skipped, not buildable yet: {sid} ({why})")
    lines.append(COST_NOTE)
    return "\n".join(lines)


def _positive(args: argparse.Namespace) -> None:
    for name, value in (("--samples", args.samples), ("--jobs", args.jobs), ("--timeout", args.timeout)):
        if value is not None and value <= 0:
            raise UsageError(f"{name} must be a positive number (got {value})")


def _check_ref_and_overlay(args: argparse.Namespace) -> Path | None:
    """Refuse a --ref whose navigator lacks accept_effects (or that git does not know) and an overlay that does not load, with
    nothing built; the resolved overlay path."""
    if args.ref:
        try:
            why = stage_live.ref_seam_gap(args.ref)
        except SystemExit as stop:
            raise Refusal(str(stop.code)) from stop
        if why:
            raise Refusal(why)
    if not args.overlay:
        return None
    path = Path(args.overlay).expanduser().resolve()
    try:
        overlays.load(path)
    except (OSError, ValueError, SystemExit, overlays.OverlayError) as error:
        raise Refusal(f"--overlay {args.overlay}: {error if not isinstance(error, SystemExit) else error.code}") from error
    return path


CHILDREN: dict = {}  # the live-sample processes that are running -> their sample folders
CHILDREN_LOCK = threading.Lock()
PRINT_LOCK = threading.Lock()
STOPPING = threading.Event()  # a signal told `live` to end: no sample starts after it


def _end_groups(processes: list[subprocess.Popen]) -> None:
    """End live-samples and the hosts below them, all at once: SIGTERM to each group (run.py's handler, in the sample, ends the
    host's own group), then SIGKILL to what is left after KILL_SECONDS."""
    for number, wait in ((signal.SIGTERM, KILL_SECONDS), (signal.SIGKILL, 5)):
        for process in processes:
            if process.poll() is None:
                with contextlib.suppress(ProcessLookupError, PermissionError):
                    os.killpg(process.pid, number)
        end = time.monotonic() + wait
        while time.monotonic() < end and any(process.poll() is None for process in processes):
            time.sleep(0.05)


def _end_group(process: subprocess.Popen) -> None:
    _end_groups([process])


def _sweep(out: Path) -> None:
    """The host of a sample that was killed from outside (its handler could not run) is in a session of its own and outlives it:
    end the host groups the sample's own ledger records and that are still the processes recorded."""
    stage_live.end_recorded_hosts(out)


def _tail(path: Path) -> str:
    try:
        lines = [line.strip() for line in path.read_text(errors="replace").splitlines() if line.strip()]
    except OSError:
        return ""
    return " ".join(lines[-1].split())[-300:] if lines else ""


def _sample_argv(sc: sb.Scenario, number: int, out: Path, args: argparse.Namespace, cases: Path, overlay: Path | None) -> list[str]:
    argv = [sys.executable, "-B", str(Path(__file__).resolve()), "live-sample", sc.id, str(out), "--sample", str(number),
            "--cases-dir", str(cases)]
    for name in ("host", "backend", "model", "effort", "host_bin", "ref"):
        if getattr(args, name):
            argv += [f"--{name.replace('_', '-')}", str(getattr(args, name))]
    if overlay:
        argv += ["--overlay", str(overlay)]
    if args.timeout:
        argv += ["--timeout", str(args.timeout)]
    return argv


def run_one_sample(sc: sb.Scenario, number: int, root: Path, args: argparse.Namespace, cases: Path, overlay: Path | None) -> dict:
    """One sample as a subprocess of ``live-sample`` (stdin closed, its own process group, a hard limit of ``--timeout`` plus
    SAMPLE_GRACE_SECONDS when there is a timeout). Whatever it did, the record says whether the sample was graded; one that
    was not (a crash, a kill, a refusal, a half-written result) gets an error.txt saying why, and the others are not touched."""
    out = root / sc.stage / sc.name / str(number)
    log = root / LOGS / f"{sc.stage}__{sc.name}__{number}.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    hard = (args.timeout + SAMPLE_GRACE_SECONDS) if args.timeout else None
    started = time.monotonic()
    code: int | None = None
    why = ""
    try:
        with log.open("wb") as handle:
            if STOPPING.is_set():
                raise OSError("`live` was told to end")
            process = subprocess.Popen(_sample_argv(sc, number, out, args, cases, overlay), stdin=subprocess.DEVNULL, stdout=handle,
                                       stderr=subprocess.STDOUT, start_new_session=True)
            with CHILDREN_LOCK:
                CHILDREN[process] = out
            if STOPPING.is_set():  # told to end between the check and the start: this one is not in the list the handler took
                _end_group(process)
            try:
                code = process.wait(timeout=hard)
            except subprocess.TimeoutExpired:
                _end_group(process)
                why = f"killed: the sample did not finish within {hard:g} s ({args.timeout:g} s timeout plus {SAMPLE_GRACE_SECONDS} s)"
            finally:
                with CHILDREN_LOCK:
                    CHILDREN.pop(process, None)
            if code is None or code < 0 or STOPPING.is_set():
                _sweep(out)
    except OSError as error:
        why = f"the sample could not be started ({type(error).__name__}: {error})"
    read = stage_report.read_sample(out) if out.is_dir() else {"graded": False, "reason": "no sample folder"}
    record = {"scenario": sc.id, "sample": number, "output": str(out), "log": str(log), "returncode": code,
              "seconds": round(time.monotonic() - started, 1), "graded": read["graded"]}
    if read["graded"]:
        result = read["result"]
        return {**record, "pass": stage_report.passed(result), "value": result.get("value"), "reason": None}
    if not why:
        why = (f"live-sample exited {code}: {_tail(log)}" if code is not None else "") or read["reason"]
    if not (out / stage_report.ERROR).is_file():
        with contextlib.suppress(OSError):
            out.mkdir(parents=True, exist_ok=True)
            (out / stage_report.ERROR).write_text(" ".join(why.split())[:2000] + "\n")
    return {**record, "pass": False, "value": None, "reason": why}


def _text_sample(record: dict) -> str:
    if not record["graded"]:
        return f"  NOT RUN  {record['scenario']} #{record['sample']}: {record['reason']}  (log {record['log']})"
    return (f"  {'PASS' if record['pass'] else 'FAIL'}  {record['scenario']} #{record['sample']}  value "
            f"{record['value'] if record['value'] is None else format(record['value'], '.2f')}  {record['output']}")


def _not_buildable(sc: sb.Scenario) -> str:
    """Why the builder cannot build ``sc`` yet (an Improve or outer stage), or ""; render skips these the same way."""
    try:
        sb._buildable(sc)
    except NotImplementedError as error:
        return str(error)
    except sb.ScenarioError as error:
        return "; ".join(error.problems)
    return ""


def _end_on_signals(told: list[int]):
    """Make a SIGTERM or SIGHUP to `live` end it as a Ctrl-C does (the KeyboardInterrupt that cmd_live answers by ending every
    sample and the host below it), recording the signal in ``told``. A signal the launch ignored (nohup keeps a run alive through
    a hangup) stays ignored. Returns the function that puts the old handlers back; it installs nothing off the main thread."""
    if threading.current_thread() is not threading.main_thread():
        return lambda: None
    old = {}

    def handler(number, frame):
        told.append(number)
        signal.signal(number, signal.SIG_DFL)  # a second one means it
        raise KeyboardInterrupt

    for number in (signal.SIGTERM, signal.SIGHUP):
        if signal.getsignal(number) is not signal.SIG_IGN:
            old[number] = signal.signal(number, handler)

    def restore() -> None:
        for number, before in old.items():
            signal.signal(number, before)

    return restore


def cmd_live(args: argparse.Namespace, chosen: list[sb.Scenario], cases: Path) -> int:
    on = [sc for sc in chosen if "live" in sc.tiers]
    off = [sc.id for sc in chosen if "live" not in sc.tiers]
    waiting = {sc.id: why for sc in on if (why := _not_buildable(sc))}
    live = [sc for sc in on if sc.id not in waiting]
    if not live:
        print(f"stages.py: nothing selected: none of the {len(chosen)} scenario{'s' if len(chosen) != 1 else ''} selected can run "
              "live (a scenario opts in with \"live\" in its tiers" + (f"; off in {', '.join(off)}" if off else "")
              + ("; not buildable yet: " + ", ".join(f"{sid} ({why})" for sid, why in waiting.items()) if waiting else "") + ")",
              file=sys.stderr)
        return EXIT_NOTHING
    _positive(args)
    driver = resolve_driver(args)
    overlay = _check_ref_and_overlay(args)
    samples = {sc.id: _sample_plan(sc, args) for sc in live}
    stamp_root = Path(args.out).expanduser() if args.out else Path(tempfile.gettempdir()) / "shiploop-e2e" / f"{RUNS_NAME}-<time>-<id>"
    plan = {"command": "live", "driver": driver.identity(), "fake_host": driver.fake, "ref": args.ref,
            "overlay": str(overlay) if overlay else None, "timeout": args.timeout, "jobs": args.jobs,
            "scenarios": samples, "off": off, "waiting": waiting, "root": str(stamp_root)}
    _say(args, _plan_text(plan, args))
    if args.dry_run:
        if args.json:
            print(json.dumps({**plan, "dry_run": True}, indent=2, ensure_ascii=False))
        else:
            print("dry run: nothing was built and nothing was launched (the host is checked when the run starts)")
        return EXIT_PASS
    if args.out and Path(args.out).expanduser().exists():
        raise Refusal(f"--out {args.out} already exists: a results root is a new folder")
    if why := driver_gap(driver):
        raise Refusal(why)
    try:
        root = run.new_output_dir(Path(args.out) if args.out else None, RUNS_NAME)
    except SystemExit as stop:
        raise Refusal(str(stop.code)) from stop
    plan["root"] = str(root)
    (root / PLAN).write_text(json.dumps({"created": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "cases_dir": str(cases),
                                         "driver": plan["driver"], "ref": plan["ref"], "overlay": plan["overlay"],
                                         "timeout": args.timeout, "jobs": args.jobs, "fake_host": bool(driver.fake),
                                         "scenarios": {sc.id: {"samples": samples[sc.id]["samples"], "required": samples[sc.id]["required"],
                                                               "planted": [row["id"] for row in sc.data.get("planted", [])],
                                                               "controls": [row["id"] for row in sc.data.get("controls", [])]}
                                                       for sc in live}}, indent=2) + "\n")
    if not args.out:
        _say(args, f"results root: {root}")
    tasks = [(sc, number) for sc in live for number in range(1, samples[sc.id]["samples"] + 1)]
    records: list[dict] = []

    def work(task: tuple) -> dict:
        record = run_one_sample(task[0], task[1], root, args, cases, overlay)
        with PRINT_LOCK:
            _say(args, _text_sample(record))
        return record

    pool = concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs)
    STOPPING.clear()
    told: list[int] = []  # the number of the signal that told `live` to end
    restore = _end_on_signals(told)
    try:
        futures = [pool.submit(work, task) for task in tasks]
        for future in futures:
            records.append(future.result())
    except KeyboardInterrupt:
        STOPPING.set()
        pool.shutdown(wait=False, cancel_futures=True)
        with CHILDREN_LOCK:
            running = dict(CHILDREN)
        _end_groups(list(running))
        for out in running.values():
            _sweep(out)
        print("stages.py: " + (f"ended by {signal.Signals(told[0]).name}" if told else "interrupted")
              + "; the host sessions were ended and the samples that finished are kept", file=sys.stderr)
        return 128 + (told[0] if told else signal.SIGINT)
    finally:
        pool.shutdown(wait=True)
        restore()
    report = stage_report.read_root(root)
    unmet = [row["id"] for row in report["scenarios"] if row["rule"] is not None and not row["rule"]["met"]]
    if args.json:
        print(json.dumps({**plan, "samples": records, "report": report, "unmet": unmet, "pass": not unmet}, indent=2,
                         ensure_ascii=False))
    else:
        print("\n" + stage_report.render(report))
        print("\n" + (f"live: every scenario met its pass rule" if not unmet else
                      f"live: {len(unmet)} scenario{'s' if len(unmet) != 1 else ''} did not meet the pass rule: {', '.join(unmet)}"))
    return EXIT_FAIL if unmet else EXIT_PASS


def cmd_live_sample(args: argparse.Namespace, cases: Path) -> int:
    """The hidden subcommand: one sample in the new folder OUT. 0 it passed, 1 it was graded and did not pass, 2 it was refused
    (nothing written), 4 it raised (error.txt says what, when the folder was made). ``live`` reads the files, not these codes."""
    sc = sb.load(args.scenario, cases)
    run.install_termination_handlers()
    driver = resolve_driver(args, sc)
    overlay = Path(args.overlay).resolve() if args.overlay else None
    try:
        result = stage_live.run_sample(sc, Path(args.out), host=driver.host, model=args.model, effort=args.effort,
                                       plugin_dir=driver.plugin_dir, ref=args.ref, overlay=overlay, timeout=args.timeout,
                                       sample=args.sample, quiet=True)
    except SystemExit as stop:
        print(stop.code if not isinstance(stop.code, int) else f"refused ({stop.code})", file=sys.stderr)
        return EXIT_USAGE
    except stage_live.SampleStopped as stop:
        print(f"stopped: {stop}", file=sys.stderr)
        return EXIT_STOPPED
    except Exception:  # noqa: BLE001 - the parent records it as not run; the traceback is in the sample's log
        traceback.print_exc()
        return EXIT_CRASH
    print(json.dumps({"scenario": sc.id, "sample": args.sample, "pass": result["pass"], "value": result["value"]}))
    return EXIT_PASS if result["pass"] else EXIT_FAIL


# ---------------------------------------------------------------------------------------------------------- grade and report

def _read_invocation(out: Path) -> dict:
    try:
        document = json.loads((out / stage_live.INVOCATION).read_text())
    except (OSError, ValueError) as error:
        raise UsageError(f"{out} is not a live sample: {stage_live.INVOCATION} cannot be read ({type(error).__name__})") from error
    if not isinstance(document, dict) or not isinstance(document.get("scenario"), str):
        raise UsageError(f"{out / stage_live.INVOCATION} names no scenario")
    return document


def cmd_grade(args: argparse.Namespace, cases: Path) -> int:
    out = Path(args.output).expanduser().resolve()
    if not out.is_dir():
        raise UsageError(f"{args.output} is not a folder: grade takes a sample folder of a live run")
    invocation = _read_invocation(out)
    sc = sb.load(invocation["scenario"], cases)
    try:
        document = stage_live.grade_sample(sc, out)
    except stage_live.SampleError as error:
        raise UsageError(str(error)) from error
    if args.json:
        print(json.dumps(document, indent=2, ensure_ascii=False))
    else:
        verdicts = ", ".join(f"{name} {'ok' if value else 'FAIL'}" for name, value in document["verdicts"].items())
        ids = "  ".join(f"{ident} {'caught' if ident in document['caught'] else 'held'}" if value else f"{ident} MISSED"
                        for ident, value in {**document["caught"], **document["held"]}.items())
        lines = [f"{document['scenario']} #{document.get('sample')}  "
                 + stage_report.driver_label((document.get("host"), document.get("backend"), document.get("model"),
                                              document.get("effort"))),
                 f"  {'PASS' if document['pass'] else 'FAIL'}: {verdicts}", f"  ids: {ids or '-'}", f"  value {document['value']:.2f}"]
        lines += [f"  failed check: {check['kind']}" + (f" for {check['proves']}" if check["proves"] else "")
                  + f": {_clip(check['detail'])}" for check in document["checks"] if not check["pass"]]
        lines.append(f"  written: {out / stage_live.RESULT}")
        print("\n".join(lines))
    return EXIT_PASS if document["pass"] else EXIT_FAIL


def cmd_report(args: argparse.Namespace) -> int:
    try:
        report = stage_report.read_root(Path(args.root))
        comparison = stage_report.compare(Path(args.root), Path(args.compare)) if args.compare else None
    except stage_report.ReportError as error:
        raise UsageError(str(error)) from error
    if args.json:
        print(json.dumps({"report": report, **({"compare": comparison} if comparison else {})}, indent=2, ensure_ascii=False))
    else:
        print(stage_report.render(report))
        if comparison:
            print("\n" + stage_report.render_compare(comparison))
    return EXIT_PASS


# ---------------------------------------------------------------------------------------------------------------- the CLI

def _driver_options(parser: argparse.ArgumentParser, timeout: float | None = None) -> None:
    parser.add_argument("--host", choices=sorted(hosts.HOSTS), default=None,
                        help=f"the host that follows the packet (default: {hosts.RUN_DEFAULT_HOST})")
    parser.add_argument("--backend", choices=("anthropic", "ollama"), default=None,
                        help="claude only: ollama (the E2E default) or anthropic")
    parser.add_argument("--model", default=None, help="default: the host's model, as slice.py")
    parser.add_argument("--effort", default=None, help="reasoning effort; default: the host's, as slice.py")
    parser.add_argument("--host-bin", metavar="PATH", default=None, help="the host's binary (default: its name, on PATH)")
    parser.add_argument("--ref", default=None, help="build the plugin from this git ref (its navigator needs accept_effects)")
    parser.add_argument("--overlay", metavar="FILE", default=None, help="a prompt overlay (overlay.py) applied to the plugin build")
    parser.add_argument("--timeout", type=float, default=timeout,
                        help="seconds before a sample's host is killed; default: " + (f"{timeout:g}" if timeout else "none"))


def _parser() -> tuple[argparse.ArgumentParser, dict[str, argparse.ArgumentParser]]:
    top = argparse.ArgumentParser(prog="stages.py", description=__doc__.split("\n\n")[0],
                                  formatter_class=argparse.RawDescriptionHelpFormatter, allow_abbrev=False)
    sub = top.add_subparsers(dest="command", metavar="{" + ",".join(COMMANDS) + "}", required=True)
    parsers = {}
    about = {"list": "one row per scenario: phase, tags, tiers, the planted, control and check counts",
             "verify": "T0, no model, no ShipLoop run: the oracle passes reference/good and fails each reference/bad-*",
             "render": "T1, no model: build each scenario, render its packet and run its render checks",
             "live": "T2, a real model (costs money): follow only the packet of each scenario with the live tier on, graded by "
                     "the oracle, --samples times",
             "grade": "regrade one live sample from its files alone (no host, no ShipLoop)",
             "report": "the matrix of catch rates of a live results root; --compare shows the change from an earlier root"}
    for name in COMMANDS:
        parser = sub.add_parser(name, help=about[name], description=about[name] + ".", allow_abbrev=False,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
        if name in ("list", "verify", "render", "live"):
            parser.add_argument("selectors", nargs="*", metavar="SELECTOR",
                                help="all | <stage> | <stage>/<scenario> | @prelude | @inner | @outer | @improve | +<tag>, and "
                                     "-<selector> to exclude (a union of the includes, minus the excludes; none means all)")
        if name == "grade":
            parser.add_argument("output", metavar="OUTPUT", help="a sample folder of a live run (<root>/<stage>/<scenario>/<n>)")
        if name == "report":
            parser.add_argument("root", metavar="ROOT", help="a results root (the --out folder of a live run)")
            parser.add_argument("--compare", metavar="EARLIER_ROOT", default=None,
                                help="also show the change from this earlier root (refused when its driver differs)")
        parser.add_argument("--json", action="store_true", help="print one JSON document instead of the table")
        if name != "report":
            parser.add_argument("--cases-dir", metavar="DIR", default=None,
                                help="the scenario folders (default: test/shiploop_e2e/stage_cases)")
        if name == "render":
            parser.add_argument("--keep", metavar="DIR", default=None,
                                help="leave the built folders under DIR/<stage>/<scenario> (default: a temporary folder removed afterwards)")
        if name == "live":
            _driver_options(parser, DEFAULT_TIMEOUT)
            parser.add_argument("--samples", type=int, default=None, metavar="N",
                                help="samples per scenario (default: the scenario's live.samples, 3)")
            parser.add_argument("--jobs", type=int, default=1, metavar="J", help="samples run at once, each its own process (default 1)")
            parser.add_argument("--out", metavar="DIR", default=None,
                                help="the results root, a new folder (default: a new folder under the harness's usual runs location)")
            parser.add_argument("--dry-run", action="store_true", help="print the plan; build nothing, launch nothing")
        parsers[name] = parser
    # Not added to the subcommands, so no help lists it: main dispatches to it by name.
    hidden = argparse.ArgumentParser(prog="stages.py live-sample", allow_abbrev=False,
                                     description="one live sample in the new folder OUT (started by `live`; not an interface)")
    hidden.add_argument("scenario")
    hidden.add_argument("out")
    hidden.add_argument("--sample", type=int, default=1)
    hidden.add_argument("--cases-dir", metavar="DIR", default=None)
    _driver_options(hidden)
    parsers["live-sample"] = hidden
    return top, parsers


def main(argv: list[str] | None = None) -> int:
    top, parsers = _parser()
    argv = _hide_excludes(list(sys.argv[1:] if argv is None else argv))
    try:
        if argv and argv[0] in parsers:
            args = parsers[argv[0]].parse_intermixed_args(argv[1:])
            args.command = argv[0]
        else:
            args = top.parse_args(argv)
    except SystemExit as stop:  # argparse's own: --help (0) or a usage error (2, with its message already on stderr)
        return stop.code if isinstance(stop.code, int) else EXIT_USAGE
    selectors = [token[len(HIDE):] if token.startswith(HIDE) else token for token in getattr(args, "selectors", [])]
    cases = Path(args.cases_dir).resolve() if getattr(args, "cases_dir", None) else sb.SCENARIOS_DIR
    try:
        if args.command == "live-sample":
            return cmd_live_sample(args, cases)
        if args.command == "grade":
            return cmd_grade(args, cases)
        if args.command == "report":
            return cmd_report(args)
        found = sb.discover(cases)
        chosen = select(selectors, found)
        if not chosen:
            if args.json:
                _emit(args, [], cases)
            print(f"stages.py: nothing selected ({len(found)} scenario{'s' if len(found) != 1 else ''} under {cases})", file=sys.stderr)
            return EXIT_NOTHING
        if args.command == "live":
            return cmd_live(args, chosen, cases)
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
