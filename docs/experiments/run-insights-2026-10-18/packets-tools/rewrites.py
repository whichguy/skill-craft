"""The ten worst planning duty items: exact printed text (Battleship packets) and a concise rewrite, with sizes.

    python3 -I rewrites.py <duty-items.json> <out.json>
"""
import json
import sys

items = json.load(open(sys.argv[1]))


def before(stage, *numbers, sub=None):
    text = "\n".join(items[stage][n] for n in numbers)
    if sub:
        start = text.index(sub[0])
        end = text.index(sub[1], start) + len(sub[1]) if sub[1] else len(text)
        text = text[start:end]
    return text


REWRITES = [
    {
        "id": "R1", "stage": "step-plan", "where": "DUTIES['step-plan'] item 4, the `check` bullet",
        "problem": "Contradictory dead end for a remote-only target: 'Tests are not a step' plus 'Remote-only target: the "
                   "recorded test route only. None runs now: change the step boundary' leaves no runnable behavioural "
                   "Proof, so Battleship's four Proofs became python source-text matches (bs-build-1 gap 1; plan B1, B2). "
                   "It also never says a check must observe behaviour rather than the implementation's own text.",
        "before": before("step-plan", "4", sub=("   - `check`:", "change the step boundary.")),
        "after": ("   - `check`: the one command, from the repository root, that proves the step's criteria with only this "
                  "step and accepted earlier ones; ShipLoop runs it at the step's done. It observes behaviour: matching the "
                  "implementation's own text (a literal, a call shape) dictates form and proves nothing, and so does "
                  "skipping a missing file. It needs no later step, unwritten test or release artifact. Behaviour that "
                  "runs only on a remote target: deploy only this step's paths to the recorded development target, then "
                  "run a read-only probe the run's authority covers."),
        "keeps_ledger_anchors": ["`check`: the one command, from the repository root, that proves the step's criteria",
                                 "skipping a missing file"],
        "decisions": ["owner decision 4.2 (B1) accepted 2026-10-18"],
    },
    {
        "id": "R2", "stage": "step-plan", "where": "DUTIES['step-plan'] item 9 (Plan record, with _PLAN_RECORD_INTERACTIONS)",
        "problem": "1,833 characters of ungated prose (8 topic bullets, one 600-character UI sentence) that all four "
                   "step-plan results skipped or shortened (run-insights plan section 1); no exit condition or gate names "
                   "it, and its UI ambition text repeats plan item 8. Replaced by the A1 concern map, which a gate checks "
                   "for structure.",
        "before": before("step-plan", "9"),
        "after": ("8. `concerns`: each applies-yes concern row the plan recorded for this item maps to the steps that "
                  "carry it and the check that proves it, or to the later stage that owns it; a row with no decision is "
                  "an open item in `summary` for the stage that must decide it. Topics a row needs in more depth "
                  "(migration, stored data, interactions): the Plan record guide's matching section "
                  "(GUIDES/plan-record.md), opened only for that row."),
        "keeps_ledger_anchors": ["GUIDES/plan-record.md"],
        "ledger_rows_to_change": ["step-plan-scope ('for the topics this item touches only')",
                                  "plan-record-code-data ('adds or moves code or stored data')",
                                  "plan-record-pinned-values ('replays a pinned value (fixed dice, seed data)')",
                                  "plan-record-interactions ('interactions, UI or service state')"],
        "decisions": ["owner decision 4.1 (A1) accepted 2026-10-18"],
    },
    {
        "id": "R3", "stage": "plan", "where": "DUTIES['plan'] item 19 (the folded _BACKCHAIN_ITEM)",
        "problem": "2,587 characters (20% of the plan duty) of child-loop mechanics for an optional route that, in its "
                   "own words, nothing refuses a plan without; it also prints `required_trivial_reviews: 0`, the field "
                   "all four Battleship planning reviews misread (plan E4). The Battleship plan read backchain SKILL.md "
                   "twice and the guide once to follow it (08-plan.actions.md).",
        "before": before("plan", "19"),
        "after": ("19. Run the dependency audit of the Backchain planning guide, then the printed `backchain-check` on "
                  "your candidate graph after each revision (a failure is a finding); cite its receipt in "
                  "`evidence_refs` and say in `summary` which route you took. An optional Backchain `plan`/`draft` "
                  "child follows the guide's Child request section; this packet does not require it."),
        "keeps_ledger_anchors": [],
        "decisions": ["moves mechanics to references/backchain-planning.md (reference, not reprint)"],
    },
    {
        "id": "R4", "stage": "plan", "where": "DUTIES['plan'] item 8 (interaction structure and Design basis)",
        "problem": "2,464 characters that restate INTERACTION_DESIGN (shiploop_prompts.py) already folded into spec "
                   "item 9 and research item 10, and the UI-ambition sentence step-plan item 9 repeats; the safeguards and "
                   "channel ladder are worded three times across stages.",
        "before": before("plan", "8"),
        "after": ("8. Record the interaction structure as AD-<n> in HOME/architecture.md: placement (the simplest that meets "
                  "HOME/spec.md; a single-user tool with no shared or lasting state runs in the client; server state, "
                  "identity, a store or a live channel only for a requirement that needs it, using the runtime's own "
                  "services first); the safeguards every placement keeps (HOME/spec.md's personal-data rules, a "
                  "server-side check on every action by a caller the product does not control, limits on anonymous "
                  "input, a record of every asynchronous failure that reaches whoever must act); per hop the lightest "
                  "channel that meets the stated freshness, with authoritative read-back after a push, gap or reconnect, "
                  "and each channel's and cache's quota cost. Then a Design basis in `summary`: baseline and delta, "
                  "recovery checks, deployment fit, and for a UI its component, interaction and skin premises, the design "
                  "guidance used and its interaction ambition (the request's, else ambitious; name each rich interaction "
                  "scaled back and why). Allocate each UI decision to its owning item (UI planning ownership guide)."),
        "keeps_ledger_anchors": [],
        "decisions": [],
    },
    {
        "id": "R5", "stage": "discovery", "where": "DUTIES['discovery'] items 9 and 11 (connected knowledge, service discovery)",
        "problem": "1,458 characters with no applicability gate: on Battleship's empty checkout the model read seven whole "
                   "guides (154,386 bytes, 02-discovery.actions.md) and recorded 'No MCP knowledge reader was required' "
                   "and 'Caching: none ... Not applicable' (run/notes/discovery.md). Plan G4.",
        "before": before("discovery", "9", "11"),
        "after": ("9. Applicability first. A checkout with nothing beyond its baseline commit: record `none` for house "
                  "style, skills, existing specs, services, consumers and the current-system and interaction baselines, "
                  "one line each, and spend discovery on the target, its identity and access (items 3, 4, 12). Otherwise, "
                  "and only for terms, services, caches or asynchronous flows the request or a discovered file names: "
                  "resolve internal terms with Connected knowledge discovery (open the content; keep private content off "
                  "public surfaces), and record in RUN/notes/discovery.md each service boundary's real capability, "
                  "identity, state owner, cache and async recovery owner, or the scoped probe that would settle it "
                  "(Service discovery guidance). An unavailable observation is not absence."),
        "keeps_ledger_anchors": [],
        "decisions": ["plan G4"],
    },
    {
        "id": "R6", "stage": "step-plan", "where": "DUTIES['step-plan'] item 5 (test_commands)",
        "problem": "Never says that ShipLoop reruns focused commands on base and mutated copies, so a focused command "
                   "against a remote copy must deploy the tree it judges (bs-build-1 gap 2: 0 of 8 mutants killed at "
                   "24-test); the gate's criterion coverage checks only that an ID is named (_normalise_criteria), which "
                   "the packet does not say (gap 3). Plan C1, B2.",
        "before": before("step-plan", "5"),
        "after": ("5. **`test_commands`** (`[{\"command\", \"suite\", \"ids\", \"criteria\"}]`), run from the repository "
                  "root; test and verify run exactly these, and ShipLoop reruns the focused rows on the item's base and "
                  "on mutated copies.\n"
                  "   - focused: this item's case IDs, with a reporter that prints one pass or fail line per test name "
                  "(platform card; never dot or junit). A listed ID counts only as its own word in a test's printed name "
                  "(`TC-4 (a)`, not `TC-4a`). `min_tests` where a command must run at least that many. A focused row "
                  "for a remote target deploys the tree it judges first.\n"
                  "   - regression: the retained suites the changed paths affect.\n"
                  "   - check: the lint, type and build commands HOME/environment.md records, judged by exit code, each "
                  "safe to repeat locally. None: `check_na` with the reason; no command at all: `test_commands_na`.\n"
                  "   - A row that names a criterion runs code on that criterion's paths; every criterion is named by "
                  "some row."),
        "keeps_ledger_anchors": ["each safe to repeat locally"],
        "decisions": ["plan C1, B2"],
    },
    {
        "id": "R7", "stage": "test-strategy", "where": "DUTIES['test-strategy'] items 1 and 2",
        "problem": "Two items open with the same source ('the spec changes since the run began') and split one plan "
                   "(new behaviour, preserved behaviour) across them.",
        "before": before("test-strategy", "1", "2"),
        "after": ("1. From HOME/spec.md, the spec changes since the run began (quoted below) and "
                  "RUN/notes/current-system-baseline.md, plan under HOME/environment.md ## Harnesses and suites, per "
                  "requirement: layers (unit, integration, system, consumer), negative cases, fixtures and data, "
                  "environment and authorization needs, required surface, due stage, owner and prerequisites; for a "
                  "state or data change its before and after checks (State and data assessment); for preserved "
                  "behaviour a preservation check (an unknown existing behaviour needs discovery first; an old pass is "
                  "not a current pass). Mark every check planned; name an expected-RED control where test-first "
                  "applies."),
        "keeps_ledger_anchors": [],
        "decisions": [],
    },
    {
        "id": "R8", "stage": "test-strategy", "where": "DUTIES['test-strategy'] item 11 (host-tool probe)",
        "problem": "Accepts a `file:` stand-in as the probe, which proves only that a browser runs, not that the "
                   "authenticated entry is reachable under this run's guard (06-test-strategy gap 2; plan H4); 669 "
                   "characters mixing the probe, the stand-in recipe, recording and the opt-in command.",
        "before": before("test-strategy", "11"),
        "after": ("11. A case needing a host tool (browser, device, account, service): name it (the host's tool listing "
                  "is the probe that it exists) and probe it now by doing the case's first step, against a stand-in "
                  "while the product does not exist (a one-line page in RUN/scratch by `file:` URL, or a harmless read), "
                  "and probe the target's entry gate (sign-in, visibility, permission) read-only by a route this run "
                  "allows. Cite each output in `evidence_refs`; record only a failed probe as an access gap under "
                  "## Real-boundary checks, with the requirement it leaves unobserved and its owner. Give the case its "
                  "own opt-in command so the default command passes without the tool."),
        "keeps_ledger_anchors": ["the host's tool listing is the probe"],
        "decisions": ["plan H4"],
    },
    {
        "id": "R9", "stage": "research", "where": "DUTIES['research'] items 3 and 11",
        "problem": "Item 3 restates discovery item 8 (the Recursive discovery policy and its shared allowance) almost "
                   "word for word; item 11 lets an assumption stay open when one allowed read-only command settles it "
                   "now (03-research gap; plan G6).",
        "before": before("research", "3", "11"),
        "after": ("3. (removed: the Recursive discovery policy line prints once, in the shared Rules of discovery and "
                  "research)\n"
                  "11. RUN/notes/research.md ## Assumptions: each load-bearing assumption (its failure would change a plan "
                  "decision, consumer or acceptance check), marked evidenced (locator), probed (command and saved output) "
                  "or open. One that a command this run may already run settles (a read-only query, an anonymous call) "
                  "is probed now; open is only for a check that needs a later artifact or a person (who, and why not "
                  "now). Plan builds its `assumptions` from it."),
        "keeps_ledger_anchors": [],
        "decisions": ["plan G6"],
    },
    {
        "id": "R10", "stage": "spec", "where": "DUTIES['spec'] item 9 (state and information lifecycle)",
        "problem": "860 characters restating INTERACTION_DESIGN; 'how simultaneous changes resolve' is the only "
                   "concurrency wording in any duty, which both runs read as not covering overlapping requests from one "
                   "client (chess play() race; Battleship's late race fix), and 'invent no level' read as no "
                   "accessibility work (100 unlabeled buttons). Plan A4.",
        "before": before("spec", "9"),
        "after": ("9. State and information lifecycle, as requirements in HOME/spec.md, in proportion to the request "
                  "(Interaction design guide). Per piece of state: owner and location; who may read it (what one user "
                  "must not see stays off that user's client); how simultaneous changes resolve, including overlapping "
                  "requests from one client (an action while another is pending; which response may update the state) "
                  "and a second session of the same user; what ends and removes it; the runtime quotas it meets. "
                  "Personal or secret data: where shown, stored and logged, how long kept, how removed. Add no identity, "
                  "sharing or persistence the request does not need; record a default for an open choice as an "
                  "assumption in `summary`. Affected UI: every control has an accessible name and status is text, even "
                  "when no accessibility level is requested; async feedback is truthful."),
        "keeps_ledger_anchors": [],
        "decisions": ["plan A4"],
    },
]
for r in REWRITES:
    r["before_chars"] = len(r["before"])
    r["after_chars"] = len(r["after"])
json.dump(REWRITES, open(sys.argv[2], "w"), indent=1)
print([(r["id"], r["before_chars"], r["after_chars"]) for r in REWRITES])
print("total", sum(r["before_chars"] for r in REWRITES), sum(r["after_chars"] for r in REWRITES))
