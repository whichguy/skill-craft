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


## 2026-10-07: R21, the rename half, two packet files per visit, the packet head and the real new layout (local, unpublished)

Status: firm for the definitions, the merged-tree results, the real-layout check, the sizes and the tests below. Local commits on
`rr20-ccaebb` on top of the R20a commits: `38e72e66` (the rename half, **atomic with the engine's `bf958708`**), `97dc44ef` (the exporter
reads two packet files per visit, SCHEMA.md, change note `improve-packet-document.md`), `5cd2477d` (the page, change note
`stage-card-improve-packet-and-head.md`) and this entry. No push, no `scripts/release.py`, no E2E run launched or resumed, no
Artifact or ArtifactData call, nothing written under `/Users/dadleet/e2e-runs`; the canonical checkout and `batch1007-68672e` were only
read (`git show`, no checkout). One throwaway worktree and branch (`rr21-merge-919215`) held the merge test and are removed. The
E2E branch's commits read: `bf958708` (stage `select-work` is now `get-next-work-item`, a run saved under the old name is refused),
`3e715dce` (record register), `bc1d6452` (an Improve child's packet gets its own file) on top of `44427a98` (every packet says how its
result is checked: a `Checked by:` line). Related: `d4b848dc`, `9b5e8af6`, `bde62009` (R20a), `ee6712a5`.

**(a) The rename half.** In the throwaway merge of `rr20-ccaebb` with `batch1007-68672e` (no conflicts: the E2E branch touches nothing
under `skills/shiploop-run-review`), the unchanged suite failed exactly four tests, all comparing the committed catalog with the engine's
table (`StageCatalogTests`: the drift test, the stages-command test, the defaults-document test and the upgrade-note test). Changes, one commit:
`defaults/stages.json` regenerated with `export.py --stages` (one line differs); `PHASES` and the page's `STAGE_FLOW` list the new name;
`STAGE_ALIASES` is `(("get-next-work-item", "select-work"),)` in both, the engine's name first and canonical, with a comment saying the old
name is history of ShipLoop 1.22.0 and earlier; SCHEMA.md says so; the test file's current-run fixtures use the new name (`IDS`, `ACCEPTS`,
the plan rows, the card and list fixtures, the skipped and seeded tests, the planning-review accepts), the old name stays where a test is
about old evidence (the alias tests of both sides, a label test, a list-row test and a card test of each name) and one new assertion pins that
it is in no `PHASES` entry; the two genuine 1.22.0 state fixtures take the engine's current stage name in their one history row, since
ShipLoop now refuses the old one. Results: on the merged tree 341 tests OK; on `rr20-ccaebb` alone exactly the four catalog tests are red
(341 run, 4 failures), by design, against the old engine. The commit was made on the merge branch and cherry-picked onto `rr20-ccaebb`
(it applies cleanly to both). **Where the old name is left** at `5cd2477d`, outside history: `scripts/export.py` 2 (a comment and the alias
table), `template/index.html` 2 (the same), `SCHEMA.md` 2 (the alias paragraph), `test/shiploop-run-review.test.py` 18 (all of them
alias or old-evidence tests; 43 before), the two fixtures and `defaults/stages.json` 0. History untouched and still rendering through the alias:
the five committed run exports, the page snapshot, `luna1.review.json`, the journal and the change notes.
*Found on the merged tree (not ours):* `scripts/check-release-boundary.py --base origin/main` fails there because `bf958708` changes
`skills/shiploop-e2e-audit/harness/behavior_capture.py` and `dag_replay.py` with no `changes/shiploop-e2e-audit/*.md` note and no
`No-Change-Note:` trailer; the E2E session must add one before merging. `rr20-ccaebb` alone passes the check.

**(b) Two packet files per visit.** After `bc1d6452` `packet_path` writes an Improve child's printings to `packets/<action>-improve.md` and
leaves the producer packet in `packets/<action>.md`. The exporter now tells a visit's layout by its own files. *New layout:* a `-improve.md`
beside the producer file. The producer file is the packet that was sent, so `carried` is read from it with no Improve test (a producer
file that merely mentions the Improve line stays a producer's), the row gets `improvePacketBytes` and, when readable, `improvePacketDoc`
true, and a second packets document `<runKey>--<action>-improve` is written with `kind` `improve` (the producer's document has no kind).
*Old layout* (ShipLoop 1.22.0 and earlier): no `-improve.md`; a visit whose one file is the child's keeps `packetImprove` and no checklist,
documented as old-layout history; one run may hold both layouts, visit by visit. An unreadable Improve file keeps its size, writes no
document and is counted; an Improve file with no producer file is not a skipped visit. `facts.md` counts both.
*Real-layout check, no model:* the harness's seed pattern (the navigator walking the graph on synthetic results, with `navigator.emit`
printing each packet), run on the merged tree's engine in a scratch directory, wrote 7 visits up to the first inner stage and an
`-improve.md` for each of the three reviewed ones (spec, test-strategy, plan); exported, those three visits have `improvePacketDoc`, all
seven checklist labels found (`inputs` aside on intake) and no `packetImprove`; the documents are 10 (7 producer, 3 improve; producer
packets 26.4 to 52.2 KB, Improve files 19.6 to 24.1 KB because only the first printing was made: the file is overwritten at each printing, so
a real run keeps the last, and the old layout's last printings were 44.8 to 55.5 KB in the 1.22.0 run). The same seed on the old engine
(this branch alone) leaves one file per visit and reads `packetImprove` on those three. `ImprovePacketLayoutTests.test_the_checkouts_own_
navigator_writes_the_layout_the_exporter_reads_for_every_reviewed_stage` runs that seed in a temporary directory and asserts whichever
layout the checkout's engine writes, so it is green on both trees; it fails on the merged tree before this change. **No real run of the new
layout exists yet, and none is committed:** the five committed exports are runs of ShipLoop 1.16.1 to 1.19.0, the 1.22.0 run and the others
re-exported for the draft page are old layout, and the synthetic run's export (`export/synthetic-new-layout`, order 99) is for looking at the
card, not for the live page. The upload cost of a reviewed visit rises by the Improve document (about 45 to 55 KB of packet text each in a
real run, within the 150,000-byte cut); the packets still go in `ArtifactData` batches of at most 50 documents and 1 MiB.

**(c) The packet head** starts at the first line beginning `ShipLoop navigator |` (the engine's own printed head, after the inline run's
delegation preamble) and takes 12 non-empty lines from there, so Goal, Done when, Checked by and the callback show; with no such line it
falls back to the first 12 non-empty lines; a mention of the phrase mid-line does not count; the caption says which start it used.
**(d)** SCHEMA.md points to the E2E session's record register of 2026-10-07 as the place where record kinds are classified and says the
contract does not copy its classes (the register is prose, a hand copy would drift); the card's "declared by the stage spec" is unchanged.
**(e)** The scratch exports were refreshed from the merged tree into
`/private/tmp/claude-501/-Users-dadleet-src-skill-craft/8ee9a7a0-b6e5-4ea7-af94-1c3edde60d84/scratchpad/rr21/export/<key>/` (`luna1`, `hello-1161`,
`hello-1180`, `hello-1190a`, `hello-1190b`, `battleship-1220`, and `synthetic-new-layout`) with `defaults/` holding `config/stages` (34 entries,
`get-next-work-item`); a second export of each from the merged tree is byte-identical to the branch's, `export.py --check` passes, and the old
runs still carry `select-work` rows that resolve through the alias.

**What the card shows for a new-layout visit** (seen in a local server over the template at 375 px, light and dark, `scrollWidth` 375; no
Artifact call; tab and server closed): "Packet size 51 KB" (the producer's), "Improve child's packet file 23.6 KB", seven ticks from the
producer packet, the head opening at "ShipLoop navigator | plan | revision 7" with the callback line, the Packet box, and a second closed
"Improve child's packet" box that, opened, did one read of its own document and showed its size and digest. A 1.22.0 `spec` visit (old layout)
still says its packet file is the Improve child's and has one box.

**Tests.** `python3 -B test/shiploop-run-review.test.py`: **363 OK on the merged tree** (278 at the R20a base `ee6712a5`, 341 after the rename
commit, 353 after the exporter commit with `ImprovePacketLayoutTests` 12, 363 after the page commit with `ImprovePacketCardTests` 7 and
`PacketHeadStartTests` 3); on `rr20-ccaebb` alone the same 363 run with exactly the four catalog tests red. Also green on the merged tree:
`node test/skill-frontmatter.test.js` (22), `test/test-groups.test.py` (21), `test/marketplace-package.test.py` (29); on `rr20-ccaebb`
`scripts/check-release-boundary.py --base origin/main` passes (the three change notes accepted). Fail-first, against a `git archive` of the
tip before each commit with only the test file copied in: the exporter commit, 9 of its 12 new tests fail on `38e72e66` and 10 of 12 on the
merged starting tree (the real-engine test fails there as it should), the three that pass on `38e72e66` are labelled (two guards, and the
real-engine test, a guard of the old layout on the old engine) plus the one facts assertion that pins the changed line; the page commit, 8 of
its 10 new tests fail, the two that pass are labelled guards (one fetch path; one box without the second document). 10 deliberate defects,
each on a copy of the merged tree, all caught: the old-layout test applied to a new-layout producer file; the Improve document never written
or without `kind`; an Improve-only visit read as skipped; the Improve size not recorded; `improvePacketId` ignoring the flag; the head
ignoring the navigator line or matching it mid-line; the Improve box loading without a tap or shown without a second document.

**Sizes.** The template 148,794 to 150,592 bytes (R20a: 127,259). The committed evidence files are unchanged.

**Owner decisions.** (1) The committed-evidence question is unchanged by R21: the five exports are old layout and old name (history, rendered
through the alias and the old-layout mark); re-exporting them only adds the R20a fields (+76.5 KB, mostly summaries), so keep them until a
real new-layout run exists and commit that one. (2) The E2E session needs a `changes/shiploop-e2e-audit` note (or a trailer) for `bf958708`
before its branch passes the release-boundary check. (3) Upload: `config/stages` first (the new name), then each run's `runs` document; never
the synthetic run to the live page; the Improve packet documents add one document per reviewed visit of any new-layout run.

## 2026-10-09: R22c, the findings layer for the runs of 2026-10-07 and 2026-10-08 (local, unpublished)

Status: firm for every status, number and commit below (each checked against git log of origin/main, the release commits, the
committed analyses or the run folders through a committed extract); interim where a line says `Inferred:`. Local commits on branch
`rr22c-eed87d` (worktree `.claude/worktrees/rr22c-eed87d`, from origin/main `1854938b`, rebased onto `923a3bd6` before the first commit):
`04874306` (findings and options), `c258c19d` (stale Luna statements), `078ea087` (expectation-change options) and this entry with the
two run reviews. No push, no `scripts/release.py`, no E2E run, no Artifact or ArtifactData call, nothing written under
`/Users/dadleet/e2e-runs`; the exporter, SCHEMA.md, SKILL.md and the template are untouched (R22a/R22b own them in another worktree).
Every commit passes `scripts/check-release-boundary.py --base origin/main` with a `No-Change-Note` trailer (no skill file changed).

**Sources.** The synthesis objects only (never the lens `reports`): `docs/experiments/batch-1009-round1-analysis-20261008/analysis.json`
(round 1 candidates), `batch-1010-round2-round3-analysis-20261008/round2-analysis.json` (batch-3 scorecard, cost finding, candidates,
round-1 status) and `round3-analysis.json` (batch-4 scorecard, loop-done check, R3-1 to R3-11, remaining known limits);
`test/shiploop_e2e/LEARNINGS.md` 'Round 1', 'Rounds 2 and 3' and 'Correction of 2026-10-09' (`923a3bd6`). The run folders were read
through `docs/experiments/run-review-r22c-20261009/collect.py`, which writes `figures.json` (planning blocks, graph-check receipts, skipped
skill visits, narrative counts, r2's host split, r3's open visit, a replay of the credential screen on the submitted lines, and a read-only
re-collect of the Luna run); the tests read that file, never the run folders. Page keys are the folder names.

**What the bundles hold now.** `general.review.json`: findings o45 to o80 (36: 19 open, 13 fixed, 4 accepted; of the open, 5 broken,
13 bent, 1 not rated on purpose, o68), options a27 to a91 (65: fix-shiploop 26, accept 20, gather-evidence 7, fix-harness 6,
change-expectation 6; open 43, done 20, built 2; 17 recommended, at most one per finding), 10 figures. `r3-battleship-sonnet.review.json`
and `r3-battleship-grok-none.review.json`: one review each (a five-line arc; basis lines for P1, P2, P3, P4, P5 and B2, and P1, P2, P4,
P5, P6 and B2, each citing the run's record or an open finding). Derived chips: Sonnet P1, P2, P4 hold, P3 and B2 bent, P5 broken; Grok
P1, P2, P4 hold, B2 bent, P5 and P6 broken; the rest not examined (no Backchain loop ran, so B1, B3 to B5 have no basis). Every
bundle passes `export.py --check` with exit 0; the only warning in any new document is o68 (the owner's choice, never exercised).
`luna1.review.json`: o34 and o40 fixed, a21 and a17 done, a23 built, o41 and a09 marked, each with a dated mark after the old text.

**Statuses verified, and where they differ from the brief.** Fixed since 1.23.0 and verified in a later round (each a done option with the
commit): A2 (`62b6ac89`, `6049ae17`, 1.26.0), A3 with N1 (`1b9918ab`, `bd3785cb`; `4fc3b3b8`), A5 (`53ab8b78`; its refusal never fired),
A6 (`f1329599`, `ab01b29a`; the launch refusal never fired), H1 (`c7a8187d` to `4e656d23`), R1 (`e39160ae`, `3bac0b19`, `55bee172`),
R2 (`8eb93c21`), U1 (`b3a8e3f1`), S1 (`84d4d9da`), K1 (`3a7bc9f4`), B1a (`0d7a35dd`), W1 (`2b2f4513`), I2 (`1f5006e7`), BC1's packet
text (`4c2a8a98`, `cc705b9d`). Built but never exercised live, so their findings stay open: A1 (`178b514c`), F1 (`e4435c85`). Open on
origin/main: R3-1 to R3-5 (the stage-spec and navigator strings are unchanged since `200c32ce`). Luna review: a21's Done when was checked
today (13 failures, 0 generic tails, 13 own lines on a re-collect with this checkout's harness), so a21 is done, not built; a17 is done
(1.21.0, and the one-pass loop was seen live on Luna xhigh 1.21.0), the brief said shipped; a09's live republish is **unknown** (journal
entries R16 to R21 each leave the template republish to the owner, and this increment made no Artifact call).

**Where the evidence disagreed with a stated claim.** (1) X1: the audit inferred that CSS hex colours trip the credential screen. The replay
says no: r3's refused line carries 7 hex colours and is flagged only for "Signature: the grid reads as an instrument" (`_KEY_VALUE_SECRET`
matches "Signature: the"); without the label it passes, and r2's flagged line has no hex colour. Inferred: the label comes from the Grok
host's frontend-design guidance that r2's spec cites. (2) "35 minutes of Chrome debugging inside implement" (LEARNINGS 'Rounds 2 and 3' and
the round evidence) is the resumed session's length (2114.2 s); the open implement visit is 27.1 min (1626.6 s, 104 turns) and browser work
began 490 s into the session, when that visit opened. (3) The round evidence's `planning_minutes` is a second definition: for round 1 it is
the harness's stage seconds from intake to prepare (1,308 s for Grok, 268 s for Sonnet Battleship); metrics.json's planning window runs to the
first accepted test-spec on the engine clock (Grok 23.3, 15.7, 23.2 min; Sonnet 4.8 to 7.0). Filed as o70 for the E2E session. (4) The brief's
Sonnet 4.9 for r3 Battleship is 291 s; the harness prints 4.8, and so does the bundle. (5) r2-battleship-grok-none is mixed host (the E2E
session's correction, `923a3bd6`): Grok accepted visits 1 to 31 (9 to 31 with no harness after the first harness ended at 855 s), Claude
Sonnet 5.5 accepted 32 to 52 from 01:06:43Z, 32.2 minutes after the harness ended; its planning window (visits 1 to 10) is Grok's on the
engine clock, its tokens and cost are not.

**The three LEARNINGS corrections and the page's own claims.** A grep of every committed review bundle, the page snapshot, the template,
the defaults, SKILL.md, SCHEMA.md, the advice rubric and this journal for "asleep", "caffeinate", "SIGTERM", "pkill", "plugin-dir",
"about:blank", "Chrome" and "display" found none of the three corrected claims (every "display" is CSS or a display name). So no page claim
needed a superseded finding; the corrections appear as engine or harness findings: the SIGTERM cause in o47, the resume line without
`--plugin-dir` in o74 (unfixed on origin/main: `resume_command` adds it only when the command line gave one), and the withdrawn
explanation is stated nowhere (a test holds it so, on its precise phrases). The Chrome findings say "Grok host".

**Not included, on purpose.** What the synthesizer dropped (round-1 X1 as stated, B7, B8, R3-11); round-1 P1, D1, D2, R3 and S2 (did not
recur or are folded into a later candidate); the document-only R3-8, R3-9, R3-10, B3, B6, B10, L1 and U2, except where they explain a kept
finding. v1230-battleship-sonnet has no review (the E2E session regraded it; it appears only in figures.json).

**Not verified.** That r3-checkers-sonnet's release-verify default-port answer came from another listener (the round-3 analysis infers it;
o47 says so); the source of the 'Signature:' label (inferred); whether the live page shows the v2 exports (a09); the cause of the Grok host's
Chrome failure (unproven; o71's first option is the probe that would settle it).

**Tests.** `test/shiploop-run-review.test.py`: 375 tests OK (363 at `923a3bd6`). New, in one block after the bundle classes,
`RoundRunFindingsTests` (12): every bundle passes `--check` and warns only on o68; ids unique across bundles and continuous from o45 and
a27; every `runs` key is a run folder and every criterion a default key (or a key the option proposes); fixed findings cite their commit
in a done option and every done or built option has a ref; no bundle states the withdrawn explanation and the Chrome findings name the
Grok host; the figures equal the analyses' and the extract's numbers; the credential finding names the trigger the screen's replay shows;
a prompt for two new options (and each live option alone, and the first two page changes) stays within the size contract and names no
unticked option; the stale Luna statements carry their marks and evidence; the phase changes keep the current text and the owner's
sentence; the new criteria validate as expectations documents in the SPEC's words for clauses no criterion carries; the two reviews ground
every basis line and derive the chips above. Changed, to follow the data: three `GeneralReviewBundleTests` assertions (the bundle is no
longer two documents) and the `LunaReviewTests` warning list (o34 no longer open). Fail first: on a `git archive` of `923a3bd6` with only
the test file and the extract copied in, all 12 new tests fail (10 failures and 4 errors across 12 tests and 2 subtests: the new bundles
and marks are absent there).

**Open for the owner.** Tick or drop: a87 (phase-2, keeping "there is no limit to this"), a88 (phase-4), a89 to a91 (P7 for S-14, which
shares its key with the Luna review's open S-14 option: tick one; P8 for S-15; P9 for S-3), and a65 (a SPEC carve-out for the refused-run
cap, only if the cap stays). The E2E session's items: a75 and a77 (resume host and plugin directory), a68 (one planning figure per run),
the X1 decision (a79 recommended), and the round-3 text batch (a27, a29, a31, a34, a37). Publishing needs the R22a/R22b exporter first.


## 2026-10-09: R22a, how a run ended: stopped, blocked, left behind, hosts, and the stale statements (local, unpublished)

Status: firm for the definitions, the real-data results, the sizes and the tests below. Local commit on `rr22-940ad8` in
`.claude/worktrees/rr22-940ad8`, base `origin/main` `1854938b` (skill-craft 1.26.0, shiploop-run-review 0.1.2; the shiploop-run-review
change note `changes/shiploop-run-review/run-ending-hosts-blocked-left-behind.md`). R22b follows as its own commit. No push, no
`scripts/release.py`, no E2E run launched or resumed, no Artifact or ArtifactData call, nothing written under `/Users/dadleet/e2e-runs`;
the canonical checkout and every other worktree were not touched, no process was signalled, and no test imports or calls
`test/shiploop_e2e/listeners.py`, `lsof` or the reaper (the exporter only reads `left_behind` from result.json). Related: `f1329599`
(the harness reaps listeners and records `left_behind`), `3b2c42b2` and `dc1edbbb` (a signal ends the hosts and is recorded as a requested
stop), `2b2b4d18` (the operator contract names them), `200c32ce` (1.26.0), R21 `38e72e66`, `97dc44ef`, `5cd2477d`.

**The audit, re-verified against the real files** (11 runs, ShipLoop 0.54.0 to 0.58.0). Confirmed: r3 Grok is state `active`, `process.status`
`stopped`, `termination.resume_stop` "stopped by .../stop", unaccepted stage `implement`, an `incomplete` metrics row of 1626.6 s, 104 turns
and 128 tool calls and its packet file on disk (`wallMin` 36.5 omits those 27.1 minutes); r2 Grok has three invocation files (the original,
a Claude resume and a Grok resume) and its visits 10 to 31 read `calls 0` while visits 1 to 9 carry Grok peaks beside Claude's 1,000,000
window; r1 Grok and v1230 Grok are blocked with `blocked_by` and `awaiting` on the last result and `status_reason` in state.md; r3 Grok
reaped node `:64332` (the worktree) and headless Chrome `:64335` (the work folder), r3 Sonnet reaped node `:3471` and `:3000`; r1 Grok, v1230
Grok and r3 Grok have `worktree_checks` 4/4 against `checks` 0/4; every producer packet of all 11 runs carries a `Checked by:` line (the
one file per finished run without it is the `done` state's). One correction to the brief: `awaiting`, `blocked_by` and `headline` are not in
result.json; they are in the last visit's result record (`results/<action>.md`), and the reason is state.md's `status_reason`.

**What was built.**
- *Stopped (gaps 1 and 2).* `status` takes the value `stopped` when the engine's status is `active` and result.json's
  `termination.process_status` (else `process.status`) is `stopped`, `timeout`, `failed` or `exited`: the engine cannot say its host went away,
  the harness can. A regrade (`not observed`) never makes a run stopped; blocked, paused and done keep the engine's word; no result.json reads
  `active` as before. The current phase's state is `stopped` (`derive_phases` pins it apart from `running` and `blocked`); the header time
  reads "stopped after 36 min, then 27 min of unaccepted work". `ending` (SCHEMA.md "How the run ended") holds `by` (the harness's own
  words, the stop file's absolute path replaced by its name), `stage`, `unacceptedMin` and `unacceptedTurns` from the `incomplete` row (absent,
  never 0, when the row has no timing), the packet issued for that stage (`action`, `packetBytes`, and a `packets` document), this
  invocation's `sessions` and `resumes`, and `earlier` terminations. It is written only when there is something to say (stopped, an unaccepted
  stage, a resume, an earlier termination), so a one-session run has none. The page: a "How it ended" card under the header, a hatched
  chevron "stopped by the harness" (the blocked one now reads "blocked here"; the key under the chevrons says both), and a hatched
  `U` column at the end of the picture outside the visits and the scale, with its own detail, packet head and a row at the end of the stage
  cards.
- *Hosts (3, 4).* `hosts` lists every distinct host, model and effort from `invocation.json` and each `invocation-resume-<host>-<time>.json`
  (ordered by that time). With more than one, `calls`, `contextPeak`, `contextWindow`, `compactions` and every visit's `context` are absent,
  each with the reason "2 hosts ran this (...): the harness mixes their events in one figure, so it is not a measure". A visit whose row
  counts no model call has no `context` (a peak beside "0 calls" was another host's); the page's `contextOf` applies the same rule, so an
  export already in the database stops printing "0 calls" too. The page shows a chip "resumed on <model>".
- *Blocked, left behind, unreturned product (5, 6, 7).* `blocked` {by, reason, headline, question, options, noDefault}; `leftBehind` {observed,
  reason?, reaped[], survived[]} with entries {command, ports, where, endedBy}, no pid, argument list or absolute path, `where` read from the
  path's components (worktree, work, other); `verdicts.worktreeChecks`. The card words the pair: "passes its checks in the worktree; the copy
  in the work folder fails them because nothing was returned there". Only a boolean was exported, not N/N [superseded 2026-10-09: R22d exports `{passed, total}`] (the count is in result.json).
- *Stale statements (10, 11, 12, 17, 21).* The refusals note and the run-detail heading say "refusal lines or failed ShipLoop commands" (the
  harness reads refusal LINES; r3 Sonnet's one failure has the verb `unknown` and exit null); SCHEMA's refusals/glue row no longer says a
  Claude host cannot measure them (refusals 1 to 5 and glue 0 to 2 on the seven Sonnet runs; glue is a lower bound where a model wraps
  ShipLoop); `stages[].context` says every Claude visit has one and a Grok run never does [SUPERSEDED 2026-10-09 by R23c: harness group G2 (6a5dc5cb)
  made a Grok stage row carry {calls, peak}; the page now follows the rows, never the host]; `NO_VISIT_CONTEXT` is a reason per host
  (`no_visit_context`) [SUPERSEDED the same way: removed, no shim]; the `Checked by:` statements (SCHEMA checklist section, the `CARRIED` comment) say the 11 runs carry it; the default
  run name carries the case ("claude claude-sonnet-5-5, battleship, release 1.24.0"; the key rules are unchanged; a Grok run's case is
  `custom`); `test/fixtures/run-review/state-stage.md` resolves the Improve card as the current engine does and the test asserts both modes.
- *The legend* lists only the kinds the picture draws (`legendKinds`: done, rev, blk, skip, seed, na, tail, imp, and ctx, warn, tri only with a
  band, a column at 90% or more, a measured compaction).

**Defects the render found** (a local server over the template, a fake database holding the 11 scratch exports, 375 px): (1) the legend's
`hidden` entries stayed visible because `.sqleg span{display:inline-flex}` beat the hidden attribute; (2) the card's two-column facts grid kept
two columns on a phone, squeezing the value into a 90 px strip; (3) a blocked run's options ran together as one paragraph. Each has a test
(`EndingCardStyleTests` reads the stylesheet, since node has no layout; it can only pin that the rule exists). Seen after the fixes: r3 Grok
(stopped), r1 Grok (blocked), r2 Grok (two hosts), r3 Sonnet (done with two listeners reaped); the final light, dark, 375 px and desktop pass
over all four is in the R22b entry.

**Real data (scratch only, `scratchpad/rr22/export/<key>/`).** All 11 runs export with exit 0, pass `--check`, and a second export into the
same folder is byte-identical; `review-export.json` 13.4 to 36.9 KB (the audit's exports were 12.7 to 38.1 KB). r3 Grok: status `stopped`,
Build `stopped`, `ending` {by "stopped by the stop file", stage implement, 27.1 min, 104 turns, the packet document}, two listeners ended,
`worktreeChecks` true; r1 Grok and v1230 Grok: `blocked` with the question and two options; r2 Grok: two hosts, no mixed figure, no visit
context; r3 Sonnet: done, two reaped listeners, no `ending`.

**Tests.** `python3 -B test/shiploop-run-review.test.py`: **409 OK** (363 at the base). 46 new tests in eight classes (`RunEndingExportTests`,
`RunHostsExportTests`, `RunBlockedAndLeftBehindExportTests`, `RunEndingContractTests`, `EndingCardLogicTests`, `EndingCardPageTests`,
`EndingCardStyleTests`, `TailColumnTests`) and four changed existing ones (the pinned refusals text, the Improve-card assertion over both
modes, the fixture). Fail-first, against a `git archive` of `1854938b` with only the test file copied in: **all 46 new test methods fail
or error** on it (52 failing or erroring cases counting subtests); one of them (`only a run whose engine reads active ...`) first passed
there because its cases are guards, so it now begins with the positive case. Also green: `node test/skill-frontmatter.test.js` (22),
`test/test-groups.test.py` (21), `test/marketplace-package.test.py` (29).

**Sizes.** Template 150,592 to 160,905 bytes.

**Declined or left.** No rename, removal, new collection or id bump was needed; the schema id stays `run-review-export/v2`. Not done: an N/N
for the worktree checks (a boolean was asked for), the `blocked` object for a paused or halted run (its `status_reason` is only used for
`blocked`), and the header's "1 refusals" plural (cosmetic, a test pins the text).


## 2026-10-09: R22b, script checks, unverified outcomes, tool use, the planning window and graph-check Backchain (local, unpublished)

Status: firm for the definitions, the real-data results, the sizes, the tests and the render below. Local commit on `rr22-940ad8` after
R22a `7ff90399` (change note `changes/shiploop-run-review/script-checks-unverified-tool-use-planning.md`); same boundaries as R22a (no push,
no `scripts/release.py`, no E2E run, no Artifact or ArtifactData call, nothing written under `/Users/dadleet/e2e-runs`, no process signalled,
`listeners.py` never imported). Related: R12 (`_model_measures` and the unmeasured rules this follows), R16 (`find_backchain_loops`, which
required an `until-loop-receipt.json`), R20a (the stage card these lines join), and the harness's `verifications`, `ToolLog.tool_use` and
`planning_window` in `test/shiploop_e2e/metrics.py`.

**The audit, re-verified.** `accepted_ran` lives in `run/tests/<action>-verifyN.md` `runs[]` and the exporter never read it; a record is
`{action, stage, disposition, passed, expect?, runs[{status, exit, counts{ran, failed}, accepted_ran?, ids_missing}], observed?}`, and one
action can have several records (r2 Checkers: 13 records on 11 visits, the test-author visit has three, two refused for ids-missing, 11
passed). The harness's `script_verifications.red` counts the records in which a command ran red; a test-red record passes because red is what
it accepts. release-verify's `observed` is `{where, copy, tree, head, kind, source, plan, receipt, ahead}` (r3 Sonnet: `returned-result`, tree
`5f846af6...`, while the result's summary says "not a clean consumer-check copy"). `unverified` is `[{outcome, reason, check, owner,
due_stage}]` on `product-acceptance` (r3 and r2 Battleship Sonnet one item each; `[]` on r2 Checkers, r3 Checkers and r2 Grok; no key on
`handoff` in any run). `tool_use` exists only for a Claude run (None on every Grok run, so also on the two-host r2 Grok run), with
`scratch_scripts[{path, bytes, wraps_shiploop, runs}]` and `packets{on_disk{files, bytes}, printed{replies, chars}, read{read_tool[{packet,
whole, chars}], shell{calls, chars}}}`. The `planning` block is on 10 of the 11 runs (the 1.22.0 Grok run has none), its `tokens` is
`{output, reasoning, clock, source}` on Grok and `{unmeasured}` on Claude. Backchain: `run/backchain/<action>/` with only `check-*.json` and
`candidate-*.json` and no `until-loop-receipt.json` on r1 Grok, r1 Sonnet, r2 Checkers (two receipts, the invalid one seven seconds before the ok one by
file time, so the last is ok as the audit reads it; the exporter takes the newest by `(mtime, name)`, as `_last_check` always did) and the 1.22.0
Grok run.
*Correction to my own first reading:* the audit's two tolerances hold, with one precision: the block's per-stage seconds equal the exporter's
`min` within 3 s (a tenth of a minute is 6 s of rounding), and the Improve seconds differ from `improve.min` by at most 1.2 s **per child**
(0.0 to 1.2 on the 10 runs; the total over five children is up to 3.9 s).

**Field shapes** (all optional, nothing renamed or removed, schema id unchanged):

| Field | Shape |
| --- | --- |
| `stages[].verify` | `{records, passed, red?, couldNotRun?, runs?[{status, ran?, failed?, acceptedRan?}], observed?{where?, tree12?}}`; `runs` of the last record, `red` and `passed` over all |
| `stages[].unverified` | `[{outcome?, reason?, check?, owner?, dueStage?}]`, texts cut at 300 characters with an ellipsis; `[]` is "none listed", no key claims nothing |
| `toolUse` | `{wrappers?[{name, runs}], packets?{files?, bytes?, printed?, printedChars?, readWhole?, readPartial?, shellReads?, shellChars?}}`; absent with `unmeasured.toolUse` where the harness has no record |
| `planning` | `{closed?, through?, windowMin?, hostWindowMin?, improveMin?, children?, outputTokens?, reasoningPct?}` read from the block; reasons `unmeasured.planning`, `planningHostWindow`, `planningImprove`, `planningTokens` |
| backchain `graphCheckOnly` | `true` on the document of a stage that ran only `backchain-check`; no segments, fact "graph check only: N checks, last ok (complete)", `candidateMatch` as for a loop |

`readPartial` is one more than the audit named (the packets Read by offset); everything else is as proposed. The page: "Checked by the script"
in the Done block, "Left unverified (owner, due stage)" in the Written block on the visits whose result has the list, "planning X min, closed
at <stage>" on the Elapsed card, the packet-use line on the Context card (also when the context is not measured), a "Model glue" row that reads
"2 commands + 41 runs of 3 wrapper scripts (...): a lower bound" and a "Planning window" row in the run detail, a graph-check card with a sentence
saying no Until Loop ran, "plan: graph check only" in the lane, and the Backchain card counting a graph check apart from a loop.

**Real data (scratch only).** All 11 runs export with exit 0, pass `--check` and re-export byte-identically; `review-export.json` 13.9 to 39.5
KB (R22a: 13.4 to 36.9). Script checks: 2 to 19 records a run (r3 Grok stopped after 2), r2 Checkers 13/11. Unverified: r3 and r2 Battleship
Sonnet one item each. Wrappers: r3 Sonnet `done.py` 30, `istart.sh` 7, `ifinish.sh` 4 (glue 2); r1 Sonnet `sub.sh` 30, `istart.sh` 7; r1 Checkers
`sub.sh` 29, `ih.sh` 10. Planning: 23.3, 15.7 and 23.2 min on the three Grok Battleship runs (r1, r2, r3) and 4.8 to 7.0 on the Sonnet runs, all closed at
test-spec (a Grok window is roughly three to four times a Sonnet one; none crosses the owner's 30-minute rule). Graph checks: four runs.

**What the four rendered runs show now** (a local server over the template with a fake database holding the 11 scratch exports; 375 px and a
1024 px pane, light and dark each; `scrollWidth` equals the viewport at 375). r3 Sonnet (done): "How it ended: done" with the two node listeners
the harness ended, Elapsed note "planning 4.8 min, closed at test-spec", the Context card with its packet line, a Backchain card that says none, and
on the product-acceptance card the unverified browser check with its owner and due stage. r3 Grok (stopped): the card first (stopped by the stop
file, Implement 27.1 min and 104 turns never accepted, the earlier SIGTERM at Test author, two listeners, the unreturned product passes in the
worktree), the Build chevron hatched "stopped by the harness", a hatched `U` column that opens a detail with a packet head read from the packets
document, a legend of two entries. r1 Grok (blocked): the question, the two options one per line, why no default, 2 sessions and 1 resume, "blocked
here" on System test. r2 Grok (two hosts): the chip "resumed on claude-sonnet-5-5", the Context card "not measured" with the two-host reason, no
visit context. **Defects found in this pass:** (1) the unverified item read "... was done Check: Open ..." as one run-on; it is now "Reason: ...
Check: ..." with full stops; (2) the first draft printed "47 printed replys" (the plural helper adds an s; the test caught it); (3) not fixed, noted:
the Context card grows tall with the packet line on a phone (it sits beside the Refusals card, which stretches), and `kbText` prints "1760.4 KB"
where "1.7 MB" would read better; the header still says "1 refusals".

**Tests.** `python3 -B test/shiploop-run-review.test.py`: **433 OK** (409 after R22a, 363 at the base). 24 new tests in five classes
(`VerifyAndUnverifiedExportTests`, `ToolUseAndPlanningExportTests`, `GraphCheckOnlyBackchainTests`, `ChecksPlanningPageLogicTests`,
`ChecksPlanningPageTests`) and four changed ones, each deliberate: `make_run`'s fixture now carries `tool_use: None` and a planning block as a
current harness writes them, the two tests that pinned the exact `unmeasured` set add the `toolUse` reason, and the R16 test that said a folder with
only check receipts is no loop now says it is a graph check. Fail-first, against a `git archive` of `7ff90399` with only the test file copied in:
**all 24 new test methods fail or error** on it, and so do the three changed ones (26 failing in the run that also holds them); one (the planning block's
seconds against the stage minutes) first passed there because it only restated existing behaviour, so it now also asserts the run carries the
`planning` object. **20 deliberate defects** on a scratch copy (red counted from passed runs, the stop path kept, only `stopped` ending a run, argv
leaked, two hosts keeping calls, zero-call context kept, the planning window rounded to whole minutes, a legend listing everything, the tail setting
the scale, an empty unverified list saying nothing, glue without its lower bound, the oldest receipt named, a loop folder read as a graph check,
the reason not cut, a regrade stopped, the first record's runs, "0 calls" back on the page, a missing chevron label, the tail drawing a band
dash, and `where` taking the farthest component): 18 caught first; the two survivors (`where` precedence, the tail's not-measured dash) got an
assertion each (`_where` now takes the component nearest the process, and a test says so), then 20 of 20. Also green:
`node test/skill-frontmatter.test.js` (22), `test/test-groups.test.py` (21), `test/marketplace-package.test.py` (29),
`scripts/check-release-boundary.py --base origin/main` (OK).

**Sizes.** Template 150,592 (base) to 160,905 (R22a) to 167,327 bytes. Export sizes above. `MAX_COMPACT_BYTES` (200,000) is not near.

**Open questions for the owner.** (1) Should a Grok run's case read `custom` in the picker, or should the harness record the prompt's case? Two
Grok Battleship runs of different prompts would collide in the picker (the keys differ by date). (2) `stopped` includes `exited` with the engine
still active (a spent resume budget): is that the label you want, or `ended`? (3) The unaccepted tail's packet is exported as a `packets` document
like any visit's (47 KB on r3 Grok); say if you would rather not upload it. (4) The N/N for the worktree checks was left out (a boolean was
asked for); the count is one line to add. (5) Items 18, 19, 20, 22 and 23 of the audit were not part of this brief and were not touched.


## 2026-10-09: R22d, counts in the right number, megabyte sizes, and the worktree checks as N/N (local, unpublished)

Status: firm. One local commit on `rr22c-eed87d` on top of `b3140b16` (the integrated R22a, R22b and the findings layer, base `origin/main`
`923a3bd6`); change note `changes/shiploop-run-review/plurals-megabytes-worktree-counts.md`. Same boundaries as R22a and R22b: no push, no
`scripts/release.py`, no Artifact or ArtifactData call, nothing exported to the draft page, no process signalled, no e2e-runs write, hermetic
fixtures. The coordinator's answers to the R22b open questions: the worktree checks are exported as counts (done here), `stopped` stays the
status label (the ending block already says by what), and the unaccepted tail's packet document stays. The case-`custom` question was not
answered and is still open.

**(1) Plurals.** The header read "1 refusals" because `headerFacts` printed the number and the plural noun without asking the number. One
pure helper in the logic block now owns it: `plural(n, word, irregular?)` (the page already had `plural(n, word)`; it gains the third argument for
"1 child, 2 children" and "1 printed reply, 3 printed replies"). Every counted noun the page printed another way now goes through it: the header
line ("1 refusal", "0 refusals", "13 refusals"; glue is a mass noun and stays "1 glue"), the prompt's run facts ("1 visit", "1 Improve pass", "1
refusal"), the Refusals card note and the run-detail heading ("refusal line or failed ShipLoop command" for one: `refusalNote`), the planning
text ("over 1 child"), the packet-use line ("1 printed reply") and the where strip ("1 of 1 visit"). `passes`/`pass` and `children` had the
same bug in the exporter's `imp` header text ("1 children, 1 review passes"): `_count(n, word, irregular?)` fixes it there ("1 child, 1 review
pass"), and the facts lines ("1 accepted action", "1 record names an action that is no visit"). The card label "Refusals" names the measure, like
"Visits", and stays. Not changed: exports already in the database and the committed evidence files keep their stored `imp` text ("1 children"),
which the page prints as it is (it is data; a re-export gives the new text).

**(2) Sizes.** `kbText` prints bytes, KB, and from 1000 KB up MB with one decimal ("1.7 MB", not "1760.4 KB"; 999.9 KB is the last KB, 1023999
bytes already reads "1 MB"). Pinned at 0, 814, 1023, 1024, 1536, 47475, 55492, 1023897, 1023999, 1048576, 1802659, 5 MiB and 50 MiB bytes.

**(3) Worktree checks.** `verdicts.worktreeChecks` is `{passed, total}` (the harness's `shiploop.worktree_checks`, counted: r3 Grok, r1 Grok and
the 1.22.0 Grok run each 4/4); `passed` equal to `total` is the old boolean's true, so one shape carries both. `verdicts` is no longer a map of
booleans only (SCHEMA.md, validator kind `verdicts`): a boolean in that place is refused, and the page reads only the count shape (`worktreeOf`),
so an R22a-shaped boolean invents no verdict. The page says "passes 4/4 checks in the worktree; the copy in the work folder fails them because
nothing was returned there" (or "... and the copy in the work folder fails its checks too" when fewer pass), a chip "worktree checks 4/4" green only
when all pass, and the facts line "Checks in the worktree (product not returned): 4/4 pass". The R22a entry's sentence that only a boolean was
exported is marked superseded in place.

**Tests.** `python3 -B test/shiploop-run-review.test.py`: **458 OK** (445 at `b3140b16`). 13 new tests in three classes
(`CountsInTheRightNumberTests` 6, `MegabyteSizeTests` 2, `WorktreeChecksCountTests` 5) and nine changed existing ones (the `imp` strings, the
worktree verdict tests and fixtures, the ending-card texts, the packet-use size, the orphan-record fact, the contract test). Fail-first, against a
`git archive` of `b3140b16` with only the test file copied in: all 13 new tests fail on it and so do the nine changed ones (22 failing). Nine
deliberate defects on a scratch copy (the irregular plural ignored, the header printing the plural for one, the MB threshold at 1024 KB, a count
accepting passed over total, the chip green for any count, the refusal note never singular, the count always `total`, `imp` printing "1 children",
the prompt facts "1 visits"): 9 of 9 caught. Real data (scratch only, `scratchpad/rr22/export-d/`): all 11 runs export with exit 0, pass `--check`
and re-export byte-identically; `imp` reads "0 children" and "2 children, 4 review passes" and so on.

## 2026-10-09: R23, the export and page read what harness batch 1011 records (local, unpublished)

**Question.** E2E's batch 1011 (origin/main `5e22fd10`, 104 commits, test/ and docs/ only) added records the exporter did not read: outcome
class, build identity, environment and overlap, product at the stop, quality, the fidelity block, fresh starts with their re-grounding cost, and
per-visit context for Grok. What does a reader of a run need from them, and what stays out? Rules in force: additive optional fields only (old
exports still render and validate), a measure not reported is unknown and never zero, generic text, KISS, fail-first script-run tests.

**Base and method.** R22 (`49209d1f`, 7 commits) merged onto `5e22fd10` with no conflict (merge `75fa4436`; Run Review suite 458 OK, the same
as before the merge). Fixture `d45dea14`: `docs/experiments/run-review-r23-20261009/{collect.py,figures.json}` reuses E2E's read-only
`generate.py saved_records()` over the seven saved runs of 2026-10-07/08 (no process started, nothing written to the run folders) and adds
E2E's full-length examples for the keys no saved run has; its hand-off table cuts every example at about 100 characters, which hid the inner
shapes. Three slices were built in parallel worktrees by three agents and integrated by merge: A `rr23a-3c735b`, B `rr23b-3c2f77`, C
`rr23c-cc04a4`. (The worktrees were first created from the canonical checkout's stale `main`, not the R23 base; each agent fast-forwarded its
own branch to `d45dea14` before starting and lost nothing.)

**Facts from E2E's answers (2026-10-09), now relied on.** `outcome_class` is the closed list PASS, FAILED, BLOCKED, STOPPED plus null (a record,
never a verdict; not in the baseline row). An Improve packet has five labels, goal, done_when, checked_by, output, recovery; engines before
skill-craft 1.25.0 wrote only the last three, so goal and done_when 0 of 8 on a 1.24.0 run is by design. A Grok stage row carries
`{calls, peak, peakPct: null}` from G2 (6a5dc5cb); a row with no events has no `context`. `result.json` is written twice when a quality phase
applies, so an absent `quality` is "not applicable or not yet", never zero.

**R23a (`055bb43b`, `1c59773b`): outcome, build, environment, product at the stop.** Over the seven saved runs: 4 PASS, 2 BLOCKED (v1230 Grok and
r1 Grok), 1 STOPPED (r3 Grok). Host build is null on the four runs a Grok launch started and `2.1.294` on the three Sonnet runs. All seven were
only regraded, so `environment.start` and `.end` are unobserved on all seven (the page says so). Every run has an observed overlap with one or two
siblings: 12 entries, 548.2 to 1249.8 s of shared time; r1 Sonnet's sibling began 0.4 s earlier, which would print `-0.0` (clamped). The harness
keeps an `identity_unmeasured` note even for hashes a regrade recomputed, so a reason is copied only for a field that is null. The STOPPED run's
basis embeds the stop file's absolute path, exported as "the stop file". Kept beyond the proposal: `engineStatus`/`engineStage` on
`productAtStop` (a partial product must not read as a finished one) and browser `targets` (a browser that cannot load a page is the cause of the
"access" blocked runs). Dropped: cpus, loadavg, the end record, `hosts_used`/`environments`/`mixed_host` (the `hosts` list already comes from the
launch records), binary paths, `overlap.span`. No saved run has an observed start or a `product_at_stop`; those shapes come from E2E's examples.

**R23b (`fa7bc132`, `6f782896`, `164b2a6a`): the fidelity reading and the Improve packets, scored by the exporter.** On r1 Sonnet the block reads
script 15, loop 7, file 1, note 12, sentence 0, skipped 2, unclassified 0 over 37 accepted stages; 10 verify records over 29 command runs and 6
distinct commands, 2 of them red; 23 rows carry a test count and none ran zero tests; 1 script-owned edit (`sed -i` on `return-plan.md`), 0 kills
by name, 1 git command by the model; 5 refusals, 1 repeated (release 2, release-plan 2, intake 1). The run's own `refusals` stays the one count
(`metrics.shiploop_failures`, 5, agreeing with the block); the block's detail is dropped with a reason if the two ever disagree. The Improve
table is scored from the packet files by the exporter, with each marker phrase pinned to `shiploop_navigator.py` by a test, and NOT read from
`fidelity.improve_packets` (E2E marked that copy temporary and asked the Run Review side to adopt it). By hand, read-only, on the saved runs: r1
Sonnet (1.24.0) read 8, goal 0, done_when 0, checked_by 8, output 8, recovery 8; r3 Sonnet (1.26.0) 8 of 8 on all five; both equal E2E's
examples. The page prints the counts beside the run's release and never as a defect flag. E2E's "63 files, 35 with all five, 28 without" is over
its whole saved set; the seven runs in `figures.json` hold 31 files, 19 with all five (1.25.0 and later) and 12 without (1.22.0 and 1.24.0);
SCHEMA.md cites the 31. `stages[].evidenceClass` kept (the only place the page shows what evidenced a stage next to the exit check the catalog
declares). Dropped: `tool_calls_seen`, `end_state` (status/ending/blocked already say it), per-record refs, `by_suite`, event numbers.

**R23c (`6ca53ab9`, `ac0f342f`): fresh starts, delivered quality, and a visit's context follows the data.** The seven saved runs hold 13 fresh
starts, all Grok compactions (v1230 6, five measured; r1 Grok 4, three; r2 Grok 1, none, the mixed-host window "may span two sessions"; r3 Grok
2, one). The nine measured windows took 1 to 54 tool calls (median 20) and 8.9 to 465.1 s (median 122); the first grounding was a packet read 7
times and another ShipLoop command twice. One failed ShipLoop command was counted, in v1230's carry-forward (a loop contract 234 bytes over its
budget). Failures and rewrites are lower bounds by the harness's own words, kept verbatim as `bound` and `scope` and printed beside the numbers.
The three Claude runs record `[]` plus a note that compactions are not detected on that host, so `[]` means unknown there: the exporter writes no
list and `unmeasured.freshStarts` holds the note. Quality: the r3 Checkers block is 21,100 bytes and exports as 1,322: mutation ratio 0.907
under operator js-1 (78 killed, 8 survived, of 86 sites; one killed mutant was a timeout and two were killed with a fixed port refused, which the
harness says raise the ratio, so the page prints both beside it); held-out checks 5 of 6 pass (`off-board-keeps-turn` failed); the model made
two writes to its own memory. The ratio is comparable only within one operator. Visit context: on disk r2 Grok has 33 of 52 rows reading
`{calls: 0, peak: null}` and r1 Grok has none, so the reason is now read from the rows (`unmeasured.visitContext` also when only some visits lack
a context); `NO_VISIT_CONTEXT_GROK` and `no_visit_context` are removed (no shim); the R22 sentence that said otherwise is marked superseded in
place above.

**Integration (`ae9d616c`, `8046f586`, `02a6c393`).** The only conflicts were three slices adding next to the same lines. Two needed more than
keeping both sides: the stage-item field dict closes on both sides of the conflict, and `renderFreshStarts` and `renderFidelity` shared one
closing brace in the common text, which left the first without its own (90 page tests failed with "Unexpected end of input" until restored).
The test file's three classes were aligned by git on their shared `KEY`/`setUp` body, so A+C's side was kept and B's `R23b` block (all prefixed)
was appended whole from its branch. One bound moved: `facts.md` of the default fixture is 26 lines (fresh starts, fidelity and Improve packets
add one line each saying what the run does not carry), so the digest guard is 30, not 25. `figures.json` of R22c and R23 now select the Run
Review suite in `test/suite_catalog.py` (`suite_catalog.targeted` checked).

**Tests.** Run Review suite **572 OK** (458 at the R22 tip; +36 A, +50 C, +28 B). Each slice ran its new tests red first for the right reason
(A: 18 of 20 export tests and 12 of 12 page tests; B: 4 failures and 12 errors, then 11 of 11 page tests; C: five groups red); A's mutation
check on the real files caught 24 of 24 deliberate defects. The four committed review bundles `--check` ok with the same warning counts
(0, 1, 5, 0, 0 with the sample). `check-release-boundary.py --base origin/main` OK. `test-groups` 27 and `marketplace-package` OK; E2E suites
that call the exporter: quality 128 OK, e2e 404 OK, fidelity 142 with **one red by design**: E2E's tripwire
`ImprovePacketsTest.test_the_exporter_scores_producer_packets_only_so_the_five_questions_of_an_improve_packet_are_read_here` fails as soon as
the exporter carries the Improve markers, and tells the E2E owner to delete the harness's temporary `IMPROVE_QUESTIONS`/`OLD_LAYOUT_MARKER`/
`improve_packets` and its replay tests. That deletion has to land before or with this branch.

**Status.** Findings: firm for the counts above (each is read from `figures.json`, which is read from the saved runs by E2E's read-only code);
exploratory for how a reader uses the new cards (nobody has looked at them yet). Not built: R23g (a `cells` collection from
`run.py --baseline-report --json` for a compare view; a data-structure change, the owner's and E2E's call); marking the fresh-start visit in
the SVG picture. Not checked: a phone-width render (no agent could start a browser). Open for the first real post-merge run: `sessions.jsonl`
runs (kind first/fresh/continued, reasons) and a `quality` block of a run made after the merge; this entry's fresh-start figures are all Grok
compactions of regraded runs.

**Follow-up, same day: the page was looked at (draft v10, `96bf74b4`).** Real post-merge runs exist now (E2E, 5e22fd10, Claude Sonnet,
hello with `--planning-review none`): `s6-after-spec` (stopped after spec with a cleared context, resumed in a fresh session; a real
`sessions.jsonl`) and `s6-inside-implement` (an unstopped full run). Both export with the integrated exporter and are in the draft with their
packets (3 run documents, 74 packet documents; a third run, `r3-checkers-quality-preview`, is the saved Checkers run with the quality block
E2E committed for that exact run overlaid, labelled as a preview in its name). On `s6-after-spec` the page shows: outcome PASS and the build
line (plugin a03059c9db03, prompt d2d7e2dabeeb, host build 2.1.295); evidence script 13, loop 2, file 18, note 2 over 35 accepted stages; 11
verify records, 25 command runs, 2 red; 5 refusals, 0 repeated (release-verify 2, system-test-author 2, test-green 1); Improve packets 3 of 3
on all five labels at 1.26.0; and one fresh start, a new host session in test-strategy, re-grounded in 6 calls and 21 s with `shiploop next`,
with the harness's lower-bound notes beside it and "compactions not detected on this host" marking the list as not complete. The page was
rendered through a static local page with a stub for the page's database (`window.claude.use("db")`), in the built-in browser, at desktop
width and at 375 px: no horizontal overflow on any new card. One defect found only by looking: the `file` class of the evidence bar was filled
with the page's own tint and the bar has no track, so the second-largest class read as a gap; it now has a fill of its own (pinned by a test,
red then green). Still not seen: a run that did not pass with a real `product_at_stop` (no real run has one yet), and dark mode.

**Second follow-up, 2026-10-10: reading the whole page, one place per figure, what was delivered, and links (`2a603293`, `06dbd479`, `2cde45c9`, `5618977a`).**
Owner asked for the draft to be read as one report, clear and not duplicative, then for insight into what a run delivered (what was
built, tested and documented, whether a skill was chosen or produced, what kind of release, whether it was merged back to the original
branch) and for links wherever a reference can be one.
*One place per figure.* Measured on the rendered page for s6-after-spec: refusals appeared in the header line, a KPI card, the Fidelity
card and the run detail; compactions three times with the same harness sentence; elapsed and context peak on a card and in the detail;
the Improve packet counts and the packet reads as extra lines inside two KPI cards. Now each is on one card; the Fidelity, Fresh starts
and Quality cards are one group after the stage cards. Step 1 for that run went 16,580 to 16,267 characters (the gain is not length).
Refusal lines carried the run's absolute folder; `failure_line` keeps `<run>/.shiploop-runs/...`. Findings and options (80 and 91): every
option links to a finding; 13 findings have no option, 10 closed and 3 open (o16, o23, o30) that say "no option yet" in their advice; the
overlaps are themes recorded at different times, left as they are because ticks are keyed by option id.
*What was delivered (D).* The answer is in three records beside the run directory: workspace.md (source branch and head, run branch,
status), return-plan.md (each path, change, disposition) and return-receipt.md (kind, status, heads). Over the 14 runs in the draft: 9
returned by fast-forward-merge; 1 (v1230-battleship-sonnet) return-planned, not returned; 3 Grok runs (r1 blocked, r3 stopped, v1230
blocked) never returned (workspace status prepared, no plan, no receipt), so the card says "Not merged back: the product is on branch X;
main was not changed" and its file lists "not measured". Kept files for the returned Checkers run: source 3, tests 4 (two under system/,
two under test/), docs 1, ShipLoop records 10, skills 0; the hello run: 1/1/0/10/0. Tests: the widest command of the release-verify
visit, never a sum (a regression visit lists 21+11+32 for a 32-test suite). Both returned runs were returned twice, so "before" is the
workspace's source_head, not the receipt's source_before. r3 Grok's last counted run is "17 ran, 15 failed, at test-red": the card says
the new tests are meant to fail there. A run with no return plan says so in one row, not five.
*Links (E).* `config/page.repoUrl` (https only; `--check` refuses anything else; `--defaults --live` adds it to a live page without
overwriting the owner's). `linkParts` links, over the committed general, luna1 and r3 review files: 143 ids (83 findings, 60 options),
338 repo paths, 220 commits (83 distinct), 178 spec clauses. Words that look like hex (`defaced`, `decade`, 1234567) stay text; 11 ids
that exist only in another bundle stay text in that bundle (they link on the live page, where all are loaded). Run-local paths are not
links: they are files on the machine that ran the case. The step-4 prompt stays plain text (pinned). Links to documents that exist only
on unpushed branches (for example docs/experiments/run-review-r22c-20261009/) will 404 until the push.
*Tests.* Run Review suite 620 OK. Slices D (24 tests) and E (19) ran red first; the two follow-ups on the card were pinned and the red-run
note was written after its fix. Draft v12 carries all of it; the page was read in the built-in browser through a stub database at desktop
width and at 375 px (first pass; the later cards were read as text and by screenshot at desktop width only).

