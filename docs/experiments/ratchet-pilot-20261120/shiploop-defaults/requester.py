#!/usr/bin/env python3
"""A stand-in requester for one E2E delivery: it reads the defaults the run printed for the requester and may reply.

DESIGN.md section 3 registers the rule.  The stand-in watches the output folder of one ``test/shiploop_e2e/run.py``
invocation.  It waits for the packet of the stage after the spec (``shiploop_defaults.SHOWN_AT``) to be printed, and
reads from that packet's own text what a requester is shown there: the block "Defaults the spec recorded" and its rows
(the rows a long list spills to its run file are read from that file, which the block names).  It does not read the
run's state for the list: the surface under test is the printed one.

The mode the stand-in was started with decides what it sends, with the CLI the run itself uses, as one owner note
holding the requester's reply (``program/replies.json``):

- ``--reply``: a plain note, the existing owner-note route, which binds no row, when any row is about the case's
  point (``about_the_point``, the rule the earlier waves used, kept as it was so they stay comparable);
- ``--answer``: an answer to the one row about how the tickets already on file get their due times (``choose_row``:
  every printed row scored on that decision, the best one taken, each candidate recorded with its score), bound by
  the selector printed at the end of that row and sent at once, so it is in time for the stage after the spec
  (shiploop-answers DESIGN.md); no qualifying row, a tie between the best rows, or no selector on the row sends
  nothing, and the record says which;
- ``--answer-at STAGE``: the same answer, sent when ``STAGE``'s packet first prints, so a delivery can get it during
  the build; at that moment the list of the current accepted spec result is read again and the row chosen from it by
  the same scoring (a tie, or no start-up row, sends nothing and says why); a stage that never prints before the
  deadline or the delivery's end sends nothing and says so;
- ``--answer-late``: ``--answer-at plan``, so the run holds the answer for a new run;
- ``--note-at STAGE``: when ``STAGE``'s packet first prints, the start-up row of the current list is chosen the same
  way, its "Decided:" part is classified (``classify_decided``: ``command`` when an operator must run something first
  or the service refuses to start while due times are missing, ``start`` when a start fills them in), and the note of
  ``../shiploop-answers/late-notes.json`` that contradicts that decision is sent as a PLAIN note (no ``--default``), so
  every delivery shows whether a late plain note is taken in; a row it cannot classify gets nothing;
- none of these: nothing is sent.

``--self-test`` checks the argument parsing of the modes, classifies every row ``late-notes.json`` labels and fails if
one differs from its label or cannot be classified, then runs the row choice and the classification over the printed
rows saved under ``evidence/``; no run is read and nothing is sent.

Either way it writes what it saw and did beside the output folder, in ``<out>-requester.json``, and ends.

It reads the run's files and writes at most one note.  It never reads or writes the session's work folder, and nothing
it holds (the reply, the rule) is in a folder a session can see.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / "skills/shiploop/scripts"))
sys.path.insert(0, str(ROOT / "test/shiploop_e2e"))

import run_choice
import shiploop_answers as answers
import shiploop_defaults as defaults
import shiploop_navigator as navigator
import shiploop_stage_spec as stage_spec
import shiploop_trace

SUFFIX = "-requester.json"
POLL_SECONDS = 2.0
WRITTEN = re.compile(r"^Owner note (N\d+) written", re.MULTILINE)
HEAD = "Defaults the spec recorded:"
ROW = re.compile(r"^\d+\. R-\d+ .+$")
# The selector the packet prints at the end of each row (shiploop_defaults.row_lines): <row>@<eight hex digits>.
SELECTOR = re.compile(r" Selector: (\d+@[0-9a-f]{8})\.$")
LATE_STAGE = "plan"
# The stages ``--answer-at`` and ``--note-at`` may wait for: the stage that shows the list and every one after it.
LATER = tuple(stage_spec.STAGES)[tuple(stage_spec.STAGES).index(defaults.SHOWN_AT):]
# What ``--note-at`` sends, and the rows a reader labelled (written before any such delivery; never in a delivery).
LATE_NOTES = HERE.parent / "shiploop-answers" / "late-notes.json"
DECIDED = re.compile(r"Decided:(.*?) Otherwise:", re.DOTALL)
# What a start-up row's "Decided:" part decided, read from what it says.  ``command``: an operator runs something of
# its own first (offline, a run of a backfill, migration, command or script, npm run, the writer or service stopped
# for it), or the service refuses or fails to start while due times are missing.  ``start``: a start of the service
# fills them in: a start named together with filling them (writes, persists, backfills, fills, prepares, populates,
# migrates, rewrites, saves), with the file that start produced, or with the inputs a due time is computed from.  A
# command signal decides the class whatever else the row says: then the operator still runs something, or the start
# is refused.  "Before enabling it" or "then enable and restart" is the flag being switched, not a command.
COMMAND_SIGNALS = {
    "offline": re.compile(r"\boffline\b", re.IGNORECASE),
    "refuses to start": re.compile(r"\brefus\w*|\bfails? to start\b|\b(?:will|does) not start\b|\bblocks? (?:enabled )?"
                                   r"start\w*", re.IGNORECASE),
    "runs a command": re.compile(r"\bnpm run\b|\brun (?:the |an |one |a )?(?:[\w-]+ )?(?:backfill|migration|command|"
                                 r"script)\w*\b", re.IGNORECASE),
    "the writer stopped": re.compile(r"\bstop(?:s|ped)? the (?:sole )?(?:writer|service)\b|\b(?:writer|service) is "
                                     r"stopped\b|\bwith the service stopped\b", re.IGNORECASE),
}
START_WORD = re.compile(r"\b(?:re)?start\w*|\bboot\w*", re.IGNORECASE)
START_SIGNALS = {
    "fills": re.compile(r"\b(?:writ\w*|persist\w*|back-?fill\w*|fill\w*|prepar\w*|populat\w*|migrat\w*|rewrit\w*|"
                        r"sav(?:e|es|ed|ing))\b", re.IGNORECASE),
    "the file it produced": re.compile(r"\b(?:resulting|populated|rewritten|updated|prepared) file\b", re.IGNORECASE),
    "the due-time inputs": re.compile(r"\bcreation time\b|\bcreated (?:time|timestamp)\b", re.IGNORECASE),
}
SPILL = re.compile(r"\(\d+ more lines? not printed here: RUN/(\S+) holds all \d+ whole\)")
# The rule of DESIGN.md section 3: a row is about the point when it names the tickets that are already there (TICKETS),
# or names starting the service together with a due time that is absent (START and ABSENT).  A reader scores the same
# rows afterwards against the rubric of that section; this rule only decides, during the run, whether to reply.
TICKETS = re.compile(r"\b(backfill\w*|back-fill\w*|migrat\w*|existing|already|older)\b", re.IGNORECASE)
START = re.compile(r"\b(start\w*|start-up|boot\w*|launch\w*|restart\w*)\b", re.IGNORECASE)
ABSENT = re.compile(r"\b(missing|without|lack\w*|no due|has none|have none|has no|have no)\b", re.IGNORECASE)
CASES = ("ticket-due-times",)


def about_the_point(case: str, row: str) -> bool:
    assert case in CASES, case
    return bool(TICKETS.search(row) or (START.search(row) and ABSENT.search(row)))


# The row an answer is bound to (``choose_row``): the due-time start-up decision, how the tickets already on file get
# their due times.  The subject is the tickets or data already there, or the data file; the act is filling them in
# (backfill, migration, preparing, populating) or switching the feature on or starting the service.  A word such as
# "existing" alone is no subject: "the existing filters" or "the existing listing" is another row's decision.
SUBJECT = re.compile(r"\b(?:existing|legacy|older|old|already[- ]stored|stored)\s+(?:tickets?|data|files?|records?)\b"
                     r"|\btickets? (?:already|on file)\b", re.IGNORECASE)
DATA_FILE = re.compile(r"\b(?:data[ _]?file|persisted file|legacy file|the file|the data)\b", re.IGNORECASE)
FILLING = {
    "backfill": re.compile(r"\bback-?fill\w*", re.IGNORECASE),
    "migration": re.compile(r"\bmigrat\w*", re.IGNORECASE),
    "preparing": re.compile(r"\b(?:prepar\w*|populat\w*|fill(?:s|ed|ing)?)\b", re.IGNORECASE),
}
STARTING = {
    "enabling": re.compile(r"\b(?:enabl\w*|activat\w*|switch(?:es|ed)? on)\b", re.IGNORECASE),
    "starting": re.compile(r"\b(?:start\w*|boot\w*|before (?:listening|serving|opening the port))\b", re.IGNORECASE),
}
DUE = re.compile(r"\b(?:due|dues|deadlines?)\b", re.IGNORECASE)


def score_row(row: str) -> dict:
    """How strongly a printed row is about the due-time start-up decision: its signals, its score, and whether it
    qualifies (a subject with an act, or a filling act with a starting one)."""
    subject = bool(SUBJECT.search(row))
    data_file = bool(DATA_FILE.search(row))
    filling = sorted(name for name, pattern in FILLING.items() if pattern.search(row))
    starting = sorted(name for name, pattern in STARTING.items() if pattern.search(row))
    acts = filling + starting
    qualifies = bool(((subject or data_file) and acts) or (filling and starting and set(filling) - {"preparing"}))
    score = 2 * subject + data_file + len(acts) + bool(DUE.search(row)) if qualifies else 0
    return {"score": score, "qualifies": qualifies, "subject": subject, "data_file": data_file, "acts": acts}


def choose_row(rows: list[str]) -> dict:
    """The printed row an answer is bound to: the best-scoring row that qualifies, with every candidate and its score.
    None when no row qualifies, or when the best score is a tie: then ``tied`` lists the tied rows and nothing is
    bound, since either could be the wrong decision.  The selector is read from the end of the chosen row; a row
    printed before rows carried one has none."""
    candidates = [{"row": index + 1, "text": row, **score_row(row)} for index, row in enumerate(rows)]
    qualified = [candidate for candidate in candidates if candidate["qualifies"]]
    best = max((candidate["score"] for candidate in qualified), default=None)
    top = [candidate for candidate in qualified if candidate["score"] == best]
    chosen = top[0] if len(top) == 1 else None
    selector = SELECTOR.search(chosen["text"]) if chosen else None
    return {"candidates": [{key: value for key, value in candidate.items() if key != "text"} for candidate in candidates],
            "chosen": chosen["row"] if chosen else None, "ambiguous": len(top) > 1,
            "tied": [candidate["row"] for candidate in top] if len(top) > 1 else [],
            "selector": selector.group(1) if selector else None}


def decided_part(row: str) -> str:
    """The text between "Decided:" and " Otherwise:" of a printed row; the whole row when it has no such part."""
    found = DECIDED.search(row)
    return found.group(1).strip() if found else row


def classify_decided(text: str) -> dict:
    """{"class": "command" | "start" | None, "signals": [...]} for a start-up row's Decided part (``COMMAND_SIGNALS``,
    ``START_SIGNALS``)."""
    command = [name for name, pattern in COMMAND_SIGNALS.items() if pattern.search(text)]
    if command:
        return {"class": "command", "signals": command}
    start = [name for name, pattern in START_SIGNALS.items() if pattern.search(text)]
    if START_WORD.search(text) and start:
        return {"class": "start", "signals": ["a start", *start]}
    return {"class": None, "signals": start + (["a start"] if START_WORD.search(text) else [])}


def note_for(rows: list[str]) -> dict:
    """What ``--note-at`` sends for this list, decided without sending: the row choice, the chosen row's class, and
    the note that contradicts it, or why nothing is sent."""
    plan: dict = {"choice_at_send": choose_row(rows)}
    choice = plan["choice_at_send"]
    if choice["tied"]:
        plan["ended"] = ("a tie between rows " + ", ".join(map(str, choice["tied"]))
                         + " on the due-time start-up decision; nothing was sent")
        return plan
    if choice["chosen"] is None:
        plan["ended"] = "no printed row is about the due-time start-up decision; nothing was sent"
        return plan
    found = classify_decided(decided_part(rows[choice["chosen"] - 1]))
    plan.update(row_class=found["class"], row_class_signals=found["signals"])
    if found["class"] is None:
        plan["ended"] = "could not tell what the row decided; nothing was sent"
        return plan
    notes = json.loads(LATE_NOTES.read_text(encoding="utf-8"))
    plan["note_sent"] = notes["sent_when_the_row_decided"][found["class"]]
    plan["text"] = notes["notes"][plan["note_sent"]]
    return plan


def labelled_test() -> int:
    """Every row ``late-notes.json`` labels, classified and compared with its label; 1 when one differs or is None."""
    labelled = json.loads(LATE_NOTES.read_text(encoding="utf-8"))["labelled_rows"]
    wrong = 0
    for relative, label in labelled.items():
        if relative == "_about":
            continue
        row = (LATE_NOTES.parent / relative).read_text(encoding="utf-8").strip()
        found = classify_decided(decided_part(row))
        ok = found["class"] == label
        wrong += not ok
        print(f"{'ok  ' if ok else 'DIFF'} {relative}: {found['class']} (label {label}; {', '.join(found['signals'])})")
    return 1 if wrong else 0


def self_test() -> int:
    """The row choice over every printed-rows file saved under ``evidence/``, one line each; no model, nothing sent."""
    for path in sorted((HERE / "evidence").glob("**/rows.txt")):
        rows = [line for line in path.read_text(encoding="utf-8").splitlines() if ROW.match(line)]
        choice = choose_row(rows)
        tied = choice["tied"]
        picked = (rows[choice["chosen"] - 1][:110] if choice["chosen"] else
                  "nothing (tie between rows " + ", ".join(map(str, tied[:-1])) + " and " + str(tied[-1]) + ")" if tied
                  else "nothing: no row qualifies")
        if choice["chosen"]:
            found = classify_decided(decided_part(rows[choice["chosen"] - 1]))
            picked = f"class {found['class']} ({', '.join(found['signals'])}): " + picked
        scores = ", ".join(f"{candidate['row']}={candidate['score']}" for candidate in choice["candidates"])
        print(f"{path.relative_to(HERE)}: row {choice['chosen'] or '-'} of {len(rows)} (scores {scores}; selector "
              f"{choice['selector'] or 'none printed'}): {picked}")
    return 0


def reply_for(case: str) -> str:
    return json.loads((HERE.parent / "program" / "replies.json").read_text(encoding="utf-8"))[case]["reply"]


def run_cli(out: Path) -> Path | None:
    found = sorted(out.glob("build/**/skills/shiploop/scripts/shiploop"))
    return found[0] if found else None


def shown_rows(run_dir: Path, packet: str) -> tuple[bool, list[str]]:
    """(the block is in the packet, its rows): the rows printed, or every row from the file a cut block names."""
    lines = packet.splitlines()
    start = next((index for index, line in enumerate(lines) if line.startswith(HEAD)), None)
    if start is None:
        return False, []
    rows = []
    for line in lines[start + 1:]:
        spilled = SPILL.search(line)
        if spilled:
            whole = run_dir / spilled.group(1)
            return True, [row for row in whole.read_text(encoding="utf-8").splitlines() if ROW.match(row)]
        if not ROW.match(line):
            break
        rows.append(line)
    return True, rows


def printed_packet(run_dir: Path, wanted: str = defaults.SHOWN_AT) -> tuple[dict, str] | None:
    """(state, packet text) once ``wanted`` (the stage after the spec) is current and its packet has been printed;
    else None."""
    state = shiploop_trace.current_state(run_dir)
    if not state or state.get("status") != "active" or state.get("active_improve"):
        return None
    stage, action, _item = shiploop_trace._cursor(state)
    action_id = (action or {}).get("id")
    if stage != wanted or not action_id:
        return None
    path = run_dir / navigator.PACKET_DIR / (action_id + ".md")
    return (state, path.read_text(encoding="utf-8")) if path.is_file() else None


def past_the_stage(run_dir: Path) -> bool:
    """Whether the run has an accepted result of the stage after the spec: the packet can no longer be awaited."""
    state = shiploop_trace.current_state(run_dir)
    return bool(state) and any(row.get("stage") == defaults.SHOWN_AT and row.get("outcome") == "done"
                               for row in state.get("history") or ())


def send(out: Path, run_dir: Path, text: str, selector: str | None) -> dict:
    """Run the run's own `note` once: a plain note, or with ``selector`` an answer to that row."""
    argv = [sys.executable, str(run_cli(out)), "note", "--run-dir", str(run_dir), "--text", text]
    done = subprocess.run(argv + (["--default", selector] if selector else []), capture_output=True, text=True,
                          timeout=120, check=False)
    hit = WRITTEN.search(done.stdout)
    return {"exit": done.returncode, "id": hit.group(1) if hit else None, "text": text, "default": selector,
            "output": (done.stdout + done.stderr).strip()[:1500]}


def wait_for_stage(out: Path, run_dir: Path, stage: str, deadline: float) -> tuple[str | None, str]:
    """(when ``stage``'s packet was first seen printed, or None; why not) before the deadline or the delivery's end."""
    while time.time() < deadline and not (out / "result.json").exists():
        try:
            if printed_packet(run_dir, stage):
                return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), ""
        except Exception:  # noqa: BLE001 - a state file read mid-write
            pass
        time.sleep(POLL_SECONDS)
    return None, (f"the delivery ended before the {stage} packet printed" if (out / "result.json").exists()
                  else f"the deadline passed before the {stage} packet printed")


def current_rows(run_dir: Path) -> list[str]:
    """The list of the current accepted spec result, as the packet prints its rows (each with its selector)."""
    state = shiploop_trace.current_state(run_dir) or {}
    entries = defaults.recorded(state) or []
    return defaults.row_lines(entries, selector=answers.selector_of(state)) if entries else []


def answer_row(record: dict, out: Path, run_dir: Path, case: str, choice: dict, sent_at: str) -> None:
    """Send the answer to the row ``choice`` names, or record why nothing was sent."""
    if choice["tied"]:
        record["ended"] = ("a tie between rows " + ", ".join(map(str, choice["tied"]))
                           + " on the due-time start-up decision; nothing was sent")
    elif choice["chosen"] is None:
        record["ended"] = "no printed row is about the due-time start-up decision; nothing was sent"
    elif choice["selector"] is None:
        record["ended"] = "the chosen row printed no selector; nothing was sent"
    else:
        record["sent_at"] = sent_at
        record["note"] = send(out, run_dir, reply_for(case), choice["selector"])


def watch(out: Path, case: str, deadline: float, mode: str | None, stage: str | None = None) -> dict:
    record: dict = {"case": case, "mode": mode, "reply_enabled": mode is not None,
                    **({"stage_waited_for": stage} if stage else {}),
                    "rule": {"tickets": TICKETS.pattern, "start": START.pattern, "absent": ABSENT.pattern}}
    while time.time() < deadline:
        time.sleep(POLL_SECONDS)
        if not out.is_dir():
            continue
        try:
            chosen = run_choice.choose(out).chosen
            run_dir = Path(chosen["run_dir"]) if chosen else None
            found = printed_packet(run_dir) if run_dir else None
            if found:
                state, packet = found
                block, rows = shown_rows(run_dir, packet)
                record.update(run_dir=str(run_dir), seen_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                              block_printed=block, rows=rows, recorded=defaults.recorded(state),
                              about=[about_the_point(case, row) for row in rows])
                record["note"] = None
                record["choice"] = choice = choose_row(rows)
                if mode == "reply" and any(record["about"]):
                    record["note"] = send(out, run_dir, reply_for(case), None)
                elif mode == "answer":
                    answer_row(record, out, run_dir, case, choice, defaults.SHOWN_AT)
                elif mode == "note-at":
                    # A plain note during the build that contradicts what the start-up row decided.
                    seen, why = wait_for_stage(out, run_dir, stage, deadline)
                    record["stage_seen_at"] = seen
                    if seen is None:
                        record["ended"] = why + "; nothing was sent"
                    else:
                        record["rows_at_send"] = rows_now = current_rows(run_dir)
                        plan = note_for(rows_now)
                        text = plan.pop("text", None)
                        record.update(plan)
                        if text is not None:
                            record["sent_at"] = stage
                            record["note"] = send(out, run_dir, text, None)
                elif mode in ("answer-at", "answer-late"):
                    # The answer goes when the named stage's packet first prints, to the row of the list as it then
                    # stands (a reconcile may have replaced the specification since the rows above were printed).
                    seen, why = wait_for_stage(out, run_dir, stage, deadline)
                    record["stage_seen_at"] = seen
                    if seen is None:
                        record["ended"] = why + "; nothing was sent"
                    else:
                        record["rows_at_send"] = rows_now = current_rows(run_dir)
                        record["choice_at_send"] = now = choose_row(rows_now)
                        answer_row(record, out, run_dir, case, now, stage)
                return record
            if run_dir and past_the_stage(run_dir):
                record["ended"] = "the stage after the spec was accepted before its packet was read"
                return record
        except Exception as exc:  # noqa: BLE001 - a folder still being made, a state file read mid-write
            record["last_error"] = f"{type(exc).__name__}: {exc}"[:300]
        if (out / "result.json").exists():
            record["ended"] = "the delivery ended before the stage after the spec printed its packet"
            return record
    record["ended"] = "deadline"
    return record


def arguments() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--self-test", action="store_true",
                        help="print the row the choice picks in each saved evidence/**/rows.txt, then end")
    parser.add_argument("--out", type=Path, help="the output folder of the delivery's run.py invocation")
    parser.add_argument("--case", choices=CASES)
    sending = parser.add_mutually_exclusive_group()
    sending.add_argument("--reply", dest="mode", action="store_const", const="reply",
                         help="send the requester's reply as a plain owner note when a row is about the point")
    sending.add_argument("--answer", dest="mode", action="store_const", const="answer",
                         help="send it as the answer to that row (note --default <its selector>), at once")
    sending.add_argument("--answer-late", dest="mode", action="store_const", const="answer-late",
                         help=f"send that answer only after the {LATE_STAGE} stage's packet has printed")
    sending.add_argument("--answer-at", metavar="STAGE", choices=LATER,
                         help="send that answer when STAGE's packet first prints, to the row of the list as it then "
                              "stands (" + ", ".join(LATER) + ")")
    sending.add_argument("--note-at", metavar="STAGE", choices=LATER,
                         help="when STAGE's packet first prints, send as a plain note the note of late-notes.json that "
                              "contradicts what the start-up row decided")
    parser.add_argument("--hours", type=float, default=3.0, help="give up after this long")
    return parser


def mode_of(args: argparse.Namespace) -> tuple[str | None, str | None]:
    """(the mode the record names, the stage it waits for): ``--answer-late`` is ``--answer-at plan``."""
    if args.answer_at:
        return "answer-at", args.answer_at
    if args.note_at:
        return "note-at", args.note_at
    return args.mode, LATE_STAGE if args.mode == "answer-late" else None


def main() -> int:
    parser = arguments()
    args = parser.parse_args()
    if args.self_test:
        for argv in (["--answer-at", "implement"], ["--answer-late"], ["--answer"], ["--note-at", "implement"]):
            mode, stage = mode_of(parser.parse_args(["--out", "x", "--case", CASES[0], *argv]))
            print(f"arguments {' '.join(argv)}: mode {mode}, stage {stage}")
        failed = labelled_test()
        return self_test() or failed
    if args.out is None or args.case is None:
        parser.error("--out and --case are required unless --self-test")
    mode, stage = mode_of(args)
    record = watch(args.out, args.case, time.time() + args.hours * 3600, mode, stage)
    args.out.with_name(args.out.name + SUFFIX).write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: record.get(key) for key in ("mode", "stage_waited_for", "stage_seen_at", "block_printed",
                                                        "about", "choice", "row_class", "note_sent", "note",
                                                        "ended")})[:900])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
