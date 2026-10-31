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
