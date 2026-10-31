#!/usr/bin/env python3
"""The stage suite's live tier, one sample (docs/plans/shiploop-stage-suite.md, "Stop at acceptance" and "The oracle"): a model
follows ONLY the one packet of a built scenario, a script grades what it did with the oracle the verify tier uses, and everything
the grade reads is kept in files, so a regrade needs no host and no ShipLoop.

It sits below the harness's top level, so it is in neither the evaluator digest nor the qualification snapshot (boundary.py). It
edits no harness module: ``run``, ``slice``, ``hosts``, ``packets``, ``sessionlog``, ``listeners`` and ``overlay`` are libraries
here. ``slice.drive`` cannot take another stop predicate, so ``drive`` below is the small piece that does, on ``run.launch``.

A sample (``run_sample``) is one folder, ``<root>/<stage>/<scenario>/<n>/``, laid out as a step slice's (slice.py) so the harness's
readers find the run in it. This is what the runner writes there (a host may add files of its own, such as its throwaway ``home/``):

    .harness-lock                the lock that says a harness is running this sample (listeners.hold_case); a regrade refuses
                                 a folder whose lock is held
    work/                        the product repository (the scenario's fixture and repo/)
    .stage-suite/fixture/        the fixture composed for the build (the scenario's fixture with its repo/ laid over it)
    .shiploop-runs/seed/{run,worktree}   the run directory and the execution checkout stage_build.build made
    build/                       the plugin built from this checkout, or from --ref (absent for a plugin_dir)
    seed-export/                 the execution checkout as the seed left it, taken before the host started
    export/                      the execution checkout when the host was ended (the stage's output tree)
    invocation.json              who ran what: host, model, effort, plugin identity, ref, overlay, the seeded block
    prompt.txt                   the request the packet follows (the scenario's step case prompt)
    host-prompt.txt, resume-N.txt   the prompt a host was started with, and the one it was resumed with the Nth time (hosts that
                                 take their prompt from a file write them)
    sessions.jsonl, events.jsonl, stderr.txt, timeline.jsonl, transcript.md, packet-archive/   the harness's own records
    resources.jsonl              the ledger of the process groups the sample started and ended (lifecycle.py)
    drive.json                   how the resume loop ended
    stage-result.json            the verdicts (rewritten by every regrade)
    error.txt                    only when the sample could not be run: why
    export-error.txt             only when the end export failed (every check that reads the tree then fails)

The stop (``accepted_reached``): the host is ended as soon as the SEEDED ACTION is accepted with ANY outcome (done, send-back,
blocked, add-work), or the run parks at that action's Improve stage (``active_improve.action_id`` is the seeded action, and the
producer's result is then ``active_improve.seed_result``), or the run stops being active. It is polled every ``run.POLL_SECONDS``.
A host that ends by itself before that is resumed when its host can be (bounded by the timeout and by ``run.RESUME_STALL``
resumed sessions in a row that moved the run nowhere); one that cannot ends the sample with its status recorded.

Three things keep the stop honest. (1) ``settle``: when the stop holds, the accepting command may still be running (``accept_effects``
saves the state and only then runs the lint finish, the commits and the knowledge close, all inside the command's dispatch under
the run lock), so the host is ended only once the run lock is free (SETTLE_SECONDS at most; the wait is kept in drive.json and
``settles``). What is waited for is that dispatch, post-save effects included. What is NOT waited for is anything the command does
after it lets the lock go (its trace row, the start of the progress observer), and the host's group is ended right after the wait.
An operator's stop (SIGTERM, SIGHUP, the stop file) that arrives during the wait ends the sample as not run: the half-finished tree
is neither exported nor graded. (2) ``_bounded_launch``: a process the host left in a session of its own holds its output open,
which the group kill cannot end and run.launch waits for; the launch is abandoned WATCHDOG_SECONDS after the deadline, and
STOP_GRACE_SECONDS after the stop at acceptance or after an operator's stop (SIGTERM, SIGHUP, the stop file) was first seen, so
``--timeout`` bounds the sample, though that process is left running. WATCHDOG_SECONDS exceeds SETTLE_SECONDS (the wait runs inside
the poll, past the deadline, where launch cannot look at the clock): the watchdog's clock is the deadline plus the whole wait and
a minute, it does not start after ``settle``. (3) A sample an operator ends (``out/stop``, SIGTERM or SIGHUP to the harness) raises
``SampleStopped`` after the stop file is consumed: nothing was measured, no stage-result.json is written (error.txt says why), and
``grade_sample`` refuses such a folder. It refuses any folder that was not run to the end: one with an error.txt and no export,
one with no export, no export-error.txt and no stage-result.json (still running, or its harness was killed), and one whose
``.harness-lock`` is held.

The grade (``grade_sample``) reads files only: ``collect_bundle`` rebuilds the oracle's ``Bundle`` from the sample folder, the
scenario's ``oracle`` checks run on it, and the verdicts are

    process       the last host session was ended by the stop (status ``stage-complete``), not a timeout, failure or crash
    accepted      the seeded action was accepted (state ``accepted``) or parked at its Improve stage
    no_overshoot  no result was accepted for a stage after the seeded one (slice.overshoot_after) and no history row follows
                  the seeded action's own (a host sent back that redoes an earlier stage overshoots too; ``overshoot``)
    oracle        stage_oracle.verdict passed: every id caught or held and no check without an id failed

``caught`` and ``held`` are per id. An id is caught or held only when the seeded action was accepted: a host that delivered no
output holds no control by doing nothing, so its ids are all False (the raw check results are kept under ``checks``). ``value``
is the fraction of planted and control ids caught or held: a per-sample number suitable for handing to ``experiment.py decide``
(no code reads stage-result.json today). ``pass`` needs every verdict, every id caught or held.

No credential is written here: ``invocation.json`` holds what slice.py's holds (no environment), and nothing else in a sample
folder is read from the host's environment.
"""
from __future__ import annotations

import ast
import fcntl
import json
import os
import shutil
import stat
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
HARNESS = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HARNESS))
import stage_build as sb  # noqa: E402  (also puts the harness and skills/shiploop/scripts on sys.path)
import stage_oracle  # noqa: E402
import hosts  # noqa: E402
import lifecycle  # noqa: E402
import listeners  # noqa: E402
import overlay as overlays  # noqa: E402
import packets  # noqa: E402
import run  # noqa: E402
import sessionlog  # noqa: E402
import slice as step_slice  # noqa: E402
import shiploop_navigator as navigator  # noqa: E402

EXPORT, SEED_EXPORT = "export", "seed-export"
RESULT, INVOCATION, DRIVE, ERROR = "stage-result.json", "invocation.json", "drive.json", "error.txt"
EXPORT_ERROR = "export-error.txt"
STATUS_COMPLETE = "stage-complete"  # a session ended by the stop (or by itself) with the seeded action accepted
RESUME_MIN_SECONDS = 60  # a session that ended is resumed only with more than this left of the timeout (as slice.py)
LS_FILES_SECONDS = 120
GIT_SHOW_SECONDS = 60
# The stop waits for the accepting command to finish (SETTLE_SECONDS at most): ``accept_effects`` saves the state first and then
# runs the lint finish, the commits and the knowledge close under the run lock, and the export must hold what they wrote.
SETTLE_SECONDS = 120
SETTLE_POLL = 0.2
# run.launch can be held up by a process the host left in a session of its own that keeps the host's output open (it cannot be
# ended by the group kill): drive abandons the launch this long after the deadline, or after the stop (the stop at acceptance,
# or an operator's stop first seen). The wait for the accepting command (SETTLE_SECONDS) runs inside run.launch's poll, which
# cannot look at the deadline meanwhile, so the watchdog's clock must outlast it: the deadline plus the whole wait and a minute.
WATCHDOG_SECONDS = SETTLE_SECONDS + 60
STOP_GRACE_SECONDS = 30
# What an export never holds: version-control metadata, ShipLoop's run evidence in the checkout, compiled files.
EVIDENCE = (".git", ".shiploop-improve", ".shiploop-runs")
IDENTITY = ("scenario", "stage", "sample", "host", "backend", "model", "effort", "delegation", "plugin", "versions",
            "local_head", "ref", "overlay", "seeded", "action_id")
SEAM = "accept_effects"
SCRIPTS = Path("skills") / "shiploop" / "scripts"
NAVIGATOR = "shiploop_navigator.py"


class SampleError(ValueError):
    """A sample folder that cannot be graded (no invocation, a scenario that is not the one it ran); the message says why."""


class SnapshotError(RuntimeError):
    """A worktree that cannot be exported; the message says why."""


class SampleStopped(RuntimeError):
    """A sample that an operator ended (the ``stop`` file, or SIGTERM or SIGHUP to the harness) before the stop at acceptance:
    nothing was measured, so it is not graded and the report counts it as not run."""


# ---------------------------------------------------------------------------------------------------------------- the stop

def accepted_reached(state: dict | None, action_id: str) -> bool:
    """Whether the host is done with the seeded action ``action_id``: it has an accepted row in ``history`` (any outcome), or
    the run is parked at its Improve stage (``active_improve.action_id``), or the run is no longer active (blocked, paused,
    halted, done). False for a state that could not be read: the next poll reads it again."""
    if not isinstance(state, dict):
        return False
    if state.get("status") != "active":
        return True
    if any(isinstance(row, dict) and row.get("action") == action_id for row in state.get("history") or []):
        return True
    child = state.get("active_improve")
    return isinstance(child, dict) and child.get("action_id") == action_id


def seeded_result(state: dict | None, action_id: str) -> tuple[dict | None, str | None]:
    """(the seeded action's result, where it is from): ``accepted`` is state ``accepted[action_id]``, ``parked`` the producer's
    ``active_improve.seed_result`` while the run waits at that action's Improve stage; (None, None) when it is neither."""
    if not isinstance(state, dict):
        return None, None
    accepted = (state.get("accepted") or {}).get(action_id)
    if isinstance(accepted, dict):
        return accepted, "accepted"
    child = state.get("active_improve")
    if isinstance(child, dict) and child.get("action_id") == action_id and isinstance(child.get("seed_result"), dict):
        return child["seed_result"], "parked"
    return None, None


# ----------------------------------------------------------------------------------------------------------------- the refusals

def seam_gap(scripts: Path) -> str:
    """Why the ShipLoop scripts folder ``scripts`` cannot build a scenario, or "": its navigator has no ``accept_effects``, the
    engine's one function for what happens after a gate passes (a scenario is built through it, stage_build.SEAM_SEED_SCRIPT)."""
    path = Path(scripts) / NAVIGATOR
    try:
        tree = ast.parse(path.read_text())
    except (OSError, SyntaxError, ValueError) as error:
        return f"the navigator {path} cannot be read ({type(error).__name__}), so its seed seam {SEAM} cannot be found"
    if any(isinstance(node, ast.FunctionDef) and node.name == SEAM for node in tree.body):
        return ""
    return (f"the navigator {path} has no {SEAM}, the seed seam a stage scenario is built through (it came with step 1 of "
            "docs/plans/shiploop-stage-suite.md); use a plugin or ref that has it")


def ref_seam_gap(ref: str) -> str:
    """``seam_gap`` for a git ref, read from the ref's navigator with ``git show`` and nothing built; SystemExit for a ref git does
    not know (overlay.resolve_ref)."""
    commit = overlays.resolve_ref(ref)
    try:
        done = subprocess.run(["git", "-C", str(overlays.ROOT), "show", f"{commit}:{(SCRIPTS / NAVIGATOR).as_posix()}"],
                              capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=GIT_SHOW_SECONDS)
    except (OSError, subprocess.SubprocessError) as error:
        return f"ref {ref} ({commit[:12]}): git show of its navigator failed ({type(error).__name__}), so its seed seam {SEAM} cannot be found"
    if done.returncode:
        return f"ref {ref} ({commit[:12]}) has no {(SCRIPTS / NAVIGATOR).as_posix()}: {(done.stderr or '').strip()[-200:]}"
    try:
        tree = ast.parse(done.stdout)
    except (SyntaxError, ValueError):
        return f"the navigator of ref {ref} ({commit[:12]}) does not parse, so its seed seam {SEAM} cannot be found"
    if any(isinstance(node, ast.FunctionDef) and node.name == SEAM for node in tree.body):
        return ""
    return (f"ref {ref} ({commit[:12]}) has no {SEAM} in its navigator, the seed seam a stage scenario is built through (it "
            "came with step 1 of docs/plans/shiploop-stage-suite.md); use a ref that has it")


def host_gap(host: Any, model: str | None, max_budget_usd: float | None = None) -> str:
    """Why a driver cannot start a sample, or "": the run.py/slice.py refusals, in one place for the command line and for
    ``run_sample``. A host on Ollama needs the server to answer and to list the model, and takes no spend cap."""
    if getattr(host, "backend", None) == "ollama":
        if max_budget_usd:
            return ("--max-budget-usd is not with --backend ollama: Claude Code prices the tokens at Anthropic's rates, so the "
                    "cap would stop the sample on a figure that is not its cost")
        if why := hosts.ollama_ready(model or host.model):
            return f"--backend ollama: {why}"
    return ""


# ----------------------------------------------------------------------------------------------------------------- the snapshot

def _listed(worktree: Path) -> list[str]:
    """The files git knows in ``worktree``: tracked and untracked, not ignored. SnapshotError when git cannot say."""
    env = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}
    try:
        done = subprocess.run(["git", "-C", str(worktree), "-c", "core.fsmonitor=false", "ls-files", "-z", "--cached", "--others",
                               "--exclude-standard"], capture_output=True, env=env, stdin=subprocess.DEVNULL,
                              timeout=LS_FILES_SECONDS)
    except (OSError, subprocess.SubprocessError) as error:
        raise SnapshotError(f"git ls-files in {worktree} failed: {type(error).__name__}") from error
    if done.returncode:
        raise SnapshotError(f"git ls-files in {worktree} exited {done.returncode}: {done.stderr.decode(errors='replace')[-300:]}")
    return sorted({os.fsdecode(name) for name in done.stdout.split(b"\0") if name})


def snapshot(worktree: Path, target: Path) -> dict:
    """Export the execution checkout ``worktree`` into the new folder ``target``: the tracked and untracked files that git does
    not ignore, without ``.git``, ShipLoop's run evidence (``.shiploop-improve/``) or compiled files. A symlink is copied as a
    link and never followed; a file below a path that is a link (or no longer a folder) is left out, so nothing outside the
    worktree is read. A tracked file the host deleted is absent. Written beside ``target`` and renamed into place, so a failed
    export leaves no ``target``. Returns ``{files, links, bytes, skipped}`` (``skipped``: the paths left out below a link)."""
    worktree, target = Path(worktree), Path(target)
    if not worktree.is_dir():
        raise SnapshotError(f"{worktree} is not a folder")
    if target.exists() or target.is_symlink():
        raise FileExistsError(f"{target} already exists: an export is written once")
    partial = target.with_name(target.name + ".partial")
    if partial.exists() or partial.is_symlink():
        shutil.rmtree(partial, ignore_errors=True)
    partial.mkdir(parents=True)
    counts = {"files": 0, "links": 0, "bytes": 0, "skipped": []}
    try:
        for rel in _listed(worktree):
            parts = rel.split("/")
            if parts[0] in EVIDENCE or "__pycache__" in parts or rel.endswith(".pyc") or ".." in parts or rel.startswith("/"):
                continue
            here, below = worktree, False
            for part in parts[:-1]:
                here = here / part
                if here.is_symlink() or not here.is_dir():
                    below = True
                    break
            if below:
                counts["skipped"].append(rel)
                continue
            source, goal = worktree / rel, partial / rel
            try:
                mode = os.lstat(source).st_mode
            except FileNotFoundError:
                continue  # tracked, and deleted in the working tree
            if stat.S_ISLNK(mode):
                goal.parent.mkdir(parents=True, exist_ok=True)
                os.symlink(os.readlink(source), goal)
                counts["links"] += 1
            elif stat.S_ISREG(mode):
                goal.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, goal, follow_symlinks=False)
                counts["files"] += 1
                counts["bytes"] += os.lstat(goal).st_size
        os.rename(partial, target)
    except OSError as error:
        shutil.rmtree(partial, ignore_errors=True)
        raise SnapshotError(f"exporting {worktree} failed: {type(error).__name__}: {error}") from error
    except BaseException:
        shutil.rmtree(partial, ignore_errors=True)
        raise
    return counts


# ------------------------------------------------------------------------------------------------------------------- the drive

def run_lock_free(run_dir: Path) -> bool:
    """Whether no ShipLoop command holds the run lock of ``run_dir`` (the flock ``shiploop`` takes around the dispatch of a
    command: the save and ``accept_effects``, the post-save effects included). It does not cover what a command does after it
    lets the lock go (its trace row, the start of the progress observer). True when there is no lock file or it cannot be
    opened (nothing can be told). The probe takes the lock without waiting and drops it at once; it never creates the file."""
    try:
        descriptor = os.open(Path(run_dir) / ".lock", os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    except OSError:
        return True
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        return False
    except OSError:
        return True
    else:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        return True
    finally:
        os.close(descriptor)


def told_to_end(out: Path) -> bool:
    """Whether an operator ended the run: a SIGTERM or SIGHUP to the harness (run.TERMINATION) or the stop file in ``out``."""
    return run.TERMINATION.is_set() or (Path(out) / "stop").exists()


def settle(run_dir: Path, out: Path, seconds: float | None = None) -> dict:
    """Wait for the command that accepted the seeded action to finish before the host is ended. ``accept_effects`` saves the
    state first and only then runs the lint finish, the two commits, the knowledge close and the iteration record, all inside
    the command's dispatch under the run lock; ending the host between the save and the end of those would leave the export
    without effects the engine would have produced, or half done. What is waited for is that dispatch; the command's trace row
    and the start of the progress observer come after the lock is let go and are not waited for. Returns ``{waited, settled,
    why}``: ``settled`` is False when the lock was still held after ``seconds`` (default SETTLE_SECONDS) or the harness was told
    to end (``told_to_end``), and ``why`` says which."""
    limit = SETTLE_SECONDS if seconds is None else seconds
    started = time.monotonic()
    while True:
        waited = round(time.monotonic() - started, 1)
        if told_to_end(out):  # also with the lock free: a SIGTERM's handler kills the host, and that lets the lock go
            return {"waited": waited, "settled": False, "why": "the run was stopped"}
        if run_lock_free(run_dir):
            return {"waited": waited, "settled": True, "why": None}
        if time.monotonic() - started >= limit:
            return {"waited": waited, "settled": False, "why": f"a ShipLoop command still held the run lock after {limit:g} s"}
        time.sleep(SETTLE_POLL)


def _bounded_launch(launch, timeout: float, stopped: list, out: Path | None = None) -> dict:
    """``launch()`` (run.launch) on a worker thread, abandoned when it is held up. run.launch ends the host's group and then waits
    for the host's output to close; a process the host started in a session of its own keeps it open and the group kill cannot
    reach it, so the launch can outlast ``timeout`` by as long as that process lives. This returns the session's own result when
    it ends, else a result with ``abandoned`` True and the status ``interrupted`` (the stop at acceptance was asked: ``stopped``
    holds the time of that), ``stopped`` (an operator's stop was first seen: a SIGTERM or SIGHUP, or the stop file in ``out``) or
    ``timeout``. It is abandoned STOP_GRACE_SECONDS after the stop at acceptance or the operator's stop, whichever was first, and
    WATCHDOG_SECONDS after the deadline otherwise, and the host's group is ended again. The process that held it up is left
    running: it is in no group of ours."""
    box: dict = {}

    def target() -> None:
        try:
            box["process"] = launch()
        except BaseException as error:  # noqa: BLE001 - re-raised below, on the caller's thread
            box["error"] = error

    worker = threading.Thread(target=target, daemon=True, name="stage-live-launch")
    began = time.monotonic()
    worker.start()
    limit = began + timeout + WATCHDOG_SECONDS
    told_at = None  # when an operator's stop was first seen
    while worker.is_alive():
        worker.join(0.25)
        now = time.monotonic()
        if told_at is None and out is not None and told_to_end(out):
            told_at = now
        since = min((moment for moment in (stopped[0] if stopped else None, told_at) if moment is not None), default=None)
        if worker.is_alive() and (now > limit or (since is not None and now - since > STOP_GRACE_SECONDS)):
            run.end_live_hosts(worker.ident, wait=2.0)
            worker.join(2.0)
            if worker.is_alive():
                return {"status": "interrupted" if stopped else "stopped" if told_at is not None else "timeout", "returncode": None,
                        "elapsed_seconds": round(now - began, 1), "stop": None, "abandoned": True}
    if "error" in box:
        raise box["error"]
    return box["process"]


def drive(argv: list[str], *, work: Path, out: Path, env: dict, run_dir: Path, action_id: str, timeout: float, watch: bool = False,
          translate=None, host_name: str = "host", model: str | None = None, first: bool = True,
          resumed_session: str | None = None, told: dict | None = None) -> dict:
    """One host session that the stop at acceptance ends. Its status is ``stage-complete`` when ``accepted_reached`` ended it, or
    when the session ended by itself with the seeded action already accepted; otherwise run.launch's own (``exited``, ``failed``,
    ``timeout``, ``stopped``). Each poll (every run.POLL_SECONDS) archives the packets ShipLoop wrote (packets.archive_packets),
    as slice.drive does, and the session is recorded in sessions.jsonl before the host starts and after it ends. When the stop
    fires, ``settle`` first waits for the accepting command to finish (the result's ``settle``); an operator's stop that arrives
    during that wait is not a stop at acceptance: ``stop_when`` says no and run.launch reports ``stopped`` (nothing was finished).
    A launch that a process outside the host's group holds up is abandoned (``_bounded_launch``; the result's ``abandoned``)."""
    settled: list = []
    stopped: list = []

    def stop_when() -> bool:
        packets.archive_packets(run_dir, out)
        if not accepted_reached(step_slice.read_state(run_dir), action_id):
            return False
        settled.append(settle(run_dir, out))
        if told_to_end(out):
            # The operator ended the run during the wait (a SIGTERM's handler kills the host, which lets the lock go, so the wait
            # may even read as settled): the effects are not known to be whole. Not a stop at acceptance; run.launch reads "stopped".
            return False
        packets.archive_packets(run_dir, out)
        stopped.append(time.monotonic())
        return True

    started: list = []

    def begin(line: int) -> None:
        started.append(sessionlog.start(out, kind="first" if first else "continued", reason="stage" if first else "resume-loop",
                                        host=host_name, model=model, events_line=line, told=told, resumed_session=resumed_session))

    process = None
    try:
        process = _bounded_launch(lambda: run.launch(argv, work, out, env, timeout, watch, first=first, fresh=False, translate=translate,
                                                     stop_when=stop_when, stop_file=out / "stop", before_start=begin),
                                  timeout, stopped, out)
    finally:
        if started:
            sessionlog.end(out, started[0], events_line=run.events_line_count(out / "events.jsonl", repair=False),
                           status=(process or {}).get("status", "crashed"), returncode=(process or {}).get("returncode"),
                           engine=None)
    packets.archive_packets(run_dir, out)
    process.pop("left_behind", None)
    if settled:
        process["settle"] = settled[-1]
    if process["status"] == "interrupted" or (process["status"] == "exited"
                                              and accepted_reached(step_slice.read_state(run_dir), action_id)):
        process["status"] = STATUS_COMPLETE
    return process


# ---------------------------------------------------------------------------------------------------------------- the bundle

def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError) as error:
        raise SampleError(f"{path} cannot be read ({type(error).__name__}): a sample folder holds it") from error


def _run_dir(out: Path, invocation: dict) -> Path:
    """The sample's run directory: where stage_build lays it under ``out`` (so a copied folder still grades), else where
    invocation.json says it was."""
    here = out / ".shiploop-runs" / "seed" / "run"
    if here.is_dir():
        return here
    return Path(((invocation.get("seeded") or {}).get("run_dir")) or here)


def _first_head(run_dir: Path, trace: list | None, action_id: str) -> str | None:
    """What ``shiploop next`` first printed for the action: the trace's first ``packet`` row for it, read from the kept copy of
    the printed head (``head_file``, kept when the print was not the whole packet) or, when the print was the whole packet, of
    the packet text (``file``); both are packets/sent/<sha>.md. None when the run kept none."""
    for row in trace or []:
        kept = (row.get("head_file") or row.get("file")) if isinstance(row, dict) else None
        if isinstance(row, dict) and row.get("kind") == "packet" and row.get("action") == action_id and isinstance(kept, str):
            try:
                path = run_dir / kept
                if run_dir.resolve() in path.resolve().parents:
                    return path.read_text(errors="replace")
            except OSError:
                continue
    return None


def _first_packet(out: Path, action_id: str) -> str | None:
    """The packet file of the seeded action as the model first saw it: the first copy packet-archive/ kept."""
    kept = sorted((out / packets.ARCHIVE / action_id).glob("*.md")) if (out / packets.ARCHIVE / action_id).is_dir() else []
    for path in kept[:1]:
        try:
            return path.read_text(errors="replace")
        except OSError:
            return None
    return None


def _collect(sc: sb.Scenario, out: Path) -> tuple[stage_oracle.Bundle, dict | None, str, dict, str | None]:
    out = Path(out)
    invocation = _read_json(out / INVOCATION)
    if not isinstance(invocation, dict) or invocation.get("scenario") != sc.id:
        raise SampleError(f"{out} is a sample of {invocation.get('scenario') if isinstance(invocation, dict) else None!r}, "
                          f"not of {sc.id}")
    action_id = invocation.get("action_id")
    if not isinstance(action_id, str) or not action_id:
        raise SampleError(f"{out / INVOCATION} names no seeded action")
    run_dir = _run_dir(out, invocation)
    state = step_slice.read_state(run_dir) if run_dir.is_dir() else None
    result, source = seeded_result(state, action_id)
    trace = sb._trace(run_dir) if run_dir.is_dir() else None
    stage = None
    if state is not None:
        try:
            stage = navigator.current_stage(state)
        except Exception:  # noqa: BLE001 - an unreadable cursor is a missing fact, not a crash of the grade
            stage = None
    bundle = stage_oracle.Bundle(
        result=result, tree=out / EXPORT if (out / EXPORT).is_dir() else None,
        seed_tree=out / SEED_EXPORT if (out / SEED_EXPORT).is_dir() else None, run_dir=run_dir if run_dir.is_dir() else None,
        trace=trace, packet=_first_packet(out, action_id), packet_head=_first_head(run_dir, trace, action_id), issued=True,
        settled=False, current_stage=stage, scenario_dir=sc.dir)
    return bundle, state, action_id, invocation, source


def collect_bundle(sc: sb.Scenario, out: Path) -> stage_oracle.Bundle:
    """The oracle's bundle for the sample in ``out``, rebuilt from the files under it alone (no host and no ShipLoop command):
    ``result`` the seeded action's accepted result (state.md ``accepted``) or, parked at its Improve stage, the producer's
    ``seed_result``; ``tree`` the end export and ``seed_tree`` the seed export (None when a folder is missing, which fails the
    checks that read it); ``run_dir``; the trace rows; ``packet`` the first archived copy of the seeded action's packet file and
    ``packet_head`` the first print of it the trace kept (None if none); ``issued`` True and ``settled`` False;
    ``current_stage`` from the state. SampleError for a folder that is not a sample of ``sc``."""
    return _collect(sc, out)[0]


# ------------------------------------------------------------------------------------------------------------------ the grade

def _sessions(out: Path, reached: bool) -> list[dict]:
    """The host sessions of the sample, from sessions.jsonl alone: n, kind, reason, status and seconds. A session ended by the
    stop reads ``stage-complete`` (run.launch's ``interrupted`` is only our stop's), and so does the last one that ended by
    itself once the action was accepted; a session with no end row (the harness died with it) reads ``unfinished``."""
    rows = sessionlog.read(out) or []
    found = []
    for index, row in enumerate(rows):
        end = row.get("end") or {}
        raw = end.get("status") or "unfinished"
        if raw == "interrupted" or (raw == "exited" and reached and index == len(rows) - 1):
            raw = STATUS_COMPLETE
        found.append({"n": row.get("n"), "kind": row.get("kind"), "reason": row.get("reason"), "status": raw,
                      "returncode": end.get("returncode"),
                      "seconds": round(end["t"] - row["t"], 1) if isinstance(end.get("t"), (int, float)) and isinstance(row.get("t"), (int, float)) else None})
    return found


def overshoot(state: dict | None, stage: str, action_id: str) -> list[str]:
    """The stages the host went on to after the seeded action: the accepted results for a stage later than ``stage``
    (slice.overshoot_after's rule) and every history row after the seeded action's own row, whatever its stage, so a host that is
    sent back and redoes an earlier stage before it is ended is seen too. Stage names, in the order accepted, once each."""
    if not isinstance(state, dict):
        return []
    history = [row for row in state.get("history") or [] if isinstance(row, dict)]
    own = next((index for index, row in enumerate(history) if row.get("action") == action_id), None)
    later = set(step_slice.overshoot_after(state, stage))
    found = [row.get("stage") for index, row in enumerate(history)
             if row.get("stage") in later or (own is not None and index > own)]
    return list(dict.fromkeys(name for name in found if isinstance(name, str)))


def _write(path: Path, data: dict) -> None:
    """Write JSON beside ``path`` and move it into place, so a reader sees the old file or the whole new one."""
    partial = path.with_name(path.name + ".partial")
    partial.write_text(json.dumps(data, indent=2) + "\n")
    os.replace(partial, path)


def _unfinished(out: Path, regraded: bool) -> str:
    """Why the folder ``out`` holds no sample that can be graded, or "": it was not run to the end. Three cases. error.txt is
    there and neither a result nor an export is (the sample could not be run, or an operator ended it). No export, no
    export-error.txt and no result, in a folder that has an invocation (a sample still running, or whose harness was killed
    before it exported: SIGKILL leaves no error.txt). Its ``.harness-lock`` is held by a harness that is still running it (only
    a regrade asks: the sample's own first grade runs under its own lock)."""
    if (out / ERROR).is_file() and not (out / RESULT).exists() and not (out / EXPORT).is_dir():
        return (f"{out} was not run to the end ({' '.join((out / ERROR).read_text(errors='replace').split())[:300]}): "
                "it holds no export, so there is nothing to grade")
    if ((out / INVOCATION).is_file() and not (out / RESULT).exists() and not (out / EXPORT).is_dir()
            and not (out / EXPORT_ERROR).exists()):
        return (f"{out} has no export, no {EXPORT_ERROR} and no {RESULT}: the sample is still running, or its harness was killed "
                "before it exported, so there is nothing to grade")
    if regraded and listeners.case_alive(out):
        return f"{out} is held by a harness that is still running the sample (its {listeners.LOCK_NAME} is locked): wait for it to end"
    return ""


def grade_sample(sc: sb.Scenario, out: Path, *, regraded: bool = True) -> dict:
    """Grade the sample in ``out`` from its files and (re)write ``stage-result.json``; the host sessions and the run are not
    touched. Returns the document. See the module docstring for the verdicts; ``regraded`` marks a later grade (``run_sample``
    passes False for the first). SampleError for a folder that was not run to the end (``_unfinished``)."""
    out = Path(out)
    if why := _unfinished(out, regraded):
        raise SampleError(why)
    bundle, state, action_id, invocation, source = _collect(sc, out)
    planted = [row["id"] for row in sc.data.get("planted", [])]
    controls = [row["id"] for row in sc.data.get("controls", [])]
    results = stage_oracle.run_checks(sc.data.get("oracle", []), bundle)
    found = stage_oracle.verdict(planted, controls, results)
    accepted = bundle.result is not None
    caught = {ident: accepted and found["caught"][ident] is True for ident in planted}
    held = {ident: accepted and found["held"][ident] is True for ident in controls}
    reached = accepted_reached(state, action_id)
    sessions = _sessions(out, reached)
    over = overshoot(state, sb.base_stage(sc.stage), action_id)
    verdicts = {"process": bool(sessions) and sessions[-1]["status"] == STATUS_COMPLETE, "accepted": accepted,
                "no_overshoot": not over, "oracle": accepted and bool(found["pass"])}
    total = len(caught) + len(held)
    hits = sum(caught.values()) + sum(held.values())
    drive_record = {}
    if (out / DRIVE).is_file():
        loaded = _read_json(out / DRIVE)
        drive_record = loaded if isinstance(loaded, dict) else {}
    document = {
        **{key: invocation.get(key) for key in IDENTITY}, "output": str(out), "regraded": regraded,
        "sessions": sessions, "resume_stop": drive_record.get("resume_stop"), "resumes": drive_record.get("resumes", 0),
        "settles": drive_record.get("settles", []), "abandoned": bool(drive_record.get("abandoned")),
        "verdicts": verdicts, "caught": caught, "held": held, "value": (hits / total) if total else (1.0 if verdicts["oracle"] else 0.0),
        "outcome": (bundle.result or {}).get("outcome"), "result_source": source, "overshoot": over,
        "run_status": (state or {}).get("status"), "stage_at_stop": bundle.current_stage,
        "tree": bundle.tree is not None and bundle.seed_tree is not None,
        "checks": [{"proves": row["proves"], "kind": row["kind"], "pass": row["pass"], "detail": row["detail"]} for row in results],
        "unproved_failures": found["unproved_failures"],
    }
    document["pass"] = all(verdicts.values()) and all(caught.values()) and all(held.values())
    _write(out / RESULT, document)
    return document


# ----------------------------------------------------------------------------------------------------------------- the sample

def _fail(out: Path, error: BaseException) -> None:
    """Keep why a sample could not be run (a sample with no stage-result.json is one the report counts as not run)."""
    text = error.code if isinstance(error, SystemExit) and not isinstance(error.code, int) else f"{type(error).__name__}: {error}"
    try:
        (out / ERROR).write_text(" ".join(str(text).split())[:2000] + "\n")
    except OSError:
        pass


def end_recorded_hosts(out: Path) -> dict:
    """End the host groups a sample's own ledger (``resources.jsonl``, written by run.launch) records and that are still alive,
    each only while its leader is the process that was recorded (lifecycle.cleanup). For the harness that ran the sample having
    been killed: the host runs in a session of its own and a signal to the harness does not reach it. Never raises; returns
    lifecycle.cleanup's record, or ``{observed: False, reason}``."""
    try:
        return lifecycle.cleanup(Path(out))
    except (OSError, ValueError, SystemExit, listeners.Unobserved) as error:
        return {"observed": False, "reason": f"{type(error).__name__}: {error}"}


def run_sample(sc: sb.Scenario, out: Path, *, host: Any, model: str | None = None, effort: str | None = None,
               plugin_dir: Path | None = None, ref: str | None = None, overlay: Path | None = None,
               timeout: float | None = None, permission_mode: str = "auto", max_turns: int | None = None,
               max_budget_usd: float | None = None, quiet: bool = True, sample: int | None = None) -> dict:
    """One live sample of scenario ``sc`` in the new folder ``out``: build the scenario, start the host on its one packet, end it
    at acceptance, export the tree, grade (``grade_sample``). ``host`` is a hosts.Host or anything with its interface (a test
    passes a fake): ``name``, ``model``, ``effort``, ``skill``, ``resumable``, ``marketplace``, ``env``, ``invoke``, ``argv``,
    ``install_plugin``, ``plugin_cli``, ``translator``, and ``backend`` for the Ollama refusal. The plugin is ``plugin_dir``, else
    the build of ``ref`` (a read-only temporary worktree), else this checkout's build; ``overlay`` is applied to that build copy.

    Refused before anything is started or written (SystemExit): ``plugin_dir`` with ``ref``/``overlay``; a host that is not
    ready (``host_gap``); a ``ref`` or plugin whose navigator has no ``accept_effects``; a scenario the builder cannot build, or
    one the engine settles by script (no packet is issued, so there is nothing for a model to follow). Nothing outside ``out``
    is written; a host whose plugin install failed (``run.require_installed``) starts nothing. The process groups the ledger
    records and ShipLoop's detached progress observer are ended when the host is done, before the tree is exported
    (``end_recorded_hosts``), on the path where nothing went wrong and on the way out of an error.
    """
    if plugin_dir is not None and (ref or overlay):
        raise SystemExit("--ref and --overlay build their own plugin; they do not take a plugin_dir. Nothing was started.")
    model = model or host.model
    effort = effort or host.effort
    if why := host_gap(host, model, max_budget_usd):
        raise SystemExit(f"{why}. Nothing was started.")
    if ref and (why := ref_seam_gap(ref)):
        raise SystemExit(f"{why}. Nothing was started.")
    host.model = model  # the model the host's environment routes to (the Claude host on Ollama names it there)
    out = run.new_output_dir(Path(out), f"stage-{sc.stage}-{sc.name}")
    held: list = []
    try:
        if (lock := listeners.hold_case(out)) is not None:
            held.append(lock)
        return _run_sample(sc, out, host=host, model=model, effort=effort, plugin_dir=plugin_dir, ref=ref, overlay=overlay,
                           timeout=timeout, permission_mode=permission_mode, max_turns=max_turns, max_budget_usd=max_budget_usd,
                           quiet=quiet, sample=sample if sample is not None else (int(out.name) if out.name.isdigit() else 1))
    except BaseException as error:
        _fail(out, error)
        raise
    finally:
        for handle in held:
            handle.close()


def _run_sample(sc: sb.Scenario, out: Path, *, host: Any, model: str, effort: str | None, plugin_dir: Path | None,
                ref: str | None, overlay: Path | None, timeout: float | None, permission_mode: str, max_turns: int | None,
                max_budget_usd: float | None, quiet: bool, sample: int) -> dict:
    work = out / "work"
    work.mkdir()
    env = host.env(out / "home")
    plugin_dir = (Path(plugin_dir).expanduser().resolve() if plugin_dir else overlays.build_ref(ref, out) if ref
                  else run.build_candidate(out))
    applied = overlays.apply_to_plugin(Path(overlay).resolve(), plugin_dir) if overlay else None
    if why := seam_gap(plugin_dir / SCRIPTS):
        raise SystemExit(f"{why}. Nothing was started.")
    plugin = host.install_plugin(env, plugin_dir)
    run.require_installed(plugin, plugin_dir)  # a build the host failed to install must not run the model without ShipLoop
    cli = host.plugin_cli(out / "home") or run.shiploop_cli(plugin_dir)
    if why := seam_gap(Path(cli).parent):
        raise SystemExit(f"{why}. Nothing was started.")
    built = sb.build(sc, out, cli=cli)
    if built.settled:
        raise SystemExit(f"{sc.id}: the engine settled {sc.stage} by script during the seed, so no packet is issued and a model "
                         "has nothing to follow. Nothing was started.")
    action_id = built.seeded["action"]
    seed_counts = snapshot(built.worktree, out / SEED_EXPORT)  # before the host starts: what the stage starts from
    case = sb.step_cases()[sc.data["request_from"]]
    delegation = (sc.data.get("options") or {}).get("delegation", "inline")
    run_dir = Path(built.seeded["run_dir"])
    opening = host.invoke(host.skill, run.seed_prompt(cli, str(run_dir), case["prompt"], delegation, sb.base_stage(sc.stage)))
    common = dict(cwd=work, model=model, effort=effort, permission_mode=permission_mode, max_turns=max_turns,
                  max_budget_usd=max_budget_usd, plugin_dir=None if host.marketplace else plugin_dir)
    backend = getattr(host, "backend", None)
    invocation = {"scenario": sc.id, "stage": sc.stage, "kind": "stage-sample", "sample": sample, "host": host.name,
                  "backend": backend, "model": model, "effort": effort, "delegation": delegation, "plugin_dir": str(plugin_dir),
                  "plugin": plugin, "versions": run.installed_versions(plugin_dir), "local_head": run.git("rev-parse", "HEAD").strip(),
                  "seeded": built.seeded, "action_id": action_id, "seed_export": seed_counts, "ref": ref, "overlay": applied,
                  "permission_mode": permission_mode, "timeout": timeout}
    (out / INVOCATION).write_text(json.dumps(invocation, indent=2) + "\n")
    (out / "prompt.txt").write_text(case["prompt"] + "\n")
    if not quiet:
        print(f"stage sample {sc.id} #{sample} host={host.name}" + (f" backend={backend}" if backend else "")
              + f" model={model}\n  output {out}\n  the host starts at {built.stage}, action {action_id}", flush=True)

    try:
        deadline = time.monotonic() + (timeout or float("inf"))  # active time, as in run.py: sleep spends none of it
        session = dict(work=work, out=out, env=env, run_dir=run_dir, action_id=action_id, watch=not quiet, translate=host.translator(),
                       host_name=host.name, model=model)
        process = drive(host.argv(prompt=opening, prompt_file=out / "host-prompt.txt", **common),
                        timeout=timeout or float("inf"), **session)
        resumes, stalled, resume_stop = 0, 0, None
        settles = [process["settle"]] if process.get("settle") else []
        revision = (step_slice.read_state(run_dir) or {}).get("revision")
        while process["status"] == "exited":
            state = step_slice.read_state(run_dir)
            if accepted_reached(state, action_id):
                break
            if not host.resumable:
                resume_stop = "the host cannot be resumed"
            elif (state or {}).get("status") != "active":
                resume_stop = "the run is no longer active"
            elif deadline - time.monotonic() <= RESUME_MIN_SECONDS:
                resume_stop = "the timeout is spent"
            elif stalled >= run.RESUME_STALL:
                resume_stop = f"{stalled} resumed sessions in a row moved ShipLoop nowhere (revision {revision})"
            elif not (session_id := run.last_session_id(out / "events.jsonl")):
                resume_stop = "no host session id to resume"
            if resume_stop:
                break
            resumes += 1
            process = drive(host.argv(prompt=run.resume_prompt(str(run_dir), cli), prompt_file=out / f"resume-{resumes}.txt",
                                      resume=session_id, **common),
                            timeout=deadline - time.monotonic(), first=False, resumed_session=session_id,
                            told=run.resume_told(str(run_dir), cli), **session)
            settles += [process["settle"]] if process.get("settle") else []
            now = (step_slice.read_state(run_dir) or {}).get("revision")
            stalled = stalled + 1 if now == revision else 0
            revision = now
        _write(out / DRIVE, {"resumes": resumes, "resume_stop": resume_stop, "settles": settles,
                             "abandoned": bool(process.get("abandoned"))})
        run.write_transcript(out / "events.jsonl", out / "transcript.md")
    finally:
        # As run.py does before it exports and grades: end the groups the ledger records that are still alive and ShipLoop's
        # progress observer (a `next` with progress on starts one that outlives the host). Never raises.
        if line := lifecycle.cleanup_line(end_recorded_hosts(out)):
            if not quiet:
                print(line, flush=True)
    if process["status"] == "stopped":  # an operator ended it: nothing was measured, so it is not graded (not run)
        cause = run.stop_cause(out / "stop")
        (out / "stop").unlink(missing_ok=True)  # consumed, as run.py's own stop file is
        raise SampleStopped(f"the host was ended before it accepted the seeded action: {cause}")
    try:
        snapshot(built.worktree, out / EXPORT)
    except SnapshotError as error:  # no export: every check that reads the tree fails, and the grade says so
        (out / EXPORT_ERROR).write_text(f"{error}\n")
    result = grade_sample(sc, out, regraded=False)
    if not quiet:
        print(f"stage sample {'PASS' if result['pass'] else 'FAIL'}: "
              + ", ".join(f"{name} {'ok' if value else 'FAIL'}" for name, value in result["verdicts"].items())
              + f"; value {result['value']:.2f}\n  {out / RESULT}", flush=True)
    return result
