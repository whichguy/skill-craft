"""Held-out acceptance for K3: team matching ignores case on listing and summary while preserving stored spelling."""
from __future__ import annotations

import importlib.util
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "shiploop_e2e_user_summary_accept", Path(__file__).with_name("user_summary_accept.py"))
S = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(S)

RETIRED_STRICT_IDS = {"team-filter-case-sensitive", "summary-team-case-sensitive"}


def team_filter_casefold_listing(base: str) -> tuple[bool, str]:
    return S.T.A.arrays(base, {"/users?team=engineering": [S.T.A.ADA, S.T.A.GRACE],
                               "/users?team=ENGINEERING": [S.T.A.ADA, S.T.A.GRACE]})


def summary_team_casefold(base: str) -> tuple[bool, str]:
    wrong = []
    for path in ("/users/summary?team=engineering", "/users/summary?team=ENGINEERING"):
        status, body = S.T.A.get(base, path)
        if status != 200 or not isinstance(body, dict) or body.get("total") != 2 or body.get("by_team") != {"Engineering": 2}:
            wrong.append(f"{path}: HTTP {status} {S.T.A.short(body)}")
    return not wrong, "; ".join(wrong) or "summary matches team names without regard to case"


def team_casefold_exact_match(base: str) -> tuple[bool, str]:
    wrong = []
    for path in ("/users?team=Eng", "/users/summary?team=Eng"):
        status, body = S.T.A.get(base, path)
        if path.startswith("/users/summary"):
            ok = (status == 200 and isinstance(body, dict) and body.get("total") == 0 and body.get("by_team") == {})
        else:
            ok = status == 200 and body == []
        if not ok:
            wrong.append(f"{path}: HTTP {status} {S.T.A.short(body)}")
    return not wrong, "; ".join(wrong) or "ignoring case still requires the exact team name"


def team_response_spelling_preserved(base: str) -> tuple[bool, str]:
    status, body = S.T.A.get(base, "/users?team=engineering&include=team")
    expected = [S.T.A.ADA, S.T.A.GRACE]
    expected = [{**user, "team": "Engineering"} for user in expected]
    ok = status == 200 and body == expected
    return ok, f"opt-in team spelling: HTTP {status} {S.T.A.short(body)}; expected stored spelling Engineering"


def summary_group_spelling_preserved(base: str) -> tuple[bool, str]:
    status, body = S.T.A.get(base, "/users/summary?team=ENGINEERING")
    ok = (status == 200 and isinstance(body, dict) and body.get("total") == 2
          and body.get("by_team") == {"Engineering": 2})
    return ok, f"summary spelling: HTTP {status} {S.T.A.short(body)}; expected by_team key Engineering"


CHECKS = {
    **{name: check for name, check in S.CHECKS.items() if name not in RETIRED_STRICT_IDS},
    "team-filter-casefold-listing": team_filter_casefold_listing,
    "summary-team-casefold": summary_team_casefold,
    "team-casefold-exact-match": team_casefold_exact_match,
    "team-response-spelling-preserved": team_response_spelling_preserved,
    "summary-group-spelling-preserved": summary_group_spelling_preserved,
}
