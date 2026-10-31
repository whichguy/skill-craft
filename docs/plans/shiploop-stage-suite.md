# Plan: the ShipLoop stage suite (one packet, one scenario, one verdict)

Status: steps 1 to 3 of "Build order" are built (steps 1 and 2 on 2026-10-30, merged to `main` as PR #28, merge commit
`475ab9a6`, with the seam shipped in shiploop 1.23.3; step 3 on 2026-10-31, on branch `claude/shiploop-stage-suite-live` and
not yet merged); step 4 (the scenario waves) is not, and **no real live round has been run** (see deviation 9). The
prototype findings in "What the prototype showed" were run on `d98451f`. **The verify and render tiers run in the quick tier
only when a path under `test/shiploop_e2e/` changes, and in the full tier (the release); an edit to a packet source
(`skills/shiploop/scripts/shiploop_prompts.py`, the stage references) selects none of the stage suites in the quick tier. Whether to
wire them to the packet sources is the owner's open decision (deviation 5).** Step 3 is the live tier: `stages.py live | grade | report`,
the sample runner `stage_suite/stage_live.py` (build, launch a host, stop at acceptance, export, grade, regrade), the results
reader `stage_suite/stage_report.py` (the matrix of catch rates and the comparison of two roots), the `shiploop-stages` command
of `test/run-integration.sh`, and the `live` tier on `validate-existing/broken-works-small-fix` and `wrong-check`.

**Built**

- Step 1, the seed seam: `navigator.accept_effects` in `skills/shiploop/scripts/shiploop_navigator.py`, with its
  equivalence test `test/shiploop-seed-seam.test.py` (in PR #28, merged to `main` as `475ab9a6`, with step 2; released in
  shiploop 1.23.3). It is registered in the catalog.
- Step 2, the harness core, in `test/shiploop_e2e/stage_suite/`:
  - `stage_oracle.py`, the check engine: the check kinds of "The oracle" except `trace: no_model_glue`, and the verdict
    rule (caught, held, not exercised);
  - `stage_build.py`, the scenario schema and loader, composition of the seed tree, the seam-based build and the render;
  - `stages.py`, the command line `list | verify | render` with the selectors and `--json`, `--keep`, `--cases-dir`.
- Three scenarios in `test/shiploop_e2e/stage_cases/validate-existing/`: `broken-works-small-fix`, `wrong-check` (both
  verify and render) and `all-match` (render only). `stage_cases/README.md` is the guide to the format.
- Hermetic tests, one per module, registered in `test/suite_catalog.py` as E2E-family suites that quick selects when a
  path under `test/shiploop_e2e/` changes: `test/shiploop-e2e-stage-oracle.test.py` (108 tests, about 5 s),
  `test/shiploop-e2e-stage-build.test.py` (48 tests, about 10 s) and `test/shiploop-e2e-stages.test.py` (117 tests, about
  100 s, step 3's cases included).

- Step 3, the live tier, in `test/shiploop_e2e/stage_suite/`:
  - `stage_live.py`: one sample. It builds the scenario (`stage_build.build`; a `--ref` whose navigator lacks
    `accept_effects` is refused first), snapshots the execution checkout as the seed tree, launches the host on
    `run.launch` with its own drive that **stops at acceptance** (`accepted_reached`: the seeded action accepted with any
    outcome, or the run parked at its Improve stage, or the run no longer active), exports the checkout, and grades from files
    (`collect_bundle`, `grade_sample`) with the oracle the verify tier uses. `stage-result.json` holds the verdicts (`process`,
    `accepted`, `no_overshoot`, `oracle`), `caught` and `held` per id, `value` (the fraction of ids caught or held: a per-sample
    number suitable for handing to `experiment.py decide`; no code reads `stage-result.json` today) and `pass`;
  - `stage_report.py`: the matrix per scenario (caught and held `k/n`, overshoot, pass, driver) and `compare`, which refuses
    two roots whose drivers differ (SPEC S-12); a missing or half-written sample is not run, never a pass;
  - `stages.py live | grade | report` (and the hidden `live-sample`): `live` selects, prints the plan and the cost warning,
    refuses before launching when the host is not ready, and runs each sample as a subprocess, `--jobs` at once; `--dry-run`
    builds and launches nothing;
  - `bash test/run-integration.sh shiploop-stages ...` runs `stages.py live`;
  - hermetic tests with a fake host, never a model: `test/shiploop-e2e-stage-live.test.py` (83 tests, about 90 s),
    `test/shiploop-e2e-stage-report.test.py` (45 tests, under 1 s), and the live and report cases added to
    `test/shiploop-e2e-stages.test.py`; registered in `test/suite_catalog.py` like the three before them.

**Not built**: building `improve@<stage>` and outer-stage scenarios (they load and validate); the per-scenario `oracle.py`
escape hatch and the `trace: no_model_glue` check; `worktree_mode: committed` (validated, refused by the builder); the scenario
catalog beyond the three above (waves 1 to 4); and a real live round (deviation 9).

### Deviations from this plan

1. **Location.** The code is `test/shiploop_e2e/stage_suite/` (not `test/shiploop_e2e/stages.py`) and the scenarios are
   `test/shiploop_e2e/stage_cases/`. `test/shiploop_e2e/boundary.py` binds the evaluator digest and the qualification
   snapshot to `SPEC.md`, `cases.json`, `suites.json`, every top-level `*.py` and `*.cjs` file of that folder and the
   `checks/`, `fixtures/` and `evaluators/` trees, so a new top-level module would move the digest under the owner's baselines and
   calibrations. A sub-folder is outside that set, as `probes/` is. The tests pin it (`boundary.fingerprint` and the
   snapshot's file list are unchanged with the suite present), the way `test/shiploop-e2e-sdlc-probes.test.py` pins the
   probes. This is a variant of "Decisions for the owner" 1: inside the harness folder, as recommended, but below its top
   level.
2. **`slice.py` and `run.py` are not edited, so the live runner has its own stop-at-acceptance drive.** "Stop at acceptance"
   put `--stop-at accept` in `slice.py`. It is instead `drive` in `stage_suite/stage_live.py`, written on `run.launch` with the
   same session records (`sessionlog`), resume loop and timeout handling as `slice.drive`, which cannot take another stop
   predicate. `slice.py` is imported as a library only (`overshoot_after`). A later, separately evidenced change to `slice.py`
   should give its drive a stop predicate and a shared exporter, so that the two drives and the two exporters become one; until
   then `drive` and `snapshot` in `stage_live.py` are the stage suite's own.
3. **The builder reuses `run.seed_run` without editing it.** It substitutes the module global `run.SEED_SCRIPT` for the
   duration of one call, with a context manager that restores it, because `seed_run` reads that global when it advances
   the run. The seed script it substitutes records each stage through `navigator.accept_effects`. `run.SEED_SCRIPT` and the
   harness's own seeds are as they were.
4. **The equivalence test and the seam were committed first on the branch** (PR #28, merged to `main` as `475ab9a6`; the seam
   shipped in shiploop 1.23.3), ahead of the harness core (the plan shipped them together under "The one engine change").
5. **Registration.** "Registration" named two catalog suites (`shiploop-stage-verify`, `shiploop-stage-render`) and one
   test file (`test/shiploop-stage-suite.test.py`). The tests are one file per module instead (three suites, ids
   `shiploop-e2e-stage-oracle`, `shiploop-e2e-stage-build` and `shiploop-e2e-stages`), named after the harness family so
   an edit under `test/shiploop_e2e/` selects them with the rest. They test the code, and the stages suite also runs `stages.py verify` and
   `render` over the shipped scenarios (the class `Shipped`, about 5 s), so a packet change that breaks a scenario fails the
   `shiploop-e2e-stages` suite *when that suite runs*. It runs in the quick tier only when a path under `test/shiploop_e2e/`
   changes (or the suite's own files), and in the full tier (the release). An edit to a packet source
   (`skills/shiploop/scripts/shiploop_prompts.py`, the stage references) selects none of the stage suites in the quick tier, so
   until the full tier at a release a template regression that a scenario would catch is not seen. It is not a separate
   `shiploop-stage-*` catalog entry either. **Open decision for the owner:** add the stage suites to the packet-source rows of
   `_PATH_SUITE_IDS` in `test/suite_catalog.py`, so a packet-source edit selects them in the quick tier; the audit of this branch
   measured about 36.5 s of quick-tier time on a harness edit. `suite_catalog.py` is not changed. None is in the fixed quick
   baseline. Step 3 adds two more of the same kind (`shiploop-e2e-stage-live`, `shiploop-e2e-stage-report`), measured at 54 s
   and 0.1 s and also outside the quick baseline.
6. **The widened `SEED_POINTS` were not needed.** The live runner seeds through `stage_build.build`, which already seeds a run
   to any stage of a scenario with `accept_effects`; `slice.py`'s `SEED_POINTS` is not used by the stage suite and is unchanged.
7. **Samples run as subprocesses.** `stage_build.build` substitutes `run.SEED_SCRIPT` in-process, which is process-global, so
   samples that run at once (`--jobs`) are separate processes (the hidden `live-sample` command), never threads.
8. **A test-only fake-host route.** `live` and `live-sample` can run a fake host in place of a model, but only when both
   `STAGE_SUITE_FAKE_HOST` and `STAGE_SUITE_TEST_ONLY=hermetic-test-no-model` are set; the plan names it loudly. It is how the
   tests drive the whole command line with no model and no network. It is not how `test/shiploop-e2e-slice.test.py` fakes a
   host (that test puts a fake `claude` binary on `--claude-bin`, and so exercises the real host class's `argv` and `translator`).
   The route replaces the host class itself, so the command-line cases never run `ClaudeHost.argv` or its stream translator; those
   are covered by the sample-level tests (`shiploop-e2e-stage-live`), which pass a Host-like object to `run_sample`, and by the host
   classes' own suites.
9. **No real live round was run, and the exit of step 3 is not met.** "Build order" step 3 ends with one live round of the three
   `validate-existing` scenarios (3 samples) that "proves the pipeline end to end", journaled in
   `test/shiploop_e2e/LEARNINGS.md`. The session that built the tier had no usable model host (Ollama was down, Codex was not
   signed in), and a live round costs money, so everything is proven with fake hosts only. `all-match` is render-only (the
   engine settles that stage by script), so the round covers two of the three scenarios. **To run the first round the owner
   must:** have a signed-in host (the default driver, or `--host`, `--backend`, `--model`, `--effort`), then run
   `python3 test/shiploop_e2e/stage_suite/stages.py live validate-existing --samples 3 --jobs 3` (or
   `bash test/run-integration.sh shiploop-stages validate-existing`), read it with `stages.py report <root>`, and write the
   round's entry in `test/shiploop_e2e/LEARNINGS.md`. This change does **not** write that entry. Until it exists, the live
   tier's pipeline is shown only against a fake host, and its catch rates are unmeasured.

## Goal

Prove that each ShipLoop stage's packet, applied to a scenario with planted conditions, has the effect it is meant
to have. A model that follows that one packet must:

- catch the planted conditions the stage exists to catch;
- leave the controls alone: invent no problem that is not there and change nothing outside the stage's remit.

You can run any selection: one scenario, one stage, a phase, a tag, or every packet ShipLoop issues (23 producer
stages plus the Improve stage).

## What already exists, and the gap

| Piece | What it gives us | What it lacks for this goal |
|---|---|---|
| `run.seed_run` + `SEED_SCRIPT` (`test/shiploop_e2e/run.py`) | Records synthetic results up to a stage, merging `seed_records` | Uses the pure `nav.apply`, so the engine's script-owned **entry effects** never run (see the prototype) |
| `slice.py` | Live host, poll every 2 s, packet archive, `--seed-at`, `--stop-after`, `--ref`, `--overlay` | Seed points are limited to `test-strategy`, `step-plan` and `test-spec`. `--stop-after` waits through the Improve child and counts only `done` |
| `experiment.py` + `evaluators/` | Script evaluators with `score` and `verify`; A/B arms; A/A-spread `decide` | Each evaluator belongs to one experiment, and the format is a claim about a template edit, not a regression suite. `e2`/`e3` verify against a run on one machine (`/Users/dadleet/...`), so they are not hermetic |
| `seeded_defects.py` | Naive and fixed reference trees prove that a probe tells them apart | Covers only the Improve-at-document effect |
| `packets.py --offline`, `obligations.py`, `graph-dry-run` | Generic packet obligations rendered with no model | No scenario data: they cannot check that this scenario's planted fact reached the packet |
| `hosts.py` | The driver is a parameter | Nothing; reuse it as is |

The suite adds the missing pieces: a seed for any stage, a stop at acceptance, a scenario format with planted
conditions and controls, a declarative oracle, and a runner with selectors. It reuses everything else.

## What the prototype showed (2026-10-30, no model)

Scratch prototype: seed `node-base` (`node-fix-bug`) with a step plan whose `works` expectation `E1` is planted to
fail, then run `shiploop next`.

1. **Through today's seed**, the validate-existing packet says "ShipLoop ran each expectation's check … results are
   below", but **no results follow**: the planted `E1` never reaches the packet. The checks run in
   `_validate_existing_entry`, which `navigator._transition` calls from `complete`, and the seed bypasses it. A
   stage test built on today's seed would test a packet no real run ever sees.
2. **Seeding through `navigator._transition`** after each synthetic `apply` fixes this. The packet then carries
   `E1 works PLANTED-E1 … -> DOES NOT MATCH, exit 1`. With that change, seeds to `implement`, `test` and
   `carry-forward` render their packets.
3. **Seeding to `document`** still fails: `step W1/S1 has no iteration record (its run has no commit to start
   from)`. Besides `_transition`, `complete` runs post-save effects (`_lint_finish`, `_skill_commit`,
   `_knowledge_close`, `_iteration_entry`), and a seed needs those too. It also needs the implement-stage tree laid
   into the worktree.
4. **Cost**: seed plus render takes about 1.0–1.3 s per scenario. Sixty scenarios fit in the quick tier.
5. The real navigator validates seed records (expectation `state` values, the exact `test_cases` keys). A scenario
   that drifts from the engine's contract therefore fails loudly at seed time. That is what we want.

## Design

### Three tiers

| Tier | Command | Model? | Where it runs | What it proves |
|---|---|---|---|---|
| **T0 verify** | `stages.py verify` | no | quick tier when a path under `test/shiploop_e2e/` changes, and the full tier (release); see deviation 5 | The scenario's oracle passes its `good` reference output and fails each `bad` one, so the oracle measures the planted condition (the SPEC triage rule: "does it pass a reference solution and fail an empty one?") |
| **T1 render** | `stages.py render` | no | the same as T0 | The template, applied to this scenario, puts the planted signal and the right instructions in the packet (printed head or packet file), or issues no packet where the engine should settle the stage itself |
| **T2 live** | `stages.py live` | yes | `test/run-integration.sh shiploop-stages` only | A model that follows only this packet in the scenario folder has the intended effect. Graded by the same oracle as T0, over N samples |

T0 and T1 are cheap and need no model. As built they run in the quick tier only when a path under `test/shiploop_e2e/` changes,
and in the full tier at a release, so they catch a template regression at the release unless the owner wires them to the
packet sources (deviation 5). T2 is the behavioural proof, and it costs money.

### A scenario is a directory; the run is built on the fly

```
test/shiploop_e2e/stage_cases/
  README.md
  validate-existing/
    broken-works-small-fix/
      scenario.json          # stage, fixture, request, seed records, planted conditions, controls, render + oracle checks
      repo/                  # laid over the fixture BEFORE the baseline commit (the planted fault lives here)
      worktree/              # optional: laid into the execution checkout at the seed point (what earlier stages left)
      notes/                 # optional: RUN/notes files earlier stages would have written
      reference/
        good/                # result.json + tree/ : a correct stage output; the oracle must pass it
        bad-touched-item/    # each bad/ misses one planted condition or breaks one control; the oracle must fail it
        bad-weakened-check/
      oracle.py              # optional: score()/verify() for what the declarative checks cannot say
    wrong-check/ …
    all-match/ …             # T1-only control: the engine must settle the stage with no packet
  test-spec/ …
  improve@spec/ …            # an Improve stage reviewing a planted, flawed producer result
```

The source of a scenario is committed. **Its run state is never committed.** ShipLoop refuses saved runs from older
state versions, so a committed `state.md` would stop loading at the next state-version bump. The builder therefore
generates every run with the engine under test:

1. Copy `fixtures/<fixture>/` and lay `repo/` over it, then commit the baseline (as `seed_run` does today).
2. Run `workspace start` with the scenario's options (`--delegation`, `--planning-review`, `--lint`).
3. Seed to the stage through the engine seam below, merging `seed_records` into each synthetic result.
4. At the seed point, lay `worktree/` into the execution checkout, either committed as an earlier accepted step or
   left uncommitted the way implement leaves it (`worktree_mode: committed|uncommitted`). Then lay `notes/` into
   `RUN/notes/`.
5. For `improve@<stage>`, submit the scenario's planted producer result through the same seam, which parks the run at
   that stage's Improve action.

One builder serves all three tiers. T0 needs no build; it reads only `reference/`.

### The one engine change: a seed seam shared with `complete`

Extract the after-gate half of `complete` into one navigator function, say
`navigator.accept_effects(core, root, before, after)`. It holds `_transition`, the save, and the post-save hooks
(`_lint_finish`, `_skill_commit`, `_knowledge_close`, `_iteration_entry`). Then:

- `complete` calls it after its gates, with no behaviour change;
- the harness seed calls it after `nav.apply` in place of today's hand-rolled `lint.capture_base`. The seed skips the
  gates (its results are synthetic) but never the effects.

This keeps one implementation of each mechanism (S-12). Without it, the harness would grow a second copy of the engine's
entry logic that drifts. Ship it with:

- a hermetic equivalence test: for each stage with no gate on a synthetic result, a real `complete` and the seam give
  the same state and writes;
- a change note in `changes/shiploop/` (`bump: patch`);
- the `No-E2E-Round:` trailer (a refactor that leaves `complete`'s effects unchanged, proven by the equivalence
  test), or an E2E round recorded after it, because the release preflight asks for one on any `skills/shiploop/`
  change.

Rejected alternative: seed by submitting synthetic result files through the real CLI. Gates at `implement` and
`test` (Until Loop receipts, base runs) refuse synthetic results, and faking those would put the harness inside the
gates.

### Stop at acceptance

`slice.py` gains `--stop-at accept`, beside today's `--stop-after` (which also waits for the Improve child). It stops
the host as soon as either of these holds:

- the seeded action has an accepted row in `history`, with **any** outcome (many scenarios expect `send-back` or
  `blocked`, not `done`);
- `active_improve.action_id` is the seeded action. The producer's result is then in `active_improve.seed_result`.

The stop waits for the accepting command to finish first (built: `stage_live.settle`). `accept_effects` saves the state and
only then runs the lint finish, the two commits, the knowledge close and the iteration record, all under the run lock; the
poll can land between the save and the end of those, and ending the host there would leave the exported tree without effects
the engine would have produced (or with half of them). So once the stop holds, the sample waits (at most `SETTLE_SECONDS`) for the
run lock (`<run>/.lock`) to be free, and the grade's tree is the one after the effects. What is waited for is the command's
dispatch (the save and `accept_effects`, post-save effects included); what is not is anything the command does after it lets the
lock go (its trace row, the start of the progress observer), and the host's group is ended right after the wait. An operator's
stop (SIGTERM, SIGHUP, the stop file) that arrives during the wait leaves the sample not run, with nothing exported or graded. `no_overshoot` also counts any history
row after the seeded action's own row (a host sent back that redoes an earlier stage), not only a later stage.

`SEED_POINTS` widens to every stage plus `improve@<stage>`. The `no_overshoot` verdict stays: a model that has already
started the next packet when the 2 s poll fires is recorded, and the oracle reads only the seeded action's output.

### The oracle: declarative, script-only, tied to planted IDs

Each planted condition (`P1`, `P2`, …) and each control (`C1`, …) has a **detectable signature**: a unique token, an
ID, an exit code or a path. A script can then tell caught from missed. An oracle that has to read loose prose is a
sign the scenario needs a sharper signature.

The oracle reads one **stage output bundle**:

- `result`: the accepted result, or the parked `seed_result`;
- `tree`: the worktree diff from the seed point;
- `knowledge`: `docs/shiploop/*`;
- `notes`: `RUN/notes/*`;
- `records`: `RUN/expectations`, `tests`, `loops`;
- `trace`: refusals and keepalive rows from `trace.jsonl`;
- `transcript`: what the host showed. Record only, never a verdict.

Check kinds (one engine, `stage_oracle.py`):

| Kind | Example |
|---|---|
| `outcome` | `{"outcome": ["send-back"]}` |
| `field` | `{"field": "failed_expectations[*].route", "equals": "check"}`; `{"field": "work_items[*].title", "matches": "PLANTED-FOLLOWUP"}` |
| `file` | `exists`, `absent`, `contains`, `not_contains` (regex), `unchanged` since the seed |
| `changed_only` | `["src/strings.js"]`: no file outside these changed |
| `command` | Run in a clean export of the worktree; `exit: 0` or `exit: "nonzero"` (the `seeded_defects` probe style) |
| `stand_in` | Swap a weaker implementation into the tree; the stage's tests must fail it (reuse the E1 stand-ins) |
| `trace` | `refusals_max`, `no_model_glue` |
| `packet_contains`, `packet_not_contains`, `packet_head_contains`, `packet_issued: false` | T1 checks on the rendered packet |

Every check names what it `proves`. A sample **catches** `P1` when every check proving `P1` passes, and **holds**
`C1` the same way. A sample **passes** when it catches every planted condition, holds every control and does not
overshoot.

`oracle.py` is the escape hatch, with the `score(sample)` and `verify()` contract of `evaluators/common.py`. The
existing experiment evaluators (`e1_stand_ins`, `e2_layers`, `e4_base_state`, `e6_step_size`) and
`seeded_defects` plug in as scenario oracles, so their cases become stage-suite scenarios without being rewritten.

**No model judges a verdict.** An LLM rubric (`judge.py`) may score prose quality as a record beside the verdict,
never as the verdict, as `evaluators/common.py` already rules.

### Example `scenario.json`

```json
{
  "stage": "validate-existing",
  "about": "A works expectation the step relies on is broken on the base by a small, known fault outside the item's change.",
  "tags": ["catch", "prep-fix"],
  "fixture": "node-base",
  "request_from": "node-fix-bug",
  "options": {"delegation": "inline"},
  "seed_records": {
    "step-plan": {"expectations": [
      {"id": "E1", "state": "works", "statement": "PLANTED-E1: capitalize('') returns ''", "steps": ["S1"],
       "paths": ["src/strings.js"], "check": "node -e \"process.exit(require('./src/strings').capitalize('')===''?0:1)\""},
      {"id": "E2", "state": "broken", "statement": "paginate([1,2,3,4,5],3,2) loses the last page", "steps": ["S1"],
       "paths": ["src/paginate.js"], "check": "node -e \"…exits 0 while the bug reproduces…\""}],
      "…": "criteria, steps, test_commands, paths, follows as the engine requires"},
    "test-spec": {"test_cases": ["…"]}
  },
  "planted": [{"id": "P1", "what": "repo/src/strings.js makes capitalize('') throw: E1 does not match", "signature": "PLANTED-E1"}],
  "controls": [
    {"id": "C1", "what": "E2 matches its broken state and is left alone"},
    {"id": "C2", "what": "nothing outside E1's paths changes; the item's own fix is not started"}
  ],
  "render": [
    {"proves": "P1", "packet_contains": "E1 works .*DOES NOT MATCH"},
    {"proves": "C1", "packet_not_contains": "E2 broken .*DOES NOT MATCH"}
  ],
  "oracle": [
    {"proves": "P1", "outcome": ["done"]},
    {"proves": "P1", "command": "node -e \"process.exit(require('./src/strings').capitalize('')===''?0:1)\"", "exit": 0},
    {"proves": "C1", "file": "src/paginate.js", "unchanged": true},
    {"proves": "C2", "changed_only": ["src/strings.js"]}
  ],
  "live": {"samples": 3, "pass": "all"}
}
```

### Runner and selectors

`test/shiploop_e2e/stages.py`:

```sh
stages.py list   [SELECTOR…]                     # scenarios, their tags, and which tiers each supports
stages.py verify [SELECTOR…]                     # T0: oracle vs reference/good and reference/bad-*
stages.py render [SELECTOR…] [--keep DIR]        # T1: build, seed, `next`, packet checks; --keep leaves the built folders
stages.py live   [SELECTOR…] [--samples N] [--jobs J] [--host H --model M --effort E] [--ref REF] [--overlay FILE]
stages.py grade  OUTPUT                          # regrade one live sample from its files
stages.py report OUT_ROOT [--compare EARLIER_ROOT]
```

| Selector | Selects |
|---|---|
| `validate-existing` | every scenario of one stage |
| `validate-existing/wrong-check` | one scenario |
| `@prelude`, `@inner`, `@outer`, `@improve` | every scenario of one phase |
| `+catch`, `+control` | every scenario with that tag |
| `all` (the default) | every scenario |

Selectors combine as a union, and `-SELECTOR` removes from the selection: `stages.py live @inner -implement`.

Live output is one folder per sample: `<out>/<stage>/<scenario>/<n>/`, holding the slice output, `stage-result.json`
and the archived packet. The report is one matrix:

```
stage              scenario                 P1    P2    C1    C2    overshoot  pass  driver
validate-existing  broken-works-small-fix   3/3   -     3/3   3/3   0/3        3/3   codex/terra/xhigh
validate-existing  wrong-check              2/3   -     3/3   -     0/3        2/3   codex/terra/xhigh
test-spec          stand-in-oracles         4/4   3/4   4/4   -     0/4        3/4   codex/terra/xhigh
```

`--compare` reads an earlier root. Two roots are compared only when they ran on the same host, model and effort
(S-12). `--ref` and `--overlay` run the same scenarios against a template edit before it is committed. To decide
between two such arms, the per-sample `value` is a number suitable for handing to `experiment.py decide`, which keeps the A/A-spread
rule in one place, rather than reimplementing it (no code reads `stage-result.json` today).

### Registration

- **`test/suite_catalog.py`**: add `shiploop-stage-verify` and `shiploop-stage-render` (hermetic, `quick`; about 1–2
  minutes at 60 scenarios; shard with the other ShipLoop suites if needed).
- **`test/shiploop-stage-suite.test.py`** (hermetic):
  - schema validation of every `scenario.json`;
  - selector parsing;
  - `--stop-at accept` against the fake host that `shiploop-e2e-slice.test.py` already uses (a send-back, a
    park at Improve, and an overshoot);
  - oracle check kinds on synthetic bundles.
- **`test/run-integration.sh`**: add a `shiploop-stages` command that runs `stages.py live "$@"`. Never in default CI.

## Scenario catalog

Each row lists the planted conditions (P) and controls (C) the stage must catch or hold. "Reuse" marks an existing
case or evaluator that becomes a scenario.

### Wave 1: inner loop (the most-used packets, with seeding verified above)

| Stage | Scenario | Planted / controls | Oracle sketch |
|---|---|---|---|
| step-plan | `existing-and-new-paths` | P1: the change touches existing `src/paginate.js` and a new file. P2: the request reports a reproducible failure. C1: no step changes only test files | `expectations` has works/broken for the existing path and absent for the new one; a `broken` expectation whose check reproduces the report; focused, regression and check commands recorded; refusals ≤ 1 |
| step-plan | `step-size` (reuse E6) | the existing evaluator | `e6_step_size` |
| test-spec | `stand-in-oracles` (reuse E1/E1b) | P: weak oracles that the empty or lenient stand-ins survive | `e1_stand_ins`, carried to test |
| test-spec | `behavioural-red` | P1: a criterion whose naive RED is "the file is missing". C1: every criterion has a case | no `red` matches `does not exist`/`not found`/`cannot find module`; every criterion id covered |
| validate-existing | `broken-works-small-fix` | above | above |
| validate-existing | `wrong-check` | P1: the fact holds but the check has a wrong path. C1: no edits | `send-back`; `failed_expectations[E1].route == check`; `actual` names the corrected check; tree unchanged |
| validate-existing | `absent-occupied` | P1: an `absent` path already exists | `send-back`, route `steps` |
| validate-existing | `all-match` (T1 only) | C1: every check matches | `packet_issued: false`; stage recorded done by script |
| implement | `step-scope` | P1: S1's proof fails on the base. C1: S2 (`formatPage`) must not be built yet | S1's proof exits 0; `formatPage` absent; `not_covered` present |
| implement | `stateful-target` (reuse E4) | the existing evaluator | `e4_base_state` |
| test | `ids-and-red` | P1: quoted TC-1 and TC-2. P2: the worktree implementation has a subtle bug that only TC-2 catches. C1: tests are not bent to pass | TC ids in test names; focused command runs them; outcome `send-back`, or a code fix with TC-2's assertion unchanged; the empty stand-in fails the tests |
| document | `public-behaviour-change` | P1: the worktree holds an uncommitted `GET /health`, and the README lists the routes. C1: docs only | README mentions `/health`; `knowledge` names each living file; `changed_only: README.md, docs/**` |
| document | `internal-only` | C1: a private refactor, so no public doc changes | no-change reason in `RUN/notes/<action>.md`; README unchanged |
| carry-forward | `leftover-followup` | P1: a seeded note records `PLANTED-FOLLOWUP`. P2: a learning sits in run notes | the queue has an item for it; the learning moved into `docs/shiploop/`; a `skill` decision is recorded |

### Wave 2: prelude and Improve

| Stage | Scenario | Planted / controls | Oracle sketch |
|---|---|---|---|
| intake | `ambiguous-export` | P1: "export the ledger" with no format. P2: a boundary, "the v1 API is frozen". C1: no invented auth requirement | the summary has an open question on format, with an owner; the boundary is recorded; no `auth` |
| discovery | `red-baseline` | P1: one existing test fails on the base (`PLANTED baseline red`). C1: discovery fixes nothing | evidence holds the command, a nonzero exit and the test name; `environment.md` has `node --test`; tree unchanged outside `docs/shiploop/` |
| discovery | `no-tests` | P1: a repo with no tests | recorded as missing coverage |
| research | `doc-constraint` | P1: `docs/vendor-api.md` sets a 900 s token TTL that the request depends on | `RUN/notes/research.md` cites `900` and the locator |
| research | `access-need` | P1: the request needs an account nobody has granted | an open item names who grants it and the gate it blocks |
| spec | `outcomes-and-nfr` | P1–P3: three outcomes, one non-functional (≤ 200 ms). C1: existing R-1..R-3 preserved | an acceptance line per outcome; the NFR assessed; R-1..R-3 text byte-identical |
| test-strategy | `ui-no-browser` (reuse E2) | the existing evaluator | `e2_layers` (re-based on committed reference records, not run 4's path) |
| plan | `hidden-dependency` | P1: R-2's route needs R-1's store method | work items in dependency order; every criterion owned |
| prepare | `uninstalled-local-dep` | P1: the tests need a `file:` dependency that is not installed | the runner exits 0 after the stage; readiness in `environment.md` |
| improve@spec | `missing-outcome` | P1: the planted spec result drops the request's "CSV export" outcome | after Improve, `spec.md` has an acceptance line for it |
| improve@document | `seeded-defects` (reuse `node-seeded-*`) | the existing probes | `seeded_defects.score` |

### Wave 3: outer stages (built on the release-slice materials: `seed_product`, `seed_home`)

| Stage | Scenario | Planted |
|---|---|---|
| system-test-author | `uncovered-system-criterion` | a system-level criterion with no test, so a test or a planned check with its due stage appears |
| system-test | `fails-on-candidate` | the built product fails one system test, so `send-back` or `add-work` names it |
| product-acceptance | `unmet-outcome` | the product omits one request outcome, so `add-work` or `unverified` lists it |
| release-plan | `no-authority` / `standing-grant` | no grant means blocked or awaiting authority; a recorded grant means a plan with rollback |
| release-check | `confirm-not-there-yet` | confirm commands record their not-there-yet output |
| release / release-verify | `local-target` | release to a local target (`fixtures/local-target`); the released identity is recorded and observed |
| operations, handoff | `uncommitted-leftovers` | the handoff reports the workspace return and the open items |

### Wave 4: generality

Re-run the waves' strongest scenarios on a second stack, a small Python fixture. The harness rule is to probe more
than one kind of software, and a stage that passes only on Node is not shown to be technology-agnostic (S-8).

## Build order

1. **Seed seam** (engine) and its equivalence test, plus the change note.
2. **Harness core**: the scenario loader and schema, the builder (on the seam), `--stop-at accept`, widened seed points,
   `stage_oracle.py`, and `stages.py list|verify|render`. Convert the prototype into
   `validate-existing/broken-works-small-fix`, `wrong-check` and `all-match`. Register T0 and T1 in the catalog.
   Exit: green in quick.
3. **`stages.py live|grade|report`** on the slice launcher. One live round of the three validate-existing scenarios
   (3 samples) proves the pipeline end to end. Journal it in `test/shiploop_e2e/LEARNINGS.md`.
4. **Wave 1**, then **2**, **3** and **4**. Each scenario lands with its `reference/good` and at least one
   `reference/bad`, and T0 must be green before its first live run.

## Decisions for the owner

These set direction. As first written they were recommendations for the owner under AGENTS.md. In the event the building
session took each as a routine decision under AGENTS.md ("a session makes routine decisions itself and records each one"), as
recorded below, and the owner merged PRs #24 (this plan) and #28 (the seam and the harness core), which contain them. The owner
did not approve them one by one; they stay changeable on request.

1. **Location.** I recommend `test/shiploop_e2e/stage_cases/` and `stages.py`, inside the E2E harness, to reuse its
   hosts, slice launcher and evaluators. The alternative is a new top-level `test/shiploop_stages/`.
   *How it was settled:* the code is in `test/shiploop_e2e/stage_suite/` and the scenarios in `test/shiploop_e2e/stage_cases/`,
   because a new top-level module of the harness folder would move the evaluator digest (deviation 1). It is the recommended
   option with one more level of folder.
2. **The engine seam** in `skills/shiploop/scripts/shiploop_navigator.py`: a product-code refactor, which the plan proposed
   to ship in the next release with a `No-E2E-Round` trailer.
   *How it was settled:* the seam is `navigator.accept_effects`, as proposed. It merged to `main` in PR #28 (`475ab9a6`) and
   shipped in shiploop 1.23.3.
3. **The live pass rule and sample count.** I recommend 3 samples with pass = all. Four samples allow
   `experiment.py`'s A/A spread but cost a third more.
   *How it was settled:* 3 samples, all of which must pass (`"live": {"samples": 3, "pass": "all"}`).
4. **The default live driver.** I recommend the slice default (Codex / Terra / xhigh, owner 2026-10-29) for rounds that
   count as evidence. A cheaper cell, such as Claude on Ollama, could serve routine checks. Its results are their own
   baseline cell and are never compared with the default's.
   *How it was settled:* the harness's own default (`hosts.RUN_DEFAULT_HOST`) is the default driver; any other driver is a
   chosen cell with its own baseline, and `stage_report.py compare` refuses two roots whose drivers differ.
