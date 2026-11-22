#!/usr/bin/env python3
"""Read the deliveries of the answers candidate: what the requester answered, where the engine says each answer
stands, the proof the stage after the spec returned, the entry before and after, and how the harness judged the run.

Usage: ``read_answers.py ROOT [NAME ...] [--json FILE] [--export DIR]``.  ROOT holds one output folder per delivery
(``launch_wave.sh``), the stand-in's record ``<NAME>-requester.json`` beside each, and the build copy
``apparatus-*/skills/shiploop/scripts`` whose own modules read the run (``shiploop_answers.standing``,
``shiploop_owner_notes.notes``, ``shiploop_defaults``, ``shiploop_knowledge_home.entries_after``,
``shiploop_store.read_record``).  With no NAME every delivery folder is read; one without ``result.json`` is printed
from what its run folder shows so far, marked "not ended".  ``--export DIR`` writes, for each delivery with an applied
answer, ``DIR/<NAME>/`` with ``row.txt``, ``answer.txt``, ``before.md`` and ``after.md`` and nothing about checks or
outcomes.  It writes nothing into a delivery's folder.  Home paths are printed as ``~``.

A bound note no ``answers`` row applied (late, replaced or superseded) gets a block headed "the held answer", and the
same facts under the JSON key ``held``: when it was written (the trace's ``note`` command; the last accepted action
before it and the action open then, from ``timeline.json``, ``state.md``'s history and the trace); its requirement's
entry then (the newest commit of the living spec at or before the answer, kept only when its digest is the note's
``entry_sha256``) and at the end (the run's checkout); the accepted results after it that name it; the commits after
it; the trace's non-zero commands after it; how the run ended; and the packets that printed the held line.  A
delivery with no applied answer exports its first held answer the same way; ``before.md``'s first line says which
text it holds.

A delivery whose stand-in sent a PLAIN note during the build (its record's ``mode`` is "note-at") gets a block "the late
note" and the JSON key ``late_note``: the same seven items for that note, with the requirement the chosen row of
``rows_at_send`` names, its newest committed entry at or before the note (unverified: a plain note stores no digest),
and what the owner-notes module and the trace recorded of the note; it is exported like a held answer.  A second run on
a project an earlier delivery left (the harness's ``follow_on``) gets a block "second run" and the JSON key
``second_run``: the prior, the request, and what the run changed in ``work/`` since ``start_head``; it is not exported.
Every other delivery has both keys null.
"""
from __future__ import annotations

import argparse
import datetime
import html
import json
import os
import re
import subprocess
import sys
from pathlib import Path

VERDICTS = ("invoked", "plugin", "process", "shiploop", "committed")
STARTUP = ("migrate", "restart", "switch", "rollback", "cli")
HOME = os.path.expanduser("~")
TAG = re.compile(r"<[^>]+>")
# Where a bound note stands when no ``answers`` row applied it: the notes "the held answer" block reads.
HELD_STANDS = ("late", "replaced", "superseded")
MENTIONS = re.compile(r"owner note|requester|answer", re.IGNORECASE)
ANSWER = re.compile(r"answer", re.IGNORECASE)
# The late plain note's block: "requester" and "answer" left out (the product "answering" a request matched them).
NAMED_NOTE = re.compile(r"owner note", re.IGNORECASE)
CODE = ("src/", "bin/")
TESTS = ("test/",)


def tilde(text: object) -> str:
    return str(text).replace(HOME, "~")


def load(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def clock(stamp: float | None) -> str | None:
    return datetime.datetime.fromtimestamp(stamp, datetime.UTC).strftime("%Y-%m-%d %H:%M:%SZ") if stamp else None


def instant(stamp: float) -> str:
    """A time to the millisecond, so two events of one second keep their order on the page."""
    return datetime.datetime.fromtimestamp(stamp, datetime.UTC).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3] + "Z"


def epoch(at: object) -> float | None:
    """The time an ISO stamp of the run names ("2026-11-22T19:13:37Z"), or None when it does not read as one."""
    try:
        return datetime.datetime.fromisoformat(str(at)).timestamp()
    except ValueError:
        return None


def git(repo: Path, *args: str) -> str | None:
    """What ``git -C repo`` prints, or None when it fails."""
    try:
        done = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, encoding="utf-8",
                              errors="replace", check=False)
    except OSError:
        return None
    return done.stdout if done.returncode == 0 else None


def engine(root: Path):
    """The engine's own modules, from the build copy the deliveries run."""
    scripts = sorted(root.glob("apparatus-*/skills/shiploop/scripts"))
    if not scripts:
        sys.exit(f"no apparatus-*/skills/shiploop/scripts under {root}")
    sys.path.insert(0, str(scripts[-1]))
    import shiploop_answers as answers
    import shiploop_defaults as defaults
    import shiploop_knowledge_home as knowledge
    import shiploop_owner_notes as owner_notes
    import shiploop_store as store
    return answers, defaults, knowledge, owner_notes, store


def run_folder(out: Path, result: dict, store) -> tuple[Path | None, int]:
    """The ShipLoop run the harness names, else the one with the longest history; and how many run folders exist."""
    folders = [path.parent for path in out.glob(".shiploop-runs/*/run/state.md")]
    named = Path(str((result.get("shiploop") or {}).get("run_dir") or load(out / "shiploop-run.json").get("run_dir") or ""))
    if (named / "state.md").is_file():
        return named, len(folders)

    def length(path: Path) -> int:
        try:
            return len(store.read_record(path / "state.md").get("history") or [])
        except Exception:  # noqa: BLE001 - a state file being written
            return -1
    return (max(folders, key=length) if folders else None), len(folders)


def trace_rows(run: Path) -> list[dict]:
    try:
        lines = (run / "trace.jsonl").read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    rows = []
    for line in lines:
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def stage_of(row: dict) -> str:
    stage = row.get("stage")
    return str(stage[0] if isinstance(stage, list) and stage else stage)


def trace(run: Path) -> dict:
    """Held callbacks, refusals naming ``answers``, and every other refused command by stage, kept apart; a failed
    check is a check, not a refusal (the trace's own rule), and is counted on its own."""
    held, naming, other, checks = [], [], {}, {}
    for row in trace_rows(run):
        if row.get("kind") != "command" or row.get("exit") in (0, None) or row.get("crashed"):
            continue
        stage, text = stage_of(row), " ".join(str(row.get("error") or "").split())
        if row.get("held"):
            held.append({"stage": stage, "notes": row["held"]})
        elif row.get("verb") == "check":
            checks[stage] = checks.get(stage, 0) + 1
        elif "answers" in text:
            naming.append({"stage": stage, "text": tilde(text[:200])})
        else:
            other[stage] = other.get(stage, 0) + 1
    return {"held": held, "naming_answers": naming, "other_refusals_by_stage": other, "failed_checks_by_stage": checks}


def packet_texts(run: Path) -> list[tuple[Path, str]]:
    return [(path, path.read_text(encoding="utf-8", errors="replace")) for path in sorted((run / "packets").glob("*.md"))]


def displays(run: Path, ids: list[str]) -> dict:
    packets = packet_texts(run)
    done = [(path, text) for path, text in packets if "\nIt's all complete." in "\n" + text]
    mention = re.compile(r"nswered by the requester|Answers held for a new run" + "".join(
        r"|\b" + re.escape(ident) + r"\b" for ident in ids))
    done_lines = ([line for line in max(done, key=lambda item: item[0].stat().st_mtime)[1].splitlines()
                   if mention.search(line)] if done else None)
    report = run / "report.html"
    report_lines = None
    if report.is_file():
        parts = TAG.split(report.read_text(encoding="utf-8", errors="replace"))
        shown = re.compile(r"answered by the requester|answered row \d+", re.IGNORECASE)
        report_lines = [html.unescape(" ".join(part.split())) for part in parts if shown.search(part)]
    return {"packets_with_the_block": sum("\nAnswers to defaults (" in "\n" + text for _path, text in packets),
            "packets_with_the_held_line": sum("Answers held for a new run" in text for _path, text in packets),
            "packets": len(packets), "done_packet_lines": done_lines, "report_lines": report_lines}


def last_message(out: Path) -> str | None:
    """The host's last message: the last ``text`` event (Codex, Grok) or the ``result`` event (Claude Code)."""
    text = None
    try:
        lines = (out / "events.jsonl").read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return None
    for line in lines:
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") == "text" and isinstance(event.get("data"), str) and event["data"].strip():
            text = event["data"]
        elif event.get("type") == "result" and isinstance(event.get("result"), str) and event["result"].strip():
            text = event["result"]
    return tilde(text) if text else None


def harness(out: Path) -> dict:
    result, metrics, invocation = load(out / "result.json"), load(out / "metrics.json"), load(out / "invocation.json")
    row = {key: result.get(key, invocation.get(key)) for key in ("host", "model", "effort")}
    if not result:
        row.update(ended=False, started=tilde((invocation.get("environment") or {}).get("at") or "not recorded"))
        return row
    span = result.get("span") or {}
    checks = [check for check in result.get("checks") or [] if isinstance(check, dict)]

    def name(check: dict) -> str:
        return " ".join(str(check.get("command") or "").replace('"', "").split()[1:]).split("/")[-1]
    stages = metrics.get("stages") or []
    row.update(
        ended=True, outcome=result.get("outcome_class"), basis=result.get("outcome_basis"),
        verdicts={key: (result.get(key) or {}).get("pass") for key in VERDICTS},
        checks_passed=sum(bool(check.get("pass")) for check in checks), checks=len(checks),
        failed=[{"check": name(check), "output_end": tilde(" ".join(str(check.get("output") or "").split())[-240:])}
                for check in checks if not check.get("pass")],
        startup={probe: next((bool(check.get("pass")) for check in checks
                              if re.search(r"due_times_probe\.py\W+" + probe + r"\b", str(check.get("command")))), None)
                 for probe in STARTUP},
        started=clock(span.get("started")), ended_at=clock(span.get("ended")),
        minutes=round((span["ended"] - span["started"]) / 60, 1) if span.get("started") and span.get("ended") else None,
        turns=metrics.get("turns"), model_calls=metrics.get("model_calls"),
        output_tokens=(metrics.get("tokens") or {}).get("output"), cost_usd=metrics.get("cost_usd"),
        spec_seconds=sum(stage.get("seconds") or 0 for stage in stages if stage.get("stage") == "spec") or None,
        strategy_seconds=sum(stage.get("seconds") or 0 for stage in stages if stage.get("stage") == "test-strategy") or None)
    return row


def checkout(state: dict, out: Path) -> Path | None:
    """The run's own checkout (state.md's ``repo``), else the folder the host ran in (invocation.json's ``cwd``): the
    first that is a git checkout; None when neither is."""
    for path in (state.get("repo"), load(out / "invocation.json").get("cwd")):
        if path and git(Path(str(path)), "rev-parse", "--git-dir") is not None:
            return Path(str(path))
    return None


def spec_then(repo: Path, requirement: str, moment: float, knowledge) -> tuple[str | None, str | None]:
    """(the commit, ``requirement``'s entry as it holds it) for the newest commit of the living spec made at or before
    ``moment``'s second; the text is None when that commit has no such entry, both are None when no commit is that old.
    The engine's own entry parser reads the committed text, as ``entries_after`` does."""
    spec = knowledge.HOME + "/spec.md"
    for line in (git(repo, "log", "--format=%H %ct", "--", spec) or "").splitlines():
        commit, at = line.split()
        if int(at) <= moment:
            shown = git(repo, "show", f"{commit}:{spec}") or ""
            entry = knowledge._entries(shown, "R").get(requirement) if shown.strip() else None
            return commit, entry.text if entry else None
    return None, None


def written(note: dict, rows: list[dict], history: list[dict], times: dict) -> dict:
    """When the note was written (the trace's ``note`` command, else its ``written_at``), the last accepted action
    before then, and the action open then."""
    wrote = next((row for row in rows if row.get("verb") == "note" and row.get("note") == note["id"]), None)
    moment = wrote["ts"] if wrote and wrote.get("ts") else epoch(note["written_at"])
    if moment is None:
        return {"moment": None, "not_recorded": "the note's written_at does not read as a time"}
    before = [entry for entry in history if times.get(entry.get("action")) is not None
              and times[entry["action"]] <= moment]
    last = before[-1] if before else None
    if wrote:
        action, stage, source = (wrote.get("cursor") or [None])[0], stage_of(wrote), "the trace's note command"
    else:
        earlier = [row for row in rows if row.get("ts") and row["ts"] <= moment and row.get("kind") in ("packet", "command")]
        row = earlier[-1] if earlier else {}
        packet = row.get("kind") == "packet"
        action = row.get("action") if packet else (row.get("cursor") or [None])[-1]
        stage = row.get("stage") if packet else (row.get("stage") or [None])[-1]
        source = "the last trace row before the note" if row else None
    item = next((entry.get("workitem") for entry in history if entry.get("action") == action), None) or next(
        (row.get("item") for row in rows if row.get("kind") == "packet" and row.get("action") == action), None)
    return {"moment": moment, "in_trace": instant(wrote["ts"]) if wrote and wrote.get("ts") else None,
            "last_accepted_before": None if last is None else {
                "stage": last.get("stage"), "workitem": last.get("workitem"), "outcome": last.get("outcome"),
                "action": last.get("action"), "accepted_at": instant(times[last["action"]])},
            "open_then": {"stage": stage, "workitem": item, "action": action, "from": source} if action else None}


def commits_after(repo: Path | None, moment: float, knowledge) -> dict:
    """The commits of the project's checkout made after ``moment`` (to the second), and those that touch its spec."""
    if repo is None:
        return {"not_recorded": "neither state.md's repo nor invocation.json's cwd is a git checkout"}
    spec = knowledge.HOME + "/spec.md"
    log = git(repo, "log", "--format=%H%x09%ct%x09%s")
    if log is None:
        return {"checkout": tilde(repo), "not_recorded": "git log failed in that checkout"}
    touched = set((git(repo, "log", "--format=%H", "--", spec) or "").split())
    rows = [line.split("\t", 2) for line in log.splitlines() if line.count("\t") >= 2]
    after = [(commit, subject) for commit, at, subject in rows if int(at) > moment]
    return {"checkout": tilde(repo), "spec": spec, "after": len(after),
            "same_second": sum(int(at) == int(moment) for _commit, at, _subject in rows),
            "touching_spec": [tilde(subject[:120]) for commit, subject in after if commit in touched]}


def failures_after(rows: list[dict], moment: float, ident: str, words: re.Pattern | None = ANSWER) -> dict:
    """The trace's commands after ``moment`` that ended non-zero, by stage, and those whose error names the note or
    (``words``) an answer."""
    naming = re.compile(r"\b" + re.escape(ident) + r"\b")
    by_stage, texts = {}, []
    for row in rows:
        if row.get("kind") != "command" or row.get("exit") in (0, None) or not row.get("ts") or row["ts"] <= moment:
            continue
        stage, text = stage_of(row), " ".join(str(row.get("error") or "").split())
        by_stage[stage] = by_stage.get(stage, 0) + 1
        if naming.search(text) or (words is not None and words.search(text)):
            texts.append({"stage": stage, "text": tilde(text[:200])})
    return {"by_stage": by_stage, "naming": texts}


def printed_packets(run: Path, rows: list[dict]) -> tuple[list[tuple[str, str, str]], int] | None:
    """(stage and work item, file, text) of every packet print the trace records, in order, and how many of those
    prints could not be read; None when the trace records none."""
    texts, found, unread = {}, [], 0
    packets = [row for row in rows if row.get("kind") == "packet"]
    if not packets:
        return None
    for row in packets:
        name = str(row.get("file") or "")
        if name not in texts:
            try:
                texts[name] = (run / name).read_text(encoding="utf-8", errors="replace") if name else None
            except OSError:
                texts[name] = None
        if texts[name] is None:
            unread += 1
        else:
            found.append((" ".join(str(part) for part in (row.get("stage"), row.get("item")) if part), name, texts[name]))
    return found, unread


def held_prints(run: Path, rows: list[dict], ident: str, prefix: str) -> dict:
    """The packets the trace says were printed whose held line (``prefix``) names ``ident``, in the order printed."""
    line = re.compile(re.escape(prefix) + r"[^\n]*\b" + re.escape(ident) + r"\b")
    printed = printed_packets(run, rows)
    if printed is None:
        return {"not_recorded": "the trace holds no packet prints"}
    prints = [(label, name) for label, name, text in printed[0] if line.search(text)]
    return {"prints": len(prints), "packets": len({name for _label, name in prints}),
            "stages": [label for label, _name in prints], "packet_prints_unreadable": printed[1]}


def accepted_times(run: Path, rows: list[dict]) -> dict:
    """When each action was accepted: the trace's command that accepted it, else timeline.json (to the second)."""
    times = {action: epoch(at) for action, at in (load(run / "timeline.json").get("accepted") or {}).items()}
    for traced in rows:
        for accepted in traced.get("accepted") or ():
            if isinstance(accepted, dict) and accepted.get("action") and traced.get("ts"):
                times[accepted["action"]] = traced["ts"]
    return times


def accepted_after(history: list[dict], times: dict, moment: float) -> list[dict]:
    """The history entries accepted after ``moment``."""
    return [entry for entry in history if times.get(entry.get("action")) is not None and times[entry["action"]] > moment]


def naming_results(later: list[dict], ident: str, words: re.Pattern) -> list[dict]:
    """The results of ``later`` whose summary names ``ident`` as a whole word or holds one of ``words``."""
    naming = re.compile(r"\b" + re.escape(ident) + r"\b")
    return [{"stage": entry.get("stage"), "workitem": entry.get("workitem"), "outcome": entry.get("outcome"),
             "summary": tilde(str(entry.get("summary") or "")[:400])} for entry in later
            if naming.search(str(entry.get("summary") or "")) or words.search(str(entry.get("summary") or ""))]


def ending(state: dict, later: list[dict], moment: float) -> dict:
    """How the run ended, its planning reconciliations (all, and after ``moment``), and the stages that returned
    blocked or reconcile in ``later``."""
    events = state.get("planning_reconciliations") or []
    return {"status": state.get("status"), "planning_reconciliations": len(events),
            "planning_reconciliations_after": sum((epoch(event.get("recorded_at")) or 0) > moment
                                                  for event in events if isinstance(event, dict)),
            "blocked_or_reconcile_after": [
                " ".join(str(part) for part in (entry.get("stage"), entry.get("workitem"), entry.get("outcome")) if part)
                for entry in later if entry.get("outcome") in ("blocked", "reconcile")]}


def held_answers(out: Path, run: Path, state: dict, row: dict, bound: list[dict], modules) -> list[dict]:
    """For each bound note no ``answers`` row applied (late, replaced or superseded): when it was written, its
    requirement's entry then and at the end, and what the run did after it."""
    answers, _defaults, knowledge, _owner_notes, _store = modules
    stands = {item["id"]: item["stands"] for item in row["notes"]}
    history = state.get("history") or []
    rows = trace_rows(run)
    times = accepted_times(run, rows)
    repo = checkout(state, out)
    found = []
    for note in bound:
        if stands.get(note["id"]) not in HELD_STANDS:
            continue
        ident, binding = note["id"], note["default"]
        requirement, stored = binding["requirement"], binding["entry_sha256"]
        # The row as the list the note was bound to holds it (a reconcile's later list may have no such row).
        rows_then = ((state.get("accepted") or {}).get(binding["spec_action"]) or {}).get("defaults") or []
        listed = rows_then[binding["row"] - 1] if 0 < binding["row"] <= len(rows_then) else {}
        item = {"id": ident, "stands": stands[ident], "row": binding["row"], "requirement": requirement,
                "selector": next(entry["selector"] for entry in row["notes"] if entry["id"] == ident),
                "words": note["text"], "written_at": note["written_at"],
                "listed_row": f"{binding['row']}. {requirement} {listed.get('question', binding['question'])} "
                              f"Decided: {listed.get('default', binding['recorded'])} Otherwise: "
                              f"{listed.get('alternative', 'not recorded (the bound list is not in state.md)')}"}
        when = written(note, rows, history, times)
        moment = when.pop("moment")
        item.update(when)
        found.append(item)
        if moment is None:
            continue
        # 2. The entry when the answer was written: the newest committed spec at or before it, when its digest is the
        # one the note stored (so it is the entry the answer was bound to, whitespace aside); and at the end.
        if repo is None:
            commit = then = now = None
            item["checkout"] = None
        else:
            commit, then = spec_then(repo, requirement, moment, knowledge)
            now = knowledge.entries(repo, "spec.md").get(requirement) if repo.is_dir() else None
            item["checkout"] = tilde(repo)
        confirmed = then is not None and answers.digest(then) == stored
        newest = f"commit {commit[:7]}, the newest of {knowledge.HOME}/spec.md at or before the answer" if commit else ""
        if confirmed:
            source = f"{newest}; its digest is the note's"
        elif repo is None:
            source = "not recorded: neither state.md's repo nor invocation.json's cwd is a git checkout"
        elif commit is None:
            source = f"not recorded: no commit of {knowledge.HOME}/spec.md at or before the answer"
        elif then is None:
            source = f"not recorded: {newest}, has no {requirement}"
        else:
            source = (f"not recorded: {newest}, holds {requirement} with another digest than the note stored, so the "
                      "entry the answer was bound to was not committed then")
        item["entry_when_written"], item["entry_when_written_from"] = (then if confirmed else None), source
        # The text export_held gives a blind reader as before.md, with a first line that says which text it is.
        closest = then
        if confirmed:
            first = f"{requirement} as it read when {ident} was written ({note['written_at']}):"
        elif then is not None:
            first = (f"{requirement} as commit {commit[:7]} holds it, the newest commit of the spec before {ident} was "
                     f"written ({note['written_at']}); it may not be the entry {ident} answered:")
        else:
            first = f"{requirement} at spec, the closest recovered; the entry when {ident} was written is not recorded:"
            closest = next((entry["at_spec"] for entry in row["entries"] if entry["requirement"] == requirement), None)
            if closest is None:
                first = f"{requirement} when {ident} was written: {source}; at spec: not recorded"
        item["before_md"] = [first, closest]
        item["entry_at_end"] = now.text if now else None
        item["entry_at_end_is"] = ("not recorded: no git checkout" if repo is None else "gone" if now is None
                                   else "retired" if now.retired else "current")
        item["unchanged_since_the_answer"] = None if now is None else answers.digest(now.text) == stored
        # 3. Accepted results after the note that name it, an owner note, the requester or an answer.
        later = accepted_after(history, times, moment)
        item["results_naming_it"] = naming_results(later, ident, MENTIONS)
        # 4-7. Commits after it, the trace's non-zero commands after it, how the run ended, the packets' held line.
        item["commits_after"] = commits_after(repo, moment, knowledge)
        item["failed_commands_after"] = failures_after(rows, moment, ident)
        item["end"] = ending(state, later, moment)
        item["held_line"] = held_prints(run, rows, ident, answers.HELD)
    return found


def commit_files(repo: Path) -> list[tuple[str, int, str, list[str]]] | None:
    """(commit, time, subject, the paths it touches) of every commit of the checkout's HEAD, newest first; None when
    git log fails."""
    log = git(repo, "log", "--no-renames", "--format=%x1e%H%x09%ct%x09%s", "--name-only")
    if log is None:
        return None
    found = []
    for chunk in log.split("\x1e")[1:]:
        head, _, rest = chunk.partition("\n")
        commit, at, subject = (head.split("\t", 2) + ["", ""])[:3]
        found.append((commit, int(at), subject, [path for path in rest.splitlines() if path.strip()]))
    return found


def commits_touching(repo: Path | None, moment: float, knowledge) -> dict:
    """The commits of the project's checkout made after ``moment`` (to the second): how many, those that touch its
    spec (by subject), and how many touch the code (``CODE``) and the tests (``TESTS``)."""
    if repo is None:
        return {"not_recorded": "neither state.md's repo nor invocation.json's cwd is a git checkout"}
    log = commit_files(repo)
    if log is None:
        return {"checkout": tilde(repo), "not_recorded": "git log failed in that checkout"}
    spec = knowledge.HOME + "/spec.md"
    later = [(subject, files) for _commit, at, subject, files in log if at > moment]
    return {"checkout": tilde(repo), "spec": spec, "after": len(later),
            "same_second": sum(at == int(moment) for _commit, at, _subject, _files in log),
            "touching_spec": [tilde(subject[:120]) for subject, files in later if spec in files],
            "touching_src_or_bin": sum(any(path.startswith(CODE) for path in files) for _subject, files in later),
            "touching_test": sum(any(path.startswith(TESTS) for path in files) for _subject, files in later)}


def note_record(run: Path, state: dict, rows: list[dict], note: dict, history: list[dict], times: dict,
                owner_notes) -> dict:
    """How the script recorded a plain note.  The owner-notes module offers the step whose acceptance delivered it
    (``delivered``) and the current action's shown record (``read_shown``: ``owner-notes/shown.json`` keeps only the
    current action's prints and held callbacks); every earlier held callback, and the ids each packet print quoted
    whole (``quoted_ids``), are in the trace, as ``shiploop_trace.notes_model`` reads them."""
    ident = note["id"]
    naming = re.compile(r"\b" + re.escape(ident) + r"\b")
    by = owner_notes.delivered(state).get(ident)
    step = next((entry for entry in history if entry.get("action") == by), {}) if by else {}
    holds = [f"{stage_of(row)} {row.get('verb')}" + (" (a check printed it in place of a hold)"
                                                     if ident in (row.get("shown") or []) else "")
             for row in rows if row.get("kind") == "command"
             and ident in [*(row.get("held") or []), *(row.get("shown") or [])]]
    shown = owner_notes.read_shown(run)
    now = [key for key in ("packet", "held") if ident in (shown.get(key) or [])]
    quoted = [" ".join(str(part) for part in (row.get("stage"), row.get("item")) if part)
              for row in rows if row.get("kind") == "packet" and ident in (row.get("notes") or [])]
    printed = printed_packets(run, rows)
    prints = None if printed is None else [
        (label, name, "quoted" if ident in owner_notes.quoted_ids(text) else "named")
        for label, name, text in printed[0] if ident in owner_notes.quoted_ids(text) or naming.search(text)]
    return {"stands": "delivered" if by else "shown" if quoted or holds or now else "waiting",
            "delivered_by": None if not by else {
                "action": by, "stage": step.get("stage"), "workitem": step.get("workitem"),
                "outcome": step.get("outcome"), "accepted_at": instant(times[by]) if times.get(by) else None,
                "cites_it": bool(naming.search(str(step.get("summary") or ""))) if step else None},
            "held_callbacks": holds,
            "shown_record": {"action": shown.get("action"), "in": now} if now else None,
            "quoted_in_trace": quoted,
            "packets": {"not_recorded": "the trace holds no packet prints"} if prints is None else {
                "prints": len(prints), "packets": len({name for _label, name, _how in prints}),
                "quoted": sum(how == "quoted" for _label, _name, how in prints),
                "named": sum(how == "named" for _label, _name, how in prints),
                "stages": [f"{label} ({how})" for label, _name, how in prints], "packet_prints_unreadable": printed[1]}}


def late_note(out: Path, run: Path, state: dict, row: dict, inbox: list[dict], modules) -> dict | None:
    """The plain owner note the stand-in sent during the build (its record's ``mode`` is "note-at"): when it was
    written, the entry of the requirement the chosen row names then and at the end, and what the run did after it;
    None for any other delivery."""
    answers, _defaults, knowledge, owner_notes, _store = modules
    requester = row.get("requester") or {}
    if requester.get("mode") != "note-at":
        return None
    sent = requester.get("note") or {}
    if not sent.get("id"):
        return {"not_recorded": "the stand-in sent no note: " + str(requester.get("ended") or "it recorded no reason")}
    note = next((note for note in inbox if note["id"] == sent["id"] and not note.get("default")), None)
    if note is None:
        return {"id": sent["id"], "not_recorded": f"the run's owner-notes/ holds no plain note {sent['id']}"}
    ident = note["id"]
    chosen = (requester.get("choice_at_send") or {}).get("chosen")
    printed = requester.get("rows_at_send") or []
    line = printed[chosen - 1] if isinstance(chosen, int) and 0 < chosen <= len(printed) else None
    named = re.match(r"\d+\. (R-\d+)\b", line or "")
    requirement = named.group(1) if named else None
    item = {"id": ident, "written_at": note["written_at"], "words": note["text"],
            "stage_waited_for": requester.get("stage_waited_for"), "stage_seen_at": requester.get("stage_seen_at"),
            "row_class": requester.get("row_class"), "note_sent": requester.get("note_sent"), "chosen": chosen,
            "row": line, "requirement": requirement}
    history = state.get("history") or []
    rows = trace_rows(run)
    times = accepted_times(run, rows)
    when = written(note, rows, history, times)
    moment = when.pop("moment")
    item.update(when)
    if moment is None:
        return item
    # 2. The chosen row's requirement: the newest committed entry at or before the note (a plain note stores no
    # digest, so nothing confirms it is the entry as it read then), and the entry at the end.
    repo = checkout(state, out)
    item["checkout"] = tilde(repo) if repo else None
    commit, then = spec_then(repo, requirement, moment, knowledge) if repo and requirement else (None, None)
    now = knowledge.entries(repo, "spec.md").get(requirement) if repo and requirement else None
    spec = knowledge.HOME + "/spec.md"
    if requirement is None:
        source = "not recorded: the chosen row of rows_at_send names no requirement"
    elif repo is None:
        source = "not recorded: neither state.md's repo nor invocation.json's cwd is a git checkout"
    elif commit is None:
        source = f"not recorded: no commit of {spec} at or before the note"
    elif then is None:
        source = f"not recorded: commit {commit[:7]}, the newest of {spec} at or before the note, has no {requirement}"
    else:
        source = f"commit {commit[:7]}, the newest of {spec} at or before the note, unverified (a plain note stores no digest)"
    item["entry_when_written"], item["entry_when_written_from"] = then, source
    item["entry_at_end"] = now.text if now else None
    item["entry_at_end_is"] = ("not recorded: no requirement or no git checkout" if repo is None or requirement is None
                               else "gone" if now is None else "retired" if now.retired else "current")
    item["differ"] = None if then is None or now is None else answers.digest(then) != answers.digest(now.text)
    item["before_md"] = [f"{requirement} as the newest commit of the spec at or before {ident} ({note['written_at']}) "
                         "holds it, unverified (a plain note stores no digest):" if then is not None else
                         f"{requirement} when {ident} was written: {source}", then]
    # 3-7. As for a held answer, with what the owner-notes module and the trace recorded of the note.
    later = accepted_after(history, times, moment)
    item["results_naming_it"] = naming_results(later, ident, NAMED_NOTE)
    item["commits_after"] = commits_touching(repo, moment, knowledge)
    item["failed_commands_after"] = failures_after(rows, moment, ident, None)
    item["end"] = ending(state, later, moment)
    item["recorded"] = note_record(run, state, rows, note, history, times, owner_notes)
    return item


def tally(numstat: list[list[str]], prefixes: tuple[str, ...] = ()) -> dict:
    """Files, insertions and deletions of the ``git diff --numstat`` rows under ``prefixes`` (all rows when empty); a
    binary file counts as a file with no lines."""
    picked = [(added, deleted) for added, deleted, path in numstat if not prefixes or path.startswith(prefixes)]
    return {"files": len(picked), "insertions": sum(int(added) for added, _ in picked if added.isdigit()),
            "deletions": sum(int(deleted) for _, deleted in picked if deleted.isdigit())}


def second_run(out: Path, row: dict, modules) -> dict | None:
    """A second run on the project an earlier delivery left (the harness's ``follow_on``, from ``run.py
    --continue-from``): the prior, the request, and what the run changed in ``work/`` since ``start_head``; None for
    any other delivery."""
    answers, _defaults, knowledge, _owner_notes, _store = modules
    follow = load(out / "result.json").get("follow_on") or load(out / "invocation.json").get("follow_on")
    if not isinstance(follow, dict):
        return None
    start, work = follow.get("start_head"), out / "work"
    try:
        prior = [tilde(line) for line in out.with_name(out.name + "-prior.txt").read_text(encoding="utf-8").splitlines()]
    except OSError:
        prior = None
    try:
        request = tilde((out / "prompt.txt").read_text(encoding="utf-8").strip())
    except OSError:
        request = None
    item = {"prior": tilde(follow.get("prior")), "start_head": start, "prior_case": follow.get("prior_case"),
            "prior_file": prior, "request": request, "work": tilde(work),
            "defaults": len(row["list"]) if "list" in row else None}
    if not start or git(work, "rev-parse", "--verify", "--quiet", start + "^{commit}") is None:
        item["not_recorded"] = ("the harness recorded no start_head" if not start
                                else f"{tilde(work)} is not a git checkout holding {start}")
        return item
    numstat = [line.split("\t", 2) for line in (git(work, "diff", "--no-renames", "--numstat", f"{start}..HEAD") or "")
               .splitlines() if line.count("\t") >= 2]
    item["diff"] = {"all": tally(numstat), "src_bin": tally(numstat, CODE), "test": tally(numstat, TESTS),
                    "knowledge_home": tally(numstat, (knowledge.HOME + "/",))}
    item["commits"] = [tilde(subject[:100]) for subject in
                       (git(work, "log", "--format=%s", f"{start}..HEAD") or "").splitlines()]
    spec = knowledge.HOME + "/spec.md"

    def entries_at(ref: str) -> dict:
        shown = git(work, "show", f"{ref}:{spec}") or ""
        return knowledge._entries(shown, "R") if shown.strip() else {}
    was, now = entries_at(start), entries_at("HEAD")
    item["changed_entries"] = []
    for ident in sorted(set(was) | set(now), key=lambda name: int(name.split("-")[1])):
        old, new = was.get(ident), now.get(ident)
        if old and new and answers.digest(old.text) == answers.digest(new.text) and old.retired == new.retired:
            continue
        how = ("new" if old is None else "gone" if new is None else "retired" if new.retired and not old.retired
               else "changed")
        item["changed_entries"].append({"id": ident, "how": how, "at_head": new.text[:600] if new else None})
    return item


def read(out: Path, modules) -> dict:
    answers, defaults, knowledge, owner_notes, store = modules
    row = {"name": out.name, **harness(out), "requester": load(out.with_name(out.name + "-requester.json")) or None,
           "last_message": last_message(out)}
    run, row["run_folders"] = run_folder(out, load(out / "result.json"), store)
    if run is None:
        row.update(run=None, late_note=None, second_run=second_run(out, row, modules))
        return row
    state = store.read_record(run / "state.md")
    inbox = owner_notes.notes(run)
    found = answers.standing(state, inbox)
    row.update(run=tilde(run), status=state.get("status"), stage=state.get("stage"), revision=state.get("revision"))
    entries = defaults.recorded(state) or []
    short = answers.selector_of(state)
    row["list"] = [{"row": number, "selector": f"{number}@{short}", "requirement": entry.get("requirement"),
                    "question": entry.get("question"), "default": entry.get("default"),
                    "alternative": entry.get("alternative")} for number, entry in enumerate(entries, 1)]
    where = {**{note["id"]: "in time" for note in found.in_time}, **{note["id"]: "late" for note in found.late},
             **{note["id"]: "replaced" for note in found.replaced},
             **{note["id"]: "superseded" for note in found.superseded},
             **{ident: "applied" if found.applied else "submitted" for ident in found.submitted}}
    bound = [note for note in inbox if note.get("default")]
    row["notes"] = [{"id": note["id"], "written_at": note["written_at"], "row": note["default"]["row"],
                     "selector": owner_notes.selector(note["default"]), "requirement": note["default"]["requirement"],
                     "words": note["text"], "stands": where.get(note["id"], "unknown")} for note in bound]
    strategy = [entry["action"] for entry in state.get("history") or []
                if entry.get("stage") == answers.STAGE and entry.get("outcome") == "done"]
    accepted = (state.get("accepted") or {}).get(strategy[-1]) if strategy else None
    row["answers_rows"] = (accepted or {}).get(answers.FIELD) if accepted else None
    row["strategy_accepted"] = bool(strategy)
    row["entries"] = []
    then, now = knowledge.entries_after(state, "spec", "spec.md"), knowledge.entries_after(state, answers.STAGE, "spec.md")
    for requirement in sorted({note["requirement"] for note in row["notes"]}):
        before = then.get(requirement).text if then and then.get(requirement) else None
        after = now.get(requirement).text if now and now.get(requirement) else None
        row["entries"].append({"requirement": requirement, "at_spec": before, "after_test_strategy": after,
                               "differ": None if before is None or after is None else before != after})
    row["trace"] = trace(run)
    row["displays"] = displays(run, [note["id"] for note in bound])
    row["applied"] = [ident for ident, stands in where.items() if stands == "applied"]
    row["held"] = held_answers(out, run, state, row, bound, modules)
    row["late_note"] = late_note(out, run, state, row, inbox, modules)
    row["second_run"] = second_run(out, row, modules)
    return row


def show(row: dict) -> None:
    print(f"== {row['name']}: {row.get('host')} {row.get('model')} {row.get('effort')}")
    if not row.get("ended"):
        print(f"   not ended (started {row.get('started')}); what the run folder shows so far:")
    else:
        print(f"   outcome {row['outcome']} ({row['basis']}) | verdicts {row['verdicts']}")
        print(f"   case checks {row['checks_passed']} of {row['checks']}")
        for failed in row["failed"]:
            print(f"      FAILED {failed['check']} | ...{failed['output_end']}")
        print("   start-up checks: " + ", ".join(f"{probe} {'pass' if ok else 'FAIL' if ok is False else 'absent'}"
                                               for probe, ok in row["startup"].items()))
        print(f"   {row['started']} to {row['ended_at']}, {row['minutes']} minutes | turns {row['turns']}, model calls "
              f"{row['model_calls']}, output tokens {row['output_tokens']}, cost {row['cost_usd']} | spec "
              f"{row['spec_seconds']} s, test-strategy {row['strategy_seconds']} s")
    print(f"   run folders {row['run_folders']}; read {row.get('run')}")
    if row.get("run") is None:
        if row.get("second_run"):
            show_second(row["second_run"])
        return
    print(f"   engine {row['status']} at {row['stage']}, revision {row['revision']}")
    requester = row.get("requester") or {}
    choice = requester.get("choice") or {}
    chosen = choice.get("chosen")
    print(f"   the list: {len(row['list'])} rows")
    for entry in row["list"]:
        print(f"      {entry['row']}. {entry['selector']} {entry['requirement']} {entry['question']}"
              + ("   <- chosen" if entry["row"] == chosen else ""))
        if entry["row"] == chosen:
            print(f"         default: {entry['default']}")
            print(f"         alternative: {entry['alternative']}")
    note = requester.get("note") or {}
    sent = next((item["written_at"] for item in row["notes"] if item["id"] == note.get("id")), None) or (
        row.get("late_note") or {}).get("written_at")
    if not requester:
        print("   stand-in: no stand-in (a second run)" if row.get("second_run") else
              "   stand-in: no record yet (it writes its record when it ends)")
    else:
        print(f"   stand-in: mode {requester.get('mode')}, row {chosen}, selector {choice.get('selector')}, tie "
              f"{bool(choice.get('tied') or choice.get('ambiguous'))} {choice.get('tied') or ''}; scores "
              + ", ".join(f"{c['row']}={c['score']}" for c in choice.get("candidates") or [])
              + f"; sent {note.get('id')} at {sent} (packet seen {requester.get('seen_at')}); ended "
              f"{requester.get('ended')}")
    for item in row["notes"]:
        print(f"   note {item['id']} {item['written_at']} row {item['row']} ({item['selector']}, {item['requirement']}): "
              f"{item['stands']} | \"{item['words']}\"")
    print(f"   accepted test-strategy result: {'yes' if row['strategy_accepted'] else 'not yet'}; its answers rows: "
          f"{json.dumps(row['answers_rows'], ensure_ascii=False)}")
    for entry in row["entries"]:
        print(f"   {entry['requirement']} at spec / after test-strategy, differ: {entry['differ']}")
        for label in ("at_spec", "after_test_strategy"):
            print(f"      -- {label}:")
            for line in str(entry[label]).splitlines():
                print("      | " + line)
    found = row["trace"]
    print(f"   held callbacks {len(found['held'])}: {[item['stage'] for item in found['held']]} | refusals naming answers "
          f"{len(found['naming_answers'])} | other refusals by stage {found['other_refusals_by_stage']} | failed "
          f"checks by stage {found['failed_checks_by_stage']}")
    for item in found["naming_answers"]:
        print(f"      [{item['stage']}] {item['text']}")
    shown = row["displays"]
    print(f"   packets {shown['packets']}: with the answers block {shown['packets_with_the_block']}, with the held line "
          f"{shown['packets_with_the_held_line']}")
    print(f"   done packet lines: {shown['done_packet_lines'] if shown['done_packet_lines'] is not None else 'no done packet'}")
    print(f"   report lines: {shown['report_lines'] if shown['report_lines'] is not None else 'no report.html'}")
    print("   the host's last message to the user:")
    for line in (row.get("last_message") or "(none found)").splitlines():
        print("      | " + line)
    for item in row.get("held") or []:
        show_held(item)
    if row.get("late_note"):
        show_late(row["late_note"])
    if row.get("second_run"):
        show_second(row["second_run"])


def label(part: dict | None) -> str:
    """A stage as the held block names it: stage, work item, outcome, and the action's first hex digits."""
    if not part:
        return "not recorded"
    return " ".join(str(value) for value in (part.get("stage"), part.get("workitem"), part.get("outcome")) if value) + (
        f" ({str(part['action'])[:12]})" if part.get("action") else "")


def when_text(item: dict) -> str:
    """Item 1 of the held and late-note blocks: when the note was written and what was open then."""
    last = item["last_accepted_before"]
    opened = item["open_then"]
    return (f"written {item['written_at']} (in the trace: {item['in_trace'] or 'no note command'}) | last accepted "
            f"before: {label(last)}{', accepted ' + last['accepted_at'] if last else ''} | open then: "
            + (f"{label(opened)}, from {opened['from']}" if opened else "not recorded in the trace"))


def ending_text(end: dict) -> str:
    """Item 6 of the held and late-note blocks."""
    return (f"run {end['status']}; planning reconciliations {end['planning_reconciliations']} "
            f"({end['planning_reconciliations_after']} after it); blocked or reconcile after it: "
            f"{', '.join(end['blocked_or_reconcile_after']) or 'none'}")


def show_held(item: dict) -> None:
    print(f"   the held answer {item['id']} ({item['stands']}), row {item['row']} ({item['selector']}, "
          f"{item['requirement']}):")
    if "not_recorded" in item:
        print(f"      not recorded: {item['not_recorded']}")
        return
    print("      1. " + when_text(item))
    print(f"      2. {item['requirement']} in {item['checkout'] or 'no git checkout'}: when the answer was written, "
          f"{item['entry_when_written_from']}")
    for line in str(item["entry_when_written"]).splitlines() if item["entry_when_written"] is not None else ():
        print("         | " + tilde(line))
    print(f"         at the end: {item['entry_at_end_is']}; unchanged since the answer: "
          f"{item['unchanged_since_the_answer']}")
    for line in str(item["entry_at_end"]).splitlines() if item["entry_at_end"] is not None else ():
        print("         | " + tilde(line))
    if item["entry_when_written"] is None:
        print("         (not recovered: the closest texts are the entry at spec and after test-strategy printed above, "
              "each from the newest such commit, which after a reconcile is the later specification's)")
    print(f"      3. accepted results after it naming {item['id']}, an owner note, the requester or an answer: "
          f"{len(item['results_naming_it'])}")
    for result in item["results_naming_it"]:
        print(f"         {label(result)}: \"{result['summary']}\"")
    commits = item["commits_after"]
    if "not_recorded" in commits:
        print(f"      4. commits after it: not recorded ({commits.get('checkout', 'no checkout')}: "
              f"{commits['not_recorded']})")
    else:
        print(f"      4. commits of {commits['checkout']} after it: {commits['after']}"
              + (f" (and {commits['same_second']} in its second, order unknown)" if commits["same_second"] else "")
              + f"; touching {commits['spec']}: {len(commits['touching_spec'])}")
        for subject in commits["touching_spec"]:
            print(f"         {subject}")
    failed = item["failed_commands_after"]
    print(f"      5. non-zero commands after it by stage {failed['by_stage']}; naming {item['id']} or an answer: "
          f"{len(failed['naming'])}")
    for named in failed["naming"]:
        print(f"         [{named['stage']}] {named['text']}")
    print("      6. " + ending_text(item["end"]))
    shown = item["held_line"]
    print("      7. packets that printed the held line for " + item["id"] + ": " + prints_text(shown))


def prints_text(shown: dict) -> str:
    """Packet prints as items 7 of the held and late-note blocks count them."""
    if "not_recorded" in shown:
        return f"not recorded ({shown['not_recorded']})"
    return (f"{shown['prints']} prints of {shown['packets']} packets, in order {shown['stages']}"
            + (f"; {shown['packet_prints_unreadable']} printed packets unreadable" if shown["packet_prints_unreadable"]
               else ""))


def show_late(item: dict) -> None:
    print(f"   the late note {item.get('id', '(none sent)')} (a plain note, bound to no row):")
    if "words" in item:
        print(f"      sent when the {item['stage_waited_for']} packet printed ({item['stage_seen_at']}); the chosen row "
              f"{item['chosen']} decided {item['row_class']}, so the note sent is \"{item['note_sent']}\": "
              f"\"{item['words']}\"")
        print(f"      the chosen row as printed: {item['row']}")
    if "not_recorded" in item:
        print(f"      not recorded: {item['not_recorded']}")
        return
    print("      1. " + when_text(item))
    print(f"      2. {item['requirement']} in {item['checkout'] or 'no git checkout'}: when the note was written, "
          f"{item['entry_when_written_from']}")
    for line in str(item["entry_when_written"]).splitlines() if item["entry_when_written"] is not None else ():
        print("         | " + tilde(line))
    print(f"         at the end: {item['entry_at_end_is']}; differs from the entry when the note was written: "
          f"{item['differ']}")
    for line in str(item["entry_at_end"]).splitlines() if item["entry_at_end"] is not None else ():
        print("         | " + tilde(line))
    print(f"      3. accepted results after it naming {item['id']} or an owner note: {len(item['results_naming_it'])}")
    for result in item["results_naming_it"]:
        print(f"         {label(result)}: \"{result['summary']}\"")
    commits = item["commits_after"]
    if "not_recorded" in commits:
        print(f"      4. commits after it: not recorded ({commits.get('checkout', 'no checkout')}: "
              f"{commits['not_recorded']})")
    else:
        print(f"      4. commits of {commits['checkout']} after it: {commits['after']}"
              + (f" (and {commits['same_second']} in its second, order unknown)" if commits["same_second"] else "")
              + f"; touching {commits['spec']}: {len(commits['touching_spec'])}; touching src/ or bin/: "
              f"{commits['touching_src_or_bin']}; touching test/: {commits['touching_test']}")
        for subject in commits["touching_spec"]:
            print(f"         {subject}")
    failed = item["failed_commands_after"]
    print(f"      5. non-zero commands after it by stage {failed['by_stage']}; naming {item['id']}: {len(failed['naming'])}")
    for named in failed["naming"]:
        print(f"         [{named['stage']}] {named['text']}")
    print("      6. " + ending_text(item["end"]))
    recorded = item["recorded"]
    by = recorded["delivered_by"]
    print(f"      7. the owner-notes record: {recorded['stands']}"
          + (f", delivered by {label(by)}, accepted {by['accepted_at']}; its summary names {item['id']}: {by['cites_it']}"
             if by else ", delivered by no accepted step (owner_notes.delivered)"))
    print(f"         held callbacks or checks that printed it (the trace): {len(recorded['held_callbacks'])} "
          f"{recorded['held_callbacks']}; the current action's shown record: "
          + (f"{recorded['shown_record']['in']} of {str(recorded['shown_record']['action'])[:12]}"
             if recorded["shown_record"] else "does not name it"))
    print(f"         packet prints that quoted it whole (the trace's record): {len(recorded['quoted_in_trace'])} "
          f"{recorded['quoted_in_trace']}")
    packets = recorded["packets"]
    print(f"         packet prints that quote it or name {item['id']}: "
          + ("" if "not_recorded" in packets else f"quoted whole in {packets['quoted']}, named only in "
                                                   f"{packets['named']}: ") + prints_text(packets))


def show_second(item: dict) -> None:
    print(f"   second run: on the project {item['prior']} left ({item['prior_case']}); its HEAD at the start "
          f"{item['start_head']}")
    print("      prior file: " + (" | ".join(item["prior_file"]) if item["prior_file"] is not None
                                  else "not recorded (no <NAME>-prior.txt beside the delivery)"))
    print("      request:" + ("" if item["request"] is not None else " not recorded (no prompt.txt)"))
    for line in (item["request"] or "").splitlines():
        print("      | " + line)
    if "not_recorded" in item:
        print(f"      not recorded: {item['not_recorded']}")
        return

    def numbers(part: dict) -> str:
        return f"{part['files']} files, +{part['insertions']} -{part['deletions']}"
    diff = item["diff"]
    print(f"      diff {str(item['start_head'])[:7]}..HEAD in {item['work']}: {numbers(diff['all'])} | src/ + bin/: "
          f"{numbers(diff['src_bin'])} | test/: {numbers(diff['test'])} | docs/shiploop/: "
          f"{numbers(diff['knowledge_home'])}")
    print(f"      commits after start_head: {len(item['commits'])}")
    for subject in item["commits"]:
        print(f"         {subject}")
    print("      requirement entries that differ between start_head and HEAD: "
          + (", ".join(f"{entry['id']} ({entry['how']})" for entry in item["changed_entries"]) or "none"))
    for entry in item["changed_entries"]:
        print(f"         {entry['id']} at HEAD" + (":" if entry["at_head"] is not None else ": gone"))
        for line in (entry["at_head"] or "").splitlines():
            print("         | " + tilde(line))
    print(f"      the second run's list of defaults: {item['defaults']} rows (the list printed above)")


def export(row: dict, folder: Path) -> None:
    """The four files a reader blind to the checks is given, for the first applied answer of a delivery, else for its
    first held answer (``before.md`` then opens with a line that says which text it holds), else for its late plain
    note; nothing for a second run."""
    applied = [note for note in row.get("notes") or [] if note["stands"] == "applied"]
    held = [item for item in row.get("held") or [] if "before_md" in item]
    if row.get("second_run"):
        return
    if not applied:
        if held:
            export_held(row, held[0], folder)
        elif "before_md" in (row.get("late_note") or {}):
            export_late(row["late_note"], folder)
        return
    note = applied[0]
    entry = next(item for item in row["entries"] if item["requirement"] == note["requirement"])
    printed = (row.get("requester") or {}).get("rows") or []
    listed = next((item for item in row["list"] if item["row"] == note["row"]), {})
    text = next((line for line in printed if line.startswith(f"{note['row']}. ")), None) or (
        f"{note['row']}. {listed.get('requirement')} {listed.get('question')} Decided: {listed.get('default')} "
        f"Otherwise: {listed.get('alternative')}")
    folder.mkdir(parents=True, exist_ok=True)
    for name, body in (("row.txt", text), ("answer.txt", note["words"]), ("before.md", entry["at_spec"]),
                       ("after.md", entry["after_test_strategy"])):
        (folder / name).write_text(str(body) + "\n", encoding="utf-8")


def export_held(row: dict, item: dict, folder: Path) -> None:
    """The same four files for a held answer: the row as the requester saw it (else as the bound list holds it), its
    words, the entry when it was written (or the closest recovered) and the entry at the end."""
    printed = (row.get("requester") or {}).get("rows") or []
    text = next((line for line in printed if line.startswith(f"{item['row']}. ") and item["selector"] in line),
                None) or item["listed_row"]
    first, before = item["before_md"]
    folder.mkdir(parents=True, exist_ok=True)
    for name, body in (("row.txt", text), ("answer.txt", item["words"]), ("before.md", f"{first}\n\n{before}"),
                       ("after.md", item["entry_at_end"] if item["entry_at_end"] is not None
                        else item["entry_at_end_is"])):
        (folder / name).write_text(str(body) + "\n", encoding="utf-8")


def export_late(item: dict, folder: Path) -> None:
    """The same four files for a late plain note: the chosen row as the stand-in printed it, the note's words, the
    newest committed entry at or before the note (its first line says so) and the entry at the end."""
    first, before = item["before_md"]
    folder.mkdir(parents=True, exist_ok=True)
    for name, body in (("row.txt", item["row"]), ("answer.txt", item["words"]),
                       ("before.md", f"{first}\n\n{before}" if before is not None else first),
                       ("after.md", item["entry_at_end"] if item["entry_at_end"] is not None
                        else item["entry_at_end_is"])):
        (folder / name).write_text(str(body) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("root", type=Path)
    parser.add_argument("names", nargs="*")
    parser.add_argument("--json", type=Path)
    parser.add_argument("--export", type=Path)
    args = parser.parse_args()
    modules = engine(args.root)
    folders = ([args.root / name for name in args.names] if args.names else
               sorted(path for path in args.root.iterdir() if path.is_dir() and (path / "invocation.json").is_file()))
    rows = []
    for folder in folders:
        if not folder.is_dir():
            print(f"== {folder.name}: no folder yet")
            continue
        rows.append(read(folder, modules))
        show(rows[-1])
        if args.export:
            export(rows[-1], args.export / folder.name)
    if args.json:
        args.json.write_text(json.dumps(rows, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


main()
