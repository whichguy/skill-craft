#!/usr/bin/env python3
"""Generate conditions.json from the frozen requirements text only (no repo/run_dir access)."""
import json, re, sys

BASE = "/Users/dadleet/src/skill-craft/docs/experiments/prompt-template-review-20261031/conditions"
req = json.load(open(f"{BASE}/bf-ds-ticket-assignment.requirements.json"))["requirements"]

rows = []


def c(id_, r, quote, observable, kind, cand=True, why=None):
    row = {
        "id": id_,
        "requirement": r,
        "quote": quote,
        "observable": observable,
        "kind": kind,
        "candidate": bool(cand),
    }
    if not cand:
        row["exclude_reason"] = why
    rows.append(row)


CAND = ("behaviour", "error", "boundary", "format")

# ---------------- R-1 ----------------
c("R-1.1", "R-1", "a newly created ticket answers 201 with `assignee: null`",
  "POST /tickets with a valid body answers 201 and the body has key assignee equal to null.", "behaviour")
c("R-1.2", "R-1", "in `GET /tickets/:id`",
  "GET /tickets/:id of a new ticket returns a body with assignee === null (key present).", "behaviour")
c("R-1.3", "R-1", "in the item from `GET /tickets`",
  "Items in GET /tickets (page items) each carry assignee (null when unassigned).", "behaviour")
c("R-1.4", "R-1", "in the ticket returned by `PATCH /tickets/:id`",
  "PATCH /tickets/:id (e.g. a title change) answers a ticket body carrying assignee (null when unassigned, the name when assigned).", "behaviour")
c("R-1.5", "R-1", "`POST /tickets/:id/transition`",
  "POST /tickets/:id/transition answers a ticket body carrying assignee (null when unassigned, the name when assigned).", "behaviour")
c("R-1.6", "R-1", "and the data file",
  "With DATA_FILE set, the JSON file written after a create contains an assignee key (null) on each ticket record.", "format")
c("R-1.7", "R-1", "after an assignment the same read surfaces return the agent name",
  "After PUT assignee dana, GET /tickets/:id returns assignee 'dana'.", "behaviour")
c("R-1.8", "R-1", "after an assignment the same read surfaces return the agent name",
  "After PUT assignee dana, the matching item of GET /tickets returns assignee 'dana'.", "behaviour")
c("R-1.9", "R-1", "after an unassignment they return `null`",
  "After assign then PUT assignee null, GET /tickets/:id returns assignee null.", "behaviour")
c("R-1.10", "R-1", "a restarted service returns the same assignee",
  "With DATA_FILE, assign dana, stop the service, start again on the same file: GET /tickets/:id returns assignee 'dana'.", "boundary")
c("R-1.11", "R-1", "a version-1 data file whose tickets have no `assignee` loads those tickets with `assignee: null`",
  "A legacy data file (tickets without assignee) loads and GET /tickets/:id answers assignee null.", "boundary")
c("R-1.12", "R-1", "is refused at load with a message naming the record",
  "A data file where a ticket has assignee 42 (non-string non-null) makes the service/store fail to load, with a message that names the offending record (ticket id).", "error")
c("R-1.13", "R-1", "not `null` and not a valid agent name (non-string, empty, over 64 characters or with a control character)",
  "A data file with assignee '' (empty string) is refused at load.", "error")
c("R-1.14", "R-1", "over 64 characters",
  "A data file with a 65-character assignee is refused at load.", "error")
c("R-1.15", "R-1", "or with a control character",
  "A data file with assignee containing a control character (tab / newline) is refused at load.", "error")
c("R-1.16", "R-1", "the existing ticket fields, their order of meaning and all existing responses; the new field is additive",
  "Existing ticket fields and responses are unchanged.", "preserved", False,
  "Preserved behaviour: no new observable to vary; covered by R-11 (existing suite).")
c("R-1.17", "R-1", "a data file whose ticket has an `assignee` that is not `null` and not a valid agent name",
  "A data file with a valid assignee name or null loads successfully (the validation does not over-reject; 64-char name loads).", "boundary", False, "Duplicate of R-1.10 (round trip with a valid name) and R-1.14 (64/65 boundary).")

# ---------------- R-2 ----------------
c("R-2.1", "R-2", "assigns the ticket to that agent and answers\n200 with the changed ticket".replace("\n", " "),
  "PUT /tickets/:id/assignee {\"assignee\":\"dana\"} on an open ticket answers 200 with the ticket body having assignee 'dana'.", "behaviour")
c("R-2.2", "R-2", "`GET /tickets/:id` agrees",
  "After the PUT, GET /tickets/:id returns assignee 'dana' (the store, not just the response, changed).", "behaviour")
c("R-2.3", "R-2", "the ticket's `updated` moves to the change time",
  "With a manual clock, PUT assignee at a later time sets updated to that time (differs from the earlier value).", "behaviour")
c("R-2.4", "R-2", "its title, priority, requester and status keep their earlier values",
  "After PUT assignee, the ticket body title, priority, requester and status equal their values before.", "behaviour")
c("R-2.5", "R-2", "The agent name is taken as given after trimming",
  "PUT {\"assignee\":\"  dana  \"} answers assignee 'dana' (trimmed) and GET agrees.", "boundary")
c("R-2.6", "R-2", "an unknown ticket id answers 404 `not_found`",
  "PUT /tickets/<unknown>/assignee answers 404 with error code not_found.", "error")
c("R-2.7", "R-2", "a body that is not a JSON object",
  "PUT with body [] / \"dana\" / 42 / null answers 400 invalid.", "error")
c("R-2.8", "R-2", "a missing `assignee` field",
  "PUT with body {} answers 400 invalid.", "error")
c("R-2.9", "R-2", "a non-string non-null value",
  "PUT {\"assignee\":42} and {\"assignee\":true} answer 400 invalid.", "error")
c("R-2.10", "R-2", "an unknown field answers 400 `invalid`",
  "PUT {\"assignee\":\"dana\",\"extra\":1} answers 400 invalid.", "error")
c("R-2.11", "R-2", "a 64-character name is accepted, a 1-character name is accepted",
  "Duplicate of R-4.1 / R-4.2.", "boundary", False, "Duplicate of R-4.1 and R-4.2 (same acceptance); counted once there.")
c("R-2.12", "R-2", "`updated` moves to the time of the change as for any other change",
  "Duplicate of R-2.3.", "behaviour", False, "Duplicate of R-2.3.")
c("R-2.13", "R-2", "the existing route, error envelope and \"one store method per handler\" convention",
  "The error envelope shape {error:{code,message}} of the new endpoint matches existing endpoints.", "preserved", False,
  "Preserved convention / structural (one store method per handler is not observable from outside).")

# ---------------- R-3 ----------------
c("R-3.1", "R-3", "removes the assignee and answers 200 with the ticket whose",
  "PUT {\"assignee\":null} on an assigned ticket answers 200 with body.assignee === null.", "behaviour")
c("R-3.2", "R-3", "the ticket reads back\n  with `assignee: null`".replace("\n  ", " "),
  "After the unassigning PUT, GET /tickets/:id shows assignee null.", "behaviour")
c("R-3.3", "R-3", "unassigning a ticket that is already unassigned is accepted",
  "PUT {\"assignee\":null} on a never-assigned open ticket answers 200 (not 400/409).", "boundary")
c("R-3.4", "R-3", "unassigning a ticket that is already unassigned is accepted and changes nothing",
  "Duplicate of R-6 (no trace).", "boundary", False, "Duplicate of R-6.3-R-6.6 (no-op leaves no trace); counted once there.")

# ---------------- R-4 ----------------
c("R-4.1", "R-4", "the strings `a` and a 64-character name are accepted as assignees",
  "PUT assignee 'a' answers 200 with assignee 'a'.", "boundary")
c("R-4.2", "R-4", "the strings `a` and a 64-character name are accepted as assignees",
  "PUT assignee of exactly 64 characters answers 200 with that name.", "boundary")
c("R-4.3", "R-4", "`\"\"`, whitespace-only text, a string over 64 characters",
  "PUT {\"assignee\":\"\"} answers 400 invalid.", "error")
c("R-4.4", "R-4", "whitespace-only text",
  "PUT {\"assignee\":\"   \"} answers 400 invalid.", "error")
c("R-4.5", "R-4", "a string over 64 characters",
  "PUT assignee of 65 characters answers 400 invalid.", "error")
c("R-4.6", "R-4", "tab, line breaks, other C0 controls and DEL",
  "PUT assignee 'one\\ttwo' (tab inside) answers 400 invalid.", "error")
c("R-4.7", "R-4", "tab, line breaks, other C0 controls and DEL",
  "PUT assignee 'one\\ntwo' (newline inside) answers 400 invalid; also '\\r'.", "error")
c("R-4.8", "R-4", "tab, line breaks, other C0 controls and DEL",
  "PUT assignee with another C0 control (e.g. \\u0001 or \\u001f) inside answers 400 invalid.", "error")
c("R-4.9", "R-4", "tab, line breaks, other C0 controls and DEL",
  "PUT assignee with DEL (\\u007f) inside answers 400 invalid.", "error")
c("R-4.10", "R-4", "a number or boolean are\nrefused with 400 `invalid`".replace("\n", " "),
  "PUT {\"assignee\":42} answers 400 invalid.", "error")
c("R-4.11", "R-4", "a number or boolean are\nrefused with 400 `invalid`".replace("\n", " "),
  "PUT {\"assignee\":true} (and false) answers 400 invalid.", "error")
c("R-4.12", "R-4", "and the message names `assignee`",
  "The 400 error message for an invalid assignee value contains the word 'assignee'.", "error")
c("R-4.13", "R-4", "`null` means \"no assignee\" and is valid only as the value of\n`assignee`".replace("\n", " "),
  "Duplicate of R-3.1 / R-3.3.", "boundary", False, "Duplicate of R-3.1 and R-3.3.")
c("R-4.14", "R-4", "the existing text-field rules used for `title`, `requester` and `X-Actor`",
  "Existing title / requester / X-Actor validation unchanged.", "preserved", False,
  "Preserved behaviour; no new observable.")

# ---------------- R-5 ----------------
c("R-5.1", "R-5", "A ticket whose status is `open` or `in_progress` accepts assignment",
  "PUT assignee on an open ticket answers 200.", "behaviour")
c("R-5.2", "R-5", "A ticket whose status is `open` or `in_progress` accepts assignment",
  "PUT assignee on an in_progress ticket answers 200.", "behaviour")
c("R-5.3", "R-5", "accepts assignment and unassignment",
  "PUT {\"assignee\":null} on an assigned in_progress ticket answers 200 and unassigns; likewise on open.", "behaviour")
c("R-5.4", "R-5", "A `resolved` or `closed`\nticket answers 409 `conflict`".replace("\n", " "),
  "PUT assignee on a resolved ticket answers 409 conflict.", "error")
c("R-5.5", "R-5", "A `resolved` or `closed`\nticket answers 409 `conflict`".replace("\n", " "),
  "PUT assignee on a closed ticket answers 409 conflict.", "error")
c("R-5.6", "R-5", "and is unchanged: no assignee change",
  "After the refused PUT on a resolved/closed ticket (which was assigned), GET shows the earlier assignee.", "behaviour")
c("R-5.7", "R-5", "no audit entry",
  "After the refused PUT, GET /tickets/:id/audit has the same entries as before.", "behaviour")
c("R-5.8", "R-5", "no notification",
  "After the refused PUT, GET /admin/outbox has the same events as before.", "behaviour")
c("R-5.9", "R-5", "the same refusal applies to `{\"assignee\": null}` on a non-active ticket",
  "PUT {\"assignee\":null} on a resolved/closed ticket answers 409 conflict and the ticket keeps its assignee.", "error")
c("R-5.10", "R-5", "keep their\n  assignee".replace("\n  ", " "),
  "Duplicate of R-5.6.", "behaviour", False, "Duplicate of R-5.6.")

# ---------------- R-6 ----------------
c("R-6.1", "R-6", "Assigning the agent a ticket already has",
  "PUT assignee dana on a ticket already assigned to dana answers 200 with the ticket body (assignee dana).", "behaviour")
c("R-6.2", "R-6", "no audit entry",
  "A same-agent PUT leaves GET /tickets/:id/audit unchanged (no new entry).", "behaviour")
c("R-6.3", "R-6", "no notification",
  "A same-agent PUT leaves GET /admin/outbox unchanged (no new event).", "behaviour")
c("R-6.4", "R-6", "`updated` keeps its earlier value",
  "A same-agent PUT with an advanced clock leaves updated at its earlier value.", "behaviour")
c("R-6.5", "R-6", "or unassigning an already unassigned ticket, answers 200 with the unchanged\nticket".replace("\n", " "),
  "PUT {\"assignee\":null} on an unassigned ticket answers 200 and leaves audit and outbox unchanged.", "behaviour")
c("R-6.6", "R-6", "or unassigning an already unassigned ticket",
  "PUT {\"assignee\":null} on an unassigned ticket with an advanced clock leaves updated unchanged.", "behaviour")
c("R-6.7", "R-6", "Assigning the agent a ticket already has",
  "Combined with R-2's trimming: PUT {\"assignee\":\" dana \"} on a ticket already assigned to dana is a no-op (no audit entry, no event, updated unchanged).", "boundary")
c("R-6.8", "R-6", "assigning an agent other than the one the ticket already has *is* a change: one\n  audit entry".replace("\n  ", " "),
  "Duplicate of R-7.1 / R-7.2.", "behaviour", False, "Duplicate of R-7.1 (one audit entry) and R-7.3.")
c("R-6.9", "R-6", "one notification, a new `updated`",
  "Duplicate of R-8.1 / R-2.3.", "behaviour", False, "Duplicate of R-8.1 and R-2.3.")
c("R-6.10", "R-6", "the existing no-op rule for `PATCH`",
  "PATCH no-op behaviour unchanged.", "preserved", False, "Preserved behaviour; no new observable.")

# ---------------- R-7 ----------------
c("R-7.1", "R-7", "appends one audit entry with action `ticket.assigned`",
  "After a real assignment, GET /tickets/:id/audit contains an entry whose action is 'ticket.assigned'.", "behaviour")
c("R-7.2", "R-7", "appends one audit entry",
  "Exactly one new audit entry per assignment change (not zero, not two).", "boundary")
c("R-7.3", "R-7", "`changes.assignee` holding\n`{from, to}` (the old and the new name, `null` where unset)".replace("\n", " "),
  "Assigning dana to an unassigned ticket: entry.changes.assignee deep-equals {from:null,to:'dana'}.", "format")
c("R-7.4", "R-7", "unassigning records `{assignee: {from: \"dana\", to: null}}`",
  "Unassigning dana records entry with action ticket.assigned and changes.assignee {from:'dana', to:null}.", "format")
c("R-7.5", "R-7", "(the old and the new name, `null` where unset)",
  "Reassigning dana to erin records changes.assignee {from:'dana', to:'erin'}.", "format")
c("R-7.6", "R-7", "the actor from `X-Actor`",
  "PUT with header X-Actor: alice records entry.actor === 'alice'.", "behaviour")
c("R-7.7", "R-7", "(or `system`)",
  "PUT without X-Actor records entry.actor === 'system'.", "behaviour")
c("R-7.8", "R-7", "the time of\nthe change".replace("\n", " "),
  "With a manual clock, the audit entry's timestamp equals the clock time of the PUT.", "behaviour")
c("R-7.9", "R-7", "returns it among the ticket's entries, oldest first",
  "After create, assign, reassign: GET /tickets/:id/audit lists entries oldest first, with the assignment entries in order.", "behaviour")
c("R-7.10", "R-7", "the audit entry shape and the actor rule",
  "Existing audit entry shape / actor rule unchanged.", "preserved", False, "Preserved behaviour; no new observable.")

# ---------------- R-8 ----------------
c("R-8.1", "R-8", "enqueues an outbox event of type\n`ticket.assigned`".replace("\n", " "),
  "After assigning dana, GET /admin/outbox lists one pending event of type 'ticket.assigned'.", "behaviour")
c("R-8.2", "R-8", "addressed to that agent name",
  "That outbox event's recipient (to) is 'dana'.", "behaviour")
c("R-8.3", "R-8", "carrying the ticket id and its title",
  "That outbox event carries the ticket id and the ticket title (payload ticket, data.title).", "behaviour")
c("R-8.4", "R-8", "The event's dedupe key distinguishes the agent, so a notice still pending for\nthe previous agent does not swallow the new one".replace("\n", " "),
  "Assign A (pending), then reassign to B: the outbox lists a pending event to B as well as A's.", "behaviour")
c("R-8.5", "R-8", "The one reassignment that adds no event is a return to an agent whose\nnotice is still pending (A→B→A)".replace("\n", " "),
  "Assign A, B, A (A's first notice still pending): the outbox holds exactly two ticket.assigned events (A and B), none added for the return to A.", "boundary")
c("R-8.6", "R-8", "the audit\nentry of R-7 still records the change".replace("\n", " "),
  "In A→B→A, the final reassignment to A still appends an audit entry {from:'B', to:'A'}.", "boundary")
c("R-8.7", "R-8", "with `NOTIFY_FILE`, the delivered line names `type: \"ticket.assigned\"`, `to` equal to the agent and the ticket id",
  "With the worker running and NOTIFY_FILE set, the delivered line names type ticket.assigned, to=dana and the ticket id.", "format")
c("R-8.8", "R-8", "with the worker running it is delivered once to `NOTIFY_FILE`",
  "Exactly one line is written to NOTIFY_FILE per assignment notice (not zero, not two).", "boundary")
c("R-8.9", "R-8", "Unassigning and re-assigning the same agent enqueue nothing",
  "Unassigning enqueues no event.", "behaviour")
c("R-8.10", "R-8", "Unassigning and re-assigning the same agent enqueue nothing",
  "Re-assigning the same agent (no-op) enqueues no new event.", "behaviour")
c("R-8.11", "R-8", "Reassigning from agent A to agent B while A's notice is still pending enqueues B's notice as\nwell".replace("\n", " "),
  "Duplicate of R-8.4.", "behaviour", False, "Duplicate of R-8.4.")
c("R-8.12", "R-8", "the template renders a subject and body naming the ticket",
  "The event is rendered to a deliverable message (not marked dead) whose subject names the ticket.", "format")
c("R-8.13", "R-8", "the template renders a subject and body naming the ticket",
  "The event is rendered to a deliverable message whose body names the ticket.", "format")
c("R-8.14", "R-8", "A failed\ndelivery is retried and eventually marked dead by the existing worker rules".replace("\n", " "),
  "A notifier failure for a ticket.assigned event retries and eventually marks the event dead.", "behaviour")
c("R-8.15", "R-8", "Unassigning and re-assigning the same agent enqueue nothing",
  "Re-assigning to an agent whose earlier notice has already been delivered (not pending) enqueues a fresh notice (the dedupe suppresses only pending notices).", "boundary")
c("R-8.16", "R-8", "Delivery of that\nnotice to a person needs a relay that tails the file and an address for the agent".replace("\n", " "),
  "Delivery to a person is unobserved (open gap).", "behaviour", False,
  "Explicitly unobservable open gap in the spec: no relay or address exists in the repository.")

# ---------------- R-9 ----------------
c("R-9.1", "R-9", "`GET /tickets?assignee=<agent>` keeps the tickets assigned to that agent",
  "With tickets assigned to dana, erin and nobody, ?assignee=dana lists only dana's tickets.", "behaviour")
c("R-9.2", "R-9", "`assignee=` (empty value) keeps the\nunassigned tickets".replace("\n", " "),
  "?assignee= lists only the unassigned tickets.", "behaviour")
c("R-9.3", "R-9", "a valid agent with no tickets lists nothing rather than falling\n  back to the unfiltered page".replace("\n  ", " "),
  "?assignee=zed (nobody has zed) returns an empty items list, not the full page.", "boundary")
c("R-9.4", "R-9", "?status=open&priority=urgent` lists only tickets that are both open and urgent",
  "Tickets: open+urgent, open+low, closed+urgent: ?status=open&priority=urgent returns only the open+urgent ticket.", "behaviour")
c("R-9.5", "R-9", "`?assignee=dana&status=open` combines the same way",
  "?assignee=dana&status=open lists only dana's open tickets.", "behaviour")
c("R-9.6", "R-9", "`status`, `priority` and `assignee`\ncombine".replace("\n", " "),
  "?status=open&priority=urgent&assignee=dana lists only tickets matching all three.", "behaviour")
c("R-9.7", "R-9", "The filter works with `limit` and `cursor`",
  "A filtered listing with limit=1 pages through next cursors, returning every matching ticket exactly once and no non-matching ticket.", "boundary", False, "Duplicate of R-9.8.")
c("R-9.8", "R-9", "a filtered listing pages through its cursors without duplicates or gaps",
  "?assignee=dana&limit=2 across the cursor chain returns each of dana's tickets exactly once, with no gap or duplicate.", "boundary")
c("R-9.9", "R-9", "whitespace-only",
  "?assignee=%20%20 answers 400 invalid.", "error")
c("R-9.10", "R-9", "longer than 64\n  characters".replace("\n  ", " "),
  "?assignee=<65 chars> answers 400 invalid.", "error")
c("R-9.11", "R-9", "contains a control character answers 400 `invalid`",
  "?assignee=a%09b (tab) answers 400 invalid.", "error")
c("R-9.12", "R-9", "A non-empty filter value must be a valid agent name; an invalid\none answers 400 `invalid`".replace("\n", " "),
  "A 64-character assignee filter value is accepted (200), the boundary of validity.", "boundary")
c("R-9.13", "R-9", "the cursor-page response, the existing `status`\nand `priority` filters, the limit rules and the ignoring of unknown parameters".replace("\n", " "),
  "Existing list contract unchanged.", "preserved", False, "Preserved behaviour; covered by the existing suite.")
c("R-9.14", "R-9", "the combination rule is corrected from the current OR implementation to the documented AND",
  "?status=open&priority=urgent is AND (duplicate of R-9.4).", "behaviour", False, "Duplicate of R-9.4.")

# ---------------- R-10 ----------------
c("R-10.1", "R-10", "`node bin/tickets.js list` prints an `ASSIGNEE` column showing the agent name",
  "The list table header has an ASSIGNEE column and an assigned ticket row shows its agent.", "format")
c("R-10.2", "R-10", "or `-` for an unassigned ticket",
  "The table row for an unassigned ticket shows '-' in the ASSIGNEE column.", "format")
c("R-10.3", "R-10", "`list --raw` appends `assignee` as the fifth column: the agent name",
  "list --raw prints the agent name as the fifth column for an assigned ticket.", "format")
c("R-10.4", "R-10", "or an empty cell for an unassigned ticket",
  "list --raw prints an empty fifth cell for an unassigned ticket.", "format")
c("R-10.5", "R-10", "Columns 1–4 keep their positions",
  "list --raw columns 1-4 are id, status, priority, title in that order.", "format")
c("R-10.6", "R-10", "so the weekly report keeps working",
  "scripts/weekly-report.js with a data file containing assigned tickets still counts by status and priority correctly.", "behaviour")
c("R-10.7", "R-10", "`show` lists `assignee` among the ticket's\nfields".replace("\n", " "),
  "node bin/tickets.js show <id> output lists an assignee field with the agent (or empty marker).", "format")
c("R-10.8", "R-10", "the positional `list --raw` contract ... and the exit codes",
  "Existing CLI exit codes unchanged.", "preserved", False, "Preserved behaviour; covered by the existing suite.")

# ---------------- R-11 ----------------
c("R-11.1", "R-11", "`npm test` runs the existing suite and the new test files together and every test\n  passes (`fail 0`)".replace("\n  ", " "),
  "npm test exits 0 with fail 0.", "tests-themselves", False, "About the test suite itself.")
c("R-11.2", "R-11", "the existing test files under `test/` are unchanged by this work",
  "git diff of baseline test files empty.", "tests-themselves", False, "About the test suite itself.")
c("R-11.3", "R-11", "the `npm test` summary reports `tests` at\n  least 117 and equal to `pass`".replace("\n  ", " "),
  "npm test summary: tests >= 117, equal to pass, fail 0, skipped 0, todo 0.", "tests-themselves", False, "About the test suite itself.")
c("R-11.4", "R-11", "every existing endpoint, error, audit, notification, persistence and CLI\nbehaviour".replace("\n", " "),
  "Existing behaviour preserved.", "preserved", False, "Preserved behaviour; covered by the existing suite.")

# ---------------- R-12 ----------------
c("R-12.1", "R-12", "`docs/api.md` documents `assignee` in the ticket, the new endpoint with its refusals, and\n  the `assignee` filter".replace("\n  ", " "),
  "docs/api.md text.", "structural", False, "Documentation inspection only; not observable behaviour.")
c("R-12.2", "R-12", "`docs/decisions/0009-*.md` records the assignment decision",
  "decision record exists and is listed.", "structural", False, "Documentation inspection only; not observable behaviour.")
c("R-12.3", "R-12", "no package is added to `package.json` and no `node_modules` is required",
  "package.json diff.", "structural", False, "Structural repository obligation, not product behaviour.")
c("R-12.4", "R-12", "`README.md` states the new raw column; `CHANGELOG.md` gains a section and `package.json` its\n  matching version".replace("\n  ", " "),
  "README/CHANGELOG/package.json text.", "structural", False, "Documentation inspection only; not observable behaviour.")

# ---------------- verify quotes against the frozen text (whitespace-normalised) ----------------
def norm(s):
    return re.sub(r"\s+", " ", s)

norm_req = {k: norm(v) for k, v in req.items()}
bad = []
for r in rows:
    q = norm(r["quote"])
    # allow explicit elisions with " ... " by checking each part
    parts = [p.strip() for p in q.split(" ... ")]
    for p in parts:
        if p not in norm_req[r["requirement"]]:
            bad.append((r["id"], p))
if bad:
    for b in bad:
        print("QUOTE NOT FOUND", b)
    sys.exit(1)

for r in rows:
    r["quote"] = norm(r["quote"])
    if r["kind"] in CAND and not r["candidate"] and not r.get("exclude_reason"):
        print("missing reason", r["id"])
        sys.exit(1)

json.dump(rows, open(f"{BASE}/bf-ds-ticket-assignment/conditions.json", "w"), indent=1, ensure_ascii=False)
cands = [r for r in rows if r["candidate"]]
print("rows", len(rows), "candidates", len(cands))
