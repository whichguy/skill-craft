#!/usr/bin/env python3
"""What a case's run owns: the leases it takes before a host starts, the process groups it starts, and how it gives them back
(SPEC "The resource lifecycle", build step 7; R19 and R20 of the final verdict).

A run appends what it owns to ``<output>/resources.jsonl`` as it goes, so a harness that is killed still leaves the list: on
2026-10-09 a Grok host worked for 28 minutes after its harness died of a SIGTERM, and ShipLoop's progress observer outlived
two stopped runs (2026-10-18, chess run 5 on 2026-10-24) until it was ended by hand. Stopping and disposing are separate:

* ``cleanup`` stops the recorded groups that are still alive, each only while its leader keeps the creation identity the
  ledger holds (pid, group and ``ps`` start time), never by name. It first adopts ShipLoop's progress observer by the pid its
  own record names. It is idempotent and deletes no file.
* ``dispose`` removes the heavy folders, and only once the evidence is in place: the delivery's identity, the logs and a
  bundle git verifies that holds the delivered head.

A lease (``take``) is an exclusive ``flock`` on a file in one folder for the machine, so two runs never hold one platform or
one fixed port at once, and the kernel gives it back on any death. ``orphans`` and ``disk`` are refusals made before a host
starts; ``contention`` records the live runs on the same host and model, which cannot be leased.

Nothing here is a verdict. A process table that cannot be read raises ``listeners.Unobserved``, which a caller records as
not observed, never as none.

    python3 test/shiploop_e2e/lifecycle.py cleanup <output>
    python3 test/shiploop_e2e/lifecycle.py dispose <output>
"""

from __future__ import annotations

import argparse
import contextlib
import fcntl
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
import environment  # noqa: E402
import listeners  # noqa: E402
import runrecord  # noqa: E402

LEDGER = "resources.jsonl"
LEASES_ENV = "SHIPLOOP_E2E_LEASES"
# Free space a case's run needs on its output's file system. Basis (SPEC): 97 run folders under ~/e2e-runs on 2026-10-26, median
# 22 MB, largest 675 MB (chess run 5b, its throwaway home most of it); this is about three times the largest.
HEADROOM_PER_RUN = 2 * 1024 ** 3
# The folders dispose removes; everything else (the records, the logs, the delivery bundle) stays.
HEAVY = ("work", "home", "marketplace", "build", "quality")
LOGS = ("events.jsonl", "stderr.txt", "timeline.jsonl")
DATA_DIRECTORIES = {"work": "the delivered tree", "home": "the host's throwaway home", "marketplace": "the marketplace install",
                    "build": "the plugin build under test", "platform": "the platform's snapshot and guard logs",
                    "quality": "the delivered-quality copy", "delivery": "the delivery bundle",
                    ".shiploop-runs": "ShipLoop's run folders and worktrees"}
OBSERVER_RECORD = "progress-observer.json"  # shiploop_progress.STATUS: the observer writes its pid and instance id here
# ShipLoop's run directories in an output folder: an external workspace root beside the repository, or inside it.
RUN_DIR_GLOBS = (".shiploop-runs/*/run", "work/.shiploop")
GRACE_SECONDS = listeners.GRACE_SECONDS  # after SIGTERM a group gets this long before SIGKILL
FORCE_SECONDS = listeners.FORCE_SECONDS
POLL_SECONDS = listeners.POLL_SECONDS

_WRITE = threading.Lock()  # suite cases run in threads of one harness; each appends to its own ledger, but one lock is enough


class Refused(SystemExit):
    """A resource conflict found before a host started: nothing was started. A SystemExit, so a run that meets one ends with
    its message, and a suite can catch it and go on with its other cases."""


# ---------------------------------------------------------------- the process table

def _ps(argv: list[str]) -> str:
    """One read-only ps call in the C locale (``lstart`` is then one fixed shape). Raises Unobserved as listeners._run does."""
    try:
        done = subprocess.run(argv, capture_output=True, text=True, timeout=listeners.LSOF_TIMEOUT, stdin=subprocess.DEVNULL,
                              env=dict(os.environ, LC_ALL="C", LANG="C"))
    except FileNotFoundError:
        raise listeners.Unobserved("ps not found") from None
    except subprocess.TimeoutExpired:
        raise listeners.Unobserved(f"ps timed out after {listeners.LSOF_TIMEOUT}s") from None
    except OSError as exc:
        raise listeners.Unobserved(f"ps could not run: {exc}") from None
    if done.returncode not in (0, 1):  # 1: none of the pids asked for exists
        raise listeners.Unobserved(f"ps exited {done.returncode}")
    return done.stdout


def table(pids=None) -> dict[int, dict]:
    """pid -> ``{pid, ppid, pgid, started, command}`` for every process, or for ``pids`` only. ``started`` is ps's ``lstart``
    (``Mon Oct 26 10:49:51 2026``): with the pid and the group it is the creation identity this module compares."""
    pids = sorted(set(pids)) if pids is not None else None
    if pids == []:
        return {}
    text = _ps(["ps", "-ww", "-o", "pid=,ppid=,pgid=,lstart=,command=",
                *(["-p", ",".join(map(str, pids))] if pids else ["-ax"])])
    rows = {}
    for line in text.splitlines():
        parts = line.split(None, 8)
        if len(parts) < 8 or not all(part.isdigit() for part in parts[:3]):
            continue
        pid, ppid, pgid = map(int, parts[:3])
        rows[pid] = {"pid": pid, "ppid": ppid, "pgid": pgid, "started": " ".join(parts[3:8]),
                     "command": parts[8] if len(parts) > 8 else ""}
    return rows


def same_leader(recorded: dict | None, now: dict | None) -> bool:
    """Whether the process ``now`` is the leader the ledger recorded: same pid, group and start time (the command may change
    by exec, so it is not compared)."""
    return bool(recorded and now) and all(recorded.get(key) == now.get(key) for key in ("pid", "pgid", "started"))


# ---------------------------------------------------------------- the ledger

def record(out, kind: str, **fields) -> dict:
    """Append one row to the run's ledger. Raises OSError where it cannot be written; callers that must not fail catch it."""
    row = {"kind": kind, "at": round(time.time(), 3), **fields}
    with _WRITE, open(Path(out) / LEDGER, "a") as handle:
        handle.write(json.dumps(row) + "\n")
    return row


def rows(out) -> list[dict]:
    """The ledger's rows; a line that is not a JSON object (a write cut by a kill) is passed over."""
    try:
        text = (Path(out) / LEDGER).read_text(errors="replace")
    except OSError:
        return []
    found = []
    for line in text.splitlines():
        with contextlib.suppress(ValueError):
            row = json.loads(line)
            if isinstance(row, dict):
                found.append(row)
    return found


def own(out, pid: int, role: str) -> dict | None:
    """Record the group ``pid`` leads, just started for this run, with its leader's creation identity. Never raises: a leader
    ps cannot see is recorded with the reason (cleanup never signals a group without an identity), and a ledger that cannot
    be written returns None."""
    try:
        leader = table([pid]).get(pid)
        reason = None if leader else "ps did not list the leader (it ended at once)"
    except listeners.Unobserved as exc:
        leader, reason = None, str(exc)
    try:
        return record(out, "group", id=f"{pid}@{time.time():.6f}", pgid=pid, role=role, leader=leader,
                      **({"reason": reason} if reason else {}))
    except OSError:
        return None


def ended(out, group: dict | None, how: str, **detail) -> None:
    """Record that a recorded group is over (``how``: why). Never raises."""
    if group:
        with contextlib.suppress(OSError):
            record(out, "ended", id=group["id"], pgid=group["pgid"], role=group.get("role"), how=how, **detail)


def open_groups(out) -> list[dict]:
    """The recorded groups with no ``ended`` row: the ones a cleanup still has to look at."""
    found = rows(out)
    closed = {row.get("id") for row in found if row.get("kind") == "ended"}
    return [row for row in found if row.get("kind") == "group" and row.get("id") not in closed]


class Recorded:
    """The live-group set a phase registers its children in (``run.LIVE_HOST_GROUPS``, so a signal still ends them), that also
    records each group in the run's ledger as it is added and ended. Only ``add`` and ``discard`` are used (quality.start and
    quality.finish)."""

    def __init__(self, groups: set, out, role: str):
        self.groups, self.out, self.role, self.rows = groups, out, role, {}

    def add(self, pid: int) -> None:
        self.groups.add(pid)
        self.rows[pid] = own(self.out, pid, self.role)

    def discard(self, pid: int) -> None:
        self.groups.discard(pid)
        ended(self.out, self.rows.pop(pid, None), "reaped by the harness")


def record_directories(out, host: str | None, work) -> None:
    """Record the run's data directories: those under the output folder, and the one a Claude host keeps outside it (Claude
    Code names its per-project folder after the working directory, every character but a letter or digit made '-')."""
    out = Path(out)
    found = [{"path": name, "role": role} for name, role in DATA_DIRECTORIES.items() if (out / name).exists()]
    if host == "claude":
        outside = Path.home() / ".claude" / "projects" / re.sub(r"[^A-Za-z0-9]", "-", os.path.realpath(work))
        found.append({"path": environment._home(outside), "role": "the Claude host's session logs", "outside_output": True,
                      "exists": outside.is_dir()})
    with contextlib.suppress(OSError):
        record(out, "directories", directories=found)


# ---------------------------------------------------------------- ShipLoop's progress observer

def _flag(words: list[str], name: str) -> str | None:
    return words[words.index(name) + 1] if name in words[:-1] else None


def observer_records(folder) -> list[Path]:
    """The progress-observer records of ShipLoop runs in an output folder (the two run-directory layouts)."""
    folder = Path(folder)
    return sorted(path for pattern in RUN_DIR_GLOBS for path in folder.glob(f"{pattern}/{OBSERVER_RECORD}"))


def observer(path: Path, now: dict[int, dict]) -> dict | None:
    """The live observer a record names, or None. Accepted only while it is an orphan (parent pid 1: the ShipLoop command that
    started it has exited, so it is no one's foreground watch), leads its own group, and its command line carries the record's
    instance id and run directory (shiploop_progress.start passes both)."""
    try:
        found = json.loads(path.read_text())
        pid, instance = int(found["pid"]), str(found["instance"])
    except (OSError, ValueError, KeyError, TypeError):
        return None
    row = now.get(pid)
    if not row or row["ppid"] != 1 or row["pgid"] != pid:
        return None
    words = row["command"].split()
    run_dir = _flag(words, "--run-dir")
    if _flag(words, "--instance") != instance or not run_dir or os.path.realpath(run_dir) != os.path.realpath(path.parent):
        return None
    return row


def adopt_observers(out, now: dict[int, dict]) -> list[dict]:
    """Record, as groups of role ``observer``, the live observers of this run's ShipLoop runs that the ledger does not hold yet."""
    known = {(row.get("pgid"), (row.get("leader") or {}).get("started")) for row in rows(out) if row.get("kind") == "group"}
    adopted = []
    for path in observer_records(out):
        row = observer(path, now)
        if row and (row["pgid"], row["started"]) not in known:
            with contextlib.suppress(OSError):
                adopted.append(record(out, "group", id=f"{row['pid']}@{time.time():.6f}", pgid=row["pgid"], role="observer",
                                      leader=row, record=path.relative_to(Path(out)).as_posix()))
    return adopted


# ---------------------------------------------------------------- stopping

def _members(pgid: int, now: dict[int, dict]) -> list[dict]:
    return [row for row in now.values() if row["pgid"] == pgid]


def _named(row: dict) -> dict:
    return {"pid": row["pid"], "command": row["command"][:200]}


def _signal_group(pgid: int, number: int) -> None:
    listeners.signal_adopted_group(pgid, number)  # the harness's group signals all live in listeners.py (S-12)


def stop(group: dict) -> tuple[str, dict]:
    """Stop one recorded group if, and only if, it is still the one recorded: ``(how, detail)``.

    ``how`` is ``stopped`` (``ended_by`` SIGTERM or SIGKILL), ``survived`` (still there after SIGKILL), ``gone`` (nothing
    left in the group), ``reused`` (the pid now names another process: not signalled), ``unverified`` (the leader is gone, or
    was never seen, and processes remain in the group: not signalled, listed) or ``protected`` (the group holds this process or
    an ancestor). A leader that is this process's unreaped child is ended by ``listeners.end_group``, the exact path. Between
    the identity check and each signal the group is never seen empty, and a group number is not reused while the group has a
    member, so a signal reaches only the group that was checked. Raises Unobserved."""
    pgid, leader = group["pgid"], group.get("leader")
    if pgid <= 1:
        return "protected", {"members": []}
    now = table()
    members = _members(pgid, now)
    current = now.get(pgid)
    if not members:
        return "gone", {}
    if current is not None and leader and not same_leader(leader, current):
        return "reused", {"now": _named(current)}
    if not leader or current is None:
        return "unverified", {"members": [_named(row) for row in members],
                              "reason": "the leader was never seen" if not leader else "the leader is gone"}
    if any(row["pid"] in listeners.protected_pids() for row in members):
        return "protected", {"members": [_named(row) for row in members]}
    if listeners.unreaped(pgid) is not None:
        listeners.end_group(pgid)  # SIGKILL; the Popen that started it reaps it
        return "stopped", {"ended_by": "SIGKILL", "members": len(members)}
    for name, number, wait in (("SIGTERM", signal.SIGTERM, GRACE_SECONDS), ("SIGKILL", signal.SIGKILL, FORCE_SECONDS)):
        _signal_group(pgid, number)
        end = time.monotonic() + wait
        while time.monotonic() < end:
            time.sleep(POLL_SECONDS)
            if not _members(pgid, table()):
                return "stopped", {"ended_by": name, "members": len(members)}
    return "survived", {"members": [_named(row) for row in _members(pgid, table())]}


def cleanup(out) -> dict:
    """Stop what the run's ledger says it owns and is still alive (ShipLoop's observer adopted first), and record each group's
    end. Idempotent: a group with an ``ended`` row is not looked at again, so a second cleanup changes nothing. Deletes no
    file. Returns ``{observed: True, stopped, survived, gone, reused, unverified, protected}`` (each a list) or
    ``{observed: False, reason}``."""
    out = Path(out)
    found: dict = {"observed": True, "stopped": [], "survived": [], "gone": [], "reused": [], "unverified": [], "protected": []}
    try:
        adopt_observers(out, table())
        for group in open_groups(out):
            how, detail = stop(group)
            entry = {"pgid": group["pgid"], "role": group.get("role"),
                     "command": ((group.get("leader") or {}).get("command") or "")[:200], **detail}
            found[how].append(entry)
            if how != "survived":  # a survivor stays open, so a later cleanup (or the orphan refusal) sees it again
                ended(out, group, how, **detail)
    except listeners.Unobserved as exc:
        return {"observed": False, "reason": str(exc), **{key: value for key, value in found.items() if value and key != "observed"}}
    return found


def cleanup_line(record_: dict | None) -> str | None:
    """The one printed line for a cleanup that stopped, could not stop or could not see something; None when it found nothing."""
    if not record_:
        return None
    parts = [f"stopped {item['role']} group {item['pgid']} by {item['ended_by']}" for item in record_.get("stopped") or []]
    parts += [f"could not stop {item['role']} group {item['pgid']}" for item in record_.get("survived") or []]
    parts += [f"left {len(item['members'])} process(es) of {item['role']} group {item['pgid']} alone ({item['reason']})"
              for item in record_.get("unverified") or []]
    if not record_.get("observed", True):
        parts.append(f"not observed: {record_.get('reason')}")
    return "  cleanup   " + "; ".join(parts) if parts else None


# ---------------------------------------------------------------- refusals before a host starts

def orphans(root, own_out=None) -> list[dict]:
    """The recorded groups and observers of runs under ``root`` (``own_out`` aside) whose harness is not alive and whose
    leader still has its recorded identity: what a cleanup of that run would stop. Raises Unobserved."""
    mine = os.path.realpath(own_out) if own_out else None
    candidates = []
    for folder in environment.run_folders(root) if Path(root).is_dir() else []:
        if os.path.realpath(folder) == mine:
            continue
        groups, records = open_groups(folder), observer_records(folder)
        if (groups or records) and not listeners.case_alive(folder):
            candidates.append((folder, groups, records))
    if not candidates:
        return []
    now = table()
    found = []
    for folder, groups, records in candidates:
        seen = set()
        for group in groups:
            row = now.get(group["pgid"])
            if same_leader(group.get("leader"), row):
                seen.add(row["pid"])
                found.append({"output": str(folder), "role": group.get("role"), **_named(row)})
        for path in records:
            row = observer(path, now)
            if row and row["pid"] not in seen:
                found.append({"output": str(folder), "role": "observer", **_named(row)})
    return found


def orphan_lines(root, own_out=None) -> list[str]:
    """One refusal line per orphan; a table that cannot be read prints a note and refuses nothing (as the stale-listener check)."""
    try:
        found = orphans(root, own_out)
    except listeners.Unobserved as exc:
        print(f"orphan check skipped: {exc}", flush=True)
        return []
    return [f"pid {item['pid']} ({item['role']}: {item['command'][:120]}) belongs to {item['output']}, whose harness is not "
            f"running: stop it with `python3 {Path(__file__).resolve()} cleanup {item['output']}`" for item in found]


def disk(path, runs: int = 1) -> dict:
    """The free space on ``path``'s file system (the nearest folder that exists) against the headroom ``runs`` cases need."""
    place = Path(path).expanduser().absolute()
    while not place.exists() and place != place.parent:
        place = place.parent
    free = shutil.disk_usage(place).free
    need = HEADROOM_PER_RUN * max(1, runs)
    return {"path": environment._home(place), "free_bytes": free, "need_bytes": need, "ok": free >= need}


def disk_line(found: dict) -> str | None:
    """The refusal line for a disk below the headroom, None when there is room."""
    if found["ok"]:
        return None
    return (f"{found['free_bytes'] / 1024 ** 3:.1f} GB free on {found['path']}, below the {found['need_bytes'] / 1024 ** 3:.0f} GB "
            "headroom this invocation's cases need: free space, or run fewer cases at once")


def contention(out, host: str | None, model: str | None) -> dict:
    """The live harness runs under the runs root (``out`` aside), with the host and model each last launched on, and which share
    this run's: provider contention is observed, never reserved. Never raises."""
    try:
        root, mine = environment.runs_root(out), os.path.realpath(out)
        live = []
        for folder in environment.run_folders(root) if root.is_dir() else []:
            if os.path.realpath(folder) == mine or not listeners.case_alive(folder):
                continue
            launched = runrecord.launches(folder)
            last = launched[-1][1] if launched else {}
            live.append({"folder": environment._shown(folder, root), "host": last.get("host"), "model": last.get("model")})
    except Exception as exc:  # noqa: BLE001 - a record that cannot be made is reported, never raised
        return {"observed": False, "reason": " ".join(str(exc).split())[:200] or type(exc).__name__}
    return {"observed": True, "root": environment._home(root), "live_runs": live,
            "same_host": [run["folder"] for run in live if host and run["host"] == host],
            "same_model": [run["folder"] for run in live if model and run["model"] == model]}


# ---------------------------------------------------------------- leases

def leases_dir() -> Path:
    named = os.environ.get(LEASES_ENV)
    if named:
        return Path(named).expanduser()
    return Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local" / "state") / "shiploop-e2e" / "leases"


def platform_target_key(platform: dict | None) -> str | None:
    """The declared external target, independent of a run's metadata prefix."""
    if not platform:
        return None
    parts = [platform.get("kind") or "platform", platform.get("org")]
    return "platform-" + "-".join(str(part) for part in parts if part)


def lease_keys(platform: dict | None, ports=()) -> list[str]:
    """Lease the target and its legacy prefix key, plus declared fixed ports."""
    keys = []
    target = platform_target_key(platform)
    if target:
        keys.append(target)
        if platform.get("prefix"):
            keys.append(f"{target}-{platform['prefix']}")
    return keys + [f"port-{int(port)}" for port in sorted(set(ports or ()))]


def _file(key: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]", "_", key) + ".lock"


def holder(key: str) -> dict | None:
    """What the harness that holds ``key`` wrote about itself, or None. Reads only."""
    try:
        found = json.loads((leases_dir() / _file(key)).read_text())
    except (OSError, ValueError):
        return None
    return found if isinstance(found, dict) else None


def _same_file(descriptor: int, path: Path) -> bool:
    with contextlib.suppress(OSError):
        mine, there = os.fstat(descriptor), os.stat(path)
        return (mine.st_dev, mine.st_ino) == (there.st_dev, there.st_ino)
    return False


class Lease:
    """The leases one harness holds: each an open, exclusively locked file. ``close`` gives them back (``held`` lists of open
    files are closed by main's ``finally``)."""

    def __init__(self, about: dict):
        self.about = about
        self.held: list[tuple[str, int, Path]] = []
        self.out: Path | None = None
        self.notes: list[str] = []

    @property
    def keys(self) -> list[str]:
        return [key for key, _, _ in self.held]

    def _write(self, descriptor: int) -> None:
        data = json.dumps({**self.about, **({"output": str(self.out)} if self.out else {})}).encode()
        os.ftruncate(descriptor, 0)
        os.pwrite(descriptor, data, 0)

    def take(self, key: str) -> None:
        """Lock ``key``'s file, or raise Refused naming its holder. A file a release removed and replaced while this one opened
        it is not the lease: the lock is taken again on the file the path names now."""
        for _ in range(10):
            folder = leases_dir()
            folder.mkdir(parents=True, exist_ok=True)
            path = folder / _file(key)
            try:
                descriptor = os.open(path, os.O_RDWR | os.O_CREAT, 0o644)
            except FileNotFoundError:  # a release removed the empty folder between the two calls
                continue
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                os.close(descriptor)
                held_by = holder(key) or {}
                raise Refused(f"{key} is leased by the harness of {held_by.get('output') or 'another run'} (pid "
                              f"{held_by.get('pid', '?')}, case {held_by.get('case', '?')}): it ends when that harness ends, "
                              "so wait for it or end that run") from None
            if not _same_file(descriptor, path):
                os.close(descriptor)
                continue
            self._write(descriptor)
            self.held.append((key, descriptor, path))
            return
        raise Refused(f"{key}: its lease file kept changing while it was taken; try again")

    def bind(self, out) -> None:
        """Name the run's output folder in each lease (taken before the folder existed) and record the leases in its ledger."""
        self.out = Path(out)
        for key, descriptor, _ in self.held:
            with contextlib.suppress(OSError):
                self._write(descriptor)
                record(self.out, "lease", key=key, folder=environment._home(leases_dir()))

    def close(self) -> None:
        """Give every lease back: remove its file while it is still locked (a harness that opened the old file finds it gone
        and opens the new one), then unlock it. Never raises."""
        for key, descriptor, path in reversed(self.held):
            with contextlib.suppress(OSError):
                if _same_file(descriptor, path):
                    os.unlink(path)
            with contextlib.suppress(OSError):
                os.close(descriptor)
            if self.out is not None:
                with contextlib.suppress(OSError):
                    record(self.out, "released", key=key)
        self.held = []
        folder = leases_dir()
        for empty in (folder, *(() if os.environ.get(LEASES_ENV) else (folder.parent,))):
            with contextlib.suppress(OSError):
                empty.rmdir()  # only when empty: leave the state home as it was


def take(keys, about: dict, ports=()) -> Lease:
    """Lease every key, all or none, and refuse when a declared port has a listener now (this user's processes; a table that
    cannot be read is a note, not a refusal). Raises Refused, with every lease of the attempt already given back."""
    lease = Lease(about)
    try:
        for key in sorted(set(keys)):
            lease.take(key)
        if ports:
            try:
                busy = [item for item in listeners.observe() if set(ports) & set(item.get("ports") or ())]
            except listeners.Unobserved as exc:
                busy = []
                lease.notes.append(f"port check skipped: {exc}")
            if busy:
                raise Refused("; ".join(f"port {','.join(map(str, sorted(set(ports) & set(item['ports']))))} is in use by pid "
                                        f"{item['pid']} {item['command']} (working directory {item.get('cwd')})"
                                        for item in busy) + ": the run's product would meet it, so no host is started")
    except BaseException:
        lease.close()
        raise
    return lease


# ---------------------------------------------------------------- evidence and disposal

def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], capture_output=True, text=True, stdin=subprocess.DEVNULL)


def evidence(out) -> dict:
    """What disposal needs kept, and whether it is there: ``{complete, head, missing: [...]}``."""
    out = Path(out)
    missing = []
    try:
        result = json.loads((out / "result.json").read_text())
    except (OSError, ValueError):
        result = {}
        missing.append("result.json")
    head = ((result.get("delivery") or {}).get("before") or {}).get("head")
    if result and not head:
        missing.append("result.json delivery.before.head (the delivery's identity)")
    missing += [name for name in LOGS if not (out / name).is_file()]
    bundle = out / "delivery" / "work.bundle"
    if not bundle.is_file():
        missing.append("delivery/work.bundle")
    elif _git("bundle", "verify", "-q", str(bundle)).returncode != 0:
        missing.append("delivery/work.bundle (git bundle verify failed)")
    elif head and not _bundle_holds(bundle, head):
        missing.append(f"delivery/work.bundle with the delivered head {head[:12]}")
    return {"complete": not missing, "head": head, "missing": missing}


def _bundle_holds(bundle: Path, head: str) -> bool:
    """Whether the delivered head is in the bundle: a ref's tip, or else a commit of its history, read from a bare clone in a
    temporary folder that is removed."""
    if head in _git("bundle", "list-heads", str(bundle)).stdout.split():
        return True
    with tempfile.TemporaryDirectory(prefix="shiploop-e2e-bundle-") as scratch:
        if _git("clone", "-q", "--bare", str(bundle), scratch + "/clone").returncode != 0:
            return False
        return _git("--git-dir", scratch + "/clone", "cat-file", "-e", head + "^{commit}").returncode == 0


def dispose(out, parts=HEAVY) -> dict:
    """Remove the heavy folders of a run that is over, keeping its records, logs and delivery bundle. Refused (nothing removed)
    while a harness holds the case, while a recorded group is alive, or while the evidence is incomplete. Idempotent: a folder
    already gone is not an error. Returns ``{disposed: bool, removed, refused?, missing?}``."""
    out = Path(out)
    lock = listeners.hold_case(out)
    if lock is None:
        return {"disposed": False, "removed": [], "refused": f"a harness holds {out / listeners.LOCK_NAME}, or it cannot be taken"}
    try:
        try:
            alive = [group["pgid"] for group in open_groups(out) if same_leader(group.get("leader"), table([group["pgid"]]).get(group["pgid"]))]
        except listeners.Unobserved as exc:
            return {"disposed": False, "removed": [], "refused": f"the process table cannot be read ({exc})"}
        if alive:
            return {"disposed": False, "removed": [], "refused": f"recorded groups {alive} are alive: run cleanup first"}
        kept = evidence(out)
        if not kept["complete"]:
            return {"disposed": False, "removed": [], "refused": "the evidence is not complete", "missing": kept["missing"]}
        removed = []
        for name in parts:
            target = out / name
            if target.is_symlink() or not target.exists():
                continue
            shutil.rmtree(target)
            removed.append(name)
        with contextlib.suppress(OSError):
            record(out, "disposed", removed=removed, head=kept["head"])
        return {"disposed": True, "removed": removed, "head": kept["head"]}
    finally:
        lock.close()


# ---------------------------------------------------------------- command line

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("action", choices=("cleanup", "dispose"))
    parser.add_argument("output", type=Path)
    args = parser.parse_args(argv)
    out = args.output.expanduser().resolve()
    if not (out / "invocation.json").is_file():
        raise SystemExit(f"{out} is not a run's output folder (no invocation.json)")
    if args.action == "dispose":
        found = dispose(out)
        print(json.dumps(found, indent=2))
        return 0 if found["disposed"] else 1
    lock = listeners.hold_case(out)
    if lock is None:
        raise SystemExit(f"a harness is running {out} (it holds {out / listeners.LOCK_NAME}): nothing was stopped")
    try:
        found = cleanup(out)
    finally:
        lock.close()
    print(json.dumps(found, indent=2))
    return 0 if found.get("observed") and not found.get("survived") else 1


if __name__ == "__main__":
    raise SystemExit(main())
