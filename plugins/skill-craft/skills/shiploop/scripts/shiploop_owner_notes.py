#!/usr/bin/env python3
"""Owner notes: what the run's owner writes to a running run, and how the model is sure to see it at its next step.

    shiploop note --run-dir RUN --text TEXT       # or --file PATH

Each note is its own file, ``RUN/owner-notes/N<k>.md`` (a ShipLoop record: id, written_at, text), written once and
never edited; no run lock is taken, so a note never waits for a command the model is running.  One term each:

- **shown**: the note's full text was printed to the model while an action was current, in that action's packet or in
  a held callback (``RUN/owner-notes/shown.json``, written by the script only);
- **held callback**: a ``complete`` refused once because a waiting note was not shown for its action;
- **delivered**: ShipLoop accepted a step whose packet showed the note; ``state.md`` ``owner_notes`` maps the note to
  that action, in the same save.  A held callback shows a note but never delivers it, so the next packet (read after a
  context clear) quotes it again.

The model never marks anything.  Every failure leaves a note undelivered, so it is quoted again.  Design and the
measured head room: docs/shiploop-owner-notes-design-2026-10.md.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import secrets
import sys
import time
from typing import Any, Mapping, Sequence

import shiploop_store as store

DIR = "owner-notes"
SHOWN_FILE = DIR + "/shown.json"
STATE_KEY = "owner_notes"
TITLE = "ShipLoop owner note"
# A note is quoted whole, so the most a note may hold is the most one quote prints, indentation included (Sol review
# 2026-10-26: a 1,999-character note of 1,000 short lines quoted at 17,000 characters, fit no head and was never
# delivered); the detail of a longer note belongs in a repository file the note names.
NOTE_LIMIT = 2000
# A quote's continuation lines: indented further than its first line, so a note's text cannot start a quote line.
CONTINUATION = " " * 6
# The most the notes block quotes in a packet file or a whole print; later notes are named by file until the earlier
# ones are delivered.  A head quotes what fits its room (shiploop_navigator._select_head).
BLOCK_LIMIT = 6000
# A head's smallest form names this many notes by id; the rest are counted.
FLOOR_IDS = 4
# Delivered notes the lookup line lists by id (the newest); the rest are counted.
DELIVERED_IDS = 8
# The strings the hooks find in a print (the keepalive marker, the print and narrative fences): a note cannot carry one.
FORBIDDEN = ("SHIPLOOP-RUN", "=== ShipLoop", "=== end ShipLoop")
NOTE_ID = re.compile(r"N([1-9][0-9]{0,5})")
_FILE = re.compile(r"N([1-9][0-9]{0,5})\.md")
# A quote's first line: exactly four spaces, the id, its time.  Continuation lines are indented further, so a note's
# own text cannot start a quote line.
QUOTE_LINE = re.compile(r"^ {4}(N[1-9][0-9]{0,5}) \d\d:\d\dZ  ", re.M)
_CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")

HEADER = "Owner notes (the run owner wrote these during the run; verbatim, oldest first):"
FOOTER = [
    "Act on each where it applies to this stage; the summary says, by id, what you did or which later stage it is for.",
    "Notes do not change the callback, the result template or ShipLoop's checks; if one conflicts with them, the summary "
    "says so.",
]


class NoteError(ValueError):
    """A note that cannot be written, with the reason the owner reads."""


# ---------------------------------------------------------------------------------------------------------- notes


def clean(text: str) -> str:
    """The note as it is kept: newlines normalized, trailing spaces and blank edge lines dropped.  Raises NoteError."""
    lines = [line.rstrip() for line in str(text).replace("\r\n", "\n").replace("\r", "\n").expandtabs(4).split("\n")]
    body = "\n".join(lines).strip("\n")
    if not body.strip():
        raise NoteError("the note is empty")
    if _CONTROL.search(body):
        raise NoteError("the note holds a control character; write plain text")
    for marker in FORBIDDEN:
        if marker in body:
            raise NoteError(f"the note holds {marker!r}, which the ShipLoop hooks read in a print; leave it out")
    quoted = len("\n".join(_quote_lines("N999999", "00:00", body)))
    if quoted > NOTE_LIMIT:
        raise NoteError(f"the note is {quoted:,} characters as a packet quotes it (each line indented), over the "
                        f"{NOTE_LIMIT:,} a packet quotes whole; put the detail in a file in the repository and name that "
                        "file in the note")
    return body


def _number(note_id: str) -> int:
    return int(note_id[1:])


def notes(root: str | Path) -> list[dict[str, Any]]:
    """Every note that reads as one, in the order written (a file being written, or not a note, is left out)."""
    folder = Path(root) / DIR
    found = []
    try:
        names = [entry.name for entry in os.scandir(folder) if entry.is_file(follow_symlinks=False)]
    except OSError:
        return []
    for name in names:
        match = _FILE.fullmatch(name)
        if not match:
            continue
        try:
            record = store.read_record(folder / name)
            text = clean(record["text"])
        except (OSError, KeyError, TypeError, ValueError, store.StorageError):
            continue
        note_id = "N" + match.group(1)
        if record.get("id") != note_id or not isinstance(record.get("written_at"), str):
            continue
        found.append({"id": note_id, "written_at": record["written_at"], "text": text, "file": f"{DIR}/{name}"})
    return sorted(found, key=lambda note: _number(note["id"]))


def delivered(state: Mapping[str, Any]) -> dict[str, str]:
    """{note id: the action whose accepted step delivered it}."""
    value = state.get(STATE_KEY)
    return dict(value) if isinstance(value, Mapping) else {}


def undelivered(root: str | Path, state: Mapping[str, Any]) -> list[dict[str, Any]]:
    done = delivered(state)
    return [note for note in notes(root) if note["id"] not in done]


def write(root: str | Path, text: str, *, now: float | None = None) -> dict[str, Any]:
    """Write one note as the next ``N<k>.md``, created whole or not at all (a temporary file linked into place, so two
    writers never take one number and a reader never sees half a note).  Returns the note."""
    body = clean(text)
    folder = Path(root) / DIR
    folder.mkdir(mode=0o700, exist_ok=True)
    stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() if now is None else now))
    temporary = folder / f".write-{os.getpid()}-{secrets.token_hex(4)}"
    numbers = [int(match.group(1)) for match in (_FILE.fullmatch(name) for name in os.listdir(folder)) if match]
    number = max(numbers, default=0) + 1
    try:
        while True:
            note_id = f"N{number}"
            record = {"id": note_id, "written_at": stamp, "text": body}
            fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, "O_NOFOLLOW", 0), 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(store.dumps(record, TITLE))
                handle.flush()
                os.fsync(handle.fileno())
            try:
                os.link(temporary, folder / f"{note_id}.md")
            except FileExistsError:
                number += 1
                continue
            return {**record, "file": f"{DIR}/{note_id}.md"}
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


# ---------------------------------------------------------------------------------------------------------- shown


def read_shown(root: str | Path) -> dict[str, Any]:
    """{"action": id, "packet": [ids its prints quoted whole], "held": [ids its held callbacks printed]}, or {}."""
    try:
        value = json.loads((Path(root) / SHOWN_FILE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(value, dict) or not isinstance(value.get("action"), str):
        return {}
    return {"action": value["action"],
            **{key: [item for item in value.get(key) or [] if isinstance(item, str)] for key in ("packet", "held")}}


def _shown_for(root: str | Path, action: str) -> dict[str, Any]:
    shown = read_shown(root)
    return shown if shown.get("action") == action else {"action": action, "packet": [], "held": []}


def _save_shown(root: str | Path, shown: Mapping[str, Any]) -> bool:
    """Write the shown record; False when it cannot be written (the notes then count as not shown: quoted again)."""
    try:
        store.atomic_write_text(Path(root) / SHOWN_FILE, json.dumps(dict(shown), indent=1) + "\n")
    except (OSError, store.StorageError):
        return False
    return True


def quoted_ids(printed: str) -> list[str]:
    """The note ids a print quotes whole: the quote lines inside its notes block."""
    start = printed.find("\n" + HEADER + "\n")
    if start < 0:
        return []
    end = printed.find("\n" + FOOTER[0], start)
    return QUOTE_LINE.findall(printed[start:end if end >= 0 else len(printed)])


def record_shown(root: str | Path, action: str, printed: str) -> list[str]:
    """Add the notes ``printed`` quoted whole to what ``action``'s prints have shown; returns those ids.  Writes only
    when something is new, so a print without notes changes nothing in the run; never raises (the packet is printed)."""
    ids = quoted_ids(printed)
    shown = _shown_for(root, action)
    new = [note_id for note_id in ids if note_id not in shown["packet"]]
    if new and not _save_shown(root, {**shown, "packet": shown["packet"] + new}):
        return []
    return ids


def to_hold(root: str | Path, state: Mapping[str, Any], action: str) -> list[dict[str, Any]]:
    """The undelivered notes ``action``'s prints have not shown whole: its callback is held for them."""
    shown = _shown_for(root, action)
    seen = set(shown["packet"]) | set(shown["held"])
    return [note for note in undelivered(root, state) if note["id"] not in seen]


def mark_held(root: str | Path, action: str, held: Sequence[Mapping[str, Any]]) -> bool:
    """Record that a held callback of ``action`` printed ``held``; False when it cannot be recorded.  A hold that
    could not be recorded is not made: it would hold every callback after it."""
    shown = _shown_for(root, action)
    return _save_shown(root, {**shown, "held": shown["held"] + [note["id"] for note in held if note["id"] not in shown["held"]]})


def deliver(root: str | Path, updated: Mapping[str, Any], action: str) -> Mapping[str, Any]:
    """``updated`` (the state a ``complete`` of ``action`` is about to save) with the notes ``action``'s packet showed
    marked delivered by it."""
    shown = _shown_for(root, action)
    waiting = {note["id"] for note in undelivered(root, updated)}
    ids = [note_id for note_id in shown["packet"] if note_id in waiting]
    if not ids:
        return updated
    result = dict(updated)
    result[STATE_KEY] = {**delivered(updated), **{note_id: action for note_id in ids}}
    return result


def validate(value: Any, action_id: re.Pattern) -> bool:
    """Whether a saved ``owner_notes`` value has its shape: {N<k>: action id}."""
    return isinstance(value, Mapping) and all(
        isinstance(key, str) and NOTE_ID.fullmatch(key) is not None
        and isinstance(action, str) and action_id.fullmatch(action) is not None for key, action in value.items())


# ---------------------------------------------------------------------------------------------------------- text


def _quote_lines(note_id: str, hhmm: str, text: str) -> list[str]:
    lines = text.split("\n")
    return [f"    {note_id} {hhmm}Z  {lines[0]}", *(CONTINUATION + line if line else "" for line in lines[1:])]


def quote(note: Mapping[str, Any]) -> list[str]:
    """One note as a packet quotes it: its id and time (UTC), then its text, every line indented."""
    return _quote_lines(note["id"], str(note["written_at"])[11:16], note["text"])


def _ids(notes_: Sequence[Mapping[str, Any]]) -> str:
    ids = [note["id"] for note in notes_]
    return ids[0] if len(ids) == 1 else ", ".join(ids[:-1]) + " and " + ids[-1]


def _named_line(root: Path, rest: Sequence[Mapping[str, Any]]) -> str:
    files = " and ".join(str(root / note["file"]) for note in rest) if len(rest) <= 2 else \
        "each " + str(root / DIR) + "/N<id>.md"
    verb = "is" if len(rest) == 1 else "are"
    return f"    {_ids(rest)} {verb} not printed here for room: read {files} before acting."


def _form(root: Path, waiting: Sequence[Mapping[str, Any]], quoted: int) -> list[str]:
    lines = [HEADER]
    for note in waiting[:quoted]:
        lines.extend(quote(note))
    if waiting[quoted:]:
        lines.append(_named_line(root, waiting[quoted:]))
    return lines + FOOTER


def floor(root: Path, waiting: Sequence[Mapping[str, Any]]) -> list[str]:
    """The smallest form, one line: the notes by id and size, and where to read them."""
    chars = sum(len(note["text"]) for note in waiting)
    if len(waiting) == 1:
        note = waiting[0]
        return [f"Owner note {note['id']} ({chars:,} characters) is not printed here for room: read "
                f"{root / note['file']} before acting; the summary says what you did about it."]
    named = waiting[:FLOOR_IDS]
    ids = ", ".join(note["id"] for note in named) + (f" and {len(waiting) - len(named)} later ones"
                                                     if len(waiting) > len(named) else "")
    return [f"Owner notes {ids} ({len(waiting)} notes, {chars:,} characters) are not printed here for room: read each "
            f"{root / DIR}/N<id>.md before acting; the summary says, by id, what you did about each."]


def packet_forms(root: str | Path, state: Mapping[str, Any]) -> tuple[list[str], list[list[str]]]:
    """(the block the packet file and a whole print carry, the shorter forms a head may print instead, fullest first).

    The file quotes every undelivered note, oldest first, while the quotes stay within ``BLOCK_LIMIT``, and names the
    rest by file; the head forms quote one note fewer each, down to the one-line floor."""
    root = Path(root)
    waiting = undelivered(root, state)
    if not waiting:
        return [], []
    quoted, used = 0, 0
    for note in waiting:
        size = sum(len(line) + 1 for line in quote(note))
        if quoted and used + size > BLOCK_LIMIT:
            break
        quoted, used = quoted + 1, used + size
    return _form(root, waiting, quoted), [*(_form(root, waiting, count) for count in range(quoted - 1, 0, -1)),
                                          floor(root, waiting)]


def delivered_lines(root: str | Path, state: Mapping[str, Any]) -> list[str]:
    """One lookup line: the delivered notes with the step that delivered each, so a later stage can read one again."""
    done = delivered(state)
    if not done:
        return []
    steps = {entry.get("action"): index for index, entry in enumerate(state.get("history") or (), 1)}
    ids = sorted(done, key=_number)
    listed = ids[-DELIVERED_IDS:]
    parts = [f"{note_id} (step {steps[done[note_id]]})" if done[note_id] in steps else note_id for note_id in listed]
    earlier = f" and {len(ids) - len(listed)} earlier" if len(ids) > len(listed) else ""
    return [f"Owner notes already delivered: {', '.join(parts)}{earlier}, in {Path(root) / DIR}/; read one again when "
            "this stage's work touches it."]


def hold_text(held: Sequence[Mapping[str, Any]], *, check: bool = False) -> str:
    """What a held callback prints: the notes whole, and what to do (a check says it is a notice)."""
    one = len(held) == 1
    noun = "an owner note" if one else "owner notes"
    lines = [(f"ShipLoop check: {noun} this action's packet did not print in full (it shows the note now; the "
              "callback is not held for it):") if check else
             f"ShipLoop held this callback once: {noun} this action's packet did not print in full (written after "
             "it was printed, or no room in its head)."]
    for note in held:
        lines.extend(quote(note))
    if not check:
        lines += [("If it changes this step's work" if one else "If one changes this step's work")
                  + ", change the work and the result first. Then run the same callback again in this turn; it is not "
                  "held twice for the same note.",
                  "The summary says, by id, what you did about " + ("it" if one else "each") + "."]
    return "\n".join(lines)


# ---------------------------------------------------------------------------------------------------------- CLI


def main(argv: Sequence[str] | None = None, *, trace_record: dict[str, Any] | None = None) -> int:
    """``shiploop note``: the owner writes one note to a current run; never takes the run lock or prints a packet."""
    import shiploop_navigator as navigator
    import shiploop_trace as trace

    parser = argparse.ArgumentParser(prog="shiploop note",
                                     description="leave a note the run's next step quotes until a step it was shown "
                                                 "in is accepted")
    parser.add_argument("--run-dir", required=True)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--text", help="the note")
    source.add_argument("--file", help="a file holding the note")
    args = parser.parse_args(argv)
    root = Path(args.run_dir).expanduser()
    if root.is_symlink():
        print("ShipLoop note: the run directory must not be a symlink; nothing was written.", file=sys.stderr)
        return 2
    root = root.resolve()
    # The input first, so a slow or bad --file never reads the run's state early, and a refusal touches nothing.
    try:
        body = clean(args.text if args.text is not None else Path(args.file).expanduser().read_text(encoding="utf-8"))
    except UnicodeDecodeError:
        print("ShipLoop note: the file is not UTF-8 text; nothing was written.", file=sys.stderr)
        return 2
    except (NoteError, OSError) as exc:
        print(f"ShipLoop note: {exc}; nothing was written.", file=sys.stderr)
        return 2
    state = trace.current_state(root) if (root / "state.md").is_file() else None
    if state is None:
        print(f"ShipLoop note: {root} is not a current ShipLoop run (no state.md, or retired, or it cannot be loaded); "
              "nothing was written.", file=sys.stderr)
        return 2
    if state.get("status") in ("done", "halted"):
        print(f"ShipLoop note: the run is {state['status']}; no later step would read a note, so nothing was written.",
              file=sys.stderr)
        return 2
    try:
        note = write(root, body)
    except (NoteError, OSError, store.StorageError) as exc:
        print(f"ShipLoop note: {exc}; nothing was written.", file=sys.stderr)
        return 2
    # Only a written note is a command in the run's trace: a refused one leaves the run as it was.
    if trace_record is not None:
        trace_record.update(root=root, before=state, note=note["id"])
    stage, action, item = trace._cursor(state)
    where = f"{(item + ' ') if item else ''}{stage}"
    print(f"Owner note {note['id']} written: {root / note['file']}.")
    status = state.get("status")
    if status == "blocked":
        wait = navigator.awaiting(state)
        asked = navigator._awaiting_text(wait[1]) if wait else "the recorded question"
        print(f"The run is blocked on: {asked} Answer it with `resume --answer`; the packet after the resume quotes "
              "this note.")
    elif status == "paused":
        print("The run is paused; the packet after `resume` quotes this note.")
    else:
        current = state.get("active_improve")
        print(f"The run is at {where} (action {(action or {}).get('id')})"
              + ("; an Improve stage is reviewing it, and the producer packet after it quotes the note" if current
                 else "; the model sees the note at its next ShipLoop callback or `next`") + ".")
    return 0
