#!/usr/bin/env python3
"""Copy the probe sessions' results into the repository's evidence, compact and redacted.

Usage: export_probes.py PROBE_ROOT EVIDENCE_DIR
Reads PROBE_ROOT/<batch>/results.jsonl (probe.py's output) and writes EVIDENCE_DIR/probes.jsonl: per session, the batch,
the case, the mode, the allow rules and hook, the command (the case folder written as {ROOT}), whether the model ran it
as asked, Grok's permission decision and wait, how the turn ended, the hook's deny if any, and the classifier verdict line.
Nothing else from the debug log is kept: it also holds the account's sign-in response.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

HOME = os.path.expanduser("~")
VERDICT = re.compile(r"classifier route completed tool=(\S+) verdict=(\S+) classifier_latency_ms=(\d+)")


def main() -> int:
    root, evidence = Path(sys.argv[1]), Path(sys.argv[2])
    rows = []
    for results in sorted(root.glob("*/results.jsonl")):
        batch = results.parent.name
        for line in results.read_text().splitlines():
            row = json.loads(line)

            def redact(text: str) -> str:
                text = re.sub(re.escape(str(results.parent)) + r"/[^/\s\"']+", "{ROOT}", text)
                return text.replace(HOME, "~")
            store = row.get("store") or []
            decision = next((s for s in store if s.get("type") == "permission_resolved"), None)
            ended = next((s for s in store if s.get("type") == "turn_ended"), None)
            hook_deny = any("Hook denied" in (u.get("text") or "") for u in row.get("updates") or [])
            verdicts = [VERDICT.search(d).groups() for d in row.get("debug") or [] if VERDICT.search(d)]
            # The Grok build that answered: the session profile's own log names it ("ver") on most of its lines.
            builds = set()
            for log in results.parent.glob(f"{row['case']}-{row['mode']}-{row['attempt']}*/home/.grok/logs/unified.jsonl"):
                for entry in log.read_text(errors="replace").splitlines():
                    try:
                        version = json.loads(entry).get("ver")
                    except ValueError:
                        continue
                    if version:
                        builds.add(version)
            rows.append({
                "batch": batch, "case": row["case"], "attempt": row["attempt"], "mode": row["mode"],
                "build": ",".join(sorted(b for b in builds if b)) or None,
                "model": row["model"], "effort": row["effort"], "allow": row.get("allow") or [],
                "preempt_hook": row.get("preempt_hook", False), "prompt_kind": row.get("prompt_kind", "exact"),
                "asked": redact(row["asked"]), "ran": [redact(c or "") for c in row.get("ran") or []],
                "ran_as_asked": row.get("same"),
                "decision": decision.get("decision") if decision else ("hook deny" if hook_deny else None),
                "wait_ms": decision.get("wait_ms") if decision else None,
                "turn": f"{ended.get('outcome')}:{ended.get('cancellation_category')}" if ended else None,
                "stop": row.get("stop"), "hook_denied": hook_deny,
                "classifier": [{"tool": t, "verdict": v, "latency_ms": int(ms)} for t, v, ms in verdicts],
                "stderr": redact(row.get("stderr") or "")[-300:], "seconds": row.get("seconds")})
    evidence.mkdir(parents=True, exist_ok=True)
    with open(evidence / "probes.jsonl", "w") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")
    print(f"{len(rows)} probe sessions")
    for row in rows:
        print(f"{row['batch']:16} {row['case']:26} hook={int(row['preempt_hook'])} allow={len(row['allow'])} "
              f"{str(row['decision']):10} {str(row['wait_ms']):>6} ms  {row['turn']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
