"""Held-out acceptance checks for the `ticket-escalation` case (style: brownfield), the follow-on of `ticket-assignment`, read
from its prompt and from the base's own documents, and never shown to a model.

``quality.acceptance`` calls each function in ``CHECKS`` as it calls the ticket-assignment checks: with the delivered server's
base URL, and, for a check that takes a second parameter, with the delivered copy (``quality.Product``). The helpers, and the
ten checks six of these run again, are ticket_assignment_accept's, loaded from beside this file, so the two cases read the
service the same way.

The case starts from the first run's delivery (``follows``, ``--continue-from``), not from the base. Seven checks are
pass-to-pass: the ticket API as the base had it, assignment as the first request asked for it (assign and unassign, its
validation and conflicts, its filters and pages, its notification, its persistence), the command line's raw columns, and,
with the worker off, no background work at all. They measure whether the second run keeps what the first one learned. The
rest are fail-to-pass: the bulk reassignment and the escalation of urgent tickets. Several read a fact the request does not
name: the error envelope (docs/decisions/0004), notifications through the outbox and the worker as the one background loop
(0006, CONTRIBUTING.md), one audit entry per changed ticket (0007), and the data file as the only state that outlives a
restart (0008), which is what "at most once, even across restarts" needs.

ESCALATE_AFTER_MINUTES=0 makes every urgent ticket old enough at once, so the escalation checks wait on the product's worker at a
25 ms interval, with bounded waits; one check sets 1 minute and watches for 1.5 s, which a unit mistaken for seconds fails.
"""

from __future__ import annotations

import importlib.util
import inspect
from pathlib import Path
import time

_SPEC = importlib.util.spec_from_file_location("shiploop_e2e_held_out_ticket_assignment_helpers",
                                               Path(__file__).with_name("ticket_assignment_accept.py"))
A = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(A)

ONCALL = "oncall.lee"
NOW = {"ESCALATE_AFTER_MINUTES": "0"}  # any ticket created before this instant is older than 0 minutes
UNIT_WATCH_SECONDS = 1.5  # with ESCALATE_AFTER_MINUTES=1, a ticket this old must not be escalated; a unit of seconds would
QUIET = {**A.QUIET, "ONCALL": None, "ESCALATE_AFTER_MINUTES": None}  # no worker, no on-call agent: only changes fill the outbox


def reassign(base: str, payload, actor: str | None = None, raw: bytes | None = None) -> tuple[int, object]:
    return A.call(base, "POST", "/tickets/reassign", payload, actor=actor, raw=raw)


def first_request(base: str, product, *checks) -> tuple[bool, str]:
    """Run some of ticket-assignment's checks; pass when all of them pass."""
    failed = []
    for check in checks:
        try:
            ok, note = check(base, product) if len(inspect.signature(check).parameters) > 1 else check(base)
        except Exception as exc:  # one check's crash is that check's failure, not the others'
            ok, note = False, f"raised {exc!r}"
        if not ok:
            failed.append(f"{check.__name__}: {note}")
    return not failed, "; ".join(failed) or f"{len(checks)} checks of the first request still pass"


def escalations(report: dict, ticket: str) -> list:
    """The outbox events naming `ticket` that go to the on-call agent."""
    return A.events(report, ONCALL, ticket)


# --------------------------------------------------------------------------------------------------------------------
# Pass-to-pass: what the base did and what the first run added

def existing_api_kept(base: str) -> tuple[bool, str]:
    return A.ticket_lifecycle_unchanged(base)


def assignment_kept(base: str) -> tuple[bool, str]:
    return first_request(base, None, A.assign_and_unassign, A.assignee_validation, A.assign_state_and_missing)


def assignment_listing_kept(base: str, product) -> tuple[bool, str]:
    return first_request(base, product, A.assignee_filter, A.filters_combine, A.assignee_filter_pages)


def assignment_notified_kept(base: str, product) -> tuple[bool, str]:
    return A.assignee_notified(base, product)


def assignment_persists_kept(base: str, product) -> tuple[bool, str]:
    return A.assignee_persists(base, product)


def cli_raw_columns_kept(base: str, product) -> tuple[bool, str]:
    return A.cli_raw_columns(base, product)


def worker_off_is_quiet(base: str, product) -> tuple[bool, str]:
    with A.serving(product, {**QUIET, "ONCALL": ONCALL, **NOW}) as server:
        tid = A.create(server, title="Payroll export fails", priority="urgent", requester="payroll@example.com")["id"]
        reads = ("/tickets", f"/tickets/{tid}", "/tickets?priority=urgent", "/tickets?assignee=", f"/tickets/{tid}/audit",
                 "/admin/outbox")
        for round_ in (1, 2):
            time.sleep(A.SETTLE_SECONDS)
            for path in reads:
                A.call(server, "GET", path)
            A.call(server, "PATCH", f"/tickets/{tid}", {"title": f"Payroll export fails, round {round_}"})
        report = A.outbox(server)
    others = [event for event in A.events(report, None, tid) if event.get("to") != "payroll@example.com"]
    oncall = A.events(report, ONCALL)
    if others or oncall:
        return False, (f"with WORKER_INTERVAL_MS=0 the outbox gained {A.short(others or oncall)}: background work ran in a request "
                       "or on a timer of its own")
    return True, "with the worker off, reads and edits of an urgent ticket enqueue nothing but the requester's notification"


# --------------------------------------------------------------------------------------------------------------------
# Fail-to-pass: bulk reassignment

def reassign_moves(base: str, product) -> tuple[bool, str]:
    rows = [("open", "normal", "dana.k"), ("in_progress", "high", "dana.k"), ("resolved", "normal", "dana.k"),
            ("closed", "low", "dana.k"), ("open", "urgent", "sam.r"), ("open", "normal", None), ("open", "low", "dana.k")]
    wrong = []
    with A.serving(product, QUIET) as server:
        made = A.seed(server, rows)
        status, body = reassign(server, {"from": "dana.k", "to": "lee.m"})
        moved = [made[0], made[1], made[6]]
        if status != 200 or not isinstance(body, dict) or body.get("moved") != 3 or body.get("ids") != moved:
            wrong.append(f"reassign dana.k to lee.m: HTTP {status} {A.short(body)}, expected moved 3 and ids {moved}")
        after = [A.get(server, tid).get("assignee", "absent") for tid in made]
        if after != ["lee.m", "lee.m", "dana.k", "dana.k", "sam.r", None, "lee.m"]:
            wrong.append(f"assignees after: {after}")
        status, body = reassign(server, {"from": "dana.k", "to": "lee.m"})
        if status != 200 or not isinstance(body, dict) or body.get("moved") != 0 or body.get("ids") != []:
            wrong.append(f"again, with nothing left to move: HTTP {status} {A.short(body)}")
    return A.verdict(wrong, "the open and in-progress tickets of one agent move to the other, answered in id order")


def reassign_validation(base: str, product) -> tuple[bool, str]:
    wrong = []
    with A.serving(product, QUIET) as server:
        [tid] = A.seed(server, [("open", "normal", "dana.k")])
        for label, payload, raw in (("the same agent twice", {"from": "dana.k", "to": "dana.k"}, None),
                                    ("no to", {"from": "dana.k"}, None), ("an empty from", {"from": "", "to": "lee.m"}, None),
                                    ("a 65-character to", {"from": "dana.k", "to": "a" * 65}, None),
                                    ("a number", {"from": "dana.k", "to": 7}, None),
                                    ("a body that is not JSON", None, b'{"from":')):
            status, body = reassign(server, payload, raw=raw)
            if not A.enveloped(status, body, 400, "invalid"):
                wrong.append(f"{label}: HTTP {status} {A.short(body)}")
        if A.get(server, tid).get("assignee") != "dana.k":
            wrong.append(f"a refused reassignment moved {tid}")
    return A.verdict(wrong, "the same agent twice and a malformed body are 400 invalid in the envelope, and move nothing")


def reassign_notifies(base: str, product) -> tuple[bool, str]:
    wrong = []
    scratch = product.scratch()
    quiet_file, live_file = scratch / "quiet.jsonl", scratch / "live.jsonl"
    with A.serving(product, {**QUIET, "NOTIFY_FILE": str(quiet_file)}) as server:
        made = A.seed(server, [("open", "normal", "dana.k"), ("in_progress", "normal", "dana.k"), ("open", "normal", "sam.r")])
        reassign(server, {"from": "dana.k", "to": "lee.m"})
        report = A.outbox(server)
        pending = [len(A.events(report, "lee.m", tid, ("pending",))) for tid in made]
        if pending != [1, 1, 0]:
            wrong.append(f"with the worker off, lee.m has pending notifications {pending} for {made}")
        if A.lines(quiet_file):
            wrong.append(f"with the worker off, {len(A.lines(quiet_file))} notifications were delivered anyway")
    with A.serving(product, {**QUIET, "WORKER_INTERVAL_MS": A.TICKS, "NOTIFY_FILE": str(live_file)}) as server:
        made = A.seed(server, [("open", "normal", "dana.k"), ("open", "high", "dana.k")])
        reassign(server, {"from": "dana.k", "to": "lee.m"})
        if not A.wait_for(lambda: all(A.lines_for(live_file, "lee.m", tid) for tid in made)):
            wrong.append("the worker did not deliver lee.m's notifications")
        time.sleep(A.SETTLE_SECONDS)
        delivered = [len(A.lines_for(live_file, "lee.m", tid)) for tid in made]
        if delivered != [1, 1]:
            wrong.append(f"lee.m was delivered {delivered} notifications for {made}")
    return A.verdict(wrong, "each moved ticket's new agent is notified through the outbox, once")


def reassign_audited(base: str, product) -> tuple[bool, str]:
    wrong = []
    with A.serving(product, QUIET) as server:
        made = A.seed(server, [("open", "normal", "dana.k"), ("in_progress", "high", "dana.k")])
        known = {tid: len(A.history(server, tid)) for tid in made}
        status, _body = reassign(server, {"from": "dana.k", "to": "lee.m"}, actor="lead.ana")
        for tid in made:
            added = A.history(server, tid)[known[tid]:]
            change = (added[0].get("changes") or {}).get("assignee") if len(added) == 1 and isinstance(added[0], dict) else None
            if len(added) != 1 or added[0].get("actor") != "lead.ana" or change != {"from": "dana.k", "to": "lee.m"}:
                wrong.append(f"{tid} (HTTP {status}): new audit entries {A.short(added)}")
    return A.verdict(wrong, "each moved ticket gains one audit entry with the actor and the assignee before and after")


# --------------------------------------------------------------------------------------------------------------------
# Fail-to-pass: escalation

def escalation_notifies_oncall(base: str, product) -> tuple[bool, str]:
    wrong = []
    scratch = product.scratch()
    live_file, quiet_file = scratch / "oncall.jsonl", scratch / "no-oncall.jsonl"
    with A.serving(product, {**QUIET, "WORKER_INTERVAL_MS": A.TICKS, "NOTIFY_FILE": str(live_file), "ONCALL": ONCALL, **NOW}) as server:
        tid = A.create(server, title="Payroll export fails", priority="urgent", requester="payroll@example.com")["id"]
        if not A.wait_for(lambda: A.lines_for(live_file, ONCALL, tid)):
            wrong.append(f"no escalation of {tid} was delivered to {ONCALL} within {A.DELIVERY_SECONDS:.0f} s")
        if not escalations(A.outbox(server), tid):
            wrong.append(f"the outbox holds no notification of {tid} for {ONCALL}")
    with A.serving(product, {**QUIET, "WORKER_INTERVAL_MS": A.TICKS, "NOTIFY_FILE": str(quiet_file), **NOW}) as server:
        tid = A.create(server, title="Door badge system down", priority="urgent", requester="facilities@example.com")["id"]
        A.wait_for(lambda: A.lines_for(quiet_file, "facilities@example.com", tid))  # the worker runs
        time.sleep(A.SETTLE_SECONDS)
        others = [event for event in A.events(A.outbox(server), None, tid) if event.get("to") != "facilities@example.com"]
        if others:
            wrong.append(f"without ONCALL, {tid} was escalated: {A.short(others)}")
    return A.verdict(wrong, "an old, open, unassigned urgent ticket is escalated to ONCALL through the outbox; without ONCALL, nothing is")


def escalation_rules(base: str, product) -> tuple[bool, str]:
    wrong = []
    scratch = product.scratch()
    data, live_file = scratch / "tickets.json", scratch / "rules.jsonl"
    with A.serving(product, {**QUIET, "DATA_FILE": str(data)}) as server:  # tickets made with no worker and no on-call agent
        urgent = A.create(server, title="Core switch down", priority="urgent")["id"]
        assigned = A.create(server, title="Core router flapping", priority="urgent")["id"]
        A.assign(server, assigned, "dana.k")
        high = A.create(server, title="Mail is slow", priority="high")["id"]
        working = A.create(server, title="Storage array degraded", priority="urgent")["id"]
        A.move(server, working, "in_progress")
        resolved = A.create(server, title="Backup failed", priority="urgent")["id"]
        A.move(server, resolved, "in_progress", "resolved")
    with A.serving(product, {**QUIET, "DATA_FILE": str(data), "NOTIFY_FILE": str(live_file), "WORKER_INTERVAL_MS": A.TICKS,
                        "ONCALL": ONCALL, **NOW}) as server:
        if not A.wait_for(lambda: A.lines_for(live_file, ONCALL, urgent)):
            wrong.append(f"the open, unassigned urgent ticket {urgent} was not escalated")
        time.sleep(A.SETTLE_SECONDS)
        report = A.outbox(server)
        for label, tid in (("assigned", assigned), ("high", high), ("in-progress", working), ("resolved", resolved)):
            if escalations(report, tid) or A.lines_for(live_file, ONCALL, tid):
                wrong.append(f"the {label} ticket {tid} was escalated")
    fresh = scratch / "fresh.json"
    with A.serving(product, {**QUIET, "DATA_FILE": str(fresh)}) as server:
        young = A.create(server, title="Phones down on floor 3", priority="urgent")["id"]
    with A.serving(product, {**QUIET, "DATA_FILE": str(fresh), "WORKER_INTERVAL_MS": A.TICKS, "ONCALL": ONCALL,
                        "ESCALATE_AFTER_MINUTES": "1"}) as server:
        time.sleep(UNIT_WATCH_SECONDS)
        if escalations(A.outbox(server), young):
            wrong.append(f"with ESCALATE_AFTER_MINUTES=1, {young} was escalated at under 2 seconds old")
    return A.verdict(wrong, "only open, unassigned, urgent tickets older than ESCALATE_AFTER_MINUTES minutes are escalated")


def escalation_at_most_once(base: str, product) -> tuple[bool, str]:
    wrong = []
    scratch = product.scratch()
    data, live_file = scratch / "tickets.json", scratch / "oncall.jsonl"
    with A.serving(product, {**QUIET, "DATA_FILE": str(data)}) as server:
        first = A.create(server, title="Payroll export fails", priority="urgent")["id"]
    env = {**QUIET, "DATA_FILE": str(data), "NOTIFY_FILE": str(live_file), "WORKER_INTERVAL_MS": A.TICKS, "ONCALL": ONCALL, **NOW}
    with A.serving(product, env) as server:
        if not A.wait_for(lambda: A.lines_for(live_file, ONCALL, first) and A.events(A.outbox(server), ONCALL, first, ("sent",))):
            wrong.append(f"{first} was not escalated and recorded as sent")
        time.sleep(A.SETTLE_SECONDS)
        before = len(A.lines_for(live_file, ONCALL, first))
    with A.serving(product, env) as server:  # the same data file, after a restart
        second = A.create(server, title="VPN concentrator down", priority="urgent")["id"]
        A.wait_for(lambda: A.lines_for(live_file, ONCALL, second))  # the restarted worker escalates
        time.sleep(A.SETTLE_SECONDS)
        after, other = len(A.lines_for(live_file, ONCALL, first)), len(A.lines_for(live_file, ONCALL, second))
    if (before, after, other) != (1, 1, 1):
        wrong.append(f"{ONCALL} was told about {first} {before} times before a restart and {after} times in all; "
                     f"about {second}, created after it, {other} times")
    return A.verdict(wrong, "each ticket is escalated once, and a restart with the data file escalates it no second time")


CHECKS = {
    "existing-api-kept": existing_api_kept,
    "assignment-kept": assignment_kept,
    "assignment-listing-kept": assignment_listing_kept,
    "assignment-notified-kept": assignment_notified_kept,
    "assignment-persists-kept": assignment_persists_kept,
    "cli-raw-columns-kept": cli_raw_columns_kept,
    "worker-off-is-quiet": worker_off_is_quiet,
    "reassign-moves": reassign_moves,
    "reassign-validation": reassign_validation,
    "reassign-notifies": reassign_notifies,
    "reassign-audited": reassign_audited,
    "escalation-notifies-oncall": escalation_notifies_oncall,
    "escalation-rules": escalation_rules,
    "escalation-at-most-once": escalation_at_most_once,
}
