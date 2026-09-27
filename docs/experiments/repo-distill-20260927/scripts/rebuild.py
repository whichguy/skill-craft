#!/usr/bin/env python3
"""E3 baseline rebuild: one plain Grok session builds from the spec alone.

    rebuild.py --spec SPEC --oracle ORACLE_DIR --out DIR

Creates DIR/work (empty git repo holding only SPEC.md), runs the build prompt
with web search off, resolves the program's start command from package.json
`bin`, runs the oracle, and writes DIR/results.json and DIR/oracle.tap.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def app_cmd(work: Path) -> str | None:
    pkg = work / "package.json"
    if not pkg.is_file():
        return None
    bin_field = json.loads(pkg.read_text()).get("bin")
    entry = next(iter(bin_field.values()), None) if isinstance(bin_field, dict) else bin_field
    return f"node {(work / entry).resolve()}" if entry else None


def score(work: Path, oracle: Path, out: Path) -> dict:
    cmd = app_cmd(work)
    if cmd is None:
        return {"error": "package.json has no bin entry"}
    if (work / "package.json").is_file() and not (work / "node_modules").exists():
        subprocess.run(["npm", "install", "--no-audit", "--no-fund", "--silent"], cwd=work,
                       stdin=subprocess.DEVNULL, capture_output=True)
    proc = subprocess.run([sys.executable, str(HERE / "oracle_run.py"), str(oracle), "--app-cmd", cmd,
                           "--json", str(out / "results.json"), "--tap", str(out / "oracle.tap")],
                          capture_output=True, text=True)
    return json.loads((out / "results.json").read_text())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", type=Path, required=True)
    ap.add_argument("--oracle", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--score-only", action="store_true", help="skip the build; rescore DIR/work")
    ap.add_argument("--forbid", action="append", default=[],
                    help="string whose appearance in the builder's transcript voids the run (original name, path)")
    args = ap.parse_args()
    out = args.out.resolve()
    work = out / "work"
    if not args.score_only:
        work.mkdir(parents=True)
        shutil.copy(args.spec, work / "SPEC.md")
        subprocess.run(["git", "init", "-q"], cwd=work, check=True)
        subprocess.run([sys.executable, str(HERE / "grok_step.py"), "--cwd", str(work),
                        "--prompt", str(HERE.parent / "prompts" / "build.md"), "--out", str(out / "step"),
                        "--no-web", "--max-turns", "200"], check=False)
    # Access voids a run; recognition does not. Only the builder's tool calls
    # (reads, commands, installs) can reach the original; a name in its
    # thoughts or text is memorisation, recorded but accepted for the pilot.
    events = out / "step" / "events.jsonl"
    tools, prose = "", ""
    for line in (events.read_text(errors="replace").splitlines() if events.is_file() else []):
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if isinstance(event, dict) and event.get("type") in ("tool_call", "tool_call_update"):
            tools += json.dumps(event.get("rawInput") or event.get("title") or "").lower()
        else:
            prose += line.lower()
    leaks = [f for f in args.forbid if f.lower() in tools]
    recognised = [f for f in args.forbid if f.lower() in prose]
    pkg = work / "package.json"
    if pkg.is_file():
        data = json.loads(pkg.read_text())
        deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
        leaks += [f"depends on {d}" for d in deps if d.lower() in (f.lower() for f in args.forbid)]
    result = score(work, args.oracle.resolve(), out)
    result["clean_room_leaks"] = leaks
    result["recognised"] = recognised
    (out / "results.json").write_text(json.dumps(result, indent=2) + "\n")
    if leaks:
        print(f"CLEAN ROOM VOID: transcript mentions {leaks}")
    print(json.dumps(result.get("counts", result)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
