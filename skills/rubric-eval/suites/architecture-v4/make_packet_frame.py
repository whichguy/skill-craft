#!/usr/bin/env python3
"""Regenerate frames/review-packet.txt from ShipLoop's source: the plan-stage Improve review as a real run sees it.

It renders a synthetic run to the plan stage's Improve review, keeps the packet's reference locators (rewritten to
the references/ folder the call's workspace holds), and places the arm where the navigator places the review
blocks, before the plan-stage Improve prompt, which is included verbatim. Run it after ShipLoop's plan-stage
packet changes; the frame records the source it was made from.

usage: make_packet_frame.py [SHIPLOOP_SCRIPTS_DIR]
"""
import hashlib
import re
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE.parents[3] / "skills" / "shiploop" / "scripts"
sys.path.insert(0, str(SCRIPTS))
import shiploop_navigator as nav  # noqa: E402
import shiploop_navigator_v3_prompts as guidance  # noqa: E402
import shiploop_store as store  # noqa: E402

repo = Path(tempfile.mkdtemp(prefix="packet-frame-")); run = repo / "run"; run.mkdir()
state = nav.new_state(str(repo), "Synthetic request.")
while not (nav.current_stage(state) == "plan" and state.get("active_improve")):
    act = nav.current_action(state)
    if state.get("active_improve"):
        state = nav.finish_improve(state, act["id"], {"summary": "Synthetic review", "lessons": "none"})
        continue
    extra = {"work_items": [{"id": "W1", "title": "Synthetic", "context": "x"}]} if nav.current_stage(state) == "plan" else {}
    state = nav.apply(state, act["id"], {"outcome": "done", "summary": "Synthetic", **extra})
store.write_record(run / "state.md", state)
packet = nav.render(None, run, store.read_record(run / "state.md"))
locators = []
for line in packet.splitlines():
    m = re.match(r"^([A-Z][^:]{2,80}):\s+\S*/skills/shiploop/(references/\S+)$", line)
    if m:
        locators.append(f"{m.group(1)}: {m.group(2)}")
improve = guidance.improve_prompt("plan").strip()
source = hashlib.sha256((packet.split("Recovery command")[0] + improve).encode()).hexdigest()[:12]
frame = f"""You are the Improve review of a ShipLoop plan-stage result, inside a ShipLoop run. The packet guidance below is what a real review receives. Run mechanics it mentions (binding an Improve skill, receipts, callbacks, commits, child workspaces, Backchain calls) do not apply in this exercise: apply its review guidance to the plan and return the revised plan.
Your working directory holds the ShipLoop references under references/, which the locators below point to; read what the guidance calls for with your file tools. There is no project to open and no command to run. Answer in this reply.

Packet reference locators:
{chr(10).join(locators)}

{{arm}}
{improve}

Request: {{request}}

Environment: {{environment}}

Plan under review:
<<<
{{plan}}
>>>

Return two sections: "## Findings" (each finding and its fix, or "None"), then "## Revised plan" with the complete revised architecture decision and work items.
"""
(HERE / "frames" / "review-packet.txt").write_text(frame)
(HERE / "frames" / "review-packet.source").write_text(f"shiploop plan-stage Improve packet {source}; {len(locators)} locators; improve prompt {len(improve.split())} words\n")
print(f"review-packet: {len(frame.split())} words, {len(locators)} locators, source {source}")
