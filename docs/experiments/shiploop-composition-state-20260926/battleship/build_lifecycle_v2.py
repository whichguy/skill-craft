"""E4 information lifecycle, E5 overbuild guard (+ multi recheck) with refined lifecycle wording (v2)."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[4] / "skills" / "shiploop" / "scripts"))
import shiploop_navigator_v3_prompts as p
src = pathlib.Path(__file__).with_name("build_architecture.py").read_text()
LIFE1 = src.split('LIFECYCLE = """')[1].split('"""')[0]
TASK = src.split('TASK = """')[1].split('"""')[0]
RUNTIMES = {
 "GAS": "An empty clasp project for a Google Apps Script web app (V8 runtime), to be deployed with clasp into the user's Google Workspace domain. clasp is signed in. No other files yet.",
 "SF": "An empty Salesforce DX project (sfdx-project.json, API 62.0) with a connected scratch org via the sf CLI. Lightning Web Components is the UI framework. No other metadata yet.",
 "CF": "An empty Cloudflare Workers project (wrangler.toml, TypeScript). wrangler is signed in to the account. No other files yet.",
}
LIFE2 = """State and information lifecycle. For each piece of state the request involves,
decide and state, in proportion to the request: its authoritative owner and where
it lives; who may read it (hidden information never reaches a client that must not
see it); how simultaneous changes are resolved; what ends it (finished, abandoned,
expired) and what removes it; and which runtime quotas or limits it meets. For
personal or secret data, state where it is shown, stored and logged, how long it is
kept, and how it is removed. Map each to what the runtime already offers, from its
own documentation and configuration. Do not add identity, sharing or persistence
the request does not call for; when the request leaves them open, carry the
question to the user with the default you would take.
"""
REQ = {
 "solo": "Build a Battleship game that a person plays in the browser against the computer.",
 "multi": "Build multiplayer Battleship: two people each sign in, one invites the other to a game, each places a fleet, and they take turns firing until one fleet is sunk.",
 "invite": ("Build multiplayer Battleship where a player invites a friend by email address. The friend gets an email with a "
            "link, signs in, and they play. Each player can see a history of their past games."),
}
V = {"current": p.INTERACTION_DESIGN, "life1": p.INTERACTION_DESIGN + "\n" + LIFE1, "life2": p.INTERACTION_DESIGN + "\n" + LIFE2}
cells = [(r, q, v) for r in RUNTIMES for q in ("solo", "invite") for v in V] + [(r, "multi", "life2") for r in RUNTIMES]
for r, q, v in cells:
    pathlib.Path(f"prompts4/{r}_{q}_{v}.txt").write_text(TASK.format(req=REQ[q], env=RUNTIMES[r], guide=V[v]))
pathlib.Path("life2.txt").write_text(LIFE2)
print(len(cells), "cells")
