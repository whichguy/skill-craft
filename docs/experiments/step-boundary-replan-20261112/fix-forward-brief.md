# Astra brief 2: fix forward instead of send-back replay (2026-11-12)

Read-only review at max effort of checkout origin/main (3d42222e). Verify every claim against the code. This follows
your first review in this folder (`astra-review.md`); its B verdict ("defer until a retention contract exists") is the
starting point.

## The owner's direction (verbatim)

"I want to avoid send back about redoing steps, I feel like this might be an excessive scenario , check on this. My idea
is that at the end of an inner loop , even if there are things to change, we should add or augment existing or new steps
in the step-plan not revisit old steps. This is a fix forward motion"

## What the data says (this folder: `fixforward.py` → `fixforward.out`, `fixforward_detail.py` → `fixforward_detail.out`;
ordered by state history, as you advised)

- 81 inner send-backs followed by an accepted step plan. 73 came before any step of the plan was documented; 8 after.
- Of all 81, the redone plan changed a done step's row (task, criteria, proof, paths) once. In 48, only the failing or a
  later step's row changed. In 32, no step row changed: only item-wide fields (test commands, expectations, criteria).
- The 8 late ones: in 6, nothing a done step owns changed (its row, the criteria it lists, any test command for those
  criteria). In p0-terra, one command for a done step's criterion C3 changed suite `focused` → `check` (a record fix, no
  code). In gym, the plan merged S1 into S2 (the runtime-defect case).
- Today a send-back drops the item's results from the step plan on (`shiploop_planning_revision.current_actions`,
  `step_actions`), so every done step's implement, test and document run again under the redone plan.

## The draft rule (mine; critique it)

Done steps are fixed. A change found at or after step k goes forward:

1. **Amend, don't replan.** Where a stage reports send-back today (test-spec through document), it reports an amendment
   to the step plan instead: the failing step's row may change (augment), later pending steps may change, be removed or
   be added, and item-wide fields may change, but every documented step's row, its criteria and the test commands that
   confirm only those criteria stay byte-identical. A step-plan packet in amend mode shows the done steps as fixed.
2. **A defect in a done step is a new step.** Never reopen it. Add a corrective step (next ID, e.g. S5) that changes the
   code and owns new test IDs for it. This mirrors carry-forward's item-level rule (carry-forward.md: a defect in the
   completed item becomes a corrective item; do not rewrite past completion evidence).
3. **IDs only grow.** Step and test IDs continue after an amendment (no renumbering; today "after a send-back the redone
   plan counts steps afresh"). A done step's test case may not change its oracle under the same ID; a changed oracle is a
   new ID in the step that changes the behaviour.
4. **Only what changed reruns.** After an amendment: test-spec writes cases for new or changed IDs only; validate-existing
   runs new expectations on the current HEAD (the last done step's commit); the failing step resumes with its
   uncommitted edits; done steps keep their commits, receipts, reviews and test counts.
5. **Closure still runs.** If an amendment removes the last pending steps, the item's last-step obligations (full
   regression and any check due at the last step) run as a script check before carry-forward.
6. **Not fixable forward.** A changed requirement intent, permission or invocation contract is not an amendment
   (carry-forward.md "Incompatible findings"): blocked, or pause for direction, as today.
7. **The boundary question (your modified A).** At each step's document, when later steps remain, it may propose an
   amendment by the same rule, so a learning reshapes the steps still to come without touching done ones.

## What I want from you

1. Is fix-forward sound for ShipLoop? Where does it lose quality against today's replay (your six hazards: same-ID oracle
   changes, case_step moving a criterion, three cursor readers, last-step regression on a retained plan, replayed commits
   absorbing later steps' uncommitted work, provenance/recovery)? Which of them do rules 1-5 close, and which remain?
2. The gym case (S1 merged into S2): what would fix-forward do, and is that worse?
3. The smallest correct implementation: which symbols change (current_actions/step_actions, implement_progress,
   test_loop.step_number, loops.current_step, case_step/new_cases, the step-plan packet, the send-back route in
   stage_spec), and what can stay. One projection or several?
4. Negative controls and tests it needs before it ships, and the cheapest live check.
5. Anything in the data above you find wrong.

Return a verdict, the design changes you would make to my rules, risks with symbol citations, and a build order.
