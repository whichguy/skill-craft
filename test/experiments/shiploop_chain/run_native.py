#!/usr/bin/env python3
"""Opt-in one-command Grok qualification; no launcher enters the skill package.

The host creates real native agents. This outer experiment retains the host
trace and independently reruns final verification. Its caller workspaces are
fixture-emulated with ordinary Git before host execution, so it does not prove
prompt-driven Ask-Agent worktree creation. It never supplies a fake agent or
treats model prose as a passing Git/code result.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import time

from trace import TraceError, evaluate_host_trace, host_terminal

ROOT = Path(__file__).resolve().parents[3]
PILOT = Path(__file__).resolve().with_name("native_pilot.py")


def json_command(argv):
    result = subprocess.run(argv, text=True, capture_output=True, timeout=120)
    if result.returncode:
        raise RuntimeError(result.stderr or result.stdout)
    return json.loads(result.stdout)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def capture_host_stream(proc: subprocess.Popen[str], raw_path: Path, events_path: Path,
                        started: float) -> tuple[threading.Thread, list[str]]:
    """Retain raw Grok JSONL and a receipt-timestamped observer copy."""
    errors: list[str] = []

    def copy() -> None:
        try:
            if proc.stdout is None:
                raise RuntimeError("native host has no stdout pipe")
            with raw_path.open("x", encoding="utf-8") as raw, events_path.open("x", encoding="utf-8") as events:
                for line in proc.stdout:
                    raw.write(line)
                    raw.flush()
                    body = line.rstrip("\r\n")
                    try:
                        payload = json.loads(body)
                    except json.JSONDecodeError:
                        payload = {"type": "unparsed", "line": body}
                    envelope = {
                        "received_at": utc_now(),
                        "monotonic_ms": round((time.monotonic() - started) * 1000, 3),
                        "payload": payload,
                    }
                    events.write(json.dumps(envelope, sort_keys=True) + "\n")
                    events.flush()
        except (OSError, RuntimeError) as exc:
            errors.append(str(exc))

    reader = threading.Thread(target=copy, name="shiploop-native-host-capture", daemon=True)
    reader.start()
    return reader, errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="new directory; retained on both success and failure")
    parser.add_argument("--grok", default="grok")
    parser.add_argument("--ask-agent-skill", type=Path, default=ROOT / "test/fixtures/ask-agent-v04/SKILL.md")
    parser.add_argument("--dispatcher-skill", type=Path, default=ROOT / "test/fixtures/plan-dispatcher-v3/SKILL.md")
    parser.add_argument("--timeout", type=int, default=1800)
    args = parser.parse_args()
    executable = shutil.which(args.grok)
    if executable is None:
        parser.error("Grok is required for this opt-in native test; use the hermetic lifecycle test for offline verification")
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    if args.output:
        output = args.output.expanduser().resolve()
        if output.exists():
            parser.error("--output must be a new directory")
        output.mkdir(parents=True)
    else:
        output = Path(tempfile.mkdtemp(prefix="shiploop-native-chain-")).resolve()
    pilot_dir = output / "pilot"
    record = {
        "schema": "shiploop-native-chain-run/v1",
        "host": "grok",
        "output": str(output),
        "native_trace_review_required": True,
        "coverage": {
            "workspace_creation": "fixture_emulation",
            "prompt_driven_ask_agent_workspace_creation": "not_qualified",
            "bridge_adoption_native_execution_merge_cleanup": "qualified_only_if_all_gates_pass",
        },
        "passed": False,
    }
    started = time.monotonic()
    try:
        prepared = json_command([sys.executable, "-B", str(PILOT), "prepare", "--pilot-dir", str(pilot_dir),
            "--source-root", str(ROOT), "--dispatcher-skill", str(args.dispatcher_skill.resolve()),
            "--ask-agent-skill", str(args.ask_agent_skill.resolve())])
        (output / "prepare.json").write_text(json.dumps(prepared, indent=2) + "\n")
        context = json.loads((pilot_dir / "context.json").read_text())
        feature = Path(context["fixture"]["initiating_feature"])
        prompt = f"""Execute this bounded native Ask-Agent chain qualification to completion.
Read the selected Ask-Agent skill {args.ask_agent_skill.resolve()} and its Git reference,
and the driver reference {PILOT.with_name('README.md')}. Use their current contracts.
The initial ShipLoop navigation/review setup is explicitly synthetic; all code work,
native agent execution, independent checks, merges and cleanup must be real.
Operate only in the disposable fixture {pilot_dir} and its registered worktrees.
Do not change the skill source, oracle, graph, frozen contract or test driver.
Do not push, install anything, or access credentials. No model/agent subprocesses:
use this Grok session's native fresh agent tools for workers, with no inherited
conversation and normal available tools. The fixture's start helper has already
prepared each caller workspace with ordinary Git to emulate the Ask-Agent
caller-worktree contract. Do not create or prepare worker worktrees yourself;
begin by using the exact workspace supplied by start. ShipLoop only adopts that
workspace. This run does not qualify prompt-driven Ask-Agent workspace creation.

Driver prefix: {sys.executable} -B {PILOT}
Every driver operation needs --pilot-dir {pilot_dir}. Execute parent driver calls
serially and wait for each command to finish. Only workers execute concurrently.
Use --help for current argument spelling. The ready graph is A/B roots, C after A,
J after B+C. Claim A and B together. Call start for A and retain its assignment,
then call start for B and retain its assignment. Only after both start responses say
action=launch, issue the two fresh background native spawn_subagent calls together
in one adjacent tool-call batch before any collection, wait, or other parent work.
Give each returned inline_native_assignment as actual prompt text, not a prompt file.
Pass the exact assigned workspace as cwd, background=true, and no resume_from or
Grok-managed worktree isolation. Record each returned native subagent UUID by using
the native write tool to create exactly {pilot_dir}/<STEP>-handle.json with
{{"handle":"ACTUAL_UUID"}}, then call launched with that exact handle file. Do not
fabricate handles or worker results. The trace gate permits parent terminal commands
only for exact native_pilot.py driver actions; do not use a parent shell command,
write, or search_replace to create worker code or handoffs. Send both A/B before
collecting either. Retain observed native status and completion.
After A completes, import-handoff with --handoff-manifest WORKER_PATH and
--confirmed-stopped, then prepare-integration --confirmed-stopped, then done
--confirmed-stopped. These commands archive results, independently verify the
combination, merge into the invoking feature branch, accept and remove the worker.
Claim/start/dispatch C immediately after A acceptance, before settling B. Continue
B and C using the same collection/import/preparation/done path, one parent command
at a time. J is meaningful code generation using B and C; start it only after both
are accepted. Never ask a worker to merge into the invoking branch or delete its
worktree. Use normal native completion and collect all worker activity before
confirmed-stopped. Preserve failed work and report a real blocker; do not fake a pass.

Run show at meaningful transitions so observable parent status is saved. Complete
J and then run finish. Success requires all four source contributions in the
invoking feature, actual composed-code checks passing, the primary unchanged,
all agent worktrees removed, and required evidence archived. Return the finish
receipt path and any concrete limitations. Do not stop after planning.
"""
        record["command"] = [executable, "--cwd", str(feature), "--permission-mode", "auto",
                             "--output-format", "streaming-json", "--max-turns", "100", "-p", "<inline qualification prompt>"]
        record["prompt"] = prompt  # Diagnostic copy, never used as prompt-file transport.
        host_trace = output / "host.ndjson"
        host_events = output / "host-events.jsonl"
        with (output / "host.stderr").open("x", encoding="utf-8") as stderr:
            proc = subprocess.Popen([*record["command"][:-1], prompt], stdout=subprocess.PIPE, stderr=stderr,
                                    text=True, bufsize=1)
            record["pid"] = proc.pid
            reader, capture_errors = capture_host_stream(proc, host_trace, host_events, started)
            timed_out = False
            try:
                record["host_exit"] = proc.wait(timeout=args.timeout)
            except subprocess.TimeoutExpired:
                timed_out = True
                proc.terminate()
                try:
                    record["host_exit"] = proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    record["host_exit"] = proc.wait(timeout=10)
            reader.join(timeout=15)
            if reader.is_alive():
                capture_errors.append("host stdout capture did not finish after process exit")
            if capture_errors:
                raise RuntimeError("native host trace capture failed: " + "; ".join(capture_errors))
        try:
            terminal = host_terminal(host_trace)
        except TraceError as exc:
            terminal = {"complete": False, "error": str(exc)}
        record["host_terminal"] = terminal
        if timed_out:
            raise RuntimeError("native host timed out; fixture retained, native workers may need explicit reconciliation")
        if terminal.get("complete") is not True:
            raise RuntimeError(f"native host terminal state is {terminal.get('stop_reason')!r}; no completion claim")
        if record["host_exit"] != 0:
            raise RuntimeError(f"native host exited {record['host_exit']}; inspect retained trace")
        final_path = pilot_dir / "results/finish.json"
        if not final_path.is_file():
            raise RuntimeError("host returned without a final lifecycle receipt")
        final = json.loads(final_path.read_text())
        if final.get("finish", {}).get("complete") is not True:
            raise RuntimeError("chain did not report complete")
        # Rerun the driver's actual code/Git checks from a fresh process.
        audited = json_command([sys.executable, "-B", str(PILOT), "finish", "--pilot-dir", str(pilot_dir)])
        if audited.get("complete") is not True:
            raise RuntimeError("independent final verification did not establish completion")
        trace_result = evaluate_host_trace(host_trace, pilot_dir)
        trace_path = output / "native-trace-evaluation.json"
        trace_path.write_text(json.dumps(trace_result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        record["native_trace"] = {
            "path": str(trace_path), "passed": trace_result.get("passed"), "overlap": trace_result.get("overlap"),
        }
        if trace_result.get("passed") is not True:
            detail = "; ".join(trace_result.get("errors", [])[:4])
            raise RuntimeError("typed native trace evidence failed: " + (detail or "inspect retained evaluation"))
        record["final"] = audited
        record["passed"] = True
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        record["error"] = str(exc)
    finally:
        record["elapsed_seconds"] = round(time.monotonic() - started, 3)
        record["trace"] = str(output / "host.ndjson")
        record["trace_events"] = str(output / "host-events.jsonl")
        (output / "result.json").write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps({k: v for k, v in record.items() if k not in {"prompt", "command"}}, indent=2), flush=True)
    return 0 if record["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
