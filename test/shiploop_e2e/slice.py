#!/usr/bin/env python3
"""Run one work item through ShipLoop's inner loop on a fixture repository, stop, and grade only that slice.

    python3 test/shiploop_e2e/slice.py --case node-add-function
    python3 test/shiploop_e2e/slice.py --case node-fix-bug --host grok --delegation ask-agent
    python3 test/shiploop_e2e/packets.py <output> --compare <earlier output>

A full E2E run (run.py) plans from intake and releases at the end; a step slice exercises one item's inner loop:
step-plan, test-spec, validate-existing, implement, test, document, verify, carry-forward (with an Improve child after
each implement step and the last item's carry-forward Improve child). The harness copies the case's fixture (step_cases.json) into a new git repository, records every stage before
step-plan without doing it (run.seed_run, on the plugin's own navigator, with the case's work item as the plan's only
item), records what those stages would have left (the item's base snapshot, which the base run, the mutation check, the
change inventory and the item commit read; a neutral docs/shiploop/ home, unless --seed-without-home), and the host follows
ShipLoop's packets from step-plan. A poll every POLL_SECONDS archives each distinct packet
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
  no_redo        only with --clear-at (repeatable, with --resume-prompt): every clear of the S-6 probe passed, none of the
                 fresh sessions repeated a completed state-changing call (clear.py; clear.json lists the clears and
                 slice-result.json `clear_unfired` the positions that never came)
The candidate is graded against the seed commit, committed or not: each item is assembled inside the execution
checkout, verify commits the files the step plan declares (and documentation and docs/shiploop/), and anything else is
committed only at the final return (`workspace plan-return`, at release), which a slice does not reach
(references/workspace-lifecycle.md, "Inner assembly and final return").
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
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run  # noqa: E402  (also puts skills/shiploop/scripts on sys.path)
import clear  # noqa: E402
import effort  # noqa: E402
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


CLEAR_RECORD = "clear.json"  # a list: one record per clear, in the order they fired
# What continues the run in a session that holds none of it (--resume-prompt): `names-next` is the prompt a resume
# always had (run.resume_prompt); `withheld` names no command, path or stage (condition R0 of the S-6 battery).
RESUME_PROMPTS = ("names-next", "withheld")
WITHHELD_PROMPT = "Continue the ShipLoop work for the repository in this directory."


def continue_prompt(condition: str, run_dir: str, cli: Path) -> tuple[str, dict | None]:
    """(the prompt that continues the run in a fresh session, what it told: sessions.jsonl `told`, None for nothing)."""
    if condition == "withheld":
        return WITHHELD_PROMPT, None
    return run.resume_prompt(run_dir, cli), run.resume_told(run_dir, cli)


def clear_records(out: Path) -> list[dict]:
    """The clears recorded so far, in the order they fired (none before the first)."""
    path = out / CLEAR_RECORD
    try:
        records = json.loads(path.read_text())
    except (OSError, ValueError):
        return []
    if not isinstance(records, list):
        raise SystemExit(f"{path} holds one clear record: an older slice.py wrote it. Read that run with the version "
                         "that wrote it; this one records a list.")
    return records


def drive(argv: list[str], *, work: Path, out: Path, env: dict, run_dir: Path, timeout: int, watch: bool,
          translate=None, host_name: str = "fake", model: str | None = None, first: bool = True,
          resumed_session: str | None = None, clear_at: list[dict] | None = None, told: dict | None = None,
          planner: "effort.Planner | None" = None, effort_now: str | None = None) -> dict:
    """One host session that the slice stop ends. Its status is ``slice-complete`` when the slice ended it, or when the
    session ended by itself with the slice already complete.

    With `clear_at` (clear.parse_spec) the session is also ended at the first position not yet cleared (status
    ``cleared``): the positions fire in order, and clear.json holds the ones that already did. The stop point is
    appended to clear.json and the caller continues in a fresh session. `told` is what that session's prompt named
    (sessions.jsonl).

    With `planner` (effort.Planner) the session is also ended when the position leaves the session's class (status
    ``reeffort``, the boundary kept in ``planner.pending``); `effort_now` is the effort this session was launched at."""
    hit: list = []
    earlier = clear_records(out)
    spec = clear_at[len(earlier)] if clear_at and len(earlier) < len(clear_at) else None
    since = earlier[-1]["stopped"]["events_line"] if earlier else 0

    def stop_when() -> bool:
        packets.archive_packets(run_dir, out)
        state = read_state(run_dir)
        if spec:
            found = clear.trigger(out / "events.jsonl", state, spec, metrics.current_stage, navigator.current_action,
                                  since=since)
            if found:
                hit.append(found)
                return True
        if planner and not slice_complete(state) and planner.stop_when():
            return True
        return slice_complete(state)

    started: list = []
    events_path = out / "events.jsonl"

    def begin(line: int) -> None:
        started.append(sessionlog.start(out, kind="first" if first else "continued", reason="slice", host=host_name,
                                        model=model, events_line=line, told=told, resumed_session=resumed_session,
                                        effort=effort_now))

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
        actual = clear.point(out / "events.jsonl", read_state(run_dir) or {}, metrics.current_stage,
                             navigator.current_action)
        record = {"n": len(earlier) + 1, **spec, "triggered": hit[0], "stopped": actual}
        (out / CLEAR_RECORD).write_text(json.dumps([*earlier, record], indent=2) + "\n")
        process["status"] = "cleared"
    elif planner and planner.pending and process["status"] == "interrupted":
        process["status"] = "reeffort"
    elif process["status"] == "interrupted" or (process["status"] == "exited" and slice_complete(read_state(run_dir))):
        process["status"] = "slice-complete"
    return process


def clear_facts(out: Path) -> list[dict]:
    """Each recorded clear with the redone work measured against its own stop point, from there to the next clear's
    (the last one to the end of the stream). Empty without a probe."""
    records = clear_records(out)
    facts = []
    for number, record in enumerate(records):
        until = records[number + 1]["stopped"]["events_line"] if number + 1 < len(records) else None
        found = clear.redone(out / "events.jsonl", record["stopped"]["events_line"], until)
        facts.append({**record, "redone": found, "pass": not found})
    return facts


def unfired_clears(out: Path, fired: int) -> list[str]:
    """The `--clear-at` positions the run asked for (invocation.json `clear_at`) that never fired: the positions fire in
    order, so they are the ones after the clears recorded."""
    try:
        asked = json.loads((out / "invocation.json").read_text()).get("clear_at") or []
    except (OSError, ValueError):
        return []
    return asked[fired:]


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
    if probe:
        verdicts["no_redo"] = all(c["pass"] for c in probe)
    return {"pass": all(verdicts.values()), "verdicts": verdicts, "item": item, "item_history": history,
            "overshoot": over, "queue_growth": max(0, len(state.get("work_items") or []) - 1),
            "run_status": state.get("status"), "stage_at_stop": metrics.current_stage(state) if state else None,
            "assembled": assembled, "checks": check_results, "sessions": sessions, "clear": probe,
            "clear_unfired": unfired_clears(out, len(probe)),
            "not_reached": "system tests, release and the report: a slice ends after the item's inner loop"}


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--case", help="a case from step_cases.json")
    p.add_argument("--regrade", type=Path, metavar="OUTPUT",
                   help="grade an earlier slice again from its files (no host starts), with the case it ran")
    p.add_argument("--host", choices=sorted(hosts.HOSTS), default="claude")
    p.add_argument("--model", help="default: the host's (claude-sonnet-5-5 on claude)")
    p.add_argument("--effort")
    p.add_argument("--effort-schedule", metavar="FILE|JSON",
                   help="experiment E-EFF1 (effort.py): an effort per class of position, {\"M\": .., \"I2\": .., \"D\": ..}. "
                        "The session ends at every change of class; a resumable host continues in its resumed session, "
                        "another in a fresh one (as after --clear-at), at the new class's effort")
    p.add_argument("--delegation", choices=("inline", "ask-agent"), default="inline",
                   help="inline (default): one session, every packet in the main context; ask-agent: native workers")
    p.add_argument("--plugin-dir", type=Path, help="a skill-craft plugin build to test (default: build this checkout)")
    p.add_argument("--output", type=Path, help="new directory for this attempt (default: under $TMPDIR)")
    p.add_argument("--timeout", type=int, default=None, help="seconds before the host is killed; default: none")
    p.add_argument("--max-turns", type=int, default=None,
                   help="a turn limit for the host session; default: none")
    p.add_argument("--max-budget-usd", type=float, default=None, help="claude only, default none; grok has no spend cap")
    p.add_argument("--permission-mode", default="auto")
    p.add_argument("--max-resumes", type=int, default=None,
                   help="resumable hosts (grok, codex): continue a session that ended before the slice was complete; "
                        "default: no limit")
    p.add_argument("--seed-without-home", action="store_true",
                   help="do not commit the neutral knowledge home (docs/shiploop/spec.md with R-1 = the request, environment.md "
                        "with the case's checks) into the seed repository; the item base is recorded either way. The flagged "
                        "variant, to see which refusals a run with no spec hits")
    p.add_argument("--clear-at", action="append", metavar="STAGE[:inside]",
                   help="the S-6 probe, repeatable: stop the host when STAGE's packet arrives (or, with :inside, after "
                        "its first completed call), continue in a fresh session, and grade no_redo (clear.py). STAGE "
                        "`improve` is an Improve stage. The positions fire in the order given, one per session")
    p.add_argument("--resume-prompt", choices=RESUME_PROMPTS, default="names-next",
                   help="what continues the run in a session after a clear: names-next (default) is the resume prompt, "
                        "which names the next command and the run directory; withheld names none of them (condition R0)")
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
        if result["clear"] or result["clear_unfired"]:
            print(f"  clears: {len(result['clear'])} fired ({sum(len(c['redone']) for c in result['clear'])} redone calls)"
                  + (f"; never fired: {', '.join(result['clear_unfired'])}" if result["clear_unfired"] else ""), flush=True)
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
    clear_at = clear.parse_spec(args.clear_at)  # a malformed position ends the command before anything is built
    run.install_termination_handlers()
    out = run.new_output_dir(args.output, f"slice-{args.case}")
    work = out / "work"
    work.mkdir()
    host = hosts.host(args.host, getattr(args, f"{args.host}_bin"))
    model, effort_level = args.model or host.model, args.effort or host.effort
    env = host.env(out / "home")
    plugin_dir = (args.plugin_dir.expanduser().resolve() if args.plugin_dir else run.build_candidate(out))
    plugin = host.install_plugin(env, plugin_dir)
    cli = run.run_cli(host.name, out, plugin_dir)
    seeded = run.seed_run(cli, work, out, case["prompt"], SEED_AT, fixture=FIXTURES / case["fixture"],
                          work_item=case["work_item"], delegation=args.delegation, checks=case["checks"],
                          home=not args.seed_without_home)
    run_dir = Path(seeded["run_dir"])
    opening = host.invoke(host.skill, run.seed_prompt(cli, str(run_dir), case["prompt"], args.delegation))
    common = dict(cwd=work, model=model, effort=effort_level, permission_mode=args.permission_mode, max_turns=args.max_turns,
                  max_budget_usd=args.max_budget_usd, plugin_dir=None if host.marketplace else plugin_dir)
    planner = None
    fresh_start, planned_id = 0, None

    def current_session_id() -> str | None:
        events = out / "events.jsonl"
        return (run.last_session_id(events, since=fresh_start) if events.exists() else None) or planned_id

    def fresh_argv(prompt: str, prompt_file: Path) -> list[str]:
        nonlocal fresh_start, planned_id
        fresh_start, planned_id = run.events_line_count(out / "events.jsonl"), None
        argv = host.argv(prompt=prompt, prompt_file=prompt_file, **common)
        if planner and host.name == "grok":
            planned_id = str(uuid.uuid4())
            argv += ["--session-id", planned_id]
            (out / run.PLANNED_SESSION_FILE).write_text(planned_id + "\n")
        return argv

    if args.effort_schedule is not None:
        try:
            schedule = effort.parse_schedule(args.effort_schedule)
            effort.check_levels(schedule, host.name)
            if args.effort and args.effort != schedule["D"]:
                raise effort.ScheduleError(f"--effort {args.effort} with --effort-schedule: the schedule names every level, "
                                           f"so drop --effort or make it class D's ({schedule['D']})")
            effort_level = schedule["D"]
            (out / effort.SCHEDULE_FILE).write_text(json.dumps(schedule, indent=2) + "\n")
            planner = effort.Planner(out, schedule, locate=lambda: run_dir, current_stage=metrics.current_stage,
                                     can_resume=((lambda: current_session_id() is not None)
                                                 if host.resumable else None))  # a fresh-session host needs no id
        except effort.ScheduleError as err:
            raise SystemExit(str(err))
        common["effort"] = planner.at_launch("start")[1]  # a slice starts at step-plan: class D

    def next_effort(why: str) -> str | None:
        """The effort the next session starts at: the schedule's for the class the run is in now, else the run's own."""
        if planner:
            common["effort"] = planner.at_launch(why)[1]
        return common["effort"] if planner else None
    invocation = {"case": args.case, "kind": "step-slice", "host": host.name, "model": model, "effort": effort_level,
                  "delegation": args.delegation, "plugin_dir": str(plugin_dir), "plugin": plugin,
                  "versions": run.installed_versions(plugin_dir), "local_head": run.git("rev-parse", "HEAD").strip(),
                  "seeded": seeded, "checks": case["checks"], "expect_paths": case.get("expect_paths"),
                  "clear_at": [clear.label(spec) for spec in clear_at], "resume_prompt": args.resume_prompt,
                  "effort_schedule": planner.schedule if planner else None}
    (out / "invocation.json").write_text(json.dumps(invocation, indent=2) + "\n")
    (out / "prompt.txt").write_text(case["prompt"] + "\n")
    if not args.quiet:
        print(f"slice {args.case} host={host.name} model={model} delegation={args.delegation}\n  output {out}\n"
              f"  seeded {', '.join(seeded['skipped'])}; the host starts at {seeded['stage']}", flush=True)

    if host.name != "claude" and any(spec["inside"] for spec in clear_at) and not args.quiet:
        print("note: an :inside position needs Claude's stream (clear.py); on this host it is recorded as requested and "
              "will not fire", flush=True)
    deadline = time.monotonic() + (args.timeout or float("inf"))  # active time, as in run.py: sleep spends none of it
    session_args = dict(work=work, out=out, env=env, run_dir=run_dir, watch=not args.quiet,
                        translate=host.translator(), host_name=host.name, model=model, clear_at=clear_at, planner=planner)
    first_argv = fresh_argv(opening, out / "host-prompt.txt")
    process = drive(first_argv, timeout=args.timeout or float("inf"), effort_now=common["effort"] if planner else None, **session_args)
    sessions = [process]
    resumes = 0
    while True:
        if process["status"] == "cleared":
            # A fresh session: no --resume, so the model holds nothing but what this prompt says (--resume-prompt).
            number = len(clear_records(out))
            if not args.quiet:
                print(f"cleared at {clear_records(out)[-1]['stopped']}; continuing in a fresh session "
                      f"(prompt {args.resume_prompt})", flush=True)
            prompt, told = continue_prompt(args.resume_prompt, str(run_dir), cli)
            now = next_effort("clear")
            process = drive(fresh_argv(prompt, out / f"resume-after-clear-{number}.txt"),
                            timeout=max(60, deadline - time.monotonic()), first=False, told=told, effort_now=now,
                            **session_args)
        elif process["status"] == "reeffort" and deadline - time.monotonic() > 60:
            # The position left its class (effort.py): the control arm restarts here too, at the same level. A host that
            # can resume continues its own session; another gets a fresh one, as after a clear. Neither spends the resume
            # budget.
            boundary = planner.consume()
            now = next_effort("restart")
            if not args.quiet:
                print(f"effort boundary {boundary['from']} -> {boundary['to']} at {boundary['stage']} ({boundary['why']}); "
                      f"continuing at effort {now}", flush=True)
            session_id = current_session_id() if host.resumable else None
            if host.resumable and not session_id:
                break
            if host.resumable:
                argv = host.argv(prompt=run.resume_prompt(str(run_dir), cli, effort.RESTART_NOTE),
                                 prompt_file=out / f"resume-{len(sessions)}.txt", resume=session_id, **common)
                process = drive(argv, timeout=deadline - time.monotonic(), first=False, resumed_session=session_id,
                                told=run.resume_told(str(run_dir), cli), effort_now=now, **session_args)
            else:
                prompt, told = continue_prompt(args.resume_prompt, str(run_dir), cli)
                process = drive(fresh_argv(prompt, out / f"resume-after-effort-{len(sessions)}.txt"),
                                timeout=deadline - time.monotonic(), first=False, told=told, effort_now=now, **session_args)
        elif (host.resumable and process["status"] == "exited" and (args.max_resumes is None or resumes < args.max_resumes)
              and (read_state(run_dir) or {}).get("status") == "active" and deadline - time.monotonic() > 60):
            # A headless Grok or Codex session ends whenever the model ends its turn; continue it while the slice is
            # unfinished (the clears still to come stay in force). A clear is not a resume: it does not use the budget.
            session_id = current_session_id()
            if not session_id:
                break
            resumes += 1
            now = next_effort("resume")
            argv = host.argv(prompt=run.resume_prompt(str(run_dir), cli), prompt_file=out / f"resume-{len(sessions)}.txt",
                             resume=session_id, **common)
            process = drive(argv, timeout=deadline - time.monotonic(), first=False, resumed_session=session_id,
                            effort_now=now,
                            told=run.resume_told(str(run_dir), cli), **session_args)
        else:
            break
        sessions.append(process)

    run.write_transcript(out / "events.jsonl", out / "transcript.md")
    return finish(out, run_dir, seeded, case, sessions,
                  {"case": args.case, "host": host.name, "model": model, "delegation": args.delegation}, args.quiet)

if __name__ == "__main__":
    raise SystemExit(main())
