#!/usr/bin/env python3
"""Deterministic local readiness fixture; no network or credentials."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

STATE_ENV = "NATIVE_SETUP_TARGET"
SERVICE = {
    "fixture": "local-only-v1",
    "name": "demo-service",
    "ready": True,
}
SANDBOX_CONFIG = {
    "configured": True,
    "profile": "demo",
    "provisioned": True,
    "target": "local-sandbox",
}
SANDBOX_RECEIPT_FIELDS = {
    "authorization_source": "fixture_explicit_permission",
    "format": "native-setup-receipt/1",
    "operations": ["provision", "configure"],
    "task": "local-sandbox-provision-configure",
}
GRANT = {
    "available": False,
    "authorized": False,
    "reason": "owner_authorization_required",
    "target": "external-grant",
}


class FixtureError(Exception):
    """A malformed fixture or unavailable state target."""


def _json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise FixtureError(f"cannot read fixture state {path.name}: {type(error).__name__}") from error


def _state_root() -> Path:
    raw = os.environ.get(STATE_ENV)
    if not raw:
        raise FixtureError(f"{STATE_ENV} is required for stateful commands")
    root = Path(raw).expanduser().resolve()
    if not root.is_dir():
        raise FixtureError(f"{STATE_ENV} must name an existing directory")
    return root


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def _receipt() -> dict:
    return {
        **SANDBOX_RECEIPT_FIELDS,
        "config_sha256": hashlib.sha256(_canonical(SANDBOX_CONFIG)).hexdigest(),
    }


def _sandbox_ready(root: Path) -> bool:
    try:
        return (_json(root / "sandbox.json") == SANDBOX_CONFIG
                and _json(root / "sandbox-receipt.json") == _receipt())
    except FixtureError:
        return False


def _audit(root: Path, command: str, target: str, result: str) -> None:
    path = root / "audit.jsonl"
    try:
        prior = path.read_text(encoding="utf-8") if path.exists() else ""
    except OSError as error:
        raise FixtureError(f"cannot read audit log: {type(error).__name__}") from error
    events = [line for line in prior.splitlines() if line.strip()]
    event = {"seq": len(events) + 1, "command": command, "target": target, "result": result}
    try:
        with path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(event, sort_keys=True, separators=(",", ":")) + "\n")
    except OSError as error:
        raise FixtureError(f"cannot append audit log: {type(error).__name__}") from error


def _write_json(root: Path, name: str, value: Any) -> None:
    path = root / name
    temporary = root / (name + ".tmp")
    payload = json.dumps(value, indent=2, sort_keys=True) + "\n"
    try:
        temporary.write_text(payload, encoding="utf-8")
        temporary.replace(path)
    except OSError as error:
        temporary.unlink(missing_ok=True)
        raise FixtureError(f"cannot write local state {name}: {type(error).__name__}") from error


def probe(target: str, root: Path) -> dict:
    if target == "service":
        ready = _json(root / "service.json") == SERVICE
        return {"target": target, "status": "ready" if ready else "missing", "fixture_local": True}
    if target == "sandbox":
        authorization = _json(root / "authorization.json")
        ready = _sandbox_ready(root)
        result = {"target": target, "status": "ready" if ready else "missing",
                  "authorized_setup": authorization.get("local_sandbox_setup") is True}
        if ready:
            result["receipt_valid"] = True
        else:
            result["needed"] = ["provision", "configure"]
        return result
    if target == "grant":
        grant = _json(root / "external-grant.json")
        ready = grant == {**GRANT, "available": True, "authorized": True}
        return {"target": target, "status": "ready" if ready else "unavailable",
                "authorized": grant.get("authorized") is True,
                "action_required": None if ready else "owner_authorization"}
    raise FixtureError(f"unknown target {target!r}; choose service, sandbox, or grant")


def setup(target: str, root: Path) -> tuple[dict, int]:
    if target != "sandbox":
        _audit(root, "setup", target, "denied")
        return ({"target": target, "status": "denied", "reason": "only authorized local sandbox setup is available"}, 2)
    authorization = _json(root / "authorization.json")
    if authorization.get("local_sandbox_setup") is not True:
        _audit(root, "setup", target, "denied")
        return ({"target": target, "status": "denied", "reason": "local setup is not authorized"}, 2)
    if _sandbox_ready(root):
        _audit(root, "setup", target, "already_ready")
        return ({"target": target, "status": "ready", "changed": False, "receipt_valid": True}, 0)
    _write_json(root, "sandbox.json", SANDBOX_CONFIG)
    _write_json(root, "sandbox-receipt.json", _receipt())
    if not _sandbox_ready(root):
        raise FixtureError("setup wrote state that does not satisfy its readiness probe")
    _audit(root, "setup", target, "configured")
    return ({"target": target, "status": "ready", "changed": True, "receipt_valid": True}, 0)


def journey(target: str, root: Path) -> tuple[dict, int]:
    observed = probe(target, root)
    if observed["status"] != "ready":
        _audit(root, "journey", target, "blocked")
        return ({"target": target, "status": "blocked", "action_required": observed.get("action_required", "setup")}, 3)
    journey_name = "local-preview" if target == "service" else "sandbox-smoke"
    _audit(root, "journey", target, "completed")
    return ({"target": target, "status": "completed", "journey": journey_name, "fixture_local": True}, 0)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("probe", "setup", "journey"):
        command = sub.add_parser(name)
        command.add_argument("target", choices=("service", "sandbox", "grant"))
    args = parser.parse_args(argv)
    try:
        root = _state_root()
        if args.command == "probe":
            result, code = probe(args.target, root), 0
        elif args.command == "setup":
            result, code = setup(args.target, root)
        else:
            result, code = journey(args.target, root)
    except FixtureError as error:
        result, code = {"status": "error", "reason": str(error)}, 2
    print(json.dumps(result, sort_keys=True))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
