"""Parse one reader's reply of the M1 replay into labels keyed by row id.

Usage: parse_reader.py NAME ENVELOPE   (NAME: sol-a, sol-b or grok; ENVELOPE: the reader's raw reply, an ``ask.sh --json``
envelope or plain text).  Writes readers/NAME.parsed.json = {row id: {class, alt, reason}}.  Exit 1, with the reason, when the
reply is not one JSON array holding every r-id of prompts/NAME.map.json exactly once with valid class names.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CLASSES = json.loads((HERE.parent / "follow-on-peek-20261031" / "classification.json").read_text(encoding="utf-8"))["classes"]


def reply_text(raw: str) -> str:
    try:
        envelope = json.loads(raw)
    except ValueError:
        return raw
    if isinstance(envelope, dict) and isinstance(envelope.get("text"), str):
        return envelope["text"]
    return raw


def parse(name: str, raw: str) -> dict:
    text = reply_text(raw)
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())
    start, end = text.find("["), text.rfind("]")
    if start < 0 or end < start:
        raise ValueError("no JSON array in the reply")
    items = json.loads(text[start:end + 1])
    mapping = json.loads((HERE / "prompts" / f"{name}.map.json").read_text(encoding="utf-8"))
    out, problems = {}, []
    for item in items:
        rid = item.get("id") if isinstance(item, dict) else None
        if rid not in mapping:
            problems.append(f"unknown id {rid!r}")
            continue
        row = mapping[rid]
        if row in out:
            problems.append(f"duplicate id {rid}")
            continue
        if item.get("class") not in CLASSES:
            problems.append(f"{rid}: class {item.get('class')!r} is not one of the seven")
            continue
        alt = item.get("alt")
        if alt is not None and alt not in CLASSES:
            problems.append(f"{rid}: alt {alt!r} is not one of the seven")
            continue
        out[row] = {"class": item["class"], "alt": alt, "reason": str(item.get("reason", ""))}
    missing = sorted(set(mapping.values()) - set(out))
    if missing:
        problems.append("missing rows: " + ", ".join(missing))
    if problems:
        raise ValueError("; ".join(problems))
    return out


def main() -> int:
    name, path = sys.argv[1], sys.argv[2]
    try:
        parsed = parse(name, Path(path).read_text(encoding="utf-8"))
    except ValueError as error:
        print(f"{name}: NOT PARSED: {error}")
        return 1
    (HERE / "readers" / f"{name}.parsed.json").write_text(json.dumps(parsed, indent=1, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    counts = {}
    for label in parsed.values():
        counts[label["class"]] = counts.get(label["class"], 0) + 1
    print(f"{name}: parsed {len(parsed)} rows; classes {dict(sorted(counts.items()))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
