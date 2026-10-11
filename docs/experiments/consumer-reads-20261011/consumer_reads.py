#!/usr/bin/env python3
"""Which ShipLoop artifacts did the model actually open, and at which stage?  Read-only over saved E2E runs.

    python3 docs/experiments/consumer-reads-20261011/consumer_reads.py <run output> [<run output> ...] [--json OUT]

Step 0 of docs/shiploop-consumer-contract-plan-2026-10-11.md.  For each run folder it reads events.jsonl (Claude's
stream-json; other hosts' translated streams carry commands too, but are reported as such and not merged with Claude),
follows the stage from the most recent "ShipLoop navigator | <stage> | revision N" header a tool result showed, and
classifies every file a tool call names into an artifact family:

    read   a Read tool call; a Bash command that runs a content-showing command (cat, sed, head, grep, python, ...) and
           names the path without writing it (a path only named by `git add`, `ls` or `test -f` is not a read)
    write  a Write or Edit tool call; a Bash command that names the path after > or >> or tee, or edits it with sed -i

What is NOT measured: whether the model used what it read (a citation of an ID is a separate question), reads by a
subagent whose tool calls are not in the main stream, and reads of a directory by a recursive grep (counted once as
"home dir", not per file).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

HEADER = re.compile(r"ShipLoop navigator \| (?P<stage>[\w-]+) \| revision \d+")
FAMILIES = [  # (family, pattern on a path); first match wins
    ("feature spec.md", re.compile(r"docs/shiploop/features/[^/\s'\"]+/spec\.md")),
    ("feature plan.md", re.compile(r"docs/shiploop/features/[^/\s'\"]+/plan\.md")),
    ("feature test-spec.md", re.compile(r"docs/shiploop/features/[^/\s'\"]+/test-spec\.md")),
    ("feature system-tests.md", re.compile(r"docs/shiploop/features/[^/\s'\"]+/system-tests\.md")),
    ("feature release-plan.md", re.compile(r"docs/shiploop/features/[^/\s'\"]+/release-plan\.md")),
    ("feature outcome.md", re.compile(r"docs/shiploop/features/[^/\s'\"]+/outcome\.md")),
    ("features/README.md", re.compile(r"docs/shiploop/features/README\.md")),
    ("spec.md", re.compile(r"docs/shiploop/spec\.md")),
    ("environment.md", re.compile(r"docs/shiploop/environment\.md")),
    ("architecture.md", re.compile(r"docs/shiploop/architecture\.md")),
    ("test-strategy.md", re.compile(r"docs/shiploop/test-strategy\.md")),
    ("home README.md", re.compile(r"docs/shiploop/README\.md")),
    ("SHIPLOOP.md", re.compile(r"(?<![\w/.-])(?:[^\s'\"]*/)?SHIPLOOP\.md")),
    ("home dir", re.compile(r"docs/shiploop/?(?=[\s'\"]|$)")),
    ("run state.md", re.compile(r"/run/state\.md")),
    ("run results/*.md", re.compile(r"/run/results/[^\s'\"]+")),
    ("run packets/*.md", re.compile(r"/run/packets/[^\s'\"]+")),
    ("run context-index.md", re.compile(r"context-index\.md")),
    ("run reference.md", re.compile(r"/run/reference\.md")),
    ("run notes/", re.compile(r"/run/notes/")),
    ("progress/report html", re.compile(r"(?:progress|report)\.html")),
]
WRITE_BASH = re.compile(r"(?:>>?|\btee\b(?:\s+-a)?)\s*[\"']?(?P<path>[^\s\"'<>|;&]+)")
SED_INPLACE = re.compile(r"\bsed\s+-i[^\n;|&]*?(?P<path>[^\s\"']+\.md)")
# A Bash command counts as a read only when it runs a command that shows file content; a path named only in `git add`,
# `ls`, `test -f` or a commit message is not a read.
READ_VERB = re.compile(r"(?<![\w-])(?:cat|sed|head|tail|grep|rg|awk|less|more|wc|diff|jq|nl|python3?|node)(?![\w-])")


def classify(text: str) -> list[str]:
    found = []
    for family, pattern in FAMILIES:
        if pattern.search(text):
            found.append(family)
    return found


def tool_text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(part.get("text", "") for part in content if isinstance(part, dict))
    return ""


def one_run(out: Path) -> dict:
    events = out / "events.jsonl"
    if not events.is_file():
        return {"run": out.name, "error": "no events.jsonl"}
    stage = "(before first packet)"
    reads: dict[str, Counter] = defaultdict(Counter)
    writes: dict[str, Counter] = defaultdict(Counter)
    calls = 0
    host = None
    for line in events.open(encoding="utf-8", errors="replace"):
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if event.get("type") == "system" and event.get("subtype") == "init":
            host = "claude"
        message = event.get("message") if isinstance(event.get("message"), dict) else {}
        for part in message.get("content") or []:
            if not isinstance(part, dict):
                continue
            if part.get("type") == "tool_result":
                headers = HEADER.findall(tool_text(part.get("content")))
                if headers:
                    stage = headers[-1]
                continue
            if part.get("type") != "tool_use":
                continue
            calls += 1
            name, data = part.get("name"), part.get("input") or {}
            if name == "Read":
                for family in classify(str(data.get("file_path", ""))):
                    reads[family][stage] += 1
            elif name in ("Write", "Edit", "MultiEdit", "NotebookEdit"):
                for family in classify(str(data.get("file_path", ""))):
                    writes[family][stage] += 1
            elif name == "Bash":
                command = str(data.get("command", ""))
                written = {m.group("path") for m in WRITE_BASH.finditer(command)}
                written |= {m.group("path") for m in SED_INPLACE.finditer(command)}
                write_families = {f for path in written for f in classify(path)}
                for family in write_families:
                    writes[family][stage] += 1
                if READ_VERB.search(command):
                    for family in classify(command):
                        if family not in write_families:
                            reads[family][stage] += 1
    return {"run": out.name, "host": host or "not claude-shaped", "tool_calls": calls,
            "reads": {f: dict(c) for f, c in sorted(reads.items())},
            "writes": {f: dict(c) for f, c in sorted(writes.items())}}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("runs", nargs="+", type=Path)
    parser.add_argument("--json", type=Path)
    args = parser.parse_args()
    rows = [one_run(run) for run in args.runs]
    families = [f for f, _ in FAMILIES]
    total_reads, total_writes, runs_reading = Counter(), Counter(), Counter()
    for row in rows:
        for family, by_stage in (row.get("reads") or {}).items():
            total_reads[family] += sum(by_stage.values())
            runs_reading[family] += 1
        for family, by_stage in (row.get("writes") or {}).items():
            total_writes[family] += sum(by_stage.values())
    print(f"{len(rows)} run(s)")
    print(f"{'artifact':28} {'reads':>6} {'runs reading':>13} {'writes':>7}")
    for family in families:
        if total_reads[family] or total_writes[family]:
            print(f"{family:28} {total_reads[family]:>6} {runs_reading[family]:>13} {total_writes[family]:>7}")
    unseen = [f for f in families if not total_reads[f] and not total_writes[f]]
    if unseen:
        print("never opened or written:", ", ".join(unseen))
    if args.json:
        args.json.write_text(json.dumps({"runs": rows, "families": families}, indent=1, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
