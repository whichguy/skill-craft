#!/usr/bin/env python3
"""Collect measured trial telemetry without treating a normal exit as success."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
from collections import Counter
from pathlib import Path


def collect(study: Path) -> dict:
    manifest = json.loads((study / "manifest.json").read_text())
    rows = []
    usage_total: Counter = Counter()
    for arm in sorted((study / "arms").iterdir()):
        meta_path = arm / "run/metadata.json"
        if not meta_path.exists():
            ledger_path = arm / "run/gateway-ledger.json"
            ledger = json.loads(ledger_path.read_text()) if ledger_path.exists() else {}
            rows.append({"arm": arm.name, "execution": "running" if (arm / "run").exists() else "unrun",
                         "gateway_actions": ledger.get("tool_calls")})
            continue
        meta = json.loads(meta_path.read_text())
        usage: Counter = Counter()
        usage_contexts = 0
        operations: Counter = Counter()
        platform_methods: Counter = Counter()
        optional_mcp_mentions = 0
        cli_errors = 0
        completion_receipts = []
        prompt_match = re.search(r"--action=(nav-[a-f0-9]+)", (arm / "prompt.md").read_text())
        expected_action = prompt_match.group(1) if prompt_match else None
        for event_path in sorted((arm / "run").glob("events-*.jsonl")):
            for line in event_path.read_text().splitlines():
                try:
                    event = json.loads(line)
                except ValueError:
                    continue
                if event.get("type") == "turn.completed" and isinstance(event.get("usage"), dict):
                    usage.update({k: v for k, v in event["usage"].items() if isinstance(v, int)})
                    usage_contexts += 1
                item = event.get("item", {})
                if event.get("type") != "item.completed" or item.get("type") != "mcp_tool_call":
                    continue
                args = item.get("arguments", {})
                if not isinstance(args, dict):
                    continue
                op = args.get("operation", "unknown")
                operations[op] += 1
                if op == "platform":
                    platform_methods[args.get("request", {}).get("method", "unknown")] += 1
                if op == "exec" and "mcp_probe.py" in json.dumps(args.get("argv", [])):
                    optional_mcp_mentions += 1
                result_text = json.dumps(item.get("result", {}))
                if "Operation not permitted" in result_text and "/private" in result_text:
                    cli_errors += 1
                argv_text = json.dumps(args.get("argv", []))
                if op == "exec" and expected_action and expected_action in argv_text and "complete" in argv_text:
                    for content in item.get("result", {}).get("content", []):
                        try:
                            result = json.loads(content.get("text", ""))
                        except (ValueError, TypeError):
                            continue
                        completion_receipts.append({"event_file": event_path.name, "item_id": item.get("id"),
                                                    "exit_code": result.get("exit_code"),
                                                    "navigator_output": "ShipLoop navigator |" in result.get("stdout", "")})
        contexts = meta.get("contexts", [])
        elapsed = (dt.datetime.fromisoformat(meta["finished_at"].replace("Z", "+00:00")) -
                   dt.datetime.fromisoformat(meta["started_at"].replace("Z", "+00:00"))).total_seconds()
        calls = meta.get("gateway_ledger", {}).get("tool_calls")
        terminated = [c.get("termination_reason") for c in contexts if c.get("termination_reason")]
        app = arm / "workspace/app.py"
        accepted_outcome = None
        state_path = arm / "workspace/shiploop-state/state.md"
        if state_path.exists() and expected_action:
            match = re.search(r"```shiploop-state\s*\n(.*?)\n```", state_path.read_text(), re.S)
            if match:
                accepted_outcome = json.loads(match.group(1)).get("accepted", {}).get(expected_action, {}).get("outcome")
        row = {
            "arm": arm.name,
            "execution": "interrupted" if terminated or any(c.get("exit_code") != 0 for c in contexts) else "completed",
            "semantic_grade": "separate evaluator required",
            "started_at": meta["started_at"], "finished_at": meta["finished_at"],
            "elapsed_seconds": round(elapsed, 2), "gateway_actions": calls,
            "contexts": len(contexts), "termination_reasons": terminated,
            "within_action_cap": calls <= 64 if isinstance(calls, int) else None,
            "usage": dict(usage) if usage_contexts else None,
            "usage_contexts_reported": usage_contexts,
            "usage_contexts_total": len(contexts),
            "completed_gateway_operations": dict(operations),
            "platform_methods": dict(platform_methods),
            "optional_mcp_probe_mentions_in_exec": optional_mcp_mentions,
            "private_path_error_receipts": cli_errors,
            "protocol": {"expected_action": expected_action, "accepted_outcome_in_state": accepted_outcome,
                         "completion_receipts": completion_receipts,
                         "observed_accepted_completion": bool(accepted_outcome and any(
                             r["exit_code"] == 0 and r["navigator_output"] for r in completion_receipts))},
            "service_status": meta.get("service", {}).get("status"),
            "service_cleanup": meta.get("service", {}).get("cleanup"),
            "worker_cleanup": [c.get("cleanup") for c in contexts],
            "final_app_sha256": hashlib.sha256(app.read_bytes()).hexdigest() if app.exists() else None,
            "report_present": (arm / "workspace/REPORT.md").exists(),
            "runtime": "frozen/runtime" if arm.name in manifest["groups"]["screen"] else "frozen/runtime-v2",
        }
        rows.append(row)
        usage_total.update(usage)
    completed = [r for r in rows if r["execution"] in {"completed", "interrupted"}]
    return {
        "version": 1,
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "notes": [
            "Execution completion is not semantic success, accepted ShipLoop transition, deployment or intended-user verification.",
            "Gateway actions are top-level adapter calls. One exec can contain multiple HTTP or nested MCP requests; those are not a request cap.",
            "Usage is host-reported telemetry. Input includes cached input; reasoning output is a reported subset, not added again to output.",
            "Mandatory workspace MCP is instrumentation. Probe-name mentions include source/document inspection and are not evidence of invocation, initialization or useful outcomes.",
            "Isolation and harness limitations are in runtime-amendment and final report; runner gateway_only labels are not a complete isolation proof.",
        ],
        "finished_trials": len(completed),
        "aggregate_worker_seconds": round(sum(r["elapsed_seconds"] for r in completed), 2),
        "aggregate_gateway_actions": sum(r["gateway_actions"] or 0 for r in completed),
        "reported_usage_sum": dict(usage_total),
        "arms": rows,
        "skipped": manifest.get("skipped", {}),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--study", required=True, type=Path)
    args = parser.parse_args()
    result = collect(args.study)
    out = args.study / "reports/run-inventory.json"
    out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"output": str(out), "finished_trials": result["finished_trials"],
                      "aggregate_gateway_actions": result["aggregate_gateway_actions"]}))


if __name__ == "__main__":
    main()
