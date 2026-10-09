"""Where a ShipLoop E2E run spent its turns, tokens and time.

Reads the output directory the runner wrote: the host event stream
(events.jsonl), its arrival times (timeline.jsonl, one line per non-streaming
event: {"line": n, "t": epoch}) and the ShipLoop run directory. Grok events
carry no timestamps, so stage attribution uses the times the runner stamped
and the times ShipLoop wrote each accepted stage result.

Never returns packet text: ShipLoop CLI output is reduced to the failing line.
"""

from __future__ import annotations

import bisect
from datetime import datetime, timezone
import itertools
import json
import os
from pathlib import Path
import re

import rollouts
import runrecord
import sessionlog

SHIPLOOP_COMMAND = re.compile(r"shiploop\S*\s+(?P<verb>complete|next|improve-[\w-]+|init|workspace|lint|resume|pause)\b")
# Model-written glue (SPEC S-4, S-5): shell commands that do a mechanical step
# ShipLoop owns. Defined by ShipLoop's own paths and verbs, never by product
# tools, so it means the same thing for every case. A heuristic signal: the
# matching commands are listed so a reviewer can confirm them.
# ShipLoop-owned: its run directory, Improve receipts and its own record files.
# The execution worktree under a workspace root is product space, not ShipLoop's.
SHIPLOOP_OWNED = re.compile(r"(?:\.shiploop-improve|/\.shiploop(?:/|[\"'\s]|$)|\.shiploop-runs/[^/\s\"']+/run\b|"
                            r"/run/(?:state\.md|results|packets|tests|quality)|until-loop|"
                            r"/(?:packet|start)\.json\b|/parent-return\.md\b|-terminal\.json\b)")
# Host tools that put a question to a person (Grok ask_user_question, Claude AskUserQuestion).
ASK_PERSON = re.compile(r"ask_?user", re.I)
# Files the packets ask the model itself to write (its result, evidence notes, Improve
# review evidence, an Improve opening or commit message): writing them is the step, not glue.
# A write to a literal /tmp path (redirect, tee, cp or mv target): shared with every other run (plan P13).
TMP_WRITE = re.compile(r"(?:>>?|\btee\s+(?:-a\s+)?|\b(?:cp|mv)\s+(?:-\S+\s+)*\S+\s+)\s*[\"']?(/tmp/[^\s\"';|&)]+)")


WRITE_TOOL = re.compile(r"write|edit|replace|create", re.I)


def tmp_writes(command: str) -> list[str]:
    """The literal /tmp paths a shell command writes (heredoc bodies are documents, not commands)."""
    return TMP_WRITE.findall(shell_text(command))


MODEL_INPUT = re.compile(r"/inbox/|/run/(?:notes|evidence|scratch)(?:/|$|[\"'\s])|/reviews(?:/|$|[\"'\s])|opening\.md|"
                         r"commit-message\.md|\.shiploop-improve/[^/\s\"']+/nav-[0-9a-f]+/?(?:[\"'\s]|$)")
# `git ... commit|add` as a command: at the start of a line or after ; && || |, optionally after VAR=value.
GLUE_COMMIT = re.compile(r"(?:^|[;&|]\s*)(?:\w+=\S*\s+)*git\b[^\n;&|]*\s(?:commit|add)\b", re.M)
# A redirect needs a path-like target (a slash, dot, $ or ~), so a `>` in prose inside a quoted string ("... > 0 must ...") is not a write.
GLUE_WRITE = re.compile(r"(?:>>?(?=\s+[\"']?[^\s\"']*[/.$~])|\btee\b|\bcp\b|\bmv\b|\bmkdir\b|\brm\b)\s+[^\n;&|]*")
GLUE_CONTRACT = re.compile(r"exit_condition|repeat_condition|required_trivial_reviews")
# Reading ShipLoop's contract is fine; writing one, or feeding one to the Until Loop runtime, is glue.
CONTRACT_WRITE = re.compile(r"json\.dump\(|write_text|open\([^)]*['\"][wa]|[^-<>=]>\s*[^\s=&]|until[-_]loop")


HEREDOC = re.compile(r"<<-?\s*['\"]?(\w+)['\"]?[^\n]*\n.*?\n\s*\1\s*(?:\n|$)", re.S)


def shell_text(command: str) -> str:
    """The command with heredoc bodies removed: words inside a document are not commands."""
    return HEREDOC.sub("\n", command)


def glue_reasons(command: str) -> list[str]:
    """Why a shell command counts as model-written glue ([] when it does not)."""
    reasons = []
    shell = shell_text(command)
    if GLUE_COMMIT.search(shell):
        reasons.append("git commit/add by the model")
    if any(SHIPLOOP_OWNED.search(m.group(0)) and not MODEL_INPUT.search(m.group(0))
           for m in GLUE_WRITE.finditer(shell)):
        reasons.append("shell write into a ShipLoop-owned path")
    if GLUE_CONTRACT.search(command) and CONTRACT_WRITE.search(command):
        reasons.append("hand-built loop contract")
    return reasons


# Shell variables a command assigns before it uses them (Claude's multi-line commands: `RUN=...`, `CLI="$SKILL_ROOT/scripts/shiploop"`).
# Read per command: no recorded run carried a variable from one tool call to the next. An assignment at a line start or after a
# `;` counts; a heredoc body is a document, not a command. Single-quoted, double-quoted and bare values, no command substitution.
ASSIGNMENT = re.compile(r"""(?:^|;[ \t]*)(?:export\s+)?([A-Za-z_]\w*)=(?:"([^"\n]*)"|'([^'\n]*)'|([^\s;&|<>()`"']*))[ \t]*(?=;|$)""",
                        re.M)
SHELL_VARIABLE = re.compile(r"\$(?:\{(\w+)\}|(\w+))")
# A path segment and the `..` that undoes it: `<dir>/run/../worktree` is `<dir>/worktree`, the product worktree beside the run
# directory, which SHIPLOOP_OWNED must not match through the run directory's prefix. A leading `..` has no segment to drop.
PARENT_STEP = re.compile(r"/(?!\.\.?(?=[/\s\"'`;&|<>()]|$))[^/\s\"'`;&|<>()=$]+/\.\.(?=[/\s\"'`;&|<>()]|$)")


def expand_variables(text: str, known: dict[str, str]) -> str:
    """The text with each `$NAME` and `${NAME}` that ``known`` assigns replaced, and each `/segment/..` that leaves behind
    removed; any other variable is left as written."""
    text = SHELL_VARIABLE.sub(lambda m: known.get(m.group(1) or m.group(2), m.group(0)), text)
    while (shorter := PARENT_STEP.sub("", text)) != text:
        text = shorter
    return text


def shell_variables(command: str, known: dict[str, str] | None = None) -> dict[str, str]:
    """The variables a command assigns, each value resolved against the ones assigned before it (``known`` first).

    An assignment whose value is still not plain text after expansion (`$?`, `$!`, `$(...)`, a variable not assigned) is
    not recorded, so `sh -c '...; R=$?; ...'` quoted inside a command cannot replace the `R=<run directory>` before it.
    """
    found = dict(known or {})
    for m in ASSIGNMENT.finditer(shell_text(command)):
        value = expand_variables(next(g for g in m.groups()[1:] if g is not None), found)
        if "$" not in value:
            found[m.group(1)] = value
    return found


FAILURE_LINE = re.compile(r"error|refus|reject|required|must|invalid", re.I)
MARKER = re.compile(r"SHIPLOOP-RUN")
# What a refused ShipLoop command prints (shiploop_protocol.py): the refusal's own line, which begins with one of
# these prefixes and often has none of FAILURE_LINE's words ("result requires outcome and summary"), then fixed
# trailer lines the script adds to every refusal. A trailer says "rejected", so matching it first named no refusal
# (8 of the 13 refusals of the Luna 1.16.1 run); the script's text is pinned by test/shiploop-e2e.test.py.
# The same line is what makes a tool result a failure on every host, whatever exit code the host showed: the model pipes
# the CLI through head, grep or sed, which hides the exit (all 5 refusals of the round-1 Sonnet Battleship run).
REFUSAL_LINE = re.compile(r"^ShipLoop (?:navigator|blocked|workspace blocked): ", re.M)
TRAILER_LINE = re.compile(r"^(?:Read the current packet with next; |The run is still active: fix the result and |"
                          r"Request failure: no in-memory result|Durable cursor recovery: )")


def failure_line(shown: str) -> str:
    """The line that names why a ShipLoop command was refused: its own, not the script's fixed trailer.

    Where no line but a trailer matches, the first trailer match is kept (what this recorded before).
    """
    lines = [ln for ln in shown.splitlines() if not MARKER.search(ln)]
    own = next((ln for ln in lines if (FAILURE_LINE.search(ln) or REFUSAL_LINE.search(ln))
                and not TRAILER_LINE.search(ln)), None)
    if own is None:
        own = next((ln for ln in lines if FAILURE_LINE.search(ln)), "")
    return own.strip()[:200]


def event_range(path: Path, start: int = 0, stop: int | None = None):
    """(line number, event) for every JSON object line in [start, stop): a line before ``start`` is counted, not parsed."""
    if not path.is_file():
        return
    with path.open(errors="replace") as handle:
        for number, line in enumerate(handle):
            if number < start:
                continue
            if stop is not None and number >= stop:
                return
            try:
                event = json.loads(line)
            except ValueError:
                continue
            if isinstance(event, dict):
                yield number, event


def events(path: Path):
    """(line number, event) for every JSON object line."""
    yield from event_range(path)


def timeline(path: Path) -> dict[int, float]:
    stamps: dict[int, float] = {}
    if path.is_file():
        for line in path.read_text(errors="replace").splitlines():
            try:
                item = json.loads(line)
                stamps[int(item["line"])] = float(item["t"])
            except (ValueError, KeyError, TypeError):
                continue
    return stamps


def visible(raw) -> str:
    if isinstance(raw, str):
        return raw
    if isinstance(raw, dict):
        for key in ("output_for_prompt", "content", "text"):
            if isinstance(raw.get(key), str):
                return raw[key]
    return ""


def tool_results(event: dict):
    """(tool call id, text) of each tool result in one event, for Claude (a `user` event's tool_result blocks) and Grok."""
    if event.get("type") == "tool_call_update" and isinstance(event.get("rawOutput"), dict):
        yield event.get("toolCallId"), visible(event["rawOutput"])
    elif event.get("type") == "user":
        for block in (event.get("message") or {}).get("content") or []:
            if isinstance(block, dict) and block.get("type") == "tool_result":
                content = block.get("content")
                if isinstance(content, list):
                    content = "".join(str(part.get("text") or "") for part in content if isinstance(part, dict))
                yield block.get("tool_use_id"), str(content or "")


def claude_exit(shown: str) -> int | None:
    """The exit code Claude's Bash result begins with (`Exit code 2`), or None: the host shows none for an exit of 0."""
    found = re.match(r"Exit code (\d+)", shown)
    return int(found.group(1)) if found else None


def failure_text(failure: dict) -> str:
    """One recorded failure's exit for a printed line; a refusal behind a pipe has none, because the host showed none."""
    return "exit not shown" if failure.get("exit") is None else f"exit {failure['exit']}"


# A file a command writes with a heredoc (`cat > PATH <<'EOF' ... EOF`, `tee PATH <<EOF`): the body is the real file.
WRITTEN_FILE = re.compile(r"(?:\bcat\s*>>?|\btee(?:\s+-a)?)\s*(?P<path>[^\s<>|;&]+)\s*<<-?\s*['\"]?(?P<tag>\w+)['\"]?[^\n]*\n"
                          r"(?P<body>.*?)\n[ \t]*(?P=tag)[ \t]*(?:\n|$)", re.S)
# A script the model wrote that ShipLoop's own run directory keeps (its scratch folder), or that calls the ShipLoop CLI.
MODEL_SCRIPT_HOME = "/run/scratch/"


def written_scripts(command: str, known: dict[str, str]) -> list[dict]:
    """The model-written scripts a command creates with a heredoc: {path, body, wraps, bytes}, variables expanded.

    A file counts when it lives in the run's scratch folder or its body calls the ShipLoop CLI (a verb after the script's
    own `shiploop`, or the CLI's `scripts/shiploop` path): the product files a heredoc writes are not scripts here, and a
    path that still holds a variable after expansion cannot be matched to a later call, so it is left out. ``bytes`` is
    the size of the body as written.
    """
    found = []
    for m in WRITTEN_FILE.finditer(command):
        path = expand_variables(m.group("path").strip("\"'"), known)
        body = expand_variables(m.group("body"), shell_variables(m.group("body"), known))
        wraps = bool(SHIPLOOP_COMMAND.search(body)) or "scripts/shiploop" in body
        if "$" not in path and (MODEL_SCRIPT_HOME in path or wraps):
            found.append({"path": path, "body": body, "wraps": wraps, "bytes": len(m.group("body").encode())})
    return found


def invocation(path: str):
    """A pattern for a command line that runs the script at ``path``: it stands where a command does (a line start, after
    `;`, `&`, `|`, `(`, `then` or `do`, behind VAR=value words) or right after an interpreter. A path that is an
    argument (`ls -l PATH`, `--result=PATH`) is not a run."""
    return re.compile(r"(?:^|[;&|(`]|\$\(|\b(?:then|do|else)\b|\b(?:python3?|bash|sh|zsh|node)[ \t]+(?:-\S+[ \t]+)*)"
                      r"[ \t]*(?:\w+=\S*[ \t]+)*[\"']?" + re.escape(path) + r"(?=[\s;&|)\"'`]|$)", re.M)


def plural(count: int, noun: str) -> str:
    return f"{count} {noun}{'' if count == 1 else 's'}"


def call_target(arg: dict) -> str:
    """The file a tool call names (Grok `target_file`, Claude `file_path`, a bare `path`), or an empty string."""
    return str(arg.get("target_file") or arg.get("file_path") or arg.get("path") or "")


def tool_call_events(event: dict) -> list[tuple]:
    """``(call id, tool name, input)`` of each tool call one event starts, whatever host wrote it.

    Claude writes one `assistant` event per content block of a message, so an event holds the `tool_use` blocks of
    that block's message (none for a text block); Grok, and Codex after the harness translator, write one `tool_call`
    event per call. The one reader: ``ToolLog.feed`` and so the whole-run reading and a window read calls this way.
    """
    kind = event.get("type")
    if kind == "assistant":
        return [(block.get("id"), str(block.get("name") or ""), block["input"] if isinstance(block.get("input"), dict) else {})
                for block in (event.get("message") or {}).get("content") or []
                if isinstance(block, dict) and block.get("type") == "tool_use"]
    if kind == "tool_call":
        return [(event.get("toolCallId"), str(event.get("toolName") or event.get("title") or ""),
                 event.get("rawInput") if isinstance(event.get("rawInput"), dict) else {})]
    return []


def cancelled_update(event: dict) -> bool:
    """Grok's headless permission check refused the call: a failed update whose content says the user cancelled it."""
    return (event.get("type") == "tool_call_update" and event.get("status") == "failed"
            and "cancelled" in json.dumps(event.get("content") or "").lower())


class ToolLog:
    """The tool calls of one host stream and what each returned, classified once for every host: Grok's `tool_call` and
    `tool_call_update` events, Codex's after the harness translator, and Claude's `tool_use` and `tool_result` blocks.

    A ShipLoop failure is one tool result, counted once, in either of two cases. Its text has a line that begins with a
    refusal prefix (REFUSAL_LINE), whatever exit code the host showed or hid: the model pipes the CLI through head, grep
    or sed. Or the host showed a nonzero exit and the command names a ShipLoop verb, directly or through a script the
    model wrote earlier whose body does. The verb is read from the command alone, else it is `unknown`. Both arms are
    heuristics: a line of a document that begins with a prefix would count, a compound command's exit is attributed to
    the ShipLoop call in it, a looping command counts once, and a result the host saved to a file is not read.
    """

    def __init__(self) -> None:
        self.calls: dict = {}  # call id -> {"t", "command" as written, "expanded", "invoked": expanded + wrapper bodies}
        self.shared: set[str] = set()  # literal /tmp paths written (plan P13)
        self.glue: list[dict] = []
        self.asked: list[str] = []
        self.reads: list[str] = []
        self.failures: list[dict] = []
        self.failed: set = set()  # call ids already counted: Grok repeats an update for one call, which is a failure once
        self.failure_of: dict = {}  # call id -> its entry in ``failures``, so a window can count the failures of its own calls
        self.answered: set = set()  # call ids whose final result arrived: a failure is known only once the result is
        self.scripts: dict[str, dict] = {}  # path -> {body, wraps, bytes, runs, pattern}: the model-written scripts so far
        self.by_tool: dict[str, int] = {}  # Claude only below: what the model called, what came back, how it used packets
        self.result_chars = 0
        self.packets = {"printed": [0, 0], "shell": [0, 0], "read_tool": []}

    def call(self, t, call_id, tool: str, arg: dict):
        """One tool call: a question put to a person, glue, a /tmp write, a path read or written, a script written.
        Returns the key it is kept under in ``calls`` (the call id, or a number for a call that had none)."""
        self.failed.discard(call_id)  # Codex numbers its calls again in each session: a reused id is a new call
        self.failure_of.pop(call_id, None)
        self.answered.discard(call_id)
        if ASK_PERSON.search(tool):  # SPEC S-14: an unattended run never asks a person
            self.asked.append(" ".join(str(arg.get("question") or arg or "").split())[:160])
        command = str(arg.get("command") or "")
        known = shell_variables(command) if command else {}
        expanded = expand_variables(command, known)
        for found in written_scripts(command, known):
            script = self.scripts.setdefault(found["path"], {"runs": 0})
            script.update(body=found["body"], wraps=found["wraps"], bytes=found["bytes"], pattern=invocation(found["path"]))
        wrappers = "".join("\n" + script["body"] for path, script in self.scripts.items() if path in expanded)
        shell = shell_text(expanded)
        for script in self.scripts.values():  # a run is a tool call that runs the script, however many lines do
            script["runs"] += bool(script["pattern"].search(shell))
        target = call_target(arg)
        self.by_tool[tool] = self.by_tool.get(tool, 0) + 1
        key = call_id if call_id is not None else f"#{len(self.calls)}"
        self.calls[key] = {
            "t": t, "command": command, "expanded": expanded, "invoked": expanded + wrappers, "tool": tool,
            "packet": "/packets/" in expanded or "/packets/" in str(target or ""),
            "whole": "offset" not in arg and "limit" not in arg, "file": str(target or "")}
        if command:
            reasons = glue_reasons(expanded)
            self.shared.update(tmp_writes(expanded))
            if reasons:
                self.glue.append({"reasons": reasons, "command": " ".join(command.split())[:200]})
        if target:
            self.reads.append(str(target))
            if WRITE_TOOL.search(tool) and str(target).startswith("/tmp/"):
                self.shared.add(str(target))
        return key

    def measure(self, call_id, shown: str) -> None:
        """What one tool result held, for a stream whose results arrive once and whole (Claude's): characters, and how the
        model met the packets: a printed head (a ShipLoop reply shown by a call that does not name a packet file), a Read
        of a packet file, or a shell command that names one."""
        call = self.calls.get(call_id) or {}
        self.result_chars += len(shown)
        if call.get("packet") and call.get("tool") == "Read":
            self.packets["read_tool"].append({"packet": Path(call["file"]).stem, "whole": call["whole"], "chars": len(shown)})
        elif call.get("packet") and call.get("command"):
            self.packets["shell"][0] += 1
            self.packets["shell"][1] += len(shown)
        elif PACKET_STAGE.search(shown):
            self.packets["printed"][0] += 1
            self.packets["printed"][1] += len(shown)

    def tool_use(self, run_dir: Path | None) -> dict:
        """The record-only `tool_use` block of a Claude run (main thread): calls, results, scripts and packets.

        ``scratch_scripts`` are the model-written scripts that were run, with the number of tool calls that ran each;
        ``packets.on_disk`` is what the run directory holds, None when it has no packets folder.
        """
        folder = run_dir / "packets" if run_dir else None
        files = [p for p in sorted(folder.glob("*.md")) if p.is_file()] if folder and folder.is_dir() else None
        return {"calls": sum(self.by_tool.values()), "by_tool": dict(sorted(self.by_tool.items())),
                "result_chars": self.result_chars,
                "scratch_scripts": [{"path": path, "bytes": s["bytes"], "wraps_shiploop": s["wraps"], "runs": s["runs"]}
                                    for path, s in sorted(self.scripts.items()) if s["runs"]],
                "packets": {"on_disk": None if files is None else {"files": len(files), "bytes": sum(p.stat().st_size for p in files)},
                            "printed": dict(zip(("replies", "chars"), self.packets["printed"])),
                            "read": {"read_tool": self.packets["read_tool"],
                                     "shell": dict(zip(("calls", "chars"), self.packets["shell"]))}}}

    def feed(self, event: dict, t) -> list:
        """One host event, read the one way for every host: the calls it starts and the results it carries.

        Claude's `tool_use` blocks, Grok's `tool_call` events and Codex's after the translator start calls; Claude's
        `tool_result` blocks and Grok's final `tool_call_update` carry results. A running update (Grok repeats one, with a
        placeholder exit 0) and a cancelled one (a permission refusal, which ends the turn) are no result. The whole-run
        reading (``collect``) and a window (``reorientation``) both feed a log this way, so they cannot differ. Returns the
        keys, in ``calls``, of the calls this event started.
        """
        started = [self.call(t, call_id, tool, arg) for call_id, tool, arg in tool_call_events(event)]
        kind = event.get("type")
        if kind == "user":  # Claude: the tool_result blocks, whose text may begin with the host's `Exit code N`
            for call_id, shown in tool_results(event):
                self.measure(call_id, shown)
                self.result(call_id, shown, claude_exit(shown))
        elif kind == "tool_call_update" and isinstance(event.get("rawOutput"), dict) and not cancelled_update(event) \
                and event.get("status") != "in_progress":
            for call_id, shown in tool_results(event):
                self.result(call_id, shown, event["rawOutput"].get("exit_code"))
        return started

    def result(self, call_id, shown: str, code: int | None) -> None:
        """One tool result, with the exit code the host showed (None when it showed none)."""
        self.answered.add(call_id)
        refusal = REFUSAL_LINE.search(shown)
        call = self.calls.get(call_id) or {}
        exited = code not in (None, 0) and SHIPLOOP_COMMAND.search(call.get("invoked", ""))
        if call_id in self.failed or not (refusal or exited):
            return
        self.failed.add(call_id)
        verb = SHIPLOOP_COMMAND.search(call.get("expanded", ""))
        # From the refusal's own line on: the model's shell errors before it are not why ShipLoop refused.
        self.failures.append({"verb": verb.group("verb") if verb else "unknown", "exit": code,
                              "line": failure_line(shown[refusal.start():] if refusal else shown)})
        self.failure_of[call_id] = self.failures[-1]


def engine_state(run_dir: Path | None) -> dict:
    """ShipLoop's own state.md record, or an empty mapping."""
    if run_dir is None or not (run_dir / "state.md").is_file():
        return {}
    found = STATE_BLOCK.search((run_dir / "state.md").read_text(errors="replace"))
    if not found:
        return {}
    try:
        value = json.loads(found.group("json"))
    except ValueError:
        return {}
    return value if isinstance(value, dict) else {}


def engine_position(run_dir: Path | None) -> dict | None:
    """Where the ledger stands: ``{status, stage, revision, accepted, last_accepted}``, or None when the run has no state.

    ``accepted`` is the length of the append-only history and ``last_accepted`` its newest entry's stage and action (None
    while nothing is accepted). The harness records it at the end of every host session (sessions.jsonl), so the
    engine's position at the moment a session ended is a fact of the record and not a reading made afterwards.
    """
    state = engine_state(run_dir)
    if not state:
        return None
    history = state.get("history") if isinstance(state.get("history"), list) else []
    last = history[-1] if history and isinstance(history[-1], dict) else None
    return {"status": state.get("status"), "stage": current_stage(state), "revision": state.get("revision"),
            "accepted": len(history),
            "last_accepted": None if last is None else {"stage": last.get("stage"), "action": last.get("action")}}


NOT_RECORDED = "not recorded"


def planning_review(state: dict) -> str:
    """The run's `planning_review` option as state.md recorded it (ShipLoop 1.22.0): the text as written (`stage` or `none`),
    any other value shown as it is, and "not recorded" when the key is absent. Never a default. The Run Review exporter
    (skills/shiploop-run-review) reads the same key the same way."""
    value = state.get("planning_review")
    return NOT_RECORDED if value is None else value if isinstance(value, str) else json.dumps(value)


def _epoch(text: object) -> float | None:
    """One ShipLoop UTC stamp as epoch seconds, or None when it cannot be read."""
    if not isinstance(text, str):
        return None
    for shape in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ"):
        try:
            naive = datetime.strptime(text, shape)
        except ValueError:
            continue
        return naive.replace(tzinfo=timezone.utc).timestamp()
    return None


def acceptance_stamps(run_dir: Path | None) -> dict[str, float]:
    """When ShipLoop accepted each action, by action id, from its own timeline.json.

    Advisory, not authoritative: the engine recreates a missing timeline and
    gives a missing historical action the current time, so a stamp can be a
    recovery artefact (not detected: all actions then share one readable stamp).
    An entry that cannot be read is left out rather than guessed, which makes its
    stage report unavailable downstream. Stamps are whole seconds, truncated, so a
    boundary is only good to one second (see per_stage).
    """
    if run_dir is None or not (run_dir / "timeline.json").is_file():
        return {}
    try:
        raw = json.loads((run_dir / "timeline.json").read_text(errors="replace"))
    except ValueError:
        return {}
    accepted = raw.get("accepted") if isinstance(raw, dict) else None
    if not isinstance(accepted, dict):
        return {}
    return {action: when for action, text in accepted.items()
            if isinstance(action, str) and (when := _epoch(text)) is not None}


def stage_results(run_dir: Path | None, state: dict | None = None) -> list[dict]:
    """Accepted actions in ShipLoop's own order, with its own acceptance times.

    The authority is state.md's history -- stage, outcome and action id -- joined
    to timeline.json by action id. Result-file mtimes are deliberately not used:
    rewriting a file would move a boundary the engine never moved, and the order
    history records is the order the graph took. An action whose stamp cannot be
    read carries ``t`` None, so attribution reports it unavailable instead of
    inventing a zero-length window.

    ``state`` lets a caller that already read state.md pass it in, so one
    collection cannot read two different versions of a live run's state.
    """
    history = (engine_state(run_dir) if state is None else state).get("history")
    if not isinstance(history, list):
        return []
    stamps = acceptance_stamps(run_dir)
    rows = []
    for entry in history:
        if not isinstance(entry, dict):
            continue
        action = entry.get("action")
        rows.append({"stage": entry.get("stage") or "?", "outcome": entry.get("outcome"),
                     "work_item": entry.get("workitem"), "action": action if isinstance(action, str) else None,
                     "t": stamps.get(action) if isinstance(action, str) else None})
    return rows


def improve_reviews(run_dir: Path | None) -> dict:
    """Review passes per Improve child, from the review notes the run's worktree keeps.

    A child's passes are its review-<n>.md files; seconds is the time between its first and last note, so a long
    child shows where review passes, not stages, spent the run. Used to decide whether repeat passes are wasted.
    """
    root = run_dir.parent / "worktree" / ".shiploop-improve" if run_dir else None
    children = []
    for reviews in sorted(root.glob("*/*/reviews")) if root and root.is_dir() else []:
        notes = sorted(reviews.glob("review-*.md"))
        if notes:
            stamps = [n.stat().st_mtime for n in notes]
            children.append({"child": reviews.parent.name, "passes": len(notes),
                             "seconds": round(max(stamps) - min(stamps), 1),
                             "bytes": sum(n.stat().st_size for n in notes)})
    return {"children": len(children), "passes": sum(c["passes"] for c in children),
            "max_passes": max((c["passes"] for c in children), default=0), "per_child": children}


def session_stop(event: dict) -> str | None:
    """The host's own reason a session ended, or None when it reported none.

    Claude ends an API failure (rate limit, exhausted credits, a model it may not
    use) with subtype "success" and is_error true, so the subtype alone would call
    that stop a success: the error fields come first. A failed Codex turn carries
    its message in ``error``. Grok's ``cancelled`` is one reason for several causes
    (an empty turn, a permission refusal, exhausted credits) and cannot be told
    apart here.
    """
    detail = event.get("error") if isinstance(event.get("error"), str) else None
    if event.get("is_error") is True or detail:
        # An error result with no terminal reason still names its subtype (error_max_turns, error_during_execution)
        # and, in the SDK's documented shape, its first entry in `errors`.
        subtype = event.get("subtype") if isinstance(event.get("subtype"), str) and event["subtype"] != "success" else None
        why = " ".join(str(p) for p in (subtype, event.get("terminal_reason"), event.get("api_error_status")) if p)
        errors = event.get("errors") if isinstance(event.get("errors"), list) else []
        said = detail or (event.get("result") if isinstance(event.get("result"), str) else "") or \
            (errors[0] if errors and isinstance(errors[0], str) else "")
        bits = [b for b in (why, " ".join(said.split())[:100]) if b]
        return "error" + (": " + ": ".join(bits) if bits else "")
    reason = event.get("stopReason") or event.get("subtype")
    if reason is None:
        return None
    return reason if isinstance(reason, str) else json.dumps(reason, sort_keys=True)[:100]


# Why a counter is unmeasured, recorded beside the run so a reader never takes its 0 for a measurement.
NO_PER_CALL_USAGE = ("the host reports no per-call usage events (one total per session), so turns cannot be "
                     "attributed to a stage")
NO_MODEL_CALLS = ("the host's events carry no per-call usage (no Claude assistant message and no Grok usage event), so "
                  "the number of model calls is not known")
NO_WINDOW = ("no result event named one context window in its modelUsage (the host reports none, the session ended "
             "before it reported, or several models reported different windows)")
NO_ROLLOUT_WINDOW = "no main-thread token_count record in the rollouts reported a model_context_window"
# Counters read only from an event shape Grok writes. A stream with no per-call usage events (Claude's, or Codex's
# through the translator) is not Grok's, so there a 0 means the signal is missing, not that nothing happened, and a
# list stays empty rather than hold what a look-alike matched (Codex prints "cancelled 0" in a failing node --test
# summary, and its file_change is a write, not a read). Not read for Claude although its SDK names a
# system/compact_boundary event: no recorded run contains one, so its shape is unverified; add the branch when a
# recorded stream shows one. A stream that mixes hosts (a resume on another) is read as the host that wrote usage events.
GROK_SIGNALS = {
    "compactions": "an auto_compact_completed event",
    "truncated_outputs": "rawOutput.truncated on a tool_call_update",
    "cancelled_tool_calls": "a failed tool_call_update saying the user cancelled it, Grok's permission refusal",
    "knowledge_reads": "a read tool call naming a file path",
}


def context_tokens(usage) -> int | None:
    """Tokens one call held as context, or None when its event carried no figure.

    Input, cache reads and cache writes: a prompt-cache write (Claude's cache_creation_input_tokens) is context the
    call sent too, and on a recorded Claude run leaving it out made a turn read up to 60.7% low and the run's
    peak 0.6% low. Each figure is counted only where the host reports it, so a host with no per-call usage stays None.
    """
    if not isinstance(usage, dict):
        return None
    parts = [usage.get(key) for key in ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")]
    numbers = [p for p in parts if isinstance(p, (int, float)) and not isinstance(p, bool)]
    return sum(numbers) if numbers else None


def context_windows(event: dict) -> set[int]:
    """The context windows a result event reports, one per model in its ``modelUsage`` (Claude's shape)."""
    usage = event.get("modelUsage")
    found = (m.get("contextWindow") for m in usage.values() if isinstance(m, dict)) if isinstance(usage, dict) else ()
    return {w for w in found if isinstance(w, int) and not isinstance(w, bool) and w > 0}


def total_cost(sessions: list[dict]) -> float | None:
    """The run's cost: its sessions' own reported costs added, or None unless every ended session reported one.

    A host that reports no cost (Codex) has an unknown cost, not a free run, and a session that ended without
    one makes the rest a part, not a total. The one implementation: the metrics and the CLI summary both call it.
    A session that never ended is not in ``sessions`` at all; ``unreported_sessions`` counts those.
    """
    costs = [s.get("cost_usd") for s in sessions if isinstance(s, dict)]
    if not costs or any(isinstance(c, bool) or not isinstance(c, (int, float)) for c in costs):
        return None
    return round(sum(costs), 4)


# Why a planning figure is missing, recorded inside the `planning` block (never in the top-level `unmeasured` map).
PLANNING_NOT_YET = "no stage has been accepted yet, so there is no planning window"
PLANNING_NO_START = ("timeline.json records no start time (a run from before the pace line, or no timeline.json), so "
                     "the engine clock cannot be read")
PLANNING_NO_END = "the stage that ends the window has no readable accept stamp"
PLANNING_SEEDED = ("a planning stage was accepted before the host's first event (the harness records a seeded run's "
                   "early stages itself), so the window is not the host's work")
PLANNING_RECREATED = ("the window's stages carry one stamp (the engine gives every action one timeline stamp when it "
                      "recreates a lost timeline.json) or do not move past the start, so no duration can be read")
PLANNING_NO_RUNNER_TIMELINE = "the harness wrote no runner timeline (timeline.jsonl), so the host clock cannot be placed"
PLANNING_NO_IMPROVE_RESULTS = "state.md records no improve_results, so a run with Improve children cannot be told from one without"
CLAUDE_OUTPUT_TOKENS = ("this host's per-message output counts are streaming snapshots (about 1/17 of the session's own "
                        "total on a recorded run); only the whole-run usage is exact")
NO_HOST_USAGE = "the host's events carry no per-call output counts and no rollouts were read"


def run_started(run_dir: Path | None) -> float | None:
    """When the engine says the run started (timeline.json `started`, the clock the narrative's pace line uses), or None."""
    if run_dir is None or not (run_dir / "timeline.json").is_file():
        return None
    try:
        raw = json.loads((run_dir / "timeline.json").read_text(errors="replace"))
    except ValueError:
        return None
    return _epoch(raw.get("started")) if isinstance(raw, dict) else None


def _improve_seconds(run_dir: Path | None, results: object, row: dict) -> tuple[float | None, str | None]:
    """(seconds an Improve child spent on this accepted action, why it is unknown): its bind file's time to the accept.

    0.0 is a measurement: no child ran for the action (it has no entry in state.md's improve_results). Accept stamps
    are whole seconds, truncated, and a bind file's mtime is fractional, so the accept can read up to one second
    before the bind (-0.33 s on a recorded Sonnet run): that is 0.0, and a larger negative is unreadable, not a duration.
    """
    if not isinstance(results, dict):
        return None, PLANNING_NO_IMPROVE_RESULTS
    if row["action"] not in results:
        return 0.0, None
    if row["t"] is None:
        return None, f"the {row['stage']} Improve child's accept stamp is unreadable"
    try:
        bound = (run_dir / "improve" / f"{row['action']}-bind.md").stat().st_mtime
    except (OSError, TypeError):
        return None, f"the {row['stage']} Improve child has no improve/<action>-bind.md to start its time from"
    gap = row["t"] - bound
    if gap < -1.0:
        return None, f"the {row['stage']} accept stamp is more than a second before its Improve child's bind file"
    return round(max(gap, 0.0), 1), None


def planning_window(run_dir: Path | None, state: dict, accepted: list[dict], stamps: dict) -> tuple[dict, tuple | None, str]:
    """The planning window and its Improve share, from ShipLoop's own records: (block, token bounds, why no bounds).

    The window runs from the engine's start (timeline.json `started`) to the first accepted `test-spec` with outcome
    done, the owner's planning rule (S-10 carve-out, 2026-10-05); a `revise` row does not close it. It is read on two
    labelled clocks: the engine's (`seconds`) and the host's (`host_seconds`, from the runner's first event), whose
    difference is `before_engine_seconds`. An open window reports `through`, the stage of its last stamped row, and is
    never 0. Anything that cannot be read is None with its reason in `unmeasured`, and a window the stamps cannot
    support (a seeded run, a recreated timeline, a missing start) is unmeasured as a whole. Each row of `stages` is one
    accepted visit with its seconds and `improve_seconds`, which runs from the Improve child's bind file to the accept
    (the exporter's `improveMin` runs to the receipt instead, so the two differ by the receipt's write time).

    Readers: `summary_lines` and progress.py print the totals; the rows are for the owner's reading of metrics.json
    (is the planning window under 30 minutes, and where did it go) and for the Run Review page.
    """
    unmeasured: dict[str, str] = {}
    window = {"closed": False, "through": None, "seconds": None, "host_seconds": None, "before_engine_seconds": None}
    block = {"window": window, "stages": [], "improve": None, "producer_seconds": None, "unmeasured": unmeasured}
    rows: list[dict] = []
    for row in accepted:
        rows.append(row)
        if row["stage"] == "test-spec" and row["outcome"] == "done":
            window["closed"] = True
            break
    if not rows:
        unmeasured["window"] = PLANNING_NOT_YET
        return block, None, PLANNING_NOT_YET
    stamped = [r for r in rows if r["t"] is not None]
    last = rows[-1] if window["closed"] else (stamped[-1] if stamped else rows[-1])
    window["through"] = last["stage"]
    end, started = last["t"], run_started(run_dir)
    first_event = min(stamps.values()) if stamps else None
    reason = (PLANNING_NO_START if started is None else PLANNING_NO_END if end is None
              else PLANNING_SEEDED if first_event is not None and any(r["t"] < first_event for r in stamped)
              else PLANNING_RECREATED if end <= started or (len(stamped) > 1 and len({r["t"] for r in stamped}) == 1)
              else None)
    if reason:
        unmeasured["window"] = reason
        return block, None, f"the planning window is not measured: {reason}"
    window["seconds"] = round(end - started, 1)
    if first_event is None:
        unmeasured["host_seconds"] = PLANNING_NO_RUNNER_TIMELINE
    else:
        window["host_seconds"] = round(end - first_event, 1)
        window["before_engine_seconds"] = round(window["host_seconds"] - window["seconds"], 1)
    results = state.get("improve_results")
    previous, known, spent, children = started, True, 0.0, 0
    for row in rows:
        seconds = None if row["t"] is None or previous is None else round(row["t"] - previous, 1)
        previous = row["t"]
        improve, why = _improve_seconds(run_dir, results, row)
        if why:
            unmeasured.setdefault("improve", why)
        known = known and improve is not None
        spent += improve or 0.0
        children += isinstance(results, dict) and row["action"] in results
        block["stages"].append({"stage": row["stage"], "outcome": row["outcome"], "action": row["action"],
                                "seconds": seconds, "improve_seconds": improve})
    if isinstance(results, dict):
        block["improve"] = {"children": children, "seconds": round(spent, 1) if known else None}
        if known:
            block["producer_seconds"] = round(window["seconds"] - spent, 1)
    if not window["closed"]:
        return block, None, f"the planning window is still open (through {window['through']})"
    if first_event is None:
        return block, None, PLANNING_NO_RUNNER_TIMELINE
    return block, (first_event - 1, end), ""


def planning_tokens(bounds: tuple | None, why: str, usage_rows: list[tuple], grok: bool, claude: bool,
                    context: dict | None) -> dict:
    """The planning window's output and reasoning tokens, where the host's per-call counts are exact, on the host clock.

    Grok writes each call's usage in the stream (the window's sum of 87 events equalled the host's own totals on a
    recorded run); Codex only in its rollout files (rollouts.window_tokens, compaction requests included); Claude's
    per-message counts are streaming snapshots, so it is unmeasured. The window is the host's: from its first event, so
    it also holds the minutes before the engine started (`before_engine_seconds`). Nothing here ever reads as 0.
    """
    if bounds is None:
        return {"unmeasured": why}
    low, high = bounds
    if grok:
        inside = [(out, reasoning) for t, out, reasoning in usage_rows if t is not None and low < t <= high]
        if not inside or any(out is None for out, _ in inside):
            return {"unmeasured": "no Grok usage event with an output count falls in the planning window"}
        return {"output": sum(out for out, _ in inside),
                "reasoning": None if any(r is None for _, r in inside) else sum(r for _, r in inside),
                "clock": "host", "source": "usage events"}
    if claude:
        return {"unmeasured": CLAUDE_OUTPUT_TOKENS}
    if context is None:
        return {"unmeasured": NO_HOST_USAGE}
    got = context.get("tokens") if "unmeasured" not in context else context
    if got is None or "unmeasured" in got:
        return {"unmeasured": (got or {}).get("unmeasured", NO_HOST_USAGE)}
    return {**got, "clock": "host", "source": "rollout token_usage_records"}


# ---------------------------------------------------------------------------------------------------------------------------
# What a fresh context did (SPEC "A fresh context is recorded, not scored"). Record-only: nothing here is a verdict.

# The ShipLoop CLI and run directory a `next` call carries, read from the command as the model wrote it (variables expanded
# where the same command assigns them), to compare with what the resume prompt told.
NEXT_CALL = re.compile(r"""(?P<cli>[^\s"'=]*shiploop)["']?\s+next\b(?P<rest>[^\n]*)""")
RUN_DIR_ARG = re.compile(r"""--run-dir(?:=|\s+)["']?(?P<dir>[^"'\s]+)""")
# The ShipLoop verbs whose call can be the one that gets an action accepted (an Improve child's finish accepts its parent).
ACCEPTING_VERBS = ("complete", "improve-complete")
# Why `rewrote` and the window's failures are lower bounds (the scope strings in a block say it short; this says it whole).
# `rewrote` sees file-edit tools only: a file a shell command writes (cat >, sed -i, cp, tee, a script) is invisible to the tool
# log, so an empty list is "none seen", not a measured none. The window's failures are the window's own calls only: a wrapper
# script the model wrote in an earlier session is not known to the window, so a ShipLoop command run through one is not
# recognised, and a refusal behind a pipe that lost its prefix line is missed.
FAILURES_SCOPE = "the window's own calls only: a ShipLoop command run through a script written in an earlier session is not seen"
FRESH_STARTS_UNREADABLE = ("not recorded: sessions.jsonl exists but cannot be read, so the host session starts are unknown; only "
                           "the compactions are listed")
FRESH_STARTS_NOT_RECORDED = ("not recorded: this run has no sessions.jsonl (the harness wrote it from 2026-10-09), so its host "
                             "session starts are unknown; only its compactions are listed")
NO_EVENT = "the session wrote no event"
NO_LATER_ACCEPT = "the ledger accepted no action after this start"
AMBIGUOUS_ACCEPT = ("an action accepted after this start has no accept stamp, so which accept came next cannot be told")
NO_SUBMISSION = ("the next accepted action ({stage}, {action}) was not submitted by a tool call this window recognises: it was "
                 "accepted by something that left no event (an orphan host), by a script this window does not see, or the "
                 "session ended before it")
PARKED = ("every call that names the next accepted action ({stage}, {action}) returned before its accept stamp: it was parked "
          "(an Improve child) or accepted by a call this window does not recognise")
SESSION_BOUNDS = "session bounds not recorded: {why}"


def written_paths(rows) -> set:
    """The paths file-edit tools (write, edit, replace, create) wrote in these (line, event) rows, normalised."""
    found = set()
    for _line, event in rows:
        for _call_id, tool, arg in tool_call_events(event):
            if WRITE_TOOL.search(tool) and call_target(arg):
                found.add(os.path.normpath(call_target(arg)))
    return found


def _verbs(call: dict) -> list[str]:
    """The ShipLoop verbs a call runs, directly or through a script the model wrote earlier in the same window."""
    return [m.group("verb") for m in SHIPLOOP_COMMAND.finditer(call.get("invoked", ""))]


# The Improve runtime's own recovery command, printed in an Improve child's packet ("Recover active Improve packet after
# compaction"): `python3 .../improve/runtime/until-loop/scripts/until_loop_ephemeral.py next --state ...`. Not a ShipLoop verb.
IMPROVE_NEXT = re.compile(r"until[_-]loop\w*\.py[\"']?\s+next\b")
SKILL_CARD = re.compile(r"SKILL\.md")


def call_kind(call: dict) -> str:
    """What one tool call is, as far as re-grounding goes: `next` (ShipLoop's), `improve-next` (the Improve runtime's recovery
    command), `packet` (a read of, or a command naming, a packet file), `verb` (another ShipLoop verb: complete, lint, an
    improve-* verb), `skill-card` (a read of a SKILL.md), or `plain`. The one classifier: the windows and the evidence script
    both read a call through it."""
    verbs = _verbs(call)
    if "next" in verbs:
        return "next"
    if IMPROVE_NEXT.search(call.get("expanded", "")):
        return "improve-next"
    if call.get("packet"):
        return "packet"
    if verbs:
        return "verb"
    return "skill-card" if SKILL_CARD.search(call.get("command", "") or call.get("file", "")) else "plain"


def _grounding(call: dict) -> str | None:
    """Whether a call goes to ShipLoop's scripts or reads a packet: `next`, `improve-next`, `packet`, or `other` (another
    ShipLoop verb, `complete` or `lint` among them), else None. It submits or asks; it is not only a question."""
    kind = call_kind(call)
    return {"verb": "other", "skill-card": None, "plain": None}.get(kind, kind)


def _same_path(told: str | None, got: str | None) -> str:
    """How a path in the model's command compares with the one it was told: `exact` (the same text), `equivalent` (the same
    place after normpath and resolve: the recorded Luna `/./` ran), `different` (another place), or `unreadable` (a relative
    path or an unexpanded variable, which cannot be compared)."""
    if got is None or not isinstance(told, str):
        return "unreadable"
    if got == told:
        return "exact"
    if "$" in got or not os.path.isabs(got):
        return "unreadable"
    return "equivalent" if os.path.realpath(got) == os.path.realpath(told) else "different"


def _recovery(tools: "ToolLog", window: list, told: dict | None, heads: dict) -> dict:
    """Was the recovery command repeated as told? The first `next` call of the window, its CLI and run directory compared with
    the ones the prompt named (None where it named none: a compaction), whether it failed, and how many `next` calls there were.
    ``revision_seen`` is the engine revision the first `next` that returned a packet printed (``heads``: the text each `next`
    call returned), which a later comparison sets beside the revision the killed session's end row recorded."""
    nexts = [(number, key) for number, key in enumerate(window, 1) if "next" in _verbs(tools.calls[key])]
    revision = next((int(found.group("revision")) for _number, key in nexts
                     for found in [PACKET_STAGE.search(heads.get(key, ""))] if found and found.group("revision")), None)
    first = None
    if nexts:
        number, key = nexts[0]
        found = NEXT_CALL.search(tools.calls[key]["expanded"])
        run_dir = RUN_DIR_ARG.search(found.group("rest")) if found else None
        failed = key in tools.failed
        first = {"call": number, "failed": failed, "exit": tools.failure_of[key]["exit"] if failed else None,
                 "cli": None if told is None else _same_path(told.get("cli"), found.group("cli") if found else None),
                 "run_dir": None if told is None else _same_path(told.get("run_dir"), run_dir.group("dir") if run_dir else None)}
    return {"told": told, "next_calls": len(nexts), "first_next": first, "revision_seen": revision}


def _scoped(event: dict, token) -> dict:
    """The event with its call ids made unique to one session, so a host that numbers its calls again in a continued session
    (Codex: item_1 in every session) cannot have one call replace another in a window's log."""
    prefix = f"{token}:"
    kind = event.get("type")
    if kind == "assistant" and isinstance(event.get("message"), dict):
        blocks = [dict(b, id=prefix + str(b.get("id"))) if isinstance(b, dict) and b.get("type") == "tool_use" else b
                  for b in event["message"].get("content") or []]
        return dict(event, message=dict(event["message"], content=blocks))
    if kind == "user" and isinstance(event.get("message"), dict):
        blocks = [dict(b, tool_use_id=prefix + str(b.get("tool_use_id"))) if isinstance(b, dict) and b.get("type") == "tool_result"
                  else b for b in event["message"].get("content") or []]
        return dict(event, message=dict(event["message"], content=blocks))
    if kind in ("tool_call", "tool_call_update") and event.get("toolCallId") is not None:
        return dict(event, toolCallId=prefix + str(event["toolCallId"]))
    return event


def _next_accept(accepted: list[dict], start_t: float | None, ledger_at_start: int | None) -> tuple:
    """(index in ``accepted`` of the first action the ledger accepted after the start, None), or (None, why it cannot be told).

    The start row's ledger length (``ledger_at_start``) names it exactly. Without it the first row stamped at or after the start's
    second is taken, and a row with no stamp between the last earlier one and that one could be the next accept, so it is
    refused rather than guessed. (An accept in the start's own second, before the start, is taken for the next: its submission
    is then not found in the window, and the window is not measured: safe, not wrong.)
    """
    if ledger_at_start is not None:
        return (ledger_at_start, None) if 0 <= ledger_at_start < len(accepted) else (None, NO_LATER_ACCEPT)
    if start_t is None:
        return None, NO_EVENT
    unstamped = False
    for index, row in enumerate(accepted):
        if row["t"] is None:
            unstamped = True
        elif row["t"] < int(start_t):
            unstamped = False
        else:
            return (None, AMBIGUOUS_ACCEPT) if unstamped else (index, None)
    return (None, AMBIGUOUS_ACCEPT) if unstamped else (None, NO_LATER_ACCEPT)


def reorientation(rows, stamps: dict, accepted: list[dict], told: dict | None = None, earlier=None, *,
                  ledger_at_start: int | None = None, scope=None, session_marks: list | None = None) -> dict:
    """What a fresh context did from its start to the next accepted action: a record, never a verdict.

    ``rows`` are the (line, event) pairs of one session's events from the fresh start, read lazily (this stops reading at
    the window's end); ``stamps`` the runner's timeline; ``accepted`` the ledger's accepted rows (``stage_results``);
    ``told`` the CLI and run directory the resume prompt named (None for a start with no recovery command, a compaction);
    ``earlier(after)`` the (line, event) pairs before the start whose stamp is after ``after`` (None: from the beginning),
    the stage's pre-start portion that `rewrote` compares. ``ledger_at_start`` is how many actions the ledger had accepted
    when the context began (a start row's engine.accepted); ``scope(line)`` names the host session a line belongs to, so call
    ids reused by a continued session stay apart; ``session_marks`` is None for a run whose sessions.jsonl bounded the rows,
    else the epoch seconds at which other launches began (runrecord), and then a host's own end or init event in the window
    counts as a session boundary too.

    The action waited for is the FIRST the ledger accepted after the start (``_next_accept``). The window ends at the LAST
    `complete` or `improve-complete` call that names it, did not fail, began before its accept stamp's second ended and
    returned at or after the stamp. The stamp is whole-second truncated, so a cut at the stamp would lose the call (it starts
    after the truncated stamp) or keep the next one (it starts in the same second); an Improve park's parent `complete`
    returns long before the accept and is not the call. Both clocks are recorded: ``seconds`` to the call, on the runner's
    clock, and ``seconds_to_accept_stamp``, good to a second. A window the records cannot place that way is never extended
    to a later action: it is ``measured: false`` with its reason.

    Always present: ``first_grounding`` (see ``_grounding``) with ``calls_before_grounding``, and ``recovery``. A window that is
    not measured has no count: unknown is not zero. ``failures`` and ``rewrote`` are lower bounds and say so.
    """
    iterator = iter(rows)
    head, start_t = [], None
    for line, event in iterator:  # the first stamped event is the start; the action waited for is chosen from its time
        head.append((line, event))
        if stamps.get(line) is not None:
            start_t = stamps[line]
            break
    index, why = _next_accept(accepted, start_t, ledger_at_start) if head else (None, NO_EVENT)
    row = accepted[index] if index is not None else None
    target = row["action"] if row and isinstance(row.get("action"), str) else None
    stamp = row["t"] if row else None
    pattern = re.compile(r"(?<![\w-])" + re.escape(target) + r"(?![\w-])") if target else None
    tools, order = ToolLog(), []
    candidates: list = []  # calls that name the target in an accepting verb and began before its accept stamp's second ended
    line_of: dict = {}
    result_t: dict = {}
    heads: dict = {}  # `next` call -> the first characters of what it returned (the last update of a running Grok call wins)
    marker = None  # (line, what) of the first host session boundary inside the window, when the run's sessions are not recorded
    last_t = start_t
    for line, event in itertools.chain(head, iterator):
        t = stamps.get(line)
        last_t = t if t is not None else last_t
        if session_marks is not None and marker is None and line != head[0][0] and (
                event.get("type") in ("end", "result") or (event.get("type") == "system" and event.get("subtype") == "init")):
            marker = (line, f"a host {event.get('type')} event at line {line}")
        seen = _scoped(event, scope(line)) if scope else event
        for key in tools.feed(seen, t):
            order.append(key)
            line_of[key] = line
            if pattern and _submits(tools.calls[key], pattern) and _plausible_submission(stamp, tools.calls[key]["t"]):
                candidates.append(key)
        for call_id, shown in tool_results(seen):
            if call_id in tools.calls and "next" in _verbs(tools.calls[call_id]):
                heads[call_id] = shown[:400]
        for key in candidates:
            if key in tools.answered and key not in result_t:
                result_t[key] = last_t
        resolved = all(key in tools.answered for key in candidates)
        if stamp is None:  # no time to wait for: the first submission that did not fail is the one
            if any(key in tools.answered and key not in tools.failed for key in candidates):
                break
        elif resolved and t is not None and t >= stamp + 1:  # every call that could have got it accepted has been seen
            break
    placed = [key for key in candidates if key in tools.answered and key not in tools.failed
              and (stamp is None or result_t.get(key) is None or result_t[key] >= stamp)]
    parked = [key for key in candidates if key in tools.answered and key not in tools.failed and key not in placed]
    end_key = (placed[0] if stamp is None else placed[-1]) if placed else None
    window = order if end_key is None else order[:order.index(end_key) + 1]
    grounding = next(((number, _grounding(tools.calls[key])) for number, key in enumerate(window)
                      if _grounding(tools.calls[key])), (None, None))
    common = {"first_grounding": grounding[1], "calls_before_grounding": grounding[0],
              "recovery": _recovery(tools, window, told, heads)}
    # A host session that began or ended inside the window means a run with no recorded bounds cannot place it.
    if session_marks is not None and start_t is not None:
        until = tools.calls[end_key]["t"] if end_key is not None else (stamp + 1 if stamp is not None else last_t)
        crossed = [f"another launch began at {m}" for m in session_marks if until is not None and start_t < m <= until]
        if marker and (end_key is None or marker[0] < line_of[end_key]):
            crossed.append(marker[1])
        if crossed:
            return {"measured": False, "reason": SESSION_BOUNDS.format(why="; ".join(crossed) + " before the next accepted "
                                                                      "action, so this window may span two sessions"), **common}
    if target is None:
        return {"measured": False, "reason": why or NO_LATER_ACCEPT, **common}
    if end_key is None:
        text = PARKED if parked else NO_SUBMISSION
        return {"measured": False, "reason": text.format(stage=row["stage"], action=target), **common}
    submitted_at = tools.calls[end_key]["t"]
    failures = [tools.failure_of[key] for key in window if key in tools.failure_of]
    return {"measured": True, "accepted": {"stage": row["stage"], "action": target}, "tool_calls": len(window),
            "seconds": None if start_t is None or submitted_at is None else round(submitted_at - start_t, 1),
            "seconds_to_accept_stamp": None if start_t is None or stamp is None else round(stamp - start_t, 1),
            **common,
            "failures": {"items": failures, "bound": "lower", "scope": FAILURES_SCOPE},
            "rewrote": _rewrote(tools, window, earlier, accepted, index),
            "asked_user": sum(bool(ASK_PERSON.search(tools.calls[key]["tool"])) for key in window)}


def _submits(call: dict, pattern) -> bool:
    """Whether a tool call runs a `complete` or `improve-complete` that names the action ``pattern`` matches."""
    return any(verb in ACCEPTING_VERBS for verb in _verbs(call)) and bool(pattern.search(call.get("invoked", "")))


def _plausible_submission(stamp: float | None, call_t: float | None) -> bool:
    """A call can have got an action accepted only if it did not begin after the accept's second: the stamp is truncated, so
    the accept lies in [stamp, stamp + 1). A call of this session that names an action accepted before the session began
    is therefore never the submission (it starts after that stamp's second)."""
    return stamp is None or call_t is None or call_t < stamp + 1


def _rewrote(tools: "ToolLog", window: list, earlier, accepted: list[dict], index: int) -> dict:
    """Paths a file-edit tool wrote both in the stage's pre-start portion (since the last accepted action) and in the window."""
    previous = accepted[index - 1] if index else None
    if earlier is None:
        paths, scope = None, "unknown: no earlier portion of the stage was given"
    elif previous is not None and previous["t"] is None:
        paths, scope = None, "unknown: the previous accepted action has no accept stamp"
    else:
        after = {os.path.normpath(call["file"]) for key in window
                 for call in [tools.calls[key]] if WRITE_TOOL.search(call["tool"]) and call["file"]}
        paths = sorted(written_paths(earlier(previous["t"] if previous else None)) & after)
        scope = f"{len(paths)} seen by file-edit tools" if paths else "none seen by file-edit tools"
    return {"paths": paths, "bound": "lower", "scope": scope}


def fresh_starts(out: Path, stamps: dict, accepted: list[dict], sessions: list[dict] | None, compactions: list[dict],
                 launch_epochs: list | None = None) -> list[dict]:
    """One block for every fresh context the run had, in the order of its first event: a host session started with no host
    session id passed (``sessions`` rows of kind `fresh`: a --resume-run, the session after an --interrupt-at) and every
    compaction (``compactions``: {"host": "grok", "line": n} where the host's event stream marks it, {"host": "codex", "t": epoch}
    where only its rollouts do). Each block is ``reorientation`` over the events from that point to the next recorded FRESH
    start (or the end of the file); a `continued` session keeps the context and the window; a compaction's has no told command.

    A start row's ``engine.accepted`` names the action a fresh session waits for exactly. Where the sessions are not recorded
    (no sessions.jsonl, or events before its first row) nothing bounds a window, so ``launch_epochs`` (runrecord) and the host's
    own end and init events say where another session began, and a window that spans one is not measured.

    Record-only. ``sessions`` None (a run from before sessions.jsonl) lists no session start, only compactions; the caller
    says so. ``stage_in_flight`` is the stage whose acceptance ends the window, else the one the previous session's end row
    left in flight, else None. A fresh start also has ``after_kill``: the engine revision in the killed session's end row, in
    this session's start row and in the first `next` result it got, and ``moved`` (None while fewer than two are known).
    """
    path = out / "events.jsonl"
    rows = [row for row in sessions or [] if isinstance(row.get("events_line"), int)]
    fresh_lines = sorted(row["events_line"] for row in rows if row.get("kind") == "fresh")
    start_lines = sorted(row["events_line"] for row in rows)
    recorded_from = None if not rows else (0 if rows[0].get("kind") == "first" and rows[0]["events_line"] == 0
                                           else rows[0]["events_line"])
    ordered = sorted(stamps)
    times = [stamps[n] for n in ordered]

    def first_line_after(after: float | None) -> int:
        """The first stamped line whose stamp is after ``after`` (line 0 where there is no bound)."""
        if after is None:
            return 0
        index = bisect.bisect_right(times, after)
        return ordered[index] if index < len(ordered) else (ordered[-1] + 1 if ordered else 0)

    points = [(row["events_line"], "fresh", row) for row in rows if row.get("kind") == "fresh"]
    for compaction in compactions:
        line = compaction["line"] if "line" in compaction else first_line_after(compaction.get("t"))
        points.append((line, "compaction", compaction))
    blocks = []
    for line, kind, info in sorted(points, key=lambda point: point[0]):
        bound = next((b for b in fresh_lines if b > line), None)
        told = info.get("told") if kind == "fresh" and isinstance(info.get("told"), dict) else None
        started = info.get("engine") if kind == "fresh" and isinstance(info.get("engine"), dict) else {}
        at_start = started.get("accepted") if isinstance(started.get("accepted"), int) else None
        unrecorded = recorded_from is None or line < recorded_from
        block = reorientation(event_range(path, line, bound), stamps, accepted, told,
                              earlier=lambda after, line=line: event_range(path, first_line_after(after), line),
                              ledger_at_start=at_start, scope=lambda n: bisect.bisect_right(start_lines, n),
                              session_marks=list(launch_epochs or []) if unrecorded else None)
        entry = {"kind": kind, "n": None, "reason": None, "host": info.get("host"),
                 "t": info.get("t") if "t" in info else stamps.get(line), "events_line": line}
        left = {}
        if kind == "fresh":
            entry.update(n=info["n"], reason=info.get("reason"))
            previous = next((row for row in rows if row["n"] == info["n"] - 1), None)
            left = ((previous or {}).get("end") or {}).get("engine")
            left = left if isinstance(left, dict) else {}
        entry["stage_in_flight"] = block["accepted"]["stage"] if block["measured"] else left.get("stage")
        if kind == "fresh":
            # The engine at the kill, at the launch and in the fresh session's first `next` result: any difference is something
            # that advanced the run after the host was killed (an in-flight command of the killed session, an orphan).
            seen = {"end_revision": left.get("revision"), "start_revision": started.get("revision"),
                    "first_next_revision": block["recovery"]["revision_seen"]}
            known = {r for r in seen.values() if isinstance(r, int)}
            entry["after_kill"] = {**seen, "moved": len(known) > 1 if sum(isinstance(r, int) for r in seen.values()) > 1 else None}
        entry["reorientation"] = block
        blocks.append(entry)
    return blocks


def collect(out: Path, run_dir: Path | None = None) -> dict:
    stamps = timeline(out / "timeline.jsonl")
    tools = ToolLog()
    turns: list[dict] = []
    sessions, compactions = [], 0
    truncated: set = set()
    cancelled: list[str] = []
    grok = False  # per-call `usage` events: the one stream shape the Grok-only counters below can be read from
    starts = 0  # sessions the host began, to tell how many never reported an end
    messages: set[str] = set()  # Claude message ids seen: one API call writes one assistant event per content block
    claude_calls = usage_events = 0
    compaction_lines: list[int] = []  # where Grok's stream says a compaction completed: a fresh context for the model
    usage_rows: list[tuple] = []  # (t, output, reasoning) of Grok's per-call usage events: the planning window's tokens
    reported: set[int] = set()  # context windows the result events reported
    versions: set[str] = set()  # Claude Code builds that opened a session: the host CLI changes between runs of one prompt
    # A session that reports no per-call usage (Codex) contributes its own turn count.
    unreported, calls_in_session = 0, 0
    for number, event in events(out / "events.jsonl"):
        kind = event.get("type")
        t = stamps.get(number)
        tools.feed(event, t)  # Claude tool_use / tool_result blocks, Grok and Codex tool_call / tool_call_update
        if kind in ("usage", "assistant"):
            calls_in_session += 1
        if kind == "available_commands" or (kind == "system" and event.get("subtype") == "init"):
            starts += 1  # Codex and Grok open a session with available_commands, Claude with system/init
            if isinstance(event.get("claude_code_version"), str):
                versions.add(event["claude_code_version"])
        if kind == "usage":
            grok = True
            usage_events += 1
            # A usage event is one model call, as `model_calls` counts it: the stage rows count it too (per_stage reads ``call``).
            turns.append({"t": t, "input": context_tokens(event.get("usage")), "call": True})
            used = event.get("usage") if isinstance(event.get("usage"), dict) else {}
            usage_rows.append((t, *(v if isinstance(v, int) and not isinstance(v, bool) else None
                                    for v in (used.get("output_tokens"), used.get("reasoning_tokens")))))
        elif kind == "assistant":  # Claude: one event per content block of a message
            # `turns` keeps counting events (baselines.jsonl holds that definition); a model call is a message, counted at
            # its first event, and an event with no id is its own call.
            message_id = (event.get("message") or {}).get("id")
            first = not isinstance(message_id, str) or not message_id or message_id not in messages
            if first:
                claude_calls += 1
                if isinstance(message_id, str) and message_id:
                    messages.add(message_id)
            turns.append({"t": t, "input": context_tokens((event.get("message") or {}).get("usage")), "call": first})
        elif kind == "tool_call_update" and cancelled_update(event):
            # Grok's headless permission check refused the call; the turn ends with it.
            cancelled.append((tools.calls.get(event.get("toolCallId")) or {}).get("command", "")[:160])
        elif kind == "tool_call_update" and isinstance(event.get("rawOutput"), dict):
            if event["rawOutput"].get("truncated"):  # Grok repeats the update; count each call once
                truncated.add(event.get("toolCallId"))
        elif kind == "auto_compact_completed":
            compactions += 1
            compaction_lines.append(number)
        elif kind in ("end", "result"):
            reported |= context_windows(event)
            # The host's own usage is kept as it wrote it: its shape differs by host (Claude's nests), and
            # a figure built here from per-event snapshots or by summing sessions would not be the host's.
            sessions.append({"stop": session_stop(event), "turns": event.get("num_turns"),
                             "cost_usd": event.get("total_cost_usd"),
                             "usage": event.get("usage") if isinstance(event.get("usage"), dict) else None})
            if not calls_in_session:
                unreported += event.get("num_turns") or 0
            calls_in_session = 0
    # One read of state.md for both the accepted history and the pending stage: a
    # live run rewrites it on every transition, so two reads could disagree.
    state = engine_state(run_dir)
    accepted, pending = stage_results(run_dir, state), pending_stage(state)
    windows = stage_windows(accepted, stamps, pending)
    planning, bounds, why_not_tokens = planning_window(run_dir, state, accepted, stamps)
    # Counters this host's events cannot show are recorded as unmeasured with the reason,
    # never as 0: a zero would read as a measurement and pass every comparison.
    unmeasured: dict[str, str] = {}
    if not _timed(turns):
        unmeasured["stage_turns"] = NO_PER_CALL_USAGE
    if not grok:
        unmeasured.update({name: f"only Grok's events carry this signal ({signal}); this host's do not, so a "
                                 f"count of 0 is a missing signal and not a measurement"
                           for name, signal in GROK_SIGNALS.items()})
        cancelled, tools.reads = [], []
    # Model calls: what the host's own events show (Claude's unique messages, Grok's usage events). The context window
    # is the one the result events agree on. A host with no per-call events (Codex) keeps them only in its rollout
    # files: a run that mixes hosts is read as the host that wrote per-call events, as for the counters above.
    model_calls = (claude_calls + usage_events) or None
    window_tokens = next(iter(reported)) if len(reported) == 1 else None
    peak = max((x["input"] for x in turns if x["input"] is not None), default=None)
    context = None
    if model_calls is None:
        context = rollouts.rollout_context(out, [None if w is None else [w[0], w[1]] for w in windows],
                                           tokens_window=bounds)
        if "unmeasured" not in context:
            model_calls, window_tokens, peak = context["calls"], context["window"], context["peak"]
            compactions = context["compactions"]
            unmeasured.pop("compactions", None)  # Grok's detector said unmeasured; the rollouts measured it
    # Why a figure is missing: the host's events (and, for Codex, its rollouts) did not report it.
    why_not = context["unmeasured"] if context and "unmeasured" in context else None
    if model_calls is None:
        unmeasured["model_calls"] = NO_MODEL_CALLS + (f"; {why_not}" if why_not else "")
    if window_tokens is None:
        unmeasured["window_tokens"] = (f"{NO_WINDOW}; {why_not}" if why_not else
                                       NO_ROLLOUT_WINDOW if context else NO_WINDOW)
    planning["tokens"] = planning_tokens(bounds, why_not_tokens, usage_rows, grok, bool(claude_calls), context)
    # Fresh contexts: the sessions the harness recorded (sessions.jsonl; a run from before it says so) and every compaction the
    # host's events (Grok) or its rollouts (Codex) show. Claude's compactions are not detected (see GROK_SIGNALS).
    compaction_points = ([{"host": "grok", "line": n} for n in compaction_lines] if "compactions" not in unmeasured else [])
    if context and "unmeasured" not in context:
        compaction_points = [{"host": "codex", "t": t} for t in context.get("compaction_times", [])]
    try:
        sessions_recorded = sessionlog.read(out)
        notes = []
        if sessions_recorded is None:
            notes.append(FRESH_STARTS_NOT_RECORDED if not (out / sessionlog.SESSIONS).exists()
                         else FRESH_STARTS_UNREADABLE)
        else:
            first = sessions_recorded[0] if sessions_recorded else None
            events_before = first["events_line"] if first and isinstance(first.get("events_line"), int) else None
            if first is None and (out / "events.jsonl").is_file() and (out / "events.jsonl").stat().st_size:
                events_before = sum(1 for _ in (out / "events.jsonl").open("rb"))
            if events_before:
                notes.append(f"partial: sessions before events line {events_before} are not recorded")
        if "compactions" in unmeasured:
            notes.append(f"compactions not detected on this host: {unmeasured['compactions']}")
        fresh_list = fresh_starts(out, stamps, accepted, sessions_recorded, compaction_points,
                                  runrecord.launch_epochs(out))
        fresh_note = "; ".join(notes) or None
    except Exception as exc:  # noqa: BLE001 - a passive record never takes the run's metrics down (per_stage once did)
        fresh_list, fresh_note = [], f"failed: {type(exc).__name__}: {' '.join(str(exc).split())[:200]}"
    stages = per_stage(accepted, turns, tools.calls, stamps, pending, unmeasured, window_tokens)
    if context and "unmeasured" not in context:
        for row, figures in zip(stages, context["perStage"]):
            if figures is not None:
                row["context"] = figures
    improve = run_dir / "improve" if run_dir else None
    return {
        "tmp_writes": sorted(tools.shared),
        # The host CLI build the sessions ran on (Claude's init event; sessions on two builds name both), None where the
        # host's events do not carry it. Two runs of one prompt on different builds are not a controlled pair.
        "claude_code_version": ", ".join(sorted(versions)) or None,
        "sessions": sessions,
        # Unknown, not 0, when no call and no ended session reported a count (a Codex session killed before its
        # end event); a session that never reported beside one that did makes it a lower bound (unreported_sessions).
        "turns": len(turns) + unreported if turns or any(
            isinstance(s["turns"], int) and not isinstance(s["turns"], bool) for s in sessions) else None,
        # Messages, not events: `turns` above counts a Claude message once per content block (1.6 to 2 times the calls).
        "model_calls": model_calls,
        "window_tokens": window_tokens,
        # Context only: a call's input side is complete when it is sent. Its output count is a streaming
        # snapshot (about 1/17 of the session's own total on a recorded Claude run), so no output figure is built.
        # Codex is the exception: its rollouts report each call's own total (input plus output), see rollouts.py.
        "tokens": {"input_peak": peak},
        "unmeasured": unmeasured,
        "cost_usd": total_cost(sessions),
        "unreported_sessions": max(0, starts - len(sessions)),
        "compactions": None if "compactions" in unmeasured else compactions,
        "truncated_outputs": None if "truncated_outputs" in unmeasured else len(truncated),
        "cancelled_tool_calls": cancelled,
        "shiploop_failures": tools.failures,
        # Claude's tool_use / tool_result blocks only (main thread): what the model ran and how it used the packets. A
        # record, never a verdict; None on the hosts whose events this harness has no such reading of.
        "tool_use": tools.tool_use(run_dir) if claude_calls and not grok else None,
        "script_verifications": verifications(run_dir),
        "model_glue": tools.glue,
        "asked_user": tools.asked,
        # Directories only: each child also leaves a `<name>-bind.md` beside its directory.
        "improve_children": sum(1 for p in improve.iterdir() if p.is_dir()) if improve and improve.is_dir() else 0,
        "improve_reviews": improve_reviews(run_dir),
        "knowledge_reads": sorted({r[r.index("docs/shiploop"):] for r in tools.reads if "docs/shiploop" in r}),
        "narrative": narrative(out, run_dir),
        "stages": stages,
        "planning": planning,
        # Record-only (SPEC "A fresh context is recorded, not scored"): see fresh_starts. The list holds the compactions only,
        # and `fresh_starts_unmeasured` says why, where the run has no sessions.jsonl; None where it is complete.
        "fresh_starts": fresh_list,
        "fresh_starts_unmeasured": fresh_note,
    }


NARRATIVE = re.compile(r"=== ShipLoop narrative ===\n(?P<rule>[^\n]*)\n(?P<body>.*?)=== end ShipLoop narrative ===", re.S)
PACKET_STAGE = re.compile(r"ShipLoop navigator \| (?P<stage>[\w-]+) \|(?: revision (?P<revision>\d+))?")
STATE_BLOCK = re.compile(r"```shiploop-state\n(?P<json>.*?)\n```", re.S)


def _tool_output(event: dict) -> tuple[str | None, str]:
    """(tool call id, text) of the first tool result in one event, for Claude and Grok streams."""
    return next(tool_results(event), (None, ""))


def _assistant_text(event: dict) -> str:
    if event.get("type") == "text":  # Grok streams text in chunks
        return str(event.get("data") or "")
    if event.get("type") == "assistant":
        return "".join(str(block.get("text") or "") for block in (event.get("message") or {}).get("content") or []
                       if isinstance(block, dict) and block.get("type") == "text")
    return ""


def _lines(text: str) -> list[str]:
    """Non-blank lines, whitespace-collapsed; a heading's leading marks do not change what it says."""
    return [" ".join(line.lstrip("#").split()) for line in text.splitlines() if line.lstrip("#").strip()]


def narrative(out: Path, run_dir: Path | None = None) -> dict:
    """SPEC S-15: did the model show each milestone narrative ShipLoop asked it to show?

    An emission is a ShipLoop tool result whose narrative section asks the model to
    show it. It counts as shown when the narrative's heading appears in the model's
    text before the next emission, and verbatim when every narrative line does.
    Keeps counts and stage names only, never narrative text.
    """
    emissions: list[dict] = []
    seen: set = set()
    for _, event in events(out / "events.jsonl"):
        call, output = _tool_output(event)
        match = NARRATIVE.search(output) if output else None
        if match and call not in seen and "Show the user" in match.group("rule"):
            seen.add(call)
            stage = PACKET_STAGE.search(output)
            emissions.append({"stage": stage.group("stage") if stage else None,
                              "lines": _lines(match.group("body")), "text": ""})
        elif emissions:
            emissions[-1]["text"] += _assistant_text(event)
    shown = verbatim = 0
    skipped = []
    for emission in emissions:
        said = set(_lines(emission["text"]))
        if emission["lines"] and emission["lines"][0] in said:
            shown += 1
            verbatim += all(line in said for line in emission["lines"])
        else:
            skipped.append(emission["stage"])
    results = with_headline = 0
    for path in sorted((run_dir / "results").glob("*.md")) if run_dir and (run_dir / "results").is_dir() else []:
        block = STATE_BLOCK.search(path.read_text(errors="replace"))
        try:
            result = json.loads(block.group("json"))["result"] if block else None
        except (ValueError, KeyError, TypeError):
            result = None
        # ShipLoop records not-applicable stages itself; only steps the model reported count.
        if not isinstance(result, dict) or str(result.get("summary", "")).startswith("Not applicable to this item"):
            continue
        results += 1
        with_headline += bool(str(result.get("headline") or "").strip())
    return {"emitted": len(emissions), "shown": shown, "verbatim": verbatim, "skipped": skipped,
            "results": results, "with_headline": with_headline}


def verifications(run_dir: Path | None) -> dict:
    """The checks ShipLoop itself ran and recorded (tests/<action>-verify<N>.md), case-agnostic.

    ``could_not_run`` counts the attempts where no command reached a verdict
    about the product (it timed out, could not start, or was skipped on budget).
    Those refuse their stage without being evidence against it, so a run with
    any of them is reporting an environment problem, not a product one.
    ``red`` counts the records in which a command ran red (a run whose own status is `red`): a test-red record, or a
    test-author probe, passes because red is what it accepts, so ``passed`` includes it. What ran is counted, not what
    the record expected: a probe accepts red or passed, and one that ran green is a green pass.
    """
    records = sorted(run_dir.rglob("*-verify*.md")) if run_dir and run_dir.is_dir() else []
    passed = commands = could_not_run = red = 0
    for path in records:
        text = path.read_text(errors="replace")
        passed += bool(re.search(r'"passed"\s*:\s*true', text))
        could_not_run += bool(re.search(r'"disposition"\s*:\s*"could-not-run"', text))
        red += bool(re.search(r'"status"\s*:\s*"red"', text))
        commands += len(re.findall(r'"command"\s*:', text))
    return {"records": len(records), "passed": passed, "could_not_run": could_not_run, "commands": commands, "red": red}


def current_stage(state: dict) -> str | None:
    """The stage ShipLoop's state names, with a Work Item's inner loop resolved to its own stage.

    While a work item is built the run state's stage is the navigator's pseudo-label
    ``inner-loop``; the stage the run is actually in is the item's.
    """
    stage = state.get("stage")
    if stage != "inner-loop":
        return stage if isinstance(stage, str) else None
    loops, items, index = state.get("inner_loops"), state.get("work_items"), state.get("work_index")
    if not (isinstance(loops, dict) and isinstance(items, list) and isinstance(index, int)):
        return None
    if not 0 <= index < len(items) or not isinstance(items[index], dict):
        return None
    record = loops.get(items[index].get("id"))
    inner = record.get("stage") if isinstance(record, dict) else None
    return inner if isinstance(inner, str) else None


def pending_stage(state: dict) -> str | None:
    """The stage ShipLoop was on when the run stopped without accepting it, if any.

    A run left active, paused or halted stopped somewhere, and that stage is exactly the
    one an attrition question is about, so it must not be dropped. A blocked run whose
    last accepted action is that stage's own ``blocked`` result left nothing unaccepted:
    the model reported the block and ShipLoop recorded it, which is the opposite of a
    host that died mid-stage.
    """
    if state.get("status") in (None, "done"):
        return None
    stage = current_stage(state)
    history = state.get("history")
    last = history[-1] if isinstance(history, list) and history and isinstance(history[-1], dict) else {}
    if stage is not None and last.get("stage") == stage and last.get("outcome") == "blocked":
        return None
    return stage


def _timed(turns: list[dict]) -> bool:
    """Whether any turn carries a runner time, which stage windows need."""
    return any(x["t"] is not None for x in turns)


def stage_windows(accepted: list[dict], stamps: dict, pending: str | None = None) -> list[tuple | None]:
    """The time window of each row ``per_stage`` reports, in the same order: (after, until, since) or None.

    A stage's events are the ones with after < t <= until; ``since`` is where its seconds start. None marks a
    row whose timing is unavailable: no runner timeline, an action ShipLoop could not stamp, one accepted before
    the host's first event (a seeded run records its early stages itself, before the host starts), or the stage
    after an unstamped one, whose lower boundary is unknown. The stage the run stopped in without accepting
    (``pending``) runs to the newest event of any kind. One implementation: the per-stage counts and the Codex
    rollout reader both join their records to these windows.
    """
    rows = len(accepted) + bool(pending)
    if not stamps:
        return [None] * rows
    start = min(stamps.values())
    windows: list[tuple | None] = []
    previous, since = start - 1, start  # the first stamped event belongs to the first stage
    gap = False  # the preceding action had no stamp, so this row's lower boundary is unknown
    for item in accepted:
        if item.get("t") is None:
            windows.append(None)
            gap = True
        elif item["t"] < start:
            # Accepted before the host's first event: the harness seeded it, so no host work
            # was done in it. Its stamp is neither a duration nor a boundary for the next stage.
            windows.append(None)
        elif gap:
            # Its window also covers the unstamped action before it, so attributing
            # the whole window here would overstate this stage. Attribution resumes
            # from this known boundary.
            windows.append(None)
            previous = since = item["t"]
            gap = False
        else:
            windows.append((previous, item["t"], since))
            previous = since = item["t"]
    if pending:
        # The last acceptance with no stamp leaves its work and this stage's indistinguishable. The newest event of
        # any kind bounds the window, so a host that reports no per-turn events still shows the time and tool calls.
        windows.append(None if gap else (previous, max(max(stamps.values()), since), since))
    return windows


def per_stage(accepted: list[dict], turns: list[dict], calls: dict, stamps: dict,
              pending: str | None = None, unmeasured: dict | None = None, context_window: int | None = None) -> list[dict]:
    """Turns, tool calls and time between one accepted action and the next.

    Needs the runner's timeline; without it only the order and outcome are known.
    An action ShipLoop could not stamp reports ``timing: "unavailable"`` rather
    than a zero-length window, and so does an action accepted before the host's
    first event (see ``stage_windows``). When the run stopped without accepting its
    current stage, a final ``incomplete`` row carries the work after the last
    acceptance, so the stage a run died in is still attributed, whatever the host
    reports.

    A counter the host does not report (``unmeasured`` names it, or a stage
    count that needs per-call usage when the host has none) is ``None`` in the
    row, never 0.

    Where the turns carry a ``call`` flag (Claude: the first event of a message; Grok: each usage event) a timed row that
    holds at least one event also has ``context`` {calls, peak, peakPct}, the shape Codex's rollouts give: the model calls
    that began in the window, the largest input side any of its events reported, and that peak as a percentage of
    ``context_window`` (None when none was reported). A stage with no event has none: nothing was measured there.
    ``turns`` keeps counting events, and a call after the last accepted stage is in no row.

    Limits, not fixed: engine stamps are whole seconds (truncated) while runner times
    carry milliseconds, so the turn that submits a stage's result lands in the next
    stage about a third of the time (stage turns are good to about one per boundary);
    seconds are wall clock and include any interruption gap (a resume, a sleep, a
    credit stop); and an engine that recreated a lost timeline.json gives every
    historical action one stamp, which no check here can tell from a real one.

    No cost is apportioned here: a per-stage share of one total, divided by turn
    count, moves when prices or unrelated work move, so it would not measure the
    stage. Total cost stays whole-run.
    """
    unmeasured = set(unmeasured or ())
    if not _timed(turns):
        unmeasured.add("stage_turns")

    def counted(window: list[dict], tools: list) -> dict:
        return {"turns": None if "stage_turns" in unmeasured else len(window), "tool_calls": len(tools)}

    labels = [(a["stage"], a.get("outcome")) for a in accepted] + ([(pending, None)] if pending else [])
    rows = []
    for index, ((stage, outcome), window) in enumerate(zip(labels, stage_windows(accepted, stamps, pending))):
        base = {"stage": stage, "outcome": outcome, **({"incomplete": True} if index >= len(accepted) else {})}
        if window is None:
            rows.append({**base, "timing": "unavailable"})
            continue
        after, until, since = window
        events = [x for x in turns if x["t"] is not None and after < x["t"] <= until]
        tools = [c for c in calls.values() if c["t"] is not None and after < c["t"] <= until]
        row = {**base, "seconds": round(until - since, 1), **counted(events, tools)}
        if events and any("call" in x for x in turns):  # a stage with no event measured nothing: no context, not 0 calls
            peak = max((x["input"] for x in events if x["input"] is not None), default=None)
            row["context"] = {"calls": sum(bool(x.get("call")) for x in events), "peak": peak,
                              "peakPct": rollouts.share(peak, context_window)}
        rows.append(row)
    return rows


def money(value) -> str:
    """A cost for a printed line; a host that reports none has an unknown cost, never $0."""
    return "not reported" if value is None else f"${value}"


def cost_text(run_metrics: dict) -> str:
    """The cost for a printed line, saying so when sessions that never reported make it a lower bound.

    A cost that is unknown has nothing for a lower bound to bound, so it says only that it is not reported.
    """
    cost, never = run_metrics.get("cost_usd"), run_metrics.get("unreported_sessions") or 0
    return money(cost) + (f" (lower bound: {never} session(s) never reported)" if never and cost is not None else "")


def turns_text(run_metrics: dict) -> str:
    """The whole-run turns for a printed line: 'not reported' when nothing reported a count, a lower bound when a session never did."""
    turns = run_metrics.get("turns")
    if turns is None:
        return "not reported"
    return f"{turns} (lower bound)" if run_metrics.get("unreported_sessions") else str(turns)


def count(run_metrics: dict, name: str) -> int | None:
    """How many of a detected thing (a list in the metrics), or None when the host cannot show it.

    A counter that is already a number in the metrics (compactions, truncated outputs) is None there when unmeasured.
    """
    value = run_metrics.get(name)
    if name in (run_metrics.get("unmeasured") or {}) or value is None:
        return None
    return len(value) if isinstance(value, (list, dict)) else value


def stage_text(row: dict) -> str:
    """One stage row for a printed line: turns and minutes where measured, else what is."""
    if row.get("seconds") is None:
        return str(row["stage"])
    minutes = f"{row['seconds'] / 60:.1f}m"
    return f"{row['stage']} {row['turns']}t/{minutes}" if row.get("turns") is not None else f"{row['stage']} {minutes}"


def _min(seconds: float) -> str:
    return f"{seconds / 60:.1f}"


def planning_text(plan: dict) -> str:
    """The planning block as one printed line: the window on both clocks, the Improve share and the window's output tokens."""
    window = plan["window"]
    if window["seconds"] is None:
        return "planning window not measured: " + plan["unmeasured"]["window"]
    clocks = f"{_min(window['seconds'])} min engine" + (
        f" / {_min(window['host_seconds'])} min host" if window["host_seconds"] is not None else "")
    parts = [f"planning window {'closed at test-spec' if window['closed'] else 'open through ' + str(window['through'])}: {clocks}"]
    improve = plan["improve"]
    if improve and improve["seconds"] is not None and plan["producer_seconds"] is not None:
        parts.append(f"Improve {_min(improve['seconds'])} min in {improve['children']} "
                     f"{'child' if improve['children'] == 1 else 'children'}, other {_min(plan['producer_seconds'])} min")
    else:
        parts.append("Improve not measured")
    tokens = plan["tokens"]
    if "output" in tokens:
        reasoning = tokens.get("reasoning")
        share = f"{round(100 * reasoning / tokens['output'])}% reasoning, " if reasoning is not None and tokens["output"] else ""
        parts.append(f"output tokens {tokens['output']:,} ({share}{tokens['clock']} clock)")
    else:
        parts.append("output tokens not measured")
    return "; ".join(parts)


def tool_use_text(use: dict) -> str:
    """The `tool_use` block as one printed line, saying that model glue does not count the ShipLoop calls in the scripts."""
    mix = ", ".join(f"{name} {n}" for name, n in sorted(use["by_tool"].items(), key=lambda item: (-item[1], item[0])))
    scripts = sorted(use["scratch_scripts"], key=lambda s: (-s["runs"], s["path"]))
    made = ", ".join(f"{Path(s['path']).name} {plural(s['runs'], 'run')}" + (" (wraps ShipLoop)" if s["wraps_shiploop"] else "")
                     for s in scripts)
    packets = use["packets"]
    read, disk = packets["read"], packets["on_disk"]
    replies = packets["printed"]["replies"]
    return (f"tool use (main thread): {plural(use['calls'], 'call')} ({mix or 'none'}), {use['result_chars']:,} result chars; "
            + (f"scripts the model wrote and ran: {made} (their ShipLoop calls are not counted in model glue)" if made
               else "no script the model wrote was run")
            + f"; packets: {replies} printed packet {'reply' if replies == 1 else 'replies'} ({packets['printed']['chars']:,} chars), "
              f"{plural(len(read['read_tool']), 'packet Read')} ({sum(r['whole'] for r in read['read_tool'])} whole), "
              f"{plural(read['shell']['calls'], 'shell command')} on packets ({read['shell']['chars']:,} chars), "
            + ("none on disk" if disk is None else f"{plural(disk['files'], 'packet file')} on disk ({disk['bytes']:,} bytes)"))


def summary_lines(metrics: dict, top: int = 5) -> list[str]:
    """A few lines for the printed report: the costliest stages and the problems."""

    def shown(name: str) -> str:
        found = count(metrics, name)
        return "not measured" if found is None else str(found)

    checks = metrics["script_verifications"]
    notes = ([f"{checks['could_not_run']} could not run"] if checks.get("could_not_run") else []) \
        + ([f"{checks['red']} ran red"] if checks.get("red") else [])
    lines = [f"turns {turns_text(metrics)}, cost {cost_text(metrics)}, sessions {len(metrics['sessions'])} "
             f"({', '.join(str(s['stop']) for s in metrics['sessions']) or 'none ended'}), "
             f"compactions {shown('compactions')}, truncated outputs {shown('truncated_outputs')}, "
             f"cancelled tool calls {shown('cancelled_tool_calls')}, "
             f"ShipLoop command failures {shown('shiploop_failures')}, "
             f"script verifications {metrics['script_verifications']['passed']}/{metrics['script_verifications']['records']} passed"
             + (f" ({', '.join(notes)})" if notes else "") + ", "
             f"model glue {shown('model_glue')}, asked a person {len(metrics['asked_user'])}, "
             f"Improve children {metrics['improve_children']}"
             + (f" ({metrics['improve_reviews']['passes']} review passes, at most "
                f"{metrics['improve_reviews']['max_passes']} in one child)"
                if metrics.get("improve_reviews", {}).get("passes") else "")]
    if metrics.get("planning"):
        lines.append(planning_text(metrics["planning"]))
    if metrics.get("tool_use"):
        lines.append(tool_use_text(metrics["tool_use"]))
    story = metrics.get("narrative") or {}
    if story.get("emitted") or story.get("results"):
        lines.append(f"narrative shown {story['shown']}/{story['emitted']} (verbatim {story['verbatim']})"
                     + (f", skipped at {', '.join(str(s) for s in story['skipped'][:5])}" if story["skipped"] else "")
                     + f"; headlines {story['with_headline']}/{story['results']} results")
    timed = [s for s in metrics["stages"] if s.get("seconds") is not None]
    if timed:
        # Turns rank the stages where the host reports them; otherwise minutes do, and the line says so.
        by_turns = all(s.get("turns") is not None for s in timed)
        costly = sorted(timed, key=lambda s: s["turns"] if by_turns else s["seconds"], reverse=True)[:top]
        lines.append("costliest stages: " + ", ".join(stage_text(s) for s in costly)
                     + ("" if by_turns else " (by minutes: this host reports no per-stage turns)"))
    return lines
