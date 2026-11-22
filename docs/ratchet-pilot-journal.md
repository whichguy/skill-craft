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

> **Qualified 2026-11-21 13:17, on the fork's later results** (received 13:15, not re-run here; its journal
> sections 13 and 15, its commits 6e1d1d4779bf76e8893962439e985166459ec673 and
> 5212365fe6b999d08c26b310a267863043874aac on its own branch; Codex `gpt-6.2-sol` at high). The reading above holds
> for its three small cells and needs a limit once the product has a rich page.
>
> - *Battleship* (a new app with a page, from an empty folder). A suite written with no build and nothing to run on
>   passes 28 of 28 when it first meets the build, and catches 32 of 51 seeded faults against 31 for a suite written
>   beside the build. By this pilot's first spread measure (F38) that is the same.
> - *Grokbot-local*, from this pilot's `p3R-grokbot-local` specification, plan and first build, which it read and
>   did not change. The suite written beside the build passes 115 of 115. The suite written with no build passes 4
>   of 115 at first meeting, and all 111 failures have one cause in the suite's own code: it works out a button's
>   name from the element's whole text, hidden parts included, where the build puts an avatar letter and an arrow
>   inside each button and marks both hidden. The name the specification asks for is there; the suite does not find
>   it. No assertion is wrong and the product is right.
>
> So besides the plan's answers and the names it fixes, a test writer facing a rich page needs something to try
> its page-reading code on. Its check of how much that one correction unlocks was still running when this was
> received.
>
> **Sharpened 2026-11-21 13:54, on the fork's catch-up result** (received 13:52, not re-run here; its journal
> section 16, its commit 50d7f3ced02a5192311a77332dc1fed190bcb5d5 on its own branch). The build-less Grokbot suite
> passes 4 of 115 as written, 87 with the function that reads an element's name corrected, 111 once an action
> waits for the page to answer it, and 112 once the driver's window counts as focused. So of the 111 items failing
> at first meeting 108 were execution, mended by three corrections in the suite's two execution files (23, 97 and
> 37 lines of diff), and 3 are the tests' own expectations (a bot name written into a test, a list order assumed,
> a two-window case the specification does not ask for). None is the product. The last two corrections and the
> three readings are a Sonnet subagent's, under a rule that only the execution files may change, checked by the
> fork.
>
> What it adds. The design was not what was missing: both suites use the same 46 labels and all 46 are in the
> specification, and the build-less writer's own list of assumptions names none of the three faults. What the
> tests assert held at this size too (112 of 115 expectations as written before any code). What did not hold is
> the code that drives a rich page, which the writer had nothing to try on. On time: the build took 15.0 minutes,
> the most that writing the tests beside it could save, and the catch-up took about half an hour of work after a
> 30-minute failing pass.

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

### Amendment 11, result (2026-11-21 11:12; Sonnet at medium against Sonnet at high)

Status: firm for what was run: five specifications at medium beside the five at high of amendment 10; one
test-strength cell on ticket assignment at each effort; one run a cell; Claude host, `claude-sonnet-5-5`; every
specification accepted on its first try; no held-out mark in any session; 1.48 dollars for the five medium
specifications, 2.03 for the high cell's two sessions and 1.05 for the medium cell's.

**Table 1. The specifications** (each cell is medium / high; the high ones are amendment 10's reworded row).

| Specification | Clauses, medium / high | Use cases | choice | `Open:` lines | `existing` | Seconds to write |
|---|---|---|---|---|---|---|
| orders | 19 / 21 | 4 / 4 | 1 / 0 | 7 / 9 | 0 / 1 | 39 / 61 |
| ticket assignment | 22 / 32 | 5 / 6 | 1 / 0 | 8 / 7 | 2 / 6 | 47 / 118 |
| due times 1 | 19 / 22 | 6 / 6 | 1 / 2 | 7 / 12 | 1 / 3 | 56 / 84 |
| due times 2 | 20 / 28 | 4 / 6 | 1 / 0 | 8 / 8 | 3 / 6 | 45 / 153 |
| due times 3 | 16 / 22 | 6 / 6 | 1 / 1 | 6 / 6 | 1 / 6 | 51 / 95 |

**Table 2. The test-strength cell on ticket assignment** (Sol's two rows are as recorded under "Rung 3, result").

| Cell | Clauses / use cases tested | Clauses failing on the correct reference | Second correct delivery, beyond the reference | Defects caught of 27 | The one missed | Caught only through the product's own tests | Minutes (enrich + the rest) | Cost |
|---|---|---|---|---|---|---|---|---|
| Sonnet medium | 22 / 5 | 0 | 5 | 26 | `update-rejects-resolved` | 5 | 5.8 (0.8 + 5.0) | 1.37 dollars |
| Sonnet high | 34 / 6 | 2 | 8 (5 clauses, 3 use cases) | 26 | `update-rejects-resolved` | 3 | 14.2 (2.0 + 12.3) | 2.45 dollars |
| Sol high, reworded | 44 / 9 | 3 | 3 | 26 | `update-rejects-resolved` | 1 | 26.9 (3.8 + 23.1) | not priced |
| Sol high, lens | 153 / 11 | 13 | 15 | 26 | `cli-no-assignee` | 0 | 38.0 (7.0 + 31.0) | not priced |

*Added 2026-11-21 11:31, after the session "Spec elaboration" found two figures here unexplained:* table 1
counts each specification as its spec stage wrote it, and table 2 counts the clauses tested, after the plan stage.
In the high cell the plan stage appended two clauses (C-33 and C-34, both passing on the reference), so its 32
became 34. In the medium cell it appended none, so 22 stands in both tables. Sol's 44 is the 43 of rung 1's table
and the one its plan appended (C-44).

**The readings of amendment 11.**

- **R12.1, what medium writes: the same on this reading.** Every medium specification writes one choice clause and 6
  to 8 open lines; none of the three due-times ones requires the refusal. What differs is size and time: 16 to 22
  clauses against 21 to 32, under a minute each, and still less existing behaviour restated (0 to 3 `existing`
  clauses against 1 to 6). *Qualified 2026-11-21 13:11 (amendment 12, F38):* on ticket assignment five medium
  specifications written from this text hold 1 to 5 `existing` clauses, so 2 against 6 on that case is not shown
  to be a difference.
- **R12.2, strength at each effort: kept at both.** 26 of 27 at each; the bar was 25.
- **R12.3, medium against high: no difference shown.** The same count and the same defect missed.

**What did differ, reported.** At high Sonnet wrote more (34 clauses against 22), took two and a half times as long
(14.2 minutes against 5.8) and cost 1.8 times as much (2.45 dollars against 1.37). Its tests fail on the correct
reference for two clauses: the request's own "has tests" clause (C-32) and an implied refusal the reference does not
make (C-5, "A name that is not a single line of text is refused": the reference answers 200 to an assignee
holding a control character where the clause says 400, the added refusal of F28 again). Medium's tests fail on
none. The second correct delivery fails 8 of the high cell's items against 5 of the medium cell's.

**How much of the catch is the suite's own** (reported, not registered). Some clauses, taken from the request ("the
existing tests must still pass"; "npm test runs the new tests"), are tested by running the product's own test suite.
Defects caught only through them: 5 of 26 at medium (22 clauses), 3 of 26 at high (34), 1 of 26 for Sol with this
text (44), none for Sol with the lens text (153). So the shorter the specification, the more of the existing
behaviour is covered by the product's tests and not by tests the session wrote. That is the risk amendment 10
named, visible and small, and it follows the specification's length across four cells.

*Qualified 2026-11-21 13:11 (amendment 12: F38 and "The first reading's instrument").* Three runs of the shortest of
these four cells give 5, 3 and 0 on this count, the whole range of the four, and the count leaves out clauses it
should take in. Four single runs therefore do not show that it follows the specification's length.

**Predictions scored.** All three held: the medium specifications meet the bar and are a little shorter; both cells
are kept; medium catches as many as high.

**Findings.**

- **F36 (firm at this size: three cells, two models, two efforts).** What the shorter specification costs is the same
  one defect each time. Sol at high, Sonnet at high and Sonnet at medium all catch 26 of 27 and all miss
  `update-rejects-resolved`, a defect in existing behaviour that none of the three specifications pins and that the
  product's own tests do not catch. The lens text on Sol, with about a hundred `existing` clauses, caught it and
  missed another. *Extended 2026-11-21 13:11 (amendment 12):* three runs of the medium cell caught 26, 24 and 26,
  so 26 is not a constant of the text; the defect is missed by eight of nine cells under it.
- **F37 (one run a cell; no measure of spread).** On Sonnet the effort changed length, time and cost, not the
  registered outcomes. Medium wrote the shortest specification of any cell (22 clauses), caught as many defects,
  rejected the correct reference on nothing, and did it in 5.8 minutes for 1.37 dollars, against 14.2 minutes and
  2.45 dollars at high and 26.9 minutes for Sol at high. *Spread measured 2026-11-21 13:11 (amendment 12, F38):*
  three runs at medium caught 24 to 26.

**Received with this round.** The session "Spec elaboration" pointed out that the stage frame already told the test
session that a test "must pass whichever reasonable answer a build took" at an open point, and that the fork's
overlays show the suites did not manage it across builds that answered differently. That is a duty written into a
prompt that the sessions did not meet, as F22 was.

**Is there enough to conclude?** For the owner's question (does Sonnet behave differently at medium than at high),
yes on these readings: it does not, and medium is cheaper. Not established: Sonnet's run-to-run spread; any case but
ticket assignment; anything built by Sonnet; which stage would be sensitive to effort if one were.

**Checked twice, and who decided what.** The readings against the registered rules were made in the main session; a
Sonnet subagent copied the evidence, recounted the figures with a script of its own and drafted this subsection from
the facts given to it. Its recount matches every count; it found two roundings of mine, corrected above (84
seconds for one specification, 14.2 minutes for the high cell, where the owner had been told 85 and 14.3). It also
searched the three medium due-times specifications for a clause that refuses a start on a file without due times:
none.

**Limits.** One run a cell and no measure of spread, so one defect either way would have been nothing. Whole cells
are compared. The calibrated defects are partly caught through the product's own tests, for every text. The gradings
ran one after another with no other run of mine live; the medium cell's grading overlapped the high cell's test
session.

Evidence: `evidence/reworded-enrichment/` (`sm-*/`, `p1S-ticket-assignment-high/` and `-medium/`,
`sonnet-effort-specs-log.txt` and `.json`; and `spec-final.md` added to the five `p1R-*` and `p3R-*` folders, whose
records had no final specification).

## 22. Amendment 12, 2026-11-21 12:02: one question from ShipLoop's own catalog, on preserved behaviour, answered in the specification or in the plan (registered before any run)

Owner, 11:39: "how much we might be able to leverage existing ShipLoop reference material in Ratchet ... If we know
key categories or key questions that need to be considered, that might actually help give us better breadth and
coverage (possibly even better depth) for when we elaborate the incoming prompt or we're trying to elaborate the
spec." He also asked that this be coordinated with the session "Spec elaboration". Asked whether to start the first
small experiment (six cells on Sonnet at medium, about 25 minutes and 9 dollars), he answered at 11:59: "Yes, start
it".

**What was found before designing anything.**

- *In ShipLoop's text.* A helper listed, with quotes, every place ShipLoop tells a session what to consider; I read
  the passages. Two lists of this kind are in text a session is handed: the intake's twelve key questions K1 to K12
  (`skills/shiploop/scripts/shiploop_prompts.py`, `DUTIES["intake"]` item 9), each with a route (inspect, research,
  experiment, default, person), a default and what it blocks; and the plan's fifteen concerns
  (`skills/shiploop/scripts/shiploop_concerns.py`), each a row or "applies: no" with a reason. The reference guides
  hold more (an audit of event families, a non-functional list).
- *From the session "Spec elaboration"* (its journal, section 38, and its answers to five questions; its work, not
  re-run here). Real builders do not open the guides: `references/behavioral-requirements.md` was opened in none of
  26 Sol and none of 9 Sonnet deliveries, and in nearly all sessions of its bench, where the folder's first lines
  point at them. K1 to K12 has run at intake in every real delivery since 2026-10-31, and on Sol its routes collapse
  to "inspect": default and person go unused and 26 real specifications hold no open gap. Of its 89 checklist items
  two outside sorters call 74 needed and 4 beyond the request, all four operator features; K1 to K12 has no operator
  question. A category list must not be judged by a covered count over the specification, which it always wins.
  It checked this amendment's reasoning before the owner saw it and corrected one sentence of mine (both long
  specifications caught the existing-behaviour defect, not only the lens one).
- *From this pilot.* What the short reworded specification gives up is existing behaviour: three cells on two
  models miss the same defect, and catches that rest only on the product's own tests rise as the specification
  shortens (F36; 0, 1, 3, 5). Clauses that restate existing behaviour almost never reject a correct product (F25),
  while the writer's own decisions do (F26, F28). The owner told that session he wants fuller specifications. So
  fuller should mean more existing behaviour pinned and more points raised, with nothing decided by the writer.

> *Added 2026-11-21 13:54, after the runs; the registration above and below is left as it was registered.* The
> series 0, 1, 3 and 5, cited in the bullet above and in R13.1, did not hold up as a trend: three runs of the
> shortest of those four cells give 5, 3 and 0 on the same count (this amendment's result: F38 and "The first
> reading's instrument"). The script does reproduce the four numbers; what is qualified is the reading that they
> follow the specification's length. Pointed out by the session "Spec elaboration" when it checked the result.

**The ladder.** Three rungs; only the first is registered here.

1. One question, K2 word for word: "Scope and preserved behaviour: what is in and out, and what existing behaviour
   must not change?", answered in writing by the spec stage or by the plan stage, each answer a clause sourced to a
   file, or an open point.
2. Not registered: all twelve questions, each ending as a clause with its source, an `Open:` line, or "does not
   apply" with a reason that can be checked; no choice clause.
3. Not registered: the fifteen concerns as rows in the plan.

**The text** (`ratchet.py`: `PRESERVE_SPEC`, `PRESERVE_PLAN`, chosen by `--preserve spec` or `--preserve plan` with
`--enrich reworded`). Only the question is ShipLoop's. In the specification text it sits above "How to get there",
outside the questions that text calls aids to thinking, and says the answer is written: each thing that must not
change is a clause "stating what the product does today, with `Source: existing: <the file that shows it>`", and
what the repository does not settle is an `Open:` line. In the plan text it asks for a sixth section, `## Preserved
behaviour`, and for a clause at the end of the specification wherever the specification has none. With the option
off both packets render byte for byte as before (checked against the committed script); the standing self-test
passes for all three settings; the paragraph appears only in the prompt of the stage it is set for.

**Cells.** The test-strength cell on ticket assignment (spec, plan, the correct reference laid in as the build, heavy
test pass, `--stop-after tests`, then `grade.py strength`), each one run from the request, Claude host,
`claude-sonnet-5-5` at medium, 6 dollars a session at most:

- `q-base-1`, `q-base-2`: the reworded text as it is. With amendment 11's medium cell that makes three baseline runs.
- `q-spec-1`, `q-spec-2`: `--preserve spec`.
- `q-plan-1`, `q-plan-2`: `--preserve plan`.

**Readings.**

- **R13.1, the first reading: catches that rest only on the product's own tests.** Defects caught only through
  clauses that are checked by running the product's test suite (`by_source.py`, `RUNS_PRODUCT_TESTS`, now counted by
  the script; it reproduces 0, 1, 3 and 5 for the four cells on record). A placement *helps* if both of its runs
  are below the lowest of the three baseline runs. It *does not* if either is at or above the highest. Otherwise
  not shown.
- **R13.2, strength.** Calibrated defects caught of 27, kept at 25 or more, and whether `update-rejects-resolved` is
  caught, a run at a time. One defect in one run is nothing; caught in both runs of a placement and in no baseline
  run is worth saying.
- **R13.3, harm.** Clauses failing on the correct reference: *no harm shown* if neither run of a placement exceeds
  the worst baseline run by more than 2. Choice clauses written stay at 2 or fewer in each.
- **R13.4, spread.** For the three baseline runs, the range of each reading: this pilot's first measure of
  run-to-run spread, on Sonnet at medium.
- Reported: clauses and `existing` clauses written, clauses the plan added, items the second correct delivery fails
  beyond the reference, minutes and cost.

**Predictions.** Baseline: 25 to 27 caught, 3 to 6 resting only on the product's own tests. In the specification:
`existing` clauses rise from 2 to between 8 and 20, the first reading falls to between 2 and 4, the missed defect is
caught in at most one of two runs, failing clauses stay at 0 to 2. In the plan: 3 to 8 clauses added, a smaller
effect, most likely not shown.

**Limits known before the runs.** One case, two runs a placement, one model at one effort. The first reading is a
word match. Only the question is ShipLoop's; the sentences around it are mine and were written knowing which
defect the short specifications miss, which is why the question was taken unchanged and the sentences name no
behaviour. Every request in this pilot is precise (180 to 280 words); nothing here reads the vague request the owner
has in mind, for which this pilot has no instrument yet.

### Amendment 12, result (2026-11-21 13:11; the question on preserved behaviour, in the specification or in the plan)

Status: firm for what was run: six cells on ticket assignment, one run each, read beside amendment 11's medium cell
as the third baseline run ("earlier" below); Claude host, `claude-sonnet-5-5` at medium; every specification accepted
on its first try; no held-out mark in any session; nothing put back by the script; 8.58 dollars for the eighteen
sessions. The six cells ran at the same time (12:02 to 12:22) and their gradings overlapped (12:22 to 13:01), so
minutes are not compared between cells.

**Table 1. The specifications as the spec stage left them.** The plan cells get the question in the plan stage
only, so their specifications are written from the baseline text: five specifications without the question, two
with it. "`existing` first" counts clauses whose source begins with that word, which is how `by_source.py` sorts
them; "`existing` anywhere" counts clauses whose source cites an existing file at all.

| Run | The question | Clauses | Use cases | `existing` first | `existing` anywhere | choice | `Open:` | Seconds |
|---|---|---|---|---|---|---|---|---|
| earlier | none | 22 | 5 | 2 | 8 | 1 | 8 | 47 |
| `q-base-1` | none | 21 | 5 | 1 | 10 | 0 | 9 | 54 |
| `q-base-2` | none | 24 | 5 | 5 | 10 | 1 | 10 | 47 |
| `q-plan-1` | none yet (it comes in the plan) | 20 | 6 | 2 | 8 | 0 | 6 | 63 |
| `q-plan-2` | none yet (it comes in the plan) | 22 | 6 | 5 | 12 | 2 | 8 | 49 |
| `q-spec-1` | in the specification | 21 | 6 | 4 | 9 | 0 | 9 | 51 |
| `q-spec-2` | in the specification | 22 | 6 | 5 | 15 | 0 | 8 | 58 |

**Table 2. The graded cells.** "Plan added" is the number of clauses the plan stage added; "Fails on reference" the
clauses failing on the correct reference; "Second delivery" the items the second correct delivery fails beyond
those; "Caught" is of the 27 planted defects; "First reading" is R13.1 as the script counts it.

| Cell | Clauses / use cases | Plan added | Fails on reference | Second delivery | Caught | First reading | Dollars |
|---|---|---|---|---|---|---|---|
| earlier | 22 / 5 | 0 | 0 | 5 | 26 | 5 | 1.37 |
| `q-base-1` | 21 / 5 | 0 | 0 | 5 | 24 | 3 | 1.18 |
| `q-base-2` | 24 / 5 | 0 | 0 | 4 | 26 | 0 | 1.18 |
| `q-spec-1` | 21 / 6 | 0 | 0 | 4 | 25 | 4 | 1.44 |
| `q-spec-2` | 22 / 6 | 0 | 0 | 5 | 25 | 2 | 1.93 |
| `q-plan-1` | 25 / 6 | 5 | 1 (C-20) | 3 | 23 | 0 | 1.36 |
| `q-plan-2` | 26 / 6 | 4 | 0 | 3 | 26 | 0 | 1.48 |

| Cell | Defects missed |
|---|---|
| earlier | `update-rejects-resolved` |
| `q-base-1` | `update-rejects-resolved`, `backoff-linear`, `validate-renamed` |
| `q-base-2` | `update-rejects-resolved` |
| `q-spec-1` | `update-rejects-resolved`, `filter-after-page` |
| `q-spec-2` | `update-rejects-resolved`, `filter-after-page` |
| `q-plan-1` | `default-limit-changed`, `resolved-template-replaced`, `backoff-linear`, `validate-renamed` |
| `q-plan-2` | `update-rejects-resolved` |

**Table 3. The six defects planted in what the product already did, and the items that caught each.** `+` marks a
clause the plan stage added. The other 21 defects are in the new feature.

| Defect | earlier | `q-base-1` | `q-base-2` | `q-spec-1` |
|---|---|---|---|---|
| `update-rejects-resolved` | missed | missed | missed | missed |
| `default-limit-changed` | C-22 | C-21 | C-23, C-24, U-5 | C-21 |
| `resolved-template-replaced` | C-22 | C-21 | C-23, C-24, U-5 | C-20, C-21, U-6 |
| `audit-not-saved` | C-22 | C-21 | C-22, C-23, C-24, U-5 | C-21 |
| `backoff-linear` | C-21 | missed | C-23 | C-20 |
| `validate-renamed` | C-21 | missed | C-23 | C-20 |

| Defect | `q-spec-2` | `q-plan-1` | `q-plan-2` |
|---|---|---|---|
| `update-rejects-resolved` | missed | C-23+ | missed |
| `default-limit-changed` | C-18, C-22 | missed | C-21, C-22 |
| `resolved-template-replaced` | C-22, U-6 | missed | C-21, C-22, U-6 |
| `audit-not-saved` | C-14, C-22 | C-25+ | C-21, C-22, C-25+, U-6 |
| `backoff-linear` | C-21 | missed | C-21 |
| `validate-renamed` | C-21 | missed | C-21 |

**The readings of amendment 12.**

- **R13.1, the first reading: not shown for either placement, and the count did not hold up as an instrument.** By
  the script, defects caught only through clauses it takes as running the product's own tests: baseline 5, 3 and 0;
  with the question in the specification 4 and 2; in the plan 0 and 0. The rule asked for both runs of a placement
  to be below the lowest baseline run. The lowest is 0, so no placement could meet it; none is at or above the
  highest, 5. Not shown. The registered count stands as counted and no other count replaces it here; what is wrong
  with it is under "The first reading's instrument".
- **R13.2, strength: not shown.** Caught of 27: baseline 26, 24 and 26; in the specification 25 and 25; in the plan
  23 and 26. The bar of 25 is missed by one baseline run and one plan run, so it separates nothing.
  `update-rejects-resolved` is caught once, in the first plan run, by a clause the plan stage added; the rule counts
  one catch in one run as nothing.
- **R13.3, harm: none shown by the rule.** Clauses failing on the correct reference: 0 in every run but the first
  plan run, which has 1, inside the allowance of 2 over the worst baseline run. That one is the request's own "has
  tests" clause (C-20), not a clause the plan added. Choice clauses: 0 to 2 in each specification.
- **R13.4, the spread of three baseline runs** (one text, case, model and effort): 24 to 26 defects caught; 0 to 5
  on the first reading; no clause failing on the reference in any; 4 to 5 items the second correct delivery fails;
  21 to 24 clauses, 1 to 5 of them `existing`; 1.18 to 1.37 dollars.

**The first reading's instrument.** Three things are wrong with the count, found by reading the graded runs.

- *It matches words, and the wording varies.* Every run has the same two clauses from the request: the existing
  tests still pass as they are, and the new tests run under `npm test`. The script takes a clause as one of the two
  when its text holds "npm test", "node:test", "existing tests" or "tests in `test/`". Two runs word the first of
  them "Every test in `test/` that exists now passes" (`q-base-2` C-23, `q-plan-2` C-21), which matches none of
  those, so the script reads 0 for both. With those two clauses taken in, the helper's recount gives 2 and 3.
- *It counts a clause whole.* The test of "existing behaviour is unchanged" runs the product's tests in some runs
  and in others also makes requests of its own (`q-base-2` C-23 creates, changes, pages and resolves tickets
  itself). The grading records which clause failed, not which of its tests, so "caught through the product's own
  tests" cannot be told from "caught by a test the session wrote" inside such a clause.
- *Across three runs of one text it ranges from 0 to 5*, the whole range of the four cells (0, 1, 3 and 5) from
  which amendment 11 read that it follows the specification's length. That sentence is qualified in place.

**What moves the count of 27 on this case** (reported). Twenty-one defects are in the new feature and six in what
the product already did. Five runs catch all 21; the two specification runs both miss `filter-after-page`. Of the
six, `update-rejects-resolved` is caught only by a clause that says a resolved ticket can still be changed, which
the product's own tests do not check. The other five are caught through the request's two clauses where their
tests work, and Table 3 shows where they do not:

- `q-base-1` (24) and `q-plan-1`: nothing in their suites compares `test/` with the base commit, as the suites of
  the five other runs do, so the two defects that edit a base test along with the code (`backoff-linear`,
  `validate-renamed`) pass.
- `q-plan-1` (23), besides: **its runs of the product's tests run nothing.** Both are started from inside the
  acceptance run (`node --test test/` and `npm test`) with the environment as it is. Node's test runner marks its
  children with `NODE_TEST_CONTEXT`, and a `node --test` started with that mark set exits 0 without running a test.
  Checked on a scratch copy of one defect tree (`default-limit-changed`, Node 26.12.1): started plainly,
  `node --test test/` exits 1 with 3 of 121 tests failing; with the mark set it exits 0 having printed only a
  warning that it skipped the files; `npm test` likewise. That loses `default-limit-changed` and
  `resolved-template-replaced`, and would have lost `audit-not-saved` but for a clause the plan added. The other
  six runs drop the mark in at least one nested run and catch all three there; in two of them (the earlier
  baseline's C-21, `q-spec-1`'s C-20) one nested run keeps the mark and runs nothing, and the other clause runs the
  tests for real. A heavy test pass against a correct build cannot notice: a run of nothing and a run of 121
  passing tests both exit 0. This run's "has tests"
  clause also fails on the reference (its test looks in the new test files for words about the command line that
  the reference's file does not use), so it counts for nothing either way.
- The two specification runs (25 and 25): `filter-after-page` cuts the page before it filters, so a filtered page
  can come back short while the pages together still hold the right tickets. Both specifications say of the new
  filter "paged as before", as the other five do. One suite never pages the filtered listing with a limit; the
  other asks for a page of two where the agent's tickets are the first two, which the defect also returns in full.
  The question was in the specification's prompt only and the clause is worded as elsewhere, so no path from the
  question to the miss is visible, and two runs cannot tell chance from an effect. It is recorded because it is
  both runs of one placement and none of the other five.

So on this case the count moves with how the test session treats two clauses of the request, and by at most one
defect with what the specification says of existing behaviour.

**What the question produced** (reported).

- *In the plan.* Both plans hold the section asked for, `## Preserved behaviour`, with 14 and 10 entries. All but
  the last of each name the file that shows the behaviour (13 and 9); the last lists what the repository does not
  settle (whether `list --raw` may gain a column, whether `show` prints the assignee) with the answer the plan
  takes. No other plan has such a section. The plan stage then added 5 and 4 clauses, 8 of the 9 sourced
  `existing`; none fails on the reference. In `q-plan-1`, whose runs of the product's tests run nothing, two added
  clauses are the only catch of a defect: C-23, "A resolved ticket can still be patched; only assignment is refused
  for resolved", catches `update-rejects-resolved`, which the other eight ticket-assignment cells graded under the
  reworded text miss (five of these six, amendment 11's two on Sonnet, and Sol's at high); C-25 (`show` and the audit
  entries print as before) catches `audit-not-saved`. In `q-plan-2` no added clause is a sole catch.
  One of the nine decides something new under an `existing` source. C-24 of `q-plan-1`, "A data file whose ticket
  carries an unusable assignee is refused at load", cites the loader's strictness for a field that did not exist.
  The reference does refuse; the second correct delivery starts, and fails the clause.
  The plan session took 126 and 118 seconds and 52 and 50 cents, against 93 to 111 seconds and 41 to 50 cents for
  the five plans written without the question.
- *In the specification.* No countable trace: 21 and 22 clauses, 4 and 5 `existing` by first word and 9 and 8 open
  lines, against 20 to 24, 1 to 5 and 6 to 10 for the five specifications written without the question. Both
  answer inside the one clause every specification has (C-20 "Existing behaviour is unchanged", C-21 "What the
  service already does keeps working": a list of what stays), not with a clause for each thing. One of the two
  cites an existing file in 15 clauses, against 8 to 12 elsewhere, and writes one clause on what stays (C-18: the
  limits and the default page size) that catches `default-limit-changed` by a test of its own.

**Predictions scored.** Baseline, "25 to 27 caught, 3 to 6 on the first reading": one of the two new runs is outside
each (24 caught; 0 by the script). In the specification, "`existing` clauses rise to between 8 and 20": wrong, 4
and 5; "the first reading falls to between 2 and 4": 4 and 2, with the baseline at 5, 3 and 0, so no fall; "the
missed defect caught in at most one run": held, in neither; "failing clauses 0 to 2": held, none. In the plan, "3
to 8 clauses added": held, 5 and 4; "a smaller effect, most likely not shown": held.

**Findings.**

- **F38 (firm for what was run; this pilot's first measure of run-to-run spread).** Three runs of one text on one
  case, model and effort differ by two defects caught (24, 26, 26), by five on the first reading and by four
  `existing` clauses. At one run a cell a difference of that size between two texts is not a difference. Two
  sentences of amendment 11 that rested on single runs of that size are qualified in place.
- **F39 (firm for what was run: two runs a placement).** A question taken from ShipLoop's catalog is answered when
  the stage is given a place to put the answer, and leaves no trace when it is one more instruction in the text.
  In the plan, with a section to fill, both runs list what must not change with the file that shows it and add 4
  to 5 sourced clauses. In the specification, with no section, both write what the five specifications without
  the question write. The placements differ in stage and in form together; which of the two decides is not
  separated. It agrees with what the session "Spec elaboration" read in real deliveries (the guides are not opened;
  on Sol the intake's routed questions leave no open gap on record). *Qualified 2026-11-21 16:55 (section 25):*
  "leaves no trace" says too much. Both specifications written with the bare instruction did answer, inside the one
  clause on existing behaviour, and one cited existing files in 15 clauses. What was missing is a separate answer
  and any consistent change in the clauses. ShipLoop's fifteen plan concerns already have
  the form that was answered here: a row, or "applies: no" with a reason.
- **F40 (not shown, and why this case cannot show it).** Neither placement moved a registered reading. On this
  case none could have by more than one defect: of the 27, one is caught only by a clause on existing behaviour,
  and the rest of the count turns on the test session's handling of two request clauses. That one defect was
  caught once, by a clause the question produced. By the registered rule that is nothing; it is recorded as the
  intended mechanism seen once in two runs.
- **F41 (one clause of nine; the harm F26 and F28 describe).** Asking what must not change let one decision in
  under an `existing` source: an existing rule carried over to a new field. The reference agrees with it and
  another correct delivery does not.
- **F42 (firm; a hazard of the apparatus and of any check written this way).** A check that runs the product's
  tests from inside a test run passes without running them unless it drops the runner's mark from the child's
  environment. One of seven sessions did not, in either of its checks, and lost two defects by that alone (a third
  was saved by a clause the plan's question added); two more did not in one check and were covered by the other.
  A check that also requires some test to have run is safe from it; three of the seven sessions wrote one, reading
  a count of tests from the output. No packet of this pilot asks for it, and the gate applies that rule only to its
  own commands.
- **F36, extended.** `update-rejects-resolved` is now missed by eight of the nine ticket-assignment cells graded
  under the reworded text, on two models; the ninth catches it by a clause the plan's question added. "26 of 27"
  is not a constant of the text (F38); the missed defect is.

**Is there enough to conclude?** For this rung, yes, and it ends here: the question is answered where there is a
section to fill and not where there is none; neither placement moved a reading; on this case no placement could
move one by more than a defect. Not established: whether pinning existing behaviour catches more defects (the pool
holds one that can show it); whether the section or the stage is what gets the question answered; anything on Sol,
on another case, or for a vague request. More runs of this cell would not settle the first of these. Proposed,
not registered, for the owner to choose from:

1. *Form or stage.* The same question in the specification text with a section to fill, spec stage only: about a
   minute and 25 cents a run, and no grading is needed to see whether the list appears.
2. *An instrument that can see what a question is for.* Either more planted defects in existing behaviour that the
   product's own tests do not catch, or, for the vague request the owner has in mind, a request with its stated
   details taken out one at a time, read for whether the specification raises the missing detail as an open
   point, decides it, or passes over it. Neither exists yet.
3. Rungs 2 and 3 of the ladder would be read on the present instrument and could show no more than this rung did;
   they wait for 1 and 2.

**Checked twice, and who decided what.** The readings against the registered rules, the reading of the tests and
the findings were made in the main session. A Sonnet subagent copied the evidence, ran the registered script,
recounted every figure with a script of its own and drafted the tables. Its recount matches the script on every
count but three: the two clauses the word match misses, which it found independently, and the earlier baseline's
specification time, which that run's record holds under another key (the table uses it).

**Limits.** One case, one model at one effort, two runs a placement and three of the baseline. The six cells ran
together and the gradings overlapped: fourteen results across the seven gradings failed once and passed when run again
(counted as passing, as the grader does; no catch rests on one), and minutes are not compared. Only the question is
ShipLoop's; the sentences around it are mine. The two placements differ in form as well as in stage. The reading of
why each defect was missed is mine, from the test code; the nested-run check was made on one defect tree. Every
request here is precise.

Evidence: `evidence/preserve-question/` (a folder for each of the six cells with the run record, the grading, the
specification as the spec stage left it and as it ended, the plan and the grading log; `by-source-log.txt` and
`.json`, `specs-log.txt` and `.json`, `recount.txt`, `nested-test-run-check.txt`).

### Received after the result: on Sol, what a command printed is not always what the model was given (2026-11-21 13:54)

Status: received from the session "Spec elaboration" at about 13:45, its work and not re-run here (its journal
section 43, its commit a3392874fb01b14c4c1c62443a80a9dce1660f6c); the check of this pilot's apparatus is mine.

**What it found.** On the Codex host GPT 6.2 Sol runs its commands from a script of its own, keeps a command's
output in a variable and prints to itself the part it asks for. What the model was given is in Codex's own session
record, not in the harness's events. Over 50 existing ShipLoop runs on Sol, the spec stage's instructions were
given at four fifths of their lines or more in 41 and at under a third in 8, and the line that says where the
requirement guides are was given in 9.

**What it touches here, and what it does not** (checked in `ratchet.py`, `Ratchet.session` and the packets). Every
stage's text and the request itself are formatted into the session's prompt, so "the stage was told" holds for
this pilot's Sol cells, and no registered reading rests on text handed over by a command. What a Sol session gave
itself afterwards through commands (the specification and plan files, the product's own files, the gate's output,
the Until Loop runtime's messages) has not been read: this pilot's readings used the harness's events. Codex's
own session files are kept in each Sol run's home folder (two for `p1R-ticket-assignment`, three for
`p3R-ticket-due-times-a`), so it can be read from records on file, with no run. The cells of amendments 10 to 12
on Sonnet are not touched: there a tool's result is what the model is given. For F39 it adds a second way, on
Sol, for text to leave no trace: it is not printed.

## 23. Amendment 13, 2026-11-21 14:28: the same question in the specification, with a section to fill (registered before any run)

Owner: asked which next step to start ("A then B's first rung (my pick), A only, add the optional reading C, or stop
here"), he answered "Yes". I take that as the pick named: step A, registered here, and then the first rung of step B,
which is designed after A's result and registered by itself.

**What it asks.** F39 left two things together: the plan answered the question and the specification did not, and
the plan had a section to fill where the specification had only one more instruction. Here the stage is the
specification and the form is the plan's.

**The text** (`ratchet.py`: `PRESERVE_SPEC_SECTION`, chosen by `--preserve spec-section` with `--enrich reworded`).
It is `PRESERVE_PLAN` word for word with the file and the place changed: "in a third section of `ratchet/spec.md`,
`## Preserved behaviour`, after the clauses" where the plan's says "in a sixth section of `ratchet/plan.md`", and "add
it as a clause with the next number" where the plan's says "add it at the end of `ratchet/spec.md` as a clause with
the next number". It sits where amendment 12's specification paragraph sat, above "How to get there". The script's
reader of a specification already ends an item at a section heading, so it reads such a file unchanged.

Checked before this registration: the 20 text constants of the committed script are unchanged and two are added; the
specification packet renders byte for byte as before for `none`, `spec` and `plan`, and with `spec-section` it is
the baseline packet plus this one paragraph; the standing self-test passes plain and with the new setting ("selftest
ok: 10 sessions, 6 gates, 14 snapshots" twice); the paragraph is in the spec session's prompt only; the setting is
refused without `--enrich reworded`. `by_source.py specs` now also counts the entries of such a section and how
many name a file (`NAMES_A_FILE`, a word match); it reproduces amendment 12's table line for line and counts the two
plans' sections as the helper's recount did (14 and 13; 10 and 9).

**Cells.** Three runs, `q-sec-1` to `q-sec-3`: ticket assignment, the spec stage alone (`--stop-after spec`), Claude
host, `claude-sonnet-5-5` at medium, 6 dollars a session at most. They are read beside the seven specifications on
file from amendment 12: five written without the question (the earlier one, `q-base-1`, `q-base-2`, `q-plan-1`,
`q-plan-2`) and two with the question as an instruction (`q-spec-1`, `q-spec-2`). No baseline is run again: the
text for the other settings is what wrote those seven, byte for byte, with the same model and effort on the same
day.

**Readings.**

- **R14.1, the first reading: is the question answered?** A run *answers* if its specification holds a section
  `## Preserved behaviour` with at least 5 entries that name a file (the plans held 13 and 9; counted by the
  script). *The form decides* if all three answer. *The stage decides* if none does. Otherwise mixed, given as
  counts.
- **R14.2, do the answers become clauses?** Clauses sourced `existing` (first word) as the spec stage leaves them,
  against 1 to 5 in the seven on file. *They do* if at least two of the three runs hold 7 or more: the top of that
  range plus two (F38), and what the plan's question ended at (7 and 8). *They do not* if all three hold 5 or
  fewer. Otherwise not shown.
- **R14.3, harm** (my reading, named as such, with the clauses listed): `existing` clauses that state behaviour of
  the new feature and not of the product as it is, the kind F41 found; and choice clauses, 2 or fewer in each.
- **R14.4, the one defect** (reported): whether any clause says that a resolved ticket can still be changed, the
  behaviour `update-rejects-resolved` breaks. No test is run here; this says only whether the clause is written.
- Reported: clauses, use cases, `Open:` lines, whether the section says what the repository does not settle,
  seconds and cost.

**Predictions.** All three answer, with 8 to 15 entries naming a file. The entries mostly do not become clauses:
`existing` clauses between 4 and 8, 7 or more in at most one run, because this text's own rule on what earns a
clause pulls the other way and every specification already has one clause that says existing behaviour is
unchanged. The resolved-ticket clause is written in at most one run. At most one clause in all decides something
new under an `existing` source.

**What each outcome means for the next rung**, written now. If the form decides, a catalog question can be put to
the specification stage as a section, and step B's question arm does that. If the stage decides, or the result is
mixed, step B's question arm puts its question in the plan, where it was answered twice of twice.

**Limits known before the runs.** One case, one model at one effort, three runs. The specification alone: nothing
here says what tests or products do with a section. The paragraph is the plan's with two phrases changed, and both
changes are mine. The seven specifications it is read against were written two hours earlier.

### Amendment 13, result (2026-11-21 14:36; three specification runs, 14:29 to 14:31)

Status: firm for what was run: three runs of the spec stage alone on ticket assignment, Claude host,
`claude-sonnet-5-5` at medium; each specification accepted on its first try; no held-out mark; nothing put back by
the script; 0.92 dollars. Read beside the seven specifications on file from amendment 12, each as its spec stage
left it.

**Table. Ten specifications of the same request.** "`existing` first" and "anywhere" as in amendment 12. "Section"
is the number of entries of a `## Preserved behaviour` section and, in brackets, how many name a file. "Test
clauses" is the number of clauses that carry the request's two sentences about tests (the existing tests still
pass; new tests run under `npm test`).

| Run | The question | Clauses | `existing` first | anywhere | choice | `Open:` | Section | Test clauses | Seconds |
|---|---|---|---|---|---|---|---|---|---|
| earlier | none | 22 | 2 | 8 | 1 | 8 | none | 2 | 47 |
| `q-base-1` | none | 21 | 1 | 10 | 0 | 9 | none | 2 | 54 |
| `q-base-2` | none | 24 | 5 | 10 | 1 | 10 | none | 2 | 47 |
| `q-plan-1` | none yet | 20 | 2 | 8 | 0 | 6 | none | 2 | 63 |
| `q-plan-2` | none yet | 22 | 5 | 12 | 2 | 8 | none | 2 | 49 |
| `q-spec-1` | an instruction | 21 | 4 | 9 | 0 | 9 | none | 2 | 51 |
| `q-spec-2` | an instruction | 22 | 5 | 15 | 0 | 8 | none | 2 | 58 |
| `q-sec-1` | a section to fill | 26 | 6 | 11 | 1 | 7 | 11 (10) | 1 | 64 |
| `q-sec-2` | a section to fill | 24 | 2 | 8 | 1 | 9 | 10 (8) | 0 | 74 |
| `q-sec-3` | a section to fill | 25 | 5 | 12 | 1 | 7 | 11 (11) | 1 | 73 |

**The readings of amendment 13.**

- **R14.1, the first reading: the form decides.** All three specifications hold the section, with 11, 10 and 11
  entries of which 10, 8 and 11 name a file (the bar was 5). Each also says what the repository does not settle
  (for example whether a data file with an invalid assignee is refused, and whether `show` prints the assignee).
  The two specifications written with the same question as an instruction hold no list.
- **R14.2, do the answers become clauses: not shown.** Clauses sourced `existing`: 6, 2 and 5, against 1 to 5 on
  file. The bar was 7 in two runs. The specifications are a little longer all the same (26, 24 and 25 clauses
  against 20 to 24), with no one kind of source accounting for it.
- **R14.3, harm, my reading.** No `existing` clause decides something new. Those about the new feature apply a rule
  the documents state for every request or every change (unknown fields are refused, an unknown ticket is 404,
  every change is on the audit record). One section says of the very point F41's clause decided, a data file with
  an invalid assignee, that it is not settled. Choice clauses: 1 in each. What reading them did turn up is below.
- **R14.4, the one defect.** None of the three says that a resolved ticket can still be changed, and none of the
  seven on file does. All three sections give the rule from the refusing side only ("a closed ticket cannot be
  changed (PATCH 409)"; "PATCH refuses closed tickets"), which a product that also refuses a resolved one
  satisfies.

**Not registered, found by reading: with a section to fill, requirements left the clauses.** The request's two
sentences about tests are two clauses in each of the seven specifications on file. With the section they are one
clause holding both in `q-sec-1` (C-26) and `q-sec-3` (C-24), and no clause in `q-sec-2`, where "the existing tests
in `test/` keep passing unmodified" is the section's opening line and the sentence on new tests under `npm test` is
nowhere in the specification. Three of three against none of seven. Only clauses and use cases are given tests, and
amendment 12 found that on this case those two clauses carry most of what is caught in existing behaviour. No
test stage ran here, so what a test session would make of a section is not known.

**Predictions scored.** "All three answer, with 8 to 15 entries naming a file": held (10, 8, 11). "`existing`
clauses between 4 and 8, 7 or more in at most one run": the second half held; one run wrote 2. "The
resolved-ticket clause in at most one run": held, in none. "At most one clause decides something new under an
`existing` source": held, none by my reading. That the section would draw requirements away from the clauses I did
not predict.

**Findings.**

- **F43 (firm for what was run: three runs; with amendment 12, five of five against none of two).** A question
  from ShipLoop's catalog is answered when there is a section to fill, at the specification stage as at the plan
  stage. At the specification stage, where both forms were run, the form decides: three of three with a section,
  none of two without. The plan was run only with one. So F39's difference was the form, as far as these runs go.
  *Qualified 2026-11-21 16:55 (section 25):* "none of two" means no separate answer; see the note under F39.
- **F44 (three runs).** At the specification stage the answer stays a list. The plan's entries became clauses (5
  and 4 added, and one of them caught the defect no short specification had caught); the specification's did not
  (R14.2), and none of the three lists says the one thing that defect needs.
- **F45 (three of three; no test stage run).** A section is also somewhere else to put a requirement. With one in
  the specification, a request sentence that had always been a clause became part of the list. A list that is
  not tested must point at the clause that carries each entry, or it takes from the tests what it adds to the
  page.

**Is there enough to conclude?** For what this amendment asked, yes: the form decides. For the design of what
follows: a catalog question can be put to the specification stage as a section, as registered, and by F45 the
section's entries must name the clause that states each of them; where entries are meant to become requirements,
the plan is the stage that made them so. Not established: what a test session does with a section; any other
question of the catalog; another case or model.

**Checked twice, and who decided what.** The readings and findings are the main session's. A Sonnet subagent
copied the evidence, ran the registered script and recounted every figure with a script of its own, quoting each
clause on tests and each line on changing a ticket by status; its counts match the script's on all ten
specifications (the earlier baseline's specification time apart, as before), and its quotes are what the readings
of R14.4 and of the test clauses rest on.

**Limits.** One case, one model at one effort, three runs. The specification alone. The seven on file were written
two hours earlier from the same text. The count of test clauses was not registered; it is exact (a clause either
carries a sentence or does not) and was made twice.

Evidence: `evidence/section-question/` (a folder for each of the three runs with its record, specification and
log; `specs-log.txt` and `.json`; `recount.txt`).

## 24. Amendment 14, 2026-11-21 14:41: a request with one stated detail left out, first rung (registered before any run)

Owner: his "Yes" of section 23 covers this rung ("B's first rung: one removed detail, six runs, about 4 dollars,
after I register its design"). His interest, from section 22: whether known questions give "better breadth and
coverage" when "we elaborate the incoming prompt", for a request that does not say everything.

**What it asks.** Every request in this pilot is precise, so nothing so far reads what a specification does about
something the request needs and does not say. Here one detail the request states is taken out, and the reading is
what the specification and the plan do about it: raise it, decide it, or pass over it; and whether one catalog
question, asked as a section, changes that. This rung is also the first trial of the instrument itself.

**The design is the session "Spec elaboration"'s five points, taken whole** (received about 13:20, before anything
was built): sort each candidate detail against the starting product first; read the plan as well as the
specification and never score "decided" as success; four classes, not three; few details with repeats and a
difference registered beforehand; a request that reads whole, checked by a reader who has not seen the original.

**The detail.** The original request says "an agent is a non-empty name of at most 64 characters". The case
`ticket-assignment-name-limit-unsaid` says "an agent is a non-empty name" and is otherwise word for word (176 words
for 181).

- *Sorted against the starting product, before any run.* It has no assignment and says nothing of an agent. It
  states a limit for every other name it takes: the requester, at most 64 characters, and the actor in `X-Actor`,
  at most 64 (`docs/api.md`); and for the title, at most 200. So nothing settles an agent's limit, and the product
  holds two like limits of 64 and one of 200. The request's other stated details, sorted the same way, are why this
  one was taken: that only open and in-progress tickets can be assigned (the product partly settles it the other
  way: "a closed ticket can no longer change", and a resolved one can); that assigning the same agent changes
  nothing (the product settles it: `CONTRIBUTING.md`); that an empty `assignee=` keeps the unassigned (the product
  settles it the other way: an empty `status=` is 400); that a ticket must match every filter (its document settles
  it, its code disagrees); that the agent is notified and that the command line shows the assignee (capabilities:
  left out of a request, passing them over is right under this text); that `null` unassigns (nothing settles it,
  but taking it out changes two sentences).
- *Reads whole.* A Sonnet subagent given only the shortened request, and asked whether any sentence reads as cut or
  refers to something never stated, answered "reads whole" and "nothing stands out".
- *The right behaviour under the text itself.* "Invent no bound: one that none of those supplies is an `Open:`
  line."

**Arms.** Three runs each, the spec stage and then the plan stage (`--stop-after plan`, new), Claude host,
`claude-sonnet-5-5` at medium, 6 dollars a session at most.

- `b-base-1` to `b-base-3`: the reworded text as it is.
- `b-rules-1` to `b-rules-3`: `--rules spec-section` (new). ShipLoop's key question K4, word for word ("Rules and
  edge cases: the domain rules, limits, invalid inputs, boundaries and end conditions."), in the form amendment 13
  found answered: a third section of the specification, `## Rules and edge cases`, each entry "with the clause that
  states it"; "The section adds no requirement and replaces no clause" (F45); what neither the request nor the
  product settles is said in the section.

The question is the one of the twelve that matches the detail, and it was chosen knowing the detail. This rung asks
whether a matching question can change the outcome at all. It says nothing about twelve questions asked together.

Checked before this registration: the 23 text constants of the script are unchanged and two are added; with the
question off the specification packet renders byte for byte as before for every `--preserve` setting, and with it
on it is the baseline packet plus the one paragraph; the plan packet is unchanged; the new case's request is the
old one less those five words; the standing self-test passes; on the stand-in host a run with the question and
`--stop-after plan` ends with two sessions and three snapshots and holds the paragraph in the spec prompt only;
three wrong combinations of options are refused. `by_source.py specs` counts the new section's entries and how many
name a clause, and still reproduces amendment 13's table.

**What is read**, a run at a time, in the specification as the spec stage left it and in the plan. The point is
the longest name an agent may have.

- **O+**: marked open (an `Open:` line, or an entry saying it is not settled) and the answer taken is named.
- **O**: marked open and no answer taken.
- **D**: decided. A longest length is stated as a requirement, in a clause or as a decision of the plan, with no
  mark that it is open. The source it is given (choice, existing, implied) is recorded.
- **P**: passed over. Neither the specification nor the plan speaks of a longest length for an agent's name.

**Readings.**

- **R15.1, the first reading: noticed or passed over.** O+, O and D count as noticed. *The question makes it
  noticed* if all three runs with the question notice and at most one baseline run does. *The baseline already
  notices* if at least two baseline runs do: this detail then leaves no room, and the instrument needs another.
  Otherwise not shown.
- **R15.2, open or decided**, among the runs that notice: counts, with each decision's source. No bar at three
  runs. "Decided" is never a success.
- **R15.3, the question arm did what was asked.** The section is there with at least 5 entries, and how many name a
  clause (by the script). By reading: how many clauses carry the request's two sentences about tests, which F45
  found lost with a section; 2 in each is kept.
- **R15.4, harm** (my reading, the clauses listed): clauses in the question arm that the request does not call for;
  choice clauses; the number of clauses in each arm.
- **Two readers.** The classes are read by me and, from the same definitions, by a Sonnet subagent given the six
  pairs under neutral names. It cannot be blind to the arm (the section shows it). The reading of record is mine;
  where the two differ, both are given.

**Predictions.** Baseline: one of three notices (most write "a non-empty name" and stop). With the question: three
of three notice, two of them marking it open and one deciding 64 "as the requester's". The section holds 8 to 15
entries, most naming a clause, and at least two of the three keep both test clauses.

**Limits known before the runs.** One detail, chosen by me who knows the case, where the product holds like limits
that make the gap easier to see than most. One question, the matching one. One model at one effort, three runs an
arm: only a stark difference can show. The specification and the plan only: "passed over" means neither says it,
and what a build would then do is not seen. The paragraph's sentences around the question are mine.

### Amendment 14, result (2026-11-21 14:50; six runs, 14:42 to 14:45)

Status: firm for what was run: six runs, the spec stage and then the plan stage, on the request with the name's
limit left out; three with the reworded text as it is and three with the rules question as a section; Claude
host, `claude-sonnet-5-5` at medium; each specification accepted on its first try; no plan added a clause; no
held-out mark; nothing put back by the script; 4.14 dollars.

**Table. What each pair of documents does about the longest name an agent may have.**

| Run | The question | Class | Marked open in | The plan takes | Clauses | `Open:` | Section | Test clauses | Seconds |
|---|---|---|---|---|---|---|---|---|---|
| `b-base-1` | none | O+ | C-1 `Open:` | 64 | 22 | 5 | none | 2 | 50 + 99 |
| `b-base-2` | none | O+ | C-3 `Open:` | 64 | 21 | 10 | none | 1 | 55 + 87 |
| `b-base-3` | none | O+ | C-3 `Open:` | 64 | 18 | 5 | none | 2 | 53 + 89 |
| `b-rules-1` | a section | O+ | C-3 `Open:`, two entries | 64 | 23 | 8 | 13 (13) | 2 | 65 + 81 |
| `b-rules-2` | a section | O+ | C-4 `Open:`, two entries | 64 | 20 | 8 | 10 (9) | 1 | 64 + 111 |
| `b-rules-3` | a section | O+ | C-3 `Open:`, one entry | 64 | 23 | 8 | 13 (12) | 2 | 58 + 95 |

"Section" is the number of entries of `## Rules and edge cases` and, in brackets, how many name a clause. "Seconds"
is the spec session and the plan session.

**The readings of amendment 14.**

- **R15.1, the first reading: the baseline already notices.** All three baseline runs mark the limit as open in the
  specification, and so do the three with the question: noticed in six of six, passed over in none. By the
  registered rule this detail leaves no room, and the instrument needs another.
- **R15.2, open or decided: open in six of six, decided in none.** Each specification gives the point an `Open:`
  line and says the requester decides ("the longest accepted name (existing text fields have limits: requester 64,
  title 200); the requester of the service decides", `b-base-1`). Each plan then names the answer it takes, 64,
  "same as requester". Five of the six plans tell the tests not to rely on a length, and at least three say the
  build reports the choice. So the class is O+ six times. The answer the plans take is the one the original
  request stated.
- **R15.3, the question arm did what was asked.** The section is there in all three, with 13, 10 and 13 entries of
  which 13, 9 and 12 name a clause. The request's two sentences about tests are 2, 1 and 2 clauses with the
  question and 2, 1 and 2 without it, and nothing about tests sits in a section: the section took no clause away.
  One run of each arm has no clause for the sentence on new tests under `npm test`.
- **R15.4, harm, my reading.** Each arm writes a few clauses the request does not ask for, of the same kinds (what
  unassigning or reassigning does to notifications, a refusal of control characters in a name), and the clearest
  capability nobody asked for is in a baseline run (`b-base-2` C-18, an `assignee` filter on the command line). No
  difference between the arms shows. Clauses: 23, 20 and 23 against 22, 21 and 18. Choice clauses: 2, 2 and 0
  against 0, 2 and 0. `Open:` lines: 8, 8 and 8 against 5, 10 and 5.
- **Two readers.** My reading and the Sonnet reader's, made from the six pairs under shuffled names, agree on six
  of six.

**Predictions scored.** Baseline, "one of three notices": wrong, all three did. With the question, "three of three
notice, two open and one decided": three noticed and all three left it open. "8 to 15 entries, most naming a
clause": held. "At least two of the three keep both test clauses": held, two.

**Why the baseline had no trouble (my reading).** The reworded text has a rule for exactly this: "Where a clause
depends on a bound, state the bound and what happens at it ... Invent no bound: one that none of those supplies is
an `Open:` line", and the product limits every other name it takes, so the gap is in plain sight. I took a detail
the text was written for. Its sentence on sets ("the states that stop something") covers states the same way. A
detail that tests a question has to be one no rule of the text names.

**Findings.**

- **F46 (firm for what was run: six of six, two readers agreeing).** With a stated limit left out of the request,
  the reworded text by itself marks the missing limit as an open point, and the plan takes the product's own
  precedent and says so. No question was needed for it, and the answer taken is the one the requester had. This
  is the text doing for an unsaid bound what F29 to F33 showed it doing for the points a request leaves open.
- **F47 (three runs).** The remedy for F45 held. A section whose entries must name the clause that states each
  left the clauses where they were (2, 1 and 2 test clauses with it and without), and 34 of its 36 entries name a
  clause. F45's own baseline is corrected by this round: a specification without any section also wrote one test
  clause for two sentences, once in three, so "none of seven" is now one of ten.
- **F43, extended.** A catalog question asked as a section was answered in three more runs: eight of eight with a
  section (two plans, three specifications for K2, three for K4), none of two without.

**Is there enough to conclude?** For this detail, yes: the text already does it, and a question adds nothing that
shows. For the instrument: it reads cleanly (four classes, two readers agreeing, about 70 cents and two and a half
minutes a run), and its first detail had no room. For the owner's question, whether key questions add breadth on
a request that does not say everything: not answered yet. What would answer it is a detail that no rule of the
text names and that the product settles otherwise than the requester wants. Proposed, not registered: leave out
"Only open and in-progress tickets can be assigned or unassigned". The product says a closed ticket can no longer
change and lets a resolved one change, so a specification written from the product alone would let a resolved
ticket be assigned, which this requester did not want.

> **Received 2026-11-21 15:05, on that proposal, from the session "Spec elaboration"** (asked for; its own guides
> test, twenty Sol runs from one vague sentence, ended "not shown" by its rule the same hour: its journal section
> 47, its commit 4f91f17010ca26daa4247266cdf0ebdb96d82959, not re-run here). Two cautions, both taken, and one
> correction of mine.
>
> - *Following the product is right.* With that sentence gone nothing in the inputs holds the requester's wish, so
>   a run that follows the product is not a miss by anything it could know. Such a rung reads whether a text makes
>   an inherited rule visible ("inherited from the product, and said so" against "inherited silently"), not
>   whether it recovers the wish. My "which this requester did not want" cannot be a yardstick.
> - *It may meet the floor*, as this rung met the ceiling: if neither the text nor the question names
>   state-dependent permissions, both arms may sit at nothing. A detail with room both ways is one the product
>   leaves unsettled and no rule names.
> - *Correction.* Reporting this result, I told the owner that no rule of the text covers that sentence. The text's
>   rule on sets does name "the states that stop something", for a clause that depends on one. It does not ask
>   which states allow an action the request is silent on, but it is not nothing, and the paragraph on why the
>   baseline had no trouble already said so.
>
> What follows for the proposal: it stands only as a reading of whether inherited rules are made visible, with the
> classes inherited and said, inherited silently, marked open, passed over. This request is tight, and it may hold
> no detail that the product leaves unsettled, that no rule names and that a writer could miss.

**Checked twice, and who decided what.** The classes, the readings and the findings are the main session's. One
Sonnet subagent read the six pairs under shuffled names from the registered definitions and gave the same six
classes, quoting every sentence it relied on. Another copied the evidence, ran the registered script and recounted
every figure with a script of its own: no disagreement with the script.

**Limits.** One detail, chosen by me, in a product that holds like limits; one question, the matching one; one
model at one effort; three runs an arm. The specification and the plan only: no build ran, so that a build would
take 64 and report it is what the plans say, not something seen. The second reader could see which pairs had a
section.

Evidence: `evidence/unsaid-detail/` (a folder for each of the six runs with its record, its specification as the
spec stage left it and as it ended, its plan and its log; `specs-log.txt` and `.json`; `recount.txt`;
`second-reading.md`, the second reader's quotes and classes with the key to the shuffled names).

### Received: the section form in ShipLoop's released spec stage, on Sol, from vague requests (2026-11-21 15:53)

Status: received at 15:52 from the session "Spec elaboration" (its journal sections 50 and 51, its commit
411646c297f603bba29835751a0c88b591252cd3); its work on its own instrument, not re-run here; I read its section 51
at that commit before writing this. Shortly after 15:07 I had passed it the form of F43 and F47 as an idea for its
bench; it registered the arm and ran it within the hour.

**What it ran.** ShipLoop's released spec stage with one more duty: to end `spec.md` with a section "Key questions"
holding one entry for each of the intake's twelve key questions, each with this change's answer in a line and the
requirement or section that states it, and the sentence "The section adds no requirement and replaces none."
Against the released stage as it is. Two one-sentence requests (a CSV import of users on a small program; a CSV
import of tickets on the ticket service), three sets a case, GPT 6.2 Sol at medium, each run stopped when ShipLoop
accepted the specification, and each specification judged blind by two models on the items its two sorters said
apply.

**What it found.**

- *The form carries over.* All six specifications with the duty end with the section, twelve entries each, every
  entry naming the requirement or section that states it, and ShipLoop accepted every one. One author gave itself
  only the first four question lines and still wrote twelve entries, from the lines it had been given at intake.
- *It does not make the specification fuller.* Item readings covered by both judges: 21 against 18 of 27 on the
  small program and 21 against 20 of 45 on the ticket service; set by set the nets are 0, 0, minus 1 and 0, 3, 1,
  where its rule needed 2 every time. Not shown. The section is an index: each entry restates in a line what a
  requirement already says; without the section's words the specifications are no longer, and the requirement ids
  are the same in number. So it took nothing out of the clauses either.
- *One item moved every time:* who may use the change at all, covered in three of three with the section and in
  none of three without. The entry for the question on what the request's words mean made the author say who an
  admin is.
- *Its reading.* The form gets a question answered, and a general question gets a general answer. What its two
  cases leave thin is particular to the change (the result for each row, what a caller may set, what happens to
  the product's own notifications and audit, hostile input, dates), and twelve general questions answered in a
  line each do not reach it. With its two earlier levers (guide text in the packet, a sentence to read the whole
  packet) that is three tried and none shown, over 56 specifications from two vague sentences. *Corrected
  2026-11-21 16:55:* 44 specifications, not 56. That session corrected its own total at 15:58, after I had read
  its section; the outside review of section 25 pointed out that this receipt still carried the old figure.

**What it does to the findings here.**

- F43 holds on another model, another host and ShipLoop's own stage: with these six, a catalog question asked as a
  section has been answered fourteen times of fourteen. F47 holds there too: nothing left the requirements.
- It answers, on a vague request and with blind judges, what amendment 14 could not: asking ShipLoop's general key
  questions in the form that gets them answered does not make the specification fuller in a way that shows.
- Taken with this pilot's amendments 12 and 14, that is five small tests in one day of reusing ShipLoop's general
  reference material at the specification or the plan, on two instruments, two models and two hosts. None shows a
  fuller specification or a stronger suite. What they show is how to get a question answered (a section to fill
  whose entries name what states them), and one case each where an answer mattered: here a clause from the plan's
  question that caught the long-missed defect, there the entry that says who may use the change.

**Not known, and the owner's to decide.** Whether questions particular to the kind of change would reach what
general ones do not. The session "Spec elaboration" names that as the next lever and as a product decision. This
pilot's removed-detail instrument could read such questions on one detail at a time; nothing is registered.

## 25. Two outside reviews at maximum effort on what to try next (2026-11-21 16:55; no run of this pilot)

Owner, after the result of section 24: "Help think deeply of there is any other consideration or idea we should
experiment with before we move forward", and then: "We are trying to create a generic SDLC prompt and scripts , how
could we make this more effective? What ideas should we try based on learnings?"

By his standing rule a deep design question goes to the latest Sol at maximum effort, read-only, before anything is
called ready. Two reviews were run on `gpt-6.2-sol` at effort max with the consult profile and no fallback: the
first from 16:32 to 16:43 on this pilot's question, the second from 16:40 to 16:53 on ShipLoop itself. Each read a
neutral folder of copies: for the first, sections 20 to 24 of this journal, sections 37 to 52 of the Spec
elaboration journal and the prompt texts under test; for the second, ShipLoop's released source, the architecture
note and the four journals. The local account name was taken out of the copies. The questions and the answers, word
for word, are in `review/` (`sol-ideas-question.md`, `sol-ideas-answer.md`, `sol-shiploop-question.md`,
`sol-shiploop-answer.md`). I gave the owner my own ideas before either answer was in.

**The first review, in short.** Keep the reworded text as the baseline. Stop spending on general additions to the
specification. Put the next effort on what the gate really measures and on one narrow comparison scored on
behaviour.

- *A missing fact is not a missing decision.* The repository can supply a fact; only the requester can supply a
  decision. A person should be asked a decision as a concrete fork that says what the answer changes.
- *The misses seen here are test-design misses.* Two suites never built an input that separates right paging from
  wrong; the lists said "a closed ticket cannot be changed" and not "a resolved one still can". A question helps
  only if it changes the test input or the expected observation.
- *Instruments.* "Fails on the correct reference" mixes an over-strict clause, a valid alternative interface, a bad
  test driver and a gap in the fixture, and should be classified before it is leaned on. The rule of R13.1 could
  not be met once a baseline measured zero. Recovering a deleted detail's original value is not a valid yardstick:
  facts that can be inferred, preferences only a requester has and choices where several products are valid need
  separate examples.
- *Its order of experiments.* First, with no model call, replay archived suites on known-good and known-bad
  products. Then, for a few dollars, hold the request and the specification fixed and compare a general question
  on preserved behaviour with one grounded in the repository, each arm proposing two test scenarios that a script
  scores against known good and bad variants. Then whether one answer from the requester reaches acceptance, a
  fresh reviewer of a finished product, and the same author against a fresh reader on a frozen draft.
- *On the texts.* The specification's declared form names two sections, so an added section is outside the form
  it calls exact; "every sentence of the request" and "joined by and is two clauses" make the count of clauses a
  stand-in for completeness; a preserved rule needs evidence that it governs the changed path, and the allowed
  neighbour beside the refusal; an open point needs a stated job downstream (an implementation choice, a
  provisional choice with a consequence, or a preference someone must settle).

**The second review, in short.** Its one change for ShipLoop: in the existing `test` gate, make a consequential case
prove that it can fail. For a chosen acceptance criterion the script checks that the right case passes on the
candidate and fails, for the expected reason, on a relevant counterexample, and that for preserved behaviour the
original product passes too.

- *Where it says the released loop is weaker than its duties read.* A test case must name a criterion of the step
  plan, but not the one its own focused command declares, and a criterion with no case is a notice, not a refusal.
  A proof or check that exits 0 with no readable tally passes. The intake's question ledger may be left out, and
  nothing joins a routed question or a request outcome to a particular acceptance line. The fifteen concern rows
  must be present, and any non-blank text satisfies a row. The packet puts the callback first and the guide paths,
  root definitions and earlier results after the duties, which is the part a sliced read loses.
- *Its ranked ideas, after the counterexample check.* Put consequential choices in the hand-off that consumes them
  (reusing assumptions and requirement ids); a short action entry with the inputs and checks that matter, the full
  packet a named read away; questions about the consequences of the actual change; outer obligations closed from
  receipts the navigator can join; decisions shown to the person while they can still change the work; a second
  reader from another model family for a named failure; a clean, local system-test stage that finishes on entry.
- *What it would remove.* The record-only Backchain graph; the routine skill decision at carry-forward (`none` in
  306 of 306); the suggested ceilings of twelve criteria and six files in step planning; repeated guidance.
- *How it would evaluate.* One change an afternoon on two cases that have room; prove the yardstick first on a good
  product, a second good product and a faulty one; three paired runs a case with the rule written first; stop
  treating specification length, clause counts, filled fields, guide opens and review edits as results.

**What I checked of them before passing anything on.**

- In the journals: 43 of 203 and 8 of 64 clauses, 15 and 3 items, 38% fewer output tokens (all as recorded here);
  83 of 84 deliveries passing at the last accepted implement step, 306 `none` skill decisions, mutation refusals in
  80 of 97 runs, a ceiling enforced by 12 of 12 Sol due-times builds and named by none of their specifications or
  reports (all as recorded in the other two journals). One figure of the first review, on row-level feedback in 3
  of 5 guide-block specifications, I could not find and did not pass on.
- In ShipLoop's source, read at the lines cited: `check_test_cases` does require only that a case's criterion be one
  of the plan's, and `coverage_notices` says of an unconfirmed criterion "never a refusal"; `judge` passes a check
  that exits 0 when no tally is recognised, and fails one whose tally shows no test ran; the intake ledger is
  optional by a recorded decision ("requiring it would refuse every synthetic intake the hermetic suites
  complete"). So its claims there hold, and two of the gaps are choices someone made on purpose.
- Its correction of this journal is right and is applied in place: the sister study's total is 44 specifications,
  not 56. Its objection to "leaves no trace" (F39, F43) is right too, and both are qualified in place.

**What I take, and what stays open.** Both reviews, the sister study and this pilot's amendments 12 to 14 point the
same way: general questions and guide text have not made a specification measurably fuller, and the failures
actually seen are downstream of the specification, in what a test builds and observes and in what a green gate
proves. F42 is one instance of the second review's main idea: a check of "the existing tests pass" that cannot
fail. Its counterexample check and my hollow-evidence idea are the same proposal at two levels. Not taken as
shown: any gain from the changes it proposes, none of which has been run. Nothing is registered by this section.

**The owner's to decide.** Whether to pilot the counterexample check in ShipLoop's test gate, which is a product
change and belongs with the session that owns ShipLoop's releases; whether this pilot's next step is the free
replay of archived suites; and whether the reworded text goes into ShipLoop's specification stage.

## 26. A program of experiments on Sol 6.2 at medium (2026-11-21 17:32; each part registered before its runs)

Owner, after the reviews of section 25: "Create the experiments and tests to evaluate all these ideas" and "Run
everything , using SOL 6.2 med as the runner".

**The frame.** Every model session of this section runs on the Codex host with `gpt-6.2-sol` at medium. The ideas
are the eight I gave the owner and the ranked ones of the two reviews; where two are the same idea they share an
experiment. Each part is registered in its own subsection, with its rule and predictions, in a commit made before
its first run. The parts, as planned:

| Part | The idea | The instrument | Model sessions |
|---|---|---|---|
| D | a decision the request leaves out is carried, not made silently | three requests with a known unsaid point, read in the specification and the plan; the plain text first, a lever only where the plain text leaves room | 9, then up to 36 |
| C | a check must be able to fail | a census of checks that run nothing in the suites on file; then test sessions with and without a script that refuses a check never seen to fail, scored on planted defects | 14 |
| E | existing code is protected | faults seeded in existing code a change touches, replayed on suites on file | none |
| V | the instruction arrives | the same text in the prompt or through a file, the checked duty first or last, read in Codex's own record | 12 |
| R | a fresh reader | one marks unstated decisions in a specification; one checks a finished product | 27 |
| T | a question at test design | a general question against one grounded in the repository; scenarios scored by a script against good and bad products | 12 |
| A | ask after reading | a census of archived deliveries: are questions routed to "inspect" answered on record | none |
| G | gaps in ShipLoop's own checks | tests that pin today's behaviour of its validators on made-up inputs | none |

Rules common to every part, from the reviews and from F38: three plain runs before any comparison; a lever is run
only where the plain runs leave room; a yardstick is shown to work on a good and a bad input before it scores
anything; what I judge by reading is read a second time by a Sonnet subagent under shuffled names; no held-out
check, planted defect or answer sheet is ever in a model session's folder or prompt; "more" of anything counted in
a specification is not a result.

Not run here: changes inside ShipLoop's own scripts (the order of a stage's text, joining receipts, a stage that
finishes on entry, removals). They are product changes and need its release harness; part G pins the behaviour a
fix would change, and part V is a bench stand-in for the first.

### Part D1, registered 17:32: what the plain text does with three unsaid points (nine runs)

**What it asks.** Amendment 14 found that on Sonnet the reworded text marks a missing limit as open by itself. The
archive read by the session "Spec elaboration" says Sol behaves otherwise in ShipLoop: 12 of 12 due-times builds
enforced a ceiling that none of their specifications named. So the first question on this runner is whether the
plain text leaves room at all.

**Cells.** Three requests, three runs each, the spec stage and then the plan stage (`--stop-after plan`), the
reworded text with no question added:

- `d-limit-1` to `-3`: `ticket-assignment-name-limit-unsaid` (amendment 14's request).
- `d-states-1` to `-3`: `ticket-assignment-states-unsaid`, new: the ticket-assignment request less the sentence
  "Only open and in-progress tickets can be assigned or unassigned." (171 words for 181).
- `d-due-1` to `-3`: `ticket-due-times` as it is. Its unsaid point is the one earlier Sol runs decided wrongly:
  who fills the due times into the existing data file, and what the service does when it starts with the switch on
  and the file does not hold them.

**The three points, sorted against the starting product before any run** (the session "Spec elaboration"'s first
point, and the first review's distinction between a fact and a decision):

- *The limit.* A decision the product does not settle, with like limits in plain sight (64 for the requester and
  the actor, 200 for the title). Right under the text: an `Open:` line.
- *The states.* A fact the product supplies: "A closed ticket can no longer change" (`docs/api.md`), and a resolved
  one can. Following the product is right, and nothing in the inputs holds this requester's stricter wish. So the
  reading is whether the inherited rule is made visible.
- *The due times.* A decision only the requester can make. The request's words admit two readings (an operator
  prepares the file before switching on; or the service fills it in itself when it starts switched on). The owner
  later ruled for the second (the SDLC journal, round 9: "the reading the owner ruled right").

**Classes**, a run at a time, read in the specification as the spec stage leaves it and in the plan.

- For the limit and the due times: **O+** marked open and the answer taken named; **O** marked open, nothing
  taken; **D** decided with no mark that it is open (for the due times: **D-refuse**, the service refuses to
  start or to switch on until someone has prepared the file; **D-fill**, the service fills the file itself);
  **P** passed over.
- For the states: **I+** the product's rule is applied to assignment and its source is named; **I** applied with
  no source and no mark; **O** or **O+** marked open; **D** a rule other than the product's is required with no
  mark (for example resolved tickets refused too); **P** nothing says which states allow assignment.

**Readings.**

- **RD1.1, room.** A request *leaves room* for a lever when at least two of its three runs are D, I or P. A request
  whose runs are O, O+ or I+ in at least two of three leaves none, and no lever is run on it.
- **RD1.2, the known bad outcome.** For the due times, the number of runs that are D-refuse: the reading earlier
  Sol runs built, which failed five of eight held-out checks.
- **RD1.3, two readers.** My classes and a Sonnet subagent's, made from the nine pairs under shuffled names.
- Reported: clauses, `Open:` lines, choice clauses, seconds for each session.

**Predictions.** The limit: Sol at medium decides it or passes over it in two of three. The states: the product's
rule is applied in three of three, with its source named in two. The due times: marked open in two of three, and
D-refuse in at most one.

**Limits known before the runs.** Three points on two products that are one code base; one model at one effort;
three runs a request; the specification and the plan only, so what a build would do is not seen.

### Part E, registered 17:36: faults seeded in the existing code a change touches (no model session)

**What it asks.** Amendment 12 could not say whether writing down what must not change protects existing behaviour:
the pool of 27 planted defects holds one that only such a clause can catch. This part gives that question an
instrument with room.

**The instrument.** `mutate.py --unchanged` (new): the harness's own fault catalog, placed only on lines of product
source that a delivery left as the starting product has them, in the files it changed. On the ticket-assignment
reference build that is 52 sites in six files (26 in `src/persistence.js`, 7 each in `src/store.js`,
`src/tickets/query.js` and `src/tickets/validate.js`, 3 in `src/format.js`, 2 in `src/app.js`), against 6 on the
lines the change added. The first 40 in the catalog's own order are used, the same 40 for every suite, since every
cell of amendment 12 tested the same reference build. For each fault the script runs the product's own tests and
every command of the suite's manifest.

**What is read.** The seven suites of amendment 12 (three baseline, two with the question in the specification,
two with it in the plan), all written by Sonnet at medium.

- **RE.1, room.** Of the 40 faults, how many the product's own tests catch and how many survive them.
- **RE.2, what a suite adds.** Of the faults that survive the product's own tests, how many each acceptance suite
  catches. *The plan's question protects existing code* if both plan suites catch more of them than the best
  baseline suite, by 3 or more. *It does not* if neither does. Otherwise not shown.
- Reported: for each suite the faults it catches at all, since a suite whose run of the product's tests runs
  nothing (F42) catches fewer of the 40 than the product's own tests do.

**Predictions.** The product's own tests catch 25 to 35 of 40. Of the survivors a baseline suite catches 0 to 2 and
each plan suite 2 or more above the best baseline, so "not shown" by the bar of 3 is the likeliest reading.

**Limits known before the run.** One build and one case; seeded faults are mechanical edits, not the defects a
person would plant; a fault can leave behaviour unchanged, and such a fault counts as surviving for every suite
alike. The two specification-question suites are slow (156 and 276 seconds a pass).

### Part G, recorded 17:36: tests that pin five gaps in ShipLoop's own checks (no model session)

The second review of section 25 named five places where a released check accepts less than its duty asks. A Sonnet
subagent wrote `shiploop-gaps/gap_checks.py`, which calls the real functions with made-up inputs and prints what
they return; it changes nothing under `skills/`. All five are shown (`shiploop-gaps/gap_checks-output.txt`):

1. `judge` passes a `check` row that exits 0 with empty output, or with any output that holds no runner summary. It
   does fail one whose summary says no test ran, and it catches a listed id marked failed.
2. `check_test_cases` accepts a case that names a criterion other than the one its own focused command declares, as
   long as the criterion is one of the plan's; `coverage_notices` then prints one notice for the orphaned criterion
   and the result is accepted.
3. `_check_intake_questions` accepts an intake result with no question ledger at all, and refuses a malformed one.
4. A plan's concern row is accepted with `decision` and `anchor` of any non-blank text, and a `no` row with a
   one-word reason.
5. `check_submitted` accepts `unverified: []` for product acceptance.

These are today's behaviours pinned as tests, three of them deliberate choices recorded in the code's own comments.
Whether any should change is a product decision for ShipLoop's owner; nothing here changes it.

### Part D1, result (18:05): the plain text marks all three points; where it marks, the plan takes an answer

Nine runs, started together at 17:32:59, all ended normally (a specification took 139 to 168 seconds, a plan 150
to 241). Two
readers, the second a Sonnet subagent given the nine pairs under shuffled names (`r1` to `r9`) and the classes of
the registration, agree on all nine.

| Request | Run | Clauses | `Open:` lines | Class | The answer the plan takes |
|---|---|---|---|---|---|
| limit unsaid | d-limit-1 | 37 | 6 | O+ | 64, "following the existing requester field's size" |
| | d-limit-2 | 44 | 9 | O+ | 200, "matching the existing title scale" |
| | d-limit-3 | 45 | 6 | O+ | 1,024 bytes, so that a name fits a request line |
| states unsaid | d-states-1 | 39 | 7 | I+ | closed refused, resolved allowed (`Source: existing: docs/api.md`) |
| | d-states-2 | 41 | 5 | I+ | the same |
| | d-states-3 | 34 | 8 | I+ | the same |
| due times | d-due-1 | 33 | 13 | O+ | a separate command; the service exits with status 2 on a file that lacks due times |
| | d-due-2 | 34 | 11 | O+ | an offline command; enabled startup refuses |
| | d-due-3 | 36 | 12 | O+ | a `prepare-due` command; enabled startup refuses |

- **RD1.1, room: none.** No request has two runs that decide silently, inherit silently or pass over, so by the
  registered rule no lever is run on *marking*: on Sol at medium, as on Sonnet (F46), the reworded text marks an
  unsaid point by itself, nine of nine.
- **RD1.2: no run requires the refusal with no mark** (0 of 3). Each due-times specification names the three ways
  the service could behave, for example d-due-1's C-20: "Open: The production operator would settle whether
  premature activation refuses startup, keeps serving with the feature hidden, or completes preparation before
  serving."
- **RD1.3:** the two readers agree, nine of nine. The second reader's one doubt: in the states runs the clauses that
  *allow* assignment carry `Source: request`, and only the clause that refuses a closed ticket names the product's
  documentation.
- **Predictions.** Wrong on the limit (I expected two of three to decide or pass over); right on the states, with
  the source named three times and not two; right on the due times.

**F48 (what the registration did not ask, and the runs show). Marking a point open does not change which answer
is built.** All three due-times plans take the answer the owner ruled wrong, a separate preparation step and a
service that refuses to start, and each names filling at start among the alternatives it set aside ("preparing
automatically on start", "Startup preparation ... would tie activation to a mutation", "Startup backfill would
couple initial assignment to service restarts"). The two earlier runs of this text on Sol at **high** took the
other answer and passed 8 of 8 held-out checks (section 21), so the answer taken moves with effort or with the run,
while the mark is constant. On the limit the three plans take three different values. An open point is now visible
and named; whose answer it gets is unchanged. Part D2 below is registered on that.

**A limit of these nine runs found afterwards.** A session sees its working folder's path, and the nine folders
were named `d-limit-…`, `d-states-…` and `d-due-…`. A name that holds the word "limit" could have pointed a session
at the limit. The check below reruns the limit request under neutral names; every later wave uses neutral names,
with the key in its registration.

### Part C, the yardstick tried on two suites whose truth was known (17:39 to 17:46), and a census by reading

`prove_fail.py` (new) runs every check of a suite on the build and on copies that ought to make a check fail: the
starting product, the build with one failing test added to one of the product's own test files (the *sabotaged
copy*), and the build with one seeded fault at a time. It was tried on two Sonnet suites of amendment 12:

| Suite | What was known | Checks | Fail on the starting product | Fail on the sabotaged copy | Never seen failing | Faults unnoticed |
|---|---|---|---|---|---|---|
| q-plan-1 | its two checks that run the product's tests do nothing (F42) | 31 (C-20 fails on the build itself) | 28 of 30 | **none** | none | 4 of 18 |
| q-base-2 | its nested runs work | 29 | 25 of 29 | C-23, C-24, U-5 | none | 4 of 18 |

**F49. The unit of "a check that cannot fail" is the test, and the copy tells more than the check.** Counted by
manifest entry the script saw nothing wrong with q-plan-1: the do-nothing test ("C-19 the existing test suite
passes") shares its entry with a real one ("C-19 PATCH still refuses assignee; ..."), so entry C-19 fails whenever
the real one does. The sabotaged copy separates the two suites cleanly: an existing test made to fail is noticed by
three checks of the good suite and by no check of the bad one. The script now reports a copy that no check noticed
(the refusal's first block), and the trial's lesson is in its docstring. The same four seeded faults go unnoticed
in both suites, all on existing lines (`src/app.js` 16 and 65, `src/format.js` 36 twice).

**A census by reading** (a Sonnet subagent; `evidence/program/hollow-checks/`): of the 82 run folders on file, 46
hold an acceptance suite, and every one of the 46 starts the product's own tests from inside a check (207 uses at
113 places). In 16 suites at least one such run keeps the variable that makes a nested run do nothing, in 13 every
one does, and in 12 at least one of those asks for no evidence that tests ran. Reading cannot say more: whether the
variable is set depends on how the manifest starts each check (30 suites start them with `node --test`, 10 with a
plain `node` runner that registers tests in-process), and the reader did not work that out. The sabotaged copy
answers it directly, so the census is rerun by script (below).

### Part A, result: questions routed to "inspect" are mostly answered on record (a census, no model session)

A Sonnet subagent read the intake results of archived ShipLoop deliveries (`evidence/program/intake-questions/`).
184 runs carry an intake question ledger; 127 are in scope (123 under the E2E runs root from 2026-10-31 on, 4 of
the SDLC study's round 12). They hold 447 questions: 270 routed to `inspect`, 158 to `default`, 15 to
`experiment`, 3 to `person`, 1 to `research`; 24 runs have a ledger with no question. A later stage result or
knowledge file cites the question's id for 121 of the 270 `inspect` questions (54 with two of the question's words
near the id), nearly always in the discovery result. Read by hand, 15 `inspect` questions from 15 runs and 13
cases: 14 have their answer stated in the specification, the environment or the architecture file; one has none (a
Salesforce API version). The script's flags found 10 of those 15 by id and 3 with words: the answer is usually on
record without the id beside it.

**Reading.** The idea "ask after reading, and check that what was routed to inspection got answered" finds little
to fix in the records: answers are there. What the records lack is the join: an id cited beside its answer in 3 of
15. A script could require it; whether that is worth a refusal is ShipLoop's owner's to weigh. Not checked: that
any stated answer is correct. Only three questions of 447 went to a person.

### Registered 18:10, before any of their runs: the rest of part D, parts C and T, part V, part R

Every session below runs on Codex with `gpt-6.2-sol` at medium. Runs are named neutrally; each key is here.

**The apparatus added** (no session has used it): `one_session.py` runs one session in a prepared folder the way
`ratchet.py` runs a stage; `program/prepare.py` makes the folder and the prompt; the texts are
`program/question.md`, `program/revise.md`, `program/review-delivery.md` and `program/review-request.md`, and the
answer sheet `program/replies.json`. `ratchet.py` gains `--tests-question`, `--deliver` and `--duty-at`, and
`prove_fail.py` gains the report of a copy no check noticed, `--lines` and `--only`. A default run's ten prompts are
byte for byte those of the committed runner, none of its 25 text constants changed, and the self-test passes.

#### D1 check: the limit request under neutral names (3 runs)

`n1` to `n3`: `ticket-assignment-name-limit-unsaid`, the spec stage only. **Reading:** the class of each (the
registration's O, D, P; a specification alone cannot be O+). The nine-run result stands if at least two of three
mark the limit open; if not, the folder names carried it, and F46's extension to Sol is withdrawn.
**Prediction:** three of three mark it open.

#### Part D2: one question to the requester (9 sessions, then up to 18)

**What it asks.** F48: the point is marked and the wrong answer is still taken. The first review's third
experiment: does a session that may ask one thing ask the thing that matters, and does the answer reach the plan?

**Cells.** `g1` to `g9`, one for each run of part D1 (g1 to g3 the limit runs 1 to 3, g4 to g6 the states runs,
g7 to g9 the due-times runs): a fresh session is given the starting product and the specification as the spec
stage left it, and `program/question.md`: choose the one point where the requester's answer matters most, and
write the question with its alternatives, what happens if no answer comes, and the next two points.

**The stand-in requester** is `program/replies.json`, written before any question: one point for each request,
with its reply (due times: the service fills the missing due times when it starts switched on and never refuses to
start, the owner's ruling; the limit: at most 40 characters, a value no precedent in the product suggests; the
states: the sentence taken out of the request). A question that asks about the request's point gets its reply; any
other question gets "No preference. Use your judgement." I decide which it is, and a Sonnet subagent sorts the nine
questions a second time without my sorting.

**Then, only for a question that asked the point:** `h<n>` revises the specification with the answer
(`program/revise.md`), and `j<n>` plans from the revised specification (`ratchet.py --spec-from`, the plan stage as
it stands).

**Readings.**

- **RD2.1, the one question.** For each request, in how many of three runs `Question:` asks the request's point;
  and in how many it is one of the two `Next:` lines.
- **RD2.2, a question the files answer.** How many of the nine questions ask something the product's files settle
  (two readers).
- **RD2.3, the answer carried.** For each run that asked the point: the revised specification states the reply as
  a requirement with `Source: answer`, and the plan follows it (due times: filled at start and no refusal; the
  limit: 40; the states: open and in progress only). *One question reaches the plan* if, for the due times, at
  least two of three runs ask the point and every one that asks carries the answer. Fewer than two asking: the
  mechanism fails at choosing, whatever follows.

**Predictions.** Due times: two of three ask the point. The limit: at most one of three (name identity or the
success response may look weightier). The states: none of three asks (the product's rule looks settled, and
nothing in the folder holds this requester's stricter wish). Every answer given is carried.

**Limits known before the runs.** A scripted requester answers at once and has an answer; a real one may have
neither. One answer changes a specification that was written without it: the clauses around it were drafted for
the other reading. The plan is read, not built.

#### Parts C and T: three levers on the test pass, on one base (1 run, then 12 test passes)

**What they ask.** Three ideas act on the same stage and are read on the same yardsticks: a check must be able to
fail (C); a question about preserved behaviour put to the test owner, in general words (T, general) or asked of
the files the change touched (T, grounded).

**Base.** `c0`: specification and plan for `ticket-assignment`, the reworded text, Sol at medium. Every test pass
starts from them and from the reference build (`--plan-from c0 --build-from <the reference> --stop-after tests`).

**Cells,** three runs each: `ta1` to `ta3` plain; `tb1` to `tb3` with `--prove-fail` (after the test session the
script runs `prove_fail.py`, shows the session what it found once, and the session works again); `tc1` to `tc3`
with `--tests-question general`; `td1` to `td3` with `--tests-question grounded`.

**Yardsticks no session is shown.**

- **Y1, planted defects** (`grade.py strength`): caught of 27; checks failing on the reference; checks failing on
  the second correct delivery.
- **Y2, faults in existing code** (`mutate.py --unchanged --manifest`, all 52 sites): how many the acceptance
  checks catch, and how many of those the product's own tests miss. The proof of failure shows a session only
  faults on even-numbered lines, so the **odd-numbered lines** are the yardstick for every arm, and the count on
  all lines is reported beside it.
- **Y3, the sabotaged copy** (`prove_fail.py --only sabotage`): does any check fail when an existing test is made
  to fail.
- Cost: seconds of the test sessions, checks written.

**Readings.**

- **RC.0, room.** Over the three plain runs: planted defects missed, odd-line faults that survive the acceptance
  checks, runs where the sabotaged copy goes unnoticed.
- **RC.1.** An arm *protects existing code* if each of its three runs catches at least 2 more odd-line faults than
  the best plain run. It *does not* if none of its runs beats the best plain run. Otherwise not shown.
- **RC.2, the defect the suites miss.** `update-rejects-resolved` (an edit of a resolved ticket is refused) was
  missed by 6 of the 7 Sonnet suites of amendment 12. An arm *catches it* if all three of its runs do and at most
  one plain run does.
- **RC.3, harm.** An arm is *over-tight* if each of its runs fails more checks on the second correct delivery than
  the worst plain run.
- Reported: Y3 for each run, and for `tb` what the script found before and after its refusal.

**Predictions.** Plain: 25 or 26 of 27; odd-line faults caught about as many as the product's own tests catch
(part E so far: 31 against 31 of 40); the sabotaged copy unnoticed in one of three. With the proof of failure: the
sabotaged copy noticed three of three after the refusal; odd-line faults up by one or two, so RC.1 not shown. The
grounded question: catches `update-rejects-resolved` in two of three; the general one in one of three.

**Limits known before the runs.** One case, one build, one specification and plan; a fault shown on an even line
can teach a check that also catches the fault on the next odd line; three runs an arm; the reference build is
correct, so nothing here says what a lever does on a build with a real defect.

#### Part C, the census by script (no model session)

`prove_fail.py WORK - OUT --only sabotage --changed 0 --unchanged 0` on each of the 46 suites on file whose work
folder holds an acceptance suite and whose starting product had a test file. **Reading:** the suites in which no
check fails on the sabotaged copy, by model family, beside the count from reading (16 with a nested run that keeps
the variable). **Prediction:** between 5 and 12 of the suites that can be measured.

#### Part V: the stage text through a command, and where the written question stands (18 runs)

**What it asks.** The session "Spec elaboration" found that on Codex the model is given only what its own script
shows it of a command's output, and that ShipLoop's later packets often arrive at under a third. Here every stage
text is in the prompt. Does the channel matter at this text's size (108 lines, 9.7 thousand characters; the 28 stage
packets of one archived ShipLoop run are 14 to 57 thousand), and does it matter where in the text a checked duty stands?

**Cells.** `ticket-assignment`, the spec stage only, the reworded text with the rules question (`--rules
spec-section`), three runs each: delivery in the prompt or through a command (`--deliver command`: the prompt
names one command whose output is the whole text), with the question first (line 6), in its standing place (line
54) or last (line 88). `v1` to `v3` prompt and first, `v4` to `v6` prompt and standing, `v7` to `v9` prompt and
last, `v10` to `v12` command and first, `v13` to `v15` command and standing, `v16` to `v18` command and last.

**Readings.**

- **RV.1, what arrived.** For the command runs, from Codex's own record of the session: the share of the text's
  non-blank lines among the outputs the model was given, and whether every line of the question was.
- **RV.2, the duty done.** The specification has a `## Rules and edge cases` section with at least one entry.
  *The channel matters* if the nine command runs have it in at least three fewer runs than the nine prompt runs.
  *The place matters* if, within one channel, one place has it in three of three and another in at most one.

**Read first, with no model** (`program/packet_position.py`, which reads the sister study's archived runs with
that study's own reader and changes nothing; run while it was written, `evidence/program/delivery/`). In 62
archived Codex runs of ShipLoop, four early stages each, 248 packets: of the instruction lines 97% were given on
average, 94% of the first third, 99% of the middle, 96% of the last, with no trend by length. What goes missing
stands after the instructions: of the lines after the result template (the template and the list of references)
the median packet's share given is 100% at intake, 94% at discovery, 52% at research and 15% at the spec stage. So
in ShipLoop the instructions arrive and the tail of the packet often does not. The runs below ask whether a duty
placed at the end of a shorter text is lost the same way.

**Predictions.** In the prompt the section is written nine of nine. Through the command the whole text is shown in
at least seven of nine and the section written in at least eight of nine; no place effect at this size.

**Limits known before the runs.** One text of one size; ShipLoop's packets are one and a half to six times as long, and a
later packet repeats much of an earlier one, which this bench does not have.

#### Part R: a fresh review of a finished change (24 sessions)

**What it asks.** The first review's fourth experiment. A green gate has passed a wrong product here before
(section 10: the due-times loop ended green on its own gate with 5 of 8 held-out checks failing from its first
build to its last).
Does a fresh reviewer catch what the gate missed, and does it matter whether the reviewer starts from the request
and the starting product, or from the delivery's own specification and checks?

**The four deliveries,** each with a green gate of its own, frozen before any review:

- `ka`, **wrong, and plainly so.** The ticket-assignment reference with the planted defect
  `update-rejects-resolved`: an edit of a resolved ticket is refused, where the product's documentation says only a
  closed ticket can no longer change. Its record is the specification, plan and checks of q-base-2. Checked
  before the registration: the product's own 122 tests pass and all 29 acceptance checks pass. **Right verdict:
  reject, with that finding.**
- `kb`, **right.** The reference itself, with the same record. **Right verdict: accept.**
- `kc` and `kd`, **two builds that differ on a point the request leaves open.** The final builds of
  p3-ticket-due-times-sol-high (it refuses to start on a file without due times) and p3R-ticket-due-times-b (it
  fills them at start), each with its own record. The owner later ruled for filling; the request does not say.
  **Right behaviour: the decision is listed under "Decisions made for the requester", whatever the verdict.**

**Cells.** Each delivery, two arms, three sessions: arm `x` starts from the delivery's own record
(`program/review-delivery.md`), arm `y` writes down what must be true from the request and the starting product,
tries it, and only then reads the record (`program/review-request.md`). Runs `w<delivery><arm><n>`, for example
`wax1`. The starting product stands outside the work folder: inside it, the product's own test command ran its
tests too (found while preparing; 239 tests for 122).

**Readings.**

- **RR.1, the wrong build.** For each arm, in how many of three sessions the verdict on `ka` is reject *with a
  finding that names the refused edit of a resolved ticket* (two readers). *A fresh review catches it* if an arm
  does so in at least two of three while accepting `kb` in at least two of three. *Starting from the request
  matters* if arm `y` does so in at least two more sessions than arm `x`.
- **RR.2, the right build.** Sessions that reject `kb`, with their reason.
- **RR.3, the open decision.** For `kc` and `kd`, in how many of three sessions each arm lists the start-up
  decision; and the verdicts.
- Reported: seconds, findings and whether each names a probe.

**Predictions.** Arm `x` catches `ka` in at most one of three; arm `y` in two of three; `kb` is accepted in at
least five of six; the start-up decision is listed for `kc` in at least five of six and for `kd` in at most three
of six (a service that simply works draws no remark).

**Limits known before the runs.** One planted defect, chosen because suites miss it; the bundle is curated, so a
catch shows the mechanism, not how often real deliveries need it; the reviewer and the builders are one model
family.

### D1 check, result (18:14): under neutral names the limit is marked open three of three

`n1` to `n3` (32, 42 and 37 clauses; 161 to 185 seconds): each specification marks the limit open and none states
one. n1, C-2: "any separate name length bound beyond the existing HTTP body limit"; n2, C-7: "whether to set a
name-specific length bound beyond the existing whole-body limit"; n3, C-7: "any name-specific length bound beyond
the existing request-body limit". The folder names did not carry the nine-run result, and F46 holds on Sol at
medium: six of six.

### Part D2, result (18:16): a session given one question does not ask the point that decided the builds

Nine sessions, 26 to 52 seconds each, every one wrote `ratchet/question.md` in the form asked and changed nothing
else. Two readers (the second a Sonnet subagent given the nine files under shuffled names, with the three points
and a copy of the starting product) agree on every sorting.

| Request | Its point | `Question:` asks the point | A `Next:` line names it | What the three sessions asked |
|---|---|---|---|---|
| limit unsaid (g1 to g3) | the longest name | 0 of 3 | 0 of 3 | who turns an agent's name into a mail address: the relay, or a directory the operators keep |
| states unsaid (g4 to g6) | the states that allow assignment | 0 of 3 | 0 of 3 | the same question, three times |
| due times (g7 to g9) | who fills the due times in, and what the service does at start | 0 of 3 | 1 of 3 (g9, third) | whether the deadlines must survive a roll-back to 1.4.0 and a later upgrade, or may be worked out again |

- **RD2.1: the one question asks the request's point in none of nine runs.** By the registered rule the mechanism
  fails at choosing, so no specification is revised and no plan made under this part. My prediction for the due
  times (two of three) was wrong; for the states (none) it held; for the limit (at most one) it held.
- **RD2.2: none of the nine asks what the files settle.** Each question rests on something read in the product
  (the notifier hands a recipient on as it is given; release 1.4.0 keeps only the fields it knows) and asks what
  the files cannot say: how the relay treats a name, what the requester wants after a roll-back.
- **RD2.3: not run**, since no question asked the point.

**F50. Asked what matters most, a session ranks by cost, and the requester's own answer was not the costly kind.**
The sessions agree with each other (three of three on each request, six of six across the two assignment
requests) and their questions are good ones by the rule they were given: a notice that silently reaches nobody, a
promised deadline that silently moves. The point that failed five of eight held-out checks is of another kind. A
service that refuses to start says so at once and is cheap to change, so by cost it ranks low; it mattered
because the requester had a preference about it. Nothing in the folder says which low-cost choices a requester
holds a view on, and a ranking by cost cannot find them. What would have shown this requester the point is the
plan's own `## Decisions` table: the refusal is a row of it in all three due-times plans, with filling at start
among the alternatives set aside, and the limit taken is a row in all three limit plans. The stricter wish about
states is in no table: the specifications applied the product's rule as a fact (I+), and a fact is not listed as a
decision. So of the nine runs the decisions table shows the point in six and a single question in none.

**Limits.** One model at one effort; the question text asks for the *one* point by cost, and another rule of
choice (the point a requester most likely holds a view on) is untested; three requests on one code base.

### Part D3, registered 18:16, before any of its runs: the answer given directly, into the plan and into a build

**What it asks.** D2 tested the choosing and it failed. The other half of any way of asking is untested: when the
requester's answer does arrive, is it carried, and is the built product then right where the plain one is wrong?

**The question put** is no longer a session's. It is written here once for each request
(`program/decision-questions.json`), as to a requester who was shown the decision the plan takes, and the reply is
the one in `program/replies.json`. For the due times: "The specification leaves open how the tickets already in
the data file get their due times. Left to itself the plan adds a separate preparation command that an operator
runs, and has the service refuse to start with DUE_TIMES=on while any ticket lacks a due time. The alternative is
that the service itself gives the missing due times when it starts switched on. Which do you want?" For the limit:
"The request gives no longest length for an agent's name, and left to itself the plan takes a limit of its own. Is
there a longest length you want?"

**Cells.**

- `h1` to `h3` (the limit specifications of d-limit-1 to 3) and `h7` to `h9` (the due-times specifications of
  d-due-1 to 3), each as the spec stage left it: one session revises the specification with the question and the
  reply (`program/revise.md`).
- `j1` to `j3`: the plan stage from the revised limit specifications.
- `b7` to `b9`: plan, build and test pass from the revised due-times specifications (`--spec-from h<n>
  --stop-after tests`).
- `p7` to `p9`: plan and build from the same three specifications without the answer (`--spec-from` the
  specification as the spec stage left it, `--stop-after build`).

**Readings.**

- **RD3.1, into the specification.** The revised specification states the reply as a requirement with `Source:
  answer` and no longer marks it open (a script finds the source line; two readers read the clause).
- **RD3.2, into the plan.** The plan follows the reply: 40 for the limit (`j`), filling at start and no refusal
  for the due times (`b`).
- **RD3.3, into the build.** The held-out checks (`grade.py snapshots`, eight of them) on the first build of each
  `b` and `p` run. *An answer reaches the product* if all three `b` builds pass at least seven of eight and at
  least two of the three `p` builds fail three or more.
- **RD3.4, into the delivery's own checks.** For each `b` run: the acceptance check of the clause that carries
  `Source: answer` exists, passes on its own build, and fails on the first build of the `p` run made from the same
  specification (the check laid over that build by script).
- Reported: seconds for each stage; what else the revise session changed.

**Predictions.** Carried into all six specifications and all six plans. The three `b` builds pass eight of eight;
the three `p` builds fail five of eight. The answer's check fails on the paired plain build in at least two of
three.

**Limits known before the runs.** The question is mine and names both alternatives, so this is the mechanism at
its best; three runs an arm; the plain arm stops after the build, since its own tests add nothing to these
readings; the limit is read in the plan only.

### Part V, result (18:20): at this size the text arrives whole through a command, and the duty is done wherever it stands

Eighteen runs, 158 to 229 seconds each, every one a single spec session (no refusal), launched from
f413b280a06c6c20616b2e5c04ccf06ac21bb8dc (`evidence/program/delivery/shown.txt`, `runs.json`).

| Delivery | The question stands | Lines of the text given to the model | Lines of the question given | `## Rules and edge cases` written (entries) |
|---|---|---|---|---|
| prompt | first | in the prompt | in the prompt | 3 of 3 (6, 8, 9) |
| prompt | standing | in the prompt | in the prompt | 3 of 3 (11, 9, 11) |
| prompt | last | in the prompt | in the prompt | 3 of 3 (12, 13, 8) |
| command | first | 83 of 83, three times | 7 of 7, three times | 3 of 3 (9, 9, 10) |
| command | standing | 83 of 83, three times | 7 of 7, three times | 3 of 3 (11, 12, 9) |
| command | last | 83 of 83, three times | 7 of 7, three times | 3 of 3 (8, 7, 6) |

- **RV.1:** in all nine command runs Codex's own record shows the model was given every non-blank line of the
  text. Its first tool call is the command the prompt names, and each time the model's script raises its own limit
  on the output it shows itself (`max_output_tokens` of 15,000 to 24,000).
- **RV.2: the channel does not matter and the place does not matter** at this size: the section is written in 18
  of 18. Both predictions held.

**F51. What ShipLoop loses on Codex is the tail of a long packet, not the channel and not a place within the
instructions.** A text of 108 lines given as a command's output arrives whole, nine of nine, when the prompt says
to read all of what the command prints. In 62 archived Codex runs of ShipLoop the instruction lines also arrive (97%
on average, no third of the packet below 94%), and what goes missing stands after them: the result template and
the list of references, a median of 15% given at the spec stage. So a duty belongs in the instructions, where it
is read, and a pointer that matters should not live only in the references after the template. Whether the tail is
lost because of its length or because the model takes it for reference material is not separated here.

**Limits.** One text of 9.7 thousand characters, one stage, one case; the prompt of the command runs says "read
all of what it prints", which ShipLoop's own entry text may not; no run here has a packet as long as ShipLoop's.

### A note on yardstick Y2, written at 18:22 while the test passes of parts C and T are still running

Part E's replay (six of seven suites done; its result follows when the last one ends) shows where the seeded
faults that survive sit. Of the 40 faults on existing lines, the product's own tests catch 30 or 31, and seven
survive every suite replayed so far: two in the request log (`src/app.js` lines 16 and 65), one in the table
formatter (`src/format.js` line 36), and four in the checks a data file gets when it is loaded
(`src/persistence.js` lines 92, 160 twice, 170). Two more in the table formatter are caught by one suite each and
by no other. None is behaviour that ticket assignment touches; they are gaps
of the product's own tests in files the change happened to edit. So Y2 has little room that a test pass for this
change ought to fill, and a run that did catch them would be testing code the request does not concern. RC.1 is
read as registered; this note says beforehand that "not shown" on Y2 would not mean a lever failed to protect what
the change touched, and that the defect a change can plausibly cause (RC.2) is the better reading of protection.

### Part D3, result (18:36; its fourth reading follows when the test passes end): the answer is carried into the specification, the plan and the build

Launched from daf3fe89d032747df17d8fd8acabaf9abefb51a1. Six revise sessions (21 to 63 seconds), three plans for the
limit, three answered runs through plan, build and test pass, three plain runs through plan and build.

| Reading | The limit (`h1` to `h3`, `j1` to `j3`) | The due times (`h7` to `h9`, `b7` to `b9`, against `p7` to `p9`) |
|---|---|---|
| RD3.1, in the specification, `Source: answer` | 3 of 3: one new clause each, accepted at 40 and refused at 41 | 3 of 3: the use case and the preparation clause rewritten ("Missing due times alone never cause startup to fail"), the open line about refusing removed |
| What else the revise session changed | nothing (5 lines added, 1 removed, each time) | nothing outside the use case and the clauses about preparing and starting: 6, 3 and 3 items touched, 13, 8 and 6 lines added |
| RD3.2, in the plan | 3 of 3 take 40 | 3 of 3 fill at start; the three plain plans again take a separate command and a refusal |
| RD3.3, held-out checks on the first build | not built | answered 8, 8 and 8 of 8; plain 3, 3 and 3 of 8 (`cli`, `migrate`, `restart`, `rollback`, `switch` fail each time) |

- **RD3.1 and RD3.2: carried, six of six**, with no other change to the specification.
- **RD3.3: an answer reaches the product.** All three answered builds pass every held-out check; all three plain
  builds, made from the same three specifications by the same stages, fail the same five. The plain runs' own gate
  is green each time.
- With part D1's three plans, **six of six plans made without the answer take the refusal** on Sol at medium.

**F52. One sentence from the requester is worth five of eight held-out checks here, and nothing else tried in this
pilot moved them.** The specification text, the plan stage and the build stage are the same in both arms. What
differs is one use case and a few clauses of the specification, 6 to 13 lines that say what the requester wants.
The cost of carrying it is one session of about a minute. So the lever on this failure is neither wording nor effort but getting the answer, and
F50 says a single question chosen by cost does not get it while the plan's decisions table shows where to ask.

**One session record holds a held-out mark, and it is not held-out material.** The build session of `b9` listed
the machine's processes, and the listing held the command line of another session's consultation, whose question
names the harness's folder. Codex's own record shows the model was given that listing. Nothing of the held-out
checks is in it, and no other plan or build session of the `b` and `p` runs holds a mark.

**Limits.** The question was mine and named both alternatives; a real requester has to notice the row. One
request, three specifications, one model at one effort. A build session took 341 to 519 seconds with the answer
and 359 to 419 without.

### Part R, result (18:36): a fresh reviewer finds the planted defect six times of six, every finding it reports is true, and its verdict cannot be used as a gate

Twenty-four sessions, 91 to 320 seconds each, launched from f413b280a06c6c20616b2e5c04ccf06ac21bb8dc. Every one
wrote `ratchet/review.md` in the form asked and changed nothing else; none changed the starting product. Two
session records hold the repository's name: it is the path of the harness's own Python shim inside the session's
home, printed by a `which`, and no held-out file.

| Delivery | Arm | Verdicts | Findings | Names the planted defect | Lists the start-up decision | Seconds |
|---|---|---|---|---|---|---|
| `ka`, wrong | from the record | reject, reject, reject | 4, 4, 3 | 3 of 3 | | 94 to 136 |
| | from the request first | reject, reject, reject | 2, 3, 2 | 3 of 3 | | 183 to 227 |
| `kb`, classed right | from the record | reject, reject, reject | 4, 4, 2 | has none: 0 of 3 | | 91 to 127 |
| | from the request first | reject, reject, reject | 1, 2, 3 | 0 of 3 | | 191 to 211 |
| `kc`, refuses at start | from the record | reject, reject, reject | 5, 4, 4 | | 3 of 3 | 215 to 262 |
| | from the request first | reject, reject, reject | 3, 2, 4 | | 3 of 3 | 242 to 320 |
| `kd`, fills at start | from the record | accept, reject, accept | 0, 1, 0 | | 3 of 3 | 114 to 128 |
| | from the request first | reject, reject, reject | 1, 2, 2 | | 3 of 3 | 231 to 312 |

**Every finding was checked by running the products** (two Sonnet subagents, one for each case, given the reviews,
the four deliveries and the starting product; `evidence/program/fresh-review/findings-checked.md`): the 24 reviews
make 62 findings, 17 of them distinct, and **all 62 reproduce**. Nothing could not be run.

- **RR.1, the wrong build.** Both arms reject `ka` with a finding that names the refused edit of a resolved
  ticket, three of three each (the second reading agrees on all six; no review of `kb` reports it, and `kb` does
  not have it). But no session accepts `kb`, so **by the registered rule "a fresh review catches it" is not met**:
  the rule asked for the right build to be accepted in two of three. *Starting from the request does not matter*:
  three against three.
- **RR.2, the build I had classed as right.** `kb` is rejected six times of six, and each time for something
  true. The reference delivery changes the shared matcher in `src/tickets/query.js` from `some` to `every`, so the
  command line's `list --status S --priority P` now shows tickets that match both where it showed tickets that
  match either: all twelve reviews of `ka` and `kb` report it. The other five (a fifth field in `list --raw`; `-`
  shown both for no assignee and for an agent named `-`; a hand-edited 65-character assignee loaded; a second
  notice to the same agent not queued while the first is pending; a repeated `assignee` parameter read by its
  first value) are true as well. **My classification of `kb`, frozen before the reviews, was wrong by the rule
  the reviewers were given.** The held-out checks do not look at the command line's filters, so the reference
  passes them.
- **RR.3, the open decision.** All twelve due-times reviews list how the existing tickets get their due times
  under "Decisions made for the requester", for both builds and in both arms. I predicted at most three of six
  for the build that fills at start. No review rejects `kc` for refusing to start.

**The seventeen distinct findings by kind**, sorted by me before the second reader's sorting came back and by a
Sonnet subagent (`evidence/program/fresh-review/kinds.md`); the two agree on the letter for 11 and on break against
no break for 16 of 17:

| Kind | Findings | In ordinary use | Only with hand-edited data, a failing disk or a number at the edge |
|---|---|---|---|
| A break: the request's own words, or existing behaviour it does not ask to change (both readers) | 7 | 3: the planted defect; the command line's filters (`ka`, `kb`); the HTTP list's filters with the switch on (`kc`) | 4, all in `kc` with the switch off |
| No break: a choice on an open point, or a gap in new behaviour (both readers) | 9 | 5 | 4 |
| Disputed | 1 (the second notice not queued: a break of "the agent ... is notified" to me, satisfied by the pending notice to the second reader) | 1 | |

Read with the verdicts: the 18 rejections of `ka`, `kb` and `kc` each rest on at least one finding both readers
class as a break. The four rejections of `kd` rest on none: on a ticket created while the switch is off taking its
due time from the priority it has when the switch goes on (three reviews), on an hours setting too large to
represent (two), on due times lost when release 1.4.0 saves the file (one). `kd` is the only delivery with no
break found, and it is accepted twice in six, both times by the arm that starts from the record.

**F53. A fresh reviewer is a sharp finder and a poor gate.** In one and a half to five minutes a session that
built nothing reports what the delivery's own gate, its 29 or more acceptance checks and the held-out checks all
passed: the planted defect six times of six (six of seven acceptance suites had missed it), and a change to
existing behaviour in the reference delivery itself. Not one of 62 findings is false. But the verdict follows the
findings without weighing them: a delivery with no break is still rejected four times of six, for a choice the
request leaves open read as a requirement. The findings are the product of a review; the accept or reject line is
not.

**F54. Starting from the request first did not help, and cost more.** It caught the planted defect as often
(three of three in each arm), reported fewer findings (27 against 35), took longer (235 seconds on average
against 149), and on the one delivery with no break it rejected three times of three where the other arm rejected
once: having written down what must be true, it held the build to its own reading. The first review expected the
opposite; three sessions an arm on four deliveries is what this rests on.

**F55. The same quirk of the starting product was changed, unasked, by two deliveries from different runs, and no
suite or held-out check noticed.** The product's documents say a listing matches every filter given; its code
matches either. The ticket-assignment reference changes it everywhere, the due-times build `kc` changes it when
the switch is on, and `kd` leaves it. Part D1's specifications mark exactly this as open ("the requester would
resolve the discrepancy"). A place where the documents and the code of the starting product disagree is a
decision, and it is being made by whoever touches the file.

**Limits.** Four deliveries, curated; one planted defect, chosen because suites miss it; the reviewer and the
builders are one model family, and the checkers and second readers another; "no break" for `kd` means none was
found by six reviews and two readers, not that none exists. Whether the reference's change to the command line is
a defect of the E2E harness's reference or a welcome fix is its owner's to say.

### Part D2b, registered 18:40, before any of its runs: three questions of three kinds (exploratory, nine sessions)

**What it asks.** F50: one question chosen by cost asks the request's point in none of nine runs. Does a session
that may ask three, one by cost, one about ordinary use and one about a place where what exists disagrees with
itself, ask it? **Exploratory:** the three kinds were written after part D2's result and with the due-times point
known to me. A hit would show that the point can be reached by a rule of choice; it would not show that this rule
is the right one.

**Cells.** `k1` to `k9`: as `g1` to `g9` (the same nine specifications of part D1, the same folders), with
`program/question-three.md` in place of `program/question.md`.

**Readings.**

- **RD2b.1.** For each request, in how many of three runs one of the three questions asks the request's point, and
  under which kind (two readers, the second without my sorting).
- **RD2b.2.** How many of the 27 questions ask what the product's files settle.
- Reported: what the third kind turns up. This product holds one such place (F55: its documents say a listing
  matches every filter given, its code matches either).

**Predictions.** Due times: the ordinary-use question asks the start-up point in two of three. The states: the
ordinary-use question asks which states allow assignment in one of three. The limit: none of three. The
disagreement question names the filters in at least six of nine.

### Part D2b, result (18:44): three questions of three kinds still miss the point, and every session finds the place where the product disagrees with itself

Nine sessions, 33 to 51 seconds, launched from 545c432df9603a982e5372ebc43cb35cfcffc77f; each wrote the file in
the form asked and changed nothing else. Two readers agree on every sorting (the second a Sonnet subagent with the
files under shuffled names; `evidence/program/one-question/three-questions*.md`).

| Request | A question asks the request's point | Cost | Ordinary use | Disagreement |
|---|---|---|---|---|
| limit unsaid (k1 to k3) | 0 of 3 | who turns a name into a mail address, three times | whether `Dana` and `dana` are one agent (twice); whether a resolved ticket keeps its assignee | the filters: both, or either (3 of 3) |
| states unsaid (k4 to k6) | 0 of 3 | the same, three times | capital letters (twice); spaces around a name | the filters (3 of 3) |
| due times (k7 to k9) | 0 of 3 | deadlines after a roll-back, three times | whether the command line shows the deadline, three times | the filters, for an overdue listing (3 of 3) |

- **RD2b.1: none of nine.** With three questions the request's own point is still not asked: 27 questions, none on
  the longest name, the states that allow assignment, or who fills the due times in. My predictions (two of three
  for the due times, one of three for the states) were wrong.
- **RD2b.2: none of the 27 asks what the files settle.**
- **The third kind works: nine of nine name the one place where this product's documents and code disagree**
  (a listing "matches every filter given"; the code matches either), and one asks outright whether the command
  line should change with the API. That is F55's place, which two deliveries changed unasked and which every
  reviewer of part R reported.

**F50 stands, more firmly, and gains a second half.** Thirty-six questions over two wordings do not reach the
choice that sank the builds: a session does not see the plan's future answer to an open point as a question worth
the requester's time, whichever way the question is framed. What a question step does reach, every time, is a
disagreement that already stands in the files. So of the two things a requester needed to be asked here, the
disagreement can be found by asking for it, and the preference cannot be found by asking the session to guess
which preference matters; it shows only when the decision taken is put in front of the requester.

**Limits.** Exploratory: the kinds were written after part D2 and with the due-times point known to me. One
product, with one known disagreement that is easy to see once looked for.

### Part D3, the fourth reading (18:47): the delivery's own check tells the answered build from the plain one, three of three

The three answered runs ended their test passes (682, 739 and 796 seconds; 41, 41 and 43 checks; the first leaves
one check failing on its own build, the other two none). `program/answer_check.py` ran each run's checks on its
own build and on the first build of the plain run made from the same specification
(`evidence/program/answer-carried/answer-checks.json`).

- **RD3.4: three of three.** In each run the two items that carry `Source: answer` (the use case and the clause on
  filling at start) have a check that passes on its own build and fails on the plain build. My prediction was at
  least two of three.
- On the plain build 16, 13 and 14 of each suite's checks fail in all: a build made without the answer does not
  pass the acceptance suite written with it.

So the answer is carried through every stage that exists here: specification, plan, build, and the delivery's own
acceptance checks. The first review's third experiment asked for exactly this chain ("carry the reply into
acceptance"); it holds, given the answer.

### Part E, result (18:50): an acceptance suite adds almost nothing to what the product's own tests catch in existing code, and what survives is not what the change touches

The replay ran from 17:36 to 18:49 (the two suites with the question in the specification take 156 and 276
seconds a pass), from f83631bc5ff33238ab7fd553524d35e226b2dbad; `evidence/program/existing-code-faults/replay.json`
holds every fault with its outcome for each suite.

| Suite | Cell of amendment 12 | The product's own tests catch | The acceptance checks catch | Caught by the checks and missed by the own tests | Survive both |
|---|---|---|---|---|---|
| q-base-1 | baseline | 31 of 40 | 31 | 0 | 9 |
| q-base-2 | baseline | 31 | 31 | 0 | 9 |
| p1S-ticket-assignment-medium | baseline | 30 (one run did not end) | 30 | 0 | 9 |
| q-spec-1 | question in the specification | 31 | 31 | 0 | 9 |
| q-spec-2 | question in the specification | 30 (one run did not end) | 31 | 0 | 9 |
| q-plan-1 | question in the plan | 30 (one run did not end) | 28 | 1 (`src/format.js` line 43) | 9 |
| q-plan-2 | question in the plan | 31 | 32 | 1 (`src/format.js` line 36) | 8 |

Where a run of the own tests did not end, the fault it was on is caught by the own tests in every other replay, so
it is not counted as missed by them.

- **RE.1, room.** The product's own tests catch 31 of the 40 faults and 9 survive them.
- **RE.2: not shown.** Each plan suite catches one fault the own tests miss and no baseline suite catches any, so
  the plan suites are ahead, by one where the bar was three. My prediction was two or more above the best
  baseline, and "not shown".
- **What survives.** Seven faults survive every suite: two in the request log, one in the table formatter, four in
  the checks a data file gets when it is loaded. The two that one plan suite each catches are in the table
  formatter. None is behaviour that ticket assignment changes.
- q-plan-1's checks catch fewer faults than the product's own tests (28 against 30): its two checks that run those
  tests run nothing (F42).

**F56. Seeded faults on the existing lines of touched files measure the product's old test gaps, not the change's
care.** An acceptance suite written for a change mirrors the product's own tests on existing code (31 against 31)
because it tests the change and runs those tests; the faults nobody catches sit in code the request does not
concern. A lever that raised this number would be buying tests of the request log and of file validation in a
delivery of ticket assignment. The hand-planted defects that a change can plausibly cause (a guard tightened, a
default moved, a notice replaced) remain the better yardstick of protection, and a fresh review found the one of
them that suites miss (F53).

**Limits.** One build, one case, forty mechanical faults; suites by one model at one effort.

### Part R, the other half, registered 18:53 before its runs: a fresh reader of a specification (three sessions)

**What it asks.** The program's table gave part R two halves; the review of a finished product is done. The other:
does a session that did not write a specification find the clauses in it that decide beyond the request?

**The specification and its known over-decisions.** `c0`'s, written by Sol at medium for `ticket-assignment`, as
its plan stage left it (45 clauses: the spec stage wrote 44 and the plan stage added C-45). Eight test passes written from it (parts C and T, the ones ended by now) were run on the correct
reference build, and two clauses' checks fail there in all eight because the reference does not do what the clause
requires, where neither the request asks for it nor the starting product does it:

- **C-34**, "A data file with an invalid assignee value is refused", for a saved assignee of 65 letters. Its source
  line names the product's documents; the product's loader checks no length (it loads an over-long requester or
  title too).
- **C-45**, "A failed save leaves the last successful ownership state intact". The starting product keeps a change
  in memory when a save fails (part R's finding C5 shows it), and the request does not speak of it.

Two more fail in most passes and are not targets: C-44 is about which new tests exist, and C-40's failure is a real
weakness of the reference (`-` shown both for no assignee and for an agent named `-`).

**Cells.** `s1` to `s3`: a fresh session is given the starting product and that specification (the plan itself is
not in the folder), and `program/spec-reader.md`: list the clauses that decide beyond the request, after checking each claim
about existing behaviour in the product's files.

**Readings.** **RR1.1:** in how many of three sessions each target is listed. *A fresh reader finds a
specification's unasked decisions* if both targets are listed in at least two of three. **RR1.2:** how many other
clauses a session lists, and whether it lists C-40 (which would be a wrong flag). Reported: seconds.

**Predictions.** C-45 is listed in two of three, C-34 in one of three, and each session lists five to ten other
clauses, which nothing here can score.

**Limits known before the runs.** One specification, two targets; the targets are what suites happened to test and
the reference happened not to do, so a clause listed and not among them may be just as right.

### Part R, the other half, result (18:56): three fresh readers each list exactly the two clauses that reject a correct build

Three sessions (52, 71 and 93 seconds), launched from b23da050d896de4cb94e0a6375045a4fc5e00865; each wrote
`ratchet/reading.md` in the form asked and changed nothing else (`evidence/program/spec-reader/`).

| Session | Listed under "Decided beyond the request" | Clauses it says it checked in the product's files |
|---|---|---|
| s1 | C-45, C-34 | 37 |
| s2 | C-45, C-34 | 39 |
| s3 | C-45, C-34 | 33 |

- **RR1.1: both targets in three of three**, so *a fresh reader finds a specification's unasked decisions*. I
  predicted two of three and one of three.
- **RR1.2: no other clause is listed, by any session**, and C-40 is not. I predicted five to ten others each.
- Each entry gives the reason from the code: for C-45, that the store applies a change before it saves and has no
  way back; for C-34, that the loader checks no length, not even the requester's. Those are the reasons the checks
  of these two clauses fail on the reference build, now in nine test passes of nine.

**F57. One short reading of the specification by a session that did not write it removes the clauses that would
later reject a correct product.** The author's own text tells it to cut a clause "a builder could leave out with
nothing missing", and the author kept both: one it had sourced to documents the code does not follow, one the plan
stage added as implied. A reader with one question, sent to check each claim about existing behaviour in the
product's files, finds both and nothing else, in about a minute. Section 20 found that what rejects a correct product is
a refusal the writer added on its own (F28: 28 times in 46); this is the cheapest lever on such clauses seen so
far.

**Limits.** One specification and two known targets, by one model at one effort. A clean sheet on the other 43
clauses means none of them is known to be wrong, not that all are right. Whether the reading holds on a
specification with no over-decision (does it then write `none`?) is not tested.

### A change to how yardstick Y2 is measured, written at 19:03 before any test pass of parts C and T has been graded on it

The registration reads Y2 on all 52 fault sites. Measured that way for twelve runs, the machine could not keep up:
`mutate.py` runs the product's own tests for every fault, `npm test` starts a process for each test file at
once, and three grading streams drove the load to 47 on 18 cores, where a check can fail for want of time. I
stopped the streams before any of them had finished a replay (one run's planted-defect grading had finished and is
kept: it shows no check that did not end).

The change: Y2 is read on the **40 faults of part E** (the first 40 of the same 52, on the same reference build),
and each fault's own-tests result is taken from part E's replay of q-base-2 (`mutate.py --own-from`, new), since
the product and its own tests are the same files under every suite. The acceptance checks are run on every fault
as before. The odd-numbered lines remain the yardstick for every arm; the proof of failure showed sessions faults
from all 52 sites on even lines, so nothing held out was shown. What is lost: the twelve sites beyond the first
forty.

### Part C, the census by script: how it is run, written at 19:15 before its count exists

The registered command (`prove_fail.py WORK - OUT --only sabotage`) runs every check twice over, on the build and on
the sabotaged copy. On six suites it took up to several minutes each on a machine other sessions were also using,
and was stopped twice to protect live sessions. `program/sabotage_census.py` asks the same question and stops at
the first check that notices: it runs the manifest's commands on the sabotaged copy, last entry first, and when
one fails it runs that one on an untouched copy; passing there makes the copy *noticed*, and a suite whose every
command still passes on the sabotaged copy is *unnoticed*. Tried on the two suites whose truth is known: q-plan-1
unnoticed, q-base-2 noticed by its last entry after one command (20 seconds for both). The six suites measured the
registered way stay on file as a cross-check: three stand-in-rules suites unnoticed, ticket assignment and due
times noticed, one product with no test file to sabotage.

### Part C, the census by script, result (19:20): one suite of 39 claims that the existing tests pass and cannot tell when one fails

46 suites, four minutes (`program/sabotage_census.py`; `evidence/program/hollow-checks/sabotage-census.json`). The
six suites measured the registered way agree with it, six of six.

| | Suites | By case |
|---|---|---|
| The product started with no test file | 7 | battleship 2, Grokbot-local 3, chess 1, shared expenses 1 |
| A check fails when an existing test is made to fail | 33 | ticket assignment 15, due times 13, stand-in rules 5 |
| No check fails | 6 | stand-in rules 5 (Sol at high), ticket assignment 1 (q-plan-1, Sonnet at medium) |

A check that noticed was found after two commands at the median (the last entry first), 115 at the most.

**The six, read.** q-plan-1 is the known case: a clause says the existing tests pass and its test starts a run
that does nothing (F42). The five stand-in-rules suites are the strength cells of one request, which adds a module
and was given a reference build: in the two I read, the clause is about which command `npm test` runs, not that
the existing tests pass (p1: "the `scripts.test` value in `package.json` is `node --test`"); in two more a script
reading shows the checks that start the product's tests failing on the given build already, so they decide
nothing. I count none of the five as a check that cannot fail.

- **The reading census overcounted.** It found 16 suites in which a nested run keeps the variable that makes it do
  nothing. By script, two of the suites it listed notice the broken test at once (their manifest starts checks
  with a plain `node` runner, where the variable is never set). What decides is how the check is started, which a
  reader of the test file does not see.
- **My prediction** (5 to 12 unnoticed of those measurable) holds as a count, six, and misses the point: one of
  the six is the failure the idea is about.

**F58. A do-nothing check of "the existing tests pass" is rare here: one suite in 39.** The rule "a check must be
able to fail" is right, and the sabotaged copy is a cheap way to enforce it for this claim (a few seconds for most
suites), but it would have changed one suite of those on file. The yardstick trial already showed where the rule
has more to do: checks that pass on the starting product and on every faulted copy (one in each of the first two
proof-of-failure runs, see below), which only a counterexample for that check's own behaviour can expose.

**Limits.** Three cases with existing tests, one fixture family; the sabotage breaks one test file and says nothing
of a check that runs some of the product's tests.

### Part T, a fourth arm, registered 19:28 before its runs: every refusal the change touches, with its nearest allowed case (three test passes)

**What is known at this moment.** Of the twelve test passes of parts C and T, the planted-defect grading exists
for these: ta1 ta2 tb1 td2 . Each catches 26 of 27 and misses `update-rejects-resolved`: two plain runs, one with
the proof of failure and one with the grounded question. The reports of the question arms show why: each
lists "closed tickets refuse edits", and none lists or tests that a resolved ticket can still be edited. The defect
tightens that guard by one state, so only a test of the case next to the refusal can see it. The first review said
so before any of these runs: "Ask for the allowed neighbor as well as the refusal when a state guard changes"
(`review/sol-ideas-answer.md`). My grounded question left that sentence out.

**Stated plainly.** This arm is written knowing which defect the suites miss. The rule is the review's and names no
state, route or file; whether it finds this defect is still open, and a hit would show the rule can reach it, not
how often such a rule pays.

**Cells.** `te1` to `te3`: as the other arms (`--plan-from c0 --build-from <the reference> --stop-after tests`), with
`--tests-question neighbour` (new in `ratchet.py`; the other two question texts are unchanged): find each condition
the change touches that refuses something, name the nearest case that must still be accepted, taken from the old
code, and name or write one test for each side.

**Readings.**

- **RT2.1.** `update-rejects-resolved` caught in how many of three. *The question catches it* if all three do (the
  bar of RC.2).
- **RT2.2.** Planted defects caught of 27; checks failing on the reference and on the second correct delivery,
  beside the plain runs (RC.3's bar for over-tight).
- **RT2.3.** The entries under `## Refusals and their allowed neighbours`: how many, and whether the edit of a
  resolved ticket is among the allowed cases.
- Not measured for this arm: the seeded faults on existing lines (F56 says what that instrument measures).

**Predictions.** It catches `update-rejects-resolved` in two of three; 26 or 27 of 27; one or two more checks fail
on the second correct delivery than in the plain runs.

### Parts C and T, result (20:24): fifteen test passes on one base; three levers move nothing that matters, and the fourth catches the missed defect once in three

Every run starts from `c0`'s specification and plan (45 clauses, 6 use cases, Sol at medium) and the reference build,
and ends after its test pass. Launched from f413b280a06c6c20616b2e5c04ccf06ac21bb8dc (`ta`, `tb`, `tc`, `td`) and
from ac93c95b74c188a50741a3fc733691aa55f7d296 (`te`). Graded with the working copy at
705581df4116da1fdf769929cca0e8a9543ab14e: planted defects by `grade.py strength`; seeded faults on existing lines
on part E's 40 faults (see the note of 19:03); the sabotaged copy by `prove_fail.py`. No check failed to end in any
grading; a check that failed once and passed when run again is counted as passing, as the gate counts it.
`evidence/program/test-pass/table.json` holds every row, with each run's own report.

| Arm | Runs | Seconds of test sessions | Planted defects caught of 27 | `update-rejects-resolved` | Checks failing on the reference | on the second correct delivery | Odd-line faults caught, of 22 (the own tests: 20) | All 40 (the own tests: 31) |
|---|---|---|---|---|---|---|---|---|
| plain | ta1 to ta3 | 834, 861, 862 | 26, 26, 26 | missed, 3 of 3 | 3, 4, 4 | 5, 4, 5 | 20, 20, 20 | 31, 31, 31 |
| proof of failure | tb1 to tb3 | 1,323, 904, 989 in three sessions each, and two script proofs of 330 to 480 seconds | 26, 26, 26 | missed, 3 of 3 | 3, 5, 3 | 5, 4, 5 | 20, 20, 20 | 31, 31, 31 |
| question, general | tc1 to tc3 | 938, 795, 956 | 26, 26, 26 | missed, 3 of 3 | 5, 5, 4 | 5, 4, 5 | 20, 20, 20 | 31, 31, 31 |
| question, grounded | td1 to td3 | 931, 902, 899 | 26, 26, 26 | missed, 3 of 3 | 4, 6, 5 | 5, 6, 6 | 21, 21, 21 | 32, 35, 32 |
| question, refusals and neighbours | te1 to te3 | 1,150, 881, 1,073 | 27, 26, 26 | caught once, missed twice | 4, 4, 4 | 4, 5, 5 | not measured | not measured |

The sabotaged copy is noticed in every run. Every suite has 51 checks.

- **RC.0, room.** The plain runs miss one planted defect of 27, the same one each time; two odd-line faults of 22
  survive their checks; no plain suite fails to notice a broken existing test (I predicted one of three would).
- **RC.1, existing code.** The proof of failure: *does not* (20, 20, 20 against a best plain run of 20). The general
  question: *does not* (20, 20, 20). The grounded question: *not shown* (21 each, one more than the plain runs, where the bar was
  two more in every run).
- **RC.2, the defect the suites miss.** None of the three registered arms catches it in any run. The fourth:
  catches it in one run of three (te1), so by the bar of all three *the question catches it* is not met. I
  predicted two of three for it, two of three for the grounded question and one of three for the general one; the
  last two caught it in none.
- **RC.3, harm.** No arm is over-tight by the rule: the worst plain run fails five checks on the second correct
  delivery, and no arm fails more than that in every run.

**What each lever did.**

- *The proof of failure.* In all three runs the script found the same check that nothing made fail (C-8: an
  assignment to a ticket that does not exist answers 404, which the starting product's handler for an unknown
  route answers too) and ten faults no check noticed, all on existing code. Each session then strengthened or
  explained C-8, explained one fault as unreachable, and wrote regression checks for the others in a new file. The
  bench's rule that every manifest entry names a clause kept those checks out of the manifest (entries named
  `R-1`, `R-2`, `R-cli-table` and `R-data-file` were refused, in all three runs), and my refusal text had not said
  where such a check may live. So the second proof found the same ten
  faults unnoticed, and nothing moved on any yardstick, for 904 to 1,323 seconds of sessions against about 850, and
  690 to 940 seconds of script time.
- *The general question.* A table of 14 rows of preserved behaviour in each run, each row with its evidence and a
  test. No reading moved.
- *The grounded question.* 57, 95 and 105 entries, one for each route, command, field and message that passes
  through a touched file. Its suites catch one to four seeded faults that the product's own
  tests miss, in the table formatter and in the checks a data file gets on load: code the request does not
  concern (F56). It lists "closed tickets refuse edits" and never that a resolved ticket can still be edited.
- *Refusals and their allowed neighbours.* 58, 42 and 45 entries. te1 lists the existing guard on edits ("Existing edit
  validation refuses a closed ticket. It allows the same edit while resolved.") with one test for each side, and its
  suite catches all 27. te2 and te3 list the refusals the change itself adds (assignment while resolved or closed,
  an assignee field in an edit, the limits on text) with their neighbours, and not the edit guard, which the
  change's diff does not touch.

**F59. A list of what must not change does not test the boundary; a list of refusals with their allowed
neighbours can, when it reaches the right guard.** The twelve suites of the plain runs and the three registered
arms all miss the defect that tightens an existing guard by one state: they test that a closed ticket refuses an
edit and that an open one accepts it, and nothing in between. Of the thirteen suites graded for this request before today, four
catch it: three written by Sol at high from the longer specification texts (164 to 209 checks) and one whose plan
listed preserved behaviour; of the nine written from the reworded text, one (F36). Asked for each refusal's nearest
allowed case, one session of three found that guard, tested its allowed side, and caught the defect; the other two
looked at the refusals in the change's own diff. So the rule has the right shape, and its reach depends on which
guards a session takes the change to touch: this defect sits on a guard beside the change, not in it. A fresh
review of the built product found it six times of six (F53), because there the defect is in front of the reader.

**F60. Feeding a test author what the script could not break buys tests of whatever the faults happened to
touch.** The proof of failure did find a real do-nothing check in every run, and that half is worth keeping. Its
other half, the list of unnoticed faults, sent three sessions to write checks of the request log and of file
validation in a delivery of ticket assignment, for a quarter more session time on average and eleven to sixteen
minutes of the script's own time in each run. As a gate it needs two
things this bench did not give it: faults confined to what the change touches, and a place for a check that no
clause covers.

**Five session records hold a held-out mark, none of them held-out material.** Each of those test sessions listed
the machine's processes and so saw the command line of another session's run (a consultation that names the
harness's folder; a ShipLoop run started with its request). Nothing of the held-out checks or of the planted
defects is in them.

**Limits.** One case, one specification and plan, one reference build that is not itself clean (F55), three runs an
arm, and a machine that was overloaded during part of the wave; the fourth arm was written knowing which defect
the suites miss, and the seeded faults were not replayed on it.

### What the program says, taken together (20:25, when its last part was read)

131 model sessions in 106 runs, every one on Codex with `gpt-6.2-sol` at medium, and no rescoring of a registered
reading. Where a registered reading was not met, or a registration turned out to rest on a wrong classification
(part R's "right" build), the entry of that part says so. Each finding below has its evidence under `evidence/program/`.

| Idea | Verdict on this bench | Finding |
|---|---|---|
| A point the request leaves out is carried, not decided silently | already done by the reworded text: marked 12 of 12 | F46, F48 |
| The answer reaches the build | holds: 8 of 8 held-out checks three times against 3 of 8 three times; into the delivery's own check 3 of 3 | F52 |
| A session chooses what to ask the requester | does not hold: the request's point asked 0 of 18; a disagreement inside the product found 9 of 9 | F50 |
| A fresh reader of the specification | holds on the one specification with a ground truth: exactly the two over-decided clauses, 3 of 3 | F57 |
| A fresh reviewer of the finished product | holds as a finder (planted defect 6 of 6, 62 of 62 findings true), not as a gate (a delivery with no break rejected 4 of 6); starting from the request first does not help | F53, F54 |
| The instruction arrives | holds at this size (18 of 18); ShipLoop loses the tail of long packets, not instructions | F51 |
| Existing code is protected | the instrument measures the product's old test gaps; suites mirror the own tests (31 against 31) | F56 |
| A check must be able to fail | the unit is the test and the tool is a counterexample copy; do-nothing checks of "the existing tests pass" are rare here (1 suite in 39) | F49, F58 |
| A question at test design | a general or a file-grounded question moves nothing (26 of 27 in all six runs); asking for each refusal's allowed neighbour catches the missed defect once in three | F59 |
| The proof of failure shown to the test owner | finds a real do-nothing check in every run; its list of unnoticed faults buys tests of unrelated code and moved no reading | F49, F60 |
| Ask after reading | nothing to fix: answers are on record (14 of 15) | part A |
| Gaps in ShipLoop's own checks | five pinned as tests | part G |

**The shape of it.** Three results point the same way. A session that did not write a thing, given one narrow
question and sent to the files, is right where the author is not: about clauses that decide too much (F57) and
about a finished build (F53). And the one input no session can supply
is the requester's own preference: it cannot be guessed (F48), cannot be chosen as a question (F50), and when it
is given it goes through every stage untouched (F52). More text in the author's packet moved nothing in this
pilot; a second pair of eyes and one sentence from the requester each moved a great deal.

**What I would try in ShipLoop, for its owner to decide.** None of these is tested in ShipLoop itself.

1. *Put the plan's decisions in front of the requester.* The plan already lists each answer it takes for an open
   point with the alternatives set aside. Attended, show that table before the build; unattended, put it at the top
   of the final report as "decided for you; one sentence changes it". On the due-times request this is the
   difference between 3 and 8 of 8.
2. *Ask one thing at intake that a session finds every time:* where the product's documents and its code disagree,
   and which the requester wants kept.
3. *A second reading of the specification* by a fresh session, one question (which clauses require what the
   request does not ask and the product does not do), each claim checked in the files. About a minute.
4. *A fresh review after the gate, for its findings.* Each finding with a probe, sorted into "breaks the request or
   existing behaviour" and "decides an open point"; no accept or reject line.
5. *For every guard in the code a change touches, test the nearest allowed case as well as the refusal.* The one
   planted defect the suites miss is a guard tightened by one state. Every inventory of preserved behaviour
   written here lists "closed tickets refuse edits"; the one suite that also tested "a resolved ticket can still
   be edited" caught all 27 (F59). The wording has to reach guards beside the change, not only in its diff.
6. *Keep what must be read inside a packet's instructions,* not only in the references after the result template.

**What I would not spend more on.** Wording of the specification text. A general question about preserved
behaviour, at any stage. A verdict from a reviewer. Seeded faults on existing lines, as a measure of a delivery or
as feedback to a test author.

**Limits of the whole program.** One evening, one model at one effort, three requests on one fixture family, three
runs a cell. The requester was a file. Several readings rest on a build I had classed as right and that was not
clean (F55). The machine was shared and at times overloaded; gradings were checked for checks that did not end.

**Received from the session "Spec elaboration" at 19:57, not checked by me.** It reran its reader over the same 62
runs and reproduces the packet figures above (its journal, section 58). It adds two results of its own: on one
one-sentence request the released spec stage decides silently in a different direction on each model (all three
Sol specifications add a new ticket status, all three Sonnet ones reuse an existing state and record that as an
assumption), and two judges reading five texts twice give an item the same state on 97 of 101 items, with nets
steadier than counts. The first is the same thing as F48 seen from the other side: what is decided when nobody
answers moves with the model.

**Not delivered.** My note on F55, on the plain builds failing five held-out checks and on part G was sent to the
session "Shiploop SDLC"; that session held it and it expired unread. The content is in this section.

## 27. A candidate for ShipLoop: the specification records the choices it made, and the run shows them (2026-11-21, from 21:25)

The owner, asked "Do you want me to draft the first of the six suggested ShipLoop changes here (showing the plan's
decisions to the requester), as a candidate branch that stays out of main until you accept it?", said "Yes". This
section is the account of that candidate. It is on branch `shiploop-defaults-2c3d50` and nowhere else. Whether it is
accepted is the owner's decision; a release is the SDLC session's.

Everything is in one folder, `docs/experiments/ratchet-pilot-20261120/shiploop-defaults/`: `DESIGN.md` (the design, the
test plan fixed before any run, and what the review changed), `review/` (the review, word for word), `evidence/`,
the scripts that read and run (`baseline_read.py`, `requester.py`, `read_wave.py`, `launch_wave.sh`) and the two
briefs a reader is given (`reader-brief.md`, `product-reader-brief.md`).

### What was read before anything was designed

- The commits that added the two lists this one copies: the spec's `primary`
  (f9d1f4cf732e9d63b46349c69e7cec3b6207995e: "a required result field per decision, a placeholder that states the bar, a
  CLI gate on the field, and downstream packets quoting it by value") and the handoff's `follow_on`
  (826c951ccfdecb8f48e406f8fbdacb6a69daabbc: only mechanical faults are refused, the stored shape is loose so every
  saved run loads, a new gate adds its dodge rows, the fixtures that hand-build a result must carry the key).
- The spec-elaboration study's conclusion and its reading of 31 real deliveries
  (0d46d085479bf43e02cf964ee86917cc5b44dcb0 and its journal's sections 26 and 28): a final report shows what a stage
  wrote down and only that; a wording that tells the stage to take a default for "a limit the request leaves to
  choice" invents limits; the stage's own text pulls two ways on an open choice.
- A fact about ShipLoop this pilot's suggestion had got wrong. The suggestion said "the plan already lists each answer
  it takes for an open point". That is true of this pilot's bench. In ShipLoop the plan's list holds facts the plan
  relies on (`assumptions`), the implement step's `decisions` go into a commit message, intake's ledger holds
  questions asked before the repository is read, and the handoff's `decision` class is for a choice only a person
  can make and the run left open (a replay before that list was built found such a leftover in 2 of 166 finished
  runs). There is no list of choices made for the requester anywhere.

### The baseline, from deliveries that already ran

Eleven full deliveries of `ticket-due-times` on Codex with `gpt-6.2-sol` at medium are archived (ShipLoop 2.4.0 and
2.4.1; the SDLC structure study's, read and not touched). No model was called for this.

| | of 11 |
| --- | --- |
| the specification decides who gives the old tickets their due times and what an enabled start does without them | 11 |
| it chose "an operator's command, and the service refuses to start" (the answer the owner ruled wrong) | 4 |
| the held-out check `migrate` fails | the same 4 |
| the choice is written as a plain line of a requirement | 11 |
| the spec result, the specification or the report says it was a choice, or names the other answer | 0 |

Evidence: `evidence/baseline-11.txt` (each run's spec summary, the lines of its specification on the point, intake's
questions on it, the report's open items) and `evidence/archive-sol-medium-checks.txt` (every archived Sol-medium run's
held-out checks). This pilot's own bench had the plan take the wrong answer six times of six (F48); real ShipLoop on
the same model takes it four times of eleven. The rate differs; the silence does not.

### The design, and the review that changed it

The design as first written (22:20) is `review/DESIGN-as-reviewed.md`. The latest Sol at maximum effort reviewed it
with the scripts and both journals (22:34, about 13 minutes; `review/sol-design-answer.md`). Its verdict: build it as
a disclosure pilot, with changes. The one that matters most: my first design printed the `note` command in the next
stage's packet and told the requester on every surface that "one sentence changes it". The review traced what a note
does, and nothing in the script replaces an accepted specification and what was planned from it: a note is quoted by
the next packet and marked delivered when that step is accepted; the one route that reopens the specification needs a
stopped review of the plan and exists only before the build. I checked three of its steps in the code and they hold.
So the promise is gone. What the candidate does is disclose; the only route it names for changing a default is the
one that holds, a new run. `DESIGN.md` section 4 lists all seven changes, including the three I did not take and why.

What this means for the suggestion as the program made it: F52's "8 of 8 against 3 of 8" was measured on a bench where
the requester's answer is applied by a step that rewrites the specification. ShipLoop has no such step for an answer
that arrives during a run. Showing the choices is the half that can be built without a product decision. The other
half, a route by which the answer takes effect before the build, is a product change of its own, with a cutoff and a
script-owned path, and it is the owner's to decide.

### What was built

- `skills/shiploop/scripts/shiploop_defaults.py` (new): the list's fields and template row, the gate, the three
  displays.
- `skills/shiploop/scripts/shiploop_navigator.py`: the result key, the shape check, the gate at `check` and
  `complete`, on the stage review's import and before an earlier check's yes is reused; the template row; the
  Checked-by phrase; one required block in the `test-strategy` packet, with the print budget and run file every other
  model-written block uses; the done packet's lines; one section in the report; one line in the packet of the
  spec's own stage review (a review that changes such a choice returns the list changed to match). No state key was
  added.
- `skills/shiploop/scripts/shiploop_prompts.py`: six sentences in spec duty 4; duty 9's clause points at the list; the
  spec template's summary hint no longer asks for defaults.
- `references/navigator.md`, `references/glossary.md` (the term "default", and what it is not), `README.md` (one
  sentence), `changes/shiploop/decided-for-you.md` (minor).
- Tests: `test/shiploop-defaults.test.py` (new, registered); three rows in the callback suite's table of named faults
  and two in the loophole table; the import route in the stage-review suite; the gate's refusals in the E2E harness's
  table of named gates (`test/shiploop_e2e/metrics.py`), so a run's gate count names it.

### What the tests say (no model called)

- **Fail first.** The new suite against the unchanged scripts: 3 failures and 14 errors (the module is missing; "result
  has unsupported fields: defaults"). With the change: 15 of 15.
- **The new suite** (`test/shiploop-defaults.test.py`) drives the real command line: the spec template prints the row
  and the duty stands once, before the template; eleven faults are each refused and the corrected list accepted,
  including two choices under one requirement and a text that happens to sit in angle brackets; the refusal of a
  missing list is a whole instruction; the next stage prints the rows and no other stage does; a list past the print
  budget prints its leading rows whole and names a file that holds all thirty; the done packet and the report carry
  the rows, escaped, with "none" and "not recorded" told apart; a result of an earlier shape loads while the gate
  refuses it; a run saved before the list loads.
- **Other suites**: three named-fault rows in the callback suite, two dodge rows in the loophole table (a template row
  with one text filled in; a requirement the specification does not hold), the stage review's import route, the
  inventory of numeric limits (the print budget is a "print budget"), and the harness's gate table.
- **The wide selection**: the quick tier, every ShipLoop suite but the E2E apparatus, and the harness suites the
  change touches, 131 suites in 1,078 seconds. 128 passed. Of the three that did not, two were right: the inventory of
  numeric limits did not know the new print budget (added), and `shiploop-knowledge` pins the words of spec duty 5 on
  a clause's basis, which I had edited at the review's suggestion (put back; duty 4's own sentence already has the
  clause say it is a default of this date). The third, an E2E calibration suite, passes when run alone; the machine's
  load was 30 at the time. After those fixes and the last small edits the 33 suites they touch were run again: 32 passed,
  and one test of `shiploop-navigator-contract` failed on a version string in a progress file that changed between
  two listings of a run folder; that test passes alone three times of three on the candidate and three of three on
  the unchanged code, and the whole suite passes alone (127 tests).
- **Packet sizes** (characters printed, at the head-order suite's reference install): the spec packet 18,507 before
  and 19,840 after (the duty 749, the template row 401, the Checked-by phrase 152, the summary hint 20). That is 160
  under the 20,000 a Grok host prints whole, so nothing more fits there; at the long-path install the same packet
  goes from 19,467 to 20,800 and Grok would drop about 800 characters from its middle, as it already does for the
  plan and `test-strategy` packets (27,968 and 22,931). The new sentences stand early in the duties and are not in
  that middle. The `test-strategy` packet is unchanged (22,051) when the spec recorded no default; five rows of a
  realistic size add 1,941 characters; a longer list prints the rows that fit 2,400 characters and names the run
  file that holds them all.
- **Lint**: no new finding in any changed file against its copy at the base, except six of the kind every test of
  `test/shiploop-e2e-analysis.test.py` already carries (names that file takes from its header); the new files pass.

One suite caught a real omission on the way: every numeric limit in the scripts is registered with its kind, and the
new print budget was not (`test_every_numeric_limit_in_the_scripts_has_a_kind`). It is now.

### What is registered, before any run

`DESIGN.md` section 3, in the commit that holds this entry. Wave 1 is a smoke test: three real deliveries of
`ticket-due-times` and one of `hello` on Codex with `gpt-6.2-sol` at medium, built from that commit. The readings:
the start-up choice on record, scored by a reader who sees the specification and the printed rows and nothing else
(`reader-brief.md`; at least 2 of 3, against 0 of 11); nothing invented and nothing lost; the empty case; the three
surfaces and what the host actually said to the user; the gate's refusals and the spec stage's cost against the
archive (`evidence/archive-cost.txt`: 820 to 1,248 seconds a delivery, the spec stage 17 to 61 seconds, 27,158 to
34,865 output tokens, 7 to 12 messages to the user); what the list misses. In two of the three due-times runs a
stand-in requester replies with the owner's ruling as an owner note when a printed row raises the point. That is an
observation of the existing note route and not a reading of the candidate.

Before any run I widened the stand-in's keyword rule once: as first written it did not fire on a row I wrote by hand
that plainly raises the point ("Who gives the tickets already on file their due times?"), because that row has none
of "backfill", "migrate", "existing". The rule now also takes "already" and "older", and a row that names starting the
service together with a due time that is absent. After the review the rule is only a trigger during the run; the
score is the reader's.

### Wave 1: the choice is shown in three of three, in the builder's words (23:10 to 23:29)

Four real deliveries built from 31e53d718113fb517c2939ea014a6850925a8950 on Codex, `gpt-6.2-sol` at medium: three of
`ticket-due-times` (d1, d2, d3) and one of `hello`. A stand-in requester read what each `test-strategy` packet
printed and, in d1 and d2, replied with the owner's ruling as one owner note; in d3 it sent nothing. A Sonnet reader
who saw only each run's specification and printed rows scored them (`reader-brief.md`), and a second read each
delivered product against the rows (`product-reader-brief.md`). `DESIGN.md` section 5 has the whole table; evidence
under `evidence/wave-1/`.

| | d1 | d2 | d3 |
| --- | --- | --- | --- |
| the start-up choice the specification took | the service fills them in at start | an operator's command, and a refusal to start | an operator's command, and a refusal to start |
| a row on it with another answer (archive: 0 of 11) | yes | yes | yes |
| the reader's score against the registered question | partly | partly | partly |
| the stand-in's reply | sent | sent | not sent |
| held-out checks passed | 8 of 8 | 8 of 8 | 3 of 8 |

- **R1 is not met by its rule** ("yes" in two of three). Each run now shows the requester the choice it took and
  another answer, where no archived run shows anything. No row says what the person who runs the service will meet:
  the refusal to start is a line of the specification in d2 and d3 and is in no row, and the rows speak of
  "backfill", "the flag" and "before listening".
- **Nothing was invented and nothing was lost.** All ten rows are real open points that the named clause states.
  The specifications are the archive's size (348 to 451 words, 4 to 6 requirements). `hello` got one row, a real and
  small one (a trailing newline).
- **The list is partial.** The reader found 5 to 7 choices in each specification that no row has; no row in any run
  says what an invalid setting does; and no row or specification has the largest number of hours each product
  enforces (2.4, 2.5 and 2.4 billion), which the build chose.
  (Corrected 23:45: an invalid setting stopping the start is the starting product's own documented behaviour, so
  leaving it out of the list is right, and the blind reader, who cannot see the product, counts such lines as
  unlisted. The 5 to 7 are an upper limit on what is missing. The refusal to start in d2 and d3 and the build's
  upper bound on hours are the real misses.)
- **The cost.** No submission was refused by the new gate. The spec stage took 52 to 56 seconds (archive: median 43,
  17 to 61); the deliveries 759 to 1,103 seconds (archive 820 to 1,248).
- **What the host said.** The block reached all four sessions. One host of three named the choices to the user as
  choices at that stage. The done packet printed the rows four times and no final message relayed them as choices.
- **F61. A plain owner note, sent right after the specification, changed the build.** d2 and d3 took the same
  answer the owner had ruled wrong. In d2 the one-sentence reply arrived while the next stage was current; that
  stage rewrote the requirement ("N1 supersedes offline preparation and startup rejection"), the plan called the
  note binding, and the delivered service passes all eight held-out checks. In d3, with no reply, the service
  refuses to start and fails the same five checks the archive's four fail. That is one pair, not a rate, and it is
  the existing note route, not the candidate. The review was right that nothing in the script checks it, and right
  about the price: d2's recorded row went stale, and its own host said so in its last message ("The ShipLoop report
  retains an early offline-migration proposal").

By the rule fixed before the wave, the instruction is reworded once and tried again. Two repairs go in with it,
both asked for by what wave 1 showed: a row whose requirement a later stage rewrote is marked "changed after the
spec stage" in the done packet and the report (it marks R-3 in d2 and in d1 and nothing in `hello` when run over
the finished runs; a line added to a requirement, which the build's stages do routinely, is not a rewrite), and the
done packet's first line now tells the host to say the choices to the user. `DESIGN.md` section 5 has the reworded
text and wave 2's rules.

### Wave 2: the reworded instruction gets two "yes" of three (2026-11-21, 23:40 to 23:58)

Four more real deliveries (d4, d5, d6 and `hello`), built from 1641ecb825d4b6a09111927c871ca7c00d9c433b, same driver,
same reader, same brief, same "strict and literal" instruction. `DESIGN.md` section 6 has the table; evidence under
`evidence/wave-2/`.

- **R1 is met**: the reader scored d4 and d5 "yes" and d6 "partly" (wave 1: three "partly"). A row of d5: "Run npm
  run backfill:due while the writer is stopped. Enabled startup also fills any missing deadlines before serving.
  Otherwise: Require a separate backfill and refuse startup when any value is missing."
- **What that does not show.** None of the three specifications chose the refusal to start (two of three did in
  wave 1; four of eleven in the archive), so the reworded text was never asked to put a refusal into a row. Asking
  for "what happens if they do not" may turn an author away from a refusal; three runs cannot say.
- **R2, no stop.** All eleven rows are real open points their clause states; none settled, added or unstated; the
  line-by-line reading did not over-list (4, 4 and 3 rows; `hello` one, the same as before). Each named clause now
  says it is a default (11 of 11; 7 of 10 in wave 1).
- **Told to, hosts say it.** The done packet's first line is now an instruction, and two final messages of three
  give the user the choices as choices ("I chose per-priority `DUE_HOURS_*` settings for whole-hour overrides, a
  strict overdue cutoff, and automatic backfill before the service starts listening"); none of three did in wave 1.
- **The mark, in a real run.** d4's reply made the next stage rewrite the requirement; its done packet and report
  mark that row "changed after the spec stage" and no other.
- **The cost.** No refusal of the new gate in eight runs. The spec stage is about fifteen seconds slower than the
  archive's median (56 to 66 seconds against 43).
- **One harness verdict to read with care.** d4 is FAILED: at grading, the check that the starting product's 117
  tests still pass "did not end within 120 s". Run by hand twice afterwards on the same delivery it passes, 117 of
  117. The record is left as the harness wrote it.
- **F61, completed: of four replies, two changed the build, one was confirmed and one was ignored.** d5's stage was
  shown the note in two prints of its packet; no summary of that run names it, the script records it as delivered,
  and the delivery keeps the operator's command the reply said nobody should need. A note is delivered when the
  step that saw it is accepted, whatever the step did with it. That is the design review's point, observed.

My launcher's last lines failed in wave 2 (exit 2) because I edited the script while it ran and the shell read the
rest of the file from a shifted place. Every run had already written its own exit file, and nothing else was lost.
The rule is old: never edit a running shell script.

**The tests, on the candidate as it stands** (the tree of 1641ecb825d4b6a09111927c871ca7c00d9c433b; 00:00 to 00:25
on 2026-11-22, four suites at a time, beside one live delivery): the same wide selection as before, 131 suites, all
passed. The two suites that had each failed one test in runs of eight at a time (`shiploop-navigator-contract`,
`shiploop-e2e-incremental-pilot`) pass here, as they do alone.

### One delivery on the other driver (2026-11-22, 00:00 to 00:43)

`ticket-due-times` on the Claude host with `claude-sonnet-5-5` at medium, built from
1641ecb825d4b6a09111927c871ca7c00d9c433b, to see that the list does not misbehave there. One run: function, not a
rate. `DESIGN.md` section 8; evidence under `evidence/sonnet-1/`.

- Six rows in an operator's words, no refusal of the gate, all eight held-out checks pass, tokens and cost inside
  the archive's range for this driver (195,151 output tokens, $10.58). Its time is not comparable: I ran the test
  selection beside it.
- The stage review changed a default and the host returned the list changed to match, saying so: the one line added
  to the spec review's packet, followed.
- One row is a limit: at most 100,000 hours. The reader calls it behaviour the request does not need. All four
  archived Sonnet specifications of this case already set such a bound; the list did not make it, and now shows it.
  This is the same bound that on Sol, in wave 1, the build sets and nothing records.
- The reader's score on the start-up question is "partly", as for every specification here that fills the due times
  in at start: three of three such rows (d1, d6, s1) got it, and both "yes" went to rows that say what an enabled
  start does. The question as I registered it rewards a sentence this design makes unnecessary.

### Where the candidate stands (2026-11-22, 00:46)

Nine real deliveries (eight on Sol at medium, one on Sonnet at medium), three commits on `shiploop-defaults-2c3d50`,
nothing pushed, nothing on `main`.

| | archive (released ShipLoop) | the candidate |
| --- | --- | --- |
| the requester is told which answer was taken on the start-up point, with another answer beside it | 0 of 11 | 7 of 7 |
| rows that are a real open point their clause states | | 26 of 27 (the one other: a bound Sonnet has always set) |
| a blind, strict reader's "yes" on the start-up row | | 0 of 3 with the first wording; 2 of 3 with the second; 0 of 1 on Sonnet |
| submissions refused by the new gate | | 0 in nine runs |
| the spec stage, Sol | 17 to 61 s, median 43 | 52 to 66 s |
| the last message tells the user the choices as choices | | 0 of 3 untold; 2 of 3 told to |

- **F62. A field to fill, with the clause to name, gets the choice written down; an instruction in prose did not.**
  The released stage's text already told the author to record a default "as an assumption" and eleven of eleven
  wrote none. With a required list whose rows name their requirement, seven of seven list the start-up choice and
  no row is behaviour the list brought about. This is F39 and F43 carried from this pilot's bench into ShipLoop
  itself.
- **F63. What a row says follows what the instruction asks for, and may move what gets chosen.** Asked for "the
  default chosen", the rows named mechanisms and left out the refusal; asked for "what that person sees or must do
  and what happens if they do not", two of three stated the consequence, and none of three chose a refusal at all
  (two of three before; four of eleven in the archive). Three runs cannot separate the two effects.
- **F61 stands as the limit.** The list tells the requester. It does not make the requester's answer take effect:
  two of four replies changed the build, one was confirmed, one was ignored and recorded as delivered.

**The owner's decisions.** Whether the candidate goes to `main` (it then needs the SDLC session's E2E round before
a release, and that session holds its own change to the same script). And whether ShipLoop gets a route of its own
for the requester's answer before the build, with a check that the requirement changed: the half this candidate
does not build.

*Overtaken, 2026-11-22: the owner accepted the candidate ("Yes, merge it"), and the other session's change was
released as ShipLoop 2.5.0 the same night, so the round on the two together is run here. See "Accepted by the
owner, joined with ShipLoop 2.5.0" below.*

**Limits.** One fixture family, two requests, three runs a cell, one run on the second driver. The reader's
question rewards a sentence that a specification which fills the due times in at start has no need to write
(three of three such rows got "partly"). The spec packet is at 19,934 of the 20,000 characters a Grok host prints
whole. Hosts tell the user about the list only some of the time; the report always carries it.

**Seen on `main` at 00:46, from the session "Spec elaboration", not checked by me**
(3503ada200d5e01406ecb3bff30f2092d75ad7b4, committed at 00:17 while wave 2 was being read). It asked a fresh Sol
session at medium, from outside, to list every decision three finished deliveries of this case had taken on the
requester's behalf, at three points of the work: the list holds the decision that mattered 27 times of 27, already
after the specification, at second to fifth place in lists of 15 to 32 items. Its own limits name the two things this
candidate tried: "a working session asked the same thing was not tested" (here the spec stage's own session, asked
through a required field, lists it seven times of seven, in lists of three to six rows), and "whether the
requester's answer, once asked for, changes the product" (F61: two of four in ShipLoop itself). The two were run
apart, on different benches, and agree on where the choice can first be shown: right after the specification.

### Accepted by the owner, joined with ShipLoop 2.5.0, and a round registered on the combined tree (2026-11-22, 06:23)

**The owner's decisions.** At 05:46: "Yes, merge it", in answer to "Do you want the candidate merged into main?"
(put at 00:48). At 05:56: "I meant publish" (the release as well), and "Use sonnet agent to handle moderate
activities like Git management". The first of the two decisions above is closed; the route for the requester's
answer stays open. From here a Sonnet worker makes the commits, the push and the release from messages and guarded
scripts written in this session, and this session reads each result.

**Overtaken, 2026-11-22.** "Where the candidate stands" says the candidate "then needs the SDLC session's E2E round
before a release, and that session holds its own change to the same script". Between 01:16 and 01:40 that session
merged its change, ran its round and released it as ShipLoop 2.5.0 in skill-craft 4.3.0
(eb4fad3023f10011b5117cbee1f5f9edafe743e5): at release-verify ShipLoop itself runs the last work item's regression
command in the clean copy (5c48bcc84ac3999cb9dce5484a1da0aeb059f2e2), and a moved file is committed whole
(1f5bb5ca8a3cc3ec1d8806133df9452049225fa8). So the round is run here, on the two changes together.

**The merge** (5eab9cf72d0c1ceae76c583b68504d633c6588dd), made in a temporary checkout cut from `origin/main` at
52ea20b30454c5a1f41f5afbc7c5025d43e7a343. Sixteen commits had landed since the branch's base. At 00:46 no file was
changed on both sides; now three are (`shiploop_navigator.py`, `shiploop_prompts.py`, the skill's `README.md`),
each joined by Git without a conflict, with nothing written by hand: main's lines are in release-plan's duty 6 and
in the one-line statement of release-verify's gate, the candidate's in the spec stage, the packets that show the
list and the report. On the merged tree, before the merge was committed:

- The wide selection, chosen by the 79 files the merge changes against main (`bash test/run-all.sh --group quick
  --group python-floor --group affected --changed-from 52ea20b30454c5a1f41f5afbc7c5025d43e7a343 --jobs 4`, 05:51 to
  06:20): 131 suites, all pass, 1,711 seconds. Among them shiploop-defaults (the list), shiploop-test-loop and
  shiploop-workspace (the release's two changes), shiploop-head-order and shiploop-packet-bounds (the packets'
  sizes), the two suites of the harness's base check, and shiploop-navigator-contract and
  shiploop-e2e-incremental-pilot, which each failed one test once under eight jobs on the branch and pass here. The
  machine's load average was about 100 throughout (file indexing of the new checkout and a media service, beside
  the suites), so the times say nothing.
- The spec packet at the reference install is still 19,934 characters.

**A correction to wave 2's record.** d4's check of the starting product's tests "did not end within 120 s" at
23:55. The entry above records the timeout and not what it left: a test server with no parent, in the system's
temporary folder, which the session "Shiploop SDLC" found and stopped at 00:25
(fb0f834d90ff8a27b4a2eaec75ed45462a913e95: "A 28th appeared at 23:55, left by another session's run of the ticket
case"). I had swept my run folders by working folder and not the temporary folders where the check's processes
sit. That commit fixes the check (it now stops its whole process group at the limit) and the merge puts the
candidate on top of it. After the round below, the sweep covers those folders too.

**The round, registered before any run** (DESIGN.md section 9 holds it in full). Four whole deliveries built from
this commit, started together, medium effort, no stand-in requester: `hello` and two of `ticket-due-times` on Codex
with gpt-6.2-sol, one of `ticket-due-times` on Claude Code with claude-sonnet-5-5 (`--max-budget-usd 40`). The
combination is accepted, and released, if all four hold:

1. every delivery passes the harness's five verdicts and every case check (a check that "did not end within 120 s"
   is run again alone on the delivered tree; passing there, it is not counted, and both results are reported);
2. no delivery is stopped by the list's gate (a refusal the session recovers from is counted, not a failure);
3. in every delivery the spec result holds the list, the done packet lists it, and the report has "Decided for you"
   directly after the request;
4. no delivery is refused wrongly at release-verify (each refusal there is read by hand).

The rows, an added command at release-verify, times, cost and the hosts' last messages are described, not rules. If
any of the four fails, nothing is pushed or released and the owner is told. Not shown by this round: Grok, another
case family, the requester's answer, a right refusal at release-verify.

### The round on the combined tree: both changes do their part, and three deliveries of four miss the round's first rule (2026-11-22, 06:58)

Four whole deliveries built from 7296b215261e515a8f86ef0e5938bcc6c0cbb09c, 06:24 to 06:52: `hello` (k1) and two of
`ticket-due-times` (k2, k3) on Codex with gpt-6.2-sol, one of `ticket-due-times` (k4) on Claude Code with
claude-sonnet-5-5, all at medium, no requester. The whole entry, with its table, is in
`test/shiploop_e2e/LEARNINGS.md` under 2026-11-22; every value with its file is in
`docs/experiments/ratchet-pilot-20261120/shiploop-defaults/evidence/round-merged/`.

**Against the registration.**

- **Rule 1 (the five verdicts and every case check): not met; one delivery of four passes it.** k1 passes
  everything. k2 and k3 pass the verdicts and 3 of 8 case checks: both specifications chose a separate backfill
  command and a refusal to start, and the five checks that start the service on a file without due times fail. k4
  passes 8 of 8 and fails the `shiploop` verdict: its session started ShipLoop twice, first with a paraphrase of
  the request and within ten seconds again with the exact text, and the harness grades neither folder. No check was
  lost to the fixture's hang.
- **Rule 2 (not stopped by the list's gate): met.** No refused command names `defaults` in any of the four.
- **Rule 3 (the list in the spec result, the done packet and the report): met.** 1, 5, 3 and 6 rows; each next
  packet printed its block, each done packet lists the same rows, each report has "Decided for you" right after the
  request. For k4 this was read from the run folder with the longer history.
- **Rule 4 (no wrong refusal at release-verify): met.** Each delivery was accepted there at its one attempt. In k4
  ShipLoop added `npm test` to a consumer check of three files and 166 tests pass in the clean copy.

So by the rule fixed beforehand the combination is not accepted, and nothing is pushed or released on the round's
result. The owner was told as each delivery ended, and the decision to release or hold was put to the owner.

**My reading, kept apart from the rules.** None of the three misses is traced to the merge. The spec and
test-strategy packets of this build are byte for byte the candidate's before the merge
(`evidence/round-merged/packet-identity.txt`), so k2 and k3 read the instruction wave 2 read. The start-up choice
is taken at the released product's rate: four of eleven archived Sol deliveries, four of eight with the list. The
double start is the host session's; neither change touches how a run starts.

- **F64. The list shows the choice that fails a delivery, and showing it changes nothing when nobody answers.** In
  k2 and k3 the start-up choice is row 3, with the answer the held-out checks expect as its alternative ("Backfill
  as part of enabled startup before listening"; "Auto-backfill during normal startup"). No requester was in the
  round, the choice stood, and five checks fail, as in d3. What the list is worth depends on the requester reading
  it and on the answer taking effect, which is F61 and is not built.
- **F63, corrected.** Its lead, that asking for "what happens if they do not" may turn an author away from a
  refusal, is gone: under the same text, two of two here chose it (two of five over wave 2 and this round, against
  four of eleven in the archive). The reworded text has now met a refusal row twice: k2's states the consequence
  ("An incomplete persisted file blocks enabled startup"), k3's stops at "then enable".
- **F65. A rule on held-out checks needs the released product's rate on them before it is registered.** Rule 1
  held four deliveries to checks the released product misses about four times in ten on this case and model. I had
  that count (section 27, the baseline) and wrote "every case check" all the same, so a round that asked whether two
  changes disturb each other was decided by a fault neither change touches. It is read as registered. Next time the
  rule is the verdicts plus the archive's rate on the case checks, or the checks the change can move.

**From the session "Spec elaboration" (two messages between 06:30 and 06:50), recorded as its reading with my
check.** In
the six Sol deliveries of 2026-11-21 no row of 21 says what a roll-back to 1.4.0 loses, though by its reading five
of the six specifications do, and a separate lister puts that decision first 27 times of 27. A word search on my
evidence files finds no row of the 21 that names a roll-back at all; the Sonnet delivery's row 5 does. In this
round a row names it in k2 and k4 and not in k3. The instruction covers such a line ("a step they must take"), so
this is about what the author picks. Its proposal (`docs/experiments/spec-elaboration-20261120/PROPOSAL-shiploop.md`,
on main in 8803536bb977f1bf9d090965dad573ccd8ec5abf) takes this list as the list and puts one question to the
owner.

**Two process notes.** The count of stray servers before the round found one of mine: a `node src/server.js` from
the program of section 26, in my scratch folder, parentless since 2026-11-21 18:30 and listening on the wildcard
address. I stopped it by its process id at 06:23, after checking its working folder; the other study's journal had
named it to the owner as another session's. After the round a sweep by working folder, the harness's temporary
folders included, found no process of the four deliveries. And from 05:56 the commits on this line are made by a
Sonnet worker from messages and guarded scripts written here, at the owner's word; its first run stopped, rightly,
on a tree hash I had given it wrongly (the test receipt records the head's tree, not the staged one).

### Follow-ups from the asking-later test of the session "Spec elaboration" (2026-11-22, 07:27)

The owner's words to this session at about 07:12: "Follow up on actions for the spec elaboration". That session's
proposal for ShipLoop (`docs/experiments/spec-elaboration-20261120/PROPOSAL-shiploop.md`, on main in
8803536bb977f1bf9d090965dad573ccd8ec5abf; its journal's sections 59 to 61) names this session as the one that would
change the list. What it asks of the list, and what was done here:

| From the proposal | For the list | Done here |
| --- | --- | --- |
| The decision that mattered is on 9 of 9 lists right after the specification and no more often later | The list stays at the end of the spec stage; no repeat at a later stage | Recorded as a constraint; nothing to change |
| Asked to rank, a separate session puts that decision second to fifth and first in none of 27 lists | Rows carry no rank, and no display may be cut to a top one or three | Recorded as a constraint. The done packet and the report print every row. The next stage's packet prints rows in list order within 2,400 characters and then names a file that holds all of them (see below) |
| Lists made after the tests are longer, by what exists only once there is code | A second list after the build could only add to the report; not proposed | Nothing to build |
| On Sol the author's list leaves out what a roll-back loses | A gap in what the author picks, inside the instruction's own words ("a step they must take") | Its counts checked on this pilot's files (below); no change to the instruction before the release |
| One separate session after the specification, at most five added rows marked as a second reader's, if its test earns it | A change of its own, made here after the release | Waiting on that session's test; nothing started |
| The requester's answer is the half that changes what gets built | The route for that answer | Still the owner's open decision (F61, F64) |

**The gap, with this round added, checked on this pilot's files by a word search and by reading the rows.** On Sol,
one delivery of eight has a row that tells what going back loses (k2, row 5: "How can a rollback preserve original
due values if 1.4.0 writes?"), one row of 29 (the 21 rows of d1 to d6, five of k2, three of k3). On Sonnet both
deliveries have it (s1 row 5, k4 row 5). The other session's count is the same.

**A limit of the display, found while checking that constraint, and a correction to the round's entry above.** In
twelve of the thirteen deliveries every row fits the next packet's budget. In k4 it does not: the test-strategy
packet printed five of its six rows (2,104 characters) and the line "(1 more line not printed here: RUN/fields/...
holds all 6 whole)". Row 6 ("Does the command line show due times?") is in that file, in the done packet and in the
report. The round's entry and its table say the next packet "printed its block", which is true and leaves this
out; rule 3 as registered asked for the list in the spec result, the done packet and the report, and is met as
read. The cut is by size from the end of the list and not by rank, and the budget exists because the block must
stay inside the part of the packet every host prints whole. A list of long rows is shown one short at that stage;
nothing shows whether that matters.

**What the owner had just read before writing that, as that session told me.** Its answer to the owner's "What
should we do?" named two things for this session: the release question ("One thing only you can settle"), and its
recommendation that the answer route be built here as a candidate after the release. Neither is the owner's
decision yet, so both were put to the owner as plain questions right afterwards, and nothing was pushed or started
on either.

**What the other session reads of this pilot's, read-only, agreed here.** All thirteen kept deliveries: the nine
under `~/e2e-runs/r-20261121-2c3d50/` and the four of this round under `~/e2e-runs/r-20261122-ffb3fb/` (k4 by its
real run folder). Neither folder is pruned until that session says it is done. Its second-reader test runs under
the owner's standing approval for its experiments; its registration and its result are its own to journal.

**Main moved a second time while the decision waited (07:19).** The session "Shiploop SDLC" merged a change of the
ticket fixtures at the owner's word (9bf65a65e8d6b8a5f89ce428baddb1aafe44bbca): the base's own tests listen on
127.0.0.1, and four pins and every case's oracle digest change. The release commit that had been cut locally on the
earlier main at 07:00 (skill-craft 4.4.0, shiploop 2.6.0; its 35-suite tier had passed) was dropped unpublished, and
this line merged main again; its seven paths outside docs/ were read and allowed one by one beforehand. This round's
deliveries ran on the old base and stand as records of it. That session's own delivery on the new base, on released
ShipLoop without the list, also chose the refusal to start: five of twelve Sol deliveries without the list, four of
eight with it.
