#!/usr/bin/env python3
"""Run bounded generalized-discovery arms through frozen capability helpers."""
from __future__ import annotations

import argparse
import concurrent.futures
import datetime as dt
import fcntl
import hashlib
import importlib.util
import json
import os
import re
import select
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
from study_inputs import validate_study_inputs


LIMITS = {"seconds_per_arm": 480, "calls_per_arm": 32, "exploration_seconds": 360, "exploration_calls": 24}
ARM_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,80}$")


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def json_file(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain an object")
    return value


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def snapshot(root: Path) -> dict[str, str]:
    return {
        str(path.relative_to(root)): sha256(path)
        for path in sorted(root.rglob("*"))
        if path.is_file() and not path.is_symlink()
    }


def tree_delta(before: dict[str, str], after: dict[str, str]) -> dict[str, list[str]]:
    return {
        "created": sorted(set(after) - set(before)),
        "deleted": sorted(set(before) - set(after)),
        "modified": sorted(path for path in before.keys() & after.keys() if before[path] != after[path]),
    }


def load_frozen(study: Path) -> Any:
    frozen = study / "frozen"
    for name in ("run_trials.py", "runtime_validation.py", "gateway.py", "receipt_gateway.py"):
        if not (frozen / name).is_file():
            raise ValueError(f"frozen {name} is unavailable")
    name = "generalized_discovery_frozen_runner_" + hashlib.sha256(str(frozen).encode()).hexdigest()[:12]
    spec = importlib.util.spec_from_file_location(name, frozen / "run_trials.py")
    if spec is None or spec.loader is None:
        raise ValueError("frozen run_trials.py is unreadable")
    sys.path.insert(0, str(frozen))
    try:
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(str(frozen))
    module.HARD_CALL_LIMIT = LIMITS["calls_per_arm"]
    module.EXPLORATION_CALL_LIMIT = LIMITS["exploration_calls"]
    return module


def read_study(path: Path) -> tuple[Path, dict[str, Any]]:
    if not path.is_absolute():
        raise ValueError("--study must be an absolute path")
    study = path.resolve(strict=True)
    state = json_file(study / "study.json")
    if state.get("schema") != "generalized-discovery-study/1":
        raise ValueError("study.json has an unexpected schema")
    for key, expected in LIMITS.items():
        if state.get(key) != expected:
            raise ValueError(f"study.json must pin {key}={expected}")
    for key in ("hard_deadline_epoch", "closeout_start_epoch"):
        if not isinstance(state.get(key), (float, int)):
            raise ValueError(f"study.json requires numeric {key}")
    if not (time.time() < float(state["hard_deadline_epoch"])):
        raise ValueError("study hard deadline has passed")
    if not isinstance(state.get("max_arm_launches"), int) or not (1 <= state["max_arm_launches"] <= 12):
        raise ValueError("study.json must cap arm launches at twelve or fewer")
    validate_study_inputs(study)
    return study, state


def default_host_command(command: list[str], receipts: Path) -> list[str]:
    """Keep frozen tool restrictions while letting the CLI choose its host default."""
    result: list[str] = []
    index = 0
    inserted = False
    while index < len(command):
        item = command[index]
        if item == "-m":
            index += 2
            continue
        if item == "-c" and index + 1 < len(command):
            setting = command[index + 1]
            if setting.startswith("model_reasoning_effort="):
                index += 2
                continue
            prefix = "mcp_servers.shiploop_workspace.args="
            if setting.startswith(prefix):
                args = json.loads(setting[len(prefix):])
                args += ["--receipts", str(receipts)]
                result += ["-c", prefix + json.dumps(args)]
                inserted = True
                index += 2
                continue
        result.append(item)
        index += 1
    if not inserted:
        raise ValueError("frozen codex command has no workspace gateway arguments")
    return result


def reserve_launch(study: Path, arm: str, maximum: int) -> int:
    path = study / "launch-ledger.json"
    path.touch(exist_ok=True)
    with path.open("r+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            try:
                raw = handle.read()
                state = json.loads(raw) if raw.strip() else {}
            except json.JSONDecodeError as exc:
                raise ValueError("launch ledger is invalid") from exc
            launches = state.get("launches", [])
            if not isinstance(launches, list):
                raise ValueError("launch ledger is invalid")
            if any(isinstance(item, dict) and item.get("arm") == arm for item in launches):
                raise ValueError("arm was already reserved; automatic retries are forbidden")
            if len(launches) >= maximum:
                raise ValueError("maximum arm launches reached")
            launches.append({"arm": arm, "reserved_at": utc_now()})
            handle.seek(0)
            json.dump({"schema": "generalized-discovery-launches/1", "launches": launches}, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.truncate()
            return len(launches)
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def ledger_snapshot(path: Path) -> dict[str, Any]:
    try:
        return json_file(path)
    except (OSError, ValueError, json.JSONDecodeError):
        return {"status": "unavailable"}


def extract_usage(events: Path) -> dict[str, Any]:
    keys = {"input_tokens", "output_tokens", "cached_input_tokens", "total_tokens"}
    records: list[dict[str, int]] = []
    if not events.is_file():
        return {"status": "unavailable", "reason": "event stream unavailable"}
    for line in events.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        stack = [value]
        while stack:
            current = stack.pop()
            if isinstance(current, dict):
                found = {key: val for key, val in current.items() if key in keys and isinstance(val, int)}
                if found:
                    records.append(found)
                stack.extend(current.values())
            elif isinstance(current, list):
                stack.extend(current)
    return {"status": "observed" if records else "unavailable", "records": records}


def reserve_watch(runtime: Any) -> type:
    class ReserveWatch(runtime.ActionWatch):
        def observe(self, context: int, event: dict[str, Any]) -> str | None:
            if event.get("type") not in {"item.started", "item.completed"} or not isinstance(event.get("item"), dict):
                return None
            item = event["item"]
            kind = str(item.get("type") or "")
            if kind not in runtime.ACTION_TYPES:
                return None
            token = f"{context}:{item.get('id') or json.dumps(item, sort_keys=True, default=str)}"
            with self.lock:
                if token in self.seen:
                    return self.stop_reason
                self.seen.add(token)
                self.by_type[kind] += 1
                count, now = len(self.seen), time.time()
                report_only = now >= self.cutoff_epoch or count > LIMITS["exploration_calls"]
                self.records.append({"context": context, "event": event.get("type"), "type": kind,
                                     "server": item.get("server"), "tool": item.get("tool"),
                                     "phase": "report_only" if report_only else "exploration"})
                if count > LIMITS["calls_per_arm"]:
                    self.stop_reason = "observed_hard_action_limit"
                elif report_only and kind != "mcp_tool_call":
                    self.stop_reason = "report_reserve_non_gateway_action"
                return self.stop_reason
    return ReserveWatch


def report_status(workspace: Path) -> dict[str, Any]:
    path = workspace / "REPORT.md"
    if not path.is_file() or path.is_symlink():
        return {"path": "REPORT.md", "exists": False, "valid_task_required_report": False}
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return {"path": "REPORT.md", "exists": True, "valid_task_required_report": False, "reason": "not_utf8"}
    return {"path": "REPORT.md", "exists": True, "bytes": len(text.encode()),
            "valid_task_required_report": bool(text.strip()), "validation": "nonempty_utf8_transport"}


def completion_status(context: Any, report: dict[str, Any], fixture_edits: dict[str, list[str]]) -> dict[str, Any]:
    """Classify an arm from observable execution and task-output evidence."""
    exit_code = context.get("exit_code") if isinstance(context, dict) else None
    termination_reason = context.get("termination_reason") if isinstance(context, dict) else None
    reasons: list[str] = []
    failed = False
    if not isinstance(exit_code, int) or isinstance(exit_code, bool):
        reasons.append("context_exit_code_unavailable")
    elif exit_code != 0:
        reasons.append("context_nonzero_exit")
        failed = True
    if termination_reason is not None:
        reasons.append("context_terminated")
        failed = True
    if isinstance(context, dict) and context.get("status") == "launcher_error":
        reasons.append("context_launcher_error")
        failed = True
    if not report.get("valid_task_required_report"):
        reasons.append("report_missing_or_invalid")
    if fixture_edits:
        reasons.append("fixture_edits_detected")
        failed = True
    return {"status": "completed" if not reasons else "failed" if failed else "incomplete",
            "reasons": reasons, "exit_code": exit_code, "termination_reason": termination_reason}


def batch_status(results: list[dict[str, Any]]) -> str:
    """Return the batch outcome without re-running or obscuring arm outcomes."""
    statuses = [result.get("status") for result in results]
    if statuses and all(status == "completed" for status in statuses):
        return "completed"
    if "failed" in statuses:
        return "failed"
    return "incomplete"


def run_arm(study: Path, state: dict[str, Any], runtime: Any, arm: str) -> dict[str, Any]:
    try:
        validate_study_inputs(study)
    except ValueError as exc:
        return {"arm": arm, "status": "not_started_study_inputs_invalid", "reason": str(exc)}
    now = time.time()
    if now >= float(state["closeout_start_epoch"]):
        return {"arm": arm, "status": "not_started_after_closeout"}
    root, workspace, prompt, run = study / "arms" / arm, study / "arms" / arm / "workspace", study / "arms" / arm / "prompt.md", study / "arms" / arm / "run"
    if not workspace.is_dir() or not prompt.is_file():
        return {"arm": arm, "status": "not_started_missing_prepared_inputs"}
    if run.exists():
        return {"arm": arm, "status": "refused_existing_run"}
    before = snapshot(workspace)
    expected_path = root / "input-hashes.json"
    if expected_path.is_file() and json_file(expected_path) != before:
        return {"arm": arm, "status": "not_started_input_hash_mismatch"}
    study_arm = state.get("arms", {}).get(arm, {}) if isinstance(state.get("arms"), dict) else {}
    if isinstance(study_arm, dict) and study_arm.get("prompt_sha256") not in (None, sha256(prompt)):
        return {"arm": arm, "status": "not_started_prompt_hash_mismatch"}
    deadline = min(now + LIMITS["seconds_per_arm"], float(state["hard_deadline_epoch"]))
    cutoff = min(now + LIMITS["exploration_seconds"], deadline - 1)
    if cutoff <= now:
        return {"arm": arm, "status": "not_started_without_report_window"}
    try:
        launch_number = reserve_launch(study, arm, state["max_arm_launches"])
    except ValueError as exc:
        return {"arm": arm, "status": "not_started_launch_refused", "reason": str(exc)}
    run.mkdir()
    pre_path, post_path, ledger, log = run / "input-hashes-pre.json", run / "input-hashes-post.json", run / "gateway-ledger.json", run / "gateway.jsonl"
    write_json(pre_path, before)
    receipts = study / "receipts.jsonl"
    command = runtime.codex_command(workspace, run, ledger, log, now, deadline, cutoff, 1, None, study / "frozen" / "receipt_gateway.py")
    command = default_host_command(command, receipts)
    invocation = {"schema": "generalized-discovery-invocation/1", "arm": arm, "launch_number": launch_number,
                  "started_at": utc_now(), "deadline_epoch": deadline, "cutoff_epoch": cutoff,
                  "command": command, "command_sha256": hashlib.sha256(json.dumps(command).encode()).hexdigest(),
                  "model_selection": {"requested": "host_default", "observed": None,
                                      "status": "unavailable", "reason": "selected CLI model/config was not observed"}}
    write_json(run / "invocation.json", invocation)
    Watch = reserve_watch(runtime)
    watch = Watch(start_epoch=now, cutoff_epoch=cutoff, deadline_epoch=deadline)
    try:
        context = runtime.stream_context(command, prompt.read_text(encoding="utf-8"), context=1, run=run, watch=watch, deadline_epoch=deadline)
    except (OSError, ValueError) as exc:
        context = {"context": 1, "status": "launcher_error", "error": exc.__class__.__name__}
    after = snapshot(workspace)
    write_json(post_path, after)
    delta = tree_delta(before, after)
    fixture_edits = {key: values for key, values in delta.items() if key in {"deleted", "modified"} and values}
    report = report_status(workspace)
    completion = completion_status(context, report, fixture_edits)
    metadata = {"schema": "generalized-discovery-run/1", "arm": arm, "finished_at": utc_now(),
                "limits": LIMITS, "deadline_epoch": deadline, "cutoff_epoch": cutoff,
                "model_selection": invocation["model_selection"], "input_hashes": {"pre": str(pre_path), "post": str(post_path)},
                "contexts": [context], "context_output": "final-1.md", "usage": extract_usage(run / "events-1.jsonl"),
                "observed_actions": watch.snapshot(), "gateway_ledger": ledger_snapshot(ledger),
                "report": report, "workspace_delta": delta, "fixture_edits": fixture_edits,
                "fixture_edits_flagged": bool(fixture_edits), "completion": completion}
    write_json(run / "metadata.json", metadata)
    return {"arm": arm, "status": completion["status"], "run": str(run),
            "report": report["valid_task_required_report"], "completion": completion}


class Rpc:
    def __init__(self, argv: list[str]) -> None:
        self.proc = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True)
        self.next_id = 1

    def request(self, method: str, params: dict[str, Any] | None = None, timeout: float = 10) -> dict[str, Any]:
        if self.proc.stdin is None or self.proc.stdout is None:
            raise RuntimeError("gateway pipes unavailable")
        ident = self.next_id
        self.next_id += 1
        message: dict[str, Any] = {"jsonrpc": "2.0", "id": ident, "method": method}
        if params is not None:
            message["params"] = params
        self.proc.stdin.write(json.dumps(message) + "\n")
        self.proc.stdin.flush()
        ready, _, _ = select.select([self.proc.stdout], [], [], timeout)
        if not ready:
            raise TimeoutError("gateway RPC timed out")
        response = self.proc.stdout.readline()
        payload = json.loads(response)
        if payload.get("id") != ident or "error" in payload or not isinstance(payload.get("result"), dict):
            raise RuntimeError("invalid gateway RPC response")
        return payload["result"]

    def workspace(self, arguments: dict[str, Any]) -> tuple[dict[str, Any], bool]:
        result = self.request("tools/call", {"name": "workspace", "arguments": arguments})
        content = result.get("content")
        text = content[0].get("text") if isinstance(content, list) and content and isinstance(content[0], dict) else None
        payload = json.loads(text) if isinstance(text, str) else None
        if not isinstance(payload, dict):
            raise RuntimeError("invalid workspace payload")
        return payload, bool(result.get("isError"))

    def close(self) -> dict[str, Any]:
        if self.proc.stdin is not None:
            self.proc.stdin.close()
        try:
            self.proc.wait(timeout=5)
            cleanup = {"exit_code": self.proc.returncode, "killed": False}
        except subprocess.TimeoutExpired:
            os.killpg(self.proc.pid, signal.SIGTERM)
            self.proc.wait(timeout=5)
            cleanup = {"exit_code": self.proc.returncode, "killed": True}
        return cleanup


def preflight(study: Path, state: dict[str, Any]) -> dict[str, Any]:
    root = study / "reports" / f"runner-preflight-{int(time.time())}"
    workspace, run, private = root / "workspace", root / "run", root / "private"
    workspace.mkdir(parents=True)
    run.mkdir()
    private.mkdir()
    (workspace / "proof.txt").write_text("safe\n", encoding="utf-8")
    canary = private / "outside-canary.txt"
    canary.write_text("not-for-receipt\n", encoding="utf-8")
    start, deadline = time.time(), min(time.time() + 60, float(state["hard_deadline_epoch"]))
    cutoff = min(start + 45, deadline - 1)
    argv = [sys.executable, str(study / "frozen" / "receipt_gateway.py"), "--workspace", str(workspace), "--log", str(run / "gateway.jsonl"), "--ledger", str(run / "gateway-ledger.json"), "--receipts", str(root / "receipts.jsonl"), "--start-epoch", str(start), "--deadline-epoch", str(deadline), "--cutoff-epoch", str(cutoff), "--call-limit", "32", "--exploration-limit", "24"]
    checks = {"initialized": False, "catalog": False, "safe_python": False, "outside_read_denied": False,
              "report_reserve": False, "hard_counter": False, "full_receipts": False}
    rpc: Rpc | None = None
    error: str | None = None
    try:
        rpc = Rpc(argv)
        checks["initialized"] = rpc.request("initialize", {"protocolVersion": "2025-11-25"}).get("protocolVersion") == "2025-11-25"
        tools = rpc.request("tools/list").get("tools", [])
        checks["catalog"] = any(isinstance(item, dict) and item.get("name") == "workspace" for item in tools)
        safe, safe_error = rpc.workspace({"operation": "exec", "argv": [sys.executable, "-c", "print('safe authorization observation')"]})
        checks["safe_python"] = not safe_error and safe.get("exit_code") == 0 and safe.get("stdout", "").strip() == "safe authorization observation"
        denied, denied_error = rpc.workspace({"operation": "read", "path": str(canary)})
        checks["outside_read_denied"] = denied_error and isinstance(denied.get("error"), str)
        for _ in range(22):
            rpc.workspace({"operation": "list", "path": ""})
        blocked, blocked_error = rpc.workspace({"operation": "exec", "argv": [sys.executable, "-c", "print('late')"]})
        report, report_error = rpc.workspace({"operation": "write", "path": "REPORT.md", "content": "# report\n"})
        checks["report_reserve"] = blocked_error and "only list/read" in str(blocked.get("error")) and not report_error and report.get("phase") == "report_only"
        for _ in range(6):
            rpc.workspace({"operation": "read", "path": "REPORT.md"})
        capped, capped_error = rpc.workspace({"operation": "list", "path": ""})
        checks["hard_counter"] = capped_error and capped.get("error") == "call_limit"
    except Exception as exc:
        error = exc.__class__.__name__
    finally:
        cleanup = rpc.close() if rpc is not None else {"status": "not_started"}
    receipt_path = root / "receipts.jsonl"
    receipts = receipt_path.read_text(encoding="utf-8").splitlines() if receipt_path.is_file() else []
    checks["full_receipts"] = (len(receipts) >= 33 and any("safe authorization observation" in line for line in receipts)
                               and not any("not-for-receipt" in line for line in receipts))
    result = {"schema": "generalized-discovery-preflight/1", "status": "verified" if error is None and all(checks.values()) else "failed",
              "checks": checks, "error": error, "cleanup": cleanup, "receipt_count": len(receipts), "usage": {"status": "unavailable", "reason": "no model launched"}}
    write_json(root / "result.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--study", required=True, type=Path)
    parser.add_argument("--arms", help="comma-separated opaque prepared arm IDs")
    parser.add_argument("--parallel", type=int, default=3)
    parser.add_argument("--preflight", action="store_true")
    args = parser.parse_args()
    try:
        study, state = read_study(args.study)
        if args.preflight:
            result = preflight(study, state)
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0 if result["status"] == "verified" else 2
        if not args.arms:
            raise ValueError("--arms is required for model launches")
        arms = [item for item in args.arms.split(",") if item]
        if not arms or len(set(arms)) != len(arms) or any(ARM_NAME.fullmatch(item) is None for item in arms):
            raise ValueError("--arms must be unique opaque IDs")
        if not (1 <= args.parallel <= 3) or args.parallel > state["parallel"]:
            raise ValueError("--parallel must be between one and the study cap")
        runtime = load_frozen(study)
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.parallel) as pool:
            results = list(pool.map(lambda arm: run_arm(study, state, runtime, arm), arms))
        status = batch_status(results)
        summary = {"schema": "generalized-discovery-runner-summary/1", "at": utc_now(), "status": status,
                   "all_requested_arms_completed": status == "completed", "results": results}
        reports = study / "reports"
        reports.mkdir(exist_ok=True)
        write_json(reports / f"runner-summary-{int(time.time())}.json", summary)
        print(json.dumps(summary, indent=2, sort_keys=True))
        return 0 if status == "completed" else 2
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"runner failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
