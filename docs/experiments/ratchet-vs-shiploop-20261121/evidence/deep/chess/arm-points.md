# Points raised by people who built the product

## Marked as open for the customer

- Handling of malformed, incomplete or syntactically valid FEN that describes an impossible position is unspecified. The requester would settle any validation or error contract for those inputs.
- The requester did not specify which standard positions or count depths the suite must include. The requester would settle any mandatory fixture list or depth beyond the separately requested start-position timing check.
- The exact middlegame FEN, runtime and hardware baseline, and timing protocol are unspecified. The requester would settle these for a fixed benchmark.
- The runtime and hardware baseline and timing protocol are unspecified. The requester would settle these for a fixed benchmark.

## Requirements added after looking at a running build

- A saved FEN is sufficient to resume or branch play independently of prior calls. Observable: A caller saves a position with a legal en passant capture, plays that capture and a different legal move as separate branches from the saved FEN, and interleaves calls for another game. A rejected move or a call on another branch leaves the saved position usable. Given only that FEN, a fresh Node.js process returns the same legal moves, status and resulting FEN for the same move.
- With a valid FEN, applyMove rejects a missing or non-string move with IllegalMoveError. Observable: From `startFen()`, omitting the move argument or supplying a value such as `null`, `['e2e4']` or `{ toString: 'e2e4' }` throws an instance of the exported `IllegalMoveError`.
- With a valid FEN, applyMove rejects a non-string move without invoking caller-defined conversion hooks. Observable: From `startFen()`, passing an object whose `Symbol.toPrimitive` or `toString` method records a call and returns `e2e4` throws `IllegalMoveError` and leaves the call count at zero.
- With a valid FEN, applyMove rejects a non-string move without reading its conversion methods. Observable: Pass separate objects with a getter for `Symbol.toPrimitive` or `toString` that records each read before returning a function or throwing. For each object, `applyMove(fen, move)` throws the exported `IllegalMoveError` and the getter's read count stays at zero. This holds for both a starting position and a position with no legal moves.

## What a reader of the code remarked was missing or risky

- The logic holds up on inspection: the castling path, the en passant victim and horizontal pin, the corner-rook rights and the BigInt counters. Perft to depth 3 on three standard positions pins move generation.
- Validation is deliberate. A non-string FEN throws a TypeError; each FEN field is checked by its own regex; rank width and piece letters are checked; each side must have exactly one king; the move's format is checked before the search; IllegalMoveError is used throughout.
- No defect found on inspection: isLegal checks the start, transit and destination squares, and en passant checks the victim pawn and the pin. But move generation is verified only to depth 2, and FENs with duplicate kings are accepted.
- Validates the FEN fields, rank width, piece letters and missing kings, and matches moves by strict equality so nothing is coerced. But a non-string FEN fails only with an incidental TypeError from .trim, and duplicate kings pass.
- Generates pseudo-legal moves on a 0x88 board, then keeps only those that leave the king safe. Castling out of, through and into check, the en-passant victim and pin checks, castling rights and both counters all read correct, and perft to depth 3 on three standard positions backs this up.
- Rejects a non-string FEN with a TypeError and validates every FEN field, the rank widths, and missing or duplicate kings. It screens the move string before searching, and the tests check error paths by message.
- Same sound design (row/file board, legality by making the move and testing king safety, castling transit check, corner rights checked by colour) and no rule defect found. Assurance is lower because move generation is pinned only to perft depth 2 on two positions.
- Validates FEN fields, ranks, widths and that both kings are present, and rejects non-string moves without coercing them. A non-string FEN fails only by accident (a TypeError from trim), a FEN with two kings is accepted and only the first is guarded, and no FEN error path is tested.
