# ShipLoop Run Review journal

The living record of the Run Review tool (`skills/shiploop-run-review`): what changed, why, and the evidence. Add an
entry in the same commit as each change. Edit an entry later rather than deleting it: mark a claim superseded with the
date and the reason. Each finding carries a status (firm, interim, exploratory, superseded) and its citations
(commits, tests, evidence files). The redesign this journal follows is
[shiploop-run-review-redesign-plan-2026-10-04.md](shiploop-run-review-redesign-plan-2026-10-04.md); the governing spec
for the runs it reviews is `test/shiploop_e2e/SPEC.md`.

## 2026-10-04: R1, the code moves into its own skill leaf (no behaviour change)

Status: firm for what moved and what was run; the page itself was not republished.

**Why.** The owner asked for the Run Review as a skill. Its code lived inside `shiploop-e2e-audit` (`run-review/`:
README, SCHEMA, defaults, exporter, template), its README was the only procedure, and its tests sat in the audit
harness: `test_run_review` in `check_suite.py` `GROUPS['harness']`, and `test_run_review_template` in no group at all
(it ran only under the apparatus `--suite all`, which the quick tier never runs). A leaf gives the skill its own name
(`/skill-craft:shiploop-run-review`), a card that carries the procedure, and a test suite the catalog registers.

**What moved** (`git mv`, so history follows): `export.py` to `scripts/export.py`, `SCHEMA.md`, `defaults/` and
`template/` to the new leaf root. `README.md` became the procedure in `SKILL.md` (frontmatter, binding from the loaded
card, the six steps, the rules). The two harness test files became one suite, `test/shiploop-run-review.test.py`,
keeping all 22 tests; `test_run_review` left `GROUPS['harness']` (the group fails when a listed file is missing).

**What changed in the moved files, and only that.**

- `export.py` finds `defaults/` from the skill root (`Path(__file__).resolve().parents[1]`), because the file now sits
  one level below it. The module attribute `HERE` is gone (nothing used it but `DEFAULTS`).
- Two empty-state strings in the template named `run-review/README.md`; they now name the skill's `SKILL.md`.
- `SCHEMA.md` names the exporter as `scripts/export.py`.
- The tests resolve the skill from the repository root and read ShipLoop's stage table from `skills/shiploop` (they
  asked the audit harness's selected skill root before).

**Repointed.** `REVIEW_EXPORTER` in `test/shiploop_e2e/run.py` (still fail-open) and that module's docstring, the
`review_export` docstring; `REVIEW_README` in `test/shiploop_e2e/iterate.py` became `REVIEW_SKILL` (the README is gone);
two places in `test/shiploop_e2e/README.md`; the "After every run" paragraph of `skills/shiploop-e2e-audit/SKILL.md`.
This journal and the dated plan and comparison documents under `docs/` keep the old path where they record history.

**Registration.** `test/suite_catalog.py`: the suite in `_SHIPLOOP_PATHS` with a duration, and the prefix
`skills/shiploop-run-review/` in `_PREFIX_SUITE_IDS` selecting `shiploop-run-review` and `marketplace-package` (the
leaf-name rule skips the ShipLoop family, and a new leaf's release gate is the package build). `test-groups.test.py`
counts 66 ShipLoop suites and 106 in all, and pins the quick selection for `scripts/export.py` and `SKILL.md`.
Notes: `changes/shiploop-run-review/first-release.md` (`version: 0.1.0`, the version already in the new `SKILL.md`, as
`changes/README.md` requires of a new skill) and `changes/shiploop-e2e-audit/run-review-moved.md` (patch).

**Learning (firm).** The catalog assertion cannot live in the new suite. `suite_catalog._suite_sources` appends the body
of any `test/*.py` helper a suite names, so a suite that imports `suite_catalog` is selected by every change to a file
that module's text mentions (its docstring names `shiploop_keepalive.py`), and `test-groups` failed that quick case on
the first try (`skills/shiploop/scripts/shiploop_keepalive.py` selected `shiploop-run-review`). The pin went into
`test-groups.test.py`, which already imports the catalog; the new suite does not name the module at all.

**Evidence** (all from the worktree for this change, base `origin/main` c895d921):

| Check | Before | After |
| --- | --- | --- |
| Run Review unit tests | 22 OK (`skills/shiploop-e2e-audit/harness`, `-p "test_run_review*.py"`) | 22 OK (`python3 -B test/shiploop-run-review.test.py`) |
| `test/shiploop-e2e.test.py` (it imports the exporter hook); `-k Review` alone | 195 OK in 309 s; `-k Review` 9 OK | 195 OK in 309 s (it takes about five minutes, which the catalog's 0.7 s entry does not reflect) |
| `python3 scripts/build-packages.py` into a temp dir, then `scripts/check-marketplace-packages.py` | | exit 0 (`skill-craft: complete marketplace payload`); the package has `shiploop-run-review/scripts/export.py`, and `shiploop-e2e-audit` no longer bundles `run-review/` |
| `export.py --defaults` run from the built package | | exit 0, 21 expectation documents and `page`, `prompt` |
| `test/marketplace-package.test.py` | | 29 OK in about 3 s including its build, so the prefix mapping stays in the quick tier |

**Not done here.** No republish of the page, no data write, no push or release; R2 (snapshot the live database) is next
and must land before any data write.

## 2026-10-04: R2, the page database is snapshotted into the repo

Status: firm for what the snapshot holds; the live database was not read or written by this change.

**Why.** Findings, options, iterations, expectation revisions and the hand-built Backchain documents live only in the
artifact database, which contradicted the old README's durability claim. Nothing after this entry may overwrite or
delete a database document before this commit exists.

**What.** `test/shiploop_e2e/evidence/run-review-db-snapshot-2026-10-04.json`, schema `run-review-db-snapshot/v1`,
pulled from the artifact (`https://claude.ai/artifact/BFc6JGjLhENVJ9shRAA2iA`) at `pulledAt` 2026-10-04T23:47:48Z and
copied here unchanged (compact one-line JSON, byte-identical to the pulled file). 113,108 bytes. Rows keep the database
shape `{data, version, updatedAt}` under `docs/<collection>/<id>`, so a later restore can pin `if_version`. Counts:
observations 39, actions 16, expectations 30, iterations 10, backchain 4, runs 8, config 2, which is 109 documents.

**Where the hand-built records now live** (all in that file):

- Iteration states: `docs.iterations` I0, I1, I2, I2b, I2c, I2r, I3, I4, I5, I6. The plan says "I0 to I6"; the database
  also holds I2b, I2c and I2r.
- Expectation revisions: 10 `revs` entries across nine `docs.expectations` documents: `iter-I1` (1), `iter-I2` (2),
  `iter-I2b`, `iter-I2r`, `iter-I3`, `iter-I4`, `iter-I5`, `iter-I6` (1 each) and `phase-2` (1). Only `phase-2` is a
  stage expectation; the other eight revise an iteration's expectation.
- Hand Backchain documents: `docs.backchain.luna1-plan` (11 segments) and `docs.backchain.luna1-step-plan` (8). The
  collection also holds `luna0-plan` and `sonnet-none`, both with no segments.
- Run documents under the page's hand keys: `hello-1161`, `hello-1180`, `hello-1190a`, `hello-1190b`, `luna0`, `luna1`,
  `sonnet-battleship`, `sonnet` (the committed evidence files use the exporter's default keys; the plan's run-key
  step maps between them later).

**Difference from the plan (status: unexplained).** The plan quotes 129,263 bytes from an earlier saved copy; this
snapshot is 113,108 bytes. The per-collection counts are identical (39, 16, 30, 10, 4, 8, 2), so there is no sign that a
document was added or removed, but the two copies' contents were not compared. The size difference is unexplained:
re-serialising today's content gives 112,855 bytes (documents only, compact), 119,411 (default separators), 130,315
(data only, indent 1), 141,064 and 161,702 (documents only, indent 1 and 2) and others, and none is 129,263.

**Deletions.** None. No document id is listed for deletion, and no later increment may delete one without a new entry
here.

**Tests.** `DbSnapshotTest` in `test/shiploop-run-review.test.py` (4 tests): the schema id, the seven collections, a
counts header equal to the actual counts (109 documents); every document has a non-empty id and the row shape; the
records named above exist (ten iterations, 11 and 8 segments, 10 revisions in nine documents); and the file is compact
and byte-stable. All four fail on the R1 tip (the file is absent there); the 22 earlier tests pass.

## 2026-10-04: R3, counters a host cannot measure stop reading as zero (code and tests only)

Status: firm for the code and its tests; the live page, the committed v1 evidence and every real run are unchanged.
This increment does not do the plan's "Operations" part: no run was regraded, nothing was uploaded to the page, the
template was not republished, and no Artifact or ArtifactData call was made. The owner reviews a draft first.

**Defect (plan, "Never zero" and the Defects list).** `export.py` published `refusals = len(failures)` and
`glue = len(glue)` for every host. On a Claude run the harness records both lists empty because Claude's tool calls
arrive as `tool_use` blocks it does not read, and names them in `metrics['unmeasured']`; the exporter never read that
key, so 4 of the 5 committed evidence files carry `refusals 0, glue 0` for Claude runs, and the E2E peer reproduced the
same zeros in the real v1190-hello-sonnet `facts.md` ("failures: 0", "glue: 0 commands"). The header line would also
have printed "undefined refusals" for a document with the fields left out.

**What changed.**

- `export.py` reads `metrics['unmeasured']` (a map of counter name to the harness's reason). `refusals`, `glue` and the
  `failures` array are omitted when `shiploop_failures` or `model_glue` is named there; the run document carries the
  whole map as `runs.unmeasured` (`{}` when every counter was measured). `facts.md` prints
  "not measured (<reason>)" for both lines instead of a count.
- A `metrics.json` without the key raises `ExportError` ("no 'unmeasured' record ... measured zeros"). For a finished
  run it names the way out (`run.py --resume-run <dir>`, which starts no host for a done run); for any other status it
  does not name `--resume-run` (resuming an unfinished run would launch a host) and says to export after it finishes.
- The export id is `run-review-export/v2`. The schema table and `SCHEMA.md` make `refusals` and `glue` optional, add the
  `unmeasured` map of strings, document the export file, and make a stage's `min` nullable.
- Template: a new `<script id="logic">` block of pure functions (no DOM, storage, network or global read) with
  `countText(run, name)` ("not measured" or the number, a measured 0 stays "0"), `headerFacts(run)` (the header line:
  "13 refusals" or "refusals not measured", never "undefined") and `minutesText(min)` ("n/a" or "4.5 min"). The page
  script calls them, and the stage card is titled "packet and result file sizes" (`packetBytes` is a packet file's
  size, not what the model read). Later increments add `cardsFor`, `chipFor`, `buildPrompt` and `sequenceModel` to the
  same block.
- Tests: `run_logic(expression)` in `test/shiploop-run-review.test.py` runs only the logic block in a node `vm` context
  with no document, window, storage or network and returns the JSON value; later increments reuse it. It skips when node
  is absent (the pure-logic tests skip with it; the structural template tests still run).
- Existing fixtures gain `unmeasured: {}`. `test/shiploop-e2e.test.py` `ReviewExportTest` built a metrics file without the
  key and a state with an empty history, which the exporter now (correctly) refuses or draws with no rows, so its fixture
  gained the key and the one history row; its `run-review-export/v1` literal became v2.

**Nullable minutes (from the E2E peer, session E2E, `ledger-design-final.json`, `cheap_fixes_now` item 1).** Stage rows
are now built by iterating `state.md` history (the engine's own record) and looking each visit's accept stamp up in
`timeline.json` by action id, instead of iterating the timeline map. A visit's `min` is its accept minus the accept
before it (the first minus the run's start). A visit with no stamp, or right after a visit with no stamp (or the first
visit of a run with no recorded start), has `min` null: its interval is unknown, which is also how the harness's per-stage
attribution treats an incomplete row. `wallMin` runs to the last stamped accept. A timeline stamp for an action the
history never accepted no longer makes a row; a visit with no stamp owns no Backchain stage window (the loop ledger still
builds). The page draws a null minute as "n/a" with no bar (never a zero-width bar or "0"), keeps such rows under "Hide
stages under 1 minute", and says how many a total leaves out; `facts.md` counts them. Relation to the plan's R12: R12 later adds
`action`, `skipped` and `improve` to these same rows; this change only fixes how the rows and their minutes are formed.

**Limit found while checking (unexplained by this fix, needs a decision).** The peer's 96 seeded rows reading 0.0 min are
not unstamped. A read-only scan of 19 finished run directories (`/Users/dadleet/shiploop-e2e-runs/*` and
`/Users/dadleet/e2e-runs/20261003/*`, 539 history rows) finds 0 history rows without a stamp and 104 seeded rows (8 in each
of 13 runs, the visits whose result summary begins "Synthetic: recorded by the E2E seed"), every one stamped, within about a
second of the run's start. The exporter therefore still reads them as 0.0 min; the null rule never fires on today's real
data. Marking them needs a signal other than the stamp: the harness's own seed marker in the result summary (the plan
declined to parse summary text for `skipped`), or the harness's per-stage `timing: unavailable`, which the exporter
ignores by design. Not changed here.

**Real-data check (read-only).** `export.py` on `/Users/dadleet/shiploop-e2e-runs/chain-seeded-claude-e57b4d` (an older
`metrics.json` with no `unmeasured`) exits 2 with the finished-run message. A scratch copy of its `metrics.json`,
`result.json`, `invocation.json` and run directory with `unmeasured` set to a Claude-shaped map exports as
`run-review-export/v2` with 34 stage rows and no `refusals`/`glue`. Nothing under the real run directory was written.

**Browser check (static file, not the live page).** Opening the template from disk in the browser pane and injecting run
documents into its `data` shows the header line "refusals not measured | glue not measured" for a run without the
fields and "13 refusals | 0 glue" with them, and the stage card with "n/a" and no bar for two null-minute visits, a
4.5 min bar for the third, and "Total 5 min in 3 accepted stages (2 without a time: n/a)". Hide-under-1-minute keeps the
two null rows. The layout at 375 px was not rechecked (no layout change).

**Not changed.** The five committed evidence files keep `run-review-export/v1` (history; R13 re-exports them). The live
database still holds v1 documents with Claude `refusals 0, glue 0` and stage `min 0.0`; the page prints those numbers
until R13 uploads regraded v2 documents.

**Tests.** `python3 -B test/shiploop-run-review.test.py`: 38 tests, 12 of them new for R3 (omitted counters and reasons,
a measured Codex-shaped count of 13, the refusal and its status-dependent message, the v2 id and contract text, null
minutes after a missing stamp with the loop ledger intact, rows follow history, null first minute with no start, and five
logic-block tests including the no-DOM check). One existing test changed (`validate_doc` no longer requires `refusals`)
and the four template tests that assumed a single script now read two. All the new and changed tests fail on the pre-R3
tip (`826b8645`, whose `skills/` equals the R1 tip `62c36c73`), run from a git archive of it.

## 2026-10-04: R12, the exporter names each visit and measures the run (exporter, schema and tests only)

Status: firm for the code, the tests and the real-run proofs below. The template and the page are untouched: the
Improve card that reads the stage rows is the template side of R12 and is built on another branch, so until it lands the
page's old Improve block (which read the removed `improve` array) draws nothing. Nothing was pushed, released, regraded
in place or uploaded, and nothing was written under `/Users/dadleet/e2e-runs` or `/Users/dadleet/shiploop-e2e-runs`:
every proof ran on a copy made with `cp -p` in the session scratchpad.

**Why.** After R3 a stage row was `{stage, outcome, min, packetBytes, resultBytes}` with no identity, Improve time came
from the volatile worktree's review notes (Luna 135.8 min against 360.3 bind to receipt), a paused run read "active",
the harness's calls, context peak and compactions (R11, R15) were not exported, and the 104 visits the E2E seed records
read as 0.0 minutes. Base: `e79f948a`, which carries R1 (`62c36c73`), R2 (`826b8645`), R3 (`7144f355`) and the harness
work R10, R11 and R15 (the plan's "Defects found" lists these defects).

**What changed (`scripts/export.py` run-building code, `SCHEMA.md` run and stage-row section).**

- Stage rows gain `action` (the history entry's id), `skipped` (present only when true: `packets/` holds files and none is
  `<action>.md`; no summary text is read), `seeded` (present only when true, below), `improve {passes?, min?}` and
  `context {calls?, peak?, peakPct?, compactions?}`. A member that was not measured is omitted, never 0.
- `improve` per visit: `passes` is `improve/<action>/terminal.json` `progress.action_number`; `min` is the file-time span
  `improve/<action>-bind.md` to `improve/<action>/receipt.md`, omitted when either file is missing or the times run
  backwards. The join is exact: a child directory is named by the id of the action whose visit started it.
- Run level: `improvePasses` and `improveMin` (sums over every child; a sum with an unknown part is itself absent, with the
  reason in `unmeasured`; no child at all is a measured 0 and 0), `calls` (`model_calls`), `contextPeak`
  (`tokens.input_peak`), `contextWindow` (`window_tokens`) and `compactions`. Each is present only when the harness measured
  it; otherwise `unmeasured[<the run field's own name>]` carries the harness's reason (its `model_calls` and `window_tokens`
  reasons are renamed `calls` and `contextWindow`; a peak with no reason of its own takes the calls' reason; a metrics file
  that names none gets "metrics.json has no X figure and names no reason"). A calls, peak or window of 0 is not a
  measurement (the old harness wrote 0 defaults); a compactions of 0 is.
- `status` `paused` (it mapped to `active`); the time text reads "paused after ...". The `improve[]` array, the
  `improve_reviews` read and the volatile review-note count are gone; `imp` is built from the durable files.
- `facts.md`: the run line splits work, skipped and seeded when either exists; the Improve line carries passes, minutes and
  the most passes in one child (or "not measured (reason)"); a new "Model calls (main thread only)" line; the "Stages with
  no minutes" count leaves out seeded visits; a "Seeded visits not marked" line says why when result.json's seeded block
  does not match.
- `SCHEMA.md` documents every new field with its optional/null rule and labels two things: a Codex peak is a call's total
  tokens (input plus that call's own output) while Claude's is input side, so for the same context Codex reads higher by
  the output share (Luna's heaviest call is 251,867 total tokens; the input side alone peaks at 244,669, 2.9% lower), and calls and context are the main thread only (chain
  workers and Improve agents report elsewhere). Documented and not guarded: file-time spans on a copied directory (`cp -p`),
  host-kill gaps inside a visit, a recreated `timeline.json`.

**(a) Per-visit context, and the join key.** The harness's per-stage rows (`metrics.json` `stages`, from `per_stage`) carry
`stage`, `outcome` and the counters, and a Codex run's rollouts add `context {calls, peak, peakPct, compactions}`
(`rollouts.rollout_context` `perStage`); the row's `action` the harness reads in `stage_results` is dropped before the row is
written. A Claude run's stage rows carry turns, tool calls and seconds only: no per-stage peak exists for Claude. So the key
the exporter can reproduce is the harness's own: one row per `state.md` history entry in order, plus a trailing `incomplete`
row for the stage a run stopped in. The exporter takes row *i* to history entry *i* and puts the context on that entry's
action id. It uses the join only when the number of non-`incomplete` rows equals the number of history entries and every
row's (stage, outcome) equals that entry's (stage or "?", outcome); otherwise no visit gets a context and
`unmeasured.visitContext` says the rows do not line up. When no visit has one (every Claude run, a Codex run with no
rollouts) `visitContext` carries one reason. The harness itself was not changed (adding `action` to its rows would change a
file other tools read; it is an easy follow-up and would make the join by id; the exporter would then check the id instead
of the position). Stage names are never the key: Luna repeats them (test-spec 140 and 137 calls, step-plan 355 and 40,
implement eight visits of 22, 14, 25, 13, 23, 18, 22 and 15 calls) and every repeat kept its own figures.

**(b) Seeded visits read null.** `result.json` `seeded.skipped` (the harness's `seed_run` record) lists the stages the seed
recorded without doing them; they are the first `len(skipped)` history rows. When their stage names equal the list in order
those rows get `seeded: true` and `min` null and are counted in neither work nor skipped; otherwise none is marked and
`facts.md` names the mismatch (or a `skipped` that is not a list of names). The visit after the last seeded one is timed from
the seeded visit's own stamp, so the first real visit keeps a true duration (chain-seeded-claude-e57b4d: step-plan 2.5 min).
Summaries are never read.

**(c) A negative delta reads null.** A visit whose accept stamp is earlier than the one before it has `min` null (not
negative, not clamped); the next visit is timed from that stamp. The same rule makes an Improve child's span unknown when
receipt is earlier than bind. `wallMin` is not guarded (start to the last accept; it would be negative only if the last
stamp preceded the run's start).

**Real-run proofs (read-only; copies in the scratchpad `rrx/proof/`, `cp -p` so file times hold).** A copy's old
`metrics.json` was replaced by `metrics.collect` run over the copy with this tree's harness (R11 and R15), which for Luna
reads the three rollouts through a symlink to the original `home/` (0.7 s).

| Run | Visits | Improve | Calls, context | Other |
| --- | --- | --- | --- | --- |
| Luna 1.16.1 battleship (`20261003/v1161-battleship-luna`, blocked) | 39, 0 skipped, 0 seeded | 9 children, 41 passes, 360.27 min (31.1% of 1,158.5 min wall); per child spec 4/36.83, test-strategy 11/66.42, plan 3/39.18, step-plan 3/21.28, test-spec 5/54.52, step-plan 1/13.96, test-spec 8/45.32, carry-forward 3/53.28, system-test-author 3/29.48 | calls 2,565, peak 251,867 of 258,400, 34 compactions; 39 of 39 visits carry a context, their calls sum to 2,562 (three calls after the last accept belong to no visit) and their compactions to 34; heaviest visit static-checks, 52 calls, peak 251,867 (97.5%), 1 compaction | refusals 13, glue 20; unmeasured: cancelled_tool_calls, knowledge_reads, stage_turns, truncated_outputs |
| hello 1.19.0, second run (`20261004/v1190-hello-sonnet-2`, done) | 54: 47 work, 7 skipped (test-spec, baseline, test-author, test-red, test-green, test-refine, regression; 0.0 min each) | 11 children, 19 passes, 3.73 min (the rows sum to the same) | calls 149, peak 271,220 of 1,000,000; compactions absent with the harness's reason; no visit has a context, `visitContext` says why | refusals and glue absent with reasons; 15.2 min wall |
| seeded chain, skill-craft 1.16.0 (`shiploop-e2e-runs/chain-seeded-claude-e57b4d`, done) | 34: 26 work, 0 skipped, 8 seeded (intake to select-work) with `min` null | 22 min wall | calls 225, peak 348,202 | 7 of the 8 seeded visits have no packet |

The old Luna `metrics.json` is refused as designed (exit 2, "no 'unmeasured' record"); hello-1190-2's on-disk file has no
`unmeasured` record either (and no `model_calls` or `window_tokens`), so both needed metrics regenerated over a copy. All three plan numbers
held: Luna 9 children, 41 passes, about 360.3 min (360.27); hello-1190-2 11 children, 19 passes, 3.73 min, 7 skipped of 54;
Luna calls 2,565, peak 251,867 of 258,400, compactions 34.

**Where the plan was incomplete.** "13 harness-seeded visits have a packet and so are not marked skipped" is true and
misleading: it is one per seeded run (the intake, whose packet `workspace start` issues). A read-only scan of every run
directory under `shiploop-e2e-runs` and `e2e-runs/2026100*` finds 96 seeded visits in 12 runs (the earlier scan's 104 in 13
includes `fanout-claude-a67220`, which has no `state.md` the exporter can find): result.json's names match the history in
order in all 12, 12 of the 96 have a packet and 84 do not. The packet-absence rule alone would have marked those 84 as
engine-skipped; the seeded rule takes precedence, and the other 592 visits mark 7 skipped, all hello-1190-2's. Across the 22
runs that have Improve children, none has a child with an unknown part, so the "sum with an unknown part is unknown" rule
never fires on today's data.

**Needs an owner decision, not changed here.**

- `_no_unmeasured_message` still tells a blocked run it "cannot be regraded without a host: export it after it finishes".
  Since R10 a blocked run is regraded by `run.py --resume-run DIR` without a host (that is how Luna's file is refreshed in
  R13), and the R3 test pins the old wording for blocked. One line and one assertion to change when R13 runs.
- The run-level reasons for the new measures sit under the run's own names (`calls`, `contextWindow`, `contextPeak`,
  `compactions`, `improvePasses`, `improveMin`, `visitContext`), while refusals and glue keep the harness names
  (`shiploop_failures`, `model_glue`): the template reads each accordingly.

**Tests.** `python3 -B test/shiploop-run-review.test.py`: 61 tests (38 before, 23 new in `RunVisitsTest`); four existing
assertions changed because the contract did (rows gain `action`, the `improve` array is gone and `imp` comes from the
terminal files, the run's `unmeasured` gains `visitContext` when no stage row has a context). Every new test fails on the
base tip `e79f948a` (run from a `git archive` of it). `python3 -B test/shiploop-e2e.test.py -k Review` (9 OK; the fixture
needed no change), `node test/skill-frontmatter.test.js`, `python3 -B test/test-groups.test.py`,
`python3 -B test/marketplace-package.test.py` and `scripts/check-release-boundary.py --base origin/main` pass.

## 2026-10-04: R13, five finished runs regraded with no host and re-exported as v2 evidence

Status: firm for the numbers, the key mapping and the tests below. Local commits only: nothing was pushed or released,
no E2E run was launched, no Artifact or ArtifactData call was made and nothing was uploaded, so the live page and its
database are untouched (the plan's "upload the run docs" step is still open, see "Before an upload" below). Base:
`c3ca793c`, which carries R1 (`62c36c73`), R2 (`826b8645`), R3 (`7144f355`), the harness work R10, R11 and R15 (`e79f948a`)
and R12 (`c3ca793c`).

**Why.** The five committed evidence files were v1 exports: Claude runs published refusals 0 and glue 0 as measured
zeros, Luna's Improve time came from the volatile worktree's review notes (135.8 min), seeded and skipped visits read as
0.0 minutes, stage rows had no action id, and none of them carried calls, context peak or compactions. R3 and R12 fixed
the exporter; this increment applies it to the five real runs, which needed their `metrics.json` regraded first (an old
file with no `unmeasured` record is refused by design).

**Regrade (no host).** Per run: `result.json`, `metrics.json`, `transcript.md`, `mismatch.md` (where present),
`review-export/` and Luna's `home/.gitconfig` were copied aside with `cp -p` into the session scratchpad
(`.../scratchpad/rrr/backup/<run>/`, with a before-listing of file times), then each run was regraded with this
worktree's harness: `python3 -B test/shiploop_e2e/run.py --resume-run <run dir>`, run from a scratch directory (not a
repository) with `PYTHONDONTWRITEBYTECODE=1` so the case checks leave no bytecode in `work/`. Luna's run is status
blocked, which only R10 lets `--resume-run` regrade; no gate refused any of the five (no version gate applies to a
regrade: `run.py` sets `versions` from the run's own record and `regraded true`). The Luna exit code 1 is the run's own
FAIL verdict (blocked, plugin and committed false), not a refusal; the four hello regrades exit 0 (PASS).

**How "no host started" was verified.** (1) The regrades ran with `PATH` set to a directory of trap scripts named `claude`,
`codex` and `grok` (each logs a line to `host-invoked.log` and exits 97), then `python3` and `node` links, then
`/usr/bin:/bin:/usr/sbin:/sbin`; the harness starts a host by the bare binary name, so any launch would have logged. The
log does not exist after all five regrades. (2) Every printout says "process ... no host ran: regraded"; each new
`result.json` carries `process.regraded true`, and the process block is the original's, with its single session
(Luna's 33,452.4 s `codex` session; each hello's one `claude` session), not a new one. (3) `events.jsonl`, `timeline.jsonl`,
`stderr.txt`, `invocation.json` and `host-prompt.txt` have unchanged times in all five run directories, and Luna's
rollouts under `home/.codex/sessions` are unchanged. (4) A regrade needs `~/.codex/auth.json` to exist for a Codex run
(`CodexHost.env` links it into the run's `home/.codex`, reads nothing from it and runs no `codex`), so it needs no Codex
login and no installed `codex`, but it does exit "Codex is not signed in" when that file is absent. What a regrade does
start: the case checks in `work/` (`python3 hello.py`, `python3 -m unittest -q`; Luna's four node checks, with local
servers on ports 39171 to 39173, all failing as the run has no product) and, for Luna, the same checks in ShipLoop's own
worktree (4 of 4 pass there). Those are the product's tests, not hosts.

**What a regrade rewrites in a run directory.** `result.json`, `metrics.json`, `transcript.md`, `review-export/` (under
the exporter's default key, as `run.py` always does; Luna's `mismatch.md` is new because it FAILs), plus new files the
harness writes on any `--resume-run`: `invocation-resume-<host>-<epoch>.json` (and `resume-codex-<epoch>.txt` for Codex),
and, for Luna (Codex), `home/.gitconfig` rewritten with identical bytes. Git's index of the Luna work tree was refreshed. Nothing else changed
(`work/` status is clean in all five). `test/shiploop_e2e/baselines.jsonl` was not touched (a `--resume-run` appends no
row, `run.py` sets `baseline_file` only for a run that is neither resumed nor seeded); its sha256 is identical before and
after (3172c232...0e34cf, 15 rows) and `git status` shows no change to it.

**Run to key mapping.** The page's database already holds a run document per hand key; each run was matched on release,
host, model, case, status, `startedAt`, `endedAt` and `wallMin` against `docs.runs` of the committed snapshot
(`run-review-db-snapshot-2026-10-04.json`), which agree exactly for all five, and on the stage count (39, 35, 34, 34, 54).
Each run was re-exported with `--key`, and also `--name` and `--order` from that document (the four Claude files already
carried the page's name and order; Luna's carried the exporter's defaults), so uploading a file updates the page's
document in place and creates no second one.

| Run directory | Page key | Name and order on the page | Committed file (name kept) |
| --- | --- | --- | --- |
| `e2e-runs/20261003/v1161-battleship-luna` (codex gpt-6-luna max, 1.16.1, blocked) | `luna1` | Luna max, release 1.16.1; 3 | `codex-gpt-6-luna-1.16.1-battleship-20261003.json` |
| `e2e-runs/20261003/v1161-hello` (claude, 1.16.1) | `hello-1161` | Sonnet 5.5 hello, release 1.16.1; 11 | `claude-claude-sonnet-5-5-1.16.1-hello-20261003.json` |
| `e2e-runs/20261004/v1180-hello-sonnet` (claude, 1.18.0) | `hello-1180` | Sonnet 5.5 hello, release 1.18.0; 12 | `claude-claude-sonnet-5-5-1.18.0-hello-20261004.json` |
| `e2e-runs/20261004/v1190-hello-sonnet` (claude, 1.19.0, gate run) | `hello-1190a` | Sonnet 5.5 hello, release 1.19.0 (gate run); 13 | `claude-claude-sonnet-5-5-1.19.0-hello-20261004.json` |
| `e2e-runs/20261004/v1190-hello-sonnet-2` (claude, 1.19.0, repeat) | `hello-1190b` | Sonnet 5.5 hello, release 1.19.0 (repeat); 14 | `claude-claude-sonnet-5-5-1.19.0-hello-20261004-b.json` |

The files keep the names the exporter's default key gave them (host, model, release, case, date), so there is still one file
per run and the planned review file `codex-gpt-6-luna-1.16.1-battleship-20261003.review.json` sits beside the Luna export;
the run document inside carries the page's key, so a file name is no longer equal to its run id (needs an owner decision,
below). The default key of the two same-day 1.19.0 runs is the same string, which is why the old second file ended in `-b`
and why an explicit `--key` matters for a second run of the same host, model, release, case and day.

**Before and after** (before: the committed v1 export at `c3ca793c`; "stored" values are what that export carried; the
run's old `metrics.json` was refused by the exporter, so the new figures come from the regraded one). Luna wall time
1,158.5 min. Improve minutes are bind to receipt; before, the sum of the old `improve[]` seconds.

| Run | Refusals | Glue | Improve passes and minutes | Calls | Context peak (window) | Compactions | Other |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Luna 1.16.1 | 13 before (the 1.16.1 record), 13 now | 21 stored (stale), 20 now | 41 passes, 135.8 min before, 360.27 min now (31.1% of wall) in 9 children | not exported, 2,565 | not exported, 251,867 (258,400, 97.5%) | not exported (the old `metrics.json` said 0, a figure nobody measured), 34 | verdict `committed` true before, false now; 39 of 39 visits carry a context |
| hello 1.16.1 | 0 before (a false zero), absent now with the reason | same | 8 passes, 0.0 before, 0.84 min now | 84 | 182,666 (1,000,000) | absent with reason | 35 visits |
| hello 1.18.0 | same | same | 18 passes, 1.2 before, 2.84 min now | 94 | 225,425 (1,000,000) | absent with reason | 34 visits |
| hello 1.19.0 gate | same | same | 14 passes, 0.4 before, 2.69 min now | 113 | 239,826 (1,000,000) | absent with reason | 34 visits |
| hello 1.19.0 repeat | same | same | 19 passes, 1.0 before, 3.73 min now (24.5% of 15.2 min) in 11 children | 149 | 271,220 (1,000,000) | absent with reason | 54 visits, 7 skipped (test-spec, baseline, test-author, test-red, test-green, test-refine, regression; 0.0 min each; the old file had 8 zero-minute rows, one of them a real 1 s visit); no run has a seeded visit |

Every stage row now has `action` (all ids unique in each run). The old Luna file said `refusals 13, glue 21`; the glue is 20
under the current harness and 13 refusals are unchanged. Luna's per-visit calls sum to 2,562 (three calls follow the last
accepted visit) and their compactions to 34. The plan's numbers all held; none needed correcting.

**Findings.**

- Luna's regraded process record still covers only the resume session (firm; recorded, not a code change). `result.json`
  `process` is the original block (one `codex` session, 33,452.4 s, `pass true`, `resumes 0`), kept as recorded and marked
  `regraded`; the run's wall time is 1,158.5 min (69,510 s), so it describes about 48% of a 19.3 h run (the first session
  ended at its 10 h timeout and is not in it). The `process` chip therefore reads pass for a run that blocked after 19.3 h;
  the regraded `termination` block says "not observed (regraded: no host ran)".
- Luna's `committed` verdict flips from true to false (firm). The stored record predated the rule that HEAD must hold at
  least one file; the blocked run never returned a product, so HEAD is the empty baseline commit (`head_files 0`). The
  `plugin` verdict was already false ("none loaded") and is unchanged. The page's Luna chips change when this is uploaded.
- A Codex regrade needs `~/.codex/auth.json` to exist (see above); a machine without it refuses the regrade with the
  harness's own message. Not changed (an environment property, and the fresh-run path needs it anyway).
- Re-exporting Luna under the key `luna1` makes the two Backchain document ids `luna1-plan` and `luna1-step-plan`, the same
  ids as the page's hand-built documents (11 and 8 segments of per-pass judgement the exporter cannot rebuild; the
  exporter's own documents have 9 and 6). See "Before an upload".

**Before an upload (open).** The run documents of all five update the page's existing documents (pin `if_version` from the
snapshot's rows). The two Luna Backchain documents must not be uploaded over the hand-built ones: skip them or merge by
hand. The old files carried them under the default key (`codex-gpt-6-luna-1.16.1-battleship-20261003-plan`), where an
upload created extra documents instead of overwriting the hand ones.

**Exporter wording (the owner decision R12 recorded).** `_no_unmeasured_message` told a blocked run it "cannot be
regraded without a host", which R10 made untrue. A blocked run now gets "Regrade the blocked run (python3
test/shiploop_e2e/run.py --resume-run DIR; a regrade starts no host and does not resume the run), then export it again."
A finished run's message is unchanged, and an active or paused run still never names `--resume-run` (resuming it would
start a host); it now says "not done or blocked" and that resuming it would start a host.

**Tests.** `python3 -B test/shiploop-run-review.test.py`: 68 tests OK (61 before, 7 new in `CommittedEvidenceTest`). The
new class loads the five committed files and asserts: id `run-review-export/v2` and one run document under the page's
key that validates and agrees with the snapshot's document on release, host, model, case, status, `startedAt` and
`endedAt`; every stage row has a unique `action` and a seeded visit would read `min` null (none exists); each of
`refusals`, `glue`, `calls` and `contextPeak` is a number, or absent with a reason under `shiploop_failures`, `model_glue`,
`calls` or `contextPeak`, never both; the Improve rows sum to the run's passes and minutes; Luna has 39 stages, 41
passes in 9 children, 360.3 min (plus or minus 0.1), refusals 13, glue 20, calls 2,565, peak 251,867 of 258,400 and 34
compactions; the four Claude hello runs omit refusals, glue, failures and compactions with a reason and have calls 84, 94,
113, 149 of a 1,000,000 window; hello 1.19.0 repeat has 54 visits with the 7 skipped, 11 children, 19 passes, 3.73 min
(plus or minus 0.1) and calls 149, peak 271,220. The blocked-run case of the existing no-`unmeasured` test now pins the new
wording and a paused case was added. Run from a `git archive` of `c3ca793c` outside the repository (v1 evidence, old
wording) the file gives 15 failures, all new: the seven loader tests (the five files of the first fail on the schema id, the rest on the
missing page key) and the blocked-wording case. `python3 -B test/shiploop-e2e.test.py -k Review` 9 OK, `node
test/skill-frontmatter.test.js` PASS 20 skills, `python3 -B test/test-groups.test.py` 16 OK and
`python3 -B scripts/check-release-boundary.py --base origin/main` OK. The whole `test/shiploop-e2e.test.py` was not run:
nothing under `test/shiploop_e2e` changed except the evidence files.

**File sizes** (bytes; v1 then v2): Luna 9,816 then 14,660; hello 1.16.1 5,009 then 8,031; hello 1.18.0 4,937 then 7,911;
hello 1.19.0 gate 4,949 then 7,926; hello 1.19.0 repeat 6,797 then 10,748; total 31,508 then 49,276. Each is under the
exporter's 200,000-byte compact limit.

**Owner decisions.** (1) File names: keep the default-key names (chosen: the plan's review file uses that name and there is
one file per run) or rename the five to the page keys (`luna1.json`, `hello-1161.json`, ...), which would make a file name
equal its run id and the Luna review file `luna1.review.json`. (2) The two Luna Backchain documents at upload (above).
(3) Whether to upload now: the page would then show the regraded Luna chips (`committed` false, 360.27 Improve minutes,
refusals 13, glue 20) and drop the Claude zeros for "not measured".
## 2026-10-04: R4, the page is four steps (template, contract and tests; not republished)

Status: firm for the code and its tests. The live page and its database were not touched: no Artifact or ArtifactData
call was made, nothing was published, uploaded or released. The owner reviews the template as a draft first.

**Why.** The page was eleven sections about five different things (plan, "The guided flow"). This increment reorganises
today's page into the agreed four steps without changing the data: 1 What happened (run selector, phase chevrons, run
detail, Backchain loop cards), 2 Expected versus seen (the contract, as a disclosure, and one card per expectation), 3
Findings and options (the existing observation and action cards and forms), 4 Your plan (the prompt). One step shows at a
time, a stepper of four buttons shows live counts (`3. Findings and options`, `39 findings, 3 ticked`), Back and Next
end each step, and on a phone (640 px and narrower) a sticky bar reads `N ticked` with a `Your plan` button.

**Removed (no hiding, no shim).** The UML process diagram (`renderSequence`, `SEQ_ACTORS`, its words list), the
iterations section and `renderIterations`/`iterCard`, the "when something unexpected happens" section with its prompt
text, the include toggles and the synthesize or concatenate mode (and `concatPreamble`), the global expectation-status
editor (`statusSeg`) and the inline expectation editor (`openEdit`, `submitEdit`, `saveExp`), the `iterations`
collection subscription (so the page reads six collections), the per-observation "revise the expectation" buttons, and
the old `slrr4` localStorage record (the new one is `slrr5`; an old record is simply not read). Expectation wording is
now only read on the page: step 2 shows each criterion's text, its revision history and the findings tagged to it, and
`SCHEMA.md` says changing one is an option applied from the repo (R5 to R7 build that). The `iterations` collection
leaves `SCHEMA.md` and the validator's table; a database that still holds it keeps it (the committed snapshot preserves
every iteration and revision) and nothing reads it.

**Working set.** The step, filters, compared run and, per run key, the ticked options and findings, the "after the plan"
choice and the notes live in this browser's localStorage under `slrr5` (every access in a `try`; the page works with it
empty or garbage). A tick on one run is not a tick on another. `after` now defaults to waiting for the owner's go-ahead
(the plan's owner decision) instead of executing.

**Interim prompt (replaced in R7).** With the toggles gone the old string building stays only as a short interim: the
selected options and findings, one plan, the constraints, the notes and the closing. The blocks the toggles governed are
dropped rather than hard-wired on: the revised-expectations dump (the 7,060-character defect), the "not holding"
status block (no status is set any more) and the Backchain tally sentence. R7 writes the real builder.

**Run fields read defensively (from the exporter work in parallel).** The pure logic block gained `reasonFor`,
`measuredText`, `grouped`, `contextText`, `factRows` and `improveFacts`. The run detail now lists, from the run document,
host, model, effort, case, status, `Elapsed (accept to accept)`, start and end, then always `Model calls (main thread)`,
`Context peak (main thread)` (as a share of `contextWindow` when both exist) and `Compactions`: a number, or `not
measured` followed by the reason from `run.unmeasured[name]`, never a zero. The Improve card reads the stage rows'
`improve {passes, min}` and the run's `improvePasses` and `improveMin` (`19 review passes in 11 visits, 3.7 min, 12% of
elapsed`); with no total it says `Improve passes: not measured` and the reason, and a visit with passes but no minutes
shows `n/a`. The old `improve[]` array is not read (documents exported before that field change read `not measured`
until they are re-exported). The stage table appends `, skipped` and `, N Improve passes` to a row's outcome when the
row carries them. The packet and result sizes keep their R3 label.

**Bug found by the tests.** `plural(n, "pass")` printed "3 passs"; it now adds `es` after an s.

**Tests.** `python3 -B test/shiploop-run-review.test.py`: 48 tests (38 before; 10 new, all 10 fail on the base tip
`e79f948a`, run from a `git archive` of it with only the new test file copied over). The new ones: the template has
exactly four `section class="step"` elements and none of 21 removed ids, functions and strings; the page and the
contract no longer mention iterations; one step shows at a time with live stepper counts, `aria-current`, Back and
Next; the step and ticks survive a reload per run, garbage storage is ignored, and every `localStorage` use is in a
`try`; a tick is kept for its run only and the sticky bar counts it; the run detail reads the new fields (absent: `not
measured`; present: numbers and a percentage; a reason is shown); and four logic tests for the new pure functions.
A small DOM stand-in (`PAGE_STUB`, `page_probe`) lets a test run the page script in node, set the documents and look at
what it drew; it has no layout or events, so the visual check is done in a browser at R7. One existing test changed
deliberately: the documented-collections check no longer expects an `iters` subscription.

**Size.** `template/index.html` is 57,754 bytes (76,339 before): the removed sections outweigh the new step shell and
logic. Budget for R5 to R7: about 75 KB.
