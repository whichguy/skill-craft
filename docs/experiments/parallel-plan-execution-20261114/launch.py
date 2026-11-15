#!/usr/bin/env python3
"""launch.py: one trial of the parallel-plan-execution probes.

Apparatus for docs/experiments/parallel-plan-execution-20261114 (see its README, "Subjects and conditions" and Amendments
A2 to A4). It builds the host's argv and environment through the E2E harness's ``hosts.host(name)`` (read-only use; nothing
in test/shiploop_e2e changes), runs the packet in a throwaway working directory, and records what ``hosts.run_agent`` does
not keep: a receive timestamp on every raw event line. It launches one host and observes it; it never dispatches a step.
Then it scores the trial.

  launch.py --host claude|codex|grok --plan fan4 --arm A2 --out TRIAL_DIR [--variant N|H] [--timeout 900]
            [--budget 6] [--model M] [--effort E] [--capacity N] [--enable-feature NAME] [--binary EXE] [--dry-run]

TRIAL_DIR must not exist. The trial folder holds work/ (kit, plan, run/ with the ledger), home/ (a throwaway profile for
Grok and Codex), packet.md, events.raw.jsonl, stderr.txt, invocation.json (written before the launch and completed after),
then score.json, timeline.txt, gantt.txt.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import signal
import string
import subprocess
import sys
import threading
import time

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "test" / "shiploop_e2e"))
sys.path.insert(0, str(HERE))
import evidence  # noqa: E402
import hosts  # noqa: E402  (the E2E harness's host adapters, used read-only)
import score  # noqa: E402
import writefix  # noqa: E402

ARMS = ("A0", "A0p", "A1", "A2", "A3", "A3s")   # a task plan (real agent work) takes A0, A0p, A3 and A3s
PACKET_FILE = {"A3s": "A3"}   # A3s is A3 at capacity one: the matched serial control (README, Amendment A3)


def is_task_plan(plan: dict) -> bool:
    return plan["steps"][0].get("kit", {}).get("mode") == "task"


# Benign analysis commands pre-allowed for the hosts that take allow rules, so the permission classifier is not a hidden
# variable in a task trial (Codex runs with approvals off).
TASK_ALLOW = tuple(f"Bash({c}:*)" for c in ("python3", "grep", "awk", "sort", "uniq", "wc", "cat", "head", "tail", "cut", "sed", "ls", "tr"))
WRITE_ALLOW = ("Edit", "Write", "Read")   # a write plan's workers write files inside the trial's work directory (README Amendment A10)


def packet_text(arm: str, plan: dict, kit: Path, run_dir: Path, plan_path: Path, variant: str, host: str, capacity: int) -> str:
    failure = (HERE / "packets" / "failure-rule.txt").read_text().rstrip("\n") if any(s.get("kit", {}).get("fail") for s in plan["steps"]) else ""
    name = PACKET_FILE.get(arm, arm)
    text = string.Template((HERE / "packets" / (f"task-{name}.md" if is_task_plan(plan) else f"{name}.md")).read_text()).substitute(
        kit=kit, run_dir=run_dir, plan_path=plan_path, failure_rule=failure, capacity=capacity, last_step=plan["steps"][-1]["id"])
    if variant == "H":
        text += "\n" + (HERE / "packets" / f"H-{host}.txt").read_text().strip() + "\n"
    return text


def end_group(pid: int) -> None:
    """Stop the process group this launcher started (start_new_session made its group id the pid), and only that."""
    for sig, wait in ((signal.SIGTERM, 5), (signal.SIGKILL, 0)):
        try:
            os.killpg(pid, sig)
        except ProcessLookupError:
            return
        time.sleep(wait)


def run_host(argv: list, cwd: Path, env: dict, events: Path, stderr: Path, timeout: int) -> dict:
    began, mono = time.time(), time.monotonic()
    with events.open("w") as out, stderr.open("wb") as err:
        proc = subprocess.Popen(argv, cwd=cwd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=err, env=env,
                                start_new_session=True)
        stream = {"reader_error": None}

        def pump():
            try:
                for raw in proc.stdout:
                    text = raw.decode("utf-8", "replace").rstrip("\n")
                    rec: dict = {"recv": round(time.time(), 3)}
                    try:
                        rec["ev"] = json.loads(text)
                    except ValueError:
                        rec["raw"] = text
                    out.write(json.dumps(rec, separators=(",", ":")) + "\n")
                    out.flush()
            except Exception as error:  # noqa: BLE001  (recorded, not hidden: an incomplete stream is evidence)
                stream["reader_error"] = f"{type(error).__name__}: {error}"
        reader = threading.Thread(target=pump, daemon=True)
        reader.start()
        try:
            proc.wait(timeout=timeout)
            status = "exited" if proc.returncode == 0 else "failed"
        except subprocess.TimeoutExpired:
            end_group(proc.pid)
            proc.wait()
            status = "timeout"
        exited = time.time()   # the process's own exit, before the reader is joined
        reader.join(timeout=10)
        proc.stdout.close()
    return {"status": status, "returncode": proc.returncode, "started": round(began, 3), "ended": round(exited, 3),
            "elapsed_s": round(exited - began, 1), "elapsed_monotonic_s": round(time.monotonic() - mono, 3),
            "reader_joined": not reader.is_alive(), "reader_error": stream["reader_error"]}


def lingering(kit: Path) -> list:
    """Processes still running this trial's kit (matched on the trial's own kit path), excluding this launcher's ancestors."""
    ps = subprocess.run(["ps", "-axww", "-o", "pid=,ppid=,command="], capture_output=True, text=True).stdout.splitlines()
    parent: dict = {}
    rows = []
    for line in ps:
        parts = line.split(None, 2)
        if len(parts) == 3 and parts[0].isdigit() and parts[1].isdigit():
            parent[int(parts[0])] = int(parts[1])
            rows.append((int(parts[0]), parts[2]))
    safe, pid = set(), os.getpid()
    while pid and pid not in safe:
        safe.add(pid)
        pid = parent.get(pid, 0)
    return [{"pid": p, "command": c[:200]} for p, c in rows if str(kit) in c and p not in safe]


def settle(kit: Path, wait_s: float) -> tuple[list, list]:
    """(what was still running after the host exited, the pids this launcher then stopped). Waits up to wait_s for the
    kit's own sleeps to end; only processes carrying this trial's kit path are ever signalled."""
    first = lingering(kit)
    deadline = time.time() + wait_s
    now = first
    while now and time.time() < deadline:
        time.sleep(2)
        now = lingering(kit)
    stopped = []
    for item in now:
        try:
            os.kill(item["pid"], signal.SIGTERM)
            stopped.append(item["pid"])
        except ProcessLookupError:
            pass
    return first, stopped


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--host", required=True, choices=sorted(hosts.HOSTS))
    parser.add_argument("--plan", required=True)
    parser.add_argument("--arm", required=True, choices=ARMS)
    parser.add_argument("--variant", default="N", choices=("N", "H"))
    parser.add_argument("--out", required=True)
    parser.add_argument("--timeout", type=int, default=900)
    parser.add_argument("--budget", type=float, default=6.0, help="Claude's per-trial dollar ceiling (a safety net)")
    parser.add_argument("--model")
    parser.add_argument("--effort")
    parser.add_argument("--capacity", type=int, help="A3's claim capacity (default: the number of steps; A3s is always 1)")
    parser.add_argument("--enable-feature", action="append", default=[], metavar="NAME",
                        help="Codex only: pass --enable NAME (README Amendment A1: multi_agent_v2 is off in the harness's "
                             "throwaway profile and on in the owner's own)")
    parser.add_argument("--settle", type=float, default=0.0, help="task plans: seconds of slow verification inside every task (the work-length dial)")
    parser.add_argument("--workspace", choices=("shared", "isolated"), default="shared",
                        help="write plans: every task edits the one checkout (shared) or each attempt gets its own git worktree that the script merges (isolated)")
    parser.add_argument("--seed", type=int, default=20261114, help="task plans: the seed of the generated log files")
    parser.add_argument("--lines", type=int, default=400, help="task plans: events per generated log")
    parser.add_argument("--binary", help="run this executable in place of the host's own (calibrate.py uses fakehost.py)")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    if args.enable_feature and args.host != "codex":
        parser.error("--enable-feature applies to the codex host only")

    trial = Path(args.out).resolve()
    work, run_dir = trial / "work", trial / "work" / "run"
    plan_src = HERE / "plans" / f"{args.plan}.json"
    plan = json.loads(plan_src.read_text())
    kit = work / "dagkit.py"
    host = hosts.host(args.host, args.binary)
    model = args.model or host.model
    effort = args.effort if args.effort is not None else host.effort
    if is_task_plan(plan) and args.arm not in ("A0", "A0p", "A3", "A3s"):
        parser.error("a task plan runs under A0, A0p, A3 or A3s")
    write = plan.get("fixture") == "write"
    capacity = 1 if args.arm == "A3s" else (args.capacity or len(plan["steps"]))
    packet = packet_text(args.arm, plan, kit, run_dir, work / "plan.json", args.variant, args.host, capacity)
    allow = (f"Bash(python3 {kit}:*)",) + (TASK_ALLOW if is_task_plan(plan) else ()) + (WRITE_ALLOW if write else ())

    def build(prompt_file: Path) -> list:
        cmd = host.argv(prompt=packet, prompt_file=prompt_file, cwd=work, model=model, effort=effort, permission_mode="auto",
                        max_turns=None, max_budget_usd=args.budget if args.host == "claude" else None, allow=allow)
        if args.enable_feature:  # Codex's prompt is its last argument; options go before it
            cmd = cmd[:-1] + [part for name in args.enable_feature for part in ("--enable", name)] + cmd[-1:]
        return cmd
    if args.dry_run:
        shown = ["<packet>" if part == packet else part for part in build(trial.parent / ".dry-run-prompt.txt")]
        print(f"host={args.host} model={model} effort={effort} plan={args.plan} arm={args.arm} variant={args.variant} capacity={capacity}\n"
              f"argv: {shown}\n--- packet\n{packet}")
        return 0

    # The owned directories exist before any adapter writes a file into them (Codex and Grok write the prompt file).
    trial.mkdir(parents=True, exist_ok=False)
    work.mkdir()
    (trial / "home").mkdir()
    clean_env = {k: v for k, v in os.environ.items() if k != "PPE_TIME_SCALE"}   # a live trial is never scaled
    shutil.copy(HERE / "dagkit.py", kit)
    shutil.copy(plan_src, work / "plan.json")
    init = [sys.executable, str(kit), "init", "--plan", str(work / "plan.json"), "--run", str(run_dir), "--settle", str(args.settle)]
    if write:   # the base commit every worker starts from; the hidden oracle sits beside work/, read only by the scorer
        writefix.make_repo(work / "repo")
        (trial / "oracle").mkdir()
        (trial / "oracle" / "hidden_tests.py").write_text(writefix.ORACLE)
        init += ["--repo", str(work / "repo"), "--workspace", args.workspace]
    subprocess.run(init, check=True, stdout=subprocess.DEVNULL, env=clean_env)
    (trial / "packet.md").write_text(packet)
    if is_task_plan(plan) and not write:   # the agents' evidence sits in work/; the oracle sits beside it, read only by the scorer
        files, expected = evidence.generate(args.seed, args.lines)
        (work / "evidence").mkdir()
        for name, text in files.items():
            (work / "evidence" / name).write_text(text)
        (trial / "oracle.json").write_text(json.dumps(expected, indent=1) + "\n")
    env = host.env(trial / "home")
    env.pop("PPE_TIME_SCALE", None)
    version, why = hosts.probe_version(host.binary, env)
    cmd = build(trial / "prompt.txt")
    inv = {"host": args.host, "binary": host.binary, "version": version or why, "model": model, "effort": effort,
           "permission_mode": "auto", "allow": list(allow), "plan": args.plan, "arm": args.arm, "variant": args.variant,
           "capacity": capacity, "enabled_features": args.enable_feature, "timeout_s": args.timeout,
           "task_plan": is_task_plan(plan), "settle_s": args.settle, "workspace": args.workspace if write else None,
           "seed": args.seed if is_task_plan(plan) and not write else None,
           "lines": args.lines if is_task_plan(plan) and not write else None,
           "budget_usd": args.budget if args.host == "claude" else None,
           "argv": ["<packet.md>" if part == packet else part for part in cmd], "cwd": str(work),
           "loadavg": [round(x, 2) for x in os.getloadavg()], "kit_sha256": score.dagkit._sha(kit.read_text()),
           "packet_sha256": score.dagkit._sha(packet), "machine": os.uname().sysname + " " + os.uname().release,
           "status": "starting", "started": round(time.time(), 3)}
    (trial / "invocation.json").write_text(json.dumps(inv, indent=1) + "\n")   # identity first: evidence survives a crash
    try:
        inv.update(run_host(cmd, work, env, trial / "events.raw.jsonl", trial / "stderr.txt", args.timeout))
    except BaseException as error:  # noqa: BLE001  (an interrupt or a bug is recorded, then re-raised)
        inv.update(status="interrupted" if isinstance(error, KeyboardInterrupt) else "error", ended=round(time.time(), 3),
                   error=f"{type(error).__name__}: {error}")
        raise
    finally:
        longest = max([s.get("kit", {}).get("seconds", 0) for s in plan["steps"]] + [60])
        first, stopped = settle(kit, min(longest + 10, 120)) if inv.get("status") != "starting" else ([], [])
        inv.update(lingering_after_exit=first, orphans_terminated=stopped)
        (trial / "invocation.json").write_text(json.dumps(inv, indent=1) + "\n")
    measures = score.score_trial(trial)
    print(score.summary_line(trial, measures))
    return 0


if __name__ == "__main__":
    sys.exit(main())
