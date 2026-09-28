"""Battleship architecture elicitation: runtimes x requests x guidance variants."""
import sys, pathlib, re
SK = pathlib.Path(__file__).resolve().parents[4] / "skills" / "shiploop"
sys.path.insert(0, str(SK / "scripts"))
import shiploop_prompts as p

def section(path, start, stop):
    t = (SK / path).read_text()
    a = t.index(start); b = t.index(stop, a + len(start))
    return t[a:b].strip()

ACTORS = section("references/behavioral-requirements.md", "## Actors, channels, and state ownership", "### Incoming events")
PLACE = section("references/service-discovery.md", "## Runtime state placement", "## Cache and authorization")

RUNTIMES = {
 "GAS": ("An empty clasp project for a Google Apps Script web app (V8 runtime), to be deployed with clasp "
         "into the user's Google Workspace domain. clasp is signed in. No other files yet.", "apps-script"),
 "SF":  ("An empty Salesforce DX project (sfdx-project.json, API 62.0) with a connected scratch org via the sf CLI. "
         "Lightning Web Components is the UI framework. No other metadata yet.", "salesforce"),
 "CF":  ("An empty Cloudflare Workers project (wrangler.toml, TypeScript). wrangler is signed in to the account. "
         "No other files yet.", None),
}
REQUESTS = {
 "solo":  "Build a Battleship game that a person plays in the browser against the computer.",
 "multi": ("Build multiplayer Battleship: two people each sign in, one invites the other to a game, each places "
           "a fleet, and they take turns firing until one fleet is sunk."),
}
REBALANCE = """
The reverse holds too: a client-only design is a decision that needs its reasons.
When two people, two devices, hidden information or a lifetime beyond one page is
involved, each actor's identity and the authoritative state belong to the runtime,
and the design names the runtime service that holds them.
"""
LIFECYCLE = """Interaction and state model. Before deciding where logic runs, write the model
the runtime must support, in proportion to the request:
1. Actors and identity: who uses the product and how the runtime itself identifies
   each one (its own sign-in and user identity, not a name typed into the page);
   what each actor may see and do. Two people are two identities and two clients.
2. Interactions: each hop between actor, client, runtime and other services; who
   starts it; how the other party learns of a change (response, polling, push,
   trigger or schedule) and how quickly it must.
3. State lifecycle: for each piece of state, its authoritative owner, where it
   lives, who may read it (hidden state never reaches a client that must not see
   it), how it is created, changed concurrently, recovered after a reload or
   disconnect, and when it expires or is deleted.
4. Information lifecycle: what personal or secret data enters, where it is shown,
   stored and logged, how long it is kept, and how it is removed.
5. Runtime capability inventory: from the runtime's own documentation and
   configuration, list what it offers for identity, per-user and shared storage,
   locking or transactions, server entry points the client can call, events, push
   and scheduling, and quotas. Map each actor, interaction and state to one of
   them, or say why something new is needed.
A client-only design is a valid result of this model, not a default: it needs the
model to show that no state is shared, hidden, or needed beyond the page.
"""
TASK = """You are running the discovery, spec and plan stages of ShipLoop, an SDLC harness, for this request.

Request: {req}

Discovered environment: {env}

{guide}
Return: (1) an architecture decision of at most 500 words, and (2) a numbered list of work items, each naming what it builds and how it is checked. Do not write code."""

def linked(card):
    refs = ["references/behavioral-requirements.md#actors-channels-and-state-ownership (Interaction design guide)",
            "references/service-discovery.md#runtime-state-placement (Service discovery guide)",
            "references/platform-discovery.md (Platform discovery guide)"]
    if card: refs.append(f"references/platforms/{card}.md (platform card)")
    return (p.INTERACTION_DESIGN + "\nGuides named in this packet (paths relative to the working directory):\n- "
            + "\n- ".join(refs) + "\n")

for rk, (env, card) in RUNTIMES.items():
    for qk, req in REQUESTS.items():
        V = {
            "control": "",
            "current-linked": linked(card),
            "current-inline": p.INTERACTION_DESIGN + "\n" + ACTORS + "\n\n" + PLACE + "\n",
            "rebalanced": p.INTERACTION_DESIGN + "\n" + ACTORS + "\n" + REBALANCE + "\n" + PLACE + "\n",
            "lifecycle": p.INTERACTION_DESIGN + "\n" + LIFECYCLE,
        }
        if qk == "solo":
            V = {k: V[k] for k in ("control", "current-inline", "lifecycle")}
        for vk, g in V.items():
            pathlib.Path(f"prompts/{rk}_{qk}_{vk}.txt").write_text(TASK.format(req=req, env=env, guide=g))
print(len(list(pathlib.Path("prompts").iterdir())), "prompts")
