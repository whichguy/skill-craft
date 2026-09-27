# ShipLoop plan after E2E runs 1-8b (2026-09-27, revision 5)

Execute: ask

Supersedes the open items of `shiploop-e2e-verification-plan-2026-09-26.md`.
Governed by `test/shiploop_e2e/SPEC.md`: ShipLoop is a general SDLC execution
engine (Purpose). Every item below went through Change admission in order:
adversarial evaluation first (each consequence mitigated, accepted or the
change rejected), then anchor, non-regression and evidence. E2E work runs
depth-first in focused suites, confirmed by a breadth suite.

## Audit behind this plan

- The 1.7.0 lifecycle rule is phrased in game/technology terms.
- Tool knowledge sits in script logic (per-runner test-count parsers, the
  `npm run lint` / `make lint` fallback).
- The harness core recognises test runs by tool name and copies the
  requirement-ID pattern.
- Four commit code paths (three identity copies, one without a fallback, none
  screening for secrets); three hand-built loop contracts; Improve packets
  carry text for steps the scripts now perform.
- All eight live runs probed one style (browser UI over an HTTP service).

## Suites

| Suite | Style | Cases | Use |
|---|---|---|---|
| `web-service` (focused) | browser UI over an HTTP service; follow-on in the same repository | battleship, battleship-scoring | depth loop for P3-P5; baselines from runs 7, 8b |
| `cli-files` (focused) | command-line tool over input files, report output, no server | new case | baseline in P6 |
| `stateful-service` (focused) | service with persistent state and concurrent writers | new case | baseline in P6 |
| `breadth` | one case per style | battleship, cli case, stateful case | generality gate before a release is called good |

## Items

### P1 Harness suites (harness only)
Change: `cases.json` gains `style`; suites named per style plus `breadth`;
`run.py --suite <name>` runs a suite's cases in order, chaining follow-on cases
from their predecessor; each result appends a summary row to a committed
per-case baseline file keyed by case and ShipLoop version.

Adversarial evaluation:
- *Baselines drift silently when ShipLoop changes* -> **mitigated**: rows are
  keyed by ShipLoop version; comparisons state both versions.
- *A committed baseline file conflicts with concurrent sessions* ->
  **mitigated**: rows only append, one line per run, written in the same
  learnings commit (already one commit per run).
- *A follow-on runs on a failed predecessor and blames ShipLoop* ->
  **mitigated**: the suite skips the follow-on with the predecessor's result
  as the reason; tested.
- *Suites encourage skipping breadth* -> **mitigated**: SPEC promotion rule;
  a release is not called good without a breadth row per style.
- *`--case` behaviour changes* -> **mitigated**: unchanged path, self-test pins it.

Anchor: SPEC "E2E suites"; eight runs of one style cannot show S-13.
Non-regression: no ShipLoop code touched; result.json fields keep meaning.
Evidence: self-test (order, chaining, skip on failed predecessor, baseline
append); a fake-host `--suite web-service` run.

### P2 Case-agnostic harness core and a glue metric (harness only)
Change: count test runs from ShipLoop's verify records; reuse ShipLoop's
requirement-ID pattern; add `model_glue` (shell writes into ShipLoop-owned
paths, hand-built loop JSON, commit/rename/mkdir commands there).

Adversarial evaluation:
- *`test_runs` changes meaning and breaks comparison with runs 6-8b* ->
  **mitigated**: recompute the old runs that still exist and record both
  definitions; where an old run is gone, the comparison says so.
- *Glue metric counts product work (tests that write files)* -> **mitigated**:
  only ShipLoop-owned paths and ShipLoop mechanics count; the matching commands
  are listed for review.
- *Glue metric misses glue done differently (Python writing a receipt)* ->
  **accepted**: the metric is a signal, not proof; the review question for
  S-4/S-5 stays.
- *Importing ShipLoop's pattern couples the harness to engine internals* ->
  **accepted**: S-12 prefers one definition; a rename fails the self-test
  loudly.

Anchor: SPEC harness rule (case-agnostic core); S-4, S-5 measurable; S-12.
Non-regression: metric names kept; only `test_runs`' source changes, recorded.
Evidence: self-test on synthetic events; recomputed old runs.

### P3 One commit path with a secret screen (ShipLoop)
Change: one `commit_paths` helper for the knowledge-home commit, the integrate
commit, `improve-commit` and workspace bootstrap; skips and names text files
the privacy screen flags; configured identity, else the workspace identity.

Adversarial evaluation:
- *A skipped file is one the product needs; the stage passes, the returned
  product is broken* -> **mitigated**: skipped paths are printed at the
  commit, recorded in the run, and remain uncommitted, so the return plan
  lists them and the harness `committed` verdict fails; tested.
- *False positives on fixture tokens* -> **mitigated**: skip that file only,
  never fail the transition; the model sanitises and recommits.
- *False negatives (a secret the screen misses)* -> **accepted**: defence in
  depth with `.gitignore` and the existing knowledge screen; the screen is not
  a guarantee (stated in the handoff).
- *Scanning large/binary files is slow* -> **mitigated**: text files only,
  size-capped.
- *The knowledge commit's behaviour changes* -> **mitigated**: it only gains
  the identity fallback it lacked (a failure fixed); success path identical,
  tested.
- *Fallback author "ShipLoop Workspace" in user history* -> **accepted**: only
  when no identity is configured (Git refuses otherwise); stated in handoff.
- *Bootstrap's empty commit goes through a helper built for paths* ->
  **mitigated**: explicit `allow_empty` path, tested.

Anchor: S-12 (four copies), S-11 (commits never carry secrets to the user's
branch), S-5. Non-regression: identical staged paths and messages for clean
files. Evidence: per-caller tests; token file skipped and named; `web-service`
focused suite keeps `committed` and glue 0.

### P3b ShipLoop commits the knowledge home after every accepted stage that changed it (ShipLoop)
Change: after any accepted stage (not only the four knowledge closes), if
`docs/shiploop/` changed in the execution checkout, ShipLoop commits it through
the P3 helper, with the same checks the closes use (no dropped requirement
ID, privacy screen).

Evidence: run 8b's remaining model glue is 3 `git add/commit` of docs during
integrate, integration-verify and handoff, stages that edit the knowledge
home between closes; the return needs those files committed.

Adversarial evaluation:
- *More, smaller commits in the product history* -> **accepted**: one commit
  per stage that changed knowledge, message names the stage (S-11 asks for
  committed knowledge); no empty commits.
- *A half-written spec is committed mid-stage* -> **mitigated**: commit only
  after the stage is accepted, never during it.
- *A dropped requirement ID slips in between closes* -> **mitigated**: the
  same ID check the closes use runs first; on refusal the stage's done is
  refused, as at the closes.
- *Model still commits docs itself out of habit* -> **mitigated**: the packets
  already say ShipLoop commits the knowledge home; glue metric shows whether
  the habit persists.
- *Conflict with the integrate item commit (both touching docs)* ->
  **mitigated**: both go through one helper; whichever runs second finds
  nothing staged and makes no commit.

Anchor: S-5, S-11, S-12. Non-regression: the four closes behave as today;
other stages gain a commit only when the knowledge home changed. Evidence:
navigator test (a docs edit in integration-verify is committed on accept, an
ID drop is refused); web-service focused suite: glue from docs commits 0.

### P4 One loop-contract builder (ShipLoop)
Change: test loop, quality loop and Improve contracts come from one module;
the Improve exit condition includes the stage's own `done_when`. Start
mechanisms unchanged (`loop-start` verb deferred: zero start failures in runs
7/8b).

Adversarial evaluation:
- *Test/quality contracts change subtly* -> **mitigated**: tests assert they
  are byte-identical to today's.
- *Longer exit text is reprinted by the Until Loop on every pass, growing
  context (S-7)* -> **mitigated**: done_when bullets are short; measure the
  contract size delta and keep it under ~500 characters; if larger, reference
  the packet's done-when section instead.
- *Stricter exit criteria add review passes and cost* -> **accepted**: S-10
  asks for checkable, stage-specific exits; cost change attributed in the
  suite comparison.
- *A done_when item is not checkable inside a review loop (it needs a later
  stage)* -> **mitigated**: include only the stage's own done_when (they are
  written for that stage); review loops confirm by recorded checks.
- *Saved runs' contracts* -> **mitigated**: frozen on disk; only new contracts
  use the builder.

Anchor: S-12; S-10. Non-regression: test/quality byte identity; Improve keeps
every field. Evidence: contract tests; `web-service` focused suite turns/cost
vs runs 7/8b.

### P5 Improve packets state each obligation once (ShipLoop)
Change: remove text describing steps the scripts now perform (hand-freezing
context fields, resource lists, runtime start syntax, rename steps); keep what
the model must still do, once each.

Adversarial evaluation:
- *Conflicts with the owner's "never trim guidance" rule* -> **mitigated**:
  only superseded text is removed, each removal citing the script function
  that now performs that step; no remaining guidance is shortened.
- *An obligation disappears and a model skips it after context loss (S-6)* ->
  **mitigated**: an obligation list is asserted by a packet-contract test.
- *Models trained on earlier packets in the same run* -> **accepted**: one
  supported version; new runs only.
- *Delegated (ask-agent) route still needs the manual steps* -> **mitigated**:
  inline route only; delegated packets unchanged, tested.

Anchor: S-7, S-6. Non-regression: obligation list; stage packets untouched.
Evidence: packet-contract, delegation, v3-guidance suites; packet sizes;
`web-service` focused suite.

### P6 Baselines for the new styles (harness + runs)
Two cases, both Python 3 standard library (a different stack from the Node web
case, nothing to install), each the only case of its focused suite and one of
the three `breadth` cases. Product checks live in `test/shiploop_e2e/checks/`
(`$E2E_CHECKS`), build their inputs in temporary directories and write
nothing into the work directory. Both were validated before any live run:
reference implementations pass every check; a race-prone service fails the
concurrency check (43 of 50 reservations accepted on capacity 20).

**`csv-report`** (style `cli-files`): `report.py FILE...` summarises sales CSV
into JSON; invalid rows reported as `FILE:LINE: reason`, exit codes 0/2/1.

| Check | What it proves | Anchor (what it lets the run show about ShipLoop) |
|---|---|---|
| unit | `python3 -m unittest` passes with at least one test | S-9: the product's own suite exists and runs |
| totals | exact rows, revenue, per-region revenue, per-product units | S-9 on a spec-level example (the spec must pin arithmetic and rounding) |
| invalid | bad rows reported with `FILE:LINE`, skipped, exit 2, valid rows across files still counted | edge cases carried from request to spec to tests (S-6: nothing lost between stages) |
| missing | unreadable file: exit 1, stderr message, empty stdout, no traceback | error paths planned, not only the happy path |
| empty | header-only file contributes nothing | boundary input |

**`seat-reservations`** (style `stateful-service`): HTTP service with SQLite
persistence (`PORT`, `DATA_FILE`) that must never oversell under concurrency.

| Check | What it proves | Anchor |
|---|---|---|
| unit | `python3 -m unittest` passes with at least one test | S-9 |
| contract | create, duplicate (409), reserve, over-capacity (409), read, unknown (404), invalid seats (400), state unchanged by rejections | S-9 on the full HTTP contract |
| restart | reservations survive a server restart on the same `DATA_FILE` | the lifecycle/state decisions in planning (owner, persistence) reach the product |
| concurrency | 50 parallel 1-seat requests on capacity 20: exactly 20 accepted, 30 refused, 20 reserved | a stated concurrency rule is planned and tested, not assumed |

What the baseline runs measure about ShipLoop in each style (from metrics and
review): verdicts including `committed`; turns, cost, sessions, cancellations;
`model_glue`; ShipLoop failures; which stages cost most in a style with no UI
(cli-files) and with a concurrency rule (stateful-service); whether the
general planning guidance (state lifecycle, simultaneous changes) is applied
without a game-shaped example.

Adversarial evaluation:
- *Cases need tools the machine lacks* -> **mitigated**: Python standard
  library only; confirmed present (Python 3.14, sqlite3).
- *Concurrency check flakes* -> **mitigated**: invariant counts only, no
  timing; validated both ways (correct service passes, racy one fails).
- *Checks encode an implementation choice the prompt did not state* ->
  **mitigated**: every asserted field, code and message shape is in the prompt;
  rounding checked to 2 decimals; region revenue compared numerically.
- *Checks leave files or servers behind* -> **mitigated**: temporary dirs;
  servers terminated in `finally`; the harness deletes new untracked files.
- *A port collision fails a check* -> **mitigated**: free port per server.
- *A failure is the product's, not ShipLoop's* -> **accepted**: product
  defects are evidence; the review judges against the spec.
- *Two runs in parallel interfere* -> **mitigated**: separate isolated host
  profiles, output directories and free ports; cost unchanged (~$25-35 each).
- *A typo in a check silently fails a live run* -> **mitigated**: self-test
  asserts every `$E2E_CHECKS` script and subcommand exists.

Anchor: SPEC "E2E suites" (a baseline per style before judging changes);
Purpose (generality). Non-regression: new cases, suites and checks only; the
web-service cases are unchanged; `breadth` gains the two cases. Evidence:
self-test (40 cases); reference/negative validation above; one run of each
focused suite on the current release, rows in `baselines.jsonl`.

### P7 Release and breadth gate
Change: one release for P3-P5 after the full hermetic tier; host updates;
`web-service` focused suite until it passes; then `breadth`.

Adversarial evaluation:
- *release.py ships another session's pending notes* -> **mitigated**: list
  `changes/` before release; only intended notes, otherwise coordinate.
- *A verb or text change breaks pinned adapters/fixtures (as in 1.5.0)* ->
  **mitigated**: full tier locally before release.
- *Breadth failure after release* -> **mitigated**: the release is not called
  good; fix in the failing style's focused suite, then re-run breadth.

Acceptance: every verdict passes in every style; 0 ShipLoop command failures;
glue 0 for mechanical steps; per-case cost no worse than baseline, or the
increase attributed to a stated intended change.

### P9 Unattended by default (ShipLoop; S-14) — design approved by the owner 2026-09-27
Owner decision: unattended is the default; if a run really cannot proceed
without the end user, it prompts the end user. No separate attended setting.

Change:
- Decisions: take a stated default, record it (with the alternatives and why
  this one) as an assumption the handoff reports, and continue.
- Steps only a person can perform (sign-in, grant, observation): record an
  open item on the result and in the run's outcome, and continue with every
  stage that does not depend on it.
- Prompt the person (`blocked` + `awaiting`, end the turn with the question and
  the resume command) only when nothing further can proceed without them. An
  `awaiting` result must state why no default would do (`no_default`), which
  ShipLoop refuses when blank.
- Wording: SKILL.md, the stage duties that route decisions and observations to
  `awaiting`, the navigator's refusal message, and the 1.7.0 lifecycle line
  "carry the question to the user with the default you would take".

Adversarial evaluation:
- *A wrong default silently builds the wrong thing* -> **mitigated**: recorded
  with alternatives; the handoff lists defaults first; S-9 checks still gate.
- *Authority: proceeding where a person must decide (production, money,
  deletion)* -> **mitigated**: authority limits are cases that cannot proceed,
  so they still prompt; unattended never widens authority.
- *The model keeps asking anyway* -> **mitigated**: `no_default` required and
  refused when blank; `asked_user` and blocked-awaiting outcomes measured in
  every suite.
- *The model never asks when it truly must* -> **mitigated**: authority and
  sign-in cases are named in the wording as cannot-proceed; resume path
  unchanged.
- *Saved runs already awaiting* -> **mitigated**: resume unchanged;
  `no_default` is checked only on new submissions.
- *Pinned tests and wording churn* -> **accepted**: updated in the same change,
  full tier before release.
- *An open item lets a run pass with key behaviour unverified* ->
  **mitigated**: the criterion stays unconfirmed (S-9); product checks and the
  committed verdict still apply.

Anchor: S-14, S-2, S-9. Non-regression: the resume path and authority blocks
are unchanged; `awaiting` remains valid with a reason. Evidence: navigator
tests (blank `no_default` refused; reasoned awaiting accepted; resume
unchanged); packet wording tests; breadth suite with `asked_user` 0 and no
run ending awaiting a person.

### P8 Engine neutrality (ShipLoop prompts/cards; owner review first)
Change: restate the 1.7.0 lifecycle rule in SDLC terms with at most one
labelled example; vary one-domain illustrations.

Adversarial evaluation:
- *The rubric-tuned wording loses measured safeguards* -> **mitigated**:
  owner review; rerun the architecture-rubric scenarios; no regression allowed.
- *Neutral wording is vaguer and models decide worse* -> **mitigated**: the
  rubric rerun and breadth suite measure it; revert if worse.
- *Test churn from pinned wording* -> **mitigated**: update pins in the same
  commit; full tier.

Anchor: S-8, S-13, Purpose. Evidence: rubric rerun; breadth suite.

### Later, each through Change admission when planned
- Tool knowledge into one catalog (S-8), behaviour-preserving.
- Grok refusal probe; any outcome host-neutral (S-8, S-13).
- Until Loop short output upstream (S-7); owner decision.

### Rejected after evaluation
- Skipping skill stages: 2-6 turns; a new rule costs more than it saves.
- Trimming planning: planning size is fine in files (S-7).
- `--always-approve`: tests an unrealistic host; unrestricted shell.
- Printing whole packets: contradicts S-7.
- A Battleship-specific hidden-state check: product-specific (S-13);
  replaced by a generic review question and case-level checks only where a
  request has hidden information.
- A `loop-start` verb now: no evidence of a start problem; churn and adapter
  risk without an anchor in run evidence.

## Status

- P6 in progress (2026-09-27): `csv-report` and `seat-reservations` cases,
  checks validated against reference and race-prone implementations; baseline
  runs of both focused suites on 1.7.0 running. Their results are reviewed
  against the spec before P3 starts; findings enter this plan only through
  Change admission.

- P1 done: styles in `cases.json`, `suites.json` (web-service, smoke, breadth),
  `--suite` with follow-on chaining and skip-on-failed-predecessor,
  `baselines.jsonl` seeded from runs 6-8b and appended per run.
- P2 done: `script_verifications` from ShipLoop's verify records;
  requirement IDs through ShipLoop's own pattern; `model_glue` defined by
  ShipLoop paths and verbs. Recomputed on past runs: glue 31/39 (1.4.0),
  17/35 (1.5.0), 5 (1.6.0). Run 8b's remaining glue: model `git add/commit`
  on docs outside Improve reviews and one `rm -rf .shiploop-improve`: input
  for P3.

## Order

1. Finish P6: record both baselines, review them against the spec (clauses
   confirmed or violated per style), admit any new findings.
2. P3 + P3b (one commit path, secret screen, knowledge commits after every
   stage), iterated on the `web-service` focused suite until it passes with
   docs-commit glue 0.
3. P4 (contract builder, stage done_when exits), same suite; turns/cost
   compared with runs 7/8b.
4. P5 (Improve packets state each obligation once), same suite; packet sizes.
5. P7: one release for P3-P5 after the full hermetic tier; hosts; then the
   `breadth` suite (battleship, csv-report, seat-reservations) against each
   case's baseline.
6. P9 (unattended by default; design approved), then P8 (engine neutrality) after owner review, confirmed by the rubric rerun and
   `breadth`.
7. Later, each through Change admission: tool knowledge into one catalog;
   Grok refusal probe (host-neutral outcome); Until Loop short output
   upstream.
