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
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from spec_check import builder_view  # noqa: E402


def app_module(work: Path) -> str:
    """The file a consumer gets when importing the package, or "" when none."""
    pkg = json.loads((work / "package.json").read_text())
    exp = pkg.get("exports")
    if isinstance(exp, dict):
        exp = exp.get(".", exp)
    while isinstance(exp, dict):
        exp = exp.get("import") or exp.get("default") or exp.get("node") or next(iter(exp.values()), None)
    entry = exp or pkg.get("module") or pkg.get("main")
    return str((work / entry).resolve()) if entry else ""


def app_cmd(work: Path) -> str | None:
    pkg = work / "package.json"
    if not pkg.is_file():
        return None
    bin_field = json.loads(pkg.read_text()).get("bin")
    entry = next(iter(bin_field.values()), None) if isinstance(bin_field, dict) else bin_field
    return f"node {(work / entry).resolve()}" if entry else None


RENAMES: list[str] = []


def score(work: Path, oracle: Path, out: Path) -> dict:
    cmd = app_cmd(work)
    if cmd is None:
        return {"error": "package.json has no bin entry"}
    if (work / "package.json").is_file() and not (work / "node_modules").exists():
        subprocess.run(["npm", "install", "--no-audit", "--no-fund", "--silent"], cwd=work,
                       stdin=subprocess.DEVNULL, capture_output=True)
    proc = subprocess.run([sys.executable, str(HERE / "oracle_run.py"), str(oracle), "--app-cmd", cmd,
                           "--app-module", app_module(work), *[a for r in RENAMES for a in ("--rename", r)],
                           "--json", str(out / "results.json"), "--tap", str(out / "oracle.tap")],
                          capture_output=True, text=True)
    return json.loads((out / "results.json").read_text())


def codex_step(work: Path, step: Path, model: str, effort: str, prompt_file: Path | None = None) -> None:
    """One headless Codex session (web search off by default) in `work` running a prompt."""
    import time
    step.mkdir(parents=True)
    prompt = (prompt_file or HERE.parent / "prompts" / "build.md").read_text()
    (step / "prompt.md").write_text(prompt)
    argv = ["codex", "exec", "-m", model, "-c", f"model_reasoning_effort={effort}", "-s", "workspace-write",
            "--skip-git-repo-check", "--json", "-C", str(work), prompt]
    # Isolated CODEX_HOME: only the sign-in, so the user's AGENTS.md, hooks,
    # memories and plugins (browser, GitHub, ...) stay out of the clean room.
    home = step / "codex-home"
    home.mkdir()
    (home / "auth.json").symlink_to(Path.home() / ".codex" / "auth.json")
    env = {k: v for k, v in os.environ.items() if not k.startswith("CODEX")}
    env["CODEX_HOME"] = str(home)
    start = time.time()
    with (step / "events.jsonl").open("wb") as out, (step / "stderr.txt").open("wb") as err:
        proc = subprocess.run(argv, cwd=work, stdin=subprocess.DEVNULL, stdout=out, stderr=err, timeout=7200,
                              env=env)
    usage: dict = {}
    turns = commands = 0
    for line in (step / "events.jsonl").read_text(errors="replace").splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if event.get("type") == "turn.completed":
            turns += 1
            for k, v in (event.get("usage") or {}).items():
                usage[k] = usage.get(k, 0) + v
        item = event.get("item") or {}
        if event.get("type") == "item.completed" and item.get("type") == "command_execution":
            commands += 1
    (step / "step.json").write_text(json.dumps({
        "status": "exited" if proc.returncode == 0 else "failed", "returncode": proc.returncode,
        "elapsed_seconds": round(time.time() - start, 1), "host": "codex", "model": model, "effort": effort,
        "turns": turns, "commands": commands, "usage": usage}, indent=2) + "\n")


def claude_step(work: Path, step: Path, model: str, budget: float) -> None:
    """One headless Claude session (web tools off) building from SPEC.md."""
    sys.path.insert(0, str(HERE.parents[3] / "test" / "shiploop_e2e"))
    import hosts
    from run import summarize_events
    step.mkdir(parents=True)
    argv = hosts.argv_for("claude", prompt=(HERE.parent / "prompts" / "build.md").read_text(),
                          prompt_file=step / "prompt.md", cwd=work, model=model, effort=None,
                          permission_mode="auto", max_turns=200, max_budget_usd=budget)
    argv += ["--disallowedTools", "WebSearch,WebFetch", "--strict-mcp-config", "--mcp-config", '{"mcpServers":{}}']
    status = hosts.run_agent(argv, work, dict(os.environ), step / "events.jsonl", step / "stderr.txt", 7200)
    summary = summarize_events(step / "events.jsonl")
    (step / "step.json").write_text(json.dumps({**status, "host": "claude", "model": model,
        "model_reported": summary.get("model"), "num_turns": summary.get("num_turns"),
        "cost_usd": summary.get("cost_usd"), "stop": summary.get("stop")}, indent=2) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", type=Path, required=True)
    ap.add_argument("--oracle", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--score-only", action="store_true", help="skip the build; rescore DIR/work")
    ap.add_argument("--host", choices=("grok", "claude", "codex"), default="grok")
    ap.add_argument("--rename", action="append", default=[],
                    help="old=new export rename between the original and the rebuild (oracle aliasing)")
    ap.add_argument("--codex-model", default="gpt-6-luna")
    ap.add_argument("--codex-effort", default="xhigh")
    ap.add_argument("--model", default="claude-sonnet-5", help="claude host only (grok uses grok_step defaults)")
    ap.add_argument("--max-budget-usd", type=float, default=15.0, help="claude host only")
    ap.add_argument("--forbid", action="append", default=[],
                    help="string whose appearance in the builder's tool calls voids the run (original name, path)")
    ap.add_argument("--forbid-dep", action="append", default=[],
                    help="package name the rebuild must not depend on (the original's published package)")
    args = ap.parse_args()
    RENAMES.extend(args.rename)
    out = args.out.resolve()
    work = out / "work"
    if not args.score_only:
        work.mkdir(parents=True)
        (work / "SPEC.md").write_text(builder_view(args.spec.read_text()))
        subprocess.run(["git", "init", "-q"], cwd=work, check=True)
        if args.host == "grok":
            subprocess.run([sys.executable, str(HERE / "grok_step.py"), "--cwd", str(work),
                            "--prompt", str(HERE.parent / "prompts" / "build.md"), "--out", str(out / "step"),
                            "--no-web", "--max-turns", "200"], check=False)
        elif args.host == "codex":
            codex_step(work, out / "step", args.codex_model, args.codex_effort)
        else:
            claude_step(work, out / "step", args.model, args.max_budget_usd)
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
        elif isinstance(event, dict) and isinstance(event.get("item"), dict):  # Codex exec --json
            item = event["item"]
            if item.get("type") == "agent_message" or item.get("type") == "reasoning":
                prose += json.dumps(item.get("text") or "").lower()
            else:
                tools += json.dumps({k: item.get(k) for k in ("command", "changes", "path", "query")}).lower()
        elif isinstance(event, dict) and event.get("type") == "assistant":  # Claude stream-json
            for block in (event.get("message") or {}).get("content") or []:
                if isinstance(block, dict) and block.get("type") == "tool_use":
                    tools += json.dumps(block.get("input") or "").lower()
                elif isinstance(block, dict):
                    prose += json.dumps(block.get("text") or block.get("thinking") or "").lower()
        else:
            prose += line.lower()
    leaks = [f for f in args.forbid if f.lower() in tools]
    recognised = [f for f in args.forbid if f.lower() in prose]
    pkg = work / "package.json"
    if pkg.is_file():
        data = json.loads(pkg.read_text())
        deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
        leaks += [f"depends on {d}" for d in deps if d.lower() in (f.lower() for f in args.forbid + args.forbid_dep)]
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
