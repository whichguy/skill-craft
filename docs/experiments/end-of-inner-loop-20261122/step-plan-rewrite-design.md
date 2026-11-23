# Design: a step that finds a requirement must change sends back, and step-plan rewrites it and re-plans (2026-11-22)

Owner, 2026-11-22, about 21:45, to "When a requirement must change mid-step and no note covers it, should ShipLoop stop and
ask you, or let step-plan rewrite it?": **"Let step-plan rewrite"**. Both Sol's review and the session had recommended
stopping and asking; the choice is the owner's and is not reopened here. Source read: main at
1966c4c00b6fb83d8edfd4dfd877585cc83fc916 (ShipLoop 2.7.1). Nothing is built yet.

It also serves the owner's rule of the same day: "if we do update the spec, we would definitely need to incrementally
update the plan to accommodate the spec changes". Step-plan rewrites the requirement and plans for it in one stage.

## What is there today

- **The way in exists.** `step_spec_refusal` (`shiploop_knowledge_home.py`) refuses a changed or new requirement inside a
  step and says "to change a requirement, report send-back naming it". `document`'s duty 3 says "a requirement whose intent
  moved is no edit: report send-back naming the R-<n>". `inner-loop.md`: "When a work item's goal proves wrong or
  unachievable while it is being built ... the stage reports send-back".
- **The redone step-plan is told why.** `_revisit_lines` (`shiploop_navigator.py`) prints the sending stage, its summary and
  its result file; `_upstream_line` says nothing upstream changed and "the result that sent the item back says what to
  change".
- **The way on is closed.** step-plan's duty 10: "Keep every R-<n> and AD-<n>; write nothing else in KNOWLEDGE/, unless an
  owner note this stage owes asks for a requirement change: then rewrite that requirement in place in KNOWLEDGE/spec.md (the
  ID stays; its entry keeps no copy of the old clause) and plan the step for the rewritten text."
- **Nothing in the scripts stops it.** At step-plan the only spec check is that no R-n is dropped. Five of five sessions
  that got an owner note during a build took exactly this route and rewrote the requirement at step-plan, before duty 10
  allowed it (`test/shiploop_e2e/LEARNINGS.md`, entry of 2026-11-22 on owner notes).
- **Other text routes the finding differently.** `carry-forward.md` ("Incompatible findings") and `research-loop.md` say
  blocked or pause for a changed requirement and for a changed completed-work assumption; carry-forward's own duty 2 makes
  the second a corrective item.
- **What the requester sees.** `shiploop_defaults.changed` marks a row of the "Decided for you" list whose requirement no
  longer reads as the spec stage left it, in the done packet and the report. A reworded requirement with no row there is
  shown nowhere but in the knowledge commit's diff.

## The change

1. **step-plan's duty 10** (both drivers read step-plan's packet; it is the one lever). Proposed:

   ```
   10. **Knowledge.** ... Keep every R-<n> and AD-<n>; write nothing else in KNOWLEDGE/, unless an owner note this stage
       owes, or the send-back this plan answers, asks for a requirement change: then rewrite that requirement in place in
       KNOWLEDGE/spec.md (the ID stays; its entry keeps no copy of the old clause) and plan the step for the rewritten
       text. A rewrite a send-back asks for keeps every clause the send-back does not name, relaxes none to fit code or
       tests already written, says in the entry that step-plan revised it and why, and is named in `summary`.
   ```

   "Keep unaffected clauses, and never relax one to fit the code or tests" is the sentence carry-forward's old duty held;
   here it bounds the risk the Ratchet pilot measured (outside judges accepted 10 of 59 requirements written after the
   build). It limits what a rewrite may be for, not whether there may be one.
2. **The sender says what the requirement must become.** `document`'s duty 3 and `step_spec_refusal`: "report send-back
   naming the R-<n> and what it must say" (today: naming it). The redone step-plan holds only the sender's summary.
3. **Carry the change to later items.** carry-forward's duty 2, the bullet on an affected future item: "(one that follows a
   requirement this item rewrote included)". Its step-plan sees the spec as a table of contents, so a pending item's
   `context` is where the change reaches it.
4. **One rule in the references.** `carry-forward.md` and `research-loop.md`: in a step, a requirement that must change is a
   send-back and step-plan rewrites it; at carry-forward, which cannot send back, it stays blocked unless an owed note asks
   (released rule); a changed permission or invocation contract stays blocked; a completed-work assumption that new
   evidence invalidates is corrective work (as duty 2 says).
5. **The requester sees every rewording, by script.** A function beside `changed` in `shiploop_defaults.py` (or a small
   module of its own) lists each R-n of the spec stage's knowledge commit whose entry lost a line it held then, or is
   retired or gone (the same comparison as `changed`, over all entries). The done packet prints one line: which
   requirements were reworded after the specification, to be told to the user in the last message. The report has a
   short table: ID, as specified, as delivered. None reworded: nothing printed. Display only: nothing is refused.
6. **Not changed:** `STAGE_FILES["step-plan"]` (it drives the packet's routine "this stage writes" lines, so listing spec.md
   there would invite a spec edit at every step-plan); the step gate; `_fix_forward_refusal` and `_frozen_case_refusal` (a
   requirement a done step served gets a new step with new criterion IDs); carry-forward's blocked rule; loops and limits.
   No gate on which step-plan may rewrite: on 58 released-engine deliveries step-plan rewrote none, so a gate has no right
   catch on record; it is offered as an option (a rewrite is refused at a step-plan that answers no send-back and owes no
   note).

## The deciding check (registered before any sample)

Decision it serves: ship this wording, or revise it. Instrument: `test/shiploop_e2e/stage_suite/stages.py live`, one packet,
no whole delivery. Scenario: the existing late send-back replay of a step-plan (`step-plan/replay-ticket-comments-late-send-back`
in `docs/experiments/step-boundary-replay-20261113/`), with the send-back's result replaced by one that names an R-n of that
run's spec, says what it must say instead and gives a fact found in the step as the reason, and that no note covers.

| Arm | Text | Sol 6.2 medium | Sonnet 5.5 medium |
|---|---|---|---|
| T | this design | 2 samples | 2 samples |
| C | ShipLoop 2.7.1 as released | 1 sample | 1 sample |

Script measures on the sample's final tree and result: the stage is accepted; the named R-n's entry holds the new meaning (a
token of the send-back's text) and no longer the old clause; its ID is kept; every other R-n's entry is byte-identical; the
amended plan has a criterion that states the new meaning; `summary` names the R-n; the fix-forward gate passes.

- T meets all of them in 3 or 4 of 4: ship. In 2: read the two that did not before deciding. In 0 or 1: the wording fails;
  revise once and run T again.
- C rewrites the entry in 2 of 2: the permission was not the lever; ship as the alignment the owner asked for, and say so.
- A rewrite that changes any other R-n, or relaxes a clause the send-back does not name, in any T sample: stop and read it
  before anything else.

After it, one whole delivery on each driver (the release preflight's round), which shows function only: the route needs a
send-back naming a requirement, which natural deliveries rarely hold.

## Revision 1, after Astra's review and before any sample or build (2026-11-22, 22:10)

Review: `gpt-6.2-astra` at xhigh (the owner, 2026-11-22: "change sol max review to astra extra high review"), read-only on a
neutral export, no fallback, 8 min 24 s; `review/astra-step-plan-review.md`. Verdict: revise before shipping. Checked by the
session in the code before adopting: `check_terminal`, `open_send_back`, `REPEAT["document"]`, `_frozen_case_refusal`, the
review focus items, `_outcome_shape_lines`, the step-plan `follows` refusal, the two further guides. This section replaces
"The change" and "The deciding check" above where they differ.

**The change, as it will be built:**

1. **The route out of `document` (a bug today).** `_evaluate` opens the send-back marker when the step spec gate refuses an
   `implement` or a `document` done, and `check_terminal` honours it only at `implement`: document's own refusal names an
   exit that is then refused. Honour it at both. `REPEAT["document"]` lets the loop stop blocked for a requirement that
   itself must change as well as for behaviour that cannot be observed (a send-back needs a stopped loop's receipt).
2. **The sender says it, in one place.** Under the send-back shape that every inner stage with that outcome prints
   (`_outcome_shape_lines`): when a requirement itself must change, `summary` starts with its R-<n>, what it must say instead
   and the observed fact that requires it, with the evidence cited, and spec.md is left as HEAD holds it. The redone packet
   keeps the first 544 characters of the summary, so the order matters. `document`'s duty 3 and `step_spec_refusal` point to
   the same: "naming it and what it must say".
3. **step-plan's duty 10.** The released owner-note clause stays, word for word. Then:

   ```
   Otherwise, when the send-back this plan answers says that an existing R-<n> must change, read that entry and the evidence
   in the sending result, and rewrite the clause in place the same way: keep its ID and every clause the send-back does not
   name, and never relax one to fit code or tests already written. Say in the entry what it is based on and why it was
   revised; begin `summary` with "Revised R-<n>: <what changes for the requester>, because <the fact>"; put the R-<n> in
   `follows` and change the steps still to run, their criteria and checks to the new text. When a done step's accepted case
   proves the old clause, report blocked naming both: that case stays as accepted.
   ```
4. **The review of the redone plan.** The planning review's item on a requirement "dropped or weakened compared with the
   prior accepted version" excepts, for a redone step-plan, a requirement change the send-back or an owner note asks for, which
   it checks against its evidence instead.
5. **Later items.** carry-forward's duty 2, affected future item: one that follows a requirement this item's step plan
   revised included; its `context` carries the changed behaviour and where it stands. An amendment already accepted at
   step-plan is not the incompatible finding that blocks carry-forward.
6. **One rule in the texts.** `carry-forward.md`, `research-loop.md`, `behavioral-requirements.md`, `execution-planning.md` and
   `inner-loop.md` say the same: in a step, a requirement that must change is a send-back, and step-plan revises it and
   re-plans; a changed permission or invocation contract still pauses; a completed-work assumption that new evidence
   invalidates is corrective work. The step-plan `follows` refusal tells the planner to correct an R-<n> that has no entry,
   not to add one (an AD-<n> keeps its route).
7. **The requester sees it, by the script.** Every accepted step-plan result of the run whose `summary` begins with
   `Revised R-<n>` is listed in the report, beside "Decided for you", and in the done packet with the instruction to tell the
   user. Labelled as reported by the plan. Astra's reasons against the line-by-line comparison first proposed: it flags a
   rewrap and misses an appended exception or a rewrite later reverted, and it needs a baseline bound to the spec's own
   action. Whether a planner can rewrite without saying so is measured by the check below, not guarded by a gate.
8. **Not changed:** `STAGE_FILES["step-plan"]`; no authority gate (Astra agrees: any "send-back or owed note" gate would
   allow an unrelated rewrite on exactly the visit of concern, and a text gate would refuse a reflow or a paraphrase).

**Recorded limits, not built:** a done step whose accepted case proves the old clause (blocked, with both named; no exact
release run on record had a send-back after a done step); a review import does not rerun `expectations.check_step_plan` on a
changed final result (there before); a nonterminal knowledge commit failure is retried at a later close (there before).

**The deciding check, replaced (six samples, one per cell; registered before any sample):**

| Cell | Sol 6.2 medium | Sonnet 5.5 medium |
|---|---|---|
| T: the branch's build, a send-back that says a requirement must change, with its evidence | 1 | 1 |
| P: the branch's build, the original Proof-only send-back | 1 | 1 |
| C: ShipLoop 2.7.1, the same send-back as T | 1 | 1 |

- T counts as met when: accepted; the normative clause states the new meaning; the sibling clause in the same entry and every
  other entry are byte-identical; the ID is kept, none added or retired; the entry gives a source and a reason; `summary` begins
  with `Revised R-n`; `follows` names it; a criterion owned by a step still to run states the new meaning; no product file changed.
  A valid paraphrase the reader cannot match is read by hand before it counts either way.
- P counts as met when spec.md is byte-identical and the failing proof was repaired. **A rewrite in P, or a changed or weakened
  clause the send-back did not name in T, stops the work** and is read before anything else.
- Both T and both P met: go on to the round. One T not met: one more sample on that driver; met: go on and say so; not met:
  revise the wording once and run T again on both. Both T not met: revise once. C is read for what the released text does and
  decides nothing by itself.
- It shows the receiving planner only: the builder injects the sender's result without its gates. The sender's side is covered by
  hermetic route tests (document's marker; the reviewed amendment in HEAD and in test-spec's packet; a later item's context).
