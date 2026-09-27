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

### P10 Measure the run narrative (harness; S-15) — requested by the owner 2026-09-27
ShipLoop 0.44.0 renders a milestone narrative (achieved, now, ahead, pace)
and asks each step for a one-line `headline`. Headless E2E hosts never set
`CLAUDE_CODE_ENTRYPOINT=cli`, so every milestone packet asks the model to
show the narrative as written.

Change (harness only): `metrics.narrative` counts, from the event stream,
the narratives ShipLoop emitted for the model to show, how many the model
showed (the heading line appears in its following text) and how many it
showed verbatim (every narrative line appears), and names the stages it
skipped; from the run's result records, the share of accepted results that
carry a headline. It is written to metrics.json, result.json and each
baseline row, printed in the report and compared with the case's previous
row. Not a verdict yet.

Adversarial evaluation:
- *Packet text leaks into metrics or reports* -> **mitigated**: only counts
  and stage names are kept; tested.
- *A host splits text into chunks (Grok) or blocks (Claude), so a shown
  narrative is missed* -> **mitigated**: all assistant text between one
  emission and the next is joined before matching; both formats tested.
- *Repeated tool updates (Grok) count one packet twice* -> **mitigated**:
  one emission per tool call; tested.
- *The model pastes an older narrative, or only the heading* ->
  **mitigated**: `shown` and `verbatim` are separate counts; verbatim needs
  every line of that emission.
- *Gamed: the model pastes every narrative and the run gets longer* ->
  **accepted**: pasting is what S-15 asks for; its cost appears in output
  tokens and turns, compared per case.
- *A run on a ShipLoop before 0.44.0 reads as zero shown* -> **mitigated**:
  zero emitted reads as "no narrative", not as a failure.
- *Making it a verdict too early fails runs that ship correct software* ->
  **mitigated**: scored beside reliability until each style has a baseline;
  promotion to a verdict goes through Change admission.

Anchor: S-15 (owner request). Non-regression: verdicts, glue, failures and
cost are unchanged; the metric only reads existing files. Evidence: hermetic
metrics tests with Claude and Grok event streams; the next focused-suite run
records the first baseline.

### P11 Follow-up return after ShipLoop's own knowledge commit (ShipLoop; S-5) — implemented 2026-09-27

Evidence: web-p5 battleship. The release-verify knowledge commit lands after the return taken at
release, so handoff refuses with "the recorded one is stale" and the model runs plan-return and return
by hand: a mechanical step done by the model on every worktree run whose release-verify updates
`docs/shiploop/`.

Proposal: when the only paths changed since the recorded receipt are knowledge paths
(`knowledge_home.in_home`), ShipLoop performs the follow-up return itself after that commit, by the
receipt's own route (fast-forward stays fast-forward), and prints the new receipt.

Adversarial evaluation (to finish before implementing):
- It writes to the user's branch without a model-run command. Bound: only knowledge paths, only after a
  verified return the run already made, and the same drift checks refuse a moved source.
- A working-tree receipt would get knowledge files as uncommitted changes in the user's checkout, which
  is what the first return already did for the product.
- If the source drifted after the first return, the automatic follow-up must refuse and fall back to
  today's message, never retry or roll back.
- Anchor: S-5 (mechanical steps are the scripts'); non-regression: the guard and message stay for any
  other change.
Implemented: `workspace.follow_up_knowledge_return` runs from `_knowledge_close` after a knowledge commit in a
worktree run; it acts only when every path changed since the returned candidate head is knowledge and
nothing else is dirty, carries the reviewed plan's dispositions, and lets execute_return's own checks refuse
a moved source (the refusal is printed and handoff asks for the return as before). It never commits
leftovers, retries or rolls back.

### P12 improve-complete derives the completion record (ShipLoop; S-1, S-5) — approved by the owner 2026-09-27

Evidence: breadth battleship on 1.11.1. The Improve child's completion record (a Markdown file with one
`shiploop-state` JSON fence holding summary, review_refs, check_refs, lessons) was written as raw JSON and
refused; the model then read ShipLoop's source to learn the format. Owner review: the hand-off is
over-precise. The model restates paths ShipLoop already knows (its own `reviews/` directory, and the
terminal packet's `unchanged_first_pass`, which fixes whether one or two review files count), in a
storage format meant for authoritative state.

Change: `improve-complete --action X`, with no record. ShipLoop takes review_refs from `reviews/`
(the last one or two `review-<n>.md`, per the terminal packet) and check_refs from `reviews/checks.md`.
The model writes only what needs judgement: optional plain-text notes (summary and lessons), and a
`final_result` record only when the review changed a decision. `parent-return.md` becomes the command.
One supported version: the `--result` record is removed, not kept beside the new form.

Adversarial evaluation:
- A child that names its review files differently cannot be matched. Guard: the packet states the names;
  improve-complete refuses with the files it found and the names it expects, one clear step, never a
  guess. Risk accepted: a model that ignores stated names gets one refusal, as today.
- "The last two" must be the two trivial passes, not an earlier material one. Guard: order by the number
  in the name (`review-<n>.md`), which the packet assigns per pass; the terminal packet's pass count and
  `unchanged_first_pass` fix how many count; a gap or a missing file refuses.
- Evidence integrity must not weaken: ShipLoop still copies and hashes the files it imports, and the
  same workspace-containment checks apply to paths it derives.
- The delegated (non-inline) route and reconcile/stopped receipts (target, evidence_refs) are separate
  shapes. Scope: change only the success completion; leave incomplete/reconcile receipts unchanged, and
  say so in the references.
- Removing `--result` breaks any saved run mid-child at release time. Accepted under "one supported
  version": a run on the old version finishes on that version.
- Tests and references that describe the record must change with it; the delegation and navigator tests
  pin packet text.
Anchor: S-1 (scripts own state), S-5 (mechanical steps are the scripts'), S-7 (small packets).
Non-regression: the same files are imported, hashed and archived; no verdict changes.

### P13 A run-local scratch directory; no shared /tmp names (ShipLoop; S-14, Parallel work) — implemented 2026-09-27

Evidence: suites web-1111 and breadth-1111 ran concurrently on 1.11.1. The web-service battleship run and
seat-reservations both wrote their Until Loop report to the literal path /tmp/improve-done-1.json; the
battleship run then read the other run's report ("the returned report mentions a different server").
The same collision hits a user running two ShipLoop sessions. Models choose fixed /tmp names because the
Until Loop report goes on standard input and no packet says where temporary files belong; TMPDIR does not
help, since the paths are literal.

Proposal: ShipLoop creates <run>/scratch/ and every packet's common rule says temporary files go there
(/tmp is shared with other runs). The Until Loop report is written to a path ShipLoop names and passed as a
file (the upstream until-loop --report-file item), not piped from a fixed /tmp name.

Adversarial evaluation:
- Leakage: the run directory is ShipLoop-owned (outside the product; `.shiploop`/`.shiploop-runs` are
  protected return paths and knowledge commits take only docs/shiploop/ and SHIPLOOP.md), so scratch files
  never reach the product or a commit.
- Cost: one sentence in the common rule, one locator line, one line in the Improve packet. Accepted.
- Guidance, not enforcement: a model can still write /tmp. Measured instead: `tmp_writes` per run, and a
  suite prints any /tmp name two of its cases wrote (their evidence is suspect). The next parallel suite
  judges whether the guidance holds; if not, the Until Loop half (a report path it names) becomes necessary.
- The Until Loop `--report-file` stays upstream; the ShipLoop half stands alone.
- Evidence from the 1111 round: the metric finds the collision (/tmp/improve-done-1.json, written with the
  file tool by web battleship and seat-reservations).
Anchor: S-14 (unattended, no hidden coupling), Parallel work (concurrency must not change a verdict).

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
6a. P10 (narrative metric, harness only) lands with the next focused-suite
   run, which records each style's first narrative baseline.
7. Later, each through Change admission: tool knowledge into one catalog;
   Grok refusal probe (host-neutral outcome); Until Loop short output
   upstream.
