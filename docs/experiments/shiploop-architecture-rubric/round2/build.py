"""Round 2: every scenario-runtime cell x five wording variants, one condition for all."""
import json, pathlib, sys
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from variants import build
SC = json.loads((HERE.parent / "scenarios.json").read_text())
V = build((HERE / "shipped_block.txt").read_text())
TASK = """You are running the discovery, spec and plan stages of ShipLoop, an SDLC harness, for this request.

Request: {req}

Discovered environment: {env}

{guide}
Return: (1) an architecture decision of at most 500 words, and (2) a numbered list of work items, each naming what it builds and how it is checked. Do not write code."""
out = HERE / "prompts"; out.mkdir(exist_ok=True)
for s in SC["scenarios"]:
    for rt in s["runtimes"] + s.get("runtimes_ext", []):
        ui = s.get("ui") if rt in s.get("runtimes_ext", []) else None
        req = s["request"] + (f" Use {ui} for the UI." if ui else "")
        for v, g in V.items():
            (out / f"{s['id']}_{rt}_{v}.txt").write_text(TASK.format(req=req, env=SC["runtimes"][rt], guide=g))
for v, g in V.items(): (HERE / f"block_{v}.txt").write_text(g)
print(len(list(out.iterdir())), "prompts")
