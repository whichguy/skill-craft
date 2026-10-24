# Architecture

## Stack

Node.js CommonJS module with no dependencies; tests on `node:test`.

## Structure

`src/chess.js` (the engine) and `test/` (its tests).

## Decisions

- AD-1 Integer mailbox. Choice: each public function parses the FEN into a 64-entry integer array, works on it and serialises back. Why: simple and fast enough for NFR-1. Alternatives: bitboards (faster, much more code); a board object kept between calls (state the API does not have). Status: accepted.

## Interfaces and boundaries

`src/chess.js` exports `startFen()`, `legalMoves(fen)`, `applyMove(fen, move)`, `status(fen)` and `IllegalMoveError`. A position crosses the boundary only as a FEN string.
