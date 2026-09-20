#!/usr/bin/env python3
"""Offline, synthetic discovery read adapter; it never contacts Slack, Teams, or MCP."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
RECEIPTS = ROOT / "receipts.jsonl"
PUBLIC_ALIASES = {"public", "public-web", "web", "internet"}
ALIASES = {"privategit": "private-git", "intranetresources": "intranet"}


def load(name: str) -> dict:
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def receipt(event: str, **fields: object) -> None:
    row = {
        "fixture": "synthetic-orion-enterprise-discovery",
        "at": datetime.now(timezone.utc).isoformat(),
        "event": event,
        **fields,
    }
    with RECEIPTS.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")


def finish(command: str, outcome: str, payload: dict | None = None, code: int = 0) -> int:
    receipt("outcome", command=command, outcome=outcome, exitCode=code, response=payload)
    if payload is not None:
        print(json.dumps(payload, indent=2, sort_keys=True))
    return code


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="Synthetic, offline Orion discovery read adapter")
    commands = root.add_subparsers(dest="command", required=True)
    commands.add_parser("catalog", help="list synthetic source availability")
    search = commands.add_parser("search", help="return snippets only")
    search.add_argument("--source", required=True)
    search.add_argument("--query", required=True)
    search.add_argument("--cursor", help="use the nextCursor returned by a prior search")
    fetch = commands.add_parser("fetch", help="return one complete synthetic record")
    fetch.add_argument("--source", required=True)
    fetch.add_argument("--id", required=True)
    return root


def source_spec(catalog: dict, source: str) -> dict | None:
    return next((item for item in catalog["sources"] if item["id"] == source), None)


def summary(record: dict) -> dict:
    return {key: record[key] for key in ("source", "id", "title", "snippet", "provenance")}


def gap(command: str, source: str, reason: str) -> int:
    return finish(command, "gap", {"status": "gap", "source": source, "reason": reason})


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    command = next((item for item in argv if not item.startswith("-")), "help")
    receipt("invocation", command=command, argv=argv)
    try:
        args = parser().parse_args(argv)
    except SystemExit as exc:
        receipt("outcome", command=command, outcome="help_or_argument_error", exitCode=int(exc.code or 0))
        return int(exc.code or 0)

    try:
        catalog = load("catalog.json")
        if args.command == "catalog":
            return finish("catalog", "ok", catalog)

        source = ALIASES.get(args.source.casefold(), args.source.casefold())
        if source in PUBLIC_ALIASES:
            return finish(args.command, "rejected", {
                "status": "rejected", "source": source,
                "reason": "Public-source reads are forbidden by this offline fixture; no request was made.",
            }, 3)
        spec = source_spec(catalog, source)
        if spec is None:
            return gap(args.command, source, "Source is absent from this synthetic catalog.")
        if spec["status"] == "unavailable":
            return gap(args.command, source, spec["gap"])
        if spec["status"] != "authorized-readonly":
            return finish(args.command, "rejected", {
                "status": "rejected", "source": source, "reason": spec["gap"],
            }, 3)

        if args.command not in spec["operations"]:
            return gap(args.command, source, "Operation unavailable; inspect catalog for supported lookup/read operations.")
        records = load("records.json")["records"]
        if args.command == "search":
            args.query = args.query.strip()
            if args.query.casefold() != "orion":
                return gap("search", source, "Directory accepts literal service-family key Orion, not free-text search.")
            matches = [record for record in records if record["source"] == "slack"]
            expected_cursor = f"{source}:{args.query.casefold()}:2"
            if args.cursor and args.cursor != expected_cursor:
                return gap("search", source, "Cursor does not belong to this source and query.")
            start = 2 if args.cursor else 0
            page = matches[start:start + 2]
            next_cursor = expected_cursor if not args.cursor and len(matches) > 2 else None
            return finish("search", "ok", {
                "status": "ok", "source": source, "query": args.query,
                "results": [summary(record) for record in page], "nextCursor": next_cursor,
            })

        record = next((item for item in records if item["source"] == source and item["id"] == args.id), None)
        if record is None:
            return gap("fetch", source, "Record is missing or not authorized in this fixture.")
        return finish("fetch", "ok", {"status": "ok", "source": source, "record": record})
    except Exception as exc:  # Keep a malformed local fixture observable in its receipt.
        return finish(command, "error", {"status": "error", "reason": str(exc)}, 1)


if __name__ == "__main__":
    raise SystemExit(main())
