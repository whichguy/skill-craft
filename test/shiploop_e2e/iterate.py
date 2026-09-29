#!/usr/bin/env python3
"""Iterate on ShipLoop: run it, review the run, improve the skill, rebuild, rerun.

Each iteration, in a dedicated worktree of this repository:

  1. build   the worktree's skill-craft plugin (scripts/build-packages.py)
  2. run     run.py with that build, from a new empty directory
  3. review  review.py answers the three questions, building on the last three
             commit messages; only material findings that keep the core premise
             (script-owned SDLC navigation) count
  4. record  append the run and review to test/shiploop_e2e/LEARNINGS.md and
             commit it with a detailed message: what was learned, key findings
             and considerations. That history is what the next iteration reads
  5. improve a headless agent applies those findings to skills/shiploop in the
             worktree, adds a change note and commits
  6. verify  the harness itself checks the commit's scope and runs the quick
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
from datetime import datetime, timezone
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
import evidence  # noqa: E402

MAX_ITERATIONS = 10
# Tests are opt-in by exact path; the harness, evaluator, cases and baselines
# under test/shiploop_e2e are never improver-owned.
ALLOWED_PREFIXES = ("skills/shiploop/", "changes/shiploop/")


def validate_allow_tests(paths: list[str] | None) -> list[str]:
    allowed = []
    for raw in paths or []:
        path = Path(raw)
        normalized = path.as_posix()
        if (path.is_absolute() or ".." in path.parts or not normalized.startswith("test/")
                or normalized.startswith(("test/shiploop_e2e/", "test/shiploop-e2e"))):
            raise ValueError(f"--allow-test must name one regression test outside the ShipLoop E2E evaluator: {raw}")
        if normalized not in allowed:
            allowed.append(normalized)
    return allowed


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True).stdout.strip()


def new_worktree(name: str) -> tuple[Path, str]:
    branch = f"auto/{name}"
    path = ROOT / ".claude" / "worktrees" / name
    git(ROOT, "worktree", "add", "-q", str(path), "-b", branch, "HEAD")
    return path, branch


def improver_prompt(worktree: Path, findings: list[dict], base: str, prior_learnings: str = "",
                    allow_tests: list[str] | None = None) -> str:
    prior = (f"""
Learnings from the last three commits in this worktree (build on them; do not undo an
earlier improvement unless the findings below show it failed):

{prior_learnings.strip()}
""" if prior_learnings.strip() else "")
    allow_tests = validate_allow_tests(allow_tests)
    test_paths = "\n".join(f"  - {path}" for path in allow_tests) or "  - (none)"
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
- Change only skills/shiploop/, add one note
  changes/shiploop/<short-slug>.md (front matter `bump: patch` or `bump: minor`, then one or
  more lines describing the change for people who install the skill), and these explicitly
  authorized regression-test paths:
{test_paths}
  Never edit any other test, the E2E harness/evaluator, case catalog, baselines, prior evidence,
  plugins/,
  catalogs, CHANGELOG.md or any `version:` field.
- Keep script-owned navigation: do not move successor choice, graph walking or prompt
  selection into model instructions. Skip a finding you cannot apply without breaking that.
- Match the surrounding code and prose style; keep changes small and targeted.
- Run `bash test/run-all.sh --group quick --changed-from {base}` and fix failures you caused.
- Commit with `git add <explicit paths>` (never `git add -A`) and a message whose final paragraph
  is `Co-Authored-By: ShipLoop E2E improver <shiploop-e2e@example.invalid>`.
- Do not push, release or touch other branches.

End with exactly one ```json fenced block:
{{"applied": [{{"title": "...", "anchor": ["S-n"], "adversarial": [{{"consequence": "...", "disposition": "mitigated|accepted|rejected", "how": "..."}}]}}], "skipped": [{{"title": "...", "reason": "..."}}], "tests": "quick tier summary line"}}
"""


def improve(worktree: Path, findings: list[dict], stage: Path, args) -> dict:
    stage.mkdir()
    agent = hosts.host(args.host)
    allow_tests = validate_allow_tests(getattr(args, "allow_test", None))
    git_config = Path.home() / ".gitconfig"
    env = agent.env(stage / "home", git_config if git_config.is_file() else None)
    base = git(worktree, "rev-parse", "HEAD")
    argv = agent.argv(prompt=improver_prompt(worktree, findings, base, reviewer.last_commit_messages(worktree),
                                             allow_tests),
                      prompt_file=stage / "prompt.txt", cwd=worktree, model=args.model or agent.model,
                      effort=args.effort or agent.effort, permission_mode=args.permission_mode,
                      max_turns=args.improve_max_turns, max_budget_usd=args.max_budget_usd)
    process = hosts.run_agent(argv, worktree, env, stage / "events.jsonl", stage / "stderr.txt",
                              args.improve_timeout, translate=agent.translator())
    report = hosts.last_json_object(hosts.final_text(stage / "events.jsonl")) or {}
    report_errors = validate_improve_report(report, process)
    commits = git(worktree, "rev-list", f"{base}..HEAD").split()
    changed = git(worktree, "diff", "--name-only", base, "HEAD").split() if commits else []
    dirty = git(worktree, "status", "--porcelain")
    allowed = set(allow_tests)
    return {"process": process, "report": report, "report_errors": report_errors,
            "base": base, "commits": commits, "changed": changed,
            "out_of_scope": [path for path in changed if not path.startswith(ALLOWED_PREFIXES) and path not in allowed],
            "uncommitted": dirty.splitlines()}


def validate_improve_report(report: dict, process: dict) -> list[str]:
    errors = []
    if process.get("status") != "exited" or process.get("returncode") != 0:
        errors.append("improver process did not exit successfully")
    if process.get("capture_errors") or process.get("stream_errors"):
        errors.append("improver process output capture was incomplete")
    if process.get("cleanup_error"):
        errors.append("improver process cleanup failed")
    if not isinstance(report, dict) or set(report) != {"applied", "skipped", "tests"}:
        return errors + ["improver report has missing or unsupported fields"]
    if not isinstance(report["applied"], list) or not isinstance(report["skipped"], list):
        errors.append("improver applied and skipped fields must be arrays")
    if not isinstance(report["tests"], str) or not report["tests"].strip():
        errors.append("improver report must state its test result")
    for row in report.get("applied", []):
        if (not isinstance(row, dict) or set(row) != {"title", "anchor", "adversarial"}
                or not isinstance(row.get("title"), str) or not row["title"].strip()
                or not isinstance(row.get("anchor"), list) or not row["anchor"]
                or not isinstance(row.get("adversarial"), list) or not row["adversarial"]):
            errors.append("improver applied entry is incomplete")
            continue
        if any(not isinstance(clause, str) or not clause.startswith("S-") for clause in row["anchor"]):
            errors.append("improver anchor must cite one or more SPEC clauses")
        if any(not isinstance(item, dict) or set(item) != {"consequence", "disposition", "how"}
               or not isinstance(item.get("consequence"), str) or not item["consequence"].strip()
               or item.get("disposition") not in {"mitigated", "accepted", "rejected"}
               or not isinstance(item.get("how"), str) or not item["how"].strip()
               for item in row["adversarial"]):
            errors.append("improver adversarial record is incomplete")
    for row in report.get("skipped", []):
        if not isinstance(row, dict) or set(row) != {"title", "reason"} or not row.get("title") or not row.get("reason"):
            errors.append("improver skipped entry is incomplete")
    return errors


def _finding_lines(finding: dict) -> list[str]:
    lines = [f"- {finding.get('title')} ({finding.get('severity')}, "
             f"{'keeps premise' if finding.get('preserves_premise') else 'breaks premise: rejected'})"]
    remedy = finding.get("remedy") if isinstance(finding.get("remedy"), dict) else {}
    values = {"Evidence": finding.get("evidence"), "Proposal": remedy.get("proposal") or finding.get("proposal"),
              "Premise": finding.get("premise_note"), "Disposition": finding.get("disposition"),
              "Cause": (finding.get("cause") or {}).get("explanation") if isinstance(finding.get("cause"), dict) else None}
    for label, value in values.items():
        if value:
            lines.append(f"  {label}: {value}")
    if finding.get("files"):
        lines.append(f"  Files: {', '.join(finding['files'])}")
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
             f"{cli.get('num_turns')} turns, reported cost ${cli.get('cost_usd')}",
             f"- ShipLoop: status {shiploop.get('status') or shiploop.get('reason')}, "
             f"stage {shiploop.get('stage')}, report {shiploop.get('report_html')}",
             f"- checks in work/: {sum(c['pass'] for c in checks)}/{len(checks)} pass"]
    if shiploop.get("worktree_checks") is not None:
        wt = shiploop["worktree_checks"]
        lines.append(f"- unreturned product in ShipLoop's worktree: {sum(c['pass'] for c in wt)}/{len(wt)} pass")
    for check in checks:
        if not check["pass"]:
            lines.append(f"  failed: {check['command'][:120]}")
    if cli.get("truncated_outputs"):
        lines.append(f"- host truncated {len(cli['truncated_outputs'])} tool outputs before the model saw them")
    lines += ["", "Reviewer outcome", "", str(verdict.get("summary") or verdict.get("outcome", ""))]
    if isinstance(verdict.get("findings"), list):
        for finding in verdict["findings"]:
            if isinstance(finding, dict):
                lines += _finding_lines(finding)
        lines += ["", "Harness dispositions", ""]
        for row in verdict.get("harness_dispositions") or []:
            lines.append(f"- {row.get('finding_id')}: {row.get('disposition')} — {row.get('reason')}")
        lines.append(f"- calibration: {(verdict.get('judge_calibration') or {}).get('status', 'not_run')}")
    else:  # compatibility for archived v0.47 diagnostics
        for category in reviewer.CATEGORIES:
            found = [f for f in verdict.get(category) or [] if isinstance(f, dict)]
            if found:
                lines += ["", category.replace("_", " ").capitalize(), ""]
                for finding in found:
                    lines += _finding_lines(finding)
        harness = verdict.get("harness") if isinstance(verdict.get("harness"), dict) else {}
        lines += ["", "Harness questions", ""]
        for key in reviewer.HARNESS_QUESTIONS:
            row = harness.get(key) if isinstance(harness.get(key), dict) else {}
            lines.append(f"- {key.replace('_', ' ')}: {row.get('answer', 'not answered')}")
            lines += [f"  proposal: {proposal}" for proposal in row.get("proposals") or []]
    actionable = verdict.get("actionable") or []
    lines += ["", "Next", ""]
    lines += ([f"- apply: {f.get('title')}" for f in actionable] if actionable
              else ["- no material, premise-preserving finding to apply"])
    if prior:
        lines += ["", "Built on the learnings of " + ", ".join(prior) + "."]
    lines += ["", "Co-Authored-By: ShipLoop E2E harness <shiploop-e2e@example.invalid>"]
    return "\n".join(lines) + "\n"


def record_learnings(worktree: Path, message: str, stage: Path) -> str:
    """Append the iteration's message to LEARNINGS.md in the worktree and commit it."""
    path = worktree / "test" / "shiploop_e2e" / "LEARNINGS.md"
    subject, _, body = message.partition("\n\n")
    body = body.split("\nCo-Authored-By:", 1)[0].rstrip()
    heading = subject.removeprefix("test(shiploop): record ")
    with path.open("a") as out:
        out.write(f"\n## {heading}\n\n{body}\n")
    (stage / "learnings-commit.txt").write_text(message)
    git(worktree, "add", "test/shiploop_e2e/LEARNINGS.md")
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


def current_open_findings(ledger: Path) -> list[dict]:
    latest = {}
    if not ledger.is_file():
        return []
    for line in ledger.read_text(encoding="utf-8").splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        finding = event.get("finding") if isinstance(event, dict) else None
        if not isinstance(finding, dict):
            continue
        relevant = finding.get("severity") == "material" or finding.get("scope") == "harness"
        if relevant and finding.get("id"):
            latest[finding["id"]] = finding
    return sorted((row for row in latest.values() if row.get("disposition") in {"open", "deferred", "disputed"}),
                  key=lambda row: row["id"])


def append_open_findings(ledger: Path, iteration: int, verdict: dict) -> list[dict]:
    findings = verdict.get("findings") or []
    with ledger.open("a", encoding="utf-8") as out:
        for finding in findings:
            if not isinstance(finding, dict):
                continue
            if finding.get("severity") != "material" and finding.get("scope") != "harness":
                continue
            event = {"iteration": iteration, "recorded_at": datetime.now(timezone.utc).isoformat(),
                     "review_attempt": verdict.get("attempt_id"), "finding": finding}
            out.write(json.dumps(event, sort_keys=True) + "\n")
    opened = current_open_findings(ledger)
    evidence.atomic_json(ledger.with_name("open-findings.json"), {"schema": "shiploop-e2e-open-findings/1",
                                                                  "open": opened})
    return opened


def campaign_receipt(path: Path, payload: dict) -> None:
    payload = {"schema": "shiploop-e2e-campaign/1", **payload}
    evidence.atomic_json(path, payload)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--case", default="battleship")
    p.add_argument("--iterations", type=int, default=3, help=f"hard cap, at most {MAX_ITERATIONS}")
    p.add_argument("--host", choices=sorted(hosts.HOSTS), default="grok",
                   help="host for the run, the review and the improvement")
    p.add_argument("--model")
    p.add_argument("--effort")
    p.add_argument("--permission-mode", default="auto")
    p.add_argument("--run-max-turns", type=int, default=10000)
    p.add_argument("--improve-max-turns", type=int, default=120)
    p.add_argument("--max-budget-usd", type=float, default=10.0, help="per Claude process; Grok has no spend cap")
    p.add_argument("--run-timeout", type=int, default=10800)
    p.add_argument("--improve-timeout", type=int, default=2700)
    p.add_argument("--output", type=Path)
    p.add_argument("--calibration", type=Path, help="model-labeled calibration receipt required to accept reviews")
    p.add_argument("--allow-test", action="append", default=[], metavar="PATH",
                   help="one explicit regression test path the improver may change; repeatable")
    args = p.parse_args(argv)
    if not 1 <= args.iterations <= MAX_ITERATIONS:
        raise SystemExit(f"--iterations must be 1..{MAX_ITERATIONS}")
    try:
        args.allow_test = validate_allow_tests(args.allow_test)
    except ValueError as exc:
        p.error(str(exc))

    name = f"auto-shiploop-e2e-{secrets.token_hex(3)}"
    out = (args.output or Path(tempfile.gettempdir()) / "shiploop-e2e" / name).resolve()
    if out == ROOT or ROOT in out.parents:
        raise SystemExit(f"output must be outside the checkout: {out}")
    out.mkdir(parents=True, exist_ok=False)
    learnings = out / "LEARNINGS.md"
    receipt_path = out / "campaign.json"
    worktree = branch = start_sha = None
    stop = f"reached iteration cap {args.iterations}"
    exit_code = 2
    clean_streak = 0
    clean_identity = None
    idle_streak = 0
    iterations = []
    last_qualification = None
    receipt = {"status": "starting", "case": args.case, "output": str(out), "iterations": iterations}
    try:
        if not args.calibration or not args.calibration.is_file():
            stop = "model-labeled calibration receipt is required before an Improve campaign"
            exit_code = 1
            receipt["status"] = "blocked_calibration"
        else:
            expected_calibration = reviewer._calibration_status(
                args.calibration.resolve(),
                {"host": args.host, "model": args.model or hosts.HOST_DEFAULTS[args.host]["model"],
                 "effort": args.effort or hosts.HOST_DEFAULTS[args.host]["effort"]},
                HERE / "SPEC.md")
            if expected_calibration.get("status") != "passed":
                stop = "calibration receipt does not match this reviewer: " + "; ".join(expected_calibration.get("reasons", []))
                exit_code = 1
                receipt["status"] = "blocked_calibration"
            else:
                worktree, branch = new_worktree(name)
                start_sha = git(worktree, "rev-parse", "HEAD")
                journal(learnings, [f"# ShipLoop E2E iterations: {args.case}", "",
                                    f"- worktree: {worktree}", f"- branch: {branch} from {start_sha}",
                                    f"- calibration: {args.calibration.resolve()}",
                                    f"- host: {args.host} model={args.model or hosts.HOST_DEFAULTS[args.host]['model']} "
                                    f"effort={args.effort or hosts.HOST_DEFAULTS[args.host]['effort']}"])
                print(f"iterate: output={out} worktree={worktree} branch={branch}", flush=True)
                ledger = out / "open-findings.jsonl"
                for index in range(1, args.iterations + 1):
                    stage = out / f"iter-{index}"
                    stage.mkdir()
                    sha = git(worktree, "rev-parse", "HEAD")
                    prior_learnings = reviewer.last_commit_messages(worktree)
                    prior = git(worktree, "log", "-3", "--format=%h").split()
                    subprocess.run([sys.executable, "-B", str(worktree / "scripts/build-packages.py"),
                                    str(stage / "build")], check=True, stdout=subprocess.DEVNULL)
                    run_args = ["--case", args.case, "--host", args.host, "--output", str(stage / "run"),
                                "--plugin-dir", str(stage / "build" / "plugins" / "skill-craft"),
                                "--permission-mode", args.permission_mode, "--max-turns", str(args.run_max_turns),
                                "--max-budget-usd", str(args.max_budget_usd), "--timeout", str(args.run_timeout)]
                    run_args += (["--model", args.model] if args.model else []) + (["--effort", args.effort] if args.effort else [])
                    print(f"\n== iteration {index}: run ({sha[:8]})", flush=True)
                    runner_code = runner.main(run_args)
                    run_path = stage / "run"
                    result_path = run_path / "result.json"
                    try:
                        result = evidence.read_json(result_path)
                    except (OSError, ValueError, TypeError) as exc:
                        iterations.append({"number": index, "status": "missing_result", "runner_code": runner_code,
                                           "error": f"{type(exc).__name__}: {exc}", "run": str(run_path)})
                        stop = "runner failed or result.json was missing/malformed"
                        exit_code = 1
                        break
                    entry = [f"## Iteration {index} ({sha[:8]})", "",
                             f"- run: {'PASS' if result.get('pass') else 'FAIL'} ({(result.get('process') or {}).get('status')}, "
                             f"shiploop {(result.get('shiploop') or {}).get('status')}, "
                             f"checks {sum(bool(c.get('pass')) for c in result.get('checks') or [])}/"
                             f"{len(result.get('checks') or [])})"]
                    if not ((result.get("invoked") or {}).get("pass") and (result.get("plugin") or {}).get("pass")):
                        iterations.append({"number": index, "status": "not_invoked", "run": str(run_path),
                                           "identity": result.get("identity")})
                        journal(learnings, entry + ["- stopped: skill was not invoked from the build under test"])
                        stop = "run did not reach the skill under test"
                        exit_code = 1
                        break

                    print(f"== iteration {index}: review", flush=True)
                    prior_open = current_open_findings(ledger)
                    verdict = reviewer.review(run_path, host=args.host, model=args.model, effort=args.effort,
                                              skill_root=worktree / "skills" / "shiploop",
                                              prior_learnings=prior_learnings, prior_findings=prior_open,
                                              calibration_path=args.calibration)
                    last_qualification = verdict.get("qualification")
                    iterations.append({"number": index, "status": "reviewed", "run": str(run_path),
                                       "review": str(run_path / "review.json"),
                                       "identity": result.get("identity"), "qualification": last_qualification})
                    if not (verdict.get("validity") or {}).get("pass"):
                        journal(learnings, entry + ["- stopped: reviewer process/schema/identity/evidence invalid",
                                                    *[f"  - {reason}" for reason in (verdict.get("validity") or {}).get("reasons", [])]])
                        stop = "review validity failed; no learnings were accepted"
                        exit_code = 1
                        break
                    if (verdict.get("judge_calibration") or {}).get("status") != "passed":
                        journal(learnings, entry + ["- stopped: model-labeled calibration is missing or mismatched"])
                        stop = "review is provisional until matching model-labeled controls pass"
                        exit_code = 1
                        break

                    opened = append_open_findings(ledger, index, verdict)
                    findings = verdict.get("actionable") or []
                    recorded = record_learnings(worktree, learnings_message(index, args, sha, result, verdict, prior), stage)
                    rejected = [f.get("title") for f in verdict.get("findings") or [] if isinstance(f, dict)
                                and f.get("preserves_premise") is False]
                    entry += [f"- outcome: {verdict.get('summary')}",
                              f"- qualification: {(verdict.get('qualification') or {}).get('status')}; "
                              f"open relevant findings: {len(opened)}",
                              f"- actionable: {len(findings)}; premise-breaking remedies rejected: {len(rejected)}"]
                    entry += [f"  - {f.get('title')}" for f in findings]
                    entry += [f"  - rejected remedy: {title}" for title in rejected]
                    entry.append(f"- review: {run_path / 'review.md'}; learnings commit {recorded}")

                    if reviewer.is_clean(verdict) and result.get("pass") is True:
                        identity = result.get("identity") if isinstance(result.get("identity"), dict) else {}
                        streak_identity = {key: identity.get(key) for key in
                                           ("subject_digest", "evaluator_digest", "case_digest")}
                        if any(not isinstance(value, str) or not value for value in streak_identity.values()):
                            journal(learnings, entry + ["- stopped: clean review lacks same-subject/evaluator/case identity"])
                            stop = "clean review identity is incomplete"
                            exit_code = 1
                            break
                        clean_streak = clean_streak + 1 if clean_identity == streak_identity else 1
                        clean_identity = streak_identity
                        journal(learnings, entry + [f"- calibrated clean candidate review (streak {clean_streak}; "
                                                    f"subject/evaluator/case {streak_identity})"])
                        if clean_streak >= 2:
                            stop = "two calibrated clean reviews of the same candidate subject"
                            exit_code = 0
                            receipt["status"] = "candidate_converged"
                            break
                        continue

                    clean_streak = 0
                    clean_identity = None
                    if not findings:
                        journal(learnings, entry + ["- stopped: review has no supported, premise-preserving repair and is not clean"])
                        stop = "run or review is unresolved without an actionable repair"
                        exit_code = 1
                        break

                    print(f"== iteration {index}: improve ({len(findings)} findings)", flush=True)
                    change = improve(worktree, findings, stage / "improve", args)
                    entry += [f"- improve: {change['process'].get('status')}, {len(change['commits'])} commit(s), "
                              f"files: {', '.join(change['changed']) or 'none'}",
                              f"  - applied: {change['report'].get('applied')}",
                              f"  - skipped: {change['report'].get('skipped')}"]
                    if change["report_errors"]:
                        journal(learnings, entry + ["- stopped: improver process/report invalid",
                                                    *[f"  - {reason}" for reason in change["report_errors"]]])
                        stop = "improver process/report validation failed"
                        exit_code = 1
                        break
                    if change["out_of_scope"] or change["uncommitted"]:
                        journal(learnings, entry + [f"- stopped: out-of-scope {change['out_of_scope']}, "
                                                    f"uncommitted {change['uncommitted']}"])
                        stop = "improver changed files outside the named scope or left work uncommitted"
                        exit_code = 1
                        break
                    if not change["commits"]:
                        idle_streak += 1
                        journal(learnings, entry + [f"- stopped: improver made no commit (idle {idle_streak})"])
                        stop = "improver made no commit"
                        exit_code = 1
                        break
                    idle_streak = 0
                    print(f"== iteration {index}: verify (quick tier)", flush=True)
                    green = quick_suite(worktree, change["base"], stage / "quick-tier.log")
                    entry.append(f"- quick tier: {'green' if green else 'RED'} ({stage / 'quick-tier.log'})")
                    journal(learnings, entry)
                    if not green:
                        stop = "quick test tier is red after the improvement (not reverted)"
                        exit_code = 1
                        break
                else:
                    receipt["status"] = "iteration_cap"
                    stop = f"reached iteration cap {args.iterations} without two clean reviews"
                    exit_code = 2
    except KeyboardInterrupt:
        stop = "operator interrupted the campaign"
        exit_code = 130
        receipt["status"] = "interrupted"
    except BaseException as exc:
        stop = f"campaign exception: {type(exc).__name__}: {exc}"
        exit_code = 1
        receipt["status"] = "failed"
        receipt["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        commits = ""
        if worktree and start_sha:
            try:
                commits = git(worktree, "log", "--oneline", f"{start_sha}..HEAD")
            except (OSError, subprocess.CalledProcessError):
                pass
        if learnings.exists():
            journal(learnings, ["## Result", "", f"- stopped: {stop}", f"- branch {branch or '(not created)'}:",
                                *(f"  - {line}" for line in commits.splitlines() or ["(no commits)"]),
                                f"- campaign receipt: {receipt_path}"])
        if receipt.get("status") == "starting":
            receipt["status"] = "completed" if exit_code == 0 else "failed"
        receipt.update(stop_reason=stop, exit_code=exit_code, branch=branch, worktree=str(worktree) if worktree else None,
                       start_sha=start_sha, clean_streak=clean_streak, clean_identity=clean_identity,
                       qualification=last_qualification, commits=commits.splitlines())
        campaign_receipt(receipt_path, receipt)
    print(f"\niterate: {stop}\n  journal: {learnings}\n  campaign: {receipt_path}\n  branch:  {branch or '(not created)'}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
