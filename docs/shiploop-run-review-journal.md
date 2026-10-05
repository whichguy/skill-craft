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
