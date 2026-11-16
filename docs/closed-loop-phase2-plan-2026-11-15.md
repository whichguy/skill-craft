# Phase 2: the ShipLoop adapter for closed-loop (plan, 2026-11-15, version 3)

**Status: draft for the owner's decisions, revised after two Sol max reviews** (`docs/experiments/closed-loop-phase2-review-20261115/`;
the nine findings of the first and the seven of the second, with what each changed, are in appendix B). **The second review's verdict on version 2
was "not ready". This version folds in all seven of its findings and has not been reviewed again**; gate G1 (section 4) puts a review of the
facade's contract, with code and tests in front of the reviewer, before any compute is spent. Grounded on origin/main
`e0d4ec65b1f27c56a4ee9703abca69d4a52cb36d` (skill-craft 2.42.0), reviewed at `579af232f25dcc93fcf0ad9a21d5f1915701c73a` and rechecked at
`19d01d5048113c8b44f328aa99b85f1facb32887` (skill-craft 2.42.1): the commits since touch ShipLoop's prompt wording (a Backchain-check sentence) and journals, and
nothing under `test/shiploop_e2e`, `skills/closed-loop`, `test/suite_catalog.py` or `.gitignore`.
`closed-loop` 0.1.0 is released (skill-craft 2.41.1; first plan `docs/closed-loop-plan-2026-11-15.md`, journal
`docs/closed-loop-journal.md`). Consumers: the owner (the decisions in section 6) and the session that builds it. Every fact has a
command in section 9; what I have not verified is in section 8.

**Built (2026-11-15, after the owner's "Approve, start W1"): W1 to W3 are in `test/shiploop_e2e/adapter/`** (facade, manifest, allowlist,
README) with three test suites, one of which runs the REAL loop with fake hosts and one the real orchestrator through the facade. The build
changed this plan in eight places, each a recorded decision in the journal's round R7: a failed or cancelled step publishes no tip; a cycle
ends the step (3.3 said a promotion); only a false attribution makes evidence invalid (3.4 said "attribution or timing"); `cleanup` also stops a
live step's worker; the runs-root variable is removed from the engine's environment; the strict outcome and the baseline predicate are the harness's
own functions run in a bridge process (3.1 said re-stated); `grading.sensitive` and `improver.invocable` are not declared (3.6); and a probe works
in a clone under the state folder. Read this plan for the reasons and the journal for what was built. Gate G1's review (round 3 in
`docs/experiments/closed-loop-phase2-review-20261115/`) said "not ready" about the first build: eleven findings, all fixed with tests (journal round R8).
Round 4 verified those fixes and said "not ready" again: seven more defects, all fixed with mutation-checked tests (journal round R9).
Round 5 verified those and said "not ready" a third time (six defects, one a regression of round 4). **A replan is proposed in the journal (round R10,
"Replan after round 5") and waits on the owner**: remove the four kinds of code the defects keep coming from instead of patching each one, check the
engine's git identity before any step (a real step on this machine would have failed after its subject run), then one verification of that diff.
Separately, the real-engine suite has failed on Linux CI from its first push: the harness passes its 175 KB reviewer prompt as one argument, over
Linux's 128 KiB limit (journal R10; the replan's step 2).

## 0. The recommendation in one screen

**Keep the route: a thin program outside the scoring files (a *facade*) drives the E2E harness's existing qualified loop through its
command line and reads its artifacts. No harness edit, so no new scoring identity.** Two Sol reviews confirmed that continuing a loop from a
positioned checkout works for committed history, and between them found sixteen ways the first drafts were not yet *safe*: readiness
claims the skill does not have; facts that could never let the certificate converge; findings lost when a step is killed; model
processes that survive a kill; and a smoke plan the orchestrator would stop after one iteration. Each is folded into the design below,
and **no real compute is spent until a list of model-free tests passes** (G1).

The first real compute, in order: a one-off readiness proof (a real `hello` run, because the skill's own start rule demands that
`cases.runs` be proven by a run), then **one** smoke iteration through the orchestrator. The smoke **ends after one iteration**: three
material records that name no case are owner-gated, and the orchestrator stops a campaign `blocked` as soon as only owner-gated records
are left (`analyze` and `plan_next`, row 16). It proves the plumbing at a quiet window of 1, with C1 the only failing check. The
two-iteration path, the kill-and-resume check on a second step, and anything that costs hours wait for your decisions on the records, which
is why those come first.

What I need from you, in order: the five record decisions in appendix A (they unblock everything and cost no compute), then the
choices in section 6. Say "approve" and I take every pick in that table.

## 1. What I verified, and what it changes

| # | Finding | Evidence | Effect on the plan |
| --- | --- | --- | --- |
| 1 | The harness already runs qualified cycles and has a durable controller for one cycle's attempts. | `iterate.py --qualify` calls `cycle.loop`; `cycle.qualify`; `epoch.py` header | Phase 2 wraps it. |
| 2 | Every invocation starts a loop in a new worktree from the HEAD of the checkout that runs the script; no base reference, no resume. | `iterate.new_worktree`; `cycle.loop` (`name = shiploop-loop-<hex>`, `out.mkdir(exist_ok=False)`) | The first plan's "continuation problem" stands. Row 3 is why it need not be fixed in the harness. |
| 3 | The files that fix the scoring identity are protected by *detection*, not prevention: a change to the grading digests and a tool call that names a held-out file are caught; a read that never names one is not. The files a loop commits (ledger, LEARNINGS, evidence) and any `adapter/` subdirectory are outside the identity. | `boundary.py` docstring, `CANDIDATE_PREFIXES`, `HARNESS_PREFIXES`; `boundary.qualification_snapshot`; `learning_records` header | A checkout positioned at the loop tip continues the loop under the same identity (verified with plain Git and, by Sol, with the real worktree functions and stubbed models). |
| 4 | The October calibration no longer matches. | `spread.scoring_digest` for csv-report and seat-reservations: `7888015a…` now, `fccc62fe…` recorded (`docs/experiments/e2e-calibration-20261031/run-01/calibration.json`; Codex Terra high, 16 attempts sealed, k = 3, tolerance 0.45 on tokens) | A fresh calibration is a prerequisite for a measured tolerance. |
| 5 | 14 material ShipLoop records are unresolved (appendix A). **Three name no case** (`355e5e` deferred, `d73cd8` open, `583e17` owner), and `check_c1` counts a record without cases against every scope. | `learning_records.current()`; `closed_loop.py` `check_c1` (`related = rec.get("cases")`) | No scope can converge, `hello` included, until you decide those three. The first plan's claim that a smoke scope could converge was wrong. |
| 6 | Run lengths, medians for the selected profiles: hello 10.6 (Terra high), 11.6 (Terra xhigh), 12.2 (Sonnet) minutes; csv-report 16.2 and 17.8; user-listing 10.8 and 16.4; battleship 26.1 (Sonnet); roundtable-agent-work 31.9 (one run). **Terra high has 22 hello rows, 13 user-listing, 4 csv-report and 0 seat-reservations.** | `baselines.jsonl`, 237 rows | Cost model (section 5). The "87 rows" figure in the first draft was an aggregate over cases and does not establish comparability for the S1 cases. |
| 7 | The qualified cycle does not run the quick test tier; only the exploration loop does. | `iterate.quick_suite` is called at `iterate.py` line 497 | The facade produces the `tier` fact itself. |
| 8 | Promotion is decided by a script from scorecards, with no model in the decision (model reviews qualify the evidence it reads). | `promotion.py` header; `_strict_outcome` | The first plan's decision 8 does not arise. |
| 9 | New ShipLoop runs call no Backchain child since 2.42.0. | `SPEC.md` S-10 amendment; `27fa9c92` | The base must be at least 2.42.0 (2.42.1 is current). |
| 10 | The reviewer's and improver's history lookup searches **every** `refs/shiploop-loop/*` ref in the repository for the record id. | `review.py` (the `git log … --glob=refs/shiploop-loop/*` call) | A shared repository lets another session's loops change this campaign's context. The evaluator checkout must be its own clone (3.2). |
| 11 | `run.py` appends each run's baseline row to `baselines.jsonl` **in the checkout that runs it**, a tracked file. | `run.py` (the `baseline_file.open("a")` block) | The evaluator checkout is dirty after every run; its rows must be captured and the file restored (3.2). |
| 12 | The cycle's epoch launchers run with `cwd` set to the evaluator checkout, not the loop worktree; reviews of a cycle's attempts run one after another. | `cycle.launch_all` (`Popen(… cwd=ROOT …)`); `cycle.review_all` | Cleanup cannot select by working directory; a cycle's wall time includes serial reviews (section 5). |
| 13 | `SIGKILL` of a step can leave material findings only in the dirty loop worktree, staged or uncommitted, with the output folder empty. Sol's witness uses a stubbed cycle: it shows the window exists, not that every real kill falls in it. | `round1-sol-kill-witness.json`; `cycle.commit_entry` stages before it commits | Salvage before cleanup (3.2 item 6). |
| 14 | closed-loop 0.1.0 has only driven a fake subject; four max reviews each said "not ready" with narrowing findings; the last round was not re-reviewed. | journal R5 | Phase 2's first real runs are also the skill's first real test. |
| 15 | `hosts.run_agent` starts every host process with `start_new_session=True`, so killing the facade's process group does not reach the model's processes. The engine records what a run owns in `<output>/resources.jsonl`; `lifecycle.py cleanup <output>` stops recorded groups by creation identity (pid, group, start time), is idempotent, and its CLI exits 0 even when it reports `unverified` or `protected` groups. | `hosts.run_agent`; `lifecycle.py` header, `cleanup`, `main` | Cleanup runs the engine's own cleanup for every run folder and rejects unresolved outcomes (3.2 item 5). |
| 16 | After an iteration the orchestrator stops a campaign `blocked` when material records remain and none is actionable, whatever the quiet window; `init` opens the first scope as `iterate`, not `sweep`. | `closed_loop.py` `analyze`, `plan_next`, `cmd_init` | The smoke is one iteration (section 0). |
| 17 | Baseline rows land in two places: X's tracked `baselines.jsonl` for default-path explorations, and `<epoch root>/baselines.jsonl` for a cycle's attempts (`epoch.py` passes `--baseline`). The harness's one comparability predicate is `run.row_matches` (S-12). | `run.py`, `epoch.py` line 444 | 3.2 item 2 and 3.4 capture both and use the predicate. |

## 2. Goal, non-goals, and what "done" means

**Goal.** Your original ask: a loop that runs ShipLoop's E2E harness, inspects the runs, has the reviewers and judge evaluate them, lets
an improver change ShipLoop inside the evaluator boundary, and repeats, with closed-loop's certificate and budget in charge of when
to stop. This phase absorbs the first plan's P4 (the first real campaign); P3 (definer tests) and P5 (extraction) wait.

**Not in this phase.** Editing any scoring file; Salesforce or other hosted cases; a Backchain child; merging or releasing what the loop
promotes; a second subject; model-proposed adapters for ShipLoop; new statistics; quality claims (sensitivity is unproven, 3.6).

**Done means** (each a command or a test):

1. `closed_loop.py adapter-check` passes; the facade's hermetic suite passes (the list in G1, section 4); a test proves the adapter's
   files leave `boundary.qualification_snapshot`'s sha256 unchanged.
2. `readiness --campaign` records every claim of 3.6 with evidence, charged to the budget, and names each unproven one.
3. The smoke campaign on `{hello}` (`init --quiet-window 1`) yields one validated, quiet iteration and stops `incomplete` with **C1 the
   only failing check, naming the three caseless records**, and `next` says owner decisions are needed. That shows C2 to C7 can pass on
   real evidence. (With the production window of 2 the same campaign also shows C2 failing; that is correct, because the orchestrator
   stops before a second iteration.)
4. After your decisions on those records, a campaign with the production window of 2 reaches two quiet iterations on `hello`. A kill during a
   real step then leaves no duplicate run, no uncounted seconds, no surviving model process and nothing lost (it is archived and reported);
   `cleanup` returns a receipt only when every run folder's own cleanup resolved cleanly; a redo starts from the same tip.
5. The second campaign runs at least one qualified cycle or stops `incomplete` with the owner list. Every PROMOTE carries acceptance
   evidence and a green quick tier on its build.
6. The cost record exists: wall time per step split into engine time and orchestration plus operator time.

**Stop rule (provisional, you may change the numbers).** Stop and report if the facade needs a harness edit to meet 3 or 4; if
orchestration plus operator time exceeds 25% of a step's wall time in the first two real phases; or if a false completion is found (fix
it and restart the phase; never continue past one). The record in done-item 6 shows cost and consistency; it cannot show that the loop
beats an operator working by hand, and the plan does not claim it.

## 3. Design

### 3.1 Parts

- `test/shiploop_e2e/adapter/adapter.json`: the manifest. `dimensions`: `style` only (every dimension value must be covered or
  listed as not covered, so each extra dimension multiplies C4's work; the allowlist of 3.7 has four styles). `evaluation_class`: `scripted+judge`. `quiet_window`: 2.
  `commands`: `cases`, `records`, `identity`, `step`, `probe`. `claims`: the six kinds of 3.6. `authority`: routine (run allowlisted cases,
  build, qualify); owner-only (any case that `requires` a browser, a platform or a base repository; merging or releasing a promotion).
  `execution`: `capability` `writes-worktree`, `timeout_seconds` raised for the long `cases.runs` probe, `pin` listing `facade.py` and
  `adapter.json`, `env_allow` the host sign-in variables.
- `test/shiploop_e2e/adapter/facade.py`: one stdlib program behind every command. It reads files and runs the harness's command line. It
  imports these harness functions, each documented in its own module: `boundary.qualification_snapshot` and `boundary.candidate_path`
  (identity and the build token), `learning_records.current` and `learning_records.select` (records), `spread.scoring_digest`
  (calibration). Scorecards come from `scorecard.py RUN --json`, and the strict-outcome rule of `promotion._strict_outcome` (floors pass
  **and** correctness valid) is re-stated in the facade with a parity test against the real function, so drift fails loudly.
- `test/shiploop-e2e-adapter.test.py`: hermetic tests built on the harness's own fixtures (`test/shiploop-e2e-support.py`,
  `shiploop-e2e-cycle.test.py`); registered in `test/suite_catalog.py`, first in the full group (a contract test that fails other
  sessions' quick tier whenever they change the harness is a cost I should not impose unasked; the identity test may go in quick).

### 3.2 Continuation without a harness edit

0. **Setup.** The operator runs `facade.py setup --base B --workspace X` before `init`: `init` calls `identity`, so X must exist first.
1. **The evaluator checkout X is its own clone** (`git clone --local`, detached at a base commit B that is a released commit, 2.42.0 or
   later), never the owner's checkout. A clone and not a worktree: row 10 shows the improver's context reads every
   `refs/shiploop-loop/*`, and a worktree shares refs. The harness runs from X, so the scoring identity is that of B's files.
2. **X stays clean, and baseline rows are captured from both places** (row 17). After every harness invocation the facade copies the rows
   appended to X's tracked `baselines.jsonl` and every `<epoch root>/baselines.jsonl` of the step into the step's `--out` and into the
   campaign's baseline history (a file under the work folder), then restores X's file (`git checkout -- test/shiploop_e2e/baselines.jsonl`).
   A step refuses to start while `git status` shows anything else.
3. **Positioning.** A step runs `git -C X checkout --detach T` (T the published loop tip) and then the harness command in X. The harness
   makes its own loop worktree and branch from X's HEAD, so each invocation continues the loop; `.claude/worktrees/` is in `.gitignore`.
   Queries never check anything out (they must not write in the workspace): `records` reads the ledger blob at the published tip with
   `git show` into a temporary file under the work folder and folds it with `learning_records.current(path)` (the path argument, not the
   module's default); `identity` reads X's harness files, which are the same at every tip.
4. **The build token** is a digest over the exact candidate set: for every path in `git ls-tree -r --full-tree T` with
   `boundary.candidate_path(path)` true (several candidate prefixes are filename patterns such as `test/shiploop-`, not directories),
   the triple (mode, path, blob id); harness paths are excluded. Learning commits move T without changing it. A test binds it to the
   engine: after a cycle the token changes exactly when the engine's `candidate_build` differs from its `control_build` and the decision
   is PROMOTE.
5. **Process control and cleanup.** Every invocation runs in its own session; its group id is written to the step's record before
   anything else (a write-ahead intent). `cancel` signals that group (TERM, then KILL). **That does not reach the model** (row 15), so
   `cleanup` runs `lifecycle.py cleanup <folder>` for every run folder the step made (each exploration's run, each epoch attempt) and
   reports `verified` only if every result has `observed` true and empty `survived`, `unverified` and `protected` lists (the CLI exits 0
   with the last two non-empty). The first result per folder is stored, because a second cleanup is idempotent and would hide it.
   `lifecycle.py` refuses a folder a live harness holds, so the group kill comes first.
6. **Kill and salvage.** A killed invocation leaves a loop worktree whose ledger rows may be staged or uncommitted (row 13). Before any
   removal or redo the facade **copies the whole worktree directory** (its index and untracked files included) and **bundles its branch**
   since T into the step's `--out`; a plain `git diff` would miss staged additions. It reports `invalid` text naming the archive and the
   count of ledger rows it holds. The operator then records an unknown inside the claim (`unknown add --inside-claim`, naming the archive)
   and resolves it (`unknown resolve --evidence`) only after a later step finds the same thing again or you discard it. Nothing resolves
   it automatically, and an `invalid` line in an old iteration eventually leaves C7's window, so the unknown is the durable blocker.
7. **Publishing the new tip is two-phase.** The facade first writes a durable `prepared.json` (the step's result, T, T′, the build token),
   then moves the tip ref (`refs/closed-loop/<campaign id>/tip`) with `git update-ref` and an expected old value, then writes
   `published.json`. A repeated `step start` with the same key reads the files: prepared and ref equal to T′ means already published, so it
   completes; ref still T means it retries the move; any other ref value is refused and reported. Every query reads the published tip.
8. **A killed step is redone, not resumed.** Resuming a half-run epoch means calling the epoch controller's internals, which is a 3.8
   trigger. The redo is a bet: a different ShipLoop study measured a redo at 2.6 to 9.9 times the repair on three hosts
   (`3cbf8f05`, E18; another setting, so a shape and not a rate, and you have since closed that study line, so it is cited as a hint and nothing here
   depends on it). W5 measures what a killed step costs.

### 3.3 What one step does

The orchestrator asks for `--cases A,B --mode iterate|sweep --base <build token>`. The facade checks the token against the published tip
and runs one harness invocation per requested case, in order, each from the tip the previous one left:
`iterate.py --qualify --iterations 1 --case X [--generality-case Y] --host … --model … --effort … (--calibration FILE | --tolerance … --attempts …) --output OUT/<n>`.
Each invocation does what the harness's own loop does for one iteration: if an admitted record is selectable for that exposing case,
one qualified cycle (improver, purpose check, A/B epoch, decision); otherwise one exploration (run, review, judge, record).

Rules that follow from the reviews:

- **At most one candidate transition per step.** After an invocation promotes, the step stops: the cases not yet run are reported
  `ran: false` (valid, not quiet). Because the build changed, the window no longer holds old-build evidence, so the next step requests the
  **whole scope** again, and the case that promoted runs once more on the new build.
- **The generality case is chosen by the facade**: the first other-style case in the scope, by id, that is not among the record's source
  cases, passed as `--generality-case`. With none, the cycle is a single-style claim, which is the engine's own meaning of omitting it. An
  engine PROMOTE is reported as PROMOTE either way (relabelling it would leave a changed build without a promotion, which
  `validate_facts` rejects), and the acceptance evidence says whether a confirmation case took part.
- **The harness's own stop rules do not carry over.** Its two-cycles-without-PROMOTE stop resets with every `--iterations 1`; the
  orchestrator's no-progress rule (three iterations) replaces it. An invocation that prints "stopped: the evaluator changed" exits 0; the
  facade reads `OUT/<n>/LOOP.md`, treats any stop other than "reached --iterations" and "no admitted learning record after exploring" as
  invalid evidence, and stops the campaign on an evaluator change.
- **Sweeps are improver-free except where the harness cannot be stopped.** A cycle starts exactly when `learning_records.select` offers a
  record for the exposing case, so the facade calls the same function on the ledger at the published tip before each invocation; in
  `sweep` mode it does not invoke a case for which a record is offered (`ran: false`; the next `iterate` step runs the cycle). It cannot
  prevent the other path: an exploration that itself admits a record continues into a cycle inside the same invocation. The facade then
  reports what ran (a candidate), the step is not quiet, and the contract's "no improver" wording is relaxed for this adapter to "none
  unless the sweep's own exploration admits a record". You ratify that relaxation with the boundary (decision I); a strictly
  improver-free sweep needs a harness flag (3.8, trigger 1). The smoke campaign is unaffected: no record is selectable for `hello`, and an
  exploration there that admits one is reported as it ran.

### 3.4 Where each fact the orchestrator needs comes from

A fact that cannot be derived fails closed: the step is `failed`, never quiet. Authoritative sources are the **final** assessment receipts
(epoch reviews use named assessments; exploration judges retry in separate folders), never the first file found.

| `iteration` field | Source | Rule |
| --- | --- | --- |
| `build_before`, `build_after` | the build token (3.2 item 4) at T and T′ | the base must equal `step start --base` |
| `scoring` | `boundary.qualification_snapshot(X/test/shiploop_e2e, None)["sha256"]` at the start and the end | equal, else invalid and the campaign stops |
| `cases {ran, floors_met, baseline}` | each invocation's `result.json` and `scorecard.py RUN --json` | `ran`: the skill was invoked from the build under test. `floors_met`: the strict-outcome rule (accuracy and fidelity floors `pass` **and** `validity.correctness.valid` true). Attribution or timing not true goes to `invalid`. **`baseline` is `comparable` when at least one earlier row passes `run.row_matches(row, case, source, host, model, effort, planning_review, prompt_sha256)`** (the harness's single comparability predicate, S-12: same host, model, effort, source, planning mode and prompt digest, and the row reached done), searched in B's `baselines.jsonl` plus the campaign's captured history (row 17) and excluding the current step's own rows; otherwise `none`. Omitting the planning mode would switch that filter off, so the facade passes this run's mode |
| `review`, `judge` | the final assessment's `review.json` (`validity.status`, `validity.discovery_qualified`) and `verdict.json` (`validity.status`), followed through the receipts the epoch and exploration write | `valid` and `complete` from those fields; an exhausted retry budget is incomplete |
| `discoveries [{id, material, repeat}]` | `opened` rows appended during the step, found by `source.run` for explorations **and** `source.epoch` and `source.attempt` for a cycle's attempt reviews | a first sighting is new; an `opened` on an existing record is a repeat |
| `candidate {id, hash, outcome}` | the cycle's result | PROMOTE, DROP, UNDECIDED as the engine reported them, never relabelled; NO_CANDIDATE, REJECTED_AT_PURPOSE, NO_PREDICTION, REFUSED are DROP only when a candidate commit exists (its id is the hash), otherwise no candidate and an `invalid` entry; UNKNOWN_LAUNCH ("attempts not sealed: reconcile them, never retry") is no candidate, an `invalid` entry and `cleanup.verified` false |
| `invalid [text]` | terminal reasons that make evidence unusable | INVALID_REVIEW, an evaluator change, a boundary crossing, a run the skill cannot be blamed for, a killed step's archive |
| `cleanup {verified, receipt}` | the facade's own check after the step | process group empty, the engine's lifecycle receipts present, no leftover worktree; the receipt lists what was checked |
| `tier {green, build}` | `bash test/run-all.sh --group quick --changed-from <base>` in the loop worktree after a PROMOTE; once on B at campaign start | green only on exit 0; `build` equals `build_after`. An iteration that leaves the build unchanged carries the last green receipt for that build: the one the `improver.bounded` probe produced for B, which the facade stores under the campaign's work folder (C5 reads only the last iteration's receipt) |
| `acceptance {candidate, evidence}` | the epoch's decision for a PROMOTE | evidence text: per case the candidate arm's strict outcomes, the hidden acceptance checks where the case has them, and whether a confirmation case of another style took part ("single-style claim" when none did); null when there is no PROMOTE. C6 needs candidate-bound evidence, not another style |
| `consumed` | step wall time; runs started; tokens where the scorecard reports them | `cost_usd` is null for Codex and Grok runs, so there is no USD budget |

### 3.5 Records: the ledger's statuses as closed-loop's statuses

`target: shiploop` is `subject`; `target: harness` is `adapter` and never blocks a subject certificate. `material` is
`materiality in (material, high)`. `cases` are each record's source cases; **a record with none counts against every scope** (row 5). Only a
record's folded status resolves it; a candidate's DROP does not. Evidence for resolved statuses is the decision and verdict row's reason and epoch.

| Engine status | Adapter status | Why |
| --- | --- | --- |
| admitted | admitted, **only if** `learning_records.select` could offer it for an (exposing, generality) pair that exists in the **current scope** (the facade reads the scope from `campaign.json` under `CLOSED_LOOP_CAMPAIGN`, read-only); else owner | an admitted record can be unselectable (confirmation exposure, or its source cases cover every candidate generality case); calling it actionable would send the orchestrator into steps that explore instead of qualify |
| open | owner | only a judge's admission or you move it |
| in_candidate | unknown | a cycle is, or died, between prediction and decision |
| owner | owner | waits for you |
| deferred | deferred | unresolved; `reopen_when` is its condition |
| verified | verified | with the epoch decision as evidence |
| refuted, no_effect, rejected | refuted, dropped, rejected | with the verdict reason as evidence |
| unexplained_gain | owner | a gain the prediction did not explain needs a human look |

A test compares the mapping with the real fold of all 24 current records, and one case per row of this table.

### 3.6 Readiness: the skill's own claims, and what each costs

The skill has six claim kinds (`CLAIM_LADDERS` in `closed_loop.py`, `references/readiness.md`). Its start rule demands `cases.runs` at `runs`,
`grading.scores` at `scores` and `improver.bounded` at `bounded`, and no effectful probe runs until you ratify the boundary hash. Readiness
is therefore **the first real compute**, charged to the budget. The adapter contract says queries must not write inside the workspace, so the
probes work in a scratch clone under the campaign's work folder, never inside X; the baseline row the `hello` probe run appends lands in that clone.

| Claim | Top state proves | Probe | Effect | Cost |
| --- | --- | --- | --- | --- |
| `cases.runs:hello` | the case runs at the current build, writes evidence, and its cleanup receipt is verified | one real `hello` run through the facade on the pinned subject profile (`run.py --preflight-only` covers the marketplace path, not a `--plugin-dir` build, so it proves nothing here) | effectful | about 12 min of run, 15 to 25 wall |
| `grading.scores` | `evaluate` returns floors and measures for a real run | `scorecard.py RUN --json` twice on a stored real run folder; identical; floors and measures present | read-only | seconds |
| `improver.bounded` | build and verify pass on the tip and a planted out-of-bounds edit is caught | in a throwaway worktree: build the plugin and run the quick tier; then commit a planted edit to a harness file and require the harness's boundary rule (`boundary.candidate_path`, which `iterate.improve` applies to every changed path) to reject it | effectful, no model | the quick tier, about 5 min |
| `improver.invocable` | the improver lands a trivial in-bounds change on a throwaway branch | one improver call (Sol 6.1 at max through Codex) with a trivial task; optional for the start rule | effectful, one model call | small |
| `grading.calibrated:codex/gpt-6.1-terra/high` | an A/A noise report exists for the profile | W6; `spread.scoring_digest` must equal the report's | read-only once the report exists | W6 |
| `grading.sensitive:PROPERTY` | the measure separates a known-bad from a known-good for that property | none found for whole-run cases (`seeded_defects.py` covers step cases only); W3 looks at the scorecard's mutation ratio and the `quality` entries | none | none |

**What this allows.** With sensitivity unproven the certificate allows no quality claim; it says so. With calibration absent it allows
efficiency only under a stated tolerance, labelled "stated, not measured". So the first campaigns can claim "no material discovery in the
scope's cases on this build, as judged by the harness's reviewers", and nothing stronger.

### 3.7 Scopes and widening

The orchestrator, not the adapter, widens: from the catalog the `cases` command lists, it adds the cheapest case that covers a dimension
value the scope lacks (`widening_candidates`). So the adapter's catalog is the ladder, and it is an **allowlist**: `hello`, `csv-report`,
`seat-reservations`, `battleship`, each with `cost` its median minutes and `dimensions {style}`. Salesforce and other hosted cases,
browser cases (roundtable and followers), brownfield cases (they need a base repository) and every other case are either absent or carry a
`requires` the manifest marks owner-only, with a `not_covered` reason. The certificate's coverage statement is about the allowlisted cases only: other cases of the same styles, and cases outside the allowlist, are neither run nor listed one by one. A campaign's first scope is whatever `init --cases` names:
**campaign 1 is `{hello}`; campaign 2 is `{csv-report, seat-reservations}`** (cli-files and stateful-service, the two styles calibrated in
October).

Neither of campaign 2's cases has an admitted record today, and each has one owner-held record (`LR-20261101-bea142`, `LR-20261101-f8c562`).
A qualified cycle there needs you to accept one of them or an exploration to admit a new one. The one admitted generic record is
`LR-20261108-4bc6cb` (`roundtable-agent-work`, a browser case): a cycle on it needs the browser probe and a calibration of its own, so it is a later campaign.

### 3.8 What would justify a harness edit

Each is one batched change with a new scoring identity and a fresh baseline for the cases and profiles it touches (not for all 237 rows),
so each is yours to approve:

1. An explore-only flag, if you want baseline sweeps strictly improver-free.
2. A base reference and resume for loops, if killed steps cost more than the stop rule allows in the real runs.
3. A machine-readable per-iteration record, if the derivations in 3.4 break twice on harness changes.

Until a trigger fires, none is built.

## 4. Work packages and gates

```
W1 facade + manifest ──┐
W2 facts + mappings ───┼─► G1 model-free gate ─► you ratify ─► R readiness ─► W4 smoke: one iteration, K = 1
W3 probes + backlog ───┘                                                              │
                                        you decide the records (appendix A) ──────────┤
                                                                                      ▼
                                           W5 second iteration at K = 2, then kill-and-resume ─► G2 you read the reports
                                                                                      │
                                              W5b first qualified cycle, if a record is admitted
                                                                                      │
                                                     W6 calibration (if a cycle can follow) ─► W7 campaign 2
```

| Package | What | Models | Gate or proof |
| --- | --- | --- | --- |
| W1 | `facade.py setup`; manifest; `cases`, `records`, `identity`, `probe`, `step start|poll|cancel`, `cleanup`; the evaluator clone; write-ahead intents; two-phase tip publication | none | `adapter-check` |
| W2 | every derivation of 3.4 and mapping of 3.5, each with a test and a fail-closed test | none | G1 |
| W3 | the model-free probes of 3.6; the first `report` listing the 14 records as the decision list; the identity test | none | G1 |
| **G1** | **model-free tests green for: every 3.4 derivation, including the baseline predicate on both baseline destinations and the tier receipt carried across an unchanged build; the preflight limits; a positive and a negative control per probe; a two-step continuation; a step with mixed candidate outcomes; a duplicate `step start`; SIGKILL at each write-ahead window and during tip publication, with prepared-and-ref-equals-T′ replay; a killed step whose ledger additions are staged, archived whole; a harmless detached child that survives the group kill and is found by the engine's lifecycle cleanup, and a cleanup that reports `unverified` or `protected` being rejected; the baseline-file restore; `records` read from the published tip without a checkout.** Lint. A Sol max review of the facade contract, with the code and tests in front of it, and no open P1 | review | no real case run before this |
| R | you ratify the boundary hash and state a budget; `readiness --campaign` runs the probes of 3.6 (the real `hello` run, the planted-edit check, the quick tier) | one real run | the start rule holds |
| W4 | `init --quiet-window 1`; one `hello` step through `closed_loop.py` | real run | done-item 3 |
| W5 | after your decisions: a second iteration at the production window of 2; then another `hello` step, its process group killed mid-run, then `status`, `next`, `cleanup`, redo | real runs | done-item 4 |
| G2 | you read both reports and the cost record | none | your go |
| W5b | only if a record is admitted after your decisions: one qualified cycle on cheap cases (exposing `hello`, generality `csv-report`, 2 attempts, stated tolerance recorded as unmeasured). It shows the cycle path, the tip publication and the facts working end to end | real runs | one validated cycle iteration |
| W6 | A/A calibration for campaign 2 (Codex Terra high) with the epoch controller and `spread.py`; worth its hours only if a cycle can follow | real runs | a report matching the scoring digest; `grading.calibrated` proven |
| W7 | campaign 2 under your budget | real runs | done-item 5 |

## 5. Cost model (estimates from the baseline medians and Sol's repricing, not promises)

| Phase | Work | Wall time | Budget I would propose |
| --- | --- | --- | --- |
| R | the `hello` probe run, the quick tier, the planted-edit check, optional improver call | 30 to 45 min | 1 h, 3 runs |
| W4 | one `hello` iteration: about 12 min run, plus review and judge | 25 to 40 min | 1 h, 2 runs |
| W5 | a second iteration, then a killed and redone `hello` step | unmeasured; guess 1 to 1.5 h | 2 h, 3 runs |
| W5b | one cycle with 2 attempts: improver up to 45 min, 8 runs (2 arms × 2 cases × 2 attempts), serial reviews | 2.5 to 3.5 h | 4 h, 10 runs |
| W6 | 16 runs for two cases at about 17 min. October ran at concurrency two for 155 minutes, with invalid timing evidence | 2.5 to 3 h | 4 h, 16 runs |
| W7 | per qualified cycle: improver up to 45 min (harness timeout), purpose check, 12 attempts (70 to 90 min with 3 at a time), **serial** reviews and judges (12 × 10 to 15 min = 2 to 3 h), quick tier | **3.9 to 5.3 h** (3.92 to 5.25 h before purpose checks, retries and quick tests) | 12 h and 40 runs for about two cycles and two sweeps |

The budget has two amounts, `seconds` and `runs`. Provider limits and other sessions' runs can stretch wall time; three identical start
failures stop a campaign `incomplete`.

## 6. Decisions for you

| | Decision | My pick | What the alternative costs |
| --- | --- | --- | --- |
| H | The five records (appendix A): the three that name no case, and the two owner-held ones from campaign 2's cases | **You decide each: accept (the loop may implement it), reject (settled), or defer.** I do not pick for you | The three caseless records keep every campaign `incomplete`; the two block campaign 2's convergence |
| A | Route | **Facade only; a harness edit only on a 3.8 trigger** | The batched change first: a new scoring identity, fresh baselines and calibration for the cases and profiles it touches, and collisions with other sessions' daily harness commits |
| B | Subject profile | **Codex gpt-6.1-terra at high** (calibrated in October; hello 22 rows, user-listing 13, csv-report 4; seat-reservations 0, so its baseline is built by the first runs) | Grok 4.6 xhigh (your default subject since 2026-11-08): 3 baseline rows and no calibration |
| C | First compute and budget | **R and the one-iteration smoke (W4) with the budgets of section 5, then wait for your record decisions** | Starting at campaign 2 skips the cheap proof of the plumbing |
| I | What the adapter means by "comparable baseline" and "acceptance", and the sweep relaxation (3.3, 3.4) | **As written: the harness's `row_matches` rows; acceptance evidence for every PROMOTE, saying whether a confirmation case took part; a sweep is improver-free unless its own exploration admits a record.** Ratified with the boundary hash | A looser meaning would let the certificate converge on evidence the harness itself would not compare; a stricter one needs the harness flag of 3.8 |
| D | Proof of value | **No two-operator drill now.** Keep the model-free planted-trap tests (G1); the cost record shows cost and consistency only | The drill measures comparative value: two operators on frozen checkpoints, a pre-registration, an estimated 1 to 2 million operator tokens. Worth it only if you want a published value claim; the Backchain study is the precedent for asking |
| E | Merging what the loop promotes | **Never automatic.** AGENTS.md lists a ShipLoop product behaviour trade-off among the things to ask you first; the loop branch waits for review, then the normal merge and release path | A routine merge would skip that reservation |
| F | A model-judged verdict may promote | **No** (the engine promotes by script; the certificate never accepts a model verdict) | Needs measured judge reliability per subject; not planned |
| G | Guard-set size per qualification | **Defer**: the engine qualifies on the exposing case plus one of another style; a larger set is a harness change | none now |

## 7. Risks and unknowns

| Risk | How it would show | Early check | If it happens |
| --- | --- | --- | --- |
| The facade drifts from a harness that changes daily | a derivation fails on a new artifact shape | contract tests on the harness's fixtures; the campaign is pinned to B in its own clone and does not see later changes | rebase deliberately: a new identity, readiness re-proven |
| `--iterations 1` behaves differently from 3.3 | wrong cases run, or a sweep reaches the improver | G1 tests with fake hosts before any real run | record the deviation; 3.8 trigger 1 |
| A killed step costs more than expected | seconds lost in W5 and W7; E18 found a redo 2.6 to 9.9 times a repair elsewhere | W5 measures it first | 3.8 trigger 2 |
| A crash at a write-ahead window or while publishing the tip | a duplicate run, a moved tip with no record, or a lost finding | the G1 crash-window tests, including the prepared-and-ref-equals-T′ replay | fix before any real run |
| Model processes survive a kill (row 15), or the engine's cleanup reports `unverified` or `protected` with exit 0 | tokens spent after a kill; a clean receipt over live processes | the G1 detached-child test; cleanup rejects unresolved outcomes and stores the first result | `cleanup.verified` false; the step stays blocking |
| A kill loses staged ledger additions | a material finding only in a dead worktree | whole-worktree copy and branch bundle; the G1 staged-additions test | the unknown inside the claim keeps the campaign incomplete |
| The smoke campaign cannot reach a second iteration | `blocked` after one iteration (row 16) | stated up front; K = 1 for the smoke | decide the three records first |
| Machine contention: case locks, port leases, other sessions' runs, provider limits | start failures with the same error | classify start errors; three identical failures stop `incomplete`; process-group cleanup | wait and reopen |
| Neighbouring runs make a run's timing validity false | a valid run recorded as `invalid` | every invocation gets a private `--output`, so other sessions' runs are not neighbours; machine-wide locks still apply | wait or reopen |
| The first real use exposes bugs in closed-loop | a failed step the fake never produced | small steps; Sol review at G1 | fix in the skill with a test, release as a patch |
| Calibration tolerance of 0.45 on tokens means few candidates can PROMOTE, and campaign 2's cases have no admitted record | PROMOTE rate near zero; no cycle unless a record is accepted or admitted | read the calibration before W7 | success does not require a PROMOTE |
| Run artifacts hold material that must not be committed | files under `<campaign>.work` | nothing from there goes into the repository; only exported summaries do | n/a |

## 8. Not yet verified (each is checked in the work package named)

- The held-out acceptance fields in the epoch cards, and the exact shape of `cases` inside a cycle's result (W2). Known keys of a cycle's
  result: `decision`, `reasons`, `verdict`, `outcome`, `cases`, `opened`, `control_build`, `candidate_build`, `tip_note`, `learnings_commit`.
- That the facade can find every run folder a step made (each exploration's run, each epoch attempt) so cleanup covers them all, and that
  `run.row_matches` matches `hello` rows on Terra high given their `source`, planning mode and prompt digests (W2). Verified already: the
  lifecycle ledger and CLI behaviour (row 15).
- That the harness itself, started from X at a loop tip, behaves as plain Git does (the G1 fake-host test; W5 on the real engine). Already
  checked: plain Git in a scratch repository, and Sol's run of the real worktree functions with stubbed models.
- Whether `roundtable-agent-work` can run here at all (a browser probe, later).

## 9. Evidence: how each fact in section 1 was read

```
git -C <checkout> grep -n "def new_worktree" origin/main -- test/shiploop_e2e/iterate.py          # row 2
sed -n 882,931p test/shiploop_e2e/cycle.py                                                         # rows 1, 2: cycle.loop
python3 -c 'import boundary; print(boundary.CANDIDATE_PREFIXES, boundary.HARNESS_PREFIXES)'        # row 3 (from test/shiploop_e2e)
python3 -c 'import spread,json; c=json.load(open("cases.json")); print(spread.scoring_digest({n:c[n] for n in ("csv-report","seat-reservations")})["sha256"])'   # row 4
python3 -c 'import learning_records as l; print({r["record"]:(r["status"],r["target"],r["materiality"]) for r in l.current().values()})'   # row 5
sed -n 797,812p skills/closed-loop/scripts/closed_loop.py                                          # row 5: check_c1
python3 (baselines.jsonl, started/ended epoch floats, grouped by case, host, model, effort)        # row 6
grep -n "quick_suite" test/shiploop_e2e/iterate.py test/shiploop_e2e/cycle.py                      # row 7
sed -n 1,25p test/shiploop_e2e/promotion.py; sed -n 452,466p test/shiploop_e2e/promotion.py        # row 8
git log -1 27fa9c92; grep -n "backchain-passes" test/shiploop_e2e/SPEC.md                          # row 9
sed -n 276,300p test/shiploop_e2e/review.py                                                        # row 10
sed -n 4918,4932p test/shiploop_e2e/run.py                                                         # row 11
sed -n 258,268p test/shiploop_e2e/cycle.py; sed -n 288,312p test/shiploop_e2e/cycle.py             # row 12
cat docs/experiments/closed-loop-phase2-review-20261115/round1-sol-kill-witness.json               # row 13
sed -n 193,206p test/shiploop_e2e/hosts.py; sed -n 1,25p test/shiploop_e2e/lifecycle.py; sed -n 344,362p test/shiploop_e2e/lifecycle.py   # row 15
sed -n 1004,1020p skills/closed-loop/scripts/closed_loop.py; sed -n 1135,1160p skills/closed-loop/scripts/closed_loop.py                # row 16
sed -n 440,446p test/shiploop_e2e/epoch.py; grep -n "def row_matches" test/shiploop_e2e/run.py                                          # row 17
```

## Appendix A. The 14 unresolved material ShipLoop records (the decision list)

The five marked **first** are the ones that gate compute: the first three block every campaign, the last two block campaign 2.

| Gate | Status | Record | Cases | Title |
| --- | --- | --- | --- | --- |
| **first** | deferred | LR-20261030-355e5e | none | An unattended run records an unconfigured issue tracker as an assumption and proceeds |
| **first** | open | LR-20261030-d73cd8 | none | Commands to accept a stage rose past the pre-registered bar after the `shiploop check` verb |
| **first** | owner | LR-20261030-583e17 | none | What a parent does with an implement worker it cannot show stopped is unspecified |
| **first** | owner | LR-20261101-bea142 | csv-report | A reviewed proof still depended on future tests |
| **first** | owner | LR-20261101-f8c562 | seat-reservations | Reviewed criteria still exceeded available focused test IDs |
| | admitted | LR-20261031-8d97e7 | gym-membership-salesforce | Required remote tests collide with the optional-host guard |
| | admitted | LR-20261108-4bc6cb | roundtable-agent-work | Structured continuation still requires model-written glue |
| | deferred | LR-20261108-15e9e9 | roundtable-agent-work | Interrupt recovery escapes the command runner's cleanup path |
| | owner | LR-20261101-94533c | hello-hook-continuation | Planning review missed an explicit failure-reporting requirement |
| | owner | LR-20261101-e982b8 | hello-hook-continuation, roundtable | Review recognized a dependency but accepted its impossible timing |
| | owner | LR-20261105-0542a3 | chess-salesforce, roundtable | Review accepted a proof whose execution facility remained unproven |
| | owner | LR-20261105-884ad2 | chess-salesforce, roundtable-rooms | Reviewed command contracts produced two avoidable send-backs |
| | owner | LR-20261105-9d39bf | chess-salesforce | Review-created regression value was not returned in the repository |
| | owner | LR-20261108-f03c2c | roundtable-rooms | Successful delivery still depended on handwritten verification orchestration |

## Appendix B. What Sol's two reviews changed

Reviewer both times: Codex `gpt-6.1-sol`, max effort, read-only, one attempt, no fallback. Briefs, answers, run records and the kill witness are
in `docs/experiments/closed-loop-phase2-review-20261115/`. I checked each finding against the code before accepting it.

**First review** (13 minutes, on `579af232`; verdict on draft 1: **not ready for real compute**; section 1's rows 1 to 9 confirmed, rows 3, 5 and 6 with corrections now in the text).

| # | Finding | Checked | Change |
| --- | --- | --- | --- |
| 1 | The readiness claims used (`improvement.callable`, `calibration`, `baseline:*`) are not the skill's; `improver.bounded` was missing; preflight proves nothing for `cases.runs` | `CLAIM_LADDERS`, `readiness.md`, `--preflight-only` is the marketplace path | 3.6 uses the six real kinds; readiness is the first real compute |
| 2 | Quiet explorations would report `baseline: none` and C3 would never pass; `acceptance: null` conflicts with C6 for every PROMOTE | `check_c3`, `check_c6` | 3.4 defines comparable baseline and acceptance; decision I |
| 3 | Floor strings alone are not enough (correctness must be valid); qualified discoveries carry `source.epoch` and `attempt`; follow final assessment receipts; pre-epoch results lack a candidate hash | `promotion._strict_outcome`, `epoch.review_attempt`, `cycle.review_all` | 3.4 rules; a DROP object needs a candidate commit |
| 4 | A SIGKILL loses ledger rows that exist only in the dirty worktree; cwd-based cleanup misses epoch launchers | Sol's witness; `cycle.launch_all` | 3.2 items 5 to 7 |
| 5 | Two invocations can promote twice; the harness's two-miss stop resets; an evaluator-change stop exits 0; sweeps cannot be improver-free | `cycle.loop` | 3.3 rules |
| 6 | The evaluator checkout is dirty after a run (`baselines.jsonl`); improver history reads every shared loop ref; the build token must hash the exact candidate set | `run.py`, `review.py`, `boundary.candidate_path` | 3.2 items 1 to 4 |
| 7 | An admitted record can be unselectable; three caseless records block every scope; widening adds one case and ignores prose exclusions | `learning_records.select`, `check_c1`, `widening_candidates` | 3.5 mapping; 3.7 allowlist catalog and `init --cases` |
| 8 | The cost model omits serial reviews; the October calibration ran at concurrency two for 155 minutes; Terra high has no seat-reservations rows | `cycle.review_all`, calibration README, `baselines.jsonl` | section 5 repriced; decision B corrected |
| 9 | A harness edit would not need all 237 rows redone; skipping the operator drill is reasonable if planted-trap checks stay; telemetry cannot show comparative value | judgement | decisions A and D; G1 gate |

**Second review** (15 minutes, on the version-2 plan at `579af232`; verdict on version 2: **not ready**; rows 10, 12 confirmed, 13 softened; the 237 rows, profile counts, medians and W6's October figures confirmed; W7 arithmetic 3.92 to 5.25 h).

| # | Finding (version 2) | Checked | Change |
| --- | --- | --- | --- |
| 1 | The two-sweep W4 is unreachable: after one iteration `analyze` returns `blocked` and `plan_next` stops; `init` opens `iterate`; the tier receipt must be carried explicitly; C7 does not check readiness's scoring identity | `analyze`, `plan_next`, `cmd_init`, `check_c7`, `certificate` | section 0, done-items 3 and 4, W4 and W5, row 16, the tier row of 3.4 |
| 2 | Host processes start in their own sessions and survive the facade's group kill; lifecycle cleanup exits 0 with `unverified` or `protected` and marks groups ended; a second cleanup hides the first result | `hosts.run_agent`, `lifecycle.cleanup`, its CLI exit | row 15; 3.2 item 5 |
| 3 | A plain `git diff` misses staged ledger additions; `unknown` neither imports archives nor resolves on rediscovery; an `invalid` line leaves C7's window | `cycle.commit_entry`, `cmd_unknown`, C7's window | row 13; 3.2 item 6 |
| 4 | Relabelling a PROMOTE as UNDECIDED fails `validate_facts`; C6 needs evidence, not another style; promotion empties the old-build window and the next step requests the whole scope; `sweep_pending` is cleared regardless | `apply_decision`, `validate_facts`, `record_iteration`, `check_c6` | 3.3 rules; decision I |
| 5 | The baseline predicate and signature were incomplete; rows also land in epoch-local files | `run.row_matches`, `epoch.py` line 444 | row 17; 3.2 item 2; 3.4 |
| 6 | A compare-and-swap does not commit the result with the tip; imports bind the importing checkout; X must exist before `identity` and readiness | module defaults, `spread.scoring_digest`, `cmd_init` | 3.2 items 0, 3 and 7 |
| 7 | Coverage claims need bounding; actionability must match real scope pairs; a qualified cycle should be demonstrated before the expensive campaign | `widening_candidates`, `learning_records.select` | 3.5; 3.7; W5b and W6 |

