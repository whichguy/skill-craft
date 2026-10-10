#!/usr/bin/env python3
"""Run one work item through ShipLoop's inner loop on a fixture repository, stop, and grade only that slice.

    python3 test/shiploop_e2e/slice.py --case node-add-function
    python3 test/shiploop_e2e/slice.py --case node-fix-bug --host grok --delegation ask-agent
    python3 test/shiploop_e2e/packets.py <output> --compare <earlier output>

A full E2E run (run.py) plans from intake and releases at the end; a step slice exercises one item's inner loop:
get-next-work-item, step-plan, ... implement ... integrate, carry-forward (and the last item's carry-forward Improve
child). The harness copies the case's fixture (step_cases.json) into a new git repository, records every stage before
step-plan without doing it (run.seed_run, on the plugin's own navigator, with the case's work item as the plan's only
item), and the host follows ShipLoop's packets from step-plan. A poll every POLL_SECONDS archives each distinct packet
ShipLoop emits (packets.archive_packets) and ends the host once the item's inner loop is over (``slice_complete``): the
item is advanced past, the run left the inner loop, or the run is no longer active. That stop is final: nothing resumes
a completed slice.

Everything is written under the output directory (default $TMPDIR/shiploop-e2e/slice-<case>-...): the product
repository (work/), ShipLoop's run directory and its product worktree (.shiploop-runs/seed/), the plugin built from this
checkout (build/), the event stream, the packet archive, slice-result.json, metrics.json and packet-report.md. No baseline
row is written; nothing is installed into a host's own plugin set (Claude loads the build with --plugin-dir; Grok and
Codex run in a throwaway HOME, but Claude's session transcript lands in the user's ~/.claude/projects).

Verdicts (slice-result.json):
  process        the host was ended by the slice stop (``slice-complete``), not a timeout, failure or crash
  inner_loop     the item's carry-forward was accepted done
  no_overshoot   no result was accepted for an outer stage or for another item (the stop held)
  committed      in ShipLoop's product worktree, the commits after the seed touch every expected path of the case,
                 hold a product change beyond docs/shiploop/, and nothing outside docs/shiploop/ is left uncommitted
  checks         every case check exits 0 in a clean `git archive HEAD` export of that worktree
ShipLoop command failures, model glue and queue growth (items a carry-forward added) are recorded, not verdicts.
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run  # noqa: E402  (also puts skills/shiploop/scripts on sys.path)
import hosts  # noqa: E402
import metrics  # noqa: E402
import packets  # noqa: E402
import sessionlog  # noqa: E402
import shiploop_navigator as navigator  # noqa: E402
import shiploop_stage_spec as stage_spec  # noqa: E402
import shiploop_store as store  # noqa: E402

STEP_CASES = HERE / "step_cases.json"
FIXTURES = HERE / "fixtures"
SEED_AT = "step-plan"
KNOWLEDGE = "docs/shiploop/"  # ShipLoop's own knowledge home: neither the product nor a leftover


def load_step_case(name: str) -> dict:
    cases = {k: v for k, v in json.loads(STEP_CASES.read_text()).items() if not k.startswith("_")}
    if name not in cases:
        raise SystemExit(f"unknown step case {name!r}; known: {', '.join(sorted(cases))}")
    return cases[name]


def read_state(run_dir: Path) -> dict | None:
    try:
        state = store.read_record(run_dir / "state.md")
    except (store.StorageError, OSError):
        return None  # mid-write or not yet there: the next poll reads it again
    return state if isinstance(state, dict) else None


def slice_complete(state: dict | None) -> bool:
    """The first item's inner loop is over: the run advanced past it, left the inner loop, or stopped being active."""
    if state is None:
        return False
    if state.get("status") != "active" or state.get("work_index", 0) > 0:
        return True
    try:
        return navigator.current_stage(state) not in stage_spec.INNER
    except Exception:  # noqa: BLE001 - an unreadable cursor is not a stop
        return False


def overshoot(state: dict, item: str) -> list[str]:
    """Accepted results past the slice: an outer stage, or an inner stage of another work item."""
    return [row.get("stage") for row in state.get("history") or [] if isinstance(row, dict) and (
        row.get("stage") in stage_spec.OUTER
        or (row.get("stage") in stage_spec.INNER and row.get("workitem") not in (None, item)))]


def item_history(state: dict, item: str) -> list[dict]:
    return [{"stage": row.get("stage"), "outcome": row.get("outcome")} for row in state.get("history") or []
            if isinstance(row, dict) and row.get("workitem") == item]


def _git(worktree: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(worktree), *args], capture_output=True, text=True)


def committed_product(worktree: Path | None, start_head: str, expect_paths: list[str]) -> dict:
    """Whether the item's work is committed in ShipLoop's product worktree, from git alone."""
    if worktree is None or not worktree.is_dir():
        return {"pass": False, "reason": "no product worktree"}
    head = _git(worktree, "rev-parse", "HEAD").stdout.strip()
    changed = [p for p in _git(worktree, "diff", "--name-only", start_head, "HEAD").stdout.splitlines() if p]
    product = [p for p in changed if not p.startswith(KNOWLEDGE)]
    missing = [pattern for pattern in expect_paths if not any(fnmatch.fnmatch(p, pattern) for p in changed)]
    outstanding = [line[3:] for line in _git(worktree, "status", "--porcelain", "--untracked-files=all").stdout.splitlines()
                   if line[3:] and not line[3:].startswith(KNOWLEDGE)]
    reasons = [*(["no commit after the seed"] if head == start_head else []),
               *(["only ShipLoop knowledge files were committed"] if changed and not product else []),
               *([f"expected paths not committed: {', '.join(missing)}"] if missing else []),
               *([f"uncommitted: {', '.join(outstanding[:10])}"] if outstanding else [])]
    return {"pass": not reasons, "head": head, "changed": changed, "missing": missing, "outstanding": outstanding,
            "reason": "; ".join(reasons) or None}


def checks_on_head(worktree: Path | None, out: Path, checks: list[str]) -> list[dict]:
    """Run the case checks in a clean export of the worktree's HEAD, so uncommitted files cannot make them pass."""
    if worktree is None or not worktree.is_dir():
        return [{"command": c, "pass": False, "output": "no product worktree"} for c in checks]
    export = out / "export"
    export.mkdir(exist_ok=True)
    archive = subprocess.run(["git", "-C", str(worktree), "archive", "--format=tar", "HEAD"], capture_output=True)
    subprocess.run(["tar", "-x", "-C", str(export)], input=archive.stdout, check=True)
    return run.run_checks(export, checks)


def drive(argv: list[str], *, work: Path, out: Path, env: dict, run_dir: Path, timeout: int, watch: bool,
          translate=None, host_name: str = "fake", model: str | None = None, first: bool = True,
          resumed_session: str | None = None) -> dict:
    """One host session that the slice stop ends. Its status is ``slice-complete`` when the slice ended it, or when the
    session ended by itself with the slice already complete."""
    def stop_when() -> bool:
        packets.archive_packets(run_dir, out)
        return slice_complete(read_state(run_dir))

    started: list = []
    events_path = out / "events.jsonl"

    def begin(line: int) -> None:
        started.append(sessionlog.start(out, kind="first" if first else "continued", reason="slice", host=host_name,
                                        model=model, events_line=line, told=None, resumed_session=resumed_session))

    process = None
    try:
        process = run.launch(argv, work, out, env, timeout, watch, first=first, fresh=False, translate=translate,
                             stop_when=stop_when, stop_file=out / "stop", before_start=begin)
    finally:
        if started:
            sessionlog.end(out, started[0], events_line=run.events_line_count(events_path, repair=False),
                           status=(process or {}).get("status", "crashed"), returncode=(process or {}).get("returncode"),
                           engine=None)
    packets.archive_packets(run_dir, out)
    process.pop("left_behind", None)
    if process["status"] == "interrupted" or (process["status"] == "exited" and slice_complete(read_state(run_dir))):
        process["status"] = "slice-complete"
    return process


def grade(out: Path, run_dir: Path, seeded: dict, case: dict, sessions: list[dict]) -> dict:
    state = read_state(run_dir) or {}
    item = case["work_item"]["id"]
    history = item_history(state, item)
    carried = any(row["stage"] == "carry-forward" and row["outcome"] == "done" for row in history)
    over = overshoot(state, item)
    worktree = run_dir.parent / "worktree"
    committed = committed_product(worktree, seeded["start_head"], case.get("expect_paths") or [])
    check_results = checks_on_head(worktree, out, case["checks"])
    verdicts = {"process": sessions[-1]["status"] == "slice-complete", "inner_loop": carried, "no_overshoot": not over,
                "committed": committed["pass"], "checks": all(c["pass"] for c in check_results)}
    return {"pass": all(verdicts.values()), "verdicts": verdicts, "item": item, "item_history": history,
            "overshoot": over, "queue_growth": max(0, len(state.get("work_items") or []) - 1),
            "run_status": state.get("status"), "stage_at_stop": metrics.current_stage(state) if state else None,
            "committed": committed, "checks": check_results, "sessions": sessions,
            "not_reached": "system tests, release and the report: a slice ends after the item's inner loop"}


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--case", required=True, help="a case from step_cases.json")
    p.add_argument("--host", choices=sorted(hosts.HOSTS), default="claude")
    p.add_argument("--model", help="default: the host's (claude-sonnet-5-5 on claude)")
    p.add_argument("--effort")
    p.add_argument("--delegation", choices=("inline", "ask-agent"), default="inline",
                   help="inline (default): one session, every packet in the main context; ask-agent: native workers")
    p.add_argument("--plugin-dir", type=Path, help="a skill-craft plugin build to test (default: build this checkout)")
    p.add_argument("--output", type=Path, help="new directory for this attempt (default: under $TMPDIR)")
    p.add_argument("--timeout", type=int, default=3600, help="seconds before the host is killed")
    p.add_argument("--max-turns", type=int, default=2000)
    p.add_argument("--max-budget-usd", type=float, default=10.0, help="claude only; grok has no spend cap")
    p.add_argument("--permission-mode", default="auto")
    p.add_argument("--max-resumes", type=int, default=5,
                   help="resumable hosts (grok, codex): continue a session that ended before the slice was complete")
    p.add_argument("--quiet", action="store_true")
    for name in sorted(hosts.HOSTS):
        p.add_argument(f"--{name}-bin", default=name)
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    case = load_step_case(args.case)
    run.install_termination_handlers()
    out = run.new_output_dir(args.output, f"slice-{args.case}")
    work = out / "work"
    work.mkdir()
    host = hosts.host(args.host, getattr(args, f"{args.host}_bin"))
    model, effort = args.model or host.model, args.effort or host.effort
    env = host.env(out / "home")
    plugin_dir = (args.plugin_dir.expanduser().resolve() if args.plugin_dir else run.build_candidate(out))
    plugin = host.install_plugin(env, plugin_dir)
    cli = run.run_cli(host.name, out, plugin_dir)
    seeded = run.seed_run(cli, work, out, case["prompt"], SEED_AT, fixture=FIXTURES / case["fixture"],
                          work_item=case["work_item"], delegation=args.delegation)
    run_dir = Path(seeded["run_dir"])
    opening = host.invoke(host.skill, run.seed_prompt(cli, str(run_dir), case["prompt"], args.delegation))
    common = dict(cwd=work, model=model, effort=effort, permission_mode=args.permission_mode, max_turns=args.max_turns,
                  max_budget_usd=args.max_budget_usd, plugin_dir=None if host.marketplace else plugin_dir)
    invocation = {"case": args.case, "kind": "step-slice", "host": host.name, "model": model, "effort": effort,
                  "delegation": args.delegation, "plugin_dir": str(plugin_dir), "plugin": plugin,
                  "versions": run.installed_versions(plugin_dir), "local_head": run.git("rev-parse", "HEAD").strip(),
                  "seeded": seeded, "checks": case["checks"], "expect_paths": case.get("expect_paths")}
    (out / "invocation.json").write_text(json.dumps(invocation, indent=2) + "\n")
    (out / "prompt.txt").write_text(case["prompt"] + "\n")
    if not args.quiet:
        print(f"slice {args.case} host={host.name} model={model} delegation={args.delegation}\n  output {out}\n"
              f"  seeded {', '.join(seeded['skipped'])}; the host starts at {seeded['stage']}", flush=True)

    deadline = time.time() + args.timeout
    session_args = dict(work=work, out=out, env=env, run_dir=run_dir, watch=not args.quiet,
                        translate=host.translator(), host_name=host.name, model=model)
    process = drive(host.argv(prompt=opening, prompt_file=out / "host-prompt.txt", **common),
                    timeout=args.timeout, **session_args)
    sessions = [process]
    # A headless Grok or Codex session ends whenever the model ends its turn; continue it while the slice is unfinished.
    while (host.resumable and process["status"] == "exited" and len(sessions) <= args.max_resumes
           and (read_state(run_dir) or {}).get("status") == "active" and deadline - time.time() > 60):
        session_id = run.last_session_id(out / "events.jsonl")
        if not session_id:
            break
        argv = host.argv(prompt=run.resume_prompt(str(run_dir), cli), prompt_file=out / f"resume-{len(sessions)}.txt",
                         resume=session_id, **common)
        process = drive(argv, timeout=int(deadline - time.time()), first=False, resumed_session=session_id,
                        **session_args)
        sessions.append(process)

    run.write_transcript(out / "events.jsonl", out / "transcript.md")
    result = {"case": args.case, "host": host.name, "model": model, "delegation": args.delegation, "output": str(out),
              "run_dir": str(run_dir), "worktree": str(run_dir.parent / "worktree"),
              **grade(out, run_dir, seeded, case, sessions)}
    (out / "slice-result.json").write_text(json.dumps(result, indent=2) + "\n")
    report = packets.write_report(out)
    (out / "metrics.json").write_text(json.dumps(metrics.collect(out, run_dir), indent=2) + "\n")
    if not args.quiet:
        print("\n" + packets.render(report), end="")
        print(f"\nslice {'PASS' if result['pass'] else 'FAIL'}: "
              + ", ".join(f"{k} {'ok' if v else 'FAIL'}" for k, v in result["verdicts"].items())
              + f"\n  {out / 'packet-report.md'}", flush=True)
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
