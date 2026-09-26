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
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import hosts  # noqa: E402

PREMISE = """\
ShipLoop's core premise, which no proposal may weaken: the script is the
orchestrator. It keeps durable Markdown navigation state, walks the SDLC graph,
and returns the prompt for the current step together with the one completion
callback. The model is a library call: it performs that one step, runs the
printed callback and follows the next packet. It never chooses a successor,
reorders stages or decides which prompt comes next. A proposal that moves graph
navigation, successor choice or prompt selection into the model does not
preserve the premise."""

QUESTIONS = """\
1. learnings: What were the key learnings about the skill that we could improve?
2. missing_considerations: Are there considerations the skill should take into
   account but does not?
3. optimizations: What could be optimized (speed, cost, turns, prompt size,
   clarity, reliability) without removing key functionality?"""

SCHEMA = """\
{
  "outcome": "one sentence: did the run deliver the request, and how well",
  "learnings": [FINDING, ...],
  "missing_considerations": [FINDING, ...],
  "optimizations": [FINDING, ...]
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


def reviewer_prompt(run_dir: Path, skill_root: Path) -> str:
    return f"""You are reviewing one end-to-end run of the ShipLoop skill so the skill can be improved.
Do not modify any file. Read only.

{PREMISE}

The run: a headless agent was started in an empty directory and asked to run ShipLoop
on the request in {run_dir / 'prompt.txt'}.
- Graded result: {run_dir / 'result.json'}
- Readable transcript (messages, tool calls, outputs): {run_dir / 'transcript.md'}
- Raw event stream: {run_dir / 'events.jsonl'}; host stderr: {run_dir / 'stderr.txt'}
- The product and its ShipLoop run state: {run_dir / 'work'} (see work/.shiploop/)
- The ShipLoop skill source that ran: {skill_root} (SKILL.md, references/, scripts/)

Answer, from evidence in this run:
{QUESTIONS}

Prefer few, well-evidenced findings over many speculative ones. Mark a finding
"material" only when it would change the outcome, cost or reliability of a run like
this one. Set preserves_premise=false for anything that moves navigation into the model.

End your reply with exactly one ```json fenced block matching:
{SCHEMA}
"""


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
    return "\n".join(lines)


def actionable(review: dict) -> list[dict]:
    """Material findings that keep the premise, in question order."""
    return [dict(finding, category=category) for category in CATEGORIES
            for finding in review.get(category) or []
            if isinstance(finding, dict) and finding.get("severity") == "material"
            and finding.get("preserves_premise") is True]


def review(run_dir: Path, *, host: str = "grok", model: str | None = None, effort: str | None = None,
           skill_root: Path = ROOT / "skills" / "shiploop", max_turns: int = 60, timeout: int = 1200,
           grok_bin: str = "grok", claude_bin: str = "claude") -> dict:
    run_dir = run_dir.resolve()
    defaults = hosts.HOST_DEFAULTS[host]
    stage = run_dir / "review"
    stage.mkdir(exist_ok=False)
    env = hosts.grok_env(stage / "home") if host == "grok" else dict(os.environ)
    argv = hosts.argv_for(host, prompt=reviewer_prompt(run_dir, skill_root.resolve()),
                          prompt_file=stage / "prompt.txt", cwd=run_dir, model=model or defaults["model"],
                          effort=effort or defaults["effort"], permission_mode="auto", max_turns=max_turns,
                          grok_bin=grok_bin, claude_bin=claude_bin)
    process = hosts.run_agent(argv, run_dir, env, stage / "events.jsonl", stage / "stderr.txt", timeout)
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
    p.add_argument("--host", choices=sorted(hosts.HOST_DEFAULTS), default="grok")
    p.add_argument("--model")
    p.add_argument("--effort")
    p.add_argument("--skill-root", type=Path, default=ROOT / "skills" / "shiploop")
    args = p.parse_args(argv)
    result = review(args.run_dir, host=args.host, model=args.model, effort=args.effort,
                    skill_root=args.skill_root)
    print((args.run_dir / "review.md").read_text())
    print(f"actionable findings: {len(result['actionable'])}")
    return 0 if result["process"]["status"] == "exited" and "learnings" in result else 1


if __name__ == "__main__":
    raise SystemExit(main())
