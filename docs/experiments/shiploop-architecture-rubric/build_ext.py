"""New environments x {no-card, card}: does linking the platform card improve the plan?"""
import sys, json, pathlib, os
SK = pathlib.Path(os.environ["SHIPLOOP_SRC"]) / "skills" / "shiploop"
sys.path.insert(0, str(SK / "scripts"))
import shiploop_prompts as p
HERE = pathlib.Path(__file__).resolve().parent
CARDS = pathlib.Path(os.environ["CARDS_DIR"])
SC = json.loads((HERE / "scenarios.json").read_text())
CARD = {"NODE": "node-express", "VERCEL": "vercel", "AWS": "aws", "GCP": "gcp", "CF": "cloudflare-workers"}
TASK = """You are running the discovery, spec and plan stages of ShipLoop, an SDLC harness, for this request.

Request: {req}

Discovered environment: {env}

{guide}
Return: (1) an architecture decision of at most 500 words, and (2) a numbered list of work items, each naming what it builds and how it is checked. Do not write code."""
def request(s): return s["request"] + (f" Use {s['ui']} for the UI." if s.get("ui") else "")
out = pathlib.Path(os.environ.get("EXP_DIR", ".")) / "prompts_ext"; out.mkdir(exist_ok=True)
for s in SC["scenarios"]:
    for rt in s.get("runtimes_ext", []):
        cards = [CARDS / f"{CARD[rt]}.md"] + ([CARDS / "ui-frameworks.md"] if s.get("ui") else [])
        link = "Guides named in this packet (read the ones that apply before deciding):\n" + "\n".join(f"- {c} (platform card)" for c in cards) + "\n"
        for v, g in (("nocard", p.INTERACTION_DESIGN), ("card", p.INTERACTION_DESIGN + "\n" + link)):
            (out / f"{s['id']}_{rt}_{v}.txt").write_text(TASK.format(req=request(s), env=SC["runtimes"][rt], guide=g))
print(len(list(out.iterdir())), "prompts")
