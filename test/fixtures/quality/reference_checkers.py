#!/usr/bin/env python3
"""A hermetic reference Checkers service for calibrating the held-out checks (test/shiploop_e2e/checks/checkers_accept.py).

It implements the contract of the `checkers` case prompt and nothing else: GET / (a page titled "Checkers"), GET /api/new, and
POST /api/move answering {"ok", "turn", "winner"}. Men move one square diagonally forward, a jump goes over an opposing piece
to the empty square behind it, a jump is mandatory when one is available, a jumped piece is removed, a piece reaching the far
row is crowned, and an illegal move keeps the turn. There is no multi-jump continuation: the checks do not ask for one.

``--defect <name>`` breaks exactly one rule, so a check can be shown to pass the correct service and to fail the defect it
reads: black-first, illegal-flips-turn, offboard-400 (the shape a real delivery answered: HTTP 400 and {ok, error} with no turn
or winner), no-alternation, optional-jump, black-optional-jump, no-removal. The port is the PORT environment variable; the
process ends by itself after two minutes, so a test that dies leaves nothing behind.
"""

from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
import sys
import threading
import time

DEFECTS = ("black-first", "illegal-flips-turn", "offboard-400", "no-alternation", "optional-jump", "black-optional-jump",
           "no-removal")
LIFETIME_SECONDS = 120


class Game:
    def __init__(self, defect: str | None):
        self.defect = defect
        self.board = {}
        for row in range(8):
            for col in range(8):
                if (row + col) % 2 == 1 and row <= 2:
                    self.board[(row, col)] = ["red", False]
                elif (row + col) % 2 == 1 and row >= 5:
                    self.board[(row, col)] = ["black", False]
        self.turn = "black" if defect == "black-first" else "red"
        self.winner = None

    def steps(self, color: str, king: bool):
        forward = 1 if color == "red" else -1
        return [(forward, -1), (forward, 1)] + ([(-forward, -1), (-forward, 1)] if king else [])

    def jumps_from(self, square):
        color, king = self.board[square]
        found = []
        for dr, dc in self.steps(color, king):
            middle, landing = (square[0] + dr, square[1] + dc), (square[0] + 2 * dr, square[1] + 2 * dc)
            if (0 <= landing[0] < 8 and 0 <= landing[1] < 8 and middle in self.board and self.board[middle][0] != color
                    and landing not in self.board):
                found.append((landing, middle))
        return found

    def jump_available(self, color: str) -> bool:
        return any(self.jumps_from(square) for square, piece in list(self.board.items()) if piece[0] == color)

    def answer(self, ok: bool) -> dict:
        return {"ok": ok, "turn": self.turn, "winner": self.winner}

    def refuse(self) -> dict:
        if self.defect == "illegal-flips-turn":
            self.turn = "black" if self.turn == "red" else "red"
        return self.answer(False)

    def play(self, source, target) -> tuple[int, dict]:
        valid = all(isinstance(p, list) and len(p) == 2 and all(isinstance(n, int) for n in p) for p in (source, target))
        if not valid or not all(0 <= n < 8 for p in (source, target) for n in p):
            if self.defect == "offboard-400":
                return 400, {"ok": False, "error": "invalid coordinates"}
            return 200, self.answer(False)
        source, target = tuple(source), tuple(target)
        piece = self.board.get(source)
        if piece is None or piece[0] != self.turn or target in self.board or (target[0] + target[1]) % 2 != 1:
            return 200, self.refuse()
        color, king = piece
        delta = (target[0] - source[0], target[1] - source[1])
        jump = next(((landing, middle) for landing, middle in self.jumps_from(source) if landing == target), None)
        simple = delta in self.steps(color, king)
        required = self.jump_available(color) and not (self.defect == "optional-jump" or
                                                       (self.defect == "black-optional-jump" and color == "black"))
        if not (jump or simple) or (required and not jump):
            return 200, self.refuse()
        del self.board[source]
        self.board[target] = [color, king or target[0] == (7 if color == "red" else 0)]
        if jump and self.defect != "no-removal":
            del self.board[jump[1]]
        if not any(p[0] != color for p in self.board.values()):
            self.winner = color
        if self.defect != "no-alternation":
            self.turn = "black" if self.turn == "red" else "red"
        return 200, self.answer(True)


GAMES: dict[str, Game] = {}
DEFECT = None


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def reply(self, status: int, body, kind: str = "application/json"):
        raw = (json.dumps(body) if kind == "application/json" else body).encode()
        self.send_response(status)
        self.send_header("content-type", kind)
        self.send_header("content-length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        if self.path == "/":
            self.reply(200, "<!doctype html><title>Checkers</title><h1>Checkers</h1>", "text/html")
        elif self.path == "/api/new":
            ident = str(len(GAMES) + 1)
            GAMES[ident] = Game(DEFECT)
            self.reply(200, {"game": ident})
        else:
            self.reply(404, {"ok": False})

    def do_POST(self):
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("content-length") or 0)) or b"{}")
        except ValueError:
            return self.reply(400, {"ok": False})
        game = GAMES.get(str(body.get("game"))) if isinstance(body, dict) else None
        if self.path != "/api/move" or game is None:
            return self.reply(404, {"ok": False})
        status, answer = game.play(body.get("from"), body.get("to"))
        self.reply(status, answer)


def main(argv: list[str]) -> None:
    global DEFECT
    if "--defect" in argv:
        DEFECT = argv[argv.index("--defect") + 1]
        if DEFECT not in DEFECTS:
            raise SystemExit(f"unknown defect {DEFECT!r}; known: {', '.join(DEFECTS)}")
    server = ThreadingHTTPServer(("127.0.0.1", int(os.environ.get("PORT") or 0)), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    time.sleep(LIFETIME_SECONDS)


if __name__ == "__main__":
    main(sys.argv[1:])
