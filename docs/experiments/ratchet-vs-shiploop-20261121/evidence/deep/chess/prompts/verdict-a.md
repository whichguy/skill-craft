# Three deliveries of one request: which is the better feature?

Three builders each delivered the same customer request (below). Each delivery was audited by running it: every
stated requirement, a list of conditions the request leaves unsaid, its tests, its specification and its documents.
Items the audits disagreed on were run again on all three by another person, and every defect an auditor reported
was tried on all three. You have the audits (with those re-runs applied) and the defect table. The deliveries are
labelled X, Y and Z; the labels and their order carry no meaning. You do not have the products and should not guess
at them beyond the audits.

Judge as the person who will run this feature and keep it working: what does each delivery give that the others do
not, and does it matter? Size is not quality: a longer specification, more tests or more code count only through
what the audits show they bought, and count against a delivery where the audits show they cost (requirements the
customer did not ask for, tests that pin one builder's choices, code a maintainer must carry). Count each
consequence once, however many audit lines mention it.

For each pair (Y-X, Y-Z, Z-X):

- `better`: `<letter>-much`, `<letter>-some` (naming the better delivery) or `same`.
- `advantages`: each real advantage of either side, with the audit line or defect id behind it (`ref`) and whom it
  matters to: `requester`, `operator`, `maintainer` or `no one`.
- `lesser_lacks`: what the lesser delivery would need to match the better one, as a list of concrete changes.
- `one_task_closes`: `yes` if one short follow-up task (about an hour of the same builder's work) would close that
  list, else `no`. `yes` when `better` is `same`.
- `why`: three sentences at most.

Answer with one JSON object and nothing else:

```json
{"pairs": [{"pair": "Y-X", "better": "same", "advantages": [{"of": "X", "what": "...", "ref": "U-4", "matters_to": "operator"}], "lesser_lacks": ["..."], "one_task_closes": "yes", "why": "..."}]}
```

## The request

Build a chess rules engine as a Node.js module src/chess.js (CommonJS, no dependencies; npm test runs node --test). A position is a FEN string. startFen() returns the standard start position. legalMoves(fen) returns an array of every legal move for the side to move in UCI form (for example e2e4, and e7e8q for a promotion), sorted alphabetically. applyMove(fen, move) returns the FEN after the move, with correct castling rights, en-passant square, halfmove clock and fullmove number, or throws IllegalMoveError (a class the module also exports) when the move is not legal. The en-passant target square is set after every two-square pawn push, whether or not a capture is possible (the FEN-spec convention). status(fen) returns ongoing, check, checkmate or stalemate for the side to move. Implement all piece moves, castling on both sides (never out of, through or into check; in UCI it is the king's two-square move: e1g1, e1c1, e8g8, e8c8), en passant, promotion to q, r, b or n, check, checkmate and stalemate. Cover the rules with node --test tests in test/: known games (fool's mate, scholar's mate), castling, en passant, promotion, stalemate and move counts from standard test positions. Keep legalMoves on a middlegame position under 50 ms and a depth-2 legal-move count of the start position under 2 seconds. npm test must pass.

## The inventory


## Stated requirements

- **S-1**: The chess rules engine is a Node.js module at src/chess.js.
- **S-2**: src/chess.js is a CommonJS module (loadable with require).
- **S-3**: The module has no dependencies.
- **S-4**: npm test runs node --test.
- **S-5**: A position is a FEN string.
- **S-6**: startFen() returns the standard start position.
- **S-7**: legalMoves(fen) returns an array of every legal move for the side to move.
- **S-8**: legalMoves returns moves in UCI form (for example e2e4).
- **S-9**: legalMoves writes a promotion in UCI form with the piece letter (for example e7e8q).
- **S-10**: legalMoves returns its moves sorted alphabetically.
- **S-11**: applyMove(fen, move) returns the FEN after the move.
- **S-12**: The FEN applyMove returns has correct castling rights.
- **S-13**: The FEN applyMove returns has the correct en-passant square.
- **S-14**: The FEN applyMove returns has the correct halfmove clock.
- **S-15**: The FEN applyMove returns has the correct fullmove number.
- **S-16**: applyMove throws IllegalMoveError when the move is not legal.
- **S-17**: IllegalMoveError is a class the module also exports.
- **S-18**: The en-passant target square is set after every two-square pawn push, whether or not a capture is possible (the FEN-spec convention).
- **S-19**: status(fen) returns ongoing, check, checkmate or stalemate for the side to move.
- **S-20**: All piece moves are implemented (king, queen, rook, bishop, knight, pawn).
- **S-21**: Castling is implemented on both sides (kingside and queenside).
- **S-22**: Castling is never allowed out of check.
- **S-23**: Castling is never allowed through check.
- **S-24**: Castling is never allowed into check.
- **S-25**: In UCI, castling is the king's two-square move: e1g1, e1c1, e8g8, e8c8.
- **S-26**: En passant is implemented.
- **S-27**: Promotion to q, r, b or n is implemented.
- **S-28**: Check is implemented.
- **S-29**: Checkmate is implemented.
- **S-30**: Stalemate is implemented.
- **S-31**: There are node --test tests in test/ covering the known game fool's mate.
- **S-32**: There are node --test tests in test/ covering the known game scholar's mate.
- **S-33**: There are node --test tests in test/ covering castling.
- **S-34**: There are node --test tests in test/ covering en passant.
- **S-35**: There are node --test tests in test/ covering promotion.
- **S-36**: There are node --test tests in test/ covering stalemate.
- **S-37**: There are node --test tests in test/ covering move counts from standard test positions.
- **S-38**: legalMoves on a middlegame position takes under 50 ms.
- **S-39**: A depth-2 legal-move count of the start position takes under 2 seconds.
- **S-40**: npm test passes.

## Conditions the request leaves unsaid

- **U-1**: What legalMoves, applyMove and status do when the FEN argument is missing, not a string, malformed (empty, wrong number of ranks or squares in a rank, unknown piece letter, bad side-to-move or other field, trailing whitespace or newline) or syntactically valid but an impossible position (a side with no king or two kings, a pawn on the first or eighth rank, the side not to move already in check).
  - Probe: From the directory that contains package.json: const c = require('./src/chess.js'). For each of: no argument, undefined, null, 42, '', 'not-a-fen', 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP w KQkq - 0 1' (7 ranks), 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR x KQkq - 0 1', c.startFen() + '\n', '8/8/8/8/8/8/8/8 w - - 0 1' (no kings), '4k3/8/8/8/8/8/8/4KK2 w - - 0 1' (two white kings), '4P3/8/8/8/8/8/8/4k2K w - - 0 1' (pawn on the eighth rank), '4k3/8/8/8/8/8/4R3/4K3 w - - 0 1' (side not to move in check), call c.legalMoves(f), c.status(f) and c.applyMove(f, 'e2e4') inside try/catch and record the returned value or the thrown value's constructor name and message.
  - Outcomes that would be acceptable: Throwing a descriptive Error (a plain Error, a TypeError for a non-string, a distinct invalid-FEN error class, or IllegalMoveError) is fine; tolerating surrounding whitespace is fine; returning a value for an impossible position is compatible with the request's words. Not fine: a confident but wrong answer for a malformed FEN, or a hang. A consistent choice across the three functions is preferable.
- **U-3**: How applyMove treats move values that are not exactly one of the lowercase UCI strings legalMoves returns: uppercase ('E2E4', 'e7e8Q'), surrounding spaces, SAN ('e4'), a hyphen or capture mark ('e2-e4', 'e2xe4'), a promotion with no piece letter ('e7e8'), a promotion letter on a non-promoting move ('e2e4q'), off-board squares ('e2e9'), a non-string value, and king-takes-rook castling ('e1h1').
  - Probe: From startFen() call applyMove with 'e2e4', 'E2E4', ' e2e4', 'e4', 'e2-e4', 'e2xe4', 'e2e4q', 'e2e9' and 42, recording the returned FEN or the thrown value's class. On '4k3/4P3/8/8/8/8/8/4K3 w - - 0 1' call applyMove with 'e7e8q', 'e7e8Q', 'e7e8', 'e7e8r', 'e7e8b' and 'e7e8n', recording the piece now on e8 or the error. On 'r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1' call applyMove with 'e1h1'.
  - Outcomes that would be acceptable: Rejecting everything that is not exactly in legalMoves(fen) with IllegalMoveError is fine. Also accepting SAN, a hyphen, a capture mark or a different letter case is compatible if documented. For a bare promotion, rejecting it or treating it as a queen promotion are both compatible, the latter if documented. Promotion with an explicit q, r, b or n must still give that piece.
- **U-4**: What the exported IllegalMoveError looks like to a caller: whether it extends Error, its name, its message (whether it names the rejected move) and any properties it carries.
  - Probe: try { c.applyMove(c.startFen(), 'e2e5') } catch (e) { console.log(e instanceof c.IllegalMoveError, e instanceof Error, e.constructor.name, e.name, e.message, !!e.stack, Object.keys(e)) }; repeat with 'a1a3'.
  - Outcomes that would be acceptable: Extending Error with name 'IllegalMoveError' and a message that includes the move (optionally the FEN) is the usual shape; any message wording is fine; extra properties such as the move or the FEN are fine and so is none. A class that does not extend Error still matches the request's words.
- **U-5**: Whether the FEN's castling-rights and en-passant fields are trusted when they cannot match the board (a rights letter whose king or rook is not on its home square; an en-passant square that no pawn could have produced with a two-square push).
  - Probe: Call legalMoves and status on '4k3/8/8/8/8/8/8/4K3 w K - 0 1' (king on e1, rights K, no rook), on '4k3/8/8/8/8/8/8/R3K3 w KQ - 0 1' (no h1 rook) and on '4k3/8/8/8/8/8/4K3/7R w K - 0 1' (king on e2), and check whether e1g1 is listed; if it is, applyMove with 'e1g1' and print the FEN. Call legalMoves and status on 'rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR w KQkq e3 0 1' (white to move, en-passant square e3) and check for any capture onto e3. Record any thrown error.
  - Outcomes that would be acceptable: Not offering the castle when the king or that rook is not on its home square, or rejecting the FEN as invalid, are both fine. Ignoring an en-passant square no pawn could have produced, or rejecting the FEN, are both fine. Not fine: moving a missing rook or capturing a missing pawn.
- **U-7**: Whether move generation is correct beyond depth 2: counts on published perft positions at depth 3 or more, which exercise pins, discovered check by en passant, loss of castling rights when a rook is captured on its corner, and promotion captures.
  - Probe: With a small perft helper built only on legalMoves and applyMove, count: start position depth 3 (expect 8902) and depth 4 (197281); Kiwipete 'r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1' depth 1 (48), 2 (2039), 3 (97862); position 3 '8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1' depth 4 (43238). Compare each with the published value.
  - Outcomes that would be acceptable: Every count matching the published value is required for correctness; how deep the delivered tests go is a separate question.
- **U-9**: What the test suite actually asserts for each named subject: the move lists or FENs for fool's mate and scholar's mate and whether a final checkmate is asserted; the fixtures and asserted results (FEN fields, UCI moves, status) for castling, en passant, promotion (q only or also r, b, n) and stalemate; and which standard positions, depths and counts the move-count tests check.
  - Probe: Run npm test from the package root and record the exit code, the number of tests and their files. Read every file under test/. For fool's mate and scholar's mate record the moves or FENs and whether checkmate is asserted. For castling, en passant, promotion and stalemate record the fixtures and what is asserted. For move counts list each FEN, depth and asserted integer, and recompute that count with legalMoves and applyMove.
  - Outcomes that would be acceptable: Any real line of each mate, and any castling, en passant, promotion and stalemate positions, are fine. Asserting final status, resulting FEN and numeric counts is a strong reading; a smaller set that still exercises each named subject is compatible. Any positions a chess programmer would call standard are fine for move counts, provided the asserted counts match the published values.
- **U-11**: A saved FEN is enough to resume or branch play: results depend only on the FEN and move given, not on earlier calls, other games or a rejected move.
  - Probe: Save F = the FEN after applying e2e4, a7a6, e4e5, d7d5 to startFen() (white can capture e5d6 en passant). Record legalMoves(F), status(F) and applyMove(F, 'e5d6'). Then, interleaving calls on startFen() for another game, apply e5d6 and separately g1f3 from F, attempt an illegal move such as 'e5e7' on F inside try/catch, and call legalMoves(F), status(F) and applyMove(F, 'e5d6') again. In a fresh Node.js process, given only F, make the same three calls. Compare all results.
  - Outcomes that would be acceptable: The same FEN and move give the same legal moves, status and resulting FEN in every case and in a fresh process; a rejected move leaves the saved position usable.
- **U-12**: Whether the delivered tests exercise the error paths: invalid FENs and illegal or malformed moves, asserting the error thrown.
  - Probe: Read every file under test/ and list each test that passes an invalid FEN (malformed or impossible) or an illegal, malformed or non-string move, and what it asserts (error class, message or other). Note which of the two kinds of error path has no test.
  - Outcomes that would be acceptable: At least one test for an invalid FEN and one for an illegal move, each asserting the thrown error's class or message, is a strong reading; asserting the class rather than exact message wording is preferable. Having none is compatible with the request's words but leaves the error contract unguarded.

## The defect table (each defect with what each delivery did when it was tried)

No defect reproduced.

## Audit of delivery X

```json
{
 "code": "X",
 "stated": [
  {
   "id": "S-1",
   "built": "yes",
   "observed": true,
   "evidence": "node -e \"require('./src/chess.js')\" from package root: loads; Object.keys -> [startFen, legalMoves, applyMove, status, IllegalMoveError]",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-2",
   "built": "yes",
   "observed": true,
   "evidence": "require('./src/chess.js') works in plain node (CommonJS, module.exports at end of file)",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-3",
   "built": "yes",
   "observed": true,
   "evidence": "package.json has no dependencies field, no node_modules; grep require( in src/chess.js finds none; module loads and runs with no install",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-4",
   "built": "yes",
   "observed": true,
   "evidence": "package.json scripts.test = \"node --test\"; npm test prints \"> node --test\" and runs test/chess.test.js",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-5",
   "built": "yes",
   "observed": true,
   "evidence": "legalMoves/applyMove/status all take six-field FEN strings; applyMove(startFen(),\"e2e4\") -> \"rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1\"",
   "spec": "stated",
   "proved": "fails",
   "proved_by": "formatFen: changed the field separator .join(' ') to .join(';') so applyMove no longer returns a FEN; npm test 12 of 16 fail (e.g. 'FEN metadata tracks double pushes, turn changes and target expiry', 'both colors can castle on either wing and relocate their rook'); restored, suite back to 16/16 pass"
  },
  {
   "id": "S-6",
   "built": "yes",
   "observed": true,
   "evidence": "startFen() -> \"rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1\"",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-7",
   "built": "yes",
   "observed": true,
   "evidence": "legalMoves(startFen()) -> 20 moves; perft built only on legalMoves/applyMove: start d1 20, d2 400, d3 8902, d4 197281; Kiwipete d1 48, d2 2039, d3 97862; position 3 d4 43238; position 4 d3 9467; position 5 d3 62379 - all equal published values",
   "spec": "stated",
   "proved": "fails",
   "proved_by": "pawnMoves: removed the line pushing the two-square advance (moves.push({ from, to: double })); start position then has 16 moves; npm test 9 of 16 fail incl. 'the standard position has 20 sorted moves and 400 two-ply continuations' and 'Kiwipete has 48 legal moves and 2039 two-ply continuations'; restored, 16/16 pass"
  },
  {
   "id": "S-8",
   "built": "yes",
   "observed": true,
   "evidence": "legalMoves(startFen()) -> [\"a2a3\",\"a2a4\",\"b1a3\",...,\"h2h4\"], four-character from-to strings",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-9",
   "built": "yes",
   "observed": true,
   "evidence": "legalMoves('4k3/P7/8/8/8/8/8/4K3 w - - 0 1') a7 moves -> ['a7a8b','a7a8n','a7a8q','a7a8r']; with capture on b8 also a7b8b/n/q/r",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-10",
   "built": "yes",
   "observed": true,
   "evidence": "middlegame r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4: 33 moves, equal to [...moves].sort(); start list is alphabetical",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-11",
   "built": "yes",
   "observed": true,
   "evidence": "applyMove(startFen(),'e2e4') -> 'rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1'; castles, ep and promotions return correct boards",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-12",
   "built": "yes",
   "observed": true,
   "evidence": "On 'r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1': e1g1 -> '... b kq', h1h2 -> 'Qkq', a1a2 -> 'Kkq', e1e2 -> 'kq', h1h8 (captures rook) -> 'Qq'; black a8a1 -> 'Kk'; promotion capture b7a8q on 'r3k2r/1P6/8/8/8/8/8/4K3 w kq' -> 'k'",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-13",
   "built": "yes",
   "observed": true,
   "evidence": "e2e4 -> e3; then e7e5 -> e6; a2a4 -> a3; h7h5 -> h6; e2e3 -> '-'; after e5d6 ep capture -> '-'; g1f3 after e6 -> '-'",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-14",
   "built": "yes",
   "observed": true,
   "evidence": "g1f3 from start -> 1; then g8f6 -> 2; capture c3d5 at clock 7 -> 0; pawn d5d4 at 7 -> 0; quiet knight at 7 -> 8; castle at 0 -> 1",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-15",
   "built": "yes",
   "observed": true,
   "evidence": "e2e4 keeps 1, e7e5 -> 2; black castle from fullmove 1 -> 2; black capture at 20 -> 21",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-16",
   "built": "yes",
   "observed": true,
   "evidence": "applyMove(startFen(),'e2e5') -> throws IllegalMoveError 'Illegal move: e2e5'; pinned bishop e2d3 on '4k3/4r3/8/8/8/8/4B3/4K3 w' -> IllegalMoveError; e1g1 while in check -> IllegalMoveError",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-17",
   "built": "yes",
   "observed": true,
   "evidence": "typeof c.IllegalMoveError === 'function'; caught error: e instanceof c.IllegalMoveError true, instanceof Error true, name 'IllegalMoveError'",
   "spec": "stated",
   "proved": "passes",
   "proved_by": "removed IllegalMoveError from module.exports (module.exports = { startFen, legalMoves, applyMove, status }); npm test still 16/16 pass because assert.throws(fn, undefined) only checks that something is thrown; restored, 16/16 pass"
  },
  {
   "id": "S-18",
   "built": "yes",
   "observed": true,
   "evidence": "applyMove(startFen(),'e2e4') sets e3 though no black pawn can capture; e7e5 sets e6; a2a4 on '4k3/8/8/8/8/8/P7/4K3 w' sets a3 with no black pawns at all",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-19",
   "built": "yes",
   "observed": true,
   "evidence": "status: startFen() 'ongoing'; after e2e4 f7f6 d1h5 'check'; fool's mate 'checkmate'; '7k/5Q2/6K1/8/8/8/8/8 b - - 0 1' 'stalemate'",
   "spec": "stated",
   "proved": "fails",
   "proved_by": "status: changed return checked ? 'check' : 'ongoing' to return checked ? 'in-check' : 'ongoing'; npm test 2 fail ('check with a legal reply is distinct from ongoing play', 'en passant can answer a pawn check but cannot reveal a rook check'); restored, 16/16 pass"
  },
  {
   "id": "S-20",
   "built": "yes",
   "observed": true,
   "evidence": "perft counts at depth 3-4 on five standard positions all match published values (exercise every piece type); start list contains pawn and knight moves; Kiwipete 48",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-21",
   "built": "yes",
   "observed": true,
   "evidence": "'r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1' legal e1 moves include e1c1 and e1g1; e1g1 -> 'r3k2r/8/8/8/8/8/8/R4RK1 b kq - 1 1'; e1c1 -> '2KR3R'; black e8g8 -> 'r4rk1', e8c8 -> '2kr3r'",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-22",
   "built": "yes",
   "observed": true,
   "evidence": "rook on e4 checking e1 ('r3k2r/8/8/8/4r3/8/8/R3K2R w KQkq - 0 1'): e1 moves ['e1d1','e1d2','e1f1','e1f2'], no castles; applyMove e1g1 -> IllegalMoveError",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-23",
   "built": "yes",
   "observed": true,
   "evidence": "rook attacking f1 (f4): e1g1 absent, e1c1 present; rook attacking d1 (d4): e1c1 absent, e1g1 present",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-24",
   "built": "yes",
   "observed": true,
   "evidence": "rook attacking g1 (g4): e1g1 absent; rook attacking c1 (c4): e1c1 absent; b1 attacked only (b4): both castles present (correct)",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-25",
   "built": "yes",
   "observed": true,
   "evidence": "castles listed and accepted as e1g1, e1c1, e8g8, e8c8 (king two-square move); e1h1 -> IllegalMoveError",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-26",
   "built": "yes",
   "observed": true,
   "evidence": "after e2e4 a7a6 e4e5 d7d5: legal e5d6; applyMove -> 'rnbqkbnr/1pp1pppp/p2P4/8/8/8/PPPP1PPP/RNBQKBNR b KQkq - 0 3' (d5 removed); black e4d3 after d2d4 removes d4; horizontal pin '8/8/8/K2pP2r/8/8/8/7k w - d6' e5d6 not offered",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-27",
   "built": "yes",
   "observed": true,
   "evidence": "'4k3/P7/8/8/8/8/8/4K3 w - - 0 1' a7a8q/r/b/n -> Q/R/B/N on a8; black a2a1n -> 'n' on a1",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-28",
   "built": "yes",
   "observed": true,
   "evidence": "after e2e4 f7f6 d1h5: status 'check', legalMoves ['g7g6']; double check '4k3/8/5N2/8/8/8/8/4R2K b' -> king moves only",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-29",
   "built": "yes",
   "observed": true,
   "evidence": "fool's mate f2f3 e7e5 g2g4 d8h4 -> status 'checkmate', legalMoves []; scholar's mate -> 'checkmate'",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-30",
   "built": "yes",
   "observed": true,
   "evidence": "status('7k/5Q2/6K1/8/8/8/8/8 b - - 0 1') 'stalemate', legalMoves []; 'k7/2Q5/1K6/8/8/8/8/8 b - - 0 1' 'stalemate'",
   "spec": "stated",
   "proved": "fails",
   "proved_by": "status: changed return checked ? 'checkmate' : 'stalemate' to return 'checkmate'; npm test 1 fail ('a safe king with no legal move is stalemated'); restored, 16/16 pass"
  },
  {
   "id": "S-31",
   "built": "yes",
   "observed": true,
   "evidence": "npm test runs 'Fool’s mate checkmates White' (f2f3 e7e5 g2g4 d8h4, asserts white to move, 'checkmate', legalMoves []) - passes",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-32",
   "built": "yes",
   "observed": true,
   "evidence": "npm test runs 'Scholar’s mate checkmates Black' (e2e4 e7e5 f1c4 b8c6 d1h5 g8f6 h5f7, asserts 'checkmate', []) - passes",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-33",
   "built": "yes",
   "observed": true,
   "evidence": "npm test runs castling tests: four castles with full FEN, out of/through/into check, blocked b1, no right, no rook, corner-rook rights - pass",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-34",
   "built": "yes",
   "observed": true,
   "evidence": "npm test runs en passant tests for both colours with full FEN, ep answering a check, ep revealing a rook check rejected - pass",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-35",
   "built": "yes",
   "observed": true,
   "evidence": "npm test runs promotion test: all four suffixes listed and applied (as captures), bare/uppercase/k suffix rejected, black underpromotion to n - passes",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-36",
   "built": "yes",
   "observed": true,
   "evidence": "npm test runs 'a safe king with no legal move is stalemated' ('7k/5K2/6Q1/8/8/8/8/8 b - - 0 1') - passes",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-37",
   "built": "yes",
   "observed": true,
   "evidence": "npm test asserts start 20 and 400, Kiwipete 48 and 2039 (published values; recomputed by my perft: identical)",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-38",
   "built": "yes",
   "observed": true,
   "evidence": "fresh node process: legalMoves('r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4') 0.55 ms cold, 0.02 ms warm; Kiwipete 0.02 ms",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-39",
   "built": "yes",
   "observed": true,
   "evidence": "fresh node process: depth-2 count from start via legalMoves+applyMove = 400 in 2.1 ms",
   "spec": "stated",
   "proved": "passes",
   "proved_by": "legalMoves: inserted Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, 100) (100 ms per call, depth-2 count > 2 s); npm test still 16/16 pass, only slower; restored, 16/16 pass"
  },
  {
   "id": "S-40",
   "built": "yes",
   "observed": true,
   "evidence": "npm test -> 16 tests, 16 pass, 0 fail, exit 0",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  }
 ],
 "unstated": [
  {
   "id": "U-1",
   "behaviour": "All three functions behave the same. Malformed strings throw a plain Error naming the fault: '' / 'not-a-fen' / bad side 'x' / bad castling / bad ep / non-numeric clock / 4 fields / fullmove 0 -> 'Invalid FEN fields'; 7 ranks -> 'Invalid FEN placement'; unknown letter or '9' -> 'Invalid FEN rank'; 7-square rank -> 'Invalid FEN rank width'; no king -> 'Missing king in FEN'. Non-strings (no arg, undefined, null, 42) throw TypeError with an incidental message ('Cannot read properties of undefined (reading 'trim')', 'fen.trim is not a function'). Surrounding whitespace and a trailing newline are tolerated (start moves returned). Impossible but well-formed positions return values: two white kings -> moves for both kings, 'ongoing'; pawn on 8th rank -> king moves; pawn on a1 -> offers a1a2; side not to move in check -> 'ongoing' with 16 moves and applyMove works. No hangs.",
   "handling": "acceptable",
   "observed": true,
   "evidence": "node .audit-probes/p2.js (each input to legalMoves, status, applyMove(f,\"e2e4\") in try/catch); results as described",
   "spec": "open",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-3",
   "behaviour": "Only exact lowercase UCI strings from legalMoves are accepted; everything else throws IllegalMoveError: 'E2E4', ' e2e4', 'e2e4 ', 'e4', 'e2-e4', 'e2xe4', 'e2e4q', 'e2e9', '', 'e2e4e4'; 42/undefined/null -> 'Illegal move: expected a UCI string'; e1h1 on the castling board rejected. On the inventory fixture '4k3/4P3/...' every e7e8 variant is rejected because the black king blocks e8 (correct). On '7k/4P3/8/8/8/8/8/4K3 w' e7e8q/r/b/n give Q/R/B/N on e8; e7e8Q, E7E8Q, bare e7e8 and e7e8k rejected.",
   "handling": "sound",
   "observed": true,
   "evidence": "node .audit-probes/p2.js and p3.js",
   "spec": "decided-unmarked",
   "told": "yes",
   "told_where": "README.md: \"This dependency-free CommonJS module uses standard six-field FEN strings for positions and lowercase UCI strings for moves.\" and \"Given a valid FEN, it throws `IllegalMoveError` for an illegal UCI string or a missing or non-string move.\""
  },
  {
   "id": "U-4",
   "behaviour": "class IllegalMoveError extends Error; e instanceof c.IllegalMoveError true, instanceof Error true, constructor.name and name 'IllegalMoveError', message 'Illegal move: e2e5' / 'Illegal move: a1a3' (non-string: 'Illegal move: expected a UCI string'), stack present, own keys ['name'], no move/fen properties.",
   "handling": "sound",
   "observed": true,
   "evidence": "try { c.applyMove(c.startFen(),'e2e5') } catch(e) {...} -> true true IllegalMoveError IllegalMoveError 'Illegal move: e2e5' true ['name']; same for a1a3",
   "spec": "decided-unmarked",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-5",
   "behaviour": "Castling rights are honoured only when king and rook stand on home squares: '4k3/8/8/8/8/8/8/4K3 w K' no castle; 'R3K3 w KQ' only e1c1 (applies to '2KR4 b - - 1 1'); king on e2 with K right no castle; '4K2R w Q' no e1c1. Impossible ep square e3 with white to move: no capture onto e3, status 'ongoing'; ep square c6/d6 without a black pawn beside: no ep move, applyMove e5c6/e5d6 -> IllegalMoveError. An ep square on the wrong rank for the side (d5) is rejected as 'Invalid FEN fields'.",
   "handling": "sound",
   "observed": true,
   "evidence": "node .audit-probes/p2.js (U-5 block)",
   "spec": "decided-unmarked",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-7",
   "behaviour": "All counts match published values: start d3 8902, d4 197281; Kiwipete d1 48, d2 2039, d3 97862; position 3 d4 43238; also position 4 d3 9467 and position 5 d3 62379. Start d4 took 181 ms.",
   "handling": "sound",
   "observed": true,
   "evidence": "node .audit-probes/perft.js (perft built only on legalMoves and applyMove)",
   "spec": "decided-unmarked",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-9",
   "behaviour": "npm test: exit 0, 16 tests, all in test/chess.test.js. Fool's mate f2f3 e7e5 g2g4 d8h4 and scholar's mate e2e4 e7e5 f1c4 b8c6 d1h5 g8f6 h5f7: assert side to move, status 'checkmate' and legalMoves []. Castling: full FEN after all four castles (rights, clocks), rejection with the king in check, f1 attacked and g1 attacked, blocked b1, no right, no rook, a b1 attack that still allows e1c1, corner-rook capture rights and no restoration. En passant: full FEN for both colours, ep that answers a pawn check, ep that would expose the king rejected. Promotion: all four (as captures) with exact FENs, bare/uppercase/k rejected, black a2a1n. Stalemate: one position, 'stalemate' and []. Move counts: start d1 20 (exact list) and d2 400, Kiwipete d1 48 and d2 2039 - recomputed, all match published values. No count deeper than 2.",
   "handling": "sound",
   "observed": true,
   "evidence": "npm test; read test/chess.test.js; perft.js recomputation",
   "spec": "open",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-11",
   "behaviour": "Results depend only on the FEN and move: F = 'rnbqkbnr/1pp1pppp/p7/3pP3/8/8/PPPP1PPP/RNBQKBNR w KQkq d6 0 3'; legalMoves (31 moves incl. e5d6), status 'ongoing', applyMove e5d6 identical before and after interleaving another game, branching e5d6 and g1f3, and a rejected e5e7 (IllegalMoveError); identical in a fresh node process. Mutating the returned array does not affect later calls.",
   "handling": "sound",
   "observed": true,
   "evidence": "node .audit-probes/p3.js (U-11 block) and a separate node -e with only F",
   "spec": "decided-unmarked",
   "told": "yes",
   "told_where": "README.md: \"Save the full six-field FEN to resume play in a fresh Node.js process or pass it to `applyMove` more than once to explore different continuations. Calls on other positions and rejected moves leave the saved position usable.\""
  },
  {
   "id": "U-12",
   "behaviour": "Illegal and malformed moves are tested, asserting the class (illegal UCI and moves that expose a king throw IllegalMoveError: e2e5, e7e5, e2e9, a1a3, e2e4q, a pinned-rook move; promotion requires a lowercase piece choice and places it in the mover’s color: a7a8, a7a8Q, a7a8k; missing and non-string moves throw IllegalMoveError without coercion: missing, undefined, null, array, objects, String object, conversion hooks; castling requires a safe king route, a clear path, rights and a rook; en passant can answer a pawn check but cannot reveal a rook check; a saved FEN supports independent branches and resumes in a fresh process). No test passes an invalid or impossible FEN. The class assertions do not even guard the export (removing IllegalMoveError from exports leaves the suite green).",
   "handling": "acceptable",
   "observed": true,
   "evidence": "read test/chess.test.js; S-17 break run",
   "spec": "silent",
   "told": "no",
   "told_where": ""
  }
 ],
 "extras": [
  {
   "what": "Strict FEN validation with descriptive errors (field syntax, rank count and width, both kings present, canonical KQkq order, ep rank 3/6, fullmove >= 1)",
   "where": "src/chess.js parseFen",
   "worth": "value",
   "why": "Malformed FENs fail loudly instead of giving a confident wrong answer; not asked for."
  },
  {
   "what": "Non-string moves rejected with IllegalMoveError without invoking or reading conversion hooks",
   "where": "src/chess.js applyMove (strict ===), test missing and non-string moves throw IllegalMoveError without coercion, spec C-54..C-56",
   "worth": "neutral",
   "why": "Harmless and consistent, but guards an exotic case; the test for it is the most intricate in the suite."
  },
  {
   "what": "A separate acceptance suite (rules.cjs, maintainer.cjs with the 50 ms / 2 s timing checks, suite-probe.cjs, npm-probe.cjs, fixtures.cjs) not run by npm test",
   "where": "acceptance/",
   "worth": "neutral",
   "why": "Carries the only timing assertions, but npm test does not run it and README does not mention it, so a maintainer may not know it exists."
  },
  {
   "what": "BigInt halfmove and fullmove counters",
   "where": "src/chess.js parseFen/applyMove",
   "worth": "neutral",
   "why": "Arbitrarily large clocks round-trip exactly; no user-visible effect in normal play."
  }
 ],
 "spec_notes": "The spec states every stated item (C-1 to C-52) and marks as Open the invalid/impossible FEN contract (C-3), the standard positions and depths for move counts (C-50) and the timing protocol (C-51, C-52). Decided without marking as the builder's choice: castling rights honoured only with king and rook on home squares (C-18) and ep only with the pushed pawn beside the target (C-20); rejection of every move form other than lowercase UCI including bare and uppercase promotions (C-21, C-37); the 'no conversion hooks' rule for non-string moves (C-55, C-56, sourced to discovery, not the request); the C-53 saved-FEN clause. C-31 pins the castling field to KQkq order (the product also rejects other orders on input, which the spec does not say). Nothing contradicts the request. C-52 requires the count to use applyMove, which a correct product need not share for the timing measurement.",
 "tests_notes": "Tests cover several behaviours at once: 'a saved FEN supports independent branches and resumes in a fresh process' (branching, interleaving, rejection, non-string move, fresh process via execFileSync), 'castling requires a safe king route, a clear path, rights and a rook' (check, path, rights, rook), 'promotion requires a lowercase piece choice and places it in the mover’s color' and 'missing and non-string moves throw IllegalMoveError without coercion'. assert.throws(fn, IllegalMoveError) is the only check of the error class, so removing the export leaves every test green (S-17 proved passes). No test times legalMoves or the depth-2 count (S-38, S-39 unguarded under npm test). No invalid-FEN test. The conversion-hook test asserts that Symbol.toPrimitive/toString are never called, which another correct build that, for example, String()-coerced and then rejected would fail. Otherwise the tests use only the public API (exact FEN strings, which any correct build must produce) and are not tied to file layout, private functions or timing.",
 "maintainer": "The rules live in one 300-line file where legality is a pseudo-legal generator plus a single isAttacked filter, and castling safety reuses boardAfter with a special crossing step; a change to boardAfter or isAttacked silently affects check, castling and en passant at once. The suite only checks perft to depth 2, so subtle generator bugs (pins, ep discoveries, corner-rook rights at depth) would pass npm test, and the timing limits are checked only in the separate acceptance/ folder that npm test does not run."
}
```

## Audit of delivery Y

```json
{
 "code": "Y",
 "stated": [
  {
   "id": "S-1",
   "built": "yes",
   "observed": true,
   "evidence": "require('./src/chess.js') from the package root loads; exports startFen, legalMoves, applyMove, status, IllegalMoveError",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-2",
   "built": "yes",
   "observed": true,
   "evidence": "loaded with require() (CommonJS, module.exports); 'use strict' CJS file",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-3",
   "built": "yes",
   "observed": true,
   "evidence": "package.json has no dependencies field; src/chess.js has no require() calls; loaded with no node_modules present",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-4",
   "built": "yes",
   "observed": true,
   "evidence": "package.json scripts.test = 'node --test'; npm test prints 'npm notice run node --test' and runs 8 tests",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-5",
   "built": "yes",
   "observed": true,
   "evidence": "every function takes/returns FEN strings: applyMove(startFen(),'e2e4') -> 'rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1'",
   "spec": "stated",
   "proved": "fails",
   "proved_by": "parseFen: changed `typeof fen !== 'string'` to `=== 'string'` (FEN strings rejected); TC-1..TC-8 all failed; restored, 8/8 pass"
  },
  {
   "id": "S-6",
   "built": "yes",
   "observed": true,
   "evidence": "startFen() -> 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-7",
   "built": "yes",
   "observed": true,
   "evidence": "legalMoves(startFen()) -> 20 moves; perft via legalMoves/applyMove matches published counts: start d3 8902, d4 197281; Kiwipete d1 48, d2 2039, d3 97862; position 3 d4 43238; position 4 d3 9467; position 5 d3 62379; position 6 d3 89890",
   "spec": "stated",
   "proved": "fails",
   "proved_by": "removed knight step 33 from KNIGHT_STEPS; TC-1, TC-7, TC-8 failed; restored, 8/8 pass"
  },
  {
   "id": "S-8",
   "built": "yes",
   "observed": true,
   "evidence": "start moves listed as a2a3,a2a4,b1a3,...,h2h4 (from+to squares)",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-9",
   "built": "yes",
   "observed": true,
   "evidence": "legalMoves('4k3/P7/8/8/8/8/8/4K3 w - - 0 1') -> a7a8b,a7a8n,a7a8q,a7a8r,...",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-10",
   "built": "yes",
   "observed": true,
   "evidence": "returned arrays equal their own .sort() (start position and others); e.g. a7a8b,a7a8n,a7a8q,a7a8r,e1d1...",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-11",
   "built": "yes",
   "observed": true,
   "evidence": "applyMove(startFen(),'e2e4') returns a six-field FEN string with placement and side updated",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-12",
   "built": "yes",
   "observed": true,
   "evidence": "on 'r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1': e1g1 -> 'R4RK1 b kq', e1f1 -> 'kq', a1a2 -> 'Kkq', h1h8 (captures corner rook) -> 'Qq'; rook leaving and returning keeps rights lost ('Qq'); b7a8q capturing a8 rook -> 'k'",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-13",
   "built": "yes",
   "observed": true,
   "evidence": "e2e4 -> e3, e7e5 -> e6, d7d5 -> d6; next quiet move -> '-'; after capture e5d6 ep -> '-'",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-14",
   "built": "yes",
   "observed": true,
   "evidence": "g1f3 g8f6 f3g1 f6g8 from start -> '... w KQkq - 4 3'; pawn move/capture resets to 0 ('4k3/8/8/8/8/8/3p4/4K3 w - - 7 30' e1d2 -> '... b - - 0 30'); castling increments",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-15",
   "built": "yes",
   "observed": true,
   "evidence": "increments after Black only: e2e4 '0 1', e7e5 '0 2', g1f3 '1 2', b8c6 '2 3'",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-16",
   "built": "yes",
   "observed": true,
   "evidence": "applyMove(startFen(), 'e2e5'|'a1a3'|'e1e2'|'e7e5') -> throws IllegalMoveError 'Illegal move: e2e5' etc.",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-17",
   "built": "yes",
   "observed": true,
   "evidence": "Object.keys(require('./src/chess.js')) includes IllegalMoveError; caught error instanceof c.IllegalMoveError === true",
   "spec": "stated",
   "proved": "passes",
   "proved_by": "removed IllegalMoveError from module.exports; suite still 8/8 pass (assert.throws with an undefined matcher only checks that something is thrown); restored, 8/8 pass"
  },
  {
   "id": "S-18",
   "built": "yes",
   "observed": true,
   "evidence": "applyMove(startFen(),'a2a4') -> '... b KQkq a3 0 1' with no black pawn able to capture; then h7h5 -> 'h6'",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-19",
   "built": "yes",
   "observed": true,
   "evidence": "status: start 'ongoing'; after e2e4 f7f6 d1h5 'check'; fool's and scholar's mate 'checkmate'; '7k/5Q2/6K1/8/8/8/8/8 b - - 0 1' 'stalemate'",
   "spec": "stated",
   "proved": "fails",
   "proved_by": "status: checkmate branch changed to return 'check'; TC-3 failed; restored, 8/8 pass"
  },
  {
   "id": "S-20",
   "built": "yes",
   "observed": true,
   "evidence": "all perft counts above match published values (knight, bishop, rook, queen, king, pawn moves); pinned bishop '4k3/4r3/8/8/8/8/4B3/4K3 w' only king moves listed",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-21",
   "built": "yes",
   "observed": true,
   "evidence": "'r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1' lists e1c1 and e1g1; black e8g8 -> 'r4rk1/... w KQ - 1 2', e8c8 -> '2kr3r/... w KQ - 1 2'",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-22",
   "built": "yes",
   "observed": true,
   "evidence": "'r3k3/8/8/8/4r3/8/8/R3K2R w KQ - 0 1' (in check): status 'check', king moves e1d1,e1d2,e1f1,e1f2 only; applyMove e1g1 -> IllegalMoveError; '... 3N4 ... b kq' knight check: no e8g8/e8c8",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-23",
   "built": "yes",
   "observed": true,
   "evidence": "'4k3/8/8/8/8/8/5r2/R3K2R w KQ - 0 1' (f1 attacked): e1g1 absent, applyMove throws IllegalMoveError, e1c1 present; d1 attacked: e1c1 absent and throws",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-24",
   "built": "yes",
   "observed": true,
   "evidence": "'4k3/8/8/8/8/8/6r1/R3K2R w KQ - 0 1' (g1 attacked): e1g1 absent and throws; c1 attacked: e1c1 absent and throws; b1 attacked only: e1c1 still listed (correct)",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-25",
   "built": "yes",
   "observed": true,
   "evidence": "castles appear and are accepted only as e1g1, e1c1, e8g8, e8c8; 'e1h1' -> IllegalMoveError",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-26",
   "built": "yes",
   "observed": true,
   "evidence": "after e2e4 a7a6 e4e5 d7d5: legal e5d6, applyMove -> 'rnbqkbnr/1pp1pppp/p2P4/8/8/8/PPPP1PPP/RNBQKBNR b KQkq - 0 3' (d5 pawn removed); black d4e3 likewise; expires after one move; horizontal-pin ep '8/8/8/KPp4r/8/8/8/7k w - c6 0 1' b5c6 refused",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-27",
   "built": "yes",
   "observed": true,
   "evidence": "'3k4/4P3/8/8/8/8/8/4K3 w - - 0 1' e7e8q/r/b/n -> Q/R/B/N on e8; black b2a1q capture -> 'q3K3' on rank 1",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-28",
   "built": "yes",
   "observed": true,
   "evidence": "after e2e4 f7f6 d1h5: status 'check', legalMoves ['g7g6']",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-29",
   "built": "yes",
   "observed": true,
   "evidence": "fool's mate (f2f3 e7e5 g2g4 d8h4) and scholar's mate: status 'checkmate', legalMoves []; back-rank '4R1k1/5ppp/8/8/8/8/8/6K1 b' checkmate",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-30",
   "built": "yes",
   "observed": true,
   "evidence": "'7k/5Q2/6K1/8/8/8/8/8 b - - 0 1' and 'k7/8/1Q6/8/8/8/8/7K b - - 0 1' -> 'stalemate', legalMoves []",
   "spec": "stated",
   "proved": "fails",
   "proved_by": "status: no-move non-check branch changed to return 'ongoing'; TC-3 failed; restored, 8/8 pass"
  },
  {
   "id": "S-31",
   "built": "yes",
   "observed": true,
   "evidence": "TC-3 plays f2f3 e7e5 g2g4 d8h4, asserts exact FEN, status checkmate and no legal moves; npm test passes it",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-32",
   "built": "yes",
   "observed": true,
   "evidence": "TC-3 plays e2e4 e7e5 f1c4 b8c6 d1h5 g8f6 h5f7, asserts exact FEN, checkmate, no moves",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-33",
   "built": "yes",
   "observed": true,
   "evidence": "TC-4 asserts all four castles with exact FENs, seven refused castles (out of, through, into check, blocked, missing rook, no rights) and rights after rook/king moves and a1a8 capture",
   "spec": "absent",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-34",
   "built": "yes",
   "observed": true,
   "evidence": "TC-5 covers white and black ep with exact FENs, expiry, a target with no pawn, and a horizontally pinned ep",
   "spec": "absent",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-35",
   "built": "yes",
   "observed": true,
   "evidence": "TC-6 covers quiet and capture promotions to b, n, q, r for both colors with exact FENs, and rejects bare and 'k' suffix",
   "spec": "absent",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-36",
   "built": "yes",
   "observed": true,
   "evidence": "TC-3 asserts status 'stalemate' and [] for '7k/5Q2/6K1/8/8/8/8/8 b - - 0 1'",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-37",
   "built": "yes",
   "observed": true,
   "evidence": "TC-7 asserts perft start 20/400/8902, Kiwipete 48/2039/97862, position 3 14/191/2812; all match published values",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-38",
   "built": "yes",
   "observed": true,
   "evidence": "legalMoves on Kiwipete 0.133 ms cold, avg 0.018 ms over 1000 calls; another middlegame FEN 0.093 ms",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-39",
   "built": "yes",
   "observed": true,
   "evidence": "perft(start, 2) = 400 in 2.2 ms in a fresh process (TC-8 reports 0.29 ms)",
   "spec": "stated",
   "proved": "fails",
   "proved_by": "applyMove: busy-wait 110 ms when the position is white to move, fullmove 1, rights KQkq (start position); TC-8 failed at 2200 ms; restored, 8/8 pass"
  },
  {
   "id": "S-40",
   "built": "yes",
   "observed": true,
   "evidence": "npm test: 8 tests, 8 pass, 0 fail, exit 0",
   "spec": "absent",
   "proved": "not-asked",
   "proved_by": ""
  }
 ],
 "unstated": [
  {
   "id": "U-1",
   "behaviour": "Non-strings (no arg, undefined, null, 42) throw TypeError 'Expected a FEN string' from legalMoves/status/applyMove (applyMove with no arguments at all throws IllegalMoveError 'Expected a legal UCI move string' because the move is checked first). '', 'not-a-fen', 7 ranks, side 'x', bad castling/ep/counter fields throw Error 'Invalid FEN fields'; '9' or unknown piece or long rank 'Invalid FEN placement'; no kings / two white kings 'Invalid FEN kings'. Leading/trailing whitespace and newline tolerated. Impossible but parseable positions (pawn on 8th or 1st rank, side not to move in check) return values: pawn on e8 ignored for moves, status 'ongoing'; side-not-to-move-in-check gives 'ongoing' and 16 moves.",
   "handling": "sound",
   "observed": true,
   "evidence": "probe script over all listed inputs for legalMoves, status, applyMove(f,'e2e4'); identical class/message across the three functions",
   "spec": "decided-unmarked",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-3",
   "behaviour": "Only exact lowercase UCI strings from legalMoves are accepted. 'E2E4', ' e2e4', 'e2e4 ', 'e4', 'e2-e4', 'e2xe4', 'e2e4q', 'e2e9' -> IllegalMoveError 'Illegal move: <move>'; 42/undefined -> IllegalMoveError 'Expected a legal UCI move string'. On '4k3/4P3/...' every e7e8x is illegal (e8 is occupied by the king, so the probe's promotions are correctly refused); on '3k4/4P3/8/8/8/8/8/4K3 w - - 0 1' e7e8q/r/b/n give Q/R/B/N on e8, 'e7e8Q' and bare 'e7e8' rejected. 'e1h1' rejected.",
   "handling": "sound",
   "observed": true,
   "evidence": "probe script outputs listed",
   "spec": "decided-unmarked",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-4",
   "behaviour": "class IllegalMoveError extends Error; instanceof IllegalMoveError and Error both true; constructor.name and name 'IllegalMoveError'; message 'Illegal move: e2e5' / 'Illegal move: a1a3'; stack present; own keys ['name']; non-string move message 'Expected a legal UCI move string'.",
   "handling": "sound",
   "observed": true,
   "evidence": "try { c.applyMove(c.startFen(),'e2e5') } catch(e) {...} -> true true IllegalMoveError IllegalMoveError 'Illegal move: e2e5' true ['name']",
   "spec": "silent",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-5",
   "behaviour": "Castling right letters are not trusted without the king on e1/e8 and the rook on its corner: 'K' with no rook, KQ with no h1 rook, king on e2 -> no e1g1, applyMove e1g1 throws IllegalMoveError, status 'ongoing'. En-passant square is used only when it is on the capturing side's ep rank and the passed pawn is present: 'e3' with white to move ignored (no capture onto e3); d6 with no d5 pawn -> e5d6 not listed and refused.",
   "handling": "sound",
   "observed": true,
   "evidence": "probe script outputs listed",
   "spec": "decided-unmarked",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-7",
   "behaviour": "All published perft counts match: start d3 8902, d4 197281; Kiwipete d1 48, d2 2039, d3 97862; position 3 d4 43238; plus position 4 d3 9467, position 5 d3 62379, position 6 d3 89890.",
   "handling": "sound",
   "observed": true,
   "evidence": "perft helper built on legalMoves/applyMove (perf.js), each count OK",
   "spec": "decided-unmarked",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-9",
   "behaviour": "npm test: exit 0, 8 tests in test/chess.test.js. Fool's/Scholar's mate: exact UCI move lines, exact final FENs, status checkmate and empty legalMoves asserted. Castling (TC-4): four castles with exact FENs, seven refusals (in check, f1/g1 attacked, black through d8, b1 blocked, missing rook, no rights) both by legalMoves and IllegalMoveError, b-file-attacked queenside allowed, rights after h1h2, e1e2, a1a8 capture. En passant (TC-5): white and black, exact FENs, expiry, missing-pawn target, horizontally pinned ep. Promotion (TC-6): b/n/q/r quiet and capture for both colors, exact FENs, bare and 'k' suffix refused. Stalemate (TC-3): one FEN, status and []. Move counts (TC-7): start 20/400/8902, Kiwipete 48/2039/97862, position 3 14/191/2812, recomputed and matching published values.",
   "handling": "sound",
   "observed": true,
   "evidence": "ran npm test; read test/chess.test.js; recomputed every asserted perft count",
   "spec": "decided-unmarked",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-11",
   "behaviour": "Stateless: same FEN gives the same legal moves, status and applyMove result after interleaved calls on another game, after a rejected move (e5e7 -> IllegalMoveError) and in a fresh Node process.",
   "handling": "sound",
   "observed": true,
   "evidence": "F = 'rnbqkbnr/1pp1pppp/p7/3pP3/8/8/PPPP1PPP/RNBQKBNR w KQkq d6 0 3'; results compared equal in-process and in a second process",
   "spec": "decided-unmarked",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-12",
   "behaviour": "Tests cover both error paths: illegal/malformed/non-string moves asserted with IllegalMoveError class (TC-2 'e2e5','e7e5','a1a3','e1e2','e2e4q','E2E4','e2e4\\n',null; TC-2 pinned rook; TC-4 refused castles; TC-5; TC-6 bare and 'k' promotion), and invalid FENs (TC-2: legalMoves(null) TypeError; no kings /Invalid FEN kings/; '4K4' /Invalid FEN rank width/; halfmove 'x' /Invalid FEN fields/) asserted by message regex.",
   "handling": "sound",
   "observed": true,
   "evidence": "read test/chess.test.js; npm test passes these",
   "spec": "decided-unmarked",
   "told": "no",
   "told_where": ""
  }
 ],
 "extras": [
  {
   "what": "Arbitrary-precision halfmove/fullmove counters (BigInt)",
   "where": "src/chess.js parseFen/formatFen",
   "worth": "neutral",
   "why": "Exact for absurd counters; no ordinary use needs it, but it costs nothing."
  },
  {
   "what": "Tolerance of leading/trailing whitespace and multiple spaces in FEN",
   "where": "src/chess.js parseFen (trim, split on \\s+)",
   "worth": "neutral",
   "why": "Lenient input handling the inventory allows; no effect on valid FENs."
  },
  {
   "what": "FEN validation with distinct messages (fields, placement, rank width, kings)",
   "where": "src/chess.js parseFen",
   "worth": "value",
   "why": "Malformed FENs fail fast with descriptive errors instead of wrong answers."
  }
 ],
 "spec_notes": "No contradiction with the request. The spec decides several unstated points in ordinary requirement lines without marking them as the builder's choice: 'Malformed FEN may raise an input error' and 'Historical reachability is outside the contract' (U-1), 'Promotion requires a q/r/b/n suffix' (bare promotion rejected, U-3), castling 'requires the right, the rook' and en passant 'requires a valid target' (U-5). It pins Kiwipete as 'the middlegame position' and node:perf_hooks timing, and the architecture pins BigInt counters and 0x88 indexing; a correct product need not share these. It names castling, en passant and promotion tests only as 'special cases', and does not say npm test must pass. R-4 adds that repetition and draw adjudication are out of scope, which the request does not mention but does not contradict. There is no customer-facing README or delivery note.",
 "tests_notes": "TC-2, TC-3 and TC-4 each bundle many behaviours (counters, double pushes, illegal moves and invalid FENs in TC-2; both mates, check and stalemate in TC-3). TC-2 asserts this build's exact error wording (/Invalid FEN kings/, /Invalid FEN rank width/, /Invalid FEN fields/) and TypeError for legalMoves(null); another correct build with other wording or error class would fail. TC-2's counters at 9007199254740993 require arbitrary-precision counters; a correct build using Number would fail. TC-2's rejection of 'e2e4\\n' and TC-4/TC-5's inconsistent-rights and missing-pawn FENs assume the FEN is accepted and the move refused; a build that rejects such FENs or trims moves would fail. The IllegalMoveError export is not really checked: assert.throws(fn, undefined) passes when the export is removed (proved). TC-8 times in-process with generous margins, low flake risk.",
 "maintainer": "Everything is in one 315-line file on a 0x88 board, where move objects carry optional fields (captureSquare, rookFrom/rookTo, target, promotion) that boardAfter and applyMove interpret implicitly, so a new move kind must be threaded through several functions. Castling-rights removal keys off fixed square indices (ROOK_RIGHTS) and the castling path checks are hand-coded offsets, which are easy to break unnoticed outside the positions the tests cover."
}
```

## Audit of delivery Z

```json
{
 "code": "Z",
 "stated": [
  {
   "id": "S-1",
   "built": "yes",
   "observed": true,
   "evidence": "node -e \"require('./src/chess.js')\" from the package root loads; exports startFen, legalMoves, applyMove, status, IllegalMoveError",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-2",
   "built": "yes",
   "observed": true,
   "evidence": "require('./src/chess.js') returns the object; module.exports assignment, 'use strict' CommonJS",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-3",
   "built": "yes",
   "observed": true,
   "evidence": "src/chess.js has no require() calls (grep found none); package.json has no dependencies field; runs with no node_modules",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-4",
   "built": "yes",
   "observed": true,
   "evidence": "package.json scripts.test is \"node --test\"; npm test prints \"run node --test\"",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-5",
   "built": "yes",
   "observed": true,
   "evidence": "legalMoves/applyMove/status take six-field FEN strings; applyMove(startFen(),'e2e4') returns 'rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1'",
   "spec": "stated",
   "proved": "fails",
   "proved_by": "formatFen join(' ') changed to join('_') (applyMove returned 'rnbqkbnr/.../RNBQKBNR_b_KQkq_e3_0_1'); 12 tests failed incl. 'FEN metadata tracks double pushes, turn changes and target expiry', 'both colors can castle on either wing and relocate their rook'; restored, 14/14 pass"
  },
  {
   "id": "S-6",
   "built": "yes",
   "observed": true,
   "evidence": "startFen() -> 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-7",
   "built": "yes",
   "observed": true,
   "evidence": "legalMoves(startFen()) -> 20 moves; perft via legalMoves/applyMove matches published counts: start d3 8902, d4 197281; Kiwipete d1 48, d2 2039, d3 97862; position 3 d4 43238, d5 674624; position 4 d3 9467; position 5 d3 62379",
   "spec": "stated",
   "proved": "fails",
   "proved_by": "pawnMoves double-push start row (color === 'w' ? 6 : 1) changed to (? 5 : 1) (start position then gave 12 moves); 7 tests failed incl. 'the standard position has 20 sorted moves and 400 two-ply continuations' and 'Kiwipete has 48 legal moves...'; restored, 14/14 pass"
  },
  {
   "id": "S-8",
   "built": "yes",
   "observed": true,
   "evidence": "start moves returned as [\"a2a3\",\"a2a4\",\"b1a3\",...,\"h2h4\"], 4-char lowercase UCI",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-9",
   "built": "yes",
   "observed": true,
   "evidence": "legalMoves('4k3/P7/8/8/8/8/8/4K3 w - - 0 1') -> [a7a8b,a7a8n,a7a8q,a7a8r,e1d1,...]; with b8 rook also a7b8b/n/q/r",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-10",
   "built": "yes",
   "observed": true,
   "evidence": "start list equals its own .sort(); promotion list ordered b,n,q,r",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-11",
   "built": "yes",
   "observed": true,
   "evidence": "applyMove(startFen(),'e2e4') -> 'rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1'",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-12",
   "built": "yes",
   "observed": true,
   "evidence": "on 'r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1': e1g1 -> '... b kq - 1 1'; a1a2 -> 'b Kkq'; h1h8 (captures h8 rook) -> 'b Qq'; e1e2 -> 'b kq'; black e8g8 -> 'w KQ'; b7a8q capturing a8 rook -> 'b k'",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-13",
   "built": "yes",
   "observed": true,
   "evidence": "e2e4 -> target e3; then a7a6 -> target '-'; g1f3,a7a5 -> 'a6'; after d7d5 the d6 target allows e5d6 and expires after h2h3 (no e5d6 next turn)",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-14",
   "built": "yes",
   "observed": true,
   "evidence": "g1f3 g8f6 f3g1 -> halfmove 3; capture a1a2 from halfmove 12 -> 0; e1g1 from 7 -> 8 (castle counts as quiet); pawn moves reset to 0",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-15",
   "built": "yes",
   "observed": true,
   "evidence": "e2e4 keeps fullmove 1; e2e4 a7a6 -> 2; black castle from 12 -> 13",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-16",
   "built": "yes",
   "observed": true,
   "evidence": "applyMove(startFen(),'e2e5') throws IllegalMoveError 'Illegal move: e2e5'; castling out of/into check also throws IllegalMoveError",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-17",
   "built": "yes",
   "observed": true,
   "evidence": "typeof c.IllegalMoveError === 'function'; 'class IllegalMoveError extends Error'; thrown errors are instanceof it",
   "spec": "stated",
   "proved": "passes",
   "proved_by": "removed IllegalMoveError from module.exports (typeof c.IllegalMoveError then 'undefined'); suite still 14/14 pass because assert.throws(fn, undefined) accepts any throw; restored, 14/14 pass"
  },
  {
   "id": "S-18",
   "built": "yes",
   "observed": true,
   "evidence": "applyMove(startFen(),'e2e4') sets e3 with no black pawn able to capture; g1f3 a7a5 sets a6",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-19",
   "built": "yes",
   "observed": true,
   "evidence": "status: startFen()->'ongoing'; after e2e4 f7f6 d1h5 ->'check'; fool's mate ->'checkmate'; '7k/5Q2/6K1/8/8/8/8/8 b - - 0 1' ->'stalemate'",
   "spec": "stated",
   "proved": "fails",
   "proved_by": "status line 'if (hasReply) return checked ? 'check' : 'ongoing';' changed to 'return 'ongoing';' (check position then gave 'ongoing'); failed 'check with a legal reply is distinct from ongoing play' and 'en passant can answer a pawn check but cannot reveal a rook check'; restored, 14/14 pass"
  },
  {
   "id": "S-20",
   "built": "yes",
   "observed": true,
   "evidence": "all piece types move correctly; perft counts at depth 3-5 on five published positions all match (see S-7); pinned knight on e2 has no moves; double check allows only king moves",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-21",
   "built": "yes",
   "observed": true,
   "evidence": "'r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1' lists e1c1 and e1g1; applied: R4RK1 and 2KR3R; black e8g8 -> r4rk1, e8c8 -> 2kr3r",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-22",
   "built": "yes",
   "observed": true,
   "evidence": "'r3k2r/8/8/8/8/8/4r3/R3K2R w KQkq - 0 1' king moves [e1d1,e1e2,e1f1], no castle; applyMove('4k3/8/8/8/8/8/4r3/R3K2R w KQ - 0 1','e1g1') throws IllegalMoveError; black in check from e1 rook: no e8g8/e8c8",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-23",
   "built": "yes",
   "observed": true,
   "evidence": "rook on f2 attacking f1: e1g1 absent, e1c1 present; rook on d2 attacking d1: e1c1 absent, e1g1 present; rook on b2 attacking b1 only: both castles present",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-24",
   "built": "yes",
   "observed": true,
   "evidence": "rook on g2: e1g1 absent; rook on c2: e1c1 absent; applyMove e1g1 there throws IllegalMoveError",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-25",
   "built": "yes",
   "observed": true,
   "evidence": "castles are listed and accepted as e1g1, e1c1, e8g8, e8c8; e1h1 rejected with IllegalMoveError",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-26",
   "built": "yes",
   "observed": true,
   "evidence": "after e2e4 a7a6 e4e5 d7d5, legalMoves includes e5d6; applyMove -> 'rnbqkbnr/1pp1pppp/p2P4/8/8/8/PPPP1PPP/RNBQKBNR b KQkq - 0 3'; black d4e3 after e2e4 removes e4 pawn; horizontal-pin en passant on '8/8/8/K2pP2r/8/8/8/7k w - d6 0 1' rejected",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-27",
   "built": "yes",
   "observed": true,
   "evidence": "'4k3/P7/8/8/8/8/8/4K3 w - - 0 1': a7a8q/r/b/n give Q/R/B/N on a8; black a2a1n gives n",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-28",
   "built": "yes",
   "observed": true,
   "evidence": "status('4k3/8/8/8/8/8/4r3/4K3 w - - 0 1') -> 'check'; moves leaving king in check are excluded (pinned knight, king next to defended rook)",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-29",
   "built": "yes",
   "observed": true,
   "evidence": "fool's mate (f2f3 e7e5 g2g4 d8h4) -> 'checkmate', legalMoves []; scholar's mate -> 'checkmate'; back-rank mate R5k1 -> 'checkmate'",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-30",
   "built": "yes",
   "observed": true,
   "evidence": "status('7k/5Q2/6K1/8/8/8/8/8 b - - 0 1') -> 'stalemate', legalMoves []; 'k7/8/1Q6/8/8/8/8/7K b' -> 'stalemate'",
   "spec": "stated",
   "proved": "fails",
   "proved_by": "status line 'return checked ? 'checkmate' : 'stalemate';' changed to ': 'ongoing'' (stalemate position then gave 'ongoing'); failed 'a safe king with no legal move is stalemated'; restored, 14/14 pass"
  },
  {
   "id": "S-31",
   "built": "yes",
   "observed": true,
   "evidence": "npm test runs 'Fool’s mate checkmates White' (f2f3 e7e5 g2g4 d8h4, asserts checkmate and [] moves) - passes",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-32",
   "built": "yes",
   "observed": true,
   "evidence": "'Scholar’s mate checkmates Black' (e2e4 e7e5 f1c4 b8c6 d1h5 g8f6 h5f7, asserts checkmate and []) - passes",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-33",
   "built": "yes",
   "observed": true,
   "evidence": "'both colors can castle on either wing and relocate their rook' and 'castling requires a safe king route, a clear path, rights and a rook' pass",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-34",
   "built": "yes",
   "observed": true,
   "evidence": "'en passant removes the passed pawn for either color' and 'en passant can answer a pawn check but cannot reveal a rook check' pass",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-35",
   "built": "yes",
   "observed": true,
   "evidence": "'promotion requires a lowercase piece choice and places it in the mover’s color' (all four pieces by capture, black knight) passes",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-36",
   "built": "yes",
   "observed": true,
   "evidence": "'a safe king with no legal move is stalemated' passes",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-37",
   "built": "yes",
   "observed": true,
   "evidence": "start position 20 and depth-2 400; Kiwipete 48 and 2039 asserted, both match published values; tests pass",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-38",
   "built": "yes",
   "observed": true,
   "evidence": "legalMoves on 'r1bq1rk1/pp2bppp/2n1pn2/2pp4/3P4/2PBPN2/PP1N1PPP/R1BQ1RK1 w - - 0 8' 0.53 ms cold, 0.033 ms average over 100; Kiwipete 0.04 ms",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  },
  {
   "id": "S-39",
   "built": "yes",
   "observed": true,
   "evidence": "depth-2 count from start (21 legalMoves calls + 20 applyMove) = 400 in 0.64 ms; depth 4 perft 175 ms",
   "spec": "stated",
   "proved": "passes",
   "proved_by": "inserted a 100 ms busy-wait at the top of legalMoves (depth-2 count then took 2100 ms); suite still 14/14 pass (duration 8.8 s, no timing check); restored, 14/14 pass"
  },
  {
   "id": "S-40",
   "built": "yes",
   "observed": true,
   "evidence": "npm test: 14 tests, 14 pass, 0 fail, exit code 0",
   "spec": "stated",
   "proved": "not-asked",
   "proved_by": ""
  }
 ],
 "unstated": [
  {
   "id": "U-1",
   "behaviour": "Non-string or missing FEN: TypeError from inside the parser (\"Cannot read properties of undefined (reading 'trim')\", \"fen.trim is not a function\"). Malformed FEN (empty, 'not-a-fen', 7 ranks, side 'x', 9-square rank, unknown letter, 5 fields): plain Error with 'Invalid FEN fields' / 'Invalid FEN placement' / 'Invalid FEN rank'. No kings: Error 'Missing king in FEN'. Trailing newline or surrounding spaces tolerated. Two white kings, pawn on rank 8 and side-not-to-move in check are accepted and answered (e.g. 'ongoing'). Same behaviour across legalMoves, status and applyMove.",
   "handling": "acceptable",
   "observed": true,
   "evidence": "node probe calling c.legalMoves(f), c.status(f), c.applyMove(f,'e2e4') in try/catch for each inventory input; e.g. legalMoves(null) -> TypeError; legalMoves('rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP w KQkq - 0 1') -> Error 'Invalid FEN placement'; status('4k3/8/8/8/8/8/4R3/4K3 w - - 0 1') -> 'ongoing'; status('4k3/8/8/8/8/8/8/4KK2 w - - 0 1') -> 'ongoing'",
   "spec": "open",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-3",
   "behaviour": "Only the exact lowercase UCI strings that legalMoves lists are accepted; 'E2E4', ' e2e4', 'e4', 'e2-e4', 'e2xe4', 'e2e4q', 'e2e9', 42, undefined, 'e7e8Q', bare 'e7e8' and 'e1h1' all throw IllegalMoveError. Explicit q/r/b/n give that piece (on a free e8: e7e8q -> Q, e7e8n -> N). On the inventory's '4k3/4P3/...' fixture every e7e8x is rejected because the black king blocks e8, which is correct.",
   "handling": "sound",
   "observed": true,
   "evidence": "applyMove(startFen(), m) for each value; applyMove('4k3/4P3/8/8/8/8/8/4K3 w - - 0 1', ...) all IllegalMoveError; applyMove('8/4P3/8/8/8/8/k7/4K3 w - - 0 1','e7e8q') -> '4Q3/...', 'e7e8Q' and 'e7e8' -> IllegalMoveError; applyMove('r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1','e1h1') -> IllegalMoveError",
   "spec": "decided-unmarked",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-4",
   "behaviour": "class IllegalMoveError extends Error; name 'IllegalMoveError'; message 'Illegal move: <move>' (names the move, not the FEN); has stack; own keys ['name'] only.",
   "handling": "sound",
   "observed": true,
   "evidence": "try { c.applyMove(c.startFen(),'e2e5') } catch(e) -> true true IllegalMoveError IllegalMoveError 'Illegal move: e2e5' true ['name']; same for a1a3",
   "spec": "silent",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-5",
   "behaviour": "Castling rights are trusted only when the king is on e1/e8 and the rook is on its corner: 'w K' with no rook, 'w KQ' with no h1 rook (e1c1 still offered with the a1 rook) and king on e2 never list e1g1, and applyMove e1g1 throws IllegalMoveError. An en-passant square no pawn could have produced (e3 with White to move; e6 with no black pawn on e5) is ignored.",
   "handling": "sound",
   "observed": true,
   "evidence": "legalMoves('4k3/8/8/8/8/8/8/4K3 w K - 0 1') -> [e1d1,e1d2,e1e2,e1f1,e1f2], status 'ongoing', applyMove e1g1 -> IllegalMoveError; same for the other two; legalMoves('rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR w KQkq e3 0 1') has no move onto e3; '4k3/8/8/3P4/8/8/8/4K3 w - e6 0 1' -> d5e6 IllegalMoveError",
   "spec": "decided-unmarked",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-7",
   "behaviour": "Every published perft count matches.",
   "handling": "sound",
   "observed": true,
   "evidence": "perft helper on legalMoves/applyMove: start d3 8902 (13 ms), d4 197281 (175 ms); Kiwipete d1 48, d2 2039, d3 97862 (57 ms); position 3 d4 43238, d5 674624; position 4 d3 9467; position 5 d3 62379 - all OK",
   "spec": "silent",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-9",
   "behaviour": "npm test: 14 tests in test/chess.test.js, all pass, exit 0. Fool's mate f2f3 e7e5 g2g4 d8h4 and scholar's mate e2e4 e7e5 f1c4 b8c6 d1h5 g8f6 h5f7, each asserting side to move, status 'checkmate' and legalMoves []. Castling: full resulting FENs for all four castles (rook moved, rights, clocks); out of/through/into check via rook on e8/f8/g8 (absent from legalMoves and applyMove throws); blocked b1, no rights, no rook; b8 attacked still allows e1c1; corner-rook capture and returning rooks. En passant: full FEN after e5d6 and black d4e3; ep answering a pawn check; ep exposing a rank rook check rejected. Promotion: all four pieces by capture onto b8 with full FEN, the 8 listed a7 moves, black a2a1n, and 'a7a8','a7a8Q','a7a8k' rejected. Stalemate: '7k/5K2/6Q1/8/8/8/8/8 b - - 0 1' status and []. Move counts: start 20 (exact list) and 400 at depth 2, Kiwipete 48 and 2039 at depth 2; recomputed, all match published values.",
   "handling": "sound",
   "observed": true,
   "evidence": "npm test output; test file read; counts recomputed with the perft helper (400, 48, 2039)",
   "spec": "decided-unmarked",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-11",
   "behaviour": "Results depend only on the FEN and move; interleaved other games, branches from the saved FEN and a rejected move leave it usable; a fresh process gives identical results.",
   "handling": "sound",
   "observed": true,
   "evidence": "F='rnbqkbnr/1pp1pppp/p7/3pP3/8/8/PPPP1PPP/RNBQKBNR w KQkq d6 0 3'; legalMoves/status/applyMove(F,'e5d6') before and after interleaved calls and applyMove(F,'e5e7') (IllegalMoveError) are identical (sha1 73eb8559...), and the same hash in a fresh node process given only F",
   "spec": "silent",
   "told": "no",
   "told_where": ""
  },
  {
   "id": "U-12",
   "behaviour": "The suite tests illegal moves (e2e5, e7e5, e2e9, a1a3, e2e4q in the start position, a pinned rook move, castles out of/through/into check, 'a7a8', 'a7a8Q', 'a7a8k', e5d6/g5f6 exposing check) asserting assert.throws(..., IllegalMoveError). No test passes an invalid or impossible FEN; that error path has no test. The class check is weaker than it looks: with IllegalMoveError removed from the exports the matcher is undefined and every such assertion still passes.",
   "handling": "acceptable",
   "observed": true,
   "evidence": "read test/chess.test.js; S-17 break experiment showed the class assertions pass with the export removed",
   "spec": "silent",
   "told": "no",
   "told_where": ""
  }
 ],
 "extras": [
  {
   "what": "README.md with API summary and example",
   "where": "README.md",
   "worth": "value",
   "why": "accurately describes the four functions, UCI move format, castling/promotion notation and the en-passant convention"
  },
  {
   "what": "BigInt halfmove and fullmove clocks",
   "where": "src/chess.js parseFen/applyMove",
   "worth": "neutral",
   "why": "exact for any digit string; never matters in real games"
  },
  {
   "what": "FEN validation (field shapes, 8x8 board, both kings present) with descriptive Error messages; surrounding whitespace trimmed",
   "where": "src/chess.js parseFen",
   "worth": "value",
   "why": "malformed FENs are rejected instead of producing confident wrong answers"
  },
  {
   "what": "builders' working notes",
   "where": "[tool]/spec.md, [tool]/plan.md, [tool]/build-1.md",
   "worth": "neutral",
   "why": "process artefacts shipped beside the product; no runtime effect"
  }
 ],
 "spec_notes": "The specification does not contradict the request. C-3 marks invalid and impossible FEN handling as Open for the customer; the code nonetheless decides it (plain Error for malformed FENs and missing kings, TypeError for non-strings, impossible positions such as two kings or pawn on rank 8 accepted) without the spec recording that choice. Decided in ordinary requirement lines without marking: C-18 trusts castling rights only when king and rook are on their home squares; C-20 requires the opposing pawn behind the target for en passant; C-21/C-37 reject unsuffixed and non-lowercase promotion suffixes; C-31 fixes rights output order KQkq. The parser also rejects castling letters out of KQkq order, which the spec does not state. C-50, C-51 and C-52 mark the fixture list, the middlegame FEN and the timing protocol as Open. C-35 pins castling as a quiet move that increments the halfmove clock, which is the standard rule.",
 "tests_notes": "All 14 tests are in test/chess.test.js and use only the public API (no internals, file names or timing). Several tests cover multiple behaviours at once: 'FEN metadata tracks double pushes, turn changes and target expiry' checks en-passant target, halfmove, fullmove and side to move together; 'castling requires a safe king route, a clear path, rights and a rook' bundles out-of/through/into check, blocked path, missing rights and missing rook; 'promotion requires ...' covers listing, all four pieces and rejection. The IllegalMoveError assertions pass even when the class is not exported (assert.throws with an undefined matcher accepts any throw), so S-17 is not guarded. There are no timing tests for the 50 ms and 2 s limits, and no test for invalid FEN input. Exact FEN string assertions and the rejection of 'a7a8Q' and bare 'a7a8' would fail on another correct build that documented accepting uppercase or defaulting a bare promotion to a queen; the rest would hold for any correct build.",
 "maintainer": "The castling legality check in isLegal relies on a synthetic 'crossing' board built by boardAfter with the rook's destination square as the king's transit square, and castling-rights updates in remainingRights depend on the CORNERS table plus checking which piece stood on the corner; both are compact and easy to break subtly. Because there are no timing tests and the IllegalMoveError matcher is not really checked, regressions in performance or the error export would pass the suite unnoticed."
}
```

