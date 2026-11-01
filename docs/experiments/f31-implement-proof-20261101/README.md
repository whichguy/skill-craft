# F31 live check: implement's exit condition names the Proof (registered 2026-11-01, before any run)

Owner, 2026-11-01, answering "Take up F31 with a pre-registered live check?": "Yes, take it up".

Decision record, before any run: at 13:48 another session recorded the owner's "Yes, leave it" for F31
(a032bb167552bc867ae22a21f31847cdbd514554). Asked "Which of your two F31 answers should stand?", the owner answered "Run the live
check". That session's evidence is in docs/experiments/implement-send-back-class-20261101/. In 20 runs of shared-expenses, the Confirm-by
reading caused 1 of 6 implement loops, each loop cost about 2 minutes, and every loop recovered. The design below is unchanged.

## What F31 is

Planning journal F31 (entry E20; docs/shiploop-step-plan-review-2026-11-01.md §7a and §8, item 4). Implement reads a
criterion's Confirm-by test as due at implement, although the test stage writes that test after implement, and it sends
good plans back. There are three live cases:
- FX F ticket-import s1 (2026-10-31): "C1 and C2 require a new test file which the implementation contract forbids
  writing until test stage". Its Proof was `npm test`. Rule C (skill-craft 2.27.4) now refuses that plan at step-plan.
- XI B ticket-import s4 (2026-10-31): "C2 requires focused test execution during implement, but implement forbids
  writing those tests and test is a later stage". Its self-contained Proof and the 117 existing tests had passed.
- SP1 xhigh csv-report s1 (2026-11-01, ShipLoop 1.27.0), the second send-back: "C1-C3 still require confirmation by
  unittest cases TC_1-TC_3 ... A passing scratch proof is not the literal specified confirmation". Its real Proof had
  passed.

The cause, read from the source:
- Implement's first exit condition (`shiploop_stage_spec.STEP_CRITERIA_CONDITION`) asks that each criterion be "shown by
  a command or file after the last edit". The criterion's own text names its Confirm-by tests, and implement's duty says
  "Write no tests".
- The planning guide said implement "loops until each is confirmed" (references/backchain-planning.md). That sentence is
  from f7d29e31 (2026-09-24), before each step got its own Proof (12151c49, 2026-10-17).

## The change (arm B)

- `STEP_CRITERIA_CONDITION` now reads: "... shown after the last edit by the step's Proof or another command or file
  (tests named in a criterion's Confirm by are written and run at the test stage), ...". It is the first exit condition
  of every implement Until Loop, on both routes. It adds 106 characters to implement's head and whole text (inline head
  17,041 and ask-agent head 17,219 at the reference install; the cut is 20,000).
- references/backchain-planning.md: implement loops until the step's Proof confirms each criterion, and the test stage
  writes and runs the tests a `Confirm by:` names.
- A route test in test/shiploop-test-loop.test.py,
  `test_implement_done_rests_on_the_proof_while_the_criterions_confirm_by_test_is_unwritten`. The step's contract carries
  the condition, and `complete` accepts implement's done on its Proof with the Confirm-by test absent. It fails on the old
  wording.
- Change note changes/shiploop/implement-proof-shows-criteria.md (patch), and the two head tables (implement only).

Arm A is this registration commit. Arm B is the candidate commit on branch `exp/f31-implement-proof-bda511` whose parent
is this commit. Its patch-id (`git patch-id --stable`) is f867fa0a9e5129c91e680f3767be2cac80d5d7ed, so a rebase keeps it identifiable.

## Design

Subject: Codex `gpt-6.1-terra` at xhigh (the owner's runner), all tools, `--permission-mode auto`, with ShipLoop built
from each arm's checkout. `launch.sh` in this folder runs everything, at most 5 at once, into
`~/e2e-runs-f31/20261101/<arm>-<case>-s<n>`.

- **Part 1, mechanism: 16 slices.** `test/shiploop_e2e/slice.py --seed-at test-spec --stop-after implement` on
  tickets-assign and stand-in-rules, 4 per arm per case, in the order A B B A A B B A for each case.
  - Each case's seeded step plan is used unchanged. Every criterion reads "Confirm by: the focused command; pass when
    TC-<n> passes". The focused command runs a test file the test stage writes later, and step S1's Proof runs the
    behaviour directly (`node -e` with assertions).
  - So every slice puts implement where F31 happened: a good Proof, and criteria whose Confirm-by tests do not exist
    yet. Test-spec and validate-existing run first, as in a delivery.
- **Part 2, no harm: 6 deliveries.** `test/shiploop_e2e/run.py --case csv-report`, the case where F31 last happened
  live, 3 per arm, in the order A B B A A B.

## Measures (`score.py`)

- **F31 send-back.** An implement send-back that says a criterion's confirmation (its Confirm by, or the criteria's
  tests) needs a test that implement may not write, that does not exist yet, or that the test stage writes. A send-back
  that blames only the step's Proof needing an unwritten test is the proof-order class, not F31.
  - `score.py`'s pattern lists candidates.
  - Every implement send-back is labelled from `score.py --blind` into `labels.jsonl`, with the reading quoted. That list
    shows the headline and summary only, shuffled, with no run or arm, and the labels are made before the scores are
    joined.
- **Tests written at implement (slices).** A test file among the candidate's changed paths after implement. A slice
  stops before the test stage, so any test file there is implement's.
- **Checks (slices).** Every case check exits 0 on the candidate.
- **Delivery pass (Part 2).** run.py's verdict: every hidden check passes.
- **First-try done (slices).** The item's first implement result is done.

## Decision rule

Adopt (merge to main and release) only when all four hold:
1. Arm B has no F31 send-back.
2. Arm B writes no test at implement.
3. No harm: B's slices pass their checks at least as often as A's, and B's deliveries pass at least as often as A's.
4. Every run finished, and every candidate send-back is labelled.

The benefit is A's F31 count. If A has none, the mechanism is unexercised and the benefit unmeasured, as with fix 1
(journal E15 and E16). The change is then adopted on 1 to 4 alone, because it states what the gate already does: at
implement's done, ShipLoop runs only the step's Proof. It also removes a contradiction that implement itself named.

If 1 or 2 fails, the change is not adopted and the branch stays off main. If 3 fails, every failing run is read. The
change is adopted only if each failure is shown to be unrelated to it (infrastructure, a port, a host timeout).

Power: there are 8 slices per arm. If A's F31 rate were 10% per slice, A would show at least one 57% of the time; at
30%, 94% of the time.

## Result

Not yet run.
