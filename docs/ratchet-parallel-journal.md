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
