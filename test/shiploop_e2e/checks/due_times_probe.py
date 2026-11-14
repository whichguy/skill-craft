#!/usr/bin/env python3
"""Held-out probes of the `ticket-due-times` case: does the delivered ticket service migrate the tickets it finds in a
data file the current release (1.4.0, the case's base) wrote, keep their due times, switch on only with DUE_TIMES=on, and
leave a data file that 1.4.0 can still start on?

    python3 "$E2E_CHECKS/due_times_probe.py" MODE          (from the delivery's work directory)

MODE is one of `migrate`, `restart`, `switch`, `rollback`, `off`, `cli`. Each builds its own data file in a scratch
folder, starts the servers it needs on free ports with WORKER_INTERVAL_MS=0 (no background delivery), stops each with SIGTERM
as an operator's service manager does (docs/operations.md: "SIGTERM stops it cleanly ... the state is saved"), and exits 0
when every expectation holds, else 1 after one `FAIL:` line per broken expectation.

The data file is what the base writes: format version 1, eight tickets (T-0001 to T-0008), their audit entries and an
empty outbox. T-0001 to T-0006 were created in September 2025; T-0007 (low) an hour ago, T-0008 (urgent) five hours ago,
so at the requested default hours (urgent 4, high 24, normal 72, low 168) the overdue ones are the open and in-progress
T-0001, T-0002, T-0003, T-0006 and T-0008, and not T-0004 (resolved), T-0005 (closed) or T-0007 (due in 167 hours).

* `migrate`: DUE_TIMES=on on that file. Every ticket shows `due` (an ISO 8601 time), equal to its creation time plus its
  priority's default hours, on GET /tickets/:id and in the listing; `GET /tickets?overdue=true` lists exactly the overdue
  ones above; a new urgent ticket's `due` is its `created` plus 4 hours, and it is not overdue.
* `restart`: DUE_TIMES=on; the due times seen after a first start and a new ticket stay the same after a restart over the
  same file, after a priority change of T-0003 (normal to urgent) and after a second restart.
* `switch`: a first start with DUE_TIMES unset, a ticket made then, a restart with DUE_TIMES=on: every ticket, the one made
  while off included, shows the due time its creation time and priority give.
* `rollback`: the delivered release runs over the file (once with DUE_TIMES unset, once with DUE_TIMES=on) and makes a ticket;
  then the base, 1.4.0, starts over the file it left and lists every ticket. "operators must be able to go back to the current
  release, 1.4.0, and it must still start on the data file the new release wrote and show every ticket."
* `off`: with DUE_TIMES unset, and again with DUE_TIMES=off, the delivered service answers the same requests as the base
  over copies of the same file with the same statuses and bodies (times of the moment normalised): no `due`, `overdue` ignored
  as the base ignores an unknown parameter, and a `due` field in a request body refused as the base refuses unknown fields.
* `cli`: after the delivered service ran with DUE_TIMES=on over the file, `bin/tickets.js list --raw` keeps the base's first
  four columns (id, status, priority, title) line for line, which scripts/weekly-report.js reads by position, and
  `scripts/weekly-report.js --json` reports the same counts as the base over the original file.

The probe reads the delivery's work directory and the base fixture only; it writes into its own scratch folder. Every
wait is a ceiling, not a tuning value.
"""

from __future__ import annotations

import datetime as dt
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import serve  # noqa: E402  (free_port and the candidate-ownership wait: one implementation of both)

BASE = HERE.parent / "fixtures" / "node-tickets"
HOURS = {"urgent": 4, "high": 24, "normal": 72, "low": 168}
STOP_SECONDS = 8.0      # a ceiling for a SIGTERM'd server to save and exit
TOLERANCE_MS = 1000     # a due computed from a second clock reading may differ from `created` by this much
# Variables the probe sets itself or that would change what it observes; dropped from the inherited environment.
SCRUB = ("DATA_FILE", "NOTIFY_FILE", "DUE_TIMES", "PORT", "BASE", "WORKER_INTERVAL_MS", "LOG_REQUESTS", "MAX_BODY_BYTES")

FAILURES: list[str] = []


def fail(message: str) -> None:
    FAILURES.append(message)
    print("FAIL: " + message, flush=True)


def iso(moment: dt.datetime) -> str:
    return moment.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.") + f"{moment.microsecond // 1000:03d}Z"


def parse_time(value) -> dt.datetime | None:
    """An ISO 8601 time with a zone (the API's convention, docs/api.md "Times"), or None."""
    if not isinstance(value, str):
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        moment = dt.datetime.fromisoformat(text)
    except ValueError:
        return None
    return moment if moment.tzinfo is not None else None


def ms_between(a: dt.datetime, b: dt.datetime) -> float:
    return abs((a - b).total_seconds()) * 1000


# The data file 1.4.0 writes

def base_document(now: dt.datetime) -> dict:
    """A version-1 data file as the base's src/persistence.js writes it, with times relative to `now` for T-0007 and T-0008."""
    recent = now.replace(microsecond=0)
    rows = [
        ("T-0001", "Printer on the second floor jams", "urgent", "ana@example.com", "open", "2025-09-01T08:00:00.000Z",
         "2025-09-01T08:00:00.000Z"),
        ("T-0002", "VPN drops every hour", "high", "ben@example.com", "in_progress", "2025-09-02T09:30:00.000Z",
         "2025-09-02T10:00:00.000Z"),
        ("T-0003", "New starter needs a laptop", "normal", "cy@example.com", "open", "2025-09-03T10:15:00.000Z",
         "2025-09-03T10:15:00.000Z"),
        ("T-0004", "Mailbox is full", "low", "dee@example.com", "resolved", "2025-09-04T11:45:00.000Z",
         "2025-09-05T09:00:00.000Z"),
        ("T-0005", "Projector bulb is out", "urgent", "eve@example.com", "closed", "2025-09-05T13:20:00.000Z",
         "2025-09-06T08:00:00.000Z"),
        ("T-0006", "Shared drive is slow", "low", "fay@example.com", "open", "2025-09-06T15:05:00.000Z",
         "2025-09-06T15:05:00.000Z"),
        ("T-0007", "Monitor flickers", "low", "gus@example.com", "open", iso(recent - dt.timedelta(hours=1)),
         iso(recent - dt.timedelta(hours=1))),
        ("T-0008", "Payroll system is down", "urgent", "hal@example.com", "in_progress", iso(recent - dt.timedelta(hours=5)),
         iso(recent - dt.timedelta(hours=4))),
    ]
    tickets, audit = [], []
    for ticket_id, title, priority, requester, status, created, updated in rows:
        tickets.append({"id": ticket_id, "title": title, "priority": priority, "requester": requester, "status": status,
                        "created": created, "updated": updated})
        audit.append({"seq": len(audit) + 1, "ticket": ticket_id, "action": "ticket.created", "actor": "system", "at": created,
                      "changes": {"title": {"from": None, "to": title}, "priority": {"from": None, "to": priority},
                                  "requester": {"from": None, "to": requester}, "status": {"from": None, "to": "open"}}})
    moves = {"T-0002": ["in_progress"], "T-0004": ["in_progress", "resolved"], "T-0005": ["in_progress", "resolved", "closed"],
             "T-0008": ["in_progress"]}
    for ticket in tickets:
        before = "open"
        for after in moves.get(ticket["id"], []):
            audit.append({"seq": len(audit) + 1, "ticket": ticket["id"], "action": "ticket.transitioned", "actor": "dana",
                          "at": ticket["updated"], "changes": {"status": {"from": before, "to": after}}})
            before = after
    return {"version": 1, "savedAt": iso(recent - dt.timedelta(minutes=30)), "nextNumber": 9, "tickets": tickets,
            "audit": audit, "outbox": {"nextId": 1, "events": []}}


def expected_due(ticket: dict) -> dt.datetime:
    return parse_time(ticket["created"]) + dt.timedelta(hours=HOURS[ticket["priority"]])


# Servers

class Server:
    """One service process on a free port of its own, started from `root` over `data`, stopped with SIGTERM."""

    def __init__(self, root: Path, data: Path, scratch: Path, label: str, **env: str | None):
        self.label = label
        self.port = serve.free_port()
        self.base = f"http://127.0.0.1:{self.port}"
        clean = {key: value for key, value in os.environ.items() if key not in SCRUB}
        clean.update(PORT=str(self.port), DATA_FILE=str(data), WORKER_INTERVAL_MS="0")
        clean.update({key: value for key, value in env.items() if value is not None})
        self.stderr = scratch / f"{label}.stderr"
        with self.stderr.open("w") as err:
            self.proc = subprocess.Popen(["node", "src/server.js"], cwd=root, env=clean, stdin=subprocess.DEVNULL,
                                         stdout=subprocess.DEVNULL, stderr=err, start_new_session=True)
        try:
            serve.wait_for_candidate(self.proc, self.port, self.stderr)  # exits 1 with a FAIL line when it never listens
        except SystemExit:
            print(f"(the {label} server did not start)", flush=True)
            serve.listeners.end_group(self.proc.pid)
            self.proc.wait()
            raise

    def call(self, method: str, path: str, body=None) -> tuple[int, object]:
        data = None if body is None else json.dumps(body).encode()
        request = urllib.request.Request(self.base + path, method=method, data=data,
                                         headers={"content-type": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=10) as reply:
                return reply.status, json.loads(reply.read() or b"null")
        except urllib.error.HTTPError as error:
            raw = error.read()
            try:
                return error.code, json.loads(raw or b"null")
            except ValueError:
                return error.code, raw.decode(errors="replace")

    def listing(self, query: str = "") -> list[dict] | None:
        """Every ticket of GET /tickets?<query>, following `next` across pages; None when a page is not a listing."""
        items, cursor = [], None
        for _ in range(100):
            params = query + ("&" if query else "") + f"limit=100" + (f"&cursor={cursor}" if cursor else "")
            status, body = self.call("GET", "/tickets?" + params)
            if status != 200 or not isinstance(body, dict) or not isinstance(body.get("items"), list):
                fail(f"{self.label}: GET /tickets?{params} answered {status} {str(body)[:200]}")
                return None
            items += body["items"]
            cursor = body.get("next")
            if not cursor:
                return items
            cursor = urllib.parse.quote(str(cursor), safe="")
        fail(f"{self.label}: GET /tickets?{query} did not end within 100 pages")
        return None

    def stop(self) -> None:
        if self.proc.poll() is None:
            self.proc.send_signal(signal.SIGTERM)
            try:
                self.proc.wait(timeout=STOP_SECONDS)
            except subprocess.TimeoutExpired:
                fail(f"{self.label}: still running {STOP_SECONDS:.0f} s after SIGTERM")
        serve.listeners.end_group(self.proc.pid)
        if self.proc.poll() is None:
            self.proc.wait()

    def tail(self) -> str:
        return serve.tail(self.stderr)


def started(root: Path, data: Path, scratch: Path, label: str, **env: str | None) -> Server:
    return Server(root, data, scratch, label, **env)


# Expectations

def check_due(server: Server, tickets: list[dict], where: str) -> dict:
    """Every ticket of `tickets` shows the due time its creation time and priority give, on GET /tickets/:id and in the
    listing; returns {id: due as shown}."""
    shown = {}
    listed = {ticket.get("id"): ticket for ticket in (server.listing() or []) if isinstance(ticket, dict)}
    for ticket in tickets:
        status, body = server.call("GET", "/tickets/" + ticket["id"])
        if status != 200 or not isinstance(body, dict):
            fail(f"{where}: GET /tickets/{ticket['id']} answered {status} {str(body)[:200]}")
            continue
        want = expected_due(ticket)
        due = parse_time(body.get("due"))
        if "due" not in body:
            fail(f"{where}: {ticket['id']} ({ticket['priority']}, created {ticket['created']}) shows no `due`")
        elif due is None:
            fail(f"{where}: {ticket['id']}'s due {body.get('due')!r} is not an ISO 8601 time with a zone")
        elif ms_between(due, want) > TOLERANCE_MS:
            fail(f"{where}: {ticket['id']} ({ticket['priority']}, created {ticket['created']}) is due {body.get('due')}, "
                 f"not {iso(want)}")
        shown[ticket["id"]] = body.get("due")
        row = listed.get(ticket["id"])
        if row is None:
            fail(f"{where}: {ticket['id']} is not in the listing")
        elif row.get("due") != body.get("due"):
            fail(f"{where}: {ticket['id']} is due {row.get('due')!r} in the listing but {body.get('due')!r} on its own")
    return shown


def overdue_ids(server: Server, where: str) -> set | None:
    items = server.listing("overdue=true")
    if items is None:
        return None
    return {item.get("id") for item in items if isinstance(item, dict)}


def make_ticket(server: Server, where: str, priority: str) -> dict | None:
    status, body = server.call("POST", "/tickets", {"title": f"Probe ticket ({priority})", "requester": "probe@example.com",
                                                     "priority": priority})
    if status != 201 or not isinstance(body, dict) or "id" not in body:
        fail(f"{where}: POST /tickets answered {status} {str(body)[:200]}")
        return None
    return body


def write(path: Path, document: dict) -> None:
    path.write_text(json.dumps(document, indent=2) + "\n")


# Modes

def mode_migrate(work: Path, scratch: Path) -> None:
    now = dt.datetime.now(dt.timezone.utc)
    document = base_document(now)
    data = scratch / "tickets.json"
    write(data, document)
    server = started(work, data, scratch, "delivery DUE_TIMES=on", DUE_TIMES="on")
    try:
        check_due(server, document["tickets"], "migrate")
        want = {"T-0001", "T-0002", "T-0003", "T-0006", "T-0008"}
        got = overdue_ids(server, "migrate")
        if got is not None and got != want:
            fail(f"migrate: GET /tickets?overdue=true lists {sorted(got)}, not {sorted(want)} (missing {sorted(want - got)}, "
                 f"extra {sorted(got - want)})")
        made = make_ticket(server, "migrate", "urgent")
        if made is not None:
            created, due = parse_time(made.get("created")), parse_time(made.get("due"))
            if due is None or created is None:
                fail(f"migrate: the new ticket {made.get('id')} shows due {made.get('due')!r}, created {made.get('created')!r}")
            elif ms_between(due, created + dt.timedelta(hours=4)) > TOLERANCE_MS:
                fail(f"migrate: the new urgent ticket {made.get('id')} was created {made.get('created')} and is due "
                     f"{made.get('due')}, not 4 hours later")
            again = overdue_ids(server, "migrate")
            if again is not None and made.get("id") in again:
                fail(f"migrate: the new ticket {made.get('id')}, due in 4 hours, is listed as overdue")
    finally:
        server.stop()


def mode_restart(work: Path, scratch: Path) -> None:
    now = dt.datetime.now(dt.timezone.utc)
    document = base_document(now)
    data = scratch / "tickets.json"
    write(data, document)
    first = started(work, data, scratch, "first start", DUE_TIMES="on")
    try:
        seen = check_due(first, document["tickets"], "restart, first start")
        made = make_ticket(first, "restart, first start", "high")
        if made is not None:
            seen[made["id"]] = made.get("due")
    finally:
        first.stop()
    second = started(work, data, scratch, "second start", DUE_TIMES="on")
    try:
        compare(second, seen, "restart, after a restart")
        status, body = second.call("PATCH", "/tickets/T-0003", {"priority": "urgent"})
        if status != 200 or not isinstance(body, dict):
            fail(f"restart: PATCH /tickets/T-0003 priority urgent answered {status} {str(body)[:200]}")
        elif parse_time(body.get("due")) is None or parse_time(seen.get("T-0003")) is None or \
                ms_between(parse_time(body.get("due")), parse_time(seen.get("T-0003"))) > 0:
            fail(f"restart: T-0003's priority change moved its due time from {seen.get('T-0003')} to {body.get('due')}")
        compare(second, seen, "restart, after a priority change")
    finally:
        second.stop()
    third = started(work, data, scratch, "third start", DUE_TIMES="on")
    try:
        compare(third, seen, "restart, after a second restart")
    finally:
        third.stop()


def compare(server: Server, seen: dict, where: str) -> None:
    for ticket_id, due in seen.items():
        status, body = server.call("GET", "/tickets/" + ticket_id)
        if status != 200 or not isinstance(body, dict):
            fail(f"{where}: GET /tickets/{ticket_id} answered {status} {str(body)[:200]}")
        elif parse_time(body.get("due")) is None or parse_time(due) is None or \
                ms_between(parse_time(body.get("due")), parse_time(due)) > 0:
            fail(f"{where}: {ticket_id} is due {body.get('due')!r}, not {due!r} as before")


def mode_switch(work: Path, scratch: Path) -> None:
    now = dt.datetime.now(dt.timezone.utc)
    document = base_document(now)
    data = scratch / "tickets.json"
    write(data, document)
    off = started(work, data, scratch, "DUE_TIMES unset")
    try:
        made = make_ticket(off, "switch, while off", "normal")
    finally:
        off.stop()
    on = started(work, data, scratch, "DUE_TIMES=on", DUE_TIMES="on")
    try:
        tickets = list(document["tickets"]) + ([{"id": made["id"], "priority": "normal", "created": made["created"]}]
                                               if made and parse_time(made.get("created")) else [])
        check_due(on, tickets, "switch, after DUE_TIMES=on")
    finally:
        on.stop()


def mode_rollback(work: Path, scratch: Path) -> None:
    for label, env in (("DUE_TIMES unset", {}), ("DUE_TIMES=on", {"DUE_TIMES": "on"})):
        now = dt.datetime.now(dt.timezone.utc)
        document = base_document(now)
        folder = scratch / ("on" if env else "off")
        folder.mkdir()
        data = folder / "tickets.json"
        write(data, document)
        delivered = started(work, data, folder, f"delivery, {label}", **env)
        try:
            made = make_ticket(delivered, f"rollback ({label})", "normal")
        finally:
            delivered.stop()
        want = {ticket["id"] for ticket in document["tickets"]} | ({made["id"]} if made else set())
        try:
            back = started(BASE, data, folder, f"1.4.0 after the delivery ran with {label}")
        except SystemExit:
            fail(f"rollback ({label}): 1.4.0 does not start on the data file the new release wrote")
            continue
        try:
            got = {item.get("id") for item in (back.listing() or []) if isinstance(item, dict)}
            if got != want:
                fail(f"rollback ({label}): 1.4.0 lists {sorted(got)}, not every ticket {sorted(want)}")
            for ticket_id in sorted(want):
                status, _body = back.call("GET", "/tickets/" + ticket_id)
                if status != 200:
                    fail(f"rollback ({label}): 1.4.0 answers {status} for GET /tickets/{ticket_id}")
        finally:
            back.stop()


TIME = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})$")


def normalised(value, since: dt.datetime):
    """The body with every time later than `since` (a time of the moment of this probe) replaced by a placeholder."""
    if isinstance(value, dict):
        return {key: normalised(item, since) for key, item in value.items()}
    if isinstance(value, list):
        return [normalised(item, since) for item in value]
    if isinstance(value, str) and TIME.match(value):
        moment = parse_time(value)
        if moment is not None and moment >= since:
            return "<a time of the probe>"
    return value


FLAG_OFF_REQUESTS = (
    ("GET", "/tickets", None),
    ("GET", "/tickets?overdue=true", None),
    ("GET", "/tickets?status=open", None),
    ("GET", "/tickets?priority=low", None),
    ("GET", "/tickets?limit=3", None),
    ("GET", "/tickets/T-0001", None),
    ("GET", "/tickets/T-0008", None),
    ("GET", "/tickets/T-0099", None),
    ("GET", "/tickets/T-0005/audit", None),
    ("POST", "/tickets", {"title": "Keyboard is missing keys", "requester": "ivy@example.com", "priority": "high"}),
    ("POST", "/tickets", {"title": "Due given by a client", "requester": "ivy@example.com", "due": "2030-01-01T00:00:00.000Z"}),
    ("PATCH", "/tickets/T-0003", {"priority": "high"}),
    ("POST", "/tickets/T-0001/transition", {"to": "in_progress"}),
    ("GET", "/tickets/T-0009", None),
    ("GET", "/tickets", None),
    ("GET", "/admin/outbox", None),
    ("GET", "/health", None),
)


def mode_flag_off(work: Path, scratch: Path) -> None:
    for label, env in (("DUE_TIMES unset", {}), ("DUE_TIMES=off", {"DUE_TIMES": "off"})):
        now = dt.datetime.now(dt.timezone.utc)
        document = base_document(now)
        folder = scratch / ("unset" if not env else "off")
        folder.mkdir()
        (folder / "base").mkdir()
        (folder / "delivery").mkdir()
        write(folder / "base" / "tickets.json", document)
        write(folder / "delivery" / "tickets.json", document)
        since = now - dt.timedelta(seconds=1)
        base = started(BASE, folder / "base" / "tickets.json", folder / "base", "1.4.0")
        try:
            delivered = started(work, folder / "delivery" / "tickets.json", folder / "delivery", f"delivery, {label}", **env)
        except SystemExit:
            base.stop()
            raise
        try:
            for method, path, body in FLAG_OFF_REQUESTS:
                want = base.call(method, path, body)
                got = delivered.call(method, path, body)
                if (want[0], normalised(want[1], since)) != (got[0], normalised(got[1], since)):
                    fail(f"off ({label}): {method} {path} answers {got[0]} {json.dumps(normalised(got[1], since))[:300]}; "
                         f"1.4.0 answers {want[0]} {json.dumps(normalised(want[1], since))[:300]}")
        finally:
            delivered.stop()
            base.stop()


def node(root: Path, argv: list[str]) -> subprocess.CompletedProcess:
    env = {key: value for key, value in os.environ.items() if key not in SCRUB}
    return subprocess.run(["node", *argv], cwd=root, env=env, capture_output=True, text=True, timeout=60)


def mode_cli(work: Path, scratch: Path) -> None:
    now = dt.datetime.now(dt.timezone.utc)
    document = base_document(now)
    original = scratch / "original.json"
    migrated = scratch / "tickets.json"
    write(original, document)
    write(migrated, document)
    server = started(work, migrated, scratch, "delivery DUE_TIMES=on", DUE_TIMES="on")
    try:
        server.listing()
    finally:
        server.stop()
    want = node(BASE, ["bin/tickets.js", "--data", str(original), "list", "--raw"])
    got = node(work, ["bin/tickets.js", "--data", str(migrated), "list", "--raw"])
    if got.returncode != 0:
        fail(f"cli: bin/tickets.js list --raw exited {got.returncode} on the migrated file: {got.stderr.strip()[-300:]}")
    else:
        want_rows = [line.split("\t")[:4] for line in want.stdout.splitlines() if line]
        got_rows = [line.split("\t")[:4] for line in got.stdout.splitlines() if line]
        if want_rows != got_rows:
            fail(f"cli: list --raw's first four columns are {got_rows}, not the base's {want_rows}")
    want = node(BASE, ["scripts/weekly-report.js", "--data", str(original), "--json"])
    got = node(work, ["scripts/weekly-report.js", "--data", str(migrated), "--json"])
    try:
        same = got.returncode == 0 and json.loads(got.stdout) == json.loads(want.stdout)
    except ValueError:
        same = False
    if not same:
        fail(f"cli: scripts/weekly-report.js --json printed {got.stdout.strip()[:300]!r} (exit {got.returncode}) on the migrated "
             f"file, not the base's {want.stdout.strip()[:300]!r}")


MODES = {"migrate": mode_migrate, "restart": mode_restart, "switch": mode_switch, "rollback": mode_rollback,
         "off": mode_flag_off, "cli": mode_cli}


def main(argv: list[str]) -> int:
    if len(argv) != 1 or argv[0] not in MODES:
        print("usage: due_times_probe.py " + "|".join(MODES), file=sys.stderr)
        return 2
    work = Path.cwd()
    if not (work / "src" / "server.js").is_file():
        print(f"FAIL: {work} has no src/server.js; run the probe from the delivery's work directory")
        return 1
    scratch = Path(tempfile.mkdtemp(prefix="due-times-probe-"))
    try:
        MODES[argv[0]](work, scratch)
    except SystemExit as stop:  # a server that never listened (serve.wait_for_candidate printed why)
        if stop.code not in (0, None):
            FAILURES.append("a server did not start")
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    if FAILURES:
        print(f"{argv[0]}: {len(FAILURES)} expectation(s) failed")
        return 1
    print(f"{argv[0]}: every expectation holds")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
