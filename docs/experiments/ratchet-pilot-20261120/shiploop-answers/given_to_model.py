#!/usr/bin/env python3
"""Whether an owner note's words reached the model, or only the commands' printed output.

Usage: ``given_to_model.py ROOT NAME [NAME ...] [--words TEXT]``.  For each delivery ``ROOT/NAME`` the words are TEXT,
else the first sentence of the delivery's own note N1: ``<run>/owner-notes/N1.md`` (its ``shiploop-state`` JSON block),
else the stand-in record ``ROOT/<NAME>-requester.json`` ``note.text``.  Texts are compared with their whitespace folded.

A Codex delivery's session records are ``NAME/home/.codex/sessions/**/rollout-*.jsonl``.  In them an ``event_msg``
line is what the host recorded (an ``item_completed`` ``CommandExecution`` holds what one command printed, in
``aggregated_output``), and a ``response_item`` line is what went into the model's context: a tool output given to it
(``custom_tool_call_output``, ``function_call_output``), another message given to it (``message`` of role user,
developer or system, ``additional_tools``), or its own (``message`` of role assistant, ``reasoning`` summaries, the
``custom_tool_call`` or ``function_call`` it wrote).  The model runs commands from its own scripts
(``custom_tool_call`` ``exec``), so a command's event carries no call id: it is paired with an output by position, as
the output of the one call open around it (that output found by its ``call_id``), else as the next tool output after it.

A Claude Code delivery has no Codex record; its ``NAME/events.jsonl`` is the host's stream-json, where each ``user``
event's ``message.content`` ``tool_result`` is the result given to the model and the same event's ``tool_use_result``
is the tool's own result (``stdout``, ``stderr``), paired by ``tool_use_id``.  Nothing is written anywhere; home paths
print as ``~``.
"""
from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path

HOME = os.path.expanduser("~")
STATE_BLOCK = re.compile(r"```shiploop-state\n(.*?)\n```", re.DOTALL)
SENTENCE = re.compile(r"(.+?[.!?])(?=\s|$)", re.DOTALL)
OWNER_NOTE = re.compile(r"owner note", re.IGNORECASE)
SKIP = {"encrypted_content", "signature", "id", "call_id", "internal_chat_message_metadata_passthrough"}
TOOL_OUTPUTS = ("custom_tool_call_output", "function_call_output", "local_shell_call_output")
OWN = ("custom_tool_call", "function_call", "local_shell_call", "reasoning")


def tilde(text: object) -> str:
    return str(text).replace(HOME, "~")


def fold(text: str) -> str:
    return " ".join(text.split())


def strings(value: object, key: str = "") -> list[str]:
    """Every text a record holds, in order, without its ids, signatures and encrypted content."""
    if key in SKIP:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [text for name, item in value.items() for text in strings(item, name)]
    if isinstance(value, list):
        return [text for item in value for text in strings(item)]
    return []


def around(text: str, words: str) -> str:
    """160 characters of ``text`` (folded) centred on the first occurrence of ``words``."""
    folded = fold(text)
    at = folded.find(words)
    start = max(0, at + len(words) // 2 - 80)
    return tilde(folded[start:start + 160])


def load_lines(path: Path) -> list[dict]:
    rows = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def run_dir(out: Path) -> Path | None:
    """The ShipLoop run the harness names (result.json, shiploop-run.json), else the only one there."""
    for record in ("result.json", "shiploop-run.json"):
        try:
            data = json.loads((out / record).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        named = (data.get("shiploop") or {}).get("run_dir") if record == "result.json" else data.get("run_dir")
        if named and Path(named).is_dir():
            return Path(named)
    found = [path.parent for path in out.glob(".shiploop-runs/*/run/state.md")]
    return found[0] if len(found) == 1 else None


def note_words(out: Path) -> tuple[str | None, str]:
    """(the first sentence of the delivery's note N1, where it was read), or (None, why not)."""
    run = run_dir(out)
    if run is not None:
        try:
            block = STATE_BLOCK.search((run / "owner-notes" / "N1.md").read_text(encoding="utf-8"))
            record = json.loads(block.group(1)) if block else None
        except (OSError, json.JSONDecodeError):
            record = None
        if isinstance(record, dict) and record.get("id") == "N1" and isinstance(record.get("text"), str):
            return first_sentence(record["text"]), tilde(run / "owner-notes" / "N1.md")
    try:
        text = (json.loads(out.with_name(out.name + "-requester.json").read_text(encoding="utf-8")).get("note")
                or {}).get("text")
    except (OSError, json.JSONDecodeError, AttributeError):
        text = None
    if isinstance(text, str) and text.strip():
        return first_sentence(text), tilde(out.with_name(out.name + "-requester.json")) + " note.text"
    return None, "no readable owner-notes/N1.md and no note.text in the stand-in record"


def first_sentence(text: str) -> str:
    found = SENTENCE.match(text.strip())
    return fold(found.group(1) if found else text)


def holds(texts: list[str], words: str) -> bool:
    return words in fold(" ".join(texts))


def kind_of(payload: dict) -> str:
    item = payload.get("item") if isinstance(payload.get("item"), dict) else None
    return payload.get("type", "?") + (f"/{item.get('type')}" if item else "")


def codex(path: Path, words: str, ident: str) -> tuple[int, int, bool]:
    """Print items 1 to 3 for one rollout; return (commands that printed the words, tool outputs given to the model
    that hold them, whether anything given to the model holds them)."""
    rows = load_lines(path)
    naming = re.compile(r"\b" + re.escape(ident) + r"\b")
    events, given_out, given_other, own = [], [], [], []
    open_calls: list[str] = []
    outputs = {}      # call_id -> (index, payload) of the tool output
    for index, row in enumerate(rows):
        payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
        kind = payload.get("type", "")
        if row.get("type") == "response_item" and kind in TOOL_OUTPUTS and payload.get("call_id"):
            outputs.setdefault(payload["call_id"], (index, payload))
    for index, row in enumerate(rows):
        payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
        kind = payload.get("type", "")
        if row.get("type") == "response_item":
            if kind in OWN[:3] and payload.get("call_id"):
                open_calls.append(payload["call_id"])
            if kind in TOOL_OUTPUTS and payload.get("call_id") in open_calls:
                open_calls.remove(payload["call_id"])
            texts = strings(payload)
            if not holds(texts, words):
                continue
            if kind in TOOL_OUTPUTS:
                given_out.append((index, kind, texts))
            elif kind in OWN or payload.get("role") == "assistant":
                own.append((index, kind + (f"/{payload.get('role')}" if payload.get("role") else ""), texts))
            else:
                given_other.append((index, kind + (f"/{payload.get('role')}" if payload.get("role") else ""), texts))
        elif row.get("type") == "event_msg":
            item = payload.get("item") if isinstance(payload.get("item"), dict) else {}
            command = item.get("type") == "CommandExecution"
            texts = [str(item.get("aggregated_output") or "")] if command else strings(payload)
            if holds(texts, words) or (command and holds(strings(item), words)):
                events.append((index, kind_of(payload), command and holds(texts, words), texts, list(open_calls)))
    print(f"   rollout {tilde(path)} ({len(rows)} lines)")
    printed = [event for event in events if event[2]]
    print(f"   1. event_msg lines holding the words: {len(events)} ({len(printed)} are a command's printed output)")
    for _index, kind, is_output, texts, _open in events:
        size = len(" ".join(texts))
        print(f"      {kind}{'' if is_output else ' (not in its output)'}, output {size} chars: \"{around(' '.join(texts), words)}\"")
    print(f"   2. response_item lines holding the words: {len(given_out) + len(given_other) + len(own)}: tool outputs given "
          f"to the model {len(given_out)}, other messages given to it {len(given_other)}, the model's own {len(own)}")
    for label, found in (("given (tool output)", given_out), ("given (other)", given_other), ("own", own)):
        for _index, kind, texts in found[:3]:
            print(f"      {label} {kind}, {len(' '.join(texts))} chars: \"{around(' '.join(texts), words)}\"")
    print("   3. for each command that printed the words, the output the model was given for it:")
    for index, _kind, _is_output, texts, open_now in printed:
        later = next((at for at, _kind, _texts in given_out if at > index), None)
        where = (f"; the first later tool output that holds the words is line {later}" if later is not None
                 else "; no later tool output holds the words")
        if len(open_now) == 1 and open_now[0] in outputs:
            at, payload = outputs[open_now[0]]
            how = f"by position: inside call {open_now[0][:13]}, whose output is found by call_id"
        else:
            nxt = next(((at, row["payload"]) for at, row in enumerate(rows) if at > index and row.get("type") ==
                        "response_item" and (row.get("payload") or {}).get("type") in TOOL_OUTPUTS), None)
            at, payload = nxt if nxt else (None, None)
            how = f"by position: the next tool output ({len(open_now)} calls open around the command)"
        if payload is None:
            print(f"      line {index}: no tool output after it ({how}){where}")
            continue
        given = strings(payload.get("output"))
        joined = " ".join(given)
        print(f"      line {index} ({len(' '.join(texts))} chars printed) -> line {at} {payload.get('type')} "
              f"({len(joined)} chars given), {how}: words {holds(given, words)}, {ident} "
              f"{bool(naming.search(joined))}, \"owner note\" {bool(OWNER_NOTE.search(joined))}{where}")
    return len(printed), len(given_out), bool(given_out or given_other)


def claude(events_path: Path, words: str, ident: str) -> tuple[int, int, bool]:
    """The same counts from a Claude Code stream-json: tool results given to the model, their raw tool results, the
    other text given to it and its own."""
    rows = load_lines(events_path)
    naming = re.compile(r"\b" + re.escape(ident) + r"\b")
    printed, given, other, own = [], [], [], []
    for index, row in enumerate(rows):
        message = row.get("message") if isinstance(row.get("message"), dict) else {}
        blocks = message.get("content") if isinstance(message.get("content"), list) else []
        if row.get("type") == "user":
            raw = row.get("tool_use_result")
            raw_texts = strings(raw) if isinstance(raw, (dict, str)) else []
            for block in blocks:
                texts = strings(block.get("content")) if block.get("type") == "tool_result" else strings(block)
                if block.get("type") == "tool_result":
                    if holds(raw_texts, words):
                        printed.append((index, raw_texts, texts, block.get("tool_use_id")))
                    if holds(texts, words):
                        given.append((index, "tool_result", texts))
                elif holds(texts, words):
                    other.append((index, f"user/{block.get('type')}", texts))
        elif row.get("type") == "assistant":
            for block in blocks:
                if holds(strings(block), words):
                    own.append((index, f"assistant/{block.get('type')}", strings(block)))
    print(f"   no Codex session record; read {tilde(events_path)} (Claude Code stream-json, {len(rows)} lines)")
    print(f"   1. tool results whose raw result (tool_use_result) holds the words: {len(printed)}")
    for _index, raw_texts, _texts, _ident in printed:
        print(f"      raw result, {len(' '.join(raw_texts))} chars: \"{around(' '.join(raw_texts), words)}\"")
    print(f"   2. given to the model: tool results {len(given)}, other user text {len(other)}; the model's own: "
          f"{len(own)}")
    for label, found in (("given (tool result)", given), ("given (other)", other), ("own", own)):
        for _index, kind, texts in found[:3]:
            print(f"      {label} {kind}, {len(' '.join(texts))} chars: \"{around(' '.join(texts), words)}\"")
    print("   3. for each raw result that holds the words, the tool result given (same event, by tool_use_id):")
    for index, raw_texts, texts, tool_id in printed:
        joined = " ".join(texts)
        print(f"      line {index} {str(tool_id)[:16]} ({len(' '.join(raw_texts))} chars raw -> {len(joined)} chars "
              f"given): words {holds(texts, words)}, {ident} {bool(naming.search(joined))}, \"owner note\" "
              f"{bool(OWNER_NOTE.search(joined))}")
    return len(printed), len(given), bool(given or other)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("root", type=Path)
    parser.add_argument("names", nargs="+")
    parser.add_argument("--words")
    args = parser.parse_args()
    summary = []
    for name in args.names:
        out = args.root / name
        print(f"== {name}")
        if args.words:
            words, source = fold(args.words), "--words"
        else:
            words, source = note_words(out)
        if words is None:
            print(f"   not read: {source}")
            summary.append(f"{name}: not read ({source})")
            continue
        print(f"   words: \"{words}\" (from {source})")
        rollouts = sorted((out / "home" / ".codex" / "sessions").glob("**/rollout-*.jsonl"))
        if rollouts:
            counts = [codex(path, words, "N1") for path in rollouts]
        elif (out / "events.jsonl").is_file():
            counts = [claude(out / "events.jsonl", words, "N1")]
        else:
            print("   no Codex session record; not read: no events.jsonl in the delivery folder")
            summary.append(f"{name}: not read (no Codex session record and no events.jsonl)")
            continue
        printed, outputs, reached = (sum(count[0] for count in counts), sum(count[1] for count in counts),
                                     any(count[2] for count in counts))
        summary.append(f"{name}: printed by {printed} commands; given to the model in {outputs} outputs; the model "
                       f"{'was' if reached else 'was not'} given the note's words")
    print("== summary")
    for line in summary:
        print("   " + line)


if __name__ == "__main__":
    main()
