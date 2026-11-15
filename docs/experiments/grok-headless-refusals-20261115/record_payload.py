#!/usr/bin/env python3
"""A PreToolUse hook that records what Grok's hook event says, for the payload-1077 batch.

Registered by hand in a probe profile (``home/.grok/hooks/log.json``, matcher ``run_terminal_command``) with
``PAYLOAD_LOG=<session>/payload.jsonl python3 record_payload.py`` as its command, and the session launched once with
``--permission-mode auto`` and once with ``bypassPermissions``. It keeps five fields of each event (the event, the
permission mode, the tool and the two folders) and gives no opinion, so the call runs as it would without it.
export_probes.py copies the first three into evidence/payloads.jsonl.
"""

import json
import os
import sys

data = sys.stdin.read()
with open(os.environ.get("PAYLOAD_LOG", "/dev/null"), "a") as handle:
    try:
        event = json.loads(data)
        handle.write(json.dumps({k: event.get(k) for k in ("hookEventName", "permissionMode", "toolName", "cwd",
                                                           "workspaceRoot")}) + "\n")
    except ValueError:
        handle.write("unparsed\n")
