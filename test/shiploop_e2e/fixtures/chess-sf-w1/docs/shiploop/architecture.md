# SLChess architecture

No product code exists yet. The checkout baseline has no tests (`run/scratch/baseline-find.txt`): missing coverage, not a failed suite.

## Decisions

### AD-1 Integer mailbox

The engine keeps a position as squares 0–63 with make/unmake and an attack test. FEN is parsed and emitted only at `SLChessEngine`'s public methods. `legalMoves` does not build a FEN per node.

Chosen so one middlegame `legalMoves`, a depth-2 walk of the start position (400 replies), and the 33-ply Opera game each finish inside one synchronous Apex transaction (10,000 ms CPU). Rejected: rebuilding a FEN string at every node. No chess library and no call into the org's existing `chess` component.

Kiwipete depth 2 (2039) is not a required check.

### AD-2 Project placement

Apex, the LWC, and the three metadata files live under `force-app/main/default` at the worktree root, next to `sfdx-project.json` (`sourceApiVersion` 68.0). Class files are `SLChess*.cls`. The bundle directory is `lwc/slChessBoard`. `.gitignore` lists `.sf/` and `.sfdx/`.

Chosen because the request puts the DX root in the checkout and the platform guide keeps CLI state out of Git. Rejected: a nested project folder, and reusing the org's `chess` or `SLBattle` names.

### AD-3 No stored game

The only position carrier is the FEN string. Apex stores no rows. The component holds one FEN in memory until New game or reload.

Chosen because two people share one screen and the request forbids custom objects. Rejected: a custom object, platform cache, or a second browser.

### AD-4 One-screen board

`slChessBoard` is a simple board: square buttons, turn and status as text, a piece click then a destination click, queen as the only promotion, and a New game button. It calls `SLChessController` with a request and renders the response. No animation, polling, or push channel.

Chosen because the request asks for a simple board. The default ambitious UI (drag, animation, keyboard paths) is scaled back for that sentence. Rejected: a chess library and a live channel. Status: accepted.

## Stack

Apex and Lightning Web Components on API 68.0, Salesforce CLI 2.154.4, org alias `de`. No Node app, no Jest, no third-party chess library.

## Structure

| Path | Owner |
| --- | --- |
| `sfdx-project.json`, `.gitignore` | W1 |
| `force-app/main/default/classes/SLChessEngine.cls` and `SLChessEngineTest.cls`, `SLChessBudgetTest.cls` | W1 |
| `force-app/main/default/classes/SLChessController.cls` and `SLChessControllerTest.cls` | W2 |
| `force-app/main/default/lwc/slChessBoard`, `tabs/SLChess_Board.tab-meta.xml`, `applications/SLChess.app-meta.xml`, `flexipages/SLChess_Board.flexipage-meta.xml` | W3 |

W1, W2, and W3 all write `force-app`. The queue is serial, so they do not edit it at the same time. W2 calls the engine and does not rewrite its rules. W3 imports the controller and does not rewrite Apex rules.

## Conventions

Apex methods that the grader calls are the names in the spec. Test methods are `TC_1` through `TC_20` with no suffix. UCI moves and whole FEN strings are the oracles in `docs/shiploop/spec.md`. Inner-loop test commands use `--result-format tap`. The human commands are run beside them.

## Interfaces and boundaries

- `SLChessEngine`: public static methods, FEN in, FEN or move list or status out. `IllegalMoveException` is the illegal-move result. No SOQL, no DML, no rows.
- `SLChessController`: the only AuraEnabled surface. It delegates to the engine. The grader calls it with legal moves only.
- `slChessBoard`: holds the current FEN in the browser until New game or reload. It renders what the controller returns. It does not store a game in the org.
- Metadata boundary: tab `SLChess_Board`, app `SLChess`, flexipage `SLChess_Board`. Nothing else.

Sharing, CRUD, and FLS do not apply: there is no query and no record.

## State and data

The position carrier is the FEN string. Apex stores nothing. The LWC holds one FEN in memory for the people at that screen.

| Carrier | Before | After a legal move | After an illegal move | After New game |
| --- | --- | --- | --- | --- |
| Caller FEN | the string passed in | the string `applyMove` returns | the previous string (the engine throws) | `startFen()` |
| Org rows | none | none | none | none |

Partial failure: an exception returns no FEN. There is no recovery record. Checks: TC_2, TC_5, TC_8, TC_10, TC_15. No cache, queue, or async job, so there is no invalidation or reconciliation check.

## Real-boundary checks

Every row is planned. None has been run against the product. Observation today is only the runner probe and the browser-tool probe.

| ID | Where it runs | Target | Requirement | Due | Status |
| --- | --- | --- | --- | --- | --- |
| TC_1–TC_14 | Remote-resident Apex, `sf apex run test` | org `de` after deploy | R-2, R-3, R-4, R-5 | `test` of the engine item, then `system-test` | planned |
| TC_15–TC_18 | same | same | R-6, NFR-1 Opera | `test` of the controller item, then `system-test` | planned |
| TC_19–TC_20 | same | same | R-3 position 6, NFR-1 | `test` of W1, then `system-test` | planned |
| TC_META | Local shell in the worktree | source files | R-1, R-8, NFR-4 | `verify` of the metadata item | planned; probed exit 2 on the empty tree (`run/scratch/probe-meta-files.txt`). Requires `<uiType>Lightning</uiType>`, Standard `<navType>`, `<tabs>SLChess_Board</tabs>`, the flexipage component name, an `SLChess` class prefix, and `.sf/` plus `.sfdx/` in `.gitignore`. |
| TC_NFR2 | Read of source and command logs | the project | NFR-2 | `verify` | planned; no token scan is claimed green |
| TC_UI_SOURCE | Read of `slChessBoard.html` | the template | NFR-6 | `verify` | planned; the file does not exist yet. Confirms turn text, the status words, and square buttons. Does not close UI-1. |
| TC_DEPLOY | CLI against org `de` | this project's metadata only | R-10, NFR-5 | `system-test` deploy, then `release` | planned |
| TC_TAB | `sf org list metadata --metadata-type CustomTab --target-org de` | CustomTab `SLChess_Board` | R-8 | `release-check` (expect absent), then after `release` | planned |
| UI-1 | Browser, opt-in, not in the default suite | `/lightning/n/SLChess_Board` in app `SLChess` | R-7, NFR-3, NFR-6 | `release-verify` | blocked: no browser tool |

Remote framework: Apex tests already in the org, invoked by Salesforce CLI 2.154.4. Definitions live in the project as `SLChess...Test` classes and are installed by `sf project deploy start --target-org de`. The runner probe (`run/scratch/probe-apex-human.txt`, `run/scratch/probe-apex-tap.txt`) exited 1 with `INVALID_INPUT` because `SLChessEngineTest` is not in the org. That shows the CLI accepts `--class-names`, `--synchronous`, `--result-format human`, `--result-format tap`, and `--code-coverage`. It is not a product pass.

A local Jest suite is not selected. The request's proof is org Apex, and there is no LWC Jest harness in the checkout. Source reading of the component template checks NFR-6's text labels at `verify`; it does not close UI-1.

### UI-1 procedure

Start: a person who can already see the `SLChess` app, on org `de`, at `/lightning/n/SLChess_Board`, with the deployed component. This host cannot reach that start. `search_tool` found no browser tool (`run/scratch/probe-browser.txt`). `sf org open` is not used. The stand-in page was not opened.

When a browser tool exists, the actions are: New game; read White to move and `ongoing`; click the e2 piece, then e4; read the board as the FEN after `e2e4` and Black to move; click a destination that is not in `legalMoves` and read the same FEN; promote a pawn and read a queen on the last rank; reach the stalemate FEN only if the controller can be driven there, and read the word `stalemate`. Oracle: the FENs in R-4 and the words in R-2. Owner: `release-verify`. Cleanup: New game, no org data.

Tab visibility may still block the start after deploy, because this request forbids permission sets and profile edits. Owner of that grant: a Salesforce admin, not this run. Gate: `release-check`. Apex grading does not wait on it.

`sf org list metadata --metadata-type CustomTab --target-org de` lists the existing tabs `Chess` and `SLBattle_Board`. Filtered by parent, `PermissionSetTabSetting` shows `Chess` is `DefaultOn` on `Chess_User` and `SLBattle_Board` is `DefaultOn` on `SLBattle_Access` (`run/scratch/prepare-sibling-tabs.txt`). A name filter that returned no rows was the wrong probe. The logged-in System Administrator holds both permission sets (`run/scratch/prepare-permsets.txt`). This run still must not create a permission set. After deploy, read `PermissionSetTabSetting` for `Name` `SLChess_Board` on this user's permission sets. No row means the tab stays hidden. A4 stays open. UI-1 still needs a person at `/lightning/n/SLChess_Board`.

### Not selected

- Security test and fuzz: not applicable. There is no stored record, no second user, and no network parser. Illegal moves are TC_2 and TC_9, not a fuzzer.
- Dependency updater: not applicable. No third-party chess library. The CLI is the platform tool already logged in.
- Cache, async, and reconciliation: not applicable. No wire cache and no job.
