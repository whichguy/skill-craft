# ShipLoop plan after E2E runs 1-8b (2026-09-27, revision 3)

Execute: ask

Supersedes the open items of `shiploop-e2e-verification-plan-2026-09-26.md`.
Governed by `test/shiploop_e2e/SPEC.md`: ShipLoop is a general SDLC execution
engine (Purpose); every change carries an anchor, a non-regression statement
and evidence (Change admission); E2E work runs depth-first in focused suites
and is confirmed by a breadth suite (E2E suites).

## Audit behind this plan

- The 1.7.0 lifecycle rule is phrased in game/technology terms ("a
  single-user game ... runs entirely in the client", "an opponent's hidden
  game state", a channel ladder naming server-sent events and WebSockets).
- Tool knowledge sits in script logic (test-count parsers per runner; the
  `npm run lint` / `make lint` fallback).
- The harness core recognises test runs by tool name and copies the
  requirement-ID pattern.
- Four commit code paths (three identity copies, one without a fallback, none
  screening for secrets); three hand-built loop contracts with two start
  mechanisms; Improve packets carry text for steps the scripts now perform.
- All eight live runs probed one style (browser UI over an HTTP service).

## Suites

| Suite | Style | Cases | Use |
|---|---|---|---|
| `web-service` (focused) | browser UI over an HTTP service; follow-on feature in the same repository | battleship, battleship-scoring | depth loop for P3-P5; has baselines (runs 7, 8b) |
| `cli-files` (focused) | command-line tool over input files, report output, no server | new case | baseline only in this plan |
| `stateful-service` (focused) | service with persistent state and concurrent writers | new case | baseline only in this plan |
| `breadth` | one case per style | battleship, cli case, stateful case | generality gate before a release is called good |

## Plan

Each item: **Anchor** (clauses, motivating evidence) / **Non-regression**
(what it could touch, why it does not weaken it) / **Evidence** (hermetic
tests, then the suite that confirms it live).

### P1 Harness suites (harness only)
- `cases.json` gains `style`; a `suites.json` (or suite section) names focused
  suites per style and the breadth suite; `run.py --suite <name>` runs a
  suite's cases in order (follow-on cases from their predecessor), and each
  case's results append to a per-case baseline history.
- Anchor: SPEC "E2E suites"; eight runs of one style could not show S-13.
- Non-regression: `--case` keeps working unchanged; existing result.json
  fields keep their meaning; no ShipLoop code touched.
- Evidence: self-test (suite order, follow-on chaining, baseline append);
  one `--suite web-service` dry run with fake hosts.

### P2 Case-agnostic harness core and a glue metric (harness only)
- Count test runs from ShipLoop's own verify records in the run directory;
  reuse ShipLoop's requirement-ID pattern; add `model_glue`: shell writes into
  ShipLoop-owned paths (run, workspace, receipts), hand-built loop JSON, and
  commit/rename/mkdir commands there.
- Anchor: SPEC harness rule "core is case-agnostic"; S-4, S-5 made
  measurable; S-12 (no copied pattern).
- Non-regression: existing metrics keep their names; `test_runs` changes its
  source, so the learnings note records the new definition; glue counts only
  ShipLoop-owned paths, never product files.
- Evidence: self-test with synthetic events; recompute metrics for runs 6-8b
  and compare with their recorded values (test_runs may differ; the reason is
  noted).

### P3 One commit path with a secret screen (ShipLoop)
- `commit_paths(repo, paths, message)` used by the knowledge-home commit, the
  integrate commit, `improve-commit` and workspace bootstrap; skips and names
  any text file the privacy screen flags; configured identity, else the
  workspace identity.
- Anchor: S-12 (four copies), S-11 (commits must never carry secrets onto the
  user's branch), S-5.
- Non-regression: same staged paths and messages as today for clean files;
  the knowledge-home commit gains the identity fallback it lacked (fixes a
  failure, changes no success path); a flagged file is skipped, never fails a
  transition.
- Evidence: per-caller tests through the helper; a token-bearing file is
  skipped and named; `web-service` focused suite: `committed` still passes
  and glue stays 0.

### P4 One loop-contract builder (ShipLoop)
- Test loop, quality loop and Improve contracts are built by one module; the
  Improve exit condition includes the stage's own `done_when`. The start
  mechanisms stay as they are (the `loop-start` verb is deferred: those starts
  failed zero times in runs 7/8b).
- Anchor: S-12; S-10 (stage-specific, checkable exit conditions).
- Non-regression: test and quality contracts are byte-identical to today's
  (asserted); Improve contracts keep every field and gain stricter exit text,
  which may add review passes (intended by S-10); saved runs keep their frozen
  contracts.
- Evidence: contract equality tests for test/quality loops; Improve contract
  contains done_when; `web-service` focused suite: turns and cost compared
  with runs 7/8b, any increase attributed to review passes.

### P5 Improve packets state each obligation once (ShipLoop)
- Remove the instructions for steps the scripts now perform (hand-freezing
  context fields, resource lists, runtime start syntax, rename steps); keep
  what the model must do (write the opening, run the printed command, follow
  the runtime packet, recover), once each.
- Anchor: S-7 (printed and filed text not bloated); S-6 (each obligation
  still present).
- Non-regression: a packet-contract test lists every obligation an Improve
  packet must still carry and fails if one disappears; stage packets
  untouched.
- Evidence: packet-contract, delegation and v3-guidance suites; Improve
  packet sizes before/after; `web-service` focused suite completes with no
  new ShipLoop failures.

### P6 Baselines for the new styles (harness + runs)
- Write the `cli-files` and `stateful-service` cases (product checks only in
  `cases.json`), then run each focused suite once on the current release to
  record its baseline. No ShipLoop change is judged against a style until its
  baseline exists.
- Anchor: SPEC "E2E suites" (baselines, breadth gate); Purpose.
- Non-regression: new cases only; nothing existing changes.
- Evidence: two runs with results in the per-case history.

### P7 Release and breadth gate
- One release for P3-P5 after the full hermetic tier; host updates; then the
  `web-service` focused suite until it passes, then the `breadth` suite.
- Acceptance: every verdict passes in every style; 0 ShipLoop command
  failures; glue 0 for mechanical steps; per-case cost no worse than its
  baseline, or the increase attributed to a stated intended change.

### P8 Engine neutrality (ShipLoop prompts/cards; owner review first)
- Restate the 1.7.0 lifecycle rule in SDLC terms (placement follows who must
  see and change the state and how fresh it must be; information a user must
  not see stays out of that user's reach; lightest channel meeting the stated
  freshness), with at most one labelled example; vary the one-domain
  illustrations (`game.js`, Tic-Tac-Toe, repeated Salesforce).
- Anchor: S-8, S-13, Purpose.
- Non-regression: the safeguard floor and every decision the rule requires
  are kept word for word in meaning; the owner's architecture-rubric
  scenarios are rerun and must not regress.
- Evidence: rubric rerun; breadth suite.

### Later, separate
- **Tool knowledge into one catalog** (S-8): move per-runner count patterns and
  the lint fallback into a catalog module; behaviour-preserving; existing
  parser tests unchanged.
- **Grok refusal probe**: understand lost sessions; any outcome must be
  host-neutral guidance, never host logic (S-8, S-13).
- **Until Loop short output** (upstream): largest context driver (S-7);
  another repository, owner decision.

### Dropped
Skipping skill stages (2-6 turns), trimming planning (planning size is fine in
files, S-7), `--always-approve` (unrealistic host), printing whole packets
(contradicts S-7), a Battleship-specific hidden-state check (replaced by a
generic review question and case-level checks only where a request has
hidden information).

## Order

P1 -> P2 -> P6 (baselines for new styles, current release) -> P3 -> P4 -> P5
(each iterated on the `web-service` focused suite) -> P7 (release, breadth
gate) -> P8 (owner review) -> later items.

## Negative implications and how each is handled

| Change | Risk | Mitigation |
|---|---|---|
| P1 suites | More runs and cost | Focused suites run only the style under work; breadth runs once per release |
| P1 baselines | Comparing noisy single runs | Compare per case against its own history; repeat a case when a result contradicts the trend |
| P2 metric change | `test_runs` values shift, breaking comparisons with earlier runs | Recompute runs 6-8b with the new definition and record both |
| P2 glue metric | Misclassifies product work | ShipLoop-owned paths and mechanics only; commands listed for review |
| P3 secret screen | Fixture tokens flagged | Skip and name the file; never fail the stage |
| P3 identity | Fallback author reaches user history | Only without a configured identity; stated in the handoff |
| P4 stricter Improve exits | More review passes and cost | Intended (S-10); attribute cost changes in the suite comparison |
| P5 trimming | An obligation lost after context loss | Obligation list asserted by test |
| P6 new cases | Failures caused by the product, not ShipLoop | Review against the spec; product defects are evidence only |
| P8 rewording | Safeguards weakened | Owner review and rubric rerun |
| All | Concurrent releases by other sessions | Fetch before each step; version gate |
| All | Machine sleep | caffeinate during runs; discard timings across a sleep gap |
