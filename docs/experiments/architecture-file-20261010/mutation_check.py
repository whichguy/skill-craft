#!/usr/bin/env python3
"""Break the architecture-file code one way at a time and count the tests that go red (a test that cannot fail is not a test).

Repeat with:  PYTHONDONTWRITEBYTECODE=1 SHIPLOOP_PROGRESS=off python3 docs/experiments/architecture-file-20261010/mutation_check.py

Each row names a file, the exact text replaced, its replacement and the test selector run.  The file is restored after every row
(and on any error); the run refuses to start when the two source files are not clean in Git.  Writes mutations.json beside this
file.  Every row must turn its selector red.  About five minutes in the foreground: the whole knowledge suite is ~11 s (the rows
about the "present" rule), ArchitectureTests ~5 s (most rows), KnowledgeTests ~2 s, the two improve rows ~6 s each.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
KNOW = "skills/shiploop/scripts/shiploop_knowledge_home.py"
NAV = "skills/shiploop/scripts/shiploop_navigator.py"
SUITE = ["test/shiploop-knowledge.test.py"]
ARCH = ["test/shiploop-knowledge.test.py", "ArchitectureTests"]
BASE = ["test/shiploop-knowledge.test.py", "KnowledgeTests"]
IMPROVE = ["test/shiploop-actual-improve-cli.test.py",
           "EphemeralImproveCliTests.test_a_reviewed_step_plan_that_drops_a_decision_id_is_refused_at_improve_complete_and_the_named_sequence_is_accepted",
           "EphemeralImproveCliTests.test_a_reviewed_step_plan_whose_architecture_looks_like_a_credential_is_refused_with_the_fix_and_the_route_commands"]
ROWS = [
    # the "present" rule shared by the close and grounding
    (KNOW, 'return path.is_file() and bool(path.read_text(encoding="utf-8", errors="replace").strip())', "return path.is_file()", SUITE),
    (KNOW, "    except OSError:\n        return False", "    except OSError:\n        return True", SUITE),
    (KNOW, "missing = [path for path in required if not _filled(repo / path)]", "missing = [path for path in required if not (repo / path).is_file()]", SUITE),
    # the tables
    (KNOW, '"test-strategy.md", ARCHITECTURE,\n                "{feature}/spec.md"', '"test-strategy.md",\n                "{feature}/spec.md"', ARCH),
    (KNOW, '"plan": ("{feature}/plan.md", "README.md", ARCHITECTURE)', '"plan": ("{feature}/plan.md", "README.md")', ARCH),
    (KNOW, '"step-plan": ("{feature}/plan.md", ARCHITECTURE)', '"step-plan": ("{feature}/plan.md",)', ARCH),
    (KNOW, '"prepare": ("environment.md",),', '"prepare": ("environment.md", ARCHITECTURE),', ARCH),
    (KNOW, 'LIVING = ("README.md", "spec.md", "environment.md", "test-strategy.md", ARCHITECTURE)', 'LIVING = ("README.md", "spec.md", "environment.md", "test-strategy.md")', ARCH),
    # what the refusal says about the new file
    (KNOW, '(ARCHITECTURE + " holds " + ARCHITECTURE_HOLDS + ".\\n" if str(repo / HOME / ARCHITECTURE) in paths else "")', '""', ARCH),
    (KNOW, '(ARCHITECTURE + " holds " + ARCHITECTURE_HOLDS + ".\\n" if str(repo / HOME / ARCHITECTURE) in paths else "")', '(ARCHITECTURE + " holds " + ARCHITECTURE_HOLDS + ".\\n")', ARCH),
    (KNOW, 'if str(repo / HOME / ARCHITECTURE) in paths else ""', 'if str(repo / HOME / ARCHITECTURE) in paths and len(paths) == 1 else ""', BASE),
    (KNOW, '"the stack (language, frameworks, dependencies and why), the structure', '"the stack and runtime (language, frameworks, dependencies and why), the structure', ARCH),
    (KNOW, "stable IDs AD-<n> (choice", "stable IDs D-<n> (choice", ARCH),
    # retention
    (KNOW, ',\n             (ARCHITECTURE, _DECISION_ID, "architecture", "decision", "Superseded"))', ")", ARCH),
    (KNOW, '_RETAINED = (("spec.md", _REQUIREMENT_ID, "living spec", "requirement", "Retired"),\n             (ARCHITECTURE,',
     '_RETAINED = ((ARCHITECTURE, _DECISION_ID, "architecture", "decision", "Superseded"),\n             ("spec.md",', ARCH),
    (KNOW, '(ARCHITECTURE, _DECISION_ID, "architecture", "decision", "Superseded")', '(ARCHITECTURE, _DECISION_ID, "architecture", "decision", "Retired")', ARCH),
    (KNOW, '_DECISION_ID = re.compile(r"\\b(AD-\\d+)\\b")', '_DECISION_ID = re.compile(r"(AD-\\d+)")', ARCH),
    (KNOW, '_DECISION_ID = re.compile(r"\\b(AD-\\d+)\\b")', '_DECISION_ID = re.compile(r"\\b(AD-\\d+)")', ARCH),
    (KNOW, '_DECISION_ID = re.compile(r"\\b(AD-\\d+)\\b")', '_DECISION_ID = re.compile(r"\\b(D-\\d+)\\b")', ARCH),
    (KNOW, 'key=lambda value: int(value.split("-")[1]))', "key=None)", ARCH),
    (KNOW, "if path.is_file() else set()", 'if path.is_file() else set(ids.findall(_committed(repo, name)))', ARCH),
    (KNOW, '    return "\\n".join(refusals)', '    return "\\n".join(refusals) if stage in CLOSES else ""', ARCH),
    (KNOW, '    return "\\n".join(refusals)', '    return refusals[0] if refusals else ""', ARCH),
    (KNOW, 'shown = _git(repo, "show", "HEAD:" + HOME + "/" + name)', 'shown = _git(repo, "show", "HEAD:" + HOME + "/spec.md")', ARCH),
    # the baseline is what HEAD holds, not the index (batch 1012 fix round: the survivor m17 of the review)
    (KNOW, 'shown = _git(repo, "show", "HEAD:" + HOME + "/" + name)', 'shown = _git(repo, "show", ":" + HOME + "/" + name)', ARCH),
    # the shape of the dropped-ID refusal: complete route
    (KNOW, '"\', then run the same complete command again.")', '"\'.")', ARCH),
    (KNOW, '"\', then run the same complete command again.")', '"\', then run the same improve-complete command again.")', ARCH),
    (KNOW, '"Restore the lost " + prefix + "-<n> in "', '"Restore the lost " + ", ".join(dropped) + " in "', ARCH),
    (KNOW, '" or move it under \'" + section', '" or move it under a \'" + section', ARCH),
    (KNOW, '"Restore the lost " + prefix + "-<n> in " + str(path)', '"Restore the lost " + prefix + "-<n> in docs/shiploop/" + name', ARCH),
    # the improve-complete route: the real sequence on line 1
    (KNOW, '"; if the review changed it, improve-commit it; "', '"; "', ARCH),
    (KNOW, '"then run " + command + ".")', '"then run complete.")', ARCH),
    (KNOW, '            if command == "complete":\n                first', '            if command == "complete" or name == "spec.md":\n                first', ARCH),
    (KNOW, '            if command == "complete":\n                first', '            if command != "complete":\n                first', ARCH),
    # the credential refusal: place, fix and command on line 1, every place after it
    (KNOW, '"Reword " + leaks[0]', '"Reword " + leaks[-1]', ARCH),
    (KNOW, 'leaks.append(str(path) + ":" + str(number))', 'leaks.append(str(path.relative_to(repo)) + ":" + str(number))', ARCH),
    (KNOW, 'assignment; then run the same " + command', 'assignment; then run the same complete"', ARCH),
    (KNOW, '"\\n".join("- " + place for place in leaks)', '"\\n".join("- " + place for place in leaks[:1])', ARCH),
    (KNOW, '"These knowledge lines look like credentials;', '"These knowledge lines resemble secrets;', ARCH),
    (KNOW, 'if command == "improve-complete" else ""))', 'if False else ""))', ARCH),
    # grounding
    (KNOW, '("architecture", ARCHITECTURE), ("test strategy", "test-strategy.md"))', '("test strategy", "test-strategy.md"), ("architecture", ARCHITECTURE))', SUITE),
    (KNOW, '("feature spec", "{feature}/spec.md")', '("feature spec", "README.md")', SUITE),
    (KNOW, "if _filled(repo / path)]", "if (repo / path).is_file()]", SUITE),
    (KNOW, 'repo = Path(str(state["repo"]))\n    paths = _expand', 'repo = Path(str(state["repo"])); _git(repo, "status")\n    paths = _expand', SUITE),
    (KNOW, "    return [(label, repo / path) for (label, _), path in zip(_GROUNDING, paths) if _filled(repo / path)]",
     "    return [(label, Path(path)) for (label, _), path in zip(_GROUNDING, paths) if _filled(repo / path)]", SUITE),
    # the route's own verb
    (NAV, 'child["seed_result"] if final_result is None else final_result, "improve-complete")', 'child["seed_result"] if final_result is None else final_result)', IMPROVE),
    (NAV, "refusal = knowledge.check(state, stage, command)", "refusal = knowledge.check(state, stage)", IMPROVE),
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
        row = {"file": target, "replaced": old.strip().splitlines()[0][:90], "with": new.strip().splitlines()[0][:70],
               "tests": " ".join(command[1:]) or command[0], "exit": done.returncode, "failing": failing}
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
