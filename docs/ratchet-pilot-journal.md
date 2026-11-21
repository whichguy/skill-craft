# Ratchet pilot journal

A living journal for the owner's idea of 2026-11-20: build a request in one pass, then let tests and what was learned
drive every further pass. Working name **Ratchet** (owner, 2026-11-20: "I like the name Ratchet. We can go with that for
now"). Nothing under `skills/` changes in this pilot; the apparatus is `docs/experiments/ratchet-pilot-20261120/`.

Status words: **firm** (measured, registered reading), **interim** (measured once or with a known limit),
**exploratory** (not registered), **superseded** (kept, with the date and the reason).

## 0. Where it ended (2026-11-21 00:40; the readings are registered, the verdict is mine for the owner to accept or not)

**Verdict: do not build Ratchet.** The half of the idea about steps held; the half about the loop did not.

- **One session builds these products correctly.** Five of six whole-loop first builds passed every held-out check
  (section 10, "P3"), and on Grokbot-local a single session with no plan passes both browser yardsticks, at low
  effort in 6.8 minutes (section 17). Planned steps are not what made any of these deliveries correct.
- **Failed tests drove almost nothing.** One acceptance clause failed naturally in the first five whole loops. The
  cycles after the first build were spent on requirements the loop wrote for itself, at 7.0 times ShipLoop's time on
  the one matched cell (R3.4), and no run stopped by itself.
- **Most of what the closing looks added is not the request's.** Two outside judges accept 10 of 59 additions and 2
  of 23 reported gaps (section 13); 6 of 9 tested additions fail on a correct reference (F15).
- **Test success alone is not a safe exit.** The due-times loop ended with 316 of 316 of its own items passing and
  5 of 8 held-out checks failing, from its first build to its last: its tests agreed with its specification's
  reading of the request, and the reading was not the customer's (F20). A repair start went green while its product
  got worse (F12), and one cycle's invented requirement rewrote 21 earlier tests (F21).
- **For the E2E harness:** a held-out yardstick written before any build exists misgrades correct builds until it
  has been calibrated on several independent builds and proven with planted defects (F18).

| Registered reading | Result |
|---|---|
| R1.1 the test pass is valid (at most 10% of clauses fail on a correct product) | not met: 8% to 15%, and a second correct delivery fails more |
| R1.2 the test pass is strong (80% of 37 calibrated defects) | met: 37 of 37 (first form 34) |
| R1.3 enrichment helps the tests | not shown by its rule |
| R2.1 the loop repairs what its tests show (80%) | not met: 6 of 8 |
| R2.2 the closing look finds what the tests miss | could not be read: the tests missed nothing planted |
| R2.3 closing-look clauses are sound (at most 20% fail on a correct reference) | not met: 6 of 9 |
| R3.1 no held-out check lost | met on five whole loops, not on due times (3 of 8 throughout) |
| R3.4 time against ShipLoop, matched cell | slower: 91.8 minutes against 13.2 |
| P4 a wrong test, by hand | not run; one natural case was handled correctly |
| R5.1, R6.1, R7.1 Grokbot-local is hard enough, on either yardstick, on any of three runners | not met: no headroom |
| R5.2, R6.2 quality at the end, bare against ShipLoop | no difference shown |
| J1 to J4 the closing looks' additions, judged blind | 10 of 59 belong; 2 of 23 gaps real; kappa 0.42 |

Added 02:00: the two results that were open when this was written are in section 17. The Ratchet arm on
Grokbot-local ended after 207.7 minutes with every check of both yardsticks passing at every stage, as at its first
build (12.3 times a bare session's time). Each build's own tests against 60 seeded faults: ShipLoop 37, the bare
sessions 24 to 31, the Ratchet builder 23 (F22): the one measured thing ShipLoop's extra time buys.

Added 03:15: the branch was merged into `main` on 2026-11-21 at 03:09 with the owner's yes. Section 19 records
the merge, completes the audit of what sessions saw, and adds a later result about the enrichment text.

## 1. The idea, in the owner's words (2026-11-20)

1. First message: ShipLoop elaborates a request, plans, and builds step by step. "It's not by breaking it up into steps
   that makes it not go well. It's more like: take a one-shot, and then basically use the accumulated test cases based
   on the specs, which is actually the thing that will create the cumulative next task to do." The failed test cases
   "create the next set and group of plans". Every shot still goes through the inner-loop duties (lint and the rest),
   folded into the one prompt. "It really depends on [...] that the spec is extremely well understood [...] and that
   the test cases are really good at enforcing the spec or the implied intention from the spec." The owner asked
   whether this is a good idea and for test scenarios, possibly as another skill used as a simulation environment.
2. Second message: learnings discovered during the implementation should "elaborate out some of the specs or more
   clearly define some of the specs that weren't enumerated", and those become new tests. "The test case success is the
   only thing that's actually gating the exit."
3. Third message: a specific stage at the end, even when the tests pass: "Based on what we learned compared to the
   original specification, is there any delta that was implicitly unknown or has been discovered that would elongate the
   new specification that wasn't adhered to?" Then the builder again ("based on this specification, based on the current
   code, build out any of the implementation pieces that don't match the spec"), then a heavy tests phase ("based on the
   full spec or any implicitness, define all the test cases. Run those test cases [...] until they succeed"). Test
   cases themselves produce learnings that may change the spec. "Try to use the until-loop if you can."
4. Fourth message: run it with a smaller model as the runner, "Sonnet High or Sol 6.2 on high"; one of them is enough.

## 2. What the records already said (read before designing)

Sources: `docs/shiploop-sdlc-structure-journal.md` rounds 4 to 6 and the guard round; commits
67ac34ae2b996205ba6018ebbd7f78bee9d338dd (the fewest-steps rule, adopted 2026-11-20) and
4a2020d5aa7396d621bbdd51bb1fa61626ab96ca (two whole deliveries on that rule); `docs/planning-time-analysis-2026-10-06.md`
section 5; `docs/shiploop-parallel-execution-journal.md` F87 and F88.

| Claim of the idea | What is measured | Reading |
|---|---|---|
| Step breakdown is not what makes a delivery correct | One step instead of two to four: the same held-out checks, 19 to 44% sooner on Sonnet 5.5 high, 30% on Grok 4.6 xhigh; adopted as ShipLoop's rule | supported, and already shipped |
| A first build mostly lands | 83 of 84 graded runs and every counted slice pass every held-out behaviour check at the accepted `implement` snapshot of the last step | supported on these cases, with the limit below |
| Planning can go | 30 to 40% of an inner-loop slice is spent before the first product edit; a substantive plan-review edit in 2 to 3% of runs | time is there; no run has built without `step-plan` and `test-spec` |
| Failed tests drive the next task | The builder's own tests fail in about 5% of recorded steps; `test` is refused in 43% of steps, mostly for a surviving seeded fault | untested: nothing failed for a loop to work on |
| Tests enforce the spec | Shipped suites left 74 of 448 stated conditions unpinned; a second look handed every condition lifted the catch rate on those from 55.1% to 84.8% (commit f9e225ce29bdfc0cec8b2cb742c6b4968b5764dd, on the unmerged branch `eeff/effort-harness-de6729`) | the weak link |

Limits I had understated to the owner and Sol's review corrected (checked against `test/shiploop_e2e/slice.py` and the
journal):

- A slice seeds only the stages before `step-plan`. `step-plan`, its review and `test-spec` still run, and the one-step
  arms kept every planning output and gate. So no record shows a build succeeding without them.
- "First complete implementation" is the accepted snapshot of the last step's `implement`, after its proof gate, not the
  first code written.
- E18 (F88, firm for Claude on one state): with the tests left unchanged and green, a redo bent a new feature behind an
  invented switch to satisfy an older test, and failed its held-out checks. Protecting a test from edits does not
  protect the product from being shaped to it.

## 3. Outside review before building (Sol 6.1, max effort, read-only, 12 min 40 s)

Question and verbatim answer: `docs/experiments/ratchet-pilot-20261120/review/`. The review was asked before the owner's
second to fourth messages, so it judged my first draft (tests written before the build, frozen). Its headline: pilot the
loop as a different way to supply the work, do not yet remove planning stages or build a production skill.

What I checked in the repository and found true: F88 as quoted; the `stand-in-rules` case and its four calibrated wrong
implementations (`test/shiploop_e2e/evaluators/e1b_subtle_stand_ins.py`, `fixtures/stand-ins/stand-in-rules/`); the six
named defects of `test/fixtures/quality/reference_due_times.py`; the slice's seeding boundary. Not checked by me: its
recomputed 1,266 of 1,267 total and its five outside paper citations.

What it changed in the design:

| Sol's point | In the pilot |
|---|---|
| A frozen suite gives a wrong "done" when a test is wrong: the builder needs a way to challenge a test, and someone else corrects it | Fix reports carry a Disputed section; a dispute goes to a referee session that owns the tests, never to the builder |
| "Nothing fails" is not "the request is complete" | The owner's closing stage (delta) asks that question each cycle; held-out checks, never fed back, measure it |
| Cheapest test that could sink the idea: run the proposed suite against known wrong implementations before paying for builds | Scenario P1 comes first and uses the harness's calibrated defects |
| Planted defects give the repair loop something to do; weakening the model does not | Scenario P2 |
| Compare with today's fewest-steps ShipLoop, charge the whole path, register failure readings before speed | Section 6 |
| No iteration cap as a product rule | `--max-cycles` and `--max-fixes` are limits of this apparatus; a run they end is reported as stopped, never as failed to converge |
| A deliberately wrong test as a control | Scenario P4, run if P1 to P3 finish |

Where the pilot does not follow it, and why: Sol advised keeping every planning responsibility and writing tests blind
to the code. The owner's later messages fix the order (build, then a heavy test pass, then the closing look), so the
pilot tests that order: the test owner is a different session from the builder, judges by the specification, and sees
the product. Tests written blind to the code are an arm this pilot does not run.

## 4. The loop the pilot runs

`docs/experiments/ratchet-pilot-20261120/ratchet.py` owns the order and writes every prompt; a model session does one
stage and knows only the files.

1. **spec**: the request as numbered clauses, each with an Observable line and a Source (`request`, `existing`,
   `choice`), in `ratchet/spec.md`.
2. Then cycles:
   - **build**: cycle 1 builds the whole request in one pass with every duty folded in (tests the request asks for,
     documents, style, the project's own checks); later cycles build what does not yet match the longer specification.
     It runs inside an Until Loop (the bundled runtime, `skills/improve/runtime/until-loop`) whose exit check is the
     gate.
   - **tests** (the heavy test pass): a session that did not build writes acceptance tests for every clause, with the
     last accepted and first refused value of every limit, runs them, leaves a test the product fails as it is, and
     reports what it learned. The script then freezes them.
   - **fix**: while the gate fails, a session fixes the product inside an Until Loop whose exit check is the gate. The
     gate puts back any change to the frozen tests or the spec and counts it.
   - **delta** (the closing look): every check passes; a session weighs the stages' reports, uses the product, and adds
     a clause for anything learned that the specification does not say. The spec only grows: a changed clause is put
     back by the script.
3. The run ends when a delta stage adds no clause.

**The gate** (`gate.py`, standard library only, copied beside each run so no prompt names this repository): every
clause's command from `ratchet/acceptance.json`, the project's own checks, and `node --check` on changed JavaScript
files. A failing command is run once more; one that passes the second time is recorded unstable and counted as passing.

Only script-run checks decide anything. Held-out checks are never shown to a session and never fed back.

## 5. Apparatus checks made before any counted run

- `selftest_fake.py`, a scripted stand-in for the model that misbehaves once in each guarded way: the run records 8
  sessions, 6 gates and 12 snapshots, converges in two cycles, puts back a builder-written acceptance file, a weakened
  frozen test, a product edit by the test owner and a rewritten clause, and keeps the new clause. Rerun:
  `python3 ratchet.py run --case selftest --host fake --fake selftest_fake.py --output DIR` then
  `python3 selftest_fake.py DIR`.
- `grade.py strength` on the harness's own test files for the orders case: its strong tests catch 4 of 4 calibrated
  wrong implementations and pass the reference; its weak tests catch 0 of 4. So the instrument tells strong from weak.
- `grade.py`'s held-out grader for the orders case: the reference passes both files; each wrong implementation fails
  the strong file.
- The Until Loop runtime starts from a copied folder with a parent-written contract and an absolute receipt path, and
  prints the work, the exit check and the `done` command.
- ruff on the four scripts: all checks passed.

## 6. Registered scenarios and readings (written before any counted run)

Runner: Codex `gpt-6.2-sol` at effort high (the owner's choice), one run a cell. Two P3 cells also on Claude
`claude-sonnet-5-5` at high, and one on `gpt-6.2-sol` medium for a like-for-like time. Cases and requests are the E2E
harness's own, copied verbatim into `cases.json`; a fixture's `docs/shiploop` knowledge home is removed so Ratchet
writes its own specification.

**P0, smoke (not counted).** `stand-in-rules` from the request, whole loop. It exists to find apparatus faults.

**P1, can the test pass carry the exit?** For `stand-in-rules`, `ticket-assignment` and `ticket-due-times`: spec from
the request and the base, then the harness's correct reference delivery laid in as the build (`--build-from`, no build
session), then the heavy test pass, stop. `grade.py strength` then runs the frozen suite against the reference, a second
correct delivery where the case has one, and every calibrated defect (4, 27 and 6).

- R1.1 **valid**: at most 10% of clauses fail on the correct reference, and the second correct delivery fails no clause
  the reference passes.
- R1.2 **strong**: the suites catch at least 80% of the 37 defects, pooled. Under 60% reads as too weak to carry the
  exit alone. Between is undecided. A defect counts as caught only by a clause that passes on the reference.
- Reported apart, no bar: defects that break a sentence of the request against defects that break a rule the base's
  own documents state.

**P2, does the loop repair what it is shown, and find what it is not?** Repair starts (`--start-tree`, `--frozen-from`):
the reference with one calibrated defect, the P1 run's frozen spec and suite, then gate, fix, delta and on. Starts:
all four `stand-in-rules` defects; for each ticket case the first two defects the P1 suite catches and the first two it
misses, in the fixture's order (fewer where fewer exist).

- R2.1 **repair works**: of the starts whose defect the suite catches, at least 80% end with every held-out check
  passing that the clean reference passes, with the product, not the tests, changed.
- R2.2 **the closing look finds it**: of the starts whose defect the suite misses, the share that end with those
  held-out checks passing. A third or more reads as the stage earning its place; none reads as no value shown.
- R2.3 **false clauses**: of the clauses delta stages add, at most 20% fail on the clean reference.

**P3, the whole loop from the request.** Sol 6.2 high: `shared-expenses`, `ticket-assignment`, `node-chess-engine`,
`ticket-due-times`. Sonnet 5.5 high: `ticket-assignment`, `node-chess-engine`. Sol 6.2 medium: `ticket-assignment`.

- R3.1 **no loss**: every held-out check passes at the end of every run.
- R3.2 reported: held-out behaviour checks passing at the first build.
- R3.3 reported: runs in which a failing acceptance test led to a product change, and runs in which a delta clause did.
- R3.4 **time**, whole path from the request to the end, read only where the model and effort match a record:
  `ticket-assignment` on Sol 6.2 medium against today's whole ShipLoop delivery of the same case (13.2 minutes, 18 of 18
  held-out checks, commit 4a2020d5aa7396d621bbdd51bb1fa61626ab96ca; that delivery also released and reviewed). 15% or
  more either way reads as slower or faster; inside reads as no difference shown. Other cells report minutes only.

**P4, a wrong test (control, if time allows).** One frozen test edited by hand to contradict its clause, on the clean
reference. Expected: the builder disputes it, the referee corrects it, the held-out checks still pass at the end.

**Stop rules of the pilot.** A run ended by `--max-cycles` (3) or `--max-fixes` (4 a cycle), or by the same checks
failing after two fix sessions in a row, is reported as stopped by the apparatus. A session that reads a path of this
repository (the audit looks for held-out file names in its event stream) is reported and its run is not counted.

## 7. Limits known before the run

- The test owner sees the product (the owner's order). Tests written blind to the code are not compared.
- The gate's lint is a syntax check; ShipLoop's lint pass and its seeded-fault check are not ported. Suite strength is
  measured after the run, against calibrated defects, not inside the gate.
- One run a cell. The four build cases sat at their ceiling in every earlier round, so P3 can show a loss, not a gain.
- Sol 6.2 high has no recorded ShipLoop baseline; only the three matched cells read a time.
- A specification may choose where the request is silent, and the reference may have chosen otherwise; such clauses
  are listed under "fails on the reference" and never count as kills.
- The calibrated defects are single edits to one reference implementation; two of the 27 also edit the base's own
  tests.
- Sessions run with the harness's usual permissions (Codex in a throwaway HOME with full disk access), so secrecy of
  the held-out checks rests on prompts that name no repository path and on the audit, not on a sandbox.

## 8. Amendment 1, 2026-11-20 19:15: a rich enrichment stage and a heavy plan stage (before any counted run of them)

Owner, fifth message, while the smoke run and the first three P1 runs were in flight: the value is in reflecting after
the first tests pass and deciding "whether or not the specification needs to take another level"; the elaboration of
the prompt "should actually be quite rich", looking for "implied requirements, use cases"; and the sequence is the
incoming prompt, the enriched prompt, then planning, "which should be, again, fairly heavy. Not really break up the
steps", then build, build the tests, run them, "determine learnings and implicit spec elaborations", turn that into
another enriched prompt, repeat. "Once you're given the elaborated spec, you really want to look for the nuance,
iteratively look for the nuance [...] that needs to be considered to then go build."

What changed in `ratchet.py` (the first form is the registration commit 05224b48127a50dd5981706beb3aa28fd1c8bb85):

- **spec becomes enrich.** The stage first finds the use cases (ordinary use, its edges, the unhappy paths, the
  operator's work, where the change meets existing features), then the requirements each use case needs that the
  request never states. `ratchet/spec.md` now holds use cases (`### U-n`, with a Flow line) before clauses, and a clause
  may have `Source: implied: ...`.
- **plan, a new stage before every build.** One session writes `ratchet/plan.md`: Approach, Decisions, Nuances (what a
  quick build would get wrong, and where), Build order within the one pass, How we will know. It does not cut the work
  into steps. It runs inside an Until Loop that asks for one more full pass after the first that finds nothing to add
  (`required_trivial_reviews: 1`). It may add clauses; the script refuses a changed one.
- **build** follows the plan and reports where it was wrong. **tests** write one scenario test per use case as well as
  the tests per clause, and take scenarios from the plan and the build's discoveries. **delta** is asked whether the
  specification needs another level and may add use cases as well as clauses.
- The dry run (`selftest_fake.py`) now records 10 sessions with the two plan stages and passes; the given-build path
  runs spec, plan, tests.

What changes in the registration:

- **P1 gains a second arm.** The three P1 runs already in flight keep the first, plainer spec form (no use cases, no
  plan). The same three cases run again in the enriched form (enrich, plan, the reference as the build, tests). Same
  instrument, same 37 defects.
  - R1.3 **enrichment helps the tests** if the enriched suites catch at least 4 more of the 37 defects, pooled, and
    fail no more clauses on the correct reference in proportion. Within 3 either way reads as no difference shown. One
    run a cell, so this reading is interim whatever it shows.
  - R1.1 and R1.2 are read on the enriched arm, the design under test; the first-form arm is reported beside it.
- **P2 and P3 run the enriched form.** P2 starts from the enriched arm's frozen suites.
- The smoke run in flight is the first form; a second smoke is not run: the plan stage's only new machinery is the
  Until Loop's review count, which the first counted run with a plan stage shows or fails to show (reported).

## 9. Amendment 2, 2026-11-20 19:22: the loosest choice, in its own clause (after the first P1 result, before any enriched result)

The first P1 cell (section 10, F1) showed one arbitrary choice of the spec stage copied into the Observable line of
eleven request clauses, so a correct product failed them. Three prompt rules follow; the enriched arm of P1, and P2 and
P3, run with them.

- **spec (enrich):** a choice is the loosest requirement that still serves the user; never a spelling, wording,
  format, order or internal detail the request leaves open; a choice lives in its own clause and no other clause's
  Observable repeats it; another correct product built from the request alone must be able to pass every clause that
  is not a choice.
- **tests:** assert only what the clause states; a detail that belongs to another clause is tested there.
- **delta and plan:** a clause says what a user or operator needs to be true, not what this product happens to do
  (the smoke run's first closing look added five clauses, every one a description of current behaviour; section 10,
  F2).

Registration: the P1 enriched arm is amendment 1 plus these rules, for all three cases. The enriched orders run
already in flight without them (`p1e-stand-in-rules`) is kept as a labelled extra cell, exploratory, so the rules'
effect can be seen beside it. The comparison R1.3 (first form against enriched) therefore compares bundles: use cases
and implied requirements, the plan stage, and the loosest-choice rules together.

## 10. Results

Evidence folders are under `docs/experiments/ratchet-pilot-20261120/evidence/`; run folders are outside the repository
under `/Users/dadleet/e2e-runs/ratchet-pilot-20261120-b6eab2/` and may be pruned.

### P1, first form, orders case (`p1-stand-in-rules`; Codex gpt-6.2-sol high; one run)

| Measure | Result | Registered bar |
|---|---|---|
| Clauses | 63 (30 from the request, 21 choices, 12 existing) | none |
| Clauses that fail on the correct reference | 22 of 63 (35%): 11 choices, 11 request clauses | R1.1: at most 10% |
| Calibrated defects caught | 2 of 4 (`one-rule-missing`, `limit-never-trips`); missed `tested-only`, `cross-field` | R1.2: 80% pooled |
| Time | 12.9 min: spec 4.6, tests 7.7, gates 0.6 | none |
| Guards | nothing put back, no frozen file changed, no held-out name in either event stream | none |

- **F1 (interim: one run, mechanism read in the artifacts).** The request says each rule names "the 1-based line in
  its message". The spec stage chose a spelling, clause C-40 "formats each line validation error message with a
  `Line N: ` prefix" (Source: choice), and wrote "a message beginning `Line 1: `" into the Observable of every clause
  that throws. The reference writes `line 1: ...`. So eleven request clauses fail on a correct product for a capital
  letter, among them C-24 (quantity below 1) and C-38 (an open order with a shipping date), the clauses that would
  have caught `tested-only` and `cross-field`: both defects fail exactly the reference's 22 clauses and no other.
  By the registered rule (a defect is caught only by a clause that passes on the reference) they count as missed.
  The suite's power to see them is masked, not shown absent.
- A third of this spec's clauses are choices where the request is silent (21 of 63); 11 of those reject the reference
  (unknown key, repeated key, missing key, empty segment, empty id, empty price, message prefix, error order).
- Reading: R1.1 fails for this cell, and with it R1.2 cannot be read for it. In a full loop the builder builds to the
  spec, so these clauses pass there (the smoke run's first build passed 68 of 68); the cost appears when the product
  must also satisfy someone who read only the request, which is what held-out checks do.
- Evidence: `evidence/p1-first-orders/` (run.json, strength.json, spec.md, acceptance.json, tests-1.md, run-log.txt).

### Smoke, first form, orders case from the request (`smoke-standin-sol-high`; not counted)

- **F2 (exploratory).** Spec 4.9 min, 68 clauses; one-pass build 2.5 min inside an Until Loop that completed on its
  first iteration with the gate passing; heavy tests 7.5 min; first gate 68 of 68, so no fix stage; closing look 2.9
  min, 5 new clauses (C-69 to C-73), each marked "product keeps to it: yes" in its own report: which of two errors is
  reported first, how a number rounds at the edge of its type, what the shared counter holds after a failed batch.
  The stage used the product (its report lists the probes) and wrote down what the product does.
- **F3 (exploratory, the finished run).** Three cycles, 10 sessions, 38.8 minutes, final gate passing, ended by the
  apparatus limit (`stop: max-cycles`). The three closing looks added 5, 3 and 1 clauses, all marked "product keeps to
  it: yes"; no build after the first changed a held-out verdict and no fix stage ever ran. Held-out checks (the
  harness's strong and boundary test files): 2 of 2 at build-1 and at every later snapshot.
- **F4 (exploratory).** The final suite of that run against the calibrated variants: 13 of 76 clauses fail on the
  correct reference; 4 of 4 defects caught. Of the 8 closing-look clauses that got a test (C-69 to C-76), one (C-70)
  fails on the reference and four (C-69, C-71, C-73, C-74) are among the clauses that catch a defect. So a clause that
  only describes this product can still catch a real defect, and one in eight rejected a correct product.
- Evidence: `evidence/smoke-orders/` (run.json, hidden.json, strength.json, spec.md, the stage reports).

### P1, orders case, the three forms side by side (one run each; Codex gpt-6.2-sol high)

| Form | Clauses | Use cases | Clauses failing on the reference | Use cases failing | Defects caught | Minutes |
|---|---|---|---|---|---|---|
| first (`p1-stand-in-rules`) | 63 | 0 | 22 (35%) | 0 | 2 of 4 | 12.9 |
| enriched, amendment 1 (`p1e-stand-in-rules`, exploratory cell) | 63 | 8 | 11 (17%) | 2 | 4 of 4 | 19.1 |
| enriched, amendments 1 and 2 (`p1e2-stand-in-rules`) | 69 | 12 | 9 (13%) | 3 | 4 of 4 | 18.8 |

- **F5 (interim).** Use cases, implied requirements and the plan stage took the suite from 2 to 4 of 4 defects and
  halved the clauses that reject the reference; the loosest-choice rules took a little more off. Neither enriched form
  meets R1.1 (10%) on this case.
- Source of clauses: first form 30 request, 21 choice, 12 existing; amendment 1: 31 request, 19 implied, 10 existing,
  11 choice; amendments 1 and 2: 33 request, 20 implied, 12 existing, 16 choice. Under amendment 2 no Observable fixes
  a message spelling; two choices explicitly loosen ("one applicable validation error suffices", "no safe-integer
  ceiling").
- What still fails on the reference under amendment 2 is strictness the spec chose, not spelling: an unknown key, a
  missing key or a repeated key must be refused, an id must be finite, an empty price is out of range (C-30, C-31,
  C-32, C-36, C-37). Three items (C-67, C-68, U-12) fail only because the harness's reference for this case ships no
  tests of its own while the request asks for them: an artifact of the reference, not of the spec.
- The first real plan stage (`p1e-stand-in-rules`): 3.3 minutes, the Until Loop's receipt complete at iteration 2 with
  a trivial streak of 1 (the second full pass happened), five sections, no clause added.
- Evidence: `evidence/p1-first-orders/`, `evidence/p1-enriched-a1-orders/`, `evidence/p1-enriched-a2-orders/`.

### P1, first form, the two ticket cases (one run each)

| Case | Clauses (request / existing / choice) | Fail on the reference | Defects caught | Minutes (spec, tests) |
|---|---|---|---|---|
| ticket assignment (`p1-ticket-assignment`) | 190 (29 / 134 / 27) | 13 in the run's own gate; 16 in the first grading | 26 of 27; missed `validate-renamed` | 28.4 (7.7, 18.6) |
| ticket due times (`p1-ticket-due-times`) | 223 (41 / 144 / 38) | 45 in the run's own gate; 52 in the first grading | 5 of 6; missed `no-backfill` | 36.4 (12.1, 21.3) |

- **F6 (interim).** On an existing product the suite is strong: 31 of 33 calibrated defects on the two ticket cases.
  Pooled with the orders case the first form catches 33 of 37 (89%), over R1.2's 80%. Most of the suite pins what the
  product already does: 134 of 190 and 144 of 223 clauses have Source: existing.
- **F7 (interim).** Validity fails in a second way on ticket assignment. The reference passes within the bar (13 of
  190, 7%), but the harness's second correct delivery (`alternative`) fails 24 clauses the reference passes: 10
  choices, 3 request clauses, 11 existing. Its PUT answers `{id, assignee}`; clause C-6 (Source: choice) says "A
  successful assignee PUT returns the full ticket with HTTP 200", and tests of other clauses read the ticket out of
  that answer. The same mechanism as F1, seen only because a second correct product exists. R1.1's second half is not
  met.
- On due times a fifth of the clauses reject the reference (45 of 223 in the run's own gate): 27 of the 52 in the
  first grading are choices (how operators set the hours, limits on the setting, what the documents must say).
- **Apparatus note.** The first gradings ran before the fixes of section 11. In the graded copies seven or more
  due-times clauses failed with `fatal: not a tree object`: their tests read the base commit of the work repository,
  which a copied variant did not have. The grader now gives each variant that history, and both ticket suites are
  graded again; the first gradings are kept as `strength-first-grading.json` and the regraded numbers are reported
  beside them when they exist.
- Evidence: `evidence/p1-first-ticket-assignment/`, `evidence/p1-first-ticket-due-times/`.

### P1, first form, the two ticket suites graded again with the corrected grader (2026-11-20 20:00)

| Case | Clauses failing on the reference | Second correct delivery | Defects caught |
|---|---|---|---|
| ticket assignment | 13 of 190 (7%), the same as the run's own gate | fails 24 more clauses | **27 of 27** (the first grading had 26: `validate-renamed` is caught by C-75, a clause on the base's tests staying unchanged whose test reads the work repository's history) |
| ticket due times | 45 of 223 (20%), the same as the run's own gate | none exists for this case | 5 of 6, missed `no-backfill` |

- **F8 (interim).** First form, pooled: 34 of 37 defects caught (92%), R1.2 met. R1.1 not met: 35%, 7% with a second
  correct delivery failing 24 more, and 20%.
- `grade.py visible`: the held-out graders see 4 of 4 orders defects, 6 of 6 due-times defects and 25 of 27
  ticket-assignment defects. They cannot see `backoff-linear` and `validate-renamed` (as the review's finding 5
  inferred), so those two are never used as repair starts.
- Evidence: `strength.json` beside `strength-first-grading.json` in the two ticket evidence folders;
  `evidence/hidden-visible/`.

### P2, repair starts on the orders case (enriched frozen suite of `p1e2-stand-in-rules`; one run each; `--max-cycles 1`)

| Planted defect | First gate | After one fix session | Held-out, start to end | Product / frozen tests | Minutes |
|---|---|---|---|---|---|
| `one-rule-missing` | 62 of 81 | 81 of 81 | 1 to 2 of 2 | 2 files changed / unchanged | 5.6 |
| `tested-only` | 67 of 81 | 81 of 81 | 0 to 2 of 2 | 2 files changed / unchanged | 5.4 |
| `limit-never-trips` | 63 of 81 | 81 of 81 | 1 to 2 of 2 | 2 files changed / unchanged | 6.4 |
| `cross-field` | 66 of 81 | 81 of 81 | 1 to 2 of 2 | 2 files changed / unchanged | 5.5 |

- **F9 (interim: four runs, one small case).** The loop repairs what its tests show. In each start the script's
  failing list held the planted defect's clause beside the strictness clauses the reference never met; one fix
  session (2.3 to 3 minutes, its Until Loop complete at iteration 1) brought the gate to 81 of 81; a held-out check
  that failed at the start passes at the end; no frozen file was touched, nothing was disputed, no held-out name
  appears in an event stream. R2.1 on this case: 4 of 4.
- The fix also made each product stricter where the spec had chosen strictness (unknown, missing and repeated keys
  refused) and added the tests the request asks for: the same work in every start, 94 to 121 added lines.
- Each start's one closing look added 1 to 3 clauses; with the limit at one cycle they got no tests, so R2.3 is not
  read here.
- All four defects were ones the suite catches, so these starts say nothing about R2.2 (the closing look finding
  what the tests miss).
- Evidence: `evidence/p2-orders/` (each start's run.json, hidden.json, fix-1.md, delta-1.md; the two chain logs).

### P1, enriched form (amendments 1 to 3), the two ticket cases, and P1 as a whole (2026-11-20 20:57)

| Case | Form | Clauses (request / implied / existing / choice) | Clauses failing on the reference | Use cases failing | Second correct delivery, beyond the reference | Defects caught | Minutes |
|---|---|---|---|---|---|---|---|
| orders | first | 63 (30 / 0 / 12 / 21) | 22 (35%) | none written | none exists | 2 of 4 | 12.9 |
| orders | enriched (1, 2) | 69 (33 / 20 / 12 / 16) | 9 (13%) | 3 of 12 | none exists | 4 of 4 | 18.8 |
| ticket assignment | first | 190 (29 / 0 / 134 / 27) | 13 (7%) | none written | 24 clauses | 27 of 27 | 28.4 |
| ticket assignment | enriched (1 to 3) | 192 (22 / 41 / 134 / 12), 17 use cases | 15 (8%) | 5 of 17 | 14 clauses, 3 use cases | 27 of 27 | 46.7 |
| ticket due times | first | 223 (41 / 0 / 144 / 38) | 45 (20%) | none written | none exists | 5 of 6 | 36.4 |
| ticket due times | enriched (1 to 3) | 238 (29 / 46 / 158 / 20), 15 use cases | 35 (15%) | 8 of 15 | none exists | 6 of 6 | 46.7 |

Registered readings, on the enriched arm:

- **R1.2 strong: met.** 37 of 37 calibrated defects caught (first form 34 of 37). No command failed to end in either
  ticket grading, none was unstable on the reference, although the machine's load average was above 30 at the time.
- **R1.1 valid: not met.** 13%, 8% and 15% of clauses fail on the correct reference, and the second correct
  ticket-assignment delivery fails 14 clauses and 3 use cases the reference passes.
- **R1.3 enrichment helps the tests: not shown by the registered rule.** The enriched suites catch 3 more defects;
  the rule asked for 4, and after the first form's regrade to 34 only 3 were left to gain, so the rule could no longer
  be met. The clause share that rejects the reference fell on two cases (35% to 13%, 20% to 15%) and held on the
  third (7% to 8%); the second correct delivery fails 14 clauses where it failed 24.

- **F10 (interim).** In both forms the heavy test pass is strong enough to carry an exit on these cases. What it is
  not is neutral: between 8% and 15% of what it enforces is the specification's own addition. In the enriched form
  that addition is mostly `implied` clauses (14 of the 20 items failing on the ticket-assignment reference, 19 of the
  43 on due times), which is what the enrichment stage is asked to write. The second ticket-assignment delivery shows
  the cost: a correct product that made different choices fails 17 items.
- **F11 (interim).** Scenario tests for use cases are the most brittle items: 5 of 17 and 8 of 15 fail on the correct
  reference, 3 of 12 on orders. A scenario walks a whole flow, so one stricter step fails it.
- `no-backfill`, the one due-times defect the first form missed, is caught in the enriched form by one clause
  (C-187). The enriched due-times spec has 46 implied clauses and 158 existing ones.
- Cost of the enriched form on a ticket case: enrich 10 to 13.5 minutes, plan 5.5 to 6, heavy tests 24 to 27; both
  plan loops completed at iteration 2 with a trivial streak of 1 and added clauses (2 on due times).
- Evidence: `evidence/p1-enriched-ticket-assignment/`, `evidence/p1-enriched-ticket-due-times/`.

### P2, repair starts on the two ticket cases (enriched frozen suites of `p1e2-ticket-*`; one run each; `--max-cycles 1`; 2026-11-20 21:00 to 22:00)

| Case, planted defect | First gate | Last gate | Fix sessions / referee sessions / disputes | Held-out, start to end | Frozen tests | Stop | Minutes |
|---|---|---|---|---|---|---|---|
| assignment, `filter-or` | 180 of 209 | 207 of 209 | 3 / 2 / 8 | 17 to 18 of 18 | 3 files changed by rulings (+90 −60) | stuck | 37.7 |
| assignment, `filter-after-page` | 185 of 209 | 209 of 209 | 1 / 1 / 1 | 17 to 18 of 18 | 1 file changed by a ruling (+11 −6) | cycle limit | 26.8 |
| due times, `version-two` | 198 of 253 | 246 of 253 | 3 / 1 / 16 | 5 to 4 of 8 | 6 files changed by rulings (+159 −87) | stuck | 41.0 |
| due times, `priority-moves-due` | 208 of 253 | 253 of 253 | 1 / 0 / 0 | 6 to 4 of 8 | unchanged | cycle limit | 16.9 |

- **Apparatus fault, found in these runs and fixed between the second and the third.** The first two starts
  (`filter-or`, `version-two`, both launched 20:59) ended "stuck" on tests that start the previous release from a Git
  commit (`22f8405`). That commit existed only in the repository of the run the suite was frozen in; a repair start
  had a new repository. Every item still failing at their last gates is one of these (C-135 and U-15; C-22, C-67,
  C-68, C-70, C-124, C-233 and U-11, each a Git exit 128, "not a valid object name"). `setup()` now gives a repair
  start the source run's objects (`.git/objects/info/alternates`), and the two later starts reached a full gate. The
  two "stuck" stops are the apparatus's.
- **R2.1, repair works: not met, 6 of 8 (75%; the bar was 80%).** The four orders starts and both assignment starts
  end with the planted defect's held-out check passing and the product changed. Both due-times starts end with
  fewer held-out checks passing than the defective start had.
- **F12 (firm for this case; two runs).** A green gate is not a correct product. In `priority-moves-due` one fix
  session brought the gate from 208 to 253 of 253, nothing was disputed, no frozen file changed, and the held-out
  checks fell from 6 to 4 of 8 (`cli`, `migrate`, `restart` and `rollback` fail at the end). The planted defect was
  repaired (its two items, C-13 and U-2, pass). The other 43 failing items are exactly the 43 the correct reference
  also fails (section "P1, enriched form": 35 clauses and 8 use cases): the specification's own additions. Making
  the product meet them broke behaviour the held-out checks require. `version-two` shows the same fall (5 to 4).
- **F13 (interim).** The dispute route is used, and it is expensive. `filter-after-page`: one dispute (C-74, a
  temporary path too long for the test's own fixture), one ruling, a corrected test, a full gate. `filter-or` and
  `version-two`: 8 and 16 disputes, rulings that rewrote 3 and 6 frozen test files, and 37.7 and 41.0 minutes, most
  of it spent on the tests my setup had made unpassable. No role owns a test's fixtures or environment: the builder
  may not edit tests, the referee rules on a test against its clause, and neither could supply the previous release.
- **R2.2, the closing look finds what the tests miss: cannot be read.** Every calibrated defect is caught by the
  enriched suites (37 of 37), so there was no missed defect to plant.
- Evidence: `evidence/p2-tickets/` (each start's run.json, hidden.json, gate records, fix, referee and delta notes).

### P3, the whole loop from the request (amendments 1 to 3; one run each; three cycles at most)

| Case, effort | Minutes (to first build) | Sessions | Output tokens | Gate at each cycle | Held-out at first build / at the end | Closing looks: added (product did not keep to it) | Later builds changed (product, its own tests, documents) |
|---|---|---|---|---|---|---|---|
| orders, high (smoke, first form, not counted) | 38.8 (7.4) | 10 | 84,885 | 68/68, 73/73, 76/76 | 2 of 2 / 2 of 2 | 5 (0), 3 (0), 1 (0) | +66 −10, +40 −6 |
| chess, high | 85.1 (20.5) | 13 | 198,671 | 111/111, 118/118, 120/120 | 10 of 10 / 10 of 10 | 7 (1), 2 (1), 1 (0) | +145 −25, +92 −2 |
| shared expenses, high | 118.3 (22.4) | 14 | 260,499 | 106/107 then 107/107 after one fix, 116/116, 124/124 | 6 of 6 / 6 of 6 (5 of 6 after build 2, 6 again after its tests) | 9 (3), 7 (1), 3 (1) | +731 −42, +343 −49 |
| ticket assignment, high | 132.9 (23.4) | 13 | 308,043 | 225/225, 232/232, 238/238 | 18 of 18 / 18 of 18 | 7 (4), 5 (2), 6 (3) | +536 −24, +567 −38 |
| ticket assignment, medium | 91.8 (17.2) | 13 | 177,302 | 181/181, 188/188, 191/191 | 18 of 18 / 18 of 18 | 6 (4), 3 (1), 3 (2) | +443 −20, +213 −5 |
| ticket due times, high | 149.7 (32.3) | 13 | 320,112 | 301/301, 311/311, 316/316 | 3 of 8 / 3 of 8 (the correct reference passes 7) | 7 (4), 4 (1), 4 (3) | +570 −48, +409 −16 |

Minutes by stage (spec, plan, build, heavy tests, fix, closing looks, gates and script): chess 9.6, 14.9, 15.1, 29.8,
0, 9.8, 5.9; shared expenses 7.1, 16.2, 26.9, 34.8, 3.0, 15.3, 15.1; ticket assignment high 9.6, 15.1, 26.9, 49.0, 0,
19.6, 12.7; medium 6.0, 11.2, 17.8, 32.6, 0, 9.9, 14.2. The heavy test pass is the largest stage in every run.

Registered readings:

- **R3.1, no loss: met on five runs, not met on the sixth.** On orders, chess, shared expenses and both
  ticket-assignment runs every held-out check passes at the end. The due-times run fails 5 of 8 from its first
  build to its end (F20 below).
- **R3.2, reported.** On five runs the first build already passed every held-out check, so the loop had nothing to
  recover. On due times the first build passed 3 of 8 and the loop recovered nothing.
- **R3.3, reported.** A failing acceptance test led to a product change in one run of five: shared expenses, cycle 1,
  clause C-18 (a group id too long to address in a URL), repaired by one fix session of 3 minutes. Closing-look
  clauses led to product changes in every run: each second and third build changed the product (the last column).
- **R3.4, time: slower.** Ticket assignment on Sol 6.2 medium took 91.8 minutes and 177,302 output tokens; ShipLoop's
  whole delivery of the same case on the same model and effort took 13.2 minutes and 29,066 (7.0 times the time, 6.1
  times the output tokens), with the same 18 of 18 held-out checks. Ratchet's first build alone came at 17.2
  minutes. ShipLoop's delivery also released and reviewed; Ratchet stops at a product.
- **No run converged.** All six ended at the three-cycle limit with the last closing look still adding items (1, 1,
  3, 6, 3, 4). The limit is the apparatus's, so "does it end by itself" is not answered; nothing seen suggests it does.

**F14 (firm on these cases).** With every first build already correct, all the work after the first gate came from
the loop's own specification. The second and third builds added 237 to 1,103 lines a run (last column). On ticket
assignment the product's source alone went from +85 −16 lines at the first build to +162 −24 at the end (medium) and
from +96 −19 to +304 −38 (high); ShipLoop's delivery of the same request is +71 −17. What the added requirements are
worth is section 13's question.

**F15 (firm; one run with a reference). R2.3, false clauses: not met.** On the medium ticket-assignment run, 9 of the
12 items its closing looks added got tests (the third look's three did not: the cycle limit), and 6 of those 9 (67%;
the bar was 20%) fail on the harness's correct reference: C-164 to C-167, C-171 and C-172. Of everything that suite
enforces (173 clauses, 18 use cases), 25 clauses (14%) and 9 use cases (50%) fail on the reference, and the second
correct delivery fails 12 more items. By the source the specification gave them, the 34 failing items are 18
implied, 6 discovery, 5 existing, 3 choice and 2 request.

**F20 (firm; one run, and the same reading in a second, independent specification).** Tests written from the
loop's own specification cannot see the specification's own reading. The due-times request says "The tickets
already in the production data file get due times too" and "Due times are switched on in production only once the
data file holds them". The enriched specification read that as a step for an operator: a preparation command run on
the file first, and a service that refuses to start with due times on while any ticket lacks one (U-11 to U-13). The
held-out checks, and all eight ShipLoop builds of this request on record, read it as the new release filling the
file in when it starts. Five held-out checks start the service on a file without due times; each fails with
"cannot start: ... tickets[0].due (T-0001) is missing". The run's gates read 301 of 301, 311 of 311 and 316 of 316;
the held-out checks read 3 of 8 at the first build, after every build and at the end, 149.7 minutes and 320,112
output tokens later. The enriched specification of the test-strength run (`p1e2-ticket-due-times`) made the same
choice, which is why the two repair starts above lost held-out checks while their gates went green.

**F21 (firm; one run).** The acceptance suite does not hold across cycles. The second closing look added C-291, "the
product must refuse a saved deadline that precedes its creation". The third build honoured it, found that 21 frozen
items used fixtures with exactly such deadlines, left the tests alone and said so ("The exit check is blocked by 21
frozen checks"); its gate read 290 of 311. The test session that followed may not touch the product. It rewrote the
tests (546 lines added, 63 removed across 8 files) and the gate read 316 of 316 with the product unchanged. Each
role kept to its rules. The result is that a requirement the loop invented in one cycle rewrote the checks of
earlier cycles, and nothing outside the loop looked. In the other five runs no build broke an earlier test, and later
test sessions removed 2 to 50 lines of earlier test files.

Evidence: `evidence/p3/` (each run's run.json, hidden.json and closing-look reports; `summary.json` for all runs;
`strength-ticket-assignment-medium.json`, verdicts without command output). The plans stay in the runs folder.

### What a delivery's own tests are worth: ticket assignment, ShipLoop's delivery against Ratchet's (no model call)

Two measures, both run after the fact on finished deliveries (`baseline.py`, `mutate.py`).

Calibrated defects (27), each suite laid over the harness's correct reference and every defect:

| Suite | Tests | Failing on the correct reference | Defects caught |
|---|---|---|---|
| the starting project's own tests | 117 | 0 | 3 of 27 |
| those and ShipLoop's delivered tests (2 files) | 122 | 4 of its 5 | 7 of 27 |
| those and the Ratchet builder's own tests (5 files) | 138 | 15 of its 21 | 18 of 27 (1 not judged) |
| Ratchet's frozen acceptance suite | 191 items | 34 (25 clauses, 9 use cases) | 26 of 27 |

Seeded faults on the lines each delivery itself changed (the E2E harness's fault catalog):

| Delivery | Product source lines changed | Fault sites | Its own tests | Ratchet's acceptance suite |
|---|---|---|---|---|
| ShipLoop, Sol 6.2 medium | +71 −17 | 7 | 7 of 7 caught | none exists |
| Ratchet, Sol 6.2 medium, final product | +162 −24 (its first build: +85 −16) | 47 | 35 caught, 6 survived, 6 did not end | 41 caught, 6 survived |

- **F16 (interim; one case, one delivery each).** A delivery's own tests are written to its own product: moved onto
  another correct product, most of them fail (4 of 5, 15 of 21), so "catches N of 27" is a low reading for both and
  is not a ranking. On its own product each suite is strong: ShipLoop's catches all 7 faults on the 7 sites its
  small change has; Ratchet's builder tests catch 35 of the 41 that ended.
- **The acceptance suite adds almost nothing over the builder's own tests on seeded faults.** The same six faults
  survive both (five in `src/http.js`, one in `src/format.js`). What the separate test session adds on this measure
  is the six faults on which the builder's suite did not end within 300 seconds.
- **Apparatus correction, 22:30.** The first run of the second table printed "own 0 caught, 47 survived": `npm test`
  had failed twice on the untouched copy (the machine's load average was above 40) and was left out, and the row
  loop scored a left-out suite as "survived". `mutate.py` now says "not measured" and keeps the reason; the own-suite
  column above is a second run at a load of 22.
- Evidence: `evidence/baselines/`.

### The audit of what sessions read (2026-11-20 21:20)

The run record of `p1e2-ticket-assignment` carries one held-out mark, `skill-craft`, in its test session. I read the
event: a `ps` listing whose output showed another session's ShipLoop runs by path. The session read no file of this
repository and none of the held-out graders; no session in any run used `pkill` or `killall`. The cell stays
counted. A clean scan remains "no named exposure seen", not proof (section 7).

### Cells registered and not run

The two Sonnet 5.5 whole-loop cells (ticket assignment, chess) and P4 (a wrong test, by hand) were not run. The
owner asked for one runner ("you don't have to run both of them"), and the Sol cells already answer the readings a
second runner would repeat. P4's question (does the builder dispute a wrong test, and does the referee correct it)
was answered in passing by `filter-after-page` above, once.

## 11. Amendment 3, 2026-11-20 19:45: the apparatus hardened after a second outside review (before P2, P3 and the enriched ticket runs)

Sol 6.1 at max effort, read-only, 21 minutes, reviewed the apparatus for ways a result could be wrong without the
record showing it (`review/sol-apparatus-question.txt`, `review/sol-apparatus-answer.txt`; 16 findings). I traced each
in the code before acting. No number reported before this section depended on a fault it found, with two exceptions
stated here: the enriched arm's share of failing "clauses" had counted use cases in both parts of the fraction
(reported above by kind), and the first gradings of the ticket suites (apparatus note above).

Fixed, with the finding it answers:

| Finding | Fix |
|---|---|
| A session could edit `.git/ratchet-gate.json`, the file that said what is frozen (1) | The script keeps its own configuration and passes it to its gate; the file is rewritten before every script gate and only a session's own gate runs read it |
| A frozen test changed while the checks ran would pass uncounted (2) | The gate compares the frozen paths again after the commands; a change is put back, logged as `restored_during`, and everything is measured once more |
| An unmeasured reference scored every failing clause as a catch (3) | No defect is judged without a measured reference; an unmeasured control is "not measured"; the pool stays the registered size and unjudged defects are listed |
| The orders defects were named in comments of the planted files (4) | `grade.py variant` writes session-facing trees without the fixture's `// stand-in:` lines |
| A repair start was never graded, so a defect the held-out checks cannot see would count as repaired (5) | The start is graded (`frozen suite` snapshot), and `grade.py visible` lists which defects the held-out grader sees; P2 picks only from those |
| A timed-out closing look read as "nothing to add", and a clause's meaning could change unnoticed (6) | A delta whose session did not end, left no report or left an unreadable spec ends the run as `delta-failed`; `grown` compares whole item blocks |
| Held-out checks that run `node --test` saw the apparatus's own tests (7) | The graded copy has no `acceptance/` or `ratchet/` |
| The rerun rule missed `(rc None)` and reported only the first result (8) | That form is matched; both results are kept and `effective_passed` is what the report counts |
| Variants graded side by side shared a temporary folder; a command that did not end counted as a catch (9) | Each variant has its own; an unfinished command decides nothing (the defect is "not judged" unless another clause catches it) |
| A clause command that selected no test passed (10) | The tests packet requires each test's name to start with its item id, and the gate fails a command whose output never names its item (`named_checks` in run.json; runs before this amendment are graded without it). node:test reports a file as passing when a name pattern matches none of its tests, so a count of tests does not show it |
| The plan stage's loop was only observed (11) | The script refuses a plan without its five sections and asks again; each plan loop's status, iterations and trivial streak are recorded |
| A referee could delete a test and turn the gate green; a dispute could go unrecorded (12) | The manifest is checked after a ruling and the tests are put back if an item lost its entry; disputes are recorded before the gate's verdict is acted on |
| A copied suite lost file modes (13) | Suites are copied with `git archive`; a repair start records the source run and commit |
| Clause shares counted use cases (14) | `strength.json` reports clauses and use cases apart |
| Conduct forbade reading outside the work folder while the packet pointed at files outside it | The two folders (tools, loops) are named as the exceptions |

Not fixed, and why: a session with full disk access can still learn held-out material by a path no marker names (15;
the journal's limit in section 7 stands, and a clean scan is "no named exposure seen", not proof); the record does not
attribute a product change to the failing test or the delta clause that caused it (16; R3.3 will be read from the
stage commits' diffs by hand); a helper file outside the frozen paths that an acceptance test loads is not protected
(part of 1's table; no suite so far has one).

Registration changes: P2 selects defects only among those `grade.py visible` shows the held-out grader can see, and
a start counts as repaired only if a held-out check that failed at the start passes at the end. The enriched ticket
runs (`p1e2-ticket-*`) run amendments 1 to 3; the enriched orders run (`p1e2-stand-in-rules`) ran amendments 1 and 2,
before the naming rule, which does not touch the spec stage.

## 12. Amendment 4, 2026-11-20 22:15: a harder scenario, Grokbot-local (registered before any of its runs has a result)

Owner, 2026-11-20, sixth and seventh messages: "do we have a sufficiently complex enough scenario for this to be
addressing the test case? should we have a 'create a node based grokbot clone running on localhost' as a scenario to
help drive better comparisons?", "each of the tests should run in an isolated, clean git repo folder", and then "go
ahead and build the grokbot-local scenario".

Why: every case run so far is at its ceiling (all four whole-loop first builds passed every held-out check; one
acceptance clause failed naturally in four runs), so the pilot could price the loop and could not show whether
iterating on failed tests beats planning when a first pass falls short.

What it is (`docs/experiments/ratchet-pilot-20261120/scenarios/grokbot-local/`):

- `REQUEST.md`, the literal request. Its customer paragraphs are the owner's Grok chat brief (commit
  71fa298e44db73f6afa46217377ba0ea850de916, `test/shiploop_e2e/scenarios/grok-chat-outcome/BUILDER_PROMPT.md`, retired
  with the Salesforce cases in 2cd119d12) with Salesforce and xAI replaced by a Node.js app on localhost. A closing
  section names what a check can find: how a person continues as someone, and the accessible names of the main
  regions and controls, as the Roundtable case's requests do. 1,150 words, about ten feature areas.
- `fixture/`, the starting folder of every run: `provider/standin.js` (a deterministic, offline stand-in for the
  model, 15 rules, documented in `provider/README.md`; its replies reflect the bot's instructions, the memory, the
  conversation and the records it was handed, so a check can tell what the app assembled) and `records/` (seven
  synthetic records, three people, who may read which). Nothing else.
- `grokbot_accept.cjs`, the held-out yardstick: Playwright, finding everything by role and accessible name; it
  starts and stops `node server.js` itself, each mode on a free port with an empty data folder. 48 checks: setup and
  the secret (5), conversation, bots, memory, records and changes (27, with a restart), long tasks (8, with the page
  closed and with a restart), everyday use at 320, 390 and 1440 pixels and from the keyboard (6), and the delivery's
  own `npm test` (1). Every check is tried and recorded; one failing does not stop the others.
  (Corrected 2026-11-20 22:39: the file as registered has 49 checks, 29 of them in the second group; "48" and "27"
  were my miscount. No check was added or removed between this registration and the first grading. Section 14.)
- `BRIEF.md`, the proposal the owner said go to.

Arms, one run each on Codex `gpt-6.2-sol` at high, each in its own new Git repository in its own folder outside this
checkout:

| Arm | What runs |
|---|---|
| bare | one session given the request and the rules of conduct, nothing else (`ratchet.py run --bare`) |
| ShipLoop | this checkout's ShipLoop source (the fewest-steps rule of 67ac34ae2b996205ba6018ebbd7f78bee9d338dd; released as 2.4.0), through `test/shiploop_e2e/run.py --source checkout` with the harness's defaults, from a throwaway checkout that alone carries the case and its fixture |
| Ratchet | amendments 1 to 3, three cycles at most (`ratchet.py run`) |

Readings:

- R5.1 **the scenario is hard enough** if the bare arm fails at least 5 of the 48 checks (49: see the correction above). Fewer reads as another
  ceiling case.
- R5.2 **quality at the end**: checks passed by each arm's final product. An arm is ahead of another by 5 checks or
  more; within 4 reads as no difference shown.
- R5.3 **what Ratchet's cycles recover**: its checks passed at the first build and at the end of each cycle.
- R5.4 reported: whole-path minutes and output tokens of each arm.
- R5.5 reported: checks that pass at Ratchet's first build and fail at its end (the spec turning a working product
  into a failing one, section 10's due-times finding).

Calibration rule, fixed before any result: there is no hand-written reference, and the yardstick was written before
any build existed. It is first run on the bare arm's product. A check is corrected only where it contradicts the
request or the stand-in's documented behaviour, never to make a build pass; every correction is listed with its
reason; after calibration one version of the yardstick grades every arm, and an arm graded earlier is graded again.

Limits known before the runs: one run an arm; a yardstick calibrated on the arms it measures, which is weaker than
the ticket cases' calibration and is said with every result; no arm is given a browser, each may use what it finds on
the machine; the ShipLoop arm releases and reviews as ShipLoop does, the other two stop at a product; a long run is
started detached and a ShipLoop run that stops is resumed with the harness's own resume.

## 13. Registered 2026-11-20 22:32, before any judge has answered: an independent read of what the closing looks added

Question. The closing looks of the four finished whole-loop runs (chess, shared expenses, ticket assignment at high
and at medium) added 59 requirements (55 clauses, 4 use cases) and reported that the product did not keep to 23 of
them. Are these requirements that the request carries, or work the loop made for itself? R2.3 measures a part of this
by machine (does an added clause's test fail on a correct reference). It cannot say whether a clause that passes on
the reference is still a free choice, and three of the four runs have no reference to run. This read asks judges
about the requirement itself.

Method (`docs/experiments/ratchet-pilot-20261120/judge.py`). One packet of 42,327 characters (sha256
`e610bf5a27b2a551dbccbc90db06f7add1f0d38fd82a664b36fe0553ab2ea7df`): the three requests verbatim; for the ticket case
the existing product's `README.md`, `docs/api.md` and `docs/operations.md`, because that request changes an existing
product; then every added requirement with how it would be observed, in one fixed shuffled order (seed 20261120),
grouped by request. A judge does not see the run, the cycle, whether the product kept to the requirement, or what the
closing look wrote about it. Each item gets one label:

| Label | Meaning | Side |
|---|---|---|
| R, required | the request's words, their plain implication, or the existing product's documented behaviour require it | belongs |
| E, expected | not required, but a user would meet a real defect without it | belongs |
| C, choice | the request is silent and another behaviour would be as correct | does not |
| X, excess or wrong | scope the request does not ask for, or against the request | does not |

A judge unsure between two labels is told to take the one further down, so the read leans against "belongs".

Judges. The clauses were written by `gpt-6.2-sol`. Two judges come from other families: the latest Claude Opus and
the newest Grok, each asked once through the ask runners, with no tools, in an empty folder. A third answer from Sol
6.1, the author's family, is reported apart and decides nothing.

Readings (exploratory; section 6 registered no bar for them):

- J1: of the 59, how many both outside judges say belong, how many both say do not, and how many split them.
- J2: the same for the 23 the product did not keep to: a real gap found, against work the loop made for itself.
- J3: agreement between the two outside judges: the share on the same side, and Cohen's kappa on the side. Under 0.4
  the labels are too unsteady to read J1 and J2 as more than a direction.
- J4: J1 by cycle, to see whether later looks add more that does not belong.

Limits: models as judges, one answer each; a judge sees documents and not code; the two ticket-assignment runs can
add the same requirement twice, and it is then counted twice.

### Result (2026-11-20 22:55; each judge answered once and labelled all 59 items)

| Judge | Required | Expected | Choice | Excess or wrong | Belongs |
|---|---|---|---|---|---|
| Claude Opus 5.5, xhigh, no tools | 4 | 7 | 15 | 33 | 11 of 59 (19%) |
| Grok 4.7, xhigh, no tools | 11 | 13 | 11 | 24 | 24 of 59 (41%) |
| Sol 6.1, xhigh, read-only (the author's family; reported apart) | 6 | 26 | 25 | 2 | 32 of 59 (54%) |

The two outside judges, Opus and Grok:

- **J3, agreement.** The same side on 44 of 59 (75%), Cohen's kappa 0.42; the same label on 34. That is just above
  the 0.4 line, so J1 and J2 are read, as moderate agreement between two model judges.
- **J1, all 59.** Both say it belongs: 10 (17%). Both say it does not: 34 (58%). They split on 15 (25%).
- **J2, the 23 the product did not keep to.** Both say it belongs, a real gap found: 2 (9%). Both say it does not,
  work the loop made for itself: 16 (70%). They split on 5, all five about malformed UTF-8 in a name or a filter.
- The 36 the product already kept to: 8 belong, 18 do not, 10 split. A test for one of these pins what the product
  already did.
- **J4, by cycle.** Both-belongs is 5 of 29 in the first looks, 1 of 17 in the second and 4 of 13 in the third: no
  trend that counts this small can show. By case: chess 2 of 10, shared expenses 4 of 19, ticket assignment 4 of 30.

The two gaps both judges accept come from the third look of the high ticket-assignment run: after a save that
failed, assignment must go by the committed status (C-216) and the committed title (C-215). The sixteen both reject
include a data file reached through a symbolic link (two items), Unicode line breaks and text-direction overrides in
names and titles (four), two processes or a changed file under a running service (two), and what the documentation
should say about ids and size limits (two).

The author's family reads its own additions differently. Sol 6.1 says 32 of 59 belong and 2 are excess, where Opus
says 33 are excess and Grok 24. Of the 34 items both outside judges reject, Sol accepts 15. Its agreement with either
outside judge is kappa 0.2.

**F17 (interim: two model judges, one answer each, kappa 0.42).** Most of what a closing look adds is not the
request's. About one added requirement in six is accepted by both outside judges, and of the gaps the looks reported
in their own products, 2 of 23. Read with F14 and F15: after a first build that was already correct, the second and
third cycles of every run built and tested scope the loop had written for itself, and the one judge that finds that
scope reasonable comes from the model family that wrote it.

Evidence: `evidence/judge-closing-looks/` (the packet, the key, the three answers with each judge's served model, the
score).

## 14. Grokbot-local: the yardstick calibrated on the bare build, and R5.1 (2026-11-20 22:39)

Status: firm for what was measured (one build, one calibrated grading); the ShipLoop and Ratchet arms had no result
when this was written and the corrected yardstick was committed.

**The bare arm.** One Codex `gpt-6.2-sol` high session, given the request and the rules of conduct and nothing else,
in a new repository holding only the starting folder: 16.9 minutes, 47,308 output tokens (1,532,165 input, 1,458,176
of them cached). It left 2,471 lines in 12 files of its own (a 129-line `server.js`, three modules under `lib/`,
three files under `public/`, two test files) and no held-out name in its event stream.

**First grading, as registered: 43 of 49.** All five setup checks failed, and
`a-second-conversation-starts-empty-and-both-are-listed`. I read each by driving the build in a browser with two
throwaway probes (Playwright, a copy of the build, its own data folder).

| Failing checks | What the build does | What the yardstick assumed | Verdict |
|---|---|---|---|
| the five setup checks | Shows the people first. After `Continue as Maya`, a region named Setup is on the main screen with `Provider token` and `Save token`, and says what is needed. | That Setup is on the first screen and the people come after a token is saved. | Yardstick. The request says "The first screen offers a button named Continue as <name>" and that Setup is shown "when no provider token has been saved"; it does not put Setup first. |
| second conversation | At a person's pace (a probe with pauses): `New conversation` opens an empty conversation, both are listed, and the reply counts 1 message. At the yardstick's pace (the message written within milliseconds of the click): the message is dropped, nothing is sent and no error is shown. | Nothing about pace; it wrote at once. | Yardstick. The request states no such speed, and the same script already paused 300 ms after opening a bot. |

**Corrections (the calibration rule of section 12; each is in the file's header).**

1. Setup is looked for on the first screen and, when it is not there, after continuing as a person.
2. A good token counts as accepted when a first message then gets a reply (the first version waited for the people
   to appear after saving, which is the same assumption).
3. After a restart, Setup must be absent on the first screen and after continuing. This is stricter than before for
   an app that shows people first, where the first version passed without looking.
4. After `New conversation` the check waits until the conversation shows no messages, which is what it is named for,
   and then writes.
5. `send` pauses 300 ms before it writes, in every check. No failing check asked for this one; it is the same class
   as 4, and I applied it before any other arm had a result so that a later arm cannot fail for the driver's speed.

**After calibration: 49 of 49** on the bare build (one grading, 78 seconds, machine load average 22). The first
grading is kept beside it (`hidden-before-calibration.json`).

**R5.1, the scenario is hard enough: not met.** The bar was 5 failing checks; none fails. On this yardstick
Grokbot-local is another ceiling case for Sol 6.2 high: one 17-minute session with no plan, no separate tests and no
closing look passes every check, including work that continues with the page closed, a restart in the middle of a
task, a confirmation pressed twice across a reload, and two people who must not see each other's records.

What follows from it:

- R5.2 can now show a loss for the ShipLoop and Ratchet arms and cannot show a gain. Their cost (R5.4) and whether
  Ratchet's cycles break something that worked (R5.5) are what those two runs can still add.
- Seen outside the yardstick and not scored: the bare build drops a message written while `New conversation` is on
  its way to the server.
- The yardstick probes what the request names. It does not probe several sentences the request states in prose (that
  everything kept lives under `DATA_DIR`, that the stand-in is unchanged, a reload during a slow or failed reply, a
  proposal whose record changed before it was confirmed, deleting a saved instruction, the narrow window keeping the
  conversation in view). A second yardstick from those sentences is the next amendment, written before the other two
  arms end.

Evidence: `evidence/grokbot-local/` (the bare run's record, both gradings, the two probes and their output).

### A second round of calibration, found on the Ratchet arm's first build (2026-11-20 23:05; before the ShipLoop arm's grading had been read)

The Ratchet arm reached its first build 37.5 minutes into its run (spec 10.1, plan 6.7, build 20.7). Graded with
the yardstick as section 14 left it, that build scored **6 of 49**: the five setup checks and its own `npm test`
pass, and all 43 others fail from the first step, `continue-as-a-person`, a time-out waiting for the Message box.

Driven by hand at a person's pace (a probe: load the page, wait, press `Continue as Maya`), the same build shows its
main screen with the Message box, both navigations and all six regions, and no page error. The build draws the three
`Continue as` buttons after it has fetched the people. The yardstick's `signIn` asked whether the button existed at
the instant the page had loaded, found none, did not click, and waited for a Message box that could not come. The
bare build happened to draw the buttons sooner.

Corrections 6 and 7, in the headers of both files:

6. `signIn` waits until the first screen has drawn the `Continue as` button, or the Message box, before it decides
   whether to click.
7. After a restart, the check that Setup is absent waits half a second before it looks (the same instant-of-load
   fault, in the direction that lets a build pass).

No check of the second yardstick changed; it uses the same `signIn`.

Under the rule every arm is graded again with this final version: the bare build (49 of 49 and 28 of 28 before it),
the Ratchet first build, and the ShipLoop arm, whose first grading already runs on it. The earlier gradings are kept
beside the new ones (`hidden-before-calibration-6.json`).

What this costs the earlier claims: section 14 said one version would grade every arm after calibration, and it
took a second build to expose a fault of the same kind (the driver outrunning the page). The yardstick has now been
corrected three times for pace. That is the limit section 12 named, a yardstick calibrated on the arms it measures,
showing up in practice.

## 15. Amendment 5, 2026-11-20 22:50: a second, harder yardstick for Grokbot-local (registered before it has graded any build)

Why. Section 14: the first yardstick is passed whole by one unstructured session, so it can show a loss for the
other two arms and no gain. The owner's question was whether a scenario exists that is hard enough to compare the
approaches. The request has sentences the first yardstick never probes. This one probes them. It was written with
the bare build finished and graded on the first yardstick, and with the ShipLoop and Ratchet arms still running and
ungraded; I had read the bare build's behaviour only where section 14 says (setup order, a second conversation).

What (`scenarios/grokbot-local/grokbot_accept2.cjs`; `grade.py second RUN`, `grade.py tree grokbot2 WORK COMMIT OUT`).
28 checks, each carrying the sentence it comes from and a tier. **Stated** (23): the sentence says it. **Implied**
(5): the check is my reading of a sentence. The tiers are counted apart and only the stated tier has a bar.

| Group | Checks (implied ones marked) |
|---|---|
| What is delivered | the stand-in's two files are byte for byte the starting ones; `package.json` names no dependency and no `node_modules` is delivered |
| Returning to the right discussion | opening an earlier conversation shows it and answers from it; exactly one conversation is marked current and the mark moves; each bot comes back to its own discussion |
| Awkward moments in a conversation | a reload during a slow reply loses neither the message nor the reply and doubles neither; a failed reply can still be retried after a reload |
| What was saved | Edit puts an instruction back into its two textboxes and saving keeps one entry; an instruction used by one bot is not another bot's; an instruction can be deleted and stays deleted after a reload; the same three for a saved task; after Enter the next message can be typed with no click (implied) |
| Three people | another person is shown neither my saved instruction nor my bot's memory; the third person is answered only from the records that list them; coming back as myself I find my instruction, my bot's memory and my conversation |
| Changes at awkward moments | Confirm changes works from the keyboard; the same proposal confirmed in two windows of one person creates one order; a proposal whose record another person has changed meanwhile is not applied over their change unless the proposal showed their value (implied) |
| Long tasks | a completed task offers no Cancel task; a steered eight-step task shows nine finished steps; cancelling one of two tasks leaves the other to finish all eight (implied); a cancelled task is still Cancelled, with no further step, after a restart (implied); Since you were away names a task that finished, one that failed and one still running while the page was closed |
| The wide and the narrow window | at 1440 pixels every region, navigation, button and textbox the request names for the main screen is visible with a memory and a task present; at 320 by 640, after a reply, the Message box is wholly in the window and the newest reply at least partly; a 240-letter unbroken word does not widen the page at 320 (implied) |
| Where things are kept | after all of the above, no file of the app's own folder was added, changed or removed (the data folder is elsewhere) |

Readings:

- R6.1 **headroom exists** if the bare build, after calibration, fails at least 3 of the 23 stated checks. Fewer
  reads as the ceiling again, on a harder yardstick.
- R6.2 **quality at the end**, stated checks: an arm is ahead of another by 3 or more; within 2 reads as no
  difference shown. Implied checks are reported beside it and decide nothing.
- R6.3 reported: for the Ratchet arm, stated checks passed at the first build and at the end of each cycle, and for
  each check its first build fails, whether its own specification and acceptance tests named that behaviour.
- R6.4 reported: any check an arm fails on this yardstick and whether the same arm's own tests cover it.

Calibration: the rule of section 12, on the bare build. A check is corrected only where it contradicts the request
or the two README files, never to make a build pass; every correction is listed; then one version grades every arm.

Limits: written by me in one sitting, with one build in existence; several checks share a mode's state, so one
failure can cause the next in the same group (each check's note says what it saw); 5 of the 28 are my reading and
are kept out of the bar for that reason.

## 16. Amendment 6, 2026-11-20 22:58: where does a bare first pass start to fall short? Two more bare arms (registered before either runs)

Why. Section 14, and the second yardstick's first reading (28 of 28 as registered; its section follows once the
yardstick itself has been shown able to fail), say one Sol 6.2 high session passes everything I can check. Comparing
ways of working needs a first pass that falls short. The owner named two runners ("Sonnet High or Sol 6.2 on high").
Before hours of ShipLoop and Ratchet go to another runner, one bare session on each of two settings says whether
headroom exists there:

- `g-bare-sonnet-high`: Claude `claude-sonnet-5-5` at high, the owner's other named runner.
- `g-bare-sol-low`: Codex `gpt-6.2-sol` at low, the same model with less effort.

Each is `ratchet.py run --case grokbot-local --bare`: the request and the rules of conduct, a new repository holding
only the starting folder, one session, 90 minutes at most. Then both yardsticks as calibrated.

Readings:

- R7.1, for each arm: checks failed on the first yardstick (of 49) and stated checks failed on the second (of 23).
  Headroom is the bars already registered: at least 5 on the first (R5.1) or at least 3 stated on the second (R6.1).
- R7.2, reported: minutes and output tokens.

What a result decides: if an arm shows headroom, ShipLoop and Ratchet on that runner are the comparison worth
running; that is hours of runs and the owner's call, so it is not launched here. If neither shows headroom, the
scenario as written is one-shot work for the current models and a harder scenario is a different product, not a
harder yardstick.

Limits: one session each; both yardsticks were calibrated on a Sol 6.2 high build, so a different design may meet
an assumption no build has exposed yet. A failure is read by hand under section 12's rule before it is counted.

## 17. Grokbot-local: the second yardstick proven and calibrated, and the arms compared (2026-11-21 00:10)

Status: firm for what was measured (one run an arm; every arm graded from scratch on one committed version of both
yardsticks, d8a7f1e6e12c70e4a7b2230ae483b4c46b24d975). The Ratchet arm was still running; its row is its first build and its first green gate.

### The second yardstick can fail

As registered it passed the bare build 28 of 28 on its first run (22:51), which showed nothing. A helper session
then planted 28 single defects, one aimed at each check, into copies of the bare build and ran the yardstick on every
copy (`evidence/grokbot-local/teeth/`: the summary, the 29 diffs). The untouched copy passed 28 of 28. 26 defects
failed the check they were aimed at. Two did not, and each showed a blind spot of its check:

- an instruction spread to every existing bot went unseen, because the check made its second bot after using the
  instruction;
- a 240-letter word overflowed inside the conversation pane (3,905 pixels in a 320-pixel pane) while the page stayed
  320 wide, which is all the check measured.

Both checks were made stricter (correction D). On the final version the seven planted copies whose checks had
changed are each caught and the untouched copy passes 28 of 28; with the 21 unchanged checks of the first run, every
check has a planted defect that fails it.

### Six rounds of calibration, and what each build exposed

| Corrections | Exposed by | What the driver had assumed | What the request says |
|---|---|---|---|
| 1 to 3 | bare, Sol high | Setup is shown before a person is chosen | the first screen offers the people; Setup is shown while no token is saved |
| 4, 5 | bare, Sol high | a message can be written within milliseconds of a click | nothing about speed |
| 6, 7, A | Ratchet, first build | the people are on the page at the instant it has loaded | nothing about when they are drawn |
| 8, C | Ratchet, first build | the account of what happened can be read seconds after coming back | "When I come back" |
| B | ShipLoop | several tasks run in one conversation | nothing; the stand-in's README says "their running task in this conversation" |
| 9 | bare, Sonnet high | no step finishes after a cancel | "what can still be stopped and what has already happened" |
| 10, E | ShipLoop | every article in the conversation is a message | messages are articles named "Message from"; Tasks is a region, placed anywhere |
| 11, F | Ratchet, first build | coming back means a new browser | "When I come back" |
| D | planted defects | (two checks too weak, above) | |

First gradings before each correction, for the record: bare 43 of 49; Ratchet first build 6 of 49, then 48; ShipLoop
26 of 28, then 25; Sonnet 47 of 49. Of all the failing checks I chased across five builds, one was the build's.

**F18 (firm).** A held-out browser yardstick written without a build to run it on is not yet an instrument. It
took five builds of four different designs to remove what the driver assumed, and no correction touched a sentence
of the request. The uncalibrated numbers would have ranked the arms wrongly in both directions.

### The arms on the final yardsticks

| Arm (one run each) | Minutes | Output tokens | Lines of its own | First yardstick (49) | Second: stated (23) | Second: implied (5) |
|---|---|---|---|---|---|---|
| bare, Sol 6.2 low | 6.8 | 19,149 | 1,485 | 49 | 23 | 5 |
| bare, Sol 6.2 high | 16.9 | 47,308 | 2,471 | 49 | 23 | 5 |
| bare, Sonnet 5.5 high | 24.1 | 179,893 | 5,126 | 48 | 23 | 4 |
| ShipLoop, Sol 6.2 high | 39.5 | 85,154 | 2,415 | 49 | 23 | 5 |
| Ratchet, Sol 6.2 high: first build, 37.5 minutes in | | | 2,960 | 49 | 23 | 5 |
| Ratchet: first full gate (291 of 291 of its own items), 71.5 minutes in | | | | 49 | 23 | 5 |
| Ratchet: the end, three cycles | 207.7 | 392,253 | 3,030 of source (2,271 at the first build) | 49 | 23 | 5 |

The only checks that fail on the final version are the Sonnet build's. At 320 pixels its page is 332 pixels wide: the top bar,
the layout and the conversation all measure 332. The first yardstick counts that; the second yardstick's long-word
check (implied tier) fails on the same width.

Registered readings:

- **R5.1, the scenario is hard enough: not met** (section 14 stands on the final version: the bare build fails none).
- **R6.1, headroom on the harder yardstick: not met.** The bare build fails none of the 23 stated checks; the bar was 3.
- **R7.1, headroom on another runner: none.** Sol 6.2 low fails no check on either; Sonnet 5.5 high fails 1 of 49 and none of the 23 stated (1 of the 5 implied). The
  bars were 5 on the first yardstick or 3 stated on the second.
- **R5.2 and R6.2, quality at the end: no difference shown** between the bare arm, the ShipLoop arm and the Ratchet
  arm on the same model and effort (49 and 23 each; the Ratchet arm's end was added at 02:00, below).
- **R5.3 and R6.3:** the Ratchet arm's first build already passes 49 of 49 and 23 of 23, so its cycles have nothing on these
  yardsticks to recover.
- **R5.4, cost:** on the same model and effort, the bare session took 16.9 minutes, ShipLoop 39.5 (2.3 times; it also
  released and reviewed) and Ratchet 37.5 to its first build and 71.5 to its first full gate, with two cycles to go.
- **R5.5** (a check passing at Ratchet's first build and failing later): none, at any of its eight graded stages.

**F19 (firm for these models and this request).** Grokbot-local is one-session work. A single Sol 6.2 session at low
effort delivers it in 6.8 minutes and passes everything both yardsticks check. Neither a plan with steps nor a loop
of tests and closing looks changed what the yardsticks see; they changed the time. A scenario that separates ways
of working is a different kind of product, not a stricter yardstick for this one.

Seen and not scored: the bare Sol high build drops a message written while New conversation is on its way; the
ShipLoop build answers a second task request in one conversation with the stand-in's "I'll work on it" followed by
its own "A task is already running in this conversation"; the Sonnet build is twice the size of the others and
includes browser scripts it wrote to check itself.

Evidence: `evidence/grokbot-local/` (`final-grading.json` holds every arm's result on the final version with each
failing check's note; `bare/`, `bare-low/`, `bare-sonnet/`, `shiploop/`, `ratchet/` hold the runs' records, the
earlier gradings and the probes; `teeth/` the planted defects).

### What each build's own tests are worth (exploratory; no model call; 2026-11-21 01:13)

Not registered: a measure taken on the finished builds, as section 10's baselines were. `mutate.py` seeds the E2E
harness's simple faults (a flipped comparison, a moved bound, flipped logic, a flipped boolean, flipped arithmetic)
one at a time on lines the build wrote, 60 a build taken in turn across its files, and runs the build's own
`npm test`. A fault is caught when the suite fails twice on it.

| Build | Fault sites in its own code | Caught of 60 | In server code | In page code (`public/`) |
|---|---|---|---|---|
| one session, Sol 6.2 low | 114 | 31 (52%) | 31 of 57 | 0 of 3 |
| one session, Sol 6.2 high | 324 | 24 (40%) | 24 of 45 | 0 of 15 |
| one session, Sonnet 5.5 high | 462 | 31 of the 54 that ended (57%) | 31 of 56 | 0 of 4 |
| ShipLoop, Sol 6.2 high | 359 | 37 (62%) | 33 of 50 | 4 of 10 |
| Ratchet, Sol 6.2 high, first build (the builder's own tests) | 595 | 23 of the 58 that ended (40%) | 23 of 52 | 0 of 8 |

**F22 (interim: one run a build, 60 faults each, a simple fault catalog).** This is the one measured thing in the
pilot that ShipLoop's extra time buys. On the same model and effort its tests catch 37 of 60 seeded faults where the
bare session's catch 24, and it is the only build whose tests reach the page's code at all. ShipLoop's run shows why:
its own check of tests against seeded faults refused the test stage twice, with 2 of 8 and then 6 of 8 seeded faults
surviving, until they were dealt with (`evidence/grokbot-local/shiploop/metrics-compact.json`: `gate_counts`,
`shiploop_failures`). The Ratchet builder's own tests
are no stronger than a bare session's (23 of 58), although its build prompt lists testing among its duties: a duty
stated in a prompt did not do what a script-run check did. Ratchet's separately written acceptance suite (291
browser-backed items) is not in this table; running it once a fault would take hours.

Read with F19: the builds behave alike on both yardsticks, and differ in the tests they leave behind.

Evidence: `evidence/grokbot-local/seeded-faults/` (each build's 60 faults with the verdict on each, and `run-log.txt`).

### The Ratchet arm at its end (2026-11-21 02:00)

The arm stopped at the three-cycle limit after 207.7 minutes, 14 sessions and 392,253 output tokens, its final gate
passing (280 clauses and 29 use cases). No held-out name appears in its event streams, no path was put back, no
frozen file was changed outside its stage.

| Stage (minutes in) | Its own gate | First yardstick | Second: stated / implied |
|---|---|---|---|
| first build (37.5) | | 49 of 49 | 23 / 5 |
| after the first test pass (71.5) | 291 of 291 | 49 | 23 / 5 |
| second build (100.3) | 291 of 291 | 49 | 23 / 5 |
| after the second test pass and one fix (135.3) | 297 of 298, then 298 of 298 | 49 | 23 / 5 |
| third build (170.5) | 298 of 298 | 49 | 23 / 5 |
| after the third test pass (191.7) | 304 of 304 | 49 | 23 / 5 |
| the end (207.7) | 309 of 309 | 49 | 23 / 5 |

Minutes by stage: enrichment 10.1, plans 20.7, builds 50.5, test passes 60.1, closing looks 16.7, the fix 7.4, gates
and script 42.2 (each gate runs about 300 browser-backed tests).

- **R5.2, R5.3, R5.5, R6.3.** The arm ends where its first build stood: every check of both yardsticks, at every
  stage. Its cycles recovered nothing, because nothing was missing, and broke nothing.
- **R5.4, cost, complete.** On one model and effort: a bare session 16.9 minutes and 47,308 output tokens; ShipLoop
  39.5 and 85,154; Ratchet 207.7 and 392,253. Ratchet took 12.3 times the bare session's time and 5.3 times
  ShipLoop's for the same result on both yardsticks.
- **What the cycles did.** The three closing looks added 6, 5 and 5 requirements and reported the product short of
  13 of them (3, 5 and 5). One closing-look clause (C-265, reopening a discussion restores the reading place) failed
  its own new test in cycle 2 and one fix session repaired it: the second naturally failing acceptance item in
  seven whole loops. The product's source grew from 2,271 lines at the first build by 932 added and 173 removed. The
  last look was still finding things: two servers sharing one browser profile, pasted input clipped at a field's
  limit without a word, a steer sent while two tasks ran, a missing field shown as "null", focus lost when a
  finished task's entry disappears. These sixteen additions were not put to the judges of section 13.
- **Like every other whole loop, it did not stop by itself.**

Evidence: `evidence/grokbot-local/ratchet/` (run.json, gates.json, the three closing looks, the fix note, the
gradings at every stage in `final-grading.json` and `end-grading-log.txt`, summary.json).

## 18. An apparatus fault of mine that loaded the machine for four hours (found 2026-11-21 02:02)

What happened. At 22:03:42 I stopped the first seeded-fault run (`mutate.py`, section 10) by its process id, to
lower a load average of 45. The script starts each command in a session of its own. Two commands were in flight,
each a `node --test` run on a seeded fault that makes a loop spin; they were not stopped with the script. Ten test
worker processes then ran at about 100% of a processor each from about 22:00 until I found them at 02:02 while
sweeping for leftovers after the last run. I stopped them by process id after checking each one's working folder
(the script's own scratch folder). The load average went from 22 to 12 at once and to 3 once the pilot's last jobs
had ended. So about half of the load I had set out to reduce was my own, for four hours.

What it touched. The machine has 18 processors and was shared with another session's runs all evening.

| Ran before the strays (not touched) | Ran with the strays on the machine |
|---|---|
| P1; P2 on orders; the chess, shared-expenses and medium ticket-assignment whole loops (ended 21:13, 21:47, 21:33) and with them the matched time reading R3.4; nearly all of the four ticket repair starts | the last 12 minutes of the high ticket-assignment loop; the due-times loop (21:43 to 00:13); every Grokbot-local arm, grading, probe and planted-defect run; the seeded-fault measures; the other session's work |

- **Times in the right-hand column are inflated by an amount I cannot measure** for their local parts (test runs,
  gates over hundreds of tests, browsers). Model latency is not affected. The Grokbot arms all ran inside the window
  and share the load, so their ratios (2.3 and 12.3 times) are less exposed than their minutes.
- **No pass or fail in this journal rests on it.** Every failing check counted here was read by hand with a probe;
  the failures that turned out to be time-outs were the driver's assumptions, shown at a person's pace under the
  same load. One earlier guess is now explained: the `npm test` that failed twice on an untouched copy at 22:05
  ("the machine's load average was above 40") was running beside these strays.
- **The other session paid for it too.** Its runs had about ten fewer processors for four hours. The owner is told.

Fix. `mutate.py` now handles being stopped: it starts nothing more, kills every command group it still has, and
exits at once. Checked on a toy project whose seeded fault spins for ever: before the fix, stopping the script left
it and two test processes running; after it, none. What I do differently: after stopping any script of mine, list
what still runs from its scratch folder and stop it by process id; and when the machine looks loaded, look for my
own strays first.

## 19. After the pilot ended (2026-11-21 03:15): the merge, the audit completed, and two things from another session

**Merged.** The owner answered "Yes" to merging and pushing. The branch was merged, not rebased (its messages cite
each other's hashes), in a temporary checkout cut from origin's `main`, so that only the pilot's 22 commits were
published and another session's 16 unpushed commits on the local `main` were left alone. Before the push: the quick
tier pinned to the base (13 suites, 160.9 s, pass), then `scripts/release-push.py` with the release-boundary,
test-groups and marketplace-package checks. No release: nothing under `skills/` changed.

**The audit, completed (my omission corrected).** Section 10's audit note examined one held-out mark. The run
records hold five. I read each event:

| Run, session | Mark | What it was |
|---|---|---|
| `p1e2-ticket-assignment`, tests | `skill-craft` | a process listing showing another session's ShipLoop runs (examined on 2026-11-20) |
| `p3-ticket-assignment-sol-high`, tests | `skill-craft` | the same kind of process listing |
| `p3-ticket-assignment-sol-high`, third closing look | `shiploop_e2e`, `skill-craft` | a process listing that showed my own `mutate.py` command line, which names the E2E fixture folder |
| `p3-ticket-assignment-sol-medium`, tests | `skill-craft` | a `PATH` value containing `skill-craft-e2e/python` |
| `p3-ticket-due-times-sol-high`, first build | `skill-craft` | a process listing showing another session's ShipLoop run of the same request |

No session ran a command that names a path of this repository or a held-out file, so by section 6's rule every cell
stays counted. Two of the five exist because my own analysis job ran beside a live run and showed up in its process
listing: one more reason not to run analysis beside live runs.

**Codex shows user-level skills to every session (reported by the session "Spec elaboration prompt for Shiploop",
its journal `docs/spec-elaboration-journal.md`, section 7; not reproduced by me).** Codex 0.171.0 lists every skill
under the account's real home to a session whatever `HOME` and `CODEX_HOME` say, the E2E harness's own isolation
included. Every pilot run but the Sonnet one ran on Codex, so each of those sessions was shown the account's skills,
ShipLoop among them: the "bare" arm was bare of instructions, not of available skills. None was opened: across all
769 session event files of the pilot, the only mention of a user-level skill path is the process listing in the
table's first row, and that session's own read-only search of the run folders found the same. This is a limit to
read with section 7: the evidence that no skill was used is the event streams, not isolation.

**A result about this pilot's enrichment text, as received and not verified by me** (same session, sent at the
owner's word; its folder `docs/experiments/spec-elaboration-20261120/`, journal sections 11, 12, 14 and 16).

- This pilot's `SPEC_PACKET` (as of e63747a3d53b342f3ddf13005ca21063806a6856, its repository-reading step removed)
  was that experiment's control: one-sentence requests, no repository, the specification graded against 89 held-out
  nuances by a calibrated judge. Adding five things to think through before writing, with the specification still
  written once, raised what it covered from 40 to 64 of 89 on Sonnet high and from 29 to 62 on Sol 6.2 medium.
- An iterating form of the same additions showed no gain over the one-pass form and took about twice the minutes and
  tokens.
- ShipLoop's released spec stage already reaches 80 to 87 of the 89, and the additions were not shown to help it.
- Its own cautions: the checklist and the additions share an author; "covered" rewards deciding; a strict auditor's
  count of clauses beyond the request rose on Sol (38 to 48); nothing there was measured through a built product.

How I read it against this pilot, as my reading:

- It is a limit on this pilot's findings about enrichment (R1.3, F10, F20). The pilot tested one enrichment text, and
  on that measure the text is a weak specification writer next to ShipLoop's released stage (29 to 40 of 89 against
  80 to 87). What I reported as the cost of enrichment is the cost of this text.
- It does not reverse them. Its measure rewards a specification for deciding more, and what this pilot measured
  through built products is that decided clauses are where correct products were rejected (F10) and where one was
  made to fail (F20). More coverage on a checklist is not yet shown to make a better product.
- Its second bullet agrees with this pilot from another side: going round again added cost and not substance.

**Five logs that were cited and not committed (found 03:16 while removing the worktree).** The repository ignores
`*.log`. Five logs I had copied into the evidence folders were therefore never in a commit, although commit messages
and two evidence lines of this journal name them. They are now saved as text files: `baselines/mutate-ratchet-log.txt`,
`grokbot-local/bare/run-and-grading-log.txt`, `grokbot-local/final-grading-log.txt`,
`grokbot-local/ratchet/end-grading-log.txt` and `grokbot-local/seeded-faults/run-log.txt`. Every number they hold is
also in a committed JSON file beside them.

**If this is continued: the arm nobody has run.** The owner's first question was whether ShipLoop can be contracted
to one build pass with the stages' duties written into the prompt. This pilot ran a bare session (no duties) and a
loop (duties named in the build prompt, plus enrichment, a plan, separate tests and closing looks). F22 says a duty
named in a prompt did not do what a script-run check did. The comparison that would answer the question has three
arms on the same cases, model and effort: a bare session; one session with the duties stated as outcomes and their
script-run checks kept (syntax and lint, a test for each stated requirement, the suite green, the session's own
tests checked against seeded faults in the lines it wrote, a short document, clean commits) and nothing else; and
ShipLoop. Readings: held-out checks, the share of 60 seeded faults the delivery's own tests catch, minutes and
output tokens. The harness for it is here: `ratchet.py run --bare` is the first arm, `grade.py`, `mutate.py` and
`analyze.py` take the three readings, and section 17 is the yardstick lesson to keep. Not started; the owner's call.

## 20. Amendment 7, 2026-11-21 03:22: the other session's lens form as the enrichment text, measured through built products (registered before any run)

Owner, 2026-11-21: "We should pick up the elaboration message from the other chat about a new elaboration of a spec
prompt." My reading, told to the owner before starting: take the one-pass lens form that the session "Spec
elaboration prompt for Shiploop" measured (section 19; its journal `docs/spec-elaboration-journal.md`, sections 11 to
16) into this pilot's enrich stage, and measure it with this pilot's instruments.

Why it is worth a run. That experiment found the lens form covers far more of a held-out checklist than this
pilot's enrichment text (64 against 43 of 89 on Sonnet high, 62 against 29 on Sol 6.2 medium), and its own review
said what its instrument cannot: whether deciding more is right. This pilot's instruments can say that for three
cases, because they run the tests a specification leads to against products known to be correct and products known
to be wrong. The pilot's findings about enrichment (F10, F20, R1.1, R1.3) were made with one text, and section 19
recorded that as a limit.

What changes. `ratchet.py` gains `SPEC_PACKET_LENSES` and `--enrich lenses` (default `single`, the pilot's own
text; `run.json` records which). The lens text is `docs/experiments/spec-elaboration-20261120/arms/L-lenses-once.md`
set into this stage: this stage's frame and file path, its repository-reading step kept as the first thing to do,
and its `existing` source kind kept (that experiment's cases had no repository). Nothing else differs
(`evidence/lens-enrichment/port-against-L-lenses-once.diff`). The plan, build, tests, fix and closing-look packets
are unchanged, and so are the gate and the graders.

Runs, each Codex `gpt-6.2-sol` at high (the runner of every cell they are compared with), one new Git repository
each, outside the checkout:

| Cell | What runs | Compared with |
|---|---|---|
| `p1L-stand-in-rules`, `p1L-ticket-assignment`, `p1L-ticket-due-times` | enrich with the lens text, plan, the correct reference laid in as the build, heavy test pass, stop; then `grade.py strength` | `p1e2-*` of 2026-11-20 (section 10, "P1, enriched form") |
| `p3L-ticket-due-times-a`, `-b` | enrich with the lens text, plan, build, heavy test pass, stop; then the held-out checks at the first build | `p3-ticket-due-times-sol-high` (3 of 8 at its first build; the reference passes 7) and F20 |

Readings:

- **R8.1, the reading of the due-times request.** The pilot's text read "Due times are switched on in production
  only once the data file holds them" as an operator's preparation step and a service that refuses to start, in two
  of two specifications. The lens form *avoids the misreading* if both `p3L` first builds pass the five held-out
  checks that failed (`cli`, `migrate`, `restart`, `rollback`, `switch`); it *does not* if both fail them; one of
  each is not settled. Each specification is also read by hand for the preparation step and the refusal.
- **R8.2, clauses that reject a correct product.** Pooled over the three `p1L` cells, the share of clauses that
  fail on the harness's correct reference. With the pilot's text it was 59 of 499 (11.8%). *Better* at or under
  7.9% (a third lower), *worse* at or over 15.7% (a third higher), otherwise no difference shown. Reported beside
  it: use cases failing on the reference (16 of 44 before), and items the second correct ticket-assignment
  delivery fails beyond the reference (17 before).
- **R8.3, strength.** Calibrated defects caught of 37 (37 before). *Kept* at 35 or more.
- **R8.4, reported.** Clauses and use cases written, minutes of the enrich session and of the cell, output tokens.

Limits known before the runs: one run a cell on both sides (two for R8.1), and no measure of this pilot's own
run-to-run spread, so the thresholds are set wide on purpose; the comparison cells ran on 2026-11-20 between 19:23
and 20:33, before the stray processes of section 18, and these run on a quieter machine, so minutes are compared
loosely; Codex still shows the account's skills to every session (section 19), the same on both sides; the gradings
are run after all five runs have ended, not beside them.

### Result (2026-11-21 04:45; five runs, graded one after another once all had ended)

Status: firm for what was run (one run a cell; two for R8.1), read against bars registered before the runs.

**Test strength, lens text against the pilot's own (`p1L-*` against `p1e2-*`).**

| Case, text | Clauses / use cases written | Clauses failing on the correct reference | Use cases failing on it | Second correct delivery, beyond the reference | Defects caught | Minutes (of which enrich) | Output tokens |
|---|---|---|---|---|---|---|---|
| orders, lens | 82 / 8 | 9 (11.0%) | 1 | none exists | 4 of 4 | 23.7 (5.0) | 61,805 |
| orders, pilot's | 69 / 12 | 9 (13.0%) | 3 | none exists | 4 of 4 | 18.8 (6.1) | 49,042 |
| ticket assignment, lens | 153 / 11 | 13 (8.5%) | 3 | 15 (11 clauses, 4 use cases) | 26 of 27 | 38.0 (7.0) | 96,512 |
| ticket assignment, pilot's | 192 / 17 | 15 (7.8%) | 5 | 17 (14 clauses, 3 use cases) | 27 of 27 | 46.7 (13.5) | 94,976 |
| ticket due times, lens | 191 / 12 | 25 (13.1%) | 7 | none exists | 6 of 6 | 44.2 (8.0) | 112,503 |
| ticket due times, pilot's | 238 / 15 | 35 (14.7%) | 8 | none exists | 6 of 6 | 46.7 (10.1) | 112,205 |
| **pooled, lens** | **426 / 31** | **47 (11.0%)** | 11 of 31 | | **36 of 37** | 105.9 | 270,820 |
| **pooled, pilot's** | **499 / 44** | **59 (11.8%)** | 16 of 44 | | **37 of 37** | 112.2 | 256,223 |

- **R8.2, clauses that reject a correct product: no difference shown.** 11.0% against 11.8%; the bars were 7.9% and
  15.7%. The second correct ticket-assignment delivery fails 15 further items where it failed 17.
- **R8.3, strength: kept.** 36 of 37 (the bar was 35). The one missed is `cli-no-assignee` on ticket assignment.
- **R8.4, size and cost.** 15% fewer clauses and 30% fewer use cases than the pilot's text, written in 5 to 8 minutes
  where the pilot's text took 6 to 14. Whole cells: 6% less time, 6% more output tokens. The size runs the other way
  from that experiment's own count (372 clauses against 225 on Sol), whose cases had no repository: on the two
  ticket cases 77 of the pilot text's 86 extra clauses were `existing` ones (134 and 158 against 104 and 111).
  *Corrected 2026-11-21 05:00:* by clauses it is 78 of 86 (132 and 157 against 101 and 110); the figures first
  written counted use cases too (the count by Source, below).

**The due-times loop, twice, with the lens text (`p3L-ticket-due-times-a`, `-b`).**

| Run | Specification | Its own gate after the test pass | Held-out checks at the first build | Minutes to that gate |
|---|---|---|---|---|
| a | 173 clauses, 11 use cases | 184 of 184 | 3 of 8: `cli`, `migrate`, `restart`, `rollback`, `switch` fail | 57.8 |
| b | 199 clauses, 16 use cases | 215 of 215 | 2 of 8: the same five, and `suite` | 61.9 |
| the pilot's text (section 10) | 301 items at its first gate | 301 of 301 | 3 of 8: the same five | 57.2 |

- **R8.1, the reading of the due-times request: the lens form does not avoid it.** Both first builds fail the five
  checks, each with "cannot start: ... tickets[0]" on a file without due times, and both gates are fully green.
- **It is a choice the specification makes, and says so.** Both specifications wrote the refusal as a clause of its
  own with `Source: choice`: "Enabled startup refuses a persisted ticket collection with an unassigned deadline ...
  fail before serving when an operator enables the feature before completing preparation" (a, C-58), and "Enabled
  persistent startup refuses an existing file with missing due ... make the production readiness order enforceable
  and avoid automatic startup backfill" (b, C-67). The third lens specification of the same request, in the
  test-strength cell, chose the other way: "Startup prepares unassigned file-backed tickets before serving"
  (C-48, also a choice). Over both texts, four of five specifications of this request chose the refusal
  (`evidence/lens-enrichment/due-times-reading.txt`).
- Loop b's `suite` failure is the grader's, not the build's: its own tests pass in its repository (130 of 130) and
  one fails in the graded copy, which has no Git history, because it fetches release 1.4.0 with `git archive`.

**F23 (firm at this size).** On this pilot's instruments the lens form changes how much a specification says and
not how sound it is. It is shorter on the cases with a repository, costs about the same, loses nothing in test
strength that these cases can show, and the same one clause in nine rejects a correct product. Its large gain on
the other experiment's checklist does not appear as a gain in anything a built product shows here.

> **Sharpened 2026-11-21 05:00** (the count by Source, below; F25): "one clause in nine" is a pooled figure that
> clauses restating existing behaviour dilute. Of the clauses about the change it is one in five with the lens text
> against one in four, lower in all three cases and still inside R8.2's bar, so "no difference shown" stands.

**F24 (firm; five specifications of one request).** The due-times failure is not a gap in elaboration that a better
elaboration closes. The specification sees the question, decides it, and labels the decision a choice; four times
in five it decides against what the customer meant, and the tests then hold the product to it. A text that tells
the writer to decide where the request is silent will keep producing this. What has not been tried is a text that
tells the writer to leave such a point undecided and mark it: that is the reworded lens text the other session has
drafted (`docs/experiments/spec-elaboration-20261120/arms/R-lenses-reworded.md`, an `Open:` line under a clause).
It is prepared here as a third enrichment text and has not been registered or run; whether it runs is the owner's
decision.

Evidence: `evidence/lens-enrichment/` (each run's record; the three graded suites; the two loops' held-out results;
`summary.json`; `grading-log.txt`; the reading clauses; the port diff).

### After the result: where the rejecting clauses come from, and a correction received (2026-11-21 05:00)

Status: the counts are firm for these six runs and are a reading made after the result, not a registered one, so
R8.1 to R8.4 stand as read above. The operator reading is exploratory: one reader, this session, not blind.

**Received.** The session "Spec elaboration" recorded this section's result (its journal, section 21) and sent three
facts at 04:50. (1) Its own journal had said the reworded text "still names the operator's work"; that was wrong and
is marked superseded there. Checked here against `ratchet.py`: the lens text that ran carries the line without a
condition ("the operator's work (start, stop, configure, observe, recover, carry on with data that already exists,
go back to the version before)"); the reworded text carries "Where running it or recovering from it is part of what
was asked, state how the person who runs it observes it, stops it or recovers it, using the controls that already
exist"; and the pilot's own text carries it without a condition too ("What an operator does: start, restart,
configure, carry on with the data that exists today, go back to the version before"). So every specification this
pilot has measured was written under an unconditional operator line. Nothing in this journal had repeated the
superseded sentence. (2) Read item by item, the lens arms' gain on that experiment's operator items was an
operator-controls requirement added to specifications written without a repository, and two outside sorters labelled
four of its 89 items, all of them operator controls, capability nobody asked for; here such requirements would be
among the clauses that fail on a correct product. (3) Its rounds 7 and 8 test two short cues in ShipLoop's released
spec stage, one that leaves a limit open and one that takes a default; it will send the result.

**The count** (`by_source.py`, new: it reads each run's specification with the loop's own reader and the run's
`strength.json`, and counts clauses by the first word of their Source line).

| Source of the clause | Lens text: written | failing on the correct reference | Pilot's text: written | failing |
|---|---|---|---|---|
| `request` | 72 | 9 (12.5%) | 73 | 13 (17.8%) |
| `implied` | 78 | 13 (16.7%) | 78 | 22 (28.2%) |
| `choice` | 53 | 21 (39.6%) | 48 | 17 (35.4%) |
| `existing` | 223 | 4 (1.8%) | 300 | 7 (2.3%) |
| all | 426 | 47 (11.0%) | 499 | 59 (11.8%) |
| all but `existing` | 203 | 43 (21.2%) | 199 | 52 (26.1%) |
| added by the plan stage (all `implied`) | 3 | 3 | 4 | 4 |

Per case, all but `existing`: orders 9 of 70 (12.9%) against 9 of 58 (15.5%); ticket assignment 10 of 52 (19.2%)
against 13 of 60 (21.7%); due times 24 of 81 (29.6%) against 30 of 81 (37.0%).

- **F25 (firm as a count).** The lens form is shorter only in how much existing behaviour it restates. It writes as
  many clauses from the request (72 against 73) and implied by it (78 against 78), a few more choices (53 against
  48), and 77 fewer `existing` ones. A clause that restates existing behaviour almost never rejects the reference
  (2%), since the reference is built on the same repository. So R8.2's pooled share moves with how much a text
  restates, and "one clause in nine" (F23) understates what a specification adds: of the clauses about the change,
  one in five (lens) and one in four (the pilot's text) reject a correct product.
- On that base the lens text is lower in all three cases, by a fifth pooled (21.2% against 26.1%). That is inside
  the bar R8.2 registered (a third), with one run a cell and no measure of this pilot's run-to-run spread, so the
  reading stays "no difference shown". It is the same direction three times, and a registration of any further text
  should read this base beside the registered one.
- **F26 (firm as a count).** The writer's own choices are where a correct product is rejected: two in five of them
  (39.6% and 35.4%), against 16.7% and 28.2% of the implied clauses and 12.5% and 17.8% of the request's own.
  Choices are an eighth of what the lens text writes and 21 of its 47 rejecting clauses. This is F24 with a number,
  on three cases instead of one request. Of the request's own clauses that fail, five in each text are about the
  tests the request asks for (`request-clauses-about-tests` in the log; on orders the reference ships no tests,
  section 10; the ticket cases were not examined).
- **F27 (interim: seven clauses, two cases).** Every clause the plan stage added fails on the correct reference: 3
  of 3 with the lens text and 4 of 4 with the pilot's. They are edge conditions: identifiers at their limit, a name
  with an unpaired surrogate, what a failed save leaves behind. Why each test fails on the reference was not
  examined. Amendment 1 made the plan stage heavy and let it add a clause where the specification "lacks something
  a use case needs"; in these cells what it added was stricter than a correct delivery. No whole loop is read this
  way here, because a loop's builder builds to the clause.

**Correction to the Result above.** "77 of the pilot text's 86 extra clauses were `existing` ones (134 and 158
against 104 and 111)" counted use cases in the 77 and in the four figures. By clauses it is 78 of 86 (132 and 157
against 101 and 110). Marked in place.

**The operator's work among the failing items** (exploratory;
`evidence/lens-enrichment/operator-items-read-by-hand.txt` holds the rule and every id). About half of the items
that fail on a correct product are the operator's work: 27 of 58 with the lens text and 35 of 75 with the pilot's.
None is on orders (a library); on ticket assignment it is the existing command-line tool; on due times it is 21 of
32 and 27 of 43, and that request is itself about operating the product (change the hours, backfill, switch on, roll
back). No failing item in either text requires a new control: where a setting or a switch appears the request names
it, and the specifications say as much in their reasons ("require no live configuration endpoint", "without a new
command"). What the specification adds on due times is the form: the name and range of a setting, refuse or prepare
at start, which failure stops a start. What goes beyond the request is documents: 10 of the 11 such items (3 with
the lens text, 8 with the pilot's) require a runbook, instructions or a reference page to say something, and a
correct product without that page fails them. So the other session's guess holds here: with a repository the
unconditional operator line did not produce controls nobody asked for. It produced decided forms of the work the
request names, and required documents.

**What this says about the reworded text, before any run of it.**

- The most its `Open:` line can do on this count: choices are 21 of the lens text's 47 rejecting clauses, so if it
  wrote none of them as requirements and nothing else moved, 26 of 373 clauses (7.0%) would reject a correct
  product. The text keeps a clause above each `Open:` line, so how much of that it takes is what a run would show.
- Its operator line is conditional ("where running it or recovering from it is part of what was asked"). On due
  times the condition holds, so the line stays in force there; on ticket assignment and orders the lens text
  already wrote nothing beyond the request. On these three cases the difference between the reworded and the lens
  text should therefore come mostly from the `Open:` line. The words "using the controls that already exist" are
  the part that could still act on due times, and a result there could not separate the two.
- If the owner says to run it, its registration reads, beside the readings of this section: choice clauses written
  and rejecting, the share rejecting among clauses not `existing`, and the plan stage's added clauses. Those
  baselines are in this entry, before any run of it.

**A provenance note on the gradings above.** Each `strength.json` says it was graded "with uncommitted changes to
the pilot folder". That change is the reworded text's port in `ratchet.py`, written at 03:33:13. All five runs had
started at 03:22:49 from commit 43d5486168448f221763d9413f7ea02878f6d237 (`run.json`: `started`, `local_head`), and
`grade.py` does not load `ratchet.py`. No graded path was touched.

Evidence: `by_source.py`; `evidence/lens-enrichment/failing-by-source.json` (every failing item with its Source
line), `failing-by-source-log.txt` (the tables), `operator-items-read-by-hand.txt`.

### Received: the other session's rounds 7 and 8, and what these records hold for its open question (2026-11-21 05:42)

Status: what was received is recorded as received (its work, its instruments; I re-ran nothing of it). The count
below is firm for these six runs as a count and rough as a mark (a word match); the hand reading is exploratory.
No model ran. No registered reading changes.

**Received at 05:36.** The session "Spec elaboration" ran two two-sentence cues inside ShipLoop's released spec
stage (its journal, section 22, read here at commit 0d46d085479bf43e02cf964ee86917cc5b44dcb0, on its local main
and not on origin when read; 48 sessions, Sonnet high and Sol 6.2 medium, four requests with no repository, two
judges, a covered count on 22 items). The cue that records an unresolved bound as an open gap moved nothing (+0.5
and 0.0 on Sonnet, +0.5 and +1.0 on Sol). The cue that takes "a limit the request leaves to choice as the best
default, recorded as an assumption" is shown on both drivers under both judges (+3.0 and +3.0 on Sonnet, +5.5 and
+6.5 on Sol), with nothing else lost and no capability added on the four items its sorters call beyond the request.
Read item by item by that session, the 20 gains are: 12 a default for a limit the released stage also says exists
and leaves without a value (a file's size and row limits, an input's maximum length, a reply timeout); 3 a cap on a
waitlist the request never mentioned (10, 10 and 20, where the released stage wrote "Assumed none"); 2 platform
limits given their numbers; 1 a set named; 2 no difference. The defaults differ between draws (1 MiB and 1,000
rows; 2 MiB and 5,000; 256 KiB and 500). Its standing there: the default cue goes to a Sol review at maximum effort
and then to the owner, as evidence that the stage's two instructions are resolved differently by the two drivers,
"not evidence that the defaults are right". Its section cites F24 and F26 as the only built-product evidence, and
asks its review how to word the sentence "so that it covers a limit the requested behaviour cannot work without and
not a limit that need not exist". It added that this pilot's instrument could tell those two kinds apart.

**What these records hold on that.**

- *Few bounds, and the ones chosen sit behind a chosen name.* The three requests here state their own limits (64
  characters; 4, 24, 72 and 168 hours; the meter's 10,000 ticks), so the writers chose few. Where a writer chose no
  further limit, or the unit the product already uses, the clause passes on the reference: 5 of 5. Where it chose a
  range for the hours setting it fails: 3 of 3. But those three fail through the setting's name. Both specifications
  chose one variable a priority (`DUE_HOURS_URGENT` and three more: lens C-6, the pilot's C-7) and their tests set
  those; the correct reference reads one `RESPONSE_HOURS` setting. Every test that changes the hours fails on it,
  the test of the request's own clause included (lens C-5, the pilot's C-6). So these records cannot say a chosen
  bound is wrong. They say that a thing which had to be decided, a setting needs a name, was decided differently by
  two correct products (`evidence/lens-enrichment/choices-read-by-hand.txt`).
- **F28 (firm as a count, rough as a mark).** What rejects a correct product is a refusal the writer added. Clauses
  whose statement makes the product refuse, fail or require something (a fixed word list in `by_source.py`,
  written once and not adjusted after its first run), both texts pooled:

  | Source of the clause | Refuses or requires: written | failing on the correct reference | The rest of its kind: written | failing |
  |---|---|---|---|---|
  | `choice` | 27 | 18 (67%) | 74 | 20 (27%) |
  | `implied` | 19 | 10 (53%) | 137 | 25 (18%) |
  | `request` | 20 | 2 (10%) | 125 | 20 (16%) |
  | `existing` | 85 | 1 (1%) | 438 | 10 (2%) |

  A refusal the writer added on its own (`choice` or `implied`) rejects a correct product 28 times in 46; its other
  additions 45 times in 211; a refusal the request states or the product already has, 3 times in 105. Each text
  alone shows the same split (choices: 9 of 14 against 12 of 39 with the lens text, 9 of 13 against 8 of 35 with the
  pilot's). My own labels of the 101 choices, made knowing the outcomes, give 65% against 28% and 67% against 21%.
  This is amendment 2's "loosest choice" seen from the other side: the choices that pass are the ones that add no
  refusal ("named fields can appear in any order", "no safe-integer ceiling", "the existing convention").
- *What it says to the other session's question, and what it cannot.* A cap on a waitlist and a maximum size for a
  file are both refusals the request did not state, so this mark does not separate its two kinds. What it supports
  is narrower: an added refusal is where two correct products most often part ways, whatever its reason; and a
  default that must exist (a name here, a size there) is still decided differently by different writers, as its own
  three draws of the file limits show. Whether a given added refusal is *wanted* is not something "fails on the
  reference" can tell. The held-out checks, written from the request alone, can: in this pilot they failed for one
  added refusal (refuse to start on a file without due times, F20 and F24) and for no chosen name.
- *Bearing on the reworded text.* In this pilot an `Open:` point is handled as the default cue's rule without the
  test: the build takes a reasonable answer and reports it, and no test pins it. A run of that text would show
  whether leaving the writer's added refusals unpinned costs caught defects (the 36 or 37 of 37) or only the
  rejections.

Evidence: `by_source.py` (the `REFUSES` word list); `evidence/lens-enrichment/failing-by-source.json`
(`choice_clauses`, `refusing`), `failing-by-source-log.txt`, `choices-read-by-hand.txt`.

## 21. Amendment 8, 2026-11-21 06:55: the reworded lens text, in three rungs, the small one first (registered before any run of it)

Owner, 2026-11-21 06:46, answering "Should I run the reworded text as a third arm (the same five runs, about an
hour)?": "Yes, plan small experiments before doing larger ones to see if you can get fast iteration". My reading: run
it, as a ladder. A cheap run comes first, whose result can change the wording within minutes; then one whole cell;
then the rest. A rung is climbed only by a rule written here before it runs.

**What runs.** `--enrich reworded`: the other session's `docs/experiments/spec-elaboration-20261120/arms/
R-lenses-reworded.md` (its commit f2ffbfdf7a4f38e1daf6505daf51d1cd5353dce5, unchanged since), set into this stage
the way the lens text was: this stage's frame and file path, the repository-reading step first, the `existing` source
kind kept, and nothing else (`evidence/reworded-enrichment/port-against-R-lenses-reworded.diff`). It differs from
the lens text in what section 20 found to matter: a clause is earned only by a sentence of the request, by what the
outcome needs, or by what must be preserved; "add no capability, duty or restriction that the request's purpose does
not call for"; a point the request leaves unsettled is the loosest choice when any answer serves the requester
equally, and otherwise a clause "at the loosest reading that is certainly wanted" with an `Open:` line; "invent no
bound"; and the operator line is conditional. In such a run every later stage's frame gains one paragraph
(`OPEN_NOTE`): an open point is not a requirement, a plan says how each is handled, a build takes a reasonable
answer and says which in its report, a test checks only what its clause states, and no stage adds a clause that
settles one. Runner as in every compared cell: Codex `gpt-6.2-sol` at high, one new Git repository a run, outside
the checkout.

**Apparatus added for the ladder** (self-tested with the scripted stand-in before this commit: the standing check
passes for all three texts; a spec-only run records `stop-after-spec`, one session, no gate; a run started from it
commits a byte-identical specification, runs no spec session and ends converged; a start from another text's
specification is refused).

- `ratchet.py run --stop-after spec`: the spec stage alone.
- `ratchet.py run --spec-from RUN`: a run that starts from the specification RUN wrote, as written, with no spec
  session; `run.json` records `spec_from` and the seconds of RUN's spec sessions. So a specification read at the
  first rung is the one built and tested on at the later rungs, and no session is paid for twice.
- `by_source.py specs`: counts what a specification wrote at its `spec` commit, with no grading: clauses by Source,
  the refusals the writer added on its own (choice or implied clauses that F28's word list marks), `Open:` lines.

**The specifications already on file, counted the same way** (the base for the first rung):

| Specification | Clauses | Use cases | request | implied | existing | choice | Added refusals | `Open:` lines | Minutes |
|---|---|---|---|---|---|---|---|---|---|
| lens, orders | 82 | 8 | 26 | 24 | 12 | 20 | 8 | 0 | 5.0 |
| lens, ticket assignment | 151 | 11 | 18 | 18 | 101 | 14 | 3 | 0 | 7.0 |
| lens, due times (test-strength cell) | 190 | 12 | 28 | 33 | 110 | 19 | 14 | 0 | 8.0 |
| lens, due times (loop a) | 170 | 11 | 19 | 31 | 95 | 25 | 7 | 0 | 7.6 |
| lens, due times (loop b) | 197 | 16 | 16 | 53 | 104 | 24 | 18 | 0 | 13.3 |
| pilot's, orders | 69 | 12 | 28 | 14 | 11 | 16 | 7 | 0 | 6.1 |
| pilot's, ticket assignment | 190 | 17 | 19 | 27 | 132 | 12 | 1 | 0 | 13.5 |
| pilot's, due times (test-strength cell) | 236 | 15 | 26 | 33 | 157 | 20 | 10 | 0 | 10.1 |
| pilot's, due times (loop) | 278 | 21 | 24 | 44 | 184 | 26 | 14 | 0 | 10.8 |

Three specifications of one request with one text spread from 7 to 18 added refusals and from 19 to 25 choices, so
a difference is read only where the new text's three fall outside that range.

**The rungs.**

| Rung | What runs | About | What it can show |
|---|---|---|---|
| 1, small | five spec-only runs: `r1-orders`, `r1-ticket-assignment`, `r1-due-times-1`, `-2`, `-3` | 5 to 13 minutes | whether the text writes what it is meant to (open lines, fewer choices, fewer added refusals) and how it treats the due-times start |
| 2, medium | from rung 1's specifications: the orders test-strength cell `p1R-stand-in-rules`; the two due-times loops `p3R-ticket-due-times-a` and `-b` (specifications 2 and 3), whose first builds are graded on the held-out checks as soon as they are committed, while the loops go on to their test pass | 20 minutes | whether later stages cope with an open line; rejecting clauses and caught defects on one case; two first builds against the held-out checks |
| 3, large | from rung 1's specifications: `p1R-ticket-assignment` and `p1R-ticket-due-times` (specification 1); the two loops end their test pass | 35 minutes | the pooled readings |

**Rules for climbing.**

- After rung 1, go on if every specification is accepted by the script and at least one of these holds. (a) On due
  times all three specifications write fewer choice clauses than the lens text's fewest (19) and fewer added
  refusals than its fewest (7). (b) At most one of the three writes, as a requirement and not under an `Open:`
  line, that an enabled start refuses a data file without due times (read by hand; four of the five on file do).
  If neither holds, the wording is changed: one change, stated with its reason in this journal before its run, and
  rung 1 runs again on due times. At most three wordings in all; then stop and report what was seen.
- After rung 2, go on unless the apparatus failed, or the orders tests pin an answer to an open point (read in the
  tests). Either is fixed and the orders cell run once more before rung 3.
- Rung 3 has no rule: it completes the cells.

**Readings.**

- **R9.1, due times.** As R8.1, on the two loops' first builds: *avoided* if both pass the five held-out checks
  that failed before (`cli`, `migrate`, `restart`, `rollback`, `switch`), *not avoided* if both fail them, otherwise
  not settled. Read beside it, in each specification, plan and build report: whether the start on a file without
  due times was a requirement, an open point or unsaid, and which answer the build took. The text's author knew
  this case when writing it, so a pass is not a blind result.
- **R9.2, clauses that reject a correct product.** Pooled over the three `p1R` cells, among clauses not `existing`
  (the base F25 argued for): the lens text's is 43 of 203 (21.2%). *Better* at or under 14.1% (a third lower),
  *worse* at or over 28.2%, otherwise no difference shown. Reported beside it: the share over all clauses (lens
  11.0%), use cases failing (11 of 31), and the second correct ticket-assignment delivery (15 more).
- **R9.3, strength.** Calibrated defects caught of 37: *kept* at 35 or more (lens 36).
- **R9.4, what was written and what it cost.** Clauses by Source, added refusals written and rejecting (lens: 28
  written, 16 rejecting), `Open:` lines, minutes and output tokens.
- **R9.5, open lines after the spec stage.** Of the clauses that carry an `Open:` line, how many fail on the
  correct reference; whether any clause a later stage added settles an open point; what each build did at each.

**Predictions, mine, before any run.** Fewer clauses than the lens text on every case. Fewer choices and fewer
added refusals, outside the lens range on due times. R9.2 lower but not by a third (between 14% and 19%). R9.3
kept. R9.1 most likely not settled, one build of each kind: a builder told to take a reasonable answer may take the
refusal as the specification writers did; avoided in both about one time in three. The author's three, registered
in its commit 917eee6047304c0c880faf87456b20b5d356c5de: fewer clauses than the lens form, a lower share of clauses
failing on a correct product, no loss of defects caught.

**Limits known before the runs.** One run a cell and three specifications of due times; no measure of this pilot's
run-to-run spread beyond the table above. The lens cells ran three and a half hours earlier on the same machine.
A cell here is a specification written in one run and continued in another, where the lens cells did both in one;
its minutes are the two added. Rung 2's held-out gradings run while the two loops are still in their test pass (one
build's held-out checks take seconds); amendment 7 graded only after every run had ended. If the wording is changed
at rung 1, what runs is no longer the other session's arm as drafted and is named for what it is. Codex still shows
the account's skills to every session (section 19), the same on every side.

### Rung 1, result (2026-11-21 07:03; five spec-only runs, 06:55:21 to 07:00:13)

Status: firm for what was run (one specification each of orders and ticket assignment, three of due times). Every
specification was accepted by the script on its first try; no session's record holds a held-out mark.

| Specification, reworded text | Clauses | Use cases | request | implied | existing | choice | Added refusals | `Open:` lines | Minutes |
|---|---|---|---|---|---|---|---|---|---|
| orders | 26 | 5 | 24 | 1 | 1 | 0 | 0 | 8 | 2.6 |
| ticket assignment | 43 | 9 | 12 | 7 | 24 | 0 | 1 | 7 | 3.8 |
| due times 1 | 30 | 8 | 12 | 5 | 13 | 0 | 0 | 10 | 4.9 |
| due times 2 | 34 | 8 | 13 | 6 | 15 | 0 | 0 | 8 | 4.6 |
| due times 3 | 34 | 7 | 12 | 5 | 17 | 0 | 0 | 9 | 4.3 |
| *lens text, same cases (base table above)* | *82; 151; 170 to 197* | *8; 11; 11 to 16* | | | *12; 101; 95 to 110* | *20; 14; 19 to 25* | *8; 3; 7 to 18* | *0* | *5.0; 7.0; 7.6 to 13.3* |

- **Rule (a) holds.** On due times the three write 0, 0 and 0 choice clauses (the lens text's fewest: 19) and 0, 0
  and 0 added refusals (its fewest: 7). No specification of any case writes a single choice; nine earlier
  specifications never wrote fewer than 12.
- **Rule (b) holds: none of the three requires the refusal to start.** Each writes the request's sentence as a
  clause and puts the decision in its `Open:` line, naming both answers: "The operator decides how an attempted
  enabled start with an incomplete file is handled, for example by requiring preparation first or completing
  preparation before serving enabled requests" (1, C-19); "The requester decides the operator workflow for
  preparation and early activation, such as a preparation step before starting the enabled server or startup
  preparation that finishes before any enabled response" (2, C-18); "The requester decides how operators initiate
  preparation and confirm readiness, including whether setting `DUE_TIMES=on` on an unprepared file waits for
  preparation or requires a prior operation" (3, C-20). Four of the five earlier specifications decided it, for the
  refusal (`evidence/reworded-enrichment/rung-1-due-times-reading.txt`).
- **What the open points are.** On orders, the eight are the things the other two texts decided and a correct
  product then failed: missing, repeated and unknown keys, further line separators, which ids and number spellings
  are admissible, an empty price, a date that is no calendar date, which error comes first, sums past the largest
  safe integer. On due times they include how two filters combine with `overdue=true` (the documents and the
  shipped code disagree), whether the command-line tool shows the due time, and what a return from a rollback must
  recover: each a clause that failed on the correct reference with the lens text (C-36, C-181, C-70 there).
- **The size.** A sixth of the lens text's on due times (30 to 34 clauses against 170 to 197), a third on orders,
  written in under five minutes. It restates far less existing behaviour (13 to 17 `existing` clauses against 95
  to 110) and writes fewer implied clauses (5 or 6 against 31 to 53). That is the thing to watch at the next rungs:
  the calibrated defects of the ticket cases sit partly in behaviour these specifications no longer pin.
- **Is there enough to conclude early?** Enough to say the text changes what a specification decides, and not by
  chance of the draw: five of five without a choice. Not enough to say anything about a built product, or about
  how many planted defects tests written from so short a specification catch. Rung 2 is the cheapest run that can
  say either, so the ladder goes on.

By the registered rule: go on to rung 2, with these specifications and this wording unchanged.

Evidence: `evidence/reworded-enrichment/` (`rung-1-specs.json`, `rung-1-specs-log.txt`,
`rung-1-due-times-reading.txt`, and each run's `run.json` and `spec.md` under `r1-*/`).

### Amendment 9, 2026-11-21 07:08: two larger cases join the ladder, as a guard against saying too little (registered before any run of them)

Owner, 07:05, while rung 2 ran: "Do we need to raise the complexity of the test cases to provide more depth of
insight? I was suggesting doing a scenario of using board games in node, another more complex would be Grokbot in
node".

**What the records say.** Both scenarios exist here and have been run: `node-chess-engine` (a chess rules engine
in Node.js; 10 held-out checks) and `grokbot-local` (amendments 4 to 6; two browser yardsticks of 49 and 28 checks,
calibrated on five builds). On both, every arm's first build passed everything: the pilot's whole loop on chess (10
of 10, at 20.5 minutes), and on Grokbot the pilot's first build, ShipLoop's delivery and one session at low effort
in 6.8 minutes (49, and 23 stated with 5 implied). So neither could separate the arms (F19), and size was not what
gave insight. The one case that taught something is the small due-times change: a change to an existing product
that leaves one consequential thing unsaid.

**What they can do now.** Rung 1 changed the question. The reworded text writes a third to a sixth of what the
other texts write. A case that every arm passes cannot show a gain, but it can show a loss, and a loss from saying
too little is this text's risk. A rule-dense case (chess) and a large, loosely worded one (Grokbot, whose second
yardstick has five checks on things the request implies without stating) are where a short specification is most
likely to cost. So both join as a guard, the small rung first.

**Cells.** `r1-chess` and `r1-grokbot`: the spec stage alone. Then, if each specification is accepted,
`p3R-node-chess-engine` and `p3R-grokbot-local` from those specifications: plan and build, stopped at the first
build (`--stop-after build`, new; self-tested with the scripted stand-in: two sessions, gates `after-build-1` and
`final`, `stop-after-build`, and the standing check still passes), graded on the held-out yardsticks.

**Readings.**

- **R10.1, chess.** Held-out checks at the first build: *no loss* at 10 of 10 (the pilot's text: 10 of 10). A
  failing check is read against the specification: was the rule stated, left open, or missing.
- **R10.2, Grokbot.** Both yardsticks at the first build: *no loss* at 49, and 23 stated with 5 implied (the pilot's
  text's first build and one bare session: 49, 23, 5; Sonnet's bare build: 48, 23, 4). A failing check is read by
  hand with a probe before it counts, under amendment 4's rule: the yardstick is corrected only where it assumes
  what the request does not say (F18).
- Reported: clauses, open lines, minutes to the first build (the pilot's text: 20.5 on chess, 37.5 on Grokbot;
  these run beside up to five other runs, so minutes are read loosely).

Prediction: no loss on chess (the rules are public and the request says "every legal move"); on Grokbot at most
one check lost, among the five implied ones.

**Limits.** One run a case. They can only show a loss. The Grokbot yardsticks have met five builds, and a sixth
design may meet an assumption they still hold.

**Not done, and the owner's to decide:** a new or harder scenario (another game, a larger Grokbot). The records
give no reason to expect more insight from size alone, and a browser yardstick written new took six rounds and five
builds before it could be trusted (F18). What would add depth on the other side of the question, deciding too
much, is more cases like due times: a change to an existing product with one thing left unsaid, which the text's
author has not seen. There is one such case today.

### Rung 2, result (2026-11-21 07:22; the orders cell and the two due-times first builds)

Status: firm for what was run: one test-strength cell and two first builds, each from a specification of rung 1.

**Orders, test strength (`p1R-stand-in-rules`, from `r1-orders`; graded 07:19 from commit 80d2f064fc7c).**

| Text | Clauses / use cases tested | Clauses failing on the correct reference | Use cases failing | Defects caught | Minutes (of which enrich) | Output tokens |
|---|---|---|---|---|---|---|
| reworded | 27 / 5 | 2 (7.4%) | 1 | 4 of 4 | 18.2 (2.6) | 42,611 |
| lens | 82 / 8 | 9 (11.0%) | 1 | 4 of 4 | 23.7 (5.0) | 61,805 |
| pilot's | 69 / 12 | 9 (13.0%) | 3 | 4 of 4 | 18.8 (6.1) | 49,042 |

- The three items that fail on the reference (C-25, C-26, U-5) are the request's own "cover it with node:test
  tests; npm test must pass": this case's reference ships no tests of its own, the artifact noted in section 10 and
  in the lens cell (C-78 to C-80 there). No other clause fails. The six that failed with the lens text were choices,
  and this specification has none: those points are its open lines, and every clause that carries one passes.
- All four planted defects are caught, each by request clauses (`one-rule-missing` by C-6, C-11, U-1; `tested-only`
  by C-13, C-20; `limit-never-trips` by C-23, C-24, C-27, U-3, U-4; `cross-field` by C-18, C-19, C-20). A third of
  the clauses, the same catch.
- The plan stage added one clause (C-27, recovery after the meter's limit error) and it passes on the reference;
  the seven it added in earlier cells all failed (F27).
- The tests pin no open point. The plan says so in words ("Inputs whose outcomes depend on an `Open:` choice are
  outside those assertions, including field permutations, alternative separators and number spellings, shape-valid
  calendar anomalies, multiple simultaneous errors, and out-of-contract or overflowing totals"), and a search of
  the acceptance tests finds no assertion on an unknown, missing or repeated key, another separator, calendar
  validity, precedence, or an empty price.

**Due times, the two first builds (`p3R-ticket-due-times-a` from specification 2, `-b` from specification 3),
graded on the held-out checks when each build was committed, while the runs went on to their test pass.**

| First build | Held-out checks | Minutes to it (enrich, plan, build) |
|---|---|---|
| reworded, a | 8 of 8 | 20.5 (4.6, 6.9, 9.0) |
| reworded, b | 8 of 8 | 18.1 (4.3, 5.0, 8.7) |
| lens, a and b | 3 of 8 and 2 of 8 | 28.1 and 31.9 |
| pilot's | 3 of 8 | 32.3 |

- **R9.1, due times: avoided.** Both first builds pass the five checks that failed in all three earlier loops
  (`cli`, `migrate`, `restart`, `rollback`, `switch`), and the other three.
- **How.** Each specification had left the start open and named both answers (rung 1). Each plan then took the
  same one as its default for the build and said it was a default: "Choose preparation as part of enabled startup
  ... It fills gaps before binding" (a); "For the open preparation policy, use one enabled startup to prepare
  missing deadlines synchronously before listening" (b). Each build report lists the answer it took at every open
  point under its discoveries (a: C-18; b: C-20), as the stage frame asks. So the same model family that decided
  for the refusal four times in five when it wrote a specification chose the other answer two times in two when
  the point reached it open, at planning, with both answers in front of it.
- **Other decisions moved the same way.** Both plans also chose the settings' names (`DUE_HOURS_URGENT` and three
  more) and a range for the hours (1 to 876,000 in a; up to the largest safe integer in b), how two filters combine
  with `overdue=true`, and what the command-line tool shows. With the earlier texts each of those was a clause with
  a test, and failed on the correct reference. Here each is a line in the build report, and no test holds a second
  correct product to it.
- Limits: two builds, one model family, and a text whose author knew this case. The held-out checks ask for none of
  the other decisions, so they say nothing about whether those defaults are what a customer wants.

**Is there enough to conclude early?** For R9.1, yes: the registered reading is settled, two of two. For the text as
a whole, no. Orders is the case with the least existing behaviour. Whether tests written from a specification of
30 to 43 clauses still catch the 27 and 6 planted defects of the two ticket cases is the open risk, and only rung 3
measures it.

By the registered rule (no apparatus failure; the orders tests pin no open point): go on. Rung 3 started at
07:20:52, from commit 80d2f064fc7c.

Evidence: `evidence/reworded-enrichment/p1R-stand-in-rules/` (run record, `strength.json`, plan, tests report,
manifest), `p3R-ticket-due-times-a/` and `-b/` (`build-1-hidden.json`, and the plan and build report at the first
build's commit), `rung-2-orders-by-source-log.txt`.

### The two larger cases, result (2026-11-21 07:41; amendment 9's cells), and the end of the two loops

Status: firm for what was run, one run a case. These cells can only show a loss.

| Case, text | Specification: clauses / use cases, choices, open lines | First build: held-out checks | Minutes to it (enrich, plan, build) | Output tokens to it |
|---|---|---|---|---|
| chess engine, reworded | 56 / 7, 0, 5 | 10 of 10 | 14.7 (4.2, 4.7, 5.8) | 38,371 |
| chess engine, pilot's (section 10) | 94 / 15, 4, 0 | 10 of 10 | 20.5 | |
| Grokbot-local, reworded | 100 / 15, 0, 18 | 49 of 49; 23 of 23 stated and 5 of 5 implied | 26.8 (4.6, 7.0, 15.0) | 71,898 |
| Grokbot-local, pilot's (section 17) | | 49 of 49; 23 and 5 | 37.5 | |
| Grokbot-local, one bare session at high (section 17) | none | 49 of 49; 23 and 5 | 16.9 | 47,308 |

- **R10.1, chess: no loss.** The specification kept the rules the request leans on: 27 of its 56 clauses are
  `implied` (the pilot's text wrote 40 of 94), and none is a choice. Its five open lines are about a malformed or
  impossible position, a move not in UCI form, which test positions to use, and on what machine the two speed
  limits are measured.
- **R10.2, Grokbot: no loss.** All 49 checks of the first yardstick and all 28 of the second pass at the first
  build, the five implied ones among them, where I had predicted that at most one of those would be lost. No check
  needed a second run or a probe. The gradings ran at 07:35 to 07:37 beside three live runs.
- Both first builds came sooner than with the pilot's text (14.7 against 20.5 minutes, 26.8 against 37.5), run
  beside four or five other runs. A single session with no specification is still the quickest on Grokbot (16.9).
- What this does not show: a gain. Every arm passed these cases before (F19). It shows that a specification a
  third to a half the size, with its undecided points marked and not decided, lost nothing on a rule-dense build
  or on a large, loosely worded one.

**The two due-times loops, at their end** (`--stop-after tests`).

| Loop | Its own gate after the test pass | Held-out checks, first build and end | Minutes to that gate | Output tokens |
|---|---|---|---|---|
| reworded, a | 41 of 42: C-31 fails | 8 of 8, 8 of 8 | 38.9 | 96,229 |
| reworded, b | 41 of 41 | 8 of 8, 8 of 8 | 32.8 | 79,353 |
| lens, a and b (section 20) | 184 of 184; 215 of 215 | 3 of 8; 2 of 8 | 57.8; 61.9 | 148,407; 157,262 |

- Loop a's failing test is on an `existing` clause (C-31, "The raw CLI list retains its existing row layout"). The
  test session wrote a data file by hand with a tab inside a ticket title and asserts four raw fields; the
  formatter, which this build did not change, joins the columns with tabs and prints five. The service refuses
  such a title at its API. So the test is stricter than the shipped product on existing behaviour: the kind of
  clause that rejected a correct product one time in fifty in section 20's count. A full loop would have sent it
  to a fix session.
- With the lens text every own test was green and the product was wrong (F20's pattern). Here one own test is red
  and the product passes every held-out check.

Evidence: `evidence/reworded-enrichment/` (`r1-chess/`, `r1-grokbot/`, `p3R-node-chess-engine/`,
`p3R-grokbot-local/` with both yardsticks' results and the grading log, `guard-specs-log.txt`; the loops' `run.json`,
`hidden.json` and, for a, `gate-after-tests-failing.txt`).

### Rung 3, result, and the readings of amendment 8 (2026-11-21 07:56)

Status: firm for what was run: one run a cell; three test-strength cells, two loops, two larger cases; one model
family (Codex `gpt-6.2-sol` at high) as writer, planner, builder and tester.

**Test strength, reworded text against the lens text and the pilot's own** (the ticket cells graded from the
specifications of rung 1; each cell's minutes are the specification run and the continued run added).

| Case, text | Clauses / use cases tested | Clauses failing on the correct reference | Use cases failing on it | Second correct delivery, beyond the reference | Defects caught | Minutes (of which enrich) | Output tokens |
|---|---|---|---|---|---|---|---|
| orders, reworded | 27 / 5 | 2 (7.4%) | 1 | none exists | 4 of 4 | 18.2 (2.6) | 42,611 |
| orders, lens | 82 / 8 | 9 (11.0%) | 1 | none exists | 4 of 4 | 23.7 (5.0) | 61,805 |
| ticket assignment, reworded | 44 / 9 | 3 (6.8%) | 0 | 3 (2 clauses, 1 use case) | 26 of 27 | 26.9 (3.8) | 63,618 |
| ticket assignment, lens | 153 / 11 | 13 (8.5%) | 3 | 15 (11 clauses, 4 use cases) | 26 of 27 | 38.0 (7.0) | 96,512 |
| ticket due times, reworded | 31 / 8 | 3 (9.7%) | 1 | none exists | 6 of 6 | 25.3 (4.9) | 62,333 |
| ticket due times, lens | 191 / 12 | 25 (13.1%) | 7 | none exists | 6 of 6 | 44.2 (8.0) | 112,503 |
| pooled, reworded | 102 / 22 | 8 (7.8%) | 2 of 22 | | 36 of 37 | 70.4 | 168,562 |
| pooled, lens | 426 / 31 | 47 (11.0%) | 11 of 31 | | 36 of 37 | 105.9 | 270,820 |
| pooled, pilot's own | 499 / 44 | 59 (11.8%) | 16 of 44 | | 37 of 37 | 112.2 | 256,223 |

**The readings of amendment 8.**

- **R9.1, due times: avoided.** Both first builds pass 8 of 8 (recorded under "Rung 2, result").
- **R9.2, clauses that reject a correct product: better.** Among clauses not `existing`: 8 of 64 (12.5%) against the
  lens text's 43 of 203 (21.2%); the bar was 14.1%. Over all clauses 7.8% against 11.0%. Use cases 2 of 22 against
  11 of 31. The second correct ticket-assignment delivery fails 3 further items where it failed 15.
- **R9.3, strength: kept.** 36 of 37 (bar 35; lens 36; pilot's 37). The one missed is `update-rejects-resolved` on
  ticket assignment, a defect in existing behaviour; the lens text missed `cli-no-assignee` there, which this text's
  tests catch. Same count, different defect.
- **R9.4, what was written and what it cost.** A quarter of the clauses (102 against 426). No choice clause in any
  of the seven specifications written with this text (five of rung 1, chess, Grokbot). Added refusals at the end of
  the three cells: 3 written and none rejecting (lens: 28 written, 16 rejecting). A third less time on the three
  cells (70.4 against 105.9 minutes) and 38% fewer output tokens.
- **R9.5, open lines after the spec stage.** 25 clauses in the three cells carry an open line; 2 of them fail on
  the correct reference (ticket assignment C-36, due times C-19), and neither failure is about its open point.
  C-19's test says in a comment that refusal until explicit preparation "is a supported outcome" and accepts either
  answer. C-36 is the command-line table showing the assignee, which failed on this reference with all three texts.
  The plan stage added 3 clauses (orders C-27, ticket assignment C-44, due times C-31); one fails on the reference
  (C-44), and none settles an open point. Both builds list the answer taken at every open point in their reports.

**What still fails on the correct reference, all eight clauses.** Four are the request's own clauses about the tests
it asks for (orders C-25, C-26; ticket assignment C-42; due times C-29), the kind section 20 counted five of in each
earlier text. One is the command-line table (ticket assignment C-36: on the reference "the assigned and unassigned
rows both show "-""), failing with every text. One was added by the plan stage (C-44, a failed save leaves an
assignment available to retry: on the reference "refused assignment changed live state"). Two are sentences of the
request tested at an edge where the reference does not do what the sentence says: due times C-3 (with due times
off, a ticket created
at the last representable instant answers 500 where release 1.4.0 answers 201) and C-19 (a due time is shown before
the data file holds it). None is an addition of the specification writer's: this text wrote none.

**Predictions scored.** Mine, six: four held (fewer clauses; fewer choices and added refusals; strength kept; no
loss on chess and at most one implied check lost on Grokbot), two did not (I said R9.2 would land between 14% and
19%: it is 12.5%; I said R9.1 would most likely be not settled: it is avoided). The author's three (fewer clauses, a
lower share failing on a correct product, no loss of defects caught) all held.

**Findings.**

- **F29 (firm: seven specifications).** The reworded text takes the writer's own decisions out of the specification:
  no choice clause in seven of seven, and 5 to 18 open lines each, where nine earlier specifications never wrote
  fewer than 12 choices. No second wording was needed.
- **F30 (two builds; not blind, the text's author knew this case).** A decision left open and named was made right
  downstream: both due-times plans chose to prepare the data file at an enabled start, where four of five
  specification writers had chosen to refuse. The pattern of F20, every own test green over a wrong product, did not
  recur: the gates were 41 of 42 and 41 of 41, with 8 of 8 held-out checks.
- **F31 (firm at this size).** A quarter of the clauses kept the tests as strong (36 of 37) and removed most of
  what rejected a correct product (12.5% against 21.2% of clauses not `existing`). What the shorter specification
  gave up is one defect in existing behaviour that it no longer pins; what it gained is one defect the longer one
  missed.
- **F32 (reported).** It is cheaper at every stage: specifications in 2.6 to 4.9 minutes, the three cells a third
  quicker with 38% fewer output tokens, first builds sooner on every case (due times 18 to 21 minutes against 28 to
  32), loops to their gate in 33 and 39 minutes against 58 and 62.
- **F33 (one run a case; can only show a loss).** On the two larger cases the owner named, a rule-dense one and a
  large loosely worded one, the shorter specification lost nothing: chess 10 of 10, Grokbot 49 of 49 and 28 of 28.

**Is there enough to conclude?** For the question the owner asked (run the reworded text as a third arm), yes: on
every registered reading it is at least as good as both earlier texts and on three it is better, at lower cost, with
no loss on the two guards. What it does not establish: that it holds for another model family (every stage here was
Sol); that it holds on more than one case with a consequential thing left unsaid (there is one, and the text's author
knew it); that the defaults the plan now takes and reports (names, ranges) are what a customer wants; and anything
about ShipLoop, whose released spec stage is a different text that the other session's experiment concluded on
without a change.

**Checked twice.** At the owner's word ("use sonnet in Task() where you can") a Sonnet subagent recounted every
figure of the table and of R9.2 to R9.5 from `strength.json` and the specifications with a script of its own, not
`by_source.py`: all match. It also copied the evidence and drafted this subsection from the facts given to it.

**Received, 07:19, from the session "Spec elaboration"** (its journal sections 26 to 28; its commit 2f4f56fe2; its
work, not re-run here). It has concluded at the owner's word with no change to ShipLoop's templates. Two things it
sent bear on this text. Inside ShipLoop's released spec stage, three wordings that let the writer leave a point
open did nothing on its covered count, so it asked whether this text's writers would use `Open:` for points they
would otherwise have settled: rung 1 answers that they do, in seven of seven specifications. And its census of 31
real ShipLoop deliveries found limits chosen at build and written nowhere (nine in this pilot's own ShipLoop
Grokbot delivery); in the runs above the builder still chooses such limits, and its report lists each one because
the stage frame asks for it.

**Limits.** One run a cell. The machine's load average was 7 to 8 while five or six runs were in flight, so minutes
are loose. The comparison cells ran three to four hours earlier. One held-out mark, in loop b's test session, is a
process listing that showed another session's command line naming the installed skill (no path of the repository
appears in that session's record); it is read as the five marks of section 19 were, and the run is counted. The
gradings of rung 2 and of the two larger cases ran beside live runs; the two last test-strength gradings did not.

Evidence: `evidence/reworded-enrichment/` (`p1R-ticket-assignment/`, `p1R-ticket-due-times/` with each run's record,
`strength.json`, plan, tests report, manifest and grading log; `failing-by-source-log.txt` and `.json` for the three
cells against the lens text's; `summary.json`).

### Amendment 10, 2026-11-21 08:02: the small step again on the other runner, Sonnet (registered before any run of it)

Owner, 08:00, to "What next: the 5-minute Sonnet check first, or merge and push this branch?": "Sonnet check first".

**Why.** Every stage of amendment 8 ran on one model family. The first limit named in the result above is that
nothing shows the reworded text does the same to another. The owner's other named runner is Sonnet at high
(section 1). The cheapest run that can say is rung 1 again: the spec stage alone.

**Cells**, each `--host claude --model claude-sonnet-5-5 --effort high --stop-after spec`, one new repository a
run, a cap of 3 dollars a session so a session that runs away ends (`--max-budget-usd 3`):

- Wave 1, the check: the reworded text, `s1-orders`, `s1-ticket-assignment`, `s1-due-times-1`, `-2`, `-3`.
- Wave 2, the base on the same model: the lens text, `s1L-orders`, `s1L-ticket-assignment`, `s1L-due-times-1`,
  `-2`, `-3`. No Sonnet specification exists with either earlier text, and "stops deciding" needs what Sonnet
  decides when it is told to. It runs when wave 1 has ended, unless wave 1 already reads "does not hold".

**Readings**, counted by `by_source.py specs` at each run's `spec` commit:

- **R11.1, the mechanism.** *Holds* if each of the five reworded specifications writes at most 2 choice clauses and
  at least one `Open:` line (Sol: none and 7 to 10). *Does not hold* if any writes 12 or more choices (the fewest
  any Sol specification wrote with the other two texts). Otherwise partly.
- **R11.2, the due-times start.** Of the three, how many require, not under an `Open:` line, that an enabled start
  refuse a data file without due times (Sol with this text: none of three; with the other texts: four of five).
- **R11.3, the base.** The same counts and the same reading for the lens text on Sonnet, beside them.
- Reported: clauses and use cases, added refusals, minutes, and the cost the host reports.

**What it cannot show.** Anything about a built product or about tests on Sonnet: that is a later rung, with priced
sessions, and it is put to the owner with the result, not run. One specification of two of the cases.

**Prediction.** With the reworded text Sonnet writes 0 to 2 choices and several open lines in each, and at most one
of its three due-times specifications requires the refusal. With the lens text it writes choices, but I do not
know how many: Sonnet and Sol resolved the same instruction differently in the other session's rounds, so its base
may be well under Sol's 14 to 25.

**Limits known before the runs.** A Claude session started by the pilot runs in the real home, so it is shown the
account's own instructions, as Codex is shown its skills (section 19); the same in both waves. Minutes are not
compared with Sol's.

### Amendment 10, result (2026-11-21 08:12; ten spec-only runs with Sonnet as the writer, 08:03 to 08:10)

Status: firm for what was run: five specifications with each text, one of orders and of ticket assignment and three
of due times; the Claude host with `claude-sonnet-5-5` at high; every specification accepted on its first try, no
held-out mark, nothing put back by the script; 1.74 dollars for the reworded wave and 2.57 for the lens wave.

| Specification, text | Clauses | Use cases | request | implied | existing | choice | `Open:` lines | Minutes |
|---|---|---|---|---|---|---|---|---|
| orders, reworded | 21 | 4 | 18 | 2 | 1 | 0 | 9 | 1.0 |
| ticket assignment, reworded | 32 | 6 | 16 | 10 | 6 | 0 | 7 | 2.0 |
| due times 1, reworded | 22 | 6 | 12 | 5 | 3 | 2 | 12 | 1.4 |
| due times 2, reworded | 28 | 6 | 18 | 4 | 6 | 0 | 8 | 2.6 |
| due times 3, reworded | 22 | 6 | 12 | 3 | 6 | 1 | 6 | 1.6 |
| orders, lens | 39 | 7 | 23 | 4 | 2 | 10 | 0 | 1.7 |
| ticket assignment, lens | 79 | 13 | 24 | 19 | 24 | 12 | 0 | 3.2 |
| due times 1, lens | 57 | 9 | 20 | 11 | 17 | 8 | 0 | 3.1 |
| due times 2, lens | 66 | 9 | 21 | 12 | 21 | 12 | 0 | 2.6 |
| due times 3, lens | 80 | 13 | 28 | 16 | 27 | 9 | 0 | 3.5 |
| *Sol, reworded (rung 1)* | *26; 43; 30, 34, 34* | | | | | *0 in all* | *8; 7; 10, 8, 9* | |
| *Sol, lens (base table)* | *82; 151; 190, 170, 197* | | | | | *20; 14; 19, 25, 24* | *0* | |

The Sonnet rows are counted by the first word of each clause's `Source:` line; one clause of the lens specification
due times 1 has a `Source:` outside the four kinds (C-38, the runtime's own rule), so its row adds to 56 of 57. The Sol
rows are as recorded under "Rung 1, result" and in the base table; their other columns are not repeated here.

- **R11.1, the mechanism: holds.** The five reworded specifications write 0, 0, 2, 0 and 1 choice clauses and 9, 7,
  12, 8 and 6 open lines. The bar was at most 2 choices and at least one open line in each.
- **R11.2, the due-times start: none of the three requires the refusal.** One has a start with due times off, and
  a stop, leave the file holding them, and marks as open whether an operator must run a separate step instead (due
  times 1, C-11: "When the file is written. The loosest reading is that the file holds them after the service has
  started and stopped normally ... The requester decides if an operator has to run a separate step instead"). One
  states the request's sentence without a mechanism and adds that a start on a file release 1.4.0 has
  since written gives the missing ones (due times 2, C-20 and C-24). One states giving due times at start as what the
  request says (due times 3, C-8).
- **R11.3, the base.** With the lens text Sonnet writes 10, 12, 8, 12 and 9 choice clauses and no open line, in
  specifications of 39 to 80 clauses. None of its three due-times specifications requires the refusal either: all
  three give the missing due times at start, as clauses sourced to the request (C-28; C-26 and C-29; C-37).

**Predictions scored.** For the reworded text all held: 0 to 2 choices, several open lines, and at most one of three
due-times specifications requiring the refusal (none did). For the base I had said I did not know and that it might
be well under Sol's 14 to 25: it is 8 to 12.

**Findings.**

- **F34 (firm: ten specifications of a second model).** The reworded text takes the writer's own decisions out of the
  specification on Sonnet as it did on Sol: 3 choice clauses in five specifications against 51 with the lens text, 42
  open lines against none, 21 to 32 clauses against 39 to 80. Two of the three choices it did write, both on
  `overdue` values other than `true`, say the value is left unspecified, one adding that a test must not assert
  either way; the third keeps the existing audit and notification output and leaves recording `due` there open.
- **F35 (firm: six Sonnet specifications against five of Sol's; it narrows F24 and F30).** The due-times
  misreading is Sol's, not every model's. Sonnet reads "the tickets already in the production data file get due
  times" as giving them at start with either text: none of six specifications requires the refusal, where Sol's
  writers chose it four times in five with the two earlier texts. So what the reworded text repaired on due times is
  a decision one model family gets wrong. On Sonnet there was nothing to repair, and that case cannot show the
  text's worth there.

**What to watch.** Sonnet's reworded specifications restate even less existing behaviour than Sol's (1, 6, 3, 6 and
6 `existing` clauses; Sol's 1, 24, 13, 15 and 17), so the risk F31 named, a defect in existing behaviour that
nothing pins, is larger on Sonnet and is not measured.

**Is there enough to conclude?** For the question asked (does another model also stop deciding), yes. Not
established: anything about a product built or tests written on Sonnet. The cheapest next step would be one
test-strength cell, ticket assignment with its 27 planted defects, from the Sonnet reworded specification; its
sessions are priced and it takes about twenty minutes, so it is put to the owner and not run.

**Checked twice, and who decided what.** The readings above were made in the main session, at the owner's word
("Use this context session for any judgment calls that are material"). A Sonnet subagent copied the evidence,
recounted every cell of the table with a script of its own (all match) and searched the six due-times
specifications for a clause that refuses a start on a file without due times: none in any of the six.

**Limits.** One specification of two of the cases with each text. A Claude session started by the pilot runs in the
real home and is shown the account's own instructions, the same in both waves. Sonnet sometimes writes a `Source:`
line that names two kinds ("request; existing: ..."), which the count reads by its first word, and one clause of one
lens specification has a `Source:` outside the four kinds. Added refusals were not read here because Sonnet adds few
with either text (6, 4, 2, 3, 1 with the lens text; 0, 2, 0, 1, 1 with the reworded).

Evidence: `evidence/reworded-enrichment/` (`s1-*/` and `s1L-*/` with each run's `run.json` and `spec.md`;
`sonnet-specs-log.txt` and `.json`).

### Received from this session's fork: a suite is written against one product's answers (2026-11-21 08:18)

Status: received, not re-run here; the reading of what it does to R9.5 and F31 is mine.

The owner forked this conversation at 08:00 to ask whether Ratchet's stages can run at once, with a catch-up. That
session, "Ratchet (fork)", works in a worktree and branch of its own (`ratchet-parallel-6f54fb`, cut from this
branch at e16be4938; its commits 810cbe5135358b4614f2bf210f63699bae271789 and
164edda800ebbeac4eca1bdcc025357e5e469fde; its journal `docs/ratchet-parallel-journal.md`) and reads this
amendment's run folders without changing them.

**What it found**, with no model, by laying one run's frozen suite over another run's product (its `overlay.py`,
as `grade.py` does for a variant), on due times:

| Suite | On loop a's build | On loop b's build | On the correct reference |
|---|---|---|---|
| loop a's (42 items) | 39 in its exported copy; 41 at this run's own gate | 38 | 29 or 31 |
| loop b's (41 items) | 41 | 41 at its own gate | 29 or 31 |
| the test-strength cell's (39 items) | 31 | 31 | 35 |

> **Superseded 2026-11-21 09:10** (the fork's own correction; its commit
> d610919065c98e9eedcb96755362034b2e7848fb): four cells of this table were wrong. Its tool made its copies under
> the system's temporary folder, which on macOS is a symbolic link, and a test that watches `npm test` by file path
> then sees no test run. Measured again in a plain folder, with the copy a clone of the product's repository, the
> tool reproduces the runs' own gates (loop a's suite on its own build 41 of 42, loop b's 41 of 41) and gives:
>
> | Suite | On loop a's build | On loop b's build | On the correct reference |
> |---|---|---|---|
> | loop a's (42 items) | 41 | 39 | 30 |
> | loop b's (41 items) | 41 | 41 | 31 |
> | the test-strength cell's (39 items) | 32 | 32 | 35 |
>
> Its readings stand, it says: a suite carries between products that took the same answers, and loses 10 to 12
> items against the reference, all of them about how the product is driven or about its own tests.

(It gives the two loops' results on the reference as "29 and 31" without saying which is which.) Every cross
failure, it reports, is about how a test drives the product at an open point (one `RESPONSE_HOURS` setting against
four `DUE_HOURS_*` ones; how the data file is prepared) or about the product's own tests. None is about what a
clause asserts.

**What that does to the readings above.** R9.5 stands as it was read: no test asserts an answer to an open point. But
it said too little. A suite is written against one product, drives it through the answers that product took, and so
does not carry to another correct product that answered differently: a loop's suite fails 10 to 13 of its items on the
reference (*corrected 09:10: 10 to 12, by the table above*). R9.2 could not show this, because in a test-strength cell
the tests are written with the reference as the product in front of them, for every text alike. So F31's "removed most
of what rejected a correct product" holds for what a clause asserts and not for how its test reaches the product. With
the earlier texts the specification fixed a control's name and a correct product that named it otherwise failed; with
this text nothing fixes it, and the test takes it from the product at hand. A second correct product still needs the
plan's answers, or tests that find a product's controls from its documents.

**Two notes on the apparatus.** The fork's exported copy of loop a's own build counts 39 of 42 where this run's
gate counted 41 (C-33 and U-8, both about `npm test`): not examined, and the same kind of difference as loop b's
`suite` check in section 20, a copy without Git history. And for about a minute (08:03 to 08:04:43), before it knew
it was the fork, it had left one untracked file in this worktree: the launch guards here read a clean tree at
08:03:08 and at 08:06:59, and no commit of this branch holds it.

> **Superseded 2026-11-21 09:10:** "a copy without Git history" was my guess at the 39 against 41 and it was wrong.
> The fork found the cause, the temporary folder above; in a plain folder its copy counts 41 of 42, as the gate
> did. `grade.py strength` makes its copies under the run folder and is not affected. Loop b's `suite` check in
> section 20 is a different case, read there in the test's own output (`git archive` of release 1.4.0).

**The fork's first run, received 09:08** (its commit d610919065c98e9eedcb96755362034b2e7848fb, its journal section
6; the owner's word to it was "Yes, run it"; Codex `gpt-6.2-sol` at high; not re-run here). Two test sessions
started from this amendment's two loop specifications and plans and the starting product, with no build present.
Their suites pass 42 of 42 and 41 of 41 on the two loop builds, which they never saw, and on each other's. It
had predicted 4 to 10 failing. The sessions were not cheaper (15.9 and 19.7 minutes against 16.7 and 13.4, on a
loaded machine). Not measured: whether such a suite catches the planted defects.

What that adds to the reading above, in my words: it is the other half of the same thing. A suite fails on a
product that took other answers, and passes on a product it never saw that took the same ones. So with the
reworded text the plan is where a product's answers to the open points are fixed. What a second product, or a
test written somewhere else, has to share is those answers and the names the plan fixes: not the whole plan, not
the specification alone and not the build. The fork, asked whether this states its finding, agreed and added that
narrowing, and that it is shown for two sessions on one request with one model, whose blind sessions took every
name that starts or configures the product from the plan, the specification or the starting documents.

### Amendment 11, 2026-11-21 10:52: Sonnet at medium against Sonnet at high, the small step first, then one test-strength cell at each (registered before any run)

Owner, 10:49, after the test-strength cell on Sonnet had been described at their request: "Can we run this at Sonnet
medium to see if we get different behavior than we would if we ran this at high?" My reading: run that cell at
both efforts and say whether what Sonnet does differs between them. Medium is also what this account's Sonnet
sessions use when no effort is given, so it is the setting a day-to-day run would have.

**How the effort reaches a session.** The harness's Claude host puts `--effort <level>` on the command line
(`test/shiploop_e2e/hosts.py`), and the installed `claude` accepts low, medium, high, xhigh and max there. Amendment
10's ten runs went out with `--effort high`. A correction to a limit stated there: I wrote that a Claude session
started by the pilot "runs in the real home and is shown the account's own instructions". The launcher also passes
`--setting-sources project,local`, which leaves the user-level settings out; what else that leaves out I have not
checked by a run. The limit was stated more broadly than I knew.

**Rungs.**

| Rung | What runs | About |
|---|---|---|
| 1, small | the spec stage alone with the reworded text at `--effort medium`: `sm-orders`, `sm-ticket-assignment`, `sm-due-times-1`, `-2`, `-3`; compared with amendment 10's five at high | 3 minutes |
| 2 | the test-strength cell on ticket assignment at each effort, each from that effort's own specification (`--spec-from`), the correct reference laid in as the build, plan and heavy test pass at that effort, `--stop-after tests`, then `grade.py strength`: `p1S-ticket-assignment-high` (from `s1-ticket-assignment`) and `p1S-ticket-assignment-medium` (from `sm-ticket-assignment`) | 20 minutes and the grading |

Rung 2 runs whatever rung 1 shows, unless the medium ticket-assignment specification is not accepted by the script.
Each session of rung 2 is capped at 6 dollars, each of rung 1 at 3.

**Readings.**

- **R12.1, what medium writes.** *Different* if any of the five medium specifications writes more than 2 choice
  clauses or no `Open:` line (R11.1's bar, which all five at high met), or if any of the three due-times ones
  requires that an enabled start refuse a data file without due times (none at high did). Otherwise the same on
  this reading. Reported beside it: clauses, `existing` clauses, minutes and cost.
- **R12.2, strength at each effort.** Calibrated defects caught of 27: *kept* at 25 or more (Sol with this text:
  26). Reported: clauses failing on the correct reference, items the second correct delivery fails beyond it, which
  defects are missed and of what kind, minutes and cost.
- **R12.3, medium against high.** *Different* if the two caught counts differ by 2 or more, or if one is kept and
  the other is not. Otherwise no difference shown.

**What it cannot show.** One run a cell at each effort, and no measure of Sonnet's run-to-run spread, so one defect
either way is nothing. Whole cells are compared (specification, plan and tests all at one effort), so a difference
would not say which stage made it. Nothing is built on Sonnet. If a cell is not kept, it does not say whether the
short specification or Sonnet's way of writing tests is the cause: the lens text on Sonnet in the same cell would,
and it is not registered here.

**Predictions.** The medium specifications meet R11.1's bar and are a little shorter than the high ones. Both cells
are kept, and medium catches as many as high or one fewer. I hold these loosely: this pilot has no record of
Sonnet writing a plan or tests.
