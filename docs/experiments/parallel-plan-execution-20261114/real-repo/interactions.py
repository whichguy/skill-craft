#!/usr/bin/env python3
"""Cross-feature interaction checks for the composed ticket-assignment + ticket-import + ticket-due-times delivery
(docs/experiments/parallel-plan-execution-20261114/real-repo/). Standard library only.

    python3 interactions.py check TREE      one JSON object {"I1": {"ok": bool, "detail": str}, ..., "I5": {...}},
                                             exit 0 iff every check's "ok" is true; or, if TREE's server cannot be
                                             started at all, {"error": str} and exit 1 (no I1-I5 object in that case)
    python3 interactions.py --selfcheck     builds scratch copies of the composed tree, the bare base and six
                                             single-point mutations of the composed tree, runs I1-I5 (and, for the
                                             composed tree and the base, the three cases' own checks) against each,
                                             and prints a compact expected-vs-observed table

Each check starts its own ``node src/server.js`` from TREE, on a free port of its own, in a fresh scratch DATA_FILE
(and NOTIFY_FILE where it matters), with WORKER_INTERVAL_MS=50 and DUE_TIMES=on unless noted, and ends only the
process group it itself started (never a pkill by pattern, never anyone else's server). A port is taken fresh for
every start; only when the candidate's own stderr shows EADDRINUSE is a new port tried, up to PORT_ATTEMPTS times.

--selfcheck reads docs/experiments/parallel-plan-execution-20261114/real-repo/refs/*.patch, and reads (never writes)
test/shiploop_e2e/cases.json, test/shiploop_e2e/checks/ and test/shiploop_e2e/fixtures/node-tickets, to build its
scratch trees and to run each case's own `checks` list the way the harness runs it (SPEC "The promotion contract").
Nothing under test/shiploop_e2e is ever modified. Scratch trees go wherever Python's tempfile module is told to put
them (TMPDIR, or the platform default); run this with TMPDIR set to keep that off /tmp.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL_CRAFT_ROOT = HERE.parents[3]  # real-repo -> ...-20261114 -> experiments -> docs -> skill-craft root
E2E_DIR = SKILL_CRAFT_ROOT / "test" / "shiploop_e2e"
BASE_FIXTURE = E2E_DIR / "fixtures" / "node-tickets"
CASES_JSON = E2E_DIR / "cases.json"
CHECKS_DIR = E2E_DIR / "checks"
COMPOSED_PATCH = HERE / "refs" / "composed.patch"

READY_SECONDS = 10.0       # a ceiling for the candidate to start listening, not a tuning value
POLL_SECONDS = 0.1
STOP_SECONDS = 8.0         # a ceiling for a SIGTERM'd server to save and exit
HTTP_TIMEOUT = 5.0         # a ceiling per HTTP request
HARD_LIMIT_SECONDS = 60.0  # a ceiling for one whole check, server start and stop included
PORT_ATTEMPTS = 3          # retried only when the candidate's own stderr shows EADDRINUSE


# --------------------------------------------------------------------------------------------------------------
# Small helpers: time, ports, process groups


def iso(moment: datetime) -> str:
    moment = moment.astimezone(timezone.utc)
    return moment.strftime("%Y-%m-%dT%H:%M:%S.") + f"{moment.microsecond // 1000:03d}Z"


def parse_time(value) -> datetime | None:
    """An ISO 8601 time with a zone, or None."""
    if not isinstance(value, str):
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        moment = datetime.fromisoformat(text)
    except ValueError:
        return None
    return moment if moment.tzinfo is not None else None


def ms_between(a: datetime, b: datetime) -> float:
    return abs((a - b).total_seconds()) * 1000


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class CandidateError(RuntimeError):
    """A server this module started could not be used: it never listened, or answered something it should not."""


# --------------------------------------------------------------------------------------------------------------
# One service process, in its own process group, on a free port of its own


class Server:
    def __init__(self, tree: Path, data_file: Path, scratch: Path, label: str, *, due_times: str | None = "on",
                 worker_interval_ms: str = "50", notify_file: Path | None = None):
        self.tree = Path(tree)
        self.label = label
        if notify_file is None:
            notify_file = scratch / f"{label}-notify.jsonl"
        base_env = dict(os.environ)
        base_env["DATA_FILE"] = str(data_file)
        base_env["NOTIFY_FILE"] = str(notify_file)
        base_env["WORKER_INTERVAL_MS"] = worker_interval_ms
        if due_times is None:
            base_env.pop("DUE_TIMES", None)
        else:
            base_env["DUE_TIMES"] = due_times
        self.proc: subprocess.Popen | None = None
        self.port: int | None = None
        self.base: str | None = None
        self.stderr_path: Path | None = None
        last_detail = None
        for attempt in range(1, PORT_ATTEMPTS + 1):
            port = free_port()
            stderr_path = scratch / f"{label}.{attempt}.stderr"
            env = dict(base_env, PORT=str(port))
            handle = stderr_path.open("w")
            try:
                proc = subprocess.Popen(["node", "src/server.js"], cwd=str(self.tree), env=env,
                                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=handle,
                                         start_new_session=True)
            finally:
                handle.close()
            ok, detail = self._wait_listening(proc, port, stderr_path)
            if ok:
                self.proc, self.port, self.stderr_path = proc, port, stderr_path
                self.base = f"http://127.0.0.1:{port}"
                return
            self._end_group(proc)
            proc.wait()
            last_detail = detail
            if "EADDRINUSE" not in (detail or ""):
                raise CandidateError(f"{label}: {detail}")
        raise CandidateError(f"{label}: did not start after {PORT_ATTEMPTS} attempts on EADDRINUSE (last: {last_detail})")

    def _wait_listening(self, proc: subprocess.Popen, port: int, stderr_path: Path) -> tuple[bool, str | None]:
        deadline = time.monotonic() + READY_SECONDS
        while time.monotonic() < deadline:
            if proc.poll() is not None:
                return False, f"exited (rc {proc.returncode}) before listening on {port}: {self._tail(stderr_path)}"
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                    return True, None
            except OSError:
                time.sleep(POLL_SECONDS)
        return False, f"did not listen on {port} within {READY_SECONDS:.0f}s: {self._tail(stderr_path)}"

    @staticmethod
    def _tail(path: Path) -> str:
        try:
            return " ".join(path.read_text(errors="replace").split())[-600:] or "(no stderr)"
        except OSError:
            return "(stderr unreadable)"

    @staticmethod
    def _end_group(proc: subprocess.Popen) -> None:
        """SIGKILL the process group this Server started, and only that group."""
        try:
            pgid = os.getpgid(proc.pid)
        except ProcessLookupError:
            return
        if pgid != proc.pid:
            return  # it is not its own group leader: ending "its" group would reach something we did not start
        try:
            os.killpg(pgid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass

    def call(self, method: str, path: str, body=None, timeout: float = HTTP_TIMEOUT) -> tuple[int, object]:
        data = None if body is None else json.dumps(body).encode()
        headers = {"content-type": "application/json"} if data is not None else {}
        request = urllib.request.Request(self.base + path, method=method, data=data, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=timeout) as reply:
                return reply.status, json.loads(reply.read() or b"null")
        except urllib.error.HTTPError as error:
            raw = error.read()
            try:
                return error.code, json.loads(raw or b"null")
            except ValueError:
                return error.code, raw.decode(errors="replace")

    def listing(self, query: str = "") -> list[dict]:
        """Every ticket of GET /tickets?<query>, following `next` across pages."""
        items: list[dict] = []
        cursor = None
        for _ in range(100):
            params = query + ("&" if query else "") + "limit=100" + (f"&cursor={cursor}" if cursor else "")
            status, body = self.call("GET", "/tickets?" + params)
            if status != 200 or not isinstance(body, dict) or not isinstance(body.get("items"), list):
                raise CandidateError(f"{self.label}: GET /tickets?{params} answered {status} {str(body)[:200]}")
            items += body["items"]
            cursor = body.get("next")
            if not cursor:
                return items
            cursor = urllib.parse.quote(str(cursor), safe="")
        raise CandidateError(f"{self.label}: GET /tickets?{query} did not end within 100 pages")

    def stop(self) -> None:
        if self.proc is None:
            return
        if self.proc.poll() is None:
            self.proc.send_signal(signal.SIGTERM)
            try:
                self.proc.wait(timeout=STOP_SECONDS)
            except subprocess.TimeoutExpired:
                pass
        self._end_group(self.proc)
        if self.proc.poll() is None:
            self.proc.wait()


def fresh_data_file(scratch: Path, name: str = "data") -> Path:
    folder = scratch / name
    folder.mkdir(parents=True, exist_ok=True)
    return folder / "tickets.json"


def write_legacy_document(path: Path, tickets: list[dict], next_number: int) -> None:
    """A version-1 data file in the base's own persistence.js shape: no `assignee`, no `due` (I4's starting file)."""
    document = {"version": 1, "savedAt": iso(datetime.now(timezone.utc)), "nextNumber": next_number,
                "tickets": tickets, "audit": [], "outbox": {"nextId": 1, "events": []}}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2) + "\n")


# --------------------------------------------------------------------------------------------------------------
# I1-I5


def check_i1(tree: Path, scratch: Path) -> tuple[bool, str]:
    """Import x assignment: an import's tickets show `assignee` (present, null) and are found by the empty filter."""
    server = Server(tree, fresh_data_file(scratch), scratch, "I1")
    try:
        status, body = server.call("POST", "/tickets/import", {"tickets": [
            {"title": "Printer jam", "requester": "a@example.com", "priority": "urgent"},
            {"title": "New laptop request", "requester": "b@example.com", "priority": "low"},
        ]})
        if status != 201 or not isinstance(body, dict) or body.get("created") != 2 or \
                not isinstance(body.get("ids"), list) or len(body["ids"]) != 2:
            return False, f"POST /tickets/import answered {status} {str(body)[:300]}"
        ids = body["ids"]
        for ticket_id in ids:
            s, t = server.call("GET", "/tickets/" + ticket_id)
            if s != 200 or not isinstance(t, dict) or "assignee" not in t or t["assignee"] is not None:
                return False, f"GET /tickets/{ticket_id} answered {s} {str(t)[:300]} (want assignee present and null)"
        s, listed = server.call("GET", "/tickets?assignee=")
        if s != 200 or not isinstance(listed, dict) or not isinstance(listed.get("items"), list):
            return False, f"GET /tickets?assignee= answered {s} {str(listed)[:300]}"
        got_ids = {item.get("id") for item in listed["items"] if isinstance(item, dict)}
        if not set(ids) <= got_ids:
            return False, f"GET /tickets?assignee= lists {sorted(got_ids)}, missing {sorted(set(ids) - got_ids)}"
        return True, f"imported {ids}: both show assignee=null, both listed by assignee="
    finally:
        server.stop()


def check_i2(tree: Path, scratch: Path) -> tuple[bool, str]:
    """Due times x import: each imported ticket's `due` is its `created` plus its priority's hours."""
    server = Server(tree, fresh_data_file(scratch), scratch, "I2", due_times="on")
    try:
        status, body = server.call("POST", "/tickets/import", {"tickets": [
            {"title": "Printer jam", "requester": "a@example.com", "priority": "urgent"},
            {"title": "New laptop request", "requester": "b@example.com", "priority": "low"},
        ]})
        if status != 201 or not isinstance(body, dict) or len(body.get("ids") or []) != 2:
            return False, f"POST /tickets/import answered {status} {str(body)[:300]}"
        ids = body["ids"]
        hours = {ids[0]: ("urgent", 4), ids[1]: ("low", 168)}
        for ticket_id in ids:
            s, t = server.call("GET", "/tickets/" + ticket_id)
            if s != 200 or not isinstance(t, dict):
                return False, f"GET /tickets/{ticket_id} answered {s} {str(t)[:300]}"
            created, due = parse_time(t.get("created")), parse_time(t.get("due"))
            if created is None or due is None:
                return False, f"{ticket_id} shows created={t.get('created')!r} due={t.get('due')!r}"
            priority, want_hours = hours[ticket_id]
            want = created + timedelta(hours=want_hours)
            if ms_between(due, want) > 1000:
                return False, f"{ticket_id} ({priority}) created {t['created']} is due {t['due']}, not {iso(want)}"
        return True, "both imported tickets are due created + their priority's hours, within 1s"
    finally:
        server.stop()


def check_i3(tree: Path, scratch: Path) -> tuple[bool, str]:
    """Assignment x due times x import: assigning an imported ticket keeps its due time."""
    server = Server(tree, fresh_data_file(scratch), scratch, "I3", due_times="on")
    try:
        status, body = server.call("POST", "/tickets/import", {"tickets": [
            {"title": "Printer jam", "requester": "a@example.com", "priority": "high"},
        ]})
        if status != 201 or not (body.get("ids") if isinstance(body, dict) else None):
            return False, f"POST /tickets/import answered {status} {str(body)[:300]}"
        ticket_id = body["ids"][0]
        s, before = server.call("GET", "/tickets/" + ticket_id)
        if s != 200 or not isinstance(before, dict):
            return False, f"GET /tickets/{ticket_id} (before) answered {s} {str(before)[:300]}"
        if parse_time(before.get("due")) is None:
            return False, f"{ticket_id} shows due={before.get('due')!r} before assignment (want a valid ISO time)"
        s, put = server.call("PUT", f"/tickets/{ticket_id}/assignee", {"assignee": "dana"})
        if s != 200 or not isinstance(put, dict) or put.get("assignee") != "dana":
            return False, f"PUT /tickets/{ticket_id}/assignee answered {s} {str(put)[:300]}"
        s, after = server.call("GET", "/tickets/" + ticket_id)
        if s != 200 or not isinstance(after, dict) or after.get("assignee") != "dana":
            return False, f"GET /tickets/{ticket_id} (after) answered {s} {str(after)[:300]}"
        if parse_time(after.get("due")) is None:
            return False, f"{ticket_id} shows due={after.get('due')!r} after assignment (want a valid ISO time)"
        if before.get("due") != after.get("due"):
            return False, f"{ticket_id}'s due moved from {before.get('due')!r} to {after.get('due')!r} on assignment"
        return True, f"assigning imported {ticket_id} kept its valid due ({after.get('due')!r}) and set assignee=dana"
    finally:
        server.stop()


def check_i4(tree: Path, scratch: Path) -> tuple[bool, str]:
    """Assignment filter x overdue filter: both filters apply together, robust to which tickets are overdue versus
    merely assigned. Seeds four tickets so that "overdue" and "assignee" each split the set a different way:
    T-0001 (urgent, 10 days old: overdue) and T-0003 (low, 1 hour old: not overdue) go to dana; T-0002 (urgent, old:
    overdue) and T-0004 (low, recent: not overdue) stay unassigned. An implementation that drops either filter
    whenever the other is given would pass the single-filter checks but fail at least one of the four below."""
    data = fresh_data_file(scratch)
    old = iso(datetime.now(timezone.utc) - timedelta(days=10))
    recent = iso(datetime.now(timezone.utc) - timedelta(hours=1))
    write_legacy_document(data, [
        {"id": "T-0001", "title": "Old urgent, to be assigned", "priority": "urgent", "requester": "a@example.com",
         "status": "open", "created": old, "updated": old},
        {"id": "T-0002", "title": "Old urgent, stays unassigned", "priority": "urgent", "requester": "b@example.com",
         "status": "open", "created": old, "updated": old},
        {"id": "T-0003", "title": "Recent low, to be assigned", "priority": "low", "requester": "c@example.com",
         "status": "open", "created": recent, "updated": recent},
        {"id": "T-0004", "title": "Recent low, stays unassigned", "priority": "low", "requester": "d@example.com",
         "status": "open", "created": recent, "updated": recent},
    ], next_number=5)
    server = Server(tree, data, scratch, "I4", due_times="on")
    try:
        for ticket_id in ("T-0001", "T-0002", "T-0003", "T-0004"):
            s, t = server.call("GET", "/tickets/" + ticket_id)
            if s != 200 or not isinstance(t, dict) or t.get("due") is None:
                return False, f"GET /tickets/{ticket_id} answered {s} {str(t)[:300]} (want a due time from the migration)"
        for ticket_id in ("T-0001", "T-0003"):
            s, put = server.call("PUT", f"/tickets/{ticket_id}/assignee", {"assignee": "dana"})
            if s != 200 or not isinstance(put, dict) or put.get("assignee") != "dana":
                return False, f"PUT /tickets/{ticket_id}/assignee answered {s} {str(put)[:300]}"

        def ids_of(query: str) -> set:
            return {item.get("id") for item in server.listing(query) if isinstance(item, dict)}

        checks = [
            ("overdue=true&assignee=dana", {"T-0001"}),
            ("overdue=true&assignee=", {"T-0002"}),
            ("assignee=dana", {"T-0001", "T-0003"}),
            ("overdue=true", {"T-0001", "T-0002"}),
        ]
        for query, want in checks:
            got = ids_of(query)
            if got != want:
                return False, f"GET /tickets?{query} lists {sorted(got)}, not {sorted(want)}"
        return True, ("overdue&assignee=dana -> {T-0001}; overdue&assignee= -> {T-0002}; "
                       "assignee=dana -> {T-0001,T-0003}; overdue=true -> {T-0001,T-0002}")
    finally:
        server.stop()


def check_i5(tree: Path, scratch: Path) -> tuple[bool, str]:
    """Persistence across restart: an import's due times and an assignment both survive a restart."""
    data = fresh_data_file(scratch)
    first = Server(tree, data, scratch, "I5-first", due_times="on")
    try:
        status, body = first.call("POST", "/tickets/import", {"tickets": [
            {"title": "Printer jam", "requester": "a@example.com", "priority": "high"},
            {"title": "VPN drops", "requester": "b@example.com", "priority": "normal"},
        ]})
        if status != 201 or not isinstance(body, dict) or len(body.get("ids") or []) != 2:
            return False, f"POST /tickets/import answered {status} {str(body)[:300]}"
        ids = body["ids"]
        s, put = first.call("PUT", f"/tickets/{ids[0]}/assignee", {"assignee": "dana"})
        if s != 200 or not isinstance(put, dict) or put.get("assignee") != "dana":
            return False, f"PUT /tickets/{ids[0]}/assignee answered {s} {str(put)[:300]}"
        before = {}
        for ticket_id in ids:
            s, t = first.call("GET", "/tickets/" + ticket_id)
            if s != 200 or not isinstance(t, dict):
                return False, f"GET /tickets/{ticket_id} (before restart) answered {s} {str(t)[:300]}"
            # Required BEFORE the restart, not just after: a backfill triggered by the restart itself must not be
            # able to masquerade as "the due time was preserved" when it was never there to begin with.
            if parse_time(t.get("due")) is None:
                return False, f"{ticket_id} shows due={t.get('due')!r} before the restart (want a valid ISO time)"
            before[ticket_id] = t
    finally:
        first.stop()
    second = Server(tree, data, scratch, "I5-second", due_times="on")
    try:
        want_assignee = {ids[0]: "dana", ids[1]: None}
        for ticket_id in ids:
            s, got = second.call("GET", "/tickets/" + ticket_id)
            if s != 200 or not isinstance(got, dict):
                return False, f"GET /tickets/{ticket_id} (after restart) answered {s} {str(got)[:300]}"
            if parse_time(got.get("due")) is None:
                return False, f"{ticket_id} shows due={got.get('due')!r} after restart (want a valid ISO time)"
            if got.get("due") != before[ticket_id].get("due"):
                return False, (f"{ticket_id}'s due changed from {before[ticket_id].get('due')!r} to "
                                f"{got.get('due')!r} across the restart")
            if got.get("assignee") != want_assignee[ticket_id]:
                return False, f"{ticket_id}'s assignee is {got.get('assignee')!r} after restart, not {want_assignee[ticket_id]!r}"
        return True, (f"both imported tickets had a valid due before the restart and the identical due after it; "
                       f"{ids[0]}'s assignment to dana survived")
    finally:
        second.stop()


CHECKS = {"I1": check_i1, "I2": check_i2, "I3": check_i3, "I4": check_i4, "I5": check_i5}


def probe_can_start(tree: Path, scratch: Path) -> str | None:
    """Try starting a plain `node src/server.js` from `tree` once, with no feature exercised. None if it listens;
    otherwise the failure detail. Used so `check` can report one clean error instead of five identical per-check
    "could not start a server" failures when the tree cannot run at all (missing `node`, a broken `src/server.js`,
    and the like)."""
    try:
        server = Server(tree, fresh_data_file(scratch, "probe"), scratch, "startup-probe")
    except CandidateError as exc:
        return str(exc)
    server.stop()
    return None


def run_interaction_checks(tree: Path) -> dict:
    """{"I1": {"ok", "detail"}, ..., "I5": {...}} for `tree`. Each check gets its own scratch folder and time limit."""
    results = {}
    for name, fn in CHECKS.items():
        with tempfile.TemporaryDirectory(prefix=f"interactions-{name}-") as raw_scratch:
            scratch = Path(raw_scratch)
            started = time.monotonic()
            try:
                ok, detail = fn(tree, scratch)
            except Exception as exc:  # noqa: BLE001 - a check's own failure is a result, not a crash
                ok, detail = False, f"{type(exc).__name__}: {exc}"
            elapsed = time.monotonic() - started
            if elapsed > HARD_LIMIT_SECONDS:
                detail = f"{detail} (took {elapsed:.1f}s, over the {HARD_LIMIT_SECONDS:.0f}s ceiling)"
            results[name] = {"ok": bool(ok), "detail": str(detail)}
    return results


# --------------------------------------------------------------------------------------------------------------
# --selfcheck: scratch copies, the three cases' own checks, three single-point mutations


def _copy_base(scratch: Path, name: str) -> Path:
    tree = scratch / name
    shutil.copytree(BASE_FIXTURE, tree, ignore=shutil.ignore_patterns(".git"))
    return tree


def apply_patch(tree: Path, patch: Path) -> None:
    done = subprocess.run(["git", "apply", str(patch)], cwd=str(tree), capture_output=True, text=True)
    if done.returncode != 0:
        raise RuntimeError(f"git apply {patch} failed in {tree}: {done.stderr[-2000:]}")


_MUTATION_A_EDIT = (
    "    const ids = inputs.map((input) => this.createRecorded(input, actor).id);",
    "    const ids = inputs.map((input) => {\n"
    "      const id = this.createRecorded(input, actor).id;\n"
    "      delete this.tickets.get(id).due; // MUTATION (a): import bypasses the code that sets due\n"
    "      return id;\n"
    "    });",
)

# Each mutation is one (file, [(old, new), ...], description); every (old, new) is an exact-substring replacement,
# applied in order, each required to be found (an outdated string fails loudly instead of silently no-op'ing).
MUTATIONS = {
    "a": ("src/store.js", [_MUTATION_A_EDIT],
          "imported tickets get no due (import bypasses the code that sets it)"),
    # (d) is the same code change as (a), kept as its own labelled tree: the coordinator asked for it by name, and
    # for it to be re-checked against the now-stricter I3/I5 (see selfcheck()'s TARGETED table and REPORT.md).
    "d": ("src/store.js", [_MUTATION_A_EDIT],
          "(same change as (a)) imported tickets get no due"),
    "b": ("src/store.js", [(
          "      .filter((ticket) => matchesFilters(ticket, filters))\n"
          "      .filter((ticket) => overdue !== true || (isActive(ticket.status) && now > ticket.due))",
          "      // MUTATION (b): overdue overrides the other filters instead of being combined with them\n"
          "      .filter((ticket) => (overdue === true ? (isActive(ticket.status) && now > ticket.due)"
          " : matchesFilters(ticket, filters)))",
    )], "the assignee and overdue filters are not combined (overdue overrides assignee)"),
    "e": ("src/store.js", [(
          "    const now = overdue === true ? this.now() : null;\n"
          "    const matching = [...this.tickets.values()]\n"
          "      .filter((ticket) => matchesFilters(ticket, filters))\n"
          "      .filter((ticket) => overdue !== true || (isActive(ticket.status) && now > ticket.due))\n",
          "    // MUTATION (e): overdue is ignored whenever assignee is present\n"
          "    const effectiveOverdue = filters.assignee !== undefined ? undefined : overdue;\n"
          "    const now = effectiveOverdue === true ? this.now() : null;\n"
          "    const matching = [...this.tickets.values()]\n"
          "      .filter((ticket) => matchesFilters(ticket, filters))\n"
          "      .filter((ticket) => effectiveOverdue !== true || (isActive(ticket.status) && now > ticket.due))\n",
    )], "overdue is ignored whenever assignee is present"),
    "c": ("src/persistence.js", [(
          "    assignee: ticket.assignee === undefined ? null : ticket.assignee,\n",
          "    assignee: null, // MUTATION (c): assignments are never written to (or read back from) the data file\n",
    )], "assignments are not saved to the data file"),
    "f": ("src/store.js", [
          (
              "    this.outbox = new Outbox(initial.outbox);\n"
              "    this.hours = hours;\n"
              "  }",
              "    this.outbox = new Outbox(initial.outbox);\n"
              "    this.hours = hours;\n"
              "    // MUTATION (f): due is recomputed from this server's own start time on every read, not kept\n"
              "    this.sessionStarted = this.now();\n"
              "  }",
          ),
          (
              "  get(id) {\n"
              "    return { ...this.find(id) };\n"
              "  }",
              "  get(id) {\n"
              "    const ticket = this.find(id);\n"
              "    return { ...ticket, due: this.dueFrom(this.sessionStarted, ticket.priority) };\n"
              "  }",
          ),
    ], "due is recomputed from the current time on every read instead of kept"),
}


def build_mutation_tree(scratch: Path, name: str, composed_patch: Path) -> Path:
    label, edits, _description = MUTATIONS[name]
    tree = _copy_base(scratch, f"mutation-{name}")
    apply_patch(tree, composed_patch)
    path = tree / label
    text = path.read_text()
    for old, new in edits:
        if old not in text:
            raise RuntimeError(f"mutation ({name}): expected source not found in {label}")
        text = text.replace(old, new, 1)
    path.write_text(text)
    return tree


def load_case_checks(case_id: str) -> list[str]:
    cases = json.loads(CASES_JSON.read_text())
    return cases[case_id]["checks"]


def run_case_checks(tree: Path, case_id: str, cache: dict[str, dict]) -> list[dict]:
    """Run case_id's own `checks` list the way the harness runs it: each command from TREE with E2E_CHECKS set.
    `cache` is shared across cases run against the same tree, so an identical command (the suite and pristine
    checks are the same text in all three cases) runs once per tree."""
    out = []
    for command in load_case_checks(case_id):
        if command not in cache:
            env = dict(os.environ, E2E_CHECKS=str(CHECKS_DIR))
            try:
                done = subprocess.run(command, shell=True, cwd=str(tree), env=env, capture_output=True, text=True,
                                       timeout=180)
                cache[command] = {"pass": done.returncode == 0, "returncode": done.returncode,
                                   "output": (done.stdout + done.stderr).strip()[-400:]}
            except subprocess.TimeoutExpired:
                cache[command] = {"pass": False, "returncode": None, "output": "timed out"}
        out.append(dict(cache[command], command=command))
    return out


# Expected outcomes. I1-I5 need no feature the bare base has, so the base is expected to fail every one of them (each
# check opens with POST /tickets/import, a route the base does not have). The composed tree is expected to pass all
# five. "ticket-due-times off" is the one case check expected to fail on the composed tree: it demands the delivered
# service answer *exactly* as 1.4.0 while DUE_TIMES is unset/off, but the composed tree also carries the assignment
# feature's `assignee` field unconditionally (per ticket-assignment's own contract, "Every ticket shows its
# assignee" - that field is not gated by DUE_TIMES), so no composed delivery of more than the due-times feature alone
# can pass that single-feature-isolation probe. See REPORT.md, "The one check that cannot pass composed".
EXPECTED_INTERACTIONS = {"composed": True, "base": False}
# For the bare base run against itself: suite needs more passing tests than the base has (none added -> fails);
# pristine, rollback, off and cli compare the delivery with 1.4.0 and the base trivially equals itself (-> pass);
# migrate/restart/switch need `due` to appear, which the base never produces (-> fail, as the case's own calibration
# note records: "the base fails exactly migrate, restart and switch").
EXPECTED_CASE_CHECKS = {
    "composed": {
        "suite": True, "pristine": True, "http-check (import)": True, "http-check (assignment)": True,
        "due_times_probe.py migrate": True, "due_times_probe.py restart": True, "due_times_probe.py switch": True,
        "due_times_probe.py rollback": True, "due_times_probe.py off": False, "due_times_probe.py cli": True,
    },
    "base": {
        "suite": False, "pristine": True, "http-check (import)": False, "http-check (assignment)": False,
        "due_times_probe.py migrate": False, "due_times_probe.py restart": False, "due_times_probe.py switch": False,
        "due_times_probe.py rollback": True, "due_times_probe.py off": True, "due_times_probe.py cli": True,
    },
}


def expected_for(tree_label: str, short: str) -> bool | None:
    return EXPECTED_CASE_CHECKS.get(tree_label, {}).get(short)


def selfcheck() -> int:
    rows = []  # (tree, check, expected, observed, detail)
    with tempfile.TemporaryDirectory(prefix="interactions-selfcheck-") as raw_scratch:
        scratch = Path(raw_scratch)
        if not COMPOSED_PATCH.is_file():
            print(f"FAIL: {COMPOSED_PATCH} is missing; build refs/composed.patch first")
            return 1

        composed_tree = _copy_base(scratch, "composed")
        apply_patch(composed_tree, COMPOSED_PATCH)
        base_tree = _copy_base(scratch, "base")

        trees = {"composed": composed_tree, "base": base_tree}
        for mutation in sorted(MUTATIONS):
            trees[f"mutation-{mutation}"] = build_mutation_tree(scratch, mutation, COMPOSED_PATCH)

        # Each mutation is meant to break one or more checks; every other check is expected to keep passing.
        # (a)/(d) (the same code change, checked twice by name) now break I2, I3 *and* I5: with the stricter I3/I5
        # (due required valid *before* the action they check, not just "present or absent on both sides"), deleting
        # due at import is caught everywhere it matters, not only by I2 as it was before those checks were tightened.
        TARGETED = {"a": {"I2", "I3", "I5"}, "d": {"I2", "I3", "I5"}, "b": {"I4"}, "e": {"I4"}, "c": {"I5"}, "f": {"I5"}}
        for label, tree in trees.items():
            print(f"-- {label}: {tree}", file=sys.stderr)
            results = run_interaction_checks(tree)
            for check, result in results.items():
                if label in EXPECTED_INTERACTIONS:
                    expected = EXPECTED_INTERACTIONS[label]
                elif label.startswith("mutation-"):
                    name = label.split("-", 1)[1]
                    expected = check not in TARGETED[name]
                else:
                    expected = None
                rows.append((label, check, expected, result["ok"], result["detail"]))

        for label in ("composed", "base"):
            cache: dict[str, dict] = {}  # one cache per tree: the same command text must still be re-run per tree
            for case_id in ("ticket-assignment", "ticket-import", "ticket-due-times"):
                for entry in run_case_checks(trees[label], case_id, cache):
                    short = short_command(entry["command"])
                    expected = expected_for(label, short)
                    rows.append((label, f"{case_id}:{short}", expected, entry["pass"], entry["output"][:160]))

    print()
    header = f"{'tree':<12} {'check':<40} {'expected':<9} {'observed':<9} detail"
    print(header)
    print("-" * len(header))
    mismatches = 0
    for tree, check, expected, observed, detail in rows:
        exp_text = "PASS" if expected is True else ("FAIL" if expected is False else "?")
        obs_text = "PASS" if observed else "FAIL"
        marker = "" if expected is None or expected == observed else "  <-- MISMATCH"
        if marker:
            mismatches += 1
        print(f"{tree:<12} {check:<40} {exp_text:<9} {obs_text:<9} {detail[:100]}{marker}")
    print()
    print(f"{mismatches} mismatch(es) against the documented expectation (ticket-due-times:off on composed is an "
          "expected, documented exception - see REPORT.md)")
    return 1 if mismatches else 0


def short_command(command: str) -> str:
    if "base_tests.py" in command:
        return "suite" if " suite " in command else "pristine" if " pristine " in command else command
    if "due_times_probe.py" in command:
        mode = command.strip().split()[-1]
        return f"due_times_probe.py {mode}"
    if "serve.py" in command:
        if "/tickets/import" in command:
            return "http-check (import)"
        if "/assignee" in command:
            return "http-check (assignment)"
        return "http-check"
    return command[:40]


# --------------------------------------------------------------------------------------------------------------
# CLI


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command")
    check_parser = sub.add_parser("check", help="print I1-I5 for TREE as one JSON object")
    check_parser.add_argument("tree", help="a delivered node-tickets tree (e.g. refs/composed.patch applied to the base)")
    parser.add_argument("--selfcheck", action="store_true", help="run against scratch copies and print a table")
    args = parser.parse_args(argv)

    if args.selfcheck:
        return selfcheck()
    if args.command == "check":
        tree = Path(args.tree).resolve()
        if not (tree / "src" / "server.js").is_file():
            print(json.dumps({"error": f"{tree} has no src/server.js"}, indent=2))
            return 1
        with tempfile.TemporaryDirectory(prefix="interactions-probe-") as raw_scratch:
            failure = probe_can_start(tree, Path(raw_scratch))
        if failure is not None:
            print(json.dumps({"error": f"could not start a server from {tree}: {failure}"}, indent=2))
            return 1
        results = run_interaction_checks(tree)
        print(json.dumps(results, indent=2))
        return 0 if all(result["ok"] for result in results.values()) else 1
    parser.print_help(sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
