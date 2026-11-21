# Ratchet in parallel, with catch-up: journal

A side line of the Ratchet pilot (`docs/ratchet-pilot-journal.md`), kept in its own file because the pilot's journal
is being written by another session on another branch. This session is a fork of that conversation, made by the
owner at 08:00 on 2026-11-21 to think about one question. It writes only in its own worktree and reads the pilot's
runs without changing them.

## 0. Where it ended (2026-11-21 10:52; stopped at the owner's word)

**Stopped, not built.** The owner, after the reading on time alone and the catch-up note in section 7: "Yes, stop
here". Nothing under `skills/` changed; the apparatus is in `docs/experiments/ratchet-pilot-20261120/`.

- **What was measured (rung 1, section 6).** A test pass written without ever seeing the build needed no catch-up:
  42 of 42 and 41 of 41 items on the real builds and on each other's, 41 of those items having never passed
  anywhere before. What the writer needs is the plan's answers at the open points and the names it fixes, not the
  build. Two sessions, one request, one model family.
- **Why it stops (section 7).** It buys waiting time only, and little. The test pass is the longer stage, so the
  saving is the build's length at most: 9 of 33 to 39 minutes, and 9.8 and 2.5 minutes with the lengths the
  build-less sessions took. Tokens do not fall. A catch-up after a build that takes another answer than the plan's
  is unmeasured and can only shrink the saving. The stage being hidden changed nothing in these two products, and
  the pilot's verdict was not to build the loop this would speed up.
- **Worth keeping, with no parallel machinery.** A test writer runs its tests on the starting product first: a
  test of existing behaviour must pass there and a test of new behaviour must fail (section 6, P1.2); and it keeps
  everything that drives the product in one adapter file (section 6).
- **Not run.** Rung 2 (how strong a build-less suite is on the planted defects; how long a catch-up takes when 10
  to 12 items need the adapter changed), rung 3 (two sessions truly at once), the split test pass and the decide
  step. Sections 3, 4 and 7 say what each would settle, for whoever takes this up again.
- **Tools left.** `overlay.py` runs one run's frozen suite on another run's product (give it `--scratch` with a
  plain folder and `--history product`; section 6 says why). `ratchet.py run --tests-blind-from RUN --stop-after
  tests` runs the test pass with no build present.

## 1. The question (owner, 2026-11-21 08:00)

"One of the things that I was trying to consider is whether we should, in Ratchet, do something where we try to
determine how much we could do in parallel from the beginning. For example, we could build the test cases in
parallel while doing the actual build, and then, after the build is done, figure out what we need to update for the
test cases. The idea is that we don't wait for perfect. We actually try to do some imperfect actions, and then
figure out what we need to wait for in order to get the totality of what we need to handle, and then 'catch up' if
need be. Or maybe even: is there anything material we need to catch up with, or could we, for example, start the
tests as soon as build finishes? Tests are written in parallel with the build, and then, after the tests finish, we
have the catch-up phase for the tests. I really want to try to see if we could think about how best to put things
in parallel with catch-up or fix-it kind of activities based on the termination of another activity."

My reading: design a schedule in which a stage starts as soon as the least it needs exists, says what it assumed,
and gets a short catch-up when the stage it did not wait for ends; and find out, before building anything, how big
that catch-up is.

History that bears on it (pilot journal, sections 3 and 7): the review before the pilot advised writing tests blind
to the code. The pilot did not run that arm, because the owner's order put the test pass after the build ("Tests
written blind to the code are an arm this pilot does not run"). Writing tests beside the build is that unrun arm,
with a catch-up added.

## 2. What the finished runs already say (2026-11-21 08:12; no model ran)

Status: firm as counts of the runs named; a reading from records, not a registered experiment.

**Where the minutes go** (the reworded text's two due-times loops, pilot journal section 21): enrich 4.6 and 4.3,
plan 6.9 and 5.0, build 9.0 and 8.7, heavy test pass 16.7 and 13.4, gates 1.7 and 1.3; 38.9 and 32.8 in all. The
test pass is the longest stage in every run of the pilot, and it waits for a build it does not need in order to be
written.

**What a suite needs from the build it was written beside** (`overlay.py`, new: it lays one run's frozen suite over
a product from another run, as `grade.py` lays it over a variant, and runs every clause command once). Three
suites of the same request (ticket due times) and three correct products, each of which passes the held-out checks:
loop a's build and loop b's build, made from two specifications of the reworded text and their own plans, and the
harness's reference.

> **Superseded 2026-11-21 09:05** (section 6): the tool made its copies under the system's temporary folder, which
> fails tests that watch `npm test`. Measured again, the table reads 41, 39, 30; 41, 41, 31; 32, 32, 35. The
> readings below it stand; of the counts in them, "7 further items" stays 7 and "10 to 13" becomes 10 to 12.

| Items passing | on loop a's build | on loop b's build | on the reference |
|---|---|---|---|
| loop a's suite, 42 items (written beside a's build) | 39 | 38 | 29 |
| loop b's suite, 41 items (written beside b's build) | 41 | 41 | 31 |
| the test-strength cell's suite, 39 items (written beside the reference) | 31 | 31 | 35 |

- **Between two products that took the same answers at the open points, a suite transfers whole.** Loop b's suite
  passes 41 of 41 on a build it never saw, from another specification and another plan. Loop a's suite loses one
  item on b's build that it passes on its own (C-34, which looks for the titles of that build's own tests). The two
  plans had chosen, each on its own, the same names for the hour settings and the same answer to the start
  question.
- **Between products that took different answers, what fails is how the product is driven, not what is asserted.**
  The suite written beside the reference fails 7 further items on the loops' builds, and each loop's suite fails 10
  to 13 on the reference. Read one by one, they are: how the hours are set (the reference reads one
  `RESPONSE_HOURS` setting, the loops four `DUE_HOURS_*` ones), how and when the data file is prepared, and the
  items about the product's own tests. No item fails for another reason.
- So what a test writer needs is not the build. It is the handful of answers the plan gives at the open points and
  the names it fixes. With those shared, the catch-up measured here is 0 to 1 item in about 41; without them it is 7
  to 13.
- Ticket assignment says the same from another side: a suite written beside the reference fails 3 further items
  of 53 on the harness's second correct delivery (pilot journal, section 21).

Apparatus notes. On loop a's own build the tool counts 39 of 42 where the run's own gate counted 41 of 42: two
items about `npm test` (C-33, U-8) fail in the exported copy and passed in the run's work folder; not examined, and
they fail the same way on both products, so they do not move the comparison. The machine's load average was 6 to 7.
The suites and builds compared come from different specifications, which a parallel run would not have: the counts
are an upper bound on its catch-up.

**How much a test session uses the product while it writes** (08:16; exploratory: counted from the five test
sessions' event records by a Sonnet subagent, at the owner's standing word to use one where possible, with each
command labelled by hand; I checked its method and the command totals roughly, not each label;
`evidence/parallel/test-session-activity.md`).

| Test session | Shell commands | Runs of its own acceptance tests | of those, showing a failing test | First such run comes after | Product code files read |
|---|---|---|---|---|---|
| due times, loop a | 36 | 12 | 7 | 50% of the commands | 2 |
| due times, loop b | 25 | 5 | 1 | 52% | 12 |
| due times, test-strength cell | 29 | 8 | 7 | 62% | 12 |
| ticket assignment, test-strength cell | 31 | 6 | 4 | 61% | 5 |
| orders, test-strength cell | 29 | 9 | 6 | 48% | 0 |
| all five | 150 | 40 | 25 | | |

- A test session spends about the first half of its commands reading and writing, and runs nothing of its own
  until then. From there it runs its tests on the product 5 to 12 times, and in 25 of 40 runs a test fails.
- So the test pass has two halves. The first, writing, needs the specification and the plan. The second,
  getting the tests to run true, needs a product. This is the part the overlay above cannot see: it compared
  suites that had already been through it.
- That answers "is there anything material to catch up on" more exactly. Not what the tests say (nothing, when the
  answers are shared). Getting them to run: about half a test pass, which has to come after the build, except for
  tests of existing behaviour, which can be run on the starting product while the build is still going (13 to
  24 of these specifications' 31 to 44 clauses are `existing`).

## 3. The design this points to

**One rule.** A stage starts when the least it needs exists. It writes down what it took as given. When a stage it
did not wait for ends, a script compares that stage's result with what was taken as given, and starts a catch-up
only for what differs. The script owns the schedule; a session still does one job.

**What each stage needs, at the least.**

| Stage | Needs to start | Does not need | What ends before it can finish |
|---|---|---|---|
| enrich (specification) | the request, the repository | | |
| decide (new, short): one answer for each open point, and the names both sides will use | the specification | | |
| plan the rest (nuances, order of work) | the specification, the decisions | the build | |
| build | the specification, the decisions | the rest of the plan, the tests | the rest of the plan: its nuances reach the build as a catch-up |
| write tests | the specification, the decisions, the starting product | the build | the build: only to run them |
| run tests on the starting product | the tests | the build | |
| gate | the build, the tests | | |

**The schedule.** Enrich, then decide. Then three things at once: the build; the test pass, written behind one
adapter file that holds everything about how the product is started, configured and called; and the rest of the
plan. Each ending triggers a script step:

1. *Tests end first or while the build runs:* the script runs them on the starting product. A test of existing
   behaviour must pass there and a test of new behaviour must fail there. Anything else is flagged at once (loop
   a's tab-in-a-title test would have been caught here, before any build existed).
2. *The rest of the plan ends:* its nuances wait for the build.
3. *The build ends:* the script compares the answers in the build report with the decisions. If they agree and the
   suite passes, there is no catch-up. If the build took another answer somewhere, only the tests of those clauses
   go to a catch-up session, which may change the adapter and nothing else without a referee. The build gets one
   catch-up of its own: the nuances it was not given, and the failing tests that are not adapter matters.
4. *Gate*, and from there the loop as it is.

**Where not to start early.** Not before the decisions. A build started from the request alone would save the most
and would bring back what the pilot found doing the harm: a decision taken silently at build (F20, F24, F28; the
other session's census of limits chosen at build and written nowhere). Catching up from a wrong decision is rework,
not catch-up.

**Guards.** Tests must not be weakened to pass: in catch-up the adapter may change, an assertion may not without a
session that neither built nor wrote it. Build and tests write in separate copies of the work repository and the
script merges them by path. In an experiment the calibrated defects say whether a caught-up suite is still as
strong (36 of 37 today).

**What it would buy, from measured stage minutes (a projection, not a measurement).**

| Schedule | Loop a | Loop b |
|---|---|---|
| as run: one after another | 38.9 | 32.8 |
| tests written beside the build after the whole plan, then got to run true on it (half the test pass each way) | about 30 | about 26 |
| the same, with both halves of the test pass split among three writers by area | about 25 | about 22 |
| the same, with a short decide step (2.5 minutes assumed) in place of waiting for the whole plan | about 21 | about 19 |

> **Superseded 2026-11-21 09:05** (section 6): for a change to an existing product the second half runs on the
> starting product, so nothing has to follow the build. The table above is too cautious; section 6 gives the
> corrected projection and the measured lengths.

These take the second reading at its word: half of a test pass can run beside the build and half must follow it.
So writing tests beside the build saves about a fifth, not the whole length of the build. Splitting the test pass
is the larger lever and needs no catch-up of its own: the loops' test sessions already wrote their tests in
several files by area. The decide step only pays once the test pass is split, because until then the test pass,
not plan and build, is the longest path. What could shorten the second half is not in these numbers: tests of
existing behaviour got to run true on the starting product while the build is still going.

It buys time only. Tokens do not fall; a split test pass and a catch-up add some. By the owner's order of
priorities (quality, then tokens, then time) it is worth having only if quality holds, and the same instruments
that measured the texts can say whether it does. One reason to expect quality to hold or rise: a test written
without sight of the build cannot write down what the build happens to do.

## 4. Unknowns, and the smallest runs that would settle them

Not registered and not run. Each rung reuses a specification, plan and build already on file, so only the new
session is paid for.

| Rung | What runs | About | What it settles |
|---|---|---|---|
| 0 | done above, no model | 6 minutes | the catch-up is small when decisions are shared |
| 1 | one test session for loop a's specification and plan, with the starting product and no build; then the script runs its suite on the starting product, on loop a's build and on loop b's | 15 minutes | how many tests a writer gets wrong when it cannot run them on the product (the part rung 0 cannot see), and what the run on the starting product catches |
| 2 | a catch-up session on what failed; then the same test-strength reading as today on the caught-up suite | 10 minutes | whether catch-up keeps the tests as strong |
| 3 | the loop with build and tests truly at once, in two copies | 25 minutes | the wall-clock gain, against 33 to 39 |

Open questions rung 0 does not touch: how often a test session runs its tests on the product while writing (being
counted from the five test sessions' records now); whether a short decide step answers as well as the whole plan
did on due times (two of two); whether the rest of the plan changes a build that did not wait for it.

## 5. Rung 1, registered 2026-11-21 08:21: two test sessions that never see the build (before any run of them)

Owner, 08:18, to "Should I run the 15-minute step, one test session that writes without the build?": "Yes, run it".

**What runs.** The test pass of the pilot's loop, started from a specification and a plan already on file and from
the starting product, with no build present, then stopped. Two cells, so that one draw is not read alone:
`b1-due-times-a` from the specification and plan of the reworded text's loop a, `b1-due-times-b` from those of loop
b (pilot journal, section 21). Codex `gpt-6.2-sol` at high, as in the loops; a new Git repository each, in a runs
root of this session's own. Each loop's build was made from that same specification and plan, by a session this
test writer never meets, and each loop's own test session wrote its suite beside that build: those two suites are
the comparison.

**The instructions.** The standing test packet with five passages changed and nothing else
(`evidence/parallel/tests-packet-blind-against-standing.diff`): it is told the build is being made elsewhere and is
not here; it keeps everything about how the product is started, configured and called in one adapter file, taking
names and the answers at open points from the plan; it runs its tests on the starting project, where a test of an
`existing` clause must pass and a test of new behaviour must fail for the reason its clause gives; and its report
lists what it had to assume. The frame's paragraph on open points is unchanged.

**Apparatus** (in this branch only): `ratchet.py run --tests-blind-from RUN --stop-after tests` copies RUN's
specification and plan as they stood after its plan stage, runs the test pass with those instructions, and gates
the suite on the starting project. Self-tested with the scripted stand-in before this entry: the standing check
passes for all three texts; a run from a source stopped at its build holds one session, no product file of that
build, an identical plan, and a prompt that says the build is not here; the two wrong combinations are refused.
Afterwards `overlay.py` runs each new suite on the two builds.

**Readings.**

- **P1.1, what a writer gets wrong without the build.** Items of the new suite that fail on the build made from its
  own specification and plan, under `overlay.py`, beside the loop's own suite under the same tool (loop a: 3 of 42
  fail; loop b: none of 41). *Little to catch up* at 5 failing items or fewer; *about half a pass or more* above a
  third of the items; *some* between. Each failing item is then read into one of four kinds: the test drives the
  product in a way the plan does not give or the build did not take; the test is wrong in itself; the build breaks
  the clause, and the suite written beside the build did not say so; the test asserts an answer to an open point.
- **P1.2, what the starting product catches early.** In the run's own gate, on the starting project: tests of
  `existing` clauses that fail (a test that is wrong or stricter than the shipped product, known before any build
  exists), and tests of other clauses that pass (a test that does not test the change). Counted and read.
- **P1.3, carry-over.** The same suite on the other loop's build.
- **P1.4, cost.** Minutes and output tokens of the session beside the loop's own test session (16.7 and 13.4
  minutes), and what it ran.
- Strength against planted defects is not read at this rung. It is rung 2, and only if P1.1 is not "about half a
  pass or more".

**Predictions, mine.** P1.1: some, 4 to 10 items on each build, most of them tests wrong in themselves, one or two
about how the product is driven, none asserting an answer to an open point, and at most one that a build really
breaks. P1.2: one to three tests of existing behaviour fail on the starting project. P1.4: a shorter session, 10
to 13 minutes, because it cannot run to green.

**Limits known before the runs.** Two sessions, one case, one model family. The suites compared were written by
other draws of the test session, so a difference of two or three items is inside the spread seen in section 2.
The overlay's exported copy differs from a run's own folder on two `npm test` items of loop a (section 2), so
every count is taken under the one tool. A wrong test and a strict test are told apart by reading, which a Sonnet
subagent drafts and I check.

## 6. Rung 1, result (2026-11-21 09:05; two test sessions, 08:21:47 to 08:43:27)

Status: firm for what was run: two sessions, one request, one model family. Both specifications were accepted by the
script on the first try; neither session's record holds a held-out mark; neither built or copied a product (each
ended with the product's files unchanged).

**P1.1, what a writer gets wrong without the build: nothing, in either cell.**

| Suite | Written | On the build made from its own specification and plan | On the other loop's build |
|---|---|---|---|
| `b1-due-times-a`, 42 items | without the build | 42 of 42 | 42 of 42 |
| `b1-due-times-b`, 41 items | without the build | 41 of 41 | 41 of 41 |
| loop a's own, 42 items | beside its build | 41 of 42 (C-31) | 39 of 42 |
| loop b's own, 41 items | beside its build | 41 of 41 | 41 of 41 |

- The bar for "little to catch up" was 5 failing items; there are none, so no item was left to read into the four
  kinds. My prediction of 4 to 10, mostly tests wrong in themselves, was wrong.
- The one failing item in the table belongs to the suite written beside the build: loop a's C-31, the test that
  writes a tab into a ticket title by hand and is stricter than the shipped product (pilot journal, section 21).
  The session that wrote without the build has no such test: it had to make its tests of existing behaviour pass
  on the starting project, and a test stricter than the shipped product cannot.

**P1.2, what the starting product catches early.** Each session ran all its commands on the starting project and
reported the exceptions, as asked.

| Cell | `existing` items | of them failing on the starting project | other items | of them passing there |
|---|---|---|---|---|
| a | 16 | 2 (C-7, C-22) | 26 | 7 (C-3, C-13, C-23, C-28, C-29, C-33, U-5) |
| b | 18 | 1 (U-6) | 23 | 4 (C-8, C-11, C-28, C-33) |

Each is explained in the session's report and none is a wrong test. The failing `existing` items are clauses the
specification filed under an existing convention whose observable needs the new behaviour (C-7: "1.4.0 ignores the
response-hours setting ... The configuration-error convention is existing, but applying it to the new setting is
new"). The passing others are clauses already true of the old release (answers stay as in 1.4.0 with the feature
off; the old release can read the file). So the Source label is too coarse to decide by script which tests must
pass on the starting project; the session's own account is what makes the run useful.

**P1.3, carry-over: whole.** Each suite passes every item on the other loop's build.

**P1.4, cost and what the sessions did** (counted from the event records by a Sonnet subagent; labels by hand;
`evidence/parallel/blind-session-activity.md`).

| Test session | Minutes | Output tokens | Shell commands | Runs of its own tests | of those, showing a failure | First such run | Product code files read |
|---|---|---|---|---|---|---|---|
| a, without the build | 15.9 | 44,295 | 26 | 3 | 3 | command 18 of 26 | 12 |
| b, without the build | 19.7 | 51,912 | 35 | 8 | 6 | command 17 of 35 | 16 |
| a, beside the build | 16.7 | 43,678 | 36 | 15 | 7 | command 14 of 36 | 3 |
| b, beside the build | 13.4 | 35,653 | 25 | 5 | 1 | command 13 of 25 | 12 |

- A session without the build is not cheaper: about the same in cell a, 47% longer with 46% more output tokens in
  cell b. The machine's load average was 6 to 11 throughout, so the minutes are loose. My prediction of a shorter
  session was wrong.
- It still runs its tests, on the starting product: 3 and 8 runs. That is where its "second half" went. Section 2
  read the second half of a test pass as needing the build; this says it needs *a* product, and for a change to an
  existing product the starting one will do.

**The adapter** (same subagent's count). Each session kept everything that drives the product in one file: 446 of
1,584 acceptance lines in a, 465 of 1,463 in b. Outside it there is no process start and no product setting's
name. In the suites written beside the build the setting names are spread through the test files (`DUE_HOURS` 12
and 11 times outside the helper file, `DATA_FILE` 5 and 2, `DUE_TIMES` 3 and 8). Every name an adapter sets to
start or configure the product is in the plan (`PORT`, `DATA_FILE`, `DUE_TIMES`, the four `DUE_HOURS_*`, `--data`)
or in the specification and the starting documents. Each report lists what it had to assume: three and four
things, the first in both being that the plan's starting commit does not exist in this repository and the local
one is used.

**The measuring tool was wrong in one way, and is corrected.** `overlay.py` first made its copies under the system's
temporary folder. On macOS that folder is reached through a symbolic link, and a test that watches `npm test` by
file path then sees no test run. Shown by running one suite on one product both ways: session a's C-33 passes in
its run's own gate on the starting project and failed in the copy. With `--scratch` naming a plain folder, and
`--history product` giving the copy the product's repository as one shared run would have, the tool reproduces
three counts the runs themselves made: 21 of 42 for session a's suite on its starting project, 41 of 42 for loop
a's suite on its build, 41 of 41 for loop b's. The first readings of this section's table, taken before the fix,
were 39 of 42 and 38 of 41 with three `npm test` items failing in each; they were reported to the owner at 08:42
and corrected at 09:00.

**Section 2's table, measured again with the corrected tool** (the first version is marked superseded there).

| Items passing | on loop a's build | on loop b's build | on the reference |
|---|---|---|---|
| loop a's suite, 42 items | 41 | 39 | 30 |
| loop b's suite, 41 items | 41 | 41 | 31 |
| the test-strength cell's suite, 39 items | 32 | 32 | 35 |
| session a's suite, written without a build, 42 items | 42 | 42 | 31 |
| session b's suite, written without a build, 41 items | 41 | 41 | 31 |

The test-strength cell's suite and the two loops' builds come from repositories with different starting commits,
and each side has tests that read its own: its row is given under the history that fails fewer items (the suite's;
under the product's it is 26 on loop a's build). The readings of section 2 stand: between products that took the
same answers a suite carries over, and against the reference, which took others, 10 to 13 items fail.

**What this changes in the design of section 3.**

1. Tests can be written beside the build with nothing to catch up, when both have the plan's answers. Two of two.
2. The catch-up is not "half a test pass" for a change to an existing product: the session gets its tests to run
   true on the starting product. Section 3's projection can drop the second half. Taking the test pass at the
   length the loops' own took, tests beside the build come to 29.9 and 24.0 minutes for loops a and b, against
   38.9 and 32.8 as run. Taking it at the length these two sessions took on a loaded machine (15.9 and 19.7), they
   come to 29.1 and 30.3. So the gain is between a twelfth and a quarter until a run measures it, and the test
   pass is still the longest path: splitting it remains the larger lever.
3. The starting-product run earns its place. It is where the one over-strict test of the sequential suite would
   have been caught, and the session's account of the exceptions is short and checkable.
4. The adapter is real and cheap: one file, a third of the suite, nothing bypassing it. That is what would make a
   catch-up small when a build takes another answer than the plan's, which these two builds did not.

**Is there enough to conclude early?** On whether a test pass can be written beside the build without a catch-up:
for this request and this model, yes, two of two with nothing failing. Not yet on the two things that would make
it safe to adopt: whether such a suite catches planted defects as well as one written beside the product (a suite
can pass on a correct build by asserting little), and what the catch-up costs when the build does take another
answer. Rung 2 measures both at once, because the planted defects are variants of the reference, which took
other answers than these plans.

Evidence: `evidence/parallel/` (`overlay-rung1.json` and `-log.txt`; `overlay-due-times-v2.json` and `-log.txt`;
`b1-due-times-a/` and `-b/` with each run's record, prompt, report, manifest, adapter and its gate on the starting
project; `blind-session-activity.md`).

## 7. Judged on time alone (2026-11-21 10:47; a reading from records, no model ran)

Status: exploratory: arithmetic on stage lengths already on file, and my recommendation. The owner's decision is
pending.

The owner asked, after section 6: "Given these results, considering that the only value is time efficiency, help me
decide". My reading: working in parallel buys waiting time and nothing else (section 3 already says tokens do not
fall), so the question is whether the minutes are worth going on for.

**The saving has a ceiling: the build's length.** The test pass is the longer of the two stages put side by side,
so the first pass can shorten by the build's 9.0 and 8.7 minutes and by no more.

| Ticket due times, minutes to the first gate | Loop a | Loop b |
|---|---|---|
| as run, one stage after another (section 2) | 38.9 | 32.8 |
| tests beside the build, the test pass as long as it was beside the build: the ceiling | 29.9 | 24.1 |
| the same, with the lengths the two build-less sessions of rung 1 took (15.9, 19.7) | 29.1 | 30.3 |
| to the first build with no test pass (enrich, plan, build; pilot journal, section 21) | 20.5 | 18.1 |
| projected: tests beside the build, split among three writers, after a 2.5-minute decide step | 17.8 | 16.8 |

- With the measured lengths the saving is 9.8 minutes in one loop and 2.5 in the other, a quarter and a twelfth.
  Section 6's "about 24 and 30" used the lengths of the sessions written beside the build; the third row is the one
  to quote.
- Four test sessions for this request took 13.4, 15.9, 16.7 and 19.7 minutes. That spread, 6.3 minutes, is two
  thirds of the ceiling, so a measured gain would need several runs a side, and no further run can raise the
  ceiling. The machine's load was 6 to 11 during rung 1.
- The last row rests on two assumptions, neither measured: that a decide step takes 2.5 minutes and answers as well
  as the whole plan, and that a test pass split in three ends before the build does. Tokens rise with it.
- Output tokens do not fall: 1% and 46% more in the build-less sessions (section 6).

**What the stage being hidden changed in these two loops: nothing in the product.** Both first builds passed 8 of 8
held-out checks before any test of the loop ran (`p3R-ticket-due-times-a.build-1.hidden.json` and `-b`, in the
parent session's runs). The first gates failed one item in loop a, C-31, a test stricter than the shipped product,
and none in loop b (`first_gate_failing` in each `run.json`). The pilot's section 0 has the same over five whole
loops: one acceptance clause failed naturally. So on time alone, leaving the test pass out saves 13.4 to 16.7
minutes, where putting it beside the build saves 9 at most.

**For scale.** ShipLoop's whole deliveries of the same request on the same model and effort took 19.7, 20.0 and
25.3 minutes (`docs/shiploop-sdlc-structure-journal.md`, R68; held-out results on high there: 8, 8, 3 and 3 of 8,
where the two first builds from the reworded text passed 8 of 8). The pilot's one matched whole loop, ticket
assignment on Sol 6.2 medium, took 91.8 minutes against ShipLoop's 13.2 (pilot journal, R3.4), its first build
alone coming at 17.2: the time went after the first build, in the test pass and the cycles, and this design
touches only the first pass.

**Recommendation put to the owner.** Stop the parallel line here and do not run rung 2. The strength check answers
whether the tests stay strong, not how much time is saved; it is worth its 30 minutes only if a loop with its own
test pass is going to be built. If one is, writing the tests in parallel is how to have that pass without waiting
longer for it (the last row against the fourth), and the next rung is then the split test pass, the larger lever,
with one strength check at the end on the suite the whole design produces. Worth keeping either way: the test
writer's run on the starting product (section 6, P1.2), which needs no parallel machinery.

**Addendum, 10:51: what these rows include of catching the tests up.** The owner asked: "even though we wrote
the tests in parallel, we may have to update the tests after the code has been written. Are we including that
catch-up-to-accuracy time for the tests in our evaluation?" Partly:

- *Included:* the time each build-less session spent getting its own tests to run true. With no build it ran them
  on the starting product, 3 and 8 times, inside its 15.9 and 19.7 minutes. Also included: one run of the finished
  suite on the finished build (the gates' 1.7 and 1.3 minutes).
- *Included at its measured value, which is nothing:* updates after the build. Of the 83 items, 41 had never
  passed anywhere before the build existed for them (21 of session a's 42 and 20 of session b's 41 fail on the
  starting project; section 6, P1.2). All 41 passed the first time the suite was run on the build. Two of two.
- *Not included:* a build that takes another answer than the plan's at an open point. Neither build did. Against
  the reference, which did, 10 to 12 of about 41 items fail in each of the four suites, and what has to change is
  how the product is set up and called, not what is asserted (section 6's last table; section 2). How long that
  catch-up session takes is not measured; the shortest session on file is a 3-minute fix of one clause (pilot
  journal, R3.3). It also costs a second run of the gate.
- *Break-even.* At the ceiling the saving survives a catch-up session shorter than 7.3 and 7.4 minutes (9.0 and
  8.7, less a second gate). With the measured lengths it survives one shorter than 8.1 minutes in loop a and 1.2
  in loop b: in loop b's case any catch-up at all makes the parallel schedule slower than one stage after another.
- A test pass written after the build pays nothing when the build takes another answer: the writer sees what the
  build did. The cost of a differing answer falls on the parallel schedule only.

So the third row is the parallel schedule's best case on catch-up, and what is unmeasured can only lower the
saving. It does not change the recommendation. It would matter to a decision to go on, and rung 2 would then come
first: it measures a catch-up session's length when 10 to 12 items need the adapter changed.

## 8. The owner's design-phase idea, and what the runs say about it (2026-11-21 10:56; a reading, no run)

Status: exploratory. It reads sections 2 and 6 against the idea; nothing new was measured.

The owner, just after stopping the line: "Maybe one idea is also: do we need to make sure that we have a phase
where we do a design, such that the design is designed up to the point where we know what the plan is to implement
and we know how to ensure that the test can actually be implemented based on the design principles? But some of
the things, specifically how to execute tests, might come out of spec to be more specific after the code has
actually been written."

My reading: a design phase whose exit is "the plan to implement is known, and every test can be written from the
design", with one part allowed to stay loose until the code exists: how a test is executed.

**The runs drew that same line, and say what sits on each side of it.**

| Part | When it can be final | What the runs showed |
|---|---|---|
| What the design must fix: one answer at each point the request leaves open, and the names of everything a test touches (settings, commands, files) | before any code | With these shared, tests written with no code present passed 42 of 42 and 41 of 41 on the code when it came (section 6). The plan held them: every name an adapter sets is in the plan, the specification or the starting documents |
| What each test asserts | before any code | About 70% of the test code (1,138 of 1,584 lines and 998 of 1,463 sit outside the adapter). None of it changed after the build |
| How a test is executed: starting the product, configuring it, calling it | drafted from the design, confirmed once the code exists | One adapter file, about 30% of the test code (446 and 465 lines). Unchanged in two runs of two. Against a product that took other answers, the 10 to 12 failing items of about 41 all fail here, none on what is asserted (sections 2 and 6) |

- So the owner's exception is the right one and it can be fenced: how tests execute is the only part that had to
  wait for a product, and it fits in one file.
- A check for "is the design far enough along" came out of rung 1 unasked: the test writer's list of what it had
  to assume (`## Assumed` in each `tests-1.md`). It was three and four items, and all seven are about execution:
  which base commit is at hand, ports, clock and fault controls, file permissions, how `npm test` is observed.
  None is a name or an answer the design left out. An assumption the design should have settled would be a gap in
  the design; an assumption about execution belongs in the adapter.
- A second check needs no build either: run the tests on the starting product. A test of existing behaviour must
  pass there and a test of new behaviour must fail (section 6, P1.2).

**ShipLoop already has the phase; Ratchet's loop had only part of it.** ShipLoop's stages before any code are
`intake`, `discovery`, `research`, `spec`, `test-strategy`, `plan`, `prepare` (`PRELUDE` in
`skills/shiploop/scripts/shiploop_stage_spec.py`); each step then runs `step-plan`, `test-spec`,
`validate-existing`, `implement`, `test` (`INNER`); and `system-test-author` comes after the code (`OUTER`).
`test-strategy` "records, before any code, which harness tests each part of the code at each layer and where the
tests run" (`references/testing-and-documentation.md`). The pilot's loop had a plan before the build and wrote all
its tests after it.

**Not known.** Whether ShipLoop's `test-strategy` and `plan` texts ask for the two things in the first row (they
ask for harnesses and layers; I have not read whether they ask for the names and the open answers). And how often,
in finished ShipLoop deliveries, a test is changed after the code it tests was written, and whether such changes
are execution or assertion. The second can be counted from archived deliveries with no model: each delivery's
repository has the commits. Offered to the owner, not run.

**Read after writing the above (10:58): what ShipLoop's stages ask for, before and after the code.** From the
`Stage` entries in `skills/shiploop/scripts/shiploop_stage_spec.py` (their `done_when` and duty lines). This
settles the first of the two unknowns above: the texts do ask for it.

| The idea's part | ShipLoop stage, and what its text asks |
|---|---|
| the plan to implement is known | `plan`: ordered work items; "the assumption list is complete: each assumption evidenced, probed, or open with the item that settles it"; "Plan namespaces, placement, schema and storage up front". `step-plan`: "Name target files, interfaces and conventions" |
| the tests can be written from the design | `spec`: "each acceptance line is independently verifiable and says how it will be confirmed". `test-strategy`: every acceptance line "maps to a check, its surface and the stage it is due", each needed tool's route probed "against a stand-in while the product does not exist". `test-spec`: each case has "an independent oracle, a RED and a GREEN definition", and "Write no test code" |
| how tests execute gets specific after the code | `implement`: "Tests are written in the test stage". `test`, which follows it: "Write the tests from the test spec"; "no test ID new at this step passes on the step's base checkout"; "every test change made to pass a run has a recorded independent reason". `system-test-author` follows all items |

- The phase exists in ShipLoop's text, with the line where the owner puts it: what a test asserts is specified
  before the code, and its code is written after.
- ShipLoop also has the rule for the owner's earlier question (the addendum to section 7): a test may be changed
  to make a run pass only with a recorded independent reason. Those records are in each delivery's results, so the
  count offered above can be taken from them.
- Two things section 0 lists as worth keeping are already ShipLoop's. The run on the starting product is its check
  that no new test passes on the step's base checkout, with `validate-existing` running every expectation on the
  item base. The strength question is its mutation check (the comment on `test-spec` names "RED on the base, the
  candidate run, the mutation check"). They were new only to the pilot's loop, which wrote all its tests after
  the build.
- What a text cannot say is whether deliveries hold the line. The second unknown stands: how often a test is
  changed after its code was written, and whether the recorded reason is about execution or about what the test
  asserts.

## 9. Is the case complex enough? (owner, 2026-11-21 11:24; a reading and a proposal, nothing run)

Status: exploratory. It states a limit of sections 6 to 8 and proposes a ladder; nothing is registered.

The owner: "Are we using a sufficiently complex test in order to evaluate this? We might need to do something
more, like create an app in Node. Could be a game, could be a Grokbot emulator, in order to really identify more
complexity in the app, which would indicate more complexity in the test."

**No. Every count this journal holds about tests comes from one request, and it is the easy case in two ways.**

- The request is ticket due times: a change to an existing small service, 41 and 42 test items.
- A working product already existed. The build-less writers ran their tests on it, 3 and 8 times (section 6). A
  new app has nothing to run on: `node-chess-engine` starts from 2 files and `grokbot-local` from 8 (a stand-in
  provider and records).
- There is no user interface. Driving the product meant a few settings and an HTTP service. The pilot's Grokbot
  suite drives a page in Chromium (`acceptance/browser.cjs` in the pilot's `g-ratchet-sol-high` run), and there
  how a test executes is the larger part: the part the owner expects to firm up after the code (section 8).

So sections 6 and 8 are firm for what was run and say nothing yet about a new app, or about one with a page.

**What is on file for the two apps the owner names.** Both are cases of the pilot with held-out checks, run again
this morning with the reworded text at the owner's earlier suggestion (pilot journal, section 21).

| Case | Reworded specification | Starting files | Plan and first build on file (`p3R-*`) | Test pass with the pilot's text |
|---|---|---|---|---|
| `node-chess-engine` | 63 clauses | 2 | plan 4.7 and build 5.8 minutes; 10 of 10 held-out checks | 17.2 minutes for 109 clauses |
| `grokbot-local` | 115 clauses | 8 | plan 7.0 and build 15.0 minutes; 49 of 49 and 28 of 28 | 29.2 minutes for 289 clauses |

- No test pass exists for either with the reworded text: both runs stopped after the build.
- What the earlier runs on these cases showed is about builds: every arm builds both correctly, so size gave no
  headroom there (pilot journal, section 0, R5.1 to R7.1, and section 21). What size does to tests written from
  the design has not been looked at.
- The two stress different sides of section 8's line. Chess is dense in rules and simple to drive: it asks whether
  expected results are right when there is no product to check them against (what tests assert). Grokbot is
  large, loosely worded and driven through a page: it asks how much of a test can be written before the page
  exists (how tests execute).

**Proposed, smallest first; not registered, not run.**

1. `grokbot-local`: one test session from the specification and plan of `p3R-grokbot-local` with no build present
   (`--tests-blind-from`, the packet unchanged from rung 1), then its suite on the build on file. Readings as in
   rung 1: items passing at first meeting; each failure read as execution or assertion; the adapter's share; the
   writer's list of assumptions read as design gap or execution. About 30 minutes.
2. `node-chess-engine` the same way, about 20 minutes, if step 1 leaves the assertion side open.
3. Beside either, from records: section 8's count over finished ShipLoop deliveries, split by size (ShipLoop's
   harness has `battleship`, `battleship-scoring` and `checkers` among its 31 cases).

This would test the design-phase reading on a harder app. It does not reopen the parallel schedule, which stays
stopped (section 0).

## 10. Battleship, registered 2026-11-21 11:30: a new app, its tests written with no build and no product to run on (before any run)

The owner, to section 9's proposal: "Yes, run Grokbot", and then: "Maybe we should start it with something more like
a game of Battleship first before Grokbot, because it might actually induce too much early complexity." So
Battleship first and Grokbot-local after it.

**Why this case.** It removes the first of section 9's two easy conditions and stays small: a new app (the work
folder starts empty), an HTTP API of two routes and a playable page. The request is the E2E harness's `battleship`
case, copied by script into the pilot's `cases.json` (658 characters, the same text).

**Cells** (Codex `gpt-6.2-sol` at high, as in rung 1; each run in its own repository under
`/Users/dadleet/e2e-runs/ratchet-parallel-20261121-6f54fb/`).

| Cell | Command | What it gives |
|---|---|---|
| `bs-loop` | `ratchet.py run --case battleship --enrich reworded --stop-after tests` | the specification, the plan, the build, and a test pass written beside the build, with its first gate |
| `bs-blind` | the same with `--tests-blind-from bs-loop`, started as soon as `bs-loop` has committed its plan | a test pass from the same specification and plan with no build present; the packet is rung 1's, unchanged |

Then, by script: the harness's four checks for the case on `bs-loop`'s build (`grade.py tree battleship`, new in
this commit: it runs each check as the harness's `run.py` runs one), and `overlay.py --history product --scratch`
laying each suite on that build.

**Readings.**

- **B1, first meeting.** Items of `bs-blind`'s suite passing on `bs-loop`'s build. Each failing item is read as
  one of: *execution* (how the product is started, configured or called), *assertion* (what the test expects is
  not what the request and the plan say), *product* (the build is wrong and the test is right). A Sonnet subagent
  reads them first; I check each label against the test and the build.
- **B2, the adapter.** Its share of the test lines, and whether anything outside it starts or configures the
  product.
- **B3, assumptions.** Each line of the writer's `## Assumed` list read as a design gap (a name or an answer the
  plan should have held) or as execution.
- **B4, with nothing to run on.** Runs of its own tests, and whether it wrote a stand-in for the product.
- **B5, beside it.** `bs-loop`'s own suite at its first gate, and both test sessions' minutes, output tokens and
  commands.
- **Tool check before any count is reported.** `overlay.py` must reproduce `bs-loop`'s own first-gate count for
  its own suite on its own build.

**Predictions** (mine have been wrong three times in this journal). With no product to run on, the build-less
suite fails more at first meeting than on due times: 3 to 8 items, nearly all execution (how the server is
started, the shape of the JSON beyond what the request fixes, the names of things on the page), at most one
assertion. The adapter's share rises above 30%. The writer lists more than four assumptions, and at least one is a
design gap about the page.

**Going on.** Grokbot-local follows at the owner's word, unless this run shows the instrument does not work on a
new app: a session that cannot proceed, or a build that fails the harness's checks, which would leave failures
unreadable. At the result I say whether there is enough to conclude early.

**Limits known in advance.** One cell a side. The build is graded by four checks, not by a yardstick calibrated
with planted defects, so "the build is right" is weaker here than on due times. The test sessions run at the same
time as each other and, for a while, as the build, on a machine other sessions also use: minutes are loose, and
this is not a registered reading of the parallel schedule, which stays stopped (section 0). The server's default
port is 3000; a test of the default may meet another process there, and a failure that names the port is rerun
alone.

**Apparatus in this commit.** `cases.json` gains `battleship` (no fixture: the work folder starts empty; the
project's own check is `node --test`, which the request names). `grade.py` gains the held-out kind `battleship`.
`ratchet.py` adds `battleship_game` to the marks a session's record must not hold. The loop's own no-model check
passes after the change (`selftest ok: 10 sessions, 6 gates, 14 snapshots`), and the new grader fails all four
checks on two archived ShipLoop work folders whose `main` is an empty baseline, as it should. A product that passes
it has not been shown yet: the run's build will be the first, and a build that fails is looked at by hand before it
is called wrong.

## 11. From records: how often ShipLoop changes a test after it is written, and why (2026-11-21 11:42; no delivery ran)

Status: interim. The counts are of what each run wrote in its own notes, read and labelled by a Sonnet subagent (at
the owner's standing word to use one where possible). I looked up nine of the quoted reasons and found each in the
note file it cites, and read three in context; I did not check the label of every row, and a run may have left a
change out of its notes.

The question, from sections 7 and 8: once tests are specified before the code, what still changes after it?

**What could be read.** ShipLoop commits a whole step at once, so Git cannot show a test edited inside the `test`
stage. The stage's own notes can: `<delivery>/.shiploop-runs/*/run/notes/<action>.md`, where the run writes each
test change's reason. Only deliveries from 2026-10-26 on have them. The 22 Battleship and Checkers deliveries of
early October first commit a test in the same commit as its code and keep no stage notes, so they say nothing
here. No earlier count exists in the SDLC journal, the spec-elaboration journal or `LEARNINGS.md` (searched first).

| Kind of case | Deliveries with readable notes | Recorded changes | Tests or assertions added | Execution | What a test asserts | Deliveries with an assertion change |
|---|---|---|---|---|---|---|
| new app with a page (Battleship, Checkers) | 6 of 8 | 21 | 7 | 6 | 8 | 3 of 8 |
| small change to an existing service (ticket cases) | 9 of 11 | 23 | 15 | 3 | 5 | 3 of 11 |

- **Most of what moves is strengthening or execution:** 31 of the 44 recorded changes. The additions follow a
  planted fault that survived or a new test that did not fail on the base.
- **An assertion does change after the code:** 13 times, in 6 of the 15 deliveries with notes. In the rows I read
  it was never because the product forced it; the value written before the code was wrong. "the test-spec text '17
  times' was a counting slip" (18 shots, after one miss, sink the fleet). "Asserting 83 would assert the walk's
  stop position instead of the rule." "I counted 16 calls in the sequence; the sequence has 15 ... my arithmetic
  error, not a product defect."
- **By model, as far as this sample can say, not by size.** All 13 are Sonnet 5.5 (7) or DeepSeek flash (6); none
  is in a delivery by Sol (5 with notes), Grok 4.6 (1) or Terra (2). The new apps show the higher share (8 of 21
  against 5 of 23), but the two groups were run by different models and on different ShipLoop versions, so size
  and model cannot be told apart here.
- **Git, the other instrument, shows almost nothing after a test file's first commit:** 4 later modifications in
  the 8 newer new-app deliveries (3 additions, 1 execution) and 16 in the 11 ticket deliveries (15 additions, 1
  execution). No base test file was modified in any ticket delivery.

**What it says about section 8's line.** It holds in ShipLoop's own deliveries, with one amendment. Execution does
move after the code (9 recorded changes). What a test asserts mostly does not, but it is not final either: a
concrete expected value written before any product exists is sometimes wrong by a slip of counting or arithmetic,
and the first run against the product is where that shows. ShipLoop's rule that such a change needs a recorded
reason is what made it countable.

Evidence: `evidence/parallel/shiploop-test-changes.md` (every row, with its note file and the run's reason) and,
in `evidence/parallel/shiploop-count/`, the deliveries taken and the rows as data.

## 12. Battleship, a reading added before it is taken (registered 2026-11-21 11:57)

Known when this is written: the build passes the harness's four checks, and the build-less suite passes 28 of 28
on it at first meeting (B1; the full result follows in the next section). Not known: anything about faults.

A suite can pass on a correct build by asserting little, and this one says it accepts several answers at the open
points and finds the page's controls by where they are drawn (its own list of assumptions). So one more reading,
registered now and taken by script with no model:

- **B6, strength.** `mutate.py --manifest` seeds the harness's own catalog of faults on the build's product source
  (the first 60 sites in its round-robin order; every line counts as changed, since the case starts empty) and runs
  each suite's commands on each fault. The same 60 faults go to the build-less suite, laid over the build in a
  scratch clone, and to the suite written beside the build, in its own work folder. Reading: faults caught of
  those valid, for each suite, and which faults only one of them catches.
- **Prediction.** The build-less suite catches fewer: 60 to 75% against 75 to 90%, with the difference at the open
  points and on the page.
- **Limits.** The catalog seeds faults in source files it can parse, so the page's inline script may get none. Its
  copies are made under a plain folder (`TMPDIR` set), for the reason given in section 6. The product's own tests
  are not measured: the tool runs `npm test` for them and this product has no package file.

## 13. Battleship, result (2026-11-21 12:16; runs 11:31 to 12:02, fault runs to 12:15)

Status: firm for what was run: one cell a side, one request, Sol 6.2 at high. No session's record holds a
held-out mark, and neither test session changed a product file.

**The loop.** `bs-loop`: specification 3.2 minutes (28 items: 4 use cases and 24 clauses, with 6 open lines), plan
3.5, build 8.0, test pass 15.1; 31.7 in all with the gates. The build is 5 files and 588 lines and passes the
harness's four checks. The new grader also passes two finished ShipLoop Battleship deliveries and fails an empty
tree, so it can tell the two apart.

**B1, first meeting: nothing to update.**

| Suite | Items | On the empty starting folder | On the build |
|---|---|---|---|
| `bs-blind`, written with no build and nothing to run on | 28 | 0 of 28 | 28 of 28 at first meeting, and again on a second run |
| `bs-loop`'s own, written beside the build | 28 | | 28 of 28 at its first gate |

- My prediction of 3 to 8 failing items was wrong. It is the fourth wrong prediction in this journal.
- Tool check: `overlay.py` reproduces `bs-loop`'s own first-gate count, 28 of 28.
- The page items are real. With the page's address for firing a shot broken by hand, the build-less U-2 fails:
  "Selecting a board square must submit a shot and receive its outcome."

**B6, strength: the same.** `mutate.py` found 51 fault sites in the build's source (`game.js` 24, `server.js` 27),
fewer than the 60 registered, so all 51 were seeded. None was invalid.

| Suite | Seeded faults caught, of 51 |
|---|---|
| written with no build | 32 (63%) |
| written beside the build | 31 (61%) |

- Fault by fault: 31 are caught by both and 19 by neither. One is caught only by the build-less suite (the upper
  bound on the port, which it tests at 65535). None is caught only by the suite written beside the build.
- My prediction that the build-less suite would catch fewer was wrong.
- The 19 that neither catches: 8 in how ships are placed and squares numbered, 11 in the server's conditions
  (request checks, the two routes, the port check, the body limit, two flags). Some cannot be told from the
  original from outside, such as a bound moved by one in a random placement. They were not examined one by one.
- The product's own tests are not measured: the tool runs `npm test` for them and this product has no package
  file.

**B2, the adapter.** `adapter.cjs` is 481 of the build-less suite's 1,430 lines (34%). With the listener
instrument, the reporter and the browser driver the execution side is 687 lines (48%), against about 30% on due
times. Nothing outside the adapter starts or configures the product. The suite written beside the build is 1,223
lines, with driving and asserting mixed in two of its files.

**B3, assumptions, and B4, nothing to run on.** A Sonnet subagent read the two session records and both suites
(`battleship/bs-session-activity.md`). I checked five of its claims against the files and they hold; I did not
check every row.

- The writer's three lines of assumptions hold four things. Two are execution: the browser driver (the Mac's own
  WebKit, compiled with Clang) and the hedges at two open points (zero-based coordinates tried first and one-based
  accepted; the `game` id field first and other shapes accepted). Two are design gaps, both where the plan fixes
  no name: the page's controls and wording (the plan says "100 labeled buttons" and a completion message, and
  gives no selector and no text), and what the rules module exposes (the plan names no export).
- The writer met both gaps by writing code that finds things (controls by where they are drawn, a board in any of
  several shapes). It did not have to wait for the code.
- It ran its tests three times and each run stopped at the first step, "no HTTP game became reachable" (66 times
  in its record). So most of its test code had never executed before it met the build. It built no stand-in
  product; it tried its own driver and instrument on two one-line throwaway files.
- One difference in kind: in three page items (C-7, C-10, C-11) the build-less suite answers the page's shots
  itself with forged replies, so those items test the page alone. The other suite's proxy passes real replies
  through.

**Tolerance** (the same reading). The build-less suite accepts more than one answer or shape in 17 places. The
suite written beside the build is as tolerant in 9 of them, more tolerant in 3 and less in 2; 2 are mixed; the
build-less suite is the looser in 1, a fallback it does not need on this build. Both packets carry the reworded
text's rule that a test must pass whichever reasonable answer a build took. The tolerance comes from that rule,
not from the missing build.

**B5, the sessions.**

| Test session | Minutes | Output tokens | Shell commands | Runs of its own tests | Product files read | Lines written |
|---|---|---|---|---|---|---|
| with no build | 16.5 | 45,571 | 22 | 3, none reaching a product | 0 | 1,430 |
| beside the build | 15.1 | 38,836 | 19 | 5, and once on 6 faulted copies of its own making | 4 | 1,223 |

The build-less session is again not cheaper: 9% longer, with 17% more output tokens.

**Predictions against results.** Failing items at first meeting: predicted 3 to 8, found 0. Adapter above 30%:
right (34%, and 48% for the whole execution side). More than four assumptions with a design gap about the page:
four, two of them design gaps, one about the page. Strength: predicted 60 to 75% against 75 to 90%; found 63%
against 61%.

**What it says.**

1. For a small new app with a page, tests written from the specification and the plan needed no update when the
   build arrived, and caught as many seeded faults as tests written beside the build. With due times that makes
   three cells of three with nothing to catch up, and this one had no product to run on at all.
2. Section 8's line holds here in a sharper form. Where the plan fixed a name, the tests used it. Where it did not
   (the page's controls, the module's interface), the writer did not wait for the code: it wrote code that finds
   the thing. That is where the larger execution side went.
3. So "how tests execute gets specific after the code" was not needed on this app. It was paid for in advance, in
   lines and in a longer session.
4. Both suites miss the same 19 faults. That is a fact about tests written under the reworded text's rule against
   a randomly placed fleet, not about writing them early.

**Limits.** One cell a side and one model family. The app is small. The build was right the first time, so
nothing here says how a build-less suite meets a wrong build, beyond the seeded faults. Seeded faults are
single-token edits, a different yardstick from the pilot's calibrated defects. The tolerance and activity readings
are a subagent's, spot-checked.

**Is there enough to conclude early?** On whether tests can be written before the code without being updated and
at no loss of strength: yes for small cases, three of three. Not for size. Grokbot-local has four times the
clauses and a far richer page, and is where this is most likely to break. It runs next, at the owner's word.

Evidence: `evidence/parallel/battleship/` (each run's record, reports and manifest; the build-less adapter and
packet; the held-out result; `overlay-battleship.json`; `mutate-bs-blind.json` and `mutate-bs-loop.json`;
`bs-session-activity.md`).

## 14. Grokbot-local, registered 2026-11-21 12:18: the large app with a page, both test passes from the plan and build on file (before any run)

The owner approved Grokbot-local before asking for Battleship first (section 10). Battleship showed the instrument
works on a new app (section 13), so by that section's rule this runs next. It is the case where "nothing to
update" is most likely to break: 115 items against 28, a loosely worded request, and a page with chat, tasks,
records and a workspace.

**What is reused, so only the two test sessions are paid for.** The parent session's `p3R-grokbot-local` run
(read, not changed): its specification with the reworded text (100 clauses and 15 use cases, 18 open lines), its
plan, and its first build, which passes both held-out yardsticks (49 of 49; 28 of 28, of which 23 stated and 5
implied; the parent's grading log). The build is 20 product files and 2,155 lines of code outside its tests.

**Cells** (Codex `gpt-6.2-sol` at high; each in its own repository under the fork's runs folder).

| Cell | Command | What it gives |
|---|---|---|
| `gb-blind` | `ratchet.py run --case grokbot-local --enrich reworded --tests-blind-from p3R-grokbot-local --stop-after tests` | the test pass from the specification and plan with no build present; the packet is rung 1's, unchanged. The starting folder holds the case's 8 files (a stand-in provider and records), no app |
| `gb-beside` | the same with `--plan-from p3R-grokbot-local --build-from <that run's first build, exported>` in place of `--tests-blind-from` | the standing test pass, written beside that build, with its first gate |

**Apparatus in this commit.** `ratchet.py` gains `--plan-from RUN`: the specification and plan as after RUN's plan
stage with no session, then the given build laid by the script (`--build-from`), then the standing test pass. No
packet text changes. Checked with no model: the loop's own check passes (`selftest ok: 10 sessions, 6 gates, 14
snapshots`), and a scripted run with the new option makes the commits base, plan-1, build-1, tests-1, final with
one session, the test pass, and is refused without `--build-from`.

**Readings**, as for Battleship.

- **G1, first meeting.** Items of `gb-blind`'s suite passing on the build. Each failing item read as execution,
  assertion or product (a Sonnet subagent first; I check each label).
- **G2, the execution side.** Its share of the test lines; whether anything outside the adapter starts or
  configures the product.
- **G3, assumptions.** Each read as design gap or execution.
- **G4, with nothing to run on.** What the writer ran its tests against.
- **G5, beside it.** `gb-beside`'s suite at its first gate; both sessions' minutes, tokens and commands.
- **G6, strength.** `mutate.py --manifest` with the first 60 fault sites of the build's source, the same faults to
  both suites. If one pass of a suite takes too long for 60, the sample is cut to 30 for both and that is said.
- **Tool check first.** `overlay.py` must reproduce `gb-beside`'s own first-gate count.

**Predictions.** Four of mine have been wrong, each time by expecting failures, so this one follows the three
cells seen: 0 to 5 of the build-less items fail at first meeting, on the page if anywhere; the two suites catch
seeded faults within 10 points of each other; the build-less execution side is above half its lines; its session
is the longer one.

**Going on.** After this I say whether there is enough to conclude. Chess is not planned unless what tests assert
is still in doubt.

**Limits known in advance.** One cell a side, one model family. The build was right the first time. The test
sessions find their own way to a browser on this machine. A session ends at 45 minutes whatever it has done. The
machine is shared (the load was 20 a few minutes before launch), so minutes are loose.

## 15. Grokbot-local, first meeting, and a reading added before it is taken (2026-11-21 13:14)

**G1, as measured: 4 of 115.** The build-less suite passes C-1 to C-4 on the build and fails the other 111, on its
first and only run there (30.4 minutes for the pass; no item unstable). The suite written beside the build passes
115 of 115 at its first gate. My prediction of 0 to 5 failing items was wrong, in the other direction this time.

**One cause, read by hand.** Every failing item stops at its first step with the same message: `Activate
{"kind":"button","name":"Continue as Maya"} (last observation: [])`. The page is there and so is the button (a
probe through the suite's own adapter shows the title, the three entry buttons, all visible). The specification
asks for buttons named `Continue as Maya` (C-9) and the build has them: `public/app.js` puts an avatar letter and
an arrow inside each button and marks both `aria-hidden`, so the button's accessible name is as specified. The
build-less adapter works out an element's name itself (`name()` in its `adapter.cjs`) and falls back to the
element's whole text, hidden parts included: it reads "MContinue as Maya→" and finds no button of the name it
wants. The suite written beside the build asks the browser for its own accessibility tree and gets the right name.

So the 111 failures are *execution*, by section 10's three kinds: how a test finds a thing on the page. No
assertion is wrong and the product is right. It is the owner's case exactly (section 8): how a test executes had to
become more specific once the code existed, and here the writer, with nothing to try its page code on, got one
piece of it wrong for every test that opens the page.

**A reading added now, before it is taken (G7, the size of the catch-up).** In a scratch copy, and by my hand, not
a session's, that one function is changed to leave out `aria-hidden` descendants when it reads an element's text.
All 115 commands are then run once on the build. Reading: how many pass; each item still failing is read as
execution, assertion or product; and how many further corrections it takes, if I make any, each one named. This
is a what-if, not a measured catch-up session: it says how much of the suite one correction unlocks and what lies
behind it, and nothing about how long a session would take to find it. I found it in about eight minutes from the
failing output, with one probe.

**G6 is not taken as registered.** With 4 of 115 commands passing on the untouched build there is nothing for
seeded faults to be caught by; and one pass of this suite takes half an hour, so even 30 faults would take hours.
If the corrected copy passes most items, a small fault sample against it is a possible later reading, labelled as
on a corrected suite.

**Prediction for G7.** After the one correction most items pass, and between 5 and 20 still fail on further
execution details the writer could not try (how it clicks, the page's `fetch` being hooked, the two numbers it
made up for "narrow" and "tiny").

**G7, first number (13:19).** With the one function corrected by hand, 73 of 115 items pass on the build (one pass,
three at a time, 13:15 to 13:18). The 42 that still fail fall into a few families by their messages: 15 cannot see
a new assistant reply in the transcript; about 17 wait for a task to show finished steps or reach Completed or
Failed; 5 cannot find a named thing or some text; and five single ones (a held view response, a background
refresh, the provider's execution, an alternate conversation, visible keyboard focus). They ran three at a time on
a busy machine, so some may be the load's and not the suite's.

**A second reading added before it is taken (G7b, a catch-up under the rule of section 3).** A Sonnet subagent
works in a further scratch copy with one rule: it may change only the execution files (`acceptance/adapter.cjs`,
`acceptance/webkit.swift`), never `acceptance/suite.cjs`, which holds what the tests expect, and never the
product. It reruns each failing item alone, finds each cause, corrects those that are execution, and lists the
items that would need an assertion changed or that show a fault in the build, with its evidence. It stops when no
execution cause is left or after 40 minutes. I read its changes and make the final count myself with a full pass.
This is a model catching a suite up, on Sonnet and outside the loop's packets, so it sizes the work and is not a
measured Ratchet stage. Prediction: it reaches 100 or more of 115 with five or fewer further corrections, and a
handful of items remain that need an assertion changed.

## 16. Grokbot-local, result (2026-11-21 13:51; test sessions 12:18 to 12:41, first meeting to 13:12, catch-up to 13:50)

Status: firm for what was run: one cell a side, one request, Sol 6.2 at high for the two test sessions. The
catch-up is by my hand and a Sonnet subagent's, outside the loop: it sizes the work and is not a measured stage.

**G1, first meeting: 4 of 115, from one cause; and what it took to catch up.**

| State of the build-less suite | Items passing on the build, of 115 |
|---|---|
| as written, first run on the build | 4 |
| with correction 1: an element's name leaves out `aria-hidden` descendants | 87 |
| with correction 2: an action waits until the page has answered it | 111 |
| with correction 3: the driver's window counts as focused | 112 |
| the suite written beside the build, at its first gate | 115 |

- The 87 is 73 in my pass run three at a time on a busy machine plus 14 that the subagent found pass when run
  alone, before it changed anything. The 112 is my own count from a full pass run one at a time (13:43 to 13:50),
  and it agrees with the subagent's.
- All three corrections are in the two execution files (`adapter.cjs`, `webkit.swift`): 23, 97 and 37 lines of
  diff. `suite.cjs`, which holds what the tests expect, and the product are unchanged; I read each change and none
  makes a test pass without observing the product.
- **Correction 1** (mine; about 8 minutes from the failing output, with one probe). Section 15.
- **Correction 2** (the subagent's, about 9 minutes). The page's `command()` returns at once while it is busy and
  its `render()` resets the message box when the open chat changes, so a test that typed straight after a click
  lost its first message. The adapter now counts the page's own requests in flight and waits, after a click or a
  key, until they are answered and the document is still. It unlocked 24 items, the whole "no new assistant reply"
  family and the task and find families behind it.
- **Correction 3** (the subagent's, about 8 minutes with two dead ends). The driver is a background application and
  its window was never the focused one, so visible keyboard focus could not be observed. The window now reports
  itself focused. It unlocked C-99.

**The three that remain are the tests' own expectations** (the subagent's reading; I checked each against the suite
and the specification and agree). No fault in the build was found, and it passes both held-out yardsticks.

| Item | What the test expects | Why that is the test's mistake |
|---|---|---|
| U-4 | a reply named `Message from Assistant` after opening a bot called Planning | the specification names a reply `Message from <bot name>` |
| C-77 | the applied one of two conversations that hold the same text, by opening the first that matches | the specification gives no order for the list; the build lists oldest first |
| C-75 | two windows of one person each confirm an order at once and both succeed | the specification only says successful overlapping creations never share an ID; the build keeps one open conversation a person and refuses the other window |

**So, of 111 items failing at first meeting: 108 were execution, 3 were assertion, none was the product.**

**G5, the sessions** (a Sonnet subagent's count from the records, `grokbot/gb-session-activity.md`; six of its
claims checked against the files).

| Test session | Minutes | Output tokens | Shell commands | Runs of its own suite | Product files read | Lines written |
|---|---|---|---|---|---|---|
| with no build | 21.8 | 60,959 | 35 | 4, none reaching an app | 0 | 2,725 |
| beside the build | 21.6 | 59,531 | 37 | 12, of which 6 showed a failure it then cleared | 5 | 2,887 |

- The session beside the build met its own execution faults while it wrote, six runs' worth, and cleared them
  inside its 21.6 minutes. The build-less session could not meet any: each of its items has one path for the empty
  folder and one for a delivered app, and only the first had ever run.
- One pass of the uncorrected suite on the build took 30.4 minutes, because every failing item waits out its
  time limits. A pass of the corrected suite takes 7.

**G2, the execution side.** 820 of the build-less suite's 2,725 lines (30%), with nothing outside the adapter
starting or configuring the product. The suite written beside the build has 555 of 2,887 (19%) and finds every
element through the browser's own accessibility tree, by role and name.

**G3, assumptions.** Six lines. Two are design gaps: two numbers the specification does not give (540 pixels for
a narrow window, 10 for tiny text; the plan says to avoid a breakpoint) and the page's requests going through
`fetch`. Neither failed an item on this build. Four are execution. The three faults that did fail items are in none
of the six: the writer did not know it was assuming them.

**Names.** Both suites use the same 46 labels and all 46 are in the specification. The suite written beside the
build takes at most 2 weak names from the build. So the design did fix the names a test touches; what was missing
was not a name.

**G6, strength: not taken**, for the reason given in section 15.

**Tolerance** (the subagent's reading). The two suites differ in 28 places: equal in 5, the build-less one looser
in 7 (mostly a check left out), stricter in 6, mixed in 10.

**The held-out mark.** The session beside the build has `skill-craft` once in its record: the name of the run's
own temporary folder, `.skill-craft-e2e`, in a directory listing. Nothing of the repository was read.

**Predictions against results.** Failing items at first meeting: predicted 0 to 5, found 111. After one
correction: predicted most passing with 5 to 20 left; 28 were left. The catch-up: predicted 100 or more of 115
with five or fewer further corrections and a handful needing an assertion changed; found 112 with two, and three.

**What it says.**

1. Size is where it breaks, and it is the page that does it. Three small cells needed no catch-up (sections 6 and
   13). On a rich page 111 of 115 items needed one.
2. The owner's line (section 8) is confirmed and sharpened. What the tests assert held: 112 of 115 expectations
   were right as written before any code, and the 3 that were not are slips of the kind ShipLoop's own deliveries
   record (section 11). How the tests execute did not hold: 108 items fell to three faults in the page-driving
   code.
3. The design was not what was missing. The specification gave every label, and the writer's own list of
   assumptions names none of the three faults. What was missing was a page to try the driving code on: how names
   are read, how actions are paced to the page's answers, whether the window has focus. A design can fix what a
   test asserts and the names it uses; it cannot stand in for running the code that drives a page.
4. Keeping execution in one place is what made the catch-up small to write: three diffs in two files brought back
   108 items, and nothing a test expects had to be touched for them.
5. For the schedule of section 3, which stays stopped: on this case the build takes 15.0 minutes, the most that
   writing tests beside it could save. The catch-up took about half an hour of work (8 minutes of mine, 23 of the
   subagent's) after a 30-minute failing pass. Where the build is long enough to be worth overlapping, the
   catch-up costs more than the overlap saves.

**Limits.** One cell a side, one model family for the test sessions. The catch-up was done by me and by a Sonnet
subagent under an adapter-only rule, not by a session of the loop, so its minutes are a size and not a rate. The
subagent's three assertion readings were checked by me by reading, and its one throwaway change to each test was
not rerun by me. Strength was not measured here. Every cell so far built a product that was right the first time.

**Is there enough to conclude?** Yes, on the question as the owner put it. Tests can be specified before the code
and what they assert survives it, small or large. The code that executes them can be written before the code for a
small app or a change to one, with nothing to update; for an app with a rich page it has to be finished, or at
least tried, against a real page. That is the order ShipLoop already keeps (section 8). Not settled, and offered,
not run: whether an existing page is enough for the writer to try its driving code on, which a change to an
existing app with a page would show (the harness has `battleship-scoring`, which follows `battleship`).

Evidence: `evidence/parallel/grokbot/` (each run's record, report and manifest; the build-less adapter, driver and
packet; `overlay-gb-blind.json`; `gb-session-activity.md`; and under `catch-up/` the three corrections as diffs,
the subagent's report, and the pass counts).
