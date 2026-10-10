#!/usr/bin/env python3
"""Break the architecture-file code one way at a time and count the tests that go red (a test that cannot fail is not a test).

Repeat with:  PYTHONDONTWRITEBYTECODE=1 SHIPLOOP_PROGRESS=off python3 docs/experiments/architecture-file-20261010/mutation_check.py

Each row names a file, the exact text replaced, its replacement and the test selector run.  The file is restored after every row
(and on any error); the run refuses to start when the two source files are not clean in Git.  Writes mutations.json beside this
file.  Every row must turn its selector red.  About eight minutes: the knowledge suite is ~12 s per row, the two route rows ~3 s each.
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
IMPROVE = ["test/shiploop-actual-improve-cli.test.py",
           "EphemeralImproveCliTests.test_a_reviewed_step_plan_that_drops_a_decision_id_is_refused_at_improve_complete_and_the_named_exit_is_accepted"]
ROWS = [
    # the "present" rule shared by the close and grounding
    (KNOW, 'return path.is_file() and bool(path.read_text(encoding="utf-8", errors="replace").strip())', "return path.is_file()", SUITE),
    (KNOW, "    except OSError:\n        return False", "    except OSError:\n        return True", SUITE),
    (KNOW, "missing = [path for path in required if not _filled(repo / path)]", "missing = [path for path in required if not (repo / path).is_file()]", SUITE),
    # the tables
    (KNOW, '"test-strategy.md", ARCHITECTURE,\n                "{feature}/spec.md"', '"test-strategy.md",\n                "{feature}/spec.md"', SUITE),
    (KNOW, '"plan": ("{feature}/plan.md", "README.md", ARCHITECTURE)', '"plan": ("{feature}/plan.md", "README.md")', SUITE),
    (KNOW, '"step-plan": ("{feature}/plan.md", ARCHITECTURE)', '"step-plan": ("{feature}/plan.md",)', SUITE),
    (KNOW, '"prepare": ("environment.md",),', '"prepare": ("environment.md", ARCHITECTURE),', SUITE),
    (KNOW, 'LIVING = ("README.md", "spec.md", "environment.md", "test-strategy.md", ARCHITECTURE)', 'LIVING = ("README.md", "spec.md", "environment.md", "test-strategy.md")', SUITE),
    # what the refusal says about the new file
    (KNOW, '(ARCHITECTURE + " holds " + ARCHITECTURE_HOLDS + ".\\n" if str(repo / HOME / ARCHITECTURE) in paths else "")', '""', SUITE),
    (KNOW, '(ARCHITECTURE + " holds " + ARCHITECTURE_HOLDS + ".\\n" if str(repo / HOME / ARCHITECTURE) in paths else "")', '(ARCHITECTURE + " holds " + ARCHITECTURE_HOLDS + ".\\n")', SUITE),
    (KNOW, '"the stack (language, frameworks, dependencies and why), the structure', '"the stack and runtime (language, frameworks, dependencies and why), the structure', SUITE),
    (KNOW, "stable IDs AD-<n> (choice", "stable IDs D-<n> (choice", SUITE),
    # retention
    (KNOW, ',\n             (ARCHITECTURE, _DECISION_ID, "architecture", "decision", "Superseded"))', ")", SUITE),
    (KNOW, '_RETAINED = (("spec.md", _REQUIREMENT_ID, "living spec", "requirement", "Retired"),\n             (ARCHITECTURE,',
     '_RETAINED = ((ARCHITECTURE, _DECISION_ID, "architecture", "decision", "Superseded"),\n             ("spec.md",', SUITE),
    (KNOW, '(ARCHITECTURE, _DECISION_ID, "architecture", "decision", "Superseded")', '(ARCHITECTURE, _DECISION_ID, "architecture", "decision", "Retired")', SUITE),
    (KNOW, '_DECISION_ID = re.compile(r"\\b(AD-\\d+)\\b")', '_DECISION_ID = re.compile(r"(AD-\\d+)")', SUITE),
    (KNOW, '_DECISION_ID = re.compile(r"\\b(AD-\\d+)\\b")', '_DECISION_ID = re.compile(r"\\b(AD-\\d+)")', SUITE),
    (KNOW, '_DECISION_ID = re.compile(r"\\b(AD-\\d+)\\b")', '_DECISION_ID = re.compile(r"\\b(D-\\d+)\\b")', SUITE),
    (KNOW, 'key=lambda value: int(value.split("-")[1]))', "key=None)", SUITE),
    (KNOW, "if path.is_file() else set()", 'if path.is_file() else set(ids.findall(_committed(repo, name)))', SUITE),
    (KNOW, '    return "\\n".join(refusals)', '    return "\\n".join(refusals) if stage in CLOSES else ""', SUITE),
    (KNOW, '    return "\\n".join(refusals)', '    return refusals[0] if refusals else ""', SUITE),
    (KNOW, 'shown = _git(repo, "show", "HEAD:" + HOME + "/" + name)', 'shown = _git(repo, "show", "HEAD:" + HOME + "/spec.md")', SUITE),
    # the shape of the refusal
    (KNOW, ', then run the same " + command + " command again.\\n"', '.\\n"', SUITE),
    (KNOW, ', then run the same " + command + " command again.\\n"', ', then run the same complete command again.\\n"', SUITE),
    (KNOW, '"Restore the lost " + dropped[0].split("-")[0] + "-<n> in "', '"Restore the lost " + ", ".join(dropped) + " in "', SUITE),
    (KNOW, '" or move it under \'"', '" or move it under a \'"', SUITE),
    (KNOW, '"Restore the lost " + dropped[0].split("-")[0] + "-<n> in " + str(path)', '"Restore the lost " + dropped[0].split("-")[0] + "-<n> in docs/shiploop/" + name', SUITE),
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
