#!/usr/bin/env python3
"""Explicit live Sonnet qualification; native Claude evidence remains host-specific."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent
CASES = {"commit3-a": (3, "commits"), "commit5-a": (5, "commits"),
         "ephemeral3-a": (3, "ephemeral")}


def accepted(record, verdict):
    return (len(record["commands"]) == 5
            and all(type(row.get("exit_code")) is int and row["exit_code"] == 0
                    for row in record["commands"])
            and isinstance(verdict, dict) and verdict.get("passed") is True
            and verdict.get("status") == "PASS")


def case_commands(run, workers, delivery, args):
    commands = [
        [sys.executable, "-B", str(ROOT / "fixture.py"), "prepare", "--run", str(run),
         "--workers", str(workers), "--mode", "parallel", "--hold-seconds", "0",
         "--delivery-mode", delivery, "--seed-compact-ignore-controls"],
        [sys.executable, "-B", str(ROOT / "claude_controller.py"), "prepare", "--run", str(run)],
        [sys.executable, "-B", str(ROOT / "claude_controller.py"), "launch", "--run", str(run),
         "--model", args.model, "--effort", args.effort],
        [sys.executable, "-B", str(ROOT / "controller.py"), "verify", "--run", str(run)],
        [sys.executable, "-B", str(run / "operator/claude_native_trace.py"), "--run", str(run)],
    ]
    if args.skill_root:
        commands[0] += ["--skill-root", str(args.skill_root.resolve())]
    if args.claude_binary:
        commands[2] += ["--claude-binary", args.claude_binary]
    return commands


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", choices=("harness", "delivery-qualification"), default="harness")
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--case", choices=tuple(CASES))
    parser.add_argument("--skill-root", type=Path)
    parser.add_argument("--claude-binary")
    parser.add_argument("--model", default="sonnet")
    parser.add_argument("--effort", default="medium")
    args = parser.parse_args(argv)
    if args.list:
        print(json.dumps({"harness": "offline Claude adapter checks", "delivery-qualification": CASES}))
        return 0
    if args.suite == "harness":
        return subprocess.run([sys.executable, "-B", "-m", "unittest", "discover", "-s",
                               str(ROOT), "-p", "test_claude_*.py", "-v"]).returncode
    if not args.live or args.output is None:
        parser.error("Live trials require --live and a new --output directory; see CONTRACT.md#claude-native-evidence")
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    selected = [args.case] if args.case else list(CASES)
    campaign = {"schema": "ask-agent-claude-suite/v1", "host": "claude-code",
                "suite": args.suite, "requested_model": args.model, "effort": args.effort,
                "started_epoch": time.time(), "status": "RUNNING",
                "cases": [{"name": name, "status": "NOT_RUN"} for name in selected]}
    campaign_path = output / "suite-result.json"
    def save():
        campaign_path.write_text(json.dumps(campaign, indent=2) + "\n")
    save()
    for index, name in enumerate(selected):
        workers, delivery = CASES[name]
        run = output / name
        record = {"name": name, "workers": workers, "delivery_mode": delivery,
                  "run": str(run), "status": "RUNNING", "commands": []}
        campaign["cases"][index] = record
        save()
        logs = output / "logs" / name
        logs.mkdir(parents=True)
        for phase, command in enumerate(case_commands(run, workers, delivery, args), 1):
            log_path = logs / f"{phase:02d}.log"
            print(json.dumps({"case": name, "phase": phase, "log": str(log_path)}), flush=True)
            began = time.monotonic()
            try:
                with log_path.open("x") as log:
                    result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT)
                receipt = {"argv": command, "exit_code": result.returncode}
            except (OSError, ValueError) as exc:
                receipt = {"argv": command, "exit_code": None, "error": f"{type(exc).__name__}: {exc}"}
            receipt.update(elapsed_s=time.monotonic() - began, evidence=str(log_path))
            record["commands"].append(receipt)
            save()
            if receipt["exit_code"] != 0 and (phase < 3 or
                    (phase == 3 and not (run / "operator/process-result.json").is_file())):
                break
        verdict_path = run / "operator/claude-native-audit.json"
        try:
            verdict = json.loads(verdict_path.read_text())
            record["status"] = "PASS" if accepted(record, verdict) else "FAIL"
        except (OSError, ValueError) as exc:
            record["status"] = "INCOMPLETE"
            record["error"] = f"Native verdict missing or invalid at {verdict_path}: {exc}"
        record["native_evidence"] = str(verdict_path)
        save()
        if record["status"] != "PASS":
            campaign.update(status=record["status"], finished_epoch=time.time())
            save()
            print(json.dumps({"error": "CLAUDE_CASE_NOT_ACCEPTED", "evidence": str(campaign_path),
                              "rationale": "CONTRACT.md#claude-native-evidence",
                              "recovery": "Preserve this attempt; diagnose logs and retry in a new output directory. Later cases remain NOT_RUN."}))
            return 1
    campaign.update(status="PASS", finished_epoch=time.time())
    save()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError) as exc:
        print(json.dumps({"error": "CLAUDE_SUITE_FAILED", "detail": str(exc),
                          "rationale": "CONTRACT.md#retry-safety",
                          "recovery": "Keep prior attempts and choose a new output directory."}), file=sys.stderr)
        sys.exit(2)
