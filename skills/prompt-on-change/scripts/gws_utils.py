#!/usr/bin/env python3
"""Optional Google Workspace calendar adapter for prompt-on-change.

Core detect/escalate works without this module's CLI. Calendar actions call
gws_get_event / gws_patch_event / gws_delete_event. Bind the binary and token
with GWS_PATH and GOOGLE_WORKSPACE_CLI_CREDENTIALS_FILE; there is no
/opt/data default.
"""

import json
import logging
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

log = logging.getLogger(__name__)

# Command or absolute path to the gws CLI.
GWS = os.environ.get("GWS_PATH", "gws")
TOKEN_FILE = os.environ.get("GOOGLE_WORKSPACE_CLI_CREDENTIALS_FILE", "")


def _gws_env() -> dict:
    """# Returns: env dict with PATH + optional credentials file injected."""
    env = os.environ.copy()
    gws_path = Path(GWS)
    if gws_path.is_absolute() or "/" in str(GWS):
        env["PATH"] = str(gws_path.parent) + ":" + env.get("PATH", "")
    if TOKEN_FILE:
        env["GOOGLE_WORKSPACE_CLI_CREDENTIALS_FILE"] = TOKEN_FILE
    return env


def gws_get_event(event_id: str, calendar_id: str = "primary") -> dict | None:
    """GET a calendar event via gws CLI. Returns event dict or None on any failure."""
    # Args: event_id str, calendar_id str. Returns: dict | None
    if not event_id:
        log.error("gws_get_event: empty event_id")
        return None
    params = json.dumps({"calendarId": calendar_id, "eventId": event_id})
    try:
        result = subprocess.run(
            [GWS, "calendar", "events", "get", "--params", params, "--format", "json"],
            capture_output=True, text=True, env=_gws_env(), timeout=30,
        )
    except Exception as exc:
        log.error(f"gws_get_event({event_id}): subprocess failed: {exc}")
        return None
    # Fail closed on nonzero returncode — do not treat junk stdout as calendar state.
    if result.returncode != 0:
        stderr_snip = (result.stderr or "")[:200]
        err_lower = f"{result.stdout or ''}\n{result.stderr or ''}".lower()
        if any(s in err_lower for s in ("auth", "unauthorized", "permission", "credential", "token")):
            kind = "auth"
        elif any(s in err_lower for s in ("notfound", "not_found", "not found", "404")):
            kind = "not_found"
        elif any(s in err_lower for s in ("timeout", "timed out", "deadline")):
            kind = "timeout"
        else:
            kind = "error"
        log.error(
            f"gws_get_event({event_id}): gws exited {result.returncode} ({kind}): {stderr_snip}"
        )
        return None
    try:
        stdout = result.stdout
        idx = stdout.find("{")
        if idx < 0:
            log.warning(f"gws_get_event({event_id}): no JSON in response")
            return None
        data = json.loads(stdout[idx:])
        if "error" in data:
            log.error(f"gws_get_event({event_id}): {data['error']}")
            return None
        return data
    except json.JSONDecodeError:
        log.error(f"gws_get_event({event_id}): could not parse JSON")
        return None


def gws_patch_event(event_id: str, patch: dict, calendar_id: str = "primary") -> bool:
    """PATCH a calendar event via gws CLI. Returns True on success."""
    # Args: event_id str, patch dict, calendar_id str. Returns: bool
    if not event_id:
        log.warning("gws_patch_event: empty event_id, skipping")
        return False
    if not patch:
        log.warning("gws_patch_event: empty patch dict, skipping")
        return False
    params = json.dumps({"calendarId": calendar_id, "eventId": event_id})
    body = json.dumps(patch)
    try:
        result = subprocess.run(
            [GWS, "calendar", "events", "patch", "--params", params,
             "--json", body, "--format", "json"],
            capture_output=True, text=True, env=_gws_env(), timeout=30,
        )
    except Exception as exc:
        log.error(f"gws_patch_event({event_id}): subprocess failed: {exc}")
        return False

    if result.returncode != 0:
        log.error(f"gws_patch_event({event_id}): gws exited {result.returncode}: {result.stderr[:200]}")
        return False
    # Check JSON body for error key (gws can exit 0 with {"error": ...})
    try:
        stdout = result.stdout
        idx = stdout.find("{")
        if idx >= 0:
            data = json.loads(stdout[idx:])
            if "error" in data:
                log.error(f"gws_patch_event({event_id}): API error: {data['error']}")
                return False
    except json.JSONDecodeError:
        pass  # Non-JSON response on success is fine (empty body)
    log.info(f"gws_patch_event({event_id}): patched successfully")
    return True


def _is_not_found_delete_error(stdout: str, stderr: str) -> bool:
    """Return whether a delete failure is an idempotent not-found response."""
    error_text = f"{stdout or ''}\n{stderr or ''}".lower()
    if any(signal in error_text for signal in (
        "auth", "permission", "forbidden", "unauthorized", "credential", "token",
    )):
        return False
    if any(signal in error_text for signal in ("notfound", "not_found", "not found", "404")):
        return True

    try:
        start = (stdout or "").find("{")
        data = json.loads((stdout or "")[start:]) if start >= 0 else {}
    except json.JSONDecodeError:
        return any(signal in error_text for signal in ("already deleted", "event deleted", "event gone"))

    error = data.get("error", {}) if isinstance(data, dict) else {}
    if isinstance(error, dict):
        code = str(error.get("code", ""))
        status = str(error.get("status", "")).lower()
        message = str(error.get("message", "")).lower()
    else:
        code = ""
        status = ""
        message = str(error).lower()
    if code in ("404", "410") or status in ("notfound", "not_found", "gone", "deleted"):
        return True
    return any(signal in message for signal in (
        "notfound", "not_found", "not found", "404", "deleted", "gone",
    ))


def gws_delete_event(event_id: str, calendar_id: str = "primary") -> bool:
    """DELETE a calendar event via gws CLI. Returns True on success."""
    # Args: event_id str, calendar_id str. Returns: bool
    if not event_id:
        log.warning("gws_delete_event: empty event_id, skipping")
        return False
    params = json.dumps({"calendarId": calendar_id, "eventId": event_id})
    try:
        result = subprocess.run(
            [GWS, "calendar", "events", "delete", "--params", params, "--format", "json"],
            capture_output=True, text=True, env=_gws_env(), timeout=30,
        )
    except Exception as exc:
        log.error(f"gws_delete_event({event_id}): subprocess failed: {exc}")
        return False

    not_found = _is_not_found_delete_error(result.stdout, result.stderr)
    if result.returncode != 0:
        if not_found:
            log.info(f"gws_delete_event({event_id}): event already absent; treating delete as successful")
            return True
        log.error(f"gws_delete_event({event_id}): gws exited {result.returncode}")
        return False
    # Check JSON body for error key (gws can exit 0 with {"error": ...})
    try:
        stdout = result.stdout
        idx = stdout.find("{")
        if idx >= 0:
            data = json.loads(stdout[idx:])
            if "error" in data:
                if not_found:
                    log.info(f"gws_delete_event({event_id}): event already absent; treating delete as successful")
                    return True
                log.error(f"gws_delete_event({event_id}): API error: {data['error']}")
                return False
    except json.JSONDecodeError:
        pass  # Non-JSON response on success is fine (empty body)
    log.info(f"gws_delete_event({event_id}): deleted successfully")
    return True


def write_health(health_file: str | Path, status: str, config_name: str = "", detail: str = ""):
    """Write health status to a JSON file (atomic: tmp → rename)."""
    # Args: health_file str|Path, status str, config_name str, detail str. Returns: None (logs on failure)
    try:
        health_file = Path(health_file)
        health_file.parent.mkdir(parents=True, exist_ok=True)
        health = {
            "status": status,
            "config": config_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "detail": detail,
        }
        tmp = health_file.with_suffix(".tmp")
        tmp.write_text(json.dumps(health, indent=2) + "\n")
        tmp.replace(health_file)
    except Exception as exc:
        log.error(f"write_health({health_file}): failed: {exc}")
