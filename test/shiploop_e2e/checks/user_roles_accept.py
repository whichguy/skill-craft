"""Held-out acceptance checks for the `user-roles` case (style: brownfield), the second pass of chain B and a cross-cutting field, read from its
prompt and never shown to a model.

``quality.acceptance`` calls each function in ``CHECKS`` with the base URL of the delivered server, which it started on a free port; a check
returns ``(ok, note)``. They run inside the harness process: neither this file's name nor a check id is ever on a command line, and nothing
is written into the delivery. Each is a black box over HTTP.

The case starts from the first pass's delivery (``follows``, ``--continue-from``). Eleven checks are the first pass's, loaded from
user_listing_accept.py and run as pass-to-pass: everything the request for `user-listing` asked, which this request says keeps working. Those
checks compare whole user records, and a user now has a ``role``, so the module shows them every answer without ``role`` (``strip_role``): the
first pass's rules are read as they were written, and the new field is read by the new checks. Five checks are fail-to-pass and read the
request:

* ``role-shown``: the role is in GET /users/:id, in the array, in a filtered array and in the items of a page (Ada admin, Grace member, Alan viewer).
* ``role-filter``: ``role=<role>`` keeps only the users with that role and still answers an array; an unrelated parameter beside it is still ignored.
* ``filters-combine``: a user must match every filter given: name and role together, an empty name beside a role.
* ``role-then-page``: with a role, ``total`` and ``pages`` count the users that matched, and a page past the end of those is empty (the first
  pass's rule about ``name``, kept for the new filter).
* ``bad-role``: a role that is none of the three, an empty one included, answers 400 with an error and no users; the first pass's page and size
  rules still refuse beside a valid role.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location("shiploop_e2e_held_out_user_listing", Path(__file__).with_name("user_listing_accept.py"))
UL = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(UL)

ROLES = {1: "admin", 2: "member", 3: "viewer"}
raw_get = UL.get


def strip_role(body):
    """The body without any ``role`` field, so a check written before roles existed compares the records it knew."""
    if isinstance(body, list):
        return [strip_role(item) for item in body]
    if isinstance(body, dict):
        return {key: strip_role(value) for key, value in body.items() if key != "role"}
    return body


def get_without_role(base: str, path: str):
    status, body = raw_get(base, path)
    return status, strip_role(body)


UL.get = get_without_role  # the first pass's checks and helpers call ``get`` by name: they now see the records as they were


def ids(body) -> object:
    return [user.get("id") for user in body if isinstance(user, dict)] if isinstance(body, list) else body


def page_of(body) -> object:
    if isinstance(body, dict) and all(key in body for key in UL.PAGE_KEYS):
        return body["page"], body["size"], body["total"], body["pages"], ids(body["items"])
    return body


def listings(base: str, expected: dict[str, list]) -> tuple[bool, str]:
    """Each path must answer 200 with an array of exactly these user ids."""
    wrong = []
    for path, want in expected.items():
        status, body = raw_get(base, path)
        if status != 200 or ids(body) != want:
            wrong.append(f"{path}: HTTP {status} {UL.short(ids(body))}, wanted {want}")
    return not wrong, "; ".join(wrong) or f"{len(expected)} listings answered with the expected users"


def pages_of(base: str, expected: dict[str, tuple]) -> tuple[bool, str]:
    """Each path must answer 200 with a page object whose page, size, total, pages and item ids are these."""
    wrong = []
    for path, want in expected.items():
        status, body = raw_get(base, path)
        if status != 200 or page_of(body) != want:
            wrong.append(f"{path}: HTTP {status} {UL.short(page_of(body))}, wanted {want}")
    return not wrong, "; ".join(wrong) or f"{len(expected)} pages answered as expected"


def roles_of(body) -> object:
    return {user.get("id"): user.get("role") for user in body if isinstance(user, dict)} if isinstance(body, list) else body


def role_shown(base: str) -> tuple[bool, str]:
    wrong = []
    for ident, role in ROLES.items():
        status, body = raw_get(base, f"/users/{ident}")
        if status != 200 or not isinstance(body, dict) or body.get("role") != role:
            wrong.append(f"/users/{ident}: HTTP {status} role {body.get('role') if isinstance(body, dict) else body!r}, wanted {role}")
    status, body = raw_get(base, "/users")
    if status != 200 or roles_of(body) != ROLES:
        wrong.append(f"/users: HTTP {status} roles {roles_of(body)}, wanted {ROLES}")
    status, body = raw_get(base, "/users?name=grace")
    if status != 200 or roles_of(body) != {2: "member"}:
        wrong.append(f"/users?name=grace: HTTP {status} roles {roles_of(body)}, wanted {{2: 'member'}}")
    status, body = raw_get(base, "/users?page=1&size=3")
    items = body.get("items") if isinstance(body, dict) else None
    if status != 200 or roles_of(items) != ROLES:
        wrong.append(f"/users?page=1&size=3: HTTP {status} roles of the items {roles_of(items)}, wanted {ROLES}")
    return not wrong, "; ".join(wrong) or "every user shows its role by id, in the array, in a filtered array and in a page"


def role_filter(base: str) -> tuple[bool, str]:
    return listings(base, {"/users?role=admin": [1], "/users?role=member": [2], "/users?role=viewer": [3], "/users?role=admin&sort=name&_=1": [1]})


def filters_combine(base: str) -> tuple[bool, str]:
    return listings(base, {"/users?name=a&role=viewer": [3], "/users?name=a&role=admin": [1], "/users?name=e&role=member": [2],
                           "/users?name=grace&role=admin": [], "/users?name=alan&role=member": [], "/users?name=zzz&role=member": [],
                           "/users?name=&role=member": [2]})


def role_then_page(base: str) -> tuple[bool, str]:
    return pages_of(base, {"/users?role=viewer&page=1&size=1": (1, 1, 1, 1, [3]), "/users?role=admin&page=1&size=2": (1, 2, 1, 1, [1]),
                           "/users?role=member&page=2&size=1": (2, 1, 1, 1, []), "/users?name=a&role=member&page=1&size=5": (1, 5, 1, 1, [2]),
                           "/users?name=alan&role=admin&page=1&size=5": (1, 5, 0, 0, [])})


def bad_role(base: str) -> tuple[bool, str]:
    wrong = []
    for query in ("role=owner", "role=", "role=root", "role=%20", "role=owner&page=1&size=2", "role=admin&page=0", "role=member&size=0"):
        status, body = raw_get(base, f"/users?{query}")
        refused = (status == 400 and isinstance(body, dict) and isinstance(body.get("error"), str) and body["error"].strip()
                   and "items" not in body)
        if not refused:
            wrong.append(f"{query}: HTTP {status} {UL.short(body)}")
    return not wrong, "; ".join(wrong) or "every bad role, and a bad page or size beside a role, answered 400 with an error and no users"


CHECKS = {
    **UL.CHECKS,
    "role-shown": role_shown,
    "role-filter": role_filter,
    "filters-combine": filters_combine,
    "role-then-page": role_then_page,
    "bad-role": bad_role,
}
