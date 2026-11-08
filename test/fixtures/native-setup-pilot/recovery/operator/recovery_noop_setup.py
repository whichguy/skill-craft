#!/usr/bin/env python3
"""Negative-control CLI that only claims setup success and writes no target state."""
import json
import sys


def main(argv: list[str]) -> int:
    if argv != ["setup", "sandbox"]:
        print(json.dumps({"status": "error", "reason": "unsupported control command"}, sort_keys=True))
        return 2
    print(json.dumps({"changed": True, "receipt_valid": True, "status": "ready", "target": "sandbox"}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
