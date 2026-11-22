# Would the customer care?

`/Users/dadleet/e2e-runs/d20261122-360a9f/deep/chess/request.md` is a request a customer gave a software builder. Below are things a reviewer says the delivered product
gets wrong. For each, taking the reviewer's description as true, say whether the customer, an operator or the next
maintainer would care:

- `must`: it loses data, misleads a user, breaks something that worked, or is a plain defect anyone would report.
- `should`: a careful builder would not have left it; a real but smaller cost.
- `no`: a reasonable builder could ignore it; fixing it is taste, speculation or over-engineering for this request.

Answer with one JSON object and nothing else: `{"ratings": [{"n": 1, "rating": "must|should|no", "why": "one sentence"}]}`

## The reported shortfalls

- **1**: Imported en passant metadata can authorize an impossible capture
- **2**: An imported castling right can take effect after a rook moves onto its corner

## The reviewer's full text, for the detail of each

# Shortfalls

## Imported en passant metadata can authorize an impossible capture — high

An en passant capture depends on the opponent's immediately preceding double pawn push. A caller importing a position needs the engine to reject a target that the board or halfmove clock directly contradicts. Otherwise the engine lists an illegal move and removes a pawn when the caller plays it. [FIDE Laws of Chess, article 3.7.3](https://handbook.fide.com/chapter/E012023)

Run from the repository root.

```sh
node <<'NODE'
const { legalMoves, applyMove } = require('./src/chess');
for (const fen of [
  '4k3/3n4/8/3pP3/8/8/8/4K3 w - d6 0 15',
  '4k3/8/8/3pP3/8/8/8/4K3 w - d6 1 15',
]) {
  console.log(legalMoves(fen).includes('e5d6'));
  console.log(applyMove(fen, 'e5d6'));
}
NODE
```

Both membership checks print `true`. The resulting FENs are `4k3/3n4/3P4/8/8/8/8/4K3 b - - 0 15` and `4k3/8/3P4/8/8/8/8/4K3 b - - 0 15`. In the first input a knight occupies d7, the pawn's required starting square. In the second input the halfmove clock is 1, although a pawn move would have reset it to 0. The engine should reject the contradictory FEN or omit `e5d6` and throw `IllegalMoveError` for the attempted capture. With d7 empty and the clock at 0, the same capture is correctly allowed.

## An imported castling right can take effect after a rook moves onto its corner — high

A caller stepping through an imported position needs castling rights to stay unavailable once the required rook has moved. A stale right on an empty corner can survive an ordinary move and then allow castling with the rook that just moved there. [FIDE Laws of Chess, article 3.8.2](https://handbook.fide.com/chapter/E012023)

Run from the repository root.

```sh
node <<'NODE'
const { legalMoves, applyMove } = require('./src/chess');
const fen = '4k3/8/8/8/8/8/7R/4K3 w K - 0 20';
console.log(legalMoves(fen).includes('e1g1'));
const next = ['h2h1', 'e8d8'].reduce(applyMove, fen);
console.log(next);
console.log(legalMoves(next).includes('e1g1'));
console.log(applyMove(next, 'e1g1'));
NODE
```

The first check prints `false`. After the rook moves to h1 and Black replies, the engine returns `3k4/8/8/8/8/8/8/4K2R w K - 2 21`. The second check prints `true`, and the castle returns `3k4/8/8/8/8/8/8/5RK1 b - - 3 21`. The engine should reject the initial contradictory right or discard it. With the right discarded, `e1g1` should stay absent and attempting it should throw `IllegalMoveError`. Starting with `-` in place of `K` produces exactly that behavior.

# Choices the customer was not told

- FEN whitespace and rank formatting. The parser accepts surrounding whitespace, tabs and repeated field separators, and split empty runs such as `44` for an empty rank. `applyMove` emits single spaces and coalesced empty runs.
- FEN field boundaries. The parser requires all six fields, exactly one king of each color, and castling letters in `KQkq` order. It accepts leading zeros in the halfmove clock and rejects them in the fullmove number.
- FEN counters beyond JavaScript's safe integer range. The engine reads, increments, and writes them as exact decimal integers.
- Invalid argument reporting. Non-string FENs throw `TypeError`, and malformed FEN strings throw ordinary `Error` with a field, placement, rank width, or king diagnostic. If the UCI argument is also malformed, `applyMove` reports `IllegalMoveError` first.
- Validation of imported positions. The parser accepts some impossible arrangements, including adjacent kings, and computes moves and status directly from the supplied board.
- Draw adjudication beyond stalemate. A bare-kings position, a repeated starting position, and a position at a halfmove clock of 150 all returned `ongoing` and allowed play in the probes. Draw adjudication in those cases is left to the caller.
