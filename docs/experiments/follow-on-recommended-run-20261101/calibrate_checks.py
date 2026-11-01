"""Calibrate the round-6 checks of launch.sh on three hand-written slug.py variants, before any live run.

Usage: python3 calibrate_checks.py          (exit 0 when every check gives the expected status on every variant)

The variants: `reserved` (what link 1 asks for), `transliterating` (a run that chose for the reserved letters, which link 1's
reserved check must catch) and `crashing` (an unhandled error on a non-ASCII title, which link 2's no-crash check must catch).
The check texts are read out of launch.sh, so the launcher and the calibration cannot drift apart.  No model is called.
"""
from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
CHECKS = dict(re.findall(r"^(C_[A-Z_]+)='(.*)'$", (HERE / "launch.sh").read_text(encoding="utf-8"), re.M))

BASE = '''import re, sys, unicodedata


def slug(title):
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")


if __name__ == "__main__":
    title = sys.argv[1]
'''
VARIANTS = {
    "reserved": BASE + '''    if not title.isascii():
        print("undecided: non-ASCII", file=sys.stderr)
        sys.exit(2)
    print(slug(title))
''',
    "transliterating": BASE + '''    plain = "".join(c for c in unicodedata.normalize("NFD", title) if not unicodedata.combining(c))
    print(slug(plain))
''',
    "crashing": BASE + '''    if not title.isascii():
        raise ValueError("non-ASCII")
    print(slug(title))
''',
}
TEST = '''import unittest
from slug import slug


class SlugTest(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(slug("Hello, World!"), "hello-world")


if __name__ == "__main__":
    unittest.main()
'''
# status of each check (0 passes) on each variant
EXPECT = {
    "reserved": {"C_HELLO": 0, "C_SPACES": 0, "C_TESTS": 0, "C_RESERVED": 0, "C_NO_CRASH": 0, "C_ANSWER": 1, "C_ANSWER_EXIT": 1},
    "transliterating": {"C_HELLO": 0, "C_SPACES": 0, "C_TESTS": 0, "C_RESERVED": 1, "C_NO_CRASH": 0, "C_ANSWER": 0, "C_ANSWER_EXIT": 0},
    "crashing": {"C_HELLO": 0, "C_SPACES": 0, "C_TESTS": 0, "C_RESERVED": 1, "C_NO_CRASH": 1, "C_ANSWER": 1, "C_ANSWER_EXIT": 1},
}


def main() -> int:
    assert set(CHECKS) == set(EXPECT["reserved"]), sorted(CHECKS)
    bad = 0
    for variant, source in VARIANTS.items():
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / "slug.py").write_text(source, encoding="utf-8")
            (Path(folder) / "test_slug.py").write_text(TEST, encoding="utf-8")
            for name, command in CHECKS.items():
                status = subprocess.run(["sh", "-c", command], cwd=folder, capture_output=True, text=True).returncode
                want = EXPECT[variant][name]
                verdict = "ok" if (status == 0) == (want == 0) else "WRONG"
                bad += verdict != "ok"
                print(f"{variant:16} {name:12} status {status} (expected {'0' if want == 0 else 'non-zero'}) {verdict}")
    print("calibrated" if not bad else f"{bad} wrong")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
