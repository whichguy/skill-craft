"""Held-out acceptance for the light K2 user-teams link.

The reference extends the in-memory store, list and detail routes, filters and page path in node-base. Team is opt-in in HTTP
responses so every user-listing object keeps its existing shape by default. These checks read that contract without requiring
persistence, a CLI or an audit subsystem.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "shiploop_e2e_user_listing_helpers", Path(__file__).with_name("user_listing_accept.py"))
A = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(A)

ADA = {**A.ADA, "team": "Engineering"}
GRACE = {**A.GRACE, "team": "Engineering"}
ALAN = {**A.ALAN, "team": "Support"}


def team_filter_exact(base: str) -> tuple[bool, str]:
    return A.arrays(base, {
        "/users?team=Engineering": [A.ADA, A.GRACE],
        "/users?team=Support": [A.ALAN],
        "/users?team=Eng": [],
        "/users?team=": [],
        "/users?team=unknown": [],
    })


def team_filter_case_sensitive(base: str) -> tuple[bool, str]:
    return A.arrays(base, {"/users?team=engineering": []})


def team_filters_combine_before_page(base: str) -> tuple[bool, str]:
    return A.pages(base, {
        "/users?name=e&team=Engineering&page=2&size=1": (2, 1, 2, 2, [A.GRACE]),
        "/users?name=Alan&team=Engineering&page=1&size=1": (1, 1, 0, 0, []),
    })


def team_include_opt_in(base: str) -> tuple[bool, str]:
    wrong = []
    for path, expected in (
        ("/users?include=team", [ADA, GRACE, ALAN]),
        ("/users?page=1&size=2&include=team", None),
    ):
        status, body = A.get(base, path)
        if path.endswith("include=team") and "page=" not in path:
            if status != 200 or body != expected:
                wrong.append(f"{path}: HTTP {status} {A.short(body)}")
        else:
            want = {"page": 1, "size": 2, "total": 3, "pages": 2, "items": [ADA, GRACE]}
            got = {key: body.get(key) for key in want} if isinstance(body, dict) else body
            if status != 200 or got != want:
                wrong.append(f"{path}: HTTP {status} {A.short(got)}")
    for include in ("TEAM", "team,x", ""):
        status, body = A.get(base, f"/users?include={include}")
        if status != 200 or body != A.USERS:
            wrong.append(f"/users?include={include}: HTTP {status} {A.short(body)}")
    for path, expected in (("/users/1?include=team", ADA), ("/users/1?include=team,x", A.ADA)):
        status, body = A.get(base, path)
        if status != 200 or body != expected:
            wrong.append(f"{path}: HTTP {status} {A.short(body)}")
    return not wrong, "; ".join(wrong) or "team is opt-in on arrays, page items and by-id; other include values preserve the old shape"


CHECKS = {
    **A.CHECKS,
    "team-filter-exact": team_filter_exact,
    "team-filter-case-sensitive": team_filter_case_sensitive,
    "team-filters-combine-before-page": team_filters_combine_before_page,
    "team-include-opt-in": team_include_opt_in,
}
