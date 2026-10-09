#!/usr/bin/env python3
"""Mutation check of the G6 build: ``python3 mutate.py a1|a5`` from anywhere.

Each mutant is one textual change to the shipped source.  The script copies the repository (without .git) to a temporary
directory, applies the change, runs the named tests there and reports CAUGHT when at least one fails or errors.  A pattern
that is not found is reported as BAD MUTANT.  Two mutants are equivalent and left out: the earliest step-plan row instead of
the latest (a plan action has one history row), and removing the ``test_id not in text`` prefilter in
``shiploop_test_counts.named`` (it only skips a second pass over the lines, a timing change).
"""
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
LOOP = "skills/shiploop/scripts/shiploop_test_loop.py"
COUNTS = "skills/shiploop/scripts/shiploop_test_counts.py"
PROMPTS = "skills/shiploop/scripts/shiploop_prompts.py"

A1 = [('A1-1 raw substring (the prototype bug)',
  COUNTS,
  'if any(match.group(1) not in listed for match in pattern.finditer(line))\n'
  '                      and not _SKIP_LINE.search(line)), None)',
  'if test_id in line and not _SKIP_LINE.search(line)), None)'),
 ('A1-2 skip lines count as inside',
  COUNTS,
  'for match in pattern.finditer(line))\n                      and not _SKIP_LINE.search(line)), None)',
  'for match in pattern.finditer(line))), None)'),
 ('A1-3 digit-ending ID: any word char starts a new run',
  COUNTS,
  'new_run = r"[^\\W\\d]" if last.isdigit()',
  'new_run = r"\\w" if last.isdigit()'),
 ('A1-4 letter-ending ID: any word char starts a new run',
  COUNTS,
  'else r"[\\d_]" if last.isalpha()',
  'else r"\\w" if last.isalpha()'),
 ('A1-5 inside drops the left word boundary',
  COUNTS,
  'return re.compile(r"(?<![\\w-])(" + re.escape(test_id) + "(?=" + new_run + r")\\w+)")',
  'return re.compile(r"(" + re.escape(test_id) + "(?=" + new_run + r")\\w+)")'),
 ('A1-6 the quoted line is not cut',
  COUNTS,
  'inside[test_id] = first[:INSIDE_CHARS]',
  'inside[test_id] = first'),
 ('A1-7 the judge drops ids_inside',
  LOOP,
  '    if names.get("inside"):\n        verdict["ids_inside"] = names["inside"]\n',
  ''),
 ('A1-8 the refusal keeps the --verbose remedy for an inside ID',
  LOOP,
  'apart = [test_id for test_id in run["ids_missing"] if test_id not in inside]',
  'apart = list(run["ids_missing"])'),
 ('A1-9 the refusal omits the rule',
  LOOP,
  'seen + ". " + guidance.ID_WORD_RULE\n',
  'seen + ". "\n'),
 ('A1-10 COUNT_RULE omits the rule',
  LOOP,
  '              + guidance.ID_WORD_RULE + " A filter "',
  '              + " A filter "'),
 ('A1-11 red_lines omits the rule',
  LOOP,
  '" and every listed ID must appear in the output. " + guidance.ID_WORD_RULE + " A failure before any"',
  '" and every listed ID must appear in the output. A failure before any"'),
 ('A1-12 test-author duty omits the rule',
  PROMPTS,
  'a failing test). """ + ID_WORD_RULE + """',
  'a failing test). """ + """'),
 ('A1-13 step-plan duty omits the rule',
  PROMPTS,
  'so the output shows them. """ + ID_WORD_RULE + """ Declare',
  'so the output shows them. """ + """ Declare'),
 ('A1-14 a longer token that is itself a listed ID holds the shorter one inside',
  COUNTS,
  'any(match.group(1) not in listed for match in pattern.finditer(line))',
  'any(True for match in pattern.finditer(line))'),
 ('A1-15 letter-ending ID: an underscore is not a new run',
  COUNTS,
  'else r"[\\d_]" if last.isalpha()',
  'else r"\\d" if last.isalpha()'),
 ('A1-16 the refusal quotes the last inside ID, not the first',
  LOOP,
  'first = next(iter(inside))',
  'first = list(inside)[-1]'),
 ('A1-17 only the first longer token of a line is looked at',
  COUNTS,
  'for match in pattern.finditer(line))\n                      and not _SKIP_LINE.search(line)), None)',
  'for match in list(pattern.finditer(line))[:1])\n                      and not _SKIP_LINE.search(line)), None)')]

A1_TESTS = [['test/shiploop-test-counts.test.py'],
 ['test/shiploop-test-loop.test.py', '-k', 'WholeWordIdTests', '-k', 'whole_word', '-k', 'starts_another_id']]

A5 = [('A5-1 refused records count', LOOP, ' or not record.get("passed"):', ':'),
 ('A5-2 scope ignores the step plan (a revise does not lower)',
  LOOP,
  'first = max(i for i, row in enumerate(history) if row.get("action") == plan) + 1',
  'first = 0'),
 ('A5-4 outer stages held (the stage guard removed)',
  LOOP,
  'floors = {} if stage in OUTER_SOURCES or stage == REFINE_STAGE else',
  'floors = {} if stage == REFINE_STAGE else'),
 ('A5-5 an equal count is refused',
  LOOP,
  'run["counts"]["ran"] < earlier:',
  'run["counts"]["ran"] <= earlier:'),
 ('A5-6 floor from other work items too',
  LOOP,
  'for row in history[first:] if row.get("workitem") == work_item):',
  'for row in history[first:]):'),
 ('A5-7 a red run is not an observation',
  LOOP,
  'if run.get("status") in ("passed", "red") and isinstance(ran, int):',
  'if run.get("status") in ("passed",) and isinstance(ran, int):'),
 ('A5-8 a red run is not converted',
  LOOP,
  'if run["status"] in ("passed", "red") and run["counts"] and run["counts"]["ran"] < earlier:',
  'if run["status"] in ("passed",) and run["counts"] and run["counts"]["ran"] < earlier:'),
 ('A5-9 the outer packet prints the floor',
  LOOP,
  '    if stage in OUTER_SOURCES:\n        return []\n    return [REFINE_RULE',
  '    return [REFINE_RULE'),
 ('A5-10 no restart at test-refine', LOOP, '    if refined:\n        first = refined[-1]\n', ''),
 ('A5-11 test-refine is floored',
  LOOP,
  'floors = {} if stage in OUTER_SOURCES or stage == REFINE_STAGE else',
  'floors = {} if stage in OUTER_SOURCES else'),
 ('A5-12 the refine packet prints the floor rule',
  LOOP,
  '[REFINE_RULE if stage == REFINE_STAGE else RATCHET_RULE]',
  '[RATCHET_RULE]'),
 ('A5-13 a loop stage is told revise now',
  LOOP,
  'if _has_loop_packet(stage) else\n',
  'if False else\n'),
 ('A5-14 a free stage is told the loop wording',
  LOOP,
  'if _has_loop_packet(stage) else\n',
  'if True else\n'),
 ('A5-15 the red packet omits the floor', LOOP, '\n            + _floor_lines(RED_STAGE))', ')'),
 ('A5-16 accepted_ran recorded only when it refuses',
  LOOP,
  '                run["accepted_ran"] = earlier\n'
  '                if run["status"] in ("passed", "red") and run["counts"] and run["counts"]["ran"] < earlier:\n'
  '                    run["status"] = "too-few-tests"',
  '                if run["status"] in ("passed", "red") and run["counts"] and run["counts"]["ran"] < earlier:\n'
  '                    run["accepted_ran"] = earlier\n'
  '                    run["status"] = "too-few-tests"'),
 ('A5-17 an uncounted run is read as a count', LOOP, 'isinstance(ran, int):', 'True:'),
 ("A5-18 the plan's own minimum always gets the floor wording",
  LOOP,
  'if earlier > int(run.get("min_tests") or 0):',
  'if True:'),
 ('A5-19 the floor refusal loses the restore advice',
  LOOP,
  'Restore the tests that were removed or now skip. ',
  ''),
 ('A5-20 a floor refusal does not count toward the cap',
  LOOP,
  'UNAVAILABLE = ("timeout", "skipped", "error")',
  'UNAVAILABLE = ("timeout", "skipped", "error", "too-few-tests")'),
 ('A5-21 the test-author duty omits what the probe count becomes',
  PROMPTS,
  ' The number\n'
  'of tests that run here is the least any later run of the command may run for this item, until test-refine reconciles any\n'
  'removed case.',
  ''),
 ('A5-22 the floor is not applied at the verify conversion',
  LOOP,
  'earlier = floors.get(row["command"])',
  'earlier = None'),
 ("A5-23 another item's test-refine restarts this item's count",
  LOOP,
  'if history[i].get("workitem") == work_item and history[i].get("stage") == REFINE_STAGE]',
  'if history[i].get("stage") == REFINE_STAGE]'),
 ('A5-24 the earliest test-refine restarts the count, not the latest',
  LOOP,
  'first = refined[-1]',
  'first = refined[0]'),
 ('A5-25 an unreadable count is compared with the floor',
  LOOP,
  'and run["counts"] and run["counts"]["ran"] < earlier:',
  'and run["counts"]["ran"] < earlier:'),
 ('A5-26 the loop-stage wording denies revise with no Improve card bound',
  LOOP,
  ' (at once when no Improve card is bound)',
  '')]

A5_TESTS = [['test/shiploop-test-loop.test.py',
  '-k',
  'CountFloorTests',
  '-k',
  'floor',
  '-k',
  'restoring_the_removed',
  '-k',
  'test_red_run',
  '-k',
  'revise_is_free',
  '-k',
  'test_refine_is_not_held',
  '-k',
  'WholeWord']]


SETS = {"a1": (A1, A1_TESTS), "a5": (A5, A5_TESTS)}


def main(which: str) -> int:
    mutants, runs = SETS[which]
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", SHIPLOOP_PROGRESS="off", GIT_CONFIG_NOSYSTEM="1",
               GIT_CONFIG_GLOBAL=os.devnull)
    survived = 0
    for name, relative, old, new in mutants:
        with tempfile.TemporaryDirectory(prefix="shiploop-mutant-") as temp:
            copy = Path(temp) / "repo"
            shutil.copytree(ROOT, copy, ignore=shutil.ignore_patterns(".git", "__pycache__"))
            target = copy / relative
            text = target.read_text()
            if old not in text:
                print("BAD MUTANT (pattern not found):", name)
                survived += 1
                continue
            target.write_text(text.replace(old, new, 1))
            failing = []
            for args in runs:
                result = subprocess.run([sys.executable] + args, cwd=copy, env=env, capture_output=True, text=True)
                failing += [line.split(" (")[0] for line in (result.stderr + result.stdout).splitlines()
                            if line.startswith(("FAIL:", "ERROR:"))]
        survived += not failing
        print("CAUGHT" if failing else "SURVIVED", "|", name, "|", len(failing), failing[:2], flush=True)
    return 1 if survived else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))
