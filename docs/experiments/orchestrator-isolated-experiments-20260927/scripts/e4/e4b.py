#!/usr/bin/env python3
import os
import sys, os, json, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import importlib
analyze = importlib.import_module("analyze")

def thought_text_before(events, idx, max_back=400):
    """Collect the thought/text chunks immediately preceding events[idx], concatenated, back to the previous tool_call/tool_call_update boundary."""
    chunks = []
    j = idx - 1
    while j >= 0 and j > idx - max_back:
        e = events[j]
        t = e.get("type")
        if t == "thought":
            chunks.append(e.get("data",""))
        elif t == "text":
            chunks.append(e.get("data") or e.get("text") or "")
        elif t in ("tool_call", "tool_call_update"):
            if chunks:
                break
        j -= 1
    chunks.reverse()
    return "".join(chunks).strip()

def e4b(run):
    print(f"\n===== E4b {run} =====")
    events = analyze.load_events(run)
    starts = [i for i,e in enumerate(events) if e.get("type")=="auto_compact_started"]
    completes = [i for i,e in enumerate(events) if e.get("type")=="auto_compact_completed"]
    for k, start_i in enumerate(starts):
        comp_i = next((x for x in completes if x > start_i), None)
        anchor = comp_i if comp_i is not None else start_i
        # find first SKILL.md read after anchor
        skill_read_idx = None
        first_tool_calls = []
        for i in range(anchor+1, min(anchor+300, len(events))):
            e = events[i]
            if e.get("type") == "tool_call":
                first_tool_calls.append((i, e.get("toolName"), e.get("rawInput",{})))
                tf = e.get("rawInput", {}).get("target_file","")
                if tf.endswith("SKILL.md") and skill_read_idx is None:
                    skill_read_idx = i
                    break
        print(f"-- compaction #{k+1}: started@{start_i} completed@{comp_i}")
        if skill_read_idx is None:
            print("   no SKILL.md read found in next 300 events after compaction")
            # show first few tool calls anyway
            for i,tn,ri in first_tool_calls[:5]:
                print(f"     first calls: idx={i} tool={tn} input={json.dumps(ri)[:150]}")
            continue
        pre_text = thought_text_before(events, skill_read_idx)
        tf = events[skill_read_idx].get("rawInput",{}).get("target_file")
        print(f"   SKILL.md read at idx={skill_read_idx}, target_file={tf}")
        print(f"   preceding thought/text ({len(pre_text)} chars): {pre_text[-600:]!r}")
        # what was the immediately-prior tool call/result (possible instruction source)?
        prior_tool_idx = None
        for i in range(skill_read_idx-1, max(anchor, skill_read_idx-50), -1):
            if events[i].get("type") == "tool_call":
                prior_tool_idx = i
                break
        if prior_tool_idx is not None:
            e = events[prior_tool_idx]
            print(f"   prior tool_call idx={prior_tool_idx} tool={e.get('toolName')} input={json.dumps(e.get('rawInput',{}))[:200]}")
            # get its result text (search forward for tool_call_update completed)
            tcid = e.get("toolCallId")
            for j in range(prior_tool_idx+1, min(prior_tool_idx+20, len(events))):
                e2 = events[j]
                if e2.get("toolCallId")==tcid and e2.get("type")=="tool_call_update" and e2.get("status")=="completed":
                    try:
                        txt = e2["content"][0]["content"]["text"]
                    except Exception:
                        txt = ""
                    print(f"   prior tool result (first 400 chars): {txt[:400]!r}")
                    break

if __name__ == "__main__":
    for run in ["e2e-run6", "e2e-run6b", "e2e-run7", "e2e-run7b", "e2e-run8b"]:
        e4b(run)
