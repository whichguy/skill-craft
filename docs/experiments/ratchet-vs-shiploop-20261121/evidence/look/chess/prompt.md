# One look at a delivered product

This folder ({work}) holds a product that was built and delivered for the request below. Every check passes. Its
builders' specification and working notes are in `docs/shiploop/`.

This look asks one question: now that the product runs, is there anything a user or an operator needs that it does
not do, or that it does without anyone having been told?

## The request
Build a chess rules engine as a Node.js module src/chess.js (CommonJS, no dependencies; npm test runs node --test). A position is a FEN string. startFen() returns the standard start position. legalMoves(fen) returns an array of every legal move for the side to move in UCI form (for example e2e4, and e7e8q for a promotion), sorted alphabetically. applyMove(fen, move) returns the FEN after the move, with correct castling rights, en-passant square, halfmove clock and fullmove number, or throws IllegalMoveError (a class the module also exports) when the move is not legal. The en-passant target square is set after every two-square pawn push, whether or not a capture is possible (the FEN-spec convention). status(fen) returns ongoing, check, checkmate or stalemate for the side to move. Implement all piece moves, castling on both sides (never out of, through or into check; in UCI it is the king's two-square move: e1g1, e1c1, e8g8, e8c8), en passant, promotion to q, r, b or n, check, checkmate and stalemate. Cover the rules with node --test tests in test/: known games (fool's mate, scholar's mate), castling, en passant, promotion, stalemate and move counts from standard test positions. Keep legalMoves on a middlegame position under 50 ms and a depth-2 legal-move count of the start position under 2 seconds. npm test must pass.

## What to weigh
- The product itself. Start it and use it as its users and operators would: the request's own examples, values at
  and just past each limit, wrong and odd input, the features next to what was asked, a restart, what its documents
  promise. Use it; do not only read it.
- The request, read once more for what it implies and the specification does not state.
- The specification and notes in `docs/shiploop/`, for a choice the builders made that the request did not settle.

## What to write
Write `docs/shiploop/look.md` and change nothing else: not the product, not a test, not another document.

**Shortfalls.** Each thing the product does not do that a user or an operator would care about and the request's
intent covers. For each: what is needed; the exact steps that show the product falling short (the commands or page
actions, what came back, what should have); and how much it matters: `high` (loses data, misleads a user or breaks
what worked), `medium` or `low`. A shortfall is not a new feature, a matter of taste or hardening nobody asked for.
If another correct product could behave differently and nobody would miss it, leave it out. Try what you suspect
before you write it: a shortfall you did not see happen does not belong here.

**Choices the customer was not told.** Each place where the request left something open, the product does
something reasonable there, and neither the request nor the documents delivered with the product (not counting
`docs/shiploop/`) say what it does. One line each: the open point, and what the product does.

Write the single line "Nothing found." under a heading whose list is empty.

## Conduct
Work only inside {work}; temporary files go in {tmp}. Use a free port you pick yourself and data files under
{tmp}. Stop every process you start, by its process id, before you finish; never stop processes by name.
