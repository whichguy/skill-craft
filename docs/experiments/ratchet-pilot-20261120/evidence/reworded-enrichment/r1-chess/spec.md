## Use cases

### U-1: A Node.js caller starts a game to obtain a position and its first choices
Flow: The caller loads `src/chess.js` through CommonJS and calls `startFen()`. It returns `rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1`. On that FEN, `status` returns `ongoing` and `legalMoves` returns the 20 opening moves in alphabetical UCI order, including `e2e4`.
Source: request

### U-2: A Node.js caller plays successive moves to advance a game
Flow: From the start FEN the caller applies `e2e4`, receiving `rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1`. Applying `e7e5` to that result returns `rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq e6 0 2`. The caller can pass either returned position to the other functions.
Source: request

### U-3: A Node.js caller plays a special move to obtain its resulting position
Flow: In a position where castling is legal, the caller finds and applies the corresponding UCI move, `e1g1`, `e1c1`, `e8g8` or `e8c8`, and sees both pieces relocated. After `e2e4 a7a6 e4e5 d7d5` from the start, the caller can apply `e5d6` and see the black pawn on d5 removed. Where a white pawn can advance from e7 to e8, the caller can choose `e7e8q`, `e7e8r`, `e7e8b` or `e7e8n` and see the chosen piece on e8.
Source: request

### U-4: A Node.js caller attempts a move to find out whether it is allowed
Flow: The caller tries `e2e5` from the start FEN and catches an instance of the exported `IllegalMoveError` class. The caller can use the same FEN to apply a legal move such as `e2e4`.
Source: request

### U-5: A Node.js caller inspects a position to determine whether play can continue
Flow: The caller supplies the current FEN to `status`. A side that can move gets `check` if its king is attacked or `ongoing` otherwise. After fool's mate (`f2f3 e7e5 g2g4 d8h4`), White gets `checkmate`. On `7k/5Q2/6K1/8/8/8/8/8 b - - 0 1`, Black gets `stalemate`. Both terminal positions have an empty legal-move list.
Source: request

### U-6: A maintainer runs the rules suite to verify the module
Flow: The maintainer runs `npm test`. It invokes `node --test` and passes with rule tests in `test/` covering fool's mate, scholar's mate, castling, en passant, promotion, stalemate and move counts from standard test positions.
Source: request

### U-7: A maintainer measures move generation to verify the requested response times
Flow: The maintainer times `legalMoves` on a middlegame position and measures less than 50 ms. From `startFen()`, the maintainer gets the opening moves, applies each to the initial position, and sums the number of replies. The depth-2 total is 400 and the count takes less than 2 seconds.
Source: request

## Clauses

### C-1: The engine is loadable as a CommonJS module at `src/chess.js`.
Observable: From the project root, a Node.js caller can use `require('./src/chess.js')` to obtain the engine's exports.
Source: request

### C-2: The module works without third-party dependencies.
Observable: In the project on Node.js, a caller can load the engine and use its API without installing third-party packages.
Source: request

### C-3: `startFen()` returns the standard starting FEN.
Observable: Calling `startFen()` returns the string `rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1` on first use and after other API calls.
Source: request

### C-4: Each position-taking API function operates on the standard chess position supplied as FEN.
Observable: A caller can pass a six-field FEN for a playable orthodox chess position to `legalMoves`, `applyMove` or `status`. Calls act on the supplied position in any call order, including on a FEN returned by `applyMove` with an en-passant target that no pawn can capture.
Source: implied: U-2 and the request that a position is a FEN string
Open: The requester would settle acceptance or error behavior for malformed or abbreviated FEN and for FEN that encodes inconsistent or impossible positions.

### C-5: `legalMoves(fen)` returns the exact set of legal moves for the active color as an array.
Observable: A caller finds each available move once, with 20 entries from the standard start and `[]` when the active side has no legal move.
Source: request

### C-6: Generated moves use UCI notation.
Observable: Each entry is the origin square followed by the destination square, using files `a` through `h` and ranks `1` through `8`. A promotion adds one lowercase piece letter. For example, `e2e4` is a pawn move and `e7e8q` is a queen promotion.
Source: request

### C-7: `legalMoves(fen)` returns moves in ascending alphabetical order.
Observable: A caller sees UCI strings sorted lexicographically, including the suffix when moves share an origin and destination. For example, the four promotions from e7 to e8 appear relative to one another as `e7e8b`, `e7e8n`, `e7e8q`, `e7e8r`.
Source: request

### C-8: A piece may land only on an empty square or a square occupied by an opponent's piece, subject to its movement rules.
Observable: A move to a square occupied by the moving side is absent from `legalMoves`. A rook that can legally reach an opponent's piece can capture it.
Source: implied: the request to implement all piece moves

### C-9: A rook moves along a rank or file.
Observable: With a clear path and a safe king, a rook on d4 can move to d7 or a4. A move from d4 to e5 is absent for that rook.
Source: implied: the request to implement all piece moves

### C-10: A bishop moves diagonally.
Observable: With a clear path and a safe king, a bishop on d4 can move to g7. A move from d4 to d5 is absent for that bishop.
Source: implied: the request to implement all piece moves

### C-11: A queen moves along a rank, file or diagonal.
Observable: With a clear path and a safe king, a queen on d4 can move to d7, a4 or g7. A move from d4 to e6 is absent for that queen.
Source: implied: the request to implement all piece moves

### C-12: A knight moves two squares on one axis plus one on the other.
Observable: With a legal destination and a safe king, a knight on d4 can move to e6 even if adjoining squares are occupied. A move from d4 to e5 is absent for that knight.
Source: implied: the request to implement all piece moves

### C-13: An ordinary king move is one square in any direction.
Observable: With legal destinations, a king on d4 can move to d5 or e5. A king move from d4 to d6 is absent.
Source: implied: the request to implement all piece moves

### C-14: A rook, bishop or queen requires unoccupied intervening squares.
Observable: Placing a piece of either color between a sliding piece and an otherwise legal destination removes that destination from its legal moves. An opposing piece on the nearer square can itself be captured when the capture is legal.
Source: implied: the request to implement all piece moves

### C-15: An ordinary single-square pawn advance goes straight forward onto an empty square.
Observable: White advances toward rank 8 and Black toward rank 1. A white pawn on e4 can play `e4e5` if e5 is empty and the king remains safe. A piece of either color on e5 blocks the advance.
Source: implied: the request to implement all piece moves

### C-16: A two-square pawn advance is available from the pawn's starting rank when both squares are empty.
Observable: White can advance from rank 2 to rank 4 and Black from rank 7 to rank 5, on the same file, subject to king safety. An occupied intervening or destination square blocks it. From any other rank, a two-square advance is absent.
Source: implied: the request to implement all piece moves and set an en-passant target after every two-square pawn push

### C-17: An ordinary pawn capture moves one square diagonally forward onto an opposing piece.
Observable: A white pawn on e4 can capture an opposing piece on d5 or f5 when its king remains safe. An empty diagonal destination is available only under the en-passant rule. A pawn cannot capture the piece straight ahead.
Source: implied: the request to implement all piece moves

### C-18: An en-passant capture uses the target recorded for the immediately preceding opposing two-square pawn advance.
Observable: A pawn on the adjacent file at the rank of the opposing pawn may move diagonally forward to the recorded empty target, subject to king safety. In U-3 the move is `e5d6`. A FEN with `-` as its en-passant field offers no en-passant capture.
Source: implied: U-3 and the request to implement en passant

### C-19: A pawn move to the farthest rank requires one of the four promotion choices.
Observable: An otherwise legal pawn advance or capture to rank 8 for White or rank 1 for Black generates four moves with suffixes `q`, `r`, `b` and `n`. No unsuffixed move appears for that origin and destination. A promotion suffix is available only for a pawn moving to its farthest rank.
Source: request

### C-20: Every legal move leaves the moving side's king safe.
Observable: From check, only moves that remove all attacks on the moving side's king are available. A king move into attack, a move that exposes the king by moving a pinned piece, or an en-passant capture that exposes the king by removing the captured pawn is omitted when the resulting king is attacked.
Source: implied: the request for every legal move, check and checkmate

### C-21: An opposing piece can attack a square even when moving to that square would expose its own king.
Observable: In `4r3/8/8/8/8/2k5/4R3/4K3 b - - 0 1`, the white rook on e2 attacks c2 despite its pin to the white king. Black's `c3c2` is absent from `legalMoves`. The same attack rule applies to the king's castling squares.
Source: implied: the request for legal king moves and castling through unattacked squares

### C-22: Castling uses the king's two-square UCI move.
Observable: A caller sees and applies `e1g1` for White kingside, `e1c1` for White queenside, `e8g8` for Black kingside or `e8c8` for Black queenside when the corresponding castle is legal.
Source: request

### C-23: Castling requires the active side's corresponding castling right in the FEN.
Observable: A clear, safe kingside castle depends on `K` for White or `k` for Black. A clear, safe queenside castle depends on `Q` for White or `q` for Black. With `-` in that field, no castle is available.
Source: implied: the request for castling with correct FEN castling rights

### C-24: Castling requires the active side's king and participating rook on their home squares.
Observable: A legal castle has the king starting on e1 or e8 and a same-color rook on h1 or h8 for kingside, or a1 or a8 for queenside. A rook on another square cannot substitute.
Source: implied: the request to implement castling on both sides

### C-25: Castling requires every square between the king and participating rook to be empty.
Observable: A piece of either color on the f-file or g-file between the pieces prevents kingside castling. A piece on the b-file, c-file or d-file between the pieces prevents queenside castling.
Source: implied: the request to implement castling on both sides

### C-26: Castling requires an unattacked king origin, transit square and destination.
Observable: On the active side's back rank, an attack on e, f or g prevents kingside castling, and an attack on e, d or c prevents queenside castling. An attack confined to the rook's origin or the b-file square between the queenside pieces does not itself prevent castling.
Source: request

### C-27: Applying a legal move returns the resulting position as a six-field FEN.
Observable: A caller receives the resulting piece placement, active color, castling availability, en-passant target, halfmove clock and fullmove number in FEN field order. For an ordinary move, the origin becomes empty and the moving piece occupies the destination, replacing any piece it captures. Pieces uninvolved in the move retain their squares.
Source: request

### C-28: Applying an en-passant capture removes the opposing pawn from its square.
Observable: After `e5d6` in U-3, White's pawn is on d6 and the black pawn is absent from d5.
Source: implied: U-3 and the request to implement en passant

### C-29: Applying a promotion places the selected piece of the moving color on the destination.
Observable: Applying `e7e8q` where legal puts a white queen on e8. The same rule selects a rook for `r`, bishop for `b` or knight for `n`, for either color on advances or captures.
Source: implied: U-3 and the request to implement promotion

### C-30: Applying a castle relocates the participating rook.
Observable: Alongside the king's UCI move, the rook moves from h1 to f1 for `e1g1`, a1 to d1 for `e1c1`, h8 to f8 for `e8g8` or a8 to d8 for `e8c8`.
Source: implied: U-3 and the request to implement castling on both sides

### C-31: A successful move switches the active color in the returned FEN.
Observable: A legal move from a FEN with `w` returns a FEN with `b`, and a legal move from a FEN with `b` returns a FEN with `w`.
Source: implied: U-2 and the request for the FEN after the move

### C-32: Moving a king clears its color's castling rights.
Observable: The returned FEN drops `K` and `Q` for a White king move or `k` and `q` for a Black king move, whether the king moves ordinarily or castles.
Source: implied: the request for correct castling rights

### C-33: Moving a rook from a corner associated with its color's castling right clears that right.
Observable: The relevant right is `K` for h1, `Q` for a1, `k` for h8 or `q` for a8, according to the moving rook's color.
Source: implied: the request for correct castling rights

### C-34: Capturing a rook on a corner associated with its color's castling right clears that right.
Observable: Capturing the eligible White rook on h1 or a1 removes `K` or `Q` respectively. Capturing the eligible Black rook on h8 or a8 removes `k` or `q` respectively.
Source: implied: the request for correct castling rights

### C-35: A resulting castling-right field retains exactly the rights the move leaves intact.
Observable: Each previously available right remains if its king and relevant home rook stay in place. A previously absent right stays absent, including when a king or rook returns home or another rook arrives on the corner. A position with no remaining rights has `-` in the field.
Source: implied: the request for correct castling rights

### C-36: The resulting en-passant field reflects the move just applied.
Observable: Every two-square pawn push sets the target to the square crossed, even if no opposing pawn can legally capture there. For example, `e2e4` from the start sets `e3` and `e7e5` in U-2 sets `e6`. Every other move sets `-`, expiring any previous target.
Source: request

### C-37: The resulting halfmove clock counts successive plies since the last pawn move or capture.
Observable: A pawn move or a capture resets the field to `0`, including en passant and promotion. A noncapturing move by another piece, including castling, increases the supplied halfmove clock by one.
Source: implied: the request for the correct FEN halfmove clock

### C-38: The resulting fullmove number advances on Black's move.
Observable: A Black move increases the supplied fullmove number by one. A White move leaves it at its supplied value. In U-2 the value is `1` after White's first turn and `2` after Black's first turn.
Source: implied: the request for the correct FEN fullmove number

### C-39: The module exports the `IllegalMoveError` class.
Observable: The caller can access `IllegalMoveError` from the module exports and use it in an `instanceof` check on an exception from an illegal move.
Source: request

### C-40: `applyMove(fen, move)` throws `IllegalMoveError` for an illegal move expressed in UCI.
Observable: On a playable input FEN, a UCI move missing from `legalMoves(fen)` throws an instance of the exported class when passed to `applyMove`. This includes a wrong-side origin, a move forbidden by piece movement or king safety, and an unsuffixed pawn move to its farthest rank. For example, `e2e5` throws from the start FEN.
Source: request
Open: The requester would settle whether to reject or normalize non-UCI representations such as surrounding whitespace or uppercase letters, and how to handle other out-of-domain move arguments.

### C-41: `status(fen)` returns `ongoing` for an unchecked side to move with at least one legal move.
Observable: The start FEN returns the string `ongoing`. The same classification applies to a position with only the two kings if the active side has a legal move with its king out of check.
Source: request

### C-42: `status(fen)` returns `check` for a checked side to move with at least one legal move.
Observable: On `4k3/8/8/8/8/8/4R3/4K3 b - - 0 1`, Black's king is attacked and can escape. The return value is the string `check`.
Source: request

### C-43: `status(fen)` returns `checkmate` for a checked side to move with no legal moves.
Observable: After the fool's mate sequence in U-5 it returns the string `checkmate` with White to move.
Source: request

### C-44: `status(fen)` returns `stalemate` for an unchecked side to move with no legal moves.
Observable: On `7k/5Q2/6K1/8/8/8/8/8 b - - 0 1`, it returns the string `stalemate` with Black to move.
Source: request

### C-45: The `npm test` script invokes `node --test`.
Observable: Running `npm test` from the project root runs the Node.js test runner with `node --test`.
Source: existing: package.json

### C-46: The rules suite is run by `node --test` from test files in `test/`.
Observable: From the project root the maintainer can run `node --test` and see the rules tests discovered from `test/`.
Source: request

### C-47: The rules suite covers fool's mate.
Observable: The suite verifies that fool's mate ends with White checkmated.
Source: request

### C-48: The rules suite covers scholar's mate.
Observable: The suite verifies that scholar's mate ends with Black checkmated. One sequence is `e2e4 e7e5 f1c4 b8c6 d1h5 g8f6 h5f7`.
Source: request

### C-49: The rules suite covers castling.
Observable: The suite verifies castling behavior in positions where castling is permitted or forbidden.
Source: request

### C-50: The rules suite covers en passant.
Observable: The suite verifies a legal en-passant capture.
Source: request

### C-51: The rules suite covers promotion.
Observable: The suite verifies promotion in a position where a pawn can promote.
Source: request

### C-52: The rules suite covers stalemate.
Observable: A test checks that a side with no legal moves and a king out of check gets `stalemate`.
Source: request

### C-53: The rules suite checks known legal-move counts from multiple standard test positions.
Observable: The tests compare computed counts with known values for more than one established chess test position.
Source: request
Open: The requester would settle any prescribed fixture list or count depths beyond the start-position depth-2 workload. Any reasonable selection of standard positions with known counts can satisfy the coverage requirement.

### C-54: `npm test` passes.
Observable: The command completes with no failing tests and exits with code `0`.
Source: request

### C-55: `legalMoves` takes less than 50 ms on a middlegame position.
Observable: A timed `legalMoves(fen)` call on a playable middlegame FEN returns its complete legal-move array in strictly under 50 ms.
Source: request
Open: The requester would settle any prescribed middlegame FEN, reference machine, Node.js version or measurement protocol for the 50 ms limit.

### C-56: Counting legal move sequences two plies deep from the standard start takes less than 2 seconds.
Observable: The maintainer generates the 20 opening moves, applies each to the start FEN, generates each child position's legal moves and sums their lengths. The result is 400 and the count completes in strictly under 2 seconds.
Source: request
Open: The requester would settle any reference machine, Node.js version or measurement protocol for the 2-second limit.
