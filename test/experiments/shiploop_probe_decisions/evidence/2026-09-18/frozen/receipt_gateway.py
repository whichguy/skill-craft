#!/usr/bin/env python3
"""Receipt-preserving wrapper around this study's frozen workspace gateway.

The original gateway remains the isolation and validation owner.  This wrapper
only changes the trial budget's report reserve and mirrors each synthetic
workspace request/result to a coordinator-owned receipt file.
"""
from __future__ import annotations

import argparse
import datetime as dt
import fcntl
import hashlib
import importlib.util
import json
import re
import sys
import time
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location(
    "generalized_discovery_frozen_gateway", HERE / "gateway.py"
)
if _spec is None or _spec.loader is None:
    raise RuntimeError("frozen gateway.py is unavailable")
gateway = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = gateway
_spec.loader.exec_module(gateway)

SENSITIVE = re.compile(r"^(?:authorization|credential|password|secret|token|api[_-]?key|cookie)$", re.I)
ENVIRONMENT = re.compile(r"^(?:env|environment|home)$", re.I)
VALUE_SECRET = re.compile(
    r"(?i)\b(authorization|credential|password|secret|token|api[_-]?key|cookie)(\s*(?:=|:)\s*)([^\s,;]+)"
)


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def safe_value(value: Any, *, key: str = "") -> Any:
    """Keep complete synthetic values while never preserving auth or env data."""
    if SENSITIVE.search(key):
        return "<redacted>"
    if ENVIRONMENT.fullmatch(key):
        return "<redacted-environment>"
    if isinstance(value, dict):
        return {str(name): safe_value(item, key=str(name)) for name, item in value.items()}
    if isinstance(value, list):
        return [safe_value(item, key=key) for item in value]
    if isinstance(value, str):
        # Preserve fixture prose such as "authorization is required" while
        # removing only credential-bearing assignments or headers.
        return VALUE_SECRET.sub(r"\1\2<redacted>", gateway.redact(value))
    return value


def payload_from_response(response: dict[str, Any]) -> Any:
    content = response.get("content")
    if not isinstance(content, list) or not content or not isinstance(content[0], dict):
        return response
    text = content[0].get("text")
    if not isinstance(text, str):
        return response
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return response


class ReportReserveLedger(gateway.Ledger):
    """Spend the post-24-call reserve on reporting instead of rejecting it."""

    def consume(self, *, operation: str | None, path: str | None) -> tuple[dict[str, Any] | None, str | None]:
        with self.path.open("r+", encoding="utf-8") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                try:
                    state = json.load(handle)
                except json.JSONDecodeError as exc:
                    raise gateway.GatewayError("trial ledger is invalid") from exc
                now = time.time()
                calls = state.get("tool_calls")
                if not isinstance(calls, int) or calls < 0:
                    raise gateway.GatewayError("trial ledger is invalid")
                if now >= float(state["hard_deadline_epoch"]):
                    return None, "hard_deadline"
                if calls >= int(state["call_limit"]):
                    return None, "call_limit"
                phase = "report_only" if (
                    now >= float(state["exploration_cutoff_epoch"])
                    or calls >= int(state["exploration_limit"])
                ) else "exploration"
                state["tool_calls"] = calls + 1
                state["records"].append({
                    "at": utc_now(), "call": calls + 1, "phase": phase,
                    "operation": operation, "path": path,
                })
                handle.seek(0)
                json.dump(state, handle, sort_keys=True)
                handle.write("\n")
                handle.truncate()
                return state, phase
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


class ReceiptGateway(gateway.Gateway):
    def __init__(self, args: argparse.Namespace) -> None:
        self.receipts_path = Path(args.receipts).resolve(strict=False)
        super().__init__(args)
        self.arm_id = self.root.parent.name
        if gateway.within(self.receipts_path, self.root):
            self.close()
            raise gateway.GatewayError("coordinator receipts must stay outside the workspace")
        self.receipts_path.parent.mkdir(parents=True, exist_ok=True)
        self.ledger = ReportReserveLedger(
            args.ledger,
            start_epoch=args.start_epoch,
            deadline_epoch=args.deadline_epoch,
            cutoff_epoch=args.cutoff_epoch,
            call_limit=args.call_limit,
            exploration_limit=args.exploration_limit,
        )

    def receipt(self, value: dict[str, Any]) -> None:
        encoded = json.dumps(safe_value(value), sort_keys=True, ensure_ascii=False) + "\n"
        with self.receipts_path.open("a", encoding="utf-8") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                handle.write(encoded)
                handle.flush()
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    def call(self, params: Any) -> dict[str, Any]:
        request = safe_value(params)
        try:
            response = super().call(params)
        except Exception as exc:
            self.receipt({"at": utc_now(), "arm": self.arm_id, "event": "workspace_call", "request": request,
                          "exception": exc.__class__.__name__})
            raise
        self.receipt({
            "at": utc_now(), "arm": self.arm_id, "event": "workspace_call", "request": request,
            "result": payload_from_response(response), "is_error": bool(response.get("isError")),
        })
        return response


def parse_args() -> argparse.Namespace:
    wrapper = argparse.ArgumentParser(add_help=False)
    wrapper.add_argument("--receipts", required=True, type=Path)
    ours, remaining = wrapper.parse_known_args()
    previous = sys.argv
    try:
        sys.argv = [sys.argv[0], *remaining]
        args = gateway.parse_args()
    finally:
        sys.argv = previous
    args.receipts = ours.receipts
    return args


def main() -> int:
    args = parse_args()
    if args.self_test:
        raise SystemExit("use runner.py --preflight so receipt coverage is checked")
    try:
        service = ReceiptGateway(args)
    except gateway.GatewayError as exc:
        print(f"gateway startup failed: {exc}", file=sys.stderr)
        return 2
    try:
        for raw in sys.stdin:
            raw = raw.rstrip("\r\n")
            if not raw:
                continue
            try:
                response = service.handle(json.loads(raw))
            except json.JSONDecodeError as exc:
                response = gateway.rpc_error(None, -32700, f"parse error: {exc.msg}")
            if response is not None:
                print(json.dumps(response, sort_keys=True), flush=True)
    finally:
        service.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
