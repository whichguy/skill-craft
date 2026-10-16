"""Build db load files for the ShipLoop-vs-Atlas comparison artifact."""
import json, glob, os, collections

BASE = os.path.dirname(os.path.abspath(__file__))
NOW = os.environ["NOW"]
SHA = "4b1759ac16a13953570f8f12f06f32b4da6ec866"
GH = "https://github.com/whichguy/skill-craft/blob/%s/" % SHA

CROSS = {
 "bitter-lesson-harness-scaffolding": "Does less scaffolding win as models improve?",
 "reward-hacking-tampering": "Do agents tamper with tests, graders and guards?",
 "broader-spec-driven-development": "Is spec-driven development itself sound?",
 "ai-review-measured-defect-reduction": "Does AI review measurably reduce defects?",
 "cross-cutting-instruction-files-and-skills": "Do instruction files and skills improve success?",
}
titles, cats, atlas_v = {}, {}, {}
for f in glob.glob(os.path.join(BASE, "export", "techniques", "*.json")):
    j = json.load(open(f)); cid = os.path.basename(f)[:-5]
    titles[cid] = j["title"]; cats[cid] = j["category"]
for f in glob.glob(os.path.join(BASE, "contra", "*.json")):
    for c in json.load(open(f))["cards"]:
        atlas_v[c["id"]] = c["verdict"]
for cid, t in CROSS.items():
    titles[cid] = t

os.makedirs(os.path.join(BASE, "cmpload"), exist_ok=True)
cards = {}
groups = {}
for f in sorted(glob.glob(os.path.join(BASE, "compare", "*.json"))):
    j = json.load(open(f))
    groups[os.path.basename(f)[:-5]] = j.get("groupSummary")
    for c in j["cards"]:
        cards[c["id"]] = c
for cid, c in cards.items():
    doc = {"title": titles.get(cid, cid), "category": cats.get(cid, "Cross-cutting"), "atlasVerdict": atlas_v.get(cid, ""),
           "isCross": cid in CROSS, "shiploop": c["shiploop"], "compare": c["compare"], "proposal": c["proposal"],
           "tests": c["tests"], "verdict": c["verdict"], "reason": c["reason"], "experiment": c.get("experiment", ""),
           "updatedAt": NOW}
    json.dump(doc, open(os.path.join(BASE, "cmpload", cid + ".json"), "w"))

tally = collections.Counter(c["verdict"] for c in cards.values())

def L(path): return GH + path

summary = {
 "commit": SHA, "commitUrl": "https://github.com/whichguy/skill-craft/commit/" + SHA,
 "commitWhen": "2026-10-11T14:48:05Z", "tally": dict(tally), "updatedAt": NOW,
 "paragraphs": [
  "Nothing in the atlas passes both of your tests for ShipLoop right now. Of 27 comparisons, 15 are already covered, 6 are skipped, 4 are on watch with a named trigger, 2 are worth a cheap experiment, and 0 are adopt. The reason is consistent: ShipLoop already does what survived the counter-evidence, which is script-side verification (it runs the recorded commands, reads test counts from runner output, requires new tests to fail on the base, mutation-checks them) and refusals that name the reason and the exact correction.",
  "Where ShipLoop deliberately differs from the popular repos, the counter-evidence backs ShipLoop. It edits the living spec in place with a script check that no requirement ID is dropped, instead of merging deltas by code (OpenSpec's own maintainers are now asking whether to stop merging deterministically). It defaults to inline execution, not a fresh agent per stage, after recorded handshake costs of 7 to 17 minutes. It has no per-finding validator agents, no repo map, no tool-list restrictions, and no per-model prompt forks.",
  "The evidence for changing anything is thin by design. In most cells ShipLoop's own record is one run, and no recorded run reached its loop caps or lost a requirement. Several cards were failed on YAGNI only because no failure is recorded, not because the idea is wrong. The list below is what is worth doing anyway: three free replays over runs you already have, one wording check, one experiment that could change the biggest decision, and one deletion."
 ],
 "candidates": [
  {"id": "c1", "title": "Replay saved runs for self-attested loop receipts", "kind": "free replay", "cost": "No code, minutes of reading",
   "why": "The Until Loop receipt's exit_assessment is the only script check on several Done-when lines and is the model's own claim. Your 2026-10-11 artifact-flow audit lists it as the top gap. In all 9 Checkers receipts it said satisfied at iteration 1, and one receipt said satisfied while its own evidence said the recorded check could not pass until a later step. Count implement receipts that claimed satisfied for a check that failed at the next script run. If the count is zero across saved runs, leave it alone.",
   "yagni": "pass", "kiss": "pass", "cards": ["evidence-gate"],
   "links": [{"text": "artifact-flow audit, row 1", "url": L("docs/shiploop-artifact-flow-2026-10-11.md")}, {"text": "loops.py check_loop_packet", "url": L("skills/shiploop/scripts/shiploop_loops.py")}]},
  {"id": "c2", "title": "Grep saved runs for waiver, red_na and retired_tests reasons", "kind": "free replay", "cost": "No code, one grep",
   "why": "Tamper resistance is structural today, and no tampering is recorded. lint_waivers is free text, so a quick look at the reasons actually written would show whether any pattern of convenient waivers exists. It is the cheapest test of whether the atlas's reward-hacking findings reach ShipLoop at all.",
   "yagni": "pass", "kiss": "pass", "cards": ["reward-hacking-tampering"],
   "links": [{"text": "test_loop.py (RED_NA, RETIRED_TESTS)", "url": L("skills/shiploop/scripts/shiploop_test_loop.py")}, {"text": "lint.py (lint_waivers)", "url": L("skills/shiploop/scripts/shiploop_lint.py")}]},
  {"id": "c3", "title": "Count awaiting.no_default refusals at early stages, then check one sentence", "kind": "replay, then a prose fix if warranted", "cost": "No code to measure; one sentence if the count is nonzero",
   "why": "references/requirements-definition.md tells the model to obtain the missing decision before dependent work and not guess. Your unattended rule S-14 says to record a default and continue. The no_default gate would catch a resulting block, so nothing may be broken. The 2026-10-11 Checkers run was also refused twice for putting an assumptions field at a non-plan stage. Measure how often the refusal fires before touching the sentence.",
   "yagni": "fail until measured", "kiss": "pass", "cards": ["cap-ambiguity"],
   "links": [{"text": "requirements-definition.md", "url": L("skills/shiploop/references/requirements-definition.md")}, {"text": "navigator _check_submitted_awaiting", "url": L("skills/shiploop/scripts/shiploop_navigator.py")}, {"text": "SPEC S-14", "url": L("test/shiploop_e2e/SPEC.md")}]},
  {"id": "c4", "title": "One bare-model control run before trimming any scaffolding", "kind": "experiment", "cost": "About 3 runs, roughly $10 to $20; the runner may need a small no-plugin mode",
   "why": "ShipLoop is about 36,900 lines of scripts, a 1,178-line SKILL.md, and 22 packets totalling 733k characters. All 25 Claude Sonnet 5.5 baseline rows pass, at $3.77 average for the trivial hello case, $4.50 for checkers and $6.32 for battleship. No bare-model control exists, and the comparison doc names the experiment but never ran it. The gates should stay regardless. This run decides whether the planning review loops and corrective text earn their cost, and it is the only item here that could change a large decision. The one measured value for the planning review bullet is positive: 10 of 15 plan errors caught against 0 of 15 without it.",
   "yagni": "pass (the decision is recorded as open)", "kiss": "pass (no skill change)", "cards": ["bitter-lesson-harness-scaffolding", "cross-cutting-instruction-files-and-skills"],
   "links": [{"text": "graph-engineering comparison", "url": L("docs/shiploop-graph-engineering-comparison-2026-10-04.md")}, {"text": "e2e plan, value versus a plain agent", "url": L("docs/shiploop-e2e-plan-2026-09-27.md")}, {"text": "baselines.jsonl", "url": L("test/shiploop_e2e/baselines.jsonl")}, {"text": "packet concision review", "url": L("docs/shiploop-packet-concision-2026-10-10.md")}]},
  {"id": "c5", "title": "Remove the Hermes row from host-matrix.md", "kind": "deletion", "cost": "One line",
   "why": "Found along the way, not from the atlas. Your checkout policy excludes Hermes from ShipLoop, but the published references/host-matrix.md still lists a Hermes row. This is a pure deletion. Your local copy of that file has uncommitted edits (8 added lines) and still has the row, so check before touching it.",
   "yagni": "pass (stated policy)", "kiss": "pass (removes)", "cards": [],
   "links": [{"text": "host-matrix.md", "url": L("skills/shiploop/references/host-matrix.md")}, {"text": "AGENTS.md (local checkout policy)", "url": L("AGENTS.md")}]}
 ],
 "watch": [
  {"card": "repo-map", "trigger": "A large existing-repo case, or a run that records orientation cost as a leading cost. Also conflicts with the technology-agnostic engine clause S-8."},
  {"card": "size-by-context", "trigger": "A run that records a compaction inside a single implement step. The recorded pressure so far comes from run-level accumulation."},
  {"card": "stop-is-script-owned", "trigger": "A run that reaches 11 refused runs with the same failing output. Until then a fingerprint stall rule has no observed need."},
  {"card": "ai-review-measured-defect-reduction", "trigger": "The second planning_review none probe. The repo already has the A/B instrument."},
  {"card": "broader-spec-driven-development", "trigger": "Paired planning_review none and stage runs on Claude 5, or a controlled spec-driven versus plain-prompting study. Planning took 375.9 minutes on Luna xhigh, 54 to 58 percent of it in Improve review children."},
  {"card": "cross-cutting-instruction-files-and-skills", "trigger": "When you need to justify ShipLoop against a plain agent, or the next Claude generation ships."}
 ],
 "method": "Five subagents compared 27 atlas cards with the published ShipLoop at the commit above, reading an export of origin/main. Every ShipLoop claim cites a file and symbol; all 189 evidence paths were checked to exist in the export. The lead spot-checked the loop-cap constants, the self-attested exit_assessment gap, the requirements-definition wording and the Hermes row. Your local checkout is 445 commits behind origin/main and holds uncommitted ShipLoop edits, so it was not used. Findings are interim.",
 "groups": groups
}
json.dump(summary, open(os.path.join(BASE, "cmpload", "_summary.json"), "w"))
print(len(cards), dict(tally))
