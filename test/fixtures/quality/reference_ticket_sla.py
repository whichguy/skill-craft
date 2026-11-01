#!/usr/bin/env python3
"""The reference delivery of the `ticket-sla` case, the fourth link of the ticket chain and the first that changes an earlier rule,
for calibrating its checks (cases.json: the case's own checks and its retention checks), its hidden acceptance
(test/shiploop_e2e/checks/ticket_sla_accept.py), the base's pristine tests and the earlier links' checks.

    python3 reference_ticket_sla.py DEST [--variant NAME]

writes a delivery into the empty folder DEST. A follow-on starts from the run before it, so every variant starts from
ticket-comments' reference (reference_ticket_comments.py), which stands in for the third pass, and that from ticket-escalation's
and ticket-assignment's. The variants:

* ``base``: the comments reference alone, as the fourth pass starts. It must fail every check of the new rule and pass the checks
  the earlier links own.
* ``reference``: the prompt done. ``TicketStore.escalate`` replaces ``escalateUrgent``: an urgent ticket waits ESCALATE_AFTER_MINUTES,
  a high one ESCALATE_HIGH_MINUTES, no other priority is escalated, and a ticket is told about a second time once it has stayed open
  and unassigned for twice its wait since the first, and never a third. The outbox keeps each escalation, sent or not, under its own
  key (``ticket.escalated:<id>``, then ``:2``) and the data file keeps the outbox, which is what keeps the count across a restart. The
  test that said "escalated once" is changed by the request, as the prompt says.
* ``alternative``: the same behaviour written another way, for the hidden acceptance not to fit one delivery. The count lives on the
  ticket record (``escalations``, a list of times that the data file keeps), not in the outbox's history.
* each name of DEFECTS: the reference with one targeted change, a sentence of the request broken. Two are seen only by the hidden
  acceptance (``second-immediate`` and ``high-unit-seconds``): the own checks use a wait of 0, which neither of them touches.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import reference_ticket_assignment as first  # noqa: E402  (the edit helpers)
import reference_ticket_comments as third  # noqa: E402  (the third pass's stand-in, which this one starts from)
import reference_ticket_escalation as second  # noqa: E402  (where the rule being changed was written)


def _slice(text: str, start: str, end: str) -> str:
    """`text` from the first `start` to just after the first `end` that follows it."""
    at = text.index(start)
    return text[at:text.index(end, at) + len(end)]


# What the second link wrote and this one replaces: the store method, the worker's job and the test that states the old rule.
OLD_ESCALATE = _slice(second.REASSIGN_AND_ESCALATE, "  /**\n   * Tell `oncall` about each open", "    return escalated;\n  }\n")
OLD_JOB = ("/** The escalation job: urgent tickets nobody has picked up are brought to the on-call agent, once each. */\n"
           "function escalateUrgent({ store, oncall, afterMinutes }) {\n"
           "  return { name: 'escalate-urgent', run: () => ({ escalated: store.escalateUrgent({ oncall, afterMinutes }).length }) };\n}\n\n"
           "module.exports = { Worker, deliverOutbox, escalateUrgent };")
OLD_TEST = _slice(second.REFERENCE_ADDED["test/escalation.test.js"],
                  "test('urgent, open, unassigned tickets are escalated once, after the wait', () => {", "\n});\n")

ESCALATE_BY_OUTBOX = r"""  /**
   * Tell `oncall` about each open, unassigned ticket that has waited long enough for its priority: an urgent one `urgentMinutes`,
   * a high one `highMinutes`, no other priority at all. A ticket is told about a second time once it has stayed open and
   * unassigned for twice its wait since the first, and never a third. The outbox keeps each escalation, sent or not, under its own
   * key (`ticket.escalated:<id>`, then `:2`), and the data file keeps the outbox, so the count survives a restart. Returns the ids
   * escalated now.
   */
  escalate({ oncall, urgentMinutes, highMinutes }) {
    const now = this.clock.now();
    const waits = { urgent: urgentMinutes, high: highMinutes };
    const escalated = [];
    for (const ticket of this.tickets.values()) {
      const wait = waits[ticket.priority];
      if (wait === undefined || ticket.status !== 'open' || ticket.assignee !== null) continue;
      const firstKey = `ticket.escalated:${ticket.id}`;
      const secondKey = `${firstKey}:2`;
      const first = this.outbox.events.find((event) => event.key === firstKey);
      let key = firstKey;
      if (!first) {
        if (Date.parse(ticket.created) >= now.getTime() - wait * 60_000) continue;
      } else {
        if (this.outbox.hasKey(secondKey) || Date.parse(first.created) >= now.getTime() - 2 * wait * 60_000) continue;
        key = secondKey;
      }
      this.notify(ticket, 'ticket.escalated', oncall, now.toISOString(), key);
      escalated.push(ticket.id);
    }
    if (escalated.length) this.save();
    return escalated;
  }
"""

ESCALATE_BY_RECORD = r"""  /**
   * Tell `oncall` about each open, unassigned ticket that has waited long enough for its priority: an urgent one `urgentMinutes`,
   * a high one `highMinutes`, no other priority at all. The ticket record keeps the times it was escalated (`escalations`, saved in
   * the data file): a second time once it has stayed open and unassigned for twice its wait since the first, never a third.
   * Returns the ids escalated now.
   */
  escalate({ oncall, urgentMinutes, highMinutes }) {
    const now = this.clock.now();
    const waits = { urgent: urgentMinutes, high: highMinutes };
    const escalated = [];
    for (const ticket of this.tickets.values()) {
      const wait = waits[ticket.priority];
      if (wait === undefined || ticket.status !== 'open' || ticket.assignee !== null || ticket.escalations.length >= 2) continue;
      const due = ticket.escalations.length === 0
        ? Date.parse(ticket.created) + wait * 60_000
        : Date.parse(ticket.escalations[0]) + 2 * wait * 60_000;
      if (due >= now.getTime()) continue;
      ticket.escalations.push(now.toISOString());
      this.notify(ticket, 'ticket.escalated', oncall, now.toISOString(), `ticket.escalated:${ticket.id}:${ticket.escalations.length}`);
      escalated.push(ticket.id);
    }
    if (escalated.length) this.save();
    return escalated;
  }
"""

NEW_JOB = ("/** The escalation job: urgent and high tickets nobody has picked up are brought to the on-call agent, and again after twice\n"
           " * their wait. */\n"
           "function escalate({ store, oncall, urgentMinutes, highMinutes }) {\n"
           "  return { name: 'escalate', run: () => ({ escalated: store.escalate({ oncall, urgentMinutes, highMinutes }).length }) };\n}\n\n"
           "module.exports = { Worker, deliverOutbox, escalate };")

NEW_TEST = r"""test('urgent and high tickets are escalated after their own wait and a second time after twice that, never a third', () => {
  const clock = manualClock();
  const store = new TicketStore({ clock });
  store.create({ title: 'Core switch down', requester: 'noc@example.com', priority: 'urgent' }, 'system');
  store.create({ title: 'Mail is slow', requester: 'li@example.com', priority: 'high' }, 'system');
  store.create({ title: 'Printer jams', requester: 'li@example.com', priority: 'normal' }, 'system');
  const escalate = () => store.escalate({ oncall: 'oncall.lee', urgentMinutes: 60, highMinutes: 240 });
  const minutes = (count) => clock.advance(count * 60_000);
  assert.deepEqual(escalate(), [], 'not before the wait');
  minutes(61);
  assert.deepEqual(escalate(), ['T-0001'], 'the urgent ticket after 60 minutes, the high one not yet');
  store.recordDelivery(store.outboxReport().pending.find((event) => event.to === 'oncall.lee').id);
  minutes(60);
  assert.deepEqual(escalate(), [], 'not a second time before twice the wait since the first');
  minutes(120);
  assert.deepEqual(escalate(), ['T-0001', 'T-0002'], 'the urgent one again, and the high one after its own wait');
  minutes(24 * 60);
  assert.deepEqual(escalate(), ['T-0002'], 'the high one a second time; the urgent one has had both');
  minutes(24 * 60);
  assert.deepEqual(escalate(), [], 'at most twice, and never the normal one');
});
"""

SHARED = [
    ("src/config.js", "  escalateAfterMinutes: 60,\n", "  escalateAfterMinutes: 60,\n  escalateHighMinutes: 240,\n"),
    ("src/config.js", "    escalateAfterMinutes: wholeNumber(env, 'ESCALATE_AFTER_MINUTES', DEFAULTS.escalateAfterMinutes, { max: 7 * 24 * 60 }),\n",
     "    escalateAfterMinutes: wholeNumber(env, 'ESCALATE_AFTER_MINUTES', DEFAULTS.escalateAfterMinutes, { max: 7 * 24 * 60 }),\n"
     "    escalateHighMinutes: wholeNumber(env, 'ESCALATE_HIGH_MINUTES', DEFAULTS.escalateHighMinutes, { max: 7 * 24 * 60 }),\n"),
    ("src/worker.js", OLD_JOB, NEW_JOB),
    ("src/server.js", "const { Worker, deliverOutbox, escalateUrgent } = require('./worker');",
     "const { Worker, deliverOutbox, escalate } = require('./worker');"),
    ("src/server.js", "    jobs.push(escalateUrgent({ store, oncall: config.oncall, afterMinutes: config.escalateAfterMinutes ?? 60 }));\n",
     "    jobs.push(escalate({ store, oncall: config.oncall, urgentMinutes: config.escalateAfterMinutes ?? 60,\n"
     "      highMinutes: config.escalateHighMinutes ?? 240 }));\n"),
    ("src/templates.js", "  'ticket.escalated': (event) => ({\n    subject: `[${event.ticket}] Urgent and unassigned`,\n"
     "    body: `Ticket ${event.ticket} \"${event.data.title}\" is urgent and nobody has it yet.`,\n  }),\n",
     "  'ticket.escalated': (event) => ({\n    subject: `[${event.ticket}] Waiting for an agent`,\n"
     "    body: `Ticket ${event.ticket} \"${event.data.title}\" has waited and nobody has it yet.`,\n  }),\n"),
    ("test/escalation.test.js", OLD_TEST, NEW_TEST),
]

REFERENCE = [("src/store.js", OLD_ESCALATE, ESCALATE_BY_OUTBOX), *SHARED]

ALTERNATIVE = [
    ("src/store.js", OLD_ESCALATE, ESCALATE_BY_RECORD),
    ("src/store.js", "status: 'open', assignee: null, comments: [], created: at, updated: at };",
     "status: 'open', assignee: null, comments: [], escalations: [], created: at, updated: at };"),
    ("src/persistence.js", "    comments: (ticket.comments ?? []).map(commentRecord),\n",
     "    comments: (ticket.comments ?? []).map(commentRecord),\n    escalations: [...(ticket.escalations ?? [])],\n"),
    *SHARED,
]

WAITS = "const waits = { urgent: urgentMinutes, high: highMinutes };"
SECOND_GUARD = "        if (this.outbox.hasKey(secondKey) || Date.parse(first.created) >= now.getTime() - 2 * wait * 60_000) continue;\n"
FIRST_LOOKUP = "      const first = this.outbox.events.find((event) => event.key === firstKey);\n"
NOTIFY_LINE = "      this.notify(ticket, 'ticket.escalated', oncall, now.toISOString(), key);\n"

DEFECTS = {
    # The request: a high ticket escalates too, after ESCALATE_HIGH_MINUTES.
    "high-never-escalated": [("src/store.js", WAITS, "const waits = { urgent: urgentMinutes };")],
    # The request: the high wait is its own variable, not the urgent one.
    "high-uses-urgent-wait": [("src/store.js", WAITS, "const waits = { urgent: urgentMinutes, high: urgentMinutes };")],
    # The request: no other priority is escalated.
    "normal-escalated": [("src/store.js", "      const wait = waits[ticket.priority];\n", "      const wait = waits[ticket.priority] ?? urgentMinutes;\n")],
    # The request: a second escalation exists (the old rule kept).
    "escalated-once-only": [("src/store.js", SECOND_GUARD, "        continue;\n")],
    # The request: and it is the last.
    "third-escalation": [("src/store.js", SECOND_GUARD,
                          "        if (Date.parse(first.created) >= now.getTime() - 2 * wait * 60_000) continue;\n")],
    # The request: the second waits twice the wait since the first (the own checks use a wait of 0, which cannot tell).
    "second-immediate": [("src/store.js", SECOND_GUARD, "        if (this.outbox.hasKey(secondKey)) continue;\n")],
    # The request: at most twice, even across restarts of the service (the count must be in the data file).
    "count-lost-on-restart": [
        ("src/store.js", FIRST_LOOKUP, "      const first = this.seenEscalations?.get(ticket.id);\n"),
        ("src/store.js", NOTIFY_LINE,
         NOTIFY_LINE + "      if (key === firstKey) (this.seenEscalations ??= new Map()).set(ticket.id, { created: now.toISOString() });\n")],
    # The request: the waits are in minutes (the own checks use a wait of 0, which cannot tell).
    "high-unit-seconds": [("src/store.js", WAITS, "const waits = { urgent: urgentMinutes, high: highMinutes / 60 };")],
}
VARIANTS = ("base", "reference", "alternative", *DEFECTS)


def build(dest: Path, variant: str = "reference") -> Path:
    """Write the delivery of `variant` into `dest` (created if missing) and return it."""
    if variant not in VARIANTS:
        raise ValueError(f"unknown variant {variant!r}; known: {', '.join(VARIANTS)}")
    dest = third.build(dest, "reference")
    if variant == "base":
        return dest
    first.apply(dest, ALTERNATIVE if variant == "alternative" else REFERENCE, variant if variant == "alternative" else "reference")
    first.apply(dest, DEFECTS.get(variant, ()), f"defect {variant}")
    return dest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("dest", type=Path)
    parser.add_argument("--variant", default="reference", choices=VARIANTS)
    args = parser.parse_args()
    print(build(args.dest, args.variant))


if __name__ == "__main__":
    main()
