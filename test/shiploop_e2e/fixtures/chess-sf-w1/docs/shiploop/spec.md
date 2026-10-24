# SLChess spec

No prior product requirements exist. Discovery found an empty checkout (`run/notes/current-system-baseline.md`). Every ID below is added from the user request (`run/request.md`) and the rules pinned in `run/notes/research.md`. Nothing is retired.

## Requirements

### R-1 Project shape

Basis: request sentences on the Salesforce DX root, `SLChess` class names, and `slChessBoard`. Preserve: none. Pending: the files themselves.

The project root is the checkout root and contains `sfdx-project.json` and `force-app/`. Every Apex class name starts with `SLChess`. The component bundle is `slChessBoard`. `sourceApiVersion` is 68.0, matching existing Apex in org `de` (`run/scratch/apex-api.json`).

- Positive: those paths exist and no Apex class name lacks the prefix. Confirmed by listing `force-app` after implementation.
- Failure: n/a: a missing file is the same miss as the positive check.
- Boundary: the root is not a subfolder. Confirmed by the same listing.
- Surface: the returned source checkout.

### R-2 Engine position API

Basis: request sentences for `SLChessEngine` static methods and FEN. `SLChessEngine` is public and has only static methods. A position is a FEN string.

`startFen()` returns `rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1`.

`legalMoves(String fen)` returns every legal UCI move for the side to move, sorted alphabetically. Examples: `e2e4`, `e7e8q`.

`applyMove(String fen, String move)` returns the FEN after a legal move.

`status(String fen)` returns `ongoing`, `check`, `checkmate`, or `stalemate` for the side to move.

- Positive: start position has 20 moves, the first alphabetically is `a2a3` and the last is `h2h4`, and `status` is `ongoing`. Confirmed by an org Apex test.
- Failure: a move absent from `legalMoves` makes `applyMove` throw `SLChessEngine.IllegalMoveException` and leaves no partial FEN. Confirmed by calling `applyMove` with `e2e5` on the start FEN.
- Boundary: an already-finished position has an empty move list. Stalemate FEN `7k/5Q2/6K1/8/8/8/8/8 b - - 0 1` returns `stalemate`. The fool's-mate position `rnb1kbnr/pppp1ppp/4p3/8/6Pq/5P2/PPPPP2P/RNBQKBNR w KQkq - 1 3` returns `checkmate`. Check with a reply: `4k3/8/8/8/8/8/4q3/4K3 w - - 0 1` returns `check`, and `e1e2` is legal. Confirmed by org tests.
- Surface: `SLChessEngine` in org `de`.

State: the FEN string is the whole position. Apex stores nothing. Before a call the caller holds the FEN; after `applyMove` the caller holds the returned FEN. A thrown exception means the caller keeps the previous FEN. No recovery record exists.

### R-3 Piece moves

Basis: request sentence listing piece moves, castling, en passant, promotion, check, checkmate, and stalemate. Research Q-uci and Q-perft.

Legal moves include ordinary king, queen, rook, bishop, knight, and pawn moves; pawn captures; double pawn steps from the second rank; promotion to `q`, `r`, `b`, or `n`; en passant; and castling `e1g1`, `e1c1`, `e8g8`, `e8c8` only when the side has the right, the squares between are empty, and the king does not leave, cross, or enter check. A pinned piece may not move if the king would be exposed. The king may not move adjacent to the other king.

- Positive: Kiwipete `r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1` has 48 legal moves, including `e1g1` and `e1c1`. Position 3 `8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1` has 14. Position 4 `r3k2r/Pppp1ppp/1b3nbN/nP6/BBP1P3/q4N2/Pp1P2PP/R2Q1RK1 w kq - 0 1` has 6. Position 6 `r4rk1/1pp1qppp/p1np1n2/2b1p1B1/2B1P1b1/P1NP1N2/1PP1QPPP/R4RK1 w - - 0 10` has 46. Confirmed by org tests comparing list size and membership.
- Failure: from `4r1k1/8/8/8/8/8/8/R3K2R w KQ - 0 1` the list has no `e1g1` (king is in check). From `5rk1/8/8/8/8/8/8/R3K2R w KQ - 0 1` it has no `e1g1` (f1 is attacked). From `6r1/8/8/8/8/8/8/R3K2R w KQ - 0 1` it has no `e1g1` (g1 is attacked). From `r3k2r/8/8/8/8/8/8/R3K2R w Qkq - 0 1` the path is clear and the king is safe, and the list still has no `e1g1` because the right is absent. From `r3k2r/8/8/8/8/8/8/R3K2R w Kkq - 0 1` it has no `e1c1`. From `8/8/8/8/8/4k3/8/4K3 w - - 0 1` the list has no `e1e2` (the kings would touch). From `4k3/4b3/8/8/8/8/8/4R2K b - - 0 1` no legal move starts with `e7` (the bishop is pinned to the king on e8 by the rook on e1). Confirmed by org tests.
- Boundary: from `k7/4P3/8/8/8/8/8/4K3 w - - 0 1` the list contains `e7e8q`, `e7e8r`, `e7e8b`, and `e7e8n`, and no bare `e7e8`. Confirmed by an org test.
- Surface: `SLChessEngine.legalMoves` in org `de`.

### R-4 FEN after a move

Basis: request sentences for castling rights, en passant, halfmove clock, fullmove number, and the FEN-spec en-passant convention. Research Q-fen.

After `e2e4` from the start FEN the result is `rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1`, including `e3` even though no black pawn can capture it. A later quiet move clears the en-passant square. A capture or pawn move sets the halfmove clock to 0; any other move increments it. The fullmove number increments only after Black's move. Castling rights are a subset of `KQkq` in that order, or `-`. Kingside castling moves the rook from h1 to f1 (or h8 to f8). Queenside castling moves the rook from a1 to d1 (or a8 to d8). An en-passant capture removes the pawn that just stepped two squares, not a piece on the target square.

- Positive: the `e2e4` FEN above. Black's reply `e7e5` returns `rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq e6 0 2`, with `e6` set even though no white pawn can capture it. Black's quiet reply `g8f6` instead returns `rnbqkb1r/pppppppp/5n2/8/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 1 2`, with the en-passant square cleared and the halfmove clock at 1. From `4k3/8/8/8/3p4/8/4P3/4K3 w - - 0 1`, `e2e4` returns `4k3/8/8/8/3pP3/8/8/4K3 b - e3 0 1`, and `d4e3` then returns `4k3/8/8/8/8/4p3/8/4K3 w - - 0 2`. From `r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1`, `e1g1` returns `r3k2r/8/8/8/8/8/8/R4RK1 b kq - 1 1`, `e1c1` returns `r3k2r/8/8/8/8/8/8/2KR3R b kq - 1 1`, `h1g1` returns `r3k2r/8/8/8/8/8/8/R3K1R1 b Qkq - 1 1` (the h1 rook moved, so `K` is gone), and `e1e2` returns `r3k2r/8/8/8/8/8/4K3/R6R b kq - 1 1` (the king moved, so both white rights are gone). From `r3k2r/8/8/8/8/8/8/R3K2R b KQkq - 0 1`, `e8g8` returns `r4rk1/8/8/8/8/8/8/R3K2R w KQ - 1 2` and `e8c8` returns `2kr3r/8/8/8/8/8/8/R3K2R w KQ - 1 2`. From `r3k2r/Q7/8/8/8/8/8/R3K2R w KQkq - 0 1`, `a7a8` returns `Q3k2r/8/8/8/8/8/8/R3K2R b KQk - 0 1` (the a8 rook was captured, so `q` is gone). From `k7/4P3/8/8/8/8/8/4K3 w - - 0 1`, `e7e8q` returns `k3Q3/8/8/8/8/8/8/4K3 b - - 0 1`, `e7e8r` returns `k3R3/8/8/8/8/8/8/4K3 b - - 0 1`, `e7e8b` returns `k3B3/8/8/8/8/8/8/4K3 b - - 0 1`, and `e7e8n` returns `k3N3/8/8/8/8/8/8/4K3 b - - 0 1`. Confirmed by org tests comparing the whole FEN.
- Failure: n/a: an illegal move never returns a FEN (R-2).
- Boundary: promoting and castling both update placement and clocks in the same returned string. Confirmed by the same tests.
- Surface: `SLChessEngine.applyMove` in org `de`.

### R-5 Known games

Basis: request sentence requiring fool's mate and scholar's mate. Research Q-games.

Fool's mate, ply by ply from `startFen()`: `f2f3`, `e7e6`, `g2g4`, `d8h4`. The FEN is then `rnb1kbnr/pppp1ppp/4p3/8/6Pq/5P2/PPPPP2P/RNBQKBNR w KQkq - 1 3`. Status is `checkmate` and the move list is empty.

Scholar's mate: `e2e4`, `e7e5`, `f1c4`, `b8c6`, `d1h5`, `g8f6`, `h5f7`. The FEN is then `r1bqkb1r/pppp1Qpp/2n2n2/4p3/2B1P3/8/PPPP1PPP/RNB1K1NR b KQkq - 0 4` (published final position). Status is `checkmate`. d8 is blocked by Black's queen, so it is not a flight square.

Each ply is a member of `legalMoves` of the position before it.

- Positive: both sequences end at the FENs named above with status `checkmate`. Confirmed by an org test that walks them with `applyMove` and compares each final FEN and `status`.
- Failure: stopping one ply early is not mate. After `f2f3 e7e6 g2g4` Black is to move and is not in check, so status is `ongoing`, and `d8h4` is legal. Confirmed by the same test.
- Boundary: n/a: the sequences are the boundary.
- Surface: `SLChessEngine` in org `de`.

### R-6 Controller

Basis: request sentences for `SLChessController` AuraEnabled methods and the grader's split between legal and illegal moves.

`legalMoves(String fen)` is `@AuraEnabled public static` and returns `List<String>`. `applyMove(String fen, String move)` is `@AuraEnabled public static` and returns `String`. `status(String fen)` is `@AuraEnabled public static` and returns `String` with the same four words as R-2.

The grader calls the controller only with legal moves. For those, the returned FEN and status match `SLChessEngine`. The controller may reject an illegal move with `AuraHandledException`. The grader calls `SLChessEngine.applyMove` itself for the illegal case.

- Positive: fool's mate, scholar's mate, and the Opera game below, played only through the controller, match the engine. Confirmed by org tests.
- Failure: n/a for the grader: it does not send illegal moves to the controller. The board's refusal is R-7.
- Boundary: one game stays in one Apex transaction. Confirmed by the Opera-game test method, which does not split the game.
- Surface: `SLChessController` in org `de`.

Opera game, 33 plies, from `startFen()`, through the controller: `e2e4 e7e5 g1f3 d7d6 d2d4 c8g4 d4e5 g4f3 d1f3 d6e5 f1c4 g8f6 f3b3 d8e7 b1c3 c7c6 c1g5 b7b5 c3b5 c6b5 c4b5 b8d7 e1c1 a8d8 d1d7 d8d7 h1d1 e7e6 b5d7 f6d7 b3b8 d7b8 d1d8`. Final status `checkmate`.

### R-7 Board

Basis: request sentences for `slChessBoard`. Two people play on one screen. The component renders the FEN as an 8x8 board, shows whose turn it is and the status, takes a piece click then a destination click, refuses a destination that is not in `legalMoves`, promotes a pawn with queen as the default, and has a New game button. It calls `SLChessController` and renders the response.

State: the component holds the current FEN in memory. Both people see the same board; chess has no hidden pieces. New game or leaving the page drops that FEN. There is no saved game and no second browser to reconcile. A refused click does not change the FEN. An Apex error leaves the previous FEN on screen.

- Positive: New game shows the start position and White to move. A legal destination updates the board to the FEN the controller returns and updates turn and status. Confirmed on the `SLChess_Board` tab when a person can open it, and by the controller tests for the data the board renders.
- Failure: an illegal destination leaves the pieces where they were. Confirmed by the same board session.
- Boundary: promotion uses `q` without a chooser. Check, checkmate, and stalemate are visible as those words. Confirmed on the board for a position the controller already classifies.
- Surface: `slChessBoard` in the `SLChess` app. Open gap: tab visibility may be missing because this request forbids permission sets and profile edits. Owner: release-check. Apex play (R-6) does not wait on it.
- Skin premise: Lightning defaults, light and dark squares distinguishable, files a–h and ranks 1–8. No separate design system exists in the repo.

### R-8 Org entry metadata

Basis: request sentences listing the only extra metadata. Files: `tabs/SLChess_Board.tab-meta.xml` with `<lwcComponent>slChessBoard</lwcComponent>`; `applications/SLChess.app-meta.xml` with standard navigation containing that tab; optional `flexipages/SLChess_Board.flexipage-meta.xml`. The component meta exposes `lightning__Tab` and, because the flexipage is included, `lightning__AppPage`.

No custom objects, fields, permission sets, static resources, triggers, profiles, labels, or flows. No edits to profiles or permission sets. Do not change existing `Chess` or `SLBattle` metadata (`docs/shiploop/environment.md`).

- Positive: deploy contains those names and the tab is a Lightning component tab. Confirmed by the deploy file list and `sf org list metadata --metadata-type CustomTab --target-org de` showing `SLChess_Board`.
- Failure: n/a: a forbidden type in the project fails this criterion.
- Boundary: a `<motif>` inside the tab file is still the same CustomTab, not a new metadata type.
- Surface: org `de` after deploy. Entry path `/lightning/n/SLChess_Board`.

### R-9 Org tests

Basis: request sentences for `SLChess...Test`, at least eight methods, and the named cases. Tests run in the org, one class at a time:

`sf apex run test --target-org de --class-names <TestClass> --synchronous --result-format human --code-coverage`

Methods cover fool's mate, scholar's mate, castling, en passant, promotion, stalemate, and the move counts in R-3. At least eight test methods in all.

- Positive: every method in those classes passes. Confirmed by that command's human output, one class at a time.
- Failure: a wrong move count or a non-mate ending fails the method. Confirmed by the same command.
- Boundary: n/a: eight is the minimum, not a cap.
- Surface: org `de`.

### R-10 Delivery

Basis: request sentences to deploy to alias `de` and not stop before the tests pass. Command: `sf project deploy start --target-org de`. Every `sf` command that talks to the org uses `--target-org de`. Never ask for, print, or store credentials, and never run `sf org display`.

- Positive: the deploy command exits success and R-9 then passes. Confirmed by those command results.
- Failure: a failed test keeps the work unfinished. Confirmed by the test output.
- Boundary: the deploy adds this project's metadata only and does not delete unrelated org metadata. Confirmed by the deploy manifest scope.
- Surface: org alias `de`, org id `00D000000000000AAA`.

## Flows

### F-1 Play a ply (R-2, R-6, R-7)

Start: a FEN and a person or the grader. The actor asks `legalMoves`. They choose a move from that list. `applyMove` returns the next FEN. `status` returns the word for that FEN. The board replaces its FEN and labels. An illegal click skips `applyMove`.

### F-2 New game (R-7)

The New game control sets the FEN to `startFen()` and status to `ongoing`.

### F-3 Grade a game (R-5, R-6, R-9)

One anonymous Apex transaction walks a scripted game through the controller only. The illegal-move check uses `SLChessEngine.applyMove` directly.

## Transitions

| ID | Before | Trigger | After | Failure |
| --- | --- | --- | --- | --- |
| T-1 | FEN, side to move, `ongoing` or `check` | legal UCI move | new FEN from R-4; status recomputed | n/a |
| T-2 | same | UCI not in `legalMoves` | same FEN | `IllegalMoveException` from the engine; board unchanged |
| T-3 | side to move in check, no legal move | `status` | `checkmate`; no further T-1 | n/a |
| T-4 | side to move not in check, no legal move | `status` | `stalemate`; no further T-1 | n/a |
| T-5 | any client FEN | New game | start FEN, `ongoing` | n/a |

No durable record, no concurrent writers, no queue. A crashed transaction leaves the org unchanged because Apex holds no chess rows.

## Non-functional requirements

- NFR-1 Performance. Operating condition: one synchronous Apex transaction, 10,000 ms CPU and 6 MB heap (Salesforce governor limits, `run/notes/research.md`). Bounds from the request: `legalMoves` on middlegame `r4rk1/1pp1qppp/p1np1n2/2b1p1B1/2B1P1b1/P1NP1N2/1PP1QPPP/R4RK1 w - - 0 10` finishes well inside that limit; a depth-2 count of the start position (400 replies) finishes in one transaction; the 33-ply Opera game through the controller, with `legalMoves`, `applyMove`, and `status` each ply, finishes in one transaction. Verified by those three Apex tests calling `Limits.getCpuTime()` and completing. Kiwipete depth 2 is not required.
- NFR-2 Security and privacy. No credentials in source, logs, or notes. No `sf org display`. No business records. FEN is not secret. Verified by review of the project and of command output.
- NFR-3 Access. The board should open for the System Administrator. The request forbids the permission-set and profile edits that usually grant a new tab. Unresolved for the UI only; see R-7. Apex tests do not need that grant.
- NFR-4 Compatibility. Apex and LWC on API 68.0 in a Developer Edition. No third-party chess library. Verified by `sfdx-project.json` and the absence of static resources.
- NFR-5 Operability. Deploy and test commands are the ones in R-9 and R-10. Rollback is removing the `SLChess` metadata later; this run does not delete it. Verified by the deploy result.
- NFR-6 Accessibility. The board shows turn and status as text, not color alone, and squares are buttons with piece and coordinate names. Verified by reading the component template. No WCAG level was requested; none is invented.
- Excluded: availability SLA, multi-user sync, saved games, and load beyond one transaction. The request is one screen and one Apex game at a time.

## Retired

None. There was no earlier requirement list.
