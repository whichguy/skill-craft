"""E7: does discovery find and follow the conventions a project layers on its runtime?"""
import sys, pathlib
SK = pathlib.Path(__file__).resolve().parents[4] / "skills" / "shiploop"
sys.path.insert(0, str(SK / "scripts"))
import shiploop_prompts as p
LAYERED = """
Layered conventions. The published runtime is only the floor. Find what this
project has layered on it: vendored or packaged frameworks and shared libraries,
wrappers around platform calls, module and loading systems, base classes, utility
modules, deployment tools and MCP servers that shape the code they write, and the
tests that exercise them. For each, record the paradigm it imposes: how modules are
declared and loaded, how the client calls the server, how requests are routed, how
configuration and state are read and written, how errors are logged and reported.
Cite one canonical example for each. New code follows that paradigm; calling the
raw platform API that a layer wraps is a departure that needs a recorded reason.
"""
REQ = {"gas": "Make the tic-tac-toe game multiplayer: two signed-in people in the domain each play from their own browser, and a game survives a reload.",
       "sf": "Add multiplayer Battleship: two users of the org play each other from their own browsers, and a game survives a reload."}
CARD = {"gas": "apps-script", "sf": "salesforce"}
T = """You are ShipLoop's discovery stage followed by step planning. The repository is the current working directory. Inspect it with your read-only tools; edit nothing.

Request: {req}

Discovery duty:
{duty}
{guide}
Return (1) the discovery findings that matter for this request, at most 300 words, and (2) a step plan naming each file to create or change and, for each, the functions, modules and calls it will use."""
for fx in ("gas", "sf"):
    links = ("\nGuides named in this packet:\n- " + "\n- ".join([
        f"{SK}/references/coding-guidance.md", f"{SK}/references/behavioral-requirements.md#actors-channels-and-state-ownership",
        f"{SK}/references/platforms/{CARD[fx]}.md"]) + "\n")
    V = {"control": "", "current": p.INTERACTION_DESIGN + links, "layered": p.INTERACTION_DESIGN + links + LAYERED}
    for v, g in V.items():
        duty = p.DUTIES["discovery"] if v != "control" else "Inspect the repository and environment that matter for the request."
        pathlib.Path(f"prompts7/{fx}_{v}.txt").write_text(T.format(req=REQ[fx], duty=duty, guide=g))
pathlib.Path("layered.txt").write_text(LAYERED)
