"""Held-out acceptance checks for the `user-listing` case (style: brownfield), read from its prompt and never shown to a model.

``quality.acceptance`` imports this module and calls each function in ``CHECKS`` with the base URL of the delivered server,
which it started on a free port; a check returns ``(ok, note)``. They run inside the harness process, so neither this file's
name nor a check id is ever on a command line, and nothing is written into the delivery. Each is a black box over HTTP: the
prompt is the only specification, and ``cases.json`` quotes the sentence each check reads (``source``) and its ``grade``.

The case starts from fixtures/node-base, whose store holds the three users below. Two checks are pass-to-pass (the API the
base already has must answer as it did); the rest are fail-to-pass (the base answers every listing with the whole array).
The checks run in this order against one server, the existing API first, so a delivery that crashes on a boundary input
fails that check and the ones after it, never the compatibility checks. Extra fields in a page object are allowed; the users
in it must be the store's users as GET /users answers them.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request

CALL_SECONDS = 5  # a ceiling for one HTTP call: a call that has not answered by then fails its check
ADA = {"id": 1, "name": "Ada Lovelace", "email": "ada@example.com"}
GRACE = {"id": 2, "name": "Grace Hopper", "email": "grace@example.com"}
ALAN = {"id": 3, "name": "Alan Turing", "email": "alan@example.com"}
USERS = [ADA, GRACE, ALAN]
PAGE_KEYS = ("page", "size", "total", "pages", "items")


def get(base: str, path: str) -> tuple[int, object]:
    """One GET; the status and the parsed JSON body (None when the body is not JSON)."""
    try:
        with urllib.request.urlopen(base + path, timeout=CALL_SECONDS) as response:
            status, raw = response.status, response.read()
    except urllib.error.HTTPError as error:
        with error:  # closes the response
            status, raw = error.code, error.read()
    try:
        return status, json.loads(raw or b"null")
    except ValueError:
        return status, None


def short(body) -> str:
    return json.dumps(body)[:100]


def names(body) -> object:
    """The names of a list of users, for a note; the body itself when it is not one."""
    return [user.get("name") for user in body if isinstance(user, dict)] if isinstance(body, list) else body


def arrays(base: str, expected: dict[str, list]) -> tuple[bool, str]:
    """Each path must answer 200 with exactly its users, as a JSON array."""
    wrong = []
    for path, users in expected.items():
        status, body = get(base, path)
        if status != 200 or body != users:
            wrong.append(f"{path}: HTTP {status} {short(names(body))}")
    return not wrong, "; ".join(wrong) or f"{len(expected)} listings answered with the expected users"


def pages(base: str, expected: dict[str, tuple]) -> tuple[bool, str]:
    """Each path must answer 200 with a page object whose page, size, total, pages and items are the expected ones."""
    wrong = []
    for path, values in expected.items():
        status, body = get(base, path)
        want = dict(zip(PAGE_KEYS, values))
        paged = isinstance(body, dict) and all(key in body for key in PAGE_KEYS)
        got = {key: body[key] for key in PAGE_KEYS} if paged else body
        if status != 200 or got != want:
            wrong.append(f"{path}: HTTP {status} {short({**got, 'items': names(got['items'])} if paged else names(body))}")
    return not wrong, "; ".join(wrong) or f"{len(expected)} pages answered as expected"


def list_unchanged(base: str) -> tuple[bool, str]:
    return arrays(base, {"/users": USERS, "/users?sort=name&_=1": USERS})


def user_by_id_unchanged(base: str) -> tuple[bool, str]:
    found, body = get(base, "/users/2")
    missing, _body = get(base, "/users/42")
    ok = found == 200 and body == GRACE and missing == 404
    return ok, f"/users/2: HTTP {found} {short(body)}; /users/42: HTTP {missing}"


def name_filter(base: str) -> tuple[bool, str]:
    return arrays(base, {"/users?name=AL": [ALAN], "/users?name=GRACE": [GRACE], "/users?name=e": [ADA, GRACE],
                         "/users?name=Grace%20H": [GRACE], "/users?name=": USERS, "/users?name=zzz": []})


def name_plain_text(base: str) -> tuple[bool, str]:
    # A regular expression would match "a.a" in "Ada" and "." everywhere, and throw on "(".
    return arrays(base, {"/users?name=a.a": [], "/users?name=.": [], "/users?name=(": []})


def page_envelope(base: str) -> tuple[bool, str]:
    return pages(base, {"/users?page=1&size=2": (1, 2, 3, 2, [ADA, GRACE])})


def partial_last_page(base: str) -> tuple[bool, str]:
    # The base's paginate floors the page count, so it loses the last page whenever the users do not fill it.
    return pages(base, {"/users?page=2&size=2": (2, 2, 3, 2, [ALAN]), "/users?page=1&size=3": (1, 3, 3, 1, USERS),
                        "/users?page=3&size=1": (3, 1, 3, 3, [ALAN])})


def page_past_end(base: str) -> tuple[bool, str]:
    return pages(base, {"/users?page=3&size=2": (3, 2, 3, 2, [])})


def page_defaults(base: str) -> tuple[bool, str]:
    return pages(base, {"/users?page=1": (1, 10, 3, 1, USERS), "/users?size=2": (1, 2, 3, 2, [ADA, GRACE])})


def filter_then_page(base: str) -> tuple[bool, str]:
    return pages(base, {"/users?name=e&page=2&size=1": (2, 1, 2, 2, [GRACE]),
                        "/users?name=zzz&page=1&size=5": (1, 5, 0, 0, [])})


def size_bounds(base: str) -> tuple[bool, str]:
    return pages(base, {"/users?size=100": (1, 100, 3, 1, USERS), "/users?size=1": (1, 1, 3, 3, [ADA])})


def bad_page_or_size(base: str) -> tuple[bool, str]:
    wrong = []
    for query in ("page=0", "page=-1", "page=1.5", "page=abc", "page=", "size=0", "size=101", "size=1.5", "size=abc", "size="):
        status, body = get(base, f"/users?{query}")
        refused = (status == 400 and isinstance(body, dict) and isinstance(body.get("error"), str) and body["error"].strip()
                   and "items" not in body)
        if not refused:
            wrong.append(f"{query}: HTTP {status} {short(names(body))}")
    return not wrong, "; ".join(wrong) or "every bad page or size answered 400 with an error and no users"


CHECKS = {
    "list-unchanged": list_unchanged,
    "user-by-id-unchanged": user_by_id_unchanged,
    "name-filter": name_filter,
    "name-plain-text": name_plain_text,
    "page-envelope": page_envelope,
    "partial-last-page": partial_last_page,
    "page-past-end": page_past_end,
    "page-defaults": page_defaults,
    "filter-then-page": filter_then_page,
    "size-bounds": size_bounds,
    "bad-page-or-size": bad_page_or_size,
}
