"""Which ShipLoop run an output folder holds: the candidates, the identity the harness recorded, and the one rule that picks.

A model under test sometimes abandons its first run (it pauses it as "replaced by a fresh run") and starts a second, so the
folder holds several. Three readers need the same answer: the verdict (run.grade_shiploop), every measurement that reads the
run's files (metrics.run_dir_of) and the live monitor (progress.py). They all call `choose`, so they cannot disagree.

The rule, first match wins:

1. The run RUN_IDENTITY records, while its state is still there.
2. The only run that was not already in the folder when the invocation started (the `preexisting` digests).
3. Among several, the runs the model did not set aside (SET_ASIDE: paused or halted) are the candidates; a finished or
   blocked run is still in play. One candidate is the run. Several are told apart only by the one the host's commands named
   (`--run-dir`), never by which changed last: two runs in play do not say which one the model means.
4. When every run was set aside, the same naming; else the run whose state.md changed last, only when it changed strictly
   after every other. Equal moments, or a moment that cannot be read, tell nothing apart.

What nothing tells apart is `tied`: no run is chosen and a verdict on the folder fails as ambiguous, never by picking one.
The grader records a choice that holds whatever the runs' statuses become (`bind`: rules 1 and 2, and a naming among runs none
of which was set aside). A choice that follows statuses is made again at every reading: a model can resume the run it paused.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path
from typing import NamedTuple

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "skills/shiploop/scripts"))
import shiploop_store as store

# Which ShipLoop run this output folder's invocations created, written by the harness: the runs that were already there when
# the first invocation started (`preexisting`: a follow-on's copy can bring one along) and, once known, the run itself
# (`run_dir`, with its `basis`). A resume and a regrade read it back, so every invocation grades the same run.
RUN_IDENTITY = "shiploop-run.json"
# A run in one of these statuses is one the model set aside (`pause`, `halt`). `blocked` waits for an answer, `done` is finished.
SET_ASIDE = ("paused", "halted")
# The `--run-dir` a ShipLoop command in the host's event stream named.
RUN_DIR_ARG = re.compile(r"""--run-dir(?:=|\s+)["']?(?P<dir>[^"'\s]+)""")

ONLY_NEW = "the only run that was not there before the invocation"
NAMED = "the run the host's commands named"
ONLY_IN_PLAY = "the only run that was not paused or halted"
CHANGED_LAST = "the run whose state changed last (every run was paused or halted)"


class Choice(NamedTuple):
    runs: list[dict]  # every run state under the folder
    before: dict  # run directory -> state digest, for each run already there when the first invocation started
    mine: list[dict]  # the runs that are this invocation's
    chosen: dict | None  # the run, or None
    basis: str | None  # why it is the run: "recorded", or one of the sentences above
    bind: bool  # whether the choice holds whatever the runs' statuses become, so the grader records it
    tied: list[dict]  # when no run was chosen from several: the ones nothing tells apart
    why: str  # when tied: what was ruled out first, as a phrase that follows "ShipLoop runs under the output directory"


def run_identity(out: Path) -> dict:
    """The identity the harness recorded for an output folder: {} where none is recorded or it cannot be read."""
    try:
        found = json.loads((out / RUN_IDENTITY).read_text())
    except (OSError, ValueError):
        return {}
    return found if isinstance(found, dict) else {}


def shiploop_runs(out: Path) -> list[dict]:
    """Every ShipLoop run state under the output directory, wherever the agent put it: inside the repository
    (work/.shiploop) or in an external workspace root beside it (<out>/.shiploop-runs/<name>/run). The throwaway home/ and
    the plugin build/ are not searched, and a state.md that cannot be read as a run's state is not a run."""
    runs = []
    for state_path in sorted(out.rglob("state.md")):
        relative = state_path.relative_to(out).parts
        if relative[0] in ("home", "build"):
            continue
        try:
            state = store.read_record(state_path)
        except (store.StorageError, OSError, ValueError):
            continue
        if isinstance(state, dict) and "status" in state:
            runs.append({"run_dir": str(state_path.parent), "status": state.get("status"),
                         "stage": state.get("stage"), "revision": state.get("revision"),
                         "report_html": (state_path.parent / "report.html").is_file()})
    return runs


def state_digest(run_dir: str) -> str | None:
    """A run's state.md as it stands: its content digest and modification time (a rewrite with the same bytes is a change)."""
    try:
        path = Path(run_dir) / "state.md"
        return f"{hashlib.sha256(path.read_bytes()).hexdigest()}@{path.stat().st_mtime_ns}"
    except OSError:
        return None


def state_changed(run_dir: str) -> int | None:
    """When a run's state.md last changed, in nanoseconds since the epoch; None where it cannot be read."""
    try:
        return (Path(run_dir) / "state.md").stat().st_mtime_ns
    except OSError:
        return None


def named_run_dirs(out: Path) -> set[str]:
    """The run directories the host's ShipLoop commands named (`--run-dir`), as resolved paths."""
    try:
        text = (out / "events.jsonl").read_text(errors="replace").replace('\\"', '"')
    except OSError:
        return set()
    return {str(Path(found.group("dir")).expanduser().resolve()) for found in RUN_DIR_ARG.finditer(text)}


def choose(out: Path) -> Choice:
    """The run an output folder holds, by the rule in the module docstring. Reads only: nothing is recorded here."""
    runs = shiploop_runs(out)
    identity = run_identity(out)
    before = identity.get("preexisting") if isinstance(identity.get("preexisting"), dict) else {}
    mine = [found for found in runs
            if found["run_dir"] not in before or state_digest(found["run_dir"]) != before[found["run_dir"]]]
    bound = identity.get("run_dir")

    def result(chosen=None, basis=None, bind=False, tied=(), why=""):
        return Choice(runs, before, mine, chosen, basis, bind, list(tied), why)

    # A recorded run whose state is gone is not a choice any more: the rules below pick again (still never a run that was
    # there before the invocation started).
    recorded = next((found for found in mine if found["run_dir"] == bound), None) if bound else None
    if recorded is not None:
        return result(recorded, "recorded", bind=True)
    if len(mine) <= 1:
        return result(mine[0], ONLY_NEW, bind=True) if mine else result()
    in_play = [found for found in mine if found["status"] not in SET_ASIDE]
    pool = in_play or mine
    if len(pool) == 1:
        return result(pool[0], ONLY_IN_PLAY)
    told = named_run_dirs(out) & {found["run_dir"] for found in pool}
    if len(told) == 1:
        return result(next(found for found in pool if found["run_dir"] in told), NAMED, bind=len(in_play) == len(mine))
    if in_play:
        return result(tied=pool, why="" if len(in_play) == len(mine) else " that are not paused or halted")
    moments = [(state_changed(found["run_dir"]), found) for found in mine]
    if any(moment is None for moment, _ in moments):
        return result(tied=mine, why=" that are paused or halted, one of them with a state that cannot be dated")
    latest = max(moment for moment, _ in moments)
    last = [found for moment, found in moments if moment == latest]
    if len(last) == 1:
        return result(last[0], CHANGED_LAST)
    return result(tied=last, why=" that are paused or halted and last changed at the same moment")
