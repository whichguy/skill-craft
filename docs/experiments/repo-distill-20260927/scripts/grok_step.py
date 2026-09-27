#!/usr/bin/env python3
"""Run one headless Grok step in an isolated HOME and record what it cost.

    grok_step.py --cwd DIR --prompt FILE --out DIR [--no-web] [--timeout S]

Reuses the ShipLoop E2E harness's host helpers so the user's Grok profile and
plugins stay out. Writes events.jsonl, stderr.txt, final.txt and step.json
into --out.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "test" / "shiploop_e2e"))

import hosts  # noqa: E402
from run import summarize_events  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cwd", type=Path, required=True)
    ap.add_argument("--prompt", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--model", default="grok-4.7")
    ap.add_argument("--effort", default="medium")
    ap.add_argument("--max-turns", type=int, default=150)
    ap.add_argument("--timeout", type=int, default=3600)
    ap.add_argument("--no-web", action="store_true", help="disable web search and fetch (clean room)")
    args = ap.parse_args()

    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    env = hosts.grok_env(out / "home")
    argv = hosts.argv_for("grok", prompt=args.prompt.read_text(), prompt_file=out / "prompt.md",
                          cwd=args.cwd.resolve(), model=args.model, effort=args.effort,
                          permission_mode="auto", max_turns=args.max_turns)
    if args.no_web:
        argv.append("--disable-web-search")
    status = hosts.run_agent(argv, args.cwd.resolve(), env, out / "events.jsonl", out / "stderr.txt",
                             args.timeout)
    summary = summarize_events(out / "events.jsonl")
    (out / "final.txt").write_text(hosts.final_text(out / "events.jsonl"))
    import re
    reported = sorted(set(re.findall(r"grok-[0-9][0-9a-z.-]*", (out / "events.jsonl").read_text(errors="replace"))))
    step = {**status, "model": args.model, "effort": args.effort, "model_reported": reported,
            "num_turns": summary.get("num_turns"), "cost_usd": summary.get("cost_usd"),
            "stop": summary.get("stop")}
    (out / "step.json").write_text(json.dumps(step, indent=2) + "\n")
    print(json.dumps(step))
    return 0 if status["status"] == "exited" else 1


if __name__ == "__main__":
    raise SystemExit(main())
