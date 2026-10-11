#!/usr/bin/env python3
"""Break the section code one way at a time and count the tests that go red (a test that cannot fail is not a test).

Repeat with:  PYTHONDONTWRITEBYTECODE=1 SHIPLOOP_PROGRESS=off python3 docs/experiments/knowledge-sections-20261010/mutation_check.py

Round 3 (the one-line-per-file round, 2026-10-10): the notice is one line per file naming every missing and empty heading, so the
wording rows follow the new code (the join of the lists, the quoted names, the fix, the architecture wording once); the rows for
the tables, the matching rules, the fences and the navigator are unchanged.  Round 2 (the fix round after review) is
mutations-round2.json (84 rows) and round 1 mutations-round1.json (55 rows); this file's rows replace them.

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
       "RefusalRouteTests.test_a_close_whose_files_have_no_named_sections_is_accepted_and_prints_one_counted_line_per_file",
       "RefusalRouteTests.test_a_close_whose_files_have_every_named_section_is_accepted_and_prints_no_notice",
       "RefusalRouteTests.test_a_stage_that_is_no_close_prints_no_notice_although_a_file_lacks_its_sections",
       "RefusalRouteTests.test_the_fix_a_notice_names_applied_to_its_file_silences_that_heading_and_only_that_heading"]
PACKET = ["test/shiploop-packet-completeness.test.py"]
ROUTE_PLAIN = ["test/shiploop-callback-contract.test.py",
               "RefusalRouteTests.test_the_test_spec_close_prints_its_notice_although_the_script_records_validate_existing_after_it"]
ROUTE_IMPROVE = ["test/shiploop-actual-improve-cli.test.py", "-k", "test_the_test_spec_close_accepted_at_improve_complete"]
GUARD = [K, "SectionsTests.test_every_heading_a_packet_duty_names_for_a_living_file_is_one_of_its_sections"]
PROMPTS = "skills/shiploop/scripts/shiploop_prompts.py"
LOOPS = "skills/shiploop/scripts/shiploop_loops.py"
ROWS = [
    # the headings as constants
    (KNOW, '    "spec.md": ("Requirements", "Non-functional requirements", "Retired"),', '    "spec.md": ("Requirements", "Retired"),', TABLES),
    (KNOW, '("Targets and runtimes", "Commands", "Skills", "Access and accounts", "Platform facts")', '("Commands", "Targets and runtimes", "Skills", "Access and accounts", "Platform facts")', TABLES),
    (KNOW, '("Targets and runtimes", "Commands", "Skills", "Access and accounts", "Platform facts")', '("Targets and runtimes", "Commands", "Access and accounts", "Platform facts")', TABLES),
    (KNOW, '("Targets and runtimes", "Commands", "Skills", "Access and accounts", "Platform facts")', '("Targets and runtimes", "Commands", "Access and accounts", "Skills", "Platform facts")', TABLES),
    (KNOW, '("Stack", "Structure", "Conventions", "Interfaces and boundaries", "Decisions", "Superseded")', '("Stack", "Structure", "Conventions", "Interfaces and boundaries", "Decisions")', TABLES),
    (KNOW, '("Harnesses and suites", "Commands", "ID convention", "Real-boundary checks")', '("Harnesses and suites", "Commands", "ID convention", "Real boundary checks")', TABLES),
    (KNOW, '           "SECTIONS",\n', '', TABLES),
    (KNOW, "a '## Decisions' section of stable IDs", "a '## Decision log' section of stable IDs", TABLES),
    # the duties' headings are pinned to the constants (the guard reads the scripts; a duty naming a heading SECTIONS lacks is red)
    (PROMPTS, "environment.md (## Commands, ## Targets and runtimes, ## Skills)", "environment.md (## Commands, ## Targets and runtimes, ## Skillz)", GUARD),
    (LOOPS, "(environment.md ## Skills \"", "(environment.md ## Skillz \"", GUARD),
    (PROMPTS, "architecture.md (## Decisions, ## Superseded)", "architecture.md (## Decisions, ## Replaced)", GUARD),
    # the writer entries
    (KNOW, '    "research": ("environment.md",),\n', '', TABLES),
    (KNOW, '    "step-plan": ("{feature}/plan.md", ARCHITECTURE, "environment.md"),', '    "step-plan": ("{feature}/plan.md", ARCHITECTURE),', TABLES),
    (KNOW, '    "step-plan": ("{feature}/plan.md", ARCHITECTURE, "environment.md"),', '    "step-plan": ("{feature}/plan.md", "environment.md", ARCHITECTURE),', TABLES),
    (KNOW, '    "step-plan": ("{feature}/plan.md", ARCHITECTURE, "environment.md"),', '    "step-plan": ("{feature}/plan.md", "environment.md"),', TABLES),
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
    (KNOW, "        if not _filled(path):\n            continue\n        try:\n            # utf-8-sig", "        if not path.is_file():\n            continue\n        try:\n            # utf-8-sig", NOTICE),
    (KNOW, "        except OSError:\n            continue\n        outline = _outline", "        except ValueError:\n            continue\n        outline = _outline", NOTICE),
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
    (KNOW, '_HEADING = re.compile(r"^(#{1,4})\\s+(.+?)\\s*$")', '_HEADING = re.compile(r"^ {0,3}(#{1,4})\\s+(.+?)\\s*$")', NOTICE),  # an indented heading counts: the documented limit is pinned
    (KNOW, "        if heading and len(heading.group(1)) <= 3:\n            current", "        if heading:\n            current", NOTICE),
    # fences: the opener (CommonMark: up to three spaces, no backtick after a backtick run) and the closer
    (KNOW, "        if opening:\n            fence = opening.group(1)\n            continue", "        if False:\n            fence = opening.group(1)\n            continue", NOTICE),
    (KNOW, "            if opening and rest[0] == fence[0] and len(rest) >= len(fence) and rest == rest[0] * len(rest):", "            if opening:", NOTICE),
    (KNOW, "            if opening and rest[0] == fence[0] and len(rest) >= len(fence) and rest == rest[0] * len(rest):", "            if opening and len(rest) >= len(fence) and rest == rest[0] * len(rest):", NOTICE),
    (KNOW, "            if opening and rest[0] == fence[0] and len(rest) >= len(fence) and rest == rest[0] * len(rest):", "            if opening and rest[0] == fence[0] and rest == rest[0] * len(rest):", NOTICE),
    (KNOW, '_FENCE = re.compile(r"^ {0,3}(`{3,}(?=[^`]*$)|~{3,})")', '_FENCE = re.compile(r"^ {0,3}(`{3,}(?=[^`]*$))")', NOTICE),
    (KNOW, '_FENCE = re.compile(r"^ {0,3}(`{3,}(?=[^`]*$)|~{3,})")', '_FENCE = re.compile(r"^ *(`{3,}(?=[^`]*$)|~{3,})")', NOTICE),
    (KNOW, '_FENCE = re.compile(r"^ {0,3}(`{3,}(?=[^`]*$)|~{3,})")', '_FENCE = re.compile(r"^\\s{0,3}(`{3,}(?=[^`]*$)|~{3,})")', NOTICE),
    (KNOW, '_FENCE = re.compile(r"^ {0,3}(`{3,}(?=[^`]*$)|~{3,})")', '_FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})")', NOTICE),
    (KNOW, '_FENCE = re.compile(r"^ {0,3}(`{3,}(?=[^`]*$)|~{3,})")', '_FENCE = re.compile(r"^ {0,3}(`{3,}(?=[^`]*$)|~{3,}(?=[^`~]*$))")', NOTICE),  # a tilde fence with a backtick in its text
    (KNOW, '_FENCE = re.compile(r"^ {0,3}(`{3,}(?=[^`]*$)|~{3,})")', '_FENCE = re.compile(r"^ {0,3}(`{2,}(?=[^`]*$)|~{2,})")', NOTICE),
    # the byte order mark
    (KNOW, 'path.read_text(encoding="utf-8-sig", errors="replace").splitlines()', 'path.read_text(encoding="utf-8", errors="replace").splitlines()', NOTICE),
    # the wording a reader greps and acts on: the prefix, the file as the first word, the lists, the acceptance, the fix, the architecture words
    (KNOW, 'NOTICE_PREFIX = "ShipLoop knowledge notice: "', 'NOTICE_PREFIX = "ShipLoop knowledge: "', NOTICE),
    (KNOW, 'notices.append(NOTICE_PREFIX + str(path) + " has " + " and ".join(said)', 'notices.append(NOTICE_PREFIX + str(path.relative_to(repo)) + " has " + " and ".join(said)', NOTICE),
    (KNOW, 'notices.append(NOTICE_PREFIX + str(path) + " has " + " and ".join(said)', 'notices.append(NOTICE_PREFIX + "has " + " and ".join(said) + " in " + str(path)', NOTICE),
    (KNOW, 'notices.append(NOTICE_PREFIX + str(path) + " has " + " and ".join(said)', 'notices.append(NOTICE_PREFIX + str(path) + ": " + " and ".join(said)', NOTICE),
    (KNOW, '" has " + " and ".join(said) + " " + _ACCEPTED', '" has " + "".join(said) + " " + _ACCEPTED', NOTICE),
    (KNOW, '" has " + " and ".join(said) + " " + _ACCEPTED', '" has " + ", ".join(said) + " " + _ACCEPTED', NOTICE),
    (KNOW, '" has " + " and ".join(said) + " " + _ACCEPTED', '" has " + " and ".join(said[:1]) + " " + _ACCEPTED', NOTICE),
    (KNOW, 'for state_name, lead in (("missing", "no "), ("empty", "an empty ")):', 'for state_name, lead in (("empty", "an empty "), ("missing", "no ")):', NOTICE),
    (KNOW, 'for state_name, lead in (("missing", "no "), ("empty", "an empty ")):', 'for state_name, lead in (("missing", "no "),):', NOTICE),
    (KNOW, 'for state_name, lead in (("missing", "no "), ("empty", "an empty ")):', 'for state_name, lead in (("missing", "no "), ("empty", "empty ")):', NOTICE),
    (KNOW, 'for state_name, lead in (("missing", "no "), ("empty", "an empty ")):', 'for state_name, lead in (("missing", "no "), ("empty", "no ")):', NOTICE),
    (KNOW, 'said.append(lead + ", ".join(quoted) + " section")', 'said.append(lead + ",".join(quoted) + " section")', NOTICE),
    (KNOW, 'said.append(lead + ", ".join(quoted) + " section")', 'said.append(lead + ", ".join(quoted) + " sections")', NOTICE),
    (KNOW, 'said.append(lead + ", ".join(quoted) + " section")', 'said.append(lead + ", ".join(quoted[:1]) + " section")', NOTICE),
    (KNOW, 'said.append(lead + ", ".join(quoted) + " section")', 'said.append(lead + "; ".join(quoted) + " section")', NOTICE),
    (KNOW, '''quoted = ["'" + heading + "'" for heading in headings if found[heading] == state_name]''', '''quoted = ["'" + heading + "'" for heading in sorted(headings) if found[heading] == state_name]''', NOTICE),
    (KNOW, '''quoted = ["'" + heading + "'" for heading in headings if found[heading] == state_name]''', '''quoted = ["'" + heading + "'" for heading in headings if found[heading] != "present"]''', NOTICE),
    (KNOW, '''quoted = ["'" + heading + "'" for heading in headings if found[heading] == state_name]''', '''quoted = [heading for heading in headings if found[heading] == state_name]''', NOTICE),
    (KNOW, '''quoted = ["'" + heading + "'" for heading in headings if found[heading] == state_name]''', '''quoted = ['"' + heading + '"' for heading in headings if found[heading] == state_name]''', NOTICE),
    (KNOW, "        if said:\n            notices.append", "        if True:\n            notices.append", NOTICE),
    (KNOW, "        if said:\n            notices.append", "        if said and found[headings[0]] != 'present':\n            notices.append", NOTICE),
    (KNOW, '_ACCEPTED = "(this close is accepted)"', '_ACCEPTED = "(this close is refused)"', NOTICE),
    (KNOW, '" " + _ACCEPTED + "; " + _FIX', '"; " + _FIX', NOTICE),
    (KNOW, '" " + _ACCEPTED + "; " + _FIX', '" " + _ACCEPTED + ". " + _FIX', NOTICE),
    (KNOW, '" " + _ACCEPTED + "; " + _FIX', '" " + _ACCEPTED + " " + _FIX', NOTICE),
    (KNOW, """or write 'none' there if it does not apply.")""", """or leave it if it does not apply.")""", NOTICE),
    (KNOW, '''_FIX = ("for each, write its content under a '## <heading>' (add the heading if missing), "''', '''_FIX = ("for each, write its content under a '## <heading>', "''', NOTICE),
    (KNOW, '(" " + name + " holds " + ARCHITECTURE_HOLDS + "." if name == ARCHITECTURE else "")', '(" " + name + " holds " + ARCHITECTURE_HOLDS + "." if True else "")', NOTICE),
    (KNOW, '(" " + name + " holds " + ARCHITECTURE_HOLDS + "." if name == ARCHITECTURE else "")', '(" " + name + " holds " + ARCHITECTURE_HOLDS + "." if name != ARCHITECTURE else "")', NOTICE),
    (KNOW, '(" " + name + " holds " + ARCHITECTURE_HOLDS + "." if name == ARCHITECTURE else "")', '("" if name == ARCHITECTURE else "")', NOTICE),
    (KNOW, '(" " + name + " holds " + ARCHITECTURE_HOLDS + "." if name == ARCHITECTURE else "")', '(" " + name + " holds " + ARCHITECTURE_HOLDS if name == ARCHITECTURE else "")', NOTICE),
    (KNOW, '(" " + name + " holds " + ARCHITECTURE_HOLDS + "." if name == ARCHITECTURE else "")', '(" holds " + ARCHITECTURE_HOLDS + "." if name == ARCHITECTURE else "")', NOTICE),
    (KNOW, '(" " + name + " holds " + ARCHITECTURE_HOLDS + "." if name == ARCHITECTURE else "")', '(" " + name + " holds " + ARCHITECTURE_HOLDS + "." if name == ARCHITECTURE and "Stack" in said[0] else "")', NOTICE),
    # the navigator: printed once, on stdout, at the close accepted in this call, after the commit
    (NAV, "    for line in knowledge.section_notices(after, close):\n        print(line)\n", "", CLOSE),
    (NAV, "    for line in knowledge.section_notices(after, close):\n        print(line)\n", "", CLI),
    (NAV, "    for line in knowledge.section_notices(after, close):\n        print(line)\n", "    for line in knowledge.section_notices(after, close):\n        print(line, file=sys.stderr)\n", CLOSE),
    (NAV, "    for line in knowledge.section_notices(after, close):\n        print(line)\n", "    for line in knowledge.section_notices(after, close)[:1]:\n        print(line)\n", CLOSE),
    (NAV, "    for line in knowledge.section_notices(after, close):\n        print(line)\n", "    for line in knowledge.section_notices(after, close):\n        print(line)\n        raise NavigatorError(line)\n", CLI),
    (NAV, "    close = next((stage for stage in reversed(stages) if stage in knowledge.CLOSES), stages[-1])\n", "    close = stages[-1]\n", CLOSE),
    (NAV, "    close = next((stage for stage in reversed(stages) if stage in knowledge.CLOSES), stages[-1])\n", "    close = stages[-1]\n", ROUTE_PLAIN),
    (NAV, "    close = next((stage for stage in reversed(stages) if stage in knowledge.CLOSES), stages[-1])\n", "    close = stages[-1]\n", ROUTE_IMPROVE),
    (NAV, "    close = next((stage for stage in reversed(stages) if stage in knowledge.CLOSES), stages[-1])\n", "    close = stages[0]\n", CLOSE),
    (NAV, "    close = next((stage for stage in reversed(stages) if stage in knowledge.CLOSES), stages[-1])\n", "    close = next((stage for stage in reversed(stages) if stage in knowledge.CLOSES), 'prepare')\n", CLOSE),
    (NAV, "    close = next((stage for stage in reversed(stages) if stage in knowledge.CLOSES), stages[-1])\n", "    close = next((stage for stage in reversed(stages) if stage in knowledge.STAGE_FILES), stages[-1])\n", CLOSE),
    (NAV, "    stages = [row[\"stage\"] for row in rows if row[\"outcome\"] == \"done\"]", "    stages = [row[\"stage\"] for row in rows]", CLOSE),
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

