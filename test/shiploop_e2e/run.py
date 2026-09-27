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
  committed the source checkout ends committed: HEAD moved past where the run
            started and no product path is left uncommitted (logs aside)
  checks    every case check command exits 0 in the working directory

A follow-on case (`follows` in cases.json) runs a second feature in a copy of an
earlier run's source checkout (--continue-from <earlier output>), to see whether
ShipLoop builds on what the first run decided. Its checks are the followed
case's checks (regression), its own feature checks and retention checks, which
get $PRIOR_WORK (the earlier checkout, read only).

Besides the verdicts, metrics.json records where ShipLoop spent turns, tokens,
cost and time (per accepted stage), its failed commands, host truncations,
compactions and the knowledge-home facts (see metrics.py).

The default host is Grok at medium reasoning effort. By default the run tests
what the whichguy marketplace publishes now (--source marketplace, gated on
local HEAD == origin/main and matching versions); --source checkout builds
this checkout instead. The host is isolated from the user's configuration:

  grok    a throwaway HOME whose .grok holds only a symlink to the user's
          auth.json and the plugin under test, so neither the user's Grok
          plugins nor anything Grok inherits from ~/.claude load, and nothing
          is installed into the real profile
  claude  --setting-sources project,local plus --plugin-dir, so the user's
          plugins and hooks stay out (~/.claude/CLAUDE.md still loads)

A Grok session that ends while the ShipLoop run is still active is resumed
(bounded by --max-resumes). Every attempt keeps its prompt, argv, event
stream, arrival timeline, stderr, metrics.json and result.json in a new
output directory outside the checkout.
This launches a real model and costs money; it is never part of default CI.

  python3 test/shiploop_e2e/run.py --case battleship
  python3 test/shiploop_e2e/run.py --case battleship-scoring --continue-from <battleship output>
  python3 test/shiploop_e2e/run.py --case hello --host claude
  python3 test/shiploop_e2e/run.py --prompt "..." --check "python3 -m unittest"
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import secrets
import shutil
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
import metrics  # noqa: E402
import shiploop_knowledge_home as knowledge_home  # noqa: E402
import shiploop_store as store  # noqa: E402

CASES = HERE / "cases.json"
SUITES = HERE / "suites.json"
BASELINES = HERE / "baselines.jsonl"
PLUGIN_NAME = "skill-craft"
# Grok does not namespace plugin skills; Claude prefixes them with the plugin name.
SKILL_COMMAND = {"grok": "shiploop", "claude": "skill-craft:shiploop"}


def load_case(args) -> tuple[str, str, list[str], str | None]:
    """Name, prompt, checks and the case it follows (None for a fresh start)."""
    if args.prompt:
        return "custom", args.prompt, args.check or [], None
    cases = json.loads(CASES.read_text())
    if args.case not in cases:
        raise SystemExit(f"unknown case {args.case!r}; known: {', '.join(sorted(cases))}")
    case = cases[args.case]
    follows = case.get("follows")
    regression = cases[follows]["checks"] if follows else []
    return args.case, case["prompt"], regression + case["checks"] + case.get("retention", []) + (args.check or []), follows


def continue_from(prior: Path, work: Path) -> dict:
    """Copy an earlier run's source checkout into `work`, as that run left it.

    The copy keeps .git and every untracked file; worktree records point at the
    earlier run's execution worktree, so they are dropped (the branches stay).
    """
    source = prior / "work"
    if not (source / ".git").exists():
        raise SystemExit(f"--continue-from has no work/.git: {prior}")
    work.rmdir()
    shutil.copytree(source, work, symlinks=True)
    shutil.rmtree(work / ".git" / "worktrees", ignore_errors=True)
    subprocess.run(["git", "-C", str(work), "worktree", "prune"], check=False, capture_output=True)
    earlier = json.loads((prior / "result.json").read_text()) if (prior / "result.json").is_file() else {}
    head = subprocess.run(["git", "-C", str(work), "rev-parse", "HEAD"], capture_output=True, text=True)
    return {"prior": str(prior), "start_head": head.stdout.strip() if head.returncode == 0 else None, "prior_case": earlier.get("case"), "prior_pass": earlier.get("pass"),
            "prior_turns": (earlier.get("metrics") or earlier.get("cli") or {}).get("turns")
            or (earlier.get("cli") or {}).get("num_turns"),
            "prior_cost_usd": (earlier.get("metrics") or earlier.get("cli") or {}).get("cost_usd")}


def new_output_dir(requested: Path | None, name: str) -> Path:
    if requested is None:
        stamp = time.strftime("%Y%m%d-%H%M%S")
        requested = Path(tempfile.gettempdir()) / "shiploop-e2e" / f"{name}-{stamp}-{secrets.token_hex(3)}"
    out = requested.expanduser().resolve()
    if out == ROOT or ROOT in out.parents:
        raise SystemExit(f"output must be outside the checkout: {out}")
    out.mkdir(parents=True, exist_ok=False)
    return out


def git(*args: str) -> str:
    return subprocess.run(["git", "-C", str(ROOT), *args], check=True, capture_output=True, text=True).stdout


def card_version(card: Path) -> str | None:
    """The top-level `version:` of a SKILL.md front matter."""
    match = re.match(r"---\n(?:(?!---\n).*\n)*?version:[ \t]*(\S+)", card.read_text()) if card.is_file() else None
    return match.group(1) if match else None


def released_versions() -> dict:
    """What the marketplace serves now: the catalog and ShipLoop versions on origin/main."""
    git("fetch", "-q", "origin")
    catalog = json.loads(git("show", "origin/main:.claude-plugin/marketplace.json"))
    plugin = next(p for p in catalog["plugins"] if p["name"] == PLUGIN_NAME)
    shiploop = re.search(r"^version:[ \t]*(\S+)", git("show", f"origin/main:plugins/{PLUGIN_NAME}/skills/shiploop/SKILL.md"), re.M)
    # A pending change note on main is source the marketplace does not serve yet: release.py has not run.
    pending = [name for name in git("ls-tree", "-r", "--name-only", "origin/main", "changes/").split()
               if name.endswith(".md") and name != "changes/README.md"]
    return {"origin_main": git("rev-parse", "origin/main").strip(), "local_head": git("rev-parse", "HEAD").strip(),
            "catalog_version": plugin.get("version"), "shiploop_version": shiploop.group(1) if shiploop else None,
            "unreleased": pending}


def version_gate(released: dict, plugin_version: str | None, shiploop_version: str | None) -> list[str]:
    """Why a marketplace run would not test what main and the marketplace publish, if at all."""
    problems = []
    if released.get("unreleased"):
        problems.append("origin/main has unreleased changes (" + ", ".join(released["unreleased"][:5])
                        + "): run scripts/release.py and push so the marketplace serves them")
    if released["local_head"] != released["origin_main"]:
        problems.append(f"local HEAD {released['local_head'][:8]} is not origin/main {released['origin_main'][:8]}")
    if plugin_version != released["catalog_version"]:
        problems.append(f"installed skill-craft {plugin_version} is not the catalog's {released['catalog_version']}")
    if shiploop_version != released["shiploop_version"]:
        problems.append(f"installed ShipLoop {shiploop_version} is not the released {released['shiploop_version']}")
    return problems


def export_released(out: Path) -> Path:
    """origin/main's plugins/skill-craft, byte for byte: the payload the marketplace serves."""
    target = out / "marketplace"
    target.mkdir()
    archive = subprocess.run(["git", "-C", str(ROOT), "archive", "origin/main", f"plugins/{PLUGIN_NAME}"],
                             check=True, capture_output=True).stdout
    subprocess.run(["tar", "-x", "-C", str(target)], input=archive, check=True)
    return target / "plugins" / PLUGIN_NAME


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


def launch(argv: list[str], work: Path, out: Path, env: dict, timeout: int, watch: bool,
           first: bool = True, fresh: bool = True) -> dict:
    if first and fresh:
        # The skill must start from a directory with nothing in it.
        leftover = sorted(p.name for p in work.iterdir())
        if leftover:
            raise SystemExit(f"working directory is not empty: {leftover}")
    start = time.time()
    view = LiveView(start, watch)
    mode = "wb" if first else "ab"  # a resumed session appends to the same streams
    events_path = out / "events.jsonl"
    line = 0 if first else sum(1 for _ in events_path.open("rb"))
    # A run takes an hour or more; on macOS keep the machine from idle-sleeping, which
    # otherwise freezes the host mid-stage and stretches every stage timing.
    caffeinate = shutil.which("caffeinate")
    if caffeinate:
        argv = [caffeinate, "-i", *argv]
    with events_path.open(mode) as events, (out / "stderr.txt").open(mode) as stderr, \
            (out / "timeline.jsonl").open("w" if first else "a") as stamps:
        proc = subprocess.Popen(argv, cwd=work, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                stderr=stderr, env=env, start_new_session=True)

        def pump():
            nonlocal line
            for raw in proc.stdout:
                events.write(raw)
                events.flush()
                number, line = line, line + 1
                try:
                    event = json.loads(raw)
                except ValueError:
                    continue
                if isinstance(event, dict):
                    # Grok events carry no time; stamp the ones metrics.py attributes.
                    if event.get("type") not in ("text", "thought"):
                        stamps.write(json.dumps({"line": number, "t": round(time.time(), 3)}) + "\n")
                        stamps.flush()
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
            seen.setdefault("sessions", []).append(
                {"num_turns": event.get("num_turns"), "cost_usd": event.get("total_cost_usd"),
                 "stop": event.get("subtype") or event.get("stopReason")})
            seen.update(stop=event.get("subtype") or event.get("stopReason"))
    ended = seen.get("sessions") or []
    if ended:
        # Each host session reports its own totals; a resumed run adds them up.
        seen["num_turns"] = sum(s["num_turns"] or 0 for s in ended)
        seen["cost_usd"] = round(sum(s["cost_usd"] or 0 for s in ended), 4)
    return seen


def last_session_id(events_path: Path) -> str | None:
    """The host session to resume: the last session id the event stream carried."""
    found = None
    for line in events_path.read_text(errors="replace").splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if isinstance(event, dict) and isinstance(event.get("sessionId"), str):
            found = event["sessionId"]
    return found


def resume_prompt(out: Path, run_dir: str | None) -> str:
    if run_dir is None:
        return ("This session ended before the ShipLoop run was started. Continue the original "
                "request now: start the ShipLoop run as its skill directs and follow each packet to "
                "the end of the run. Never end the turn while a ShipLoop command is still running.")
    cli = next((out / "home" / ".grok" / "installed-plugins").glob("skill-craft-*/skills/shiploop/scripts/shiploop"),
               None)
    command = f'python3 "{cli}" next --run-dir "{run_dir}"' if cli else f'shiploop next --run-dir "{run_dir}"'
    return ("This session ended while the ShipLoop run was still active. Continue it now: run "
            f"`{command}` and follow the packet it prints, to the end of the run. Never end the turn "
            "while a ShipLoop command is still running.")


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
                         "stage": state.get("stage"), "revision": state.get("revision"),
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


def knowledge_facts(work: Path) -> dict:
    """How the run left the source checkout: knowledge home, commits and branches.

    Informational: it shows whether a later run could inherit the spec and
    environment notes from the repository itself.
    """
    def g(*args: str) -> str:
        done = subprocess.run(["git", "-C", str(work), *args], capture_output=True, text=True)
        return done.stdout if done.returncode == 0 else ""

    spec = work / "docs" / "shiploop" / "spec.md"
    status = g("status", "--porcelain", "--untracked-files=all").splitlines()
    untracked = [ln[3:] for ln in status if ln.startswith("??")]
    # Logs a server or test run leaves behind are not product; anything else uncommitted is.
    uncommitted = [ln[3:] for ln in status if not ln[3:].endswith(".log")]
    return {"spec": spec.is_file(),
            "head": g("rev-parse", "HEAD").strip() or None,
            "uncommitted": uncommitted,
            "spec_tracked": bool(g("ls-files", "--", "docs/shiploop/spec.md").strip()),
            "requirement_ids": sorted(set(knowledge_home._REQUIREMENT_ID.findall(spec.read_text())),
                                      key=lambda value: int(value.split("-")[1])) if spec.is_file() else [],
            "head_commits": len(g("rev-list", "HEAD").split()),
            "untracked_files": len(untracked),
            "branches": g("branch", "--format=%(refname:short)").split()}


def untracked(work: Path) -> set[str]:
    done = subprocess.run(["git", "-C", str(work), "status", "--porcelain", "--untracked-files=all"],
                          capture_output=True, text=True)
    return {ln[3:] for ln in done.stdout.splitlines() if ln.startswith("?? ")} if done.returncode == 0 else set()


def run_checks(work: Path, checks: list[str], timeout: int = 180, env: dict | None = None) -> list[dict]:
    """Run each check in `work`, then delete any untracked file the checks created.

    A follow-on run copies this checkout; a leftover (a server log, say) would
    make ShipLoop see a dirty start and return only a working-tree delta.
    """
    before = untracked(work)
    results = []
    for command in checks:
        try:
            done = subprocess.run(command, shell=True, cwd=work, capture_output=True, stdin=subprocess.DEVNULL,
                                  text=True, timeout=timeout,
                                  env=dict(os.environ, E2E_CHECKS=str(HERE / "checks"), **(env or {})))
            code, output = done.returncode, (done.stdout + done.stderr)[-2000:]
        except subprocess.TimeoutExpired:
            code, output = None, "timeout"
        results.append({"command": command, "pass": code == 0, "returncode": code, "output": output})
    for leftover in sorted(untracked(work) - before):
        (work / leftover).unlink(missing_ok=True)
    return results


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--case", default="hello", help="case name from cases.json (default: hello)")
    p.add_argument("--suite", help="run a suite from suites.json in order (focused: one style in depth; "
                                   "breadth: one case per style); --output becomes the suite directory")
    p.add_argument("--baseline", type=Path, default=BASELINES,
                   help="append one summary row per run to this file (default: the committed baselines.jsonl)")
    p.add_argument("--prompt", help="run this prompt instead of a named case")
    p.add_argument("--continue-from", type=Path,
                   help="an earlier run's output directory: start in a copy of its source checkout "
                        "(required by follow-on cases, which name the case they follow)")
    p.add_argument("--check", action="append", help="extra shell check run in the work dir (repeatable)")
    p.add_argument("--output", type=Path, help="new directory for this attempt (default: under $TMPDIR)")
    p.add_argument("--host", choices=sorted(hosts.HOST_DEFAULTS), default="grok")
    p.add_argument("--model", help="default: grok-4.7 (grok) or sonnet (claude)")
    p.add_argument("--effort", help="reasoning effort; default: medium (grok), host default (claude)")
    p.add_argument("--skill", help="command that invokes ShipLoop; default: shiploop (grok), skill-craft:shiploop (claude)")
    p.add_argument("--source", choices=("marketplace", "checkout"), default="marketplace",
                   help="marketplace (default): test what the whichguy marketplace publishes now, gated on "
                        "local HEAD == origin/main and matching versions; checkout: build this checkout")
    p.add_argument("--plugin-dir", type=Path, help="test this skill-craft plugin build (implies --source checkout)")
    p.add_argument("--max-turns", type=int, default=10000)
    p.add_argument("--max-budget-usd", type=float, default=10.0, help="claude only; grok has no spend cap")
    p.add_argument("--permission-mode", default="auto")
    p.add_argument("--timeout", type=int, default=10800, help="seconds before the host is killed")
    p.add_argument("--max-resumes", type=int, default=20,
                   help="grok only: resume the same session this many times while ShipLoop is still active")
    p.add_argument("--quiet", action="store_true", help="do not print the live progress view")
    p.add_argument("--suite-name", help=argparse.SUPPRESS)
    p.add_argument("--grok-bin", default="grok")
    p.add_argument("--claude-bin", default="claude")
    return p


def baseline_row(result: dict, style: str | None, suite: str | None) -> dict:
    """One comparable summary of a run: the per-case history the suites judge against (SPEC: E2E suites)."""
    m = result.get("metrics") or {}
    versions = result.get("versions") or {}
    return {"date": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "case": result.get("case"), "style": style,
            "suite": suite, "source": versions.get("source"), "plugin_version": versions.get("plugin_version"),
            "shiploop_version": versions.get("shiploop_version"), "pass": result.get("pass"),
            "verdicts": {k: (result.get(k) or {}).get("pass") for k in ("invoked", "plugin", "process",
                                                                       "shiploop", "committed")},
            "checks_passed": sum(bool(c.get("pass")) for c in result.get("checks") or []),
            "checks": len(result.get("checks") or []),
            "turns": m.get("turns"), "cost_usd": m.get("cost_usd"),
            "sessions": len((result.get("process") or {}).get("sessions") or []),
            "cancelled_tool_calls": m.get("cancelled_tool_calls"), "model_glue": m.get("model_glue"),
            "shiploop_failures": m.get("shiploop_failures"), "compactions": m.get("compactions"),
            "truncated_outputs": m.get("truncated_outputs"), "narrative": m.get("narrative"),
            "output": result.get("output")}


def previous_row(path: Path, case: str, source: str | None) -> dict | None:
    """The last recorded row for this case from the same source (marketplace vs checkout)."""
    if not path.is_file():
        return None
    found = None
    for line in path.read_text().splitlines():
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if row.get("case") == case and row.get("source") == source:
            found = row
    return found


def run_suite(args, argv: list[str]) -> int:
    """Run a suite's cases in order; a follow-on starts from its predecessor and is skipped if it failed."""
    suites = json.loads(SUITES.read_text())
    if args.suite not in suites or args.suite.startswith("_"):
        raise SystemExit(f"unknown suite {args.suite!r}; known: {', '.join(k for k in suites if not k.startswith('_'))}")
    cases = json.loads(CASES.read_text())
    base = new_output_dir(args.output, "suite-" + args.suite)
    passthrough, skip = [], {"--suite", "--output", "--case", "--continue-from"}
    it = iter(argv)
    for token in it:
        name = token.split("=", 1)[0]
        if name in skip:
            if "=" not in token:
                next(it, None)
            continue
        passthrough.append(token)
    outputs: dict[str, Path] = {}
    summary = []
    for case in suites[args.suite]["cases"]:
        follows = cases[case].get("follows")
        prior = outputs.get(follows) if follows else None
        if follows and prior is None:
            summary.append({"case": case, "skipped": f"its predecessor {follows!r} is not in this suite run"})
            continue
        if prior is not None and not json.loads((prior / "result.json").read_text()).get("pass"):
            summary.append({"case": case, "skipped": f"its predecessor {follows!r} failed; nothing to build on"})
            continue
        out = base / case
        case_argv = [*passthrough, "--case", case, "--output", str(out), "--suite-name", args.suite]
        if prior is not None:
            case_argv += ["--continue-from", str(prior)]
        code = main(case_argv)
        outputs[case] = out
        summary.append({"case": case, "pass": code == 0, "output": str(out)})
    (base / "suite-result.json").write_text(json.dumps({"suite": args.suite, "cases": summary}, indent=2) + "\n")
    print(f"suite {args.suite}: " + ", ".join(
        f"{row['case']} {'SKIP' if 'skipped' in row else 'PASS' if row['pass'] else 'FAIL'}" for row in summary))
    return 0 if all(row.get("pass") for row in summary) else 1


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    args = parser().parse_args(argv)
    if args.suite:
        return run_suite(args, argv)
    defaults = hosts.HOST_DEFAULTS[args.host]
    args.model = args.model or defaults["model"]
    args.effort = args.effort or defaults["effort"]
    args.skill = args.skill or SKILL_COMMAND[args.host]
    if args.plugin_dir:
        args.source = "checkout"
    if args.plugin_dir and not (args.plugin_dir / ".claude-plugin" / "plugin.json").is_file():
        raise SystemExit(f"--plugin-dir has no .claude-plugin/plugin.json: {args.plugin_dir}")

    name, prompt, checks, follows = load_case(args)
    if follows and not args.continue_from:
        raise SystemExit(f"case {name!r} follows {follows!r}: pass --continue-from <that run's output directory>")
    out = new_output_dir(args.output, name)
    work = out / "work"
    work.mkdir()
    follow_on = continue_from(args.continue_from.expanduser().resolve(), work) if args.continue_from else None
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0", NO_COLOR="1")
    plugin = None
    released = released_versions() if args.source == "marketplace" else None
    if args.host == "grok":
        env = hosts.grok_env(out / "home")
    if args.source == "marketplace" and args.host == "grok":
        installed = hosts.grok_install_marketplace(env, grok_bin=args.grok_bin)
        plugin_dir = Path(installed["path"]) if installed["path"] else out / "missing-plugin"
        plugin = {"pass": installed["pass"], "loaded": installed["loaded"], "source": installed["source"]}
    elif args.source == "marketplace":
        plugin_dir = export_released(out)
    else:
        plugin_dir = args.plugin_dir or build_candidate(out)
        if args.host == "grok":
            plugin = hosts.grok_install(env, plugin_dir, args.grok_bin)
    manifest = plugin_dir / ".claude-plugin" / "plugin.json"
    versions = {"source": args.source,
                "plugin_version": json.loads(manifest.read_text()).get("version") if manifest.is_file() else None,
                "shiploop_version": card_version(plugin_dir / "skills" / "shiploop" / "SKILL.md"),
                **({"released": released} if released else {"local_head": git("rev-parse", "HEAD").strip()})}
    if released:
        versions["gate"] = version_gate(released, versions["plugin_version"], versions["shiploop_version"])
        if versions["gate"]:
            (out / "result.json").write_text(json.dumps({"case": name, "pass": False, "versions": versions,
                                                         "output": str(out)}, indent=2) + "\n")
            raise SystemExit("version gate: " + "; ".join(versions["gate"]) + f" (see {out / 'result.json'})")
    keepalive = hosts.grok_keepalive(env, plugin_dir) if args.host == "grok" else None
    cli = hosts.argv_for(args.host, prompt=f"/{args.skill} {prompt}", prompt_file=out / "host-prompt.txt",
                         cwd=work, model=args.model, effort=args.effort,
                         permission_mode=args.permission_mode, max_turns=args.max_turns,
                         max_budget_usd=args.max_budget_usd,
                         plugin_dir=plugin_dir if args.host == "claude" else None,
                         grok_bin=args.grok_bin, claude_bin=args.claude_bin)
    (out / "prompt.txt").write_text(prompt + "\n")
    (out / "invocation.json").write_text(json.dumps(
        {"case": name, "host": args.host, "model": args.model, "effort": args.effort, "argv": cli,
         "cwd": str(work), "plugin_dir": str(plugin_dir), "versions": versions, "checks": checks,
         "follow_on": follow_on},
        indent=2) + "\n")
    if not args.quiet:
        print(f"shiploop e2e case={name} host={args.host} model={args.model} effort={args.effort} "
              f"work={work}", flush=True)

    deadline = time.time() + args.timeout
    process = launch(cli, work, out, env, args.timeout, watch=not args.quiet, fresh=follow_on is None)
    sessions = [dict(process, resumed=None)]
    # A headless Grok session ends whenever the model ends its turn. While ShipLoop's
    # run is still active, resume that same session (bounded) instead of losing the run.
    while args.host == "grok" and len(sessions) <= args.max_resumes:
        state = grade_shiploop(out)
        session_id = last_session_id(out / "events.jsonl")
        remaining = int(deadline - time.time())
        # No run yet means the session ended before ShipLoop wrote its state; a
        # run that is paused, blocked, awaiting, halted or done is not resumed.
        if state.get("status") not in ("active", None) or not session_id or remaining <= 60:
            break
        if not args.quiet:
            print(f"resume {len(sessions)}/{args.max_resumes}: session {session_id} ended with ShipLoop "
                  f"{'not yet started' if state.get('status') is None else 'active at revision ' + str(state.get('revision')) + ', stage ' + str(state.get('stage'))}", flush=True)
        argv = hosts.argv_for(args.host, prompt=resume_prompt(out, state.get("run_dir")),
                              prompt_file=out / f"resume-{len(sessions)}.txt", cwd=work, model=args.model,
                              effort=args.effort, permission_mode=args.permission_mode,
                              max_turns=args.max_turns, resume=session_id, grok_bin=args.grok_bin)
        process = launch(argv, work, out, env, remaining, watch=not args.quiet, first=False)
        sessions.append(dict(process, resumed=session_id))
    process = dict(process, sessions=sessions, resumes=len(sessions) - 1)
    process["pass"] = process["status"] == "exited"
    cli_seen = summarize_events(out / "events.jsonl")
    write_transcript(out / "events.jsonl", out / "transcript.md")
    cli_seen["truncated_outputs"] = host_truncations(out / "events.jsonl")
    invoked = {"pass": args.skill in cli_seen.pop("commands"), "skill": args.skill}
    plugins = cli_seen.pop("plugins")
    if plugin is None:
        plugin = grade_claude_plugin(plugins, plugin_dir)
    shiploop = grade_shiploop(out)
    shiploop["knowledge"] = knowledge_facts(work)
    start_head = (follow_on or {}).get("start_head")
    knowledge = shiploop["knowledge"]
    committed = {"pass": bool(knowledge["head"]) and knowledge["head"] != start_head and not knowledge["uncommitted"],
                 "start_head": start_head, "head": knowledge["head"], "uncommitted": knowledge["uncommitted"][:20]}
    run_metrics = metrics.collect(out, Path(shiploop["run_dir"]) if shiploop.get("run_dir") else None)
    (out / "metrics.json").write_text(json.dumps(run_metrics, indent=2) + "\n")
    check_env = {"PRIOR_WORK": str(Path(follow_on["prior"]) / "work")} if follow_on else {}
    check_results = run_checks(work, checks, env=check_env)
    if not shiploop["pass"] and shiploop.get("worktree"):
        # Informational only: does the unreturned candidate already pass?
        shiploop["worktree_checks"] = [{k: c[k] for k in ("command", "pass")}
                                       for c in run_checks(Path(shiploop["worktree"]), checks, env=check_env)]
    verdicts = [invoked["pass"], plugin["pass"], process["pass"], shiploop["pass"], committed["pass"],
                *(c["pass"] for c in check_results)]
    if keepalive is not None:
        keepalive["decisions"] = hosts.keepalive_decisions(out / "home")
    result = {"case": name, "host": args.host, "model": args.model, "effort": args.effort,
              "pass": all(verdicts), "invoked": invoked, "plugin": plugin, "versions": versions,
              "process": process,
              "keepalive": keepalive,
              "shiploop": shiploop, "committed": committed, "checks": check_results, "cli": cli_seen, "follow_on": follow_on,
              "metrics": {k: run_metrics[k] for k in ("turns", "cost_usd", "compactions", "truncated_outputs",
                                                      "improve_children")}
              | {"script_verifications": run_metrics["script_verifications"],
                 "model_glue": len(run_metrics["model_glue"]),
                 "asked_user": len(run_metrics["asked_user"]),
                 "narrative": {k: v for k, v in run_metrics["narrative"].items() if k != "skipped"},
                 "shiploop_failures": len(run_metrics["shiploop_failures"]),
                 "cancelled_tool_calls": len(run_metrics["cancelled_tool_calls"])},
              "output": str(out)}
    (out / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    style = json.loads(CASES.read_text()).get(name, {}).get("style") if name != "custom" else None
    row = baseline_row(result, style, args.suite_name)
    before = previous_row(args.baseline, name, versions["source"]) if args.baseline else None
    if args.baseline:
        with args.baseline.open("a") as handle:
            handle.write(json.dumps(row) + "\n")

    mark = lambda ok: "PASS" if ok else "FAIL"  # noqa: E731
    print(f"{mark(result['pass'])}  shiploop e2e case={name} host={args.host}  output={out}")
    print(f"  versions  {versions['source']}: skill-craft {versions['plugin_version']}, "
          f"ShipLoop {versions['shiploop_version']}")
    print(f"  invoked   {mark(invoked['pass'])}  /{args.skill}")
    print(f"  plugin    {mark(plugin['pass'])}  {', '.join(map(str, plugin['loaded'])) or 'none loaded'}")
    print(f"  process   {mark(process['pass'])}  {process['status']} rc={process['returncode']} "
          f"{sum(s['elapsed_seconds'] for s in sessions):.1f}s cost=${cli_seen.get('cost_usd')} "
          f"sessions={len(sessions)}")
    if keepalive is not None:
        print(f"  keepalive {'installed' if keepalive['installed'] else 'NOT installed'}; "
              f"decisions {keepalive['decisions'] or 'none (hooks never ran)'}")
    print(f"  shiploop  {mark(shiploop['pass'])}  {shiploop.get('status') or shiploop.get('reason')}")
    if shiploop.get("worktree_checks") is not None:
        passed = sum(c["pass"] for c in shiploop["worktree_checks"])
        print(f"            unreturned product in {shiploop['worktree']}: "
              f"{passed}/{len(shiploop['worktree_checks'])} checks pass there")
    print(f"  committed {mark(committed['pass'])}  HEAD {str(committed['head'])[:8]} (started at "
          f"{str(committed['start_head'])[:8] if committed['start_head'] else 'no commit'}); "
          f"{len(knowledge['uncommitted'])} uncommitted product paths")
    print(f"  knowledge docs/shiploop/spec.md {'present' if knowledge['spec'] else 'missing'}"
          f"{', tracked' if knowledge['spec_tracked'] else ', not committed'}; {len(knowledge['requirement_ids'])} "
          f"requirement ids; HEAD has {knowledge['head_commits']} commits, {knowledge['untracked_files']} untracked files")
    for line in metrics.summary_lines(run_metrics):
        print(f"  metrics   {line}")
    for failure in run_metrics["shiploop_failures"][:5]:
        print(f"  failed    shiploop {failure['verb']} exit {failure['exit']}: {failure['line']}")
    if follow_on:
        print(f"  follow-on of {follow_on['prior_case']} ({follow_on['prior']}): turns {run_metrics['turns']} vs "
              f"{follow_on['prior_turns']}, cost ${run_metrics['cost_usd']} vs ${follow_on['prior_cost_usd']}")
    for check in check_results:
        print(f"  check     {mark(check['pass'])}  {check['command']}")
    if before:
        print(f"  baseline  vs {before['date'][:10]} (ShipLoop {before['shiploop_version']}): "
              f"turns {before['turns']} -> {row['turns']}, cost ${before['cost_usd']} -> ${row['cost_usd']}, "
              f"sessions {before['sessions']} -> {row['sessions']}, glue {before['model_glue']} -> {row['model_glue']}"
              + (f", narrative shown {before['narrative']['shown']}/{before['narrative']['emitted']} -> "
                 f"{row['narrative']['shown']}/{row['narrative']['emitted']}"
                 if before.get("narrative") and row.get("narrative") else ""))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
