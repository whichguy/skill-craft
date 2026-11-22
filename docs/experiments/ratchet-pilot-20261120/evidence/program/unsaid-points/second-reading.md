# Part D1: the second reading (a Sonnet subagent, the nine pairs under shuffled names)

## The key (not shown to the reader)

```
r1 d-limit-2 question A spec 20576 chars plan 18354 chars
r2 d-limit-1 question A spec 19120 chars plan 16909 chars
r3 d-states-3 question B spec 16858 chars plan 16217 chars
r4 d-due-1 question C spec 20302 chars plan 19265 chars
r5 d-limit-3 question A spec 18659 chars plan 17086 chars
r6 d-due-2 question C spec 19220 chars plan 19135 chars
r7 d-states-1 question B spec 17947 chars plan 15698 chars
r8 d-states-2 question B spec 17357 chars plan 17305 chars
r9 d-due-3 question C spec 19438 chars plan 16643 chars
```

## The brief

# Brief: a second reading of nine pairs of documents

You are a careful reader. You read nine pairs of documents and sort each pair into a class by fixed definitions.
Read only; write nothing; run no command except to read the files named below. Do not judge which behaviour is
better, and do not say which pairs you think belong together.

## The documents

Nine folders, `r1` to `r9`, in
`<scratch>/lens/d1-reading/`.
Each holds `spec.md`, a specification, `plan.md`, a plan written after it, and `question.txt`, one letter (A, B or
C) that says which of the three questions below applies to that pair. All were written for change requests to one
existing help-desk ticket service.

In a specification, clauses are headed `### C-<n>: ...` or `### U-<n>: ...`; each has an `Observable:` line (or a
`Flow:` line) and a `Source:` line, and may have an `Open:` line, which marks something the request does not
settle. A plan has a `## Decisions` table, among other sections.

## Question A (folders whose `question.txt` says A)

The request adds ticket assignment and says of an agent only this: "an agent is a non-empty name". It gives no
longest length for the name. **What do the two documents do about the longest name an agent may have?**

- **O+** marked open, answer named: a document marks the point as open or not settled (an `Open:` line, or a
  sentence saying it is not settled or is the requester's to decide) **and** a document names the length it takes
  for now.
- **O** marked open, nothing taken: the point is marked open or not settled, and no document names a length taken.
- **D** decided: a longest length is stated as a requirement or as a decision with no mark, in either document, that
  it is open or not settled.
- **P** passed over: neither document speaks of a longest length for an agent's name.

Limits on other things (a ticket's title, the requester, the `X-Actor` header or actor, a request body, a page
size) do not count unless the sentence applies them to the agent's or assignee's name.

## Question B (folders whose `question.txt` says B)

The request adds ticket assignment and does not say in which ticket states (open, in progress, resolved, closed) a
ticket may be assigned or unassigned. The existing service's documentation says that a closed ticket can no longer
change. **What do the two documents do about the states in which a ticket may be assigned or unassigned?**

- **I+** the existing rule applied, source named: assignment is refused for closed tickets and allowed for the
  other states, and the clause that says so names the existing product, its documentation or its code as the source
  (for example `Source: existing: ...`).
- **I** the existing rule applied, no source: the same rule, with no source naming the existing product and no mark
  that the point is open.
- **O** or **O+** marked open: a document marks as open or not settled *which states allow assignment* (O+ if a
  document also names the answer taken). An `Open:` line about something narrower (for example what a request that
  changes nothing returns on a closed ticket) does not count for this class: report it separately.
- **D** another rule decided: a rule other than the existing one is required (for example resolved tickets are
  refused too), with no mark that it is open.
- **P** passed over: nothing says which states allow assignment.

## Question C (folders whose `question.txt` says C)

The request adds due times to tickets. It says: "The tickets already in the production data file get due times
too, from their own creation time and priority, and keep them from then on. Due times are switched on in production
only once the data file holds them: until the DUE_TIMES environment variable is `on`, the service answers exactly
as it does today." It does not say **who or what puts the due times into the existing data file, and what the
service does when it is started with `DUE_TIMES=on` while the data file holds tickets without due times.**

Two answers are possible, among others: *refuse* (someone runs a separate preparation step first; the service
refuses to start, or to switch on, while a ticket lacks a due time) and *fill* (the service itself gives the
missing due times when it starts switched on, saves them, then serves).

Sort each pair by what the **specification** does, then say what the **plan** takes:

- **O+** marked open, answer named: the specification marks the point as open or not settled, and the plan names
  the answer it takes.
- **O** marked open, nothing taken: the specification marks it open; the plan names no answer.
- **D-refuse**: the specification requires the refuse answer as a requirement, with no mark that it is open.
- **D-fill**: the specification requires the fill answer as a requirement, with no mark that it is open.
- **P** passed over: neither document speaks of it.

And separately, **the answer the plan takes**: `refuse`, `fill`, `both` (the service fills at start and a separate
step also exists, and nothing refuses), `other` (say what) or `none`.

## What to send back

For each of `r1` to `r9`, in order:

1. The question letter.
2. Every sentence, in either file, that bears on the question: quoted exactly, with the file and the clause id or
   section heading it is in. If there is none, say "none found" and which words you searched for.
3. The class. For A with D or O+: the number taken. For B: the words after `Source:` of the clause that states the
   rule, and any narrower `Open:` line you set aside. For C: the class and the answer the plan takes, and, when the
   plan's `## Decisions` table names alternatives it rejected for this point, quote them.
4. One line on any doubt you had in choosing the class.

Then one closing line listing the nine classes in order (for C: class and plan answer).

## The reader's report, word for word

All nine pairs read in full (spec.md and plan.md each; question.txt letters: r1 A, r2 A, r3 B, r4 C, r5 A, r6 C, r7 B, r8 B, r9 C). Nothing written or changed.

## r1 (question A)
Sentences bearing on the longest agent name:
- spec.md, C-9 (`Open:` line): "Open: The requester decides whitespace-only validity, treatment of surrounding whitespace and control characters, and any name-specific maximum. The existing request-wide byte limit applies independently."
- plan.md, `## Decisions` table, row "C-9, C-14, C-32": "Use a cap of 200 UTF-16 code units, matching the existing title scale for human-readable text and keeping encoded names practical in URLs."
- plan.md, same row, alternative column: "An unbounded name could fit the body but exceed the HTTP request-target budget when encoded for filtering."
- plan.md, `## Decisions` intro: "The choices below resolve implementation questions for this build. Where an `Open:` line applies, the choice is provisional."
Class: **O+**, number taken: 200 (UTF-16 code units).
Doubt: none.

## r2 (question A)
- spec.md, C-3 (`Open:` line): "Open: The requester would settle the accepted name syntax and which spellings identify the same agent, including case, surrounding whitespace, whitespace-only strings, control characters, Unicode normalization and any name-specific length limit within the request-body limit."
- plan.md, `## Decisions` intro: "The choices below for `Open:` points are proposed build defaults."
- plan.md, row "C-3, C-26, C-27": "limit it to 64 UTF-16 code units, following the existing requester field's size."
- plan.md, same row, alternative column: "Using the body limit alone can admit names too long to look up comfortably in an HTTP URL or show in a table."
Class: **O+**, number taken: 64 (UTF-16 code units).
Doubt: none.

## r3 (question B)
- spec.md, C-1: "Observable: On an existing `open`, `in_progress`, or `resolved` ticket, send `PUT /tickets/:id/assignee` with `{"assignee":"Dana"}`." (Source: request)
- spec.md, C-2: "Observable: On an assigned `open`, `in_progress`, or `resolved` ticket, send `PUT /tickets/:id/assignee` with `{"assignee":null}`." (Source: request)
- spec.md, C-8 heading: "A closed ticket cannot acquire, replace, or lose an assignee"; its Observable: "The response is HTTP 409 with `error.code` equal to `conflict` and a human-readable `error.message`. This applies to `closed`. The other statuses are covered by C-1 and C-2, and an unchanged value is covered by C-3."
- plan.md, Nuances "C-1–C-3, C-8–C-14, C-23": "The existing `isActive` excludes resolved tickets. Use the final-state guard instead."
- plan.md, Decisions row C-3: "Check for a closed ticket before comparing assignees, consistent with PATCH's closed-ticket guard."
Class: **I+**. Words after `Source:` on C-8: "existing: docs/api.md and docs/decisions/0004-error-envelope.md".
Set aside (narrower `Open:`): C-3, "Open: The requester decides whether a PUT of the current value on a closed ticket succeeds as a no-op or returns the closed-ticket conflict." Also C-1's `Open:` (success status and payload), which is not about states.
Doubt: C-1 and C-2, which say which states allow assignment, are `Source: request`. Only C-8, the clause that refuses closed, names an existing source. I took C-8 as "the clause that says so".

## r4 (question C)
- spec.md, U-4 Flow: "The operator deploys with due times hidden, prepares the production `DATA_FILE` until all its tickets have durable deadlines based on their creation time and priority, then serves enabled production responses with `DUE_TIMES=on`."
- spec.md, C-17 (`Open:`): "Open: The production operator would settle how and when preparation runs, including whether it may stop ticket writes or must run while the service is serving traffic. The request fixes the outcome before activation."
- spec.md, C-20 Observable: "Attempt activation with `DUE_TIMES=on` against a production file containing a ticket without a deadline. Any successful enabled ticket response comes only after the file contains all required deadlines. After successful preparation, start with `DUE_TIMES=on` and observe enabled responses."
- spec.md, C-20 (`Open:`): "Open: The production operator would settle whether premature activation refuses startup, keeps serving with the feature hidden, or completes preparation before serving. The requester would settle enabled behavior when no `DATA_FILE` is configured. The existing off-mode in-memory service remains covered by C-16."
- spec.md, C-18 (`Open:`, in part): "For tickets created while responses are hidden, the operator would settle whether deadlines are assigned at creation or filled in during preparation."
- plan.md, Decisions row "C-20": "Reject an incomplete configured file with a file/record diagnostic and exit 2, giving the operator a clear signal to prepare."
- plan.md, row "C-17, C-18, C-25": "Use a separate command, for example `DATA_FILE=/path/to/tickets.json node scripts/prepare-due-times.js`, so `list` and `show` remain read-only."
- plan.md, Approach: "check completeness at enabled startup before listener or worker startup."
- plan.md, `## Decisions` intro: "The following choices cover the open points for this build."
Class: **O+**. Plan answer: **refuse** (a separate preparation command, and enabled startup refuses an incomplete file and exits 2).
Rejected alternatives quoted from the plan's `## Decisions` table: row C-17, C-18, C-25: "Live preparation beside the service or stamping hidden-mode tickets as they arrive." Row C-20: "Starting with the feature hidden, preparing automatically on start, or requiring persistence for enabled use."
Doubt: U-4 and C-20's Observable lean toward preparation first, but neither says what the service does on early activation. C-20's `Open:` names that point, so I kept it as open.

## r5 (question A)
- spec.md, C-6 (`Open:` line): "Open: The requester can settle how spaces, whitespace-only values, control characters and case affect name validity or identity, and whether a name-specific length bound is needed. The existing body byte limit still applies."
- plan.md, `## Decisions` intro: "The following proposals cover every `Open:` line."
- plan.md, row C-6: "Cap the normalized name at 1,024 UTF-8 bytes and apply the same name rules for nonempty query selectors."
- plan.md, same row, reason column: "Relying only on the 65,536-byte body limit could admit names too long for the HTTP request line once encoded."
- plan.md, Nuances row "C-6, C-9, C-34–C-35, U-5": "The proposed name limit keeps its percent-encoded query value within 3,072 ASCII bytes".
Class: **O+**, number taken: 1,024 (UTF-8 bytes, of the normalized name).
Doubt: none. This is the only one of the three with the cap in bytes, not UTF-16 code units.

## r6 (question C)
- spec.md, U-4 (Source: implied): "While the service gives its old API responses, the operator prepares the existing `DATA_FILE`. ... The operator confirms that the file holds due times for every ticket, then serves with `DUE_TIMES=on`."
- spec.md, C-16 Observable: "The operator has a way to prepare the production file and verify completion before enabling due-time responses. While any ticket in that file lacks a valid saved due time, the service cannot serve a due-enabled view of that file."
- spec.md, C-16 (`Open:`): "Open: The requester decides whether preparation is a separate operator action or can complete at startup before serving, and whether writes must remain available during preparation."
- plan.md, Approach: "File-backed enabled startup checks the loaded state before listening or starting the worker."
- plan.md, row "C-15–C-17, C-23, C-32": "Prepare offline with an explicit command and the existing single-writer operating model." and "Enabled startup rechecks readiness independently."
- plan.md, same row, alternative: "Startup preparation and continued writes during migration would tie activation to a mutation or need writer coordination."
- plan.md, Nuances: "Keep readiness checks before the listen call." and "Startup config and readiness errors need to occur inside the current startup error handling, which logs to stderr and exits 2."
Class: **O+**. Plan answer: **refuse** (offline command, and enabled startup refuses to listen when a ticket lacks a due time).
Rejected alternatives quoted from the plan's `## Decisions` table, row "C-15–C-17, C-23, C-32": "Startup preparation and continued writes during migration would tie activation to a mutation or need writer coordination. Treating a missing file as empty is convenient for bootstrap but can conceal a wrong production path."
Doubt: C-16's sentence "the service cannot serve a due-enabled view of that file" while a ticket lacks a due time reads close to a requirement. It fits both refuse and fill, and the same clause marks the choice open, so I took O+.

## r7 (question B)
- spec.md, C-1: "Send `PUT /tickets/T-0001/assignee` with `{"assignee":"Dana"}` for an `open`, `in_progress`, or `resolved` ticket." (Source: request)
- spec.md, C-2: "Send `PUT /tickets/T-0001/assignee` with `{"assignee":null}` for an assigned `open`, `in_progress`, or `resolved` ticket." (Source: request)
- spec.md, C-5 heading: "A closed ticket's assignment cannot be changed."; Observable: "For a `closed` ticket, a valid PUT that would set, replace, or clear its assignee returns 409 `conflict`. The other ticket states are `open`, `in_progress`, and `resolved`."
- plan.md, Nuances "C-1–C-5, C-11–C-17 and U-1/U-6": "`resolved` can reopen and is eligible for assignment. `closed` alone is final."
Class: **I+**. Words after `Source:` on C-5: "existing: docs/api.md".
Set aside (narrower `Open:`): C-5, "Open: The requester decides whether a valid PUT of the value a closed ticket already has is acknowledged as a no-op or refused as a conflict. The ticket stays unchanged either way."
Doubt: none beyond the same source split as r3 (the allow clauses are `Source: request`, the refuse clause names `docs/api.md`).

## r8 (question B)
- spec.md, C-1: "Send `PUT /tickets/T-0001/assignee` with `{"assignee":"Dana"}` for an existing `open`, `in_progress`, or `resolved` ticket." (Source: request)
- spec.md, C-2: "Send `PUT /tickets/T-0001/assignee` with `{"assignee":null}` for an assigned ticket in `open`, `in_progress`, or `resolved`." (Source: request)
- spec.md, C-12 heading: "A closed ticket refuses an actual assignment change"; Observable: "The PUT returns 409 `conflict`. The statuses eligible for an actual assignment change are `open`, `in_progress`, and `resolved`."
- plan.md, Nuances "C-7–C-14, C-18": "then compare the validated value and use `isFinal` for actual changes, as resolved tickets are eligible."
Class: **I+**. Words after `Source:` on C-12: "existing: docs/api.md".
Set aside (narrower `Open:`): C-12, "Open: The requester can settle whether a same-value PUT on a closed ticket acknowledges the no-op or returns the closed-ticket conflict. The ticket remains unchanged either way." (The plan takes equality first, so a same-value PUT on a closed ticket is acknowledged.)
Doubt: none beyond the same source split.

## r9 (question C)
- spec.md, U-4 Flow: "The operator takes the existing `DATA_FILE` through the release's preparation procedure. ... Once the deadlines are saved, the operator runs with `DUE_TIMES=on` and verifies them through the API."
- spec.md, C-15 (`Open:`): "Open: The requester would settle any required preparation command, when preparation occurs relative to starting the service, and when a ticket created during disabled operation first gets a deadline. The release must give the operator a way to tell when preparation is complete."
- spec.md, C-16 Observable: "During production rollout, a client cannot receive an enabled ticket view or overdue page while the production file still has tickets without deadlines."
- spec.md, C-16 (`Open:`): "Open: The requester would settle whether an early `on` startup refuses to serve, first completes preparation or continues serving legacy answers until preparation succeeds."
- plan.md, Approach: "Enabled startup checks completeness before it listens or starts the worker."
- plan.md, row "C-15–C-18": "Provide `DATA_FILE=… node bin/tickets.js prepare-due`" and "Enabled startup refuses a configured file containing any missing deadlines, naming the file and a ticket and pointing to preparation."
- plan.md, same row, alternative: "Lazy assignment or background migration can expose partially prepared results. Startup backfill would couple initial assignment to service restarts."
- plan.md, `## Decisions` intro: "Record the answers to the specification's open points in the build report."
Class: **O+**. Plan answer: **refuse** (separate `prepare-due` command, and enabled startup refuses).
Rejected alternatives: the quoted alternatives column above ("Lazy assignment or background migration ... Startup backfill ...").
Doubt: none. The spec marks C-16 open in so many words, and the plan's own decision is unambiguous.

Closing line (classes in order): r1 O+ (200), r2 O+ (64), r3 I+, r4 O+/refuse, r5 O+ (1,024 bytes), r6 O+/refuse, r7 I+, r8 I+, r9 O+/refuse.
