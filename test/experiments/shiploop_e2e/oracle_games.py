"""Independent semantic game oracles for the Checkers and Battleship cases.

The public surface is deliberately small:

``cases(step_id)`` returns the cumulative, JSON-serializable case records for
one scenario step.  ``evaluate(case, observations)`` compares one complete
driver trace with game rules and returns ordinary behavioral issues.  It raises
``ValueError`` when the trace is not a complete semantic observation.  The
suite wrapper distinguishes that evidence gap (``unverified``) from a product
behavioral failure.

This module has no browser, source-inspection, model, deployment, or prompt
logic.  A separate, read-only UI driver maps a returned application to this
semantic protocol.  It receives ``case["actions"]`` unchanged and reports one
complete snapshot after every action.

Action schema
-------------

Checkers actions are ``reset``, ``set_fixture``, ``select``, ``move``, and
``set_hints``.  Squares are ``[row, column]`` on a standard 8 by 8 board.
``set_fixture`` is an explicit controlled-state request, used only where a
normal game would take too many moves to reach a public rule boundary.  A
driver that cannot apply it must report ``fixture_applied: false``; that is
unverified evidence, never a failed game.  ``set_hints`` means use the visible
toggle until its requested visibility is reached; it is not permission to
patch product state.

Every Checkers observation contains ``board``, ``active_player``, ``phase``,
``winner``, ``selected``, ``legal_destinations``, ``capture_chain_piece``, and
``variant``.  ``legal_destinations`` means squares carrying the visible
destination treatment, not merely moves recoverable from source.  ``variant``
is a driver-declared policy object with these exact fields:

* ``capture_priority``: ``"any"`` or ``"maximum"``;
* ``men_capture_direction``: ``"forward"`` or ``"both"``;
* ``promotion_capture_continuation``: ``"end-turn"`` or ``"continue"``.

The scenarios do not choose among those legitimate Checkers variants.  Their
fixtures have a single relevant capture, so the assertions only require the
requested mandatory-capture and same-piece continuation behavior.  The oracle
still freezes the declared variant within every trace to prevent a silent
rule-set change from being mistaken for a feature result.

Battleship actions are ``reset``, ``set_fixture``, ``place_ship``, ``shot``,
and ``set_history_filter``.  Every Battleship case declares its small
``config`` (board size and fleet IDs/lengths); this does not prescribe a
candidate's normal UI layout or default fleet.  The explicit fixture lets a
driver map an equivalent controlled state when it can do so.  A Battleship
observation contains ``config``, ``phase``, ``active_player``, ``winner``, and
``visible``.  ``visible`` names a current ``viewer`` and has an ``own_board``
and ``opponent_board``.  The opponent grid uses ``unknown``, ``hit``, or
``miss``; ``ship`` is accepted only long enough to report the privacy failure.
History-capable cases additionally require a visible ``status_panel``, a full
``history``, ``history_filter``, and ``visible_history``.  Entries record an
actor, coordinate, and hit/miss result.

The protocol is intentionally semantic rather than DOM-shaped.  It does not
specify selectors, scripts, frameworks, filenames, or a test hook in the
product.  A missing or malformed semantic field is insufficient evidence and
raises ``ValueError``.  An explicit observed absence such as
``hints_visible: null`` or ``history_filter: null`` is valid data and becomes
an ordinary issue for the feature case.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any


CHECKERS_STEPS = ("checkers-create", "checkers-guidance", "checkers-hint-toggle")
BATTLESHIP_STEPS = (
    "battleship-create",
    "battleship-status-history",
    "battleship-history-filter",
)
PLAYERS = ("P1", "P2")
CHECKERS_PLAYERS = ("black", "white")


def _square(value: Any, *, name: str = "square") -> tuple[int, int]:
    if (
        not isinstance(value, list)
        or len(value) != 2
        or any(type(item) is not int for item in value)
    ):
        raise ValueError(f"{name} must be a [row, column] integer pair")
    return value[0], value[1]


def _json_square(value: tuple[int, int] | None) -> list[int] | None:
    return None if value is None else [value[0], value[1]]


def _inside(square: tuple[int, int], size: int) -> bool:
    return 0 <= square[0] < size and 0 <= square[1] < size


def _dark(square: tuple[int, int]) -> bool:
    return (square[0] + square[1]) % 2 == 1


def _other_checkers(player: str) -> str:
    return "white" if player == "black" else "black"


def _other_player(player: str) -> str:
    return "P2" if player == "P1" else "P1"


def _empty_checkers_board() -> list[list[dict[str, Any] | None]]:
    return [[None for _column in range(8)] for _row in range(8)]


def _checkers_fixture(
    pieces: list[tuple[int, int, str, bool]], *, active: str = "black",
    phase: str = "playing", winner: str | None = None,
    locked: tuple[int, int] | None = None,
) -> dict[str, Any]:
    board = _empty_checkers_board()
    for row, column, player, king in pieces:
        if not _inside((row, column), 8) or not _dark((row, column)):
            raise AssertionError("internal Checkers fixture uses an invalid square")
        board[row][column] = {"player": player, "king": king}
    return {
        "board": board,
        "active_player": active,
        "phase": phase,
        "winner": winner,
        "capture_chain_piece": _json_square(locked),
    }


def _checkers_action_fixture(fixture: dict[str, Any]) -> dict[str, Any]:
    return {"type": "set_fixture", "fixture": fixture}


def _checkers_move(
    source: tuple[int, int], destination: tuple[int, int], **extra: Any
) -> dict[str, Any]:
    return {"type": "move", "from": list(source), "to": list(destination), **extra}


def _checkers_select(square: tuple[int, int], **extra: Any) -> dict[str, Any]:
    return {"type": "select", "square": list(square), **extra}


def _checkers_cases() -> list[dict[str, Any]]:
    quiet = _checkers_fixture([(5, 0, "black", False), (2, 3, "white", False)])
    forced = _checkers_fixture(
        [(5, 0, "black", False), (5, 4, "black", False), (4, 1, "white", False)]
    )
    chain = _checkers_fixture(
        [
            (5, 0, "black", False),
            (5, 4, "black", False),
            (4, 1, "white", False),
            (2, 3, "white", False),
            (0, 1, "white", False),
        ]
    )
    promotion = _checkers_fixture(
        [(1, 4, "black", False), (0, 1, "white", False), (7, 0, "white", False)]
    )
    win = _checkers_fixture(
        [
            (0, 1, "white", False),
            (1, 0, "black", False),
            (1, 2, "black", False),
            (2, 3, "black", False),
            (4, 1, "black", False),
        ]
    )

    base = [
        {
            "id": "checkers-base-legal-diagonal-moves",
            "game": "checkers",
            "step_id": "checkers-create",
            "level": "base",
            "actions": [
                _checkers_action_fixture(quiet),
                _checkers_move((5, 0), (4, 1)),
                _checkers_move((2, 3), (3, 2)),
            ],
        },
        {
            "id": "checkers-base-required-capture",
            "game": "checkers",
            "step_id": "checkers-create",
            "level": "base",
            "actions": [
                _checkers_action_fixture(forced),
                _checkers_move((5, 4), (4, 3)),
                _checkers_move((5, 0), (3, 2)),
            ],
        },
        {
            "id": "checkers-base-capture-chain-lock",
            "game": "checkers",
            "step_id": "checkers-create",
            "level": "base",
            "actions": [
                _checkers_action_fixture(chain),
                _checkers_move(
                    (5, 0), (3, 2), expect_selected=[3, 2], expect_destinations=True
                ),
                _checkers_move((5, 4), (4, 3)),
                _checkers_move((3, 2), (1, 4)),
            ],
        },
        {
            "id": "checkers-base-promotion",
            "game": "checkers",
            "step_id": "checkers-create",
            "level": "base",
            "actions": [
                _checkers_action_fixture(promotion),
                _checkers_move((1, 4), (0, 3)),
            ],
        },
        {
            "id": "checkers-base-win",
            "game": "checkers",
            "step_id": "checkers-create",
            "level": "base",
            "actions": [
                _checkers_action_fixture(win),
                _checkers_move((4, 1), (3, 0)),
            ],
        },
        {
            "id": "checkers-base-reset",
            "game": "checkers",
            "step_id": "checkers-create",
            "level": "base",
            "actions": [
                {"type": "reset", "remember_reset": "initial"},
                _checkers_action_fixture(chain),
                _checkers_move((5, 0), (3, 2)),
                {"type": "reset", "compare_reset": "initial"},
            ],
        },
    ]
    guidance = [
        {
            "id": "checkers-guidance-selected-destinations",
            "game": "checkers",
            "step_id": "checkers-guidance",
            "level": "guidance",
            "actions": [
                _checkers_action_fixture(quiet),
                _checkers_select(
                    (5, 0), expect_selected=[5, 0], expect_destinations=True
                ),
            ],
        },
        {
            "id": "checkers-guidance-required-capture-destinations",
            "game": "checkers",
            "step_id": "checkers-guidance",
            "level": "guidance",
            "actions": [
                _checkers_action_fixture(forced),
                _checkers_select(
                    (5, 4), expect_selected="none-or-source", expect_destinations=True
                ),
                _checkers_select(
                    (5, 0), expect_selected=[5, 0], expect_destinations=True
                ),
            ],
        },
    ]
    refine = [
        {
            "id": "checkers-refine-hint-toggle-and-chain",
            "game": "checkers",
            "step_id": "checkers-hint-toggle",
            "level": "refine",
            "requires_hints": True,
            "actions": [
                _checkers_action_fixture(chain),
                _checkers_select(
                    (5, 0), expect_selected=[5, 0], expect_destinations=True
                ),
                {"type": "set_hints", "visible": False, "expect_destinations": True},
                {"type": "set_hints", "visible": True, "expect_destinations": True},
                _checkers_move(
                    (5, 0), (3, 2), expect_selected=[3, 2], expect_destinations=True
                ),
                _checkers_move((3, 2), (1, 4)),
            ],
        }
    ]
    return base + guidance + refine


def _battle_config() -> dict[str, Any]:
    return {
        "board_size": 4,
        "fleet": [
            {"id": "patrol", "length": 2},
            {"id": "scout", "length": 1},
        ],
    }


def _battle_fixture(
    *, phase: str, active: str, placements: dict[str, dict[str, list[list[int]]]],
    shots: dict[str, list[list[int]]] | None = None,
    history: list[dict[str, Any]] | None = None,
    winner: str | None = None,
) -> dict[str, Any]:
    return {
        "config": _battle_config(),
        "phase": phase,
        "active_player": active,
        "winner": winner,
        "placements": placements,
        "shots": shots or {"P1": [], "P2": []},
        "history": history or [],
        "history_filter": "all",
    }


def _battle_action_fixture(fixture: dict[str, Any]) -> dict[str, Any]:
    return {"type": "set_fixture", "fixture": fixture}


def _place(player: str, ship: str, start: tuple[int, int], direction: str) -> dict[str, Any]:
    return {
        "type": "place_ship",
        "player": player,
        "ship": ship,
        "start": list(start),
        "direction": direction,
    }


def _shot(player: str, coordinate: tuple[int, int]) -> dict[str, Any]:
    return {"type": "shot", "player": player, "coordinate": list(coordinate)}


def _battleship_cases() -> list[dict[str, Any]]:
    placement = _battle_fixture(
        phase="placement", active="P1", placements={"P1": {}, "P2": {}}
    )
    play_placements = {
        "P1": {"patrol": [[0, 0], [0, 1]], "scout": [[2, 2]]},
        "P2": {"patrol": [[1, 0], [1, 1]], "scout": [[3, 3]]},
    }
    play = _battle_fixture(phase="playing", active="P1", placements=play_placements)
    filter_placements = {
        "P1": {"patrol": [[0, 0], [0, 1]], "scout": [[2, 2]]},
        "P2": {"patrol": [[1, 0], [1, 1]], "scout": [[3, 3]]},
    }
    filter_play = _battle_fixture(
        phase="playing", active="P1", placements=filter_placements
    )
    base = [
        {
            "id": "battleship-base-placement-rules",
            "game": "battleship",
            "step_id": "battleship-create",
            "level": "base",
            "config": _battle_config(),
            "actions": [
                _battle_action_fixture(placement),
                _place("P1", "patrol", (0, 3), "horizontal"),
                _place("P1", "patrol", (0, 0), "horizontal"),
                _place("P1", "scout", (0, 0), "horizontal"),
                _place("P1", "scout", (2, 2), "horizontal"),
                _place("P2", "patrol", (0, 0), "vertical"),
                _place("P2", "scout", (3, 3), "horizontal"),
            ],
        },
        {
            "id": "battleship-base-shots-sunk-winner-and-privacy",
            "game": "battleship",
            "step_id": "battleship-create",
            "level": "base",
            "config": _battle_config(),
            "actions": [
                _battle_action_fixture(play),
                _shot("P1", (1, 0)),
                _shot("P2", (3, 3)),
                _shot("P1", (1, 0)),
                _shot("P1", (1, 1)),
                _shot("P2", (0, 0)),
                _shot("P1", (3, 3)),
            ],
        },
        {
            "id": "battleship-base-reset",
            "game": "battleship",
            "step_id": "battleship-create",
            "level": "base",
            "config": _battle_config(),
            "actions": [
                {"type": "reset", "remember_reset": "initial"},
                _battle_action_fixture(play),
                _shot("P1", (1, 0)),
                {"type": "reset", "compare_reset": "initial"},
            ],
        },
    ]
    status = [
        {
            "id": "battleship-status-history-visible-and-private",
            "game": "battleship",
            "step_id": "battleship-status-history",
            "level": "guidance",
            "config": _battle_config(),
            "requires_history": True,
            "actions": [
                _battle_action_fixture(play),
                _shot("P1", (1, 0)),
                _shot("P2", (3, 3)),
                _shot("P1", (1, 0)),
                _shot("P1", (1, 1)),
            ],
        }
    ]
    refine = [
        {
            "id": "battleship-refine-history-filters-preserve-game",
            "game": "battleship",
            "step_id": "battleship-history-filter",
            "level": "refine",
            "config": _battle_config(),
            "requires_history": True,
            "requires_filters": True,
            "actions": [
                _battle_action_fixture(filter_play),
                _shot("P1", (1, 0)),
                _shot("P2", (3, 3)),
                _shot("P1", (0, 2)),
                {"type": "set_history_filter", "filter": "hit"},
                {"type": "set_history_filter", "filter": "miss"},
                {"type": "set_history_filter", "filter": "all"},
            ],
        }
    ]
    return base + status + refine


_ALL_CASES = _checkers_cases() + _battleship_cases()
_CASE_BY_ID = {case["id"]: case for case in _ALL_CASES}


def cases(step_id: str) -> list[dict[str, Any]]:
    """Return cumulative independent cases for one scheduled game step.

    The returned data is a deep copy because the wrapper may attach transport
    metadata without mutating this oracle's catalog.  A feature/refinement
    includes all prerequisites, while its own behavior is identified by a case
    whose ``step_id`` equals the requested step.
    """
    if not isinstance(step_id, str):
        raise ValueError("step_id must be a string")
    if step_id in CHECKERS_STEPS:
        limit = CHECKERS_STEPS.index(step_id)
        selected = [
            case
            for case in _ALL_CASES
            if case["game"] == "checkers"
            and CHECKERS_STEPS.index(case["step_id"]) <= limit
        ]
    elif step_id in BATTLESHIP_STEPS:
        limit = BATTLESHIP_STEPS.index(step_id)
        selected = [
            case
            for case in _ALL_CASES
            if case["game"] == "battleship"
            and BATTLESHIP_STEPS.index(case["step_id"]) <= limit
        ]
    else:
        raise ValueError(f"unsupported game scenario step: {step_id!r}")
    return deepcopy(selected)


def _canonical_piece(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    if (
        not isinstance(value, dict)
        or set(value) - {"player", "king"}
        or value.get("player") not in CHECKERS_PLAYERS
        or type(value.get("king")) is not bool
    ):
        raise ValueError("Checkers board piece is malformed")
    return {"player": value["player"], "king": value["king"]}


def _canonical_checkers_board(value: Any) -> list[list[dict[str, Any] | None]]:
    if not isinstance(value, list) or len(value) != 8:
        raise ValueError("Checkers observation requires an 8 by 8 board")
    board: list[list[dict[str, Any] | None]] = []
    for row_index, row in enumerate(value):
        if not isinstance(row, list) or len(row) != 8:
            raise ValueError("Checkers observation requires an 8 by 8 board")
        normalized = [_canonical_piece(piece) for piece in row]
        for column_index, piece in enumerate(normalized):
            if piece is not None and not _dark((row_index, column_index)):
                raise ValueError("Checkers piece appears on a non-playable square")
        board.append(normalized)
    return board


def _canonical_optional_square(value: Any, *, name: str) -> tuple[int, int] | None:
    if value is None:
        return None
    square = _square(value, name=name)
    if not _inside(square, 8) or not _dark(square):
        raise ValueError(f"{name} must name a playable Checkers square")
    return square


def _canonical_destinations(value: Any) -> list[tuple[int, int]]:
    if not isinstance(value, list):
        raise ValueError("Checkers observation requires legal_destinations")
    destinations = [_canonical_optional_square(square, name="legal destination") for square in value]
    if any(square is None for square in destinations) or len(set(destinations)) != len(destinations):
        raise ValueError("Checkers legal destinations must be unique playable squares")
    return sorted(destinations)


def _canonical_variant(value: Any) -> dict[str, str]:
    if not isinstance(value, dict) or set(value) != {
        "capture_priority",
        "men_capture_direction",
        "promotion_capture_continuation",
    }:
        raise ValueError("Checkers observation requires an explicit complete variant")
    if value["capture_priority"] not in ("any", "maximum"):
        raise ValueError("unsupported Checkers capture priority")
    if value["men_capture_direction"] not in ("forward", "both"):
        raise ValueError("unsupported Checkers man capture direction")
    if value["promotion_capture_continuation"] not in ("end-turn", "continue"):
        raise ValueError("unsupported Checkers promotion capture continuation")
    return {
        "capture_priority": value["capture_priority"],
        "men_capture_direction": value["men_capture_direction"],
        "promotion_capture_continuation": value["promotion_capture_continuation"],
    }


def _canonical_checkers_observation(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("Checkers observation must be an object")
    required = {
        "board", "active_player", "phase", "winner", "selected",
        "legal_destinations", "capture_chain_piece", "variant", "hints_visible",
    }
    missing = required - set(value)
    if missing:
        raise ValueError(f"Checkers observation missing {sorted(missing)!r}")
    phase = value["phase"]
    if phase not in ("playing", "won", "draw"):
        raise ValueError("unsupported Checkers phase")
    active = value["active_player"]
    if active not in (*CHECKERS_PLAYERS, None):
        raise ValueError("invalid Checkers active player")
    winner = value["winner"]
    if winner not in (*CHECKERS_PLAYERS, None):
        raise ValueError("invalid Checkers winner")
    if value["hints_visible"] not in (True, False, None):
        raise ValueError("Checkers hints_visible must be boolean or null")
    fixture_applied = value.get("fixture_applied")
    if fixture_applied not in (True, False, None):
        raise ValueError("Checkers fixture_applied must be boolean when supplied")
    action_supported = value.get("action_supported")
    if action_supported not in (True, False, None):
        raise ValueError("Checkers action_supported must be boolean when supplied")
    return {
        "board": _canonical_checkers_board(value["board"]),
        "active_player": active,
        "phase": phase,
        "winner": winner,
        "selected": _canonical_optional_square(value["selected"], name="selected"),
        "legal_destinations": _canonical_destinations(value["legal_destinations"]),
        "capture_chain_piece": _canonical_optional_square(
            value["capture_chain_piece"], name="capture_chain_piece"
        ),
        "variant": _canonical_variant(value["variant"]),
        "hints_visible": value["hints_visible"],
        "fixture_applied": fixture_applied,
        "action_supported": action_supported,
    }


def _checkers_state_from_fixture(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("Checkers fixture must be an object")
    required = {"board", "active_player", "phase", "winner", "capture_chain_piece"}
    if required - set(value):
        raise ValueError("Checkers fixture is incomplete")
    state = _canonical_checkers_observation(
        {
            **value,
            "selected": None,
            "legal_destinations": [],
            "variant": {
                "capture_priority": "any",
                "men_capture_direction": "forward",
                "promotion_capture_continuation": "end-turn",
            },
            "hints_visible": None,
        }
    )
    return {
        key: deepcopy(state[key])
        for key in ("board", "active_player", "phase", "winner", "capture_chain_piece")
    }


def _checkers_move_directions(piece: dict[str, Any], *, capture: bool, variant: dict[str, str]) -> list[tuple[int, int]]:
    distance = 2 if capture else 1
    if piece["king"]:
        return [
            (-distance, -distance), (-distance, distance),
            (distance, -distance), (distance, distance),
        ]
    forward = -distance if piece["player"] == "black" else distance
    if capture and variant["men_capture_direction"] == "both":
        return [(forward, -distance), (forward, distance), (-forward, -distance), (-forward, distance)]
    return [(forward, -distance), (forward, distance)]


def _checkers_jumps_from(
    board: list[list[dict[str, Any] | None]], square: tuple[int, int], variant: dict[str, str]
) -> list[tuple[tuple[int, int], tuple[int, int]]]:
    piece = board[square[0]][square[1]]
    if piece is None:
        return []
    candidates = []
    for row_delta, column_delta in _checkers_move_directions(piece, capture=True, variant=variant):
        destination = (square[0] + row_delta, square[1] + column_delta)
        jumped = (square[0] + row_delta // 2, square[1] + column_delta // 2)
        if not _inside(destination, 8) or not _dark(destination) or board[destination[0]][destination[1]] is not None:
            continue
        jumped_piece = board[jumped[0]][jumped[1]]
        if jumped_piece is not None and jumped_piece["player"] != piece["player"]:
            candidates.append((destination, jumped))
    return candidates


def _checkers_quiets_from(
    board: list[list[dict[str, Any] | None]], square: tuple[int, int], variant: dict[str, str]
) -> list[tuple[int, int]]:
    piece = board[square[0]][square[1]]
    if piece is None:
        return []
    candidates = []
    for row_delta, column_delta in _checkers_move_directions(piece, capture=False, variant=variant):
        destination = (square[0] + row_delta, square[1] + column_delta)
        if _inside(destination, 8) and _dark(destination) and board[destination[0]][destination[1]] is None:
            candidates.append(destination)
    return candidates


def _checkers_all_jumps(
    state: dict[str, Any], variant: dict[str, str]
) -> list[tuple[tuple[int, int], tuple[int, int], tuple[int, int]]]:
    board = state["board"]
    only = state["capture_chain_piece"]
    squares = [only] if only is not None else [
        (row, column)
        for row in range(8) for column in range(8)
        if board[row][column] is not None and board[row][column]["player"] == state["active_player"]
    ]
    all_jumps = []
    for source in squares:
        if source is None:
            continue
        for destination, jumped in _checkers_jumps_from(board, source, variant):
            all_jumps.append((source, destination, jumped))
    return all_jumps


def _checkers_legal_from(
    state: dict[str, Any], source: tuple[int, int], variant: dict[str, str]
) -> list[tuple[int, int]]:
    if state["phase"] != "playing":
        return []
    if not _inside(source, 8) or state["board"][source[0]][source[1]] is None:
        return []
    piece = state["board"][source[0]][source[1]]
    if piece["player"] != state["active_player"]:
        return []
    jumps = _checkers_all_jumps(state, variant)
    if jumps:
        return sorted(destination for start, destination, _jumped in jumps if start == source)
    if state["capture_chain_piece"] is not None:
        return []
    return sorted(_checkers_quiets_from(state["board"], source, variant))


def _checkers_has_legal_move(state: dict[str, Any], player: str, variant: dict[str, str]) -> bool:
    candidate = deepcopy(state)
    candidate["active_player"] = player
    candidate["capture_chain_piece"] = None
    if _checkers_all_jumps(candidate, variant):
        return True
    return any(
        _checkers_quiets_from(candidate["board"], (row, column), variant)
        for row in range(8) for column in range(8)
        if candidate["board"][row][column] is not None
        and candidate["board"][row][column]["player"] == player
    )


def _apply_checkers_move(
    state: dict[str, Any], action: dict[str, Any], variant: dict[str, str]
) -> dict[str, Any]:
    source = _square(action.get("from"), name="Checkers move source")
    destination = _square(action.get("to"), name="Checkers move destination")
    result = deepcopy(state)
    legal = _checkers_legal_from(state, source, variant)
    if destination not in legal:
        return result
    board = result["board"]
    piece = deepcopy(board[source[0]][source[1]])
    assert piece is not None
    capture = abs(destination[0] - source[0]) == 2
    board[source[0]][source[1]] = None
    if capture:
        jumped = ((source[0] + destination[0]) // 2, (source[1] + destination[1]) // 2)
        board[jumped[0]][jumped[1]] = None
    promoted = not piece["king"] and destination[0] in (0, 7)
    if promoted:
        piece["king"] = True
    board[destination[0]][destination[1]] = piece
    result["capture_chain_piece"] = None
    if capture and (not promoted or variant["promotion_capture_continuation"] == "continue"):
        if _checkers_jumps_from(board, destination, variant):
            result["capture_chain_piece"] = destination
            return result
    opponent = _other_checkers(state["active_player"])
    result["active_player"] = opponent
    if not _checkers_has_legal_move(result, opponent, variant):
        result["phase"] = "won"
        result["winner"] = state["active_player"]
        result["active_player"] = state["active_player"]
    return result


def _checkers_state_issue(
    index: int, field: str, reason: str, expected: Any, actual: Any
) -> dict[str, Any]:
    return {"index": index, "field": field, "reason": reason, "expected": expected, "actual": actual}


def _compare_checkers_state(index: int, expected: dict[str, Any], observed: dict[str, Any]) -> list[dict[str, Any]]:
    issues = []
    for field in ("board", "phase", "winner", "capture_chain_piece"):
        if observed[field] != expected[field]:
            issues.append(_checkers_state_issue(index, field, "reference-rule-mismatch", expected[field], observed[field]))
    if expected["phase"] == "playing" and observed["active_player"] != expected["active_player"]:
        issues.append(_checkers_state_issue(
            index, "active_player", "turn-mismatch", expected["active_player"], observed["active_player"]
        ))
    return issues


def _checkers_reset_signature(observed: dict[str, Any]) -> dict[str, Any]:
    return {key: deepcopy(observed[key]) for key in (
        "board", "active_player", "phase", "winner", "capture_chain_piece"
    )}


def _checkers_reset_issues(index: int, observed: dict[str, Any]) -> list[dict[str, Any]]:
    pieces = [piece for row in observed["board"] for piece in row if piece is not None]
    issues = []
    if observed["phase"] != "playing" or observed["winner"] is not None:
        issues.append(_checkers_state_issue(index, "phase", "reset-not-active-game", "playing", observed["phase"]))
    if observed["active_player"] not in CHECKERS_PLAYERS:
        issues.append(_checkers_state_issue(index, "active_player", "reset-missing-active-player", "black-or-white", observed["active_player"]))
    if observed["capture_chain_piece"] is not None:
        issues.append(_checkers_state_issue(index, "capture_chain_piece", "reset-retained-capture-lock", None, observed["capture_chain_piece"]))
    if not {piece["player"] for piece in pieces}.issuperset(set(CHECKERS_PLAYERS)):
        issues.append(_checkers_state_issue(index, "board", "reset-missing-player-pieces", "both players", observed["board"]))
    return issues


def _expected_destinations(
    state: dict[str, Any], selected: tuple[int, int] | None, variant: dict[str, str], hints_visible: bool | None
) -> list[tuple[int, int]]:
    if selected is None or hints_visible is False:
        return []
    return _checkers_legal_from(state, selected, variant)


def _evaluate_checkers(case: dict[str, Any], observations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized = [_canonical_checkers_observation(item) for item in observations]
    if not normalized:
        raise ValueError("Checkers case requires observations")
    variant = normalized[0]["variant"]
    if any(observation["variant"] != variant for observation in normalized[1:]):
        return [{"index": index, "field": "variant", "reason": "variant-changed-within-trace"}
                for index, observation in enumerate(normalized) if observation["variant"] != variant]
    if len(normalized) != len(case["actions"]):
        raise ValueError("Checkers observation count must equal action count")

    issues: list[dict[str, Any]] = []
    state: dict[str, Any] | None = None
    selected: tuple[int, int] | None = None
    hints_visible: bool | None = None
    reset_signatures: dict[str, dict[str, Any]] = {}
    previous: dict[str, Any] | None = None
    for index, (action, observed) in enumerate(zip(case["actions"], normalized, strict=True)):
        action_type = action.get("type")
        if action_type == "set_fixture":
            if observed["fixture_applied"] is not True:
                raise ValueError("Checkers controlled fixture was not applied")
            state = _checkers_state_from_fixture(action.get("fixture"))
            selected = None
            issues.extend(_compare_checkers_state(index, state, observed))
        elif action_type == "reset":
            issues.extend(_checkers_reset_issues(index, observed))
            signature = _checkers_reset_signature(observed)
            if "remember_reset" in action:
                reset_signatures[action["remember_reset"]] = signature
            if "compare_reset" in action:
                expected_signature = reset_signatures.get(action["compare_reset"])
                if expected_signature is None:
                    raise ValueError("Checkers reset comparison lacks a remembered baseline")
                if signature != expected_signature:
                    issues.append(_checkers_state_issue(
                        index, "reset", "reset-does-not-restore-initial-game", expected_signature, signature
                    ))
            state = None
            selected = None
        elif state is None:
            raise ValueError("Checkers action requires a fixture or reset reference state")
        elif action_type == "select":
            selected = _square(action.get("square"), name="Checkers selected square")
            issues.extend(_compare_checkers_state(index, state, observed))
        elif action_type == "move":
            state = _apply_checkers_move(state, action, variant)
            selected = state["capture_chain_piece"]
            issues.extend(_compare_checkers_state(index, state, observed))
        elif action_type == "set_hints":
            if observed["action_supported"] is False or observed["hints_visible"] is None:
                issues.append({"index": index, "field": "hints_visible", "reason": "hint-toggle-unavailable"})
            else:
                requested = action.get("visible")
                if type(requested) is not bool:
                    raise ValueError("set_hints requires a boolean visible value")
                if observed["hints_visible"] != requested:
                    issues.append(_checkers_state_issue(
                        index, "hints_visible", "hint-toggle-did-not-reach-requested-visibility", requested,
                        observed["hints_visible"]
                    ))
                hints_visible = observed["hints_visible"]
            issues.extend(_compare_checkers_state(index, state, observed))
            if previous is not None:
                for field in ("board", "active_player", "phase", "winner", "capture_chain_piece"):
                    if observed[field] != previous[field]:
                        issues.append(_checkers_state_issue(
                            index, field, "hint-toggle-mutated-game-state", previous[field], observed[field]
                        ))
        else:
            raise ValueError(f"unsupported Checkers action {action_type!r}")

        if action.get("expect_selected") is not None:
            expected_selected = action["expect_selected"]
            if expected_selected == "none-or-source":
                source = _square(action.get("square"), name="Checkers selected square")
                if observed["selected"] not in (None, source):
                    issues.append(_checkers_state_issue(
                        index, "selected", "unexpected-selected-piece", "none-or-selected-source", observed["selected"]
                    ))
            else:
                expected_square = _square(expected_selected, name="expected selected square")
                if observed["selected"] != expected_square:
                    issues.append(_checkers_state_issue(
                        index, "selected", "selected-piece-not-visible", expected_square, observed["selected"]
                    ))
        if action.get("expect_destinations"):
            expected_selected = state["capture_chain_piece"] if state is not None and state["capture_chain_piece"] else selected
            effective_hints = hints_visible if case.get("requires_hints") else True
            expected_destinations = _expected_destinations(state, expected_selected, variant, effective_hints) if state else []
            if observed["legal_destinations"] != expected_destinations:
                issues.append(_checkers_state_issue(
                    index, "legal_destinations", "visible-destinations-do-not-match-legal-moves",
                    [list(square) for square in expected_destinations], [list(square) for square in observed["legal_destinations"]]
                ))
        if state is not None and state["capture_chain_piece"] is not None:
            if observed["selected"] != state["capture_chain_piece"]:
                issues.append(_checkers_state_issue(
                    index, "selected", "capture-chain-piece-not-kept-selected", state["capture_chain_piece"], observed["selected"]
                ))
        previous = observed
    return issues


def _canonical_battle_config(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != {"board_size", "fleet"}:
        raise ValueError("Battleship observation requires config with board_size and fleet")
    size = value["board_size"]
    fleet = value["fleet"]
    if type(size) is not int or not 2 <= size <= 16 or not isinstance(fleet, list) or not fleet:
        raise ValueError("Battleship config is invalid")
    normalized_fleet = []
    ids = set()
    for ship in fleet:
        if (
            not isinstance(ship, dict)
            or set(ship) != {"id", "length"}
            or not isinstance(ship["id"], str)
            or not ship["id"]
            or type(ship["length"]) is not int
            or not 1 <= ship["length"] <= size
            or ship["id"] in ids
        ):
            raise ValueError("Battleship fleet is invalid")
        ids.add(ship["id"])
        normalized_fleet.append({"id": ship["id"], "length": ship["length"]})
    return {"board_size": size, "fleet": normalized_fleet}


def _canonical_battle_grid(value: Any, size: int, markers: set[str], *, name: str) -> list[list[str]] | None:
    if value is None:
        return None
    if not isinstance(value, list) or len(value) != size:
        raise ValueError(f"Battleship {name} must be a {size} by {size} grid")
    grid: list[list[str]] = []
    for row in value:
        if not isinstance(row, list) or len(row) != size or any(cell not in markers for cell in row):
            raise ValueError(f"Battleship {name} has invalid cells")
        grid.append(list(row))
    return grid


def _canonical_history(value: Any) -> list[dict[str, Any]] | None:
    if value is None:
        return None
    if not isinstance(value, list):
        raise ValueError("Battleship history must be a list or null")
    history = []
    for entry in value:
        if not isinstance(entry, dict) or set(entry) != {"actor", "coordinate", "result"}:
            raise ValueError("Battleship history entry is malformed")
        if entry["actor"] not in PLAYERS or entry["result"] not in ("hit", "miss"):
            raise ValueError("Battleship history entry has invalid actor or result")
        history.append({
            "actor": entry["actor"],
            "coordinate": list(_square(entry["coordinate"], name="history coordinate")),
            "result": entry["result"],
        })
    return history


def _canonical_status_panel(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    if not isinstance(value, dict) or set(value) != {"active_player", "phase", "winner"}:
        raise ValueError("Battleship status_panel is malformed")
    active = value["active_player"]
    phase = value["phase"]
    winner = value["winner"]
    if active not in (*PLAYERS, None) or phase not in ("placement", "playing", "won") or winner not in (*PLAYERS, None):
        raise ValueError("Battleship status_panel has invalid values")
    return {"active_player": active, "phase": phase, "winner": winner}


def _canonical_last_action(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    if not isinstance(value, dict) or set(value) - {"supported", "accepted", "result", "sunk"}:
        raise ValueError("Battleship last_action is malformed")
    supported = value.get("supported", True)
    accepted = value.get("accepted")
    result = value.get("result")
    sunk = value.get("sunk")
    if type(supported) is not bool or type(accepted) is not bool:
        raise ValueError("Battleship last_action requires boolean supported and accepted")
    if result not in ("hit", "miss", None) or sunk not in (True, False, None):
        raise ValueError("Battleship last_action has invalid result or sunk flag")
    return {"supported": supported, "accepted": accepted, "result": result, "sunk": sunk}


def _canonical_battle_observation(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("Battleship observation must be an object")
    required = {"config", "phase", "active_player", "winner", "visible"}
    if required - set(value):
        raise ValueError("Battleship observation is incomplete")
    config = _canonical_battle_config(value["config"])
    phase = value["phase"]
    active = value["active_player"]
    winner = value["winner"]
    if phase not in ("placement", "playing", "won") or active not in (*PLAYERS, None) or winner not in (*PLAYERS, None):
        raise ValueError("Battleship observation has invalid game state")
    visible = value["visible"]
    if not isinstance(visible, dict) or set(visible) != {"viewer", "own_board", "opponent_board"}:
        raise ValueError("Battleship observation visible state is malformed")
    if visible["viewer"] not in PLAYERS:
        raise ValueError("Battleship visible state lacks a valid viewer")
    fixture_applied = value.get("fixture_applied")
    if fixture_applied not in (True, False, None):
        raise ValueError("Battleship fixture_applied must be boolean when supplied")
    history_filter = value.get("history_filter")
    if history_filter not in ("all", "hit", "miss", None):
        raise ValueError("Battleship history_filter is invalid")
    return {
        "config": config,
        "phase": phase,
        "active_player": active,
        "winner": winner,
        "visible": {
            "viewer": visible["viewer"],
            "own_board": _canonical_battle_grid(
                visible["own_board"], config["board_size"], {"empty", "ship", "hit", "miss"}, name="own_board"
            ),
            "opponent_board": _canonical_battle_grid(
                visible["opponent_board"], config["board_size"], {"unknown", "hit", "miss", "ship"}, name="opponent_board"
            ),
        },
        "status_panel": _canonical_status_panel(value.get("status_panel")),
        "history": _canonical_history(value.get("history")),
        "history_filter": history_filter,
        "visible_history": _canonical_history(value.get("visible_history")),
        "fixture_applied": fixture_applied,
        "last_action": _canonical_last_action(value.get("last_action")),
    }


def _fleet_lengths(config: dict[str, Any]) -> dict[str, int]:
    return {ship["id"]: ship["length"] for ship in config["fleet"]}


def _canonical_placements(value: Any, config: dict[str, Any]) -> dict[str, dict[str, list[tuple[int, int]]]]:
    if not isinstance(value, dict) or set(value) != set(PLAYERS):
        raise ValueError("Battleship fixture placements must name P1 and P2")
    lengths = _fleet_lengths(config)
    placements: dict[str, dict[str, list[tuple[int, int]]]] = {}
    for player in PLAYERS:
        player_placements = value[player]
        if not isinstance(player_placements, dict) or set(player_placements) - set(lengths):
            raise ValueError("Battleship fixture placement has an unknown ship")
        occupied = set()
        normalized: dict[str, list[tuple[int, int]]] = {}
        for ship, cells in player_placements.items():
            if not isinstance(cells, list) or len(cells) != lengths[ship]:
                raise ValueError("Battleship fixture ship has wrong length")
            coordinates = [_square(cell, name="fixture ship cell") for cell in cells]
            if len(set(coordinates)) != len(coordinates) or any(not _inside(cell, config["board_size"]) for cell in coordinates):
                raise ValueError("Battleship fixture ship placement is invalid")
            if occupied.intersection(coordinates):
                raise ValueError("Battleship fixture ships overlap")
            occupied.update(coordinates)
            normalized[ship] = coordinates
        placements[player] = normalized
    return placements


def _canonical_shots(value: Any, config: dict[str, Any]) -> dict[str, set[tuple[int, int]]]:
    if not isinstance(value, dict) or set(value) != set(PLAYERS):
        raise ValueError("Battleship fixture shots must name P1 and P2")
    shots: dict[str, set[tuple[int, int]]] = {}
    for player in PLAYERS:
        cells = value[player]
        if not isinstance(cells, list):
            raise ValueError("Battleship fixture shots must be lists")
        coordinates = {_square(cell, name="fixture shot") for cell in cells}
        if len(coordinates) != len(cells) or any(not _inside(cell, config["board_size"]) for cell in coordinates):
            raise ValueError("Battleship fixture shots are invalid")
        shots[player] = coordinates
    return shots


def _battle_state_from_fixture(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("Battleship fixture must be an object")
    required = {"config", "phase", "active_player", "winner", "placements", "shots", "history", "history_filter"}
    if required - set(value):
        raise ValueError("Battleship fixture is incomplete")
    config = _canonical_battle_config(value["config"])
    phase = value["phase"]
    active = value["active_player"]
    winner = value["winner"]
    if phase not in ("placement", "playing", "won") or active not in PLAYERS or winner not in (*PLAYERS, None):
        raise ValueError("Battleship fixture state is invalid")
    history = _canonical_history(value["history"])
    if history is None or value["history_filter"] not in ("all", "hit", "miss"):
        raise ValueError("Battleship fixture history is invalid")
    return {
        "config": config,
        "phase": phase,
        "active_player": active,
        "winner": winner,
        "placements": _canonical_placements(value["placements"], config),
        "shots": _canonical_shots(value["shots"], config),
        "history": history,
        "history_filter": value["history_filter"],
    }


def _placement_cells(start: tuple[int, int], direction: str, length: int) -> list[tuple[int, int]]:
    if direction not in ("horizontal", "vertical"):
        return []
    delta = (0, 1) if direction == "horizontal" else (1, 0)
    return [(start[0] + delta[0] * index, start[1] + delta[1] * index) for index in range(length)]


def _player_complete(state: dict[str, Any], player: str) -> bool:
    return set(state["placements"][player]) == set(_fleet_lengths(state["config"]))


def _apply_place_ship(state: dict[str, Any], action: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    result = deepcopy(state)
    player = action.get("player")
    ship = action.get("ship")
    if player not in PLAYERS or not isinstance(ship, str):
        raise ValueError("Battleship place_ship action is invalid")
    start = _square(action.get("start"), name="ship start")
    lengths = _fleet_lengths(state["config"])
    if state["phase"] != "placement" or player != state["active_player"] or ship not in lengths or ship in state["placements"][player]:
        return result, {"supported": True, "accepted": False, "result": None, "sunk": None}
    cells = _placement_cells(start, action.get("direction"), lengths[ship])
    occupied = {cell for existing in state["placements"][player].values() for cell in existing}
    if not cells or any(not _inside(cell, state["config"]["board_size"]) for cell in cells) or occupied.intersection(cells):
        return result, {"supported": True, "accepted": False, "result": None, "sunk": None}
    result["placements"][player][ship] = cells
    if _player_complete(result, player):
        opponent = _other_player(player)
        if _player_complete(result, opponent):
            result["phase"] = "playing"
            result["active_player"] = "P1"
        else:
            result["active_player"] = opponent
    return result, {"supported": True, "accepted": True, "result": None, "sunk": None}


def _ship_for_cell(state: dict[str, Any], player: str, coordinate: tuple[int, int]) -> str | None:
    for ship, cells in state["placements"][player].items():
        if coordinate in cells:
            return ship
    return None


def _is_sunk(state: dict[str, Any], player: str, ship: str) -> bool:
    return set(state["placements"][player][ship]).issubset(state["shots"][_other_player(player)])


def _apply_shot(state: dict[str, Any], action: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    result = deepcopy(state)
    player = action.get("player")
    if player not in PLAYERS:
        raise ValueError("Battleship shot action has invalid player")
    coordinate = _square(action.get("coordinate"), name="shot coordinate")
    if (
        state["phase"] != "playing"
        or state["active_player"] != player
        or not _inside(coordinate, state["config"]["board_size"])
        or coordinate in state["shots"][player]
    ):
        return result, {"supported": True, "accepted": False, "result": None, "sunk": None}
    opponent = _other_player(player)
    result["shots"][player].add(coordinate)
    ship = _ship_for_cell(state, opponent, coordinate)
    hit = ship is not None
    sunk = bool(ship and _is_sunk(result, opponent, ship))
    result["history"].append({
        "actor": player,
        "coordinate": list(coordinate),
        "result": "hit" if hit else "miss",
    })
    all_opponent_cells = {cell for cells in result["placements"][opponent].values() for cell in cells}
    if all_opponent_cells and all_opponent_cells.issubset(result["shots"][player]):
        result["phase"] = "won"
        result["winner"] = player
        result["active_player"] = player
    else:
        result["active_player"] = opponent
    return result, {"supported": True, "accepted": True, "result": "hit" if hit else "miss", "sunk": sunk}


def _battle_visible_boards(state: dict[str, Any], viewer: str) -> tuple[list[list[str]], list[list[str]]]:
    size = state["config"]["board_size"]
    opponent = _other_player(viewer)
    own = [["empty" for _column in range(size)] for _row in range(size)]
    opponent_view = [["unknown" for _column in range(size)] for _row in range(size)]
    own_cells = {cell for cells in state["placements"][viewer].values() for cell in cells}
    for row, column in own_cells:
        own[row][column] = "ship"
    for coordinate in state["shots"][opponent]:
        own[coordinate[0]][coordinate[1]] = "hit" if coordinate in own_cells else "miss"
    opponent_cells = {cell for cells in state["placements"][opponent].values() for cell in cells}
    for coordinate in state["shots"][viewer]:
        opponent_view[coordinate[0]][coordinate[1]] = "hit" if coordinate in opponent_cells else "miss"
    return own, opponent_view


def _battle_state_issue(index: int, field: str, reason: str, expected: Any, actual: Any) -> dict[str, Any]:
    return {"index": index, "field": field, "reason": reason, "expected": expected, "actual": actual}


def _expected_viewer(state: dict[str, Any]) -> str:
    return state["winner"] if state["phase"] == "won" and state["winner"] else state["active_player"]


def _compare_battle_state(index: int, state: dict[str, Any], observed: dict[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for field in ("config", "phase", "winner"):
        if observed[field] != state[field]:
            issues.append(_battle_state_issue(index, field, "reference-rule-mismatch", state[field], observed[field]))
    if state["phase"] in ("placement", "playing") and observed["active_player"] != state["active_player"]:
        issues.append(_battle_state_issue(
            index, "active_player", "turn-mismatch", state["active_player"], observed["active_player"]
        ))
    viewer = _expected_viewer(state)
    if observed["visible"]["viewer"] != viewer:
        issues.append(_battle_state_issue(index, "visible.viewer", "viewer-does-not-match-current-player", viewer, observed["visible"]["viewer"]))
        return issues
    own, target = _battle_visible_boards(state, viewer)
    if observed["visible"]["own_board"] != own:
        issues.append(_battle_state_issue(index, "visible.own_board", "visible-own-board-mismatch", own, observed["visible"]["own_board"]))
    if state["phase"] in ("playing", "won"):
        if observed["visible"]["opponent_board"] != target:
            reason = "opponent-unshot-ship-visible" if any(
                cell == "ship" for row in (observed["visible"]["opponent_board"] or []) for cell in row
            ) else "visible-opponent-board-mismatch"
            issues.append(_battle_state_issue(
                index, "visible.opponent_board", reason, target, observed["visible"]["opponent_board"]
            ))
    return issues


def _compare_last_action(index: int, observed: dict[str, Any], expected: dict[str, Any]) -> list[dict[str, Any]]:
    actual = observed["last_action"]
    if actual is None:
        raise ValueError("Battleship action observation lacks last_action")
    issues = []
    for field in ("supported", "accepted", "result", "sunk"):
        if actual[field] != expected[field]:
            issues.append(_battle_state_issue(index, f"last_action.{field}", "action-result-mismatch", expected[field], actual[field]))
    return issues


def _history_for_filter(history: list[dict[str, Any]], filter_name: str) -> list[dict[str, Any]]:
    return history if filter_name == "all" else [entry for entry in history if entry["result"] == filter_name]


def _compare_battle_history(index: int, state: dict[str, Any], observed: dict[str, Any]) -> list[dict[str, Any]]:
    if observed["status_panel"] is None or observed["history"] is None or observed["visible_history"] is None:
        raise ValueError("Battleship status/history capability is absent from observation")
    expected_status = {
        "active_player": state["active_player"], "phase": state["phase"], "winner": state["winner"],
    }
    issues = []
    if observed["status_panel"] != expected_status:
        issues.append(_battle_state_issue(index, "status_panel", "status-panel-does-not-match-game", expected_status, observed["status_panel"]))
    if observed["history"] != state["history"]:
        issues.append(_battle_state_issue(index, "history", "shot-history-mismatch", state["history"], observed["history"]))
    if observed["history_filter"] != state["history_filter"]:
        issues.append(_battle_state_issue(index, "history_filter", "history-filter-not-applied", state["history_filter"], observed["history_filter"]))
    expected_visible = _history_for_filter(state["history"], state["history_filter"])
    if observed["visible_history"] != expected_visible:
        issues.append(_battle_state_issue(index, "visible_history", "filtered-history-mismatch", expected_visible, observed["visible_history"]))
    return issues


def _battle_reset_signature(observed: dict[str, Any]) -> dict[str, Any]:
    return {
        "config": deepcopy(observed["config"]),
        "phase": observed["phase"],
        "active_player": observed["active_player"],
        "winner": observed["winner"],
        "visible": deepcopy(observed["visible"]),
    }


def _evaluate_battleship(case: dict[str, Any], observations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized = [_canonical_battle_observation(item) for item in observations]
    if len(normalized) != len(case["actions"]):
        raise ValueError("Battleship observation count must equal action count")
    issues: list[dict[str, Any]] = []
    state: dict[str, Any] | None = None
    reset_signatures: dict[str, dict[str, Any]] = {}
    previous: dict[str, Any] | None = None
    for index, (action, observed) in enumerate(zip(case["actions"], normalized, strict=True)):
        action_type = action.get("type")
        if action_type == "set_fixture":
            if observed["fixture_applied"] is not True:
                raise ValueError("Battleship controlled fixture was not applied")
            state = _battle_state_from_fixture(action.get("fixture"))
            issues.extend(_compare_battle_state(index, state, observed))
        elif action_type == "reset":
            if observed["phase"] != "placement" or observed["winner"] is not None:
                issues.append(_battle_state_issue(
                    index, "reset", "reset-does-not-return-to-placement", "placement without winner",
                    {"phase": observed["phase"], "winner": observed["winner"]}
                ))
            signature = _battle_reset_signature(observed)
            if "remember_reset" in action:
                reset_signatures[action["remember_reset"]] = signature
            if "compare_reset" in action:
                expected_signature = reset_signatures.get(action["compare_reset"])
                if expected_signature is None:
                    raise ValueError("Battleship reset comparison lacks a remembered baseline")
                if signature != expected_signature:
                    issues.append(_battle_state_issue(
                        index, "reset", "reset-does-not-restore-initial-game", expected_signature, signature
                    ))
            state = None
        elif state is None:
            raise ValueError("Battleship action requires a fixture or reset reference state")
        elif action_type == "place_ship":
            state, expected_action = _apply_place_ship(state, action)
            issues.extend(_compare_battle_state(index, state, observed))
            issues.extend(_compare_last_action(index, observed, expected_action))
        elif action_type == "shot":
            state, expected_action = _apply_shot(state, action)
            issues.extend(_compare_battle_state(index, state, observed))
            issues.extend(_compare_last_action(index, observed, expected_action))
        elif action_type == "set_history_filter":
            filter_name = action.get("filter")
            if filter_name not in ("all", "hit", "miss"):
                raise ValueError("Battleship filter action is invalid")
            actual = observed["last_action"]
            if actual is None:
                raise ValueError("Battleship filter observation lacks last_action")
            if actual["supported"] is False:
                issues.append({"index": index, "field": "history_filter", "reason": "history-filter-unavailable"})
            state = deepcopy(state)
            state["history_filter"] = filter_name
            issues.extend(_compare_battle_state(index, state, observed))
            if previous is not None:
                for field in ("config", "phase", "active_player", "winner", "visible"):
                    if observed[field] != previous[field]:
                        issues.append(_battle_state_issue(
                            index, field, "history-filter-mutated-game-state", previous[field], observed[field]
                        ))
        else:
            raise ValueError(f"unsupported Battleship action {action_type!r}")

        if case.get("requires_history") and state is not None:
            issues.extend(_compare_battle_history(index, state, observed))
        previous = observed
    return issues


def evaluate(case: dict[str, Any], observations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return behavioral issues for one full semantic trace.

    ``ValueError`` means that a driver omitted or malformed required semantic
    evidence.  The caller must report that outcome as unverified instead of
    turning an unsupported fixture or UI mapping into a product failure.
    """
    if not isinstance(case, dict) or not isinstance(case.get("id"), str) or not isinstance(case.get("actions"), list):
        raise ValueError("case must be a catalog case with id and actions")
    if case["id"] not in _CASE_BY_ID or _CASE_BY_ID[case["id"]]["game"] != case.get("game"):
        raise ValueError("case is not a recognized game-oracle case")
    if not isinstance(observations, list):
        raise ValueError("observations must be a list")
    if case["game"] == "checkers":
        return _evaluate_checkers(case, observations)
    if case["game"] == "battleship":
        return _evaluate_battleship(case, observations)
    raise ValueError("unsupported game")


# Test-only trace synthesis.  This stays private so the public contract remains
# cases/evaluate; it lets calibration tests carry complete semantic snapshots
# without a browser or product implementation.
_TEST_VARIANT = {
    "capture_priority": "any",
    "men_capture_direction": "forward",
    "promotion_capture_continuation": "end-turn",
}


def _starting_checkers_state() -> dict[str, Any]:
    pieces = []
    for row in range(3):
        for column in range(8):
            if _dark((row, column)):
                pieces.append((row, column, "white", False))
    for row in range(5, 8):
        for column in range(8):
            if _dark((row, column)):
                pieces.append((row, column, "black", False))
    return _checkers_state_from_fixture(_checkers_fixture(pieces))


def _synthetic_checkers_trace(case: dict[str, Any]) -> list[dict[str, Any]]:
    result = []
    state: dict[str, Any] | None = None
    selected: tuple[int, int] | None = None
    hints: bool | None = None
    for action in case["actions"]:
        fixture = False
        action_type = action["type"]
        if action_type == "set_fixture":
            state = _checkers_state_from_fixture(action["fixture"])
            selected = None
            fixture = True
        elif action_type == "reset":
            state = _starting_checkers_state()
            selected = None
        elif action_type == "select":
            assert state is not None
            selected = _square(action["square"])
        elif action_type == "move":
            assert state is not None
            state = _apply_checkers_move(state, action, _TEST_VARIANT)
            selected = state["capture_chain_piece"]
        elif action_type == "set_hints":
            hints = action["visible"]
        else:
            raise AssertionError(action_type)
        assert state is not None
        effective_hints = hints if case.get("requires_hints") else True
        destinations = _expected_destinations(state, selected, _TEST_VARIANT, effective_hints)
        result.append({
            "board": deepcopy(state["board"]),
            "active_player": state["active_player"],
            "phase": state["phase"],
            "winner": state["winner"],
            "selected": _json_square(selected),
            "legal_destinations": [list(square) for square in destinations],
            "capture_chain_piece": _json_square(state["capture_chain_piece"]),
            "variant": deepcopy(_TEST_VARIANT),
            "hints_visible": hints,
            "fixture_applied": True if fixture else None,
            "action_supported": True,
        })
    return result


def _synthetic_battle_observation(
    state: dict[str, Any], *, fixture: bool = False, last_action: dict[str, Any] | None = None,
    include_history: bool = False,
) -> dict[str, Any]:
    viewer = _expected_viewer(state)
    own, opponent = _battle_visible_boards(state, viewer)
    observation = {
        "config": deepcopy(state["config"]),
        "phase": state["phase"],
        "active_player": state["active_player"],
        "winner": state["winner"],
        "visible": {"viewer": viewer, "own_board": own, "opponent_board": opponent},
        "fixture_applied": True if fixture else None,
        "last_action": deepcopy(last_action),
    }
    if include_history:
        observation.update({
            "status_panel": {
                "active_player": state["active_player"], "phase": state["phase"], "winner": state["winner"],
            },
            "history": deepcopy(state["history"]),
            "history_filter": state["history_filter"],
            "visible_history": deepcopy(_history_for_filter(state["history"], state["history_filter"])),
        })
    return observation


def _starting_battle_state() -> dict[str, Any]:
    return _battle_state_from_fixture(_battle_fixture(
        phase="placement", active="P1", placements={"P1": {}, "P2": {}}
    ))


def _synthetic_battleship_trace(case: dict[str, Any]) -> list[dict[str, Any]]:
    result = []
    state: dict[str, Any] | None = None
    for action in case["actions"]:
        action_type = action["type"]
        fixture = False
        last_action = None
        if action_type == "set_fixture":
            state = _battle_state_from_fixture(action["fixture"])
            fixture = True
        elif action_type == "reset":
            state = _starting_battle_state()
        elif action_type == "place_ship":
            assert state is not None
            state, last_action = _apply_place_ship(state, action)
        elif action_type == "shot":
            assert state is not None
            state, last_action = _apply_shot(state, action)
        elif action_type == "set_history_filter":
            assert state is not None
            state = deepcopy(state)
            state["history_filter"] = action["filter"]
            last_action = {"supported": True, "accepted": True, "result": None, "sunk": None}
        else:
            raise AssertionError(action_type)
        assert state is not None
        result.append(_synthetic_battle_observation(
            state, fixture=fixture, last_action=last_action, include_history=bool(case.get("requires_history"))
        ))
    return result


def _synthetic_observations(case: dict[str, Any]) -> list[dict[str, Any]]:
    """Return a private calibration trace; never use this against a candidate."""
    if case["game"] == "checkers":
        return _synthetic_checkers_trace(case)
    return _synthetic_battleship_trace(case)
