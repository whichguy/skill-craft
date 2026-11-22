# Shortfalls

## Malformed FEN can pass as a playable or finished position

Severity is `high`. A caller importing a position needs the engine to flag invalid board and turn fields before returning legal moves, a game status, or an updated FEN. Run the following command from the repository root.

```sh
node <<'NODE'
const { startFen, legalMoves, applyMove, status } = require('./src/chess.js');
const shortRank = startFen().replace('RNBQKBNR', 'RNBQKBN');
console.log(status(shortRank), legalMoves(shortRank).length);
console.log(applyMove(shortRank, 'e2e4'));
const badTurn = startFen().replace(' w ', ' W ');
console.log(status(badTurn), JSON.stringify(legalMoves(badTurn)));
NODE
```

The command printed the following.

```text
ongoing 20
rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBN1 b KQkq e3 0 1
stalemate []
```

The seven-square rank is silently padded with an empty square where the rook would be, and the returned FEN retains White’s kingside castling right. Changing the active color to `W` makes the starting board appear stalemated. Both inputs should produce an invalid-position error so the caller can correct the FEN before continuing or declaring the game over.

# Choices the customer was not told

- FEN whitespace tolerance — The engine accepts leading and trailing whitespace and tabs or repeated whitespace between fields. `applyMove` emits a FEN with single-space separators.
- UCI whitespace tolerance — `applyMove` requires the exact move string. Leading or trailing whitespace triggers `IllegalMoveError`.
- Clock precision — `applyMove` preserves and increments decimal FEN counters exactly, including values beyond JavaScript’s safe integer range.
- Draw adjudication outside stalemate — `status` reports check and move availability. A bare-kings position, a position reached for the fifth time, and a position at a halfmove clock of 150 can all return `ongoing` with legal moves.
