"""Held-out acceptance for K1 user-summary, which reuses the user-listing filters by explicit reference."""
from __future__ import annotations

import importlib.util
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "shiploop_e2e_user_teams_accept", Path(__file__).with_name("user_teams_accept.py"))
T = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(T)


def summary_total_by_team(base: str) -> tuple[bool, str]:
    status, body = T.A.get(base, "/users/summary")
    expected = {"Engineering": 2, "Support": 1}
    ok = (status == 200 and isinstance(body, dict) and body.get("total") == 3
          and body.get("by_team") == expected)
    return ok, f"/users/summary: HTTP {status} {T.A.short(body)}; expected total 3 and exact by_team counts"


def summary_uses_user_filters(base: str) -> tuple[bool, str]:
    probes = {
        "/users/summary?name=Grace": (1, {"Engineering": 1}),
        "/users/summary?team=Support": (1, {"Support": 1}),
        "/users/summary?name=Alan&team=Engineering": (0, {}),
    }
    wrong = []
    for path, (total, by_team) in probes.items():
        status, body = T.A.get(base, path)
        if status != 200 or not isinstance(body, dict) or body.get("total") != total or body.get("by_team") != by_team:
            wrong.append(f"{path}: HTTP {status} {T.A.short(body)}")
    return not wrong, "; ".join(wrong) or "summary applies the same name and exact team filters as the listing"


def summary_unpaginated_ignores(base: str) -> tuple[bool, str]:
    paths = ("/users/summary?page=2&size=1&include=team&sort=name",
             "/users/summary?page=bad&size=0")
    wrong = []
    for path in paths:
        status, body = T.A.get(base, path)
        if (status != 200 or not isinstance(body, dict) or body.get("total") != 3
                or body.get("by_team") != {"Engineering": 2, "Support": 1}):
            wrong.append(f"{path}: HTTP {status} {T.A.short(body)}")
    return not wrong, "; ".join(wrong) or "summary counts all matching users and ignores pagination and other query parameters"


def summary_no_matches(base: str) -> tuple[bool, str]:
    wrong = []
    for path in ("/users/summary?name=zzz", "/users/summary?team="):
        status, body = T.A.get(base, path)
        if status != 200 or not isinstance(body, dict) or body.get("total") != 0 or body.get("by_team") != {}:
            wrong.append(f"{path}: HTTP {status} {T.A.short(body)}")
    return not wrong, "; ".join(wrong) or "no matching users gives total 0 and an empty by_team"


def summary_team_case_sensitive(base: str) -> tuple[bool, str]:
    status, body = T.A.get(base, "/users/summary?team=engineering")
    ok = status == 200 and isinstance(body, dict) and body.get("total") == 0 and body.get("by_team") == {}
    return ok, f"lowercase exact team: HTTP {status} {T.A.short(body)}; expected no matches under the inherited rule"


CHECKS = {
    **T.CHECKS,
    "summary-total-by-team": summary_total_by_team,
    "summary-uses-user-filters": summary_uses_user_filters,
    "summary-unpaginated-ignores": summary_unpaginated_ignores,
    "summary-no-matches": summary_no_matches,
    "summary-team-case-sensitive": summary_team_case_sensitive,
}
