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
            started and no product path is left uncommitted
  checks    every case check command exits 0 in a disposable product copy

A follow-on case (`follows` in cases.json) runs a second feature in a copy of an
earlier run's source checkout (--continue-from <earlier output>), to see whether
ShipLoop builds on what the first run decided. Its checks are the followed
case's checks (regression), its own feature checks and retention checks, which
get $PRIOR_WORK (a disposable copy of the earlier checkout).

Besides the verdicts, metrics.json records where ShipLoop spent turns, tokens,
cost and time (per accepted stage), its failed commands, host truncations,
compactions and the knowledge-home facts (see metrics.py).

The default host is Grok at medium reasoning effort. By default the run tests
what the whichguy marketplace publishes now (--source marketplace, gated on
no unpublished local commits and matching versions); --source checkout builds
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
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import signal
import platform
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
import evidence  # noqa: E402
import metrics  # noqa: E402
import shiploop_knowledge_home as knowledge_home  # noqa: E402
import shiploop_store as store  # noqa: E402

CASES = HERE / "cases.json"
SUITES = HERE / "suites.json"
BASELINES = HERE / "baselines.jsonl"
PLUGIN_NAME = "skill-craft"
# Grok does not namespace plugin skills; Claude prefixes them with the plugin name.
def the_host(args) -> "hosts.Host":
    """The selected host, with the binary its --<host>-bin flag names."""
    return hosts.host(args.host, getattr(args, args.host + "_bin"))


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
    earlier = evidence.read_json(prior / "result.json")
    if not earlier.get("pass"):
        raise SystemExit("--continue-from needs a mechanically passing predecessor")
    if (prior / "evidence-seal.json").is_file() and evidence.verify_seal(prior):
        raise SystemExit("--continue-from predecessor evidence changed")
    work.rmdir()
    shutil.copytree(source, work, symlinks=True)
    shutil.rmtree(work / ".git" / "worktrees", ignore_errors=True)
    subprocess.run(["git", "-C", str(work), "worktree", "prune"], check=False, capture_output=True)
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
    origin_main = git("rev-parse", "origin/main").strip()
    local = git("rev-parse", "HEAD").strip()
    # Behind origin/main is fine (the plugin comes from the marketplace); unpublished local commits are not.
    behind = subprocess.run(["git", "-C", str(ROOT), "merge-base", "--is-ancestor", local, origin_main]).returncode == 0
    return {"origin_main": origin_main, "local_head": local, "local_behind_main": behind,
            "catalog_version": plugin.get("version"), "shiploop_version": shiploop.group(1) if shiploop else None,
            "unreleased": pending, "ci": main_ci(origin_main)}


def main_ci(commit: str) -> str:
    """origin/main's CI result: success, failure, pending, or unknown (no gh, or no run found).

    The full hermetic tier runs in CI on release commits, not locally; the E2E runs wait for it.
    """
    try:
        done = subprocess.run(["gh", "run", "list", "--repo", "whichguy/skill-craft", "--workflow", "ci.yml", "--commit", commit,
                               "--json", "status,conclusion"], capture_output=True, text=True, timeout=10)
        runs = json.loads(done.stdout) if done.returncode == 0 else None
    except (OSError, ValueError, subprocess.TimeoutExpired):
        runs = None
    if not runs:
        return "unknown"
    if any(run.get("conclusion") == "failure" for run in runs):
        return "failure"
    if any(run.get("status") != "completed" for run in runs):
        return "pending"
    return "success" if all(run.get("conclusion") == "success" for run in runs) else "failure"


class CIMonitor:
    """Own cancellation for one pinned release; never touch other runs."""
    def __init__(self, commit: str | None, initial: str = "unknown", interval: float = 30):
        self.commit, self.status, self.interval = commit, initial, interval
        self.failed = threading.Event()
        self.stopped = threading.Event()
        self.observations = []
        self.thread = None

    def refresh(self):
        if self.commit:
            try:
                self.status = main_ci(self.commit)
            except Exception:
                self.status = "unknown"
            self.observations.append({"time": time.time(), "status": self.status})
            if self.status == "failure":
                self.failed.set()
        return self.status

    def start(self):
        if not self.commit:
            return self
        if self.status == "failure":
            self.failed.set()
        def poll():
            while not self.stopped.wait(self.interval):
                self.refresh()
        self.thread = threading.Thread(target=poll, daemon=True)
        self.thread.start()
        return self

    def close(self):
        self.stopped.set()
        if self.thread:
            self.thread.join(timeout=12)
        self.refresh()
        return {"owner": "runner", "commit": self.commit, "workflow": "ci.yml", "status": self.status,
                "observations": self.observations, "failed": self.failed.is_set()}


def version_gate(released: dict, plugin_version: str | None, shiploop_version: str | None) -> list[str]:
    """Why a marketplace run would not test what main and the marketplace publish, if at all."""
    problems = []
    # Optimistic: a run starts while CI is still pending and is cancelled if CI then fails (SPEC).
    if released.get("ci") == "failure":
        problems.append("origin/main's CI failed: fix it (or revert) before spending a live run")
    if released.get("unreleased"):
        problems.append("origin/main has unreleased changes (" + ", ".join(released["unreleased"][:5])
                        + "): run scripts/release.py and push so the marketplace serves them")
    if released["local_head"] != released["origin_main"] and not released.get("local_behind_main"):
        problems.append(f"local HEAD {released['local_head'][:8]} has commits origin/main "
                        f"{released['origin_main'][:8]} does not: publish them first")
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


def installed_versions(plugin_dir: Path) -> dict:
    """The skill-craft and ShipLoop versions of the plugin a host will actually load."""
    manifest = plugin_dir / ".claude-plugin" / "plugin.json"
    return {"plugin_version": json.loads(manifest.read_text()).get("version") if manifest.is_file() else None,
            "shiploop_version": card_version(plugin_dir / "skills" / "shiploop" / "SKILL.md")}


def marketplace_preflight(args, out: Path, env: dict) -> tuple[Path, dict | None, dict]:
    """Pull from the marketplace the way the host does, then report and gate what was actually installed.

    Grok: add the published marketplace and install skill-craft into the fresh profile in ``env``.
    Claude: load origin/main's plugins/skill-craft, the bytes the marketplace serves.
    Prints one line naming what main publishes and what the host got, so a stale
    marketplace is visible before any run starts (SPEC: publish, refresh, then run).
    """
    released = released_versions()
    plugin = None
    host = the_host(args)
    if host.marketplace:
        installed = host.install_marketplace(env)
        plugin_dir = Path(installed["path"]) if installed["path"] else out / "missing-plugin"
        plugin = {"pass": installed["pass"], "loaded": installed["loaded"], "source": installed["source"],
                  "registry_version": installed["version"]}
        how = f"{host.name} marketplace add + install (fresh profile)"
    else:
        plugin_dir = export_released(out)
        how = "origin/main export"
    versions = {"source": "marketplace", "installed_by": how, **installed_versions(plugin_dir), "released": released}
    versions["gate"] = version_gate(released, versions["plugin_version"], versions["shiploop_version"])
    if plugin is not None and not plugin["pass"]:
        versions["gate"].append("the marketplace install failed: " + ("; ".join(plugin["loaded"]) or "no plugin"))
    print(preflight_line(versions), flush=True)
    return plugin_dir, plugin, versions


def preflight_line(versions: dict) -> str:
    released = versions["released"]
    return (f"marketplace preflight: origin/main {released['origin_main'][:8]} publishes skill-craft "
            f"{released['catalog_version']} / ShipLoop {released['shiploop_version']}; "
            f"{versions['installed_by']} got skill-craft {versions['plugin_version']} / ShipLoop "
            f"{versions['shiploop_version']}; unreleased notes: {len(released.get('unreleased') or [])}; "
            f"main CI: {released.get('ci', 'unknown')}; "
            + ("OK" if not versions["gate"] else "REFUSED: " + "; ".join(versions["gate"])))


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


def stop_owned_process(proc) -> str | None:
    return hosts.stop_owned_process(proc)


def launch(argv: list[str], work: Path, out: Path, env: dict, timeout: int, watch: bool,
           first: bool = True, fresh: bool = True, translate=None, monitor: CIMonitor | None = None) -> dict:
    if first and fresh:
        # The skill must start from a directory with nothing in it.
        leftover = sorted(p.name for p in work.iterdir())
        if leftover:
            raise SystemExit(f"working directory is not empty: {leftover}")
    start = time.time()
    view = LiveView(start, watch)
    mode = "wb" if first else "ab"  # a resumed session appends to the same streams
    events_path = out / "events.jsonl"
    if first:
        line = 0
    else:
        with events_path.open("rb") as existing:
            line = sum(1 for _ in existing)
    # A run takes an hour or more; on macOS keep the machine from idle-sleeping, which
    # otherwise freezes the host mid-stage and stretches every stage timing.
    caffeinate = shutil.which("caffeinate")
    if caffeinate:
        argv = [caffeinate, "-i", *argv]
    with events_path.open(mode) as events, (out / "stderr.txt").open(mode) as stderr, \
            (out / "timeline.jsonl").open("w" if first else "a") as stamps:
        proc = subprocess.Popen(argv, cwd=work, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                stderr=stderr, env=env, start_new_session=True)

        def record(raw: bytes):
            nonlocal line
            events.write(raw)
            events.flush()
            number, line = line, line + 1
            try:
                event = json.loads(raw)
            except ValueError:
                return
            if isinstance(event, dict):
                # Grok events carry no time; stamp the ones metrics.py attributes.
                if event.get("type") not in ("text", "thought"):
                    stamps.write(json.dumps({"line": number, "t": round(time.time(), 3)}) + "\n")
                    stamps.flush()
                view.event(event)

        capture_errors = []
        def pump():
            # Translation or capture failure cannot silently leave a passing prefix.
            try:
                for original in proc.stdout:
                    for raw in (translate or (lambda b: [b]))(original):
                        record(raw)
                view.flush_text()
            except Exception as exc:
                capture_errors.append(str(exc))

        reader = threading.Thread(target=pump, daemon=True)
        reader.start()
        try:
            deadline = time.monotonic() + timeout
            while proc.poll() is None:
                if monitor and monitor.failed.is_set():
                    status = "cancelled_ci"
                    break
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    status = "timeout"
                    break
                try:
                    proc.wait(timeout=min(1, remaining))
                except subprocess.TimeoutExpired:
                    continue
            else:
                status = "exited" if proc.returncode == 0 else "failed"
        finally:
            # Catch interruption too; no owned descendants are intentionally retained.
            cleanup_error = stop_owned_process(proc)
        reader.join(timeout=10)
        if reader.is_alive():
            capture_errors.append("capture did not finish after owned process cleanup")
        else:
            proc.stdout.close()
    return {"status": status, "returncode": proc.returncode, "capture_errors": capture_errors,
            "cleanup_error": cleanup_error,
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
        priced = [s["cost_usd"] for s in ended if isinstance(s["cost_usd"], (int, float)) and not isinstance(s["cost_usd"], bool)]
        seen["known_cost_usd"] = round(sum(priced), 4) if priced else None
        seen["cost_usd"] = round(sum(priced), 4) if len(priced) == len(ended) else None
        seen["cost_status"] = "known" if len(priced) == len(ended) else "partial" if priced else "unknown"
    return seen


def shiploop_cli_ran(events_path: Path) -> bool:
    """Whether any tool call ran the installed ShipLoop CLI."""
    for line in events_path.read_text(errors="replace").splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if isinstance(event, dict) and event.get("type") == "tool_call":
            arg = event.get("rawInput") if isinstance(event.get("rawInput"), dict) else {}
            if "skills/shiploop/scripts/shiploop" in str(arg.get("command") or ""):
                return True
    return False


def last_session_id(events_path: Path, start_line: int = 0) -> str | None:
    """The host session to resume: the last session id the event stream carried."""
    found = None
    for line in events_path.read_text(errors="replace").splitlines()[start_line:]:
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if isinstance(event, dict) and isinstance(event.get("sessionId"), str):
            found = event["sessionId"]
    return found


def resume_prompt(out: Path, run_dir: str | None, host: "hosts.Host | None" = None) -> str:
    if run_dir is None:
        return ("This session ended before the ShipLoop run was started. Continue the original "
                "request now: start the ShipLoop run as its skill directs and follow each packet to "
                "the end of the run. Never end the turn while a ShipLoop command is still running.")
    cli = (host or hosts.host("grok")).plugin_cli(out / "home")
    command = f'python3 "{cli}" next --run-dir "{run_dir}"' if cli else f'shiploop next --run-dir "{run_dir}"'
    return ("This session ended while the ShipLoop run was still active. Continue it now: run "
            f"`{command}` and follow the packet it prints, to the end of the run. Never end the turn "
            "while a ShipLoop command is still running. If an interrupted operation may have taken effect, "
            "read back its stable operation/resource identity before retrying; never blindly repeat a write. "
            "A blocked or awaiting action has not been answered by this continuation.")


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
    binding_path = out / "run-binding.json"
    binding = evidence.read_json(binding_path) if binding_path.is_file() else None
    invocation = evidence.read_json(out / "invocation.json") if (out / "invocation.json").is_file() else {}
    previous = invocation.get("initial_states", {})
    malformed = []
    for state_path in sorted(out.rglob("state.md")):
        relative = state_path.relative_to(out).parts
        if relative[0] in ("home", "build", "marketplace", "preflight", "evaluation", "checks", "attempts") or relative[0].startswith("review"):
            continue
        if binding and state_path.parent.resolve() != Path(binding["run_dir"]).resolve():
            continue
        if not binding and previous.get(str(state_path.resolve())) == evidence.tree_digest(state_path):
            continue
        try:
            state = store.read_record(state_path)
        except (store.StorageError, OSError, ValueError):
            malformed.append(str(state_path))
            continue
        if isinstance(state, dict) and "status" in state:
            runs.append({"run_dir": str(state_path.parent), "status": state.get("status"),
                         "stage": state.get("stage"), "revision": state.get("revision"),
                         "report_html": (state_path.parent / "report.html").is_file()})
    if binding and binding.get("invocation_id") != invocation.get("invocation_id"):
        return {"pass": False, "reason": "run binding belongs to another invocation", "evidence_status": "invalid"}
    if len(runs) != 1 or malformed:
        reason = "ambiguous or malformed current run state" if runs or malformed else "no ShipLoop state.md under the output directory"
        return {"pass": False, "reason": reason, "runs": len(runs), "malformed": malformed,
                "evidence_status": "incomplete"}
    chosen = runs[0]
    if not binding and invocation.get("invocation_id"):
        evidence.atomic_json(binding_path, {"invocation_id": invocation["invocation_id"], "run_dir": chosen["run_dir"]})
    # ShipLoop builds in its own worktree beside the run and returns it to the
    # source only at release; name it so an unreturned product can be inspected.
    worktree = Path(chosen["run_dir"]).parent / "worktree"
    return {"pass": chosen["status"] == "done" and chosen["report_html"], **chosen, "runs": len(runs),
            "evidence_status": "valid",
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
    # A filename extension cannot exempt a changed tracked product from return.
    uncommitted = [ln[3:] for ln in status]
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


def run_checks(work: Path, checks: list[str], timeout: int = 180, env: dict | None = None,
               output: Path | None = None, checks_root: Path | None = None,
               monitor: CIMonitor | None = None) -> list[dict]:
    """Check disposable copies, retain logs, and detect changes to retained originals."""
    work = work.resolve()
    env = dict(env or {})
    before = evidence.fingerprint(work)
    output = output or Path(tempfile.mkdtemp(prefix="shiploop-checks-"))
    output.mkdir(parents=True, exist_ok=True)
    target = output / "work"
    for source in (work, Path(env["PRIOR_WORK"]).resolve() if env.get("PRIOR_WORK") else None):
        if source is None:
            continue
        unsupported = ((source / ".git").is_file() or any(
            p.is_symlink() and (Path(os.readlink(p)).is_absolute() or not p.resolve().is_relative_to(source))
            for p in source.rglob("*")))
        if unsupported:
            return [{"command": command, "pass": False, "returncode": None, "status": "unsupported",
                     "output": "Check copy requires a standalone checkout without absolute or escaping symlinks.",
                     "effects": {"originals_unchanged": True, "cleanup_error": None}} for command in checks]
    shutil.copytree(work, target, symlinks=True, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    prior = Path(env["PRIOR_WORK"]).resolve() if env.get("PRIOR_WORK") else None
    prior_before = evidence.fingerprint(prior) if prior else None
    if prior:
        shutil.copytree(prior, output / "prior", symlinks=True,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        env["PRIOR_WORK"] = str(output / "prior")
    for name in ("home", "tmp"):
        (output / name).mkdir()
    check_env = {"PATH": os.environ.get("PATH", ""), "HOME": str(output / "home"),
                 "TMPDIR": str(output / "tmp"), "LANG": os.environ.get("LANG", "C.UTF-8"),
                 "PYTHONDONTWRITEBYTECODE": "1", **env,
                 "E2E_CHECKS": str(checks_root or HERE / "checks")}
    results = []
    for index, command in enumerate(checks):
        log = output / f"check-{index:03d}.log"
        status, code, cleanup_error = "exited", None, None
        with log.open("wb") as handle:
            if monitor and monitor.failed.is_set():
                results.append({"command": command, "pass": False, "returncode": None,
                                "status": "cancelled_ci", "output": "pinned release CI failed", "log": str(log)})
                break
            proc = subprocess.Popen(command, shell=True, cwd=target, stdout=handle, stderr=subprocess.STDOUT,
                                    stdin=subprocess.DEVNULL, env=check_env, start_new_session=True)
            try:
                deadline = time.monotonic() + timeout
                while proc.poll() is None:
                    if monitor and monitor.failed.is_set():
                        status = "cancelled_ci"
                        break
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise subprocess.TimeoutExpired(command, timeout)
                    try:
                        proc.wait(timeout=min(1, remaining))
                    except subprocess.TimeoutExpired:
                        continue
                code = proc.returncode
                if status != "cancelled_ci":
                    status = "exited" if code == 0 else "failed"
            except subprocess.TimeoutExpired:
                status = "timeout"
            finally:
                # A server launched by a shell may outlive that shell even on success.
                cleanup_error = stop_owned_process(proc)
        intact = before == evidence.fingerprint(work) and (not prior or prior_before == evidence.fingerprint(prior))
        results.append({"command": command, "pass": status == "exited" and code == 0 and intact and cleanup_error is None,
                        "returncode": code, "status": status, "output": log.read_text(errors="replace")[-2000:],
                        "log": str(log), "scratch": str(target),
                        "effects": {"originals_unchanged": intact, "cleanup_error": cleanup_error}})
        if not intact or cleanup_error:
            break
    return results


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--case", default="hello", help="case name from cases.json (default: hello)")
    p.add_argument("--suite", help="run a suite from suites.json in order (focused: one style in depth; "
                                   "breadth: one case per style); --output becomes the suite directory")
    p.add_argument("--baseline", type=Path, default=BASELINES,
                   help="append one summary row per run to this file (default: the committed baselines.jsonl)")
    p.add_argument("--prompt", help="run this prompt instead of a named case")
    p.add_argument("--resume-run", type=Path,
                   help="an earlier run's output directory whose ShipLoop run stopped while active (a host ran "
                        "out of credits, a machine slept): continue that same run in place, on --host, and grade "
                        "it as usual. The case and checks come from the earlier run.")
    p.add_argument("--continue-from", type=Path,
                   help="an earlier run's output directory: start in a copy of its source checkout "
                        "(required by follow-on cases, which name the case they follow)")
    p.add_argument("--check", action="append", help="extra shell check run in the work dir (repeatable)")
    p.add_argument("--output", type=Path, help="new directory for this attempt (default: under $TMPDIR)")
    p.add_argument("--host", choices=[*sorted(hosts.HOSTS), "all"], default="grok",
                   help="the host that drives ShipLoop; 'all' only with --preflight-only (checks every host)")
    p.add_argument("--model", help="default: grok-4.7 (grok) or sonnet (claude)")
    p.add_argument("--effort", help="reasoning effort; default: medium (grok), host default (claude)")
    p.add_argument("--skill", help="command that invokes ShipLoop; default: shiploop (grok), skill-craft:shiploop (claude)")
    p.add_argument("--source", choices=("marketplace", "checkout"), default="marketplace",
                   help="marketplace (default): test what the whichguy marketplace publishes now, gated on "
                        "no unpublished local commits and matching versions; checkout: build this checkout")
    p.add_argument("--preflight-only", action="store_true",
                   help="pull skill-craft from the marketplace into a fresh profile, print what main publishes "
                        "and what the host installed, and exit non-zero if the version gate refuses")
    p.add_argument("--plugin-dir", type=Path, help="test this skill-craft plugin build (implies --source checkout)")
    p.add_argument("--max-turns", type=int, default=10000)
    p.add_argument("--max-budget-usd", type=float, default=10.0, help="claude only; grok has no spend cap")
    p.add_argument("--permission-mode", default="auto")
    p.add_argument("--timeout", type=int, default=10800, help="seconds before the host is killed")
    p.add_argument("--max-resumes", type=int, default=20,
                   help="grok only: resume the same session this many times while ShipLoop is still active")
    p.add_argument("--quiet", action="store_true", help="do not print the live progress view")
    p.add_argument("--max-parallel", type=int, default=3,
                   help="suites: run up to this many independent case chains at once (default 3)")
    p.add_argument("--serial", action="store_true",
                   help="suites: run every case one after another (rerun a failure that appears only in parallel "
                        "this way before attributing it to ShipLoop)")
    p.add_argument("--suite-name", help=argparse.SUPPRESS)
    p.add_argument("--release-pin", type=Path, help=argparse.SUPPRESS)
    p.add_argument("--trial-concurrency", type=int, default=1, help=argparse.SUPPRESS)
    p.add_argument("--grok-bin", default="grok")
    p.add_argument("--claude-bin", default="claude")
    p.add_argument("--codex-bin", default="codex")
    return p


def baseline_row(result: dict, style: str | None, suite: str | None) -> dict:
    import comparison
    return comparison.baseline_row(result, style, suite)


def previous_row(path: Path, case: str, source: str | None, conditions: dict | None = None) -> dict | None:
    import comparison
    return comparison.previous_row(path, case, source, conditions)


def shared_tmp_writes(outputs: list[Path]) -> dict[str, list[str]]:
    """Each literal /tmp path that more than one of these runs wrote, with the runs that wrote it."""
    writers: dict[str, list[str]] = {}
    for out in outputs:
        for name in metrics.collect(out).get("tmp_writes") or []:
            writers.setdefault(name, []).append(out.name)
    return {name: runs for name, runs in sorted(writers.items()) if len(runs) > 1}


def suite_chains(order: list[str], cases: dict) -> list[list[str]]:
    """Independent chains: a case with its follow-ons, in suite order. Chains share nothing, so they may run
    concurrently; a follow-on always runs after its predecessor, in the same chain."""
    chains: list[list[str]] = []
    home: dict[str, list[str]] = {}
    for case in order:
        follows = cases[case].get("follows")
        chain = home.get(follows) if follows else None
        if chain is None:
            chain = []
            chains.append(chain)
        chain.append(case)
        home[case] = chain
    return chains


def run_suite(args, argv: list[str]) -> int:
    """Run one pinned batch; skips and incomplete evidence remain in its denominator."""
    import comparison
    suites, cases = evidence.read_json(SUITES), evidence.read_json(CASES)
    if args.suite not in suites or args.suite.startswith("_"):
        raise SystemExit(f"unknown suite {args.suite!r}")
    base = new_output_dir(args.output, "suite-" + args.suite)
    gate = suites[args.suite].get("gate") or []
    order = suites[args.suite]["cases"]
    all_cases = gate + order
    passthrough, skip = [], {"--suite", "--output", "--case", "--continue-from", "--max-parallel"}
    it = iter(argv)
    for token in it:
        name = token.split("=", 1)[0]
        if name in skip:
            if "=" not in token:
                next(it, None)
            continue
        passthrough.append(token)

    def finish(rows, shared=None):
        summary = {"suite": args.suite, "cases": rows, "shared_tmp_writes": shared or {},
                   "counts": comparison.suite_counts(rows),
                   "qualification": {"status": "pending_review", "clean": False},
                   "pass": bool(rows) and all(row.get("pass") is True for row in rows)}
        evidence.atomic_json(base / "suite-result.json", summary)
        print(f"suite {args.suite}: " + ", ".join(f"{row['case']} {row.get('status', 'unknown')}" for row in rows))
        return 0 if summary["pass"] else 1

    # Freeze the release and harness before a gate or a concurrent chain starts.
    check = base / "preflight"
    check.mkdir()
    try:
        versions = {}
        if args.source == "marketplace" and not args.plugin_dir:
            env = the_host(args).env(check / "home")
            package, _, versions = marketplace_preflight(args, check, env)
            evidence.atomic_json(check / "preflight.json", versions)
            if versions["gate"]:
                raise ValueError("version gate: " + "; ".join(versions["gate"]))
        else:
            package = args.plugin_dir or build_candidate(check)
            if not args.plugin_dir:
                passthrough += ["--plugin-dir", str(package)]
        pin = {"origin_main": (versions.get("released") or {}).get("origin_main"),
               "subject_digest": evidence.tree_digest(package),
               "evaluator_digest": evidence.object_digest(evidence.evaluator_recipe()),
               "catalog_digest": evidence.tree_digest(CASES)}
        evidence.atomic_json(base / "batch-pin.json", pin)
        passthrough += ["--release-pin", str(base / "batch-pin.json")]
    except (Exception, SystemExit) as exc:
        return finish([{"case": case, "pass": False, "status": "blocked_preflight", "reason": str(exc),
                        "evidence": {"status": "incomplete"}} for case in all_cases])

    def run_case(case, concurrency=1, prior=None):
        out = base / case
        case_argv = [*passthrough, "--case", case, "--output", str(out), "--suite-name", args.suite,
                     "--trial-concurrency", str(concurrency)]
        if prior is not None:
            case_argv += ["--continue-from", str(prior)]
        try:
            code = main(case_argv)
            result = evidence.read_json(out / "result.json")
            receipt = evidence.read_json(out / "attempt.json")
            return {"case": case, "pass": code == 0 and result.get("pass") is True, "output": str(out),
                    "status": receipt.get("status", "incomplete"), "evidence": result.get("evidence"),
                    "criteria": result.get("criteria"), "suite": args.suite,
                    "qualification": result.get("qualification"), "process": result.get("process")}
        except (Exception, SystemExit) as exc:
            return {"case": case, "pass": False, "status": "incomplete", "output": str(out), "reason": str(exc),
                    "evidence": {"status": "incomplete"}}

    gate_rows = [dict(run_case(case), gate=True) for case in gate]
    if not all(row["pass"] for row in gate_rows):
        return finish(gate_rows + [{"case": case, "status": "skipped", "skipped": "the gate failed"} for case in order])
    chains = suite_chains(order, cases)
    workers = 1 if args.serial else max(1, min(args.max_parallel, len(chains)))
    if workers > 1 and "--quiet" not in passthrough:
        passthrough.append("--quiet")

    def run_chain(chain):
        completed, rows = {}, []
        for case in chain:
            follows = cases[case].get("follows")
            predecessor = completed.get(follows)
            if follows and (not predecessor or not predecessor.get("pass")):
                rows.append({"case": case, "status": "skipped", "skipped": f"its predecessor {follows!r} failed or is missing"})
                continue
            row = run_case(case, workers, Path(predecessor["output"]) if predecessor else None)
            completed[case] = row
            rows.append(row)
        return rows

    with ThreadPoolExecutor(max_workers=workers) as pool:
        rows = [row for chain_rows in pool.map(run_chain, chains) for row in chain_rows]
    summary = gate_rows + sorted(rows, key=lambda row: order.index(row["case"]))
    shared = shared_tmp_writes([Path(row["output"]) for row in summary if row.get("output")])
    if shared:
        affected = {case for writers in shared.values() for case in writers}
        for row in summary:
            if row["case"] in affected:
                row.update(pass_mechanical_before_collision=row.get("pass"), status="incomplete",
                           evidence={"status": "incomplete", "reasons": ["shared temporary path written by another case"]})
                row["pass"] = False
    return finish(summary, shared)


def archive_attempt(out: Path) -> Path:
    """Retain the previous projection before an explicit resume changes it."""
    archive = out / "attempts" / f"before-resume-{time.time_ns()}"
    archive.mkdir(parents=True)
    for item in list(out.iterdir()):
        if item.name in {"attempts", "home", "build", "marketplace", "checks", "evaluation", "reviews"}:
            continue
        if item.is_dir():
            shutil.copytree(item, archive / item.name, symlinks=True,
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        elif item.is_file():
            shutil.copy2(item, archive / item.name)
    evidence.atomic_json(archive / "archive.json", {"original_output": str(out),
                         "note": "Original artifact bytes retained; absolute locators still name the original run. Do not regrade as a fresh attempt."})
    return archive


def _main(argv: list[str] | None = None, *, attempt: dict) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    args = parser().parse_args(argv)
    if args.plugin_dir:
        args.plugin_dir = args.plugin_dir.expanduser().resolve()
    if args.preflight_only:
        # Before a rerun, every host must get the latest release (SPEC: publish, refresh, then run).
        out = new_output_dir(args.output, "preflight")
        refused = False
        for name in (sorted(hosts.HOSTS) if args.host == "all" else [args.host]):
            args.host = name
            check = out / name
            check.mkdir()
            _, _, versions = marketplace_preflight(args, check, the_host(args).env(check / "home"))
            (check / "preflight.json").write_text(json.dumps(versions, indent=2) + "\n")
            refused = refused or bool(versions["gate"])
        return 1 if refused else 0
    if args.host == "all":
        raise SystemExit("--host all is only for --preflight-only; a run needs one host")
    if args.suite:
        return run_suite(args, argv)
    host = the_host(args)
    args.model = args.model or host.model
    args.effort = args.effort or host.effort
    args.skill = args.skill or host.skill
    if args.plugin_dir:
        args.source = "checkout"
    if args.plugin_dir and not (args.plugin_dir / ".claude-plugin" / "plugin.json").is_file():
        raise SystemExit(f"--plugin-dir has no .claude-plugin/plugin.json: {args.plugin_dir}")

    resumed = None
    if args.resume_run:
        # Continue a stopped run in place: same work directory, run state and event stream.
        out = args.resume_run.expanduser().resolve()
        if evidence.verify_seal(out):
            raise SystemExit("--resume-run requires intact sealed evidence; start a new trial for changed or unsealed output")
        earlier = json.loads((out / "invocation.json").read_text())
        name, checks, follow_on = earlier["case"], earlier["checks"], earlier.get("follow_on")
        prompt = (out / "prompt.txt").read_text().strip()
        work = out / "work"
        state = grade_shiploop(out)
        if state.get("status") != "active":
            raise SystemExit(f"--resume-run needs an active ShipLoop run; found {state.get('status')!r} in {out}")
        resumed = {"from_host": earlier["host"], "from_model": earlier.get("model"), "run_dir": state.get("run_dir"),
                   "revision": state.get("revision"), "stage": state.get("stage")}
        resumed["archive"] = str(archive_attempt(out))
    else:
        name, prompt, checks, follows = load_case(args)
        if follows and not args.continue_from:
            raise SystemExit(f"case {name!r} follows {follows!r}: pass --continue-from <that run's output directory>")
        out = new_output_dir(args.output, name)
        attempt.update(output=str(out), case=name, attempt_id=secrets.token_hex(12),
                       status="preflight", started_at=time.time())
        work = out / "work"
        work.mkdir()
        follow_on = continue_from(args.continue_from.expanduser().resolve(), work) if args.continue_from else None
    attempt.update(output=str(out), case=name, attempt_id=secrets.token_hex(12),
                   status="preflight", started_at=time.time(), resume=bool(resumed),
                   budget={"timeout_seconds": args.timeout, "explicit_extension": bool(resumed)})
    evidence.atomic_json(out / "attempt.json", attempt)
    env = host.env(out / "home")
    if resumed and earlier.get("host") == args.host and Path(earlier.get("plugin_dir") or "").is_dir() and args.source == "marketplace":
        # A resumed run keeps the plugin it started on: reinstalling would replace that version's files, and a
        # bound Improve child records paths inside them. Only the CI and checkout checks still apply.
        plugin_dir, plugin = Path(earlier["plugin_dir"]), None
        released = released_versions()
        versions = {"source": "marketplace (resumed on its original install)", **installed_versions(plugin_dir),
                    "released": released,
                    "gate": [problem for problem in version_gate(released, None, None)
                             if not problem.startswith("installed ")]}
        if versions["gate"]:
            raise SystemExit("version gate: " + "; ".join(versions["gate"]))
        if host.name == "codex" and versions["plugin_version"] != released["catalog_version"]:
            # Codex syncs installed plugins to its marketplace's current release when a session starts and
            # deletes the old version's files, which the run's CLI and any bound Improve child point to.
            raise SystemExit(f"a Codex run started on skill-craft {versions['plugin_version']} cannot resume after "
                             f"release {released['catalog_version']}: Codex replaces the plugin at session start. "
                             "Start the case again.")
    elif args.source == "marketplace":
        plugin_dir, plugin, versions = marketplace_preflight(args, out, env)
        if resumed:
            # No original install to reuse: a newer release is still not a reason to refuse the run.
            versions["gate"] = [problem for problem in versions["gate"] if not problem.startswith("installed ")]
        if versions["gate"]:
            (out / "result.json").write_text(json.dumps({"case": name, "pass": False, "versions": versions,
                                                         "output": str(out)}, indent=2) + "\n")
            raise SystemExit("version gate: " + "; ".join(versions["gate"]) + f" (see {out / 'result.json'})")
    else:
        plugin = None
        plugin_dir = args.plugin_dir or build_candidate(out)
        plugin = host.install_plugin(env, plugin_dir)
        versions = {"source": "checkout", **installed_versions(plugin_dir), "local_head": git("rev-parse", "HEAD").strip()}
    if args.release_pin:
        pin = evidence.read_json(args.release_pin)
        actual = versions.get("released") or {}
        if (actual.get("origin_main") != pin.get("origin_main") or
                evidence.tree_digest(plugin_dir) != pin.get("subject_digest") or
                evidence.object_digest(evidence.evaluator_recipe()) != pin.get("evaluator_digest") or
                evidence.tree_digest(CASES) != pin.get("catalog_digest")):
            raise ValueError("batch release changed after preflight; start a new qualification batch")
    invocation_id = earlier["invocation_id"] if resumed else secrets.token_hex(16)
    if resumed:
        frozen = evidence.read_json(out / "evaluation.json")
        recipe = evidence.read_json(out / "evaluation" / "case.json")
        if checks != recipe["checks"] or prompt != recipe["case"]["prompt"]:
            raise ValueError("resume changed the frozen prompt or check recipe")
        if frozen["identity"]["subject_digest"] != evidence.tree_digest(plugin_dir):
            raise ValueError("resume changed the original installed package")
        if frozen["frozen_digest"] != evidence.tree_digest(out / "evaluation"):
            raise ValueError("resume evaluator evidence changed")
    else:
        case = {"prompt": prompt} if name == "custom" else json.loads(CASES.read_text())[name]
        frozen = evidence.freeze(out, plugin_dir, case, checks, invocation_id)
    criteria = frozen["criteria"]
    initial_input = evidence.fingerprint(work)
    initial_states = {str(p.resolve()): evidence.tree_digest(p) for p in work.rglob("state.md")}
    attempt.update(invocation_id=invocation_id, status="running")
    evidence.atomic_json(out / "attempt.json", attempt)
    keepalive = hosts.grok_keepalive(env, plugin_dir) if host.keepalive else None
    # A resumed run keeps the ShipLoop CLI of the host that started it, so its version does not change.
    opening = (resume_prompt(out, resumed["run_dir"], hosts.host(resumed["from_host"])) if resumed
               else host.invoke(args.skill, prompt))
    cli = host.argv(prompt=opening, prompt_file=out / ("host-prompt.txt" if not resumed else
                                                       f"resume-{host.name}-{int(time.time())}.txt"),
                    cwd=work, model=args.model, effort=args.effort,
                    permission_mode=args.permission_mode, max_turns=args.max_turns,
                    max_budget_usd=args.max_budget_usd,
                    plugin_dir=None if host.marketplace else plugin_dir)
    invocation = {"case": name, "host": args.host, "model": args.model, "effort": args.effort, "argv": cli,
                  "cwd": str(work), "plugin_dir": str(plugin_dir), "versions": versions, "checks": checks,
                  "follow_on": follow_on, "resumed_run": resumed}
    invocation.update(invocation_id=invocation_id, attempt_id=attempt["attempt_id"],
                      initial_states=initial_states, initial_input=initial_input,
                      budget={"timeout_seconds": args.timeout, "max_resumes": args.max_resumes,
                              "max_turns": args.max_turns if host.name != "codex" else None,
                              "max_budget_usd": args.max_budget_usd if host.name == "claude" else None})
    if resumed:
        # The original invocation stays as it was; each resume is recorded beside it.
        (out / f"invocation-resume-{host.name}-{int(time.time())}.json").write_text(
            json.dumps(invocation, indent=2) + "\n")
    else:
        (out / "prompt.txt").write_text(prompt + "\n")
        (out / "invocation.json").write_text(json.dumps(invocation, indent=2) + "\n")
    if not args.quiet:
        print(f"shiploop e2e case={name} host={args.host} model={args.model} effort={args.effort} "
              f"work={work}", flush=True)

    released = versions.get("released") or {}
    monitor = CIMonitor(released.get("origin_main"), released.get("ci", "unknown")).start()
    attempt["monitor"] = monitor
    deadline = time.time() + args.timeout
    stream_start = len((out / "events.jsonl").read_text().splitlines()) if (out / "events.jsonl").is_file() else 0
    process = launch(cli, work, out, env, args.timeout, watch=not args.quiet, fresh=follow_on is None,
                     first=resumed is None, translate=host.translator(), monitor=monitor)
    old_result = evidence.read_json(Path(resumed["archive"]) / "result.json") if resumed and (Path(resumed["archive"]) / "result.json").is_file() else {}
    prior_sessions = (old_result.get("process") or {}).get("sessions", [])
    sessions = [dict(process, resumed=None, host=host.name)]
    # A headless Grok session ends whenever the model ends its turn. While ShipLoop's
    # run is still active, resume that same session (bounded) instead of losing the run.
    while host.resumable and len(sessions) <= args.max_resumes:
        state = grade_shiploop(out)
        session_id = last_session_id(out / "events.jsonl", stream_start)
        remaining = int(deadline - time.time())
        # No run yet means the session ended before ShipLoop wrote its state; a
        # run that is paused, blocked, awaiting, halted or done is not resumed.
        if (process.get("status") != "exited" or monitor.failed.is_set() or
                state.get("status") == criteria["expected_terminal"] or
                state.get("status") not in ("active", None) or not session_id or remaining <= 60 or
                state.get("runs", 0) > 1 or state.get("malformed")):
            break
        if not args.quiet:
            print(f"resume {len(sessions)}/{args.max_resumes}: session {session_id} ended with ShipLoop "
                  f"{'not yet started' if state.get('status') is None else 'active at revision ' + str(state.get('revision')) + ', stage ' + str(state.get('stage'))}", flush=True)
        argv = host.argv(prompt=resume_prompt(out, state.get("run_dir"), host),
                         prompt_file=out / f"resume-{len(sessions)}.txt", cwd=work, model=args.model,
                         effort=args.effort, permission_mode=args.permission_mode,
                         max_turns=args.max_turns, resume=session_id)
        stream_start = len((out / "events.jsonl").read_text().splitlines())
        process = launch(argv, work, out, env, remaining, watch=not args.quiet, first=False,
                         translate=host.translator(), monitor=monitor)
        sessions.append(dict(process, resumed=session_id, host=host.name))
    process = dict(process, sessions=prior_sessions + sessions, resumes=len(sessions) - 1,
                   total_elapsed_seconds=sum(s["elapsed_seconds"] for s in prior_sessions + sessions))
    process["pass"] = process["status"] == "exited"
    cli_seen = summarize_events(out / "events.jsonl")
    write_transcript(out / "events.jsonl", out / "transcript.md")
    cli_seen["truncated_outputs"] = host_truncations(out / "events.jsonl")
    commands = cli_seen.pop("commands")
    invoked = {"pass": args.skill in commands, "skill": args.skill}
    if not commands or resumed:
        # A host that lists no commands (Codex), or a run continued on another host whose
        # stream mixes both hosts' command lists: the skill was invoked if its CLI ran.
        invoked.update({"pass": shiploop_cli_ran(out / "events.jsonl"), "evidence": "ShipLoop CLI ran"})
    plugins = cli_seen.pop("plugins")
    if plugin is None:
        plugin = grade_claude_plugin(plugins, plugin_dir)
    shiploop = grade_shiploop(out)
    start_head = (follow_on or {}).get("start_head")
    run_metrics = metrics.collect(out, Path(shiploop["run_dir"]) if shiploop.get("run_dir") else None)
    (out / "metrics.json").write_text(json.dumps(run_metrics, indent=2) + "\n")
    check_env = {"PRIOR_WORK": str(Path(follow_on["prior"]) / "work")} if follow_on else {}
    check_results = run_checks(work, checks, env=check_env, output=out / "checks" / attempt["attempt_id"],
                               checks_root=out / "evaluation" / "checks", monitor=monitor)
    if not shiploop["pass"] and shiploop.get("worktree"):
        # Informational only: does the unreturned candidate already pass?
        shiploop["worktree_checks"] = [{k: c[k] for k in ("command", "pass")}
                                       for c in run_checks(Path(shiploop["worktree"]), checks, env=check_env,
                                                           checks_root=out / "evaluation" / "checks", monitor=monitor)]
    # Check subprocesses must not change the recorded candidate or predecessor.
    shiploop["knowledge"] = knowledge_facts(work)
    knowledge = shiploop["knowledge"]
    committed = {"pass": bool(knowledge["head"]) and knowledge["head"] != start_head and not knowledge["uncommitted"],
                 "start_head": start_head, "head": knowledge["head"], "uncommitted": knowledge["uncommitted"][:20]}
    if criteria["kind"] == "noop":
        committed["pass"] = knowledge["head"] == initial_input["git"]["head"] and not knowledge["uncommitted"]
    if criteria["kind"] == "boundary":
        committed = {**committed, "pass": True, "applicable": False, "reason": "predeclared boundary scenario"}
    expected_state = shiploop.get("status") == criteria["expected_terminal"]
    state_pass = shiploop["pass"] if criteria["expected_terminal"] == "done" else expected_state
    ci = monitor.close()
    attempt.pop("monitor")
    process["ci"] = ci
    validity_reasons = evidence.stream_errors(out / "events.jsonl")
    if process.get("status") in {"timeout", "cancelled_ci"}:
        validity_reasons.append("host execution ended before completion: " + process["status"])
    if any(c.get("status") in {"timeout", "cancelled_ci"} for c in check_results):
        validity_reasons.append("required checks did not complete within their execution boundary")
    for session in process["sessions"]:
        validity_reasons.extend("capture incomplete: " + reason for reason in session.get("capture_errors", []))
        if session.get("cleanup_error"):
            validity_reasons.append(session["cleanup_error"])
    if shiploop.get("evidence_status") != "valid":
        validity_reasons.append(shiploop.get("reason", "run binding incomplete"))
    if len(check_results) != len(checks) or not checks:
        validity_reasons.append("required checks missing or not all executed")
    if any((c.get("effects") or {}).get("originals_unchanged") is False or
           (c.get("effects") or {}).get("cleanup_error") for c in check_results):
        validity_reasons.append("check effects unsettled")
    if evidence.tree_digest(plugin_dir) != frozen["identity"]["subject_digest"]:
        validity_reasons.append("installed package changed during run")
    if evidence.tree_digest(out / "evaluation") != frozen["frozen_digest"]:
        validity_reasons.append("frozen evaluation changed during run")
    if evidence.evaluator_recipe() != frozen["evaluator"]:
        validity_reasons.append("harness evaluator changed during run")
    if any(c.get("status") == "unsupported" for c in check_results):
        validity_reasons.append("required check isolation is unsupported")
    verdicts = [not validity_reasons, invoked["pass"], plugin["pass"], process["pass"], state_pass, committed["pass"],
                not ci["failed"],
                *(c["pass"] for c in check_results)]
    if keepalive is not None:
        keepalive["decisions"] = hosts.keepalive_decisions(out / "home")
    dependencies = {p.name: evidence.tree_digest(p) for p in sorted((plugin_dir / "skills").glob("*")) if p.name != "shiploop"}
    conditions = {"host": args.host, "model": args.model, "effort": args.effort,
                  "case_digest": frozen["identity"]["case_digest"],
                  "evaluator_digest": frozen["identity"]["evaluator_digest"],
                  "inputs_digest": evidence.object_digest(initial_input),
                  "dependency_digest": evidence.object_digest(dependencies),
                  "environment": {"system": platform.system(), "release": platform.release(),
                                  "machine": platform.machine(), "python": platform.python_version(),
                                  "reported_model": cli_seen.get("model"),
                                  "model_revision": "unverified provider alias",
                                  "host_binary": evidence.tree_digest(Path(host.binary)) if Path(host.binary).is_file() else
                                      evidence.tree_digest(Path(shutil.which(host.binary))) if shutil.which(host.binary) else "unknown"},
                  "budget": invocation["budget"], "concurrency": args.trial_concurrency}
    result = {"schema": "shiploop-e2e-result/2", "identity": {**frozen["identity"], "candidate_digest": evidence.tree_digest(work)},
              "evidence": {"status": "valid" if not validity_reasons else "incomplete", "reasons": validity_reasons},
              "qualification": {"status": "pending_review", "scope": "candidate" if args.source == "checkout" else "release", "clean": False},
              "comparison": conditions, "criteria": criteria, "attempt_id": attempt["attempt_id"],
              "case": name, "host": args.host, "model": args.model, "effort": args.effort,
              "pass": all(verdicts), "invoked": invoked, "plugin": plugin, "versions": versions,
              "process": process,
              "keepalive": keepalive,
              "shiploop": shiploop, "committed": committed, "checks": check_results, "cli": cli_seen, "follow_on": follow_on,
              "resumed_run": resumed,
              "metrics": {k: run_metrics[k] for k in ("turns", "cost_usd", "cost_status", "cost_known_subtotal_usd", "compactions", "truncated_outputs",
                                                      "improve_children")}
              | {"script_verifications": run_metrics["script_verifications"],
                 "model_glue": len(run_metrics["model_glue"]),
                 "tmp_writes": len(run_metrics["tmp_writes"]),
                 "asked_user": len(run_metrics["asked_user"]),
                 "narrative": {k: v for k, v in run_metrics["narrative"].items() if k != "skipped"},
                 "shiploop_failures": len(run_metrics["shiploop_failures"]),
                 "cancelled_tool_calls": len(run_metrics["cancelled_tool_calls"])},
              "output": str(out)}
    result["outcome"] = {"status": "unverified" if all(c["pass"] for c in check_results) else "partial",
                         "note": "Mechanical checks do not establish complete request coverage; review required."}
    result["workflow"] = {"status": "unverified", "expected_terminal": criteria["expected_terminal"]}
    evidence.atomic_json(out / "result.json", result)
    attempt.update(status="checks_passed" if result["pass"] else "incomplete" if validity_reasons else "failed",
                   ended_at=time.time(), pass_checks=result["pass"], qualification="pending_review")
    evidence.atomic_json(out / "attempt.json", attempt)
    evidence.seal(out)
    style = json.loads(CASES.read_text()).get(name, {}).get("style") if name != "custom" else None
    row = baseline_row(result, style, args.suite_name)
    # A baseline measures one host running a case from the start; a resumed run is not one.
    baseline_file = args.baseline if not resumed else None
    before = previous_row(baseline_file, name, versions["source"], conditions) if baseline_file else None
    if baseline_file:
        with baseline_file.open("a") as handle:
            handle.write(json.dumps(row) + "\n")

    mark = lambda ok: "PASS" if ok else "FAIL"  # noqa: E731
    print(f"{mark(result['pass'])} mechanical checks (qualification pending review)  shiploop e2e case={name} host={args.host}  output={out}")
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


def main(argv: list[str] | None = None) -> int:
    attempt = {}
    try:
        return _main(argv, attempt=attempt)
    except (Exception, SystemExit, KeyboardInterrupt) as exc:
        # Existing directories and invalid arguments have no output ownership.
        # Once allocated, every failure leaves a terminal receipt and result.
        if not attempt.get("output"):
            raise
        out = Path(attempt["output"])
        monitor = attempt.pop("monitor", None)
        ci = monitor.close() if monitor else None
        stopped = "interrupted" if isinstance(exc, KeyboardInterrupt) else "blocked_preflight" if attempt.get("status") == "preflight" else "incomplete"
        attempt.update(status=stopped, ended_at=time.time(), pass_checks=False, reason=str(exc) or type(exc).__name__)
        evidence.atomic_json(out / "attempt.json", attempt)
        observed = None
        try:
            observed = evidence.read_json(out / "result.json")
        except (OSError, ValueError):
            pass
        result = {"schema": "shiploop-e2e-result/2", "case": attempt.get("case"), "pass": False,
                  "attempt_id": attempt.get("attempt_id"), "output": str(out),
                  "evidence": {"status": "incomplete", "reasons": [attempt["reason"]]},
                  "qualification": {"status": "incomplete", "clean": False},
                  "process": {"status": stopped, "pass": False, "ci": ci},
                  "observations_before_error": observed}
        evidence.atomic_json(out / "result.json", result)
        if isinstance(exc, (SystemExit, KeyboardInterrupt)):
            raise
        print(f"INCOMPLETE shiploop e2e: {attempt['reason']} (see {out / 'attempt.json'})", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
