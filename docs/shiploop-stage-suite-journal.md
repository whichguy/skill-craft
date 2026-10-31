# ShipLoop stage suite journal

Hermetic and apparatus work on the stage suite (`test/shiploop_e2e/stage_suite/`, plan
`docs/plans/shiploop-stage-suite.md`). Live stage-suite rounds go in `test/shiploop_e2e/LEARNINGS.md`, which the release
preflight reads as the E2E journal; work that ran nothing live goes here.

## Stage suite core on macOS: two causes, three failing tests (2026-10-30) — status: firm; a test-apparatus fix, nothing live

The stage suite core (c8af6a5c, built in a Linux container) failed 3 tests in quick on macOS, on a clean origin/main too:

- **`stage_build.build` gave two spellings of one folder.** `run_dir` came from `out` as the caller gave it
  (`/var/folders/…`). `worktree` came from `state.md`, which ShipLoop records resolved (`/private/var/folders/…`). The
  same split happens under any symlinked output folder, Linux included.
  - The fix: `build` and `render` resolve `out` first.
  - The test: `Builds.test_a_build_through_a_symlinked_folder_spells_each_path_one_way`, which fails on the old builder.
  - The class's temp root is resolved to match.
- **The oracle's environment probe counted a macOS variable as inherited.** CoreFoundation gives every process
  `__CF_USER_TEXT_ENCODING` at start, even under `env -i`. The oracle's cut is right: it passes five variables. The
  probe now ignores that name, as it ignores the shell's own `PWD`, `SHLVL` and `_`.

After the fix, quick (`--changed-from origin/main`) passes all 49 suites on this Mac. The stage_suite files are outside
`boundary.fingerprint`, so the evaluator digest is unchanged.

## The stage suite: the seam, the no-model tiers, the live tier and two audits (2026-10-30 to 2026-10-31) — status: seam and no-model tiers firm; live tier built and fake-host tested only, no real round

**What this is, by kind** (AGENTS.md asks the two to be told apart). The one change under `skills/` is a **generic ShipLoop
internal refactor** with no behaviour change: `accept_effects`, 77884063f5451f4683328af77844f41dee7ae5fb, shipped in the
release 5ef936ab8b63907cac55e7da2fbbf04bfb2c2d40 (skill-craft 2.24.3, shiploop 1.23.3). Everything else is **E2E apparatus**:
`test/shiploop_e2e/stage_suite/` (oracle, builder, runner, live runner, report), `stage_cases/` (three `validate-existing`
scenarios), seven test files and their catalog entries. None of it is a ShipLoop product improvement, and nothing here
measures ShipLoop's behaviour with a model. The plan is `docs/plans/shiploop-stage-suite.md` (dae643fafefeba5b8f947b7fb0ab9b6d82afac79).

**What landed, in order.**
- 55f312a504460c977ad59355599080d506babe83: `shiploop-actual-improve-cli` runs with the progress observer off. An apparatus fix
  (test only); the failure also happens on the base commit.
- 77884063f5451f4683328af77844f41dee7ae5fb: the seam, with `test/shiploop-seed-seam.test.py` and
  `changes/shiploop/seed-effects-seam.md`; carries `No-E2E-Round:`.
- c8af6a5c19b307fa8acb15e717dd9ef60c59eb6b: the no-model tiers (`stages.py list | verify | render`).
- 475ab9a655b9f0a9afbec5eb5753009c30e892d1: PR #28 (the two above) merged to main after the owner marked it ready, by
  another session on the owner's instruction (see 527b9a31925fdbe453e6a0be8f99165073be02d2). The owner's own update-branch
  merge 6b8fc70cedd437e0e7b44a93016c5231a66600dd made the release preflight refuse, and that session recorded the waiver.
- ab0fbeabcc7c5c17c8b3b4fe6bf3f8ad8457dbbd (live tier), ab6f42924e451214b71f67a87af5f1261cba24fe (first audit's fixes),
  aef6fe8f4769a84ce8d77755540c1bf2ace5b5af (pre-landing audit's fixes), landed directly on main as a fast-forward
  86a858b9b9fddc63af25a3d0f7e145e4c13ca924..626e2d221589582de19c1109e12238b0dfcbe01f, per the owner's instruction not to open PRs.

**Decisions, with the earlier commits that shaped them.**
- *Everything new sits outside what `boundary.py` binds* (SPEC.md, cases.json, suites.json, every top-level harness `*.py`,
  `checks/`, `fixtures/`, `evaluators/`). Why: the evaluator and oracle digests bind baselines and calibrations; the
  closed-loop plan says a calibration whose digests differ is refused, and 733f812b8a42ea4f0897bedfa9960c105505c99c put the
  SDLC probes in a subfolder for the same reason. `run.py` and `slice.py` were not edited. The builder reuses `run.seed_run` by
  substituting `run.SEED_SCRIPT` in-process, restored on every path; the live runner has its own small stop-at-acceptance
  drive because `slice.drive` cannot take another stop predicate (S-12 trade-off, accepted). Checked against the merge base:
  evaluator and oracle fingerprints and all 80 snapshot hashes identical (the first audit); no bound file differs between
  the landed branch and main (the pre-landing audit). `fixtures/` is bound since cefff5edabdbfb1d8600e88fe0460f422c385056; my
  first boundary check and the docs that list the bound set omitted it, and no change touched it.
- *The seam, not an edit to the harness seed.* The old seed records stages with the pure `apply`, so a `validate-existing`
  packet said "results are below" with none and a seed to `document` failed ("no iteration record"). Seeding through
  `_transition` fixed the first; the post-save hooks of `complete` were needed for the second. Moving the after-gate effects
  into one function that `complete`, the Improve import and the control verbs all call keeps one implementation (S-12).
- *A plugin build the host failed to install starts no host* is 8ff81566e1ef45054964bbcc65a1edac59f296a6. My live runner did
  not honour it until the pre-landing audit found it (below).
- *Merged straight to main*, as the owner asked and AGENTS.md now says, after the pre-landing audit and my own re-run on the
  merge. Never forced, never squashed; main moved several times while this ran and each time I merged it in and re-tested.
- *Reverted* two unrelated tests a repair agent had edited to fit this root cloud container (`shiploop-e2e`,
  `shiploop-e2e-reorientation`); they fail identically on a clean main there.

**Measurements.**
- Seed plus packet render on the throwaway prototype: 0.995 s (`validate-existing`) and 1.27 s (`test`).
- At landing (626e2d22…): `shiploop-seed-seam` 14 tests; stage oracle 108, builder 48, report 45, live 86, runner 121;
  `stages.py verify all` 2 passed, 1 skipped (the render-only scenario); `render all` 3 of 3; catalog 111 ShipLoop suites,
  166 in total.
- CI: PR #28's quick job (run 41142815506) 19 min 18 s; the push of the live tier (run 41179700606, run number 831): plan,
  release-boundary, quick (17 min 41 s) and hermetic all succeeded.
- First audit of what had landed: 7 lenses, 16 findings (none a blocker), 12 statements checked clean. A real-CLI differential
  of the seam against the base commit across walk, send-back, control verbs, switches, workspace, Improve import and handoff:
  0 differences after normalising ids and times. Mutation: 72 mutants, 65 killed, 6 survived (all in findings R3 and R5 of that
  audit: the oracle's special-file handling and behaviours the code promised that no test pinned), 1 equivalent.
- Pre-landing audit of the live tier: 4 lenses, 25 findings, 13 statements checked clean; mutation 148 mutants, 114 killed,
  34 survived (itemised and mostly given tests afterwards). Every fix's new test was shown to fail without it by a fresh agent
  reverting the fix in a scratch copy.
- Cost of building and auditing this: seven workflows, about 28.0 million subagent tokens as the workflow tool reported
  them (seam 4.14 M, core 5.54 M, live 5.04 M, first audit 6.01 M, its fixes 0.60 M, pre-landing audit 5.93 M, its fixes
  0.78 M), 6 h 50 min, 2 h 31 min, 2 h 57 min, 1 h 04 min, 53 min, 1 h 50 min and 1 h 18 min of workflow time. No dollar
  figure was measured.

**Contrary evidence and what went wrong.**
- The build-time review of the live tier found that the stop could fire before the accepting command's post-save effects had
  run, and fixed it by waiting for the run lock. The pre-landing audit then found that fix's own hole (a SIGTERM or stop file
  during the wait still graded the half-finished tree, contradicting the README) and that `stage_live` never called
  `run.require_installed` (8ff81566e1ef above). Both would have mattered once a real model ran. A second review round found
  what the first did not; one round of review was not enough.
- The first audit found the oracle's `{"file": P, "unchanged": true}` passing when a fifo, socket or device appeared at `P`,
  a README listing four of six bad reference outputs from the first commit on, the plan still saying PR #28 was unmerged, tests
  that needed `node` with no skip, and six behaviours promised in docstrings that no test pinned.
- The core was green on Linux and red on the owner's Mac (09a0f19c376ec49cfb933f883652071bf211054f: a path spelled two ways
  across a symlink, and a macOS environment variable). Verification in one Linux container missed it. The live tier's
  signal tests read `/proc`; they now use `ps` but have not been run on macOS.
- Process: the first build workflow stopped on a failing "test" that was an agent's evidence run on a pristine copy of the
  base commit, a defect in my own orchestration, not in the code; and my pinned-count line in `test/test-groups.test.py`
  conflicted in three of my six merges with main because every suite-adding change edits it.
- The new SIGHUP test hung for about two minutes when the whole run was launched under `nohup`, which leaves SIGHUP ignored
  and which `stages.py live` deliberately honours; the test children now reset it.

**Remaining unknowns.**
- **No real live round has run.** No model host was usable in the container (Ollama down, Codex not signed in), so the live
  tier's catch rates are unmeasured, and whether a model that follows only one packet catches the planted conditions is
  unknown. The plan's step-3 exit (one real round of the `validate-existing` scenarios, journaled in
  `test/shiploop_e2e/LEARNINGS.md`) is not met. Until it is, the live tier is UNQUALIFIED by any real evidence.
- The settle wait assumes the real `shiploop` holds the run lock through the post-save effects. Verified by reading
  `run_lock` and `accept_effects` and by a fake that mimics it, not against a real model's `shiploop complete`. The command's
  trace row and the progress observer start run after the lock is released and are not waited for.
- A process a host leaves in a session of its own is abandoned, not ended; ending it needs a change to `run.launch` or the
  lifecycle ledger, both digest-bound.
- The `verify` tier's seed tree lacks the knowledge home a live run's has, so a check reading `docs/shiploop/` is proved only
  by a live run.
- Not measured: macOS for the live tier, the cost of a real round, and whether the 3-sample, all-must-pass default rule is the
  right bar.

**Left for the owner** (none changed): whether an edit to a packet's source should run the stage suites in the quick tier
(today only a change under `test/shiploop_e2e/` does, and the full tier; about 36.5 s more on a harness edit); whether
`stages.py live` should need an explicit `--host` or `--yes` (it starts the default host as soon as one is signed in, with the
3600 s per-sample timeout as its only cost bound, as `run.py` and `slice.py` do); the release preflight's treatment of a
GitHub update-branch merge; and the merged branches left on origin (`claude/shiploop-stage-suite-plan`, `-core`, `-live`).

**Evidence locations.** In the repository: the commits above, `docs/plans/shiploop-stage-suite.md`,
`test/shiploop_e2e/stage_cases/README.md`, the tests, and CI runs 41142815506 and 41179700606. Not retained: the seven
workflow journals and the audits' full reports lived in the cloud session's container under
`/root/.claude/projects/-home-user-skill-craft/13ba7f75-0230-543a-9fb9-f305dbacaa6f/subagents/workflows/` (runs
wf_76db106a-178, wf_563a96d1-2da, wf_39a49ee6-f5e, wf_6c0bb6ba-535, wf_dd049fa5-b25, wf_f615b145-ec7, wf_4fb364b8-408) and
are gone with it; the findings and numbers above are what survives. AGENTS.md's 2026-10-30 rule to cite earlier commits in full
reached this session after most of these commits were written, so their messages cite few full hashes; this entry supplies
them and nothing was rewritten.
