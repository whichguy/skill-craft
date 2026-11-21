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
| ticket due times, high | in flight | | | | 3 of 8 at the first build | | |

Minutes by stage (spec, plan, build, heavy tests, fix, closing looks, gates and script): chess 9.6, 14.9, 15.1, 29.8,
0, 9.8, 5.9; shared expenses 7.1, 16.2, 26.9, 34.8, 3.0, 15.3, 15.1; ticket assignment high 9.6, 15.1, 26.9, 49.0, 0,
19.6, 12.7; medium 6.0, 11.2, 17.8, 32.6, 0, 9.9, 14.2. The heavy test pass is the largest stage in every run.

Registered readings:

- **R3.1, no loss: met on the five finished runs** (every held-out check passes at the end); the due-times run is
  read when it ends and starts from a first build that fails 5 of 8.
- **R3.2, reported.** Every finished run's first build already passed every held-out check. The loop had nothing to
  recover on any of them.
- **R3.3, reported.** A failing acceptance test led to a product change in one run of five: shared expenses, cycle 1,
  clause C-18 (a group id too long to address in a URL), repaired by one fix session of 3 minutes. Closing-look
  clauses led to product changes in every run: each second and third build changed the product (the last column).
- **R3.4, time: slower.** Ticket assignment on Sol 6.2 medium took 91.8 minutes and 177,302 output tokens; ShipLoop's
  whole delivery of the same case on the same model and effort took 13.2 minutes and 29,066 (7.0 times the time, 6.1
  times the output tokens), with the same 18 of 18 held-out checks. Ratchet's first build alone came at 17.2
  minutes. ShipLoop's delivery also released and reviewed; Ratchet stops at a product.
- **No run converged.** All five ended at the three-cycle limit with the last closing look still adding items (1, 1,
  3, 6, 3). The limit is the apparatus's, so "does it end by itself" is not answered; nothing seen suggests it does.

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
