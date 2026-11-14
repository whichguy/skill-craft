#!/usr/bin/env python3
"""Require source review and attended live evidence before accepting quality.

The operator writes the review; the subject may read findings but never author
the evaluator's receipt. This is a trusted test apparatus, not a hostile-host
security boundary. Human judgment remains explicit rather than a comment quota.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time

DIMENSIONS = ("code", "errors", "comments", "tombstones", "tests")
PHASES = {"builder", "final"}
# This is the existing hosted-check observation budget, not a ShipLoop loop cap.
CHECK_SECONDS = 2700
ENDPOINT = "https://api.x.ai/v1/responses"
LIVE_REQUEST_SCHEMA = "shiploop-grok-chat-live-acceptance-request/1"
LIVE_RECEIPT_SCHEMA = "shiploop-grok-chat-live-acceptance-receipt/1"
JOIN_FIELDS = {
    "method", "request_id", "request_started_at", "response_completed_at", "log_id", "native_request_id",
    "body_sha256", "outcome", "endpoint", "endpoint_kinds", "log_started_at", "trace_flag_id",
    "org_id", "user_id", "window",
}
RESOLUTION_FIELDS = {
    "org_id", "user_id", "name", "named_credential_id", "endpoint",
    "before_started_at", "before_completed_at", "after_started_at", "after_completed_at",
}
STAMP = re.compile(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d{1,6})?(?:Z|[+-]\d\d:?\d\d)")

# Load only the local, import-safe receipt and deploy validators. No browser or
# Salesforce entry point runs when this file is imported or when quality runs.
UI_SPEC = importlib.util.spec_from_file_location(
    "grok_chat_quality_ui", Path(__file__).resolve().with_name("grok_chat_full_ui.py"))
assert UI_SPEC is not None and UI_SPEC.loader is not None
ui = importlib.util.module_from_spec(UI_SPEC)
UI_SPEC.loader.exec_module(ui)


def snapshot(root: Path) -> dict:
    root = root.resolve()
    deployable = root / "force-app"
    if not (root / "sfdx-project.json").is_file() or not deployable.is_dir() or deployable.is_symlink():
        raise ValueError("candidate is not a Salesforce source project")
    files = subprocess.run(
        ["git", "-C", str(root), "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        capture_output=True, check=True, timeout=20,
    ).stdout.split(b"\0")
    names = {os.fsdecode(raw) for raw in files if raw}
    # Git ignore rules do not prevent Salesforce from deploying local metadata.
    # Include that entire tree so ignored Apex cannot evade source-bound review.
    for path in deployable.rglob("*"):
        if path.is_symlink():
            raise ValueError("deployable source contains a symbolic path")
        if path.is_file():
            names.add(path.relative_to(root).as_posix())
    entries = []
    digest = hashlib.sha256()
    for name in sorted(names):
        raw = os.fsencode(name)
        path = root / name
        if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(root):
            raise ValueError("candidate has a missing, escaping or symbolic source path")
        content = path.read_bytes()
        sha = hashlib.sha256(content).hexdigest()
        entries.append({"path": name, "sha256": sha})
        digest.update(raw + b"\0" + content + b"\0")
    if not entries:
        raise ValueError("candidate has no source files")
    head = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"],
                          capture_output=True, text=True, check=True, timeout=10).stdout.strip()
    return {"repo": str(root), "head": head, "sha256": digest.hexdigest(), "files": entries}


def validate_review(review: dict, expected: dict, directory: Path) -> list[str]:
    errors = []
    if not isinstance(review, dict):
        return ["review-not-an-object"]
    if review.get("schema") != "shiploop-grok-chat-quality-review/1":
        errors.append("review-schema")
    if review.get("source_sha256") != expected["sha256"]:
        errors.append("review-source-mismatch")
    reviewer = review.get("reviewer", {})
    if (not isinstance(reviewer, dict) or reviewer.get("independent") is not True
            or any(not isinstance(reviewer.get(key), str) or not reviewer[key].strip()
                   for key in ("actor", "execution_id", "provenance"))):
        errors.append("independent-reviewer-missing")
    dimensions = review.get("dimensions")
    if not isinstance(dimensions, dict) or set(dimensions) != set(DIMENSIONS):
        errors.append("review-dimensions-incomplete")
    else:
        for key in DIMENSIONS:
            row = dimensions[key]
            if not isinstance(row, dict) or row.get("status") != "PASS" or not row.get("reason"):
                errors.append("review-dimension-" + key)
    findings = review.get("findings")
    if not isinstance(findings, list):
        errors.append("review-findings-missing")
    elif any(not isinstance(row, dict) or row.get("actionable") is not False for row in findings):
        errors.append("actionable-findings-remain")
    evidence = review.get("evidence")
    if not isinstance(evidence, list) or not evidence:
        errors.append("review-evidence-missing")
    else:
        for item in evidence:
            if not isinstance(item, dict) or not isinstance(item.get("path"), str):
                errors.append("review-evidence-invalid")
                continue
            path = directory / item["path"]
            try:
                if path.is_symlink() or not path.resolve().is_relative_to(directory.resolve()):
                    raise ValueError("evidence path escaped review")
                raw = path.read_bytes()
                if not raw or hashlib.sha256(raw).hexdigest() != item.get("sha256"):
                    raise ValueError("evidence hash mismatch")
            except (OSError, ValueError):
                errors.append("review-evidence-invalid")
    if review.get("status") != "PASS":
        errors.append("review-not-passed")
    return sorted(set(errors))


def timestamp_ms(value: object) -> float:
    if not isinstance(value, str) or not STAMP.fullmatch(value):
        raise ValueError("invalid evidence timestamp")
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp() * 1000
    except (OSError, OverflowError) as exc:
        raise ValueError("invalid evidence timestamp") from exc


def latest_ui_path(platform: Path, phase: str, *, nonblocking: bool = False) -> Path | None:
    attempts = platform / "grok-chat-ui" / phase
    ledger_path = attempts / ui.UI_ATTEMPT_LEDGER
    if not ledger_path.is_file() or ledger_path.is_symlink():
        return None
    with ledger_path.open(encoding="ascii", newline="") as ledger:
        try:
            fcntl.flock(ledger, fcntl.LOCK_SH | (fcntl.LOCK_NB if nonblocking else 0))
        except BlockingIOError as exc:
            raise EvidenceBusy("ui-evidence-busy") from exc
        rows = ledger.readlines()
        if not rows or any(not row.endswith("\n") or not ui.UI_ATTEMPT_ID_RE.fullmatch(row[:-1])
                           for row in rows):
            return None
        ids = [row[:-1] for row in rows]
        registered = set(ids)
        if len(registered) != len(ids) or any(
                ui.UI_ATTEMPT_ID_RE.fullmatch(path.name) and path.name not in registered
                for path in attempts.iterdir()):
            return None
    return attempts / ids[-1] / "observation.json"


def deploy_started_without_overlap(platform: Path, call_id: str) -> bool:
    # The guarded loader selects by start order. If an earlier deploy was still
    # active at that start, the receipts cannot establish the remote write order.
    active = set()
    latest = None
    serial = False
    for line in (platform / "sf-calls.jsonl").read_text().splitlines():
        row = json.loads(line) if line.strip() else None
        if not isinstance(row, dict) or not isinstance(call := row.get("call"), str):
            continue
        if row.get("end") is True:
            active.discard(call)
            continue
        if ui._is_deploy_start(row):
            latest = call
            serial = not active
            active.add(call)
    return latest == call_id and serial and not active


def live_request(root: Path, platform: Path, phase: str, source: dict, *, nonblocking: bool = False) -> dict | None:
    try:
        path = latest_ui_path(platform, phase, nonblocking=True) if nonblocking else latest_ui_path(platform, phase)
        if path is None or path.resolve() != path:
            return None
        raw = path.read_bytes()
        receipt = json.loads(raw)
        if (not isinstance(receipt, dict) or receipt.get("status") != "passed"
                or receipt.get("check_id") != path.parent.name):
            return None
        org = receipt.get("org")
        if not isinstance(org, dict) or org.get("org_id") != ui.EXPECTED_ORG_ID:
            return None
        user, host = org.get("user_id"), org.get("lightning_host")
        if (not isinstance(user, str) or not ui.SF_ID_RE.fullmatch(user)
                or not isinstance(host, str) or not re.fullmatch(r"[a-z0-9.-]+\.lightning\.force\.com", host)):
            return None
        deploy = ui._latest_successful_deploy(platform)
        if (deploy is None or receipt.get("deployment") != deploy
                or type(deploy.get("exit")) is not int or deploy["exit"] != 0
                or deploy.get("interrupted") is not False
                or not isinstance(deploy.get("call_id"), str)
                or not re.fullmatch(r"[a-f0-9]{8}", deploy["call_id"])
                or not deploy_started_without_overlap(platform, deploy["call_id"])):
            return None
        finished_ms = timestamp_ms(deploy.get("finished_at"))
        if timestamp_ms(deploy.get("started_at")) > finished_ms:
            return None
        metadata = ui.sf_guard.force_app_sha256(root)
        if not ui._source_is_fresh(root, deploy, metadata) or ui.validate_observation(
                receipt, mode="run", phase=phase, expected_host=host,
                source_head=source["head"], metadata_sha256=metadata):
            return None
        calls = receipt["controller_calls"]
        by_sequence = {call["request_sequence"]: call for call in calls}
        execution = [call for call in calls if call["method"] == "testConnection"]
        execution.extend(by_sequence[turn["execution_request_sequence"]] for turn in receipt["chat_turns"])
        if len(execution) != 6 or any(call["request_started_at"] < finished_ms for call in execution):
            return None
        return {
            "schema": LIVE_REQUEST_SCHEMA,
            "identity": {
                "source_sha256": source["sha256"], "ui_receipt_sha256": hashlib.sha256(raw).hexdigest(),
                "deployment_call_id": deploy["call_id"], "deployment_source_sha256": metadata,
                "org_id": org["org_id"], "user_id": user,
            },
            "phase": phase,
            "ui_receipt_path": path.relative_to(platform).as_posix(),
            "browser_requests": [{
                "method": call["method"], "request_id": call["server_request_id"],
                "started_ms": call["request_started_at"], "completed_ms": call["response_completed_at"],
            } for call in execution],
            "instructions": (
                f"Publish sibling receipt.json atomically with exactly schema ({LIVE_RECEIPT_SCHEMA}), "
                "identity (copied verbatim from this request), trace_window and joins. "
                "Set trace_window to exactly org_id and user_id from the trace ledger's window event, "
                "baseline and expires from its ready event, and trace_flag_id from the create_observed "
                "event's id for resource TraceFlag. For each of the six browser_requests, pass its method, "
                "request_id, started_ms and completed_ms to the trace helper's match_browser_call. "
                "Use that closed join verbatim (method, request_id, request_started_at, response_completed_at, "
                "log_id, native_request_id, body_sha256, outcome, endpoint, endpoint_kinds, org_id, user_id, "
                "window containing exactly baseline and expires, and endpoint_resolution only for a "
                "NAMED_CREDENTIAL kind). Add log_started_at from the matched log projection's start "
                "for that log_id and trace_flag_id from the same TraceFlag creation event. "
                f"Each join requires outcome HTTP_200 and endpoint {ENDPOINT}. "
                "Copy endpoint_resolution verbatim from the helper for same-org, same-user readbacks "
                f"bracketing the request, with exactly {', '.join(sorted(RESOLUTION_FIELDS))}. "
                "The method index, beginMessage, terminal replays, app ok flags, local nonce reads and separate "
                "preflights cannot supply joins. Exclude raw bodies, headers and secrets."),
        }
    except EvidenceBusy:
        raise
    except (OSError, ValueError, KeyError, TypeError, RuntimeError):
        return None


def same_sf_id(value: object, expected: str) -> bool:
    return isinstance(value, str) and bool(ui.SF_ID_RE.fullmatch(value)) and value[:15] == expected[:15]


def valid_endpoint_resolution(value: object, identity: dict, start: float, end: float) -> bool:
    if (not isinstance(value, dict) or set(value) != RESOLUTION_FIELDS
            or not same_sf_id(value["org_id"], identity["org_id"])
            or not same_sf_id(value["user_id"], identity["user_id"])
            or value["name"] != ui.NAMED_CREDENTIAL or value["endpoint"] != "https://api.x.ai"
            or not isinstance(value["named_credential_id"], str)
            or not ui.SF_ID_RE.fullmatch(value["named_credential_id"])):
        return False
    try:
        return (timestamp_ms(value["before_started_at"]) <= timestamp_ms(value["before_completed_at"])
                <= start <= end <= timestamp_ms(value["after_started_at"])
                <= timestamp_ms(value["after_completed_at"]))
    except ValueError:
        return False


def validate_live_receipt(receipt: object, request: dict) -> list[str]:
    if (not isinstance(receipt, dict) or set(receipt) != {"schema", "identity", "trace_window", "joins"}
            or receipt.get("schema") != LIVE_RECEIPT_SCHEMA):
        return ["live-acceptance-schema"]
    identity = request["identity"]
    if receipt["identity"] != identity:
        return ["live-acceptance-identity-mismatch"]
    window = receipt["trace_window"]
    if (not isinstance(window, dict) or set(window) != {"trace_flag_id", "org_id", "user_id", "baseline", "expires"}
            or not same_sf_id(window["org_id"], identity["org_id"])
            or not same_sf_id(window["user_id"], identity["user_id"])
            or not isinstance(window["trace_flag_id"], str) or not ui.SF_ID_RE.fullmatch(window["trace_flag_id"])):
        return ["live-acceptance-trace-window"]
    try:
        baseline, expires = timestamp_ms(window["baseline"]), timestamp_ms(window["expires"])
    except ValueError:
        return ["live-acceptance-trace-window"]
    if baseline >= expires:
        return ["live-acceptance-trace-window"]
    window_times = {"baseline": window["baseline"], "expires": window["expires"]}

    expected = {call["request_id"]: call for call in request["browser_requests"]}
    joins = receipt["joins"]
    if not isinstance(joins, list) or len(joins) != len(expected) or len(expected) != 6:
        return ["live-acceptance-six-joins-required"]
    log_ids, request_ids = set(), set()
    for join in joins:
        if not isinstance(join, dict):
            return ["live-acceptance-join-schema"]
        kinds = join.get("endpoint_kinds")
        if (not isinstance(kinds, list) or not kinds
                or any(kind not in ("HTTPS", "NAMED_CREDENTIAL") for kind in kinds)):
            return ["live-acceptance-join-schema"]
        alias = "NAMED_CREDENTIAL" in kinds
        fields = JOIN_FIELDS | ({"endpoint_resolution"} if alias else set())
        if set(join) != fields:
            return ["live-acceptance-join-schema"]
        request_id = join["request_id"]
        call = expected.get(request_id) if isinstance(request_id, str) else None
        native_id = join["native_request_id"]
        if (call is None or request_id in request_ids
                or join["method"] != call["method"] or join["request_started_at"] != call["started_ms"]
                or join["response_completed_at"] != call["completed_ms"]
                or (native_id != request_id and (len(request_id) > 80 or native_id != "TID:" + request_id))):
            return ["live-acceptance-request-mismatch"]
        request_ids.add(request_id)
        log_id = join["log_id"]
        if not isinstance(log_id, str) or not ui.SF_ID_RE.fullmatch(log_id) or log_id[:15] in log_ids:
            return ["live-acceptance-log-identity"]
        log_ids.add(log_id[:15])
        if (not same_sf_id(join["trace_flag_id"], window["trace_flag_id"])
                or not same_sf_id(join["org_id"], identity["org_id"])
                or not same_sf_id(join["user_id"], identity["user_id"]) or join["window"] != window_times):
            return ["live-acceptance-trace-window"]
        start, end = call["started_ms"], call["completed_ms"]
        try:
            log_start = timestamp_ms(join["log_started_at"])
        except ValueError:
            return ["live-acceptance-join-time"]
        # The trace reader bounds ApexLog StartTime at whole-second precision.
        if not (baseline < start <= end < expires and baseline < log_start < expires
                and int(start // 1000) * 1000 <= log_start <= end):
            return ["live-acceptance-join-time"]
        if (not ui._valid_digest(join["body_sha256"]) or join["outcome"] != "HTTP_200"
                or join["endpoint"] != ENDPOINT):
            return ["live-acceptance-callout-unproven"]
        if alias and not valid_endpoint_resolution(join["endpoint_resolution"], identity, start, end):
            return ["live-acceptance-endpoint-resolution"]
    return []


def write_request(path: Path, request: dict) -> None:
    if path.exists():
        return
    path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
    # Publish complete bytes once even if multiple checks request the same evidence.
    with tempfile.NamedTemporaryFile(mode="w", dir=path.parent) as temporary:
        temporary.write(json.dumps(request, indent=2) + "\n")
        temporary.flush()
        try:
            os.link(temporary.name, path)
        except FileExistsError:
            pass


def request_source_review(platform: Path, phase: str, source: dict) -> Path:
    directory = platform / "grok-chat-quality" / source["sha256"]
    request_path = directory / "request.json"
    safe_request(request_path)
    write_request(request_path, {
        "schema": "shiploop-grok-chat-quality-request/1",
        "requested_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "phase": phase, "source": source, "dimensions": list(DIMENSIONS),
        "instructions": (
            "Independent operator review required. Subject must not write review/evidence receipts. "
            "Cite exact source/test locations, decisive assertions and executed native results for each claim. "
            "Require field-only denial when object access exists and expired-confirmation evidence. "
            "Verify authority, replay, transaction ordering, ownership/recovery comments and warranted tombstones. "
            "The nine-method public API and independent sendMessage oracle remain required. "
            "Inspect the full test map; missing required observations or generic unsupported review prose are non-pass. "
            "Attended provider callout joins are handled by the separate live acceptance request."),
    })
    read_source_request(request_path, source)
    print("grok-chat-quality: independent review requested; " + str(request_path), flush=True, file=sys.stderr)
    return directory


class InvalidRequest(ValueError):
    """An existing immutable request is unsafe or does not bind this content."""


class EvidenceBusy(RuntimeError):
    """The latest UI ledger cannot be read without waiting."""


def safe_request(path: Path) -> None:
    if path.resolve() != path or path.is_symlink() or (path.exists() and not path.is_file()):
        raise InvalidRequest("unsafe-request-path")


def read_source_request(path: Path, source: dict) -> dict:
    safe_request(path)
    try:
        value = json.loads(path.read_bytes())
        historical = value["source"]
        if (not isinstance(value, dict) or value.get("schema") != "shiploop-grok-chat-quality-request/1"
                or value.get("phase") not in PHASES or value.get("dimensions") != list(DIMENSIONS)
                or not isinstance(value.get("instructions"), str) or not value["instructions"].strip()
                or not isinstance(historical, dict) or set(historical) != {"repo", "head", "sha256", "files"}
                or historical["sha256"] != source["sha256"] or historical["files"] != source["files"]
                or not isinstance(historical["head"], str) or not re.fullmatch(r"[a-f0-9]{40,64}", historical["head"])
                or not isinstance(historical["repo"], str) or not Path(historical["repo"]).is_absolute()
                or str(Path(historical["repo"])) != historical["repo"]
                or ".." in Path(historical["repo"]).parts):
            raise InvalidRequest("invalid-source-request")
        timestamp_ms(value.get("requested_at"))
        return value
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise InvalidRequest("invalid-source-request") from exc


def live_request_path(directory: Path, live: dict) -> Path:
    key = hashlib.sha256(json.dumps(live["identity"], sort_keys=True,
                                   separators=(",", ":")).encode()).hexdigest()
    return directory / "live-acceptance" / key / "request.json"


def published_live_request(directory: Path, live: dict, *, publish: bool) -> Path | None:
    path = live_request_path(directory, live)
    safe_request(path)
    if publish:
        write_request(path, live)
    if not path.exists():
        return None
    safe_request(path)
    try:
        if json.loads(path.read_bytes()) != live:
            raise InvalidRequest("invalid-live-request")
    except (OSError, ValueError, TypeError) as exc:
        raise InvalidRequest("invalid-live-request") from exc
    return path


def request_context(root: Path, platform: Path, phase: str, source: dict, *, publish: bool,
                    nonblocking: bool) -> dict:
    directory = platform / "grok-chat-quality" / source["sha256"]
    source_path = directory / "request.json"
    safe_request(source_path)
    if publish:
        request_source_review(platform, phase, source)
    published = read_source_request(source_path, source) if source_path.exists() else None
    historical = published["source"] if published else None
    pending = [] if historical else ["source-request-not-prepared"]
    try:
        live = live_request(root, platform, phase, source, nonblocking=True) if nonblocking else live_request(
            root, platform, phase, source)
    except EvidenceBusy:
        live = None
        pending.append("ui-evidence-busy")
    path = published_live_request(directory, live, publish=publish) if live is not None else None
    if live is None:
        pending.append("current-live-evidence-unavailable")
    elif path is None:
        pending.append("live-request-not-prepared")
    return {"schema": "shiploop-grok-chat-quality-preparation/1", "phase": phase,
            "status": "pending" if pending else "prepared", "current_source": source,
            "historical_source": historical, "historical_phase": published["phase"] if published else None,
            "scope": "request-preparation-only", "source_request": str(source_path) if historical else None,
            "live_request": str(path) if path else None, "live_identity": live["identity"] if path else None,
            "pending": pending}


def _operation_inputs(root: Path, platform: Path, phase: str) -> tuple[Path, Path]:
    if phase not in PHASES:
        raise ValueError("unsupported phase")
    root, platform = root.resolve(), platform.resolve()
    if not root.is_relative_to(platform.parent) or root.is_relative_to(platform):
        raise ValueError("candidate outside run")
    return root, platform


def prepare_requests(root: Path, platform: Path, phase: str) -> dict:
    """Publish missing immutable requests once, without waiting or judging them."""
    root, platform = _operation_inputs(root, platform, phase)
    source = snapshot(root)
    result = request_context(root, platform, phase, source, publish=True, nonblocking=True)
    # A concurrently superseded source or selector must not leave a stale current pointer.
    current = snapshot(root)
    try:
        live = live_request(root, platform, phase, current, nonblocking=True)
    except EvidenceBusy:
        live = None
        result["pending"].append("ui-evidence-busy")
    if current != source or (live["identity"] if live else None) != result["live_identity"]:
        result.update(status="pending", live_request=None, live_identity=None)
        result["pending"].append("source-or-live-evidence-changed")
        if current != source:
            result.update(current_source=current, source_request=None, historical_source=None, historical_phase=None)
    return result


def assess_current(root: Path, platform: Path, phase: str) -> dict:
    """Assess only current quality/live obligations once; write no evidence."""
    root, platform = _operation_inputs(root, platform, phase)
    source = snapshot(root)
    context = request_context(root, platform, phase, source, publish=False, nonblocking=True)
    directory = platform / "grok-chat-quality" / source["sha256"]
    errors, pending = [], list(context["pending"])
    review_path = directory / "review.json"
    receipt_path = Path(context["live_request"]).with_name("receipt.json") if context["live_request"] else None
    review_raw = receipt_raw = None
    if review_path.exists() or review_path.is_symlink():
        try:
            safe_request(review_path)
            review_raw = review_path.read_bytes()
            errors.extend(validate_review(json.loads(review_raw), source, directory))
        except (OSError, ValueError, TypeError):
            errors.append("source-review-unreadable")
    else:
        pending.append("independent-review-pending")
    if receipt_path and (receipt_path.exists() or receipt_path.is_symlink()):
        try:
            safe_request(receipt_path)
            receipt_raw = receipt_path.read_bytes()
            live = json.loads(Path(context["live_request"]).read_bytes())
            errors.extend(validate_live_receipt(json.loads(receipt_raw), live))
        except (OSError, ValueError, KeyError, TypeError):
            errors.append("live-acceptance-receipt-unreadable")
    else:
        pending.append("live-acceptance-pending")
    current = snapshot(root)
    if current != source:
        errors.append("candidate-changed-during-review")
    # Re-run the same selectors and request validation; no publication on this path.
    try:
        after = request_context(root, platform, phase, current, publish=False, nonblocking=True)
        if after != context:
            errors.append("live-acceptance-evidence-changed")
            context.update(live_request=None, live_identity=None)
        if review_raw is not None:
            if review_path.read_bytes() != review_raw:
                errors.append("source-review-changed")
            errors.extend(validate_review(json.loads(review_raw), source, directory))
        if receipt_raw is not None and receipt_path.read_bytes() != receipt_raw:
            errors.append("live-acceptance-receipt-changed")
    except (OSError, ValueError, TypeError):
        errors.append("evidence-changed-during-assessment")
        context.update(live_request=None, live_identity=None)
    return {**context, "schema": "shiploop-grok-chat-quality-assessment/1",
            "scope": "current-source-quality-and-live-evidence",
            "status": "FAIL" if errors else "UNKNOWN" if pending else "PASS",
            "errors": sorted(set(errors)), "pending": sorted(set(pending))}


def run(root: Path, platform: Path, phase: str, *, wait_seconds: float = CHECK_SECONDS) -> int:
    if phase not in PHASES:
        print("grok-chat-quality: UNKNOWN (allowed only in builder/final)")
        return 2
    root, platform = root.resolve(), platform.resolve()
    if not root.is_relative_to(platform.parent) or root.is_relative_to(platform):
        print("grok-chat-quality: UNKNOWN (candidate outside this run)")
        return 2
    try:
        expected = snapshot(root)
        directory = request_source_review(platform, phase, expected)
        deadline = time.monotonic() + wait_seconds
        review_path = directory / "review.json"
        live_request_path = directory / "live-acceptance" / "*" / "request.json"
        receipt_path = None
        receipt_sha256 = None
        live = None
        reviewed = False
        errors = []
        pending = []
        while True:
            current = snapshot(root)
            source_changed = current["sha256"] != expected["sha256"]
            if source_changed:
                # Review can start while deployment and UI evidence are pending.
                expected = current
                directory = request_source_review(platform, phase, expected)
                review_path = directory / "review.json"
                reviewed = False
            current_live = live_request(root, platform, phase, current)
            if source_changed or current_live != live:
                # Retain earlier callbacks but stop looking at their receipts,
                # including while the newest attempt is still incomplete.
                live = current_live
                live_directory = directory / "live-acceptance"
                live_request_path = live_directory / "*" / "request.json"
                receipt_path = None
                if live is not None:
                    live_request_path = published_live_request(directory, live, publish=True)
                    receipt_path = live_request_path.with_name("receipt.json")
                    print("grok-chat-quality: live acceptance requested; " + str(live_request_path), flush=True)
            review_superseded = False
            if not reviewed and review_path.exists():
                errors = validate_review(json.loads(review_path.read_text()), expected, directory)
                if errors:
                    if snapshot(root)["sha256"] == expected["sha256"]:
                        break
                    # A failed review can arrive during evidence lookup for a
                    # source already replaced. Retry at the normal poll cadence.
                    errors = []
                    review_superseded = True
                else:
                    reviewed = True
            has_receipt = receipt_path is not None and receipt_path.exists()
            ready = reviewed and has_receipt
            remaining = deadline - time.monotonic()
            if ready or remaining <= 0:
                if review_superseded:
                    pending.append("source-review-superseded")
                    break
                if ready:
                    try:
                        receipt_bytes = receipt_path.read_bytes()
                        errors = validate_live_receipt(json.loads(receipt_bytes), live)
                        receipt_sha256 = hashlib.sha256(receipt_bytes).hexdigest()
                    except (OSError, ValueError):
                        errors = ["live-acceptance-receipt-unreadable"]
                    errors.extend(validate_review(json.loads(review_path.read_text()), expected, directory))
                current = snapshot(root) if reviewed else expected
                if current["sha256"] != expected["sha256"]:
                    errors.append("candidate-changed-during-review")
                if live is not None and live != live_request(root, platform, phase, current):
                    errors.append("live-acceptance-evidence-changed")
                if not reviewed:
                    pending.append("independent-review-pending")
                if not has_receipt:
                    pending.append("live-acceptance-pending")
                break
            time.sleep(min(2, remaining))
        status = "FAIL" if errors else "UNKNOWN" if pending else "PASS"
        result = {"schema": "shiploop-grok-chat-quality-check/1", "phase": phase,
                  "source_sha256": expected["sha256"], "errors": sorted(set(errors)),
                  "status": status}
        if live is not None:
            result["live_acceptance_identity"] = live["identity"]
            result["live_acceptance_request"] = live_request_path.relative_to(platform).as_posix()
        if status == "PASS":
            result["live_acceptance_receipt_sha256"] = receipt_sha256
        (directory / ("check-" + phase + ".json")).write_text(json.dumps(result, indent=2) + "\n")
        if errors:
            print("grok-chat-quality: FAIL (" + ", ".join(result["errors"]) + "); findings=" + str(review_path)
                  + "; live acceptance request=" + str(live_request_path))
            return 1
        if pending:
            print("grok-chat-quality: UNKNOWN (" + ", ".join(pending) + "); live acceptance request="
                  + str(live_request_path))
            return 2
        print("grok-chat-quality: PASS (independent source review and six attended native joins); review="
              + str(review_path) + "; live acceptance receipt=" + str(receipt_path))
        return 0
    except (OSError, ValueError, KeyError, subprocess.SubprocessError):
        # Provider/session strings and arbitrary source text never enter failure logs.
        print("grok-chat-quality: UNKNOWN (candidate or review evidence unreadable)")
        return 2


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    operations = parser.add_mutually_exclusive_group()
    operations.add_argument("--prepare-only", action="store_true")
    operations.add_argument("--assess-only", action="store_true")
    parser.add_argument("--json", action="store_true", help="one JSON document for prepare/assess")
    args = parser.parse_args(argv)
    platform = os.environ.get("E2E_PLATFORM_DIR")
    if args.prepare_only or args.assess_only:
        try:
            if not platform:
                raise ValueError("run-scoped platform unavailable")
            result = (prepare_requests if args.prepare_only else assess_current)(
                args.repo, Path(platform), os.environ.get("E2E_CHECK_PHASE", "unknown"))
        except InvalidRequest:
            result = {"schema": "shiploop-grok-chat-quality-preparation/1" if args.prepare_only else
                      "shiploop-grok-chat-quality-assessment/1",
                      "status": "invalid" if args.prepare_only else "FAIL",
                      "scope": "current-source-quality-and-live-evidence" if args.assess_only else "request-preparation-only",
                      "errors": ["invalid-published-request"], "live_request": None}
        except (OSError, ValueError, KeyError, TypeError, RuntimeError, subprocess.SubprocessError):
            result = {"schema": "shiploop-grok-chat-quality-preparation/1" if args.prepare_only else
                      "shiploop-grok-chat-quality-assessment/1",
                      "status": "invalid" if args.prepare_only else "UNKNOWN",
                      "scope": "current-source-quality-and-live-evidence" if args.assess_only else "request-preparation-only",
                      "errors": ["candidate-or-evidence-unreadable"], "live_request": None}
        print(json.dumps(result, indent=2) if args.json else
              "grok-chat-quality: " + result["status"] + " " + json.dumps(result))
        return (1 if result["status"] == "invalid" else 0) if args.prepare_only else {
            "PASS": 0, "FAIL": 1, "UNKNOWN": 2}[result["status"]]
    if args.json:
        parser.error("--json requires --prepare-only or --assess-only")
    if not platform:
        print("grok-chat-quality: UNKNOWN (run-scoped platform directory unavailable)")
        return 2
    return run(args.repo, Path(platform), os.environ.get("E2E_CHECK_PHASE", "unknown"))


if __name__ == "__main__":
    sys.exit(main())
