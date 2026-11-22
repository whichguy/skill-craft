# Ratchet against ShipLoop: a head-to-head on the same cases (journal)

Apparatus: `docs/experiments/ratchet-vs-shiploop-20261121/`. Earlier work this builds on: `docs/ratchet-pilot-journal.md`
(the Ratchet pilot, 2026-11-20 and 21) and `docs/ratchet-parallel-journal.md`.

## 0. Where it stands

Registered 2026-11-21 23:55 (commit d522655ae4f6a8af0b289d346aa08cf44d2e9fbe), before any run; all eight runs started at 23:59. Results go in section 7.

## 1. The question, in the owner's words (2026-11-21, late evening)

> I would like to know if ratchet or shiploop produce better results. Create a test harness to run each separately in
> their own clean repo from scratch against some of the test cases then examine the results from time, tokens,
> breadth, depth and quality of code , and test coverage and documentation coverage

## 2. What the records already say (read before designing)

From `docs/ratchet-pilot-journal.md` (sections 0, 10, 17; runs under `~/e2e-runs/ratchet-pilot-20261120-b6eab2/`):

- Time and tokens, one matched cell (ticket assignment, Sol 6.2 medium): Ratchet 91.8 minutes and 177,302 output
  tokens against ShipLoop's 13.2 minutes and 29,066. Grokbot-local at high: ShipLoop 39.5 minutes, Ratchet 207.7
  minutes and 392,253 output tokens (Ratchet stopped by its three-cycle limit, still adding requirements).
- Held-out checks: no headroom. Five of six Ratchet first builds passed every held-out check; on Grokbot-local one
  bare session, ShipLoop and Ratchet's first build all pass both browser yardsticks (49 and 28 checks).
- Depth of tests, one measure: 60 seeded faults against each Grokbot build's own tests, ShipLoop 37, bare sessions 24
  to 31, the Ratchet builder 23 (F22).
- Spread: the same text gives 24 to 26 of 27 calibrated defects caught over three runs (F38), so a difference of two
  between single runs is nothing.
- Those ShipLoop records are of ShipLoop 2.3.0 and 2.4.0. Today's ShipLoop is 2.4.1 (and later commits, if any, on
  `main`): the earlier numbers are background, not evidence about today's ShipLoop (owner's rule, "always the absolute
  latest ShipLoop").

Never measured: code quality, test coverage, documentation coverage, and any of these on today's ShipLoop.

## 3. Design

**Arms.** One run of each arm on each case. Both run on Codex `gpt-6.2-sol` (the newest Sol in the Codex catalog on
2026-11-22) at `medium` effort, the owner's current setting for harness tests.

| Arm | What runs |
|---|---|
| ShipLoop | the newest ShipLoop on `main`, through the E2E harness: `test/shiploop_e2e/run.py --source checkout --case C --host codex --model gpt-6.2-sol --effort medium` |
| Ratchet | the pilot's loop with its best specification text: `docs/experiments/ratchet-pilot-20261120/ratchet.py run --case C --host codex --model gpt-6.2-sol --effort medium --enrich reworded`, its other settings at their defaults (at most 3 cycles and 4 fix sessions a cycle) |

**Clean repositories.** Each run gets a new folder under one runs root outside this checkout, and its own tool makes
a new Git repository in it: the harness copies the case's starting files into an empty `work/` and commits them;
`ratchet.py` does the same. Nothing is shared between runs. Both arms run from one detached checkout of this
repository made by `launch.py checkout`, so the ShipLoop source and the Ratchet apparatus are the same commit; that
checkout adds one commit of its own, which puts the two cases the harness lacks into its `cases.json` (the request
word for word, the same starting files, the case's own commands as the harness's verdict checks). No file under
`skills/` differs from `main`.

**Cases** (the requests are the E2E harness's own, copied into the pilot's `cases.json`):

| Case | Kind | Starts from | Held-out checks (no session sees them) |
|---|---|---|---|
| `shared-expenses` | new service | an empty folder | the harness's expense-service checks (`grade.py`, kind `expenses`) |
| `node-chess-engine` | new library | `package.json` and `.gitignore` | 10 chess checks (kind `chess`) |
| `ticket-assignment` | change to an existing service | the node-tickets service (about 1,700 lines) | 18 acceptance checks (kind `ticket-assignment`), and 27 calibrated defects with a correct reference |
| `grokbot-local` | new app with a page | a model stand-in and seven records | two browser yardsticks, 49 and 28 checks (kinds `grokbot`, `grokbot2`) |

Why these: two new builds of different shape, a change to an existing product, and the largest request on file (the
case most likely to separate the arms, per the cheapest-instrument rule: run the case most likely to break a result).

**Order.** All eight runs start together. Each is checked once it is about ten minutes in: a ShipLoop run must be
past intake, a Ratchet run must have written its specification. A run that fails to start for a reason of the
apparatus is fixed and started again; a run that fails for a reason of the arm is a result.

## 4. Measures (all by script except one judge reading; nothing is shown to any session)

The final product of a run is its `work/` repository at the end: ShipLoop's delivered head; Ratchet's last commit.
For Ratchet the product at its first build is measured too, so its time and its result can be read at either point.
Where a measure concerns the product, each arm's process folders are left out: `docs/shiploop/` (ShipLoop's
specification, plan and architecture notes), `ratchet/` and `acceptance/` (Ratchet's specification and acceptance
suite). Where a measure concerns tests, it is taken twice: with the product's own test command (the case's command,
the same for both arms: `node --test` for shared expenses, `npm test` otherwise), and with every suite the arm left
(for Ratchet, its acceptance suite as well).

- **M1 time:** minutes of the arm's whole run. ShipLoop: the host process's elapsed seconds (the harness's grading
  after the host ends is not counted). Ratchet: `run.json` seconds; also minutes to its first build.
- **M2 tokens:** from the Codex rollout files of every session in the run's home folder (the last
  `total_token_usage` of each): input, of it cached, output, of it reasoning.
- **M3 breadth, how much of the request was delivered:** held-out checks passed on the final product, graded by
  `grade.py tree` with the same graders for both arms.
- **M4 depth, how hard the product's tests are to fool:** (a) 60 seeded faults from the E2E harness's catalog
  (flipped comparisons, moved bounds, flipped logic and arithmetic) on the product lines the delivery added or
  changed, run against the product's own tests (`mutate.py`; with Ratchet's acceptance suite as well, `--manifest`);
  share caught. (b) Ticket assignment only: the 27 calibrated defects caught by the delivery's tests (`baseline.py`).
  Also reported: the number of tests the own suite runs.
- **M5 test coverage:** line and function coverage of the product's JavaScript source by its tests, from the V8
  coverage of every Node process the tests start (servers the tests spawn included; a preload writes a process's
  coverage when it is stopped by SIGTERM or SIGINT). A source file no test loads counts with all its lines uncovered.
  Branch coverage is reported, not read.
- **M6 documentation coverage:** (a) of the product's public surfaces found in its source by script (environment
  variables it reads, HTTP paths it serves, npm scripts, command-line flags, names its modules export), the share
  named in its user documents (Markdown outside test folders and the process folders); taken again with the process
  folders' documents included. (b) The share of the product's named functions with a comment directly above them.
  (c) Words of user documents.
- **M7 code quality:** (a) by script, reported and not read: source lines, functions, longest function, share of
  functions over 50 lines, cyclomatic complexity per function (mean, max, share over 10), share of repeated 6-line
  windows, `node --check` failures. (b) One blind judge, the latest Opus: both final products of a case side by
  side (product source and tests; process folders removed; arm names, run folders and tool names masked), labelled X
  and Y by a seeded coin, read twice with the order swapped, scoring five criteria from 1 to 5 (correctness risk,
  structure, readability, error handling, tests) and naming the better product.

The instruments for M5 and M6 are new. They are checked on archived deliveries of both arms (no model) before any
new run is measured; after the first new run is measured they do not change, and a fault found later is recorded as
a correction with every number it moves.

### Instrument checks, 2026-11-22 00:00 to 00:40 (before any new run was measured; the first ShipLoop run had ended)

On a toy product (`scratchpad`, a module with a called and an uncalled function, a server the test spawns and stops
with SIGTERM) and on five archived deliveries under `~/e2e-runs/ratchet-pilot-20261120-b6eab2/` (Ratchet: chess,
ticket assignment at medium, shared expenses, Grokbot; ShipLoop 2.3.0: Grokbot). What changed, and why:

- **Coverage of a stopped server.** `v8.takeCoverage()` followed at once by raising the signal again lost the
  server's coverage file in 4 of 8 toy runs; waiting 100 ms before raising it lost none in 8 (and 3 of 3 through
  `coverage.py`). The preload waits 100 ms. On the toy, `coverage.py` and Node's own `--experimental-test-coverage`
  name the same unrun lines (7 and 11 to 14 of the module); Node counts comment and blank lines as run, so its
  percentage is higher (68.75 against 58.3). On the archived Ratchet chess delivery both give 100% of lines and
  functions.
- **Code a browser runs.** On the archived Grokbot delivery, `public/app.js` (592 lines, the page's script) is never
  loaded by Node; no Node coverage can see it, whichever arm wrote it. So R5 reads coverage over the files Node can
  run: files under a folder named public, static, client, www, assets, frontend, web or browser are left out of the
  reading (`measure.py`, `browser_free`) and reported apart.
- **Which lines.** On the ticket change, coverage of the whole product is mostly the existing service's tests. R5
  reads the `changed` scope: the lines and functions the delivery added or changed (for a new build, all of its
  source; a starting file the delivery did not touch, such as Grokbot's model stand-in, is left out).
- **Which surfaces.** Likewise R6 reads the surfaces that are new in the product (for a new build, all of them).
  Two kinds were missed and are now read: settings code that is handed `process.env` and reads `env.PORT` (both
  archived Grokbot deliveries; now names given `process.env` and names `env` or `environment` count), and query
  parameters (`params.get('status')`, `searchParams.has('assignee')`; the ticket change's new `assignee` filter).
  After these, the archived ticket delivery has 2 new surfaces (`/tickets/:p/assignee`, `assignee`), the chess
  delivery 5 (its exports), shared expenses 4, Grokbot 8 (Ratchet) and 6 (ShipLoop).
- **Seeded faults on a product tested with `node --test`.** `mutate.py` ran `npm test` only; it gains
  `--own-command` (default unchanged), because a shared-expenses delivery need not have a `package.json`.

Known limits of the readers, kept: the JavaScript reading is a lexer, not a parser (a function written in an unusual
form may be missed); a route built from pieces at run time is not seen; JSON body fields are not surfaces.

## 5. Readings, registered before any run

Per case and measure, one arm is **ahead** only by these margins; otherwise **no difference shown**:

| Reading | Ahead when |
|---|---|
| R1 time | its minutes are at most two thirds of the other's |
| R2 tokens | its output tokens and its input tokens are both at most two thirds of the other's |
| R3 breadth | it passes at least max(2, 10% of the case's checks) more held-out checks (Grokbot: the two yardsticks summed) |
| R4 depth | (a) at least 10 points more seeded faults caught by the own tests; (b) ticket assignment, at least 3 more calibrated defects |
| R5 coverage | at least 10 points more line coverage by the own tests |
| R6 documentation | at least 15 points more surface coverage by the user documents |
| R7 code quality | the judge names it the better product in both orders |

**Overall:** the quality cells are R3 to R7 (R4 counts once: (a), or (b) where they disagree in direction, then no
difference). Over the four cases an arm **produces better results** if it is ahead in at least three more quality
cells than the other and behind on breadth (R3) in no case: a product that does less of the request is not better
whatever its tests. Otherwise: **no difference in results shown**. R1 and R2 are the cost of each, reported apart.

**Predictions, to be scored, not used to decide anything:** P1 ShipLoop ahead on time in 4 of 4 cases; P2 ShipLoop
ahead on tokens in 4 of 4; P3 breadth no difference shown in at least 3 cases; P4 ShipLoop ahead on depth (a) in at
least 2 cases; P5 coverage no difference shown in at least 3; P6 documentation no difference shown in at least 3; P7
the judge's preference split or absent in at least 3; P8 overall no difference in results shown.

## 6. Limits known before the runs

- One run per arm and case: a difference inside the margins above is within the spread seen before (F38).
- One model at one effort; the requests are the harness's, and three of the four were solved by every arm before.
- Codex shows the account's own user-level skills (`~/.codex/skills`, `~/.agents/skills`; none of them ShipLoop) to
  every session of both arms, whatever its home folder (see the memory note on the Codex harness): the same condition
  for both arms.
- ShipLoop also reviews and releases as ShipLoop does; Ratchet stops at a product. Ratchet's three-cycle limit is the
  pilot's, and every earlier whole loop met it; a run it ends is reported as stopped at that limit.
- The machine is shared with other sessions' runs (other sessions' ShipLoop runs of both ticket cases were live at 23:50); the
  harness's port leases keep ShipLoop runs of one case apart, and a held-out check that does not end is run again.
- A background task of this host has been seen to end at about two hours; a ShipLoop run resumes in place
  (`launch.py resume`), a Ratchet run cannot and would be reported as stopped.
- The documentation and coverage measures are mine and new; section 4 says how they are checked before use.
