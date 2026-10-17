# chess-salesforce-reference

The known-good answer to the `chess-salesforce` E2E case (`test/shiploop_e2e/cases.json`): an Apex chess rules engine, its
`@AuraEnabled` controller, Apex tests, a Lightning web component board, a Lightning tab and a Lightning app, all carrying the case
prefix (`SLChess` / `slChess`).

**Nothing in this folder is ever shown to a model.** It is the harness's own fixture: the case prompt is all a model sees, and a model's
working directory never contains this folder. Do not copy it into a case workspace, a prompt or a packet.
Known limit: a host with file access could still read it from the checkout; the main session greps the run's commands for
`chess-salesforce-reference` to see whether one did.

## What it is for

- It is the first thing the real checks (`project`, `deployed`, `tests`, `rules`) run against, so a wrong oracle or limit shows up here
  instead of as a failed 90-minute model run that looks like an engine failure (`chess_salesforce.py selftest --reference`; real org:
  main session only).
- Deployed to the real Developer Edition org it is a playable board: the tab opens at `/lightning/n/SLChess_Board` and the app is
  `SL Chess` in the App Launcher. Whether either is visible to the owner's profile without a profile change is unproven until a
  run has deployed it; the case never touches profiles or permission sets. Keep-or-clean decides whether it stays in the org.

## Status of the Apex

There is no Apex runtime in this repository, so Salesforce has not compiled or run this Apex. Before its first real deploy it was
cross-checked by translating the source text mechanically (a throwaway tool, not kept) to TypeScript, type-checking it and running it
under Node. All 26 Apex test methods, every `rules` script of the grader as it stood when this was written (19 scripts, 28 markers), the
published perft counts below to depth 4, and 30,769 random-game positions compared move for move with an independent generator agreed.
That proves the logic. It does not prove that Apex compiles: the first real deploy is the proof. If the compiler objects, look first at
the places below.

After that cross-check, `SLChessEngineTest` got one `System.debug('CPU ' + Limits.getCpuTime());` after each of the Kiwipete and
position-5 depth-2 counts, so the first rehearsal can read the real CPU use of the heaviest enumerations from the test log.

## If the first deploy fails, look first at

1. `SLChessEngine.cls`: the two `static final` tables initialised by calling static methods (`SQ_NAMES = buildNames()`,
   `EMPTY_POSITION = buildEmpty()`); `new List<Integer>(otherList)` (the copy constructor); `String.codePointAt`, `String.isNumeric`,
   `String.join`.
2. Identifier rules: Apex is case-insensitive and has reserved words. No local shares a name with a constant or a reserved word as far as
   a checker could tell, but `file`, `rank`, `kind`, `shift`, `home`, `moved`, `blank` and `one` are the names to doubt.
3. `SLChessController.cls`: `AuraHandledException.setMessage` (the message shows in a test only after it is called).
4. The metadata: the tab's `<motif>Custom57: Grid</motif>` (the same value the selftest probe uses, so one measurement settles both; drop
   the element or pick another from the tab-style list if the org refuses it), the app XML, and `apiVersion` / `sourceApiVersion` 68.0.
5. A deploy of Apex to a production-type org can require tests and 75% coverage; these tests should clear that for both classes by a wide
   margin (coverage is not measured offline).

## Files

```
sfdx-project.json                                         sourceApiVersion 68.0, package directory force-app
force-app/main/default/
  classes/SLChessEngine.cls                               the rules (public, static methods, IllegalMoveException inside)
  classes/SLChessController.cls                           public with sharing; legalMoves, applyMove, status (@AuraEnabled)
  classes/SLChessEngineTest.cls                           19 tests: perft, mates, castling, en passant, promotion, stalemate, errors
  classes/SLChessGameTest.cls                             4 tests: whole games, through the engine and again through the controller
  classes/SLChessControllerTest.cls                       3 tests: delegation and AuraHandledException messages
  classes/*.cls-meta.xml                                  apiVersion 68.0, Active
  lwc/slChessBoard/slChessBoard.{html,js,css}             the board: click a piece, then a highlighted destination
  lwc/slChessBoard/slChessBoard.js-meta.xml               exposed; targets lightning__Tab and lightning__AppPage
  tabs/SLChess_Board.tab-meta.xml                         Lightning component tab showing slChessBoard
  applications/SLChess.app-meta.xml                       Lightning app (Standard nav) holding the tab
```

No other metadata type exists here, and none may: the guard and the verification allow exactly ApexClass, LightningComponentBundle,
CustomTab, CustomApplication and FlexiPage, each with the prefix. There is no flexipage in this reference (it is optional in the case).

## How the engine is built

- A position is a `List<Integer>`: a 10 x 12 mailbox board (so every step is a constant offset and an off-board cell stops a ray) plus
  the FEN's other fields in the cells after it. Every public method parses its FEN once and holds no state.
- Moves are generated pseudo-legally as `(from, to, promotion)` integer triples; castling is generated complete (right kept, rook and king
  at home, squares between empty, king not in, through or into check).
- A move is legal when the mover's king is not attacked after playing it on a copy of the position: pins, check evasion and the
  en passant discovered check along a rank all fall out of that one test, with no special cases.
- `applyMove` matches the requested move against the pseudo-legal triples, tests that one move, and updates rights (a rook captured on its
  home square also loses its right), the en passant target (set after every two-square push), both clocks and the side.
- UCI strings are built only for the moves returned, then sorted. No SOQL, no DML, no recursion: Kiwipete depth 2 is about 260 thousand
  list operations, far inside the 10 second synchronous CPU limit.

## Numbers it was designed against

Published perft counts (chessprogramming.org), counted through the public API (`legalMoves` and `applyMove`):

| position | depth 1 | depth 2 | deeper (checked offline only) |
| --- | --- | --- | --- |
| start | 20 | 400 | 8,902; 197,281 |
| Kiwipete | 48 | 2,039 | 97,862 |
| position 3 | 14 | 191 | 2,812; 43,238 |
| position 4 | 6 | 264 | 9,467 |
| position 5 | 44 | 1,486 | 62,379 |
| position 6 | 46 | 2,079 | 89,890 |
| `r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1` | 26 | | |

Games: the Opera Game (33 plies, a queenside castle, checks after plies 21, 29 and 31, mate on ply 33); a 13-ply game with an en passant
capture (ply 5), a promotion by capture (ply 13) and the mate it gives; Sam Loyd's 19-ply stalemate (check after ply 11).
