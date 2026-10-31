#!/usr/bin/env python3
"""Independently exercise the deployed Gym Salesforce Lightning UI.

The browser receives the Salesforce frontdoor URL and the initial self record
over stdin only. Receipts contain a closed projection of IDs, counts, statuses,
and hashes; raw Aura payloads, names, emails, headers, and login URLs stay in
memory.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import unittest
import uuid
from urllib.parse import urlparse


HERE = Path(__file__).resolve().parent
SHARED_BATTLESHIP_UI_PATH = HERE / "battleship_ui.py"
EXPECTED_ORG_ID = "00Daj000018BzO3EAK"
ALLOWED_METHODS = frozenset({
    "getMyMembership", "saveMyMembership", "setMyStatus", "adminSave",
    "listMembers", "member360", "checkIn",
})
REQUIRED_MUTATION_METHODS = frozenset({
    "saveMyMembership", "setMyStatus", "adminSave", "checkIn",
})
STATUSES = frozenset({"Active", "Frozen", "Cancelled"})
PLANS = frozenset({"Basic", "Coached"})
SAFE_STAGES = frozenset({
    "identity", "authenticate", "route", "render", "self-membership",
    "admin-member", "coaching", "status-refusal", "basic-checkin",
    "reload", "controller", "browser",
})
SAFE_REASONS = frozenset({
    "invalid-options", "duplicate-scope-option", "scope-invalid",
    "org-identity-mismatch", "developer-edition-mismatch",
    "current-user-not-admin", "self-record-invalid", "browser-unavailable",
    "browser-result-invalid", "controller-proof-missing",
    "controller-proof-invalid", "screenshot-missing", "journey-invalid",
    "database-state-mismatch", "evaluation-failed", "route-invalid",
    "aura-request-invalid", "controller-method-invalid",
    "controller-params-invalid", "controller-host-invalid",
    "controller-id-invalid", "controller-response-missing",
    "controller-response-id-mismatch", "controller-response-unsuccessful",
    "controller-response-invalid", "ui-control-missing", "ui-state-invalid",
    "ui-check-failed",
})
CHECK_PHASES = frozenset({"builder", "final", "product_at_stop", "unknown"})
ID_RE = re.compile(r"^[A-Za-z0-9]{15}(?:[A-Za-z0-9]{3})?$")
PREFIX_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,39}$")
ORG_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._@-]{0,79}$")


class CheckFailure(RuntimeError):
    """A failure whose only printable details are bounded stage and reason codes."""

    def __init__(self, stage: str, reason: str):
        self.stage = stage if stage in SAFE_STAGES else "browser"
        self.reason = reason if reason in SAFE_REASONS else "evaluation-failed"
        super().__init__(self.reason)


def load_shared_battleship_ui():
    """Load only the pinned-runtime and Salesforce CLI scaffolding by path."""
    path = SHARED_BATTLESHIP_UI_PATH
    if not path.is_file():
        raise CheckFailure("identity", "evaluation-failed")
    spec = importlib.util.spec_from_file_location("gym_battleship_ui_scaffolding", path)
    if spec is None or spec.loader is None:
        raise CheckFailure("identity", "evaluation-failed")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    required = ("command_path", "runtime_env", "sf_json", "org_identity",
                "frontdoor_url", "candidate_fingerprint")
    if any(not callable(getattr(module, name, None)) for name in required):
        raise CheckFailure("identity", "evaluation-failed")
    return module


def check_phase() -> str:
    phase = os.environ.get("E2E_CHECK_PHASE", "unknown")
    return phase if phase in CHECK_PHASES else "unknown"


def parse_scope(argv: list[str]) -> tuple[argparse.Namespace | None, list[str]]:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--org", required=True)
    parser.add_argument("--prefix", required=True)
    parser.add_argument("--final", action="store_true")
    parser.add_argument("--check-name")
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        return None, ["invalid-options"]
    org_flags = [arg for arg in argv if arg == "--org" or arg.startswith("--org=")]
    prefix_flags = [arg for arg in argv if arg == "--prefix" or arg.startswith("--prefix=")]
    final_flags = [arg for arg in argv if arg == "--final"]
    check_flags = [arg for arg in argv if arg == "--check-name" or arg.startswith("--check-name=")]
    if len(org_flags) != 1 or len(prefix_flags) != 1 or len(final_flags) > 1 or len(check_flags) > 1:
        return None, ["duplicate-scope-option"]
    if not ORG_RE.fullmatch(args.org) or not PREFIX_RE.fullmatch(args.prefix):
        return None, ["scope-invalid"]
    if args.check_name not in (None, "gym-ui"):
        return None, ["scope-invalid"]
    return args, []


def _soql_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'")


def _result_records(document: object) -> list[dict]:
    if not isinstance(document, dict):
        raise CheckFailure("identity", "evaluation-failed")
    if document.get("status") not in (0, None):
        raise CheckFailure("identity", "evaluation-failed")
    result = document.get("result")
    records = result.get("records") if isinstance(result, dict) else None
    if not isinstance(records, list) or any(not isinstance(row, dict) for row in records):
        raise CheckFailure("identity", "evaluation-failed")
    total_size = result.get("totalSize") if isinstance(result, dict) else None
    done = result.get("done") if isinstance(result, dict) else None
    if done is False or type(total_size) is not int or total_size != len(records):
        raise CheckFailure("identity", "evaluation-failed")
    return records


def _query(shared, org: str, query: str) -> list[dict]:
    try:
        document = shared.sf_json([
            "data", "query", "--query", query, "--target-org", org, "--json",
        ])
    except Exception as exc:
        raise CheckFailure("identity", "evaluation-failed") from exc
    return _result_records(document)


def _connected_username(shared, org: str) -> str:
    try:
        document = shared.sf_json(["org", "list", "--json"])
    except Exception as exc:
        raise CheckFailure("identity", "evaluation-failed") from exc
    result = document.get("result", {}) if isinstance(document, dict) else {}
    rows = []
    if isinstance(result, dict):
        for key in ("nonScratchOrgs", "scratchOrgs"):
            candidate = result.get(key)
            if isinstance(candidate, list):
                rows.extend(row for row in candidate if isinstance(row, dict))
    row = next((item for item in rows if item.get("alias") == org), None)
    username = row.get("username") if isinstance(row, dict) else None
    if not isinstance(username, str) or not username:
        raise CheckFailure("identity", "evaluation-failed")
    return username


def _current_user(shared, org: str) -> tuple[str, bool]:
    username = _connected_username(shared, org)
    rows = _query(shared, org,
                  "SELECT Id, Profile.PermissionsModifyAllData FROM User "
                  "WHERE Username = '%s' LIMIT 2" % _soql_escape(username))
    if len(rows) != 1:
        raise CheckFailure("identity", "current-user-not-admin")
    row = rows[0]
    profile = row.get("Profile")
    user_id = row.get("Id")
    is_admin = profile.get("PermissionsModifyAllData") if isinstance(profile, dict) else None
    if not isinstance(user_id, str) or not ID_RE.fullmatch(user_id) or is_admin is not True:
        raise CheckFailure("identity", "current-user-not-admin")
    return user_id, True


def _self_record(shared, org: str, prefix: str, user_id: str) -> dict | None:
    rows = _query(
        shared, org,
        "SELECT Id, FullName__c, Email__c, Goal__c, Plan__c, Status__c, LoginUserId__c "
        "FROM %sMember__c WHERE LoginUserId__c = '%s' LIMIT 2" %
        (prefix, _soql_escape(user_id)),
    )
    if len(rows) > 1:
        raise CheckFailure("identity", "self-record-invalid")
    if not rows:
        return None
    row = rows[0]
    if (not isinstance(row.get("Id"), str) or not ID_RE.fullmatch(row["Id"])
            or row.get("LoginUserId__c") != user_id
            or row.get("Status__c") not in STATUSES
            or row.get("Plan__c") not in PLANS):
        raise CheckFailure("identity", "self-record-invalid")
    return {key: row.get(key) for key in (
        "Id", "FullName__c", "Email__c", "Goal__c", "Plan__c", "Status__c", "LoginUserId__c",
    )}


def _organization_preflight(shared, org: str) -> dict:
    if org != "de":
        raise CheckFailure("identity", "org-identity-mismatch")
    try:
        identity = shared.org_identity(org)
    except Exception as exc:
        raise CheckFailure("identity", "evaluation-failed") from exc
    if not isinstance(identity, dict) or identity.get("org_id") != EXPECTED_ORG_ID:
        raise CheckFailure("identity", "org-identity-mismatch")
    host = identity.get("lightning_host")
    parsed = urlparse("https://" + str(host))
    if parsed.scheme != "https" or not parsed.hostname or not parsed.hostname.endswith(".lightning.force.com"):
        raise CheckFailure("identity", "org-identity-mismatch")
    rows = _query(shared, org, "SELECT Id, OrganizationType FROM Organization")
    if len(rows) != 1 or rows[0].get("Id") != EXPECTED_ORG_ID:
        raise CheckFailure("identity", "org-identity-mismatch")
    org_type = rows[0].get("OrganizationType")
    if not isinstance(org_type, str) or "developer edition" not in org_type.lower():
        raise CheckFailure("identity", "developer-edition-mismatch")
    return {"org_id": EXPECTED_ORG_ID, "lightning_host": parsed.hostname.lower()}


def _member_rows(shared, org: str, prefix: str, ids: list[str]) -> dict[str, dict]:
    if not ids or any(not isinstance(value, str) or not ID_RE.fullmatch(value) for value in ids):
        raise CheckFailure("reload", "database-state-mismatch")
    quoted = ",".join("'%s'" % _soql_escape(value) for value in sorted(set(ids)))
    rows = _query(
        shared, org,
        "SELECT Id, FullName__c, Email__c, Goal__c, Plan__c, Status__c, LoginUserId__c "
        "FROM %sMember__c WHERE Id IN (%s)" % (prefix, quoted),
    )
    return {row["Id"]: row for row in rows if isinstance(row.get("Id"), str)}


def _visit_rows(shared, org: str, prefix: str, ids: list[str]) -> dict[str, list[dict]]:
    if not ids or any(not isinstance(value, str) or not ID_RE.fullmatch(value) for value in ids):
        raise CheckFailure("reload", "database-state-mismatch")
    quoted = ",".join("'%s'" % _soql_escape(value) for value in sorted(set(ids)))
    rows = _query(
        shared, org,
        "SELECT Id, Member__c, CheckedInAt__c, Coaching__c "
        "FROM %sVisit__c WHERE Member__c IN (%s) ORDER BY CheckedInAt__c DESC, Id DESC" %
        (prefix, quoted),
    )
    result: dict[str, list[dict]] = {}
    for row in rows:
        member_id = row.get("Member__c")
        if isinstance(member_id, str):
            result.setdefault(member_id, []).append(row)
    return result


def _id(value: object) -> bool:
    return isinstance(value, str) and ID_RE.fullmatch(value) is not None


def _valid_call(call: object) -> bool:
    if not isinstance(call, dict):
        return False
    allowed_keys = {
        "request_number", "method", "request_id", "response_id", "response_state", "params_verified",
        "member_id", "status_value", "plan_value", "result_member_id",
        "result_status", "result_plan", "result_visit_count", "visit_id",
    }
    if set(call) - allowed_keys:
        return False
    if type(call.get("request_number")) is not int or call["request_number"] < 1:
        return False
    if call.get("member_id") is not None and not _id(call.get("member_id")):
        return False
    if call.get("result_member_id") is not None and not _id(call.get("result_member_id")):
        return False
    if call.get("visit_id") is not None and not _id(call.get("visit_id")):
        return False
    if call.get("status_value") is not None and (
        not isinstance(call.get("status_value"), str) or call.get("status_value") not in STATUSES
    ):
        return False
    if call.get("result_status") is not None and (
        not isinstance(call.get("result_status"), str) or call.get("result_status") not in STATUSES
    ):
        return False
    if call.get("plan_value") is not None and (
        not isinstance(call.get("plan_value"), str) or call.get("plan_value") not in PLANS
    ):
        return False
    if call.get("result_plan") is not None and (
        not isinstance(call.get("result_plan"), str) or call.get("result_plan") not in PLANS
    ):
        return False
    if call.get("result_visit_count") is not None and (
        type(call.get("result_visit_count")) is not int or call["result_visit_count"] < 0
    ):
        return False
    return (
        isinstance(call.get("method"), str)
        and call.get("method") in ALLOWED_METHODS
        and isinstance(call.get("request_id"), str)
        and re.fullmatch(r"[A-Za-z0-9._;:-]{1,128}", call["request_id"]) is not None
        and call.get("response_id") == call.get("request_id")
        and isinstance(call.get("response_state"), str)
        and call.get("response_state") in {"SUCCESS", "ERROR"}
        and call.get("params_verified") is True
        and (call.get("response_state") == "SUCCESS" or call.get("method") == "checkIn")
        and (call.get("response_state") != "SUCCESS"
             or call.get("method") in {"getMyMembership", "listMembers"}
             or _id(call.get("result_member_id")))
        and (call.get("method") != "checkIn" or call.get("response_state") != "SUCCESS"
             or (_id(call.get("visit_id")) and type(call.get("result_visit_count")) is int))
    )


def validate_browser_observation(value: object, *, expected_host: str, prefix: str) -> list[str]:
    """Require correlated mutation proof; cacheable reads are checked through visible UI and SOQL."""
    if (not isinstance(value, dict) or value.get("schema") != "shiploop-gym-ui-browser/1"
            or set(value) - {"schema", "route_host", "route_path", "browser_version", "journeys", "calls"}):
        return ["browser-result-invalid"]
    version = value.get("browser_version")
    if not isinstance(version, str) or len(version) > 100 or not re.fullmatch(r"[A-Za-z0-9 ._()/:-]*", version):
        return ["browser-result-invalid"]
    if value.get("route_host") != expected_host or value.get("route_path") != "/lightning/n/" + prefix + "_Members":
        return ["browser-result-invalid"]
    calls = value.get("calls")
    if not isinstance(calls, list) or not calls or not all(_valid_call(call) for call in calls):
        return ["controller-proof-missing"]
    calls_by_method: dict[str, list[dict]] = {}
    for call in calls:
        calls_by_method.setdefault(call["method"], []).append(call)
    if len({(call["request_number"], call["request_id"]) for call in calls}) != len(calls):
        return ["controller-proof-invalid"]
    if any(not calls_by_method.get(method) for method in REQUIRED_MUTATION_METHODS):
        return ["controller-proof-missing"]
    checkins = calls_by_method.get("checkIn", [])
    if (len(checkins) != 5
            or sum(c["response_state"] == "SUCCESS" for c in checkins) != 3
            or sum(c["response_state"] == "ERROR" for c in checkins) != 2
            or len(calls_by_method.get("saveMyMembership", [])) < 2):
        return ["controller-proof-invalid"]
    journeys = value.get("journeys")
    if not isinstance(journeys, dict):
        return ["journey-invalid"]
    self_journey = journeys.get("self")
    coached = journeys.get("coached")
    basic = journeys.get("basic")
    if not all(isinstance(item, dict) for item in (self_journey, coached, basic)):
        return ["journey-invalid"]
    allowed_journey_keys = {
        "self": {"member_id", "initial_status", "first_save_status", "frozen_status",
                 "frozen_edit_status", "resume_status", "reloaded_status",
                 "frozen_profile_edit_verified"},
        "coached": {"member_id", "plan_verified", "initial_visit_count", "first_visit_id",
                    "repeat_visit_id", "first_visit_count", "repeat_visit_count",
                    "coaching_contains_goal", "frozen_refused", "cancelled_refused",
                    "visits_after_frozen_refusal", "visits_after_cancelled_refusal",
                    "reloaded_status", "reloaded_visit_count"},
        "basic": {"member_id", "plan_verified", "visit_id", "visit_count",
                  "coaching_contains_independent_training", "reloaded_status",
                  "reloaded_visit_count"},
    }
    if (set(journeys) != set(allowed_journey_keys)
            or any(set(journeys[key]) - allowed for key, allowed in allowed_journey_keys.items())):
        return ["journey-invalid"]
    self_id = self_journey.get("member_id")
    coached_id = coached.get("member_id")
    basic_id = basic.get("member_id")
    if not all(_id(value) for value in (self_id, coached_id, basic_id)):
        return ["journey-invalid"]
    if len({self_id, coached_id, basic_id}) != 3:
        return ["journey-invalid"]
    coached_checks = [call for call in checkins if call.get("member_id") == coached_id]
    basic_checks = [call for call in checkins if call.get("member_id") == basic_id]
    if (sum(call["response_state"] == "SUCCESS" for call in coached_checks) != 2
            or sum(call["response_state"] == "ERROR" for call in coached_checks) != 2
            or sum(call["response_state"] == "SUCCESS" for call in basic_checks) != 1
            or any(call["response_state"] == "ERROR" for call in basic_checks)
            or any(call.get("result_member_id") != coached_id
                   for call in coached_checks if call["response_state"] == "SUCCESS")
            or any(call.get("result_visit_count") != 1
                   for call in coached_checks if call["response_state"] == "SUCCESS")
            or len({call.get("visit_id") for call in coached_checks
                    if call["response_state"] == "SUCCESS"}) != 1
            or any(call.get("result_member_id") != basic_id for call in basic_checks)
            or any(call.get("result_visit_count") != 1 for call in basic_checks)):
        return ["controller-proof-invalid"]
    self_status_calls = calls_by_method.get("setMyStatus", [])
    if (not any(call.get("status_value") == "Frozen" and call.get("result_status") == "Frozen"
                and call.get("result_member_id") == self_id for call in self_status_calls)
            or not any(call.get("status_value") == "Active" and call.get("result_status") == "Active"
                       and call.get("result_member_id") == self_id for call in self_status_calls)):
        return ["controller-proof-invalid"]
    coached_admin = [call for call in calls_by_method.get("adminSave", [])
                     if call.get("member_id") == coached_id]
    if ({call.get("status_value") for call in coached_admin} != {"Frozen", "Cancelled"}
            or any(call.get("result_member_id") != coached_id or call.get("result_status") != call.get("status_value")
                   for call in coached_admin)):
        return ["controller-proof-invalid"]
    if any(call.get("result_member_id") != call.get("member_id")
           for method in ("member360", "checkIn")
           for call in calls_by_method.get(method, [])
           if call["response_state"] == "SUCCESS"):
        return ["controller-proof-invalid"]
    if self_journey.get("first_save_status") != "Active":
        self_admin = [call for call in calls_by_method.get("adminSave", [])
                      if call.get("member_id") == self_id]
        if not any(call.get("status_value") == "Active" and call.get("result_status") == "Active"
                   and call.get("result_member_id") == self_id for call in self_admin):
            return ["controller-proof-invalid"]
    creates = {call.get("result_member_id") for call in calls_by_method.get("adminSave", [])
               if call.get("member_id") is None}
    if not {coached_id, basic_id}.issubset(creates):
        return ["controller-proof-invalid"]
    if (not _id(self_journey.get("member_id"))
            or self_journey.get("initial_status") not in (None, *STATUSES)
            or self_journey.get("first_save_status") not in STATUSES
            or self_journey.get("first_save_status") != (
                self_journey.get("initial_status") or "Active"
            )
            or self_journey.get("frozen_status") != "Frozen"
            or self_journey.get("frozen_edit_status") != "Frozen"
            or self_journey.get("resume_status") != "Active"
            or self_journey.get("reloaded_status") != "Active"
            or self_journey.get("frozen_profile_edit_verified") is not True):
        return ["journey-invalid"]
    if (not _id(coached.get("member_id"))
            or coached.get("plan_verified") is not True
            or coached.get("initial_visit_count") != 0
            or not _id(coached.get("first_visit_id"))
            or coached.get("first_visit_id") != coached.get("repeat_visit_id")
            or coached.get("first_visit_count") != 1
            or coached.get("repeat_visit_count") != 1
            or coached.get("coaching_contains_goal") is not True
            or coached.get("frozen_refused") is not True
            or coached.get("cancelled_refused") is not True
            or coached.get("visits_after_frozen_refusal") != 1
            or coached.get("visits_after_cancelled_refusal") != 1
            or coached.get("reloaded_status") != "Cancelled"
            or coached.get("reloaded_visit_count") != 1):
        return ["journey-invalid"]
    if (not _id(basic.get("member_id"))
            or basic.get("plan_verified") is not True
            or not _id(basic.get("visit_id"))
            or basic.get("visit_count") != 1
            or basic.get("coaching_contains_independent_training") is not True
            or basic.get("reloaded_status") != "Active"
            or basic.get("reloaded_visit_count") != 1):
        return ["journey-invalid"]
    return []


def _closed_browser_projection(observation: dict) -> tuple[dict, list[dict]]:
    journey_keys = {
        "self": ("member_id", "initial_status", "first_save_status", "frozen_status",
                 "frozen_edit_status", "resume_status", "reloaded_status",
                 "frozen_profile_edit_verified"),
        "coached": ("member_id", "plan_verified", "initial_visit_count", "first_visit_id",
                    "repeat_visit_id", "first_visit_count", "repeat_visit_count",
                    "coaching_contains_goal", "frozen_refused", "cancelled_refused",
                    "visits_after_frozen_refusal", "visits_after_cancelled_refusal",
                    "reloaded_status", "reloaded_visit_count"),
        "basic": ("member_id", "plan_verified", "visit_id", "visit_count",
                  "coaching_contains_independent_training", "reloaded_status",
                  "reloaded_visit_count"),
    }
    call_keys = (
        "request_number", "method", "request_id", "response_id", "response_state", "params_verified",
        "member_id", "status_value", "plan_value", "result_member_id",
        "result_status", "result_plan", "result_visit_count", "visit_id",
    )
    journeys = {
        name: {key: observation["journeys"][name][key] for key in keys}
        for name, keys in journey_keys.items()
    }
    calls = [{key: call[key] for key in call_keys if key in call}
             for call in observation["calls"]]
    return journeys, calls


def _validate_database(shared, org: str, prefix: str, user_id: str,
                       initial_self: dict | None, synthetic: dict,
                       observation: dict) -> dict:
    journeys = observation["journeys"]
    self_id = journeys["self"]["member_id"]
    coached_id = journeys["coached"]["member_id"]
    basic_id = journeys["basic"]["member_id"]
    if len({self_id, coached_id, basic_id}) != 3:
        raise CheckFailure("reload", "database-state-mismatch")
    members = _member_rows(shared, org, prefix, [self_id, coached_id, basic_id])
    if set(members) != {self_id, coached_id, basic_id}:
        raise CheckFailure("reload", "database-state-mismatch")
    self_row = members[self_id]
    coach_row = members[coached_id]
    basic_row = members[basic_id]
    current_self = _self_record(shared, org, prefix, user_id)
    if (current_self is None or current_self.get("Id") != self_id
            or self_row.get("LoginUserId__c") != user_id
            or self_row.get("FullName__c") != synthetic["self_final"]["fullName"]
            or self_row.get("Email__c") != synthetic["self_final"]["email"]
            or self_row.get("Goal__c") != synthetic["self_final"]["goal"]
            or self_row.get("Status__c") != "Active"
            or self_row.get("Plan__c") != synthetic["self_final"]["plan"]
            or (initial_self is not None and self_row.get("Id") != initial_self.get("Id"))):
        raise CheckFailure("reload", "database-state-mismatch")
    if (coach_row.get("LoginUserId__c") not in (None, "")
            or coach_row.get("FullName__c") != synthetic["coached"]["fullName"]
            or coach_row.get("Email__c") != synthetic["coached"]["email"]
            or coach_row.get("Goal__c") != synthetic["coached"]["goal"]
            or coach_row.get("Plan__c") != "Coached"
            or coach_row.get("Status__c") != "Cancelled"):
        raise CheckFailure("reload", "database-state-mismatch")
    if (basic_row.get("LoginUserId__c") not in (None, "")
            or basic_row.get("FullName__c") != synthetic["basic"]["fullName"]
            or basic_row.get("Email__c") != synthetic["basic"]["email"]
            or basic_row.get("Goal__c") != synthetic["basic"]["goal"]
            or basic_row.get("Plan__c") != "Basic"
            or basic_row.get("Status__c") != "Active"):
        raise CheckFailure("reload", "database-state-mismatch")

    visits = _visit_rows(shared, org, prefix, [self_id, coached_id, basic_id])
    coach_visits = visits.get(coached_id, [])
    basic_visits = visits.get(basic_id, [])
    if len(coach_visits) != 1 or len(basic_visits) != 1:
        raise CheckFailure("reload", "database-state-mismatch")
    coach_visit = coach_visits[0]
    basic_visit = basic_visits[0]
    if (coach_visit.get("Id") != journeys["coached"]["first_visit_id"]
            or coach_visit.get("Coaching__c") is None
            or synthetic["coached"]["goal"].lower() not in str(coach_visit.get("Coaching__c")).lower()
            or basic_visit.get("Id") != journeys["basic"]["visit_id"]
            or basic_visit.get("Coaching__c") is None
            or "independent training" not in str(basic_visit.get("Coaching__c")).lower()):
        raise CheckFailure("reload", "database-state-mismatch")
    if (journeys["coached"].get("reloaded_status") != coach_row.get("Status__c")
            or journeys["coached"].get("reloaded_visit_count") != len(coach_visits)
            or journeys["basic"].get("reloaded_status") != basic_row.get("Status__c")
            or journeys["basic"].get("reloaded_visit_count") != len(basic_visits)
            or journeys["coached"].get("first_visit_id") != coach_visit.get("Id")
            or journeys["basic"].get("visit_id") != basic_visit.get("Id")):
        raise CheckFailure("reload", "database-state-mismatch")
    return {
        "self_member_id": self_id,
        "self_status": self_row["Status__c"],
        "self_profile_verified": True,
        "self_plan_verified": self_row.get("Plan__c") == synthetic["self_final"]["plan"],
        "coached_member_id": coached_id,
        "coached_status": coach_row["Status__c"],
        "coached_profile_verified": True,
        "coached_visit_id": coach_visit["Id"],
        "coached_visit_count": len(coach_visits),
        "coached_plan_verified": coach_row["Plan__c"] == "Coached",
        "coached_stored_coaching_verified": True,
        "basic_member_id": basic_id,
        "basic_status": basic_row["Status__c"],
        "basic_profile_verified": True,
        "basic_visit_id": basic_visit["Id"],
        "basic_visit_count": len(basic_visits),
        "basic_plan_verified": basic_row["Plan__c"] == "Basic",
        "basic_stored_coaching_verified": True,
        "initial_self_present": initial_self is not None,
        "initial_self_status": initial_self.get("Status__c") if initial_self else None,
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _synthetic_profiles(nonce: str) -> dict:
    return {
        "self_first": {
            "fullName": "Gym Self " + nonce,
            "email": "self-" + nonce + "@example.invalid",
            "goal": "Mobility " + nonce,
            "plan": "Basic",
        },
        "self_final": {
            "fullName": "Gym Self Edited " + nonce,
            "email": "self-edited-" + nonce + "@example.invalid",
            "goal": "Strength " + nonce,
            "plan": "Coached",
        },
        "coached": {
            "fullName": "Gym Coached " + nonce,
            "email": "coached-" + nonce + "@example.invalid",
            "goal": "Strength " + nonce,
            "plan": "Coached",
        },
        "basic": {
            "fullName": "Gym Basic " + nonce,
            "email": "basic-" + nonce + "@example.invalid",
            "goal": "Mobility " + nonce,
            "plan": "Basic",
        },
    }


def _write_receipt(path: Path, platform_dir: Path, receipt: dict) -> tuple[str, str]:
    payload = (json.dumps(receipt, indent=2, sort_keys=True) + "\n").encode()
    path.write_bytes(payload)
    path.chmod(0o600)
    return path.relative_to(platform_dir).as_posix(), hashlib.sha256(payload).hexdigest()


def run_check(org: str, prefix: str, *, shared=None) -> int:
    phase = check_phase()
    platform_value = os.environ.get("E2E_PLATFORM_DIR")
    if not platform_value:
        print("gym-ui: FAIL (run-scoped platform directory unavailable)", file=sys.stderr)
        return 1
    platform_dir = Path(platform_value).resolve()
    evidence_dir = platform_dir / "gym-ui" / phase
    evidence_dir.mkdir(parents=True, exist_ok=True)
    check_id = uuid.uuid4().hex
    artifact_dir = evidence_dir / check_id
    artifact_dir.mkdir(mode=0o700, exist_ok=False)
    receipt_path = artifact_dir / "observation.json"
    started = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    failure: CheckFailure | None = None
    try:
        shared = shared if shared is not None else load_shared_battleship_ui()
        identity = _organization_preflight(shared, org)
        user_id, _ = _current_user(shared, org)
        initial_self = _self_record(shared, org, prefix, user_id)
        source_head, metadata_digest = shared.candidate_fingerprint(Path.cwd())
        login = shared.frontdoor_url(org)
        helper = HERE / "gym_ui_browser.cjs"
        node = shared.command_path("node")
        if not node or not helper.is_file():
            raise CheckFailure("browser", "browser-unavailable")
        screenshots = {
            name: artifact_dir / (name + ".png")
            for name in ("self", "self-frozen", "coached", "coached-frozen",
                         "coached-cancelled", "basic", "reload")
        }
        nonce = uuid.uuid4().hex[:12]
        synthetic = _synthetic_profiles(nonce)
        request = {
            "login_url": login,
            "prefix": prefix,
            "controller_class": prefix + "Controller",
            "expected_lightning_host": identity["lightning_host"],
            "initial_self": initial_self,
            "check_nonce": nonce,
            "synthetic": synthetic,
            "screenshots": {key: str(path) for key, path in screenshots.items()},
        }
        try:
            proc = subprocess.run(
                [node, str(helper)],
                input=json.dumps(request),
                capture_output=True,
                text=True,
                timeout=240,
                check=False,
                env=shared.runtime_env(),
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise CheckFailure("browser", "evaluation-failed") from exc
        if proc.returncode != 0:
            try:
                browser_failure = json.loads(proc.stdout)
            except (ValueError, TypeError):
                browser_failure = {}
            stage = browser_failure.get("stage") if isinstance(browser_failure, dict) else None
            reason = browser_failure.get("reason") if isinstance(browser_failure, dict) else None
            failure = CheckFailure(stage if stage in SAFE_STAGES else "browser",
                                   reason if reason in SAFE_REASONS else "evaluation-failed")
            raise failure
        try:
            observation = json.loads(proc.stdout)
        except (ValueError, TypeError) as exc:
            raise CheckFailure("browser", "browser-result-invalid") from exc
        errors = validate_browser_observation(
            observation, expected_host=identity["lightning_host"], prefix=prefix,
        )
        if errors:
            controller = errors[0] in {"controller-proof-missing", "controller-proof-invalid"}
            failure = CheckFailure("controller" if controller else "browser", errors[0])
            raise failure
        database_projection = _validate_database(
            shared, org, prefix, user_id, initial_self, synthetic, observation,
        )
        screenshot_hashes = {}
        for name, path in screenshots.items():
            if not path.is_file() or path.stat().st_size == 0:
                raise CheckFailure("browser", "screenshot-missing")
            screenshot_hashes[name] = {
                "path": path.relative_to(platform_dir).as_posix(),
                "sha256": _sha256(path),
            }
        safe_journeys, safe_calls = _closed_browser_projection(observation)
        receipt = {
            "schema": "shiploop-gym-ui-observation/1",
            "check_id": check_id,
            "run_scope": platform_dir.parent.name,
            "checked_at": started,
            "phase": phase,
            "org": identity,
            "prefix": prefix,
            "source_head": source_head,
            "candidate_metadata_sha256": metadata_digest,
            "status": "passed",
            "journeys": safe_journeys,
            "database": database_projection,
            "controller_calls": safe_calls,
            "screenshots": screenshot_hashes,
            "browser_version": observation.get("browser_version", ""),
        }
        receipt_rel, receipt_hash = _write_receipt(receipt_path, platform_dir, receipt)
        print("gym-ui: PASS (self profile, status preservation, check-in, and stored-record journeys verified)")
        print("gym-ui: receipt=%s sha256=%s" % (receipt_rel, receipt_hash))
        return 0
    except CheckFailure as exc:
        failure = exc
    except Exception:
        failure = CheckFailure("browser", "evaluation-failed")
    safe = {
        "schema": "shiploop-gym-ui-observation/1",
        "check_id": check_id,
        "run_scope": platform_dir.parent.name,
        "checked_at": started,
        "phase": phase,
        "status": "failed",
        "failure": {
            "stage": failure.stage if failure else "browser",
            "reason": failure.reason if failure else "evaluation-failed",
        },
    }
    receipt_rel, receipt_hash = _write_receipt(receipt_path, platform_dir, safe)
    print("gym-ui: FAIL (%s)" % safe["failure"]["reason"], file=sys.stderr)
    print("gym-ui: receipt=%s sha256=%s" % (receipt_rel, receipt_hash), file=sys.stderr)
    return 1


def main() -> int:
    args, errors = parse_scope(sys.argv[1:])
    if errors or args is None:
        print("gym-ui: invalid or duplicate org/prefix/check scope refused", file=sys.stderr)
        return 2

    class GymUiTest(unittest.TestCase):
        def test_independent_gym_ui_journeys(self):
            self.assertEqual(run_check(args.org, args.prefix), 0,
                             "The independent Gym UI check failed; see its bounded receipt.")

    result = unittest.TextTestRunner(verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(GymUiTest))
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
