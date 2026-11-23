#!/usr/bin/env python3
"""Owner notes: what the run's owner writes to a running run, and the row in a stage's result that accounts for each.

    shiploop note --run-dir RUN --text TEXT       # or --file PATH

Each note is its own file, ``RUN/owner-notes/N<k>.md`` (a ShipLoop record: id, written_at, text), written once and
never edited; no run lock is taken, so a note never waits for a command the model is running.

A note is settled by a row, never by a print.  A done result of any producer stage may carry ``notes``: one row
``{"note", "did", "detail"}`` (``item`` too, on an applied row at plan and carry-forward) per note, where ``did`` is
``applied``, ``already``, ``carried`` or ``declined``.  Three words for where a note stands, read from the rows of
every accepted done result in the order the run accepted them (``ledger``):

- **open**: no result has a row for it;
- **carried**: its latest row is ``carried``: the stage needed something it may not change;
- **settled**: its latest row is ``applied``, ``already`` or ``declined``; a settled note stays settled for the run.

A fresh done result owes a row for every open note, and for every carried one except a note carried by a stage of a
work item (step-plan to document), which that item's carry-forward owes; ``handoff`` owes every note not settled, and
it and carry-forward may not carry (``owed``).  ShipLoop refuses done while a row is missing, extra or malformed, and
the refusal's first line names the notes, their folder and the result file (``refusal``).  Nothing asks and nothing
waits.  Design: docs/experiments/ratchet-pilot-20261120/shiploop-notes/DESIGN.md (section 2).
"""
from __future__ import annotations

import argparse
import html
import os
from pathlib import Path
import re
import secrets
import sys
import time
from typing import Any, Mapping, Sequence

import shiploop_stage_spec as stage_spec
import shiploop_store as store

DIR = "owner-notes"
FIELD = "notes"
TITLE = "ShipLoop owner note"
# A note is quoted whole, so the most a note may hold is the most one quote prints, indentation included (Sol review
# 2026-10-26: a 1,999-character note of 1,000 short lines quoted at 17,000 characters, fit no head and was never
# delivered); the detail of a longer note belongs in a repository file the note names.
NOTE_LIMIT = 2000
# A quote's continuation lines: indented further than its first line, so a note's text cannot start a quote line.
CONTINUATION = " " * 6
# The most the notes block quotes in a packet file or a whole print, and a refusal of its owed notes; later notes are
# named by file.  A head quotes what fits its room (shiploop_navigator._select_head).
BLOCK_LIMIT = 6000
# A head's smallest form names this many notes by id; the rest are counted.
FLOOR_IDS = 4
# Notes the lookup line lists by id (the newest); the rest are counted.
LISTED_IDS = 8
# Display cut: the characters of a row's detail the packet's carried line, the lookup line and the done packet print
# (the report and the stored result keep it whole).
DETAIL_SHOWN = 160
# The strings the hooks find in a print (the keepalive marker, the print and narrative fences): a note cannot carry one.
FORBIDDEN = ("SHIPLOOP-RUN", "=== ShipLoop", "=== end ShipLoop")
NOTE_ID = re.compile(r"N([1-9][0-9]{0,5})")
_FILE = re.compile(r"N([1-9][0-9]{0,5})\.md")
_CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")
_SURROGATE = re.compile("[\ud800-\udfff]")  # an undecodable command-line byte arrives as one

# The four answers a row gives, and the three that settle a note.
DID = ("applied", "already", "carried", "declined")
SETTLES = frozenset(("applied", "already", "declined"))
CARRY_FORWARD, HANDOFF, PLAN = "carry-forward", "handoff", "plan"
# The stages whose applied row names the work item that does the work (design 2.3), and the two that settle every note
# they owe (no carried row).
ITEM_STAGES = frozenset((PLAN, CARRY_FORWARD))
SETTLE_ONLY = frozenset((CARRY_FORWARD, HANDOFF))
# A work item's steps: a note one of them carries is owed by that item's carry-forward, and by no step before it.
ITEM_STEPS = frozenset(stage_spec.INNER) - {CARRY_FORWARD}
ROW_KEYS = ("note", "did", "detail", "item")

HEADER = ("Owner notes this stage must account for (the run owner wrote these during the run; verbatim, oldest first; "
          "each is a file in {folder}/):")
# The result template's row.  A text equal to one of these is a placeholder left in.
DID_PLACEHOLDER = "<applied | already | carried | declined>"
SETTLE_PLACEHOLDER = "<applied | already | declined>"
DETAIL_PLACEHOLDER = "<what this stage changed, where the run already does it, what it needs, or why it cannot be done>"
ITEM_PLACEHOLDER = "<with applied: the work item of the queue this result leaves that does it>"
_PLACEHOLDERS = frozenset((DID_PLACEHOLDER, SETTLE_PLACEHOLDER, DETAIL_PLACEHOLDER, ITEM_PLACEHOLDER))


class NoteError(ValueError):
    """A note that cannot be written, a notes folder that cannot be read, or a ``notes`` field of the wrong shape."""


# ---------------------------------------------------------------------------------------------------------- notes


def clean(text: str) -> str:
    """The note as it is kept: newlines normalized, trailing spaces and blank edge lines dropped.  Raises NoteError."""
    lines = [line.rstrip() for line in str(text).replace("\r\n", "\n").replace("\r", "\n").expandtabs(4).split("\n")]
    body = "\n".join(lines).strip("\n")
    if not body.strip():
        raise NoteError("the note is empty")
    if _CONTROL.search(body):
        raise NoteError("the note holds a control character; write plain text")
    if _SURROGATE.search(body):
        raise NoteError("the note holds a byte that is not UTF-8 text; write plain text")
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


def read(root: str | Path) -> list[dict[str, Any]]:
    """Every note on file, in the order written; the one read a result's admission makes.

    A folder that does not exist holds no note.  A folder or a note file that exists and cannot be read raises
    NoteError: the result is then refused, never judged against an empty list.  A file that is not a note (a name that
    is not N<k>.md, a record that does not parse) is left out; a note is linked into place whole, so none is half
    written."""
    folder = Path(root) / DIR
    try:
        names = [entry.name for entry in os.scandir(folder) if entry.is_file(follow_symlinks=False)]
    except FileNotFoundError:
        return []
    except OSError as exc:
        raise NoteError(f"the owner notes folder {folder} cannot be read ({exc.strerror or exc})") from exc
    found = []
    for name in names:
        match = _FILE.fullmatch(name)
        if not match:
            continue
        try:
            record = store.read_record(folder / name)
        except OSError as exc:
            raise NoteError(f"the owner note {folder / name} cannot be read ({exc.strerror or exc})") from exc
        except (KeyError, TypeError, ValueError, store.StorageError):
            continue
        try:
            text = clean(record["text"])
        except (KeyError, TypeError, ValueError):
            continue
        note_id = "N" + match.group(1)
        if record.get("id") != note_id or not isinstance(record.get("written_at"), str):
            continue
        found.append({"id": note_id, "written_at": record["written_at"], "text": text, "file": f"{DIR}/{name}"})
    return sorted(found, key=lambda note: _number(note["id"]))


def notes(root: str | Path) -> list[dict[str, Any]]:
    """Every note that reads as one, for a display (a packet, the done packet, the report): ``read``, with a folder that
    cannot be read shown as holding none (the admission that follows refuses it)."""
    try:
        return read(root)
    except NoteError:
        return []


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


# ---------------------------------------------------------------------------------------------------------- rows


def canonical(value: Any) -> list[dict[str, str]]:
    """The stored form of a done result's ``notes``: shape only (a list of objects of text values, each text stripped),
    so a saved result reloads without reading a note file whatever a later edit does to the row's fields.  The exact
    rows are checked when the result is admitted (``faults``)."""
    if not isinstance(value, list):
        raise NoteError('notes must be a list of rows, one {"note", "did", "detail"} per owner note this stage accounts '
                        "for")
    rows = []
    for index, row in enumerate(value):
        if not (isinstance(row, Mapping) and all(isinstance(key, str) and isinstance(text, str)
                                                 for key, text in row.items())):
            raise NoteError(f'notes[{index}] must be an object of text values: {{"note", "did", "detail"}}')
        rows.append({key: text.strip() for key, text in row.items()})
    return rows


def ledger(state: Mapping[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """{note id: its rows, oldest first}, from the ``notes`` of every accepted done result in ``history`` order (results
    a reconcile or a send-back later took out of the current view included).  Each row carries the step number, the
    stage, the work item and the action of the result that held it."""
    found: dict[str, list[dict[str, Any]]] = {}
    accepted = state.get("accepted") or {}
    for step, entry in enumerate(state.get("history") or (), 1):
        result = accepted.get(entry.get("action")) if isinstance(entry, Mapping) else None
        if not isinstance(result, Mapping) or result.get("outcome") != "done":
            continue
        for row in result.get(FIELD) or ():
            if not isinstance(row, Mapping) or not isinstance(row.get("note"), str):
                continue
            found.setdefault(row["note"], []).append({
                "note": row["note"], "did": str(row.get("did", "")), "detail": str(row.get("detail", "")),
                **({"item": str(row["item"])} if "item" in row else {}), "step": step, "stage": entry.get("stage"),
                "workitem": entry.get("workitem"), "action": entry.get("action")})
    return found


def standing(rows: Sequence[Mapping[str, Any]]) -> str:
    """Where a note stands: ``open`` (no row), ``carried`` (its latest row is carried) or ``settled``."""
    if not rows:
        return "open"
    return "settled" if rows[-1]["did"] in SETTLES else "carried"


def _carried_in_item(row: Mapping[str, Any]) -> bool:
    return row["did"] == "carried" and row.get("stage") in ITEM_STEPS


def owes(rows: Sequence[Mapping[str, Any]], stage: str, workitem: str | None) -> bool:
    """Whether a fresh done result of ``stage`` (in ``workitem``) owes a row for a note with these rows."""
    where = standing(rows)
    if where == "settled":
        return False
    if where == "open" or stage == HANDOFF:
        return True
    last = rows[-1]
    if _carried_in_item(last):
        return stage == CARRY_FORWARD and workitem == last.get("workitem")
    return True


def owed(state: Mapping[str, Any], found: Sequence[Mapping[str, Any]], stage: str,
         workitem: str | None) -> list[dict[str, Any]]:
    """The notes of ``found`` a fresh done result of ``stage`` owes a row for, oldest first."""
    rows = ledger(state)
    return [dict(note) for note in found if owes(rows.get(note["id"], ()), stage, workitem)]


def _who_next(stage: str) -> str:
    """Who accounts for a note this stage carries."""
    return "this work item's carry-forward" if stage in ITEM_STEPS else "the next stage"


def _where(row: Mapping[str, Any]) -> str:
    """The stage of a row, with its work item: "implement of W1", "spec"."""
    return str(row.get("stage")) + (" of " + str(row["workitem"]) if row.get("workitem") else "")


def _cut(text: Any, limit: int = DETAIL_SHOWN) -> str:
    text = " ".join(str(text).split())
    return text if len(text) <= limit else text[:limit - 1].rstrip() + "…"


def owed_by(rows: Sequence[Mapping[str, Any]]) -> str:
    """Who accounts for a note that is not settled: the next stage, or the carry-forward of the item that carried it."""
    if rows and _carried_in_item(rows[-1]):
        return str(rows[-1].get("workitem")) + " carry-forward"
    return "the next stage"


# ---------------------------------------------------------------------------------------------------------- the gate


def _queue(state: Mapping[str, Any], stage: str, result: Mapping[str, Any]) -> list[str]:
    """The work items an applied row's ``item`` may name (design 2.3): at plan the queue the result leaves; at
    carry-forward the future queue it leaves (the result's ``work_items`` replace every item after the current one)."""
    given = result.get("work_items")
    if isinstance(given, list):
        return [str(row.get("id")).strip() for row in given if isinstance(row, Mapping) and row.get("id") is not None]
    items = [str(row.get("id")) for row in state.get("work_items") or () if isinstance(row, Mapping)]
    return items if stage == PLAN else items[int(state.get("work_index") or 0) + 1:]


def _ids(ids: Sequence[str]) -> str:
    ids = list(ids)
    return ids[0] if len(ids) == 1 else ", ".join(ids[:-1]) + " and " + ids[-1]


def _did_list(stage: str) -> str:
    allowed = [did for did in DID if not (did == "carried" and stage in SETTLE_ONLY)]
    return ", ".join(allowed[:-1]) + " or " + allowed[-1]


def _row_fault(row: Mapping[str, Any], state: Mapping[str, Any], stage: str, workitem: str | None,
               result: Mapping[str, Any]) -> str | None:
    """What is wrong with one owed note's row, or None."""
    unknown = sorted(str(key) for key in row if key not in ROW_KEYS)
    if unknown:
        return "has the unknown " + ", ".join(repr(key) for key in unknown) + ': a row holds only "note", "did", "detail"' \
               + (' and, on an applied row, "item"' if stage in ITEM_STAGES else "")
    did = row.get("did")
    if not isinstance(did, str) or did.strip() not in DID:
        return f'"did" is {did!r}, not one of {_did_list(stage)}'
    did = did.strip()
    if did == "carried" and stage in SETTLE_ONLY:
        return (f'"did" is "carried", which {stage} may not give: it settles every note it owes ({_did_list(stage)})'
                + ('; a note that needs a later work item is "applied" with that item' if stage == CARRY_FORWARD else ""))
    detail = row.get("detail")
    if not isinstance(detail, str) or not detail.strip():
        return '"detail" is empty: say what changed, where the run already does it, what it needs or why it cannot be done'
    if " ".join(detail.split()) in _PLACEHOLDERS:
        return '"detail" still holds the template placeholder'
    item = row.get("item")
    if "item" in row and (stage not in ITEM_STAGES or did != "applied"):
        return ('"item" goes only on an applied row at plan or carry-forward' if stage not in ITEM_STAGES else
                f'"item" goes only on an applied row; this one is {did}') + ": remove it"
    if stage not in ITEM_STAGES or did != "applied":
        return None
    queue = _queue(state, stage, result)
    listed = ", ".join(queue) if queue else "it leaves none"
    where = "the queue this result leaves" if stage == PLAN else "the future queue this result leaves"
    if not isinstance(item, str) or not item.strip():
        return f'"item" is missing: an applied row at {stage} names the work item of {where} that does it ({listed})'
    item = item.strip()
    if " ".join(item.split()) in _PLACEHOLDERS:
        return '"item" still holds the template placeholder'
    if stage == CARRY_FORWARD and item == workitem:
        return (f'"item" is {item}, the item this carry-forward closes: name a pending item of {where} that does the '
                'work ({listed}), or say "already" when the run already does it')
    if stage == CARRY_FORWARD and item in (state.get("completed_work_items") or ()):
        return f'"item" is {item}, a finished item: name a pending item of {where} that does the work ({listed})'
    if item not in queue:
        return f'"item" {item!r} is not in {where} ({listed})'
    return None


def faults(found: Sequence[Mapping[str, Any]], state: Mapping[str, Any], stage: str, workitem: str | None,
           result: Any, *, folder: Path) -> list[dict[str, Any]]:
    """What keeps a submitted result from accounting for the notes ``found`` (the admission's one read): one entry per
    fault, ``{"note", "kind", "text"}`` with kind ``missing``, ``row`` or ``extra``.  Only a done result owes rows; any
    other outcome holds none (``notes`` is a done-only field) and leaves the notes owed."""
    if not isinstance(result, Mapping) or result.get("outcome") != "done":
        return []
    owing = [note["id"] for note in owed(state, found, stage, workitem)]
    rows = result.get(FIELD, [])
    out: list[dict[str, Any]] = []
    if not isinstance(rows, list):
        out.append({"note": None, "kind": "shape", "text": '"notes" is not a list of rows'})
        rows = []
    led, on_file = ledger(state), {note["id"] for note in found}
    seen: set[str] = set()
    for index, row in enumerate(rows):
        note_id = row.get("note").strip() if isinstance(row, Mapping) and isinstance(row.get("note"), str) else None
        if not isinstance(row, Mapping) or not note_id:
            out.append({"note": None, "kind": "extra", "text": f'notes[{index}] names no owner note: give "note": "N<k>"'})
        elif note_id in seen:
            out.append({"note": note_id, "kind": "extra", "text": f"{note_id} has two rows; keep one"})
        elif note_id not in owing:
            history = led.get(note_id, ())
            why = (f"no owner note {note_id} is on file in {folder}/" if note_id not in on_file else
                   f"{note_id} was settled at {_where(history[-1])} (step {history[-1]['step']}, {history[-1]['did']}); "
                   "a settled note takes no further row" if standing(history) == "settled" else
                   f"{note_id} was carried by {_where(history[-1])}: {owed_by(history)} accounts for it")
            out.append({"note": note_id, "kind": "extra", "text": f"this stage owes no row for {note_id}: {why}; remove "
                                                                  "the row"})
        else:
            seen.add(note_id)
            fault = _row_fault(row, state, stage, workitem, result)
            if fault:
                out.append({"note": note_id, "kind": "row", "text": f"{note_id}'s row {fault}"})
    out.extend({"note": note_id, "kind": "missing", "text": f"{note_id} has no row"} for note_id in owing
               if note_id not in seen)
    return out


# ---------------------------------------------------------------------------------------------------------- texts


def _quote_lines(note_id: str, hhmm: str, text: str) -> list[str]:
    lines = text.split("\n")
    return [f"    {note_id} {hhmm}Z  {lines[0]}", *(CONTINUATION + line if line else "" for line in lines[1:])]


def quote(note: Mapping[str, Any]) -> list[str]:
    """One note as a packet quotes it: its id and time (UTC), then its text, every line indented."""
    return _quote_lines(note["id"], str(note["written_at"])[11:16], note["text"])


def _quote_with_carry(note: Mapping[str, Any], rows: Sequence[Mapping[str, Any]]) -> list[str]:
    """The quote, and for a carried note who carried it and what it needs."""
    lines = quote(note)
    if rows and rows[-1]["did"] == "carried":
        lines.append(f"{CONTINUATION}Carried here by {_where(rows[-1])} (step {rows[-1]['step']}): "
                     + _cut(rows[-1]["detail"]))
    return lines


def _named_line(root: Path, rest: Sequence[Mapping[str, Any]]) -> str:
    files = " and ".join(str(root / note["file"]) for note in rest) if len(rest) <= 2 else \
        "each " + str(root / DIR) + "/N<id>.md"
    verb = "is" if len(rest) == 1 else "are"
    return f"    {_ids([note['id'] for note in rest])} {verb} not printed here for room: read {files} before acting."


def duty(stage: str) -> str:
    """What the block tells the stage to do with each note it owes (design 2.6): the row and the four meanings of
    ``did``; carry-forward and handoff leave out ``carried``, plan and carry-forward add the ``item``; carry-forward and
    document say what a note that changes a requirement is."""
    applied = "this stage did what it asks, within what this stage may change; say what changed"
    if stage == PLAN:
        applied += ', and name in "item" the work item of this result\'s queue that does it'
    elif stage == CARRY_FORWARD:
        applied += (', and name in "item" the pending work item of the queue this result leaves that does it, never this '
                    "item or a finished one")
    parts = [f'"applied" ({applied})', '"already" (the run already does it; say where)']
    if stage not in SETTLE_ONLY:
        parts.append(f'"carried" (it needs something this stage may not change; say what; {_who_next(stage)} must then '
                     "account for it)")
    parts.append('"declined" (it cannot be done in this run; say why)')
    row = '{"note", "did", "detail"} per note' + (', with "item" on an applied one' if stage in ITEM_STAGES else "")
    text = ("Each is the run owner's instruction for this run. Account for each in this stage's result, \"notes\": one "
            f"{row}. did: " + ", ".join(parts) + ". ShipLoop refuses done without them.")
    if stage == CARRY_FORWARD:
        text += (' A note that needs no work is "already". An owner note is the direction the rule on a changed '
                 "requirement waits for: when one changes a requirement, revise that requirement's entry in "
                 "KNOWLEDGE/spec.md in place (the ID stays; say the owner note revised it; keep no copy of the old "
                 "clause), queue the item that follows it, and report done, not blocked.")
    elif stage == "document":
        text += (' A note that changes a requirement is "carried" (this work item\'s carry-forward revises the '
                 "requirement and queues its work), not a send-back.")
    return text


def _form(root: Path, waiting: Sequence[Mapping[str, Any]], quoted: int, rows: Mapping[str, Sequence[Any]],
          stage: str) -> list[str]:
    lines = [HEADER.format(folder=root / DIR)]
    for note in waiting[:quoted]:
        lines.extend(_quote_with_carry(note, rows.get(note["id"], ())))
    if waiting[quoted:]:
        lines.append(_named_line(root, waiting[quoted:]))
    return lines + [duty(stage)]


def floor(root: Path, waiting: Sequence[Mapping[str, Any]], stage: str) -> list[str]:
    """The smallest form: one line naming the notes by id and size and where to read them, and the duty."""
    chars = sum(len(note["text"]) for note in waiting)
    if len(waiting) == 1:
        note = waiting[0]
        line = (f"Owner note {note['id']} ({chars:,} characters) is not printed here for room: read "
                f"{root / note['file']} before acting.")
    else:
        named = waiting[:FLOOR_IDS]
        ids = ", ".join(note["id"] for note in named) + (f" and {len(waiting) - len(named)} later ones"
                                                         if len(waiting) > len(named) else "")
        line = (f"Owner notes {ids} ({len(waiting)} notes, {chars:,} characters) are not printed here for room: read "
                f"each {root / DIR}/N<id>.md before acting.")
    return [line, duty(stage)]


def _quoted_count(waiting: Sequence[Mapping[str, Any]], rows: Mapping[str, Sequence[Any]]) -> int:
    """How many notes, oldest first, a block quotes whole within ``BLOCK_LIMIT`` (always the first)."""
    quoted, used = 0, 0
    for note in waiting:
        size = sum(len(line) + 1 for line in _quote_with_carry(note, rows.get(note["id"], ())))
        if quoted and used + size > BLOCK_LIMIT:
            break
        quoted, used = quoted + 1, used + size
    return quoted


def packet_forms(root: str | Path, state: Mapping[str, Any], stage: str,
                 waiting: Sequence[Mapping[str, Any]]) -> tuple[list[str], list[list[str]]]:
    """(the block the packet file and a whole print carry, the shorter forms a head may print instead, fullest first),
    for the notes ``waiting`` that ``stage`` owes.

    The file quotes the notes, oldest first, while the quotes stay within ``BLOCK_LIMIT``, and names the rest by file; a
    carried note is quoted again with who carried it.  The duty ends every form, the floor included."""
    root = Path(root)
    if not waiting:
        return [], []
    rows = ledger(state)
    quoted = _quoted_count(waiting, rows)
    return _form(root, waiting, quoted, rows, stage), [
        *(_form(root, waiting, count, rows, stage) for count in range(quoted - 1, 0, -1)), floor(root, waiting, stage)]


def template_rows(stage: str, waiting: Sequence[Mapping[str, Any]]) -> list[dict[str, str]]:
    """The result template's ``notes`` rows: one per owed note, by id."""
    did = SETTLE_PLACEHOLDER if stage in SETTLE_ONLY else DID_PLACEHOLDER
    return [{"note": note["id"], "did": did, "detail": DETAIL_PLACEHOLDER,
             **({"item": ITEM_PLACEHOLDER} if stage in ITEM_STAGES else {})} for note in waiting]


def fallback_line(root: str | Path, waiting: Sequence[Mapping[str, Any]]) -> str:
    """The line a minimal result template keeps when the long one is not printed: the notes owed and their folder."""
    return (f"Owner {'note' if len(waiting) == 1 else 'notes'} {_ids([note['id'] for note in waiting])} owed here (each a "
            f"file in {Path(root) / DIR}/): give each its row in \"notes\" as the owner notes block above says.")


def gate_words(stage: str) -> str:
    """The refusal the stage's checked line names while a note is owed."""
    words = 'a missing or extra "notes" row for an owner note this stage owes, a did outside ' + _did_list(stage) + \
            ", or an empty detail"
    if stage in ITEM_STAGES:
        words += ", or an applied row whose item is not " + ("in the queue this result leaves" if stage == PLAN else
                                                             "a pending item of the queue this result leaves")
    return words


def accounted_lines(root: str | Path, state: Mapping[str, Any], waiting: Sequence[Mapping[str, Any]]) -> list[str]:
    """One lookup line: the notes with rows that this stage does not owe, settled (how, by which step) or carried (by
    whom, for whom), newest ``LISTED_IDS``, so a later stage can read one again."""
    rows = ledger(state)
    owing = {note["id"] for note in waiting}
    ids = sorted((note_id for note_id in rows if note_id not in owing and NOTE_ID.fullmatch(note_id)), key=_number)
    if not ids:
        return []
    listed = ids[-LISTED_IDS:]
    parts = []
    for note_id in listed:
        last = rows[note_id][-1]
        parts.append(f"{note_id} {last['did']} at {_where(last)} (step {last['step']})" if last["did"] in SETTLES else
                     f"{note_id} carried by {_where(last)} (step {last['step']}), for {owed_by(rows[note_id])}")
    earlier = f" and {len(ids) - len(listed)} earlier" if len(ids) > len(listed) else ""
    return [(f"Owner notes accounted for: {'; '.join(parts)}{earlier}; in {Path(root) / DIR}/, with each row in its "
             "result's \"notes\"; read one again when this stage's work touches it.")]


def refusal(root: str | Path, result_path: str | Path, found: Sequence[Mapping[str, Any]], state: Mapping[str, Any],
            stage: str, workitem: str | None, found_faults: Sequence[Mapping[str, Any]]) -> str:
    """The refusal of a result that does not account for its notes, without the command's prefix (``ShipLoop check:``
    or ``ShipLoop navigator:``).  Its first line can be acted on alone (a host may show its model only that much): it
    names the notes, the folder to read and the result file to change.  Then the row and the four meanings of ``did``,
    every fault, the owed notes' words within ``BLOCK_LIMIT``, and what to do when a note changes the stage's work."""
    root = Path(root)
    folder = root / DIR
    ids = sorted({fault["note"] for fault in found_faults if fault["kind"] in ("missing", "row") and fault["note"]},
                 key=_number)
    if ids:
        missing_only = all(fault["kind"] == "missing" for fault in found_faults if fault["note"] in ids)
        one = len(ids) == 1
        read_what = f"read {folder / (ids[0] + '.md')}" if one else f"read each in {folder}/"
        verb = ("add its row to" if missing_only else "fix its row in") if one else \
            ("add their rows to" if missing_only else "add or fix their rows in")
        first = (f"owner {'note' if one else 'notes'} {_ids(ids)} {'is' if one else 'are'} not accounted for: "
                 f"{read_what}, {verb} \"notes\" in {result_path}, then run this again.")
    elif any(fault["kind"] == "shape" for fault in found_faults):
        first = (f"\"notes\" in {result_path} is not a list of rows: give it as [] or as one row per owed note, then "
                 "run this again.")
    else:
        extra = [fault for fault in found_faults if fault["kind"] == "extra"]
        named = sorted({fault["note"] for fault in extra if fault["note"]}, key=_number)
        first = (f"\"notes\" in {result_path} has a row this stage does not owe"
                 + (f" ({_ids(named)})" if named else "") + ": remove it, then run this again.")
    shape = ('A row: {"note": "N<k>", "did": "' + '" | "'.join(did for did in DID if not (did == "carried" and stage in
                                                                                         SETTLE_ONLY))
             + '", "detail": "<text>"' + (', "item": "<work item>" (applied only)' if stage in ITEM_STAGES else "")
             + "}, one per owed note and no other row:")
    meanings = ["  applied: this stage did what the note asks, within what this stage may change; detail says what "
                "changed" + ("; item names the work item of the queue this result leaves that does it" if stage == PLAN
                             else "; item names the pending work item of the queue this result leaves that does it "
                                  "(not this item, not a finished one)" if stage == CARRY_FORWARD else ""),
                "  already: the run already does what it asks; detail says where",
                (f"  carried: not at {stage}, which settles every note it owes" if stage in SETTLE_ONLY else
                 f"  carried: it needs something this stage may not change; detail says what; {_who_next(stage)} must "
                 "then account for it"),
                "  declined: it cannot be done in this run; detail says why"]
    lines = [first, shape, *meanings, "What is wrong:", *("- " + fault["text"] for fault in found_faults)]
    waiting = owed(state, found, stage, workitem)
    if waiting:
        rows = ledger(state)
        quoted = _quoted_count(waiting, rows)
        lines.append("The notes this stage owes (verbatim, oldest first):")
        for note in waiting[:quoted]:
            lines.extend(_quote_with_carry(note, rows.get(note["id"], ())))
        if waiting[quoted:]:
            lines.append(_named_line(root, waiting[quoted:]))
    lines.append("If a note changes this stage's work, do that work first and run this stage's checks again; then give "
                 "its row and complete. If it does not, add the row and run this same command again; nothing else needs "
                 "to run again.")
    return "\n".join(lines)


def unreadable(error: NoteError, result_path: str | Path) -> str:
    """The refusal when the notes cannot be read: the result is never judged against an empty list."""
    return (f"{error}, so ShipLoop cannot tell which owner notes this result must account for: make it readable, then "
            f"run this again (the result file {result_path} needs no change for this).")


def arrived(root: str | Path, result_path: str | Path, late: Sequence[Mapping[str, Any]]) -> str:
    """The refusal of a handoff completion when a note arrived between its two reads of the notes."""
    folder = Path(root) / DIR
    ids = [note["id"] for note in late]
    one = len(ids) == 1
    return (f"owner {'note' if one else 'notes'} {_ids(ids)} arrived while this handoff was being completed and "
            f"{'is' if one else 'are'} not accounted for: read "
            + (str(folder / (ids[0] + ".md")) if one else f"each in {folder}/")
            + f", add {'its row' if one else 'their rows'} to \"notes\" in {result_path}, then run this again.\n"
            + "\n".join(line for note in late for line in quote(note)))


# ---------------------------------------------------------------------------------------------------------- the end


def item_fate(state: Mapping[str, Any], item: str) -> str:
    """What became of a work item a row names, from the run's own record: completed, still queued, or no longer in the
    queue (work that was scheduled is not shown as work that was done)."""
    if item in (state.get("completed_work_items") or ()):
        return "completed"
    if item in [str(row.get("id")) for row in state.get("work_items") or () if isinstance(row, Mapping)]:
        return "still queued"
    return "no longer in the queue"


def _ending(state: Mapping[str, Any], rows: Sequence[Mapping[str, Any]]) -> str:
    """How a note ended, in a few words: its latest row, or that no stage accounted for it."""
    where = standing(rows)
    if where == "open":
        return "not accounted for: no stage's result has a row for it"
    last = rows[-1]
    if where == "carried":
        return f"carried by {_where(last)}, not settled: {_cut(last['detail'])}"
    item = f" (item {last['item']}, {item_fate(state, last['item'])})" if last.get("item") else ""
    return f"{last['did']} at {_where(last)}{item}: {_cut(last['detail'])}"


def done_lines(root: str | Path, state: Mapping[str, Any]) -> list[str]:
    """The done packet's short summary (design 2.7): each note's id and how it ended, and that the host's last message
    says what happened to each; the report holds the words and every row.  Nothing when no note was written."""
    found = notes(root)
    if not found:
        return []
    rows = ledger(state)
    count = f"{len(found)} owner note" + ("" if len(found) == 1 else "s")
    return [(f"Your notes: {count}. In your last message tell the user what happened to each; the report's section "
             "\"Your notes\" has each note's words and every row:"),
            *(f"- {note['id']}: {_ending(state, rows.get(note['id'], ()))}" for note in found)]


def open_lines(root: str | Path, state: Mapping[str, Any]) -> list[str]:
    """A halted run's notes that no stage settled, as not accounted for; nothing when every note is settled."""
    rows = ledger(state)
    left = [note["id"] for note in notes(root) if standing(rows.get(note["id"], ())) != "settled"]
    if not left:
        return []
    one = len(left) == 1
    return [(f"Owner {'note' if one else 'notes'} {_ids(left)} {'is' if one else 'are'} not accounted for: the run "
             f"stopped before a stage settled {'it' if one else 'them'} ({Path(root) / DIR}/; the report lists "
             f"{'it' if one else 'them'}).")]


def html_section(root: str | Path | None, state: Mapping[str, Any]) -> list[str]:
    """The report's section "Your notes": each note's words and every row (step, stage, what it did, the detail, and
    for a row that names an item what became of it).  Nothing when no note was written.  Every value is escaped."""
    found = notes(root) if root is not None else []
    rows = ledger(state)
    on_file = {note["id"] for note in found}
    listed = [*found, *({"id": note_id, "written_at": "", "text": None, "file": f"{DIR}/{note_id}.md"}
                        for note_id in sorted((key for key in rows if key not in on_file and NOTE_ID.fullmatch(key)),
                                              key=_number))]
    if not listed:
        return []
    out = ["<h2>Your notes</h2>",
           ("<p>What you wrote to the run while it ran, and what each stage's result said it did with it. ShipLoop "
            "checks that each note has a row; it does not check that the work does what the row says.</p>")]
    for note in listed:
        history = rows.get(note["id"], [])
        when = f", written {note['written_at']}" if note["written_at"] else ""
        out.append(f"<h3>{html.escape(note['id'])}{html.escape(when)}: {html.escape(standing(history))}</h3>")
        out.append(f"<pre>{html.escape(note['text'])}</pre>" if note["text"] is not None else
                   f"<p>Its file ({html.escape(note['file'])}) cannot be read now.</p>")
        if not history:
            out.append("<p>Not accounted for: no stage's result has a row for it.</p>")
            continue
        out.append("<table><thead><tr><th>Step</th><th>Stage</th><th>Work item</th><th>Did</th><th>Detail</th>"
                   "<th>Item</th></tr></thead><tbody>")
        for row in history:
            item = (f"{row['item']} ({item_fate(state, row['item'])})" if row.get("item") else "—")
            out.append("<tr>" + "".join(f"<td>{html.escape(str(value))}</td>" for value in (
                row["step"], row["stage"], row.get("workitem") or "—", row["did"], row["detail"], item)) + "</tr>")
        out.append("</tbody></table>")
        if standing(history) == "carried":
            out.append(f"<p>Not settled: carried by {html.escape(_where(history[-1]))}, for "
                       f"{html.escape(owed_by(history))}.</p>")
    return out


def review_lines(root: str | Path, seed: Mapping[str, Any]) -> list[str]:
    """What an Improve review of a result with ``notes`` rows is told: each note's file and its row, and that the
    review's result keeps a row for exactly those notes."""
    rows = [row for row in seed.get(FIELD) or () if isinstance(row, Mapping) and isinstance(row.get("note"), str)]
    if seed.get("outcome") != "done" or not rows:
        return []
    folder = Path(root) / DIR
    return ["## Owner notes this result accounts for",
            ("The reviewed result has a row in \"notes\" for each owner note below. Read each note and check that the "
             "work does what its row says; a row the work does not bear out is corrected in final_result. "
             "final_result keeps one row for exactly these notes (ShipLoop refuses a missing or added one; a note that "
             "arrived during this review is the next stage's):"),
            *(f"- {row['note']} ({folder / (row['note'] + '.md')}): {row.get('did', '')}: {_cut(row.get('detail', ''))}"
              + (f" (item {row['item']})" if row.get("item") else "") for row in rows), ""]


def import_faults(seed: Mapping[str, Any], effective: Any, state: Mapping[str, Any], stage: str,
                  workitem: str | None, *, folder: Path) -> list[dict[str, Any]]:
    """What keeps a review's result from taking effect for the notes (design 2.4): a done result that takes effect holds
    rows for exactly the notes the producer's parked result held rows for, each a valid row; any other outcome holds
    none and leaves the notes owed."""
    if not isinstance(effective, Mapping) or effective.get("outcome") != "done":
        return []
    parked = [row["note"] for row in seed.get(FIELD) or () if isinstance(row, Mapping) and isinstance(row.get("note"), str)] \
        if seed.get("outcome") == "done" else []
    if not parked and not effective.get(FIELD):
        return []
    pretend = [{"id": note_id, "written_at": "", "text": "", "file": f"{DIR}/{note_id}.md"} for note_id in parked]
    # The parked notes are the ones owed here, whatever the folder now holds: no note that arrived during the review
    # is taken in.  The ledger is left out because these notes were open when the producer's result was admitted.
    found = faults(pretend, {**state, "history": [], "accepted": {}}, stage, workitem, effective, folder=folder)
    for fault in found:
        if fault["kind"] == "missing":
            fault["text"] = f"{fault['note']} has no row, though the reviewed result had one: keep a row for it"
        elif fault["kind"] == "extra" and fault["note"] and fault["note"] not in parked:
            fault["text"] = (f"{fault['note']} has a row the reviewed result did not have: a note that arrived during "
                             "the review is the next stage's; remove the row")
    return found


# ---------------------------------------------------------------------------------------------------------- CLI


def main(argv: Sequence[str] | None = None, *, trace_record: dict[str, Any] | None = None) -> int:
    """``shiploop note``: the owner writes one note to a current run; never takes the run lock or prints a packet."""
    import shiploop_navigator as navigator
    import shiploop_trace as trace

    parser = argparse.ArgumentParser(prog="shiploop note",
                                     description="leave a note that the run's next done result must account for")
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
    print(f"Owner note {note['id']} written: {root / note['file']}.")
    # The state again, after the write: a run that ended in between never reads the note (design 2.4).
    now = trace.current_state(root) or state
    status = now.get("status")
    if status in ("done", "halted"):
        print(f"ShipLoop note: the run ended ({status}) while {note['id']} was being written, so no stage read it and "
              "none will. Start a new run on this project with its words.", file=sys.stderr)
        return 2
    stage, action, item = trace._cursor(now)
    where = f"{(item + ' ') if item else ''}{stage}"
    who = f"{note['id']} is accounted for by"
    if status == "blocked":
        wait = navigator.awaiting(now)
        asked = navigator._awaiting_text(wait[1]) if wait else "the recorded question"
        flag = "--answer" if not wait or wait[1].get("kind") == "answer" else "--observed"
        print(f"The run is blocked on: {asked} Reply with `resume {flag}`; {who} the done result of {where} after the "
              "resume.")
    elif status == "paused":
        print(f"The run is paused at {where}; {who} its done result after `resume`.")
    elif now.get("active_improve"):
        print(f"An Improve stage is reviewing the {now['active_improve'].get('stage')} result; {who} the done result of "
              "the next stage after it.")
    else:
        print(f"The run is at {where} (action {(action or {}).get('id')}); {who} its done result, which ShipLoop checks "
              "for a row when it is next checked or completed (a result already being read leaves it to the next "
              "stage's).")
    return 0
