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
