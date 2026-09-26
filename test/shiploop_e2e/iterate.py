#!/usr/bin/env python3
"""Iterate on ShipLoop: run it, review the run, improve the skill, rebuild, rerun.

Each iteration, in a dedicated worktree of this repository:

  1. build   the worktree's skill-craft plugin (scripts/build-packages.py)
  2. run     run.py with that build, from a new empty directory
  3. review  review.py answers the three questions; only material findings
             that keep the core premise (script-owned SDLC navigation) count
  4. improve a headless agent applies those findings to skills/shiploop in the
             worktree, adds a change note and commits
  5. verify  the harness itself checks the commit's scope and runs the quick
             test tier; a red suite stops the loop (nothing is reverted)

It stops at --iterations, after two consecutive clean reviews of passing runs,
when the improver commits nothing twice in a row, on a run the skill cannot be
blamed for (skill not invoked or wrong plugin), or on a red suite. Every
iteration appends to LEARNINGS.md in the output directory.

Nothing is published. The loop ends with a branch whose commits you can review,
merge, release (scripts/release.py) and push (scripts/release-push.py).

  python3 test/shiploop_e2e/iterate.py --case battleship --iterations 3
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import hosts  # noqa: E402
import review as reviewer  # noqa: E402
import run as runner  # noqa: E402

MAX_ITERATIONS = 10
# An improvement may touch only the skill, its notes and tests.
ALLOWED_PREFIXES = ("skills/shiploop/", "changes/shiploop/", "test/")


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True).stdout.strip()


def new_worktree(name: str) -> tuple[Path, str]:
    branch = f"auto/{name}"
    path = ROOT / ".claude" / "worktrees" / name
    git(ROOT, "worktree", "add", "-q", str(path), "-b", branch, "HEAD")
    return path, branch


def improver_prompt(worktree: Path, findings: list[dict], base: str) -> str:
    return f"""You are improving the ShipLoop skill in the git worktree {worktree} (your working directory).

{reviewer.PREMISE}

An end-to-end run was reviewed. Apply these material findings, each of which keeps the premise:

```json
{json.dumps(findings, indent=2)}
```

Rules:
- Change only skills/shiploop/, its tests under test/, and add one note
  changes/shiploop/<short-slug>.md (front matter `bump: patch` or `bump: minor`, then one or
  more lines describing the change for people who install the skill). Never edit plugins/,
  catalogs, CHANGELOG.md or any `version:` field.
- Keep script-owned navigation: do not move successor choice, graph walking or prompt
  selection into model instructions. Skip a finding you cannot apply without breaking that.
- Match the surrounding code and prose style; keep changes small and targeted.
- Run `bash test/run-all.sh --group quick --changed-from {base}` and fix failures you caused.
- Commit with `git add <explicit paths>` (never `git add -A`) and a message whose final paragraph
  is `Co-Authored-By: ShipLoop E2E improver <shiploop-e2e@example.invalid>`.
- Do not push, release or touch other branches.

End with exactly one ```json fenced block:
{{"applied": ["finding titles"], "skipped": [{{"title": "...", "reason": "..."}}], "tests": "quick tier summary line"}}
"""


def improve(worktree: Path, findings: list[dict], stage: Path, args) -> dict:
    stage.mkdir()
    defaults = hosts.HOST_DEFAULTS[args.host]
    git_config = Path.home() / ".gitconfig"
    env = (hosts.grok_env(stage / "home", git_config if git_config.is_file() else None)
           if args.host == "grok" else dict(os.environ))
    base = git(worktree, "rev-parse", "HEAD")
    argv = hosts.argv_for(args.host, prompt=improver_prompt(worktree, findings, base),
                          prompt_file=stage / "prompt.txt", cwd=worktree, model=args.model or defaults["model"],
                          effort=args.effort or defaults["effort"], permission_mode=args.permission_mode,
                          max_turns=args.improve_max_turns, max_budget_usd=args.max_budget_usd)
    process = hosts.run_agent(argv, worktree, env, stage / "events.jsonl", stage / "stderr.txt",
                              args.improve_timeout)
    report = hosts.last_json_object(hosts.final_text(stage / "events.jsonl")) or {}
    commits = git(worktree, "rev-list", f"{base}..HEAD").split()
    changed = git(worktree, "diff", "--name-only", base, "HEAD").split() if commits else []
    dirty = git(worktree, "status", "--porcelain")
    return {"process": process, "report": report, "base": base, "commits": commits, "changed": changed,
            "out_of_scope": [path for path in changed if not path.startswith(ALLOWED_PREFIXES)],
            "uncommitted": dirty.splitlines()}


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
    p.add_argument("--iterations", type=int, default=3, help=f"hard cap, at most {MAX_ITERATIONS}")
    p.add_argument("--host", choices=sorted(hosts.HOST_DEFAULTS), default="grok",
                   help="host for the run, the review and the improvement")
    p.add_argument("--model")
    p.add_argument("--effort")
    p.add_argument("--permission-mode", default="auto")
    p.add_argument("--run-max-turns", type=int, default=150)
    p.add_argument("--improve-max-turns", type=int, default=120)
    p.add_argument("--max-budget-usd", type=float, default=10.0, help="per Claude process; Grok has no spend cap")
    p.add_argument("--run-timeout", type=int, default=2700)
    p.add_argument("--improve-timeout", type=int, default=2700)
    p.add_argument("--output", type=Path)
    args = p.parse_args(argv)
    if not 1 <= args.iterations <= MAX_ITERATIONS:
        raise SystemExit(f"--iterations must be 1..{MAX_ITERATIONS}")

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
                        f"- host: {args.host} model={args.model or hosts.HOST_DEFAULTS[args.host]['model']} "
                        f"effort={args.effort or hosts.HOST_DEFAULTS[args.host]['effort']}"])
    print(f"iterate: output={out} worktree={worktree} branch={branch}", flush=True)

    clean_streak = idle_streak = 0
    stop = f"reached --iterations {args.iterations}"
    for index in range(1, args.iterations + 1):
        stage = out / f"iter-{index}"
        stage.mkdir()
        sha = git(worktree, "rev-parse", "HEAD")
        subprocess.run([sys.executable, "-B", str(worktree / "scripts/build-packages.py"), str(stage / "build")],
                       check=True, stdout=subprocess.DEVNULL)
        run_args = ["--case", args.case, "--host", args.host, "--output", str(stage / "run"),
                    "--plugin-dir", str(stage / "build" / "plugins" / "skill-craft"),
                    "--permission-mode", args.permission_mode, "--max-turns", str(args.run_max_turns),
                    "--max-budget-usd", str(args.max_budget_usd), "--timeout", str(args.run_timeout)]
        run_args += (["--model", args.model] if args.model else []) + (["--effort", args.effort] if args.effort else [])
        print(f"\n== iteration {index}: run ({sha[:8]})", flush=True)
        runner.main(run_args)
        result = json.loads((stage / "run" / "result.json").read_text())
        entry = [f"## Iteration {index} ({sha[:8]})", "",
                 f"- run: {'PASS' if result['pass'] else 'FAIL'} ({result['process']['status']}, "
                 f"{result['process']['elapsed_seconds']}s, cost ${result['cli'].get('cost_usd')}, "
                 f"shiploop {result['shiploop'].get('status') or result['shiploop'].get('reason')}, "
                 f"checks {sum(c['pass'] for c in result['checks'])}/{len(result['checks'])})"]
        if not (result["invoked"]["pass"] and result["plugin"]["pass"]):
            journal(learnings, entry + ["- stopped: the skill was not invoked from the build under test"])
            stop = "run did not reach the skill under test (see result.json invoked/plugin)"
            break

        print(f"== iteration {index}: review", flush=True)
        verdict = reviewer.review(stage / "run", host=args.host, model=args.model, effort=args.effort,
                                  skill_root=worktree / "skills" / "shiploop")
        findings = verdict["actionable"]
        rejected = [f.get("title") for c in reviewer.CATEGORIES for f in verdict.get(c) or []
                    if isinstance(f, dict) and f.get("preserves_premise") is False]
        entry += [f"- outcome: {verdict.get('outcome')}",
                  f"- actionable: {len(findings)}; premise-breaking (rejected): {len(rejected)}"]
        entry += [f"  - [{f['category']}] {f.get('title')}" for f in findings]
        entry += [f"  - rejected: {title}" for title in rejected]
        entry.append(f"- review: {stage / 'run' / 'review.md'}")
        if not findings:
            clean_streak = clean_streak + 1 if result["pass"] else 0
            journal(learnings, entry + [f"- clean review (streak {clean_streak})"])
            if clean_streak >= 2:
                stop = "two consecutive clean reviews of passing runs"
                break
            continue
        clean_streak = 0

        print(f"== iteration {index}: improve ({len(findings)} findings)", flush=True)
        change = improve(worktree, findings, stage / "improve", args)
        entry += [f"- improve: {change['process']['status']}, {len(change['commits'])} commit(s), "
                  f"files: {', '.join(change['changed']) or 'none'}",
                  f"  - applied: {change['report'].get('applied')}",
                  f"  - skipped: {change['report'].get('skipped')}"]
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
