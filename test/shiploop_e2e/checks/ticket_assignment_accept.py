"""Held-out acceptance checks for the `ticket-assignment` case (style: brownfield), read from its prompt and from the base's own
documents, and never shown to a model.

``quality.acceptance`` imports this module and calls each function in ``CHECKS``: with the base URL of the delivered server,
which it started on a free port, and, for a check that takes a second parameter, with the delivered copy (``quality.Product``),
which starts more servers of the product with an environment of the check's own (a data file, a notification file, the worker
off) and runs the product's command line. A check returns ``(ok, note)``. They run inside the harness process, so neither this
file's name nor a check id is ever on a command line, and nothing is written into the delivery: the files the product reads and
writes for a check live in that check's scratch folder. Each is a black box over HTTP and the command line, and ``cases.json``
quotes the sentence or the base document each check reads (``source``) and its ``grade``.

The case starts from fixtures/node-tickets, a help-desk ticket service. The first six checks are pass-to-pass: the existing
API, its listing, its notifications, a restart from the data file, the raw columns of the command line that the weekly report
reads, and a data file the base wrote must all answer as they did. The rest are fail-to-pass: the base has no assignee. Several
read a fact the request depends on and does not name, each kept in the base's documents: the error envelope
(docs/decisions/0004), the outbox and its keys (0006, src/store.js), the audit log's before and after values (0007), cursor
pages under every filter (0005), filters that combine (docs/api.md, which the base's listing breaks), the data file and the
files an earlier version wrote (0008), and the raw columns (README.md).

The checks that start servers of their own set WORKER_INTERVAL_MS (0 for none, 25 ms when they wait for a delivery), so they
wait on the product's own interval, never on a fixed sleep longer than a second, and every wait is bounded.
"""

from __future__ import annotations

import contextlib
import http.client
import json
from pathlib import Path
import re
import threading
import time
import urllib.parse

CALL_SECONDS = 5  # a ceiling for one HTTP call: a call that has not answered by then fails its check
DELIVERY_SECONDS = 3.0  # a ceiling for the worker to deliver a notification at a 25 ms interval: 120 of its intervals
SETTLE_SECONDS = 0.3  # how long a check keeps watching after a delivery, for a second one: twelve worker intervals
COMMAND_SECONDS = 20  # a ceiling for one run of the product's command line
TICKS = "25"  # WORKER_INTERVAL_MS of a check that waits for deliveries
QUIET = {"WORKER_INTERVAL_MS": "0", "NOTIFY_FILE": None, "DATA_FILE": None}  # a server whose outbox only fills
TICKET_ID = re.compile(r"T-\d{4,}")
BASE_FIELDS = ("id", "title", "priority", "requester", "status", "created", "updated")
ACTIVE_PATH = {"open": (), "in_progress": ("in_progress",), "resolved": ("in_progress", "resolved"),
               "closed": ("in_progress", "resolved", "closed")}

# A data file as the base writes it (src/persistence.js, version 1), with the tickets of a service that ran before the change.
OLD_DATA = {
    "version": 1,
    "savedAt": "2025-09-12T16:40:00.000Z",
    "nextNumber": 4,
    "tickets": [
        {"id": "T-0001", "title": "VPN drops every hour", "priority": "high", "requester": "maria@example.com",
         "status": "in_progress", "created": "2025-09-08T08:15:00.000Z", "updated": "2025-09-08T09:02:00.000Z"},
        {"id": "T-0002", "title": "Printer on the 4th floor jams", "priority": "normal", "requester": "li@example.com",
         "status": "open", "created": "2025-09-09T10:00:00.000Z", "updated": "2025-09-09T10:00:00.000Z"},
        {"id": "T-0003", "title": "New starter needs a laptop", "priority": "low", "requester": "hr@example.com",
         "status": "resolved", "created": "2025-09-10T07:30:00.000Z", "updated": "2025-09-11T15:45:00.000Z"},
    ],
    "audit": [
        {"seq": 1, "ticket": "T-0001", "action": "ticket.created", "actor": "system", "at": "2025-09-08T08:15:00.000Z",
         "changes": {"title": {"from": None, "to": "VPN drops every hour"}, "priority": {"from": None, "to": "high"},
                     "requester": {"from": None, "to": "maria@example.com"}, "status": {"from": None, "to": "open"}}},
        {"seq": 2, "ticket": "T-0001", "action": "ticket.transitioned", "actor": "dana.k", "at": "2025-09-08T09:02:00.000Z",
         "changes": {"status": {"from": "open", "to": "in_progress"}}},
        {"seq": 3, "ticket": "T-0002", "action": "ticket.created", "actor": "system", "at": "2025-09-09T10:00:00.000Z",
         "changes": {"title": {"from": None, "to": "Printer on the 4th floor jams"}, "priority": {"from": None, "to": "normal"},
                     "requester": {"from": None, "to": "li@example.com"}, "status": {"from": None, "to": "open"}}},
        {"seq": 4, "ticket": "T-0003", "action": "ticket.created", "actor": "system", "at": "2025-09-10T07:30:00.000Z",
         "changes": {"title": {"from": None, "to": "New starter needs a laptop"}, "priority": {"from": None, "to": "low"},
                     "requester": {"from": None, "to": "hr@example.com"}, "status": {"from": None, "to": "open"}}},
        {"seq": 5, "ticket": "T-0003", "action": "ticket.transitioned", "actor": "sam.r", "at": "2025-09-11T09:00:00.000Z",
         "changes": {"status": {"from": "open", "to": "in_progress"}}},
        {"seq": 6, "ticket": "T-0003", "action": "ticket.transitioned", "actor": "sam.r", "at": "2025-09-11T15:45:00.000Z",
         "changes": {"status": {"from": "in_progress", "to": "resolved"}}},
    ],
    "outbox": {"nextId": 4, "events": [
        {"id": n, "key": f"{kind}:{ticket}", "type": kind, "to": to, "ticket": ticket, "data": {"title": title},
         "status": "sent", "attempts": 1, "created": at, "nextAttemptAt": None, "lastError": None, "sentAt": at}
        for n, kind, ticket, to, title, at in (
            (1, "ticket.created", "T-0001", "maria@example.com", "VPN drops every hour", "2025-09-08T08:15:00.000Z"),
            (2, "ticket.created", "T-0002", "li@example.com", "Printer on the 4th floor jams", "2025-09-09T10:00:00.000Z"),
            (3, "ticket.resolved", "T-0003", "hr@example.com", "New starter needs a laptop", "2025-09-11T15:45:00.000Z"))]},
}


# --------------------------------------------------------------------------------------------------------------------
# HTTP

# One kept-alive connection per thread and server, closed by this side (hang_up) before the server ends. A connection per call
# would leave a TCP wait per call: on the product's port when the product closes first, where a later server given that port
# (the base's own tests listen on port 0) can meet it, or on this side's ports when it closes first, which a few thousand calls
# a minute run out of.
_connections: dict[tuple[int, str], http.client.HTTPConnection] = {}
_connections_lock = threading.Lock()
STALE = (http.client.RemoteDisconnected, BrokenPipeError, ConnectionResetError)  # a kept-alive connection the server closed


def _connection(base: str) -> tuple[http.client.HTTPConnection, bool]:
    """This thread's connection to `base`, and whether it was used before."""
    key = (threading.get_ident(), base)
    with _connections_lock:
        connection = _connections.get(key)
        if connection is not None:
            return connection, True
        address = urllib.parse.urlsplit(base)
        _connections[key] = connection = http.client.HTTPConnection(address.hostname, address.port, timeout=CALL_SECONDS)
        return connection, False


def hang_up(base: str) -> None:
    """Close this thread's connection to `base`, from this side."""
    with _connections_lock:
        connection = _connections.pop((threading.get_ident(), base), None)
    if connection is not None:
        connection.close()


@contextlib.contextmanager
def serving(product, env: dict):
    """A server of the product's own (``product.serve``), whose connection this side closes before the server ends."""
    with product.serve(env) as server:
        try:
            yield server
        finally:
            hang_up(server)


def call(base: str, method: str, path: str, body=None, actor: str | None = None, raw: bytes | None = None) -> tuple[int, object]:
    """One request; the status and the parsed JSON body (None when the body is empty or not JSON). A kept-alive connection the
    server had closed is opened again once, which a request never sent cannot have changed anything with."""
    data = raw if raw is not None else (None if body is None else json.dumps(body).encode())
    headers = {"content-type": "application/json"} if data is not None else {}
    if actor:
        headers["x-actor"] = actor
    for _attempt in range(2):
        connection, reused = _connection(base)
        try:
            connection.request(method, path, body=data, headers=headers)
            response = connection.getresponse()
            status, text = response.status, response.read()
        except STALE:
            hang_up(base)
            if reused:
                continue
            raise
        except BaseException:
            hang_up(base)
            raise
        if response.will_close:
            hang_up(base)
        break
    try:
        return status, json.loads(text or b"null")
    except ValueError:
        return status, None


def short(body) -> str:
    return json.dumps(body)[:120]


def ok2xx(status: int) -> bool:
    return 200 <= status < 300


def enveloped(status: int, body, want_status: int, want_code: str) -> bool:
    """The base's error envelope (docs/decisions/0004-error-envelope.md): the status, and {"error": {"code", "message"}}."""
    error = body.get("error") if isinstance(body, dict) else None
    return (status == want_status and isinstance(error, dict) and error.get("code") == want_code
            and isinstance(error.get("message"), str) and bool(error["message"].strip()))


def create(base: str, title: str = "Laptop will not boot", priority: str = "normal", requester: str = "li@example.com",
           actor: str | None = None) -> dict:
    """A new ticket; raises when the service will not create one, which fails the check that needed it."""
    status, ticket = call(base, "POST", "/tickets", {"title": title, "requester": requester, "priority": priority}, actor=actor)
    if status != 201 or not isinstance(ticket, dict) or not TICKET_ID.fullmatch(str(ticket.get("id"))):
        raise AssertionError(f"POST /tickets answered HTTP {status} {short(ticket)}")
    return ticket


def move(base: str, ticket: str, *statuses: str) -> None:
    for to in statuses:
        status, body = call(base, "POST", f"/tickets/{ticket}/transition", {"to": to})
        if status != 200:
            raise AssertionError(f"moving {ticket} to {to} answered HTTP {status} {short(body)}")


def assign(base: str, ticket: str, assignee, actor: str | None = None) -> tuple[int, object]:
    return call(base, "PUT", f"/tickets/{ticket}/assignee", {"assignee": assignee}, actor=actor)


def get(base: str, ticket: str) -> dict:
    status, body = call(base, "GET", f"/tickets/{ticket}")
    return body if status == 200 and isinstance(body, dict) else {}


def history(base: str, ticket: str) -> list:
    status, body = call(base, "GET", f"/tickets/{ticket}/audit")
    items = body.get("items") if status == 200 and isinstance(body, dict) else None
    return items if isinstance(items, list) else []


def outbox(base: str) -> dict:
    status, body = call(base, "GET", "/admin/outbox")
    return body if status == 200 and isinstance(body, dict) else {}


def events(report: dict, to: str | None = None, ticket: str | None = None, states=("pending", "sent", "dead")) -> list:
    """The outbox events in `states` for recipient `to` (any recipient when None) whose record names `ticket`."""
    found = []
    for state in states:
        for event in report.get(state) or []:
            if isinstance(event, dict) and (to is None or event.get("to") == to) and (
                    ticket is None or ticket in json.dumps(event)):
                found.append(event)
    return found


def pages(base: str, query: str, limit: int) -> tuple[list[str], list[int], str | None]:
    """Every page of GET /tickets?<query> through its cursors: (ids in order, each page's size, why the walk broke or None)."""
    ids, sizes, cursor = [], [], None
    for _ in range(200):
        path = f"/tickets?{query}{'&' if query else ''}limit={limit}" + (f"&cursor={cursor}" if cursor else "")
        status, body = call(base, "GET", path)
        items = body.get("items") if isinstance(body, dict) else None
        if status != 200 or not isinstance(items, list) or "next" not in body:
            return ids, sizes, f"{path}: HTTP {status} {short(body)}"
        ids += [item.get("id") for item in items if isinstance(item, dict)]
        sizes.append(len(items))
        cursor = body["next"]
        if cursor is None:
            return ids, sizes, None
        if not isinstance(cursor, str) or not items:
            return ids, sizes, f"{path}: next {short(cursor)} after {len(items)} items"
        cursor = urllib.parse.quote(cursor, safe="")
    return ids, sizes, "more than 200 pages"


def listed(base: str, ticket: str) -> dict | None:
    """The listing's item for `ticket`, found by walking every page of GET /tickets; None when it is not listed."""
    cursor = None
    for _ in range(200):
        status, body = call(base, "GET", "/tickets?limit=100" + (f"&cursor={urllib.parse.quote(cursor, safe='')}" if cursor else ""))
        items = body.get("items") if isinstance(body, dict) else None
        if status != 200 or not isinstance(items, list):
            return None
        found = next((item for item in items if isinstance(item, dict) and item.get("id") == ticket), None)
        if found is not None:
            return found
        cursor = body.get("next")
        if not isinstance(cursor, str) or not cursor:
            return None
    return None


def listing(base: str, query: str) -> list[str] | str:
    """The ids GET /tickets?<query> lists over all its pages, or why it could not be read."""
    ids, _sizes, broken = pages(base, query, 100)
    return broken or ids


def seed(base: str, rows) -> list[str]:
    """Tickets from (status, priority, assignee) rows: each created, assigned while open when it has an agent, then moved to
    its status. Their ids, in order."""
    made = []
    for number, (status, priority, assignee) in enumerate(rows, 1):
        ticket = create(base, title=f"Request {number}: {status} {priority}", priority=priority,
                        requester=f"user{number}@example.com")["id"]
        if assignee is not None:
            answer, body = assign(base, ticket, assignee)
            if not ok2xx(answer):
                raise AssertionError(f"assigning {ticket} to {assignee} answered HTTP {answer} {short(body)}")
        move(base, ticket, *ACTIVE_PATH[status])
        made.append(ticket)
    return made


def wait_for(condition, seconds: float = DELIVERY_SECONDS) -> bool:
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        if condition():
            return True
        time.sleep(0.02)
    return bool(condition())


def lines(path: Path) -> list[dict]:
    """The JSON lines of a notification file (none when it does not exist)."""
    try:
        text = path.read_text()
    except OSError:
        return []
    found = []
    for line in text.splitlines():
        try:
            parsed = json.loads(line)
        except ValueError:
            continue
        if isinstance(parsed, dict):
            found.append(parsed)
    return found


def lines_for(path: Path, to: str, ticket: str) -> list[dict]:
    return [line for line in lines(path) if line.get("to") == to and ticket in json.dumps(line)]


def verdict(wrong: list[str], fine: str) -> tuple[bool, str]:
    return not wrong, "; ".join(wrong) or fine


# --------------------------------------------------------------------------------------------------------------------
# The command line

def command(product, argv: list[str], data: Path) -> tuple[int | None, str]:
    """(return code, output) of one of the product's commands over the data file `data`."""
    result = product.run(argv, env={"DATA_FILE": str(data), "NOTIFY_FILE": None}, ceiling=COMMAND_SECONDS)
    return result["returncode"], result["output"]


def raw_rows(output: str) -> list[list[str]]:
    return [line.split("\t") for line in output.splitlines() if TICKET_ID.match(line)]


def report_counts(output: str) -> dict | None:
    """The weekly report's --json counts: the last line of the output that is a JSON object holding them."""
    for line in reversed(output.splitlines()):
        try:
            parsed = json.loads(line)
        except ValueError:
            continue
        if isinstance(parsed, dict) and "byStatus" in parsed:
            return parsed
    return None


# --------------------------------------------------------------------------------------------------------------------
# Pass-to-pass: what the service already does

def ticket_lifecycle_unchanged(base: str) -> tuple[bool, str]:
    wrong = []
    ticket = create(base, title="Monitor flickers", priority="high", requester="maria@example.com", actor="dana.k")
    tid = ticket["id"]
    if (ticket.get("status"), ticket.get("priority"), ticket.get("title")) != ("open", "high", "Monitor flickers") or \
            ticket.get("created") != ticket.get("updated"):
        wrong.append(f"created {short(ticket)}")
    if {key: get(base, tid).get(key) for key in BASE_FIELDS} != {key: ticket.get(key) for key in BASE_FIELDS}:
        wrong.append(f"GET {tid}: {short(get(base, tid))}")
    status, body = call(base, "PATCH", f"/tickets/{tid}", {"priority": "urgent"}, actor="sam.r")
    if status != 200 or not isinstance(body, dict) or body.get("priority") != "urgent":
        wrong.append(f"PATCH: HTTP {status} {short(body)}")
    for to, want_status, want_code in (("closed", 409, "conflict"), ("done", 400, "invalid")):
        status, body = call(base, "POST", f"/tickets/{tid}/transition", {"to": to})
        if not enveloped(status, body, want_status, want_code):
            wrong.append(f"transition to {to}: HTTP {status} {short(body)}")
    for to in ("in_progress", "resolved", "edit", "open", "in_progress", "resolved", "closed"):
        if to == "edit":  # a resolved ticket can still change; only a closed one cannot
            status, body = call(base, "PATCH", f"/tickets/{tid}", {"title": "Monitor flickers after lunch"})
            if status != 200 or not isinstance(body, dict) or body.get("title") != "Monitor flickers after lunch":
                wrong.append(f"PATCH of a resolved ticket: HTTP {status} {short(body)}")
            continue
        status, body = call(base, "POST", f"/tickets/{tid}/transition", {"to": to})
        if status != 200 or not isinstance(body, dict) or body.get("status") != to:
            wrong.append(f"transition to {to}: HTTP {status} {short(body)}")
            break
    status, body = call(base, "PATCH", f"/tickets/{tid}", {"title": "Reworded"})
    if not enveloped(status, body, 409, "conflict"):
        wrong.append(f"PATCH of a closed ticket: HTTP {status} {short(body)}")
    for method, path, payload, raw, want in (("GET", "/tickets/T-99999", None, None, (404, "not_found")),
                                            ("POST", "/tickets", {"title": "", "requester": "x@example.com"}, None, (400, "invalid")),
                                            ("POST", "/tickets", None, b'{"title":', (400, "invalid"))):
        status, body = call(base, method, path, payload, raw=raw)
        if not enveloped(status, body, *want):
            wrong.append(f"{method} {path}: HTTP {status} {short(body)}")
    trail = [(entry.get("action"), entry.get("actor"), json.dumps(entry.get("changes"), sort_keys=True))
             for entry in history(base, tid)]
    expected = ([("ticket.created", "dana.k"), ("ticket.updated", "sam.r")] + [("ticket.transitioned", "system")] * 2
                + [("ticket.updated", "system")] + [("ticket.transitioned", "system")] * 4)
    if [row[:2] for row in trail] != expected or '"from": "high", "to": "urgent"' not in trail[1][2]:
        wrong.append(f"audit of {tid}: {trail}")
    return verdict(wrong, "create, read, change, the lifecycle, the envelope and the audit trail answer as the base does")


def listing_unchanged(base: str, product) -> tuple[bool, str]:
    rows = [(("open", "in_progress", "resolved", "closed")[n % 4], ("low", "normal", "high", "urgent")[n * 3 % 4], None)
            for n in range(25)]
    wrong = []
    with serving(product, QUIET) as server:
        made = seed(server, rows)
        status, first = call(server, "GET", "/tickets")
        if status != 200 or not isinstance(first, dict) or [t.get("id") for t in first.get("items") or []] != made[:20] \
                or not first.get("next"):
            wrong.append(f"GET /tickets: HTTP {status}, 20 tickets and a next expected: {short(first)}")
        ids, sizes, broken = pages(server, "", 7)
        if broken or ids != made or sizes != [7, 7, 7, 4]:
            wrong.append(f"paging by 7: {broken or (sizes, ids)}")
        for query, want in (("status=open", [t for t, r in zip(made, rows) if r[0] == "open"]),
                            ("priority=urgent", [t for t, r in zip(made, rows) if r[1] == "urgent"])):
            ids, _sizes, broken = pages(server, query, 2)
            if broken or ids != want:
                wrong.append(f"{query} by 2: {broken or ids}")
        for query in ("limit=0", "limit=101", "limit=ten", "cursor=not-a-cursor", "status=done", "priority=critical"):
            status, body = call(server, "GET", f"/tickets?{query}")
            if not enveloped(status, body, 400, "invalid"):
                wrong.append(f"{query}: HTTP {status} {short(body)}")
    return verdict(wrong, "the listing pages 25 tickets by cursor, filters by one field and refuses bad parameters as before")


def notifications_unchanged(base: str, product) -> tuple[bool, str]:
    wrong = []
    scratch = product.scratch()
    quiet_file, live_file = scratch / "quiet.jsonl", scratch / "live.jsonl"
    with serving(product, {**QUIET, "NOTIFY_FILE": str(quiet_file)}) as server:
        tid = create(server, requester="li@example.com")["id"]
        move(server, tid, "in_progress", "resolved")
        report = outbox(server)
        kinds = sorted(event.get("type") for event in events(report, "li@example.com", tid, ("pending",)))
        if kinds != ["ticket.created", "ticket.resolved"]:
            wrong.append(f"with the worker off, pending for the requester: {kinds}")
        if lines(quiet_file):
            wrong.append(f"with the worker off, the notification file holds {len(lines(quiet_file))} lines")
    with serving(product, {**QUIET, "WORKER_INTERVAL_MS": TICKS, "NOTIFY_FILE": str(live_file)}) as server:
        tid = create(server, requester="maria@example.com")["id"]
        move(server, tid, "in_progress", "resolved")
        if not wait_for(lambda: len(lines_for(live_file, "maria@example.com", tid)) >= 2):
            wrong.append(f"the worker delivered {len(lines_for(live_file, 'maria@example.com', tid))} of the 2 notifications")
        time.sleep(SETTLE_SECONDS)
        delivered = sorted(line.get("type") for line in lines_for(live_file, "maria@example.com", tid))
        sent = events(outbox(server), "maria@example.com", tid, ("sent",))
        if delivered != ["ticket.created", "ticket.resolved"] or len(sent) != 2:
            wrong.append(f"delivered {delivered}, sent in the outbox {len(sent)}")
    return verdict(wrong, "changes enqueue the requester's notifications, and the worker delivers each once")


def restart_keeps_state(base: str, product) -> tuple[bool, str]:
    wrong = []
    data = product.scratch() / "tickets.json"
    env = {**QUIET, "DATA_FILE": str(data)}
    with serving(product, env) as server:
        made = [create(server, title=f"Restart {n}", priority=p)["id"] for n, p in enumerate(("low", "high", "urgent"), 1)]
        move(server, made[1], "in_progress")
        call(server, "POST", f"/tickets/{made[1]}/transition", {"to": "resolved"}, actor="sam.r")
        before = [get(server, tid) for tid in made]
    with serving(product, env) as server:
        after = [get(server, tid) for tid in made]
        if [{k: t.get(k) for k in BASE_FIELDS} for t in after] != [{k: t.get(k) for k in BASE_FIELDS} for t in before]:
            wrong.append(f"after the restart: {short(after)}")
        actors = [entry.get("actor") for entry in history(server, made[1])]
        if actors != ["system", "system", "sam.r"]:
            wrong.append(f"the audit of {made[1]} after the restart: {actors}")
        pending = len(events(outbox(server), None, None, ("pending",)))
        if pending != 4:
            wrong.append(f"{pending} notifications pending after the restart, 4 expected")
        again = create(server)["id"]
        if again != "T-0004":
            wrong.append(f"the next ticket after the restart is {again}, not T-0004")
    return verdict(wrong, "a restart from the data file keeps the tickets, their history and the outbox, and numbers go on")


def cli_raw_columns(base: str, product) -> tuple[bool, str]:
    rows = [("open", "low", "dana.k"), ("in_progress", "urgent", None), ("resolved", "high", "sam.r"),
            ("closed", "normal", None), ("open", "urgent", "dana.k"), ("in_progress", "normal", "priya.n")]
    wrong = []
    data = product.scratch() / "tickets.json"
    with serving(product, {**QUIET, "DATA_FILE": str(data)}) as server:
        made = []
        for number, (status, priority, agent) in enumerate(rows, 1):
            tid = create(server, title=f"Weekly row {number}", priority=priority)["id"]
            if agent:
                assign(server, tid, agent)  # the base has no assignment: its answer is not this check's business
            move(server, tid, *ACTIVE_PATH[status])
            made.append(tid)
    code, output = command(product, ["node", "bin/tickets.js", "list", "--raw"], data)
    got = [row[:4] for row in raw_rows(output)]
    want = [[tid, status, priority, f"Weekly row {n}"] for n, (tid, (status, priority, _a)) in enumerate(zip(made, rows), 1)]
    if code != 0 or got != want:
        wrong.append(f"list --raw (rc {code}): id, status, priority and title expected first, got {got[:3]}")
    code, output = command(product, ["node", "scripts/weekly-report.js", "--json"], data)
    counts = report_counts(output)
    want_status = {s: sum(1 for r in rows if r[0] == s) for s in ("open", "in_progress", "resolved", "closed")}
    want_priority = {p: sum(1 for r in rows if r[1] == p) for p in ("low", "normal", "high", "urgent")}
    if code != 0 or not counts or counts.get("total") != len(rows) or counts.get("byStatus") != want_status \
            or counts.get("byPriority") != want_priority:
        wrong.append(f"weekly report (rc {code}): {short(counts) if counts else output[-160:]}")
    return verdict(wrong, "list --raw keeps id, status, priority and title in their places and the weekly report counts right")


def old_data_loads(base: str, product) -> tuple[bool, str]:
    wrong = []
    data = product.scratch() / "tickets.json"
    data.write_text(json.dumps(OLD_DATA, indent=2))
    with serving(product, {**QUIET, "DATA_FILE": str(data)}) as server:
        status, body = call(server, "GET", "/tickets")
        got = [(t.get("id"), t.get("status"), t.get("title")) for t in (body or {}).get("items") or []] \
            if isinstance(body, dict) else body
        want = [(t["id"], t["status"], t["title"]) for t in OLD_DATA["tickets"]]
        if status != 200 or got != want:
            wrong.append(f"GET /tickets over a file the base wrote: HTTP {status} {short(got)}")
        if [entry.get("actor") for entry in history(server, "T-0003")] != ["system", "sam.r", "sam.r"]:
            wrong.append("the audit of T-0003 is not the file's")
        new = create(server)["id"]
        if new != "T-0004":
            wrong.append(f"the next ticket is {new}, not T-0004")
    code, output = command(product, ["node", "bin/tickets.js", "list", "--raw"], data)
    if code != 0 or [row[0] for row in raw_rows(output)] != ["T-0001", "T-0002", "T-0003", "T-0004"]:
        wrong.append(f"list --raw over the file (rc {code}): {output[-160:]}")
    return verdict(wrong, "a data file the base wrote loads: its tickets, history and next number, on the API and the command line")


# --------------------------------------------------------------------------------------------------------------------
# Fail-to-pass: assignment

def assign_and_unassign(base: str) -> tuple[bool, str]:
    wrong = []
    ticket = create(base, title="Shared drive is full")
    tid = ticket["id"]
    if "assignee" not in ticket or ticket["assignee"] is not None:
        wrong.append(f"a new ticket shows no null assignee: {short(ticket)}")
    status, body = assign(base, tid, "dana.k")
    if not ok2xx(status) or get(base, tid).get("assignee") != "dana.k":
        wrong.append(f"assign dana.k: HTTP {status} {short(body)}; then {short(get(base, tid))}")
    found = listed(base, tid)
    if not found or found.get("assignee") != "dana.k":
        wrong.append(f"the listing shows {tid} as {short(found)}")
    status, body = assign(base, tid, None)
    if not ok2xx(status) or "assignee" not in get(base, tid) or get(base, tid)["assignee"] is not None:
        wrong.append(f"unassign: HTTP {status} {short(body)}; then {short(get(base, tid))}")
    working = create(base, title="Phone has no dial tone")["id"]
    move(base, working, "in_progress")
    status, body = assign(base, working, "sam.r")
    if not ok2xx(status) or get(base, working).get("assignee") != "sam.r":
        wrong.append(f"assign an in-progress ticket: HTTP {status} {short(body)}")
    return verdict(wrong, "new tickets show a null assignee; assign, unassign and an in-progress ticket work, and the listing shows it")


def assignee_validation(base: str) -> tuple[bool, str]:
    wrong = []
    tid = create(base, title="Keyboard missing keys")["id"]
    for label, payload, raw in (("an empty name", {"assignee": ""}, None), ("65 characters", {"assignee": "a" * 65}, None),
                                ("a number", {"assignee": 42}, None), ("a list", {"assignee": ["dana.k"]}, None),
                                ("a body that is not JSON", None, b'{"assignee":')):
        status, body = call(base, "PUT", f"/tickets/{tid}/assignee", payload, raw=raw)
        if not enveloped(status, body, 400, "invalid"):
            wrong.append(f"{label}: HTTP {status} {short(body)}")
    if get(base, tid).get("assignee", "absent") is not None:
        wrong.append(f"after the refusals: {short(get(base, tid))}")
    name = "agent-" + "x" * 58
    status, body = assign(base, tid, name)
    if not ok2xx(status) or get(base, tid).get("assignee") != name:
        wrong.append(f"a 64-character name: HTTP {status} {short(body)}")
    return verdict(wrong, "an empty, over-long or non-text agent and a malformed body are 400 invalid; 64 characters are taken")


def assign_state_and_missing(base: str) -> tuple[bool, str]:
    wrong = []
    resolved = create(base, title="Old request")["id"]
    move(base, resolved, "in_progress", "resolved")
    status, body = assign(base, resolved, "dana.k")
    if not enveloped(status, body, 409, "conflict") or get(base, resolved).get("assignee") is not None:
        wrong.append(f"assign a resolved ticket: HTTP {status} {short(body)}")
    closed = create(base, title="Finished request")["id"]
    assign(base, closed, "dana.k")
    move(base, closed, "in_progress", "resolved", "closed")
    kept = get(base, closed).get("assignee")
    for agent in (None, "sam.r"):
        status, body = assign(base, closed, agent)
        if not enveloped(status, body, 409, "conflict"):
            wrong.append(f"{'unassign' if agent is None else 'reassign'} a closed ticket: HTTP {status} {short(body)}")
    if get(base, closed).get("assignee") != kept or kept is None:
        wrong.append(f"the closed ticket's assignee went from {kept!r} to {get(base, closed).get('assignee')!r}")
    status, body = assign(base, "T-99999", "dana.k")
    if not enveloped(status, body, 404, "not_found"):
        wrong.append(f"an unknown ticket: HTTP {status} {short(body)}")
    return verdict(wrong, "resolved and closed tickets answer 409 conflict and keep their assignee; an unknown one is 404 not_found")


def assign_same_agent_noop(base: str, product) -> tuple[bool, str]:
    with serving(product, QUIET) as server:
        tid = create(server, title="Badge reader rejects card")["id"]
        status, body = assign(server, tid, "dana.k")
        if not ok2xx(status):
            return False, f"assign dana.k: HTTP {status} {short(body)}"
        before = (get(server, tid), len(history(server, tid)), len(events(outbox(server), None, tid)))
        time.sleep(0.01)
        status, body = assign(server, tid, "dana.k")
        after = (get(server, tid), len(history(server, tid)), len(events(outbox(server), None, tid)))
    if not ok2xx(status) or after != before:
        return False, (f"again: HTTP {status}; ticket {short(before[0])} -> {short(after[0])}, audit {before[1]} -> {after[1]}, "
                       f"notifications {before[2]} -> {after[2]}")
    return True, "assigning the agent the ticket already has answers 2xx and changes nothing: ticket, audit and outbox"


def assign_audited(base: str) -> tuple[bool, str]:
    wrong = []
    tid = create(base, title="Laptop battery swells")["id"]
    for agent, actor, frm in (("dana.k", "lead.ana", None), ("sam.r", None, "dana.k"), (None, "lead.ana", "sam.r")):
        known = len(history(base, tid))
        status, _body = assign(base, tid, agent, actor=actor)
        added = history(base, tid)[known:]
        change = (added[0].get("changes") or {}).get("assignee") if len(added) == 1 and isinstance(added[0], dict) else None
        if not ok2xx(status) or len(added) != 1 or added[0].get("actor") != (actor or "system") or \
                change != {"from": frm, "to": agent}:
            wrong.append(f"{frm} -> {agent} by {actor or 'no X-Actor'}: HTTP {status}, new entries {short(added)}")
    return verdict(wrong, "each assignment adds one audit entry with its actor and the assignee before and after")


def assignee_notified(base: str, product) -> tuple[bool, str]:
    wrong = []
    scratch = product.scratch()
    quiet_file, live_file = scratch / "quiet.jsonl", scratch / "live.jsonl"
    with serving(product, {**QUIET, "NOTIFY_FILE": str(quiet_file)}) as server:
        tid = create(server, title="Projector in room 2 is dim")["id"]
        for agent in ("dana.k", "sam.r"):
            status, body = assign(server, tid, agent)
            pending = events(outbox(server), agent, tid, ("pending",))
            if not ok2xx(status) or len(pending) != 1:
                wrong.append(f"with the worker off, assigning {agent} left {len(pending)} pending notifications for them "
                             f"(HTTP {status})")
        if lines(quiet_file):
            wrong.append(f"with the worker off, {len(lines(quiet_file))} notifications were delivered anyway")
    with serving(product, {**QUIET, "WORKER_INTERVAL_MS": TICKS, "NOTIFY_FILE": str(live_file)}) as server:
        tid = create(server, title="Wi-Fi drops in the canteen")["id"]
        status, _body = assign(server, tid, "priya.n")
        if not wait_for(lambda: lines_for(live_file, "priya.n", tid)):
            wrong.append(f"assign priya.n (HTTP {status}): no notification delivered to them within {DELIVERY_SECONDS:.0f} s")
        time.sleep(SETTLE_SECONDS)
        delivered = lines_for(live_file, "priya.n", tid)
        report = outbox(server)
        if len(delivered) != 1 or len(events(report, "priya.n", tid, ("sent",))) != 1 or \
                events(report, "priya.n", tid, ("pending", "dead")):
            wrong.append(f"priya.n was delivered {len(delivered)} notifications; the outbox shows "
                         f"{short(events(report, 'priya.n', tid))}")
    return verdict(wrong, "each new agent's notification waits in the outbox, and the worker delivers it once")


def assignee_filter(base: str, product) -> tuple[bool, str]:
    rows = [("open", "normal", "dana.k"), ("in_progress", "high", "dana.k"), ("open", "low", None), ("in_progress", "urgent", "sam.r"),
            ("open", "normal", None), ("resolved", "high", "dana.k"), ("closed", "low", None)]
    wrong = []
    with serving(product, QUIET) as server:
        made = seed(server, rows)
        for query, want in (("assignee=dana.k", [t for t, r in zip(made, rows) if r[2] == "dana.k"]),
                            ("assignee=sam.r", [t for t, r in zip(made, rows) if r[2] == "sam.r"]),
                            ("assignee=", [t for t, r in zip(made, rows) if r[2] is None]),
                            ("assignee=nobody.here", []), ("", made)):
            got = listing(server, query)
            if got != want:
                wrong.append(f"{query or 'no filter'}: {got}, expected {want}")
    return verdict(wrong, "assignee=<agent> keeps that agent's tickets and an empty assignee= the unassigned ones")


def filters_combine(base: str, product) -> tuple[bool, str]:
    rows = [("open", "urgent", "dana.k"), ("open", "high", None), ("in_progress", "urgent", "sam.r"), ("open", "urgent", None),
            ("resolved", "urgent", "dana.k"), ("in_progress", "normal", "dana.k"), ("open", "low", "sam.r"),
            ("in_progress", "urgent", "dana.k")]
    wrong = []
    with serving(product, QUIET) as server:
        made = seed(server, rows)
        pick = lambda keep: [t for t, r in zip(made, rows) if keep(*r)]  # noqa: E731
        for query, want in (("status=open&priority=urgent", pick(lambda s, p, a: s == "open" and p == "urgent")),
                            ("status=in_progress&assignee=dana.k", pick(lambda s, p, a: s == "in_progress" and a == "dana.k")),
                            ("priority=urgent&assignee=dana.k", pick(lambda s, p, a: p == "urgent" and a == "dana.k")),
                            ("status=open&priority=urgent&assignee=dana.k",
                             pick(lambda s, p, a: s == "open" and p == "urgent" and a == "dana.k"))):
            got = listing(server, query)
            if got != want:
                wrong.append(f"{query}: {got}, expected {want}")
    return verdict(wrong, "every filter given must match: status, priority and assignee combine")


def assignee_filter_pages(base: str, product) -> tuple[bool, str]:
    rows = [("open", "normal", "dana.k" if n % 2 else None) for n in range(16)]
    wrong = []
    with serving(product, QUIET) as server:
        made = seed(server, rows)
        dana = [t for t, r in zip(made, rows) if r[2] == "dana.k"]
        for limit, want_sizes in ((2, [2, 2, 2, 2]), (3, [3, 3, 2]), (8, [8])):
            ids, sizes, broken = pages(server, "assignee=dana.k", limit)
            if broken or ids != dana or sizes != want_sizes:
                wrong.append(f"assignee=dana.k by {limit}: {broken or (sizes, ids)}")
    return verdict(wrong, "the assignee filter pages by cursor: full pages of matches, and next is null after the last one")


def assignee_persists(base: str, product) -> tuple[bool, str]:
    wrong = []
    data = product.scratch() / "tickets.json"
    env = {**QUIET, "DATA_FILE": str(data)}
    with serving(product, env) as server:
        made = [create(server, title=f"Persisted {n}")["id"] for n in range(1, 4)]
        answers = [assign(server, made[0], "dana.k", actor="lead.ana")[0], assign(server, made[1], "sam.r")[0]]
    with serving(product, env) as server:
        got = [get(server, tid).get("assignee", "absent") for tid in made]
        if not all(ok2xx(status) for status in answers) or got != ["dana.k", "sam.r", None]:
            wrong.append(f"after the restart the assignees are {got} (assigned with HTTP {answers})")
        for query, want in (("assignee=dana.k", made[:1]), ("assignee=sam.r", made[1:2])):
            if listing(server, query) != want:
                wrong.append(f"{query} after the restart: {listing(server, query)}")
    return verdict(wrong, "assignees survive a restart from the data file, and the filter finds them")


def old_tickets_unassigned(base: str, product) -> tuple[bool, str]:
    wrong = []
    data = product.scratch() / "tickets.json"
    data.write_text(json.dumps(OLD_DATA, indent=2))
    env = {**QUIET, "DATA_FILE": str(data)}
    old = [ticket["id"] for ticket in OLD_DATA["tickets"]]
    with serving(product, env) as server:
        shown = [get(server, tid).get("assignee", "absent") for tid in old]
        if shown != [None, None, None]:
            wrong.append(f"tickets saved before the change show assignees {shown}")
        status, body = assign(server, "T-0002", "dana.k")
        if not ok2xx(status):
            wrong.append(f"assigning a ticket saved before the change: HTTP {status} {short(body)}")
        if listing(server, "assignee=") != ["T-0001", "T-0003"]:
            wrong.append(f"assignee= lists {listing(server, 'assignee=')}, not the tickets saved before the change and left unassigned")
    with serving(product, env) as server:
        if [get(server, tid).get("assignee", "absent") for tid in old] != [None, "dana.k", None]:
            wrong.append(f"after a restart: {[get(server, tid).get('assignee', 'absent') for tid in old]}")
    return verdict(wrong, "tickets from a data file written before the change are unassigned (null) and can be assigned")


def cli_shows_assignee(base: str, product) -> tuple[bool, str]:
    data = product.scratch() / "tickets.json"
    with serving(product, {**QUIET, "DATA_FILE": str(data)}) as server:
        made = [create(server, title=f"Command line {n}")["id"] for n in range(1, 4)]
        answers = [assign(server, made[0], "dana.k")[0], assign(server, made[2], "priya.n")[0]]
    code, output = command(product, ["node", "bin/tickets.js", "list"], data)
    rows = {tid: next((line for line in output.splitlines() if tid in line), "") for tid in made}
    ok = (code == 0 and "dana.k" in rows[made[0]] and "priya.n" not in rows[made[0]] and "priya.n" in rows[made[2]]
          and "dana.k" not in rows[made[2]] and not ({"dana.k", "priya.n"} & set(rows[made[1]].split())))
    return ok, ("tickets list shows each ticket's assignee" if ok else
                f"tickets list (rc {code}, assigned with HTTP {answers}): {[rows[tid] for tid in made]}")


CHECKS = {
    "ticket-lifecycle-unchanged": ticket_lifecycle_unchanged,
    "listing-unchanged": listing_unchanged,
    "notifications-unchanged": notifications_unchanged,
    "restart-keeps-state": restart_keeps_state,
    "cli-raw-columns": cli_raw_columns,
    "old-data-loads": old_data_loads,
    "assign-and-unassign": assign_and_unassign,
    "assignee-validation": assignee_validation,
    "assign-state-and-missing": assign_state_and_missing,
    "assign-same-agent-noop": assign_same_agent_noop,
    "assign-audited": assign_audited,
    "assignee-notified": assignee_notified,
    "assignee-filter": assignee_filter,
    "filters-combine": filters_combine,
    "assignee-filter-pages": assignee_filter_pages,
    "assignee-persists": assignee_persists,
    "old-tickets-unassigned": old_tickets_unassigned,
    "cli-shows-assignee": cli_shows_assignee,
}
