"""Held-out acceptance checks for the `ticket-sla` case (style: brownfield), the fourth link of the ticket chain and the first that
changes a rule an earlier link set, read from its prompt and from the base's own documents, and never shown to a model.

``quality.acceptance`` calls each function in ``CHECKS`` as it calls the ticket-escalation checks: with the delivered server's base
URL, and, for a check that takes a second parameter, with the delivered copy (``quality.Product``). The helpers and thirteen of the
checks are ticket_escalation_accept's, loaded from beside this file, so the two cases read the service the same way.

The case starts from the third pass's delivery (``follows``, ``--continue-from``). Thirteen checks are pass-to-pass: everything the
second link's acceptance asked, except one. ``escalation-at-most-once`` is not here: this request replaces the rule it reads ("a
ticket is escalated at most once"), so a correct delivery fails it by design, which is why the case declares an acceptance of its
own and does not inherit the second link's. Three checks are fail-to-pass and read the new rule:

* ``sla-waits-by-priority``: an urgent ticket waits ESCALATE_AFTER_MINUTES and a high one ESCALATE_HIGH_MINUTES, each its own
  variable with its own default, in minutes (a unit mistaken for seconds fails); no other priority is escalated.
* ``sla-second-then-stop``: with the waits at 0 an urgent ticket is told about exactly twice, also across a restart over the data
  file, and a ticket made after the restart is told about twice as well.
* ``sla-second-not-immediate``: a ticket three hours old is escalated at once with the default wait of 60 minutes, and is not
  escalated a second time within seconds: the second waits twice the wait since the first. The data file is written by hand, in the
  base's format, so no delivery's own record of an escalation is assumed.
"""

from __future__ import annotations

import datetime
import importlib.util
import json
from pathlib import Path
import time

_SPEC = importlib.util.spec_from_file_location("shiploop_e2e_held_out_ticket_escalation", Path(__file__).with_name("ticket_escalation_accept.py"))
E = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(E)
A = E.A

ONCALL = E.ONCALL
NOW = E.NOW                                     # ESCALATE_AFTER_MINUTES=0: every urgent ticket is old enough at once
HIGH_NOW = {"ESCALATE_HIGH_MINUTES": "0"}       # and every high one
QUIET = {**E.QUIET, "ESCALATE_HIGH_MINUTES": None}
UNIT_WATCH_SECONDS = E.UNIT_WATCH_SECONDS
STILL_SECONDS = 1.5   # how long a ticket that must not be escalated again is watched


def settled(report_of, tickets) -> dict:
    return {name: len(E.escalations(report_of(), ticket)) for name, ticket in tickets.items()}


def sla_waits_by_priority(base: str, product) -> tuple[bool, str]:
    wrong = []
    scratch = product.scratch()
    with A.serving(product, {**QUIET, "WORKER_INTERVAL_MS": A.TICKS, "NOTIFY_FILE": str(scratch / "urgent.jsonl"), "ONCALL": ONCALL, **NOW}) as server:
        made = {name: A.create(server, title=f"A {name} ticket", priority=name)["id"] for name in ("urgent", "high", "normal", "low")}
        if not A.wait_for(lambda: A.lines_for(scratch / "urgent.jsonl", ONCALL, made["urgent"])):
            wrong.append("with ESCALATE_AFTER_MINUTES=0 the open, unassigned urgent ticket was not escalated")
        time.sleep(A.SETTLE_SECONDS)
        got = settled(lambda: A.outbox(server), made)
        if {name: count for name, count in got.items() if name != "urgent" and count}:
            wrong.append(f"with only the urgent wait at 0, other priorities were escalated: {got}")
    with A.serving(product, {**QUIET, "WORKER_INTERVAL_MS": A.TICKS, "NOTIFY_FILE": str(scratch / "high.jsonl"), "ONCALL": ONCALL, **HIGH_NOW}) as server:
        made = {name: A.create(server, title=f"A {name} ticket", priority=name)["id"] for name in ("urgent", "high", "normal", "low")}
        if not A.wait_for(lambda: A.lines_for(scratch / "high.jsonl", ONCALL, made["high"])):
            wrong.append("with ESCALATE_HIGH_MINUTES=0 the open, unassigned high ticket was not escalated")
        time.sleep(A.SETTLE_SECONDS)
        got = settled(lambda: A.outbox(server), made)
        if {name: count for name, count in got.items() if name != "high" and count}:
            wrong.append(f"with only the high wait at 0, other priorities were escalated (the urgent wait is its own, default 60): {got}")
    with A.serving(product, {**QUIET, "WORKER_INTERVAL_MS": A.TICKS, "ONCALL": ONCALL, "ESCALATE_HIGH_MINUTES": "1"}) as server:
        young = A.create(server, title="Mail is slow", priority="high")["id"]
        time.sleep(UNIT_WATCH_SECONDS)
        if E.escalations(A.outbox(server), young):
            wrong.append(f"with ESCALATE_HIGH_MINUTES=1, {young} was escalated at under 2 seconds old: the unit is minutes")
    return A.verdict(wrong, "an urgent ticket waits ESCALATE_AFTER_MINUTES and a high one ESCALATE_HIGH_MINUTES, in minutes; no other priority is escalated")


def sla_second_then_stop(base: str, product) -> tuple[bool, str]:
    wrong = []
    scratch = product.scratch()
    data, live = scratch / "tickets.json", scratch / "twice.jsonl"
    env = {**QUIET, "DATA_FILE": str(data), "NOTIFY_FILE": str(live), "WORKER_INTERVAL_MS": A.TICKS, "ONCALL": ONCALL, **NOW}
    with A.serving(product, env) as server:
        first = A.create(server, title="Payroll export fails", priority="urgent")["id"]
        A.wait_for(lambda: len(A.lines_for(live, ONCALL, first)) >= 2)
        time.sleep(A.SETTLE_SECONDS * 3)
        before = len(A.lines_for(live, ONCALL, first))
    with A.serving(product, env) as server:  # the same data file, after a restart
        second = A.create(server, title="VPN concentrator down", priority="urgent")["id"]
        A.wait_for(lambda: len(A.lines_for(live, ONCALL, second)) >= 2)
        time.sleep(A.SETTLE_SECONDS * 3)
        after, other = len(A.lines_for(live, ONCALL, first)), len(A.lines_for(live, ONCALL, second))
    if (before, after, other) != (2, 2, 2):
        wrong.append(f"{ONCALL} was told about {first} {before} times before a restart and {after} in all; "
                     f"about {second}, made after it, {other} times; each should be told twice")
    return A.verdict(wrong, "a ticket is escalated twice and never a third time, and a restart over the data file adds none")


def sla_second_not_immediate(base: str, product) -> tuple[bool, str]:
    wrong = []
    scratch = product.scratch()
    data, live = scratch / "old.json", scratch / "old.jsonl"
    stamp = lambda ago: (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=ago)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    made = stamp(3)
    data.write_text(json.dumps({
        "version": 1, "savedAt": stamp(0), "nextNumber": 2,
        "tickets": [{"id": "T-0001", "title": "Core switch down", "priority": "urgent", "requester": "noc@example.com",
                     "status": "open", "created": made, "updated": made}],
        "audit": [{"seq": 1, "ticket": "T-0001", "action": "ticket.created", "actor": "system", "at": made,
                   "changes": {"title": {"from": None, "to": "Core switch down"}, "priority": {"from": None, "to": "urgent"},
                               "requester": {"from": None, "to": "noc@example.com"}, "status": {"from": None, "to": "open"}}}],
        "outbox": {"nextId": 1, "events": []}}))
    env = {**QUIET, "DATA_FILE": str(data), "NOTIFY_FILE": str(live), "WORKER_INTERVAL_MS": A.TICKS, "ONCALL": ONCALL}  # the default waits
    with A.serving(product, env):
        if not A.wait_for(lambda: A.lines_for(live, ONCALL, "T-0001")):
            wrong.append("the three-hour-old urgent ticket was not escalated with the default wait of 60 minutes")
        time.sleep(STILL_SECONDS)
        count = len(A.lines_for(live, ONCALL, "T-0001"))
        if count != 1:
            wrong.append(f"{ONCALL} was told about T-0001 {count} times within seconds; the second escalation waits twice the wait since the first")
    return A.verdict(wrong, "a ticket old enough is escalated at once and is not escalated a second time within seconds")


CHECKS = {
    **{name: check for name, check in E.CHECKS.items() if name != "escalation-at-most-once"},
    "sla-waits-by-priority": sla_waits_by_priority,
    "sla-second-then-stop": sla_second_then_stop,
    "sla-second-not-immediate": sla_second_not_immediate,
}
