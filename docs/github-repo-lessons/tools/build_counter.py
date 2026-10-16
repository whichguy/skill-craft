"""Merge the six adversarial-research JSON files into load files for the Technique Atlas db.

Writes counterload/<id>.json (technique patches), crossload/<id>.json (new crosscuts docs) and metaload/overall.json.
"""
import json, glob, os, collections

BASE = os.path.dirname(os.path.abspath(__file__))
NOW = os.environ["NOW"]
SPEC = ("https://github.com/obra/superpowers/blob/HEAD/docs/superpowers/specs/"
        "2026-06-10-positive-instruction-redesign-design.md")

cards = {}
for f in sorted(glob.glob(os.path.join(BASE, "contra", "*.json"))):
    for c in json.load(open(f))["cards"]:
        cards[c["id"]] = c

# Correct the baseline card: the "0 placeholders in 60 plans" result is real and sits in the spec file, not in the PRs.
b = cards["baseline-pressure-test"]
b["summary"] = ("Anthropic's own skill guide prescribes evaluation-driven development with a no-skill baseline, and SkillsBench "
                "(curated skills +16 to +25pp, self-generated skills negative) shows skills must be validated, not assumed helpful. "
                "Superpowers' own 2026-06-10 micro-test shows what a baseline is for: current-generation Opus wrote 0 placeholders "
                "in 20 plans, then 40 of 40 clean plans on a harder 10-task spec, with or without the banned-patterns list.")
b["conclusion"] = ("The method is sound and endorsed by Anthropic; no credible source argues against baseline comparison. "
                   "Verified in the Superpowers spec file: 60 plans, no placeholders with or without the rule, so the rule was left "
                   "in place because it costs little and the counterfactual is unmeasurable. On Claude 5-era models the likely finding "
                   "is that many scaffolding rules are no-ops, which makes baselines more valuable, not less. The Opus 5.5 PR ablations "
                   "are small (2 runs per arm, one fixture). Verdict would drop if baseline results failed to predict real-use behavior.")
for x in b["contrarian"]:
    x["note"] = ("Opened PRs #2333/#2379 show building-during-planning 2/2 with the rule removed and 2/2 with no skill, versus 0/5 "
                 "with the rewrite. Small n: 2 runs per arm, one fixture. (The 0-in-60 placeholder result is in the spec file linked "
                 "in this card's claims, not in these PRs.)")
b["searched"] = b.get("searched", []) + ["Checked docs/superpowers/specs/2026-06-10-positive-instruction-redesign-design.md directly: 0/20 and 40/40 clean plans"]

CROSS = {
 "bitter-lesson-harness-scaffolding": ("Does less scaffolding win as models improve?", "Enforcement and hooks"),
 "reward-hacking-tampering": ("Do agents tamper with tests, graders and guards?", "Verification and review"),
 "broader-spec-driven-development": ("Is spec-driven development itself sound?", "Planning and specs"),
 "ai-review-measured-defect-reduction": ("Does AI review measurably reduce defects?", "Verification and review"),
 "cross-cutting-instruction-files-and-skills": ("Do instruction files and skills improve success?", "Prompt text"),
}

os.makedirs(os.path.join(BASE, "counterload"), exist_ok=True)
os.makedirs(os.path.join(BASE, "crossload"), exist_ok=True)
os.makedirs(os.path.join(BASE, "metaload"), exist_ok=True)

def counter_of(c):
    return {k: c.get(k) for k in ("verdict", "confidence", "summary", "contrarian", "failures", "conditions", "conclusion", "searched")}

tech_ids = []
for cid, c in cards.items():
    if cid in CROSS:
        title, cat = CROSS[cid]
        json.dump({"title": title, "category": cat, "summary": c["summary"], "counter": counter_of(c),
                   "verdict": c["verdict"], "added": NOW[:10], "updatedAt": NOW},
                  open(os.path.join(BASE, "crossload", cid + ".json"), "w"))
    else:
        tech_ids.append(cid)
        patch = {"counter": counter_of(c), "verdict": c["verdict"], "updatedAt": NOW}
        json.dump(patch, open(os.path.join(BASE, "counterload", cid + ".json"), "w"))

# baseline claim: link the spec file
exp = json.load(open(os.path.join(BASE, "export", "techniques", "baseline-pressure-test.json")))
claims = list(exp.get("claims", []))
claims.append({"text": "Superpowers' micro-test found 0 placeholders in 20 plans, then 40 of 40 clean plans on a harder spec, with or without the banned-patterns list.",
               "repo": "obra/superpowers", "path": "docs/superpowers/specs/2026-06-10-positive-instruction-redesign-design.md", "url": SPEC})
p = json.load(open(os.path.join(BASE, "counterload", "baseline-pressure-test.json")))
p["claims"] = claims
json.dump(p, open(os.path.join(BASE, "counterload", "baseline-pressure-test.json"), "w"))

tally = collections.Counter(cards[i]["verdict"] for i in tech_ids)
cross_tally = collections.Counter(cards[i]["verdict"] for i in CROSS)
overall = {
 "title": "Overall conclusion",
 "asOf": "2026-10-11",
 "tally": dict(tally), "crossTally": dict(cross_tally),
 "paragraphs": [
  "No technique in the catalogue was refuted outright. One was refuted for a specific use: removing edit tools is not a security boundary, because Bash can still write files, and a Claude 5-era Claude Code version still shows a subagent ignoring its own disallowedTools. Keep it as a soft guard and enforce read-only with a sandbox or a hook on Bash.",
  "The techniques that hold best put a script in charge of checking observed behavior: validators grounded in execution, a loop stop decided by a script, gates that read tool logs and exit codes. The weakest rely on the model obeying a prompt: numeric caps written in a prompt, spec-kit's marker limit, the trigger-only description rule (one uncontrolled anecdote), and hooks that the model has been seen to delete or route around. Evidence that agents fake or stale-report verification (35 of 101 'tests pass' claims untrue in one audit; reward-hacking attempts in about 80% of attempts on one hidden-test task) is the strongest reason to prefer script-checked evidence over model-written evidence.",
  "Several measured effects were small or absent on current models. Edit-format gains shrink to roughly 0 to 11 points over str_replace. No source supports a specific 30 to 50 percent context-fill threshold: the one Claude 5-era controlled test found Opus 5 flat with unrelated padding to 500k tokens but losing about 15% of solved tasks with task-related context at 250k, so relevance matters more than fill. SWE-bench Verified, where the 75 percent bash-only score comes from, was abandoned by OpenAI after an audit found at least 59.4 percent of audited failing problems had tests rejecting correct solutions. Treat the bash-only result as weak evidence about harness value.",
  "The most contested items are the ones your design leans on most. Delta-spec merge by code is contested with high confidence: OpenSpec's own maintainers are asking whether to stop merging deterministically after 46 fix commits since June, and several merge bugs remain open. Authored file-based handoffs have no controlled test against raw transcripts. Repo map versus agentic search is unresolved. Spec-driven development as a whole has respected critics (Böckeler, Beck) and only one small controlled result, in test generation.",
  "Most of the evidence is from Claude 4.x-era or non-Claude models, and Claude 5-specific controlled evidence is thin everywhere. Where it exists (a Sonnet 5 verifier ablation, an Opus 5 context test, Superpowers' Opus micro-tests) it points the same way: fewer prescriptive prompt rules, more script-side verification. The open questions that would change verdicts are cheap to test inside your own harness: sequential fresh stages against one long session, authored handoff against raw transcript, a prompted cap against a script-enforced one, and each prompt rule against a no-guidance control. That last test already pays off: the Superpowers placeholder rule was a no-op on current Opus.",
  "Reliability of this review: every cited URL returned HTTP 200 and the agents report opening the sources they cite, but several PDFs, issue bodies and secondary summaries were read only as abstracts or snippets and are marked in each card. I spot-checked one claim myself and found the adversarial agent wrong about it (see the baseline-test card); treat the rest as interim until you check the links you rely on."
 ],
 "updatedAt": NOW
}
json.dump(overall, open(os.path.join(BASE, "metaload", "overall.json"), "w"))
print(len(tech_ids), "technique patches;", len(CROSS), "crosscuts;", dict(tally), dict(cross_tally))
