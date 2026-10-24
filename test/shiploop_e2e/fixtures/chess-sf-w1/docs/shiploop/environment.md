# Environment

Checked at worktree `b3d6a2137d25b8f4fed40851ac7a1fc69d07d7e3` (empty baseline). Observation time is in `run/scratch/org-read.json`.

## Targets and runtimes

- Edit and commit in the isolated worktree. The source checkout stays at the empty baseline until the final workspace return. A return copies files only; it does not deploy. Source: workspace start and `run/scratch/baseline-find.txt`.
- Local runtime: none. There is no Node app, no Jest harness, and no Apex compiler in the checkout. Binding requirement: do not invent a local substitute for org tests.
- Test and delivery target: Salesforce Developer Edition org alias `de`, org id `00D000000000000AAA`, name `Self`, type Developer Edition, instance `USA838`, instance host `example-dev-ed.develop.my.salesforce.com`. Not a sandbox, scratch org, or Dev Hub. Source: `run/scratch/org-read.json` (read-only `sf org list` and `Organization` query). Revalidate the alias before deploy.
- CLI: `@salesforce/cli/2.154.4` (darwin-arm64, node-v25.9.0). Confirmed at prepare by `sf --version` exit 0 (`run/scratch/prepare-sf-version.txt`). The harness allows `sf` only against alias `de`, and only the commands it lists. `sf org display` is forbidden because it prints an access token. `sf org open` is not in that list and would print a session URL, so the browser front-door route was not probed.
- Prepare: runners start. `sf apex run test --help`, `sf project deploy start --help`, and `sf org list metadata --help` each exited 0 (`run/scratch/prepare-apex-help.txt`, `run/scratch/prepare-deploy-help.txt`, `run/scratch/prepare-list-help.txt`). Help shows `--class-names`, `--synchronous`, `--result-format`, `--target-org`, and deploy `--dry-run`. The Apex suite was not run: the classes are not deployed. Deploy was not run. `.gitignore` lists `.sf/` and `.sfdx/` so CLI state is not a product change. No local Jest or Apex compiler was installed.
- Platform guide: `references/platforms/salesforce.md`. No other platform guide applies.
- Deploy route: `sf project deploy start --target-org de` of this project's own metadata. It is an explicit command, not a Git hook or CI trigger. None exists. Org Apex tests see the last deploy, so a deploy must precede `system-test`. That test deploy is distinct from the final release receipt.
- API version: existing `SL*` Apex classes in this org are API 68 (`run/scratch/apex-api.json`). Proposal for this empty project: `sourceApiVersion` 68.0. Not a repo convention yet.
- Consumer entry after deploy: Lightning component tab `SLChess_Board` inside app `SLChess`, path `/lightning/n/SLChess_Board`. The tab file creates the entry; `lightning__Tab` alone does not. Optional flexipage remains the intake default.

## Commands

No formatter or linter exists in the checkout. Baseline: `run/scratch/baseline-find.txt` (no suite, missing coverage). Every command below is planned. The runner probe exited 1 before any test ran (`run/scratch/probe-apex-human.txt`, `run/scratch/probe-apex-tap.txt`).

ShipLoop's inner loop reads `tap` (`ok` / `not ok`). Step plans put only the tap commands in `test_commands`. The human fences are the request's evidence: run each one as well when that class is tested, and do not give them to the tap reader. One synchronous invocation takes one class. A pass of one class is not the full suite.

Setup for every Apex command: the class is already deployed to alias `de`. No DML fixture. Each test method is its own transaction. Re-run is safe.

Smoke (TC_1 only). Cost: one short transaction. Prints `TC_1`.

```sh
sf apex run test --target-org de --tests SLChessEngineTest.TC_1 --synchronous --result-format tap --code-coverage
```

Focused engine class. Cost: the rule methods, no depth-2 walk. Prints TC_1 through TC_14.

```sh
sf apex run test --target-org de --class-names SLChessEngineTest --synchronous --result-format tap --code-coverage
```

Focused controller class. Cost: fool's mate, scholar's mate, and the 33-ply Opera game, each in its own transaction. Prints TC_15 through TC_18.

```sh
sf apex run test --target-org de --class-names SLChessControllerTest --synchronous --result-format tap --code-coverage
```

Focused budget class. Cost: one position-6 `legalMoves` and one depth-2 count. Prints TC_19 and TC_20.

```sh
sf apex run test --target-org de --class-names SLChessBudgetTest --synchronous --result-format tap --code-coverage
```

Request evidence, human, one class at a time. Same IDs as the tap twin. Not the format ShipLoop's reader accepts.

```sh
sf apex run test --target-org de --class-names SLChessEngineTest --synchronous --result-format human --code-coverage
```

```sh
sf apex run test --target-org de --class-names SLChessControllerTest --synchronous --result-format human --code-coverage
```

```sh
sf apex run test --target-org de --class-names SLChessBudgetTest --synchronous --result-format human --code-coverage
```

Deploy. Adds this project's metadata only. Must precede the Apex commands. Distinct from the release receipt.

```sh
sf project deploy start --target-org de
```

Local file check for R-1, R-8, and NFR-4. Planned. Exit 0 only when API 68.0, `force-app/`, an exposed `slChessBoard` with both Lightning targets, the component tab, a Lightning app (`<uiType>Lightning</uiType>`) with Standard navigation and a `<tabs>SLChess_Board</tabs>` entry, a flexipage that names `slChessBoard`, and a `.gitignore` that lists `.sf/` and `.sfdx/` are present; every `*.cls` name starts with `SLChess`; and the forbidden metadata directories are absent. A comment that merely mentions `SLChess_Board` does not satisfy the app. Not an Apex test. Probed on the empty tree: exit 2, because `sfdx-project.json` is absent (`run/scratch/probe-meta-files.txt`). That is the planned pre-implementation result, not a pass.

```sh
grep -q '"sourceApiVersion": "68.0"' sfdx-project.json && test -d force-app && test -f .gitignore && grep -q '\.sf/' .gitignore && grep -q '\.sfdx/' .gitignore && test -f force-app/main/default/lwc/slChessBoard/slChessBoard.js-meta.xml && grep -q '<isExposed>true</isExposed>' force-app/main/default/lwc/slChessBoard/slChessBoard.js-meta.xml && grep -q '<target>lightning__Tab</target>' force-app/main/default/lwc/slChessBoard/slChessBoard.js-meta.xml && grep -q '<target>lightning__AppPage</target>' force-app/main/default/lwc/slChessBoard/slChessBoard.js-meta.xml && grep -q '<lwcComponent>slChessBoard</lwcComponent>' force-app/main/default/tabs/SLChess_Board.tab-meta.xml && grep -q '<uiType>Lightning</uiType>' force-app/main/default/applications/SLChess.app-meta.xml && grep -q '<navType>Standard</navType>' force-app/main/default/applications/SLChess.app-meta.xml && grep -q '<tabs>SLChess_Board</tabs>' force-app/main/default/applications/SLChess.app-meta.xml && test -f force-app/main/default/flexipages/SLChess_Board.flexipage-meta.xml && grep -q '<componentName>slChessBoard</componentName>' force-app/main/default/flexipages/SLChess_Board.flexipage-meta.xml && test ! -e force-app/main/default/objects && test ! -e force-app/main/default/permissionsets && test ! -e force-app/main/default/staticresources && test ! -e force-app/main/default/triggers && test ! -e force-app/main/default/profiles && test ! -e force-app/main/default/labels && test ! -e force-app/main/default/flows && ! find force-app -name '*.cls' ! -name 'SLChess*.cls' | grep -q .
```

Tab confirm, release-check and again after release. Look for the name `SLChess_Board`.

```sh
sf org list metadata --metadata-type CustomTab --target-org de
```

## Harnesses and suites

- Apex runner, selected. Role: prove R-2 through R-6 and NFR-1 inside org `de`. Fit: the platform executes Apex only in the org (platform guide, Testing and Remote tests). Available: CLI 2.154.4, probe exit 1 on a missing class, which is the expected pre-deploy result. Setup: deploy, then one class per synchronous command. Isolation: no rows, no `SeeAllData`, methods do not share a FEN. Teardown: none. Coverage tool: `--code-coverage` on the same command. Revalidate if the CLI or the org alias changes. New org-bound tests are `red_na` on an item base: the org still has the previous deploy, so a base run cannot fail the new assertions unless the command deploys first. The mutation check skips these commands because they test the org, not the checkout (platform guide, Remote tests).
- No Jest and no local Apex compiler. Not selected: a local substitute would not meet the request. LWC behavior on screen is UI-1, which is blocked, plus a source read of the template for the words the component must show.
- No MCP test tool. `search_tool` returned no tools (`run/scratch/probe-browser.txt`).
- Browser automation, required for R-7 and not available. Failed probe recorded in architecture.md UI-1. The default Apex commands do not run UI-1.
- Security and fuzz: not applicable (architecture.md, Not selected). No dependency updater.

Case record (all planned, not passed). Setup for TC_1–TC_20: none (stateless). Teardown: none. Surface: remote Apex. Owner: the test stage of the item that adds the class, then system-test. Oracle source: `docs/shiploop/spec.md`.

| ID | Class.method | Requirement | Input and expected result |
| --- | --- | --- | --- |
| TC_1 | SLChessEngineTest.TC_1 | R-2 | `startFen()` is the standard start FEN; `legalMoves` has 20 strings, equals that list sorted alphabetically, first `a2a3`, last `h2h4`; `status` is `ongoing`. |
| TC_2 | SLChessEngineTest.TC_2 | R-2, T-2 | `applyMove(start, e2e5)` throws `SLChessEngine.IllegalMoveException`. |
| TC_3 | SLChessEngineTest.TC_3 | R-2, T-4 | Stalemate FEN `7k/5Q2/6K1/8/8/8/8/8 b - - 0 1`: status `stalemate`, move list empty. |
| TC_4 | SLChessEngineTest.TC_4 | R-2 | `4k3/8/8/8/8/8/4q3/4K3 w - - 0 1`: status `check`, and `e1e2` is legal. |
| TC_5 | SLChessEngineTest.TC_5 | R-5, T-3 | Fool's mate plies end at `rnb1kbnr/pppp1ppp/4p3/8/6Pq/5P2/PPPPP2P/RNBQKBNR w KQkq - 1 3`, status `checkmate`, move list empty. |
| TC_6 | SLChessEngineTest.TC_6 | R-5 | Scholar's mate ends at `r1bqkb1r/pppp1Qpp/2n2n2/4p3/2B1P3/8/PPPP1PPP/RNB1K1NR b KQkq - 0 4`, status `checkmate`. |
| TC_7 | SLChessEngineTest.TC_7 | R-5 | After `f2f3 e7e6 g2g4`, status is `ongoing` and `d8h4` is legal. |
| TC_8 | SLChessEngineTest.TC_8 | R-3, R-4 | The four castle results in R-4, compared as the whole FEN string, not a suffix: `e1g1`, `e1c1`, `e8g8`, `e8c8`. |
| TC_9 | SLChessEngineTest.TC_9 | R-3 | No `e1g1` from the three rook-attack FENs in R-3. No `e1g1` when rights are `Qkq`. No `e1c1` when rights are `Kkq`. |
| TC_10 | SLChessEngineTest.TC_10 | R-4 | Whole strings from R-4: `e2e4` returns `rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1`; `e7e5` returns `rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq e6 0 2`; `g8f6` instead returns `rnbqkb1r/pppppppp/5n2/8/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 1 2`. From the pawn FEN, `e2e4` returns `4k3/8/8/8/3pP3/8/8/4K3 b - e3 0 1` and `d4e3` returns `4k3/8/8/8/8/4p3/8/4K3 w - - 0 2`. |
| TC_11 | SLChessEngineTest.TC_11 | R-3, R-4 | From `k7/4P3/8/8/8/8/8/4K3 w - - 0 1`, the list has `e7e8q`, `e7e8r`, `e7e8b`, `e7e8n` and not `e7e8`. Whole results: `e7e8q` → `k3Q3/8/8/8/8/8/8/4K3 b - - 0 1`, `e7e8r` → `k3R3/8/8/8/8/8/8/4K3 b - - 0 1`, `e7e8b` → `k3B3/8/8/8/8/8/8/4K3 b - - 0 1`, `e7e8n` → `k3N3/8/8/8/8/8/8/4K3 b - - 0 1`. |
| TC_12 | SLChessEngineTest.TC_12 | R-3 | Kiwipete has 48 moves, including `e1g1` and `e1c1`. Position 3 has 14. Position 4 has 6. |
| TC_13 | SLChessEngineTest.TC_13 | R-3 | No `e1e2` from `8/8/8/8/8/4k3/8/4K3 w - - 0 1`. No move starts with `e7` from `4k3/4b3/8/8/8/8/8/4R2K b - - 0 1`. |
| TC_14 | SLChessEngineTest.TC_14 | R-4 | The R-4 whole FENs, not a placement fragment: `h1g1` drops `K`; `e1e2` drops `KQ`; `a7a8` on the queen FEN drops `q` and returns `Q3k2r/8/8/8/8/8/8/R3K2R b KQk - 0 1`. |
| TC_15 | SLChessControllerTest.TC_15 | R-6, R-5 | Fool's mate through `SLChessController.legalMoves`, `applyMove`, and `status` only. Each ply is in that position's legal list. Final FEN and `checkmate` match TC_5. |
| TC_16 | SLChessControllerTest.TC_16 | R-6, R-5 | Scholar's mate the same way. Final FEN matches TC_6. |
| TC_17 | SLChessControllerTest.TC_17 | R-6, NFR-1 | Opera game, the 33 plies in R-6, through the controller, one transaction. Final status `checkmate`. `Limits.getCpuTime()` is under 10000. |
| TC_18 | SLChessControllerTest.TC_18 | R-6 | Controller `legalMoves(start)` equals the engine list, and controller `status(start)` is `ongoing`. |
| TC_19 | SLChessBudgetTest.TC_19 | R-3, NFR-1 | Position 6 has 46 legal moves. `Limits.getCpuTime()` after that call is under 2000, the strategy's reading of "well inside" 10000. Revisit the 2000 if a correct engine exceeds it. |
| TC_20 | SLChessBudgetTest.TC_20 | NFR-1 | Depth 2 from the start position: sum of legal replies is 400. `Limits.getCpuTime()` is under 10000. |

UI-1 is not in this table's Apex classes. It is the opt-in browser procedure in architecture.md. The default commands pass without a browser.

## ID convention

An ID is the Apex method name: `TC_1` through `TC_20`. The printed tap token is `Class.TC_1`, so the ID is the whole method name. Do not append a suffix (`TC_1_start` would hide `TC_1`). Hyphens are illegal in Apex identifiers. UI-1 and TC_META and TC_DEPLOY are not Apex methods. The test classes are the home of TC_1–TC_20 once they exist; until then this table is the list. No ID is taken: the checkout has no tests.

## Platform facts

- The checkout has no code, README, AGENTS, or skills. No house style exists. The first implementation sets naming and test shape on purpose. Checked at `b3d6a2137d25`.
- Naming already taken in the org, so this project must not reuse or retrieve them: Apex `SLBattleEngine`, `SLBattleController`, `SLBattleEngineTest`, `SLBattleGameTest`, `SLBattleRulesTest`; LWC `slBattleBoard` and `chess`; tabs `SLBattle_Board`, `Chess`, `Chess_Game__c`; apps `Chess` and `SLBattle`; flexipage `Chess_Game_Record_Page`. `SLChess*` and `slChessBoard` were absent. Source: metadata section of `run/scratch/org-read.json`.
- Allowed new metadata, from the request: Apex classes `SLChess...`, LWC `slChessBoard`, tab `SLChess_Board`, app `SLChess`, and at most one `SLChess_` flexipage. No objects, fields, permission sets, static resources, triggers, profiles, labels, or flows, and no profile or permission-set edits.
- `.sf/` and `.sfdx/` must be gitignored when the project is created. Source: platform guide, Tool state. Proposal until the files exist.
- Apex here does no SOQL or DML. Sharing, object CRUD, and FLS are not applicable. AuraEnabled methods run for the Lightning user; tests and the grader run as the logged-in System Administrator. Do not add user-mode queries to satisfy a rule that has no data.
- Game state is the FEN string. The LWC holds it in memory for one screen until New game or reload. Apex is the rules authority and stores nothing. No cache, queue, or custom object.
- Synchronous Apex CPU limit is 10,000 ms and heap is 6 MB per transaction (Salesforce governor-limits page, cited in `run/notes/research.md`). One middlegame `legalMoves`, one depth-2 enumeration, and about 35 plies through `SLChessController` must each finish in one transaction.
- Move generation will be an in-process integer mailbox. The public boundary stays a FEN string. No chess library and no call into the org's existing `chess` component.

## Access and accounts

- Discovery operator and deploy identity: alias `de`, user id `005000000000000AAA`, profile System Administrator, active. Username is the `de` row in `run/scratch/org-read.json`. This is the CLI user, not a separate end-user role.
- End users of the board are two people on that same Lightning session. The grader is anonymous Apex in one transaction, using the same org user.
- Grant: the request names alias `de` and `sf project deploy start --target-org de`. Scope is this run, this project's metadata only, no destructive changes. Recorded in `run/notes/environment-lifecycle.md`.
- Open item: whether the System Administrator can open a new tab without a profile or permission-set edit. Prepare re-read the user `005000000000000AAA`: profile System Administrator (`run/scratch/prepare-user.txt`), 12 permission-set assignments, including `Chess_User` and `SLBattle_Access` (`run/scratch/prepare-permsets.txt`). Those sets grant `Chess` and `SLBattle_Board` as `DefaultOn` (`run/scratch/prepare-sibling-tabs.txt`). A new `SLChess` permission set is forbidden. After deploy, the visibility read is `PermissionSetTabSetting` for `Name` `SLChess_Board` on this user's sets. No row means hidden. Gate: release-check. `play-on-board` at release-verify still needs a person. Apex grading does not depend on that row.
- Open item: browser front door. `sf org open` is not an allowed command and prints a session URL. Who can grant a look: a person already in the org. Gate: release-verify. No login is missing for the CLI reads already done.

## Skills

- No repository skill, `SHIPLOOP.md`, or README. No fit. Source: empty tree in `run/scratch/baseline-find.txt`.
