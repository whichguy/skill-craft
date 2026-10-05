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
