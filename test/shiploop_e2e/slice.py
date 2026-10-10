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
checkout (build/), the event stream, the packet archive, slice-result.json, metrics.json, packet-report.md, and
flow.json with flow.html (flow.py: the ShipLoop-to-model sequence, browsable with other runs). No baseline
row is written; nothing is installed into a host's own plugin set (Claude loads the build with --plugin-dir; Grok and
Codex run in a throwaway HOME, but Claude's session transcript lands in the user's ~/.claude/projects).

Verdicts (slice-result.json):
  process        the host was ended by the slice stop (``slice-complete``), not a timeout, failure or crash
  inner_loop     the item's carry-forward was accepted done
  no_overshoot   no result was accepted for an outer stage or for another item (the stop held)
  assembled      ShipLoop's product worktree holds the item's candidate: against the seed, its tracked and untracked
                 (not ignored) files change every expected path of the case, and change a product file, not only
                 ShipLoop's own (docs/shiploop/ knowledge, .shiploop-improve/ run evidence)
  checks         every case check exits 0 in a clean copy of that candidate (the files `workspace plan-return` would
                 commit: tracked and untracked, not ignored, without ShipLoop's run evidence)
The candidate is graded uncommitted on purpose: the inner `integrate` stage assembles each item inside the execution
checkout, and the product is committed only at the final return (`workspace plan-return`, at release), which a slice
does not reach (references/workspace-lifecycle.md, "Inner assembly and final return"). Observed on the first live
slice, 2026-10-10: the fix was correct and uncommitted; only knowledge files had been committed.
ShipLoop command failures, model glue and queue growth (items a carry-forward added) are recorded, not verdicts.
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run  # noqa: E402  (also puts skills/shiploop/scripts on sys.path)
import clear  # noqa: E402
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
# ShipLoop's own files in the product checkout: its knowledge home and an Improve child's run evidence. Neither is the
# product; plan-return keeps run evidence out of the return.
SHIPLOOP_OWN = ("docs/shiploop/", ".shiploop-improve/")


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


def candidate_files(worktree: Path) -> list[str]:
    """The files `workspace plan-return` would consider: tracked and untracked, not ignored, without ShipLoop's own."""
    listed = _git(worktree, "ls-files", "-z", "--cached", "--others", "--exclude-standard").stdout.split("\0")
    return sorted({p for p in listed if p and not p.startswith(SHIPLOOP_OWN[1]) and (worktree / p).is_file()})


def assembled_product(worktree: Path | None, start_head: str, expect_paths: list[str]) -> dict:
    """Whether the item's candidate is assembled in ShipLoop's product worktree, committed or not (git alone)."""
    if worktree is None or not worktree.is_dir():
        return {"pass": False, "reason": "no product worktree"}
    tracked = [p for p in _git(worktree, "diff", "--name-only", start_head).stdout.splitlines() if p]
    untracked = [p for p in _git(worktree, "ls-files", "--others", "--exclude-standard").stdout.splitlines() if p]
    changed = sorted({*tracked, *untracked})
    product = [p for p in changed if not p.startswith(SHIPLOOP_OWN)]
    missing = [pattern for pattern in expect_paths if not any(fnmatch.fnmatch(p, pattern) for p in product)]
    committed = [p for p in _git(worktree, "diff", "--name-only", start_head, "HEAD").stdout.splitlines() if p]
    reasons = [*(["no product change, only ShipLoop's own files"] if not product else []),
               *([f"expected paths unchanged: {', '.join(missing)}"] if missing else [])]
    return {"pass": not reasons, "changed": product, "missing": missing,
            "committed_since_seed": committed, "uncommitted_product": sorted(set(product) - set(committed)),
            "reason": "; ".join(reasons) or None}


def checks_on_candidate(worktree: Path | None, out: Path, checks: list[str]) -> list[dict]:
    """Run the case checks in a clean copy of the candidate, so ignored files (node_modules) and run evidence don't count."""
    if worktree is None or not worktree.is_dir():
        return [{"command": c, "pass": False, "output": "no product worktree"} for c in checks]
    export = out / "export"
    if export.exists():
        shutil.rmtree(export)
    for relative in candidate_files(worktree):
        target = export / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(worktree / relative, target)
    export.mkdir(exist_ok=True)
    return run.run_checks(export, checks)


CLEAR_RECORD = "clear.json"


def drive(argv: list[str], *, work: Path, out: Path, env: dict, run_dir: Path, timeout: int, watch: bool,
          translate=None, host_name: str = "fake", model: str | None = None, first: bool = True,
          resumed_session: str | None = None, clear_at: dict | None = None) -> dict:
    """One host session that the slice stop ends. Its status is ``slice-complete`` when the slice ended it, or when the
    session ended by itself with the slice already complete.

    With `clear_at` (clear.parse_spec) and no clear recorded yet, the session is also ended at that point (status
    ``cleared``) and the stop point is written to clear.json: the caller then continues in a fresh session."""
    hit: list = []

    def stop_when() -> bool:
        packets.archive_packets(run_dir, out)
        state = read_state(run_dir)
        if clear_at and not (out / CLEAR_RECORD).exists():
            found = clear.trigger(out / "events.jsonl", state, clear_at, metrics.current_stage)
            if found:
                hit.append(found)
                return True
        return slice_complete(state)

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
    if hit and process["status"] == "interrupted":
        # Recorded after the kill, so the point is where the stop actually landed (an overrun is work done before it).
        actual = clear.point(out / "events.jsonl", read_state(run_dir) or {}, metrics.current_stage)
        (out / CLEAR_RECORD).write_text(json.dumps({**clear_at, "triggered": hit[0], "stopped": actual}, indent=2) + "\n")
        process["status"] = "cleared"
    elif process["status"] == "interrupted" or (process["status"] == "exited" and slice_complete(read_state(run_dir))):
        process["status"] = "slice-complete"
    return process


def clear_facts(out: Path) -> dict | None:
    """The probe's record and the redone work measured against the actual stop point (None without a probe)."""
    try:
        record = json.loads((out / CLEAR_RECORD).read_text())
    except (OSError, ValueError):
        return None
    found = clear.redone(out / "events.jsonl", record["stopped"]["events_line"])
    return {**record, "redone": found, "pass": not found}


def grade(out: Path, run_dir: Path, seeded: dict, case: dict, sessions: list[dict]) -> dict:
    state = read_state(run_dir) or {}
    item = case["work_item"]["id"]
    history = item_history(state, item)
    carried = any(row["stage"] == "carry-forward" and row["outcome"] == "done" for row in history)
    over = overshoot(state, item)
    worktree = run_dir.parent / "worktree"
    assembled = assembled_product(worktree, seeded["start_head"], case.get("expect_paths") or [])
    check_results = checks_on_candidate(worktree, out, case["checks"])
    verdicts = {"process": sessions[-1]["status"] == "slice-complete", "inner_loop": carried, "no_overshoot": not over,
                "assembled": assembled["pass"], "checks": all(c["pass"] for c in check_results)}
    probe = clear_facts(out)
    if probe is not None:
        verdicts["no_redo"] = probe["pass"]
    return {"pass": all(verdicts.values()), "verdicts": verdicts, "item": item, "item_history": history,
            "overshoot": over, "queue_growth": max(0, len(state.get("work_items") or []) - 1),
            "run_status": state.get("status"), "stage_at_stop": metrics.current_stage(state) if state else None,
            "assembled": assembled, "checks": check_results, "sessions": sessions, "clear": probe,
            "not_reached": "system tests, release and the report: a slice ends after the item's inner loop"}


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--case", help="a case from step_cases.json")
    p.add_argument("--regrade", type=Path, metavar="OUTPUT",
                   help="grade an earlier slice again from its files (no host starts), with the case it ran")
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
    p.add_argument("--clear-at", metavar="STAGE[:inside]",
                   help="the S-6 probe: stop the host when STAGE's packet arrives (or, with :inside, after its first "
                        "completed call), continue in a fresh session, and grade no_redo (clear.py)")
    p.add_argument("--quiet", action="store_true")
    for name in sorted(hosts.HOSTS):
        p.add_argument(f"--{name}-bin", default=name)
    return p


def finish(out: Path, run_dir: Path, seeded: dict, case: dict, sessions: list[dict], identity: dict, quiet: bool) -> int:
    result = {**identity, "output": str(out), "run_dir": str(run_dir), "worktree": str(run_dir.parent / "worktree"),
              **grade(out, run_dir, seeded, case, sessions)}
    (out / "slice-result.json").write_text(json.dumps(result, indent=2) + "\n")
    report = packets.write_report(out)
    (out / "metrics.json").write_text(json.dumps(metrics.collect(out, run_dir), indent=2) + "\n")
    flow_line = run.flow_record(out)
    if not quiet:
        print("\n" + packets.render(report), end="")
        print(f"\nslice {'PASS' if result['pass'] else 'FAIL'}: "
              + ", ".join(f"{k} {'ok' if v else 'FAIL'}" for k, v in result["verdicts"].items())
              + f"\n  {out / 'packet-report.md'}\n  flow {flow_line}", flush=True)
    return 0 if result["pass"] else 1


def regrade(out: Path, quiet: bool) -> int:
    out = out.expanduser().resolve()
    invocation = json.loads((out / "invocation.json").read_text())
    earlier = json.loads((out / "slice-result.json").read_text())
    seeded = invocation["seeded"]
    identity = {k: invocation.get(k) for k in ("case", "host", "model", "delegation")}
    return finish(out, Path(seeded["run_dir"]), seeded, load_step_case(invocation["case"]), earlier["sessions"],
                  {**identity, "regraded": True}, quiet)


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.regrade:
        return regrade(args.regrade, args.quiet)
    if not args.case:
        raise SystemExit("--case is required (or --regrade OUTPUT)")
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
    clear_at = clear.parse_spec(args.clear_at)
    process = drive(host.argv(prompt=opening, prompt_file=out / "host-prompt.txt", **common),
                    timeout=args.timeout, clear_at=clear_at, **session_args)
    sessions = [process]
    if process["status"] == "cleared":
        # A fresh session: no --resume, so the model holds nothing but what the recovery command prints.
        if not args.quiet:
            print(f"cleared at {json.loads((out / CLEAR_RECORD).read_text())['stopped']}; continuing in a fresh session",
                  flush=True)
        process = drive(host.argv(prompt=run.resume_prompt(str(run_dir), cli), prompt_file=out / "resume-after-clear.txt",
                                  **common),
                        timeout=max(60, int(deadline - time.time())), first=False, **session_args)
        sessions.append(process)
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
    return finish(out, run_dir, seeded, case, sessions,
                  {"case": args.case, "host": host.name, "model": model, "delegation": args.delegation}, args.quiet)

if __name__ == "__main__":
    raise SystemExit(main())
