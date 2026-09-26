#!/usr/bin/env python3
"""Run ShipLoop end to end from one prompt in a new, empty directory.

Each run creates a fresh empty working directory, invokes the ShipLoop skill
there with one headless host process, shows its progress live, and grades:

  invoked   the host registered the invoked skill command, so the prompt went
            to the skill (Claude: /skill-craft:shiploop; Grok: /shiploop, since
            Grok does not namespace plugin skills)
  plugin    exactly one skill-craft plugin loaded, and it is the build under test
  process   the host exited 0 within the timeout
  shiploop  a ShipLoop state.md under the output directory reports status
            "done" and its report.html exists
  checks    every case check command exits 0 in the working directory

The default host is Grok at medium reasoning effort. By default the run tests a
fresh build of this checkout (scripts/build-packages.py), never an installed
plugin, and isolates the host from the user's configuration:

  grok    a throwaway HOME whose .grok holds only a symlink to the user's
          auth.json and the candidate plugin, so neither the user's Grok
          plugins nor anything Grok inherits from ~/.claude load, and nothing
          is installed into the real profile
  claude  --setting-sources project,local plus --plugin-dir, so the user's
          plugins and hooks stay out (~/.claude/CLAUDE.md still loads)

Nothing is resumed or retried. Every attempt keeps its prompt, argv, event
stream, stderr and result.json in a new output directory outside the checkout.
This launches a real model and costs money; it is never part of default CI.

  python3 test/shiploop_e2e/run.py --case battleship
  python3 test/shiploop_e2e/run.py --case hello --host claude
  python3 test/shiploop_e2e/run.py --prompt "..." --check "python3 -m unittest"
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import secrets
import signal
import subprocess
import sys
import tempfile
import threading
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "skills/shiploop/scripts"))
sys.path.insert(0, str(HERE))
import hosts  # noqa: E402
import shiploop_store as store  # noqa: E402

CASES = HERE / "cases.json"
PLUGIN_NAME = "skill-craft"
# Grok does not namespace plugin skills; Claude prefixes them with the plugin name.
SKILL_COMMAND = {"grok": "shiploop", "claude": "skill-craft:shiploop"}


def load_case(args) -> tuple[str, str, list[str]]:
    if args.prompt:
        return "custom", args.prompt, args.check or []
    cases = json.loads(CASES.read_text())
    if args.case not in cases:
        raise SystemExit(f"unknown case {args.case!r}; known: {', '.join(sorted(cases))}")
    case = cases[args.case]
    return args.case, case["prompt"], case["checks"] + (args.check or [])


def new_output_dir(requested: Path | None, name: str) -> Path:
    if requested is None:
        stamp = time.strftime("%Y%m%d-%H%M%S")
        requested = Path(tempfile.gettempdir()) / "shiploop-e2e" / f"{name}-{stamp}-{secrets.token_hex(3)}"
    out = requested.expanduser().resolve()
    if out == ROOT or ROOT in out.parents:
        raise SystemExit(f"output must be outside the checkout: {out}")
    out.mkdir(parents=True, exist_ok=False)
    return out


def build_candidate(out: Path) -> Path:
    """A fresh package build of this checkout, working-tree changes included."""
    subprocess.run([sys.executable, "-B", str(ROOT / "scripts/build-packages.py"), str(out / "build")],
                   check=True, stdout=subprocess.DEVNULL)
    return out / "build" / "plugins" / PLUGIN_NAME


class LiveView:
    """One short line per assistant message or tool call, from either host's stream."""

    def __init__(self, start: float, enabled: bool):
        self.start, self.enabled, self.text = start, enabled, ""

    def emit(self, line: str):
        if self.enabled:
            print(f"[{time.time() - self.start:6.0f}s] {line}", flush=True)

    def flush_text(self):
        if self.text.strip():
            self.emit("say   " + " ".join(self.text.split())[:160])
        self.text = ""

    def event(self, event: dict):
        kind = event.get("type")
        if kind == "text" and isinstance(event.get("data"), str):  # Grok text delta
            self.text += event["data"]
            return
        if kind in ("thought", "usage"):
            return
        self.flush_text()
        if kind == "assistant":  # Claude whole message
            for block in (event.get("message") or {}).get("content") or []:
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "text":
                    self.text = block.get("text", "")
                    self.flush_text()
                elif block.get("type") == "tool_use":
                    self.tool(block.get("name"), block.get("input"))
        elif kind == "tool_call":  # Grok
            name = next((event[k] for k in ("toolName", "tool_name", "tool", "name", "title") if event.get(k)), "?")
            self.tool(name, event.get("rawInput"))
        elif kind in ("result", "end"):
            self.emit(f"done  {event.get('subtype') or event.get('stopReason')} turns={event.get('num_turns')} "
                      f"cost=${event.get('total_cost_usd')}")

    def tool(self, name, arg):
        arg = arg if isinstance(arg, dict) else {}
        detail = next((arg[k] for k in ("command", "cmd", "file_path", "target_file", "target_directory", "pattern",
                                    "path", "skill", "description") if arg.get(k)), "")
        self.emit(f"tool  {name}: " + " ".join(str(detail).split())[:140])


def launch(argv: list[str], work: Path, out: Path, env: dict, timeout: int, watch: bool) -> dict:
    # The skill must start from a directory with nothing in it.
    leftover = sorted(p.name for p in work.iterdir())
    if leftover:
        raise SystemExit(f"working directory is not empty: {leftover}")
    start = time.time()
    view = LiveView(start, watch)
    with (out / "events.jsonl").open("wb") as events, (out / "stderr.txt").open("wb") as stderr:
        proc = subprocess.Popen(argv, cwd=work, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                stderr=stderr, env=env, start_new_session=True)

        def pump():
            for raw in proc.stdout:
                events.write(raw)
                events.flush()
                try:
                    event = json.loads(raw)
                except ValueError:
                    continue
                if isinstance(event, dict):
                    view.event(event)
            view.flush_text()

        reader = threading.Thread(target=pump, daemon=True)
        reader.start()
        try:
            proc.wait(timeout=timeout)
            status = "exited" if proc.returncode == 0 else "failed"
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            proc.wait()
            status = "timeout"
        reader.join(timeout=10)
        proc.stdout.close()
    return {"status": status, "returncode": proc.returncode,
            "elapsed_seconds": round(time.time() - start, 1)}


def summarize_events(path: Path) -> dict:
    """What the host reported: commands, plugins, model, turns and cost."""
    seen: dict = {"commands": [], "plugins": []}
    for line in path.read_text(errors="replace").splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if not isinstance(event, dict):
            continue
        kind = event.get("type")
        if kind == "system" and event.get("subtype") == "init":  # Claude
            seen["model"] = event.get("model")
            seen["commands"] = event.get("slash_commands") or []
            seen["plugins"] = [p for p in event.get("plugins") or [] if isinstance(p, dict)]
        elif kind == "available_commands" and not seen["commands"]:  # Grok
            seen["commands"] = [c for c in event.get("commands") or [] if isinstance(c, str)]
        elif kind in ("result", "end"):
            seen.update(num_turns=event.get("num_turns"), cost_usd=event.get("total_cost_usd"),
                        stop=event.get("subtype") or event.get("stopReason"))
    return seen


def model_visible_output(raw) -> str:
    """The text a host showed the model for one tool result.

    Grok stores shell output twice: `output` as a list of byte values and
    `output_for_prompt` as the (possibly truncated) text the model saw.
    """
    if isinstance(raw, str):
        return raw
    if isinstance(raw, dict):
        for key in ("output_for_prompt", "content", "text"):
            if isinstance(raw.get(key), str):
                return raw[key]
    return ""


def host_truncations(events_path: Path) -> list[dict]:
    """Tool results the host cut off before the model saw them (Grok's ~20 KB cap)."""
    calls, cut = {}, {}
    for line in events_path.read_text(errors="replace").splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if not isinstance(event, dict):
            continue
        if event.get("type") == "tool_call":
            arg = event.get("rawInput") if isinstance(event.get("rawInput"), dict) else {}
            calls[event.get("toolCallId")] = str(arg.get("command") or arg.get("target_file") or "")[-160:]
        elif event.get("type") == "tool_call_update" and isinstance(event.get("rawOutput"), dict):
            raw = event["rawOutput"]
            if raw.get("truncated"):
                cut[event.get("toolCallId")] = {"total_bytes": raw.get("total_bytes"),
                                                "shown_chars": len(model_visible_output(raw))}
    return [dict(item, call=calls.get(call_id, "")) for call_id, item in cut.items()]


def write_transcript(events_path: Path, path: Path) -> None:
    """A readable transcript (messages and tool calls) for people and the reviewer."""
    lines: list[str] = []
    view = LiveView(0.0, False)
    view.emit = lambda line: lines.append(line)  # type: ignore[method-assign]
    for raw in events_path.read_text(errors="replace").splitlines():
        try:
            event = json.loads(raw)
        except ValueError:
            continue
        if isinstance(event, dict):
            if event.get("type") == "user":  # Claude tool results
                for block in (event.get("message") or {}).get("content") or []:
                    if isinstance(block, dict) and block.get("type") == "tool_result":
                        content = block.get("content")
                        text = content if isinstance(content, str) else json.dumps(content)
                        lines.append("out   " + " ".join(str(text).split())[:400])
            elif event.get("type") == "tool_call_update" and event.get("status"):  # Grok
                shown = model_visible_output(event.get("rawOutput"))
                if shown:
                    lines.append(f"out   {event.get('status')} " + " ".join(shown[:400].split()))
            view.event(event)
    view.flush_text()
    path.write_text("\n".join(lines) + "\n")


def grade_claude_plugin(plugins: list[dict], plugin_dir: Path | None) -> dict:
    paths = [p.get("path") for p in plugins if p.get("name") == PLUGIN_NAME]
    if plugin_dir is None:
        return {"pass": len(paths) == 1, "loaded": paths}
    wanted = str(plugin_dir.resolve())
    return {"pass": paths == [wanted], "loaded": paths, "wanted": wanted}


def grade_shiploop(out: Path) -> dict:
    """ShipLoop's run state, wherever the agent put it under the output directory.

    The skill may keep its run inside the repository (work/.shiploop) or in an
    external workspace root beside it (for example <out>/.shiploop-runs/<name>/run);
    the throwaway home/ and the plugin build/ are not searched.
    """
    runs = []
    for state_path in sorted(out.rglob("state.md")):
        relative = state_path.relative_to(out).parts
        if relative[0] in ("home", "build"):
            continue
        try:
            state = store.read_record(state_path)
        except store.StorageError:
            continue
        if isinstance(state, dict) and "status" in state:
            runs.append({"run_dir": str(state_path.parent), "status": state.get("status"),
                         "stage": state.get("stage"),
                         "report_html": (state_path.parent / "report.html").is_file()})
    if not runs:
        return {"pass": False, "reason": "no ShipLoop state.md under the output directory"}
    done = [run for run in runs if run["status"] == "done" and run["report_html"]]
    chosen = done[0] if done else runs[0]
    # ShipLoop builds in its own worktree beside the run and returns it to the
    # source only at release; name it so an unreturned product can be inspected.
    worktree = Path(chosen["run_dir"]).parent / "worktree"
    return {"pass": bool(done), **chosen, "runs": len(runs),
            "worktree": str(worktree) if worktree.is_dir() else None}


def run_checks(work: Path, checks: list[str], timeout: int = 180) -> list[dict]:
    results = []
    for command in checks:
        try:
            done = subprocess.run(command, shell=True, cwd=work, capture_output=True,
                                  text=True, timeout=timeout)
            code, output = done.returncode, (done.stdout + done.stderr)[-2000:]
        except subprocess.TimeoutExpired:
            code, output = None, "timeout"
        results.append({"command": command, "pass": code == 0, "returncode": code, "output": output})
    return results


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--case", default="hello", help="case name from cases.json (default: hello)")
    p.add_argument("--prompt", help="run this prompt instead of a named case")
    p.add_argument("--check", action="append", help="extra shell check run in the work dir (repeatable)")
    p.add_argument("--output", type=Path, help="new directory for this attempt (default: under $TMPDIR)")
    p.add_argument("--host", choices=sorted(hosts.HOST_DEFAULTS), default="grok")
    p.add_argument("--model", help="default: grok-4.7 (grok) or sonnet (claude)")
    p.add_argument("--effort", help="reasoning effort; default: medium (grok), host default (claude)")
    p.add_argument("--skill", help="command that invokes ShipLoop; default: shiploop (grok), skill-craft:shiploop (claude)")
    p.add_argument("--plugin-dir", type=Path, help="skill-craft plugin build to test (default: build this checkout)")
    p.add_argument("--installed", action="store_true",
                   help="claude only: use the installed skill-craft plugin instead of a build")
    p.add_argument("--max-turns", type=int, default=10000)
    p.add_argument("--max-budget-usd", type=float, default=10.0, help="claude only; grok has no spend cap")
    p.add_argument("--permission-mode", default="auto")
    p.add_argument("--timeout", type=int, default=10800, help="seconds before the host is killed")
    p.add_argument("--quiet", action="store_true", help="do not print the live progress view")
    p.add_argument("--grok-bin", default="grok")
    p.add_argument("--claude-bin", default="claude")
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    defaults = hosts.HOST_DEFAULTS[args.host]
    args.model = args.model or defaults["model"]
    args.effort = args.effort or defaults["effort"]
    args.skill = args.skill or SKILL_COMMAND[args.host]
    if args.installed and (args.host != "claude" or args.plugin_dir):
        raise SystemExit("--installed is claude-only and excludes --plugin-dir")
    if args.plugin_dir and not (args.plugin_dir / ".claude-plugin" / "plugin.json").is_file():
        raise SystemExit(f"--plugin-dir has no .claude-plugin/plugin.json: {args.plugin_dir}")

    name, prompt, checks = load_case(args)
    out = new_output_dir(args.output, name)
    work = out / "work"
    work.mkdir()
    plugin_dir = None if args.installed else (args.plugin_dir or build_candidate(out))
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0", NO_COLOR="1")
    plugin = None
    if args.host == "grok":
        env = hosts.grok_env(out / "home")
        plugin = hosts.grok_install(env, plugin_dir, args.grok_bin)
    cli = hosts.argv_for(args.host, prompt=f"/{args.skill} {prompt}", prompt_file=out / "host-prompt.txt",
                         cwd=work, model=args.model, effort=args.effort,
                         permission_mode=args.permission_mode, max_turns=args.max_turns,
                         max_budget_usd=args.max_budget_usd,
                         plugin_dir=plugin_dir if args.host == "claude" else None,
                         grok_bin=args.grok_bin, claude_bin=args.claude_bin)
    (out / "prompt.txt").write_text(prompt + "\n")
    (out / "invocation.json").write_text(json.dumps(
        {"case": name, "host": args.host, "model": args.model, "effort": args.effort, "argv": cli,
         "cwd": str(work), "plugin_dir": str(plugin_dir) if plugin_dir else None, "checks": checks},
        indent=2) + "\n")
    if not args.quiet:
        print(f"shiploop e2e case={name} host={args.host} model={args.model} effort={args.effort} "
              f"work={work}", flush=True)

    process = launch(cli, work, out, env, args.timeout, watch=not args.quiet)
    process["pass"] = process["status"] == "exited"
    cli_seen = summarize_events(out / "events.jsonl")
    write_transcript(out / "events.jsonl", out / "transcript.md")
    cli_seen["truncated_outputs"] = host_truncations(out / "events.jsonl")
    invoked = {"pass": args.skill in cli_seen.pop("commands"), "skill": args.skill}
    plugins = cli_seen.pop("plugins")
    if plugin is None:
        plugin = grade_claude_plugin(plugins, plugin_dir)
    shiploop = grade_shiploop(out)
    check_results = run_checks(work, checks)
    if not shiploop["pass"] and shiploop.get("worktree"):
        # Informational only: does the unreturned candidate already pass?
        shiploop["worktree_checks"] = [{k: c[k] for k in ("command", "pass")}
                                       for c in run_checks(Path(shiploop["worktree"]), checks)]
    verdicts = [invoked["pass"], plugin["pass"], process["pass"], shiploop["pass"],
                *(c["pass"] for c in check_results)]
    result = {"case": name, "host": args.host, "model": args.model, "effort": args.effort,
              "pass": all(verdicts), "invoked": invoked, "plugin": plugin, "process": process,
              "shiploop": shiploop, "checks": check_results, "cli": cli_seen, "output": str(out)}
    (out / "result.json").write_text(json.dumps(result, indent=2) + "\n")

    mark = lambda ok: "PASS" if ok else "FAIL"  # noqa: E731
    print(f"{mark(result['pass'])}  shiploop e2e case={name} host={args.host}  output={out}")
    print(f"  invoked   {mark(invoked['pass'])}  /{args.skill}")
    print(f"  plugin    {mark(plugin['pass'])}  {', '.join(map(str, plugin['loaded'])) or 'none loaded'}")
    print(f"  process   {mark(process['pass'])}  {process['status']} rc={process['returncode']} "
          f"{process['elapsed_seconds']}s cost=${cli_seen.get('cost_usd')}")
    print(f"  shiploop  {mark(shiploop['pass'])}  {shiploop.get('status') or shiploop.get('reason')}")
    if shiploop.get("worktree_checks") is not None:
        passed = sum(c["pass"] for c in shiploop["worktree_checks"])
        print(f"            unreturned product in {shiploop['worktree']}: "
              f"{passed}/{len(shiploop['worktree_checks'])} checks pass there")
    if cli_seen["truncated_outputs"]:
        print(f"  note      host truncated {len(cli_seen['truncated_outputs'])} tool outputs the model saw")
    for check in check_results:
        print(f"  check     {mark(check['pass'])}  {check['command']}")
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
