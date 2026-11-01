"""Held-out acceptance checks for the `user-team-listing` case (style: brownfield), the third pass of chain B and the one that must reuse what the
first pass set, read from its prompt and never shown to a model.

``quality.acceptance`` calls each function in ``CHECKS`` with the base URL of the delivered server, which it started on a free port; a check
returns ``(ok, note)``. They run inside the harness process: neither this file's name nor a check id is ever on a command line, and nothing
is written into the delivery. Each is a black box over HTTP.

The case starts from the second pass's delivery (``follows``, ``--continue-from``). Sixteen checks are the earlier passes' (the first request's
eleven and the second's five, from user_roles_accept.py) and run as pass-to-pass. Seven are fail-to-pass and read the request, which asks that
``GET /teams`` list the teams "the way ``GET /users`` lists users", errors included, and that ``GET /teams/:id`` answer 404 "the way"
``GET /users/:id`` does. Five of them read a rule the first request set for the users and the first pass wrote into its living files: the
name matched as plain text and ignoring case, a page count that counts a partly filled last page (the base's own ``paginate`` floors it, and
the first pass either mended that helper or computed the count itself, and said so), the default page size of 10 and the largest of 100, and
the refusal of anything else. A run that reads those from what the earlier passes left reuses them; a run that works them out again may not.

* ``teams-listing``: the five teams of the request in id order, each with its ``members``, and any other query parameter ignored.
* ``team-by-id``: each team by id; a team that does not exist is a 404 with a JSON object whose "error" is a text.
* ``teams-name-filter``: part of a name, ignoring case and as plain text (``a.a``, ``.``, ``(`` keep no team), an empty name keeping every team.
* ``teams-pages``: ``page``, ``size``, ``total``, ``pages`` and ``items``; a partly filled last page counted; a page after the last empty; a
  ``name`` applied before the paging.
* ``teams-page-defaults``: ``size`` is 10 when only ``page`` is given and ``page`` is 1 when only ``size`` is given. A later request replaces
  the 10 (``user-page-size``), which is why that case declares an acceptance of its own.
* ``teams-size-bounds``: ``size`` 1 and 100 are accepted. A later request replaces the 100.
* ``teams-bad-page-or-size``: ``page`` and ``size`` that are not whole numbers in range, an empty one included, answer 400 with an error and no teams.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location("shiploop_e2e_held_out_user_roles", Path(__file__).with_name("user_roles_accept.py"))
R = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(R)
UL = R.UL

raw_get = R.raw_get
TEAMS = [
    {"id": 1, "name": "Analytical Engine", "members": [1]},
    {"id": 2, "name": "Compilers", "members": [2]},
    {"id": 3, "name": "Computing Machinery", "members": [3]},
    {"id": 4, "name": "Cryptanalysis", "members": [3]},
    {"id": 5, "name": "Data Systems", "members": [1, 2]},
]
EVERY = [team["id"] for team in TEAMS]


def shown(body) -> object:
    """A list of teams as (id, name, members); the body itself when it is not one."""
    if isinstance(body, list):
        return [(t.get("id"), t.get("name"), t.get("members")) if isinstance(t, dict) else t for t in body]
    return body


def short(body) -> str:
    return UL.short(body)


def teams_listing(base: str) -> tuple[bool, str]:
    want = [(t["id"], t["name"], t["members"]) for t in TEAMS]
    wrong = []
    for path in ("/teams", "/teams?sort=name&_=1"):
        status, body = raw_get(base, path)
        if status != 200 or shown(body) != want:
            wrong.append(f"{path}: HTTP {status} {short(shown(body))}")
    return not wrong, "; ".join(wrong) or "the five teams answered in id order with their members, and an unrelated parameter was ignored"


def team_by_id(base: str) -> tuple[bool, str]:
    wrong = []
    for team in TEAMS:
        status, body = raw_get(base, f"/teams/{team['id']}")
        if status != 200 or not isinstance(body, dict) or (body.get("id"), body.get("name"), body.get("members")) != (team["id"], team["name"], team["members"]):
            wrong.append(f"/teams/{team['id']}: HTTP {status} {short(body)}")
    for path in ("/teams/99", "/teams/0"):
        status, body = raw_get(base, path)
        if status != 404 or not isinstance(body, dict) or not isinstance(body.get("error"), str):
            wrong.append(f"{path}: HTTP {status} {short(body)}, wanted 404 with an error text")
    return not wrong, "; ".join(wrong) or "every team answered by id, and a missing one answered 404 with an error"


def teams_name_filter(base: str) -> tuple[bool, str]:
    return R.listings(base, {"/teams?name=COMP": [2, 3], "/teams?name=an": [1, 4], "/teams?name=SYS": [5], "/teams?name=Data%20S": [5],
                             "/teams?name=a.a": [], "/teams?name=.": [], "/teams?name=(": [], "/teams?name=": EVERY, "/teams?name=zzz": []})


def teams_pages(base: str) -> tuple[bool, str]:
    return R.pages_of(base, {"/teams?page=1&size=2": (1, 2, 5, 3, [1, 2]), "/teams?page=2&size=2": (2, 2, 5, 3, [3, 4]),
                             "/teams?page=3&size=2": (3, 2, 5, 3, [5]), "/teams?page=1&size=5": (1, 5, 5, 1, EVERY),
                             "/teams?page=5&size=1": (5, 1, 5, 5, [5]), "/teams?page=4&size=2": (4, 2, 5, 3, []),
                             "/teams?name=comp&page=2&size=1": (2, 1, 2, 2, [3]), "/teams?name=zzz&page=1&size=5": (1, 5, 0, 0, [])})


def teams_page_defaults(base: str) -> tuple[bool, str]:
    return R.pages_of(base, {"/teams?page=1": (1, 10, 5, 1, EVERY), "/teams?size=2": (1, 2, 5, 3, [1, 2])})


def teams_size_bounds(base: str) -> tuple[bool, str]:
    return R.pages_of(base, {"/teams?size=100": (1, 100, 5, 1, EVERY), "/teams?size=1": (1, 1, 5, 5, [1])})


def teams_bad_page_or_size(base: str) -> tuple[bool, str]:
    wrong = []
    for query in ("page=0", "page=-1", "page=1.5", "page=abc", "page=", "size=0", "size=101", "size=1.5", "size=abc", "size="):
        status, body = raw_get(base, f"/teams?{query}")
        refused = (status == 400 and isinstance(body, dict) and isinstance(body.get("error"), str) and body["error"].strip()
                   and "items" not in body)
        if not refused:
            wrong.append(f"{query}: HTTP {status} {short(shown(body))}")
    return not wrong, "; ".join(wrong) or "every bad page or size answered 400 with an error and no teams"


CHECKS = {
    **R.CHECKS,
    "teams-listing": teams_listing,
    "team-by-id": team_by_id,
    "teams-name-filter": teams_name_filter,
    "teams-pages": teams_pages,
    "teams-page-defaults": teams_page_defaults,
    "teams-size-bounds": teams_size_bounds,
    "teams-bad-page-or-size": teams_bad_page_or_size,
}
