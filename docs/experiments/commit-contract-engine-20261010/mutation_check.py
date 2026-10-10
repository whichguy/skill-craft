#!/usr/bin/env python3
"""Break the commit-contract code one way at a time and count the tests that go red (a test that cannot fail is not a test).

Repeat with:  PYTHONDONTWRITEBYTECODE=1 SHIPLOOP_PROGRESS=off python3 docs/experiments/commit-contract-engine-20261010/mutation_check.py

Each row names a file, the exact text replaced, its replacement and the test selector run.  The file is restored
after every row (and on any error); the run refuses to start when the three files are not clean in Git.  Writes
mutations.json beside this file.  About six minutes: the navigator rows run the real-CLI class, ~19 s each.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
LESSONS = "skills/shiploop/scripts/shiploop_lessons.py"
GIT = "skills/shiploop/scripts/shiploop_git.py"
NAV = "skills/shiploop/scripts/shiploop_navigator.py"
KNOW = ["test/shiploop-knowledge.test.py"]
CLI = ["test/shiploop-actual-improve-cli.test.py", "ImproveCommitContractTests"]
ROWS = [
    (LESSONS, "if index >= trailer or _HEADING.match(row):", "if _HEADING.match(row):", KNOW + ["LessonsGrammarTests"]),
    (LESSONS, 'return known is not None and known.group("colon") is not None', "return False", KNOW + ["LessonsGrammarTests"]),
    (LESSONS, "while not first and end < len(lines) and not lines[end].strip():", "while False:", KNOW + ["LessonsGrammarTests"]),
    (LESSONS, 'token = words[0].strip(_TOKEN_EDGE) if words else ""', 'token = words[0] if words else ""', KNOW + ["LessonsGrammarTests"]),
    (LESSONS, 'return re.search(r"[^\\W_]", body) is not None', "return bool(body.strip())", KNOW + ["LessonsGrammarTests"]),
    (LESSONS, 'if len(words) == 2 and words[0].lower() == "commit":', "if False:", KNOW + ["LessonsGrammarTests"]),
    (GIT, '"--allow-empty", "--only", *given', '"--allow-empty", *given', KNOW + ["CommitHelperTests"]),
    (GIT, '"--cleanup=whitespace", *given, "--", *chosen', '*given, "--", *chosen', KNOW + ["CommitHelperTests"]),
    (GIT, '"--cleanup=whitespace", "--allow-empty"', '"--allow-empty"', KNOW + ["CommitHelperTests"]),
    (GIT, 'and git(repo, "cat-file", "-t", name).stdout.strip() == "commit"]', "]", KNOW + ["CommitHelperTests"]),
    (GIT, "name.startswith(token)", "True", KNOW + ["CommitHelperTests"]),
    (GIT, "if reachable.returncode == 1:", "if False:", KNOW + ["CommitHelperTests"]),
    (GIT, '"--disambiguate=" + token', '"--verify", token', KNOW + ["CommitHelperTests"]),
    (GIT, 'if git(repo, "rev-parse", "--verify", "-q", "HEAD").returncode:', "if False:", KNOW + ["CommitHelperTests"]),
    (NAV, "        message_path.unlink()  # a stale message must not be committed by a later run", "        pass", CLI),
    (NAV, "    refusal = _credential_refusal(message, message_path, command)\n    _need(not refusal, refusal)\n"
          "    refusal, message = _lessons_and_citations_refusal(repo, message, message_path, command)\n    _need(not refusal, refusal)",
     "    refusal, message = _lessons_and_citations_refusal(repo, message, message_path, command)\n    _need(not refusal, refusal)\n"
     "    refusal = _credential_refusal(message, message_path, command)\n    _need(not refusal, refusal)", CLI),
    (NAV, '    store.atomic_write_text(message_path, message.strip() + "\\n")  # what was checked is what is committed', "    pass", CLI),
    (NAV, 'lesson = "empty" if commit_lessons.sections(message, commit_lessons.LESSON_LABELS) else "missing"', 'lesson = "missing"', CLI),
    (NAV, '            problems.append("- line " + str(cite.line) + ": say what the commit contributed after its ID")', "            pass", CLI),
    (NAV, "    message_path.unlink()\n    head, pending = committed.commit, committed.paths", "    head, pending = committed.commit, committed.paths", CLI),
    (NAV, "allow_empty=not pending, message_file=message_path", "message_file=message_path", CLI),
    (NAV, '    elif not pending:\n        print("Nothing to commit', '    if not pending:\n        print("Nothing to commit', CLI),
    (NAV, "        _need(bool(commit_lessons.remote_change(message)),", "        _need(True,", CLI),
    (NAV, '               + (" --remote-change" if remote else ""))', '               + "")', CLI),
    (NAV, '"are in " + str(parent_return) + ".")', '"are in " + str(parent_return) + ". " + "padding to prove the budget test can fail " * 40)', CLI),
    (NAV, '        _callback(core, root, "improve-commit", action=action_id, message=str(message_path)),\n        "ShipLoop commits exactly',
     '        "ShipLoop commits exactly', CLI),
    (NAV, 'The child runs no ShipLoop callback except "\n                 "improve-commit; its command', 'The child never runs a ShipLoop callback except "\n                 "improve-commit; its command', CLI),
    (NAV, "except a recorded remote change. No push", "No push", CLI),
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
            continue
        try:
            path.write_text(original.replace(old, new, 1), encoding="utf-8")
            done = subprocess.run([sys.executable, "-B", str(ROOT / command[0]), *command[1:]], capture_output=True,
                                  text=True, cwd=ROOT, env=env, timeout=600)
        finally:
            path.write_text(original, encoding="utf-8")
        failing = sum(1 for line in (done.stdout + done.stderr).splitlines() if line.startswith(("FAIL:", "ERROR:")))
        results.append({"file": target, "replaced": old.strip().splitlines()[0][:90], "with": new.strip().splitlines()[0][:60],
                        "tests": " ".join(command[1:]) or command[0], "exit": done.returncode, "failing": failing})
        print(results[-1])
    out = Path(__file__).with_name("mutations.json")
    out.write_text(json.dumps({"rows": results, "all_red": all(row.get("exit") == 1 and row.get("failing", 0) > 0 for row in results)},
                              indent=1) + "\n", encoding="utf-8")
    return 0 if all(row.get("exit") == 1 for row in results) else 1


if __name__ == "__main__":
    sys.exit(main())
