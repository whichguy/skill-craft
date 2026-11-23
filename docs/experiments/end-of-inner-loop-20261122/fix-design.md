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

### Deciding evidence first (running now)

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
