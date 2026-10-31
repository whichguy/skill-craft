"""Held-out acceptance checks for the `ticket-import` case (style: brownfield), read from its prompt and from the base's own
documents, and never shown to a model.

``quality.acceptance`` imports this module and calls each function in ``CHECKS``, as for ticket-assignment: with the base URL of
the delivered server, and, for a check that takes a second parameter, with the delivered copy (``quality.Product``), which
starts more servers of the product with an environment of the check's own. A check returns ``(ok, note)``. The helpers and the
six pass-to-pass checks are ticket_assignment_accept's, loaded from beside this file, so the two cases read the base the same
way.

The case starts from fixtures/node-tickets. The first six checks are pass-to-pass. The rest are fail-to-pass: the base has no
import. Three read facts the request depends on and does not name, each in the base: a request body over MAX_BODY_BYTES (65536
by default, README.md "Configuration", a default the base's own config test pins) is refused, so a 5000-ticket body needs a
limit of the import's own; with DATA_FILE set the data file is rewritten whole after every change (docs/operations.md,
decision 8), so 5000 tickets created one at a time take far longer than 10 seconds; and a create audits and enqueues a
notification (decisions 6 and 7), which an import refused for an invalid item must not leave behind. The time and
persistence checks run the product as docs/operations.md runs it, with DATA_FILE set.
"""

from __future__ import annotations

import http.client
import importlib.util
import json
from pathlib import Path
import re
import time
import urllib.parse

_SPEC = importlib.util.spec_from_file_location("shiploop_e2e_held_out_ticket_assignment_helpers_for_import",
                                               Path(__file__).with_name("ticket_assignment_accept.py"))
A = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(A)

LIMIT = 5000  # the most tickets one import takes (the prompt)
ANSWER_SECONDS = 10.0  # an import of LIMIT tickets is answered within this (the prompt)
WAIT_SECONDS = 120  # how long the time check waits for a slow answer, so its note can say how slow
INDEX = {0: re.compile(r"(?<![\w.])0(?![\w.])"), 2: re.compile(r"(?<![\w.])2(?![\w.])")}
CREATED_KEYS = ("title", "priority", "requester", "status")


def batch(count: int, start: int = 0) -> list[dict]:
    """`count` valid import items, the way the old tracker's export would hand them over."""
    priorities = ("low", "normal", "high", "urgent")
    return [{"title": f"Imported ticket {start + n}", "requester": f"user{(start + n) % 50}@example.com",
             "priority": priorities[(start + n) % 4]} for n in range(count)]


def post_import(base: str, items, actor: str | None = None, raw: bytes | None = None) -> tuple[int, object]:
    return A.call(base, "POST", "/tickets/import", {"tickets": items}, actor=actor, raw=raw)


def number(ticket_id: str) -> int:
    return int(str(ticket_id)[2:])


def all_ids(base: str) -> list[str]:
    """Every ticket's id, in the listing's order, page by page."""
    ids, cursor = [], None
    for _page in range(1000):
        status, body = A.call(base, "GET", "/tickets?limit=100" + (f"&cursor={urllib.parse.quote(cursor)}" if cursor else ""))
        if status != 200 or not isinstance(body, dict):
            raise AssertionError(f"GET /tickets answered HTTP {status} {A.short(body)}")
        ids += [item.get("id") for item in body.get("items") or []]
        cursor = body.get("next")
        if not cursor:
            return ids
    raise AssertionError("the listing never ended")


def event_count(base: str) -> int:
    return len(A.events(A.outbox(base)))


def refused(status: int, body, index: int) -> str | None:
    """Why (status, body) is not a refusal of the import that names item `index`, or None when it is one."""
    if not A.enveloped(status, body, 400, "invalid"):
        return f"HTTP {status} {A.short(body)}, not 400 invalid in the envelope"
    if not INDEX[index].search(body["error"]["message"]):
        return f"the message {body['error']['message']!r} does not name index {index}"
    return None


# --------------------------------------------------------------------------------------------------------------------
# Fail-to-pass: the import

def import_creates_in_order(base: str) -> tuple[bool, str]:
    wrong = []
    before = A.create(base, title="Before the import")["id"]
    items = [{"title": "Printer jams on tray 2", "requester": "ana@example.com", "priority": "high"},
             {"title": "VPN is slow", "requester": "ben@example.com"},
             {"title": "  Badge reader offline  ", "requester": "cy@example.com", "priority": "low"}]
    status, body = post_import(base, items)
    ids = body.get("ids") if isinstance(body, dict) else None
    if status != 201 or not isinstance(body, dict) or body.get("created") != 3 or not isinstance(ids, list) or len(ids) != 3:
        return False, f"importing 3 tickets answered HTTP {status} {A.short(body)}"
    if [number(i) for i in ids] != [number(before) + n for n in (1, 2, 3)]:
        wrong.append(f"ids {ids} after {before}: not the next numbers in the given order")
    want = [("Printer jams on tray 2", "ana@example.com", "high"), ("VPN is slow", "ben@example.com", "normal"),
            ("Badge reader offline", "cy@example.com", "low")]
    for tid, (title, requester, priority) in zip(ids, want):
        got = A.get(base, tid)
        if (got.get("title"), got.get("requester"), got.get("priority"), got.get("status")) != (title, requester, priority, "open"):
            wrong.append(f"{tid} is {A.short(got)}")
        elif not all(got.get(field) for field in ("created", "updated")):
            wrong.append(f"{tid} lacks created or updated")
    listed = all_ids(base)
    if [i for i in listed if i in ids] != ids:
        wrong.append("the listing does not hold the imported tickets in id order")
    return A.verdict(wrong, "an import creates its tickets as POST /tickets would, in order, and answers created and ids")


def import_all_or_none(base: str) -> tuple[bool, str]:
    wrong = []
    A.create(base, title="Before the refused imports")
    tickets, events = all_ids(base), event_count(base)
    bad = batch(4)
    del bad[2]["requester"]
    why = refused(*post_import(base, bad), 2)
    if why:
        wrong.append(f"an import whose item 2 has no requester: {why}")
    first_bad = batch(3)
    first_bad[0]["priority"] = "critical"
    why = refused(*post_import(base, first_bad), 0)
    if why:
        wrong.append(f"an import whose item 0 has no such priority: {why}")
    if all_ids(base) != tickets:
        wrong.append(f"refused imports changed the tickets: {len(tickets)} before, {len(all_ids(base))} after")
    if event_count(base) != events:
        wrong.append(f"refused imports changed the outbox: {events} events before, {event_count(base)} after")
    return A.verdict(wrong, "an import with an invalid item creates nothing, records nothing, and names the item's index")


def import_validates_like_create(base: str) -> tuple[bool, str]:
    wrong = []
    tickets = all_ids(base)
    good = {"title": "Monitor flickers", "requester": "dee@example.com"}
    for label, item in (("an unknown field", {**good, "severity": "high"}), ("a 201-character title", {**good, "title": "x" * 201}),
                        ("a two-line title", {**good, "title": "one\ntwo"}), ("a blank title", {**good, "title": "   "}),
                        ("a 65-character requester", {**good, "requester": "r" * 65}), ("an unknown priority", {**good, "priority": "critical"}),
                        ("no title", {"requester": "dee@example.com"}), ("an item that is not an object", "Monitor flickers")):
        why = refused(*post_import(base, [item]), 0)
        if why:
            wrong.append(f"{label}: {why}")
    for label, body in (("no tickets field", {}), ("tickets that are not a list", {"tickets": "many"}),
                        ("an unknown field beside tickets", {"tickets": [good], "source": "old tracker"})):
        status, answer = A.call(base, "POST", "/tickets/import", body)
        if not A.enveloped(status, answer, 400, "invalid"):
            wrong.append(f"{label}: HTTP {status} {A.short(answer)}")
    status, answer = post_import(base, batch(LIMIT + 1))
    if not A.enveloped(status, answer, 400, "invalid"):
        wrong.append(f"{LIMIT + 1} tickets: HTTP {status} {A.short(answer)}")
    if all_ids(base) != tickets:
        wrong.append("a refused import created tickets")
    return A.verdict(wrong, f"each item is checked as POST /tickets checks a body, and more than {LIMIT} tickets is refused")


def import_audited(base: str) -> tuple[bool, str]:
    wrong = []
    single = A.create(base, title="One at a time", priority="high", requester="eve@example.com", actor="migration.bot")["id"]
    reference = A.history(base, single)
    status, body = post_import(base, [{"title": "Laptop fan loud", "requester": "fay@example.com", "priority": "high"},
                                      {"title": "Shared drive full", "requester": "gus@example.com"}], actor="migration.bot")
    ids = body.get("ids") if isinstance(body, dict) else None
    if status != 201 or not isinstance(ids, list) or len(ids) != 2:
        return False, f"importing 2 tickets answered HTTP {status} {A.short(body)}"
    shape = [(entry.get("action"), entry.get("actor"), sorted(entry.get("changes") or {})) for entry in reference]
    for tid in ids:
        entries = A.history(base, tid)
        got = [(entry.get("action"), entry.get("actor"), sorted(entry.get("changes") or {})) for entry in entries]
        if got != shape:
            wrong.append(f"{tid}'s history is {got}, a single create's is {shape}")
            continue
        ticket = A.get(base, tid)
        if any(entries[0]["changes"][key] != {"from": None, "to": ticket.get(key)} for key in CREATED_KEYS):
            wrong.append(f"{tid}'s created entry does not record its values from null: {A.short(entries[0]['changes'])}")
    return A.verdict(wrong, "each imported ticket is audited as one created ticket is, with the request's actor")


def import_notifies(base: str, product) -> tuple[bool, str]:
    wrong = []
    with A.serving(product, dict(A.QUIET)) as server:
        single = A.create(server, requester="hal@example.com")["id"]
        model = A.events(A.outbox(server), "hal@example.com", single)
        if len(model) != 1:
            return False, f"a single create enqueued {len(model)} notifications for its requester"
        status, body = post_import(server, [{"title": "Phone line dead", "requester": "ida@example.com"},
                                            {"title": "Mail bounces", "requester": "jo@example.com"}])
        ids = body.get("ids") if isinstance(body, dict) else None
        if status != 201 or not isinstance(ids, list) or len(ids) != 2:
            return False, f"importing 2 tickets answered HTTP {status} {A.short(body)}"
        report = A.outbox(server)
        for tid, to in zip(ids, ("ida@example.com", "jo@example.com")):
            found = A.events(report, to, tid)
            if len(found) != 1:
                wrong.append(f"{len(found)} notifications for {to} about {tid}")
                continue
            event, like = found[0], model[0]
            if (event.get("type"), event.get("status")) != (like.get("type"), like.get("status")) or \
                    event.get("key") != str(like.get("key")).replace(single, tid):
                wrong.append(f"{tid}'s notification {A.short(event)} differs from a single create's {A.short(like)}")
    return A.verdict(wrong, "each imported ticket's requester is notified once, as for a single create")


def import_5000_in_time(base: str, product) -> tuple[bool, str]:
    data = product.scratch() / "tickets.json"
    items = batch(LIMIT)
    payload = json.dumps({"tickets": items}).encode()
    with A.serving(product, {**A.QUIET, "DATA_FILE": str(data)}) as server:
        first = A.create(server, title="Before the big import")["id"]
        address = urllib.parse.urlsplit(server)
        connection = http.client.HTTPConnection(address.hostname, address.port, timeout=WAIT_SECONDS)
        started = time.monotonic()
        try:
            connection.request("POST", "/tickets/import", body=payload, headers={"content-type": "application/json"})
            response = connection.getresponse()
            status, text = response.status, response.read()
        except (TimeoutError, OSError) as error:
            return False, f"no answer to {LIMIT} tickets ({len(payload)} bytes) within {WAIT_SECONDS} s: {error}"
        finally:
            connection.close()
        seconds = time.monotonic() - started
        try:
            body = json.loads(text or b"null")
        except ValueError:
            body = None
        ids = body.get("ids") if isinstance(body, dict) else None
        if status != 201 or not isinstance(ids, list) or body.get("created") != LIMIT or len(ids) != LIMIT:
            return False, f"{LIMIT} tickets ({len(payload)} bytes) answered HTTP {status} {A.short(body)} in {seconds:.1f} s"
        if [number(i) for i in ids] != list(range(number(first) + 1, number(first) + 1 + LIMIT)):
            return False, f"{LIMIT} tickets were given ids that are not the next numbers in order"
        last = A.get(server, ids[-1])
        if last.get("title") != items[-1]["title"]:
            return False, f"the last imported ticket reads {A.short(last)}"
        if seconds > ANSWER_SECONDS:
            return False, f"{LIMIT} tickets answered in {seconds:.1f} s with DATA_FILE set, over {ANSWER_SECONDS:.0f} s"
    return True, f"{LIMIT} tickets ({len(payload)} bytes) answered in {seconds:.1f} s with DATA_FILE set"


def import_persists(base: str, product) -> tuple[bool, str]:
    wrong = []
    data = product.scratch() / "tickets.json"
    env = {**A.QUIET, "DATA_FILE": str(data)}
    with A.serving(product, env) as server:
        status, body = post_import(server, batch(3), actor="migration.bot")
        ids = body.get("ids") if isinstance(body, dict) else None
        if status != 201 or not isinstance(ids, list) or len(ids) != 3:
            return False, f"importing 3 tickets answered HTTP {status} {A.short(body)}"
        before = [A.get(server, tid) for tid in ids]
    with A.serving(product, env) as server:
        after = [A.get(server, tid) for tid in ids]
        if [{k: t.get(k) for k in A.BASE_FIELDS} for t in after] != [{k: t.get(k) for k in A.BASE_FIELDS} for t in before]:
            wrong.append(f"after the restart: {A.short(after)}")
        again = A.create(server)["id"]
        if number(again) != number(ids[-1]) + 1:
            wrong.append(f"the next ticket after the restart is {again}, after {ids[-1]}")
    return A.verdict(wrong, "imported tickets survive a restart from the data file, and numbers go on")


CHECKS = {
    "ticket-lifecycle-unchanged": A.ticket_lifecycle_unchanged,
    "listing-unchanged": A.listing_unchanged,
    "notifications-unchanged": A.notifications_unchanged,
    "restart-keeps-state": A.restart_keeps_state,
    "cli-raw-columns": A.cli_raw_columns,
    "old-data-loads": A.old_data_loads,
    "import-creates-in-order": import_creates_in_order,
    "import-all-or-none": import_all_or_none,
    "import-validates-like-create": import_validates_like_create,
    "import-audited": import_audited,
    "import-notifies": import_notifies,
    "import-5000-in-time": import_5000_in_time,
    "import-persists": import_persists,
}
