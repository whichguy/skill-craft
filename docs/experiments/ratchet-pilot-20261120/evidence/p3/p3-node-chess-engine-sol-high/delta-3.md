# Closing look

Read the request, specification, plan, all three build and test reports, both earlier deltas, the README, and the engine and test sources. The third build report lists no unfinished work and the third test report lists no failures. The folder contains no fix or referee reports.

Ran `npm test` (39 passed) and the five existing acceptance suites (138 passed). Through the CommonJS API, replayed the README opening, both named mates, stalemate, all four castles, promotion, and en passant. Checked illegal UCI and retry, malformed FEN around eight-square rank width and minimum counters, halfmove clocks around 100 and 150, and exact counter updates around JavaScript's safe-integer limit. Tried occupied and expired en-passant targets, a target shared by two pawns with different king-safety outcomes, and an imported position in which taking en passant would erase a pre-existing attack on the pusher's king. Resumed FENs with both live and cleared special-move fields in fresh Node.js processes.

Measured 48 Kiwipete moves in 0.046 ms and 400 start-position two-ply paths in 0.998 ms. Also counted 8,902 paths at start depth three and 2,039 at Kiwipete depth two.

## Added clause

- C-106 — product keeps to it: yes. Replayed `b7b5 c5b6` and the color-reversed `b2b4 c4b3`. In each case the push blocked check and recorded its midpoint. The saved FEN alone gave the same legal capture in a fresh process, and the capture cleared the target and restored check. In both cases manually clearing the target removed the capture from the legal moves.
