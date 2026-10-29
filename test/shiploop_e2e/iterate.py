#!/usr/bin/env python3
"""Iterate on ShipLoop: run it, review the run, improve the skill, rebuild, rerun.

Each iteration, in a dedicated worktree of this repository:

  1. build   the worktree's skill-craft plugin (scripts/build-packages.py)
  2. run     run.py with that build, from a new empty directory
  3. review  review.py examines conformance and discoveries, building on the last
             three commit messages; a fresh judge admits supported improvements
             and retains design challenges for a separate disposition
  4. record  append the run and review to test/shiploop_e2e/LEARNINGS.md and
             commit it with a detailed message: what was learned, key findings
             and considerations. That history is what the next iteration reads.
             The same commit adds the run's compact Run Review export as
             test/shiploop_e2e/evidence/<run key>.json
  5. improve a headless agent applies those findings to skills/shiploop in the
             worktree, adds a change note and commits
  6. verify  the harness itself checks the commit's scope and runs the quick
             test tier; a red suite stops the loop (nothing is reverted)

The evaluator boundary (SPEC "The promotion contract", build step 3): the improver may change only the
candidate (boundary.candidate_path), the held-out files are withheld from its worktree while it works, its
tool calls are searched for their names, and the digests of what grades the runs (this checkout's harness, its
checks/ and the case entry) must be the same after it as before. Any of those failing stops the loop.

It stops at --iterations, after two consecutive clean reviews of passing runs
(a scoped clean review is v2, independently judged, with no pending material
discovery; this never establishes exhausted learning),
when the improver commits nothing twice in a row, on a run the skill cannot be
blamed for (skill not invoked or wrong plugin), when the improver crosses the
evaluator boundary, or on a red suite. Every
iteration appends to LEARNINGS.md in the output directory.

Nothing is published. The loop ends with a branch whose commits you can review,
merge, release (scripts/release.py) and push (scripts/release-push.py).

  python3 test/shiploop_e2e/iterate.py --case battleship --iterations 3
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import secrets
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import boundary  # noqa: E402
import hosts  # noqa: E402
import judge
import review as reviewer  # noqa: E402
import run as runner  # noqa: E402


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True).stdout.strip()


def new_worktree(name: str) -> tuple[Path, str]:
    branch = f"auto/{name}"
    path = ROOT / ".claude" / "worktrees" / name
    git(ROOT, "worktree", "add", "-q", str(path), "-b", branch, "HEAD")
    return path, branch


def improver_prompt(worktree: Path, findings: list[dict], base: str, prior_learnings: str = "") -> str:
    prior = (f"""
Learnings from the last three commits in this worktree (build on them; do not undo an
earlier improvement unless the findings below show it failed):

{prior_learnings.strip()}
""" if prior_learnings.strip() else "")
    return f"""You are improving the ShipLoop skill in the git worktree {worktree} (your working directory).

{reviewer.PREMISE}
{prior}
An end-to-end run was reviewed. Apply these material findings, each of which keeps the premise:

```json
{json.dumps(findings, indent=2)}
```

Rules:
- Follow the specification's Change admission before editing: for each finding, first write an
  adversarial evaluation (how the change could weaken any clause, break another style or host,
  fail silently, add glue or refusals, grow packets or context, leak secrets or touch user work,
  break saved runs or pinned tests, cost more than it saves, or game a metric), give every
  consequence a disposition (mitigated and tested / accepted with the clause that asks for it /
  rejected), then state the anchor, the non-regression statement and the evidence. Apply only
  findings whose consequences are all addressed; put that record in the commit message.
- Change only skills/shiploop/ and ShipLoop's own tests (test/shiploop-*.test.py, the test/shiploop_*.py
  helpers, test/fixtures/shiploop-*, test/experiments/shiploop_*), and add one note
  changes/shiploop/<short-slug>.md (front matter `bump: patch` or `bump: minor`, then one or
  more lines describing the change for people who install the skill). Never edit plugins/,
  catalogs, CHANGELOG.md or any `version:` field. The E2E harness that grades the runs
  (test/shiploop_e2e/, test/shiploop-e2e*), the test runner and the suite catalog are not yours to
  change: a change there stops the loop. The held-out acceptance checks are withheld from this
  worktree; a command that names one stops the loop too.
- Keep script-owned navigation: do not move successor choice, graph walking or prompt
  selection into model instructions. Skip a finding you cannot apply without breaking that.
- Match the surrounding code and prose style; keep changes small and targeted.
- Run `bash test/run-all.sh --group quick --changed-from {base}` and fix failures you caused.
- Commit with `git -C {worktree} add <explicit paths>` and a message whose final paragraph
  is `Co-Authored-By: ShipLoop E2E improver <shiploop-e2e@example.invalid>`.
- Do not push, release or touch other branches.

End with exactly one ```json fenced block:
{{"applied": [{{"title": "...", "anchor": ["S-n"], "adversarial": [{{"consequence": "...", "disposition": "mitigated|accepted|rejected", "how": "..."}}]}}], "skipped": [{{"title": "...", "reason": "..."}}], "tests": "quick tier summary line"}}
"""


def improve(worktree: Path, findings: list[dict], stage: Path, args) -> dict:
    stage.mkdir()
    cases = json.loads(runner.CASES.read_text())
    graded_before = boundary.fingerprint(HERE, cases.get(args.case))
    profile = role_profile(args, "improver")
    agent = hosts.host(profile["host"])
    git_config = Path.home() / ".gitconfig"
    env = agent.env(stage / "home", git_config if git_config.is_file() else None)
    base = git(worktree, "rev-parse", "HEAD")
    argv = agent.argv(prompt=improver_prompt(worktree, findings, base, reviewer.last_commit_messages(worktree)),
                      prompt_file=stage / "prompt.txt", cwd=worktree, model=profile["model"],
                      effort=profile["effort"], permission_mode=args.permission_mode,
                      max_turns=args.improve_max_turns, max_budget_usd=args.max_budget_usd)
    held_out = boundary.held_out_files(cases)
    with boundary.withheld(worktree, held_out) as withheld:
        process = hosts.run_agent(argv, worktree, env, stage / "events.jsonl", stage / "stderr.txt",
                                  args.improve_timeout, translate=agent.translator())
    report = hosts.last_json_object(hosts.final_text(stage / "events.jsonl")) or {}
    graded_after = boundary.fingerprint(HERE, json.loads(runner.CASES.read_text()).get(args.case))
    commits = git(worktree, "rev-list", f"{base}..HEAD").split()
    changed = git(worktree, "diff", "--name-only", base, "HEAD").split() if commits else []
    dirty = git(worktree, "status", "--porcelain")
    return {"process": process, "report": report, "base": base, "commits": commits, "changed": changed,
            "out_of_scope": [path for path in changed if not boundary.candidate_path(path)],
            "uncommitted": dirty.splitlines(), "withheld": withheld,
            "held_out_named": boundary.named(stage / "events.jsonl", held_out),
            "grading": {"before": graded_before, "after": graded_after,
                        "changed": boundary.changed(graded_before, graded_after)}}


def boundary_crossing(change: dict) -> str | None:
    """Why the improver's work crossed the evaluator boundary, or None: what grades the runs changed, or its tool calls
    name a held-out file, or its events could not be read (an exposure that cannot be ruled out)."""
    if change["grading"]["changed"]:
        return ("the improver changed what grades the runs (" + ", ".join(change["grading"]["changed"]) + " digest; "
                "SPEC: a harness or oracle change is an experiment of its own)")
    if change["held_out_named"] is None:
        return "the improver's events could not be read, so an exposure of the held-out files cannot be ruled out"
    if change["held_out_named"]:
        return f"the improver's tool calls name a held-out file {change['held_out_named']} time(s): the holdout may be exposed"
    return None


def role_profile(args, role: str) -> dict:
    """Subject flags never silently select a reviewer, judge or improver."""
    return hosts.resolve_role(role, {key: getattr(args, f"{role}_{key}", None)
                                     for key in ("host", "model", "effort")})


def _finding_lines(finding: dict) -> list[str]:
    lines = [(f"- {finding.get('title')} ({finding.get('materiality', finding.get('severity'))}, "
              f"{'within current authority' if finding.get('implementation_eligible', finding.get('preserves_premise')) else 'requires separate disposition'})")]
    for label, key in (("Evidence", "evidence"), ("Proposal", "proposal"), ("Premise", "premise_note")):
        if finding.get(key):
            lines.append(f"  {label}: {finding[key]}")
    if finding.get("files"):
        lines.append(f"  Files: {', '.join(finding['files'])}")
    if finding.get("mission_anchor"):
        lines.append("  Mission relationship: " + json.dumps(finding["mission_anchor"], sort_keys=True))
        lines.append(f"  Confidence: {finding.get('confidence')}; next experiment: {finding.get('next_experiment')}")
    return lines


def learnings_message(index: int, args, sha: str, result: dict, verdict: dict, prior: list[str]) -> str:
    """A detailed commit message for one iteration: outcome, what was learned, what to try next."""
    process, shiploop, cli = result["process"], result["shiploop"], result["cli"]
    checks = result["checks"]
    driver = result["host"] + (f" {result['effort']}" if result.get("effort") else "")
    lines = [f"test(shiploop): record E2E iteration {index} learnings ({args.case}, {driver})", "",
             f"Iteration {index} ran ShipLoop built from {sha[:8]} with {result['host']} "
             f"{result['model']} (effort {result.get('effort')}) from an empty directory on the "
             f"{args.case} case.", "",
             "Outcome", "",
             f"- run: {'PASS' if result['pass'] else 'FAIL'}; host {process['status']} "
             f"(rc {process['returncode']}) after {process['elapsed_seconds']} s, "
             f"{cli.get('num_turns')} turns, cost {runner.metrics.money(cli.get('cost_usd'))}",
             f"- ShipLoop: status {shiploop.get('status') or shiploop.get('reason')}, "
             f"stage {shiploop.get('stage')}, report {shiploop.get('report_html')}",
             f"- checks in work/: {sum(c['pass'] for c in checks)}/{len(checks)} pass"]
    if "outcome_basis" in result:  # how the run ended (a record: run.outcome_class), where the result has one
        lines.append(f"- ended as: {result.get('outcome_class') or 'unknown'} ({result['outcome_basis']})")
    at_stop = result.get("product_at_stop")
    if isinstance(at_stop, dict) and at_stop.get("ran"):
        engine = at_stop.get("engine") or {}
        lines.append(f"- product at stop (information only, engine {engine.get('status')} at {engine.get('stage')}): "
                     f"{at_stop['passed']}/{at_stop['total']} checks pass in ShipLoop's unreturned worktree"
                     + (f", {at_stop['timed_out']} timed out" if at_stop.get("timed_out") else ""))
    for check in checks:
        if not check["pass"]:
            lines.append(f"  failed: {check['command'][:120]}")
    if cli.get("truncated_outputs"):
        lines.append(f"- host truncated {len(cli['truncated_outputs'])} tool outputs before the model saw them")
    lines += ["", "Reviewer outcome", "", str(verdict.get("outcome", ""))]
    checked = verdict.get("validity") or {}
    if checked.get("status") != "valid":
        lines += ["", f"Review {checked.get('status') or 'unchecked'}: {checked.get('reason') or 'no validity recorded'}; "
                  "not counted as clean and nothing applied."]
    for category in reviewer.CATEGORIES:
        found = [f for f in verdict.get(category) or [] if isinstance(f, dict)]
        if found:
            lines += ["", category.replace("_", " ").capitalize(), ""]
            for finding in found:
                lines += _finding_lines(finding)
    discoveries = [f for f in verdict.get("discoveries", []) if isinstance(f, dict)]
    if discoveries:
        lines += ["", "Discoveries and independent judgment", ""]
        for finding in discoveries:
            lines += _finding_lines(finding)
        judged = verdict.get("judge") or {}
        lines.append("Judge: " + json.dumps({key: judged.get(key) for key in
                                          ("review_sha256", "validity", "assessments")}, sort_keys=True))
    harness = verdict.get("harness") if isinstance(verdict.get("harness"), dict) else {}
    lines += ["", "Harness questions", ""]
    for key in reviewer.HARNESS_QUESTIONS:
        row = harness.get(key) if isinstance(harness.get(key), dict) else {}
        lines.append(f"- {key.replace('_', ' ')}: {row.get('answer', 'not answered')}")
        lines += [f"  proposal: {proposal}" for proposal in row.get("proposals") or []]
    actionable = verdict.get("actionable") or []
    lines += ["", "Next", ""]
    lines += ([f"- apply: {f.get('title')}" for f in actionable] if actionable
              else ["- no independently admitted ShipLoop finding to apply; retained challenges need disposition"])
    if prior:
        lines += ["", "Built on the learnings of " + ", ".join(prior) + "."]
    lines += ["", "Co-Authored-By: ShipLoop E2E harness <shiploop-e2e@example.invalid>"]
    return "\n".join(lines) + "\n"


REVIEW_ADVISE = "/skill-craft:shiploop-run-review advise"


def review_line(index: int, run_dir: Path) -> str:
    """The step after the learnings commit: Claude writes the advice for this run (the skill's advise mode)."""
    return f"== iteration {index}: update the Run Review page: {REVIEW_ADVISE} {run_dir}"


def review_evidence(worktree: Path, stage: Path) -> str | None:
    """Copy the run's compact Run Review export to test/shiploop_e2e/evidence/<run key>.json.

    Returns the repository path, or None when the run left no readable export (run.py reports why).
    """
    try:
        bundle = stage / "run" / "review-export" / "review-export.json"
        text = bundle.read_text()
        keys = list(json.loads(text)["docs"]["runs"])
        if len(keys) != 1 or not keys[0] or "/" in keys[0] or keys[0].startswith("."):
            return None
    except (OSError, ValueError, KeyError, TypeError):
        return None
    relative = f"test/shiploop_e2e/evidence/{keys[0]}.json"
    (worktree / relative).parent.mkdir(parents=True, exist_ok=True)
    (worktree / relative).write_text(text)
    return relative


def record_learnings(worktree: Path, message: str, stage: Path) -> str:
    """Append the iteration's message to LEARNINGS.md in the worktree and commit it, with the run's
    compact Run Review export when the run left one."""
    path = worktree / "test" / "shiploop_e2e" / "LEARNINGS.md"
    subject, _, body = message.partition("\n\n")
    body = body.split("\nCo-Authored-By:", 1)[0].rstrip()
    heading = subject.removeprefix("test(shiploop): record ")
    with path.open("a") as out:
        out.write(f"\n## {heading}\n\n{body}\n")
    (stage / "learnings-commit.txt").write_text(message)
    evidence = review_evidence(worktree, stage)
    git(worktree, "add", "test/shiploop_e2e/LEARNINGS.md", *([evidence] if evidence else []))
    git(worktree, "commit", "-q", "-F", str(stage / "learnings-commit.txt"))
    return git(worktree, "rev-parse", "--short", "HEAD")


def quick_suite(worktree: Path, base: str, log: Path) -> bool:
    with log.open("w") as out:
        done = subprocess.run(["bash", "test/run-all.sh", "--group", "quick", "--changed-from", base],
                              cwd=worktree, stdout=out, stderr=subprocess.STDOUT)
    return done.returncode == 0


def journal(path: Path, lines: list[str]) -> None:
    with path.open("a") as out:
        out.write("\n".join(lines) + "\n\n")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--case", default="battleship")
    p.add_argument("--iterations", type=int, default=3, help="how many iterations to run")
    p.add_argument("--host", choices=sorted(hosts.HOSTS), default=hosts.RUN_DEFAULT_HOST,
                   help="test subject host; reviewer, judge and improver have separate role profiles")
    p.add_argument("--model")
    p.add_argument("--effort")
    for role in ("reviewer", "judge", "improver"):
        p.add_argument(f"--{role}-host", choices=sorted(hosts.HOSTS))
        p.add_argument(f"--{role}-model")
        p.add_argument(f"--{role}-effort")
    p.add_argument("--permission-mode", default="auto")
    p.add_argument("--run-max-turns", type=int, default=None)  # no turn limit unless one is asked for
    p.add_argument("--improve-max-turns", type=int, default=None)  # no turn limit unless asked
    p.add_argument("--max-budget-usd", type=float, default=None, help="per Claude process, default none; Grok has no spend cap")
    p.add_argument("--run-timeout", type=int, default=None)  # no time limit unless asked
    p.add_argument("--improve-timeout", type=int, default=2700)
    p.add_argument("--output", type=Path)
    args = p.parse_args(argv)
    if args.iterations < 1:
        raise SystemExit("--iterations must be at least 1")

    name = f"auto-shiploop-e2e-{secrets.token_hex(3)}"
    out = (args.output or Path(tempfile.gettempdir()) / "shiploop-e2e" / name).resolve()
    if out == ROOT or ROOT in out.parents:
        raise SystemExit(f"output must be outside the checkout: {out}")
    out.mkdir(parents=True, exist_ok=False)
    worktree, branch = new_worktree(name)
    start_sha = git(worktree, "rev-parse", "HEAD")
    learnings = out / "LEARNINGS.md"
    journal(learnings, [f"# ShipLoop E2E iterations: {args.case}", "",
                        f"- worktree: {worktree}", f"- branch: {branch} from {start_sha}",
                        f"- host: {args.host} model={args.model or hosts.run_default_model(args.host)} "
                        f"effort={args.effort or hosts.HOST_DEFAULTS[args.host]['effort']}"])
    print(f"iterate: output={out} worktree={worktree} branch={branch}", flush=True)
    (out / "roles.json").write_text(json.dumps({"subject": hosts.resolve_role("subject", {
        "host": args.host, "model": args.model, "effort": args.effort}),
        **{role: role_profile(args, role) for role in ("reviewer", "judge", "improver")}}, indent=2) + "\n")
    frozen_evaluator = boundary.qualification_snapshot(HERE, [args.case])
    (out / "qualification-inputs.json").write_text(json.dumps(frozen_evaluator, indent=2) + "\n")

    clean_streak = idle_streak = 0
    stop = f"reached --iterations {args.iterations}"
    tested_source = None
    for index in range(1, args.iterations + 1):
        if boundary.qualification_snapshot(HERE, [args.case]) != frozen_evaluator:
            stop = "frozen evaluator inputs changed; start a new exploration round"
            journal(learnings, ["- stopped: " + stop])
            break
        stage = out / f"iter-{index}"
        stage.mkdir()
        sha = git(worktree, "rev-parse", "HEAD")
        tested_source = runner.tree_digest(worktree / "skills" / "shiploop")
        prior_learnings = reviewer.last_commit_messages(worktree)
        prior = git(worktree, "log", "-3", "--format=%h").split()
        subprocess.run([sys.executable, "-B", str(worktree / "scripts/build-packages.py"), str(stage / "build")],
                       check=True, stdout=subprocess.DEVNULL)
        run_args = ["--case", args.case, "--host", args.host, "--output", str(stage / "run"),
                    "--plugin-dir", str(stage / "build" / "plugins" / "skill-craft"),
                    "--permission-mode", args.permission_mode,
                    *(["--max-turns", str(args.run_max_turns)] if args.run_max_turns else []),
                    *(["--max-budget-usd", str(args.max_budget_usd)] if args.max_budget_usd else []),
                    *(["--timeout", str(args.run_timeout)] if args.run_timeout else [])]
        run_args += (["--model", args.model] if args.model else []) + (["--effort", args.effort] if args.effort else [])
        print(f"\n== iteration {index}: run ({sha[:8]})", flush=True)
        runner.main(run_args)
        result = json.loads((stage / "run" / "result.json").read_text())
        graded = result.get("boundary") or {}
        entry = [f"## Iteration {index} ({sha[:8]})", "",
                 f"- run: {'PASS' if result['pass'] else 'FAIL'} ({result['process']['status']}, "
                 f"{result['process']['elapsed_seconds']}s, cost {runner.metrics.money(result['cli'].get('cost_usd'))}, "
                 f"shiploop {result['shiploop'].get('status') or result['shiploop'].get('reason')}, "
                 f"checks {sum(c['pass'] for c in result['checks'])}/{len(result['checks'])})",
                 f"- boundary: evaluator {graded.get('evaluator')}, oracle {graded.get('oracle')}, case {graded.get('case')}, "
                 f"candidate {(result.get('versions') or {}).get('plugin_sha256')}"]
        if not (result["invoked"]["pass"] and result["plugin"]["pass"]):
            journal(learnings, entry + ["- stopped: the skill was not invoked from the build under test"])
            stop = "run did not reach the skill under test (see result.json invoked/plugin)"
            break
        if boundary.qualification_snapshot(HERE, [args.case]) != frozen_evaluator:
            stop = "frozen evaluator inputs changed during the run; its assessment is unqualified"
            journal(learnings, entry + ["- stopped: " + stop])
            break

        print(f"== iteration {index}: review", flush=True)
        verdict = reviewer.review(stage / "run", **role_profile(args, "reviewer"),
                                  skill_root=worktree / "skills" / "shiploop", prior_learnings=prior_learnings)
        if (verdict.get("validity") or {}).get("discovery_qualified"):
            judged = judge.judge(stage / "run", verdict, **role_profile(args, "judge"))
            routes = judge.admitted(verdict, judged)
            verdict["judge"] = judged
            verdict["actionable"] = routes["implementation"]
            (stage / "dispositions.json").write_text(json.dumps(routes, indent=2) + "\n")
        else:
            # Historical reviews are readable diagnostics, not fresh discovery/judge evidence.
            verdict["actionable"] = []
        if boundary.qualification_snapshot(HERE, [args.case]) != frozen_evaluator:
            stop = "frozen evaluator inputs changed during review; do not apply its findings"
            journal(learnings, entry + ["- stopped: " + stop])
            break
        recorded = record_learnings(worktree, learnings_message(index, args, sha, result, verdict, prior), stage)
        print(review_line(index, stage / "run"), flush=True)
        findings = verdict["actionable"]
        admitted_ids = {finding.get("id") for finding in findings}
        rejected = [f.get("title") for f in verdict.get("discoveries", []) if isinstance(f, dict)
                    and f.get("materiality") == "material" and f.get("id") not in admitted_ids]
        rejected += [f.get("title") for c in reviewer.CATEGORIES for f in verdict.get(c) or []
                     if isinstance(f, dict) and f.get("preserves_premise") is False]
        entry += [f"- outcome: {verdict.get('outcome')}",
                  f"- actionable: {len(findings)}; design challenges retained: {len(rejected)}"]
        entry += [f"  - [{f.get('category', 'discovery')}] {f.get('title')}" for f in findings]
        entry += [f"  - requires disposition: {title}" for title in rejected]
        entry.append(f"- review: {stage / 'run' / 'review.md'}; learnings commit {recorded} "
                     f"(built on {', '.join(prior)})")
        checked = verdict["validity"]
        if checked["status"] != "valid":
            # An unusable review (failed, timed out, no JSON, no review structure) says nothing about the run: it never
            # counts as clean, breaks a clean streak, and hands nothing to the improver.
            clean_streak = 0
            journal(learnings, entry + [f"- review {checked['status']}: {checked['reason']}; not counted as clean "
                                        "(streak 0)"])
            continue
        if not findings:
            clean_streak = clean_streak + 1 if result["pass"] and reviewer.counts_as_clean(verdict) else 0
            journal(learnings, entry + [f"- scoped review complete without admitted implementation (streak {clean_streak})"])
            if clean_streak >= 2:
                stop = "two scoped passing assessments; no claim of exhausted learning"
                break
            continue
        clean_streak = 0

        print(f"== iteration {index}: improve ({len(findings)} findings)", flush=True)
        change = improve(worktree, findings, stage / "improve", args)
        entry += [f"- improve: {change['process']['status']}, {len(change['commits'])} commit(s), "
                  f"files: {', '.join(change['changed']) or 'none'}",
                  f"  - applied: {change['report'].get('applied')}",
                  f"  - skipped: {change['report'].get('skipped')}",
                  f"- withheld: {', '.join(change['withheld']) or 'none'}; improver tool calls naming one: "
                  f"{change['held_out_named']}"]
        crossed = boundary_crossing(change)
        if crossed:
            journal(learnings, entry + [f"- stopped: {crossed}"])
            stop = crossed
            break
        if change["out_of_scope"] or change["uncommitted"]:
            journal(learnings, entry + [f"- stopped: out-of-scope {change['out_of_scope']}, "
                                        f"uncommitted {change['uncommitted']}"])
            stop = "improver changed files outside the allowed scope or left work uncommitted"
            break
        if not change["commits"]:
            idle_streak += 1
            journal(learnings, entry + [f"- no commit (streak {idle_streak})"])
            if idle_streak >= 2:
                stop = "improver committed nothing twice in a row"
                break
            continue
        idle_streak = 0
        print(f"== iteration {index}: verify (quick tier)", flush=True)
        green = quick_suite(worktree, change["base"], stage / "quick-tier.log")
        entry.append(f"- quick tier: {'green' if green else 'RED'} ({stage / 'quick-tier.log'})")
        journal(learnings, entry)
        if not green:
            stop = "quick test tier is red after the improvement (not reverted)"
            break

    commits = git(worktree, "log", "--oneline", f"{start_sha}..HEAD")
    journal(learnings, ["## Result", "", f"- stopped: {stop}", f"- branch {branch}:",
                        *(f"  - {line}" for line in commits.splitlines() or ["(no commits)"]),
                        "- next: review the branch, merge it, then scripts/release.py and "
                        "scripts/release-push.py to publish; nothing was published"])
    print(f"\niterate: {stop}\n  journal: {learnings}\n  branch:  {branch} ({len(commits.splitlines())} commits)")
    final_sha = git(worktree, "rev-parse", "HEAD")
    final_source = runner.tree_digest(worktree / "skills" / "shiploop")
    evaluator_unchanged = boundary.qualification_snapshot(HERE, [args.case]) == frozen_evaluator
    # A late improver commit is explicitly unevaluated; the comparative controller must evaluate this artifact.
    (out / "iteration-result.json").write_text(json.dumps({"contract": "shiploop-iteration/2", "branch": branch,
        "worktree": str(worktree), "final_commit": final_sha, "stop_reason": stop,
        "tested_source_sha256": tested_source, "final_source_sha256": final_source,
        "qualification": "unevaluated" if (not evaluator_unchanged or final_source is None
                                           or final_source != tested_source) else "comparison_required",
        "evaluator_unchanged": evaluator_unchanged,
        "publication": "not_performed", "learning_exhausted": False}, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
