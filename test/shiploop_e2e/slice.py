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
flow.json with flow.html (flow.py: the ShipLoop-to-model sequence, browsable with other runs), and .harness-lock, held
while the slice runs (listeners.hold_case, as run.py holds it). No baseline
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
import os
import shlex
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
import listeners  # noqa: E402
import metrics  # noqa: E402
import overlay as overlays  # noqa: E402
import packets  # noqa: E402
import sessionlog  # noqa: E402
import shiploop_navigator as navigator  # noqa: E402
import shiploop_stage_spec as stage_spec  # noqa: E402
import shiploop_store as store  # noqa: E402

STEP_CASES = HERE / "step_cases.json"
FIXTURES = HERE / "fixtures"
SEED_AT = "step-plan"
# Where an experiment slice may start (experiment.py): the stages before it are recorded from the case (its
# ``seed_records`` merge into those synthetic results, as a step-plan seed does).
SEED_POINTS = ("test-strategy", "step-plan", "test-spec")
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


def _order(stage: str | None) -> int:
    return stage_spec.STAGES.index(stage) if stage in stage_spec.STAGES else -1


def stop_reached(state: dict | None, stop_after: str) -> bool:
    """The run is past ``stop_after``: its result was accepted done and the cursor moved on (an Improve child after it
    finishes first), or the run left the first item or stopped being active."""
    if state is None:
        return False
    if state.get("status") != "active" or state.get("work_index", 0) > 0:
        return True
    try:
        here = navigator.current_stage(state)
    except Exception:  # noqa: BLE001 - an unreadable cursor is not a stop
        return False
    accepted = any(isinstance(row, dict) and row.get("stage") == stop_after and row.get("outcome") == "done"
                   for row in state.get("history") or [])
    return accepted and _order(here) > _order(stop_after)


def overshoot_after(state: dict, stop_after: str) -> list[str]:
    """Accepted results for a stage later than ``stop_after`` (the stop did not hold)."""
    return [row.get("stage") for row in state.get("history") or []
            if isinstance(row, dict) and _order(row.get("stage")) > _order(stop_after)]


def merged_records(case: dict, extra: Path | None) -> dict | None:
    """The case's ``seed_records`` with an arm's own (``--seed-records``) merged over them, stage by stage."""
    records = {stage: dict(fields) for stage, fields in (case.get("seed_records") or {}).items()}
    for stage, fields in (json.loads(extra.read_text()) if extra else {}).items():
        records[stage] = {**records.get(stage, {}), **fields}
    return records or None


def seed_gap(seed_at: str, records: dict | None) -> str:
    """Why a seed past step-plan would leave implement nothing to build, or "".

    Implement builds each step's Until Loop from the recorded step plan's steps; a synthetic step-plan without any makes it
    refuse every done result, so the slice reaches implement only if test-spec happens to send the plan back.
    """
    if SEED_POINTS.index(seed_at) <= SEED_POINTS.index("step-plan") or ((records or {}).get("step-plan") or {}).get("steps"):
        return ""
    return (f"--seed-at {seed_at} records step-plan without doing it, and the case's seed_records give it no steps, so implement "
            "would have no step to build its loop from. Seed at step-plan, or give step-plan steps in the case's seed_records "
            "or --seed-records. Nothing was started.")


def seed_state(case: dict, out: Path, env: dict) -> dict | None:
    """A case's ``seed_state`` ({"env": NAME, "from": "<fixture folder>"}): a local target that keeps state between
    commands, outside every checkout (<output>/target), pre-loaded from the fixture as an earlier stage left it. NAME is
    set to its path in the host's environment, which every command ShipLoop runs (the base run too) inherits."""
    spec = case.get("seed_state")
    if not spec:
        return None
    target = out / "target"
    shutil.copytree(FIXTURES / spec["from"], target, dirs_exist_ok=True)
    env[spec["env"]] = str(target)
    return {"env": spec["env"], "path": str(target),
            "files": sorted(str(p.relative_to(target)) for p in target.rglob("*") if p.is_file())}


def fake_sf(case: dict, out: Path, env: dict) -> dict | None:
    """A case's ``fake_sf`` ({"orgs": "de"}): fake_sf.py first on PATH as ``sf`` (<output>/shim), with its org state and
    call log under <output>/fake-sf, so no command of the slice can reach a real org through ``sf`` (this machine has a
    logged-in one). The shim goes into the host's environment, which every command ShipLoop and the host run inherits,
    and into this process's own, which the case checks at grading (run.run_checks) and a regrade inherit."""
    spec = case.get("fake_sf")
    if not spec:
        return None
    shim, folder = out / "shim", out / "fake-sf"
    shim.mkdir(exist_ok=True)
    folder.mkdir(exist_ok=True)
    sf = shim / "sf"
    sf.write_text(f"#!/bin/sh\nexec {shlex.quote(sys.executable)} {shlex.quote(str(HERE / 'fake_sf.py'))} \"$@\"\n")
    sf.chmod(0o755)
    fake = {"FAKE_SF_STATE": str(folder / "state.json"), "FAKE_SF_LOG": str(folder / "calls.jsonl"),
            "FAKE_SF_ORGS": str(spec.get("orgs") or "de")}
    for environment in (env, os.environ):
        environment.update(PATH=f"{shim}{os.pathsep}{environment.get('PATH', '')}", **fake)
        if shutil.which("sf", path=environment["PATH"]) != str(sf):
            raise SystemExit(f"fake_sf: {sf} is not the first sf on PATH")
    return {"shim": str(sf), "log": fake["FAKE_SF_LOG"], "orgs": fake["FAKE_SF_ORGS"]}


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


def release_keepalive_owner(cli: Path, run_dir: str, env: dict) -> None:
    """Free the run's keepalive owner, as shiploop_keepalive.drive does after each session: the cleared session is gone,
    and until its claim goes stale (OWNER_STALE_SECONDS) the stop hook would let the fresh session stop as "another
    session owns this run". The plugin under test's own release, in the environment its hooks run in."""
    code = ("import sys; sys.path.insert(0, sys.argv[1]); import shiploop_keepalive as keepalive; "
            "keepalive.release_owner(keepalive.run_status(sys.argv[2])['run_dir'])")
    result = subprocess.run([sys.executable, "-c", code, str(Path(cli).parent), run_dir], env=env, capture_output=True,
                            text=True, check=False, timeout=60)
    if result.returncode != 0:
        raise SystemExit("the plugin under test could not release the run's keepalive owner: " + result.stderr.strip()[-300:])


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
          stop_after: str | None = None) -> dict:
    """One host session that the slice stop ends. Its status is ``slice-complete`` when the slice ended it, or when the
    session ended by itself with the slice already complete.

    With `clear_at` (clear.parse_spec) the session is also ended at the first position not yet cleared (status
    ``cleared``): the positions fire in order, and clear.json holds the ones that already did. The stop point is
    appended to clear.json and the caller continues in a fresh session. `told` is what that session's prompt named
    (sessions.jsonl)."""
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
        return stop_reached(state, stop_after) if stop_after else slice_complete(state)

    started: list = []
    events_path = out / "events.jsonl"

    def begin(line: int) -> None:
        started.append(sessionlog.start(out, kind="first" if first else "continued", reason="slice", host=host_name,
                                        model=model, events_line=line, told=told, resumed_session=resumed_session))

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
    elif process["status"] == "interrupted" or (process["status"] == "exited" and (
            stop_reached(read_state(run_dir), stop_after) if stop_after else slice_complete(read_state(run_dir)))):
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


def grade(out: Path, run_dir: Path, seeded: dict, case: dict, sessions: list[dict],
          stop_after: str | None = None) -> dict:
    state = read_state(run_dir) or {}
    item = case["work_item"]["id"]
    history = item_history(state, item)
    carried = any(row["stage"] == "carry-forward" and row["outcome"] == "done" for row in history)
    over = overshoot(state, item)
    worktree = run_dir.parent / "worktree"
    assembled = assembled_product(worktree, seeded["start_head"], case.get("expect_paths") or [])
    check_results = checks_on_candidate(worktree, out, case["checks"])
    if stop_after:
        # An experiment slice (--stop-after): the stop stage accepted and nothing after it; the product is recorded only.
        over = overshoot_after(state, stop_after)
        verdicts = {"process": sessions[-1]["status"] == "slice-complete",
                    "stopped": any(isinstance(row, dict) and row.get("stage") == stop_after and row.get("outcome") == "done"
                                   for row in state.get("history") or []),
                    "no_overshoot": not over}
    else:
        verdicts = {"process": sessions[-1]["status"] == "slice-complete", "inner_loop": carried, "no_overshoot": not over,
                    "assembled": assembled["pass"], "checks": all(c["pass"] for c in check_results)}
    probe = clear_facts(out)
    if probe:
        verdicts["no_redo"] = all(c["pass"] for c in probe)
    return {"pass": all(verdicts.values()), "verdicts": verdicts, "item": item, "item_history": history,
            "overshoot": over, "queue_growth": max(0, len(state.get("work_items") or []) - 1),
            "run_status": state.get("status"), "stage_at_stop": metrics.current_stage(state) if state else None,
            "assembled": assembled, "checks": check_results, "sessions": sessions, "clear": probe,
            "clear_unfired": unfired_clears(out, len(probe)), "stop_after": stop_after,
            "not_reached": "system tests, release and the report: a slice ends after the item's inner loop"}


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--case", help="a case from step_cases.json")
    p.add_argument("--regrade", type=Path, metavar="OUTPUT",
                   help="grade an earlier slice again from its files (no host starts), with the case it ran")
    p.add_argument("--host", choices=sorted(hosts.HOSTS), default=hosts.RUN_DEFAULT_HOST,
                   help=f"host for the slice (default: {hosts.RUN_DEFAULT_HOST})")
    p.add_argument("--backend", choices=("anthropic", "ollama"), default=None,
                   help="claude only: ollama (default, as for run.py: Claude Code on the local Ollama server's "
                        f"{hosts.OLLAMA_MODEL}) or anthropic, Claude's own models")
    p.add_argument("--model", help=f"default: gpt-6.1-terra (codex), {hosts.OLLAMA_MODEL} (claude), "
                                   "claude-sonnet-5-5 (claude --backend anthropic), grok-4.7 (grok)")
    p.add_argument("--effort", help="reasoning effort; default: xhigh (codex), host default (claude), medium (grok)")
    p.add_argument("--delegation", choices=("inline", "ask-agent"), default="inline",
                   help="inline (default): one session, every packet in the main context; ask-agent: native workers")
    p.add_argument("--plugin-dir", type=Path, help="a skill-craft plugin build to test (default: build this checkout)")
    p.add_argument("--output", type=Path, help="new directory for this attempt (default: under $TMPDIR)")
    p.add_argument("--timeout", type=int, default=None, help="seconds before the host is killed; default: none")
    p.add_argument("--max-turns", type=int, default=None,
                   help="a turn limit for the host session; default: none")
    p.add_argument("--max-budget-usd", type=float, default=None,
                   help="claude --backend anthropic only, default none; grok and codex have no spend cap")
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
    p.add_argument("--seed-at", choices=SEED_POINTS, default=SEED_AT,
                   help="the stage the host starts at (default step-plan); the earlier stages are recorded from the case")
    p.add_argument("--stop-after", choices=stage_spec.STAGES, metavar="STAGE",
                   help="end the host once STAGE is accepted and the run moved past it, instead of after the item")
    p.add_argument("--planning-review", choices=stage_spec.PLANNING_REVIEW_MODES,
                   help="the run's planning review option (default: the engine's, stage); none starts no Improve child "
                        "after a planning stage (step-plan included) and names the build's Improve card for the rest")
    p.add_argument("--ref", help="build the plugin from this git ref (a read-only temporary worktree), not the working tree")
    p.add_argument("--overlay", type=Path, help="a prompt overlay (overlay.py) applied to the plugin build copy")
    p.add_argument("--seed-records", type=Path, metavar="JSON",
                   help="{stage: fields} merged over the case's seed_records for the stages the seed records (an arm's "
                        "own seeded facts, such as a summary the next packet quotes)")
    p.add_argument("--opening-note", type=Path, help="a text file appended to the opening prompt (the same in every arm)")
    p.add_argument("--quiet", action="store_true")
    for name in sorted(hosts.HOSTS):
        p.add_argument(f"--{name}-bin", default=name)
    return p


def finish(out: Path, run_dir: Path, seeded: dict, case: dict, sessions: list[dict], identity: dict, quiet: bool,
           stop_after: str | None = None) -> int:
    result = {**identity, "output": str(out), "run_dir": str(run_dir), "worktree": str(run_dir.parent / "worktree"),
              **grade(out, run_dir, seeded, case, sessions, stop_after)}
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
    case = load_step_case(invocation["case"])
    fake_sf(case, out, {})  # the case checks rerun here; never against a real org
    return finish(out, Path(seeded["run_dir"]), seeded, case, earlier["sessions"],
                  {**identity, "regraded": True}, quiet, invocation.get("stop_after"))


def main(argv: list[str] | None = None) -> int:
    """Run one slice (or --regrade one) and return the exit code; see _main."""
    held: list = []  # the case lock, taken inside once the output folder is known, and released here whatever happens
    try:
        return _main(argv, held)
    finally:
        for handle in held:
            handle.close()


def _main(argv: list[str] | None, held: list) -> int:
    args = parser().parse_args(argv)
    if args.regrade:
        return regrade(args.regrade, args.quiet)
    if not args.case:
        raise SystemExit("--case is required (or --regrade OUTPUT)")
    case = load_step_case(args.case)
    clear_at = clear.parse_spec(args.clear_at)  # a malformed position ends the command before anything is built
    records = merged_records(case, args.seed_records)
    if why := seed_gap(args.seed_at, records):
        raise SystemExit(why)
    run.install_termination_handlers()
    out = run.new_output_dir(args.output, f"slice-{args.case}")
    # This harness is alive while main runs, as run.py's is: a launch elsewhere reads the lock (lifecycle.orphans, the
    # stale-listener check) to tell this slice's host and servers from a killed harness's leftovers. Without it a live
    # slice reads as an orphan and refuses every run.py launch under the same runs root.
    if (lock := listeners.hold_case(out)) is not None:
        held.append(lock)
    work = out / "work"
    work.mkdir()
    # A step slice is an E2E run: with no --backend it takes run.py's default (hosts.RUN_DEFAULT_BACKEND).
    host = hosts.host(args.host, getattr(args, f"{args.host}_bin"),
                      args.backend or hosts.RUN_DEFAULT_BACKEND.get(args.host))
    model, effort = args.model or host.model, args.effort or host.effort
    host.model = model  # the model the host's environment routes to (the Claude host on Ollama names it there)
    backend = getattr(host, "backend", None)
    if backend == "ollama":
        if args.max_budget_usd:
            raise SystemExit("--max-budget-usd is not with --backend ollama: Claude Code prices the tokens at Anthropic's "
                             "rates, so the cap would stop the slice on a figure that is not its cost. Nothing was started.")
        if why := hosts.ollama_ready(model):
            raise SystemExit(f"--backend ollama: {why}. Nothing was started.")
    env = host.env(out / "home")
    if args.plugin_dir and (args.ref or args.overlay):
        raise SystemExit("--ref and --overlay build their own plugin; they do not take --plugin-dir")
    plugin_dir = (args.plugin_dir.expanduser().resolve() if args.plugin_dir
                  else overlays.build_ref(args.ref, out) if args.ref else run.build_candidate(out))
    applied = overlays.apply_to_plugin(args.overlay.resolve(), plugin_dir) if args.overlay else None
    run.require_improve_card(args.planning_review, plugin_dir)
    plugin = host.install_plugin(env, plugin_dir)
    cli = run.run_cli(host.name, out, plugin_dir)
    seeded = run.seed_run(cli, work, out, case["prompt"], args.seed_at, fixture=FIXTURES / case["fixture"],
                          work_item=case["work_item"], delegation=args.delegation, checks=case["checks"],
                          home=not args.seed_without_home, records=records,
                          planning_review=args.planning_review,
                          improve_skill=str(run.improve_card(plugin_dir)) if args.planning_review == "none" else "")
    target = seed_state(case, out, env)
    shim = fake_sf(case, out, env)
    run_dir = Path(seeded["run_dir"])
    note = args.opening_note.read_text().strip() if args.opening_note else ""
    opening = host.invoke(host.skill, run.seed_prompt(cli, str(run_dir), case["prompt"], args.delegation, args.seed_at)
                          + (f"\n\n{note}" if note else ""))
    common = dict(cwd=work, model=model, effort=effort, permission_mode=args.permission_mode, max_turns=args.max_turns,
                  max_budget_usd=args.max_budget_usd, plugin_dir=None if host.marketplace else plugin_dir)
    invocation = {"case": args.case, "kind": "step-slice", "host": host.name, "backend": backend, "model": model, "effort": effort,
                  "delegation": args.delegation, "plugin_dir": str(plugin_dir), "plugin": plugin,
                  "versions": run.installed_versions(plugin_dir), "local_head": run.git("rev-parse", "HEAD").strip(),
                  "seeded": seeded, "checks": case["checks"], "expect_paths": case.get("expect_paths"),
                  "clear_at": [clear.label(spec) for spec in clear_at], "resume_prompt": args.resume_prompt,
                  "seed_at": args.seed_at, "stop_after": args.stop_after, "ref": args.ref, "overlay": applied,
                  "opening_note": note or None, "seed_state": target, "fake_sf": shim,
                  "planning_review": args.planning_review or stage_spec.DEFAULT_PLANNING_REVIEW}
    (out / "invocation.json").write_text(json.dumps(invocation, indent=2) + "\n")
    (out / "prompt.txt").write_text(case["prompt"] + "\n")
    if not args.quiet:
        print(f"slice {args.case} host={host.name}" + (f" backend={backend}" if backend else "")
              + f" model={model} delegation={args.delegation}\n  output {out}\n"
              f"  seeded {', '.join(seeded['skipped'])}; the host starts at {seeded['stage']}", flush=True)

    if host.name != "claude" and any(spec["inside"] for spec in clear_at) and not args.quiet:
        print("note: an :inside position needs Claude's stream (clear.py); on this host it is recorded as requested and "
              "will not fire", flush=True)
    deadline = time.monotonic() + (args.timeout or float("inf"))  # active time, as in run.py: sleep spends none of it
    session_args = dict(work=work, out=out, env=env, run_dir=run_dir, watch=not args.quiet,
                        translate=host.translator(), host_name=host.name, model=model, clear_at=clear_at,
                        stop_after=args.stop_after)
    process = drive(host.argv(prompt=opening, prompt_file=out / "host-prompt.txt", **common),
                    timeout=args.timeout or float("inf"), **session_args)
    sessions = [process]
    resumes = 0
    while True:
        if process["status"] == "cleared":
            # A fresh session: no --resume, so the model holds nothing but what this prompt says (--resume-prompt).
            number = len(clear_records(out))
            if not args.quiet:
                print(f"cleared at {clear_records(out)[-1]['stopped']}; continuing in a fresh session "
                      f"(prompt {args.resume_prompt})", flush=True)
            release_keepalive_owner(cli, str(run_dir), env)
            prompt, told = continue_prompt(args.resume_prompt, str(run_dir), cli)
            process = drive(host.argv(prompt=prompt, prompt_file=out / f"resume-after-clear-{number}.txt", **common),
                            timeout=max(60, deadline - time.monotonic()), first=False, told=told, **session_args)
        elif (host.resumable and process["status"] == "exited" and (args.max_resumes is None or resumes < args.max_resumes)
              and (read_state(run_dir) or {}).get("status") == "active" and deadline - time.monotonic() > 60
              and not (args.stop_after and stop_reached(read_state(run_dir), args.stop_after))):
            # A headless Grok or Codex session ends whenever the model ends its turn; continue it while the slice is
            # unfinished (the clears still to come stay in force). A clear is not a resume: it does not use the budget.
            session_id = run.last_session_id(out / "events.jsonl")
            if not session_id:
                break
            resumes += 1
            argv = host.argv(prompt=run.resume_prompt(str(run_dir), cli), prompt_file=out / f"resume-{len(sessions)}.txt",
                             resume=session_id, **common)
            process = drive(argv, timeout=deadline - time.monotonic(), first=False, resumed_session=session_id,
                            told=run.resume_told(str(run_dir), cli), **session_args)
        else:
            break
        sessions.append(process)

    run.write_transcript(out / "events.jsonl", out / "transcript.md")
    return finish(out, run_dir, seeded, case, sessions,
                  {"case": args.case, "host": host.name, "model": model, "delegation": args.delegation}, args.quiet,
                  args.stop_after)

if __name__ == "__main__":
    raise SystemExit(main())
