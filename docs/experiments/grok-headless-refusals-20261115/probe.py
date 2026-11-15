#!/usr/bin/env python3
"""Ask headless Grok, launched exactly as the E2E harness launches it, to run one shell command, and record Grok's own
permission decision for it.

Each case is one fresh Grok session in its own throwaway profile, built by ``hosts.GrokHost`` (the harness's own env and
argv: ``--permission-mode auto``, ``--verbatim``, streaming JSON), plus ``--debug-file`` so that Grok's permission manager
writes its decision source. The working directory is ``<case>/work`` (a git repository), and a ShipLoop-like run folder
sits beside it at ``<case>/.shiploop-runs/w/{run,worktree}``, outside the session's working directory, as in every E2E run.
No ShipLoop or keepalive is installed: the permission decision does not depend on them.

Usage: probe.py OUT_DIR CASES_JSON [--model M] [--effort E] [--mode MODE] [--repeat N]
CASES_JSON maps a case name to a command, or to {"command": ..., "layout": <the run's folder name>}; in a command {RUN},
{WT}, {WORK} and {ROOT} stand for the run folder, the worktree, the working directory and the case folder (a replayed E2E
command has its run root replaced by {ROOT}, so it keeps its exact shape). Writes OUT_DIR/results.jsonl: per session, the command asked for, the command the model ran, Grok's
permission events and the permission lines of its debug log.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "test" / "shiploop_e2e"))
import hosts  # noqa: E402  (the harness's own Grok launch)

PROMPT = ("This is a permission test. Use your terminal tool to run the shell command below exactly once, character for "
          "character, with no changes, as a single tool call. Do not run any other command and do not read any file. "
          "Then reply with the single word DONE.\n\n```sh\n{command}\n```\n")
DEBUG_KEEP = re.compile(r"permission|auto mode|classifier|floor|opaque|unverified|needs_user|request_floor|approval",
                        re.I)


def setup(case_dir: Path, layout: str = "w") -> dict:
    """``layout`` names the run's folder under .shiploop-runs, so a replayed E2E command keeps its exact paths."""
    work, run, worktree = (case_dir / "work", case_dir / ".shiploop-runs" / layout / "run",
                           case_dir / ".shiploop-runs" / layout / "worktree")
    for folder in (work, run / "inbox", run / "scratch", run / "notes", worktree):
        folder.mkdir(parents=True, exist_ok=True)
    (run / "inbox" / "a.md").write_text("result\n")
    (run / "scratch" / "probe.py").write_text("print('probe ok')\n")
    for repo in (work, worktree):
        (repo / "README.md").write_text("# probe\n")
        subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
        subprocess.run(["git", "add", "README.md"], cwd=repo, check=True)
        subprocess.run(["git", "-c", "user.name=p", "-c", "user.email=p@example.invalid", "-c", "maintenance.auto=false",
                        "commit", "-q", "-m", "base"], cwd=repo, check=True)
    return {"RUN": str(run), "WT": str(worktree), "WORK": str(work), "ROOT": str(case_dir)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("out", type=Path)
    parser.add_argument("cases", type=Path)
    parser.add_argument("--model", default=hosts.GROK_DEFAULT_MODEL)
    parser.add_argument("--effort", default="low")
    parser.add_argument("--mode", default="auto")
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--only", nargs="*")
    parser.add_argument("--rust-log", help="RUST_LOG for the session's debug file")
    parser.add_argument("--allow", action="append", default=[], help="a Grok --allow rule for every session")
    parser.add_argument("--preempt-hook", action="store_true",
                        help="install the harness's PreToolUse hook (hosts.GrokHost.preempt_install) in each profile; "
                             "the batches hook-1077 and task-hook-1077 ran the prototype committed in "
                             "ded345978767587e07c6fffe60aa3f7e785c668b instead")
    parser.add_argument("--prompt", choices=("exact", "task"), default="exact",
                        help="exact: run the command as given; task: the case text is a task for the model to do")
    args = parser.parse_args()
    cases = json.loads(args.cases.read_text())
    host = hosts.GrokHost()
    args.out.mkdir(parents=True, exist_ok=True)
    results = args.out / "results.jsonl"
    for name, spec in cases.items():
        template, layout = (spec, "w") if isinstance(spec, str) else (spec["command"], spec.get("layout", "w"))
        if args.only and name not in args.only:
            continue
        for attempt in range(1, args.repeat + 1):
            tags = ("-trace" if args.rust_log else "") + ("-allow" if args.allow else "") + (
                "-hook" if args.preempt_hook else "")
            case_dir = args.out / f"{name}-{args.mode}-{attempt}{tags}"
            if case_dir.exists():
                continue  # a case already run keeps its record
            paths = setup(case_dir, layout)
            command = template.replace("{RUN}", paths["RUN"]).replace("{WT}", paths["WT"]).replace(
                "{WORK}", paths["WORK"]).replace("{ROOT}", paths["ROOT"])
            env = host.env(case_dir / "home")
            if args.preempt_hook:
                host.preempt_install(env)  # the harness's own hook and registration (test/shiploop_e2e/grok_preempt.py)
            if args.rust_log:
                env["RUST_LOG"] = args.rust_log
            prompt = PROMPT.format(command=command) if args.prompt == "exact" else command
            argv = host.argv(prompt=prompt, prompt_file=case_dir / "prompt.txt",
                             cwd=Path(paths["WORK"]), model=args.model, effort=args.effort, permission_mode=args.mode,
                             max_turns=None, allow=tuple(args.allow)) + ["--debug-file", str(case_dir / "debug.log")]
            start = time.time()
            done = subprocess.run(argv, env=env, cwd=paths["WORK"], capture_output=True, text=True, timeout=600)
            (case_dir / "stdout.jsonl").write_text(done.stdout)
            (case_dir / "stderr.txt").write_text(done.stderr)
            ran, updates, end = [], [], None
            for line in done.stdout.splitlines():
                try:
                    event = json.loads(line)
                except ValueError:
                    continue
                if event.get("type") == "tool_call" and event.get("toolName") == "run_terminal_command":
                    ran.append((event.get("rawInput") or {}).get("command"))
                elif event.get("type") == "tool_call_update" and event.get("status") in ("failed", "completed"):
                    updates.append({"status": event.get("status"),
                                    "text": json.dumps(event.get("content"))[:300]})
                elif event.get("type") == "end":
                    end = event.get("stopReason")
            store = []
            for events in (case_dir / "home" / ".grok" / "sessions").glob("*/*/events.jsonl"):
                for line in events.read_text().splitlines():
                    event = json.loads(line)
                    if event.get("type") in ("permission_resolved", "turn_ended"):
                        store.append({k: v for k, v in event.items() if k != "ts"})
            debug = case_dir / "debug.log"
            debug_lines = [line[:600] for line in (debug.read_text(errors="replace").splitlines() if debug.is_file() else [])
                           if DEBUG_KEEP.search(line)]
            row = {"case": name, "attempt": attempt, "mode": args.mode, "model": args.model, "effort": args.effort,
                   "allow": args.allow, "preempt_hook": args.preempt_hook, "prompt_kind": args.prompt,
                   "asked": command, "ran": ran, "same": ran[:1] == [command], "updates": updates, "stop": end,
                   "store": store, "stderr": done.stderr.strip()[-600:], "debug": debug_lines,
                   "seconds": round(time.time() - start, 1)}
            with results.open("a") as handle:
                handle.write(json.dumps(row) + "\n")
            print(f"{name} #{attempt}: same={row['same']} stop={end} store={store} ({row['seconds']} s)", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
