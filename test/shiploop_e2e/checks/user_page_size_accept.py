"""Held-out acceptance checks for the `user-page-size` case (style: brownfield), the fourth pass of chain B and the one that CHANGES a rule
the first request set (as `ticket-sla` does for the ticket chain), read from its prompt and never shown to a model.

``quality.acceptance`` calls each function in ``CHECKS`` as it calls the earlier cases': with the delivered server's base URL, and, for a check
that takes a second parameter, with the delivered copy (``quality.Product``), which can start the server again with an environment of its own.
The case starts from the third pass's delivery (``follows``, ``--continue-from``). Nineteen checks are pass-to-pass: everything the third
link's acceptance asked, except four. ``page-defaults`` and ``size-bounds`` (the first request's) and ``teams-page-defaults`` and
``teams-size-bounds`` (the third's) read the sentences this request replaces ("a page holds 10 when `size` is not given", "`size` goes up to
100"), so a correct delivery fails them by design, which is why the case declares an acceptance of its own and does not inherit the third
link's. Three checks are fail-to-pass and read the new rules:

* ``page-size-default``: with PAGE_SIZE unset a page without ``size`` holds 25, for the users and for the teams, and a ``size`` that is given wins.
* ``page-size-setting``: with PAGE_SIZE=2 both listings page by 2 when ``size`` is not given; the plain array (neither ``page`` nor ``size``) is
  still the whole list, which the first request set and this one does not replace; a ``size`` that is given beats the setting.
* ``page-size-largest``: ``size`` 50 is accepted and 51 and 100 are refused with an error and no records, for both listings.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location("shiploop_e2e_held_out_user_team_listing", Path(__file__).with_name("user_team_listing_accept.py"))
T = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(T)
R = T.R

DROPPED = ("page-defaults", "size-bounds", "teams-page-defaults", "teams-size-bounds")
EVERY_TEAM = T.EVERY


def page_size_default(base: str, product) -> tuple[bool, str]:
    with product.serve({"PAGE_SIZE": None}) as unset:
        return R.pages_of(unset, {"/users?page=1": (1, 25, 3, 1, [1, 2, 3]), "/teams?page=1": (1, 25, 5, 1, EVERY_TEAM),
                                  "/users?size=2": (1, 2, 3, 2, [1, 2]), "/teams?page=2&size=2": (2, 2, 5, 3, [3, 4])})


def page_size_setting(base: str, product) -> tuple[bool, str]:
    wrong = []
    with product.serve({"PAGE_SIZE": "2"}) as two:
        for ok, note in (R.pages_of(two, {"/users?page=1": (1, 2, 3, 2, [1, 2]), "/users?page=2": (2, 2, 3, 2, [3]),
                                          "/teams?page=1": (1, 2, 5, 3, [1, 2]), "/teams?page=3": (3, 2, 5, 3, [5]),
                                          "/users?size=3": (1, 3, 3, 1, [1, 2, 3]), "/teams?size=5": (1, 5, 5, 1, EVERY_TEAM)}),
                         R.listings(two, {"/users": [1, 2, 3], "/teams": EVERY_TEAM, "/users?role=admin": [1]})):
            if not ok:
                wrong.append(note)
    return not wrong, "; ".join(wrong) or "PAGE_SIZE=2 set the default page size of both listings, the plain arrays stayed whole, and a given size won"


def page_size_largest(base: str, product) -> tuple[bool, str]:
    wrong = []
    with product.serve({"PAGE_SIZE": None}) as unset:
        ok, note = R.pages_of(unset, {"/users?size=50": (1, 50, 3, 1, [1, 2, 3]), "/teams?size=50": (1, 50, 5, 1, EVERY_TEAM)})
        if not ok:
            wrong.append(note)
        for path in ("/users?size=51", "/users?size=100", "/teams?size=51", "/teams?size=100", "/users?page=1&size=51"):
            status, body = R.raw_get(unset, path)
            refused = (status == 400 and isinstance(body, dict) and isinstance(body.get("error"), str) and body["error"].strip()
                       and "items" not in body)
            if not refused:
                wrong.append(f"{path}: HTTP {status} {R.UL.short(body)}, wanted 400 with an error and no records")
    return not wrong, "; ".join(wrong) or "size 50 was accepted and 51 and 100 were refused, for both listings"


CHECKS = {
    **{name: check for name, check in T.CHECKS.items() if name not in DROPPED},
    "page-size-default": page_size_default,
    "page-size-setting": page_size_setting,
    "page-size-largest": page_size_largest,
}
