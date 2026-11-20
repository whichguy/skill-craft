#!/usr/bin/env node
// Hidden checks for the node-chess-engine step case (round 6): one check per run, through the module's public API
// only (startFen, legalMoves, applyMove, status, IllegalMoveError). The move counts are the standard published
// "perft" totals (the number of move sequences of a given length from a position), which any correct rules engine
// reproduces; the model's own spec asks only for the length-1 counts.
//
// Usage: node chess_hidden.js <product root> <check id>      exit 0 = pass; one line says what was seen
//        node chess_hidden.js --list
'use strict';
const path = require('path');

const POSITIONS = {
  start: 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1',
  kiwipete: 'r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1',
  position3: '8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1',
  position4: 'r3k2r/Pppp1ppp/1b3nbN/nP6/BBP1P3/q4N2/Pp1P2PP/R2Q1RK1 w kq - 0 1',
  position5: 'rnbq1k1r/pp1Pbppp/2p5/8/2B5/8/PPP1NnPP/RNBQK2R w KQ - 1 8',
  position6: 'r4rk1/1pp1qppp/p1np1n2/2b1p1B1/2B1P1b1/P1NP1N2/1PP1QPPP/R4RK1 w - - 0 10',
};
const PERFT = {
  'count-start-3': ['start', 3, 8902],
  'count-kiwipete-3': ['kiwipete', 3, 97862],
  'count-position3-4': ['position3', 4, 43238],
  'count-position4-3': ['position4', 3, 9467],
  'count-position5-3': ['position5', 3, 62379],
  'count-position6-3': ['position6', 3, 89890],
};
const GAMES = [
  ['e2e4 e7e5 g1f3 b8c6 f1b5 a7a6 b5a4 g8f6 e1g1', 'r1bqkb1r/1ppp1ppp/p1n2n2/4p3/B3P3/5N2/PPPP1PPP/RNBQ1RK1 b kq - 3 5', 'ongoing'],
  ['e2e4 e7e5 f1c4 b8c6 d1h5 g8f6 h5f7', 'r1bqkb1r/pppp1Qpp/2n2n2/4p3/2B1P3/8/PPPP1PPP/RNB1K1NR b KQkq - 0 4', 'checkmate'],
];
const STATUS = [
  ['R5k1/5ppp/8/8/8/8/8/4K3 b - - 0 1', 'checkmate'],
  ['k7/8/1Q6/8/8/8/8/K7 b - - 0 1', 'stalemate'],
  ['4k3/8/8/8/8/8/8/4RK2 b - - 0 1', 'check'],
  [POSITIONS.kiwipete, 'ongoing'],
];
const ILLEGAL = [
  [POSITIONS.start, 'e2e5'], [POSITIONS.start, 'e1g1'], ['k7/4P3/8/8/8/8/8/4K3 w - - 0 1', 'e7e8'],
  ['4k3/4b3/8/8/8/8/8/4R2K b - - 0 1', 'e7d6'],
];

function perft(chess, fen, depth) {
  const moves = chess.legalMoves(fen);
  if (depth === 1) return moves.length;
  let total = 0;
  for (const move of moves) total += perft(chess, chess.applyMove(fen, move), depth - 1);
  return total;
}

function run(chess, id) {
  if (PERFT[id]) {
    const [name, depth, expected] = PERFT[id];
    const seen = perft(chess, POSITIONS[name], depth);
    return [seen === expected, `${name} depth ${depth}: ${seen} move sequences, ${expected} expected`];
  }
  if (id === 'game-fens') {
    for (const [moves, fen, status] of GAMES) {
      let at = chess.startFen();
      for (const move of moves.split(' ')) at = chess.applyMove(at, move);
      if (at !== fen) return [false, `after ${moves}: ${at}, expected ${fen}`];
      if (chess.status(at) !== status) return [false, `after ${moves}: status ${chess.status(at)}, expected ${status}`];
    }
    return [true, `${GAMES.length} games end on the expected position and status`];
  }
  if (id === 'status-positions') {
    for (const [fen, status] of STATUS) {
      if (chess.status(fen) !== status) return [false, `${fen}: status ${chess.status(fen)}, expected ${status}`];
    }
    return [true, `${STATUS.length} positions report the expected status`];
  }
  if (id === 'illegal-moves-throw') {
    for (const [fen, move] of ILLEGAL) {
      let thrown = null;
      try { chess.applyMove(fen, move); } catch (error) { thrown = error; }
      if (!(thrown instanceof chess.IllegalMoveError)) {
        return [false, `${move} from ${fen}: ${thrown ? 'threw ' + thrown.constructor.name : 'returned a position'}`];
      }
    }
    return [true, `${ILLEGAL.length} illegal moves throw IllegalMoveError`];
  }
  if (id === 'moves-sorted') {
    for (const [name, fen] of Object.entries(POSITIONS)) {
      const moves = chess.legalMoves(fen);
      const sorted = [...moves].sort();
      if (moves.join(' ') !== sorted.join(' ')) return [false, `${name}: the move list is not in alphabetical order`];
      if (new Set(moves).size !== moves.length) return [false, `${name}: the move list repeats a move`];
    }
    return [true, 'every move list is sorted and has no repeat'];
  }
  return [false, `unknown check ${id}`];
}

const IDS = [...Object.keys(PERFT), 'game-fens', 'status-positions', 'illegal-moves-throw', 'moves-sorted'];
if (process.argv[2] === '--list') {
  console.log(IDS.join('\n'));
} else {
  let outcome;
  try {
    const chess = require(path.resolve(process.argv[2], 'src', 'chess.js'));
    outcome = run(chess, process.argv[3]);
  } catch (error) {
    outcome = [false, `${error && error.constructor ? error.constructor.name : 'error'}: ${String(error && error.message).slice(0, 160)}`];
  }
  console.log(outcome[1]);
  process.exit(outcome[0] ? 0 : 1);
}
