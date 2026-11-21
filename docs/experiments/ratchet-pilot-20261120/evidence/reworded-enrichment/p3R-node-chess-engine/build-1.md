## Done

- C-1–C-4. Added the dependency-free CommonJS module at `src/chess.js` with the standard start FEN and six-field position parsing.
- C-5–C-21. Implemented sorted UCI generation for all pieces, en passant and promotions, with king-safety checks that account for pinned attackers.
- C-22–C-26. Implemented both castle directions for both colors, checking the right, home pieces, path and attacks on the king's origin, transit and destination.
- C-27–C-38. Implemented the shared board transition and FEN output, including special-move effects, color to move, castling rights, en-passant targets and both move counters.
- C-39–C-44. Exported `IllegalMoveError` and implemented all four position statuses.
- C-45–C-54. Added 17 Node.js rules tests under `test/`, including both named mates, special moves, stalemate and standard move counts. The existing `npm test` script passed all 17 tests. Both JavaScript files passed `node --check`.
- C-55–C-56. Timed the public API on Kiwipete and the standard start. Kiwipete returned 48 moves in 0.570 ms, and the start-position depth-2 traversal counted 400 sequences in 2.024 ms.
- Added `README.md` with the public API, FEN input behavior, UCI examples and test command.

## Not done

none

## Discoveries

- C-4 build choice. The parser checks six FEN fields, rank encodings, king counts, active color, castling and en-passant syntax, and decimal counters. It accepts whitespace between fields and uses the supplied position without validating game history. | Observable: Abbreviated FEN throws `TypeError`. A syntactically valid missing-rook position loads, and the absent rook prevents its castle. | Why: Structural validation lets the APIs use standalone positions, with piece and square checks enforcing each special move.
- C-40 build choice. Move matching is exact and case sensitive. | Observable: With a playable FEN, `E2E4`, ` e2e4 ` and a non-string argument each throw the exported `IllegalMoveError`. | Why: The engine uses the same canonical UCI strings to list and apply moves.
- C-53 build choice. The rules suite checks the standard start at depths one and two (20 and 400) and Kiwipete at the same depths (48 and 2039). | Observable: Run `npm test` and inspect the standard-count test. | Why: Kiwipete adds a dense position with castling and captures to the opening baseline.
- C-55–C-56 build choice. The timing observations use Node.js v26.12.1 on Darwin arm64 with an Apple M5 Max. | Observable: Measure one Kiwipete `legalMoves` call and one start-position depth-2 traversal through `legalMoves` and `applyMove` in separate synchronous `node:perf_hooks` intervals, with fixture setup and assertions outside both intervals. | Why: The timings cover the full public operations, and the rules suite stays independent of machine load.
