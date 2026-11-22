# Ratchet against ShipLoop: a head-to-head on the same cases (journal)

Apparatus: `docs/experiments/ratchet-vs-shiploop-20261121/`. Earlier work this builds on: `docs/ratchet-pilot-journal.md`
(the Ratchet pilot, 2026-11-20 and 21) and `docs/ratchet-parallel-journal.md`.

## 0. Where it stands

**As of 2026-11-22 10:20, after three rounds** (the first script measures on eight clean runs, sections 3 to 7; a
deeper judge that runs every product and checks it item by item, sections 10 to 12; one look and one fix on
ShipLoop's deliveries, first as repairs and then from clean runs, sections 11 and 13 to 15):

- **Nothing a request states was left unbuilt by either tool**, on any of 12 products last night and 12 audited
  today.
- **ShipLoop alone delivers in 15% to 31% of Ratchet's time and tells the customer less.** On two runs and two
  ShipLoop versions (2.4.1, 2.6.0) it shipped no user page on the new service and no release record on the ticket
  change. On three small cases that is the whole difference from Ratchet's final.
- **On the large stateful case (Grokbot) Ratchet builds the better feature**, already at its first build, which
  costs what ShipLoop's delivery costs: medium defects 6 against 2 against 1 (ShipLoop, Ratchet's first build,
  Ratchet's final) last night, 8 against 3 on today's fresh ShipLoop run and re-audit.
- **From clean runs, ShipLoop followed by one look (the builder's model, 2 to 8 minutes) and one fix (Opus at
  xhigh) is level with Ratchet's final on shared expenses and tickets and ahead on chess, at 28% to 44% of Ratchet's
  time.** On Grokbot the same sequence takes 38% of the time and closes about half the gap: Ratchet's final is still
  the better feature there (medium defects 5 against 3, unsaid points handled 34 against 38 of 39).
- **Limits that matter:** Ratchet's side is one run a case; the fixer is a stronger model than either builder; one
  audit a product, and a look and an audit each find things the other does not, so every defect count is a floor.

The first round's registered result stands as recorded in section 7 ("no difference in results shown; ShipLoop
costs 15% to 31% of Ratchet's time"); sections 12 and 15 say where that verdict was too coarse.

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

Two scope notes made during the measuring, each before the run it touches was measured:

- 00:40. At a Ratchet first build there is no acceptance suite yet, so its seeded faults run against the own tests
  alone (the first attempt with `--manifest` stopped on the missing `ratchet/acceptance.json`; no number was lost).
- 01:45. For Grokbot, Ratchet's acceptance suite is about 300 browser commands; `mutate.py --manifest` runs every one
  of them for a fault that survives, so 60 faults would take many hours. Grokbot's seeded faults run against the own
  tests only, as R4(a) reads and as the pilot measured Grokbot (F22). Coverage with every suite is still taken.

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

## 7. Results (all eight runs ended 2026-11-22 02:41; measured and judged by 03:05)

Runs root `~/e2e-runs/d20261122-360a9f/` (label `-1` ShipLoop, `-2` Ratchet); one checkout for both arms,
`source-d522655ae4f6` (ShipLoop 2.4.1, plugin 4.2.1). Every run ended by itself: no resume, no restart, no apparatus
failure. Every ShipLoop run passed its harness verdict; every Ratchet run stopped at its three-cycle limit with its
gate passing (as every whole loop of the pilot did). No run left a process behind. Evidence:
`docs/experiments/ratchet-vs-shiploop-20261121/evidence/` (each run's measure record, the judge's answers, the report).

### Cost (M1, M2)

| Case | ShipLoop minutes | Ratchet minutes (first build) | Ratchet ÷ ShipLoop | Output tokens, ShipLoop / Ratchet | Uncached input, ShipLoop / Ratchet | Total input, ShipLoop / Ratchet |
|---|---|---|---|---|---|---|
| shared expenses | 14.3 | 46.4 (10.2) | 3.2× | 27,535 / 111,434 | 148k / 770k | 10.7M / 8.1M |
| chess engine | 10.4 | 37.2 (8.5) | 3.6× | 21,313 / 87,564 | 130k / 718k | 6.0M / 6.5M |
| ticket assignment | 15.3 | 100.4 (11.1) | 6.6× | 30,077 / 132,054 | 202k / 908k | 11.8M / 12.4M |
| Grokbot-local | 26.5 | 162.3 (20.0) | 6.1× | 52,934 / 234,368 | 190k / 1,246k | 18.6M / 31.4M |

ShipLoop ran each case as one Codex session (one rollout); Ratchet as 13 or 14 sessions. ShipLoop writes about a
quarter of Ratchet's output tokens and a sixth of its uncached input. Its total input is close to Ratchet's, or
higher (shared expenses), because one long session re-reads its whole cached context on every call.

Ratchet's first build was ready at 8.5 to 20.0 minutes, near ShipLoop's whole delivery (10.4 to 26.5), and it
already passed every held-out check it passed at the end (next table). Its cycles after that took 28.7 to 142.3
minutes, and its specifications ended at 49 to 98 clauses; the ticket case's third build alone ran 45.8 minutes.

### Results (M3 to M7)

| Case | Arm | Held-out checks | Seeded faults caught by own tests | Line coverage, changed lines Node runs | New surfaces named in user documents | Tests the own command runs |
|---|---|---|---|---|---|---|
| shared expenses | ShipLoop | 6 of 6 | 49 of 60 (82%) | 95% | 0 of 3 (no README) | 5 |
| | Ratchet | 6 of 6 (first build 6) | 31 of 59 (53%) | 93% | 4 of 4 | 13 |
| chess engine | ShipLoop | 10 of 10 | 47 of 60 (80%; 1 did not end) | 99% | 0 of 5 (no README) | 8 |
| | Ratchet | 10 of 10 (first build 10) | 50 of 60 (83%) | 98% | 5 of 5 | 16 |
| ticket assignment | ShipLoop | 18 of 18 | 9 of 9 (100%; its change has 9 sites) | 95% | 2 of 2 | 123 (117 the service's own) |
| | Ratchet | 18 of 18 (first build 18) | 24 of 25 (96%; 2 did not end) | 100% | 2 of 2 | 134 |
| Grokbot-local | ShipLoop | 49 of 49 and 28 of 28 | 27 of 60 (45%) | 94% | 3 of 6 | 8 |
| | Ratchet | 49 of 49 and 28 of 28 (first build the same) | 32 of 60 (53%) | 97% (first build 95%) | 3 of 8 | 19 |

- **Breadth is at the ceiling again.** Every final product passes every held-out check, and so does every Ratchet
  first build: the cycles after Ratchet's first build moved no held-out check, as in the pilot (section 2).
- **Depth.** Seeded faults separate the arms on shared expenses only (ShipLoop 82% against 53%). On ticket
  assignment's 27 calibrated defects Ratchet's tests catch 19 (18 at its first build) and ShipLoop's 7; 5 of
  ShipLoop's 6 new test cases fail on the correct reference (a second correct product), so they can catch nothing
  there, and 11 of Ratchet's tests do too. R4 as registered reads the seeded faults, so this is reported apart (R4b).
- **Coverage** is high for both everywhere (93% to 100%); no difference shown.
- **Documentation.** For the two new builds without a page, ShipLoop wrote no README: its documents are its
  `docs/shiploop/` specification, architecture and environment notes, which name every new surface (all-documents
  scope: 100% for both arms on both cases). Ratchet wrote a user README that names them all. On the ticket change
  both updated the service's own documents; on Grokbot both READMEs name the settings and leave out the API routes.
  User-document words: ShipLoop 0, 0, 4,912 (the service's, updated), 1,440; Ratchet 754, 213, 5,516, 2,033.
- **Code, by script (reported, not read).** ShipLoop's code is smaller in three cases of four: changed code lines 165 against 285, 274
  against 263, 62 against 92, 1,001 against 1,720; mean cyclomatic complexity per function 4.2/3.1, 6.7/4.0,
  1.9/2.4, 2.4/3.4 (ShipLoop/Ratchet). No syntax failures in either.
- **Code, read blind (R7; one Opus judge, two orders).** Chess: ShipLoop both times (means 4.6 against 3.9:
  depth-3 move counts on three positions, timing limits tested; the other product's tests "pin behaviour the
  request does not ask for"). Shared expenses: Ratchet both times (4.1 against 3.8: a commit queue and validated
  reloads, "over-engineering in places"). Ticket assignment: split (3.9 against 4.0: one reading prefers the
  smaller change that follows the service's conventions, the other the change that leaves the documented
  `list --raw` output alone). Grokbot: Ratchet both times (4.0 against 3.5: schema-checked confirmations applied once,
  receipts that survive a reload, validated atomic saves, 17 to 19 tests with real restarts and injected file faults;
  the other product leaner and easier to read, with a Host check, but no schema on record changes and a snapshot
  that crashes startup when damaged).

### Readings (section 5's margins)

| Case | R1 time | R2 tokens | R3 breadth | R4 depth | R5 coverage | R6 docs | R7 code | R4b calibrated |
|---|---|---|---|---|---|---|---|---|
| shared expenses | ShipLoop | – | – | ShipLoop | – | Ratchet | Ratchet | |
| chess engine | ShipLoop | – | – | – | – | Ratchet | ShipLoop | |
| ticket assignment | ShipLoop | – | – | – | – | – | – | Ratchet |
| Grokbot-local | ShipLoop | ShipLoop | – | – | – | – | Ratchet | |

(– no difference shown.) R2 as registered needs both output and total input at most two thirds: met on Grokbot
only, because ShipLoop's one long session reads as much cached input as Ratchet's fourteen. A better reading, its
own line and not the registered one: on output and on uncached input ShipLoop is at most a quarter of Ratchet in all
four cases.

**Overall, as registered: no difference in results shown.** Result cells ahead: ShipLoop 2 (depth on shared
expenses, the chess code reading), Ratchet 4 (documentation on the two new builds without a page, the expenses and
Grokbot code readings); neither arm is behind on breadth anywhere; the rule needs a lead of three cells and
Ratchet's is two. ShipLoop is ahead on time in 4 of 4 cases and on tokens, as registered, in 1.

### Predictions, scored as registered

P1 right (time, 4 of 4). P2 wrong (tokens, 1 of 4: the total-input condition). P3 right (breadth, 4 of 4 no
difference). P4 wrong (depth: ShipLoop ahead in 1 case, not 2). P5 right (coverage, 4 of 4). P6 wrong (docs: Ratchet
ahead in 2 cases, so 2 no difference, not 3). P7 wrong (the judge named one product in both orders in 3 of 4
cases). P8 right (overall).

### What this says (my reading, for the owner to accept or not)

- **Neither produces better results by the rule registered before the runs, and the result cells lean to
  Ratchet.** Both deliver everything the requests ask (breadth equal everywhere), coverage is equal everywhere, and
  seeded-fault depth is equal in three cases of four. Ratchet is ahead in four result cells (a user README on both
  new builds without a page; the blind code reading on shared expenses and Grokbot, both for more defensive code and
  deeper tests), ShipLoop in two (its tests catch 82% of seeded faults against 53% on shared expenses; the chess
  code reading). The rule needed a lead of three; Ratchet's is two, from one run a case.
- **The cost is not close.** ShipLoop delivers the same held-out result in 15% to 31% of the time and a
  quarter of the output tokens, in all four cases. Ratchet's first build reaches that same held-out result in
  about ShipLoop's time; everything Ratchet spends after its first build (29 to 142 minutes a case) buys its own
  added clauses and more tests, not one more held-out check.
- **What Ratchet gives that ShipLoop does not, measured:** a user README on new builds (ShipLoop writes none there;
  its `docs/shiploop/` notes cover the same surfaces for a maintainer), on the ticket change a suite that carries to
  another correct product (19 of 27 calibrated defects against 7), and, by the blind reading of the final products,
  more defensive code with deeper tests on two cases. The README and 18 of the 19 calibrated catches are already
  there at Ratchet's first build, so they come from its build stage, not from the later cycles; the first builds
  were not given to the judge, so where the more defensive code came from is not shown.
- **What ShipLoop's script-run fault check buys, measured again:** on shared expenses its 5 tests catch 82% of
  seeded faults against 53% for Ratchet's 13 (the pilot's F22 on Grokbot, here on a second case). Elsewhere equal.
- Since the request is the owner's question "which produces better results": on results, no difference shown by
  the registered rule, with the result cells leaning to Ratchet (4 to 2, documentation and code readings); on
  results per minute and per token, ShipLoop, by three to seven times.

### Not shown by this run

- One run per arm and case, one model (Sol 6.2 medium); the spread between two runs of one arm was not measured here
  (F38 of the pilot: 24 to 26 of 27 for one text).
- Breadth cannot separate them: all eight products and all four Ratchet first builds pass every held-out check.
  A case where a first pass falls short is still missing (the pilot's conclusion too).
- Documentation coverage is a surface count by script; it does not judge whether a README is useful. The blind
  judge did not see documents.
- The judge is one model family (Opus) reading each pair twice; its split on ticket assignment shows it is a reading,
  not a gate.
- Ratchet's three-cycle limit is the pilot's; a Ratchet run without it would only take longer (no run so far stopped
  by itself).

## 8. Learnings for either tool (2026-11-22, the owner's follow-up: "could we improve either one based on learnings, or from each other")

Status: exploratory. Read from the eight runs' records after the fact; nothing here was registered before the runs,
and each line rests on one run a case. No new run. Sources: `evidence/report/report.json`, the judge's reasons in
`evidence/judge/N-answer-M.json` (labels in `key.json`), and each point's `mutation.json`, `calibrated.json` and
`coverage-own.json` under the runs root's `measure/LABEL/POINT/`.

### Ratchet's first build beside ShipLoop's delivery (same cost)

| Case | Minutes: ShipLoop / Ratchet first build | Output tokens: ShipLoop / Ratchet first build | Seeded faults own tests catch: ShipLoop / Ratchet first build |
|---|---|---|---|
| Shared expenses | 14.3 / 10.2 | 27,535 / 26,349 | 49 of 60 / 28 of 60 |
| Chess | 10.4 / 8.5 | 21,313 / 20,961 | 47 of 59 / 50 of 60 |
| Ticket assignment | 15.3 / 11.1 | 30,077 / 28,708 | 9 of 9 / 19 of 19 |
| Grokbot | 26.5 / 20.0 | 52,934 / 52,820 | 27 of 60 / 29 of 60 |

Ratchet's first three sessions (specification, plan, build) cost what a whole ShipLoop delivery costs, pass every
held-out check, and already hold the README and 18 of the 27 calibrated ticket catches. Their code was not read by
the judge.

### What Ratchet's later cycles bought

| Case | Minutes after the first build | Its own tests: first build to final | Seeded faults caught: first build to final |
|---|---|---|---|
| Shared expenses | 36.2 | 6 to 13 | 28 of 60 to 31 of 59 |
| Chess | 28.7 | 14 to 16 | 50 of 60 to 50 of 60 |
| Ticket assignment | 89.3 | 127 to 134 | 19 of 19 to 24 of 25 (calibrated 18 to 19 of 27) |
| Grokbot | 142.3 | 7 to 19 | 29 of 60 to 32 of 60 |

- **L1. More tests did not make deeper tests.** On shared expenses and Grokbot the later cycles more than doubled
  the test count and the seeded-fault catch rose by three. ShipLoop's 5 tests on shared expenses catch 49 of 60.
  Same direction as the pilot's F22: a script-run check of tests against seeded faults did what added testing
  passes did not.
- **L2. The later cycles add what the request did not ask for.** In all four cases the judge names extras in
  Ratchet's final product or tests (a stricter duplicate-member rule and 400s the request does not ask for; tests
  for coercion and subprocess behaviour on chess while the stated time limits and depth-3 move counts go untested;
  parsing written to the stand-in provider's phrasing on Grokbot, with a lookup that misfires on ordinary
  questions). Same direction as the pilot's section 13 (outside judges accepted 10 of 59 additions).

### What ShipLoop lacks that Ratchet's first build has

- **L3. No user page on a new build.** ShipLoop named 0 of 3 and 0 of 5 new public surfaces in a user document on
  the two builds that start without one (its `docs/shiploop/` notes name all of them); where a page existed it
  kept it current (2 of 2 on tickets). Ratchet's build prompt carries one line for this ("The documents the change
  makes wrong or incomplete (the README, ...)") and its first build named 4 of 4 and 5 of 5.
- **L4. ShipLoop's ticket tests do not carry to another correct product.** 5 of its 6 new test cases fail on the
  harness's correct reference and on the alternative control, so only one can catch a calibrated defect (7 of 27
  against Ratchet's 18 at first build). Each of those cases covers several behaviours in one test (for example
  "TC-1 assigns, leaves repeated requests unchanged, and clears the assignee"). Against its own product the same
  tests catch 9 of 9 seeded faults: they are strong as a guard of this build and weak as a statement of the
  request. My reading of the cause (not checked assertion by assertion): one detail particular to its own product
  fails a whole many-behaviour test. One case, one run; not yet measured on archived ShipLoop ticket deliveries.
- **L5. Saved state is trusted on load.** On both new builds that keep a file, the judge notes ShipLoop reads it
  without validation (Grokbot: a damaged snapshot ends startup with a raw error); Ratchet validates in both. No
  request asks for it and no held-out check covers it. Reported, not proposed: a rule here would be a design
  opinion, and the judge also marks Ratchet down for over-engineering in the same readings.

### Seen in both

- **L6. Both made choices the requester was not told.** On ticket assignment ShipLoop added a column to the
  documented `list --raw` output and routed every change through a rewritten `apply()`; Ratchet kept untrimmed
  names, counted the length limit in UTF-16 units and logged a clear as "assigned". This is the finding of the
  spec-elaboration study (an unstated limit is chosen silently) on new runs, and more evidence for the `defaults`
  candidate that awaits the owner (branch `shiploop-defaults-2c3d50`), not a new change.

### For the next harness round

- Register output and uncached input tokens, not total input (R2 here).
- A case where a first build falls short is still missing; breadth has now sat at the ceiling in the pilot and here.
- Give Ratchet's first builds to the blind judge: that says whether the code readings it won (shared expenses,
  Grokbot) come from its build or from the later cycles.

## 9. Unstated requirements: who finds them (2026-11-22, the owner's second follow-up)

The owner: "I do wonder if [Ratchet] is better about detecting implicit or unidentified requirements or spec
conditions. Is this the case and should we consider that in both the judge and implemention? Shiploop may do better
at re-planning spec requirements after a pass of the build?"

Status: exploratory. Counts read from the eight runs' own files after the fact, plus one probe of one delivered
product. Nothing registered beforehand; no model ran. Sources under the runs root: `LABEL/work/ratchet/spec.md` and
`delta-N.md` (Ratchet), `LABEL/work/docs/shiploop/spec.md` (ShipLoop).

| Case | Specification words: ShipLoop / Ratchet | Ratchet: points marked `Open:` | Ratchet: clauses it labels implied | Ratchet's after-build looks: clauses added | of those, its own product did not meet |
|---|---|---|---|---|---|
| Shared expenses | 486 / 3,759 | 10 | 11 | 8 | 1 |
| Chess | 336 / 3,172 | 4 | 19 | 4 | 1 |
| Ticket assignment | 310 / 3,794 | 5 | 9 | 10 | 5 |
| Grokbot | 785 / 6,996 | 23 | 11 | 15 | 10 |

ShipLoop's four specifications mark no point as open or as its own choice.

- **L7. Ratchet writes down what the request leaves unsaid; ShipLoop decides it in passing.** On ticket assignment
  Ratchet's specification marks five points for the requester. ShipLoop's specification settles four of them inside
  ordinary requirement lines with no mark ("trimmed single-line agent name of up to 64 characters"; "matches an
  explicit name exactly"; a repeat after an intervening change is news; "Raw output appends the assignee column")
  and does not mention the fifth (what a filter value outside the name rules does; the judge notes the filter value
  is unchecked). Two of the five are the choices the blind judge later picked on (how a name is trimmed and
  counted; the raw column).
- **L8. Marking a point did not make the build better.** No one answers an `Open:` line in an unattended run, so
  Ratchet's builder chose as well. On the name rule the judge preferred ShipLoop's unmarked choice (it follows the
  product's own convention for requesters) to Ratchet's (untrimmed, UTF-16 units). The gain from marking is that a
  requester could answer; these runs had no requester.
- **L9. The after-build looks find shortfalls in a product that passes every held-out check.** Of 37 clauses the
  looks added, Ratchet's own product did not meet 17, by the look's own probe of the running product. Several read
  as defects to me (Grokbot: reloading after a send leaves the draft, and sending it starts a second task;
  asking for `ORD-1001A` answers with `ORD-1001`; two processes on one data folder each confirm `ORD-1005` and one
  is lost. Tickets: a body with a malformed UTF-8 byte is saved as a name). Others are finer than a requester may
  care about (a 20,000-letter ID; a move passed as an object with `toString`). This corrects L2's wording: about
  half of what the later cycles added named something the product did not do. Not judged by an outside reader
  here; the pilot's outside judges accepted 10 of 59 additions written under the earlier specification text.
- **L10. The look is cheap; the cycle it starts is not.** The three looks of a run took 4.8 to 11.0 minutes
  together (`seconds_by_role.delta`: 289 to 662 seconds), 1.6 to 3.7 minutes a look. The 29 to 142 minutes after
  the first build went to the rebuilds and the test passes the looks set off.
- **Probe, ShipLoop's delivered ticket product against Ratchet's ticket finds** (a copy in the scratchpad, started
  on a free port, 2026-11-22 13:44 UTC): the detail view shows the current assignee (Ratchet's C-45: ShipLoop
  already right); a clear is logged as `ticket.unassigned` (C-49: already right); a body holding byte `0xFF` in the
  name returns 200 and saves the name with a replacement character (C-50: same gap); `?assignee=Da%FFna` returns
  200 and matches that ticket (C-52: same gap). C-51 (a name containing the handoff separator) was not tried. So of
  four finds tried, ShipLoop's product shares two.

### What this means for the measures

Neither instrument here can see any of this. The held-out checks cover what the request states and sit at the
ceiling; the judge read code and tests and was not asked what the product does where the request is silent, nor
whether a choice was told to anyone. A tool earns nothing for marking a point and loses nothing for choosing
silently. A measure that could see it: per case, a list of conditions the request leaves unsaid, fixed before the
runs from sources independent of both arms, each probed on the running product and scored handled / chosen and
told / chosen silently / not handled. It is scored on the product and on what the requester is told, never on the
length of a specification (the spec-elaboration study's lesson: a count over a specification rewards deciding).
The 42 `Open:` lines and 17 shortfalls above could seed such a list for these four cases only after an outside
reader has kept the ones a requester would care about, since a list written by one arm favours that arm.

### Not shown

Whether a requester would want any of the 17; whether ShipLoop's other three products share Ratchet's finds (one
case probed, four finds); whether one look after ShipLoop's build, reported to the requester and not rebuilt
automatically, finds as much on ShipLoop's products. That last is the cheapest next test: four sessions of a few
minutes on the four delivered ShipLoop products, then two outside judges on the findings.

## 10. The deep judge: design, registered before it reads any product (2026-11-22)

The owner: "Help me do both: improve the judge first to deeply analyze the quality of feature, examining the spec,
tests and build with a lot more finesse to determine if there is a better quality product built or the smaller
faster version is nearly competitive to a lot of specification like ratchet". "Both" is section 9's two offers: a
measure that can see what a product does where the request is silent, then one after-build look on ShipLoop's
products (section 11, to be registered when this judge has been proven).

### Why the first judge is not enough

It read code and tests as text, gave five 1-to-5 scores and a preference, saw no specification and ran nothing.
It could not say what a product does where the request is silent, whether a test pins a requirement, or whether a
defect it suspected is real. It compared final products only, so it could not separate what Ratchet's long
specification buys at ShipLoop's cost from what its later cycles buy.

### What is judged

Three products a case, twelve in all: **S**, ShipLoop's delivery; **F**, Ratchet's first build (the same cost as S,
section 8); **L**, Ratchet's final (3 to 7 times the cost). S against F asks what the long specification buys at
equal cost. F against L asks what the later cycles buy. S against L is the owner's question.

### Steps (apparatus: `deep_judge.py`; every model's answer is a JSON file kept as evidence)

1. **Case inventory, written without seeing any product.** Two listers of different families (Opus; Grok), each
   from the request alone (and the starting files, where the case has them), write (a) the stated requirements as
   separate checkable items and (b) the conditions the request leaves unsaid that a requester, an operator or the
   next maintainer would plausibly care about, each with a way to observe it on a running product. One session
   merges the two lists and a third list, the points the arms themselves raised (Ratchet's `Open:` lines and
   after-build clauses, the first judge's remarks), removing duplicates and recording each item's sources. Then
   both families rate every unstated item without seeing its source: `must`, `should`, `no` (a requester would not
   care, or it is over-engineering). An unstated item is **kept** when both rate it `must` or `should`. Results
   are reported for all kept items and again for the items an independent lister raised, since an item only an
   arm raised may favour that arm.
2. **Product audit, one product at a time.** An auditor (Opus) is given the request, the starting files, the
   inventory and one product under a code name. It is not told another product or any tool exists. It must run the
   product and its tests in its own copy. For each stated item: built (`yes`, `partly`, `no`, `wrong`) with the
   command and output that shows it; whether the product's own specification states it; whether a test pins it
   (`strong`: the named test would fail if the item broke; `weak`; `none`). For each kept unstated item: what the
   product does (observed), how sound that is (`sound`, `acceptable`, `poor`, `unhandled`), whether its
   specification marked the point open, decided it with a mark, decided it without one or is silent, and whether
   the choice is told to a reader of the product's documents. Then findings outside the inventory: defects with an
   exact reproduction, things built beyond the request (`value`, `neutral`, `liability`), tests tied to internals
   or to one product's choices, and what a maintainer would find hardest.
3. **Cross-probe.** Every defect any auditor reports for any product of a case is tried, by its reproduction, on
   the case's other products by a separate session, so a defect counts against every product that has it and not
   only the one where it was noticed. A defect whose reproduction does not reproduce on its own product is dropped.
4. **Verdict.** Two judges of different families (Opus; Grok) get the three audits and the defect table of a case
   with tool names masked and letters assigned by a seeded coin; no times, no token counts. For each pair they
   answer on a five-step scale which is the better feature for someone who will run and maintain it, name each
   advantage with the audit line behind it and whom it matters to (requester, operator, maintainer, no one), and
   answer one fixed question: could one short follow-up task (about an hour of the same builder's work) close what
   the lesser product lacks. A pair is decided only where both judges agree on the side.

### Instrument check, before any of the twelve is audited

The ticket case has a correct reference and 27 calibrated single-edit defects (`grade.build_variant`). The audit of
step 2 is run on the reference and on three defects drawn by a seeded choice
(`random.Random("deep-judge calibration").sample(sorted(defects), 3)`), under code names. **Bar:** the audit marks
no stated item `no` or `wrong` on the reference, and reports the planted defect (as a stated item `no`, `wrong` or
`partly`, or as a defect with a reproduction) in at least two of the three. If the bar is missed the audit text is
revised once, the change is recorded here, and the check is rerun on three newly drawn defects.

### Readings (margins fixed now; "ahead" needs the margin)

| | Measure | Ahead when |
|---|---|---|
| D1 | Stated items built `yes` | 2 items more |
| D2 | Stated items with a `strong` test | 2 items and 10 points more |
| D3 | Kept unstated items handled `sound` or `acceptable` | 2 items and 10 points more |
| D4 | Of the unstated items where the product chose, the share whose choice is told (marked in its specification or stated in its documents) | 2 items and 10 points more |
| D5 | Defects that reproduce, severity high or medium, after the cross-probe | 2 fewer |
| D6 | Verdict of the two judges on the pair | both agree on the side |

Per case and pair, the product ahead in at least two more of D1 to D6 than the other is **the better feature**;
otherwise no difference shown. **Nearly competitive:** S is nearly competitive with L in a case when the pair shows
no difference or S is better, or L is better and both judges answer that one short follow-up task closes the gap.
Things built beyond the request and maintainability notes are reported, not counted (one auditor's opinion).

### Predictions

- Q1. The instrument check meets its bar at the first attempt.
- Q2. D1 is level for every pair in every case (the held-out checks already say so).
- Q3. L is ahead of S on D3 in at least two cases; S is ahead of L on D3 in none.
- Q4. F is level with L on D1 to D3 in at least three cases (what Ratchet has, it has at its first build).
- Q5. Neither arm is ahead on D4 anywhere when "told" means the product's documents; counting marks in the
  specification, F and L are ahead of S in at least three cases.
- Q6. L has fewer reproducing defects than S (D5) in at least two cases.
- Q7. S is nearly competitive with L in at least three of four cases.
- Q8. Of the unstated items only an arm raised, fewer than half are kept by both raters.

### Limits known now

One auditor a product, one family (Opus); an audit is an observation by a model, and only its defects are
re-run by another session. The inventory's unstated list is what two models thought of plus what the arms raised;
it is not what this requester would say. The judges see the audits, not the products. The products were built by
Sol 6.2; the listers, raters, auditors and judges are other families (the pilot's section 13: the author's family
accepts three times what outside judges accept). Still one run a case.

### Amendment 1 to section 10 (2026-11-22 06:10, before any product was audited): Sol's review, and what changed

The design above went to Sol 6.2 at max effort for an adversarial review (question and verbatim answer:
`evidence/deep/review/`). At that moment the only sessions that had run were the two listers on the ticket request,
which see no product. What the review said and what I did with each point:

| Sol's point | Decision |
|---|---|
| The arms shape which behaviours earn credit: Ratchet supplied the `Open:` lines and after-build clauses | **Taken.** D3 and D4 are read on the items an independent lister raised. The merger finishes that list before it opens the arms' points. Items only an arm raised are rated and probed too and reported apart, as a sensitivity check. |
| Auditors can give each product a different exam; cross-probing only corrects defects someone found | **Taken.** Every auditor runs the inventory's own probe for every item, behaviour first, before opening the product's tests or specification, and may not change a behaviour grade afterwards. Every inventory item on which the audits grade the products differently is then run again on all the case's products by the cross-probe session, and its grade replaces the audits'. Each auditor gets the same number of probes of its own (12) and lists all of them. |
| One serious failure can vanish in a tally | **Taken as a gate.** Serious = a reproducing high-severity defect or a stated item not built (after the re-run). In a pair, the product with fewer serious failures is the better feature whatever the tallies say, and S is not nearly competitive with L if S has more. |
| D2 (a `strong` test by reading) can be bought with volume; an exhaustive test census costs much and decides little | **Taken.** D2 is now proved on six stated items a case drawn by seed (`random.Random(f"deep-judge proved {case}")`): the auditor breaks the behaviour in its copy, runs the suite, and records whether it fails. Ahead at 2 items. The by-reading grade is reported, not counted. |
| D4: an `Open:` mark alone should earn nothing; fix the denominator | **Taken.** D4 = of the kept independent unstated items that apply, those where the documents delivered with the product (not the builders' specification or notes) give an accurate account of what it does. Marks in the specification are reported apart. |
| D6: judges can be swayed by volume and order | **Partly.** Each judge gets its own seeded lettering and order; the packet tells them size counts only through what the audits show it bought and to count a consequence once. The audits still show how much each product holds; a limit. |
| The instrument check is too weak (an auditor catching half the defects passes 2 of 3 on 47% of draws; a clean reference can be given false deficits) | **Taken; the check replaces the one above.** Four products under code names, run through every step including the judges: the correct reference; the same reference **padded** (a specification of some 2,000 words restating the request six ways, and every test of the new behaviour a second time under another name); the reference with one calibrated defect that breaks a **stated** requirement; the reference with one that breaks a behaviour the request leaves **unsaid**. Draws: `random.Random("deep-judge calibration stated").choice` and `...unstated").choice` over the two pools named in `deep_judge.py` (9 and 7 of the 27). **Bars:** (C1) reference and padded: every stated item `yes`, no reproducing high or medium defect, no reading D1 to D5 ahead for either, both judges answer `same`; (C2) the stated defect: its item is not `yes` or a reproducing defect names it, the reference is the better feature of that pair, and both judges prefer the reference; (C3) the unsaid defect: reported as `poor` or `unhandled` on an inventory item or as a reproducing high or medium defect. A miss: the instructions are revised once (a fix session on Opus at xhigh, the owner's instruction of 2026-11-22), the change recorded, and the check rerun on newly drawn defects. |
| Repairability could be measured (run the follow-up task and compare all-in cost) | **Not now.** The judges' answer to the one-task question stands in; a real repair run is a candidate for after the results (it would run on Opus at xhigh by the owner's instruction, which is not the builders' model: a limit to state then). |
| One run a case: a result applies to these deliveries, not to specification length as such | **Accepted as a limit**, as before. |

Changed readings, replacing the table above: D1 as before; **D2** proved tests of six seeded stated items, ahead
at 2; **D3** independent kept unstated items handled, 2 items and 10 points; **D4** as redefined, 2 items and 10
points; D5 as before; D6 as before, each judge with its own lettering. The better feature of a pair: the gate
first, then a lead of two readings. Nearly competitive: the gate does not favour L, and the pair shows no
difference or S better, or both judges say one short task closes the gap. Prediction Q1 now refers to bars C1 to
C3; Q5 reads "level on D4 everywhere; counting marks in the specification, F and L ahead in at least three cases".

Models: listers, raters and judges are Opus (default effort) and Grok 4.7 at xhigh (the `ask` runner's newest
stable Grok); auditors and the cross-probe are Opus.

### The instrument check, round 1 (2026-11-22 06:15 to 06:50): result, and amendment 2

Status: firm for what it measured (four products, one auditor each). Evidence: `evidence/deep/calibration/` (the
key, the four audits, the cross-probe, the single reader's `told.json`, both verdicts, `deep.md`) and
`evidence/deep/tickets/` (both listers, the merge, both ratings, the inventory).

**The ticket inventory.** Opus listed 18 stated and 18 unstated items, Grok 4.7 20 and 11. Merged: 21 stated, 28
unstated (22 raised by an independent lister, 6 only by an arm). Both raters kept 19 of the 22 and 2 of the 6
(Q8, fewer than half of arm-only items kept: right on this case). The two raters disagreed on keep-or-drop for 2 of
28 items.

**The draws:** stated `name-limit-off-by-one`, unstated `raw-column-inserted`.

| Bar | Result |
|---|---|
| C1, reference and padded reference: every stated item `yes` | Met: 21 of 21 each |
| C1: no reproducing high or medium defect | Met: 0 each (5 low ones, the same 5, present on all four products) |
| C1: no reading D1 to D5 ahead for either | Met: D1 21 and 21, D2 5 and 5 of 6 (the same item unproved on all four), D3 18 and 18 of 19, D4 2 and 2 of 19 (single reader), D5 0 and 0 |
| C1: both judges answer `same` | **Missed as written.** Both judges, each with its own lettering, rate the clean reference somewhat better than the padded one, for one reason: the duplicated test file and the specification that "decides nothing" are cost a maintainer carries. |
| C2, the stated defect: item not `yes`, or a reproducing defect names it | Met: S-6 `wrong` by the auditor and by the re-run; defect D-5, medium, present only there |
| C2: the reference is the better feature of the pair; both judges prefer it | Met: by the gate (one stated item not built), and both judges |
| C3, the unsaid defect: reported | Met: U-16 `poor`, S-18 `partly`, defect D-6 graded high (the weekly report counts every status as 0), present only there |

**My decision on the missed clause:** the instrument is not revised for it. The clause was mine and it was wrong:
the padded copy is a larger product with nothing added, and a judge who calls it somewhat worse is doing what the
clause exists to protect (size must not earn credit). The pair still reads "no difference shown" (one reading, D6,
is not a lead of two). The owner can overrule. For the real cases this means D6 can go against a product for
carrying material that buys nothing; that is intended.

**What the check exposed beyond its bars, and amendment 2 (made before any real product was audited):**

- **`told` by each product's own auditor is noise.** On four products with identical delivered documents the
  auditors answered `yes` on 1, 0, 3 and 2 of the 19 independent items, more than D4's margin. *Change:* one reader
  (Opus) answers `told` for every product of a case, with one standard and a quoted line (`told-packet`, written
  by a fix session on Opus at xhigh, the owner's instruction). On the same four products it answers 2, 2, 2 and 2.
- **A test's strength by reading is noise.** Identical test files were graded `strong` on 14, 11 and 14 of 21
  stated items, and one judge credited a product with "slightly stronger tests" on that basis. *Change:* the
  judges' packets no longer carry the by-reading grade, only what was proved by breaking the behaviour. D2 was
  already the proved sample; it came out identical on all four (5 of 6, the same item).
- **What held without change:** `built` and `handling` (three items differed between audits, all three the planted
  defects, each confirmed by the re-run); the cross-probe (15 reported defects merged to 7, five low ones found
  present on all four products, each planted one on its own product only).

Because the instrument changed, the check is run again on two newly drawn defects (round 2: stated
`notify-requester`, unsaid `actor-ignored`; the reference's and the padded copy's audits are reused, the
cross-probe, the reader and the judges run afresh). The audit instructions did not change, so the real ticket
audits were started in parallel with round 2.

### The instrument check, round 2 (2026-11-22 06:50 to 07:10): the changed instrument on two newly drawn defects

Status: firm for what it measured. Evidence: `evidence/deep/calibration2/` (the two new audits, the cross-probe,
`told.json`, both verdicts; the reference's and the padded copy's audits are round 1's).

The draws: stated `notify-requester` (the assignment notice goes to the ticket's requester), unsaid
`actor-ignored` (assignment history records "system", not the acting user).

| Bar | Result |
|---|---|
| C1, reference against padded: stated items, defects, readings D1 to D5 | Met again: 21 and 21; 0 and 0; D2 5 and 5 of 6; D3 18 and 18 of 19; D4 2 and 2 of 19 |
| C1: both judges answer `same` | Missed as written, as in round 1 and for the same reason: both judges put the clean reference somewhat ahead of the padded copy |
| C2, the stated defect | Met: S-13 `wrong` by the auditor and the re-run, two unsaid items about the notice `poor`, defect D-5 graded high and present only there; the gate and both judges (each "much") put the reference ahead |
| C3, the unsaid defect | Met: U-4 `poor` by the auditor and the re-run, defect D-7 graded high and present only there |

Over both rounds: four planted defects, four found, each on its own product only after the cross-probe; no stated
item marked short on a correct product; the single reader's `told` the same on every product of a round (2 of 19
independent items, eight products). The judges' strength follows severity: "some" for the medium defect of round
1, "much" for the high one of round 2. The by-reading test grade stayed noisy (14, 11, 14 of 21) and is no longer
shown to the judges.

**What the check does not show:** how often an auditor misses a defect that no one planted and no other auditor
reports; whether a judge's preference between two correct products of different shape is stable (each pair was
judged once by each family).

A second change to the apparatus, made for Grokbot before its audits: its inventory holds 108 stated and 45 kept
unstated items, too many for one session to try with care, so each product's audit is shared between three
sessions (stated items 1 to 54, 55 to 108, and the unstated items with the probes of the auditor's own choosing
and the closing notes) and joined by script (`join-shares`). The shares use the same instructions; the page is
driven with this machine's Playwright, the one the pilot's grader uses. A limit: three auditors a product there,
one elsewhere.

## 11. One look after ShipLoop's build, then a fix: registered before any look runs (2026-11-22 07:40)

The second of the owner's two requests ("Help me do both"), from section 9: Ratchet's looks at a running build are
cheap (1.6 to 3.7 minutes each) and found shortfalls in products that pass every held-out check; the cost was the
rebuilds they set off. The owner: "Shiploop may do better at re-planning spec requirements after a pass of the
build?" and, on the fixes, "Use Opus Extra high for fixes".

At this moment the deep judge has scored chess, expenses and tickets; Grokbot's cross-probe is running. No look
session sees any of the deep judge's files.

### Steps

1. **The look.** One session of ShipLoop's builder (Sol 6.2 medium on Codex, through the pilot's `one_session.py`)
   in a copy of ShipLoop's delivered product, the copy the deep judge audited. The instructions (`look.py`) are
   Ratchet's closing look turned into a report: use the running product, then write `docs/shiploop/look.md` with
   two lists, **shortfalls** (each with the steps that show it and `high`, `medium` or `low`) and **choices the
   customer was not told**. It may change nothing else; `one_session.py` puts any other change back.
2. **What the look is worth, against the deep judge.** The deep judge's findings on ShipLoop's delivery were made
   by other sessions that never saw the look: the kept unstated items graded short after the re-run, and the
   defects that reproduce on it. One Opus session matches the look's shortfalls to that list; I check the matches.
   - **K1, recall:** of the deep judge's shortfalls and reproducing defects on S, the share the look names.
   - **K2, precision:** of the look's shortfalls, the share that are on the deep judge's list, plus those not on it
     that a probe reproduces and both rating families (Opus, Grok) keep (`must` or `should`). The rest are noise.
   - **K3, the choices:** of the kept unstated items where the single reader found S's documents silent, the share
     the look lists under choices.
3. **The fix, where the deep judge puts Ratchet's final ahead of ShipLoop's delivery.** One session on Opus at
   xhigh effort (the owner's instruction; not the builder's model, which is a limit to state with the result) gets
   the product and `look.md` and is told to close each shortfall the request's intent covers, with a test for
   each, and to tell the customer the listed choices in the delivered documents; no new features.
4. **The deep judge again, on the fixed product.** The same inventory and audit instructions under a new code
   name, the cross-probe over the case's defect list and every item on which the fixed product, the original and
   Ratchet's final differ, the single reader, both judges. The pairs: fixed against Ratchet's final (the
   question), and fixed against the original.
   - **K4:** the better feature of fixed against Ratchet's final, and whether the fixed product is nearly
     competitive, by section 10's rules unchanged.
   - **K5, cost:** ShipLoop's minutes plus the look's plus the fix's, beside Ratchet's minutes. Tokens are reported
     by model and not added across models.

### Predictions

- K1: at least half on Grokbot; lower on the three small cases, where the deep judge's list is short.
- K2: at least half of the look's shortfalls are real by the rule above.
- K3: under a third (a session lists few of its own family's silent choices unprompted; this asks for them, so it
  may do better).
- K4: after the fix, ShipLoop's product is nearly competitive with Ratchet's final, or better, in every case where
  it was behind.
- K5: under half of Ratchet's minutes in every case.

### Limits known now

One look and one fix a case. The fixer is a stronger model at a higher effort than either builder, so K4 says what
a look plus a strong fix reaches, not what ShipLoop's builder would reach. The deep judge's list is itself what
three auditors and a cross-probe found, not everything wrong with the product.

## 12. The deep judge's results on the twelve products (2026-11-22, audits 06:50 to 08:00)

Status: firm for what was measured: one audit a product (three sessions a product on Grokbot), one cross-probe a
case, one reading by each judge family. Evidence: `evidence/deep/CASE/` (both listers, the merge, both ratings,
the inventory, every audit, the cross-probe, the single reader's `told.json`, both verdicts and their letterings)
and `evidence/deep/deep.md`, `deep.json`. S is ShipLoop's delivery, F Ratchet's first build (the same cost as S),
L Ratchet's final (3 to 7 times the cost).

### Inventories

| Case | Stated items | Unstated items an independent lister raised: rated, kept by both raters | Items only an arm raised: rated, kept |
|---|---|---|---|
| Shared expenses | 35 | 27, 16 | 9, 2 |
| Chess | 40 | 10, 6 | 2, 2 |
| Ticket assignment | 21 | 22, 19 | 6, 2 |
| Grokbot | 108 | 46, 39 | 15, 6 |

### Readings (S / F / L)

| | Shared expenses | Chess | Ticket assignment | Grokbot |
|---|---|---|---|---|
| D1 stated items built | 35 / 35 / 35 of 35 | 40 / 40 / 40 of 40 | 21 / 21 / 21 of 21 | 108 / 108 / 108 of 108 |
| D2 tests proved by breaking six stated behaviours | 6 / 6 / 5 | 5 / 4 / 4 | 6 / 6 / 6 | 2 / 2 / 4 |
| D3 independent unstated items handled | 16 / 16 / 16 of 16 | 6 / 6 / 6 of 6 | 18 / 19 / 19 of 19 | 33 / 35 / 38 of 39 |
| D4 of them, told in the delivered documents | 0 / 14 / 14 | 0 / 0 / 1 | 15 / 17 / 18 | 6 / 14 / 20 |
| D5 reproducing defects, medium (none is high); low | 0 / 0 / 0; 2 / 1 / 1 | 0 / 0 / 0; 0 / 0 / 0 | 0 / 0 / 0; 2 / 2 / 1 | 6 / 2 / 1; 7 / 5 / 2 |
| Reported: D3 with the arm-only items | 18 / 18 / 18 of 18 | 8 / 8 / 8 of 8 | 20 / 21 / 21 of 21 | 33 / 39 / 43 of 45 |
| Reported: D4 counting marks in the specification | 0 / 14 / 14 | 0 / 1 / 3 | 15 / 18 / 18 | 6 / 23 / 26 |

### Pairs (the better feature by section 10's rule; the judges are Opus, then Grok 4.7)

| | S against L | S against F | F against L | S nearly competitive with L |
|---|---|---|---|---|
| Shared expenses | **L** (D4, D6; both judges L "some") | **F** (D4, D6; both F "some") | no difference (judges: same, F some) | no (one judge says a short task closes it, the other not) |
| Chess | no difference (D6 to S: both judges S "some") | no difference (both judges S "some") | no difference (both same) | yes |
| Ticket assignment | **L** (D4, D6; both L "some") | no difference (D4 to F; judges: same, S some) | no difference (D6 to L; both L "some") | no (judges split on the short task) |
| Grokbot | **L** (D2, D3, D4, D5, D6; both L "much") | **F** (D4, D5, D6; both F "much") | **L** (D2, D4, D6; both L "some") | no (both judges: a short task does not close it) |

No pair was decided by the gate: no product has a high-severity defect or an unbuilt stated item.

### What decided each case, from the audits and both judges' reasons

- **Shared expenses.** The three products behave alike on every stated and every kept unstated item. ShipLoop's
  delivery ships no user document, so it tells a customer none of the 16 unsaid points where both Ratchet builds
  tell 14, and it overwrites an existing `DATA_FILE` that holds JSON without a `groups` list (a low defect, on S
  only). Ratchet's later cycles bought nothing the instrument sees: F and L are level.
- **Chess.** Level on everything measured, no defect on any. Both judges put ShipLoop's delivery somewhat ahead of
  both Ratchet builds for what its suite guards (the two time limits, move counts at depth 3, invalid positions);
  Ratchet's README is the offset.
- **Ticket assignment.** All three are level on behaviour and tests (6 of 6 proved each). ShipLoop's delivery did
  not record the release (no changelog entry or version for the change: the one unstated item graded short, after
  the re-run) and tells 15 of 19 unsaid points against 18 for Ratchet's final. Ratchet's first build is level
  with ShipLoop's delivery; its final is ahead by the release record, a malformed name it refuses, and the
  assignee in the detail view.
- **Grokbot.** The only case where behaviour separates the products. All three build all 108 stated items. Of 14
  distinct defects the cross-probe found present 13 on S, 7 on F, 3 on L; six of S's are medium, among them two
  in the confirm flow the request stresses (after confirming by keyboard, a second Enter decides the next
  proposal; a capitalised field name adds a second field) and a reply left pending for good after a storage
  failure. F has none of those three. Both judges put F and L "much" ahead of S.

### What this says (my reading)

- **Where a request is small and its edges few, the heavier process bought documentation and little else.** On
  three of four cases every product built everything stated and handled nearly every unsaid point both raters
  kept; the differences are a user document ShipLoop did not write (expenses), a release record it did not write
  (tickets) and test choices (chess, in ShipLoop's favour).
- **Where the product is large and stateful, the long specification bought behaviour, at ShipLoop's cost.**
  Ratchet's first build of Grokbot, made in 20.0 minutes against ShipLoop's 26.5, has 2 medium defects against 6
  and tells 14 unsaid points against 6. That difference is there before any later cycle runs.
- **The later cycles bought something on two cases of four.** F to L: nothing on expenses and chess; on tickets a
  release record and two small behaviours (judges only); on Grokbot four more defects closed, three more unsaid
  points handled and two more tests proved, for 142 further minutes.
- **ShipLoop is "nearly competitive" by the registered rule on one case of four.** On expenses and tickets the gap
  is what a customer is told, and one of the two judges says a short task closes it; on Grokbot both say it does
  not.
- **Section 7's answer changes in one respect.** The first instruments read "no difference in results shown,
  leaning to Ratchet". This judge shows where the lean is real: on what the customer is told in three cases, and
  on behaviour where the request is silent in the largest case. It also shows what the first instruments had
  right: nothing stated was left unbuilt by anyone.

### Predictions, scored as registered

| | Prediction | Result |
|---|---|---|
| Q1 | The instrument check meets its bar at the first attempt | Wrong as registered: one clause of C1 missed (both judges mark the padded copy down) |
| Q2 | D1 level for every pair in every case | Right |
| Q3 | L ahead of S on D3 in at least two cases; S ahead in none | Wrong: one case (Grokbot). S ahead in none: right |
| Q4 | F level with L on D1 to D3 in at least three cases | Right: three (not Grokbot, on D2) |
| Q5 | Level on D4 everywhere; counting marks, F and L ahead in at least three cases | Wrong on the first half: L is ahead of S on D4 in three cases without counting any mark. Right on the second |
| Q6 | L has fewer reproducing defects than S (by two) in at least two cases | Wrong: one case |
| Q7 | S nearly competitive with L in at least three of four cases | Wrong: one |
| Q8 | Of the items only an arm raised, fewer than half are kept | Right over all cases (12 of 32); not on chess (2 of 2) |

### Not shown

One audit a product: an auditor's miss shows only where another product's auditor reported the same thing or the
re-run caught it. The judges read audits, not products. "Told" is one reader's call against quoted lines. The
inventory's unsaid items are what two models and the arms thought of; a real requester might keep others. One run
of each tool a case, as throughout: Grokbot's gap is one delivery against one delivery.

## 13. The look and the fix: results (2026-11-22 07:25 to 08:40; Grokbot's fix added below when it ends)

Status: firm for what was measured (one look and one fix a case). Evidence: `evidence/look/CASE/` (the look's
instructions, `look.md`, the deep judge's list it was matched against, the matches, the probe of its other
findings on all three products, both ratings), `evidence/fix/` (costs, each fix's report and diff) and
`evidence/deep/CASE-fixed/`.

**A change the owner made during this step (2026-11-22, about 08:25): "just use opus for the judge to speed things
up".** The twelve products of section 12 had already been judged by both families. From here a verdict is the Opus
judge's alone: the fixed-product cases below have one judge, so D6 is that judge's side and "one short task closes
the gap" is that judge's answer. Grok's raters had already rated the looks' findings.

### The looks (Sol 6.2 medium, one session each, in ShipLoop's delivered product)

| Case | Minutes | Shortfalls written | Reproduce on S | K2: real (on the deep judge's list, or reproduce and both raters keep) | K1: the deep judge's findings on S the look names | K3: silent choices listed, of those the reader found untold |
|---|---|---|---|---|---|---|
| Shared expenses | 4.5 | 5 | 5 | 2 of 5 | 1 of 2 | 5 of 18 |
| Chess | 2.1 | 2 | 2 | 1 of 2 | none to find | 1 of 8 |
| Ticket assignment | 3.2 | 5 | 5 | 1 of 5 | 0 of 3 | 1 of 4 |
| Grokbot | 7.8 | 15 | 15 | 15 of 15 | 10 of 25 | 8 of 27 |

- **Every shortfall a look wrote reproduces** (27 of 27 on the product it looked at). What separates the cases is
  whether both raters think a customer would care: 3 of 11 new ones on the small cases (Opus kept 3, Grok 8), 11
  of 11 on Grokbot.
- **The look and the audit find different things.** On Grokbot the look names 10 of the deep judge's 25 findings
  and adds 11 the three auditors did not report; on tickets it names none of the judge's 3 and adds 5.
- **The look's new findings are not ShipLoop's alone.** Probed on all three products: of Grokbot's 11, 7 are
  present on Ratchet's first build and 5 on its final (among them: an incomplete clarification loses the pending
  change request, rated `must` by both); of the small cases' real new ones, all three are present on F and L too.
  So section 12's defect counts are a floor for every product, Ratchet's final included.
- Predictions: K1 at least half on Grokbot, wrong (10 of 25); K2 at least half real, right on Grokbot (15 of 15),
  wrong on the small cases (4 of 12); K3 under a third, right on all four (5 of 18, 1 of 8, 1 of 4, 8 of 27).

### The fixes (Opus at xhigh, one session each, given the product and `look.md` only) and the deep judge again

| | Shared expenses | Ticket assignment |
|---|---|---|
| The fix | 3 of 5 shortfalls fixed, each with a test that fails without it; 2 declined as beyond the request; a README written | 4 of 5 fixed with tests; 1 declined and documented; release record and documents updated |
| Minutes: ShipLoop + look + fix, beside Ratchet's whole run | 14.3 + 4.5 + 6.8 = 25.6, beside 46.4 | 15.3 + 3.2 + 10.0 = 28.5, beside 100.4 |
| D3 unstated items handled: fixed / original / Ratchet's final | 16 / 16 / 16 of 16 | 19 / 18 / 19 of 19 |
| D4 told in the delivered documents | 12 / 0 / 14 of 16 | 18 / 14 / 19 of 19 |
| D5 low defects (no medium or high on any) | 2 / 3 / 1 | 3 / 2 / 1 |
| K4, fixed against Ratchet's final | no difference shown; the judge: same | no difference shown; the judge: Ratchet's final somewhat better |
| Nearly competitive with Ratchet's final | yes (was no) | yes (was no) |

(The single reader's counts for an unchanged product differ by one between its two readings on tickets: 15 then 14
of 19 for ShipLoop's original, 18 then 19 for Ratchet's final. That is the reader's noise, inside D4's margin.)

- **One look and one fix closed the gap the deep judge had found on both small cases**, without either session
  seeing the deep judge's findings: the fixer was told to tell the customer the choices the look listed, and that
  is where ShipLoop's deliveries were behind.
- **The fix is not free of cost to the product.** On tickets it changed what an existing query returns (a repeated
  `status` or `priority` filter now lists nothing where the service used the first value), which the fresh audit
  reported and the cross-probe confirmed as a low defect, and it is why the judge still leans to Ratchet's final.
- K5 (under half of Ratchet's minutes): right on tickets (28%), wrong on expenses (55%).
- A limit, as registered: the fixer is Opus at xhigh, a stronger model at a higher effort than the builders'.

- Added after the commit of this section: Grok's verdict on the fixed shared-expenses case had been requested
  before the owner's instruction and arrived after it. It is not counted. It puts Ratchet's final somewhat ahead
  of the fixed product where Opus says "same"; under section 10's two-judge rule the pair would still read "no
  difference shown" (the judges would not agree on a side) and nearly competitive.

## 14. Clean runs for the ShipLoop side: registered before any of them starts (2026-11-22 08:15)

The owner, on section 13: "I wanted to make sure that we're doing this from clean runs, not just repairs from old
ones, in order to make sure that our evaluations are not overly biased. Can you confirm that this is what
happened?" My answer from the records: the eight builds of section 7 were clean runs (each repository starts at
its base commit at 23:59 or 00:00 and ends at its delivery), and the deep judge of section 12 re-read those
deliveries with fresh sessions; but section 13's look-and-fix results are **repairs of those deliveries**, with
four ways to be biased: only ShipLoop's product was repaired, and only where it had been found behind; the fixer
is a stronger model than either builder; the fixed product got a fresh audit while the products beside it kept
their earlier ones; and there is one delivery of each tool a case. Offered: (1) fresh ShipLoop runs with the look
and the fix, beside last night's Ratchet finals; (2) fresh runs of both tools. The owner: "2", then "let's focus
on 1 first". This section registers (1).

### What runs

1. **A fresh ShipLoop run of each of the four cases**, from scratch in a new repository, through
   `launch.py` and the E2E harness as in section 3, on Codex Sol 6.2 medium, from a new checkout of `origin/main`.
   **The ShipLoop version is the one on main today, 2.6.0** (the owner's standing rule: always the latest
   ShipLoop), not last night's 2.4.1. 2.6.0 carries the released `defaults` change (the specification's result
   lists the choices it made for the requester), which bears on D4. So two things differ from section 7's ShipLoop
   runs at once, a fresh run and a newer version, and this section cannot say which moved a number.
2. **The look on every fresh delivery** (Sol 6.2 medium, `look.py`'s instructions unchanged) **and the fix on
   every one** (Opus at xhigh, the instructions of section 13 unchanged), all four cases, whether or not the
   delivery is behind: the process under test is "ShipLoop, one look, one fix" as a fixed sequence.
3. **The deep judge on three products a case, all audited afresh in one round**: the fresh delivery after the look
   and the fix, the fresh delivery itself, and last night's Ratchet final, which is audited again by a new session
   so that no product is read against an older audit. The inventories of section 12 are used unchanged (they were
   written without seeing any product). One cross-probe a case, the single reader, and the Opus judge alone (the
   owner's instruction).

### Readings

- **C-1, the fresh delivery against Ratchet's final**, by section 10's rules with one judge: does section 12's
  result repeat on a second ShipLoop delivery, now on 2.6.0?
- **C-2, the fresh delivery after look and fix against Ratchet's final**: the better feature, and nearly
  competitive or not. This is section 13's K4 without the repair.
- **C-3, cost**: the fresh run's minutes, plus the look's, plus the fix's, beside last night's Ratchet minutes.
- Reported: the held-out checks on each fresh delivery and on each fixed product (a fix must not break one); what
  each look found and each fix changed.

### Predictions

- The fresh deliveries build every stated item again (D1 level everywhere).
- C-1: on Grokbot Ratchet's final is again the better feature; on the three small cases ShipLoop 2.6.0 tells more
  unsaid points than 2.4.1 did, and at most one of them still goes to Ratchet's final.
- C-2: nearly competitive or better on the three small cases; on Grokbot not (my guess from section 12: its gap is
  in behaviour, and a look names under half of what an audit finds).
- C-3: under half of Ratchet's minutes on tickets and Grokbot; not on expenses and chess.

### Limits known now

Ratchet is not rerun (that is option 2): its side is still one delivery a case, from 2.4.1's night. The fixer is
Opus at xhigh, stronger than the builders. One fresh ShipLoop run a case. A version change and a fresh run are
confounded. The repaired Grokbot product of section 13 is still being audited; its result is recorded as a repair.

### Section 13, continued: Grokbot's repair (recorded 2026-11-22 09:00; a repair of last night's delivery, not a clean run)

The fix (Opus at xhigh, 26.4 minutes) closed 13 of the look's 15 shortfalls, each with a test that fails on the
original, and declined 2 with a note in the README. The deep judge on the repaired product (three shares, a
cross-probe on all three products, the single reader, the Opus judge), S' / S / L being repaired, original and
Ratchet's final:

| | S' / S / L |
|---|---|
| D1 stated items built | 107 / 107 / 107 of 108 (the re-run graded one item, the away summary in a browser new to the app, `partly` on all three) |
| D2 tests proved | 3 / 2 / 4 of 6 |
| D3 independent unstated items handled | 35 / 33 / 38 of 39 |
| D4 told in the delivered documents | 21 / 7 / 23 of 39 |
| D5 reproducing medium defects (none high); low | 4 / 8 / 3; 4 / 6 / 2 |
| K4, repaired against Ratchet's final | no difference shown by the rule (only D6 goes to L); the judge: Ratchet's final somewhat better, and a short task does not close it |
| Minutes: ShipLoop + look + fix, beside Ratchet's | 26.5 + 7.8 + 26.4 = 60.7, beside 162.3 |

Of the 14 distinct defects this round's cross-probe tried, 14 are present on the original, 8 on the repaired
product, 5 on Ratchet's final. The repair closed the two defects in the confirm flow and both storage-failure
ones; it left what the look had not named (a provider token printed on a damaged data file, duplicate bot names,
a prefix match on record ids). So on the case where the gap was in behaviour, one look and one strong fix halved
it and did not close it: the look names under half of what an audit finds (K1, 10 of 25). The fresh audit of this
round also found a stated item short on all three products that section 12's audits had passed, a reminder that
one audit a product is a floor.

## 15. Clean ShipLoop runs with one look and one fix: results (2026-11-22 08:20 on; Grokbot added below when it ends)

Status: firm for what was measured: one fresh ShipLoop run, one look, one fix and one audit round a case.
Registered in section 14. Evidence: `evidence/clean/` (the checkout record, each fresh run's launch and measure
records, each look and fix with its diff, the fix costs) and `evidence/deep/CASE-clean/` (three fresh audits, the
cross-probe, the single reader's `told.json`, the Opus verdict). S' is the fresh delivery after the look and the
fix, N the fresh delivery itself, L last night's Ratchet final, audited again by a new session in the same round.

**The fresh runs** (ShipLoop 2.6.0 from `origin/main` at 22e52c0807ca, Codex Sol 6.2 medium, each in a new
repository): all four ended PASS, in 10.1, 10.7, 10.5 and 28.7 minutes (last night on 2.4.1: 14.3, 10.4, 15.3,
26.5), and every one passes every held-out check (6, 10, 18, and 49 and 28).

| | Shared expenses | Chess | Ticket assignment |
|---|---|---|---|
| The look (Sol 6.2 medium): minutes, shortfalls written | 3.9, 5 | 1.6, 1 | 3.3, 7 |
| The fix (Opus xhigh): minutes, fixed, declined | 6.3, 4, 1 | 4.1, 1, 0 | 14.1, 4, 3 |
| C-3 minutes, run + look + fix, beside Ratchet's | 20.3 beside 46.4 (44%) | 16.4 beside 37.2 (44%) | 27.9 beside 100.4 (28%) |
| D1 stated items built, S' / N / L | 35 / 35 / 35 | 40 / 40 / 40 | 21 / 21 / 21 |
| D2 tests proved, of 6 | 5 / 5 / 6 | 6 / 5 / 4 | 6 / 6 / 6 |
| D3 independent unstated items handled | 16 / 16 / 16 of 16 | 6 / 5 / 6 of 6 | 19 / 18 / 19 of 19 |
| D4 told in the delivered documents | 13 / 0 / 15 of 16 | 4 / 0 / 1 of 6 | 18 / 13 / 18 of 19 |
| D5 reproducing defects, medium; low | 0 / 0 / 0; 0 / 0 / 0 | 0 / 1 / 0; 0 / 1 / 1 | 0 / 0 / 0; 2 / 3 / 1 |
| C-1, N against L | **L** (D4, D6) | no difference (the judge: L somewhat) | **L** (D4, D6) |
| C-2, S' against L | no difference; the judge: same; nearly competitive | **S'** (D2, D4, D6); the judge: S' somewhat | no difference (no reading ahead); the judge: same; nearly competitive |

- **C-1 repeats section 12 on a second delivery and a newer version.** ShipLoop alone again ships no user document
  on shared expenses (0 of 16 told) and no release record on tickets (the same unstated item graded short), and
  loses to Ratchet's final on those two cases for that reason. 2.6.0's `defaults` list did not change what the
  delivered documents say: it marks 2 of 16 points in the specification on expenses, none in a user document.
- **C-2: from clean runs, one look and one fix bring ShipLoop's delivery level with Ratchet's final on two small
  cases and ahead on the third**, at 28% to 44% of Ratchet's time. This is section 13's repair result without the
  repair: fresh run, fresh look, fresh fix, and all three products audited afresh in one round.
- **A fresh run is not the same product twice.** This chess delivery accepts a malformed position and answers
  for it (a medium defect; last night's delivery validated every field). The look reported exactly that, the fix
  closed it, and the fixed product's suite proves all six sampled behaviours.
- **The look and the audit still find different things.** Three fresh audits of the expenses delivery reported
  none of the five shortfalls its look wrote; on tickets the audits reported a malformed name the look did not.
- **A fix still costs something.** On tickets the fix again changed what a repeated `status` or `priority` filter
  returns (the fixer's own report); this round's auditors did not flag it.
- Predictions: D1 level everywhere, right. C-1: Ratchet's final ahead on at most one small case, wrong (two). C-2
  nearly competitive or better on the three small cases, right. C-3 under half on tickets, right; not on expenses
  and chess, wrong (44% each).

Limits as registered: Ratchet's side is last night's single delivery; the fixer is Opus at xhigh; a fresh run and
ShipLoop 2.6.0 are confounded; one audit a product, and the Opus judge alone.

### Section 15, continued: Grokbot from a clean run (recorded 2026-11-22 10:20)

The fresh ShipLoop 2.6.0 run ended PASS in 28.7 minutes and passes both held-out yardsticks (49 and 28). The look
(Sol 6.2 medium, 8.3 minutes) wrote 15 shortfalls (8 high, 6 medium, 1 low) and 9 choices. The fix (Opus xhigh,
24.7 minutes) closed 14, one of them in part, each with a test that fails on the unfixed product, and declined
one; the fixed product still passes both yardsticks. Nine audit shares, one cross-probe through the page on all
three products (11 disputed items re-run, 22 reported defects merged to 15), the single reader, the Opus judge.

| | S' fresh + look + fix / N fresh / L Ratchet's final again |
|---|---|
| D1 stated items built | 108 / 108 / 108 of 108 |
| D2 tests proved, of 6 | 3 / 2 / 4 |
| D3 independent unstated items handled | 34 / 31 / 38 of 39 |
| D4 told in the delivered documents | 17 / 2 / 18 of 39 |
| D5 reproducing defects, medium (none high); low | 5 / 8 / 3; 4 / 7 / 2 |
| C-1, N against L | **L** (D2, D3, D4, D5, D6; the judge: L much better) |
| C-2, S' against L | **L** (D3, D5, D6; the judge: L somewhat better; a short task does not close it); not nearly competitive |
| S' against N | **S'** (D4, D5, D6; the judge: S' somewhat better) |
| C-3 minutes | 28.7 + 8.3 + 24.7 = 61.7 beside 162.3 (38%) |

- **C-1 repeats section 12 on Grokbot too:** a second, fresh ShipLoop delivery is again well behind Ratchet's final
  where the request is silent (8 medium defects against 3; last night 6 against 1).
- **C-2 on Grokbot: the look and the fix halve the gap and do not close it**, from a clean run as from the repair
  (section 13: 4 medium against 3 after the repair; here 5 against 3). What the fix closed is what the look named
  (a save that overwrites, a failed reply hidden by a new message, a task left "Running", over-limit text cut
  silently). What remains on the fixed product the look had not named: conversations and same-named bots that
  cannot be told apart, a reply left pending after a storage failure, a damaged data file ending startup.
- **Every product has defects of its own.** Two medium ones are present on all three (a forget that matches nothing
  is reported as done; two server processes on one data folder both accept writes and a confirmed order is lost),
  and Ratchet's final has two the fixed ShipLoop product does not (a task left "Running" after a storage error;
  over-limit text cut silently).
- The hidden checks on all four fixed products: 6, 10, 18, and 49 and 28 passed, none failed
  (`evidence/clean/fixed-hidden/`). No fix broke anything the request states.
- Predictions (section 14): C-1 on Grokbot, right. C-2 on Grokbot not nearly competitive, right. C-3 under half on
  Grokbot, right (38%).

### All four clean cases together

| Case | Fresh ShipLoop alone against Ratchet's final | With one look and one fix | Minutes, beside Ratchet's |
|---|---|---|---|
| Shared expenses | Ratchet's final better | level (the judge: same) | 20.3 beside 46.4 |
| Chess | no difference (the judge: Ratchet somewhat) | **ShipLoop's better** | 16.4 beside 37.2 |
| Ticket assignment | Ratchet's final better | level (the judge: same) | 27.9 beside 100.4 |
| Grokbot | Ratchet's final better (much) | Ratchet's final better (somewhat) | 61.7 beside 162.3 |

**What this says (my reading).** A short look at the running product, followed by a fix pass, is worth adding
after ShipLoop's build: it is cheap, it finds things that reproduce, and on small requests it removes the
difference from the heavier process at under half the cost. It is not a substitute for what Ratchet's long
specification does on a large stateful request: there the first build already avoids defects that a look does not
name, and a look names under half of what an audit finds. Whether the fix must be a stronger model than the
builder was not tested (the owner chose Opus at xhigh for fixes); nor was a second look after the fix.

**Not shown.** Ratchet rerun from scratch (the owner's option 2, deferred: "let's focus on 1 first"). The same
sequence with the builder's own model as fixer. Whether the look belongs inside ShipLoop as a stage: that is a
ShipLoop product decision for the owner, with section 11's design and these results as the evidence.

## 16. Fresh Ratchet runs, and the look as a ShipLoop candidate: registered before either starts (2026-11-22 10:44)

The owner, on section 15's three open decisions: "Do 3 then 2 then 1, plan out all and execute, use agents as needed
for parallel". 3 was the merge and push of this study to `main` (done 10:41, merge commit
`472919dfcc81ec1933293f836d4c7ee8d54286d4`; the boundary check and the quick tier's 14 suites passed on it). 2 is
"one look after the build, then a fix" drafted as a ShipLoop candidate. 1 is the fresh Ratchet runs, the half of
the owner's earlier "2" (fresh runs of both tools) that section 14 left out. The Ratchet runs take about three
hours, so they start first and the candidate is drafted beside them.

### 16.1 Fresh Ratchet runs (the owner's step 1)

**Question.** Section 15 set a fresh ShipLoop 2.6.0 delivery, with and without the look and the fix, beside
*last night's* Ratchet final. Does its result hold when Ratchet's side is also a fresh run, of the same day, from
the same commit and the same starting files?

**What runs.**

1. **A fresh Ratchet run of each of the four cases**, from scratch in a new repository, through `launch.py run ROOT
   ratchet CASE LABEL` (the pilot's `ratchet.py --enrich reworded`, Codex, Sol 6.2 medium, the three-cycle limit),
   in a new runs root, from a new checkout of commit `22e52c0807ca41aa0224dd81f03b84e9bba44e82`, **the same commit
   this morning's ShipLoop runs came from**. Checked by `git diff` between last night's base
   (`d522655ae4f6a8af0b289d346aa08cf44d2e9fbe`) and that commit: `ratchet.py`, `one_session.py`, the pilot's
   `cases.json` and `grade.py` are unchanged; the one difference in starting files is the ticket fixture
   (its tests listen on 127.0.0.1), which this morning's ShipLoop ticket run already started from. So on tickets
   the fresh Ratchet run starts from the same files as the fresh ShipLoop run, which last night's did not. The four
   runs start together, as last night's did.
2. **Script measures** of each run's first build and final (`measure.py`: time, tokens, held-out checks).
3. **The deep judge on three products a case, all audited afresh in one round** (the rule of section 14): the
   fresh ShipLoop delivery after the look and the fix (S'), the fresh ShipLoop delivery (N), both exactly the
   products of section 15, and the **fresh Ratchet final (L2)**. Section 12's inventories are used unchanged. One
   cross-probe a case, the single reader, the Opus judge alone. Ratchet's fresh first build is measured by script
   and not audited (section 12 already read a first build; the question here is the final).

**Readings.**

- **F-1, S' against L2** and **F-2, N against L2**: the better feature and "nearly competitive", by section 10's
  rules with one judge. These repeat C-2 and C-1 with a fresh Ratchet side.
- **F-3, cost**: section 15's ShipLoop minutes (run, look, fix) beside the fresh Ratchet minutes.
- **F-4, how much one Ratchet run differs from another** (reported, no rule): L2's readings beside last night's
  final (L, as audited in section 15), per case; the time and the cycle count of each.
- **F-5, how much one audit differs from another on the same product** (reported, no rule): S' and N are the same
  trees section 15 audited, read here by new sessions. For each of D1 to D5, the difference between the two
  audits of the same product, set beside the margin the reading needs (2 items). A reading whose two audits of
  one product differ by its own margin cannot carry a verdict on that case, and I will say so where it happens.

**Predictions.**

- Every fresh Ratchet final passes every held-out check (as all of last night's did).
- F-1: on the three small cases S' is level with or ahead of L2 on at least two; on Grokbot L2 is the better
  feature again.
- F-2: N is behind L2 on what the customer is told (D4) on at least three of four cases.
- F-3: Ratchet's fresh minutes within 30% of last night's on at least three of four cases.
- F-5: the two audits of one product agree within one item on D1, D3 and D5 on the small cases; on Grokbot's 153
  items I expect D5 (defects found) to differ by two or more on at least one product, because section 13 already
  showed that two readers of one product find different defects.

**Limits known now.** One fresh run of each tool a case: two deliveries of Ratchet and two of ShipLoop a case in
all, still far too few for a rate. The ShipLoop side is not rerun for this section. The fixer is Opus at xhigh,
stronger than either builder. ShipLoop is 2.6.0 against section 7's 2.4.1.

### 16.2 The look as a ShipLoop candidate (the owner's step 2)

**What is drafted.** A candidate change to ShipLoop that adds the sequence section 15 measured: after the build
and its tests, the session uses the running product as its users and operators would, writes down the shortfalls
it saw happen and the choices the customer was not told, fixes the shortfalls the request's intent covers (each
with a test) and tells the choices in the delivered documents. It is built on a branch with tests and a change
note, reviewed by Sol 6.2 at max, tried on real runs of this comparison's cases, and **stays off `main` until the
owner accepts it** (AGENTS.md: a ShipLoop product behaviour trade-off is the owner's decision).

**What is already known that the design must respect** (read before designing):

- Section 15: one look and one fix bring a fresh ShipLoop delivery level with or ahead of Ratchet's final on the
  three small cases; on Grokbot they halve the gap. There the look ran as a **separate session that had not built
  the product** (Sol medium), and the fix was done by **a stronger model** (Opus xhigh). Inside ShipLoop both
  would be the building session itself, after its context has cleared: neither condition carries over for free,
  and the trial has to measure what is left of the gain.
- Section 13: everything a look writes reproduces, but on the small cases under half of it is something a customer
  would call a shortfall (2 of 5, 1 of 2, 1 of 5; 15 of 15 on Grokbot). A fix that builds every line of a look
  would add work nobody asked for on small cases.
- The Ratchet pilot's journal (`docs/ratchet-pilot-journal.md`, sections 13 and 14, finding on the closing looks):
  of what Ratchet's closing looks **added to the specification**, two outside judges accepted 10 of 59, and no run
  converged within three cycles because each look kept adding. So the candidate is **one look, not a loop**, it
  reports what it saw happen, not new requirements, and it adds no cycle limit of its own (no limit on a ShipLoop
  loop is added or changed without the owner).
- The released `defaults` list (ShipLoop 2.6.0) already tells the requester the choices made at specification
  time; section 15's fresh deliveries still told 0 to 13 of 16 to 39 unsaid points in the documents delivered
  with the product. The look's second list is about choices the *running product* shows, told in the *product's*
  documents.

**The trial, registered now.** The candidate is run from its branch (`run.py --source checkout`) on the four
cases, Codex Sol 6.2 medium. Read by script: the run ends delivered; the held-out checks; the minutes the new
step adds (the harness's per-stage timings); whether the look's file exists and names at least one tried step.
Read by the deep judge, as a fourth product beside 16.1's three where time allows: D3 to D5 against N (the same
ShipLoop without the step). The candidate is worth proposing to the owner if, on at least three of four cases, it
is not behind N on any of D1 to D5 and ahead on at least one, at under 1.5 times N's minutes; otherwise it is
reported as tried and not proposed. This is one run a case and reads as a first look, not a rate.

### 16.3 The candidate's design, its outside review, and two amendments made before any candidate run (2026-11-22 11:01)

**Where the look attaches, and the evidence for it.** A read-only map of ShipLoop's stage machinery (an Explore
agent, 85 tool calls) and the per-stage timings of this morning's four fresh ShipLoop runs
(`~/e2e-runs/d20261122-b54ea4/*/metrics.json`) settle it:

- No stage asks the session to start the assembled product and use it. `document` runs one step's changed
  behaviour, the Improve reviews trace entry points in code, `system-test` runs the planned commands,
  `release-verify` runs the consumer checks.
- The stage whose goal is "assess the product against the request", `product-acceptance`, took **5, 6, 6 and 46
  seconds** in the four fresh runs (expenses, chess, tickets, Grokbot). It closes from evidence already recorded.
- Those runs have no Improve review at all (the harness's default), so a design that extends the end-of-work
  review would not run in the trial; and a new stage would break the 23-stage count that some twenty suites pin.

So the candidate adds no stage. `product-acceptance` gets one duty (use the running product as its users and
operators would, and record each thing done as a row of a new result field `look`: works, shortfall or untold
choice), one script check with a routing rule (a `done` result is refused while a high or medium shortfall or an
untold choice is listed; they go to **one** corrective work item through the existing `add-work`, so the inner loop
supplies the failing-first test, the fix and the document edit), and an answer pass after that item (no new look;
each routed row answered `closed` with a test file that changed since the look, or `told` with a line the script
finds in a delivered document). **One look a run, and no limit added to any loop.** Full text:
`docs/experiments/ratchet-vs-shiploop-20261121/shiploop-look/DESIGN.md` on the candidate's branch.

**Outside review** (Sol 6.2 at max, 8 minutes; question and verbatim answer beside the design): "Change first."
Seven changes. Taken: a test of the actual claim (below); discovery narrowed to what a person who uses or runs the
product would notice, with the checklist conditional on the request and the product; routing and closure made
executable (the corrective item must name every routed id; `closed` and `told` checked against the tree); the
hand-off to a retry printed whole. **Not taken, on purpose, and recorded as the two options the trial can call
for:** (1) a script-owned receipt that the look happened, which the review ranks first. No cheap script-run form
exists for a page action, and the owner's standing rule is the plain rule first with the guard offered as the
option; the trial instead reads, from the session's own command record, whether the product was started during the
stage. (2) A direct edit of the delivered documents at acceptance when a look finds only untold choices; it would
change the stage's read-only contract and the engine's commit route.

**Amendment a, the cost bound.** 16.2 said "under 1.5 times N's minutes". I set that without checking section
15's own numbers: the look-and-fix sequence this candidate reproduces cost 2.0, 1.5, 2.7 and 2.1 times N (20.3,
16.4, 27.9, 61.7 minutes against 10.1, 10.7, 10.5, 28.7), so the bound would have rejected the result that
motivates the candidate. The claim is "near Ratchet's result at well under Ratchet's cost": the bound is now **at
most half of the fresh Ratchet run's minutes for the case**, with the ratio to N reported beside it.

**Amendment b, the rule.** The review showed what 16.2's rule lets through: three small cases each gaining one
reading while Grokbot, the one case with a measured behaviour gap, does not move, and no comparison with Ratchet
at all. The rule is now, all four required:

1. every candidate run ends delivered and passes every held-out check;
2. against N, on at least three of four cases not behind on any of D1 to D5 and ahead on at least one, **Grokbot
   among them, ahead on D4 or D5**;
3. against the fresh Ratchet final, "nearly competitive" by section 10's rule on at least two of the three small
   cases;
4. at most half of the fresh Ratchet run's minutes for the case.

A reading on its margin (one item either side of a two-item margin, or 45 to 55% of Ratchet's minutes) is not
decided by one run: that case is run once more first. The candidate's delivery is audited in one round with N and
the fresh Ratchet final (the candidate takes S's place in a layout like `CASE-fresh`), so both comparisons are read
from the same audits. S' (a separate observer, a stronger fixer) is a different intervention and is read beside
the candidate, not as its target.

Both amendments are made before the candidate exists as code: an Opus worker at xhigh began building it at 11:00
on its own branch, off `main`.

### 16.4 The fresh Ratchet runs ended; Grokbot's stopped as stuck, and a second Grokbot run is registered (12:15, before any Grokbot audit has answered)

The four runs of 16.1 (runs root `~/e2e-runs/d20261122-ac4afc/`, started together at 10:44:05), by `measure.py`:

| Case | Minutes (last night) | Stop | First build, minutes | Held-out checks, first build / final | Output tokens |
|---|---|---|---|---|---|
| shared expenses | 47.4 (46.4) | cycle limit, 3 cycles | 9.4 | 6 of 6 / 6 of 6 | 113,490 |
| chess | 45.5 (37.2) | cycle limit, 3 cycles | 10.1 | 10 of 10 / 10 of 10 | 108,955 |
| ticket assignment | 72.1 (100.4) | cycle limit, 3 cycles | 11.6 | 18 of 18 / 18 of 18 | 146,279 |
| Grokbot | 85.1 (162.3) | **stuck in cycle 1** | 21.6 | 49 of 49 and 28 of 28 / the same | 122,201 |

**Grokbot's fresh run is not a full Ratchet run, and why.** Its specification wrote clause C-2, "The application
works on the declared Node.js runtime: start the app on Node.js 22, the minimum supported version declared by the
project" (source: the starting files' `package.json`). Its acceptance test for that clause asks for a Node.js 22
executable; this machine has Node.js 26 only, so the test fails with "Node.js 22 is unavailable. Set
ACCEPTANCE_NODE22 to an installed Node.js 22 executable." The first gate failed on C-2 and C-18; the first fix
closed C-18; three fix sessions could not make a missing runtime appear, and the loop stopped as `stuck` with its
own gate failing on that one clause (110 of 111 pass). **No closing look ever ran** (sessions: spec, plan, build,
tests, fix, fix, fix), so this product is a first build with the heavy test pass and three fixes, not the
three-cycle product of last night. It still passes every held-out check.

What this is: a real outcome of the tool, and a failure mode of its own. A clause the environment cannot satisfy
has no way out of Ratchet's gate (ShipLoop has one: an outcome it cannot observe here is listed as `unverified`
with an owner and a due stage, and the run goes on). The clause itself is an artificial mandate in the sense of
the owner's rule of 2026-11-18: nothing in the request asks for a version floor to be proven, and last night's
run of the same request wrote no such test.

**Decision (routine: launching a verification run).** The stuck product is audited and judged as registered in
16.1; it is the fresh run. But it cannot answer 16.1's question for Grokbot, whether section 15's "still behind"
holds against a fresh *full* Ratchet run. So one more fresh Grokbot Ratchet run is started now, same commit, same
settings, in a new runs root, with nothing changed and no Node.js 22 supplied (supplying it would be tuning the
environment to one run's specification). If it completes its cycles, its final is audited in the same way
(three shares, cross-probe with the two ShipLoop products, the single reader, the Opus judge) and reported as
Grokbot's second fresh Ratchet run, beside the stuck one. If it sticks again, that is reported and no third run is
started. **Prediction:** it does not write the Node.js 22 clause as a tested clause and runs three cycles (of this study's two Ratchet runs of
Grokbot, last night's ran three cycles and today's stuck; I have not counted the pilot's).

Noted for the tickets audits: the auditors' `base/` folder is last night's copy of the starting files; today's
builders started from the fixture as changed on `main` yesterday (its tests listen on 127.0.0.1). One auditor read
that difference in `test/helpers.js` as the builder's edit and graded the item `yes` anyway; the cross-probe was
told the difference is not a builder's change.

## 17. Both tools fresh: results of section 16.1 (2026-11-22, audits 11:30 to 13:00; written 13:00; Grokbot's second Ratchet run is added below when it ends)

Status: firm for what was run (one fresh run of each tool a case); Grokbot's Ratchet side is a run that stopped as
stuck (16.4), so Grokbot's row is interim until the second run is judged.

Three products a case, all audited in this round by new sessions (41 Opus sessions in all: 9 audits for the three
small cases, 9 shares for Grokbot, 4 cross-probes, 4 readers, 4 judges; the inventories are section 12's,
unchanged): **S'** this morning's fresh ShipLoop 2.6.0 delivery after one look (Sol medium) and one fix (Opus
xhigh); **N** that fresh delivery itself; **L2** the fresh Ratchet run's final. Evidence:
`evidence/deep/CASE-fresh/`, `evidence/deep/deep.json` and `deep.md`, `evidence/fresh/` (the Ratchet runs' measure
and launch records).

### 17.1 The readings (S' / N / L2)

| | shared expenses | chess | ticket assignment | Grokbot (L2 = the stuck run) |
|---|---|---|---|---|
| D1 stated items built | 35 / 35 / 35 of 35 | 40 / 40 / 40 of 40 | 21 / 21 / 21 of 21 | 108 / 108 / 108 of 108 |
| D2 tests proved by breaking the behaviour | 5 / 5 / 6 of 6 | 6 / 5 / 5 of 6 | 6 / 6 / 6 of 6 | 3 / 3 / 4 of 6 |
| D3 unsaid points handled | 16 / 16 / 16 of 16 | 6 / 5 / 6 of 6 | 18 / 17 / 19 of 19 | 34 / 31 / 37 of 39 |
| D4 unsaid points told in the delivered documents | 13 / 0 / 12 of 16 | 4 / 0 / 1 of 6 | 17 / 10 / 17 of 19 | 20 / 2 / 16 of 39 |
| D5 reproducing medium defects (none high anywhere); low | 0 / 0 / 0; 2 / 2 / 2 | 0 / 1 / 0; 0 / 1 / 0 | 0 / 0 / 0; 2 / 3 / 1 | 4 / 6 / 3; 5 / 8 / 2 |
| The Opus judge, S' against L2 | S' somewhat | S' somewhat | same | L2 somewhat; a short task does not close it |
| **F-1, S' against L2, by the rule** | no difference shown | **S' better** (D4, D6) | no difference shown | no difference shown (D4 to S', D6 to L2) |
| **F-2, N against L2, by the rule** | L2 better (D4, D6) | no difference shown (judge: L2 somewhat) | L2 better (D3, D4, D6) | L2 better (D3, D4, D5, D6; judge: much) |
| S' "nearly competitive" with L2 | yes | yes | yes | yes by the rule; the judge says a short task does not close it |
| **F-3, minutes: S' (run + look + fix) / N / L2** | 20.3 / 10.1 / 47.4 | 16.4 / 10.7 / 45.5 | 27.9 / 10.5 / 72.1 | 61.7 / 28.7 / 85.1 (stuck) |
| S' as a share of L2's minutes | 43% | 36% | 39% | 73% of a run that stopped early |

### 17.2 What repeats

- **The three small cases repeat section 15 exactly**: level, S' ahead, level, with Ratchet's side now a run of the
  same day from the same commit and starting files. Unchanged ShipLoop is behind Ratchet on two of them and level
  on the third, again as in section 15, and for the same reason: it tells the customer little (0, 0 and 10 unsaid
  points told against 12, 1 and 17).
- **F-5, two audits of one product.** S' and N are the trees section 15 audited; different sessions read them
  here. Small cases: D1 and D2 identical on all six products; D3 within one item; D5's medium count identical;
  D4 within one item on five, and **three items apart on tickets' N (13, then 10)**, more than the two-item margin.
  Grokbot: S' 34 and 34 handled, told 17 then 20, medium defects 5 then 4; N 31 and 31 handled, told 2 and 2,
  medium defects **8 then 6**. Every verdict by the rule on the small cases is the same in both rounds. So: the
  rule's verdicts on the small cases are stable under a second audit; a two-defect difference on Grokbot is within
  what two audits of one product differ by, and section 15's "5 against 3" there could not carry a verdict alone
  (it did not have to: the judge agreed).
- **F-4, one Ratchet run against another.** L2 beside last night's final as audited in section 15: expenses told
  12 against 15, tests proved 6 and 6; chess tests proved 5 against 4, told 1 and 1; tickets handled 19 and 19,
  told 17 against 18; minutes 47.4, 45.5, 72.1 against 46.4, 37.2, 100.4. Close on every reading.

### 17.3 Grokbot: what the stuck run shows

The fresh Ratchet run never reached a closing look (16.4), and its product reads almost as last night's
three-cycle final did: handled 37 of 39 (38 last night), told 16 (18), medium defects 3 (3), tests proved 4 of 6
(4). Section 12 had already read last night's *first build* at 35 handled, 14 told, 2 medium defects. Three
readings of Ratchet's Grokbot product before or without closing looks, all close to its three-cycle final: **on
Grokbot, what puts Ratchet ahead of ShipLoop is in its specification, its build from that specification and its
heavy test pass, not in its closing looks.** The looks and extra cycles are what cost the second half of last
night's 162 minutes.

Against that product, ShipLoop with one look and one fix: ahead on told (20 against 16), one more medium defect (4
against 3, inside audit noise), three fewer unsaid points handled (34 against 37, 8 points of share, under the
ten the rule asks), and the judge prefers Ratchet's ("somewhat"; X leaves a reply pending for ever when it cannot be
saved, which blocks the conversation). By the registered rule that is "no difference shown"; I would not call it
level. The honest reading: **the gap is smaller than section 15 put it, and it is in failure handling**
(D-2, D-4, D-6, D-7, D-8 of this round's fifteen probed defects are present on both ShipLoop products and absent on
Ratchet's), which one look and one fix reduced (ten defects Ratchet's lacks on N, five on S') and did not close.

### 17.4 Predictions of 16.1, scored as registered

| Prediction | Result |
|---|---|
| Every fresh Ratchet final passes every held-out check | holds, 4 of 4 (6, 10, 18, 49 and 28) |
| F-1: on the small cases S' level with or ahead of L2 on at least two | holds, 3 of 3 |
| F-1: on Grokbot L2 is the better feature again | **fails by the rule** on the stuck run (no difference shown); the judge prefers L2; the second run decides |
| F-2: N behind L2 on D4 on at least three of four | holds: expenses, tickets, Grokbot (chess 0 against 1) |
| F-3: Ratchet's fresh minutes within 30% of last night's on at least three of four | holds: +2%, +22%, -28%; Grokbot -48% (stuck) |
| F-5: two audits agree within one item on D1, D3 and D5 on the small cases | holds |
| F-5: on Grokbot D5 differs by two or more on at least one product | holds (N: 8, then 6) |

### 17.5 Not shown

One fresh run of each tool a case; two deliveries of each a case in the whole study. The fixer of S' is Opus at
xhigh, stronger than either builder, and the look was done by a session that had not built the product (the
candidate of 16.2 tests both inside ShipLoop). D4 on one product moved by three items between two readers once.
The Grokbot comparison with a full fresh Ratchet run waits on the second run.
