#!/usr/bin/env python3
"""Exercise the deployed Battleship Lightning tab in a fresh authenticated browser.

This is deliberately an independent live UI check: it does not inspect candidate
markup or trust a builder-authored receipt. The Salesforce frontdoor URL is held
in memory and passed to the browser helper over stdin only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import unittest
import uuid
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent
SAFE_BROWSER_STAGES = frozenset({
    "authenticate", "route", "render", "fire-shot-count", "fire-feedback",
    "play", "game-over", "reset", "controller", "browser",
})
SAFE_BROWSER_REASONS = frozenset({
    "route-invalid", "initial-board-invalid", "shot-count-mismatch",
    "cell-state-mismatch", "feedback-mismatch", "ships-left-mismatch",
    "unfired-count-mismatch", "premature-game-over", "game-over-missing",
    "game-summary-mismatch", "game-not-finished", "reset-state-invalid",
    "stale-game-over", "controller-config-invalid", "controller-proof-missing",
    "controller-new-game-missing", "controller-initial-state-mismatch",
    "controller-fire-missing", "controller-response-missing",
    "controller-response-id-mismatch", "controller-response-unsuccessful",
    "controller-response-invalid", "controller-coordinate-mismatch",
    "controller-last-shot-mismatch", "controller-last-shot-coordinate-mismatch",
    "controller-counters-mismatch", "controller-game-over-mismatch", "ui-check-failed",
})
CHECK_PHASES = frozenset({"builder", "final", "product_at_stop", "unknown"})
CONTROLLER_SHIP_SIZES = {
    "carrier": 5, "battleship": 4, "cruiser": 3, "submarine": 3, "destroyer": 2,
}


def check_phase() -> str:
    """Return the harness phase as a bounded, additive receipt value."""
    phase = os.environ.get("E2E_CHECK_PHASE", "unknown")
    return phase if phase in CHECK_PHASES else "unknown"


def valid_controller_action_id(value: object) -> bool:
    return (isinstance(value, str) and len(value) <= 128
            and re.fullmatch(r"[A-Za-z0-9._;:-]+", value) is not None)


def valid_controller_last_shot(value: object) -> bool:
    if not isinstance(value, dict):
        return False
    if not {"row", "col", "result", "ship", "size"}.issubset(value):
        return False
    row, column, result = value.get("row"), value.get("col"), value.get("result")
    if (type(row) is not int or not 0 <= row <= 9
            or type(column) is not int or not 0 <= column <= 9
            or not isinstance(result, str) or result not in {"hit", "miss", "sunk"}):
        return False
    ship, size = value.get("ship"), value.get("size")
    if result == "sunk":
        return isinstance(ship, str) and ship in CONTROLLER_SHIP_SIZES \
            and type(size) is int and size == CONTROLLER_SHIP_SIZES[ship]
    return ship is None and size is None


def validate_controller_proof(value: dict, *, prefix: str, dom_shots: list) -> str | None:
    """Validate only the normalized Apex proof fields needed to corroborate the DOM."""
    if value.get("controller_proof_scope") != "apex-controller-and-dom":
        return "controller-proof-missing"
    proof = value.get("controller_proof")
    if not isinstance(proof, dict):
        return "controller-proof-missing"
    if proof.get("controller_class") != f"{prefix}Controller":
        return "controller-config-invalid"

    initial = proof.get("new_game")
    if not isinstance(initial, dict):
        return "controller-new-game-missing"
    method = initial.get("method")
    if not isinstance(method, str) or method.lower() not in {"newgame", "reset"}:
        return "controller-new-game-missing"
    request_id, response_id = initial.get("request_id"), initial.get("response_id")
    if (not valid_controller_action_id(request_id) or not valid_controller_action_id(response_id)
            or request_id != response_id):
        return "controller-response-id-mismatch"
    if (initial.get("last_shot") is not None
            or type(initial.get("shots")) is not int or initial["shots"] != 0
            or type(initial.get("ships_left")) is not int or initial["ships_left"] != 5
            or type(initial.get("game_over")) is not bool or initial["game_over"] is not False):
        return "controller-initial-state-mismatch"

    proof_shots = proof.get("shots")
    if not isinstance(proof_shots, list) or len(proof_shots) != len(dom_shots):
        return "controller-fire-missing"
    for index, (proof_shot, dom_shot) in enumerate(zip(proof_shots, dom_shots), start=1):
        if not isinstance(proof_shot, dict) or not isinstance(dom_shot, dict):
            return "controller-response-invalid"
        if not isinstance(proof_shot.get("method"), str) or proof_shot["method"].lower() != "fire":
            return "controller-response-invalid"
        request_id, response_id = proof_shot.get("request_id"), proof_shot.get("response_id")
        if (not valid_controller_action_id(request_id) or not valid_controller_action_id(response_id)
                or request_id != response_id):
            return "controller-response-id-mismatch"

        row, column = proof_shot.get("row"), proof_shot.get("column")
        if (type(row) is not int or type(column) is not int
                or row != dom_shot.get("row") or column != dom_shot.get("column")):
            return "controller-coordinate-mismatch"
        last_shot = proof_shot.get("last_shot")
        if not valid_controller_last_shot(last_shot):
            return "controller-response-invalid"
        if last_shot["row"] != dom_shot.get("row") or last_shot["col"] != dom_shot.get("column"):
            return "controller-last-shot-coordinate-mismatch"
        if last_shot["result"] != dom_shot.get("result"):
            return "controller-last-shot-mismatch"

        ships_left = dom_shot.get("ships_left_after")
        if (type(proof_shot.get("shots")) is not int or proof_shot["shots"] != index
                or type(proof_shot.get("ships_left")) is not int
                or type(ships_left) is not int or proof_shot["ships_left"] != ships_left):
            return "controller-counters-mismatch"
        expected_game_over = ships_left == 0
        if (type(proof_shot.get("game_over")) is not bool
                or proof_shot["game_over"] is not expected_game_over):
            return "controller-game-over-mismatch"

    if not proof_shots or proof_shots[-1].get("game_over") is not True:
        return "controller-game-over-mismatch"
    return None


def project_controller_proof(proof: dict) -> dict:
    """Retain a closed proof projection; discard every unrecognized controller field."""
    def project_call(call: dict, *, include_coordinates: bool) -> dict:
        result = {key: call[key] for key in (
            "method", "request_id", "response_id", "shots", "ships_left", "game_over",
        )}
        if include_coordinates:
            result.update(row=call["row"], column=call["column"])
        last_shot = call["last_shot"]
        result["last_shot"] = None if last_shot is None else {
            key: last_shot[key] for key in ("row", "col", "result", "ship", "size")
        }
        return result

    return {
        "controller_class": proof["controller_class"],
        "new_game": project_call(proof["new_game"], include_coordinates=False),
        "shots": [project_call(shot, include_coordinates=True) for shot in proof["shots"]],
    }


def command_path(name: str) -> str | None:
    """Resolve a real host command, ignoring the model's run-local wrappers."""
    blocked = {os.environ.get("E2E_MODEL_BIN_DIR"), str(Path(os.environ.get("E2E_PLATFORM_DIR", "/nonexistent")) / "bin")}
    paths = [p for p in os.environ.get("PATH", "").split(os.pathsep) if p and p not in blocked]
    return shutil.which(name, path=os.pathsep.join(paths))


def runtime_env() -> dict:
    """Keep the authenticated subprocesses free of inherited runtime hooks."""
    return {key: value for key, value in os.environ.items()
            if not key.upper().startswith(("NODE_", "PLAYWRIGHT_", "NPM_CONFIG_"))
            and key not in {"BROWSER_EXECUTABLE_PATH", "DEBUG", "PWDEBUG"}}


def sf_json(argv: list[str], *, timeout: int = 60) -> dict:
    binary = command_path("sf")
    if not binary:
        raise RuntimeError("Salesforce CLI unavailable")
    try:
        proc = subprocess.run([binary, *argv], stdin=subprocess.DEVNULL, capture_output=True,
                              text=True, timeout=timeout, check=False, env=runtime_env())
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError("Salesforce CLI command failed") from exc
    if proc.returncode:
        raise RuntimeError("Salesforce CLI command failed")
    try:
        value = json.loads(proc.stdout)
    except (ValueError, TypeError) as exc:
        raise RuntimeError("Salesforce CLI returned invalid JSON") from exc
    if not isinstance(value, dict) or value.get("status") not in (0, None):
        raise RuntimeError("Salesforce CLI returned an unsuccessful result")
    return value


def org_identity(org: str) -> dict:
    listing = sf_json(["org", "list", "--json"])
    result = listing.get("result", {})
    rows = []
    if isinstance(result, dict):
        rows.extend(result.get("nonScratchOrgs", []) if isinstance(result.get("nonScratchOrgs"), list) else [])
        rows.extend(result.get("scratchOrgs", []) if isinstance(result.get("scratchOrgs"), list) else [])
    row = next((item for item in rows if isinstance(item, dict) and (item.get("alias") == org or item.get("username") == org)), None)
    if not row or not isinstance(row.get("orgId"), str) or not isinstance(row.get("instanceUrl"), str):
        raise RuntimeError("Requested Salesforce org identity unavailable")
    host = urlparse(row["instanceUrl"]).hostname
    suffix = ".my.salesforce.com"
    if not host or not host.lower().endswith(suffix):
        raise RuntimeError("Requested Salesforce org My Domain unavailable")
    lightning_host = host[:-len(suffix)].lower() + ".lightning.force.com"
    # Salesforce org ids are identifiers, not credentials; do not retain usernames.
    return {"alias": org, "org_id": row["orgId"], "lightning_host": lightning_host}


def frontdoor_url(org: str) -> str:
    response = sf_json(["org", "open", "--url-only", "--json", "--target-org", org])
    result = response.get("result")
    url = result.get("url") if isinstance(result, dict) else None
    if not isinstance(url, str) or not url.startswith("https://"):
        raise RuntimeError("Salesforce did not provide a frontdoor URL")
    return url


def candidate_fingerprint(root: Path) -> tuple[str | None, str]:
    digest = hashlib.sha256()
    base = root / "force-app"
    if not base.is_dir():
        raise RuntimeError("Salesforce DX metadata tree is unavailable")
    files = sorted(p for p in base.rglob("*") if p.is_file() and p.suffix.lower() in {".cls", ".xml", ".js", ".html", ".css"})
    if not files:
        raise RuntimeError("Salesforce DX metadata tree is empty")
    for path in files:
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    try:
        head = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], stdin=subprocess.DEVNULL,
                              capture_output=True, text=True, timeout=5, check=True).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        head = None
    return head, digest.hexdigest()


def latest_deploy_call(platform_dir: Path, org: str, prefix: str) -> dict | None:
    """Return the local allowed guard record; the guard retains no remote Salesforce job id."""
    log = platform_dir / "sf-calls.jsonl"
    if not log.is_file():
        return None
    try:
        rows = [json.loads(line) for line in log.read_text(errors="replace").splitlines() if line.strip()]
    except (OSError, ValueError):
        return None
    starts = [row for row in rows if isinstance(row, dict) and row.get("argv", [])[:3] == ["project", "deploy", "start"]
              and row.get("decision") == "allowed" and row.get("org") == org and row.get("prefix") == prefix]
    if not starts:
        return None
    row = starts[-1]
    return {key: row.get(key) for key in ("call", "ts", "decision", "argv")}


def validate_observation(value: object, *, expected_host: str, prefix: str) -> list[str]:
    if not isinstance(value, dict):
        return ["browser-result-invalid"]
    errors = []
    expected = {"initial_cells": 100, "initial_unique_cells": 100,
                "initial_labels_matched": True, "initial_all_enabled": True,
                "initial_shots": 0, "initial_ships": 5,
                "reset_cells": 100, "reset_unique_cells": 100,
                "reset_labels_matched": True, "reset_all_enabled": True,
                "reset_shots": 0, "reset_ships": 5}
    for key, want in expected.items():
        if value.get(key) != want:
            errors.append(f"ui-{key.replace('_', '-')}-mismatch")
    if value.get("reset_cell_enabled") is not True:
        errors.append("ui-reset-cell-disabled")
    if expected_host and value.get("route_host") != expected_host:
        errors.append("ui-route-host-mismatch")
    if value.get("route_path") != f"/lightning/n/{prefix}_Board":
        errors.append("ui-route-path-mismatch")
    if not isinstance(value.get("browser_version"), str) or not value["browser_version"].strip():
        errors.append("ui-browser-version-missing")

    shots = value.get("shot_observations")
    if not isinstance(shots, list):
        errors.append("ui-shot-observations-missing")
        shots = []
    if not 17 <= len(shots) <= 100:
        errors.append("ui-shot-count-mismatch")

    observed_sinks = 0
    observed_hits = 0
    expected_ships = 5
    seen_cells = set()
    shots_well_formed = True
    for index, shot in enumerate(shots, start=1):
        if not isinstance(shot, dict):
            shots_well_formed = False
            continue
        row = shot.get("row")
        column = shot.get("column")
        result = shot.get("result")
        if (type(shot.get("shot_index")) is not int or shot.get("shot_index") != index
                or type(row) is not int or not 0 <= row <= 9
                or type(column) is not int or not 0 <= column <= 9
                or type(shot.get("duration_ms")) is not int or shot["duration_ms"] < 0
                or not isinstance(result, str) or result not in {"hit", "miss", "sunk"}
                or type(shot.get("fired_cell_disabled")) is not bool):
            shots_well_formed = False
        if type(row) is int and type(column) is int:
            if (row, column) in seen_cells:
                errors.append("ui-shot-cell-repeat")
            seen_cells.add((row, column))
        if result == "sunk":
            observed_sinks += 1
            expected_ships -= 1
        if result in {"hit", "sunk"}:
            observed_hits += 1
        if type(shot.get("ships_left_after")) is not int or shot.get("ships_left_after") != expected_ships:
            errors.append("ui-ship-counter-sequence-mismatch")
        if type(shot.get("unfired_cells_after")) is not int or shot.get("unfired_cells_after") != 100 - index:
            errors.append("ui-unfired-count-sequence-mismatch")
    if not shots_well_formed:
        errors.append("ui-shot-observations-invalid")

    expected_summary = {
        "shots_played": len(shots),
        "sink_count": observed_sinks,
        "hit_or_sunk_shots": observed_hits,
        "final_ships_left": expected_ships,
        "final_unfired_cells": 100 - len(shots),
    }
    for key, want in expected_summary.items():
        if type(value.get(key)) is not int or value.get(key) != want:
            errors.append(f"ui-{key.replace('_', '-')}-mismatch")
    if observed_sinks != 5:
        errors.append("ui-sink-count-mismatch")
    if observed_hits != 17:
        errors.append("ui-hit-count-mismatch")
    if expected_ships != 0:
        errors.append("ui-final-ships-mismatch")

    message_counts = (
        "game_over_initial_message_count",
        "game_over_after_fourth_sink_message_count",
        "game_over_after_fourth_sink_new_message_count",
        "game_over_final_message_count",
        "game_over_final_new_message_count",
        "game_over_after_reset_message_count",
    )
    if any(type(value.get(key)) is not int or value.get(key) < 0 for key in message_counts):
        errors.append("ui-game-over-observation-missing")
    if (value.get("game_over_after_fourth_sink_new_message_count") != 0
            or type(value.get("game_over_final_message_count")) is not int
            or value.get("game_over_final_message_count", 0) < 1
            or type(value.get("game_over_final_new_message_count")) is not int
            or value.get("game_over_final_new_message_count", 0) < 1
            or value.get("game_over_new_message_observed") is not True
            or value.get("game_over_after_reset_matches_initial") is not True
            or value.get("game_over_after_reset_message_count") != value.get("game_over_initial_message_count")):
        errors.append("ui-game-over-observation-mismatch")
    controller_error = validate_controller_proof(value, prefix=prefix, dom_shots=shots)
    if controller_error:
        errors.append(controller_error)
    return errors


def scope_errors(argv: list[str]) -> list[str]:
    """Reject model-supplied duplicate scope options and malformed baked scope."""
    _, errors = parse_scope(argv)
    return errors


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
    if len(org_flags) != 1 or len(prefix_flags) != 1 or len(final_flags) > 1:
        return None, ["duplicate-scope-option"]
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._@-]{0,79}", args.org):
        return None, ["org-alias-invalid"]
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,39}", args.prefix):
        return None, ["metadata-prefix-invalid"]
    if args.check_name not in (None, "battleship-ui"):
        return None, ["check-name-mismatch"]
    return args, []


def run_check(org: str, prefix: str) -> int:
    phase = check_phase()
    platform_value = os.environ.get("E2E_PLATFORM_DIR")
    if not platform_value:
        print("battleship-ui: run-scoped platform directory unavailable", file=sys.stderr)
        return 1
    platform_dir = Path(platform_value).resolve()
    evidence_dir = platform_dir / "battleship-ui" / phase
    evidence_dir.mkdir(parents=True, exist_ok=True)
    check_id = uuid.uuid4().hex
    artifact_dir = evidence_dir / check_id
    artifact_dir.mkdir(mode=0o700)
    screenshot = artifact_dir / "screen.png"
    game_over_screenshot = artifact_dir / "game-over.png"
    receipt_path = artifact_dir / "observation.json"
    started = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    failure_record = None

    def persist_receipt(receipt: dict) -> tuple[str, str]:
        receipt_path.write_text(json.dumps(receipt, indent=2) + "\n")
        relative_path = receipt_path.relative_to(platform_dir).as_posix()
        receipt_sha256 = hashlib.sha256(receipt_path.read_bytes()).hexdigest()
        return relative_path, receipt_sha256

    try:
        identity = org_identity(org)
        head, digest = candidate_fingerprint(Path.cwd())
        # Keep the frontdoor URL in memory. The browser receives it over stdin;
        # it is never included in diagnostics or retained evidence.
        login = frontdoor_url(org)
        helper = HERE / "battleship_ui_browser.cjs"
        node = command_path("node")
        if not node:
            raise RuntimeError("Node.js unavailable")
        request = json.dumps({"login_url": login, "prefix": prefix,
                              "controller_class": prefix + "Controller", "require_controller": True,
                              "expected_lightning_host": identity["lightning_host"],
                              "screenshot": str(screenshot),
                              "game_over_screenshot": str(game_over_screenshot)})
        browser_env = runtime_env()
        try:
            proc = subprocess.run([node, str(helper)], input=request, capture_output=True, text=True,
                                  timeout=180, check=False, env=browser_env)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise RuntimeError("browser evaluation failed at browser") from exc
        if proc.returncode:
            try:
                failure = json.loads(proc.stdout)
            except ValueError:
                failure = None
            stage = failure.get("stage") if isinstance(failure, dict) else None
            reason_code = failure.get("reason") if isinstance(failure, dict) else None
            if stage not in SAFE_BROWSER_STAGES:
                stage = "browser"
            if reason_code not in SAFE_BROWSER_REASONS:
                reason_code = "ui-check-failed"
            failure_record = {"stage": stage, "reason_code": reason_code}
            for key, low, high in (("shot_index", 1, 100), ("row", 0, 9), ("column", 0, 9)):
                value = failure.get(key) if isinstance(failure, dict) else None
                if type(value) is int and low <= value <= high:
                    failure_record[key] = value
            raise RuntimeError(f"browser evaluation failed at {stage}: {reason_code}")
        try:
            observation = json.loads(proc.stdout)
        except ValueError as exc:
            raise RuntimeError("browser evaluation returned invalid data") from exc
        errors = validate_observation(observation, expected_host=identity["lightning_host"], prefix=prefix)
        if errors:
            controller_error = next((error for error in errors if error in SAFE_BROWSER_REASONS
                                     and error.startswith("controller-")), None)
            if controller_error:
                failure_record = {"stage": "controller", "reason_code": controller_error}
            raise RuntimeError(", ".join(errors))
        screenshot_hash = hashlib.sha256(screenshot.read_bytes()).hexdigest()
        game_over_screenshot_hash = hashlib.sha256(game_over_screenshot.read_bytes()).hexdigest()
        receipt = {
            "schema": "shiploop-battleship-ui-observation/3", "check_id": check_id,
            "run_scope": platform_dir.parent.name, "checked_at": started, "phase": phase,
            "org": identity, "prefix": prefix, "source_head": head,
            "candidate_metadata_sha256": digest,
            "deployment_id": None,
            "deployment_id_reason": "sf_guard retains the local deploy call only; no remote job id is available without an unpinned cache lookup",
            "deployment_guard_call": latest_deploy_call(platform_dir, org, prefix),
            "observations": {key: observation[key] for key in (
                "initial_cells", "initial_unique_cells", "initial_labels_matched", "initial_all_enabled",
                "initial_shots", "initial_ships", "shots_played", "sink_count", "hit_or_sunk_shots",
                "final_ships_left", "final_unfired_cells", "shot_observations",
                "game_over_initial_message_count", "game_over_after_fourth_sink_message_count",
                "game_over_after_fourth_sink_new_message_count", "game_over_final_message_count",
                "game_over_final_new_message_count", "game_over_new_message_observed",
                "game_over_after_reset_message_count", "game_over_after_reset_matches_initial",
                "reset_cells", "reset_unique_cells", "reset_cell_enabled",
                "reset_labels_matched", "reset_all_enabled", "reset_shots", "reset_ships",
                "route_host", "route_path", "browser_version")},
            "controller_proof_scope": observation["controller_proof_scope"],
            "controller_proof": project_controller_proof(observation["controller_proof"]),
            "screenshot_sha256": screenshot_hash,
            "screenshot_path": str(screenshot.relative_to(platform_dir)),
            "game_over_screenshot_sha256": game_over_screenshot_hash,
            "game_over_screenshot_path": str(game_over_screenshot.relative_to(platform_dir)),
        }
        receipt_relative_path, receipt_sha256 = persist_receipt(receipt)
        print(f"battleship-ui: PASS (complete game: {observation['shots_played']} shots, 5 sinks, game over shown, New game reset)")
        print(f"battleship-ui: receipt={receipt_relative_path} sha256={receipt_sha256}")
        return 0
    except Exception as exc:  # browser/CLI exceptions can contain secret-bearing URLs
        reason = str(exc) if isinstance(exc, RuntimeError) else "evaluation failed"
        safe = {"schema": "shiploop-battleship-ui-observation/3", "check_id": check_id,
                "run_scope": platform_dir.parent.name, "checked_at": started, "phase": phase, "status": "failed",
                "reason": reason[:200]}
        if failure_record is not None:
            safe["failure"] = failure_record
        receipt_relative_path, receipt_sha256 = persist_receipt(safe)
        print(f"battleship-ui: FAIL ({reason[:200]})", file=sys.stderr)
        print(f"battleship-ui: receipt={receipt_relative_path} sha256={receipt_sha256}", file=sys.stderr)
        return 1


def main() -> int:
    argv = sys.argv[1:]
    args, errors = parse_scope(argv)
    if errors:
        print("battleship-ui: invalid or duplicate org/prefix scope refused", file=sys.stderr)
        return 2
    class BattleshipUiTest(unittest.TestCase):
        def test_deployed_open_fire_reset(self):
            self.assertEqual(run_check(args.org, args.prefix), 0,
                             "The deployed UI check failed; see its reported stage.")

    result = unittest.TextTestRunner(verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(BattleshipUiTest))
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
