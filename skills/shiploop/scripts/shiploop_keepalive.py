"""ShipLoop keepalive: host hooks and an outer driver that keep a run moving.

A host ends its turn whenever the model decides to.  These hooks ask ShipLoop
(``shiploop hook-status``) whether the run bound to the session can still move
and, while it can, refuse the stop and hand back the run's next command.

Two hook events per host:

* observe -- after a shell command.  When its output carries the packet's
  ``SHIPLOOP-RUN`` marker, bind this host session to that run.
* stop    -- when the host is about to end the turn.  Continue while the bound
  run is active and its revision moved since the last refusal; otherwise allow.

Several agents can touch one run: a parallel-chain worker, a second terminal,
consecutive driver sessions.  Only one session, the run's owner, is ever kept
alive.  The first session to bind a free run owns it; ownership is released when
the owner's turn ends normally, when the driver finishes a session, or after
OWNER_STALE_SECONDS without any activity from the owner.  Every read-modify-write
of a binding or owner record holds an exclusive file lock.

Every failure allows the stop: a broken hook must never trap a session.  The
driver (``shiploop-drive``) covers hosts whose headless mode cannot be kept
going from inside: it starts or resumes host sessions until the run is no
longer active.  Hermes is deliberately not a host here.
"""

from __future__ import annotations

import argparse
import contextlib
import fcntl
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Iterator, Mapping

SCRIPTS = Path(__file__).resolve().parent
SHIPLOOP = SCRIPTS / "shiploop"
HOOK = SCRIPTS / "shiploop-hook"
HOOKS_DIR = SCRIPTS.parent / "hooks"
HOSTS = ("claude", "grok", "codex", "cursor", "opencode")
# Plugin hooks ship one registration for every host that loads the plugin.
AUTO = "auto"

# Must match shiploop_navigator.KEEPALIVE_MARKER and the packet line format.
MARKER = re.compile(r"SHIPLOOP-RUN run=(?P<run_id>\S+) rev=(?P<rev>\d+) dir=(?P<dir>[^\r\n]+)")
SESSION_KEYS = ("session_id", "sessionId", "sessionID", "conversation_id")
# Two registrations of one host (say a plugin and settings) can fire for the
# same stop; within this window the second repeats the first decision.
DUPLICATE_WINDOW_SECONDS = 3.0
STATUS_TIMEOUT_SECONDS = 20
# An owner that has shown no hook activity for this long (a crashed or closed
# session) no longer blocks another session from taking the run over.
OWNER_STALE_SECONDS = 1800


# ---------------------------------------------------------------- state

def home() -> Path:
    override = os.environ.get("SHIPLOOP_KEEPALIVE_HOME")
    if override:
        return Path(override)
    base = os.environ.get("XDG_STATE_HOME") or str(Path.home() / ".local" / "state")
    return Path(base) / "shiploop" / "keepalive"


def disabled() -> bool:
    return os.environ.get("SHIPLOOP_KEEPALIVE", "").strip().lower() in ("off", "0", "false", "no")


def _binding_path(host: str, session: str) -> Path:
    digest = hashlib.sha256(session.encode()).hexdigest()[:32]
    return home() / "bindings" / f"{host}-{digest}.json"


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


@contextlib.contextmanager
def _locked(path: Path) -> Iterator[None]:
    """Exclusive advisory lock for one record's read-modify-write."""
    lock = path.with_name(path.name + ".lock")
    lock.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(lock, os.O_RDWR | os.O_CREAT, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def _owner_path(run_dir: str) -> Path:
    return home() / "runs" / (hashlib.sha256(run_dir.encode()).hexdigest()[:32] + ".json")


def _owner_id(host: str, session: str) -> str:
    return f"{host}:{session}"


def _load_owner(run_dir: str) -> dict:
    try:
        data = _read_json(_owner_path(run_dir))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def claim_owner(run_dir: str, host: str, session: str) -> bool:
    """Take a free or stale run, or refresh our own claim.  True when we own it."""
    path = _owner_path(run_dir)
    me = _owner_id(host, session)
    with _locked(path):
        owner = _load_owner(run_dir)
        now = time.time()
        if owner.get("owner") not in (None, me) and now - owner.get("seen", 0) < OWNER_STALE_SECONDS:
            return False
        _write_json(path, {"run_dir": run_dir, "owner": me, "seen": now})
        return True


def release_owner(run_dir: str, host: str | None = None, session: str | None = None) -> None:
    """Release the run; with a session given, only if that session owns it."""
    path = _owner_path(run_dir)
    with _locked(path):
        owner = _load_owner(run_dir)
        if session is None or owner.get("owner") == _owner_id(host or "", session):
            path.unlink(missing_ok=True)


def load_binding(host: str, session: str) -> dict | None:
    path = _binding_path(host, session)
    try:
        data = _read_json(path)
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) and data.get("session") == session else None


def bindings_for_run(host: str, run_dir: str) -> list[dict]:
    """Bindings of ``host`` sessions to ``run_dir``, most recently bound first."""
    found = []
    for path in (home() / "bindings").glob(f"{host}-*.json"):
        try:
            data = _read_json(path)
        except (OSError, ValueError):
            continue
        if isinstance(data, dict) and data.get("run_dir") == run_dir:
            found.append(data)
    return sorted(found, key=lambda item: item.get("bound_at", 0), reverse=True)


def run_status(run_dir: str) -> dict:
    """Ask ShipLoop about a run.  Never raises; an unanswerable run has ``error``."""
    try:
        proc = subprocess.run(
            [sys.executable, str(SHIPLOOP), "hook-status", "--run-dir", run_dir],
            capture_output=True, text=True, timeout=STATUS_TIMEOUT_SECONDS,
            stdin=subprocess.DEVNULL)
        answer = json.loads(proc.stdout.strip().splitlines()[-1])
    except (OSError, ValueError, IndexError, subprocess.TimeoutExpired) as exc:
        return {"run_dir": run_dir, "error": f"hook-status failed: {exc}"}
    return answer if isinstance(answer, dict) else {"run_dir": run_dir, "error": "hook-status gave no object"}


# ---------------------------------------------------------------- payloads

def session_of(payload: Mapping[str, Any]) -> str | None:
    for key in SESSION_KEYS:
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def detected_host(payload: Mapping[str, Any]) -> str | None:
    """Which host sent this payload, when its shape says so.

    Grok also runs Cursor's ~/.cursor/hooks.json and a project's
    .claude/settings.json, so one Grok event can reach another host's entry.
    """
    if "promptId" in payload or "hookEventName" in payload:
        return "grok"
    if "turn_id" in payload:
        return "codex"
    if "cursor_version" in payload or "generation_id" in payload:
        return "cursor"
    if "transcript_path" in payload and "prompt_id" in payload:
        return "claude"
    return None


def resolve_auto_host(payload: Mapping[str, Any]) -> str:
    """Host for a plugin hook, which every plugin-loading host runs unchanged.

    Grok and Cursor set their own plugin-root variables next to the
    CLAUDE_PLUGIN_ROOT alias; otherwise the payload shape decides.
    """
    if os.environ.get("GROK_PLUGIN_ROOT"):
        return "grok"
    if os.environ.get("CURSOR_PLUGIN_ROOT"):
        return "cursor"
    return detected_host(payload) or "claude"


def _strings(value: Any) -> Iterator[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, Mapping):
        for item in value.values():
            yield from _strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _strings(item)


# A ShipLoop command in the tool input names its run even when the model
# filtered the output and the packet's marker never reached the hook.
COMMAND_RUN_DIR = re.compile(r"\bshiploop\b[^\n|;&]*?--run-dir[= ]['\"]?([^\s'\"|;&]+)")


def command_run_dir(payload: Any) -> str | None:
    found = None
    for text in _strings(payload):
        for match in COMMAND_RUN_DIR.finditer(text):
            found = match[1]
    return found


def last_marker(payload: Any) -> dict | None:
    found = None
    for text in _strings(payload):
        for match in MARKER.finditer(text):
            found = {"run_id": match["run_id"], "rev": int(match["rev"]),
                     "run_dir": match["dir"].strip()}
    return found


# ---------------------------------------------------------------- hook events

def _is_subagent(payload: Mapping[str, Any]) -> bool:
    return any(payload.get(key) for key in ("subagentType", "agent_id", "agent_type"))


def observe(host: str, payload: Mapping[str, Any]) -> dict | None:
    """Bind the session to the run named by a marker in this tool output.

    Any tool call from a bound owner also refreshes its claim, so a long
    stage does not let another session take the run over.
    """
    session = session_of(payload)
    if session is None or _is_subagent(payload):
        # A subagent works for its parent; it never owns the parent's run.
        return None
    marker = last_marker(payload)
    if marker is None:
        run_dir = command_run_dir(payload)
        if run_dir is not None:
            status = run_status(run_dir)
            if not status.get("error") and status.get("run_id"):
                marker = {"run_id": status["run_id"], "run_dir": status["run_dir"]}
    if marker is None:
        existing = load_binding(host, session)
        if existing is not None:
            owner = _load_owner(existing["run_dir"])
            if owner.get("owner") == _owner_id(host, session):
                claim_owner(existing["run_dir"], host, session)
        return None
    status = run_status(marker["run_dir"])
    if status.get("error") or status.get("run_id") != marker["run_id"]:
        # Marker text copied from a log or file does not name a live run here.
        return None
    path = _binding_path(host, session)
    with _locked(path):
        previous = load_binding(host, session) or {}
        binding = {
            "host": host,
            "session": session,
            "run_dir": status["run_dir"],
            "run_id": status["run_id"],
            "bound_at": time.time(),
            "last_block_rev": (previous.get("last_block_rev")
                               if previous.get("run_id") == status["run_id"] else None),
        }
        _write_json(path, binding)
    claim_owner(status["run_dir"], host, session)
    return binding


# Hosts that force a turn to end after this many stop-hook continuations.
CONTINUATION_CAPS = {"grok": 8}
# From this many continuations before a cap, the reason asks harder not to stop.
CAP_WARNING_MARGIN = 2


def _continue_reason(status: Mapping[str, Any], host: str = "", turn_blocks: int = 0,
                     waiting: bool = False) -> str:
    text = (f"ShipLoop run {status['run_dir']} is still active at stage {status['stage']} "
            f"(revision {status['revision']}). Do not end the turn: run `{status['next']}` "
            "and follow the packet it prints. Only an explicit user stop or pause ends the run; "
            "then run the packet's pause command.")
    if waiting:
        text += (" A background task is still running: wait for it in this turn (poll its "
                 "output), then continue the packet; do not end the turn to wait.")
    cap = CONTINUATION_CAPS.get(host)
    if cap and turn_blocks >= cap - CAP_WARNING_MARGIN:
        text += (f" This is continuation {turn_blocks} of {host}'s {cap} per turn; the host ends "
                 "the turn after that. Do not end the turn to report progress: keep following "
                 "packets until the run is done or needs the user.")
    return text


def _turn_continued(payload: Mapping[str, Any]) -> bool:
    """True when this stop follows a stop-hook continuation within the same turn."""
    return bool(payload.get("stopHookActive") or payload.get("stop_hook_active"))


def _background_tasks(payload: Mapping[str, Any]) -> bool:
    tasks = payload.get("backgroundTasks") or payload.get("background_tasks")
    return bool(tasks)


def stop(host: str, payload: Mapping[str, Any]) -> dict:
    """Decide one stop.  Returns {"decision": "continue"|"allow", ...}."""
    if payload.get("reason") not in (None, "end_turn") or payload.get("subagentType"):
        # Grok's session-end stop and subagent stops never keep anything alive.
        return {"decision": "allow", "why": "not a turn end"}
    session = session_of(payload)
    if session is None:
        return {"decision": "allow", "why": "no session id"}
    path = _binding_path(host, session)
    with _locked(path):
        binding = load_binding(host, session)
        if binding is None:
            return {"decision": "allow", "why": "no run bound to this session"}
        last = binding.get("last_decision")
        if isinstance(last, dict) and time.time() - last.get("at", 0) < DUPLICATE_WINDOW_SECONDS:
            # A second registration of this host for the same stop.
            return {key: value for key, value in last.items() if key != "at"}
        if not _turn_continued(payload):
            binding["turn_blocks"] = 0
        decision = _decide(host, session, binding, waiting=_background_tasks(payload))
        if decision.pop("drop", False):
            path.unlink(missing_ok=True)
        else:
            binding["last_decision"] = {**decision, "at": time.time()}
            _write_json(path, binding)
    if decision["decision"] == "allow":
        # The owner's turn is over; another session may take the run.
        release_owner(binding["run_dir"], host, session)
    return decision


def _decide(host: str, session: str, binding: dict, *, waiting: bool = False) -> dict:
    status = run_status(binding["run_dir"])
    if status.get("error") or status.get("run_id") != binding["run_id"]:
        return {"decision": "allow", "drop": True,
                "why": f"run cannot be read: {status.get('error', 'run changed')}"}
    if status["status"] != "active":
        reason = status.get("status_reason")
        return {"decision": "allow", "drop": True,
                "why": f"run is {status['status']}" + (f": {reason}" if reason else "")}
    if not claim_owner(binding["run_dir"], host, session):
        return {"decision": "allow", "why": "another session owns this run",
                "notice": ("ShipLoop keepalive: another session owns this run, so this one is not "
                           "kept going. Continue the run from that session, or close it and run: "
                           + status["next"])}
    # Revision, callback attempts and Improve review passes all count as progress.
    progress = status.get("progress", str(status["revision"]))
    if binding.get("last_block_progress") == progress and not waiting:
        return {"decision": "allow", "why": "no progress",
                "notice": ("ShipLoop keepalive: the run made no progress since the last "
                           "continuation, so the turn may end. Resume with: " + status["next"])}
    binding["last_block_progress"] = progress
    binding["turn_blocks"] = int(binding.get("turn_blocks", 0)) + 1
    cap = CONTINUATION_CAPS.get(host)
    why = "run can move" + (" (background task running)" if waiting else "")
    why += f"; continuation {binding['turn_blocks']}" + (f"/{cap}" if cap else "")
    return {"decision": "continue", "why": why,
            "reason": _continue_reason(status, host, binding["turn_blocks"], waiting)}


def _log_decision(host: str, payload: Mapping[str, Any], decision: Mapping[str, Any]) -> None:
    """One line per stop decision, so "why did it stop?" has an answer."""
    session = session_of(payload) or ""
    record = {"at": time.time(), "host": host,
              "session": hashlib.sha256(session.encode()).hexdigest()[:12] if session else None,
              "decision": decision["decision"], "why": decision.get("why", "run can move")}
    try:
        path = home() / "decisions.log"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record) + "\n")
    except OSError:
        pass


def host_reply(host: str, decision: Mapping[str, Any]) -> dict | None:
    """Translate a decision into the host's own stop-hook output."""
    if decision["decision"] == "continue":
        if host in ("cursor", "opencode"):
            return {"followup_message": decision["reason"]}
        return {"decision": "block", "reason": decision["reason"]}
    if decision.get("notice") and host in ("claude", "grok", "codex"):
        return {"systemMessage": decision["notice"]}
    return None


def _log_error(event: str, host: str, exc: BaseException) -> None:
    try:
        path = home() / "errors.log"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({"at": time.time(), "event": event, "host": host,
                                     "error": repr(exc)}) + "\n")
    except OSError:
        pass


def run_hook(event: str, host: str, raw: str) -> str:
    """Handle one hook call; returns what to print (may be empty).  Never raises."""
    try:
        if disabled():
            return ""
        payload = json.loads(raw) if raw.strip() else {}
        if not isinstance(payload, dict):
            return ""
        sender = detected_host(payload)
        if host == AUTO:
            host = resolve_auto_host(payload)
        elif sender is not None and sender != host:
            # The sender's own registration handles this event.
            return ""
        if event == "observe":
            observe(host, payload)
            return ""
        decision = stop(host, payload)
        _log_decision(host, payload, decision)
        reply = host_reply(host, decision)
        return json.dumps(reply) if reply else ""
    except Exception as exc:  # noqa: BLE001 - fail open by contract
        _log_error(event, host, exc)
        return ""


# ---------------------------------------------------------------- install

OWNED_JS_HEADER = "// shiploop-keepalive: generated by shiploop-hook install; do not edit."


def _config_root() -> Path:
    return Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")


def hook_command(event: str, host: str) -> str:
    return shlex.join(["python3", str(HOOK), event, "--host", host])


def _is_owned_command(command: Any, host: str) -> bool:
    if not isinstance(command, str):
        return False
    try:
        argv = shlex.split(command)
    except ValueError:
        return False
    return (len(argv) >= 5 and Path(argv[1]).name == "shiploop-hook"
            and argv[-2:] == ["--host", host])


def _claude_style_entries(host: str) -> dict:
    matcher = {"matcher": "Bash"} if host == "claude" else {}
    return {
        "PostToolUse": {**matcher, "hooks": [{"type": "command", "command": hook_command("observe", host), "timeout": 30}]},
        "Stop": {"hooks": [{"type": "command", "command": hook_command("stop", host), "timeout": 30}]},
    }


def _cursor_entries() -> dict:
    return {
        "afterShellExecution": {"command": hook_command("observe", "cursor"), "timeout": 30},
        # ShipLoop's own no-progress rule ends loops; the host limit is a backstop.
        "stop": {"command": hook_command("stop", "cursor"), "timeout": 30, "loop_limit": 50},
    }


class InstallError(RuntimeError):
    """A config file exists but is not something this installer may edit."""


def _load_config(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        data = _read_json(path)
    except ValueError as exc:
        raise InstallError(f"{path} is not valid JSON ({exc}); left untouched") from exc
    if not isinstance(data, dict) or not isinstance(data.get("hooks", {}), dict):
        raise InstallError(f"{path} does not have the expected hooks object; left untouched")
    return data


def _entry_commands(entry: Any) -> list:
    if not isinstance(entry, dict):
        return []
    nested = entry.get("hooks")
    if isinstance(nested, list):
        return [item.get("command") for item in nested if isinstance(item, dict)]
    return [entry.get("command")]


def _merge(data: dict, host: str, wanted: Mapping[str, dict] | None) -> dict:
    """Remove this host's owned entries, then add ``wanted`` (None = uninstall)."""
    hooks = data.setdefault("hooks", {})
    for event in list(hooks):
        entries = hooks[event]
        if not isinstance(entries, list):
            continue
        kept = [entry for entry in entries
                if not any(_is_owned_command(command, host) for command in _entry_commands(entry))]
        if kept:
            hooks[event] = kept
        else:
            del hooks[event]
    for event, entry in (wanted or {}).items():
        hooks.setdefault(event, []).append(entry)
    if not hooks:
        del data["hooks"]
    return data


def config_path(host: str) -> Path:
    if host == "claude":
        return Path.home() / ".claude" / "settings.json"
    if host == "codex":
        return Path.home() / ".codex" / "hooks.json"
    if host == "cursor":
        return Path.home() / ".cursor" / "hooks.json"
    if host == "grok":
        return Path.home() / ".grok" / "hooks" / "shiploop-keepalive.json"
    if host == "opencode":
        return _config_root() / "opencode" / "plugins" / "shiploop-keepalive.js"
    raise InstallError(f"unknown host {host!r}")


def _opencode_plugin() -> str:
    template = (HOOKS_DIR / "opencode-keepalive.js").read_text(encoding="utf-8")
    return OWNED_JS_HEADER + "\n" + template.replace("__SHIPLOOP_HOOK__", json.dumps(str(HOOK)))


def _desired(host: str) -> Mapping[str, dict]:
    return _cursor_entries() if host == "cursor" else _claude_style_entries(host)


def status(host: str) -> str:
    """installed | stale | absent | foreign"""
    path = config_path(host)
    if host == "opencode":
        if not path.exists():
            return "absent"
        text = path.read_text(encoding="utf-8")
        if not text.startswith(OWNED_JS_HEADER):
            return "foreign"
        return "installed" if text == _opencode_plugin() else "stale"
    try:
        data = _load_config(path)
    except InstallError:
        return "foreign"
    owned = [command for entries in data.get("hooks", {}).values() if isinstance(entries, list)
             for entry in entries for command in _entry_commands(entry)
             if _is_owned_command(command, host)]
    if not owned:
        return "absent"
    wanted = {command for entry in _desired(host).values() for command in _entry_commands(entry)}
    return "installed" if set(owned) == wanted else "stale"


def install(host: str, *, remove: bool = False, dry_run: bool = False) -> str:
    """Install (or remove) this host's hooks; returns a one-line report."""
    path = config_path(host)
    verb = "remove" if remove else "install"
    if host == "opencode":
        current = status(host)
        if current == "foreign":
            raise InstallError(f"{path} exists and was not written by shiploop-hook; left untouched")
        if remove:
            if current == "absent":
                return f"opencode: nothing to remove at {path}"
            if not dry_run:
                path.unlink()
            return f"opencode: {'would remove' if dry_run else 'removed'} {path}"
        if not dry_run:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(_opencode_plugin(), encoding="utf-8")
        return f"opencode: {'would write' if dry_run else 'wrote'} {path}"
    data = _load_config(path)
    if host == "cursor" and not remove:
        data.setdefault("version", 1)
    updated = _merge(json.loads(json.dumps(data)), host, None if remove else _desired(host))
    if updated == data:
        return f"{host}: {path} already {'clean' if remove else 'up to date'}"
    if not dry_run:
        # A hooks file left holding nothing but a version stamp is removed;
        # Claude's settings.json carries other settings and always stays.
        if host != "claude" and not set(updated) - {"version"}:
            path.unlink(missing_ok=True)
        else:
            _write_json(path, updated)
    done = {"install": ("would add ShipLoop hooks to", "added ShipLoop hooks to"),
            "remove": ("would remove ShipLoop hooks from", "removed ShipLoop hooks from")}[verb]
    return f"{host}: {done[0] if dry_run else done[1]} {path}"


# Hosts that never run a plugin's hooks, keyed to the variable the host sets
# in every shell command it runs.  Grok 1.0.41 lists the ShipLoop plugin's
# hooks but never dispatches them (headless or interactive, trusted or not),
# so ShipLoop installs its global hooks there the first time it runs.
SELF_INSTALL = {"grok": "GROK_AGENT"}


def _script_free(command: str) -> str:
    """An owned command with its shiploop-hook path left out."""
    argv = shlex.split(command)
    return shlex.join(argv[:1] + argv[2:])


def _working_copy(host: str) -> bool:
    """True when this host's owned hooks are the wanted set from any existing ShipLoop copy.

    A host can load ShipLoop from more than one installed copy; a hook that
    already runs a present copy is left alone rather than rewritten each time
    another copy runs.
    """
    data = _load_config(config_path(host))
    owned = [command for entries in data.get("hooks", {}).values() if isinstance(entries, list)
             for entry in entries for command in _entry_commands(entry)
             if _is_owned_command(command, host)]
    wanted = {_script_free(command) for entry in _desired(host).values()
              for command in _entry_commands(entry)}
    return ({_script_free(command) for command in owned} == wanted
            and all(Path(shlex.split(command)[1]).is_file() for command in owned))


def ensure_hooks(env: Mapping[str, str] | None = None) -> str | None:
    """Install or repair the calling host's global hooks when its plugin hooks never run.

    Returns a one-line notice when it wrote a file, else None.  Never raises:
    keepalive is optional, and a failure here must not block ShipLoop.
    """
    env = os.environ if env is None else env
    if disabled():
        return None
    for host, variable in SELF_INSTALL.items():
        if env.get(variable) != "1":
            continue
        try:
            current = status(host)
            if current in ("installed", "foreign") or (current == "stale" and _working_copy(host)):
                return None
            install(host)
        except (InstallError, OSError, ValueError):
            return None
        verb = "installed" if current == "absent" else "updated"
        return (f"ShipLoop keepalive: {verb} the {host} hooks in {config_path(host)} ({host} does not "
                f"run plugin hooks). New {host} sessions load them; in this session open /hooks and press r.")
    return None


TRUST_NOTES = {
    "codex": "Codex asks you to trust new hooks once; approve the ShipLoop entries when prompted.",
    "cursor": "Cursor's stop hook does not fire in `cursor-agent -p`; use shiploop-drive for unattended runs.",
    "opencode": "`opencode run` exits before a plugin's follow-up is answered; use shiploop-drive for unattended runs.",
}


# ---------------------------------------------------------------- driver

RESUMING_HOSTS = ("cursor", "opencode")
EXIT_DONE, EXIT_NEEDS_USER, EXIT_STUCK, EXIT_CAP = 0, 3, 4, 5


def _driver_prompt(status: Mapping[str, Any]) -> str:
    return (f"Continue the ShipLoop run in {status['run_dir']}: run `{status['next']}` and follow "
            "the packet it prints. Keep going until the packet reports the run done, paused or "
            "blocked; progress reports are not a reason to stop.")


def host_argv(host: str, prompt: str, session: str | None, extra: list[str]) -> list[str]:
    if host == "claude":
        return ["claude", "-p", prompt, *extra]
    if host == "grok":
        return ["grok", "-p", prompt, *extra]
    if host == "codex":
        return ["codex", "exec", *extra, prompt]
    if host == "cursor":
        return ["cursor-agent", "-p", *(["--resume", session] if session else []), *extra, prompt]
    if host == "opencode":
        return ["opencode", "run", *(["--session", session] if session else []), *extra, prompt]
    raise ValueError(f"unknown host {host!r}")


def drive(host: str, run_dir: str, *, max_sessions: int, session_timeout: int,
          extra: list[str], cwd: str | None, out=print, runner=subprocess.run) -> int:
    """Start or resume host sessions until the run stops being active."""
    status = run_status(run_dir)
    if status.get("error"):
        out(f"shiploop-drive: cannot read the run: {status['error']}")
        return EXIT_NEEDS_USER
    run_dir = status["run_dir"]
    logs = home() / "drive" / status["run_id"]
    logs.mkdir(parents=True, exist_ok=True)
    journal = logs / "drive.log"
    # One driver per run: a second one would start competing host sessions.
    lock_fd = os.open(logs / "driver.lock", os.O_RDWR | os.O_CREAT, 0o600)
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        os.close(lock_fd)
        out(f"shiploop-drive: another shiploop-drive is already running this run ({run_dir}).")
        return EXIT_NEEDS_USER
    try:
        return _drive_sessions(host, run_dir, logs, journal, max_sessions=max_sessions,
                               session_timeout=session_timeout, extra=extra, cwd=cwd,
                               out=out, runner=runner)
    finally:
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        os.close(lock_fd)


def _drive_sessions(host: str, run_dir: str, logs: Path, journal: Path, *, max_sessions: int,
                    session_timeout: int, extra: list[str], cwd: str | None, out, runner) -> int:
    stalled = 0
    for number in range(1, max_sessions + 1):
        before = run_status(run_dir)
        if before.get("error"):
            out(f"shiploop-drive: cannot read the run: {before['error']}")
            return EXIT_NEEDS_USER
        if before["status"] != "active":
            out(f"shiploop-drive: run is {before['status']} after {number - 1} session(s).")
            return EXIT_DONE if before["status"] == "done" else EXIT_NEEDS_USER
        session = None
        if host in RESUMING_HOSTS:
            bound = bindings_for_run(host, run_dir)
            session = bound[0]["session"] if bound else None
        argv = host_argv(host, _driver_prompt(before), session, extra)
        started = time.time()
        try:
            proc = runner(argv, cwd=cwd or before.get("repo") or None, capture_output=True,
                          text=True, timeout=session_timeout, stdin=subprocess.DEVNULL)
            code, stdout, stderr = proc.returncode, proc.stdout or "", proc.stderr or ""
        except subprocess.TimeoutExpired as exc:
            code, stdout, stderr = "timeout", str(exc.stdout or ""), str(exc.stderr or "")
        except OSError as exc:
            out(f"shiploop-drive: cannot start {argv[0]}: {exc}")
            return EXIT_NEEDS_USER
        # The session is over however it ended; let the next one own the run.
        release_owner(run_dir)
        session_log = logs / f"session-{number}.log"
        session_log.write_text(f"$ {shlex.join(argv)}\n{stdout}\n--- stderr ---\n{stderr}", encoding="utf-8")
        after = run_status(run_dir)
        moved = not after.get("error") and after["revision"] != before["revision"]
        entry = {"session": number, "host": host, "resumed": session, "exit": code,
                 "seconds": round(time.time() - started), "revision": [before["revision"], after.get("revision")],
                 "status": after.get("status"), "log": str(session_log)}
        with journal.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry) + "\n")
        out("shiploop-drive: " + json.dumps(entry))
        if not moved and code not in (0, "timeout"):
            out(f"shiploop-drive: {host} exited with {code} without advancing the run; "
                f"it may have failed to start. See {session_log}")
            return EXIT_STUCK
        stalled = 0 if moved else stalled + 1
        if stalled >= 2:
            out(f"shiploop-drive: two sessions in a row made no progress; stopping. See {journal}")
            return EXIT_STUCK
    out(f"shiploop-drive: reached --max-sessions {max_sessions}; the run is still active.")
    return EXIT_CAP


# ---------------------------------------------------------------- CLIs

def hook_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="shiploop-hook",
        description="Keep a ShipLoop run moving across host turns (see references/keepalive.md).")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("observe", "stop"):
        event = sub.add_parser(name, help=f"host hook event: {name} (reads the payload on stdin)")
        event.add_argument("--host", choices=(*HOSTS, AUTO), required=True)
    for name in ("install", "uninstall", "status"):
        action = sub.add_parser(name, help=f"{name} the keepalive hooks for hosts")
        action.add_argument("--host", choices=HOSTS, action="append", required=True)
        if name != "status":
            action.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    if args.command in ("observe", "stop"):
        reply = run_hook(args.command, args.host, sys.stdin.read())
        if reply:
            print(reply)
        return 0
    worst = 0
    for host in args.host:
        try:
            if args.command == "status":
                print(f"{host}: {status(host)} ({config_path(host)})")
                continue
            print(install(host, remove=args.command == "uninstall", dry_run=args.dry_run))
            if args.command == "install" and host in TRUST_NOTES:
                print(f"  note: {TRUST_NOTES[host]}")
        except InstallError as exc:
            print(f"{host}: refused: {exc}", file=sys.stderr)
            worst = 3
    return worst


def drive_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="shiploop-drive",
        description="Run host sessions until a ShipLoop run is done, paused, blocked or stuck. "
                    "Arguments after -- go to the host command unchanged (model, permissions).")
    parser.add_argument("--host", choices=HOSTS, required=True)
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--max-sessions", type=int, default=20)
    parser.add_argument("--session-timeout", type=int, default=3600, help="seconds per host session")
    parser.add_argument("--cwd", help="directory to run the host in (default: the run's repository)")
    raw = list(sys.argv[1:] if argv is None else argv)
    extra: list[str] = []
    if "--" in raw:
        split = raw.index("--")
        raw, extra = raw[:split], raw[split + 1:]
    args = parser.parse_args(raw)
    return drive(args.host, str(Path(args.run_dir).expanduser().resolve()),
                 max_sessions=args.max_sessions, session_timeout=args.session_timeout,
                 extra=extra, cwd=args.cwd)
