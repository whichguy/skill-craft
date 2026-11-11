#!/usr/bin/env python3
"""Independently exercise the registered Grok chat Salesforce UI case.

The frontdoor URL is passed to the pinned Playwright helper over stdin only.
Receipts retain closed projections, action IDs, source/deployment identity,
independent database predicates, and screenshot hashes; they never retain chat
text, Notes values, Aura bodies, credentials, headers, or session URLs.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import secrets
import select
import subprocess
import sys
import time
import uuid
import xml.etree.ElementTree as ET


HERE = Path(__file__).resolve().parent
SHARED_UI_PATH = HERE / "battleship_ui.py"
GUARD_SPEC = importlib.util.spec_from_file_location("grok_chat_full_ui_sf_guard", HERE / "sf_guard.py")
assert GUARD_SPEC is not None and GUARD_SPEC.loader is not None
sf_guard = importlib.util.module_from_spec(GUARD_SPEC)
GUARD_SPEC.loader.exec_module(sf_guard)
EXPECTED_ORG = "de"
EXPECTED_ORG_ID = "00Daj000018BzO3EAK"
PREFIX = "SLGrokChat"
CONTROLLER = "SLGrokChatController"
ITEM_OBJECT = "SLGrokChatItem__c"
CONFIG_OBJECT = "SLGrokChatConfig__c"
NAMED_CREDENTIAL = "Grok_Chat_Model"
MODEL = "grok-4.7"
ALLOWED_METHODS = frozenset({
    "getSetup", "saveSetup", "testConnection", "newConversation",
    "getConversation", "sendMessage", "confirmAction", "cancelAction", "seedItems",
})
TURN_METHODS = frozenset({"sendMessage", "beginMessage", "executePendingMessage"})
OBSERVED_METHODS = ALLOWED_METHODS | TURN_METHODS
TURN_STEPS = ("read-tool", "create-proposal", "update-proposal", "cancel-proposal", "stale-proposal")
TURN_DIGEST_FIELDS = ("message_sha256", "client_request_id_sha256",
                      "issued_turn_token_sha256", "submitted_turn_token_sha256")
SAFE_STAGES = frozenset({
    "identity", "source", "deployment", "authenticate", "route", "render",
    "setup-missing", "setup-save", "connection", "seed", "read-tool",
    "create-proposal", "create-confirm", "update-proposal", "update-confirm",
    "cancel-proposal", "cancel-confirm", "stale-proposal", "stale-confirm",
    "reload", "viewport", "keyboard", "controller", "database", "observe", "browser",
})
SAFE_REASONS = frozenset({
    "invalid-options", "duplicate-mode-option", "mode-invalid", "phase-invalid",
    "platform-unavailable", "identity-mismatch", "admin-required", "source-invalid",
    "source-changed", "source-stale", "baseline-mismatch", "deployment-missing", "deployment-failed",
    "browser-unavailable", "browser-result-invalid", "route-invalid", "host-mismatch",
    "ui-control-missing", "ui-state-invalid", "keyboard-inaccessible", "layout-overflow",
    "setup-not-missing", "chat-attempted-before-setup", "setup-save-missing",
    "setup-readback-mismatch", "connection-failed", "conversation-missing", "seed-invalid",
    "read-tool-missing", "fake-prose-without-tool", "nonce-result-mismatch", "unsafe-text",
    "proposal-missing", "proposal-mismatch", "preconfirm-write", "write-missing",
    "extra-write", "cancel-mismatch", "stale-not-rejected", "replay-mismatch",
    "reload-mismatch", "controller-proof-missing", "controller-action-invalid",
    "controller-response-id-mismatch", "controller-response-invalid",
    "database-state-mismatch", "screenshot-missing", "browser-provider-call", "evaluation-failed",
})
PHASES = frozenset({"builder", "final"})
UI_ATTEMPT_LEDGER = "attempts.log"
UI_ATTEMPT_ID_RE = re.compile(r"[a-f0-9]{32}")
MODE_RE = re.compile(r"^(observe|run)$")
SF_ID_RE = re.compile(r"^[A-Za-z0-9]{15}(?:[A-Za-z0-9]{3})?$")
ACTION_ID_RE = re.compile(r"^[A-Za-z0-9._;:-]{1,128}$")
SHA256_RE = re.compile(r"^[a-f0-9]{64}$")
SERVER_REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,84}$")
# ECMAScript whitespace, matching cardText in the browser helper.
VISIBLE_WHITESPACE_RE = re.compile(r"[\t-\r \u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000\ufeff]+")
INVISIBLE_NAME_CHARS = str.maketrans("", "", "\u200b\u00ad")


class CheckFailure(RuntimeError):
    """Bounded public failure identifiers and a sanitized browser snapshot."""

    def __init__(self, stage: str, reason: str, browser_result: dict | None = None):
        self.stage = stage if stage in SAFE_STAGES else "browser"
        self.reason = reason if reason in SAFE_REASONS else "evaluation-failed"
        self.browser_result = _safe_browser_failure_result(browser_result or {})
        super().__init__(self.reason)


class _QuietArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError("invalid command options")


def load_shared_ui():
    path = SHARED_UI_PATH
    if not path.is_file():
        raise CheckFailure("identity", "browser-unavailable")
    spec = importlib.util.spec_from_file_location("grok_chat_battleship_ui_shared", path)
    if spec is None or spec.loader is None:
        raise CheckFailure("identity", "browser-unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    required = ("command_path", "runtime_env", "sf_json", "org_identity",
                "frontdoor_url", "candidate_fingerprint")
    if any(not callable(getattr(module, name, None)) for name in required):
        raise CheckFailure("identity", "browser-unavailable")
    return module


def check_phase() -> str:
    phase = os.environ.get("E2E_CHECK_PHASE", "unknown")
    return phase if phase in {"builder", "final", "product_at_stop", "unknown"} else "unknown"


def parse_options(argv: list[str]) -> tuple[argparse.Namespace | None, list[str]]:
    parser = _QuietArgumentParser(add_help=False)
    parser.add_argument("--mode", required=True, choices=("observe", "run"))
    try:
        args = parser.parse_args(argv)
    except (SystemExit, ValueError):
        return None, ["invalid-options"]
    mode_flags = [arg for arg in argv if arg == "--mode" or arg.startswith("--mode=")]
    if len(mode_flags) != 1:
        return None, ["duplicate-mode-option"]
    if not MODE_RE.fullmatch(args.mode):
        return None, ["mode-invalid"]
    return args, []


def _records(document: object) -> list[dict]:
    if not isinstance(document, dict) or document.get("status") not in (0, None):
        raise CheckFailure("database", "database-state-mismatch")
    result = document.get("result")
    if not isinstance(result, dict):
        raise CheckFailure("database", "database-state-mismatch")
    rows = result.get("records")
    if (not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows)
            or result.get("done") is False or type(result.get("totalSize")) is not int
            or result["totalSize"] != len(rows)):
        raise CheckFailure("database", "database-state-mismatch")
    return rows


def _soql_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'")


def _query(shared, query: str) -> list[dict]:
    try:
        document = shared.sf_json([
            "data", "query", "--query", query, "--target-org", EXPECTED_ORG, "--json",
        ])
    except Exception as exc:
        raise CheckFailure("database", "database-state-mismatch") from exc
    return _records(document)


def _current_user(shared) -> tuple[str, bool]:
    try:
        listing = shared.sf_json(["org", "list", "--json"])
    except Exception as exc:
        raise CheckFailure("identity", "identity-mismatch") from exc
    result = listing.get("result", {}) if isinstance(listing, dict) else {}
    rows = []
    if isinstance(result, dict):
        for key in ("nonScratchOrgs", "scratchOrgs"):
            value = result.get(key)
            if isinstance(value, list):
                rows.extend(row for row in value if isinstance(row, dict))
    org_row = next((row for row in rows if row.get("alias") == EXPECTED_ORG), None)
    username = org_row.get("username") if isinstance(org_row, dict) else None
    if not isinstance(username, str) or not username:
        raise CheckFailure("identity", "identity-mismatch")
    rows = _query(shared,
        "SELECT Id, Profile.PermissionsModifyAllData FROM User "
        "WHERE Username = '%s' LIMIT 2" % _soql_escape(username))
    if len(rows) != 1:
        raise CheckFailure("identity", "admin-required")
    row = rows[0]
    profile = row.get("Profile")
    user_id = row.get("Id")
    is_admin = profile.get("PermissionsModifyAllData") if isinstance(profile, dict) else None
    if not isinstance(user_id, str) or not SF_ID_RE.fullmatch(user_id):
        raise CheckFailure("identity", "identity-mismatch")
    return user_id, is_admin is True


def _is_deploy_start(row: object) -> bool:
    if (not isinstance(row, dict) or row.get("decision") != "allowed"
            or row.get("org") != EXPECTED_ORG or row.get("prefix") != PREFIX
            or not isinstance(row.get("call"), str)):
        return False
    argv = row.get("argv")
    if not isinstance(argv, list) or not all(isinstance(token, str) for token in argv):
        return False
    words, rest = sf_guard.command_words(argv)
    # Corroborated guard help cannot deploy. Keep later real starts in order,
    # even when unbound, partial, failed, open, or overlapping.
    return words == ("project", "deploy", "start") and not (
        row.get("reason") == "help" and any(token in sf_guard.HELP_FLAGS for token in rest)
    )


def _latest_successful_deploy(platform_dir: Path) -> dict | None:
    log = platform_dir / "sf-calls.jsonl"
    if not log.is_file():
        return None
    try:
        rows = [json.loads(line) for line in log.read_text(errors="replace").splitlines() if line.strip()]
    except (OSError, ValueError):
        return None
    starts = [row for row in rows if _is_deploy_start(row)]
    if not starts:
        return None
    row = starts[-1]
    end = next((item for item in rows if isinstance(item, dict)
                and item.get("end") is True and item.get("call") == row["call"]), None)
    if not isinstance(end, dict):
        return None
    deploy = {"call_id": row["call"], "started_at": row.get("ts"),
              "finished_at": end.get("ts"), "exit": end.get("exit"), "interrupted": end.get("interrupted")}
    binding = end.get("source_binding")
    if isinstance(binding, dict):
        deploy["source_binding"] = {key: binding.get(key) for key in (
            "root", "before_sha256", "after_sha256", "full_package", "unchanged",
        )}
    return deploy


def _candidate_identity(root: Path) -> tuple[str, str]:
    """Fingerprint every deployable source file, including ignored files."""
    try:
        digest = sf_guard.force_app_sha256(root)
        proc = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"],
                              stdin=subprocess.DEVNULL, capture_output=True, text=True,
                              timeout=5, check=True)
        head = proc.stdout.strip()
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        raise CheckFailure("source", "source-invalid") from exc
    if not re.fullmatch(r"[a-f0-9]{40,64}", head):
        raise CheckFailure("source", "source-invalid")
    return head, digest


def _source_is_fresh(root: Path, deploy: dict, metadata_sha256: str) -> bool:
    binding = deploy.get("source_binding")
    if not isinstance(binding, dict):
        return False
    try:
        resolved_root = str(root.resolve(strict=True))
    except (OSError, RuntimeError, ValueError):
        return False
    return (binding.get("root") == resolved_root and binding.get("full_package") is True
            and binding.get("unchanged") is True
            and binding.get("before_sha256") == binding.get("after_sha256") == metadata_sha256)


def _validate_app_tab(root: Path) -> None:
    """Bind the checker’s app host to the full case's declared tab and bundle."""
    base = root / "force-app" / "main" / "default"
    ns = "{http://soap.sforce.com/2006/04/metadata}"
    try:
        tab = ET.parse(base / "tabs" / "SLGrokChat_Chat.tab-meta.xml").getroot()
        bundle = ET.parse(base / "lwc" / "slGrokChatApp" / "slGrokChatApp.js-meta.xml").getroot()
    except (OSError, ET.ParseError) as exc:
        raise CheckFailure("source", "source-invalid") from exc
    components = [(node.text or "").strip() for node in tab.findall(ns + "lwcComponent")]
    targets = [(node.text or "").strip() for node in bundle.findall(f"{ns}targets/{ns}target")]
    if (tab.tag != ns + "CustomTab" or components != ["slGrokChatApp"]
            or bundle.tag != ns + "LightningComponentBundle"
            or bundle.findtext(ns + "isExposed", "").strip() not in {"true", "1"}
            or "lightning__Tab" not in targets):
        raise CheckFailure("source", "source-invalid")


def _config_rows(shared) -> list[dict]:
    return _query(shared,
        "SELECT Id, CreatedById, NamedCredential__c, Model__c FROM %sConfig__c LIMIT 50" % PREFIX)


def _validate_before_snapshot(platform_dir: Path, shared) -> str:
    path = platform_dir / "before.json"
    try:
        raw_snapshot = path.read_bytes()
        before = json.loads(raw_snapshot)
    except (OSError, ValueError):
        raise CheckFailure("identity", "baseline-mismatch")
    gym = before.get("gym") if isinstance(before, dict) else None
    if (not isinstance(before, dict) or before.get("org") != EXPECTED_ORG
            or before.get("prefix") != PREFIX or before.get("existing") == "update"
            or not isinstance(gym, dict) or gym.get("schema") != "shiploop-gym-snapshot/1"
            or gym.get("object_api_names") != [] or not isinstance(gym.get("fields"), list)):
        raise CheckFailure("identity", "baseline-mismatch")
    live_rows = _query(shared, "SELECT Id, OrganizationType, IsSandbox FROM Organization LIMIT 2")
    if len(live_rows) != 1:
        raise CheckFailure("identity", "baseline-mismatch")
    live_identity = {key: live_rows[0].get(key) for key in ("Id", "OrganizationType", "IsSandbox")}
    if gym.get("identity") != live_identity or live_identity.get("Id") != EXPECTED_ORG_ID:
        raise CheckFailure("identity", "baseline-mismatch")
    return hashlib.sha256(raw_snapshot).hexdigest()


def _reset_config(shared, user_id: str) -> int:
    rows = _config_rows(shared)
    if len(rows) > 20 or any(row.get("CreatedById") != user_id
                              or not isinstance(row.get("Id"), str)
                              or not SF_ID_RE.fullmatch(row["Id"]) for row in rows):
        raise CheckFailure("setup-missing", "database-state-mismatch")
    for row in rows:
        record_id = row.get("Id")
        try:
            shared.sf_json([
                "data", "delete", "record", "--sobject", CONFIG_OBJECT,
                "--record-id", record_id, "--target-org", EXPECTED_ORG, "--json",
            ])
        except Exception as exc:
            raise CheckFailure("setup-missing", "database-state-mismatch") from exc
    if _config_rows(shared):
        raise CheckFailure("setup-missing", "database-state-mismatch")
    return len(rows)


RESET_SCOPE = "current-user-created Grok Demo records only"
EMPTY_IDS_SHA256 = hashlib.sha256(b"").hexdigest()


def _reset_evidence() -> dict:
    return {"status": "not_run", "scope": RESET_SCOPE,
            "selected_count": 0, "selected_ids_sha256": EMPTY_IDS_SHA256,
            "deleted_count": 0, "deleted_ids_sha256": EMPTY_IDS_SHA256}


def _ids_digest(ids: list[str]) -> str:
    return hashlib.sha256("\n".join(sorted(ids)).encode()).hexdigest()


def _reset_synthetic_items(shared, user_id: str, evidence: dict) -> dict:
    """Retain bounded progress even if deletion or subsequent browser work fails."""
    evidence["status"] = "incomplete"
    rows = _items(shared, created_by=user_id)
    if len(rows) >= 501:
        raise CheckFailure("database", "seed-invalid")
    owned = []
    for row in rows:
        if not isinstance(row.get("Name"), str) or not row["Name"].startswith("Grok Demo "):
            continue
        if (not isinstance(row.get("Id"), str) or not SF_ID_RE.fullmatch(row["Id"])
                or row.get("CreatedById") != user_id):
            raise CheckFailure("database", "seed-invalid")
        owned.append(row)
    ids = sorted(row["Id"] for row in owned)
    evidence.update(selected_count=len(ids), selected_ids_sha256=_ids_digest(ids))
    deleted = []
    for record_id in ids:
        try:
            result = shared.sf_json(["data", "delete", "record", "--sobject", ITEM_OBJECT,
                                     "--record-id", record_id, "--target-org", EXPECTED_ORG, "--json"])
            if not isinstance(result, dict) or type(result.get("status")) is not int or result["status"] != 0:
                raise CheckFailure("database", "seed-invalid")
        except Exception as exc:
            raise CheckFailure("database", "seed-invalid") from exc
        deleted.append(record_id)
        evidence.update(deleted_count=len(deleted), deleted_ids_sha256=_ids_digest(deleted))
    readback = _items(shared, created_by=user_id)
    if len(readback) >= 501:
        raise CheckFailure("database", "seed-invalid")
    if any(isinstance(row.get("Name"), str) and row["Name"].startswith("Grok Demo ") for row in readback):
        raise CheckFailure("database", "seed-invalid")
    evidence["status"] = "complete"
    return evidence


def _valid_reset_evidence(reset: object) -> bool:
    if not isinstance(reset, dict) or set(reset) != set(_reset_evidence()):
        return False
    selected, deleted = reset["selected_count"], reset["deleted_count"]
    selected_digest, deleted_digest = reset["selected_ids_sha256"], reset["deleted_ids_sha256"]
    return (reset["status"] == "complete" and reset["scope"] == RESET_SCOPE
            and type(selected) is int and type(deleted) is int
            and 0 <= selected <= 500 and selected == deleted
            and isinstance(selected_digest, str) and isinstance(deleted_digest, str)
            and bool(SHA256_RE.fullmatch(selected_digest)) and bool(SHA256_RE.fullmatch(deleted_digest))
            and selected_digest == deleted_digest
            and (selected != 0 or selected_digest == EMPTY_IDS_SHA256))


def _verify_config(shared) -> bool:
    rows = _config_rows(shared)
    return len(rows) == 1 and rows[0].get("NamedCredential__c") == NAMED_CREDENTIAL \
        and rows[0].get("Model__c") == MODEL


def _items(shared, *, ids: list[str] | None = None, created_by: str | None = None) -> list[dict]:
    where = []
    if ids is not None:
        if not ids or any(not isinstance(value, str) or not SF_ID_RE.fullmatch(value) for value in ids):
            raise CheckFailure("database", "seed-invalid")
        where.append("Id IN (%s)" % ",".join("'%s'" % value for value in ids))
    if created_by is not None:
        if not SF_ID_RE.fullmatch(created_by):
            raise CheckFailure("database", "identity-mismatch")
        where.append("CreatedById = '%s'" % created_by)
    query = "SELECT Id, Name, Status__c, Notes__c, CreatedById FROM %s" % ITEM_OBJECT
    if where:
        query += " WHERE " + " AND ".join(where)
    query += " ORDER BY Id LIMIT 501"
    return _query(shared, query)


def _unique_visible_item_name(rows: list[dict], selected_id: str, selected_name: str) -> bool:
    def visible(value: str) -> str:
        return VISIBLE_WHITESPACE_RE.sub(" ", value.translate(INVISIBLE_NAME_CHARS)).strip(" ")

    expected = visible(selected_name)
    # _items uses a 501-row limit. A saturated snapshot cannot prove uniqueness.
    return len(rows) < 501 and bool(expected) and [
        row.get("Id") for row in rows
        if isinstance(row.get("Name"), str) and visible(row["Name"]) == expected
    ] == [selected_id]


def _set_item_notes(shared, record_id: str, value: str) -> None:
    safe_fixture_value = re.fullmatch(
        r"[A-Za-z0-9_-]{24,96}(?: <img src=x onerror=alert\(1\)>)?", value)
    if not SF_ID_RE.fullmatch(record_id) or not safe_fixture_value:
        raise CheckFailure("database", "database-state-mismatch")
    try:
        shared.sf_json([
            "data", "update", "record", "--sobject", ITEM_OBJECT,
            "--record-id", record_id, "--values", "Notes__c='" + value + "'",
            "--target-org", EXPECTED_ORG, "--json",
        ])
    except Exception as exc:
        raise CheckFailure("database", "database-state-mismatch") from exc


class BrowserWorker:
    """One authenticated browser page controlled by bounded newline JSON requests."""

    def __init__(self, shared):
        helper = HERE / "grok_chat_full_ui_browser.cjs"
        node = shared.command_path("node")
        if not node or not helper.is_file():
            raise CheckFailure("browser", "browser-unavailable")
        try:
            self.process = subprocess.Popen(
                [node, str(helper)], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL, text=True, bufsize=1, env=shared.runtime_env(),
            )
        except OSError as exc:
            raise CheckFailure("browser", "browser-unavailable") from exc
        self.sequence = 0
        self.closed = False

    def run(self, request: dict, *, timeout: int = 240) -> dict:
        if self.closed or self.process.poll() is not None or self.process.stdin is None \
                or self.process.stdout is None:
            raise CheckFailure("browser", "browser-result-invalid")
        self.sequence += 1
        ipc_id = str(self.sequence)
        # Give failure diagnostics the same deadline, with headroom for IPC delivery.
        request = {**request, "ipc_id": ipc_id,
                   "ipc_deadline_ms": int((time.time() + timeout) * 1000) - 250}
        try:
            self.process.stdin.write(json.dumps(request, separators=(",", ":")) + "\n")
            self.process.stdin.flush()
            ready, _, _ = select.select([self.process.stdout], [], [], timeout)
            if not ready:
                self.terminate()
                raise CheckFailure("browser", "evaluation-failed")
            line = self.process.stdout.readline()
            result = json.loads(line)
        except CheckFailure:
            raise
        except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
            self.terminate()
            raise CheckFailure("browser", "browser-result-invalid") from exc
        if not isinstance(result, dict) or result.get("ipc_id") != ipc_id:
            self.terminate()
            raise CheckFailure("browser", "browser-result-invalid")
        result.pop("ipc_id", None)
        if result.get("status") != "ok":
            stage, reason = result.get("stage"), result.get("reason")
            raise CheckFailure(stage if stage in SAFE_STAGES else "browser",
                               reason if reason in SAFE_REASONS else "evaluation-failed", result)
        return result

    def terminate(self) -> None:
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=5)

    def close(self) -> None:
        if self.closed:
            return
        self.closed = True
        try:
            if self.process.poll() is None and self.process.stdin is not None:
                self.process.stdin.write('{"close":true}\n')
                self.process.stdin.flush()
                self.process.stdin.close()
                self.process.wait(timeout=10)
        except (OSError, subprocess.TimeoutExpired):
            self.terminate()


def _start_browser(shared) -> BrowserWorker:
    return BrowserWorker(shared)


def _run_browser(worker: BrowserWorker, request: dict, *, timeout: int = 240) -> dict:
    return worker.run(request, timeout=timeout)


def _valid_call(value: object) -> bool:
    return (isinstance(value, dict) and isinstance(value.get("method"), str)
            and value["method"] in OBSERVED_METHODS
            and isinstance(value.get("request_id"), str)
            and ACTION_ID_RE.fullmatch(value["request_id"]) is not None
            and isinstance(value.get("response_id"), str)
            and ACTION_ID_RE.fullmatch(value["response_id"]) is not None
            and value.get("request_id") == value.get("response_id")
            and value.get("response_state") == "SUCCESS"
            and value.get("params_valid") is True and value.get("http_ok") is True
            and value.get("json_string_decoded_once") is True)


def _valid_digest(value: object) -> bool:
    return isinstance(value, str) and SHA256_RE.fullmatch(value) is not None


def _timed_call(call: dict) -> bool:
    start, end = call.get("request_started_at"), call.get("response_completed_at")
    return (type(start) in (int, float) and type(end) in (int, float)
            and 0 < start <= end < math.inf
            and isinstance(call.get("server_request_id"), str)
            and SERVER_REQUEST_ID_RE.fullmatch(call["server_request_id"]) is not None)


def _turn_execution_methods(value: dict, calls: list) -> list[str] | None:
    """Join the five render proofs to distinct, completed controller calls."""
    turns = value.get("chat_turns")
    conversation_id = value.get("conversation_id")
    action_ids = value.get("action_ids")
    if (not isinstance(turns, list) or len(turns) != len(TURN_STEPS)
            or not isinstance(conversation_id, str) or not SF_ID_RE.fullmatch(conversation_id)
            or not isinstance(action_ids, dict)):
        return None
    by_sequence = {}
    for call in calls:
        if not _valid_call(call):
            return None
        sequence = call.get("request_sequence")
        if type(sequence) is not int or sequence <= 0 or sequence in by_sequence:
            return None
        by_sequence[sequence] = call
    connection = [call for call in calls if call["method"] == "testConnection"]
    if (len(connection) != 1 or not _timed_call(connection[0])
            or connection[0].get("result_status") != "ok" or connection[0].get("ui_correlated") is not True):
        return None

    methods = ["testConnection"]
    used_sequences = set()
    execution_requests = {connection[0]["server_request_id"]}
    client_ids, tokens, messages = set(), set(), set()
    previous_step = connection[0]["request_sequence"]
    previous_count, previous_history = -1, None
    for step, turn in zip(TURN_STEPS, turns):
        if (not isinstance(turn, dict) or turn.get("step") != step
                or turn.get("conversation_id") != conversation_id
                or turn.get("rendered_history_matched") is not True):
            return None
        before, final = turn.get("before_message_count"), turn.get("final_message_count")
        before_digest, final_digest = turn.get("before_history_sha256"), turn.get("final_history_sha256")
        if (type(before) is not int or type(final) is not int or before < max(0, previous_count)
                or final < before + 2 or not _valid_digest(before_digest) or not _valid_digest(final_digest)
                or before_digest == final_digest or (before == previous_count and before_digest != previous_history)):
            return None
        previous_count, previous_history = final, final_digest
        execution = turn.get("execution_request_sequence")
        begin = turn.get("begin_request_sequence")
        if type(execution) is not int or execution <= previous_step or execution not in by_sequence:
            return None
        call = by_sequence[execution]
        if (call["method"] not in {"sendMessage", "executePendingMessage"}
                or call.get("result_status") != "ready" or not _timed_call(call)
                or call["server_request_id"] in execution_requests):
            return None
        execution_requests.add(call["server_request_id"])
        chain = [call]
        if call["method"] == "executePendingMessage":
            if type(begin) is not int or not previous_step < begin < execution or begin not in by_sequence:
                return None
            start = by_sequence[begin]
            token = start.get("issued_turn_token_sha256")
            client_id = start.get("client_request_id_sha256")
            if (start["method"] != "beginMessage" or start.get("result_status") != "working"
                    or start["request_id"] == call["request_id"] or not _valid_digest(token)
                    or token != call.get("submitted_turn_token_sha256") or token in tokens
                    or not _valid_digest(client_id) or client_id in client_ids
                    or not _timed_call(start) or not _timed_call(call)
                    or start["server_request_id"] == call["server_request_id"]
                    or start["response_completed_at"] > call["request_started_at"]):
                return None
            tokens.add(token)
            client_ids.add(client_id)
            chain.insert(0, start)
        elif begin is not None:
            return None
        message = chain[0].get("message_sha256")
        if (not _valid_digest(message) or message in messages
                or any(not _timed_call(entry) or entry.get("ui_correlated") is not True
                       or entry.get("request_conversation_id") != conversation_id
                       or entry.get("result_conversation_id") != conversation_id for entry in chain)):
            return None
        messages.add(message)
        action = turn.get("proposal_action_id")
        previous_step = execution
        if step == "read-tool":
            if action is not None:
                return None
        else:
            if not isinstance(action, str) or action != action_ids.get(step.removesuffix("-proposal")):
                return None
            mutations = [entry["request_sequence"] for entry in calls
                         if entry["method"] in ("confirmAction", "cancelAction")
                         and entry.get("card_action_id") == action]
            if not mutations or min(mutations) <= execution:
                return None
            previous_step = max(mutations)
        used_sequences.update(entry["request_sequence"] for entry in chain)
        if call["method"] not in methods:
            methods.append(call["method"])
    if used_sequences != {seq for seq, call in by_sequence.items() if call["method"] in TURN_METHODS}:
        return None
    return methods


def validate_observation(value: object, *, mode: str, phase: str, expected_host: str,
                         source_head: str, metadata_sha256: str) -> list[str]:
    """Validate a closed browser/database projection; never accept UI prose alone."""
    if not isinstance(value, dict):
        return ["browser-result-invalid"]
    errors: list[str] = []
    if value.get("schema") != "shiploop-grok-chat-full-ui-observation/1":
        errors.append("browser-result-invalid")
    if value.get("mode") != mode or value.get("phase") != phase:
        errors.append("browser-result-invalid")
    if value.get("ui_attempted_first") is not True:
        errors.append("identity-mismatch")
    if type(value.get("auth_required")) is not bool or value.get("auth_used") != value.get("auth_required"):
        errors.append("identity-mismatch")
    if value.get("route_host") != expected_host:
        errors.append("host-mismatch")
    if value.get("route_path") != "/lightning/n/SLGrokChat_Chat":
        errors.append("route-invalid")
    if value.get("source_head") != source_head or value.get("candidate_metadata_sha256") != metadata_sha256:
        errors.append("source-stale")
    if not isinstance(value.get("browser_version"), str) or not value["browser_version"].strip():
        errors.append("browser-result-invalid")
    calls = value.get("controller_calls")
    if not isinstance(calls, list) or not calls:
        errors.append("controller-proof-missing")
        calls = []
    elif any(not _valid_call(call) for call in calls):
        errors.append("controller-response-id-mismatch" if any(
            isinstance(call, dict) and call.get("request_id") != call.get("response_id") for call in calls
        ) else "controller-response-invalid")
    if mode == "observe":
        if (value.get("status") != "observed" or value.get("evidence_scope") != "ui-exploration"
                or value.get("acceptance_bound") is not False
                or value.get("source_deployment_bound") is not False):
            errors.append("browser-result-invalid")
        if value.get("observed_setup_status") not in ("missing", "ready", "error"):
            errors.append("ui-state-invalid")
        if value.get("screenshots") != 1:
            errors.append("screenshot-missing")
        return list(dict.fromkeys(errors))

    needed_methods = ALLOWED_METHODS - {"sendMessage"}
    method_names = {call["method"] for call in calls if _valid_call(call)}
    if not needed_methods.issubset(method_names):
        errors.append("controller-proof-missing")
    if not _valid_reset_evidence(value.get("synthetic_fixture_reset")):
        errors.append("seed-invalid")
    mutation_calls = [call for call in calls if isinstance(call, dict)
                      and call.get("method") in ("confirmAction", "cancelAction")]
    if any(call.get("ui_correlated") is not True or call.get("card_action_id") != call.get("action_id")
           or call.get("request_action_id") != call.get("action_id") for call in mutation_calls):
        errors.append("controller-proof-missing")
    confirm_calls = [call for call in mutation_calls if call.get("method") == "confirmAction"]
    cancel_calls = [call for call in mutation_calls if call.get("method") == "cancelAction"]
    action_ids = value.get("action_ids")
    if (not isinstance(action_ids, dict)
            or set(action_ids) != {"create", "update", "cancel", "stale"}
            or any(not isinstance(action_ids.get(key), str) or not ACTION_ID_RE.fullmatch(action_ids[key])
                   for key in ("create", "update", "cancel", "stale"))
            or len(set(action_ids.values())) != 4):
        errors.append("controller-proof-missing")
        action_ids = {}
    expected_counts = {action_ids.get("create"): (1, 2), action_ids.get("update"): (1,), action_ids.get("stale"): (1,)}
    if len(expected_counts) != 3:
        errors.append("controller-proof-missing")
    actual_counts = {}
    for call in confirm_calls:
        action_id = call.get("action_id")
        if isinstance(action_id, str):
            actual_counts[action_id] = actual_counts.get(action_id, 0) + 1
    by_action = {action_id: [call for call in confirm_calls if call.get("action_id") == action_id]
                 for action_id in expected_counts}
    create_results = by_action.get(action_ids.get("create"), [])
    update_results = by_action.get(action_ids.get("update"), [])
    stale_results = by_action.get(action_ids.get("stale"), [])
    if (len(confirm_calls) not in {3, 4} or len(cancel_calls) != 1
            or not all(isinstance(call.get("action_id"), str) for call in mutation_calls)
            or any(actual_counts.get(action_id, 0) not in allowed for action_id, allowed in expected_counts.items())
            or not create_results or create_results[0].get("result_status") != "applied"
            or any(call.get("result_status") not in ("applied", "rejected")
                   or call.get("result_operation") != "create" for call in create_results)
            or len(update_results) != 1 or update_results[0].get("result_status") != "applied"
            or update_results[0].get("result_operation") != "update"
            or len(stale_results) != 1 or stale_results[0].get("result_status") != "stale"
            or stale_results[0].get("result_operation") != "update"
            or cancel_calls[0].get("action_id") != action_ids.get("cancel")
            or cancel_calls[0].get("result_status") != "cancelled"
            or value.get("duplicate_attempted") is not True
            or value.get("duplicate_delivery_count") != len(create_results)):
        errors.append("replay-mismatch")
    execution_methods = _turn_execution_methods(value, calls)
    if execution_methods is None or value.get("live_callout_methods") != execution_methods:
        errors.append("controller-proof-missing")
    if value.get("setup_missing_without_chat_attempt") is not True:
        errors.append("chat-attempted-before-setup")
    if value.get("setup_business_unchanged") is not True:
        errors.append("extra-write")
    if value.get("config_readback_match") is not True:
        errors.append("setup-readback-mismatch")
    if value.get("connection_ok") is not True or value.get("recheck_ready") is not True:
        errors.append("connection-failed")
    if value.get("read_tool_proof") != {
        "find_items": True, "read_item": True, "result_matches_nonce": True,
        "assistant_used_result": True, "conversation_persisted": True,
        "prompt_excluded_nonce": True,
        "unsafe_markup_is_text": True,
    }:
        errors.append("fake-prose-without-tool")
    for key in ("create_proposal_exact", "create_preconfirm_absent", "create_one_write",
                "update_proposal_exact", "update_preconfirm_unchanged", "update_one_write",
                "cancel_proposal_exact", "cancelled_absent", "stale_proposal_exact",
                "stale_rejected", "stale_external_value_preserved", "duplicate_safe",
                "reload_history_persisted", "new_conversation", "desktop_layout_ok",
                "narrow_layout_ok", "keyboard_ok", "safe_text_ok"):
        if value.get(key) is not True:
            reason = {
                "create_proposal_exact": "proposal-mismatch", "update_proposal_exact": "proposal-mismatch",
                "cancel_proposal_exact": "proposal-mismatch", "stale_proposal_exact": "proposal-mismatch",
                "create_preconfirm_absent": "preconfirm-write", "update_preconfirm_unchanged": "preconfirm-write",
                "create_one_write": "write-missing", "update_one_write": "write-missing",
                "cancelled_absent": "cancel-mismatch", "stale_rejected": "stale-not-rejected",
                "stale_external_value_preserved": "extra-write", "duplicate_safe": "replay-mismatch",
                "reload_history_persisted": "reload-mismatch", "desktop_layout_ok": "layout-overflow",
                "narrow_layout_ok": "layout-overflow", "keyboard_ok": "keyboard-inaccessible",
                "safe_text_ok": "unsafe-text",
            }.get(key, "ui-state-invalid")
            errors.append(reason)
    if value.get("extra_write_count") != 0 or value.get("business_write_count") != 2:
        errors.append("extra-write" if value.get("extra_write_count", 0) else "write-missing")
    if value.get("screenshots") != 5:
        errors.append("screenshot-missing")
    return list(dict.fromkeys(errors))


def _screen_receipts(paths: dict[str, Path], platform_dir: Path) -> dict:
    result = {}
    for name, path in paths.items():
        try:
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError as exc:
            raise CheckFailure("browser", "screenshot-missing") from exc
        result[name] = {"path": path.relative_to(platform_dir).as_posix(), "sha256": digest}
    return result


DIAGNOSTIC_BRANCHES = frozenset({
    "step-failure", "request-validation", "request-host", "request-cancelled", "request-network-failure",
    "response-host", "http-non-2xx", "response-body-read", "response-body-decode", "response-pairing",
    "response-wrapper", "response-state", "response-value-type", "response-schema", "response-identity",
    "response-server-id", "response-lifecycle",
})
BROWSER_STEPS = frozenset({"attempt", "authenticate", "observe", "setup", "seed", *TURN_STEPS,
                           "create-confirm", "update-confirm", "cancel-confirm", "stale-confirm"})


def _safe_browser_failure_result(result: dict) -> dict:
    # Failed IPC is evidence, not trusted free-form error output. Whitelist both
    # keys and values before attaching it to an exception or durable receipt.
    diagnostic = result.get("browser_failure")
    safe = {}
    if isinstance(diagnostic, dict):
        for key, allowed in (("step", BROWSER_STEPS), ("branch", DIAGNOSTIC_BRANCHES),
                             ("method", OBSERVED_METHODS), ("drain_state", {"complete", "incomplete"})):
            value = diagnostic.get(key)
            if isinstance(value, str) and value in allowed:
                safe[key] = value
        for key, upper in (("request_sequence", 1000000), ("batch", 1000000),
                           ("request_count", 10000), ("http_status", 599)):
            value = diagnostic.get(key)
            if type(value) is int and (100 if key == "http_status" else 1) <= value <= upper:
                safe[key] = value
        for key in ("pending_jobs", "unresolved_requests"):
            value = diagnostic.get(key)
            if type(value) is int and 0 <= value <= 10000:
                safe[key] = value
        ipc_id = diagnostic.get("ipc_id")
        if isinstance(ipc_id, str) and re.fullmatch(r"[0-9]{1,8}", ipc_id):
            safe["ipc_id"] = ipc_id
        value = diagnostic.get("request_id")
        if isinstance(value, str) and ACTION_ID_RE.fullmatch(value):
            safe["request_id"] = value
    return {"controller_calls": _safe_controller_projection([result]), "browser_failure": safe}


def _safe_call_fields(call: dict) -> dict:
    enums = {
        "method": OBSERVED_METHODS, "response_state": {"PENDING", "SUCCESS", "ERROR", "CONFLICT"},
        "result_status": {"missing", "ready", "error", "ok", "working", "applied", "stale",
                          "rejected", "failed", "cancelled"},
        "result_operation": {"create", "update"},
        "request_lifecycle": {"dispatched", "response", "finished", "failed"},
    }
    safe = {}
    for key, value in call.items():
        if key in enums:
            if isinstance(value, str) and value in enums[key]:
                safe[key] = value
        elif key in {"request_id", "response_id", "action_id", "request_action_id", "card_action_id"}:
            if value is None or isinstance(value, str) and ACTION_ID_RE.fullmatch(value):
                safe[key] = value
        elif key in {"result_record_id", "result_conversation_id", "request_conversation_id"}:
            if isinstance(value, str) and SF_ID_RE.fullmatch(value):
                safe[key] = value
        elif key in {"params_valid", "http_ok", "json_string_decoded_once", "ui_correlated"}:
            if type(value) is bool:
                safe[key] = value
        elif key in {"request_sequence", "http_status"}:
            if type(value) is int and 1 <= value <= (599 if key == "http_status" else 1000000):
                safe[key] = value
        elif key in {"request_started_at", "response_completed_at"}:
            if type(value) in (float, int) and 0 < value < 1e15:
                safe[key] = value
        elif key in TURN_DIGEST_FIELDS and _valid_digest(value):
            safe[key] = value
        elif key == "server_request_id" and isinstance(value, str) and SERVER_REQUEST_ID_RE.fullmatch(value):
            safe[key] = value
    return safe


def _safe_controller_projection(results: list[dict]) -> list[dict]:
    calls = {}
    for result in results:
        rows = result.get("controller_calls", [])
        if not isinstance(rows, list):
            continue
        for call in rows:
            if not isinstance(call, dict):
                continue
            call = _safe_call_fields(call)
            sequence = call.get("request_sequence")
            sequence = sequence if type(sequence) is int and sequence > 0 else None
            key = ("sequence", sequence) if sequence is not None else (
                "legacy", call.get("request_id"), call.get("method"))
            projected = {name: call.get(name) for name in (
                "method", "request_sequence", "request_id", "response_id", "response_state", "params_valid",
                "http_ok", "json_string_decoded_once", "result_status", "result_operation", "result_record_id",
                "result_conversation_id", "request_conversation_id", "action_id", "request_action_id",
                "card_action_id", "ui_correlated", "request_started_at", "response_completed_at",
                "http_status", "request_lifecycle",
            ) if name in call}
            projected.update({name: call[name] for name in TURN_DIGEST_FIELDS
                              if _valid_digest(call.get(name))})
            server_id = call.get("server_request_id")
            if isinstance(server_id, str) and SERVER_REQUEST_ID_RE.fullmatch(server_id):
                projected["server_request_id"] = server_id
            previous = calls.get(key)
            if previous is not None:
                # Cumulative snapshots may add UI correlation, but must not revise
                # a completed response. Retain a conflict as non-passing evidence.
                stable = lambda value: {k: v for k, v in value.items()
                                        if k not in {"ui_correlated", "card_action_id", "request_lifecycle"}}
                changed_request = any(previous.get(k) != projected.get(k) for k in (
                    "method", "request_id", "request_sequence", "params_valid", "request_conversation_id",
                    "request_action_id", "message_sha256", "client_request_id_sha256", "submitted_turn_token_sha256"))
                previous_card = previous.get("card_action_id")
                if previous_card is not None:
                    changed_request |= projected.get("card_action_id", previous_card) != previous_card
                    projected["card_action_id"] = previous_card
                changed_response = (previous.get("response_state") != "PENDING"
                                    and stable(previous) != stable(projected))
                if changed_request or changed_response:
                    projected["response_state"] = "CONFLICT"
                projected["ui_correlated"] = (previous.get("ui_correlated") is True
                                                or projected.get("ui_correlated") is True)
            # A request can be pending in the route snapshot and complete later.
            # Response ID belongs to its outcome, not to the request identity.
            calls[key] = projected
    return list(calls.values())


def _safe_chat_turn_projection(result: dict) -> dict:
    turn = result.get("chat_turn")
    if not isinstance(turn, dict):
        return {}
    projected = {key: turn.get(key) for key in (
        "step", "conversation_id", "proposal_action_id", "execution_request_sequence",
        "begin_request_sequence", "before_message_count", "final_message_count", "rendered_history_matched",
    )}
    projected.update({key: turn[key] for key in ("before_history_sha256", "final_history_sha256")
                      if _valid_digest(turn.get(key))})
    return projected


def _action_calls(result: dict, action_id: str) -> list[dict]:
    calls = result.get("controller_calls")
    if not isinstance(calls, list):
        return []
    return [call for call in calls if isinstance(call, dict)
            and call.get("method") == "confirmAction" and call.get("action_id") == action_id]


def _write_receipt(path: Path, platform_dir: Path, receipt: dict) -> tuple[str, str]:
    payload = (json.dumps(receipt, indent=2, sort_keys=True) + "\n").encode()
    path.write_bytes(payload)
    path.chmod(0o600)
    return path.relative_to(platform_dir).as_posix(), hashlib.sha256(payload).hexdigest()


def _request(mode: str, step: str, login_url: str | None, identity: dict, source_head: str,
             metadata_sha256: str, screenshots: dict[str, Path], **fields) -> dict:
    request = {
        "mode": mode, "step": step, "phase": check_phase(), "login_url": login_url,
        "expected_lightning_host": identity["lightning_host"],
        "controller_class": CONTROLLER, "prefix": PREFIX,
        "source_head": source_head, "candidate_metadata_sha256": metadata_sha256,
        "screenshots": {key: str(path) for key, path in screenshots.items()},
        **fields,
    }
    if login_url is None:
        request.pop("login_url")
    return request


def register_ui_attempt(platform_dir: Path, phase: str, check_id: str) -> Path:
    attempts = platform_dir / "grok-chat-ui" / phase
    attempts.mkdir(parents=True, mode=0o700, exist_ok=True)
    artifact_dir = attempts / check_id
    with (attempts / UI_ATTEMPT_LEDGER).open("a", encoding="ascii") as ledger:
        fcntl.flock(ledger, fcntl.LOCK_EX)
        if artifact_dir.exists():
            raise FileExistsError(artifact_dir)
        # The append is the start order. A process that stops after it still
        # supersedes earlier attempts, even without an artifact directory.
        ledger.write(check_id + "\n")
        ledger.flush()
        artifact_dir.mkdir(mode=0o700)
    return artifact_dir


def run_check(mode: str) -> int:
    if mode not in {"observe", "run"}:
        print("grok-chat-ui: invalid mode refused", file=sys.stderr)
        return 2
    phase = check_phase()
    if phase not in PHASES:
        print("grok-chat-ui: FAIL (phase not allowed)", file=sys.stderr)
        return 1
    platform_value = os.environ.get("E2E_PLATFORM_DIR")
    if not platform_value:
        print("grok-chat-ui: FAIL (run-scoped platform directory unavailable)", file=sys.stderr)
        return 1
    platform_dir = Path(platform_value).resolve()
    try:
        artifact_dir = register_ui_attempt(platform_dir, phase, uuid.uuid4().hex)
    except OSError:
        print("grok-chat-ui: FAIL (attempt registration unavailable)", file=sys.stderr)
        return 1
    receipt_path = artifact_dir / "observation.json"
    started = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    failure: CheckFailure | None = None
    browser_results: list[dict] = []
    screenshots = {
        "setup-missing": artifact_dir / "setup-missing.png",
        "setup-desktop": artifact_dir / "setup-desktop.png",
        "setup-narrow": artifact_dir / "setup-narrow.png",
        "pending-desktop": artifact_dir / "pending-desktop.png",
        "chat-narrow": artifact_dir / "chat-narrow.png",
    }
    source_head = None
    metadata_sha256 = None
    deployment = None
    auth_used = False
    identity = None
    browser_worker = None
    item_reset = _reset_evidence()
    try:
        shared = load_shared_ui()
        identity = shared.org_identity(EXPECTED_ORG)
        if identity.get("org_id") != EXPECTED_ORG_ID:
            raise CheckFailure("identity", "identity-mismatch")
        user_id, is_admin = _current_user(shared)
        if not is_admin:
            raise CheckFailure("identity", "admin-required")
        try:
            source_head, metadata_sha256 = _candidate_identity(Path.cwd())
        except Exception as exc:
            raise CheckFailure("source", "source-invalid") from exc
        if not isinstance(metadata_sha256, str) or not SHA256_RE.fullmatch(metadata_sha256):
            raise CheckFailure("source", "source-invalid")
        deployment = _latest_successful_deploy(platform_dir)
        if mode == "run":
            if not deployment:
                raise CheckFailure("deployment", "deployment-missing")
            if (type(deployment.get("exit")) is not int or deployment.get("exit") != 0
                    or deployment.get("interrupted") is not False):
                raise CheckFailure("deployment", "deployment-failed")
            if not _source_is_fresh(Path.cwd(), deployment, metadata_sha256):
                raise CheckFailure("source", "source-stale")
            _validate_before_snapshot(platform_dir, shared)
            _reset_synthetic_items(shared, user_id, item_reset)
            # Capture before opening the app: setup and connection must not silently
            # seed business data, even when later explicit seeding succeeds.
            pre_setup_items = _items(shared)
            if len(pre_setup_items) > 500:
                raise CheckFailure("database", "database-state-mismatch")
            cleared_configs = 0
        else:
            cleared_configs = 0
        browser_worker = _start_browser(shared)
        attempt = _run_browser(browser_worker, _request(
            mode, "attempt", None, identity, source_head or "", metadata_sha256, screenshots,
        ))
        browser_results.append(attempt)
        if attempt.get("ui_attempted_first") is not True or type(attempt.get("auth_required")) is not bool:
            raise CheckFailure("route", "browser-result-invalid")
        if attempt.get("auth_required") is True:
            login = shared.frontdoor_url(EXPECTED_ORG)
            authenticated = _run_browser(browser_worker, _request(
                mode, "authenticate", login, identity, source_head or "", metadata_sha256, screenshots,
            ), timeout=120)
            browser_results.append(authenticated)
            if authenticated.get("authenticated") is not True:
                raise CheckFailure("authenticate", "identity-mismatch")
            auth_used = True
            login = None
        else:
            login = None
        if mode == "run":
            _validate_app_tab(Path.cwd())
            cleared_configs = _reset_config(shared, user_id)
        if mode == "observe":
            result = _run_browser(browser_worker, _request(
                mode, "observe", login, identity, source_head or "", metadata_sha256,
                {"setup-desktop": screenshots["setup-desktop"]},
            ))
            browser_results.append(result)
            receipt_data = {
                "schema": "shiploop-grok-chat-full-ui-observation/1", "check_id": artifact_dir.name,
                "checked_at": started, "phase": phase, "mode": mode, "status": "observed",
                "evidence_scope": "ui-exploration", "acceptance_bound": False,
                "source_deployment_bound": False,
                "org": {"org_id": identity["org_id"], "lightning_host": identity["lightning_host"]},
                "source_head": source_head, "candidate_metadata_sha256": metadata_sha256,
                "deployment": deployment, "observed_setup_status": result.get("observed_setup_status"),
                "route_host": result.get("route_host"), "route_path": result.get("route_path"),
                "browser_version": result.get("browser_version"),
                "ui_attempted_first": attempt.get("ui_attempted_first"),
                "auth_required": attempt.get("auth_required"), "auth_used": auth_used,
                "controller_calls": _safe_controller_projection(browser_results),
                "screenshots": 1,
            }
            errors = validate_observation(receipt_data, mode=mode, phase=phase,
                expected_host=identity["lightning_host"], source_head=source_head or "",
                metadata_sha256=metadata_sha256)
            if errors:
                raise CheckFailure("observe", errors[0])
        else:
            run_id = secrets.token_hex(6)
            nonce = secrets.token_urlsafe(27)
            note_payload = nonce + " <img src=x onerror=alert(1)>"
            common = {"run_id": run_id, "model": MODEL, "named_credential": NAMED_CREDENTIAL}
            setup = _run_browser(browser_worker, _request(
                mode, "setup", login, identity, source_head or "", metadata_sha256, screenshots,
                **common,
            ), timeout=240)
            browser_results.append(setup)
            if not _verify_config(shared):
                raise CheckFailure("setup-save", "setup-readback-mismatch")
            if not _same_items(pre_setup_items, _items(shared)):
                raise CheckFailure("setup-save", "extra-write")
            seed = _run_browser(browser_worker, _request(
                mode, "seed", login, identity, source_head or "", metadata_sha256, screenshots,
                **common,
            ), timeout=120)
            browser_results.append(seed)
            seed_ids = seed.get("seed_record_ids")
            if (not isinstance(seed_ids, list) or not seed_ids
                    or len(seed_ids) > 20 or any(not isinstance(value, str) or not SF_ID_RE.fullmatch(value)
                                                  for value in seed_ids)):
                raise CheckFailure("seed", "seed-invalid")
            seeded = _items(shared, ids=seed_ids)
            if len(seeded) != len(set(seed_ids)) or any(
                row.get("CreatedById") != user_id or not isinstance(row.get("Name"), str)
                or not row["Name"].startswith("Grok Demo ") or row.get("Status__c") not in {"Open", "Done"}
                for row in seeded
            ):
                raise CheckFailure("seed", "seed-invalid")
            selected = next((row for row in seeded if row.get("Status__c") == "Open"), None)
            if selected is None:
                raise CheckFailure("seed", "seed-invalid")
            selected_id = selected.get("Id")
            selected_name = selected.get("Name")
            _set_item_notes(shared, selected_id, note_payload)
            selected_rows = _items(shared, ids=[selected_id])
            if len(selected_rows) != 1 or selected_rows[0].get("Notes__c") != note_payload:
                raise CheckFailure("database", "database-state-mismatch")
            baseline_items = _items(shared)
            if len(baseline_items) > 500:
                raise CheckFailure("database", "database-state-mismatch")
            conversation_id = setup.get("conversation_id")
            if not isinstance(conversation_id, str) or not SF_ID_RE.fullmatch(conversation_id):
                raise CheckFailure("setup-save", "conversation-missing")
            shared_fields = {**common, "conversation_id": conversation_id,
                             "selected_record_id": selected_id, "selected_name": selected_name,
                             "nonce": nonce, "note_payload": note_payload}
            read_result = _run_browser(browser_worker, _request(
                mode, "read-tool", login, identity, source_head or "", metadata_sha256, screenshots,
                **shared_fields,
            ), timeout=300)
            browser_results.append(read_result)
            after_read = _items(shared)
            if not _same_items(baseline_items, after_read):
                raise CheckFailure("read-tool", "extra-write")
            create_name = "Grok Demo Create " + run_id
            create_notes = "Synthetic create note " + run_id
            create_result = _run_browser(browser_worker, _request(
                mode, "create-proposal", login, identity, source_head or "", metadata_sha256, screenshots,
                **shared_fields, create_name=create_name, create_notes=create_notes,
            ), timeout=300)
            browser_results.append(create_result)
            create_action_id = create_result.get("action_id")
            if not isinstance(create_action_id, str) or not ACTION_ID_RE.fullmatch(create_action_id):
                raise CheckFailure("create-proposal", "proposal-missing")
            if any(row.get("Name") == create_name for row in _items(shared)):
                raise CheckFailure("create-proposal", "preconfirm-write")
            create_confirm = _run_browser(browser_worker, _request(
                mode, "create-confirm", login, identity, source_head or "", metadata_sha256, screenshots,
                **shared_fields, create_name=create_name, create_notes=create_notes,
                create_action_id=create_action_id,
            ), timeout=180)
            browser_results.append(create_confirm)
            after_create = _items(shared)
            created_rows = [row for row in after_create if row.get("Name") == create_name]
            create_id = created_rows[0].get("Id") if len(created_rows) == 1 else None
            if (len(created_rows) != 1 or created_rows[0].get("Status__c") != "Open"
                    or created_rows[0].get("Notes__c") != create_notes
                    or created_rows[0].get("CreatedById") != user_id):
                raise CheckFailure("create-confirm", "write-missing")
            create_calls = _action_calls(create_confirm, create_action_id)
            if (not any(call.get("result_status") == "applied"
                        and call.get("result_operation") == "create"
                        and call.get("result_record_id") == create_id for call in create_calls)
                    or any(call.get("result_status") == "rejected"
                           and call.get("result_record_id") not in (None, create_id) for call in create_calls)):
                raise CheckFailure("create-confirm", "controller-proof-missing")
            update_fields = {
                **shared_fields,
                "selected_name_unique": _unique_visible_item_name(after_create, selected_id, selected_name),
            }
            update_result = _run_browser(browser_worker, _request(
                mode, "update-proposal", login, identity, source_head or "", metadata_sha256, screenshots,
                **update_fields,
            ), timeout=300)
            browser_results.append(update_result)
            update_action_id = update_result.get("action_id")
            if not isinstance(update_action_id, str) or not ACTION_ID_RE.fullmatch(update_action_id):
                raise CheckFailure("update-proposal", "proposal-missing")
            before_update = _items(shared, ids=[selected_id])
            if (len(before_update) != 1 or before_update[0].get("Status__c") != selected.get("Status__c")
                    or before_update[0].get("Notes__c") != note_payload):
                raise CheckFailure("update-proposal", "preconfirm-write")
            update_confirm = _run_browser(browser_worker, _request(
                mode, "update-confirm", login, identity, source_head or "", metadata_sha256, screenshots,
                **update_fields, update_action_id=update_action_id,
            ), timeout=180)
            browser_results.append(update_confirm)
            after_update = _items(shared, ids=[selected_id])
            if (len(after_update) != 1 or after_update[0].get("Status__c") != "Done"
                    or after_update[0].get("Notes__c") != note_payload):
                raise CheckFailure("update-confirm", "write-missing")
            update_calls = _action_calls(update_confirm, update_action_id)
            if (len(update_calls) != 1 or update_calls[0].get("result_status") != "applied"
                    or update_calls[0].get("result_operation") != "update"
                    or update_calls[0].get("result_record_id") != selected_id):
                raise CheckFailure("update-confirm", "controller-proof-missing")
            cancel_name = "Grok Demo Cancel " + run_id
            cancel_notes = "Synthetic cancelled note " + run_id
            cancel_proposal = _run_browser(browser_worker, _request(
                mode, "cancel-proposal", login, identity, source_head or "", metadata_sha256, screenshots,
                **shared_fields, cancel_name=cancel_name, cancel_notes=cancel_notes,
            ), timeout=300)
            browser_results.append(cancel_proposal)
            cancel_action_id = cancel_proposal.get("action_id")
            if not isinstance(cancel_action_id, str) or not ACTION_ID_RE.fullmatch(cancel_action_id):
                raise CheckFailure("cancel-proposal", "proposal-missing")
            if any(row.get("Name") == cancel_name for row in _items(shared)):
                raise CheckFailure("cancel-proposal", "preconfirm-write")
            cancel_confirm = _run_browser(browser_worker, _request(
                mode, "cancel-confirm", login, identity, source_head or "", metadata_sha256, screenshots,
                **shared_fields, cancel_name=cancel_name, cancel_notes=cancel_notes,
                cancel_action_id=cancel_action_id,
            ), timeout=180)
            browser_results.append(cancel_confirm)
            after_cancel = _items(shared)
            if any(row.get("Name") == cancel_name for row in after_cancel):
                raise CheckFailure("cancel-confirm", "cancel-mismatch")
            stale_notes = secrets.token_urlsafe(20)
            stale_fields = {
                **shared_fields,
                "selected_name_unique": _unique_visible_item_name(after_cancel, selected_id, selected_name),
            }
            stale_proposal = _run_browser(browser_worker, _request(
                mode, "stale-proposal", login, identity, source_head or "", metadata_sha256, screenshots,
                **stale_fields, stale_notes=stale_notes,
            ), timeout=300)
            browser_results.append(stale_proposal)
            stale_action_id = stale_proposal.get("action_id")
            if not isinstance(stale_action_id, str) or not ACTION_ID_RE.fullmatch(stale_action_id):
                raise CheckFailure("stale-proposal", "proposal-missing")
            stale_before = _items(shared, ids=[selected_id])
            if len(stale_before) != 1 or stale_before[0].get("Notes__c") != note_payload:
                raise CheckFailure("stale-proposal", "preconfirm-write")
            external_notes = secrets.token_urlsafe(20)
            _set_item_notes(shared, selected_id, external_notes)
            stale_confirm = _run_browser(browser_worker, _request(
                mode, "stale-confirm", login, identity, source_head or "", metadata_sha256, screenshots,
                **stale_fields, stale_notes=stale_notes, external_notes=external_notes,
                stale_action_id=stale_action_id, create_action_id=create_action_id,
                update_action_id=update_action_id, cancel_action_id=cancel_action_id,
            ), timeout=180)
            browser_results.append(stale_confirm)
            after_stale = _items(shared, ids=[selected_id])
            if (len(after_stale) != 1 or after_stale[0].get("Status__c") != "Done"
                    or after_stale[0].get("Notes__c") != external_notes):
                raise CheckFailure("stale-confirm", "stale-not-rejected")
            stale_calls = _action_calls(stale_confirm, stale_action_id)
            if (len(stale_calls) != 1 or stale_calls[0].get("result_status") != "stale"
                    or stale_calls[0].get("result_operation") != "update"
                    or stale_calls[0].get("result_record_id") != selected_id):
                raise CheckFailure("stale-confirm", "controller-proof-missing")
            final_items = _items(shared)
            extra_write_count = _unexpected_item_changes(baseline_items, final_items,
                                                        selected_id, create_id, create_name, create_notes,
                                                        external_notes)
            if extra_write_count:
                raise CheckFailure("database", "extra-write")
            final_receipt = {
                "schema": "shiploop-grok-chat-full-ui-observation/1", "check_id": artifact_dir.name,
                "checked_at": started, "phase": phase, "mode": mode, "status": "passed",
                "org": {"org_id": identity["org_id"], "lightning_host": identity["lightning_host"],
                        "user_id": user_id},
                "source_head": source_head, "candidate_metadata_sha256": metadata_sha256,
                "deployment": deployment, "cleared_config_rows": cleared_configs,
                "synthetic_fixture_reset": item_reset,
                "conversation_id": conversation_id,
                "selected_item_id": selected_id, "created_item_id": create_id,
                "observed_setup_status": "missing", "route_host": setup.get("route_host"),
                "route_path": setup.get("route_path"), "browser_version": setup.get("browser_version"),
                "ui_attempted_first": attempt.get("ui_attempted_first"),
                "auth_required": attempt.get("auth_required"), "auth_used": auth_used,
                "setup_missing_without_chat_attempt": setup.get("setup_missing_without_chat_attempt"),
                "setup_business_unchanged": True,
                "config_readback_match": True, "connection_ok": setup.get("connection_ok"),
                "recheck_ready": setup.get("recheck_ready"),
                "read_tool_proof": read_result.get("read_tool_proof"),
                "create_proposal_exact": create_result.get("proposal_exact"),
                "create_preconfirm_absent": True, "create_one_write": create_confirm.get("one_write"),
                "update_proposal_exact": update_result.get("proposal_exact"),
                "update_preconfirm_unchanged": True, "update_one_write": update_confirm.get("one_write"),
                "cancel_proposal_exact": cancel_proposal.get("proposal_exact"),
                "cancelled_absent": cancel_confirm.get("cancelled_absent"),
                "stale_proposal_exact": stale_proposal.get("proposal_exact"),
                "stale_rejected": stale_confirm.get("stale_rejected"),
                "stale_external_value_preserved": True,
                "duplicate_safe": create_confirm.get("duplicate_safe"),
                "duplicate_attempted": create_confirm.get("duplicate_attempted"),
                "duplicate_delivery_count": create_confirm.get("duplicate_delivery_count"),
                "reload_history_persisted": stale_confirm.get("reload_history_persisted"),
                "new_conversation": setup.get("new_conversation"),
                "desktop_layout_ok": setup.get("desktop_layout_ok") and read_result.get("desktop_layout_ok"),
                "narrow_layout_ok": setup.get("narrow_layout_ok") and stale_confirm.get("narrow_layout_ok"),
                "keyboard_ok": setup.get("keyboard_ok"), "safe_text_ok": read_result.get("safe_text_ok"),
                "business_write_count": 2, "extra_write_count": extra_write_count,
                "action_ids": {"create": create_action_id, "update": update_action_id,
                               "cancel": cancel_action_id, "stale": stale_action_id},
                "chat_turns": [_safe_chat_turn_projection(result) for result in (
                    read_result, create_result, update_result, cancel_proposal, stale_proposal,
                )],
                "screenshots": 5,
                "controller_calls": _safe_controller_projection(browser_results),
                "database_projection": {
                    "config_match": True, "seed_count": len(seed_ids),
                    "created_count": len(created_rows), "updated_count": 1,
                    "cancelled_count": 0, "stale_write_count": 0,
                    "final_owned_item_count": len(final_items), "extra_write_count": extra_write_count,
                },
            }
            final_receipt["live_callout_methods"] = (
                _turn_execution_methods(final_receipt, final_receipt["controller_calls"]) or [])
            errors = validate_observation(final_receipt, mode=mode, phase=phase,
                expected_host=identity["lightning_host"], source_head=source_head or "",
                metadata_sha256=metadata_sha256)
            if errors:
                raise CheckFailure("controller", errors[0])
            receipt_data = final_receipt
        final_head, final_digest = _candidate_identity(Path.cwd())
        if final_head != source_head or final_digest != metadata_sha256:
            raise CheckFailure("source", "source-changed")
        screenshots_used = {key: value for key, value in screenshots.items() if value.is_file()}
        if mode == "run" and len(screenshots_used) != 5:
            raise CheckFailure("browser", "screenshot-missing")
        receipt_data["screenshot_receipts"] = _screen_receipts(screenshots_used, platform_dir)
        receipt_path_relative, receipt_sha256 = _write_receipt(receipt_path, platform_dir, receipt_data)
        if mode == "observe":
            print("grok-chat-ui: OBSERVED (UI exploration only; acceptance and deployment unbound)")
        else:
            print("grok-chat-ui: PASS (public UI, controller pairing, and independent database assertions)")
        print(f"grok-chat-ui: receipt={receipt_path_relative} sha256={receipt_sha256}")
        return 0
    except CheckFailure as exc:
        failure = exc
        # The failed step never returns normally to append its terminal snapshot.
        # Merge it after earlier snapshots so PENDING can become completed.
        browser_results.append(exc.browser_result)
    except Exception:
        failure = CheckFailure("browser", "evaluation-failed")
    finally:
        if browser_worker is not None:
            browser_worker.close()

    failure_data = {
        "schema": "shiploop-grok-chat-full-ui-observation/1", "check_id": artifact_dir.name,
        "checked_at": started, "phase": phase, "mode": mode, "status": "failed",
        "source_head": source_head, "candidate_metadata_sha256": metadata_sha256,
        "deployment": deployment,
        "synthetic_fixture_reset": item_reset,
        "browser_failure": failure.browser_result.get("browser_failure", {}) if failure else {},
        "failure": {"stage": failure.stage if failure else "browser",
                    "reason_code": failure.reason if failure else "evaluation-failed"},
        "chat_turns": [_safe_chat_turn_projection(result) for result in browser_results if "chat_turn" in result],
        "controller_calls": _safe_controller_projection(browser_results),
    }
    try:
        receipt_path_relative, receipt_sha256 = _write_receipt(receipt_path, platform_dir, failure_data)
        print(f"grok-chat-ui: FAIL ({failure.stage if failure else 'browser'}: {failure.reason if failure else 'evaluation-failed'})",
              file=sys.stderr)
        print(f"grok-chat-ui: receipt={receipt_path_relative} sha256={receipt_sha256}", file=sys.stderr)
    except OSError:
        print(f"grok-chat-ui: FAIL ({failure.stage if failure else 'browser'}: {failure.reason if failure else 'evaluation-failed'})",
              file=sys.stderr)
    return 1


def _same_items(left: list[dict], right: list[dict]) -> bool:
    fields = ("Id", "Name", "Status__c", "Notes__c", "CreatedById")
    return sorted(tuple(row.get(field) for field in fields) for row in left) == \
        sorted(tuple(row.get(field) for field in fields) for row in right)


def _unexpected_item_changes(before: list[dict], after: list[dict], selected_id: str,
                             create_id: str | None, create_name: str, create_notes: str,
                             selected_notes: str) -> int:
    old = {row.get("Id"): row for row in before}
    new = {row.get("Id"): row for row in after}
    unexpected = 0
    expected_ids = set(old) | ({create_id} if create_id else set())
    if set(new) != expected_ids:
        unexpected += len(set(new) ^ expected_ids)
    for record_id, row in old.items():
        latest = new.get(record_id)
        if latest is None:
            unexpected += 1
            continue
        if record_id == selected_id:
            if (row.get("Name") != latest.get("Name") or row.get("CreatedById") != latest.get("CreatedById")
                    or latest.get("Status__c") != "Done" or latest.get("Notes__c") != selected_notes):
                unexpected += 1
        elif any(row.get(field) != latest.get(field) for field in ("Name", "Status__c", "Notes__c", "CreatedById")):
            unexpected += 1
    if create_id:
        created = new.get(create_id)
        if (not created or created.get("Name") != create_name or created.get("Status__c") != "Open"
                or created.get("Notes__c") != create_notes):
            unexpected += 1
    return unexpected


def main() -> int:
    args, errors = parse_options(sys.argv[1:])
    if errors:
        print("grok-chat-ui: invalid mode options refused", file=sys.stderr)
        return 2
    return run_check(args.mode)


if __name__ == "__main__":
    raise SystemExit(main())
