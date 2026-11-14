# Planning-points probe (2026-11-14)

Journal: E24 in [docs/shiploop-question-driven-planning-journal.md](../../shiploop-question-driven-planning-journal.md).
Case: `ticket-due-times` in [test/shiploop_e2e/cases.json](../../../test/shiploop_e2e/cases.json). Probe:
[due_times_probe.py](../../../test/shiploop_e2e/checks/due_times_probe.py). Reference and defects:
[reference_due_times.py](../../../test/fixtures/quality/reference_due_times.py). Calibration: [calibrate.py](calibrate.py),
[evidence/calibration.json](evidence/calibration.json). Scorer: `score.py` (added before any run is scored; it implements the
definitions below and nothing else).

## Why

On 2026-11-14 the owner proposed planning exit criteria: setup and data migration, schema, services and tooling, auth,
documentation, UI, interactions and deployment phasing, each answered or marked not applicable in one gate question, under a
scope rule (nothing beyond the request unless it is a material implied requirement). Most of this is ShipLoop's concern map
([shiploop_concerns.py](../../../skills/shiploop/scripts/shiploop_concerns.py), built in
fff7fa13fd537d7152e9d71a476b716e4f5e6839 and delivered to its owning stages in e0c9a19cd5e4ec1588a340b32b7cf7d58fca98bc): the
plan writes one row per concern per work item, and step-plan's Until Loop exits on mapping the rows it owns. The concern-scope
study (E23; 7323fee9b3a18025df5f802d451cc537f3973a59 registered it, 3f8ebf5a30ea8c70a6e8118d66b97d1d7951f399 recorded it) judged
376 applicable rows: 73% requested, 25% implied, 2% beyond, so no scope-basis field was built. Its census found switchover,
migrate-before and migrate-after applying in only 11, 9 and 1 of 416 recorded work items, and documentation and setup have no
row of their own (F38, F41). The recorded runs cannot say whether planning handles the owner's deployment, migration,
documentation and setup points. This probe can.

## Question

Given a request that genuinely needs a data migration before its feature is switched on, a stored field that existing records
keep across restarts, a staged switch-on with a way back to the current release, a new setting with defaults, and the
documentation an operator and a maintainer would read, does ShipLoop's planning cover each point, and do the release and
migration rows bind what is delivered?

## The case

`ticket-due-times` starts from ticket-assignment's base, `fixtures/node-tickets` (pin `5652a97375d0`), a 1.4.0 help-desk
service with a JSON data file. The request (verbatim in cases.json) asks for due times per priority (4, 24, 72, 168 hours by
default, changeable without a code change), fixed once set, shown as `due`, an `overdue=true` listing, due times for the tickets
already in the production data file, a switch-on with `DUE_TIMES=on` only once the data file holds them (until then the service
answers exactly as today), and a way back to 1.4.0 that still starts on the data file the new release wrote.

How each point is needed:

| Point | Stated in the request | Made necessary by the base |
|---|---|---|
| Data migration before the feature | "The tickets already in the production data file get due times too ... Due times are switched on in production only once the data file holds them" | |
| Schema change that records survive across a restart | "set once", "keep them from then on" | decision 8: a field added to a ticket is added in `src/persistence.js` "or it is lost at the next restart" |
| Staged release with a rollback step | `DUE_TIMES` off until `on`; "go back to the current release, 1.4.0" | `src/persistence.js` reads only format version 1, so a version bump breaks the way back; `test/persistence.test.js` pins version 1 |
| Documentation update | not stated | README.md lists every setting; docs/operations.md is the operators' runbook; docs/api.md documents every field and parameter; CONTRIBUTING.md asks for a decision record for a data-file change and a CHANGELOG section per release |
| Setup step | `DUE_TIMES`, and the hours "without a code change" (no name given) | README.md: "Every setting is an environment variable" |

The documentation point is the one the request leaves to the repository, on purpose: it is the point the owner asked about
that has no concern row.

## Calibration (before any run)

`calibrate.py` builds every variant of `reference_due_times.py` (the base, a reference delivery, six targeted defects) and runs
each probe mode and the base's pristine tests on each. Result (`evidence/calibration.json`): 0 of 56 cells differ from the
expectation. The base fails exactly migrate, restart and switch; the reference passes all seven; `version-two` fails rollback
and pristine; `priority-moves-due` and `due-not-persisted` fail restart; `no-backfill` fails migrate, restart and switch;
`flag-ignored` fails off; `overdue-active` fails migrate.

## Design (registered before any run)

- **Runs.** 3 runs of `ticket-due-times` on the E2E default subject, `hosts.ROLE_DEFAULTS["subject"]`: Grok, `grok-4.6`, effort
  `xhigh` (owner, 2026-11-10). `run.py --source marketplace` (what origin/main publishes: skill-craft 2.37.4, ShipLoop 1.34.3),
  no `--planning-review` (the engine's default), no timeout, turn or resume limit (run.py's defaults), each in
  `~/e2e-runs-planning-points/20261114/pp-<n>`, side by side (the case leases no port; cases.json says why). A run that the
  host or harness ends with ShipLoop still active and that `--resume-run` cannot continue is invalid and is replaced once by a
  fourth run; a run ShipLoop ends blocked is valid and scored as it stands.
- **What is read.** From each run's ShipLoop folder (`shiploop-run.json` `run_dir`): `state.md` (`history`, `accepted`) and
  `results/*.md`; and the delivered `work/` checkout against the base commit (`result.json` `base.start_head`).
  - *The plan*: the first accepted `plan` result in history order, the plan the queue started from. A later accepted plan
    result (a re-plan) is reported beside it and not scored.
  - *The step plans*: every accepted `step-plan` result, by work item.
  - *The release plan*: the last accepted `release-plan` result.
  - *Plan text*: the plan result's string values (work item titles and contexts, concern decisions and reasons, assumptions,
    summary), without the labels named under M5.
- **Measures** (all by script; no judge is registered, so none is used; a reading that needs judgement is reported as a reading,
  never as a score):
  - **M1 rows.** For migrate-before, migrate-after, switchover, state and config: does the row apply to at least one work item,
    with its owner stage.
  - **M2 order.** Migration items: items whose migrate-before row applies; if none applies, items whose title or context matches
    `MIGRATION` (`backfill|migrat|existing tickets?|already in the (production )?data file|saved before|older (data )?files?`,
    case-insensitive). Feature items: items whose title or context matches `overdue`. Verdict *before* (the first migration item
    comes before the first feature item), *same* (one item), *after*, or *unknown* (either set empty). For *same*, the item's
    accepted step plan: the first step matching `MIGRATION` against the first step matching `overdue`.
  - **M3 release last.** Every applicable switchover row: *last* when each is owned by release-plan or operations, or belongs to
    the last work item; *early* when one owned by another stage belongs to an earlier item; *none* when no switchover row
    applies.
  - **M4 rollback.** The release plan's text is split into segments at line ends and sentence ends. *Rollback planned*: a segment
    matches `roll ?back|revert|go back`. *Data-aware*: such a segment also matches
    `DUE_TIMES|1\.4\.0|data file|DATA_FILE|tickets\.json|backup|version 1|format`.
  - **M5 documents in the plan.** Plan text naming README.md, docs/operations.md (or "runbook"), docs/api.md, CHANGELOG.md,
    docs/decisions/ (or "decision record"), or the word "documentation" (or a bare "docs"); a path under docs/shiploop/ does
    not count. Each document is reported. (The word entry was added after a smoke test of the scorer on an older ticket
    run, whose plan wrote "API documentation" and matched no file pattern; it was added before any run of this case.)
    *Plan text* throughout is the plan result's string values, without the labels (`id`, `applies`, `owner_stage`,
    `follows`, `outcome`, `due_item`, `anchor`).
  - **M6 setup in the plan.** Plan text naming `DUE_TIMES` and a setting for the hours: an upper-case name with an underscore that
    the base does not read (the base reads PORT, DATA_FILE, NOTIFY_FILE, WORKER_INTERVAL_MS, MAX_BODY_BYTES, LOG_REQUESTS), or a
    configuration file path ending `.json`, `.env` or `.conf`, other than a file the base has.
  - **M7 product checks.** The case's eight checks as `result.json` records them (suite, pristine and the six probe modes). For a
    run that never reached its checks, the probe is run on `work/` and the record says so.
  - **M8 documents in the product.** The delivery's diff from the base commit: D1 README.md names `DUE_TIMES`; D2 README.md names
    each new setting of M9; D3 README.md or docs/operations.md has a segment naming `DUE_TIMES` or switching on, and one naming
    going back (`1\.4\.0|roll ?back|go back`); D4 CHANGELOG.md gains a `## ` section and package.json's version changes; D5 a new
    file under docs/decisions/; D6 docs/api.md names `due` and `overdue`. **A documentation miss**: D1, D2, D3 or D6 fails. D4
    and D5 are the repository's conventions and are reported, not part of the miss.
  - **M9 setup in the product.** New settings: upper-case names the delivered `src/` and `bin/` read through `process.env` or an
    `env` object that the base's do not, other than `DUE_TIMES`, or a new configuration file (a new file ending `.json`, `.env`
    or `.conf` outside test/ and docs/). **A setup miss**: no new setting, or D2 fails. (That the service starts and uses the
    default hours without it is M7's migrate check.)
  - **Binding**, per run, for migrate-before and switchover: (a) the row applies to an item (M1); (b) its owner acted on it: a
    step-plan row is mapped to at least one step in that item's accepted step plan; a row owned by another stage is named in that
    stage's accepted results (migrate-before by `MIGRATION` or `data file`, switchover by `DUE_TIMES`); (c) the product passes the
    checks the row serves (migrate-before: migrate, restart and switch; switchover: off and rollback). A row binds in a run
    when (a), (b) and (c) hold.

## Predictions (registered; scored as written)

"Every run" means every valid run; "every completed run" means every valid run whose case checks ran.

| # | Prediction | My probability |
|---|---|---|
| P1 | migrate-before applies to at least one work item, in every run | 70% |
| P2 | switchover applies to at least one work item, in every run | 55% |
| P3 | state applies to at least one work item, in every run | 80% |
| P4 | config applies to at least one work item, in every run | 80% |
| P5 | migrate-after applies in at most one run | 65% |
| P6 | the migration comes before the feature in every run: M2 *before*, or *same* with the first migration step no later than the first overdue step | 70% |
| P7 | the release is planned last in every run: M3 *last* | 60% |
| P8 | in every run that reaches release-plan, its result plans a rollback (M4) | 90% |
| P9 | in every run that reaches release-plan, the rollback is data-aware (M4) | 55% |
| P10 | in every run, the plan names at least one product document (M5) | 70% |
| P11 | in every run, the plan names `DUE_TIMES` and a setting for the hours (M6) | 75% |
| P12 | in every completed run, migrate, restart and switch pass | 55% |
| P13 | in every completed run, rollback passes | 75% |
| P14 | in every completed run, off passes (the off mode) | 50% |
| P15 | in every completed run, there is no documentation miss (M8) | 40% |
| P16 | in every completed run, there is no setup miss (M9) | 65% |
| P17 | migrate-before and switchover both bind in every run | 35% |

## Decision rules (registered)

- **A documentation row.** Recommend examining a documentation concern row only if at least one valid run has a documentation
  miss (M8). If the run's plan named the missed document (M5), the miss happened after planning, so say that a plan row would
  not have bound it and name the stage that missed it. With no miss, recommend no row.
- **A setup row.** The same rule with M9 and M6.
- **Do the release and migration rows bind in practice?** *Yes* when both rows bind in every valid run; *partly* when some do,
  naming the failing condition per run; *no* when a row does not apply in most runs, or its (b) fails in most runs.
- **Either way.** No concern row is added and no ShipLoop prompt is changed in this probe (owner constraint: not without a
  measured miss); a measured miss becomes a proposal to the owner with its evidence.

## Validity and limits

- The runs go side by side and the case leases no port. A model's own smoke test on port 4180 could meet another run's server;
  each run's events are searched for a server started on a fixed port and for `EADDRINUSE`, and any hit is reported with the run.
- One host and model, 3 runs: "every run" predictions are about these runs, not a rate.
- The request states the migration, switch-on and rollback outcomes, so the rows' applicability is partly given by the request;
  only documentation is left to the repository.
- The probe cannot check that a change of the hours leaves a due time where it is (the request names no setting for the hours);
  it checks the priority half of "set once".
- The plan-text measures (M2 to M6) count words, not intent: a plan that names a document without planning to change it counts
  as naming it, and a paraphrase the patterns miss counts as absent. Each matched excerpt is kept in the evidence so a reader
  can see what counted.
