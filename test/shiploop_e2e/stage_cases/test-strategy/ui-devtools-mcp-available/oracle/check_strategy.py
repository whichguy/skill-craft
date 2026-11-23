"""Deterministic checks for test-strategy/ui-devtools-mcp-available."""
import json
import os
import re
import sys
from pathlib import Path

MCP_PATTERN = re.compile(r"\bmcp\b|chrome[- ]?devtools\s+mcp|devtools\s+mcp", re.I)
NODE_UNIT_PATTERN = re.compile(r"\bnode(?::test|\s+--test|\b)", re.I)


def fail(message: str) -> None:
    raise SystemExit(message)


def load_result() -> dict:
    path = os.environ.get("STAGE_RESULT")
    if not path:
        fail("STAGE_RESULT is not set")
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        fail("result.json must be a JSON object")
    return data


def check_p1(result: dict) -> None:
    layers = result.get("test_layers")
    if not isinstance(layers, list) or not layers:
        fail("test_layers must be a non-empty list")
    browser_rows = [
        row for row in layers
        if isinstance(row, dict) and row.get("layer") in ("component", "e2e")
    ]
    if not browser_rows:
        fail("test_layers must include at least one component or e2e browser layer")
    for row in browser_rows:
        harness = str(row.get("harness", "")).strip()
        if not harness or harness.lower() == "none":
            fail(f"browser layer {row.get('layer')!r} has no executable harness")
        if MCP_PATTERN.search(harness):
            fail(
                f"browser layer {row.get('layer')!r} selects an MCP server wrapper "
                f"as its automated harness: {harness!r}"
            )


def check_c1(result: dict) -> None:
    layers = result.get("test_layers")
    if not isinstance(layers, list) or not layers:
        fail("test_layers must be a non-empty list")
    unit_rows = [
        row for row in layers
        if isinstance(row, dict) and row.get("layer") == "unit"
    ]
    if not unit_rows:
        fail("test_layers must retain a unit layer")
    if not any(NODE_UNIT_PATTERN.search(str(row.get("harness", ""))) for row in unit_rows):
        fail("unit layer must retain node / node:test / node --test")


def main() -> None:
    if len(sys.argv) != 2 or sys.argv[1] not in ("P1", "C1"):
        fail("usage: check_strategy.py <P1|C1>")
    result = load_result()
    if sys.argv[1] == "P1":
        check_p1(result)
    else:
        check_c1(result)


if __name__ == "__main__":
    main()
