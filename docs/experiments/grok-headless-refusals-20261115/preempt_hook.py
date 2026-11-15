#!/usr/bin/env python3
"""Prototype Grok PreToolUse hook (probe only): deny, with a reason the model reads, a shell command that Grok 1.0.77's
headless auto mode would refuse before running it.

Grok's refusal of such a command cannot be answered in a headless run, so it cancels the turn and ends the session. A
PreToolUse deny is reported to the model instead, and the turn goes on (10-hooks.md, "Apply the decision"). The shapes
come from analyze.floor_shapes, which the 2026-11-15 probes calibrated against Grok 1.0.77. Any other command, any
failure and any non-shell tool get no opinion, so Grok's own checks decide as before.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

REASON = ("Not run. Grok's headless permission check would refuse this command before it ran, and that refusal ends "
          "the session, because it cannot tell which files the command writes ({shapes}). Rewrite it so that every "
          "file it writes is named by a literal absolute path: no $VAR, ${{...}} or $(...) in a mkdir, cp, mv, rm, tee "
          "or tar -C target; no relative write after a cd (use git -C and absolute paths instead); and no backtick "
          "inside double quotes (put Python that reads a ``` block in a script file). Or write the script to a file "
          "with your file tool and run it with one plain command.")
SHAPE_WORDS = {"var-write": "a written path holds a shell expansion", "cd-relative-write": "a relative path is written "
               "after a cd", "backtick-in-dq": "a backtick inside double quotes"}


def main() -> int:
    try:
        from analyze import floor_shapes
        payload = json.loads(sys.stdin.read() or "{}")
        if payload.get("toolName") != "run_terminal_command" or payload.get("toolInputTruncated"):
            return 0
        command = (payload.get("toolInput") or {}).get("command") or ""
        shapes = floor_shapes(command, payload.get("workspaceRoot") or payload.get("cwd"))
        if shapes:
            print(json.dumps({"decision": "deny",
                              "reason": REASON.format(shapes="; ".join(SHAPE_WORDS[s] for s in shapes))}))
    except Exception:  # noqa: BLE001 - a broken hook must never block: no opinion
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
