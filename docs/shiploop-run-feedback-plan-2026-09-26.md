# ShipLoop run-feedback plan (2026-09-26)

Execute: ask

Source: the Salesforce Battleship run (a Lightning component, a Jest suite and a
Fleet command tab in org `de`). By revision 140 most turns were packet handling,
duplicate reviews and release stages that ran again after a small metadata fix.
This plan turns the nine points of that report, checked against `origin/main`
(ShipLoop 0.31.2), and the owner's answers of 2026-09-26 into one set of changes.
A second, adversarial pass against the code (same day) corrected the first draft;
its corrections are folded in.

It builds on [shiploop-delivery-overhead-plan-2026-09-23.md](shiploop-delivery-overhead-plan-2026-09-23.md)
and delivers several of its planned items: E1 (evidence class from the diff), E4
(merge same-fact records), E5 (check ledger) and F4 (empty-diff Improve cap).
Per-stage applicability replaces the general Phase 5 compact profile.

## Rules every change follows

1. **The script decides; the model does the step.** Every skip, resume point and
   reuse is decided by the script from state, the Git tree or a recorded check
   ([navigator.md](../skills/shiploop/references/navigator.md)).
2. **Skip only on proof.** A stage is left out only when the script can prove, from
   state it reads itself, that the stage has nothing to do for this item. What the
   model declares is an input to that proof, never the proof. When the script cannot
   tell, the stage runs.
3. **Checked, not assumed.** Where the proof needs a look the script cannot take, the
   stage is still issued. Its packet opens with an applicability check the script
   has written, preferably a `shiploop` command whose output the script can verify.
   The script refuses a not-applicable result that does not cite that check, or whose
   recorded output contradicts it.
4. **An unchanged Improve review needs no test rerun.** If the working tree after an
   Improve review is identical to the tree that a recorded run of the same commands
   passed on, in the same environment, that pass stands. "Identical" is a tree-id
   comparison, never the review's own label. This covers reruns of a recorded
   check. A stage that has its own work to do (tighten tests, run lint, verify the
   integrated result) still runs.
5. **Point to it; don't make the model reread it.** Packets give labelled references
   (path, what it answers, when to open it) instead of "read X first" at every
   stage, and do not reprint unchanged run rules. The current stage's own prompt stays
   complete; no prompt is shortened to fit a size (owner rule 2026-09-25).
6. **Keep what worked.** The dry-run before the real deploy, "a Jest pass is not a
   deployed game", and no deploy before the grant is recorded. No change below weakens
   them.
7. **One supported version.** The new state, history, result and contract fields ship
   with a single `STATE_VERSION` bump (3 → 4) and a single `DELIVERY_CONTRACT_VERSION`
   bump (1 → 2) in the release that first needs them. Older runs are refused with
   `FRESH_RUN_HINT`; nothing is migrated and no key becomes optional to admit them.

## Findings (verified 2026-09-26)

Paths under `skills/shiploop/scripts/` unless noted.

| # | Report item | State on `origin/main` |
|---|---|---|
| 1 | Test stages run with no test command | INNER order is fixed (`shiploop_navigator_v3_prompts.py` `INNER`); `_next_stage` is always `index+1`. `test_commands_na` only shortens test-green and regression. test-spec (plus its Improve child), baseline, test-author and test-red ignore it. Step-plan results have no script-checked field listing the files an item will touch. |
| 2 | Full outer restart after a small replan | Carry-forward after a replan goes to `system-test-author`; `_accepted_done` voids every outer stage accepted before it. In `shiploop_consumer_delivery.py` a replan clears `release_plan_completed`, and a material post-plan contract change sets a barrier that only a fresh system-test and release-plan clear. `_preserved_observations` already carries unchanged effect/identity rows across a contract correction. |
| 3 | Two trivial Improve passes on unchanged files | Five callbacks + four file writes per reviewed artifact. `finish_improve` already uses the seed result when `final_result` is absent; only the packet wording asks for a restatement. The overhead plan rejected a one-review tier; Improve's `review-policy.md` rules out a hash gate. |
| 4 | `next` reprints everything | `next` re-renders the full packet from state; nothing records what was printed. Packets tell the model to read the context index and cards "in full once per context". |
| 5 | Zero-test run passes | `shiploop_test_loop.verify` judges by exit code only and writes `tests/<action>-verifyN.md`. The zero-selected rule is only guidance (`references/execution-planning.md`). test-red is not script-run. |
| 6 | Salesforce consumer entry | `references/platforms/salesforce.md` already notes the CustomTab Tooling failure. Missing: `lightning__Tab` does not create a tab; a required navigation entry; exercising the confirm command before the deploy it confirms. |
| 7 | Stop hook while blocked on the user | A `blocked` run already lets the stop through quietly and drops the binding. The defect is upstream: the question was asked while the run stayed `active`, so every turn was continued, and "Resume with" is printed for an active run with no progress. `resume` accepts any blocked run without an answer. |
| 8 | Deploy question combines two questions | Mostly fixed by c5ac103 (a request naming the target is the grant). When a question is still needed, `references/delivery-authority.md` combines both parts, and `authority` has no scope field. |
| 9 | Browser cases need a person | Only generic `blocked`; no structured "what the person must do"; `repeat` can loop. |

## Shared mechanisms

### M1 Test runs that prove something

Extend the existing verify records; do not add a parallel ledger.

- `tests/<action>-verifyN.md` (written by `test_loop.verify`, counted by
  `MAX_REFUSED_RUNS`) gains: `tree` (M2), `env` (below), recognised `counts`,
  matched test IDs and a `status`.
- **Status:** `passed` needs exit 0 **and** at least one executed test **and** every
  ID the command must cover (below) appearing as run. `no-tests` (nothing ran),
  `ids-missing` (ran, but not the named cases) and `failed` all refuse.
  `passed-uncounted` (exit 0, output not recognised) is accepted only for a command
  that declares no IDs and no `min_tests`. It never satisfies a skip, a reuse or
  test-red.
- **Recognisers:** Jest/Vitest (all skipped, `No tests found`, `--json` totals), pytest
  (exit 5, skipped/deselected-only), `go test` ("no test files", "no tests to run"),
  unittest (`Ran 0 tests`), Mocha (`0 passing`), cargo (`running 0 tests`), dotnet
  (`No test matches`). Recorded fixture outputs pin each one.
- **Named cases:** step-plan test commands gain `ids` (the test-spec case IDs the
  command must run, e.g. TC-9…TC-12) and optional `min_tests`. A focused command
  defaults to `min_tests: 1`. This is the rule the Battleship confirm had to grow
  by hand.
- **test-red becomes script-run:** each named new case must be reported as failing.
  An exit code alone, a compile error or a missing module is not red for the right
  reason.
- **Reuse key:** a record is reusable only for the same work item, command, cwd, tree
  and `env` digest (lockfiles, runtime and tool versions, the resolved target alias).
  A command marked `touches: remote` (org, network, deploy) is never reused. Any
  `prepare`, install or dependency change invalidates reuse. Records store both
  what ran and what was reused, and the report shows the difference.

### M2 Tree identity and path classes (E1)

Reuse the lint module: `shiploop_lint.snapshot_tree` (`add -A`, untracked included,
ignored and run-directory excluded), `capture_base` (per-item base tree) and
`_diff_scope` (changed paths). No new snapshot code.

- `complete` records `tree_after` on every accepted result. The history row records
  `changed_paths` since the item's base.
- **Path classes are package-owned:** `references/path-classes.json` ships in the
  skill, one profile per platform plus a generic one, and names classes `code`, `test`,
  `metadata-nav` (Salesforce tabs, apps and flexipages), `docs` and `config`. Discovery
  records which profiles apply; the model does not write them. A path with no class
  counts as `code`.

### M3 Not-applicable result with a cited check

- New result field `applicability: {"applies": false, "check": <record ref>,
  "reason": "…"}`, allowed only on stages whose packet printed a gate (M4). The outcome
  stays `done`.
- The script checks that the cited record exists for the current tree and satisfies
  the gate's printed condition. Otherwise it refuses and reprints the gate.
- Status and the run report show the stage as `n/a — <check>`; history keeps every
  stage.

### M4 Stage gates

`STAGE_GATES` in `shiploop_navigator_v3_prompts.py`, one row per stage:

- `skip_when(state, item) -> reason | None`: script-proven. The script writes a
  `skipped` history row with the reason and continues. Skips are recorded rows,
  so graph order stays linear: `_next_stage`, `validate`, status, the dry run and
  `shiploop_context_index` still walk every stage.
- `gate(state, item) -> text | None`: the printed applicability check.
- `guard(state, item, result) -> refusal | None`: after a stage is accepted, a
  condition that sends the item back (S2's scope guard).

### M5 References, not rereads

- One `References` block per packet: `label — path — what it answers — open when`.
  Example: `Run rules — run/rules.md — callbacks, recovery, delegation — open if they
  are not already in your context, for example after compaction.` "Read in full once
  per context" lines become entries like this.
- Run-level policy lines (locators, recovery prose, the delegation rule, the original
  request) move to `run/rules.md`. It is written at `init`, rewritten only when they
  change, and listed first with its digest.
- **Repeat `next`:** `run/last-packet.json` stores the action id, stage, revision and
  rules digest. A second `next` for the same action and stage prints: header, callback,
  status block, keepalive marker, what changed since that revision, the References
  block **and the stage prompt**. Only the run rules are replaced by their reference.
  A new action or stage, `init`, `resume`, `next --full`, or a host signal that
  context was compacted (Claude `SessionStart` with source `compact`, where the host
  provides it) prints the full packet.
- Stages cite recorded evidence (M1 records, accepted results) by path and tree rather
  than rerunning or rereading it (E4).

### M6 A question the run waits on

The run stays `active` while independent work remains; an open question is carried
in the status block. When the next step depends on the answer, the step ends
`blocked` with a question, and the existing quiet stop applies.

- A `blocked` result may carry `awaiting: {kind: answer|present, question | steps,
  options?}`. This is a field of the blocked result, not a new run status. The
  status block's `Stopped:` line prints the question or steps.
- The keepalive's "no progress" notice no longer says "Resume with" while the status
  shows an open question.
- `resume` on such a block requires `--answer "<the user's words>"` (kind `answer`)
  or `--observed "<what the person reported>"` (kind `present`). The reply is
  recorded verbatim in `run/decisions.md`. Otherwise `resume` is refused and the
  question is reprinted. `pause`/`resume` without an open question behave as today.
  `resume` rebinds the keepalive the same way `init` does.
- `references/keepalive.md` and the SKILL guidance: a message about the skill, the
  loop or its cost is neither an answer nor a resume.

## Work streams

One PR each against `main`, each with a `changes/<leaf>/<slug>.md` note, released
only through `scripts/release.py`.

### S1 Test runs that prove something (item 5) — M1

- Implement M1 in `shiploop_test_loop.py`: extend `normalise_commands`
  (`ids`, `min_tests`, `touches`), `verify` and the verify record, and add the
  recognisers.
- Make test-red script-run.
- Step-plan prompt asks for per-command IDs. `TEST_ITERATION` and
  `TEST_EXIT_CONDITION` add the zero-test and named-case rules (wording below).
- Tests: `test/shiploop-test-loop.test.py` with recorded outputs (all-skipped,
  no-match filter, deselected, missing IDs, uncounted, `min_tests`), plus test-red
  cases in `test/shiploop-navigator-v3.test.py`.

### S2 Test stages by evidence (items 1 and 3a) — M2, M3, M4

- **Declared paths:** step-plan results gain a required `paths` field (files or
  globs the item will change). The script validates it against the repository and
  classifies it with M2.
- Gates for the INNER test stages:

| Stage | Script-proven skip | Printed gate otherwise |
|---|---|---|
| test-spec (+ its Improve child) | The final accepted step-plan has empty `test_commands` with `test_commands_na`, **and** every declared path classifies as `docs`, `metadata-nav` or `config`. | "Run `shiploop classify --item <W>`. Write the spec unless it reports no code or test paths." |
| baseline | Same as test-spec, **and** no recorded suite covers the declared paths. | — |
| test-author, test-red | test-spec was skipped or n/a. | — |
| test-green | test-author was skipped **and** the post-implement diff has no `code` or `test` path. | — |
| test-refine, static-checks, integration-verify | Never skipped. Only their closing rerun of a recorded command may cite an M1 record (same key) instead of running it again. For static-checks the cited record must be a lint record. | — |
| regression | Never skipped when the project records a suite. It may cite an M1 record for the current tree and env. | — |

- **Scope guard (no reopen after implement):** if the item's test stages were
  skipped and implement's diff touches a `code` or `test` path, or any path outside
  `paths`, implement's `done` is refused. The model then either keeps the change
  within the declared scope, or reports `repeat` at step-plan to revise the item.
  After a revised step-plan with tests, test-red runs in a temporary checkout of the
  item's base tree plus the new test files, so red is still measured before the code
  it tests.
- **Improve changes are made and committed (owner rule 2026-09-26):** an Improve
  review changes code, tests or documentation wherever it finds a change warranted,
  and commits it. At `improve-complete` the script refuses the import while the
  candidate checkout has uncommitted changes to tracked or untracked non-ignored
  files outside the run directory. The refusal names the paths, unless the frozen
  binding carries an explicit no-commit override.
- **End-of-work Improve:** at import, if the tree differs from the latest `passed`
  record, the script runs the regression and lint commands before accepting. This
  covers the case where the final Improve child edits code after the last rerun.
- **Improve receipt wording (3a):** say that `final_result` is omitted when the
  result is unchanged (`shiploop_navigator.py` receipt text). Drop "This includes
  valid confirmation with no plan diff" except for the planning-experiment case.
- Update the readers that assume these stage results exist:
  `shiploop_context_index.py`, `shiploop_planning_context.py`, the dry-run
  fixture and `TEST_DECISION_STAGES`.
- Tests: `-v3`/`-v4` navigator suites (a decision item, a metadata-only item, a
  metadata item whose implement touches `.js` and is refused, a code item that is
  unchanged by its Improve review, an end-of-work Improve that edits code),
  the dry-run event counts, and status lines for `skipped` and `n/a`.

### S3 Questions and people (items 7, 8, 9) — M6

- Implement M6 in `shiploop_navigator.py` (result schema, `control`, status block),
  `shiploop_protocol.hook_status` and `shiploop_keepalive`.
- **Deploy question (8):** keep c5ac103's rule that a request naming the target is the
  grant. When a question is still needed, use the wording below: one yes/no question,
  with the scope stated as this run by default, so one "yes" can't be misread.
  Add `scope: run|standing` to `authority`; `standing` requires `kind: repo-policy`
  and a policy reference.
- **Person-present stop (9):** a `blocked` result at release-verify carries
  `awaiting.kind = present` with the App Launcher name, `/lightning/n/<Tab>`, the steps
  and what to report. `repeat` at release-verify is refused while it is open.
  `resume --observed` re-runs only the blocked behaviour rows against the same
  candidate; nothing is redeployed. No case is marked passed until the person's
  report is recorded.
- Tests: `test/shiploop-keepalive.test.py` (quiet stop on a question block; no
  "Resume with" while a question is open; a skill question does not resume; rebind
  after `resume --answer`), `test/shiploop-consumer-delivery.test.py` (scope),
  `test/shiploop-status-display.test.py`.

### S4 Release after a replan, and the consumer entry (items 2 and 6) — M1, M2

- **Redefine the barrier** in `shiploop_consumer_delivery.py` by path class of the
  corrective diff:
  - Any `code` or `test` path: today's full outer rerun.
  - Only `metadata-nav`, `docs` or `config` paths: system-test runs **delta-scoped**.
    It runs the new or changed obligations (for Battleship: the tab and app entry)
    and cites unchanged rows through `_preserved_observations` and M1 records for
    the unchanged tree paths. system-test-author and release-plan get delta Improve
    children that list only the changed rows. release-check runs the dry-run deploy
    of the new metadata, then release and release-verify run.
- The resume point and the reused stages are recorded as rows (`reused: <record>`),
  so graph order stays linear (M4).
- **Consumer entry (6):**
  - `references/platforms/salesforce.md`: `lightning__Tab` in `js-meta.xml` only
    makes a component eligible for a tab. A `CustomTab` plus app and tab visibility
    must be source metadata. Confirm with
    `sf org list metadata --metadata-type CustomTab`.
  - The release-plan prompt requires one **consumer-entry** row: how a person reaches
    the result, and which source files create it. The script refuses a release-plan
    without one.
  - release-check and `references/environment-lifecycle.md`: run each post-release
    confirm command once, before the real deploy, against current state, and record
    its "not there yet" output beside the dry-run deploy. A confirm command that cannot
    tell present from absent is fixed at release-check.
- Tests: `test/shiploop-v4-consumers.test.py` (a metadata-only corrective item: delta
  system-test and the release stages; a code corrective item: full rerun),
  `test/shiploop-consumer-delivery.test.py` (barrier by class),
  `test/shiploop-navigator-dry-run.test.py`.

### S5 References and the repeat packet (item 4) — M5

- Implement M5 in `render` and `dispatch`. Convert "read first" and "read in full once
  per context" lines across `shiploop_navigator.py`, `shiploop_navigator_v3_prompts.py`
  and `shiploop_test_loop.py` into References entries.
- Tests: `test/shiploop-packet-bounds.test.py`, `test/shiploop-delegation.test.py`,
  `test/shiploop-reference-routing.test.py` (every reference resolves), and a new case:
  a repeat `next` prints the short form with the stage prompt; a new action, `--full`
  or a compaction signal prints the full form. No packet-length assertions.

### S6 One Improve pass when nothing changed (item 3b) — owner decision

Only if the owner approves. The candidate tree is recorded at pass 1 start. At import,
if pass 1 is `trivial`, changed no file and the tree still matches, one `review_ref`
is accepted and the second pass is that script check. release-plan and the final
carry-forward keep two passes. Edits: `shiploop_standalone_improve.py` (streak and
`review_refs` checks), the navigator's `required_trivial_reviews 2` line, and
`skills/improve/references/review-policy.md`. That last one needs its own
`changes/improve/` note.

### S7 Planning knowledge kept in the repository (owner to-do 2026-09-26)

**Goal.** Planning produces a spec and environment knowledge that outlive the run.
The script stages and commits it in the product repository at the end of planning.
A later run that adds another feature starts from it instead of rediscovering it.

**Today** (verified): every planning result lives in the run directory, which is
outside the repo and never committed. The durable homes (`docs/requirements.md`,
`docs/current-system.md`, `SHIPLOOP.md`) are written only when the model follows
prose, and `references/project-knowledge.md` says "No commit/push is implied".
No script reads earlier knowledge; a new run finds it only through
`SHIPLOOP.md` links. `.shiploop/` cannot hold it, because the workspace return
refuses that path (`shiploop_workspace.FORBIDDEN_PARTS`).

**One home, `docs/shiploop/`:**

| Path | Contents | Lifetime |
|---|---|---|
| `docs/shiploop/README.md` | Index: what each file answers, the feature list, when each was last updated | Living |
| `docs/shiploop/spec.md` | The consolidated product spec: every accepted requirement with a stable ID, grouped by capability, and a `Retired` section | Living; each run preserves, adds, modifies or retires by ID |
| `docs/shiploop/environment.md` | Targets and accounts (non-secret names and aliases), the working test, deploy, dry-run and confirm commands, platform facts learned the hard way (for example "`lightning__Tab` does not create a tab; confirm with `sf org list metadata --metadata-type CustomTab`") | Living; facts carry the run and date that verified them |
| `docs/shiploop/test-strategy.md` | Harnesses, suites, the commands that own them, the ID convention | Living |
| `docs/shiploop/features/<YYYY-MM-DD>-<slug>/` | This run's feature record: `spec.md` (the delta: added, modified and retired IDs), `plan.md` (work items and each step plan), `test-spec.md` (case IDs to requirement IDs), `system-tests.md`, `release-plan.md`, `outcome.md` | Written once per run, then kept as history |

`SHIPLOOP.md` at the root stays the short index the packets already print, and
links to `docs/shiploop/README.md`. A product's own docs (README, an existing
requirements file the team maintains) are linked, never copied. Files that earlier
runs wrote in the old homes (`docs/requirements.md`, `docs/current-system.md`,
ShipLoop-authored only) move into `docs/shiploop/` at the first close, and
`SHIPLOOP.md` is repointed. That is the consolidation, done once per repository.

**Closes (script-owned; each stages exactly its paths and commits):**

| Close | When | Writes | Commit |
|---|---|---|---|
| C1 planning | `prepare` accepted (the execution worktree now exists) | `spec.md`, `environment.md`, `test-strategy.md`, the feature's `spec.md` and `plan.md`, README | `docs(shiploop): record <feature> spec and environment` |
| C2 item | each `test-spec` accepted | the feature's `plan.md` (that item's step plan) and `test-spec.md` | with a `docs(shiploop): record <item> test spec` commit |
| C3 release plan | `release-plan` accepted | `system-tests.md`, `release-plan.md`, environment updates | `docs(shiploop): record <feature> release plan` |
| C4 outcome | `handoff` accepted | `outcome.md` (what shipped, where, what a person still has to check), environment facts learned this run, README | `docs(shiploop): record <feature> outcome` |

- The script renders these files from accepted results, which the Improve reviews
  already checked. The model does not hand-copy them. Each close runs `git add --
  <exact paths>` and `git commit` in the execution worktree with hooks disabled
  (the `shiploop_workspace._git` helper). It never uses `git add -A`.
- Before committing, `shiploop_privacy` screens every file; a hit refuses the close
  and names the line. The environment file records alias names, never tokens,
  passwords or session URLs.
- The return plan marks `docs/shiploop/**` as `keep`, and the return is refused if
  a close commit would be dropped. A user's or repository's no-commit override is
  honoured: the files are still written and the status says they are uncommitted.

**Consolidating the living spec (the model's part, script-checked):**

- The spec stage's result must carry the full consolidated spec
  (`results/<action>-spec.md`). The model builds it from the prior
  `docs/shiploop/spec.md` plus this feature, keeping IDs stable.
- The script refuses a consolidated spec that drops a prior ID: every ID in the
  committed `spec.md` must appear as kept or modified, or under `Retired` with a
  reason. New IDs must not reuse retired ones. The feature `spec.md` delta is
  derived by the script from the ID diff.
- `environment.md` follows the same rule for its fact IDs. A fact this run could not
  re-verify stays, marked with the run that last verified it.

**Using it in this run:**

- **intake / discovery:** the packet lists `docs/shiploop/README.md`,
  `environment.md` and `spec.md` as references (M5), with "open when". Discovery
  re-verifies recorded environment facts with one cheap probe each, instead of
  rediscovering them, and records what changed.
- **spec / test-strategy / plan:** start from the committed spec and test strategy.
  The plan names which requirement IDs each work item touches.
- **step-plan / test-spec:** test IDs map to requirement IDs. Commands come from
  `test-strategy.md`, so an earlier run's working commands, with their `ids` and
  runner flags, are reused.
- **system-test-author:** existing cases for unchanged IDs are cited, not rewritten.
- **release-plan / release-check:** deploy, dry-run and confirm commands start from
  `environment.md`, including facts such as the CustomTab probe. That is what would
  have saved the Battleship replan.
- **handoff:** C4 writes what the next run needs: what shipped, what a person still
  has to check (for example TC-13 and TC-14 in a browser), and new environment facts.

**Using it in a later run:** a new feature run starts with the index and three living
files as references, a feature list for context, and requirement IDs to extend. It
does not import an earlier run's state; the files are evidence to read, consistent
with "an old artifact is evidence, not a protocol to import".

**Policy text to update** (it contradicts the owner's request):
`references/project-knowledge.md` ("No commit/push is implied"; "do not become a
second permanent product contract"), `references/state-files.md`,
`references/requirements-definition.md`, `references/current-system-baseline.md`,
and a superseded note on `docs/shiploop-requirements-retention-2026-09-17.md`
("not a permanent copy of every run spec"). The owner's 2026-09-26 decision keeps
both the living spec and each feature's record.

**Tests:** `test/shiploop-planning-handoff.test.py` (C1–C4 render, stage only
`docs/shiploop/**`, commit, privacy refusal, no-commit override), a real-Git return
test (the close commits reach the source branch; `docs/shiploop/**` is never
dropped), a consolidation test (a dropped prior ID is refused; a retired ID needs a
reason), and a second-run test (a new run's intake packet lists the committed files).

## Prompt wording

New and changed text follows the house tone of the existing prompts: plain sentences,
the reason given, no capitalised MUST or NEVER. Proposed text:

**Applicability gate** (default is to do the stage; n/a is the documented exception):

> Applicability check for this stage (this work item only): run
> `shiploop classify --item W3`. Do this stage unless the output reports no code or
> test paths. In that case, complete it as not applicable and cite the output file;
> ShipLoop checks it.

Avoid "skip" in packets, because it spreads to neighbouring stages; use "not
applicable to this item". Name an observable condition rather than a judgement like
"no code".

**Zero tests** (verify refusal):

> The command exited 0 but ran no tests (Jest reported 2 skipped). A filter that
> matches nothing is not evidence. Fix the filter or the test names so the output
> names TC-9, TC-10, TC-11 and TC-12. Running the whole suite instead does not
> satisfy this.

The last sentence closes the easy escape of dropping the filter.

**Improve review packet:** do not mention that an unchanged review saves test runs.
Say: "Change what is warranted in code, tests or documentation, and commit it;
ShipLoop reruns the affected checks." Otherwise a review may leave a warranted fix
undone to keep the reruns away.

**Deploy question** (only when c5ac103's rule does not settle it):

> May this run deploy the Battleship changes to org `de`
> (dev@example.com, Developer Edition)? It adds components, a tab and an app;
> it deletes nothing. Reply yes or no. A yes covers this run only. Say "standing" if
> it should also cover future runs of this kind.

One decision per reply. The scope has a stated default rather than a second
question.

**Waiting on a person** (status `Stopped:` line and the model's last message):

> Waiting on you: open the App Launcher, choose **Fleet command**
> (`/lightning/n/Fleet_command`), place a fleet and reload the page. Then tell me
> whether the board appears and whether your fleet is still there after the reload.

Written to the person, one action per step, and says what to report back. The model
does not mark the case passed from its own reading.

**Refused resume:**

> This run is waiting on an answer: "<question>". "Continue" does not answer it.
> Ask the user, then run `shiploop resume --answer "<their words>"`.

**Repeat packet header:**

> Same action as revision 138; nothing changed since. The run rules are in
> `run/rules.md`; open it only if they are not already in your context.

## Order

| PR | Stream | Depends on | Notes |
|---|---|---|---|
| 1 | S1 test runs that prove something | — | Safety net for everything that reuses or skips. |
| 2 | S3 questions and people | — | Independent; can go in parallel with 1. |
| 3 | S2 test stages by evidence | 1 | Ship 1 and 3 in one release with the single version bump. |
| 4 | S5 references and repeat packet | — | After 3, so the packet text is converted once. |
| 5 | S4 release after a replan, consumer entry | 1, 3 | Uses records, tree ids and path classes. |
| 6 | S7 planning knowledge kept in the repository | 4 (references) | Independent of the test work; can start after 4. |
| 7 | S6 Improve single pass | owner decision, 3 | Policy change in Improve too. |

Each PR registers new suites in `test/suite_catalog.py` (group list and timing map),
runs its footprint suites locally and CI's quick tier on push. The release commit
runs the full tier.

## Measuring it

- **Dry run:** `test/shiploop-navigator-dry-run.test.py` gets a Battleship-shaped
  scenario: one code item, one decision item, one metadata item, and a release-verify
  replan adding metadata. Record events after each PR. Target: the decision and
  metadata items fall from about 9 test-stage events plus an Improve child each to
  skip rows or one n/a check. The replan reruns system-test delta-scoped, not the full
  outer ladder.
- **Live:** after release, a comparable Salesforce run, compared with this run's
  140 revisions on revisions, Improve children, verify records reused vs run, and
  wall time.

## Out of scope, noted

- Decision and note items still walk implement, document and the rest of INNER.
  After c5ac103 such an item should rarely exist, so revisit only if a run shows one.

## Open decision

- **Improve single pass (S6):** when pass 1 changes nothing and the tree still
  matches, can that one pass end the Improve review? Recommended: yes for planning
  artifacts, with release-plan and the final carry-forward kept at two.

## Invariants no stream may weaken

- A stage is left out only on script proof. An unclassified path counts as code, and
  a gate's n/a is valid only with a cited check that matches its condition.
- A run that executes no tests, or not the named cases, never counts as passing.
- No reuse across a changed environment or for a command that touches a remote.
- No deploy without a recorded grant; the dry-run deploy precedes the real one; a
  passing unit suite is not delivery evidence.
- Every stage stays in the history as run, skipped (reason), n/a (check) or reused
  (record).
- Stale or conflicting action IDs and wrong verbs stay refused; the script picks the
  successor.
- Older runs are refused, not migrated.
- Planning knowledge is committed only under `docs/shiploop/`, by exact path, after a
  privacy screen; a prior requirement ID is never silently dropped.
