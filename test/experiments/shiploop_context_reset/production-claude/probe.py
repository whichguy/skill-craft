#!/usr/bin/env python3
"""Run the bounded Claude fresh-context experiment and write a compact receipt.

This uses the account's existing Claude CLI session/authentication.  It does
not use ``--bare``, bypass permissions, or attempt to add a sandbox policy the
Claude CLI cannot enforce.  The disposable fixture contains only a harmless
script that writes one marker file.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import secrets
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "skills/shiploop/scripts"))

from shiploop_host_claude import ClaudeTransport  # noqa: E402


INITIAL_RECEIPT = Path(__file__).with_name("receipt.json")
MARKER_TEXT = "fresh-session-script-ran\n"


def compact(turn):
    usage = turn.get("usage") or {}
    return {
        "status": turn["status"],
        "thread_id": turn["thread_id"],
        "turn_id": turn["turn_id"],
        "elapsed_seconds": turn["elapsed_seconds"],
        "error": turn["error"],
        "input_tokens": usage.get("input_tokens"),
        "cache_read_input_tokens": usage.get("cache_read_input_tokens"),
        "cache_creation_input_tokens": usage.get("cache_creation_input_tokens"),
        "output_tokens": usage.get("output_tokens"),
    }


def claude_version():
    completed = subprocess.run(
        ["claude", "--version"], text=True, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, timeout=30, check=False,
    )
    return completed.stdout.strip() if completed.returncode == 0 else "unavailable"


def continuation_assertion(turn, marker):
    """Return a failed assertion, rather than raising, when the script did not run."""
    marker_value = marker.read_text(encoding="utf-8") if marker.is_file() else None
    response = turn["text"].strip()
    return {
        "passed": (turn["status"] == "completed"
                   and "SCRIPT_EXECUTED" in response
                   and marker_value == MARKER_TEXT),
        "response": response,
        "marker": marker_value,
    }


def run(output: Path, timeout: float):
    if output.expanduser().resolve() == INITIAL_RECEIPT.resolve():
        raise ValueError("refusing to overwrite the initial Claude receipt; use verified-receipt.json")
    canary = "ROSEWOOD-" + secrets.token_hex(8).upper()
    recall_prompt = (
        "What is the exact test canary? Reply only the value if it is in this conversation; "
        "otherwise reply exactly UNKNOWN. Do not use tools."
    )
    recall_prompt_sha256 = hashlib.sha256(recall_prompt.encode("utf-8")).hexdigest()
    with tempfile.TemporaryDirectory(prefix="shiploop-claude-context-reset-") as temporary:
        fixture = Path(temporary)
        script = fixture / "continue.py"
        marker = fixture / "continuation-marker.txt"
        script.write_text(
            "from pathlib import Path\n"
            f"Path('continuation-marker.txt').write_text({MARKER_TEXT!r}, encoding='utf-8')\n"
            "print('SCRIPT_EXECUTED')\n",
            encoding="utf-8",
        )
        with ClaudeTransport(fixture, timeout=timeout) as host:
            retained_id = host.start_thread(fixture)
            seed = host.run_turn(
                retained_id,
                f"Remember the temporary test canary {canary}. Reply exactly ACK and do not use tools.",
            )
            retained = host.run_turn(
                retained_id,
                recall_prompt,
            )
            capabilities = host.capabilities
            permissions = host.permission_metadata

        # Reopening the transport makes the retained-session positive control
        # prove CLI persistence rather than local Python object state.
        with ClaudeTransport(fixture, timeout=timeout) as host:
            host.resume_thread(retained_id)
            retained_reopened = host.run_turn(retained_id, recall_prompt)
            fresh_id = host.start_thread(fixture)
            fresh = host.run_turn(fresh_id, recall_prompt)
            continuation = host.run_turn(
                fresh_id,
                "You are in a disposable test fixture. First inspect `continue.py`. It is a known one-file "
                "fixture and should only write `continuation-marker.txt` containing `fresh-session-script-ran` "
                "and print `SCRIPT_EXECUTED`. If its contents match that description, execute exactly "
                "`python3 continue.py` once. Then reply with the actual terminal stdout. Do no other work "
                "and do not use network access.",
            )

        assertion = {
            "seed_ack": {
                "passed": seed["status"] == "completed" and seed["text"].strip() == "ACK",
                "expected": "ACK",
                "actual": seed["text"].strip(),
            },
            "retained_same_session_recall": {
                "passed": retained["status"] == "completed" and retained["text"].strip() == canary,
                "expected": canary,
                "actual": retained["text"].strip(),
            },
            "retained_reopened_resume_positive_control": {
                "passed": (retained_reopened["status"] == "completed"
                           and retained_reopened["text"].strip() == canary),
                "expected": canary,
                "actual": retained_reopened["text"].strip(),
            },
            "fresh_identical_recall_forgets": {
                "passed": fresh["status"] == "completed" and fresh["text"].strip() == "UNKNOWN",
                "expected": "UNKNOWN",
                "actual": fresh["text"].strip(),
            },
            "fresh_script_continuation": continuation_assertion(continuation, marker),
        }
        receipt = {
            "schema": "shiploop-context-reset/production-claude/v2",
            "status": "passed" if all(value["passed"] for value in assertion.values()) else "failed",
            "claude_version": claude_version(),
            "fixture": "temporary directory removed after the receipt was written",
            "canary": canary,
            "identical_recall_prompt_sha256": recall_prompt_sha256,
            "transport": {
                "fresh_context": "new Claude --session-id",
                "retained_context": "Claude --resume same session id",
                "literal_clear": "not invoked; launcher starts a fresh session",
                "capabilities": capabilities,
                "permission_metadata": permissions,
            },
            "session_ids": {
                "retained": retained_id,
                "fresh": fresh_id,
            },
            "assertions": assertion,
            "turns": {
                "seed": compact(seed),
                "retained_same_session_recall": compact(retained),
                "retained_reopened_resume_recall": compact(retained_reopened),
                "fresh_identical_recall": compact(fresh),
                "fresh_same_session_continuation": compact(continuation),
            },
            "limitations": [
                "Claude CLI exposes no writable-root or network sandbox equivalent to Codex app-server.",
                "The adapter rejects requested writable roots and network denial rather than claiming enforcement.",
                "This is a bounded host transport experiment, not a full ShipLoop delivery run.",
            ],
        }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return receipt


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--timeout", type=float, default=300)
    args = parser.parse_args(argv)
    receipt = run(args.output, args.timeout)
    print(json.dumps({"status": receipt["status"], "output": str(args.output)}))
    return 0 if receipt["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
