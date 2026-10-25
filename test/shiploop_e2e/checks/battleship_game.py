#!/usr/bin/env python3
"""The game check of the `battleship` case (style: web-service): a 10x10 sweep must play a game, not only answer in shape.

Run through `checks/serve.py`, which starts the candidate and sets BASE: `python3 serve.py -- python3 battleship_game.py`.
It reads only sentences of the case prompt:

- "GET /api/new starts a game and returns JSON with a game id";
- "POST /api/fire ... returns JSON with "result" set to "miss", "hit" or "sunk" and "gameOver" true once every ship is sunk";
- "the player fires at a computer-placed fleet": a fleet is more than one ship, so a game ends only after two sinks or more.

So, firing row by row at every cell of a new game: every result is miss, hit or sunk; gameOver is not true before the shot
that ends the game; that shot sinks a ship, and at least two ships have sunk by then; and a shot after the end does not
report the game as running again. Fleet layout, ship sizes and the page are left to the product's own tests (SPEC S-9).

Why (2026-10-24, docs/experiments/e2e-runner-review-20261024 E2): the case's checks passed the 2026-10-16 audit's server with
no fleet whose every shot is a miss with gameOver true, and the three stubs of the 2026-10-04 review. Exits 0 on a pass, else
non-zero after one `FAIL:` line. Nothing is written.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

SIZE = 10
RESULTS = ("miss", "hit", "sunk")
FLEET = 2  # "a computer-placed fleet": more than one ship
TIMEOUT = 10


def fail(code: int, reason: str) -> None:
    print("FAIL: " + reason)
    sys.exit(code)


def call(base: str, path: str, body: dict | None = None) -> dict:
    data = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(base + path, data=data, method="GET" if body is None else "POST",
                                     headers={"content-type": "application/json"})
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        return json.loads(response.read().decode() or "null")


def game_id(started) -> object:
    if isinstance(started, dict):
        for key in ("game", "id", "gameId"):
            if started.get(key) is not None:
                return started[key]
    fail(2, f"GET /api/new returned no game id: {json.dumps(started)[:200]}")


def main() -> int:
    base = os.environ.get("BASE")
    if not base:
        fail(9, "BASE is not set: run this through checks/serve.py")
    try:
        game = game_id(call(base, "/api/new"))
        sunk = 0
        for shot in range(SIZE * SIZE):
            row, col = divmod(shot, SIZE)
            reply = call(base, "/api/fire", {"game": game, "row": row, "col": col})
            result = reply.get("result") if isinstance(reply, dict) else None
            if result not in RESULTS:
                fail(3, f"shot {shot + 1} at ({row},{col}) returned result {result!r}, not one of {', '.join(RESULTS)}")
            sunk += result == "sunk"
            if reply.get("gameOver") is not True:
                continue
            if result != "sunk":
                fail(5, f"gameOver became true on shot {shot + 1} at ({row},{col}), a {result}: the game ends when the last ship sinks")
            if sunk < FLEET:
                fail(5, f"gameOver became true after {sunk} sunk ship(s) on shot {shot + 1}: a fleet has more than one ship")
            break
        else:
            fail(4, f"gameOver never became true after firing at all {SIZE * SIZE} cells ({sunk} sunk)")
    except urllib.error.URLError as exc:
        fail(6, f"a request failed: {exc}")
    except (ValueError, OSError) as exc:
        fail(6, f"a reply could not be read: {exc}")
    try:
        after = call(base, "/api/fire", {"game": game, "row": 0, "col": 0})
    except (urllib.error.URLError, ValueError, OSError):
        return 0  # refusing a shot after the end is allowed: the prompt says nothing about it
    if isinstance(after, dict) and after.get("gameOver") is False:
        fail(7, "a shot after the game ended reported gameOver false")
    return 0


if __name__ == "__main__":
    sys.exit(main())
