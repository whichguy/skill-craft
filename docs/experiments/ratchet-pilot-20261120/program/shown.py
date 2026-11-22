#!/usr/bin/env python3
"""How much of the spec stage's text was a Codex session's model given? No model is called.

    python3 shown.py RUN [RUN ...]

Part V of the program of journal section 26. RUN is a ratchet.py run; RUN/packets/spec-1.txt is the whole text of
its first spec session, however it was given (run.json says: `deliver` is `prompt` or `command`). On Codex the model
runs commands from a script of its own and is given only what that script shows, so the host's own record of the
session (RUN/home/.codex/sessions/**/rollout-*.jsonl) is read, never the harness's events.

A non-blank line of the text counts as given when it stands, with its white space squeezed, in a tool output the
model was given. For a run whose text was in the prompt every line was given by construction, and the columns say
`prompt`. Printed for each run: the lines given, whether every line of the written question (the rules question,
ratchet.RULES_SPEC_SECTION) was, the tool calls of the first spec session, and whether the specification holds a
`## Rules and edge cases` section and how many entries it has.
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import ratchet


def squeeze(text):
    return re.sub(r"\s+", " ", text).strip()


def rows_of(path):
    for line in path.read_text(errors="replace").splitlines():
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if isinstance(row, dict):
            yield row


def first_session(run):
    """(squeezed text of every tool output the model was given, number of tool calls) for the run's first session."""
    files = sorted(Path(run).glob("home/.codex/sessions/**/rollout-*.jsonl"))
    if not files:
        return None, None
    given, calls = [], 0
    for row in rows_of(files[0]):
        payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
        kind = str(payload.get("type") or "")
        if kind.endswith("_call"):
            calls += 1
        if not kind.endswith("_output"):
            continue
        output = payload.get("output")
        parts = output if isinstance(output, list) else [{"text": output}]
        text = "".join(str(part.get("text") or "") for part in parts if isinstance(part, dict))
        # a script may print a command's output in its JSON form: read that form as plain text too
        plain = text.replace("\\n", "\n").replace('\\"', '"').replace("\\\\", "\\")
        given.append(text if plain == text else text + "\n" + plain)
    return squeeze("\n".join(given)), calls


def section_entries(run):
    spec = Path(run) / "work" / "ratchet" / "spec.md"
    if not spec.is_file():
        return None
    found = re.search(r"^## Rules and edge cases\s*$(.*?)(?=^## |\Z)", spec.read_text(), re.MULTILINE | re.DOTALL)
    if not found:
        return None
    return sum(1 for line in found.group(1).splitlines() if line.strip().startswith(("-", "*", "|")) and not set(line.strip()) <= set("|-: "))


def read(run):
    run = Path(run)
    record = json.loads((run / "run.json").read_text())
    packet = (run / "packets" / "spec-1.txt").read_text()
    lines = [squeeze(line) for line in packet.splitlines() if line.strip()]
    duty = [squeeze(line) for line in ratchet.RULES_SPEC_SECTION.splitlines() if line.strip()]
    given, calls = first_session(run)
    row = {"run": run.name, "deliver": record.get("deliver", "prompt"), "duty_at": record.get("duty_at", "standing"), "lines": len(lines),
           "tool_calls": calls, "section_entries": section_entries(run)}
    if row["deliver"] == "command" and given is not None:
        row["lines_given"] = sum(1 for line in lines if line in given)
        row["duty_lines_given"] = sum(1 for line in duty if line in given)
        row["duty_lines"] = len(duty)
    return row


def main(argv=None):
    runs = list(sys.argv[1:] if argv is None else argv)
    if not runs:
        raise SystemExit(__doc__)
    print("run | delivery | question at | lines of the text given | lines of the question given | tool calls | rules section (entries)")
    rows = [read(run) for run in runs]
    for row in rows:
        absent = "prompt" if row["deliver"] == "prompt" else "no record"
        shown = f"{row['lines_given']} of {row['lines']}" if "lines_given" in row else absent
        duty = f"{row['duty_lines_given']} of {row['duty_lines']}" if "duty_lines_given" in row else absent
        section = "none" if row["section_entries"] is None else f"yes ({row['section_entries']})"
        print(f"{row['run']} | {row['deliver']} | {row['duty_at']} | {shown} | {duty} | {row['tool_calls']} | {section}")
    print(json.dumps(rows))
    return 0


if __name__ == "__main__":
    sys.exit(main())
