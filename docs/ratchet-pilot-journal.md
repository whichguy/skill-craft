# Ratchet pilot journal

A living journal for the owner's idea of 2026-11-20: build a request in one pass, then let tests and what was learned
drive every further pass. Working name **Ratchet** (owner, 2026-11-20: "I like the name Ratchet. We can go with that for
now"). Nothing under `skills/` changes in this pilot; the apparatus is `docs/experiments/ratchet-pilot-20261120/`.

Status words: **firm** (measured, registered reading), **interim** (measured once or with a known limit),
**exploratory** (not registered), **superseded** (kept, with the date and the reason).

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
