#!/usr/bin/env python3
"""writefix.py: the write fixture of journal entry E13 (README Amendment A10): a small Python package, four independent implementation
tasks and a dependent integration task, with a hidden oracle (apparatus).

Apparatus for docs/experiments/parallel-plan-execution-20261114. The analysis5 fixture only reads; this one writes files, so it can
price what the read-only trials could not: giving each worker its own checkout, merging the results, and what happens when the plan
missed a file two tasks both change. It holds

  SKELETON    the base commit of the package every worker starts from (an empty package, an empty tests package, and check.py,
              a helper that runs the unit tests and prints ``TESTS n PASSED m``)
  REFERENCE   a correct solution for each task (calibration and the fake host write these; no real agent ever sees them)
  ORACLE      the hidden test script the scorer runs against the final tree (it lives in the trial folder beside work/)
  make_repo   writes the skeleton and makes the base commit
  evaluate    the oracle's verdict on a final tree and on the answers the tasks reported

  python3 writefix.py --selfcheck     the reference solutions pass the oracle, broken ones fail it, the evaluator reads a tree
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile

GIT = ["git", "-c", "user.name=ppe", "-c", "user.email=ppe@example.invalid", "-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null"]
MODULES = {"W1": ("m1", "rle"), "W2": ("m2", "roman_to_int"), "W3": ("m3", "merge_intervals"), "W4": ("m4", "balanced")}

CHECK_PY = '''#!/usr/bin/env python3
"""check.py: run this package's unit tests from wherever the package is checked out.

  python3 check.py m1|m2|m3|m4    the tests of one module (tests/test_<name>.py)
  python3 check.py all            every test under tests/
Prints ``TESTS n PASSED m`` and one ``FAILED <test id>`` line per failing test; exit 0 when n > 0 and every test passed."""

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)


def main(arg: str) -> int:
    loader = unittest.TestLoader()
    if arg == "all":
        suite = loader.discover(os.path.join(ROOT, "tests"), top_level_dir=ROOT)
    else:
        suite = loader.loadTestsFromName("tests.test_" + arg)
    with open(os.devnull, "w") as quiet:
        result = unittest.TextTestRunner(stream=quiet, verbosity=0).run(suite)
    total = result.testsRun
    bad = result.failures + result.errors
    passed = total - len(bad) - len(result.skipped)
    print(f"TESTS {total} PASSED {passed}")
    for case, _ in bad:
        print("FAILED", case.id())
    return 0 if total > 0 and passed == total else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "all"))
'''

SKELETON = {
    "pkg/__init__.py": '"""Small string and interval utilities."""\n',
    "tests/__init__.py": "",
    "check.py": CHECK_PY,
    ".gitignore": "__pycache__/\n*.pyc\n",
}

REFERENCE = {
    "W1": {"pkg/m1.py": '''def rle(s):
    """Run-length encode: each maximal run becomes the character and its decimal length."""
    out = []
    i = 0
    while i < len(s):
        j = i
        while j < len(s) and s[j] == s[i]:
            j += 1
        out.append(f"{s[i]}{j - i}")
        i = j
    return "".join(out)
''', "tests/test_m1.py": '''import unittest

from pkg.m1 import rle


class RleTests(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(rle(""), "")

    def test_single(self):
        self.assertEqual(rle("a"), "a1")

    def test_runs(self):
        self.assertEqual(rle("aaabccdd"), "a3b1c2d2")

    def test_no_repeats(self):
        self.assertEqual(rle("abc"), "a1b1c1")

    def test_long_run(self):
        self.assertEqual(rle("z" * 12), "z12")

    def test_case_sensitive(self):
        self.assertEqual(rle("AAaa"), "A2a2")
'''},
    "W2": {"pkg/m2.py": '''_VALUES = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}


def roman_to_int(s):
    """Convert a standard Roman numeral (1 to 3999) to an integer."""
    total = 0
    for i, ch in enumerate(s):
        value = _VALUES[ch]
        if i + 1 < len(s) and value < _VALUES[s[i + 1]]:
            total -= value
        else:
            total += value
    return total
''', "tests/test_m2.py": '''import unittest

from pkg.m2 import roman_to_int


class RomanTests(unittest.TestCase):
    def test_simple(self):
        self.assertEqual(roman_to_int("III"), 3)

    def test_subtractive(self):
        self.assertEqual(roman_to_int("IV"), 4)
        self.assertEqual(roman_to_int("IX"), 9)

    def test_mixed(self):
        self.assertEqual(roman_to_int("LVIII"), 58)

    def test_year(self):
        self.assertEqual(roman_to_int("MCMXCIV"), 1994)

    def test_largest(self):
        self.assertEqual(roman_to_int("MMMCMXCIX"), 3999)
'''},
    "W3": {"pkg/m3.py": '''def merge_intervals(intervals):
    """Merge [start, end] intervals that share at least one integer point; sorted by start; the input is not modified."""
    merged = []
    for a, b in sorted([a, b] for a, b in intervals):
        if merged and a <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])
    return merged
''', "tests/test_m3.py": '''import unittest

from pkg.m3 import merge_intervals


class MergeTests(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(merge_intervals([]), [])

    def test_overlap(self):
        self.assertEqual(merge_intervals([[1, 3], [2, 6], [8, 10], [15, 18]]), [[1, 6], [8, 10], [15, 18]])

    def test_touching_point_merges(self):
        self.assertEqual(merge_intervals([[1, 4], [4, 5]]), [[1, 5]])

    def test_adjacent_integers_do_not_merge(self):
        self.assertEqual(merge_intervals([[1, 2], [3, 4]]), [[1, 2], [3, 4]])

    def test_unsorted_input(self):
        self.assertEqual(merge_intervals([[8, 9], [1, 3], [2, 4]]), [[1, 4], [8, 9]])

    def test_input_not_modified(self):
        data = [[5, 6], [1, 2], [2, 3]]
        merge_intervals(data)
        self.assertEqual(data, [[5, 6], [1, 2], [2, 3]])
'''},
    "W4": {"pkg/m4.py": '''_PAIRS = {")": "(", "]": "[", "}": "{"}


def balanced(s):
    """True when the brackets ()[]{} in s are balanced and properly nested; other characters are ignored."""
    stack = []
    for ch in s:
        if ch in "([{":
            stack.append(ch)
        elif ch in _PAIRS:
            if not stack or stack.pop() != _PAIRS[ch]:
                return False
    return not stack
''', "tests/test_m4.py": '''import unittest

from pkg.m4 import balanced


class BalancedTests(unittest.TestCase):
    def test_empty(self):
        self.assertTrue(balanced(""))

    def test_simple_pairs(self):
        self.assertTrue(balanced("()[]{}"))

    def test_nested(self):
        self.assertTrue(balanced("{[()]}"))

    def test_mismatch(self):
        self.assertFalse(balanced("(]"))

    def test_unclosed(self):
        self.assertFalse(balanced("(()"))

    def test_closing_first(self):
        self.assertFalse(balanced("())("))

    def test_other_characters_ignored(self):
        self.assertTrue(balanced("a(b[c]{d})"))
'''},
}
TEST_COUNTS = {"W1": 6, "W2": 5, "W3": 6, "W4": 7}   # the reference test files' sizes (calibration only)
IMPORTS = {"W1": "from .m1 import rle\n", "W2": "from .m2 import roman_to_int\n", "W3": "from .m3 import merge_intervals\n", "W4": "from .m4 import balanced\n"}

ORACLE = r'''#!/usr/bin/env python3
"""The hidden oracle of the write fixture: python3 hidden_tests.py REPO prints one JSON object. Read only by the scorer."""
import importlib.util
import json
import os
import subprocess
import sys

repo = os.path.abspath(sys.argv[1])
CASES = {
    "m1": ("rle", [("", ""), ("a", "a1"), ("aaabccdd", "a3b1c2d2"), ("abc", "a1b1c1"), ("z" * 12, "z12"), ("aabbaa", "a2b2a2"), ("AAaa", "A2a2"),
                   ("x" * 100, "x100"), ("ababab", "a1b1a1b1a1b1"), ("mississippi", "m1i1s2i1s2i1p2i1"), ("qqqqqwwe", "q5w2e1"), ("Zz", "Z1z1")]),
    "m2": ("roman_to_int", [("I", 1), ("III", 3), ("IV", 4), ("IX", 9), ("LVIII", 58), ("XL", 40), ("XC", 90), ("CD", 400), ("CM", 900),
                            ("MCMXCIV", 1994), ("MMMCMXCIX", 3999), ("MDCLXVI", 1666), ("XLII", 42), ("CCCLXXXVIII", 388)]),
    "m3": ("merge_intervals", [([], []), ([[1, 3], [2, 6], [8, 10], [15, 18]], [[1, 6], [8, 10], [15, 18]]), ([[1, 4], [4, 5]], [[1, 5]]),
                               ([[1, 2], [3, 4]], [[1, 2], [3, 4]]), ([[5, 6], [1, 2], [2, 3]], [[1, 3], [5, 6]]), ([[1, 10], [2, 3], [4, 5]], [[1, 10]]),
                               ([[2, 2]], [[2, 2]]), ([[8, 9], [1, 3], [2, 4]], [[1, 4], [8, 9]]), ([[0, 0], [0, 0]], [[0, 0]]),
                               ([[-5, -1], [-2, 3]], [[-5, 3]])]),
    "m4": ("balanced", [("", True), ("()", True), ("()[]{}", True), ("(]", False), ("(()", False), ("())(", False), ("a(b[c]{d})", True),
                        ("{[()]}", True), ("{[(])}", False), ("((((", False), ("no brackets here", True), (")", False), ("[", False)]),
}
out = {"hidden": {}, "exports": {}, "tests": {}, "export_error": None}
for module, (name, cases) in CASES.items():
    path = os.path.join(repo, "pkg", module + ".py")
    row = {"cases": len(cases), "passed": 0, "error": None}
    try:
        spec = importlib.util.spec_from_file_location("oracle_" + module, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        fn = getattr(mod, name)
        for given, want in cases:
            try:
                arg = json.loads(json.dumps(given))
                got = fn(arg)
                if got == want:
                    row["passed"] += 1
            except Exception:
                pass
        if module == "m3":   # the input must not be modified
            data = [[5, 6], [1, 2], [2, 3]]
            fn(data)
            if data != [[5, 6], [1, 2], [2, 3]]:
                row["passed"] = max(0, row["passed"] - 1)
                row["modified_input"] = True
    except Exception as error:
        row["error"] = f"{type(error).__name__}: {error}"
    out["hidden"][module] = row
sys.path.insert(0, repo)
try:
    import pkg
    for module, (name, _) in CASES.items():
        out["exports"][name] = hasattr(pkg, name)
except Exception as error:
    out["export_error"] = f"{type(error).__name__}: {error}"
    out["exports"] = {name: False for _, (name, _) in CASES.items()}
for arg in ("m1", "m2", "m3", "m4", "all"):
    done = subprocess.run([sys.executable, os.path.join(repo, "check.py"), arg], capture_output=True, text=True, cwd=repo)
    line = next((l for l in done.stdout.splitlines() if l.startswith("TESTS ")), "TESTS 0 PASSED 0").split()
    out["tests"][arg] = {"tests": int(line[1]), "passed": int(line[3])}
print(json.dumps(out))
'''


def make_repo(dest: Path) -> str:
    """Write the skeleton into dest, initialise a git repository on branch main and commit it; returns the base commit."""
    dest = Path(dest)
    for rel, text in SKELETON.items():
        path = dest / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    for args in (["init", "-q", "-b", "main"], ["add", "-A"], ["commit", "-q", "-m", "base: empty package and the test helper"]):
        subprocess.run(GIT + ["-C", str(dest)] + args, check=True, capture_output=True)
    return subprocess.run(GIT + ["-C", str(dest), "rev-parse", "HEAD"], check=True, capture_output=True, text=True).stdout.strip()


def run_oracle(oracle: Path, repo: Path) -> dict:
    done = subprocess.run([sys.executable, str(oracle), str(repo)], capture_output=True, text=True, timeout=120)
    return json.loads(done.stdout.strip().splitlines()[-1])


def evaluate(oracle: Path, repo: Path, reported: dict) -> dict:
    """The oracle's verdict on the final tree plus the integrity of what the tasks reported.

    ``reported`` maps a task id to the integer answer it recorded (None when it never did). Task Wk (k = 1 to 4) reports the number of tests
    in its own test file and W5 the number of tests in the whole suite; the answers must equal what the final tree really holds, so a lost or
    overwritten file shows up as a mismatch even when the test counts a worker typed in looked right."""
    raw = run_oracle(oracle, repo)
    hidden_ok = {m: row["error"] is None and row["passed"] == row["cases"] for m, row in raw["hidden"].items()}
    by_task = {t: raw["tests"][m]["tests"] for t, (m, _) in MODULES.items()}
    answers_ok = {t: reported.get(t) == by_task[t] for t in MODULES}
    answers_ok["W5"] = reported.get("W5") == raw["tests"]["all"]["tests"]
    all_pass = raw["tests"]["all"]["tests"] > 0 and raw["tests"]["all"]["passed"] == raw["tests"]["all"]["tests"]
    verdict = {"hidden": raw["hidden"], "hidden_ok": hidden_ok, "exports": raw["exports"], "export_error": raw["export_error"],
               "tests": raw["tests"], "answers_ok": answers_ok, "suite_passes": all_pass}
    verdict["valid"] = bool(all(hidden_ok.values()) and all(raw["exports"].values()) and all(answers_ok.values()) and all_pass)
    return verdict


def selfcheck() -> int:
    ok = True
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        oracle = tmp / "hidden_tests.py"
        oracle.write_text(ORACLE)
        repo = tmp / "repo"
        make_repo(repo)
        for files in REFERENCE.values():
            for rel, text in files.items():
                (repo / rel).write_text(text)
        (repo / "pkg" / "__init__.py").write_text(SKELETON["pkg/__init__.py"] + "".join(IMPORTS.values()))
        reported = {**TEST_COUNTS, "W5": sum(TEST_COUNTS.values())}
        good = evaluate(oracle, repo, reported)
        print("reference solutions:", "valid" if good["valid"] else f"NOT valid {json.dumps(good)[:300]}")
        ok &= good["valid"]
        wrong = evaluate(oracle, repo, {**reported, "W2": 99})
        print("a wrong reported count is caught:", not wrong["valid"] and not wrong["answers_ok"]["W2"])
        ok &= (not wrong["valid"]) and (not wrong["answers_ok"]["W2"])
        (repo / "pkg" / "m1.py").write_text(REFERENCE["W1"]["pkg/m1.py"].replace('f"{s[i]}{j - i}"', 'f"{s[i]}{j - i}" if j - i > 1 else s[i]'))
        broken = evaluate(oracle, repo, reported)
        print("an rle that omits the count 1 fails the hidden cases:", (not broken["hidden_ok"]["m1"]) and not broken["valid"])
        ok &= (not broken["hidden_ok"]["m1"]) and not broken["valid"]
        (repo / "pkg" / "m1.py").write_text(REFERENCE["W1"]["pkg/m1.py"])
        (repo / "pkg" / "__init__.py").write_text(SKELETON["pkg/__init__.py"] + IMPORTS["W1"])   # three imports missing
        partial = evaluate(oracle, repo, reported)
        print("a package that exports one name of four is not valid:", (not partial["valid"]) and sum(partial["exports"].values()) == 1)
        ok &= (not partial["valid"]) and sum(partial["exports"].values()) == 1
        (repo / "tests" / "test_m3.py").unlink()
        lost = evaluate(oracle, repo, reported)
        print("a lost test file shows as a count mismatch:", not lost["answers_ok"]["W3"])
        ok &= not lost["answers_ok"]["W3"]
    print("SELFCHECK", "OK" if ok else "FAILED")
    return 0 if ok else 1


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--selfcheck", action="store_true")
    args = parser.parse_args(argv)
    if args.selfcheck:
        return selfcheck()
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
