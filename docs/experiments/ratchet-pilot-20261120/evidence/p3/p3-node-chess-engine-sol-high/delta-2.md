# Closing look

Read the request, specification, plan, both build and test reports, the previous delta, the README, and the engine and test sources. The stage reports list no unfinished work or failing checks. There were no fix or referee reports in `ratchet/`.

Ran `npm test` (34 passed) and the five existing acceptance suites (130 passed). Used the CommonJS API to replay the README example, both named mates, stalemate, all four castles, and quiet and capture promotions. Checked malformed FEN and exact UCI rejection, retry and branching, rank widths around eight squares, the minimum counter values, halfmove draw thresholds, and counters around JavaScript's safe-integer limit. Exercised expired, occupied, replaced, and usable en-passant targets, checked and blocked castling rights, and stale metadata for both colors. Resumed saved FENs in a fresh Node.js process and compared status, legal moves, and the resulting FEN.

Measured a full Kiwipete call at 0.907 ms for 48 moves and a full start-position depth-two traversal at 3.061 ms for 400 paths. Also checked 8,902 paths at start depth three and 2,039 at Kiwipete depth two.

The third and fifth occurrences of the starting position in a knight shuffle still reported `ongoing` and allowed the same 20 moves. C-72 already covers independence from game history. The composed diagram with pawns already on their promotion ranks loaded and preserved the pawns. Making that specific impossible board a required import would extend the analysis-position contract beyond the request.

## Added clauses

- C-104 — product keeps to it: yes. The first `a2a3` returned `Q` alone, dropping both inactive black flags and preserving the blocked white right. A fresh process continued from that FEN with the same rights. A separate position also dropped an inactive flag whose rook was missing before the first move.
- C-105 — product keeps to it: no. The engine refused `d7d5` from `4k3/3p4/2B5/4P3/8/8/8/K7 b - - 0 1` but listed and applied `e5d6` when given the purported result directly. The color-reversed `d2d4` and `e4d3` showed the same discrepancy. Both positions allowed ordinary play, and shifting the bishop off the pin allowed the double push and subsequent en-passant capture for either color.
