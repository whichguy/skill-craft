#!/usr/bin/env python3
"""Run ShipLoop end to end from one prompt in a new, empty directory.

Each run creates a fresh empty working directory, invokes the ShipLoop skill
there with one headless host process, shows its progress live, and grades:

  invoked   the host registered the invoked skill command, so the prompt went
            to the skill (Claude: /skill-craft:shiploop; Grok: /shiploop, since
            Grok does not namespace plugin skills)
  plugin    exactly one skill-craft plugin loaded, and it is the build under test
            (a resumed or regraded Grok or Codex run keeps its first launch's
            verdict, which invocation.json records; Claude shows it in its events)
  process   the host exited 0 within the timeout
  shiploop  a ShipLoop state.md under the output directory reports status
            "done" and its report.html exists
  committed the source checkout ends committed: HEAD moved past where the run
            started, holds at least one file (ShipLoop's own empty baseline
            commit is not product) and no product path is left uncommitted
            (logs aside)
  checks    every case check command exits 0 in the working directory

--seed-at step-plan starts an Ask-Agent run whose stages before step-plan are
recorded without doing them (the case prompt is the specification), so a host
reaches the implementation chain in minutes instead of hours of planning. The
host then follows ShipLoop's own packets from step-plan. A seeded run is also
graded on `chain` (every step accepted and at least two workers in flight
together) and writes no baseline row, since it does not start from intake.

A follow-on case (`follows` in cases.json) runs a second feature in a copy of an
earlier run's source checkout (--continue-from <earlier output>), to see whether
ShipLoop builds on what the first run decided. Its checks are the followed
case's checks (regression), its own feature checks and retention checks, which
get $PRIOR_WORK (the earlier checkout, read only).

Besides the verdicts, metrics.json records where ShipLoop spent turns, tokens,
cost and time (per accepted stage), its failed commands, host truncations,
compactions and the knowledge-home facts (see metrics.py). The run's Run Review
documents go to <output>/review-export/ (skills/shiploop-run-review/);
an export problem is printed and never changes a verdict.

The default host is Claude (Sonnet 5.5, claude-sonnet-5-5). By default the run tests
what the whichguy marketplace publishes now (--source marketplace, gated on
local HEAD == origin/main and matching versions); --source checkout builds
this checkout instead. The host is isolated from the user's configuration:

  grok    a throwaway HOME whose .grok holds only a symlink to the user's
          auth.json and the plugin under test, so neither the user's Grok
          plugins nor anything Grok inherits from ~/.claude load, and nothing
          is installed into the real profile
  claude  --setting-sources project,local plus --plugin-dir, so the user's
          plugins and hooks stay out, and --strict-mcp-config, so none of the
          account's claude.ai connectors load (~/.claude/CLAUDE.md still loads)

A Grok session that ends while the ShipLoop run is still active is resumed
(bounded by --max-resumes). Every attempt keeps its prompt, argv, event
stream, arrival timeline, stderr, metrics.json and result.json in a new
output directory outside the checkout.

--resume-run on a run whose ShipLoop is already done or blocked (a regrade) starts no
host. It restates the run's own last record (result.json, else invocation.json): host,
model, effort, plugin verdict and the process block, whatever --host, --model or
--effort say, and grades ShipLoop, the checkout and the checks again. A host that
failed stays failed; a run with no record of its exit says "not observed" and leaves
the process verdict out of the result. A blocked run waits for a person (SPEC S-14), so
it is never resumed as if answered: it is only graded again, which refreshes its
metrics.json and result.json. An active run is a real resume. --grade-only does the
same regrade for a run in any status that has a ShipLoop state, for a run whose harness
was killed with its host and so never wrote its records. Creating <output>/stop ends a
running host on purpose: it is not relaunched, the records are written, and the exit
code is non-zero.
This launches a real model and costs money; it is never part of default CI.

  python3 test/shiploop_e2e/run.py --case battleship
  python3 test/shiploop_e2e/run.py --case battleship-scoring --continue-from <battleship output>
  python3 test/shiploop_e2e/run.py --case hello --host claude
  python3 test/shiploop_e2e/run.py --case temperature-report --host codex --effort xhigh --seed-at step-plan
  python3 test/shiploop_e2e/run.py --prompt "..." --check "python3 -m unittest"
"""

from __future__ import annotations

import argparse
import atexit
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import importlib.util
import json
import os
from pathlib import Path
import re
import secrets
import shlex
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
import listeners  # noqa: E402
import metrics  # noqa: E402
import shiploop_knowledge_home as knowledge_home  # noqa: E402
import shiploop_chain_ledger as chain_ledger  # noqa: E402
import shiploop_store as store  # noqa: E402

CASES = HERE / "cases.json"
SUITES = HERE / "suites.json"
BASELINES = HERE / "baselines.jsonl"
REVIEW_EXPORTER = ROOT / "skills" / "shiploop-run-review" / "scripts" / "export.py"
PLUGIN_NAME = "skill-craft"
# How often a running host is checked for its deadline, a requested stop and an interrupt.
POLL_SECONDS = 2
# Hosts this process has started and not yet reaped, by the pid of the leader of the group it leads. A host starts in a
# session of its own (start_new_session=True), so a SIGTERM to the harness does not reach it: on 2026-10-08 the Grok host of a
# round-2 run went on working for about 28 minutes after the harness died of one, with nothing collecting its events.
LIVE_HOST_GROUPS: set[int] = set()
# Set when the harness was told to end (SIGTERM, SIGHUP): every launch and every resume treats it as a requested stop.
TERMINATION = threading.Event()
TERMINATED_BY: list[str] = []  # the name of the first signal, for the record
HANDLED_SIGNALS: list[int] = []  # the signals install_termination_handlers took over


def kill_group(pid: int) -> None:
    """SIGKILL the process group `pid` leads. A group already gone, or a reused one that is not ours, is left alone."""
    try:
        os.killpg(pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass


def end_live_hosts() -> None:
    """Kill every host session that is running. Also runs at exit, so a Ctrl-C or a crash leaves no orphan host."""
    for pid in tuple(LIVE_HOST_GROUPS):  # a copy: suite worker threads add and discard concurrently
        kill_group(pid)


atexit.register(end_live_hosts)


def on_termination(signum, frame) -> None:
    """A SIGTERM or SIGHUP reached the harness: end every host at once and let main write the records as a requested stop."""
    TERMINATED_BY.append(signal.Signals(signum).name)
    TERMINATION.set()  # before the kill, so a launch that finds its host dead already knows why
    end_live_hosts()
    for number in HANDLED_SIGNALS:
        signal.signal(number, signal.SIG_DFL)  # a second signal means it: the default action ends the harness now


def install_termination_handlers() -> list[int]:
    """Take over SIGTERM and SIGHUP, except one the launch ignored: `nohup` keeps a run alive through a hangup by ignoring it."""
    for number in (signal.SIGTERM, signal.SIGHUP):
        if signal.getsignal(number) is not signal.SIG_IGN:
            signal.signal(number, on_termination)
            HANDLED_SIGNALS.append(number)
    return list(HANDLED_SIGNALS)


def stop_cause(stop_file: Path) -> str:
    """Why a run ended on purpose: a signal that told the harness to end, or a stop file."""
    if TERMINATION.is_set():
        return f"terminated by {TERMINATED_BY[0] if TERMINATED_BY else 'a signal'}"
    return f"stopped by {stop_file}"


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
        done = subprocess.run(["gh", "run", "list", "--repo", "whichguy/skill-craft", "--commit", commit,
                               "--json", "status,conclusion"], capture_output=True, text=True, timeout=60)
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
            turns = event.get("num_turns")
            self.emit(f"done  {metrics.session_stop(event) or 'ended'} turns={'not reported' if turns is None else turns} "
                      f"cost={metrics.money(event.get('total_cost_usd'))}")

    def tool(self, name, arg):
        arg = arg if isinstance(arg, dict) else {}
        detail = next((arg[k] for k in ("command", "cmd", "file_path", "target_file", "target_directory", "pattern",
                                    "path", "skill", "description") if arg.get(k)), "")
        self.emit(f"tool  {name}: " + " ".join(str(detail).split())[:140])


def keep_awake(argv: list[str]) -> list[str]:
    """The host's argv, run under `caffeinate -d -i` on macOS and unchanged elsewhere.

    A run takes an hour or more. -i keeps the machine from idle-sleeping, which otherwise freezes the host mid-stage
    and stretches every stage timing. -d keeps the display on: on 2026-10-07 the display was off from 06:04 to 10:10
    (pmset log), the whole window in which headless Chrome never loaded a page for the Grok run, and on 2026-10-06,
    display on, the same host loaded it. That is a correlation, not a proven cause (a display woken with
    `caffeinate -u -d` still hung once), so this removes a variable and claims nothing more.
    """
    caffeinate = shutil.which("caffeinate") if sys.platform == "darwin" else None
    return [caffeinate, "-d", "-i", *argv] if caffeinate else argv


def launch(argv: list[str], work: Path, out: Path, env: dict, timeout: int, watch: bool,
           first: bool = True, fresh: bool = True, translate=None, stop_when=None, stop_file: Path | None = None) -> dict:
    """Run one host session. `stop_when`, polled every POLL_SECONDS, kills the session (status "interrupted").

    A `stop_file` that exists kills it the same way with status "stopped": a person's request to end the run
    (the caller consumes the file). So does a SIGTERM or SIGHUP to the harness (TERMINATION, set by on_termination, which
    has already killed the host's group): the session reads as "stopped". One that begins after the harness was told to end
    (during the install, say) is ended at its first poll, with its files in place so the run's records can still be written.
    The deadline wins over all.

    The result carries ``stop``: the host's own reason from the last end/result event this
    session wrote, or None when it wrote none (killed, crashed), so a termination record can
    hold one entry per session and say unknown for the ones that never reported.

    It also carries ``left_behind``: the listeners the session left under `out` (a model's backgrounded
    server), stopped as the session ends and recorded (see listeners.py).
    """
    if first and fresh:
        # The skill must start from a directory with nothing in it.
        leftover = sorted(p.name for p in work.iterdir())
        if leftover:
            raise SystemExit(f"working directory is not empty: {leftover}")
    start = time.time()
    view = LiveView(start, watch)
    mode = "wb" if first else "ab"  # a resumed session appends to the same streams
    stop = None
    events_path = out / "events.jsonl"
    if first:
        line = 0
    else:
        with events_path.open("rb") as existing:
            line = sum(1 for _ in existing)
    argv = keep_awake(argv)
    with events_path.open(mode) as events, (out / "stderr.txt").open(mode) as stderr, \
            (out / "timeline.jsonl").open("w" if first else "a") as stamps:
        proc = subprocess.Popen(argv, cwd=work, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                stderr=stderr, env=env, start_new_session=True)
        LIVE_HOST_GROUPS.add(proc.pid)  # a signal to the harness now ends this group (on_termination)

        def record(raw: bytes):
            nonlocal line, stop
            events.write(raw)
            events.flush()
            number, line = line, line + 1
            try:
                event = json.loads(raw)
            except ValueError:
                return
            if isinstance(event, dict):
                if event.get("type") in ("end", "result"):
                    stop = metrics.session_stop(event)
                # Grok events carry no time; stamp the ones metrics.py attributes.
                if event.get("type") not in ("text", "thought"):
                    stamps.write(json.dumps({"line": number, "t": round(time.time(), 3)}) + "\n")
                    stamps.flush()
                view.event(event)

        def pump():
            # The host's translator turns its stream into the shared event shape.
            for original in proc.stdout:
                for raw in (translate or (lambda b: [b]))(original):
                    record(raw)
            view.flush_text()

        reader = threading.Thread(target=pump, daemon=True)
        reader.start()
        deadline = time.time() + timeout
        status = None
        try:
            while proc.poll() is None:
                if time.time() >= deadline:
                    status = "timeout"
                elif (stop_file is not None and stop_file.exists()) or TERMINATION.is_set():
                    status = "stopped"
                elif stop_when is not None and stop_when():
                    status = "interrupted"
                if status:
                    # The whole process group: the host and any native workers it started.
                    kill_group(proc.pid)
                    proc.wait()
                    break
                try:
                    # Wake the moment the session ends; a plain sleep held the caller for the rest of the tick.
                    proc.wait(timeout=POLL_SECONDS)
                except subprocess.TimeoutExpired:
                    pass
        finally:
            if proc.poll() is not None:
                LIVE_HOST_GROUPS.discard(proc.pid)  # reaped: its pgid may be reused, so it is never signalled again
        if status is None:
            # A signal may have killed the group before this loop saw it: that is a stop, not a host failure.
            status = "stopped" if TERMINATION.is_set() else "exited" if proc.returncode == 0 else "failed"
        reader.join(timeout=10)
        proc.stdout.close()
    return {"status": status, "returncode": proc.returncode,
            "elapsed_seconds": round(time.time() - start, 1), "stop": stop, "left_behind": listeners.reap(out)}


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
            # The stop is the host's own reason, an error never a success (metrics.session_stop, the one rule).
            stop = metrics.session_stop(event)
            seen.setdefault("sessions", []).append(
                {"num_turns": event.get("num_turns"), "cost_usd": event.get("total_cost_usd"), "stop": stop})
            seen.update(stop=stop)
    ended = seen.get("sessions") or []
    if ended:
        # Each host session reports its own totals; a resumed run adds them up. The cost is
        # unknown unless every ended session reported one (metrics.total_cost, the one rule),
        # and the turns are unknown unless one did: a count nobody reported is not 0.
        reported = [s["num_turns"] for s in ended if isinstance(s["num_turns"], int)
                    and not isinstance(s["num_turns"], bool)]
        seen["num_turns"] = sum(reported) if reported else None
        seen["cost_usd"] = metrics.total_cost(ended)
    return seen


def _runs_shiploop_cli(command: str) -> bool:
    # Claude often builds the path from a variable (SKILL_ROOT=.../skills/shiploop; $SKILL_ROOT/scripts/shiploop).
    return "skills/shiploop" in command and "scripts/shiploop" in command


def shiploop_cli_ran(events_path: Path) -> bool:
    """Whether any tool call ran the installed ShipLoop CLI (Grok/Codex tool_call or Claude tool_use events)."""
    for line in events_path.read_text(errors="replace").splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if not isinstance(event, dict):
            continue
        if event.get("type") == "tool_call":
            arg = event.get("rawInput") if isinstance(event.get("rawInput"), dict) else {}
            if "skills/shiploop/scripts/shiploop" in str(arg.get("command") or ""):
                return True
        elif event.get("type") == "assistant" and isinstance(event.get("message"), dict):
            for block in event["message"].get("content") or []:
                if isinstance(block, dict) and block.get("type") == "tool_use" and isinstance(block.get("input"), dict):
                    if _runs_shiploop_cli(str(block["input"].get("command") or "")):
                        return True
    return False


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


def shiploop_cli(plugin_dir: Path) -> Path:
    """The ShipLoop CLI file of a plugin build."""
    return plugin_dir / "skills" / "shiploop" / "scripts" / "shiploop"


def run_cli(host_name: str, out: Path, plugin_dir: Path) -> Path:
    """The ShipLoop CLI a run uses: the copy its host installed into the run's profile (Grok, Codex), else the plugin
    build itself (Claude loads --plugin-dir directly). The one place the seed and every resume prompt get it from."""
    return hosts.host(host_name).plugin_cli(out / "home") or shiploop_cli(plugin_dir)


def resume_prompt(run_dir: str | None, cli: Path) -> str:
    """The prompt that continues a run: the exact command of the CLI the run started on (SPEC: a resume names the
    CLI the run itself uses). There is no bare-command form; main refuses a resume whose CLI file is gone."""
    if run_dir is None:
        return ("This session ended before the ShipLoop run was started. Continue the original "
                "request now: start the ShipLoop run as its skill directs and follow each packet to "
                "the end of the run. Never end the turn while a ShipLoop command is still running.")
    return ("This session ended while the ShipLoop run was still active. Continue it now: run "
            f"`python3 \"{cli}\" next --run-dir \"{run_dir}\"` and follow the packet it prints, to the end of the "
            "run. Never end the turn while a ShipLoop command is still running.")


def resume_command(out: Path, args) -> str:
    """The exact command that continues this run in place, with the harness flags that bound it.

    invocation.json keeps the host's argv and not the harness flags, so a command with only --resume-run would
    fall back to the default --timeout, which is above the limit of a launching task (a task kill leaves no
    records). The binary flag is carried because a fake or a non-default binary is part of the invocation.
    """
    parts = ["python3", str(Path(__file__).resolve()), "--resume-run", str(out), "--host", args.host,
             "--model", args.model, *(["--effort", args.effort] if args.effort else []),
             "--timeout", str(args.timeout), "--max-resumes", str(args.max_resumes),
             "--max-budget-usd", str(args.max_budget_usd), "--permission-mode", args.permission_mode]
    binary = getattr(args, args.host + "_bin")
    if binary != parser().get_default(args.host + "_bin"):
        parts += [f"--{args.host}-bin", binary]
    if args.source == "checkout" and args.plugin_dir:
        parts += ["--plugin-dir", str(args.plugin_dir)]
    return shlex.join(parts)


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


SEED_STAGES = ("step-plan",)
# Runs in a separate interpreter on the installed plugin's own navigator, so the
# seeded state is exactly what that version's CLI reads back.
SEED_SCRIPT = """
import json, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import shiploop_navigator as nav, shiploop_store as store
run_dir, stop = Path(sys.argv[2]), sys.argv[3]
state = store.read_record(run_dir / "state.md")
skipped = []
while nav.current_stage(state) != stop:
    stage, action = nav.current_stage(state), str(nav.current_action(state)["id"])
    result = {"outcome": "done", "summary": "Synthetic: recorded by the E2E seed without doing it; "
              "the request is the specification."}
    if stage == "plan":
        result["work_items"] = [{"id": "seeded-request", "title": "The whole request"}]
    state = nav.apply(state, action, result)
    if state["active_improve"] is not None:
        state = nav.finish_improve(state, action, {"summary": "Synthetic Improve receipt from the E2E seed."})
    skipped.append(stage)
    nav.save(run_dir, state)
print(json.dumps({"skipped": skipped, "stage": nav.current_stage(state),
                  "action": str(nav.current_action(state)["id"]), "delegation": state.get("delegation")}))
"""


def seed_run(cli: Path, work: Path, out: Path, prompt: str, stop: str) -> dict:
    """Start an Ask-Agent run and record its stages before `stop` as synthetic.

    ShipLoop refuses a repository without a commit, so the seed commits a README first.
    """
    (work / "README.md").write_text("# Seeded ShipLoop E2E case\n")
    # The seed must not depend on the machine's Git config: a global or system filter (for example git-lfs on a
    # CI runner) would make ShipLoop's workspace refuse the repository.
    git_env = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}
    identity = ["-c", "user.name=ShipLoop E2E seed", "-c", "user.email=shiploop-e2e-seed@example.invalid"]
    for args in (["init", "-q"], ["add", "README.md"], [*identity, "commit", "-qm", "seed: baseline"]):
        subprocess.run(["git", "-C", str(work), *args], check=True, capture_output=True, text=True, env=git_env)
    head = subprocess.run(["git", "-C", str(work), "rev-parse", "HEAD"], check=True, capture_output=True,
                          text=True, env=git_env).stdout.strip()
    root = out / ".shiploop-runs" / "seed"
    started = subprocess.run([sys.executable, str(cli), "workspace", "start", f"--repo={work}",
                              f"--workspace-root={root}", "--delegation=ask-agent", f"--prompt={prompt}"],
                             capture_output=True, text=True, env=git_env)
    if started.returncode:
        raise SystemExit(f"seed: workspace start failed: {(started.stderr or started.stdout)[-2000:]}")
    run_dir = root / "run"
    advanced = subprocess.run([sys.executable, "-c", SEED_SCRIPT, str(cli.parent), str(run_dir), stop],
                              capture_output=True, text=True, env=git_env)
    if advanced.returncode:
        raise SystemExit(f"seed: could not advance the run to {stop}: {advanced.stderr[-2000:]}")
    return {"stage": stop, "run_dir": str(run_dir), "start_head": head, **json.loads(advanced.stdout)}


def seed_prompt(cli: Path, run_dir: str, prompt: str) -> str:
    return (f"A ShipLoop run for the request below is already active, with Ask-Agent delegation. The test "
            "harness recorded its stages before step-plan without doing them, so the request itself is the "
            f"specification. Continue the run now: run `python3 \"{cli}\" next --run-dir \"{run_dir}\"` and "
            "follow the packet it prints, to the end of the run. Never end the turn while a ShipLoop command "
            f"is still running.\n\nThe request: {prompt}")


CHAIN_DEFAULTS = {"min_steps": 2, "min_in_flight": 2, "min_depth": 1}


def _bindings(out: Path):
    for binding_path in sorted(out.rglob("chains/*/binding.md")):
        if binding_path.relative_to(out).parts[0] not in ("home", "build", "marketplace"):
            yield binding_path


def _depth(deps: dict[str, list[str]]) -> int:
    """Steps on the longest dependency path (1 = no step depends on another)."""
    memo: dict[str, int] = {}

    def level(step: str, seen: frozenset = frozenset()) -> int:
        if step not in memo:
            memo[step] = 1 + max((level(d, seen | {step}) for d in deps.get(step, []) if d not in seen), default=0)
        return memo[step]
    return max((level(step) for step in deps), default=0)


def chain_facts(out: Path, expect: dict | None = None) -> dict:
    """ShipLoop chain evidence from files only, never from the model's account.

    For each binding under run/chains/<action>/, from the dispatcher state and the
    bridge ledger (in ledger order): steps accepted, native vs main-context
    attempts, the most launched workers not yet imported (fan-out), each step's
    integrations (contribution_recorded; exactly one each), and whether every step
    launched only after each dependency was integrated. `expect` (a case's
    "chain" entry) sets min_steps, min_in_flight and min_depth.
    """
    expect = {**CHAIN_DEFAULTS, **(expect or {})}
    chains = []
    for binding_path in _bindings(out):
        fact = {"binding": str(binding_path)}
        try:
            binding = store.read_record(binding_path)
            state_file = Path(binding["dispatcher_run"]) / "plan-dispatcher-state.json"
            state = json.loads(state_file.read_text()) if state_file.is_file() else {"steps": {}, "attempts": {}}
            events = chain_ledger.read_events(str(binding_path.parent / "events"))
        except (store.StorageError, ValueError, KeyError, OSError) as exc:
            chains.append(dict(fact, error=str(exc)))
            continue
        attempts = state.get("attempts", {})
        steps = state.get("steps", {})
        deps = {s["id"]: list(s.get("deps") or []) for s in (state.get("graph") or {}).get("steps", [])}
        step_of = {attempt: record.get("step") for attempt, record in attempts.items()}
        in_flight, most, after_retry, retried = set(), 0, 0, False
        first_launch, integrated, integrations = {}, {}, {}
        for row in events:
            event = row["event"]
            data = event.get("data") or {}
            attempt = data.get("attempt")
            step = data.get("step") or step_of.get(attempt)
            if event["kind"] == "launched_result":
                in_flight.add(attempt)
                most = max(most, len(in_flight))
                if retried:
                    after_retry = max(after_retry, len(in_flight))
                first_launch.setdefault(step, event["seq"])
            elif event["kind"] in ("handoff_import_result", "retry_result"):
                # A retried attempt was lost or rejected; it is no longer running work for the chain.
                in_flight.discard(attempt)
                retried = retried or event["kind"] == "retry_result"
            elif event["kind"] == "contribution_recorded":
                integrations[step] = integrations.get(step, 0) + 1
                integrated.setdefault(step, event["seq"])
        out_of_order = sorted(step for step, needs in deps.items() if step in first_launch and any(
            dep not in integrated or integrated[dep] > first_launch[step] for dep in needs))
        accepted = sum(1 for s in steps.values() if s.get("status") == "accepted")
        fact.update({
            "mode": binding.get("mode"),
            "steps": len(steps),
            "accepted": accepted,
            "depth": _depth(deps),
            "native_attempts": sum(1 for a in attempts.values() if a.get("handle")),
            "main_context_attempts": sum(1 for a in attempts.values() if a.get("executor")),
            "attempts": len(attempts),
            "max_in_flight": most,
            "max_in_flight_after_retry": after_retry if retried else None,
            "out_of_order": out_of_order,
            "integrated_twice": sorted(step for step, count in integrations.items() if count > 1),
            "not_integrated": sorted(step for step in steps if integrations.get(step, 0) == 0),
            "events": len(events),
        })
        fact["pass"] = (fact["steps"] >= expect["min_steps"] and accepted == fact["steps"]
                        and fact["depth"] >= expect["min_depth"] and most >= expect["min_in_flight"]
                        and not out_of_order and not fact["integrated_twice"] and not fact["not_integrated"])
        chains.append(fact)
    return {"pass": any(c.get("pass") for c in chains), "expect": expect, "bindings": chains}


RECOVERY_SOURCE = ("SPEC S-6 (runs survive session resumes) and S-14 (unattended by default): a fresh session "
                   "recovers the chain without a person")


def run_minutes(run_dir: str | None) -> float | None:
    """Minutes from ShipLoop's run start to its last accepted action, from the run's own timeline.

    It survives killed sessions, and includes any pause between a kill and its resume.
    """
    if not run_dir:
        return None
    try:
        timeline = json.loads((Path(run_dir) / "timeline.json").read_text())
        stamps = [datetime.strptime(v, "%Y-%m-%dT%H:%M:%SZ") for v in timeline.get("accepted", {}).values()]
        start = datetime.strptime(timeline["started"], "%Y-%m-%dT%H:%M:%SZ")
    except (OSError, ValueError, KeyError, TypeError):
        return None
    return round((max(stamps) - start).total_seconds() / 60, 1) if stamps else None


def budget_facts(budget: dict | None, seeded: bool, run_dir: str | None, interrupted: bool = False) -> dict | None:
    """A should-level expectation: reported beside the verdicts, never failing the run.

    An interrupted run is not held to it: the deliberate kill makes the run replay its lost
    workers' work, so its time measures recovery, not the request (c1, 2026-10-04: 30.9 min).
    """
    if not budget or not seeded or "seeded_minutes" not in budget:
        return None
    observed = run_minutes(run_dir)
    if interrupted:
        return {"level": "should", "applies": False, "expected_minutes": budget["seeded_minutes"],
                "observed_minutes": observed, "pass": None, "source": budget.get("source"),
                "reason": "interrupted on purpose: recovery replays the lost workers' work"}
    return {"level": "should", "applies": True, "expected_minutes": budget["seeded_minutes"],
            "observed_minutes": observed, "pass": observed is not None and observed <= budget["seeded_minutes"],
            "source": budget.get("source")}


MISMATCH_TEMPLATE = """# Mismatch: {case} on {host} ({output})

Fill in every field, then record the decision in test/shiploop_e2e/LEARNINGS.md.

## Expected
{expected}

## Observed
{observed}

## Triage (answer in order; stop at the first yes)
1. Is the check itself wrong? (Does it pass a reference solution and fail an empty one? If not, fix the test.)
2. Is it the environment? (Network, session limits, host outages: fix the harness or ops; the expectation stands.)
3. Is it reproduced, or is its trigger clear? (If not, rerun before changing anything.)
4. Does the expectation describe how instead of what? (Then the expectation changes.)
5. Would a normal run hit it? (If not, document it as a known limit.)
6. Does the behaviour come from a deliberate design rule? (Then two intents conflict: the owner decides.)
7. Does the expectation trace to its source? (Then the product changes. An expectation with no source gets one first, or is dropped.)

## Why

## Decision (product / expectation / owner / known limit / environment)

## Verified by
"""


def write_mismatch(out: Path, name: str, host: str, failed: list[tuple[str, str, str]]) -> Path:
    """One file per failing run, pre-filled with each failed must-level expectation and what was observed."""
    expected = "\n".join(f"- **{verdict}**: {want}" for verdict, want, _ in failed)
    observed = "\n".join(f"- **{verdict}**: {got}" for verdict, _, got in failed)
    path = out / "mismatch.md"
    path.write_text(MISMATCH_TEMPLATE.format(case=name, host=host, output=out, expected=expected, observed=observed))
    return path


def chain_in_flight(out: Path) -> bool:
    """Whether some chain worker has launched and its result is not yet imported."""
    for binding_path in _bindings(out):
        try:
            events = chain_ledger.read_events(str(binding_path.parent / "events"))
        except (ValueError, OSError):
            continue
        open_attempts = set()
        for row in events:
            event = row["event"]
            attempt = (event.get("data") or {}).get("attempt")
            if event["kind"] == "launched_result":
                open_attempts.add(attempt)
            elif event["kind"] in ("handoff_import_result", "retry_result"):
                open_attempts.discard(attempt)
        if open_attempts:
            return True
    return False


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
            "head_files": len(g("ls-tree", "-r", "--name-only", "HEAD").splitlines()),
            "untracked_files": len(untracked),
            "branches": g("branch", "--format=%(refname:short)").split()}


def committed_facts(knowledge: dict, start_head: str | None) -> dict:
    """The ``committed`` verdict: the product is in HEAD, and none of it is left outside.

    HEAD must have moved past where the run started, hold at least one file and leave no product
    path uncommitted (logs aside). The file count is what makes the first test mean something: on a
    fresh run ShipLoop's first act is an empty baseline commit, so HEAD always differs from a start
    with no commit, and a run that ended before it returned anything would otherwise pass.

    Known limit, not guarded: any file counts. A future ShipLoop that returned only knowledge files
    (docs/shiploop/) to the source checkout before the product would pass early; today those stay in
    ShipLoop's worktree until the product is returned.
    """
    head, files = knowledge["head"], knowledge["head_files"]
    return {"pass": bool(head) and head != start_head and files > 0 and not knowledge["uncommitted"],
            "start_head": start_head, "head": head, "head_files": files,
            "uncommitted": knowledge["uncommitted"][:20]}


def review_export(out: Path) -> str:
    """Export the run's Run Review documents (skills/shiploop-run-review/SKILL.md). Fail-open: a problem is reported in
    the returned line and never changes a verdict or the exit code."""
    try:
        if not REVIEW_EXPORTER.is_file():
            return f"review export skipped: no exporter at {REVIEW_EXPORTER}"
        spec = importlib.util.spec_from_file_location("run_review_export", REVIEW_EXPORTER)
        exporter = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(exporter)
        return f"review export: {exporter.export_run(out)}"
    except Exception as exc:  # noqa: BLE001 - any export failure is reported, never raised
        return f"review export skipped: {' '.join(str(exc).split())[:300] or type(exc).__name__}"


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
    p.add_argument("--resume-run", type=Path,
                   help="an earlier run's output directory whose ShipLoop run stopped while active (a host ran "
                        "out of credits, a machine slept): continue that same run in place, on --host, and grade "
                        "it as usual. The case and checks come from the earlier run. A run that is already "
                        "done or blocked is only graded again (a regrade): no host starts, so its metrics.json "
                        "and result.json are refreshed and a blocked run is not resumed as if answered. "
                        "The harness prints the exact command that continues a run when it starts and when it "
                        "ends with the run still active.")
    p.add_argument("--grade-only", action="store_true",
                   help="with --resume-run: start no host for any run, whatever its status, and write metrics.json, "
                        "result.json and the review export from what is on disk. For a run whose harness was killed "
                        "with its host (a task limit, an owner kill) and so never wrote them. Stop the host first: "
                        "a live host makes this a mid-run snapshot.")
    p.add_argument("--continue-from", type=Path,
                   help="an earlier run's output directory: start in a copy of its source checkout "
                        "(required by follow-on cases, which name the case they follow)")
    p.add_argument("--seed-at", choices=SEED_STAGES,
                   help="start an Ask-Agent run at this stage, with the earlier stages recorded without doing "
                        "them, to reach the implementation chain without hours of planning; also grades the chain")
    p.add_argument("--interrupt-at", choices=("chain-launched",),
                   help="kill the host (and its workers) as soon as a chain worker is in flight, then resume the "
                        "run with a fresh session; graded as `recovery`")
    p.add_argument("--check", action="append", help="extra shell check run in the work dir (repeatable)")
    p.add_argument("--output", type=Path, help="new directory for this attempt (default: under $TMPDIR)")
    p.add_argument("--host", choices=[*sorted(hosts.HOSTS), "all"], default="claude",
                   help="the host that drives ShipLoop; 'all' only with --preflight-only (checks every host)")
    p.add_argument("--model", help="default: claude-sonnet-5-5 (claude) or grok-4.7 (grok)")
    p.add_argument("--effort", help="reasoning effort; default: host default (claude), medium (grok)")
    p.add_argument("--skill", help="command that invokes ShipLoop; default: skill-craft:shiploop (claude), shiploop (grok)")
    p.add_argument("--source", choices=("marketplace", "checkout"), default="marketplace",
                   help="marketplace (default): test what the whichguy marketplace publishes now, gated on "
                        "local HEAD == origin/main and matching versions; checkout: build this checkout")
    p.add_argument("--preflight-only", action="store_true",
                   help="pull skill-craft from the marketplace into a fresh profile, print what main publishes "
                        "and what the host installed, and exit non-zero if the version gate refuses")
    p.add_argument("--plugin-dir", type=Path, help="test this skill-craft plugin build (implies --source checkout)")
    p.add_argument("--max-turns", type=int, default=10000)
    p.add_argument("--max-budget-usd", type=float, default=40.0, help="claude only; grok has no spend cap")
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
    p.add_argument("--grok-bin", default="grok")
    p.add_argument("--claude-bin", default="claude")
    p.add_argument("--codex-bin", default="codex")
    return p


def host_given(argv: list[str]) -> bool:
    """Whether --host was passed at all (argparse cannot tell a default from the same value given)."""
    probe = parser()
    probe.set_defaults(host=None)
    return probe.parse_args(argv).host is not None


def baseline_stages(stages: list | None) -> list | None:
    """The per-stage fields worth committing: enough to locate a regression, no more.

    `tool_calls` stays in the run's own metrics.json, which is
    disposable; a committed baseline only needs what a comparison reads, plus the
    markers that say a row is not comparable. A counter the host did not report is
    committed as null (see metrics.per_stage), never as 0.
    """
    if stages is None:
        return None
    keep = ("stage", "outcome", "seconds", "turns", "timing", "incomplete")
    return [{k: row[k] for k in keep if k in row} for row in stages if isinstance(row, dict)]


def baseline_row(result: dict, style: str | None, suite: str | None,
                 planning_review: str = metrics.NOT_RECORDED) -> dict:
    """One comparable summary of a run: the per-case history the suites judge against (SPEC: E2E suites).

    Carries host, model and effort because a baseline compares only with rows
    from the same three (SPEC: the driver is a parameter, not a code path), and
    per-stage rows so a regression can be located in a stage rather than only in
    a whole-run total. ``baseline_stages`` decides which stage fields are worth
    committing; the full rows stay in the run's own metrics.json. A counter the host's
    events cannot show is null here and named in ``unmeasured``, so a later run on that
    host compares it as not measured and never as 0 -> 0. ``planning_review`` is the
    run's option as its state.md recorded it (``metrics.planning_review``): a run is
    compared only with a row of the same mode (``planning_review_line``).
    """
    m = result.get("metrics") or {}
    versions = result.get("versions") or {}
    return {"date": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "case": result.get("case"), "style": style,
            "suite": suite, "host": result.get("host"), "model": result.get("model"),
            "effort": result.get("effort"), "stages": baseline_stages(m.get("stages")),
            "termination": result.get("termination"), "unmeasured": sorted(m.get("unmeasured") or {}),
            "source": versions.get("source"), "plugin_version": versions.get("plugin_version"),
            "shiploop_version": versions.get("shiploop_version"), "planning_review": planning_review,
            "pass": result.get("pass"),
            "verdicts": {k: (result.get(k) or {}).get("pass") for k in ("invoked", "plugin", "process",
                                                                       "shiploop", "committed")},
            "checks_passed": sum(bool(c.get("pass")) for c in result.get("checks") or []),
            "checks": len(result.get("checks") or []),
            "turns": m.get("turns"), "cost_usd": m.get("cost_usd"),
            "sessions": len((result.get("process") or {}).get("sessions") or []),
            "cancelled_tool_calls": m.get("cancelled_tool_calls"), "model_glue": m.get("model_glue"),
            "tmp_writes": m.get("tmp_writes"),
            "shiploop_failures": m.get("shiploop_failures"), "compactions": m.get("compactions"),
            "truncated_outputs": m.get("truncated_outputs"), "narrative": m.get("narrative"),
            "output": result.get("output")}


# `planning_review` (state.md key, ShipLoop 1.22.0 and later) says which planning results start an Improve child: `stage`
# after each of spec, test-strategy, plan, step-plan and test-spec, `none` after none of them. Planning minutes, Improve
# passes and turns are not the same quantity in the two modes, so a run is compared with the last row of its own mode
# (the same case, source, host, model and effort as ever) and never with a row of the other mode; when no earlier row of
# that driver has the run's mode, nothing is compared and the report says so (`planning_review_line`). A row written before
# the field existed has no mode; it stands for `stage` only when its recorded plugin_version is below
# PLANNING_REVIEW_FIRST_RELEASE (the option did not exist then, so each of its planning stages started an Improve child,
# which is what `stage` does). A row with no usable plugin_version, or with that release or a later one and no field, stands
# for nothing known ("not recorded") and is compared with no run: a mode is never inferred from anything else.
PLANNING_REVIEW_FIRST_RELEASE = "1.22.0"


def _release(text) -> tuple[int, int, int] | None:
    """A MAJOR.MINOR.PATCH version as numbers, or None for a missing version or any other shape (a development build)."""
    found = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", text) if isinstance(text, str) else None
    return tuple(int(part) for part in found.groups()) if found else None


def row_planning_review(row: dict) -> tuple[str, str]:
    """(the planning_review mode a baseline row stands for, why, when the row does not say: "" for a recorded mode)."""
    recorded = row.get("planning_review")
    if recorded is not None:
        return (recorded if isinstance(recorded, str) else json.dumps(recorded)), ""
    version = row.get("plugin_version")
    placed = _release(version)
    if placed is not None and placed < _release(PLANNING_REVIEW_FIRST_RELEASE):
        return "stage", f"records no mode, read as stage because plugin {version} predates the option"
    return (metrics.NOT_RECORDED, "records no mode and " + (
        f"plugin {version} does not predate the option" if placed is not None
        else "no plugin_version places it before the option"))


def planning_review_line(mode: str, last: dict) -> str:
    """The report line for a run that has no earlier row of its own mode to compare with. `last` is the last row of the
    same driver, which stands for another mode or for none (a run that records no mode matches no row)."""
    earlier, why = row_planning_review(last)
    reason = "this run records no mode" if mode == metrics.NOT_RECORDED else f"no earlier row of mode {mode}"
    return (f"  baseline  not compared across planning_review modes ({mode} vs {earlier}); {reason}; the last row for this "
            f"driver is {str(last.get('date'))[:10]}, ShipLoop {last.get('shiploop_version')}" + (f"; it {why}" if why else ""))


def scan_baseline(path: Path, case: str, source: str | None, host: str | None = None,
                  model: str | None = None, effort: str | None = None,
                  planning_review: str | None = None) -> tuple[dict | None, int]:
    """(the last comparable row, how many rows were recorded for this case and source).

    SPEC: a baseline compares only with rows from the same host, model and
    effort, so a row that does not name all three, or names different ones, is
    not a baseline for this run. Rows written before those fields existed are
    therefore skipped rather than compared against. The count lets a caller say
    "rows exist but none is comparable" instead of printing nothing. With
    ``planning_review`` (this run's mode) a row that stands for another mode
    (``row_planning_review``) is skipped too, so the last row of the run's own
    mode is found past any rows of the other; a run that records no mode matches no row.
    """
    if not path.is_file():
        return None, 0
    found, seen = None, 0
    for line in path.read_text().splitlines():
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if row.get("case") != case or row.get("source") != source:
            continue
        seen += 1
        if (row.get("host"), row.get("model"), row.get("effort")) != (host, model, effort):
            continue
        if planning_review is not None and (planning_review == metrics.NOT_RECORDED
                                            or row_planning_review(row)[0] != planning_review):
            continue
        found = row
    return found, seen


def previous_row(path: Path, case: str, source: str | None, host: str | None = None,
                 model: str | None = None, effort: str | None = None) -> dict | None:
    """The last recorded row for this case that is actually comparable with this run."""
    return scan_baseline(path, case, source, host, model, effort)[0]


NOT_OBSERVED = "not observed (regraded: no host ran)"


def regraded_process(observed: dict | None) -> dict:
    """The ``process`` block of a regrade: what the original run observed, or nothing.

    A regrade starts no host, so it claims no exit. The block the original run recorded is kept as it
    was, verdict included (marked ``regraded``), so a host that failed stays failed and the per-session
    list and elapsed time survive. With no record the harness never saw an exit: the block says so and
    its verdict is None, which no verdict list counts and no report calls a pass.
    """
    if isinstance(observed, dict) and observed.get("status"):
        kept = dict(observed, regraded=True)
        kept.setdefault("pass", kept["status"] == "exited")
        return kept
    return {"status": "not observed", "returncode": None, "elapsed_seconds": None, "sessions": [],
            "resumes": None, "pass": None, "regraded": True}


def termination_facts(process: dict, engine: dict, resume_stop: str | None, earlier: dict | None = None) -> dict:
    """Why this run is not still going, from the observer that owns the process.

    ShipLoop cannot answer this: it is not running when its host times out, runs
    out of credits, or is killed, so only the harness around the process can say
    what happened. Every field keeps ``unknown`` rather than a guess, and the
    last ShipLoop refusal is never reported as the cause -- a refusal is a
    rejected callback, not a terminated run.

    ``session_stops`` has one entry per session this invocation launched, in
    launch order, the same population ``sessions`` counts: the host's own reason,
    or ``unknown`` for a session that wrote no terminal event (killed, crashed).
    A resumed invocation describes its own sessions; the ones before it stay in the
    result's ``earlier_terminations``.

    A regrade (``process.regraded``) started no host, so nothing was observed: it
    keeps ``earlier`` (the termination the original run recorded) when there is one,
    and otherwise says no host ran. It never reports an exit that nobody saw.
    """
    pending = metrics.pending_stage(engine)
    reason = engine.get("status_reason")
    engine_facts = {
        "engine_status": engine.get("status") or "unknown",
        # Where the graph stopped: the stage it never accepted, when there is one, else the stage it is in.
        "engine_stage": metrics.current_stage(engine) or "unknown",
        "engine_unaccepted_stage": pending,
        # The engine's own recorded cause for a blocked, paused or halted run.
        "engine_status_reason": " ".join(reason.split())[:200] if isinstance(reason, str) and reason.strip() else None,
    }
    if process.get("regraded"):
        if isinstance(earlier, dict) and earlier.get("process_status"):
            return {**earlier, "regraded": True, "engine_status_at_regrade": engine_facts["engine_status"]}
        return {"process_status": NOT_OBSERVED, "returncode": None, "sessions": 0, "resumes": None,
                "session_stops": [], "resume_stop": "not evaluated (regraded)", **engine_facts, "regraded": True}
    sessions = process.get("sessions") or []
    return {
        "process_status": process.get("status") or "unknown",
        "returncode": process.get("returncode"),
        "sessions": len(sessions),
        "resumes": process.get("resumes"),
        "session_stops": [(s.get("stop") if isinstance(s, dict) else None) or "unknown" for s in sessions],
        "resume_stop": resume_stop or "unknown",
        **engine_facts,
    }


def stopped_line(t: dict) -> str:
    """The printed answer to why the run is not still going."""
    if t["process_status"] == NOT_OBSERVED:
        line = f"no host ran (regraded); engine {t['engine_status']}"
    else:
        line = (f"host {t['process_status']} rc={t['returncode']}; "
                f"session stops {', '.join(str(s) for s in t['session_stops']) or 'none'}; "
                f"no further resume: {t['resume_stop']}; engine {t['engine_status']}")
    if t["engine_unaccepted_stage"]:
        line += f" with {t['engine_unaccepted_stage']} never accepted"
    elif t["engine_status"] in ("blocked", "paused", "halted") and t["engine_stage"] != "unknown":
        line += f" at {t['engine_stage']}"  # the engine recorded that stage's own result: nothing was lost
    if t.get("engine_status_reason"):
        line += f" ({t['engine_status_reason'][:100]})"
    if t.get("regraded") and t["process_status"] != NOT_OBSERVED:
        line += f"; the original record, regraded with engine {t.get('engine_status_at_regrade')}"
    return line


def _minutes(seconds: float) -> str:
    return f"{seconds / 60:.0f}" if seconds >= 600 else f"{seconds / 60:.1f}"


def stage_diff_lines(before: list | None, now: list | None, top: int = 5) -> list[str]:
    """Where a whole-run difference actually landed, by stage.

    Compares whole, measured stage rows only. A row the run stopped in
    (``incomplete``) or that has no measured timing is never counted as a visit, so a
    stage with any such row on either side is not comparable: it is named and counted
    in the coverage line, which covers both runs. Stages are summed per name because
    a stage can be visited more than once (one `implement` action per planned step).
    Turns rank the differences where both runs report them; a host that reports no
    per-stage turns is compared by minutes, and the line says so. Stage turns are good
    to about one per boundary and minutes are wall clock, interruption gaps included
    (see metrics.per_stage). This prints; it gates nothing, because no threshold is
    calibrated yet.
    """
    def sides(rows: list | None) -> dict[str, dict]:
        out: dict[str, dict] = {}
        for row in rows or []:
            if not isinstance(row, dict):
                continue
            seen = out.setdefault(row.get("stage") or "?", {"turns": 0, "seconds": 0.0, "whole": True,
                                                              "has_turns": True})
            if row.get("incomplete") or row.get("seconds") is None:
                seen["whole"] = False
                continue
            seen["seconds"] += row["seconds"]
            if row.get("turns") is None:
                seen["has_turns"] = False
            else:
                seen["turns"] += row["turns"]
        return out

    was, became = sides(before), sides(now)
    if not any(s["whole"] for s in was.values()) or not any(s["whole"] for s in became.values()):
        return ["per-stage comparison unavailable (one run has no measured stage timing)"]
    names = set(was) | set(became)
    comparable = sorted(s for s in set(was) & set(became) if was[s]["whole"] and became[s]["whole"])
    not_comparable = sorted(s for s in names if not was.get(s, {"whole": True})["whole"]
                            or not became.get(s, {"whole": True})["whole"])
    only_now = sorted(s for s in set(became) - set(was) if became[s]["whole"])
    only_before = sorted(s for s in set(was) - set(became) if was[s]["whole"])
    lines = []
    if not_comparable or only_now or only_before:
        lines.append(f"per-stage comparison covers {len(comparable)} of {len(names)} stages"
                     + (f" ({len(not_comparable)} not comparable, incomplete or unmeasured on a side: "
                        f"{', '.join(not_comparable[:top])})" if not_comparable else ""))
    by_turns = [s for s in comparable if was[s]["has_turns"] and became[s]["has_turns"]]
    by_minutes = [s for s in comparable if s not in by_turns]
    turn_moves = sorted((s for s in by_turns if became[s]["turns"] != was[s]["turns"]),
                        key=lambda s: abs(became[s]["turns"] - was[s]["turns"]), reverse=True)
    minute_moves = sorted((s for s in by_minutes if became[s]["seconds"] != was[s]["seconds"]),
                          key=lambda s: abs(became[s]["seconds"] - was[s]["seconds"]), reverse=True)
    if turn_moves:
        lines.append("stage turns: " + ", ".join(
            f"{s} {was[s]['turns']}->{became[s]['turns']}"
            f" ({_minutes(was[s]['seconds'])}->{_minutes(became[s]['seconds'])}m)" for s in turn_moves[:top]))
    if minute_moves:
        lines.append("stage minutes (this host reports no per-stage turns): " + ", ".join(
            f"{s} {_minutes(was[s]['seconds'])}->{_minutes(became[s]['seconds'])}" for s in minute_moves[:top]))
    for label, listed in (("only now", only_now), ("only before", only_before)):
        if listed:
            lines.append(f"{label}: " + ", ".join(listed[:top]))
    if not turn_moves and not minute_moves:
        lines.append("no per-stage turn difference" if by_turns else
                     "no per-stage minute difference (turns not measured)" if by_minutes else
                     "no stage is comparable on both runs")
    return lines


def shared_tmp_writes(outputs: list[Path]) -> dict[str, list[str]]:
    """Each literal /tmp path that more than one of these runs wrote, with the runs that wrote it.

    Every host's tool calls are read (Claude's tool_use blocks too), so a run that wrote nothing is a measured none.
    """
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


def stale_listener_lines(own: Path | None) -> list[str]:
    """One line per listener an ended case left behind (see listeners.stale): the process, its port, its case and the command.

    Where the process table cannot be read the check is skipped with a printed note, never refused on a guess.
    """
    try:
        found = listeners.stale(own)
    except listeners.Unobserved as exc:
        print(f"stale-listener check skipped: {exc}", flush=True)
        return []
    return [f"pid {item['pid']} {item['command']} listens on port {','.join(map(str, item['ports']))} (working directory "
            f"{item['cwd']}), left by {item['case']}, whose harness is not running: stop it by pid with `kill {item['pid']}`"
            for item in found]


def refuse_stale_listeners(own: Path | None) -> None:
    """Start nothing while an ended case still has a server bound: a later run would meet it (SPEC: a run leaves nothing listening)."""
    lines = stale_listener_lines(own)
    if lines:
        raise SystemExit("a listener an ended case left is still bound, so no host is started (no override: stop it by pid):\n  "
                         + "\n  ".join(lines))


def run_suite(args, argv: list[str]) -> int:
    """Run a suite's cases in order; a follow-on starts from its predecessor and is skipped if it failed."""
    suites = json.loads(SUITES.read_text())
    if args.suite not in suites or args.suite.startswith("_"):
        raise SystemExit(f"unknown suite {args.suite!r}; known: {', '.join(k for k in suites if not k.startswith('_'))}")
    cases = json.loads(CASES.read_text())
    # Once, up front (like the version gate): a refusal raised inside a case's worker thread would reach the suite only after
    # the running chains finish, with no suite-result.json. Its cases skip their own check (--suite-name).
    refuse_stale_listeners(None)
    base = new_output_dir(args.output, "suite-" + args.suite)
    passthrough, skip = [], {"--suite", "--output", "--case", "--continue-from", "--max-parallel"}
    it = iter(argv)
    for token in it:
        name = token.split("=", 1)[0]
        if name in skip:
            if "=" not in token:
                next(it, None)
            continue
        passthrough.append(token)
    if args.source == "marketplace" and not args.plugin_dir:
        check = base / "preflight"
        check.mkdir()
        env = the_host(args).env(check / "home")
        _, _, versions = marketplace_preflight(args, check, env)
        (check / "preflight.json").write_text(json.dumps(versions, indent=2) + "\n")
        if versions["gate"]:
            raise SystemExit("suite not started, version gate: " + "; ".join(versions["gate"]))
    gate = suites[args.suite].get("gate") or []
    gate_rows = []
    for case in gate:
        # A batch suite's gate runs first and alone: a cheap case that fails stops the costly ones.
        if TERMINATION.is_set():
            gate_rows.append({"case": case, "pass": False, "skipped": stop_cause(base / "stop"), "gate": True})
            continue
        out = base / case
        code = main([*passthrough, "--case", case, "--output", str(out), "--suite-name", args.suite])
        gate_rows.append({"case": case, "pass": code == 0, "output": str(out), "gate": True})
    if not all(row["pass"] for row in gate_rows):
        summary = gate_rows + [{"case": case, "skipped": "the gate failed"} for case in suites[args.suite]["cases"]]
        (base / "suite-result.json").write_text(json.dumps({"suite": args.suite, "cases": summary}, indent=2) + "\n")
        print(f"suite {args.suite}: gate failed ({', '.join(r['case'] for r in gate_rows if not r['pass'])}); "
              "the other cases did not run")
        return 1
    order = suites[args.suite]["cases"]
    chains = suite_chains(order, cases)
    if len(chains) > 1 and not args.serial and "--quiet" not in passthrough:
        passthrough.append("--quiet")  # concurrent live views would interleave

    def run_chain(chain: list[str]) -> list[dict]:
        outputs: dict[str, Path] = {}
        rows = []
        for case in chain:
            if TERMINATION.is_set():
                # Not main's own early return: a case that wrote no result.json would break the readers of the rows below.
                rows.append({"case": case, "skipped": stop_cause(base / "stop")})
                continue
            follows = cases[case].get("follows")
            prior = outputs.get(follows) if follows else None
            if follows and prior is None:
                rows.append({"case": case, "skipped": f"its predecessor {follows!r} is not in this suite run"})
                continue
            if prior is not None and not json.loads((prior / "result.json").read_text()).get("pass"):
                rows.append({"case": case, "skipped": f"its predecessor {follows!r} failed; nothing to build on"})
                continue
            out = base / case
            case_argv = [*passthrough, "--case", case, "--output", str(out), "--suite-name", args.suite]
            if prior is not None:
                case_argv += ["--continue-from", str(prior)]
            code = main(case_argv)
            outputs[case] = out
            rows.append({"case": case, "pass": code == 0, "output": str(out)})
        return rows

    workers = 1 if args.serial else max(1, min(args.max_parallel, len(chains)))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        rows = [row for chain_rows in pool.map(run_chain, chains) for row in chain_rows]
    summary = gate_rows + sorted(rows, key=lambda row: order.index(row["case"]))
    shared = shared_tmp_writes([Path(row["output"]) for row in summary if row.get("output")])
    if shared:
        # Concurrent runs that wrote the same /tmp name may have read each other's files (plan P13).
        print("suite " + args.suite + ": /tmp names written by more than one case (their evidence is suspect): "
              + "; ".join(f"{name} ({', '.join(cases_)})" for name, cases_ in shared.items()), flush=True)
    (base / "suite-result.json").write_text(json.dumps({"suite": args.suite, "cases": summary,
                                                        "shared_tmp_writes": shared}, indent=2) + "\n")
    print(f"suite {args.suite}: " + ", ".join(
        f"{row['case']} {'SKIP' if 'skipped' in row else 'PASS' if row['pass'] else 'FAIL'}" for row in summary))
    return 0 if all(row.get("pass") for row in summary) else 1


def main(argv: list[str] | None = None) -> int:
    """Run one case (or a suite) and return the exit code; see _main."""
    held: list = []  # the case lock, taken inside once the output folder is known, and released here whatever happens
    try:
        return _main(argv, held)
    finally:
        for handle in held:
            handle.close()


def _main(argv: list[str] | None, held: list) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    args = parser().parse_args(argv)
    if args.preflight_only:
        # Before a rerun, every host must get the latest release (SPEC: publish, refresh, then run).
        out = new_output_dir(args.output, "preflight")
        problems = stale_listener_lines(None)
        for line in problems:
            print(f"refused: {line}", flush=True)
        refused = bool(problems)
        for name in (sorted(hosts.HOSTS) if args.host == "all" else [args.host]):
            args.host = name
            check = out / name
            check.mkdir()
            _, _, versions = marketplace_preflight(args, check, the_host(args).env(check / "home"))
            (check / "preflight.json").write_text(json.dumps(versions, indent=2) + "\n")
            refused = refused or bool(versions["gate"])
        return 1 if refused else 0
    if args.grade_only and not args.resume_run:
        raise SystemExit("--grade-only needs --resume-run <output directory>: it grades a run that already exists")
    if args.host == "all":
        raise SystemExit("--host all is only for --preflight-only; a run needs one host")
    if args.suite:
        return run_suite(args, argv)
    if args.plugin_dir:
        args.source = "checkout"
    if args.plugin_dir and not (args.plugin_dir / ".claude-plugin" / "plugin.json").is_file():
        raise SystemExit(f"--plugin-dir has no .claude-plugin/plugin.json: {args.plugin_dir}")

    resumed = None
    regrade = False
    earlier = {}
    earlier_result: dict = {}
    recorded: dict = {}  # a regrade restates this: the run's own last record
    if args.resume_run:
        # Continue a stopped run in place: same work directory, run state and event stream.
        out = args.resume_run.expanduser().resolve()
        (out / "stop").unlink(missing_ok=True)  # a request left by an earlier invocation must not stop this one
        earlier = json.loads((out / "invocation.json").read_text())
        name, checks, follow_on = earlier["case"], earlier["checks"], earlier.get("follow_on")
        prompt = (out / "prompt.txt").read_text().strip()
        work = out / "work"
        state = grade_shiploop(out)
        # A run that finished while no harness was watching (its parent was killed) is graded again, not resumed.
        # So is a blocked run: it waits for a person (SPEC S-14), so no host may continue it as if answered,
        # but its metrics and verdicts can be refreshed from what is on disk. --grade-only does the same for a run
        # in any status that has a ShipLoop state: the records a killed harness never wrote, with no host started.
        regrade = state.get("status") in ("done", "blocked") or (args.grade_only and state.get("status") is not None)
        if state.get("status") != "active" and not regrade:
            raise SystemExit(f"--resume-run needs an active, blocked or finished ShipLoop run; found "
                             f"{state.get('status')!r} in {out}")
        if not regrade and not args.suite_name:
            refuse_stale_listeners(out)  # the run's own leftovers are stopped below, not refused
        # The one CLI value every prompt of this invocation names (a record with no plugin_dir yields a path that is not a file).
        resumed_cli = run_cli(earlier["host"], out, Path(earlier.get("plugin_dir") or out / "missing-plugin"))
        if not regrade and not resumed_cli.is_file():
            raise SystemExit(f"--resume-run: the ShipLoop CLI this run started on is gone: {resumed_cli}. A resume "
                             "names that CLI in its prompt, so no host is started. Grade what is on disk with "
                             "--grade-only, or start the case again.")
        try:
            earlier_result = json.loads((out / "result.json").read_text())
        except (OSError, ValueError):
            earlier_result = {}
        if regrade:
            # Nothing is launched, so identity is not a choice: restate the run's own last record (its result.json,
            # which a resume on another host updates) or, when no result was written, its first launch
            # (invocation.json). --host, --model and --effort cannot relabel a finished run with a host that
            # did not run it.
            recorded = earlier_result if isinstance(earlier_result.get("host"), str) else earlier
            kept = {"host": recorded["host"], "model": recorded.get("model") or earlier.get("model"),
                    "effort": recorded.get("effort") or earlier.get("effort")}
            asked = {"host": args.host if host_given(argv) else None, "model": args.model, "effort": args.effort}
            ignored = [f"--{key} {value}" for key, value in asked.items() if value and value != kept[key]]
            if ignored and not args.quiet:
                print(f"regrade: no host starts, so the run's recorded host, model and effort stay ({kept['host']}, "
                      f"{kept['model']}, {kept['effort'] or 'no effort'}); ignoring {', '.join(ignored)}", flush=True)
            args.host, args.model, args.effort = kept["host"], kept["model"], kept["effort"]
        resumed = {"from_host": earlier["host"], "from_model": earlier.get("model"), "run_dir": state.get("run_dir"),
                   "revision": state.get("revision"), "stage": state.get("stage")}
    else:
        name, prompt, checks, follows = load_case(args)
        if follows and not args.continue_from:
            raise SystemExit(f"case {name!r} follows {follows!r}: pass --continue-from <that run's output directory>")
        if not args.suite_name:
            refuse_stale_listeners(None)  # before the folder exists, so a refusal leaves nothing behind
        out = new_output_dir(args.output, name)
        work = out / "work"
        work.mkdir()
        follow_on = continue_from(args.continue_from.expanduser().resolve(), work) if args.continue_from else None
    stop_file = out / "stop"  # a person (or a watcher) creates it to end the run; main consumes it
    # This harness is alive while main runs: a launch elsewhere reads the lock to tell a sibling's server from a leftover.
    # The kernel also drops it on any death, SIGKILL included, which is why a lock and not a pid file.
    lock = listeners.hold_case(out)
    if lock is not None:
        held.append(lock)
    left_behind: list = []  # what each reap pass of this invocation found (see listeners.py)

    def session(*launch_args, **launch_kw) -> dict:
        done = launch(*launch_args, **launch_kw)
        left_behind.append(done.pop("left_behind", None))  # a run's one record is built below, not repeated per session
        return done

    host = the_host(args)
    args.model = args.model or host.model
    args.effort = args.effort or host.effort
    args.skill = args.skill or host.skill
    env = host.env(out / "home")
    if regrade:
        # No host starts, so nothing is installed or gated: a regrade keeps the plugin identity and the plugin
        # verdict the run recorded (see the invocation record below). Claude's init event shows the plugin on
        # any launch, so Claude is graded from its events again.
        plugin_dir = Path(earlier.get("plugin_dir") or out / "missing-plugin")
        plugin = None if args.host == "claude" else recorded.get("plugin")
        versions = {"source": None, "plugin_version": None, "shiploop_version": None,
                    **(recorded.get("versions") or earlier.get("versions") or {}), "regraded": True}
    elif resumed and earlier.get("host") == args.host and Path(earlier.get("plugin_dir") or "").is_dir():
        # A resumed run keeps the plugin it started on: reinstalling would replace that version's files, and a
        # bound Improve child records paths inside them. Only the CI and checkout checks still apply. It also
        # keeps that launch's plugin verdict, since a Grok or Codex stream cannot show which plugin loaded.
        plugin_dir, plugin = Path(earlier["plugin_dir"]), earlier.get("plugin")
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
            if resumed:
                # The run already has a result.json worth more than a refusal stub; leave it as it was.
                raise SystemExit("version gate: " + "; ".join(versions["gate"]))
            (out / "result.json").write_text(json.dumps({"case": name, "pass": False, "versions": versions,
                                                         "output": str(out)}, indent=2) + "\n")
            raise SystemExit("version gate: " + "; ".join(versions["gate"]) + f" (see {out / 'result.json'})")
    else:
        plugin = None
        plugin_dir = args.plugin_dir or build_candidate(out)
        plugin = host.install_plugin(env, plugin_dir)
        versions = {"source": "checkout", **installed_versions(plugin_dir), "local_head": git("rev-parse", "HEAD").strip()}
    keepalive = hosts.grok_keepalive(env, plugin_dir) if host.keepalive else None
    seeded = earlier.get("seeded") if resumed else None
    interrupt_at = earlier.get("interrupt_at") if resumed else args.interrupt_at
    # The CLI of the host and plugin the run started on (a resume on another host keeps it): every prompt below names it.
    the_cli = resumed_cli if resumed else run_cli(host.name, out, plugin_dir)
    if args.seed_at and not resumed:
        seeded = seed_run(the_cli, work, out, prompt, args.seed_at)
        if not args.quiet:
            print(f"seeded: {', '.join(seeded['skipped'])} recorded without doing them; host starts at "
                  f"{seeded['stage']} in {seeded['run_dir']}", flush=True)
    # A resumed run keeps the ShipLoop CLI of the host that started it, so its version does not change.
    opening = (resume_prompt(resumed["run_dir"], the_cli) if resumed
               else host.invoke(args.skill, seed_prompt(the_cli, seeded["run_dir"], prompt)) if seeded
               else host.invoke(args.skill, prompt))
    cli = host.argv(prompt=opening, prompt_file=out / ("host-prompt.txt" if not resumed else
                                                       f"resume-{host.name}-{int(time.time())}.txt"),
                    cwd=work, model=args.model, effort=args.effort,
                    permission_mode=args.permission_mode, max_turns=args.max_turns,
                    max_budget_usd=args.max_budget_usd,
                    plugin_dir=None if host.marketplace else plugin_dir)
    # `plugin` is the install check made before the host started (Grok, Codex), kept so a resume or a regrade
    # grades the run on its first launch's evidence; None for Claude, whose init event shows it on every launch.
    invocation = {"case": name, "host": args.host, "model": args.model, "effort": args.effort, "argv": cli,
                  "cwd": str(work), "plugin_dir": str(plugin_dir), "plugin": plugin, "versions": versions,
                  "checks": checks,
                  "follow_on": follow_on, "resumed_run": resumed, "seeded": seeded,
                  "interrupt_at": interrupt_at}
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
        if not regrade:
            # Before any host spend: a later session that finds only this log, even after the harness was
            # killed, holds the output directory and the command that continues the run.
            print(f"resume: {resume_command(out, args)}", flush=True)

    deadline = time.time() + args.timeout
    if resumed and not regrade:
        # A server an earlier invocation's model left (its harness may have been killed before it could stop it) must
        # not answer the new session's probes: that is how two runs met the same port in round 2.
        left_behind.append(listeners.reap(out))
    if regrade:
        # ShipLoop is done or blocked: no host is started, and the verdicts are computed from what is on disk.
        process = regraded_process(earlier_result.get("process"))
    else:
        interrupt_file = out / "interrupt.json"
        stop_when = ((lambda: chain_in_flight(out)) if interrupt_at and not interrupt_file.exists() else None)
        process = session(cli, work, out, env, args.timeout, watch=not args.quiet,
                         fresh=follow_on is None and seeded is None,
                         first=resumed is None, translate=host.translator(), stop_when=stop_when,
                         stop_file=stop_file)
    sessions = [] if regrade else [dict(process, resumed=None, host=host.name)]  # a regrade launched no session
    if process["status"] == "interrupted":
        state = grade_shiploop(out)
        interrupt_file.write_text(json.dumps({
            "at": interrupt_at, "elapsed_seconds": process["elapsed_seconds"], "stage": state.get("stage"),
            "revision": state.get("revision"), "chain": chain_facts(out)["bindings"]}, indent=2) + "\n")
        if not args.quiet:
            print(f"interrupted: killed the host at {process['elapsed_seconds']}s with a chain worker in flight; "
                  "resuming with a fresh session", flush=True)
        argv = host.argv(prompt=resume_prompt(state.get("run_dir"), the_cli),
                         prompt_file=out / "resume-after-interrupt.txt", cwd=work, model=args.model,
                         effort=args.effort, permission_mode=args.permission_mode, max_turns=args.max_turns,
                         max_budget_usd=args.max_budget_usd, plugin_dir=None if host.marketplace else plugin_dir)
        process = session(argv, work, out, env, max(60, int(deadline - time.time())), watch=not args.quiet,
                         first=False, translate=host.translator(), stop_file=stop_file)
        sessions.append(dict(process, resumed="after-interrupt", host=host.name))
    # A headless Grok session ends whenever the model ends its turn. While ShipLoop's
    # run is still active, resume that same session (bounded) instead of losing the run.
    resume_stop = ("not evaluated (regraded)" if regrade
                   else None if host.resumable else "host is not resumable")
    stop_seen = not regrade and process["status"] == "stopped"  # a requested stop ended the host
    while host.resumable and not regrade and len(sessions) <= args.max_resumes:
        state = grade_shiploop(out)
        session_id = last_session_id(out / "events.jsonl")
        remaining = int(deadline - time.time())
        # No run yet means the session ended before ShipLoop wrote its state; a
        # run that is paused, blocked, halted or done is not resumed. (A question
        # waiting for a person is a view of blocked, not a status of its own.)
        # Each reason is recorded, because "why did this run stop?" is answerable
        # only here: the engine is not running when its host goes away.
        if state.get("status") not in ("active", None):
            resume_stop = f"ShipLoop run is {state.get('status')}"
            break
        if stop_seen or stop_file.exists() or TERMINATION.is_set():
            stop_seen = True  # asked for between two sessions, or the host was stopped: never relaunched
            break
        if not session_id:
            resume_stop = "no host session id to resume"
            break
        if remaining <= 60:
            resume_stop = "run deadline spent"
            break
        if not args.quiet:
            print(f"resume {len(sessions)}/{args.max_resumes}: session {session_id} ended with ShipLoop "
                  f"{'not yet started' if state.get('status') is None else 'active at revision ' + str(state.get('revision')) + ', stage ' + str(state.get('stage'))}", flush=True)
        argv = host.argv(prompt=resume_prompt(state.get("run_dir"), the_cli),
                         prompt_file=out / f"resume-{len(sessions)}.txt", cwd=work, model=args.model,
                         effort=args.effort, permission_mode=args.permission_mode,
                         max_turns=args.max_turns, resume=session_id)
        process = session(argv, work, out, env, remaining, watch=not args.quiet, first=False,
                         translate=host.translator(), stop_file=stop_file)
        sessions.append(dict(process, resumed=session_id, host=host.name))
        stop_seen = process["status"] == "stopped"
    if resume_stop is None and host.resumable:
        # The loop also ends on its budget without grading the run again, and the last session it
        # was allowed may have finished it: say what the run is, not that the budget was spent.
        status = grade_shiploop(out).get("status")
        resume_stop = (f"ShipLoop run is {status}" if status not in ("active", None)
                       else stop_cause(stop_file) if stop_seen
                       else f"resume budget spent ({args.max_resumes})")
    if not regrade:
        if stop_seen:
            stop_file.unlink(missing_ok=True)  # consumed: the request is answered, a later resume starts clean
            if resume_stop == "host is not resumable":
                resume_stop = stop_cause(stop_file)  # the stop, not the host kind, is why this one is over
            # However the request arrived (it killed the host, or it was found as a session ended on its own), the run
            # ends stopped; the last session keeps its own status in `sessions`.
            process = dict(process, status="stopped")
        process = dict(process, sessions=sessions, resumes=len(sessions) - 1 if sessions else None)
        # A requested stop is not a host failure: no process verdict (None, which no verdict list counts).
        process["pass"] = None if process["status"] == "stopped" else process["status"] == "exited"
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
    shiploop["knowledge"] = knowledge_facts(work)
    start_head = (follow_on or {}).get("start_head") or (seeded or {}).get("start_head")
    knowledge = shiploop["knowledge"]
    committed = committed_facts(knowledge, start_head)
    run_metrics = metrics.collect(out, Path(shiploop["run_dir"]) if shiploop.get("run_dir") else None)
    if "truncated_outputs" in (run_metrics.get("unmeasured") or {}):
        cli_seen["truncated_outputs"] = None  # [] would read as a measured none
    (out / "metrics.json").write_text(json.dumps(run_metrics, indent=2) + "\n")
    check_env = {"PRIOR_WORK": str(Path(follow_on["prior"]) / "work")} if follow_on else {}
    check_results = run_checks(work, checks, env=check_env)
    if not shiploop["pass"] and shiploop.get("worktree"):
        # Informational only: does the unreturned candidate already pass?
        shiploop["worktree_checks"] = [{k: c[k] for k in ("command", "pass")}
                                       for c in run_checks(Path(shiploop["worktree"]), checks, env=check_env)]
    if not regrade:
        # A check may leave a server too (a timed-out check leaves its `node server.js &`). A regrade reaps nothing: it
        # starts no host, and the run it grades may have a live one.
        left_behind.append(listeners.reap(out))
    left = (earlier_result.get("left_behind") if regrade
            else listeners.merge_left_behind([earlier_result.get("left_behind") if resumed else None, *left_behind]))
    case = json.loads(CASES.read_text()).get(name, {}) if name != "custom" else {}
    expect = case.get("chain")
    chain = chain_facts(out, expect) if (seeded or interrupt_at or expect) else None
    if chain is not None:
        chain["source"] = (expect or {}).get("source") or "the harness default: a fanned-out chain (seeded or interrupted run)"
    recovery = None
    if interrupt_at:
        interrupt_file = out / "interrupt.json"
        interrupted = json.loads(interrupt_file.read_text()) if interrupt_file.is_file() else None
        recovery = {"pass": bool(interrupted) and chain["pass"], "interrupt": interrupted, "source": RECOVERY_SOURCE}
    budget = budget_facts(case.get("budget"), bool(seeded), shiploop.get("run_dir"), interrupted=bool(interrupt_at))
    expectations = {
        "checks": case.get("checks_source") or "the --check arguments given with --prompt",
        **({"retention": case["retention_source"]} if case.get("retention_source") else {}),
        **({"chain": {k: v for k, v in chain["expect"].items()} | {"source": chain["source"]}} if chain else {}),
        **({"recovery": RECOVERY_SOURCE} if recovery else {}),
        **({"budget": {"seeded_minutes": budget["expected_minutes"], "level": "should",
                       "source": budget["source"]}} if budget else {}),
    }
    verdicts = [invoked["pass"], plugin["pass"], *([] if process["pass"] is None else [process["pass"]]),
                shiploop["pass"], committed["pass"],
                *([chain["pass"]] if chain else []), *([recovery["pass"]] if recovery else []),
                *(c["pass"] for c in check_results)]
    if keepalive is not None:
        keepalive["decisions"] = hosts.keepalive_decisions(out / "home")
    engine = metrics.engine_state(Path(shiploop["run_dir"]) if shiploop.get("run_dir") else None)
    termination = termination_facts(process, engine, resume_stop,
                                    earlier_result.get("termination") if regrade else None)
    # A resumed run overwrites result.json: keep the termination each earlier invocation recorded.
    earlier_terminations = list(earlier_result.get("earlier_terminations") or []) if resumed else []
    if resumed and not regrade and isinstance(earlier_result.get("termination"), dict):
        earlier_terminations.append(earlier_result["termination"])
    result = {"case": name, "host": args.host, "model": args.model, "effort": args.effort,
              "pass": all(verdicts), "invoked": invoked, "plugin": plugin, "versions": versions,
              "process": process, "termination": termination,
              **({"earlier_terminations": earlier_terminations} if earlier_terminations else {}),
              **({"left_behind": left} if left is not None else {}),
              "keepalive": keepalive,
              "shiploop": shiploop, "committed": committed, "checks": check_results, "cli": cli_seen, "follow_on": follow_on,
              "resumed_run": resumed, "seeded": seeded, "chain": chain, "recovery": recovery, "budget": budget,
              "expectations": expectations,
              "metrics": {k: run_metrics[k] for k in ("claude_code_version", "turns", "model_calls", "window_tokens",
                                                      "cost_usd", "unreported_sessions", "compactions",
                                                      "truncated_outputs", "improve_children", "stages", "unmeasured")}
              # None, not 0, where the host's events cannot show the thing counted.
              | {"script_verifications": run_metrics["script_verifications"],
                 "model_glue": metrics.count(run_metrics, "model_glue"),
                 "tmp_writes": metrics.count(run_metrics, "tmp_writes"),
                 "asked_user": len(run_metrics["asked_user"]),
                 "narrative": {k: v for k, v in run_metrics["narrative"].items() if k != "skipped"},
                 "shiploop_failures": metrics.count(run_metrics, "shiploop_failures"),
                 "cancelled_tool_calls": metrics.count(run_metrics, "cancelled_tool_calls")},
              "output": str(out)}
    (out / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    exported = review_export(out)
    style = json.loads(CASES.read_text()).get(name, {}).get("style") if name != "custom" else None
    row = baseline_row(result, style, args.suite_name, metrics.planning_review(engine))
    # A baseline measures one host running a case from the start to its end; a resumed run is not one, and neither is
    # a run the harness ended: its engine still active (a deadline, a requested stop, a spent resume budget) or its host
    # killed by the deadline or a stop before ShipLoop wrote any state (engine unknown). The turns, cost and stages are a
    # fragment, and the next run would be compared with it (SPEC). A host that ends by itself is a finished run's row.
    engine_active = engine.get("status") == "active"
    unfinished = engine_active or process["status"] in ("timeout", "stopped")
    baseline_file = args.baseline if not (resumed or seeded or unfinished) else None
    before, rows_for_case = (scan_baseline(baseline_file, name, versions["source"], args.host, args.model,
                                           args.effort, row["planning_review"]) if baseline_file else (None, 0))
    last = (previous_row(baseline_file, name, versions["source"], args.host, args.model, args.effort)
            if baseline_file and before is None else None)  # the driver's last row, of another mode: what the report names
    if baseline_file:
        with baseline_file.open("a") as handle:
            handle.write(json.dumps(row) + "\n")

    mark = lambda ok: "PASS" if ok else "FAIL"  # noqa: E731
    print(f"{'STOPPED' if stop_seen and not result['pass'] else mark(result['pass'])}  "
          f"shiploop e2e case={name} host={args.host}  output={out}")
    print(f"  versions  {versions['source']}: skill-craft {versions['plugin_version']}, "
          f"ShipLoop {versions['shiploop_version']}")
    print(f"  invoked   {mark(invoked['pass'])}  /{args.skill}")
    print(f"  plugin    {mark(plugin['pass'])}  {', '.join(map(str, plugin['loaded'])) or 'none loaded'}")
    print(f"  process   {'n/a ' if process['pass'] is None else mark(process['pass'])}  " + (
        "no host ran: regraded from what is on disk" if process.get("regraded") and process["pass"] is None else
        f"no host ran: regraded, the original run's {process['status']} rc={process['returncode']} is kept"
        if process.get("regraded") else
        f"{process['status']} rc={process['returncode']} {sum(s['elapsed_seconds'] for s in sessions):.1f}s "
        f"cost={metrics.cost_text(run_metrics)} sessions={len(sessions)}"))
    if keepalive is not None:
        print(f"  keepalive {'installed' if keepalive['installed'] else 'NOT installed'}; "
              f"decisions {keepalive['decisions'] or 'none (hooks never ran)'}")
    print(f"  shiploop  {mark(shiploop['pass'])}  {shiploop.get('status') or shiploop.get('reason')}")
    print(f"  stopped   {stopped_line(termination)}")
    if line := listeners.left_behind_line(left):
        print(line)
    if shiploop.get("worktree_checks") is not None:
        passed = sum(c["pass"] for c in shiploop["worktree_checks"])
        print(f"            unreturned product in {shiploop['worktree']}: "
              f"{passed}/{len(shiploop['worktree_checks'])} checks pass there")
    print(f"  committed {mark(committed['pass'])}  HEAD {str(committed['head'])[:8]} (started at "
          f"{str(committed['start_head'])[:8] if committed['start_head'] else 'no commit'}); "
          f"{committed['head_files']} files in HEAD, {len(knowledge['uncommitted'])} uncommitted product paths")
    print(f"  knowledge docs/shiploop/spec.md {'present' if knowledge['spec'] else 'missing'}"
          f"{', tracked' if knowledge['spec_tracked'] else ', not committed'}; {len(knowledge['requirement_ids'])} "
          f"requirement ids; HEAD has {knowledge['head_commits']} commits, {knowledge['untracked_files']} untracked files")
    if chain is not None:
        want = chain["expect"]
        print(f"            expected  >= {want['min_steps']} steps all accepted, >= {want['min_in_flight']} in flight, "
              f"depth >= {want['min_depth']}, dependency order, each merged once ({chain['source']})")
        for binding in chain["bindings"] or [{}]:
            print(f"  chain     {mark(chain['pass'])}  " + (
                f"{binding.get('mode')} {binding.get('accepted')}/{binding.get('steps')} steps accepted, depth "
                f"{binding.get('depth')}, native {binding.get('native_attempts')}, main-context "
                f"{binding.get('main_context_attempts')}, most in flight {binding.get('max_in_flight')}"
                + "".join(f", {key} {binding[key]}" for key in ("out_of_order", "integrated_twice", "not_integrated")
                          if binding.get(key))
                if binding.get("steps") is not None else binding.get("error") or "no chain bound"))
    if recovery is not None:
        stop = recovery["interrupt"]
        print(f"  recovery  {mark(recovery['pass'])}  " + (
            f"killed at {stop['elapsed_seconds']}s in {stop['stage']}; a fresh session resumed the chain"
            if stop else "the host was never interrupted (no chain worker was ever in flight)"))
        print(f"            expected  {recovery['source']}")
    if budget is not None and not budget["applies"]:
        print(f"  budget    n/a   took {budget['observed_minutes']} min; {budget['reason']}")
    elif budget is not None:
        print(f"  budget    {'met ' if budget['pass'] else 'over'}  should finish within {budget['expected_minutes']} min; "
              f"took {budget['observed_minutes']} min ({budget['source']})")
    for line in metrics.summary_lines(run_metrics):
        print(f"  metrics   {line}")
    for failure in run_metrics["shiploop_failures"][:5]:
        print(f"  failed    shiploop {failure['verb']} {metrics.failure_text(failure)}: {failure['line']}")
    if follow_on:
        print(f"  follow-on of {follow_on['prior_case']} ({follow_on['prior']}): turns {metrics.turns_text(run_metrics)} vs "
              f"{'not reported' if follow_on['prior_turns'] is None else follow_on['prior_turns']}, cost {metrics.money(run_metrics['cost_usd'])} vs "
              f"{metrics.money(follow_on['prior_cost_usd'])}")
    print(f"  checks    expected from {expectations['checks']}")
    for check in check_results:
        print(f"  check     {mark(check['pass'])}  {check['command']}")
    print(f"  {exported}")
    if before:
        unknown = lambda value: "not measured" if value is None else value  # noqa: E731
        print(f"  baseline  vs {before['date'][:10]} (ShipLoop {before['shiploop_version']}, same "
              f"{args.host}/{args.model}/{args.effort}, planning_review {row['planning_review']}): "
              f"turns {unknown(before['turns'])} -> {unknown(row['turns'])}, cost {metrics.money(before['cost_usd'])} -> "
              f"{metrics.money(row['cost_usd'])}, "
              f"sessions {before['sessions']} -> {row['sessions']}, "
              f"glue {unknown(before['model_glue'])} -> {unknown(row['model_glue'])}"
              + (f", narrative shown {before['narrative']['shown']}/{before['narrative']['emitted']} -> "
                 f"{row['narrative']['shown']}/{row['narrative']['emitted']}"
                 if before.get("narrative") and row.get("narrative") else ""))
        if why := row_planning_review(before)[1]:  # a row with no mode compared as stage by the plugin version rule
            print(f"            the earlier row {why}")
        for line in stage_diff_lines(before.get("stages"), row.get("stages")):
            print(f"            {line}")
    elif last:
        print(planning_review_line(row["planning_review"], last))  # turns, cost and stages mean something else in the other mode
    elif baseline_file:
        print("  baseline  nothing compared: " + (
            f"{rows_for_case} earlier row(s) for {name}, none recorded with {args.host}/{args.model}/"
            f"{args.effort}, so there is no baseline" if rows_for_case
            else f"no earlier row for {name} from this source"))
    elif resumed or seeded:
        print("  baseline  nothing compared: a resumed or seeded run is not a baseline")
    else:
        why = ("its engine is still active" if engine_active else
               f"the harness ended the host: {process['status']}; engine {engine.get('status') or 'unknown'}")
        print(f"  baseline  nothing compared: the run is not finished ({why}), so it is not a baseline")
    if engine_active and not regrade:
        # The exact command, flags included, for whoever finds only this log (SPEC: a resume names what the run uses).
        # Only an active engine can be resumed: --resume-run refuses a run that never wrote ShipLoop state.
        print(f"  resume    {resume_command(out, args)}")
    elif engine_active:
        # A regrade's flags are the grading invocation's (the default --timeout is above any task limit), not the run's.
        print("  resume    use the command printed when the run started, with --timeout below the launcher's limit "
              "(this regrade's own flags are not the run's)")
    if not result["pass"] and not stop_seen:
        failed = [(verdict, want, got) for ok, verdict, want, got in (
            (invoked["pass"], "invoked", "the host registers the invoked ShipLoop skill", "not registered"),
            (plugin["pass"], "plugin", "exactly the skill-craft build under test loads", str(plugin.get("loaded"))),
            (process["pass"], "process", "the host exits 0 within the timeout",
             f"{process['status']} rc={process['returncode']}"),
            (shiploop["pass"], "shiploop", "ShipLoop reaches done and writes its report",
             str(shiploop.get("status") or shiploop.get("reason"))),
            (committed["pass"], "committed", "HEAD moves past the start, has files in HEAD and no product path is "
             "uncommitted", f"HEAD {str(committed['head'])[:8]}, {committed['head_files']} files in HEAD, "
             f"{len(committed['uncommitted'])} uncommitted"),
        ) if ok is not None and not ok]
        if chain is not None and not chain["pass"]:
            want = chain["expect"]
            got = "; ".join(f"{b.get('accepted')}/{b.get('steps')} accepted, depth {b.get('depth')}, "
                            f"most in flight {b.get('max_in_flight')}, out of order {b.get('out_of_order')}, "
                            f"merged twice {b.get('integrated_twice')}, not merged {b.get('not_integrated')}"
                            if b.get("steps") is not None else b.get("error", "no chain")
                            for b in chain["bindings"]) or "no chain bound"
            failed.append(("chain", f">= {want['min_steps']} steps all accepted, >= {want['min_in_flight']} in "
                           f"flight, depth >= {want['min_depth']}, in dependency order, each merged once "
                           f"(source: {chain['source']})", got))
        if recovery is not None and not recovery["pass"]:
            failed.append(("recovery", f"a fresh session finishes the chain after the kill (source: {RECOVERY_SOURCE})",
                           "never interrupted" if not recovery["interrupt"] else "the chain did not finish"))
        def check_observed(check: dict) -> str:
            lines = [line for line in str(check.get("output") or "").splitlines() if line.strip()]
            last = f": {lines[-1].strip()[:300]}" if lines else ""
            return ("timed out" if check.get("returncode") is None else f"exit {check['returncode']}") + last

        failed.extend(("check", f"`{c['command']}` exits 0 (source: {expectations['checks']})", check_observed(c))
                      for c in check_results if not c["pass"])
        print(f"  mismatch  {write_mismatch(out, name, args.host, failed)}")
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    install_termination_handlers()  # a program only: signal.signal is main-thread-only, and tests call main() from workers
    raise SystemExit(main())
