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

## 2026-10-04: R5, findings and options with their pictures (template, contract, validator and tests; not republished)

Status: firm for the code and its tests. As for R4, no Artifact or ArtifactData call was made and nothing was published,
uploaded or released; the live page and its database are untouched.

**Contract.** `observations` (the page's findings) gain `runs` (the run keys it applies to, overriding `run`), `effect`
(`broken` or `bent`: how an OPEN finding hits its expectation), `advice` and `figure`. `actions` (the page's options)
gain `findings`, `kind` (`fix-shiploop`, `fix-harness`, `change-expectation`, `gather-evidence`, `accept`), `effort`
(`S`, `M`, `L`), `recommended`, `cost`, `change {target: page|spec, to, reason}` and `ref`; `status` is now the enum
`open`, `planned`, `built`, `done`, and `base` is no longer read or written. `validate_doc` enforces all of it
(`SCHEMA` table in `scripts/export.py`; two new spec kinds, `object` and `figure`) and `SCHEMA.md` documents it in
tables. The live database still holds the old status words (`building`, `analysed`, `waiting`); the page shows any
status string it is given, and R9's data update normalises them. The cross-field rule (`change` present exactly for
`change-expectation`) is left to R8's `--check`, as the plan says.

**Step 3 as data.** The pure `cardsFor(state)` groups every option once: under the first of its `findings` that is in the
current view (the other findings in view show a reference chip), apart in `loose` when it names no existing finding, in
`elsewhere` when all its findings are outside the filter (the page says how many), and done options in `done`
(listed under "Already done"). Options rank recommended first, then kind in the order above, then effort, then as
given. An open finding that no option of any status names is flagged `noOption` and offers "No option yet. Ask Claude to
propose options" (a tick that step 4 turns into an INVESTIGATE line). The four filters are `open for this run` (the
default), `all for this run`, `other runs` and `general` (`run: any` and no list); a finding applies to a run when its
`runs` list names it (or `any`), or, with no list, when its `run` is that key, `any` or empty; a missing `status` reads as
open. "Tick recommended" ticks the recommended option of each open finding in view. A tick on an option that is gone or
done, or a finding that is gone, is dropped with a notice, but only when the database is live (an empty read must not wipe
a viewer's ticks). The old flat observation and action lists are gone; the phase panel in step 1 now lists a compact row
per finding that jumps to its card, so no section draws the same finding twice.

**Illustrations (the owner's request, asked twice).** Every finding card carries a picture next to its technical box
(Expected, Saw, Evidence, Expectation with its S-clauses), and the picture never replaces that text.

- `whereStrip(run, finding)`, automatic for any finding with a `phase`: one cell per visit of the run, in order, 14 px
  pitch so Luna's 39 visits are 562 px wide inside a scroller; colour by outcome, a letter under any visit that did not
  finish done (R revise, P replan, B blocked), skipped or seeded visits dashed and hatched, the cells of the finding's
  phase outlined and bracketed and labelled (`Plan: 5 of 39 visits`; the label hangs from the right end when it would run
  off the strip). It needs no authored data. The visit-to-phase table `STAGE_FLOW` lives in the logic block, equal to the
  exporter's `PHASES` (a test compares them; an unknown stage takes the phase of the visit before it, as the exporter
  does). Drawn from the chosen run, or the first run the finding applies to.
- `figureSvg(figure)`, from an optional authored `figure {kind: "bars", items: [{label, value, unit?, lowerBound?,
  tone?}]}`: expected and seen numbers side by side on one scale; a `lowerBound` item prints `>=` and ends in an open
  chevron; a measured 0 draws a stub, never a missing or NaN bar. Strictly structured: unknown kinds and fields,
  negative or non-finite values, a non-string label and more than 6 items are rejected by the validator and not drawn.
  Both functions return markup made only of fixed class names, numbers and escaped text (`&lt;script&gt;` in a label).

**Bugs found while checking in the browser.** A strip label for a phase at the end of a run ran off the right edge (now
anchored from the bracket's right end); a figure label of 20 or more characters was cut too early (limit 24).

**Tests.** `python3 -B test/shiploop-run-review.test.py`: 65 tests (48 before; 17 new, all 17 fail on the base tip
`e79f948a` from a `git archive` with only the test file copied over; 38 pass there, all of them existing tests). New:
`validate_doc` accepts the new fields and rejects bad kind, effort, status, change.target and change without a reason;
the figure is a structured spec (unknown kind, 7 items, empty, negative, infinite, boolean, non-string label, unknown
tone, unknown fields, a raw markup field); the contract documents every field; `cardsFor` (every option once, a shared
option under its first finding in view with a reference elsewhere, done apart, rank, flagged open findings, filters and
their counts, the expectation filter); the strip over the committed Luna run (exactly 39 `rect`s, the phase's outlined
cells, 2 letters for one revise and one blocked, the label anchors); hatching and escaping of a stage named
`<script>`; `STAGE_FLOW` equal to `export.PHASES`; the figure's element counts (2 rects and 4 texts for expected 0 and
saw 13), `>=` with one open chevron, the escaping of a `<script>` label, 6 of 8 items, a zero stub; and page probes of the
card (picture, text, advice, options, the ask-for-options tick), Tick recommended, the filters per run, and the
selection pruning. Deliberate change to an existing test: the logic block's purity check now ignores string literals
(a stage is called "document", a data word, not a global read).

**Size.** `template/index.html` is 75,869 bytes (57,754 after R4). R6 and R7 add step 2 and the prompt builder and
remove what they replace; the final size is recorded with R7.

## 2026-10-04: R6, step 2 rows with chips derived from the findings (template, contract, defaults and tests; not republished)

Status: firm for the code and its tests. No Artifact or ArtifactData call; the live page and database are untouched.

**The defect this removes.** An expectation's status was a hand-set global (`holds`, `bent`, `broken`, `unjudged`) that
disagreed with the findings tagged to it: P5 read holds with 5 open defects and B1 bent with 6 open. Nothing is
stored now. `chipFor(criterion, run, findings, review)` (pure, in the logic block) derives it for the chosen run: the
worst `effect` among the run's open findings for the criterion (`broken`, then `bent`); with none open, `holds` only when
the run's review gives a one-line `basis` for it; otherwise `not examined`. Fixed, accepted and re-expected findings do
not count, and a finding's `runs` list limits it to those runs (`run: any` applies to all). A chip therefore cannot
disagree with its findings, and a criterion nobody looked at does not read holds.

**One state beyond the plan: `not rated`.** An open finding with no `effect` (every finding in today's database, until R9
authors them) makes the chip `unrated`, not `holds`. The plan's four chips would have shown P5 as holds again, or as
not examined, which is wrong in the other direction (it was examined; it has findings). `not rated` says exactly that
and is the visible mark of a review that has not been written yet. The step 2 summary counts it
(`This run: 3 bent, 6 not rated, 2 hold.`). Owner decision: keep it, or fold it into `bent`.

**Step 2.** One card per criterion, grouped Principles and Backchain (the group text from the expectations
documents): the chip, the S-clause chips (`clauses`), the expectation text with its revision history (`revised 1x`, the
inline disclosure; a revision now names the `option` that asked for it), the review's basis line when it has one, and
`N open findings`, which opens step 3 filtered to that expectation (a `Expectation P1: clear` chip removes the filter).
The stepper count reads `1 broken, 1 not rated`. The review's `summary` (the arc, 3 to 6 lines) heads step 1 when the
run has a review. The old per-expectation "Saw" list and status editor are gone; so are the `.pill` styles (chips
replace them in the phase panel and the verdict chips).

**Contract.** `expectations` lose `status` and the `iter` kind (the validator rejects `kind: iter`), gain `clauses`, and
`revs` items gain `option` (replacing `iter`). New collection `reviews/<runKey>`: `summary` (list of strings), `basis`
(map criterion key to a one-line reason), `reviewedAt`; the page reads it and never writes it (subscription `reviews`,
documented in `SCHEMA.md`). `defaults/expectations.json`: the 11 criteria drop `status` and gain `clauses` from the
plan's proposed map (P1 S-1 S-2; P2 S-5 S-10; P3 S-2 S-4 S-6 S-7; P4 S-2; P5 S-9 S-11; P6 none; B1 S-10; B2 S-1 S-5 S-9;
B3 S-1 S-5; B4 S-5; B5 S-10; every clause exists in `test/shiploop_e2e/SPEC.md`). The map is still the plan's open
owner decision (confirm or amend). The Principles group text said "mark each as holds, bent or broken", which describes
the removed editor, so it now says the chip is worked out from findings and the review.

**Not done here (for a later step).** The live `phase-2` expectation text has one revision that exists only in the
database; copying it into `defaults/expectations.json` before the first publish is an operation (R9 and the publish
procedure), not part of this increment, and the defaults still carry the original `phase-2` wording. The live
expectation documents also still carry the old `status` field and the `iter-*` documents; the page ignores both.

**Tests.** `python3 -B test/shiploop-run-review.test.py`: 75 tests (65 before; 10 new, all fail on the base tip
`e79f948a` from a `git archive` with only the test file copied; 38 existing tests pass there). New: `chipFor` (worst
effect wins, accepts a run key or a document; fixed, accepted and re-expected do not count; holds needs a basis and
no open finding, with five shapes of "no basis"; a `runs` list and `run: any`; five open defects with no effect read
`unrated`, never holds); the defaults name clauses that exist in SPEC.md, carry no status and have no `iter` kind; the
schema (no status, `option`, `reviews`, the contract text); step 2 rows through the page probe (derived chips that
ignore a stored `status: holds`, clauses, `revised 1x`, `by option a07`, the basis line, the jump to step 3 filtered to
P1, the stepper count and the arc); `not examined` with no findings; and the removed names. One existing test changed
deliberately: the defaults' allowed kinds no longer include `iter`; the stepper-count assertion follows the new step 2
text.

**Size.** `template/index.html` is 78,551 bytes (75,869 after R5).

## 2026-10-04: R7, one pure prompt builder, and the static render check of R4 to R7 (not published)

Status: firm for the code, its tests and the render check. The plan's last step is to republish the page once; that is
deliberately NOT done here (the owner reviews a draft first): no Artifact or ArtifactData call was made, nothing was
published, uploaded or released, and the live page and its database are untouched.

**The defect this removes.** The old prompt builder's `inc.rev` branch took every expectation that had revisions
and ignored the selection: for one ticked action (`a01`, "Run the Backchain comparison, pilot first") 7,060 of the
prompt's 7,862 characters were a "Revised expectations" dump of nine unrelated documents (eight iteration expectations
and `phase-2`). The toggles that governed it were removed in R4; R7 replaces the whole builder. The new prompt for the
same `a01`, built from the committed snapshot's saved documents (the nine revised expectations present), is **1,830
characters**: the head, the run facts, one option line with its instruction (226 characters), the rules (about 640) and
the report-back. It contains no revision text and names no other option or expectation.

**`buildPrompt(state)`**, pure, in the logic block (the page's own string building is gone; a test counts zero
`out.push(` in the page script). Structure, expectation changes first so later work is judged against the new wording:
the head (run name, release, host, model, date, status; the repo; the page URL; the run directory; the review file
`test/shiploop_e2e/evidence/<runKey>.review.json`), then "You ticked N options (kind counts). Plan them as one plan:
merge overlap, resolve conflicts, order by dependency, split into the smallest verifiable increments, mark what can run
in parallel", then the after line (default: `Present the plan and wait for my go-ahead.`; `Then execute it.` only when
chosen), then `Run facts:` with measured values only (visits, minutes elapsed, Improve passes, refusals, glue; a counter
the run does not carry reads `refusals not measured`, never a 0). Then the options grouped by kind: CHANGE AN
EXPECTATION (`id key title: target page|spec. Now: ... Was: <current text> Why: ...`, plus the note that a spec change
means amending `test/shiploop_e2e/SPEC.md` first in its own commit, and a page change means editing
`defaults/expectations.json` with a revs entry naming the option), FIX SHIPLOOP, FIX THE HARNESS (its own commit),
GATHER EVIDENCE (read-only unless told to run), ACCEPT AS KNOWN LIMIT (record in `LEARNINGS.md`, no code change), and
OTHER (no kind set). Each option line reads `n. id title [status, effort X]. Resolves: finding ids. Expectation: key
title (chip in this run); clauses S-n.`, then `Do: <instruction>` (an instruction already starting `Do:` is not
prefixed twice) and, only for an option with a cost, `Ask me before starting: costs <cost>.` Then INVESTIGATE (ticked
findings no option names: read the evidence, propose options of the five kinds, change no code), EVIDENCE (only findings
linked to ticked options or asked about, each once, with `evidence:`, the run key and that run's directory), the rules
from `config/prompt` `constraints`, the notes, and the closing from `closing`. Step 3 also shows the same prompt live
in a collapsed box (it updates as you tick), and step 4 lists the ticks by kind with untick controls and flags each
cost.

**Defaults rewritten.** `defaults/config.json` `constraints` (about 640 characters, specific to repairing a reviewed
run: small verified increments each ended by a script-run test, S-clause anchors, unmeasured is never zero, fix only
what breaks or misleads a normal run, no E2E run, release or push unless an option asks and release only through
`scripts/release.py`, ask-me-first options wait, follow the owner's memory rules and read the last three commits) and
`closing` (report back done, not done or blocked with the evidence, set each landed option to done in the review file
citing the commit, then run `/skill-craft:shiploop-run-review publish`); `concatPreamble` is gone, and the config schema
drops `concatPreamble` and `synthPreamble`. The live `config/prompt` document still has the old strings until a publish
overwrites it (R9).

**Static render check (R4 to R7 together; the plan's republish gate, minus the publish).** The Browser pane cannot
drive a `file://` page, so the template from the worktree was served from a scratch folder by `python3 -m http.server`
on 127.0.0.1 (port 8791, stopped afterwards) with a fake `window.claude.use("db")` in front of it: the real code path
(`claude.use("db")`, `collection().orderBy().onSnapshot()`, `doc().update/set`, `add`) over the committed db snapshot
plus a small synthetic overlay (effect, advice, options with kind, effort, recommended, cost and change, a figure on four
findings, and a review with an arc and three basis lines for the Luna run). The build script, overlay and screenshots
stay in the session scratchpad (`rrt/`), not committed; the overlay is invented sample text, not a review of the run.
Looked at, in my own tab: 375 px light (steps 1, 3, 4), 375 px dark (step 3), desktop light (steps 2, 3, 4) and desktop
dark (step 3). What I saw and fixed:

- At 375 px the page was 393 px wide: the step 4 cost chip (`ask me first: about 10 h of Luna time and its quota`)
  had `white-space: nowrap`. Chips may now wrap, and the ticked list prints the cost as a line of text. After the fix the
  document is 375 px wide and no element in any of the four steps extends past the viewport outside a scroller.
- The where strip on a phone showed the start of a 39-visit run while the finding's phase was off the right edge, and on
  desktop it sat in a narrow column and scrolled. The strip is now full card width, carries the position of its phase
  (`data-view`), and the page scrolls it there once the step is on screen (a hidden step has no layout to scroll; the
  first version missed that and the check caught it). A label near the end of a run hangs from the right end of its
  bracket.
- Figure text was about 9 px on a phone: 13.5 px now, labels limited to 22 characters (SCHEMA.md says so).
- Touch targets: the `Instruction and why` summaries were about 20 px high and the `Untick` buttons 26 px; both are
  now at least 40 to 44 px. The option checkboxes were already 44 px rows.
- Looked right and unchanged: the stepper (four pills wrapping their counts at 375 px), the sticky `N ticked, Your plan`
  bar, the option rows with chips, the dark tokens (strip colours, accent boxes, chips), the review arc, step 2 rows, and
  step 4 with its radios, notes and prompt box. One thing that reads oddly but is correct: the Luna header line says
  `13 refusals | 21 glue` because the database documents are still v1 (R13 re-exports them), and every expectation with an
  open finding reads `not rated` until R9 authors the effects. The status buttons wrap onto two lines at 375 px; left.

**Tests.** `python3 -B test/shiploop-run-review.test.py`: 91 tests (38 at the base tip; 53 new in R4 to R7, all 53 fail
on the base tip `e79f948a` from a `git archive` with only the test file copied over; the one existing test that
fails there, the config-keys check, was changed on purpose). The 16 new in R7: the size contract on the saved `a01`
(at most 3,000 characters plus the instruction, no revision text, no other option id or title, no unrelated
expectation); nothing ticked gives no prompt and wait is the default; the exact head line; run facts never print a 0 for
an absent counter; kind order and numbering; the option line with its resolves, chip, clauses and `Do:`; the cost line
only with a cost; a change-expectation option with target spec names `SPEC.md` first (and a page target names
`defaults/expectations.json` only); INVESTIGATE and one-per-finding evidence including another run's directory;
rules, notes and closing in order; the default rules and closing (length, content, schema); step 4 through the page
probe (counts, cost flag, untick, live box); the choice and notes per run; the hint with nothing ticked; and every step
working from documents with every optional field absent.

**Size.** `template/index.html` is 86,892 bytes (css 15,200, markup 7,151, pure logic 21,448, page script 42,837),
against 76,339 at the base tip: over the plan's 75 KB guide by about 11 KB. The growth is the testable logic block
(`cardsFor`, `chipFor`, `buildPrompt`, `whereStrip`, `figureSvg`, `improveFacts` and friends, 21 KB) plus the cards; R4
already removed about 19 KB of UML, iterations, editors and toggles, and I cut dead styles and the contract boxes. R14
replaces the old stage table in `renderRunDetail` (6.7 KB), which will give some of it back.

**Open for the owner.** Keep the extra `not rated` chip (R6) or fold it into `bent`; confirm the criterion to S-clause
map (R6); the publish step (not done) and the live-data operations of R9 (copy the live `phase-2` text into the defaults
first, merge clauses into the live criterion documents, overwrite `config/prompt`, normalise option statuses); and
`COLLECTION_ORDER` in `export.py` still lists `iterations` and not `reviews` (left alone so this branch merges with the
exporter work, which edits the lines beside it; `reviews` sorts last, which is harmless).

## 2026-10-04: R8, the skill procedure, the advice rubric and the review check (local, unpublished)

Status: firm for the code, its tests and the probe below. Local commits on branch `rr8-af090e` only: no push, no
release, no E2E run, and no Artifact or ArtifactData call (the live page and its database are untouched; the template
was not edited, R14 owns it).

**What changed.** `SKILL.md` has four modes (`advise RUN_DIR_OR_KEY`, `export RUN_DIR`, `publish`, `check FILE`) and
says plainly that scripts own the numbers and Claude owns the advice, with unmeasured never zero. `publish` takes the
artifact URL from the user (which may be a separate draft artifact with its own empty database), finds the page
titled "ShipLoop Run Review" only when none is given, never creates a second page unless asked, overwrites only the
replicas it wrote (pinned with `if_version`), never overwrites an owner-added document and never writes an existing
Backchain document (`luna1-plan` and `luna1-step-plan` hold hand verdicts). `references/advice.md` is the rubric:
inputs, six steps, the option form, the honesty rules, the `mismatch.md` triage mapping, and (owner request) when to
leave `effect` unset on purpose, how to write a `figure`, and a worked example with Luna's real numbers (13 refusals
against an expected 0, 3 of them a space typed into a long path). `export.py --check FILE` and `--docs FILE` share
`validate_doc` and the writer with the export; `COLLECTION_ORDER` lists every SCHEMA collection once (the removed
`iterations` is gone; `reviews` sits before `observations` and `actions`). `iterate.py` prints
`/skill-craft:shiploop-run-review advise <run dir>` instead of a file path (`review_line`).

**The check, as built.** Failures (exit 2, every one listed, one per line, naming the document): schema and enums
through `validate_doc`; every option's `findings` exist in the bundle; a `change-expectation` option has `change`
and no other kind has one; each `goal` ends with a `Done when` clause (the last labelled part, with a condition);
at most one `recommended` option per finding; a `clauses` id is `S-n` and one `defaults/expectations.json` uses.
Warnings (exit 0, listed): an open finding no option names; evidence with no path or commit token (an open finding
with no evidence at all reads the same, "none given"; a closed one with none does not warn); an open finding with no
`effect`. A missing status reads as open, as the page does.

**Probe on real data.** The R2 snapshot's findings and options, read as a bundle: 5 of 39 evidence strings have no
path or commit token (o05, o06, o12, o17, o39: the same five the plan counted by hand, so the loose token test matches
that count), 29 open findings with no option and no effect, all 16 option goals with no `Done when`, and three
statuses outside the normalised vocabulary (a13 `building`, a14 `analysed`, a16 `waiting`). R9 must therefore
rewrite all 16 instructions and map those three statuses, not only a12 to a15 as the plan scoped. A test pins this.

**Decisions and deviations.**
- The clause rule checks `clauses` lists in expectation documents of the bundle, the only structured carrier of a
  clause id once the per-finding `clauses` override was cut. It does not scan prose: the defaults use 9 of the 15
  SPEC clauses, so an option citing S-14 in its text is legitimate and must not fail. Open for the owner: also
  check that a finding's, option's or review's `criterion` key exists in `defaults/expectations.json` (a typo there
  silently reads "not examined"); the brief said no more rules, so it is not added.
- `--docs` runs the check first and refuses a failing bundle without writing anything (the brief only said it writes
  through `write_export`); this keeps `publish` from uploading an unchecked file. With no `--out` it writes to a new
  temporary directory (`export_defaults` uses a fixed one, which would leave stale files between bundles).
- The review file is named `<export name>.review.json` beside the run's export in `test/shiploop_e2e/evidence/`: the
  evidence files carry the default key in their name while the documents inside use the page's key (`luna1`).
- `SKILL.md` stays 119 lines (7,164 bytes) and `advice.md` 163 lines (10,342 bytes); no size bound is tested, per
  "raise the bound, never trim".

**Tests.** `python3 -B test/shiploop-run-review.test.py`: 148 tests (121 at the base tip `c2c4b63e`); 27 are new
(`ReviewBundleCheckTests` 19, `ReviewSkillTextTests` 8) and all 27 fail on the base tip (a `git archive` of
`c2c4b63e` into a temporary directory with only the test file and the fixture copied over; none of the 121 existing
tests fails there). The skill-text tests collapse whitespace; the worked example in `advice.md` is run through
`--check` and its numbers are compared with the committed Luna evidence (`refusals` 13, 3 broken paths). Also green
after the commits: `node test/skill-frontmatter.test.js` (20 skills), `test/test-groups.test.py` (16),
`test/marketplace-package.test.py` (29; the packaged copy of `export.py` passes `--check` on the sample),
`test/ci-policy.test.py` (10), `scripts/check-release-boundary.py --base origin/main`, and the whole
`test/shiploop-e2e.test.py` once (218 tests, 323 s; `iterate.py` changed, `ReviewAdviseLineTest` is new and fails on
the base tip).

**Commits.** `1a6c83ce` (--check, --docs, collection order, sample fixture, 18 tests), `f1b4e867` (iterate advise
line), `ee20c5a7` (SKILL.md, advice.md, change note, 8 tests; a prompt-text commit with the learning and evidence),
`366d6a8f` (the saved-data probe as a test).

## 2026-10-04: R14, the sequence picture and the six cards on step 1 (template and tests; not published)

Status: firm for the model, the picture, the cards, their tests and the render check. Local commits only: nothing was pushed or
released, no E2E run was launched, and no Artifact or ArtifactData call was made, so the live page and its database are
untouched (the plan's republish step is still open). Base: `c2c4b63e` (R1 to R7, R10 to R13, R15). Two commits: the pure model
with its tests (`2fa82da5`), then the renderer, the cards, the strip and the render fixes.

**Why.** The owner asked for "a very visual diagram of the number, duration, and meta context used during the sequences".
The exporter (R12, R13) already carries what the picture needs: a row per visit with `action`, `skipped`, `seeded`, `improve`
and, on a Codex run, `context`, plus the run's `calls`, `contextPeak`, `contextWindow`, `compactions` and the reasons for
what a host could not measure. R14 turns those rows into a picture that never draws an unmeasured value as a zero.

**`sequenceModel(run, opts)`** (pure, in the page's logic block, so node tests it with no DOM). One column per visit in history
order; consecutive `skipped` visits collapse into one "xN" column (the 54-visit hello run draws 49 columns: 47 work visits and
two collapsed runs of 4 and 3 skipped ones; Luna draws 39). A work visit is as tall as the square root of its minutes on the
run's own scale, the tallest column is the full 96 units and printed ("tallest: 196.4 min, plan, visit 6" for Luna), and no
column is under 2 (a work visit timed to under 0.05 min, hello's `skill-validate`, still gets 2 and the detail says "under 0.1
min", never "0 min"). A skipped column has a fixed height of 14, a seeded visit a fixed 20 and a visit with no accept time (`min`
null, not seeded) a fixed 26 drawn as an outlined "n/a": none of them is a minutes bar and none is zero high. Non-done outcomes
carry a text mark (R revise, P replan, B blocked, S seeded) so colour is never the only cue. `band` is the per-column context
strip: a bar of `peakPct` (0 to 100 of the window), a warning flag from 90%, and the compaction count per column; it is null
when no visit carries a `context` (every Claude run), and `bandNote` then reads "Per-visit context not measured on this host:
<run.unmeasured.visitContext>". A visit with no context in a run that has some gets no bar (height null), not a zero bar.

**The six cards** (`kpiCards`, each a number or "not measured" with the host's reason, never a zero): Visits ("54 (47 work, 7
skipped)", Luna "39 (39 work)"), Elapsed (accept to accept; Luna "19.3 h", hello "15.2 min"), Improve (Luna "41 passes, 360.3
min, 31% of elapsed"; hello 1.19.0 repeat "19 passes"), Backchain loops (as the existing ledger: loops, minutes as stages,
share of elapsed; "none" when the run has no loop, "not loaded" while the record loads), Context (main thread) (Luna "97.5%,
251,867 of 258,400 tokens; 34 compactions"; hello 1.19.0 repeat "27.1%, 271,220 of 1,000,000 tokens; compactions not
measured"; or "not measured" with the reason) and Refusals (Luna 13; the four Claude hello runs "not measured" with
`unmeasured.shiploop_failures`). `columnDetail` (what a tapped column says: stage, outcome, minutes and share, packet and
result file sizes, Improve, the visit's context and the findings whose `phase` is the column's phase) and `visitTable` (the
phone-readable and accessible form, one row per visit, context columns only when there is a band) are pure too.

**One change to an existing behaviour.** A percentage now reads to one decimal everywhere (`pctText`: "97.5%", "27%"), so the
card, the detail and the run facts agree; `contextText` said "(27%)" for 271,220 of 1,000,000 and says "(27.1%)" now, and
the two existing assertions that pinned the old text were changed on purpose. `kb` moved from the page script to the logic
block as `kbText`.

**Tests.** `python3 -B test/shiploop-run-review.test.py`: 134 tests OK (121 at the base tip). The 13 new tests of
`SequenceModelTests` run `sequenceModel` over the five committed v2 evidence files and a few fixtures: column counts (Luna 39,
hello 1.19.0 repeat 49 with the 4 and 3 collapsed runs), the square-root scale (every column within 0.11 of the formula, the
tallest equal to the plot height, 196.4 min visit 6 for Luna and 2.2 min visit 4 for the hello repeat), the 2 px minimum and no
NaN on a run of zeros or an empty run, the marks (Luna 16 R and 39 B, hello 27 P), the cards (the exact texts above), a
Context card that reads "not measured" with its reason, the band (Luna 39 bars, the peak bar 97.5, 34 compaction ticks, 21
warning flags equal to the visits at 90% or more; none for the four Claude runs, whose note carries `visitContext`), a visit
with no context getting no bar, a seeded and an n/a fixture row (fixed heights, S mark, never zero), the detail card and the
table. Run from a `git archive` of `c2c4b63e` outside the repository with only the test file copied over, all 13 fail
(the template has no `sequenceModel`), and the two changed assertions fail too.

**The picture** (`sequenceSvg(model, picked)`, pure, in the logic block; inline SVG, only fixed class names, numbers and escaped
text, every colour a class of the page's own tokens so dark mode follows). One column per visit on a 16 unit pitch (13 wide), so
Luna's 39 columns are 624 units and the 54-visit run's 49 are 784, inside an inner horizontal scroller in the card; the SVG is
at least as wide as the card up to 1.4 times its natural size, so a desktop card shows it whole. Top to bottom: the Improve
passes as a number above a column, the columns on a baseline (green done, amber revise or replan, red blocked; hatched skipped
with an "xN" label; cross-hatched seeded; outlined "n/a" for a visit with no time), the text marks R, P, B and S under the
baseline, the context band when there is one, its compaction ticks, and visit numbers every fifth column. The band is a bar per
column at its `peakPct` of the window (a faint dashed 100% line, labelled), amber with a "!" inside from 90%, a dashed tick (not
a bar) for a visit with no context, and a small triangle per compaction up to three, a number above three (Luna's visit 6 has 4
and visit 9 has 5). A transparent hit area spans each column's full height (16 wide, 176 high), and the detail card carries
Previous visit, Next visit and Close buttons of 44 px for a thumb that cannot hit a 16 px column. Tapping a column again closes it.

**The page, step 1.** The old stage table is gone, replaced (not kept): the six cards, then the picture, then the detail of the
tapped column, then a collapsed table of every visit (one row per visit, the phone-readable and accessible form), then the path
chevrons (each Observed chevron now says how many findings sit at its phase for this run, and how many are open) and the run
detail. In the run detail the stage table, its "hide stages under 1 minute" checkbox and the per-visit Improve card are removed
(the Improve card is a headline card now, and the passes sit in the picture and the table); the facts card, the planning
documents and the failures stay, and choosing a second run shows "The same six numbers, side by side" (the six cards of both
runs in one table) instead of the stage comparison. Findings at a phase now use the same rule everywhere (`appliesTo`, so a
finding with a `runs` list counts for those runs only): the chevron counts, the numbered dots and the phase panel agree.

**Static render check (required).** The template was served from a scratch folder by `python3 -m http.server` on 127.0.0.1 (port
8814, stopped afterwards) in front of a fake `window.claude.use("db")` (the build script of R7, copied and pointed at this
worktree) loaded with the committed db snapshot, the five committed v2 evidence files as run documents under the page's keys
(`luna1`, `hello-1161`, `hello-1180`, `hello-1190a`, `hello-1190b`, replacing the snapshot's older v1 run documents; the two
Luna Backchain documents are the snapshot's hand-built ones) and the R7 sample overlay (invented sample text, not a review of
the run). Scripts and screenshots stay in the session scratchpad (`rr14/`), not committed. Looked at, in my own tab: step 1 for
Luna and for the 54-visit hello run at 375 px light and dark and at 1100 px light and dark, plus a tapped column, the skipped
column's detail, the table and the comparison.

What I saw. Luna: six cards (39 visits; 19.3 h; 41 passes, 360.3 min, 31% of elapsed; 2 loops, 384 min as stages, 33%; context
97.5% of 258,400 tokens with 34 compactions; 13 refusals) over 39 columns. The tallest is `plan` (visit 6, 196.4 min, "3"
Improve passes above it) next to `test-strategy` (visit 5, "11" passes), `step-plan` (visit 9, 187.7 min) and the second
`test-spec` (visit 18, "8"); visit 16 is amber with an R, the last column is red with a B (blocked at system-test). The band
under it is mostly amber with "!" from the spec stage on (21 of 39 visits at 90% or more), with 34 triangles and the numbers 4
and 5. The 54-visit hello run: 49 columns, the tallest `spec` (visit 4, 2.2 min), an amber column with a P (visit 27,
replan), two hatched columns labelled x4 and x3 (visits 30 to 33 and 35 to 37), a 2 px sliver for `skill-validate` (visit 40,
timed to under 0.05 min), Improve numbers 1 to 3 above eleven columns, no band, and under the picture "Per-visit context not
measured on this host: the harness's stage rows carry no per-stage context ...". Its Context card reads 27.1% of 1,000,000
and its Refusals card "not measured" with the harness's reason in full.

What the check found and fixed (all in this commit): (1) a blank 16 unit header row above the columns wasted a tenth of the
chart on a phone (the caption moved to HTML); the row is 6 units now. (2) The band legend, one inline-flex span holding three
items, wrapped into three narrow columns of broken text; it is three spans in a `display: contents` wrapper now. (3) The detail
card laid its facts out one per line on a phone (a tall card with the labels above the values) and listed all 24 findings of
Luna's Plan phase as pills; the facts are a two-column list and the findings a collapsed disclosure that names their count
(open by default for four or fewer). (4) Table cells wrapped on a phone ("36.83 min" over three lines); cells do not wrap now
and the table scrolls inside its wrapper. (5) The Refusals card carried the harness's 150 character reason in a 160 px card, nine
lines tall, stretching its neighbour; an unmeasured card whose note is longer than 60 characters spans its whole row (the
reason stays printed in full). (6) The "scroll it sideways" hint was computed once, so it stayed after the window widened;
it follows a resize and the step being shown. Looked right: no horizontal page scroll at 375 px in any of the four steps for
both runs with a comparison chosen (document width 375, every element past the viewport inside a scroller); every label in
the picture is 11 px or more at natural size (11 px on a phone, about 15 px on a wide card); dark tokens (bars, hatch, band, "!"
marks, legend, cards); the "x4" and "x3" labels clear their neighbours' numbers; compaction triangles keep a gap of 2 px or
more between adjacent columns; the scroller has no vertical overflow (scroll height equals client height), so it cannot hold the page's vertical scroll. Seen and left: the
Context card sits next to an empty cell when the Refusals card spans the row; the selection outline spans the column's whole
height, so it crosses the visit's compaction number.

**Tests (part 2).** `python3 -B test/shiploop-run-review.test.py`: 145 tests OK (134 after part 1, 121 at the base tip). Eleven
are new: ten in `SequencePictureTests` (the SVG for Luna has 39 columns, 39 hit areas, 39 context bars, 21 warning bars, the
triangles of 1 to 3 compactions and the numbers 4 and 5, one 100% line, one selection outline when a column is picked; the
hello repeat's SVG has 49 columns, two hatched ones labelled x4 and x3, 11 Improve numbers, a P mark and none of the band's
elements; a fixture draws n/a, seeded and skipped columns with heights 26, 20 and 14 and a 2 px work visit, never a zero bar;
no colour literal in the SVG or in the `.sq`, `.sw` and `.kpi` rules and hostile stage names escaped; the page shows six cards,
the picture and a table and none of the removed stage table; a tap shows the detail with the findings at its stage and Previous
and Close work; the click handler selects, deselects and resets on another run; the table has a row per visit, Luna's cards and
the hello repeat's "Visits 54, 47 work, 7 skipped", its not-measured Refusals with the harness reason and its band note; the
comparison shows the same six numbers for both runs; the chevrons count findings per run) and one splits the old Improve
assertions out of the run-detail test (`kpis` now carries them). Three existing tests were changed on purpose: the context
text (one decimal, part 1), the file-size label (the page now says "packet and result are file sizes, not what the model
read") and the run-detail test (the stage table is gone). Run from a `git archive` of `c2c4b63e` outside the repository with
only the test file copied over, all 24 new tests of both parts fail (31 failures counting the subtests of one) and so do the
three changed tests; nothing else fails. The four gates pass: `node
test/skill-frontmatter.test.js`, `python3 -B test/test-groups.test.py` (16 tests), `python3 -B test/marketplace-package.test.py`
(29 tests) and `python3 -B scripts/check-release-boundary.py --base origin/main`. `test/shiploop-e2e.test.py` was not run: nothing
under `test/shiploop_e2e` changed.

**Size.** `template/index.html` is 110,496 bytes (css 18,711, markup and head about 8,840, pure logic 38,519, page script
44,425), against 86,892 at the base tip: 23.6 KB more. The old stage table and the Improve card gave back about 8 KB of page
script, but the model, its detail and table, and the SVG renderer add 17 KB to the logic block (that is the code the tests run)
and the picture's styles 3.5 KB. The 75 KB guide of R4 is long gone; nothing here is dead code, so I did not trim.

**Deviations from the plan, and open for the owner.** (1) A column's hit area is 16 units wide, the plan's minimum column, not
40 px: 39 to 54 columns cannot each be 40 px wide in one picture, so the touch path is Previous and Next buttons of 44 px in the
detail card (and the table). Say if you would rather have a 40 px pitch (Luna 1,560 px, the 54-visit run 2,000 px, scrolled).
(2) Seeded visits are not collapsed (only skipped ones are, as written); each is a column marked S. The harness seeds a block at
the start of a run, so a seeded run draws that many fixed-height columns; collapsing them like the skipped ones is a one-line
change. (3) The Context card shows one decimal ("97.5%", "27.1%") and so does `contextText` now (it said 97% and 27%); the
percentages in the picture's band come from the exporter's `peakPct`. (4) A visit with no context in a run that has some is a
dashed tick, not a bar; no real run has one yet (Luna has all 39). (5) Backchain loops is the existing ledger's number (loops,
minutes as stages, share of elapsed); the per-pass judgement stays in the loop cards below. (6) The picture's legend lists
seeded and n/a items even for a run with none, so the legend is the same for every run.

## 2026-10-05: R9, the Luna 1.16.1 review authored, and the page's one-time upgrade as code (local, unpublished)

Status: firm for the code, the review file and their tests. Local commits on branch `rr9-e0c0c4` only: no push,
no release, no E2E run, and no Artifact or ArtifactData call (the live page and its database are untouched; uploading
the review and running the upgrade are the next publish). The template was not edited (R14 owns it).

**The review** (`test/shiploop_e2e/evidence/codex-gpt-6-luna-1.16.1-battleship-20261003.review.json`, 69 documents,
`--check` exit 0 with 7 warnings). It keeps the page's 39 saved findings and 16 saved options (titles, expectations and
criteria unchanged; observed text only appended to, except o37, restated) and adds 4 findings and 9 options.

- Findings: 43, 30 open and 13 closed (7 fixed, 6 accepted). 27 open findings carry an effect (9 broken, 18 bent);
  28 findings carry advice; 8 carry a figure. Runs lists replace `any` and `sonnet` on the ten findings keyed so
  (o05 luna1 only; o34 the six Claude runs; o37 to o39 the hello runs; and so on).
- New findings: o40 (the harness records a generic tail line for 9 of 13 refusals: `FAILURE_LINE` in `metrics.py`
  matches "rejected" in "Read the current packet with next" and "error" in a model's AssertionError, while the cause
  is the `ShipLoop navigator:` line before it), o41 (accepted: the process record covers only the resumed session,
  33,452 s, the limit 05269ede documents; the plan asked for it as a finding), o42 (the page showed Improve as 135.8
  min; bind to receipt it is 360.3, 31% of 1,158.5), o43 (the 13 refusals by cause: 4 run-path copy errors, 3
  Improve contracts over budget, 5 results or an opening in the wrong shape, 1 blocked result refused under S-14).
- Options: 25. Kinds: fix-shiploop 10, fix-harness 7, gather-evidence 5, change-expectation 2, accept 1. Status:
  open 9, planned 4, built 7, done 5. 12 recommended, at most one per finding. Every instruction is
  `Do / Files and symbols / Test / Done when` with symbols, not line numbers; every fix option has a for, against and
  verdict line.
- New options: a17 (one-pass Backchain default, planned on `fastplan-1f1dd3`), a18 and a19 (change-expectation: B1
  reworded for one pass after the S-10 carve-out lands; a criterion P7 for S-14, the clause this run broke, which no
  criterion carries, so o35 sits on phase-6 with no step 2 row), a20 (plugin verdict kept on a resume, built,
  2528c470), a21 (record the refusal's cause line, open), a22 (accept: path typos stay a monitored limit, done, o33's
  decision), a23 (export the `backchain_passes` option and whether the final candidate was checked: item I4 the
  fast-planning plan handed to this work), a24 (compare Improve's planning passes on the next Luna run: the owner's
  D4 "revisit as its own option"), a25 (outcome shapes in the head and refusals that name the correction, built on
  `rrr-edc892`: d412a45d, f14f90c7).
- Left "no option yet" on purpose: o16 (B5; unknown whether the revise was visible at planning: not rated), o23 (a
  model difference, advice only), o30 (decided by I2c of the comparison plan, advice only), o34 (Claude runs, not this
  review's scope). o17 has an option and advice but no effect: whether to buy the comparison is the owner's choice
  (advice.md, "Effect"), not a miss of B1.
- reviews/luna1: a five-line arc and a basis for all 11 criteria. Derived chips for luna1: P4 holds; B5 not rated;
  P1, P2, B1, B4 bent; P3, P5, P6, B2, B3 broken.

**Statuses, verified from git and the run files, and where they differ from the plan's mapping.** The plan mapped
three: a13 building to built (c7ee64ba, released in 1.20.0, unexercised live), a14 analysed to done (no split: the
optional $28 hello A/B stays dropped, `docs/shiploop-e2e-plan-reconciliation-2026-10-04.md` section 7 and owner
decision 8), a16 waiting to planned (no recurrence in the four other hello runs, the 1.20.0 gate included). Beyond the
mapping: a01 open to planned (the comparison plan, superseded in part by the fast-planning plan); a03 and a06 open to
built (931c53e2, 6a997a02 and 112b239c are in 1.19.0, never seen in a looped run); a09 open to built (the redesign on
`rr8-af090e`, unreleased); a10 open to done (A2, 3c604304, verified: this run's regrade gives plan 11,782 s and
test-strategy 5,658 s, the accept deltas); a11 open to done (the run ended itself blocked and was journaled, 4b5d41dd);
a15 built to done (verified live: the 1.20.0 hello's init event lists 0 MCP servers and 28 tools). Two findings move to
fixed because this run's own regraded record shows the fix: o18 (stage minutes, 3c604304) and o31 (Improve children,
7eb7ee88). Owner: undo either flip if you read "fixed" as "verified in a new run".

**Where the evidence disagreed with a stored claim** (each old text kept, marked superseded 2026-10-05 here or in the
finding):
- o03 "the fix is committed locally, not released" and a06 "Release 1.16.2": superseded; 112b239c shipped in 1.19.0
  (19fa890d) and no 1.16.2 exists.
- o05's evidence "luna1 status: ShipLoop failures 9": superseded by the regraded 13. A fourth run-path error came after
  the o33 count's cutoff (events.jsonl line 7203, a run directory typed `.../20261003/20261003-bad`, repaired by the
  next call), so this run has 4 path errors, not 3; R1 and R2 still have not fired (no such line in any 2026-10-04 run).
- o07 "repeat review passes ... about 16% of the time": superseded; Improve is 360.3 of 1,158.5 min (31%).
- o36 "cause not traced": superseded; traced and fixed for new runs by 2528c470; this run cannot be regraded to pass.
- o37 "0 failures": superseded; Claude failures are not measured (o34). Its turns now stand beside model calls (84,
  94, 113 and 149 against 143, 167, 194 and 254; four runs, where the brief named three).
- The R8 sample and advice.md's worked example say 8 refusals "share one message whose cause is not shown": the message
  is the generic tail; every cause is on the line before it (o40, o43). The example stays valid as an example.
- The brief's "a11 ... that run was killed anyway": the 1.16.1 run was not killed; it ended its own turn blocked after
  9.29 h (cli stop end_turn). The run stopped after about 48 minutes was the 1.20.0 Luna run (`v1200-battleship-luna`).
- The fast-planning plan's "that loop is no longer offered whole at 1.20.0": `BACKCHAIN_NATIVE_CALLS` never allowed the
  step-plan whole loop (o27 says so for 1.16.1); what changed in 1.19.0 is that its text prints only at plan (a12).

**Figures chosen** (only numbers from the v2 exports and the run files; each is pinned by a test against them): o43
refusals by cause (expected 0, 13 refused, 5, 3, 4, 1); o40 recorded lines (13, 4 name the cause, 8 generic tails, 1
AssertionError); o42 Improve (page 135.8, bind to receipt 360.3, run elapsed 1,158.5 as the limit); o41 calls 2,565
against turns 2,189 (the one lower bound); o06 context peak as a share of the window (Luna 97.5, the largest Sonnet
hello 27.1; a Codex peak includes the call's output); o12 Backchain pass minutes (87, 16, 97, 10); o15 graph steps
(20 and 10 per criterion, in both graphs, counted in the two candidate-plan.json files); o37 hello model calls (84, 94,
113, 149).

**The one-time upgrade, as code.** `upgrade_docs(live)` in `export.py`, exposed as `--defaults --live FILE` (a file of
the page's rows, the snapshot's shape). It writes each expectation the defaults name as the defaults have it (so stored
`status` goes and clauses arrive), never writes `iter-*` or anything else, refuses when the page holds a revision the
defaults lack, notes each page text it replaces, writes config/prompt from the defaults and config/page only when the
page has none. The live phase-2 text and its revision (2026-10-04T15:50:07.905Z, from o03) are now in
`defaults/expectations.json`, verbatim, including its lower-case "there is no limit to this" (the owner's wording;
tidy it with a change-expectation if wanted). On the saved page the upgrade writes 21 expectations and config/prompt
with two notes: group-principles (its text is the pre-R6 seed about the removed status editor, with no revision) and
config/prompt (concatPreamble and the old constraints go; the snapshot keeps them). `--check` also fails a finding
`criterion` or a review `basis` key that is not a key of the defaults (the R8 open item; any key counts, since o35
uses phase-6).

**Found while reviewing the flow with real data, for the template (not edited here).** `buildPrompt`'s head names
`test/shiploop_e2e/evidence/<runKey>.review.json`, which for this run is `luna1.review.json`; the file is
`codex-gpt-6-luna-1.16.1-battleship-20261003.review.json` (R8 chose the export name). One of the two must change; the
prompt otherwise reads well (three ticked options: 7,483 characters, 2,617 of them the builder's own).

**Tests.** `python3 -B test/shiploop-run-review.test.py`: 161 tests (148 at the base tip `fd6810fe`); 13 new
(the criterion-key check 1, DefaultsUpgradeTests 5, LunaReviewTests 6, the SKILL.md text 1), all 13 fail on the base
tip from a `git archive` with only the test file copied over, and no existing test fails there. The prompt size
contract on real data: over three ticked options and over each of the 20 live options alone, the builder adds 1,862
to 2,617 characters to what the options and their findings say (at most 3,000), and no prompt names an unticked option.
Also green: `node test/skill-frontmatter.test.js` (20 skills), `test/test-groups.test.py` (16),
`test/marketplace-package.test.py` (29), `scripts/check-release-boundary.py --base origin/main`.

**Commits.** `f912bc60` (upgrade_docs, `--live`, the criterion-key check, the phase-2 copy, 6 tests), `384bea92` (the
review file, 6 tests), `77dd56b2` (SKILL.md publish and check wording, 1 test; a prompt-text commit with its learning),
and this entry.

**Open for the owner.** Tick or drop the two expectation changes (a18 after the S-10 carve-out lands; a19 adds P7 for
S-14). Confirm the o18 and o31 flips to fixed. The next Luna run (xhigh, one pass) is the shared verification of a03,
a06, a12, a13 and a17; a21 (refusal causes) and a25 (shapes) are cheapest to land before it, and a09 (publish) after
R14.

## 2026-10-04: the review file is named by the page's run key (integration)

Status: firm. R8 named a review file `<export name>.review.json` and R7's prompt head names `<runKey>.review.json`; the R9 report
flagged that the two disagreed (the page cannot know an evidence file's default name, only the run key). Decision: the page's key
wins. `test/shiploop_e2e/evidence/luna1.review.json` replaces `codex-gpt-6-luna-1.16.1-battleship-20261003.review.json`
(`git mv`, content unchanged), and SKILL.md and SCHEMA.md say `<runKey>.review.json`. The five export files keep their
default-key names; the run id inside each is the page key, so an export is found by its id and a review by its key.
Evidence: `python3 -B test/shiploop-run-review.test.py` 185 OK after the rename; `export.py --check` on the renamed file exits 0
with the same 7 warnings. Related: `eee16763` (R13 file names), `1a6c83ce` (R8), `c2c4b63e` (R7 prompt head).

## 2026-10-05: R16, the exporter reads the Backchain loops of ShipLoop 1.21.0 and records the passes option (local, unpublished)

Status: firm for the code, the tests and the real-data proof below; interim for what `candidateMatch` false means (one run).
Local commits on branch `rr16-a04384` only (base `origin/main` 1411d5f1, release 1.21.0): `df627852` (exporter, SCHEMA.md,
13 tests, change note `changes/shiploop-run-review/loops-under-run-backchain.md`), `cf1e349f` (the pass strip, 4 tests, note
`zero-streak-reads-neutral.md`) and this entry. No push, no release, no E2E run launched or resumed, no Artifact or ArtifactData
call, nothing written under `/Users/dadleet/e2e-runs`. The template changed, so the page needs one republish (not done).

**Why.** The E2E session reported two reader gaps on the Luna xhigh 1.21.0 battleship run: the export printed "Backchain loops:
none found under scratch/" because 1.21.0 keeps the loops under `run/backchain/<action>/`, and the first stage read 2.5 min in
the export against 3.4 in the harness's own line. The fast-planning plan's I4 had handed the exporter two record-only facts to
this work: the `backchain_passes` option, and whether the last `backchain-check` receipt is for the loop's final candidate.

**What 1.21.0 keeps (real shapes, read from the final run directory, copied first; field names only).**

| File under `run/backchain/<action>/` | Written by | Fields the exporter reads |
| --- | --- | --- |
| `until-loop-receipt.json` (and `until-loop-terminal-packet.json`, the same bytes in the plan loop) | the Until Loop runtime, kept by the host | `status`, `progress.action_number` (the passes), `progress.trivial_streak`, `progress.required_trivial_reviews`, `last_report.classification`, `last_report.exit_assessment`; the digests inside it are model prose (`last_report.evidence`, `handoff`) and are not read |
| `until-loop-start-contract.json` | the host (named by the host; the engine does not write these `until-loop-*` names) | its file time is the loop start; `required_trivial_reviews` repeats the receipt's |
| `check-<sha12>.json` and `candidate-<sha12>.json` | `shiploop backchain-check` (`shiploop_backchain_graph.py`) | `candidate_sha256` (equals the sha256 of the snapshot bytes), `ok`, `completion`; the snapshot has `steps` |
| `notes/<action>-backchain-review-record.json` (or `revise-output.json` inside the loop directory) | the host, in the shape Backchain's own contract gives (`references/convergence.md`, `caller-contract.md`) | `candidate.output_sha256` (the final candidate), `convergence.candidate.input_sha256` and `.output_sha256`, `candidate.cycle_start_sha256` (the host's addition, not read); `review.candidate.*` inside a `{plan, review}` wrapper |

The plan loop (`nav-5c67...`) has all three `until-loop-*` files; the step-plan loop (`nav-f675...`) has only the receipt
(plus `until-report.json`, `until-done-output.json` and its start contract at `notes/<action>-until-start-contract.json`): the
host chose the names, so the exporter finds a loop by its receipt and the start record from three places.

**Which layouts the exporter reads, and why.** Three, listed in SCHEMA.md ("Where a loop's numbers come from"): the two
`scratch/` layouts of runs before 1.21.0 (per-pass review records; the five committed v2 evidence files were exported from
them) and `run/backchain/<action>/`. "One supported version" governs what new runs write; it does not mean the exporter may
stop reading the data the committed evidence and the page's hand-built documents rest on, so the old reading is untouched
(all 185 existing tests pass unchanged). The five committed files are not re-exported here and keep their meaning; a re-export
of an old run would add `backchainPasses` "not recorded", `candidateMatch` "unknown" (no check receipts) and the receipt's
`trivialRequired`, nothing else.

**(a) Finding and building the loops.** `find_backchain_loops(run_dir)` returns each `backchain/*/until-loop-receipt.json`
directory (a directory with only check receipts is no loop; a loop still running has no receipt yet). The loop is named by
the stage of the action its directory is named for, with its accept window, so ids stay `<runKey>-plan` and `-step-plan`.
Passes come from `progress.action_number`; a one-pass loop is one `Pass 1` segment from the start record to the receipt
(file times), with `change` from the step diff of `convergence.candidate.input_sha256` to the final digest, `streak` from the
receipt and the last outcome in the note ("recorded it as non-trivial; its exit was assessed as satisfied"); more than one
pass with no per-pass record is one segment "Passes 1 to N" without `pass`; no start record means no segments and a `Timing`
fact saying why, never a 0. A loop whose layout cannot be read now says "unknown" passes (it said 0).

**(b) Record-only facts.** `backchainPasses`: the option as `state.md` wrote it; "not recorded" when the key is absent; an
unknown value verbatim (tests: one, converge, none, "maybe", 2, absent). `candidateMatch`: true, false or "unknown" (with the
reason in the `Candidate match` fact) from the newest `check-*.json` by file time against the final candidate digest: the
newest record the loop kept, in its directory or `notes/<action>-*.json`, whose `candidate` (or `convergence.candidate`)
carries a 64-hex `output_sha256`. `facts.md` gains "Backchain passes option (state.md)" as a run line (a run with option none
has no loop document to carry it) and "candidate match yes/no/unknown" on each loop. Nothing is refused or enforced.

**(c) The 0-of-0 streak.** The runtime receipt writes `required_trivial_reviews: 0` on a one-pass loop. The fact now reads "no
trivial-streak requirement on this loop" (a requirement of 2 still reads "1 of 2 required") and the document carries
`trivialRequired: 0`. The template printed facts generically (so the fact and the two new ones already reach the loop card with
no edit) but its pass strip hard-coded a streak axis to 2 and "the loop closes at 2": `streakTarget` and `streakNote` (logic
block, tested through `run_logic`) now keep a real 0, draw no streak axis, target or line for it and say the note under the
strip; a document with no `trivialRequired` is drawn as before.

**(d) Intake minutes: the exporter is right for a visit; documented, not changed.** On the Luna xhigh run `timeline.json`
`started` is 04:45:10Z, the first accept (intake) 04:47:37Z: 2.45 min (the export rounds to a tenth: 2.5). The harness's stage
window starts at `min(stamps)`, its first runner event (`metrics.stage_windows`, `since`), 04:44:11.139Z, and ends at the same
accept: 3.431 min ("3.4"). The 59 s between is the host starting (plugin and skill loading) before ShipLoop's `workspace
start`. The plan's DURATION rule is accept minus the previous accept, the first from `timeline.started`, so the export's number
is the visit's; the harness's includes pre-ShipLoop start-up. SCHEMA.md now says so (the limits paragraph). Open: whether the
harness line should say "from the host's first event"; not changed here (harness code).

**Real-data proof (read-only).** The run directory was copied twice into the session scratchpad (`rr16/livecopy`, taken while
the run was live; `rr16/livecopy2`, after the coordinator said the run is stopped and final), `cp -pR` of
`.shiploop-runs/<work>/run` so file times hold. The two copies' `backchain/` directories are byte-identical to each other and to
the final directory (`diff -rq`); `state.md` differed by two later accepted visits (21 then 23). A stub `metrics.json` (every
counter named unmeasured, "stub") was written into the copy only, because the run has no grade; the dry run is
`build_run(copy)`, so only the loop part and the first visit are real. Result on the final copy (23 accepted visits, 585.5 min):

| Loop | Passes, status | Requirement, option | Stage split (min) | `change` | Last check vs final candidate |
| --- | --- | --- | --- | --- | --- |
| plan (`nav-5c67...`) | 1, complete (non-trivial, exit satisfied) | `trivialRequired` 0, option one | 121: before 37, pass 22, after 62 | 6 steps changed | false: last check `25aecd520d40` (01:58, after the loop's receipt at 01:22 and the stage's accept), loop final `85f180cd6cd4` |
| step-plan (`nav-f675...`) | 1, complete (non-trivial, exit satisfied) | `trivialRequired` 0, option one | 120: before 27, pass 8, after 85 | 2 steps changed | false: last check `aa747e2fe573`, loop final `319381dcb76a` |

Both documents validate; the facts line reads "Backchain loops: plan 1 passes, complete, stage 121 min, candidate match no;
step-plan 1 passes, complete, stage 120 min, candidate match no". Intake reads 2.5 min.

**Finding (interim, one run).** In both loops the plan on disk was rewritten and rechecked after the loop closed (plan: eight
check receipts, the last 36 minutes after the loop's receipt, the candidate file rewritten at 01:58 and the stage accepted at
02:24; inferred: by the stage's parent action, before its accept; step-plan: the host's own accepted summary says "the earlier whole source-aware convergence remains bound to candidate 319381dcb76a ... so no
new whole-plan convergence is claimed"). So `candidateMatch` false means "the final plan is not the candidate the loop
converged on", not a failed check (the last receipts are ok). Whether that edit is wanted is the owner's question for the
fast-planning plan's one-pass exit ("the printed backchain-check is ok on the final candidate"); the fact records it and
enforces nothing.

**Tests.** `python3 -B test/shiploop-run-review.test.py`: 202 tests OK (185 at the base, 13 new in `BackchainLoopRecordsTest`:
a 1.21.0 fixture found and exported with passes, option and match true; mismatch false; newest by file time not name; missing
receipt and missing digest unknown with the reason; the option as written and absent; a 0 requirement neutral and a real one
unchanged; several passes one span; no start record no segments; check-only directory no loop; two loops ordered; the scratch
fixtures still export as before with the new facts unknown; an unreadable loop reports unknown passes; the schema and
SCHEMA.md; the intake limit text; and 4 in `LoopStreakTests`). All 17 new tests fail on the base 1411d5f1 (`git archive` into
the scratchpad, my test file copied over; 17 distinct failures, no existing test among them). Also green:
`node test/skill-frontmatter.test.js` (20 skills), `test/test-groups.test.py` (16), `test/marketplace-package.test.py` (29),
`scripts/check-release-boundary.py --base origin/main`. Commit 1 was verified without the template edit (198 tests), then the
template commit (202).

**Limits, documented not guarded.** "Last" check receipt and every loop minute are file times: right on the original
directory, a copy needs `cp -p` (already true of Improve minutes). The file names the host gives its records (`notes/<action>-
backchain-review-record.json`, `revise-output.json`, the start contract) are the host's: the exporter reads them by the field
names Backchain's contract defines, so a host that names or places them elsewhere gives "unknown", not a guess. A receipt's
mtime is the loop end; the terminal-packet copy is saved later (83 s in the plan loop). The page database's hand-built
documents (`luna1-plan`, `luna1-step-plan`) are untouched and have none of the new fields; the page treats a missing
`trivialRequired` as 2.

**Owner decisions.** (1) Republish the template (the pass strip) when the next publish happens. (2) Whether the harness's
first-stage line should start at ShipLoop's start (as the export does) or say "from the host's first event". (3) Whether a plan
edited after its loop (`candidateMatch` false in both real loops) should be a finding on the Luna 1.21.0 review.

## 2026-10-05: R16 follow-up, the prompt head names the review bundles and publish supplies the page URL (local, unpublished)

Status: firm for the code, the tests and the reproduction below. Local commit `47efcfdf` on `rr16-a04384` (base `f62bd428`);
no push, release, run, Artifact or ArtifactData call. The template and `defaults/config.json` changed, so the page needs one
republish and its `config/prompt` and `config/page` rows one write (neither done).

**What the owner's prompt showed.** A prompt built on the draft page with run `hello-1190b` primary, option `a16` and finding
`o39` ticked had two defects.

1. *A review file that does not exist.* The head said `Review file: test/shiploop_e2e/evidence/hello-1190b.review.json`. The
   builder named the file from the primary run key (R7), and the integration rename `38119014` ("a review file is named by
   the page's run key") made the same assumption. A finding is authored in one run's review bundle and may span runs (its
   `runs` list); `luna1.review.json` is the only bundle that holds `a16` and `o39` (checked by `grep` over the committed
   bundles), and `o39` applies to `hello-1190b` only. The page cannot know which bundle holds an id.
   **Fix.** The head now reads: `Review files: the *.review.json bundles in test/shiploop_e2e/evidence/ (find each ticked id
   below in the bundle that has it, for example grep -l '"a16"' test/shiploop_e2e/evidence/*.review.json; edit it there).`
   The example is the first ticked option (or, when only findings are ticked, the first finding); an id that is not plain text
   (`[\w.-]+`) is replaced by `<id>`, so no id is put into a shell line. `defaults/config.json` `closing` says "set its status
   to done in the review file that holds it, citing the commit". The earlier "named by the page's run key" decision stands for
   *writing* a review (SKILL.md advise: `<runKey>.review.json` is where a run's review is authored); only the prompt stops
   assuming it can name the file for a given id.
2. *No `Page:` part.* The head prints `config/page.artifactUrl`, which the template already reads (`promptState`,
   `cfgOf("page").artifactUrl`); the field is named `artifactUrl`, not `url`, and the live page's stored document uses that
   name, so it is kept. Cause: publish step 2 writes `config/page` from `defaults/config.json` only when the page has none, and
   the defaults carry `artifactUrl: ""`. A draft page (a separate artifact with its own empty database) therefore stores an
   empty URL, and the builder prints nothing for an empty one. The live page's row was set by hand (the snapshot holds
   `https://claude.ai/artifact/BFc6JGjLhENVJ9shRAA2iA`). A page cannot read its own claude.ai URL from inside the artifact
   sandbox (its own origin is not the artifact link), so the URL can only come from publish, which has it from the Artifact
   result. **Fix.** `export.py --defaults [--live FILE] --page-url URL` sets `config/page.artifactUrl`: it keeps the page's own
   title and any other field, writes nothing when the page already holds that URL, notes a different non-empty URL it replaces,
   and exits 2 for a value that is not an http(s) URL; without the flag `config/page` is written only when absent, as before.
   SKILL.md publish step 2 passes it (one sentence); SCHEMA.md documents `artifactUrl` (optional string) and that an empty or
   absent URL prints nothing. **The Page URL can be supplied**, by publish, not by the page. A draft page needs its own URL
   passed, not the live page's.

**Confirmed and left.** `Run evidence:` is the primary run's directory (`run.evidence`). Each `EVIDENCE` line carries the
finding's own run: the primary run when the finding applies to it (`appliesTo`: its `runs` list or `run`), otherwise the first
run in the list it applies to, printed as `run: <key> at <directory>`. A finding spanning runs therefore prints once, with the
primary run's key and directory when the primary is among them (a test pins this, and a finding of another run only).

**Reproduction with real data.** The owner's case rebuilt from the committed `luna1.review.json` and the committed
`hello-1190b` run export, `a16` ticked, an empty page URL (the draft's state): the head is `Repair work from the Run Review of
Sonnet 5.5 hello, release 1.19.0 (repeat) (skill-craft 1.19.0, ShipLoop 0.51.0; claude claude-sonnet-5-5; 2026-10-04; done). In
the skill-craft repository. Run evidence: /Users/dadleet/e2e-runs/20261004/v1190-hello-sonnet-2. Review files: the
*.review.json bundles in test/shiploop_e2e/evidence/ (find each ticked id below in the bundle that has it, for example grep -l
'"a16"' test/shiploop_e2e/evidence/*.review.json; edit it there).` followed by one `- o39 [P1, open]` evidence line. No `Page:`
part, as pasted, until publish writes the URL.

**Size contract (unchanged bound).** The builder's own text for three ticked options (a19, a13, a21 of the Luna review) was
2,627 characters before and is 2,794 now; over the 20 live options alone it was 1,872 to 2,403 and is 2,039 to 2,570. The head
grew by 167 characters; the bound of 3,000 (and `3000 + len(goal)` for a01) did not move.

**Tests.** `python3 -B test/shiploop-run-review.test.py`: 212 tests OK (202 before). New: in `PromptBuilderTests` the head
names no per-run review file for three run keys and an investigate-only prompt and an unplain id, the report-back line, a finding
spanning runs prints once with the primary run's key and directory (and one of another run prints that run's), and the page
prints `config/page.artifactUrl` and nothing when it is empty or absent; `PageUrlTests` (6: an empty page, a draft page with an
empty URL keeping its fields, a replaced URL with its note and an unchanged one writing nothing, a live page with no
`config/page`, the CLI refusals and the writes, and the SCHEMA.md and SKILL.md text). Changed with the text they pin: the head
test (renamed), the SKILL.md command assertion. On the base `1411d5f1` and on the previous commit `f62bd428` (the test file
copied into a `git archive`), 8 of the 10 new tests fail; the other two (a finding spanning runs, the page URL read) pin behaviour
that already held ("confirm and leave") and pass there by design. Also green: `node test/skill-frontmatter.test.js`,
`test/test-groups.test.py`, `test/marketplace-package.test.py`, `scripts/check-release-boundary.py --base origin/main`.

**For the owner.** (1) Republish the page and write `config/prompt` (the closing) and, on the draft, `config/page` with its URL
(`--page-url`); until then a prompt from the page still names the old file. (2) The live page's `config/page` already holds
its URL; pass the same one to keep it (`--live` with an equal URL writes nothing). (3) Findings span runs but a review bundle is
named by one run key (`luna1.review.json` holds the hello findings): the prompt no longer depends on that, but `advise` still
writes `<runKey>.review.json`; whether a finding of another run should live in that run's own bundle is a convention to settle.

## 2026-10-05: R17, the plan, the steps loop and each visit's packet on step 1 (local, unpublished)

Status: firm for the definitions, the numbers and the tests below. Local commits `d897fe06` (exporter, contract, evidence) and
`721c8212` (template) on `rr17-a0486a`, base `d1cca62f` (skill-craft 1.21.2, shiploop-run-review 0.1.1, released); no push, no
`scripts/release.py`, no E2E run, no Artifact or ArtifactData call, nothing written under `/Users/dadleet/e2e-runs` (every export
went to the session scratchpad with `--out`). The template changed, so the page needs one republish and the page database needs
the `packets` upload (neither done). Related: `f1545b10` (R16, the loops under `run/backchain/`), `38119014`.

**The owner's request.** "I would like the run review draft to be able to also show me the packets and the number of times it
went through the steps loop (because, technically, we should have multiple steps in our planning process that were produced that
we're supposed to go execute on)." Two things were missing from the page: the packet text of each visit, and the plan: how many
work items and steps planning produced, and how many of those steps an implement visit executed.

**Definitions** (SCHEMA.md "Plan and execution" holds them; every number is counted from `state.md` history and the accepted
results, never from summary text).

- `stepPlans`: the item's accepted `step-plan` visits of any outcome (a plan that came back `repeat` counts).
- `loops`: how many times the item went through the **steps loop**: ShipLoop plans the item's steps, then builds them one
  implement visit per step. The first pass counts 1 (once the item has any visit, else 0) and each accepted `revise` starts one
  more, so `loops` is `1 + revises` while `stepPlans` also counts a repeated plan. Why this and not `stepPlans`: the engine sends
  an item back to `step-plan` only on a `revise` (`REVISE_TO`, at most `MAX_REVISES` 2), and a pass is what the owner means by "went
  through the loop"; a `repeat` re-issues the same stage and is not a new pass.
- The pairing of steps with visits is the engine's own rule (`implement_progress`, `_step_lines` in `shiploop_navigator.py`): on
  the inline route ShipLoop issues one implement packet per step, in order, and only a `done` visit moves to the next, so the k-th
  done implement visit after an item's **latest accepted step plan** executed step k; a `repeat` visit is another attempt at that
  step, and a `revise` visit ends the pass. A stage row gets `workitem`, `loop` and, for an implement visit, the `step` its packet
  named (the plan then in force), so `S3` of loop 1 and `S3` of loop 2 are told apart.
- Where the rule does not hold the export says so instead of guessing: `workItems` is absent with a reason when `state.md` has no
  queue or history rows carry no `workitem`, or when the plan visit was recorded by the E2E seed; an item has no `stepsExecuted`
  and its steps no `action` when the run's `delegation` is not `inline` (ask-agent issues one implement packet for the whole
  plan) or when the counts do not line up with one packet per step (more done visits than steps, or the item moved past implement
  with fewer); the run's `stepsPlanned` and `stepsExecuted` are then absent with a reason under their own name. A planned step no
  visit executed has `action: null` (written, not omitted).

**Real data, read only** (each run exported through this exporter into the scratchpad; `Steps` is planned/executed; the
pairing was tested against every run by a loader test: each executed step names an accepted implement visit of its own item with
the same step id, and the counted `revises` equal `state.md`'s own `revisions` map, `{W1: 1}` for Luna and `{}` for the hello
runs). The real records agreed with the engine pairing in all five runs: no row needed a different rule.

| Run (key) | Work items | Step plans | Loops | Steps | Implement visits by outcome | Packets | Packet text | Largest | Cut |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Luna 1.16.1 (`luna1`) | 1 (W1) | 2 | 2 | 5/5 | done 7, revise 1 | 39 | 1,830,890 B | 65,126 B | 0 |
| hello 1.16.1 (`hello-1161`) | 1 | 1 | 1 | 2/2 | done 2 | 35 | 1,276,373 B | 59,205 B | 0 |
| hello 1.18.0 (`hello-1180`) | 1 | 1 | 1 | 1/1 | done 1 | 34 | 1,246,204 B | 59,112 B | 0 |
| hello 1.19.0 gate (`hello-1190a`) | 1 | 1 | 1 | 1/1 | done 1 | 34 | 1,249,392 B | 55,961 B | 0 |
| hello 1.19.0 repeat (`hello-1190b`) | 2 (W2 added by replan) | 2 | 1 + 1 | 2/2 | done 2 | 47 | 1,738,609 B | 56,177 B | 0 |

Luna's first pass planned five steps and built S1 and S2 before the revise at S3 (visit 15); the second plan has the same five
step ids and an implement visit executed each (visits 22 to 26). The packets are one document per visit that has a packet file
(Luna has 40 files and 39 accepted visits, the fortieth is the next action's), 189 documents and 7,487,848 bytes on disk for the
five runs, none near the 150,000-byte cut. In `hello-1190b` W2 is the corrective item the system-test replan added; the seven
engine-skipped visits have no packet file and no document. At upload the packets go in `ArtifactData` batches of at most 50
documents and 1 MiB: two batches a run, ten in all.

**What the page shows.** Step 1 gains a "Plan and execution" panel below the six cards (still six): per work item its title, a
badge ("steps loop once", "steps loop x2"), a counts line, one cell per planned step (filled with its visit number when executed,
dashed "not run" when no visit executed it, dotted "?" when unpaired) and the step tasks in a collapsed list; the headline "1 work
item, 2 passes through the steps loop" and the line "Steps planned 5, executed 5"; a run with no `workItems` reads "Not measured:"
with its reason. Tapping an item shades its visits in the picture, tapping a step selects the visit that ran it or says it was never
executed. A tapped visit's detail names its work item, loop and step, and a closed "Packet" box does one `get` of
`packets/<runKey>--<action>` when opened, with a scroll box, Copy, size, digest and truncation note. The page never subscribes to
`packets`. Seen in a browser tab (a local server over the template with a mock database that served the exported documents):
Luna's panel, W1 selected and 30 columns shaded, S1 tapped to "Visit 22: implement" with "W1, steps-loop pass 2" and "S1", the Packet
read once as `packets/luna1--nav-b7f4...` (47.3 KB, `dd1d01c90aa4`), seven collections subscribed and none of them `packets`;
a hello run edited to have a never-run step and an unpaired item drew the dashed and dotted cells and the message on tapping, and
fits 375 px in the dark scheme with no sideways scroll.

**Limits, documented not guarded.** A run that switched its delegation route mid-run is read by its final route (`state.md`
keeps only the current one). An item a `carry-forward` revision removed before it started is not listed (the export reads the final
queue). A step task and a work item title are cut at 200 characters with a flag; a packet over 150,000 bytes is cut at a line
boundary and one whose escaped JSON would pass the page database's 256 KiB per-document limit is cut further (a test with 150,000
bytes of quotes and newlines); the validator refuses an oversize document. The page keeps a loaded packet for the page's life, so
a re-uploaded packet shows after a reload. The artifact database's total size cap is not known here (a `quota_exceeded` would
name it): 7.5 MB for the five runs is the largest write the page has had.

**Tests.** `python3 -B test/shiploop-run-review.test.py`: 255 tests OK (212 at the base, 43 new: `PlanAndExecutionTest` 13,
`PacketDocumentTest` 9, four in `CommittedEvidenceTest`, `PlanPanelTests` 10 and `PacketBoxTests` 7). The fixture's `state.md` and results now follow the engine's shape (a `workitem`
on each history row, a `delegation`, a step plan with steps), and two existing assertions changed with what they pin (the row's
`packetDoc`, and `writes.json` now ending with the packets). Run from a `git archive` of `d1cca62f` outside the repository with
only the new test file copied over, all 43 new tests fail and the only other two failures are those two changed assertions. Also
green: `node test/skill-frontmatter.test.js` (22 skills), `test/test-groups.test.py` (21), `test/marketplace-package.test.py` (29),
`scripts/check-release-boundary.py --base origin/main` (both change notes accepted), `export.py --check` on `luna1.review.json` (69
documents, 0 failures) and on the committed evidence files. The long `test/shiploop-e2e.test.py` was not run: nothing under
`test/shiploop_e2e` changed except the five evidence files.

**Evidence files.** The five committed run exports were re-exported with the page keys (`--key --name --order` as R13 recorded) and
the same file names: 49,276 bytes in all became 60,562 (Luna 14,660 to 18,277, hello 1.16.1 8,031 to 9,766, 1.18.0 7,911 to 9,495,
1.19.0 gate 7,926 to 9,467, repeat 10,748 to 13,557), each under the exporter's 200,000-byte limit. Every run document differs from
before only by the new fields; the two Luna Backchain documents also gained the R16 record-only fields (`backchainPasses`,
`candidateMatch`, `trivialRequired`, two facts) that the earlier file predates. The packets are not in these files.

**Left for the owner.** (1) A seeded run has `workItems` absent (as asked): its work item is the harness's, though its step-plan
visits are the model's, so the steps loop of a seeded run is not shown; showing it with the item marked seeded is a small change.
(2) The ask-agent route has no per-step pairing by construction (one implement packet for the whole plan); the panel then shows
the planned steps as "?" and `executed not measured`. (3) Republish the template, then upload each run: its `runs` document with
`if_version`, the Luna Backchain documents never over the hand-built `luna1-plan` and `luna1-step-plan`, and the packets in ten
batches; whether to upload the packets of all five runs or only the run under review (7.5 MB). (4) The page cannot refresh a
loaded packet without a reload.

## 2026-10-06: R18, the planning_review option in the export, the page and the baseline rows, and the general review bundle (local, unpublished)

Status: firm for the definitions, the real state.md lines, the printed readings and the tests below; interim for the old-row rule on
rows nobody has written yet (one case below). Local commits on `rr17-a0486a` (base `origin/main` 45f163d0, skill-craft 1.22.0, then
the three R17 commits `c439244f`, `442bd572`, `cd631edb`): `b2e879a6` (exporter, page, SCHEMA.md, SKILL.md, 15 tests, two state
fixtures, change note `changes/shiploop-run-review/planning-review-option.md`), `defaeb12` (the baseline row and comparison, 10
tests, harness only), `4b09f959` (`general.review.json` and 5 tests) and this entry. No push, no `scripts/release.py`, no E2E run
launched or resumed, no Artifact or ArtifactData call, nothing written under `/Users/dadleet/e2e-runs`; the canonical checkout was
not touched. The template changed, so the page needs one republish (not done); a re-export of any run now carries
`planningReview` (`not recorded` for a run before 1.22.0).

**Why.** The E2E session landed the run option `planning_review` (`--planning-review stage|none`, state key `planning_review`) in
1.22.0 (45f163d0; engine commits `7317f458`, `f6ed230f`, `17cded5a`) and handed this leaf the readers (D7 of
`docs/shiploop-planning-review-plan-2026-10-05.md`; the "Handoffs to the Run Review session" bullets of the Planning review entry
of `test/shiploop_e2e/LEARNINGS.md`): record the mode in the export, the page and the baseline rows so a cell is never compared
across modes silently; do not let a none run's zero Improve passes read like a run with missing evidence; and fix the phase-1
expectation, whose text ("The script accepts each only after its Improve review") is untrue under `none`. Item a24 of
`luna1.review.json` ("compare Improve's planning-stage passes on the next Luna run") is, per the plan, answered by its M1 to M4
runs; it stays open here, and R18 makes those runs' Improve numbers readable.

**Real format (no model, no network).** `shiploop init --run-dir RUN --repo REPO --prompt P --planning-review stage|none` of the
plugin's own CLI at this tree, in a scratch git repository, then the harness's `SEED_SCRIPT` pattern (the pure navigator, a
synthetic `done` result per stage, a synthetic Improve receipt wherever a child is parked) stopped at `step-plan`. The two lines
the exporter reads, from the two `state.md` files:

| Mode | The key | The Improve card (resolved at `init`) | Children parked while walking intake to select-work |
| --- | --- | --- | --- |
| `stage` | `  "planning_review": "stage",` | `  "improve_skill": "",` | 3: spec, test-strategy, plan (`improve_results` holds 3 records) |
| `none` | `  "planning_review": "none",` | `  "improve_skill": "<path>/skills/improve/SKILL.md",` | 0 (`improve_results` is `{}`) |

Everything else in the two records is the same key set (sorted keys, `backchain_passes`, `delegation`, `lint`, a `history` of
8 rows with `workitem`). They are committed as `test/fixtures/run-review/state-stage.md` (5,299 bytes) and `state-none.md`
(4,392 bytes) with the two scratch paths normalised to `/work/repo` and `/plugin/skills/improve/SKILL.md` and nothing else
changed; the test fixtures take the option's value from them.

**(a) The export.** `export.py` reads the key with one helper (`_recorded_option(state, key)`, replacing `_backchain_option`, so
both options are read the same way): the value as written, any other value shown as it is (a number as its JSON), and
`not recorded` when the key is absent, never a default. A run document gains `planningReview`; `facts.md` gains
"Planning review option (state.md): none"; SCHEMA.md and the exporter's `SCHEMA` table type it (optional string).

**(b) Improve under none.** The Improve totals are what the `improve/` directories hold, so a none run that has not yet reached its
last item's `carry-forward` reads `improvePasses` 0 and `improveMin` 0 as measured, which for a stage run means missing evidence.
They are kept (they are measured); a run whose recorded mode is `none` also gets `improveScope`
"planning stages skipped by design (planning_review none)", and no other run does (`stage`, an unknown value and `not recorded`
claim nothing). A planning-stage row of a none run never has an `improve` map; the rows at `carry-forward` and
`system-test-author` do.

| Reading of a none fixture (2 children at carry-forward and system-test-author) | What it prints |
| --- | --- |
| run document | `planningReview` "none", `improveScope` as above, `improvePasses` 3, `improveMin` 9.5, `imp` "2 children, 3 review passes" |
| facts.md | "- Improve: 2 children, 3 review passes; most passes in one child: 2; 9.5 min bind to receipt; planning stages skipped by design (planning_review none)" and "- Planning review option (state.md): none" |
| header line (`headerFacts`) | "skill-craft 1.16.1, ShipLoop 0.48.1 \| running, 3.3 h at snapshot \| 1 refusals \| 2 glue \| 2 children, 3 review passes \| planning review: none" |
| chip beside it (`modeChip`) | "no Improve at planning stages" (title: the mode and "not comparable with a stage run's") |
| Improve card (`kpiCards`) | "3 passes", note "9.5 min; no Improve at planning stages (planning_review none)", no share of elapsed |
| detail of the spec visit (`columnDetail`) | "Improve: not run by design (planning_review none)"; the carry-forward visit reads "2 passes, 6.5 min" |

A stage fixture reads "9 passes", "36.5 min, 18% of elapsed" and no chip; a fixture with no key reads the same and its header
prints nothing about the mode (a hand-built document with `planningReview` missing, empty or `not recorded` prints as before).
The page's list of the five planning stages (`PLANNING_REVIEW_STAGES`) is kept equal to the engine's `PLANNING_CHOICE_STAGES` by a
test, and the engine's registered modes are asserted to be exactly `stage` and `none`, so a mode the engine adds fails a test
instead of reading silently. The detail line is said only for a work visit (a skipped or seeded visit says nothing, and a visit
that does have a child shows the measured line, never contradicted).

*Decisions.* (1) Under none the card prints no share of elapsed, not even a non-zero one: the minutes stay, the percentage beside
a stage run's would invite the comparison the chip says not to make. (2) The chip is only for `none`; a `stage` run shows the
mode in the header line, and an unknown value shows there verbatim and nothing more. (3) The visit table's "Improve" column is
unchanged: blank for a planning visit of a none run (the detail card says why).

**Seen in a browser tab** (a local `python3 -m http.server` on 127.0.0.1 over the template with a mock database serving exports of
the fixtures; no Artifact call): the none run's header with the amber chip, its Improve card, the spec visit's detail line, and the
stage and no-record runs with no chip and the old card; at 375 px the header wraps and the chip takes its own line.

**(c) Baseline rows.** `metrics.planning_review(state)` reads the key from the state `metrics.engine_state` already returns, as
written, `not recorded` when absent. `run.main` reads the state once (the termination record used the same read) and
`baseline_row(..., planning_review)` stores it, `not recorded` when a caller passes none. The comparison:

- `row_planning_review(row)`: the recorded value as written; for a row with no field, `stage` only when its `plugin_version` is
  below `PLANNING_REVIEW_FIRST_RELEASE` (1.22.0, named once, compared as numbers: 1.9.0 is before it), because the option did not
  exist and every planning stage of that run started an Improve child, which is what `stage` does; otherwise `not recorded` (no
  or malformed `plugin_version`, or 1.22.0 or later with no field). A null counts as absent.
- (Superseded 2026-10-06, see the last entry: the row is now the last of the run's own mode.) `planning_review_line(mode, before)`: None when this run and the previous row name the same recorded mode; otherwise "baseline
  not compared across planning_review modes (<this> vs <previous>); the earlier row is <date>, ShipLoop <v>" (plus "; it records no
  mode, read as stage because plugin 1.21.0 predates the option" when the rule supplied the mode) and nothing below it is compared,
  not turns, cost, sessions, glue nor a stage. Two `not recorded` modes are not known to match and are not compared. A comparison
  that does run names the mode in its header and says so on its own line when the previous row's mode came from the rule.

Printed by the fake-host harness: stage then stage "baseline  vs ... same grok/grok-4.7/medium, planning_review stage): turns 4 -> 4,
..."; stage then none "... modes (none vs stage); the earlier row is <date>, ShipLoop <v>"; a 1.21.0 row with no field then none "...
(none vs stage); ...; it records no mode, read as stage because plugin 1.21.0 predates the option", then stage, which compares and
prints "the earlier row records no mode, read as stage because plugin 1.21.0 predates the option"; a row with no `plugin_version`
then stage "(stage vs not recorded) ... no plugin_version places it before the option". The committed `baselines.jsonl` has 16
rows and only the last (claude, claude-sonnet-5-5, plugin 1.20.0) names a host, so the rule changes what that one row compares as
and nothing else today. README.md (Suites and baselines) says all of it.

**(d) The general bundle and the expectation option.** `test/shiploop_e2e/evidence/general.review.json` (no `reviews` document;
run `any`; no `phase`) holds finding **o44** (criterion `phase-1`, kind `decision`, status `open`, effect `bent`) and option **a26**
(`change-expectation`, effort S, recommended, open, `change` target `page`). a26's `to` is the original phase-1 text followed by the
SPEC S-10 carve-out of 2026-10-05 in its own words (seven phrases of it appear verbatim in both, which a test checks against the
SPEC), and the goal follows `references/advice.md` (Do, Files and symbols, Test, Done when). `defaults/expectations.json` is not
edited: an expectation change is the owner's tick and the aggregate prompt's edit. `export.py --check` on the bundle: "check: ok
(2 documents, 0 failures, 0 warnings)", exit 0. The ids follow o43 and a25 of `luna1.review.json` and appear in no other committed
bundle. The page files o44 under its General filter with a26 under it, and ticking a26 gives a prompt that names
`test/shiploop_e2e/evidence/` with a `grep -l '"a26"'` for it. SCHEMA.md says in one sentence that a bundle named for a run holds
that run's reviews and `general.review.json` the findings that belong to no single run; SKILL.md says in one sentence that a
finding spanning runs or belonging to none goes there. (The R16 follow-up's open point (3), whether a finding of another run
should live in its own run's bundle, is settled for findings that span runs or belong to none; `luna1.review.json` keeps what it
already holds.)

**Tests.** `python3 -B test/shiploop-run-review.test.py`: 275 tests OK (255 at the base `cd631edb`; new: `PlanningReviewExportTest` 7,
`PlanningReviewPageTests` 8, `GeneralReviewBundleTests` 5). `python3 -B test/shiploop-e2e.test.py`: 241 tests OK (231 before;
new: `PlanningReviewRowTest` 5, `PlanningReviewBaselineThroughMainTest` 5; the fake hosts' state.md now records
`FAKE_PLANNING_REVIEW`, default `stage`, `absent` leaves the key out). Fail-first, each against a `git archive` of the tip before
its commit with only its test files and fixtures copied in: 13 of the 15 exporter and page tests fail (the 2 that pass are labelled
guards: a stage run, an unknown value and a run with no record keep their numbers and their card), all 10 harness tests fail, and
the bundle class errors because the bundle is absent. Mutation checks on copies (28 deliberate defects, all caught): share printed
under none, by-design claimed for any recorded mode, `not recorded` printed in the header, a chip for every recorded mode, a stage
dropped from the page's list, a skipped visit told by design, the scope for every non-stage value, a default for an absent key, the
scope missing from facts.md; unrecorded modes equal, the first release read as before the option, every field-less row read as
stage, a loose version parse, the mode check not gating, the row defaulting to stage, a default for an absent key, the rule applied
silently; and eleven on the bundle. Also green: `node test/skill-frontmatter.test.js` (22 skills), `test/test-groups.test.py` (21),
`test/marketplace-package.test.py` (29), `scripts/check-release-boundary.py --base origin/main`.

**Limits, documented not guarded.**
- (Superseded 2026-10-06, see the last entry: the owner approved choosing the last row of the same mode.) The previous row is still the last row of the same case, source, host, model and effort. When it has the other mode nothing is
  compared, even if an earlier row of this run's mode exists: after none runs, a stage control would not be compared with the
  1.21.0 stage rows. Choosing the last row of the same mode is a change of `scan_baseline` of about ten lines; it is not made
  because the handoff says "compares nothing when the modes differ" and the safe reading is the literal one.
- A row written by a `--source checkout` run of a tree that already carries the option but whose plugin version is still below
  1.22.0 (the planning-review commits landed before the release bump) has no field and would read as `stage` even if it ran
  none. `baselines.jsonl` holds no such row (its latest plugin version is 1.20.0); every row written after `defaeb12` records the
  mode itself. Rows the E2E session wrote locally in that window are not visible here.
- A stage run, or one whose key is absent, that has no `improve/` directory at all still reads 0 passes and 0 minutes as
  measured (unchanged, as the handoff's own text says). Marking it unmeasured needs a rule for when a planning stage was accepted
  without a child in a run that should have one.
- The five committed run exports are not re-exported: none has `planningReview`, the page treats the absence as before, and a
  re-export would add `not recorded` to each.
- The prompt's "Run facts" line and the "Compare with" table do not name the mode (a none run's Improve cell carries the scope
  note; the run facts line reads "3 Improve passes" as it does for any run).
- Not in R18, still open from the same handoff: a case that runs `--planning-review none` must also pass `--improve-skill` in the
  `init` or `workspace start` its prompt names (`run.py` and the case catalog; the E2E session's), and the stop-point design.

**Owner decisions.** (1) Republish the template; then upload each new run's document and `export.py --docs
test/shiploop_e2e/evidence/general.review.json` for o44 and a26. (2) Tick a26 (or not): it amends phase-1 on the page only. (3)
Whether the baseline comparison should take the last row of the same mode (the limit above; decided yes on 2026-10-06, built in `25d1d93d`). (4) Whether the prompt's run facts and
the comparison table should carry the mode.

## 2026-10-06: R18 follow-up, a run is compared with the last row of its own planning_review mode (local, unpublished)

Status: firm. Decision 2 of the R18 entry (take the last row of the same mode) was approved by the coordinator on the owner's
"continue", and is built in one harness-only commit, `25d1d93d` (test/shiploop_e2e/run.py, README.md, test/shiploop-e2e.test.py; no
change note). `scan_baseline(..., planning_review)` now finds the last row of the same driver that stands for the run's mode, past rows of
the other mode (the old-row rule is unchanged: a row with no field is `stage` only when its plugin_version is below 1.22.0); with no such
row the report prints "baseline  not compared across planning_review modes (<this> vs <previous>); no earlier row of mode <this>; the
last row for this driver is <date>, ShipLoop <v>" and compares nothing, and a comparison names its row by date and ShipLoop version as
before. Effect on the sequence the plan measures: [1.21.0 stage row, none, none] then a stage control compares with the 1.21.0 row, and a
none run after [stage, none] compares with the none row. 247 tests in test/shiploop-e2e.test.py (241 before); 11 of the 16 tests of the two
baseline classes fail on the tip before it, and 11 deliberate defects are caught. The proof trees for harness tests must be real git
repositories (the harness runs git on its own checkout): the R18 commit `9eba8f41` was re-proved that way (all 10 of its tests fail on its
parent, all 8 of its defects are caught), so its recorded claims stand. The branch was rebased onto `origin/main` 3b246328 with no
conflicts; the R18 commits of the entry above are now `c757cedf` (exporter, page), `9eba8f41` (baseline rows), `cb0baf6e` (bundle) and
`219c1de6` (that entry), and the R17 commits `f31095ce`, `09f27638` and `a88a3cf7` (they were `b2e879a6`, `defaeb12`, `4b09f959`, `4a7fe0e8`
and `c439244f`, `442bd572`, `cd631edb`). Also resolved there: the limit "a stage control would not be compared with the 1.21.0 stage rows".

## 2026-10-06: a26 applied, the Specify expectation states what the engine does under each planning_review mode (defaults, tests and note)

Status: firm for the text, its revision, the tests and the upgrade dry run below; the page itself is not updated. Base `origin/main`
219c1de6 (R17 and R18 landed). Commit `d48a0630` (defaults, tests, change note `changes/shiploop-run-review/phase-1-planning-review-modes.md`)
and the commit that carries this entry and the two statuses; both go to main in one push. No `scripts/release.py`, no E2E run, no
Artifact or ArtifactData call.

**Why.** The owner ticked option a26 on the page (the advice of finding o44, R18): amend phase-1 with the wording of the SPEC's S-10
carve-out of 2026-10-05 and keep the original sentence. Under `--planning-review none` (skill-craft 1.22.0) the engine starts no
Improve child after spec, test-strategy, plan, step-plan or test-spec, so "The script accepts each only after its Improve review" is
untrue for the spec and the test strategy there, and a none run would read as a defect of Specify. Under `stage`, the code default
until a later dated SPEC commit says otherwise, the sentence holds, so the added text describes the exception and the original
sentence stays the rule.

**What changed.** `phase-1` in `skills/shiploop-run-review/defaults/expectations.json` takes a26's `change.to` verbatim (180 to 945
characters: the original sentence, then the carve-out's words) and one `revs` entry `{at 2026-10-06T14:45:21Z, from, obs o44, option
a26, reason, to}`, the revision form SCHEMA.md requires, so the page's upgrade never overwrites the owner's wording. The text and the
reason are read from `general.review.json`, not retyped. In `general.review.json` a26 is `done` (its `ref` adds `d48a0630`) and o44
is `fixed`. Tests (`test/shiploop-run-review.test.py`): the exact upgrade-notes list in `DefaultsUpgradeTests` gains the phase-1
note (it comes first, in defaults order); `GeneralReviewBundleTests` now requires the defaults' phase-1 text to equal a26's `to` and
pins the two statuses and the commit in `ref`, and the two page-view tests there (the general filter's card and the prompt for a ticked
option) now build their state from the rows as they were while open, because the page by design lists a `done` option under done and
prints a finding's own status; three new tests pin the revision (`from` is the original sentence, `obs` o44, `option` a26, `reason`
a26's), the saved page's upgrade, and the applied state (a26 under done, no option card).

**Evidence.** Fail-first: before the edit two of the new tests errored and two existing ones failed (the exact upgrade-notes list and the SPEC-phrase test); after it
`python3 -B test/shiploop-run-review.test.py` passes 278 tests (275 at the base plus the three new). `export.py --defaults --live
test/shiploop_e2e/evidence/run-review-db-snapshot-2026-10-04.json` (phase-1 with the original text and no revs) prints a note for
phase-1 and none of a refusal, and writes phase-1 with the revision. The quick tier selected by the commit's files passed (18 suites,
exit 0). `scripts/release.py --dry-run` accepts the four pending `shiploop-run-review` notes (R17 two, R18 one, this one): 0.1.1 to
0.1.2 and skill-craft 1.22.0 to 1.22.1.

**Limits, documented not guarded.** (a) The page is not updated: its database changes only through publish (SKILL.md). The live
page was last read at the 2026-10-04 snapshot; if the owner edited phase-1 there since, the upgrade refuses with an `ExportError`
naming the document and the page's text and revs must be copied into the defaults first. (b) The draft page's o44 and a26 rows still
read `open` there until the Run Review session refreshes them. (c) The amendment reaches installs only through a release.

**Owner decisions.** (1) When to cut the release that carries the four notes. (2) Whether to apply the defaults upgrade to the live
page after the template republish (re-read its expectations first).


## 2026-10-07: R20a, the stage card: a derived catalog, the exit-check rule, the packet checklist, and the card and list on step 1 (local, unpublished)

Status: firm for the definitions, the survey counts, the sizes and the tests below; interim for what a reader of the card should
conclude from the two packet findings (they are the E2E session's to act on). Local commits `d4b848dc` (exporter, contract,
catalog, fixtures, change note `changes/shiploop-run-review/stage-catalog-and-card-fields.md`) and `9b5e8af6` (template, tests,
SCHEMA.md card section, change note `stage-card-and-list.md`) and this entry, on branch `rr20-ccaebb` in
`.claude/worktrees/rr20-ccaebb`, base `origin/main` ee6712a5 (skill-craft 1.22.0 with the S-6 tenet; shiploop-run-review 0.1.1).
No push, no `scripts/release.py`, no E2E run launched or resumed, no Artifact or ArtifactData call, nothing written under
`/Users/dadleet/e2e-runs` (every export went to the session scratchpad with `--out`), the canonical checkout untouched. The
template changed, so the page needs one republish, and the page database needs `config/stages` (`export.py --defaults --live`) and
each run's re-export (`runs` documents with the new row fields; the packets) before a card shows more than sizes. (The two commits
were first made with a reserved `recordAudit` hook for an observed read-back; the E2E session then dropped its record audit, so
the hook was removed before anything was pushed and the commits rebuilt without it.) Related:
`219c1de6` (R18, the `planning_review` option the rule reads), `81e0502f` (the Specify amendment that names the modes),
`d48a0630`, `ee6712a5` (the tenet, SPEC S-6).

**The owner's request** (B11 of `docs/shiploop-batch-1007-plan-2026-10-07.md`, relayed by the E2E session): for each stage visit
show (a) what the stage was, its purpose in one line and the kind of exit check; (b) the packet sent; (c) the output written back:
summary, result file and size, which later stage or script reads it, time, refusals and revise count; plus a read-back state per
record (the page can show only the declared readers: the engine records no observed reads). The aim is to step through a run and see SENT, DONE, WRITTEN for every stage at a glance, and, by the main tenet (SPEC S-6:
context is cleared between any two stages, each packet restates how its stage operates and how it is checked), to see whether each
packet carried what its stage needed. Four refinements arrived mid-task and are built: one alias table only, resolved once; the
checklist named with the E2E session's packet-completeness vocabulary (purpose, operates, checked, produces, recovery) plus where;
no observed read-back and no hook for one; and a derived display name for a stage plus a `Checked by:` rule for the `checked` item.

**What was built.**
- **The catalog** `defaults/stages.json`, written by `export.py --stages` from the sibling skill's `shiploop_stage_spec.py` (loaded
  in place, no copy), never by hand; `config/stages` in the database is its replica, written by `--defaults`. Command, not an import at
  export time: the exporter and the page never depend on the engine's version at run time, so an export of an old run directory
  still renders, and a test (`StageCatalogTests`) fails when the committed file differs from what the table yields. The catalog is
  the table below.
- **The exit-check rule** (`exit_check`, `effective_exit_check`; SCHEMA.md "Stage catalog"): `script-run` when `complete_runs` is
  non-empty, else `review loop` when `improve` is set, else `model judgement`; under a recorded `planning_review none` the five
  `planningChoice` stages are `model judgement`. Pinned over every engine stage and compared with the engine's own
  `reviewed_stages` for both registered modes. No row has both a script run and an Improve rule, and a test says so, so the stated
  precedence is not an untested guess. `carry-forward` is `review loop` for its `last-item` rule (the card says an earlier item's
  advances directly).
- **One alias table**, `STAGE_ALIASES` (`select-work`, `get-next-work-item`), mirrored once in the page and kept equal by a test;
  resolved only where the phase table and the catalog are looked up, in both directions (a table that lists the new name gives the
  old one the same phase; a catalog naming either is found under either). The engine rename is not on main; the catalog is derived
  from whatever the table says at the base (`select-work`), and regenerating after the rename changes one name and the drift test
  goes green. The phase-table test now compares through the alias, so it holds before and after.
- **Row fields** (all optional, small): `summary` and `summaryTruncated`, `resultFile` (true or false), `carried`, `packetImprove`.
  The `carried` table is `CARRIED` in `export.py`: per label, any of its rules (a rule is a set of groups of alternative patterns).
  `checked` has two rules: the Done-when list with the Improve line, or alone a line starting `Checked by:`, which the E2E batch's
  producer packets will print (no packet on disk has it, nothing depends on it; tests cover both rules and a mid-line mention).
- **The page**: the tap-a-column detail is the stage card (three labelled blocks, Previous and Next unchanged), plus a "Stage cards"
  list under the picture (one row per column, so a tap selects the same visit), with a packet head (the first 12 non-empty lines
  of the packet document, loaded on demand by the same single `get` and cache as the Packet box). A stage is named by one derived
  rule (`stageLabel`: hyphens to spaces, first letter upper-cased, `get-next-work-item` reads "Get next work item"; the raw name is
  the tooltip and, when it differs, secondary text). The readers are the stage table's declared readers, worded "declared readers
  N" or "no declared reader" in the list and "Read by (declared by the stage spec)" on the card, never "read by 0".

**The engine rename, as a one-table change.** In the Run Review half the old name is written, outside tests, fixtures and history, in
exactly these places (all counted at `9b5e8af6`): `scripts/export.py` (the `PHASES` entry, `STAGE_ALIASES`, two comments),
`template/index.html` (the `STAGE_FLOW` entry, its `STAGE_ALIASES`, one comment), `SCHEMA.md` (two sentences of prose), and
`defaults/stages.json` (one entry, generated). The rename does not need any of them but the last: with the alias table both names
resolve to one phase and one catalog entry, so the whole finished branch (341 tests) passes after the engine row is renamed once
`export.py --stages` has rewritten `defaults/stages.json`; before that exactly the four tests that compare with the committed
catalog fail (checked on a scratch copy with only `shiploop_stage_spec.py` renamed). Optional tidy in the later commit: make the new
name the first member of both alias groups and rename the `PHASES` and `STAGE_FLOW` entries together (the phase-table test compares
through `stage_names(...)[0]`, so the entry and the group's first member must move in the same commit). Elsewhere the old name
appears as history: 43 mentions in `test/shiploop-run-review.test.py` (24 at the base; 19 in the new tests, which deliberately use both
names), one each in `test/fixtures/run-review/state-none.md` and `state-stage.md`, seven committed evidence files and the page
snapshot, `luna1.review.json`, and this journal. None of those needs to change: the alias resolves them.

**The catalog** (generated; `Readers` is the inverse of the engine's `reads`, `this item` marks `item:` reads; "none" means no
stage declares reading it, scripts still read some of these results).

| Stage | Purpose (the row's goal) | Exit check | Declared readers |
| --- | --- | --- | --- |
| `intake` | confirm the request, boundaries and open questions | model judgement | discovery, research, spec, plan, product-acceptance, handoff |
| `discovery` | inspect the current repository, environment and baseline tests | model judgement | research, spec, plan |
| `research` | resolve the unknowns that matter with evidence | model judgement | spec, test-strategy, plan |
| `spec` | define required behavior and acceptance criteria | review loop (always; model judgement under none) | test-strategy, plan, select-work, step-plan, test-spec, implement, test-refine, document, verify, integration-verify, carry-forward, system-test-author, system-test, product-acceptance, release-plan, release-verify, handoff |
| `test-strategy` | map requirements to the checks that will prove them | review loop (always; model judgement under none) | plan, prepare, step-plan, test-spec, baseline, test-author, regression, verify, system-test-author |
| `plan` | build the dependency plan and the work-item queue | review loop (always; model judgement under none) | prepare, select-work, step-plan, test-spec, implement, document, skill-assess, integrate, carry-forward, system-test-author, release-plan, handoff |
| `prepare` | ready the development and test environment | model judgement | step-plan |
| `select-work` | confirm this work item is still the right next item | model judgement | none |
| `step-plan` | plan this item's concrete changes and checks | review loop (always; model judgement under none) | test-spec, baseline, test-author, implement, document, skill-assess, static-checks, verify, integrate (this item) |
| `test-spec` | specify the tests this item needs before code changes | review loop (always; model judgement under none) | baseline, test-author, test-red, implement, test-green, test-refine, verify (this item) |
| `baseline` | record the relevant checks before any change | model judgement | regression (this item) |
| `test-author` | write the tests the item's test spec calls for | script-run (test-probe) | test-red (this item) |
| `test-red` | run the new tests and confirm they fail for the right reason | script-run (test-red) | none |
| `implement` | make the planned change | script-run (lint-gate) | test-green, test-refine, document, static-checks, verify (this item) |
| `test-green` | run the focused tests and confirm they pass | script-run (lint-gate, test-loop) | verify (this item) |
| `test-refine` | tighten the tests against the actual implementation | script-run (test-rerun) | none |
| `regression` | rerun the retained suites for regressions | script-run (lint-gate, test-loop) | verify (this item) |
| `document` | update the documentation this change affects | model judgement | none |
| `skill-assess` | decide whether a reusable skill or helper change is warranted | model judgement | skill-validate (this item) |
| `skill-validate` | validate any skill or helper change against real inputs | model judgement | none |
| `static-checks` | run formatting, lint, type and build checks | script-run (quality-terminal, test-rerun) | verify (this item) |
| `verify` | verify the item against its acceptance criteria | script-run (test-rerun) | integrate (this item) |
| `integrate` | integrate the candidate into the working branch | model judgement | integration-verify (this item) |
| `integration-verify` | verify the integrated result and shared interfaces | script-run (test-rerun) | carry-forward (this item) |
| `carry-forward` | record lessons and revise the remaining queue | review loop (last-item) | none |
| `system-test-author` | prepare end-to-end and system tests | review loop (always) | system-test |
| `system-test` | run end-to-end and system tests on the real candidate | script-run (test-rerun) | product-acceptance, release-plan |
| `product-acceptance` | assess the product against the original outcome | model judgement | handoff |
| `release-plan` | plan the release, rollback and checks | review loop (always) | release-check, release, release-verify, operations |
| `release-check` | confirm release readiness without releasing | model judgement | release |
| `release` | perform the planned release | model judgement | release-verify |
| `release-verify` | verify the release where consumers use it | script-run (test-rerun) | operations, handoff |
| `operations` | confirm monitoring, recovery and support readiness | model judgement | handoff |
| `handoff` | write the final handoff with status and evidence | model judgement | none |

Classes: 11 `script-run`, 8 `review loop`, 15 `model judgement`. Seven stages have no declared reader (`select-work`, `test-red`,
`test-refine`, `document`, `skill-validate`, `carry-forward`, `handoff`): the card says "no stage declares reading it", which is the
stage table's statement, not an observation (the engine records no observed reads).

**The packet survey** (question: which lines does a packet carry, in every engine era I can read, and do they differ?). Cases:
every packet set under `/Users/dadleet/e2e-runs/*/*/.shiploop-runs/*/run/packets` (read only), 15 run directories, 493 files, ShipLoop
1.16.1, 1.18.0, 1.19.0, 1.20.0, 1.21.0 and 1.22.0 (and a 1.22.0 development audit run). Method: `export.carried_markers` over each
file, `IMPROVE_PACKET` first; no model, no network. Result:

| Run directory | Files | Improve child's | Producer, all seven | Producer, all but inputs (intake) | Other shape |
| --- | --- | --- | --- | --- | --- |
| `20261003/battleship-luna` | 7 | 3 | 2 | 1 | 1 |
| `20261003/hello` | 36 | 8 | 26 | 1 | 1 |
| `20261003/seat-reservations` | 37 | 8 | 27 | 1 | 1 |
| `20261003/v1161-battleship-luna` (the Luna 1.16.1 run, `luna1`) | 40 | 9 | 29 | 1 | 1 |
| `20261003/v1161-hello` | 36 | 8 | 26 | 1 | 1 |
| `20261004/v1180-hello-sonnet` | 35 | 8 | 25 | 1 | 1 |
| `20261004/v1190-hello-sonnet-2` (`hello-1190b`) | 48 | 11 | 35 | 1 | 1 |
| `20261004/v1190-hello-sonnet` | 35 | 8 | 25 | 1 | 1 |
| `20261004/v1200-battleship-luna` | 4 | 0 | 3 | 1 | 0 |
| `20261004/v1200-hello-sonnet` | 36 | 8 | 26 | 1 | 1 |
| `20261005/v1210-battleship-grok-medium` | 12 | 5 | 6 | 1 | 0 |
| `20261005/v1210-battleship-luna-xhigh` | 24 | 7 | 16 | 1 | 0 |
| `20261006/gas-battleship-audit` | 43 | 8 | 34 | 1 | 0 |
| `20261006/v1220-battleship-grok-medium-none` | 53 | 3 | 48 | 1 | 1 |
| `20261006/v1220-battleship-sonnet` (`battleship-1220`) | 47 | 10 | 35 | 1 | 1 |
| total | 493 | 104 | 363 | 15 | 11 |

- *Firm.* Every packet of an accepted producer visit carried all seven labels in every era, `inputs` aside on `intake` (it reads
  nothing). The "other shape" file of a run is the packet of the action after the last accepted visit (the final `done` state or the
  state a blocked run stopped in), which belongs to no visit. The one wording that differs by era is the blocked_by sentence: `A
  blocked result adds blocked_by: ...` through ShipLoop 1.21.0, the `blocked: {"outcome": "blocked", "blocked_by": ...}` shape line
  from 1.22.0 (`e07e44d1`, 2026-10-04); the sentence that a problem the run can fix itself is repaired in the stage is in both.
  `Goal:` and `Done when (` exist in every era, so the "stage's step line" alternative for `purpose` is only the implement packet's
  `Step S1 (1 of 3)` line, which both eras that have implement packets print.
- *Firm, and the finding that matters.* A packet file is rewritten at every printing of its action, so a visit that started an
  Improve child keeps only the child's last packet: 104 of 493 files (21%), 10 of 46 visits of the 1.22.0 Sonnet run (spec,
  test-strategy, plan, step-plan twice, test-spec twice, system-test-author, release-plan, carry-forward) and 9 of 39 of the Luna 1.16.1
  run. They are the reviewed planning stages, which is where the tenet matters most, and no export can say whether their producer
  packet carried what the stage needed. The exporter marks such a file `packetImprove` (its first lines are "Current action: Improve
  the completed ..."), reads no label from it and says so on the card; it also labels the file's size as the Improve child's.
  Recommendation to the E2E session: keep one packet file per printing, or at least the producer's first printing.
- *Firm.* No packet on disk has a `Checked by:` line (the E2E batch branch will print one); the `checked` item is found by the old
  pair of markers in all 378 producer packets, and by the new line when a later engine prints it.
- *Firm.* Per-visit refusals are not recorded: `metrics.json` `shiploop_failures` entries carry `verb`, `exit` and `line`, no action
  id (Luna 13 entries, the 1.22.0 Grok none run 2, the 1.22.0 Sonnet run measures none and says so). The card prints "not recorded per
  visit" and the run-level figure labelled as such; nothing is attributed to a visit.

**What the page showed** (a local `python3 -m http.server` on 127.0.0.1 over a copy of the template with a viewport meta (the host
adds one to an artifact) and a fake `window.claude.use("db")` over the committed snapshot, the defaults and the real re-exports of
`luna1`, `hello-1190b` and the 1.22.0 run (key `battleship-1220`, order 15), packet documents served by `get` on demand; the tab and the
server are closed). At 375 px in the light and the dark scheme, `scrollWidth` 375: the Stage cards list reads each visit as a row
(number and name, outcome chip, exit-check chip, the purpose in muted text, then minutes, sent, written and read-by as separate
spans); the card of a `step-plan` visit (an Improve child's packet) shows the exit check "review loop", "Packet file kept (the Improve
child's) 52 KB" with the note and no checklist, "Revises of this item 1", "Improve 1 pass, 0.02 min"; the card of an `implement` visit
shows seven ticks, then after "Show the packet head" the first 12 lines (for an inline run most of them are the delegation preamble:
see the decision below), and with one label forced false in the page a red cross with the glyph; `intake`'s `inputs` shows a muted
dash (not applicable); the old hello 1.16.1 row of the snapshot shows its packet size, "not recorded in this export" and a result
file, with no zero. A second look after the display-name rule: "System test author" with its raw name `system-test-author` beside it in the list and in
the card title (the raw name stays in one piece on a narrow screen). The render changed four things: the minutes moved into the figures
line (they wrapped alone); the host's long refusal reason (repeated on every card) became "the reason is on the Refusals card";
"read by 0" became "no declared reader" (a bare zero would read as an observed count); and the raw name no longer breaks at a hyphen.

**Tests.** `python3 -B test/shiploop-run-review.test.py`: 341 OK (278 at the base; 300 after `d4b848dc`: `StageCatalogTests` 8,
`StageAliasTests` 2, `CardRowFieldsTests` 12; 341 after `9b5e8af6`: `StageCatalogPageTests` 5, `StageCardLogicTests` 15,
`StageLabelTests` 3, `StageCardListTests` 4, `StageCardPageTests` 9, `PacketHeadTests` 5). Fail-first, against a `git archive` of
ee6712a5 outside the repository with only the test file and the three fixtures copied in: 70 fail, 61 of the 63 new tests and
nine existing tests that pin what changed (the phase-table test, the defaults and upgrade tests, the usage message, one stage-row
equality, and three page assertions that now read the label); the two new tests that pass are labelled guards (the committed
evidence still validates without any card field; the page has one packet fetch path). Against the tree of `d4b848dc` 41 page
tests fail: 38 of the 41 new page tests and the three changed page assertions (the three new ones that pass there are the fetch-path
guard, the keys-pinned-to-the-exporter check and the skipped-group guard). 27 deliberate defects, each on a copy and all caught:
precedence swapped; Improve packets read as producer; `carried` read from the cut document; the mode ignored in the exporter and in
the page; the alias dropped from either lookup; the summary uncut or set as markup; `resultFile` always true; the catalog edited by
hand; readers keeping the `item:` prefix; refusals or a missing size printed as zero; the head loaded without a tap; the `inputs`
cross on `intake`; the checklist shown for an Improve packet; the `Checked by:` rule removed or matched mid-line; the label not
upper-cased or keeping its hyphens; the card title raw; the raw name shown for every stage; a zero reader count worded as a count;
the list row without its tooltip. Also green: `node test/skill-frontmatter.test.js` (22 skills), `test/test-groups.test.py` (21),
`test/marketplace-package.test.py` (29), `scripts/check-release-boundary.py --base origin/main` (both change notes accepted).
`test/shiploop-e2e.test.py` was not run: nothing under `test/shiploop_e2e` changed.

**Sizes.** The template grows from 127,259 to 148,794 bytes (+21,535). The committed evidence files are NOT re-exported (the
instruction was to do so only if the new fields are small): re-exporting the five would take them from 60,562 to 137,091 bytes
(+76,529; each stays under the 200,000-byte limit), summaries being 52,575 of the 77,057 bytes of new field text (68%), `carried`
17,115 (22%), `resultFile` 3,724, `summaryTruncated` 2,675 and `packetImprove` 968. The exports for the page's draft database are in the
session scratchpad: `luna1` 35,889 bytes with 39 packet documents, `hello-1190b` 34,645 with 47, `battleship-1220` 29,258 with 46
(`export.py --check` passes on each; byte-identical on a second run). Every run document of the five old files differs from a fresh
export only by the new fields and the R18 `planningReview: not recorded`, and the page reads the old files unchanged.

**Limits, documented not guarded.**
- The head is the literal first 12 non-empty lines of the packet file. For an inline run the file starts with a seven-line delegation
  preamble, so the head ends at the progress line and does not reach `Goal:`; the ticks say the goal is there. Starting the head at the
  `ShipLoop navigator |` line (the part the engine prints) would show Goal, Done when and the callback in the same twelve lines: a
  one-line change in `packetHeadLines`, not made because the instruction said first twelve lines.
- The checklist reads wording, so a packet that restated an item in other words reads as a cross; it says what the text lacks, not what
  the model needed. The patterns were checked on 493 files of six releases, not against a future wording.
- `exitCheck` classes the stage by the row's fields and the mode, not by what the visit did: a `carry-forward` visit that is not the
  last item is `review loop` in the catalog with its `last-item` note, and the visit's own `improve` figures show whether a child ran.
- The declared readers are the stage table's, not observed, and the engine records no observed reads; the card never says "read".
  The stage table declares stage readers only (ShipLoop's scripts read results too), and a later record register may change what
  the card should say about them.
- A skipped visit has a card (no packet, no checklist) and a seeded one says it was not run; a collapsed run of skipped visits keeps the
  old lines.

**Owner decisions.** (1) Re-export the five committed evidence files (+76.5 KB, mostly summaries), or keep them as history and let the
page read them without the fields (chosen here: kept). (2) Start the packet head at the progress line instead of the first line.
(3) Ask the E2E session to keep one packet file per printing so the producer packet of every reviewed stage can be read (104 of 493 files
are an Improve child's today). (4) Republish the template, then upload `config/stages` and the three scratch exports (never over the
hand-built `luna1-plan` and `luna1-step-plan` backchain documents). (5) The later rename commit: regenerate `defaults/stages.json`;
flipping the alias order and the two phase-table entries is optional.
