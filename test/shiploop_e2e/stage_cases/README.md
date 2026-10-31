# The stage suite: scenarios

One ShipLoop stage, one packet, one scenario, one verdict. A scenario plants conditions in a small repository and names
controls the stage must leave alone. The suite then checks, with scripts and no model, that

- the stage's packet puts each planted signal and the right instructions in front of the model (the **render** tier), and
- the check list that will grade a model's output can tell a good output from each bad one (the **verify** tier).

The plan is `docs/plans/shiploop-stage-suite.md`. The code is `test/shiploop_e2e/stage_suite/`; this folder holds only
scenario data.

```
test/shiploop_e2e/
  stage_suite/
    stage_oracle.py   the check engine (one function per check kind, one verdict rule)
    stage_build.py    the scenario schema and loader, file composition, the seam-based build, the render
    stages.py         the command line: list | verify | render, selectors, reports
  stage_cases/
    README.md         this file
    <stage>/<scenario>/   one scenario each
```

Tests: `test/shiploop-e2e-stage-oracle.test.py`, `test/shiploop-e2e-stage-build.test.py` and
`test/shiploop-e2e-stages.test.py`, one per module, all hermetic.

## The three tiers

| Tier | Command | Model | Built | What it proves |
|---|---|---|---|---|
| verify (T0) | `stages.py verify` | no | yes | The scenario's `oracle` checks pass `reference/good` and fail every `reference/bad-*` on the ids that bad output declares, so the oracle can fail each planted condition and control. No ShipLoop run is started. |
| render (T1) | `stages.py render` | no | yes | A real run is built to the scenario's stage with the engine's own seed seam, `shiploop next` is run, and the `render` checks read the packet. A stage the engine settles by script (no packet) is checked as that. |
| live (T2) | `stages.py live` | yes | **no, step 3** | A model that follows only this packet has the intended effect, graded by the same `oracle` checks over N samples. |

`live` is accepted in a scenario's `tiers` and in its `live` block, and is validated like the rest, but nothing runs it
yet. `stages.py` names `live`, `grade` and `report` as not built; it does not stub them. Step 3 adds them on the slice
launcher.

A scenario for an Improve stage (`improve@<stage>`) or an outer stage loads and validates but does not build yet; the
render tier skips it and says so.

## A scenario

```
<stage>/<scenario>/
  scenario.json
  repo/              optional  files laid over the fixture BEFORE the baseline commit (a planted fault lives here)
  worktree/          optional  files laid into the execution checkout at the seed point (what earlier stages left);
                               for a scenario past implement they are laid before implement is recorded, or document
                               records itself not applicable for want of a change. Not allowed for a stage at or before
                               validate-existing: nothing before implement changes the tree, and the checks that stage
                               runs on entry come before the seed point, so those files go in repo/
  notes/             optional  files laid into RUN/notes/
  reference/
    good/            result.json (the stage's accepted result, a JSON object with "outcome") and optional tree/
    bad-<slug>/      the same, plus meta.json {"fails": ["P1", ...], "why": "..."}
```

`tree/` is overlaid on the seed tree (the fixture, then `repo/`, then `worktree/`). A path named in `deleted.txt` (one
per line, beside `result.json`) is removed from it.

### scenario.json

Unknown keys are rejected. `about` and `fixture` are required; `request_from` is required once the render or live tier
is on. Every other key has a default.

| Key | Meaning |
|---|---|
| `stage` | A stage of `shiploop_stage_spec`, or `improve@<stage>`. It must equal the stage folder the scenario sits in. |
| `about` | One sentence: the situation and what the stage must do with it. |
| `tags` | Free labels for selection (`catch`, `control`, `send-back`, ...). Letters, digits, `-` and `_`. |
| `tiers` | A subset of `verify`, `render`, `live`. Default: all three. |
| `fixture` | A folder under `test/shiploop_e2e/fixtures/` (the repository the run starts from). |
| `request_from` | A key of `test/shiploop_e2e/step_cases.json`; supplies the prompt, the work item and the checks. |
| `options` | `{"delegation": "inline" \| "ask-agent"}`, default `inline`. |
| `seed_records` | `{stage: fields}` merged into that earlier stage's synthetic result. The engine validates them, so a record that drifts from its contract fails at seed time. |
| `worktree_mode` | `committed` or `uncommitted` (default). Reserved: `committed` validates and the builder refuses it. |
| `planted` | `[{"id": "P1", "what": ..., "signature": ...}]`: what the stage must catch, and the token, id, exit code or path a script can see. |
| `controls` | `[{"id": "C1", "what": ...}]`: what the stage must leave alone. |
| `render` | Checks run on the rendered packet (render tier). |
| `oracle` | Checks run on a stage output (verify tier now, live tier later). |
| `live` | `{"samples": 3, "pass": "all"}`; the defaults. Not run in this step. |

Rules the loader keeps (all problems of all scenarios are listed in one error):

- Ids are unique within a scenario (planted and controls together): `P<n>` for a planted condition, `C<n>` for a control.
- A `render` check's `proves` names a known id.
- With the verify or live tier on, **every planted and control id is proven by at least one `oracle` check**.
- With the verify tier on, `reference/good` exists, and **every planted and control id is failed by at least one
  `reference/bad-*`**. That is the proof the oracle can fail it: a check that no bad output ever trips has not been
  shown to measure anything.
- A `meta.json` parses and names known ids; a `result.json` is an object with an `outcome`.

### A worked example

`validate-existing/broken-works-small-fix`: the step plan says `paginate()` works for an evenly divided list (E1, a
`works` expectation, but on the planted base it does not), loses the last partial page (E2, `broken`, reproduces) and
has no regression test yet (E3, `absent`). A guard in `repo/src/strings.js` makes `capitalize('')` throw, which E1
depends on. The stage must fix that one line and leave the item's own change alone. (`seed_records` is shortened here;
the file holds the whole step plan and test specification.)

```json
{
  "stage": "validate-existing",
  "about": "A works expectation the step relies on fails on the item base because of a small, known fault in a file outside the item's own change; the broken and absent expectations match.",
  "tags": ["catch", "prep-fix"],
  "tiers": ["verify", "render"],
  "fixture": "node-base",
  "request_from": "node-fix-bug",
  "options": {"delegation": "inline"},
  "seed_records": {"step-plan": {"criteria": ["..."], "steps": ["..."], "expectations": ["E1 works", "E2 broken", "E3 absent"], "...": "..."},
                   "test-spec": {"test_cases": ["..."]}},
  "planted": [
    {"id": "P1", "what": "src/strings.js makes capitalize('') throw (a falsy-text guard), so E1, a works expectation, does not match on the base", "signature": "PLANTED-E1"}
  ],
  "controls": [
    {"id": "C1", "what": "E2 (broken, reproduces) and E3 (absent, place free) match and are left alone: src/paginate.js is untouched and the regression test file is not created"},
    {"id": "C2", "what": "nothing outside E1's paths changes, and the item's own change (the paginate fix) is not started"}
  ],
  "render": [
    {"packet_issued": true, "why": "one expectation mismatches, so the engine does not settle the stage itself"},
    {"current_stage": "validate-existing"},
    {"proves": "P1", "packet_contains": "E1 works .*PLANTED-E1.*-> DOES NOT MATCH"},
    {"proves": "C1", "packet_contains": "E2 broken .*-> MATCHES"},
    {"proves": "C1", "packet_not_contains": "E[23] .*DOES NOT MATCH"},
    {"proves": "C2", "packet_contains": "Start none of the item's own change"}
  ],
  "oracle": [
    {"proves": "P1", "outcome": ["done"]},
    {"field": "failed_expectations", "exists": false, "why": "a done result names no mismatch"},
    {"proves": "P1", "command": "node -e \"process.exit(require('./src/strings').capitalize('')===''?0:1)\"", "exit": 0, "why": "E1's own check, as the step plan records it"},
    {"proves": "P1", "command": "node --test test/strings.test.js", "exit": 0, "why": "the fix keeps the file's other behaviour"},
    {"proves": "C1", "file": "src/paginate.js", "unchanged": true},
    {"proves": "C1", "file": "test/paginate-last-page.test.js", "exists": false},
    {"proves": "C2", "changed_only": ["src/strings.js"]}
  ]
}
```

(The file also holds a third `P1` command check and a `C2` command check that E2 still reproduces; they are left out
here.) Its `reference/` folder holds the output that makes every check pass and four outputs that each fail something:

| Folder | What it does | `meta.json` `fails` |
|---|---|---|
| `good` | Drops the falsy-text guard clause in `src/strings.js` and reports `done` | none |
| `bad-not-fixed` | Reads E1's mismatch, calls it irrelevant, reports `done` with the tree unchanged | `P1` |
| `bad-send-back` | Sends E1 back to the step plan though the fix is known and small | `P1` |
| `bad-wrong-file` | Bends `test/strings.test.js` to the fault; `src/strings.js` stays broken | `P1`, `C2` |
| `bad-started-item` | Fixes E1 and also starts the paginate fix and its test | `C1`, `C2` |

Between them the bad outputs fail every id, so the oracle is shown able to fail `P1`, `C1` and `C2`.

## The check vocabulary

A check is a dict with **one kind key**, an optional `proves` (a planted or control id) and an optional `why` (prose,
never read by the engine). The engine is `stage_suite/stage_oracle.py`; its docstring and test file are the full
contract.

| Kind | Form | Notes |
|---|---|---|
| `outcome` | `{"outcome": ["done", "send-back"]}` | The result's `outcome` is one of the list. |
| `field` | `{"field": "failed_expectations[*].route", "equals": "check"}` | A dotted path; `[*]` selects every element. Assertion keys: `equals`, `matches` (regex search of the string form), `exists`, `count`, `none_equal`. All selected values must satisfy unless `"any": true`. At least one value must be selected, except with `exists: false` or `count: 0`. |
| `file` | `{"file": "src/paginate.js", "exists": true}` | Exactly one assertion key: `exists` (true or false), `contains` (regex), `not_contains` (regex), `unchanged` (true, against the seed tree). The path must stay inside the tree. The last component is looked at as it is: `exists` is true for a link that dangles, and a file replaced by a link to the same bytes is changed. |
| `changed_only` | `{"changed_only": ["src/strings.js", "docs/**"]}` | Every file added, changed or removed against the seed tree matches a glob; `dir/**` is everything below `dir`. An empty list means nothing may differ. A change is different bytes, a flipped executable bit or a different link target; an empty folder, added or removed, is not one. A stage that keeps the knowledge home up to date may write `docs/shiploop/`, so allow `docs/shiploop/**` where the live checkout would hold it. |
| `command` | `{"command": "node --test", "exit": 0}` | `exit` is a status or `"nonzero"`; `"timeout"` overrides the 120 s default. Runs in a scratch copy of the tree (a symlink whose target leaves the copy is left out), stdin closed, a minimal environment (HOME and TMPDIR are scratch folders). A command that writes more than 16 MB is stopped and fails whatever exit was asked for. |
| `stand_in` | `{"stand_in": "stand_ins/empty", "command": "node --test", "kills": true}` | Overlays a weaker implementation (a folder relative to the scenario) over a copy of the candidate and requires the command to fail on it. With `kills: true` the command is run on the candidate first and must pass there: a command that already fails on the candidate kills every stand-in and shows nothing. |
| `trace` | `{"trace": "refusals_max", "value": 1}` | Reads the run's `trace.jsonl` rows; the refusals count. |
| packet checks | `{"packet_contains": re}`, `{"packet_not_contains": re}`, `{"packet_head_contains": re}` | The packet is the packet file's text; the head is what `shiploop next` printed. Regexes are searched with `re.MULTILINE`. |
| run state | `{"packet_issued": true\|false}`, `{"settled_by_script": true\|false}`, `{"current_stage": "implement"}` | Whether the engine issued a packet, recorded the stage done by script, and where the run stands afterwards. |

Rules the engine keeps:

- A check that cannot be evaluated **fails** with the reason; a missing input (no tree, no packet, no result) fails
  every check that needs it, `not_contains` and `exists: false` included. Absence of evidence is not evidence of
  absence.
- Commands run with `/bin/sh -c`; an exit of 126 or 127 never counts as "nonzero" (the shell could not run the command).
- **Verdict.** An id is *caught* (planted) or *held* (control) when at least one check proves it and every check that
  proves it passes. A check without `proves` must pass for the sample to pass. An id with no check in the list being run
  is *not exercised*, never a pass.

## Adding a scenario

1. Make `stage_cases/<stage>/<scenario>/` and write `scenario.json`. Start from a scenario of the same stage and run
   `stages.py list` to see it load.
2. Choose the fixture and `request_from`. Put the planted fault in `repo/` (it is committed in the baseline) and what
   earlier stages left in `worktree/`.
3. Write `seed_records` for the stages before yours. The builder records them through the engine, so the engine's
   validation tells you what is missing.
4. Give every planted condition a **signature** a script can see (a token, an id, an exit code, a path) and name each
   control. If the only way to tell caught from missed is to read prose, sharpen the scenario.
5. Write `render` checks for the packet and `oracle` checks for the output, each tied to an id with `proves`.
6. Write `reference/good`, and **a `reference/bad-<slug>` for every planted and control id**: an output that misses that
   planted condition or breaks that control, with `meta.json` listing exactly the ids it must make the oracle fail. A
   bad output with no `meta.json`, or an id no bad output fails, is a loader error. This is the rule that keeps the
   oracle honest: it is shown able to fail each id before any model is graded by it.
7. Run `stages.py verify <stage>/<scenario>` and `stages.py render <stage>/<scenario>`; both must pass. A failure no
   `meta.json` declared prints as a *surprise*: read it, then either fix the oracle or declare it.
8. A scenario that needs only one tier says so in `tiers` (`all-match` is render-only: the engine settles the stage
   itself, so there is no model output to grade).

## Running

```sh
python3 test/shiploop_e2e/stage_suite/stages.py list                          # every scenario, its tiers and counts
python3 test/shiploop_e2e/stage_suite/stages.py verify                        # all (T0)
python3 test/shiploop_e2e/stage_suite/stages.py render validate-existing      # one stage (T1)
python3 test/shiploop_e2e/stage_suite/stages.py render validate-existing/wrong-check --keep /tmp/built
python3 test/shiploop_e2e/stage_suite/stages.py verify @inner -validate-existing/all-match +catch   # an exclude must select something
python3 test/shiploop_e2e/stage_suite/stages.py verify --json
```

Run with `SHIPLOOP_PROGRESS=off` outside the hermetic runner: a printed packet otherwise starts a detached progress
observer. `render` builds real ShipLoop runs (about a second each) under a temporary folder removed afterwards; `--keep
DIR` leaves each built run under `DIR/<stage>/<scenario>`. `--cases-dir DIR` reads scenarios from another folder.

### Selectors

Selectors are a **union** of the includes, then the excludes are removed. No include means all.

| Selector | Selects |
|---|---|
| `all` | every scenario (the default) |
| `<stage>` | every scenario of one stage. `spec` never selects `improve@spec`. |
| `improve@<stage>` | the scenarios of an Improve stage |
| `<stage>/<scenario>` | one scenario |
| `@prelude`, `@inner`, `@outer`, `@improve` | every scenario of one phase (an `improve@` stage is phase `improve`) |
| `+<tag>` | every scenario carrying that tag |
| `-<selector>` | removes what the selector selects |

A selector that is not one of these, or that selects nothing, is a usage error naming it.

### Output and exit codes

A table with one row per scenario (tier, `PASS`, `FAIL` or `skipped: <reason>`, and each id *caught*, *held*, *missed* or
*not exercised*) and a total line; `--json` prints the same as one document. A scenario without the tier is skipped: it
counts in the total, not as a failure.

| Exit | Meaning |
|---|---|
| 0 | everything selected passed |
| 1 | something failed |
| 2 | a usage or schema error (the text is printed) |
| 3 | nothing selected |

## Why this lives in `stage_suite/` and `stage_cases/`

`test/shiploop_e2e/boundary.py` binds the evaluator digest and the qualification snapshot to `SPEC.md`, `cases.json`,
`suites.json`, **every top-level `*.py` and `*.cjs` file** in `test/shiploop_e2e/`, and the whole `checks/` and
`evaluators/` trees. Changing any of them moves the digest under the owner's baselines and calibrations, and promotion
compares attempts only across equal digests. So the stage suite adds nothing to that set:

- all its code is in the sub-folder `stage_suite/`, which `boundary.evaluator_files` does not read (it lists the top
  level only), as `probes/` is;
- all its scenario data is in `stage_cases/`;
- `run.py`, `slice.py`, `SPEC.md`, `cases.json` and `suites.json` are untouched, and `step_cases.json` is only read;
- its tests are outside the harness folder (`test/shiploop-e2e-stage-*.test.py`), and pin that the digest and the
  snapshot are the same with the stage suite present (`boundary.fingerprint` before and after, and the snapshot's file
  list holding no `stage_suite/` or `stage_cases/` path).

`README.md` files are not part of the digest either, so this file and the section in `../README.md` may change freely.

The consequences, each a choice and not an oversight:

- The builder reuses `run.seed_run` (workspace start, baseline commit, neutral knowledge home, item base) without editing
  `run.py`: it substitutes the module global `run.SEED_SCRIPT` with its own seed script for the one call, and restores it
  whatever happens. `run.SEED_SCRIPT` itself is as it was, and the harness's own seeds do not change.
- The seed script records each earlier stage through `navigator.accept_effects`, the engine's single function for what
  happens after a gate passes, so the script-owned effects of a stage run as they do in a real run. The packet a scenario
  renders is a packet a real run sees.
- Nothing here edits `slice.py`, so the stop at acceptance (`--stop-at accept`) and the widened seed points belong to
  the live runner in step 3, which will have its own poll in `stage_suite/` and import `slice.py` as a library.
