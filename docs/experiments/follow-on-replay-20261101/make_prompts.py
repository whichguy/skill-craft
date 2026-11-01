"""Write the blind prompts for the second and third readers of the M1 replay (design section 7, M1).

A prompt holds the class definitions of ../follow-on-peek-20261031/classification.json verbatim, each row's full
``Open for the next run`` text and the request that run was given (numbered sentences).  It holds no label, note or
``arguable`` flag of the first reader, and no case or run name.  Rows are shuffled with a seeded generator and renamed r01..r32,
and requests are lettered in order of first appearance, so neither the frozen order nor the strata show.

Readers (fixed before any call): sol-a (file class order, seed 20261101), sol-b (class order reversed, seed 20261102; the
retest of sol-a) and grok (file class order, seed 20261103).  Each prompt has a map file from r-id to row id.
"""

from __future__ import annotations

import json
import os
import random
import string
from pathlib import Path

HERE = Path(__file__).resolve().parent
PEEK = HERE.parent / "follow-on-peek-20261031"
READERS = {"sol-a": (20261101, False), "sol-b": (20261102, True), "grok": (20261103, False)}

HEAD = """You are one of several independent readers. Your job is to classify short texts. Do not run commands, open files or use any tool: judge only what is written below.

CONTEXT
A coding harness called ShipLoop builds software for a written request, tests it and delivers it. At the end of a run it writes a short text under the heading "Open for the next run": what a later run should pick up. Each ROW below is one such text, with the request that run was given (as numbered sentences). Rows are unrelated; judge each on its own.

CLASSES (choose exactly one per row)
{classes}

FOR EACH ROW give
  "class": one of the seven class names above, exactly as written;
  "alt": another class that is also a reasonable reading of the same text, or null if you see none;
  "reason": one sentence of at most 25 words.

OUTPUT
Reply with one JSON array and nothing else, one object per row, in the order given, using the ids exactly as written:
[{{"id": "r01", "class": "...", "alt": null, "reason": "..."}}, ...]
"""


HOME = os.path.expanduser("~") + "/"


def redact(text: str) -> str:
    """The owner's home directory prefix is not sent to a reader; nothing else is changed."""
    return text.replace(HOME, "~/")


def build(name: str, seed: int, reverse: bool, data: dict, classes: dict) -> tuple[str, dict]:
    rows = sorted(data["rows"], key=lambda row: row["id"])
    random.Random(seed).shuffle(rows)
    order = list(classes)
    if reverse:
        order.reverse()
    class_lines = "\n".join(f"- {key}: {classes[key]}" for key in order)
    letters, lettered = {}, []
    for row in rows:
        if row["request"] not in letters:
            letters[row["request"]] = string.ascii_uppercase[len(letters)]
            lettered.append(row["request"])
    parts = [HEAD.format(classes=class_lines), "REQUESTS (each row names the request its run was given)"]
    for request in lettered:
        sentences = "\n".join(f"S{item['s']}: {redact(item['text'])}" for item in data["requests"][request])
        parts.append(f"### Request {letters[request]}\n{sentences}")
    parts.append("ROWS")
    mapping = {}
    for index, row in enumerate(rows, 1):
        rid = f"r{index:02d}"
        mapping[rid] = row["id"]
        parts.append(f"### {rid} (request {letters[row['request']]})\n{redact(row['text'])}")
    return "\n\n".join(parts) + "\n", mapping


def main() -> None:
    data = json.loads((HERE / "rows.json").read_text(encoding="utf-8"))
    classes = json.loads((PEEK / "classification.json").read_text(encoding="utf-8"))["classes"]
    for name, (seed, reverse) in READERS.items():
        text, mapping = build(name, seed, reverse, data, classes)
        (HERE / "prompts" / f"{name}.txt").write_text(text, encoding="utf-8")
        (HERE / "prompts" / f"{name}.map.json").write_text(json.dumps(mapping, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        print(f"{name}: {len(text)} bytes, {len(text.split())} words, {len(mapping)} rows")


if __name__ == "__main__":
    main()
