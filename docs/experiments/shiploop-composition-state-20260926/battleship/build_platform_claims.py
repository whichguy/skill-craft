"""E6: does the research stage catch false platform claims in a draft plan?"""
import sys, pathlib, json
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[4] / "skills" / "shiploop" / "scripts"))
import shiploop_navigator_v3_prompts as p
CLAIMS = {
 "GAS": {"env": "Google Apps Script web app, executing as the user accessing it, access limited to the Workspace domain.",
   "F1": "google.script.run calls are synchronous, so the page blocks until fire() returns and needs no callback handling.",
   "F2": "Each game is stored in CacheService; it is durable, so finished games stay available for the history view.",
   "T1": "LockService.getScriptLock() serializes concurrent fire() calls from both players.",
   "T2": "Because the web app executes as the user accessing it inside the domain, Session.getActiveUser().getEmail() returns the player's email."},
 "SF": {"env": "Salesforce DX project, LWC UI, players are internal users of the org.",
   "F1": "Field-level security on Fleet__c restricts each fleet record so only its owning player can read it.",
   "F2": "A composite unique constraint on Shot__c over (Game__c, Row__c, Col__c) rejects duplicate shots declaratively.",
   "T1": "SELECT ... FOR UPDATE on the Game__c row serializes two simultaneous fire() transactions.",
   "T2": "The LWC calls @AuraEnabled Apex methods imperatively for invite, place and fire."},
 "CF": {"env": "Cloudflare Workers project in TypeScript.",
   "F1": "Invite passwords are hashed with scrypt through crypto.subtle inside the Worker.",
   "F2": "Game state lives in Workers KV, which is strongly consistent, so both players read each shot immediately after it is written.",
   "T1": "A Durable Object per game processes its requests one at a time, so turn order cannot race.",
   "T2": "The game Durable Object accepts WebSocket connections and pushes each move to both players."},
}
VERIFY = """
Challenge the draft before building on it: list every claim about what the runtime
or a library can do that a decision depends on. Mark each confirmed (a primary
documentation URL or a probe's saved result), wrong (the correction and the
decisions it changes), or unverified (the check that would settle it). A recalled
fact is not evidence, and neither is the draft saying so.
"""
T = """You are the research stage of ShipLoop, an SDLC harness, for multiplayer Battleship (two signed-in players, invites, fleets, turns).

Environment: {env}

Draft architecture from the previous stage:
{plan}

Research duty:
{duty}
Return the research result (at most 450 words): conclusions with sources, corrections to the draft, and remaining unknowns."""
for rt, c in CLAIMS.items():
    plan = "\n".join(f"- {c[k]}" for k in ("T1", "F1", "T2", "F2"))
    for v, duty in (("current", p.DUTIES["research"]), ("current-web", p.DUTIES["research"]), ("verify-web", p.DUTIES["research"] + VERIFY)):
        pathlib.Path(f"prompts6/{rt}_research_{v}.txt").write_text(T.format(env=c["env"], plan=plan, duty=duty))
json.dump(CLAIMS, open("claims6.json", "w"), indent=1)
