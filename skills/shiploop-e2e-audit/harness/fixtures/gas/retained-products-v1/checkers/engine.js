/**
 * English/American checkers rules.
 * Playable squares: (row+col)%2===1; row 0 is White's back rank (top).
 * applyMove never throws on illegal input; returns {ok:false,error,state}.
 */
(function (root) {
  "use strict";

  var BLACK = "black";
  var WHITE = "white";
  var state = null;
  var debug = false;

  function playable(r, c) {
    return r >= 0 && r < 8 && c >= 0 && c < 8 && (r + c) % 2 === 1;
  }

  function clonePiece(p) {
    return p ? { color: p.color, king: !!p.king } : null;
  }

  function cloneState(s) {
    return {
      board: s.board.map(function (row) {
        return row.map(clonePiece);
      }),
      turn: s.turn,
      activeSquare: s.activeSquare ? { r: s.activeSquare.r, c: s.activeSquare.c } : null,
      status: s.status,
      winner: s.winner
    };
  }

  function startingBoard() {
    var board = [];
    var r, c;
    for (r = 0; r < 8; r++) {
      board[r] = [];
      for (c = 0; c < 8; c++) {
        if (!playable(r, c)) {
          board[r][c] = null;
        } else if (r <= 2) {
          board[r][c] = { color: WHITE, king: false };
        } else if (r >= 5) {
          board[r][c] = { color: BLACK, king: false };
        } else {
          board[r][c] = null;
        }
      }
    }
    return board;
  }

  function logDebug(phase, extra) {
    if (!debug) return;
    try {
      console.log("checkers", phase, {
        turn: extra.turn,
        active: extra.activeSquare,
        status: extra.status,
        ok: extra.ok,
        error: extra.error || null
      });
    } catch (e) {}
  }

  function forward(color) {
    return color === BLACK ? -1 : 1;
  }

  function promoteRow(color) {
    return color === BLACK ? 0 : 7;
  }

  function jumpDirs(piece) {
    if (piece.king) {
      return [
        [-2, -2],
        [-2, 2],
        [2, -2],
        [2, 2]
      ];
    }
    var d = forward(piece.color) * 2;
    return [
      [d, -2],
      [d, 2]
    ];
  }

  function quietDirs(piece) {
    if (piece.king) {
      return [
        [-1, -1],
        [-1, 1],
        [1, -1],
        [1, 1]
      ];
    }
    var d = forward(piece.color);
    return [
      [d, -1],
      [d, 1]
    ];
  }

  function jumpsFrom(board, r, c) {
    var piece = board[r][c];
    if (!piece) return [];
    var out = [];
    var dirs = jumpDirs(piece);
    var i, dr, dc, midR, midC, toR, toC, mid;
    for (i = 0; i < dirs.length; i++) {
      dr = dirs[i][0];
      dc = dirs[i][1];
      toR = r + dr;
      toC = c + dc;
      midR = r + dr / 2;
      midC = c + dc / 2;
      if (!playable(toR, toC) || board[toR][toC]) continue;
      mid = board[midR][midC];
      if (mid && mid.color !== piece.color) {
        out.push({
          from: { r: r, c: c },
          to: { r: toR, c: toC },
          capture: { r: midR, c: midC }
        });
      }
    }
    return out;
  }

  function quietsFrom(board, r, c) {
    var piece = board[r][c];
    if (!piece) return [];
    var out = [];
    var dirs = quietDirs(piece);
    var i, toR, toC;
    for (i = 0; i < dirs.length; i++) {
      toR = r + dirs[i][0];
      toC = c + dirs[i][1];
      if (playable(toR, toC) && !board[toR][toC]) {
        out.push({ from: { r: r, c: c }, to: { r: toR, c: toC }, capture: null });
      }
    }
    return out;
  }

  function allJumps(board, color, only) {
    if (only) return jumpsFrom(board, only.r, only.c);
    var out = [];
    var r, c, p;
    for (r = 0; r < 8; r++) {
      for (c = 0; c < 8; c++) {
        p = board[r][c];
        if (p && p.color === color) out = out.concat(jumpsFrom(board, r, c));
      }
    }
    return out;
  }

  function allQuiets(board, color) {
    var out = [];
    var r, c, p;
    for (r = 0; r < 8; r++) {
      for (c = 0; c < 8; c++) {
        p = board[r][c];
        if (p && p.color === color) out = out.concat(quietsFrom(board, r, c));
      }
    }
    return out;
  }

  function sameSq(a, b) {
    return a && b && a.r === b.r && a.c === b.c;
  }

  function legalMoves(from) {
    if (!state || state.status !== "playing") return [];
    var jumps = allJumps(state.board, state.turn, state.activeSquare);
    if (jumps.length) {
      if (from) {
        return jumps.filter(function (m) {
          return sameSq(m.from, from);
        });
      }
      return jumps;
    }
    if (state.activeSquare) return [];
    var quiets = allQuiets(state.board, state.turn);
    if (from) {
      return quiets.filter(function (m) {
        return sameSq(m.from, from);
      });
    }
    return quiets;
  }

  function countColor(board, color) {
    var n = 0;
    var r, c, p;
    for (r = 0; r < 8; r++) {
      for (c = 0; c < 8; c++) {
        p = board[r][c];
        if (p && p.color === color) n++;
      }
    }
    return n;
  }

  function opponent(color) {
    return color === BLACK ? WHITE : BLACK;
  }

  function hasAnyMove(board, color) {
    return allJumps(board, color, null).length > 0 || allQuiets(board, color).length > 0;
  }

  function newGame() {
    state = {
      board: startingBoard(),
      turn: BLACK,
      activeSquare: null,
      status: "playing",
      winner: null
    };
    logDebug("newGame", state);
    return getState();
  }

  function getState() {
    if (!state) newGame();
    return cloneState(state);
  }

  function setState(next) {
    if (!next || !next.board) {
      return { ok: false, error: "invalid state", state: getState() };
    }
    state = cloneState(next);
    if (!state.turn) state.turn = BLACK;
    if (!state.status) state.status = "playing";
    return { ok: true, state: getState() };
  }

  function applyMove(from, to) {
    if (!state) newGame();
    var before = cloneState(state);
    if (state.status !== "playing") {
      return { ok: false, error: "game over", state: getState() };
    }
    if (!from || !to || !playable(from.r, from.c) || !playable(to.r, to.c)) {
      return { ok: false, error: "invalid square", state: getState() };
    }
    var moves = legalMoves(from);
    var match = null;
    var i;
    for (i = 0; i < moves.length; i++) {
      if (sameSq(moves[i].to, to)) {
        match = moves[i];
        break;
      }
    }
    if (!match) {
      logDebug("applyMove", { turn: state.turn, activeSquare: state.activeSquare, status: state.status, ok: false, error: "illegal move" });
      return { ok: false, error: "illegal move", state: getState() };
    }
    var board = cloneState(state).board;
    var piece = clonePiece(board[from.r][from.c]);
    board[from.r][from.c] = null;
    if (match.capture) board[match.capture.r][match.capture.c] = null;
    var promoted = false;
    if (!piece.king && to.r === promoteRow(piece.color)) {
      piece.king = true;
      promoted = true;
    }
    board[to.r][to.c] = piece;
    var next = {
      board: board,
      turn: state.turn,
      activeSquare: null,
      status: "playing",
      winner: null
    };
    if (match.capture && !promoted) {
      var more = jumpsFrom(board, to.r, to.c);
      if (more.length) {
        next.activeSquare = { r: to.r, c: to.c };
        state = next;
        logDebug("applyMove", { turn: state.turn, activeSquare: state.activeSquare, status: state.status, ok: true });
        return { ok: true, state: getState() };
      }
    }
    var opp = opponent(state.turn);
    next.turn = opp;
    if (countColor(board, opp) === 0 || !hasAnyMove(board, opp)) {
      next.status = "won";
      next.winner = state.turn;
      next.turn = state.turn;
    }
    state = next;
    logDebug("applyMove", { turn: state.turn, activeSquare: state.activeSquare, status: state.status, ok: true });
    return { ok: true, state: getState() };
  }

  var api = {
    BLACK: BLACK,
    WHITE: WHITE,
    playable: playable,
    newGame: newGame,
    getState: getState,
    setState: setState,
    legalMoves: legalMoves,
    applyMove: applyMove,
    get debug() {
      return debug;
    },
    set debug(v) {
      debug = !!v;
    }
  };

  newGame();
  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  }
  root.Checkers = api;
})(typeof globalThis !== "undefined" ? globalThis : this);
