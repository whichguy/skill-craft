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
# Time limits. None is a measurement; each is a point past which something is taken to have hung, and a result records it.
# RUN_CEILING_SECONDS defines a hang: one test run (the unmutated baseline or one mutant) that has not ended by then is a hang,
# which counts as a caught mutant and as a `timeout`, so changing it changes results. 10 s is the limit the prototype sweeps
# of the eight saved deliveries ran with, beside suites that took 0.23 to 1.27 s.
RUN_CEILING_SECONDS = 10
# PHASE_CEILING_SECONDS is the point at which the whole mutation phase gives up; the mutants not reached are `not_run` and
# `ceiling_hit` says so. About five times the longest sweep measured here (113 s) and well under a task launcher's limit of
# about 30 minutes; reaching it is recorded, never hidden.
PHASE_CEILING_SECONDS = 600
# How long a product's server has to start listening; past it the held-out checks are `observed: false`.
LISTEN_CEILING_SECONDS = 10
POLL_SECONDS = 0.01  # how often a running child is looked at
TAIL_BYTES = 200_000  # how much of the end of a test run's output is read back: the summary is last
NOTE_CHARS = 300  # display only: a held-out check's note is cut here
EVIDENCE_CHARS = 200  # display only: the failing line kept for a caught mutant is cut here
# The operator catalog a ratio belongs to. Any change to the operators or to the masking is a new id: ratios of two ids
# are never compared.
OPERATOR_ID = "js-1"


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


# node's reporters mark a failing test with a cross (spec, the default when piped) or `not ok` (TAP)
JS_FAILING_TEST = re.compile(r"^\s*(?:\u2716|not ok)\s+(.+?)\s*$", re.M)
JS_TIMING = re.compile(r"\s*\([\d.]+ms\)$")
HTML_SCRIPT = re.compile(r"<script\b([^>]*)>(.*?)</script>", re.S | re.I)


def js_failing_line(output: str) -> str:
    """The first failing test of a run's output, as its reporter named it (timing and TAP numbering removed, so two runs read the
    same); the last non-empty line when no test is named (a file that cannot load)."""
    found = JS_FAILING_TEST.search(output)
    if found:
        name = re.sub(r"^(?:\d+\s+)?-?\s*", "", JS_TIMING.sub("", found.group(1)))
        return (("not ok - " if found.group(0).lstrip().startswith("not ok") else "\u2716 ") + name)[:EVIDENCE_CHARS]
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    return (lines[-1] if lines else "no output")[:EVIDENCE_CHARS]


def js_page_scripts(copy: Path, exclude: list[str]) -> list[dict]:
    """The HTML files of the delivery that carry inline script, with the lines of script: JavaScript no text operator of this
    catalog reaches, because it is not in a `.js` file. A script with a `src` is a file, not inline."""
    found = []
    for path in sorted(copy.rglob("*")):
        relative = path.relative_to(copy).as_posix()
        if path.suffix.lower() not in (".html", ".htm") or not path.is_file() or path.is_symlink():
            continue
        if any(part in JS_NOT_SOURCE_FOLDERS for part in path.relative_to(copy).parts[:-1]):
            continue
        if any(relative == prefix or relative.startswith(prefix.rstrip("/") + "/") for prefix in exclude):
            continue
        lines = sum(len(body.strip("\n").splitlines()) for attrs, body in HTML_SCRIPT.findall(path.read_text(errors="replace"))
                    if "src=" not in attrs.lower())
        if lines:
            found.append({"file": relative, "inline_script_lines": lines})
    return found


REFUSE_PORTS_PRELOAD = HERE / "refuse_ports.cjs"


def js_guard_env(ports: list[int], log: Path, preload: Path = REFUSE_PORTS_PRELOAD) -> dict:
    """The environment that makes every Node process of a run (a test's children included) refuse the declared ports and note each
    refusal in `log`: the preload is added to NODE_OPTIONS beside whatever was there."""
    quoted = f'"{preload}"' if " " in str(preload) else str(preload)
    options = " ".join(part for part in (os.environ.get("NODE_OPTIONS", "").strip(), f"--require {quoted}") if part)
    return {"NODE_OPTIONS": options, "SHIPLOOP_E2E_REFUSE_PORTS": ",".join(str(port) for port in ports),
            "SHIPLOOP_E2E_REFUSE_LOG": str(log)}


class Catalog:
    """What the harness knows about one language: its operators, its test files, how to check a syntax, how a runner counts and
    names a failure, which ports a run is kept off, which files a run loaded and which page script no operator reaches."""

    def __init__(self, ident: str, extensions: tuple, operators, not_source: tuple, test_file, syntax_check, count, coverage_env,
                 coverage_files, guard_env, failing_line, page_scripts):
        self.ident, self.extensions, self.operators = ident, extensions, operators
        self.not_source, self.test_file = not_source, test_file
        self.syntax_check, self.count, self.coverage_env, self.coverage_files = syntax_check, count, coverage_env, coverage_files
        self.guard_env, self.failing_line, self.page_scripts = guard_env, failing_line, page_scripts


JS = Catalog(OPERATOR_ID, (".js", ".mjs", ".cjs"), JS_OPERATORS, JS_NOT_SOURCE_FOLDERS, JS_TEST_FILE.search,
             lambda path: ["node", "--check", str(path)], js_test_count,
             lambda directory: {"NODE_V8_COVERAGE": str(directory)}, js_coverage_files, js_guard_env, js_failing_line, js_page_scripts)
CATALOGS = {extension: JS for extension in JS.extensions}


# --------------------------------------------------------------------------------------------------------------------
# Processes: every child in a group of its own, registered while its leader is unreaped, its whole group ended with it.

def exited(proc: subprocess.Popen) -> bool:
    """Whether the leader has exited, without reaping it: an exited, unreaped leader is a zombie that still pins its pid."""
    if proc.returncode is not None:
        return True
    try:
        done = os.waitid(os.P_PID, proc.pid, os.WEXITED | os.WNOHANG | os.WNOWAIT)
    except ChildProcessError:
        return True
    return done is not None and done.si_pid != 0


def end_group(proc: subprocess.Popen) -> bool:
    """SIGKILL the whole process group `proc` leads and reap `proc`; False (nothing signalled) when it was already reaped, or
    is alive and does not lead a group of its own.

    This is the one place the phase signals a group. A group is ended while its leader is alive and leads it, or has exited and
    is not yet reaped: an unreaped leader keeps its pid, so the number cannot have been reused for someone else's group, and
    anything a test run left behind shares that group (a reaped leader would leave it orphaned and unreachable). On macOS
    ``getpgid`` raises for an exited, unreaped process while ``killpg`` still works, so the guard is applied only to a leader
    that is still running. The harness's other group kills (``run.kill_group``, ``hosts.run_process``) signal without this
    guard; a test helper (``kill_hosts``) uses it.
    """
    if proc.returncode is not None:  # reaped: the pid may belong to someone else now
        return False
    if not exited(proc):
        try:
            if os.getpgid(proc.pid) != proc.pid:
                return False
        except ProcessLookupError:
            pass  # it exited just now: still an unreaped zombie holding the id
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        proc.wait()
        return False
    proc.wait()
    return True


def start(argv: list[str], cwd: Path, env: dict, log: Path, groups: set) -> subprocess.Popen:
    """One child in a session of its own, standard input closed, output to `log`, registered in `groups` at once."""
    with log.open("wb") as handle:
        proc = subprocess.Popen(argv, cwd=cwd, env=env, stdin=subprocess.DEVNULL, stdout=handle, stderr=subprocess.STDOUT,
                                start_new_session=True)
    if os.getpgid(proc.pid) != proc.pid:  # setsid ran before exec returned: anything else means the id is not ours to signal
        proc.kill()
        proc.wait()
        raise OSError(f"{argv[0]} did not start in a session of its own")
    groups.add(proc.pid)
    return proc


def finish(proc: subprocess.Popen, groups: set) -> None:
    """End `proc`'s whole group (a hung leader, or what a leader that exited left behind), reap it and forget it."""
    end_group(proc)
    proc.wait()
    groups.discard(proc.pid)


def wait_exit(proc: subprocess.Popen, ceiling: float) -> bool:
    """Wait up to `ceiling` seconds for the leader to exit without reaping it. True when it exited by itself."""
    end = time.monotonic() + ceiling
    while not exited(proc):
        if time.monotonic() >= end:
            return False
        time.sleep(POLL_SECONDS)
    return True


def run_once(argv: list[str], cwd: Path, env: dict, log: Path, ceiling: float, groups: set) -> dict:
    """Run a command to its end or to `ceiling` seconds: ``{returncode, timeout, seconds, output}`` (returncode None on a timeout).
    Whatever else shares the command's group is ended with it."""
    began = time.monotonic()
    try:
        proc = start(argv, cwd, env, log, groups)
    except OSError as exc:  # the command is not there: a run that exited 127, not a crash of the harness
        return {"returncode": 127, "timeout": False, "seconds": 0.0, "output": f"could not start {argv[0]}: {exc}"}
    timed_out = False
    try:
        timed_out = not wait_exit(proc, ceiling)
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


def count_refusals(log: Path) -> int:
    """How many times the preload refused a declared port in one run (one line each); 0 when it wrote nothing."""
    try:
        return len(log.read_text().splitlines())
    except OSError:
        return 0


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
             clock: Callable[[], float] = time.monotonic, ports: list[int] | tuple = ()) -> dict:
    """The mutation block for the copy of a delivery: ``{observed: true, ...}`` or ``{observed: false, reason}``.

    `spec` is the case's ``quality.mutation``: ``command`` (the delivered tests' command, run in the copy) and optionally
    ``exclude`` (path prefixes that are not source). `ports` are the fixed ports the case declares: every run is kept off them
    and the refusals are counted; a delivery whose own unmutated tests touch one is not run. `stop` returns a reason when a stop
    was requested; it is asked before every run, and the phase then ends with no ratio. `clock` measures the phase against its
    ceiling.

    A failing run is run once more before the mutant counts as caught: a failure that does not repeat is ``unconfirmed``, out of
    the ratio, and a hang is not repeated. ``killed + survived + invalid + unconfirmed + not_run == sites``.
    """
    command = shlex.split(spec["command"])
    exclude = list(spec.get("exclude") or [])
    chosen = targets(copy, exclude)
    if not chosen:
        return {"observed": False, "reason": "no delivered source file has an operator catalog (" + ", ".join(CATALOGS)
                + f") outside the test folders and the case's exclusions; the delivery's files by extension: {extension_census(copy)}"}
    originals = {name: (copy / name).read_bytes().decode("utf-8", "surrogateescape") for name in chosen}  # exact: CRLF stays
    found = {name: sites(text) for name, text in originals.items()}
    total = sum(len(items) for items in found.values())
    per_file = {name: {"sites": len(found[name]), "lines": len(originals[name].splitlines()), "loaded_by_tests": None, "killed": 0,
                       "timeout": 0, "port_refusals": 0, "survived": 0, "invalid": 0, "unconfirmed": 0, "not_run": 0}
                for name in sorted(found)}
    if not total:
        return {"observed": False, "reason": f"no operator applies to any of the {len(chosen)} delivered source files: "
                + ", ".join(sorted(chosen))}
    logs.mkdir(parents=True, exist_ok=True)
    began = clock()
    catalog = next(iter(chosen.values()))
    ports = list(ports)
    refusal_logs = logs / "refusals"
    refusal_logs.mkdir(exist_ok=True)

    def run_tests(label: str, extra: dict | None = None) -> tuple[dict, int]:
        """One run of the case's command under the port guard; its result and how many refusals it saw."""
        log = refusal_logs / f"{label}.log"
        env = {**(extra or {}), **(catalog.guard_env(ports, log) if ports else {})}
        result = run_once(command, copy, child_env(env), logs / "run.log", RUN_CEILING_SECONDS, groups)
        return result, count_refusals(log)

    def failed(result: dict) -> bool:
        return result["timeout"] or result["returncode"] != 0

    coverage = logs / "coverage"
    shutil.rmtree(coverage, ignore_errors=True)
    base, base_refusals = run_tests("baseline", catalog.coverage_env(coverage))
    tests = catalog.count(base["output"], base["returncode"]) if not base["timeout"] else None
    baseline = {"returncode": base["returncode"], "seconds": base["seconds"], "tests": tests, "port_refusals": base_refusals}
    if base_refusals:
        return {"observed": False, "baseline": baseline, "refuse_ports": ports, "reason": f"its tests bind a fixed port; not run: "
                f"the unmutated copy's test run touched a declared port ({', '.join(map(str, ports))}) {base_refusals} "
                f"time{'s' if base_refusals != 1 else ''}"}
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
    ceiling_hit = False
    killed = timeouts = survived = invalid = unconfirmed = not_run = port_refusals = port_refused = 0
    not_run_reasons: dict[str, int] = {}
    kills: list[dict] = []
    survivors: list[dict] = []
    unconfirmed_mutants: list[dict] = []
    ordered = round_robin(found)

    def stopped(position: int, where: str) -> dict | None:
        why = stop()
        return None if not why else {"observed": False, "baseline": baseline,
                                     "reason": f"{why}: the mutation phase ended {where} and records no ratio"}

    for position, (name, site) in enumerate(ordered):
        ended = stopped(position, f"after {position} of {total} mutants")
        if ended:
            return ended
        if clock() - began >= PHASE_CEILING_SECONDS:
            ceiling_hit = True
            for rest_name, _site in ordered[position:]:
                per_file[rest_name]["not_run"] += 1
            not_run += len(ordered) - position
            not_run_reasons["the phase ceiling was reached"] = len(ordered) - position
            break
        path = copy / name
        text = originals[name]
        row = per_file[name]
        mutant = {"file": name, "line": site["line"], "op": site["op"], "from": site["old"], "to": site["new"]}
        try:
            path.write_bytes((text[:site["start"]] + site["new"] + text[site["end"]:]).encode("utf-8", "surrogateescape"))
            if catalog.syntax_check is not None:
                syntax = run_once(catalog.syntax_check(path), copy, child_env(), logs / "syntax.log", RUN_CEILING_SECONDS, groups)
                if syntax["timeout"] or syntax["returncode"] == 127:
                    # Neither a program nor a non-program was seen: the mutant is out of the ratio for a reason that is not the delivery's
                    reason = "its syntax check did not finish" if syntax["timeout"] else "its syntax check could not start"
                    not_run += 1
                    row["not_run"] += 1
                    not_run_reasons[reason] = not_run_reasons.get(reason, 0) + 1
                    continue
                if syntax["returncode"] != 0:
                    invalid += 1
                    row["invalid"] += 1
                    continue
            result, refusals = run_tests(f"mutant-{position}")
            again = None
            if failed(result) and not result["timeout"]:
                ended = stopped(position, f"during mutant {position + 1} of {total}")  # a run the stop killed must not confirm anything
                if ended:
                    return ended
                again, _ = run_tests(f"mutant-{position}-again")
        finally:
            path.write_bytes(text.encode("utf-8", "surrogateescape"))
        port_refusals += refusals
        row["port_refusals"] += refusals
        if not failed(result):
            survived += 1
            row["survived"] += 1
            survivors.append({**mutant, **({"port_refusals": refusals} if refusals else {})})
        elif again is not None and not failed(again):
            unconfirmed += 1
            row["unconfirmed"] += 1
            unconfirmed_mutants.append({**mutant, "first": {"returncode": result["returncode"], "evidence": catalog.failing_line(result["output"])},
                                        "second": {"returncode": again["returncode"]}})
        else:
            killed += 1
            row["killed"] += 1
            if result["timeout"]:
                timeouts += 1
                row["timeout"] += 1
            if refusals:
                port_refused += 1
            kills.append({**mutant, "timeout": result["timeout"], "port_refusals": refusals,
                          "evidence": f"timed out after {RUN_CEILING_SECONDS} s" if result["timeout"] else catalog.failing_line(result["output"])})
    ended = stopped(len(ordered), "during its last mutant")  # a run the stop itself killed reads as a failing run
    if ended:
        return ended
    signs = {kill["file"] for kill in kills if not kill["timeout"]}
    for name, row in per_file.items():
        # A confirmed, non-timeout caught mutant is a sign the file ran, even in a process the coverage record misses: a server the
        # tests spawn and then stop with a signal exits without writing its coverage (the saved r1 Checkers run: 23 of server.js's 32
        # mutants were caught and the coverage record alone said it was never loaded). A hang or an unconfirmed failure is no sign:
        # load or a port collision can cause either in a file that never ran.
        if name in signs and row["loaded_by_tests"] is not True:
            row["loaded_by_tests"] = True
    return {"observed": True, "operator_id": catalog.ident, "command": spec["command"], "source": spec.get("source"),
            "baseline": baseline, "refuse_ports": ports,
            "sites": total, "killed": killed, "timeout": timeouts, "port_refused": port_refused, "port_refusals": port_refusals,
            "survived": survived, "invalid": invalid, "unconfirmed": unconfirmed, "not_run": not_run, "not_run_reasons": not_run_reasons,
            "ratio": ratio(killed, survived), "ceiling_hit": ceiling_hit,
            "ceilings": {"run_seconds": RUN_CEILING_SECONDS, "phase_seconds": PHASE_CEILING_SECONDS},
            "per_file": per_file, "uncovered": catalog.page_scripts(copy, exclude), "kills": kills, "survivors": survivors,
            "unconfirmed_mutants": unconfirmed_mutants, "seconds": round(clock() - began, 1)}


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
               checks_dir: Path = HERE / "checks", ports: list[int] | tuple = ()) -> dict:
    """One block of held-out checks run against the copy's server: ``{observed, source, checks: [{id, source, pass, note}]}``.

    The server is started as ``block['start']`` with PORT set to a free port, in the copy, in a group of its own; each check
    gets its base URL. A check that raises fails with the exception as its note; a server that never listens leaves every check
    unrun and the block unobserved. The checks run in this process: nothing but the server's own command line reaches an argv.
    The server runs under the same port guard as the mutation runs (`ports`): a product that ignores PORT and meets it says so.
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
    refusals_log = logs / f"refusals-{block['module']}.log"
    guard = JS.guard_env(list(ports), refusals_log) if ports else {}
    try:
        proc = start(shlex.split(block["start"]), copy, child_env({"PORT": str(port), **guard}), logs / f"server-{block['module']}.log",
                     groups)
    except OSError as exc:
        return {"observed": False, "reason": f"the product's server ({block['start']}) could not be started: {exc}"}
    try:
        end = time.monotonic() + LISTEN_CEILING_SECONDS
        while True:
            if proc.poll() is not None:
                refused = count_refusals(refusals_log)
                return {"observed": False, "reason": f"the product's server ({block['start']}) exited {proc.returncode} before it "
                        f"listened on PORT={port}" + (f"; it touched a declared port ({', '.join(map(str, ports))}) {refused} "
                                                      f"time{'s' if refused != 1 else ''}, so it may ignore PORT" if refused else "")}
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
                results.append({"id": item["id"], "source": item.get("source"), "pass": bool(ok), "note": str(note)[:NOTE_CHARS]})
            except Exception as exc:
                results.append({"id": item["id"], "source": item.get("source"), "pass": False, "note": f"raised {exc!r}"[:NOTE_CHARS]})
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
        if mut.get("observed"):
            counts = [f"{mut['unconfirmed']} unconfirmed" if mut.get("unconfirmed") else "",
                      f"{mut['timeout']} timeout{'s' if mut['timeout'] != 1 else ''}" if mut.get("timeout") else "",
                      f"{mut['port_refusals']} port refusal{'s' if mut['port_refusals'] != 1 else ''}" if mut.get("port_refusals") else "",
                      "ceiling hit" if mut.get("ceiling_hit") else ""]
            idle = [name for name, row in mut["per_file"].items() if row["loaded_by_tests"] is False]
            pages = [f"{page['file']} {page['inline_script_lines']} lines" for page in mut.get("uncovered") or []]
            parts.append(f"mutation {mut['killed']} of {mut['killed'] + mut['survived']} caught (ratio {mut['ratio']}, {mut['operator_id']}, "
                         f"{len(mut['per_file'])} files" + "".join(f", {count}" for count in counts if count)
                         + (f", no sign of a load in: {', '.join(idle)}" if idle else "")
                         + (f", page script no operator reaches: {', '.join(pages)}" if pages else "") + ")")
        else:
            parts.append(f"mutation not observed: {mut.get('reason')}")
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
    ports = list((spec or {}).get("refuse_ports") or [])
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
                parts = [acceptance(copy, one, groups=groups, stop=stop, logs=folder / "logs", checks_dir=checks_dir, ports=ports)
                         for one in blocks]
                block["acceptance"] = merge_acceptance(parts)
            if spec.get("mutation"):
                block["mutation"] = mutation(copy, spec["mutation"], groups=groups, stop=stop, logs=folder / "logs", ports=ports)
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
