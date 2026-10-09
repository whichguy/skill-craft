"""The fidelity block of metrics.json: what a run's own records show about how ShipLoop was carried (SPEC, 2026-10-09).

A record, never a verdict. It reads what the run left: ShipLoop's ledger (state.md, tests/, lint/, quality/, backchain/, improve/,
packets/) and the tool calls of the host's event stream, already classified once by metrics.ToolLog. It changes no verdict, exit
code, baseline row or run, starts no process and sends nothing to a model; the model never sees it. Each part is independent and
fails open: an input it cannot read, a stage table or packet layout of another ShipLoop, or an event stream with no tool call makes
the part null with its reason in the block's ``unmeasured`` map, never 0 and never a pass.

  evidence       the class of evidence each accepted action rests on, against the check its stage declares
  validation     ShipLoop's verify records read as JSON; a focused or regression row whose counts are null is unmeasured
  edits          the model's edits of script-owned files, name-pattern kills and git commit/add commands, as listed facts
  refusals       each ShipLoop refusal, and whether the same first line came back in the same stage
  end_state      the engine's status and, for a blocked run, what it awaits
  improve_packets  whether each Improve packet carries its five questions

The heuristic parts (edits, refusals) are a lower bound: no hit is not proof. Known misses are in the README and pinned by tests.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import re
import shlex

import metrics
import runrecord

SCHEMA = "shiploop-e2e-fidelity/v1"
# Files the engine keeps beside a run (shiploop_workspace.MANIFEST, RETURN_PLAN, RETURN_RECEIPT): script-owned, and named in a
# command that has changed directory first, so they are matched by their name.
WORKSPACE_FILES = ("return-plan.md", "return-receipt.md", "workspace.md")
VERIFY_SCHEMA = "shiploop-test-loop/v1"
# The suites whose rows are tests: a row with no count does not show that a test ran. A check row is judged by its exit code.
TEST_SUITES = ("focused", "regression")
RECORD_KINDS = ("verify", "lint", "quality", "backchain", "improve")
SCRIPT_KINDS = ("verify", "lint", "quality", "backchain")
# The record kind each run a stage declares at `done` (the stage table's complete_runs) leaves behind: the lint gate writes
# lint/<action>.gate<N>.md, the test runs write tests/<action>-verify<N>.md, the quality loop's terminal check writes
# quality/<action>-terminal.json. A run this table does not know is not judged (`unmapped_runs`).
RUN_KIND = {"lint-gate": "lint", "test-loop": "verify", "test-probe": "verify", "test-red": "verify", "test-rerun": "verify",
            "quality-terminal": "quality"}
# The five questions an Improve packet (packets/<action>-improve.md) answers for a model that holds only that packet. Anchored to
# the engine's wording (shiploop_navigator _goal_lines, _checked_line, _render_improve, _first_callback_lines); a test pins each
# prefix against the engine's source. The exporter records `carried` labels for producer packets only; if it ever scores Improve
# packets, this table goes.
IMPROVE_QUESTIONS = (
    ("goal", re.compile(r"^Reviewing the returned .* result\. Goal: ", re.M)),
    ("done_when", re.compile(r"^Done when \(", re.M)),
    ("checked_by", re.compile(r"^Checked by:", re.M)),
    ("output", re.compile(r"^(?:The opening file holds exactly these headings|Then run: )", re.M)),
    ("recovery", re.compile(r"^Recovery command:", re.M)),
)
EDIT_LIMITS = ("a lower bound: a script-owned file rewritten by interpreter code (a python3 heredoc), a shell apply_patch or git apply, "
               "a kill by numeric pid and a relative path after cd (other than the three workspace files, matched by name) are not seen")
UNREAD_REASON = ("a verify record that is not shiploop-test-loop/v1 or cannot be read as JSON is not read, so its rows are in no "
                 "count below")
COUNTS_REASON = ("a focused or regression row whose counts are null does not show that a test ran (S-9: a check that ran nothing "
                 "is not a pass), so those rows are unmeasured, not passed")
UNVERIFIED_REASON = "no accepted result carries an unverified key, and a result without the key says nothing (it is not an empty list)"
NO_TOOL_CALLS = "the event stream holds no tool call (events.jsonl missing or empty), so what the model ran is unknown"


class Unmeasured(Exception):
    """A part that cannot be computed from what the run left; the message is the reason recorded in ``unmeasured``."""


# The cuts below (120 and 200 characters of a recorded string) keep a row small; they are a ceiling, not a tuning value.
def clip(text, limit: int = 200) -> str | None:
    text = " ".join(str(text or "").split())
    return (text if len(text) <= limit else text[:limit - 1] + "…") or None


# --- shell commands -------------------------------------------------------------------------------------------------------

SHELL_WRAPPER = re.compile(r"""^\s*(?:\S*/)?(?:sh|bash|zsh)\s+-[a-z]*c[a-z]*\s+(?P<quote>["'])(?P<body>.*)(?P=quote)\s*$""", re.S)


def unwrap_shell(command: str) -> str:
    """The script of a command that is one shell wrapper (`/bin/zsh -lc "<script>"`, how Codex prints its commands; a model may
    write `bash -c '...'` too), else the command as it is. Only a leading wrapper that spans the whole command is stripped. The
    frozen metrics.glue_reasons does not read inside it, so a Codex glue count is a known undercount; only the detectors here do."""
    found = SHELL_WRAPPER.match(command)
    if not found:
        return command
    body = found.group("body")
    return re.sub(r'\\(["\\])', r"\1", body) if found.group("quote") == '"' else body


def shell_view(command: str) -> str:
    """What the shell reads: the wrapper stripped, the variables the command assigns expanded, heredoc bodies (documents) removed."""
    text = unwrap_shell(command)
    return metrics.shell_text(metrics.expand_variables(text, metrics.shell_variables(text)))


SEPARATOR = re.compile(r"&&|\|\||[;|&\n]")
SKIPPED_WORDS = {"sudo", "command", "exec", "time", "nohup", "env", "then", "do", "else", "elif", "if", "while", "until", "!", "{", "(", ")"}
REDIRECT = re.compile(r"^\d?(>>?)(?!&)(.*)$")
SED_IN_PLACE = re.compile(r"^(?:-[nEr]*i\S*|--in-place\S*)$")
PERL_IN_PLACE = re.compile(r"^-[pnlaw]*i\S*$")


def _word(raw: str) -> str:
    return raw.strip("\"'`")


def _words(segment: str) -> list[str]:
    """The words of one simple command, quotes resolved; a segment whose quotes do not balance (a separator inside a quoted string
    cut it in two, or Codex's own quoting) is split at whitespace."""
    try:
        return shlex.split(segment)
    except ValueError:
        return segment.split()


def _files_of(rest: list[str]) -> list[str]:
    """The file operands of an in-place sed or perl: the words that are not options, without the script (the word after -e or -f, or
    else the first operand) and without BSD sed's empty suffix."""
    operands, scripted, index = [], False, 0
    while index < len(rest):
        word = rest[index]
        if word in ("-e", "-f", "--expression", "--file"):
            scripted, index = True, index + 2
        elif word.startswith("-"):
            index += 1
        else:
            operands.append(word)
            index += 1
    operands = [w for w in operands if _word(w)]
    return operands if scripted else operands[1:]


def owned_path(word: str) -> bool:
    """Whether a path is ShipLoop's to write: the harness's own SHIPLOOP_OWNED set (its run directory, Improve receipts and record
    files) and the three workspace files by name, and not a file a packet asks the model to write (MODEL_INPUT)."""
    word = _word(word)
    return bool(word) and not metrics.MODEL_INPUT.search(word) and bool(
        metrics.SHIPLOOP_OWNED.search(word) or word.rsplit("/", 1)[-1] in WORKSPACE_FILES)


def _written(words: list[str]) -> list[tuple[str, str]]:
    """(form, target) for each file one simple command writes: a redirect, tee, cp (its last operand), mv, rm, sed -i, perl -i."""
    found: list[tuple[str, str]] = []
    for index, word in enumerate(words):
        redirect = REDIRECT.match(word)
        if redirect and redirect.group(2):
            found.append((redirect.group(1), _word(redirect.group(2))))
        elif re.fullmatch(r"\d?>>?", word) and index + 1 < len(words):
            found.append((word.lstrip("0123456789"), _word(words[index + 1])))
    first = next((i for i, w in enumerate(words) if w not in SKIPPED_WORDS and not re.match(r"\w+=", w)), None)
    if first is None:
        return found
    verb, rest, skip = words[first], [], False
    for word in words[first + 1:]:  # the arguments, without redirects and the word a standalone `>` or `>>` names
        if skip:
            skip = False
        elif word in (">", ">>") or re.fullmatch(r"\d>>?", word):
            skip = True
        elif not REDIRECT.match(word):
            rest.append(word)
    operands = [w for w in rest if not w.startswith("-")]
    if verb == "tee":
        found += [("tee", _word(w)) for w in operands]
    elif verb == "cp" and operands:
        found.append(("cp", _word(operands[-1])))
    elif verb in ("mv", "rm"):
        found += [(verb, _word(w)) for w in operands]
    elif verb == "sed" and any(SED_IN_PLACE.match(w) for w in rest):
        found += [("sed -i", _word(w)) for w in _files_of(rest)]
    elif verb == "perl" and any(PERL_IN_PLACE.match(w) for w in rest):
        found += [("perl -i", _word(w)) for w in _files_of(rest)]
    return found


def shell_edits(command: str) -> list[dict]:
    """The script-owned files a shell command writes: [{"form", "target"}], each owned target of each simple command. Heredoc bodies
    are documents and not read; a rewrite by interpreter code (python3 - <<EOF ... open(p, "w")) is a known miss."""
    hits = []
    for segment in SEPARATOR.split(shell_view(command)):
        for form, target in _written(_words(segment)):
            if owned_path(target):
                hits.append({"form": form, "target": target[:200]})
    return hits


NAME_KILL = re.compile(r"(?:(?:^|[;&|(])[ \t]*(?:(?:then|do|else)[ \t]+)?(?:sudo[ \t]+)?(?P<by>(?:pkill|killall)\b[^\n;&|)]*)"
                       r"|(?P<pipe>\bpgrep\b[^\n;&]*\|[ \t]*xargs[ \t]+(?:-\S+[ \t]+)*kill\b[^\n;&|]*)"
                       r"|(?P<sub>\bkill\b[^\n;&|]*(?:\$\(|`)[ \t]*pgrep\b[^\n)`]*[)`]))", re.M)


TRAILING_REDIRECT = re.compile(r"(?:\s+\d?>>?\S*)+$")


def name_kills(command: str) -> list[str]:
    """The kills by process name a command runs (pkill, killall, pgrep piped to kill, kill of a pgrep): they match any run's server
    by its name. A kill by numeric pid is out of scope (a model's own job and a sibling's look alike). Reads strings only."""
    found = (m.group("by") or m.group("pipe") or m.group("sub") for m in NAME_KILL.finditer(shell_view(command)))
    return [TRAILING_REDIRECT.sub("", text.strip())[:120] for text in found]


# `git [-C path] [-c key=value] [--option] commit|add`: the subcommand, not a word of a path or a message that says add or commit.
GIT_SUBCOMMAND = re.compile(r"\bgit\b(?:\s+(?:-C|-c|--git-dir|--work-tree)\s+\S+|\s+--?\S+)*\s+(commit|add)\b")


def commit_forms(command: str) -> list[str]:
    """`git add` and `git commit` invocations of a command, in order, by the frozen glue reader's own pattern (one meaning of a
    model commit command) applied to the unwrapped command."""
    return ["git " + (GIT_SUBCOMMAND.search(m.group(0)) or re.search(r"\b(commit|add)\b", m.group(0))).group(1)
            for m in metrics.GLUE_COMMIT.finditer(shell_view(command))]


# --- evidence -------------------------------------------------------------------------------------------------------------

def _refs(entry: dict, action: str) -> dict:
    """How an accepted result's evidence_refs split: the action's own packet, inbox or result file (a ref that names the action;
    another action's result is a cited file); a note the model wrote (the harness's MODEL_INPUT: run/notes, run/evidence,
    run/scratch, Improve reviews); anything else. The refs are paths of the machine that ran, so whether they still exist is not
    asked: the engine checked at the callback."""
    own = note = outside = 0
    owned = re.compile(r"/run/(?:packets|inbox|results)/" + re.escape(action) + r"(?:[.\-/]|$)")
    for ref in entry.get("evidence_refs") or []:
        ref = str(ref)
        if owned.search(ref):
            own += 1
        elif metrics.MODEL_INPUT.search(ref):
            note += 1
        else:
            outside += 1
    return {"own": own, "note": note, "outside": outside}


def _records(run_dir: Path, action: str, improved: dict) -> list[str]:
    """The records ShipLoop's scripts wrote for one action, from the file names of the ledger. A lint record counts when it is the
    gate (`lint/<action>.gate<N>.md`): the advisory passes (`<action>.md`, `<action>.<N>.md`) are the lint's own text "not exit-criteria
    evidence"."""
    found = []
    if any(run_dir.glob(f"tests/{action}-verify*.md")):
        found.append("verify")
    if any(run_dir.glob(f"lint/{action}.gate*.md")):  # the gate the script ran at done; an advisory pass is supporting output
        found.append("lint")
    if (run_dir / "quality" / f"{action}-terminal.json").is_file():
        found.append("quality")
    if any(run_dir.glob(f"backchain/{action}/check-*.json")):
        found.append("backchain")
    if action in improved or (run_dir / "improve" / action / "receipt.md").is_file():
        found.append("improve")
    return found


def evidence(run_dir: Path | None, state: dict, declared: dict | None) -> dict:
    """One row per accepted action (state.md's history, in order) with the class of evidence it rests on.

    Precedence: skipped (the engine's own not-applicable entry), script (a verify, lint, quality-terminal or backchain-check record
    the script wrote), loop (an Improve child), file (a cited file that is neither the stage's own nor a model note), note (only
    model-authored notes), sentence (nothing beyond its own packet, inbox or result file). `records` lists every kind found, because
    the precedence hides a review loop behind a script record. `declared` is the check the stage table declares for the stage
    (None when the table could not be read). `needs` is the record kinds the stage's declared runs leave (RUN_KIND; without a lint
    gate when the run's lint option is off) and `lacks` the ones the action has none of; `declared_script_run_without_record` names a
    done, not skipped stage that declares a script-run check and lacks any of them, so one script's record does not stand in for
    another's. A run RUN_KIND does not know makes `needs` None, is not judged and is named in `unmapped_runs`. A reading aid, not a
    target: citing any file makes a row `file`."""
    history = state.get("history") if isinstance(state, dict) else None
    if run_dir is None or not isinstance(history, list):
        raise Unmeasured("state.md records no history (no ShipLoop run directory, or one of another layout)")
    accepted = state.get("accepted") if isinstance(state.get("accepted"), dict) else {}
    improved = state.get("improve_results") if isinstance(state.get("improve_results"), dict) else {}
    counts = {"script": 0, "loop": 0, "file": 0, "note": 0, "sentence": 0, "skipped": 0, "unclassified": 0}
    kinds = dict.fromkeys(RECORD_KINDS, 0)
    rows, missing, unmapped = [], [], set()
    lint_off = state.get("lint") == "off"
    for item in history:
        if not isinstance(item, dict) or not isinstance(item.get("action"), str):
            continue
        action = item["action"]
        entry = accepted.get(action) if isinstance(accepted.get(action), dict) else None
        records = _records(run_dir, action, improved)
        for kind in records:
            kinds[kind] += 1
        refs = _refs(entry, action) if entry is not None else None
        summary = str((entry or {}).get("summary") or item.get("summary") or "")
        if entry is None:
            klass = "unclassified"
        elif summary.startswith(metrics.NOT_APPLICABLE):
            klass = "skipped"
        elif set(SCRIPT_KINDS) & set(records):
            klass = "script"
        elif "improve" in records:
            klass = "loop"
        else:
            klass = "file" if refs["outside"] else "note" if refs["note"] else "sentence"
        counts[klass] += 1
        row = (declared or {}).get(item.get("stage")) or {}
        check, runs = row.get("check"), row.get("runs") or []
        known = [RUN_KIND[name] for name in runs if name in RUN_KIND]
        unknown = [name for name in runs if name not in RUN_KIND]
        unmapped.update(unknown)
        needs = None if declared is None or unknown else sorted({kind for kind in known if not (lint_off and kind == "lint")})
        lacks = None if needs is None else [kind for kind in needs if kind not in records]
        if check == "script-run" and item.get("outcome") == "done" and klass != "skipped" and lacks:
            missing.append(item.get("stage"))
        rows.append({"action": action, "stage": item.get("stage"), "work_item": item.get("workitem"), "outcome": item.get("outcome"),
                     "declared": check, "needs": needs, "lacks": lacks, "class": klass, "records": records, "refs": refs})
    return {"counts": counts, "records": kinds,
            "declared_script_run_without_record": None if declared is None else missing,
            "unmapped_runs": sorted(unmapped), "stages": rows}


_EXPORTERS: dict[Path, object] = {}


def _exporter(path):
    """The Run Review exporter loaded as a module (the route run.review_export takes), once per file."""
    if path is None or not Path(path).is_file():
        raise Unmeasured("the Run Review exporter is missing, so the stage table cannot be read")
    path = Path(path)
    if path not in _EXPORTERS:
        spec = importlib.util.spec_from_file_location("fidelity_run_review_export", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _EXPORTERS[path] = module
    return _EXPORTERS[path]


def declared_checks(state: dict, engine_scripts, exporter) -> dict:
    """{stage: {"check": the exit check its row declares, "runs": the runs it declares at done}} from the stage table of the ShipLoop
    the run used, read by the exporter's own stage_catalog and effective_exit_check (planning_review `none` reads the planning stages
    as model judgement)."""
    module = _exporter(exporter)
    if engine_scripts is None:
        raise Unmeasured("the ShipLoop scripts directory of the run is not known, so its stage table cannot be read")
    catalog = module.stage_catalog(module.load_stage_spec(Path(engine_scripts) / "shiploop_stage_spec.py"))
    mode = metrics.planning_review(state)
    return {entry["stage"]: {"check": module.effective_exit_check(entry, mode), "runs": list(entry.get("completeRuns") or [])}
            for entry in catalog}


# --- validation -----------------------------------------------------------------------------------------------------------

def _verify_record(path: Path) -> dict | None:
    found = metrics.STATE_BLOCK.search(path.read_text(errors="replace"))
    try:
        record = json.loads(found.group("json")) if found else None
    except ValueError:
        return None
    return record if isinstance(record, dict) and record.get("schema") == VERIFY_SCHEMA and isinstance(record.get("runs"), list) else None


def validation(run_dir: Path | None) -> dict:
    """ShipLoop's verify records (tests/<action>-verify<N>.md) read as JSON. Counts and presence only, no threshold.

    ``tests_ran_unmeasured`` is the focused and regression rows whose counts are null; ``zero_ran`` the rows that counted a test
    and ran none. ``unread`` is the records that are not shiploop-test-loop/v1 or not JSON: their rows are in no count. The regex
    reader metrics.verifications stays what baselines use; a test pins that both agree on the saved runs."""
    if run_dir is None or not Path(run_dir).is_dir():
        raise Unmeasured("no ShipLoop run directory, so its verify records cannot be read")
    files = sorted(Path(run_dir).rglob("*-verify*.md"))
    suites: dict[str, dict] = {}
    commands, schemas, accepted_stages = set(), set(), set()
    passed = could_not_run = red = unread = runs = accepted_rows = 0
    release = None
    for path in files:
        record = _verify_record(path)
        if record is None:
            unread += 1
            continue
        schemas.add(record["schema"])
        passed += record.get("passed") is True
        could_not_run += record.get("disposition") == "could-not-run"
        rows = [row for row in record["runs"] if isinstance(row, dict)]
        red += any(row.get("status") == "red" for row in rows)
        observed = record.get("observed")
        if isinstance(observed, dict) and observed.get("where"):
            release = {"where": observed.get("where"), "kind": observed.get("kind")}
        for row in rows:
            runs += 1
            commands.add(str(row.get("command")))
            suite = suites.setdefault(str(row.get("suite")), {"runs": 0, "counted": 0, "counts_null": 0, "zero_ran": 0})
            suite["runs"] += 1
            counts = row.get("counts")
            ran = counts.get("ran") if isinstance(counts, dict) else None
            if isinstance(ran, int) and not isinstance(ran, bool):
                suite["counted"] += 1
                suite["zero_ran"] += ran == 0
            else:
                suite["counts_null"] += 1
            if "accepted_ran" in row:
                accepted_rows += 1
                accepted_stages.add(str(record.get("stage")))
    return {"records": len(files), "unread": unread, "runs": runs, "distinct_commands": len(commands), "passed": passed,
            "could_not_run": could_not_run, "red": red, "schemas": sorted(schemas),
            "by_suite": dict(sorted(suites.items())),
            "tests_ran_unmeasured": sum(suites.get(name, {}).get("counts_null", 0) for name in TEST_SUITES),
            "accepted_ran": {"runs": accepted_rows, "stages": sorted(accepted_stages)}, "release_verify": release}


# --- the model's edits, kills and commits ---------------------------------------------------------------------------------

def edits(tools) -> dict:
    """What the model ran that touches ShipLoop's side of the work, as listed facts with the event number of each (a line of
    events.jsonl). Heuristic and a lower bound (``limits``). ``script_owned`` are edits of files ShipLoop's scripts own, by an edit
    tool or a shell write; ``name_kills`` are kills by process name; ``model_commits`` are the calls that ran git commit or add
    (the frozen model_glue counts them too, but does not read inside a Codex `zsh -lc` string)."""
    if tools is None or not tools.sequence:
        raise Unmeasured(NO_TOOL_CALLS)
    owned, kills, commits = [], [], []
    for call in tools.sequence:
        where = {"event": call["event"], "tool": call["tool"]}
        if call["command"]:
            owned += [{**where, **hit} for hit in shell_edits(call["command"])]
            kills += [{**where, "form": form} for form in name_kills(call["command"])]
            if forms := commit_forms(call["command"]):
                commits.append({**where, "forms": forms})
        elif metrics.WRITE_TOOL.search(call["tool"]):
            owned += [{**where, "form": "edit tool", "target": path} for path in call["paths"] if owned_path(path)]
    return {"script_owned": owned, "name_kills": kills, "model_commits": commits, "limits": EDIT_LIMITS}


# --- refusals -------------------------------------------------------------------------------------------------------------

def stage_of(event, stamps: dict, labels: list, windows: list):
    """The stage whose window holds one event (the join per_stage uses), or None: no timeline, or an event the runner did not stamp.
    Stamps are whole seconds, so an event next to a boundary can fall in the neighbouring stage."""
    t = stamps.get(event)
    if t is None:
        return None
    for label, window in zip(labels, windows):
        if window is not None and metrics.within(t, window[0], window[1]):
            return label
    return None


def refusals(tools, out: Path, run_dir: Path | None, state: dict) -> dict:
    """Each ShipLoop refusal, from the same list as ``shiploop_failures`` (one count), with the stage it came in and whether it is a
    repeat: the refusal just before it has the same whole first line (not the 200-character cut) in the same known stage. A repeat
    with an unknown stage is not flagged. The same line twice is a pointer, neutral about cause (a remedy that misled, or an honest
    second failed try)."""
    if tools is None or not tools.sequence:
        raise Unmeasured(NO_TOOL_CALLS)
    stamps = metrics.timeline(Path(out) / "timeline.jsonl")
    accepted = metrics.stage_results(run_dir, state)
    pending = metrics.pending_stage(state)
    labels = [row["stage"] for row in accepted] + ([pending] if pending else [])
    windows = metrics.stage_windows(accepted, stamps, pending)
    items, previous = [], None
    for index, (failure, found) in enumerate(zip(tools.failures, tools.failure_events)):
        stage = stage_of(found["event"], stamps, labels, windows)
        repeat = previous is not None and stage is not None and previous == (found["line"], stage)
        items.append({"event": found["event"], "verb": failure["verb"], "exit": failure["exit"], "stage": stage,
                      "line": failure["line"], "repeat_of": index - 1 if repeat else None})
        previous = (found["line"], stage)
    return {"count": len(tools.failures), "repeated": sum(item["repeat_of"] is not None for item in items), "items": items}


# --- end state, Improve packets -------------------------------------------------------------------------------------------

def end_state(state: dict) -> dict:
    """The engine's own record of where the run stood: status, stage, the stage it never accepted, its stated reason; for a run that
    ended on a blocked result, the last accepted entry's ``blocked_by`` and ``awaiting`` (the kind, and whether it states why no
    default would do); the product-acceptance ``unverified`` list (None when no result carries the key). Nothing here is a verdict."""
    if not isinstance(state, dict) or not state.get("status"):
        raise Unmeasured("state.md records no status (no ShipLoop run directory, or one of another layout)")
    history = [h for h in state.get("history") or [] if isinstance(h, dict)]
    accepted = state.get("accepted") if isinstance(state.get("accepted"), dict) else {}
    last = accepted.get(history[-1].get("action")) if history else None
    last = last if isinstance(last, dict) else {}
    awaiting = last.get("awaiting") if isinstance(last.get("awaiting"), dict) else None
    unverified = None
    for item in history:
        entry = accepted.get(item.get("action"))
        if isinstance(entry, dict) and isinstance(entry.get("unverified"), list):
            unverified = entry["unverified"]
    return {"status": state.get("status"), "stage": metrics.current_stage(state), "unaccepted_stage": metrics.pending_stage(state),
            "status_reason": clip(state.get("status_reason")), "blocked_by": last.get("blocked_by"),
            "awaiting": None if awaiting is None else {"kind": awaiting.get("kind"),
                                                       "no_default": bool(str(awaiting.get("no_default") or "").strip())},
            "unverified": None if unverified is None else {
                "entries": len(unverified),
                "owners": sorted({str(u["owner"]) for u in unverified if isinstance(u, dict) and u.get("owner")})}}


def improve_packets(run_dir: Path | None, state: dict) -> dict:
    """Whether each Improve child's packet carries its five questions (IMPROVE_QUESTIONS): label counts and, for a packet that lacks
    any, its action, stage and the labels it lacks. Never the packet text. Only the files of the current layout are read."""
    files = sorted(Path(run_dir).glob("packets/*-improve.md")) if run_dir is not None else []
    if not files:
        raise Unmeasured("no packets/<action>-improve.md file (no Improve child ran, or ShipLoop 1.22.0 or earlier, whose "
                         "one packet file per action is not read)")
    stages = {h.get("action"): h.get("stage") for h in (state.get("history") or []) if isinstance(h, dict)}
    carried = {name: 0 for name, _ in IMPROVE_QUESTIONS}
    missing = []
    for path in files:
        text = path.read_text(errors="replace")
        lacking = [name for name, pattern in IMPROVE_QUESTIONS if not pattern.search(text)]
        for name, _ in IMPROVE_QUESTIONS:
            carried[name] += name not in lacking
        action = path.name[:-len("-improve.md")]
        if lacking:
            missing.append({"action": action, "stage": stages.get(action), "labels": lacking})
    return {"read": len(files), "carried": carried, "missing": missing}


# --- the block ------------------------------------------------------------------------------------------------------------

def build(out: Path, run_dir: Path | None, tools, *, engine_scripts=None, exporter=None) -> dict:
    """The fidelity block of one run folder. ``tools`` is the metrics.ToolLog that metrics.collect filled (None where the run has no
    stream); ``engine_scripts`` the scripts directory of the ShipLoop the run used, ``exporter`` the Run Review exporter, which together
    read the run's stage table. Every part fails open: an exception is the part's reason in ``unmeasured``."""
    out = Path(out)
    state = metrics.engine_state(run_dir)
    block = {"schema": SCHEMA, "hosts": runrecord.hosts_used(out), "mixed_host": runrecord.mixed_host(out),
             "tool_calls_seen": len(tools.sequence) if tools is not None else 0, "unmeasured": {}}
    gone = block["unmeasured"]

    def part(name: str, make, *args):
        try:
            block[name] = make(*args)
        except Unmeasured as why:
            block[name], gone[name] = None, str(why)
        except Exception as exc:  # noqa: BLE001 - any one part failing leaves the others
            block[name], gone[name] = None, f"{type(exc).__name__}: {' '.join(str(exc).split())[:300]}"

    declared = None
    try:
        declared = declared_checks(state, engine_scripts, exporter)
    except Unmeasured as why:
        gone["declared"] = str(why)
    except Exception as exc:  # noqa: BLE001 - an older or incompatible stage table
        gone["declared"] = f"{type(exc).__name__}: {' '.join(str(exc).split())[:300]}"
    part("evidence", evidence, run_dir, state, declared)
    part("validation", validation, run_dir)
    part("edits", edits, tools)
    part("refusals", refusals, tools, out, run_dir, state)
    part("end_state", end_state, state)
    part("improve_packets", improve_packets, run_dir, state)
    if block["validation"]:
        if block["validation"]["tests_ran_unmeasured"]:
            gone["validation.counts"] = COUNTS_REASON
        if block["validation"]["unread"]:
            gone["validation.unread"] = UNREAD_REASON
    if block["evidence"] and block["evidence"]["unmapped_runs"]:
        gone["declared.runs"] = ("the stage table declares runs this reader does not know (" + ", ".join(block["evidence"]["unmapped_runs"])
                                 + "), so the stages that declare them are not judged")
    if block["end_state"] and block["end_state"]["unverified"] is None:
        gone["end_state.unverified"] = UNVERIFIED_REASON
    return block


def safe_build(out: Path, run_dir: Path | None, tools, **options) -> dict:
    """build, or an error block when it raises: a problem here is recorded and never changes a verdict or the exit code."""
    try:
        return build(out, run_dir, tools, **options)
    except Exception as exc:  # noqa: BLE001
        return {"schema": SCHEMA, "error": f"{type(exc).__name__}: {' '.join(str(exc).split())[:300]}"}


def lines(block: dict) -> list[str]:
    """At most five report lines, each saying what the figure is a count of and, where it is heuristic, that no hit is not proof.
    (Not worded "lower bound": the report's cost note uses that phrase and a test asserts its absence from a clean run's report.)"""
    if block.get("error"):
        return [f"skipped: {block['error']}"]
    gone = block.get("unmeasured") or {}
    result = []
    ev = block.get("evidence")
    if ev:
        c = ev["counts"]
        no_record = ev["declared_script_run_without_record"]
        records = ", ".join(f"{kind} {n}" for kind, n in ev["records"].items())
        result.append(f"evidence {len(ev['stages'])} accepted: script {c['script']}, loop {c['loop']}, file {c['file']}, "
                      f"note {c['note']}, sentence {c['sentence']}, skipped {c['skipped']} (records: {records}); declared "
                      f"script-run without a record: "
                      + (f"unmeasured ({gone.get('declared')})" if no_record is None else ", ".join(no_record) or "none"))
    else:
        result.append(f"evidence unmeasured: {gone.get('evidence')}")
    v = block.get("validation")
    if v:
        result.append(f"validation {v['records']} records / {v['runs']} runs / {v['distinct_commands']} commands: test counts "
                      f"unmeasured {v['tests_ran_unmeasured']}, zero-ran {sum(s['zero_ran'] for s in v['by_suite'].values())}, "
                      f"red {v['red']}, accepted_ran at {len(v['accepted_ran']['stages'])} stages"
                      + (f", release verified {v['release_verify']['where']}" if v["release_verify"] else ""))
    else:
        result.append(f"validation unmeasured: {gone.get('validation')}")
    e = block.get("edits")
    result.append(f"edits (heuristic, no hit is not proof): script-owned edits {len(e['script_owned'])}, name-pattern kills "
                  f"{len(e['name_kills'])}, model commit commands {len(e['model_commits'])}" if e
                  else f"edits unmeasured: {gone.get('edits')}")
    r = block.get("refusals")
    if r:
        repeat = next((i for i in r["items"] if i["repeat_of"] is not None), None)
        result.append(f"refusals {r['count']}, repeated {r['repeated']}" + (f": \"{(repeat['line'] or '')[:100]}\"" if repeat else ""))
    else:
        result.append(f"refusals unmeasured: {gone.get('refusals')}")
    s, p = block.get("end_state"), block.get("improve_packets")
    state_text = (f"end state {s['status']}" + (f" at {s['unaccepted_stage']}" if s["unaccepted_stage"] else "")
                  + (f", blocked by {s['blocked_by']}" if s["blocked_by"] else "")
                  + (f", unverified {s['unverified']['entries']}" if s["unverified"] else "") if s
                  else f"end state unmeasured: {gone.get('end_state')}")
    packet_text = (f"Improve packets {p['read']}: all five {p['read'] - len(p['missing'])}, lacking {len(p['missing'])}" if p
                   else f"Improve packets unmeasured: {gone.get('improve_packets')}")
    result.append(f"{state_text}; {packet_text}")
    return result
