# Chess engine spec

No prior product requirements exist. Every ID below is added from the user request. Nothing is retired.

## Requirements

### R-1 Project shape

Basis: request sentences on the Node.js module. The project root holds `package.json` (CommonJS, no dependencies, `npm test` runs `node --test`) and `src/chess.js`; tests live in `test/`.

- Positive: those paths exist and `require('./src/chess')` exports `startFen`, `legalMoves`, `applyMove`, `status` and `IllegalMoveError`. Confirmed by a `node --test` case.
- Failure: n/a: a missing export is the same miss as the positive check.
- Boundary: `package.json` has no dependencies. Confirmed by reading it.
- Surface: the checkout.

### R-2 Engine position API

Basis: request sentences for the `src/chess.js` functions and FEN. `src/chess.js` exports only functions and `IllegalMoveError`. A position is a FEN string.

`startFen()` returns `rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1`.

`legalMoves(fen)` returns every legal UCI move for the side to move, sorted alphabetically. Examples: `e2e4`, `e7e8q`.

`applyMove(fen, move)` returns the FEN after a legal move.

`status(fen)` returns `ongoing`, `check`, `checkmate`, or `stalemate` for the side to move.

- Positive: start position has 20 moves, the first alphabetically is `a2a3` and the last is `h2h4`, and `status` is `ongoing`. Confirmed by a `node --test` case.
- Failure: a move absent from `legalMoves` makes `applyMove` throw `IllegalMoveError` and leaves no partial FEN. Confirmed by calling `applyMove` with `e2e5` on the start FEN.
- Boundary: an already-finished position has an empty move list. Stalemate FEN `7k/5Q2/6K1/8/8/8/8/8 b - - 0 1` returns `stalemate`. The fool's-mate position `rnb1kbnr/pppp1ppp/4p3/8/6Pq/5P2/PPPPP2P/RNBQKBNR w KQkq - 1 3` returns `checkmate`. Check with a reply: `4k3/8/8/8/8/8/4q3/4K3 w - - 0 1` returns `check`, and `e1e2` is legal. Confirmed by `node --test` cases.
- Surface: `src/chess.js`.

State: the FEN string is the whole position. The module stores nothing. Before a call the caller holds the FEN; after `applyMove` the caller holds the returned FEN. A thrown exception means the caller keeps the previous FEN. No recovery record exists.

### R-3 Piece moves

Basis: request sentence listing piece moves, castling, en passant, promotion, check, checkmate, and stalemate. Research Q-uci and Q-perft.

Legal moves include ordinary king, queen, rook, bishop, knight, and pawn moves; pawn captures; double pawn steps from the second rank; promotion to `q`, `r`, `b`, or `n`; en passant; and castling `e1g1`, `e1c1`, `e8g8`, `e8c8` only when the side has the right, the squares between are empty, and the king does not leave, cross, or enter check. A pinned piece may not move if the king would be exposed. The king may not move adjacent to the other king.

- Positive: Kiwipete `r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1` has 48 legal moves, including `e1g1` and `e1c1`. Position 3 `8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1` has 14. Position 4 `r3k2r/Pppp1ppp/1b3nbN/nP6/BBP1P3/q4N2/Pp1P2PP/R2Q1RK1 w kq - 0 1` has 6. Position 6 `r4rk1/1pp1qppp/p1np1n2/2b1p1B1/2B1P1b1/P1NP1N2/1PP1QPPP/R4RK1 w - - 0 10` has 46. Confirmed by `node --test` cases comparing list size and membership.
- Failure: from `4r1k1/8/8/8/8/8/8/R3K2R w KQ - 0 1` the list has no `e1g1` (king is in check). From `5rk1/8/8/8/8/8/8/R3K2R w KQ - 0 1` it has no `e1g1` (f1 is attacked). From `6r1/8/8/8/8/8/8/R3K2R w KQ - 0 1` it has no `e1g1` (g1 is attacked). From `r3k2r/8/8/8/8/8/8/R3K2R w Qkq - 0 1` the path is clear and the king is safe, and the list still has no `e1g1` because the right is absent. From `r3k2r/8/8/8/8/8/8/R3K2R w Kkq - 0 1` it has no `e1c1`. From `8/8/8/8/8/4k3/8/4K3 w - - 0 1` the list has no `e1e2` (the kings would touch). From `4k3/4b3/8/8/8/8/8/4R2K b - - 0 1` no legal move starts with `e7` (the bishop is pinned to the king on e8 by the rook on e1). Confirmed by `node --test` cases.
- Boundary: from `k7/4P3/8/8/8/8/8/4K3 w - - 0 1` the list contains `e7e8q`, `e7e8r`, `e7e8b`, and `e7e8n`, and no bare `e7e8`. Confirmed by a `node --test` case.
- Surface: `legalMoves`.

### R-4 FEN after a move

Basis: request sentences for castling rights, en passant, halfmove clock, fullmove number, and the FEN-spec en-passant convention. Research Q-fen.

After `e2e4` from the start FEN the result is `rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1`, including `e3` even though no black pawn can capture it. A later quiet move clears the en-passant square. A capture or pawn move sets the halfmove clock to 0; any other move increments it. The fullmove number increments only after Black's move. Castling rights are a subset of `KQkq` in that order, or `-`. Kingside castling moves the rook from h1 to f1 (or h8 to f8). Queenside castling moves the rook from a1 to d1 (or a8 to d8). An en-passant capture removes the pawn that just stepped two squares, not a piece on the target square.

- Positive: the `e2e4` FEN above. Black's reply `e7e5` returns `rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq e6 0 2`, with `e6` set even though no white pawn can capture it. Black's quiet reply `g8f6` instead returns `rnbqkb1r/pppppppp/5n2/8/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 1 2`, with the en-passant square cleared and the halfmove clock at 1. From `4k3/8/8/8/3p4/8/4P3/4K3 w - - 0 1`, `e2e4` returns `4k3/8/8/8/3pP3/8/8/4K3 b - e3 0 1`, and `d4e3` then returns `4k3/8/8/8/8/4p3/8/4K3 w - - 0 2`. From `r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1`, `e1g1` returns `r3k2r/8/8/8/8/8/8/R4RK1 b kq - 1 1`, `e1c1` returns `r3k2r/8/8/8/8/8/8/2KR3R b kq - 1 1`, `h1g1` returns `r3k2r/8/8/8/8/8/8/R3K1R1 b Qkq - 1 1` (the h1 rook moved, so `K` is gone), and `e1e2` returns `r3k2r/8/8/8/8/8/4K3/R6R b kq - 1 1` (the king moved, so both white rights are gone). From `r3k2r/8/8/8/8/8/8/R3K2R b KQkq - 0 1`, `e8g8` returns `r4rk1/8/8/8/8/8/8/R3K2R w KQ - 1 2` and `e8c8` returns `2kr3r/8/8/8/8/8/8/R3K2R w KQ - 1 2`. From `r3k2r/Q7/8/8/8/8/8/R3K2R w KQkq - 0 1`, `a7a8` returns `Q3k2r/8/8/8/8/8/8/R3K2R b KQk - 0 1` (the a8 rook was captured, so `q` is gone). From `k7/4P3/8/8/8/8/8/4K3 w - - 0 1`, `e7e8q` returns `k3Q3/8/8/8/8/8/8/4K3 b - - 0 1`, `e7e8r` returns `k3R3/8/8/8/8/8/8/4K3 b - - 0 1`, `e7e8b` returns `k3B3/8/8/8/8/8/8/4K3 b - - 0 1`, and `e7e8n` returns `k3N3/8/8/8/8/8/8/4K3 b - - 0 1`. Confirmed by `node --test` cases comparing the whole FEN.
- Failure: n/a: an illegal move never returns a FEN (R-2).
- Boundary: promoting and castling both update placement and clocks in the same returned string. Confirmed by the same tests.
- Surface: `applyMove`.

### R-5 Known games

Basis: request sentence requiring fool's mate and scholar's mate. Research Q-games.

Fool's mate, ply by ply from `startFen()`: `f2f3`, `e7e6`, `g2g4`, `d8h4`. The FEN is then `rnb1kbnr/pppp1ppp/4p3/8/6Pq/5P2/PPPPP2P/RNBQKBNR w KQkq - 1 3`. Status is `checkmate` and the move list is empty.

Scholar's mate: `e2e4`, `e7e5`, `f1c4`, `b8c6`, `d1h5`, `g8f6`, `h5f7`. The FEN is then `r1bqkb1r/pppp1Qpp/2n2n2/4p3/2B1P3/8/PPPP1PPP/RNB1K1NR b KQkq - 0 4` (published final position). Status is `checkmate`. d8 is blocked by Black's queen, so it is not a flight square.

Each ply is a member of `legalMoves` of the position before it.

- Positive: both sequences end at the FENs named above with status `checkmate`. Confirmed by a `node --test` case that walks them with `applyMove` and compares each final FEN and `status`.
- Failure: stopping one ply early is not mate. After `f2f3 e7e6 g2g4` Black is to move and is not in check, so status is `ongoing`, and `d8h4` is legal. Confirmed by the same test.
- Boundary: n/a: the sequences are the boundary.
- Surface: `src/chess.js`.

## Transitions

| ID | Before | Trigger | After | Failure |
| --- | --- | --- | --- | --- |
| T-1 | FEN, side to move, `ongoing` or `check` | legal UCI move | new FEN from R-4; status recomputed | n/a |
| T-2 | same | UCI not in `legalMoves` | same FEN | `IllegalMoveError` from the engine; board unchanged |
| T-3 | side to move in check, no legal move | `status` | `checkmate`; no further T-1 | n/a |
| T-4 | side to move not in check, no legal move | `status` | `stalemate`; no further T-1 | n/a |

No durable record, no concurrent writers, no queue.

## Non-functional requirements

- NFR-1 Performance. Operating condition: Node.js 20 or later on one core. `legalMoves` on middlegame `r4rk1/1pp1qppp/p1np1n2/2b1p1B1/2B1P1b1/P1NP1N2/1PP1QPPP/R4RK1 w - - 0 10` returns within 50 ms; a depth-2 count of the start position (400 replies) returns within 2 seconds. Verified by `node --test` cases that time them with `process.hrtime.bigint()`.
- NFR-2 Compatibility. No third-party chess library and no dependency. Verified by `package.json`.
- Excluded: a board, persistence and anything beyond one call at a time.

## Retired

None.
