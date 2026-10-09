"""What the run delivered, measured after the run and recorded, never judged (SPEC: How the harness checks the clauses, `quality`).

Three measures, each optional, each `{observed: false, reason}` when it could not be taken (never 0, never a pass):

* ``mutation``: small text mutations of the delivered source, run against the delivered tests on a copy. The ratio is the share
  of mutants the tests catch. It belongs to one operator catalog (``operator_id``) and is compared only within that id.
* ``acceptance``: held-out checks, written by hand from the case's prompt and never shown to the model, run against the
  delivered product's server. They run inside the harness process, so no check text or id reaches an argv.
* ``memory_writes`` and ``held_out_seen``: facts read from the run's own event stream.

The delivered ``work/`` is only read. Everything this module starts runs in a process group of its own, registered with the
harness's live groups so a signal ends it, and everything it writes lives under ``<output>/quality``. Tool knowledge (the
mutation operators, how a runner reports its test count, which files a run loaded) sits in one catalog keyed by file extension;
product knowledge sits in ``cases.json`` and ``checks/``.
"""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import signal
import socket
import subprocess
import time
from typing import Callable
import urllib.parse

import listeners
import metrics
import shiploop_test_counts as test_counts

HERE = Path(__file__).resolve().parent
# Ceilings, not tuning values (as listeners.LSOF_TIMEOUT is): the point past which a thing is taken to have hung.
# One test run, the unmutated baseline and each mutant alike: the eight saved deliveries' own suites took 0.23 to 1.27 s, and the
# prototype sweeps over them (33 to 108 mutants, 25 to 152 s each) ran with this limit. A run that reaches it is a killed mutant
# (a hang is a visible change) counted as a timeout, or, for the baseline, an unobserved ratio.
RUN_CEILING_SECONDS = 10
# The whole mutation phase. Its largest measured sweep was 152 s; a task launcher's limit is near 30 minutes. Mutants not reached
# are `not_run` and `ceiling_hit` says so.
PHASE_CEILING_SECONDS = 600
# How long a product's server has to start listening.
LISTEN_CEILING_SECONDS = 10
# One HTTP call of a held-out check.
CALL_CEILING_SECONDS = 5
POLL_SECONDS = 0.05
# The operator catalog a ratio belongs to. Any change to the operators or to the masking is a new id: ratios of two ids
# are never compared.
OPERATOR_ID = "js-1"
TAIL_BYTES = 200_000  # how much of a test run's output is read back: the summary is at the end


# --------------------------------------------------------------------------------------------------------------------
# The extension catalog (JavaScript). Tool knowledge lives here and nowhere else in the harness.

# (operator, regular expression over the masked source, replacement; None replaces a number by its successor)
JS_OPERATORS = (
    ("eq-flip", r"===", "!=="), ("eq-flip", r"!==", "==="),
    ("rel-bound", r"(?<![<>=!-])<=(?!=)", "<"), ("rel-bound", r"(?<![<>=!-])>=(?!=)", ">"),
    ("rel-bound", r"(?<![<>=-])<(?![<=])", "<="), ("rel-bound", r"(?<![<>=-])>(?![>=])", ">="),
    ("logic-flip", r"&&", "||"), ("logic-flip", r"\|\|", "&&"),
    ("bool-flip", r"\btrue\b", "false"), ("bool-flip", r"\bfalse\b", "true"),
    ("arith-flip", r"(?<=\s)\+(?=\s)", "-"), ("arith-flip", r"(?<=\s)-(?=\s)", "+"),
    ("bound-literal", r"(?<=[<>]\s)(\d+)(?![\w.$])", None), ("bound-literal", r"(?<=[<>]=\s)(\d+)(?![\w.$])", None),
)
# Folders whose files are tests, dependencies or a ShipLoop record, not delivered source; a case adds its own (`exclude`).
JS_NOT_SOURCE_FOLDERS = ("test", "tests", "__tests__", "node_modules", "docs")
JS_TEST_FILE = re.compile(r"(?:\.(?:test|spec)|[-_]test)\.[cm]?js$|(?:^|/)test(?:-[^/]*)?\.[cm]?js$")  # node --test's own patterns


def mask(source: str) -> str:
    """The source with every comment and every string or template literal body replaced by spaces (newlines and length kept),
    so an operator is looked for in code only. A regular expression literal is not recognised: a `//` inside one masks the
    rest of its line (a known limit of this catalog)."""
    out, i, n = list(source), 0, len(source)
    while i < n:
        c = source[i]
        if source.startswith("//", i):
            j = source.find("\n", i)
            j = n if j < 0 else j
            for k in range(i, j):
                out[k] = " "
            i = j
        elif source.startswith("/*", i):
            j = source.find("*/", i + 2)
            j = n if j < 0 else j + 2
            for k in range(i, j):
                out[k] = " " if source[k] != "\n" else "\n"
            i = j
        elif c in "'\"`":
            j = i + 1
            while j < n and source[j] != c:
                j += 2 if source[j] == "\\" else 1
            for k in range(i + 1, min(j, n)):
                out[k] = " " if source[k] != "\n" else "\n"
            i = j + 1
        else:
            i += 1
    return "".join(out)


def sites(source: str) -> list[dict]:
    """Every place an operator applies: ``{op, start, end, old, new, line}``, in source order."""
    masked = mask(source)
    found = []
    for name, pattern, replacement in JS_OPERATORS:
        for match in re.finditer(pattern, masked):
            new = replacement if replacement is not None else str(int(match.group(1)) + 1)
            found.append({"op": name, "start": match.start(), "end": match.end(), "old": source[match.start():match.end()],
                          "new": new, "line": source.count("\n", 0, match.start()) + 1})
    return sorted(found, key=lambda site: (site["start"], site["op"], site["new"]))


def js_test_count(output: str, returncode: int | None) -> int | None:
    """How many tests a run counted, by the engine's one reader of test-runner summaries; None when the output has none."""
    counted = test_counts.count(output, returncode)
    return None if counted is None else int(counted["ran"])


def js_coverage_files(coverage: Path, copy: Path) -> set[str] | None:
    """The files (relative to the copy) a run loaded, from the V8 coverage Node writes for every process that exits by itself when
    NODE_V8_COVERAGE is set (a test's child server included, unless the test stops it with a signal: it then writes none).
    None where no process wrote any."""
    real = os.path.realpath(copy)
    loaded: set[str] = set()
    wrote = False
    for path in sorted(coverage.glob("*.json")) if coverage.is_dir() else []:
        try:
            scripts = json.loads(path.read_text()).get("result") or []
        except (OSError, ValueError):
            continue
        wrote = True
        for script in scripts:
            url = script.get("url") if isinstance(script, dict) else None
            if isinstance(url, str) and url.startswith("file://"):
                place = urllib.parse.unquote(urllib.parse.urlparse(url).path)
                if place.startswith(real + os.sep):
                    loaded.add(place[len(real) + 1:])
    return loaded if wrote else None


class Catalog:
    """What the harness knows about one language: its operators, its test files, how to check a syntax, how a runner counts."""

    def __init__(self, ident: str, extensions: tuple, operators, not_source: tuple, test_file, syntax_check, count, coverage_env,
                 coverage_files):
        self.ident, self.extensions, self.operators = ident, extensions, operators
        self.not_source, self.test_file = not_source, test_file
        self.syntax_check, self.count, self.coverage_env, self.coverage_files = syntax_check, count, coverage_env, coverage_files


JS = Catalog(OPERATOR_ID, (".js", ".mjs", ".cjs"), JS_OPERATORS, JS_NOT_SOURCE_FOLDERS, JS_TEST_FILE.search,
             lambda path: ["node", "--check", str(path)], js_test_count,
             lambda directory: {"NODE_V8_COVERAGE": str(directory)}, js_coverage_files)
CATALOGS = {extension: JS for extension in JS.extensions}


# --------------------------------------------------------------------------------------------------------------------
# Processes: every child in a group of its own, registered while its leader is unreaped, signalled only while it leads it.

def end_group(proc: subprocess.Popen) -> bool:
    """SIGKILL the process group `proc` leads, then reap it. False (nothing signalled) unless `proc` is alive and its own
    group's leader: a pid that has been reaped may be reused, and its group is then someone else's (the guard the harness's
    other kills use, ``os.getpgid(pid) == pid``)."""
    try:
        if proc.poll() is not None or os.getpgid(proc.pid) != proc.pid:
            return False
        os.killpg(proc.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        return False
    proc.wait()
    return True


def start(argv: list[str], cwd: Path, env: dict, log: Path, groups: set) -> subprocess.Popen:
    """One child in a session of its own, standard input closed, output to `log`, registered in `groups` at once."""
    with log.open("wb") as handle:
        proc = subprocess.Popen(argv, cwd=cwd, env=env, stdin=subprocess.DEVNULL, stdout=handle, stderr=subprocess.STDOUT,
                                start_new_session=True)
    groups.add(proc.pid)
    return proc


def finish(proc: subprocess.Popen, groups: set) -> None:
    """End `proc`'s group if it is still running, reap it and forget it (a reaped pid is never signalled again)."""
    end_group(proc)
    proc.wait()
    groups.discard(proc.pid)


def run_once(argv: list[str], cwd: Path, env: dict, log: Path, ceiling: float, groups: set) -> dict:
    """Run a command to its end or to `ceiling` seconds: ``{returncode, timeout, seconds, output}`` (returncode None on a timeout)."""
    began = time.monotonic()
    try:
        proc = start(argv, cwd, env, log, groups)
    except OSError as exc:  # the command is not there: a run that exited 127, not a crash of the harness
        return {"returncode": 127, "timeout": False, "seconds": 0.0, "output": f"could not start {argv[0]}: {exc}"}
    timed_out = False
    try:
        try:
            proc.wait(timeout=ceiling)
        except subprocess.TimeoutExpired:
            timed_out = True
    finally:
        finish(proc, groups)
    try:
        with log.open("rb") as handle:
            handle.seek(0, os.SEEK_END)
            handle.seek(max(0, handle.tell() - TAIL_BYTES))
            output = handle.read().decode("utf-8", "replace")
    except OSError:
        output = ""
    return {"returncode": None if timed_out else proc.returncode, "timeout": timed_out,
            "seconds": round(time.monotonic() - began, 3), "output": output}


def child_env(extra: dict | None = None) -> dict:
    """The harness's environment for a delivered product's own commands: no PORT of ours, no colour."""
    env = {key: value for key, value in os.environ.items() if key != "PORT"}
    return {**env, "NO_COLOR": "1", **(extra or {})}


# --------------------------------------------------------------------------------------------------------------------
# The copy

def export_delivery(work: Path, dest: Path) -> int:
    """Copy the files `work` tracks or would track (its ignore rules applied), without .git, into `dest`; returns how many.
    `work` is only read."""
    listed = subprocess.run(["git", "-C", str(work), "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
                            capture_output=True, check=True).stdout
    count = 0
    for raw in sorted({name for name in listed.split(b"\0") if name}):
        relative = Path(raw.decode("utf-8", "surrogateescape"))
        source = work / relative
        if not (source.is_file() or source.is_symlink()):
            continue  # tracked and deleted
        target = dest / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target, follow_symlinks=False)
        count += 1
    return count


def extension_census(copy: Path) -> str:
    """The delivered files by extension, for a reason that says what a catalog does not cover: `.md 5, .py 3`."""
    counts: dict[str, int] = {}
    for path in copy.rglob("*"):
        if path.is_file():
            counts[path.suffix or "(none)"] = counts.get(path.suffix or "(none)", 0) + 1
    return ", ".join(f"{extension} {number}" for extension, number in sorted(counts.items())) or "no files"


# --------------------------------------------------------------------------------------------------------------------
# Mutation

def targets(copy: Path, exclude: list[str]) -> dict[str, Catalog]:
    """The delivered source files an operator catalog covers: relative path -> catalog. Not a test file, not under a test or
    dependency folder, not under a path the case excludes."""
    chosen: dict[str, Catalog] = {}
    for path in sorted(copy.rglob("*")):
        catalog = CATALOGS.get(path.suffix)
        relative = path.relative_to(copy)
        if catalog is None or not path.is_file() or path.is_symlink():
            continue
        parts = relative.parts
        if any(part in catalog.not_source for part in parts[:-1]) or catalog.test_file(relative.as_posix()):
            continue
        if any(relative.as_posix() == prefix or relative.as_posix().startswith(prefix.rstrip("/") + "/") for prefix in exclude):
            continue
        chosen[relative.as_posix()] = catalog
    return chosen


def round_robin(per_file: dict[str, list]) -> list[tuple[str, dict]]:
    """Mutants in the order they are run: the first site of every file, then the second of every file, and so on, so that a
    ceiling hit leaves a sample of every file and not the files that sort last unmutated."""
    order: list[tuple[str, dict]] = []
    for depth in range(max((len(found) for found in per_file.values()), default=0)):
        order += [(name, found[depth]) for name, found in sorted(per_file.items()) if depth < len(found)]
    return order


def ratio(killed: int, survived: int) -> float | None:
    return round(killed / (killed + survived), 4) if killed + survived else None


def mutation(copy: Path, spec: dict, *, groups: set, stop: Callable[[], str | None], logs: Path,
             clock: Callable[[], float] = time.monotonic) -> dict:
    """The mutation block for the copy of a delivery: ``{observed: true, ...}`` or ``{observed: false, reason}``.

    `spec` is the case's ``quality.mutation``: ``command`` (the delivered tests' command, run in the copy) and optionally
    ``exclude`` (path prefixes that are not source). `stop` returns a reason when a stop was requested; it is asked before
    every mutant, and the phase then ends with no ratio. `clock` measures the phase against its ceiling.
    """
    command = shlex.split(spec["command"])
    chosen = targets(copy, list(spec.get("exclude") or []))
    if not chosen:
        return {"observed": False, "reason": "no delivered source file has an operator catalog (" + ", ".join(CATALOGS)
                + f") outside the test folders and the case's exclusions; the delivery's files by extension: {extension_census(copy)}"}
    originals = {name: (copy / name).read_bytes().decode("utf-8", "surrogateescape") for name in chosen}  # exact: CRLF stays
    found = {name: sites(text) for name, text in originals.items()}
    total = sum(len(items) for items in found.values())
    per_file = {name: {"sites": len(found[name]), "loaded_by_tests": None, "killed": 0, "timeout": 0, "survived": 0, "invalid": 0,
                       "not_run": 0} for name in sorted(found)}
    if not total:
        return {"observed": False, "reason": f"no operator applies to any of the {len(chosen)} delivered source files: "
                + ", ".join(sorted(chosen))}
    logs.mkdir(parents=True, exist_ok=True)
    began = clock()
    catalog = next(iter(chosen.values()))
    coverage = logs / "coverage"
    shutil.rmtree(coverage, ignore_errors=True)
    base = run_once(command, copy, child_env(catalog.coverage_env(coverage)), logs / "baseline.log", RUN_CEILING_SECONDS, groups)
    tests = catalog.count(base["output"], base["returncode"]) if not base["timeout"] else None
    baseline = {"returncode": base["returncode"], "seconds": base["seconds"], "tests": tests}
    if base["timeout"]:
        return {"observed": False, "baseline": baseline, "reason": f"the unmutated copy's test run did not finish within the "
                f"ceiling ({RUN_CEILING_SECONDS} s): a mutant could not be told from it"}
    if base["returncode"] != 0:
        return {"observed": False, "baseline": baseline, "reason": f"the unmutated copy's test run exited {base['returncode']}: "
                "with a red baseline every mutant would read as caught"}
    if not tests:
        return {"observed": False, "baseline": baseline, "reason": "the unmutated copy's test run counted "
                + ("no tests" if tests == 0 else "nothing readable (no summary the engine's test counter recognises)")
                + ": a run that ran no test catches no mutant"}
    loaded = catalog.coverage_files(coverage, copy)
    for name, row in per_file.items():
        row["loaded_by_tests"] = None if loaded is None else name in loaded
    sites_seen = ceiling_hit = False
    killed = timeouts = survived = invalid = not_run = 0
    survivors: list[dict] = []
    ordered = round_robin(found)
    for position, (name, site) in enumerate(ordered):
        why = stop()
        if why:
            return {"observed": False, "reason": f"{why}: the mutation phase ended after {position} of {total} mutants and "
                    "records no ratio", "baseline": baseline}
        if clock() - began >= PHASE_CEILING_SECONDS:
            ceiling_hit = True
            for rest_name, _site in ordered[position:]:
                per_file[rest_name]["not_run"] += 1
            not_run = len(ordered) - position
            break
        path = copy / name
        text = originals[name]
        row = per_file[name]
        try:
            path.write_bytes((text[:site["start"]] + site["new"] + text[site["end"]:]).encode("utf-8", "surrogateescape"))
            if catalog.syntax_check is not None:
                syntax = run_once(catalog.syntax_check(path), copy, child_env(), logs / "syntax.log", RUN_CEILING_SECONDS, groups)
                if syntax["returncode"] != 0:
                    invalid += 1
                    row["invalid"] += 1
                    continue
            result = run_once(command, copy, child_env(), logs / "mutant.log", RUN_CEILING_SECONDS, groups)
        finally:
            path.write_bytes(text.encode("utf-8", "surrogateescape"))
        if result["timeout"] or result["returncode"] != 0:
            killed += 1
            row["killed"] += 1
            if result["timeout"]:
                timeouts += 1
                row["timeout"] += 1
        else:
            survived += 1
            row["survived"] += 1
            survivors.append({"file": name, "line": site["line"], "op": site["op"], "from": site["old"], "to": site["new"]})
    why = stop()  # a run the stop itself killed reads as a failing run: never let it into a ratio
    if why:
        return {"observed": False, "reason": f"{why}: the mutation phase ended during its last mutant and records no ratio",
                "baseline": baseline}
    for row in per_file.values():
        # A mutant the tests caught proves the file ran, even in a process the coverage record misses: a server the tests spawn and
        # then stop with a signal exits without writing its coverage (the saved r1 Checkers run: 23 of server.js's 32 mutants were
        # caught and the coverage record alone said it was never loaded).
        if row["killed"] and row["loaded_by_tests"] is not True:
            row["loaded_by_tests"] = True
    return {"observed": True, "operator_id": catalog.ident, "command": spec["command"], "source": spec.get("source"),
            "baseline": baseline,
            "sites": total, "killed": killed, "timeout": timeouts, "survived": survived, "invalid": invalid, "not_run": not_run,
            "ratio": ratio(killed, survived), "ceiling_hit": ceiling_hit,
            "ceilings": {"run_seconds": RUN_CEILING_SECONDS, "phase_seconds": PHASE_CEILING_SECONDS},
            "per_file": per_file, "survivors": survivors, "seconds": round(clock() - began, 1)}


# --------------------------------------------------------------------------------------------------------------------
# Held-out acceptance

def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def load_checks(module: str, checks_dir: Path):
    """The module of held-out checks `<checks_dir>/<module>.py`: ``CHECKS`` maps a check id to ``fn(base_url) -> (ok, note)``."""
    path = checks_dir / f"{module}.py"
    spec = importlib.util.spec_from_file_location(f"shiploop_e2e_held_out_{module}", path)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


def acceptance(copy: Path, block: dict, *, groups: set, stop: Callable[[], str | None], logs: Path,
               checks_dir: Path = HERE / "checks") -> dict:
    """One block of held-out checks run against the copy's server: ``{observed, source, checks: [{id, source, pass, note}]}``.

    The server is started as ``block['start']`` with PORT set to a free port, in the copy, in a group of its own; each check
    gets its base URL. A check that raises fails with the exception as its note; a server that never listens leaves every check
    unrun and the block unobserved. The checks run in this process: nothing but the server's own command line reaches an argv.
    """
    declared = [item["id"] for item in block["checks"]]
    try:
        implemented = load_checks(block["module"], checks_dir).CHECKS
    except Exception as exc:  # a harness defect, never a delivery's: say so
        return {"observed": False, "reason": f"the held-out module {block['module']!r} could not be loaded: {exc!r}"}
    missing = [ident for ident in declared if ident not in implemented]
    if missing:
        return {"observed": False, "reason": f"the held-out module {block['module']!r} has no check for: {', '.join(missing)}"}
    logs.mkdir(parents=True, exist_ok=True)
    port = free_port()
    try:
        proc = start(shlex.split(block["start"]), copy, child_env({"PORT": str(port)}), logs / f"server-{block['module']}.log",
                     groups)
    except OSError as exc:
        return {"observed": False, "reason": f"the product's server ({block['start']}) could not be started: {exc}"}
    try:
        end = time.monotonic() + LISTEN_CEILING_SECONDS
        while True:
            if proc.poll() is not None:
                return {"observed": False, "reason": f"the product's server ({block['start']}) exited {proc.returncode} before it "
                        f"listened on PORT={port}"}
            try:
                socket.create_connection(("127.0.0.1", port), timeout=0.2).close()
                break
            except OSError:
                pass
            if time.monotonic() >= end:
                return {"observed": False, "reason": f"the product's server ({block['start']}) did not listen on PORT={port} "
                        f"within {LISTEN_CEILING_SECONDS} s"}
            time.sleep(POLL_SECONDS)
        results = []
        for item in block["checks"]:
            why = stop()
            if why:
                return {"observed": False, "reason": f"{why}: the held-out checks ended after {len(results)} of {len(declared)}"}
            try:
                ok, note = implemented[item["id"]](f"http://127.0.0.1:{port}")
                results.append({"id": item["id"], "source": item.get("source"), "pass": bool(ok), "note": str(note)[:300]})
            except Exception as exc:
                results.append({"id": item["id"], "source": item.get("source"), "pass": False, "note": f"raised {exc!r}"[:300]})
    finally:
        finish(proc, groups)
    return {"observed": True, "source": block.get("source"), "ids": declared,
            "passed": [row["id"] for row in results if row["pass"]], "checks": results}


# --------------------------------------------------------------------------------------------------------------------
# Facts read from the run's own events

CLAUDE_MEMORY = re.compile(r"(?:^|/)\.claude/projects/[^/]+/memory(?:/|$)")
MEMORY_TOOLS = ("Write", "Edit", "MultiEdit")


def memory_writes(events_path: Path) -> list[dict]:
    """The Claude file-write calls (``Write``, ``Edit``, ``MultiEdit``) whose path is under a ``~/.claude/projects/*/memory``
    folder, in the order made: ``{path, tool, line}`` with `line` the 1-based line of events.jsonl. Computed from the run's
    events, so a regrade gives the same answer whatever the live profile holds now; a write made by a shell command is not seen."""
    found = []
    for number, event in metrics.events(events_path):
        if event.get("type") != "assistant":
            continue
        for block in (event.get("message") or {}).get("content") or []:
            if isinstance(block, dict) and block.get("type") == "tool_use" and block.get("name") in MEMORY_TOOLS:
                path = (block.get("input") or {}).get("file_path")
                if isinstance(path, str) and CLAUDE_MEMORY.search(path):
                    found.append({"path": path, "tool": block["name"], "line": number + 1})
    return found


def held_out_markers(blocks: list[dict]) -> list[str]:
    """What names a held-out check in a host's events: its module, the checks folder, the variable the checks run under and
    the catalog the harness reads them from."""
    names = {"E2E_CHECKS", "shiploop_e2e/checks", "shiploop_e2e/cases.json"}
    names.update(block["module"] for block in blocks)
    return sorted(names)


def held_out_seen(events_path: Path, blocks: list[dict]) -> int:
    """How many lines of the host's events mention a held-out marker (0 is a measured none)."""
    markers = held_out_markers(blocks)
    return sum(1 for line in events_path.read_text(errors="replace").splitlines() if any(mark in line for mark in markers))


def event_facts(events_path: Path, hosts_used: list[str], blocks: list[dict]) -> tuple[dict, dict]:
    """``({memory_writes, held_out_seen}, {key: reason})`` for the keys that could not be read (null here, never 0 or [])."""
    facts: dict = {"memory_writes": None, "held_out_seen": None}
    unmeasured: dict = {}
    readable = events_path.is_file()
    if readable:
        try:
            events_path.read_text(errors="replace")
        except OSError:
            readable = False
    if not readable:
        why = f"{events_path.name} is absent or unreadable in the run folder"
        return facts, {"memory_writes": why, "held_out_seen": why}
    if "claude" in hosts_used:
        facts["memory_writes"] = memory_writes(events_path)
    else:
        unmeasured["memory_writes"] = ("the detector reads Claude's file-write calls and this run's launch records show "
                                       + (", ".join(hosts_used) if hosts_used else "no host"))
    if blocks:
        facts["held_out_seen"] = held_out_seen(events_path, blocks)
    else:
        unmeasured["held_out_seen"] = "the case declares no held-out acceptance, so nothing is held out"
    return facts, unmeasured


# --------------------------------------------------------------------------------------------------------------------
# The block

def declared(spec: dict | None) -> bool:
    return bool(spec and (spec.get("mutation") or spec.get("acceptance")))


def summary(block: dict | None) -> dict | None:
    """The compact form a baseline row carries (None where the run has no block)."""
    if not isinstance(block, dict) or not block.get("declared"):
        return None  # a case that declares nothing has nothing to compare
    row: dict = {"observed": bool(block.get("observed")), "hosts": block.get("hosts"), "mixed_host": block.get("mixed_host")}
    mut, acc = block.get("mutation"), block.get("acceptance")
    if mut is not None:
        row["mutation"] = ({k: mut.get(k) for k in ("operator_id", "sites", "killed", "survived", "ratio", "ceiling_hit")}
                           if mut.get("observed") else {"observed": False})
    if acc is not None:
        row["acceptance"] = ({"ids": len(acc["ids"]), "passed": len(acc["passed"])} if acc.get("observed") else {"observed": False})
    return row


def line(block: dict) -> str:
    """The one printed line for a run's block: what was measured, or why nothing was."""
    parts = []
    mut, acc = block.get("mutation"), block.get("acceptance")
    if mut is not None:
        parts.append(
            f"mutation {mut['killed']} of {mut['killed'] + mut['survived']} caught (ratio {mut['ratio']}, {mut['operator_id']}, "
            f"{len(mut['per_file'])} files{', ceiling hit' if mut['ceiling_hit'] else ''}"
            + (f", never loaded by the tests: {', '.join(n for n, r in mut['per_file'].items() if r['loaded_by_tests'] is False)}"
               if any(r["loaded_by_tests"] is False for r in mut["per_file"].values()) else "") + ")"
            if mut.get("observed") else f"mutation not observed: {mut.get('reason')}")
    if acc is not None:
        failed = [i for i in acc.get("ids", []) if i not in acc.get("passed", [])]
        parts.append(f"held-out {len(acc['passed'])} of {len(acc['ids'])} pass" + (f" (failed: {', '.join(failed)})" if failed else "")
                     if acc.get("observed") else f"held-out not observed: {acc.get('reason')}")
    if not parts:
        parts.append(f"not observed: {block.get('reason')}")
    seen, writes = block.get("held_out_seen"), block.get("memory_writes")  # null is unknown, and its reason is in `unmeasured`
    if seen is not None:
        parts.append(f"held-out names in the host's events: {seen}")
    if writes is not None:
        parts.append(f"Claude memory writes: {len(writes)}")
    return "; ".join(parts)


def measure(out: Path, work: Path, spec: dict, *, gate: str | None, hosts_used: list[str], groups: set,
            stop: Callable[[], str | None], checks_dir: Path = HERE / "checks") -> dict:
    """The ``quality`` block of a run.

    `gate` is the reason the delivery is not to be measured (None when it is a finished, returned one). `spec` is what the case
    declares (``mutation``, ``acceptance``: a list of blocks). Events are read either way. The copy and every log live under
    ``<out>/quality``, which is removed first and whose listeners are stopped last; nothing outside it is touched.
    """
    began = time.monotonic()
    blocks = list((spec or {}).get("acceptance") or [])
    block: dict = {"observed": False, "declared": [key for key in ("mutation", "acceptance") if (spec or {}).get(key)],
                   "hosts": list(hosts_used), "mixed_host": len(hosts_used) > 1}
    facts, unmeasured = event_facts(out / "events.jsonl", hosts_used, blocks)
    if gate is not None:
        block["reason"] = gate
    elif not declared(spec):
        block["reason"] = "the case declares no quality measures (no mutation command, no held-out acceptance)"
    else:
        folder = out / "quality"
        shutil.rmtree(folder, ignore_errors=True)  # ours: a regrade's earlier copy
        folder.mkdir(parents=True)
        try:
            copy = folder / "copy"
            copy.mkdir()
            block["delivered_files"] = export_delivery(work, copy)
            if blocks:
                parts = [acceptance(copy, one, groups=groups, stop=stop, logs=folder / "logs", checks_dir=checks_dir)
                         for one in blocks]
                block["acceptance"] = merge_acceptance(parts)
            if spec.get("mutation"):
                block["mutation"] = mutation(copy, spec["mutation"], groups=groups, stop=stop, logs=folder / "logs")
        finally:
            block["left_behind"] = listeners.reap(folder)  # only this folder: a regrade reaps nothing of the run's own
        measured = [block.get(key) for key in ("mutation", "acceptance")]
        block["observed"] = any(isinstance(part, dict) and part.get("observed") for part in measured)
        if not block["observed"]:
            block["reason"] = "none of the declared measures could be taken: " + "; ".join(
                f"{key}: {part.get('reason')}" for key, part in zip(("mutation", "acceptance"), measured) if part)
    block.update(facts)
    if unmeasured:
        block["unmeasured"] = unmeasured
    block["seconds"] = round(time.monotonic() - began, 1)
    return block


def merge_acceptance(parts: list[dict]) -> dict:
    """One acceptance record from the blocks of a case (a followed case's first). Unobserved when any block could not run."""
    if len(parts) == 1:
        return parts[0]
    bad = [part for part in parts if not part.get("observed")]
    if bad:
        return {"observed": False, "reason": "; ".join(str(part.get("reason")) for part in bad)}
    return {"observed": True, "source": " | ".join(str(part.get("source")) for part in parts),
            "ids": [i for part in parts for i in part["ids"]], "passed": [i for part in parts for i in part["passed"]],
            "checks": [row for part in parts for row in part["checks"]]}
