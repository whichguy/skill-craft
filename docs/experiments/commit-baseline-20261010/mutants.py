#!/usr/bin/env python3
"""Mutation check of the packets and commits counters: apply one change at a time to the implementation, run
test/shiploop-e2e-commit-counters.test.py, expect it to fail, restore the file.

    python3 docs/experiments/commit-baseline-20261010/mutants.py [--out docs/experiments/commit-baseline-20261010/mutants-result.json]

A mutant is a literal replacement of one piece of counters.py, metrics.py or run.py; "killed" means the suite failed with it in
place. The files are restored after every mutant (also on an error) and the working tree is unchanged when the script ends. The
list is the committed record of what the tests were shown to catch; a survivor is a test still to write. Takes about ten
minutes (the suite runs in about fifteen seconds, once per mutant).
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
COUNTERS = ROOT / "test/shiploop_e2e/counters.py"
METRICS = ROOT / "test/shiploop_e2e/metrics.py"
RUN = ROOT / "test/shiploop_e2e/run.py"
SUITE = ROOT / "test/shiploop-e2e-commit-counters.test.py"

MUTANTS = [
    # packets: what makes a head whole
    ("narrative block not followed to its end", COUNTERS, 'if re.match(r"\\n*" + re.escape(NARRATIVE_BEGIN), reply[cut:]):',
     'if False and re.match(r"\\n*" + re.escape(NARRATIVE_BEGIN), reply[cut:]):'),
    ("callback line not checked", COUNTERS, 'if any(not line.rstrip().endswith(".md") for line in CALLBACK_LINE.findall(head)):', "if False:"),
    ("keepalive line not checked", COUNTERS, 'if any(not re.search(r"\\bdir=\\S+$", line.rstrip()) for line in KEEPALIVE_LINE.findall(head)):', "if False:"),
    ("closing line not required", COUNTERS, "    end = reply.find(STATUS_END)\n    if end < 0:\n        return None, NOT_WHOLE_BEFORE_CLOSING",
     "    end = reply.find(STATUS_END)\n    if end < 0:\n        end = len(reply) - len(STATUS_END)"),
    ("a head cut inside the narrative gives the wrong reason", COUNTERS, "return None, NOT_WHOLE_IN_NARRATIVE", "return None, NOT_WHOLE_BEFORE_CLOSING"),
    ("a cut by column gives the wrong reason", COUNTERS, "        return None, NOT_WHOLE_SHORTENED\n    if any(not re.search",
     "        return None, NOT_WHOLE_BEFORE_CLOSING\n    if any(not re.search"),
    ("a head with no Full packet line is given to the first file", COUNTERS, 'stem = Path(found.group("path")).stem if found else None',
     'stem = Path(found.group("path")).stem if found else next(iter(files), None)'),
    # packets: which replies, which print, which unit
    ("calls that name a packet file are prints", COUNTERS, '        if reply["packet"]:\n            continue\n', ""),
    ("the last print counts", COUNTERS, 'printed.setdefault(stem, len(head.encode("utf-8")))', 'printed[stem] = len(head.encode("utf-8"))'),
    ("characters instead of bytes", COUNTERS, 'printed.setdefault(stem, len(head.encode("utf-8")))', "printed.setdefault(stem, len(head))"),
    # packets: the entries
    ("entries not in run order", COUNTERS, "for _revision, _stem, row in sorted(rows, key=lambda item: item[:2])", "for _revision, _stem, row in rows"),
    ("stage read from the first line only", COUNTERS, 'return (found.group("stage"), int(found.group("revision"))) if found else (None, 10 ** 9)',
     'return (found.group("stage"), int(found.group("revision"))) if found and path.read_text().startswith("ShipLoop navigator") else (None, 10 ** 9)'),
    ("an empty packets folder is null", COUNTERS, '    files = {path.stem: path for path in folder.glob("*.md") if path.is_file()}',
     '    files = {path.stem: path for path in folder.glob("*.md") if path.is_file()}\n    if not files:\n        return None, {"packets": "x"}'),
    ("the reason does not name the host", COUNTERS, 'hosts = ", ".join(runrecord.hosts_used(out)) or "host not recorded"', 'hosts = ""'),
    # ToolLog
    ("a repeated result is kept again", METRICS, "first = call_id not in self.answered  #", "first = True  #"),
    ("every reply is kept", METRICS, "if first and KEPT_REPLY.search(shown):", "if first:"),
    ("whether the call named a packet is lost", METRICS, '"packet": bool(call.get("packet"))', '"packet": False'),
    # commits: who made a commit
    ("improve told by the six-label shape", COUNTERS, 'if any(commit_id.startswith(sha) for sha in named["improve"]):', 'if "Review:" in message:'),
    ("the work item's reply ignored", COUNTERS, 'elif (any(commit_id.startswith(sha) for sha in named["item"]) or', "elif (False or"),
    ("the work item's subject ignored", COUNTERS, "subject.startswith((CHAIN_PREFIX, *items))", "subject.startswith((CHAIN_PREFIX,))"),
    ("any feat: subject is a work item", COUNTERS, 'return tuple(f"feat: {item[\'id\']} " for item in items',
     'return ("feat: ",) + tuple(f"feat: {item[\'id\']} " for item in items'),
    ("the knowledge subject loosened", COUNTERS, 'KNOWLEDGE_SUBJECT = re.compile(r"^docs\\(shiploop\\): record \\S+ knowledge (?:at|after) \\S+$")',
     'KNOWLEDGE_SUBJECT = re.compile(r"^docs\\(shiploop\\): record ")'),
    ("the empty baseline is not the script's", COUNTERS, "or subject in (BASELINE_SUBJECT, LEFTOVERS_SUBJECT)", "or subject in (LEFTOVERS_SUBJECT,)"),
    # commits: which commits
    ("the starting head ignored", COUNTERS, '*(["--not", start] if start else [])', ""),
    ("the starting head not checked", COUNTERS, "    found = _commit_id(work, head)\n    if found is None:", "    found = head\n    if False:"),
    ("the classes do not sum to counted", COUNTERS, '"counted": len(ran["commits"]), "start_head": start}',
     '"counted": len(ran["commits"]) - 1, "start_head": start}'),
    ("the author is not read", COUNTERS, 'author = next((line[len(b"author "):]', 'author = b"" and next((line[len(b"author "):]'),
    ("every script commit is marked knowledge", COUNTERS, '"knowledge": knowledge and kind == "script"}', '"knowledge": kind == "script"}'),
    # commits: citations and lessons
    ("no commit is ever from an earlier run", COUNTERS, 'row["cited_earlier_run"] += bool(start and any(', 'row["cited_earlier_run"] += bool(False and any('),
    ("a citation need not resolve", COUNTERS,
     'cited = [found for found in (_commit_id(work, match.group("id")) for match in LEARNED_FROM.finditer(commit["message"])) if found]',
     'cited = [match.group("id") for match in LEARNED_FROM.finditer(commit["message"])]'),
    ("a citation anywhere in a line", COUNTERS, 'LEARNED_FROM = re.compile(r"^Learned-from:', 'LEARNED_FROM = re.compile(r"Learned-from:'),
    ("a section does not end at the next label", COUNTERS, "if SECTION_END.match(following) or following.strip() in knowledge_home.LEARNING_SECTIONS:",
     "if following.strip() in knowledge_home.LEARNING_SECTIONS:"),
    ("a section does not end at the knowledge home's next section", COUNTERS,
     "if SECTION_END.match(following) or following.strip() in knowledge_home.LEARNING_SECTIONS:", "if SECTION_END.match(following):"),
    ("the Learned label is not read", COUNTERS, 'LESSON_LABEL = re.compile(rf"^(?:{KEY_LEARNINGS}|{LEARNED})', 'LESSON_LABEL = re.compile(rf"^(?:{KEY_LEARNINGS})'),
    # commits: what cannot be read
    ("events.jsonl not required", COUNTERS, "if not events.is_file() or not events.stat().st_size:", "if False:"),
    ("invocation.json not required", COUNTERS, '    if not isinstance(record, dict):\n        return None, "invocation.json cannot be read',
     '    if not isinstance(record, dict):\n        record = {}\n    if False:\n        return None, "invocation.json cannot be read'),
    # run.py
    ("run.py does not build the blocks", RUN, "    run_metrics.update(counters.safe_build(out, ledger, tool_log))\n", ""),
    ("run.py hands the builder an empty tool log", RUN, "counters.safe_build(out, ledger, tool_log)", "counters.safe_build(out, ledger, metrics.ToolLog())"),
    ("run.py hands the builder no run directory", RUN, "counters.safe_build(out, ledger, tool_log)", "counters.safe_build(out, None, tool_log)"),
    ("run.py does not fail open", RUN, "counters.safe_build(out, ledger, tool_log)", "counters.build(out, ledger, tool_log)"),
]


def run_suite() -> tuple[int, str]:
    done = subprocess.run([sys.executable, str(SUITE)], capture_output=True, text=True, cwd=str(ROOT), timeout=600,
                          env=dict(os.environ, SHIPLOOP_PROGRESS="off"))
    lines = done.stderr.strip().splitlines()
    return done.returncode, lines[-1] if lines else ""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--out", type=Path, default=HERE / "mutants-result.json")
    args = parser.parse_args()
    code, last = run_suite()
    if code:
        raise SystemExit(f"the suite is not green without a mutant: {last}")
    results = []
    for name, path, old, new in MUTANTS:
        text = path.read_text()
        if old not in text:
            results.append({"mutant": name, "file": str(path.relative_to(ROOT)), "killed": None, "suite": "pattern not found"})
            print("NOT APPLICABLE", name)
            continue
        path.write_text(text.replace(old, new, 1))
        try:
            code, last = run_suite()
        finally:
            path.write_text(text)
        results.append({"mutant": name, "file": str(path.relative_to(ROOT)), "killed": bool(code), "suite": last})
        print("killed  " if code else "SURVIVED", name, "|", last)
    document = {"suite": str(SUITE.relative_to(ROOT)), "mutants": len(results), "killed": sum(r["killed"] is True for r in results),
                "survived": [r["mutant"] for r in results if r["killed"] is False],
                "not_applicable": [r["mutant"] for r in results if r["killed"] is None], "results": results}
    args.out.write_text(json.dumps(document, indent=1) + "\n")
    print(f"{document['killed']} of {len(results)} killed; survivors {document['survived']}; not applicable {document['not_applicable']}")


if __name__ == "__main__":
    main()
