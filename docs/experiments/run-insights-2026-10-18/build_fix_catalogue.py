"""Build SP/insights2/fix-catalogue.json: methodology, open items, already fixed, conflicts.

Read-only over the repository: reads the analysis JSON files to number the gaps and checks that every source fix item
(149 gaps, 18 report fixes, 8 SDLC recommendations, 31 packet-review cross-cutting findings) is covered exactly by an open
item or an already-fixed entry.  Run: python3 -I build_fix_catalogue.py
"""
import glob
import json
import os
import re
import sys

R = "/Users/dadleet/src/skill-craft/.claude/worktrees/shiploop-eff-int-c5f79b"
RA = R + "/docs/experiments/run-analysis-2026-10-18"
PR = R + "/docs/experiments/packet-review-2026-10-17"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fix-catalogue.json")

# ---------------------------------------------------------------- sources: number every gap like gaps-dump.txt
GAPS = {}
n = 0
for path in sorted(glob.glob(RA + "/*/analysis-*.json")):
    data = json.load(open(path))
    for step in data["steps"]:
        for k, text in enumerate(step.get("gaps", [])):
            n += 1
            GAPS[n] = {"file": os.path.relpath(path, R), "group": data["group"], "step": step["tag"], "index": k,
                       "text": text}
assert n == 149, n
FIXES = {}
for run in ("bs", "chess"):
    for k, row in enumerate(json.load(open(RA + "/tools/meta-" + run + ".json"))["fixes"], 1):
        FIXES[run + "#" + str(k)] = row
SDLC = json.load(open(RA + "/sdlc-audit.json"))
RECS = {"rec" + str(row["rank"]): row for row in SDLC["recommendations"]}
CROSS = {}
for path in sorted(glob.glob(PR + "/[A-F]-*.json")):
    for row in json.load(open(path))["cross_cutting"]:
        CROSS[row["id"]] = os.path.basename(path)
assert len(CROSS) == 31, len(CROSS)

# ---------------------------------------------------------------- methodology
METHODOLOGY = [
    {"id": "M1", "name": "The packet is the contract",
     "rule": "Every rule, accepted value and row shape a gate enforces is printed where the model acts: in the duty, the "
             "template or Checked by, generated from the same table or function the gate reads (allowed_consumers, "
             "_stage_gates, the validators), so the text cannot drift from the gate. A model that needs ShipLoop's "
             "source to learn what complete accepts is a packet defect, not a model defect.",
     "tested_by": "A render test pins the printed values to the gate's own table, and a route test builds a result "
                  "only from the printed template or example row and submits it through the real `complete "
                  "--check-only`. Live: reads of skills/shiploop/scripts/*.py per stage (E2E counters) fall towards 0.",
     "owner_rules": ["main tenet: context is cleared between stages, each packet works alone",
                     "test the route, not the wording"]},
    {"id": "M2", "name": "The script owns it",
     "rule": "What the script can know or compute (tree identity, reuse of a passed run, routing after a revise, which "
             "paths to commit, whether a command reads the tree) the script decides, records and prints; what it can "
             "check it refuses, and every refusal names its way out (the revise or blocked route). The model never "
             "re-derives state or decides to skip a check.",
     "tested_by": "A route test through the real CLI (fail-first with the source reverted), and each guard proven "
                  "against a mutant of the new code (the U9 pattern: one-byte edit, changed command list).",
     "owner_rules": ["scripts own graph position and state; the model does one step and reports done",
                     "test skip is fail-safe (skip only on script-proven 'nothing to test')",
                     "test the route, not the wording"]},
    {"id": "M3", "name": "By value, once",
     "rule": "Content the step acts on is printed by value at its point of use (the selected card section, ## "
             "Commands, the revise summary), each fact in one home and printed once per packet; everything else is a "
             "locator. Low-value repeats are removed rather than trimmed.",
     "tested_by": "render_diff's head table (every stage at or under 20,000 printed characters) and a test that a "
                  "repeated fact (an open item, a summary) appears once; live: file reads right after a print.",
     "owner_rules": ["compact packets printed whole", "reference, do not reprint unchanged long text"]},
    {"id": "M4", "name": "One step's context only",
     "rule": "A packet carries what this step needs: duties that cannot apply (an empty checkout, no service) shrink to "
             "a one-line trigger, and every pointer is precise enough to open only its section (heading plus line "
             "range).",
     "tested_by": "Render a fixture where the duty does not apply and assert the one-line trigger replaces it; for "
                  "every pointer, a test opens the printed line range and finds the named heading on its first line.",
     "owner_rules": ["KISS", "compact packets printed whole", "open only the section a step needs"]},
    {"id": "M5", "name": "Evidence is a script-run command with visible output",
     "rule": "A claim (a criterion, a platform behaviour, a reviewer's classification, a person procedure, a release "
             "confirm) is backed by a command that ran against the tree or target under test and whose output is "
             "saved; a check that reads the implementation's own text, or a run that cannot see the candidate, is not "
             "evidence.",
     "tested_by": "A fixture whose only evidence is text (a literal grep Proof, a command that ignores the tree) is "
                  "refused or flagged; live: mutants killed, Proofs that execute behaviour, probes saved under RUN.",
     "owner_rules": ["test pass is the evidence (progress = a script-run test that passed)",
                     "ShipLoop enterprise rigour"]},
    {"id": "M6", "name": "Platform knowledge lives in the platform card, linked where decided",
     "rule": "Runner reporters, deploy-before-test, tool-state paths and access probes are written once in "
             "references/platforms/<platform>.md (machine-readable parts declared there too) and linked by section at "
             "the stages that decide them (test-strategy, plan, step-plan, prepare); scripts stay generic and the card "
             "never contradicts the code.",
     "tested_by": "A render test that a run whose target is platform X prints GUIDES/platforms/X.md#<section> at "
                  "those stages; a card-versus-code test (the card's claim about a reporter or path class matches "
                  "shiploop_test_counts / item_scope); a grep test that scripts name no platform outside the card "
                  "loader.",
     "owner_rules": ["generic fixes only; platform detail only in references/platforms/"]},
    {"id": "M7", "name": "Every file has one writer and named consumers",
     "rule": "Each output (a committed path, an open item, a HOME section, loop state) has one stage or script that "
             "writes it and names who reads it, when and in what form; tool state with no decision is listed, not "
             "silently committed; a person's item carries the entry and a yes/no form the person can answer.",
     "tested_by": "A route test that an output without its writer or consumer is refused or left uncommitted "
                  "(untracked tool state is not committed by plan-return; a person-owned item without an entry line "
                  "is refused) and that report.html shows the consumer's form.",
     "owner_rules": ["produce for a consumer (every output names its consumer, when it reads it, in what form)"]},
    {"id": "M8", "name": "Recovery state is printed, not searched",
     "rule": "Whatever a model needs after a compaction, revise or reboot (its own previous result, the recorded "
             "passes, the next command, whether a narrative was shown) is printed by the script in the text the "
             "model reads first, computed from run records.",
     "tested_by": "A compaction or revise fixture: render after the recorded state and assert the line names it and "
                  "the one next command; live: file reads after each compaction.",
     "owner_rules": ["main tenet: context is cleared between stages", "stateless skill: scripts own the last "
                     "in-progress item, the model reports done"]},
    {"id": "M9", "name": "One wording per rule; contradictions are fixed at the home",
     "rule": "A rule has one wording in one constant, imported wherever it prints (the PROCEDURE_WALK pattern); when "
             "two texts disagree (authority versus focus, card versus parser, docstring versus route, narrative "
             "versus status), the home is fixed and every copy follows. Permissions are stated positively: what may "
             "run, under which grant.",
     "tested_by": "A test that every surface imports the one constant, and a card or docstring sentence asserted "
                  "against the code behaviour it describes.",
     "owner_rules": ["one supported version (no second wording kept for compatibility)", "KISS",
                     "prompts: concise, meaningful change"]},
    {"id": "M10", "name": "Decide early, prove late",
     "rule": "Each SDLC concern (UI, API, state, migration before and after, switchover, concurrency, security, "
             "accessibility, operations) is decided as data at the earliest stage that owns it, carried by ID to the "
             "steps and checks that prove it, and reviewed for coverage; a gate checks structure only, Improve "
             "judges substance.",
     "tested_by": "A structure gate route test (a missing concern row or an unmapped yes row is refused; a docs-only "
                  "item with every row `no` and a reason passes) and a live stateful case whose rows each name a "
                  "decision and a check.",
     "owner_rules": ["example apps are SDLC examples: judge by SDLC fidelity", "ShipLoop enterprise rigour"]},
]


def item(i, title, mech, theme, unit, wave, sources, run, step, quote, cite, change, where, test, route_test,
         status="open", depends=(), notes=None):
    row = {"id": i, "title": title, "mechanism": mech, "theme": theme, "unit": unit, "wave": wave, "status": status,
           "sources": list(sources),
           "evidence": {"run": run, "step": step, "quote": quote, "cite": cite},
           "change": change, "where": where, "test": test, "route_test": route_test}
    if depends:
        row["depends_on"] = list(depends)
    if notes:
        row["notes"] = notes
    return row


A = "R/docs/experiments/run-analysis-2026-10-18/"
ITEMS = [
    # ------------------------------------------------------------------ Theme A: SDLC concerns in the plan
    item("A1", "A concern map per work item replaces step-plan duty 9's prose", "M10", "A", "A1", "A",
         ["sdlc:rec1", "sdlc:structure", "sdlc:dim:System API interface", "sdlc:dim:Configuration and secrets",
          "sdlc:dim:Scale up and down", "sdlc:dim:Use of existing platform services"],
         "both", "11-step-plan (bs); 11, 17-step-plan (chess)",
         "Its own concern surface is duty 9, a free-text 'Plan record' that is ungated and was skipped or compressed "
         "in all four step-plan results.", A + "sdlc-audit.json structure.verdict",
         "Plan writes per work item one row per concern (15 ids) {id, applies, decision or reason, anchor, "
         "owner_stage}; step-plan maps each applies=yes row to steps and a check (or a later owner stage). Replaces "
         "duty 9's bullets (net shorter); the gate checks structure only; DUTIES['plan'] item 10's 'invent no decision "
         "ledger' is reworded to allow these rows (see conflict CF19).",
         "shiploop_prompts.py DUTIES['plan'] (new item beside 7-8), DUTIES['step-plan'] item 9 and "
         "_PLAN_RECORD_INTERACTIONS; shiploop_navigator._result_template and _stage_gates (plan, step-plan); "
         "shiploop_stage_spec.py step-plan done_when (one exit condition)",
         "Route test through `complete --check-only`: a plan missing a concern row and a step plan with an unmapped "
         "yes row are refused; a docs-only item with every row `no` and a reason is accepted (fail-first with the "
         "source reverted).", True),
    item("A2", "Insert the selected card's first section, not a pointer", "M3", "A", "A2", "A",
         ["sdlc:rec2", "sdlc:dim:User interface"],
         "both", "plan, step-plan, implement",
         "platforms/ui.md already states the exact rules both runs broke (overlapping requests; accessible names) and "
         "was opened 0 times", A + "sdlc-audit.json recommendations[rank 2].why",
         "Add a concern column to coding-guidance.md's Conditional index; each applies=yes concern selects its card "
         "section, and the step-plan Improve hand-off and implement packet print that section's first paragraph by "
         "value.",
         "references/coding-guidance.md (Conditional index); shiploop_navigator.step_block and improve_handoff_text; "
         "shiploop_prompts.STAGE_REFERENCES",
         "Render test: a UI item's implement packet carries the overlapping-request rule text; render_diff head table "
         "stays at or under 20,000 per stage; the implement Improve hand-off re-measured against U2's 12 KB.", False,
         depends=["A1"]),
    item("A3", "Decide activation at plan; release-plan refuses an entry with no activation step", "M10", "A", "A3",
         "A", ["sdlc:rec3", "sdlc:dim:Deployment switchover"],
         "both", "chess 37-38-release-verify; bs 24/38-test",
         "Chess deployed a hidden tab, release-verify blocked twice and the owner granted access out of band",
         A + "sdlc-audit.json recommendations[rank 3].why",
         "Plan records how the change goes live (deploy unit, visibility/permission step, order, compatibility "
         "window, rollback) and whether the test target is the delivery target (then every test deploy, mutation "
         "included, is a user-visible cutover with a restore obligation); spec item 6 treats a request rule that "
         "blocks the consumer entry as a material conflict; release-plan refuses `consumer_entry` with neither an "
         "access/activation step nor `activation_na: <reason>`.",
         "shiploop_prompts.py DUTIES['plan'] items 6/8, DUTIES['spec'] item 6, DUTIES['release-plan'] items 2 and 7; "
         "shiploop_navigator._result_template (release-plan consumer_entry), _stage_gates; "
         "shiploop_consumer_delivery.checked_lines",
         "Route test: a release-plan result whose consumer_entry has no activation step and no activation_na is "
         "refused by `complete`; a local-only package with activation_na and a reason is accepted.", True),
    item("A4", "Spec names two baselines: overlapping requests and accessible names", "M10", "A", "A4", "A",
         ["sdlc:rec4", "sdlc:dim:Concurrency", "sdlc:dim:Accessibility"],
         "both", "bs 21-improve-implement (race found late); chess shipped the play() race",
         "Found: an in-flight fire could resolve after New game and put the old game back on the board.",
         "SP/report-bs/in/21-improve-implement.actions.md (review-1.md write)",
         "Spec item 9 and the state-lifecycle text: for interactive or UI requests, which response may update the "
         "state when an action overlaps a pending one or a reset, and a second session of the same user; for affected "
         "UI, every control has an accessible name and status is text even when no accessibility level is requested.",
         "shiploop_prompts.py DUTIES['spec'] item 9; INTERACTION_DESIGN (state and information lifecycle)",
         "Render pin: an interactive request's spec packet carries both baselines, a CLI request's does not "
         "(names_interactions); live: the seat-reservations case's concern rows.", False),
    item("A5", "Migration before/after and API callers decided at plan", "M10", "A", "A5", "A",
         ["sdlc:rec6", "sdlc:dim:Data migration before the change (backfill, compatibility of existing data)",
          "sdlc:dim:Data migration after the change (cleanup, contraction)", "sdlc:skippable:entry-point criterion"],
         "battleship", "11-step-plan",
         "step-plan duty 3 public-entry-point argument/contract criterion (Battleship has none for the `game` input)",
         A + "sdlc-audit.json structure.skippable_without_refusal[1]",
         "Plan item 7: existing data needs backfill or compatibility before and cleanup or contraction after, each an "
         "item or step with an owner, or `none: <reason>`; an API change names its callers and versioning; link "
         "execution-planning.md#baseline-tests-and-migrations at plan, step-plan and release-plan; step-plan item 3's "
         "entry-point criterion is confirmed by its rejection test.",
         "shiploop_prompts.py DUTIES['plan'] item 7, DUTIES['step-plan'] item 3; STAGE_REFERENCES['plan'|'step-plan'|"
         "'release-plan']",
         "Render pins; the later data-migration case (decision 6) exercises the rows live.", False),
    item("A6", "Planning review focus checks concern coverage", "M10", "A", "A6", "A", ["sdlc:rec5"],
         "chess", "planning Improve hand-offs",
         "chess's 'Simultaneous editors are out of scope' passed about ten Improve handoffs unchallenged.",
         A + "sdlc-audit.json recommendations[rank 5].why",
         "Add to _REVIEW_FOCUS_ITEMS: a concern the item touches with no decision, owner or check, or scoped out "
         "although the request's actors can still trigger it (overlapping requests, a second tab, a hidden entry).",
         "shiploop_prompts._REVIEW_FOCUS_ITEMS (reaches PLANNING_REVIEW_FOCUS and _duty_focus)",
         "packet-completeness reads the new bullet's first line in every planning hand-off; render pin.", False,
         depends=["A1"]),
    item("A7a", "Identity out of committed knowledge, with a lint", "M2", "A", "A7", "A",
         ["sdlc:rec7", "sdlc:dim:Security and access"],
         "chess", "02-discovery (environment.md)",
         "Chess environment.md L10-11 committed the org username and instance URL; Battleship omitted them "
         "deliberately.", A + "sdlc-audit.json recommendations[rank 7].why",
         "Discovery item 12 records the target alias and account/org ID, never usernames or instance hosts; a "
         "knowledge-home lint refuses e-mail-shaped strings in HOME (example.com allowed) at the close that writes it.",
         "shiploop_prompts.py DUTIES['discovery'] item 12; shiploop_knowledge_home close check (or a shiploop_lint "
         "knowledge rule); references/platforms/salesforce.md 'Consumer entry access' (see CF12)",
         "Route test: a discovery close whose HOME/environment.md holds user@corp.com is refused; one holding "
         "user@example.com is accepted.", True),
    item("A7b", "Release-plan drafts the operations record", "M7", "A", "A7", "A",
         ["sdlc:rec8", "sdlc:dim:Observability and operations"],
         "chess", "37-38-release-verify (blocked; operations never ran)",
         "Chess ended blocked at release-verify, so no operations record (monitoring, recovery, cleanup) exists.",
         A + "sdlc-audit.json recommendations[rank 8].why",
         "Release-plan item 2 drafts HOME/environment.md's operations section (monitoring, recovery, cleanup, "
         "owners); operations verifies that draft instead of writing it first.",
         "shiploop_prompts.py DUTIES['release-plan'] item 2, DUTIES['operations'] item 1", "Render pin.", False),
    # ------------------------------------------------------------------ Theme B: step proofs that prove behaviour
    item("B1", "A behavioural Proof for a remote-only target", "M5", "B", "B1", "A", ["gap:1a", "gap:63"],
         "battleship", "11-step-plan",
         "leaves an org-only engine with no runnable behavioural Proof at any step, so the criteria were weakened to "
         "source strings", A + "bs/analysis-bs-build-1.json steps[11-step-plan].gaps[0]",
         "Replace 'Remote-only target: the recorded test route only. None runs now: change the step boundary.' with: "
         "a step Proof may deploy only the step's paths to the recorded development target and run a read-only probe "
         "the run's authority covers (decision 4.2), when plan (A3) recorded that target.",
         "shiploop_prompts.py DUTIES['step-plan'] item 4 (`check` bullet); shiploop_stage_spec.py step-plan "
         "done_when condition 3; shiploop_navigator.STEP_CHECK_PLACEHOLDER",
         "Route test: a step plan whose S1 check deploys S1's paths and runs a probe (stub CLI) passes check-only and "
         "the step-proof gate runs it at S1's done; stage-spec pair test for the changed condition.", True,
         depends=["A3", "F2"]),
    item("B2", "A check proves behaviour, not the implementation's text; a criterion's command observes its paths",
         "M5", "B", "B2", "A", ["gap:3", "gap:14"],
         "battleship", "11-step-plan, 20-implement",
         "Such a check dictates code form, not behaviour, as with S3's `length: 10` count and S2's 'cacheable' ban.",
         A + "bs/analysis-bs-build-1.json steps[20-implement].gaps[0]",
         "Step-plan item 4: a check that matches the implementation's own text (a literal, a token count) dictates "
         "form, not behaviour; item 5: the command that names a criterion observes that criterion's paths (today "
         "_normalise_criteria checks only that an ID is named).",
         "shiploop_prompts.py DUTIES['step-plan'] items 4-5; shiploop_navigator._normalise_criteria (docstring only)",
         "Render pin; live: count of step Proofs that grep source literals (Battleship S1-S3 had them).", False),
    item("B3", "Print the Proof with its directory", "M1", "B", "B3", "A", ["gap:11"],
         "battleship", "16-implement, 21-improve-implement",
         "The model ran it from the original checkout twice (here and in Improve 21).",
         A + "bs/analysis-bs-build-1.json steps[16-implement].gaps[2]",
         "The step block prints the model's own invocation as `cd <WORKTREE> && <proof>` (literal, absolute) beside "
         "'ShipLoop runs it from WORKTREE at done'.",
         "shiploop_navigator.step_block (Proof line), shared by the packet, head and Improve hand-off (W2-B)",
         "Render test: the Proof line reads `cd <worktree> && <check>` on all three surfaces (one-step-block test).",
         False),
    item("B4", "Implement probes the platform behaviour a design choice rests on", "M5", "B", "B4", "A", ["gap:10"],
         "battleship", "16-implement",
         "The belief 'Apex throws on signed Long overflow' drove the 16-bit-limb multiply. The org probe ran only the "
         "workaround", A + "bs/analysis-bs-build-1.json steps[16-implement].gaps[1]",
         "Implement item 2: a language or platform behaviour a design choice rests on is probed once (saved output in "
         "RUN/notes) before building on it.",
         "shiploop_prompts.py DUTIES['implement'] item 2", "Render pin.", False),
    item("B5", "A criterion whose behaviour a later test proves is unproven at its step", "M5", "B", "B5 (new)", "A",
         ["gap:9", "gap:1b"],
         "battleship", "16-implement",
         "let the model report 'C1 and C2 hold' from a string Proof. C2 itself says the later org methods 'exercise "
         "the behavior'.", A + "bs/analysis-bs-build-1.json steps[16-implement].gaps[0]",
         "A criterion may name the later test that proves its behaviour, distinct from the step check; the implement "
         "exit condition then says the step shows shape only and lists that behaviour as unproven (not_covered).",
         "shiploop_stage_spec.STEP_CRITERIA_CONDITION; shiploop_prompts.py DUTIES['step-plan'] item 3",
         "stage-spec pair test (both wordings equal); render pin.", False),
    # ------------------------------------------------------------------ Theme C: testing a remote-resident target
    item("C1", "A remote-resident focused command deploys the tree it judges; red_na at test-spec", "M5", "C", "C1",
         "A", ["gap:2", "gap:22a", "gap:6", "fix:bs#1"],
         "battleship", "11-step-plan, 13-test-spec, 24-test",
         "A focused command against a remote copy therefore has to deploy the tree it judges. The plan recorded plain "
         "`sf apex run test`", A + "bs/analysis-bs-build-1.json steps[11-step-plan].gaps[1]",
         "Step-plan item 5 says ShipLoop reruns focused commands on a base copy and on mutated copies, so a command "
         "whose runner reads a remote copy deploys the tree it judges first; test-spec item 3 records red_na there "
         "when the base run cannot see the base; the test Checked by and BASE_RULE say the same.",
         "shiploop_prompts.py DUTIES['step-plan'] item 5, DUTIES['test-spec'] item 3; shiploop_test_loop.BASE_RULE; "
         "shiploop_navigator._check_text",
         "Render pins; the gate that catches a violation is C2's sentinel.", False,
         notes="gap 2's Checked-by refusal of a 'remote focused row without a deploy' is not adopted: telling remote "
               "from local needs platform knowledge (CF17); C2 refuses the same fault generically."),
    item("C2", "Mutation sentinel; the refusal names the revise route", "M2", "C", "C2", "A",
         ["gap:16", "gap:19", "fix:bs#1"],
         "battleship", "24-test",
         "The docstring 'revise opens only at the cap' (shiploop_loops.py:744) misled the model into planning 11 "
         "refusals.", A + "bs/analysis-bs-build-1.json steps[24-test].gaps[3]",
         "Before sampling, run one build-breaking sentinel mutant; if every focused command still passes, refuse with "
         "'these commands do not read the tree under test: stop the Until Loop blocked and report revise naming the "
         "command' instead of 'Add or strengthen assertions'; correct the loops docstring the route text came from. "
         "Measured: tests/nav-3cc80f...-mutation-check-only.md killed 0 of 8.",
         "shiploop_mutation._check and mutation_check (refusal lines); shiploop_loops.check_loop_packet docstring",
         "Route test through `complete`: a fixture whose focused command ignores the tree is refused with the "
         "sentinel message and the revise route; a real test kills the sentinel and proceeds (fail-first).", True),
    item("C3", "Generated and test path classes for platform tool state, declared by the card", "M6", "C", "C3",
         "A", ["gap:18", "gap:35", "gap:64", "gap:38", "fix:bs#5"],
         "battleship", "24-test, 38-test, 39-document",
         "\"file\": \".sf/orgs/00Daj000018BzO3EAK/localSourceTracking/config\"",
         "bs run .shiploop-runs/work-20261018-040601-5105d5/run/tests/nav-3cc80f8581a743c6853ac37d64fa378b-mutation-"
         "check-only.md",
         "Add a `generated` class (never mutated, never committed by leftovers, marked in the changed-files line) and "
         "let the platform card declare its globs (`.sf/**`, `.sfdx/**` generated; `**/classes/*Test.cls` and its "
         "-meta.xml test), loaded by item_scope.classify.",
         "references/path-classes.json (order, generated); shiploop_item_scope.classify, CATALOG; "
         "shiploop_mutation._changed_lines; shiploop_navigator._commit_scope_lines; references/platforms/salesforce.md",
         "Unit: classify('.sf/orgs/x/localSourceTracking/HEAD') is generated and classify('force-app/main/default/"
         "classes/FooTest.cls') is test; route: the mutation sample of a fixture with .sf/ files holds none of them.",
         True),
    item("C4", "Complete takes a passed mutation check-only record on an unchanged tree", "M2", "C", "C4", "A",
         ["gap:33"],
         "battleship", "38-test",
         "mutation_check / shiploop_mutation reran about 171 s of deploys on an unchanged tree.",
         A + "bs/analysis-bs-build-2.json steps[38-test].gaps[0]",
         "Extend U9's reuse to the mutation check: a counted run takes a passed mutation-check-only record of the same "
         "stage, item, candidate tree and focused command list.",
         "shiploop_mutation.mutation_check (count=True); shiploop_test_loop._reused, mutation_check_only_path",
         "Route test (U9 pattern): check-only passes, complete runs 0 mutants; a one-byte edit or a changed command "
         "list reruns them; each guard proven against a mutant of the new code.", True),
    item("C5", "Restore a remote target after the last mutant", "M2", "C", "C5", "A", ["gap:34", "gap:22c"],
         "battleship", "38-test",
         "When a focused command writes to a remote target, no restore follows the mutation gate.",
         A + "bs/analysis-bs-build-2.json steps[38-test].gaps[1]",
         "After the last mutant, ShipLoop reruns the unmutated focused commands once and records it; the test packet "
         "says so.",
         "shiploop_mutation._check; shiploop_navigator._check_text (test)",
         "Route test with a recording stub runner: the last focused run uses the unmutated candidate; the record "
         "says restored.", True, depends=["A3"]),
    item("C6", "Salesforce card corrections (deploy before test, TAP, tool state, two wrong sentences)", "M6", "C",
         "C6", "A", ["gap:4", "gap:17", "gap:22b", "gap:106", "gap:108", "gap:132b", "gap:146b"],
         "both", "chess 22-implement; bs 11-step-plan, 24-test",
         "`sf project deploy` writes .sf/ into the worktree, which exit condition 1 and lint flag; the model ran "
         "`rm -rf .sf` here and again at 24.", A + "chess/analysis-chess-build.json steps[22-implement].gaps[2]",
         "salesforce.md: a focused Apex command deploys the tree before testing; TAP; '.sf/ and .sfdx/ are CLI "
         "state: the step that adds sfdx-project.json adds both to .gitignore'; make 'human output is refused as "
         "unread' match shiploop_test_counts; replace 'let the candidate run and the mutation check carry the proof' "
         "with the deploy requirement and who restores.",
         "references/platforms/salesforce.md (focused Apex test paragraph; a tool-state paragraph); "
         "shiploop_test_counts (if the parser is the side that changes)",
         "Card-versus-code test: a human-format Apex output fixture is refused or accepted exactly as the card says; "
         "card byte-bound test.", False),
    # ------------------------------------------------------------------ Theme D: revise without redoing
    item("D1", "Keep accepted implement steps after a test-commands-only revise", "M2", "D", "D1", "A",
         ["gap:20", "gap:21", "gap:27b", "fix:bs#3"],
         "battleship", "24-test -> 25..37",
         "A revise whose only defect is test_commands still re-runs test-spec, validate-existing, all 4 implement "
         "steps and their 4 Improves (stages 25-37).", A + "bs/analysis-bs-build-1.json steps[24-test].gaps[4]",
         "When _id_changes reports no change to steps, criteria or expectations, ShipLoop reruns each accepted step's "
         "Proof, carries the steps, and goes from step-plan (and test-spec if its IDs changed) to test (decision "
         "4.4); about 11 min of re-proving saved.",
         "shiploop_navigator.implement_progress, the revise routing, _upstream_line/_id_changes",
         "Route test: a revise whose amended plan changes only test_commands issues no implement packet and records "
         "rerun Proofs; one changing a step reissues that step.", True),
    item("D2", "An empty-diff, unchanged step records its Improve as not needed", "M2", "D", "D2", "A",
         ["gap:29", "gap:27a"],
         "battleship", "31-improve-implement",
         "ShipLoop knows the base and bound trees are equal (_review_base_line in shiploop_navigator.py) but still "
         "issues the review.", A + "bs/analysis-bs-build-2.json steps[31-improve-implement].gaps[1]",
         "When a step's diff is empty and its row unchanged, record its Improve as not needed with the reason "
         "instead of binding a review.",
         "shiploop_navigator._review_base_line and the step Improve schedule (stage_spec.with_improve('step'))",
         "Route test: an empty-diff unchanged step completes with an Improve record 'not needed'; a one-line diff "
         "binds a review.", True, notes="Needs the owner's word: see CF9."),
    item("D3", "Revisit lines for every revisited step and the test stage", "M8", "D", "D3", "A",
         ["gap:23", "gap:25", "gap:26", "gap:30", "gap:32", "gap:36", "fix:bs#7"],
         "battleship", "25-step-plan, 27-test-spec, 30-38",
         "_sent_back_results returns earlier[-1], the last implement result before the revise (S4), as the 'previous "
         "accepted implement result' for S1.", A + "bs/analysis-bs-build-2.json steps[30-implement].gaps[0]",
         "Each revisited implement step names its own step's accepted result; `test` joins REVISIT_STAGES ('you sent "
         "W1 back for X; the amended plan changed Y'); the revise summary is quoted whole once (no 600 cut, no "
         "duplicate LAST ACCEPTED block); _change_text matches test_commands rows on suite and IDs ('changed, same "
         "IDs').",
         "shiploop_navigator._sent_back_results, _revisit_lines, REVISIT_SUMMARY, REVISIT_STAGES, _change_text, "
         "_last_accepted_lines",
         "shiploop-revise route tests: drive a revise through the CLI and assert S1..S4 and test each name their own "
         "previous result; a deploy-prefix change reads 'changed (same IDs)'.", True),
    item("D4", "Revisit Improve keeps untouched steps; a merge or split cites evidence", "M5", "D", "D4", "A",
         ["gap:100", "gap:101"],
         "chess", "17-18 step-plan and its Improve",
         "Collapsed three steps to one; plan record not revisited", A + "sdlc-audit.json structure.step_plan_shape."
         "what_was_written.chess_17",
         "The revisit line of the Improve hand-off adds 'keep each step the revise evidence does not touch; a merge "
         "or split cites that evidence'; _REVIEW_FOCUS_STEPS adds 'steps merged or split without that evidence'.",
         "shiploop_navigator.improve_handoff_text (revisit line); shiploop_prompts._REVIEW_FOCUS_STEPS",
         "Render pin; packet-completeness reads the bullet's first line.", False),
    # ------------------------------------------------------------------ Theme E: rules in the packet
    item("E1", "Open items: example row, allowed values, positive gate, 'due here' label", "M1", "E", "E1", "B",
         ["gap:39", "gap:67", "gap:68", "gap:73", "gap:74", "gap:85", "gap:88", "gap:92", "fix:bs#4", "fix:chess#6"],
         "both", "bs 43-system-test-author, 46-product-acceptance; chess 13-test-spec",
         "The double-negative gate 'refuses ... an open item whose consumer is not a later outer stage' was read as "
         "forbidding later-stage consumers.", A + "bs/analysis-bs-release.json steps[43-system-test-author].gaps[1]",
         "OUTER templates print one example row {id, assumption, disposition: open, check, reason, consumer, owner}; "
         "the consumer placeholder and Checked by print allowed_consumers(stage) and the allowed due_stage values; "
         "gates worded positively; 'open items due here: none (N open for later stages)'; a person-only item names "
         "consumer handoff. Measured: 66 source reads (meta-bs fix 4).",
         "shiploop_navigator._CONSUMER_PLACEHOLDER, HANDOFF_SHAPES['assumptions'], _result_template (OUTER "
         "assumptions), _stage_gates, _source_lines; shiploop_assumptions.allowed_consumers; shiploop_unverified; "
         "DUTIES['release-verify'] item 6",
         "Render test: the printed list equals allowed_consumers(stage) for every OPEN_ITEM_STAGES stage; route test: "
         "a result built from the printed example row passes `complete --check-only` at system-test-author and "
         "product-acceptance.", True),
    item("E2", "Plan and step-plan gates stated in Checked by", "M1", "E", "E2", "B",
         ["gap:58", "gap:59", "gap:65", "fix:bs#6", "pr:C-2"],
         "battleship", "08-plan, 11-step-plan",
         "Plan and step-plan validation rules not in the packet (52 source reads; 1,610 s vs chess 1,032 s)",
         A + "tools/meta-bs.json fixes[5].issue",
         "Checked by and the templates state: evidence is an existing absolute path or an https URL; an ID moved "
         "under ## Superseded or ## Retired counts as kept; step paths are exact files or globs with no '*' across "
         "'/'; the expectation shapes; 'leave parallel_groups as []; the check computes it'.",
         "shiploop_navigator._stage_gates (plan, step-plan), _result_template, _backchain_lines, "
         "_normalise_work_items; shiploop_backchain_graph.compute_parallel_groups",
         "Render pins generated from the validators' constants; route test: a step plan written from the printed "
         "rules passes check-only on the node-fix-bug fixture.", True),
    item("E3", "Templates match their gates", "M1", "E", "E3", "B",
         ["gap:41", "gap:133", "gap:79", "gap:76", "gap:69", "gap:127", "gap:42"],
         "both", "bs 41-carry-forward, 43, 47-release-plan; chess 27, 11",
         "The model planned around a refusal that does not exist, because _placeholders only walks the hand-off "
         "fields.", A + "bs/analysis-bs-release.json steps[47-release-plan].gaps[4]",
         "carry-forward `skill: none` prints {decision, reason} only; the rollback recipe prints with the return "
         "plan's keep rows or is marked exempt; consumer_checks row shape inline; system_commands ids are the names "
         "the runner prints; the step-plan template's check row binds C1, not a later step's C2; 'named' for unnamed "
         "commands means the command text, whitespace collapsed, under ## Commands.",
         "shiploop_navigator._result_template, _placeholders, _unnamed_command_lines; shiploop_workspace.rollback_lines; "
         "shiploop_knowledge_home.unnamed_commands; DUTIES['release-plan'] item 6, DUTIES['system-test-author'] item 6",
         "Route test per stage: the printed template with its placeholders filled passes `complete --check-only`.",
         True),
    item("E4", "Loop gates in words", "M9", "E", "E4", "B",
         ["gap:37", "gap:51", "gap:70", "gap:81", "gap:134", "gap:96"],
         "battleship", "05/07/09/12-improve (prep), 44, 48",
         "2 means the unchanged-content gate, one trivial pass ... but the model reads it as a count. All 4 BS prep "
         "Improves show the misread.", A + "bs/analysis-bs-prep.json steps[05-improve-spec].gaps[0]",
         "Wherever the number prints (contract, receipt, Improve 'Review passes', Until Loop block) print the gate "
         "as words ('ends on the first trivial pass that leaves content unchanged'); each stage loop's Work says "
         "whether a trivial confirming pass is needed; the result line says a stopped receipt supports revise or "
         "blocked. The field keeps its upstream name (CF2).",
         "shiploop_loops.WORK, REPEAT, TRIVIAL_REVIEWS, _RESULT_HEAD; shiploop_navigator._loop_lines, "
         "_improve_two_pass_sentence; skills/improve/runtime/until-loop/scripts/until_loop_ephemeral.py (lean return "
         "text)",
         "Render pins whose gate words derive from TRIVIAL_REVIEWS / stage_spec.improve_gate; shiploop-loops suite.",
         False),
    item("E5", "One rule line: ShipLoop's scripts are not instructions", "M1", "E", "E5", "B",
         ["gap:129b", "pr:C-2"],
         "chess", "11-step-plan",
         "the plan depends on (which output line scores an ID, how expectations and the mutation gate run), so 16 "
         "calls went to ShipLoop's source.", A + "chess/analysis-chess-prep.json steps[11-step-plan].gaps[3]",
         "STAGE_RULES gains: 'ShipLoop's scripts are not instructions; this packet, Checked by and the guides hold "
         "every rule; `complete --check-only` quotes the shape it needs.'",
         "shiploop_prompts.STAGE_RULES",
         "Render pin; live: source reads per stage after E1, E2 and E9 land.", False, depends=["E1", "E2", "E9"]),
    item("E6", "Improve mechanics in the packet", "M1", "E", "E6", "B",
         ["gap:52", "gap:56", "gap:57", "gap:124", "gap:44"],
         "both", "chess 09-improve-plan; bs 05/07-improve, 42-improve-carry-forward",
         "The final_result and work_items rule lives in an 80 KB handoff that the model did not read, so it read "
         "shiploop_navigator.py instead", A + "chess/analysis-chess-prep.json steps[09-improve-plan].gaps[1]",
         "Improve packet: Improve has no --check-only; parent-return.md: when to pass --final-result and what it "
         "holds; History window: `git -C <WORKTREE> log -7 --format=full`; the route file named by heading and line "
         "range; the Evidence line says whether 'tree unchanged since the bind' applies per pass and that the "
         "reviewed stage's own HOME edits are not this review's changes.",
         "shiploop_navigator.improve_packet, _start_improve (parent-return.md), _render_improve (Evidence line); "
         "skills/improve/references/shiploop-route.md (History window)",
         "Render pins (shiploop-actual-improve-cli, shiploop-handoff).", False),
    item("E7", "Test-spec: a case for each regression ID the item adds; where a justified N/A goes", "M2", "E", "E7",
         "B", ["gap:7", "gap:93"],
         "battleship", "13-test-spec",
         "That left sameSeed, sink, gameOver, shotAfterGameOver, outOfRange, repeatShot and fullBoard without an "
         "oracle, RED or GREEN.", A + "bs/analysis-bs-build-1.json steps[13-test-spec].gaps[1]",
         "Test-spec item 1 and its gate: one row per focused ID and per regression ID the item itself adds; "
         "done_when names where a justified not-applicable goes (summary, naming the confirming command).",
         "shiploop_prompts.py DUTIES['test-spec'] item 1; shiploop_expectations.check_test_cases; "
         "shiploop_stage_spec.py test-spec done_when",
         "Route test: a test spec with a case for an item-added regression ID is accepted and one missing it is "
         "refused.", True),
    item("E8", "Outer stages: system-test's check-only is its run; product-acceptance carries open items", "M1", "E",
         "E8", "B", ["gap:71", "gap:72"],
         "battleship", "45-system-test, 46-product-acceptance",
         "It does not say the check-only run may serve as this stage's run, so the model wrote 'passed' into the "
         "result before any run existed.", A + "bs/analysis-bs-release.json steps[45-system-test].gaps[0]",
         "System-test item 3: the check-only rerun is this stage's run; write pass or fail after it. "
         "Product-acceptance item 3: carry earlier open items as unverified rows (it takes no assumptions list).",
         "shiploop_prompts.py DUTIES['system-test'] item 3, DUTIES['product-acceptance'] item 3", "Render pin.",
         False),
    item("E9", "Test mechanics stated at test-strategy and step-plan", "M1", "E", "E9 (new)", "B",
         ["gap:119", "gap:129a"],
         "chess", "06-test-strategy, 11-step-plan",
         "Which runner lines ShipLoop scores is stated only in the platform card and in shiploop_test_counts.py, and "
         "the model read the source.", A + "chess/analysis-chess-prep.json steps[06-test-strategy].gaps[1]",
         "One line each: ShipLoop scores an ID from the runner's own pass or fail line that names it (the platform "
         "card names the reporter); expectations run on the unchanged base at validate-existing; the mutation gate "
         "mutates changed product lines in a copy and reruns the focused commands.",
         "shiploop_prompts.py DUTIES['test-strategy'] item 9, DUTIES['step-plan'] items 5-6", "Render pin.", False),
    # ------------------------------------------------------------------ Theme F: Improve that catches what later stages hit
    item("F1a", "Focus: the remote-runtime example for 'does not run what it claims'", "M5", "F", "F1", "B",
         ["gap:5", "gap:8", "gap:55", "gap:61", "gap:66", "fix:bs#2"],
         "battleship", "07, 09, 12, 14-improve",
         "'a documented command that does not run what it claims on the target runtime' is too abstract. Reviewers "
         "read it as 'run it once, see RED'.", A + "bs/analysis-bs-prep.json steps[07-improve-test-strategy].gaps[0]",
         "The focus item gains a generic example: a test command against a remote runtime that does not deploy the "
         "tree under test first runs the old copy; a reporter the platform card says ShipLoop cannot read.",
         "shiploop_prompts._REVIEW_FOCUS_ITEMS", "Render and completeness pins.", False),
    item("F1b", "Focus: a deferred gap that can stop the request's outcome", "M10", "F", "F1", "B",
         ["gap:117", "gap:121"],
         "chess", "05, 07-improve",
         "The planning review focus has no condition for a deferred gap that can stop a request outcome.",
         A + "chess/analysis-chess-prep.json steps[05-improve-spec].gaps[1]",
         "Add: an open gap or assumption that can stop the request's outcome being reached or seen, parked at a later "
         "stage without a read-only check.",
         "shiploop_prompts._REVIEW_FOCUS_ITEMS", "Render and completeness pins.", False),
    item("F1c", "Focus: a behaviour a criterion states that no command exercises", "M5", "F", "F1", "B", ["gap:131"],
         "chess", "12-improve-step-plan",
         "The focus has no condition for a behaviour that a criterion states but that no command exercises",
         A + "chess/analysis-chess-prep.json steps[12-improve-step-plan].gaps[1]",
         "Extend _REVIEW_FOCUS_STEPS: '... or a behaviour a criterion states that no listed command exercises'.",
         "shiploop_prompts._REVIEW_FOCUS_STEPS", "Render and completeness pins.", False),
    item("F1d", "Release review: a planned dry run is not a release effect", "M9", "F", "F1", "B", ["gap:80"],
         "battleship", "48-improve-release-plan",
         "forbids 'execute or replay a release effect (a deployment ...)' without saying that a planned dry run is not "
         "a release effect.", A + "bs/analysis-bs-release.json steps[48-improve-release-plan].gaps[0]",
         "The release guard adds: 'A planned dry run (validate, check-only, plan, what-if) is not a release effect: "
         "run it once and record its exit code.'",
         "shiploop_prompts.py the release guard text beside 'Release operation guidance' (improve_stage_prompt)",
         "Render pin.", False),
    item("F1e", "Carry-forward review focus gains the procedure walk", "M1", "F", "F1", "B", ["gap:135"],
         "chess", "28-improve-carry-forward",
         "It lacks the procedure walk that the integration branch added to PLANNING_REVIEW_FOCUS",
         A + "chess/analysis-chess-release.json steps[28-improve-carry-forward].gaps[0]",
         "Add _PROCEDURE_ITEM to the carry-forward focus (it reviews HOME/architecture.md ## Real-boundary checks).",
         "shiploop_navigator._improve_focus (carry-forward branch); shiploop_prompts.END_REVIEW_FOCUS_HEAD",
         "Render pin that the carry-forward hand-off carries PROCEDURE_WALK.", False),
    item("F2", "Authority stated positively: what may deploy, what is a probe", "M9", "F", "F2", "B",
         ["gap:24", "gap:43", "gap:105", "gap:107", "fix:bs#8", "fix:chess#8"],
         "both", "bs 26-improve-step-plan, 42; chess 22-23",
         "'No push, deploy' (shiploop_navigator.py:7918) conflicts with the planning focus 'run it once and record "
         "the exit code'", A + "bs/analysis-bs-build-2.json steps[26-improve-step-plan].gaps[0]",
         "One authority constant (decision 4.3): the recorded test commands may run under the run's deploy grant; a "
         "read-only execute through the recorded route is a probe, not a deploy; a step Proof may deploy the step's "
         "paths to the development target (B1); nothing else deploys. Printed in the Improve opening's Authority, "
         "implement item 3, and the carry-forward Improve (its import rerun is the org proof).",
         "shiploop_navigator.improve_opening_text (## Authority); shiploop_prompts._IMPLEMENT_CHECK_INLINE, "
         "IMPLEMENT_STEP_REVIEW_FOCUS_HEAD (probe line); a new shared constant in shiploop_prompts",
         "A test that every surface imports the one constant; E2E guard log: deploys only by recorded commands.",
         False, depends=["A3"]),
    item("F3", "A pass is classified after its reads", "M5", "F", "F3", "B", ["gap:13", "gap:138"],
         "chess", "30-improve-system-test-author",
         "Improve accepts a trivial pass whose Read line names files the pass never opened before it decided.",
         A + "chess/analysis-chess-release.json steps[30-improve-system-test-author].gaps[0]",
         "The 'Review passes' paragraph: decide the classification only after the reads the Read line lists; "
         "improve-pass records whether each changed file was opened during the pass where the host logs reads.",
         "shiploop_navigator._render_improve ('Review passes'); the improve-pass handler (shiploop_skill_calls "
         "precedent)",
         "Render pin; a Claude fixture with a read log shows the recorded field.", False),
    item("F4", "Review focus cites Code craft, does not paraphrase it; a found dead branch is material", "M9", "F",
         "F4", "B", ["gap:12", "gap:28", "gap:40"],
         "battleship", "17, 31-improve-implement; 40-verify",
         "names dead code but does not say that a noticed instance is material. The reviewer judged it not material "
         "and passed.", A + "bs/analysis-bs-build-1.json steps[17-improve-implement].gaps[0]",
         "The implement and verify focus bullets cite rule numbers instead of a clipped paraphrase (which drops 'the "
         "received value'); add 'a found dead branch or misused error type is fixed, or recorded with a reason'.",
         "shiploop_prompts.IMPLEMENT_STEP_REVIEW_FOCUS_HEAD; DUTIES['verify'] review item 5",
         "Render pin; a test that a bullet naming 'Code craft N' does not restate rule N.", False),
    item("F5", "Replay a person procedure's scripted inputs through the product's API once", "M5", "F", "F5", "B",
         ["gap:137", "gap:144", "gap:147", "fix:chess#4"],
         "chess", "29-system-test-author, 34, 37-release-verify",
         "No step of the ask was checked against the deployed product before a person was asked.",
         A + "chess/analysis-chess-release.json steps[37-release-verify].gaps[0]",
         "Where the product exposes an API, replay the person's scripted inputs through it once (a recorded command) "
         "before asking; the person observes only what renders (chess's promotion line failed at a6a7).",
         "shiploop_prompts.py DUTIES['system-test-author'] item 7, DUTIES['release-verify'] item 6, _PROCEDURE_ITEM",
         "Render pin; live.", False, notes="Must respect read-only probing on the delivery target: CF13."),
    # ------------------------------------------------------------------ Theme G: references and platform knowledge
    item("G1", "Link the platform card where test decisions are made; prepare checks the focused commands", "M6",
         "G", "G1", "B", ["gap:53", "gap:62", "fix:bs#2"],
         "battleship", "06-test-strategy, 08-plan, 10-prepare, 11-step-plan",
         "The Salesforce card (deploy before test, TAP) never reached test-strategy, plan or step-plan",
         A + "tools/meta-bs.json fixes[1].issue",
         "STAGE_REFERENCES resolves the target's platform card section at test-strategy, plan, step-plan and prepare; "
         "prepare item 3 checks each recorded focused command runs the tree under test with a reporter ShipLoop "
         "reads; a user-mandated format stays the acceptance command.",
         "shiploop_navigator._stage_guide_lines, _cited_guides; shiploop_prompts.STAGE_REFERENCES, DUTIES['prepare'] "
         "item 3, DUTIES['test-strategy'] items 4/9",
         "Render test: a run whose environment names salesforce prints GUIDES/platforms/salesforce.md#<section> in "
         "those four heads; a python run prints python.md.", False),
    item("G2", "Guide pointers print their heading and line range", "M4", "G", "G2", "B",
         ["gap:45", "gap:48", "gap:111"],
         "chess", "02-discovery",
         "so on Grok the only cheap route is a whole-file read: 8 whole reads against 'never a whole reference file'.",
         A + "chess/analysis-chess-prep.json steps[02-discovery].gaps[1]",
         "Pointers print '<label>: <path> lines a-b (## <heading>)', computed at render from the reference's "
         "headings (about 360-800 KB of whole guides read per run).",
         "shiploop_navigator._stage_guide_lines, _cited_guides; shiploop_knowledge_home.outline (heading parser)",
         "Render test: for every STAGE_REFERENCES entry the printed range's first line is the named heading.", False),
    item("G3", "Quote ## Commands whole beside the knowledge table of contents", "M3", "G", "G3", "B", ["gap:60"],
         "battleship", "08-plan",
         "The BS packet lists environment.md as headings only, so those commands are never in view.",
         A + "bs/analysis-bs-prep.json steps[08-plan].gaps[2]",
         "reads_lines quotes HOME/environment.md ## Commands whole (bounded) beside the table of contents.",
         "shiploop_navigator.reads_lines; shiploop_knowledge_home.reads_quotes",
         "Render test and head table.", False, notes="Exception to owner decision D1: CF3."),
    item("G4", "Discovery: an empty-checkout branch; service, MCP and async duties by cue", "M4", "G", "G4", "B",
         ["gap:47", "gap:112", "pr:AX-7"],
         "chess", "02-discovery",
         "Duties 9 and 11 (MCP, service, cache and async discovery, 1.7 KB) apply to nothing in an empty repo (A2-2).",
         A + "chess/analysis-chess-prep.json steps[02-discovery].gaps[2]",
         "Discovery's first line for a checkout holding only the baseline commit: record none for house style, "
         "skills, specs, services and consumers and spend discovery on the target and access; the service/MCP/async "
         "duties print whole only when the request or intake names them, else a one-line trigger with its guide.",
         "shiploop_prompts.py DUTIES['discovery'] items 3-6, 9-13; names_interactions precedent",
         "Render test: the empty-checkout fixture prints the branch and the one-line triggers; a service request "
         "prints the full duties.", False, notes="Reverses U6's deliberate 'not changed': CF5."),
    item("G5", "Prelude packets say 'Work items: set by plan'", "M9", "G", "G5", "B", ["gap:46"],
         "battleship", "01-intake",
         "Prelude packets print 'Work items planned: 1; execution starts after the preparation graph completes.'",
         A + "bs/analysis-bs-prep.json steps[01-intake].gaps[1]",
         "Print 'Work items: set by plan' until plan is accepted (the narrative already says so).",
         "shiploop_navigator._run_context_lines", "Render pin.", False),
    item("G6", "Probe now; leave a walk trace; the spec self-check cites output", "M5", "G", "G6", "B",
         ["gap:49", "gap:50", "gap:114"],
         "chess", "04-spec",
         "Duty 10's self-check has no evidence obligation, so the model skipped it (0 check calls).",
         A + "chess/analysis-chess-prep.json steps[04-spec].gaps[0]",
         "Research item 11: an unknown one allowed read-only command settles is probed now and saved; open only for "
         "a later artifact or a person. Spec item 10: one 'Walked:' line per ordered procedure and one check per "
         "condition that can run, cited in evidence_refs.",
         "shiploop_prompts.py DUTIES['research'] item 11; _duty_focus (spec 10, test-strategy 13)",
         "Render pin.", False),
    # ------------------------------------------------------------------ Theme H: person-only acceptance
    item("H1", "Person-owned open items carry an entry line and yes/no checks; report.html shows a checklist", "M7",
         "H", "H1", "B", ["gap:86", "fix:bs#9", "pr:X-1"],
         "battleship", "51-release-verify",
         "A person-owned open item gets free text with no reply route.",
         A + "bs/analysis-bs-release.json steps[51-release-verify].gaps[1]",
         "Every open item whose owner is a person carries in `check` the entry line (URL path or menu) and one "
         "yes/no line per check; agent-only prohibitions stay out of a person's ask; report.html renders the lines "
         "as a checklist.",
         "shiploop_assumptions._FIELDS, check_files; DUTIES['release-verify'] item 6, DUTIES['system-test'] item 7, "
         "DUTIES['system-test-author'] item 7; shiploop_navigator._render_report",
         "Route test: a person-owned item without an entry line is refused at check-only; render test: report.html "
         "shows checkbox rows.", True, status="partial",
         notes="U7 gave the blocked ask this form; open items outside a block still lack it."),
    item("H2", "Person-only behaviour is a one-line expected outcome at release-plan", "M7", "H", "H2", "B",
         ["gap:142", "gap:148", "fix:chess#5"],
         "chess", "33-release-plan, 38-release-verify",
         "With O-behavior's expected listing six sequences, 'It loads and I can play it' is not a pass",
         A + "chess/analysis-chess-release.json steps[38-release-verify].gaps[0]",
         "When a behaviour obligation only a person can observe is planned, its `expected` is the one outcome a "
         "person confirms in one line; the detailed sequences go in the open item's check; a reply confirming that "
         "outcome is the passed observation (D6's narrower ask stays for the rest).",
         "shiploop_prompts.py DUTIES['release-plan'] item 6, DUTIES['release-verify'] item 6; "
         "shiploop_consumer_delivery._settling_template",
         "Route test: release-verify with a person reply confirming the one-line expected settles the behaviour "
         "obligation through the real delivery gate.", True, notes="See CF11."),
    item("H3", "Never open the target through a session or front-door URL", "M9", "H", "H3", "B", ["gap:149"],
         "chess", "38-release-verify",
         "Nothing stops the stage from routing around a person-only check with session credentials; only the E2E "
         "harness guard did.", A + "chess/analysis-chess-release.json steps[38-release-verify].gaps[1]",
         "Extend the session rule: opening the target through a session or front-door URL counts as using session "
         "contents; a signed-in browser is the person's step. Fix salesforce.md, which today recommends `sf org open "
         "--url-only` for browser checks (CF1).",
         "shiploop_prompts.STAGE_RULES ('Never read, keep or report credential-store or session contents'); "
         "references/platforms/salesforce.md (browser-session paragraph)",
         "A test that no card or duty recommends a front-door URL; E2E guard log has no `sf org open`.", False),
    item("H4", "The earliest stage that can check an entry prerequisite names and checks it", "M10", "H", "H4", "B",
         ["gap:54", "gap:118", "gap:115", "gap:113"],
         "chess", "03-research, 04-spec, 06-test-strategy",
         "R-2 deferred a gap that can stop a request outcome (the board opening) to the last stage.",
         A + "chess/analysis-chess-prep.json steps[04-spec].gaps[1]",
         "Test-strategy item 11 names the target-side entry gate (sign-in, visibility, permission) and checks it "
         "read-only, or records it under ## Real-boundary checks with who can grant it; spec item 4 names the "
         "earliest stage that can check an unresolved prerequisite (prepare at the latest); research item 4 names "
         "the consumer entry, not only the target.",
         "shiploop_prompts.py DUTIES['test-strategy'] item 11, DUTIES['spec'] item 4, DUTIES['research'] item 4",
         "Render pin.", False, status="partial", notes="Prepare item 6 (b4c9677c) already probes entry access."),
    # ------------------------------------------------------------------ Theme I: return and delivery
    item("I1", "Untracked tool state is not committed by the return", "M7", "I", "I1", "A",
         ["gap:82", "gap:132a", "gap:146a", "gap:77", "gap:143", "gap:145", "fix:bs#5", "fix:chess#7"],
         "both", "bs 49-release-check; chess 35-release-check",
         "committed: HEAD 45e3cc53, 0 files in HEAD, 18 uncommitted",
         "/Users/dadleet/e2e-runs/20261017/bs-sf-int-b7c77f/mismatch.md (Observed); worktree commit c5f3834 added "
         ".sf/orgs/.../localSourceTracking/{HEAD,config}",
         "commit_leftovers commits untracked paths only in declared classes (step-plan paths, docs, HOME) and lists "
         "the rest (generated, tool state) as 'undecided, not committed: add to .gitignore or keep with "
         "review-return'; release-plan item 4 lists untracked tool state for .gitignore before plan-return; the "
         "release-plan Improve scope names a return route a later command breaks.",
         "shiploop_workspace.commit_leftovers, _untracked; shiploop_stage_spec.RETURN_LEFTOVERS; shiploop_prompts.py "
         "DUTIES['release-plan'] item 4, IMPROVE_SCOPES['release-plan']",
         "Route test: a worktree with untracked .sf/ state and a new doc: plan-return commits the doc only, "
         "review-return keeps the fast-forward route, and the E2E 'committed' check passes.", True, depends=["C3"]),
    item("I2", "An unattended done packet records an uncommitted return as an open item", "M7", "I", "I2", "A",
         ["gap:89"],
         "battleship", "53-handoff",
         "The done packet says 'Ask the user to commit the returned files' even in an unattended run",
         A + "bs/analysis-bs-release.json steps[53-handoff].gaps[0]",
         "In an unattended run the working-tree return's commit message and paths become an open item in "
         "report.html, not a question to an absent user.",
         "shiploop_navigator._workspace_return_packet_lines, _render_report",
         "Route test: an unattended working-tree return's done packet has no 'Ask the user' line and report.html "
         "lists the item.", True),
    item("I3", "Present/absent confirm after earlier deploys; a consumer check observes the entry", "M5", "I", "I3",
         "A", ["gap:75", "gap:83", "gap:78"],
         "battleship", "47-release-plan, 49-release-check",
         "Here every test command deploys to org de, so 'absent' cannot be observed and both release-plan and "
         "release-check had to work around it.", A + "bs/analysis-bs-release.json steps[47-release-plan].gaps[0]",
         "When earlier stages already placed the candidate on the target, cite the last recorded absent observation "
         "and expect present at release-check; at least one consumer check observes what consumer_entry names.",
         "shiploop_prompts.py DUTIES['release-plan'] items 5-6, DUTIES['release-check'] item 4; shiploop_stage_spec.py "
         "release-check done_when",
         "stage-spec pair test for the changed condition; render pin.", False),
    item("I4", "Keep a failing dry run's output beside the retry's", "M5", "I", "I4", "A", ["gap:84"],
         "battleship", "49-release-check",
         "Item 3 saves the dry-run output to one file, so a retry after a fix overwrote the failing output.",
         A + "bs/analysis-bs-release.json steps[49-release-check].gaps[2]",
         "Release-check item 3 saves each dry run to its own numbered file.",
         "shiploop_prompts.py DUTIES['release-check'] item 3", "Render pin.", False),
    # ------------------------------------------------------------------ Theme J: duplicate runs
    item("J1", "Outer test stages reuse verify's passed runs on the same tree", "M2", "J", "J1", "C",
         ["gap:136", "gap:139", "pr:DX-2"],
         "chess", "29-system-test-author, 31-system-test",
         "After verify, the same three deploy+test commands ran 9 more times.",
         A + "chess/analysis-chess-release.json steps[29-system-test-author].gaps[0]",
         "A system command equal to one that passed at verify on the same product tree (tree identity checked by the "
         "script, as U9's _reused) is taken as run; system-test-author item 5 and system-test item 3 say ShipLoop's "
         "rerun at done is the run.",
         "shiploop_test_loop._reused, verify; shiploop_prompts.py DUTIES['system-test-author'] item 5, "
         "DUTIES['system-test'] item 3",
         "Route test: system-test's complete on an unchanged tree after verify runs 0 commands; a changed product "
         "path reruns them.", True),
    # ------------------------------------------------------------------ Theme K: recovery and context
    item("K1", "Improve recovery state where a compacted model looks", "M8", "K", "K1", "C", ["gap:15"],
         "battleship", "21-improve-implement",
         "Compaction recovery inside Improve still took 5 file reads to learn that review-1 was written but "
         "improve-pass had not run", A + "bs/analysis-bs-build-1.json steps[21-improve-implement].gaps[0]",
         "U10's 'Review progress' line prints only in ShipLoop's Improve packet, which a compaction inside the "
         "improve skill does not reprint; add the same line to the Until Loop receipt's handoff (the runtime tells "
         "a compacted model to read the receipt first) or the route file's recovery section.",
         "shiploop_navigator._improve_recovery_lines, _start_improve (contract handoff); "
         "skills/improve/references/shiploop-route.md",
         "Compaction fixture: with review-1.md written and no pass-1.json, the receipt handoff names it and the next "
         "command improve-pass.", False, status="partial"),
    item("K2", "Narrative: show only this packet's, never search", "M8", "K", "K2", "C", ["gap:31", "gap:90"],
         "battleship", "32-implement, 53-handoff",
         "does not say whether narratives missed before a context reset must be replayed, and the model went back and "
         "forth.", A + "bs/analysis-bs-release.json steps[53-handoff].gaps[1]",
         "narrative_lines: 'Show only this packet's narrative, once; never search for an earlier one.'",
         "shiploop_navigator.narrative_lines", "Render pin (shiploop-narrative).", False),
    item("K3", "Until Loop state lives under the run", "M7", "K", "K3", "C", ["gap:128"],
         "chess", "11-step-plan",
         "The Until Loop start command passes no state directory, so the runtime put the loop state in the system "
         "temp directory.", A + "chess/analysis-chess-prep.json steps[11-step-plan].gaps[2]",
         "start_command passes `--directory <run>/until-loop`, as the Improve start already does.",
         "shiploop_loops.start_command",
         "Route test: a started stage loop's state_file is under RUN/until-loop (callback-contract).", True),
    item("K4", "Open items quoted once per packet", "M3", "K", "K4", "C", ["gap:87"],
         "battleship", "51-release-verify",
         "Every stage re-listed the same open item, so release-verify's packet quotes A1 five times.",
         A + "bs/analysis-bs-release.json steps[51-release-verify].gaps[2]",
         "_source_lines dedupes open items by id and text and names their origin stages; open-item duties say an "
         "item already recorded for a later consumer stays open and is not re-listed; the shape text 'Later stages "
         "quote each' becomes 'ShipLoop quotes each' (CF15).",
         "shiploop_navigator._source_lines, _handoff_fault; shiploop_assumptions.open_items; DUTIES "
         "system-test-author 7, system-test 7, release-plan 6",
         "Render test: an item listed by three stages prints once.", False),
    # ------------------------------------------------------------------ Theme L: harness
    item("L1", "--keep-platform keeps a done run whose keep checks pass", "M2", "L", "L1", "A", ["fix:bs#10"],
         "battleship", "end of run (harness)",
         "Harness: --keep-platform cleaned up a done-but-uncommitted run; the Grok host idled 30 min after done",
         A + "tools/meta-bs.json fixes[9].issue",
         "keep_refusal keeps when ShipLoop is done and the case's keep checks pass, whatever the host exit code or "
         "the committed check.", "test/shiploop_e2e/run.py keep_refusal, keep_blocker, keep_check_names",
         "Harness unit test: done + rc=143 + committed failed -> kept.", False),
    item("L2", "End the host session when the done packet is printed", "M2", "L", "L2", "A",
         ["gap:91", "fix:bs#10"],
         "battleship", "53-handoff (harness)",
         "Harness, not directive: the Grok host did not exit after handle_prompt.done.",
         A + "bs/analysis-bs-release.json steps[53-handoff].gaps[2]",
         "run_agent ends the host when the done packet is observed instead of waiting for the timeout.",
         "test/shiploop_e2e/hosts.py run_agent; run.py",
         "Harness unit test with a fake host that idles after done.", False),
    # ------------------------------------------------------------------ Theme M (new): packet-review leftovers
    item("M1", "Drop the remaining low-value head lines", "M3", "M (new)", "M1", "C", ["pr:AX-6"],
         "chess", "every producer packet (packet review A)",
         "Recovery command repeated at the bottom 5.7 KB (line 2 already gives it)",
         "R/docs/experiments/packet-review-2026-10-17/A-preparation.json cross_cutting[AX-6].evidence",
         "Drop Last accepted where 'Results this stage builds on' names that result; drop the bottom Recovery block; "
         "the Progress view line out of producer heads (U5 removed the status block, not this line).",
         "shiploop_navigator._last_accepted_lines, _run_rules (Recovery lines), _producer_blocks ('progress-view')",
         "render_diff head table; shiploop-head-order.", False),
    item("M2", "Raise PRINT_LIMIT to 20,000", "M3", "M (new)", "M2", "C", ["pr:AX-2"],
         "chess", "discovery, research, spec, prepare (packet review A)",
         "Six of seven producer packets in this group exceed 16 KB.",
         "R/docs/experiments/packet-review-2026-10-17/A-preparation.json cross_cutting[AX-2].evidence",
         "PRINT_LIMIT 16,000 -> 20,000 (HEAD_LIMIT already is) so a packet under 20,000 prints whole; keep "
         "shiploop_status_hook.WINDOW consistent.",
         "shiploop_navigator.PRINT_LIMIT; shiploop_status_hook.WINDOW",
         "shiploop-head-order; status-hook window test.", False, status="partial",
         notes="AX-2(a), the guide lines in the head, is fixed by U3."),
]

# ---------------------------------------------------------------- already fixed (verified on the integration branch)
FIXED = [
    {"id": "AF1", "title": "Each step has its own Proof; checks scoped to their step; focus flags a check needing a later "
     "step", "sources": ["gap:94", "gap:95", "gap:98", "gap:99", "gap:126", "gap:130", "pr:BX-1", "pr:X4", "fix:chess#1"],
     "fixed_by": "603a709c; W2-A/B 12151c49 (merged 672973ae)",
     "verified": "shiploop_prompts.DUTIES['step-plan'] item 5: 'implement runs only each step's own `check`'; "
                 "_REVIEW_FOCUS_STEPS: 'a check that needs a later step's work'; shiploop_navigator.step_block: "
                 "'Proof (ShipLoop runs it from WORKTREE at done'",
     "live": "Battleship ran one Proof per step (run/tests/*-step-proof1.md, 8 records); no step merge"},
    {"id": "AF2", "title": "Revisited stages say why they are back and name their previous result",
     "sources": ["gap:97", "gap:102", "gap:103", "pr:X1", "pr:X2"],
     "fixed_by": "U4 0a3d8542 (merged 8b696a4f)",
     "verified": "shiploop_navigator.REVISIT_STAGES = (REVISE_TO, 'test-spec', 'implement'); _revisit_lines; "
                 "improve_handoff_text 'Revisit:' line",
     "live": "Battleship 25-step-plan printed it; residual: D3 (per step, test stage, truncation)"},
    {"id": "AF3", "title": "The implement head prints the step's criteria by value",
     "sources": ["gap:104"], "fixed_by": "U3/W2-B",
     "verified": "shiploop_navigator.step_block 'Serves (each criterion this step satisfies...'",
     "live": "Battleship implement packets read zero ShipLoop source (bs-build-1 run_level.directive)"},
    {"id": "AF4", "title": "ShipLoop fills the authority target and operation", "sources": ["gap:109"],
     "fixed_by": "U6 54651813",
     "verified": "shiploop_consumer_delivery._authority; template_assessment comment 'ShipLoop fills them in'",
     "live": "no authority refusal in Battleship"},
    {"id": "AF5", "title": "The head prints the guides its duties cite, with paths",
     "sources": ["gap:110", "pr:AX-2", "pr:C-1"], "fixed_by": "U3 0a3d8542",
     "verified": "shiploop_navigator._cited_guides (CitedGuides) and the LOOKUP 'guides' block",
     "live": "residual: G2 (line ranges); AX-2(b) open as M2"},
    {"id": "AF6", "title": "Host-neutral Improve invocation line", "sources": ["gap:116"], "fixed_by": "U6 54651813",
     "verified": "shiploop_navigator.improve_packet: 'the Skill tool, or /improve'", "live": "offline only"},
    {"id": "AF7", "title": "Knowledge by locator, request by its file, slim Improve hand-off",
     "sources": ["gap:120", "pr:AX-1", "pr:AX-3", "pr:BX-2", "pr:BX-3", "pr:X5", "pr:C-3", "pr:X-2"],
     "fixed_by": "U1/U2/D2 ab515869 (merged 0aefb458)",
     "verified": "shiploop_navigator.reads_lines docstring 'No file's text is quoted'; REQUEST_WHOLE_STAGES; "
                 "_reviewed_input_lines",
     "live": "Battleship; residual: G3 (## Commands lost from view)"},
    {"id": "AF8", "title": "UI ambition follows the request; module format only where it varies",
     "sources": ["gap:122"], "fixed_by": "U6 54651813",
     "verified": "DUTIES['plan'] item 8 'takes the ambition the request states'; item 13 'where the language has more "
                 "than one module format'", "live": "offline only"},
    {"id": "AF9", "title": "--notes takes a file", "sources": ["gap:123"], "fixed_by": "U6 54651813",
     "verified": "shiploop_protocol.py --notes metavar='FILE'", "live": "offline only"},
    {"id": "AF10", "title": "Consumer access probed read-only at prepare and release-check",
     "sources": ["gap:125", "fix:chess#3"], "fixed_by": "U7 b4c9677c (merged acee1c33)",
     "verified": "DUTIES['prepare'] item 6; DUTIES['release-check'] item 2; salesforce.md '## Consumer entry access "
                 "(read-only probe)'",
     "live": "Battleship: 'Consumer-access probe now exists (Battleship shows it works)' (sdlc-audit Security); "
             "residual: H4"},
    {"id": "AF11", "title": "Release-plan's delivery gate stated in Checked by and the template",
     "sources": ["gap:140", "gap:141", "fix:chess#2"], "fixed_by": "U6 54651813",
     "verified": "shiploop_consumer_delivery._settling_template, checked_lines; navigator _stage_gates",
     "live": "Battleship release-plan 5.3 min and 21 reads vs chess 12.5 min and 34 (meta-chess fixes[1])"},
    {"id": "AF12", "title": "Procedure walk in the shared review focus and test-spec",
     "sources": ["fix:chess#4"], "fixed_by": "W2-C 7d372c5a (merged 4cdf08ee)",
     "verified": "shiploop_prompts.PROCEDURE_WALK, _PROCEDURE_ITEM, _TEST_SPEC_PROCEDURE",
     "live": "not yet exercised by a reviewer; residual: F5, F1e"},
    {"id": "AF13", "title": "Answerable person ask; a partial reply continues (D6)", "sources": ["pr:X-1"],
     "fixed_by": "U7 b4c9677c; D6 b5dfef52",
     "verified": "DUTIES['release-verify'] item 6 'fill-in list, one yes/no line per case'; "
                 "shiploop_navigator._answered_lines", "live": "residual: H1, H2"},
    {"id": "AF14", "title": "One progress block per packet", "sources": ["pr:C-5", "pr:X-4"],
     "fixed_by": "U5 26c2932a", "verified": "shiploop_navigator.progress_lines, status_line; improve_packet",
     "live": "offline only"},
    {"id": "AF15", "title": "Stale pointer clause dropped", "sources": ["pr:AX-4", "pr:X3", "pr:C-4"],
     "fixed_by": "U6 54651813",
     "verified": "shiploop_prompts.packet_pointer has no 'or you need the duties or the template'",
     "live": "offline only"},
    {"id": "AF16", "title": "Each recorded command runs once; complete takes a passing check-only run",
     "sources": ["pr:DX-2"], "fixed_by": "U9 a3b2f975",
     "verified": "shiploop_test_loop.normalise_commands (_fold), _reused",
     "live": "residual: C4 (mutation not reused), J1 (cross-stage)"},
    {"id": "AF17", "title": "Improve recovery line after compaction", "sources": [], "fixed_by": "U10 b4c9677c",
     "verified": "shiploop_navigator._improve_recovery_lines",
     "live": "Battleship 21 still took 5 reads: the line is not where the compacted model looks (K1)"},
    {"id": "AF18", "title": "'ShipLoop navigator' prefixes: template heading dropped, header and refusal kept",
     "sources": ["pr:AX-5", "pr:BX-4", "pr:X6", "pr:DX-3", "pr:C-6", "pr:X-3"], "fixed_by": "U6 54651813, decision D4",
     "verified": "shiploop_navigator._compact_record / _result_contract_lines without the heading", "live": "closed"},
    {"id": "AF19", "title": "Code craft printed whole in code-craft packets (closed by decision)",
     "sources": ["pr:X7"], "fixed_by": "W2 disposition 'Code craft text kept'",
     "verified": "shiploop_prompts.IMPLEMENT_STEP_REVIEW_FOCUS = HEAD + CODE_CRAFT", "live": "closed (see CF6)"},
    {"id": "AF20", "title": "Heads under 20,000 at test, document and verify (offline)", "sources": ["pr:DX-1"],
     "fixed_by": "U3 re-measure e6a86587, fe18d950",
     "verified": "test/shiploop_e2e/packet_head_table.json _doc: 'every printed text stays under 20,000 at 83 and 163'",
     "live": "offline only"},
]

CONFLICTS = [
    {"id": "CF1", "items": ["H3", "C6"], "with": "references/platforms/salesforce.md browser-session paragraph; "
     "STAGE_RULES session rule",
     "what": "The card tells the model to open the browser through `sf org open --url-only` (a one-time front-door URL "
             "it calls 'a session credential'), which H3 forbids and which sits beside STAGE_RULES 'Never read, keep or "
             "report ... session contents'.", "resolve": "Fix the card in H3's change (M9: one wording)."},
    {"id": "CF2", "items": ["E4"], "with": "vendored until-loop runtime (until_loop_ephemeral.py keeps "
     "'required_trivial_reviews' under its upstream name); one supported version",
     "what": "Renaming the field forks the vendored runtime from upstream or needs a coordinated upstream release.",
     "resolve": "Keep the name; print the gate in words."},
    {"id": "CF3", "items": ["G3"], "with": "owner decision D1 (knowledge as a table of contents; U1 quotes no file "
     "text); 'reference, do not reprint'",
     "what": "Quoting ## Commands whole is a by-value exception to D1.",
     "resolve": "Owner OK for this one bounded section, with a byte cap."},
    {"id": "CF4", "items": ["A2"], "with": "compact packets printed whole; head <= 20,000; U2's 12 KB hand-off",
     "what": "Inserted card text grows heads and hand-offs.", "resolve": "Decision 5 accepted; measure after A1, "
     "first paragraph only."},
    {"id": "CF5", "items": ["G4"], "with": "U6 row: MCP/async/service duties 'Not changed, on purpose (conservative, "
     "KISS)'; main tenet", "what": "A missed cue drops a rule for a service-heavy run.",
     "resolve": "Keep a one-line trigger with its guide; owner confirms reversing U6's disposition."},
    {"id": "CF6", "items": ["F4"], "with": "compact packets: 'rules and code craft as one-liners'; W2 kept Code "
     "craft whole", "what": "Quoting rule 2 again in the focus adds a second wording.",
     "resolve": "Cite rule numbers; delete the paraphrase rather than extend it."},
    {"id": "CF7", "items": ["C3"], "with": "'platform detail only in references/platforms/'",
     "what": "`.sf/**` and `*Test.cls` in the package path-classes.json put Salesforce detail outside platforms/ "
             "(precedent: the metadata-nav globs already there).",
     "resolve": "The card declares its path classes; item_scope loads them."},
    {"id": "CF8", "items": ["B1", "F2", "C5"], "with": "A3 (test target equals delivery target)",
     "what": "In Battleship the development org was the delivery org: every step-Proof deploy, Improve deploy and "
             "mutant is a user-visible cutover.",
     "resolve": "A3 first; B1/F2 deploy grants and C5's restore apply per plan's recorded target decision."},
    {"id": "CF9", "items": ["D2", "D1"], "with": "owner decision 2026-10-10: an Improve child reviews every accepted "
     "implement step (comment above IMPLEMENT_STEP_REVIEW_FOCUS_HEAD)",
     "what": "D2 skips a step's Improve; D1 skips re-accepting steps.",
     "resolve": "D1 is accepted (decision 4.4: carried steps keep their earlier Improve); D2 needs the owner's word."},
    {"id": "CF10", "items": ["E5"], "with": "E1, E2, E9 (packet review C-2 risk)",
     "what": "The rule line before Checked by is complete pushes models into blind refusals.",
     "resolve": "Ship E5 after E1, E2 and E9."},
    {"id": "CF11", "items": ["H2"], "with": "decision D6 (a partial reply gets a narrower second ask)",
     "what": "gap 148 proposes 'do not ask again' when the person declines detail lines.",
     "resolve": "Keep D6; the one-line expected makes the second ask rare."},
    {"id": "CF12", "items": ["A7a"], "with": "salesforce.md 'Consumer entry access' (query by username; record "
     "grants under ## Access and accounts)",
     "what": "The probe needs the username, which the lint would refuse in HOME.",
     "resolve": "Record alias and user Id; resolve the username at run time from `sf org list`."},
    {"id": "CF13", "items": ["F5"], "with": "decision 4.3 (read-only probes only); A3",
     "what": "Replaying moves through the product API (anonymous Apex) can write state in the delivery org.",
     "resolve": "Replay inside a rolled-back transaction or on the development target only; else person-only."},
    {"id": "CF14", "items": ["J1"], "with": "'test skip is fail-safe'; system-test-author item 5 'Run each system "
     "command once now'", "what": "A model-decided skip is forbidden.",
     "resolve": "The script proves tree identity (U9 pattern) and words item 5 accordingly."},
    {"id": "CF15", "items": ["K4", "E1"], "with": "shiploop_navigator._handoff_fault shape text 'Later stages quote "
     "each until its consumer settles it'", "what": "Two wordings: stages re-list vs do not re-list.",
     "resolve": "One wording: ShipLoop quotes each open item once; stages do not re-record it."},
    {"id": "CF16", "items": ["B1"], "with": "STAGE_RULES 'Temporary files go in RUN/scratch'; step-plan item 4 'Tests "
     "are not a step'", "what": "Where the step's probe file lives: a committed repo file or a RUN file.",
     "resolve": "Pick one: a committed test-support path in the item's paths, so the Proof reruns at Improve import."},
    {"id": "CF17", "items": ["C1"], "with": "generic fixes only",
     "what": "gap 2 proposes refusing a 'remote focused row without a deploy', which needs platform knowledge.",
     "resolve": "Not adopted; C2's sentinel catches the same fault generically."},
    {"id": "CF18", "items": ["M2"], "with": "shiploop_status_hook.WINDOW = 16,000",
     "what": "A larger print can move the status line past the hook window.",
     "resolve": "Raise WINDOW with PRINT_LIMIT, or keep the progress block near the top (it is P0)."},
    {"id": "CF19", "items": ["A1"], "with": "DUTIES['plan'] item 10 and WORK_ITEM_CONTEXT 'invent no decision "
     "ledger'; owner rule against ledgers and gated prose",
     "what": "Concern rows read as a ledger under today's wording.",
     "resolve": "Decision 1 accepted (structure-only, replaces duty 9); reword item 10 in the same change."},
]


# ---------------------------------------------------------------- checks
def ids_of(rows):
    seen = []
    for row in rows:
        for src in row["sources"]:
            seen.append(src)
    return seen


def base(src):
    if src.startswith("gap:"):
        return "gap:" + re.sub(r"[a-z]$", "", src[4:])
    return src


errors = []
all_ids = [row["id"] for row in ITEMS]
if len(set(all_ids)) != len(all_ids):
    errors.append("duplicate item ids")
mechs = {m["id"] for m in METHODOLOGY}
for row in ITEMS:
    if row["mechanism"] not in mechs:
        errors.append(row["id"] + " bad mechanism")
    if len(row["evidence"]["quote"]) > 150:
        errors.append(row["id"] + " quote too long: " + str(len(row["evidence"]["quote"])))
    if row["wave"] not in ("A", "B", "C"):
        errors.append(row["id"] + " bad wave")
covered = {base(s) for s in ids_of(ITEMS) + ids_of(FIXED)}
expected = {"gap:" + str(k) for k in GAPS} | {"fix:" + k for k in FIXES} | {"sdlc:" + k for k in RECS} | \
           {"pr:" + k for k in CROSS}
missing = sorted(expected - covered, key=lambda s: (s.split(":")[0], int(s[4:]) if s[4:].isdigit() else 0, s))
unknown = sorted(s for s in covered if (s.startswith(("gap:", "fix:", "pr:")) or re.match(r"sdlc:rec", s))
                 and s not in expected)
if missing:
    errors.append("not covered: " + ", ".join(missing))
if unknown:
    errors.append("unknown source ids: " + ", ".join(unknown))
# a raw gap in two open items must be split a/b
from collections import Counter
open_gaps = Counter(s for s in ids_of(ITEMS) if s.startswith("gap:"))
for src, count in open_gaps.items():
    if count > 1:
        errors.append(src + " appears in " + str(count) + " open items")
fixed_gaps = {s for s in ids_of(FIXED) if s.startswith("gap:")}
both = {base(s) for s in ids_of(ITEMS) if s.startswith("gap:")} & fixed_gaps
if both:
    errors.append("gap in open and fixed: " + ", ".join(sorted(both)))
# a quote cited to an analysis gap must be in that gap's text ("..." elides)
CITE = re.compile(r"(bs|chess)/(analysis-[a-z0-9-]+\.json) steps\[([^\]]+)\]\.gaps\[(\d+)\]")
for row in ITEMS:
    match = CITE.search(row["evidence"]["cite"])
    if not match:
        continue
    path = RA + "/" + match.group(1) + "/" + match.group(2)
    step = next((s for s in json.load(open(path))["steps"] if s["tag"] == match.group(3)), None)
    if step is None or int(match.group(4)) >= len(step.get("gaps", [])):
        errors.append(row["id"] + " cite has no such gap: " + row["evidence"]["cite"])
        continue
    text = step["gaps"][int(match.group(4))]
    for part in row["evidence"]["quote"].split(" ... "):
        if part.strip().rstrip(".") not in text:
            errors.append(row["id"] + " quote part not in cited gap: " + part[:60])
for c in CONFLICTS:
    for i in c["items"]:
        if i not in all_ids:
            errors.append(c["id"] + " names unknown item " + i)
if errors:
    sys.exit("\n".join(errors))

# ---------------------------------------------------------------- counts and output
by_mech = Counter(row["mechanism"] for row in ITEMS)
by_wave = Counter(row["wave"] for row in ITEMS)
by_mech_wave = {m["id"]: {w: sum(1 for r in ITEMS if r["mechanism"] == m["id"] and r["wave"] == w)
                          for w in "ABC"} for m in METHODOLOGY}
gap_map = {}
for row in ITEMS:
    for s in row["sources"]:
        if s.startswith("gap:"):
            gap_map.setdefault(base(s), []).append(row["id"])
for row in FIXED:
    for s in row["sources"]:
        if s.startswith("gap:"):
            gap_map.setdefault(s, []).append(row["id"])
legend = {}
for k, g in GAPS.items():
    legend["gap:" + str(k)] = {"file": g["file"], "step": g["step"], "gaps_index": g["index"],
                               "mapped_to": gap_map.get("gap:" + str(k), [])}
out = {
    "meta": {
        "date": "2026-10-18",
        "branch": "feat/shiploop-eff-int-c5f79b at 71d7187c (no code change since the Battleship run; only docs)",
        "consumer": "the owner revising docs/shiploop-run-insights-plan-2026-10-18.md, then the session building the "
                    "units; read once per wave, as JSON",
        "method": "Every source fix item read; each open one checked against the code with git grep / reads of the "
                  "cited symbols; deduplicated into items, each mapped to one mechanism and one plan unit; coverage "
                  "asserted by build_fix_catalogue.py (every gap, report fix, SDLC recommendation and cross-cutting "
                  "finding lands in an item or an already-fixed entry).",
        "source_counts": {"gaps": len(GAPS), "report_fixes": len(FIXES), "sdlc_recommendations": len(RECS),
                          "packet_review_cross_cutting": len(CROSS)},
        "source_ids": "gap:N numbers the 149 `gaps` entries in sorted(glob('*/analysis-*.json')) order, steps then "
                      "entries (see gap_legend); a/b suffix = one part of a gap with two proposals; fix:bs#N / "
                      "fix:chess#N = tools/meta-*.json fixes[N-1]; sdlc:recN = sdlc-audit recommendations rank N; "
                      "pr:<ID> = packet-review cross_cutting id.",
        "counts": {"items": len(ITEMS), "already_fixed": len(FIXED), "conflicts": len(CONFLICTS),
                   "by_mechanism": dict(sorted(by_mech.items(), key=lambda kv: int(kv[0][1:]))),
                   "by_wave": dict(sorted(by_wave.items())), "by_mechanism_and_wave": by_mech_wave,
                   "route_tests": sum(1 for r in ITEMS if r["route_test"]),
                   "partial": sum(1 for r in ITEMS if r["status"] == "partial")},
    },
    "methodology": METHODOLOGY,
    "items": ITEMS,
    "already_fixed": FIXED,
    "conflicts": CONFLICTS,
    "gap_legend": legend,
}
with open(OUT, "w") as handle:
    json.dump(out, handle, indent=1, ensure_ascii=False)
    handle.write("\n")
print("wrote", OUT, os.path.getsize(OUT), "bytes")
print(json.dumps(out["meta"]["counts"], indent=1))
