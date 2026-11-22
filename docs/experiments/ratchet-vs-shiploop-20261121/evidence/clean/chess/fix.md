# Fix pass

Baseline before the fix: `npm test` passed 10 of 10.

## Shortfalls

- Malformed FEN can pass as a playable or finished position: fixed. `parseFen` now checks the form of all six FEN fields and throws a plain `Error` starting `Invalid FEN:` from `legalMoves`, `status` and `applyMove` (which now checks the FEN before the move). Test: `TC-9 rejects malformed FEN fields instead of answering for them` (fails without the fix, passes with it).

## Choices documented in README.md ("Behaviour to know about")

- What counts as a malformed FEN, and the error it raises (new with the fix).
- Only the form of the FEN is checked, not whether the position could occur (no king, two kings, pawns on the back rank, side not to move in check, castling rights without their king or rook, unusable en-passant squares).
- FEN whitespace tolerance: surrounding and repeated whitespace (spaces, tabs, newlines) accepted; output uses single spaces.
- UCI whitespace tolerance: the move string must be exact; whitespace, upper case or a non-string throws `IllegalMoveError`.
- Clock precision: counters of any size are carried and incremented exactly; leading zeros are dropped.
- Draw adjudication outside stalemate: no insufficient-material, fifty/seventy-five-move or repetition detection; such positions report `ongoing`.

After the fix: `npm test` passes 11 of 11; the middlegame and depth-two timing checks in TC-8 still pass.
