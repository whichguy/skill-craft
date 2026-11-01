"""Print each accepted follow_on entry of finished E2E runs beside the record its source names (the R3 reading).

Usage: python3 read_records.py OUTPUT_DIR [OUTPUT_DIR ...].  Read-only.  It prints the request, the handoff summary, and for each entry
its class, source, statement and needs next to the cited record (a lessons field, an unverified row, an assumption, a stage's summary);
a commit source is not printed.
"""
import json
import re
import sys
from pathlib import Path


def load(path):
    text = Path(path).read_text(encoding="utf-8")
    return json.loads(re.search(r"```[a-z-]*\n(.*?)\n```", text, re.DOTALL).group(1))

def record(state, source):
    accepted, history = state.get("accepted", {}), state.get("history", [])
    kind, _, rest = source.partition(":")
    if source.startswith("lessons."):
        for row in reversed(history):
            if row.get("stage") == "release-verify" and row.get("outcome") == "done":
                return (accepted.get(row["action"], {}).get("lessons") or {}).get(source.split(".", 1)[1], "(no text)")
    if kind == "unverified":
        for row in reversed(history):
            res = accepted.get(row.get("action"), {})
            if isinstance(res.get("unverified"), list) and row.get("outcome") == "done":
                hits = [r for r in res["unverified"] if r.get("requirement") == rest]
                if hits:
                    return json.dumps(hits, ensure_ascii=False)[:700]
        return "(no row)"
    if kind == "assumption":
        for row in history:
            res = accepted.get(row.get("action"), {})
            for a in res.get("assumptions") or []:
                if a.get("id") == rest:
                    return json.dumps(a, ensure_ascii=False)[:600]
        return "(no assumption)"
    if kind == "result":
        for row in reversed(history):
            if row.get("stage") == rest and row.get("outcome") == "done":
                res = accepted.get(row["action"], {})
                return (res.get("summary") or "")[:700]
        return "(no result)"
    return "(commit or other: not printed)"

for out in sys.argv[1:]:
    for st in sorted(Path(out).glob(".shiploop-runs/*/run/state.md")):
        state = load(st)
        rows = [r for r in state.get("history", []) if r.get("stage") == "handoff" and r.get("outcome") == "done"]
        res = state.get("accepted", {}).get(rows[-1]["action"], {}) if rows else {}
        print("#" * 90); print(out, "|", state.get("status"))
        print("REQUEST:", " ".join(str(state.get("prompt", "")).split())[:400])
        print("handoff summary:", " ".join(str(res.get("summary", "")).split())[:900])
        for i, e in enumerate(res.get("follow_on") or [], 1):
            print(f"\n[{i}] {e.get('class')} | source {e.get('source')} | sentence {e.get('request_sentence') or '-'}")
            print("    statement:", " ".join(e.get("statement", "").split()))
            print("    needs:", " ".join(e.get("needs", "").split()))
            print("    RECORD:", " ".join(str(record(state, e.get('source', ''))).split())[:700])
