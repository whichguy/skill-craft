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
    stages.py         the command line: list | verify | render | live | grade | report, selectors, reports
    stage_live.py     one live sample: build, launch the host, stop at acceptance, export, grade, regrade
    stage_report.py   read a results root: the matrix of catch rates, and the comparison of two roots
  stage_cases/
    README.md         this file
    <stage>/<scenario>/   one scenario each
```

Tests: `test/shiploop-e2e-stage-oracle.test.py`, `test/shiploop-e2e-stage-build.test.py`,
`test/shiploop-e2e-stage-live.test.py`, `test/shiploop-e2e-stage-report.test.py` and `test/shiploop-e2e-stages.test.py`, one per
module, all hermetic (the live ones use a fake host, never a model).

## The three tiers

| Tier | Command | Model | Built | What it proves |
|---|---|---|---|---|
| verify (T0) | `stages.py verify` | no | yes | The scenario's `oracle` checks pass `reference/good` and fail every `reference/bad-*` on the ids that bad output declares, so the oracle can fail each planted condition and control. No ShipLoop run is started. |
| render (T1) | `stages.py render` | no | yes | A real run is built to the scenario's stage with the engine's own seed seam, `shiploop next` is run, and the `render` checks read the packet. A stage the engine settles by script (no packet) is checked as that. |
| live (T2) | `stages.py live` | yes (costs money) | yes | A model that follows only this packet has the intended effect, graded by the same `oracle` checks over N samples. |

`live` starts a real model for every sample (see "Live" below). It is a scenario's choice: only a scenario with
`live` in its `tiers` runs there (`all-match` is render-only; `broken-works-small-fix` and `wrong-check` have it).

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
per line, beside `result.json`) is removed from it; it must name a file or folder below the tree (not an absolute path, not a
path with `..`, and not `.`, which would be the tree itself).

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
| `live` | `{"samples": 3, "pass": "all"}`; the defaults. `samples` is how many times `stages.py live` repeats the scenario (`--samples` overrides it); `pass` is `"all"` or the number of samples that must pass. |

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
here.) Its `reference/` folder holds the output that makes every check pass and six outputs that each fail something:

| Folder | What it does | `meta.json` `fails` |
|---|---|---|
| `good` | Drops the falsy-text guard clause in `src/strings.js` and reports `done` | none |
| `bad-not-fixed` | Reads E1's mismatch, calls it irrelevant, reports `done` with the tree unchanged | `P1` |
| `bad-send-back` | Sends E1 back to the step plan though the fix is known and small | `P1` |
| `bad-wrong-file` | Bends `test/strings.test.js` to the fault; `src/strings.js` stays broken | `P1`, `C2` |
| `bad-started-item` | Fixes E1 and also starts the paginate fix and its test | `C1`, `C2` |
| `bad-collateral-edit` | Fixes E1 but rewrites `capitalize` on the way: the rest of the text is lower-cased, so the small fix is not small and the file's behaviour changed (E1's own check passes) | `P1` |
| `bad-guard-removed` | Fixes E1 by deleting the whole guard line of `capitalize`, not only the falsy-text clause: `capitalize('')` returns `''`, but the type check goes too (`capitalize(5)` now fails with a different error), so the fix is wider than E1 asks | `P1` |

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

## Live

**Costs money.** `stages.py live` starts a real model host for every sample and leaves it running until its packet is done:
tokens and minutes of host time, per scenario times `--samples`. It prints the plan with that warning and, with `--dry-run`,
prints it and does nothing else. **No real model round has been run at the time of writing**: the host this was built on had
none usable (Ollama down, Codex not signed in), so the tier is tested only with a fake host (`test/shiploop-e2e-stage-live.test.py`,
`-stage-report.test.py` and the CLI cases of `-stages.test.py`). Its first round, and the journal entry for it in
`../LEARNINGS.md`, are still to do (`docs/plans/shiploop-stage-suite.md`, Deviations).

### What a sample is

A model follows ONLY the one packet of a built scenario (`stage_build.build` seeds the run; the model's opening prompt is the
host's skill invocation with the harness's seed prompt for that stage). A script, never a model, grades what it did, with the
same `oracle` checks the verify tier uses. The sample is repeated, and a report shows the catch rates.

The host is ended as soon as the **seeded action is accepted with any outcome** (`done`, `send-back`, `blocked`, `add-work`), or
the run parks at that action's Improve stage (`active_improve.action_id` is the seeded action; the producer's result is then
`active_improve.seed_result`), or the run stops being active. It is polled every `run.POLL_SECONDS`. A host that ends by itself
earlier is resumed when its host can be, within the timeout. The stop is its own small drive in `stage_suite/stage_live.py` (on
`run.launch`), not `slice.py`'s, which takes no other stop predicate.

Everything the grade reads is kept in the sample folder, so a regrade needs no host and no ShipLoop: the seed tree
(`seed-export/`, taken after the build and before the host starts), the tree at the stop (`export/`), the run's `trace.jsonl`,
the seeded action's packet from `packet-archive/`, and the accepted result from the run state. Both trees hold tracked and
untracked non-ignored files, with no `.git` and no ShipLoop run evidence (`.shiploop-improve/`).

The stop waits for the command that accepted the action to finish (the run lock, `<run>/.lock`, free; `SETTLE_SECONDS` at most)
before it ends the host, so `export/` holds what the engine's own post-save effects wrote. What is waited for is the command's
dispatch: the save and `accept_effects`, post-save effects included. What is **not** waited for is what the command does after
it lets the lock go (its trace row, the start of the progress observer), and the host's group is ended right after the wait. A
host that is held up by a process it left in a session of its own is abandoned after the timeout plus `WATCHDOG_SECONDS` (which
exceeds `SETTLE_SECONDS`, because the wait runs past the deadline), or `STOP_GRACE_SECONDS` after the stop at acceptance or after
an operator's stop was first seen, so `--timeout` is a bound on the grade, though that process is left running. A sample an
operator ends (the `stop` file in its folder, SIGTERM or SIGHUP to the harness) is **not graded**, also when it arrives while the
stop is waiting for the accepting command: it measured nothing, nothing is exported, and the report counts it as not run. When the
host is done the sample ends what its ledger records and ShipLoop's detached progress observer, before it exports and grades.

**The two tiers' seed trees differ by the knowledge home.** The verify tier composes the seed tree from files (the fixture,
`repo/`, `worktree/`); a live sample's `seed-export/` is the execution checkout as `run.seed_run` left it, which also holds the
neutral knowledge home (`docs/shiploop/spec.md` and `environment.md`). A check that reads `docs/shiploop/` (a `changed_only` that
allows it, a `file` check on it) therefore cannot be verified by the verify tier alone: it can pass there and fail live, or the
reverse. Prefer checks that do not read it; one that must is proven by a live run, not by `verify` alone.

### Running

```sh
python3 test/shiploop_e2e/stage_suite/stages.py live validate-existing/wrong-check --dry-run   # the plan only
python3 test/shiploop_e2e/stage_suite/stages.py live validate-existing/wrong-check               # one scenario, the default driver, 3 samples
python3 test/shiploop_e2e/stage_suite/stages.py live validate-existing --samples 5 --jobs 3      # some: a stage, 5 samples, 3 at once
python3 test/shiploop_e2e/stage_suite/stages.py live --out /tmp/stages-1                          # all with the live tier on
python3 test/shiploop_e2e/stage_suite/stages.py live +catch --ref origin/main                     # a plugin built from a git ref
python3 test/shiploop_e2e/stage_suite/stages.py live validate-existing --overlay overlay.json     # a template-field overlay
bash test/run-integration.sh shiploop-stages validate-existing --samples 3                        # the same, through the optional runner
```

Selectors are the ones above. Only a scenario with `live` in its `tiers` runs; the others are named as "not live (tier off)".

| Option | Meaning |
|---|---|
| `--samples N` | Samples per scenario. Default: the scenario's `live.samples` (3). |
| `--jobs J` | Samples at once (default 1). Each is a separate **process** (the hidden `live-sample` subcommand), because the builder's substitution of `run.SEED_SCRIPT` is process-global; threads would share it. |
| `--host H --backend B --model M --effort E --host-bin PATH` | The driver. Defaults are `slice.py`'s: `hosts.RUN_DEFAULT_HOST` and the host's own backend, model and effort. |
| `--ref REF` | Build the plugin from a git ref (`overlay.build_ref`) instead of this checkout. The ref's navigator must have `accept_effects` (the seed seam, which the builder needs); a ref without it is refused before anything starts, naming the reason. |
| `--overlay FILE` | Apply a template-field overlay to the plugin (`overlay.apply_to_plugin`), as `experiment.py` does. |
| `--timeout S` | Seconds a sample's host may run before it is ended (default 3600). A finite positive number: `nan`, `inf` and `1e400` are refused (every sample is bounded). A sample that does not return within it plus a grace period (`SAMPLE_GRACE_SECONDS`) is killed and counts as not run. |
| `--out DIR` | The results root (a new folder). Default: a new `stages-live-<stamp>-<id>` folder under the harness's usual runs location. |
| `--dry-run` | Print the plan; build nothing, launch nothing, and do not look at the host. |
| `--cases-dir DIR`, `--json` | Scenarios from another folder; the plan or the outcome as one JSON document. |

`live` refuses before it creates anything when the host is not ready (the binary is not found, it is not signed in, Ollama does not
answer or lacks the model, or the ref lacks the seam): the message ends `Nothing was started.` and the exit is 2. It never reads or
prints a credential; the host classes of `hosts.py` own the environments. Run it with `SHIPLOOP_PROGRESS=off` outside the hermetic
runner.

### The sample folder

This lists what the runner writes (a host may add files of its own, such as its throwaway `home/`).

```
<root>/live-plan.json                       the plan: scenarios, samples, pass rule, planted and control ids, driver
<root>/.logs/                               the stdout and stderr of each sample's process
<root>/<stage>/<scenario>/<n>/              one sample (n from 1)
    .harness-lock                           the lock that says a harness is running the sample; `grade` refuses a folder whose lock is held
    stage-result.json                       the verdicts (rewritten by every regrade)
    invocation.json                         who ran what: host, model, effort, plugin identity, ref, overlay, the seeded block
    prompt.txt                              the request the packet follows
    host-prompt.txt  resume-N.txt           the prompt a host was started with, and the one it was resumed with the Nth time (hosts that take it from a file)
    seed-export/  export/                   the execution checkout before the host started, and when it was ended
    work/  .shiploop-runs/seed/{run,worktree}   the product repository, and the run and checkout the builder made
    .stage-suite/fixture/                   the fixture composed for the build
    build/                                  the plugin built from this checkout or from --ref (absent when a plugin folder is named)
    sessions.jsonl  events.jsonl  stderr.txt  timeline.jsonl  transcript.md  packet-archive/   the harness's own records
    resources.jsonl                         the ledger of the process groups the sample started and ended
    drive.json                              how the resume loop ended, and how long each stop waited for the accepting command
    error.txt                               only when the sample could not be run (or was ended by an operator): why; `grade` refuses such a folder
    export-error.txt                        only when the end export failed (every check that reads the tree then fails)
```

`grade` also refuses a folder that was not run to the end without an `error.txt` (no export, no `export-error.txt` and no
`stage-result.json`: a sample still running, or whose harness was killed).

`stage-result.json` holds: the scenario id and stage, the sample number, the host, backend, model, effort and delegation, the plugin
identity and versions, the ref and overlay, the `seeded` block and `action_id`, the session statuses, and

| Field | Meaning |
|---|---|
| `verdicts.process` | The stop ended the host: the last session's status is `stage-complete`, not a timeout, a failure or a crash. |
| `verdicts.accepted` | The seeded action was accepted, or the run parked at its Improve stage. |
| `verdicts.no_overshoot` | No result was accepted for a stage after the seeded one (`slice.overshoot_after`) and no history row follows the seeded action's own (a host that was sent back and redid an earlier stage overshoots too). |
| `verdicts.oracle` | The scenario's `oracle` checks passed: every planted id caught, every control held, nothing else failing. |
| `caught`, `held` | Per planted id and per control id. An id is caught or held only if the seeded action was accepted: a host that delivered nothing holds no control by doing nothing. |
| `checks` | Every check's result, kept as the oracle returned it. |
| `value` | The fraction (0 to 1) of planted and control ids caught or held: a per-sample number suitable for handing to `experiment.py decide` (no code reads `stage-result.json` today). |
| `pass` | Every verdict true and every id caught or held. |

### The pass rule

A sample passes when `pass` is true. A scenario meets its `live.pass` rule when the samples that passed number at least what the
rule asks of the samples that were planned: `"all"` is every sample, a number is that many. A sample that crashed, timed out or left
no whole `stage-result.json` is **not run**: it counts in the denominator and is never a pass. Exit codes: 0 every scenario met its
rule, 1 any did not, 2 usage or a host refusal, 3 nothing selected (or nothing with the live tier on); a signal to `live` ends
every running sample and its host and exits 128 plus the signal, and a second signal (SIGTERM, SIGHUP or SIGINT) while the first is
being answered kills the samples at once, ends their hosts from the ledgers and exits 128 plus that signal. `report` prints a root and exits 0 whatever it shows (its `rule`
column and `--json` carry the verdict; `live` is the command whose exit code says whether the rule was met), and 2 for a root it
cannot read or compare.

### Report, compare and grade

```sh
python3 test/shiploop_e2e/stage_suite/stages.py report /tmp/stages-1                       # the matrix, from the files
python3 test/shiploop_e2e/stage_suite/stages.py report /tmp/stages-1 --json
python3 test/shiploop_e2e/stage_suite/stages.py report /tmp/stages-2 --compare /tmp/stages-1
python3 test/shiploop_e2e/stage_suite/stages.py grade /tmp/stages-1/validate-existing/wrong-check/1   # regrade one sample
```

`report` prints a row per scenario: samples run, each planted id caught and each control held as `k/n` (n counts the samples not
run), `overshoot k/n`, `pass k/n`, whether the `live.pass` rule is met, and the driver (host, model, effort). A half-written or
missing sample is not run, never a pass (so is a result that checked no id, lacks an id the plan names, or has a `value` outside
0 to 1, and a sample folder whose name is not its number is listed as ignored). A root that mixes plugin builds, refs or overlays says
so under the matrix. `--compare EARLIER_ROOT` adds the change in each cell, **and refuses two roots whose drivers
(host, backend, model or effort) differ, naming both** (SPEC S-12: results of different drivers are different baselines). `grade`
rebuilds the oracle's bundle from the sample's files alone, reruns the checks (after a change to a scenario's `oracle`, say) and
rewrites `stage-result.json`; it exits 0 for a pass and 1 for a fail, and 2 for a folder it cannot grade.

Tests drive the whole command line with a fake host through a test-only route that is refused unless two environment switches are
set (the docstring of `stages.py`); nothing else may use it.

## Why this lives in `stage_suite/` and `stage_cases/`

`test/shiploop_e2e/boundary.py` binds the evaluator digest and the qualification snapshot to `SPEC.md`, `cases.json`,
`suites.json`, **every top-level `*.py` and `*.cjs` file** in `test/shiploop_e2e/`, and the whole `checks/`, `fixtures/` and
`evaluators/` trees. Changing any of them moves the digest under the owner's baselines and calibrations, and promotion
compares attempts only across equal digests. So the stage suite adds nothing to that set:

- all its code is in the sub-folder `stage_suite/`, which `boundary.evaluator_files` does not read (it lists the top
  level only), as `probes/` is;
- all its scenario data is in `stage_cases/`;
- `run.py`, `slice.py`, `SPEC.md`, `cases.json` and `suites.json` are untouched, and `step_cases.json` and the `fixtures/` tree
  are only read (a scenario's own files lay over a copy of its fixture, from `repo/`);
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
  the live runner (`stage_live.py`), which has its own poll in `stage_suite/` and imports `slice.py` as a library.
