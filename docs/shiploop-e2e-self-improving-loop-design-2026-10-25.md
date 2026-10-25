---
Execute: ask
Status: design proposal; nothing implemented
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

## Phases

| Phase | What | Built on | Size | Adopt when |
|---|---|---|---|---|
| P1 | `scorecard.py` over the existing records, plus a versioned id; backfilled on the 2.9.0 gate runs (no model) | `metrics.py`, `quality.py`, `fidelity`, `arms.py` | S–M | It reproduces the gate's verdicts, and its parts agree with the run reports |
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
