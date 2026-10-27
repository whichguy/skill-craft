"""Headless Grok, Claude and Codex launches shared by the E2E runner, reviewer and improver.

Each host is one ``Host`` in ``HOSTS``; callers never branch on the host name.
A host builds its launch argv, its isolated environment, its plugin install,
the prompt that invokes a skill, and a translator that turns its event stream
into the one shape the parsers read (Grok's streaming JSON; Claude's stream is
already understood as is).

Grok and Codex always run in a throwaway HOME: their profile holds only a
symlink to the user's auth.json (plus the plugin installed for the run), so the
user's plugins and settings stay out and nothing is installed into the real
profile. Claude runs with only project/local settings, so the user's plugins and
hooks stay out. With ``backend="ollama"`` the Claude host runs Claude Code on a model the local Ollama server serves,
with the user's Anthropic credentials scrubbed from its environment (SPEC "The Claude host can run on Ollama").
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parent))
import listeners  # noqa: E402  (the one group kill)
import runrecord  # noqa: E402  (the one set of host-build reasons)

# The user's Grok sign-in; the only file an isolated Grok HOME links to.
GROK_AUTH = Path.home() / ".grok" / "auth.json"

MARKETPLACE_SOURCE = "whichguy/skill-craft"

# The Claude host on Ollama: the route the ask-ollama skill verified (claude_harness_once.py, 2026-10-24). The local server
# runs a :cloud tag on ollama.com under the owner's Ollama plan.
OLLAMA_URL = "http://127.0.0.1:11434"
OLLAMA_MODEL = "deepseek-v4.1-flash:1017-cloud"
# Dropped from the child's environment before the route is set: a `claude` started inside a Claude session otherwise sends
# the user's OAuth bearer to the replacement endpoint (verified by ask-ollama with Claude Code 2.1.310, whose scrub is
# ANTHROPIC_*, CLAUDE_CODE_*, CLAUDECODE and CLAUDE_PROXY_BYPASS). Every CLAUDE* name goes, as for the Codex host: the
# launching session's own settings (CLAUDE_EFFORT, CLAUDE_PID, CLAUDE_PLUGIN_DATA, ...) are not this driver's either.
OLLAMA_SCRUB_PREFIXES = ("ANTHROPIC_", "CLAUDE")
# Every model class Claude Code can pick (main thread, the default classes, subagents) goes to the one Ollama model.
OLLAMA_MODEL_VARS = ("ANTHROPIC_MODEL", "ANTHROPIC_DEFAULT_OPUS_MODEL", "ANTHROPIC_DEFAULT_SONNET_MODEL",
                     "ANTHROPIC_DEFAULT_HAIKU_MODEL", "CLAUDE_CODE_SUBAGENT_MODEL")
# An explicit allowlist: without one the child also gets this installation's orchestration tools (SendMessage, CronCreate,
# Monitor, Workflow, ...), which no outside model may have (ask-ollama). Skill and Agent are ShipLoop's Improve route.
OLLAMA_TOOLS = ("Bash", "Read", "Edit", "Write", "Glob", "Grep", "NotebookEdit", "WebFetch", "WebSearch", "TodoWrite",
                "Skill", "Agent")
# The backend an E2E run (run.py) uses when none is named: the Claude host runs on Ollama's DeepSeek flash, and
# `--backend anthropic` names Claude's own models (owner, 2026-10-26: "switch the default e2e ... to use ollama and
# deepseek-flash as the models for testing"). The host factory's own default stays anthropic, so the session reviewer and
# the slice and fan-out drivers keep Claude's models.
RUN_DEFAULT_BACKEND = {"claude": "ollama"}


def run_default_model(name: str) -> str:
    """The model an E2E run of host ``name`` uses when no --model and no --backend are given."""
    return OLLAMA_MODEL if RUN_DEFAULT_BACKEND.get(name) == "ollama" else HOSTS[name].model


def ollama_ready(model: str, url: str = OLLAMA_URL, timeout: float = 5.0) -> str | None:
    """None when the Ollama server at ``url`` answers and lists ``model``, else why not: a `claude -p` against an
    endpoint that does not answer hangs instead of failing (ask-ollama), so the run is refused before it starts."""
    try:
        with urllib.request.urlopen(url.rstrip("/") + "/api/tags", timeout=timeout) as reply:
            listed = [m.get("name") for m in json.loads(reply.read()).get("models", []) if isinstance(m, dict)]
    except (OSError, ValueError, urllib.error.URLError) as exc:
        return f"the Ollama server at {url} does not answer ({exc})"
    return None if model in listed else f"the Ollama server at {url} does not list {model} (it lists {len(listed)} models)"

# The one ceiling of a `<binary> --version` read, not a tuning value: the CLIs, tools and browsers answer in 0.01 to 0.05 s,
# so a read still running after this long is stuck, and its value is recorded as unknown.
VERSION_TIMEOUT_SECONDS = 20


def probe_version(binary: str, env: dict | None = None) -> tuple[str | None, str | None]:
    """(the first line of ``<binary> --version`` on stdout, None) or (None, why it could not be read). The one ``--version``
    reader of the harness: a host CLI's build at launch (``Host.cli_version``), the node, python3 and git versions on the
    harness's PATH (environment.read_tools) and the browser's (environment.browser_record).

    The reasons: ``probe failed: not found``, ``non-zero exit N``, ``silent`` (no stdout) and ``hung`` (still running after
    VERSION_TIMEOUT_SECONDS). stdin is closed and stderr is dropped: Codex prints a WARNING there when its CODEX_HOME does
    not exist yet. ``env``: a host CLI is read in the launch's own isolated environment (``grok --version`` creates
    ``~/.grok`` in whatever HOME it runs under); None (or empty) is the harness's own environment, for the tools and the
    browser. A host build is a record of the build a run was launched on, taken once at launch (run.py) and never at report
    time, because today's answer stamped on a past run would be a made-up fact.
    """
    try:
        done = subprocess.run([binary, "--version"], env=env or None, stdin=subprocess.DEVNULL, capture_output=True,
                              text=True, timeout=VERSION_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        return None, f"probe failed: hung (still running after {VERSION_TIMEOUT_SECONDS} s)"
    except FileNotFoundError:
        return None, "probe failed: not found"
    except (OSError, subprocess.SubprocessError) as error:
        return None, f"probe failed: {type(error).__name__}"
    if done.returncode != 0:
        return None, f"probe failed: non-zero exit {done.returncode}"
    lines = done.stdout.strip().splitlines()
    first = lines[0].strip() if lines else ""
    return (first, None) if first else (None, "probe failed: silent")


def grok_keepalive(env: dict, plugin_dir: Path) -> dict:
    """Install ShipLoop's global Grok keepalive hooks before the session starts.

    Headless Grok never runs plugin hooks and loads ~/.grok/hooks only at session
    start, so the hooks ShipLoop self-installs mid-run would protect no session of
    this run. Installing them first is what a user's second session gets.
    """
    installer = plugin_dir / "skills" / "shiploop" / "scripts" / "shiploop-hook"
    done = subprocess.run([sys.executable, str(installer), "install", "--host", "grok"], env=env,
                          capture_output=True, text=True)
    return {"installed": done.returncode == 0, "output": (done.stdout + done.stderr).strip()[-400:]}


def keepalive_decisions(home: Path) -> dict:
    """What the keepalive decided in an isolated profile: proof its hooks ran."""
    log = home / ".local" / "state" / "shiploop" / "keepalive" / "decisions.log"
    counts: dict = {}
    if log.is_file():
        for line in log.read_text(errors="replace").splitlines():
            try:
                decision = json.loads(line).get("decision", "?")
            except ValueError:
                continue
            counts[decision] = counts.get(decision, 0) + 1
    return counts


def final_text(events_path: Path) -> str:
    """The assistant's closing text: Claude's result, or Grok's text deltas after its last tool call."""
    grok_text, result = "", None
    for line in events_path.read_text(errors="replace").splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if not isinstance(event, dict):
            continue
        if event.get("type") == "result" and isinstance(event.get("result"), str):
            result = event["result"]
        elif event.get("type") == "text" and isinstance(event.get("data"), str):
            grok_text += event["data"]
        elif event.get("type") in ("tool_call", "tool_call_update"):
            grok_text = ""
    return result if result is not None else grok_text


def last_json_object(text: str) -> dict | None:
    """The last ```json fenced object in `text`, or the last top-level {...} that parses."""
    fenced = re.findall(r"```json\s*(\{.*?\})\s*```", text, re.S)
    candidates = fenced[::-1] or [text[i:] for i in range(len(text)) if text[i] == "{"]
    for candidate in candidates:
        try:
            value, _ = json.JSONDecoder().raw_decode(candidate)
        except ValueError:
            continue
        if isinstance(value, dict):
            return value
    return None


def run_agent(argv: list[str], cwd: Path, env: dict, events_path: Path, stderr_path: Path,
              timeout: int, translate=None) -> dict:
    """Run one headless host process to completion (or kill it at `timeout`).

    ``translate`` (a host's ``translator()``) rewrites each stdout line into the
    shared event shape as it is written.
    """
    start = time.time()
    translate = translate or (lambda raw: [raw])
    with events_path.open("wb") as out, stderr_path.open("wb") as err:
        proc = subprocess.Popen(argv, cwd=cwd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=err,
                                env=env, start_new_session=True)

        def pump():
            for raw in proc.stdout:
                for line in translate(raw):
                    out.write(line)
            out.flush()

        reader = threading.Thread(target=pump, daemon=True)
        reader.start()
        try:
            proc.wait(timeout=timeout)
            status = "exited" if proc.returncode == 0 else "failed"
        except subprocess.TimeoutExpired:
            listeners.end_group(proc.pid)  # the whole group, while the unreaped leader still holds its number
            proc.wait()
            status = "timeout"
        reader.join(timeout=10)
        proc.stdout.close()
    return {"status": status, "returncode": proc.returncode, "elapsed_seconds": round(time.time() - start, 1)}


# ---------------------------------------------------------------- hosts

def _isolated_env(home: Path, git_config: Path | None, strip: tuple, extra: dict) -> dict:
    """The environment of a throwaway profile at ``home`` with its own git identity."""
    if git_config is None:
        git_config = home / ".gitconfig"
        git_config.write_text("[user]\n\tname = ShipLoop E2E\n\temail = shiploop-e2e@example.invalid\n")
    env = {k: v for k, v in os.environ.items() if not k.startswith(strip)}
    env.update(HOME=str(home), XDG_CONFIG_HOME=str(home / ".config"),
               XDG_DATA_HOME=str(home / ".local/share"), XDG_CACHE_HOME=str(home / ".cache"),
               XDG_STATE_HOME=str(home / ".local/state"),
               GIT_CONFIG_GLOBAL=str(git_config), GIT_TERMINAL_PROMPT="0", NO_COLOR="1", **extra)
    return env


def _identity(raw: bytes) -> list[bytes]:
    return [raw]


class Host:
    """One headless coding host. Every E2E caller goes through this interface."""

    name = ""
    model = ""
    effort: str | None = None
    skill = "skill-craft:shiploop"   # how this host names the ShipLoop skill
    resumable = False                 # resume a session that ended while the run is active
    keepalive = False                 # install ShipLoop's keepalive hooks before the session
    marketplace = False               # installs from the published marketplace itself

    def env(self, home: Path, git_config: Path | None = None) -> dict:
        return dict(os.environ, GIT_TERMINAL_PROMPT="0", NO_COLOR="1")

    def invoke(self, skill: str, prompt: str) -> str:
        return f"/{skill} {prompt}"

    def argv(self, **kw) -> list[str]:
        raise NotImplementedError

    def install_marketplace(self, env: dict, source: str = MARKETPLACE_SOURCE) -> dict:
        raise NotImplementedError

    def install_plugin(self, env: dict, plugin_dir: Path) -> dict | None:
        """Install a checkout build; None when the host loads it from its argv instead."""
        return None

    def plugin_cli(self, home: Path) -> Path | None:
        """The ShipLoop CLI of the copy of the plugin this host installed into its isolated profile, if it makes one.

        Grok and Codex install a copy and load it, so their packets name that copy. Claude loads --plugin-dir itself,
        so it has no second copy and the plugin dir is its CLI (run.run_cli).
        """
        return None

    def translator(self):
        return _identity

    def cli_version(self, env: dict) -> tuple[str | None, str | None]:
        """(the build of this host's CLI as its own ``--version`` prints it, None) or (None, why not), probed by the
        caller once at launch.

        Claude names its build in its init event, so it is never probed. Never call it to describe a run that was
        launched earlier.
        """
        return None, runrecord.CLAUDE_BUILD  # "Claude: read from the init event after the run"


class GrokHost(Host):
    name, model, effort, skill = "grok", "grok-4.7", "medium", "shiploop"
    resumable = keepalive = marketplace = True

    def __init__(self, binary: str = "grok"):
        self.binary = binary

    def env(self, home, git_config=None):
        """A throwaway HOME whose .grok links only the user's auth.json; no inherited skills."""
        (home / ".grok").mkdir(parents=True, exist_ok=True)
        if not GROK_AUTH.is_file():
            raise SystemExit(f"Grok is not signed in: {GROK_AUTH} is missing (run grok once to log in)")
        link = home / ".grok" / "auth.json"
        if not link.is_symlink():
            link.symlink_to(GROK_AUTH)
        return _isolated_env(home, git_config, ("CLAUDE", "GROK", "XDG_"), {
            "GROK_CONFIG_DIR": str(home / ".grok"), "GROK_CLAUDE_SKILLS_ENABLED": "false",
            "GROK_CURSOR_SKILLS_ENABLED": "false"})

    def argv(self, *, prompt, prompt_file, cwd, model, effort, permission_mode, max_turns,
             max_budget_usd=None, plugin_dir=None, resume=None, allow=()):
        prompt_file.write_text(prompt)
        argv = [self.binary, "--cwd", str(cwd), "--prompt-file", str(prompt_file), "--verbatim",
                "--output-format", "streaming-json", "--model", model,
                *(["--max-turns", str(max_turns)] if max_turns else []),  # no turn limit unless one is asked for
                "--permission-mode", permission_mode, "--no-auto-update"]
        for rule in allow:  # a case's platform.host_allow: auto mode blocks an action it judges the user did not ask for
            argv += ["--allow", rule]
        if resume:
            argv += ["--resume", resume]
        return argv + (["--reasoning-effort", effort] if effort else [])

    def install_marketplace(self, env, source=MARKETPLACE_SOURCE):
        """Install skill-craft the way a user does: add the marketplace, then install the plugin by name.

        Returns the installed plugin's version and directory from Grok's own registry.
        """
        added = subprocess.run([self.binary, "plugin", "marketplace", "add", source], env=env,
                               capture_output=True, text=True)
        installed = subprocess.run([self.binary, "plugin", "install", "skill-craft", "--trust"], env=env,
                                   capture_output=True, text=True)
        registry = Path(env["GROK_CONFIG_DIR"]) / "installed-plugins" / "registry.json"
        repos = json.loads(registry.read_text()).get("repos", {}) if registry.is_file() else {}
        entries = [(repo, meta) for repo, meta in repos.items() if "skill-craft" in (meta.get("plugins") or {})]
        version = entries[0][1]["plugins"]["skill-craft"].get("version") if len(entries) == 1 else None
        path = Path(entries[0][1]["path"]) if len(entries) == 1 else None
        return {"pass": added.returncode == 0 and installed.returncode == 0 and len(entries) == 1
                and len(repos) == 1,
                "source": source, "version": version, "path": str(path) if path else None,
                "loaded": [f"{repo} {meta.get('path')}" for repo, meta in repos.items()],
                "output": (added.stdout + added.stderr + installed.stdout + installed.stderr).strip()[-400:]}

    def install_plugin(self, env, plugin_dir):
        """Install a checkout build; pass only if it is the one plugin in the profile."""
        install = subprocess.run([self.binary, "plugin", "install", str(plugin_dir), "--trust"], env=env,
                                 capture_output=True, text=True)
        listing = subprocess.run([self.binary, "plugin", "list"], env=env, capture_output=True, text=True).stdout
        loaded = re.findall(r"^\s*\S+: (\S+) \[local: (.+)\]", listing, re.M)
        wanted = str(plugin_dir.resolve())
        return {"pass": install.returncode == 0 and loaded == [("skill-craft", wanted)],
                "loaded": [f"{name} {path}" for name, path in loaded], "wanted": wanted}

    def plugin_cli(self, home):
        return next((home / ".grok" / "installed-plugins").glob("skill-craft-*/skills/shiploop/scripts/shiploop"), None)

    def cli_version(self, env):
        return probe_version(self.binary, env)


class ClaudeHost(Host):
    name, model, effort = "claude", "claude-sonnet-5-5", None
    backends = ("anthropic", "ollama")

    def __init__(self, binary: str = "claude", backend: str = "anthropic"):
        if backend not in self.backends:
            raise SystemExit(f"the claude host has no backend {backend!r}; it has {', '.join(self.backends)}")
        self.binary, self.backend = binary, backend
        if backend == "ollama":
            self.model = OLLAMA_MODEL  # the default; the runner sets the run's own model before env()

    def env(self, home, git_config=None):
        if self.backend != "ollama":
            return super().env(home, git_config)
        env = {k: v for k, v in os.environ.items() if not k.startswith(OLLAMA_SCRUB_PREFIXES)}
        env.update(GIT_TERMINAL_PROMPT="0", NO_COLOR="1", ANTHROPIC_BASE_URL=OLLAMA_URL, ANTHROPIC_API_KEY="ollama",
                   **{name: self.model for name in OLLAMA_MODEL_VARS})
        return env

    def argv(self, *, prompt, prompt_file, cwd, model, effort, permission_mode, max_turns,
             max_budget_usd=None, plugin_dir=None, resume=None, allow=()):
        argv = [self.binary, "-p", prompt, "--model", model,
                *(["--max-turns", str(max_turns)] if max_turns else []),  # no turn limit unless one is asked for
                *(["--max-budget-usd", str(max_budget_usd)] if max_budget_usd else []),  # no spend limit unless asked
                "--permission-mode", permission_mode,
                "--output-format", "stream-json", "--verbose", "--no-session-persistence",
                "--setting-sources", "project,local", "--strict-mcp-config"]
        if self.backend == "ollama":
            argv += ["--tools", ",".join(OLLAMA_TOOLS)]
        if allow:
            argv += ["--allowedTools", ",".join(allow)]
        if effort:
            argv += ["--effort", effort]
        if plugin_dir is not None:
            argv += ["--plugin-dir", str(plugin_dir.resolve())]
        return argv


class CodexHost(Host):
    """``codex exec --json`` in a throwaway CODEX_HOME; its stream is translated to Grok's shape.

    Codex has no turn cap or dollar figure: ``max_turns`` and ``max_budget_usd``
    are not applied, and cost is reported as unknown. The session runs with
    ``danger-full-access`` and no approvals, as the other hosts run unattended.
    """

    name, model, effort = "codex", "gpt-6-luna", "xhigh"
    resumable = marketplace = True

    def __init__(self, binary: str = "codex"):
        self.binary = binary

    def env(self, home, git_config=None):
        codex_home = home / ".codex"
        codex_home.mkdir(parents=True, exist_ok=True)
        auth = Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex") / "auth.json"
        if not auth.is_file():
            raise SystemExit(f"Codex is not signed in: {auth} is missing (run codex once to log in)")
        link = codex_home / "auth.json"
        if not link.is_symlink():
            link.symlink_to(auth)
        return _isolated_env(home, git_config, ("CLAUDE", "CODEX", "XDG_"), {"CODEX_HOME": str(codex_home)})

    def invoke(self, skill, prompt):
        return f"${skill} {prompt}"

    def argv(self, *, prompt, prompt_file, cwd, model, effort, permission_mode, max_turns,
             max_budget_usd=None, plugin_dir=None, resume=None, allow=()):
        # `allow` is not used: this host runs with approval_policy "never", so no action waits for a permission.
        prompt_file.write_text(prompt)
        argv = [self.binary, "exec", "--json", "-m", model, "--skip-git-repo-check",
                "-s", "danger-full-access", "-c", 'approval_policy="never"', "-C", str(cwd)]
        if effort:
            argv += ["-c", f"model_reasoning_effort={effort}"]
        return argv + (["resume", resume, prompt] if resume else [prompt])

    def install_marketplace(self, env, source=MARKETPLACE_SOURCE):
        added = subprocess.run([self.binary, "plugin", "marketplace", "add", source], env=env,
                               capture_output=True, text=True)
        installed = subprocess.run([self.binary, "plugin", "add", "skill-craft@whichguy"], env=env,
                                   capture_output=True, text=True)
        listing = subprocess.run([self.binary, "plugin", "list", "--marketplace", "whichguy", "--json"], env=env,
                                 capture_output=True, text=True)
        try:
            rows = [row for row in json.loads(listing.stdout).get("installed", []) if row.get("installed")]
        except ValueError:
            rows = []
        ours = [row for row in rows if row.get("name") == "skill-craft"]
        root = (Path(env["CODEX_HOME"]) / "plugins" / "cache" / "whichguy" / "skill-craft" / ours[0]["version"]
                if len(ours) == 1 and ours[0].get("version") else None)
        return {"pass": added.returncode == 0 and installed.returncode == 0 and len(rows) == 1 and len(ours) == 1
                and root is not None and root.is_dir(),
                "source": source, "version": ours[0].get("version") if len(ours) == 1 else None,
                "path": str(root) if root else None,
                "loaded": [f"{row.get('pluginId')} {row.get('version')}" for row in rows],
                "output": (added.stdout + added.stderr + installed.stdout + installed.stderr).strip()[-400:]}

    def install_plugin(self, env, plugin_dir):
        """A checkout build: its root (two levels above the plugin) carries Codex's catalog."""
        installed = self.install_marketplace(env, str(Path(plugin_dir).resolve().parents[1]))
        return {"pass": installed["pass"], "loaded": installed["loaded"], "wanted": str(plugin_dir),
                "path": installed["path"]}

    def plugin_cli(self, home):
        return next((home / ".codex" / "plugins" / "cache").glob("*/skill-craft/*/skills/shiploop/scripts/shiploop"),
                    None)

    def cli_version(self, env):
        return probe_version(self.binary, env)

    def translator(self):
        return CodexTranslator()


class CodexTranslator:
    """Rewrite ``codex exec --json`` lines as the Grok events the parsers read.

    thread.started -> available_commands (with the session id); a command item
    -> tool_call plus tool_call_update carrying output and exit code; a file
    change -> an edit tool call; agent messages -> text; reasoning -> thought;
    turn.completed or turn.failed -> end with the session id, usage and a turn
    count (items completed, since Codex reports no per-call usage).
    """

    TOOL = {"command_execution": "run_terminal_command", "file_change": "search_replace",
            "mcp_tool_call": "mcp_tool", "web_search": "web_search", "todo_list": "todo_write"}

    def __init__(self):
        self.session = None
        self.items = 0
        self.called: set = set()

    @staticmethod
    def _line(event: dict) -> bytes:
        return (json.dumps(event) + "\n").encode()

    def _call(self, item: dict) -> dict:
        kind = item.get("type")
        arg: dict = {}
        if kind == "command_execution":
            arg = {"command": item.get("command") or ""}
        elif kind == "file_change":
            paths = [c.get("path") for c in item.get("changes") or [] if isinstance(c, dict)]
            arg = {"target_file": paths[0] if paths else "", "paths": paths}
        else:
            arg = {k: item[k] for k in ("server", "tool", "query", "arguments") if k in item}
        name = self.TOOL.get(kind, str(kind))
        return {"type": "tool_call", "toolCallId": item.get("id"), "title": name, "toolName": name,
                "status": "pending", "rawInput": arg}

    def __call__(self, raw: bytes) -> list[bytes]:
        try:
            event = json.loads(raw)
        except ValueError:
            return [raw]
        if not isinstance(event, dict):
            return [raw]
        kind = event.get("type")
        item = event.get("item") if isinstance(event.get("item"), dict) else {}
        itype = item.get("type")
        out: list[dict] = []
        if kind == "thread.started":
            self.session = event.get("thread_id")
            out.append({"type": "available_commands", "commands": [], "sessionId": self.session})
        elif kind == "item.started" and itype in self.TOOL:
            self.called.add(item.get("id"))
            out.append(self._call(item))
        elif kind == "item.completed":
            self.items += 1
            if itype == "agent_message":
                out.append({"type": "text", "data": str(item.get("text") or "") + "\n"})
            elif itype == "reasoning":
                out.append({"type": "thought", "data": str(item.get("text") or "")})
            elif itype:
                if item.get("id") not in self.called:
                    out.append(self._call(item))
                output = item.get("aggregated_output")
                if output is None:
                    output = json.dumps({k: v for k, v in item.items() if k not in ("id", "type")})
                failed = item.get("status") == "failed"
                out.append({"type": "tool_call_update", "toolCallId": item.get("id"),
                            "status": "failed" if failed else "completed",
                            "content": [{"type": "content", "content": {"type": "text", "text": str(output)}}],
                            "rawOutput": {"type": itype, "output_for_prompt": str(output),
                                          "exit_code": item.get("exit_code"), "command": item.get("command")}})
        elif kind in ("turn.completed", "turn.failed"):
            usage = event.get("usage") or {}
            out.append({"type": "end", "stopReason": "end_turn" if kind == "turn.completed" else "error",
                        "sessionId": self.session, "num_turns": self.items, "total_cost_usd": None,
                        "usage": {"input_tokens": usage.get("input_tokens"),
                                  "cache_read_input_tokens": usage.get("cached_input_tokens"),
                                  "output_tokens": usage.get("output_tokens"),
                                  "reasoning_tokens": usage.get("reasoning_output_tokens")},
                        "error": (event.get("error") or {}).get("message") if kind == "turn.failed" else None})
            self.items = 0
        elif kind == "error":
            out.append({"type": "text", "data": "[codex error] " + str(event.get("message")) + "\n"})
        return [self._line(e) for e in out]


HOSTS: dict[str, type] = {"grok": GrokHost, "claude": ClaudeHost, "codex": CodexHost}
HOST_DEFAULTS = {name: {"model": cls.model, "effort": cls.effort} for name, cls in HOSTS.items()}


def host(name: str, binary: str | None = None, backend: str | None = None) -> Host:
    """The host object for ``name``, optionally with a non-default binary and, for the Claude host, a backend."""
    cls = HOSTS[name]
    if backend not in (None, "anthropic") and "backends" not in vars(cls):
        raise SystemExit(f"--backend {backend} is a Claude host option; the {name} host has one backend")
    kwargs = {"backend": backend} if backend else {}
    return cls(binary, **kwargs) if binary else cls(**kwargs)

