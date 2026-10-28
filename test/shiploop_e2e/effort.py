"""The by-stage effort schedule of experiment E-EFF1 (docs/shiploop-effort-by-stage-experiment-plan-2026-10-24.md).

A host session runs at one reasoning effort. To run some packets at another, the harness ends the session at a boundary
and continues in a new one. A position of the run belongs to one class:

  M   a mechanical stage (``MECHANICAL``): the model runs, checks and reports; it writes no product file and no plan
  I2  an Improve child's pass 2 or later (the Until Loop's latest packet is active with action_number >= 2)
  D   every other position, Improve pass 1 included

A schedule names an effort level for each class, ``{"M": "low", "I2": "low", "D": "medium"}``. A boundary is every change
of class, whatever the levels are, so the control schedule (one level named three times) restarts the session at exactly
the positions the treatment schedule does and only the effort flag differs: the pair is blocked on the restart itself.

The class is read from the run's state and the Improve child's latest runtime packet, never from what the model says.
A fact that cannot be read (no state, no packet yet, a half-written file) is *indeterminate*, and an indeterminate
position never ends a session: ``classify`` returns None and the session keeps its class.

    python3 test/shiploop_e2e/run.py --case hello --host grok --effort-schedule treatment.json --baseline <own file>
    python3 test/shiploop_e2e/slice.py --case node-fix-bug --host claude --effort-schedule treatment.json

A resume continues the run's recorded schedule (``effort.json``) and refuses a different one. ``effort.json`` also holds
every launch and every restart, for the analysis that attributes tokens and seconds to a class.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "skills" / "shiploop" / "scripts"))
import shiploop_standalone_improve as standalone  # noqa: E402
import shiploop_store as store  # noqa: E402

CLASSES = ("M", "I2", "D")
# The mechanical stages of the plan (section 3), fixed before any run. Each is an outer or prelude stage whose work is to
# run, check and report; `handoff` authors the final document and stays in D. test/shiploop-e2e-effort.test.py pins this
# list against the stage table.
MECHANICAL = frozenset(("prepare", "system-test", "product-acceptance", "release-check", "release", "release-verify",
                        "operations"))
# The levels each host accepts for its effort flag, from probe P1 (docs/experiments/shiploop-effort-by-stage-20261024/probes).
# Grok refuses any other value; Claude ignores one with a warning and runs at its default, so a typo in a schedule would
# silently run both arms at the default. Codex is not probed: its levels are not checked here.
LEVELS = {"grok": ("xhigh", "high", "medium", "low"), "claude": ("low", "medium", "high", "xhigh", "max")}
# Said to the host session that continues a run after a boundary (run.resume_prompt's `note`). R1: the first session after
# a restart into pass 2 submitted `improve-pass` before writing the pass's review, three times in three cycles, against none
# in a Grok run without restarts. The note is the same for both arms; refusals it does not prevent are attributed
# (docs/experiments/shiploop-effort-by-stage-20261024/run_totals.py, `refusals`).
RESTART_NOTE = ("The test harness ended your session at a settings boundary and continued it; every command you ran before "
                "this point has already taken effect and nothing was undone. Do not repeat a command from before the "
                "restart: take the next step only from the packet that `next` prints.")
RECORD = "effort.json"
SCHEDULE_FILE = "effort-schedule.json"
LOCATE_EVERY = 5.0  # seconds between looks for the run directory, until one is found


class ScheduleError(ValueError):
    """A schedule that cannot be used; its message is the whole explanation."""


def parse_schedule(source: str) -> dict[str, str]:
    """The schedule in `source`, JSON text or the path of a file holding it: exactly the classes M, I2 and D, each a
    non-empty level with no whitespace. Whether a host accepts a level is the host's to say (probe P1), not checked here."""
    text = source if source.lstrip().startswith("{") else None
    if text is None:
        try:
            text = Path(source).expanduser().read_text()
        except OSError as err:
            raise ScheduleError(f"--effort-schedule {source!r}: not JSON text and not a readable file ({err.strerror})") from err
    try:
        found = json.loads(text)
    except ValueError as err:
        raise ScheduleError(f"--effort-schedule: not valid JSON ({err})") from err
    if not isinstance(found, dict) or set(found) != set(CLASSES):
        raise ScheduleError(f"--effort-schedule: name exactly the classes {', '.join(CLASSES)}; got "
                            f"{', '.join(sorted(map(str, found))) if isinstance(found, dict) else type(found).__name__}")
    for name in CLASSES:
        level = found[name]
        if not isinstance(level, str) or not level or level != level.strip() or any(c.isspace() for c in level):
            raise ScheduleError(f"--effort-schedule: class {name} needs a level without spaces, got {level!r}")
    return {name: found[name] for name in CLASSES}


def check_levels(schedule: dict[str, str], host_name: str) -> None:
    """Refuse a schedule that names a level the host does not accept (see LEVELS); a host not in LEVELS is not checked."""
    valid = LEVELS.get(host_name)
    bad = {name: level for name, level in schedule.items() if valid is not None and level not in valid}
    if bad:
        raise ScheduleError(f"--effort-schedule: {host_name} accepts {', '.join(valid)}; got "
                            + ", ".join(f"{name}={level}" for name, level in bad.items()))


def running_pass(child: dict, receipt_of=None) -> tuple[int | None, str]:
    """(the number of the pass the Improve child's loop is on, why), or (None, why) when that is not readable.

    The Until Loop runtime keeps the latest packet of a bound child at ``receipt_path(child)`` (shiploop_standalone_improve):
    status ``active`` and ``progress.action_number`` n mean pass n is running or about to run. A ``complete`` or ``stopped``
    packet means no further pass will run but the child is still bound until the model's own ``complete`` call: the loop is
    closing, which is indeterminate (None), not a class. R1 showed why: a boundary there ended the session before that call,
    and the resumed session re-ran ``improve-pass`` on a loop that had ended (a refusal, in every cycle)."""
    receipt_of = receipt_of or standalone.receipt_path
    try:
        packet = json.loads(Path(receipt_of(child)).read_text())
    except Exception as err:  # noqa: BLE001 - unreadable is indeterminate, never a class
        return None, f"no readable packet ({type(err).__name__})"
    if not isinstance(packet, dict):
        return None, "packet is not an object"
    status = packet.get("status")
    if status in ("complete", "stopped"):
        return None, f"loop {status}: closing"
    number = (packet.get("progress") or {}).get("action_number") if isinstance(packet.get("progress"), dict) else None
    if status == "active" and isinstance(number, int) and not isinstance(number, bool) and number >= 1:
        return number, f"improve pass {number}"
    return None, "packet has no pass number"


def classify(state: dict | None, current_stage, *, receipt_of=None, mechanical=MECHANICAL) -> tuple[str | None, str]:
    """(class, why) of the run's position, or (None, why) when it is indeterminate or the run is not active."""
    if not state or state.get("status") != "active":
        return None, "run not active"
    child = state.get("active_improve")
    if child is not None:
        number, why = running_pass(child, receipt_of)
        if number is None:
            return None, why
        return ("I2" if number >= 2 else "D"), why
    try:
        stage = current_stage(state)
    except Exception as err:  # noqa: BLE001 - an unreadable cursor is not a boundary
        return None, f"no readable stage ({type(err).__name__})"
    return ("M" if stage in mechanical else "D"), f"stage {stage}"


def restart_point(state: dict | None, session_class: str | None, current_stage, **kw) -> dict | None:
    """The boundary to end a session at, or None: the position's class differs from the session's."""
    now, why = classify(state, current_stage, **kw)
    if now is None or session_class is None or now == session_class:
        return None
    try:
        stage = current_stage(state)
    except Exception:  # noqa: BLE001
        stage = None
    return {"from": session_class, "to": now, "stage": stage, "why": why, "revision": (state or {}).get("revision")}


def _write(path: Path, record: dict) -> None:
    """Atomic enough for a record read by the same process family: write beside, then replace."""
    temp = path.with_name(path.name + f".{os.getpid()}.tmp")
    temp.write_text(json.dumps(record, indent=2) + "\n")
    temp.replace(path)


def recorded(out: Path) -> dict | None:
    """The run's effort record, or None when it has none (a run that used no schedule)."""
    try:
        found = json.loads((Path(out) / RECORD).read_text())
    except (OSError, ValueError):
        return None
    return found if isinstance(found, dict) and isinstance(found.get("schedule"), dict) else None


class Planner:
    """One run's schedule in use: the effort a session starts at, and when it must end.

    `locate()` returns the run directory once ShipLoop has made one (None before); `current_stage(state)` is
    metrics.current_stage. `can_resume()` says whether a session ended now could be continued: a Grok session reports its id
    only when a turn ends, so a boundary before that has nothing to resume (R1b: the control run was killed at pass 2 eight
    minutes in and could not be continued). Until it is true no session is ended; the boundary is applied at the next natural
    turn end, when the next launch reads the class again. `receipt_of` and `mechanical` exist for tests."""

    def __init__(self, out: Path, schedule: dict[str, str], *, locate, current_stage, receipt_of=None,
                 mechanical=MECHANICAL, can_resume=None):
        self.out, self.schedule = Path(out), dict(schedule)
        self._locate, self.current_stage = locate, current_stage
        self._receipt_of, self._mechanical, self._can_resume = receipt_of, mechanical, can_resume
        self._run_dir: Path | None = None
        self._asked = 0.0  # when `locate` was last called: it scans the run folder, so not on every 2 s poll
        self.session_class: str | None = None
        self.pending: dict | None = None
        earlier = recorded(self.out)
        if earlier and earlier["schedule"] != self.schedule:
            raise ScheduleError(f"{self.out / RECORD} holds schedule {earlier['schedule']}: a resume continues the run's "
                                f"schedule and cannot change it to {self.schedule}")
        self.record = earlier or {"schedule": self.schedule, "mechanical": sorted(self._mechanical),
                                  "classes": {"M": "mechanical stage", "I2": "Improve pass 2 or later",
                                              "D": "every other position"}, "launches": [], "restarts": []}
        _write(self.out / RECORD, self.record)

    def state(self) -> dict | None:
        """The run's state now, None before it exists or while a write is in flight (the next poll reads it again)."""
        if self._run_dir is None and time.time() - self._asked >= LOCATE_EVERY:
            self._asked = time.time()
            try:
                found = self._locate()
            except Exception:  # noqa: BLE001 - locating is fail-open
                found = None
            self._run_dir = Path(found) if found else None
        if self._run_dir is None:
            return None
        try:
            state = store.read_record(self._run_dir / "state.md")
        except (store.StorageError, OSError):
            return None
        return state if isinstance(state, dict) else None

    def at_launch(self, why: str) -> tuple[str, str]:
        """(class, effort) for the session about to start, and the launch recorded. No state yet, or an indeterminate
        position, starts as D: the first packets of a run are planning."""
        self.consume()  # a boundary that ended the last session is recorded before the next one starts
        state = self.state()
        found, _ = classify(state, self.current_stage, receipt_of=self._receipt_of, mechanical=self._mechanical)
        cls = found or "D"
        self.session_class, self.pending = cls, None
        self.record["launches"].append({"t": round(time.time(), 3), "class": cls, "effort": self.schedule[cls], "why": why})
        _write(self.out / RECORD, self.record)
        return cls, self.schedule[cls]

    def stop_when(self) -> bool:
        """Polled while a session runs: true when the position left the session's class. Keeps the first boundary."""
        if self.pending is not None:
            return True
        if self._can_resume is not None and not self._can_resume():
            return False  # nothing to continue yet: wait for the host's first turn end
        found = restart_point(self.state(), self.session_class, self.current_stage, receipt_of=self._receipt_of,
                              mechanical=self._mechanical)
        if found:
            self.pending = found
            return True
        return False

    def consume(self) -> dict | None:
        """Called after a session ended: the boundary that ended it (recorded, then cleared), or None if none did."""
        point, self.pending = self.pending, None
        if point is None:
            return None
        row = {"n": len(self.record["restarts"]) + 1, "t": round(time.time(), 3), **point,
               "effort_before": self.schedule[point["from"]], "effort_after": self.schedule[point["to"]]}
        self.record["restarts"].append(row)
        _write(self.out / RECORD, self.record)
        return row
