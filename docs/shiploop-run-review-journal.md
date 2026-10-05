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
