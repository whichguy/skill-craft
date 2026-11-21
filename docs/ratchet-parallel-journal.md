# Ratchet in parallel, with catch-up: journal

A side line of the Ratchet pilot (`docs/ratchet-pilot-journal.md`), kept in its own file because the pilot's journal
is being written by another session on another branch. This session is a fork of that conversation, made by the
owner at 08:00 on 2026-11-21 to think about one question. It writes only in its own worktree and reads the pilot's
runs without changing them.

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
