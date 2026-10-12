#!/usr/bin/env python3
"""Session-scoped Claude Code hooks for retained experiment evidence."""
from __future__ import annotations

import argparse
import json
import shlex
import sys
import time
import uuid
from pathlib import Path

HOOK_EVENTS = ("SessionStart", "SubagentStart", "SubagentStop", "SessionEnd")


def _write_exclusive(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(payload)
        stream.flush()


def record_hook(directory, *, raw_input=None, observed_epoch=None):
    """Retain the hook's exact stdin bytes and parsed payload in one immutable record."""
    raw = sys.stdin.buffer.read() if raw_input is None else bytes(raw_input)
    try:
        payload = json.loads(raw.decode("utf-8"))
        parse_error = None
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        payload = None
        parse_error = f"{type(exc).__name__}: {exc}"
    record = {
        "schema": "ask-agent.claude-hook/v1",
        "observed_epoch": time.time() if observed_epoch is None else observed_epoch,
        "raw_input": raw.decode("utf-8", errors="replace"),
        "payload": payload,
    }
    if parse_error:
        record["parse_error"] = parse_error
    target = Path(directory) / f"{time.time_ns()}-{uuid.uuid4().hex}.json"
    _write_exclusive(target, (json.dumps(record, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
    return target


def settings_object(hooks_directory, *, script_path=None, python_path=None):
    """Return run-local hook settings; no global Claude settings are read or changed."""
    hook_directory = Path(hooks_directory).resolve()
    script = Path(script_path or __file__).resolve()
    python = str(Path(python_path or sys.executable).resolve())
    command = shlex.join([python, "-B", str(script), "--record", "--directory", str(hook_directory)])
    return {
        "hooks": {
            event: [{"hooks": [{"type": "command", "command": command}]}]
            for event in HOOK_EVENTS
        }
    }


def write_settings(path, hooks_directory, *, script_path=None, python_path=None):
    target = Path(path)
    payload = (json.dumps(
        settings_object(hooks_directory, script_path=script_path, python_path=python_path),
        indent=2,
    ) + "\n").encode("utf-8")
    _write_exclusive(target, payload)
    return target


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--record", action="store_true")
    parser.add_argument("--directory", required=True)
    args = parser.parse_args(argv)
    if not args.record:
        parser.error("--record is required")
    try:
        record_hook(args.directory)
    except OSError as exc:
        print(f"hook evidence write failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
