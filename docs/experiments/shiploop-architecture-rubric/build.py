"""Scenario catalog x runtimes x {shipped, candidate} architecture prompts."""
import sys, json, pathlib, os
SK = pathlib.Path(os.environ["SHIPLOOP_SRC"]) / "skills" / "shiploop"
sys.path.insert(0, str(SK / "scripts"))
import shiploop_navigator_v3_prompts as p
HERE = pathlib.Path(__file__).resolve().parent
SC = json.loads((HERE / "scenarios.json").read_text())
RUNTIMES = {
 "GAS": "An empty clasp project for a Google Apps Script web app (V8 runtime), to be deployed with clasp into the user's Google Workspace domain. clasp is signed in. No other files yet.",
 "SF": "An empty Salesforce DX project (sfdx-project.json, API 62.0) with a connected scratch org via the sf CLI. Lightning Web Components is the UI framework. No other metadata yet.",
 "CF": "An empty Cloudflare Workers project (wrangler.toml, TypeScript). wrangler is signed in to the account. No other files yet.",
}
TASK = """You are running the discovery, spec and plan stages of ShipLoop, an SDLC harness, for this request.

Request: {req}

Discovered environment: {env}

{guide}
Return: (1) an architecture decision of at most 500 words, and (2) a numbered list of work items, each naming what it builds and how it is checked. Do not write code."""
OLD_READ = "who may read it (hidden information never reaches a client that must not\nsee it);"
NEW_READ = ("who may read it (information one user must not see, such as an opponent's\n"
            "fleet or another person's record, stays off that user's client; information a\n"
            "lone user could only misuse against themselves may stay on their client);")
ADD = """Choose the simplest placement that meets the request: a single-user game or tool
with no shared or lasting state runs entirely in the client. Add server state,
identity, a store or a live channel only for a requirement that needs it, and use
the runtime's native storage, identity, cache, workflow and notification services
before building your own. For each hop, pick the lightest channel that meets the
freshness the request states: request/response; polling at a stated interval;
email or platform notification for changes hours apart; server-sent events,
WebSockets or platform push only when seconds matter. After a push, poll gap or
reconnect, read the authoritative state back. Cache only derived data, in the
runtime's cache, with an expiry that matches the staleness the request allows.
State each channel's and cache's cost against the runtime's quotas.
"""
shipped = p.INTERACTION_DESIGN
assert OLD_READ in shipped, "shipped lifecycle wording changed; update OLD_READ"
candidate = shipped.replace(OLD_READ, NEW_READ).rstrip("\n") + "\n" + ADD
out = pathlib.Path(os.environ.get("EXP_DIR", ".")) / "prompts"; out.mkdir(parents=True, exist_ok=True)
for s in SC["scenarios"]:
    for rt in s["runtimes"]:
        for v, g in (("shipped", shipped), ("candidate", candidate)):
            (out / f"{s['id']}_{rt}_{v}.txt").write_text(TASK.format(req=s["request"], env=RUNTIMES[rt], guide=g))
(HERE / "candidate_interaction_design.txt").write_text(candidate)
print(len(list(out.iterdir())), "prompts")
