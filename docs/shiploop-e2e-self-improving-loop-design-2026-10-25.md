---
Execute: ask
Status: design proposal; P1 (scorecard.py) built on feat/e2e-scorecard-b79a33, the rest not implemented
Directive: owner, 2026-10-25
Builds on: docs/shiploop-e2e-runner-review-plan-2026-10-24.md, test/shiploop_e2e/SPEC.md
---

# A self-improving E2E loop for ShipLoop (design, 2026-10-25)

## The directive

> A recursive, self-improving ShipLoop that generalises and meets the purpose of an accurate and efficient SDLC: it turns
> any given prompt into working code, or adapts a repository with a feature into fully enterprise-grade working code.

So the E2E loop is not just a test. It is the **training loop** for ShipLoop.
- It must measure the two jobs, greenfield prompts and brownfield features, against one objective.
- Each change it promotes must improve that objective on cases it was not tuned on.
- Each step must run with as little human involvement as the owner's release gates allow.

## What the loop optimises: one scorecard

The objective is a script-computed **scorecard**, with an id like `quality.py`'s operator catalogue. Two scorecards are
compared only when their ids match.

| Part | What it measures | Role | Source today |
|---|---|---|---|
| Accuracy | Hidden acceptance checks pass; the base repository's own tests still pass (brownfield); test strength (mutation ratio) | **floor**: never traded away | `checks`, `quality.mutation`, `quality.acceptance` (Checkers only) |
| Enterprise grade | Scripted rubric: lint clean, tests run in CI config, input validation, errors handled, no secrets, docs and run instructions, migrations where the schema changed | **floor** | not measured |
| SDLC fidelity | Every stage did its row; evidence classes; no skipped gate | **floor** | `fidelity` block |
| Efficiency | Minutes, cost or tokens, turns, refusals, re-orientation minutes, Improve share | **target**: what a change improves | `metrics.json`, baseline rows |

The rule follows the owner's eval priority (quality first, then tokens, then time). A change is promoted only if every
floor holds and the target improves beyond the A/A spread. Efficiency can never buy a lower floor.

## What the corpus must look like

| Today (`cases.json`, 12 cases) | Needed |
|---|---|
| 11 greenfield prompts; one follow-on (`battleship-scoring`) built on ShipLoop's own output | Both jobs: **greenfield** prompts and **brownfield** features on repositories ShipLoop did not write |
| One held-out oracle (`checkers_accept.py`); most checks read the response shape (E2) | A **hidden oracle** per case, never shown to the model or the improver |
| No enterprise requirements, except seat-reservations (concurrency) and the Salesforce cases (deploy) | Cases that require auth, persistence, a migration, CI and error handling |
| Fixes judged on the case that exposed them (chess runs 3 → 4 → 5) | **Three pools**: dev (tune on it), holdout (judge generalisation; its transcripts are never read by the reviewer), canary (the cheap gate) |

Brownfield already exists at step scale: `step_cases.json` has seven cases on `fixtures/node-base`, three of them with
planted defects (`seeded_defects.py`). The gap is brownfield at case scale.

**Example brownfield case:** "Add CSV export of tasks to this Flask todo service; only the owner of a task may export it."
- Base: a small fixture repository at a pinned commit, with its own 30 tests.
- Hidden oracle: the export works, other users get a 403, and quoting is correct.
- Regression oracle: the base's 30 tests still pass.
- Rubric: no new dependency outside the base's manager, the route is documented, the input is validated.

## The loop (one epoch)

1. **Run** the dev pool, n=2 per case, one driver (Grok 4.7 medium or Claude Sonnet) per epoch, serially where minutes
   are compared.
2. **Score** every run with the scorecard; the script writes it, no model.
3. **Find**: script records first (refusals, dodges, fidelity gaps, stage minutes), then one valid review (the 10-16 rule).
   Each finding names its SPEC clause and the run line that shows it.
4. **Rank** by expected gain × breadth (how many styles it touches). Rejected and deferred findings are journaled.
5. **Try** each candidate on the cheapest rung that shows it: replay (no model) → step slice → small case → full case.
   The arms are control and candidate, plus an A/A pair, chosen by `arms.py` (hard gates first, then bytes, then time).
6. **Batch** the winners into one release candidate, admitted by SPEC Change admission.
7. **Promote**: run the holdout pool and the canary. Release only if no floor drops and the target improves. Otherwise
   drop the candidate that lost and journal why.
8. **Record**: LEARNINGS, baseline rows, the release-gate line, and the next epoch's coverage map.

**The recursion (a later phase):** in step 5, the candidate itself is built by a ShipLoop run on skill-craft, whose
prompt is the ranked finding. It is judged by the same hermetic tests and the same holdout. ShipLoop then improves
ShipLoop through its own SDLC, and an engine that cannot do that shows it in its own scorecard.

## Guards against gaming

- Hidden oracles are never in a prompt, a packet or a review brief. `quality.held_out_seen` already detects a leak.
- The holdout is frozen per epoch and rotated each quarter. Its transcripts are not read by the reviewer or the improver.
- Scorecard and oracle changes go through SPEC admission. A changed scorecard gets a new id, and old figures are never
  compared with new ones.
- A fidelity floor stops "faster by skipping a stage". All verdicts must pass before a case counts.

## Setup and teardown: no run starts polluted (owner, 2026-10-25)

> We need a test setup and test teardown. Teardown can be done after inspection, so it doesn't have to be synchronous,
> but we just want to make sure it's not polluted when we run.

Pollution this review found, each of which made a verdict or a figure wrong:
- **E4:** a check deleted the product's committed `page.html`. The verdict was false, and the mutation baseline went red.
- **E1:** sixteen Grok slices ran beside chess run 5, which spoiled its timing.
- **Leftover processes:**
  - run 5's `shiploop_progress.py --watch` outlived its run, as on 2026-10-18;
  - two `shiploop-e2e.test.py` processes from another worktree were alive after 13 and 14 hours.
- **Kept platform state:** a Salesforce app kept in org `de` made the next preflight refuse.
- **Accumulation:** `~/e2e-runs` holds 13 GB over 65 runs, and the repository has 52 worktrees.

**Setup (synchronous, before a run starts):** one preflight that refuses or warns.
- It already refuses stale listeners under another case's folder, a non-empty `work/`, a kept platform app, and a red CI on
  origin/main.
- It now prints the live harness runs under the runs root (the `concurrent` line).
- **To add:**
  - orphaned processes from earlier runs (an ancestor that is gone, a command line under `~/e2e-runs`);
  - a timing run refuses to start beside live runs of the same driver, unless told it may;
  - a disk floor.

**Teardown (asynchronous, after inspection):** a run is torn down only once it is inspected. That means its `result.json`,
`metrics.json`, scorecard, review export and journal entry exist, and an `inspected` marker names the commit that recorded
them. Then a `teardown` step does the following, and records what it removed:
- stops what the run left;
- runs the case's platform cleanup;
- removes the heavy parts (`work/`, `home/`, `marketplace/`, platform deploys), keeping the compact records;
- removes the harness's temporary worktrees.

A live run (its lock is held) is never torn down.

**In the scorecard (P1, built):** the validity block marks a polluted run as not comparable (overlap, resumed, mixed host,
leftovers, a work tree changed after delivery), so pollution is seen even before setup refuses it.

## Live triage: fatal now, or run to the end (owner, 2026-10-25)

The batch rule (2026-09-27) stays. A run is stopped only when it is fatal, meaning it cannot continue or cannot produce
usable evidence, or to apply a change certain not to affect planning. Everything else runs to the end, then is evaluated
and fixed. Triage makes "fatal" a reading of records, so the 3.5-minute monitor can decide it. Its thresholds start from
these rules, then take the `inner-loop` session's learnings (asked 2026-10-25).

| Signal (read live from the run folder) | Example | Call |
|---|---|---|
| The engine is honestly `blocked` (present) by the environment, such as the host's own permission mode | run 5a: Grok 1.0.70's auto mode refused `sf project deploy` ("Auto mode blocked this action … remote stateful mutation"); the events and stderr say "Auto mode blocked" or "permission required" | **fatal**: nothing more to learn; fix the environment, then rerun |
| The same refusal first line three or more times on one `--action`, with no accept between | a refusal loop; identical text means looping, changing text means converging (a judgement) | **fatal** when identical |
| The host process is gone while `run.py` is alive and no `resume-N.txt` appears (`pgrep -f "<host> --cwd <run>/work"`) | run 5b after a 9.8 h laptop sleep | **fatal**: resume in place |
| No new events for over 15 min while the host is up (the `events.jsonl` mtime) | hung inference or a dead connection | **fatal** |
| The interpreter or host build changed mid-run (the launch record's `tools.python3` and `host_build` against now) | run 5a: Homebrew swapped Python, and `run.py` crashed at the end | **fatal**: invalid evidence |
| A required action blocked by the harness's own guard (`platform/sf-calls.jsonl` `decision: denied`) | — | **fatal**: a harness defect; fix it, then resume |
| A neighbour starts on a timing run, or the product tree changes under a check | E1, E4 | **not fatal**: run on for the verdict, and mark the timing or verdict invalid |
| Refusals fixed in stage; send-backs (about 6-10 min of rework each); long but converging Improve reviews (each pass's Changed line differs); paired Grok restarts | runs 5b, 3 and 4 | **run to the end**: this is the evidence |
| The deadline projection exceeds the remaining budget | runs 3 and 4 at the 4 h cap | **not fatal**: plan the resume budget |

Sources: the rules above come from the batch rule and from the `inner-loop` session, which watched chess runs 5a and 5b
live (2026-10-25; its notes are `chess5-report/run5-observations.md`, which moves into the repository with the run-5
report). A script can read every signal in the first column. Two calls need a person: whether a repeated refusal is
converging or looping, and whether a `present` block is a real owner action or the environment.

`triage.py <run>` (read-only) prints OK, WATCH or FATAL with the record behind each reason. The progress card shows it.

## What the scorecard should measure next (scorecard/2 candidates, from `inner-loop`, 2026-10-25)

Each needs a record the harness does not write yet, or a reader that does not exist yet. Each would change the scorecard's
id.
- **Prepare harness_runs:** each evidence file shows a test result line (a count, PASS or FAIL, ok or not ok). In 5a it
  passed with none; 5b's showed "1 passed". A browser probe page that said "This is not … the slChessBoard component" was
  accepted.
- **Discrimination of the spec's `primary` field:** the share of R-<n> marked primary (5a: 7 of 7, 5b: 13 of 14).
- **Send-backs per item and their rework minutes:** the cost of the honest route.
- **RED unobserved:** focused commands left out as remote, and items whose mutation check was skipped as all-remote.
  Hosted code has no mutation coverage by construction.
- **F5 at the end-of-work Improve:** code-changing commits with a `Regression test:` line whose test ID a test file in
  the commit holds.
- **Improve passes per review, and whether each changed anything.** `metrics.improve_reviews` reads 0 on 2.9.0 runs with
  10 Improve children and needs a reader that follows the Improve route first.
- **The environment per run, in validity:** active against wall time, an interpreter swap, a sleep gap. scorecard/1
  already marks a host build that changed within a run.

## Phases

| Phase | What | Built on | Size | Adopt when |
|---|---|---|---|---|
| P1 | `scorecard.py` over the existing records, plus a versioned id; backfilled on the 2.9.0 gate runs (no model) | `metrics.py`, `quality.py`, `fidelity`, `arms.py` | S–M | It reproduces the gate's verdicts, and its parts agree with the run reports |
| P1b | Setup and teardown: orphan, concurrency and disk checks in the preflight; `teardown.py <run>` after an `inspected` marker, asynchronous, recording what it removed | `listeners.py`, the platform cleanup, `environment.alive_runs` | M | A dirty fixture (an orphan watcher, a live neighbour, a deleted product file) is refused or marked; a torn-down run still scores from its compact records |
| P1c | Live triage: `triage.py <run>` (OK, WATCH, FATAL) from the live records, on the progress card | `sessions.jsonl`, `fidelity.refusals`, `state.md`, baselines; the inner-loop session's learnings | S–M | Replayed on chess runs 3-5 and the gate runs, it flags run 5a's auto-mode block as FATAL and runs 3, 4 and 5b as run-to-the-end |
| P2 | Corpus v2: hidden oracles for battleship, seat-reservations and csv-report; three brownfield cases (a Node service, a Python CLI, a stateful service) on fixture bases with their own tests and an enterprise rubric; the dev, holdout and canary split in `suites.json` | `checkers_accept.py`, `fixtures/node-base`, `step_cases.json` | M | Each oracle rejects a constructed broken product and accepts the saved real deliveries (the E2b method) |
| P3 | The epoch driver: revive `iterate.py` as the runner (or retire it for `epoch.py`), with promotion by `arms.py` and an epoch report card | `iterate.py`, `review.py`, `arms.py`, `owner_page.py` | M | One epoch end to end on the canary and dev pools, with the decisions in the journal |
| P4 | Dogfood: step 5's candidate is built by ShipLoop on skill-craft | ShipLoop itself | L | P3 has promoted at least two candidates by hand that the loop also picks |

## Decisions for the owner

- n per cell (2 proposed) and the holdout size (one case per style proposed).
- The driver per epoch: Grok 4.7 medium (owner, 2026-10-25: Luna skipped) or Claude Sonnet, which is about 10× faster on
  the same case and so the cheaper dev driver.
- Which brownfield bases: synthetic fixture repositories in `fixtures/` (products are never committed; a base is input,
  not product), or pinned public repositories cloned at run time.
- A budget per epoch, and whether a release may be cut by the loop or only proposed to you.
