#!/usr/bin/env python3
"""External Tic-Tac-Toe behavioral oracle for ShipLoop E2E trials.

This program deliberately does not emulate Google Apps Script, choose DOM
selectors, start a browser, inspect product source, or alter the candidate.
It delegates that product-specific work to a *read-only UI-driver adapter*.
The adapter is an explicit JSON argv supplied with ``--driver`` and must drive
the real locally served application.  It receives exactly one JSON request on
stdin::

    {"repo": "/candidate", "actions": [{"type": "reset"},
     {"type": "move", "cell": 0}]}

and emits exactly one JSON object on stdout with one observation per action::

    {"observations": [{"board": ["", ...], "active_player": "X",
      "outcome": "playing", "legal_highlights": [0, ...],
      "recommended_move": 0}]}

The oracle compares those externally returned observations against independent
game rules.  It cannot prove that an adapter actually used a browser; adapter
provenance is therefore an execution boundary, not a claim of a universal GAS
browser bridge.  If the adapter cannot make the product observable, this
verifier records the affected behavioral check as unverified.

Adapter stdout and stderr are captured only in private temporary files, polled
against the configured byte ceiling while the adapter runs, then deleted.  The
receipt retains canonical protocol observations and hashes, never raw streams.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
from typing import Any


HERE = Path(__file__).resolve().parent
ORACLE_VERSION = "shiploop-e2e-tictactoe-oracle/1"
RECEIPT_SCHEMA = "shiploop-e2e-receipt/1"
WIN_LINES = ((0, 1, 2), (3, 4, 5), (6, 7, 8), (0, 3, 6), (1, 4, 7),
             (2, 5, 8), (0, 4, 8), (2, 4, 6))
OUTCOMES = frozenset(("playing", "X", "O", "draw"))
BASELINE_DELTA_CHECKS = frozenset(("previous-behavior-preserved",
                                  "feature-before-absent-or-already-satisfied",
                                  "feature-passes-after-when-eligible"))
DRIVER_POLL_SECONDS = 0.02
DRIVER_TERM_GRACE_SECONDS = 0.10
DRIVER_KILL_GRACE_SECONDS = 0.50


class DriverError(RuntimeError):
    """A safe-to-record UI-driver invocation or protocol failure."""


def _json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_json_bytes(value) + b"\n")


def _other(player: str) -> str:
    return "O" if player == "X" else "X"


def _winner(board: list[str]) -> str | None:
    for a, b, c in WIN_LINES:
        if board[a] and board[a] == board[b] == board[c]:
            return board[a]
    return None


def _outcome(board: list[str]) -> str:
    return _winner(board) or ("draw" if all(board) else "playing")


def _empty_cells(board: list[str]) -> list[int]:
    return [index for index, value in enumerate(board) if not value]


def _reference_after(state: dict[str, Any], action: dict[str, Any]) -> dict[str, Any]:
    """Apply public Tic-Tac-Toe rules without consulting adapter output."""
    if action["type"] == "reset":
        return {"board": [""] * 9, "active_player": "X", "outcome": "playing"}
    board = list(state["board"])
    player = state["active_player"]
    if state["outcome"] == "playing" and board[action["cell"]] == "":
        board[action["cell"]] = player
        outcome = _outcome(board)
        return {"board": board, "active_player": _other(player) if outcome == "playing" else player,
                "outcome": outcome}
    return {"board": board, "active_player": player, "outcome": state["outcome"]}


def _base_actions() -> list[dict[str, Any]]:
    # Includes alternation, occupied/terminal attempts, a win, a draw, and reset.
    return ([{"type": "reset"}]
            + [{"type": "move", "cell": cell} for cell in (0, 0, 3, 1, 4, 2, 8)]
            + [{"type": "reset"}]
            + [{"type": "move", "cell": cell} for cell in (0, 1, 2, 4, 3, 5, 7, 6, 8)]
            + [{"type": "reset"}])


def _guidance_actions() -> list[dict[str, Any]]:
    return ([{"type": "reset"}]
            + [{"type": "move", "cell": cell} for cell in (0, 4, 0, 8, 1)]
            + _base_actions())


def _best_move_actions() -> list[dict[str, Any]]:
    # At indexes 4 and 9, X respectively has one winning move (2) and one block (5).
    return ([{"type": "reset"}]
            + [{"type": "move", "cell": cell} for cell in (0, 3, 1, 4)]
            + [{"type": "reset"}]
            + [{"type": "move", "cell": cell} for cell in (0, 3, 8, 4)]
            + _base_actions())


def _canonical_observation(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise DriverError("observation-not-object")
    board = value.get("board")
    if not isinstance(board, list) or len(board) != 9 or any(cell not in ("", "X", "O") for cell in board):
        raise DriverError("invalid-board")
    active = value.get("active_player")
    if active not in ("X", "O", None):
        raise DriverError("invalid-active-player")
    outcome = value.get("outcome")
    if outcome not in OUTCOMES:
        raise DriverError("invalid-outcome")
    highlights = value.get("legal_highlights")
    if (not isinstance(highlights, list) or any(type(cell) is not int or cell not in range(9) for cell in highlights)
            or len(set(highlights)) != len(highlights)):
        raise DriverError("invalid-legal-highlights")
    recommendation = value.get("recommended_move")
    if recommendation is not None and (type(recommendation) is not int or recommendation not in range(9)):
        raise DriverError("invalid-recommended-move")
    return {"board": board, "active_player": active, "outcome": outcome,
            "legal_highlights": highlights, "recommended_move": recommendation}


def _parse_driver_argv(value: str) -> list[str]:
    try:
        argv = json.loads(value)
    except json.JSONDecodeError as exc:
        raise ValueError("--driver must be a JSON argv array") from exc
    if (not isinstance(argv, list) or not argv or len(argv) > 64
            or any(not isinstance(item, str) or not item or "\x00" in item for item in argv)
            or sum(len(item) for item in argv) > 16_384):
        raise ValueError("--driver must be a bounded non-empty JSON argv array of strings")
    return argv


def _stream_size(path: Path) -> int:
    try:
        return path.stat().st_size
    except FileNotFoundError:
        return 0


def _stop_driver_group(process: subprocess.Popen[bytes]) -> None:
    """End the adapter's private process group, including conventional children."""
    if os.name != "posix":
        if process.poll() is None:
            process.kill()
        try:
            process.wait(timeout=DRIVER_KILL_GRACE_SECONDS)
        except subprocess.TimeoutExpired:
            pass
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except (ProcessLookupError, PermissionError):
        return
    time.sleep(DRIVER_TERM_GRACE_SECONDS)
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass
    try:
        process.wait(timeout=DRIVER_KILL_GRACE_SECONDS)
    except subprocess.TimeoutExpired:
        pass


def _wait_for_driver(
    process: subprocess.Popen[bytes], stdout_path: Path, stderr_path: Path,
    timeout: float, max_output_bytes: int,
) -> int:
    """Poll file-backed streams before output can be read into memory."""
    deadline = time.monotonic() + timeout
    while process.poll() is None:
        if max(_stream_size(stdout_path), _stream_size(stderr_path)) > max_output_bytes:
            _stop_driver_group(process)
            raise DriverError("driver-output-exceeded-bound")
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            _stop_driver_group(process)
            raise DriverError("driver-timeout")
        time.sleep(min(DRIVER_POLL_SECONDS, remaining))
    # A driver may have started a same-group server or browser and exited.  Do
    # not leave that descendant alive or let it append to the temporary files.
    _stop_driver_group(process)
    if max(_stream_size(stdout_path), _stream_size(stderr_path)) > max_output_bytes:
        raise DriverError("driver-output-exceeded-bound")
    return process.returncode


def _invoke_driver(argv: list[str], repo: Path, actions: list[dict[str, Any]], timeout: float,
                   max_output_bytes: int) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    request = {"repo": str(repo), "actions": actions}
    request_bytes = _json_bytes(request)
    try:
        with tempfile.TemporaryDirectory(prefix="shiploop-e2e-driver-") as raw_directory:
            raw_root = Path(raw_directory)
            stdin_path = raw_root / "stdin.json"
            stdout_path = raw_root / "stdout.json"
            stderr_path = raw_root / "stderr.log"
            stdin_path.write_bytes(request_bytes)
            with (stdin_path.open("rb") as stdin_handle,
                  stdout_path.open("wb") as stdout_handle,
                  stderr_path.open("wb") as stderr_handle):
                process = subprocess.Popen(
                    argv, cwd=repo, stdin=stdin_handle, stdout=stdout_handle,
                    stderr=stderr_handle, start_new_session=os.name == "posix",
                )
                returncode = _wait_for_driver(
                    process, stdout_path, stderr_path, timeout, max_output_bytes
                )
            if returncode != 0:
                raise DriverError("driver-nonzero-exit")
            stdout = stdout_path.read_bytes()
            stderr = stderr_path.read_bytes()
    except DriverError:
        raise
    except OSError as exc:
        raise DriverError("driver-execution-error") from exc
    try:
        response = json.loads(stdout.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DriverError("driver-invalid-json") from exc
    observations = response.get("observations") if isinstance(response, dict) else None
    if not isinstance(observations, list) or len(observations) != len(actions):
        raise DriverError("driver-observation-count-mismatch")
    canonical = [_canonical_observation(observation) for observation in observations]
    metadata = {"request": request, "driver_stdout_sha256": _sha256_bytes(stdout),
                "driver_stderr_sha256": _sha256_bytes(stderr), "observation_count": len(canonical)}
    return canonical, metadata


def _rule_issues(
    actions: list[dict[str, Any]], observations: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    state = {"board": [""] * 9, "active_player": "X", "outcome": "playing"}
    expected_states: list[dict[str, Any]] = []
    issues: list[dict[str, Any]] = []
    for index, (action, observed) in enumerate(zip(actions, observations, strict=True)):
        state = _reference_after(state, action)
        expected_states.append(state)
        for field in ("board", "outcome"):
            if observed[field] != state[field]:
                issues.append({"index": index, "field": field, "reason": "reference-rule-mismatch"})
        if state["outcome"] == "playing" and observed["active_player"] != state["active_player"]:
            issues.append({"index": index, "field": "active_player", "reason": "turn-mismatch"})
    return expected_states, issues


def _immediate_wins(board: list[str], player: str) -> list[int]:
    matches: list[int] = []
    for cell in _empty_cells(board):
        next_board = list(board)
        next_board[cell] = player
        if _winner(next_board) == player:
            matches.append(cell)
    return matches


def _guidance_issues(expected: list[dict[str, Any]], observations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for index, (state, observed) in enumerate(zip(expected, observations, strict=True)):
        legal = _empty_cells(state["board"]) if state["outcome"] == "playing" else []
        if sorted(observed["legal_highlights"]) != legal:
            issues.append({"index": index, "field": "legal_highlights", "reason": "does-not-match-empty-cells"})
    return issues


def _best_move_issues(expected: list[dict[str, Any]], observations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for index, (state, observed) in enumerate(zip(expected, observations, strict=True)):
        if state["outcome"] != "playing":
            if observed["recommended_move"] is not None:
                issues.append({"index": index, "field": "recommended_move", "reason": "terminal-game-has-hint"})
            continue
        recommendation = observed["recommended_move"]
        legal = _empty_cells(state["board"])
        if recommendation not in legal:
            issues.append({"index": index, "field": "recommended_move", "reason": "not-one-legal-move"})
            continue
        wins = _immediate_wins(state["board"], state["active_player"])
        blocks = _immediate_wins(state["board"], _other(state["active_player"]))
        required = wins or blocks
        if required and recommendation not in required:
            issues.append({"index": index, "field": "recommended_move", "reason": "missed-immediate-win-or-block"})
    return issues


def _scenario_step(step_id: str) -> dict[str, Any]:
    if not isinstance(step_id, str):
        raise ValueError("this verifier requires a string Tic-Tac-Toe step ID")
    catalog = json.loads((HERE / "scenarios.json").read_text(encoding="utf-8"))
    matches = [
        step for family in catalog.get("scenarios", [])
        for step in family.get("steps", []) if step.get("id") == step_id
    ]
    if len(matches) != 1 or step_id not in {"ttt-create", "ttt-guidance", "ttt-best-move"}:
        raise ValueError("this verifier accepts one Tic-Tac-Toe scenario step")
    return matches[0]


def _context(environ: dict[str, str]) -> tuple[dict[str, Any], Path, Path, Path, dict[str, Any]]:
    required_env = ("SHIPLOOP_E2E_TRIAL", "SHIPLOOP_E2E_REPO", "SHIPLOOP_E2E_EVIDENCE")
    if any(not environ.get(name) for name in required_env):
        raise ValueError("SHIPLOOP_E2E_TRIAL, SHIPLOOP_E2E_REPO, and SHIPLOOP_E2E_EVIDENCE are required")
    trial = Path(environ["SHIPLOOP_E2E_TRIAL"]).resolve()
    repo = Path(environ["SHIPLOOP_E2E_REPO"]).resolve()
    evidence = Path(environ["SHIPLOOP_E2E_EVIDENCE"]).resolve()
    result = json.loads((trial / "result.json").read_text(encoding="utf-8"))
    step = _scenario_step(result.get("step_id", ""))
    if result.get("required_checks") not in (None, step["required_checks"]):
        raise ValueError("trial required checks do not match scenarios.json")
    if not isinstance(result.get("trial_id"), str) or not isinstance(result.get("candidate_digest"), str):
        raise ValueError("trial result lacks receipt bindings")
    evidence.mkdir(parents=True, exist_ok=True)
    return result, trial, repo, evidence, step


def _unverified_row(check_id: str, detail: str) -> dict[str, Any]:
    return {"id": check_id, "status": "unverified", "evidence": [], "details": detail}


def _unsupported_check_row(check_id: str) -> dict[str, Any]:
    if check_id in BASELINE_DELTA_CHECKS:
        return _unverified_row(
            check_id,
            "no external pre-feature UI-driver trace was supplied; "
            "source and run metadata do not prove a baseline delta",
        )
    if check_id == "incremental-integration-review":
        return _unverified_row(check_id, "a behavior trace cannot establish source or product lineage")
    return _unverified_row(check_id, "not assessed by this behavior-only verifier")


def verify(environ: dict[str, str], driver: list[str], timeout: float, max_output_bytes: int) -> dict[str, Any]:
    """Run exactly the step's external trace and return a receipt object."""
    result, _trial, repo, evidence, step = _context(environ)
    target = {"ttt-create": ("ttt-base-game", _base_actions, None),
              "ttt-guidance": ("ttt-turn-indicator-and-legal-highlights", _guidance_actions, _guidance_issues),
              "ttt-best-move": ("ttt-best-move-hint", _best_move_actions, _best_move_issues)}[step["id"]]
    check_id, action_factory, extension_check = target
    actions = action_factory()
    trace_path = evidence / "tictactoe" / f"{step['id']}-trace.json"
    try:
        observations, metadata = _invoke_driver(driver, repo, actions, timeout, max_output_bytes)
        expected, issues = _rule_issues(actions, observations)
        if extension_check is not None:
            issues.extend(extension_check(expected, observations))
        trace = {"schema": "shiploop-e2e-tictactoe-trace/1", "oracle": ORACLE_VERSION,
                 "step_id": step["id"], "adapter_boundary": "external-ui-driver", **metadata,
                 "observations": observations, "issues": issues}
        _write_json(trace_path, trace)
        evidence_rows = [{
            "path": str(trace_path.relative_to(evidence)), "sha256": _sha256_file(trace_path)
        }]
        target_row = {"id": check_id, "status": "pass" if not issues else "fail", "evidence": evidence_rows,
                      "details": "external UI-driver trace matched independent rules" if not issues else issues}
    except DriverError as exc:
        _write_json(trace_path, {"schema": "shiploop-e2e-tictactoe-trace/1", "oracle": ORACLE_VERSION,
                                 "step_id": step["id"], "adapter_boundary": "external-ui-driver",
                                 "driver_status": "unverified", "reason": str(exc)})
        target_row = {
            "id": check_id,
            "status": "unverified",
            "evidence": [{"path": str(trace_path.relative_to(evidence)), "sha256": _sha256_file(trace_path)}],
            "details": f"external UI-driver could not produce a complete trace: {exc}",
        }

    rows = [target_row if required == check_id else _unsupported_check_row(required)
            for required in step["required_checks"]]
    return {"schema": RECEIPT_SCHEMA, "trial_id": result["trial_id"],
            "candidate_digest": result["candidate_digest"], "baseline_digest": result.get("baseline_digest"),
            "verifier": ORACLE_VERSION, "step_id": step["id"], "checks": rows,
            "incremental_review": {"status": "unverified", "evidence": [],
                                   "details": "behavior trace cannot establish incremental lineage or baseline deltas"}}


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify one ShipLoop Tic-Tac-Toe trial through an external UI-driver adapter."
    )
    parser.add_argument("--driver", required=True, help="bounded JSON argv for the read-only UI-driver adapter")
    parser.add_argument("--timeout", type=float, default=20.0, help="adapter deadline in seconds (1-120, default: 20)")
    parser.add_argument(
        "--max-output-bytes", type=int, default=1_048_576,
        help="maximum stdout or stderr bytes (default: 1048576)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    if not 0 < args.timeout <= 120 or not 0 < args.max_output_bytes <= 16 * 1024 * 1024:
        raise SystemExit("adapter bounds must be positive and within documented limits")
    try:
        receipt = verify(dict(os.environ), _parse_driver_argv(args.driver), args.timeout, args.max_output_bytes)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"verify-tictactoe: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
