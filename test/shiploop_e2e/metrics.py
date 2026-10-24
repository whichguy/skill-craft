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
import math
import os
from pathlib import Path
import re

import glossary
import rollouts
import runrecord
import sessionlog

# The prefix of the summary ShipLoop itself records for a stage not applicable to a work item (shiploop_item_scope.NOT_APPLICABLE;
# a test pins the two equal). The narrative reader and fidelity.py both key on it.
NOT_APPLICABLE = "Not applicable to this item"
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


# The replies counters.py reads (the `packets` and `commits` blocks): a ShipLoop packet head, or a line ShipLoop printed to announce
# a commit it made (`improve-commit`, a work item's commit). ToolLog keeps the text of those replies and no other; counters.py
# holds the patterns that read them, and its test pins that each is covered here.
# A coarse filter: which replies counters.py reads. The precise patterns (counters.IMPROVE_COMMITTED, counters.ITEM_COMMITTED) stay in
# counters.py, so a reworded announcement (release 1.27 reworded the work item's) changes one pattern there, not a second copy here.
KEPT_REPLY = re.compile(r"ShipLoop navigator \||Committed this review's changes as |ShipLoop committed \S+'s ")


# Named ShipLoop refusal gates (run-insights gate_counts), each a regex read against a refusal's own first line --
# the same text ``failure_line`` keeps in ``shiploop_failures[i]["line"]``, cut to 200 characters, so a signature
# must sit inside that budget (checked against two live runs: chess-sf-full-9e52e8, 13 refusals, and
# chess-sf-full-05fe25b, 5 refusals -- every one of those 18 lines matched a row below, none fell to "other").
# Read from the gates' own refusal text: shiploop_navigator.py (handoff faults section 3115-3219, length limits
# 2998-3027, record fields 2626-2658), shiploop_test_loop.py (the base run, 1751), shiploop_mutation.py (409),
# shiploop_concerns.py (56-150), shiploop_assumptions.py (52-142), shiploop_expectations.py (339-399) and
# shiploop_knowledge_home.py (317). A line matching no row counts under "other". New gates are one line each,
# with no other reader to update; a gate not yet seeded (its refusal text not read here) stays a commented
# placeholder below rather than an empty or guessed pattern.
GATE_SIGNATURES: dict[str, re.Pattern] = {
    # Consumer hand-off faults (_handoff_fault / _Fault, shiploop_navigator.py ~3151-3219): a done result's
    # follows, assumptions, test_cases, step notes or lessons the next stage cannot use.
    "handoff_placeholders": re.compile(r"Replace placeholders in |that has real values,"),
    "handoff_follows": re.compile(r"follows is a list of the R-<n> and AD-<n>|Add follows to \S|Fix the follows IDs in \S"),
    # "Fix the consumers" is the wording before run-5 batch R3 (2026-10-24), kept so older runs still classify.
    "handoff_open_items": re.compile(r"Add assumptions to \S|Fix the (?:due stages|consumers) in \S|Fix the evidence in \S"),
    "handoff_test_cases": re.compile(r"Not listed by a focused command of|Add test_cases to \S|Add the missing cases to \S|"
                                     r"Fix the case IDs in \S|Fix the case criteria in \S|Fix case requirements in \S"),
    "handoff_step_notes": re.compile(r"Add (?:learned and decisions|learned|decisions) to \S|Fix learned_from in \S"),
    "handoff_lessons": re.compile(r"Add lessons to \S"),
    # The step plan's or run's written spec diverged from HEAD plus this step's acceptance lines (shiploop_navigator.py).
    "spec_writeback": re.compile(r"Restore \S*spec\.md to what HEAD holds"),
    # A living-file entry (R-<n>/AD-<n>) went missing from docs/shiploop (shiploop_knowledge_home.py:317).
    "knowledge_gate": re.compile(r"Restore the lost "),
    # A packet-printed field (criteria, concern rows, a step's task or check, a work item's context) is over the
    # character budget the packet prints it whole at (shiploop_navigator.py:2998-3027, shiploop_concerns.py:109).
    "producer_limits": re.compile(r"characters(?: together)?; the limit is"),
    # red_na / retired_tests record-field shape (shiploop_navigator.py:2626-2658).
    "record_fields": re.compile(r"is a non-empty list of \{|entries each need "),
    # concerns shape and coverage (shiploop_concerns.py).
    "concerns_gate": re.compile(r"concern rows are|concerns is (?:an object|a list)|unknown concern|concern \S+ is "
                                r"(?:listed|mapped) twice|concerns names items that are not in work_items|no step "
                                r"delivers|concerns maps concerns the plan does not give"),
    # An open plan assumption's due_item and an expectation's "from" must name each other both ways
    # (shiploop_expectations.py:396-399).
    "assumptions_due_item": re.compile(r"expectations cite from .+, which is not an open plan assumption|"
                                       r"open plan assumptions .+ name .+ as (?:due_item|consumer)"),
    # Open-item (assumptions) record shape (shiploop_assumptions.py).
    "assumptions_gate": re.compile(r"assumption \S+ is listed twice|assumptions is a list of"),
    # Expectations: a step's expectations must list every changed path and the path's presence on the item's lint
    # base must match the expectation's state (shiploop_expectations.py:339-390).
    "expectations_gate": re.compile(r"must list expectations: the facts its steps build on|names steps the result "
                                    r"does not list|have no expectation listing them in paths|needs an absent "
                                    r"expectation\.|needs a works or broken expectation\."),
    # Improve stage misuse: --check-only has no draft to preview there (shiploop_navigator.py).
    "improve_checkonly": re.compile(r"the Improve stage has no draft to check"),
    # improve-pass gates: no bound Improve stage, the review loop already ended or is not active, the improve
    # skill was not invoked, or the review file is missing or incomplete (shiploop_navigator.py:8095-8149).
    "improve_pass": re.compile(r"Write this pass's review to |This review loop has already ended|No active review "
                               r"loop to record a pass|Run the improve skill on this .* result first|\(missing or "
                               r"invalid:"),
    # Improve ended on an unchanged trivial pass, but the worktree moved since the review was bound (shiploop_navigator.py:4232).
    "improve_stale_files": re.compile(r"ended on one unchanged trivial pass, but these files changed"),
    # complete --check-only replays the base run's own refusal (shiploop_navigator.py:4075).
    "check_only_base_run": re.compile(r"ShipLoop check-only: the base run would refuse this result"),
    # The focused/regression commands on the item's base are not all passing (shiploop_test_loop.py:1751).
    "base_run_not_done": re.compile(r"ShipLoop base run: test is not done"),
    # A mutation a focused test should have caught slipped through (shiploop_mutation.py:409).
    "mutation_not_done": re.compile(r"ShipLoop mutation check: test is not done"),
    # complete expected a model-written result file that was never written (shiploop_navigator.py:7714).
    "missing_result_file": re.compile(r"no result file at "),
    # Until Loop receipt checks for an inner stage's loop (shiploop_loops.py:275-767). The receipt was called the
    # "terminal packet" until R4 of the run-5 batch (2026-10-24); both texts match, so runs 3 and 4 still classify.
    "loop_receipt": re.compile(r"a loop receipt needs an action id|is not the current inner action|the Until Loop "
                               r"(?:terminal packet|receipt) must be a JSON object|the run is not in an inner stage, so "
                               r"it has no stage loop"),
    # A focused command whose every test ID an earlier item's step plan made focused (run-4 quality Q2,
    # shiploop_navigator.py _check_focused_ids_new).
    "focused_ids_new": re.compile(r"step plan already made focused: it tests an earlier item's behaviour"),
    # A focused command that starts with a file guard or a printed path, which fakes RED (run-5 batch F2,
    # shiploop_navigator.py _check_focused_guards).
    "focused_guard": re.compile(r"checks for a file or prints a path before its tests run"),
    # The test layers (run-5 batch F1, shiploop_test_layers.py and shiploop_navigator.py _check_submitted_layers):
    # the rows' shape and rules, an item's own rows, and the printed size.
    "test_layers": re.compile(r"lists test_layers: one row per|test_layers (?:repeats|gives|marks a unit|is a list of|"
                              r"and targets print as)|test_layers\[\d+\]|the run recorded no test layers"),
    # Each step-plan criterion's confirm (F1).
    "confirm": re.compile(r"each criterion says confirm:|are inspected, but name no test_layers row|are executed, "
                          r"but every command naming them only searches text|'s confirm is one of"),
    # Prepare's proof that each prerequisite harness runs (F1).
    "harness_runs": re.compile(r"lists harness_runs|harness_runs (?:has no run|is a list of|evidence)|"
                               r"harness_runs\[\d+\]"),
    # Where the tests run, and how a test still fails on an item's base there (F1), and each command's target (F3).
    "targets": re.compile(r"lists targets: where the tests run|targets is a list of|targets\[\d+\]|which is no "
                          r"test-strategy targets row|so each focused or regression command names, in target"),
    # The spec's primary requirements (run-5 batch F6, shiploop_primary.py check_spec and canonical).
    "primary": re.compile(r"a done spec result lists primary:|primary (?:lists (?:at least|an ID)|still holds the "
                          r"template|names |is a list of the R-<n>|is allowed only)"),
    # An unverified row's requirement (F6: shiploop_unverified.py's ID shape, shiploop_primary.py's living-spec entry).
    "unverified_requirement": re.compile(r"unverified\[\d+\]\.requirement .+? (?:is not one requirement ID|has no "
                                         r"current entry in)"),
    # A primary requirement's unverified outcome whose lower_layer_check names no test ShipLoop saw pass for it (F6).
    "lower_layer_check": re.compile(r"a primary requirement \(spec primary\), and its lower_layer_check names no test"),
    # An Improve commit that changes code without the Regression test line it owes (F5, shiploop_navigator.py
    # _regression_refusal). F4's entry_points and stand_in_rejected were dropped by the owner (2026-10-24).
    "improve_regression_test": re.compile(r"Add a line `Regression test: <"),
    # New gates land as one row each, read from the gate's own refusal text when it ships, never guessed.
}

# A ShipLoop CLI call's own ``--action=<id>`` (or ``--action <id>``), read from the expanded command text: the
# action a `complete`/`next`/`improve-*` call submits a result for, so a later accepted `complete` of the same id
# is what "caught" a refusal of it (gate_counts). Not every call names one (``next`` while nothing is bound).
ACTION_ARG = re.compile(r"--action[= ](\S+)")

# Test-quality dodges a gate does not refuse (dodge_counts), beside GATE_SIGNATURES: ported from the template
# experiments' evaluators E2 (e2_layers.source_search, inspected_ui) and E3 (e3_red._GUARD) on f14d4ec4, which showed
# these are only visible at full-run scale. Read from the run's accepted step-plan results and mutation records.
# A command whose every program only searches text (shiploop_test_layers.SEARCH_PROGRAMS, plus file tests and prints).
DODGE_SEARCH_PROGRAMS = frozenset(("grep", "egrep", "fgrep", "rg", "ag", "ack", "test", "[", "[[", "ls", "stat",
                                   "find", "printf", "echo", "cat"))
# A source file a grep can read in place of running it; documentation and data files are not code.
DODGE_CODE_FILE = re.compile(r"\.(?:c|cc|cjs|cls|cpp|cs|go|h|java|js|jsx|kt|mjs|php|py|rb|rs|sh|swift|trigger|ts|tsx|"
                             r"vue|svelte|html|css)\b|(?:^|[\s'\"=])(?:src|lib|app|force-app|public)/", re.I)
# A file-existence guard or a print-only path ahead of the tests, which fakes RED (e3_red._GUARD), or a require of a
# module checked for existence rather than run (require.resolve).
DODGE_GUARD = re.compile(r"(^|&&|\|\||;|\(|\bif|\bthen)\s*!?\s*(test\s+(!\s+)?-[efsd]\s|\[\[?\s+(!\s+)?-[efsd]\s|ls\s|"
                         r"stat\s|printf\s+'%s\\n'\s|echo\s+\S+\.\w+\s*(&&|;|$))|existsSync\(|require\.resolve\(")
# A criterion with no structured confirm whose text says it is confirmed by inspection (e2_layers._INSPECT/_EXEC).
DODGE_INSPECT = re.compile(r"\b(inspect\w*|inspection)\b", re.I)
DODGE_EXECUTED = re.compile(r"\b(exercised|executed|confirm: executed)\b", re.I)
RECORD_BLOCK = re.compile(r"```shiploop-state\n(.*?)\n```", re.S)
MUTATION_RECORD = re.compile(r"^(?P<action>.+)-mutation(?P<n>\d+)\.md$")


def failure_line(shown: str, limit: int | None = 200) -> str:
    """The line that names why a ShipLoop command was refused: its own, not the script's fixed trailer.

    Where no line but a trailer matches, the first trailer match is kept (what this recorded before). ``limit`` cuts the
    line for a printed or recorded row (200 characters); None keeps it whole, which is what two refusals are compared by.
    """
    lines = [ln for ln in shown.splitlines() if not MARKER.search(ln)]
    own = next((ln for ln in lines if (FAILURE_LINE.search(ln) or REFUSAL_LINE.search(ln))
                and not TRAILER_LINE.search(ln)), None)
    if own is None:
        own = next((ln for ln in lines if FAILURE_LINE.search(ln)), "")
    return own.strip() if limit is None else own.strip()[:limit]


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


def within(t: float, after: float, until: float) -> bool:
    """Whether an event at ``t`` belongs to the stage window (after, until]: a stage holds the event of its own acceptance stamp
    and not the stamp it started at (that one belongs to the stage before)."""
    return after < t <= until


def target_paths(arg: dict) -> list[str]:
    """The file paths a tool call names, each once and in the order it names them: the single target of Claude's and
    Grok's edit tools, and Codex's `paths` (its file_change repeats the first path as `target_file`)."""
    found: list[str] = []
    listed = arg.get("paths") if isinstance(arg.get("paths"), list) else []
    for value in (arg.get("target_file"), arg.get("file_path"), arg.get("path"), *listed):
        if isinstance(value, str) and value and value not in found:
            found.append(value)
    return found


def call_target(arg: dict) -> str:
    """The file a tool call names first (``target_paths``: Grok `target_file`, Claude `file_path`, a bare `path`, Codex's
    `paths`), or an empty string. ``ToolLog.call`` keeps it as a call's ``file``, and ``written_paths`` reads the same."""
    paths = target_paths(arg)
    return paths[0] if paths else ""


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
        # Read by fidelity.py: every tool call in the order the stream made it (``calls`` keeps one per id, and Codex numbers
        # its calls again in each session), and for each entry of ``failures`` the event it was found at and its whole first line.
        self.sequence: list[dict] = []
        self.failure_events: list[dict] = []
        self.failure_of: dict = {}  # call id -> its entry in ``failures``, so a window can count the failures of its own calls
        self.answered: set = set()  # call ids whose final result arrived: a failure is known only once the result is
        self.scripts: dict[str, dict] = {}  # path -> {body, wraps, bytes, runs, pattern}: the model-written scripts so far
        self.by_tool: dict[str, int] = {}  # Claude only below: what the model called, what came back, how it used packets
        self.result_chars = 0
        self.packets = {"printed": [0, 0], "shell": [0, 0], "read_tool": []}
        # Read by counters.py, on every host: the replies (KEPT_REPLY) of calls, each call's first result only, with whether the
        # call named a packet file (a model reading the file is not ShipLoop printing a head) and the line it is at in events.jsonl.
        self.replies: list[dict] = []
        # Read by gate_counts: every call that named a ShipLoop verb (SHIPLOOP_COMMAND), in stream order, with the
        # action id its ``--action=`` named (None when it named none) and whether its own result was accepted (None
        # until the result arrives). Never exported as part of ``failures``, whose shape test/shiploop-e2e.test.py
        # pins exactly.
        self.action_log: list[dict] = []
        # ``failures``'s own call id, same order and length as ``failures``: a second, internal list rather than a
        # new key on each failure dict, which other readers (progress.py, packets.py, run.py) take as {verb, exit, line}.
        self.failure_call_ids: list = []

    def call(self, t, call_id, tool: str, arg: dict, event: int | None = None):
        """One tool call: a question put to a person, glue, a /tmp write, a path read or written, a script written.
        Returns the key it is kept under in ``calls`` (the call id, or a number for a call that had none).

        ``event`` is the call's line number in events.jsonl, kept in ``sequence`` so a listed fact can cite it."""
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
        paths = target_paths(arg)
        target = paths[0] if paths else ""  # call_target(arg), from the one list
        self.sequence.append({"event": event, "t": t, "tool": tool, "command": command, "paths": paths})
        self.by_tool[tool] = self.by_tool.get(tool, 0) + 1
        key = call_id if call_id is not None else f"#{len(self.calls)}"
        self.calls[key] = {
            "t": t, "command": command, "expanded": expanded, "invoked": expanded + wrappers, "tool": tool,
            "packet": "/packets/" in expanded or "/packets/" in str(target or ""),
            "whole": "offset" not in arg and "limit" not in arg, "file": str(target or "")}
        verb = SHIPLOOP_COMMAND.search(self.calls[key]["invoked"])
        if verb:
            action = ACTION_ARG.search(self.calls[key]["invoked"])
            self.action_log.append({"call_id": call_id, "t": t, "verb": verb.group("verb"),
                                    "action": action.group(1) if action else None, "accepted": None})
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

    def feed(self, event: dict, t, number: int | None = None) -> list:
        """One host event, read the one way for every host: the calls it starts and the results it carries.

        Claude's `tool_use` blocks, Grok's `tool_call` events and Codex's after the translator start calls; Claude's
        `tool_result` blocks and Grok's final `tool_call_update` carry results. A running update (Grok repeats one, with a
        placeholder exit 0) and a cancelled one (a permission refusal, which ends the turn) are no result. The whole-run
        reading (``collect``, and through it fidelity.py's ``sequence`` and ``failure_events``) and a window
        (``reorientation``) all feed a log this way, so they cannot differ. ``number`` is the event's line in events.jsonl,
        passed on as ``event`` to ``call`` and ``result``. Returns the keys, in ``calls``, of the calls this event started.
        """
        started = [self.call(t, call_id, tool, arg, event=number) for call_id, tool, arg in tool_call_events(event)]
        kind = event.get("type")
        if kind == "user":  # Claude: the tool_result blocks, whose text may begin with the host's `Exit code N`
            for call_id, shown in tool_results(event):
                self.measure(call_id, shown)
                self.result(call_id, shown, claude_exit(shown), event=number)
        elif kind == "tool_call_update" and isinstance(event.get("rawOutput"), dict) and not cancelled_update(event) \
                and event.get("status") != "in_progress":
            for call_id, shown in tool_results(event):
                self.result(call_id, shown, event["rawOutput"].get("exit_code"), event=number)
        return started

    def result(self, call_id, shown: str, code: int | None, event: int | None = None) -> None:
        """One tool result, with the exit code the host showed (None when it showed none) and its line in events.jsonl."""
        first = call_id not in self.answered  # Grok repeats an update for one call; Codex's reused ids were discarded in ``call``
        self.answered.add(call_id)
        refusal = REFUSAL_LINE.search(shown)
        call = self.calls.get(call_id) or {}
        if first and KEPT_REPLY.search(shown):
            self.replies.append({"event": event, "packet": bool(call.get("packet")), "text": shown})
        exited = code not in (None, 0) and SHIPLOOP_COMMAND.search(call.get("invoked", ""))
        if first:  # gate_counts: this call's own result, accepted when it is neither a refusal nor a failed exit
            for entry in reversed(self.action_log):
                if entry["call_id"] == call_id:
                    entry["accepted"] = not (refusal or exited)
                    break
        if call_id in self.failed or not (refusal or exited):
            return
        self.failed.add(call_id)
        verb = SHIPLOOP_COMMAND.search(call.get("expanded", ""))
        # From the refusal's own line on: the model's shell errors before it are not why ShipLoop refused.
        source = shown[refusal.start():] if refusal else shown
        self.failures.append({"verb": verb.group("verb") if verb else "unknown", "exit": code, "line": failure_line(source)})
        self.failure_events.append({"event": event, "line": failure_line(source, None)})
        self.failure_of[call_id] = self.failures[-1]
        self.failure_call_ids.append(call_id)


def refusal_gate(line: str) -> str:
    """The named gate a ShipLoop refusal's own first line matches (GATE_SIGNATURES, first row that matches wins),
    or "other" for a line no row's signature covers."""
    return next((name for name, pattern in GATE_SIGNATURES.items() if pattern.search(line)), "other")


def nomenclature(tools: ToolLog, path: Path | None = None) -> dict:
    """Retired ShipLoop terms in what ShipLoop printed to this run (E2E SPEC S-16, added 2026-10-24).

    For each retired term of the glossary's block (``glossary.retired_terms``): how many of the run's kept ShipLoop
    replies (packets, printed or read, and commit replies) and refusal first lines hold it, and the first such line
    with its events.jsonl line.  A record beside the verdicts, never a verdict.  The glossary read is the checkout's, so
    an older run is held to today's retired terms; ``glossary_sha256`` names the version read.  ``unmeasured`` says why
    when the glossary cannot be read.
    """
    source = path or glossary.GLOSSARY
    try:
        terms, digest = glossary.retired_terms(source), glossary.digest(source)
    except (OSError, ValueError) as exc:
        return {"unmeasured": str(exc)[:200]}
    texts = [(reply.get("event"), str(reply.get("text") or "")) for reply in tools.replies]
    texts += [(found.get("event"), str(found.get("line") or "")) for found in tools.failure_events]
    retired: dict[str, dict] = {}
    for event, text in texts:
        for term in terms:
            match = term["regex"].search(text)
            if not match:
                continue
            row = retired.setdefault(term["retired"], {"use": term["use"], "texts": 0, "first": None})
            row["texts"] += 1
            if row["first"] is None:
                start = text.rfind("\n", 0, match.start()) + 1
                end = text.find("\n", match.end())
                row["first"] = {"event": event, "line": text[start:end if end >= 0 else None].strip()[:200]}
    return {"glossary_sha256": digest, "texts_scanned": len(texts), "retired": retired}


def nomenclature_text(record: dict) -> str:
    """``term N`` per retired term the run's ShipLoop output held, most frequent first."""
    rows = sorted((record.get("retired") or {}).items(), key=lambda item: (-item[1]["texts"], item[0]))
    return ", ".join(f"{name} {row['texts']}" for name, row in rows)


def gate_counts(tools: ToolLog) -> dict[str, dict[str, int]]:
    """Per gate: how many of this run's ShipLoop refusals it fired, and how many of those it caught.

    ``fired`` is how many of ``tools.failures`` classify under the gate (``refusal_gate`` on the refusal's own
    line); a refusal naming no row counts under "other", so new gates become visible there before they are seeded.
    ``caught`` is how many of a gate's refusals were followed, later in the stream, by an accepted `complete` of
    the same action id (the refusing call's own ``--action=``, read by ``tools.action_log``); when the id cannot
    be read, the next `complete` call afterwards (of any action) stands in, as the owner's fallback rule says.
    A refusal whose own call cannot be found in ``action_log`` (should not happen: every refused call named a
    ShipLoop verb) is fired but never caught.
    """
    index_by_call: dict = {}
    for position, entry in enumerate(tools.action_log):
        index_by_call[entry["call_id"]] = position  # last occurrence: a reused id (Codex) is this call, not an older one
    counts: dict[str, dict[str, int]] = {}
    for call_id, failure in zip(tools.failure_call_ids, tools.failures):
        row = counts.setdefault(refusal_gate(failure["line"]), {"fired": 0, "caught": 0})
        row["fired"] += 1
        start = index_by_call.get(call_id)
        if start is None:
            continue
        action = tools.action_log[start].get("action")
        later = [entry for entry in tools.action_log[start + 1:] if entry.get("verb") == "complete"]
        if action is not None:
            caught = any(entry.get("action") == action and entry.get("accepted") for entry in later)
        else:
            caught = bool(later) and bool(later[0].get("accepted"))
        row["caught"] += int(caught)
    return counts


def _record(path: Path) -> dict | None:
    """The shiploop-state JSON block of one ShipLoop record file, or None."""
    try:
        found = RECORD_BLOCK.search(path.read_text(errors="replace"))
        return json.loads(found.group(1)) if found else None
    except (OSError, ValueError):
        return None


def search_only_command(command: str) -> bool:
    """Whether every program ``command`` runs only searches or prints text (no runner, interpreter or deploy)."""
    programs = []
    for segment in re.split(r"&&|\|\||[;|\n]", command):
        words = segment.strip().lstrip("(").split()
        while words and (words[0] in ("!", "env", "command", "exec", "time", "if", "then", "else", "fi")
                         or re.match(r"^\w+=", words[0])):
            words = words[1:]
        if words and words[0] != "cd":
            programs.append(words[0].rsplit("/", 1)[-1].lower())
    return bool(programs) and all(program in DODGE_SEARCH_PROGRAMS for program in programs)


def guarded_command(command: str) -> bool:
    """Whether ``command`` holds a file-existence guard or a print-only path that can fake RED."""
    return bool(DODGE_GUARD.search(command))


def plan_dodges(plan: dict) -> dict:
    """One step plan's dodges: grep-only checks on code files split by the confirm of the criteria they serve, guarded
    commands, and criteria confirmed by inspection.

    A check counts ``searched`` (context: a docstring or contract duty) when every criterion it names says confirm
    ``searched``; ``executed`` when one says executed; ``unmatched`` when it names no criterion (a step's proof, or a
    command with no criteria). Only ``executed`` is a dodge: a command naming no criterion confirms nothing, and a step's
    proof is followed by the item's real tests."""
    criteria = {str(c.get("id")): c for c in plan.get("criteria") or [] if isinstance(c, dict)}
    rows = [(str(c.get("command") or ""), [str(i) for i in c.get("criteria") or ()], c.get("suite"))
            for c in plan.get("test_commands") or [] if isinstance(c, dict)]
    rows += [(str(s.get("proof") or s.get("check") or ""), [str(i) for i in s.get("criteria") or ()], "proof")
             for s in plan.get("steps") or [] if isinstance(s, dict)]
    grep = {"searched": [], "executed": [], "unmatched": []}
    seen = set()
    for command, ids, _suite in rows:
        if not command or command in seen or not search_only_command(command) or not DODGE_CODE_FILE.search(command):
            continue
        seen.add(command)
        confirms = {criteria[i].get("confirm") for i in ids if i in criteria}
        kind = "unmatched" if not confirms else "searched" if confirms == {"searched"} else "executed"
        grep[kind].append(command)
    guarded = sorted({command for command, _ids, suite in rows if suite == "focused" and guarded_command(command)})
    inspected = [cid for cid, c in criteria.items() if c.get("confirm") == "inspected" or (
        "confirm" not in c and DODGE_INSPECT.search(str(c.get("text") or ""))
        and not DODGE_EXECUTED.search(str(c.get("text") or "")))]
    return {"grep": grep, "guarded": guarded, "inspected": inspected}


def surviving_mutants(run_dir: Path | None) -> int | None:
    """Mutants that survived, from each action's last counted ``tests/<action>-mutation<N>.md``; None with no record."""
    folder = run_dir / "tests" if run_dir else None
    if folder is None or not folder.is_dir():
        return None
    last: dict[str, tuple[int, Path]] = {}
    for path in folder.glob("*-mutation*.md"):
        found = MUTATION_RECORD.match(path.name)
        if found and int(found["n"]) >= last.get(found["action"], (-1, path))[0]:
            last[found["action"]] = (int(found["n"]), path)
    if not last:
        return None
    return sum(int((_record(path) or {}).get("survived") or 0) for _n, path in last.values())


def dodge_counts(run_dir: Path | None) -> dict:
    """Run-level test-quality dodges (the template experiments E2/E3), counted over every accepted step-plan result.

    ``grep_executed`` (grep-only checks on code files serving an executed criterion; step-plan refuses these, so 0 shows
    the gate held), ``guarded`` (focused commands with a file guard) and ``surviving_mutants`` sum into ``dodges``.
    ``grep_searched`` (a docstring or contract duty) and ``grep_unmatched`` (no criterion, or a step's proof) are context;
    ``inspected`` (criteria confirmed by inspection) is its own count. ``surviving_mutants`` is None when the run wrote no
    mutation record. ``plans`` 0 means nothing was measured."""
    folder = run_dir / "results" if run_dir else None
    plans = []
    if folder is not None and folder.is_dir():
        for path in sorted(folder.glob("*.md")):
            record = _record(path)
            if isinstance(record, dict) and record.get("stage") == "step-plan" and isinstance(record.get("result"), dict):
                plans.append((record.get("action") or path.stem, plan_dodges(record["result"])))
    counts = {"plans": len(plans),
              "grep_searched": sum(len(p["grep"]["searched"]) for _a, p in plans),
              "grep_executed": sum(len(p["grep"]["executed"]) for _a, p in plans),
              "grep_unmatched": sum(len(p["grep"]["unmatched"]) for _a, p in plans),
              "guarded": sum(len(p["guarded"]) for _a, p in plans),
              "inspected": sum(len(p["inspected"]) for _a, p in plans),
              "surviving_mutants": surviving_mutants(run_dir)}
    counts["dodges"] = counts["grep_executed"] + counts["guarded"] + (counts["surviving_mutants"] or 0)
    counts["by_action"] = {action: p for action, p in plans
                           if any(p["grep"].values()) or p["guarded"] or p["inspected"]}
    return counts


def dodge_text(counts: dict) -> str:
    """``Test-quality dodges: N (...)`` for the printed report."""
    mutants = counts.get("surviving_mutants")
    return (f"Test-quality dodges: {counts['dodges']} over {plural(counts['plans'], 'step plan')} "
            f"(grep-only on code for an executed criterion {counts['grep_executed']}; guarded RED {counts['guarded']}; "
            f"surviving mutants " + ("none recorded" if mutants is None else str(mutants)) + "); "
            f"inspected criteria {counts['inspected']}; context: {counts['grep_searched']} searched greps, "
            f"{counts['grep_unmatched']} greps with no criterion")


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


# ShipLoop's four outcomes (run-insights plan N5, owner decision 10, 2026-10-18): done, blocked, send-back and add-work.
# `revise` became send-back and `replan` became add-work, and `repeat` was retired. A run recorded before keeps the old names
# in its state.md, and this harness grades those runs too, so a reader that counts an outcome accepts both names. Rows are
# copied as the run wrote them (a historical run's stage rows say `revise`); only a count folds the two names together.
SEND_BACK_OUTCOMES = ("send-back", "revise")
ADD_WORK_OUTCOMES = ("add-work", "replan")


def blocked_detail(state: dict) -> dict:
    """What the engine recorded when it blocked: the one reader of the blocked detail, over the parsed ``state.md``.

    Read from the accepted record of the last history action, and only while the engine is blocked and that action's
    outcome is blocked (a block that was answered leaves the last history entry blocked while the engine is active again, and
    reads as nothing). ``awaiting_kind`` is the kind of wait the blocked result asked for (answer or present: a person; service:
    an outside service), ``awaiting_no_default`` whether it stated why no recorded default would do (SPEC S-14; None when it
    awaits no one). ``blocked_by`` is who could unblock it (user, access or external) in a run recorded before the four outcomes,
    where a blocked result carried it beside ``awaiting``; a current blocked result has none (the engine refuses it), so it is
    None there. Each is None where the state holds no accepted blocked result (an old state): never a guess from the prose of
    ``status_reason``.
    """
    detail = {"blocked_by": None, "awaiting_kind": None, "awaiting_no_default": None}
    if not isinstance(state, dict):
        return detail
    history, accepted = state.get("history"), state.get("accepted")
    last = history[-1] if isinstance(history, list) and history and isinstance(history[-1], dict) else {}
    record = accepted.get(last.get("action")) if (state.get("status") == "blocked" and last.get("outcome") == "blocked"
                                                  and isinstance(accepted, dict)) else None
    if not isinstance(record, dict):
        return detail
    if isinstance(record.get("blocked_by"), str):
        detail["blocked_by"] = record["blocked_by"]
    awaiting = record.get("awaiting")
    if isinstance(awaiting, dict):
        if isinstance(awaiting.get("kind"), str):
            detail["awaiting_kind"] = awaiting["kind"]
        detail["awaiting_no_default"] = bool(str(awaiting.get("no_default") or "").strip())
    return detail


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

    A reviewed action's row also carries ``improve_action`` when state.md records its Improve stage's id
    (``improve_results[<action>]["improve_action"]``, set when the Improve stage's `complete` imports the review): that
    id, not the reviewed action's, is what the `complete` call that accepts the action names.
    """
    state = engine_state(run_dir) if state is None else state
    history = state.get("history")
    if not isinstance(history, list):
        return []
    stamps = acceptance_stamps(run_dir)
    improved = state.get("improve_results") if isinstance(state.get("improve_results"), dict) else {}
    rows = []
    for entry in history:
        if not isinstance(entry, dict):
            continue
        action = entry.get("action")
        row = {"stage": entry.get("stage") or "?", "outcome": entry.get("outcome"),
               "work_item": entry.get("workitem"), "action": action if isinstance(action, str) else None,
               "t": stamps.get(action) if isinstance(action, str) else None}
        record = improved.get(action) if isinstance(action, str) else None
        if isinstance(record, dict) and isinstance(record.get("improve_action"), str):
            row["improve_action"] = record["improve_action"]
        rows.append(row)
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
NO_SESSION_START = ("Grok's events mark no session start: its available_commands event is announced again inside a session "
                    "(314 of them for 2 end events on a recorded run), so a session that never reported cannot be counted from "
                    "the stream (model calls after the last end prove at least one did: unreported_sessions_at_least); cost "
                    "and turns are a lower bound")
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
    done, the owner's planning rule (S-10 carve-out, 2026-10-05); a `send-back` row (`revise` in an earlier run) does not close it. It is read on two
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


def init_build(event: dict) -> str | None:
    """The Claude Code build a session's ``system/init`` event names, None for any other event."""
    build = event.get("claude_code_version")
    return build if isinstance(build, str) and build else None


def claude_builds(path: Path) -> str | None:
    """The build(s) named by the init events of an events file, ', '-joined, None where it names none: the run's own record
    of the host build, for a run whose metrics did not keep it."""
    found = {init_build(event) for _number, event in events(path) if event.get("type") == "system"
             and event.get("subtype") == "init"}
    return ", ".join(sorted(b for b in found if b)) or None


def span(stamps) -> dict:
    """{started, ended}: the first and the last stamp of a run's stream (epoch seconds), from a timeline mapping (``timeline``)
    or from the path of a timeline.jsonl. The one span reader: the run's own span (metrics.json, result.json, the baseline row),
    the baseline report's rows and environment.overlap's neighbours.

    Defensive, so a span is never made up: only finite stamps count (NaN and infinity are not times), a line that does not
    parse is skipped (a growing file's half-written last line), and where the first stamp in line order is after the last, or
    no stamp can be read, or the file cannot be read, both are None: no readable span, which a caller names, never a negative
    or shorter one. For the runner's own timeline (appended in order) first and last are its earliest and latest stamps.
    """
    if not isinstance(stamps, dict):
        try:
            stamps = timeline(Path(stamps))
        except OSError:
            stamps = {}
    ordered = [stamps[line] for line in sorted(stamps)
               if isinstance(stamps[line], (int, float)) and not isinstance(stamps[line], bool) and math.isfinite(stamps[line])]
    if not ordered or ordered[0] > ordered[-1]:
        return {"started": None, "ended": None}
    return {"started": ordered[0], "ended": ordered[-1]}


def spans_overlap(a, b) -> bool:
    """Whether two (start, end) spans share time: they cross (each starts before the other ends), so spans that only touch do
    not, and an instant strictly inside the other span does. False when any end is unknown (a caller counts that as unknown).
    The one interval rule: the baseline report's count (run.span_overlaps) and environment.overlap both ask it."""
    if any(value is None for value in (*a, *b)):
        return False
    return a[0] < b[1] and b[0] < a[1]


def planning_seconds(planning: dict | None) -> float | None:
    """The planning window in seconds, from a ``planning`` block, only when it is closed and measured.

    An open window is not the planning time (it is still running) and one that could not be read is unknown: neither
    is ever 0. The one reader of the window's length, for the baseline row and for a report built from a saved folder.
    """
    window = (planning or {}).get("window") if isinstance(planning, dict) else None
    seconds = window.get("seconds") if isinstance(window, dict) and window.get("closed") else None
    return seconds if isinstance(seconds, (int, float)) and not isinstance(seconds, bool) else None


def planning_unmeasured(planning: dict | None) -> str | None:
    """Why ``planning_seconds`` is null, None when it is measured: the block's own reason for the window, else that it is
    still open, else that there is no block."""
    if planning_seconds(planning) is not None:
        return None
    block = planning if isinstance(planning, dict) else {}
    window = block.get("window") if isinstance(block.get("window"), dict) else {}
    reason = (block.get("unmeasured") or {}).get("window") if isinstance(block.get("unmeasured"), dict) else None
    if reason:
        return reason
    if window and not window.get("closed"):
        return f"the planning window is still open (through {window.get('through')})"
    return "the metrics hold no planning block"


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
# The ShipLoop verbs whose call can be the one that gets an action accepted. The Improve stage's `complete` (it names the Improve
# stage's id) accepts the action it reviews; `improve-complete` was the Improve child's finish before the Improve stage was an
# action of its own, and a saved run still holds it.
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
    `complete` call (`improve-complete` in a run of the older layout) that names it or its Improve stage, did not fail, began
    before its accept stamp's second ended and returned at or after the stamp. The stamp is whole-second truncated, so a cut at the stamp would lose the call (it starts
    after the truncated stamp) or keep the next one (it starts in the same second); a producer's `complete`
    that parks the action at its Improve stage returns long before the accept and is not the call. Both clocks are recorded: ``seconds`` to the call, on the runner's
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
    # The call that gets the action accepted names the action itself (a stage with no review) or its Improve stage.
    named = [target, row.get("improve_action")] if target else []
    pattern = (re.compile(r"(?<![\w-])(?:" + "|".join(re.escape(n) for n in named if isinstance(n, str)) + r")(?![\w-])")
               if target else None)
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
        for key in tools.feed(seen, t, line):
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
    """Whether a tool call runs a `complete` (or an older run's `improve-complete`) that names what ``pattern`` matches."""
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


# The eight sources context_window_rows tallies a window's result and output characters into. Order is the order a
# row's ``bytes`` and ``context_summary``'s totals report them, never read for meaning.
WINDOW_SOURCES = ("shiploop_packets", "shiploop_reads", "product_reads", "run_record_reads", "knowledge_reads",
                 "shell_output", "web", "model_text", "other")
# FILE_CLASSES names that are ShipLoop's own skill files (its scripts, references and cards): reading one fills the
# context with ShipLoop's own text, the same text shiploop_packets tallies when the CLI prints it instead.
SHIPLOOP_FILE_CLASSES = ("script", "reference", "entry_card", "improve_card", "adapter")
# FILE_CLASSES names that are the run's own written record (results, lint, tests, an Improve child's handoff and
# files): read back, these are what the run itself produced under its run directory, not knowledge or product source.
RUN_RECORD_FILE_CLASSES = ("run_file", "result_record", "handoff", "child_record")
WEB_TOOL = re.compile(r"web[ _]?search|web[ _]?fetch", re.I)


def _window_bytes_table() -> dict:
    return {name: 0 for name in WINDOW_SOURCES}


def window_source(tool: str, arg: dict, shown: str) -> str:
    """Which of the eight context_window_rows sources one tool result's characters belong to.

    Built on ``classify_call``'s own reading of the same call (a packet print or read, a ShipLoop script or
    reference, a run record, a knowledge file): a file-content tool (Read/Grep and their Grok names) that names none
    of those is a product read, any other shell result that named no ShipLoop/run/knowledge path is shell output, and
    a web-search tool is ``web``. ``other`` is what is left: a write, an edit, a directory listing, anything this
    call's own classification does not place.
    """
    if WEB_TOOL.search(tool):
        return "web"
    if tool == "get_command_or_subagent_output":  # Grok's read of a background command's own output
        return "shell_output"
    info = classify_call(tool, arg, shown)
    cls, bucket = info["cls"], info["bucket"]
    if bucket in ("packet_output", "shiploop_messages") or cls == "packet_file":
        return "shiploop_packets"
    if cls in SHIPLOOP_FILE_CLASSES:
        return "shiploop_reads"
    if cls in RUN_RECORD_FILE_CLASSES:
        return "run_record_reads"
    if cls == "knowledge":
        return "knowledge_reads"
    if info["read"] or tool in SEARCH_TOOLS:
        return "product_reads" if info["path"] else "other"
    if str(arg.get("command") or "").strip():
        return "shell_output"
    return "other"


def _window_top_label(tool: str, arg: dict) -> str:
    """A short label for one tool result in a context window's ``top`` list: the command, collapsed to one line, or
    the path it names, else the tool's own name."""
    command = str(arg.get("command") or "").strip()
    if command:
        return " ".join(command.split())[:80]
    return call_target(arg) or tool


def _context_boundaries(sessions: list[dict] | None, compaction_lines: list[int]) -> list[tuple[int, str]]:
    """Every line that starts a context window, in line order: line 0 (the stream's own start, kept even where a
    session or a compaction also marks it), each session ``sessionlog.read`` recorded (a run with no sessions.jsonl
    gives ``None``: then only compactions split the stream) and each compaction line. A line two kinds would mark
    keeps the first in this order, since line 0 is always the start of something and a session row is never a
    compaction's own line."""
    points: dict[int, str] = {0: "start"}
    for row in sessions or []:
        line = row.get("events_line")
        if isinstance(line, int):
            points.setdefault(line, "session")
    for line in compaction_lines:
        if isinstance(line, int):
            points.setdefault(line, "compaction")
    return sorted(points.items())


def _event_context_tokens(event: dict) -> int | None:
    """The context-token figure one event's own usage reports, Grok's per-call ``usage`` event or Claude's
    per-message snapshot, whichever shape the event carries; None for any other event or an unreported figure."""
    if event.get("type") == "usage":
        return context_tokens(event.get("usage"))
    if event.get("type") == "assistant":
        return context_tokens((event.get("message") or {}).get("usage"))
    return None


def _server_tool_round(event: dict) -> bool:
    """Whether one event is a Grok native (server-side) web search or page-open round: a request/response the model
    ran itself mid-turn, billed as input tokens but never shown to the client (its ``tool_call_update`` carries only
    ``action``/``id``/``status`` -- no ``content`` or ``output_for_prompt`` -- so it is already 0 result characters
    through ``result_text``). A turn can run several of these before its one ``usage`` event, and that event's input
    then sums every round's growing input, which is not the context at any single point (confirmed on a recorded
    run: a usage event after 9 such rounds reported context 498,847; the next ordinary usage event reported 136,051,
    up only ~25k from the 111,715 before the batch). So a round is counted (``server_tool_rounds``), but the usage
    event that follows one or more of them is never read for ``peak_tokens``."""
    raw = event.get("rawOutput")
    action = raw.get("action") if isinstance(raw, dict) else None
    return event.get("type") == "tool_call_update" and isinstance(action, dict) and action.get("type") in (
        "search", "open_page")


def context_window_rows(out: Path, run_dir: Path | None = None, *, stamps: dict | None = None,
                        accepted: list[dict] | None = None, pending: str | None = None,
                        sessions: list[dict] | None = None, compaction_lines: list[int] | None = None) -> list[dict]:
    """One row for every context window a run had: the span from the run's start, a recorded session start, or a
    compaction, to the next one of those or the end of the stream. Answers what filled the context between the
    compactions a live Grok run hits every few minutes -- ShipLoop's own printed packets, the scripts and references
    it reads, product source, the run's own record files, knowledge files, other shell output, web calls, or the
    model's own generated text -- so a packet-template redesign can be aimed at what is actually large.

    Boundaries: line 0, every row ``sessionlog.read`` recorded (``sessions`` None: a run from before sessions.jsonl,
    or one with none; then only compactions split the stream) and every compaction line (Grok's own
    ``auto_compact_completed``, the line numbers ``collect`` already finds for ``fresh_starts``; a run on a host that
    writes none is one open window). Each row: ``start``/``end`` (the runner's own stamps, None where it kept none for
    the window), ``minutes``, ``stages`` (every accepted stage whose own window, ``stage_windows``'s, overlaps this
    one, in the order it was accepted), ``peak_tokens`` (the largest per-call context figure any event in the window
    reported that is not a server round's own inflated usage event -- see ``_server_tool_round`` -- None where none
    qualified), ``server_tool_rounds`` (native web search/page-open rounds in the window: billed input, never
    context, counted by number and never added to ``bytes``), ``compacted`` (whether a compaction closes the window),
    ``bytes`` (characters of every tool result and of the model's own text, by ``window_source``) and ``top`` (its
    five largest single tool results). Never packet text or a tool result verbatim: counts and short labels only.

    Record-only, like ``fresh_starts``: nothing here is a verdict. ``accepted``, ``pending``, ``stamps`` and
    ``sessions`` let ``collect`` pass what it already read, so a caller that reads the run directory once is not read
    twice; a standalone caller (the CLI, a test, a recompute script) leaves them out and they are read here instead.
    """
    out = Path(out)
    path = out / "events.jsonl"
    if stamps is None:
        stamps = timeline(out / "timeline.jsonl")
    if accepted is None:
        state = engine_state(run_dir)
        accepted, pending = stage_results(run_dir, state), pending_stage(state)
    if sessions is None:
        sessions = sessionlog.read(out)
    if compaction_lines is None:
        compaction_lines = [number for number, event in events(path) if event.get("type") == "auto_compact_completed"]
    stage_entries = list(zip([row["stage"] for row in accepted] + ([pending] if pending else []),
                             stage_windows(accepted, stamps, pending)))
    boundaries = _context_boundaries(sessions, compaction_lines)
    boundary_lines = [line for line, _kind in boundaries]
    windows = [{"lines": [], "peak": None, "bytes": _window_bytes_table(), "top": [], "server_tool_rounds": 0}
              for _ in boundaries]
    calls: dict = {}  # call id -> (tool, arg); one log for the whole pass, so a result is placed by its own line
    rounds_since_usage = 0  # server rounds since the last usage figure (across the whole pass, not per window)
    for number, event in events(path):
        window = windows[bisect.bisect_right(boundary_lines, number) - 1]
        window["lines"].append(number)
        for call_id, tool, arg in tool_call_events(event):
            calls[call_id] = (tool, arg)
        if _server_tool_round(event):
            window["server_tool_rounds"] += 1
            rounds_since_usage += 1
        tokens = _event_context_tokens(event)
        if tokens is not None:
            is_usage = event.get("type") == "usage"
            if not is_usage or rounds_since_usage == 0:
                window["peak"] = tokens if window["peak"] is None else max(window["peak"], tokens)
            if is_usage:
                rounds_since_usage = 0
        for call_id, shown in result_text(event):
            size = len(shown)
            if not size:
                continue
            tool, arg = calls.get(call_id, ("", {}))
            source = window_source(tool, arg, shown)
            window["bytes"][source] += size
            window["top"].append({"tool": tool, "label": _window_top_label(tool, arg), "bytes": size})
        text = _assistant_text(event)
        if event.get("type") == "thought":  # Grok's reasoning stream: chunks _assistant_text does not read
            text += str(event.get("data") or "")
        if text:
            window["bytes"]["model_text"] += len(text)
    rows = []
    for index, (line, _kind) in enumerate(boundaries):
        window = windows[index]
        held = [stamps[n] for n in window["lines"] if n in stamps]
        start_t = stamps.get(line, held[0] if held else None)
        end_t = held[-1] if held else start_t
        active: list = []
        for stage_name, bounds in stage_entries:
            if (bounds is not None and start_t is not None and end_t is not None
                    and spans_overlap((bounds[0], bounds[1]), (start_t, end_t)) and stage_name not in active):
                active.append(stage_name)
        rows.append({
            "start": start_t, "end": end_t,
            "minutes": round((end_t - start_t) / 60, 2) if start_t is not None and end_t is not None else None,
            "stages": active, "peak_tokens": window["peak"], "server_tool_rounds": window["server_tool_rounds"],
            "compacted": index + 1 < len(boundaries) and boundaries[index + 1][1] == "compaction",
            "bytes": window["bytes"], "top": sorted(window["top"], key=lambda row: -row["bytes"])[:5],
        })
    return rows


def context_summary(rows: list[dict]) -> dict:
    """Totals, shares and the median window over every row ``context_window_rows`` built: ``{}`` for a run with none
    (a run whose events.jsonl holds nothing), never a reason to read the empty totals below as a measurement.

    ``share`` is each source's fraction of the run's total bytes (None where the total is 0, never a divide); ``top_sources``
    ranks the sources themselves by total bytes, so the biggest contributor across the whole run reads directly, not just
    per window. ``median_minutes`` and ``median_window_bytes`` read a run from a saved metrics.json the same way
    ``summary_lines`` reads other medians: the one implementation, ``_median``. ``server_tool_rounds`` is the run's
    total native web search/page-open rounds (billed input, kept apart from ``bytes``'s ``web``; see
    ``_server_tool_round``).
    """
    if not rows:
        return {}
    totals = _window_bytes_table()
    for row in rows:
        for source, size in row["bytes"].items():
            totals[source] = totals.get(source, 0) + size
    grand = sum(totals.values())
    share = {source: (round(size / grand, 4) if grand else None) for source, size in totals.items()}
    minutes = [row["minutes"] for row in rows if row["minutes"] is not None]
    window_totals = [sum(row["bytes"].values()) for row in rows]
    ranked = sorted(((source, size) for source, size in totals.items() if size), key=lambda pair: -pair[1])
    return {"windows": len(rows), "compactions": sum(1 for row in rows if row["compacted"]),
            "server_tool_rounds": sum(row["server_tool_rounds"] for row in rows),
            "bytes": totals, "share": share, "total_bytes": grand,
            "median_minutes": _median(minutes), "median_window_bytes": _median(window_totals),
            "top_sources": [{"source": source, "bytes": size} for source, size in ranked]}


def collect(out: Path, run_dir: Path | None = None, tools: ToolLog | None = None) -> dict:
    """The run's metrics. ``tools`` is the ToolLog to fill (a caller that reads the tool calls itself, as fidelity.py does,
    passes an empty one); without it the log is this call's own. It is fed through ``ToolLog.feed``, the one reader the
    windows of ``fresh_starts`` use too, with each event's line number (``sequence``, ``failure_events``)."""
    stamps = timeline(out / "timeline.jsonl")
    tools = ToolLog() if tools is None else tools
    turns: list[dict] = []
    sessions, compactions = [], 0
    truncated: set = set()
    cancelled: list[str] = []
    grok = False  # per-call `usage` events: the one stream shape the Grok-only counters below can be read from
    starts = 0  # sessions the host began, to tell how many never reported an end
    announced = 0  # available_commands events: a session start for Codex, a repeated announcement inside one for Grok
    usage_since_end = 0  # Grok model calls since the last `end` event: a session that never ended made them
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
        tools.feed(event, t, number)  # Claude tool_use / tool_result blocks, Grok and Codex tool_call / tool_call_update
        if kind in ("usage", "assistant"):
            calls_in_session += 1
        if kind == "available_commands":
            announced += 1  # whose start it is depends on the host, decided once the whole stream has been read
        elif kind == "system" and event.get("subtype") == "init":
            starts += 1  # Claude opens a session with system/init
        if kind in ("available_commands", "system") and init_build(event):
            versions.add(init_build(event))
        if kind == "usage":
            usage_since_end += 1
        elif kind == "end":
            usage_since_end = 0
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
    # Grok's events mark no session start (its `available_commands` is announced again inside a session: 314 for 2 `end`
    # events on r1-battleship-grok-none), Codex's translator emits one per thread. A stream is Grok's when a launch record
    # names Grok or it holds Grok's per-call `usage` events: never by a field of one event, which a Grok build can add.
    grok_stream = grok or "grok" in runrecord.hosts_used(out)
    if not grok_stream:
        starts += announced
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
    sessions_recorded = None  # set inside the try below; kept bound here so context_window_rows can reuse it on a failure
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
    try:
        context_rows = context_window_rows(out, run_dir, stamps=stamps, accepted=accepted, pending=pending,
                                           sessions=sessions_recorded, compaction_lines=compaction_lines)
    except Exception as exc:  # noqa: BLE001 - record-only, like fresh_starts above
        context_rows = []
    stages = per_stage(accepted, turns, tools.calls, stamps, pending, unmeasured, window_tokens)
    if grok_stream:
        unmeasured["unreported_sessions"] = NO_SESSION_START
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
        # Null when the stream holds Grok's events: no event marks one of its session starts, so how many sessions never
        # reported is unknown and cost and turns stay a lower bound (lower_bound). The harness's own launch records, not
        # this stream, can count them: a launch whose lines hold no `end` event never reported.
        "unreported_sessions": None if grok_stream else max(0, starts - len(sessions)),
        # What the stream does prove about a Grok run: model calls after its last `end` (or with no `end`) were made by a
        # session that never reported, so at least one did. None where the count is exact.
        "unreported_sessions_at_least": (1 if usage_since_end else 0) if grok_stream else None,
        "compactions": None if "compactions" in unmeasured else compactions,
        "truncated_outputs": None if "truncated_outputs" in unmeasured else len(truncated),
        "cancelled_tool_calls": cancelled,
        "shiploop_failures": tools.failures,
        # Per named gate (GATE_SIGNATURES): how many times it refused ("fired") and how many of those refusals the
        # run then got past ("caught": the same action id's next accepted complete). Never 0 for a gate that fired
        # nothing -- it is simply absent; an unclassified refusal is under "other".
        "gate_counts": gate_counts(tools),
        # Test-quality dodges no gate refuses (dodge_counts): grep-only checks on code, guarded REDs, inspected criteria,
        # surviving mutants. A record, never a verdict.
        "dodges": dodge_counts(run_dir),
        # Retired glossary terms in ShipLoop's printed packets and refusals (S-16): a record, never a verdict.
        "nomenclature": nomenclature(tools),
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
        # What filled the context between compactions (and from the run's start, and to its end): one row per window,
        # record-only like fresh_starts, plus the run-level totals and shares context_summary reduces them to.
        "context_windows": context_rows,
        "context_summary": context_summary(context_rows),
        # The first and last stamp of the stream (a resumed run's covers all its launches): the interval another run's
        # span is compared with to count overlap. None where the runner wrote no timeline.
        "span": span(stamps),
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
        if not isinstance(result, dict) or str(result.get("summary", "")).startswith(NOT_APPLICABLE):
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
    ``red`` counts the records in which a command ran red (a run whose own status is `red`): the test stage's base run
    on the base checkout passes because red is what it accepts, so ``passed`` includes it. What ran is counted, not
    what the record expected.
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
        events = [x for x in turns if x["t"] is not None and within(x["t"], after, until)]
        tools = [c for c in calls.values() if c["t"] is not None and within(c["t"], after, until)]
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


def lower_bound(run_metrics: dict) -> bool | None:
    """Whether the whole-run cost and turns cover only the sessions that reported, by the one predicate every reader shares.

    True when a session is known not to have reported (``unreported_sessions`` above 0) and when the count is unknown
    for a reason (null, named in ``unmeasured``: Grok's events mark no session start, so a killed session cannot be ruled
    out). False when every session reported. None when the metrics say nothing (they predate the field).
    """
    if "unreported_sessions" not in run_metrics:
        return None
    never = run_metrics["unreported_sessions"]
    if never is None:
        return True if "unreported_sessions" in (run_metrics.get("unmeasured") or {}) else None
    return never > 0


def cost_text(run_metrics: dict) -> str:
    """The cost for a printed line, saying so when sessions that never reported make it a lower bound.

    A cost that is unknown has nothing for a lower bound to bound, so it says only that it is not reported. When the
    host's events cannot count the sessions that never reported (Grok), no count is printed, only that it may be one.
    """
    cost, never = run_metrics.get("cost_usd"), run_metrics.get("unreported_sessions")
    if cost is None or not lower_bound(run_metrics):
        return money(cost)
    at_least = run_metrics.get("unreported_sessions_at_least")
    return money(cost) + (f" (lower bound: {never} session(s) never reported)" if never else
                          f" (lower bound: at least {at_least} session(s) never reported)" if at_least else
                          " (lower bound: this host's events do not show whether a session never reported)")


def turns_text(run_metrics: dict) -> str:
    """The whole-run turns for a printed line: 'not reported' when nothing reported a count, a lower bound when a session never did."""
    turns = run_metrics.get("turns")
    if turns is None:
        return "not reported"
    return f"{turns} (lower bound)" if lower_bound(run_metrics) else str(turns)


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


def gate_counts_text(gates: dict[str, dict[str, int]]) -> str:
    """One line per named gate that fired at least once, busiest first: ``name fired (caught N)``."""
    ordered = sorted(gates.items(), key=lambda item: (-item[1]["fired"], item[0]))
    return ", ".join(f"{name} {row['fired']}" + (f" (caught {row['caught']})" if row["caught"] else "")
                     for name, row in ordered)


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
    if metrics.get("gate_counts"):
        lines.append("ShipLoop gates: " + gate_counts_text(metrics["gate_counts"]))
    if (metrics.get("dodges") or {}).get("plans"):
        lines.append(dodge_text(metrics["dodges"]))
    if (metrics.get("nomenclature") or {}).get("retired"):
        lines.append("Retired terms in ShipLoop's output: " + nomenclature_text(metrics["nomenclature"]))
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


# ======================================================================================================================
# The reading path (ShipLoop efficiency plan, unit U5): where the characters a model took in came from, how it ran each
# ShipLoop command, and what it did after a break. Read from the host event stream and the run directory the runner kept.
# A record, never a verdict: arms.py decides from these numbers. Unknown is None (or ``measured: false`` with a reason),
# never 0. Every function reads files and calls nothing else; no host, model or ShipLoop command runs here.
# ======================================================================================================================

# The last line of every print (shiploop_navigator.HEAD_END; a test pins the two equal). A print that lacks it was cut.
# Its name before R4 of the run-5 batch (2026-10-24), which a saved run keeps, is HEAD_END_UNTIL_R4.
HEAD_END = "=== end ShipLoop print ==="
HEAD_END_UNTIL_R4 = "=== end ShipLoop head ==="
# Either name, as a line: the packet's second pointer line names it inside a sentence near the top of every print, cut or not.
HEAD_END_LINE = re.compile(r"^(?:" + re.escape(HEAD_END) + "|" + re.escape(HEAD_END_UNTIL_R4) + r")$", re.M)
COLD_CALLS = 12  # the calls after a break (a compaction, a fresh session, the run's start) that count as cold
SCRIPTS = Path(__file__).resolve().parents[2] / "skills" / "shiploop" / "scripts"
READ_TOOLS = ("Read", "read_file")
SEARCH_TOOLS = ("Grep", "grep")
# The classes of file a model opens, by path; the first pattern that matches names the file. `handoff` and `child_record`
# are an Improve child's files (the bucket "child_handoffs"); the other classes are the bucket "files".
FILE_CLASSES: tuple[tuple[str, re.Pattern], ...] = (
    ("entry_card", re.compile(r"/skills/shiploop/SKILL\.md$")),
    ("improve_card", re.compile(r"/skills/improve/SKILL\.md$")),
    ("adapter", re.compile(r"/ADAPTER\.md$")),
    ("packet_file", re.compile(r"/packets/nav-[0-9a-f]+(?:-[\w-]+)?\.md$")),
    ("handoff", re.compile(r"/handoff\.md$")),
    ("child_record", re.compile(r"/\.shiploop-improve/.+\.(?:json|md|txt)$")),
    ("reference", re.compile(r"/skills/(?:shiploop|improve)/references/")),
    ("run_file", re.compile(r"/run/(?:reference|context-index|status|state|start-here)\.md$")),
    ("knowledge", re.compile(r"/docs/shiploop/")),
    ("script", re.compile(r"/skills/shiploop/scripts/shiploop_\w+\.py$")),
    ("result_record", re.compile(r"/run/(?:results|tests|lint|notes|loops|quality|expectations|inbox)/")),
)
CHILD_CLASSES = ("handoff", "child_record")
BUCKETS = ("packet_output", "shiploop_messages", "files", "child_handoffs", "runtime_output", "other")
# An absolute path in a shell command, the few files a command names without a directory (a model that has changed into an
# Improve child's folder), and the Until Loop runtime's script (its output is the bucket "runtime_output").
ABS_PATH = re.compile(r"""(?:(?<=[\s"'=(:,])|^)(/[\w.@+~%-][\w./@+~%-]*)""", re.M)
BARE_FILES = ((re.compile(r"(?<![\w/.-])handoff\.md\b"), "handoff"),
              (re.compile(r"(?<![\w/.-])(?:packet\.json|parent-return\.md|opening\.md)\b"), "child_record"),
              (re.compile(r"(?<![\w/.-])ADAPTER\.md\b"), "adapter"))
RUNTIME_SCRIPT = re.compile(r"until_loop_ephemeral\.py")
# KNOWLEDGE replaced HOME as the knowledge-home symbol on 2026-10-18 (decision 19); saved runs before it print HOME.
SYMBOL_DEFINITION = re.compile(r"\b(KNOWLEDGE|HOME|RUN|WORKTREE|GUIDES|FEATURE) = (/\S+)")
SYMBOL_PATH = re.compile(r"\b(KNOWLEDGE|HOME|RUN|WORKTREE|GUIDES|FEATURE)/([\w.@+~/<>-]*[\w@+~>-])")
READER = re.compile(r"\b(?:cat|head|tail|sed|grep|egrep|awk|less|more|rg|nl|wc|jq)\b")
SLICING_COMMAND = re.compile(r"\|\s*(?:head|tail|sed|grep|awk)\b|^\s*(?:head|tail|sed|grep|awk)\b|\b(?:sed -n|grep)\b")
SHELL_VARIABLE_ANY = re.compile(r"\$[\w{(]")
SKILL_TOOLS = ("Skill",)
# Where the knowledge of a packet sits (shiploop_navigator._consumer_lines): a header, then one block per file: the file
# quoted whole ("HOME/spec.md (source: ..., whole file):", before 2026-10-17) or listed by contents ("HOME/spec.md (16027
# bytes, 188 lines), contents:", owner decision D1).  The request is quoted whole at intake, spec and plan, and named by its
# file elsewhere ("Original request: RUN/request.md ...", decision D2), which quotes nothing.
QUOTE_START = re.compile(r"^Knowledge files this stage reads", re.M)
QUOTE_FILE = re.compile(r"^(?P<name>\S+) \((?:source: [^)\n]*|\d+ bytes, \d+ lines?)\)(?::|, contents:|, no headings)[ \t]*$",
                        re.M)
QUOTE_HANDOFFS = re.compile(r"^Handed off by earlier stages, quoted by value", re.M)
QUOTE_REQUEST = re.compile(r"^Original request \(", re.M)
QUOTE_STOPS = re.compile(r"^(?:Recovery command|Original request[ (:]|Last accepted transition|Work item:|"
                         r"Current stage guidance:|Evidence references|Handed off by earlier stages)", re.M)


def file_class(path: str) -> str | None:
    """The class of file a path names (FILE_CLASSES), or None for any other file."""
    for name, pattern in FILE_CLASSES:
        if pattern.search(path):
            return name
    return None


def result_text(event: dict) -> list[tuple]:
    """(call id, text) of each final tool result in one event, for every host; the text is what the model was shown.

    ``tool_results`` reads Claude's blocks and the flat Grok outputs; Grok's read_file keeps its text under
    ``FileContent.content``, its grep under ``stdout`` and a directory listing under ``Content``. A running update and a
    cancelled one are no result (the same rule ``ToolLog.feed`` applies)."""
    kind = event.get("type")
    if kind == "user":
        return list(tool_results(event))
    if kind != "tool_call_update" or not isinstance(event.get("rawOutput"), dict) or cancelled_update(event) \
            or event.get("status") == "in_progress":
        return []
    raw = event["rawOutput"]
    found = visible(raw)
    if not found:
        for key in ("FileContent", "Content"):
            part = raw.get(key)
            found = part.get("content", "") if isinstance(part, dict) else part if isinstance(part, str) else found
            if found:
                break
    found = found or (raw.get("stdout") if isinstance(raw.get("stdout"), str) else "")
    return [(event.get("toolCallId"), str(found or ""))]


def _tokens(line: str) -> list[str] | None:
    """The shell tokens of one command line (pipes, redirects and chains are their own tokens), None where it does not parse."""
    import shlex
    lexer = shlex.shlex(line, posix=True, punctuation_chars=True)
    lexer.whitespace_split = True
    try:
        return list(lexer)
    except ValueError:
        return None


def pipe_of(line: str) -> dict | None:
    """The pipe a command line sends its output through: ``{"into": "head", "lines": 20}`` (lines None when it names none), or
    None for a line with no pipe. Only a single `|` counts (`||` is a chain). Read from the tokens, so a `|` inside quotes is not
    a pipe; a line that does not tokenise is read by a plain match."""
    tokens = _tokens(line)
    if tokens is None:
        found = re.search(r"(?<!\|)\|(?!\|)", line)
        rest = line[found.end():].split() if found else None
    else:
        rest = next((tokens[i + 1:] for i, token in enumerate(tokens) if token == "|"), None)
    if rest is None:
        return None
    into = os.path.basename(rest[0]) if rest else ""
    lines = None
    for number, token in enumerate(rest[1:], 1):
        found = re.fullmatch(r"-(\d+)", token) or re.fullmatch(r"-n(\d+)", token)
        if not found and token == "-n" and number < len(rest) - 1:
            found = re.fullmatch(r"\+?(\d+)", rest[number + 1])
        if not found and into == "sed":
            found = re.fullmatch(r"\d+,(\d+)p", token)
        if found:
            lines = int(found.group(1))
            break
    return {"into": into, "lines": lines}


def hook_verb(command: str):
    """What the status display makes of a whole Bash command: ``shiploop_status_hook._verb`` (a verb and its wrapper for one
    direct ShipLoop call, None for anything piped, chained, redirected or built through a variable). Imported on first use:
    the plugin source is a sibling tree of this harness."""
    import sys
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    import shiploop_status_hook
    return shiploop_status_hook._verb(command)


def shiploop_invocations(command: str) -> list[dict]:
    """Each ShipLoop CLI verb a shell command runs, one entry per verb on a logical line (a backslash joins lines; heredoc
    bodies are documents and are not read). Variables the command assigns are expanded first, so `python3 $SC complete` is
    seen as the ShipLoop call it is.

    Each entry: ``verb``, ``check_only``, ``piped`` (the line sends its output into a pipe), ``cut`` (the pipe keeps the first
    or last lines: ``{"into", "lines"}``), ``variable_built`` (the run directory argument is a shell variable or substitution),
    ``variable_any`` (any part of the command before its pipe is) and ``hook_visible`` (the whole command is one direct call
    to the display: the status display cannot read a piped command or one built through a variable).
    """
    known = shell_variables(command)
    visible_to_hook = hook_verb(command) is not None
    found = []
    for raw in re.sub(r"\\\n", " ", shell_text(command)).split("\n"):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        verbs = [m.group("verb") for m in SHIPLOOP_COMMAND.finditer(expand_variables(line, known))]
        if not verbs:
            continue
        pipe = pipe_of(line)
        before_pipe = line if pipe is None else re.split(r"(?<!\|)\|(?!\|)", line, maxsplit=1)[0]
        run_dir = RUN_DIR_ARG.search(before_pipe)
        for verb in verbs:
            found.append({"verb": verb, "check_only": "--check-only" in line, "piped": pipe is not None,
                          "cut": pipe if pipe is not None and pipe["into"] in ("head", "tail", "sed") else None,
                          "variable_built": bool(run_dir and SHELL_VARIABLE_ANY.search(run_dir.group("dir"))),
                          "variable_any": bool(SHELL_VARIABLE_ANY.search(before_pipe)), "hook_visible": visible_to_hook})
    return found


def quote_regions(text: str) -> dict[str, int]:
    """Characters of quoted material in one tool result, by what is quoted: each knowledge file under its name, plus
    ``handoffs`` (what earlier stages handed off) and ``request`` (the original request), as the packet file lays them out.
    A print cut before the quote region holds none; the packet file read whole holds all of it."""
    found: dict[str, int] = {}
    start = QUOTE_START.search(text)
    if start:
        stop = QUOTE_STOPS.search(text, start.end())
        block = text[start.end():stop.start() if stop else len(text)]
        marks = list(QUOTE_FILE.finditer(block))
        for index, mark in enumerate(marks):
            end = marks[index + 1].start() if index + 1 < len(marks) else len(block)
            name = os.path.basename(mark.group("name"))
            found[name] = found.get(name, 0) + end - mark.start()
    for label, pattern in (("handoffs", QUOTE_HANDOFFS), ("request", QUOTE_REQUEST)):
        mark = pattern.search(text)
        if mark:
            stop = QUOTE_STOPS.search(text, mark.end())
            found[label] = found.get(label, 0) + (stop.start() if stop else len(text)) - mark.start()
    return found


NUMBERED = re.compile(r"^\s*\d+→", re.M)


def unnumbered(shown: str) -> str:
    """A file read's text without the line numbers Claude's Read and Grok's read_file put before each line (`   12→text`)."""
    return NUMBERED.sub("", shown) if NUMBERED.match(shown) else shown


def classify_call(tool: str, arg: dict, shown: str) -> dict:
    """What one tool call returned to the model, named once for every host: ``bucket`` (BUCKETS), ``cls`` (a FILE_CLASSES
    name or None), ``mode`` (`whole`, `slice` or None), ``path`` (the file it names first) and ``read`` (a Read or read_file
    tool call). Packets the model met are decided here: a shell command that names a packet file is a read of it
    (``ToolLog.measure`` did the same), a ShipLoop verb whose output shows a packet header is a print, and a command that runs
    the Until Loop runtime returned runtime output."""
    command = str(arg.get("command") or "")
    paths = target_paths(arg)
    if not command:
        if tool in SKILL_TOOLS:
            skill = str(arg.get("skill") or "").lower()
            cls = "improve_card" if "improve" in skill else "entry_card" if "shiploop" in skill else None
            return {"bucket": "files" if cls else "other", "cls": cls, "mode": "whole" if cls else None, "path": skill, "read": False}
        path = paths[0] if paths else ""
        cls = file_class(path) if path and (tool in READ_TOOLS or tool in SEARCH_TOOLS) else None
        mode = None if cls is None else ("whole" if tool in READ_TOOLS and "offset" not in arg and "limit" not in arg else "slice")
        return {"bucket": ("child_handoffs" if cls in CHILD_CLASSES else "files") if cls else "other", "cls": cls, "mode": mode,
                "path": path, "read": tool in READ_TOOLS}
    expanded = expand_variables(command, shell_variables(command))
    shell = shell_text(expanded)  # heredoc bodies are documents: a path or a verb inside one is not a command
    named = [(file_class(p), p) for p in ABS_PATH.findall(shell)]
    named += [(cls, found.group(0)) for bare, cls in BARE_FILES for found in [bare.search(shell)] if found]
    named = [(cls, p) for cls, p in named if cls]
    packet = next(((c, p) for c, p in named if c == "packet_file"), None)
    mode = "slice" if SLICING_COMMAND.search(shell) else "whole"
    if packet:
        return {"bucket": "files", "cls": "packet_file", "mode": mode, "path": packet[1], "read": False}
    if SHIPLOOP_COMMAND.search(shell):
        return {"bucket": "packet_output" if PACKET_STAGE.search(shown) else "shiploop_messages", "cls": None, "mode": None,
                "path": "", "read": False}
    if RUNTIME_SCRIPT.search(shell):
        return {"bucket": "runtime_output", "cls": None, "mode": None, "path": "", "read": False}
    if named:
        cls, path = named[0]
        return {"bucket": "child_handoffs" if cls in CHILD_CLASSES else "files", "cls": cls, "mode": mode, "path": path,
                "read": False}
    return {"bucket": "other", "cls": None, "mode": None, "path": "", "read": False}


def _median(values: list) -> float | None:
    values = sorted(values)
    if not values:
        return None
    middle = len(values) // 2
    return float(values[middle]) if len(values) % 2 else (values[middle - 1] + values[middle]) / 2


def _bucket_table() -> dict:
    return {name: {"calls": 0, "chars": 0} for name in BUCKETS}


def run_dir_of(out: Path) -> Path | None:
    """The ShipLoop run directory a harness output folder recorded: a slice's invocation.json (`seeded.run_dir`) or a full
    run's result.json (`shiploop.run_dir`), else the one `.shiploop-runs/*/run` under the folder; None where none is there."""
    out = Path(out)
    for name, keys in (("invocation.json", ("seeded", "run_dir")), ("result.json", ("shiploop", "run_dir"))):
        try:
            value: object = json.loads((out / name).read_text())
            for key in keys:
                value = value.get(key) if isinstance(value, dict) else None
        except (OSError, ValueError):
            continue
        # A run moved after it was recorded keeps its folder name: prefer the copy beside the events file.
        if isinstance(value, str) and value:
            local = out / ".shiploop-runs" / Path(value).parent.name / "run"
            for candidate in (local, Path(value)):
                if (candidate / "state.md").is_file():
                    return candidate
    found = sorted((out / ".shiploop-runs").glob("*/run/state.md")) if (out / ".shiploop-runs").is_dir() else []
    return found[0].parent if len(found) == 1 else None


def _state_block(path: Path) -> dict | None:
    try:
        found = STATE_BLOCK.search(path.read_text(errors="replace"))
        value = json.loads(found.group("json")) if found else None
    except (OSError, ValueError):
        return None
    return value if isinstance(value, dict) else None


def skipped_reason(record: dict) -> str | None:
    """Why a base-run or mutation-check record says its gate did nothing, or None for a gate that ran.

    The engine writes ``disposition: "skipped"`` (with ``passed`` true, so every reader of ``passed`` is unchanged) and the
    reason under ``skipped``; a record from before that kept the reason alone under ``disposition: "passed"``. Either marks the
    gate as not exercised, and a disposition without a reason is still one."""
    reason = record.get("skipped")
    if reason:
        return str(reason)
    return "no reason recorded" if record.get("disposition") == "skipped" else None


def skipped_gates(run_dir: Path | None) -> dict:
    """The gates a run's records say did not run, from the run directory alone: the test stage's base run, its mutation check
    (skipped, or run and found no mutants), the change inventory, and the item commit (which cannot read an item's changes
    when no base snapshot was captured). Each gate is a row ``{gate, records, skipped, reason}``; ``count`` is the number of
    gates with at least one skipped record. A run that never reached a gate has no row for it."""
    if run_dir is None or not Path(run_dir).is_dir():
        return {"measured": False, "reason": "no run directory", "count": None, "gates": []}
    run_dir = Path(run_dir)
    gates = []

    def row(name: str, records: list[dict], reasons: list[str]) -> None:
        if records:
            gates.append({"gate": name, "records": len(records), "skipped": len(reasons), "reason": reasons[0] if reasons else None})

    base = [r for p in sorted((run_dir / "tests").glob("*-base*.md")) if (r := _state_block(p))]
    row("base", base, [reason for r in base if (reason := skipped_reason(r))])
    mutation = [r for p in sorted((run_dir / "tests").glob("*-mutation*.md")) if not p.name.endswith("-check-only.md")
                and (r := _state_block(p))]
    row("mutation", mutation, [skipped_reason(r) or "no mutants" for r in mutation
                               if skipped_reason(r) or not r.get("mutants")])
    inventory = [r for p in sorted((run_dir / "lint").glob("*-inventory.md")) if (r := _state_block(p))]
    row("inventory", inventory, [str(r.get("reason") or r.get("status")) for r in inventory if r.get("status") == "unavailable"])
    state = engine_state(run_dir)
    items = sorted({e.get("workitem") for e in state.get("history") or [] if isinstance(e, dict)
                    and e.get("stage") == "verify" and e.get("outcome") == "done" and e.get("workitem")})
    row("item_commit", [{"item": i} for i in items],
        [f"no base snapshot for {i} (lint/items/{i}.md): the item's changes cannot be read, so nothing is committed"
         for i in items if not (run_dir / "lint" / "items" / f"{i}.md").is_file()])
    return {"measured": True, "count": sum(1 for g in gates if g["skipped"]), "gates": gates}


def reading_path(out: Path, run_dir: Path | None = None, *, limit_events: int | None = None) -> dict:
    """The reading path of one run, from its host event stream (events.jsonl, timeline.jsonl, sessions.jsonl) and its ShipLoop
    run directory (``run_dir``; found beside the events by ``run_dir_of`` when not given). ``limit_events`` reads only the first
    N lines of the stream, which is how a snapshot taken while a run was live is read again.

    ``buckets`` partition the characters tool results returned to the model: ShipLoop's own prints, files opened, an Improve
    child's handoff and records, the Until Loop runtime's output, and everything else (``files_by_class`` splits the files).
    ``cold`` and ``warm`` split the same totals by whether a call is one of the first COLD_CALLS after a break (a compaction, a
    fresh session, or the run's start). The counters the plan names follow, each a dict with a ``count``:
    ``piped_shiploop_calls``, ``variable_built_shiploop_calls``, ``shiploop_print_cut``, ``packet_file_opens``,
    ``listed_pointers_followed``, ``skipped_gates``, ``warm_next_calls``, ``improve_skill_invoked``, and ``quoted_chars``
    (characters of quoted knowledge that reached the model, by file). A host that cannot show a signal gives None.
    """
    out = Path(out)
    run_dir = Path(run_dir) if run_dir else run_dir_of(out)
    stamps = timeline(out / "timeline.jsonl")
    tools = ToolLog()
    args: dict = {}
    line_of: dict = {}
    chars: dict = {}
    seen_at: dict = {}
    kept: dict = {}  # call -> text, kept for a print, a packet read or a quote region only
    compaction_lines: list[int] = []
    cancels = 0
    grok = claude = False
    skill_key = None
    last_line = -1
    for number, event in event_range(out / "events.jsonl", 0, limit_events):
        last_line = number
        kind = event.get("type")
        if kind == "auto_compact_completed":
            compaction_lines.append(number)
        elif kind == "usage":
            grok = True
        elif kind == "assistant":
            claude = True
        elif cancelled_update(event):
            cancels += 1
        for call_id, tool, arg in tool_call_events(event):
            args[call_id if call_id is not None else f"#{len(args)}"] = (tool, arg)
        started = tools.feed(event, stamps.get(number), number)
        for key in started:
            line_of[key] = number
        for block in ((event.get("message") or {}).get("content") or []) if kind == "user" else []:
            # Claude puts a skill's own text into the conversation as a user message after the Skill call returned.
            if isinstance(block, dict) and block.get("type") == "text" and str(block.get("text", "")).startswith(
                    "Base directory for this skill:") and skill_key is not None:
                chars[skill_key] = chars.get(skill_key, 0) + len(block["text"])
        for key in started:
            if tools.calls[key]["tool"] in SKILL_TOOLS:
                skill_key = key
        for call_id, shown in result_text(event):
            if call_id in chars:
                continue  # Grok repeats an update for one call; Codex's reused ids were discarded in ToolLog.call
            chars[call_id] = len(shown)
            seen_at[call_id] = number
            if PACKET_STAGE.search(shown) or QUOTE_START.search(shown) or "Original request (" in shown:
                kept[call_id] = unnumbered(shown)
    order = list(tools.calls)
    classes = {key: classify_call(*args.get(key, ("", {})), kept.get(key, "")) for key in order}
    host = "claude" if claude and not grok else "grok" if grok else None
    # Breaks: the run's start, every compaction the stream marks (Grok), and every fresh host session the harness recorded.
    breaks = [{"kind": "start", "line": 0}]
    breaks += [{"kind": "compaction", "line": n} for n in compaction_lines]
    sessions = sessionlog.read(out)
    breaks += [{"kind": "fresh", "line": row["events_line"]} for row in sessions or []
               if row.get("kind") == "fresh" and isinstance(row.get("events_line"), int)]
    breaks.sort(key=lambda b: b["line"])
    call_lines = [line_of.get(key, 0) for key in order]
    cold: set[int] = set()
    for brk in breaks:
        first = bisect.bisect_right(call_lines, brk["line"]) if brk["kind"] != "start" else 0
        brk["first_call"] = first
        cold.update(range(first, min(first + COLD_CALLS, len(order))))
    totals = {"all": _bucket_table(), "cold": _bucket_table(), "warm": _bucket_table()}
    by_class: dict[str, dict] = {}
    reads: dict[str, int] = {}
    for position, key in enumerate(order):
        info, size = classes[key], chars.get(key, 0)
        for scope in ("all", "cold" if position in cold else "warm"):
            totals[scope][info["bucket"]]["calls"] += 1
            totals[scope][info["bucket"]]["chars"] += size
        if info["cls"]:
            row = by_class.setdefault(info["cls"], {"calls": 0, "chars": 0, "reads": 0, "whole": 0, "slice": 0})
            row["calls"] += 1
            row["chars"] += size
            row["reads"] += info["read"]
            row[info["mode"] or "slice"] += 1
            reads[info["cls"]] = reads.get(info["cls"], 0) + int(info["read"])
    # ShipLoop commands, one per verb a command line runs.
    invocations, print_rows, latency = [], [], []
    for position, key in enumerate(order):
        call = tools.calls[key]
        mine = shiploop_invocations(call["command"]) if call["command"] else []
        for found in mine:
            invocations.append({**found, "call": position, "cold": position in cold})
        text = kept.get(key, "")
        header = PACKET_STAGE.search(text) if mine else None
        if header:
            cut = mine[-1]["cut"]
            ended = HEAD_END_LINE.search(text) is not None
            print_rows.append({"call": position, "stage": header.group("stage"), "verb": mine[-1]["verb"], "chars": len(text),
                               "lines": text.count("\n") + (not text.endswith("\n")), "ended": ended,
                               "cut_by": None if cut is None else f"{cut['into']} -{cut['lines']}" if cut["lines"] else cut["into"],
                               "n": None if cut is None else cut["lines"]})
        if mine and call["t"] is not None and stamps.get(seen_at.get(key)) is not None:
            latency.append(round(stamps[seen_at[key]] - call["t"], 3))
    marker_seen = any(row["ended"] for row in print_rows)
    for row in print_rows:  # a pipe that keeps lines cut the print; without one, only a head that lost its closing line is cut
        row["cut"] = True if row["cut_by"] else (not row["ended"] if marker_seen else None)
    by_verb: dict[str, dict] = {}
    for found in invocations:
        row = by_verb.setdefault(found["verb"], {"invocations": 0, "piped": 0, "variable_built": 0, "variable_any": 0,
                                                 "hook_visible": 0, "check_only": 0})
        row["invocations"] += 1
        for name in ("piped", "variable_built", "variable_any", "hook_visible", "check_only"):
            row[name] += bool(found[name])
    nexts = [found for found in invocations if found["verb"] == "next"]
    cut_rows = [r for r in print_rows if r["cut"]]
    # Per break: what the first calls were, and whether `next` came within the cold window.
    for brk in breaks:
        window = order[brk["first_call"]:brk["first_call"] + COLD_CALLS]
        first = classes[window[0]] if window else None
        brk["first_call_kind"] = call_kind(tools.calls[window[0]]) if window else None
        brk["first_call_class"] = first["cls"] if first else None
        brk["next_within_12"] = any("next" in _verbs(tools.calls[k]) for k in window)
        brk["cold_chars"] = sum(chars.get(k, 0) for k in window)
    minutes = None
    run_span = span(stamps)
    if run_span.get("started") is not None and run_span.get("ended") is not None:
        minutes = round((run_span["ended"] - run_span["started"]) / 60.0, 2)
    quoted: dict[str, int] = {}
    for key, text in kept.items():
        for name, size in quote_regions(text).items():
            quoted[name] = quoted.get(name, 0) + size
    report = {
        "measured": True, "host": host, "events": last_line + 1, "limit_events": limit_events, "calls": len(order),
        "result_chars": sum(b["chars"] for b in totals["all"].values()),
        "buckets": totals["all"], "cold": totals["cold"], "warm": totals["warm"],
        "files_by_class": dict(sorted(by_class.items())), "reads_by_class": dict(sorted(reads.items())),
        "breaks": breaks,
        "compactions": len(compaction_lines) if grok else None,
        "compactions_per_100_min": round(len(compaction_lines) * 100.0 / minutes, 2) if grok and minutes else None,
        "run_minutes": minutes,
        "shiploop_commands": {"invocations": len(invocations), "by_verb": by_verb,
                              "hook_visible": sum(f["hook_visible"] for f in invocations)},
        "piped_shiploop_calls": {"count": sum(f["piped"] for f in invocations), "of": len(invocations)},
        "variable_built_shiploop_calls": {"count": sum(f["variable_built"] for f in invocations), "of": len(invocations),
                                          "any_variable": sum(f["variable_any"] for f in invocations)},
        "check_only_calls": {"count": sum(f["check_only"] for f in invocations), "of": len(invocations)},
        "warm_next_calls": {"count": sum(1 for f in nexts if not f["cold"]), "of": len(nexts)},
        "shiploop_print_cut": {"count": len(cut_rows), "of": len(print_rows), "marker_seen": marker_seen,
                               "median_lines_seen": _median([r["n"] for r in cut_rows if r["n"]]), "prints": print_rows},
        "quoted_chars": {"count": sum(quoted.values()), "by_class": dict(sorted(quoted.items()))},
        "permission_cancels": cancels if grok else None,
        "script_latency": {"calls": len(latency), "median_seconds": _median(latency)} if latency else None,
    }
    report.update(_run_dir_counters(run_dir, order, tools, classes, kept, print_rows, host))
    report["skipped_gates"] = skipped_gates(run_dir)
    return report


def _run_dir_counters(run_dir: Path | None, order: list, tools: "ToolLog", classes: dict, kept: dict, print_rows: list,
                      host: str | None) -> dict:
    """The counters that need the run directory beside the stream: which packet files the model opened, which listed pointers it
    followed, and whether each Improve stage invoked the improve skill.

    A producer packet counts when the model was shown its stage: the stages it met are the stages of the prints in the stream
    (consecutive prints of one stage are one visit), and a stage met n times is its n newest packet files in ledger order (the
    header's revision), so a packet the harness seeded without the model is not counted."""
    seen: list[str] = []
    for row in print_rows:
        if row["stage"] != "improve" and (not seen or seen[-1] != row["stage"]):
            seen.append(row["stage"])
    visits = {stage: seen.count(stage) for stage in set(seen)}
    producers: dict[str, str] = {}  # action id -> stage, the packets the model met
    packets: dict[str, Path] = {}
    if run_dir is not None and (Path(run_dir) / "packets").is_dir():
        files = []
        for path in (Path(run_dir) / "packets").glob("nav-*.md"):
            found = PACKET_STAGE.search(path.read_text(errors="replace")[:4000]) if re.fullmatch(r"nav-[0-9a-f]+\.md", path.name) else None
            if found and found.group("stage") in visits:
                files.append((int(found.group("revision") or 0), found.group("stage"), path))
        for stage, count in visits.items():
            for _revision, _stage, path in sorted(f for f in files if f[1] == stage)[-count:]:
                producers[path.stem] = stage
                packets[path.stem] = path
    opens: dict[str, dict] = {action: {"stage": stage, "action": action, "mode": "none", "calls": 0}
                              for action, stage in producers.items()}
    for key in order:
        info = classes[key]
        if info["cls"] != "packet_file":
            continue
        action = re.search(r"nav-[0-9a-f]+", info["path"])
        row = opens.get(action.group(0)) if action else None
        if row is not None:
            row["calls"] += 1
            row["mode"] = "whole" if "whole" in (row["mode"], info["mode"]) else "slice"
    if run_dir is None or not producers:
        no_packets = {"measured": False, "reason": "no run directory with producer packets beside the stream", "count": None}
        opened = pointers = no_packets
    else:
        opened = {"measured": True, "count": sum(1 for r in opens.values() if r["mode"] != "none"), "of": len(opens),
                  "stages": sorted(opens.values(), key=lambda r: r["action"])}
        # Pointers: the files a producer packet names through its path symbols (KNOWLEDGE/spec.md, HOME/spec.md before 2026-10-18,
        # RUN/results/<id>.md, GUIDES/...),
        # each resolved against the symbol definitions in the packet's own References block.
        listed: dict[str, str] = {}
        for path in packets.values():
            text = path.read_text(errors="replace")
            roots = {m.group(1): m.group(2) for m in SYMBOL_DEFINITION.finditer(text)}
            for symbol, rest in SYMBOL_PATH.findall(text):
                if symbol not in roots or "<" in rest:
                    continue
                full = roots[symbol].rstrip("/") + "/" + rest
                cls = file_class(full)
                if cls in ("packet_file",) or "/inbox/" in full or "/loops/" in full or "/scratch/" in full:
                    continue  # the packet itself, the result it asks for, the Until Loop's files and the model's scratch space
                listed.setdefault(full, "result_record" if cls == "result_record" else "guide" if symbol == "GUIDES" or cls == "reference"
                                  else "knowledge" if cls == "knowledge" or symbol in ("KNOWLEDGE", "HOME") else cls or "other")
        # Opened: the target of a Read or read_file call, or named by a command that reads it (a redirect target is a write).
        touched = " ".join(
            tools.calls[k]["file"] if not tools.calls[k]["command"]
            else re.sub(r">>?\s*\S+|<\s*\S+", "", shell_text(tools.calls[k]["expanded"]))
            if READER.search(shell_text(tools.calls[k]["expanded"])) else "" for k in order)
        followed = sorted(p for p in listed if p in touched)
        pointers = {"measured": True, "count": len(followed), "of": len(listed), "followed": followed,
                    "by_class": {c: sum(1 for v in listed.values() if v == c) for c in sorted(set(listed.values()))}}
    # Improve stages: one window per run of Improve prints, ended by the next print of another stage.
    windows, current = [], None
    for position, key in enumerate(order):
        header = PACKET_STAGE.search(kept.get(key, ""))
        if header and header.group("stage") == "improve":
            if current is None:
                current = {"start": position, "invoked": 0}
                windows.append(current)
        elif header:
            current = None
    skill_calls = [p for p, key in enumerate(order) if tools.calls[key]["tool"] in SKILL_TOOLS and classes[key]["cls"] == "improve_card"]
    card_reads = [p for p, key in enumerate(order) if classes[key]["cls"] == "improve_card" and classes[key]["read"]]
    for window in windows:
        later = [w["start"] for w in windows if w["start"] > window["start"]]
        end = later[0] if later else len(order) + 1
        window["invoked"] = sum(1 for p in skill_calls if window["start"] < p < end)
        window["card_read"] = sum(1 for p in card_reads if window["start"] < p < end)
    record = None
    if run_dir is not None:
        records = Path(run_dir) / "skill-calls.jsonl"
        if records.is_file():
            record = sum(1 for line in records.read_text(errors="replace").splitlines() if '"skill":"improve"' in line.replace(" ", ""))
    improve = {"count": sum(1 for w in windows if w["invoked"]) if host == "claude" else None, "of": len(windows),
               "record_calls": record, "card_reads": sum(1 for w in windows if w["card_read"]),
               "stages": [{"call": w["start"], "invoked": bool(w["invoked"]), "card_read": bool(w["card_read"])} for w in windows]}
    if host != "claude":
        improve["reason"] = ("the Skill tool exists on Claude only; on this host the improve card is opened as a file, "
                             "which `card_reads` counts per Improve stage")
    return {"packet_file_opens": opened, "listed_pointers_followed": pointers, "improve_skill_invoked": improve}


def stage_share(out: Path, run_dir: Path | None = None, stage: str = "plan", needle: str = "backchain") -> dict:
    """What a planning stage takes of the planning window, offline (plan N5: the plan-stage Backchain child, which the 30-minute
    bar does not price). The window and its stages are ``planning_window``'s; ``authoring_seconds`` is the stage's accept-to-accept
    time less its Improve child's (the figure the Luna study called the plan-stage Backchain work, 64.1 of 375.9 minutes), and
    ``named`` is the span of the stage's own tool calls whose input names ``needle`` (the Backchain guide, its artifacts), from
    the stage's start to the end of its authoring. Shares are fractions of the window on the engine clock. Anything the records
    cannot support is ``measured: false`` with the reason."""
    out = Path(out)
    run_dir = Path(run_dir) if run_dir else run_dir_of(out)
    if run_dir is None:
        return {"measured": False, "reason": "no run directory beside the stream"}
    state = engine_state(run_dir)
    accepted = stage_results(run_dir, state)
    stamps = timeline(out / "timeline.jsonl")
    block, _bounds, why = planning_window(run_dir, state, accepted, stamps)
    window = block["window"]
    row = next((r for r in block["stages"] if r["stage"] == stage), None)
    if window["seconds"] is None or row is None or row["seconds"] is None or row["improve_seconds"] is None:
        return {"measured": False, "reason": why or f"the {stage} stage is not in a measured planning window"}
    index = next(i for i, r in enumerate(accepted) if r["action"] == row["action"])
    started, ended = (accepted[index - 1]["t"] if index else run_started(run_dir)), accepted[index]["t"]
    authoring_end = ended - row["improve_seconds"]
    times = []
    for number, event in events(out / "events.jsonl"):
        for _call_id, _tool, arg in tool_call_events(event):
            t = stamps.get(number)
            if t is not None and started < t <= authoring_end and needle in json.dumps(arg).lower():
                times.append(t)
    authoring = round(row["seconds"] - row["improve_seconds"], 1)
    span_seconds = round(max(times) - min(times), 1) if times else None
    return {"measured": True, "stage": stage, "window_seconds": window["seconds"], "through": window["through"],
            "stage_seconds": row["seconds"], "improve_seconds": row["improve_seconds"], "authoring_seconds": authoring,
            "authoring_share": round(authoring / window["seconds"], 4),
            "named": {"needle": needle, "calls": len(times), "span_seconds": span_seconds,
                      "span_share": None if span_seconds is None else round(span_seconds / window["seconds"], 4)}}


def main(argv: list[str] | None = None) -> int:
    """`metrics.py reading-path OUT [--run-dir D] [--limit-events N]` and `metrics.py stage-share OUT [--stage S]`: the reading
    path of a run folder, and the share of the planning window one stage takes, as JSON on stdout."""
    import argparse
    import sys
    parser = argparse.ArgumentParser(description=main.__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("reading-path", "stage-share"):
        one = sub.add_parser(name)
        one.add_argument("out", type=Path)
        one.add_argument("--run-dir", type=Path)
        if name == "reading-path":
            one.add_argument("--limit-events", type=int, help="read only the first N lines of the event stream")
        else:
            one.add_argument("--stage", default="plan")
            one.add_argument("--needle", default="backchain")
    args = parser.parse_args(argv)
    result = (reading_path(args.out, args.run_dir, limit_events=args.limit_events) if args.command == "reading-path"
              else stage_share(args.out, args.run_dir, args.stage, args.needle))
    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
