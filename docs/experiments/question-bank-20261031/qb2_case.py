"""QB2's case (README.md): one long, loosely worded request over the help desk fixture, what its repository really holds,
and the 17 items the request raises with what a good intake does about each.

The request is written in the owner's dictated style (long, conversational, naming installed skills and internet jargon,
pointing at things it does not state).  Every repository fact below was read from
test/shiploop_e2e/fixtures/node-tickets on 2026-10-31 (README.md, CONTRIBUTING.md, docs/api.md, docs/decisions/0006,
src/templates.js, src/tickets/query.js, scripts/weekly-report.js); the one absence (OldTracker, a report window, a bulk
endpoint) was checked with a recursive search.
"""

SENTENCES = [
    "OK so this is for the tickets service in this folder, the help desk one.",
    ("What I want is that when an agent closes a ticket the requester gets the same kind of heads-up they get when it's "
    "resolved, but I don't want to send a second one if they just got one, so make it smart about that."),
    ("It should go out right away, but also not spam people if an agent closes a pile of tickets in one go, so batch it, "
    "whatever's reasonable."),
    ("While you're in there, the list endpoint should let me see just the closed tickets from the usual window, there's a "
    "window we use for the weekly report I think, so use that."),
    "And the filters should work together, the way the docs say.",
    "I'm pretty sure they do already but double check.",
    ("I want you to run this as an until loop with the exit being green tests plus the thing actually working against a "
    "running server, and back-chain it first so we don't find preconditions halfway through."),
    "If you want to go ralph-style overnight that's fine, but put a cap on it so it doesn't run away.",
    "Tests should be real, not vibes, and no slop in the docs.",
    "Don't touch the outbox retry logic, we're moving off OldTracker soon and I don't want to redo that twice.",
    "Keep it zero-dependency like the rest.",
    ("The close should stay idempotent but also give a 409 if the ticket is already closed, whatever makes sense, and the "
    "audit log should say who closed it."),
    "Performance should be snappy, I don't care about exact numbers, but closing 500 tickets in one bulk call has to work.",
]
# paragraph breaks fall after these sentence numbers (1-based)
BREAKS = {1, 3, 6, 9}

CONTEXT = "an existing Node.js help desk ticket service (its README.md describes it)"
SAMPLES_N = 5  # outputs per arm

SKILLS = [
    ("until-loop", ("Interpret a natural-language request as work to pursue, a continuation condition, and an "
                   "evidence-based exit condition; adapt each next action until the outcome is established or a real "
                   "blocker requires attention.")),
    ("backchain", ("Backward planner: an implementation task gets a dependency-aware, precondition-first plan before "
                  "coding (dependency graphs, scheduler-ready step graphs).")),
    ("plan-dispatcher", ("Execute or resume an agreed dependency graph with one main dispatcher and parallel native "
                        "workers.")),
    ("improve", ("A deliberate review-and-improvement loop over a repository candidate until a pass finds only trivial "
                "changes.")),
    ("in-parallel", ("Coordinate independent native workers, verify their returns, and report progress and optional Git "
                    "delivery.")),
    ("ralph-loop", "Start Ralph Loop in the current session."),
    ("loop", "Run a prompt or slash command on a recurring interval."),
    ("schedule", "Create, update, list or run scheduled cloud agents (routines) on a cron schedule."),
    ("code-review", "Review the current diff or a pull request for correctness bugs."),
    ("simplify", "Review changed code for reuse, simplification and efficiency, then apply the fixes."),
    ("ask", "Ask another model for a second opinion or plan review."),
    ("shiploop", "Markdown-authoritative delivery harness: start or resume once and follow the script's action packets."),
]

FACTS = """\
- Notifications: `ticket.created` and `ticket.resolved` have templates in src/templates.js; there is none for closed
  tickets, and an event with no template goes dead after its retries (docs/decisions/0006). A new kind of notification
  needs a template (CONTRIBUTING.md). Request handlers never call the notifier; a change enqueues the notification in the
  store and the worker delivers it.
- Outbox key: enqueueing a key that is still pending changes nothing, so the same news is not queued twice (decision 6);
  once a notification is sent, nothing stops an identical one being enqueued.
- Delivery: one background worker runs every WORKER_INTERVAL_MS (500 by default) and delivers the due notifications;
  they arrive up to one interval late. The worker is the service's one background loop (decision 6, CONTRIBUTING.md).
- Weekly report (scripts/weekly-report.js): counts tickets by status for a week-of date; it has no time window. The only
  "7 days" in the repository is the resolved notification's "Reply within 7 days to reopen it." No setting or document
  defines a window for closed tickets. GET /tickets has the filters status and priority, limit and cursor only.
- Filters: docs/api.md says "Filters combine: a ticket is listed only when it matches every filter given". The code
  (matchesFilters in src/tickets/query.js) lists a ticket when ANY given filter matches (`some`).
- Lifecycle (docs/api.md, src/tickets/states.js): open, in_progress, resolved, closed; POST /tickets/:id/transition
  {"to": ...}; closed is final; a move the lifecycle does not allow, and any change to a closed ticket, answers 409
  `conflict` (CONTRIBUTING.md: "the ticket's state does not allow this" is a 409). Closing exists today as a transition
  from resolved to closed.
- Actor and audit: a request may name the actor in the X-Actor header (at most 64 characters, `system` without it); the
  store records it in the audit entry of every change; the transition handler already passes it.
- Bulk: the repository has no bulk endpoint, and no document describes one. Every change saves the data file in one step
  when DATA_FILE is set. MAX_BODY_BYTES is 65536 by default.
- Conventions (CONTRIBUTING.md): no dependencies (package.json has none); errors through the envelope; changes go
  through the store; notifications only through the outbox; background work only in the worker; listings are cursor
  pages. The outbox retry logic is src/backoff.js with src/outbox.js.
- OldTracker, "cutover" and any migration appear nowhere in the repository, and no installed skill is named for them.
- Installed skills offered by the host: until-loop, backchain, plan-dispatcher, improve, in-parallel, ralph-loop, loop,
  schedule, code-review, simplify, ask, shiploop."""

# id, group, whether the repository, the skills list or general knowledge settles it ("env") or only a decision does
# ("decision"), the part of the request it concerns, and what a good intake does about it
ITEMS = [
    ("J1", "skill", "env", ("S7: run this as an until loop with the exit being green tests plus the thing working against a "
     "running server"),
     ("Recognises 'until loop' as the installed until-loop skill (a loop that continues until an evidence-based exit "
     "condition holds) and records the exit the request states: green tests plus a check against a running server. Wrong: "
     "another meaning, or ignoring it.")),
    ("J2", "skill", "env", "S7: back-chain it first so we don't find preconditions halfway through",
     ("Recognises 'back-chain' as the installed backchain skill (backward, precondition-first dependency planning) and "
     "records that a plan of preconditions comes before the work.")),
    ("J4", "skill", "env", "S8: go ralph-style overnight, but put a cap on it so it doesn't run away",
     ("Recognises 'ralph-style' as the installed ralph-loop skill or the Ralph loop technique (the same prompt run in a "
     "loop until done), notes that the cap is not given (iterations or time), and records a default cap or asks.")),
    ("J3", "slang", "env", "S9: tests should be real, not vibes",
     ("Reads 'vibes' as: tests must really exercise and assert behaviour (run, with outcomes checked), not placeholders or "
     "mocks that assert nothing.")),
    ("J6", "slang", "env", "S9: no slop in the docs",
     "Reads 'slop' as generic, padded or low-value filler text; docs should be specific and necessary."),
    ("J5", "unknown", "decision", "S10: we're moving off OldTracker soon",
     ("'OldTracker' appears nowhere in the repository or the skills. A good intake flags it as an unknown name, states a "
     "best reading (a legacy tracker being replaced) with low confidence, treats the sentence's reason as non-blocking, "
     "and invents no facts about it.")),
    ("R1", "referent", "env", "S2: the same kind of heads-up they get when it's resolved",
     ("Finds by reading that resolved tickets notify the requester through a ticket.resolved template and the outbox, that "
     "no template exists for closed tickets, and that a new notification kind needs a template (an event with none goes "
     "dead).")),
    ("R3", "referent", "env", "S2: I don't want to send a second one if they just got one",
     ("Notes the outbox key dedupe and that it suppresses an identical key only while it is still pending, so 'if they "
     "just got one' (already sent) is not covered and needs a decision or a recorded default.")),
    ("R2", "referent", "env", "S4: the usual window, there's a window we use for the weekly report I think",
     ("Checks the weekly report and finds it has no window (it counts tickets by status): the request's 'usual window' "
     "does not exist in the repository. Says so and records a default window or flags it for confirmation, rather than "
     "asserting a window.")),
    ("C1", "conflict", "decision", "S3: go out right away, but batch it",
     ("Spots that 'right away' and 'batch it' pull apart and takes or asks for an explicit reading (for example deliver on "
     "the next worker run, batching meaning one worker run delivers many), rather than silently satisfying only one.")),
    ("C2", "conflict", "env", "S12: idempotent but also give a 409 if the ticket is already closed",
     ("Spots that 'idempotent' and '409 if already closed' pull apart and settles it from the repository's conventions: "
     "closed is final and a move the lifecycle does not allow is a 409 conflict, so a repeated close is a 409; or flags "
     "it with that evidence.")),
    ("C3", "conflict", "env", ("S5-S6: the filters should work together, the way the docs say; I'm pretty sure they do "
     "already but double check"),
     ("Checks the filter code against the docs and finds the drift: docs/api.md says filters combine (all must match) but "
     "matchesFilters lists a ticket when any filter matches. Reports it and ties it to the request.")),
    ("B1", "constraint", "env", "S10: don't touch the outbox retry logic",
     "Records as a boundary that the outbox retry logic (src/backoff.js, src/outbox.js) is not to change."),
    ("D1", "constraint", "env", "S11: keep it zero-dependency like the rest",
     "Confirms no dependencies as a constraint (CONTRIBUTING.md, package.json)."),
    ("A1", "constraint", "env", "S12: the audit log should say who closed it",
     ("Finds that the actor comes from the X-Actor header and is recorded in the audit entry of every change, and that the "
     "transition handler already passes it, so who closed it is recorded through the existing path.")),
    ("O1", "open", "decision", "S13: closing 500 tickets in one bulk call has to work",
     ("Notes that there is no bulk endpoint and the request gives no contract for one (path, body, partial failure, "
     "limit, response), so it is an open decision with a recorded default or a person-only question.")),
    ("N1", "open", "decision", "S13: snappy, I don't care about exact numbers",
     ("Relates 'snappy' and 500 closes to the repository: each change saves the data file and enqueues an audit entry and "
     "a notification, so a bulk close may cost many writes; flags performance as a risk to check by running, or records a "
     "default bound.")),
]
GROUPS = ["skill", "slang", "unknown", "referent", "conflict", "constraint", "open"]
