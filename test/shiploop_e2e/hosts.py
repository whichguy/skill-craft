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

from contextlib import ExitStack
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parent))
import grok_preempt  # noqa: E402  (the PreToolUse hook a Grok profile gets, beside the keepalive)
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
# The host an E2E run drives when no --host is given. An explicitly selected Claude host runs Claude's own models
# (Sonnet 5.5, backend "anthropic") like every other Claude caller; `--backend ollama` selects a model the local Ollama
# server serves (owner, 2026-11-01, replacing the 2026-10-26 default of Ollama's DeepSeek flash).
# Antigravity Orchestrator (Neon) (`gemini-pro-orchestrator-neon`, pairing Neon planning with Carbon execution
# internally) is the default profile for new subjects, reviewers, judges, and improvers (owner, 2026-11-25,
# replacing Codex GPT-6.2 Sol at extra-high from 2026-11-19 for subjects and matching the 2026-11-25 evaluator default).
RUN_DEFAULT_HOST = "antigravity"
GROK_DEFAULT_MODEL = "grok-4.6"
GROK_DEFAULT_EFFORT = "xhigh"
CODEX_DEFAULT_MODEL = "gpt-6.2-sol"
CODEX_DEFAULT_EFFORT = "xhigh"
CODEX_AUTO_REVIEW = "auto-review"
# Note on Antigravity orchestrator indirection: `agy models` defines concrete orchestrator slugs
# (`gemini-pro-orchestrator-neon` -> Orchestrator (Neon), `gemini-pro-orchestrator` -> Orchestrator (Carbon),
# `gemini-pro-orchestrator-argon` -> Orchestrator (Argon)) and `agy` rejects a bare `--model orchestrator` slug while
# omitting `--model` falls back to single-model `gemini-4-neon-high` rather than an orchestrator. The harness provides
# the `orchestrator` alias and `SHIPLOOP_E2E_ANTIGRAVITY_ORCHESTRATOR` env override so callers can target the active
# Antigravity orchestrator indirectly while resolving to a concrete model slug before launch and recording.
ANTIGRAVITY_ORCHESTRATOR_ALIAS = "orchestrator"
ANTIGRAVITY_ORCHESTRATOR_ENV = "SHIPLOOP_E2E_ANTIGRAVITY_ORCHESTRATOR"
ANTIGRAVITY_ORCHESTRATOR_MODEL = "gemini-pro-orchestrator-neon"
ANTIGRAVITY_DEFAULT_MODEL = ANTIGRAVITY_ORCHESTRATOR_MODEL
ANTIGRAVITY_DEFAULT_EFFORT = None


def default_antigravity_orchestrator() -> str:
    """Return the active Antigravity orchestrator model slug (env override or repo default)."""
    return os.environ.get(ANTIGRAVITY_ORCHESTRATOR_ENV, "").strip() or ANTIGRAVITY_ORCHESTRATOR_MODEL


def resolve_antigravity_model(model: str | None) -> str | None:
    """Resolve the generic Antigravity ``orchestrator`` alias to its concrete model slug."""
    if model == ANTIGRAVITY_ORCHESTRATOR_ALIAS:
        return default_antigravity_orchestrator()
    return model


def permission_args(mode: str) -> list[str]:
    return ["--codex-auto-review"] if mode == CODEX_AUTO_REVIEW else ["--permission-mode", mode]


def resolve_role(name: str, overrides: dict | None = None) -> dict:
    """Return a role's host/model/effort, applying explicit overrides.

    Changing hosts selects that host's defaults. An explicit model or effort then wins.
    """
    if name not in ROLE_DEFAULTS:
        raise ValueError(f"unknown ShipLoop E2E role {name!r}; known: {', '.join(sorted(ROLE_DEFAULTS))}")
    resolved = dict(ROLE_DEFAULTS[name])
    overrides = overrides or {}
    host_override = overrides.get("host")
    if host_override is not None and host_override != resolved["host"]:
        if host_override not in HOSTS:
            raise ValueError(f"unknown E2E host {host_override!r}; known: {', '.join(sorted(HOSTS))}")
        resolved.update(host=host_override, model=HOST_DEFAULTS[host_override]["model"],
                        effort=ROLE_EFFORT.get(name, HOST_DEFAULTS[host_override]["effort"]))
    for key in ("host", "model", "effort"):
        value = overrides.get(key)
        if value is not None:
            resolved[key] = value
    if resolved["host"] == "antigravity":
        env_orch = os.environ.get(ANTIGRAVITY_ORCHESTRATOR_ENV, "").strip()
        if resolved["model"] == ANTIGRAVITY_ORCHESTRATOR_ALIAS:
            resolved["model"] = default_antigravity_orchestrator()
        elif (
            overrides.get("model") is None
            and (host_override is None or host_override == ROLE_DEFAULTS[name]["host"])
            and name in ROLE_DEFAULTS
            and env_orch
        ):
            resolved["model"] = env_orch
    return resolved


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
              timeout: int, translate=None, *, stdin_payload: bytes | None = None) -> dict:
    """Run one headless host process to completion (or kill it at `timeout`).

    ``translate`` (a host's ``translator()``) rewrites each stdout line into the
    shared event shape as it is written. A non-None ``stdin_payload`` is buffered
    in a scoped binary regular file, including when empty; None keeps DEVNULL.
    """
    start = time.time()
    translate = translate or (lambda raw: [raw])
    with ExitStack() as stack:
        out = stack.enter_context(events_path.open("wb"))
        err = stack.enter_context(stderr_path.open("wb"))
        stdin = subprocess.DEVNULL
        if stdin_payload is not None:
            stdin = stack.enter_context(tempfile.TemporaryFile("w+b"))
            stdin.write(stdin_payload)
            stdin.seek(0)
        proc = subprocess.Popen(argv, cwd=cwd, stdin=stdin, stdout=subprocess.PIPE, stderr=err,
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

# A throwaway HOME has no login keychain, so a CLI that stores a secret in the keychain makes macOS show a modal "Keychain Not
# Found" dialog on the owner's screen and blocks until someone answers it. The Salesforce CLI does this on its first org command
# in a new HOME (it creates its key: service `sfdx`, account `local`, so the dialog says it cannot store "local"); this variable
# makes it keep the key in <HOME>/.sfdx/key.json instead, and the command fails at once for want of a login. A command that runs
# with the real HOME (platform.model_bin) unsets it, so the real CLI keeps reading its key from the real keychain.
THROWAWAY_HOME_ENV = {"SF_USE_GENERIC_UNIX_KEYCHAIN": "true"}

# The same dialog comes from any program the model starts that saves a secret, and a variable cannot reach them all: Google Chrome
# started by a model-written browser test without --use-mock-keychain saves its "Chrome Safe Storage" key at launch, and most such
# tests name /Applications/Google Chrome.app directly, so no PATH wrapper or CHROME_PATH sees them (2026-11-15: 67 of the 123 distinct
# raw launchers under ~/e2e-runs). So the throwaway HOME gets its own keychain. macOS looks for the user's keychain under $HOME
# (with HOME set to an empty folder `security default-keychain -d user` finds none), so an empty-password keychain at
# <HOME>/Library/Keychains/login.keychain-db, never auto-locked, is where such a program stores its secret, with no dialog. It
# writes nothing outside that HOME (measured: the real keychain list, default keychain and security preferences unchanged).
SECURITY = "/usr/bin/security"
THROWAWAY_KEYCHAIN = "Library/Keychains/login.keychain-db"


def throwaway_keychain(home: Path) -> Path | None:
    """Give the throwaway HOME ``home`` an empty, unlocked login keychain, so a program that saves a secret raises no dialog.

    macOS only (None elsewhere); a HOME that already has one keeps it. Raises RuntimeError when ``security`` fails: a run without
    the keychain could stop on a modal dialog on the owner's screen, so it does not start."""
    if sys.platform != "darwin" or not os.access(SECURITY, os.X_OK):
        return None
    path = home / THROWAWAY_KEYCHAIN
    if path.exists():
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, HOME=str(home))
    # create-keychain leaves it unlocked; set-keychain-settings with no option turns off the lock timeout and the lock on sleep.
    for argv in ([SECURITY, "create-keychain", "-p", "", str(path)], [SECURITY, "set-keychain-settings", str(path)]):
        done = subprocess.run(argv, env=env, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=30, check=False)
        if done.returncode != 0:
            raise RuntimeError(f"{' '.join(argv[:2])} for the throwaway HOME {home} failed ({done.returncode}): "
                               f"{(done.stderr or done.stdout).strip()}")
    return path


# The startup files a shell the model may use reads after /etc/zprofile or /etc/profile ran macOS path_helper: zsh login (.zprofile),
# zsh interactive (.zshrc), bash login (the first of .bash_profile, .profile) and bash interactive (.bashrc). run.pin_shell_path uses them too.
SHELL_STARTUP_FILES = (".zprofile", ".zshrc", ".bash_profile", ".bashrc", ".profile")

# python3, in every shell a model may use in a throwaway HOME, is this harness's own interpreter. ShipLoop itself runs on
# Python 3.9+ (skills/shiploop/scripts/shiploop_pyfloor.py, 12c8f967b868f0f51994ba76d2176adc94a989ac), while Codex and Grok run commands
# in login shells where macOS path_helper puts /usr/bin first: a throwaway HOME has none of the owner's startup files, so python3 fell
# back to Apple's 3.9.6 instead of the harness's interpreter. Pinning python3 keeps the child on the same interpreter across shells
# so a run's outcome does not depend on which Python happened to sit first on PATH (2026-11-18, docs/closed-loop-journal.md R15). The pin is the guarded commands' mechanism (run.pin_shell_path):
# a marked PATH line in each startup file, which runs after path_helper, and the same folder first in the environment's PATH for shells
# that read no startup file.
PYTHON_PIN_DIR = ".skill-craft-e2e/python"
PYTHON_PIN_MARK = "# skill-craft E2E: python3 is the harness's own interpreter, first on PATH after macOS path_helper"


def pin_python(home: Path) -> Path:
    """Give the throwaway ``home`` a folder whose ``python3`` runs this harness's interpreter, and pin it first on PATH for login and
    interactive shells: a marked block appended once to each of SHELL_STARTUP_FILES (a startup file that is a symlink is never written
    through). Returns the folder."""
    folder = home / PYTHON_PIN_DIR
    folder.mkdir(parents=True, exist_ok=True)
    wrapper = folder / "python3"
    wrapper.write_text(f'#!/bin/sh\nexec {shlex.quote(sys.executable)} "$@"\n')
    wrapper.chmod(0o755)
    block = f'{PYTHON_PIN_MARK}\nPATH={shlex.quote(str(folder))}":$PATH"\nexport PATH\n'
    for name in SHELL_STARTUP_FILES:
        path = home / name
        if path.is_symlink():
            continue
        text = path.read_text(errors="replace") if path.exists() else ""
        if block not in text:
            with path.open("a") as handle:
                handle.write(("" if not text or text.endswith("\n") else "\n") + block)
    return folder


def _isolated_env(home: Path, git_config: Path | None, strip: tuple, extra: dict) -> dict:
    """The environment of a throwaway profile at ``home`` with its own git identity, its own keychain, and this harness's
    interpreter as ``python3`` in every shell (pin_python)."""
    if git_config is None:
        git_config = home / ".gitconfig"
        git_config.write_text("[user]\n\tname = ShipLoop E2E\n\temail = shiploop-e2e@example.invalid\n")
    throwaway_keychain(home)
    python_folder = pin_python(home)
    env = {k: v for k, v in os.environ.items() if not k.startswith(strip)}
    env["PATH"] = f"{python_folder}{os.pathsep}{env.get('PATH', os.defpath)}"
    env.update(HOME=str(home), XDG_CONFIG_HOME=str(home / ".config"),
               XDG_DATA_HOME=str(home / ".local/share"), XDG_CACHE_HOME=str(home / ".cache"),
               XDG_STATE_HOME=str(home / ".local/state"),
               GIT_CONFIG_GLOBAL=str(git_config), GIT_TERMINAL_PROMPT="0", NO_COLOR="1", **THROWAWAY_HOME_ENV, **extra)
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
    # A shell call the host's permission check refuses ends the session (Grok headless, --permission-mode auto), so the
    # prompt that resumes it says so (run.refusal_note).
    refusal_ends_session = False

    def env(self, home: Path, git_config: Path | None = None) -> dict:
        return dict(os.environ, GIT_TERMINAL_PROMPT="0", NO_COLOR="1")

    def keepalive_install(self, env: dict, plugin_dir: Path) -> dict | None:
        """The keepalive block the run records: the hooks this host has before the session starts, or None for a host with none."""
        return grok_keepalive(env, plugin_dir) if self.keepalive else None

    def preempt_install(self, env: dict) -> dict | None:
        """The preempt block the run records: the hook that refuses in the turn a call the host's permission check would
        refuse by ending the session (grok_preempt), installed before the session starts, or None for a host with none."""
        return None

    def preempt_record(self, env: dict) -> dict | None:
        """The preempt block of a run that starts no host (a regrade): the hook its profile already holds, read only."""
        return None

    def invoke(self, skill: str, prompt: str) -> str:
        return f"/{skill} {prompt}"

    def argv(self, **kw) -> list[str]:
        raise NotImplementedError

    def prepare(self, **kwargs) -> tuple[list[str], bytes | None]:
        """Prepare a buffered helper launch, preserving legacy argv by default."""
        return self.argv(**kwargs), None

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
    name, model, effort, skill = "grok", GROK_DEFAULT_MODEL, GROK_DEFAULT_EFFORT, "shiploop"
    resumable = keepalive = marketplace = refusal_ends_session = True

    def preempt_install(self, env):
        """grok_preempt's hook in the run's throwaway profile (GROK_CONFIG_DIR), never in the user's own ~/.grok."""
        return grok_preempt.install(Path(env["GROK_CONFIG_DIR"]))

    def preempt_record(self, env):
        return grok_preempt.installed(Path(env["GROK_CONFIG_DIR"]))

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
    are not applied, and cost is reported as unknown. The auto-review route
    uses the workspace sandbox and automatic review of individual commands.
    Legacy launches keep their original permission settings.

    Codex runs a plugin's hooks (``hooks/codex.json``: the keepalive, its session-end hook, the status display) only
    once they are trusted, and a throwaway CODEX_HOME holds no trust, so ``argv`` passes
    ``--dangerously-bypass-hook-trust`` (owner, 2026-10-29). That is safe here because nothing else can run: ``env``
    links ``auth.json`` and nothing with a hook, and the only plugin installed is the one this harness installs
    (the published marketplace, or a build of this checkout).
    """

    name, model, effort = "codex", CODEX_DEFAULT_MODEL, CODEX_DEFAULT_EFFORT
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
             max_budget_usd=None, plugin_dir=None, resume=None, allow=(), workspace_state=None):
        if permission_mode not in (None, "auto", "never", "read-only", CODEX_AUTO_REVIEW):
            raise ValueError(f"unsupported Codex permission mode: {permission_mode}")
        prompt_file.write_bytes(prompt.encode("utf-8"))
        legacy = "read-only" if permission_mode == "read-only" else "danger-full-access"
        permissions = ["-s", legacy, "-c", 'approval_policy="never"']
        if permission_mode == CODEX_AUTO_REVIEW:
            # The working directory and the sibling ShipLoop workspace need
            # writes. The harness's own evidence lives outside both.
            recovery = (
                f"This run owns the disposable checkout {Path(cwd).resolve()}. "
                "Git initialization, worktree creation and commits in that checkout are expected. "
                "If a command in this run is refused because its Git metadata is protected, "
                "retry that exact command with exec_command sandbox_permissions set to require_escalated "
                "and a justification naming the checked-out path, so it receives individual automatic review."
            )
            permissions = ["--approve-for-me",
                           *(["--add-dir", str(workspace_state.resolve())] if workspace_state is not None else []),
                           "-c", f"developer_instructions={json.dumps(recovery)}",
                           "-c", "sandbox_workspace_write.exclude_slash_tmp=true",
                           "-c", "sandbox_workspace_write.exclude_tmpdir_env_var=true",
                           "-c", "sandbox_workspace_write.network_access=false",
                           "-c", "sandbox_workspace_write.writable_roots=[]"]
        argv = [self.binary, "exec", "--json", "-m", model, "--skip-git-repo-check",
                *permissions,
                "--dangerously-bypass-hook-trust", "-C", str(cwd),
                # Keep default native workers on this launch's resolved model, including explicit overrides and resumes.
                "-c", f"agents.default_subagent_model={json.dumps(model)}"]
        if effort:
            argv += ["-c", f"model_reasoning_effort={effort}", "-c", f"agents.default_subagent_reasoning_effort={effort}"]
        return argv + (["resume", resume, prompt] if resume else [prompt])

    def prepare(self, **kwargs) -> tuple[list[str], bytes | None]:
        """Keep the full prompt as evidence and send helper input through stdin."""
        argv = self.argv(**kwargs)
        payload = kwargs["prompt"].encode("utf-8")
        argv[-1] = "-"
        return argv, payload

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
                "path": installed["path"], "output": installed["output"]}

    def keepalive_install(self, env, plugin_dir):
        """Codex loads the plugin's own hooks, so nothing is installed: the block says whether the plugin brought them."""
        brought = (Path(plugin_dir) / "hooks" / "codex.json").is_file()
        return {"installed": brought, "output": "the plugin's hooks/codex.json, run with the trust bypass"
                if brought else f"no hooks/codex.json in {plugin_dir}"}

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
        elif kind == "item.completed" and itype == "error":
            # A notice from Codex itself (the trust bypass, a clamped hook timeout), not a tool call and not a turn.
            out.append({"type": "thought", "data": "[codex notice] " + str(item.get("message") or "") + "\n"})
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


class AntigravityHost(Host):
    """``agy --output-format stream-json`` with a staged native plugin in ``--add-dir``."""

    name, model, effort, skill = "antigravity", ANTIGRAVITY_DEFAULT_MODEL, ANTIGRAVITY_DEFAULT_EFFORT, "shiploop"
    resumable = True

    def __init__(self, binary: str = "agy"):
        self.binary = binary
        self._stage_root: Path | None = None

    def env(self, home, git_config=None):
        """Isolate Antigravity in a throwaway HOME while linking ~/.gemini and macOS Keychains for agy OAuth."""
        home = Path(home)
        real_home = Path(os.environ.get("HOME") or Path.home())
        home.mkdir(parents=True, exist_ok=True)
        if home.resolve() != real_home.resolve():
            link_specs: list[tuple[str, ...]] = [(".gemini",)]
            if sys.platform == "darwin":
                link_specs.append(("Library", "Keychains"))
            for parts in link_specs:
                src = real_home.joinpath(*parts)
                dst = home.joinpath(*parts)
                if src.exists() and not os.path.lexists(dst):
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    dst.symlink_to(src)
        if git_config is None:
            git_config = home / ".gitconfig"
            git_config.write_text("[user]\n\tname = ShipLoop E2E\n\temail = shiploop-e2e@example.invalid\n")
        python_folder = pin_python(home)
        self._stage_root = home / ".antigravity-e2e"
        drop_Exact = {"ANTIGRAVITY_AGENT", "ANTIGRAVITY_CONVERSATION_ID", "ANTIGRAVITY_TRAJECTORY_ID"}
        env = {k: v for k, v in os.environ.items()
               if not k.startswith(("CLAUDE", "CODEX", "GROK")) and k not in drop_Exact}
        env["PATH"] = f"{python_folder}{os.pathsep}{env.get('PATH', os.defpath)}"
        env.update(
            HOME=str(home),
            GIT_CONFIG_GLOBAL=str(git_config),
            GIT_TERMINAL_PROMPT="0",
            NO_COLOR="1",
            SHIPLOOP_KEEPALIVE_HOME=str(home / ".local" / "state" / "shiploop" / "keepalive"),
            **THROWAWAY_HOME_ENV,
        )
        return env

    def install_plugin(self, env, plugin_dir):
        """Stage a native Antigravity plugin checkout build so ``--add-dir`` discovers it."""
        stage_root = self._stage_root
        if stage_root is None:
            keepalive_home = env.get("SHIPLOOP_KEEPALIVE_HOME")
            stage_root = (Path(keepalive_home).parents[3] if keepalive_home else Path(plugin_dir).parent) / ".antigravity-e2e"
            self._stage_root = stage_root
        dest = stage_root / ".agents" / "plugins" / "skill-craft"
        shutil.rmtree(dest, ignore_errors=True)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(plugin_dir, dest)
        ok = (dest / ".antigravity-plugin" / "plugin.json").is_file() and (dest / "skills" / "shiploop" / "SKILL.md").is_file()
        return {"pass": ok, "loaded": [f"skill-craft {dest}"] if ok else [], "wanted": str(plugin_dir),
                "path": str(dest) if ok else None,
                "output": "" if ok else f"missing .antigravity-plugin/plugin.json or skills/shiploop/SKILL.md in {dest}"}

    def keepalive_install(self, env, plugin_dir):
        brought = (Path(plugin_dir) / "hooks.json").is_file()
        return {"installed": brought,
                "output": "the plugin's native hooks.json" if brought else f"no hooks.json in {plugin_dir}"}

    def plugin_cli(self, home):
        cli = home / ".antigravity-e2e" / ".agents" / "plugins" / "skill-craft" / "skills" / "shiploop" / "scripts" / "shiploop"
        return cli if cli.is_file() else None

    def argv(self, *, prompt, prompt_file, cwd, model, effort, permission_mode, max_turns,
             max_budget_usd=None, plugin_dir=None, resume=None, allow=(), workspace_state=None):
        prompt_file.write_bytes(prompt.encode("utf-8"))
        model = resolve_antigravity_model(model)
        argv = [self.binary, "--output-format", "stream-json"]
        if model:
            argv += ["--model", model]
        if effort:
            argv += ["--effort", effort]
        if permission_mode == "read-only":
            # Headless `agy --mode plan` alone auto-denies terminal inspection commands without prompting;
            # `--mode plan --sandbox --dangerously-skip-permissions` preserves Plan mode + sandbox restrictions.
            argv += ["--mode", "plan", "--sandbox", "--dangerously-skip-permissions"]
        elif permission_mode == "plan":
            argv += ["--mode", "plan"]
        elif permission_mode == "accept-edits":
            argv += ["--mode", "accept-edits"]
        else:
            argv += ["--dangerously-skip-permissions"]
        if self._stage_root is not None:
            argv += ["--add-dir", str(self._stage_root)]
        elif plugin_dir is not None:
            argv += ["--add-dir", str(Path(plugin_dir).resolve())]
        if workspace_state is not None:
            argv += ["--add-dir", str(workspace_state.resolve())]
        if resume:
            argv += ["--resume", resume]
        # Attach prompt with = last because bare --print consumes the next token as the prompt.
        return argv + [f"--print={prompt}"]

    def cli_version(self, env):
        return probe_version(self.binary, env)

    def translator(self):
        return AntigravityTranslator()


class AntigravityTranslator:
    """Rewrite ``agy --output-format stream-json`` lines into Grok's streaming JSON event shape."""

    _EXIT_RE = re.compile(r"Command exited with code (\d+)\.")

    def __init__(self):
        self.session = None
        self.turns = 0
        self.called: set = set()

    @staticmethod
    def _line(event: dict) -> bytes:
        return (json.dumps(event) + "\n").encode()

    @staticmethod
    def _usage(raw_usage: dict) -> dict:
        return {
            "input_tokens": raw_usage.get("input_tokens"),
            "cache_read_input_tokens": raw_usage.get("cache_read_tokens"),
            "output_tokens": raw_usage.get("output_tokens"),
            "reasoning_tokens": raw_usage.get("thinking_tokens"),
        }

    def __call__(self, raw: bytes) -> list[bytes]:
        try:
            event = json.loads(raw)
        except ValueError:
            return [raw]
        if not isinstance(event, dict):
            return [raw]
        kind = event.get("event")
        out: list[dict] = []
        if kind == "init":
            self.session = event.get("conversation_id")
            out.append({"type": "available_commands", "commands": [], "sessionId": self.session})
        elif kind == "step_update":
            su = event.get("step_update") if isinstance(event.get("step_update"), dict) else {}
            stype = su.get("step_type")
            state = su.get("state")
            idx = su.get("step_index")
            if stype in ("tool", "subagent"):
                call_id = f"step-{idx}"
                tname = su.get("tool_name") or ("invoke_subagent" if stype == "subagent" else "tool")
                info = (su.get("subagent_info") if stype == "subagent" else su.get("tool_info")) or {}
                params = info.get("parameters") if isinstance(info.get("parameters"), dict) else (info if stype == "subagent" else {})
                mapped_name = "run_terminal_command" if tname == "run_command" else tname
                raw_input = {"command": params.get("CommandLine") or ""} if tname == "run_command" else params
                if call_id not in self.called:
                    self.called.add(call_id)
                    out.append({"type": "tool_call", "toolCallId": call_id, "title": mapped_name,
                                "toolName": mapped_name, "status": "pending", "rawInput": raw_input})
                if state in ("DONE", "ERROR"):
                    err = info.get("error") if isinstance(info.get("error"), dict) else {}
                    output = info.get("output")
                    if output is None:
                        output = err.get("message") or (json.dumps(info) if info else "")
                    output = str(output)
                    exit_code = None
                    if tname == "run_command":
                        match = self._EXIT_RE.search(output)
                        exit_code = int(match.group(1)) if match else (1 if state == "ERROR" or err else None)
                    failed = (state == "ERROR") or bool(err) or (exit_code not in (None, 0))
                    raw_out = {"type": tname, "output_for_prompt": output}
                    if tname == "run_command":
                        raw_out["exit_code"] = exit_code
                        raw_out["command"] = params.get("CommandLine")
                    out.append({"type": "tool_call_update", "toolCallId": call_id,
                                "status": "failed" if failed else "completed",
                                "content": [{"type": "content", "content": {"type": "text", "text": output}}],
                                "rawOutput": raw_out})
            elif stype == "agent_response":
                delta = su.get("text_delta")
                if isinstance(delta, str) and delta:
                    out.append({"type": "text", "data": delta})
                if state == "DONE" and isinstance(su.get("usage"), dict):
                    self.turns += 1
                    out.append({"type": "usage", "usage": self._usage(su["usage"])})
        elif kind == "result":
            res = event.get("result") if isinstance(event.get("result"), dict) else {}
            usage = res.get("usage") if isinstance(res.get("usage"), dict) else {}
            sid = res.get("conversation_id") or self.session
            num_turns = self.turns or res.get("num_turns") or 1
            out.append({"type": "end",
                        "stopReason": "end_turn" if res.get("status") == "SUCCESS" else "error",
                        "sessionId": sid, "num_turns": num_turns, "total_cost_usd": None,
                        "usage": self._usage(usage) if usage else None,
                        "error": res.get("error")})
            self.turns = 0
        return [self._line(e) for e in out]


def enforce_readonly_sandbox(host_name: str, argv: list[str], *, context: str) -> None:
    """Ensure ``argv`` carries the host's explicit read-only sandbox flags (mutating Codex ``-s`` to ``read-only``)."""
    if host_name == "codex":
        try:
            sandbox_index = argv.index("-s")
        except ValueError as exc:
            raise RuntimeError(f"CodexHost.argv did not provide the sandbox option required by {context}") from exc
        argv[sandbox_index + 1] = "read-only"
    elif host_name == "antigravity":
        has_plan = "--mode" in argv and argv.index("--mode") + 1 < len(argv) and argv[argv.index("--mode") + 1] == "plan"
        if not (has_plan and "--sandbox" in argv):
            raise RuntimeError(f"AntigravityHost.argv did not provide the read-only sandbox flags required by {context}")


HOSTS: dict[str, type] = {"antigravity": AntigravityHost, "grok": GrokHost, "claude": ClaudeHost, "codex": CodexHost}
HOST_DEFAULTS = {name: {"model": cls.model, "effort": cls.effort} for name, cls in HOSTS.items()}
# Owner-selected profiles for new work (2026-11-25): subject, reviewer, judge and improver all default to
# Antigravity Orchestrator (Neon) (`gemini-pro-orchestrator-neon`, pairing Neon planning with Carbon execution
# internally), replacing Codex GPT-6.2 Sol at extra-high for subjects (2026-11-19) and Codex Astra/Sol for evaluators.
# Recorded and explicit profiles (such as `--host codex` with GPT-6.2 Sol `xhigh`) remain authoritative.
ROLE_DEFAULTS = {
    "subject": {"host": RUN_DEFAULT_HOST, **HOST_DEFAULTS[RUN_DEFAULT_HOST]},
    "reviewer": {"host": "antigravity", "model": ANTIGRAVITY_ORCHESTRATOR_MODEL, "effort": None},
    "judge": {"host": "antigravity", "model": ANTIGRAVITY_ORCHESTRATOR_MODEL, "effort": None},
    "improver": {"host": "antigravity", "model": ANTIGRAVITY_ORCHESTRATOR_MODEL, "effort": None},
}
# A role whose effort holds on whichever host it moves to (an explicit effort still wins): the improver runs at max on
# Codex and on Claude alike.
ROLE_EFFORT = {"improver": "max"}


def host(name: str, binary: str | None = None, backend: str | None = None) -> Host:
    """The host object for ``name``, optionally with a non-default binary and, for the Claude host, a backend."""
    cls = HOSTS[name]
    if backend not in (None, "anthropic") and "backends" not in vars(cls):
        raise SystemExit(f"--backend {backend} is a Claude host option; the {name} host has one backend")
    kwargs = {"backend": backend} if backend and "backends" in vars(cls) else {}
    return cls(binary, **kwargs) if binary else cls(**kwargs)

