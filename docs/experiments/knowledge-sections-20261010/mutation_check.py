#!/usr/bin/env python3
"""Break the section code one way at a time and count the tests that go red (a test that cannot fail is not a test).

Repeat with:  PYTHONDONTWRITEBYTECODE=1 SHIPLOOP_PROGRESS=off python3 docs/experiments/knowledge-sections-20261010/mutation_check.py

Each row names a file, the exact text replaced, its replacement and the test selector run.  The file is restored after every row
(and on any error); the run refuses to start when the source files are not clean in Git.  Writes mutations.json beside this file.
Every row must turn its selector red.  In the foreground: the SectionsTests / SectionNoticeTests / SectionNoticeCloseTests rows take
about 2 s each, the real-CLI rows about 4 s each.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
KNOW = "skills/shiploop/scripts/shiploop_knowledge_home.py"
NAV = "skills/shiploop/scripts/shiploop_navigator.py"
K = "test/shiploop-knowledge.test.py"
TABLES = [K, "SectionsTests"]
NOTICE = [K, "SectionNoticeTests"]
CLOSE = [K, "SectionNoticeCloseTests"]
CLI = ["test/shiploop-callback-contract.test.py",
       "RefusalRouteTests.test_a_close_whose_files_have_no_named_sections_is_accepted_and_prints_one_counted_line_per_section",
       "RefusalRouteTests.test_a_close_whose_files_have_every_named_section_is_accepted_and_prints_no_notice",
       "RefusalRouteTests.test_a_stage_that_is_no_close_prints_no_notice_although_a_file_lacks_its_sections",
       "RefusalRouteTests.test_the_fix_a_notice_names_applied_to_its_file_silences_that_line_and_only_that_line"]
PACKET = ["test/shiploop-packet-completeness.test.py"]
ROWS = [
    # the headings as constants
    (KNOW, '    "spec.md": ("Requirements", "Non-functional requirements", "Retired"),', '    "spec.md": ("Requirements", "Retired"),', TABLES),
    (KNOW, '("Targets and runtimes", "Commands", "Access and accounts", "Platform facts")', '("Commands", "Targets and runtimes", "Access and accounts", "Platform facts")', TABLES),
    (KNOW, '("Stack", "Structure", "Conventions", "Interfaces and boundaries", "Decisions", "Superseded")', '("Stack", "Structure", "Conventions", "Interfaces and boundaries", "Decisions")', TABLES),
    (KNOW, '("Harnesses and suites", "Commands", "ID convention", "Real-boundary checks")', '("Harnesses and suites", "Commands", "ID convention", "Real boundary checks")', TABLES),
    (KNOW, '           "SECTIONS",\n', '', TABLES),
    (KNOW, "a '## Decisions' section of stable IDs", "a '## Decision log' section of stable IDs", TABLES),
    # the writer entries
    (KNOW, '    "research": ("environment.md",),\n', '', TABLES),
    (KNOW, '    "validate-existing": ("environment.md",),\n', '', TABLES),
    (KNOW, '    "implement": ("environment.md", ARCHITECTURE),', '    "implement": ("environment.md",),', TABLES),
    (KNOW, '    "implement": ("environment.md", ARCHITECTURE),', '    "implement": (ARCHITECTURE,),', TABLES),
    (KNOW, '    "test": ("environment.md",),\n', '', TABLES),
    (KNOW, '    "carry-forward": (ARCHITECTURE, "environment.md"),', '    "carry-forward": (ARCHITECTURE,),', TABLES),
    (KNOW, '    "carry-forward": (ARCHITECTURE, "environment.md"),', '    "carry-forward": ("environment.md", ARCHITECTURE),', TABLES),
    (KNOW, '    "system-test-author": ("{feature}/system-tests.md",),', '    "verify": (ARCHITECTURE,),\n    "system-test-author": ("{feature}/system-tests.md",),', TABLES),
    (KNOW, '    "research": ("environment.md",),', '    "research-notes": ("environment.md",),', TABLES),  # a stale key
    (KNOW, '    "carry-forward": (ARCHITECTURE, "environment.md"),', '    "carry-forward": (ARCHITECTURE, "environment.md"),\n    "validate": ("environment.md",),', TABLES),
    # the notice: where and when
    (KNOW, "    if stage not in CLOSES:\n        return []\n    repo = Path(str(state[\"repo\"]))\n    notices", "    repo = Path(str(state[\"repo\"]))\n    notices", NOTICE),
    (KNOW, "    if stage not in CLOSES:\n        return []\n    repo = Path(str(state[\"repo\"]))\n    notices", "    if stage not in STAGE_FILES:\n        return []\n    repo = Path(str(state[\"repo\"]))\n    notices", NOTICE),
    (KNOW, "        if not _filled(path):\n            continue\n        try:\n            lines", "        if not path.is_file():\n            continue\n        try:\n            lines", NOTICE),
    (KNOW, "        except OSError:\n            continue\n        outline, hint", "        except ValueError:\n            continue\n        outline, hint", NOTICE),
    (KNOW, "    for name, headings in SECTIONS.items():\n        path = repo / HOME / name\n        if not _filled", "    for name, headings in sorted(SECTIONS.items()):\n        path = repo / HOME / name\n        if not _filled", NOTICE),
    # the matching rules
    (KNOW, "if not title.lower().startswith(heading.lower()):", "if not title.startswith(heading):", NOTICE),
    (KNOW, "if not title.lower().startswith(heading.lower()):", "if heading.lower() not in title.lower():", NOTICE),
    (KNOW, "if not title.lower().startswith(heading.lower()):", "if title.lower() != heading.lower():", NOTICE),
    (KNOW, "if deeper <= level), len(lines))", "if deeper < level), len(lines))", NOTICE),
    (KNOW, "if deeper <= level), len(lines))", "if True), len(lines))", NOTICE),
    (KNOW, "if deeper <= level), len(lines))", "if deeper <= 2), len(lines))", NOTICE),
    (KNOW, "        if any(line.strip() for line in lines[index + 1:end]):", "        if lines[index + 1:end]:", NOTICE),
    (KNOW, '    return "empty" if found else "missing"', '    return "missing"', NOTICE),
    (KNOW, '_HEADING = re.compile(r"^(#{1,4})\\s+(.+?)\\s*$")', '_HEADING = re.compile(r"^(#{1,6})\\s+(.+?)\\s*$")', NOTICE),
    (KNOW, '_HEADING = re.compile(r"^(#{1,4})\\s+(.+?)\\s*$")', '_HEADING = re.compile(r"^(#{1,3})\\s+(.+?)\\s*$")', NOTICE),
    (KNOW, '_HEADING = re.compile(r"^(#{1,4})\\s+(.+?)\\s*$")', '_HEADING = re.compile(r"^(#{1,4})\\s*(.+?)\\s*$")', NOTICE),
    (KNOW, "        if heading and len(heading.group(1)) <= 3:\n            current", "        if heading:\n            current", NOTICE),
    (KNOW, "        if opening:\n            fence = opening.group(1)\n            continue", "        if False:\n            fence = opening.group(1)\n            continue", NOTICE),
    (KNOW, "            if opening and rest[0] == fence[0] and len(rest) >= len(fence) and rest == rest[0] * len(rest):", "            if opening:", NOTICE),
    (KNOW, "            if opening and rest[0] == fence[0] and len(rest) >= len(fence) and rest == rest[0] * len(rest):", "            if opening and len(rest) >= len(fence) and rest == rest[0] * len(rest):", NOTICE),
    (KNOW, '_FENCE = re.compile(r"^\\s{0,3}(`{3,}|~{3,})")', '_FENCE = re.compile(r"^\\s{0,3}(`{3,})")', NOTICE),
    # the wording a reader greps and acts on
    (KNOW, 'NOTICE_PREFIX = "ShipLoop knowledge notice: "', 'NOTICE_PREFIX = "ShipLoop knowledge: "', NOTICE),
    (KNOW, 'notices.append(NOTICE_PREFIX + str(path) + " has no \'"', 'notices.append(NOTICE_PREFIX + str(path.relative_to(repo)) + " has no \'"', NOTICE),
    (KNOW, 'notices.append(NOTICE_PREFIX + str(path) + " has no \'"', 'notices.append(NOTICE_PREFIX + "has no \'" + heading + "\' in " + str(path) + ", and none \'"', NOTICE),
    (KNOW, '+ "\' section (" + hint + "), or write \'none\' under it when nothing applies.")', '+ "\' section (" + hint + ").")', NOTICE),
    (KNOW, '+ "), or write \'none\' when nothing applies.")', '+ ").")', NOTICE),
    (KNOW, "' is empty; write under it (\"", "' has no text; write under it (\"", NOTICE),
    (KNOW, 'return name + " holds " + ARCHITECTURE_HOLDS', 'return name + " has the sections " + ", ".join(SECTIONS[name])', NOTICE),
    (KNOW, 'return name + " has the sections " + ", ".join(SECTIONS[name])', 'return name + " holds " + ARCHITECTURE_HOLDS', NOTICE),
    (KNOW, "    if name == ARCHITECTURE:\n        return", "    if False:\n        return", NOTICE),
    (KNOW, '            if found == "missing":', '            if found != "present":', NOTICE),
    # the navigator: printed once, on stdout, at the close, after the commit
    (NAV, "    for line in knowledge.section_notices(after, stages[-1]):\n        print(line)\n", "", CLOSE),
    (NAV, "    for line in knowledge.section_notices(after, stages[-1]):\n        print(line)\n", "", CLI),
    (NAV, "    for line in knowledge.section_notices(after, stages[-1]):\n        print(line)\n", "    for line in knowledge.section_notices(after, stages[-1]):\n        print(line, file=sys.stderr)\n", CLOSE),
    (NAV, "    for line in knowledge.section_notices(after, stages[-1]):\n        print(line)\n", "    for line in knowledge.section_notices(after, stages[0]):\n        print(line)\n", CLOSE),
    (NAV, "    for line in knowledge.section_notices(after, stages[-1]):\n        print(line)\n", "    for line in knowledge.section_notices(after, 'prepare'):\n        print(line)\n", CLOSE),
    (NAV, "    for line in knowledge.section_notices(after, stages[-1]):\n        print(line)\n", "    for line in knowledge.section_notices(after, stages[-1])[:1]:\n        print(line)\n", CLOSE),
    (NAV, "    for line in knowledge.section_notices(after, stages[-1]):\n        print(line)\n", "    for line in knowledge.section_notices(after, stages[-1]):\n        print(line)\n        raise NavigatorError(line)\n", CLI),
    # the steps that come after the commit are untouched by the notice (the retire suite checks the terminal order)
    (KNOW, "    if stage not in CLOSES:\n        return []\n    repo = Path(str(state[\"repo\"]))\n    notices", "    if stage not in CLOSES and stage != \"handoff\":\n        return []\n    repo = Path(str(state[\"repo\"]))\n    notices", CLOSE),
]


def main() -> int:
    paths = sorted({row[0] for row in ROWS})
    dirty = subprocess.run(["git", "-C", str(ROOT), "status", "--porcelain", "--", *paths], capture_output=True, text=True).stdout
    if dirty.strip():
        print("refusing to run: these files are not clean in Git:\n" + dirty)
        return 2
    env = {**os.environ, "SHIPLOOP_PROGRESS": "off", "PYTHONDONTWRITEBYTECODE": "1"}
    results = []
    for target, old, new, command in ROWS:
        path = ROOT / target
        original = path.read_text(encoding="utf-8")
        if original.count(old) != 1:
            results.append({"file": target, "replaced": old[:80], "error": "text not found exactly once"})
            print(results[-1])
            continue
        try:
            path.write_text(original.replace(old, new, 1), encoding="utf-8")
            done = subprocess.run([sys.executable, "-B", str(ROOT / command[0]), *command[1:]], capture_output=True,
                                  text=True, cwd=ROOT, env=env, timeout=900)
        finally:
            path.write_text(original, encoding="utf-8")
        failing = sum(1 for line in (done.stdout + done.stderr).splitlines() if line.startswith(("FAIL:", "ERROR:")))
        row = {"file": target, "replaced": old.strip().splitlines()[0][:90], "with": (new.strip().splitlines() or ["(removed)"])[0][:70],
               "tests": " ".join(command[1:2]) or command[0], "exit": done.returncode, "failing": failing}
        results.append(row)
        print(row, flush=True)
    killed = [row for row in results if row.get("exit") == 1 and row.get("failing", 0) > 0]
    survivors = [row for row in results if row not in killed]
    out = Path(__file__).with_name("mutations.json")
    out.write_text(json.dumps({"rows": results, "killed": len(killed), "of": len(results),
                               "survivors": len(survivors)}, indent=1) + "\n", encoding="utf-8")
    print("killed %d of %d; survivors %d" % (len(killed), len(results), len(survivors)))
    return 0 if not survivors else 1


if __name__ == "__main__":
    sys.exit(main())
