#!/usr/bin/env python3
"""launch.py: one trial of the parallel-plan-execution probes.

Apparatus for docs/experiments/parallel-plan-execution-20261114 (see its README, "Subjects and conditions"). It builds
the host's argv and environment through the E2E harness's ``hosts.host(name)`` (read-only use; nothing in
test/shiploop_e2e changes), runs the packet in a throwaway working directory, and records what ``hosts.run_agent``
does not keep: a receive timestamp on every raw event line. Then it scores the trial.

  launch.py --host claude|codex|grok --plan fan4 --arm A2 --out TRIAL_DIR [--variant N|H] [--timeout 900]
            [--budget 6] [--model M] [--effort E] [--dry-run]

TRIAL_DIR must not exist. The trial folder holds work/ (kit, plan, run/ with the ledger), home/ (a throwaway profile for
Grok and Codex), packet.md, events.raw.jsonl, stderr.txt, invocation.json, then score.json, timeline.txt, gantt.txt.
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
import hosts  # noqa: E402  (the E2E harness's host adapters, used read-only)
import score  # noqa: E402

ARMS = ("A0", "A1", "A2", "A3")


def packet_text(arm: str, plan: dict, kit: Path, run_dir: Path, plan_path: Path, variant: str, host: str) -> str:
    failure = (HERE / "packets" / "failure-rule.txt").read_text().rstrip("\n") if any(s["kit"].get("fail") for s in plan["steps"]) else ""
    text = string.Template((HERE / "packets" / f"{arm}.md").read_text()).substitute(
        kit=kit, run_dir=run_dir, plan_path=plan_path, failure_rule=failure)
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
    began = time.time()
    with events.open("w") as out, stderr.open("wb") as err:
        proc = subprocess.Popen(argv, cwd=cwd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=err, env=env,
                                start_new_session=True)

        def pump():
            for raw in proc.stdout:
                text = raw.decode("utf-8", "replace").rstrip("\n")
                rec: dict = {"recv": round(time.time(), 3)}
                try:
                    rec["ev"] = json.loads(text)
                except ValueError:
                    rec["raw"] = text
                out.write(json.dumps(rec, separators=(",", ":")) + "\n")
                out.flush()
        reader = threading.Thread(target=pump, daemon=True)
        reader.start()
        try:
            proc.wait(timeout=timeout)
            status = "exited" if proc.returncode == 0 else "failed"
        except subprocess.TimeoutExpired:
            end_group(proc.pid)
            proc.wait()
            status = "timeout"
        reader.join(timeout=10)
        proc.stdout.close()
    ended = time.time()
    return {"status": status, "returncode": proc.returncode, "started": round(began, 3), "ended": round(ended, 3),
            "elapsed_s": round(ended - began, 1)}


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
    parser.add_argument("--enable-feature", action="append", default=[], metavar="NAME",
                        help="Codex only: pass --enable NAME (README Amendment A1: multi_agent_v2 is off in the harness's "
                             "throwaway profile and on in the owner's own)")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    if args.enable_feature and args.host != "codex":
        parser.error("--enable-feature applies to the codex host only")

    trial = Path(args.out).resolve()
    work, run_dir = trial / "work", trial / "work" / "run"
    plan_src = HERE / "plans" / f"{args.plan}.json"
    plan = json.loads(plan_src.read_text())
    kit = work / "dagkit.py"
    host = hosts.host(args.host)
    model = args.model or host.model
    effort = args.effort if args.effort is not None else host.effort
    packet = packet_text(args.arm, plan, kit, run_dir, work / "plan.json", args.variant, args.host)
    allow = (f"Bash(python3 {kit}:*)",)
    prompt_file = (trial.parent / ".dry-run-prompt.txt") if args.dry_run else trial / "prompt.txt"
    cmd = host.argv(prompt=packet, prompt_file=prompt_file, cwd=work, model=model, effort=effort, permission_mode="auto",
                    max_turns=None, max_budget_usd=args.budget if args.host == "claude" else None, allow=allow)
    if args.enable_feature:  # Codex's prompt is its last argument; options go before it
        cmd = cmd[:-1] + [part for name in args.enable_feature for part in ("--enable", name)] + cmd[-1:]
    if args.dry_run:
        shown = ["<packet>" if part == packet else part for part in cmd]
        print(f"host={args.host} model={model} effort={effort} plan={args.plan} arm={args.arm} variant={args.variant}\n"
              f"argv: {shown}\n--- packet\n{packet}")
        return 0

    trial.mkdir(parents=True, exist_ok=False)
    work.mkdir()
    shutil.copy(HERE / "dagkit.py", kit)
    shutil.copy(plan_src, work / "plan.json")
    subprocess.run([sys.executable, str(kit), "init", "--plan", str(work / "plan.json"), "--run", str(run_dir)], check=True,
                   stdout=subprocess.DEVNULL)
    (trial / "packet.md").write_text(packet)
    home = trial / "home"
    home.mkdir()
    env = host.env(home)
    version, why = hosts.probe_version(host.binary, env)
    result = run_host(cmd, work, env, trial / "events.raw.jsonl", trial / "stderr.txt", args.timeout)
    inv = {"host": args.host, "binary": host.binary, "version": version or why, "model": model, "effort": effort,
           "permission_mode": "auto", "allow": list(allow), "plan": args.plan, "arm": args.arm, "variant": args.variant,
           "enabled_features": args.enable_feature,
           "timeout_s": args.timeout, "budget_usd": args.budget if args.host == "claude" else None,
           "argv": ["<packet.md>" if part == packet else part for part in cmd], "cwd": str(work),
           "loadavg": [round(x, 2) for x in os.getloadavg()], "kit_sha256": score.dagkit._sha(kit.read_text()),
           "packet_sha256": score.dagkit._sha(packet), "machine": os.uname().sysname + " " + os.uname().release, **result}
    (trial / "invocation.json").write_text(json.dumps(inv, indent=1) + "\n")
    measures = score.score_trial(trial)
    print(score.summary_line(trial, measures))
    return 0


if __name__ == "__main__":
    sys.exit(main())
