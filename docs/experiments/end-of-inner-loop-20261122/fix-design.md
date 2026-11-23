# Fix design: carry-forward's spec edits, and open items settled without evidence (2026-11-22)

Owner, 2026-11-22, answering "Fix the three defects on main?": "Yes, fix them". The defects are in
`docs/shiploop-end-of-inner-loop-journal.md` section 5. Source: main at 30d4be54f0d8b08e2951ff6f0c634da435a71236
(ShipLoop 2.6.1). This document is for the outside review before anything is built.

## Scope, and why defect 2 is not built here

- **Defect 1 (carry-forward edits spec.md, unchecked) and defect 3 (an open item settles with no evidence) are built
  here.**
- **Defect 2 (a requirement change found mid-step goes nowhere) is not.** It overlaps the owner-notes candidate on
  branch `shiploop-notes-85299a`, which belongs to another session and which the owner accepted on 2026-11-22.
  - That candidate edits the same sentences: document's duty 3, carry-forward's duty 2 and its loop rule.
  - Its deliveries showed every session taking the route defect 2 is about: send-back, then the requirement is
    rewritten at step-plan.
  - So defect 2 is handed to that session with the evidence and a suggested rule (message sent 2026-11-22). It takes
    the half that needs an owner note: its step-plan duty 10 gets a clause "unless an owner note this stage owes asks
    for a requirement change, then rewrite that requirement in place and plan the step for it".
  - The other half, a step that finds a requirement must change with no owner note, is a product-behaviour choice that
    the candidate does not take. It is put to the owner (stop and ask, or let the step plan rewrite it) and is not
    built here.

## Defect 1: carry-forward's duty writes spec.md

### Evidence

From the census (journal section 3): 282 deliveries on ShipLoop 2.4.0 and later; 175 carry-forwards done.

- carry-forward changed spec.md in 33 of 175.
- In 24 of its 27 changed-line cases, the only change was to take test IDs out of the step-marked "Met by" lines that
  implement or document wrote. That was the only change in 19 of the 33.
- Contract text changed in 5:
  - 2 small edits in exact release builds (an appended due line; a corrected file name);
  - 3 in candidate builds: `t03`, and two owner-note revisions (`g2`, `m1`).
- No requirement was added or retired.

The duty is the cause. It tells carry-forward to write "each R-<n> this item satisfied; an open gap under its R-<n>
... Test IDs live only in test code: write none here". Meanwhile the step lines name test IDs and files, which
document's duty 3 asks for ("the files and test file that now meet it").

Three parts of ShipLoop disagree:

- `STAGE_FILES["carry-forward"]` in `shiploop_knowledge_home.py` lists only architecture.md and environment.md;
- the duty lists spec.md;
- `_step_spec_refusal` never runs at carry-forward, so only the ID-retention check (`_knowledge_gate`) applies there.

Sol's max review (journal section 4) recommended removing the duty's spec write and routing a gap as an obligation or
a corrective item.

### Change: one bullet of `DUTIES["carry-forward"]` in `shiploop_prompts.py`

Today (duty 1, three lines):

```
   - KNOWLEDGE/spec.md: each R-<n> this item satisfied; an open gap under its R-<n>, an unresolved state or data change
     included (State and data assessment). Keep unaffected clauses, and never relax one to fit the code or tests.
     Test IDs live only in test code: write none here.
```

Proposed (after the owner-notes candidate lands, which adds to item 2 "unless an owner note this stage owes asks for the
requirement change: then rewrite the requirement in place, queue the work and report done"):

```
   - KNOWLEDGE/spec.md: no edit at this stage beyond the owner-note rewrite of item 2; each step's document has already
     marked what its step met. A gap under an R-<n> (a clause this item did not meet, or an unresolved state or data
     change: State and data assessment) is an open item below, or corrective work in item 2.
```

Unchanged:

- `STAGE_FILES`, which already says what the new text says;
- the step gate;
- document's and step-plan's duties, except the candidate's own changes to them;
- duty 2's rule that a changed requirement means blocked, with the candidate's owner-note exception.

Sequencing: agreed with the candidate's session on 2026-11-22. It releases first (about 21:00); this change is then
built on top of the merged main and lands after it, so neither session resolves the other's sentence in a conflict.

### No script gate on carry-forward's spec edits, and why

- A gate that refused any spec.md change at carry-forward would block the candidate's own route for a carried owner
  note. Allowing that route would need the candidate's `notes` ledger, which is not on main.
- The record also has no harmful carry-forward rewrite in an exact release build.
- So the plain rule comes first, per the owner's "Go for the simpler". The gate is offered as an option once the
  candidate lands: keyed on an applied `notes` row, it could refuse every other spec.md change at carry-forward and at
  its review.

### Acceptance

- **Hermetic.**
  - The carry-forward packet prints the new bullet and none of the three old sentences.
  - Every existing pin of that text (packet completeness, head budgets in `test/shiploop_e2e/head_table.json`) is
    updated to the new bytes, and nothing else changes.
- **Live.** Deliveries on both target drivers (Sonnet 5.5 medium and Sol 6.2 medium) on the standard cases must:
  - pass every held-out check;
  - leave spec.md unchanged at carry-forward's own knowledge commit.
  The old rates were 19 of 50 carry-forwards on Sonnet medium and 8 of 95 on Sol medium, so Sonnet medium is the
  driver most likely to show the difference.

### Change note

`changes/shiploop/carry-forward-leaves-spec.md`, bump `patch`: a duty now matches the stage table, with no new field or
gate.

## Defect 3: `_settled` closes an open item by ordering alone

### What the code does

`open_items` in `shiploop_assumptions.py` lists every open `assumptions` row (disposition `open`, with `settle`,
`reason` and `due_stage`). `_settled` drops a row once a done result of its due stage is current and was accepted
after the row's result. For a row due at carry-forward, that means the same item's carry-forward. A row the due stage
re-lists by the same ID, still open, becomes that result's own row. Nothing checks that the due stage did anything
with the row. The test `test_each_steps_document_keeps_its_open_items_until_its_items_carry_forward` pins this
behaviour: a carry-forward with `"assumptions": []` settles document's items.

The precedent is the 2026-11-15 change to the unverified-outcomes ledger (dbd2a47f3dd52fc939620e6481cc64f486630075). A
pending outcome may leave the list only through an explicit settled row (requirement, outcome, basis, evidence_refs).
Settlement keys must equal the prior pending keys minus the submitted ones, and missing, extra and duplicate rows are
refused. That change followed reproduced bypasses.

### Deciding evidence first (done: see "Defect 3 decided by the census" below)

A free census of every open row in the same 255 deliveries: what its due stage did with it (re-listed, queued,
recorded in the knowledge home, addressed in the summary, or dropped), and whether a dropped one was a real obligation.
The outputs go to `docs/experiments/end-of-inner-loop-20261122/open-items/`. The census decides between two variants:

- **Variant A: the guard,** if real obligations are dropped. The due stage's result must re-list each open row it
  owes by the same ID, in its own `assumptions`, with one of the three existing dispositions:
  - `open` with a later due stage (carried; today's behaviour);
  - `evidenced` (evidence: where it went, such as the knowledge-home file or a test);
  - `probed` (the check run and its output).
  The result is refused while an owed ID is missing, with a first line that names the missing IDs, the due stage and
  the result file (on Sol, a refusal's first line is what reaches the model). Then `_settled` settles a row only when
  the due stage's current result re-lists its ID with a closing disposition.
  - Due stages with no `assumptions` field (product-acceptance, release-check, release, operations, handoff) keep
    today's rule.
  - The pinning test is changed to the new rule.
  - Open question for the review: how carry-forward says "this open item is now work item W2". No existing disposition
    fits a queue entry. The candidates are `evidenced` with the state file as evidence, or a new `queued` disposition
    naming the work item; a new disposition is a contract change.
- **Variant B: the plain rule,** if nothing real is dropped. No guard. carry-forward's duty 2 already says every
  observation that affects later work must reach an owner, and its packet already lists the open items due at it
  (`open_items`). The finding is recorded in the journal and nothing is built.

### Acceptance (variant A)

- **Hermetic, each failing first on main.**
  - A carry-forward result that omits an owed open ID is refused, with the ID in the first line.
  - Re-listing it open with a later due stage carries it.
  - Re-listing it evidenced settles it.
  - An omitted `assumptions` field is refused while rows are owed; an empty list with no rows owed is accepted.
  - The same rules hold for an outer due stage that has an `assumptions` field (system-test-author, system-test,
    release-plan, release-verify).
- **Live.** The E2E round on both drivers. Open items occur in about 25 of 224 document results, so the route may not
  run live; the report says so if it does not.

## Review result (Sol 6.2 at max, 19:07 to 19:21, 2026-11-22; `review/sol-fix-review.md`) and what was done with it

Run: read-only, neutral export of the source, the pinning tests, this design, the spec-to-plan map and the owner-notes
candidate's prompt diff; served `gpt-6.2-sol`, effort max, no fallback, exit 0. Sol ran read-only in-memory probes of
the short carry-forward duty, duplicate IDs, silent settlement and an outer revisit, and did not run the full suites.

Adopted in the build (branch `fix/carry-forward-spec-47da85`, main-compatible, no owner-note clause yet):

- **The one-bullet patch was incomplete.** The bullet now routes a gap to its work item in duty 2 or to an open item due
  at the later outer stage, naming the R-n and what would settle it. `shiploop_primary.check_queue`'s refusal no longer
  says "or write the entry first". A sentence in `carry-forward.md` and a clause in `project-knowledge.md` say
  carry-forward does not edit spec.md. The end-of-work review hand-off gets the same line if there is one clear place
  for it.
- **"Each step's document has already marked what it met"** is dropped from the text: a step with no code or test change
  has an automatic not-applicable document (Sol, `_document_entry`).
- **No script gate** stays the decision (the plain rule first). Sol agrees: the claim the record supports is "no verified
  harmful producer rewrite", and a check that does not block the candidate's owner-note route needs its notes ledger and
  a binding from a note to a requirement ID, which it has in free text only. Offered as an option after the candidate
  lands.

Not taken, or not built here:

- **The owner-note clause in the shared duty.** The candidate's session keeps its exception in duty 2 and in the loop
  rule, and prints the owed-note rule in its own block in the one-step form as well (its reply, 2026-11-22), so this
  change adds no owner-note text. Sol had noted that duty 2 is replaced in the one-step rendering.
- **Defect 3, the open-item guard.** Sol confirms the drop is real in the code (`_settled` is called only by `open_items`;
  a later done result with an empty list hides the row) and that every reader loses it: the packet, the generated
  release-verify commit body, the handoff's lessons, the report's Open items table. It also found the minimal guard
  larger than this design had: IDs are unique only within one result, so matching needs a stable origin action and ID;
  a queued item needs its own disposition naming the item; outer revisits and review imports need their own checks;
  and old runs need an activation boundary. The census still decides. If no consequential drop is found, nothing is built
  and the ordering bypass is recorded in the journal so a later real loss can reopen it.
- **Defect 2, the no-note half.** Sol recommends `blocked` with the requirement ID, the conflict and the choices, when a
  step finds that a requirement itself must change and nobody has decided it; ordinary send-back stays for correcting a
  plan or test against the accepted requirement. The strongest case against asking is a local correction already
  dictated by the accepted request, where the amended-plan route is enough. It is the owner's decision.
- **Queueing must reach a cold planner** (an added item's context must name the revised requirement, because step-plan
  sees only the spec's outline): for the owner-note route, the candidate's session.
- **Corrected evidence for defect 2:** the saved runs show two candidate runs rewriting a requirement at step-plan
  after a send-back (`k1`, `g3`) and one at carry-forward (`g2`).

## Defect 3 decided by the census: variant B, nothing built (2026-11-22)

Census (`open-items/census.out`, `census.json.gz`, `census.py`; one Opus agent, no model, no run; the totals recounted
by the main session from the raw file). Corpus: 255 runs, 69 with an open row after the plan, 313 current open rows
(56 on exact release builds; pool by version and driver in `census.out`).

| What the due stage did with the row | Rows |
|---|---|
| Same ID, about the same item | 64 |
| Re-listed under a new ID | 12 |
| Put in the work queue | 4 |
| Recorded in documents only, the due stage silent (both about finding F-1 in one run: recorded in architecture.md and the changelog earlier, named later in summaries, lessons and handoff) | 2 |
| Addressed in the result text | 230 |
| Not due yet (the run stopped first) | 1 |
| **Dropped with nothing said** | **0** |

The guard as designed (re-list every owed item by its ID, at a stage whose result has an `assumptions` list) would have
refused 42 of 68 such results: system-test 21 of 23, release-verify 18 of 27, carry-forward 3 of 15, release-plan 0 of 3.
No refused result held a dropped item, so there is no right catch. It would also pass the one silent case, because the
due stage's own A2 is a different item. IDs are local to one result (9 rows have the same ID on a different item; 12
rows come back under new IDs), so an ID key refuses the wrong things and passes the wrong ones. 156 of the 312 settled
rows were due at stages whose result has no list to check (handoff 115, product-acceptance 36, operations 5).

Decision (the owner's "go for the simpler": a guard with no right catch on record costs wrong refusals): nothing is
built for defect 3. The ordering bypass in `_settled` is real in the code and stays on record here and in the journal;
it has cost nothing on record. A later real loss reopens it, and the cheapest instrument would then be content-based and
limited to stages that have a list. The owner can overrule.

Two findings beside the question, recorded and not acted on:

- The final report's Open items table shows no non-plan row in all 68 runs that reached handoff: the handoff's own done
  result settles handoff-due rows before the report renders. They appear in Unverified, Follow-on and Lessons.
- `unverified` is a parallel channel: one release-verify result with an empty `assumptions` list carried all seven
  owed rows there.
