#!/usr/bin/env python3
"""HTTP probes for the own checks of the `ticket-sla` case, run by serve.py against the delivered server.

    python3 "$E2E_CHECKS/serve.py" --start "node src/server.js" -- python3 "$E2E_CHECKS/ticket_sla_probe.py" MODE [TICKET]

serve.py puts the server's address in BASE. The on-call agent is ``check.oncall`` (ONCALL in the check's environment). A mode exits 0
when its expectation holds, else a code that says which: 2 a ticket could not be made, 3 an escalation that should have happened
did not, 4 one that should not have happened did. Every wait is a ceiling and every watch a short fixed time, not a tuning value.

* ``urgent``: with ESCALATE_AFTER_MINUTES=0 and the high wait left at its default, an urgent ticket is escalated and a high, a
  normal and a low one are not.
* ``high``: with ESCALATE_HIGH_MINUTES=0 and the urgent wait long, a high ticket is escalated and an urgent, a normal and a low
  one are not.
* ``twice``: with both waits 0, an urgent ticket is escalated a second time and then no third time.
* ``still TICKET``: on a restarted service over the same data file, TICKET has been escalated twice and stays at two.
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request

ONCALL = "check.oncall"
WAIT_SECONDS = 8.0   # a ceiling for an escalation to appear at a 50 ms worker interval
WATCH_SECONDS = 1.5  # how long to keep watching for an escalation that must not come
POLL_SECONDS = 0.05


def call(method: str, path: str, body=None) -> tuple[int, object]:
    request = urllib.request.Request(os.environ["BASE"] + path, method=method, data=None if body is None else json.dumps(body).encode(),
                                     headers={"content-type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=5) as reply:
            return reply.status, json.loads(reply.read() or b"null")
    except urllib.error.HTTPError as error:
        try:
            return error.code, json.loads(error.read() or b"null")
        except ValueError:
            return error.code, None


def make(priority: str, title: str) -> str:
    status, body = call("POST", "/tickets", {"title": title, "requester": "check@example.com", "priority": priority})
    if status != 201 or not isinstance(body, dict):
        sys.exit(2)
    return body["id"]


def told(ticket: str) -> int:
    """How many outbox events, pending, sent or dead, bring `ticket` to the on-call agent."""
    _status, box = call("GET", "/admin/outbox")
    box = box if isinstance(box, dict) else {}
    events = [event for state in ("pending", "sent", "dead") for event in box.get(state) or []]
    return sum(1 for event in events if isinstance(event, dict) and event.get("to") == ONCALL and ticket in json.dumps(event))


def wait_for(condition, seconds: float = WAIT_SECONDS) -> bool:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if condition():
            return True
        time.sleep(POLL_SECONDS)
    return condition()


def watch(seconds: float = WATCH_SECONDS) -> None:
    time.sleep(seconds)


def only(priority: str) -> int:
    made = {name: make(name, f"A {name} ticket") for name in ("urgent", "high", "normal", "low")}
    if not wait_for(lambda: told(made[priority])):
        return 3
    watch()
    return 4 if any(told(ticket) for name, ticket in made.items() if name != priority) else 0


def twice(argv: list[str]) -> int:
    ticket = make("urgent", "Core switch down")
    if not wait_for(lambda: told(ticket) >= 2):
        return 3
    watch()
    return 0 if told(ticket) == 2 else 4


def still(argv: list[str]) -> int:
    if len(argv) != 1:
        return 64
    if told(argv[0]) != 2:
        return 3
    watch()
    return 0 if told(argv[0]) == 2 else 4


# One word each: the suite's helper-script test reads `"$E2E_CHECKS/ticket_sla_probe.py" MODE` in a case's check and looks for `"MODE":` here.
MODES = {"urgent": lambda argv: only("urgent"), "high": lambda argv: only("high"), "twice": twice, "still": still}


def main(argv: list[str]) -> int:
    mode = MODES.get(argv[0]) if argv else None
    if mode is None:
        print(f"unknown mode {argv[:1]!r}; known: {', '.join(MODES)}", file=sys.stderr)
        return 64
    return mode(argv[1:])


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
