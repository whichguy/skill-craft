#!/usr/bin/env python3
"""Offline observation fixture; every response is synthetic and receipt-backed."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError(message)


def receipt_log() -> Path:
    here = Path(__file__).resolve().parent
    return (here.parent if here.name == "participant" else here) / "tool-receipts/probes.jsonl"


def observe(args):
    log = str(receipt_log())
    if args.help:
        return {"usage": "python3 -B probe.py --system crm|documents --topic identity|inventory|schema|completion [--target TARGET] [--page N]", "effects": "Read-only synthetic observations; receipts only.", "receipt_log": log}
    if not args.system or not args.topic:
        raise ValueError("--system and --topic are required")
    target = {"crm": "tenant-green", "documents": "folder-shared"}[args.system]
    if args.topic != "identity" and args.target != target:
        raise ValueError(f"{args.topic} requires current --target from identity; supplied target is not current")
    if args.system == "crm":
        if args.topic == "identity":
            return {"target": target, "discovery_operator": {"principal": "discovery-reader", "permissions": ["identity", "inventory", "schema_read"]}, "runtime_principal": {"principal": "crm-review-service", "ReviewState_records": "read/write configured, not behaviorally verified"}, "as_of": "current synthetic observation"}
        if args.topic == "inventory":
            if args.page not in (1, 2): raise ValueError("inventory page must be 1 or 2")
            return {"objects": ["LegacyCache"] if args.page == 1 else ["ReviewState"], "next_page": 2 if args.page == 1 else None, "scope": target}
        if args.topic == "schema":
            return {"object": "ReviewState", "fields": ["operation_id", "status", "revision"], "authority_candidate": "review state", "uniqueness": "unverified", "atomicity": "unverified", "migration_permission": "not established"}
        return {"record_write": "not a document-completion receipt", "operation_mapping": "not specified"}
    if args.topic == "identity":
        return {"target": target, "discovery_operator": {"principal": "metadata-reader", "read": "allowed", "write": "denied"}, "runtime_principal": {"principal": "document-worker", "write": "denied"}, "as_of": "current synthetic observation"}
    if args.topic in ("inventory", "schema"):
        return {"existing_facility": "shared workflow-state.json", "fields": ["operation_id", "document_id", "status"], "lock_scope": "document-project lock only; other document projects and external writers excluded", "conditional_write": "unverified", "old_note_conflict": "writer availability has changed"}
    return {"accepted_response": "queued, not completed", "processor": "unknown", "recovery_owner": "unknown", "lost_acknowledgement": "not specified", "durability": "runtime must not depend on developer workstation"}


def main():
    parser = Parser(add_help=False)
    parser.add_argument("--help", action="store_true")
    parser.add_argument("--system", choices=("crm", "documents"))
    parser.add_argument("--topic", choices=("identity", "inventory", "schema", "completion"))
    parser.add_argument("--target")
    parser.add_argument("--page", type=int, default=1)
    code = 0
    try:
        result = {"synthetic": True, "receipt_log": str(receipt_log()), "observation": observe(parser.parse_args())}
    except ValueError as error:
        code = 2; result = {"synthetic": True, "receipt_log": str(receipt_log()), "error": str(error)}
    text = json.dumps(result, sort_keys=True)
    receipt = {"at": datetime.now(timezone.utc).isoformat(), "argv": sys.argv[1:], "exit_code": code, "stdout": text if not code else "", "stderr": text if code else ""}
    log = receipt_log(); log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a", encoding="utf-8") as stream: stream.write(json.dumps(receipt, sort_keys=True) + "\n")
    print(text, file=sys.stderr if code else sys.stdout)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
