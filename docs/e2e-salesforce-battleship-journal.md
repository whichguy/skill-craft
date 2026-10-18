# Salesforce Battleship E2E: journal

Owner request (2026-10-17): "run the proper prompt with 'developing a battleship game' in my Salesforce org". This file is the
living record of the `battleship-salesforce` case: its design, its oracle, what the fake CLI models, what no real org has shown yet,
and each run. The case is modelled on `chess-salesforce` (its journal is `docs/e2e-salesforce-chess-journal.md`, F1 to F9). Judge a
run by ShipLoop's SDLC fidelity, not by the game (the example-apps rule).

## 2026-10-17: the case is built (harness only; no real org touched) — status: interim

Built on branch `feat/bs-sf-7b267d` from the integration branch `feat/shiploop-eff-int-c5f79b` (fe18d950). Nothing here called the
real `sf` or read `~/.sf`: every suite ran with `env -i HOME=<empty> PATH=<python3 only>:/usr/bin:/bin:/usr/sbin:/sbin`, where no
`sf` resolves.

### Decisions

| Question | Answer and why |
|---|---|
| A shared Salesforce module, or reuse `chess_salesforce.py`? | **Reuse: `checks/battleship_salesforce.py` loads `chess_salesforce.py` by path as a library.** About 60% of that file (the `sf` calls and scrub, queries, prefix rules, preflight, snapshot, compare, the destructive deploy, `deployed`, `tests`, the anonymous Apex runner, the probe writer) works unchanged for any prefix. A move would have split module globals the chess suite patches (`cs.sf`, `cs.records`, `cs.CASES` in `RealOrgQuirkTest` and `TestSelftestReference`), and the chess case is the one checked against the real org. Chess changed only by default-preserving parameters: `destructive_xml(members, order)`, `describe(diff, removable)` and the extracted `destructive_deploy(org, members, order)`, which now also names the component failures of a refused destructive deploy (failure text only). Chess suite: 192 tests before and after, all pass. |
| How does the board become visible? | A permission set `SLBattle_Access` granting the app, the tab (Visible) and both classes, deployed with the rest and assigned by the model with `sf org assign permset --name SLBattle_Access --target-org de`. The chess case granted nothing; the brief of 2026-10-17 reports its run 2 left the tab hidden (F9). The committed chess journal still lists tab visibility as unproven, so that fact is the brief's, not measured here. |
| How does the guard allow it without widening chess? | A new wrapper flag `sf_guard.py --permission-sets` (only the battleship case passes it): the deploy scope also takes `permissionsets/<prefix>*.permissionset-meta.xml` / `PermissionSet:<prefix>*` / a manifest type PermissionSet, and `org assign permset` joins the pinned commands. Without the flag the allow list and the scope are byte-for-byte the chess ones. |
| How strict is `org assign permset`? | Every `--name`/`-n` must be `<prefix>` plus letters, digits or underscores; at least one name; no `--on-behalf-of`/`-b`; the org pinned like every other command. Only `--name`, `--target-org`, `--api-version` and `--json` are accepted: oclif reads a bare word after a repeatable flag as another value (`--name SLBattle_Access Other`), and unknown flags (`--loglevel` decoys, the old `--permsetname` / `--onbehalfof` aliases) fail closed. |
| Cleanup order | 1. every PermissionSetAssignment of a new, exactly prefixed permission set (`sf data delete record --sobject PermissionSetAssignment --record-id <Id>`, one Id at a time); 2. those permission sets (one destructive deploy); 3. the rest in chess's order (a second destructive deploy); then chess's verification against the snapshot. A permission set that is assigned cannot be deleted, and it names the app, the tab and the classes, so it goes before them. |
| Rehearsal | `battleship_salesforce.py selftest` (a probe class, test, component, tab, app, app page and permission set; assign; access; anonymous Apex; cleanup) and `selftest --reference` (the known-good project in `test/shiploop_e2e/fixtures/battleship-salesforce-reference/`, graded by all five checks). Real org: main session only. |

### The prompt and the checks

The prompt is the chess prompt's frame (org `de`, `--target-org de` on every org command, no credentials, no `sf org display`,
prefix `SLBattle`, component `slBattleBoard`, the exact metadata allowed, the project root, the deploy and per-class test commands,
"Do not stop until the tests pass in the org") with the Battleship rules, the exact JSON keys (`shots`, `shipsLeft`, `gameOver`,
`lastShot` = `{"row", "col", "result", "ship", "size"}`), `SLBattleEngine.InvalidShotException`, the seed contract, the post-game shot
rule, the controller, the board, at least 8 Apex test methods and the efficiency sentence. It lives only in `cases.json`.

| Check | Prompt sentence it tests | How |
|---|---|---|
| `project` | the DX project, the classes, the component, the tab, the app, the permission set and its grants, no other metadata | file scan; the permission set XML must grant the app (visible true), the tab (Visible) and both classes (enabled true) |
| `deployed` | deploy it to the org | chess's `deployed` plus a PermissionSet query |
| `tests --min-tests 8` | at least 8 Apex test methods, run in the org one class at a time | chess's `tests` |
| `access` | the board opens for the user the CLI is logged in as | read-only: PermissionSet by name; PermissionSetTabSetting (Name, Visibility) of that set; the user named by `sf org list`; PermissionSetAssignment (AssigneeId) of that set |
| `rules` | the game rules, the JSON keys, the seed contract, the invalid shots | four anonymous Apex runs, graded in Python (below) |

### The oracle (`rules`)

Four anonymous Apex runs; the Apex only records, Python decides:

- `game_a` (seed 7) and `game_b` (seed 20261017): `SLBattleController.newGame(seed)`, then `fire` once at each of the 100 cells in
  row-major order, every answer recorded (result, ship, size, gameOver, shots, shipsLeft, row, col) and printed as one JSON array on the
  last debug line (a log over the size limit loses its oldest lines, not its last). Per game, seven markers: `start` (shots 0,
  shipsLeft 5, gameOver false, lastShot null), `results` (every result miss/hit/sunk at the cell fired, ship and size only on a sink),
  `hits` (exactly 17), `sunk` (exactly five sinks, sizes the multiset {5, 4, 3, 3, 2}, names distinct and each the standard name of its
  size), `gameover` (false before the fifth sink, true from it on), `counts` (shots and shipsLeft after every shot), `fleet`.
- `fleet` is the geometry check: every sinking shot must end a straight run of its size to its left or above it (row-major order fires
  a ship's last cell there) whose other cells were plain hits, and one choice of runs must cover every hit cell exactly once. It catches
  a bent, wrapped or overlapping ship that the counts alone would pass.
- `repeat`: `newGame(7)` once, then a second `newGame(7)` played through: its sequence must equal `game_a`'s (`seed.same`: the same
  seed in another transaction and after an earlier call). `seed.different`: `game_a` and `game_b` differ.
- `invalid`: on `SLBattleEngine` directly, after a valid shot at (0, 0): (0, 0) again, (10, 0) and (0, -1) must each throw
  `InvalidShotException` (three markers). The controller is never given an invalid shot: an `AuraHandledException` is uncatchable in
  anonymous Apex (chess F7.4).

19 markers. The independent oracle is the standard fleet and the grid geometry, never the candidate's own output.

### Experiments and tests (hermetic)

| What | Result | Evidence |
|---|---|---|
| Guard tests written first (11 in `PermissionSetTest` and the `parse_fixed` tuple test) | red on the unchanged guard: 2 failures, 10 errors of 12; green after the change. A 12th `PermissionSetTest` added in review (a wrapper without `--prefix` assigns nothing; names are ASCII) is red with those two lines removed and green with them | `test/shiploop-e2e-sf-guard.test.py` |
| Oracle against broken copies of the reference engine (MIRROR in the battleship suite) | each fails on its own marker: fixed fleet -> `seed.different` only; state carried between calls -> `seed.same` only; diagonal destroyer -> both `fleet` markers only; overlapping cruiser -> `hits`, `fleet`; a 16-cell fleet -> `hits`, `sunk`; capitalised names -> `sunk`; a sink reported as a hit -> `sunk`, `gameover`, `counts`, `fleet`; a name on a hit -> `results`; no shot count -> `counts`; game over one ship early -> `gameover`; a repeated cell accepted -> `invalid.repeat`; out-of-range accepted -> `invalid.row`, `invalid.col`; a refused post-game shot -> every game marker but `start` | `TestOracle` |
| The grader's own Apex, translated by the suite's Apex subset and run against the reference copy | 19 of 19 markers | `TestMirrorOfTheReference` |
| Cleanup order, two mutations of `do_cleanup` (not committed) | skipping the assignment step: 2 cleanup tests fail; one destructive deploy for everything: 1 fails (the order assertion). Both restored byte for byte | this entry |
| Fake-org rehearsal of the whole case, in harness order (preflight, snapshot, model deploy and assign through the case's own wrapper, the five checks, cleanup, `selftest`, `selftest --reference`) | 14 of 14 steps exit 0; `rules: 19 of 19`; the guard logged 2 model calls, both allowed; the org back to 4 ApexClass, 13 bundles, PermissionSet `baseChessAccess` only, 0 assignments | scratch script, output quoted here; the same path is `TestModelThroughTheGuard` and `TestSelftest` |

`run.py` has no fake or rehearsal mode for a platform case (`--preflight-only` installs the marketplace build and calls the real
`sf`), so the fake-org rehearsal above stands in for one. Suite counts are in the commit message.

### What the fake models that no real org has shown yet (unverified)

1. `sf org list --json` gives the alias's `username` (the `access` check reads it; chess read only `alias` and `connectedStatus`).
2. `PermissionSetTabSetting` answers `Name` and `Visibility` for a permission set's `ParentId`, with `DefaultOn` for metadata
   `Visible` (the check also accepts `Visible` and prints what it saw).
3. `sf org assign permset --json` returns `result.successes` / `result.failures`; assigning to the logged-in user needs no flag.
4. `sf data delete record --sobject PermissionSetAssignment --record-id <Id>` deletes an assignment of the logged-in admin.
5. A destructive deploy refuses an assigned permission set (believed true) and, in the fake only, refuses a component that a remaining
   permission set names (the stricter model; the cleanup's order is safe either way).
6. The reference Apex compiles (no Apex runtime here; README of the fixture lists where to look first), and the grader's scripts
   compile: `Math.mod`, `JSON.deserializeUntyped` casts, `List<Object>` literals, `e.getTypeName()`.
7. The org's own permission sets: the chess reference rehearsal of 2026-10-17 saw the platform create one (no prefix) mid-run. The
   cleanup still fails closed on any difference from the snapshot, and now names such an item as "left alone" instead of as a removal
   that failed.

### Before the first live run

1. Do not merge this branch into a checkout a chess run is reading: it changes `sf_guard.py`, `fake_sf.py` and `chess_salesforce.py`,
   which a live run reads at call time (chess journal, operating rules).
2. Read-only on the real org: `python3 test/shiploop_e2e/checks/battleship_salesforce.py preflight --org de --prefix SLBattle`.
3. With the owner's go for a deploy: `selftest --org de` (probe), then `selftest --org de --reference`. They answer items 1 to 6 above.
   Fix the fake to every shape the real org shows, as chess F7 did.
4. A one-prompt Grok probe through the wrapper: `sf org assign permset --name SLBattle_Access --target-org de --json` allowed and
   logged, `--name Other` denied.
5. Then the live run: `run.py --case battleship-salesforce --host grok --model grok-4.7 --effort medium --source checkout ...` with
   the chess case's host and permission settings.

## 2026-10-17 · real-org self-tests before the first live run (firm)
- `preflight --org de --prefix SLBattle`: org connected, no SLBattle item in 13 metadata types.
- `selftest --org de` (probe project): every step PASS — deploy, deployed, tests, assign (`sf org assign permset` status 0,
  1 success), access (tab settings seen: `DefaultOn`; assignment read back), apex-run, cleanup (unassigned 1, then the
  permission set, then the rest; org equals its snapshot: 151 PermissionSet, 38 CustomApplication, 12 CustomTab, ...).
  Settles the unverified items: the `sf org list` user name, `PermissionSetTabSetting.Visibility` = `DefaultOn`, the assign
  JSON, deleting an assignment with `sf data delete record`, and that the assignment must go before the permission set.
- `selftest --org de --reference`: every rules marker PASS on both seeded games (17 hits, the standard fleet sunk,
  gameOver at the fifth sink, counts, straight non-overlapping fleet), seed.same, seed.different and the three invalid
  shots; cleanup back to the snapshot. The reference Apex and the grader's anonymous scripts compile on the real org.

## 2026-10-18 · live run 1 (interim)
See `test/shiploop_e2e/LEARNINGS.md` "The Salesforce Battleship case, live run 1". Findings to fix: the keep rule for a done-but-uncommitted run (harness), the idle host after done (harness), the mutation gate for remote-resident test commands and the test-command-only revise restarting every step (ShipLoop).

## 2026-10-18 · the release slice: deployment tested from a built product (harness only, fake org, no real `sf`) — status: interim

Owner request: an end-to-end test focused on deploying into the owner's Salesforce org, starting at ShipLoop's release stages with an
already-built product instead of building the app from intake. Built on `feat/e2e-release-slice-ef1f39` from main 7580fb9a. Nothing
here called the real `sf` or read `~/.sf`: every suite ran with `env -i HOME=<empty> PATH=<a folder holding only python3 and node>:/usr/bin:/bin:/usr/sbin:/sbin`,
where no `sf` resolves. The runbook is `test/shiploop_e2e/README.md` "The release slice"; the code is `test/shiploop_e2e/release_slice.py`
(no platform word in it or in the run.py additions) and the case's `seed_product`, `seed_home`, `seed_release` and `platform.existing` keys.

### Decisions

| Question | Answer and why |
|---|---|
| Where does the seed stop, and what does it record? | `--seed-at release-plan` (and `system-test-author`, which fell out for free: the same machinery with an earlier stop and three more graded stages). The existing `SEED_SCRIPT` walks the navigator through every stage before it; it now also takes `records` ({stage: fields}) merged into each synthetic result. A first experiment showed the walk already reaches release-plan on the real navigator, so no engine change (no `skills/` file touched, no change note). |
| Where is the product committed? | In the run's **worktree**, on the run branch, after the item's base was recorded (the seed stops once at step-plan, commits, then continues). So the item reads as built after its base, `workspace plan-return` sees exactly the product's files as the delta (17 paths, `.gitignore` included), and the source checkout holds only the baseline until the run's own return. Committing it into the source baseline instead would have left the return nothing to return. |
| What of the fixture is the product? | `battleship-salesforce-reference` minus its README (it documents the harness: checks, self-test; `seed_release.product_exclude`), plus a new `.gitignore` for the CLI's `.sf/` and `.sfdx/`. Live run 1 committed two `.sf` tracking files at the return, which forced a working-tree return and failed `committed` (finding 4 of its entry); a standard SFDX project has that `.gitignore`. The reference README now says the one place its files reach a run. |
| The knowledge home | `battleship-salesforce-home/{spec,environment,architecture}.md`, written by hand from the request and the reference: R-1..R-12, AD-1..AD-4, the deploy, validate (`--source-dir force-app`: the bare command exits 2, seen in run 1), assign and test commands with `--target-org de`, the access the request grants. Committed in the baseline like the neutral home. No grader, fixture or oracle word in any of it (a test greps the worktree). `records.json` beside them (not copied) holds the work item and the fields the skipped stages leave: step-plan criteria, test commands and paths; system-test-author `system_commands` (the org suite **without** a deploy: the deploy is the release stage's) and an open item A1 for release-plan ("the suite has not run: it runs after the deploy"). |
| Input gates of the outer stages | Checked on the checkout's own CLI: `next` prints the release-plan packet with the system commands, A1 and the three knowledge files; a model-shaped release-plan result passes `complete --check-only`, and one without `consumer_checks` does not. Later stages' gates need accepted results and an Improve child; the rehearsal drives them with the navigator. No delivery contract (unmarked run, as in run 1). |
| Delegation | inline for a release slice (a real run of the case is inline); step-plan seeds keep Ask-Agent. |
| Chain verdict | not computed for a release slice (it has no implementation chain; the old rule would have failed every such run). |
| Grading | New `release_slice` block and verdict (also in the printed report and `mismatch.md`): which stages from the seed point ShipLoop accepted, where and why it stopped, and the deploy. The deploy verdict reads the guard log: every allowed `sf project deploy start` (outside the harness's own preflight lines) must fall between the acceptance of release-check and of release, and at least one must have exited 0. The exit is required because in update mode the kept app answers `deployed`, `tests` and `rules` by itself: a failed deploy over it would pass every check. `project` (reads the source checkout) runs only once any file of the product is in it; before that it is left out and named in `skipped_checks`. |
| Platform modes | `--platform-existing fresh` (default, unchanged) or `update`, listed per case in `platform.existing`. The harness sets `$E2E_PLATFORM_EXISTING` for the preflight and before commands only when it is not fresh. `update`: preflight accepts the prefixed items and names them; the snapshot records them and the assignments of the baseline permission set; the cleanup (reading the mode from the snapshot, not the environment) removes only what the run added, including assignments added to a baseline permission set; a baseline class or bundle whose LastModifiedDate changed is reported as deployed over in place (`compare(..., updated=)`), every other difference still fails; a snapshot without the baseline assignments is unusable and deletes nothing. A resume keeps its run's mode. |

### Tests

| Suite | Before | After | Notes |
|---|---|---|---|
| `shiploop-e2e-release-slice` (new, registered in `suite_catalog.py`, pinned in `test-groups`) | - | 43 tests, 31 to 37 s | the seed on the real CLI (release-plan, system-test-author), the case keys and their refusals, the release verdict on run folders made by hand, the mode rules, and 8 whole-run rehearsals: `run.main` with a fake Grok that drives the navigator and calls the guarded `sf` (the case's own `sf_guard.py`, preflight, snapshot and cleanup commands) against `fake_sf.py`: fresh pass, fresh refusal of a kept app, update + keep, update + cleanup, early stop, early deploy, failed deploy over the kept app, resume mode |
| `shiploop-e2e-battleship-salesforce` | 52 | 63 | +11 update-mode tests on the fake org |
| `shiploop-e2e-chess-salesforce` | 192 | 192 | the library changes are default-preserving |
| `shiploop-e2e` | 429 | 429 | 4 `FanoutGradeTest` errors under `env -i` until a `node` link was added to the sanitized PATH (they spawn `node`; not related) |
| `-environment` / `-platform` / `-sf-guard` / `-slice` | 133 / 161 / 108 / 58 | same | |
| `test-groups` | 38 | 38 | catalog pin 95 -> 96 ShipLoop suites, 150 -> 151 suites, the family list gains the new id |
| the rest of the E2E family (runrecord, fidelity, reorientation, baseline, quality, packet-anatomy, render-diff, commit-counters, efficiency, owner-page) | | all pass | render-diff fails one test under `env -i` with no `TMPDIR` on the unchanged tree too (checked with `git stash`); it passes with `TMPDIR` set |

Fail-first: run against the unchanged check scripts, 8 of the 11 update-mode tests fail (the other 3 pin what must not change: a fresh
snapshot's file, the default cleanup, the case's key). Mutations of the new code, each caught by the test named for it: the deploy
window always "in" (GradeTest), "returned" always true (the split-checks and the early-stop rehearsal), the chain graded for a release
slice (the fresh rehearsal).

### Not verified against the real org (unverified)

1. Update mode's queries (the assignments of a permission set by Id, the changed LastModifiedDate on a redeploy) run only against the fake. Whether the real org
   changes LastModifiedDate on a redeploy of identical source is not known; either way the cleanup passes (`updated` or unchanged).
2. A real model's release-plan..handoff results through `complete`: only release-plan's gates were run (`--check-only`); the rest of the walk is the
   fake host applying results with the navigator, so Improve children, the return (`workspace execute-return`), the `release-verify` consumer-check
   rerun and the knowledge closes are not exercised. The return is emulated with a fast-forward merge.
3. Whether the seeded home steers a model well (the records are accurate to the reference and to run 1's observations, nothing more).
4. `committed` after a real return: with the `.gitignore` the return should be able to fast-forward; not shown.
5. The idle-host gap below.

### Known limits that this entry does not fix

- The host stays open after ShipLoop is done (run 1, finding 3) until `--timeout` ends it; a host something else kills (rc 143) is a failed
  process, so `--keep-platform` is not honoured (`keep_refusal`). Use a `--timeout` a little above the expected run and do not kill the host.
- `committed` fails for a return that applies only the kept files to the working tree (run 1, finding 4).

Related commits: 7580fb9a (main at the start), fef544f4 (the case), 0d6d781e (live run 1 learnings). Commit: see `git log` of the branch.
