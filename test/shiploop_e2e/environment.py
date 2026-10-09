"""What the machine, the launches and the neighbouring runs were while a case ran: the ``environment`` record.

SPEC (2026-10-09, "A record of the machine, of the product at stop or of the ending is not a verdict"): a record beside the
verdicts, never a verdict.  Nothing here changes ``pass``, the exit code or the control flow, and every part says what it could
not measure instead of guessing: a value nothing measured is ``None`` with its reason, ``[]`` only where something looked and
found none.

* the tool versions on the harness's PATH (``node``, ``python3``, ``git``), the CPU count and the load, at the start of each
  launch and at the end of the run, and whether the host ran under a display hold;
* ``hosts_used`` and one entry per launch, read through ``runrecord`` (the one reader of the launch records), so a run that two
  hosts worked on is named so;
* ``overlap``: the sibling output folders whose ``timeline.jsonl`` span overlaps this run's, read at the end of the run and only
  for reading;
* a browser capability record, only where a case or ``--need browser`` declares one.

The host CLI build is not read here: a launch record carries ``host_build`` where the harness captured it at launch, and the
per-launch entry passes it through (null where the record has none).

Run it as a program to see the browser record for a browser by hand (the calibration the SPEC asks for before any use of it)::

    python3 test/shiploop_e2e/environment.py --need browser [--browser-bin PATH]
"""

from __future__ import annotations

import argparse
import contextlib
from datetime import datetime, timezone
import http.server
import json
import os
from pathlib import Path
import shutil
import signal
import select
import subprocess
import sys
import tempfile
import threading
import time
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hosts  # noqa: E402  (hosts.probe_version: the one `--version` reader)
import listeners  # noqa: E402
import metrics  # noqa: E402
import runrecord  # noqa: E402

NEEDS = ("browser",)
TOOLS = ("node", "python3", "git")
# Every `--version` (the tools here, the browser, the host CLIs) is read by hosts.probe_version, under its one ceiling
# (hosts.VERSION_TIMEOUT_SECONDS) and with its one set of reasons.

# A browser started headless to dump the DOM of a stand-in page.  The hygiene flags keep a fresh profile from phoning home
# (a first launch registered with a push service and tried to install a default app); they did not change how long a launch
# lingers, so they are hygiene only.
BROWSER_FLAGS = ("--headless=new", "--disable-gpu", "--no-first-run", "--disable-background-networking",
                 "--disable-default-apps", "--disable-component-update", "--disable-sync")
# How long a launch that never prints its page is waited for: a ceiling, not a tuning value (16 of 16 launches in the design audit
# printed in 0.36 to 0.47 s).  Past it the browser's group is stopped and the target is recorded as no title.  Recorded as
# ``ceiling_seconds``.
TITLE_CEILING_SECONDS = 20.0
# How long a browser that has printed its page is given to exit by itself before its group is stopped.  A definition, not a
# ceiling: ``lingered`` means still running after this long, and ``exited`` means it ended within it.  Most launches did not exit at
# all (the audit: 3 of 16 exited before its 12 to 20 s ceiling; the other 13 were still running there and were killed, so their exit
# time is unknown), which is why the exit is recorded and not waited for.  Recorded as ``grace_seconds``.
GRACE_SECONDS = 1.0
# How long a stopped group is given to be gone before it is recorded as not empty: a ceiling, and the basis of ``group_empty``.
# Recorded as ``empty_seconds``.
EMPTY_SECONDS = 2.0
POLL_SECONDS = 0.02
# Where a browser is looked for when none is named.  Tests patch `autodetect_browser`, so none of this runs there.
BROWSER_PATHS = ("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                 "/Applications/Chromium.app/Contents/MacOS/Chromium")
BROWSER_NAMES = ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "chrome")

NOT_DECLARED = {"declared": False, "probed": False, "reason": "no case or --need declares a browser"}


def now_text() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def unobserved(reason: str) -> dict:
    """A part of the record nothing measured: said so, with why, never an empty value that reads as a measured none."""
    return {"observed": False, "reason": reason}


# ---------------------------------------------------------------- tools, load, the start and the end

def read_tools() -> tuple[dict, dict]:
    """(``{tool: first stdout line of tool --version or None}``, ``{tool: why None}``), the tools found on this PATH, each read
    by hosts.probe_version in the harness's own environment (what the model's shell inherits)."""
    versions: dict = {}
    unread: dict = {}
    for name in TOOLS:
        path = shutil.which(name)
        if path is None:
            versions[name], unread[name] = None, "not found on PATH"
            continue
        versions[name], why = hosts.probe_version(path, None)
        if why:
            unread[name] = why
    return versions, unread


_TOOLS: tuple[dict, dict] | None = None


def tools() -> tuple[dict, dict]:
    """The tool versions, read once per process: they do not change while a harness runs, and every test case calls main()."""
    global _TOOLS
    if _TOOLS is None:
        _TOOLS = read_tools()
    return _TOOLS


def machine() -> tuple[dict, dict]:
    """(``{cpus, loadavg}``, ``{field: why None}``): None where the machine would not say, with the reason."""
    unread: dict = {}
    cpus = os.cpu_count()
    if cpus is None:
        unread["cpus"] = "os.cpu_count() could not tell"
    try:
        load = [round(value, 2) for value in os.getloadavg()]
    except OSError as exc:
        load = None
        unread["loadavg"] = f"os.getloadavg() failed: {exc}"
    return {"cpus": cpus, "loadavg": load}, unread


def start_record(display_hold: bool, needs=(), browser_bin: str | None = None, should_stop=None) -> dict:
    """The record of one launch's start: tools, machine, display hold and (only where declared) the browser capability.
    ``should_stop`` (the harness passes its termination flag) ends the browser probe early."""
    versions, unread = tools()
    state, missing = machine()
    return {"observed": True, "at": now_text(), "tools": dict(versions), **state, "display_hold": bool(display_hold),
            "unread": {**unread, **missing},
            "browser": browser_record(browser_bin, should_stop=should_stop) if "browser" in needs else dict(NOT_DECLARED)}


def end_record() -> dict:
    """The machine at the end of the run (the tools are not read again)."""
    state, unread = machine()
    return {"observed": True, "at": now_text(), **state, "unread": unread}


# ---------------------------------------------------------------- launches and hosts

def _environment_reason(record: dict) -> str | None:
    """Why a launch's ``environment`` is null (None when it holds a record)."""
    if isinstance(record.get("environment"), dict):
        return None
    if "environment" not in record:
        return "the launch record has no environment (it was written before the record existed)"
    return f"the launch record's environment is not a record ({type(record['environment']).__name__})"


def launch_environments(out) -> list[dict]:
    """One entry per launch of the run that could be read, first launch first: who ran it and the start record that launch kept.
    ``host_build`` and its reason are read through runrecord.host_build, the one reader of a launch's build, under the launch
    record's own key names (``host_build``, ``identity_unmeasured.host_build``: empty when the build is known); ``environment``
    is whatever the launch record carries, null with ``environment_reason`` saying why (an old launch has none)."""
    entries = []
    for name, record in runrecord.launches(Path(out)):
        build, why = runrecord.host_build(record)
        entries.append({"launch": name, "host": record.get("host"), "model": record.get("model"), "effort": record.get("effort"),
                        "host_build": build, "identity_unmeasured": {"host_build": why} if why else {},
                        "environment": record.get("environment") if isinstance(record.get("environment"), dict) else None,
                        "environment_reason": _environment_reason(record)})
    return entries


def restated_start(out) -> dict:
    """A regrade starts no host: the start of the run's last launch, as that launch recorded it."""
    last = launch_environments(out)[-1:]
    if not last:
        return unobserved("regraded: the run has no readable launch record")
    return last[0]["environment"] or unobserved("regraded: " + last[0]["environment_reason"])


# ---------------------------------------------------------------- overlap with the neighbouring runs

OVERLAP_BASIS = ("the first and last host event of this run and of each sibling folder in the same parent folder (timeline.jsonl holds "
                 "host events only): it counts a pause between sessions, and misses the setup before the first event and the checks "
                 "and reap after the last, so the seconds are neither an upper nor a lower bound")


def overlap(out) -> dict:
    """Which neighbouring runs were running while this one was, read-only (SPEC "Parallel work").

    A count taken at the start of a run misses an overlap that begins later: of the nine round runs of 2026-10-08 all nine
    overlapped another run, and three saw the overlap begin more than a second after their own start.  So the whole span is
    compared, at the end.  ``started_offset_seconds`` is the sibling's start minus this run's: negative when it was already
    running, positive when it began later.  Siblings in other parent folders are not seen.
    """
    out = Path(out)
    mine = metrics.span(out / "timeline.jsonl")  # the one span reader (finite stamps, first <= last)
    if mine["started"] is None:
        return unobserved("this run's timeline.jsonl has no readable stamp")
    own = (mine["started"], mine["ended"])
    try:
        folders = sorted(path for path in out.parent.iterdir() if path.is_dir() and path.name != out.name)
    except OSError as exc:
        return unobserved(f"the folder beside this run could not be listed: {exc}")
    runs, read, unreadable = [], 0, []
    for folder in folders:
        timeline = folder / "timeline.jsonl"
        if not (timeline.exists() or timeline.is_symlink()):
            continue  # not a run, or one that has not had an event yet: not seen
        theirs = metrics.span(timeline)
        if theirs["started"] is None:
            unreadable.append(folder.name)  # there, and no span can be read from it: named, never dropped silently
            continue
        read += 1
        other = (theirs["started"], theirs["ended"])
        # Concurrent when they share time (metrics.spans_overlap, the one interval rule): an instant inside the other span
        # counts (a run whose stamps are all one instant, inside a neighbour's span), one span ending as the other begins does not.
        if not metrics.spans_overlap(own, other):
            continue
        seconds = min(own[1], other[1]) - max(own[0], other[0])
        launched = runrecord.launches(folder)
        bad = runrecord.unreadable(folder)
        hosts = None if bad or not launched else runrecord.hosts_used(folder)
        why = (f"{len(bad)} launch record(s) could not be read: {', '.join(bad)}" if bad else
               "no launch record in the folder" if not launched else None)
        runs.append({"folder": folder.name, "case": (launched[0][1].get("case") if launched else None),
                     "hosts": hosts, "hosts_reason": why, "overlapped_seconds": round(seconds, 1),
                     "started_offset_seconds": round(other[0] - own[0], 1)})
    return {"observed": True, "basis": OVERLAP_BASIS, "span": {"first": own[0], "last": own[1]}, "siblings_read": read,
            "siblings_unreadable": unreadable, "runs": runs}


def result_block(out, start: dict, end: dict) -> dict:
    """The ``environment`` block of result.json: this launch's start and the run's end, the hosts and launches of the whole run,
    and the overlap.  Each part that cannot be made says so and the others stand."""
    def part(make):
        try:
            return make()
        except Exception as exc:  # noqa: BLE001 - a record that cannot be made is reported, never raised
            return unobserved(" ".join(str(exc).split())[:200] or type(exc).__name__)

    bad = part(lambda: runrecord.unreadable(Path(out)))
    if isinstance(bad, list) and bad:
        # A launch that cannot be read may be another host's: the list of hosts would be shorter than the truth, so it is unknown.
        hosts = mixed = unobserved(f"{len(bad)} launch record(s) could not be read: {', '.join(bad)}")
    else:
        hosts = part(lambda: runrecord.hosts_used(Path(out)))
        mixed = part(lambda: runrecord.mixed_host(Path(out)))
    return {"start": start, "end": end, "hosts_used": hosts, "mixed_host": mixed,
            "launches_unreadable": bad, "environments": part(lambda: launch_environments(out)),
            "overlap": part(lambda: overlap(out))}


# ---------------------------------------------------------------- the browser capability record

def autodetect_browser() -> str | None:
    """A browser binary in the usual places, or None.  Nothing is launched to find it."""
    for path in BROWSER_PATHS:
        if os.access(path, os.X_OK) and Path(path).is_file():
            return path
    for name in BROWSER_NAMES:
        found = shutil.which(name)
        if found:
            return found
    return None


def find_browser(named: str | None) -> str | None:
    """The browser binary to probe: the named one if it is runnable, else a detected one; None if there is none."""
    if named:
        path = shutil.which(named) if os.sep not in named else named
        return path if path and os.access(path, os.X_OK) and Path(path).is_file() else None
    return autodetect_browser()


class _Page(http.server.BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802 - the http.server name
        body = self.server.page.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):  # a stand-in logs nothing
        pass


class StandIn:
    """One page, served two ways for a browser to load: a ``file:`` URL and a loopback ``http://127.0.0.1:<port>/`` URL on a
    port the system chooses.  The server runs in this process and is closed, with its thread and its files, on exit."""

    def __enter__(self):
        self.token = "e2e-stand-in-" + uuid.uuid4().hex[:12]
        self.page = f"<!doctype html><html><head><title>{self.token}</title></head><body>ok</body></html>"
        self.dir = Path(tempfile.mkdtemp(prefix="e2e-stand-in-"))
        (self.dir / "index.html").write_text(self.page)
        self.file_url = (self.dir / "index.html").as_uri()
        self.server, self.thread, self.http_url, self.http_error = None, None, None, None
        try:
            self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Page)
            self.server.daemon_threads = True
            self.server.page = self.page
            self.thread = threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
            self.thread.start()
            self.http_url = f"http://127.0.0.1:{self.server.server_address[1]}/"
        except OSError as exc:
            self.http_error = f"the loopback stand-in could not listen: {exc}"
            if self.server is not None:
                self.server.server_close()
        return self

    def __exit__(self, *exc_info):
        if self.thread is not None:
            self.server.shutdown()
            self.thread.join(timeout=5)
        if self.server is not None:
            self.server.server_close()
        shutil.rmtree(self.dir, ignore_errors=True)
        return False


def _group_alive(group: int) -> bool:
    try:
        os.killpg(group, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


# The process groups of the browsers a probe has started and not yet ended, by the pid of the leader of each (verified at launch).
# `run.end_live_hosts` ends them too, so a SIGTERM to the harness, a Ctrl-C and the exit-time hook reach a browser the probe started,
# as they reach a host: only a SIGKILL of the harness can leave one.
LIVE_PROBE_GROUPS: set[int] = set()


def end_live_probes() -> None:
    """SIGKILL the group of every browser a probe is running now (listeners.end_group: a group already gone, or one whose leader
    was already reaped, is left alone)."""
    for group in tuple(LIVE_PROBE_GROUPS):  # a copy: a probe discards its own group as it ends
        listeners.end_group(group)


def probe_target(binary: str, url: str, token: str, ceiling: float, grace: float, should_stop=None) -> dict:
    """Load one URL in a headless browser and record what the browser did, not what its exit code says.

    The browser is started in a session of its own, so its group is its own; that is verified at launch, and only that group
    is ever signalled (a browser whose group cannot be confirmed is stopped by its pid alone).  Success is the stand-in's title
    appearing in the browser's output.  Once it has, the browser gets ``grace`` seconds to exit by itself; a browser still there
    is stopped (it lingered: ``lingered`` is True, ``exited`` False).  A browser that prints nothing is waited for up to
    ``ceiling`` seconds.  ``should_stop``, polled with the waits, ends the probe early (``interrupted`` is True).  Whatever
    ends the probe (a title, the ceiling, a stop request, an exception), the browser it started is stopped before it returns.
    """
    profile = tempfile.mkdtemp(prefix="e2e-browser-profile-")
    record = {"title_seen": False, "output_s": None, "exited": False, "lingered": False, "returncode": None,
              "killed": False, "group_empty": None, "interrupted": False, "error": None}
    proc = None
    reader = None
    group = None
    leads = False
    stop = threading.Event()

    def asked_to_stop() -> bool:
        return bool(should_stop is not None and should_stop())

    def end_browser() -> None:
        """Stop what is still running of the browser this call started: its group if it leads one, else the child alone."""
        if proc is None:
            return
        if leads and (proc.poll() is None or _group_alive(group)):
            listeners.end_group(group)  # nothing is sent once poll() has reaped the leader: its number may be reused
        elif not leads and proc.poll() is None:
            with contextlib.suppress(OSError):
                proc.kill()
        with contextlib.suppress(subprocess.TimeoutExpired):
            proc.wait(timeout=5)

    try:
        argv = [binary, *BROWSER_FLAGS, f"--user-data-dir={profile}", "--dump-dom", url]
        started = time.monotonic()
        try:
            proc = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                    start_new_session=True)
        except OSError as exc:
            record["error"] = f"could not start: {exc}"
            return record
        group = proc.pid
        try:
            leads = os.getpgid(proc.pid) == group
        except OSError:
            leads = False  # gone already, or not confirmable: the child alone is stopped, never a group that is not ours
        if leads:
            LIVE_PROBE_GROUPS.add(group)
        seen: list[float] = []
        data = bytearray()
        needle = token.encode()

        def read() -> None:
            # Raw reads with a poll, so the thread can be told to stop: closing a pipe that a thread is blocked reading waits
            # for the pipe to close, and a helper that left the group can hold it open long after the browser is gone.
            fd = proc.stdout.fileno()
            while not stop.is_set():
                if not select.select([fd], [], [], 0.1)[0]:
                    continue
                chunk = os.read(fd, 65536)
                if not chunk:
                    break
                data.extend(chunk)
                if not seen and needle in data:
                    seen.append(time.monotonic())

        reader = threading.Thread(target=read, daemon=True)
        reader.start()
        while not seen and proc.poll() is None and time.monotonic() - started < ceiling and not asked_to_stop():
            time.sleep(POLL_SECONDS)
        if proc.poll() is not None:
            reader.join(timeout=2)  # the last of its output
        if seen:
            end = time.monotonic() + grace
            while proc.poll() is None and time.monotonic() < end and not asked_to_stop():
                time.sleep(POLL_SECONDS)
        record["interrupted"] = asked_to_stop()
        record["title_seen"] = bool(seen)
        record["output_s"] = round(seen[0] - started, 2) if seen else None
        record["exited"] = proc.poll() is not None
        record["returncode"] = proc.returncode if record["exited"] else None
        record["lingered"] = bool(seen) and not record["exited"] and not record["interrupted"]
        if not record["exited"] or (leads and _group_alive(group)):
            record["killed"] = True
            end_browser()
        if leads:
            end = time.monotonic() + EMPTY_SECONDS
            while _group_alive(group) and time.monotonic() < end:
                time.sleep(POLL_SECONDS)
            record["group_empty"] = not _group_alive(group)
        return record
    finally:
        end_browser()  # a no-op after the normal path; the stop for an exception or an interrupt that skipped it
        stop.set()
        if reader is not None:
            reader.join(timeout=2)  # it looks at `stop` every 0.1 s
        if proc is not None and proc.stdout is not None and (reader is None or not reader.is_alive()):
            with contextlib.suppress(OSError):
                proc.stdout.close()
        if group is not None:
            LIVE_PROBE_GROUPS.discard(group)
        shutil.rmtree(profile, ignore_errors=True)


def browser_record(binary: str | None, ceiling: float | None = None, grace: float | None = None, should_stop=None) -> dict:
    """The browser capability record of a declared need: can a headless browser load a stand-in page here, over ``file:`` and
    over loopback http?  A record, never a gate.  The two targets are probed one after the other, so each browser is measured
    beside no other probe browser.  ``should_stop`` ends the probe early.  Never raises: a failing part is the record's reason."""
    ceiling = TITLE_CEILING_SECONDS if ceiling is None else ceiling
    grace = GRACE_SECONDS if grace is None else grace
    try:
        found = find_browser(binary)
        if found is None:
            return {"declared": True, "probed": False,
                    "reason": "no browser binary" + (f" at {binary}" if binary else " found in the usual places or on PATH")}
        version, why = hosts.probe_version(found, None)  # the binary on disk, in the harness's environment
        record: dict = {"declared": True, "probed": True, "binary": found, "version": version,
                        "flags": list(BROWSER_FLAGS), "ceiling_seconds": ceiling, "grace_seconds": grace,
                        "empty_seconds": EMPTY_SECONDS}
        if why:
            record["version_unread"] = why
        with StandIn() as page:
            targets = {"file": page.file_url}
            if page.http_url:
                targets["http"] = page.http_url
            else:
                record["http"] = {"probed": False, "reason": page.http_error}
            for kind, url in targets.items():
                if should_stop is not None and should_stop():
                    record[kind] = {"probed": False, "reason": "the harness was told to end before this target was probed"}
                    continue
                record[kind] = probe_target(found, url, page.token, ceiling, grace, should_stop)
        return record
    except Exception as exc:  # noqa: BLE001 - a record that cannot be made is reported, never raised
        return {"declared": True, "probed": False, "reason": "probe failed: " + (" ".join(str(exc).split())[:200] or type(exc).__name__)}


def browser_line(record: dict) -> str:
    """One printed line for a declared browser capability: what the browser did, said as a record and not as a verdict."""
    if not record.get("probed"):
        return f"browser declared, not probed: {record.get('reason')}"
    parts = []
    for kind in ("file", "http"):
        target = record.get(kind)
        if not isinstance(target, dict):
            continue
        if target.get("probed") is False:
            parts.append(f"{kind} not probed ({target.get('reason')})")
        elif target.get("title_seen"):
            ending = ("lingered and was stopped" if target.get("lingered") else
                      "exited by itself" if target.get("exited") else "stopped")
            parts.append(f"{kind} title in {target.get('output_s')} s, {ending}")
        else:
            parts.append(f"{kind} no title ({'exited ' + str(target.get('returncode')) if target.get('exited') else 'stopped at the ceiling'})"
                         if not target.get("error") else f"{kind} not started ({target['error']})")
    return f"browser {record.get('version') or record.get('binary')}: " + "; ".join(parts) + " (a record, not a verdict)"


def summary_lines(block: dict) -> list[str]:
    """The printed lines for a run's environment block: the machine, a mixed-host run, and the neighbours."""
    lines = []
    start, end = block.get("start") or {}, block.get("end") or {}
    if start.get("observed") and end.get("observed"):
        first, last = (start.get("loadavg") or [None])[0], (end.get("loadavg") or [None])[0]
        lines.append(f"load {'not read' if first is None else first} -> {'not read' if last is None else last} on "
                     f"{start.get('cpus') if start.get('cpus') is not None else 'an unknown number of'} cpus; display "
                     f"{'held' if start.get('display_hold') else 'not held'}")
    else:
        lines.append("machine: " + (start.get("reason") if not start.get("observed") else "end not observed (" + str(end.get("reason")) + ")"))
    if block.get("mixed_host") is True:
        lines.append(f"MIXED HOST: {', '.join(block.get('hosts_used') or [])} worked on this run; its verdicts and costs belong to no one host")
    seen = block.get("overlap") or {}
    if not seen.get("observed"):
        lines.append("overlap not observed: " + str(seen.get("reason")))
    elif seen.get("runs"):
        lines.append("overlap: " + "; ".join(
            f"{r['folder']} ({', '.join(r.get('hosts') or []) or 'no host'}) {r['overlapped_seconds']} s, began "
            + (f"{r['started_offset_seconds']} s after this run started" if r["started_offset_seconds"] > 0 else
               f"{-r['started_offset_seconds']} s before this run started") for r in seen["runs"]))
    else:
        lines.append(f"overlap: none ({seen.get('siblings_read')} neighbouring runs read)")
    return lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Print the environment start record, for a calibration by hand.")
    parser.add_argument("--need", action="append", choices=NEEDS, default=[], help="declare a need (browser)")
    parser.add_argument("--browser-bin", help="the browser to probe (default: a detected Chrome or Chromium)")
    args = parser.parse_args(argv)

    def end(number, _frame):
        raise SystemExit(128 + number)  # unwinds through the probe's `finally`, which ends the browser and removes its files

    for number in (signal.SIGTERM, signal.SIGHUP):
        signal.signal(number, end)
    print(json.dumps(start_record(display_hold=False, needs=tuple(args.need), browser_bin=args.browser_bin), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
