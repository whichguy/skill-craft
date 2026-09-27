#!/usr/bin/env python3
"""Review one ShipLoop E2E run and propose skill improvements.

Reads a run.py output directory (result.json, transcript.md, stderr, the
product in work/ and its .shiploop run state), gives it to a reviewer model
with read-only instructions, and asks three questions:

  1. What were the key learnings about the skill that we could improve?
  2. Which considerations should the skill take into account but does not?
  3. What could be optimized without removing key functionality?

Every proposal must keep ShipLoop's core premise (PREMISE below). The reviewer
marks each finding `preserves_premise`; the harness never applies one that
does not. Writes review.json and review.md into the run directory.

  python3 test/shiploop_e2e/review.py /tmp/shiploop-e2e/battleship-...
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import hosts  # noqa: E402

SPEC = Path(__file__).resolve().parent / "SPEC.md"
# The standing E2E specification is the premise: one copy, loaded, never restated.
PREMISE = ("Judge this run against the ShipLoop E2E specification below. Cite its clause IDs "
           "(S-1 ...) in every finding; a proposal that weakens a clause does not preserve the "
           "premise.\n\n" + SPEC.read_text(encoding="utf-8"))

QUESTIONS = """\
1. learnings: What were the key learnings about the skill that we could improve?
2. missing_considerations: Are there considerations the skill should take into
   account but does not?
3. optimizations: What could be optimized (speed, cost, turns, prompt size,
   clarity, reliability) without removing key functionality?

Then, separately, about this E2E harness (not ShipLoop), answer in "harness":
4. learning_retention: Should the harness retain key learnings or keep state in
   a different way?
5. further_learning: Is there something more we could learn from during
   subsequent passes?
6. evaluation_criteria: Are more evaluation criteria needed to re-evaluate
   ShipLoop's efficacy?"""

SCHEMA = """\
{
  "outcome": "one sentence: did the run deliver the request, and how well",
  "learnings": [FINDING, ...],
  "missing_considerations": [FINDING, ...],
  "optimizations": [FINDING, ...],
  "harness": {
    "learning_retention": {"answer": "...", "proposals": ["..."]},
    "further_learning": {"answer": "...", "proposals": ["..."]},
    "evaluation_criteria": {"answer": "...", "proposals": ["..."]}
  }
}
FINDING = {
  "title": "short imperative title",
  "evidence": "what in the run shows this; quote transcript lines or cite files",
  "proposal": "the concrete change to the skill",
  "files": ["skills/shiploop/... paths the change touches"],
  "severity": "material" or "minor",
  "preserves_premise": true or false,
  "premise_note": "why the change keeps (or breaks) script-owned navigation"
}"""

CATEGORIES = ("learnings", "missing_considerations", "optimizations")
# About the harness itself; recorded in the learnings, never handed to the ShipLoop improver.
HARNESS_QUESTIONS = ("learning_retention", "further_learning", "evaluation_criteria")


def reviewer_prompt(run_dir: Path, skill_root: Path, prior_learnings: str = "") -> str:
    prior = (f"""
Learnings recorded by earlier iterations (the last three commit messages). Build on them:
check whether this run confirms, contradicts or moves past them, and do not re-report a
finding that was already applied unless this run shows it did not work.

{prior_learnings.strip()}
""" if prior_learnings.strip() else "")
    return f"""You are reviewing one end-to-end run of the ShipLoop skill so the skill can be improved.
Do not modify any file. Read only.

{PREMISE}
{prior}
The run: a headless agent was started in an empty directory and asked to run ShipLoop
on the request in {run_dir / 'prompt.txt'}.
- Graded result: {run_dir / 'result.json'}
- Readable transcript (messages, tool calls, outputs): {run_dir / 'transcript.md'}
- Raw event stream: {run_dir / 'events.jsonl'}; host stderr: {run_dir / 'stderr.txt'}
- The product: {run_dir / 'work'}; the ShipLoop run directory is named by result.json
  shiploop.run_dir (it may sit beside work/, in an external workspace root)
- Where ShipLoop spent turns, time and cost per accepted stage, its failed commands,
  truncations and compactions: {run_dir / 'metrics.json'}
- The ShipLoop skill source that ran: {skill_root} (SKILL.md, references/, scripts/)

If result.json has a follow_on block, this run added a feature in a copy of an earlier
run's repository (follow_on.prior). Then also judge retention: did ShipLoop find and use
the earlier docs/shiploop/ spec, environment and test-strategy notes and extend the
existing modules and tests, or did it rediscover or rebuild beside them? Compare its
turns and cost with the earlier run.

Answer, from evidence in this run:
{QUESTIONS}

Prefer few, well-evidenced findings over many speculative ones. Mark a finding
"material" only when it would change the outcome, cost or reliability of a run like
this one. Set preserves_premise=false for anything that moves navigation into the model.

End your reply with exactly one ```json fenced block matching:
{SCHEMA}
"""


def last_commit_messages(repo: Path, count: int = 3) -> str:
    """The last `count` full commit messages: the learnings the next step builds on."""
    return subprocess.run(["git", "-C", str(repo), "log", f"-{count}", "--format=commit %h%n%B"],
                          check=True, capture_output=True, text=True).stdout


def render_markdown(review: dict) -> str:
    lines = ["# ShipLoop E2E review", "", review.get("outcome", ""), ""]
    for category in CATEGORIES:
        lines += [f"## {category.replace('_', ' ').capitalize()}", ""]
        for finding in review.get(category) or []:
            premise = "keeps premise" if finding.get("preserves_premise") else "BREAKS PREMISE (rejected)"
            lines += [f"- **{finding.get('title')}** ({finding.get('severity')}, {premise})",
                      f"  - Evidence: {finding.get('evidence')}",
                      f"  - Proposal: {finding.get('proposal')}"]
            if finding.get("files"):
                lines.append(f"  - Files: {', '.join(finding['files'])}")
        lines.append("")
    harness = review.get("harness") if isinstance(review.get("harness"), dict) else {}
    lines += ["## Harness", ""]
    for key in HARNESS_QUESTIONS:
        row = harness.get(key) if isinstance(harness.get(key), dict) else {}
        lines.append(f"- **{key.replace('_', ' ').capitalize()}:** {row.get('answer', 'not answered')}")
        lines += [f"  - {proposal}" for proposal in row.get("proposals") or []]
    lines.append("")
    return "\n".join(lines)


def actionable(review: dict) -> list[dict]:
    """Material findings that keep the premise, in question order."""
    return [dict(finding, category=category) for category in CATEGORIES
            for finding in review.get(category) or []
            if isinstance(finding, dict) and finding.get("severity") == "material"
            and finding.get("preserves_premise") is True]


def review(run_dir: Path, *, host: str = "grok", model: str | None = None, effort: str | None = None,
           skill_root: Path = ROOT / "skills" / "shiploop", max_turns: int = 60, timeout: int = 1200,
           prior_learnings: str = "", grok_bin: str = "grok", claude_bin: str = "claude",
           codex_bin: str = "codex") -> dict:
    run_dir = run_dir.resolve()
    agent = hosts.host(host, {"grok": grok_bin, "claude": claude_bin, "codex": codex_bin}[host])
    stage = run_dir / "review"
    stage.mkdir(exist_ok=False)
    env = agent.env(stage / "home")
    argv = agent.argv(prompt=reviewer_prompt(run_dir, skill_root.resolve(), prior_learnings),
                      prompt_file=stage / "prompt.txt", cwd=run_dir, model=model or agent.model,
                      effort=effort or agent.effort, permission_mode="auto", max_turns=max_turns)
    process = hosts.run_agent(argv, run_dir, env, stage / "events.jsonl", stage / "stderr.txt", timeout,
                              translate=agent.translator())
    parsed = hosts.last_json_object(hosts.final_text(stage / "events.jsonl"))
    if parsed is None:
        parsed = {"outcome": f"reviewer produced no JSON ({process['status']})"}
    parsed["process"] = process
    parsed["actionable"] = actionable(parsed)
    (run_dir / "review.json").write_text(json.dumps(parsed, indent=2) + "\n")
    (run_dir / "review.md").write_text(render_markdown(parsed))
    return parsed


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("run_dir", type=Path, help="a run.py output directory")
    p.add_argument("--host", choices=sorted(hosts.HOSTS), default="grok")
    p.add_argument("--model")
    p.add_argument("--effort")
    p.add_argument("--skill-root", type=Path, default=ROOT / "skills" / "shiploop")
    p.add_argument("--no-prior-learnings", action="store_true",
                   help="do not give the reviewer the last three commit messages of this checkout")
    args = p.parse_args(argv)
    prior = "" if args.no_prior_learnings else last_commit_messages(ROOT)
    result = review(args.run_dir, host=args.host, model=args.model, effort=args.effort,
                    skill_root=args.skill_root, prior_learnings=prior)
    print((args.run_dir / "review.md").read_text())
    print(f"actionable findings: {len(result['actionable'])}")
    return 0 if result["process"]["status"] == "exited" and "learnings" in result else 1


if __name__ == "__main__":
    raise SystemExit(main())
