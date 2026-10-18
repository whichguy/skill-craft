#!/usr/bin/env python3
"""Lay out one Grok E2E run step by step: each packet (the prompt) with what the model said, thought and did under it.

    python3 run_steps.py RUN_OUTPUT_DIR OUT_DIR

Reads RUN/.shiploop-runs/work-*/run (packets, results, improve records, state.md), the worktree's .shiploop-improve
hand-offs and reviews, flow.json (the action order) and events.jsonl (the host's stream).  An event belongs to the
action whose packet header the model last received in a tool output ("ShipLoop navigator | <stage> | revision N"),
mapped to an action through the packet files' own headers.  Writes OUT/index.json and per step
OUT/in/<NN>-<tag>.{packet.md,result.md,transcript.md,improve-*} .
"""
import glob, json, os, re, shutil, sys

RUN, OUT = sys.argv[1], sys.argv[2]
RD = glob.glob(RUN + "/.shiploop-runs/work-*/run")[0]
WT = glob.glob(RUN + "/.shiploop-runs/work-*/worktree")[0]
HEAD = re.compile(r"ShipLoop navigator \| ([a-z-]+) \| revision (\d+)")
os.makedirs(OUT + "/in", exist_ok=True)

flow = json.load(open(RUN + "/flow.json"))
state_text = open(RD + "/state.md").read()
state = json.loads(re.search(r"```shiploop-state\n(.*?)\n```", state_text, re.S).group(1))

# (stage, revision) -> action, from each packet file's first line and callback action id
by_head = {}
for path in glob.glob(RD + "/packets/*.md"):
    action = os.path.basename(path)[:-3]
    text = open(path, errors="replace").read(4000)
    m = HEAD.search(text)
    if m:
        by_head[(m.group(1), int(m.group(2)))] = action
improve_of = {a["action"]: a.get("reviewed") for a in flow["actions"] if a.get("reviewed_stage")}

# Walk the event stream
per = {}            # action -> list of (kind, text)
current = None
say, think = [], []
def flush():
    if current is None:
        return
    if think:
        per.setdefault(current, []).append(("think", "".join(think)))
    if say:
        per.setdefault(current, []).append(("say", "".join(say)))
    think.clear(); say.clear()

calls = {}
for line in open(RUN + "/events.jsonl", errors="replace"):
    try:
        e = json.loads(line)
    except ValueError:
        continue
    t = e.get("type")
    if t == "thought":
        if say: flush()
        think.append(e.get("data", ""))
    elif t == "text":
        if think and not say:
            per.setdefault(current, []).append(("think", "".join(think))) if current else None; think.clear()
        say.append(e.get("data", ""))
    elif t == "tool_call":
        flush()
        raw = e.get("rawInput") or {}
        desc = raw.get("command") or raw.get("target_file") or raw.get("path") or raw.get("pattern") or raw.get("query") or json.dumps(raw)[:400]
        calls[e.get("toolCallId")] = current
        per.setdefault(current, []).append(("call", f"{e.get('toolName') or e.get('title')}: {desc}"))
    elif t == "tool_call_update":
        out = e.get("rawOutput")
        text = ""
        for c in e.get("content") or []:
            if isinstance(c, dict):
                inner = c.get("content")
                if isinstance(inner, dict) and isinstance(inner.get("text"), str):
                    text += inner["text"]
                elif isinstance(c.get("text"), str):
                    text += c["text"]
        if not text and isinstance(out, dict):
            v = out.get("output_for_prompt") or out.get("output")
            if isinstance(v, list):
                try:
                    v = bytes(v).decode("utf-8", "replace")
                except (ValueError, TypeError):
                    v = ""
            if not isinstance(v, str):
                v = ""
            for key in ("FileContent", "Content"):
                if not v and isinstance(out.get(key), dict):
                    v = str(out[key].get("content") or "")
            text = v
        elif not text and isinstance(out, str):
            text = out
        if not text or e.get("status") not in ("completed", "failed", None):
            continue
        owner = calls.get(e.get("toolCallId"), current)
        per.setdefault(owner, []).append(("out", text))
        heads = HEAD.findall(text)
        if heads:
            stage, rev = heads[-1]
            nxt = by_head.get((stage, int(rev)))
            if nxt:
                flush()
                current = nxt
flush()

def clip(s, n):
    s = s.strip()
    return s if len(s) <= n else s[:n] + f" … [{len(s) - n} more characters]"

index = []
n = 0
for a in flow["actions"]:
    if a["stage"] == "release-verify" and a["outcome"] is None and not per.get(a["action"]):
        continue
    n += 1
    reviewed = a.get("reviewed_stage")
    tag = "%02d-%s" % (n, ("improve-" + reviewed) if reviewed else a["stage"])
    act = a["action"]
    pk = RD + "/packets/" + act + ".md"
    if os.path.exists(pk):
        shutil.copy(pk, f"{OUT}/in/{tag}.packet.md")
    rs = RD + "/results/" + act + ".md"
    if os.path.exists(rs):
        shutil.copy(rs, f"{OUT}/in/{tag}.result.md")
    lines = []
    for kind, text in per.get(act, []):
        if kind == "call":
            lines.append("CALL  " + clip(text, 600))
        elif kind == "out":
            lines.append("OUT   " + clip(text, 1500).replace("\n", "\n      "))
        elif kind == "say":
            lines.append("SAY   " + text.strip().replace("\n", "\n      "))
        elif kind == "think":
            lines.append("THINK " + clip(text, 6000).replace("\n", "\n      "))
    if lines:
        open(f"{OUT}/in/{tag}.transcript.md", "w").write("\n".join(lines) + "\n")
    if reviewed:
        rev_id = a.get("reviewed")
        for cand in (act, rev_id):
            d = RD + "/improve/" + cand
            if os.path.isdir(d):
                for f in ("passes.md", "receipt.md"):
                    if os.path.exists(d + "/" + f):
                        shutil.copy(d + "/" + f, f"{OUT}/in/{tag}.improve-{f}")
                break
        hd = [p for p in glob.glob(WT + "/.shiploop-improve/*") if rev_id and p.endswith(rev_id[-8:])]
        if hd:
            for f in ("handoff.md", "opening.md", "parent-return.md"):
                if os.path.exists(hd[0] + "/" + f):
                    shutil.copy(hd[0] + "/" + f, f"{OUT}/in/{tag}.improve-{f}")
            for rv in sorted(glob.glob(hd[0] + "/reviews/review-*.md")):
                shutil.copy(rv, f"{OUT}/in/{tag}.improve-{os.path.basename(rv)}")
    p = a["phases"][0] if a["phases"] else {}
    kinds = [k for k, _ in per.get(act, [])]
    index.append({"n": n, "tag": tag, "action": act, "stage": a["stage"], "reviews": reviewed, "outcome": a["outcome"],
                  "calls": kinds.count("call"), "says": kinds.count("say"), "think_chars": sum(len(t) for k, t in per.get(act, []) if k == "think"),
                  "model_seconds": p.get("span_seconds"), "packet_chars": os.path.getsize(pk) if os.path.exists(pk) else 0})
unattributed = per.get(None, [])
json.dump({"run": RUN, "steps": index, "unattributed_events": len(unattributed)}, open(OUT + "/index.json", "w"), indent=1)
print(len(index), "steps;", sum(s["calls"] for s in index), "calls attributed;", len(unattributed), "events before the first packet")
