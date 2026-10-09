"""Held-out acceptance checks for the `checkers` case (style: web-service), read from its prompt and never shown to a model.

``quality.acceptance`` imports this module and calls each function in ``CHECKS`` with the base URL of the delivered server,
which it started on a free port; a check returns ``(ok, note)``. They run inside the harness process, so neither this file's
name nor a check id is ever on a command line, and nothing is written into the delivery. Each is a black box over HTTP: the
prompt is the only specification, and ``cases.json`` quotes the sentence each check reads (``source``).

Every check starts its own game, so the checks do not depend on one another or on their order. The coordinates are the
prompt's: red on rows 0 to 2 moving toward higher rows, black on rows 5 to 7, pieces on squares whose row plus column is odd.
Kings, multi-jump continuation and the end of the game are not asserted: no delivery has yet been seen to settle them.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request

CALL_SECONDS = 5


def call(base: str, method: str, path: str, body: dict | None = None) -> tuple[int, dict]:
    """One request; the status and the JSON object answered ({} when the body is not one)."""
    data = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(base + path, data=data, method=method, headers={"content-type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=CALL_SECONDS) as response:
            status, raw = response.status, response.read()
    except urllib.error.HTTPError as error:
        with error:  # closes the response
            status, raw = error.code, error.read()
    try:
        parsed = json.loads(raw or b"{}")
    except ValueError:
        return status, {}
    return status, parsed if isinstance(parsed, dict) else {}


def new_game(base: str):
    """The id of a new game, or None when GET /api/new answers none."""
    _status, answer = call(base, "GET", "/api/new")
    for key in ("game", "id", "gameId"):
        if key in answer:
            return answer[key]
    return None


def move(base: str, game, source: list, target: list) -> dict:
    return call(base, "POST", "/api/move", {"game": game, "from": source, "to": target})[1]


def shaped(answer: dict) -> bool:
    """The prompt's response: "ok" true or false, "turn" red or black, and a "winner" key."""
    return isinstance(answer.get("ok"), bool) and answer.get("turn") in ("red", "black") and "winner" in answer


def refused_keeping_the_turn(answer: dict, turn: str) -> bool:
    return answer.get("ok") is False and answer.get("turn") == turn and shaped(answer)


def started(base: str):
    game = new_game(base)
    return game, (None if game is not None else (False, "GET /api/new returned no game id"))


def red_moves_first(base: str) -> tuple[bool, str]:
    game, bad = started(base)
    if bad:
        return bad
    answer = move(base, game, [5, 0], [4, 1])  # a black piece's ordinary forward move, before red has moved
    return refused_keeping_the_turn(answer, "red"), f"black first: {json.dumps(answer)[:120]}"


def illegal_keeps_the_turn(base: str) -> tuple[bool, str]:
    game, bad = started(base)
    if bad:
        return bad
    illegal = {"not diagonal": ([2, 1], [2, 2]), "backward": ([2, 1], [1, 0]), "onto a piece": ([1, 0], [2, 1]),
               "from an empty square": ([4, 1], [5, 2]), "from a light square": ([2, 2], [3, 3])}
    wrong = []
    for name, (source, target) in illegal.items():
        answer = move(base, game, source, target)
        if not refused_keeping_the_turn(answer, "red"):
            wrong.append(f"{name}: {json.dumps(answer)[:80]}")
    return not wrong, "; ".join(wrong) or "every board-legal illegal move refused with the turn kept"


def off_board_keeps_the_turn(base: str) -> tuple[bool, str]:
    game, bad = started(base)
    if bad:
        return bad
    wrong = []
    for name, target in {"past the last row": [8, 2], "a negative column": [3, -1]}.items():
        status, answer = call(base, "POST", "/api/move", {"game": game, "from": [2, 1], "to": target})
        if not refused_keeping_the_turn(answer, "red"):
            wrong.append(f"{name}: HTTP {status} {json.dumps(answer)[:80]}")
    return not wrong, "; ".join(wrong) or "off-board moves refused with the turn kept"


def legal_moves_alternate_the_turn(base: str) -> tuple[bool, str]:
    game, bad = started(base)
    if bad:
        return bad
    answers = [move(base, game, [2, 1], [3, 0]), move(base, game, [5, 0], [4, 1]), move(base, game, [2, 3], [3, 4])]
    turns = [(a.get("ok"), a.get("turn")) for a in answers]
    return turns == [(True, "black"), (True, "red"), (True, "black")], f"(ok, turn) after red, black, red: {turns}"


def play_to_a_red_jump(base: str):
    """Red [2,1]->[3,2], black [5,4]->[4,3]: red's piece on [3,2] can now jump to [5,4]. Returns the game, or a failure."""
    game, bad = started(base)
    if bad:
        return None, bad
    first, second = move(base, game, [2, 1], [3, 2]), move(base, game, [5, 4], [4, 3])
    if first.get("ok") is not True or second.get("ok") is not True:
        return None, (False, f"setup moves refused: {json.dumps(first)[:60]} {json.dumps(second)[:60]}")
    return game, None


def a_jump_is_mandatory_for_red(base: str) -> tuple[bool, str]:
    game, bad = play_to_a_red_jump(base)
    if bad:
        return bad
    skipped = move(base, game, [2, 3], [3, 4])  # an ordinary move while a jump is available
    jumped = move(base, game, [3, 2], [5, 4])
    ok = refused_keeping_the_turn(skipped, "red") and jumped.get("ok") is True and jumped.get("turn") == "black"
    return ok, f"ordinary move with a jump available: {json.dumps(skipped)[:80]}; the jump: {json.dumps(jumped)[:80]}"


def a_jump_is_mandatory_for_black_and_removes_the_piece(base: str) -> tuple[bool, str]:
    game, bad = play_to_a_red_jump(base)
    if bad:
        return bad
    jumped = move(base, game, [3, 2], [5, 4])  # removes the black piece on [4,3]; red's piece now stands on [5,4]
    if jumped.get("ok") is not True:
        return False, f"the red jump was refused: {json.dumps(jumped)[:100]}"
    skipped = move(base, game, [5, 2], [4, 1])  # an ordinary black move while black can jump
    recaptured = move(base, game, [6, 5], [4, 3])  # onto the square of the removed piece
    ok = refused_keeping_the_turn(skipped, "black") and recaptured.get("ok") is True and recaptured.get("turn") == "red"
    return ok, f"black ordinary move: {json.dumps(skipped)[:80]}; black recapture onto the removed piece's square: {json.dumps(recaptured)[:80]}"


CHECKS = {
    "red-moves-first": red_moves_first,
    "illegal-keeps-turn": illegal_keeps_the_turn,
    "off-board-keeps-turn": off_board_keeps_the_turn,
    "legal-moves-alternate": legal_moves_alternate_the_turn,
    "red-jump-mandatory": a_jump_is_mandatory_for_red,
    "black-jump-mandatory-and-removal": a_jump_is_mandatory_for_black_and_removes_the_piece,
}
