# Closing look

Read the original request, `spec.md`, `plan.md`, `build-1.md`, `tests-1.md`, the README, and the engine and test sources. The build reported no unfinished work, and the test report listed no outstanding failures. There were no fix or referee reports in `ratchet/`.

Ran `npm test` (27 passed) and the existing acceptance tests (121 passed). Used the CommonJS API directly to replay the README example, both named mates, stalemate, all four castles, and promotions for both colors. Exercised exact UCI rejection and retry, malformed FEN and rank widths below and above eight, halfmove thresholds at 99–101 and 149–151, and exact counter updates on both sides of JavaScript's safe-integer limit. Checked live and stale special-move fields, an occupied en-passant target, en-passant expiry and check evasion, and a temporarily blocked castle. Passed saved FEN strings to a fresh Node.js process and compared moves, status, and continuations.

Measured a complete Kiwipete call at 0.920 ms for 48 moves and a complete start-position depth-two traversal at 2.979 ms for 400 paths. Also enumerated 8,902 paths at start depth three and 2,039 at Kiwipete depth two.

## Added clauses

- C-97 — product keeps to it: yes. Both stale-field fixtures reported `ongoing`, allowed the ordinary move, and rejected the unavailable special move.
- C-98 — product keeps to it: no. After `h2h1 a8a7` from the stale-flag fixture, the engine returned `8/k7/8/8/8/8/8/4K2R w K - 2 2`, listed `e1g1`, and applied the castle. The same line starting with `-` in the castling field left `e1g1` unavailable. A valid flag with a temporarily occupied path survived the blocker moving away.
- C-99 — product keeps to it: yes. The capture on the occupied target removed the knight and left the pawn on `d5`.
- C-100 — product keeps to it: yes. The capture was available at halfmove clock `12` and reset the clock to `0`.
- C-101 — product keeps to it: yes. The composed position loaded as `ongoing` for White. `e2e7` produced `check` for Black.
- C-102 — product keeps to it: yes. All three APIs accepted the alternate field formatting and `applyMove` emitted the expected FEN.
- C-103 — product keeps to it: yes. All three position APIs rejected `44` and accepted `8` for the empty rank.
